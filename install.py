# -*- coding: utf-8 -*-
"""
HSTool one-time installer (no server needed).
Drag this file into the Maya viewport. It registers HSTool as a Maya module
(Documents/maya/modules/HSTool.mod) pointing at wherever this folder lives,
and creates the "HardSurface_Tools" menu. After that, updates come from the
in-tool Update menu (GitHub Releases).
"""
import io
import os
import sys

import maya.cmds as cmds

PLUGIN = "HardSurface_Toolset_Plugin.py"


def onMayaDroppedPythonFile(*args):
	install()


def _unload_stale_plugins(correct_file):
	# Unload/forget copies of this plug-in loaded from a different (old) location
	try:
		loaded = cmds.pluginInfo(q=True, listPlugins=True) or []
	except Exception:
		return
	for name in loaded:
		if os.path.basename(name) != PLUGIN:
			continue
		try:
			path = cmds.pluginInfo(name, q=True, path=True)
		except Exception:
			path = name
		if os.path.normcase(os.path.normpath(path)) != os.path.normcase(os.path.normpath(correct_file)):
			try:
				cmds.unloadPlugin(name)
			except Exception:
				pass


def install():
	root = os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")
	plug_path = root + "/plug-ins"
	plugin_file = plug_path + "/" + PLUGIN

	if not os.path.isfile(plugin_file):
		cmds.confirmDialog(icn="critical", title="HSTool",
		                   m="Khong tim thay file plug-in:\n{0}\n\nCo the folder bi giai nen long nhau (HSTool/HSTool/...). "
		                     "install.py phai nam ngay trong folder HSTool chua cac thu muc Check_Tools, Model_Tools, plug-ins...".format(plugin_file))
		return

	# 1) Register module for future Maya sessions
	try:
		mod_dir = os.path.join(cmds.internalVar(userAppDir=True), "modules")
		if not os.path.isdir(mod_dir):
			os.makedirs(mod_dir)
		with io.open(os.path.join(mod_dir, "HSTool.mod"), "w", encoding="utf-8") as f:
			f.write(u"+ HSTool 1.0 {0}\n".format(root))
			f.write(u"scripts: .\n")
			f.write(u"MAYA_PLUG_IN_PATH +:= plug-ins\n")
	except Exception as e:
		cmds.warning("HSTool: khong ghi duoc HSTool.mod: {0}".format(e))

	# 2) Current session: make modules importable and drop plug-ins loaded from old locations
	if root not in sys.path:
		sys.path.insert(0, root)
	if plug_path not in sys.path:
		sys.path.insert(0, plug_path)
	_unload_stale_plugins(plugin_file)

	# 3) Create the menu directly (does not depend on MAYA_PLUG_IN_PATH / plug-in manager)
	try:
		import HardSurface_Toolset_Plugin as hs_plugin
		try:
			from importlib import reload
		except ImportError:
			pass
		reload(hs_plugin)
		hs_plugin._create_menu()
	except Exception as e:
		cmds.confirmDialog(icn="critical", title="HSTool", m="Khong tao duoc menu HSTool:\n{0}".format(e))
		return

	# 4) Best effort: load plug-in so the menu also appears after restarting Maya
	autoload_msg = ""
	try:
		cmds.loadPlugin(plugin_file, quiet=True)
		try:
			cmds.pluginInfo(plugin_file, e=True, autoload=True)
		except Exception:
			pass
	except Exception as e:
		autoload_msg = "\n\n(Luu y: chua dat duoc tu dong nap khi mo lai Maya: {0})".format(e)

	cmds.confirmDialog(icn="information", title="HSTool",
	                   m="HSTool installed at:\n{0}\n\nMenu: HardSurface_Tools{1}".format(root, autoload_msg))
