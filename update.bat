@echo off
title Auto Push to GitHub - RPA Monitor
cd /d "D:\Dashboard\text"

echo [1/4] Checking unstaged files...
git add .

echo [2/4] Creating commit...
git commit -m "RPA Auto-update: %date% %time%"

echo [3/4] Pulling updates from GitHub (rebase)...
git pull --rebase origin main

echo [4/4] Pushing changes to GitHub...
git push origin main

echo.
echo =======================================
echo   Process Completed Successfully!
echo =======================================
echo.
pause