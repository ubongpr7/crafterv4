#pragma once

#include <string>
#include <vector>
#include <map>
#include <memory>
#include <functional>
#include <chrono>
#include <optional>
#include <filesystem>
#include <unordered_map>

// FFmpeg libraries
extern "C" {
#include <libavcodec/avcodec.h>
#include <libavformat/avformat.h>
#include <libavutil/avutil.h>
#include <libavutil/imgutils.h>
#include <libswscale/swscale.h>
#include <libavfilter/avfilter.h>
#include <libavfilter/buffersink.h>
#include <libavfilter/buffersrc.h>
#include <libavutil/opt.h>
#include <libavutil/pixdesc.h>
}

// AWS SDK
#include <aws/core/Aws.h>
#include <aws/s3/S3Client.h>
#include <aws/s3/model/GetObjectRequest.h>
#include <aws/s3/model/PutObjectRequest.h>

namespace fs = std::filesystem;

// Forward declarations
class VideoClip;
class AudioClip;
class ImageClip;
class SubtitleItem;

// Resolution map similar to Python's RESOLUTIONS
struct Resolution {
    int width;
    int height;
};

// Aspect ratio map similar to Python's MAINRESOLUTIONS
struct AspectRatio {
    double ratio;
};

// Struct to hold subtitle information
struct SubtitleInfo {
    int index;
    double start_time;
    double end_time;
    std::string text;
};

// Class to handle video processing operations
class VideoProcessor {
public:
    VideoProcessor();
    ~VideoProcessor();

    // Initialize AWS SDK and S3 client
    bool initialize(const std::string& aws_access_key, const std::string& aws_secret_key, const std::string& bucket_name);

    // Text to speech conversion
    std::string convertTextToSpeech(const std::string& text_file_path, const std::string& voice_id, 
                                   const std::string& api_key, const std::string& output_audio_file);

    // SRT file generation
    std::string generateSrtFile(const std::string& audio_file_path, const std::string& text_file_path);
    std::string generateSubclipsSrtFile(const std::string& audio_file_path, const std::string& text_file_path);

    // Process SRT file
    std::vector<SubtitleInfo> processSrtFile(const std::string& srt_file_path);

    // Generate blank video with audio
    std::string generateBlankVideoWithAudio(const std::string& audio_file_path, const std::string& resolution_key, 
                                           double duration);

    // Load video from file
    std::shared_ptr<VideoClip> loadVideoFromFile(const std::string& file_path);

    // Load subtitles from file
    std::vector<SubtitleItem> loadSubtitlesFromFile(const std::string& file_path);

    // Get video segments using SRT
    std::pair<std::vector<std::shared_ptr<VideoClip>>, std::vector<SubtitleItem>> 
    getSegmentsUsingSrt(std::shared_ptr<VideoClip> video, const std::vector<SubtitleItem>& subtitles);

    // Adjust segment duration
    std::shared_ptr<VideoClip> adjustSegmentDuration(std::shared_ptr<VideoClip> segment, double duration, bool strict = true);

    // Get video paths for text file
    std::vector<std::string> getVideoPathsForTextFile(int text_file_id);

    // Crop video to aspect ratio
    std::shared_ptr<VideoClip> cropToAspectRatio(std::shared_ptr<VideoClip> clip, double desired_aspect_ratio);

    // Crop video with ffmpeg
    std::shared_ptr<VideoClip> cropVideoWithFfmpeg(const std::string& input_video, const Resolution& output_resolution, 
                                                 std::shared_ptr<VideoClip> clip, bool is_tiktok);

    // Concatenate clips
    std::shared_ptr<VideoClip> concatenateClips(const std::vector<std::shared_ptr<VideoClip>>& clips, 
                                              const std::optional<Resolution>& target_resolution = std::nullopt, 
                                              int target_fps = 30);

    // Resize clips to max size
    std::vector<std::shared_ptr<VideoClip>> resizeClipsToMaxSize(const std::vector<std::shared_ptr<VideoClip>>& clips);

    // Replace video segments
    std::vector<std::shared_ptr<VideoClip>> replaceVideoSegments(
        const std::vector<std::shared_ptr<VideoClip>>& original_segments,
        const std::vector<std::shared_ptr<VideoClip>>& replacement_videos,
        const std::vector<SubtitleItem>& subtitles,
        std::shared_ptr<VideoClip> original_video);

    // Add subtitles to clip
    std::shared_ptr<VideoClip> addSubtitlesToClip(std::shared_ptr<VideoClip> clip, const SubtitleItem& subtitle);

    // Add static watermark
    std::string addStaticWatermark(const std::string& video_path, const std::string& watermark_path);

    // Speed up video with audio
    std::shared_ptr<VideoClip> speedUpVideoWithAudio(std::shared_ptr<VideoClip> input_video, double speed_factor);

    // Save final video
    std::string saveFinalVideo(std::shared_ptr<VideoClip> clip, const std::string& output_path);

    // S3 operations
    std::vector<uint8_t> downloadFromS3(const std::string& file_key);
    bool uploadToS3(const std::string& file_path, const std::string& s3_key);

    // Utility functions
    double subripTimeToSeconds(const SubtitleItem& time);
    std::string convertTime(double seconds);
    double srtTimeToFloat(const std::string& srt_time);
    std::string generateRandomString(int length = 10);
    std::vector<std::pair<std::string, std::string>> extractStartEnd(const std::string& generated_srt);

private:
    // FFmpeg context management
    AVFormatContext* createFormatContext(const std::string& filename, bool is_output = false);
    AVCodecContext* createCodecContext(AVFormatContext* format_ctx, int stream_index, bool is_encoder = false);
    
    // Filter graph setup
    bool setupFilterGraph(AVFilterGraph** graph, AVFilterContext** src_ctx, AVFilterContext** sink_ctx,
                         AVCodecContext* dec_ctx, AVCodecContext* enc_ctx, const std::string& filter_desc);
    
    // Frame processing
    bool processFrames(AVFormatContext* in_fmt_ctx, AVFormatContext* out_fmt_ctx,
                      AVCodecContext* dec_ctx, AVCodecContext* enc_ctx,
                      AVFilterContext* buffersrc_ctx, AVFilterContext* buffersink_ctx,
                      int video_stream_idx);

    // Create rounded rectangle for subtitles
    std::vector<uint8_t> createRoundedRectangle(const std::pair<int, int>& size, int radius, 
                                              const std::string& bg_color = "#ffffff", int upscale_factor = 20);

    // AWS SDK members
    Aws::SDKOptions aws_options;
    std::shared_ptr<Aws::S3::S3Client> s3_client;
    std::string bucket_name;

    // Resolution and aspect ratio maps
    std::unordered_map<std::string, Resolution> resolutions;
    std::unordered_map<std::string, double> aspect_ratios;

    // Font paths
    std::unordered_map<std::string, std::string> fonts;

    // Temporary file management
    std::vector<fs::path> temp_files;
    
    // Progress tracking callback
    std::function<void(int)> progress_callback;
};

// Clip classes for video manipulation
class Clip {
public:
    virtual ~Clip() = default;
    virtual double getDuration() const = 0;
    virtual void setDuration(double duration) = 0;
    virtual std::pair<int, int> getSize() const = 0;
};

class VideoClip : public Clip {
public:
    VideoClip(const std::string& file_path);
    ~VideoClip();

    double getDuration() const override;
    void setDuration(double duration) override;
    std::pair<int, int> getSize() const override;
    
    std::shared_ptr<AudioClip> getAudio() const;
    void setAudio(std::shared_ptr<AudioClip> audio);
    
    std::shared_ptr<VideoClip> subclip(double start, double end) const;
    std::shared_ptr<VideoClip> resize(const std::pair<int, int>& newsize) const;
    std::shared_ptr<VideoClip> crop(int x1, int y1, int x2, int y2) const;
    std::shared_ptr<VideoClip> speedx(double factor) const;
    std::shared_ptr<VideoClip> withoutAudio() const;
    
    void writeVideofile(const std::string& filename, const std::string& codec = "libx264",
                       const std::string& preset = "medium", const std::string& audio_codec = "aac",
                       int fps = 30);

    int getFps() const;
    void setFps(int fps);
    
    AVFormatContext* getFormatContext() const;
    int getVideoStreamIndex() const;

private:
    std::string file_path;
    double duration;
    std::pair<int, int> size;
    int fps;
    std::shared_ptr<AudioClip> audio;
    
    AVFormatContext* format_context;
    int video_stream_index;
};

class AudioClip : public Clip {
public:
    AudioClip(const std::string& file_path);
    ~AudioClip();

    double getDuration() const override;
    void setDuration(double duration) override;
    std::pair<int, int> getSize() const override { return {0, 0}; }
    
    std::shared_ptr<AudioClip> subclip(double start, double end) const;
    
    AVFormatContext* getFormatContext() const;
    int getAudioStreamIndex() const;

private:
    std::string file_path;
    double duration;
    
    AVFormatContext* format_context;
    int audio_stream_index;
};

class ImageClip : public Clip {
public:
    ImageClip(const std::string& file_path);
    ~ImageClip();

    double getDuration() const override;
    void setDuration(double duration) override;
    std::pair<int, int> getSize() const override;
    
    std::shared_ptr<VideoClip> setDurationAsVideo(double duration) const;
    std::shared_ptr<ImageClip> resize(const std::pair<int, int>& newsize) const;
    
private:
    std::string file_path;
    double duration;
    std::pair<int, int> size;
};

class SubtitleItem {
public:
    SubtitleItem(int index, double start_time, double end_time, const std::string& text);
    
    int getIndex() const;
    double getStartTime() const;
    double getEndTime() const;
    std::string getText() const;
    
private:
    int index;
    double start_time;
    double end_time;
    std::string text;
};
