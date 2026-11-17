# 热力图：想要绿格子，不想暴露内容

本页记录 2026-11-17 的排查结论和可选方案。核心结论：**绿格子本身只是"某天几笔"的计数，
不含标题、仓库名、commit message**；你现在的问题不是"格子泄露内容"，而是**格子根本是空的**。
所以先把数据源解决掉，隐私边界靠"只统计计数 + 只统计 commit"来守住。

---

## 一、体检结果（2026-11-17）

| 检查项 | 结果 |
| --- | --- |
| `github.com/users/bihongcue876/contributions` | 367 个格子全部 `data-level="0"`，页面文字 **"0 contributions in the last year"** |
| `ghchart.rshah.org/2f81f7/bihongcue876` | 返回 200，但 367 个 `<rect>` 全是 `#EEEEEE`（空） |
| 对照实验：`torvalds` 同接口 | 4,025 contributions，格子有 4 级色阶 → 抓取方式没问题 |
| 私有仓库 `bihongcue876/bihongcue876` | 公开仓库、非 fork、`main` 为默认分支 |
| 该仓库提交 | `d94363a 2026-11-17`、`f3a8c5c 2026-11-10`，API 里 `author.login = bihongcue876` |

**即：今天有提交、作者也对得上你，但公开日历仍然记 0。**
这不是 ghchart 坏了（它只是忠实地画了一张空日历），也不是 README 里那段 HTML 写错了。

### 2026-11-17 实测：三项排除 + 一项确认

用 WSL 里已登录的 `gh`（`repo` scope，能读私有贡献）走 GraphQL `contributionsCollection`：

| 事实 | 数值 |
| --- | --- |
| **本人视角**日历总数 | **903**（100 天有活动） |
| 其中 commit | 826（30 个仓库：10 私有 / 20 公开） |
| 其中 PR | 46 · issue 2 · 新建仓库 25 · review 0 |
| `restrictedContributionsCount` | 0 |
| 三个提交邮箱 | `1581672842@qq.com`(primary) / `66735326+bihongcue876@users.noreply.github.com` / `wuyh_0706@126.com` **全部 verified** |
| `/users/<login>/events/public` | 有当天 PushEvent、IssuesEvent |

→ **邮箱不是原因（全 verified）、fork/分支不是原因（公开仓库 main 分支有提交）、活动不是原因（公开仓库一年 600+ 提交）**。
公开日历仍然是 0，说明是**账号层面的公开贡献展示异常**（GitHub 侧）。
这一项你自己能做的只有两个动作：翻一下 *Include private contributions* 开关再看；仍为 0 就带着上面这张表找 Support。

**但本方案不需要修它**：脚本用认证视角（`gh auth token`）取数，"你自己看得见的 903"就等于"格子里能画的 903"。

#### 那到底什么算一个绿格子

| 计入 | 不计入 |
| --- | --- |
| 默认分支上的 commit | 非默认分支（fork 里的、feature 分支上没合并的） |
| 开 issue / 提 PR / review | fork 里别人的 issue/PR（除非你参与了讨论） |
| 新建仓库 | 提了但被删的仓库 |
| 用**账号内已验证邮箱**提交 | 用未验证邮箱、或用别人名字提交 |

### 两个最可能的原因（按概率排序）

1. **提交邮箱没有在账号里"验证"**
   Settings → Emails，看 `66735326+bihongcue876@users.noreply.github.com` / `1581672842@qq.com` 是不是 **Verified**。
   GitHub 的贡献图只为"已加入账号的邮箱"计数，光是 API 能把提交认到你头上并不够。
   修好之后历史提交会自动回溯补绿。

2. **私有贡献没打开**
   Settings → Public profile → Contribution settings → 勾上 *Include private contributions on my profile*。
   这个开关只影响"私有仓库里的贡献算不算进格子"，**不会公开私有仓库名、也不公开 commit 内容**，
   只会多出"N contributions in private repositories"这一行聚合数字。

3. **账号被判定为 spam / limited**
   这种情况下公开日历会整体归零，但仓库照样可见——与你现在的现象完全吻合。
   自证：`gh api /users/bihongcue876` 看 `plan`、再看 Dashboard 有没有黄色提示；确认无误后找 Support。

> 说明：GitHub 没有"隐藏整个贡献图"的开关，`0 contributions` 只会由"公开活动为空"造成。
> 顺带一提，即使关掉上面第 2 项，你**公开**仓库的提交也照样会显示——所以第 1 项更可疑。

### 另一个坑：删不掉的记录

issue / PR 的**计数**会留在当天的格子里，删掉 issue 也不会回落。
但格子里永远只有数字；会露馅的是 profile 下方那段 *Contribution activity* 时间线（会写标题）。
本方案用一条规则同时解决两件事：**只数 commit**（`--source local` 天然如此），
issue / PR / review 一律不进统计。

---

## 二、可选方案对比

| 方案 | 需要什么 | 会暴露什么 | 你的情况能用吗 |
| --- | --- | --- | --- |
| `ghchart.rshah.org`（现在用的） | 公开日历非空 | 只有格子 | ❌ 日历是 0，画出来必然空白 |
| [lowlighter/metrics](https://github.com/lowlighter/metrics) `plugin_isocalendar` | PAT + Actions | 只有格子；插件可自由开关 | ⚠️ 能跑，但数据仍取自 GitHub 日历（受上面两个开关限制） |
| [yoshi389111/github-profile-3d-contrib](https://github.com/yoshi389111/github-profile-3d-contrib) | PAT + Actions | 3D 柱子，只有计数 | ⚠️ 同上，还要先在本地生成 `.github-profile-3d-contrib/` |
| [Platane/snk](https://github.com/Platane/snk) | Actions | 贪吃蛇啃格子 | ⚠️ 需要已有日历 SVG；日历空 → 蛇没得吃 |
| [DenverCoder1/github-readme-streak-stats](https://github.com/DenverCoder1/github-readme-streak-stats) | 公开数据 | 连续天数，不是格子 | ❌ 同样吃日历 |
| [greens](https://github.com/yuvrajangadsingh/greens)（你 `D:/Projects/greens`） | gh CLI + jq + Git Bash | 把私有仓库的**时间戳**镜像到另一个仓库 | ⚠️ 见下文 |
| **本仓库 `scripts/heatmap.py`** | Python 3（无三方依赖） | **只有 `date,count`** | ✅ 不依赖 GitHub 日历，本机历史也能出图 |

### 为什么 `greens` 在你机器上"没用"

- 它一次都没跑起来：`~/.contrib-mirror/` 不存在，`D:/Projects/commits-record` 是个**零提交的空仓库**（`git log` 报 `does not have any commits yet`）。
- 依赖链没装：需要 `gh`（本机没有）、`jq`、Git Bash；Windows 支持仍是 beta。
- 更关键的是**它解决的不是你的问题**：greens 把各仓库的提交时间戳重写成 `greens <你的邮箱>` 推到 **private** 镜像仓库里
  （`sync.sh:200` 明确警告镜像若是 public 就会泄露你的**工作仓库名**，所以它坚持 private）。
  私有镜像里的贡献要显示，还是得打开"Include private contributions"；而且它同样要求提交邮箱已验证。
  也就是说：**greens 是"补日历"的工具，不是"画 SVG"的工具**，对 README 里那张图没有直接帮助。

---

## 三、本仓库的实现

```
scripts/heatmap.py                 生成器（纯标准库）
assets/heatmap-light.svg           浅色版
assets/heatmap-dark.svg            深色版
```

### 数据源 A：本机 git 历史（默认，推荐）

```bash
python scripts/heatmap.py --roots D:/Projects \
  --email 66735326+bihongcue876@users.noreply.github.com --email 1581672842@qq.com
```

- 只数 `commit`，跨仓库按 sha 去重（clone/fork 不会翻倍）
- 只输出 `date → count`，不写仓库名、不写 message
- 结果完全由你掌握，GitHub 日历空不空都无所谓

先跑 `--summary` 看一眼命中的作者邮箱（`*` 表示计入），确认没有把别人的提交算进来：

```bash
python scripts/heatmap.py --roots D:/Projects --summary
```

### 数据源 B：GitHub 日历（自动化用）

```bash
set HEATMAP_TOKEN=<你的 PAT>          # 需要 read:user（私有贡献还要 repo 权限）
python scripts/heatmap.py --source github --token-env HEATMAP_TOKEN
```

（取到 0 时脚本会跳过覆盖，避免把已有的图冲成空白。）

### 可用参数

| 参数 | 作用 |
| --- | --- |
| `--weeks 53` | 显示多少周 |
| `--end 2026-12-31` | 截止日期 |
| `--lang zh\|en` | 月份标签语言（`zh` = 1月…12月，`en` = Jan…Dec） |
| `--no-merges` | 排除 merge commit |
| `--out assets` | 输出目录 |
| `--commits-only` | github 模式：只数 commit，**排除 issue / PR / review**（隐私首选） |
| `--style` | 格子形状：`square` 圆角方块（默认）/ `dot` 圆点 / `flat` 直角方块 |
| `--accent` | 主色，如 `2f81f7`（蓝）、`a371f7`（紫）；默认 GitHub 绿 |
| `--summary` | 只打印统计，不写文件 |
| `--force` | GitHub 取到 0 也覆盖 |

### 隐私边界（写死在实现里）

1. SVG 里只有 `<rect x y fill>` 和 `date · N commits` 的 tooltip；
2. 不请求、不读取 commit message / 仓库名 / issue 标题；
3. 只统计 commit 时，issue / PR / review 完全不出现在数据里；
4. 若要"连 commit 数都不想给"，`--email` 留空只统计单一邮箱，或用 `--weeks 26` 缩短时间窗。

---

## 四、五种样式（同一份数据，改两个参数）

`--style`（形状）× `--accent`（主色）随便搭，实测 840 commits / 100 天时：

| # | 命令片段 | 观感 |
| --- | --- | --- |
| ① | （默认） | GitHub 经典圆角方块 + 官方绿，最不挑读者 |
| ② | `--style dot` | 圆点，像"热度地图"，比方块轻盈 |
| ③ | `--style flat` | 直角方块，密度感最强、最"技术" |
| ④ | `--accent 2f81f7` | 蓝色系，和 GitHub 链接色一致 |
| ⑤ | `--style dot --accent a371f7` | 紫色圆点，配合头像/主题色 |

换色只影响 5 级色阶（空 + 4 级），由 `palette(theme, accent)` 往白/往黑混出来，不用手填 5 个色号。

## 五、在 WSL 里跑（推荐做法）

```bash
scripts/update.sh            # 正常刷新（取数 → 出图 → 有变化才 commit & push）
DRY_RUN=1 scripts/update.sh  # 只看效果，不提交
```

- token 全部从 `gh auth login` 那次的 OAuth token 里取（含 `repo`，所以**私有仓库的提交也数得进去**），脚本自己去取，不写进文件、不进 shell 历史；
- Windows 侧没有 `gh` 也没关系：`--gh auto`（默认）会自动借 `wsl.exe` 里的 gh；
- 只读接口，不需要任何写权限；单次 GraphQL 约 1 点，一天跑一次毫无压力；
- `--commits-only` 遇到单仓库活跃天 >100 会自动把时间窗对半拆开重取（2026-07 起 GitHub 对单连接 `contributions` 有资源上限）。

## 六、年度交互页面（docs/heatmap/index.html）

`scripts/build_site.py` 把近三年的「逐日 commit 次数」内联进一张单文件 HTML，
不依赖任何库、不联网、不发请求——双击能开，丢到 GitHub Pages 也能开。

```bash
python3 scripts/build_site.py --login <用户名>        # token 自动从 gh 取
# 产物：docs/heatmap/index.html（约 27 KB）+ assets/heatmap-data.json（纯数据）
```

页面里有什么：

- **年份切换**（2024 / 2025 / 2026，键盘 ←/→ 也行），每年独立的色阶分档；
- **平面视图**：JS 生成的 SVG，GitHub 同款 53×7 布局，悬停看「日期 · 周几 · 次数」；
- **立体视图**：canvas 等距投影的柱子天际线，柱高 = log(提交数)，
  自绘顶面/左面/右面三级明暗，年份切换时高度做 easing 动画（`prefers-reduced-motion` 时跳过）；
- **年度统计**：总提交 / 活跃天 / 最长连续 / 最忙一天 / 活跃日均；
- 深浅色跟随系统，右上角 ◐ 可手动切（记在 localStorage）；
- **默认打开立体视图**（更像"天际线"），`?view=flat` 切回平面；
- 月度柱状条：12 个月各画一根，柱顶直接标数字（今年的"多少次"一眼可见）。

本地双开（都在 `scripts/` 里）：

| 文件 | 干什么 |
| --- | --- |
| `scripts\preview.cmd` | 双击 = 用默认浏览器打开 `docs/heatmap/index.html` |
| `scripts\refresh.cmd` | 双击 = 让 WSL 重算数据 + 重绘 + 有变化就 commit & push |
| `scripts\refresh.cmd --dry` | 只重绘、不提交（先看效果用这个） |

### Markdown 里能不能"内嵌"它

**实测过，不能。** 把下面这段丢给 GitHub 自己的渲染接口（`POST /markdown`，就是网页端用的那个
sanitizer）跑一遍，结果是：

| 写法 | GitHub 渲染后 |
| --- | --- |
| `<details>` / `<summary>` | ✅ 保留（能点开/收起） |
| `<img title="…">` | ✅ 保留，**鼠标悬停会显示 title** |
| `<a href>` / `<picture>` / `<sub>` / `<div align>` | ✅ 保留 |
| `<iframe>` | ❌ 变成纯文本 |
| `<svg>`、`<style>`、`<title>`、`<script>` | ❌ 全部剥掉 |
| `onclick="…"` / `onerror="…"` / `href="javascript:…"` | ❌ 属性被删除 |
| `style="…"` | ❌ 属性也被删除（`align` 之类保留） |

探针文件：`docs/heatmap/live.js`（放了绿色徽章 + 点月度小图换大图，脚本真跑起来就看得见），
README 底部有个临时测试块 A–F，在网页端验证完可以整段删掉。

所以「在 README 里跑一个 JS 窗口」是不可能的，能做到的是这两层，现在的 README 都用上了：

1. **图片点开 → 完整的交互页**（新标签页里是真正的 html+js，立体/平面、切年、悬停看每天次数）；
2. **纯 HTML 折叠**：`<details>` 里放按年份的图；再放 12 张小图，每张 `<img title="9月 · 291 次提交">`，
   鼠标悬停就能看到那个月的次数——这是 README 里唯一能"悬停出数字"的办法。

想让第 1 层变成**可点的网页**，只需要开一次 Pages（`main` + `/docs`，不用写配置）：

`Settings → Pages → Source: Deploy from a branch → main / docs` → 之后
`https://<用户>.github.io/<仓库>/heatmap/` 就是交互页（之前 404 是因为一直没启用）。
不想开 Pages 也没关系：本地双击 `scripts\preview.cmd` 就是同一个页面。

## 七、多久刷新一次 / 怎么自动刷新

### 频率建议

热力图只在"有新提交"时才真的变，但 **53 周滚动窗口每天会整体左移一列**，
所以哪怕当天没提交，图也会有 1 列位移 → 「每天跑一次」实际等于「每天一个 bot 提交」。

| 频率 | 适合谁 | 代价 |
| --- | --- | --- |
| **每天 23:30（默认）** | 想要"当天就看得到" | 每天 1 个 `chore(heatmap)` 提交 |
| 每天 12:30 + 23:30 | 常在午夜前后提交 | 每天最多 2 个 |
| 每周日 23:30 | 讨厌提交噪音 | 当天的格子最多滞后 6 天 |

GitHub 自己的日历（Pages 上的那块）也是每日一刷，所以"每天一次"就是它的节奏。

### 本机定时（Windows 任务计划 → 进 WSL 跑）

`scripts/update.sh` 是幂等的：取 token → 重绘 SVG → 重绘交互页 → **只有文件变了才 commit & push**。
手动触发就用 `scripts\refresh.cmd`（双击即可；加 `--dry` 只重绘不提交）。
日志写在仓库根的 `.heatmap.log`（已在 `.gitignore` 里），并用 `flock` 防止定时任务重叠。

已经装好（**默认停用**，确认没问题再开）：

```powershell
schtasks /query /tn HeatmapRefresh /v /fo list   # 看状态/上次结果
schtasks /change /tn HeatmapRefresh /enable      # 启用：每天 23:30
schtasks /change /tn HeatmapRefresh /disable     # 想停就停
schtasks /run    /tn HeatmapRefresh              # 立刻手动跑一次
```

任务动作是 `wsl.exe -d Debian -e bash -lc /home/<用户>/.local/bin/heatmap-refresh`
（那条 `~/.local/bin/heatmap-refresh` 里只有一句 `exec <仓库>/scripts/update.sh "$@"`，
把中文路径藏在 WSL 侧，让 Windows 的命令行保持纯 ASCII）。它按需唤醒 WSL，不要求 WSL 常驻。

> 也可以改用 WSL 内的 cron（`crontab -e` 加 `30 23 * * * ~/.local/bin/heatmap-refresh`），
> 但 WSL 不常驻时不触发，所以任务计划更省心；两者同时启用也不会打架（`flock` + 无变化不提交）。

> 云端 Actions 那套已经删掉（这个仓库只走本机 / WSL 定时，简单可控）。

## 八、还能怎么玩（等数据绿了再说）

- `--weeks 26` 做"半年版"，放进主页更紧凑；
- 用同一份 `counts` 顺手生成"年度总览"文字（脚本已有 `total / active days`）；
- 想要彩色/圆点/月历样式，只需改 `render()` 里的 `CELL/GAP/rx/调色板`，数据层不用动。
