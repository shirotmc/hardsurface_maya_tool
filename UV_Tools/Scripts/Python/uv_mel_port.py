import math
import re

import maya.cmds as cmds
import maya.mel as mel

SMART_UNFOLD_WINDOW = 'UVScaleUnfoldOptions'
UV_RATIO_WINDOW = 'UVRatioOptions'


def _filter_components(components, token):
	return [component for component in (components or []) if token in component]


def _selection_to_uvs(selection=None):
	selection = selection or (cmds.ls(sl=True, long=True, flatten=True) or [])
	uvs = cmds.ls(cmds.polyListComponentConversion(selection, tuv=True) or [], long=True, flatten=True) or []
	return _filter_components(uvs, '.map[')


def _selection_to_edges(selection=None):
	selection = selection or (cmds.ls(sl=True, long=True, flatten=True) or [])
	edges = cmds.ls(cmds.polyListComponentConversion(selection, te=True) or [], long=True, flatten=True) or []
	return _filter_components(edges, '.e[')


def _selection_to_faces(selection=None):
	selection = selection or (cmds.ls(sl=True, long=True, flatten=True) or [])
	faces = cmds.ls(cmds.polyListComponentConversion(selection, tf=True) or [], long=True, flatten=True) or []
	return _filter_components(faces, '.f[')


def _uv_position(uv):
	position = cmds.polyEditUV(uv, q=True) or [0.0, 0.0]
	return (position[0], position[1])


def _set_uv_position(uv, position):
	cmds.polyEditUV(uv, u=position[0], v=position[1], relative=False)


def _vector_length(vector):
	return math.sqrt(vector[0] * vector[0] + vector[1] * vector[1])


def _normalize(vector, default=(1.0, 0.0)):
	length = _vector_length(vector)
	if length <= 1e-8:
		return default
	return (vector[0] / length, vector[1] / length)


def _shared_face_uvs(uv):
	faces = _selection_to_faces([uv])
	result = set()
	for face in faces:
		result.update(_selection_to_uvs([face]))
	result.discard(uv)
	return list(result)


def _shared_edge_uvs(uv):
	edges = _selection_to_edges([uv])
	result = set()
	for edge in edges:
		result.update(_selection_to_uvs([edge]))
	result.discard(uv)
	return list(result)


def _adjacent_uvs(uv):
	shared_face = set(_shared_face_uvs(uv))
	return [candidate for candidate in _shared_edge_uvs(uv) if candidate in shared_face]


def _uv_shell(uv):
	cmds.select(uv, r=True)
	mel.eval('polySelectBorderShell 0;')
	return _selection_to_uvs()


def _shortest_path(start_uv, end_uv, allowed_uvs=None):
	allowed = set(allowed_uvs or _uv_shell(start_uv))
	allowed.add(start_uv)
	allowed.add(end_uv)
	queue = [(start_uv, [start_uv])]
	seen = {start_uv}
	while queue:
		current, path = queue.pop(0)
		if current == end_uv:
			return path
		for neighbor in _adjacent_uvs(current):
			if neighbor not in allowed or neighbor in seen:
				continue
			seen.add(neighbor)
			queue.append((neighbor, path + [neighbor]))
	return []


def _uv_vertex(uv):
	vertices = cmds.ls(cmds.polyListComponentConversion(uv, tv=True) or [], long=True, flatten=True) or []
	return vertices[0] if vertices else None


def _vertex_distance(uv_a, uv_b):
	vertex_a = _uv_vertex(uv_a)
	vertex_b = _uv_vertex(uv_b)
	if not vertex_a or not vertex_b:
		return 0.0
	pos_a = cmds.pointPosition(vertex_a, world=True)
	pos_b = cmds.pointPosition(vertex_b, world=True)
	return math.sqrt(
		(pos_b[0] - pos_a[0]) ** 2 +
		(pos_b[1] - pos_a[1]) ** 2 +
		(pos_b[2] - pos_a[2]) ** 2
	)


def _snap_axis(direction):
	if abs(direction[0]) >= abs(direction[1]):
		return (1.0 if direction[0] >= 0.0 else -1.0, 0.0)
	return (0.0, 1.0 if direction[1] >= 0.0 else -1.0)


def _redistribute_path(path, straight_mode=True):
	if len(path) < 2:
		return []
	start_position = _uv_position(path[0])
	end_position = _uv_position(path[-1])
	direction = (end_position[0] - start_position[0], end_position[1] - start_position[1])
	if straight_mode:
		direction = _snap_axis(direction)
	else:
		direction = _normalize(direction)

	total_vertex_distance = 0.0
	segment_lengths = []
	for index in range(len(path) - 1):
		segment = max(_vertex_distance(path[index], path[index + 1]), 1e-8)
		segment_lengths.append(segment)
		total_vertex_distance += segment

	total_uv_distance = _vector_length((end_position[0] - start_position[0], end_position[1] - start_position[1]))
	if total_uv_distance <= 1e-8:
		total_uv_distance = total_vertex_distance if total_vertex_distance > 1e-8 else float(len(path) - 1)

	travelled = 0.0
	new_positions = [start_position]
	for segment in segment_lengths:
		travelled += segment
		ratio = travelled / total_vertex_distance if total_vertex_distance > 1e-8 else travelled / max(float(len(segment_lengths)), 1.0)
		new_positions.append((
			start_position[0] + direction[0] * total_uv_distance * ratio,
			start_position[1] + direction[1] * total_uv_distance * ratio,
		))

	for uv, position in zip(path, new_positions):
		_set_uv_position(uv, position)
	return path


def _selected_uv_path():
	selected_uvs = _selection_to_uvs()
	if not selected_uvs:
		return []
	if len(selected_uvs) == 1:
		neighbors = _adjacent_uvs(selected_uvs[0])
		if len(neighbors) < 2:
			return []
		path_a = _shortest_path(neighbors[0], selected_uvs[0])
		path_b = _shortest_path(selected_uvs[0], neighbors[1])
		return path_a + path_b[1:] if path_a and path_b else []
	if len(selected_uvs) == 2:
		return _shortest_path(selected_uvs[0], selected_uvs[1])
	return selected_uvs


def _unfold_selected(apply_to_selected_only):
	selection = _selection_to_uvs()
	if not selection:
		cmds.warning('Please select UVs or polygon components.')
		return []
	mel.eval('polySelectBorderShell 0;')
	cmds.polyEditUV(pu=0.5, pv=0.5, su=20.0, sv=20.0)
	cmds.select(selection, r=True)
	cmds.unfold(i=5000, ss=0.001, gb=0, gmb=0.5, pub=0, ps=1 if apply_to_selected_only else 0, oa=0, us=False)
	mel.eval('polySelectBorderShell 0;')
	cmds.polyEditUV(pu=0.5, pv=0.5, su=1.0 / 20.0, sv=1.0 / 20.0)
	cmds.select(selection, r=True)
	return selection


def select_hard_edge(*args):
	selection = cmds.ls(sl=True, long=True) or []
	edges = _selection_to_edges(selection)
	if not edges:
		cmds.warning('Please select a mesh or mesh components.')
		return []
	cmds.select(edges, r=True)
	cmds.polySelectConstraint(disable=True)
	cmds.polySelectConstraint(m=3, t=0x8000, sm=1)
	result = cmds.ls(sl=True, long=True, flatten=True) or []
	cmds.polySelectConstraint(disable=True)
	if selection:
		cmds.hilite(selection)
	return result


def select_uv_border(*args):
	selection = cmds.ls(sl=True, long=True, flatten=True) or []
	uv_borders = []
	for edge in _selection_to_edges(selection):
		edge_uvs = _selection_to_uvs([edge])
		edge_faces = _selection_to_faces([edge])
		if len(edge_uvs) > 2 or len(edge_faces) < 2:
			uv_borders.append(edge)
	if not uv_borders:
		objects = cmds.ls(selection, objectsOnly=True, long=True) or selection
		for obj in objects:
			for edge in _selection_to_edges([obj]):
				edge_uvs = _selection_to_uvs([edge])
				edge_faces = _selection_to_faces([edge])
				if len(edge_uvs) > 2 or len(edge_faces) < 2:
					uv_borders.append(edge)
	uv_borders = list(dict.fromkeys(uv_borders))
	if uv_borders:
		cmds.select(uv_borders, r=True)
	return uv_borders


def select_border_edge(*args):
	selection = cmds.ls(sl=True, long=True) or []
	edges = _selection_to_edges(selection)
	if not edges:
		cmds.warning('Please select a mesh or mesh components.')
		return []
	cmds.select(edges, r=True)
	cmds.polySelectConstraint(disable=True)
	cmds.polySelectConstraint(m=3, t=0x8000, w=1)
	result = cmds.ls(sl=True, long=True, flatten=True) or []
	cmds.polySelectConstraint(disable=True)
	if selection:
		cmds.hilite(selection)
	return result


def unwrap_hard_edge(*args):
	objects = cmds.filterExpand(ex=True, sm=12) or []
	if not objects:
		return []
	plugins = cmds.pluginInfo(q=True, listPlugins=True) or []
	if 'Unfold3D' not in plugins:
		raise RuntimeError("'Unfold3D' Plugin has to be loaded in order to continue.")

	maya_version = int(float(cmds.about(version=True)))
	for obj in objects:
		faces = _selection_to_faces([obj])
		cmds.polyProjection(faces, ch=True, type='planar', ibd=True, kir=True, md='c')
		cmds.select(obj, r=True)
		cmds.polySelectConstraint(m=0, dis=True)
		cmds.polySelectConstraint(m=3, t=0x8000, sm=1)
		cmds.polySelectConstraint(m=0, dis=True)
		hard_edges = cmds.ls(sl=True, fl=True) or []
		if not hard_edges:
			raise RuntimeError(obj + 'Your mesh as no hard edges, UV generation failed.')
		cmds.polyMapCut(ch=True)

		if maya_version > 2016:
			cmds.u3dUnfold(obj, ite=10, p=1, bi=1, tf=1, ms=1024, rs=0)
		else:
			cmds.u3dUnfold(obj, ite=1, p=0, bi=1, tf=1, ms=1024, rs=0)
			cmds.polyLayoutUV(obj, lm=0, sc=0, se=0, rbf=0, fr=0, ps=0.2, l=2, gu=1, gv=1, ch=True)
		cmds.u3dUnfold(obj, ite=10, p=1, bi=1, tf=1, ms=1024, rs=0)

	cmds.select(objects, r=True)
	return objects


def unwrap_select_edge(*args):
	selected_edges = _selection_to_edges()
	if not selected_edges:
		cmds.warning('Please select polygon edges.')
		return []
	objects = cmds.ls(cmds.listRelatives(selected_edges, parent=True, fullPath=True) or [], long=True) or []
	if not objects:
		objects = list({edge.split('.', 1)[0] for edge in selected_edges})
	object_name = objects[0]
	face_selection = ['{0}.f[*]'.format(object_name)]
	cmds.select(face_selection, r=True)
	cmds.polyProjection(face_selection, ch=True, type='Planar', ibd=True, kir=True, md='b')
	cmds.select(selected_edges, r=True)
	cmds.polyMapCut(ch=True)
	uvs = ['{0}.map[*]'.format(object_name)]
	cmds.select(uvs, r=True)
	try:
		cmds.u3dUnfold(ite=1, p=0, bi=1, tf=1, ms=1024, rs=0)
	except Exception:
		cmds.unfold()
	cmds.polyMultiLayoutUV(l=2, psc=2, rbf=2)
	cmds.polyNormalizeUV()
	cmds.select(selected_edges, r=True)
	return selected_edges


def _ari_axis(vector):
	return _snap_axis(vector)


def _ari_distance_uv(first_uv, second_uv):
	first = _uv_position(first_uv)
	second = _uv_position(second_uv)
	return _vector_length((second[0] - first[0], second[1] - first[1]))


def _ari_vector_move(position, distance, direction):
	return (position[0] + distance * direction[0], position[1] + distance * direction[1])


def _ari_face_uvs(face):
	face_uvs = _selection_to_uvs([face])
	vertices = cmds.ls(cmds.polyListComponentConversion(face, tv=True) or [], long=True, flatten=True) or []
	ordered_uvs = []
	for vertex in vertices:
		vertex_uvs = set(_selection_to_uvs([vertex]))
		matches = [uv for uv in face_uvs if uv in vertex_uvs]
		if not matches:
			return []
		ordered_uvs.append(matches[-1])
	return ordered_uvs if len(ordered_uvs) == 4 else []


def _ari_grid_go(face, selected_uvs, mode):
	quad_uvs = _ari_face_uvs(face)
	if len(quad_uvs) != 4:
		return None
	positions = [_uv_position(uv) for uv in quad_uvs]
	for index in range(4):
		previous = positions[(index - 1) % 4]
		current = positions[index]
		next_position = positions[(index + 1) % 4]
		diagonal_index = (index + 2) % 4
		diagonal = positions[diagonal_index]
		if abs(previous[0] - current[0]) <= 1e-5 and abs(current[1] - next_position[1]) <= 1e-5:
			target = (next_position[0], previous[1])
		elif abs(previous[1] - current[1]) <= 1e-5 and abs(current[0] - next_position[0]) <= 1e-5:
			target = (previous[0], next_position[1])
		else:
			continue
		moved_uv = quad_uvs[diagonal_index]
		if target == diagonal or (mode == 0 and moved_uv not in selected_uvs):
			return None
		_set_uv_position(moved_uv, target)
		return moved_uv
	return None


def _ari_grid_selected(selected_uvs):
	faces = _selection_to_faces(selected_uvs)
	processed = []
	moved_uvs = []
	while True:
		moved = []
		for face in faces:
			if face in processed:
				continue
			moved_uv = _ari_grid_go(face, selected_uvs, 0)
			if moved_uv:
				moved.append(moved_uv)
				moved_uvs.append(moved_uv)
				processed.append(face)
		if not moved:
			break
	return moved_uvs


def _ari_surrounding_uvs(uv):
	return _adjacent_uvs(uv)


def _ari_next_uv(base_uv, previous_uv):
	surrounding = _ari_surrounding_uvs(base_uv)
	if previous_uv not in surrounding or len(surrounding) not in (3, 4):
		return None
	faces = _selection_to_faces([base_uv])
	if len(surrounding) == 4 and len(faces) != 4:
		return None
	remaining = list(surrounding)
	for face in faces:
		face_uvs = _selection_to_uvs([face])
		if previous_uv in face_uvs:
			remaining = [uv for uv in remaining if uv not in face_uvs]
	return remaining[0] if remaining else None


def _ari_loop_uvs(first_uv, second_uv):
	forward = [second_uv, first_uv]
	base_uv, previous_uv = first_uv, second_uv
	returned_to_start = False
	for _ in range(100000):
		next_uv = _ari_next_uv(base_uv, previous_uv)
		if not next_uv:
			break
		if returned_to_start and next_uv == first_uv:
			forward.pop()
			break
		returned_to_start = next_uv == second_uv
		forward.append(next_uv)
		previous_uv, base_uv = base_uv, next_uv
	backward = []
	if not returned_to_start:
		base_uv, previous_uv = second_uv, first_uv
		for _ in range(100000):
			next_uv = _ari_next_uv(base_uv, previous_uv)
			if not next_uv or (backward and next_uv == backward[0]):
				break
			backward.append(next_uv)
			previous_uv, base_uv = base_uv, next_uv
	return list(reversed(backward)) + forward


def _ari_selected_loop(selected_uvs):
	if len(selected_uvs) == 1:
		result = []
		for surrounding_uv in _ari_surrounding_uvs(selected_uvs[0]):
			if surrounding_uv not in result:
				result.extend(_ari_loop_uvs(selected_uvs[0], surrounding_uv))
		return result
	if len(selected_uvs) != 2:
		return []
	first_uv, second_uv = selected_uvs
	if second_uv in _ari_surrounding_uvs(first_uv):
		return _ari_loop_uvs(first_uv, second_uv)
	shortest = []
	for surrounding_uv in _ari_surrounding_uvs(first_uv):
		loop = _ari_loop_uvs(first_uv, surrounding_uv)
		if second_uv not in loop:
			continue
		start = loop.index(first_uv)
		end = loop.index(second_uv, start + 1) if second_uv in loop[start + 1:] else -1
		segment = loop[start:end + 1] if end >= 0 else []
		if segment and (not shortest or len(segment) < len(shortest)):
			shortest = segment
	return shortest


def _ari_ratio_move(first_group, second_group, only_uvs, mode):
	if not first_group:
		return (0.0, 0.0)
	uv_distances = [_ari_distance_uv(first_uv, second_uv) for first_uv, second_uv in zip(first_group, second_group)]
	vertex_distances = [_vertex_distance(first_uv, second_uv) for first_uv, second_uv in zip(first_group, second_group)]
	if mode == 0:
		directions = [
			_normalize((_uv_position(second_uv)[0] - _uv_position(first_uv)[0], _uv_position(second_uv)[1] - _uv_position(first_uv)[1]))
			for first_uv, second_uv in zip(first_group, second_group)
		]
	else:
		direction = _ari_axis((_uv_position(only_uvs[1])[0] - _uv_position(only_uvs[0])[0], _uv_position(only_uvs[1])[1] - _uv_position(only_uvs[0])[1]))
		forced = {2: (1.0, 0.0), 3: (0.0, 1.0), 4: (-1.0, 0.0), 5: (0.0, -1.0)}
		directions = [forced.get(mode, direction)] * len(first_group)
	total_uv = sum(uv_distances)
	total_vertex = sum(vertex_distances)
	if total_vertex <= 1e-8:
		return (total_uv, total_vertex)
	for first_uv, second_uv, vertex_distance, direction in zip(first_group, second_group, vertex_distances, directions):
		move_distance = total_uv * vertex_distance / total_vertex
		_set_uv_position(second_uv, _ari_vector_move(_uv_position(first_uv), move_distance, direction))
	return (total_uv, total_vertex)


def _ari_two_selected_uvs(selected_uvs, mode):
	loop_uvs = _ari_selected_loop(selected_uvs)
	if len(loop_uvs) < 2:
		return ([], (0.0, 0.0))
	first_group, second_group = loop_uvs[:-1], loop_uvs[1:]
	base_position = _uv_position(selected_uvs[0])
	distances = _ari_ratio_move(first_group, second_group, [loop_uvs[0], loop_uvs[-1]], mode)
	after_position = _uv_position(selected_uvs[0])
	for uv in loop_uvs:
		position = _uv_position(uv)
		_set_uv_position(uv, (position[0] + base_position[0] - after_position[0], position[1] + base_position[1] - after_position[1]))
	return (loop_uvs, distances)


def _ari_one_selected_uv(uv):
	faces = _selection_to_faces([uv])
	if not faces:
		return []
	face_uvs = _selection_to_uvs([faces[0]])
	next_uvs = [candidate for candidate in face_uvs if candidate != uv and candidate in _ari_surrounding_uvs(uv)]
	if len(next_uvs) < 2:
		return []
	base_position = _uv_position(uv)
	first_direction = _ari_axis((base_position[0] - _uv_position(next_uvs[0])[0], base_position[1] - _uv_position(next_uvs[0])[1]))
	first_mode = {(1.0, 0.0): 2, (0.0, 1.0): 3, (-1.0, 0.0): 4, (0.0, -1.0): 5}[first_direction]
	first_loop, first_distances = _ari_two_selected_uvs([uv, next_uvs[0]], first_mode)
	if not first_loop:
		return []
	second_direction = _ari_axis((base_position[0] - _uv_position(next_uvs[1])[0], base_position[1] - _uv_position(next_uvs[1])[1]))
	second_mode = {(1.0, 0.0): 2, (0.0, 1.0): 3, (-1.0, 0.0): 4, (0.0, -1.0): 5}[second_direction]
	if first_mode == second_mode or abs(first_mode - second_mode) == 2:
		second_mode = 2 if second_mode == 5 else second_mode + 1
	second_loop, second_distances = _ari_two_selected_uvs([uv, next_uvs[1]], second_mode)
	if not second_loop:
		return []
	first_uv_distance, first_vertex_distance = first_distances
	second_uv_distance, second_vertex_distance = second_distances
	if first_uv_distance > 1e-8 and second_uv_distance > 1e-8 and first_vertex_distance + second_vertex_distance > 1e-8:
		scale_first = (first_vertex_distance + second_vertex_distance) * (first_uv_distance / (first_uv_distance + second_uv_distance)) / first_vertex_distance if first_vertex_distance > 1e-8 else 1.0
		scale_second = (first_vertex_distance + second_vertex_distance) * (second_uv_distance / (first_uv_distance + second_uv_distance)) / second_vertex_distance if second_vertex_distance > 1e-8 else 1.0
		loop_uvs = list(dict.fromkeys(first_loop + second_loop))
		if second_mode in (2, 4):
			cmds.polyEditUV(loop_uvs, pu=base_position[0], pv=base_position[1], su=scale_first, sv=scale_second)
		else:
			cmds.polyEditUV(loop_uvs, pu=base_position[0], pv=base_position[1], su=scale_second, sv=scale_first)
		return loop_uvs
	return list(dict.fromkeys(first_loop + second_loop))


def _ari_grid_one_shell(base_uv):
	if len(_selection_to_faces([base_uv])) > 4:
		return []
	seed_uvs = _ari_one_selected_uv(base_uv)
	if not seed_uvs:
		return []
	processed_faces = set(_selection_to_faces([base_uv]))
	current_faces = list(processed_faces)
	processed_uvs = list(seed_uvs)
	while current_faces:
		for face in current_faces:
			moved_uv = _ari_grid_go(face, [], 1)
			if moved_uv:
				processed_uvs.append(moved_uv)
		next_faces = []
		for face in current_faces:
			for edge in _selection_to_edges([face]):
				edge_uvs = _selection_to_uvs([edge])
				if len(edge_uvs) != 2:
					continue
				for next_face in _selection_to_faces([edge]):
					if next_face not in processed_faces:
						processed_faces.add(next_face)
						next_faces.append(next_face)
		current_faces = next_faces
	shell_uvs = _uv_shell(base_uv)
	return [uv for uv in shell_uvs if uv not in processed_uvs]


def _grid_shell(uv):
	cmds.select(uv, r=True)
	mel.eval('polySelectBorderShell 0;')
	return _selection_to_uvs()


def _grid_face_uvs(face):
	object_name = face.rsplit('.', 1)[0]
	face_uvs = _selection_to_uvs([face])
	face_info = cmds.polyInfo(face, faceToVertex=True) or []
	if not face_info:
		return []
	vertex_indices = re.findall(r'-?\d+', face_info[0].partition(':')[2])
	ordered_uvs = []
	for vertex_index in vertex_indices:
		vertex = '{0}.vtx[{1}]'.format(object_name, vertex_index)
		vertex_uvs = _selection_to_uvs([vertex])
		matches = [uv for uv in vertex_uvs if uv in face_uvs]
		if not matches:
			return []
		ordered_uvs.append(matches[-1])
	return ordered_uvs if len(ordered_uvs) == 4 else []


def _grid_axis(vector):
	if abs(vector[0]) < abs(vector[1]):
		return (0.0, 1.0 if vector[1] > 0.0 else -1.0)
	return (1.0 if vector[0] > 0.0 else -1.0, 0.0)


def _grid_mode_axis(mode, vector):
	if mode == 2:
		return (1.0, 0.0)
	if mode == 3:
		return (0.0, 1.0)
	if mode == 4:
		return (-1.0, 0.0)
	if mode == 5:
		return (0.0, -1.0)
	return _grid_axis(vector)


def _grid_vector_move(position, distance, direction):
	length = _vector_length(direction)
	if length <= 1e-8:
		return position
	return (position[0] + distance * direction[0] / length, position[1] + distance * direction[1] / length)


def _grid_ratio_move(first_group, second_group, only_uvs, mode):
	if not first_group:
		return (0.0, 0.0)
	only_directions = []
	if mode != 0:
		for index in range(0, len(only_uvs) - 1, 2):
			first_position = _uv_position(only_uvs[index])
			second_position = _uv_position(only_uvs[index + 1])
			direction = _grid_axis((second_position[0] - first_position[0], second_position[1] - first_position[1]))
			only_directions.append(_grid_mode_axis(mode, direction))

	uv_distances = []
	vertex_distances = []
	directions = []
	direction_index = 0
	for index, (first_uv, second_uv) in enumerate(zip(first_group, second_group)):
		uv_distances.append(_ari_distance_uv(first_uv, second_uv))
		vertex_distances.append(_vertex_distance(first_uv, second_uv))
		if mode == 0:
			first_position = _uv_position(first_uv)
			second_position = _uv_position(second_uv)
			directions.append((second_position[0] - first_position[0], second_position[1] - first_position[1]))
		else:
			directions.append(only_directions[direction_index // 2])
			if direction_index + 1 < len(only_uvs) and only_uvs[direction_index + 1] == second_uv:
				direction_index += 2

	total_uv_distance = sum(uv_distances)
	total_vertex_distance = sum(vertex_distances)
	if total_vertex_distance <= 1e-8:
		return (total_uv_distance, total_vertex_distance)
	for first_uv, second_uv, vertex_distance, direction in zip(first_group, second_group, vertex_distances, directions):
		move_distance = total_uv_distance * vertex_distance / total_vertex_distance
		_set_uv_position(second_uv, _grid_vector_move(_uv_position(first_uv), move_distance, direction))
	return (total_uv_distance, total_vertex_distance)


def _grid_surrounding_uvs(uv):
	edges = _selection_to_edges([uv])
	edge_uvs = _selection_to_uvs(edges)
	faces = _selection_to_faces([uv])
	face_uvs = _selection_to_uvs(faces)
	return [candidate for candidate in edge_uvs if candidate != uv and candidate in face_uvs]


def _grid_next_uv(base_uv, previous_uv):
	surrounding_uvs = _grid_surrounding_uvs(base_uv)
	if previous_uv not in surrounding_uvs or len(surrounding_uvs) not in (3, 4):
		return None
	faces = _selection_to_faces([base_uv])
	if len(surrounding_uvs) == 4 and len(faces) != 4:
		return None
	remaining_uvs = list(surrounding_uvs)
	for face in faces:
		face_uvs = _selection_to_uvs([face])
		if previous_uv in face_uvs:
			remaining_uvs = [uv for uv in remaining_uvs if uv not in face_uvs]
	return remaining_uvs[0] if remaining_uvs else None


def _grid_loop_uvs(first_uv, second_uv):
	forward = [second_uv, first_uv]
	base_uv = first_uv
	previous_uv = second_uv
	returned_to_second = False
	for _ in range(100000):
		next_uv = _grid_next_uv(base_uv, previous_uv)
		if not next_uv:
			break
		if returned_to_second and next_uv == first_uv:
			forward.pop()
			break
		if next_uv == second_uv:
			returned_to_second = True
		else:
			returned_to_second = False
		forward.append(next_uv)
		previous_uv, base_uv = base_uv, next_uv

	backward = []
	if not returned_to_second:
		base_uv = second_uv
		previous_uv = first_uv
		for _ in range(100000):
			next_uv = _grid_next_uv(base_uv, previous_uv)
			if not next_uv or (backward and next_uv == backward[0]):
				break
			backward.append(next_uv)
			previous_uv, base_uv = base_uv, next_uv
	return list(reversed(backward)) + forward


def _grid_selected_loop(selected_uvs):
	if len(selected_uvs) == 1:
		loop_uvs = []
		for surrounding_uv in _grid_surrounding_uvs(selected_uvs[0]):
			if surrounding_uv not in loop_uvs:
				loop_uvs.extend(_grid_loop_uvs(selected_uvs[0], surrounding_uv))
		return loop_uvs
	if len(selected_uvs) != 2:
		return []
	first_uv, second_uv = selected_uvs
	surrounding_uvs = _grid_surrounding_uvs(first_uv)
	if second_uv in surrounding_uvs:
		return _grid_loop_uvs(first_uv, second_uv)
	shortest_loop = []
	for surrounding_uv in surrounding_uvs:
		work_loop = _grid_loop_uvs(first_uv, surrounding_uv)
		if second_uv not in work_loop:
			continue
		segment = []
		collecting = False
		for loop_uv in work_loop:
			if loop_uv == first_uv or loop_uv == second_uv:
				if collecting:
					segment.append(loop_uv)
					collecting = False
				else:
					collecting = True
			if collecting:
				segment.append(loop_uv)
		if segment and (not shortest_loop or len(segment) < len(shortest_loop)):
			shortest_loop = segment
	return shortest_loop


def _grid_two_selected_uvs(selected_uvs, mode):
	loop_uvs = _grid_selected_loop(selected_uvs)
	if len(loop_uvs) < 2:
		return ([], (0.0, 0.0))
	base_position = _uv_position(selected_uvs[0])
	distances = _grid_ratio_move(loop_uvs[:-1], loop_uvs[1:], [loop_uvs[0], loop_uvs[-1]], mode)
	after_position = _uv_position(selected_uvs[0])
	for loop_uv in loop_uvs:
		position = _uv_position(loop_uv)
		_set_uv_position(loop_uv, (position[0] + base_position[0] - after_position[0], position[1] + base_position[1] - after_position[1]))
	return (loop_uvs, distances)


def _grid_one_selected_uv(base_uv):
	base_position = _uv_position(base_uv)
	faces = _selection_to_faces([base_uv])
	if not faces:
		return []
	face_uvs = _selection_to_uvs([faces[0]])
	edge_uvs = _selection_to_uvs(_selection_to_edges([base_uv]))
	next_uvs = [uv for uv in face_uvs if uv in edge_uvs and uv != base_uv]
	if len(next_uvs) < 2:
		return []

	first_position = _uv_position(next_uvs[0])
	first_axis = _grid_axis((base_position[0] - first_position[0], base_position[1] - first_position[1]))
	axis_modes = {(1.0, 0.0): 2, (0.0, 1.0): 3, (-1.0, 0.0): 4, (0.0, -1.0): 5}
	first_mode = axis_modes[first_axis]
	first_loop, first_distances = _grid_two_selected_uvs([base_uv, next_uvs[0]], first_mode)
	if not first_loop:
		return []

	second_position = _uv_position(next_uvs[1])
	second_axis = _grid_axis((base_position[0] - second_position[0], base_position[1] - second_position[1]))
	second_mode = axis_modes[second_axis]
	if first_mode == second_mode or first_mode == second_mode + 2 or first_mode == second_mode - 2:
		second_mode += 1
		if second_mode == 6:
			second_mode = 2
	second_loop, second_distances = _grid_two_selected_uvs([base_uv, next_uvs[1]], second_mode)
	if not second_loop:
		return []

	first_uv_distance, first_vertex_distance = first_distances
	second_uv_distance, second_vertex_distance = second_distances
	if first_vertex_distance <= 1e-8 or second_vertex_distance <= 1e-8 or first_uv_distance + second_uv_distance <= 1e-8:
		return list(dict.fromkeys(first_loop + second_loop))
	scale_first = (first_vertex_distance + second_vertex_distance) * (first_uv_distance / (first_uv_distance + second_uv_distance)) / first_vertex_distance
	scale_second = (first_vertex_distance + second_vertex_distance) * (second_uv_distance / (first_uv_distance + second_uv_distance)) / second_vertex_distance
	loop_uvs = list(dict.fromkeys(first_loop + second_loop))
	if second_mode in (2, 4):
		cmds.polyEditUV(loop_uvs, pu=base_position[0], pv=base_position[1], su=scale_first, sv=scale_second)
	else:
		cmds.polyEditUV(loop_uvs, pu=base_position[0], pv=base_position[1], su=scale_second, sv=scale_first)
	return loop_uvs


def _grid_go(face, selected_uvs, mode):
	quad_uvs = _grid_face_uvs(face)
	if len(quad_uvs) != 4:
		return None
	positions = [_uv_position(uv) for uv in quad_uvs]
	for index in range(4):
		previous = positions[(index - 1) % 4]
		current = positions[index]
		next_position = positions[(index + 1) % 4]
		diagonal_index = (index + 2) % 4
		diagonal = positions[diagonal_index]
		if abs(previous[0] - current[0]) <= 1e-5 and abs(current[1] - next_position[1]) <= 1e-5:
			target = (next_position[0], previous[1])
		elif abs(previous[1] - current[1]) <= 1e-5 and abs(current[0] - next_position[0]) <= 1e-5:
			target = (previous[0], next_position[1])
		else:
			continue
		moved_uv = quad_uvs[diagonal_index]
		if target == diagonal:
			return None
		if mode == 1 or moved_uv in selected_uvs:
			_set_uv_position(moved_uv, target)
		return moved_uv
	return None


def _grid_selected_faces(selected_uvs):
	faces = _selection_to_faces(selected_uvs)
	processed_faces = []
	processed_uvs = []
	while True:
		moved_in_pass = False
		for face in faces:
			if face in processed_faces:
				continue
			moved_uv = _grid_go(face, selected_uvs, 0)
			if moved_uv:
				processed_uvs.append(moved_uv)
				processed_faces.append(face)
				moved_in_pass = True
		if not moved_in_pass:
			break
	return processed_uvs


def _grid_one_shell(base_uv):
	initial_faces = _selection_to_faces([base_uv])
	if len(initial_faces) > 4:
		return []
	processed_uvs = _grid_one_selected_uv(base_uv)
	if not processed_uvs:
		return []
	processed_faces = set(initial_faces)
	processed_edges = set()
	current_faces = list(initial_faces)
	for _ in range(100000):
		if not current_faces:
			break
		for face in current_faces:
			moved_uv = _grid_go(face, [], 1)
			if moved_uv:
				processed_uvs.append(moved_uv)
		next_edges = [edge for edge in _selection_to_edges(current_faces) if edge not in processed_edges]
		processed_edges.update(next_edges)
		next_faces = []
		for edge in next_edges:
			if len(_selection_to_uvs([edge])) != 2:
				continue
			for face in _selection_to_faces([edge]):
				if face not in processed_faces:
					processed_faces.add(face)
					next_faces.append(face)
		current_faces = next_faces
	shell_uvs = _grid_shell(base_uv)
	return [uv for uv in shell_uvs if uv not in processed_uvs]


def uv_gridding(*args):
	selected_uvs = _selection_to_uvs()
	if not selected_uvs:
		return []
	cmds.polyEditUV(selected_uvs, pu=0, pv=0, a=5.0)
	completed_uvs = _grid_selected_faces(selected_uvs)
	no_move_uvs = [uv for uv in selected_uvs if uv not in completed_uvs]
	if no_move_uvs:
		cmds.polyEditUV(no_move_uvs, pu=0, pv=0, a=-5.0)

	processed_uvs = []
	for index, uv in enumerate(selected_uvs):
		if uv in processed_uvs:
			continue
		shell_uvs = _grid_shell(uv)
		multiple_selection_in_shell = False
		for selected_uv in selected_uvs[index + 1:]:
			if selected_uv in shell_uvs:
				multiple_selection_in_shell = True
				processed_uvs.append(selected_uv)
		if not multiple_selection_in_shell:
			no_move_uvs = [candidate for candidate in no_move_uvs if candidate != uv]
			no_move_uvs.extend(_grid_one_shell(uv))
	cmds.select(no_move_uvs, r=True)
	return no_move_uvs


def _smart_unfold_option(name, default):
	if cmds.optionVar(exists=name):
		return cmds.optionVar(q=name)
	return default


def _save_smart_unfold_options(*args):
	cmds.optionVar(floatValue=('UVScaleUnfold_Scale', cmds.floatField('uv_scale_unfold_scale_ff', q=True, v=True)))
	cmds.optionVar(intValue=('UVScaleUnfold_VerHor', cmds.radioButtonGrp('uv_scale_unfold_axis_rbg', q=True, sl=True) - 1))
	cmds.optionVar(intValue=('UVScaleUnfold_Select', cmds.radioButtonGrp('uv_scale_unfold_selection_rbg', q=True, sl=True) - 1))
	cmds.optionVar(intValue=('UVScaleUnfold_Reverse', cmds.radioButtonGrp('uv_scale_unfold_reverse_rbg', q=True, sl=True) - 1))
	cmds.optionVar(intValue=('UVScaleUnfold_Check', cmds.intField('uv_scale_unfold_check_if', q=True, v=True)))


def _update_smart_unfold_options_ui(*args):
	reverse_mode = cmds.radioButtonGrp('uv_scale_unfold_reverse_rbg', q=True, sl=True) - 1
	cmds.intField('uv_scale_unfold_check_if', e=True, en=(reverse_mode == 2))


def show_smart_unfold_options(*args):
	if cmds.window(SMART_UNFOLD_WINDOW, ex=True):
		cmds.deleteUI(SMART_UNFOLD_WINDOW, window=True)
	cmds.window(SMART_UNFOLD_WINDOW, title='UVScaleUnfoldOptions', tlb=True, w=300, h=50)
	form = cmds.formLayout()
	column = cmds.columnLayout(adj=True)
	cmds.rowLayout(nc=3, adj=2)
	cmds.text(l='Scale')
	cmds.floatField('uv_scale_unfold_scale_ff', v=_smart_unfold_option('UVScaleUnfold_Scale', 100.0), min=1.0, pre=2)
	cmds.setParent('..')
	cmds.separator(h=4, st='in')
	cmds.radioButtonGrp('uv_scale_unfold_axis_rbg', nrb=3, la3=['None', 'Vertical', 'Horizontal'], sl=int(_smart_unfold_option('UVScaleUnfold_VerHor', 0)) + 1)
	cmds.separator(h=4, st='in')
	cmds.radioButtonGrp('uv_scale_unfold_selection_rbg', nrb=2, la2=['Selected', 'Unselected'], sl=int(_smart_unfold_option('UVScaleUnfold_Select', 0)) + 1)
	cmds.separator(h=4, st='in')
	cmds.radioButtonGrp('uv_scale_unfold_reverse_rbg', nrb=3, la3=['Front', 'Reverse', 'Auto'], sl=int(_smart_unfold_option('UVScaleUnfold_Reverse', 2)) + 1, cc=_update_smart_unfold_options_ui)
	cmds.intField('uv_scale_unfold_check_if', w=40, v=int(_smart_unfold_option('UVScaleUnfold_Check', 10)), ann='Number of faces to check front and back')
	cmds.separator(h=4, st='in')
	cmds.setParent('..')
	button_form = cmds.formLayout()
	button_save = cmds.button(l='Save', c=_save_smart_unfold_options)
	button_save_close = cmds.button(l='Save Close', c=lambda *_: (_save_smart_unfold_options(), cmds.deleteUI(SMART_UNFOLD_WINDOW, window=True)))
	button_apply = cmds.button(l='Apply', h=38, bgc=(0.5, 0.5, 1.0), c=lambda *_: (_save_smart_unfold_options(), smart_unfold()))
	cmds.formLayout(button_form, e=True,
		af=[(button_apply, 'bottom', 0), (button_apply, 'right', 0), (button_apply, 'top', 0), (button_save, 'top', 0), (button_save, 'left', 0), (button_save_close, 'bottom', 0), (button_save_close, 'left', 0)],
		ap=[(button_apply, 'left', 0, 50), (button_save, 'bottom', 0, 50)],
		ac=[(button_save, 'right', 0, button_apply), (button_save_close, 'top', 0, button_save), (button_save_close, 'right', 0, button_apply)])
	cmds.setParent('..')
	cmds.formLayout(form, e=True,
		af=[(column, 'top', 0), (column, 'left', 0), (column, 'right', 0), (button_form, 'bottom', 0), (button_form, 'left', 0), (button_form, 'right', 0)],
		ac=[(button_form, 'top', 0, column)])
	_update_smart_unfold_options_ui()
	cmds.showWindow(SMART_UNFOLD_WINDOW)


def smart_unfold(*args):
	selected_uvs = _selection_to_uvs()
	if not selected_uvs:
		show_smart_unfold_options()
		return []
	scale_value = float(_smart_unfold_option('UVScaleUnfold_Scale', 100.0))
	axis_mode = int(_smart_unfold_option('UVScaleUnfold_VerHor', 0))
	selection_mode = int(_smart_unfold_option('UVScaleUnfold_Select', 0))
	reverse_mode = int(_smart_unfold_option('UVScaleUnfold_Reverse', 2))
	reverse_scale = -1.0 if reverse_mode == 1 else 1.0
	mel.eval('polySelectBorderShell 0;')
	cmds.polyEditUV(pu=0.5, pv=0.5, su=scale_value, sv=scale_value * reverse_scale)
	cmds.select(selected_uvs, r=True)
	cmds.unfold(i=5000, ss=0.001, gb=0, gmb=0.5, pub=0, ps=selection_mode, oa=axis_mode, us=False)
	mel.eval('polySelectBorderShell 0;')
	cmds.polyEditUV(pu=0.5, pv=0.5, su=1.0 / scale_value, sv=(1.0 / scale_value) * reverse_scale)
	cmds.select(selected_uvs, r=True)
	return selected_uvs


def _uv_ratio_option(name, default):
	if cmds.optionVar(exists=name):
		return cmds.optionVar(q=name)
	return default


def _save_uv_ratio_options(*args):
	cmds.optionVar(intValue=('UVRatio_straight', cmds.checkBox('uv_ratio_straight_cb', q=True, v=True)))
	cmds.optionVar(intValue=('UVRatio_unfold', cmds.checkBox('uv_ratio_unfold_cb', q=True, v=True)))


def show_uv_ratio_options(*args):
	if cmds.window(UV_RATIO_WINDOW, ex=True):
		cmds.deleteUI(UV_RATIO_WINDOW, window=True)
	cmds.window(UV_RATIO_WINDOW, title='UVRatioOptions', tlb=True, w=300, h=50)
	form = cmds.formLayout()
	column = cmds.columnLayout(adj=True)
	cmds.checkBox('uv_ratio_straight_cb', l='Straight (recommend)', v=bool(_uv_ratio_option('UVRatio_straight', 1)))
	cmds.checkBox('uv_ratio_unfold_cb', l='Unfold UV', v=bool(_uv_ratio_option('UVRatio_unfold', 0)))
	cmds.separator(h=4, st='in')
	cmds.rowColumnLayout(nc=2, cw=[(1, 150), (2, 150)])
	cmds.button(l='Contiguous', c=lambda *_: cmds.SelectContiguousEdges())
	cmds.columnLayout(adj=True)
	cmds.button(l='UnfoldUV (UnSel)', c=lambda *_: _unfold_selected(True))
	cmds.button(l='UnfoldUV (Sel)', c=lambda *_: _unfold_selected(False))
	cmds.setParent('..')
	cmds.setParent('..')
	cmds.separator(h=8, st='in')
	cmds.setParent('..')
	button_form = cmds.formLayout()
	button_save = cmds.button(l='Save', c=_save_uv_ratio_options)
	button_save_close = cmds.button(l='Save Close', c=lambda *_: (_save_uv_ratio_options(), cmds.deleteUI(UV_RATIO_WINDOW, window=True)))
	button_apply = cmds.button(l='Apply', h=38, bgc=(0.0, 0.5, 0.5), c=lambda *_: (_save_uv_ratio_options(), uv_ratio()))
	cmds.formLayout(button_form, e=True,
		af=[(button_apply, 'bottom', 0), (button_apply, 'right', 0), (button_apply, 'top', 0), (button_save, 'top', 0), (button_save, 'left', 0), (button_save_close, 'bottom', 0), (button_save_close, 'left', 0)],
		ap=[(button_apply, 'left', 0, 50), (button_save, 'bottom', 0, 50)],
		ac=[(button_save, 'right', 0, button_apply), (button_save_close, 'top', 0, button_save), (button_save_close, 'right', 0, button_apply)])
	cmds.setParent('..')
	cmds.formLayout(form, e=True,
		af=[(column, 'top', 0), (column, 'left', 0), (column, 'right', 0), (button_form, 'bottom', 0), (button_form, 'left', 0), (button_form, 'right', 0)],
		ac=[(button_form, 'top', 0, column)])
	cmds.showWindow(UV_RATIO_WINDOW)


def uv_ratio(*args):
	straight_mode = bool(_uv_ratio_option('UVRatio_straight', 1))
	unfold_mode = bool(_uv_ratio_option('UVRatio_unfold', 0))
	path = _selected_uv_path()
	if not path:
		show_uv_ratio_options()
		return []
	result = _redistribute_path(path, straight_mode=straight_mode)
	if result and unfold_mode:
		cmds.select(result, r=True)
		_unfold_selected(False)
	if result:
		cmds.select(result, r=True)
	return result