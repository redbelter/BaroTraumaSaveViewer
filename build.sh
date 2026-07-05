#!/bin/bash
# Build script for reverse-baro Windows executable
# Usage: bash build.sh

set -e

cd "$(dirname "$0")"

echo "Building reverse-baro..."
echo

.venv/Scripts/pyinstaller.exe --clean reverse-baro.spec

if [ $? -eq 0 ]; then
    echo
    echo "Build succeeded!"
    echo
    echo "Output: dist/reverse-baro/reverse-baro.exe"
    ls -lh dist/reverse-baro/reverse-baro.exe 2>/dev/null || echo "(file listing failed)"
else
    echo "Build FAILED"
    exit 1
fi
