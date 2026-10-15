$folder = (Get-Item -Path ".").FullName
$watcher = New-Object System.IO.FileSystemWatcher
$watcher.Path = $folder
$watcher.Filter = "*.*"
$watcher.IncludeSubdirectories = $true
$watcher.EnableRaisingEvents = $true

Write-Host "Monitoring changes in: $folder" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop..." -ForegroundColor Yellow

$action = {
    $path = $Event.SourceEventArgs.FullPath
    $changeType = $Event.SourceEventArgs.ChangeType
    
    # ป้องกันไม่ให้จับโฟลเดอร์ Git หรือไฟล์สคริปต์
    if ($path -match "\\\.git\\" -or $path -match "autopush\.ps1") { return }

    Write-Host "[$changeType] File changed! Syncing to GitHub..." -ForegroundColor Cyan
    Start-Sleep -Seconds 2
    
    git add .
    git commit -m "Auto-sync: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    git push
    
    Write-Host "Done! Synced to GitHub." -ForegroundColor Green
}

Register-ObjectEvent $watcher "Changed" -Action $action
Register-ObjectEvent $watcher "Created" -Action $action

try {
    while ($true) { Start-Sleep -Seconds 1 }
}
finally {
    Unregister-Event -SourceIdentifier *
    $watcher.Dispose()
}
