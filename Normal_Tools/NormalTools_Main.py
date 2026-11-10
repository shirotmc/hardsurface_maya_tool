import maya.cmds as cmds
import maya.api.OpenMaya as om
import math
import os
import site

try:
	from importlib import reload
except:
	pass

# VARIABLES

LOCAL_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace("\\", "/")  # HSTool root (self-locating)

#region SUPPORT
site.addsitedir(LOCAL_PATH + '/Normal_Tools/Scripts/Python')
import normal_mel_port
reload(normal_mel_port)
import normal_value_copy
reload(normal_value_copy)

def normalize_vector(vector):
	vector_length = math.sqrt(sum([e**2 for e in vector]))
	normalize_vector = [e/vector_length for e in vector]
	return normalize_vector

def average_vectors(vectors):
	if not vectors:
		return [0.0, 0.0, 1.0]

	average_vector = [
		sum(axis_values) / float(len(vectors))
		for axis_values in zip(*vectors)
	]

	vector_length = math.sqrt(sum([element ** 2 for element in average_vector]))
	if vector_length <= 0.000001:
		return [0.0, 0.0, 1.0]

	return [element / vector_length for element in average_vector]

def get_average_vertex_normal(vertex):
	vertex_normals = cmds.polyNormalPerVertex(vertex, query=True, normalXYZ=True) or []
	if not vertex_normals:
		return [0.0, 0.0, 1.0]

	normal_vectors = []
	for i in range(0, len(vertex_normals), 3):
		normal_vectors.append(vertex_normals[i:i+3])

	return average_vectors(normal_vectors)

def ensure_tracked_selection_order():
	if cmds.selectPref(tso=True, q=True) == 0:
		cmds.selectPref(tso=True)

def get_edge_vertices(edge):
	return cmds.ls(cmds.polyListComponentConversion(edge, fromEdge=True, toVertex=True), flatten=True, long=True) or []

def get_connected_vertex_groups_from_edges(edges):
	vertex_neighbors = {}

	for edge in edges:
		vertices = get_edge_vertices(edge)
		if len(vertices) != 2:
			continue

		vertex_neighbors.setdefault(vertices[0], set()).add(vertices[1])
		vertex_neighbors.setdefault(vertices[1], set()).add(vertices[0])

	connected_groups = []
	remaining_vertices = set(vertex_neighbors.keys())

	while remaining_vertices:
		start_vertex = remaining_vertices.pop()
		stack = [start_vertex]
		group = [start_vertex]

		while stack:
			current_vertex = stack.pop()
			for neighbor in vertex_neighbors.get(current_vertex, set()):
				if neighbor in remaining_vertices:
					remaining_vertices.remove(neighbor)
					stack.append(neighbor)
					group.append(neighbor)

		connected_groups.append(group)

	return connected_groups

def find_closest_vertex(mesh, target_position, max_distance=None):
	vertices = cmds.ls(mesh + '.vtx[*]', flatten=True, long=True) or []
	closest_vertex = None
	closest_distance = None
	max_distance_squared = None

	if max_distance is not None:
		max_distance_squared = max_distance * max_distance

	for vertex in vertices:
		position = cmds.pointPosition(vertex, world=True)
		distance = sum([(src - dst) ** 2 for src, dst in zip(position, target_position)])

		if max_distance_squared is not None and distance > max_distance_squared:
			continue

		if closest_distance is None or distance < closest_distance:
			closest_distance = distance
			closest_vertex = vertex

	if closest_vertex or max_distance is None:
		return closest_vertex

	for vertex in vertices:
		position = cmds.pointPosition(vertex, world=True)
		distance = sum([(src - dst) ** 2 for src, dst in zip(position, target_position)])
		if closest_distance is None or distance < closest_distance:
			closest_distance = distance
			closest_vertex = vertex

	return closest_vertex

def toggle_selected_normal(*arg):
	normal_size = cmds.floatField('normal_size_textfield', v=True, q=True)
	is_display_normals = cmds.polyOptions(activeObjects=True, displayNormal=True, query=True)
	if (is_display_normals):
		toggle_normals = not is_display_normals[0]
		cmds.polyOptions(activeObjects=True, displayNormal=toggle_normals, point=True, sizeNormal= normal_size)

def toggle_everything_normal(*arg):
	normal_size = cmds.floatField('normal_size_textfield', v=True, q=True)
	is_display_normals = cmds.polyOptions(activeObjects=True, displayNormal=True, query=True)
	if (is_display_normals):
		toggle_normals = not is_display_normals[0]
	cmds.polyOptions(gl=True, displayNormal=toggle_normals, point=True, sizeNormal=normal_size)

#endregion

#region COPY/PASTE NORMAL

def get_selected_object():
	sel_comp = cmds.ls(sl=True)
	sel_obj  = []

	for comp in sel_comp:
		obj = comp.split('.')[0]
		if obj not in sel_obj:
			sel_obj.append(obj)

	return sel_obj

def copy_vertex_normal(*arg):
	normal_mel_port.copy_vertex_normals('x')

def paste_vertex_normal(*arg):
	normal_mel_port.paste_vertex_normals('x')


def copy_average_normal(*arg):
	normal_mel_port.copy_average_vertex_normal()

def copy_paste_average_3_vetices_normals(*arg):
	normal_mel_port.paste_vertex_normals_three_vertices()

def copy_paste_average_normals(*arg):
	normal_mel_port.copy_paste_average_vertex_normal()

def set_average_normal_and_merge_vertices(*arg):
	verts = cmds.ls(selection=True, flatten=True)

	normal_mel_port.copy_paste_average_vertex_normal()
	
	if verts:
		positions = [cmds.pointPosition(v, world=True) for v in verts]
		center = [
			sum(axis_values) / float(len(axis_values))
			for axis_values in zip(*positions)
		]

		cmds.xform(verts, worldSpace=True, translation=center)
		cmds.polyMergeVertex(verts, distance=0.001, alwaysMergeTwoVertices=True, constructionHistory=False)

def target_weld_keep_normal(*arg):
	ensure_tracked_selection_order()
	selected_components = cmds.ls(orderedSelection=True, flatten=True, long=True) or []
	selected_vertices = cmds.filterExpand(selected_components, selectionMask=31, expand=True) or []

	if len(selected_vertices) != 2:
		cmds.confirmDialog(title='Confirm', message='Please select exactly 2 vertices in order: target first, source second', button=['Confirm'], defaultButton='Confirm', cancelButton='Confirm', dismissString='No')
		return

	target_vertex = selected_vertices[0]
	source_vertex = selected_vertices[1]
	target_mesh = target_vertex.split('.')[0]
	source_mesh = source_vertex.split('.')[0]

	if target_vertex == source_vertex:
		cmds.confirmDialog(title='Confirm', message='Please select 2 different vertices', button=['Confirm'], defaultButton='Confirm', cancelButton='Confirm', dismissString='No')
		return

	if target_mesh != source_mesh:
		cmds.confirmDialog(title='Confirm', message='Please select 2 vertices on the same mesh', button=['Confirm'], defaultButton='Confirm', cancelButton='Confirm', dismissString='No')
		return

	target_position = cmds.pointPosition(target_vertex, world=True)
	target_normal = get_average_vertex_normal(target_vertex)
	result_vertex = None

	cmds.undoInfo(openChunk=True)
	try:
		cmds.xform(source_vertex, worldSpace=True, translation=target_position)
		cmds.polyMergeVertex([target_vertex, source_vertex], distance=0.0001, alwaysMergeTwoVertices=True, constructionHistory=False)
		result_vertex = find_closest_vertex(target_mesh, target_position, max_distance=0.001)
		if result_vertex:
			cmds.polyNormalPerVertex(result_vertex, xyz=target_normal)
	finally:
		cmds.undoInfo(closeChunk=True)

	if result_vertex:
		cmds.select(result_vertex, r=True)
	else:
		cmds.select(target_mesh, r=True)

def collapse_selected_edges_with_average_normals(*arg):
	selected_components = cmds.ls(selection=True, flatten=True, long=True) or []
	selected_edges = cmds.filterExpand(selected_components, selectionMask=32, expand=True) or []

	if not selected_edges:
		cmds.confirmDialog(title='Confirm', message='Please select one or more edges', button=['Confirm'], defaultButton='Confirm', cancelButton='Confirm', dismissString='No')
		return

	edges_by_mesh = {}
	for edge in selected_edges:
		mesh = edge.split('.')[0]
		edges_by_mesh.setdefault(mesh, []).append(edge)

	backup_meshes = []
	result_selection = []
	cmds.undoInfo(openChunk=True)
	try:
		for mesh, edges in edges_by_mesh.items():
			backup_mesh = cmds.duplicate(mesh, renameChildren=True)[0]
			backup_meshes.append(backup_mesh)
			vertex_groups = get_connected_vertex_groups_from_edges(edges)
			vertices_to_merge = []
			group_results = []

			for vertices in vertex_groups:
				if len(vertices) < 2:
					continue

				average_normal = average_vectors([get_average_vertex_normal(vertex) for vertex in vertices])
				positions = [cmds.pointPosition(vertex, world=True) for vertex in vertices]
				center_position = [
					sum(axis_values) / float(len(positions))
					for axis_values in zip(*positions)
				]
				max_distance = max([
					math.sqrt(sum([(src - dst) ** 2 for src, dst in zip(position, center_position)]))
					for position in positions
				])

				group_results.append({
					'center': center_position,
					'normal': average_normal,
					'max_distance': max_distance + 0.001
				})

				cmds.xform(vertices, worldSpace=True, translation=center_position)
				vertices_to_merge.extend(vertices)

			if vertices_to_merge:
				cmds.polyMergeVertex(vertices_to_merge, distance=0.0001, constructionHistory=False)
				cmds.transferAttributes(backup_mesh, mesh, transferPositions=0, transferNormals=1, transferUVs=0, transferColors=0)

				for group_result in group_results:
					collapsed_vertex = find_closest_vertex(mesh, group_result['center'], max_distance=group_result['max_distance'])
					if collapsed_vertex:
						cmds.polyNormalPerVertex(collapsed_vertex, xyz=group_result['normal'])
						result_selection.append(collapsed_vertex)
	finally:
		for backup_mesh in backup_meshes:
			if cmds.objExists(backup_mesh):
				cmds.delete(backup_mesh)
		if result_selection:
			cmds.select(result_selection, r=True)
		else:
			cmds.select(list(edges_by_mesh.keys()), r=True)
		cmds.undoInfo(closeChunk=True)

def inverse_selected_vertex_normals(*arg):
	selected = cmds.ls(sl=True, fl=True, l=True)
	for i in selected:
		cmds.select(d=True)
		cmds.select(i)
		list = cmds.polyNormalPerVertex(q=True, xyz=True)
		result = [0,0,0]
		while len(list):
			result = [result[0] + list.pop(0), result[1] + list.pop(0), result[2] + list.pop(0)]
		result = (-result[0], -result[1], -result[2])
		cmds.polyNormalPerVertex(xyz=result)
	cmds.select(selected)

def tranfer_normal(source, target):
	cmds.transferAttributes(source, target, transferPositions = 0, transferNormals = 1, transferUVs=0, transferColors=0)

#endregion

#region TRANSFER NORMAL
def pick_source_for_transfer(*arg):
	selected_mesh = cmds.ls(long=True, selection=True)

	if(len(selected_mesh)==1):
		cmds.textField('source_normal_textfield', e = True, tx = selected_mesh[0])
	else:
		cmds.confirmDialog(title='Confirm', message='Please select ONE mesh', button=['Confirm'], defaultButton='Confirm', cancelButton='Confirm', dismissString='No')

def copy_vertex_normal_for_transfer(source_vertices=None, destination_vertices=None):
	closest_vertex = None
	for destination_vertex in destination_vertices:

		min_distance = 1000000
		for source_vertex in source_vertices:

			source_vertex_coordinate = cmds.xform(source_vertex,
												query=True,
												worldSpace=True,
												translation=True)
			destination_vertex_coordinate = cmds.xform(destination_vertex,
												query=True,
												worldSpace=True,
												translation=True)

			distance_vertices = sum([(src - des)**2 for src, des in zip(source_vertex_coordinate, destination_vertex_coordinate)])

			if(distance_vertices < min_distance):
				min_distance = distance_vertices
				closest_vertex = source_vertex

		closest_vertex_normal = cmds.polyNormalPerVertex(closest_vertex, query=True, normalXYZ=True)

		for k in range(0, len(closest_vertex_normal), 3):
			cmds.polyNormalPerVertex(destination_vertex,
									normalXYZ=[closest_vertex_normal[k],
											closest_vertex_normal[k+1],
											closest_vertex_normal[k+2]])

def transfer_normals_to_selected_vertices(*arg):
	source_mesh = cmds.textField('source_normal_textfield', tx = True, q = True)
	selected_vertex = cmds.ls(long=True, selection=True, flatten=True)
	if(source_mesh and selected_vertex):
		if('.vtx' in selected_vertex[0]):
			transfer_normals_to_selected_vertices_function(source_mesh)
			cmds.select(d=True)
		else:
			infor = 'Please pick source MESH, then select destination VERTEX'
			cmds.confirmDialog(title='Confirm', message=infor, button=['Confirm'], defaultButton='Confirm', cancelButton='Confirm', dismissString='No')

	else:
		infor = 'Please pick source MESH, then select destination VERTEX'
		cmds.confirmDialog(title='Confirm', message=infor, button=['Confirm'], defaultButton='Confirm', cancelButton='Confirm', dismissString='No')

def transfer_normals_to_selected_vertices_function(source_mesh):

	# Get soft edges
	selected = cmds.ls(sl=True, fl=True)
	selected_object = get_selected_object()
	get_soft_edges()
	soft_edges = cmds.ls(sl=True, fl=True)

	cmds.undoInfo(openChunk = True)

	# # Get FnMesh Source
	cmds.select(selected)
	dgpa_source = om.MDagPath.getAPathTo(om.MSelectionList().add(source_mesh).getDependNode(0))
	fn_mesh_source = om.MFnMesh(dgpa_source)

	# Get Vertices Target and check if we have any face normal that closet to target vert
	selection_list = om.MGlobal.getActiveSelectionList()

	for i in range(selection_list.length()):
		dgpa, component = selection_list.getComponent(i)
		fn_mesh = om.MFnMesh(dgpa)
		
		if component.hasFn(om.MFn.kMeshVertComponent): # take infor of selected vertex
			vertex_normal_dict = {}
			vert_iter = om.MItMeshVertex(dgpa, component)

			while not vert_iter.isDone():
				v_pos = vert_iter.position()
				v_id = vert_iter.index()

				return_value = fn_mesh_source.getClosestNormal(v_pos, space=om.MSpace.kObject)
				if return_value:
					vertex_normal_dict[str(v_id)] = return_value[0]

				try:
					vert_iter.next(True)
				except:
					vert_iter.next()

			# Transfer closest normal to vertices
			for id, vector in vertex_normal_dict.items():
				fn_mesh.setVertexNormal(vector, int(id))

	# Set soft edge
	cmds.select(soft_edges)
	cmds.polySoftEdge(soft_edges, ch=True, angle=180)
	
	# Reset select
	cmds.ConvertSelectionToVertices()
	
	# Delete history
	cmds.delete(selected_object, constructionHistory = True)

	cmds.undoInfo(closeChunk = True)


def transfer_normals_to_object(*arg):
	source_mesh = cmds.textField('source_normal_textfield', tx = True, q = True)
	selected_mesh = cmds.ls(long=True, selection=True)

	if(source_mesh and selected_mesh):
		for e_mesh in selected_mesh:
			transfer_normals_to_object_function(source_mesh, e_mesh)
		cmds.select(d=True)
	else:
		cmds.confirmDialog(title='Confirm', message='Please pick SOURCE mesh, then select DESTINATION mesh', button=['Confirm'], defaultButton='Confirm', cancelButton='Confirm', dismissString='No')

def transfer_normals_to_object_function(source_mesh, target_mesh):
	cmds.undoInfo(openChunk = True)
	# Convert to dgpa
	dgpa_source = om.MDagPath.getAPathTo(om.MSelectionList().add(source_mesh).getDependNode(0))
	dgpa_target = om.MDagPath.getAPathTo(om.MSelectionList().add(target_mesh).getDependNode(0))

	# Get Mfn Source
	fn_mesh_source = om.MFnMesh(dgpa_source)
	fn_mesh_target = om.MFnMesh(dgpa_target)

	# Get Vertices Target and check if we have any face normal that closet to target vert
	vertices_target = om.MItMeshVertex(dgpa_target)
	vertex_normal_dict = {}

	while not vertices_target.isDone():
		v_id = vertices_target.index()
		pos = vertices_target.position()

		return_value = fn_mesh_source.getClosestNormal(pos, space=om.MSpace.kObject)
		if return_value:
			vertex_normal_dict[str(v_id)] = return_value[0]

		try:
			vertices_target.next(True)
		except:
			vertices_target.next()

	for id, vector in vertex_normal_dict.items():
		fn_mesh_target.setVertexNormal(vector, int(id))

#endregion

#region LOCK/UNLOCK NORMAL
def get_current_selection_mode():
	selected = cmds.ls(sl=True, fl=True)
	mode = selected[0].split("[", 1)[0].rsplit(".", 1)[-1]
	if mode == 'vtx' or mode == 'f' or mode == 'vtxFace' or mode == 'e':
		return mode
	else:
		return 'obj'

def return_selection_mode(mode):
	if mode == 'vtx':
		cmds.ConvertSelectionToVertices()
	elif mode == 'vtxFace':
		cmds.ConvertSelectionToVertexFaces()
	elif mode == 'f':
		cmds.ConvertSelectionToFaces()
	elif mode == 'e':
		cmds.ConvertSelectionToEdges()

def get_soft_edges():
	cmds.ConvertSelectionToEdges()
	cmds.polySelectConstraint(disable=True)
	cmds.polySelectConstraint(m=3, t=0x8000, sm=2)
	cmds.polySelectConstraint(disable=True)

def lock_normals(*arg):
	selected_mesh = cmds.ls(long=True, selection=True)

	for e_mesh in selected_mesh:
		cmds.polyNormalPerVertex(e_mesh, freezeNormal=True)
		cmds.polyOptions(e_mesh, softEdge=True)

def lock_normals_keep_hard_soft_edges(*arg):
	mode = get_current_selection_mode()
	# Get infor selected
	selected = cmds.ls(sl=True, fl=True)
	get_soft_edges()
	soft_edges = cmds.ls(sl=True, fl=True)
	# Lock normal
	cmds.select(selected)
	if mode != 'vtxFace':
		selected_vt = cmds.ls(cmds.polyListComponentConversion(selected, tv=True), fl=True)
		for vt in selected_vt:
			if not cmds.polyNormalPerVertex(vt, q=True, al=True)[0]:
				cmds.polyNormalPerVertex(vt, freezeNormal=True)
	else:
		selected_vtf = cmds.ls(cmds.polyListComponentConversion(selected, tvf=True), fl=True)
		for vtf in selected_vtf:
			cmds.polyNormalPerVertex(vtf, freezeNormal=True)

	# Set soft edge
	cmds.select(soft_edges)
	cmds.polySoftEdge(soft_edges, ch=True, angle=180)
	# Reset select
	return_selection_mode(mode)
	cmds.select(selected)

def unlock_normals(*arg):
	selected = cmds.ls(sl=True, fl=True)
	selected_object = get_selected_object()
	if len(selected[0].split(".")) > 1:
		selected_vt = cmds.ls(cmds.polyListComponentConversion(selected, tvf=True), fl=True)
		cmds.polyNormalPerVertex(selected_vt, unFreezeNormal=True)
	else:
		# Get soft edges
		get_soft_edges()
		soft_edges = cmds.ls(sl=True, fl=True)

		# Unlock normal
		cmds.select(selected)
		selected_vt = cmds.ls(cmds.polyListComponentConversion(selected, tvf=True), fl=True)
		cmds.polyNormalPerVertex(selected_vt, unFreezeNormal=True)

		# Set soft edge
		cmds.select(soft_edges)
		cmds.polySoftEdge(soft_edges, ch=True, angle=180)
		
		# Reset select
		cmds.ConvertSelectionToVertices()
		cmds.select(d=True)

def locked_normals_to_hard_soft_edges(*arg):
	import lockNormals_toHS as lockNormals_toHS
	reload(lockNormals_toHS)

def lock_follow_small_face(*arg):
	normal_mel_port.lock_edge_normals_by_related_face_areas(0)

def lock_follow_large_face(*arg):
	normal_mel_port.lock_edge_normals_by_related_face_areas(1)

def smooth_bevelled_faces(*arg):
	normal_mel_port.smooth_bevel(0)

def smooth_flatten_faces(*arg):
	normal_mel_port.smooth_faces()

def transfer_normal(*arg):
	normal_mel_port.transfer_normal()

def lock_face_90_angle(*arg):
	mode = get_current_selection_mode()
	current_object = cmds.ls(sl=True, fl=True)[0].rsplit("[", 1)[0].rsplit(".", 1)[0]

	# Get border edges
	selected_faces = cmds.ls(sl=True, fl=True)

	cmds.ConvertSelectionToEdgePerimeter()
	border_edges = cmds.ls(sl=True, fl=True)

	# Get hard edges
	cmds.polySelectConstraint(disable=True)
	cmds.polySelectConstraint(m=3, t=0x8000, sm=1)
	hard_edges = cmds.ls(sl=True, fl=True)
	cmds.polySelectConstraint(disable=True)

	# Get soft border edges
	soft_border_edges = list(set(border_edges) - set(hard_edges))
	soft_border_edge_num = len(soft_border_edges)

	# Get side vertices
	side_vertices = []

	soft_border_vertices = cmds.ls(cmds.polyListComponentConversion(soft_border_edges, tv=True), fl=True)

	for v in soft_border_vertices:
		edges = cmds.ls(cmds.polyListComponentConversion(v, fv=True, te=True), fl=True)
		edge_in_list_num = len(list(set(soft_border_edges) - set(edges)))
		if edge_in_list_num == soft_border_edge_num - 1:
			side_vertices.append(v)

	inside_vertices = list(set(soft_border_vertices) - set(side_vertices))

	# Get vertex faces
	selected_edge_vertex_faces = cmds.ls(cmds.polyListComponentConversion(soft_border_edges, tvf=True), fl=True)
	selected_vertices_vertex_faces = cmds.ls(cmds.polyListComponentConversion(inside_vertices, tvf=True), fl=True)

	hard_edge_vertex_faces = cmds.ls(cmds.polyListComponentConversion(selected_faces, tvf=True), fl=True)

	selected_vertex_faces = list(set(selected_edge_vertex_faces + selected_vertices_vertex_faces + hard_edge_vertex_faces))

	# Use the face normal directly so clone topology cannot change the lock direction.
	face_normal_info = cmds.polyInfo(selected_faces[0], fn=True) or []
	if not face_normal_info:
		cmds.warning('Unable to determine the selected face normal.')
		cmds.select(selected_faces)
		return
	face_normal = [float(value) for value in face_normal_info[0].split()[-3:]]

	# Apply true normal to all vertex faces
	cmds.select(selected_vertex_faces)
	get_soft_edges()
	soft_edges = cmds.ls(sl=True, fl=True)
	cmds.select(selected_vertex_faces)
	for vertex_face in selected_vertex_faces:
		cmds.polyNormalPerVertex(vertex_face, xyz=face_normal)
	if soft_edges:
		cmds.select(soft_edges)
		cmds.polySoftEdge(soft_edges, ch=True, angle=180)

	# Soft edge
	cmds.select(selected_faces)
	cmds.ConvertSelectionToContainedEdges()
	contained_edges = cmds.ls(sl=True, fl=True)
	
	# Check contained_edges
	if selected_faces == contained_edges:
		contained_edges = []
	final_edges = contained_edges + cmds.ls(cmds.polyListComponentConversion(inside_vertices, te=True), fl=True)
	final_edges = list(set(final_edges) - set(hard_edges))
	cmds.select(final_edges)
	cmds.polySoftEdge(final_edges, ch=True, angle=180)
	if len(soft_border_edges) != 0:
		cmds.polySoftEdge(soft_border_edges, ch=True, angle=180)

	# Return Selection
	cmds.select(current_object)
	return_selection_mode(mode)
	cmds.select(selected_faces)

def lock_hard_face(*arg):
	cmds.polySetToFaceNormal()
	cmds.ConvertSelectionToVertexFaces()
	lock_normals()
	cmds.ConvertSelectionToFaces()


#endregion

#region CONNECT NORMAL

def connect_with_follow(*arg):
	sel = cmds.ls(sl=True, fl=True, l=True)
	storeVertex = []
	newVertex = []

	for edge in sel:
		converVertex = cmds.polyListComponentConversion(edge, fromEdge=True, toVertex=True)
		cmds.select(converVertex)
		converVertex = cmds.ls(sl=True, fl=True, l=True)
		storeVertex.append(converVertex)
	
	edgeConnection = cmds.polyConnectComponents(sel, ch=True, insertWithEdgeFlow=True, adjustEdgeFlow=True)
	for vertex in storeVertex:
		cmds.select(vertex)
		sel_ver = cmds.ls(sl=True, fl=True, l=True)
		firstIndex = sel_ver[0][(sel_ver[0].index("[")+1):-1]
		secondIndex = sel_ver[1][(sel_ver[1].index("[")+1):-1]
		cmds.polySelect(shortestEdgePath=[int(firstIndex),int(secondIndex)])
		converVertex = cmds.polyListComponentConversion(fromEdge=True, toVertex=True)
		cmds.select(converVertex)
		converVertex = cmds.ls(sl=True, fl=True, l=True)
		newVertex.extend([i for i in converVertex if i not in sel_ver])
		cmds.select(converVertex)
		normal_mel_port.paste_vertex_normals_three_vertices()

	cmds.select(newVertex)
	cmds.ConvertSelectionToContainedEdges()
	cmds.polySoftEdge(ch=True, a=180)

def connect_without_follow(*arg):
	sel = cmds.ls(sl=True, fl=True, l=True)
	storeVertex = []
	newVertex = []

	for edge in sel:
		converVertex = cmds.polyListComponentConversion(edge, fromEdge=True, toVertex=True)
		cmds.select(converVertex)
		converVertex = cmds.ls(sl=True, fl=True, l=True)
		storeVertex.append(converVertex)
	
	edgeConnection = cmds.polyConnectComponents(sel, ch=True, insertWithEdgeFlow=False, adjustEdgeFlow=True)
	for vertex in storeVertex:
		cmds.select(vertex)
		sel_ver = cmds.ls(sl=True, fl=True, l=True)
		firstIndex = sel_ver[0][(sel_ver[0].index("[")+1):-1]
		secondIndex = sel_ver[1][(sel_ver[1].index("[")+1):-1]
		cmds.polySelect(shortestEdgePath=[int(firstIndex),int(secondIndex)])
		converVertex = cmds.polyListComponentConversion(fromEdge=True, toVertex=True)
		cmds.select(converVertex)
		converVertex = cmds.ls(sl=True, fl=True, l=True)
		newVertex.extend([i for i in converVertex if i not in sel_ver])
		cmds.select(converVertex)
		normal_mel_port.paste_vertex_normals_three_vertices()

	cmds.select(newVertex)
	cmds.ConvertSelectionToContainedEdges()
	cmds.polySoftEdge(ch=True, a=180)

#endregion
