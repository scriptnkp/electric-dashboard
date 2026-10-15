@echo off
title Auto Push to GitHub
cd /d "D:\Dashboard\text"

echo =======================================
echo   Checking and pushing files to GitHub
echo =======================================
echo.

git add .
git commit -m "Update files: %date% %time%"
git push origin main

echo.
echo =======================================
echo   Updated successfully!
echo =======================================
timeout /t 3