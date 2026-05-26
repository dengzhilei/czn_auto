# CZN State Map From Full Recording

Source video:
`C:\Users\123\Videos\NVIDIA\Base Profile\Base Profile 2026.05.24 - 09.35.35.03.mp4`

Review contact sheets:
`vision-automation-research/video_frames/full_review/contact_page_*.jpg`

## Hard Lesson

The full recording shows more states than the first templates covered. Missing states caused false conclusions:

- `return_confirm` modal was not recognized, so the detector kept seeing the dimmed background `flee_button`.
- `choice_screen` and `flee_screen` can coexist visually with overlays; overlay states must win.
- Pixel diff alone is not a flow result. Use explicit state transitions.

## States

| State | Seen At | Visual Anchor | Action | Expected Next |
|---|---:|---|---|---|
| `outer_info` / `start_screen` | 0-2, 24-25, 43-51, 69, 88, 119 | large info panel + bottom-right `进入` | click `进入` | `team_screen` or loading |
| `team_screen` | 3-7, 26, 52-53, 71, 89-91, 120-121 | three character cards + right-bottom `进入` | click team `进入` | loading / battle |
| loading / black | 8-14, 23, 27-33, 42, 54-59, 68, 72-78, 86-87, 92-96, 118, 122-127 | mostly black or loading room | wait / advance only if visible cue | battle |
| battle_dialogue | 15-17, 21-22, 34-36, 40-41, 60-62, 66-67, 78-81, 84-85, 97-106, 128-130, 133-134 | battle scene + dialogue/arrow | click dialogue advance arrow / bottom text area | choice or card reward |
| `choice_screen` | 18, 37, 63, 82, 107, 131-132 | three bottom option cards with cyan glow | if no legend: top-right menu; if legend: click option | `flee_screen` or card reward |
| `flee_screen` | 19-20, 38-39, 64, 114-115 | card info page + orange `脱逃` | click orange `脱逃` | `return_confirm` |
| `return_confirm` | 65, 83 | black modal text `确定要返回吗？` + orange `确认` | click orange `确认` | loading / outer info / team |
| card_reward / card select | 111-117, 135-149 | title `卡牌奖励` + three large cards + confirm button | if `梦之边境` visible: stop; otherwise retry/return | target stop or retry flow |
| `dream_found` | 136-149 | card title `梦之边境` visible | stop | stop |

## Current Minimal Loop

1. From `outer_info` click bottom-right `进入`.
2. From `team_screen` click right-bottom `进入`.
3. During loading/battle dialogue, click only known advance anchor or wait.
4. At `choice_screen`:
   - if `legend_choice` exists, click that option and wait for card reward.
   - otherwise click top-right menu to reach `flee_screen`.
5. At `flee_screen`, click orange `脱逃`.
6. At `return_confirm`, click orange `确认`.
7. Repeat until reward screen appears with `dream_found`.

## Detector Priority

Overlay and terminal states must be checked before background states:

1. `dream_found`
2. `card_reward`
3. `return_confirm`
4. `legend_choice`
5. `choice_screen`
6. `flee_screen`
7. `team_screen`
8. `start_screen`
9. `unknown`
