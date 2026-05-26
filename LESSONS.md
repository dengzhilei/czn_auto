# CZN Automation Hard Rules

These rules come from actual failures during this task. Treat them as higher priority than quick fixes.

1. Never judge current game state from an old saved screenshot.
   Always run `python .\czn_auto\state_check.py` or capture a fresh monitor-1 frame before making a conclusion.

2. Do not use generic visual diff as proof of success.
   Animation, sparkles, cursor highlights, and menu glow can change pixels without changing flow state.

3. A click is successful only if the expected state transition happens.
   Examples: `choice_screen -> return_info/flee_screen`, `flee_screen -> return_confirm`, `return_confirm -> start/team/unknown`.

4. Detection priority must handle overlays first.
   Confirmation modals can leave underlying buttons visible. Detect modal states before background page states.

5. Do not infer "button did not trigger" while a modal or next page is visible.
   If the screen changed into a new UI, the click worked. The missing piece is state recognition.

6. Do not build state coverage from a few cropped frames.
   Review the full recording and list every intermediate page before running loops.

7. Keep current-state debugging single-source.
   `state_check.py` is the authority for current live state. Fresh screenshot, printed state, saved annotated image.

8. When adding a click action, define:
   current state, click target, expected next state, timeout, and failure screenshot.

9. Do not keep clicking unknown states if a known overlay/page might be present.
   First improve recognition; then resume automation.

10. If user says a screen changed and my state says otherwise, assume my detector is wrong until proven with a fresh screenshot.

11. Treat template matches as candidates, not final state proof.
    Lower-priority templates can match inside other pages. Use the final `label`, the full fresh screenshot, and expected transition together.
