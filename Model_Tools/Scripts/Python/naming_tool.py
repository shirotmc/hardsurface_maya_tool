import maya.cmds as cmds


WINDOW_NAME = 'HSNameToolsWindow'
UI = {}
NON_RENAMEABLE = {'front', 'persp', 'top', 'side'}


def _unique(items):
	seen = set()
	result = []
	for item in items:
		if item in seen:
			continue
		seen.add(item)
		result.append(item)
	return result


def _short_name(node):
	return node.rsplit('|', 1)[-1]


def _base_name(node):
	return _short_name(node).rsplit(':', 1)[-1]


def _rename_order(items):
	return sorted(items, key=lambda item: (item.count('|'), item.lower()), reverse=True)


def _display_order(items):
	return sorted(items, key=lambda item: (_base_name(item).lower(), item.lower()))


def _scope_targets():
	scope = cmds.radioButtonGrp(UI['scope'], q=True, select=True)
	if scope == 1:
		nodes = cmds.ls(sl=True, long=True, type='transform') or []
	elif scope == 2:
		selected = cmds.ls(sl=True, long=True, type='transform') or []
		descendants = []
		for node in selected:
			descendants.extend(cmds.listRelatives(node, allDescendents=True, fullPath=True, type='transform') or [])
		nodes = selected + descendants
	else:
		nodes = cmds.ls(objectsOnly=True, long=True, type='transform') or []

	reference_nodes = set(cmds.ls(referencedNodes=True, long=True) or [])
	targets = []
	for node in _unique(nodes):
		if node in reference_nodes:
			continue
		if _base_name(node) in NON_RENAMEABLE:
			continue
		targets.append(node)
	return targets


def _sequence(start, count, digits):
	return [str(start + index).zfill(max(int(digits), 1)) for index in range(count)]


def _apply_names(name_map):
	if not name_map:
		cmds.warning('No transform nodes found for the chosen scope.')
		return []

	renamed = []
	for node in _rename_order(list(name_map.keys())):
		if not cmds.objExists(node):
			continue
		new_name = name_map[node] or _base_name(node)
		renamed.append(cmds.rename(node, new_name))

	if renamed:
		cmds.select(renamed, replace=True)
	return renamed


def _update_rename_preview(*args):
	name = cmds.textFieldGrp(UI['rename_name'], q=True, text=True)
	start = cmds.intFieldGrp(UI['rename_start'], q=True, value1=True)
	digits = cmds.intFieldGrp(UI['rename_digits'], q=True, value1=True)
	cmds.textFieldGrp(UI['rename_preview'], e=True, text='{0}{1}'.format(name, str(start).zfill(max(int(digits), 1))))


def _update_suffix_preview(*args):
	start = cmds.intFieldGrp(UI['suffix_start'], q=True, value1=True)
	digits = cmds.intFieldGrp(UI['suffix_digits'], q=True, value1=True)
	cmds.textFieldGrp(UI['suffix_preview'], e=True, text=str(start).zfill(max(int(digits), 1)))


def rename_sequence(*args):
	targets = _display_order(_scope_targets())
	base = cmds.textFieldGrp(UI['rename_name'], q=True, text=True)
	start = cmds.intFieldGrp(UI['rename_start'], q=True, value1=True)
	digits = cmds.intFieldGrp(UI['rename_digits'], q=True, value1=True)
	name_map = {
		target: '{0}{1}'.format(base, suffix)
		for target, suffix in zip(targets, _sequence(start, len(targets), digits))
	}
	return _apply_names(name_map)


def replace_names(*args):
	targets = _scope_targets()
	search = cmds.textFieldGrp(UI['replace_search'], q=True, text=True)
	replacement = cmds.textFieldGrp(UI['replace_value'], q=True, text=True)
	name_map = {target: _base_name(target).replace(search, replacement) for target in targets}
	return _apply_names(name_map)


def remove_names(*args):
	targets = _scope_targets()
	search = cmds.textFieldGrp(UI['replace_search'], q=True, text=True)
	name_map = {target: _base_name(target).replace(search, '') for target in targets}
	return _apply_names(name_map)


def add_prefix(*args):
	targets = _scope_targets()
	prefix = cmds.textFieldGrp(UI['prefix'], q=True, text=True)
	name_map = {target: prefix + _base_name(target) for target in targets}
	return _apply_names(name_map)


def add_suffix(*args):
	targets = _scope_targets()
	suffix = cmds.textFieldGrp(UI['suffix'], q=True, text=True)
	name_map = {target: _base_name(target) + suffix for target in targets}
	return _apply_names(name_map)


def add_digit_suffix(*args):
	targets = _display_order(_scope_targets())
	start = cmds.intFieldGrp(UI['suffix_start'], q=True, value1=True)
	digits = cmds.intFieldGrp(UI['suffix_digits'], q=True, value1=True)
	name_map = {
		target: _base_name(target) + suffix
		for target, suffix in zip(targets, _sequence(start, len(targets), digits))
	}
	return _apply_names(name_map)


def show_window(parent_window):
	if cmds.window(WINDOW_NAME, ex=True):
		cmds.deleteUI(WINDOW_NAME, window=True)

	cmds.window(WINDOW_NAME, title='HS Naming Tools', p=parent_window, sizeable=False, titleBar=True)
	cmds.columnLayout(adj=True)

	cmds.frameLayout(label='Name Tools', collapsable=False, mw=4, mh=4)
	UI['scope'] = cmds.radioButtonGrp(
		numberOfRadioButtons=3,
		labelArray3=['Selected', 'Hierarchy', 'All'],
		select=1,
	)

	cmds.frameLayout(label='Rename Option', collapsable=False, mw=4, mh=4)
	cmds.columnLayout(adj=True)
	UI['rename_preview'] = cmds.textFieldGrp(label='Preview', text='', editable=False)
	UI['rename_name'] = cmds.textFieldGrp(label='Name', text='', cc=_update_rename_preview)
	cmds.rowColumnLayout(nc=2, cw=[(1, 170), (2, 170)])
	UI['rename_start'] = cmds.intFieldGrp(numberOfFields=1, label='Start At', value1=1, cc=_update_rename_preview)
	UI['rename_digits'] = cmds.intFieldGrp(numberOfFields=1, label='Digit', value1=1, cc=_update_rename_preview)
	cmds.setParent('..')
	cmds.button(label='Rename', h=32, bgc=(0.2, 0.8, 0.5), c=rename_sequence)
	cmds.setParent('..')
	cmds.setParent('..')

	cmds.frameLayout(label='Search Replace Option', collapsable=False, mw=4, mh=4)
	cmds.columnLayout(adj=True)
	UI['replace_search'] = cmds.textFieldGrp(label='Search For', text='')
	UI['replace_value'] = cmds.textFieldGrp(label='Replace With', text='')
	cmds.rowColumnLayout(nc=2, cw=[(1, 170), (2, 170)])
	cmds.button(label='Replace', h=32, bgc=(0.2, 0.8, 0.5), c=replace_names)
	cmds.button(label='Remove', h=32, bgc=(0.48, 0.18, 0.18), c=remove_names)
	cmds.setParent('..')
	cmds.setParent('..')
	cmds.setParent('..')

	cmds.frameLayout(label='Prefix Suffix Option', collapsable=False, mw=4, mh=4)
	cmds.columnLayout(adj=True)
	cmds.rowColumnLayout(nc=2, cw=[(1, 260), (2, 80)])
	UI['prefix'] = cmds.textFieldGrp(label='Prefix', text='')
	cmds.button(label='Add', h=25, bgc=(0.2, 0.8, 0.5), c=add_prefix)
	cmds.setParent('..')
	cmds.rowColumnLayout(nc=2, cw=[(1, 260), (2, 80)])
	UI['suffix'] = cmds.textFieldGrp(label='Suffix', text='')
	cmds.button(label='Add', h=25, bgc=(0.2, 0.8, 0.5), c=add_suffix)
	cmds.setParent('..')
	UI['suffix_preview'] = cmds.textFieldGrp(label='Preview', text='', editable=False)
	cmds.rowColumnLayout(nc=2, cw=[(1, 170), (2, 170)])
	UI['suffix_start'] = cmds.intFieldGrp(numberOfFields=1, label='Start At', value1=1, cc=_update_suffix_preview)
	UI['suffix_digits'] = cmds.intFieldGrp(numberOfFields=1, label='Digit', value1=1, cc=_update_suffix_preview)
	cmds.setParent('..')
	cmds.button(label='Add Digit To Suffix', h=32, bgc=(0.2, 0.8, 0.5), c=add_digit_suffix)
	cmds.setParent('..')
	cmds.setParent('..')

	_update_rename_preview()
	_update_suffix_preview()
	cmds.window(WINDOW_NAME, e=True, w=360)
	cmds.showWindow(WINDOW_NAME)