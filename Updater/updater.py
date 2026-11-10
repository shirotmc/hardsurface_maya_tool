# -*- coding: utf-8 -*-
"""
HSTool online updater (GitHub Releases).

Flow: GET releases/latest -> compare tag with local version.json -> download HSTool.zip
      -> verify sha256 (if the release ships HSTool.zip.sha256) -> extract to temp
      -> back up current files -> copy new files over -> rollback on any failure.

Python 2 / 3 compatible (Maya 2018-2025). Standard library only. No git required.
"""
from __future__ import print_function

import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
import zipfile

try:
	from urllib.request import Request, urlopen
except ImportError:  # Python 2
	from urllib2 import Request, urlopen

import maya.cmds as cmds
import maya.utils

HSTOOL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace("\\", "/")
CONFIG_PATH = HSTOOL_ROOT + "/Updater/update_config.json"
VERSION_PATH = HSTOOL_ROOT + "/version.json"
BACKUP_ROOT = os.path.dirname(HSTOOL_ROOT) + "/HSTool_backup"
TIMEOUT = 15
_OPTVAR_LAST_CHECK = "hstool_last_update_check"


# ----------------------------------------------------------------------------- config / version

def _read_json(path, default=None):
	try:
		with io.open(path, "r", encoding="utf-8") as f:
			return json.load(f)
	except Exception:
		return default


def load_config():
	cfg = {"repo": "", "asset_name": "HSTool.zip", "token_env": "HSTOOL_GITHUB_TOKEN",
	       "check_interval_hours": 12, "auto_check_on_startup": True, "preserve": []}
	cfg.update(_read_json(CONFIG_PATH, {}) or {})
	return cfg


def get_local_version():
	return str((_read_json(VERSION_PATH, {}) or {}).get("version", "0"))


def _parse_version(v):
	# "v2026.7" / "2026.12.1" -> (2026, 12, 1)
	return tuple(int(x) for x in re.findall(r"\d+", str(v))) or (0,)


def is_newer(remote, local):
	return _parse_version(remote) > _parse_version(local)


# ----------------------------------------------------------------------------- network

def _headers(cfg, accept="application/vnd.github+json"):
	h = {"Accept": accept, "User-Agent": "HSTool-Updater"}
	token = os.environ.get(cfg.get("token_env", ""), "")  # only needed for private repos
	if token:
		h["Authorization"] = "Bearer " + token
	return h


def _get(url, cfg, accept="application/vnd.github+json"):
	return urlopen(Request(url, headers=_headers(cfg, accept)), timeout=TIMEOUT)


def _is_ssl_error(e):
	reason = getattr(e, "reason", e)
	try:
		import ssl
		if isinstance(reason, ssl.SSLError) or isinstance(e, ssl.SSLError):
			return True
	except ImportError:
		return True  # Python of this Maya has no ssl module at all
	text = (str(e) + " " + str(reason)).upper()
	return "SSL" in text or "CERTIFICATE" in text


def _curl_path():
	p = os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "System32", "curl.exe")
	return p if os.path.isfile(p) else None


def _curl(url, cfg, accept, out_path=None):
	# Fallback when Python's own SSL fails (corporate proxy / antivirus / broken cert store).
	# curl.exe (Windows 10+) uses the Windows certificate store + system proxy and STILL verifies certs.
	curl = _curl_path()
	if not curl:
		raise RuntimeError("Loi SSL va may khong co curl.exe (can Windows 10 tro len)")
	conf = ['header = "{0}: {1}"'.format(k, v) for k, v in _headers(cfg, accept).items()]
	conf.append('url = "{0}"'.format(url))
	cmd = [curl, "-sS", "-L", "--fail", "--max-time", "120", "--config", "-"]
	if out_path:
		cmd += ["-o", out_path]
	flags = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW
	p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=flags)
	out, err = p.communicate("\n".join(conf).encode("utf-8"))
	if p.returncode != 0:
		raise RuntimeError("curl loi ({0}): {1}".format(p.returncode, err.decode("utf-8", "ignore").strip()))
	return out


def _http_text(url, cfg, accept="application/vnd.github+json"):
	try:
		return _get(url, cfg, accept).read().decode("utf-8")
	except Exception as e:
		if not _is_ssl_error(e):
			raise
		return _curl(url, cfg, accept).decode("utf-8")


def fetch_latest_release(cfg):
	repo = cfg.get("repo", "")
	if not re.match(r"^[\w.-]+/[\w.-]+$", repo) or repo == "OWNER/REPO":
		raise RuntimeError("Updater chua duoc cau hinh: hay dien 'repo' trong Updater/update_config.json")
	rel = json.loads(_http_text("https://api.github.com/repos/{0}/releases/latest".format(repo), cfg))
	asset = None
	sha_asset = None
	for a in rel.get("assets", []):
		if a.get("name") == cfg["asset_name"]:
			asset = a
		elif a.get("name") == cfg["asset_name"] + ".sha256":
			sha_asset = a
	if not asset:
		raise RuntimeError("Release {0} khong co file {1}".format(rel.get("tag_name"), cfg["asset_name"]))
	return {"version": rel.get("tag_name", ""), "notes": rel.get("body") or "", "asset": asset, "sha": sha_asset}


def _download(asset, cfg, dest, progress=None):
	# API asset url + octet-stream works for both public and private repos
	try:
		resp = _get(asset["url"], cfg, accept="application/octet-stream")
	except Exception as e:
		if not _is_ssl_error(e):
			raise
		_curl(asset["url"], cfg, "application/octet-stream", out_path=dest)
		return
	total = int(resp.headers.get("Content-Length", 0) or 0)
	done = 0
	with open(dest, "wb") as f:
		while True:
			chunk = resp.read(64 * 1024)
			if not chunk:
				break
			f.write(chunk)
			done += len(chunk)
			if progress and total:
				progress(done, total)


def _sha256(path):
	h = hashlib.sha256()
	with open(path, "rb") as f:
		for chunk in iter(lambda: f.read(1024 * 1024), b""):
			h.update(chunk)
	return h.hexdigest()


# ----------------------------------------------------------------------------- install

def _safe_extract(zip_path, dest):
	dest_abs = os.path.realpath(dest)
	with zipfile.ZipFile(zip_path) as z:
		for member in z.namelist():
			target = os.path.realpath(os.path.join(dest, member))
			if not (target == dest_abs or target.startswith(dest_abs + os.sep)):
				raise RuntimeError("Zip khong an toan (path traversal): " + member)
		z.extractall(dest)


def _find_package_root(extracted):
	# The zip may contain the files at top level or inside one wrapper folder
	for base, dirs, files in os.walk(extracted):
		if "version.json" in files and os.path.isdir(os.path.join(base, "Updater")):
			return base
	raise RuntimeError("Goi update khong hop le (thieu version.json / Updater)")


def _iter_files(root):
	for base, dirs, files in os.walk(root):
		dirs[:] = [d for d in dirs if d != "__pycache__"]
		for fn in files:
			if fn.endswith((".pyc", ".pyo")) or fn == "Thumbs.db":
				continue
			full = os.path.join(base, fn)
			yield os.path.relpath(full, root).replace("\\", "/")


def _apply(new_root, cfg):
	preserve = set(cfg.get("preserve", []))
	stamp = time.strftime("%Y%m%d_%H%M%S")
	backup = os.path.normpath(BACKUP_ROOT + "/" + stamp)
	written = []  # (rel, existed_before)
	try:
		for rel in _iter_files(new_root):
			dst = os.path.join(HSTOOL_ROOT, rel)
			if rel in preserve and os.path.exists(dst):
				continue  # keep user settings
			existed = os.path.exists(dst)
			if existed:
				b = os.path.join(backup, rel)
				if not os.path.isdir(os.path.dirname(b)):
					os.makedirs(os.path.dirname(b))
				shutil.copy2(dst, b)
			if not os.path.isdir(os.path.dirname(dst)):
				os.makedirs(os.path.dirname(dst))
			shutil.copy2(os.path.join(new_root, rel), dst)
			written.append((rel, existed))
	except Exception:
		_rollback(written, backup)
		raise
	_prune_backups()
	return backup


def _rollback(written, backup):
	for rel, existed in reversed(written):
		dst = os.path.join(HSTOOL_ROOT, rel)
		try:
			if existed:
				shutil.copy2(os.path.join(backup, rel), dst)
			elif os.path.exists(dst):
				os.remove(dst)
		except Exception:
			pass


def _prune_backups(keep=3):
	try:
		root = os.path.normpath(BACKUP_ROOT)
		for d in sorted(os.listdir(root))[:-keep]:
			shutil.rmtree(os.path.join(root, d), ignore_errors=True)
	except Exception:
		pass


def install_release(release, cfg, progress=None):
	"""Download + verify + install. Raises on failure (files are rolled back)."""
	tmp = tempfile.mkdtemp(prefix="hstool_update_")
	try:
		zip_path = os.path.join(tmp, "update.zip")
		_download(release["asset"], cfg, zip_path, progress)
		if release.get("sha"):
			sha_file = os.path.join(tmp, "update.sha256")
			_download(release["sha"], cfg, sha_file)
			with io.open(sha_file, "r", encoding="utf-8") as f:
				expected = f.read().split()[0].lower()
			if _sha256(zip_path) != expected:
				raise RuntimeError("Sai checksum SHA256, goi tai ve bi loi hoac bi thay doi")
		extracted = os.path.join(tmp, "x")
		os.makedirs(extracted)
		_safe_extract(zip_path, extracted)
		new_root = _find_package_root(extracted)
		new_version = (_read_json(os.path.join(new_root, "version.json"), {}) or {}).get("version")
		if not new_version:
			raise RuntimeError("Goi update khong co version hop le")
		_apply(new_root, cfg)
		return new_version
	finally:
		shutil.rmtree(tmp, ignore_errors=True)


# ----------------------------------------------------------------------------- UI

def _on_main(fn, *args, **kwargs):
	maya.utils.executeDeferred(lambda: fn(*args, **kwargs))


def _ask_and_install(release, current):
	notes = release["notes"].strip()
	if len(notes) > 600:
		notes = notes[:600] + "..."
	msg = "Co ban moi: {0}  (hien tai: {1})\n\n{2}\n\nCap nhat ngay?".format(release["version"], current, notes)
	if cmds.confirmDialog(title="HSTool Update", message=msg, button=["Update", "Later"],
	                      defaultButton="Update", cancelButton="Later", dismissString="Later") != "Update":
		return
	cfg = load_config()
	cmds.waitCursor(state=True)
	try:
		new_version = install_release(release, cfg)
		cmds.confirmDialog(icn="information", title="HSTool Update",
		                   m="Da cap nhat len {0}.\nHay dong tool va mo lai (khuyen nghi khoi dong lai Maya).".format(new_version))
	except Exception as e:
		cmds.confirmDialog(icn="critical", title="HSTool Update",
		                   m="Cap nhat that bai, file cu da duoc khoi phuc.\n\n{0}".format(e))
	finally:
		cmds.waitCursor(state=False)


def _check_worker(current, silent):
	cfg = load_config()
	try:
		release = fetch_latest_release(cfg)
	except Exception as e:
		if not silent:
			_on_main(cmds.confirmDialog, title="HSTool Update", icn="warning",
			         m="Khong the kiem tra ban cap nhat:\n{0}".format(e))
		return
	if is_newer(release["version"], current):
		_on_main(_ask_and_install, release, current)
	elif not silent:
		_on_main(cmds.confirmDialog, title="HSTool Update", icn="information",
		         m="Ban dang dung phien ban moi nhat ({0}).".format(current))


def check_for_updates_ui(current, silent=False):
	"""Network runs in a thread so Maya never freezes; dialogs are raised on the main thread."""
	t = threading.Thread(target=_check_worker, args=(current, silent))
	t.daemon = True
	t.start()


def check_on_startup(current):
	cfg = load_config()
	if not cfg.get("auto_check_on_startup", True):
		return
	now = time.time()
	last = cmds.optionVar(q=_OPTVAR_LAST_CHECK) if cmds.optionVar(ex=_OPTVAR_LAST_CHECK) else 0
	if now - last < float(cfg.get("check_interval_hours", 12)) * 3600:
		return
	cmds.optionVar(fv=[_OPTVAR_LAST_CHECK, now])
	check_for_updates_ui(current, silent=True)
