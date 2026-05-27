# CZN Auto

CZN Auto 是一个 Windows 自动化小工具，用截图识别当前界面，再按固定流程完成点击操作。它主要用于一套重复流程：从主页进入队伍界面、推进对白、识别三选一卡牌奖励，并在目标卡牌出现时停止。

这个项目不要求使用者安装 Python。普通用户直接下载发布版安装包即可。

## 下载

最新版发布页：

[https://github.com/dengzhilei/czn_auto/releases/latest](https://github.com/dengzhilei/czn_auto/releases/latest)

推荐下载：

- `CZNAutoSetup-0.1.0.exe`：安装版，适合大多数用户
- `CZNAuto-portable.zip`：便携版，解压后运行

## 使用

安装版：

1. 下载并运行 `CZNAutoSetup-0.1.0.exe`
2. 安装时默认创建桌面快捷方式
3. 启动游戏，打开到“卡厄思选难度”界面
4. 从桌面快捷方式或开始菜单打开 `CZN Auto`
5. 按提示授权管理员权限
6. 切换到全屏游戏界面，工具会自动开始运行
7. 工具识别到“梦之边境”后会自动停止
8. 停止快捷键：`F8`、`Esc`、`Pause`、`End`

使用流程建议参考视频：

[https://www.bilibili.com/video/BV1KCVT6PEJ7/](https://www.bilibili.com/video/BV1KCVT6PEJ7/)

有问题可以加群 `1107667206` 反馈。

便携版：

1. 下载并解压 `CZNAuto-portable.zip`
2. 双击 `run_min_loop.bat`
3. 如需先测试一次点击，双击 `run_one_click.bat`
4. 如需强制停止，双击 `stop_czn_auto.bat`

## 运行日志

每次启动程序都会单独生成一个日志文件，里面会记录启动参数、运行环境、屏幕分辨率、显示器列表、实际截图尺寸、识别到的界面状态、点击位置、截图后等待结果和异常信息。

默认日志目录：

```text
%LOCALAPPDATA%\CZN Auto\logs
```

如果运行不正常，反馈时请把最新的 `czn_auto_*.log` 一起发出来。日志里出现 `HIGH RISK` 时，通常表示“已经点击，但一段时间内没有进入预期的下一个状态”，优先检查游戏是否在目标显示器、分辨率/缩放是否异常、截图是否 stale、等待时间是否太短。

开发调试时也可以用 `--log-file 路径` 指定日志文件，或用 `--no-run-log` 临时关闭文件日志。

部分快速流程会先等下一步界面识别成功，再点击真实按钮位置；如果等待超时，才会使用固定坐标兜底并在日志里标记 `HIGH RISK`。这主要用于兼容不同电脑加载速度不一致的问题。

对白连点默认使用 `rapid` 模式，保留原来的连续点击速度，并在连点后做一次状态检查。如果没有进入下一步，会自动追加少量慢速 checked 兜底点击；用户不需要改参数。

排查慢机器或异常点击时，也可以临时使用：

```powershell
--dialog-burst-mode checked
```

`checked` 模式会在每次点击后重新截图识别；如果已经进入三选一、卡牌奖励、目标卡等已知界面，会提前停止后续连点，但速度会比 `rapid` 慢。

点中传说选项并确认后，如果进入卡牌奖励前还有一小段对白，程序会把这段 `unknown` 当作传说后的对白，只短点 2 下，再继续等待卡牌奖励界面。

## 适配说明

当前模板以 4K `3840x2160` 为基准制作。程序会按截图比例自动缩放模板和点击坐标，所以同为 16:9 的全屏分辨率通常可以直接使用：

- 4K：`3840x2160`
- 2K：`2560x1440`
- 1080P：`1920x1080`

如果游戏窗口化、带黑边、非 16:9，程序会打印比例警告，识别和点击位置可能需要重新调模板或坐标。

## 工作方式

程序每轮会截图并识别当前界面，然后根据状态执行下一步：

1. 主页：点击进入
2. 队伍界面：点击进入
3. 对白/过场：按配置进行连续点击
4. 三选一界面：识别右侧是否有目标词
5. 卡牌奖励界面：识别目标卡牌，找到后停止
6. 没找到目标卡牌：按配置退出/重试

对 unknown 画面的连续点击只会在“主页 -> 队伍 -> 对白”这条流程中启用，不会在退出、返回大厅等其它 unknown 画面乱点。

## 开发运行

开发环境需要 Python 3.11+：

```powershell
python -m pip install -r requirements.txt
python czn_detector.py --live
```

实际点击：

```powershell
python czn_detector.py --live --act --advance-on-unknown --fast-start-to-team
```

常用开发脚本：

```text
run_min_loop_admin.bat
run_one_click_admin.bat
stop_czn_auto.bat
```

## 关键参数

常用参数集中在 `czn_detector.py` 顶部：

```python
LIVE_LOOP_INTERVAL = 0.25
LIVE_LOG_INTERVAL = 1.50
DIALOG_BURST_MAX_TAPS = 9
DIALOG_BURST_TAP_DELAY = 0.4
DIALOG_BURST_MODE = "rapid"
DIALOG_BURST_RAPID_POSTCHECK = 1.0
DIALOG_BURST_FALLBACK_TAPS = 3
DIALOG_BURST_FALLBACK_TAP_DELAY = 0.6
LEGEND_DIALOG_TAPS = 2
LEGEND_DIALOG_TAP_DELAY = 0.4
START_TO_TEAM_BURST_TAPS = 1
START_TO_TEAM_TAP_DELAY = 0.5
WAIT_AFTER_TEAM_ENTER_BEFORE_DIALOG = 7.0
REWARD_SETTLE_BEFORE_ACTION = 1.5
```

如果识别不稳定，可以尝试启动参数：

```powershell
--wide-match-scales
```

## 构建发布版

在 Windows 上运行：

```text
build_release.bat
```

生成结果：

```text
dist\CZNAuto-portable.zip
dist\installer\CZNAutoSetup-0.1.0.exe
```

仓库也提供 GitHub Actions 的 `Windows Release` 工作流，可以手动触发云端构建。

## 注意

请只在你了解自动点击行为、并能随时停止程序的情况下使用。建议先用 `run_one_click.bat` 做单次测试，确认当前分辨率和界面状态识别正常后，再运行完整循环。
