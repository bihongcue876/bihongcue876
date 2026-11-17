#!/usr/bin/env bash
# 定时刷新主页热力图：取数 → 重绘 SVG / README 区块 / 交互页 → 只有变了才提交并推送。
#
# 数据来源：GitHub CLI（`gh auth login` 过一次就行，脚本自己从 gh 取 token）。
# 统计口径：只数 commit 次数，不碰仓库名、议题、合并请求的标题。
#
# 用法：
#   scripts/update.sh              # 正常跑（有变化就 commit & push）
#   DRY_RUN=1 scripts/update.sh    # 只重绘 + 看 diff，不 commit / 不 push
#   scripts/update.sh --no-push    # 同上（--dry 的别名，给 refresh.cmd 用）
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG="$REPO/.heatmap.log"
LOCK="/tmp/heatmap-refresh.lock"
LOGIN="${HEATMAP_LOGIN:-bihongcue876}"
TARGETS=(assets README.md docs/heatmap/index.html)

case "${1:-}" in
  --dry|--no-push) DRY_RUN=1 ;;
esac

cd "$REPO"

# 同一时间只允许一个实例（WSL cron 与 Windows 任务重复触发时也一样）
exec 9>"$LOCK"
if ! flock -n 9; then
  echo "$(date -Is) 已在运行，跳过" >>"$LOG"
  exit 0
fi

log() { echo "$(date -Is) $*" >>"$LOG"; }
log "--- start ($REPO)"

# gh 不在非交互 PATH 里的情况兜底
export PATH="/usr/local/bin:/usr/bin:/bin:$HOME/.local/bin"

if ! gh auth token >/dev/null 2>&1; then
  log "!! gh 还没登录（跑一次 gh auth login）"; exit 1
fi

# git 在 /mnt/d 上容易误报 filemode 变更
GIT="git -c core.fileMode=false"

# 1) README 用的图（近一年 / 按年 / 按月）+ 就地重写 README 的 <!-- HEATMAP --> 区块
if ! python3 scripts/build_readme.py --login "$LOGIN" --gh native >>"$LOG" 2>&1; then
  log "!! README 图渲染失败，见下方输出"; exit 1
fi

# 2) 可交互的年度页面（单文件、数据内联）
python3 scripts/build_site.py --login "$LOGIN" --gh native \
  --json-out assets/heatmap-data.json >>"$LOG" 2>&1 || log "!! 交互页生成失败（不影响 SVG）"

# 3) 有变化才提交
changed() { $GIT status --porcelain -- "${TARGETS[@]}" | grep -q . ; }
if ! changed; then
  log "无变化，结束"; exit 0
fi

if [ "${DRY_RUN:-0}" = "1" ]; then
  log "DRY_RUN：有变化但不提交"
  $GIT --no-pager diff --stat -- "${TARGETS[@]}" >>"$LOG" 2>&1 || true
  exit 0
fi

# 4) 提交 + 推送（失败也不会卡住下一次运行）
$GIT add "${TARGETS[@]}"
$GIT -c user.name="heatmap-bot" \
     -c user.email="heatmap-bot@users.noreply.github.com" \
     commit -q -m "更新热力图（$(date +%F)）" || true
$GIT pull --rebase --autostash -q >>"$LOG" 2>&1 || log "pull 失败，继续尝试 push"
if $GIT push -q >>"$LOG" 2>&1; then
  log "已推送 $(git log -1 --pretty=%h)"
else
  log "!! push 失败（检查 gh auth setup-git / 权限）"
  exit 1
fi

# 日志留最近 400 行
if [ -f "$LOG" ] && [ "$(wc -l <"$LOG")" -gt 400 ]; then
  tail -n 400 "$LOG" >"$LOG.tmp" && mv "$LOG.tmp" "$LOG"
fi
