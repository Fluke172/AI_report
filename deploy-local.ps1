# deploy-local.ps1 - local one-click deploy script
# Usage:
#   $env:SERVER='root@your-server-ip'; .\deploy-local.ps1
#   powershell -ExecutionPolicy Bypass -File .\deploy-local.ps1 -ServerAddress root@your-server-ip
# Optional:
#   $env:COMMIT_MESSAGE='update: report fields'; .\deploy-local.ps1

param(
    [string]$ServerAddress = $env:SERVER,
    [string]$CommitMessage = $env:COMMIT_MESSAGE
)

$SERVER = $ServerAddress
if ([string]::IsNullOrEmpty($SERVER)) {
    $SERVER = "user@your-server-ip"
}

$REMOTE_PATH = "/opt/ai-report"
$BRANCH = "main"
$PYTHON = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $PYTHON)) {
    $PYTHON = "python"
}

if ($SERVER -eq "user@your-server-ip") {
    Write-Host "ERROR: Please set SERVER first. Example:" -ForegroundColor Red
    Write-Host "  `$env:SERVER='root@115.190.187.208'; .\deploy-local.ps1" -ForegroundColor Yellow
    exit 1
}

# Step 1: run local tests
Write-Host ">>> Running tests..." -ForegroundColor Cyan
& $PYTHON -m pytest tests/test_prompt_builder.py tests/test_edge_cases.py -q -s
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Tests failed. Deploy stopped." -ForegroundColor Red
    exit 1
}

# Step 2: commit and push tracked changes
Write-Host ">>> Preparing git push..." -ForegroundColor Cyan
git add -u

$msg = $CommitMessage
if ([string]::IsNullOrEmpty($msg)) {
    $msg = Read-Host "Commit message (press Enter for default)"
}
if ([string]::IsNullOrEmpty($msg)) {
    $msg = "update: prompt and logic"
}

git diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
    git commit -m $msg
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Git commit failed. Deploy stopped." -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host ">>> No tracked changes to commit" -ForegroundColor Yellow
}

git push origin $BRANCH
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Git push failed. Deploy stopped." -ForegroundColor Red
    exit 1
}

# Step 3: remote deploy
Write-Host ">>> Running remote deploy..." -ForegroundColor Cyan
ssh $SERVER "cd ${REMOTE_PATH} && ./deploy.sh"
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Remote deploy failed." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Deploy completed." -ForegroundColor Green
