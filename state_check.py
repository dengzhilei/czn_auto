from __future__ import annotations

import argparse
from pathlib import Path

from czn_detector import CznDetector, annotate, print_state, save_image, screen_shot


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture one fresh frame and classify the current CZN state.")
    parser.add_argument("--monitor", type=int, default=1)
    parser.add_argument("--capture-method", choices=["dxgi", "mss"], default="dxgi")
    parser.add_argument("--window-title", help="Capture the client area of the visible window whose title contains this text.")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    frame, monitor = screen_shot(args.monitor, args.capture_method, args.window_title)
    detector = CznDetector()
    state = detector.detect(frame)
    print(f"capture={args.capture_method} monitor={monitor}")
    print_state("fresh_state", state)
    save_image(root / "debug_live" / "fresh_state.jpg", frame)
    save_image(root / "debug_live" / "fresh_state_annotated.jpg", annotate(frame, state))


if __name__ == "__main__":
    main()
