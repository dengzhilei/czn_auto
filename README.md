# CZN Visual Automation Prototype

This is a cautious prototype for the recorded loop:

1. Advance until the three-option scene.
2. Detect the golden `传说` word in the right option.
3. Click the right option.
4. Detect `梦之边境` among the three reward cards.
5. Stop when found.

The default live mode is dry-run and only prints intended clicks.

## Offline Tests

```powershell
python czn_auto/czn_detector.py --image "vision-automation-research/video_frames/fine_128_138/frame_0131.5s.jpg" --out-dir czn_auto/out
python czn_auto/czn_detector.py --image "vision-automation-research/video_frames/keyframes/frame_0140.0s.jpg" --out-dir czn_auto/out
python czn_auto/czn_detector.py --video "C:\Users\123\Videos\NVIDIA\Base Profile\Base Profile 2026.05.24 - 09.35.35.03.mp4" --every-sec 0.5 --out-dir czn_auto/out
```

## Live Dry Run

```powershell
python czn_auto/czn_detector.py --live
```

Or double-click:

```text
czn_auto\run_one_click_admin.bat
```

Emergency stop:

```text
Press F8 at any time.
```

Live mode no longer clicks unknown screens by default. To allow blind advance clicks, opt in explicitly:

```powershell
python czn_auto/czn_detector.py --live --advance-on-unknown
```

Even with `--advance-on-unknown`, the script will not click the advance point when it detects the three-choice card panel but fails to match `传说`; it waits instead.

If the three-card reward screen appears but `梦之边境` is not detected, the default planned action is:

```powershell
--no-dream-action retry-top-right
```

Other options:

```powershell
python czn_auto/czn_detector.py --live --no-dream-action confirm
python czn_auto/czn_detector.py --live --no-dream-action none
```

## Live Clicking

Only run this after the dry-run output is stable:

```powershell
python czn_auto/czn_detector.py --live --act
```

Common loop bat:

```text
czn_auto\run_min_loop_admin.bat
```

Single-action test bat:

```text
czn_auto\run_one_click_admin.bat
```

Both admin bats enable `--advance-on-unknown` and `--fast-start-to-team`.

To actually click confirm instead of the top-right retry/menu area when no target card appears:

```powershell
python czn_auto/czn_detector.py --live --act --no-dream-action confirm
```

## Quick Start Chain

To speed up the main screen -> team setup transition, opt into:

```powershell
python czn_auto/czn_detector.py --live --fast-start-to-team
```

Once the main enter button is detected, this taps the enter area several times without waiting for team-screen image recognition between taps. The `run_min_loop_admin.bat` shortcut enables this together with `--advance-on-unknown`.

## Performance Knobs

Live mode defaults are tuned to reduce CPU load:

```powershell
--interval 0.25 --log-interval 1.5 --post-click-wait 4.0
```

The admin bat reads these Python defaults and only passes mode flags.

```powershell
python .\czn_auto\czn_detector.py --live --act --advance-on-unknown --fast-start-to-team
```

Click-followup visual polling uses `0.20s` between screenshots.

Template matching uses a faster single-scale search by default. If UI detection gets flaky on unusual display scaling, try:

```powershell
--wide-match-scales
```

Resolution compatibility assumes same-ratio fullscreen capture. 4K `3840x2160`, 2K `2560x1440`, and 1080P `1920x1080` all use the same normalized ROIs/click points, while templates are scaled from the 4K base size. If the game is windowed, letterboxed, or not 16:9, the detector will print an aspect-ratio warning and matching/clicking may need new templates or window-specific coordinates.

Dialog advance bursts are intentionally blind now: after team enter arms the dialog step, the script sends the configured taps continuously, then returns to visual detection after the burst. Unknown screens outside the main -> team -> dialog flow will not trigger the burst.

After clicking team enter, blind dialog bursts are delayed by the Python default:

```powershell
WAIT_AFTER_TEAM_ENTER_BEFORE_DIALOG = 4.0
```

Set it higher in `czn_detector.py` if the loading/entry animation is still being clicked, or set it to `0` to disable this cooldown.

Debug screenshots are off by default to avoid filling the repository with large runtime captures. Set `SAVE_VISUAL_CHANGE_DEBUG = True` in `czn_detector.py` only when diagnosing a transition.

## Windows Release Build

Build a portable Windows app that does not require Python on the target machine:

```text
build_release.bat
```

The portable build is written to:

```text
dist\CZNAuto
```

If Inno Setup is installed and `ISCC.exe` is on `PATH`, the same script also creates an installer under:

```text
dist\installer
```

GitHub Actions also has a manual `Windows Release` workflow that builds the portable zip and installer artifacts on Windows.

Published users should run:

```text
run_min_loop.bat
```

or use the installed Start Menu shortcut. `CZNAuto.exe` itself is a console program and expects command-line arguments; the bat files and installer shortcuts provide the usual live-mode arguments.
