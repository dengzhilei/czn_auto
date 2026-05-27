from __future__ import annotations

import argparse
import atexit
import dataclasses
import ctypes
import sys
import time
from pathlib import Path
from typing import Iterable

import cv2
import numpy as np


BASE_W = 3840
BASE_H = 2160
BASE_ASPECT = BASE_W / BASE_H
ASPECT_TOLERANCE = 0.03
_DXGI_CAMERAS: dict[int, object] = {}


def app_base_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


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
BUTTON_TEXT_POINT = (0.78, 0.52)
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

# 点确认后给页面开始跳转的一点时间；后续仍由主循环识别当前位置。
CHAIN_AFTER_CONFIRM_DELAY = 0.20

# 对白页连续点击：最多连点次数。到三选一/奖励等已知状态会提前停。
DIALOG_BURST_MAX_TAPS = 9

# 对白页连续点击：每次点击后的间隔。想更快可以先试 0.08，再低要观察是否漏点。
DIALOG_BURST_TAP_DELAY = 0.4

# Start-screen quick chain: after the main enter button is seen once,
# keep tapping the known enter area briefly instead of waiting for team-screen recognition.
START_TO_TEAM_BURST_TAPS = 2
START_TO_TEAM_TAP_DELAY = 0.5
WAIT_AFTER_TEAM_ENTER_BEFORE_DIALOG = 7.0
POST_CLICK_WAIT = 4.0
REWARD_SETTLE_BEFORE_ACTION = 1.5
SAVE_VISUAL_CHANGE_DEBUG = False
LOG_CLICK_WINDOW = False

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
        root = app_base_dir()
        self.template_dir = template_dir or root / "templates"
        self.match_scale_factors = WIDE_MATCH_SCALE_FACTORS if wide_match_scales else FAST_MATCH_SCALE_FACTORS
        self._warned_aspect_sizes: set[tuple[int, int]] = set()
        self.legend_template = self._load_template("legend_word.jpg")
        self.legend_wide_template = self._load_template("legend_word_wide.jpg")
        self.dream_template = self._load_template("dream_border_title.jpg")
        self.card_reward_template = self._load_template("card_reward_title.jpg")
        self.start_enter_template = self._load_template("start_enter_button.jpg")
        self.choice_glow_template = self._load_template("choice_bottom_glow.jpg")
        self.top_right_menu_template = self._load_template("combat_top_right_menu.jpg")
        self.flee_button_template = self._load_template("flee_button.jpg")
        self.team_enter_template = self._load_template("team_enter_button.jpg")
        self.return_confirm_template = self._load_template("return_confirm_button.jpg")

    def _load_template(self, name: str) -> np.ndarray:
        path = self.template_dir / name
        image = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise FileNotFoundError(f"template not found or unreadable: {path}")
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
            scale = base_scale * scale_factor
            tw = max(8, int(round(template_gray.shape[1] * scale)))
            th = max(8, int(round(template_gray.shape[0] * scale)))
            if tw >= haystack.shape[1] or th >= haystack.shape[0]:
                continue
            template = cv2.resize(template_gray, (tw, th), interpolation=cv2.INTER_AREA)
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


def _monitor_meta(monitor_index: int) -> dict:
    import mss

    with mss.mss() as sct:
        if monitor_index < 0 or monitor_index >= len(sct.monitors):
            raise ValueError(f"monitor index {monitor_index} is out of range; available: 0..{len(sct.monitors) - 1}")
        monitor = sct.monitors[monitor_index]
    return monitor


def _screen_shot_mss(monitor_index: int) -> tuple[np.ndarray, dict]:
    import mss

    with mss.mss() as sct:
        if monitor_index < 0 or monitor_index >= len(sct.monitors):
            raise ValueError(f"monitor index {monitor_index} is out of range; available: 0..{len(sct.monitors) - 1}")
        monitor = sct.monitors[monitor_index]
        raw = np.array(sct.grab(monitor))
    return cv2.cvtColor(raw, cv2.COLOR_BGRA2BGR), monitor


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


def screen_shot(monitor_index: int, capture_method: str = "dxgi") -> tuple[np.ndarray, dict]:
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
        after_frame, _ = screen_shot(monitor_index, capture_method)
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
    print(
        f"after click timeout/unexpected: state {before_state.label}->{after_state.label}, "
        f"best_diff={best_score:.2f}, best_bottom_diff={best_roi_score:.2f}{saved}",
        flush=True,
    )


def fast_advance_unknown(
    detector: CznDetector,
    monitor: dict,
    monitor_index: int,
    capture_method: str,
    stop_keys: list[str],
    stop_file: Path | None,
    act: bool,
    max_taps: int = DIALOG_BURST_MAX_TAPS,
    tap_delay: float = DIALOG_BURST_TAP_DELAY,
) -> int:
    if stop_requested(stop_keys, stop_file):
        return 0
    print_action(f"advance/continue burst x{max_taps}", CLICK_ADVANCE, act)
    if act:
        return rapid_click_norm(
            CLICK_ADVANCE,
            monitor,
            count=max_taps,
            duration=FAST_CLICK_DURATION,
            interval=tap_delay,
            stop_keys=stop_keys,
            stop_file=stop_file,
        )
    for i in range(max_taps):
        print_action(f"advance/continue burst {i + 1}/{max_taps}", CLICK_ADVANCE, act)
        if sleep_interruptible(tap_delay, stop_keys, stop_file):
            return 0
    return 0


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

    if sleep_interruptible(CHAIN_MENU_TO_FLEE_DELAY, stop_keys, stop_file):
        return clicks

    print_action("no legend chain: click fixed flee", CHAIN_FLEE_POINT, act)
    if act:
        click_norm(CHAIN_FLEE_POINT, monitor, duration=CHAIN_CLICK_DURATION)
        clicks += 1

    if sleep_interruptible(CHAIN_FLEE_TO_CONFIRM_DELAY, stop_keys, stop_file):
        return clicks

    print_action("no legend chain: click fixed confirm", CHAIN_RETURN_CONFIRM_POINT, act)
    if act:
        click_norm(CHAIN_RETURN_CONFIRM_POINT, monitor, duration=CHAIN_CLICK_DURATION)
        clicks += 1
        if sleep_interruptible(CHAIN_AFTER_CONFIRM_DELAY, stop_keys, stop_file):
            return clicks
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


def click_screen_xy(x: int, y: int, duration: float = 0.08) -> None:
    hwnd = window_at(x, y)
    if hwnd:
        ensure_foreground_and_top(hwnd)
    ctypes.windll.user32.SetCursorPos(x, y)
    time.sleep(CLICK_MOVE_DELAY)
    _send_mouse(0x0001, x, y)
    time.sleep(CLICK_ABSOLUTE_MOVE_DELAY)
    _send_mouse(0x0002)
    time.sleep(duration)
    _send_mouse(0x0004)
    time.sleep(CLICK_AFTER_UP_DELAY)


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
    click_screen_xy(x, y, duration=duration)


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
    hwnd = window_at(x, y)
    if hwnd:
        ensure_foreground_and_top(hwnd)
    ctypes.windll.user32.SetCursorPos(x, y)
    sent = 0
    for _ in range(count):
        if stop_requested(stop_keys, stop_file):
            return sent
        _send_mouse(0x0002)
        time.sleep(duration)
        _send_mouse(0x0004)
        sent += 1
        if sleep_interruptible(interval, stop_keys, stop_file):
            return sent
    return sent


def click_frame_point(point: tuple[int, int], monitor: dict, duration: float = 0.08) -> None:
    x = int(monitor["left"] + point[0])
    y = int(monitor["top"] + point[1])
    print(f"click screen=({x},{y}){click_log_suffix(x, y)}", flush=True)
    click_screen_xy(x, y, duration=duration)


def parse_stop_keys(stop_key: str) -> list[str]:
    keys = [key.strip().lower() for key in stop_key.split(",") if key.strip()]
    return [key for key in keys if key in VK_CODES]


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
    fast_start_to_team_enabled: bool
    log_interval: float
    wait_after_team_enter: float


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
        if cfg.stop_file and cfg.stop_file.exists():
            cfg.stop_file.unlink()

        while True:
            if self.should_stop():
                return
            frame, monitor = screen_shot(cfg.monitor_index, cfg.capture_method)
            if not self.runtime.printed_monitor:
                print(f"using monitor {cfg.monitor_index}: {monitor}")
                self.runtime.printed_monitor = True
            state = cfg.detector.detect(frame)
            now = time.time()
            self.log_state(now, state)
            if now - self.runtime.last_action >= self.runtime.next_action_delay:
                if not self.handle_state(frame, monitor, state, now):
                    return
            if sleep_interruptible(cfg.interval, cfg.stop_keys, cfg.stop_file):
                return

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
            cfg.stop_keys,
            cfg.stop_file,
            cfg.post_click_wait,
            action_name=action_name,
            expected_labels=expected_labels,
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
            frame, monitor = screen_shot(cfg.monitor_index, cfg.capture_method)
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
                self.wait_visual(frame, "legend_confirm", {"card_reward", "dream_found"})
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
            self.wait_visual(frame, "legend_confirm", {"card_reward", "dream_found"})
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
        rt.click_count += fast_abandon_no_legend(
            cfg.detector,
            frame,
            monitor,
            cfg.monitor_index,
            cfg.capture_method,
            cfg.stop_keys,
            cfg.stop_file,
            cfg.act,
        )
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
        rt.wait_for_dialog_until = time.time() + cfg.wait_after_team_enter
        rt.dialog_advance_armed = True
        print(f"team enter clicked; dialog advance armed after {cfg.wait_after_team_enter:.1f}s.")
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
            rt.click_count += fast_start_to_team(
                monitor,
                cfg.stop_keys,
                cfg.stop_file,
                cfg.act,
                first_point=click_point,
            )
            if cfg.act:
                rt.wait_for_dialog_until = time.time() + cfg.wait_after_team_enter
                rt.dialog_advance_armed = True
                print(f"start -> team quick chain armed dialog advance after {cfg.wait_after_team_enter:.1f}s.")
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
        if not cfg.advance_on_unknown:
            print("unknown screen: no click. Pass --advance-on-unknown to enable blind advance clicks.")
            self.mark_action(now, DELAY_UNKNOWN_IDLE)
            return True
        if not rt.dialog_advance_armed:
            print("unknown screen: dialog advance is not armed; waiting for a team enter first.")
            self.mark_action(now, DELAY_UNKNOWN_IDLE)
            return not sleep_interruptible(cfg.interval, cfg.stop_keys, cfg.stop_file)
        if rt.wait_for_dialog_until > now:
            remaining = rt.wait_for_dialog_until - now
            print(f"unknown screen: waiting {remaining:.1f}s before dialog advance burst.")
            self.mark_action(now, min(max(remaining, cfg.interval), 1.0))
            return not sleep_interruptible(cfg.interval, cfg.stop_keys, cfg.stop_file)
        rt.wait_for_dialog_until = 0.0
        rt.click_count += fast_advance_unknown(
            cfg.detector,
            monitor,
            cfg.monitor_index,
            cfg.capture_method,
            cfg.stop_keys,
            cfg.stop_file,
            cfg.act,
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
    fast_start_to_team_enabled: bool,
    log_interval: float,
    wait_after_team_enter: float,
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
            fast_start_to_team_enabled=fast_start_to_team_enabled,
            log_interval=log_interval,
            wait_after_team_enter=wait_after_team_enter,
        )
    ).run()


def print_action(label: str, point: tuple[float, float], act: bool) -> None:
    mode = "ACT" if act else "DRY"
    print(f"{mode}: {label} at normalized {point}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="CZN visual detector and cautious automation helper.")
    parser.add_argument("--image", type=Path)
    parser.add_argument("--video", type=Path)
    parser.add_argument("--every-sec", type=float, default=0.25)
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--act", action="store_true", help="Actually click in live mode. Omit for dry-run.")
    parser.add_argument("--interval", type=float, default=LIVE_LOOP_INTERVAL)
    parser.add_argument("--log-interval", type=float, default=LIVE_LOG_INTERVAL, help="Minimum seconds between repeated live state log lines. 0 prints every loop.")
    parser.add_argument("--max-seconds", type=float, default=0.0, help="Stop live mode after this many seconds. 0 means run until stopped/found.")
    parser.add_argument("--max-clicks", type=int, default=0, help="Stop live mode after this many actual clicks. 0 means unlimited.")
    parser.add_argument("--post-click-wait", type=float, default=POST_CLICK_WAIT, help="Wait this many seconds after each click for a real visual change.")
    parser.add_argument(
        "--wait-after-team-enter",
        type=float,
        default=WAIT_AFTER_TEAM_ENTER_BEFORE_DIALOG,
        help="After clicking team enter, wait this many seconds before allowing blind dialog advance bursts.",
    )
    parser.add_argument("--monitor", type=int, default=1, help="monitor index. 1 is primary on this machine; 2 is the secondary display.")
    parser.add_argument(
        "--capture-method",
        choices=["dxgi", "mss"],
        default="dxgi",
        help="Live screenshot backend. DXGI is the default because mss returned stale frames after clicks in this game.",
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

    detector = CznDetector(wide_match_scales=args.wide_match_scales)
    if args.image:
        run_image(detector, args.image, args.out_dir)
    elif args.video:
        run_video(detector, args.video, args.every_sec, args.out_dir)
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
            args.fast_start_to_team,
            args.log_interval,
            args.wait_after_team_enter,
        )
    else:
        parser.error("pass --image, --video, or --live")


if __name__ == "__main__":
    main()
