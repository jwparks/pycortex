# pycortex-cli — command reference

Command-line interface for pycortex. Open the WebGL viewer, export
flatmaps, inspect the database, and manage subjects and transforms
without writing Python.

**Status legend**

| Badge | Meaning |
|---|---|
| `T1` | Tier 1 — implementation target for the hackathon presentation |
| `T2` | Tier 2 — planned, not required now |
| `T3` | Tier 3 — planned; requires external binaries (FreeSurfer / FSL / playwright) |

All example outputs below are the **proposed interface**; values shown for
subject `S1` are real (taken from the pycortex example filestore).

Entry point: `[project.scripts] pycortex = "cortex.cli:main"`. Data
arguments accept a NIfTI path (`.nii`, `.nii.gz`) or a pycortex HDF5
dataset (`.hdf`, loaded via `cortex.load`).

---

## 1. Viewers

### `pycortex view` — `T1`

Open data in the live WebGL viewer (the fsleyes moment).

```
pycortex view <data> <subject> [xfm] [options]
```

| Option | Description |
|---|---|
| `[xfm]` | transform name; defaults to `identity` (anatomical space) |
| `--cmap NAME` | colormap (default from config) |
| `--vmin F --vmax F` | color range |
| `--port N` | fixed server port (useful with SSH tunnels) |
| `--no-browser` | do not open a browser; just print the URL |
| `--recache` | rebuild the subject's surface cache |

```console
$ pycortex view statmap.nii.gz S1 fullhead --cmap RdBu_r --vmin -3 --vmax 3
Started server on port 8899
Open viewer: http://maryjane:8899/mixer.html
Remote session detected -- after forwarding the port, open: http://localhost:8899/mixer.html
```

4D input opens with the timeseries panel available (movie controls →
timeseries). See the timeseries feature documentation.

### `pycortex flatmap` — `T1`

Render data to a flatmap image. Pure file→file, no GUI.

```
pycortex flatmap <data> <subject> [xfm] -o <out.png|out.svg> [options]
```

| Option | Description |
|---|---|
| `-o PATH` | output image; `.svg` selects vector output with ROI layers |
| `--with-rois / --no-rois` | draw ROI outlines (default: on) |
| `--with-sulci` | draw sulci outlines |
| `--with-curvature` | curvature underlay |
| `--height N` | image height in pixels (default 1024) |
| `--cmap / --vmin / --vmax` | color mapping |

```console
$ pycortex flatmap statmap.nii.gz S1 fullhead -o statmap_flat.png --with-rois --with-curvature
wrote statmap_flat.png  (2436 x 1024 px, 28 ROI outlines)
```

### `pycortex static` — `T2`

Write a self-contained static WebGL viewer to a directory (shareable,
no server needed).

```
pycortex static <outdir> <data> <subject> [xfm]
```

```console
$ pycortex static ./viewer_out statmap.nii.gz S1 fullhead
wrote static viewer to ./viewer_out  (open index.html in a browser)
```

### `pycortex snapshot` — `T3` (playwright)

Save 3D surface views from named camera angles, headless.

```
pycortex snapshot <data> <subject> <xfm> -o fig.png --angles lateral_pivot,medial_pivot
```

---

## 2. Database inspection

### `pycortex subjects` — `T1`

```console
$ pycortex subjects
Pycortex database  (/data/jiwoongpark/pycortex/filestore/db)
  S1          surfaces: wm, pia, inflated, flat   transforms: fullhead, retinotopy
  fsaverage   surfaces: wm, pia, inflated, flat   transforms: -
```

### `pycortex info` — `T1`

Summarize one subject, or one transform.

```console
$ pycortex info S1
subject:     S1
filestore:   /data/jiwoongpark/pycortex/filestore/db
surfaces:    wm, pia, inflated, flat   (lh: 152,893 verts / rh: 151,487 verts)
transforms:  fullhead, retinotopy
overlays:    rois (28 labels), sulci (3 labels)
anatomicals: raw
```

```console
$ pycortex info S1 fullhead
transform:   fullhead  (type: coord)
reference:   100 x 100 x 31  @  2.24 x 2.24 x 4.13 mm
expected data shape (z, y, x): (31, 100, 100)
```

### `pycortex rois` — `T2`

```console
$ pycortex rois S1
rois:   V1  V2  V3  V3A  V3B  V4  V7  LO  MT  EBA  FFA  OFA  PPA  OPA  RSC
        Broca  AC  FEF  SEF  FO  IPS  IFSFP  M1F  M1H  M1M  S1F  S1H  S1M
sulci:  CaS  CeS  StS
```

### `pycortex check` — `T2`

Which transform fits this file?

```console
$ pycortex check bold.nii.gz S1
bold.nii.gz: 100 x 100 x 31 x 240  (4D, 240 frames)
matches:     S1 / fullhead  (shape and affine agree)
suggestion:  pycortex view bold.nii.gz S1 fullhead
```

### `pycortex config` — `T2`

```console
$ pycortex config
user config:  /home/user/.config/pycortex/options.cfg
filestore:    /data/jiwoongpark/pycortex/filestore/db
colormaps:    /data/jiwoongpark/pycortex/filestore/colormaps
```

### `pycortex colormaps` — `T2`

List available colormap names (one per line, pipe-friendly).

### `pycortex cache` — `T2`

```
pycortex cache warm  <subject>        # precompute WebGL surface bundle
pycortex cache clear <subject> --yes  # delete cached flatmaps/CTMs
```

---

## 3. Subject setup

### `pycortex download` — `T1`

Fetch a prepackaged subject into the filestore. Zero setup.

```console
$ pycortex download fsaverage
downloading fsaverage ... done
installed subject 'fsaverage' into /data/jiwoongpark/pycortex/filestore/db
```

### `pycortex import fmriprep` — `T2` (no external deps)

Import a subject from fMRIPrep derivatives (needs `fmriprep/` and
`freesurfer/` subfolders in the derivatives directory). Pure file copy.

```console
$ pycortex import fmriprep sub-01 /data/study/derivatives
imported sub-01  (surfaces + transforms from fMRIPrep derivatives)
```

### `pycortex import freesurfer` — `T3` (FreeSurfer)

```console
$ pycortex import freesurfer bert --subjects-dir $SUBJECTS_DIR
imported FreeSurfer subject 'bert' as pycortex subject 'bert'
```

---

## 4. Transforms and alignment

### `pycortex xfm list` — `T2`

```console
$ pycortex xfm list S1
fullhead     coord   reference: 100 x 100 x 31
retinotopy   coord   reference: 72 x 72 x 22
```

### `pycortex xfm import` — `T1`

Convert an existing FSL / FreeSurfer registration into the database.

```
pycortex xfm import <subject> <name> --from-fsl flirt.mat --func func.nii.gz --anat anat.nii.gz
pycortex xfm import <subject> <name> --from-freesurfer register.dat --func func.nii.gz
```

```console
$ pycortex xfm import sub-006 retino --from-fsl flirt.mat --func bold.nii.gz --anat T1w.nii.gz
saved transform 'retino' for sub-006  (reference: 97 x 101 x 91 @ 2.0 mm)
```

### `pycortex xfm export` — `T2`

```
pycortex xfm export <subject> <name> --to-fsl out.mat --anat anat.nii.gz
```

### `pycortex align auto` — `T3` (FreeSurfer; `auto-fsl` variant needs FSL)

Automatic functional↔anatomical alignment, saved into the database.

```console
$ pycortex align auto sub-006 run1 mean_bold.nii.gz
running bbregister ... done  (final cost: 0.4123)
saved transform 'run1' for sub-006
```

### `pycortex align manual` — `T3` (FreeSurfer)

Open FreeView to inspect or hand-tune an alignment:
`pycortex align manual sub-006 run1`.

---

## 5. Masks and QC

### `pycortex mask` — `T2`

```console
$ pycortex mask S1 fullhead -o cortex_mask.nii.gz --type thick
wrote cortex_mask.nii.gz  (54,231 cortical voxels, type=thick)
```

### `pycortex roi-masks` — `T2`

```console
$ pycortex roi-masks S1 fullhead -o rois.nii.gz --index-volume
wrote rois.nii.gz  (index volume, 28 ROIs; left = negative, right = positive)
wrote rois.json    (index -> ROI name)
```

### `pycortex dropout` — `T2`

One-command signal-dropout QC image.

```console
$ pycortex dropout sub-006 NatPAC -o dropout.png
wrote dropout.png  (regions with low EPI signal highlighted)
```

---

## Roadmap

### Tier 1 — hackathon (needed for the presentation)

| Command | Wraps | Effort |
|---|---|---|
| `pycortex view` | `cortex.webgl.show` | small — arg plumbing over existing API |
| `pycortex subjects` | `cortex.db.subjects` | trivial |
| `pycortex info` | `db.get_paths`, `db.get_xfm`, `nibabel` headers | small |
| `pycortex download` | `cortex.utils.download_subject` | trivial |
| `pycortex flatmap` | `cortex.quickflat.make_png/make_svg` | small |
| `pycortex xfm import` | `Transform.from_fsl/.from_freesurfer` + `.save` | small |

Shared plumbing built once: entry point + subparsers, the
`(path, subject, xfm) → Volume / cortex.load` data shim, friendly error
messages (unknown subject → list; shape mismatch → suggest transform).

### Tier 2 — next

`rois`, `check`, `config`, `colormaps`, `cache`, `static`,
`import fmriprep`, `xfm list/export`, `mask`, `roi-masks`, `dropout`.
All zero-dependency; each is a thin wrapper.

### Tier 3 — external tools required

`align auto` / `align auto-fsl` / `align manual` (FreeSurfer / FSL),
`import freesurfer` (FreeSurfer), `snapshot` (playwright + Chromium),
MNI transforms (FSL). Guard each with a clear error when the binary is
missing.

### Out of scope

- `quickflat.make_movie`, `epi2anatspace_fsl`, `anat2epispace_fsl` —
  currently raise `NotImplementedError` in pycortex itself.
- mayavi-based tools (`mayavi_manual`, `fix_wm/fix_pia`) — deprecated
  upstream.

### Implementation notes

- Several wrapped functions block on `input()` prompts
  (`db.make_subj`, `db.clear_cache`, `freesurfer.autorecon`, ...);
  every CLI wrapper needs a `--yes` / `--force` passthrough.
- Import subcommand modules lazily: `cortex.mni` warns at import time
  when `$FSLDIR` is unset, and heavy imports slow every invocation.
- After adding the entry point, one `pip install -e .` re-run is needed
  for the `pycortex` command to appear.
