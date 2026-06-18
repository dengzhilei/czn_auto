from __future__ import annotations

import argparse
from pathlib import Path

from czn_detector import (
    CAPTURE_METHODS,
    DEFAULT_CAPTURE_METHOD,
    MONITOR_INDEX,
    CznDetector,
    UI_LANGUAGES,
    UI_LANGUAGE,
    annotate,
    print_state,
    resolve_monitor_index,
    save_image,
    screen_shot,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture one fresh frame and classify the current CZN state.")
    parser.add_argument("--monitor", default=MONITOR_INDEX)
    parser.add_argument("--capture-method", choices=sorted(CAPTURE_METHODS), default=DEFAULT_CAPTURE_METHOD)
    parser.add_argument("--ui-language", choices=sorted(UI_LANGUAGES), default=UI_LANGUAGE)
    args = parser.parse_args()
    args.monitor = resolve_monitor_index(args.monitor)

    root = Path(__file__).resolve().parent
    frame, monitor = screen_shot(args.monitor, args.capture_method)
    detector = CznDetector(ui_language=args.ui_language)
    state = detector.detect(frame)
    print(f"capture={args.capture_method} monitor={monitor}")
    print_state("fresh_state", state)
    save_image(root / "debug_live" / "fresh_state.jpg", frame)
    save_image(root / "debug_live" / "fresh_state_annotated.jpg", annotate(frame, state))


if __name__ == "__main__":
    main()
