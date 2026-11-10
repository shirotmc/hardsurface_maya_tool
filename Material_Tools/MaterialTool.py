# -*- coding: utf-8 -*-
"""
Material Manager window (HSTool style) - a separate window, opened from the Model tab.

Python port of "Material Manager" v5.2.0 by Dennis Porter (GPL-3.0)
https://github.com/Bartalon/Material-Manager
The logic lives in Scripts/Python/material_core.py, pure data helpers in material_data.py.

Layout (same visual language as the rest of HSTool: orange frame titles, grey buttons,
green = main action, orange = secondary / destructive)

    Search
    Material List  [name plate | colour swatch (= Assign) | mark]   (scrolls, follows the window height)
    Create / Edit  Lambert Phong Blinn Standard | Custom | Refresh Duplicate Match Rename Delete
    Texture Channels   Color Normal Roughness ...  [+] / [x] for each channel, indicator when occupied
    Color Presets  (tab)   swatches + preset list
    ID Map Baker   (tab)   auto ID, high / low / cage, size, path, Bake
    Tools          UV borders, handedness, colorize, vertex colour, namespace, auto match name, load files
"""
from __future__ import print_function

import os
import json
import io
import sys
import site

import maya.cmds as cmds
import maya.utils

try:
	from importlib import reload
except ImportError:
	pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace('\\', '/')   # HSTool root
TOOL_DIR = ROOT + '/Material_Tools'
site.addsitedir(TOOL_DIR + '/Scripts/Python')

import material_data as data
import material_core as core
reload(data)
reload(core)

WINDOW = 'hs_material_window'
TITLE = 'Material Manager'
SETTING_PATH = ROOT + '/HardSurface_Tool/Database/Setting/HardSurfaceTool_Setting.json'
PRESETS_PATH = TOOL_DIR + '/Data/mm_material_presets.txt'
ICONS = TOOL_DIR + '/Icons/'

OPT = 'hs_mm_'
MIN_W, MIN_H = 330, 560

# colours (same as the rest of HSTool)
GREEN = (0.2, 0.8, 0.5)
ORANGE = (0.8, 0.5, 0.0)
BLUE = (0.115, 0.357, 0.5)
DARK = (0.2, 0.2, 0.2)
BLACK = (0.1, 0.1, 0.1)
GREY = (0.4, 0.4, 0.4)
YELLOW = (0.8, 0.8, 0.5)

BTN_H = 30
ROW_H = 24

# ----------------------------------------------------------------------------- state

_state = {
	'mats': [],            # materials shown in the list (after filter)
	'markers': set(),      # marked materials
	'last_mark': None,
	'last_select': None,
	'job': None,
	'presets': None,       # (swatches, presets)
	'building': False,
}

DEFAULTS = {
	'sort': 0,            # 0 alphabetical / 1 chronological
	'sass': 0,            # sort assigned materials first
	'part': 0,            # include particleCloud
	'attr': 0,            # show attribute editor on select
	'inst': 1,            # apply to instances
	'cind': 1,            # per-component indication
	'find': 0,            # match only in selection
	'appm': 1,            # auto add M_ prefix
	'children': 0,        # report children
	'preset_assign': 1,   # presets: 1 assign to selection / 0 add to scene
	'bk_w': 2048, 'bk_h': 2048, 'bk_d': 16, 'bk_fmt': 0,
	'match_name': 1,
}
FORMATS = ('png', 'tga', 'dds', 'psd')

for _c, _v in data.DEFAULT_SUFFIXES.items():
	DEFAULTS['sfx_' + _c] = _v


def _opt(name):
	key = OPT + name
	default = DEFAULTS[name]
	if cmds.optionVar(ex=key):
		return cmds.optionVar(q=key)
	return default


def _set_opt(name, value):
	key = OPT + name
	if isinstance(value, str):
		cmds.optionVar(sv=[key, value])
	elif isinstance(value, float):
		cmds.optionVar(fv=[key, value])
	else:
		cmds.optionVar(iv=[key, int(value)])


def _bool(name):
	return bool(_opt(name))


# ----------------------------------------------------------------------------- helpers

def _frame_color():
	try:
		with io.open(SETTING_PATH, 'r', encoding='utf-8') as f:
			return json.load(f)['ui']['frame_color']
	except Exception:
		return [0.7, 0.3, 0.0]


def _button_color():
	try:
		with io.open(SETTING_PATH, 'r', encoding='utf-8') as f:
			return json.load(f)['ui']['button_color']
	except Exception:
		return [0.4, 0.4, 0.4]


def _icon(name):
	path = ICONS + name + '.png'
	return path if os.path.isfile(path) else name + '.png'


def _warn(message):
	cmds.warning('Material Manager: ' + message)
	try:
		cmds.inViewMessage(amg='<hl>Material Manager</hl>: ' + message, pos='topCenter', fade=True)
	except Exception:
		pass


def _info(message):
	try:
		cmds.inViewMessage(amg='<hl>Material Manager</hl>: ' + message, pos='topCenter', fade=True)
	except Exception:
		print('Material Manager: ' + message)


def _guard(fn):
	"""Run a UI action: MMError -> a readable warning, anything else -> a short message + the traceback."""
	def wrapper(*args, **kwargs):
		try:
			return fn(*args, **kwargs)
		except core.MMError as e:
			_warn(str(e))
		except Exception as e:
			import traceback
			traceback.print_exc()
			_warn('%s (see Script Editor)' % e)
	wrapper.__name__ = getattr(fn, '__name__', 'action')
	return wrapper


def _modifiers():
	"""(shift, ctrl, alt) of the click that triggered the callback."""
	mod = cmds.getModifiers()
	return bool(mod & 1), bool(mod & 4), bool(mod & 8)


def _bind(fn, *bound):
	"""Callback with fixed arguments; Maya's own extra callback argument is ignored (works on Python 2 and 3)."""
	def callback(*_ignored):
		return fn(*bound)
	return callback


def _control(name):
	return OPT + name


def _exists(control):
	return control and cmds.control(control, q=True, ex=True)


def _load_presets():
	if _state['presets'] is None:
		try:
			with io.open(PRESETS_PATH, 'r', encoding='utf-8', errors='replace') as f:
				_state['presets'] = data.parse_presets(f.read())
		except IOError:
			_state['presets'] = ([], [])
			_warn('mm_material_presets.txt not found: %s' % PRESETS_PATH)
	return _state['presets']


def _presets_by_name():
	swatches, presets = _load_presets()
	return dict((p['name'], p) for p in swatches + presets)


def _search_text():
	if _exists(_control('search')):
		return cmds.textField(_control('search'), q=True, tx=True)
	return ''


def _prefix():
	return _bool('appm')


# ----------------------------------------------------------------------------- material list

def _visible_materials():
	mats = core.all_materials(include_particle=_bool('part'), sort='alpha' if _opt('sort') == 0 else 'scene')
	return core.filter_materials(mats, _search_text())


def _clear_children(layout):
	"""Delete every child of a layout. layout -q -ca gives short names, so the full path is rebuilt from the layout."""
	full = cmds.layout(layout, q=True, fpn=True) if False else None
	for child in cmds.layout(layout, q=True, ca=True) or []:
		try:
			cmds.deleteUI(child)           # children names are unique (controls are created with Maya generated names)
		except RuntimeError:
			pass


def refresh_list(*args):
	"""Rebuild the material list (name plate / swatch / mark for every material)."""
	if not _exists(_control('list_col')) or _state['building']:
		return
	_state['building'] = True
	try:
		mats = _visible_materials()
		assigned = core.assigned_materials(report_children=_bool('children'), per_component=_bool('cind'))
		if _bool('sass'):
			mats = [m for m in mats if m in assigned] + [m for m in mats if m not in assigned]
		_state['mats'] = mats
		_state['markers'] &= set(core.all_materials(include_particle=True))
		col = _control('list_col')
		_clear_children(col)
		_rows.clear()
		cmds.setParent(col)
		default = core.default_material()
		for mat in mats:
			_add_material_row(col, mat, mat in assigned, mat == default)
		if not mats:
			cmds.text(l='No material matches the search.' if _search_text() else 'No material in the scene.',
			          h=40, enable=False, p=col)
		_update_counters(assigned)
		_update_channel_indicators(assigned)
		_update_buttons(assigned)
	finally:
		_state['building'] = False


def _add_material_row(parent, mat, is_assigned, is_default):
	row = cmds.formLayout(p=parent, h=ROW_H)
	col = (0.5, 0.5, 0.5) if len(_state['mats']) > 120 else core.material_color(mat)
	textured = not core.channel_is_empty(mat, 'color') if len(_state['mats']) <= 120 else False
	name_btn = cmds.iconTextButton(style='iconAndTextCentered', al='left', l='  ' + mat, h=ROW_H,
	                               bgc=BLUE if is_assigned else DARK,
	                               ann='Click: select the material\nShift + click: select a range\n'
	                                   'Alt + click: toggle in selection\nCtrl + click: select the objects / faces that use it',
	                               c=_guard(_bind(on_select_material, mat)))
	swatch = cmds.iconTextButton(style='iconOnly', i=_icon('mm_assign'), h=ROW_H, w=ROW_H + 6,
	                             bgc=DARK if textured else col,
	                             ann='Assign %s to the selection%s' % (mat, '\nCtrl + click: invert "apply to instances"'),
	                             c=_guard(_bind(on_assign, mat)))
	mark = cmds.checkBox(l='', v=mat in _state['markers'], w=ROW_H, h=ROW_H,
	                     ann='Mark / unmark %s.\nShift: mark a range. Ctrl: clear all marks.' % mat,
	                     cc=_bind(on_mark, mat))
	cmds.setParent('..')
	cmds.formLayout(row, e=True,
	                af=[(name_btn, 'left', 0), (name_btn, 'top', 0), (name_btn, 'bottom', 0),
	                    (swatch, 'top', 0), (swatch, 'bottom', 0), (mark, 'top', 0), (mark, 'right', 2)],
	                ac=[(name_btn, 'right', 2, swatch), (swatch, 'right', 2, mark)])
	# keep the controls reachable by material name for in-place updates
	_rows[mat] = (name_btn, swatch, mark)


_rows = {}


def _update_counters(assigned=None):
	assigned = core.assigned_materials(report_children=_bool('children'), per_component=_bool('cind')) if assigned is None else assigned
	total = core.all_materials(include_particle=_bool('part'))
	shown = len(_state['mats'])
	label = 'Material List  (%d)' % shown if shown == len(total) else 'Material List  (%d of %d - filtered)' % (shown, len(total))
	if _exists(_control('list_frame')):
		cmds.frameLayout(_control('list_frame'), e=True, l=label)
	if _exists(_control('count_txt')):
		cmds.text(_control('count_txt'), e=True, l='%d on selection   |   %d marked' % (len(assigned), len(_state['markers'])))
	if _exists(_control('search')):
		cmds.textField(_control('search'), e=True, bgc=YELLOW if _search_text() else (0.2, 0.2, 0.2))


def _update_buttons(assigned=None):
	assigned = core.assigned_materials(report_children=_bool('children'), per_component=_bool('cind')) if assigned is None else assigned
	targets = _target_materials(assigned)
	protected = not targets or all(core.is_default_material(m) for m in targets)
	for key in ('rename', 'delete'):
		if _exists(_control(key)):
			cmds.iconTextButton(_control(key), e=True, en=not protected)
	if _exists(_control('hand_btn')):
		cmds.iconTextButton(_control('hand_btn'), e=True, i=_icon({'right': 'tc_rhand', 'left': 'tc_lhand', 'mixed': 'tc_bhand', 'none': 'tc_nhand'}[core.handedness()]))


def _update_channel_indicators(assigned=None):
	assigned = core.assigned_materials() if assigned is None else assigned
	occupied = set(core.occupied_channels(assigned))
	for channel in data.CHANNELS:
		ind = _control('ind_' + channel)
		if _exists(ind):
			cmds.iconTextButton(ind, e=True, bgc=GREEN if channel in occupied else DARK,
			                    ann='%s: %s' % (data.CHANNEL_LABELS[channel], 'occupied' if channel in occupied else 'empty'))


def update_selection_state(*args):
	"""Cheap refresh when only the selection changed (no rebuild of the list)."""
	if not _exists(_control('list_col')) or _state['building']:
		return
	try:
		mats = _visible_materials()
		if mats != _state['mats'] or _bool('sass'):
			refresh_list()
			return
		assigned = core.assigned_materials(report_children=_bool('children'), per_component=_bool('cind'))
		for mat, (name_btn, swatch, mark) in list(_rows.items()):
			if _exists(name_btn):
				cmds.iconTextButton(name_btn, e=True, bgc=BLUE if mat in assigned else DARK)
		_update_counters(assigned)
		_update_channel_indicators(assigned)
		_update_buttons(assigned)
	except Exception:
		refresh_list()


def _target_materials(assigned=None):
	"""Materials the buttons act on: the marked ones, else the ones assigned to the selection."""
	marked = [m for m in _state['mats'] if m in _state['markers']]
	if marked:
		return marked
	sel = cmds.ls(sl=True, l=True) or []
	if len(sel) == 1 and core.is_material(sel[0]):
		return [sel[0]]
	return assigned if assigned is not None else core.assigned_materials(report_children=_bool('children'), per_component=_bool('cind'))


# ----------------------------------------------------------------------------- list actions

def on_select_material(mat):
	shift, ctrl, alt = _modifiers()
	if ctrl:
		count = core.select_material(mat, mode='objects')
		if not count:
			_info('%s is not assigned to anything.' % mat)
		return
	mode = 'range' if shift else 'toggle' if alt else 'replace'
	core.select_material(mat, mode=mode, last=_state['last_select'], ordered=_state['mats'])
	_state['last_select'] = mat
	if _bool('attr'):
		maya.utils.executeDeferred(lambda: _show_attribute_editor(mat))


def _show_attribute_editor(mat):
	try:
		import maya.mel as mel
		mel.eval('showEditor "%s"' % mat)
	except Exception:
		pass


def on_assign(mat):
	_shift, ctrl, _alt = _modifiers()
	to_instances = _bool('inst') != ctrl      # Ctrl inverts the option
	count = core.assign_material(mat, to_instances=to_instances)
	_info('%s assigned to %d object%s / face group%s' % (mat, count, '' if count == 1 else 's', '' if count == 1 else 's'))
	refresh_list()


def on_mark(mat):
	shift, ctrl, _alt = _modifiers()
	value = cmds.checkBox(_rows[mat][2], q=True, v=True) if mat in _rows and _exists(_rows[mat][2]) else True
	if ctrl:
		_state['markers'].clear()
		for m, (_n, _s, cb) in _rows.items():
			if _exists(cb):
				cmds.checkBox(cb, e=True, v=False)
	elif shift and _state['last_mark'] in _state['mats'] and mat in _state['mats']:
		a, b = sorted((_state['mats'].index(_state['last_mark']), _state['mats'].index(mat)))
		for m in _state['mats'][a:b + 1]:
			if _exists(_rows[m][2]):
				cmds.checkBox(_rows[m][2], e=True, v=value)
			(_state['markers'].add if value else _state['markers'].discard)(m)
	else:
		(_state['markers'].add if value else _state['markers'].discard)(mat)
		_state['last_mark'] = mat
	_update_counters()
	_update_buttons()


def clear_markers(*args):
	_state['markers'].clear()
	refresh_list()


def on_search(*args):
	refresh_list()


def clear_search(*args):
	cmds.textField(_control('search'), e=True, tx='')
	refresh_list()


# ----------------------------------------------------------------------------- create / edit

def _ask_name(title, message, text=''):
	result = cmds.promptDialog(title=title, message=message, text=text, button=['OK', 'Cancel'],
	                           defaultButton='OK', cancelButton='Cancel', dismissString='Cancel')
	if result != 'OK':
		return None
	return cmds.promptDialog(q=True, text=True)


def _ask_new_material_name(default, assign_ok=True):
	"""Prompt until the name is free (returns None on cancel)."""
	message = 'Name of the new material.' + ('\nThe "M_" prefix is added automatically.' if _prefix() else '')
	name = default
	while True:
		name = _ask_name('Name Your Material', message, name)
		if name is None:
			return None
		clean = data.sanitize_name(name)
		final = ('M_' + clean) if _prefix() and not clean.startswith('M_') else clean
		if clean and not cmds.objExists(final):
			return clean
		cmds.confirmDialog(title='Error', message='"%s" is empty or already exists. Choose another name.' % final)


def on_quick_material(node_type):
	_shift, ctrl, _alt = _modifiers()
	label = {'lambert': 'Lambert', 'phong': 'Phong', 'blinn': 'Blinn', 'standardSurface': 'Standard'}[node_type]
	if ctrl:                                   # Ctrl: no prompt, just add to the scene
		n = 1
		while cmds.objExists('M_%s%d' % (label, n)):
			n += 1
		name, assign = '%s%d' % (label, n), False
	else:
		name = _ask_new_material_name(label)
		if name is None:
			return
		assign = True
	mat, assigned = core.quick_material(node_type, name, assign=assign, prefix=_prefix())
	_info('%s created%s' % (mat, ' and assigned to %d target%s' % (assigned, '' if assigned == 1 else 's') if assigned else ''))
	refresh_list()


def on_custom_material(*args):
	"""Open Maya's own 'Assign New Material' list for shader types that have no quick button."""
	import maya.mel as mel
	mel.eval('source doCreateAssignNewMaterialTreeLister.mel;')
	sel = cmds.ls(sl=True)
	mel.eval('createAssignNewMaterialTreeLister "%s";' % ('' if sel else core.default_material()))
	cmds.scriptJob(p='assignNewMaterialWindow', e=['RebuildUIValues', lambda: refresh_list()], protected=False) if cmds.window('assignNewMaterialWindow', ex=True) else None


def on_duplicate(*args):
	targets = _target_materials()
	if not targets:
		raise core.MMError('Mark or select a material to duplicate.')
	last = None
	for mat in targets:
		name = _ask_name('Duplicate Material', 'New name for the copy of %s' % mat, data.unprefixed(mat) + '_Copy')
		if name is None:
			break
		last = core.duplicate_material(mat, name, prefix=_prefix())
	if last:
		_info('Duplicated to %s' % last)
	refresh_list()


def on_match(*args):
	shift, ctrl, _alt = _modifiers()
	targets = _target_materials()
	if not targets:
		raise core.MMError('Mark or select a material to match.')
	selection_only = _bool('find') != ctrl
	count = core.match_material(targets, selection_only=selection_only)
	_info('%d element%s selected' % (count, '' if count == 1 else 's'))


def on_rename(*args):
	targets = [m for m in _target_materials() if not core.is_default_material(m)]
	if not targets:
		raise core.MMError('Nothing to rename (the default material cannot be renamed).')
	for mat in targets:
		while True:
			name = _ask_name('Rename Material', 'Rename %s' % mat, mat)
			if name is None:
				break
			try:
				core.rename_material(mat, name, prefix=_prefix())
				break
			except core.MMError as e:
				cmds.confirmDialog(title='Error', message=str(e))
	_state['markers'].clear()
	refresh_list()


def on_delete(*args):
	targets = [m for m in _target_materials() if not core.is_default_material(m)]
	if not targets:
		raise core.MMError('Nothing to delete (the default material cannot be deleted).')
	assigned = core.assigned_materials()
	if len(targets) > 1 and set(targets) == set(assigned):
		if cmds.confirmDialog(title='Confirm', message='Really delete all materials assigned to this selection?',
		                      button=['Yes', 'No'], defaultButton='No', cancelButton='No', dismissString='No') != 'Yes':
			return
	count = core.delete_materials(targets)
	_state['markers'].clear()
	_info('%d material%s deleted' % (count, '' if count == 1 else 's'))
	refresh_list()


# ----------------------------------------------------------------------------- channels

def on_channel_add(channel):
	mats = core.assigned_materials()
	marked = [m for m in _state['mats'] if m in _state['markers']]
	mats = marked or mats
	if not mats:
		raise core.MMError('Select an object or mark a material first.')
	if len(mats) > 1:
		picked = _choose_material(mats, 'Choose the material that gets the %s map' % data.CHANNEL_LABELS[channel].lower())
		if not picked:
			return
		mats = [picked]
	sel = cmds.ls(sl=True, l=True) or []
	tex = core.connect_file(mats[0], channel)
	if sel:
		cmds.select(sel, r=True)
	if tex:
		_info('%s: %s connected' % (mats[0], data.CHANNEL_LABELS[channel].lower()))
	refresh_list()


def on_channel_delete(channel):
	mats = [m for m in _state['mats'] if m in _state['markers']] or core.assigned_materials()
	if not mats:
		raise core.MMError('Select an object or mark a material first.')
	removed = 0
	for mat in mats:
		removed += core.delete_channel(mat, channel)
	_info('%s channel cleared (%d node%s deleted)' % (data.CHANNEL_LABELS[channel], removed, '' if removed == 1 else 's'))
	refresh_list()


def on_channels_clear(*args):
	mats = [m for m in _state['mats'] if m in _state['markers']] or core.assigned_materials()
	if not mats:
		raise core.MMError('Select an object or mark a material first.')
	if cmds.confirmDialog(title='Clear all channels', message='Delete every texture of %d material%s?' % (len(mats), '' if len(mats) == 1 else 's'),
	                      button=['Clear', 'Cancel'], defaultButton='Cancel', cancelButton='Cancel', dismissString='Cancel') != 'Clear':
		return
	for mat in mats:
		core.clear_channels(mat)
	refresh_list()


def _choose_material(mats, title):
	buttons = list(mats[:8]) + ['Cancel']
	result = cmds.confirmDialog(title='Multiple Materials', message=title, button=buttons, cancelButton='Cancel', dismissString='Cancel')
	return None if result == 'Cancel' else result


def on_load_from_folder(*args):
	"""Find and connect all the textures of the selected / marked materials from one folder."""
	mats = [m for m in _state['mats'] if m in _state['markers']] or core.assigned_materials()
	mats = [m for m in mats if not core.is_default_material(m)]
	if not mats:
		raise core.MMError('Select an object (or mark materials) that have their own material first.')
	picked = cmds.fileDialog2(fm=3, okc='Search From Here', cap='Folder with the textures')
	if not picked:
		return
	suffixes = _suffix_table()
	cmds.waitCursor(state=True)
	try:
		try:
			connected, report = core.load_textures_from_folder(mats, picked[0], suffixes, match_name=_bool('match_name'))
		except data.TooManyFolders as e:
			raise core.MMError('That folder is too big to search (%s). Choose a more specific folder.' % e)
	finally:
		cmds.waitCursor(state=False)
	_info('%d texture%s connected' % (connected, '' if connected == 1 else 's'))
	if report:
		print('\n'.join('Material Manager: ' + line for line in report))
	refresh_list()


def _suffix_table():
	return dict((c, data.parse_suffixes(_opt('sfx_' + c))) for c in data.DEFAULT_SUFFIXES)


def open_suffix_window(*args):
	name = _control('sfx_win')
	if cmds.window(name, ex=True):
		cmds.deleteUI(name, window=True)
	cmds.window(name, title='Load Files - Suffixes', p=WINDOW, rtf=True, mnb=False, mxb=False)
	cmds.columnLayout(adj=True, rs=4, cw=300)
	cmds.text(l='File name endings used to find each map.\nSeparate several with commas (e.g. _A, _BaseColor).', al='left', h=36)
	cmds.rowColumnLayout(nc=2, cw=[(1, 90), (2, 200)], adj=2, cs=[(2, 5)])
	fields = {}
	for channel in ('color', 'normal', 'roughness', 'metallic', 'specular', 'emissive', 'transparency', 'occlusion'):
		cmds.text(l=data.CHANNEL_LABELS[channel] + ':', al='right', h=ROW_H)
		fields[channel] = cmds.textField(tx=_opt('sfx_' + channel), h=ROW_H)
	cmds.setParent('..')
	match = cmds.checkBox(l='Match file name to material name', v=_bool('match_name'),
	                      ann='When on, the file name must contain the material name (without "M_")')

	def save(*a):
		for channel, field in fields.items():
			_set_opt('sfx_' + channel, cmds.textField(field, q=True, tx=True).strip())
		_set_opt('match_name', cmds.checkBox(match, q=True, v=True))
		cmds.deleteUI(name, window=True)

	def reset(*a):
		for channel, field in fields.items():
			cmds.textField(field, e=True, tx=data.DEFAULT_SUFFIXES[channel])
		cmds.checkBox(match, e=True, v=True)

	cmds.rowColumnLayout(nc=2, cw=[(1, 145), (2, 145)], adj=2, cs=[(2, 5)])
	cmds.button(l='Save', h=BTN_H, bgc=GREEN, c=save)
	cmds.button(l='Reset', h=BTN_H, c=reset)
	cmds.setParent('..')
	cmds.showWindow(name)


# ----------------------------------------------------------------------------- presets

def on_preset(entry):
	assign = _bool('preset_assign')
	_shift, ctrl, _alt = _modifiers()
	if ctrl:
		assign = not assign
	mat, created = core.apply_preset(entry, assign=assign, prefix=_prefix())
	if assign:
		_info('%s %s and assigned' % (mat, 'created' if created else 'reused'))
	else:
		_info('%s added to the scene' % mat)
	refresh_list()


def on_checker(kind):
	_shift, ctrl, _alt = _modifiers()
	mat, created = core.checker_material(kind, assign=not ctrl, prefix=_prefix())
	_info('%s %s' % (mat, 'created' if created else 'reused'))
	refresh_list()


def on_preset_mode(*args):
	value = 1 - int(_opt('preset_assign'))
	_set_opt('preset_assign', value)
	cmds.iconTextButton(_control('preset_mode'), e=True, l='Assign to Selection' if value else 'Add to Scene',
	                    bgc=GREEN if value else ORANGE)


def build_presets_tab(parent):
	swatches, presets = _load_presets()
	col = cmds.columnLayout(p=parent, adj=True, rs=4)
	form = cmds.formLayout(p=col, h=26)
	label = cmds.text(l='Preset Mode:', al='left')
	mode = cmds.iconTextButton(_control('preset_mode'), style='textOnly', l='Assign to Selection' if _bool('preset_assign') else 'Add to Scene',
	                           bgc=GREEN if _bool('preset_assign') else ORANGE, h=24,
	                           ann='Assign to Selection: create the material and assign it.\nAdd to Scene: only create it.\nCtrl + click on a preset inverts the mode.',
	                           c=on_preset_mode)
	cmds.formLayout(form, e=True, af=[(label, 'left', 4), (label, 'top', 5), (mode, 'top', 0), (mode, 'right', 2), (mode, 'bottom', 0)],
	                ac=[(mode, 'left', 6, label)])
	cmds.frameLayout(l='Color ID Swatches', cll=False, p=col, mw=4, mh=4)
	flow = cmds.flowLayout(wr=True, cs=4, rs=4)
	for entry in swatches:
		rgb = data.preset_color(entry)
		cmds.button(l='', w=24, h=24, bgc=rgb, ann='%s (%s)' % (entry['name'], entry['type']), c=_guard(_bind(on_preset, entry)))
	for kind, img, tip in ((0, 'swatch_checker', 'Checker'), (1, 'swatch_checker_green', 'Green checker'), (2, 'swatch_checker_red', 'Red checker')):
		cmds.iconTextButton(style='iconOnly', i=_icon(img), w=24, h=24, ann='%s (Ctrl: add to scene only)' % tip, c=_guard(_bind(on_checker, kind)))
	cmds.setParent(col)
	cmds.frameLayout(l='Material Presets', cll=False, p=col, mw=4, mh=4)
	cmds.scrollLayout(cr=True, hst=0, h=260, bgc=(0.18, 0.18, 0.18))
	grid = cmds.rowColumnLayout(nc=2, cw=[(1, 150), (2, 150)], adj=2, cs=[(2, 3)], rs=[(1, 2)])
	for entry in presets:
		rgb = data.preset_color(entry)
		cmds.iconTextButton(style='iconAndTextCentered', al='left', l='  ' + entry['name'].replace('_', ' '), h=20, bgc=rgb,
		                    ann='%s - %s' % (entry['name'], entry['type']), c=_guard(_bind(on_preset, entry)))
	return col


# ----------------------------------------------------------------------------- baker

def _bk_field(name):
	return _control('bk_' + name)


def _bk_text(name):
	return cmds.textField(_bk_field(name), q=True, tx=True) if _exists(_bk_field(name)) else ''


def _bk_list(name):
	return [s for s in _bk_text(name).split(', ') if s]


def on_store_mesh(kind):
	_shift, ctrl, _alt = _modifiers()
	field = _bk_field(kind)
	if ctrl:
		cmds.textField(field, e=True, tx='')
	else:
		sel = [s for s in (cmds.ls(sl=True, l=True) or []) if not core.is_component(s) and not core.is_material(s)
		       and core.selection_shapes([s])]
		if not sel:
			if _bk_text(kind):
				cmds.textField(field, e=True, tx='')
			else:
				raise core.MMError('Select the mesh(es) to load.')
		else:
			if kind == 'lp' and len(sel) > 1:
				sel = sel[:1]
				_info('Only one low poly mesh at a time: using %s' % sel[0].split('|')[-1])
			cmds.textField(field, e=True, tx=', '.join(sel))
	update_baker_state()


def update_baker_state(*args):
	if not _exists(_bk_field('bake_btn')):
		return
	ready = bool(_bk_text('hp') and _bk_text('lp') and _bk_text('path'))
	cmds.button(_bk_field('bake_btn'), e=True, en=ready, bgc=GREEN if ready else (0.3, 0.3, 0.3))
	for key in ('hp', 'lp', 'cage'):
		cmds.iconTextButton(_bk_field('sel_' + key), e=True, vis=bool(_bk_text(key)))


def on_select_stored(kind):
	items = [i for i in _bk_list(kind) if cmds.objExists(i)]
	if items:
		cmds.select(items, r=True)
	else:
		_warn('The loaded meshes no longer exist.')


def on_bk_adjust(which, factor):
	ctl = _bk_field(which)
	value = cmds.intField(ctl, q=True, v=True)
	value = int(round(value * factor))
	value = max(2, min(128, value)) if which == 'd' else max(128, min(32768, value))
	cmds.intField(ctl, e=True, v=value)
	_set_opt('bk_' + which, value)


def on_bk_value_changed(which):
	value = cmds.intField(_bk_field(which), q=True, v=True)
	_set_opt('bk_' + which, value)


def on_bk_format(*args):
	index = cmds.optionMenu(_bk_field('fmt'), q=True, sl=True) - 1
	_set_opt('bk_fmt', index)
	path = _bk_text('path')
	if path:
		cmds.textField(_bk_field('path'), e=True, tx=os.path.splitext(path)[0] + '.' + FORMATS[index])


def on_bk_path(*args):
	_shift, ctrl, _alt = _modifiers()
	if ctrl:
		cmds.textField(_bk_field('path'), e=True, tx='')
	else:
		fmt = FORMATS[_opt('bk_fmt')]
		picked = cmds.fileDialog2(fm=0, ff='%s (*.%s);;All Files (*.*)' % (fmt.upper(), fmt), cap='Save the ID map as')
		if picked:
			path = picked[0]
			if not path.lower().endswith('.' + fmt):
				path = os.path.splitext(path)[0] + '.' + fmt
			cmds.textField(_bk_field('path'), e=True, tx=path)
	update_baker_state()


def on_bk_explorer(*args):
	path = _bk_text('path')
	if path and os.name == 'nt':
		os.startfile(os.path.dirname(path))


def on_auto_id(*args):
	by_object = cmds.radioButton(_bk_field('by_obj'), q=True, sl=True)
	sel = [s for s in (cmds.ls(sl=True, l=True) or []) if not core.is_component(s) and not core.is_material(s)]
	if not sel:
		raise core.MMError('Select at least one object.')
	swatches, _presets = _load_presets()
	cmds.progressWindow(title='Assigning colour IDs', progress=0, status='Working...  (Esc to stop)', isInterruptable=True)
	try:
		def progress(done, total):
			cmds.progressWindow(e=True, progress=done if total else 0, status='%d assigned' % done)
			return not cmds.progressWindow(q=True, isCancelled=True)
		count = core.auto_assign_ids(sel, swatches, by_object=bool(by_object), prefix=_prefix(), progress=progress)
	finally:
		cmds.progressWindow(endProgress=True)
	cmds.select(sel, r=True)
	_info('%d colour ID%s assigned' % (count, '' if count == 1 else 's'))
	refresh_list()


def on_bake(*args):
	path = _bk_text('path')
	if os.path.isfile(path):
		if cmds.confirmDialog(title='Confirm Overwrite', message='%s already exists. Overwrite?' % os.path.basename(path),
		                      button=['Overwrite && Bake', 'Cancel'], defaultButton='Cancel', cancelButton='Cancel', dismissString='Cancel') != 'Overwrite && Bake':
			return
	cmds.waitCursor(state=True)
	try:
		out = core.bake_id_map(_bk_list('hp'), _bk_list('lp'), _bk_list('cage'), path,
		                       cmds.intField(_bk_field('w'), q=True, v=True), cmds.intField(_bk_field('h'), q=True, v=True),
		                       cmds.intField(_bk_field('d'), q=True, v=True), FORMATS[_opt('bk_fmt')])
	finally:
		cmds.waitCursor(state=False)
	_info('Baked %s' % out)


def build_baker_tab(parent):
	col = cmds.columnLayout(p=parent, adj=True, rs=4)
	cmds.frameLayout(l='1. Color IDs (optional)', cll=False, p=col, mw=4, mh=4)
	form = cmds.formLayout(h=BTN_H)
	auto = cmds.button(l='Auto-assign color IDs', h=BTN_H, bgc=GREEN,
	                   ann='Gives every element (or object) of the selection a different colour ID material.', c=_guard(on_auto_id))
	cmds.radioCollection()
	by_ele = cmds.radioButton(_bk_field('by_ele'), l='Element', sl=True)
	by_obj = cmds.radioButton(_bk_field('by_obj'), l='Object')
	cmds.setParent('..')
	cmds.formLayout(form, e=True, af=[(auto, 'left', 0), (auto, 'top', 0), (auto, 'bottom', 0), (by_obj, 'right', 2), (by_obj, 'top', 6), (by_ele, 'top', 6)],
	                ac=[(auto, 'right', 6, by_ele), (by_ele, 'right', 6, by_obj)])
	cmds.setParent(col)

	cmds.frameLayout(l='2. Meshes', cll=False, p=col, mw=4, mh=4)
	for kind, label, tip in (('hp', 'High Poly', 'Select the high poly mesh(es), then click. Ctrl + click clears.'),
	                         ('lp', 'Low Poly', 'Select the low poly mesh, then click (one at a time). Ctrl + click clears.'),
	                         ('cage', 'Cage', 'Optional cage mesh(es). Ctrl + click clears.')):
		row = cmds.formLayout(h=BTN_H - 4)
		btn = cmds.button(l=label, w=84, h=BTN_H - 4, ann=tip, c=_guard(_bind(on_store_mesh, kind)))
		field = cmds.textField(_bk_field(kind), ed=False, h=BTN_H - 4)
		sel = cmds.iconTextButton(_bk_field('sel_' + kind), style='iconOnly', i='out_list.png', w=24, h=BTN_H - 4, vis=False,
		                          ann='Select the loaded meshes', c=_bind(on_select_stored, kind))
		cmds.setParent('..')
		cmds.formLayout(row, e=True, af=[(btn, 'left', 0), (btn, 'top', 0), (btn, 'bottom', 0), (sel, 'right', 0), (sel, 'top', 0), (sel, 'bottom', 0),
		                                (field, 'top', 0), (field, 'bottom', 0)],
		                ac=[(field, 'left', 4, btn), (field, 'right', 2, sel)])
	cmds.setParent(col)

	cmds.frameLayout(l='3. Map', cll=False, p=col, mw=4, mh=4)
	size = cmds.rowColumnLayout(nc=6, cw=[(1, 44), (2, 62), (3, 16), (4, 44), (5, 62), (6, 16)], adj=6, cs=[(2, 2), (3, 2), (4, 8), (5, 2), (6, 2)])
	for key, label in (('w', 'Width'), ('h', 'Height')):
		cmds.text(l=label + ':', al='right', h=ROW_H)
		cmds.intField(_bk_field(key), v=int(_opt('bk_' + key)), min=128, max=32768, h=ROW_H, cc=_bind(on_bk_value_changed, key))
		cmds.columnLayout(adj=True)
		cmds.iconTextButton(style='iconOnly', i='trackUp.png', h=12, w=16, c=_bind(on_bk_adjust, key, 2.0))
		cmds.iconTextButton(style='iconOnly', i='trackDown.png', h=12, w=16, c=_bind(on_bk_adjust, key, 0.5))
		cmds.setParent('..')
	cmds.setParent(col)
	cmds.rowColumnLayout(nc=6, cw=[(1, 60), (2, 62), (3, 16), (4, 44), (5, 62), (6, 16)], adj=5, cs=[(2, 2), (3, 2), (4, 8), (5, 2)], p=col)
	cmds.text(l='Dilation:', al='right', h=ROW_H)
	cmds.intField(_bk_field('d'), v=int(_opt('bk_d')), min=2, max=128, h=ROW_H, cc=lambda *a: on_bk_value_changed('d'))
	cmds.columnLayout(adj=True)
	cmds.iconTextButton(style='iconOnly', i='trackUp.png', h=12, w=16, c=lambda *a: on_bk_adjust('d', 2.0))
	cmds.iconTextButton(style='iconOnly', i='trackDown.png', h=12, w=16, c=lambda *a: on_bk_adjust('d', 0.5))
	cmds.setParent('..')
	cmds.text(l='Format:', al='right', h=ROW_H)
	cmds.optionMenu(_bk_field('fmt'), h=ROW_H, cc=on_bk_format)
	for fmt in FORMATS:
		cmds.menuItem(l=fmt)
	cmds.optionMenu(_bk_field('fmt'), e=True, sl=int(_opt('bk_fmt')) + 1)
	cmds.setParent(col)

	cmds.frameLayout(l='4. Output', cll=False, p=col, mw=4, mh=4)
	row = cmds.formLayout(h=BTN_H - 4)
	dest = cmds.button(l='Set Destination', w=100, h=BTN_H - 4, ann='Choose where the ID map is saved. Ctrl + click clears.', c=_guard(on_bk_path))
	path = cmds.textField(_bk_field('path'), ed=False, h=BTN_H - 4, cc=update_baker_state)
	cmds.setParent('..')
	cmds.formLayout(row, e=True, af=[(dest, 'left', 0), (dest, 'top', 0), (dest, 'bottom', 0), (path, 'right', 0), (path, 'top', 0), (path, 'bottom', 0)],
	                ac=[(path, 'left', 4, dest)])
	cmds.rowColumnLayout(nc=2, cw=[(1, 150), (2, 150)], adj=2, cs=[(2, 4)], p=col)
	cmds.button(_bk_field('bake_btn'), l='Bake Color ID Map', h=BTN_H + 6, en=False, c=_guard(on_bake))
	cmds.button(l='Show in Explorer', h=BTN_H + 6, c=_guard(on_bk_explorer))
	cmds.setParent(col)
	return col


# ----------------------------------------------------------------------------- tools

def _selected_objects():
	return [s for s in (cmds.ls(sl=True, l=True) or []) if not core.is_component(s) and not core.is_material(s)]


def tool_uv_borders(*args):
	count = core.harden_texture_borders()
	_info('Hard edges set on %d UV border edge%s' % (count, '' if count == 1 else 's'))


def tool_handedness(*args):
	count = core.toggle_handedness()
	_info('Tangent space switched on %d mesh%s' % (count, '' if count == 1 else 'es'))
	_update_buttons()


def tool_colorize(*args):
	_shift, ctrl, _alt = _modifiers()
	mats = core.assigned_materials()
	if not mats:
		raise core.MMError('Select objects that have materials.')
	count = core.colorize(mats, restore=ctrl, presets=_presets_by_name())
	_info('%d material%s %s' % (count, '' if count == 1 else 's', 'restored' if ctrl else 'colorized'))
	refresh_list()


def tool_vertex_color(*args):
	shift, ctrl, alt = _modifiers()
	if ctrl:
		core.clear_vertex_color()
		_info('Vertex colours cleared')
		return
	if alt:
		core.toggle_vertex_color_display()
		return
	count = core.vertex_color_from_material()
	_info('Vertex colours painted from %d material group%s' % (count, '' if count == 1 else 's'))


def tool_namespace(*args):
	_shift, ctrl, _alt = _modifiers()
	if ctrl:
		import maya.mel as mel
		mel.eval('NamespaceEditor;')
		return
	count = core.remove_namespaces()
	_info('%d namespace%s removed' % (count, '' if count == 1 else 's'))


def tool_auto_match(*args):
	_shift, ctrl, alt = _modifiers()
	prefix = _prefix() != ctrl
	mat, how = core.auto_match_name(use_scene_name=alt, prefix=prefix)
	_info('%s: %s' % (mat, how))
	refresh_list()


# cleanup
def clean_unused(*args):
	n = core.remove_unused_materials()
	_info('%d unused material%s removed' % (n, '' if n == 1 else 's'))
	refresh_list()


def clean_orphans(*args):
	core.remove_orphan_nodes()
	_info('Unused texture / utility nodes removed')
	refresh_list()


def clean_purge(*args):
	if cmds.confirmDialog(title='Purge All', message='Purging removes ALL materials, utilities and textures.\nThis cannot be undone and clears the undo queue!',
	                      button=['Proceed', 'Abort'], defaultButton='Abort', cancelButton='Abort', dismissString='Abort') != 'Proceed':
		return
	core.purge_scene()
	_info('Scene purged')
	refresh_list()


def clean_relate(*args):
	core.relate_all_names()
	_info('File / utility / shading group names now follow their material')
	refresh_list()


def clean_prefix(*args):
	n = core.add_m_prefix()
	_info('M_ prefix added to %d material%s' % (n, '' if n == 1 else 's'))
	refresh_list()


# ----------------------------------------------------------------------------- window

def _toggle_option(name):
	def cb(*args):
		_set_opt(name, int(cmds.menuItem(_control('mi_' + name), q=True, cb=True)))
		refresh_list()
	return cb


def _build_menu():
	def check(label, key, tip=''):
		cmds.menuItem(_control('mi_' + key), l=label, cb=_bool(key), ann=tip, c=_toggle_option(key))

	cmds.menu(l='Sorting', tearOff=False)
	cmds.radioMenuItemCollection()
	cmds.menuItem(l='Sort Alphabetically', rb=_opt('sort') == 0, c=lambda *a: (_set_opt('sort', 0), refresh_list()))
	cmds.menuItem(l='Sort Chronologically', rb=_opt('sort') == 1, c=lambda *a: (_set_opt('sort', 1), refresh_list()))
	cmds.menuItem(divider=True)
	check('Assigned Materials First', 'sass')
	cmds.menuItem(divider=True)
	cmds.menuItem(l='Clear All Marks', c=clear_markers)
	cmds.menuItem(l='Reset Search and Sorting', c=lambda *a: (cmds.textField(_control('search'), e=True, tx=''), _set_opt('sort', 0), _set_opt('sass', 0), clear_markers()))

	cmds.menu(l='Options', tearOff=False)
	check('Apply to Instances', 'inst', 'Assign to every instance of an object')
	check('Per-component Indication', 'cind', 'Show the materials of the selected faces, not of the whole object')
	check('Report Children', 'children', 'Include child objects when reporting the materials of the selection')
	check('Match Only in Selection', 'find', 'Match Material only looks inside the current selection')
	check('Auto "M_" Prefix', 'appm', 'New / renamed materials get the M_ prefix')
	check('Show Attribute Editor on Select', 'attr')
	check('Include particleCloud', 'part')
	cmds.menuItem(divider=True)
	cmds.menuItem(l='Texture File Suffixes...', c=open_suffix_window)

	cmds.menu(l='Tools', tearOff=False)
	cmds.menuItem(l='Load Textures From Folder...', i=_icon('cc_load'), c=_guard(on_load_from_folder))
	cmds.menuItem(divider=True)
	cmds.menuItem(l='UV Texture Border Tool', i=_icon('cc_UVborders'), c=_guard(tool_uv_borders))
	cmds.menuItem(l='Switch Handedness', i=_icon('tc_nhand'), c=_guard(tool_handedness))
	cmds.menuItem(l='Colorize Materials', i=_icon('cc_colorize'), c=_guard(tool_colorize))
	cmds.menuItem(l='Material to Vertex Color', i=_icon('cc_vertexColor'), c=_guard(tool_vertex_color))
	cmds.menuItem(l='Remove Namespace', i=_icon('cc_namespace'), c=_guard(tool_namespace))
	cmds.menuItem(l='Auto Match Material Name', i=_icon('cc_autoMatch'), c=_guard(tool_auto_match))

	cmds.menu(l='Cleanup', tearOff=False)
	cmds.menuItem(l='Remove Unused Materials', c=_guard(clean_unused))
	cmds.menuItem(l='Remove Unused Texture / Utility Nodes', c=_guard(clean_orphans))
	cmds.menuItem(divider=True)
	cmds.menuItem(l='Relate File / Utility / Shading Group Names', c=_guard(clean_relate))
	cmds.menuItem(l='Add "M_" Prefix to All Materials', c=_guard(clean_prefix))
	cmds.menuItem(divider=True)
	cmds.menuItem(l='Purge Scene...', c=_guard(clean_purge))

	cmds.menu(l='Help', tearOff=False)
	cmds.menuItem(l='About', c=lambda *a: cmds.confirmDialog(
		title='Material Manager', message='Material Manager - HSTool edition\n\nPython port of Material Manager v5.2.0\nby Dennis Porter (GPL-3.0)\n'
		                                  'https://github.com/Bartalon/Material-Manager'))


def _build_material_controls(parent):
	"""Quick create row + material actions row."""
	cmds.frameLayout(l='Create / Edit', cll=False, p=parent, mw=4, mh=4)
	standard_ok = 'standardSurface' in (cmds.allNodeTypes() or [])
	kinds = [('lambert', 'mat_lambert', 'Lambert'), ('phong', 'mat_phong', 'Phong'), ('blinn', 'mat_blinn', 'Blinn')]
	if standard_ok:
		kinds.append(('standardSurface', 'mat_custom', 'Standard Surface'))
	row = cmds.rowColumnLayout(nc=len(kinds) + 1, adj=len(kinds) + 1, cs=[(i, 3) for i in range(2, len(kinds) + 2)])
	for node_type, icon, label in kinds:
		cmds.iconTextButton(style='iconOnly', i=_icon(icon), w=34, h=34, bgc=DARK, ann='New %s. Ctrl + click: add to the scene without asking a name.' % label,
		                    c=_guard(_bind(on_quick_material, node_type)))
	cmds.iconTextButton(style='textOnly', l='Other shader...', h=34, bgc=DARK, ann="Maya's list of all shader types", c=_guard(on_custom_material))
	cmds.setParent(parent)
	cmds.rowColumnLayout(nc=5, adj=1, cs=[(i, 3) for i in range(2, 6)], p=parent)
	spec = (('refresh', 'mat_reload', 'Refresh the material list', refresh_list),
	        ('duplicate', 'mat_duplicate', 'Duplicate the marked materials (with their textures)', on_duplicate),
	        ('match', 'mat_match', 'Select the objects / faces that use the marked materials.\nCtrl + click: invert "match only in selection".', on_match),
	        ('rename', 'mat_rename', 'Rename the marked / assigned materials (their texture nodes follow)', on_rename),
	        ('delete', 'mat_delete', 'Delete the marked materials and their textures', on_delete))
	cmds.text(l='', h=1)
	for key, icon, tip, fn in spec:
		cmds.iconTextButton(_control(key), style='iconOnly', i=_icon(icon), w=34, h=34, bgc=DARK, ann=tip,
		                    c=_guard(fn) if key != 'refresh' else fn)
	cmds.setParent(parent)


def _build_channel_controls(parent):
	cmds.frameLayout(l='Texture Channels', cll=False, p=parent, mw=4, mh=4)
	icons = {'color': 'cc_diffuse', 'normal': 'cc_normal', 'roughness': 'cc_roughness', 'metallic': 'cc_metallic',
	         'specular': 'cc_spec', 'occlusion': 'cc_occlusion', 'emissive': 'cc_emissive', 'transparency': 'cc_opacity'}
	grid = cmds.rowColumnLayout(nc=8, adj=1, cs=[(i, 3) for i in range(2, 9)])
	for channel in data.CHANNELS:
		cmds.columnLayout(adj=True, rs=2)
		cmds.iconTextButton(style='iconAndTextVertical', i=_icon(icons[channel]), l=data.CHANNEL_LABELS[channel][:6], h=44, bgc=DARK,
		                    ann='Add a %s map to the marked / assigned material' % data.CHANNEL_LABELS[channel].lower(),
		                    c=_guard(_bind(on_channel_add, channel)))
		cmds.iconTextButton(_control('ind_' + channel), style='textOnly', l='x', h=16, bgc=DARK,
		                    ann='%s: empty\nClick: delete this map' % data.CHANNEL_LABELS[channel],
		                    c=_guard(_bind(on_channel_delete, channel)))
		cmds.setParent('..')
	cmds.setParent(parent)
	form = cmds.rowColumnLayout(nc=3, adj=1, cs=[(2, 4), (3, 4)], p=parent)
	cmds.button(l='Load Textures From Folder...', h=BTN_H, ann='Find and connect every map of the marked / assigned materials from a folder',
	            c=_guard(on_load_from_folder))
	cmds.button(l='Suffixes', h=BTN_H, ann='Edit the file name endings used to find the maps', c=open_suffix_window)
	cmds.button(l='Clear All', h=BTN_H, bgc=ORANGE, ann='Delete every texture of the marked / assigned materials', c=_guard(on_channels_clear))
	cmds.setParent(parent)


def _build_tool_buttons(parent):
	cmds.frameLayout(l='Tools', cll=False, p=parent, mw=4, mh=4)
	cmds.rowColumnLayout(nc=6, adj=1, cs=[(i, 3) for i in range(2, 7)])
	spec = (('cc_UVborders', 'UV Border Tool: hard edges on UV shell borders, soft elsewhere', tool_uv_borders),
	        (None, 'Switch handedness of the selected meshes (green channel of the normal map)', tool_handedness),
	        ('cc_colorize', 'Colorize the materials of the selection.\nCtrl + click: restore preset / grey colours', tool_colorize),
	        ('cc_vertexColor', 'Material to vertex colour.\nCtrl: clear vertex colours. Alt: toggle display', tool_vertex_color),
	        ('cc_namespace', 'Remove namespaces from the selection.\nCtrl + click: open Namespace Editor', tool_namespace),
	        ('cc_autoMatch', 'Name the material after its object.\nCtrl: invert M_ prefix. Alt: use the scene name', tool_auto_match))
	for icon, tip, fn in spec:
		if icon is None:
			cmds.iconTextButton(_control('hand_btn'), style='iconOnly', i=_icon('tc_nhand'), w=34, h=34, bgc=DARK, ann=tip, c=_guard(fn))
		else:
			cmds.iconTextButton(style='iconOnly', i=_icon(icon), w=34, h=34, bgc=DARK, ann=tip, c=_guard(fn))
	cmds.setParent(parent)


def open_tool(parent_window=None):
	"""Open (or rebuild) the Material Manager window."""
	if cmds.window(WINDOW, ex=True):
		cmds.deleteUI(WINDOW, window=True)
	_state['markers'] = set()
	_state['last_mark'] = None
	_state['last_select'] = None
	_rows.clear()
	_state['presets'] = None

	kwargs = dict(title=TITLE, menuBar=True, mnb=False, mxb=False, s=True, rtf=False, w=MIN_W + 30, h=700)
	if parent_window and cmds.window(parent_window, ex=True):
		kwargs['p'] = parent_window
	cmds.window(WINDOW, **kwargs)

	frame_bg, button_bg = _frame_color(), _button_color()
	template = 'HSMaterialTemplate'
	if cmds.uiTemplate(template, ex=True):
		cmds.deleteUI(template, uiTemplate=True)
	cmds.uiTemplate(template)
	cmds.frameLayout(defineTemplate=template, bgc=frame_bg)
	cmds.button(defineTemplate=template, bgc=button_bg)
	cmds.setUITemplate(template, pushTemplate=True)

	_build_menu()

	form = cmds.formLayout(_control('root'))
	tabs = cmds.tabLayout(_control('tabs'), cr=True, p=form, imh=3, imw=3)
	cmds.formLayout(form, e=True, af=[(tabs, 'top', 0), (tabs, 'left', 0), (tabs, 'right', 0), (tabs, 'bottom', 0)])

	# ---- tab 1: scene
	t1 = cmds.formLayout(_control('tab_scene'), p=tabs)
	scroll = cmds.scrollLayout(_control('tab_scene_scroll'), cr=True, hst=0, p=t1)
	main = cmds.columnLayout(adj=True, rs=4, p=scroll)

	cmds.frameLayout(l='Search', cll=False, p=main, mw=4, mh=4)
	row = cmds.formLayout(h=26)
	search = cmds.textField(_control('search'), h=26, pht='Search by name or part of a name', tcc=lambda *a: on_search())
	clear = cmds.iconTextButton(style='iconOnly', i='closeObject.png', w=24, h=26, ann='Clear the search', c=clear_search)
	cmds.setParent('..')
	cmds.formLayout(row, e=True, af=[(search, 'left', 0), (search, 'top', 0), (search, 'bottom', 0), (clear, 'right', 0), (clear, 'top', 0), (clear, 'bottom', 0)],
	                ac=[(search, 'right', 3, clear)])
	cmds.setParent(main)

	cmds.frameLayout(_control('list_frame'), l='Material List', cll=False, p=main, mw=4, mh=4)
	cmds.text(_control('count_txt'), l='', al='left', h=18)
	cmds.scrollLayout(_control('list_scroll'), cr=True, hst=0, h=230, bgc=(0.18, 0.18, 0.18))
	cmds.columnLayout(_control('list_col'), adj=True, rs=2)
	cmds.setParent(main)

	_build_material_controls(main)
	_build_channel_controls(main)
	_build_tool_buttons(main)

	cmds.formLayout(t1, e=True, af=[(scroll, 'top', 0), (scroll, 'left', 0), (scroll, 'right', 0), (scroll, 'bottom', 0)])
	cmds.setParent(tabs)

	# ---- tab 2: presets
	t2 = cmds.scrollLayout(_control('tab_presets'), cr=True, hst=0, p=tabs)
	build_presets_tab(t2)

	# ---- tab 3: baker
	t3 = cmds.scrollLayout(_control('tab_baker'), cr=True, hst=0, p=tabs)
	build_baker_tab(t3)

	cmds.tabLayout(tabs, e=True, tabLabel=[(t1, 'Scene'), (t2, 'Color Presets'), (t3, 'ID Map Baker')])
	cmds.setUITemplate(popTemplate=True)

	cmds.scriptJob(e=['SelectionChanged', update_selection_state], p=WINDOW)
	for event in ('NewSceneOpened', 'PostSceneRead'):
		cmds.scriptJob(e=[event, refresh_list], p=WINDOW)
	cmds.scriptJob(e=['Undo', refresh_list], p=WINDOW)
	cmds.scriptJob(e=['Redo', refresh_list], p=WINDOW)
	# the list also changes when nodes are created / renamed outside the tool
	cmds.scriptJob(e=['NameChanged', _deferred_refresh], p=WINDOW)

	cmds.showWindow(WINDOW)
	_set_min_size()
	_enable_width_scaling()
	refresh_list()
	update_baker_state()


_pending = {'refresh': False}


def _deferred_refresh():
	if _pending['refresh']:
		return
	_pending['refresh'] = True

	def run():
		_pending['refresh'] = False
		if cmds.window(WINDOW, ex=True):
			refresh_list()
	maya.utils.executeDeferred(run)


def _set_min_size():
	try:
		try:
			from PySide2 import QtWidgets
			from shiboken2 import wrapInstance
		except ImportError:
			from PySide6 import QtWidgets
			from shiboken6 import wrapInstance
		import maya.OpenMayaUI as omui
		ptr = omui.MQtUtil.findControl(WINDOW)
		if ptr:
			wrapInstance(int(ptr), QtWidgets.QWidget).window().setMinimumSize(MIN_W, MIN_H)
	except Exception:
		pass


def _enable_width_scaling():
	"""Material tool rows already stretch (formLayouts); nothing to scale. Kept as a hook for ui_resize."""
	return None
