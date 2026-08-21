# Timeseries panel — design guide

Reference design for the click-a-voxel timeseries feature (2026 Pycortex Hackathon).
The dark figure `rgb-timeseries-panel-dark.png` is the target look for the in-viewer
panel; the architecture is in `timeseries-flow-figure.svg`.

## Architecture (per Alex Huth's suggestion)

On-demand, server-side. The browser shows one light volume; the 4D data stays in
Python. A click sends `GET /timeseries?voxel=x,y,z&vertex=i&hemi=lh` (extending the
existing picker channel, see `PickerHandler` in `cortex/webgl/view.py`); a new
tornado handler slices the array and returns ~2 KB of JSON:

```json
{"name": "...", "data": [[...]], "channels": ["bold"] | ["R","G","B"],
 "vertex": 12345, "refs": {"stimulus": [...]}}
```

- Scalar `Volume`/`Vertex` (t,z,y,x) or (t,v): `data` has one channel.
- `VolumeRGB`/`VertexRGB`: one channel per color; panel adds the blended color strip.
- The x axis is the volume index (no TR needed). The power spectrum was
  removed from the design (2026-08-21); `rate` remains an optional upstream
  attr controlling movie playback speed only.
- Panel v2+: checkbox + color picker per trace (datasets and 1D reference
  traces), raw / z-scored dropdown, matplotlib-style ticks, click a
  timepoint to seek the brain (re-prioritizes frame streaming).

## Panel layout (see figures)

Bottom panel, docked via the existing side-panel system (`jsplot`/`figure.add`,
precedent: `MovieAxes` in `mriview.js`). Width ratio **timeseries : spectrum = 2 : 1**.

Left (timeseries), stacked rows sharing the time axis:
1. **Color strip** (RGB data only): the blended color per frame, `imshow`-style.
2. One row per channel: line plot, y-range fixed to the data range ([0,1] for RGB),
   dotted midline, channel label on the left in the channel's color.
3. **Playhead**: dashed vertical line across all rows, synced to movie
   `setFrame`; frame counter `frame N / T (TR = x s)` shown top-right.

Right (spectrum): Welch PSD, log power, x from 0 to Nyquist (1/(2·TR)),
one curve per channel, legend inline, subtle grid.

## Style tokens (dark = viewer-native)

| token        | dark        | light       |
|--------------|-------------|-------------|
| background   | `#0D1117`   | `#FFFFFF`   |
| text         | `#E8ECF5`   | `#222222`   |
| muted text   | `#9AA3B5`   | `#5B6579`   |
| spines/grid  | `#3A4250` / `#232B36` | `#B9C2D0` / `#EEEEEE` |
| R / G / B    | `#FF6B6B` `#5DD97C` `#6FA8FF` | `#D64545` `#3A9E4D` `#3B6FD4` |
| single-channel BOLD line | `#6FA8FF` | `#2E90D9` |
| playhead     | `#FFB454` (dashed) | `#E8964A` (dashed) |

Line width 2.4 px equivalent. Fonts: viewer default sans; monospace for coordinates.

## Behavior

- Click re-plots immediately (single fetch, no debounce needed at ~2 KB).
- Header shows the picked location: `voxel (x, y, z)` or `vertex N · subject`.
- Panel works with or without movie mode; playhead only renders when a movie is
  loaded. Cost per click is independent of run length — never preload the 4D data
  for this panel.

Mockup figures were generated with matplotlib (synthesized AR-smoothed + slow-
oscillation traces); the conversation that produced them also validated the
measured costs of the current all-frames movie path (~314 ms/frame packing,
~3.2 MB/frame for a 97×101×91 volume).
