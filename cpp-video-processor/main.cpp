#include "video_processor.h"
#include <iostream>
#include <string>
#include <vector>
#include <filesystem>
#include <chrono>
#include <thread>

namespace fs = std::filesystem;

void printUsage() {
    std::cout << "Usage: video_processor <command> [options]" << std::endl;
    std::cout << "Commands:" << std::endl;
    std::cout << "  process <text_file_id> <resolution> <voice_id> <api_key>" << std::endl;
    std::cout << "  trim <input_file> <output_file> <start_time> <end_time>" << std::endl;
    std::cout << "  resize <input_file> <output_file> <width> <height>" << std::endl;
    std::cout << "  rotate <input_file> <output_file> <angle>" << std::endl;
    std::cout << "  concatenate <output_file> <input_file1> <input_file2> ..." << std::endl;
    std::cout << "  addaudio <video_file> <audio_file> <output_file>" << std::endl;
}

void trackProgress(int progress) {
    std::cout << "Progress: " << progress << "%" << std::endl;
}

int main(int argc, char* argv[]) {
    if (argc < 2) {
        printUsage();
        return 1;
    }

    std::string command = argv[1];
    VideoProcessor processor;

    // Initialize AWS credentials from environment variables
    const char* aws_access_key = std::getenv("AWS_ACCESS_KEY_ID");
    const char* aws_secret_key = std::getenv("AWS_SECRET_ACCESS_KEY");
    const char* bucket_name = std::getenv("AWS_STORAGE_BUCKET_NAME");

    if (!aws_access_key || !aws_secret_key || !bucket_name) {
        std::cerr << "AWS credentials or bucket name not set in environment variables" << std::endl;
        return 1;
    }

    // Initialize the processor
    if (!processor.initialize(aws_access_key, aws_secret_key, bucket_name)) {
        std::cerr << "Failed to initialize video processor" << std::endl;
        return 1;
    }

    try {
        if (command == "process" && argc >= 6) {
            int text_file_id = std::stoi(argv[2]);
            std::string resolution = argv[3];
            std::string voice_id = argv[4];
            std::string api_key = argv[5];

            std::cout << "Processing text file ID: " << text_file_id << std::endl;
            std::cout << "Resolution: " << resolution << std::endl;
            std::cout << "Voice ID: " << voice_id << std::endl;

            // Track progress at 2%
            trackProgress(2);

            // 1. Download text file from S3
            std::string text_file_key = "text_files/" + std::to_string(text_file_id) + ".txt";
            auto text_content = processor.downloadFromS3(text_file_key);
            
            if (text_content.empty()) {
                std::cerr << "Failed to download text file" << std::endl;
                return 1;
            }

            // Save text content to a temporary file
            fs::path temp_text = fs::temp_directory_path() / (std::to_string(text_file_id) + ".txt");
            std::ofstream text_file(temp_text.string(), std::ios::binary);
            text_file.write(reinterpret_cast<const char*>(text_content.data()), text_content.size());
            text_file.close();

            // 2. Convert text to speech
            trackProgress(5);
            fs::path temp_audio = fs::temp_directory_path() / (std::to_string(text_file_id) + "_audio.mp3");
            std::string audio_s3_key = processor.convertTextToSpeech(temp_text.string(), voice_id, api_key, temp_audio.string());
            
            if (audio_s3_key.empty()) {
                std::cerr << "Failed to convert text to speech" << std::endl;
                return 1;
            }

            trackProgress(10);
            std::cout << "Audio file generated: " << audio_s3_key << std::endl;

            // 3. Generate SRT file
            trackProgress(15);
            std::string srt_s3_key = processor.generateSrtFile(temp_audio.string(), temp_text.string());
            
            if (srt_s3_key.empty()) {
                std::cerr << "Failed to generate SRT file" << std::endl;
                return 1;
            }

            trackProgress(25);
            std::cout << "SRT file generated: " << srt_s3_key << std::endl;

            // 4. Generate subclips SRT file
            std::string subclips_text_file_key = "subclips_text_files/" + std::to_string(text_file_id) + ".txt";
            auto subclips_text_content = processor.downloadFromS3(subclips_text_file_key);
            
            if (!subclips_text_content.empty()) {
                fs::path temp_subclips_text = fs::temp_directory_path() / (std::to_string(text_file_id) + "_subclips.txt");
                std::ofstream subclips_text_file(temp_subclips_text.string(), std::ios::binary);
                subclips_text_file.write(reinterpret_cast<const char*>(subclips_text_content.data()), subclips_text_content.size());
                subclips_text_file.close();

                std::string subclips_srt_s3_key = processor.generateSubclipsSrtFile(temp_audio.string(), temp_subclips_text.string());
                std::cout << "Subclips SRT file generated: " << subclips_srt_s3_key << std::endl;
            }

            // 5. Download the SRT file and process it
            auto srt_content = processor.downloadFromS3(srt_s3_key);
            fs::path temp_srt = fs::temp_directory_path() / (std::to_string(text_file_id) + "_srt.json");
            std::ofstream srt_file(temp_srt.string(), std::ios::binary);
            srt_file.write(reinterpret_cast<const char*>(srt_content.data()), srt_content.size());
            srt_file.close();

            auto subtitles_info = processor.processSrtFile(temp_srt.string());
            trackProgress(27);

            // 6. Generate blank video with audio
            double audio_duration = 0;
            for (const auto& subtitle : subtitles_info) {
                audio_duration = std::max(audio_duration, subtitle.end_time);
            }

            std::string blank_video_s3_key = processor.generateBlankVideoWithAudio(
                temp_audio.string(), resolution, audio_duration);
            
            if (blank_video_s3_key.empty()) {
                std::cerr << "Failed to generate blank video" << std::endl;
                return 1;
            }

            trackProgress(29);
            std::cout << "Blank video generated: " << blank_video_s3_key << std::endl;

            // 7. Download the blank video
            auto blank_video_content = processor.downloadFromS3(blank_video_s3_key);
            fs::path temp_blank_video = fs::temp_directory_path() / (std::to_string(text_file_id) + "_blank.mp4");
            std::ofstream blank_video_file(temp_blank_video.string(), std::ios::binary);
            blank_video_file.write(reinterpret_cast<const char*>(blank_video_content.data()), blank_video_content.size());
            blank_video_file.close();

            // 8. Load the blank video and subtitles
            auto blank_video_clip = processor.loadVideoFromFile(temp_blank_video.string());
            auto subtitles = processor.loadSubtitlesFromFile(temp_srt.string());
            trackProgress(32);

            // 9. Get video segments using SRT
            auto [blank_video_segments, subtitle_segments] = processor.getSegmentsUsingSrt(blank_video_clip, subtitles);
            trackProgress(36);

            // 10. Adjust segment durations
            std::vector<std::shared_ptr<VideoClip>> output_video_segments;
            double start = 0;
            
            for (size_t i = 0; i < blank_video_segments.size(); ++i) {
                double end = subtitle_segments[i].getEndTime();
                double required_duration = end - start;
                
                auto new_video_segment = processor.adjustSegmentDuration(
                    blank_video_segments[i], required_duration);
                
                output_video_segments.push_back(new_video_segment->withoutAudio());
                start = end;
            }
            
            trackProgress(39);

            // 11. Get replacement video files
            std::vector<std::string> replacement_video_files = processor.getVideoPathsForTextFile(text_file_id);
            trackProgress(40);

            // 12. Load replacement videos
            std::vector<std::shared_ptr<VideoClip>> replacement_video_clips;
            for (const auto& video_file : replacement_video_files) {
                auto clip = processor.loadVideoFromFile(video_file);
                clip->setFps(30);
                replacement_video_clips.push_back(clip);
            }
            
            // 13. Resize replacement videos
            replacement_video_clips = processor.resizeClipsToMaxSize(replacement_video_clips);
            trackProgress(48);

            // 14. Concatenate blank video segments
            auto final_blank_video = processor.concatenateClips(blank_video_segments);
            trackProgress(50);

            // 15. Replace video segments
            replacement_video_clips = processor.resizeClipsToMaxSize(replacement_video_clips);
            auto final_video_segments = processor.replaceVideoSegments(
                output_video_segments, replacement_video_clips, subtitles, blank_video_clip);
            
            // 16. Resize final video segments
            auto final_resized_clips = processor.resizeClipsToMaxSize(final_video_segments);
            
            // 17. Concatenate final video
            auto concatenated_video = processor.concatenateClips(final_resized_clips);
            
            // 18. Set audio from blank video
            auto original_audio = blank_video_clip->getAudio()->subclip(
                0, std::min(concatenated_video->getDuration(), blank_video_clip->getAudio()->getDuration()));
            
            concatenated_video->setAudio(original_audio);
            
            // 19. Speed up video
            auto final_video_speeded_up = processor.speedUpVideoWithAudio(concatenated_video, 1.0);
            
            // 20. Save final video
            fs::path temp_final_video = fs::temp_directory_path() / (std::to_string(text_file_id) + "_final.mp4");
            std::string final_video_s3_key = processor.saveFinalVideo(final_video_speeded_up, temp_final_video.string());
            trackProgress(75);
            
            // 21. Add watermark
            std::string watermark_s3_key = "logos/watermark.png";
            auto watermark_content = processor.downloadFromS3(watermark_s3_key);
            
            if (!watermark_content.empty()) {
                fs::path temp_watermark = fs::temp_directory_path() / "watermark.png";
                std::ofstream watermark_file(temp_watermark.string(), std::ios::binary);
                watermark_file.write(reinterpret_cast<const char*>(watermark_content.data()), watermark_content.size());
                watermark_file.close();
                
                std::string watermarked_video_s3_key = processor.addStaticWatermark(
                    temp_final_video.string(), temp_watermark.string());
                
                trackProgress(99);
                std::cout << "Watermarked video generated: " << watermarked_video_s3_key << std::endl;
            }
            
            trackProgress(100);
            std::cout << "Processing complete for text file ID: " << text_file_id << std::endl;
            return 0;
        }
        else if (command == "trim" && argc == 6) {
            std::string input_file = argv[2];
            std::string output_file = argv[3];
            double start_time = std::stod(argv[4]);
            double end_time = std::stod(argv[5]);
            
            std::cout << "Trimming video from " << start_time << "s to " << end_time << "s..." << std::endl;
            
            auto input_clip = processor.loadVideoFromFile(input_file);
            auto trimmed_clip = input_clip->subclip(start_time, end_time);
            trimmed_clip->writeVideofile(output_file);
            
            std::cout << "Successfully trimmed video to " << output_file << std::endl;
            return 0;
        }
        else if (command == "resize" && argc == 6) {
            std::string input_file = argv[2];
            std::string output_file = argv[3];
            int width = std::stoi(argv[4]);
            int height = std::stoi(argv[5]);
            
            std::cout << "Resizing video to " << width << "x" << height << "..." << std::endl;
            
            auto input_clip = processor.loadVideoFromFile(input_file);
            auto resized_clip = input_clip->resize({width, height});
            resized_clip->writeVideofile(output_file);
            
            std::cout << "Successfully resized video to " << output_file << std::endl;
            return 0;
        }
        else if (command == "concatenate" && argc >= 4) {
            std::string output_file = argv[2];
            std::vector<std::shared_ptr<VideoClip>> clips;
            
            for (int i = 3; i < argc; i++) {
                clips.push_back(processor.loadVideoFromFile(argv[i]));
            }
            
            std::cout << "Concatenating " << clips.size() << " videos..." << std::endl;
            
            auto concatenated_clip = processor.concatenateClips(clips);
            concatenated_clip->writeVideofile(output_file);
            
            std::cout << "Successfully concatenated videos to " << output_file << std::endl;
            return 0;
        }
        else if (command == "addaudio" && argc == 5) {
            std::string video_file = argv[2];
            std::string audio_file = argv[3];
            std::string output_file = argv[4];
            
            std::cout << "Adding audio to video..." << std::endl;
            
            // Use FFmpeg to add audio to video
            std::string command = "ffmpeg -y -i \"" + video_file + "\" -i \"" + audio_file + 
                                 "\" -c:v copy -c:a aac -map 0:v:0 -map 1:a:0 \"" + output_file + "\"";
            
            int result = system(command.c_str());
            if (result != 0) {
                std::cerr << "Error adding audio to video. Command returned: " << result << std::endl;
                return 1;
            }
            
            std::cout << "Successfully added audio to video at " << output_file << std::endl;
            return 0;
        }
        else {
            printUsage();
            return 1;
        }
    }
    catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }

    std::cerr << "Operation failed" << std::endl;
    return 1;
}
