cmake_minimum_required(VERSION 3.10)
project(VideoProcessor)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find required packages
find_package(PkgConfig REQUIRED)
find_package(OpenCV REQUIRED)
find_package(CURL REQUIRED)
find_package(Freetype REQUIRED)

# Find FFmpeg libraries
pkg_check_modules(FFMPEG REQUIRED IMPORTED_TARGET
    libavcodec
    libavformat
    libavutil
    libswscale
    libavfilter
)

# AWS SDK setup
set(AWS_SDK_DIR "/usr/local" CACHE PATH "AWS SDK installation directory")
set(AWS_LIBS aws-cpp-sdk-core aws-cpp-sdk-s3)

# Include directories
include_directories(
    ${FFMPEG_INCLUDE_DIRS}
    ${OpenCV_INCLUDE_DIRS}
    ${CURL_INCLUDE_DIRS}
    ${FREETYPE_INCLUDE_DIRS}
    ${AWS_SDK_DIR}/include
)

# Link directories
link_directories(
    ${AWS_SDK_DIR}/lib
)

# Add executable
add_executable(video_processor 
    main.cpp
    video_processor.cpp
)

# Link libraries
target_link_libraries(video_processor
    ${FFMPEG_LIBRARIES}
    ${OpenCV_LIBS}
    ${CURL_LIBRARIES}
    ${FREETYPE_LIBRARIES}
    ${AWS_LIBS}
    pthread
    dl
    z
)

# Add compiler flags
target_compile_options(video_processor PRIVATE ${FFMPEG_CFLAGS})

# Install target
install(TARGETS video_processor DESTINATION bin)
