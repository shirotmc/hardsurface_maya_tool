# -*- coding: utf-8 -*-
"""
HardSurface Toolset plug-in: creates the "HardSurface_Tools" menu in Maya's main menu bar.

Maya may execute plug-in files without defining __file__, so the HSTool root is resolved
in several ways (see _resolve_root). Uses only maya.api.OpenMaya (API 2.0) for MFnPlugin.loadPath.
"""
import os
import sys

import maya.cmds as cmds
import maya.mel as mel
import maya.utils

MENU_NAME = "HardSurface_Tools"
_state = {"root": None}


def maya_useNewAPI():
	pass


def _norm(p):
	return os.path.abspath(p).replace("\\", "/")


def _resolve_root(mobject=None):
	# 1) normal case: __file__ exists (also when imported as a module by install.py)
	try:
		return _norm(os.path.dirname(os.path.dirname(__file__)))
	except NameError:
		pass
	# 2) Maya tells us where the plug-in was loaded from
	if mobject is not None:
		try:
			import maya.api.OpenMaya as om2
			load_path = om2.MFnPlugin(mobject).loadPath()
			if load_path:
				return _norm(os.path.dirname(load_path))
		except Exception:
			pass
	# 3) module registered by install.py (HSTool.mod)
	try:
		mod = cmds.getModulePath(moduleName="HSTool")
		if mod:
			return _norm(mod)
	except Exception:
		pass
	# 4) already importable
	for p in sys.path:
		if p and os.path.isdir(os.path.join(p, "HardSurface_Tool")):
			return _norm(p)
	return None


def _command(root):
	return (
		"import sys\n"
		"if r'{root}' not in sys.path:\n"
		"    sys.path.insert(0, r'{root}')\n"
		"from HardSurface_Tool import HardSurfaceTool\n"
		"try:\n"
		"    from importlib import reload\n"
		"except ImportError:\n"
		"    pass\n"
		"reload(HardSurfaceTool)\n"
		"HardSurfaceTool.GUI()\n"
	).format(root=root)


def _create_menu(*args):
	root = _state["root"] or _resolve_root()
	if not root:
		cmds.warning("HSTool: khong xac dinh duoc thu muc HSTool, hay chay lai install.py")
		return
	_state["root"] = root
	if root not in sys.path:
		sys.path.insert(0, root)
	if cmds.menu(MENU_NAME, exists=True):
		cmds.deleteUI(MENU_NAME)
	main_window = mel.eval("$tmp = $gMainWindow;")
	menu = cmds.menu(MENU_NAME, label=MENU_NAME, parent=main_window, tearOff=False)
	cmds.menuItem(label="HardSurface Toolset", parent=menu, command=_command(root))


def initializePlugin(mobject):
	_state["root"] = _resolve_root(mobject)
	# Deferred: the main window may not exist yet when Maya autoloads plug-ins at startup
	maya.utils.executeDeferred(_create_menu)


def uninitializePlugin(mobject):
	try:
		if cmds.menu(MENU_NAME, exists=True):
			cmds.deleteUI(MENU_NAME)
	except Exception:
		pass
