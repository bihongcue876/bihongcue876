#!/usr/bin/env python3
"""重新生成 README 里的「活动」区块（纯标准库）。

产出：
  assets/heatmap-light.svg / -dark.svg          最近 53 周（主页主图，点进去是交互版）
  assets/years/year-<Y>-light.svg / -dark.svg   按自然年
  assets/months/<Y>-<MM>.svg                    当年每月一张（README 里悬停可看次数）
然后就地改写 README.md 中 <!-- HEATMAP:START --> 与 <!-- HEATMAP:END --> 之间的内容。

为什么长这样：github.com 会 sanitize README 里的 HTML（实测：<iframe>/<svg>/<style>/
<script>/onclick 全部被剥掉，<details>/<img title>/<a>/<picture> 保留），所以
「在 README 里跑 JS」不可能，能做的是「图片点开 → 交互页」+「悬停 img 看 title」。

用法：
  python3 scripts/build_readme.py --login <你>     # token 自动从 gh CLI 取
  DRY_RUN=1 ./scripts/update.sh   # 日常更新走这个
"""
import argparse
import datetime as dt
import importlib.util
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def _load_heatmap():
    spec = importlib.util.spec_from_file_location("heatmap", os.path.join(HERE, "heatmap.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


hm = _load_heatmap()

START_MARK = "<!-- HEATMAP:START -->"
END_MARK = "<!-- HEATMAP:END -->"

MONTH_CN = ["1月", "2月", "3月", "4月", "5月", "6月",
            "7月", "8月", "9月", "10月", "11月", "12月"]


def repo_slug():
    try:
        url = subprocess.check_output(["git", "-C", ROOT, "remote", "get-url", "origin"],
                                      text=True).strip()
    except Exception:
        return ""
    m = re.search(r"github\.com[:/]+([^/]+)/([^/.]+)", url)
    return "%s/%s" % (m.group(1), m.group(2)) if m else ""


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def summarize(counts):
    days = [v for v in counts.values() if v]
    return sum(days), len(days)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--login", default=None)
    ap.add_argument("--token-env", default="GH_TOKEN")
    ap.add_argument("--gh", default="auto", choices=["auto", "native", "wsl", "off"])
    ap.add_argument("--readme", default=os.path.join(ROOT, "README.md"))
    ap.add_argument("--years", type=int, default=3, help="生成几个自然年（含今年）")
    ap.add_argument("--end", default=None, help="默认今天")
    ap.add_argument("--lang", default="zh")
    ap.add_argument("--accent", default=None)
    ap.add_argument("--style", default="square")
    ap.add_argument("--months", action="store_true", default=True)
    ap.add_argument("--no-months", dest="months", action="store_false")
    ap.add_argument("--check", action="store_true", help="只校验 README 里的区块，不改写")
    args = ap.parse_args(argv)

    today = dt.date.fromisoformat(args.end) if args.end else dt.date.today()

    if args.check:
        cur = open(args.readme, encoding="utf-8").read()
        print("markers:", cur.count(START_MARK), cur.count(END_MARK))
        return 0

    token = hm.resolve_token(os.environ.get(args.token_env, ""), args.gh)
    login = args.login or hm.guess_login(os.getcwd())
    # 交互页就在仓库里；想让它变成可点的网页，开一次 GitHub Pages（main + /docs）就行，
    # 开了以后把下面改成 "https://<你>.github.io/<仓库>/heatmap/"。
    page = "./docs/heatmap/index.html"
    open_link = ""

    # ---------- 主图：最近 53 周 ----------
    start = today - dt.timedelta(days=364)
    counts, _ = hm.collect_github(login, token, start, today, commits_only=True)
    total, active = summarize(counts)
    for theme in ("light", "dark"):
        svg, _, _ = hm.render(counts, start, today, theme, args.lang,
                              "%d 次提交 · 近一年" % total, args.style, args.accent)
        write(os.path.join(ROOT, "assets", "heatmap-%s.svg" % theme), svg)

    # ---------- 按自然年 ----------
    year_blocks = []
    for y in range(today.year, today.year - args.years, -1):
        ys = dt.date(y, 1, 1)
        ye = min(dt.date(y, 12, 31), today)
        yc, _ = (hm.collect_github(login, token, ys, ye, commits_only=True)
                 if token else ({}, 0))
        ytotal, yactive = summarize(yc)
        if not ytotal and y != today.year:
            continue
        for theme in ("light", "dark"):
            svg, _, _ = hm.render(yc, ys, ye, theme, args.lang,
                                  "%d 年 · %d 次提交 / %d 天" % (y, ytotal, yactive),
                                  args.style, args.accent)
            write(os.path.join(ROOT, "assets", "years", "year-%d-%s.svg" % (y, theme)), svg)
        year_blocks.append(
            '  <p align="center"><picture>\n'
            '      <source media="(prefers-color-scheme: dark)" srcset="./assets/years/year-%d-dark.svg">\n'
            '      <img src="./assets/years/year-%d-light.svg" alt="%d 年 · %d 次提交" width="700">\n'
            '    </picture></p>' % (y, y, y, ytotal))

    # ---------- 今年每月：README 里悬停 img 的 title 就能看到次数 ----------
    month_blocks = []
    if args.months:
        y = today.year
        yc, _ = (hm.collect_github(login, token, dt.date(y, 1, 1), today, commits_only=True)
                 if token else ({}, 0))
        for m in range(1, today.month + 1):
            ms = dt.date(y, m, 1)
            me = (dt.date(y + (m == 12), (m % 12) + 1, 1) - dt.timedelta(days=1))
            me = min(me, today)
            mc = {k: v for k, v in yc.items() if k[:7] == "%d-%02d" % (y, m)}
            mtotal = sum(mc.values())
            svg, _, _ = hm.render(mc, ms, me, "light", args.lang,
                                  "%s %d 次" % (MONTH_CN[m - 1], mtotal), args.style, args.accent)
            write(os.path.join(ROOT, "assets", "months", "%d-%02d.svg" % (y, m)), svg)
            month_blocks.append(
                '<img src="./assets/months/%d-%02d.svg" alt="%s %d 次" title="%s · %d 次提交" width="104">'
                % (y, m, MONTH_CN[m - 1], mtotal, MONTH_CN[m - 1], mtotal))
        rows = ["    " + " ".join(month_blocks[i:i + 6]) for i in range(0, len(month_blocks), 6)]

    # ---------- 拼 README 区块 ----------
    parts = [
        START_MARK,
        '<h4 align="center">- 活动 -</h4>',
        "",
        '<div align="center">',
        "  <picture>",
        '    <source media="(prefers-color-scheme: dark)" srcset="./assets/heatmap-dark.svg">',
        '    <img src="./assets/heatmap-light.svg" alt="近一年提交热力图" width="700">',
        "  </picture>",
        "</div>",
        "",
        '<p align="center"><sub>近一年 %d 次提交 · %d 天有提交 · 只统计次数，'
        '不显示仓库名、议题与合并请求的标题</sub></p>' % (total, active),
    ]
    if year_blocks:
        parts += ["", "<details>", "<summary><sub>按年份看（点开）</sub></summary>", ""]
        parts += year_blocks
        parts += ["", "</details>"]
    if month_blocks:
        parts += ["", "<details>",
                  "<summary><sub>%d 年每月（鼠标悬停每张小图看次数）</sub></summary>" % today.year, "",
                  '<p align="center">']
        for i, row in enumerate(rows):
            parts.append(row + ("<br>" if i < len(rows) - 1 else ""))
        parts += ["</p>", "", "</details>"]
    parts += ["", END_MARK]
    block = "\n".join(parts)

    cur = open(args.readme, encoding="utf-8").read() if os.path.exists(args.readme) else ""
    if START_MARK in cur and END_MARK in cur:
        pre, rest = cur.split(START_MARK, 1)
        _, post = rest.split(END_MARK, 1)
        new = pre + block + post
    else:
        new = cur.rstrip() + "\n\n" + block + "\n"

    if new != cur:
        write(args.readme, new)
        print("README 已更新（%d 次提交 / %d 天）" % (total, active))
    else:
        print("README 无变化")
    return 0


if __name__ == "__main__":
    sys.exit(main())
