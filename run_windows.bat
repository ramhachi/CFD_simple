@echo off
setlocal
cd /d "%~dp0"

echo ==================================================
echo FSAE CFD System Initialization (Windows)
echo ==================================================
echo.
echo Building Docker Image (This may take a few minutes...)
docker build -t fsae-cfd .

echo.
echo Running CFD System inside Docker...
docker run -it --rm -v "%cd%":/data -e IN_DOCKER=1 fsae-cfd bash -lc "cd /data && python3 run_cfd.py"
pause
