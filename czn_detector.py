from __future__ import annotations

import argparse
import atexit
import dataclasses
import ctypes
import json
import os
import platform
import sys
import time
import traceback
from pathlib import Path
from typing import Iterable

import cv2
import numpy as np


BASE_W = 3840
BASE_H = 2160
BASE_ASPECT = BASE_W / BASE_H
ASPECT_TOLERANCE = 0.03
DEFAULT_GAME_WINDOW_TITLE = "卡厄思梦境"
_DXGI_CAMERAS: dict[int, object] = {}
_RUN_LOG_HANDLE = None
_RUN_LOG_STDOUT = None
_RUN_LOG_STDERR = None
_DEFAULT_UNRAISABLEHOOK = sys.unraisablehook
_ENUM_WINDOWS_PROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)


class TeeStream:
    def __init__(self, stream, log_file) -> None:
        self.stream = stream
        self.log_file = log_file

    def write(self, data: str) -> int:
        for target in (self.stream, self.log_file):
            try:
                target.write(data)
            except Exception:
                pass
        return len(data)

    def flush(self) -> None:
        for target in (self.stream, self.log_file):
            try:
                target.flush()
            except Exception:
                pass

    def isatty(self) -> bool:
        try:
            return self.stream.isatty()
        except Exception:
            return False

    @property
    def encoding(self) -> str:
        return getattr(self.stream, "encoding", "utf-8")

    def __getattr__(self, name: str):
        return getattr(self.stream, name)


def install_unraisable_filter() -> None:
    def hook(unraisable) -> None:
        exc = unraisable.exc_value
        obj = unraisable.object
        obj_text = repr(obj)
        if (
            isinstance(exc, OSError)
            and "access violation writing" in str(exc).lower()
            and ("comtypes" in obj_text or "_compointer_base" in obj_text)
        ):
            print(
                f"warning: suppressed known comtypes cleanup warning: {exc}",
                file=sys.stderr,
                flush=True,
            )
            return
        _DEFAULT_UNRAISABLEHOOK(unraisable)

    sys.unraisablehook = hook


def app_base_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def app_install_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def default_log_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base) / "CZN Auto" / "logs"
    return Path.home() / "AppData" / "Local" / "CZN Auto" / "logs"


def default_config_dir() -> Path:
    return app_install_dir()


def default_config_file() -> Path:
    return default_config_dir() / "config.json"


def default_log_file() -> Path:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    return default_log_dir() / f"czn_auto_{stamp}_{os.getpid()}.log"


def _close_run_log() -> None:
    global _RUN_LOG_HANDLE, _RUN_LOG_STDOUT, _RUN_LOG_STDERR
    if _RUN_LOG_HANDLE is None:
        return
    try:
        print(f"run log closed: {_RUN_LOG_HANDLE.name}", flush=True)
    except Exception:
        pass
    try:
        sys.stdout = _RUN_LOG_STDOUT or sys.stdout
        sys.stderr = _RUN_LOG_STDERR or sys.stderr
        _RUN_LOG_HANDLE.close()
    except Exception:
        pass
    _RUN_LOG_HANDLE = None


def setup_run_log(log_file: Path | None) -> Path | None:
    global _RUN_LOG_HANDLE, _RUN_LOG_STDOUT, _RUN_LOG_STDERR
    if _RUN_LOG_HANDLE is not None:
        return Path(_RUN_LOG_HANDLE.name)

    path = log_file or default_log_file()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        _RUN_LOG_HANDLE = path.open("a", encoding="utf-8", buffering=1)
    except OSError as exc:
        print(f"warning: failed to open run log {path}: {exc}", file=sys.stderr, flush=True)
        return None

    _RUN_LOG_STDOUT = sys.stdout
    _RUN_LOG_STDERR = sys.stderr
    sys.stdout = TeeStream(sys.stdout, _RUN_LOG_HANDLE)
    sys.stderr = TeeStream(sys.stderr, _RUN_LOG_HANDLE)
    atexit.register(_close_run_log)
    return path


def json_safe_args(args: argparse.Namespace) -> str:
    values = {}
    for key, value in vars(args).items():
        if isinstance(value, Path):
            values[key] = str(value)
        else:
            values[key] = value
    return json.dumps(values, ensure_ascii=False, sort_keys=True)


def print_run_header(args: argparse.Namespace, log_path: Path | None) -> None:
    print("=" * 80)
    print(f"CZN Auto run started at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"log_file={log_path if log_path else 'disabled/unavailable'}")
    print(f"cwd={Path.cwd()}")
    print(f"app_base={app_base_dir()}")
    print(f"app_install_dir={app_install_dir()}")
    print(f"frozen={bool(getattr(sys, 'frozen', False))}")
    print(f"python={sys.version.split()[0]} executable={sys.executable}")
    print(f"platform={platform.platform()}")
    print(f"argv={sys.argv!r}")
    print(f"args={json_safe_args(args)}")
    print(f"config_messages={json.dumps(CONFIG_MESSAGES, ensure_ascii=False)}")
    print(f"display_environment={json.dumps(display_environment(), ensure_ascii=False, sort_keys=True)}")
    print(f"runtime_defaults={json.dumps(runtime_timing_profile(), ensure_ascii=False, sort_keys=True)}")
    print(f"click_defaults={json.dumps(runtime_click_profile(), ensure_ascii=False, sort_keys=True)}")
    print("=" * 80)


def display_environment() -> dict:
    user32 = ctypes.windll.user32
    info: dict[str, object] = {
        "primary_width": user32.GetSystemMetrics(0),
        "primary_height": user32.GetSystemMetrics(1),
        "virtual_left": user32.GetSystemMetrics(76),
        "virtual_top": user32.GetSystemMetrics(77),
        "virtual_width": user32.GetSystemMetrics(78),
        "virtual_height": user32.GetSystemMetrics(79),
        "monitor_count": user32.GetSystemMetrics(80),
    }
    try:
        info["system_dpi"] = user32.GetDpiForSystem()
    except Exception:
        pass
    try:
        import mss

        mss_cls = getattr(mss, "MSS", None) or getattr(mss, "mss")
        with mss_cls() as sct:
            info["mss_monitors"] = [dict(monitor) for monitor in sct.monitors]
    except Exception as exc:
        info["mss_monitors_error"] = repr(exc)
    return info


def _window_text(hwnd: int) -> str:
    length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buffer = ctypes.create_unicode_buffer(length + 1)
    ctypes.windll.user32.GetWindowTextW(hwnd, buffer, length + 1)
    return buffer.value


def _window_pid(hwnd: int) -> int:
    pid = ctypes.c_ulong()
    ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return int(pid.value)


def list_visible_windows() -> list[dict[str, object]]:
    user32 = ctypes.windll.user32
    windows: list[dict[str, object]] = []

    @_ENUM_WINDOWS_PROC
    def callback(hwnd, _lparam) -> bool:
        hwnd_int = int(hwnd)
        visible = bool(user32.IsWindowVisible(hwnd_int))
        iconic = bool(user32.IsIconic(hwnd_int))
        if not visible and not iconic:
            return True
        title = _window_text(hwnd_int).strip()
        if not title:
            return True
        rect = window_client_rect(hwnd_int, allow_minimized=False)
        if rect is None and iconic:
            left, top, width, height = (-32000, -32000, 0, 0)
        elif rect is None:
            return True
        else:
            left, top, width, height = rect
            if width < 200 or height < 150:
                return True
        windows.append(
            {
                "hwnd": hwnd_int,
                "pid": _window_pid(hwnd_int),
                "title": title,
                "left": left,
                "top": top,
                "width": width,
                "height": height,
                "minimized": iconic,
            }
        )
        return True

    user32.EnumWindows(callback, 0)
    return windows


def find_window_by_title(title_query: str) -> int:
    query = title_query.strip().lower()
    if not query:
        raise ValueError("window title query is empty")
    exact: int | None = None
    partial: int | None = None
    user32 = ctypes.windll.user32

    @_ENUM_WINDOWS_PROC
    def callback(hwnd_raw, _lparam) -> bool:
        nonlocal exact, partial
        hwnd = int(hwnd_raw)
        title = _window_text(hwnd).strip()
        if not title:
            return True
        lowered = title.lower()
        if lowered == query:
            exact = hwnd
            return False
        if partial is None and query in lowered:
            partial = hwnd
        return True

    user32.EnumWindows(callback, 0)
    hwnd = exact or partial
    if hwnd:
        return hwnd
    raise RuntimeError(f"no visible window title contains: {title_query!r}")


def window_client_rect(hwnd: int, *, allow_minimized: bool = True) -> tuple[int, int, int, int] | None:
    user32 = ctypes.windll.user32
    if not hwnd or not user32.IsWindow(hwnd):
        return None
    if not allow_minimized and user32.IsIconic(hwnd):
        return None

    class Rect(ctypes.Structure):
        _fields_ = (("left", ctypes.c_long), ("top", ctypes.c_long), ("right", ctypes.c_long), ("bottom", ctypes.c_long))

    class Point(ctypes.Structure):
        _fields_ = (("x", ctypes.c_long), ("y", ctypes.c_long))

    rect = Rect()
    if not user32.GetClientRect(hwnd, ctypes.byref(rect)):
        return None
    width = int(rect.right - rect.left)
    height = int(rect.bottom - rect.top)
    if width <= 0 or height <= 0:
        return None
    point = Point(0, 0)
    if not user32.ClientToScreen(hwnd, ctypes.byref(point)):
        return None
    return int(point.x), int(point.y), width, height


def window_outer_rect(hwnd: int) -> tuple[int, int, int, int] | None:
    user32 = ctypes.windll.user32
    if not hwnd or not user32.IsWindow(hwnd):
        return None

    class Rect(ctypes.Structure):
        _fields_ = (("left", ctypes.c_long), ("top", ctypes.c_long), ("right", ctypes.c_long), ("bottom", ctypes.c_long))

    rect = Rect()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return None
    return int(rect.left), int(rect.top), int(rect.right), int(rect.bottom)


def ensure_window_not_minimized(hwnd: int, title: str) -> bool:
    user32 = ctypes.windll.user32
    if not user32.IsIconic(hwnd):
        return True
    print(f"window is minimized; trying ShowWindow(SW_SHOWNOACTIVATE): {title!r}", flush=True)
    user32.ShowWindow(hwnd, 4)
    time.sleep(0.25)
    if not user32.IsIconic(hwnd):
        return True
    print(
        "window is still minimized. Restore the game window without covering it, then retry.",
        flush=True,
    )
    return False


def runtime_timing_profile() -> dict:
    return {
        "live_loop_interval": LIVE_LOOP_INTERVAL,
        "live_log_interval": LIVE_LOG_INTERVAL,
        "post_click_wait": POST_CLICK_WAIT,
        "wait_after_team_enter": WAIT_AFTER_TEAM_ENTER_BEFORE_DIALOG,
        "dialog_burst_max_taps": DIALOG_BURST_MAX_TAPS,
        "dialog_burst_tap_delay": DIALOG_BURST_TAP_DELAY,
        "dialog_burst_mode": DIALOG_BURST_MODE,
        "dialog_burst_rapid_postcheck": DIALOG_BURST_RAPID_POSTCHECK,
        "dialog_burst_fallback_taps": DIALOG_BURST_FALLBACK_TAPS,
        "dialog_burst_fallback_tap_delay": DIALOG_BURST_FALLBACK_TAP_DELAY,
        "legend_dialog_taps": LEGEND_DIALOG_TAPS,
        "legend_dialog_tap_delay": LEGEND_DIALOG_TAP_DELAY,
        "start_to_team_burst_taps": START_TO_TEAM_BURST_TAPS,
        "start_to_team_tap_delay": START_TO_TEAM_TAP_DELAY,
        "reward_settle_before_action": REWARD_SETTLE_BEFORE_ACTION,
        "chain_menu_to_flee_delay": CHAIN_MENU_TO_FLEE_DELAY,
        "chain_flee_to_confirm_delay": CHAIN_FLEE_TO_CONFIRM_DELAY,
        "chain_menu_to_flee_timeout": CHAIN_MENU_TO_FLEE_TIMEOUT,
        "chain_flee_to_confirm_timeout": CHAIN_FLEE_TO_CONFIRM_TIMEOUT,
        "chain_after_confirm_delay": CHAIN_AFTER_CONFIRM_DELAY,
        "legend_confirm_delay": LEGEND_CONFIRM_DELAY,
        "fast_click_duration": FAST_CLICK_DURATION,
        "chain_click_duration": CHAIN_CLICK_DURATION,
        "click_move_delay": CLICK_MOVE_DELAY,
        "click_absolute_move_delay": CLICK_ABSOLUTE_MOVE_DELAY,
        "click_after_up_delay": CLICK_AFTER_UP_DELAY,
        "focus_top_delay": FOCUS_TOP_DELAY,
        "focus_foreground_delay": FOCUS_FOREGROUND_DELAY,
        "focus_retry_delay": FOCUS_RETRY_DELAY,
        "visual_change_poll_interval": VISUAL_CHANGE_POLL_INTERVAL,
        "delay_reward_already_handled": DELAY_REWARD_ALREADY_HANDLED,
        "delay_after_reward_action": DELAY_AFTER_REWARD_ACTION,
        "delay_after_return_confirm": DELAY_AFTER_RETURN_CONFIRM,
        "delay_after_no_legend_chain": DELAY_AFTER_NO_LEGEND_CHAIN,
        "delay_choice_already_handled": DELAY_CHOICE_ALREADY_HANDLED,
        "delay_after_flee": DELAY_AFTER_FLEE,
        "delay_after_team_enter": DELAY_AFTER_TEAM_ENTER,
        "delay_start_already_handled": DELAY_START_ALREADY_HANDLED,
        "delay_after_start_enter": DELAY_AFTER_START_ENTER,
        "delay_after_unknown_burst": DELAY_AFTER_UNKNOWN_BURST,
        "delay_unknown_idle": DELAY_UNKNOWN_IDLE,
        "delay_after_legend_confirm": DELAY_AFTER_LEGEND_CONFIRM,
        "click_window_log": LOG_CLICK_WINDOW,
        "click_method": CLICK_METHOD,
        "click_restore_after_action": CLICK_RESTORE_AFTER_ACTION,
        "postmessage_fallback_sendinput": POSTMESSAGE_FALLBACK_SENDINPUT,
    }


def runtime_click_profile() -> dict:
    return {
        "advance": CLICK_ADVANCE,
        "choice_right": CLICK_CHOICE_RIGHT,
        "confirm": CLICK_CONFIRM,
        "retry_top_right": CLICK_RETRY_TOP_RIGHT,
        "start_enter": CLICK_START_ENTER,
        "team_enter": CLICK_TEAM_ENTER,
        "button_text_point": BUTTON_TEXT_POINT,
        "chain_flee": CHAIN_FLEE_POINT,
        "chain_return_confirm": CHAIN_RETURN_CONFIRM_POINT,
        "choice_confirm_y": CHOICE_CONFIRM_Y,
        "team_fallback_match_max_x": TEAM_FALLBACK_MATCH_MAX_X,
        "team_fallback_match_min_y": TEAM_FALLBACK_MATCH_MIN_Y,
    }


def set_dpi_awareness() -> None:
    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        return
    except Exception:
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass


set_dpi_awareness()
install_unraisable_filter()


def _stop_dxgi_cameras() -> None:
    for camera in list(_DXGI_CAMERAS.values()):
        try:
            camera.stop()
        except Exception:
            pass
    _DXGI_CAMERAS.clear()


atexit.register(_stop_dxgi_cameras)


@dataclasses.dataclass(frozen=True)
class Box:
    x1: float
    y1: float
    x2: float
    y2: float

    def to_pixels(self, width: int, height: int) -> tuple[int, int, int, int]:
        return (
            max(0, min(width, int(round(self.x1 * width)))),
            max(0, min(height, int(round(self.y1 * height)))),
            max(0, min(width, int(round(self.x2 * width)))),
            max(0, min(height, int(round(self.y2 * height)))),
        )


@dataclasses.dataclass
class MatchResult:
    name: str
    score: float
    box: tuple[int, int, int, int]

    @property
    def center(self) -> tuple[int, int]:
        x1, y1, x2, y2 = self.box
        return ((x1 + x2) // 2, (y1 + y2) // 2)

    def point_at(self, rx: float, ry: float) -> tuple[int, int]:
        x1, y1, x2, y2 = self.box
        return (int(round(x1 + (x2 - x1) * rx)), int(round(y1 + (y2 - y1) * ry)))


@dataclasses.dataclass
class DetectionState:
    legend_choice: MatchResult | None
    dream_card: MatchResult | None
    card_reward: MatchResult | None
    choice_card: MatchResult | None
    return_confirm: MatchResult | None
    start_screen: MatchResult | None
    top_right_menu: MatchResult | None
    flee_button: MatchResult | None
    team_enter: MatchResult | None

    @property
    def label(self) -> str:
        if self.dream_card:
            return "dream_found"
        if self.card_reward:
            return "card_reward"
        if self.return_confirm:
            return "return_confirm"
        if self.legend_choice:
            return "legend_choice"
        if self.choice_card:
            return "choice_screen"
        if self.flee_button:
            return "flee_screen"
        if self.team_enter:
            return "team_screen"
        if self.start_screen:
            return "start_screen"
        return "unknown"


def detection_state(
    legend_choice: MatchResult | None = None,
    dream_card: MatchResult | None = None,
    card_reward: MatchResult | None = None,
    choice_card: MatchResult | None = None,
    return_confirm: MatchResult | None = None,
    start_screen: MatchResult | None = None,
    top_right_menu: MatchResult | None = None,
    flee_button: MatchResult | None = None,
    team_enter: MatchResult | None = None,
) -> DetectionState:
    return DetectionState(
        legend_choice=legend_choice,
        dream_card=dream_card,
        card_reward=card_reward,
        choice_card=choice_card,
        return_confirm=return_confirm,
        start_screen=start_screen,
        top_right_menu=top_right_menu,
        flee_button=flee_button,
        team_enter=team_enter,
    )


CHOICE_RIGHT_ROI = Box(2440 / BASE_W, 1600 / BASE_H, 3430 / BASE_W, 2050 / BASE_H)
CARD_REWARD_ROI = Box(560 / BASE_W, 470 / BASE_H, 3300 / BASE_W, 920 / BASE_H)

CLICK_ADVANCE = (0.935, 0.855)
CLICK_CHOICE_RIGHT = (0.765, 0.860)
CLICK_CONFIRM = (0.895, 0.945)
CLICK_RETRY_TOP_RIGHT = (0.955, 0.055)
CLICK_START_ENTER = (0.840, 0.905)
CLICK_TEAM_ENTER = (0.840, 0.905)
BUTTON_TEXT_POINT = (0.78, 0.52)
TEAM_FALLBACK_MATCH_MAX_X = 0.86
TEAM_FALLBACK_MATCH_MIN_Y = 0.90
CHOICE_CONFIRM_Y = 0.946

# ===== 可调速度参数 =====
# 主循环识别间隔。越小反应越快，也会更吃 CPU/GPU。
LIVE_LOOP_INTERVAL = 0.25
LIVE_LOG_INTERVAL = 1.50
FAST_MATCH_SCALE_FACTORS = (1.0,)
WIDE_MATCH_SCALE_FACTORS = (0.85, 0.9, 0.95, 1.0, 1.05, 1.1, 1.15)

# 一般点击按下到抬起的时间。太小可能被游戏漏掉，太大会拖慢连点。
FAST_CLICK_DURATION = 0.035

# 固定流程里的点击时长，例如“右上角 -> 脱逃 -> 确认”快链。
CHAIN_CLICK_DURATION = 0.04

# 无传说快链固定点击点。这里不做中途识图，按固定流程直接点。
CHAIN_FLEE_POINT = (0.923, 0.920)
CHAIN_RETURN_CONFIRM_POINT = (0.691, 0.652)

# 无传说快链固定间隔：右上角菜单 -> 脱逃 -> 确认。
# 如果漏点，优先稍微加大这两个值；如果稳定，可以继续降低。
CHAIN_MENU_TO_FLEE_DELAY = 0.3
CHAIN_FLEE_TO_CONFIRM_DELAY = 0.2
CHAIN_MENU_TO_FLEE_TIMEOUT = 1.8
CHAIN_FLEE_TO_CONFIRM_TIMEOUT = 1.8

# 点确认后给页面开始跳转的一点时间；后续仍由主循环识别当前位置。
CHAIN_AFTER_CONFIRM_DELAY = 0.20

# 对白页连续点击：最多连点次数。到三选一/奖励等已知状态会提前停。
DIALOG_BURST_MAX_TAPS = 9

# 对白页连续点击：每次点击后的间隔。想更快可以先试 0.08，再低要观察是否漏点。
DIALOG_BURST_TAP_DELAY = 0.4
DIALOG_BURST_MODE = "rapid"
DIALOG_BURST_RAPID_POSTCHECK = 1.0
DIALOG_BURST_FALLBACK_TAPS = 3
DIALOG_BURST_FALLBACK_TAP_DELAY = 0.6
LEGEND_DIALOG_TAPS = 2
LEGEND_DIALOG_TAP_DELAY = 0.4
DIALOG_BURST_STOP_LABELS = {
    "dream_found",
    "card_reward",
    "legend_choice",
    "choice_screen",
    "flee_screen",
    "return_confirm",
    "team_screen",
    "start_screen",
}

# Start-screen click count. Keep this at 1 so the team screen is recognized
# before clicking the team enter button.
START_TO_TEAM_BURST_TAPS = 1
START_TO_TEAM_TAP_DELAY = 0.5
WAIT_AFTER_TEAM_ENTER_BEFORE_DIALOG = 7.0
POST_CLICK_WAIT = 4.0
REWARD_SETTLE_BEFORE_ACTION = 1.5
SAVE_VISUAL_CHANGE_DEBUG = False
LOG_CLICK_WINDOW = False
CLICK_METHOD = "postmessage"
CLICK_RESTORE_AFTER_ACTION = True
POSTMESSAGE_FALLBACK_SENDINPUT = False

# 识别等待轮询间隔，用在等待“脱逃页/确认弹窗/回首页”等关键状态。

# 旧的 before/after 调试等待轮询间隔。正常快链较少用到，单步调试会用。
VISUAL_CHANGE_POLL_INTERVAL = 0.20

# 无传说快链兜底等待。当前直接快链不再依赖这两个值，只留给以后调试用。

# 无传说快链兜底等待。当前直接快链不再依赖这两个值，只留给以后调试用。

# 无传说快链：点确认后等回到首页/队伍/加载页的最长时间。

# 传说选项：点选项卡后，等对勾出现/可点的短暂停顿。
LEGEND_CONFIRM_DELAY = 0.20

# 点击函数内部固定耗时。一次点击大约是：
# CLICK_MOVE_DELAY + CLICK_ABSOLUTE_MOVE_DELAY + duration + CLICK_AFTER_UP_DELAY。
CLICK_MOVE_DELAY = 0.03
CLICK_ABSOLUTE_MOVE_DELAY = 0.02
CLICK_AFTER_UP_DELAY = 0.03

# 窗口抢前台时的等待。正常游戏已经在前台时不会每次都吃满。
FOCUS_TOP_DELAY = 0.05
FOCUS_FOREGROUND_DELAY = 0.12
FOCUS_RETRY_DELAY = 0.05

# 各状态处理完后下一轮识别的短暂停顿。
INITIAL_ACTION_DELAY = 0.20
DELAY_REWARD_ALREADY_HANDLED = 0.30
DELAY_AFTER_REWARD_ACTION = 0.50
DELAY_AFTER_RETURN_CONFIRM = 0.50
DELAY_AFTER_NO_LEGEND_CHAIN = 0.20
DELAY_CHOICE_ALREADY_HANDLED = 0.30
DELAY_AFTER_FLEE = 0.30
DELAY_AFTER_TEAM_ENTER = 0.50
DELAY_START_ALREADY_HANDLED = 0.30
DELAY_AFTER_START_ENTER = 0.50
DELAY_AFTER_UNKNOWN_BURST = 0.05
DELAY_UNKNOWN_IDLE = 0.30
DELAY_AFTER_LEGEND_CONFIRM = 1


CONFIG_MESSAGES: list[str] = []
CONFIG_BINDINGS = {
    "click_points": {
        "advance": ("CLICK_ADVANCE", "point"),
        "choice_right": ("CLICK_CHOICE_RIGHT", "point"),
        "confirm": ("CLICK_CONFIRM", "point"),
        "retry_top_right": ("CLICK_RETRY_TOP_RIGHT", "point"),
        "start_enter": ("CLICK_START_ENTER", "point"),
        "team_enter": ("CLICK_TEAM_ENTER", "point"),
        "button_text_point": ("BUTTON_TEXT_POINT", "point"),
        "chain_flee": ("CHAIN_FLEE_POINT", "point"),
        "chain_return_confirm": ("CHAIN_RETURN_CONFIRM_POINT", "point"),
        "choice_confirm_y": ("CHOICE_CONFIRM_Y", "unit_float"),
        "team_fallback_match_max_x": ("TEAM_FALLBACK_MATCH_MAX_X", "unit_float"),
        "team_fallback_match_min_y": ("TEAM_FALLBACK_MATCH_MIN_Y", "unit_float"),
    },
    "timing": {
        "live_loop_interval": ("LIVE_LOOP_INTERVAL", "positive_float"),
        "live_log_interval": ("LIVE_LOG_INTERVAL", "nonnegative_float"),
        "post_click_wait": ("POST_CLICK_WAIT", "nonnegative_float"),
        "wait_after_team_enter": ("WAIT_AFTER_TEAM_ENTER_BEFORE_DIALOG", "nonnegative_float"),
        "reward_settle_before_action": ("REWARD_SETTLE_BEFORE_ACTION", "nonnegative_float"),
        "start_to_team_burst_taps": ("START_TO_TEAM_BURST_TAPS", "nonnegative_int"),
        "start_to_team_tap_delay": ("START_TO_TEAM_TAP_DELAY", "nonnegative_float"),
        "dialog_burst_max_taps": ("DIALOG_BURST_MAX_TAPS", "nonnegative_int"),
        "dialog_burst_tap_delay": ("DIALOG_BURST_TAP_DELAY", "nonnegative_float"),
        "dialog_burst_mode": ("DIALOG_BURST_MODE", "dialog_mode"),
        "dialog_burst_rapid_postcheck": ("DIALOG_BURST_RAPID_POSTCHECK", "nonnegative_float"),
        "dialog_burst_fallback_taps": ("DIALOG_BURST_FALLBACK_TAPS", "nonnegative_int"),
        "dialog_burst_fallback_tap_delay": ("DIALOG_BURST_FALLBACK_TAP_DELAY", "nonnegative_float"),
        "legend_dialog_taps": ("LEGEND_DIALOG_TAPS", "nonnegative_int"),
        "legend_dialog_tap_delay": ("LEGEND_DIALOG_TAP_DELAY", "nonnegative_float"),
        "legend_confirm_delay": ("LEGEND_CONFIRM_DELAY", "nonnegative_float"),
        "chain_menu_to_flee_delay": ("CHAIN_MENU_TO_FLEE_DELAY", "nonnegative_float"),
        "chain_flee_to_confirm_delay": ("CHAIN_FLEE_TO_CONFIRM_DELAY", "nonnegative_float"),
        "chain_menu_to_flee_timeout": ("CHAIN_MENU_TO_FLEE_TIMEOUT", "nonnegative_float"),
        "chain_flee_to_confirm_timeout": ("CHAIN_FLEE_TO_CONFIRM_TIMEOUT", "nonnegative_float"),
        "chain_after_confirm_delay": ("CHAIN_AFTER_CONFIRM_DELAY", "nonnegative_float"),
        "fast_click_duration": ("FAST_CLICK_DURATION", "nonnegative_float"),
        "chain_click_duration": ("CHAIN_CLICK_DURATION", "nonnegative_float"),
        "click_move_delay": ("CLICK_MOVE_DELAY", "nonnegative_float"),
        "click_absolute_move_delay": ("CLICK_ABSOLUTE_MOVE_DELAY", "nonnegative_float"),
        "click_after_up_delay": ("CLICK_AFTER_UP_DELAY", "nonnegative_float"),
        "focus_top_delay": ("FOCUS_TOP_DELAY", "nonnegative_float"),
        "focus_foreground_delay": ("FOCUS_FOREGROUND_DELAY", "nonnegative_float"),
        "focus_retry_delay": ("FOCUS_RETRY_DELAY", "nonnegative_float"),
        "visual_change_poll_interval": ("VISUAL_CHANGE_POLL_INTERVAL", "nonnegative_float"),
        "delay_reward_already_handled": ("DELAY_REWARD_ALREADY_HANDLED", "nonnegative_float"),
        "delay_after_reward_action": ("DELAY_AFTER_REWARD_ACTION", "nonnegative_float"),
        "delay_after_return_confirm": ("DELAY_AFTER_RETURN_CONFIRM", "nonnegative_float"),
        "delay_after_no_legend_chain": ("DELAY_AFTER_NO_LEGEND_CHAIN", "nonnegative_float"),
        "delay_choice_already_handled": ("DELAY_CHOICE_ALREADY_HANDLED", "nonnegative_float"),
        "delay_after_flee": ("DELAY_AFTER_FLEE", "nonnegative_float"),
        "delay_after_team_enter": ("DELAY_AFTER_TEAM_ENTER", "nonnegative_float"),
        "delay_start_already_handled": ("DELAY_START_ALREADY_HANDLED", "nonnegative_float"),
        "delay_after_start_enter": ("DELAY_AFTER_START_ENTER", "nonnegative_float"),
        "delay_after_unknown_burst": ("DELAY_AFTER_UNKNOWN_BURST", "nonnegative_float"),
        "delay_unknown_idle": ("DELAY_UNKNOWN_IDLE", "nonnegative_float"),
        "delay_after_legend_confirm": ("DELAY_AFTER_LEGEND_CONFIRM", "nonnegative_float"),
        "click_method": ("CLICK_METHOD", "click_method"),
        "click_restore_after_action": ("CLICK_RESTORE_AFTER_ACTION", "bool"),
        "postmessage_fallback_sendinput": ("POSTMESSAGE_FALLBACK_SENDINPUT", "bool"),
    },
}


def default_user_config() -> dict:
    return {
        "_说明": "坐标都是相对当前截图的比例，左上角是 [0, 0]，右下角是 [1, 1]。时间单位是秒。",
        "_建议": "先只小幅调整一个值。改坏了可以删除本文件，程序会重新生成默认配置。",
        "click_points": {
            "_说明": "常用点击位置。一般只需要改 start_enter/team_enter/advance。",
            "advance": list(CLICK_ADVANCE),
            "choice_right": list(CLICK_CHOICE_RIGHT),
            "confirm": list(CLICK_CONFIRM),
            "retry_top_right": list(CLICK_RETRY_TOP_RIGHT),
            "start_enter": list(CLICK_START_ENTER),
            "team_enter": list(CLICK_TEAM_ENTER),
            "button_text_point": list(BUTTON_TEXT_POINT),
            "chain_flee": list(CHAIN_FLEE_POINT),
            "chain_return_confirm": list(CHAIN_RETURN_CONFIRM_POINT),
            "choice_confirm_y": CHOICE_CONFIRM_Y,
            "team_fallback_match_max_x": TEAM_FALLBACK_MATCH_MAX_X,
            "team_fallback_match_min_y": TEAM_FALLBACK_MATCH_MIN_Y,
        },
        "timing": {
            "_说明": "流程等待和连点参数。机器慢就优先加 wait_after_team_enter、post_click_wait、reward_settle_before_action。",
            "live_loop_interval": LIVE_LOOP_INTERVAL,
            "live_log_interval": LIVE_LOG_INTERVAL,
            "post_click_wait": POST_CLICK_WAIT,
            "wait_after_team_enter": WAIT_AFTER_TEAM_ENTER_BEFORE_DIALOG,
            "reward_settle_before_action": REWARD_SETTLE_BEFORE_ACTION,
            "start_to_team_burst_taps": START_TO_TEAM_BURST_TAPS,
            "start_to_team_tap_delay": START_TO_TEAM_TAP_DELAY,
            "dialog_burst_max_taps": DIALOG_BURST_MAX_TAPS,
            "dialog_burst_tap_delay": DIALOG_BURST_TAP_DELAY,
            "dialog_burst_mode": DIALOG_BURST_MODE,
            "dialog_burst_rapid_postcheck": DIALOG_BURST_RAPID_POSTCHECK,
            "dialog_burst_fallback_taps": DIALOG_BURST_FALLBACK_TAPS,
            "dialog_burst_fallback_tap_delay": DIALOG_BURST_FALLBACK_TAP_DELAY,
            "legend_dialog_taps": LEGEND_DIALOG_TAPS,
            "legend_dialog_tap_delay": LEGEND_DIALOG_TAP_DELAY,
            "legend_confirm_delay": LEGEND_CONFIRM_DELAY,
            "chain_menu_to_flee_delay": CHAIN_MENU_TO_FLEE_DELAY,
            "chain_flee_to_confirm_delay": CHAIN_FLEE_TO_CONFIRM_DELAY,
            "chain_menu_to_flee_timeout": CHAIN_MENU_TO_FLEE_TIMEOUT,
            "chain_flee_to_confirm_timeout": CHAIN_FLEE_TO_CONFIRM_TIMEOUT,
            "chain_after_confirm_delay": CHAIN_AFTER_CONFIRM_DELAY,
            "fast_click_duration": FAST_CLICK_DURATION,
            "chain_click_duration": CHAIN_CLICK_DURATION,
            "click_move_delay": CLICK_MOVE_DELAY,
            "click_absolute_move_delay": CLICK_ABSOLUTE_MOVE_DELAY,
            "click_after_up_delay": CLICK_AFTER_UP_DELAY,
            "focus_top_delay": FOCUS_TOP_DELAY,
            "focus_foreground_delay": FOCUS_FOREGROUND_DELAY,
            "focus_retry_delay": FOCUS_RETRY_DELAY,
            "visual_change_poll_interval": VISUAL_CHANGE_POLL_INTERVAL,
            "delay_reward_already_handled": DELAY_REWARD_ALREADY_HANDLED,
            "delay_after_reward_action": DELAY_AFTER_REWARD_ACTION,
            "delay_after_return_confirm": DELAY_AFTER_RETURN_CONFIRM,
            "delay_after_no_legend_chain": DELAY_AFTER_NO_LEGEND_CHAIN,
            "delay_choice_already_handled": DELAY_CHOICE_ALREADY_HANDLED,
            "delay_after_flee": DELAY_AFTER_FLEE,
            "delay_after_team_enter": DELAY_AFTER_TEAM_ENTER,
            "delay_start_already_handled": DELAY_START_ALREADY_HANDLED,
            "delay_after_start_enter": DELAY_AFTER_START_ENTER,
            "delay_after_unknown_burst": DELAY_AFTER_UNKNOWN_BURST,
            "delay_unknown_idle": DELAY_UNKNOWN_IDLE,
            "delay_after_legend_confirm": DELAY_AFTER_LEGEND_CONFIRM,
            "click_method": CLICK_METHOD,
            "click_restore_after_action": CLICK_RESTORE_AFTER_ACTION,
            "postmessage_fallback_sendinput": POSTMESSAGE_FALLBACK_SENDINPUT,
        },
    }


def write_default_config(path: Path, overwrite: bool = False) -> Path:
    if path.exists() and not overwrite:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(default_user_config(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def _coerce_config_value(value: object, kind: str, label: str) -> object:
    if kind == "point":
        if not isinstance(value, (list, tuple)) or len(value) != 2:
            raise ValueError(f"{label} must be [x, y]")
        x = float(value[0])
        y = float(value[1])
        if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
            raise ValueError(f"{label} point values must be between 0 and 1")
        return (x, y)
    if kind == "unit_float":
        number = float(value)
        if not 0.0 <= number <= 1.0:
            raise ValueError(f"{label} must be between 0 and 1")
        return number
    if kind == "positive_float":
        number = float(value)
        if number <= 0:
            raise ValueError(f"{label} must be greater than 0")
        return number
    if kind == "nonnegative_float":
        number = float(value)
        if number < 0:
            raise ValueError(f"{label} must be >= 0")
        return number
    if kind == "nonnegative_int":
        number = int(value)
        if number < 0:
            raise ValueError(f"{label} must be >= 0")
        return number
    if kind == "dialog_mode":
        text = str(value)
        if text not in {"rapid", "checked"}:
            raise ValueError(f"{label} must be rapid or checked")
        return text
    if kind == "bool":
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            text = value.strip().lower()
            if text in {"1", "true", "yes", "on"}:
                return True
            if text in {"0", "false", "no", "off"}:
                return False
        raise ValueError(f"{label} must be true or false")
    if kind == "click_method":
        text = str(value)
        if text not in {"sendinput", "postmessage"}:
            raise ValueError(f"{label} must be sendinput or postmessage")
        return text
    raise ValueError(f"unknown config type {kind}")


def apply_user_config(path: Path, create_missing: bool = True) -> None:
    if create_missing and not path.exists():
        try:
            write_default_config(path)
            CONFIG_MESSAGES.append(f"created default config: {path}")
        except OSError as exc:
            CONFIG_MESSAGES.append(f"warning: failed to create config {path}: {exc}")
            return
    if not path.exists():
        CONFIG_MESSAGES.append(f"user config disabled or missing: {path}")
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        CONFIG_MESSAGES.append(f"warning: failed to read config {path}: {exc}")
        return
    if not isinstance(data, dict):
        CONFIG_MESSAGES.append(f"warning: config root must be an object: {path}")
        return

    applied: list[str] = []
    for section, bindings in CONFIG_BINDINGS.items():
        section_data = data.get(section, {})
        if section_data is None:
            continue
        if not isinstance(section_data, dict):
            CONFIG_MESSAGES.append(f"warning: config section {section} must be an object")
            continue
        for key, value in section_data.items():
            if key.startswith("_"):
                continue
            binding = bindings.get(key)
            if not binding:
                CONFIG_MESSAGES.append(f"warning: unknown config key ignored: {section}.{key}")
                continue
            global_name, kind = binding
            try:
                globals()[global_name] = _coerce_config_value(value, kind, f"{section}.{key}")
            except Exception as exc:
                CONFIG_MESSAGES.append(f"warning: invalid config value ignored: {section}.{key}: {exc}")
                continue
            applied.append(f"{section}.{key}")
    CONFIG_MESSAGES.append(f"loaded config: {path} ({len(applied)} values applied)")


VK_CODES = {
    "esc": 0x1B,
    "end": 0x23,
    "f8": 0x77,
    "f9": 0x78,
    "f10": 0x79,
    "f12": 0x7B,
    "pause": 0x13,
}


class CznDetector:
    def __init__(self, template_dir: Path | None = None, wide_match_scales: bool = False) -> None:
        visible_templates = app_install_dir() / "templates"
        bundled_templates = app_base_dir() / "templates"
        self.template_dir = template_dir or self._default_template_dir(visible_templates, bundled_templates)
        self.match_scale_factors = WIDE_MATCH_SCALE_FACTORS if wide_match_scales else FAST_MATCH_SCALE_FACTORS
        self._warned_aspect_sizes: set[tuple[int, int]] = set()
        self._scaled_template_cache: dict[tuple[int, float], tuple[int, int, np.ndarray]] = {}
        self.legend_template = self._load_template("legend_word.jpg")
        self.legend_wide_template = self._load_template("legend_word_wide.jpg")
        self.dream_template = self._load_template("dream_border_title.jpg")
        self.card_reward_template = self._load_template("card_reward_title.jpg")
        self.start_enter_template = self._load_template("start_enter_button.jpg")
        self.choice_glow_template = self._load_template("choice_bottom_glow.jpg")
        self.top_right_menu_template = self._load_template("combat_top_right_menu.jpg")
        self.flee_button_template = self._load_template("flee_button.jpg")
        self.team_enter_template = self._load_template("team_enter_button.jpg")
        self.stage_enter_template = self._load_optional_template("stage_enter_button.jpg")
        self.return_confirm_template = self._load_template("return_confirm_button.jpg")

    def _default_template_dir(self, visible_templates: Path, bundled_templates: Path) -> Path:
        required = "legend_word.jpg"
        if visible_templates.is_dir() and (visible_templates / required).exists():
            return visible_templates
        return bundled_templates

    def _load_template(self, name: str) -> np.ndarray:
        path = self.template_dir / name
        image = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise FileNotFoundError(f"template not found or unreadable: {path}")
        return image

    def _load_optional_template(self, name: str) -> np.ndarray | None:
        path = self.template_dir / name
        if not path.exists():
            return None
        image = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
        if image is None:
            print(f"warning: optional template unreadable: {path}", flush=True)
        return image

    def detect(self, frame_bgr: np.ndarray) -> DetectionState:
        frame_gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        h, w = frame_bgr.shape[:2]
        self._warn_if_unexpected_aspect(w, h)
        dream = self._match_in_roi(
            frame_gray,
            self.dream_template,
            CARD_REWARD_ROI,
            "dream_border_title",
            threshold=0.78,
        )
        if dream:
            return detection_state(dream_card=dream)

        card_reward = self._match_in_roi(
            frame_gray,
            self.card_reward_template,
            Box(0.38, 0.06, 0.62, 0.20),
            "card_reward_title",
            threshold=0.72,
        )
        if card_reward:
            top_right_menu = self._match_in_roi(
                frame_gray,
                self.top_right_menu_template,
                Box(0.85, 0.00, 0.995, 0.11),
                "top_right_menu",
                threshold=0.70,
            )
            return detection_state(card_reward=card_reward, top_right_menu=top_right_menu)

        return_confirm = self._match_in_roi(
            frame_gray,
            self.return_confirm_template,
            Box(0.40, 0.56, 0.86, 0.76),
            "return_confirm_button",
            threshold=0.78,
        )
        if return_confirm:
            return detection_state(return_confirm=return_confirm)

        legend = self._best_match(
            frame_gray=frame_gray,
            templates=[
                ("legend_word", self.legend_template),
                ("legend_word_wide", self.legend_wide_template),
            ],
            roi=CHOICE_RIGHT_ROI,
            threshold=0.72,
        )
        if legend:
            return detection_state(legend_choice=legend)

        choice_card = self._detect_choice_anchors(frame_gray)
        if choice_card:
            return detection_state(choice_card=choice_card)

        flee_button = self._match_in_roi(
            frame_gray,
            self.flee_button_template,
            Box(0.70, 0.82, 0.995, 0.995),
            "flee_button",
            threshold=0.72,
        )
        if flee_button:
            return detection_state(flee_button=flee_button)

        team_enter = self._match_in_roi(
            frame_gray,
            self.team_enter_template,
            Box(0.74, 0.84, 0.995, 0.995),
            "team_enter_button",
            threshold=0.74,
        )
        if team_enter:
            return detection_state(team_enter=team_enter)

        if self.stage_enter_template is not None:
            stage_enter = self._match_in_roi(
                frame_gray,
                self.stage_enter_template,
                Box(0.66, 0.84, 0.995, 0.995),
                "stage_enter_button",
                threshold=0.72,
            )
            if stage_enter:
                return detection_state(start_screen=stage_enter)

        start_screen = self._match_in_roi(
            frame_gray,
            self.start_enter_template,
            Box(0.70, 0.82, 0.995, 0.99),
            "start_enter_button",
            threshold=0.72,
        )
        return detection_state(start_screen=start_screen)

    def _detect_choice_anchors(self, frame_gray: np.ndarray) -> MatchResult | None:
        h, w = frame_gray.shape[:2]
        glow_rois = [
            Box(0.18, 0.84, 0.33, 0.998),
            Box(0.44, 0.84, 0.59, 0.998),
            Box(0.70, 0.84, 0.85, 0.998),
        ]
        matches: list[MatchResult] = []
        for index, roi in enumerate(glow_rois, start=1):
            match = self._match_in_roi(
                frame_gray,
                self.choice_glow_template,
                roi,
                f"choice_glow_{index}",
                threshold=0.60,
            )
            if match:
                matches.append(match)
        if len(matches) < 3:
            return None

        x1 = min(match.box[0] for match in matches)
        y1 = min(match.box[1] for match in matches)
        x2 = max(match.box[2] for match in matches)
        y2 = max(match.box[3] for match in matches)
        score = min(match.score for match in matches)
        return MatchResult("choice_glows", score, (x1, y1, x2, y2))

    def _best_match(
        self,
        frame_gray: np.ndarray,
        templates: list[tuple[str, np.ndarray]],
        roi: Box,
        threshold: float,
    ) -> MatchResult | None:
        best: MatchResult | None = None
        for name, template in templates:
            match = self._match_in_roi(frame_gray, template, roi, name, threshold)
            if match and (best is None or match.score > best.score):
                best = match
        return best

    def _match_in_roi(
        self,
        frame_gray: np.ndarray,
        template_gray: np.ndarray,
        roi: Box,
        name: str,
        threshold: float,
    ) -> MatchResult | None:
        h, w = frame_gray.shape[:2]
        x1, y1, x2, y2 = roi.to_pixels(w, h)
        haystack = frame_gray[y1:y2, x1:x2]
        if haystack.size == 0:
            return None

        base_scale = self._template_scale(w, h)
        best_score = -1.0
        best_loc = (0, 0)
        best_size = (0, 0)
        for scale_factor in self.match_scale_factors:
            tw, th, template = self._scaled_template(template_gray, base_scale, scale_factor)
            if tw >= haystack.shape[1] or th >= haystack.shape[0]:
                continue
            score_map = cv2.matchTemplate(haystack, template, cv2.TM_CCOEFF_NORMED)
            _, max_score, _, max_loc = cv2.minMaxLoc(score_map)
            if max_score > best_score:
                best_score = float(max_score)
                best_loc = max_loc
                best_size = (tw, th)

        max_score = best_score
        if max_score < threshold:
            return None
        mx, my = best_loc
        tw, th = best_size
        return MatchResult(
            name=name,
            score=float(max_score),
            box=(x1 + mx, y1 + my, x1 + mx + tw, y1 + my + th),
        )

    def _scaled_template(
        self,
        template_gray: np.ndarray,
        base_scale: float,
        scale_factor: float,
    ) -> tuple[int, int, np.ndarray]:
        scale = base_scale * scale_factor
        key = (id(template_gray), round(scale, 6))
        cached = self._scaled_template_cache.get(key)
        if cached is not None:
            return cached

        tw = max(8, int(round(template_gray.shape[1] * scale)))
        th = max(8, int(round(template_gray.shape[0] * scale)))
        resized = cv2.resize(template_gray, (tw, th), interpolation=cv2.INTER_AREA)
        cached = (tw, th, resized)
        self._scaled_template_cache[key] = cached
        return cached

    def _template_scale(self, width: int, height: int) -> float:
        # For same-aspect fullscreen captures, 4K/2K/1080P share one uniform UI scale.
        return min(width / BASE_W, height / BASE_H)

    def _warn_if_unexpected_aspect(self, width: int, height: int) -> None:
        size = (width, height)
        if size in self._warned_aspect_sizes:
            return
        self._warned_aspect_sizes.add(size)
        aspect = width / max(1, height)
        if abs(aspect - BASE_ASPECT) > ASPECT_TOLERANCE:
            print(
                f"warning: capture aspect {width}x{height} differs from base {BASE_W}x{BASE_H}; "
                "same-ratio 16:9 fullscreen captures are expected.",
                flush=True,
            )


def read_image(path: Path) -> np.ndarray:
    frame = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        raise FileNotFoundError(f"could not read image: {path}")
    return frame


def iter_video_frames(path: Path, every_sec: float) -> Iterable[tuple[float, np.ndarray]]:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise FileNotFoundError(f"could not open video: {path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration = frame_count / fps if frame_count else 0.0
    t = 0.0
    while t <= duration:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, frame = cap.read()
        if not ok:
            break
        yield t, frame
        t += every_sec
    cap.release()


def annotate(frame: np.ndarray, state: DetectionState) -> np.ndarray:
    out = frame.copy()
    for match, color in (
        (state.legend_choice, (0, 215, 255)),
        (state.choice_card, (255, 160, 0)),
        (state.return_confirm, (0, 165, 255)),
        (state.start_screen, (80, 255, 255)),
        (state.top_right_menu, (255, 120, 255)),
        (state.flee_button, (0, 140, 255)),
        (state.team_enter, (120, 255, 120)),
        (state.card_reward, (255, 255, 255)),
        (state.dream_card, (0, 255, 0)),
    ):
        if not match:
            continue
        x1, y1, x2, y2 = match.box
        cv2.rectangle(out, (x1, y1), (x2, y2), color, 4)
        cv2.putText(
            out,
            f"{match.name} {match.score:.3f}",
            (x1, max(30, y1 - 12)),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.1,
            color,
            3,
            cv2.LINE_AA,
        )
    return out


def save_image(path: Path, frame: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 94])
    if not ok:
        raise RuntimeError(f"failed to encode image: {path}")
    buf.tofile(str(path))


def run_image(detector: CznDetector, image_path: Path, out_dir: Path | None) -> None:
    frame = read_image(image_path)
    state = detector.detect(frame)
    print_state(image_path.name, state)
    if out_dir:
        save_image(out_dir / f"{image_path.stem}_annotated.jpg", annotate(frame, state))


def run_video(detector: CznDetector, video_path: Path, every_sec: float, out_dir: Path | None) -> None:
    for t, frame in iter_video_frames(video_path, every_sec):
        state = detector.detect(frame)
        if state.label != "unknown":
            print_state(f"{t:7.2f}s", state)
            if out_dir:
                save_image(out_dir / f"video_{t:07.2f}s_{state.label}.jpg", annotate(frame, state))


def print_state(prefix: str, state: DetectionState) -> None:
    parts = [prefix, state.label]
    if state.legend_choice:
        parts.append(f"legend={state.legend_choice.score:.3f}@{state.legend_choice.center}")
    if state.choice_card:
        parts.append(f"choice={state.choice_card.score:.3f}@{state.choice_card.center}")
    if state.return_confirm:
        parts.append(f"return={state.return_confirm.score:.3f}@{state.return_confirm.center}")
    if state.start_screen:
        parts.append(f"start={state.start_screen.score:.3f}@{state.start_screen.center}")
    if state.top_right_menu:
        parts.append(f"menu={state.top_right_menu.score:.3f}@{state.top_right_menu.center}")
    if state.flee_button:
        parts.append(f"flee={state.flee_button.score:.3f}@{state.flee_button.center}")
    if state.team_enter:
        parts.append(f"team={state.team_enter.score:.3f}@{state.team_enter.center}")
    if state.card_reward:
        parts.append(f"reward={state.card_reward.score:.3f}@{state.card_reward.center}")
    if state.dream_card:
        parts.append(f"dream={state.dream_card.score:.3f}@{state.dream_card.center}")
    try:
        print(" | ".join(parts), flush=True)
    except OSError:
        pass


def start_match_looks_like_team_fallback(state: DetectionState, frame_shape: tuple[int, ...]) -> bool:
    if not state.start_screen:
        return False
    if state.start_screen.name == "stage_enter_button":
        return False
    h, w = frame_shape[:2]
    cx, cy = state.start_screen.center
    return (cx / max(1, w)) <= TEAM_FALLBACK_MATCH_MAX_X and (cy / max(1, h)) >= TEAM_FALLBACK_MATCH_MIN_Y


def _monitor_meta(monitor_index: int) -> dict:
    import mss

    mss_cls = getattr(mss, "MSS", None) or getattr(mss, "mss")
    with mss_cls() as sct:
        if monitor_index < 0 or monitor_index >= len(sct.monitors):
            raise ValueError(f"monitor index {monitor_index} is out of range; available: 0..{len(sct.monitors) - 1}")
        monitor = sct.monitors[monitor_index]
    return monitor


def _screen_shot_mss(monitor_index: int) -> tuple[np.ndarray, dict]:
    import mss

    mss_cls = getattr(mss, "MSS", None) or getattr(mss, "mss")
    with mss_cls() as sct:
        if monitor_index < 0 or monitor_index >= len(sct.monitors):
            raise ValueError(f"monitor index {monitor_index} is out of range; available: 0..{len(sct.monitors) - 1}")
        monitor = sct.monitors[monitor_index]
        raw = np.array(sct.grab(monitor))
    return cv2.cvtColor(raw, cv2.COLOR_BGRA2BGR), monitor


def _screen_shot_window_mss(window_title: str) -> tuple[np.ndarray, dict]:
    import mss

    hwnd = find_window_by_title(window_title)
    if not ensure_window_not_minimized(hwnd, window_title):
        raise RuntimeError(f"window is minimized and could not be restored without activation: {window_title!r}")
    rect = window_client_rect(hwnd)
    if rect is None:
        raise RuntimeError(f"window is minimized or has no capturable client area: {window_title!r}")
    left, top, width, height = rect
    monitor = {
        "left": left,
        "top": top,
        "width": width,
        "height": height,
        "hwnd": hwnd,
        "pid": _window_pid(hwnd),
        "title": _window_text(hwnd),
        "source": "window",
    }
    mss_cls = getattr(mss, "MSS", None) or getattr(mss, "mss")
    with mss_cls() as sct:
        raw = np.array(sct.grab({"left": left, "top": top, "width": width, "height": height}))
    return cv2.cvtColor(raw, cv2.COLOR_BGRA2BGR), monitor


def _screen_shot_window_printwindow(window_title: str) -> tuple[np.ndarray, dict]:
    hwnd = find_window_by_title(window_title)
    if not ensure_window_not_minimized(hwnd, window_title):
        raise RuntimeError(f"window is minimized and could not be restored without activation: {window_title!r}")
    rect = window_client_rect(hwnd)
    if rect is None:
        raise RuntimeError(f"window is minimized or has no capturable client area: {window_title!r}")
    left, top, width, height = rect
    outer = window_outer_rect(hwnd)
    src_x = max(0, left - outer[0]) if outer else 0
    src_y = max(0, top - outer[1]) if outer else 0
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32
    hdc_window = user32.GetWindowDC(hwnd)
    if not hdc_window:
        raise RuntimeError(f"GetWindowDC failed for window: {window_title!r}")
    hdc_mem = gdi32.CreateCompatibleDC(hdc_window)
    hbmp = gdi32.CreateCompatibleBitmap(hdc_window, width, height)
    old_obj = gdi32.SelectObject(hdc_mem, hbmp)

    class BitmapInfoHeader(ctypes.Structure):
        _fields_ = (
            ("biSize", ctypes.c_uint32),
            ("biWidth", ctypes.c_long),
            ("biHeight", ctypes.c_long),
            ("biPlanes", ctypes.c_uint16),
            ("biBitCount", ctypes.c_uint16),
            ("biCompression", ctypes.c_uint32),
            ("biSizeImage", ctypes.c_uint32),
            ("biXPelsPerMeter", ctypes.c_long),
            ("biYPelsPerMeter", ctypes.c_long),
            ("biClrUsed", ctypes.c_uint32),
            ("biClrImportant", ctypes.c_uint32),
        )

    class BitmapInfo(ctypes.Structure):
        _fields_ = (("bmiHeader", BitmapInfoHeader), ("bmiColors", ctypes.c_uint32 * 3))

    try:
        # Match ok-script's BitBlt_RenderFull flow: ask DWM to render full
        # content, then BitBlt the client area from the window DC.
        user32.PrintWindow(hwnd, hdc_window, 0x00000002)
        if not gdi32.BitBlt(hdc_mem, 0, 0, width, height, hdc_window, src_x, src_y, 0x00CC0020):
            raise RuntimeError(f"BitBlt failed for window: {window_title!r}")
        bmi = BitmapInfo()
        bmi.bmiHeader.biSize = ctypes.sizeof(BitmapInfoHeader)
        bmi.bmiHeader.biWidth = width
        bmi.bmiHeader.biHeight = -height
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = 0
        buffer = np.empty((height, width, 4), dtype=np.uint8)
        scan_lines = gdi32.GetDIBits(
            hdc_mem,
            hbmp,
            0,
            height,
            buffer.ctypes.data_as(ctypes.c_void_p),
            ctypes.byref(bmi),
            0,
        )
        if scan_lines != height:
            raise RuntimeError(f"GetDIBits returned {scan_lines}/{height} lines")
    finally:
        gdi32.SelectObject(hdc_mem, old_obj)
        gdi32.DeleteObject(hbmp)
        gdi32.DeleteDC(hdc_mem)
        user32.ReleaseDC(hwnd, hdc_window)

    monitor = {
        "left": left,
        "top": top,
        "width": width,
        "height": height,
        "hwnd": hwnd,
        "pid": _window_pid(hwnd),
        "title": _window_text(hwnd),
        "source": "printwindow",
    }
    return cv2.cvtColor(buffer, cv2.COLOR_BGRA2BGR), monitor


def _screen_shot_dxgi(monitor_index: int) -> tuple[np.ndarray, dict]:
    import dxcam

    output_idx = max(0, monitor_index - 1)
    camera = _DXGI_CAMERAS.get(output_idx)
    if camera is None:
        camera = dxcam.create(output_idx=output_idx, output_color="BGR")
        camera.start(target_fps=20, video_mode=True)
        _DXGI_CAMERAS[output_idx] = camera
        time.sleep(0.35)
    frame = None
    deadline = time.time() + 2.0
    while time.time() < deadline:
        frame = camera.get_latest_frame()
        if frame is not None:
            break
        time.sleep(0.03)
    if frame is None:
        frame = camera.grab()
    if frame is None:
        raise RuntimeError("DXGI capture did not return a frame")
    return frame.copy(), _monitor_meta(monitor_index)


def screen_shot(
    monitor_index: int,
    capture_method: str = "dxgi",
    window_title: str | None = None,
) -> tuple[np.ndarray, dict]:
    if window_title:
        if capture_method in {"printwindow", "bitblt-renderfull"}:
            return _screen_shot_window_printwindow(window_title)
        return _screen_shot_window_mss(window_title)
    if capture_method == "dxgi":
        try:
            return _screen_shot_dxgi(monitor_index)
        except Exception as exc:
            print(f"DXGI capture failed, falling back to mss: {exc}", flush=True)
            return _screen_shot_mss(monitor_index)
    if capture_method == "mss":
        return _screen_shot_mss(monitor_index)
    raise ValueError(f"unknown capture method: {capture_method}")


def visual_diff_score(before: np.ndarray, after: np.ndarray) -> float:
    if before.shape[:2] != after.shape[:2]:
        return 999.0
    small_before = cv2.resize(before, (320, 180), interpolation=cv2.INTER_AREA)
    small_after = cv2.resize(after, (320, 180), interpolation=cv2.INTER_AREA)
    gray_before = cv2.cvtColor(small_before, cv2.COLOR_BGR2GRAY)
    gray_after = cv2.cvtColor(small_after, cv2.COLOR_BGR2GRAY)
    return float(np.mean(cv2.absdiff(gray_before, gray_after)))


def roi_visual_diff_score(before: np.ndarray, after: np.ndarray, roi: Box) -> float:
    if before.shape[:2] != after.shape[:2]:
        return 999.0
    h, w = before.shape[:2]
    x1, y1, x2, y2 = roi.to_pixels(w, h)
    return visual_diff_score(before[y1:y2, x1:x2], after[y1:y2, x1:x2])


def choice_confirm_point_for(choice_point: tuple[int, int], frame_shape: tuple[int, ...]) -> tuple[int, int]:
    height, width = frame_shape[:2]
    x, _ = choice_point
    if x < width * 0.37:
        confirm_x = int(width * 0.238)
    elif x < width * 0.63:
        confirm_x = int(width * 0.500)
    else:
        confirm_x = int(width * 0.760)
    return confirm_x, int(height * CHOICE_CONFIRM_Y)


def wait_visual_change(
    detector: CznDetector,
    before_frame: np.ndarray,
    monitor_index: int,
    capture_method: str,
    window_title: str | None,
    stop_keys: list[str],
    stop_file: Path | None,
    timeout: float,
    threshold: float = 2.0,
    action_name: str = "action",
    expected_labels: set[str] | None = None,
) -> None:
    before_state = detector.detect(before_frame)
    after_path: Path | None = None
    if SAVE_VISUAL_CHANGE_DEBUG:
        debug_dir = Path.cwd() / "debug_live"
        stamp = time.strftime("%H%M%S")
        before_path = debug_dir / f"{stamp}_{action_name}_before.jpg"
        after_path = debug_dir / f"{stamp}_{action_name}_after.jpg"
        save_image(before_path, annotate(before_frame, before_state))
    deadline = time.time() + timeout
    best_score = 0.0
    best_roi_score = 0.0
    after_frame = before_frame
    after_state = before_state
    while time.time() < deadline:
        if stop_requested(stop_keys, stop_file):
            return
        time.sleep(VISUAL_CHANGE_POLL_INTERVAL)
        after_frame, _ = screen_shot(monitor_index, capture_method, window_title)
        after_state = detector.detect(after_frame)
        score = visual_diff_score(before_frame, after_frame)
        roi_score = roi_visual_diff_score(before_frame, after_frame, Box(0.0, 0.60, 1.0, 1.0))
        best_score = max(best_score, score)
        best_roi_score = max(best_roi_score, roi_score)
        expected_hit = expected_labels is not None and after_state.label in expected_labels
        state_changed = after_state.label != before_state.label
        visual_changed = score >= threshold or roi_score >= threshold
        if expected_hit or (expected_labels is None and (state_changed or visual_changed)):
            if after_path:
                save_image(after_path, annotate(after_frame, after_state))
            status = "expected" if expected_hit else "changed"
            saved = f", saved={after_path.name}" if after_path else ""
            print(
                f"after click {status}: state {before_state.label}->{after_state.label}, "
                f"diff={score:.2f}, bottom_diff={roi_score:.2f}{saved}",
                flush=True,
            )
            return
    if after_path:
        save_image(after_path, annotate(after_frame, after_state))
    saved = f", saved={after_path.name}" if after_path else ""
    expected = f", expected={','.join(sorted(expected_labels))}" if expected_labels else ""
    print(
        f"HIGH RISK: after click timeout/unexpected: state {before_state.label}->{after_state.label}, "
        f"best_diff={best_score:.2f}, best_bottom_diff={best_roi_score:.2f}{expected}{saved}",
        flush=True,
    )


def wait_for_detected_state(
    detector: CznDetector,
    monitor_index: int,
    capture_method: str,
    window_title: str | None,
    stop_keys: list[str],
    stop_file: Path | None,
    expected_labels: set[str],
    timeout: float,
    action_name: str,
    *,
    high_risk_on_timeout: bool = True,
) -> tuple[np.ndarray, dict, DetectionState] | None:
    deadline = time.time() + timeout
    last_state: DetectionState | None = None
    poll_count = 0
    while time.time() < deadline:
        if sleep_interruptible(VISUAL_CHANGE_POLL_INTERVAL, stop_keys, stop_file):
            return None
        frame, monitor = screen_shot(monitor_index, capture_method, window_title)
        state = detector.detect(frame)
        poll_count += 1
        last_state = state
        if state.label in expected_labels:
            print(
                f"fast wait ok: action={action_name}, state={state.label}, "
                f"polls={poll_count}, elapsed={timeout - max(0.0, deadline - time.time()):.1f}s"
            )
            return frame, monitor, state

    level = "HIGH RISK: " if high_risk_on_timeout else ""
    current = last_state.label if last_state else "none"
    expected = ",".join(sorted(expected_labels))
    print(
        f"{level}fast wait timeout: action={action_name}, current={current}, "
        f"expected={expected}, timeout={timeout:.1f}s, polls={poll_count}"
    )
    return None


def fast_advance_unknown(
    detector: CznDetector,
    monitor: dict,
    monitor_index: int,
    capture_method: str,
    window_title: str | None,
    stop_keys: list[str],
    stop_file: Path | None,
    act: bool,
    max_taps: int = DIALOG_BURST_MAX_TAPS,
    tap_delay: float = DIALOG_BURST_TAP_DELAY,
    mode: str = DIALOG_BURST_MODE,
) -> int:
    if stop_requested(stop_keys, stop_file):
        return 0
    print_action(f"advance/continue burst x{max_taps} mode={mode}", CLICK_ADVANCE, act)
    if act and mode == "rapid":
        clicks = rapid_click_norm(
            CLICK_ADVANCE,
            monitor,
            count=max_taps,
            duration=FAST_CLICK_DURATION,
            interval=tap_delay,
            stop_keys=stop_keys,
            stop_file=stop_file,
        )
        waited = wait_for_detected_state(
            detector,
            monitor_index,
            capture_method,
            window_title,
            stop_keys,
            stop_file,
            DIALOG_BURST_STOP_LABELS,
            max(DIALOG_BURST_RAPID_POSTCHECK, tap_delay * 2),
            "dialog_burst_rapid_postcheck",
            high_risk_on_timeout=True,
        )
        if waited:
            _, _, state = waited
            print(f"dialog rapid burst postcheck: reached {state.label} after {clicks} taps.")
            return clicks
        if stop_requested(stop_keys, stop_file):
            print("dialog rapid burst postcheck stopped; skip fallback clicks.")
            return clicks

        print(
            f"dialog rapid burst fallback: no next state after {clicks} rapid taps; "
            f"switching to checked fallback x{DIALOG_BURST_FALLBACK_TAPS}."
        )
        clicks += checked_dialog_advance(
            detector,
            monitor,
            monitor_index,
            capture_method,
            window_title,
            stop_keys,
            stop_file,
            act,
            max_taps=DIALOG_BURST_FALLBACK_TAPS,
            tap_delay=DIALOG_BURST_FALLBACK_TAP_DELAY,
            prefix="dialog fallback",
        )
        return clicks

    return checked_dialog_advance(
        detector,
        monitor,
        monitor_index,
        capture_method,
        window_title,
        stop_keys,
        stop_file,
        act,
        max_taps=max_taps,
        tap_delay=tap_delay,
        prefix="dialog burst",
    )


def checked_dialog_advance(
    detector: CznDetector,
    monitor: dict,
    monitor_index: int,
    capture_method: str,
    window_title: str | None,
    stop_keys: list[str],
    stop_file: Path | None,
    act: bool,
    max_taps: int,
    tap_delay: float,
    prefix: str,
) -> int:
    clicks = 0
    for i in range(max_taps):
        print_action(f"{prefix} {i + 1}/{max_taps}", CLICK_ADVANCE, act)
        if act:
            click_norm(CLICK_ADVANCE, monitor, duration=FAST_CLICK_DURATION)
            clicks += 1
        if sleep_interruptible(tap_delay, stop_keys, stop_file):
            return clicks
        if act:
            frame, _ = screen_shot(monitor_index, capture_method, window_title)
            state = detector.detect(frame)
            print_state(f"{prefix} {i + 1}/{max_taps}", state)
            if state.label in DIALOG_BURST_STOP_LABELS:
                print(f"{prefix} stopped early: reached {state.label} after {clicks} taps.")
                return clicks
    if act:
        print(
            f"HIGH RISK: {prefix} exhausted: taps={clicks}, state still unknown or not recognized. "
            "Possible causes: slow loading, stale screenshot, wrong monitor/resolution, or dialog timing mismatch."
        )
    return clicks


def fast_start_to_team(
    monitor: dict,
    stop_keys: list[str],
    stop_file: Path | None,
    act: bool,
    first_point: tuple[int, int] | None,
    max_taps: int = START_TO_TEAM_BURST_TAPS,
    tap_delay: float = START_TO_TEAM_TAP_DELAY,
) -> int:
    clicks = 0
    for i in range(max_taps):
        if stop_requested(stop_keys, stop_file):
            return clicks
        if i == 0 and first_point is not None:
            print_action(f"start -> team quick tap {i + 1}/{max_taps}", CLICK_START_ENTER, act)
            if act:
                click_frame_point(first_point, monitor, duration=FAST_CLICK_DURATION)
                clicks += 1
        else:
            print_action(f"start -> team quick tap {i + 1}/{max_taps}", CLICK_START_ENTER, act)
            if act:
                click_norm(CLICK_START_ENTER, monitor, duration=FAST_CLICK_DURATION)
                clicks += 1
        if sleep_interruptible(tap_delay, stop_keys, stop_file):
            return clicks
    return clicks


def fast_abandon_no_legend(
    detector: CznDetector,
    frame: np.ndarray,
    monitor: dict,
    monitor_index: int,
    capture_method: str,
    window_title: str | None,
    stop_keys: list[str],
    stop_file: Path | None,
    act: bool,
) -> int:
    clicks = 0
    state = detector.detect(frame)
    retry_point = state.top_right_menu.center if state.top_right_menu else None
    print_action("no legend chain: click top-right menu", CLICK_RETRY_TOP_RIGHT, act)
    if act:
        if retry_point:
            click_frame_point(retry_point, monitor, duration=CHAIN_CLICK_DURATION)
        else:
            click_norm(CLICK_RETRY_TOP_RIGHT, monitor, duration=CHAIN_CLICK_DURATION)
        clicks += 1

    flee_state: DetectionState | None = None
    flee_monitor = monitor
    if act:
        waited = wait_for_detected_state(
            detector,
            monitor_index,
            capture_method,
            window_title,
            stop_keys,
            stop_file,
            {"flee_screen"},
            CHAIN_MENU_TO_FLEE_TIMEOUT,
            "no_legend_menu_to_flee",
        )
        if waited:
            _, flee_monitor, flee_state = waited
    elif sleep_interruptible(CHAIN_MENU_TO_FLEE_DELAY, stop_keys, stop_file):
        return clicks

    if act:
        if flee_state and flee_state.flee_button:
            flee_point = flee_state.flee_button.point_at(0.72, 0.50)
            print_action(f"no legend chain: click detected flee at {flee_point}", CHAIN_FLEE_POINT, act)
            click_frame_point(flee_point, flee_monitor, duration=CHAIN_CLICK_DURATION)
        else:
            print_action("no legend chain: click fixed flee fallback", CHAIN_FLEE_POINT, act)
            click_norm(CHAIN_FLEE_POINT, monitor, duration=CHAIN_CLICK_DURATION)
        clicks += 1
    else:
        print_action("no legend chain: click fixed flee", CHAIN_FLEE_POINT, act)

    confirm_state: DetectionState | None = None
    confirm_monitor = monitor
    if act:
        waited = wait_for_detected_state(
            detector,
            monitor_index,
            capture_method,
            window_title,
            stop_keys,
            stop_file,
            {"return_confirm"},
            CHAIN_FLEE_TO_CONFIRM_TIMEOUT,
            "no_legend_flee_to_confirm",
        )
        if waited:
            _, confirm_monitor, confirm_state = waited
    elif sleep_interruptible(CHAIN_FLEE_TO_CONFIRM_DELAY, stop_keys, stop_file):
        return clicks

    if act:
        if confirm_state and confirm_state.return_confirm:
            confirm_point = confirm_state.return_confirm.point_at(0.68, 0.50)
            print_action(f"no legend chain: click detected confirm at {confirm_point}", CHAIN_RETURN_CONFIRM_POINT, act)
            click_frame_point(confirm_point, confirm_monitor, duration=CHAIN_CLICK_DURATION)
        else:
            print_action("no legend chain: click fixed confirm fallback", CHAIN_RETURN_CONFIRM_POINT, act)
            click_norm(CHAIN_RETURN_CONFIRM_POINT, monitor, duration=CHAIN_CLICK_DURATION)
        clicks += 1
        if sleep_interruptible(CHAIN_AFTER_CONFIRM_DELAY, stop_keys, stop_file):
            return clicks
    else:
        print_action("no legend chain: click fixed confirm", CHAIN_RETURN_CONFIRM_POINT, act)
    return clicks


class MouseInput(ctypes.Structure):
    _fields_ = (
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    )


class InputUnion(ctypes.Union):
    _fields_ = (("mi", MouseInput),)


class Input(ctypes.Structure):
    _fields_ = (("type", ctypes.c_ulong), ("union", InputUnion))


class Point(ctypes.Structure):
    _fields_ = (("x", ctypes.c_long), ("y", ctypes.c_long))


WM_MOUSEMOVE = 0x0200
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
MK_LBUTTON = 0x0001
WM_ACTIVATE = 0x0006
WA_ACTIVE = 0x0001


def _send_mouse(flags: int, x: int | None = None, y: int | None = None) -> bool:
    mi = MouseInput()
    if x is not None and y is not None:
        vx = ctypes.windll.user32.GetSystemMetrics(76)
        vy = ctypes.windll.user32.GetSystemMetrics(77)
        vw = ctypes.windll.user32.GetSystemMetrics(78)
        vh = ctypes.windll.user32.GetSystemMetrics(79)
        mi.dx = int((x - vx) * 65535 / max(1, vw - 1))
        mi.dy = int((y - vy) * 65535 / max(1, vh - 1))
        mi.dwFlags = flags | 0x8000 | 0x4000
    else:
        mi.dwFlags = flags
    inp = Input()
    inp.type = 0
    inp.union.mi = mi
    return ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp)) == 1


def _post_window_click(hwnd: int, x: int, y: int, duration: float = 0.08) -> bool:
    if not hwnd:
        return False

    point = Point(x, y)
    user32 = ctypes.windll.user32
    if not user32.ScreenToClient(hwnd, ctypes.byref(point)):
        return False
    lparam = ((int(point.y) & 0xFFFF) << 16) | (int(point.x) & 0xFFFF)
    user32.PostMessageW(hwnd, WM_ACTIVATE, WA_ACTIVE, 0)
    ok_move = user32.PostMessageW(hwnd, WM_MOUSEMOVE, 0, lparam)
    ok_down = user32.PostMessageW(hwnd, WM_LBUTTONDOWN, MK_LBUTTON, lparam)
    time.sleep(duration)
    ok_up = user32.PostMessageW(hwnd, WM_LBUTTONUP, 0, lparam)
    return bool(ok_move and ok_down and ok_up)


def cursor_position() -> tuple[int, int]:
    point = Point()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(point))
    return int(point.x), int(point.y)


def restore_foreground(hwnd: int) -> None:
    if not hwnd or not ctypes.windll.user32.IsWindow(hwnd):
        return
    user32 = ctypes.windll.user32
    user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0040)
    user32.SetForegroundWindow(hwnd)


def click_screen_xy(x: int, y: int, duration: float = 0.08) -> None:
    user32 = ctypes.windll.user32
    restore_hwnd = user32.GetForegroundWindow() if CLICK_RESTORE_AFTER_ACTION else 0
    restore_pos = cursor_position() if CLICK_RESTORE_AFTER_ACTION else None
    hwnd = window_at(x, y)
    try:
        if hwnd:
            ensure_foreground_and_top(hwnd)
        user32.SetCursorPos(x, y)
        time.sleep(CLICK_MOVE_DELAY)
        _send_mouse(0x0001, x, y)
        time.sleep(CLICK_ABSOLUTE_MOVE_DELAY)
        _send_mouse(0x0002)
        time.sleep(duration)
        _send_mouse(0x0004)
        time.sleep(CLICK_AFTER_UP_DELAY)
    finally:
        if CLICK_RESTORE_AFTER_ACTION and restore_pos:
            if restore_hwnd and restore_hwnd != hwnd:
                restore_foreground(restore_hwnd)
            user32.SetCursorPos(*restore_pos)
            time.sleep(0.06)
            user32.SetCursorPos(*restore_pos)


def click_monitor_xy(x: int, y: int, monitor: dict, duration: float = 0.08) -> None:
    hwnd = int(monitor.get("hwnd") or 0)
    if CLICK_METHOD == "postmessage" and hwnd:
        print(f"postmessage click screen=({x},{y}) hwnd=0x{hwnd:x}", flush=True)
        if _post_window_click(hwnd, x, y, duration=duration):
            return
        if not POSTMESSAGE_FALLBACK_SENDINPUT:
            print("postmessage click failed; skipped SendInput to avoid foreground activation.", flush=True)
            return
        print("postmessage click failed; falling back to SendInput.", flush=True)
    click_screen_xy(x, y, duration=duration)


def ensure_foreground_and_top(hwnd: int) -> bool:
    if not hwnd:
        return False
    user32 = ctypes.windll.user32
    foreground = user32.GetForegroundWindow()
    if hwnd == foreground:
        return True
    # Same basic strategy as MaaFramework's Win32 controller: bring the
    # target window to the top, then request foreground, then verify.
    user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0040)
    time.sleep(FOCUS_TOP_DELAY)
    user32.SetForegroundWindow(hwnd)
    time.sleep(FOCUS_FOREGROUND_DELAY)
    ok = hwnd == user32.GetForegroundWindow()
    if not ok:
        user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0001 | 0x0002)
        time.sleep(FOCUS_RETRY_DELAY)
        ok = hwnd == user32.GetForegroundWindow()
    print(f"foreground {'ok' if ok else 'failed'} target=0x{hwnd:x} current=0x{user32.GetForegroundWindow():x}", flush=True)
    return ok


def describe_window_at(x: int, y: int) -> str:
    hwnd = window_at(x, y)
    pid = ctypes.c_ulong()
    ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    title = ctypes.create_unicode_buffer(256)
    ctypes.windll.user32.GetWindowTextW(hwnd, title, 256)
    return f"hwnd=0x{hwnd:x} pid={pid.value} title={title.value!r}"


def click_log_suffix(x: int, y: int) -> str:
    if not LOG_CLICK_WINDOW:
        return ""
    return f" {describe_window_at(x, y)}"


def window_at(x: int, y: int) -> int:
    class Point(ctypes.Structure):
        _fields_ = (("x", ctypes.c_long), ("y", ctypes.c_long))

    return int(ctypes.windll.user32.WindowFromPoint(Point(x, y)))


def click_norm(point: tuple[float, float], monitor: dict, duration: float = 0.08) -> None:
    x = int(monitor["left"] + monitor["width"] * point[0])
    y = int(monitor["top"] + monitor["height"] * point[1])
    print(f"click screen=({x},{y}){click_log_suffix(x, y)}", flush=True)
    click_monitor_xy(x, y, monitor, duration=duration)


def rapid_click_norm(
    point: tuple[float, float],
    monitor: dict,
    count: int,
    duration: float,
    interval: float,
    stop_keys: list[str],
    stop_file: Path | None,
) -> int:
    x = int(monitor["left"] + monitor["width"] * point[0])
    y = int(monitor["top"] + monitor["height"] * point[1])
    print(f"rapid click screen=({x},{y}) count={count}{click_log_suffix(x, y)}", flush=True)
    hwnd = int(monitor.get("hwnd") or 0)
    sent = 0
    if CLICK_METHOD == "postmessage" and hwnd:
        for _ in range(count):
            if stop_requested(stop_keys, stop_file):
                return sent
            if not _post_window_click(hwnd, x, y, duration=duration):
                if not POSTMESSAGE_FALLBACK_SENDINPUT:
                    print("postmessage rapid click failed; skipped SendInput to avoid foreground activation.", flush=True)
                    return sent
                print("postmessage rapid click failed; falling back to SendInput.", flush=True)
                break
            sent += 1
            if sleep_interruptible(interval, stop_keys, stop_file):
                return sent
        if sent == count:
            return sent
    remaining = count - sent if CLICK_METHOD == "postmessage" and hwnd else count
    if remaining <= 0:
        return sent
    user32 = ctypes.windll.user32
    restore_hwnd = user32.GetForegroundWindow() if CLICK_RESTORE_AFTER_ACTION else 0
    restore_pos = cursor_position() if CLICK_RESTORE_AFTER_ACTION else None
    hwnd = window_at(x, y)
    try:
        if hwnd:
            ensure_foreground_and_top(hwnd)
        user32.SetCursorPos(x, y)
        for _ in range(remaining):
            if stop_requested(stop_keys, stop_file):
                return sent
            _send_mouse(0x0002)
            time.sleep(duration)
            _send_mouse(0x0004)
            sent += 1
            if sleep_interruptible(interval, stop_keys, stop_file):
                return sent
        return sent
    finally:
        if CLICK_RESTORE_AFTER_ACTION and restore_pos:
            if restore_hwnd and restore_hwnd != hwnd:
                restore_foreground(restore_hwnd)
            user32.SetCursorPos(*restore_pos)
            time.sleep(0.06)
            user32.SetCursorPos(*restore_pos)


def click_frame_point(point: tuple[int, int], monitor: dict, duration: float = 0.08) -> None:
    x = int(monitor["left"] + point[0])
    y = int(monitor["top"] + point[1])
    print(f"click screen=({x},{y}){click_log_suffix(x, y)}", flush=True)
    click_monitor_xy(x, y, monitor, duration=duration)


def parse_stop_keys(stop_key: str) -> list[str]:
    keys = [key.strip().lower() for key in stop_key.split(",") if key.strip()]
    if not keys:
        return ["f8"]
    unknown = sorted(set(keys) - set(VK_CODES))
    if unknown:
        supported = ", ".join(sorted(VK_CODES))
        raise ValueError(f"unsupported stop key(s): {', '.join(unknown)}. Supported: {supported}")
    return keys


def stop_requested(stop_keys: list[str], stop_file: Path | None) -> bool:
    if stop_file and stop_file.exists():
        print(f"stop file detected: {stop_file}")
        return True
    for key in stop_keys:
        if ctypes.windll.user32.GetAsyncKeyState(VK_CODES[key]) & 0x8000:
            print(f"{key.upper()} pressed; exiting immediately.")
            return True
    return False


def sleep_interruptible(seconds: float, stop_keys: list[str], stop_file: Path | None) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        if stop_requested(stop_keys, stop_file):
            return True
        time.sleep(min(0.05, max(0.0, deadline - time.time())))
    return False


@dataclasses.dataclass(frozen=True)
class LiveConfig:
    detector: CznDetector
    act: bool
    interval: float
    no_dream_action: str
    max_seconds: float
    monitor_index: int
    advance_on_unknown: bool
    stop_keys: list[str]
    max_clicks: int
    stop_file: Path | None
    post_click_wait: float
    capture_method: str
    window_title: str | None
    fast_start_to_team_enabled: bool
    log_interval: float
    wait_after_team_enter: float
    dialog_burst_mode: str


@dataclasses.dataclass
class ExpectedTransition:
    action_name: str
    from_label: str
    expected_labels: set[str]
    started: float
    deadline: float


@dataclasses.dataclass
class LiveRuntime:
    last_action: float = 0.0
    next_action_delay: float = INITIAL_ACTION_DELAY
    started: float = dataclasses.field(default_factory=time.time)
    printed_monitor: bool = False
    waiting_after_legend: bool = False
    waiting_after_reward_action: bool = False
    handled_choice_without_legend: bool = False
    handled_start_screen: bool = False
    pending_legend_confirm_point: tuple[int, int] | None = None
    click_count: int = 0
    last_logged_state: str = ""
    last_log_time: float = 0.0
    wait_for_dialog_until: float = 0.0
    dialog_advance_armed: bool = False
    expected_transition: ExpectedTransition | None = None


class LiveSession:
    def __init__(self, config: LiveConfig) -> None:
        self.config = config
        self.runtime = LiveRuntime()

    def run(self) -> None:
        cfg = self.config
        print(
            f"live mode started. capture={cfg.capture_method}. Stop keys: {', '.join(k.upper() for k in cfg.stop_keys)}. "
            "Dry-run is ON unless --act is passed."
        )
        print(
            "live config: "
            f"act={cfg.act}, interval={cfg.interval}, log_interval={cfg.log_interval}, "
            f"monitor={cfg.monitor_index}, max_seconds={cfg.max_seconds}, max_clicks={cfg.max_clicks}, "
            f"window_title={cfg.window_title!r}, "
            f"no_dream_action={cfg.no_dream_action}, advance_on_unknown={cfg.advance_on_unknown}, "
            f"fast_start_to_team={cfg.fast_start_to_team_enabled}, post_click_wait={cfg.post_click_wait}, "
            f"wait_after_team_enter={cfg.wait_after_team_enter}, dialog_burst_mode={cfg.dialog_burst_mode}, "
            f"stop_file={cfg.stop_file}"
        )
        print(
            f"detector: template_dir={cfg.detector.template_dir}, "
            f"match_scale_factors={cfg.detector.match_scale_factors}"
        )
        if cfg.stop_file and cfg.stop_file.exists():
            cfg.stop_file.unlink()

        try:
            while True:
                if self.should_stop():
                    return
                frame, monitor = screen_shot(cfg.monitor_index, cfg.capture_method, cfg.window_title)
                if not self.runtime.printed_monitor:
                    print(f"using monitor {cfg.monitor_index}: {monitor}; frame_shape={frame.shape}")
                    self.runtime.printed_monitor = True
                state = cfg.detector.detect(frame)
                now = time.time()
                self.log_state(now, state)
                self.check_expected_transition(now, state)
                if now - self.runtime.last_action >= self.runtime.next_action_delay:
                    if not self.handle_state(frame, monitor, state, now):
                        return
                if sleep_interruptible(cfg.interval, cfg.stop_keys, cfg.stop_file):
                    return
        finally:
            elapsed = time.time() - self.runtime.started
            print(f"live mode stopped. elapsed={elapsed:.1f}s, clicks={self.runtime.click_count}")

    def should_stop(self) -> bool:
        cfg = self.config
        rt = self.runtime
        if stop_requested(cfg.stop_keys, cfg.stop_file):
            return True
        if cfg.max_seconds > 0 and time.time() - rt.started >= cfg.max_seconds:
            print("live mode max seconds reached; exiting.")
            return True
        if cfg.max_clicks > 0 and rt.click_count >= cfg.max_clicks:
            print("live mode max clicks reached; exiting.")
            return True
        return False

    def log_state(self, now: float, state: DetectionState) -> None:
        rt = self.runtime
        if state.label != rt.last_logged_state or now - rt.last_log_time >= self.config.log_interval:
            print_state(time.strftime("%H:%M:%S"), state)
            rt.last_logged_state = state.label
            rt.last_log_time = now

    def mark_action(self, now: float, delay: float) -> None:
        self.runtime.last_action = now
        self.runtime.next_action_delay = delay

    def expect_transition(
        self,
        action_name: str,
        from_label: str,
        expected_labels: set[str],
        timeout: float,
    ) -> None:
        if not self.config.act:
            return
        started = time.time()
        timeout = max(timeout, self.config.interval)
        self.runtime.expected_transition = ExpectedTransition(
            action_name=action_name,
            from_label=from_label,
            expected_labels=expected_labels,
            started=started,
            deadline=started + timeout,
        )
        expected = ",".join(sorted(expected_labels))
        print(
            f"watch transition: action={action_name}, from={from_label}, "
            f"expected={expected}, timeout={timeout:.1f}s"
        )

    def check_expected_transition(self, now: float, state: DetectionState) -> None:
        transition = self.runtime.expected_transition
        if transition is None:
            return
        if state.label in transition.expected_labels:
            elapsed = now - transition.started
            print(
                f"transition ok: action={transition.action_name}, "
                f"{transition.from_label}->{state.label}, elapsed={elapsed:.1f}s"
            )
            self.runtime.expected_transition = None
            return
        if now < transition.deadline:
            return

        expected = ",".join(sorted(transition.expected_labels))
        elapsed = now - transition.started
        print(
            "HIGH RISK: transition timeout: "
            f"action={transition.action_name}, from={transition.from_label}, "
            f"current={state.label}, expected={expected}, elapsed={elapsed:.1f}s. "
            "Possible causes: click missed, wrong monitor/resolution, stale screenshot, or UI timing too short."
        )
        self.runtime.expected_transition = None

    def disarm_dialog(self) -> None:
        self.runtime.dialog_advance_armed = False
        self.runtime.wait_for_dialog_until = 0.0

    def reset_common(
        self,
        *,
        legend: bool = True,
        reward: bool = True,
        choice: bool = True,
        start: bool = True,
        dialog: bool = True,
    ) -> None:
        rt = self.runtime
        if dialog:
            self.disarm_dialog()
        if legend:
            rt.waiting_after_legend = False
            rt.pending_legend_confirm_point = None
        if reward:
            rt.waiting_after_reward_action = False
        if choice:
            rt.handled_choice_without_legend = False
        if start:
            rt.handled_start_screen = False

    def wait_visual(
        self,
        frame: np.ndarray,
        action_name: str,
        expected_labels: set[str],
    ) -> None:
        cfg = self.config
        wait_visual_change(
            cfg.detector,
            frame,
            cfg.monitor_index,
            cfg.capture_method,
            cfg.window_title,
            cfg.stop_keys,
            cfg.stop_file,
            cfg.post_click_wait,
            action_name=action_name,
            expected_labels=expected_labels,
        )

    def handle_after_legend_confirm(self, frame: np.ndarray, monitor: dict) -> None:
        cfg = self.config
        rt = self.runtime
        if not cfg.act:
            return

        waited = wait_for_detected_state(
            cfg.detector,
            cfg.monitor_index,
            cfg.capture_method,
            cfg.window_title,
            cfg.stop_keys,
            cfg.stop_file,
            {"card_reward", "dream_found", "unknown"},
            cfg.post_click_wait,
            "legend_confirm_to_reward_or_dialog",
        )
        if not waited:
            return

        _, next_monitor, next_state = waited
        if next_state.label in {"card_reward", "dream_found"}:
            return

        print("legend confirm reached unknown/dialog; advancing dialog before reward.")
        dialog_clicks = checked_dialog_advance(
            cfg.detector,
            next_monitor or monitor,
            cfg.monitor_index,
            cfg.capture_method,
            cfg.window_title,
            cfg.stop_keys,
            cfg.stop_file,
            cfg.act,
            max_taps=LEGEND_DIALOG_TAPS,
            tap_delay=LEGEND_DIALOG_TAP_DELAY,
            prefix="legend dialog",
        )
        rt.click_count += dialog_clicks
        if dialog_clicks > 0:
            self.expect_transition(
                "legend_dialog_advance",
                "unknown",
                {"card_reward", "dream_found", "choice_screen", "legend_choice"},
                max(cfg.post_click_wait, LEGEND_DIALOG_TAPS * LEGEND_DIALOG_TAP_DELAY + 1.0),
            )

    def handle_state(self, frame: np.ndarray, monitor: dict, state: DetectionState, now: float) -> bool:
        if state.dream_card:
            return self.handle_dream_card()
        if state.card_reward:
            return self.handle_card_reward(frame, monitor, state, now)
        if state.return_confirm:
            return self.handle_return_confirm(frame, monitor, state, now)
        if state.legend_choice:
            return self.handle_legend_choice(frame, monitor, state, now)
        if state.choice_card:
            return self.handle_choice_screen(frame, monitor, now)
        if state.flee_button:
            return self.handle_flee_screen(frame, monitor, state, now)
        if state.team_enter:
            return self.handle_team_enter(monitor, state, now)
        if state.start_screen and start_match_looks_like_team_fallback(state, frame.shape):
            return self.handle_team_enter_fallback(monitor, state, now)
        if state.start_screen:
            return self.handle_start_screen(frame, monitor, state, now)
        return self.handle_unknown(monitor, now)

    def handle_dream_card(self) -> bool:
        self.disarm_dialog()
        print("dream card found; stopping automation loop.")
        return False

    def handle_card_reward(self, frame: np.ndarray, monitor: dict, state: DetectionState, now: float) -> bool:
        cfg = self.config
        rt = self.runtime
        self.reset_common(legend=True, reward=False, choice=True, start=True, dialog=True)
        if not rt.waiting_after_reward_action and REWARD_SETTLE_BEFORE_ACTION > 0:
            print(f"reward screen: settle {REWARD_SETTLE_BEFORE_ACTION:.1f}s before checking cards.")
            if sleep_interruptible(REWARD_SETTLE_BEFORE_ACTION, cfg.stop_keys, cfg.stop_file):
                return False
            frame, monitor = screen_shot(cfg.monitor_index, cfg.capture_method, cfg.window_title)
            state = cfg.detector.detect(frame)
            print_state("reward settle", state)
            if state.dream_card:
                print("dream card found after reward settle; stopping automation loop.")
                return False
            if not state.card_reward:
                self.mark_action(time.time(), cfg.interval)
                return True
        if rt.waiting_after_reward_action:
            print("reward screen already handled once; waiting for screen to change.")
            self.mark_action(now, DELAY_REWARD_ALREADY_HANDLED)
            return not sleep_interruptible(cfg.interval, cfg.stop_keys, cfg.stop_file)

        if cfg.no_dream_action == "retry-top-right":
            retry_point = state.top_right_menu.center if state.top_right_menu else None
            print_action("no dream card: click top-right retry/menu area", CLICK_RETRY_TOP_RIGHT, cfg.act)
            if cfg.act:
                if retry_point:
                    click_frame_point(retry_point, monitor)
                else:
                    click_norm(CLICK_RETRY_TOP_RIGHT, monitor)
                rt.click_count += 1
                self.wait_visual(frame, "reward_retry", {"flee_screen", "start_screen", "team_screen", "unknown"})
        elif cfg.no_dream_action == "confirm":
            print_action("no dream card: click confirm", CLICK_CONFIRM, cfg.act)
            if cfg.act:
                click_norm(CLICK_CONFIRM, monitor)
                rt.click_count += 1
                self.wait_visual(frame, "reward_confirm", {"start_screen", "team_screen", "unknown"})
        else:
            print("no dream card: reward screen detected; no action configured.")

        rt.waiting_after_reward_action = True
        self.mark_action(now, DELAY_AFTER_REWARD_ACTION)
        return True

    def handle_return_confirm(self, frame: np.ndarray, monitor: dict, state: DetectionState, now: float) -> bool:
        cfg = self.config
        self.reset_common()
        confirm_point = state.return_confirm.point_at(0.68, 0.50)
        print_action(f"return confirm: click confirm at {confirm_point}", CLICK_CONFIRM, cfg.act)
        if cfg.act:
            click_frame_point(confirm_point, monitor)
            self.runtime.click_count += 1
            self.wait_visual(frame, "return_confirm", {"start_screen", "team_screen", "unknown"})
        self.mark_action(now, DELAY_AFTER_RETURN_CONFIRM)
        return True

    def handle_legend_choice(self, frame: np.ndarray, monitor: dict, state: DetectionState, now: float) -> bool:
        cfg = self.config
        rt = self.runtime
        self.reset_common(legend=False, reward=True, choice=True, start=True, dialog=True)
        if rt.waiting_after_legend:
            if rt.pending_legend_confirm_point is None:
                rt.pending_legend_confirm_point = choice_confirm_point_for(state.legend_choice.center, frame.shape)
            print_action(f"legend option selected: click check at {rt.pending_legend_confirm_point}", CLICK_CONFIRM, cfg.act)
            if cfg.act:
                click_frame_point(rt.pending_legend_confirm_point, monitor)
                rt.click_count += 1
                self.handle_after_legend_confirm(frame, monitor)
            rt.waiting_after_legend = False
            rt.pending_legend_confirm_point = None
            self.mark_action(now, DELAY_AFTER_LEGEND_CONFIRM)
            return True

        print_action(f"click matched legend option at {state.legend_choice.center}", CLICK_CHOICE_RIGHT, cfg.act)
        if cfg.act:
            rt.pending_legend_confirm_point = choice_confirm_point_for(state.legend_choice.center, frame.shape)
            click_frame_point(state.legend_choice.center, monitor)
            rt.click_count += 1
            if sleep_interruptible(LEGEND_CONFIRM_DELAY, cfg.stop_keys, cfg.stop_file):
                return False
            print_action(f"legend option confirm: click check at {rt.pending_legend_confirm_point}", CLICK_CONFIRM, cfg.act)
            click_frame_point(rt.pending_legend_confirm_point, monitor)
            rt.click_count += 1
            self.handle_after_legend_confirm(frame, monitor)
        else:
            rt.pending_legend_confirm_point = choice_confirm_point_for(state.legend_choice.center, frame.shape)
        rt.waiting_after_legend = False
        rt.pending_legend_confirm_point = None
        self.mark_action(now, DELAY_AFTER_LEGEND_CONFIRM)
        return True

    def handle_choice_screen(self, frame: np.ndarray, monitor: dict, now: float) -> bool:
        cfg = self.config
        rt = self.runtime
        self.reset_common(reward=True, choice=False, start=True, dialog=True)
        if rt.handled_choice_without_legend:
            print("choice screen without legend already handled once; waiting for screen to change.")
            self.mark_action(now, DELAY_CHOICE_ALREADY_HANDLED)
            return not sleep_interruptible(cfg.interval, cfg.stop_keys, cfg.stop_file)
        chain_clicks = fast_abandon_no_legend(
            cfg.detector,
            frame,
            monitor,
            cfg.monitor_index,
            cfg.capture_method,
            cfg.window_title,
            cfg.stop_keys,
            cfg.stop_file,
            cfg.act,
        )
        rt.click_count += chain_clicks
        if chain_clicks > 0:
            self.expect_transition(
                "no_legend_chain",
                "choice_screen",
                {"return_confirm", "start_screen", "team_screen", "unknown"},
                max(cfg.post_click_wait, CHAIN_MENU_TO_FLEE_TIMEOUT + CHAIN_FLEE_TO_CONFIRM_TIMEOUT + 1.0),
            )
            rt.wait_for_dialog_until = time.time() + 0.6
            rt.dialog_advance_armed = True
            print("choice chain reached possible dialog/loading; controlled unknown advance armed.")
        rt.handled_choice_without_legend = True
        self.mark_action(now, DELAY_AFTER_NO_LEGEND_CHAIN)
        return True

    def handle_flee_screen(self, frame: np.ndarray, monitor: dict, state: DetectionState, now: float) -> bool:
        cfg = self.config
        self.reset_common()
        flee_point = state.flee_button.point_at(0.72, 0.50)
        print_action(f"flee screen: click flee text area at {flee_point}", CLICK_ADVANCE, cfg.act)
        if cfg.act:
            click_frame_point(flee_point, monitor)
            self.runtime.click_count += 1
            self.wait_visual(frame, "flee", {"return_confirm", "unknown"})
        self.mark_action(now, DELAY_AFTER_FLEE)
        return True

    def handle_team_enter(self, monitor: dict, state: DetectionState, now: float) -> bool:
        cfg = self.config
        rt = self.runtime
        self.reset_common(dialog=False)
        click_point = state.team_enter.point_at(*BUTTON_TEXT_POINT)
        print_action(f"team screen: click enter at {click_point}", CLICK_START_ENTER, cfg.act)
        if cfg.act:
            click_frame_point(click_point, monitor)
            rt.click_count += 1
            self.expect_transition(
                "team_enter",
                state.label,
                {"unknown", "choice_screen", "legend_choice", "card_reward", "dream_found"},
                max(cfg.wait_after_team_enter + 2.0, cfg.post_click_wait),
            )
        rt.wait_for_dialog_until = time.time() + cfg.wait_after_team_enter
        rt.dialog_advance_armed = True
        print(f"team enter clicked; dialog advance armed after {cfg.wait_after_team_enter:.1f}s.")
        self.mark_action(now, min(max(cfg.wait_after_team_enter, cfg.interval), 1.0))
        return True

    def handle_team_enter_fallback(self, monitor: dict, state: DetectionState, now: float) -> bool:
        cfg = self.config
        rt = self.runtime
        self.reset_common(dialog=False)
        print(
            "start template matched the lower-left team row; treating this as team screen "
            f"fallback. match={state.start_screen.center if state.start_screen else None}"
        )
        print_action("team screen fallback: click fixed enter", CLICK_TEAM_ENTER, cfg.act)
        if cfg.act:
            click_norm(CLICK_TEAM_ENTER, monitor, duration=FAST_CLICK_DURATION)
            rt.click_count += 1
            self.expect_transition(
                "team_enter_fallback",
                state.label,
                {"unknown", "choice_screen", "legend_choice", "card_reward", "dream_found"},
                max(cfg.wait_after_team_enter + 2.0, cfg.post_click_wait),
            )
        rt.wait_for_dialog_until = time.time() + cfg.wait_after_team_enter
        rt.dialog_advance_armed = True
        print(f"team fallback clicked; dialog advance armed after {cfg.wait_after_team_enter:.1f}s.")
        self.mark_action(now, min(max(cfg.wait_after_team_enter, cfg.interval), 1.0))
        return True

    def handle_start_screen(self, frame: np.ndarray, monitor: dict, state: DetectionState, now: float) -> bool:
        cfg = self.config
        rt = self.runtime
        self.reset_common(choice=True, start=False, dialog=True)
        if rt.handled_start_screen:
            print("start screen already clicked once; waiting for screen to change.")
            self.mark_action(now, DELAY_START_ALREADY_HANDLED)
            return not sleep_interruptible(cfg.interval, cfg.stop_keys, cfg.stop_file)
        click_point = state.start_screen.point_at(*BUTTON_TEXT_POINT)
        if cfg.fast_start_to_team_enabled:
            quick_clicks = fast_start_to_team(
                monitor,
                cfg.stop_keys,
                cfg.stop_file,
                cfg.act,
                first_point=None,
            )
            rt.click_count += quick_clicks
            if cfg.act:
                if quick_clicks > 0:
                    self.expect_transition(
                        "start_enter",
                        state.label,
                        {"team_screen", "unknown"},
                        max(cfg.post_click_wait, 2.0),
                    )
                print("start enter clicked; waiting for team screen recognition.")
        else:
            print_action(f"start screen: click enter at {click_point}", CLICK_START_ENTER, cfg.act)
            if cfg.act:
                click_frame_point(click_point, monitor)
                rt.click_count += 1
                self.wait_visual(frame, "start_enter", {"team_screen", "unknown"})
        rt.handled_start_screen = True
        self.mark_action(now, DELAY_AFTER_START_ENTER)
        return True

    def handle_unknown(self, monitor: dict, now: float) -> bool:
        cfg = self.config
        rt = self.runtime
        self.reset_common(dialog=False)
        if not rt.dialog_advance_armed:
            if not cfg.advance_on_unknown:
                print("unknown screen: no click. Pass --advance-on-unknown to enable blind advance clicks.")
                self.mark_action(now, DELAY_UNKNOWN_IDLE)
                return True
            print("unknown screen: dialog advance is not armed; waiting for a team enter first.")
            self.mark_action(now, DELAY_UNKNOWN_IDLE)
            return not sleep_interruptible(cfg.interval, cfg.stop_keys, cfg.stop_file)
        if rt.wait_for_dialog_until > now:
            remaining = rt.wait_for_dialog_until - now
            print(f"unknown screen: waiting {remaining:.1f}s before dialog advance burst.")
            self.mark_action(now, min(max(remaining, cfg.interval), 1.0))
            return not sleep_interruptible(cfg.interval, cfg.stop_keys, cfg.stop_file)
        rt.wait_for_dialog_until = 0.0
        burst_clicks = fast_advance_unknown(
            cfg.detector,
            monitor,
            cfg.monitor_index,
            cfg.capture_method,
            cfg.window_title,
            cfg.stop_keys,
            cfg.stop_file,
            cfg.act,
        )
        rt.click_count += burst_clicks
        if burst_clicks > 0:
            self.expect_transition(
                "dialog_advance_burst",
                "unknown",
                {"choice_screen", "legend_choice", "card_reward", "dream_found", "flee_screen", "return_confirm"},
                max(2.0, cfg.interval * 4),
            )
        rt.dialog_advance_armed = False
        self.mark_action(now, DELAY_AFTER_UNKNOWN_BURST)
        return True


def run_live(
    detector: CznDetector,
    act: bool,
    interval: float,
    no_dream_action: str,
    max_seconds: float,
    monitor_index: int,
    advance_on_unknown: bool,
    stop_key: str,
    max_clicks: int,
    stop_file: Path | None,
    post_click_wait: float,
    capture_method: str,
    window_title: str | None,
    fast_start_to_team_enabled: bool,
    log_interval: float,
    wait_after_team_enter: float,
    dialog_burst_mode: str,
) -> None:
    stop_keys = parse_stop_keys(stop_key)
    LiveSession(
        LiveConfig(
            detector=detector,
            act=act,
            interval=interval,
            no_dream_action=no_dream_action,
            max_seconds=max_seconds,
            monitor_index=monitor_index,
            advance_on_unknown=advance_on_unknown,
            stop_keys=stop_keys,
            max_clicks=max_clicks,
            stop_file=stop_file,
            post_click_wait=post_click_wait,
            capture_method=capture_method,
            window_title=window_title,
            fast_start_to_team_enabled=fast_start_to_team_enabled,
            log_interval=log_interval,
            wait_after_team_enter=wait_after_team_enter,
            dialog_burst_mode=dialog_burst_mode,
        )
    ).run()


def run_state_check(
    detector: CznDetector,
    monitor_index: int,
    capture_method: str,
    window_title: str | None,
) -> None:
    root = app_install_dir()
    frame, monitor = screen_shot(monitor_index, capture_method, window_title)
    state = detector.detect(frame)
    print(f"capture={capture_method} monitor={monitor}")
    print_state("fresh_state", state)
    save_image(root / "debug_live" / "fresh_state.jpg", frame)
    save_image(root / "debug_live" / "fresh_state_annotated.jpg", annotate(frame, state))


def print_action(label: str, point: tuple[float, float], act: bool) -> None:
    mode = "ACT" if act else "DRY"
    print(f"{mode}: {label} at normalized {point}", flush=True)


def main() -> None:
    global CLICK_METHOD
    global CLICK_RESTORE_AFTER_ACTION
    global POSTMESSAGE_FALLBACK_SENDINPUT
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument("--config", type=Path, default=default_config_file())
    pre_parser.add_argument("--no-user-config", action="store_true")
    pre_parser.add_argument("--init-config", action="store_true")
    pre_args, _ = pre_parser.parse_known_args()
    if pre_args.init_config:
        path = write_default_config(pre_args.config, overwrite=False)
        print(f"config ready: {path}")
        return
    if not pre_args.no_user_config and not any(arg in {"-h", "--help"} for arg in sys.argv[1:]):
        apply_user_config(pre_args.config)

    parser = argparse.ArgumentParser(description="CZN visual detector and cautious automation helper.")
    parser.add_argument("--config", type=Path, default=pre_args.config, help="User config JSON path. Defaults to config.json next to the program.")
    parser.add_argument("--no-user-config", action="store_true", help="Ignore the user config file for this run.")
    parser.add_argument("--init-config", action="store_true", help="Create the default user config file and exit.")
    parser.add_argument("--image", type=Path)
    parser.add_argument("--video", type=Path)
    parser.add_argument("--gui", action="store_true", help="Open the graphical launcher.")
    parser.add_argument("--state-check", action="store_true", help="Capture one fresh frame and classify the current state.")
    parser.add_argument("--list-windows", action="store_true", help="List visible capturable windows and exit.")
    parser.add_argument("--game-window", action="store_true", help="Capture the default CZN game window.")
    parser.add_argument("--window-title", help="Capture the client area of the visible window whose title contains this text.")
    parser.add_argument("--every-sec", type=float, default=0.25)
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--log-file", type=Path, help="Write detailed run output to this log file. Defaults to LocalAppData\\CZN Auto\\logs.")
    parser.add_argument("--no-run-log", action="store_true", help="Disable the automatic per-run log file.")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--act", action="store_true", help="Actually click in live mode. Omit for dry-run.")
    parser.add_argument("--interval", type=float, default=LIVE_LOOP_INTERVAL)
    parser.add_argument("--log-interval", type=float, default=LIVE_LOG_INTERVAL, help="Minimum seconds between repeated live state log lines. 0 prints every loop.")
    parser.add_argument("--max-seconds", type=float, default=0.0, help="Stop live mode after this many seconds. 0 means run until stopped/found.")
    parser.add_argument("--max-clicks", type=int, default=0, help="Stop live mode after this many actual clicks. 0 means unlimited.")
    parser.add_argument("--post-click-wait", type=float, default=POST_CLICK_WAIT, help="Wait this many seconds after each click for a real visual change.")
    parser.add_argument(
        "--click-method",
        choices=["sendinput", "postmessage"],
        default=CLICK_METHOD,
        help="sendinput uses the real mouse. postmessage sends background window click messages and does not move the cursor.",
    )
    parser.add_argument(
        "--restore-after-click",
        action=argparse.BooleanOptionalAction,
        default=CLICK_RESTORE_AFTER_ACTION,
        help="Restore the previous foreground window and cursor position after each SendInput click.",
    )
    parser.add_argument(
        "--postmessage-fallback-sendinput",
        action=argparse.BooleanOptionalAction,
        default=POSTMESSAGE_FALLBACK_SENDINPUT,
        help="Allow postmessage mode to fall back to real SendInput clicks when background messages fail.",
    )
    parser.add_argument(
        "--wait-after-team-enter",
        type=float,
        default=WAIT_AFTER_TEAM_ENTER_BEFORE_DIALOG,
        help="After clicking team enter, wait this many seconds before allowing blind dialog advance bursts.",
    )
    parser.add_argument(
        "--dialog-burst-mode",
        choices=["rapid", "checked"],
        default=DIALOG_BURST_MODE,
        help="Dialog advance burst behavior. rapid keeps the old fast continuous clicks; checked re-detects after each tap.",
    )
    parser.add_argument("--monitor", type=int, default=1, help="monitor index. 1 is primary on this machine; 2 is the secondary display.")
    parser.add_argument(
        "--capture-method",
        choices=["dxgi", "mss", "printwindow", "bitblt-renderfull"],
        default="printwindow",
        help="Live screenshot backend. printwindow/bitblt-renderfull can capture some covered windows without foregrounding.",
    )
    parser.add_argument("--advance-on-unknown", action="store_true", help="Allow live mode to click the advance point when no known UI state is detected.")
    parser.add_argument(
        "--fast-start-to-team",
        action="store_true",
        help="After detecting the main enter button once, tap the enter area several times without waiting for team-screen recognition.",
    )
    parser.add_argument(
        "--wide-match-scales",
        action="store_true",
        help="Use the older wider 7-scale template search. Slower, but useful if fast matching misses UI on unusual scaling.",
    )
    parser.add_argument(
        "--stop-key",
        default="f8,esc,pause,end",
        help="Comma-separated global emergency stop keys for live mode.",
    )
    parser.add_argument("--stop-file", type=Path, default=Path("STOP"), help="Create this file to stop live mode.")
    parser.add_argument(
        "--no-dream-action",
        choices=["retry-top-right", "confirm", "none"],
        default="retry-top-right",
        help="What live mode should do on a card reward screen when 梦之边境 is not detected.",
    )
    args = parser.parse_args()
    if args.game_window and not args.window_title:
        args.window_title = DEFAULT_GAME_WINDOW_TITLE
    CLICK_METHOD = args.click_method
    CLICK_RESTORE_AFTER_ACTION = args.restore_after_click
    POSTMESSAGE_FALLBACK_SENDINPUT = args.postmessage_fallback_sendinput
    if args.live:
        try:
            parse_stop_keys(args.stop_key)
        except ValueError as exc:
            parser.error(str(exc))

    if args.list_windows:
        for item in list_visible_windows():
            print(
                f"hwnd=0x{int(item['hwnd']):x} pid={item['pid']} "
                f"{item['width']}x{item['height']}+{item['left']}+{item['top']} title={item['title']!r}"
            )
        return

    if args.gui:
        from czn_gui import main as gui_main

        gui_main()
        return

    log_path = None
    if not args.no_run_log:
        log_path = setup_run_log(args.log_file)
    print_run_header(args, log_path)

    detector = CznDetector(wide_match_scales=args.wide_match_scales)
    if args.image:
        run_image(detector, args.image, args.out_dir)
    elif args.video:
        run_video(detector, args.video, args.every_sec, args.out_dir)
    elif args.state_check:
        run_state_check(detector, args.monitor, args.capture_method, args.window_title)
    elif args.live:
        run_live(
            detector,
            args.act,
            args.interval,
            args.no_dream_action,
            args.max_seconds,
            args.monitor,
            args.advance_on_unknown,
            args.stop_key,
            args.max_clicks,
            args.stop_file,
            args.post_click_wait,
            args.capture_method,
            args.window_title,
            args.fast_start_to_team,
            args.log_interval,
            args.wait_after_team_enter,
            args.dialog_burst_mode,
        )
    else:
        parser.error("pass --image, --video, or --live")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("KeyboardInterrupt; exiting.", file=sys.stderr, flush=True)
        raise SystemExit(130)
    except Exception:
        print("fatal error: unhandled exception", file=sys.stderr, flush=True)
        traceback.print_exc()
        raise SystemExit(1)
