#!/bin/bash
set -e

# Create build directory
mkdir -p build
cd build

# Configure with CMake
cmake ..

# Build
make -j$(nproc)

# Install (optional)
# sudo make install

echo "Build completed successfully!"
