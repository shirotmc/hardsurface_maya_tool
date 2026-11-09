import maya.cmds as cmds
import maya.api.OpenMaya as om


STATE = {
	'faces': [],
	'normal': (0.0, 0.0, 1.0),
	'per_face': False,
}


def _selected_faces():
	return [item for item in (cmds.ls(orderedSelection=True, long=True, flatten=True) or []) if '.f[' in item]


def _selection_order_enabled():
	return cmds.selectPref(q=True, trackSelectionOrder=True)


def _mesh_and_face_index(face_component):
	mesh_name, face_token = face_component.split('.f[')
	face_index = int(face_token.rstrip(']').split(':', 1)[0])
	return mesh_name, face_index


def _face_normal(face_component):
	mesh_name, face_index = _mesh_and_face_index(face_component)
	selection = om.MSelectionList()
	selection.add(mesh_name)
	dag_path = selection.getDagPath(0)
	if dag_path.apiType() != om.MFn.kMesh:
		dag_path.extendToShape()
	normal = om.MFnMesh(dag_path).getPolygonNormal(face_index, om.MSpace.kWorld)
	return (normal.x, normal.y, normal.z)


def _average_vector(vectors):
	if not vectors:
		return (0.0, 0.0, 1.0)
	count = float(len(vectors))
	return (
		sum(vector[0] for vector in vectors) / count,
		sum(vector[1] for vector in vectors) / count,
		sum(vector[2] for vector in vectors) / count,
	)


def _constraint_select(seed_faces, normal, angle):
	cmds.polySelectConstraint(disable=True)
	cmds.polySelectConstraint(
		mode=2,
		type=0x0008,
		orient=1,
		orientaxis=normal,
		orientbound=(0, angle),
	)
	cmds.select(seed_faces, replace=True)
	for _ in range(50):
		cmds.polySelectConstraint(pp=1)
	return cmds.ls(sl=True, long=True, flatten=True) or []


def _clear_constraints():
	cmds.polySelectConstraint(orient=0, orientaxis=(0, 0, 0), orientbound=(0, 0))
	cmds.polySelectConstraint(disable=True)


def _restore_selection_pref(was_enabled):
	if not was_enabled:
		cmds.selectPref(trackSelectionOrder=False)


def grow_selection_by_normal_angle(angle, *args):
	faces = _selected_faces()
	if not faces:
		cmds.warning('Please select one or more polygon faces.')
		return []

	selection_order = _selection_order_enabled()
	cmds.selectPref(trackSelectionOrder=True)
	internal_edges = cmds.ls(
		cmds.polyListComponentConversion(faces, fromFace=True, toEdge=True, internal=True) or [],
		flatten=True,
	) or []

	try:
		if len(faces) == 1 or internal_edges:
			normal = _average_vector([_face_normal(face) for face in faces])
			result = _constraint_select(faces, normal, angle)
			STATE['normal'] = normal
			STATE['per_face'] = False
		else:
			result = []
			for face in faces:
				result.extend(_constraint_select([face], _face_normal(face), angle))
			result = list(dict.fromkeys(result))
			cmds.select(result, replace=True)
			STATE['normal'] = _average_vector([_face_normal(face) for face in faces])
			STATE['per_face'] = True
		STATE['faces'] = list(faces)
		return result
	finally:
		_clear_constraints()
		_restore_selection_pref(selection_order)


def update_angle(angle, *args):
	faces = list(STATE['faces'])
	if not faces:
		return grow_selection_by_normal_angle(angle)

	selection_order = _selection_order_enabled()
	cmds.selectPref(trackSelectionOrder=True)

	try:
		if not STATE['per_face']:
			result = _constraint_select(faces, STATE['normal'], angle)
			cmds.select(result, replace=True)
			return result

		result = []
		for face in faces:
			if cmds.objExists(face):
				result.extend(_constraint_select([face], _face_normal(face), angle))
		result = list(dict.fromkeys(result))
		cmds.select(result, replace=True)
		return result
	finally:
		_clear_constraints()
		_restore_selection_pref(selection_order)


def force_clean_up_by_combine(clean_list):
	transforms = cmds.ls(clean_list, long=True, type='transform') or []
	if not transforms:
		raise RuntimeError('Nothing To Combine!')

	primary = transforms[0]
	uv_sets = cmds.polyUVSet(primary, q=True, allUVSets=True) or []
	parent = (cmds.listRelatives(primary, fullPath=True, parent=True) or [None])[0]
	result_name = primary.split('|')[-1]
	proxy_cube = cmds.polyCube(ch=False, o=True, w=1, h=1, d=1, cuv=4)[0]
	combined = cmds.polyUnite(*(transforms + [proxy_cube]), ch=False)[0]
	if cmds.objExists(proxy_cube):
		cmds.delete(proxy_cube)

	face_count = cmds.polyEvaluate(combined, face=True) or 0
	if face_count >= 6:
		cmds.delete('{0}.f[{1}:{2}]'.format(combined, face_count - 6, face_count - 1))

	result = cmds.rename(combined, result_name)
	cmds.delete(result, ch=True)
	if parent and cmds.objExists(parent):
		result = cmds.parent(result, parent)[0]

	new_uv_sets = cmds.polyUVSet(result, q=True, allUVSets=True) or []
	if len(new_uv_sets) != len(uv_sets) and 'map1' in new_uv_sets and len(new_uv_sets) > 1:
		cmds.polyUVSet(result, delete=True, uvSet='map1')

	return result


def force_clean_up_by_combine_preprocess(*args):
	selection = cmds.ls(sl=True, long=True) or []
	results = []
	for item in selection:
		cmds.select(clear=True)
		cmds.select(item, replace=True)
		results.append(force_clean_up_by_combine([item]))
		cmds.select(clear=True)
	if results:
		cmds.select(results, replace=True)
	return results