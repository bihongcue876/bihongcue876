@echo off
rem 打开 github.io 站点里的交互式热力图页面（本地文件预览）
setlocal
if "%HEATMAP_SITE_REPO%"=="" set "HEATMAP_SITE_REPO=D:\Projects\主页设计\bihongcue876.github.io"
if not exist "%HEATMAP_SITE_REPO%\index.html" (
  echo [!] 没找到 %HEATMAP_SITE_REPO%\index.html
  echo     先把站点仓库拉下来，或者先跑一次 refresh.cmd
  pause
  exit /b 1
)
start "" "%HEATMAP_SITE_REPO%\index.html"
