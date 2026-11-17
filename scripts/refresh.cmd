@echo off
setlocal
rem Double-click: refresh heatmap + interactive page (WSL), then commit/push if changed.
rem "refresh.cmd --dry" = redraw only, no git commit.
if /i "%~1"=="--dry" (
  wsl.exe -d Debian -e bash -lc "DRY_RUN=1 ~/.local/bin/heatmap-refresh"
) else (
  wsl.exe -d Debian -e bash -lc "~/.local/bin/heatmap-refresh"
)
set RC=%ERRORLEVEL%
echo.
if "%RC%"=="0" (echo [OK] heatmap refreshed) else (echo [FAIL %RC%] see scripts\.heatmap.log)
pause
