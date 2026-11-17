#!/usr/bin/env python3
"""生成可交互的年度热力图页面（单文件 HTML，数据内联，双击即可打开）。

用法：
  python3 scripts/build_site.py --login <用户名>      # token 自动从 gh CLI 取
  ... --years 2024 2025 2026 --out docs/heatmap/index.html

只取「commit 次数」：不请求仓库名、issue/PR 标题、提交信息。
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent


def load_heatmap():
    spec = importlib.util.spec_from_file_location("heatmap", HERE / "heatmap.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--login", required=True)
    ap.add_argument("--token-env", default="GH_TOKEN")
    ap.add_argument("--gh", default="auto", choices=["auto", "native", "wsl", "off"])
    ap.add_argument("--years", nargs="+", type=int, default=None,
                    help="要生成的年份，默认 今年 与前两年")
    ap.add_argument("--out", default=str(ROOT / "docs" / "heatmap" / "index.html"))
    ap.add_argument("--template", default=str(HERE / "site_template.html"))
    ap.add_argument("--json-out", default=None, help="另外存一份纯数据 JSON")
    args = ap.parse_args(argv)

    hm = load_heatmap()
    token = hm.resolve_token(os.environ.get(args.token_env, ""), args.gh)
    if not token:
        raise SystemExit("取不到 token：先 `gh auth login`，或设置 %s（gh auth token）" % args.token_env)

    today = dt.date.today()
    years = args.years or [today.year - 2, today.year - 1, today.year]

    data = {}
    for y in years:
        start = dt.date(y, 1, 1)
        end = min(dt.date(y, 12, 31), today)
        if start > end:
            print(f"[skip] {y} 还没开始", file=sys.stderr)
            continue
        counts, _ = hm.collect_github(args.login, token, start, end, commits_only=True)
        counts = {d: v for d, v in counts.items() if v > 0}
        data[str(y)] = counts
        print(f"[{y}] {sum(counts.values())} commits / {len(counts)} days", file=sys.stderr)

    payload = {
        "login": args.login,
        "generated": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "years": data,
    }

    tpl = pathlib.Path(args.template).read_text(encoding="utf-8")
    html = (tpl
            .replace("__DATA__", json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
            .replace("__LOGIN__", args.login)
            .replace("__GENERATED__", payload["generated"]))

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8", newline="\n")
    print(f"写入 {out} ({len(html) / 1024:.1f} KB)", file=sys.stderr)

    if args.json_out:
        pathlib.Path(args.json_out).write_text(
            json.dumps(payload, ensure_ascii=False, indent=0), encoding="utf-8", newline="\n")
        print(f"写入 {args.json_out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
