"""Command-line interface for pycortex.

Registered as the ``pycortex`` console script (see pyproject.toml). Heavy
imports (cortex itself, matplotlib, nibabel) happen inside each command so
that ``pycortex --help`` stays fast and dependency warnings from optional
modules are not triggered by unrelated commands.

See examples/cli/CLI.md for the full command reference and roadmap.
"""

import argparse
import os
import sys


def _die(msg):
    print("error: %s" % msg, file=sys.stderr)
    sys.exit(1)


def _subjects():
    import cortex
    return sorted(s for s in cortex.db.subjects if not s.startswith("."))


def _check_subject(subject):
    """Exit with the list of available subjects if `subject` is unknown."""
    if subject not in _subjects():
        _die("unknown subject %r\navailable subjects: %s"
             % (subject, ", ".join(_subjects())))


def _transform_shapes(subject):
    """{xfmname: expected (z, y, x) data shape} for a subject."""
    import cortex
    from cortex.database import default_filestore
    shapes = {}
    xfmdir = os.path.join(default_filestore, subject, "transforms")
    if not os.path.isdir(xfmdir):
        return shapes
    for name in sorted(os.listdir(xfmdir)):
        try:
            ref = cortex.db.get_xfm(subject, name).reference
            shapes[name] = tuple(int(i) for i in ref.shape[:3][::-1])
        except Exception:
            pass
    return shapes


def _load_data(path, subject, xfmname, cmap=None, vmin=None, vmax=None):
    """(path, subject, xfm) -> Dataview. Accepts NIfTI or pycortex HDF5."""
    import cortex
    if not os.path.exists(path):
        _die("no such file: %s" % path)
    if path.endswith((".hdf", ".h5", ".hf5")):
        return cortex.load(path)
    if subject is None:
        _die("a subject is required for NIfTI input")
    _check_subject(subject)
    kwargs = {}
    if cmap is not None:
        kwargs["cmap"] = cmap
    if vmin is not None:
        kwargs["vmin"] = vmin
    if vmax is not None:
        kwargs["vmax"] = vmax
    try:
        vol = cortex.Volume(path, subject, xfmname, **kwargs)
    except (ValueError, IndexError) as exc:
        import nibabel as nib
        shape = nib.load(path).shape
        lines = ["data %r (shape %s) does not fit subject %r with transform %r: %s"
                 % (os.path.basename(path), "x".join(map(str, shape)), subject,
                    xfmname, exc)]
        shapes = _transform_shapes(subject)
        if shapes:
            lines.append("expected data shapes (z, y, x) per transform:")
            for name, zyx in shapes.items():
                match = "  <-- matches" if tuple(shape[:3][::-1]) == zyx else ""
                lines.append("  %-12s %s%s" % (name, "x".join(map(str, zyx)), match))
        _die("\n".join(lines))
    # auto-computed vmin/vmax are numpy scalars, which break the viewer's
    # metadata JSON; force plain floats
    if getattr(vol, "vmin", None) is not None:
        vol.vmin = float(vol.vmin)
    if getattr(vol, "vmax", None) is not None:
        vol.vmax = float(vol.vmax)
    return vol


# ---------------------------------------------------------------- commands

def cmd_view(args):
    import cortex
    data = _load_data(args.data, args.subject, args.xfm,
                      args.cmap, args.vmin, args.vmax)
    handle = cortex.webgl.show(data, port=args.port,
                               open_browser=not args.no_browser,
                               recache=args.recache)
    # show() returns the WebApp thread (open_browser=False) or a JS client
    # whose .server is that thread
    server = handle if hasattr(handle, "join") else handle.server
    try:
        server.join()
    except KeyboardInterrupt:
        print("\nshutting down")
        server.stop()


def cmd_flatmap(args):
    import matplotlib
    matplotlib.use("Agg")
    from cortex import quickflat
    data = _load_data(args.data, args.subject, args.xfm,
                      args.cmap, args.vmin, args.vmax)
    kwargs = dict(with_rois=args.with_rois, with_sulci=args.with_sulci,
                  with_curvature=args.with_curvature, height=args.height)
    if args.output.endswith(".svg"):
        quickflat.make_svg(args.output, data, height=args.height,
                           with_curvature=args.with_curvature)
    else:
        quickflat.make_png(args.output, data, **kwargs)
    print("wrote %s" % args.output)


def cmd_subjects(args):
    from cortex.database import default_filestore
    print("Pycortex database  (%s)" % default_filestore)
    for name in _subjects():
        sdir = os.path.join(default_filestore, name)
        surfs = sorted(set(f.split("_")[0] for f in
                           os.listdir(os.path.join(sdir, "surfaces"))
                           if "_" in f)) if os.path.isdir(
                               os.path.join(sdir, "surfaces")) else []
        xfmdir = os.path.join(sdir, "transforms")
        xfms = sorted(os.listdir(xfmdir)) if os.path.isdir(xfmdir) else []
        if len(xfms) > 5:
            xfms = xfms[:4] + ["... (%d total)" % len(xfms)]
        print("  %-12s surfaces: %-30s transforms: %s"
              % (name, ", ".join(surfs) or "-", ", ".join(xfms) or "-"))


def _overlay_labels(subject):
    """{layer: [labels]} parsed from the subject's overlays.svg."""
    from cortex.database import default_filestore
    import xml.etree.ElementTree as ET
    svgpath = os.path.join(default_filestore, subject, "overlays.svg")
    if not os.path.exists(svgpath):
        return {}
    label_attr = "{http://www.inkscape.org/namespaces/inkscape}label"
    group = "{http://www.w3.org/2000/svg}g"
    out = {}
    for layer in ET.parse(svgpath).getroot().findall(group):
        lname = layer.get(label_attr)
        if lname is None:
            continue
        labels = set()
        for sub in layer.iter(group):
            slabel = sub.get(label_attr)
            if slabel and slabel not in (lname, "shapes", "labels"):
                labels.add(slabel)
        out[lname] = sorted(labels)
    return out


def cmd_info(args):
    import cortex
    from cortex.database import default_filestore
    _check_subject(args.subject)
    if args.xfm is not None:
        try:
            xfm = cortex.db.get_xfm(args.subject, args.xfm)
        except Exception as exc:
            shapes = _transform_shapes(args.subject)
            _die("cannot load transform %r for %s: %s\navailable: %s"
                 % (args.xfm, args.subject, exc, ", ".join(shapes) or "-"))
        ref = xfm.reference
        zooms = ref.header.get_zooms()[:3]
        print("transform:   %s  (type: coord)" % args.xfm)
        print("reference:   %s  @  %s mm"
              % (" x ".join(str(int(i)) for i in ref.shape[:3]),
                 " x ".join("%.2f" % z for z in zooms)))
        print("expected data shape (z, y, x): %s"
              % (tuple(int(i) for i in ref.shape[:3][::-1]),))
        return

    sdir = os.path.join(default_filestore, args.subject)
    print("subject:     %s" % args.subject)
    print("filestore:   %s" % default_filestore)
    surfdir = os.path.join(sdir, "surfaces")
    surfs = sorted(set(f.split("_")[0] for f in os.listdir(surfdir)
                       if "_" in f)) if os.path.isdir(surfdir) else []
    counts = ""
    try:
        base = "wm" if "wm" in surfs else ("fiducial" if "fiducial" in surfs
                                           else None)
        if base:
            lh = cortex.db.get_surf(args.subject, base, "lh")[0].shape[0]
            rh = cortex.db.get_surf(args.subject, base, "rh")[0].shape[0]
            counts = "   (lh: {:,} verts / rh: {:,} verts)".format(lh, rh)
    except Exception:
        pass
    print("surfaces:    %s%s" % (", ".join(surfs) or "-", counts))
    print("transforms:  %s" % (", ".join(_transform_shapes(args.subject)) or "-"))
    overlays = _overlay_labels(args.subject)
    if overlays:
        print("overlays:    %s" % ", ".join(
            "%s (%d labels)" % (k, len(v)) for k, v in overlays.items() if v))
    anatdir = os.path.join(sdir, "anatomicals")
    anats = sorted(f.split(".")[0] for f in os.listdir(anatdir)) \
        if os.path.isdir(anatdir) else []
    print("anatomicals: %s" % (", ".join(anats) or "-"))


def cmd_download(args):
    from cortex.utils import download_subject
    from cortex.database import default_filestore
    download_subject(subject_id=args.subject, url=args.url,
                     download_again=args.force)
    print("installed subject %r into %s" % (args.subject, default_filestore))


def cmd_xfm_import(args):
    import cortex
    from cortex.xfm import Transform
    _check_subject(args.subject)
    if args.from_fsl:
        if not args.func or not args.anat:
            _die("--from-fsl requires --func and --anat")
        xfm = Transform.from_fsl(args.from_fsl, args.func, args.anat)
    elif args.from_freesurfer:
        if not args.func or not args.fs_subject:
            _die("--from-freesurfer requires --func and --fs-subject")
        xfm = Transform.from_freesurfer(args.from_freesurfer, args.func,
                                        args.fs_subject,
                                        freesurfer_subject_dir=args.fs_dir)
    else:
        _die("one of --from-fsl or --from-freesurfer is required")
    xfm.save(args.subject, args.name, "coord")
    ref = xfm.reference
    zooms = ref.header.get_zooms()[:3]
    print("saved transform %r for %s  (reference: %s @ %s mm)"
          % (args.name, args.subject,
             " x ".join(str(int(i)) for i in ref.shape[:3]),
             " x ".join("%.2f" % z for z in zooms)))


# ------------------------------------------------------------------ parser

def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="pycortex",
        description="pycortex command-line interface. "
                    "See examples/cli/CLI.md for the full reference.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("view", help="open data in the live WebGL viewer")
    p.add_argument("data", help="NIfTI file or pycortex .hdf dataset")
    p.add_argument("subject", nargs="?", help="subject name (not needed for .hdf)")
    p.add_argument("xfm", nargs="?", default="identity",
                   help="transform name (default: identity)")
    p.add_argument("--cmap")
    p.add_argument("--vmin", type=float)
    p.add_argument("--vmax", type=float)
    p.add_argument("--port", type=int)
    p.add_argument("--no-browser", action="store_true")
    p.add_argument("--recache", action="store_true")
    p.set_defaults(handler=cmd_view)

    p = sub.add_parser("flatmap", help="render data to a flatmap image")
    p.add_argument("data")
    p.add_argument("subject", nargs="?")
    p.add_argument("xfm", nargs="?", default="identity")
    p.add_argument("-o", "--output", required=True,
                   help="output image (.png or .svg)")
    p.add_argument("--with-rois", action=argparse.BooleanOptionalAction,
                   default=True)
    p.add_argument("--with-sulci", action="store_true")
    p.add_argument("--with-curvature", action="store_true")
    p.add_argument("--height", type=int, default=1024)
    p.add_argument("--cmap")
    p.add_argument("--vmin", type=float)
    p.add_argument("--vmax", type=float)
    p.set_defaults(handler=cmd_flatmap)

    p = sub.add_parser("subjects", help="list subjects in the filestore")
    p.set_defaults(handler=cmd_subjects)

    p = sub.add_parser("info", help="summarize a subject or a transform")
    p.add_argument("subject")
    p.add_argument("xfm", nargs="?")
    p.set_defaults(handler=cmd_info)

    p = sub.add_parser("download", help="download a prepackaged subject")
    p.add_argument("subject", nargs="?", default="fsaverage")
    p.add_argument("--url", help="custom download URL")
    p.add_argument("--force", action="store_true",
                   help="re-download even if the subject exists")
    p.set_defaults(handler=cmd_download)

    p = sub.add_parser("xfm", help="transform utilities")
    xsub = p.add_subparsers(dest="xfm_command", required=True)
    px = xsub.add_parser("import",
                         help="import an FSL/FreeSurfer registration")
    px.add_argument("subject")
    px.add_argument("name", help="name for the new transform")
    px.add_argument("--from-fsl", metavar="MAT",
                    help="FSL FLIRT .mat file (func -> anat)")
    px.add_argument("--from-freesurfer", metavar="REG",
                    help="FreeSurfer register.dat / .lta file")
    px.add_argument("--func", help="functional NIfTI (transform reference)")
    px.add_argument("--anat", help="anatomical NIfTI (FSL only)")
    px.add_argument("--fs-subject", help="FreeSurfer subject name")
    px.add_argument("--fs-dir", help="FreeSurfer SUBJECTS_DIR override")
    px.set_defaults(handler=cmd_xfm_import)

    args = parser.parse_args(argv)
    try:
        args.handler(args)
    except BrokenPipeError:
        # output piped into head/less that exited early; not an error.
        # point stdout at devnull so the interpreter's exit flush is quiet
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        sys.exit(0)


if __name__ == "__main__":
    main()
