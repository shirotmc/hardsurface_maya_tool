import maya.cmds as cmds


def _selected_faces_and_parent_target():
	selection = cmds.ls(sl=True, long=True, flatten=True) or []
	if not selection:
		raise RuntimeError('Nothing selected.')

	parent_target = None
	face_selection = list(selection)
	if '.f[' not in selection[-1]:
		parent_target = selection[-1]
		face_selection = selection[:-1]

	faces = [item for item in face_selection if '.f[' in item]
	if not faces:
		raise RuntimeError('Please select polygon faces.')

	mesh_transform = faces[0].split('.', 1)[0]
	return faces, mesh_transform, parent_target


def _duplicate_faces(face_components):
	original_transform = face_components[0].split('.', 1)[0]
	duplicate_transform = cmds.duplicate(original_transform, rr=True)[0]
	duplicate_faces = [component.replace(original_transform, duplicate_transform, 1) for component in face_components]
	return original_transform, duplicate_transform, duplicate_faces


def clone_faces(*args):
	face_components, _, parent_target = _selected_faces_and_parent_target()
	_, duplicate_transform, duplicate_faces = _duplicate_faces(face_components)

	all_duplicate_faces = cmds.ls(cmds.polyListComponentConversion(duplicate_transform, toFace=True) or [], flatten=True) or []
	faces_to_delete = [face for face in all_duplicate_faces if face not in set(duplicate_faces)]
	if faces_to_delete:
		cmds.delete(faces_to_delete)

	if parent_target and cmds.objExists(parent_target):
		duplicate_transform = cmds.parent(duplicate_transform, parent_target)[0]

	cmds.select(duplicate_transform, replace=True)
	return duplicate_transform


def detach_faces(*args):
	face_components, original_transform, parent_target = _selected_faces_and_parent_target()
	_, duplicate_transform, duplicate_faces = _duplicate_faces(face_components)

	all_duplicate_faces = cmds.ls(cmds.polyListComponentConversion(duplicate_transform, toFace=True) or [], flatten=True) or []
	faces_to_delete_from_duplicate = [face for face in all_duplicate_faces if face not in set(duplicate_faces)]
	if faces_to_delete_from_duplicate:
		cmds.delete(faces_to_delete_from_duplicate)

	if cmds.objExists(original_transform):
		cmds.delete(face_components)

	if parent_target and cmds.objExists(parent_target):
		duplicate_transform = cmds.parent(duplicate_transform, parent_target)[0]

	cmds.select(duplicate_transform, replace=True)
	return duplicate_transform


def combine_objects(*args):
	selection = cmds.ls(sl=True, long=True) or []
	if not selection:
		raise RuntimeError('Nothing Selected.')

	transforms = []
	for item in selection:
		if cmds.nodeType(item) == 'transform':
			shapes = cmds.listRelatives(item, shapes=True, fullPath=True) or []
			if any(cmds.nodeType(shape) == 'mesh' for shape in shapes):
				transforms.append(item)
		elif cmds.nodeType(item) == 'mesh':
			parent = cmds.listRelatives(item, parent=True, fullPath=True) or []
			if parent:
				transforms.append(parent[0])

	transforms = list(dict.fromkeys(transforms))
	if len(transforms) < 2:
		raise RuntimeError('Not enough objects selected. You need at least TWO.')

	master = transforms[0]
	short_name = master.rsplit('|', 1)[-1]
	parent = (cmds.listRelatives(master, parent=True, fullPath=True) or [None])[0]
	translation = cmds.getAttr(master + '.translate')[0]
	pivot = cmds.xform(master, q=True, ws=True, sp=True)
	layers = cmds.listConnections(master, source=True, type='displayLayer') or []

	cmds.showHidden(transforms, below=True)
	for transform in transforms:
		try:
			cmds.lockNode(transform, lock=False)
		except RuntimeError:
			pass

	combined = cmds.polyUnite(transforms, ch=False)[0]
	cmds.delete(combined, ch=True)

	for transform in transforms:
		if cmds.objExists(transform):
			cmds.delete(transform)

	for attr in ('doubleSided', 'opposite'):
		if cmds.attributeQuery(attr, node=combined, exists=True):
			cmds.setAttr(combined + '.' + attr, 0)

	cmds.move(-translation[0], -translation[1], -translation[2], combined, absolute=True)
	cmds.move(0, 0, 0, combined + '.scalePivot', absolute=True)
	cmds.move(0, 0, 0, combined + '.rotatePivot', absolute=True)
	cmds.makeIdentity(combined, apply=True)
	cmds.move(translation[0], translation[1], translation[2], combined, absolute=True)
	cmds.move(pivot[0], pivot[1], pivot[2], combined + '.scalePivot', absolute=True, ws=True)
	cmds.move(pivot[0], pivot[1], pivot[2], combined + '.rotatePivot', absolute=True, ws=True)

	if parent and cmds.objExists(parent):
		combined = cmds.parent(combined, parent, absolute=True)[0]
		cmds.reorder(combined, front=True)

	for layer in layers:
		if layer != 'defaultLayer' and cmds.objExists(layer):
			cmds.editDisplayLayerMembers(layer, combined, noRecurse=True)

	final_name = cmds.rename(combined, short_name)
	cmds.select(final_name, replace=True)
	return final_name