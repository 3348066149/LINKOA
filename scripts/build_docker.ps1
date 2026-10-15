# 一键打包 LINKOA Docker 离线镜像
# 用法：在 PowerShell 里跑  ./scripts/build_docker.ps1
# 产物：docker/linkoa-latest.tar（离线服务器用 docker load -i 导入）

$ErrorActionPreference = "Stop"
$ROOT = Split-Path -Parent $PSScriptRoot
Set-Location $ROOT

Write-Host "==> [1/3] 构建镜像 linkoa:latest ..." -ForegroundColor Cyan
docker compose -f docker/docker-compose.yml build

Write-Host "==> [2/3] 导出离线 tar 包 ..." -ForegroundColor Cyan
$tarPath = Join-Path $ROOT "docker\linkoa-latest.tar"
if (Test-Path $tarPath) { Remove-Item $tarPath -Force }
docker save -o $tarPath linkoa:latest

# 顺便把服务器端启动脚本拷到 docker/ 目录，和 tar 包放一起方便整包传过去
Copy-Item (Join-Path $ROOT "scripts\server_start.sh") (Join-Path $ROOT "docker\server_start.sh") -Force

$size = (Get-Item $tarPath).Length
$sizeMB = [math]::Round($size / 1MB, 1)
$md5 = (Get-FileHash -Algorithm MD5 $tarPath).Hash.ToLower()

Write-Host ""
Write-Host "==> 完成" -ForegroundColor Green
Write-Host "  产物: $tarPath"
Write-Host "  大小: $sizeMB MB ($size bytes)"
Write-Host "  MD5 : $md5"
Write-Host ""
Write-Host "把 docker/ 目录下这两个文件一起传到服务器：" -ForegroundColor Yellow
Write-Host "  - linkoa-latest.tar"
Write-Host "  - server_start.sh"
Write-Host "然后在服务器上执行："
Write-Host "  chmod +x server_start.sh"
Write-Host "  ./server_start.sh"
