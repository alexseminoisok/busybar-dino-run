#!/usr/bin/env python3
"""Pack the app into an installable .tgz for the bar's "Upload app" button
(web interface) or POST /api/apps/stage.

The bar only unpacks gzip'd POSIX ustar archives WITH directory entries, with
the app id as the top folder (fw 27.13). Files-only archives, GNU/PAX tars and
macOS `tar` output (space-padded octal fields) are rejected with
400 "Cannot unpack", so the archive is built here with tarfile.

    python3 build_package.py            # -> dist/community.dino_run-<version>.tgz
"""
import gzip, io, json, os, tarfile

HERE = os.path.dirname(os.path.abspath(__file__))
APP_ID = "community.dino_run"
SRC = os.path.join(HERE, APP_ID)
SKIP = {".DS_Store"}


def _info(name, size=0, is_dir=False):
    ti = tarfile.TarInfo(name)
    ti.type = tarfile.DIRTYPE if is_dir else tarfile.REGTYPE
    ti.mode = 0o755 if is_dir else 0o644
    ti.size = size
    ti.mtime = 0
    ti.uid = ti.gid = 0
    ti.uname = ti.gname = ""
    return ti


def build():
    version = json.load(open(os.path.join(SRC, "appmeta", "manifest.json")))["version"]
    out_dir = os.path.join(HERE, "dist")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f"{APP_ID}-{version}.tgz")

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.USTAR_FORMAT) as tar:
        tar.addfile(_info(APP_ID + "/", is_dir=True))
        for root, dirs, files in os.walk(SRC):
            dirs.sort()
            rel_root = os.path.relpath(root, HERE)
            for d in dirs:                              # each directory before its files
                tar.addfile(_info(os.path.join(rel_root, d) + "/", is_dir=True))
            for f in sorted(files):
                if f in SKIP:
                    continue
                path = os.path.join(root, f)
                with open(path, "rb") as fh:
                    data = fh.read()
                tar.addfile(_info(os.path.join(rel_root, f), len(data)), io.BytesIO(data))
    with open(out, "wb") as fh:
        fh.write(gzip.compress(buf.getvalue(), compresslevel=9, mtime=0))
    return out


if __name__ == "__main__":
    path = build()
    with tarfile.open(path) as t:
        names = t.getnames()
    print(f"{os.path.relpath(path, HERE)}: {len(names)} entries, {os.path.getsize(path) / 1024:.0f} KB")
