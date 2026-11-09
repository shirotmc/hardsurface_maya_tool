# -*- coding: utf-8 -*-
"""
Build release assets (run with normal Python, not inside Maya):
    python Updater/build_release.py 2026.8
Writes version.json, then dist/HSTool.zip + dist/HSTool.zip.sha256.
Upload both files to a GitHub Release whose tag is the same version (e.g. v2026.8).
"""
import hashlib, io, os, sys, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {"__pycache__", "dist", ".git"}
SKIP_FILES = {"Thumbs.db"}


def main():
	if len(sys.argv) != 2:
		sys.exit("usage: build_release.py <version>")
	version = sys.argv[1].lstrip("v")
	with io.open(os.path.join(ROOT, "version.json"), "w", encoding="utf-8") as f:
		f.write(u'{\n\t"version": "%s"\n}\n' % version)
	dist = os.path.join(ROOT, "dist")
	if not os.path.isdir(dist):
		os.makedirs(dist)
	zpath = os.path.join(dist, "HSTool.zip")
	with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
		for base, dirs, files in os.walk(ROOT):
			dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
			for fn in files:
				if fn in SKIP_FILES or fn.endswith((".pyc", ".pyo")):
					continue
				full = os.path.join(base, fn)
				z.write(full, os.path.relpath(full, ROOT).replace("\\", "/"))
	with open(zpath, "rb") as f:
		h = hashlib.sha256(f.read()).hexdigest()
	with io.open(zpath + ".sha256", "w", encoding="utf-8") as f:
		f.write(u"%s  HSTool.zip\n" % h)
	print("Built %s (v%s)\nsha256 %s" % (zpath, version, h))


if __name__ == "__main__":
	main()
