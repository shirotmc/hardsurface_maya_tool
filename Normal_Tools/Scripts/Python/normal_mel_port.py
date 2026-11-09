import math

import maya.cmds as cmds


_COPIED_VERTEX_NORMAL = []


def _unique(items):
	result = []
	seen = set()
	for item in items or []:
		if item not in seen:
			seen.add(item)
			result.append(item)
	return result


def _component_object(component):
	return component.split('.', 1)[0]


def _component_index(component):
	return component[component.index('[') + 1:component.index(']')]


def _vector_length(vector):
	return math.sqrt(sum([value * value for value in vector]))


def _normalize(vector, fallback=None):
	fallback = fallback or [0.0, 0.0, 1.0]
	length = _vector_length(vector)
	if length <= 0.000001:
		return list(fallback)
	return [value / length for value in vector]


def _average_vectors(vectors):
	if not vectors:
		return [0.0, 0.0, 1.0]

	average = [
		sum(axis_values) / float(len(vectors))
		for axis_values in zip(*vectors)
	]
	return _normalize(average)


def _flatten_conversion(items, **kwargs):
	converted = cmds.polyListComponentConversion(items, **kwargs)
	return cmds.ls(converted, flatten=True, long=True) or []


def _to_faces(items):
	return _unique(_flatten_conversion(items, toFace=True))


def _to_vertices(items):
	return _unique(_flatten_conversion(items, toVertex=True))


def _to_edges(items):
	return _unique(_flatten_conversion(items, toEdge=True))


def _intersect(left, right):
	left_set = set(left)
	return [item for item in right if item in left_set]


def _face_normal(face):
	info = cmds.polyInfo(face, fn=True) or []
	if not info:
		return [0.0, 0.0, 1.0]

	tokens = info[0].split()
	if len(tokens) < 5 or tokens[0] != 'FACE_NORMAL':
		return [0.0, 0.0, 1.0]

	return _normalize([float(tokens[-3]), float(tokens[-2]), float(tokens[-1])])


def _tri_area(v1, v2, v3):
	d1 = [v1[index] - v2[index] for index in range(3)]
	d2 = [v2[index] - v3[index] for index in range(3)]
	d3 = [v3[index] - v1[index] for index in range(3)]
	e1 = _vector_length(d1)
	e2 = _vector_length(d2)
	e3 = _vector_length(d3)
	s = (e1 + e2 + e3) / 2.0
	area_sq = (s - e1) * (s - e2) * (s - e3) * s
	if area_sq <= 0.0:
		return 0.0
	return math.sqrt(area_sq)


def _poly_3d_area(face):
	object_name = _component_object(face)
	face_to_vertex = cmds.polyInfo(face, faceToVertex=True) or []
	if not face_to_vertex:
		return 0.0

	tokens = face_to_vertex[0].replace(':', ' ').split()
	vertices = []
	for token in tokens[2:]:
		if token.isdigit():
			vertices.append(object_name + '.vtx[' + token + ']')

	if len(vertices) < 3:
		return 0.0

	area = 0.0
	base_position = cmds.pointPosition(vertices[-1], world=True)
	for index in range(len(vertices) - 2):
		area += _tri_area(
			base_position,
			cmds.pointPosition(vertices[index], world=True),
			cmds.pointPosition(vertices[index + 1], world=True)
		)
	return area


def _face_area(face):
	try:
		area = cmds.polyEvaluate(face, faceArea=True)
		if isinstance(area, (list, tuple)):
			return area[0] if area else 0.0
		return area or 0.0
	except Exception:
		return _poly_3d_area(face)


def _lock_to(vertex_faces, faces):
	if not faces:
		return

	normal = [0.0, 0.0, 0.0]
	for face in faces:
		face_normal = _face_normal(face)
		normal = [normal[index] + face_normal[index] for index in range(3)]

	normal = _normalize(normal)
	for vertex_face in vertex_faces:
		cmds.polyNormalPerVertex(vertex_face, xyz=normal)


def _vertex_faces_for(verts, faces):
	if not verts or not faces:
		return []

	base = _component_object(verts[0])
	vertex_faces = []
	for face in faces:
		face_index = _component_index(face)
		for vert in verts:
			vertex_faces.append(base + '.vtxFace[' + _component_index(vert) + '][' + face_index + ']')
	return vertex_faces


def _is_edge_hard(edge):
	if not edge:
		return False
	edge_info = cmds.polyInfo(edge, ev=True) or []
	if not edge_info:
		return False
	return edge_info[0].strip().endswith('Hard')


def copy_vertex_normals(axis='x'):
	del axis
	global _COPIED_VERTEX_NORMAL
	_COPIED_VERTEX_NORMAL = cmds.polyNormalPerVertex(query=True, xyz=True) or []


def paste_vertex_normals(axis='x'):
	if len(_COPIED_VERTEX_NORMAL) < 3:
		cmds.warning('No copied vertex normal found.')
		return

	paste_to = cmds.ls(selection=True, flatten=True, long=True) or []
	if not paste_to:
		return

	normal = list(_COPIED_VERTEX_NORMAL[:3])
	mirror_paste = []

	if axis == '-x':
		normal[0] *= -1.0

	if axis == '-X':
		for component in paste_to:
			position = cmds.xform(component, query=True, worldSpace=True, translation=True)
			parent_object = _component_object(component)
			all_vertices = cmds.ls(parent_object + '.vtx[*]', flatten=True, long=True) or []
			for vertex in all_vertices:
				other_position = cmds.xform(vertex, query=True, worldSpace=True, translation=True)
				distance = math.sqrt(
					((-1.0 * position[0]) - other_position[0]) ** 2 +
					(position[1] - other_position[1]) ** 2 +
					(position[2] - other_position[2]) ** 2
				)
				if distance < 0.01:
					mirror_paste.append(vertex)

	for component in paste_to:
		cmds.polyNormalPerVertex(component, xyz=normal)

	if axis == '-X':
		mirrored_normal = [-1.0 * _COPIED_VERTEX_NORMAL[0], _COPIED_VERTEX_NORMAL[1], _COPIED_VERTEX_NORMAL[2]]
		mirror_paste = _unique(mirror_paste)
		for component in mirror_paste:
			cmds.polyNormalPerVertex(component, xyz=mirrored_normal)
		selection = paste_to
		if mirror_paste:
			selection = _unique([_component_object(mirror_paste[0])] + paste_to + mirror_paste)
		cmds.select(selection, r=True)
		return

	cmds.select(paste_to, r=True)


def copy_average_vertex_normal():
	global _COPIED_VERTEX_NORMAL
	all_normals = cmds.polyNormalPerVertex(query=True, xyz=True) or []
	if not all_normals:
		_COPIED_VERTEX_NORMAL = [0.0, 0.0, 1.0]
		return

	normal_vectors = []
	for index in range(0, len(all_normals), 3):
		normal_vectors.append(all_normals[index:index + 3])

	_COPIED_VERTEX_NORMAL = _average_vectors(normal_vectors)


def copy_paste_average_vertex_normal():
	copy_average_vertex_normal()
	paste_vertex_normals('x')


def paste_vertex_normals_three_vertices():
	vertices = _to_vertices(cmds.ls(selection=True, flatten=True, long=True) or [])
	if len(vertices) != 3:
		cmds.confirmDialog(title='Invalid Selection', message='Please select 3 adjacent vertices!')
		return

	edges = []
	selected_set = set(vertices)
	for edge in _to_edges(vertices):
		edge_vertices = _to_vertices([edge])
		if len(edge_vertices) == 2 and set(edge_vertices).issubset(selected_set):
			edges.insert(0, edge)

	if len(edges) != 2:
		cmds.confirmDialog(title='Invalid Selection', message='Please select 3 adjacent vertices!')
		return

	verts0 = _to_vertices([edges[0]])
	verts1 = _to_vertices([edges[1]])
	mid_vert = ''
	for vertex in verts0:
		if vertex in verts1:
			mid_vert = vertex
			break

	if not mid_vert:
		cmds.confirmDialog(title='Invalid Selection', message='Please select 3 adjacent vertices!')
		return

	outer_verts = [vertex for vertex in verts0 if vertex != mid_vert]
	outer_verts.extend([vertex for vertex in verts1 if vertex != mid_vert])
	outer_verts = _unique(outer_verts)

	cmds.select(outer_verts, r=True)
	copy_average_vertex_normal()
	cmds.select(mid_vert, r=True)
	paste_vertex_normals('x')
	cmds.select(vertices, r=True)


def lock_edge_normals_by_related_face_areas(side):
	sel_edges = cmds.ls(selection=True, flatten=True, long=True) or []
	sel_edges = [edge for edge in sel_edges if '.e[' in edge]
	if not sel_edges:
		cmds.error('Please select one edge loop.')

	for edge in sel_edges:
		edge_faces = _to_faces([edge])
		if len(edge_faces) == 1:
			cmds.error('There are some open edges in the selection!')
		if len(edge_faces) > 2:
			cmds.error('There are some non-manifold edges in the selection!')

	sel_edge_verts = _to_vertices(sel_edges)
	sel_edge_faces = _to_faces(sel_edge_verts)

	end_verts = []
	for vert in sel_edge_verts:
		adjacent_edges = _to_edges([vert])
		selected_adjacent_edges = _intersect(sel_edges, adjacent_edges)
		if len(selected_adjacent_edges) >= 3:
			cmds.error('There are errors with the selection: more than 2 edges per vert detected!')
		if len(selected_adjacent_edges) == 1:
			end_verts.append(vert)

	if len(end_verts) > 2:
		cmds.error('There are errors with the selection: more than 2 end verts detected!')

	if len(end_verts) == 0:
		current_selection = list(sel_edges)
		cmds.select(sel_edges[0], r=True)
		cmds.polySelectSp(loop=True)
		loop_edges = cmds.ls(selection=True, flatten=True, long=True) or []
		cmds.select(current_selection, r=True)
		other_loop_edges = [edge for edge in sel_edges if edge not in loop_edges]
		if other_loop_edges:
			cmds.error('This tool DOES NOT work with multiple edge loops!')

	if len(end_verts) == 2:
		first_vert = end_verts[0]
		first_edge = _intersect(_to_edges([first_vert]), sel_edges)[0]
		inner_verts = [vert for vert in sel_edge_verts if vert not in end_verts]
		faces_need_processing = _to_faces(sel_edges) if not inner_verts else _to_faces(inner_verts)
	else:
		first_edge = sel_edges[0]
		faces_need_processing = list(sel_edge_faces)

	first_edge_faces = _to_faces([first_edge])
	sel_edge_faces_left = [first_edge_faces[0]]
	sel_edge_faces_right = [first_edge_faces[1]]
	faces_need_processing = [face for face in faces_need_processing if face not in first_edge_faces]

	exit_loop = 0
	while faces_need_processing:
		progressed = False
		for cur_face in list(faces_need_processing):
			cur_face_edges = [edge for edge in _to_edges([cur_face]) if edge not in sel_edges]

			left_face_edges = _to_edges([sel_edge_faces_left[-1]])
			if _intersect(left_face_edges, cur_face_edges):
				sel_edge_faces_left.append(cur_face)
				faces_need_processing.remove(cur_face)
				progressed = True
				break

			right_face_edges = _to_edges([sel_edge_faces_right[-1]])
			if _intersect(right_face_edges, cur_face_edges):
				sel_edge_faces_right.append(cur_face)
				faces_need_processing.remove(cur_face)
				progressed = True
				break

		exit_loop += 1
		if exit_loop > 100000 or not progressed:
			break

	area_left = sum([_face_area(face) for face in sel_edge_faces_left])
	area_right = sum([_face_area(face) for face in sel_edge_faces_right])

	if area_left == area_right:
		faces_lock_to = list(sel_edge_faces_left)
	elif side == 1:
		faces_lock_to = sel_edge_faces_left if area_left > area_right else sel_edge_faces_right
	else:
		faces_lock_to = sel_edge_faces_right if area_left > area_right else sel_edge_faces_left

	for vert in sel_edge_verts:
		lock_toward_faces = _intersect(_to_faces([vert]), faces_lock_to)
		avg_normal = [0.0, 0.0, 0.0]
		for face in lock_toward_faces:
			face_normal = _face_normal(face)
			avg_normal = [avg_normal[index] + face_normal[index] for index in range(3)]
		cmds.polyNormalPerVertex(vert, xyz=_normalize(avg_normal))

	cmds.select(sel_edges, r=True)
	cmds.polySoftEdge(a=180, ch=0)


def smooth_bevel(sharp_ends=0):
	del sharp_ends
	face_selection = cmds.ls(selection=True, flatten=True, long=True) or []
	face_selection = [face for face in face_selection if '.f[' in face]
	vert_selection = _to_vertices(face_selection)
	edge_selection = _to_edges(face_selection)
	face_selection_set = set(face_selection)
	vert_selection_set = set(vert_selection)
	edge_selection_set = set(edge_selection)

	for vert in vert_selection:
		faces_on_vert = _to_faces([vert])
		edges_on_vert = _to_edges([vert])
		unselected_faces_on_vert = [face for face in faces_on_vert if face not in face_selection_set]
		selected_faces_on_vert = [face for face in faces_on_vert if face in face_selection_set]

		if not unselected_faces_on_vert:
			cmds.warning(vert + ' has no unselected faces attached to it. Could not smooth bevel here!')
			continue

		selected_edges_on_vert = [edge for edge in edges_on_vert if edge in edge_selection_set]

		if len(selected_faces_on_vert) == 1:
			faces_to_lock_to = []
			for face in faces_on_vert:
				verts_on_face = _to_vertices([face])
				selected_verts_on_face = [face_vert for face_vert in verts_on_face if face_vert in vert_selection_set]
				if len(selected_verts_on_face) >= 2:
					use_face = False
					for face_vert in selected_verts_on_face:
						faces_on_selected_vert = _to_faces([face_vert])
						selected_faces_on_selected_vert = [selected_face for selected_face in faces_on_selected_vert if selected_face in face_selection_set]
						if len(selected_faces_on_selected_vert) >= 2:
							use_face = True
							break
					if use_face:
						faces_to_lock_to.append(face)

			faces_to_lock_to = [face for face in faces_to_lock_to if face not in selected_faces_on_vert]
			faces_to_lock = list(selected_faces_on_vert) + faces_to_lock_to
			vfs_to_lock = _vertex_faces_for([vert], faces_to_lock)
			_lock_to(vfs_to_lock, faces_to_lock_to)
			continue

		internal_edge = ''
		for edge in selected_edges_on_vert:
			edge_faces = _to_faces([edge])
			selected_edge_faces = [face for face in edge_faces if face in selected_faces_on_vert]
			if len(selected_edge_faces) == 2:
				internal_edge = edge

		if internal_edge and _is_edge_hard(internal_edge):
			face_group1 = [selected_faces_on_vert[0]]
			edges_to_fan = [edge for edge in edges_on_vert if edge != internal_edge]

			edges_on_last_face = _to_edges([face_group1[-1]])
			next_edge = _intersect(edges_to_fan, edges_on_last_face)
			next_polys = [face for face in _to_faces(next_edge) if face not in face_group1]
			if next_polys:
				face_group1.append(next_polys[0])
			edges_to_fan = [edge for edge in edges_on_vert if edge not in next_edge]

			for _ in range(1, 20):
				edges_on_last_face = _to_edges([face_group1[-1]])
				next_edge = _intersect(edges_to_fan, edges_on_last_face)
				if not next_edge or _is_edge_hard(next_edge[0]):
					break

				next_polys = [face for face in _to_faces(next_edge) if face not in face_group1]
				if not next_polys:
					break

				face_group1.append(next_polys[0])
				edges_to_fan = [edge for edge in edges_on_vert if edge not in next_edge]
				if not edges_to_fan:
					break

			face_group2 = [face for face in faces_on_vert if face not in face_group1]

			vfs_to_lock = _vertex_faces_for([vert], face_group1)
			faces_to_lock_to = [face for face in selected_faces_on_vert if face not in face_group1]
			_lock_to(vfs_to_lock, faces_to_lock_to)

			vfs_to_lock = _vertex_faces_for([vert], face_group2)
			faces_to_lock_to2 = [face for face in selected_faces_on_vert if face not in face_group2]
			if not faces_to_lock_to2:
				faces_to_lock_to2 = faces_to_lock_to
			_lock_to(vfs_to_lock, faces_to_lock_to2)
			continue

		_lock_to([vert], unselected_faces_on_vert)


def smooth_faces():
	faces = cmds.ls(selection=True, flatten=True, long=True) or []
	faces = [face for face in faces if '.f[' in face]
	face_set = set(faces)
	verts = _to_vertices(faces)
	border_verts = _unique(_flatten_conversion(faces, border=True, toVertex=True))
	border_vert_set = set(border_verts)
	non_border_verts = [vert for vert in verts if vert not in border_vert_set]

	for vert in border_verts:
		faces_on_vert = _to_faces([vert])
		selected_faces_on_vert = [face for face in faces_on_vert if face in face_set]
		_lock_to([vert], selected_faces_on_vert)

	for vert in non_border_verts:
		cmds.polyNormalPerVertex(vert, unFreezeNormal=True)


def transfer_normal():
	sel = cmds.ls(selection=True, long=True, flatten=True) or []
	if len(sel) < 2:
		cmds.warning('Select destination vertices or mesh, then a source mesh.')
		return

	if len(sel) > 2:
		vert_sel = list(sel[:-1])
		source_sel = _to_vertices([sel[-1]])
	else:
		vert_sel = _to_vertices([sel[0]])
		source_sel = _to_vertices([sel[1]])

	if not vert_sel or not source_sel:
		cmds.warning('Could not resolve source or destination vertices.')
		return

	for vert in vert_sel:
		shortest_distance = None
		closest_vert = None
		v_pos = cmds.xform(vert, query=True, worldSpace=True, translation=True)

		for source_vert in source_sel:
			test_vert = cmds.xform(source_vert, query=True, worldSpace=True, translation=True)
			test_length = sum([
				(test_vert[index] - v_pos[index]) * (test_vert[index] - v_pos[index])
				for index in range(3)
			])
			if shortest_distance is None or test_length < shortest_distance:
				shortest_distance = test_length
				closest_vert = source_vert

		if not closest_vert:
			continue

		world_normal = cmds.polyNormalPerVertex(closest_vert, query=True, xyz=True) or []
		for index in range(0, len(world_normal), 3):
			cmds.polyNormalPerVertex(vert, xyz=world_normal[index:index + 3])

	cmds.select(clear=True)
	cmds.select(sel, r=True)


def clone_selected_faces():
	faces = cmds.ls(selection=True, flatten=True, long=True) or []
	faces = [face for face in faces if '.f[' in face]
	if not faces:
		return None

	object_original = _component_object(faces[0])
	object_duplicate = cmds.duplicate(object_original, rr=True)[0]
	duplicated_faces = [face.replace(object_original, object_duplicate, 1) for face in faces]
	duplicate_all_faces = cmds.ls(object_duplicate + '.f[*]', flatten=True, long=True) or []
	duplicate_keep_set = set(duplicated_faces)
	faces_to_delete = [face for face in duplicate_all_faces if face not in duplicate_keep_set]
	if faces_to_delete:
		cmds.delete(faces_to_delete)

	cmds.select(clear=True)
	cmds.select(object_duplicate, r=True)
	return object_duplicate