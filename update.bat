@echo off
title Auto Push to GitHub
cd /d "D:\Dashboard\text"

echo =======================================
echo   Syncing and pushing to GitHub...
echo =======================================
echo.

git pull --rebase origin main
git add .
git commit -m "Update files: %date% %time%"
git push origin main

echo.
echo =======================================
echo   Updated successfully!
echo =======================================
timeout /t 3