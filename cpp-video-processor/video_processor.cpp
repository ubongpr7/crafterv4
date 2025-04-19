#include <iostream>
#include <string>
#include <vector>
#include <memory>
#include <stdexcept>

extern "C" {
#include <libavcodec/avcodec.h>
#include <libavformat/avformat.h>
#include <libavutil/avutil.h>
#include <libavutil/imgutils.h>
#include <libswscale/swscale.h>
#include <libavfilter/avfilter.h>
#include <libavfilter/buffersink.h>
#include <libavfilter/buffersrc.h>
}

#include "video_processor.h"
#include <iostream>
#include <fstream>
#include <sstream>
#include <random>
#include <algorithm>
#include <thread>
#include <chrono>
#include <cmath>
#include <regex>
#include <nlohmann/json.hpp>
#include <curl/curl.h>

// For image processing
#include <opencv2/opencv.hpp>

// For text rendering
#include <ft2build.h>
#include FT_FREETYPE_H

using json = nlohmann::json;

// Callback function for CURL to write data to a string
size_t WriteCallback(void* contents, size_t size, size_t nmemb, std::string* s) {
    size_t newLength = size * nmemb;
    try {
        s->append((char*)contents, newLength);
        return newLength;
    } catch(std::bad_alloc& e) {
        return 0;
    }
}

// Callback function for CURL to write data to a vector
size_t WriteCallbackVector(void* contents, size_t size, size_t nmemb, std::vector<uint8_t>* vec) {
    size_t newLength = size * nmemb;
    size_t oldSize = vec->size();
    try {
        vec->resize(oldSize + newLength);
        std::copy((uint8_t*)contents, (uint8_t*)contents + newLength, vec->begin() + oldSize);
        return newLength;
    } catch(std::bad_alloc& e) {
        return 0;
    }
}

class VideoProcessor {
private:
    AVFormatContext* inputFormatContext = nullptr;
    AVFormatContext* outputFormatContext = nullptr;
    AVCodecContext* decoderContext = nullptr;
    AVCodecContext* encoderContext = nullptr;
    int videoStreamIndex = -1;
    AVFilterContext* bufferSrcContext = nullptr;
    AVFilterContext* bufferSinkContext = nullptr;
    AVFilterGraph* filterGraph = nullptr;

    Aws::SDKOptions aws_options;
    std::shared_ptr<Aws::S3::S3Client> s3_client;
    std::string bucket_name;
    std::vector<fs::path> temp_files;
    std::map<std::string, Resolution> resolutions;
    std::map<std::string, double> aspect_ratios;
    std::map<std::string, std::string> fonts;

public:
    VideoProcessor();

    ~VideoProcessor();

    void cleanup() {
        if (decoderContext) avcodec_free_context(&decoderContext);
        if (encoderContext) avcodec_free_context(&encoderContext);
        if (inputFormatContext) avformat_close_input(&inputFormatContext);
        if (outputFormatContext) {
            if (!(outputFormatContext->oformat->flags & AVFMT_NOFILE))
                avio_closep(&outputFormatContext->pb);
            avformat_free_context(outputFormatContext);
        }
        if (filterGraph) avfilter_graph_free(&filterGraph);
    }

    bool openInputFile(const std::string& filename) {
        // Initialize input format context
        inputFormatContext = avformat_alloc_context();
        if (!inputFormatContext) {
            std::cerr << "Failed to allocate input format context" << std::endl;
            return false;
        }

        // Open input file
        if (avformat_open_input(&inputFormatContext, filename.c_str(), nullptr, nullptr) < 0) {
            std::cerr << "Failed to open input file: " << filename << std::endl;
            return false;
        }

        // Find stream info
        if (avformat_find_stream_info(inputFormatContext, nullptr) < 0) {
            std::cerr << "Failed to find stream information" << std::endl;
            return false;
        }

        // Find video stream
        for (unsigned int i = 0; i < inputFormatContext->nb_streams; i++) {
            if (inputFormatContext->streams[i]->codecpar->codec_type == AVMEDIA_TYPE_VIDEO) {
                videoStreamIndex = i;
                break;
            }
        }

        if (videoStreamIndex == -1) {
            std::cerr << "No video stream found" << std::endl;
            return false;
        }

        // Find decoder
        const AVCodec* decoder = avcodec_find_decoder(inputFormatContext->streams[videoStreamIndex]->codecpar->codec_id);
        if (!decoder) {
            std::cerr << "Failed to find decoder" << std::endl;
            return false;
        }

        // Allocate decoder context
        decoderContext = avcodec_alloc_context3(decoder);
        if (!decoderContext) {
            std::cerr << "Failed to allocate decoder context" << std::endl;
            return false;
        }

        // Copy codec parameters to decoder context
        if (avcodec_parameters_to_context(decoderContext, inputFormatContext->streams[videoStreamIndex]->codecpar) < 0) {
            std::cerr << "Failed to copy codec parameters to decoder context" << std::endl;
            return false;
        }

        // Open decoder
        if (avcodec_open2(decoderContext, decoder, nullptr) < 0) {
            std::cerr << "Failed to open decoder" << std::endl;
            return false;
        }

        return true;
    }

    bool setupOutput(const std::string& filename) {
        // Allocate output format context
        if (avformat_alloc_output_context2(&outputFormatContext, nullptr, nullptr, filename.c_str()) < 0) {
            std::cerr << "Failed to allocate output format context" << std::endl;
            return false;
        }

        // Add video stream
        AVStream* outStream = avformat_new_stream(outputFormatContext, nullptr);
        if (!outStream) {
            std::cerr << "Failed to create output stream" << std::endl;
            return false;
        }

        // Find encoder
        const AVCodec* encoder = avcodec_find_encoder(AV_CODEC_ID_H264);
        if (!encoder) {
            std::cerr << "Failed to find encoder" << std::endl;
            return false;
        }

        // Allocate encoder context
        encoderContext = avcodec_alloc_context3(encoder);
        if (!encoderContext) {
            std::cerr << "Failed to allocate encoder context" << std::endl;
            return false;
        }

        // Set encoder parameters
        encoderContext->height = decoderContext->height;
        encoderContext->width = decoderContext->width;
        encoderContext->sample_aspect_ratio = decoderContext->sample_aspect_ratio;
        encoderContext->pix_fmt = AV_PIX_FMT_YUV420P;
        encoderContext->time_base = inputFormatContext->streams[videoStreamIndex]->time_base;
        encoderContext->framerate = inputFormatContext->streams[videoStreamIndex]->r_frame_rate;

        if (outputFormatContext->oformat->flags & AVFMT_GLOBALHEADER)
            encoderContext->flags |= AV_CODEC_FLAG_GLOBAL_HEADER;

        // Open encoder
        if (avcodec_open2(encoderContext, encoder, nullptr) < 0) {
            std::cerr << "Failed to open encoder" << std::endl;
            return false;
        }

        // Copy encoder parameters to output stream
        if (avcodec_parameters_from_context(outStream->codecpar, encoderContext) < 0) {
            std::cerr << "Failed to copy encoder parameters to output stream" << std::endl;
            return false;
        }

        outStream->time_base = encoderContext->time_base;

        // Open output file
        if (!(outputFormatContext->oformat->flags & AVFMT_NOFILE)) {
            if (avio_open(&outputFormatContext->pb, filename.c_str(), AVIO_FLAG_WRITE) < 0) {
                std::cerr << "Failed to open output file: " << filename << std::endl;
                return false;
            }
        }

        // Write header
        if (avformat_write_header(outputFormatContext, nullptr) < 0) {
            std::cerr << "Failed to write header to output file" << std::endl;
            return false;
        }

        return true;
    }

    bool setupFilter(const std::string& filterDesc) {
        char args[512];
        int ret = 0;

        // Create filter graph
        filterGraph = avfilter_graph_alloc();
        if (!filterGraph) {
            std::cerr << "Failed to allocate filter graph" << std::endl;
            return false;
        }

        // Create buffer source filter
        const AVFilter* bufferSrc = avfilter_get_by_name("buffer");
        if (!bufferSrc) {
            std::cerr << "Failed to find buffer source filter" << std::endl;
            return false;
        }

        snprintf(args, sizeof(args),
                "video_size=%dx%d:pix_fmt=%d:time_base=%d/%d:pixel_aspect=%d/%d",
                decoderContext->width, decoderContext->height, decoderContext->pix_fmt,
                decoderContext->time_base.num, decoderContext->time_base.den,
                decoderContext->sample_aspect_ratio.num, decoderContext->sample_aspect_ratio.den);

        ret = avfilter_graph_create_filter(&bufferSrcContext, bufferSrc, "in", args, nullptr, filterGraph);
        if (ret < 0) {
            std::cerr << "Failed to create buffer source filter" << std::endl;
            return false;
        }

        // Create buffer sink filter
        const AVFilter* bufferSink = avfilter_get_by_name("buffersink");
        if (!bufferSink) {
            std::cerr << "Failed to find buffer sink filter" << std::endl;
            return false;
        }

        ret = avfilter_graph_create_filter(&bufferSinkContext, bufferSink, "out", nullptr, nullptr, filterGraph);
        if (ret < 0) {
            std::cerr << "Failed to create buffer sink filter" << std::endl;
            return false;
        }

        // Set output pixel format
        enum AVPixelFormat pix_fmts[] = { AV_PIX_FMT_YUV420P, AV_PIX_FMT_NONE };
        ret = av_opt_set_int_list(bufferSinkContext, "pix_fmts", pix_fmts, AV_PIX_FMT_NONE, AV_OPT_SEARCH_CHILDREN);
        if (ret < 0) {
            std::cerr << "Failed to set output pixel format" << std::endl;
            return false;
        }

        // Parse and create filter chain
        AVFilterInOut* outputs = avfilter_inout_alloc();
        AVFilterInOut* inputs = avfilter_inout_alloc();
        if (!outputs || !inputs) {
            avfilter_inout_free(&inputs);
            avfilter_inout_free(&outputs);
            std::cerr << "Failed to allocate filter inputs/outputs" << std::endl;
            return false;
        }

        outputs->name = av_strdup("in");
        outputs->filter_ctx = bufferSrcContext;
        outputs->pad_idx = 0;
        outputs->next = nullptr;

        inputs->name = av_strdup("out");
        inputs->filter_ctx = bufferSinkContext;
        inputs->pad_idx = 0;
        inputs->next = nullptr;

        ret = avfilter_graph_parse_ptr(filterGraph, filterDesc.c_str(), &inputs, &outputs, nullptr);
        avfilter_inout_free(&inputs);
        avfilter_inout_free(&outputs);
        if (ret < 0) {
            std::cerr << "Failed to parse filter description: " << filterDesc << std::endl;
            return false;
        }

        ret = avfilter_graph_config(filterGraph, nullptr);
        if (ret < 0) {
            std::cerr << "Failed to configure filter graph" << std::endl;
            return false;
        }

        return true;
    }

    bool processVideo() {
        AVPacket* packet = av_packet_alloc();
        AVFrame* frame = av_frame_alloc();
        AVFrame* filteredFrame = av_frame_alloc();
        int ret;

        if (!packet || !frame || !filteredFrame) {
            std::cerr << "Failed to allocate packet or frame" << std::endl;
            av_packet_free(&packet);
            av_frame_free(&frame);
            av_frame_free(&filteredFrame);
            return false;
        }

        // Process frames
        while (av_read_frame(inputFormatContext, packet) >= 0) {
            if (packet->stream_index == videoStreamIndex) {
                // Send packet to decoder
                ret = avcodec_send_packet(decoderContext, packet);
                if (ret < 0) {
                    std::cerr << "Error sending packet to decoder" << std::endl;
                    break;
                }

                while (ret >= 0) {
                    // Receive frame from decoder
                    ret = avcodec_receive_frame(decoderContext, frame);
                    if (ret == AVERROR(EAGAIN) || ret == AVERROR_EOF) {
                        break;
                    } else if (ret < 0) {
                        std::cerr << "Error receiving frame from decoder" << std::endl;
                        goto end;
                    }

                    // Push frame to filter graph
                    ret = av_buffersrc_add_frame_flags(bufferSrcContext, frame, 0);
                    if (ret < 0) {
                        std::cerr << "Error adding frame to filter graph" << std::endl;
                        goto end;
                    }

                    while (true) {
                        // Get filtered frame
                        ret = av_buffersink_get_frame(bufferSinkContext, filteredFrame);
                        if (ret == AVERROR(EAGAIN) || ret == AVERROR_EOF) {
                            break;
                        }
                        if (ret < 0) {
                            std::cerr << "Error getting frame from filter graph" << std::endl;
                            goto end;
                        }

                        // Encode filtered frame
                        ret = avcodec_send_frame(encoderContext, filteredFrame);
                        if (ret < 0) {
                            std::cerr << "Error sending frame to encoder" << std::endl;
                            av_frame_unref(filteredFrame);
                            goto end;
                        }

                        while (ret >= 0) {
                            AVPacket* outPacket = av_packet_alloc();
                            ret = avcodec_receive_packet(encoderContext, outPacket);
                            if (ret == AVERROR(EAGAIN) || ret == AVERROR_EOF) {
                                av_packet_free(&outPacket);
                                break;
                            } else if (ret < 0) {
                                std::cerr << "Error receiving packet from encoder" << std::endl;
                                av_packet_free(&outPacket);
                                goto end;
                            }

                            // Rescale output packet timestamp
                            av_packet_rescale_ts(outPacket, encoderContext->time_base, 
                                                outputFormatContext->streams[0]->time_base);
                            outPacket->stream_index = 0;

                            // Write packet to output file
                            ret = av_interleaved_write_frame(outputFormatContext, outPacket);
                            av_packet_free(&outPacket);
                            if (ret < 0) {
                                std::cerr << "Error writing packet to output file" << std::endl;
                                goto end;
                            }
                        }

                        av_frame_unref(filteredFrame);
                    }

                    av_frame_unref(frame);
                }
            }
            av_packet_unref(packet);
        }

        // Flush encoder
        avcodec_send_frame(encoderContext, nullptr);
        while (true) {
            AVPacket* outPacket = av_packet_alloc();
            ret = avcodec_receive_packet(encoderContext, outPacket);
            if (ret == AVERROR(EAGAIN) || ret == AVERROR_EOF) {
                av_packet_free(&outPacket);
                break;
            } else if (ret < 0) {
                std::cerr << "Error flushing encoder" << std::endl;
                av_packet_free(&outPacket);
                goto end;
            }

            av_packet_rescale_ts(outPacket, encoderContext->time_base, 
                                outputFormatContext->streams[0]->time_base);
            outPacket->stream_index = 0;

            ret = av_interleaved_write_frame(outputFormatContext, outPacket);
            av_packet_free(&outPacket);
            if (ret < 0) {
                std::cerr << "Error writing packet to output file" << std::endl;
                goto end;
            }
        }

        // Write trailer
        av_write_trailer(outputFormatContext);

    end:
        av_packet_free(&packet);
        av_frame_free(&frame);
        av_frame_free(&filteredFrame);
        return ret >= 0;
    }

    // Example methods for common video operations
    bool trim(const std::string& inputFile, const std::string& outputFile, double startTime, double endTime) {
        if (!openInputFile(inputFile)) return false;
        
        // Set up filter for trimming
        std::string filterDesc = "trim=start=" + std::to_string(startTime) + ":end=" + std::to_string(endTime) + ",setpts=PTS-STARTPTS";
        if (!setupFilter(filterDesc)) return false;
        
        if (!setupOutput(outputFile)) return false;
        return processVideo();
    }

    bool resize(const std::string& inputFile, const std::string& outputFile, int width, int height) {
        if (!openInputFile(inputFile)) return false;
        
        // Set up filter for resizing
        std::string filterDesc = "scale=" + std::to_string(width) + ":" + std::to_string(height);
        if (!setupFilter(filterDesc)) return false;
        
        if (!setupOutput(outputFile)) return false;
        return processVideo();
    }

    bool rotate(const std::string& inputFile, const std::string& outputFile, int angle) {
        if (!openInputFile(inputFile)) return false;
        
        // Set up filter for rotation
        std::string filterDesc = "rotate=" + std::to_string(angle * M_PI / 180.0);
        if (!setupFilter(filterDesc)) return false;
        
        if (!setupOutput(outputFile)) return false;
        return processVideo();
    }

    bool concatenate(const std::vector<std::string>& inputFiles, const std::string& outputFile) {
        // This is a simplified version - actual implementation would be more complex
        std::string filterList = "concat:";
        for (size_t i = 0; i < inputFiles.size(); i++) {
            filterList += inputFiles[i];
            if (i < inputFiles.size() - 1) filterList += "|";
        }
        
        // For simplicity, we'll just use the system command to call ffmpeg directly
        std::string command = "ffmpeg -i \"" + filterList + "\" -c copy \"" + outputFile + "\"";
        return system(command.c_str()) == 0;
    }

    bool addAudio(const std::string& videoFile, const std::string& audioFile, const std::string& outputFile) {
        // For simplicity, we'll just use the system command to call ffmpeg directly
        std::string command = "ffmpeg -i \"" + videoFile + "\" -i \"" + audioFile + 
                             "\" -c:v copy -c:a aac -map 0:v:0 -map 1:a:0 \"" + outputFile + "\"";
        return system(command.c_str()) == 0;
    }

bool VideoProcessor::initialize(const std::string& aws_access_key, const std::string& aws_secret_key, const std::string& bucket) {
    // Initialize AWS SDK
    Aws::InitAPI(aws_options);
    
    // Configure AWS credentials
    Aws::Auth::AWSCredentials credentials;
    credentials.SetAWSAccessKeyId(aws_access_key);
    credentials.SetAWSSecretKey(aws_secret_key);
    
    // Create S3 client
    Aws::Client::ClientConfiguration clientConfig;
    clientConfig.region = "us-east-1"; // Set your region
    s3_client = std::make_shared<Aws::S3::S3Client>(credentials, clientConfig);
    
    bucket_name = bucket;
    
    return true;
}

std::vector<uint8_t> VideoProcessor::downloadFromS3(const std::string& file_key) {
    std::vector<uint8_t> file_content;
    
    Aws::S3::Model::GetObjectRequest request;
    request.SetBucket(bucket_name);
    request.SetKey(file_key);
    
    auto outcome = s3_client->GetObject(request);
    
    if (outcome.IsSuccess()) {
        Aws::IOStream& body_stream = outcome.GetResult().GetBody();
        
        // Read the data
        char buffer[4096];
        while (body_stream.good()) {
            body_stream.read(buffer, sizeof(buffer));
            auto bytes_read = body_stream.gcount();
            
            if (bytes_read > 0) {
                size_t current_size = file_content.size();
                file_content.resize(current_size + bytes_read);
                std::memcpy(file_content.data() + current_size, buffer, bytes_read);
            }
        }
        
        std::cout << "Downloaded " << file_key << " from S3 (" << file_content.size() << " bytes)" << std::endl;
    } else {
        std::cerr << "Failed to download " << file_key << " from S3: " 
                  << outcome.GetError().GetExceptionName() << " - " 
                  << outcome.GetError().GetMessage() << std::endl;
    }
    
    return file_content;
}

bool VideoProcessor::uploadToS3(const std::string& file_path, const std::string& s3_key) {
    std::ifstream file(file_path, std::ios::binary);
    if (!file) {
        std::cerr << "Failed to open file: " << file_path << std::endl;
        return false;
    }
    
    // Get file size
    file.seekg(0, std::ios::end);
    size_t file_size = file.tellg();
    file.seekg(0, std::ios::beg);
    
    // Read file content
    std::vector<char> file_content(file_size);
    file.read(file_content.data(), file_size);
    
    // Create memory stream
    auto input_data = Aws::MakeShared<Aws::StringStream>("PutObjectInputStream");
    input_data->write(file_content.data(), file_size);
    
    // Create request
    Aws::S3::Model::PutObjectRequest request;
    request.SetBucket(bucket_name);
    request.SetKey(s3_key);
    request.SetBody(input_data);
    
    // Set content type based on file extension
    std::string extension = file_path.substr(file_path.find_last_of(".") + 1);
    if (extension == "mp4" || extension == "avi" || extension == "mov") {
        request.SetContentType("video/" + extension);
    } else if (extension == "mp3" || extension == "wav") {
        request.SetContentType("audio/" + extension);
    } else if (extension == "jpg" || extension == "jpeg") {
        request.SetContentType("image/jpeg");
    } else if (extension == "png") {
        request.SetContentType("image/png");
    } else if (extension == "json") {
        request.SetContentType("application/json");
    } else if (extension == "txt") {
        request.SetContentType("text/plain");
    }
    
    // Upload file
    auto outcome = s3_client->PutObject(request);
    
    if (outcome.IsSuccess()) {
        std::cout << "Uploaded " << file_path << " to S3 as " << s3_key << std::endl;
        return true;
    } else {
        std::cerr << "Failed to upload " << file_path << " to S3: " 
                  << outcome.GetError().GetExceptionName() << " - " 
                  << outcome.GetError().GetMessage() << std::endl;
        return false;
    }
}

std::string VideoProcessor::convertTextToSpeech(const std::string& text_file_path, const std::string& voice_id, 
                                              const std::string& api_key, const std::string& output_audio_file) {
    // Read the text from the file
    std::ifstream text_file(text_file_path);
    if (!text_file) {
        std::cerr << "Failed to open text file: " << text_file_path << std::endl;
        return "";
    }
    
    std::stringstream buffer;
    buffer << text_file.rdbuf();
    std::string text = buffer.str();
    
    // Replace newlines with spaces
    text = std::regex_replace(text, std::regex("\\r?\\n"), " ");
    
    // Call ElevenLabs API
    CURL* curl = curl_easy_init();
    if (!curl) {
        std::cerr << "Failed to initialize CURL" << std::endl;
        return "";
    }
    
    // Prepare JSON payload
    json payload = {
        {"text", text},
        {"model_id", "eleven_monolingual_v1"},
        {"voice_settings", {
            {"stability", 1.0},
            {"similarity_boost", 0.66},
            {"style", 0.0},
            {"use_speaker_boost", true},
            {"speed", 1.1}
        }}
    };
    
    std::string payload_str = payload.dump();
    
    // Set up the request
    std::string url = "https://api.elevenlabs.io/v1/text-to-speech/" + voice_id;
    
    struct curl_slist* headers = NULL;
    headers = curl_slist_append(headers, "Content-Type: application/json");
    std::string auth_header = "xi-api-key: " + api_key;
    headers = curl_slist_append(headers, auth_header.c_str());
    
    curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
    curl_easy_setopt(curl, CURLOPT_POSTFIELDS, payload_str.c_str());
    
    // Set up the response
    std::vector<uint8_t> response_data;
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, WriteCallbackVector);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response_data);
    
    // Perform the request
    CURLcode res = curl_easy_perform(curl);
    
    // Check for errors
    if (res != CURLE_OK) {
        std::cerr << "CURL failed: " << curl_easy_strerror(res) << std::endl;
        curl_slist_free_all(headers);
        curl_easy_cleanup(curl);
        return "";
    }
    
    // Get HTTP response code
    long http_code = 0;
    curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &http_code);
    
    // Clean up
    curl_slist_free_all(headers);
    curl_easy_cleanup(curl);
    
    if (http_code != 200) {
        std::cerr << "ElevenLabs API returned HTTP code " << http_code << std::endl;
        return "";
    }
    
    // Save the audio data to a file
    std::ofstream output_file(output_audio_file, std::ios::binary);
    if (!output_file) {
        std::cerr << "Failed to open output file: " << output_audio_file << std::endl;
        return "";
    }
    
    output_file.write(reinterpret_cast<const char*>(response_data.data()), response_data.size());
    output_file.close();
    
    // Upload the file to S3
    std::string timestamp = std::to_string(std::chrono::system_clock::now().time_since_epoch().count() / 1000000000);
    std::string s3_key = timestamp + "_audio.mp3";
    
    if (uploadToS3(output_audio_file, s3_key)) {
        return s3_key;
    } else {
        return "";
    }
}

std::string VideoProcessor::generateSrtFile(const std::string& audio_file_path, const std::string& text_file_path) {
    // Create a temporary output file for the SRT
    fs::path temp_srt = fs::temp_directory_path() / (generateRandomString() + ".json");
    temp_files.push_back(temp_srt);
    
    // Use aeneas to generate the SRT file
    std::string command = "python3 -m aeneas.tools.execute_task \"" + audio_file_path + "\" \"" + text_file_path + 
                         "\" \"task_language=eng|is_text_type=plain|os_task_file_format=json\" \"" + temp_srt.string() + "\"";
    
    std::cout << "Running command: " << command << std::endl;
    
    int result = system(command.c_str());
    if (result != 0) {
        std::cerr << "Error generating SRT file. Command returned: " << result << std::endl;
        return "";
    }
    
    // Upload the SRT file to S3
    std::string timestamp = std::to_string(std::chrono::system_clock::now().time_since_epoch().count() / 1000000000);
    std::string s3_key = timestamp + "_generated.json";
    
    if (uploadToS3(temp_srt.string(), s3_key)) {
        return s3_key;
    } else {
        return "";
    }
}

std::string VideoProcessor::generateSubclipsSrtFile(const std::string& audio_file_path, const std::string& text_file_path) {
    // Similar to generateSrtFile but for subclips
    fs::path temp_srt = fs::temp_directory_path() / (generateRandomString() + "_subclips.json");
    temp_files.push_back(temp_srt);
    
    std::string command = "python3 -m aeneas.tools.execute_task \"" + audio_file_path + "\" \"" + text_file_path + 
                         "\" \"task_language=eng|is_text_type=plain|os_task_file_format=json\" \"" + temp_srt.string() + "\"";
    
    std::cout << "Running command: " << command << std::endl;
    
    int result = system(command.c_str());
    if (result != 0) {
        std::cerr << "Error generating subclips SRT file. Command returned: " << result << std::endl;
        return "";
    }
    
    // Upload the SRT file to S3
    std::string timestamp = std::to_string(std::chrono::system_clock::now().time_since_epoch().count() / 1000000000);
    std::string s3_key = timestamp + "_subclips_generated.json";
    
    if (uploadToS3(temp_srt.string(), s3_key)) {
        return s3_key;
    } else {
        return "";
    }
}

std::vector<SubtitleInfo> VideoProcessor::processSrtFile(const std::string& srt_file_path) {
    std::vector<SubtitleInfo> result;
    
    // Read the JSON file
    std::ifstream file(srt_file_path);
    if (!file) {
        std::cerr << "Failed to open SRT file: " << srt_file_path << std::endl;
        return result;
    }
    
    json srt_data;
    try {
        file >> srt_data;
    } catch (const std::exception& e) {
        std::cerr << "Error parsing SRT JSON: " << e.what() << std::endl;
        return result;
    }
    
    // Process the fragments
    if (srt_data.contains("fragments") && srt_data["fragments"].is_array()) {
        for (size_t i = 0; i < srt_data["fragments"].size(); ++i) {
            const auto& fragment = srt_data["fragments"][i];
            
            if (fragment.contains("begin") && fragment.contains("end") && 
                fragment.contains("lines") && fragment["lines"].is_array() && 
                !fragment["lines"].empty()) {
                
                double begin = std::stod(fragment["begin"].get<std::string>());
                double end = std::stod(fragment["end"].get<std::string>());
                std::string text = fragment["lines"][0].get<std::string>();
                
                result.push_back({static_cast<int>(i + 1), begin, end, text});
            }
        }
    }
    
    return result;
}

std::string VideoProcessor::generateBlankVideoWithAudio(const std::string& audio_file_path, const std::string& resolution_key, 
                                                      double duration) {
    // Check if the resolution is supported
    if (resolutions.find(resolution_key) == resolutions.end()) {
        std::cerr << "Resolution '" << resolution_key << "' is not supported." << std::endl;
        return "";
    }
    
    // Get the resolution
    Resolution res = resolutions[resolution_key];
    
    // Create a temporary output file for the video
    fs::path temp_video = fs::temp_directory_path() / (generateRandomString() + ".mp4");
    temp_files.push_back(temp_video);
    
    // Use FFmpeg to create a blank video with the audio
    std::string command = "ffmpeg -y -f lavfi -i color=c=black:s=" + std::to_string(res.width) + "x" + 
                         std::to_string(res.height) + ":d=" + std::to_string(duration) + 
                         " -i \"" + audio_file_path + "\" -c:v libx264 -preset ultrafast -c:a aac -shortest \"" + 
                         temp_video.string() + "\"";
    
    std::cout << "Running command: " << command << std::endl;
    
    int result = system(command.c_str());
    if (result != 0) {
        std::cerr << "Error generating blank video. Command returned: " << result << std::endl;
        return "";
    }
    
    // Upload the video file to S3
    std::string timestamp = std::to_string(std::chrono::system_clock::now().time_since_epoch().count() / 1000000000);
    std::string s3_key = timestamp + "_blank_video.mp4";
    
    if (uploadToS3(temp_video.string(), s3_key)) {
        return s3_key;
    } else {
        return "";
    }
}

std::shared_ptr<VideoClip> VideoProcessor::loadVideoFromFile(const std::string& file_path) {
    return std::make_shared<VideoClip>(file_path);
}

std::vector<SubtitleItem> VideoProcessor::loadSubtitlesFromFile(const std::string& file_path) {
    std::vector<SubtitleItem> subtitles;
    
    // Read the JSON file
    std::ifstream file(file_path);
    if (!file) {
        std::cerr << "Failed to open subtitle file: " << file_path << std::endl;
        return subtitles;
    }
    
    json srt_data;
    try {
        file >> srt_data;
    } catch (const std::exception& e) {
        std::cerr << "Error parsing subtitle JSON: " << e.what() << std::endl;
        return subtitles;
    }
    
    // Process the fragments
    if (srt_data.contains("fragments") && srt_data["fragments"].is_array()) {
        for (size_t i = 0; i < srt_data["fragments"].size(); ++i) {
            const auto& fragment = srt_data["fragments"][i];
            
            if (fragment.contains("begin") && fragment.contains("end") && 
                fragment.contains("lines") && fragment["lines"].is_array() && 
                !fragment["lines"].empty()) {
                
                double begin = std::stod(fragment["begin"].get<std::string>());
                double end = std::stod(fragment["end"].get<std::string>());
                std::string text = fragment["lines"][0].get<std::string>();
                
                subtitles.push_back(SubtitleItem(i + 1, begin, end, text));
            }
        }
    }
    
    return subtitles;
}

std::pair<std::vector<std::shared_ptr<VideoClip>>, std::vector<SubtitleItem>> 
VideoProcessor::getSegmentsUsingSrt(std::shared_ptr<VideoClip> video, const std::vector<SubtitleItem>& subtitles) {
    std::vector<std::shared_ptr<VideoClip>> video_segments;
    std::vector<SubtitleItem> subtitle_segments;
    
    double video_duration = video->getDuration();
    
    for (const auto& subtitle : subtitles) {
        double start = subtitle.getStartTime();
        double end = subtitle.getEndTime();
        
        if (start >= video_duration) {
            std::cout << "Subtitle start time (" << start << ") is beyond video duration (" 
                     << video_duration << "). Skipping this subtitle." << std::endl;
            continue;
        }
        
        if (end > video_duration) {
            std::cout << "Subtitle end time (" << end << ") exceeds video duration (" 
                     << video_duration << "). Clamping to video duration." << std::endl;
            end = video_duration;
        }
        
        if (end <= start) {
            std::cout << "Invalid subtitle duration: start (" << start << ") >= end (" 
                     << end << "). Skipping this subtitle." << std::endl;
            continue;
        }
        
        auto video_segment = video->subclip(start, end);
        if (video_segment->getDuration() == 0) {
            std::cout << "Video segment duration is zero for subtitle (" 
                     << subtitle.getText() << "). Skipping this segment." << std::endl;
            continue;
        }
        
        subtitle_segments.push_back(subtitle);
        video_segments.push_back(video_segment);
    }
    
    return {video_segments, subtitle_segments};
}

std::shared_ptr<VideoClip> VideoProcessor::adjustSegmentDuration(std::shared_ptr<VideoClip> segment, double duration, bool strict) {
    double current_duration = segment->getDuration();
    
    if (duration < 0) {
        throw std::invalid_argument("Target duration must be non-negative.");
    }
    
    if (current_duration == 0) {
        throw std::invalid_argument("Segment duration is zero; cannot adjust.");
    }
    
    // If durations are very close, still adjust to be exact
    if (std::abs(current_duration - duration) < 1e-3) {
        return segment->subclip(0, duration);
    }
    
    std::shared_ptr<VideoClip> adjusted_segment;
    if (current_duration < duration) {
        // Calculate speed factor with a small buffer to prevent overshooting
        double speed_factor = (current_duration / duration) * 0.999;
        adjusted_segment = segment->speedx(speed_factor);
    } else {
        adjusted_segment = segment->subclip(0, duration);
    }
    
    // When strict mode is enabled, force exact duration
    if (strict) {
        double final_duration = adjusted_segment->getDuration();
        if (std::abs(final_duration - duration) > 0.001) {
            adjusted_segment = adjusted_segment->subclip(0, duration);
        }
        
        // Verify the final duration
        if (std::abs(adjusted_segment->getDuration() - duration) > 0.001) {
            throw std::runtime_error("Failed to achieve target duration. Target: " + 
                                    std::to_string(duration) + ", Actual: " + 
                                    std::to_string(adjusted_segment->getDuration()));
        }
    }
    
    return adjusted_segment;
}

std::shared_ptr<VideoClip> VideoProcessor::cropToAspectRatio(std::shared_ptr<VideoClip> clip, double desired_aspect_ratio) {
    auto size = clip->getSize();
    int original_width = size.first;
    int original_height = size.second;
    
    double original_aspect_ratio = static_cast<double>(original_width) / original_height;
    
    // If the aspect ratios are already close, return the original clip
    if (std::abs(original_aspect_ratio - desired_aspect_ratio) < 0.01) {
        return clip;
    }
    
    int x1, y1, x2, y2;
    
    if (desired_aspect_ratio == 9.0/16.0) {
        // Special case for 9:16 aspect ratio
        int crop_width = static_cast<int>(original_height * 9.0 / 16.0);
        return clip->crop(original_width/2 - 300, 0, original_width/2 + 300, 5000);
    }
    
    if (original_aspect_ratio > desired_aspect_ratio) {
        // Original is wider than desired, crop the width
        int new_width = static_cast<int>(original_height * desired_aspect_ratio);
        int new_height = original_height;
        x1 = (original_width - new_width) / 2;
        y1 = 0;
        x2 = x1 + new_width;
        y2 = new_height;
    } else {
        // Original is taller than desired, crop the height
        int new_width = original_width;
        int new_height = static_cast<int>(original_width / desired_aspect_ratio);
        x1 = 0;
        y1 = (original_height - new_height) / 2;
        x2 = new_width;
        y2 = y1 + new_height;
    }
    
    return clip->crop(x1, y1, x2, y2);
}

std::shared_ptr<VideoClip> VideoProcessor::cropVideoWithFfmpeg(const std::string& input_video, 
                                                             const Resolution& output_resolution, 
                                                             std::shared_ptr<VideoClip> clip, 
                                                             bool is_tiktok) {
    auto size = clip->getSize();
    int input_width = size.first;
    int input_height = size.second;
    
    int output_width = output_resolution.width;
    int output_height = output_resolution.height;
    
    // Create a temporary output file
    fs::path temp_output = fs::temp_directory_path() / (generateRandomString() + ".mp4");
    temp_files.push_back(temp_output);
    
    std::string command;
    
    if (is_tiktok) {
        // For TikTok videos, use a blurred background
        command = "ffmpeg -y -i \"" + input_video + "\" -fflags +genpts -r 30 -vf " +
                 "\"split=2[original][blurred];" +
                 "[blurred]scale=" + std::to_string(output_width) + ":" + std::to_string(output_height) + 
                 ",boxblur=luma_radius=min(h\\,w)/20:luma_power=1[blurred];" +
                 "[original]scale=" + std::to_string(output_width) + ":" + std::to_string(output_height) + 
                 ":force_original_aspect_ratio=decrease[scaled];" +
                 "[blurred][scaled]overlay=(W-w)/2:(H-h)/2\" " +
                 "-c:v libx264 -preset fast -crf 23 -c:a aac -b:a 128k -fps_mode vfr \"" + 
                 temp_output.string() + "\"";
    } else {
        // Calculate crop parameters
        double input_aspect = static_cast<double>(input_width) / input_height;
        double output_aspect = static_cast<double>(output_width) / output_height;
        
        int new_width, new_height, x_offset, y_offset;
        
        if (input_aspect > output_aspect) {
            new_width = static_cast<int>(input_height * output_aspect);
            new_height = input_height;
            x_offset = (input_width - new_width) / 2;
            y_offset = 0;
        } else {
            new_width = input_width;
            new_height = static_cast<int>(input_width / output_aspect);
            x_offset = 0;
            y_offset = (input_height - new_height) / 2;
        }
        
        command = "ffmpeg -y -i \"" + input_video + "\" -vf \"crop=" + 
                 std::to_string(new_width) + ":" + std::to_string(new_height) + ":" + 
                 std::to_string(x_offset) + ":" + std::to_string(y_offset) + "\" " +
                 "-c:v libx264 -preset fast -crf 23 -c:a copy \"" + 
                 temp_output.string() + "\"";
    }
    
    std::cout << "Running command: " << command << std::endl;
    
    int result = system(command.c_str());
    if (result != 0) {
        std::cerr << "Error cropping video. Command returned: " << result << std::endl;
        return clip; // Return original clip on error
    }
    
    return std::make_shared<VideoClip>(temp_output.string());
}

std::vector<std::shared_ptr<VideoClip>> VideoProcessor::resizeClipsToMaxSize(
    const std::vector<std::shared_ptr<VideoClip>>& clips) {
    
    if (clips.empty()) {
        return {};
    }
    
    // Find the maximum width and height
    int max_width = 0;
    int max_height = 0;
    
    for (const auto& clip : clips) {
        auto size = clip->getSize();
        max_width = std::max(max_width, size.first);
        max_height = std::max(max_height, size.second);
    }
    
    // Resize all clips to the maximum size
    std::vector<std::shared_ptr<VideoClip>> resized_clips;
    
    for (const auto& clip : clips) {
        if (max_width == 0 || max_height == 0) {
            resized_clips.push_back(clip);
        } else {
            resized_clips.push_back(clip->resize({max_width, max_height}));
        }
    }
    
    return resized_clips;
}

std::shared_ptr<VideoClip> VideoProcessor::concatenateClips(
    const std::vector<std::shared_ptr<VideoClip>>& clips,
    const std::optional<Resolution>& target_resolution,
    int target_fps) {
    
    if (clips.empty()) {
        throw std::invalid_argument("Cannot concatenate empty clip list");
    }
    
    // Create a temporary file list for FFmpeg
    fs::path temp_list = fs::temp_directory_path() / (generateRandomString() + ".txt");
    temp_files.push_back(temp_list);
    
    std::ofstream list_file(temp_list.string());
    if (!list_file) {
        throw std::runtime_error("Failed to create temporary file list");
    }
    
    // Create temporary files for each clip
    std::vector<fs::path> temp_clip_files;
    
    for (size_t i = 0; i < clips.size(); ++i) {
        fs::path temp_clip = fs::temp_directory_path() / (generateRandomString() + ".mp4");
        temp_files.push_back(temp_clip);
        temp_clip_files.push_back(temp_clip);
        
        // Set the frame rate
        auto clip = clips[i];
        clip->setFps(target_fps);
        
        // Write the clip to a temporary file
        clip->writeVideofile(temp_clip.string(), "libx264", "ultrafast", "aac", target_fps);
        
        // Add the file to the list
        list_file << "file '" << temp_clip.string() << "'" << std::endl;
    }
    
    list_file.close();
    
    // Create a temporary output file
    fs::path temp_output = fs::temp_directory_path() / (generateRandomString() + ".mp4");
    temp_files.push_back(temp_output);
    
    // Use FFmpeg to concatenate the clips
    std::string command = "ffmpeg -y -f concat -safe 0 -i \"" + temp_list.string() + 
                         "\" -c copy \"" + temp_output.string() + "\"";
    
    std::cout << "Running command: " << command << std::endl;
    
    int result = system(command.c_str());
    if (result != 0) {
        std::cerr << "Error concatenating clips. Command returned: " << result << std::endl;
        throw std::runtime_error("Failed to concatenate clips");
    }
    
    return std::make_shared<VideoClip>(temp_output.string());
}

std::vector<std::shared_ptr<VideoClip>> VideoProcessor::replaceVideoSegments(
    const std::vector<std::shared_ptr<VideoClip>>& original_segments,
    const std::vector<std::shared_ptr<VideoClip>>& replacement_videos,
    const std::vector<SubtitleItem>& subtitles,
    std::shared_ptr<VideoClip> original_video) {
    
    std::vector<std::shared_ptr<VideoClip>> combined_segments = original_segments;
    
    for (size_t replace_index = 0; replace_index < replacement_videos.size(); ++replace_index) {
        if (replace_index < combined_segments.size()) {
            // Get exact target duration from subtitle timings
            double start = subtitles[replace_index].getStartTime();
            double end = subtitles[replace_index].getEndTime();
            double target_duration = end - start;
            
            auto replacement_segment = adjustSegmentDuration(
                replacement_videos[replace_index],
                target_duration,
                true
            );
            
            // Adjust segment properties
            replacement_segment->setFps(original_video->getFps());
            replacement_segment->setDuration(replacement_segment->getDuration());
            
            // Add subtitles to clip
            auto adjusted_segment_with_subtitles = addSubtitlesToClip(
                replacement_segment,
                subtitles[replace_index]
            );
            
            // Verify final duration
            if (std::abs(adjusted_segment_with_subtitles->getDuration() - target_duration) > 0.001) {
                adjusted_segment_with_subtitles = adjusted_segment_with_subtitles->subclip(0, target_duration);
            }
            
            combined_segments[replace_index] = adjusted_segment_with_subtitles;
        }
    }
    
    return combined_segments;
}

std::shared_ptr<VideoClip> VideoProcessor::addSubtitlesToClip(
    std::shared_ptr<VideoClip> clip,
    const SubtitleItem& subtitle) {
    
    std::cout << "Adding subtitle: " << subtitle.getText() << std::endl;
    
    // Create a temporary subtitle file
    fs::path temp_srt = fs::temp_directory_path() / (generateRandomString() + ".srt");
    temp_files.push_back(temp_srt);
    
    std::ofstream srt_file(temp_srt.string());
    if (!srt_file) {
        std::cerr << "Failed to create temporary subtitle file" << std::endl;
        return clip;
    }
    
    // Write the subtitle to the file
    srt_file << "1" << std::endl;
    srt_file << "00:00:00,000 --> " << convertTime(clip->getDuration()) << std::endl;
    srt_file << subtitle.getText() << std::endl;
    srt_file.close();
    
    // Create a temporary output file
    fs::path temp_output = fs::temp_directory_path() / (generateRandomString() + ".mp4");
    temp_files.push_back(temp_output);
    
    // Get the clip's file path
    auto clip_path = fs::temp_directory_path() / (generateRandomString() + ".mp4");
    temp_files.push_back(clip_path);
    clip->writeVideofile(clip_path.string());
    
    // Use FFmpeg to add the subtitle
    std::string command = "ffmpeg -y -i \"" + clip_path.string() + "\" -vf \"subtitles=" + 
                         temp_srt.string() + ":force_style='FontSize=24,PrimaryColour=&HFFFFFF,BackColour=&H80000000,BorderStyle=4'\" " +
                         "-c:v libx264 -preset ultrafast -c:a copy \"" + temp_output.string() + "\"";
    
    std::cout << "Running command: " << command << std::endl;
    
    int result = system(command.c_str());
    if (result != 0) {
        std::cerr << "Error adding subtitles. Command returned: " << result << std::endl;
        return clip;
    }
    
    return std::make_shared<VideoClip>(temp_output.string());
}

std::string VideoProcessor::addStaticWatermark(const std::string& video_path, const std::string& watermark_path) {
    // Create a temporary output file
    fs::path temp_output = fs::temp_directory_path() / (generateRandomString() + ".mp4");
    temp_files.push_back(temp_output);
    
    // Use FFmpeg to add the watermark
    std::string command = "ffmpeg -y -i \"" + video_path + "\" -i \"" + watermark_path + 
                         "\" -filter_complex \"[1:v]scale=iw*0.3:-1[watermark];[0:v][watermark]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2:format=auto,format=yuv420p\" " +
                         "-c:v libx264 -preset ultrafast -c:a copy \"" + temp_output.string() + "\"";
    
    std::cout << "Running command: " << command << std::endl;
    
    int result = system(command.c_str());
    if (result != 0) {
        std::cerr << "Error adding watermark. Command returned: " << result << std::endl;
        return "";
    }
    
    // Upload the watermarked video to S3
    std::string timestamp = std::to_string(std::chrono::system_clock::now().time_since_epoch().count() / 1000000000);
    std::string s3_key = timestamp + "_watermarked.mp4";
    
    if (uploadToS3(temp_output.string(), s3_key)) {
        return s3_key;
    } else {
        return "";
    }
}

std::shared_ptr<VideoClip> VideoProcessor::speedUpVideoWithAudio(std::shared_ptr<VideoClip> input_video, double speed_factor) {
    if (speed_factor <= 0) {
        throw std::invalid_argument("Speed factor must be positive");
    }
    
    if (speed_factor == 1.0) {
        return input_video;
    }
    
    // Create temporary files
    fs::path temp_input = fs::temp_directory_path() / (generateRandomString() + ".mp4");
    fs::path temp_output = fs::temp_directory_path() / (generateRandomString() + ".mp4");
    temp_files.push_back(temp_input);
    temp_files.push_back(temp_output);
    
    // Write the input video to a temporary file
    input_video->writeVideofile(temp_input.string());
    
    // Use FFmpeg to speed up the video
    std::string command = "ffmpeg -y -i \"" + temp_input.string() + "\" -filter_complex " +
                         "\"[0:v]setpts=" + std::to_string(1.0/speed_factor) + "*PTS[v];" +
                         "[0:a]atempo=" + std::to_string(speed_factor) + "[a]\" " +
                         "-map \"[v]\" -map \"[a]\" -c:v libx264 -preset ultrafast -c:a aac \"" + 
                         temp_output.string() + "\"";
    
    std::cout << "Running command: " << command << std::endl;
    
    int result = system(command.c_str());
    if (result != 0) {
        std::cerr << "Error speeding up video. Command returned: " << result << std::endl;
        return input_video;
    }
    
    return std::make_shared<VideoClip>(temp_output.string());
}

std::string VideoProcessor::saveFinalVideo(std::shared_ptr<VideoClip> clip, const std::string& output_path) {
    // Write the video to the output path
    clip->writeVideofile(output_path, "libx264", "ultrafast", "aac", 30);
    
    // Upload the video to S3
    std::string timestamp = std::to_string(std::chrono::system_clock::now().time_since_epoch().count() / 1000000000);
    std::string s3_key = timestamp + "_final.mp4";
    
    if (uploadToS3(output_path, s3_key)) {
        return s3_key;
    } else {
        return "";
    }
}

double VideoProcessor::subripTimeToSeconds(const SubtitleItem& time) {
    return time.getStartTime();
}

std::string VideoProcessor::convertTime(double seconds) {
    int milliseconds = static_cast<int>((seconds - static_cast<int>(seconds)) * 1000);
    int total_seconds = static_cast<int>(seconds);
    int minutes = (total_seconds / 60) % 60;
    int hours = total_seconds / 3600;
    int secs = total_seconds % 60;
    
    std::stringstream ss;
    ss << std::setfill('0') << std::setw(2) << hours << ":"
       << std::setfill('0') << std::setw(2) << minutes << ":"
       << std::setfill('0') << std::setw(2) << secs << ","
       << std::setfill('0') << std::setw(3) << milliseconds;
    
    return ss.str();
}

double VideoProcessor::srtTimeToFloat(const std::string& srt_time) {
    std::regex time_pattern("(\\d+):(\\d+):(\\d+),(\\d+)");
    std::smatch matches;
    
    if (std::regex_match(srt_time, matches, time_pattern)) {
        int hours = std::stoi(matches[1]);
        int minutes = std::stoi(matches[2]);
        int seconds = std::stoi(matches[3]);
        int milliseconds = std::stoi(matches[4]);
        
        return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000.0;
    }
    
    throw std::invalid_argument("Invalid SRT time format: " + srt_time);
}

std::string VideoProcessor::generateRandomString(int length) {
    const std::string chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
    std::random_device rd;
    std::mt19937 generator(rd());
    std::uniform_int_distribution<> distribution(0, chars.size() - 1);
    
    std::string result;
    result.reserve(length);
    
    for (int i = 0; i < length; ++i) {
        result += chars[distribution(generator)];
    }
    
    return result;
}

std::vector<std::pair<std::string, std::string>> VideoProcessor::extractStartEnd(const std::string& generated_srt) {
    std::vector<std::pair<std::string, std::string>> time_data;
    
    // Process the SRT file
    std::vector<SubtitleInfo> aligned_output = processSrtFile(generated_srt);
    
    for (const auto& entry : aligned_output) {
        std::string start = convertTime(entry.start_time);
        std::string end = convertTime(entry.end_time);
        time_data.push_back({start, end});
    }
    
    return time_data;
}

// VideoClip implementation
VideoClip::VideoClip(const std::string& file_path) : file_path(file_path), duration(0), size({0, 0}), fps(30),
                                                   format_context(nullptr), video_stream_index(-1) {
    // Open the video file
    format_context = avformat_alloc_context();
    if (!format_context) {
        throw std::runtime_error("Failed to allocate format context");
    }
    
    if (avformat_open_input(&format_context, file_path.c_str(), nullptr, nullptr) < 0) {
        avformat_free_context(format_context);
        throw std::runtime_error("Failed to open input file: " + file_path);
    }
    
    if (avformat_find_stream_info(format_context, nullptr) < 0) {
        avformat_close_input(&format_context);
        throw std::runtime_error("Failed to find stream info");
    }
    
    // Find the video stream
    for (unsigned int i = 0; i < format_context->nb_streams; ++i) {
        if (format_context->streams[i]->codecpar->codec_type == AVMEDIA_TYPE_VIDEO) {
            video_stream_index = i;
            break;
        }
    }
    
    if (video_stream_index == -1) {
        avformat_close_input(&format_context);
        throw std::runtime_error("No video stream found");
    }
    
    // Get video properties
    AVStream* video_stream = format_context->streams[video_stream_index];
    size.first = video_stream->codecpar->width;
    size.second = video_stream->codecpar->height;
    
    // Calculate duration
    if (video_stream->duration != AV_NOPTS_VALUE) {
        duration = video_stream->duration * av_q2d(video_stream->time_base);
    } else if (format_context->duration != AV_NOPTS_VALUE) {
        duration = format_context->duration / (double)AV_TIME_BASE;
    }
    
    // Get frame rate
    if (video_stream->avg_frame_rate.num != 0 && video_stream->avg_frame_rate.den != 0) {
        fps = av_q2d(video_stream->avg_frame_rate);
    }
    
    // Check for audio stream and create audio clip if found
    for (unsigned int i = 0; i < format_context->nb_streams; ++i) {
        if (format_context->streams[i]->codecpar->codec_type == AVMEDIA_TYPE_AUDIO) {
            audio = std::make_shared<AudioClip>(file_path);
            break;
        }
    }
}

VideoClip::~VideoClip() {
    if (format_context) {
        avformat_close_input(&format_context);
    }
}

double VideoClip::getDuration() const {
    return duration;
}

void VideoClip::setDuration(double new_duration) {
    duration = new_duration;
}

std::pair<int, int> VideoClip::getSize() const {
    return size;
}

std::shared_ptr<AudioClip> VideoClip::getAudio() const {  const {
    return size;
}

std::shared_ptr<AudioClip> VideoClip::getAudio() const {
    return audio;
}

void VideoClip::setAudio(std::shared_ptr<AudioClip> new_audio) {
    audio = new_audio;
}

std::shared_ptr<VideoClip> VideoClip::subclip(double start, double end) const {
    if (start < 0 || end > duration || start >= end) {
        throw std::invalid_argument("Invalid subclip range");
    }
    
    // Create a temporary file for the subclip
    std::string temp_file = std::filesystem::temp_directory_path().string() + "/" + 
                           std::to_string(std::chrono::system_clock::now().time_since_epoch().count()) + ".mp4";
    
    // Use FFmpeg to extract the subclip
    std::string command = "ffmpeg -y -i \"" + file_path + "\" -ss " + std::to_string(start) + 
                         " -to " + std::to_string(end) + " -c:v libx264 -c:a aac \"" + temp_file + "\"";
    
    int result = system(command.c_str());
    if (result != 0) {
        throw std::runtime_error("Failed to create subclip");
    }
    
    return std::make_shared<VideoClip>(temp_file);
}

std::shared_ptr<VideoClip> VideoClip::resize(const std::pair<int, int>& newsize) const {
    // Create a temporary file for the resized clip
    std::string temp_file = std::filesystem::temp_directory_path().string() + "/" + 
                           std::to_string(std::chrono::system_clock::now().time_since_epoch().count()) + ".mp4";
    
    // Use FFmpeg to resize the clip
    std::string command = "ffmpeg -y -i \"" + file_path + "\" -vf \"scale=" + 
                         std::to_string(newsize.first) + ":" + std::to_string(newsize.second) + 
                         "\" -c:v libx264 -c:a copy \"" + temp_file + "\"";
    
    int result = system(command.c_str());
    if (result != 0) {
        throw std::runtime_error("Failed to resize clip");
    }
    
    return std::make_shared<VideoClip>(temp_file);
}

std::shared_ptr<VideoClip> VideoClip::crop(int x1, int y1, int x2, int y2) const {
    int width = x2 - x1;
    int height = y2 - y1;
    
    if (width <= 0 || height <= 0) {
        throw std::invalid_argument("Invalid crop dimensions");
    }
    
    // Create a temporary file for the cropped clip
    std::string temp_file = std::filesystem::temp_directory_path().string() + "/" + 
                           std::to_string(std::chrono::system_clock::now().time_since_epoch().count()) + ".mp4";
    
    // Use FFmpeg to crop the clip
    std::string command = "ffmpeg -y -i \"" + file_path + "\" -vf \"crop=" + 
                         std::to_string(width) + ":" + std::to_string(height) + ":" + 
                         std::to_string(x1) + ":" + std::to_string(y1) + 
                         "\" -c:v libx264 -c:a copy \"" + temp_file + "\"";
    
    int result = system(command.c_str());
    if (result != 0) {
        throw std::runtime_error("Failed to crop clip");
    }
    
    return std::make_shared<VideoClip>(temp_file);
}

std::shared_ptr<VideoClip> VideoClip::speedx(double factor) const {
    if (factor <= 0) {
        throw std::invalid_argument("Speed factor must be positive");
    }
    
    // Create a temporary file for the speed-adjusted clip
    std::string temp_file = std::filesystem::temp_directory_path().string() + "/" + 
                           std::to_string(std::chrono::system_clock::now().time_since_epoch().count()) + ".mp4";
    
    // Use FFmpeg to adjust the speed
    std::string command = "ffmpeg -y -i \"" + file_path + "\" -filter_complex " +
                         "\"[0:v]setpts=" + std::to_string(1.0/factor) + "*PTS[v];" +
                         "[0:a]atempo=" + std::to_string(factor) + "[a]\" " +
                         "-map \"[v]\" -map \"[a]\" -c:v libx264 -c:a aac \"" + temp_file + "\"";
    
    int result = system(command.c_str());
    if (result != 0) {
        throw std::runtime_error("Failed to adjust clip speed");
    }
    
    return std::make_shared<VideoClip>(temp_file);
}

std::shared_ptr<VideoClip> VideoClip::withoutAudio() const {
    // Create a temporary file for the clip without audio
    std::string temp_file = std::filesystem::temp_directory_path().string() + "/" + 
                           std::to_string(std::chrono::system_clock::now().time_since_epoch().count()) + ".mp4";
    
    // Use FFmpeg to remove the audio
    std::string command = "ffmpeg -y -i \"" + file_path + "\" -c:v copy -an \"" + temp_file + "\"";
    
    int result = system(command.c_str());
    if (result != 0) {
        throw std::runtime_error("Failed to remove audio from clip");
    }
    
    return std::make_shared<VideoClip>(temp_file);
}

void VideoClip::writeVideofile(const std::string& filename, const std::string& codec, 
                             const std::string& preset, const std::string& audio_codec, int fps) {
    // Use FFmpeg to write the video file
    std::string command = "ffmpeg -y -i \"" + file_path + "\" -c:v " + codec + 
                         " -preset " + preset + " -c:a " + audio_codec + 
                         " -r " + std::to_string(fps) + " \"" + filename + "\"";
    
    int result = system(command.c_str());
    if (result != 0) {
        throw std::runtime_error("Failed to write video file");
    }
}

int VideoClip::getFps() const {
    return fps;
}

void VideoClip::setFps(int new_fps) {
    fps = new_fps;
}

AVFormatContext* VideoClip::getFormatContext() const {
    return format_context;
}

int VideoClip::getVideoStreamIndex() const {
    return video_stream_index;
}

// AudioClip implementation
AudioClip::AudioClip(const std::string& file_path) : file_path(file_path), duration(0),
                                                   format_context(nullptr), audio_stream_index(-1) {
    // Open the audio file
    format_context = avformat_alloc_context();
    if (!format_context) {
        throw std::runtime_error("Failed to allocate format context");
    }
    
    if (avformat_open_input(&format_context, file_path.c_str(), nullptr, nullptr) < 0) {
        avformat_free_context(format_context);
        throw std::runtime_error("Failed to open input file: " + file_path);
    }
    
    if (avformat_find_stream_info(format_context, nullptr) < 0) {
        avformat_close_input(&format_context);
        throw std::runtime_error("Failed to find stream info");
    }
    
    // Find the audio stream
    for (unsigned int i = 0; i < format_context->nb_streams; ++i) {
        if (format_context->streams[i]->codecpar->codec_type == AVMEDIA_TYPE_AUDIO) {
            audio_stream_index = i;
            break;
        }
    }
    
    if (audio_stream_index == -1) {
        avformat_close_input(&format_context);
        throw std::runtime_error("No audio stream found");
    }
    
    // Calculate duration
    AVStream* audio_stream = format_context->streams[audio_stream_index];
    if (audio_stream->duration != AV_NOPTS_VALUE) {
        duration = audio_stream->duration * av_q2d(audio_stream->time_base);
    } else if (format_context->duration != AV_NOPTS_VALUE) {
        duration = format_context->duration / (double)AV_TIME_BASE;
    }
}

AudioClip::~AudioClip() {
    if (format_context) {
        avformat_close_input(&format_context);
    }
}

double AudioClip::getDuration() const {
    return duration;
}

void AudioClip::setDuration(double new_duration) {
    duration = new_duration;
}

std::shared_ptr<AudioClip> AudioClip::subclip(double start, double end) const {
    if (start < 0 || end > duration || start >= end) {
        throw std::invalid_argument("Invalid subclip range");
    }
    
    // Create a temporary file for the subclip
    std::string temp_file = std::filesystem::temp_directory_path().string() + "/" + 
                           std::to_string(std::chrono::system_clock::now().time_since_epoch().count()) + ".mp3";
    
    // Use FFmpeg to extract the subclip
    std::string command = "ffmpeg -y -i \"" + file_path + "\" -ss " + std::to_string(start) + 
                         " -to " + std::to_string(end) + " -c:a aac \"" + temp_file + "\"";
    
    int result = system(command.c_str());
    if (result != 0) {
        throw std::runtime_error("Failed to create audio subclip");
    }
    
    return std::make_shared<AudioClip>(temp_file);
}

AVFormatContext* AudioClip::getFormatContext() const {
    return format_context;
}

int AudioClip::getAudioStreamIndex() const {
    return audio_stream_index;
}

// ImageClip implementation
ImageClip::ImageClip(const std::string& file_path) : file_path(file_path), duration(0) {
    // Use OpenCV to get image dimensions
    cv::Mat image = cv::imread(file_path);
    if (image.empty()) {
        throw std::runtime_error("Failed to load image: " + file_path);
    }
    
    size.first = image.cols;
    size.second = image.rows;
}

ImageClip::~ImageClip() {
    // Nothing to clean up
}

double ImageClip::getDuration() const {
    return duration;
}

void ImageClip::setDuration(double new_duration) {
    duration = new_duration;
}

std::pair<int, int> ImageClip::getSize() const {
    return size;
}

std::shared_ptr<VideoClip> ImageClip::setDurationAsVideo(double new_duration) const {
    if (new_duration <= 0) {
        throw std::invalid_argument("Duration must be positive");
    }
    
    // Create a temporary file for the video
    std::string temp_file = std::filesystem::temp_directory_path().string() + "/" + 
                           std::to_string(std::chrono::system_clock::now().time_since_epoch().count()) + ".mp4";
    
    // Use FFmpeg to convert the image to a video
    std::string command = "ffmpeg -y -loop 1 -i \"" + file_path + "\" -c:v libx264 -t " + 
                         std::to_string(new_duration) + " -pix_fmt yuv420p \"" + temp_file + "\"";
    
    int result = system(command.c_str());
    if (result != 0) {
        throw std::runtime_error("Failed to convert image to video");
    }
    
    return std::make_shared<VideoClip>(temp_file);
}

std::shared_ptr<ImageClip> ImageClip::resize(const std::pair<int, int>& newsize) const {
    // Create a temporary file for the resized image
    std::string temp_file = std::filesystem::temp_directory_path().string() + "/" + 
                           std::to_string(std::chrono::system_clock::now().time_since_epoch().count()) + ".png";
    
    // Use OpenCV to resize the image
    cv::Mat image = cv::imread(file_path);
    cv::Mat resized;
    cv::resize(image, resized, cv::Size(newsize.first, newsize.second));
    cv::imwrite(temp_file, resized);
    
    return std::make_shared<ImageClip>(temp_file);
}

// SubtitleItem implementation
SubtitleItem::SubtitleItem(int index, double start_time, double end_time, const std::string& text)
    : index(index), start_time(start_time), end_time(end_time), text(text) {
}

int SubtitleItem::getIndex() const {
    return index;
}

double SubtitleItem::getStartTime() const {
    return start_time;
}

double SubtitleItem::getEndTime() const {
    return end_time;
}

std::string SubtitleItem::getText() const {
    return text;
}
