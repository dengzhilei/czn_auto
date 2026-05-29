# CZN Auto

CZN Auto 是一个给《卡厄思梦境》相关重复流程用的 Windows 自动点击工具。它会看当前游戏画面，自动点进入、推进对白、识别三选一卡牌奖励，并在找到目标卡时停下来。

普通用户不需要安装 Python，也不用会写代码。下载发布版安装包，安装后从桌面图标或开始菜单正常启动即可。

## 这版更新

- 正常启动默认使用后台窗口点击，通常不占用日常鼠标。
- 识别和固定点击位置都会按游戏窗口客户区计算，窗口模式也可以尝试使用。
- 多屏/窗口模式下会默认按游戏窗口标题自动选择截图显示器。
- 副屏初始窗口会优先选择像游戏画面的 16:9 窗口；标题匹配失败时会用画面识别兜底找回游戏窗口。
- 点击后等待画面变化超时时，会按当前识别状态清理流程锁并重试，避免一直卡在“已点击一次，等待变化”。
- 清理多余启动脚本，普通用户只需要从桌面图标、开始菜单或 `start_czn_auto.bat` 正常启动。

## 新手快速开始

1. 打开最新版发布页：

   [https://github.com/dengzhilei/czn_auto/releases/latest](https://github.com/dengzhilei/czn_auto/releases/latest)

2. 下载 `CZNAutoSetup-0.1.5.exe`。

3. 双击安装，安装时保留桌面快捷方式。

4. 打开游戏，切到需要开始自动流程的界面(进入卡厄思，选难度界面)。

5. 启动桌面上的 `CZN Auto`。

6. Windows 弹出管理员权限提示时点允许。

7. 切回游戏全屏界面，工具会自动开始运行。

8. 需要停止时，按 `F8`、`Esc`、`Pause` 或 `End`。

首次使用建议先运行开始菜单里的 `CZN Auto One Click Test`，它只会测试一次点击，用来确认当前分辨率和点击位置是否正常。

## 下载哪个文件

一般只需要下载这个：

```text
CZNAutoSetup-0.1.5.exe
```

这是安装版，适合大多数用户。

如果你不想安装，也可以下载：

```text
CZNAuto-portable.zip
```

这是便携版，解压后运行 `start_czn_auto.bat`。

## 使用前注意

- 建议游戏使用全屏或无边框全屏。
- 建议先用默认配置跑一次，不要一开始就改配置。
- 正常启动默认使用后台窗口点击，通常不会移动或占用你的真实鼠标。
- 窗口模式也可以尝试使用；程序会按游戏窗口客户区计算固定点击位置。窗口不要被其他窗口遮住。
- 多屏用户默认不需要手动选屏；如果日志里显示 `runtime monitor: auto could not find target window`，请确认游戏窗口标题包含 `卡厄思梦境`。
- 程序运行时仍会自动操作游戏窗口，请确保当前画面就是你想自动操作的游戏画面。
- 找到目标卡后程序会自动停止。
- 如果运行不正常，请反馈日志文件和出问题时的截图。

日志位置：

```text
%LOCALAPPDATA%\CZN Auto\logs
```

最新的日志文件名一般长这样：

```text
czn_auto_20260527_234348_67688.log
```

## 能做什么

- 自动识别主页、配队页、对白/过场、三选一奖励、卡牌奖励、返回确认等界面。
- 自动从主页进入配队页，再从配队页进入后续流程。
- 自动推进对白。
- 自动识别三选一奖励里的目标选项。
- 自动识别卡牌奖励里的目标卡。
- 找到目标卡后自动停止。
- 没找到目标卡时，自动退出并进入下一轮。
- 每次运行都会生成日志，方便排查问题。

## 安装版使用

1. 下载并运行 `CZNAutoSetup-0.1.5.exe`。
2. 安装时建议保留桌面快捷方式。
3. 启动游戏，并打开到“卡厄思选难度/主页进入”相关界面。
4. 从桌面快捷方式 `CZN Auto` 或开始菜单启动。
5. 按 Windows 提示授权管理员权限。
6. 切换到全屏游戏界面，程序会开始识别并自动点击。
7. 程序识别到目标卡后会自动停止。

停止快捷键：

```text
F8 / Esc / Pause / End
```

开始菜单里还会有：

- `CZN Auto`：运行完整循环。
- `CZN Auto One Click Test`：只测试一次点击，适合首次使用前试点位。
- `Open CZN Auto Config`：打开配置文件。
- `Stop CZN Auto`：创建停止文件，强制让程序退出循环。

## 便携版使用

1. 下载并解压 `CZNAuto-portable.zip`。
2. 运行 `start_czn_auto.bat`。它默认就是后台窗口点击。
3. 首次使用建议先运行 `run_one_click.bat` 测试一次点击。
4. 如需强制停止，运行 `stop_czn_auto.bat`。
5. 如需修改配置，运行 `open_config.bat`。

便携版目录里的主要文件：

```text
start_czn_auto.bat      正式启动脚本，默认后台窗口点击
CZNAuto.exe             主程序本体，不建议直接双击
run_one_click.bat       单次点击测试脚本
stop_czn_auto.bat       停止脚本
open_config.bat         打开配置
config.json             当前生效配置
config.example.json     默认配置备份
CONFIG.md               配置字段说明
templates\              识别图片
_internal\              程序依赖文件，不建议手动改
```

## 配置文件

配置文件放在程序目录：

```text
config.json
```

`config.json` 是真正生效的配置。`config.example.json` 是默认模板和备份，正常不要改它。

如果 `config.json` 改坏了，可以删除它，或者用 `config.example.json` 覆盖回来。

配置里最常改的是：

- `click_points.team_enter`：配队页“进入”点击位置。
- `click_points.advance`：对白/继续点击位置。
- `timing.wait_after_team_enter`：点配队进入后，等多久再开始对白连点。
- `timing.post_click_wait`：点击后等待画面变化的通用时间。
- `timing.reward_settle_before_action`：卡牌奖励页出现后，等多久再识别/退出。

详细字段说明见：

[CONFIG.md](./CONFIG.md)

输入方式也在配置里：

```json
"input": {
  "backend": "postmessage_activate",
  "restore_cursor_after_click": false,
  "target_window_title": "卡厄思梦境"
}
```

`postmessage_activate` 是默认后台窗口点击，正常启动时就会使用，通常不会移动或占用你的真实鼠标。当前测试里它已经能完成配队进入、对白推进、传说选择、奖励页退出、回首页和继续下一轮。`sendinput` 是真实鼠标兼容模式，稳定但会占用鼠标；`restore_cursor_after_click` 可以在真实点击后把鼠标移回原位置，只是点击瞬间仍会占用鼠标。

多屏和截图方式在配置里的 `runtime`：

```json
"runtime": {
  "monitor": "auto",
  "capture_method": "auto"
}
```

`monitor: auto` 会按游戏窗口标题自动选屏。`capture_method: auto` 默认使用更适合多屏/窗口模式的稳定截图；如果手动改成 `dxgi` 后窗口化一直 unknown、日志里 DXGI 反复 access loss，可以改回 `auto` 或 `mss`。

坐标使用比例，不是像素。例如：

```json
"team_enter": [0.84, 0.905]
```

表示点击当前截图宽度的 84%、高度的 90.5%。同一画面比例下，1080P、2K、4K 会自动缩放。

## 识别图片

识别图片放在程序目录：

```text
templates\
```

程序会优先读取外层 `templates\`。如果高级用户需要适配自己的画面，可以替换同名图片，重启程序后生效。

常见模板：

- `start_enter_button.jpg`：主页进入按钮。
- `team_enter_button.jpg`：配队页进入按钮。
- `legend_word.jpg` / `legend_word_wide.jpg`：三选一里的目标词。
- `card_reward_title.jpg`：卡牌奖励页标题区域。
- `dream_border_title.jpg`：目标卡牌识别区域。
- `choice_bottom_glow.jpg`：三选一卡牌底部光效锚点。
- `combat_top_right_menu.jpg`：右上角菜单。
- `flee_button.jpg`：脱逃按钮。
- `return_confirm_button.jpg`：返回确认按钮。

替换模板前建议先备份原图。模板改坏后，用发布包里的原文件覆盖回来即可。

## 工作流程

程序每轮会截图并识别当前状态，然后按状态执行下一步：

1. 主页：点击进入。
2. 配队页：点击进入。
3. 加载/对白：等待一段时间后进行对白推进。
4. 三选一：识别右侧选项是否包含目标词。
5. 命中目标词：点击目标选项并确认。
6. 目标词后对白：如果进奖励页前还有一小段对白，只短点几下。
7. 卡牌奖励页：识别是否出现目标卡。
8. 找到目标卡：停止程序。
9. 没找到目标卡：按配置退出/重试，进入下一轮。

为了降低误点风险，`unknown` 画面的连续点击只会在“主页 -> 配队 -> 对白”这条流程里启用，不会在退出、返回大厅等其它 unknown 画面随意连点。

## 快速点击和等待

对白连点默认使用 `rapid` 模式：

- 先快速连续点击，保留原来的推进速度。
- 连点后识别一次当前状态。
- 如果没有进入下一步，会追加少量慢速 checked 兜底点击。

如果某台机器加载慢，可以优先调大：

```json
"wait_after_team_enter": 8.0,
"post_click_wait": 5.0,
"reward_settle_before_action": 2.0
```

如果要临时使用更稳但更慢的对白模式，可以改配置：

```json
"dialog_burst_mode": "checked"
```

开发调试时也可以用启动参数：

```powershell
--dialog-burst-mode checked
```

## 分辨率和适配

当前识别模板以 4K `3840x2160` 为基准制作。程序会按截图尺寸自动缩放模板和点击坐标。

同为 16:9 的全屏分辨率通常可以直接使用：

- 4K：`3840x2160`
- 2K：`2560x1440`
- 1080P：`1920x1080`

`2560x1600` 等 16:10 环境也做了部分兼容，尤其是配队页误识别时会启用 `team_enter` 兜底点击。

如果游戏窗口化、带黑边、非全屏、显示缩放异常，识别和点击位置可能偏移。此时优先检查：

- 游戏是否在主显示器或配置的目标显示器上。
- 游戏画面是否铺满截图区域。
- Windows 缩放、分辨率是否和预期一致。
- `config.json` 里的对应点击比例是否需要微调。
- `templates\` 里的模板是否适合当前语言/画面。

## 运行日志

每次启动都会生成独立日志。默认目录：

```text
%LOCALAPPDATA%\CZN Auto\logs
```

日志文件名类似：

```text
czn_auto_20260527_234348_67688.log
```

日志会记录：

- 启动参数。
- 程序路径。
- 配置读取情况。
- 屏幕分辨率和显示器列表。
- DPI、截图尺寸、截图后端。
- 当前识别到的状态。
- 模板匹配分数和坐标。
- 实际点击位置。
- 点击后是否进入预期状态。
- `HIGH RISK` 高风险等待/超时提示。
- 异常堆栈。

用户反馈问题时，建议提供：

1. 最新的 `czn_auto_*.log`。
2. 出问题时的游戏截图或手机拍屏。
3. 使用的分辨率、是否全屏、是否多显示器。
4. 大概卡在哪一步，例如配队页点歪、对白不点、奖励页退出太快。

日志里出现 `HIGH RISK`，通常表示“程序已经点击，但一段时间内没有进入预期的下一个状态”。常见原因是点击位置偏、加载时间太短、画面比例不一致、截图失效或模板没识别到。

## 常见问题

**程序没有反应**

先确认是否以管理员权限运行。游戏窗口通常也需要在前台，且画面要能被截图捕获。

**点击位置偏很多**

先看日志里的 `display_environment`、`frame_shape` 和 `click screen=(x,y)`。如果是配队页点歪，优先改 `config.json` 里的 `click_points.team_enter`。

**点配队进入后，对白还没出来就开始连点**

调大：

```json
"wait_after_team_enter": 8.0
```

**奖励页刚出现就退出，没等卡牌稳定**

调大：

```json
"reward_settle_before_action": 2.0
```

**对白推进太慢**

可以适当增大：

```json
"dialog_burst_max_taps": 11
```

**对白误点风险高**

改成更稳的 checked 模式：

```json
"dialog_burst_mode": "checked"
```

**识别不稳定**

可以尝试启动参数：

```powershell
--wide-match-scales
```

也可以针对当前画面替换 `templates\` 里的同名模板。

## 开发运行

开发环境需要 Python 3.11+。

安装依赖：

```powershell
python -m pip install -r requirements.txt
```

只识别不点击：

```powershell
python czn_detector.py --live
```

实际点击：

```powershell
python czn_detector.py --live --act --advance-on-unknown --fast-start-to-team --wide-match-scales
```

单张图片识别：

```powershell
python czn_detector.py --image path\to\screenshot.jpg --out-dir out
```

常用开发脚本：

```text
start_czn_auto_admin.bat
run_one_click_admin.bat
stop_czn_auto.bat
```

## 构建发布版

构建需要：

- Windows
- Python 3.11+
- Inno Setup 6，可选但推荐，用于生成安装包

运行：

```text
build_release.bat
```

生成结果：

```text
dist\CZNAuto-portable.zip
dist\installer\CZNAutoSetup-0.1.5.exe
```

仓库也提供 GitHub Actions 的 `Windows Release` 工作流，可以手动触发云端构建。

## 项目结构

```text
czn_detector.py          主程序，识别和自动点击逻辑
templates\               默认识别模板
config.example.json      默认配置模板
CONFIG.md                配置字段说明
installer\czn_auto.iss   Inno Setup 安装包脚本
czn_auto.spec            PyInstaller 打包配置
build_release.bat        本地打包脚本
RELEASE.md               发布和打包规范
start_*_admin.bat        开发环境正式启动脚本
start_*_exe.bat          发布包正式启动脚本
run_*_admin.bat          其他开发环境运行脚本
run_*_exe.bat            其他发布包运行脚本
STATE_MAP.md             状态流程说明
LESSONS.md               调试经验记录
```

## 注意事项

请只在你了解自动点击行为、并能随时停止程序的情况下使用。首次使用建议先运行 `run_one_click.bat` 做单次测试，确认当前分辨率、画面状态、点击位置都正常后，再运行完整循环。

如果程序表现和预期不同，不要连续多开多个实例。先按 `F8`、`Esc`、`Pause` 或 `End` 停止，再查看最新日志。
