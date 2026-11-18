# Comic panel split — parameters and pitfalls

## Parameter table

| Knob | Default | Range | Affected metrics | Side effect |
|---|---|---|---|---|
| `cells` | 4 | locked | — | The implementation is fixed at four panels |
| `mono_sat` | 0.05 | 0–1 (step 0.05) | V, laplacian_var | Saturation of the black and white panels; the lower it is the more comic the frame reads |
| `color_sat` | 1.40 | 0.5–2.5 (step 0.05) | V | Saturation of the colour panels; one colour and one monochrome pair creates the contrast |
| `contrast` | 1.25 | 0.9–2.0 (step 0.02) | V, dark_pct | Contrast shared by all four panels |
| `beat_align` | true | boolean | cut_rate | Consumed by `lib/plan.py` |

## Acceptance thresholds

- `dark_pct < 2%`: the desaturated panels pull the frame down, and so does a high contrast.
- `V` stable between 100 and 160: the two-tone contrast should not swing the overall brightness much.
- `laplacian_var` rises because of the dividers and the offset crops, which is expected.
- Pull one frame and confirm the cross dividers are visible and the four panels do not show the same content.

## Known pitfalls

- After `split=4` each of the four streams must be cropped to `w//2 x h//2`; mismatched sizes make `hstack`/`vstack` fail outright.
- The offset (48px and `ch-48` here) must stay below half a panel, otherwise the crop reaches past the edge and leaves a black border.
- Cropping the original quadrants and putting them back in place restores the geometry exactly, leaving only a colour difference the eye cannot read as a split. The offsets are mandatory.
- The cross dividers use `drawbox` with `t=fill`, width 4px, offset by 2px to stay centred.

## Current implementation boundary

Regular four panels; arbitrary panel counts and irregular shapes are not supported. The irregular slanted mask from the reference cut needs a pre-generated mask sequence combined with `maskedmerge`, which is not migrated. That is exactly why `cells` is locked.
