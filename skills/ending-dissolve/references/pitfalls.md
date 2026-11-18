# Ending dissolve — parameters and pitfalls

## Parameter table

| Knob | Default | Range | Affected metrics | Side effect |
|---|---|---|---|---|
| `gblur_sigma` | 8 | see the global params.yaml | laplacian_var | Base blur radius; the larger the softer |
| `gamma` | 0.68 | 0.40–1.00 (step 0.02) | V, dark_pct | Dimming factor; 0.68 came out of the reference request to dim by 1.5x |
| `mix` | 0.28 | 0–0.60 (step 0.02) | motion_p90, laplacian_var | Share of the heavier blur in the blend; the higher it is the softer |
| `dissolve_frames` | — | see the global params.yaml | — | Currently only recorded in plan.json, it does not drive the filter chain |

## Acceptance thresholds

- `laplacian_var` clearly lower than in the body of the cut: the main evidence that the frame is soft.
- `dark_pct < 2%`: dimming too far creates large dark areas.
- `motion_p90` drops: blurring smooths the frame-to-frame difference.
- Pull several consecutive frames to confirm the blur is continuous rather than alternating between sharp and soft.

## Known pitfalls

- Use `blend all_expr='A*keep+B*mix'`, never `all_mode=screen`; the latter raises the U/V planes and tints the frame.
- Both layers need `format=yuv420p` before they are blended, otherwise the pixel formats do not match and the filter fails.
- Both layers are blurred, only at different strengths. One sharp and one soft layer produces exactly the flicker the user complained about.
- `gblur` on this ffmpeg build only accepts a constant sigma, it cannot vary over time.

## Current implementation boundary

A parameterised double blur. The 96-frame cross-dissolve sequence and the continuous blur rhythm that changes every four frames from the reference cut are not migrated; `dissolve_frames` is currently only a record in plan.json and does not drive the filter chain.
