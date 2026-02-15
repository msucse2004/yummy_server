# DB 백업 스크립트 (Windows) - Task Scheduler로 주기 실행 권장
$BackupDir = if ($env:BACKUP_DIR) { $env:BACKUP_DIR } else { ".\backups" }
$Password = if ($env:POSTGRES_PASSWORD) { $env:POSTGRES_PASSWORD } else { "yummy_secret" }
New-Item -ItemType Directory -Force -Path $BackupDir
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$env:PGPASSWORD = $Password
pg_dump -h localhost -U yummy -d yummy -F c -f "$BackupDir\yummy_$Timestamp.dump"
Write-Host "Backup saved: $BackupDir\yummy_$Timestamp.dump"
