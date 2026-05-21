# deploy-local.ps1 - 本地一键部署脚本
# 用法: 修改下方 $SERVER 后，在项目根目录运行 .\deploy-local.ps1

$SERVER = "user@你的服务器IP"        # ← 改成你的
$REMOTE_PATH = "/opt/ai-report"

# Step 1: 本地跑测试
Write-Host ">>> 运行测试..." -ForegroundColor Cyan
python -m pytest tests/test_prompt_builder.py tests/test_edge_cases.py -q
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 测试未通过，停止部署" -ForegroundColor Red
    exit 1
}

# Step 2: Git 提交并推送
Write-Host ">>> Git push..." -ForegroundColor Cyan
git add .
$msg = Read-Host "提交信息 (直接回车用默认)"
if ([string]::IsNullOrEmpty($msg)) { $msg = "update: prompt & logic" }
git commit -m $msg
git push

# Step 3: 远程部署
Write-Host ">>> 远程部署..." -ForegroundColor Cyan
ssh $SERVER "${REMOTE_PATH}/deploy.sh"

Write-Host "`n✅ 部署完成！" -ForegroundColor Green
