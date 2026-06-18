# 配置说明

配置文件就在程序目录：

```text
config.json
```

识别图片也在程序目录：

```text
templates\
```

安装版开始菜单里有 `Open CZN Auto Config`，便携版双击 `open_config.bat`，会直接打开 `config.json`。

坐标是比例，不是像素。`[0, 0]` 是截图左上角，`[1, 1]` 是截图右下角。

例如：

```json
"team_enter": [0.84, 0.905]
```

含义是当前截图宽度的 84%、高度的 90.5%。同一画面比例下，1080P、2K、4K 会自动缩放。

时间单位都是秒。改配置后需要重新启动程序才会生效。

## 最常改的项

- `click_points.team_enter`：配队页进入按钮点歪时，优先改这个。
- `click_points.advance`：对白/继续点歪时改这个。
- `timing.wait_after_team_enter`：点配队进入后，加载慢、对白还没出来就开始点时，加大这个。
- `timing.post_click_wait`：点击后等待下一步界面变化的通用时间。
- `timing.reward_settle_before_action`：卡牌奖励页出现后，识别太急或立刻退出时，加大这个。
- `timing.choice_settle_before_action`：第一阶段三选一出现后，先短等多久再判断是否没有传说；通常不用加太大。

机器慢，可以先试：

```json
"wait_after_team_enter": 8.0,
"post_click_wait": 5.0,
"reward_settle_before_action": 2.0,
"choice_settle_before_action": 0.35
```

## click_points 字段

- `_说明`：给用户看的说明文字，程序会忽略。
- `advance`：对白、过场、继续推进时点击的位置。
- `choice_right`：三选一奖励里右侧选项的大致点击位置。
- `confirm`：通用确认按钮兜底位置，主要用于固定流程里的确认。
- `retry_top_right`：卡牌奖励页右上角菜单/重试区域。
- `start_enter`：主页进入按钮的固定点击位置。
- `team_enter`：配队页进入按钮的固定点击位置，也是 16:10 配队页误识别时的兜底点击位置。
- `button_text_point`：当程序识别到某个按钮图片后，在识别框内部点击的位置；`[0.78, 0.52]` 表示点识别框内横向 78%、纵向 52% 的地方。
- `chain_flee`：无传说快链里，打开菜单后点击“脱逃/退出”的兜底位置。
- `chain_return_confirm`：无传说快链里，返回确认弹窗的确认按钮兜底位置。
- `choice_confirm_y`：点三选一选项后，对勾确认按钮的纵向比例；横向会根据选中的卡牌位置推算。
- `team_fallback_match_max_x`：配队页被误识别成主页按钮时的横向判定阈值；识别点的 x 比例小于等于它，才可能触发配队兜底。
- `team_fallback_match_min_y`：配队页被误识别成主页按钮时的纵向判定阈值；识别点的 y 比例大于等于它，才可能触发配队兜底。

`team_fallback_match_max_x` 和 `team_fallback_match_min_y` 一般不用改。只有日志里明明在配队页，却一直没有出现 `team screen fallback: click fixed enter` 时，才考虑小幅调整。

## timing 字段

- `_说明`：给用户看的说明文字，程序会忽略。
- `live_loop_interval`：主循环识图间隔。越小反应越快，也越吃性能。
- `live_log_interval`：同一个状态重复打印日志的最小间隔。只影响日志频率。
- `post_click_wait`：点击后等待画面变化的通用时间。网络或机器慢可以加大。
- `wait_after_team_enter`：点配队页进入后，等待加载/对白出现的时间。加载慢最优先调这个。
- `reward_settle_before_action`：识别到卡牌奖励页后，先停留多久再判断有没有目标卡、是否退出。
- `choice_settle_before_action`：第一阶段三选一还没识别到传说时，先短暂停留多久再按无传说处理。
- `start_to_team_burst_taps`：主页到配队页的快速点击次数。现在默认 1，通常不要加大。
- `start_to_team_tap_delay`：主页快速点击之间的间隔。
- `dialog_burst_max_taps`：对白 rapid 连点最多点几下。
- `dialog_burst_tap_delay`：对白 checked 模式下，每次点击后的等待时间。
- `dialog_burst_mode`：对白推进模式。`rapid` 是快速连续点击，`checked` 是每点一次就识图，慢但更稳。
- `dialog_burst_rapid_postcheck`：rapid 连点完成后，等待多久再识图检查是否进入下一步。
- `dialog_burst_fallback_taps`：rapid 连点后没有推进时，追加 checked 兜底点击的次数。
- `dialog_burst_fallback_tap_delay`：追加 checked 兜底点击之间的间隔。
- `legend_dialog_taps`：点传说选项并确认后，如果奖励页前还有一小段对白，最多短点几下。
- `legend_dialog_tap_delay`：传说后短对白每次点击之间的间隔。
- `legend_confirm_delay`：点传说选项后，等待确认对勾可点的时间。
- `chain_menu_to_flee_delay`：无传说快链里，点右上角菜单后，等多久再点脱逃兜底。
- `chain_flee_to_confirm_delay`：无传说快链里，点脱逃后，等多久再点返回确认兜底。
- `chain_menu_to_flee_timeout`：点右上角菜单后，等待识别脱逃页的最长时间。
- `chain_flee_to_confirm_timeout`：点脱逃后，等待识别返回确认弹窗的最长时间。
- `chain_after_confirm_delay`：点返回确认后，给界面开始跳转的一小段等待。
- `fast_click_duration`：普通快速点击的按下时长。通常不要改。
- `chain_click_duration`：固定快链点击的按下时长。通常不要改。
- `click_move_delay`：点击前鼠标移动准备等待。通常不要改。
- `click_absolute_move_delay`：鼠标移动到目标坐标后的短等待。通常不要改。
- `click_after_up_delay`：鼠标松开后的短等待。通常不要改。
- `focus_top_delay`：程序尝试把游戏窗口提到前台后的等待。
- `focus_foreground_delay`：窗口切到前台后的等待。
- `focus_retry_delay`：前台切换重试之间的等待。
- `visual_change_poll_interval`：等待画面变化时的轮询间隔。
- `delay_reward_already_handled`：奖励页已经处理过一次后，再次识别到奖励页时的短等待。
- `delay_after_reward_action`：奖励页执行退出/确认动作后的短等待。
- `delay_after_return_confirm`：点返回确认后的短等待。
- `delay_after_no_legend_chain`：无传说快链执行完后的短等待。
- `delay_choice_already_handled`：三选一无传说已经处理过一次后，再次识别到三选一时的短等待。
- `delay_after_flee`：点脱逃后的短等待。
- `delay_after_team_enter`：点配队页进入后的循环短等待；主要防止立刻重复处理。
- `delay_start_already_handled`：主页进入已经点过一次后，还停留在主页识别时的短等待。
- `delay_after_start_enter`：点主页进入后的短等待。
- `delay_after_unknown_burst`：对白/unknown 连点完成后的短等待。
- `delay_unknown_idle`：unknown 状态但还没允许对白连点时的空等时间。
- `delay_after_legend_confirm`：传说选项确认后的短等待。

## templates 识别图片

`templates\` 里的图片是识别模板。高级用户可以替换同名图片来适配自己的画面。替换后重启程序生效。

简体资源放在单独目录，原来的 `templates\` 根目录继续作为默认/繁体模板：

```text
templates\zh-Hans\   简体覆盖图
templates\           默认/繁体图
```

`input.ui_language` 可以填：

- `auto`：默认。自动尝试语言子目录和通用模板。
- `zh-Hans`：强制优先使用简体模板。
- `zh-Hant`：强制优先使用繁体模板；没有繁体覆盖目录时使用根目录模板。

语言目录里不用放全套图片。缺少的图片会自动回退到 `templates\` 里的默认模板。

常见文件：

- `start_enter_button.jpg`：主页进入按钮。
- `team_enter_button.jpg`：配队页进入按钮。
- `legend_word.jpg` / `legend_word_wide.jpg`：三选一里“传说”文字。
- `card_reward_title.jpg`：卡牌奖励页标题区域。
- `dream_border_title.jpg`：目标卡牌文字/标题区域。
- `choice_bottom_glow.jpg`：三选一底部光效锚点。
- `combat_top_right_menu.jpg`：战斗/奖励页右上角菜单。
- `flee_button.jpg`：脱逃按钮。
- `return_confirm_button.jpg`：返回确认按钮。

改坏了就用发布包里的原文件覆盖回来。

## 日志

运行日志仍在：

```text
%LOCALAPPDATA%\CZN Auto\logs
```

日志开头会打印实际读取的 `config.json`、点击坐标和等待时间。配置写错时会打印 warning，并继续使用默认值。
## input 字段

- `backend`: 输入后端。`postmessage_activate` 是默认后台窗口点击，通常不会移动或占用真实鼠标；当前测试里已经跑通配队进入、对白推进、传说选择、奖励页退出、回首页和继续下一轮。`sendinput` 是真实鼠标兼容模式，稳定但会占用鼠标。
- `restore_cursor_after_click`: 仅对 `sendinput` 有效。设为 `true` 时，每次点击后把鼠标移回点击前的位置，可以减轻对日常鼠标的打扰，但点击瞬间仍会占用鼠标。
- `target_window_title`: 默认 `卡厄思梦境`。程序会优先把后台点击消息发给标题匹配的窗口，并把固定比例点击按这个窗口的客户区计算，所以窗口模式下也不会再按整块显示器计算固定点击坐标；设为空字符串时退回按点击坐标下方窗口发送消息。
- `ui_language`: 识别图片语言。默认 `auto`；简体版识别不稳时可改成 `zh-Hans`，繁体版可改成 `zh-Hant`。

## runtime 字段

- `monitor`: 默认 `auto`。程序会按 `target_window_title` 自动选择游戏窗口所在的显示器，适合多屏和窗口模式；也可以手动填 `1`、`2`、`3` 等显示器编号。
- `capture_method`: 默认 `auto`。优先使用更适合多屏/窗口模式的 `mss`；如果需要追求截图速度，可以手动改成 `dxgi`，但多屏顺序不对或日志里反复出现 DXGI access loss 时建议改回 `auto` 或 `mss`。
