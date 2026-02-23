#!/bin/bash
echo "=================================================="
echo "FSAE CFD System Initialization (Mac/Linux)"
echo "=================================================="
echo ""
echo "Building Docker Image (This may take a few minutes)..."
export PATH=$PATH:/usr/local/bin:/opt/homebrew/bin:/Applications/Docker.app/Contents/Resources/bin
docker build -t fsae-cfd .

echo ""
echo "Running CFD System inside Docker..."
docker run -i --rm -v "$(pwd)":/data -e IN_DOCKER=1 fsae-cfd bash -c "cd /data && python3 run_cfd.py"
