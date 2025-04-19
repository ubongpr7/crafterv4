#!/bin/bash
set -e

# Update package lists
sudo apt-get update

# Install build tools
sudo apt-get install -y build-essential cmake pkg-config

# Install FFmpeg development libraries
sudo apt-get install -y libavcodec-dev libavformat-dev libavutil-dev libswscale-dev libavfilter-dev

# Install OpenCV
sudo apt-get install -y libopencv-dev

# Install CURL
sudo apt-get install -y libcurl4-openssl-dev

# Install FreeType for text rendering
sudo apt-get install -y libfreetype6-dev

# Install JSON library
sudo apt-get install -y nlohmann-json3-dev

# Install AWS SDK for C++
sudo apt-get install -y libssl-dev libcurl4-openssl-dev
git clone --recurse-submodules https://github.com/aws/aws-sdk-cpp.git
cd aws-sdk-cpp
mkdir build
cd build
cmake .. -DBUILD_ONLY="s3" -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)
sudo make install
cd ../..
rm -rf aws-sdk-cpp

echo "All dependencies installed successfully!"
