import math

import maya.cmds as cmds

import circle_polygon_port


WINDOW_NAME = 'StraightLineToolWindow'
UI = {}

STATE_KEYS = {
	'axis_mode': 'straightLine_axisMode',
	'even_mode': 'straightLine_evenMode',
	'base_mode': 'straightLine_baseMode',
	'end_mode': 'straightLine_endMode',
	'view_mode': 'straightLine_viewMode',
	'hv_mode': 'straightLine_hvMode',
	'camera': 'straightLine_camera',
}


def _dot(lhs, rhs):
	return lhs[0] * rhs[0] + lhs[1] * rhs[1] + lhs[2] * rhs[2]


def _sub(lhs, rhs):
	return (lhs[0] - rhs[0], lhs[1] - rhs[1], lhs[2] - rhs[2])


def _add(lhs, rhs):
	return (lhs[0] + rhs[0], lhs[1] + rhs[1], lhs[2] + rhs[2])


def _mul(vec, scalar):
	return (vec[0] * scalar, vec[1] * scalar, vec[2] * scalar)


def _length(vec):
	return math.sqrt(_dot(vec, vec))


def _unit(vec, default=(0.0, 0.0, 0.0)):
	length = _length(vec)
	if length <= 1e-8:
		return default
	return (vec[0] / length, vec[1] / length, vec[2] / length)


def _project_to_plane(point_a, point_b, point_c, point):
	ab = _sub(point_b, point_a)
	ac = _sub(point_c, point_a)
	normal = (
		ab[1] * ac[2] - ab[2] * ac[1],
		ab[2] * ac[0] - ab[0] * ac[2],
		ab[0] * ac[1] - ab[1] * ac[0],
	)
	normal_length_sq = _dot(normal, normal)
	if normal_length_sq <= 1e-8:
		return point
	d = -_dot(point_a, normal)
	x = (point[0] * (normal[1] * normal[1] + normal[2] * normal[2]) - (point[1] * normal[1] + point[2] * normal[2] + d) * normal[0]) / normal_length_sq
	y = (point[1] * (normal[2] * normal[2] + normal[0] * normal[0]) - (point[2] * normal[2] + point[0] * normal[0] + d) * normal[1]) / normal_length_sq
	z = (point[2] * (normal[0] * normal[0] + normal[1] * normal[1]) - (point[0] * normal[0] + point[1] * normal[1] + d) * normal[2]) / normal_length_sq
	return (x, y, z)


def _project_to_line(point_a, point_b, point):
	direction = _sub(point_b, point_a)
	length_sq = _dot(direction, direction)
	if length_sq <= 1e-8:
		return point_a
	t = -_dot(_sub(point_a, point), direction) / length_sq
	return (point_a[0] + direction[0] * t, point_a[1] + direction[1] * t, point_a[2] + direction[2] * t)


def _even_point(point_a, point_b, vertex_count, vertex_index):
	direction = _sub(point_b, point_a)
	if vertex_count <= 1:
		return point_a
	distance = _length(direction) * float(vertex_index) / float(vertex_count - 1)
	length = _length(direction)
	if length <= 1e-8:
		return point_a
	t = distance / length
	return _add(point_a, _mul(direction, t))


def _rotate_position(point, rotate_x, rotate_y, rotate_z):
	current = point
	for axis in range(3):
		if axis == 2:
			value_a, value_b, rotate = current[1], current[2], rotate_x
		if axis == 1:
			value_a, value_b, rotate = current[2], current[0], rotate_y
		if axis == 0:
			value_a, value_b, rotate = current[0], current[1], rotate_z
		radians = math.radians(rotate)
		new_a = value_a * math.cos(radians) - value_b * math.sin(radians)
		new_b = value_a * math.sin(radians) + value_b * math.cos(radians)
		if axis == 2:
			current = (current[0], new_a, new_b)
		if axis == 1:
			current = (new_b, current[1], new_a)
		if axis == 0:
			current = (new_a, new_b, current[2])
	return current


def _get_option(name, default, is_string=False):
	key = STATE_KEYS[name]
	if cmds.optionVar(exists=key):
		return cmds.optionVar(q=key)
	return default


def _set_option(name, value):
	key = STATE_KEYS[name]
	if isinstance(value, str):
		cmds.optionVar(sv=(key, value))
	else:
		cmds.optionVar(iv=(key, int(value)))


def _selected_vertices():
	selection = cmds.ls(sl=True, fl=True, long=True) or []
	vertices = cmds.polyListComponentConversion(selection, tv=True) or []
	return cmds.filterExpand(vertices, selectionMask=31, expand=True) or []


def _selected_transforms():
	return cmds.ls(sl=True, transforms=True, long=True) or []


def _point_position(component):
	if '.' in component:
		return tuple(cmds.pointPosition(component, world=True))
	return tuple(cmds.xform(component, q=True, ws=True, rp=True))


def _save_state(*args):
	_set_option('axis_mode', cmds.radioButtonGrp(UI['axis_mode'], q=True, sl=True) - 1)
	_set_option('even_mode', cmds.checkBox(UI['even_mode'], q=True, v=True))
	_set_option('base_mode', 'field' if cmds.radioButtonGrp(UI['base_mode'], q=True, sl=True) == 1 else 'ends')
	_set_option('end_mode', 'horizontal' if cmds.radioButtonGrp(UI['end_mode'], q=True, sl=True) == 1 else 'vertical')
	view_selection = cmds.radioButtonGrp(UI['view_mode'], q=True, sl=True)
	_set_option('view_mode', ['top', 'front', 'side', 'persp'][view_selection - 1])
	hv_selection = cmds.radioButtonGrp(UI['hv_mode'], q=True, sl=True)
	_set_option('hv_mode', ['shortest', 'horizontal', 'vertical'][hv_selection - 1])
	_set_option('camera', cmds.textField(UI['camera'], q=True, tx=True))


def _load_state():
	cmds.radioButtonGrp(UI['axis_mode'], e=True, sl=_get_option('axis_mode', 0) + 1)
	cmds.checkBox(UI['even_mode'], e=True, v=bool(_get_option('even_mode', 0)))
	cmds.radioButtonGrp(UI['base_mode'], e=True, sl=1 if _get_option('base_mode', 'field', is_string=True) == 'field' else 2)
	cmds.radioButtonGrp(UI['end_mode'], e=True, sl=1 if _get_option('end_mode', 'horizontal', is_string=True) == 'horizontal' else 2)
	view_mode = _get_option('view_mode', 'persp', is_string=True)
	cmds.radioButtonGrp(UI['view_mode'], e=True, sl={'top': 1, 'front': 2, 'side': 3, 'persp': 4}.get(view_mode, 4))
	hv_mode = _get_option('hv_mode', 'shortest', is_string=True)
	cmds.radioButtonGrp(UI['hv_mode'], e=True, sl={'shortest': 1, 'horizontal': 2, 'vertical': 3}.get(hv_mode, 1))
	cmds.textField(UI['camera'], e=True, tx=_get_option('camera', 'persp', is_string=True))


def _ui_change(*args):
	axis_mode = cmds.radioButtonGrp(UI['axis_mode'], q=True, sl=True) - 1
	base_mode = cmds.radioButtonGrp(UI['base_mode'], q=True, sl=True)
	view_mode = cmds.radioButtonGrp(UI['view_mode'], q=True, sl=True)

	view_enabled = axis_mode == 1
	cmds.checkBox(UI['even_mode'], e=True, en=axis_mode == 0)
	cmds.radioButtonGrp(UI['view_mode'], e=True, en=view_enabled)
	cmds.textField(UI['camera'], e=True, en=view_enabled or base_mode == 2)
	cmds.button(UI['get_active_camera'], e=True, en=view_enabled or base_mode == 2)
	cmds.radioButtonGrp(UI['base_mode'], e=True, en=axis_mode != 2)
	if axis_mode == 2 and base_mode != 1:
		cmds.radioButtonGrp(UI['base_mode'], e=True, sl=1)
		base_mode = 1
	cmds.floatFieldGrp(UI['position3'], e=True, en=axis_mode == 2)
	cmds.columnLayout(UI['position_column'], e=True, en=base_mode == 1)
	hv_enabled = base_mode == 2 and axis_mode == 1 and view_mode != 4
	cmds.radioButtonGrp(UI['end_mode'], e=True, en=base_mode == 2 and axis_mode != 2)
	cmds.radioButtonGrp(UI['hv_mode'], e=True, en=hv_enabled)
	cmds.button(UI['get_all_positions'], e=True, en=base_mode == 1, bgc=(0.5, 0.5, 1.0) if base_mode == 1 else (0.5, 0.5, 0.5))

	if hv_enabled:
		if view_mode == 1:
			cmds.radioButtonGrp(UI['hv_mode'], e=True, la3=['Shortest', 'Horizontal(X)', 'Vertical(Z)'])
		if view_mode == 2:
			cmds.radioButtonGrp(UI['hv_mode'], e=True, la3=['Shortest', 'Horizontal(X)', 'Vertical(Y)'])
		if view_mode == 3:
			cmds.radioButtonGrp(UI['hv_mode'], e=True, la3=['Shortest', 'Horizontal(Z)', 'Vertical(Y)'])
	else:
		cmds.radioButtonGrp(UI['hv_mode'], e=True, la3=['Shortest', 'Horizontal', 'Vertical'])

	_save_state()


def _set_position_field(field_name, position):
	cmds.floatFieldGrp(UI[field_name], e=True, value1=position[0], value2=position[1], value3=position[2])


def _capture_positions(mode):
	axis_mode = cmds.radioButtonGrp(UI['axis_mode'], q=True, sl=True) - 1
	transforms = _selected_transforms()
	if transforms:
		items = transforms
	else:
		items = _selected_vertices()
	if not items:
		return

	if mode in (0, 1):
		_set_position_field('position1', _point_position(items[0]))
		cmds.select(items[0], r=True)
	if mode == 0 and len(items) > 1:
		_set_position_field('position2', _point_position(items[-1]))
		cmds.select(items[-1], add=True)
	if mode == 0 and len(items) > 2 and axis_mode == 2:
		_set_position_field('position3', _point_position(items[1]))
		cmds.select(items[1], add=True)
	if mode == 2:
		_set_position_field('position2', _point_position(items[0]))
		cmds.select(items[0], r=True)
	if mode == 3:
		_set_position_field('position3', _point_position(items[0]))
		cmds.select(items[0], r=True)


def _active_camera(*args):
	panel = cmds.getPanel(withFocus=True)
	if not cmds.modelEditor(panel, ex=True):
		return
	camera = cmds.modelEditor(panel, q=True, camera=True)
	cmds.textField(UI['camera'], e=True, tx=camera)
	if camera == 'top':
		cmds.radioButtonGrp(UI['view_mode'], e=True, sl=1)
	elif camera == 'front':
		cmds.radioButtonGrp(UI['view_mode'], e=True, sl=2)
	elif camera == 'side':
		cmds.radioButtonGrp(UI['view_mode'], e=True, sl=3)
	else:
		cmds.radioButtonGrp(UI['view_mode'], e=True, sl=4)
	_ui_change()


def _field_position(field_name):
	return (
		cmds.floatFieldGrp(UI[field_name], q=True, value1=True),
		cmds.floatFieldGrp(UI[field_name], q=True, value2=True),
		cmds.floatFieldGrp(UI[field_name], q=True, value3=True),
	)


def _move_vertices(vertex_list, position1, position2, position3):
	axis_mode = cmds.radioButtonGrp(UI['axis_mode'], q=True, sl=True) - 1
	even_mode = cmds.checkBox(UI['even_mode'], q=True, v=True)
	view_mode = ['top', 'front', 'side', 'persp'][cmds.radioButtonGrp(UI['view_mode'], q=True, sl=True) - 1]
	hv_mode = ['shortest', 'horizontal', 'vertical'][cmds.radioButtonGrp(UI['hv_mode'], q=True, sl=True) - 1]

	if axis_mode in (0, 2) or view_mode == 'persp':
		vertex_count = len(vertex_list) + 2
		for index, vertex in enumerate(vertex_list, start=1):
			current = tuple(cmds.pointPosition(vertex, world=True))
			if axis_mode == 1 and view_mode == 'persp':
				target = _project_to_plane(position1, position2, position3, current)
			elif axis_mode == 2:
				target = _project_to_plane(position1, position2, position3, current)
			elif not even_mode:
				target = _project_to_line(position1, position2, current)
			else:
				target = _even_point(position1, position2, vertex_count, index)
			cmds.move(target[0], target[1], target[2], vertex, absolute=True, worldSpace=True)
		return

	axis_map = {'front': (0, 1), 'top': (0, 2), 'side': (2, 1)}
	xx, yy = axis_map[view_mode]
	delta = position1[xx] - position2[xx]
	slope_valid = abs(delta) > 1e-8
	if slope_valid:
		slope = (position1[yy] - position2[yy]) / delta
		intercept = position2[yy] - slope * position2[xx]
	else:
		slope = 0.0
		intercept = 0.0
		fixed_position = position1[xx]

	for vertex in vertex_list:
		current = list(cmds.pointPosition(vertex, world=True))
		if hv_mode == 'shortest':
			if slope_valid and abs(slope) > 1e-8:
				orthogonal = -1.0 / slope
				orthogonal_intercept = current[yy] - orthogonal * current[xx]
				move_x = (orthogonal_intercept - intercept) / (slope - orthogonal)
				move_y = slope * move_x + intercept
			elif slope_valid:
				move_x = current[xx]
				move_y = intercept
			else:
				move_x = fixed_position
				move_y = current[yy]
		elif hv_mode == 'horizontal':
			move_x = (current[yy] - intercept) / slope if slope_valid and abs(slope) > 1e-8 else (fixed_position if not slope_valid else current[xx])
			move_y = current[yy]
		else:
			move_x = current[xx]
			move_y = current[xx] * slope + intercept if slope_valid else current[yy]

		current[xx] = move_x
		current[yy] = move_y
		cmds.move(current[0], current[1], current[2], vertex, absolute=True, worldSpace=True)


def _end_positions(vertices):
	camera = cmds.textField(UI['camera'], q=True, tx=True)
	if cmds.objectType(camera) != 'transform':
		return None
	rx = -cmds.getAttr(camera + '.rx')
	ry = -cmds.getAttr(camera + '.ry')
	rz = -cmds.getAttr(camera + '.rz')
	rotated = []
	base_positions = []
	for vertex in vertices:
		position = tuple(cmds.pointPosition(vertex, world=True))
		base_positions.append(position)
		rotated.append(_rotate_position(position, rx, ry, rz))
	end_mode = ['horizontal', 'vertical'][cmds.radioButtonGrp(UI['end_mode'], q=True, sl=True) - 1]
	axis_index = 0 if end_mode == 'horizontal' else 1
	min_index = 0
	max_index = 0
	min_value = rotated[0][axis_index]
	max_value = rotated[0][axis_index]
	for index, position in enumerate(rotated[1:], start=1):
		value = position[axis_index]
		if value < min_value:
			min_value = value
			min_index = index
		if value > max_value:
			max_value = value
			max_index = index
	return base_positions[min_index], base_positions[max_index]


def straighten_vertices(*args):
	_save_state()
	axis_mode = cmds.radioButtonGrp(UI['axis_mode'], q=True, sl=True) - 1
	base_mode = ['field', 'ends'][cmds.radioButtonGrp(UI['base_mode'], q=True, sl=True) - 1]
	selection = cmds.ls(sl=True, fl=True, long=True) or []
	vertices = _selected_vertices()
	edges = cmds.filterExpand(selection, selectionMask=32, expand=True) or []
	edge_mode = bool(edges)
	if edge_mode:
		vertices = []

	position1 = _field_position('position1')
	position2 = _field_position('position2')
	position3 = _field_position('position3')

	if base_mode == 'ends' and not edge_mode:
		end_positions = _end_positions(vertices)
		if end_positions is None:
			return
		position1, position2 = end_positions

	view_mode = ['top', 'front', 'side', 'persp'][cmds.radioButtonGrp(UI['view_mode'], q=True, sl=True) - 1]
	if view_mode == 'persp' and axis_mode != 2:
		camera = cmds.textField(UI['camera'], q=True, tx=True)
		if cmds.objectType(camera) != 'transform':
			return
		position3 = (
			cmds.getAttr(camera + '.tx'),
			cmds.getAttr(camera + '.ty'),
			cmds.getAttr(camera + '.tz'),
		)

	if edge_mode:
		ordered = circle_polygon_port.ordered_vertices_from_edges(edges)
		for chain in _edge_vertex_chains(ordered):
			if len(chain) < 2:
				continue
			position1 = tuple(cmds.pointPosition(chain[0], world=True))
			position2 = tuple(cmds.pointPosition(chain[-1], world=True))
			_move_vertices(chain[1:-1], position1, position2, position3)
	else:
		_move_vertices(vertices, position1, position2, position3)


def _edge_vertex_chains(ordered_vertices):
	chains = []
	current = []
	for vertex in ordered_vertices:
		if vertex == '--Loop':
			break
		if vertex == '--':
			if current:
				chains.append(current)
			current = []
			continue
		current.append(vertex)
	if current:
		chains.append(current)
	return chains


def show_window(parent_window):
	if cmds.window(WINDOW_NAME, ex=True):
		cmds.deleteUI(WINDOW_NAME, window=True)
	kwargs = {'title': 'Straight Line Tool', 'rtf': True, 'mnb': False, 'mxb': False, 'tlb': True}
	if parent_window:
		kwargs['p'] = parent_window
	cmds.window(WINDOW_NAME, **kwargs)
	cmds.columnLayout(adj=True)

	cmds.frameLayout(l='Mode', bgc=(0, 0, 0), cll=True, cl=False)
	cmds.columnLayout(adj=True)
	UI['axis_mode'] = cmds.radioButtonGrp(
		nrb=3,
		la3=['Linear 3D', 'Linear 2D (Axis-Limited)', 'Flatten (Based on 3 vertices)'],
		cw4=[1, 140, 180, 190],
		cc=_ui_change,
	)
	cmds.separator(w=200, h=2, st='in')
	UI['even_mode'] = cmds.checkBox(l='Even', cc=_ui_change)
	cmds.setParent('..')
	cmds.setParent('..')

	cmds.frameLayout(l='Base Position', bgc=(0, 0, 0), cll=True, cl=False)
	cmds.columnLayout(adj=True)
	UI['base_mode'] = cmds.radioButtonGrp(nrb=2, la2=['Get Position', 'Both Ends'], cc=_ui_change)
	cmds.frameLayout(l='Position', cll=True, cl=False)
	UI['position_column'] = cmds.columnLayout(adj=True)
	cmds.rowLayout(nc=2)
	cmds.button(w=38, l='Pos1', c=lambda *unused: _capture_positions(1))
	UI['position1'] = cmds.floatFieldGrp(numberOfFields=3, pre=3, value1=0.0, value2=0.0, value3=0.0, cw4=[1, 50, 50, 50])
	cmds.setParent('..')
	cmds.rowLayout(nc=2)
	cmds.button(w=38, l='Pos2', c=lambda *unused: _capture_positions(2))
	UI['position2'] = cmds.floatFieldGrp(numberOfFields=3, pre=3, value1=0.0, value2=1.0, value3=0.0, cw4=[1, 50, 50, 50])
	cmds.setParent('..')
	cmds.rowLayout(nc=2)
	cmds.button(w=38, l='Pos3', c=lambda *unused: _capture_positions(3))
	UI['position3'] = cmds.floatFieldGrp(numberOfFields=3, pre=3, value1=0.0, value2=0.0, value3=1.0, cw4=[1, 50, 50, 50])
	cmds.setParent('..')
	cmds.setParent('..')
	cmds.setParent('..')
	UI['get_all_positions'] = cmds.button(label='Get Position', h=36, bgc=(0.5, 0.5, 1), c=lambda *unused: _capture_positions(0))
	cmds.columnLayout(adj=True)
	UI['end_mode'] = cmds.radioButtonGrp(nrb=2, la2=['End Horizontal', 'End Vertical'], cc=_ui_change)
	cmds.setParent('..')
	cmds.setParent('..')
	cmds.setParent('..')

	cmds.frameLayout(l='Fix Axis', bgc=(0, 0, 0), cll=True, cl=False)
	cmds.columnLayout(adj=True)
	cmds.separator(w=200, h=2)
	UI['view_mode'] = cmds.radioButtonGrp(nrb=4, la4=['top-Y', 'front-Z', 'side-X', 'persp'], cc=_ui_change)
	cmds.rowLayout(nc=3, adj=3)
	UI['camera'] = cmds.textField(w=60, ed=False, tx='persp')
	UI['get_active_camera'] = cmds.button(w=100, l='Get Active Camera', c=_active_camera)
	cmds.setParent('..')
	cmds.separator(w=200, h=2, st='in')
	UI['hv_mode'] = cmds.radioButtonGrp(nrb=3, la3=['Shortest', 'Horizontal', 'Vertical'])
	cmds.separator(w=200, h=2, st='in')
	cmds.setParent('..')
	cmds.setParent('..')

	cmds.button(label='Straight Line', h=36, bgc=(0.2, 0.8, 0.5), c=straighten_vertices)
	cmds.showWindow(WINDOW_NAME)
	_load_state()
	_ui_change()