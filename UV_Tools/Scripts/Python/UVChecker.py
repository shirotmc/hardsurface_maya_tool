import maya.cmds as cmds
import maya.mel as mel
import os

LOCAL_PATH = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))).replace("\\", "/")  # HSTool root (self-locating)
CHECKER_DEFAULT_NAME = "HSTool_Checker"

global texture_name

def GUI():
	if cmds.window("checker_window", ex = True):
		cmds.deleteUI("checker_window", window = True)
	cmds.window("checker_window", title = "UV Checker", rtf = True, mnb = False, mxb = False, h=40)
	
	cmds.rowColumnLayout(nc = 2, cw = [(1,130), (2,130)], adj = 2, cs = [(2,10)])
	cmds.columnLayout("checker_button_layout", columnAttach=('both', 0), rowSpacing= 5, cw=130)

	cmds.rowColumnLayout(nc = 5, cw = [(1,25), (2,25), (3,25), (4,25), (5,25)], adj = 5)
	cmds.iconTextButton("UVChecker1_button", style = "iconOnly", image1 = LOCAL_PATH + "/UV_Tools/Icons/UVChecker_1.png", c=lambda *args: assign_uv_checker(1))
	cmds.iconTextButton("UVChecker2_button", style = "iconOnly", image1 = LOCAL_PATH + "/UV_Tools/Icons/UVChecker_2.png", c=lambda *args: assign_uv_checker(2))
	cmds.iconTextButton("UVChecker3_button", style = "iconOnly", image1 = LOCAL_PATH + "/UV_Tools/Icons/UVChecker_3.png", c=lambda *args: assign_uv_checker(3))
	cmds.iconTextButton("UVChecker4_button", style = "iconOnly", image1 = LOCAL_PATH + "/UV_Tools/Icons/UVChecker_4.png", c=lambda *args: assign_uv_checker(4))
	cmds.iconTextButton("UVChecker5_button", style = "iconOnly", image1 = LOCAL_PATH + "/UV_Tools/Icons/UVChecker_5.png", c=lambda *args: assign_uv_checker(5))
	cmds.setParent("..")

	cmds.rowColumnLayout(nc = 5, cw = [(1,25), (2,25), (3,25), (4,25), (5,25)], adj = 5)
	cmds.iconTextButton("UVChecker6_button", style = "iconOnly", image1 = LOCAL_PATH + "/UV_Tools/Icons/UVChecker_6.png", c=lambda *args: assign_uv_checker(6))
	cmds.iconTextButton("UVChecker7_button", style = "iconOnly", image1 = LOCAL_PATH + "/UV_Tools/Icons/UVChecker_7.png", c=lambda *args: assign_uv_checker(7))
	cmds.iconTextButton("UVChecker8_button", style = "iconOnly", image1 = LOCAL_PATH + "/UV_Tools/Icons/UVChecker_8.png", c=lambda *args: assign_uv_checker(8))
	cmds.iconTextButton("UVChecker9_button", style = "iconOnly", image1 = LOCAL_PATH + "/UV_Tools/Icons/UVChecker_9.png", c=lambda *args: assign_uv_checker(9))
	cmds.iconTextButton("UVChecker10_button", style = "iconOnly", image1 = LOCAL_PATH + "/UV_Tools/Icons/UVChecker_10.png", c=lambda *args: assign_uv_checker(10))
	cmds.setParent("..")

	cmds.rowColumnLayout(nc = 5, cw = [(1,25), (2,25), (3,25), (4,25), (5,25)], adj = 5)
	cmds.iconTextButton("UVChecker11_button", style = "iconOnly", image1 = LOCAL_PATH + "/UV_Tools/Icons/UVChecker_11.png", c=lambda *args: assign_uv_checker(11))
	cmds.iconTextButton("UVChecker12_button", style = "iconOnly", image1 = LOCAL_PATH + "/UV_Tools/Icons/UVChecker_12.png", c=lambda *args: assign_uv_checker(12))
	cmds.iconTextButton("UVChecker13_button", style = "iconOnly", image1 = LOCAL_PATH + "/UV_Tools/Icons/UVChecker_13.png", c=lambda *args: assign_uv_checker(13))
	cmds.iconTextButton("UVChecker14_button", style = "iconOnly", image1 = LOCAL_PATH + "/UV_Tools/Icons/UVChecker_14.png", c=lambda *args: assign_uv_checker(14))
	cmds.iconTextButton("UVChecker15_button", style = "iconOnly", image1 = LOCAL_PATH + "/UV_Tools/Icons/UVChecker_15.png", c=lambda *args: assign_uv_checker(15))
	cmds.setParent("..")

	cmds.setParent("..")

	cmds.columnLayout("main_button_layout", columnAttach=('both', 0), rowSpacing= 5, cw=130)
	cmds.button("Delete Checker", bgc =(0.8, 0.8, 0.8), c=delete_checker_material)
	cmds.intField("checker_tiling_if", v=1, min=1, max=100, cc = uv_checker_intfield_changed)
	cmds.intSlider("checker_tiling_isl", v=1, min=1, max=100, cc = uv_checker_intslider_changed)
	cmds.setParent("..")

	cmds.setParent("..")

	cmds.window("checker_window", e=True, s=True)
	cmds.showWindow("checker_window")

def uv_checker_intfield_changed(*arg):
	tiling_value =  cmds.intField("checker_tiling_if", q=True, v=True)
	cmds.intSlider("checker_tiling_isl", e=True, v=tiling_value)
	tiling_checker(tiling_value)

def uv_checker_intslider_changed(*arg):
	tiling_value =  cmds.intSlider("checker_tiling_isl", q=True, v=True)
	cmds.intField("checker_tiling_if", e=True, v=tiling_value)
	tiling_checker(tiling_value)

def assign_checker_texture_node_to_material(shader_name, checker_number):
	# Clear data
	delete_checker_material()

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
	checker_path = LOCAL_PATH + "/UV_Tools/Checkers/UVChecker_" + str(checker_number) + ".png"
	cmds.setAttr(file_node + ".fileTextureName", checker_path, type="string" )
	cmds.setAttr(file_node + ".colorSpace", "Raw", type="string")

	outputs = cmds.listConnections(shader_name + '.color', source=True, destination=True, plugs=True)
	if outputs:
		for o in outputs:
			if '.outColor' in o:
				cmds.disconnectAttr(o, shader_name + '.color')
				break

	# Connect file node to material node 
	cmds.connectAttr(file_node + '.outColor', shader_name + '.color')
	cmds.setAttr(file_node + ".fileTextureName", checker_path, type="string" )

	return file_node, texture_name

def delete_unused_node(*arg):
	mel.eval('hyperShadePanelMenuCommand("hyperShadePanel1", "deleteUnusedNodes");')

def get_material_from_objects(*arg):
	shapes_sel = cmds.ls(dagObjects=True, objectsOnly=True, shapes=True, selection=True) # get shapes of selection
	shaders_list = []
	if shapes_sel != []:
		shading_group = cmds.listConnections(shapes_sel, type='shadingEngine') # get shading groups from shapes
		shaders_list = set(cmds.ls(cmds.listConnections(shading_group), materials=True)) # get the shaders  
	return list(shaders_list)

def assign_uv_checker(checker_number):
	global texture_name
	selected_objects = cmds.ls(sl=True, l=True)
	# 0 object selection
	if len(selected_objects) == 0:
		cmds.confirmDialog(icn="information", m = "Please select mesh to assign checker!")
		return False
	else:
		# >1 object
		materials = get_material_from_objects()
		delete_unused_node()
		#file_node, texture_name = create_checker_texture_node(checker_number)
		for m in materials:
			assign_checker_texture_node_to_material(m, checker_number)

def tiling_checker(tiling_number):
	materials = get_material_from_objects()
	if len(materials) == 0:
		cmds.confirmDialog(icn="information", m = "Please select mesh to tiling checker!")
		return False
	for m in materials:
		file_node = cmds.listConnections(m + '.color', source=True, destination=True, plugs=True)[0]
		texture_node = ''
		for node in cmds.listConnections(file_node.rsplit(".", 1)[0]):
			if 'place2dTexture' in node:
				texture_node = node
				break
		cmds.setAttr(texture_node +".repeatU", tiling_number)
		cmds.setAttr(texture_node + ".repeatV", tiling_number)
	return True

def delete_checker_material(*arg):
	materials = get_material_from_objects()
	for shader_name in materials:
		outputs = cmds.listConnections(shader_name + '.color', source=True, destination=True, plugs=True)
		if outputs:
			for o in outputs:
				if '.outColor' in o:
					cmds.disconnectAttr(o, shader_name + '.color')
					break

GUI()