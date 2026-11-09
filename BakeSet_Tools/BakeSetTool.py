import maya.cmds as cmds
import maya.mel as mel
import math
import os
import site

#-------------------------------------------Support Function----------------------------------------------------
LOCAL_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace("\\", "/")  # HSTool root (self-locating)

site.addsitedir(LOCAL_PATH + "/Model_Tools/Scripts/Python")
import combine_detach_clone_port

highpoly_define_name = "HSTool_High"

def combine_object(selected_objects):
	cmds.select(selected_objects)
	if len(selected_objects) > 1:
		combine_detach_clone_port.combine_objects()
	return cmds.ls(sl=True)

def check_highpoly_name(name):
	split_list = name.rsplit("|", 1)[-1].rsplit("_", 1)
	if split_list[0] == highpoly_define_name and split_list[-1].isnumeric():
		return True
	else:
		return False

def export_fbx_for_baking(object_name, fbx_path):
	# Lock Normal
	if cmds.checkBox('bakeset_lock_normal_cb', q=True, v=True):
		mel.eval('FBXProperty Export|IncludeGrp|Geometry|TangentsandBinormals -v true')
	else:
		mel.eval('FBXProperty Export|IncludeGrp|Geometry|TangentsandBinormals -v false')

	# General Setting
	mel.eval('FBXProperty Export|IncludeGrp|Geometry|expHardEdges -v false')
	mel.eval('FBXProperty Export|IncludeGrp|Geometry|SelectionSet -v false')
	mel.eval('FBXProperty Export|IncludeGrp|Geometry|Instances -v false')
	mel.eval('FBXExportReferencedAssetsContent -v false')

	if "high" in object_name.rsplit('_', 1)[-1].lower():
		# Highpoly
		mel.eval('FBXProperty Export|IncludeGrp|Geometry|SmoothingGroups -v false')
		mel.eval('FBXProperty Export|IncludeGrp|Geometry|SmoothMesh -v false')
		mel.eval('FBXExportInAscii -v false')
		mel.eval('FBXExportTriangulate -v false')
	else: 
		# Lowpoly
		mel.eval('FBXProperty Export|IncludeGrp|Geometry|SmoothingGroups -v true')
		mel.eval('FBXProperty Export|IncludeGrp|Geometry|SmoothMesh -v true')
		mel.eval('FBXExportInAscii -v true')
		mel.eval('FBXExportTriangulate -v true')
	
	mel.eval('FBXExport -f "' + fbx_path + '/' + object_name + '.fbx' + '" -s')

def get_distance(a_pos, b_pos):
	distance = math.sqrt(pow((a_pos[0]-b_pos[0]),2) + pow((a_pos[1]-b_pos[1]),2) + pow((a_pos[2]-b_pos[2]),2))
	return distance

def check_intersection(object_a, object_b):
	obj_a = cmds.duplicate(object_a)
	obj_b = cmds.duplicate(object_b)
	results = cmds.polyCBoolOp(obj_a[0], obj_b[0], useThresholds=True, op=3)
	num_intersect_vertex = cmds.polyEvaluate(results[0], v=True)
	
	cmds.delete(results)
	cmds.delete(obj_a[0])
	cmds.delete(obj_b[0])

	if num_intersect_vertex != 0:
		return True
	else:
		return False

def check_overlap(object_a, object_b):
	bb_a = cmds.exactWorldBoundingBox(object_a)
	a_min = [bb_a[0], bb_a[1], bb_a[2]]
	a_max = [bb_a[3], bb_a[4], bb_a[5]]

	bb_b = cmds.exactWorldBoundingBox(object_b)
	b_min = [bb_b[0], bb_b[1], bb_b[2]]
	b_max = [bb_b[3], bb_b[4], bb_b[5]]

	diagonal_line_length = get_distance(b_min, b_max)
	min_distance = diagonal_line_length * cmds.floatField('bakeset_auto_threshold_ff', q=True, v=True)
	if get_distance(a_min, b_min) >= min_distance or get_distance(a_max, b_max) >= min_distance:
		return False
	else:
		return True
#----------------------------------------------------Function----------------------------------------------------
def get_material_from_objects(*arg):
	shapes_sel = cmds.ls(dagObjects=True, objectsOnly=True, shapes=True, selection=True) # get shapes of selection
	shaders_list = []
	if shapes_sel == []:
		cmds.warning('Nothing selected!')
	if shapes_sel != []:
		shading_group = cmds.listConnections(shapes_sel, type='shadingEngine') # get shading groups from shapes
		shaders_list = set(cmds.ls(cmds.listConnections(shading_group), materials=True)) # get the shaders  
	return list(shaders_list)

def delete_unused_node(*arg):
	mel.eval('hyperShadePanelMenuCommand("hyperShadePanel1", "deleteUnusedNodes");')

#region Normal Map
def assign_normal_map(*arg):
	selected_objects = cmds.ls(sl=True, l=True)
	normal_path = cmds.textField('normal_map_path_tf', q=True, tx= True)
	# 0 object selection
	if len(selected_objects) == 0:
		cmds.warning("Please select mesh to assign normal!")
		return False
	else:
		# >1 object
		delete_unused_node()
		materials = get_material_from_objects()
		for m in materials:
			assign_normal_node_to_material(m, normal_path)
	cmds.select(selected_objects)

def clear_normal_map(*arg):
	materials = get_material_from_objects()
	for shader_name in materials:
		outputs = cmds.listConnections(shader_name + '.normalCamera', source=True, destination=True, plugs=True)
		if outputs:
			for o in outputs:
				if '.outNormal' in o:
					cmds.disconnectAttr(o, shader_name + '.normalCamera')
					break
	delete_unused_node()

def get_normal_map_path(*arg):
	multipleFilters = "Texture Files (*.psd *.tga *.png);;All Files (*.*)"
	current_file_path = cmds.file(q= True, loc = True)
	if current_file_path != "unknown":
		default_path = current_file_path.rsplit("/", 1)[0]
		new_dir = cmds.fileDialog2(dir = default_path, cap = 'Choose Normal Map Path!', fm=1, ff=multipleFilters)
	else:
		new_dir = cmds.fileDialog2(cap = 'Choose Normal Map Path!', fm=1, ff=multipleFilters)
	cmds.textField('normal_map_path_tf', e=True, tx= new_dir[0])
	return True

def assign_normal_node_to_material(shader_name, normal_path):
	# Clear data
	clear_normal_map()

	# Create bump2d node
	bumpNode = cmds.shadingNode('bump2d', asUtility=True)
	cmds.setAttr(bumpNode + '.bumpInterp', 1)
	cmds.connectAttr(bumpNode + '.outNormal', shader_name + '.normalCamera')

	# Create file node
	file_node = cmds.shadingNode("file", asTexture=True, isColorManaged=True )
	texture_name = cmds.shadingNode( "place2dTexture", asUtility=True )
	cmds.connectAttr(texture_name + ".coverage", file_node + ".coverage", force=True )
	cmds.connectAttr(texture_name + ".translateFrame", file_node + ".translateFrame", force=True )
	cmds.connectAttr(texture_name + ".rotateFrame", file_node + ".rotateFrame", force=True )
	cmds.connectAttr(texture_name + ".mirrorU", file_node + ".mirrorU", force=True )
	cmds.connectAttr(texture_name + ".mirrorV", file_node + ".mirrorV", force=True )
	cmds.connectAttr(texture_name + ".stagger", file_node + ".stagger", force=True )
	cmds.connectAttr(texture_name + ".wrapU", file_node + ".wrapU", force=True )
	cmds.connectAttr(texture_name + ".wrapV", file_node + ".wrapV", force=True )
	cmds.connectAttr(texture_name + ".repeatUV", file_node + ".repeatUV", force=True )
	cmds.connectAttr(texture_name + ".offset", file_node + ".offset", force=True )
	cmds.connectAttr(texture_name + ".rotateUV", file_node + ".rotateUV", force=True )
	cmds.connectAttr(texture_name + ".noiseUV", file_node + ".noiseUV", force=True )
	cmds.connectAttr(texture_name + ".vertexUvOne", file_node + ".vertexUvOne", force=True )
	cmds.connectAttr(texture_name + ".vertexUvTwo", file_node + ".vertexUvTwo", force=True )
	cmds.connectAttr(texture_name + ".vertexUvThree", file_node + ".vertexUvThree", force=True )
	cmds.connectAttr(texture_name + ".vertexCameraOne", file_node + ".vertexCameraOne", force=True )
	cmds.connectAttr(texture_name + ".outUV", file_node + ".uv", force=True )
	cmds.connectAttr(texture_name + ".outUvFilterSize", file_node + ".uvFilterSize", force=True )

	# Set path for file node
	cmds.setAttr(file_node + ".fileTextureName", normal_path, type="string" )
	cmds.setAttr(file_node + ".colorSpace", "Raw", type="string")

	# Connect file node to bump2d node
	cmds.connectAttr(file_node + '.outAlpha', bumpNode+'.bumpValue')

	return file_node, texture_name

#endregion

#region AO Map
def assign_ao_map(*arg):
	selected_objects = cmds.ls(sl=True, l=True)
	ao_path = cmds.textField('ao_map_path_tf', q=True, tx= True)
	# 0 object selection
	if len(selected_objects) == 0:
		cmds.warning("Please select mesh to assign AO Map!")
		return False
	else:
		# >1 object
		delete_unused_node()
		materials = get_material_from_objects()
		for m in materials:
			assign_ao_node_to_material(m, ao_path)
	cmds.select(selected_objects)

def clear_ao_map(*arg):
	materials = get_material_from_objects()
	for shader_name in materials:
		outputs = cmds.listConnections(shader_name + '.ambientColor', source=True, destination=True, plugs=True)
		if outputs:
			for o in outputs:
				if '.outColor' in o:
					cmds.disconnectAttr(o, shader_name + '.ambientColor')
					break
	delete_unused_node()

def get_ao_map_path(*arg):
	multipleFilters = "Texture Files (*.psd *.tga *.png);;All Files (*.*)"
	current_file_path = cmds.file(q= True, loc = True)
	if current_file_path != "unknown":
		default_path = current_file_path.rsplit("/", 1)[0]
		new_dir = cmds.fileDialog2(dir = default_path, cap = 'Choose ao Map Path!', fm=1, ff=multipleFilters)
	else:
		new_dir = cmds.fileDialog2(cap = 'Choose ao Map Path!', fm=1, ff=multipleFilters)
	cmds.textField('ao_map_path_tf', e=True, tx= new_dir[0])
	return True

def assign_ao_node_to_material(shader_name, ao_path):
	# Clear data
	clear_ao_map()

	# Create file node
	file_node = cmds.shadingNode("file", asTexture=True, isColorManaged=True )
	texture_name = cmds.shadingNode( "place2dTexture", asUtility=True )
	cmds.connectAttr(texture_name + ".coverage", file_node + ".coverage", force=True )
	cmds.connectAttr(texture_name + ".translateFrame", file_node + ".translateFrame", force=True )
	cmds.connectAttr(texture_name + ".rotateFrame", file_node + ".rotateFrame", force=True )
	cmds.connectAttr(texture_name + ".mirrorU", file_node + ".mirrorU", force=True )
	cmds.connectAttr(texture_name + ".mirrorV", file_node + ".mirrorV", force=True )
	cmds.connectAttr(texture_name + ".stagger", file_node + ".stagger", force=True )
	cmds.connectAttr(texture_name + ".wrapU", file_node + ".wrapU", force=True )
	cmds.connectAttr(texture_name + ".wrapV", file_node + ".wrapV", force=True )
	cmds.connectAttr(texture_name + ".repeatUV", file_node + ".repeatUV", force=True )
	cmds.connectAttr(texture_name + ".offset", file_node + ".offset", force=True )
	cmds.connectAttr(texture_name + ".rotateUV", file_node + ".rotateUV", force=True )
	cmds.connectAttr(texture_name + ".noiseUV", file_node + ".noiseUV", force=True )
	cmds.connectAttr(texture_name + ".vertexUvOne", file_node + ".vertexUvOne", force=True )
	cmds.connectAttr(texture_name + ".vertexUvTwo", file_node + ".vertexUvTwo", force=True )
	cmds.connectAttr(texture_name + ".vertexUvThree", file_node + ".vertexUvThree", force=True )
	cmds.connectAttr(texture_name + ".vertexCameraOne", file_node + ".vertexCameraOne", force=True )
	cmds.connectAttr(texture_name + ".outUV", file_node + ".uv", force=True )
	cmds.connectAttr(texture_name + ".outUvFilterSize", file_node + ".uvFilterSize", force=True )

	# Set path for file node
	cmds.setAttr(file_node + ".fileTextureName", ao_path, type="string" )
	cmds.setAttr(file_node + ".colorSpace", "Raw", type="string")


	# Connect file node to material node 
	cmds.connectAttr(file_node + '.outColor', shader_name + '.ambientColor')
	cmds.setAttr(file_node + ".fileTextureName", ao_path, type="string" )

	return file_node, texture_name

#endregion

#region BakeSet
def expand_all_bakeset(*arg):
	"""Expand all groups in Maya"""
	p = cmds.getPanel(type='outlinerPanel')[0]
	cmds.outlinerEditor(p, e=True, eai=True)

def collapse_all_bakeset(*arg):
	"""Collapse all groups in Maya."""
	p = cmds.getPanel(type='outlinerPanel')[0]
	cmds.outlinerEditor(p, e=True, eai=False)

def auto_fill_export_path(*arg):
	current_file_path = cmds.file(q= True, loc = True)
	if current_file_path != "unknown":
		current_folder_path = current_file_path.rsplit("/", 1)[0] + "/FBX_" + current_file_path.rsplit("/", 1)[-1].rsplit(".", 1)[0]
		return current_folder_path
	return ""

def get_export_fbx_path(*arg):
	current_file_path = cmds.file(q= True, loc = True)
	if current_file_path != "unknown":
		default_path = current_file_path.rsplit("/", 1)[0]
		new_dir = cmds.fileDialog2(dir = default_path, cap = 'Choose Export FBX Path!', fm=3)
	else:
		default_path = "D:/"
		new_dir = cmds.fileDialog2(dir = default_path, cap = 'Choose Export FBX Path!', fm=3)
	cmds.textField('export_fbx_path_tf', e=True, tx= new_dir[0])
	return True

def set_right_handed(*arg):
	obj = cmds.ls(sl=True, l=True)
	for s in obj:
		cmds.setAttr(s+'.tangentSpace', 0)

def set_left_handed(*arg):
	obj = cmds.ls(sl=True, l=True)
	for s in obj:
		cmds.setAttr(s+'.tangentSpace', 2)

def rename_highpoly(*arg):
	selected_transform_list = cmds.listRelatives(cmds.ls(sl=True, type = 'mesh', dag=True, ni=True, l=True), parent=True, f=True)
	if len(selected_transform_list) == 0:
		cmds.warning('Please select mesh for rename!')
		return False
	
	i = 1
	new_name = highpoly_define_name + '_1'
	for transform in selected_transform_list:
		# if check_highpoly_name(transform):
		# 	continue
		transform_list = [str(tr.rsplit("|", 1)[-1]) for tr in cmds.listRelatives(cmds.ls(sl=True, type = 'mesh', dag=True, ni=True, l=True), parent=True, f=True)]
		while new_name in transform_list:
			i += 1
			new_name = highpoly_define_name + '_' + str(i)
		cmds.rename(transform, new_name) 

	cmds.warning('Rename Highpoly: Done!')
	return True

def create_bakeset_group_auto_v2(*arg):
	# Unparent mesh list
	cmds.Unparent(cmds.ls(sl=True, type = 'mesh', dag=True, ni=True), s=True, w = True)
	# Delete empty group
	mel.eval('source cleanUpScene;')
	mel.eval('deleteEmptyGroups;')
	
	selected_transform_list = cmds.listRelatives(cmds.ls(sl=True, type = 'mesh', dag=True, ni=True, l=True), parent=True, f=True)

	# Get highpoly+lowpoly list
	highpoly_list = []
	lowpoly_list = []
	for obj in selected_transform_list:
		if check_highpoly_name(obj):
			highpoly_list.append(obj)
		else:
			lowpoly_list.append(obj)

	# Get bakeset group list
	bakeset_group_list = []
	## Get highpoly bakeset group list
	checked_highpoly_list = []
	for i in range(0, len(highpoly_list)):
		bakeset_highpoly_list = []
		if highpoly_list[i] not in checked_highpoly_list:
			checked_highpoly_list.append(highpoly_list[i])
			bakeset_highpoly_list.append(highpoly_list[i])
			for j in range(i+1, len(highpoly_list)):
				if highpoly_list[j] not in checked_highpoly_list:
					for k in range(0, len(bakeset_highpoly_list)):
						if check_intersection(bakeset_highpoly_list[k], highpoly_list[j]):
							break
						elif k == len(bakeset_highpoly_list) - 1:
							checked_highpoly_list.append(highpoly_list[j])
							bakeset_highpoly_list.append(highpoly_list[j])
			bakeset_group_list.append([bakeset_highpoly_list])

	# Get low bakeset group list
	checked_lowpoly_list = []

	for i in range(0, len(bakeset_group_list)):
		bakeset_lowpoly_list = []
		for j in range(0, len(bakeset_group_list[i][0])):
			for k in range(0, len(lowpoly_list)):
				if (lowpoly_list[k] not in checked_lowpoly_list) and check_overlap(bakeset_group_list[i][0][j], lowpoly_list[k]):
					checked_lowpoly_list.append(lowpoly_list[k])
					bakeset_lowpoly_list.append(lowpoly_list[k])
		bakeset_group_list[i].append(bakeset_lowpoly_list)

	for i in range(0, len(bakeset_group_list)):
		bakeset_name = cmds.textField('bakeset_name_tf', q=True, tx=True) + str(i+1)
		high_group = cmds.group(bakeset_group_list[i][0], n="High", w=True)
		if bakeset_group_list[i][1]:
			low_group = cmds.group(bakeset_group_list[i][1], n="Low", w=True)
		else:
			low_group = cmds.group(n="Low", w=True, em=True)
		cmds.group(high_group, low_group, n=bakeset_name, w=True)
		cmds.hide(bakeset_name)
	
	# Delete empty group
	mel.eval('source cleanUpScene;')
	mel.eval('deleteEmptyGroups;')

def create_bakeset_group_auto(*arg):
	# Unparent mesh list
	cmds.Unparent(cmds.ls(sl=True, type = 'mesh', dag=True, ni=True), s=True, w = True)
	# Delete empty group
	mel.eval('source cleanUpScene;')
	mel.eval('deleteEmptyGroups;')

	#Create BakeSet Group
	object_pair_list = []
	checked_object_list = []
	selected_mesh_list = cmds.ls(sl=True, type = 'mesh', dag=True, ni=True, l=True)
	for i in range(0, len(selected_mesh_list)):
		for j in range(i+1, len(selected_mesh_list)):
			if i not in checked_object_list:
				if check_overlap(selected_mesh_list[i], selected_mesh_list[j]):
					object_pair_list.append([selected_mesh_list[i], selected_mesh_list[j]])
					checked_object_list.append(j)
					break
	for obj_pair in object_pair_list:
		transform_list = cmds.listRelatives(obj_pair, parent=True, f=True)
		if check_highpoly_name(transform_list[0]):
			highpoly_mesh = transform_list[0]
			lowpoly_mesh = transform_list[1]
		elif check_highpoly_name(transform_list[1]):
			highpoly_mesh = transform_list[1]
			lowpoly_mesh = transform_list[0]

		bakeset_name = cmds.textField('bakeset_name_tf', q=True, tx=True) + "1"
		high_group = cmds.group(highpoly_mesh, n="High")
		low_group = cmds.group(lowpoly_mesh, n="Low")
		bakeset_name = cmds.group(high_group, low_group, n=bakeset_name, w=True)

		new_highpoly_mesh_name = '|' + bakeset_name + '|High|' + highpoly_mesh.rsplit('|', 1)[-1]
		new_lowpoly_mesh_name = '|' + bakeset_name + '|Low|' + lowpoly_mesh.rsplit('|', 1)[-1]

		highpoly_mesh = cmds.rename(new_highpoly_mesh_name, bakeset_name + "_High")
		lowpoly_mesh = cmds.rename(new_lowpoly_mesh_name, bakeset_name + "_Low")
		cmds.hide(bakeset_name)
		
	# Delete empty group
	mel.eval('source cleanUpScene;')
	mel.eval('deleteEmptyGroups;')

def create_bakeset_group_manual(*arg):
	# Unparent mesh list
	cmds.Unparent(cmds.ls(sl=True, type = 'mesh', dag=True, ni=True), s=True, w = True)
	# Delete empty group
	mel.eval('source cleanUpScene;')
	mel.eval('deleteEmptyGroups;')

	# Create BakeSet Group
	transform_list = cmds.listRelatives(cmds.ls(sl=True, type = 'mesh', dag=True, ni=True, l=True), parent=True, f=True)

	# Get lowpoly & highpoly mesh
	highpoly_mesh_list = []
	lowpoly_mesh_list = []
	for i in range(0, len(transform_list)):
		if check_highpoly_name(transform_list[i]):
			highpoly_mesh_list.append(transform_list[i])
		else:
			lowpoly_mesh_list.append(transform_list[i])


	highpoly_mesh = combine_object(highpoly_mesh_list)[0]

	lowpoly_mesh = combine_object(lowpoly_mesh_list)[0]

	bakeset_name = cmds.textField('bakeset_name_tf', q=True, tx=True) + "1"
	high_group = cmds.group(highpoly_mesh, n="High")
	low_group = cmds.group(lowpoly_mesh, n="Low")
	bakeset_name = cmds.group(high_group, low_group, n=bakeset_name, w=True)

	new_highpoly_mesh_name = '|' + bakeset_name + '|High|' + highpoly_mesh.rsplit('|', 1)[-1]
	new_lowpoly_mesh_name = '|' + bakeset_name + '|Low|' + lowpoly_mesh.rsplit('|', 1)[-1]

	highpoly_mesh = cmds.rename(new_highpoly_mesh_name, bakeset_name + "_High")
	lowpoly_mesh = cmds.rename(new_lowpoly_mesh_name, bakeset_name + "_Low")
	cmds.hide(bakeset_name)

	mel.eval('source cleanUpScene;')
	mel.eval('deleteEmptyGroups;')

def create_highlow_layer(*arg):
	high_group = []
	low_group = []

	mesh_list = cmds.listRelatives(cmds.ls(type="mesh"), parent=True)

	for mesh in mesh_list:
		if "high" in mesh.rsplit("|", 1)[-1].rsplit('_', 1)[-1].lower():
			high_group.append(mesh)
		elif "low" in mesh.rsplit("|", 1)[-1].rsplit('_', 1)[-1].lower():
			low_group.append(mesh)
	
	bakeset_name = cmds.textField('bakeset_name_tf', q=True, tx=True)
	bakeset_list = cmds.ls(bakeset_name + '*', type="transform")
	cmds.showHidden(bakeset_list)
	# Create Highpoly Layer
	cmds.select(high_group)
	try:
		cmds.createDisplayLayer(noRecurse=True, name='_High')
	except:
		pass
	cmds.editDisplayLayerMembers('_High', high_group)

	# Create Lowpoly Layer
	cmds.select(low_group)
	try:
		cmds.createDisplayLayer(noRecurse=True, name='_Low')
	except:
		pass
	cmds.editDisplayLayerMembers('_Low', low_group)

	cmds.select(d=True)

def export_bakeset(*arg):
	file_name = cmds.file(q=True, loc=True)

	# Check open maya file
	if file_name == "unknown":
		cmds.warning('Please open maya file!')
		return False
	else:
		fbx_path = cmds.textField('export_fbx_path_tf', q=True, tx=True)
	
	# Create FBX folder
	if not os.path.exists(fbx_path):
		os.makedirs(fbx_path)
	
	# FBX Export
	cmds.select(d=True)
	bakeset_name = cmds.textField('bakeset_name_tf', q=True, tx=True)
	mesh_list = cmds.listRelatives(cmds.ls(bakeset_name + '*', type="mesh"), parent=True)
	export_mode = cmds.radioButtonGrp('export_bakeset_mode_rbg', q=True, sl=True)

	if export_mode == 2:
		# Multiple Files
		for mesh in mesh_list:
			cmds.select(mesh, r=True)
			export_fbx_for_baking(mesh, fbx_path)
	else:
		# Single Files
		low_mesh = [m for m in mesh_list if m.rsplit("_", 1)[-1].lower() == "low"]
		high_mesh = [m for m in mesh_list if m.rsplit("_", 1)[-1].lower() == "high"]
		cmds.select(low_mesh)
		export_fbx_for_baking('Object_Low', fbx_path)
		cmds.select(high_mesh)
		export_fbx_for_baking('Object_High', fbx_path)

	cmds.select(d=True)	

def export_selected_bakeset(*arg):
	file_name = cmds.file(q=True, loc=True)
	bakeset_name = cmds.textField('bakeset_name_tf', q=True, tx=True)

	# Check open maya file
	if file_name == "unknown":
		cmds.warning('Please open maya file!')
		return False
	else:
		fbx_path = cmds.textField('export_fbx_path_tf', q=True, tx=True)
	
	# Create FBX folder
	if not os.path.exists(fbx_path):
		os.makedirs(fbx_path)
	
	# FBX Export
	selected_meshes = cmds.ls(sl=True, dag=True, type='mesh', ni=True, l=True)
	mesh_list = cmds.listRelatives(selected_meshes, parent=True, f=True) or []
	mesh_list = list(dict.fromkeys(mesh_list))
	if not mesh_list:
		cmds.warning('Please select a BakeSet group or mesh to export!')
		return False
	export_mode = cmds.radioButtonGrp('export_bakeset_mode_rbg', q=True, sl=True)

	if export_mode == 2:
		# Multiple Files
		cmds.select(d=True)
		for mesh in mesh_list:
			cmds.select(mesh, r=True)
			export_fbx_for_baking(mesh.rsplit('|', 1)[-1], fbx_path)
		cmds.select(d=True)
	else:
		# Single Files
		low_list = [m for m in mesh_list if "low" in m.rsplit("_", 1)[-1].lower()]
		high_list = [m for m in mesh_list if "high" in m.rsplit("_", 1)[-1].lower()]
		cmds.select(d=True)
		cmds.select(high_list, r=True)
		export_fbx_for_baking('Object_High', fbx_path)
		cmds.select(d=True)
		cmds.select(low_list, r=True)
		export_fbx_for_baking('Object_Low', fbx_path)
		cmds.select(d=True)	

#endregion

#-------------------------------------------------------UI--------------------------------------------------------
