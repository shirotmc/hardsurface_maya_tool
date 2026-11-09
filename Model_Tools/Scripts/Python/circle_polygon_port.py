import math
import re

import maya.cmds as cmds


def _add(lhs, rhs):
	return (lhs[0] + rhs[0], lhs[1] + rhs[1], lhs[2] + rhs[2])


def _sub(lhs, rhs):
	return (lhs[0] - rhs[0], lhs[1] - rhs[1], lhs[2] - rhs[2])


def _mul(vec, scalar):
	return (vec[0] * scalar, vec[1] * scalar, vec[2] * scalar)


def _dot(lhs, rhs):
	return lhs[0] * rhs[0] + lhs[1] * rhs[1] + lhs[2] * rhs[2]


def _cross(lhs, rhs):
	return (
		lhs[1] * rhs[2] - lhs[2] * rhs[1],
		lhs[2] * rhs[0] - lhs[0] * rhs[2],
		lhs[0] * rhs[1] - lhs[1] * rhs[0],
	)


def _length(vec):
	return math.sqrt(_dot(vec, vec))


def _unit(vec, default=(0.0, 0.0, 0.0)):
	length = _length(vec)
	if length <= 1e-8:
		return default
	return (vec[0] / length, vec[1] / length, vec[2] / length)


def _angle(lhs, rhs):
	left = _length(lhs)
	right = _length(rhs)
	if left <= 1e-8 or right <= 1e-8:
		return 0.0
	value = _dot(lhs, rhs) / (left * right)
	value = max(-1.0, min(1.0, value))
	return math.acos(value)


def _distance(lhs, rhs):
	return _length(_sub(lhs, rhs))


def _vector_average(vectors):
	if not vectors:
		return (0.0, 0.0, 0.0)
	total = (0.0, 0.0, 0.0)
	for vector in vectors:
		total = _add(total, vector)
	count = float(len(vectors))
	return (total[0] / count, total[1] / count, total[2] / count)


def _vector_min_max_average(vectors):
	if not vectors:
		return (0.0, 0.0, 0.0)
	first = vectors[0]
	max_x = min_x = first[0]
	max_y = min_y = first[1]
	max_z = min_z = first[2]
	for vector in vectors[1:]:
		max_x = max(max_x, vector[0])
		max_y = max(max_y, vector[1])
		max_z = max(max_z, vector[2])
		min_x = min(min_x, vector[0])
		min_y = min(min_y, vector[1])
		min_z = min(min_z, vector[2])
	return ((min_x + max_x) / 2.0, (min_y + max_y) / 2.0, (min_z + max_z) / 2.0)


def _rotate_about_axis(vec, angle_radians, axis_mode):
	if axis_mode == 0:
		return (
			vec[0],
			vec[1] * math.cos(angle_radians) - vec[2] * math.sin(angle_radians),
			vec[1] * math.sin(angle_radians) + vec[2] * math.cos(angle_radians),
		)
	if axis_mode == 1:
		return (
			vec[2] * math.sin(angle_radians) + vec[0] * math.cos(angle_radians),
			vec[1],
			vec[2] * math.cos(angle_radians) - vec[0] * math.sin(angle_radians),
		)
	return (
		vec[0] * math.cos(angle_radians) - vec[1] * math.sin(angle_radians),
		vec[0] * math.sin(angle_radians) + vec[1] * math.cos(angle_radians),
		vec[2],
	)


def _quaternion_multiply(left, right):
	t1 = left[0]
	v1 = left[1:4]
	t2 = right[0]
	v2 = right[1:4]
	vec = _add(_add(_mul(v2, t1), _mul(v1, t2)), _cross(v1, v2))
	return (t1 * t2 - _dot(v1, v2), vec[0], vec[1], vec[2])


def _quaternion_rotate(point, axis, angle_radians):
	axis = _unit(axis, (1.0, 0.0, 0.0))
	point_quaternion = (0.0, point[0], point[1], point[2])
	quaternion = (
		math.cos(angle_radians / 2.0),
		axis[0] * math.sin(angle_radians / 2.0),
		axis[1] * math.sin(angle_radians / 2.0),
		axis[2] * math.sin(angle_radians / 2.0),
	)
	reverse = (
		math.cos(angle_radians / 2.0),
		-axis[0] * math.sin(angle_radians / 2.0),
		-axis[1] * math.sin(angle_radians / 2.0),
		-axis[2] * math.sin(angle_radians / 2.0),
	)
	result = _quaternion_multiply(_quaternion_multiply(reverse, point_quaternion), quaternion)
	return (result[1], result[2], result[3])


def _project_point_to_plane(origin, normal, point):
	normal_length_sq = _dot(normal, normal)
	if normal_length_sq <= 1e-8:
		return point
	d = -_dot(origin, normal)
	x = (point[0] * (normal[1] * normal[1] + normal[2] * normal[2]) - (point[1] * normal[1] + point[2] * normal[2] + d) * normal[0]) / normal_length_sq
	y = (point[1] * (normal[2] * normal[2] + normal[0] * normal[0]) - (point[2] * normal[2] + point[0] * normal[0] + d) * normal[1]) / normal_length_sq
	z = (point[2] * (normal[0] * normal[0] + normal[1] * normal[1]) - (point[0] * normal[0] + point[1] * normal[1] + d) * normal[2]) / normal_length_sq
	return (x, y, z)


def _component_index(component):
	match = re.search(r'\[(\d+)\]', component)
	if not match:
		return None
	return int(match.group(1))


def _selected_transforms():
	transforms = cmds.ls(sl=True, tr=True, long=True) or []
	if transforms:
		return transforms
	selection = cmds.ls(sl=True, long=True) or []
	objects = cmds.polyListComponentConversion(selection) or []
	return cmds.listRelatives(objects, p=True, pa=True, type='transform', fullPath=True) or []


def _edge_vertices(edge):
	vertices = cmds.polyListComponentConversion(edge, fromEdge=True, toVertex=True) or []
	return cmds.ls(vertices, flatten=True, long=True) or []


def ordered_vertices_from_edges(edges):
	edges = cmds.ls(edges, flatten=True, long=True) or []
	edge_vertices = {}
	vertex_edges = {}
	for edge in edges:
		vertices = _edge_vertices(edge)
		if len(vertices) < 2:
			continue
		edge_vertices[edge] = vertices[:2]
		for vertex in edge_vertices[edge]:
			vertex_edges.setdefault(vertex, set()).add(edge)

	remaining = set(edge_vertices.keys())
	ordered_vertices = []

	while remaining:
		start_edge = next(edge for edge in edges if edge in remaining)
		component_edges = set()
		pending = [start_edge]
		while pending:
			current_edge = pending.pop()
			if current_edge in component_edges:
				continue
			component_edges.add(current_edge)
			for vertex in edge_vertices[current_edge]:
				pending.extend(list(vertex_edges.get(vertex, set()) & remaining))

		degrees = {}
		for component_edge in component_edges:
			for vertex in edge_vertices[component_edge]:
				degrees[vertex] = degrees.get(vertex, 0) + 1

		endpoints = [vertex for vertex, degree in degrees.items() if degree == 1]
		is_loop = len(endpoints) == 0
		if is_loop:
			current_vertex = edge_vertices[start_edge][0]
		else:
			current_vertex = edge_vertices[start_edge][0]
			previous_edge = start_edge
			while current_vertex not in endpoints:
				next_edges = [
					edge for edge in vertex_edges.get(current_vertex, [])
					if edge in component_edges and edge != previous_edge
				]
				if not next_edges:
					break
				next_edge = next_edges[0]
				vertex_a, vertex_b = edge_vertices[next_edge]
				current_vertex = vertex_b if vertex_a == current_vertex else vertex_a
				previous_edge = next_edge
		previous_edge = None
		visited_edges = set()
		component_vertices = [current_vertex]

		while True:
			next_edges = [
				edge for edge in sorted(vertex_edges.get(current_vertex, []))
				if edge in component_edges and edge != previous_edge and edge not in visited_edges
			]
			if not next_edges:
				break
			next_edge = next_edges[0]
			visited_edges.add(next_edge)
			vertex_a, vertex_b = edge_vertices[next_edge]
			next_vertex = vertex_b if vertex_a == current_vertex else vertex_a
			if is_loop and next_vertex == component_vertices[0]:
				break
			component_vertices.append(next_vertex)
			previous_edge = next_edge
			current_vertex = next_vertex
			if len(visited_edges) == len(component_edges):
				break

		ordered_vertices.extend(component_vertices)
		ordered_vertices.append('--Loop' if is_loop else '--')
		remaining -= component_edges

	return ordered_vertices


def _alignment_circle(vertex_list, distance_input, move_mode, priority_vertices):
	vertex_positions = [tuple(cmds.pointPosition(vertex, world=True)) for vertex in vertex_list]
	center_position = _vector_min_max_average(vertex_positions)
	vectors = []
	triangle_normals = []
	for index, position in enumerate(vertex_positions):
		vector_a = _sub(position, center_position)
		vectors.append(vector_a)
		next_position = vertex_positions[index + 1] if index + 1 < len(vertex_positions) else vertex_positions[0]
		triangle_normals.append(_unit(_cross(vector_a, _sub(next_position, center_position))))
	center_normal = _unit(_vector_average(triangle_normals), (0.0, 0.0, -1.0))

	if distance_input == 0 or move_mode == 1:
		distance = sum([_distance(center_position, position) for position in vertex_positions]) / float(len(vertex_positions))
	else:
		distance = distance_input

	if move_mode == 1:
		return distance

	if move_mode == 0:
		axis = (0.0, 1.0, 0.0)
		priority_vertices = set(cmds.ls(priority_vertices or [], flatten=True, long=True) or [])
		fix_vertex_number = 0
		priority_vertex_found = False
		minimum_angle = math.pi + 0.01
		minimum_vertex_number = 0

		for index, vertex in enumerate(vertex_list):
			if vertex in priority_vertices:
				priority_vertex_found = True
				fix_vertex_number = index
			else:
				axis_angle = _angle(axis, vectors[index])
				if axis_angle < minimum_angle:
					minimum_angle = axis_angle
					minimum_vertex_number = index

		if not priority_vertex_found:
			fix_vertex_number = minimum_vertex_number

		sorted_vertices = []
		sorted_positions = []
		index = fix_vertex_number
		while len(sorted_vertices) < len(vertex_list):
			sorted_vertices.append(vertex_list[index])
			sorted_positions.append(vertex_positions[index])
			index += 1
			if index >= len(vertex_list):
				index = 0

		base_positions = []
		rotation_degrees = 360.0 / float(len(sorted_vertices))
		for index in range(len(sorted_vertices)):
			radians = math.radians(rotation_degrees * index)
			base_positions.append((distance * math.sin(radians), distance * math.cos(radians), 0.0))

		base_normal = (0.0, 0.0, -1.0)
		normal_cross = _unit(_cross(base_normal, center_normal), (1.0, 0.0, 0.0))
		normal_angle = _angle(base_normal, center_normal)
		fixed_local_position = _sub(sorted_positions[0], center_position)
		rotated_fixed_position = _quaternion_rotate(fixed_local_position, normal_cross, normal_angle)
		fixed_front_vector = (rotated_fixed_position[0], rotated_fixed_position[1], 0.0)
		fix_cross = _cross(base_positions[0], fixed_front_vector)
		fix_angle = _angle(base_positions[0], fixed_front_vector)
		if fix_cross[2] < 0:
			fix_angle *= -1.0

		move_positions = []
		for position in base_positions:
			move_positions.append(_quaternion_rotate(_rotate_about_axis(position, fix_angle, 2), normal_cross, -normal_angle))

		for index, vertex in enumerate(sorted_vertices):
			move_position = _add(move_positions[index], center_position)
			cmds.move(move_position[0], move_position[1], move_position[2], vertex, absolute=True, worldSpace=True)

	if move_mode == 4:
		for index, vertex in enumerate(vertex_list):
			plane_position = _project_point_to_plane(center_position, center_normal, vertex_positions[index])
			point_normal = _unit(_sub(plane_position, center_position), (0.0, 1.0, 0.0))
			move_position = _add(_mul(point_normal, distance), center_position)
			cmds.move(move_position[0], move_position[1], move_position[2], vertex, absolute=True, worldSpace=True)

	return distance


def _alignment_semicircle(vertex_list, input_angle, move_mode):
	if len(vertex_list) <= 2:
		return 0.0

	vertex_positions = [tuple(cmds.pointPosition(vertex, world=True)) for vertex in vertex_list]
	first_position = vertex_positions[0]
	last_position = vertex_positions[-1]
	target_vector = _sub(last_position, first_position)
	center_position = _vector_min_max_average(vertex_positions)
	vectors = []
	triangle_normals = []
	for index, position in enumerate(vertex_positions):
		vector_a = _sub(position, center_position)
		vectors.append(vector_a)
		next_position = vertex_positions[index + 1] if index + 1 < len(vertex_positions) else vertex_positions[0]
		triangle_normals.append(_unit(_cross(vector_a, _sub(next_position, center_position))))
	center_normal = _vector_average(triangle_normals)

	if input_angle == 0 or move_mode == 2:
		angle_total = 0.0
		for index in range(1, len(vertex_positions) - 1):
			angle_total += _angle(_sub(vertex_positions[index], first_position), _sub(vertex_positions[index], last_position))
		angle_average = angle_total / float(len(vertex_positions) - 2)
		input_angle = 360.0 - (math.degrees(angle_average) * 2.0)

	distance = (_distance(first_position, last_position) / 2.0) / math.sin(math.radians((360.0 - input_angle) / 2.0))
	if move_mode == 1:
		return distance
	if move_mode == 2:
		return input_angle

	base_positions = []
	rotation_degrees = input_angle / float(len(vertex_list) - 1)
	for index in range(len(vertex_list)):
		radians = math.radians(rotation_degrees * index + 180.0 - (input_angle / 2.0))
		base_positions.append((distance * math.sin(radians), distance * math.cos(radians), 0.0))

	base_normal = (0.0, 0.0, -1.0)
	base_vector = (-1.0, 0.0, 0.0)
	vector_cross = _unit(_cross(base_vector, target_vector), (0.0, 0.0, 1.0))
	vector_angle = _angle(base_vector, target_vector)
	rotated_target_vector = _quaternion_rotate(center_normal, vector_cross, vector_angle)
	rotated_target_front = (0.0, rotated_target_vector[1], rotated_target_vector[2])
	first_cross = _cross(base_normal, rotated_target_front)
	first_angle = _angle(base_normal, rotated_target_front)
	if first_cross[0] < 0:
		first_angle *= -1.0

	move_positions = []
	for position in base_positions:
		move_positions.append(_quaternion_rotate(_rotate_about_axis(position, first_angle, 0), vector_cross, -vector_angle))

	translation = _sub(first_position, move_positions[0])
	for index, vertex in enumerate(vertex_list):
		move_position = _add(move_positions[index], translation)
		cmds.move(move_position[0], move_position[1], move_position[2], vertex, absolute=True, worldSpace=True)

	return distance


def circle_vertices(move_mode, use_average_distance, use_average_angle, average_distance, average_angle, priority_vertices=None):
	distance = 0.0 if use_average_distance else average_distance
	angle = 0.0 if use_average_angle else average_angle
	distance /= 2.0

	selection = cmds.ls(sl=True, flatten=True, long=True) or []
	edges = cmds.filterExpand(selection, selectionMask=32, expand=True) or []
	sorted_vertices = ordered_vertices_from_edges(edges) if edges else []
	faces = cmds.filterExpand(selection, selectionMask=34, expand=True) or []

	if faces:
		border_edges = []
		face_edges = cmds.polyListComponentConversion(faces, toEdge=True) or []
		face_edges = cmds.ls(face_edges, flatten=True, long=True) or []
		for edge in face_edges:
			edge_faces = cmds.polyListComponentConversion(edge, toFace=True) or []
			edge_faces = cmds.filterExpand(edge_faces, selectionMask=34, expand=True) or []
			if len(edge_faces) == 1:
				border_edges.append(edge)
		cmds.select(faces, r=True)
		cmds.ConvertSelectionToEdgePerimeter()
		if border_edges:
			cmds.select(border_edges, add=True)
		selected_edge_list = cmds.ls(sl=True, flatten=True, long=True) or []
		edges = cmds.filterExpand(selected_edge_list, selectionMask=32, expand=True) or []
		sorted_vertices = ordered_vertices_from_edges(edges)
		cmds.select(selected_edge_list, r=True)

	vertex_group = []
	distance_total = 0.0
	distance_count = 0
	angle_total = 0.0
	angle_count = 0
	priority_vertices = priority_vertices or []

	for vertex in sorted_vertices:
		if vertex == '--Loop':
			if vertex_group:
				distance_total += _alignment_circle(vertex_group, distance, move_mode, priority_vertices)
				distance_count += 1
			vertex_group = []
			continue
		if vertex == '--':
			if vertex_group:
				angle_total += _alignment_semicircle(vertex_group, angle, move_mode)
				angle_count += 1
			vertex_group = []
			continue
		vertex_group.append(vertex)

	result = {}
	if distance_count:
		result['distance'] = distance_total / float(distance_count) * 2.0
	if angle_count:
		result['angle'] = angle_total / float(angle_count)
	return result


def _edge_point(vertex):
	edges = cmds.polyListComponentConversion(vertex, toEdge=True) or []
	edges = cmds.ls(edges, flatten=True, long=True) or []
	if not edges:
		return None
	edge = edges[0]
	vertex_index = _component_index(vertex)
	edge_index = _component_index(edge)
	info = cmds.polyInfo(edge, edgeToVertex=True) or []
	indices = [int(value) for value in re.findall(r'\d+', info[0])] if info else []
	if len(indices) < 3 or vertex_index is None or edge_index is None:
		return None
	side = 0 if indices[1] == vertex_index else 1
	return (edge_index, side)


def _split_vertices(vertex_a, vertex_b):
	object_name = vertex_a.split('.')[0]
	edge_point_a = _edge_point(vertex_a)
	edge_point_b = _edge_point(vertex_b)
	if edge_point_a is None or edge_point_b is None:
		return
	cmds.polySplit(object_name, ch=True, sma=180, ip=[edge_point_a, edge_point_b])


def split_polygon():
	object_transforms = _selected_transforms()
	if len(object_transforms) != 1:
		return

	obj = object_transforms[0]
	selection = cmds.ls(sl=True, flatten=True, long=True) or []
	edge_list = cmds.filterExpand(selection, selectionMask=32, expand=True) or []
	vertex_list = cmds.filterExpand(selection, selectionMask=31, expand=True) or []
	two_vertex_mode = len(vertex_list) == 2
	if not edge_list and not two_vertex_mode:
		return

	if two_vertex_mode:
		ordered_a = [vertex_list[0]]
		ordered_b = [vertex_list[1]]
	else:
		ordered_vertices = ordered_vertices_from_edges(edge_list)
		ordered_a = []
		ordered_b = []
		first_group = True
		for vertex in ordered_vertices:
			if vertex == '--':
				first_group = False
				continue
			if vertex == '--Loop':
				continue
			if first_group:
				ordered_a.append(vertex)
			else:
				ordered_b.append(vertex)
		if not ordered_b:
			return

	translate = cmds.getAttr(obj + '.translate')[0]
	rotate = cmds.getAttr(obj + '.rotate')[0]
	scale = cmds.getAttr(obj + '.scale')[0]
	cmds.setAttr(obj + '.translate', 0, 0, 0)
	cmds.setAttr(obj + '.rotate', 0, 0, 0)
	cmds.setAttr(obj + '.scale', 1, 1, 1)

	vertex_a_start = tuple(cmds.pointPosition(ordered_a[0], world=True))
	vertex_a_end = tuple(cmds.pointPosition(ordered_a[-1], world=True))
	vertex_b_start = tuple(cmds.pointPosition(ordered_b[0], world=True))
	vertex_b_end = tuple(cmds.pointPosition(ordered_b[-1], world=True))
	angle_a = _angle(_sub(vertex_b_start, vertex_a_start), _sub(vertex_b_end, vertex_a_end))
	angle_b = _angle(_sub(vertex_b_start, vertex_a_end), _sub(vertex_b_end, vertex_a_start))
	if angle_a > angle_b:
		ordered_b = list(reversed(ordered_b))

	max_size = min(len(ordered_a), len(ordered_b))
	cross_sorted_a = list(ordered_a)
	cross_sorted_b = list(ordered_b)
	for index in range(len(ordered_a)):
		cross_sorted_a[index] = ordered_a[index // 2] if index % 2 == 0 else ordered_a[len(ordered_a) - 1 - (index // 2)]
	for index in range(len(ordered_b)):
		cross_sorted_b[index] = ordered_b[index // 2] if index % 2 == 0 else ordered_b[len(ordered_b) - 1 - (index // 2)]

	for index in range(max_size):
		_split_vertices(cross_sorted_a[index], cross_sorted_b[index])

	cmds.setAttr(obj + '.translate', translate[0], translate[1], translate[2])
	cmds.setAttr(obj + '.rotate', rotate[0], rotate[1], rotate[2])
	cmds.setAttr(obj + '.scale', scale[0], scale[1], scale[2])