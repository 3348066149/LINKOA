@echo off
chcp 65001 >nul
cd /d "%~dp0\.."

echo ==^> [1/3] 构建镜像 linkoa:latest ...
docker compose -f docker/docker-compose.yml build
if errorlevel 1 goto :err

echo.
echo ==^> [2/3] 导出离线 tar 包 ...
if exist "docker\linkoa-latest.tar" del /f /q "docker\linkoa-latest.tar"
docker save -o "docker\linkoa-latest.tar" linkoa:latest
if errorlevel 1 goto :err

copy /y "scripts\server_start.sh" "docker\server_start.sh" >nul

echo.
echo ==^> [3/3] 完成
for %%A in (docker\linkoa-latest.tar) do echo   产物: docker\linkoa-latest.tar  ^|  大小: %%~zA 字节
echo.
echo 把 docker\ 目录下这两个文件一起传到服务器：
echo   - linkoa-latest.tar
echo   - server_start.sh
echo.
echo 然后在服务器上执行：
echo   chmod +x server_start.sh
echo   ./server_start.sh
echo.
pause
exit /b 0

:err
echo.
echo ==^> 出错了，看上面日志
pause
exit /b 1
