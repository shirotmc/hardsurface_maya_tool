# -*- coding: utf-8 -*-
"""
HSTool one-time installer (no server needed).
Drag this file into the Maya viewport. It registers HSTool as a Maya module
(Documents/maya/modules/HSTool.mod) pointing at wherever this folder lives,
and loads the plug-in so the "HardSurface_Tools" menu appears. After that,
updates come from the in-tool Update menu (GitHub Releases).
"""
import io
import os
import sys

import maya.cmds as cmds


def onMayaDroppedPythonFile(*args):
	install()


def install():
	root = os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")
	mod_dir = os.path.join(cmds.internalVar(userAppDir=True), "modules")
	if not os.path.isdir(mod_dir):
		os.makedirs(mod_dir)
	mod_path = os.path.join(mod_dir, "HSTool.mod")
	with io.open(mod_path, "w", encoding="utf-8") as f:
		f.write(u"+ HSTool 1.0 {0}\n".format(root))
		f.write(u"scripts: .\n")
		f.write(u"MAYA_PLUG_IN_PATH +:= plug-ins\n")

	# Make it work in the current session without restarting
	if root not in sys.path:
		sys.path.insert(0, root)
	plugin = "HardSurface_Toolset_Plugin.py"
	plug_path = root + "/plug-ins"
	cur = os.environ.get("MAYA_PLUG_IN_PATH", "")
	if plug_path not in cur:
		os.environ["MAYA_PLUG_IN_PATH"] = plug_path + os.pathsep + cur
	try:
		if not cmds.pluginInfo(plugin, q=True, loaded=True):
			cmds.loadPlugin(plug_path + "/" + plugin)
		cmds.pluginInfo(plugin, e=True, autoload=True)
		cmds.create_toolset()
	except Exception as e:
		cmds.warning("HSTool: plug-in load failed: {0}".format(e))
	cmds.confirmDialog(icn="information", title="HSTool",
	                   m="HSTool installed at:\n{0}\n\nMenu: HardSurface_Tools".format(root))
