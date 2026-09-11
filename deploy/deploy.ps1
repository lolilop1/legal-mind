<#
.SYNOPSIS
    Legal Mind — deploy to VPS.

.USAGE
    .\deploy\deploy.ps1
    .\deploy\deploy.ps1 -SkipTests
#>

param(
    [string]$Server = "root@201.24.49.121",
    [string]$RemoteDir = "/opt/legal_mind",
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupDir = "$RemoteDir.backup_$Timestamp"

Write-Host "=== Legal Mind deploy ===" -ForegroundColor Cyan
Write-Host "Server:  $Server"
Write-Host "Project: $ProjectRoot"
Write-Host ""

# --- Step 1. Tests ---
if (-not $SkipTests) {
    Write-Host "[1/6] Running offline tests..." -ForegroundColor Yellow
    & python "tests\run_all.py"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "TESTS FAILED. Deploy cancelled." -ForegroundColor Red
        exit 1
    }
    Write-Host "Tests passed" -ForegroundColor Green
} else {
    Write-Host "[1/6] Skipped tests (-SkipTests)" -ForegroundColor DarkGray
}

# --- Step 2. Backup ---
Write-Host ""
Write-Host "[2/6] Backing up remote..." -ForegroundColor Yellow
ssh $Server "cp -r $RemoteDir $BackupDir"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Backup failed" -ForegroundColor Red
    exit 1
}
Write-Host "Backup: $BackupDir" -ForegroundColor Green

# --- Step 3. Upload ---
Write-Host ""
Write-Host "[3/6] Uploading prod folders..." -ForegroundColor Yellow

$prodItems = @("core", "region", "modules", "web", "deploy")

foreach ($item in $prodItems) {
    Write-Host "  -> $item" -ForegroundColor Gray
    scp -r "$item" "$Server`:$RemoteDir/"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Upload $item failed" -ForegroundColor Red
        exit 1
    }
}
Write-Host "Uploaded" -ForegroundColor Green

# --- Step 4. Permissions and restart ---
Write-Host ""
Write-Host "[4/6] Fixing permissions and restarting..." -ForegroundColor Yellow

ssh $Server "if [ -f $BackupDir/web/cases.db ]; then cp $BackupDir/web/cases.db $RemoteDir/web/cases.db ; fi ; cd $RemoteDir ; chown -R legal:legal . ; chmod 600 web/.env ; chmod 755 core region modules web deploy ; chmod -R 755 web/static ; chmod 644 web/static/* ; cp deploy/legal-mind.service /etc/systemd/system/legal-mind.service ; cp deploy/nginx.conf /etc/nginx/sites-available/legal-mind ; systemctl daemon-reload ; systemctl restart legal-mind ; systemctl reload nginx ; sleep 3"

if ($LASTEXITCODE -ne 0) {
    Write-Host "Restart failed. Rolling back..." -ForegroundColor Red
    ssh $Server "rm -rf $RemoteDir ; mv $BackupDir $RemoteDir ; systemctl restart legal-mind"
    exit 1
}
Write-Host "Service restarted" -ForegroundColor Green

# --- Step 5. Health check ---
Write-Host ""
Write-Host "[5/6] Checking /health..." -ForegroundColor Yellow
Start-Sleep -Seconds 2

$health = ssh $Server "curl -s http://127.0.0.1:5000/health"
Write-Host "Response: $health" -ForegroundColor Gray

if ($health -notmatch '"status":"ok"') {
    Write-Host "Health check failed. Rolling back..." -ForegroundColor Red
    ssh $Server "rm -rf $RemoteDir ; mv $BackupDir $RemoteDir ; systemctl restart legal-mind"
    exit 1
}
Write-Host "Health check OK" -ForegroundColor Green

# --- Step 6. Done ---
Write-Host ""
Write-Host "[6/6] Done!" -ForegroundColor Green
Write-Host ""
Write-Host "Check:" -ForegroundColor Cyan
Write-Host "  - http://201.24.49.121/"
Write-Host "  - ssh $Server 'tail -20 $RemoteDir/logs/requests.log'"
Write-Host ""
Write-Host "Backup: $BackupDir" -ForegroundColor DarkGray
Write-Host "Manual rollback:" -ForegroundColor DarkGray
Write-Host "  ssh $Server `"rm -rf $RemoteDir ; mv $BackupDir $RemoteDir ; systemctl restart legal-mind`"" -ForegroundColor DarkGray