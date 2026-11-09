import maya.cmds as cmds
import maya.mel as mel
import maya.OpenMaya as OpenMaya

import os
import sys
import site
import subprocess
import tempfile, platform
import shutil
import subprocess
import logging
import random
import math

try:
	from importlib import reload
	import configparser as ConfigParser
except:
	import ConfigParser

LOCAL_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace("\\", "/")  # HSTool root (self-locating)

WINDOW_NAME = "uv_tools_window"
WINDOW_TITLE = "UV Tools"

site.addsitedir(LOCAL_PATH + "/UV_Tools/Scripts/Python")
import uv_mel_port
reload(uv_mel_port)

# SELECT

# tu dong chon hard edge
def selectHardEdge(*arg):
	uv_mel_port.select_hard_edge()

# tu dong chon Uv border Edge
def selectUVBorder(*arg):
	uv_mel_port.select_uv_border()

# tu dong chon Border Edge
def selectBorderEdge(*arg):
	uv_mel_port.select_border_edge()

# tu dong chon cac canh hard edge not uv border
def get_uv_borders(objects):
	# Try to get edges from provided objects
	mesh_edges = list()
	for o in objects:
		try:
			mesh_edges.extend(cmds.ls(cmds.polyListComponentConversion(o, te=True), fl=True, l=True))
		except:
			pass
	
	# Error if no valid objects were found
	if len(mesh_edges) <= 0:
		raise RuntimeError('No valid mesh objects or components were provided.')
		
	# Find and return uv border edges
	uv_border_edges = list()
	for edge in mesh_edges:  # Filter through the mesh(s) edges.
		edge_uvs = cmds.ls(cmds.polyListComponentConversion(edge, tuv=True), fl=True)
		edge_faces = cmds.ls(cmds.polyListComponentConversion(edge, tf=True), fl=True)
		if len(edge_uvs) > 2:  # If an edge has more than two uvs, it is a uv border edge.
			uv_border_edges.append(edge)
		elif len(edge_faces) < 2:  # If an edge has less than 2 faces, it is a border edge.
			uv_border_edges.append(edge)
	return (uv_border_edges)

def get_hard_edges(objects):
	# Try to get edges from provided objects
	mesh_edges = list()
	for o in objects:
		try:
			mesh_edges.extend(cmds.ls(cmds.polyListComponentConversion(o, te=True), fl=True, l=True))
		except:
			pass
	
	# Error if no valid objects were found
	if len(mesh_edges) <= 0:
		raise RuntimeError('No valid mesh objects or components were provided.')

	mel.eval("resetPolySelectConstraint();")
	cmds.polySelectConstraint(m=0, dis=True)
	cmds.polySelectConstraint(m=3, t=0x8000, sm=1)
	cmds.polySelectConstraint(m=0, dis=True)
	mel.eval("resetPolySelectConstraint();")
	hard_edges = cmds.ls(sl=True, fl=True, l=True)
	return (hard_edges)

def get_hard_edges_without_uv_border(*arg):
	selection = cmds.ls(sl=True, fl=True)
	border_uv_edges = get_uv_borders(selection)
	hard_edges = get_hard_edges(selection)
	result = list(set(hard_edges) - set(border_uv_edges))
	cmds.select(selection, r=True)
	cmds.selectMode(component=True)
	cmds.select(result)
	if len(result) > 0:
		cmds.warning("Hard Edges (Not UV Border) were selected!")
	else:
		cmds.warning("All Hard Edges are UV Border!")



# UVS UNWRAP

#  Unwrap Hard edge
def unwrapHardEdge(*arg):
	uv_mel_port.unwrap_hard_edge()

#   Unwrap selected edge
def unwrapSelectEdge(*arg):
	uv_mel_port.unwrap_select_edge()

# UVS EDIT

# Grid UV
def UVGridding(*arg):
	uv_mel_port.uv_gridding()

#  UV Unfold None
def smartUnfold(*arg):
	uv_mel_port.smart_unfold()

#region Transfer UV
# Logging Setup
logging.basicConfig()
logger = logging.getLogger("transfer_uvs")
logger.setLevel(logging.INFO)

def uv_import():
	""" Imports an OBJ file containing UVs (It meshes should be identical for this to work) """
	# Validate
	is_valid = False

	selection = cmds.ls(selection=True)

	if len(selection) > 0:
		is_valid = True
	else:
		cmds.warning('Please select at least one target mesh.')

	function_name = 'GT Import UVs'
	cmds.undoInfo(openChunk=True, chunkName=function_name)

	try:
		if is_valid:
			file_name = cmds.fileDialog2(fileFilter=script_name + " - Obj File (*.obj)", dialogStyle=2, fileMode=1,
										 okCaption='Import',
										 caption='Importing Obj with UVs for "' + script_name + '"') or []

			if len(file_name) > 0:
				# uv_file = file_name[0]
				file_exists = True
			else:
				file_exists = False

			if file_exists:
				# try:
				import_ns = 'tempObj_' + str(int(random.random() * 1000)) + '_'
				cmds.file(file_name, i=True, type='OBJ', ignoreVersion=True, ra=True, mergeNamespacesOnClash=False,
						  namespace=import_ns, options='obj', pr=True, importTimeRange='combine')

				imported_objects = cmds.ls(import_ns + ":*")
				imported_shapes = cmds.ls(imported_objects, type='mesh')

				if len(imported_shapes) > 0:
					error_occurred = False
					transfer_count = 0
					for obj in selection:
						try:
							transfer_history = cmds.transferAttributes(imported_objects[0], obj, transferPositions=0,
																	   transferNormals=0, transferUVs=2,
																	   transferColors=2, sampleSpace=4, searchMethod=3,
																	   colorBorders=1)
							history = cmds.listHistory(obj)
							intermediate_objs = []
							for hist in history:
								if cmds.objectType(hist) == 'mesh':
									if cmds.objExists(hist + '.intermediateObject'):
										if cmds.getAttr(hist + '.intermediateObject') is True:
											intermediate_objs.append(hist)

							for i_obj in intermediate_objs:
								cmds.setAttr(i_obj + '.intermediateObject', 0)
								cmds.transferAttributes(imported_objects[0], i_obj, transferPositions=0,
														transferNormals=0, transferUVs=2, transferColors=2,
														sampleSpace=4, searchMethod=3, colorBorders=1)
								cmds.delete(i_obj, constructionHistory=True)
								cmds.setAttr(i_obj + '.intermediateObject', 1)

							try:
								cmds.delete(transfer_history)
							except Exception as e:
								logger.debug(str(e))

							if are_uvs_identical(imported_objects[0], obj):
								transfer_count += 1
						except Exception as e:
							logger.debug(str(e))
							error_occurred = True
					cmds.delete(imported_objects)
					cmds.select(selection)

					unique_message = '<' + str(random.random()) + '>'
					if transfer_count == 1:
						unique_message += '<span style=\"color:#FF0000;text-decoration:underline;\">'
						unique_message += str(transfer_count)
						unique_message += '</span><span style=\"color:#FFFFFF;\"> ' \
										  'object received transferred UVs.</span>'
						cmds.inViewMessage(amg=unique_message, pos='botLeft', fade=True, alpha=.9)
						sys.stdout.write(str(transfer_count) + ' object received transferred UVs.')
					else:
						unique_message += '<span style=\"color:#FF0000;text-decoration:underline;\">'
						unique_message += str(transfer_count)
						unique_message += '</span><span style=\"color:#FFFFFF;\"> ' \
										  'objects received transferred UVs.</span>'
						cmds.inViewMessage(amg=unique_message, pos='botLeft', fade=True, alpha=.9)
						sys.stdout.write(str(transfer_count) + ' objects received transferred UVs.')
					if error_occurred:
						warning = 'Some UVs were not transferred as expected, please make sure you\'re using '
						warning += 'identical meshes. (Consider its history and intermediate objects)'
						cmds.warning(warning)

					# Clean Up Imported Objects
					delete_temp_namespace(import_ns)
				else:
					warning = "Imported Mesh with UVs couldn't be accessed. Please make sure it was exported correctly."
					cmds.warning(warning)
			else:
				cmds.warning("Couldn't read the file. Please make sure the selected file is accessible.")
	except Exception as e:
		cmds.warning(str(e))
	finally:
		cmds.undoInfo(closeChunk=True, chunkName=function_name)

def uv_transfer_source_target():
	""" Transfers UVs from a source object to target objects """
	# Validate
	is_valid = False

	selection = cmds.ls(selection=True)

	if len(selection) > 1:
		is_valid = True
	else:
		cmds.warning('Please select at least one source and one target.')

	if is_valid:
		function_name = 'GT Transfer UVs'
		cmds.undoInfo(openChunk=True, chunkName=function_name)
		try:
			error_occurred = False
			transfer_count = 0
			for obj in selection:
				if obj != selection[0]:
					try:
						transfer_history = cmds.transferAttributes(selection[0], obj, transferPositions=0,
																   transferNormals=0, transferUVs=2, transferColors=2,
																   sampleSpace=4, searchMethod=3, colorBorders=1)

						history = cmds.listHistory(obj)
						intermediate_objs = []
						for hist in history:
							if cmds.objectType(hist) == 'mesh':
								if cmds.objExists(hist + '.intermediateObject'):
									if cmds.getAttr(hist + '.intermediateObject') is True:
										intermediate_objs.append(hist)

						logger.debug(str(intermediate_objs))
						for i_obj in intermediate_objs:
							cmds.setAttr(i_obj + '.intermediateObject', 0)
							cmds.transferAttributes(selection[0], i_obj, transferPositions=0, transferNormals=0,
													transferUVs=2, transferColors=2, sampleSpace=4, searchMethod=3,
													colorBorders=1)
							cmds.delete(i_obj, constructionHistory=True)
							cmds.setAttr(i_obj + '.intermediateObject', 1)
						try:
							cmds.delete(transfer_history)
						except Exception as e:
							logger.debug(str(e))

						if are_uvs_identical(selection[0], obj):
							transfer_count += 1

					except Exception as e:
						logger.debug(str(e))
						error_occurred = True
			unique_message = '<' + str(random.random()) + '>'
			if transfer_count == 1:
				unique_message += '<span style=\"color:#FF0000;text-decoration:underline;\">'
				unique_message += str(transfer_count)
				unique_message += '</span><span style=\"color:#FFFFFF;\"> object received transferred UVs.</span>'
				cmds.inViewMessage(amg=unique_message, pos='botLeft', fade=True, alpha=.9)
				sys.stdout.write(str(transfer_count) + ' object received transferred UVs.')
			else:
				unique_message += '<span style=\"color:#FF0000;text-decoration:underline;\">'
				unique_message += str(transfer_count)
				unique_message += '</span><span style=\"color:#FFFFFF;\"> objects received transferred UVs.</span>'
				cmds.inViewMessage(amg=unique_message, pos='botLeft', fade=True, alpha=.9)
				sys.stdout.write(str(transfer_count) + ' objects received transferred UVs.')
			if error_occurred:
				warning = 'Some UVs were not transferred as expected, please make sure '
				warning += 'you\'re using identical meshes. (Consider its history and intermediate objects)'
				cmds.warning(warning)
		except Exception as e:
			cmds.warning(str(e))
		finally:
			cmds.undoInfo(closeChunk=True, chunkName=function_name)

def uv_export():
	""" Exports an OBJ file containing the model and UVs to be imported in another scene/model. """
	# Validate Proxy and Write file
	is_valid = False
	successfully_created_file = False

	selection = cmds.ls(selection=True)

	# Determine naming and validate
	if len(selection) == 1:
		shapes = cmds.listRelatives(selection[0], shapes=True, fullPath=True) or []
		if len(shapes) > 0:
			if cmds.objectType(shapes[0]) == 'mesh':
				is_valid = True
			else:
				cmds.warning('Please select an object of the type "Mesh".')
	elif len(selection) == 0:
		cmds.warning('Please select at least one object.')
	else:
		cmds.warning('Please select only one object.')

	uv_file = None
	if is_valid:
		file_name = cmds.fileDialog2(fileFilter=script_name + " - OBJ File (*.obj)", dialogStyle=2,
									 okCaption='Export UVs',
									 caption='Exporting OBJ with UVs for "' + script_name + '"') or []
		if len(file_name) > 0:
			uv_file = file_name[0]
			successfully_created_file = True

	if successfully_created_file and is_valid:
		try:
			cmds.file(uv_file, pr=1, typ="OBJexport", es=1, f=True, op="materials=0")
			unique_message = '<' + str(random.random()) + '>'
			unique_message += '<span style=\"color:#FF0000;text-decoration:underline;\">'
			unique_message += 'UV Obj</span><span style=\"color:#FFFFFF;\"> exported.</span>'
			cmds.inViewMessage(amg=unique_message, pos='botLeft', fade=True, alpha=.9)
			sys.stdout.write('UV Obj exported to the file "' + uv_file + '".')
		except Exception as e:
			logger.info(str(e))
			successfully_created_file = False
			logger.debug('successfully_created_file' + str(successfully_created_file))
			cmds.warning("Couldn't write to file. Please make sure the exporting directory is accessible.")

def delete_temp_namespace(temp_namespace):
	"""
	Deletes the provided namespace
	
				Parameters:
					temp_namespace (string): Namespace to be deleted
	"""
	default_namespaces = ['UI', 'shared']

	def num_children(namespace):
		""" Used as a sort key, this will sort namespaces by how many children they have. """
		return namespace.count(':')

	namespaces = [namespace for namespace in cmds.namespaceInfo(lon=True, r=True) if
				  namespace not in default_namespaces]

	# Reverse List
	namespaces.sort(key=num_children, reverse=True)  # So it does the children first

	for namespace in namespaces:
		if namespace not in default_namespaces and namespace == temp_namespace:
			mel.eval('namespace -mergeNamespaceWithRoot -removeNamespace "' + namespace + '";')


def get_uv_shells(obj):
	"""
	Returns a list with all UV sets
	
			Returns:
				all_sets = A list with all sets
	"""
	selection = OpenMaya.MSelectionList()
	selection.add(obj)
	sel_iter = OpenMaya.MItSelectionList(selection, OpenMaya.MFn.kMesh)
	shape_path = OpenMaya.MDagPath()
	sel_iter.getDagPath(shape_path)
	mesh_node = shape_path.fullPathName()
	uv_sets = cmds.polyUVSet(mesh_node, query=True, allUVSets=True)
	all_sets = []
	for uv_set in uv_sets:
		shape_fn = OpenMaya.MFnMesh(shape_path)
		shells = OpenMaya.MScriptUtil()
		shells.createFromInt(0)
		nb_uv_shells = shells.asUintPtr()

		u_array = OpenMaya.MFloatArray()  # U coordinates
		v_array = OpenMaya.MFloatArray()  # V coordinates
		shell_ids = OpenMaya.MIntArray()  # The container for the uv shell Ids

		shape_fn.getUVs(u_array, v_array)
		shape_fn.getUvShellsIds(shell_ids, nb_uv_shells, uv_set)

		shells = {}
		for i, n in enumerate(shell_ids):
			if n in shells:
				shells[n].append('%s.map[%i]' % (obj, i))
			else:
				shells[n] = ['%s.map[%i]' % (obj, i)]
		all_sets.append({uv_set: shells})
	return all_sets


def are_uvs_identical(obj_a, obj_b):
	"""
	Compares the UVs of objects A and B and returns True if they are different or False if they are not.
	
			Returns:
				is_identical(bool) : True if objects are different
	"""
	is_identical = True

	obj_a_uvs = get_uv_shells(obj_a)
	obj_b_uvs = get_uv_shells(obj_b)

	if len(obj_a_uvs) > 0 and len(obj_b_uvs) > 0:
		uvs_a_list = obj_a_uvs[0].get(list(obj_a_uvs[0].keys())[0])[0]
		uvs_b_list = obj_b_uvs[0].get(list(obj_b_uvs[0].keys())[0])[0]

		uv_pairs = zip(uvs_a_list, uvs_b_list)

		for uv_pair in uv_pairs:
			if is_identical:
				uv_sample_a = cmds.polyEditUV(uv_pair[0], query=True)
				uv_sample_b = cmds.polyEditUV(uv_pair[1], query=True)
				if uv_sample_a != uv_sample_b:
					is_identical = False

	return is_identical

# Creates GUI
def transferUV(*arg):
	script_name = 'Transfer UV Tool'
	""" Builds the UI for GT Sphere Types """
	if cmds.window("build_gui_uv_transfer", exists=True):
		cmds.deleteUI("build_gui_uv_transfer")

	# main dialog Start Here =================================================================================

	window_gui_uv_transfer = cmds.window("build_gui_uv_transfer", title=script_name,
										 titleBar=True, minimizeButton=False, maximizeButton=False, sizeable=True)
	cmds.window(window_gui_uv_transfer, e=True, s=True, wh=[1, 1])
	content_main = cmds.columnLayout(adj=True)

	cmds.separator(h=5, p=content_main, st="none")
	cmds.rowColumnLayout(p=content_main, numberOfColumns=3, columnWidth=[(1, 100), (2, 100), (3, 10)],
						 cs=[(1, 10), (2, 5)])
	cmds.button(l="Export UVs", bgc = (0.8, 0.5, 0), h=30, c=lambda x: uv_export(), w=100)
	cmds.button(l="Import UVs", bgc = (0.2, 0.8, 0.5), h=30, c=lambda x: uv_import())


	cmds.separator(h=10, st="in", p=content_main)
	cmds.rowColumnLayout(p=content_main, numberOfColumns=1, columnWidth=[(1, 205), (2, 1), (3, 10)],
						 cs=[(1, 10), (2, 5), (3, 5)])
	cmds.button(l="Transfer from Source to Target(s)", h=30, c=lambda x: uv_transfer_source_target(), w=100)

	# Show and Lock Window
	cmds.showWindow(window_gui_uv_transfer)
	cmds.window(window_gui_uv_transfer, e=True, s=False)

#endregion


# UV Planar
def set_camera_by_selected_face(*arg):
	print(1)

def unfold_uv_by_camera(*arg):
	print(2)

#  chon vung chon ben maya xuat qua PSD
def UVtoPSD(*arg):
	import edgeToPSSelection
	reload(edgeToPSSelection)
	edgeToPSSelection.run()

# Match UV 
def matchUV(*arg):
	import matchUV
	reload(matchUV)
	matchUV.matchUVs()

# UV Ratio
def UV_ratio(*arg):
	uv_mel_port.uv_ratio()

# UV Scale
def get_texel_density(*arg):
	faces = cmds.polyListComponentConversion(cmds.ls(sl=True, fl=True), tf = True)
	ws_area = 0.0
	uv_area = 0.0

	for face in faces:
		ws_area += cmds.polyEvaluate(face, worldFaceArea=True)[0]
		uv_area += cmds.polyEvaluate(face, uvFaceArea=True)[0] # By default I hope it picks the current uv set
	

	# Get the square root of the area
	ws_area = math.sqrt(ws_area)
	uv_area = math.sqrt(uv_area)

	px_area = uv_area * cmds.intField("size_map_tf", q=True, v=True)

	return px_area / ws_area
	

def show_texel_density(*arg):
	cmds.floatField("texel_density_ff", e=True, v=get_texel_density())

def scale_by_center_group(*arg):
	ratio = cmds.floatField('texel_density_ff', q=True, v=True) / get_texel_density()
	#convert selected object to UV
	cmds.select(cmds.polyListComponentConversion(tuv = True), r = True)
	x = cmds.ls(sl=True, fl=True)
	
	#calculate center
	u = 0
	v = 0

	for i in x:
		u += cmds.polyEditUV(i, query = True)[0]
		v += cmds.polyEditUV(i, query = True)[1]

	u = u/len(x)
	v = v/len(x)

	#scale UV from center
	cmds.polyEditUV(pivotU=u, pivotV=v, scaleU=ratio, scaleV=ratio)

def scale_by_center_element(*arg):
	ratio = cmds.floatField('texel_density_ff', q=True, v=True) / get_texel_density()
	#convert selected object to UV
	cmds.select(cmds.polyListComponentConversion(tuv = True), r = True)
	uv_list = cmds.ls(sl=True, fl=True)
	while len(uv_list) > 0:
		cmds.select(uv_list[0])
		cmds.ConvertSelectionToUVShell()
		x = cmds.ls(sl=True, fl=True)
		u = 0
		v = 0
		for i in x:
			u += cmds.polyEditUV(i, query = True)[0]
			v += cmds.polyEditUV(i, query = True)[1]

		u = u/len(x)
		v = v/len(x)

		#scale UV from center
		cmds.polyEditUV(pivotU=u, pivotV=v, scaleU=ratio, scaleV=ratio)
		uv_list = list(set(uv_list) - set(cmds.ls(sl=True, fl=True)))
		

# UV Checker
def UVChecker(*arg):
	import UVChecker
	reload(UVChecker)

# UV Editor
def OpenUVEditor(*arg):
	cmds.TextureViewWindow()

#region support function
global config_path
global Config
global rizom_path
global rizom_script_path
global export_file

DEBUG = True

def remove_all_namespace():
	listRef = [n.replace('RN','') for n in cmds.ls(rf = True)]
	cmds.namespace( set=':' )
	allNameSpace = [n.split(':')[len(n.split(':'))-1] for n in cmds.namespaceInfo(lon = True, fn = True, r = True) if n not in ['UI', 'shared']]
	remove = []
	if allNameSpace:
		for a in allNameSpace:
			if a not in listRef:
				cmds.namespace(rm = a , mnr = True, f = True)
				remove.append(a)
		cmds.confirmDialog(icn = 'warning', m = 'remove namsepace: ' + str(remove))
	else:
		cmds.select(d=True)

def config_for_rizom():
	global config_path
	global Config
	global rizom_path
	global rizom_script_path
	global export_file

	config_path = tempfile.gettempdir() + os.sep + "rizom_uvtool_config.ini"

	Config = ConfigParser.ConfigParser()
	
	rizom_script_path = tempfile.gettempdir() + os.sep + "MayaRizomBridgeScript.lua"
	rizom_script_path = rizom_script_path.replace('\\', '/')
	
	check_lua_path()

	if not os.path.exists(config_path):
		reset_config()
	Config.read(config_path)

	rizom_path = Config.get('Application', 'AppPath')
	export_file = os.path.join(tempfile.gettempdir(), Config.get('Application', 'ObjName')).replace('\\', '/')

def check_lua_path():
	if not os.path.exists(rizom_script_path):
		with open(rizom_script_path, 'w') as f:
			if DEBUG: 
				print("<RizomUV Bridge> Creating blank lua file at " + rizom_script_path)
			f.write('')


def reset_config():
	if not os.path.exists(config_path):
		default_file = os.path.join(os.path.dirname(__file__), 'config_default.ini')
		if DEBUG: 
			print("<RizomUV Bridge> Default config file path:" + default_file)
		with open(config_path, 'w') as f:
			shutil.copyfile(default_file, config_path)

def write_to_lua_file(command):
	with open(rizom_script_path, 'w') as f:
		f.write(command)

#endregion

def open_rizom(*arg):
	# Rizomuv -cf path/to/remote/control/script.lua
	# Each time the file date stamp, rizomuv will execute the script

	global rizom_path

	if not os.path.exists(config_path):
		reset_config()
	Config.read(config_path)

	# Confirm application path
	if not os.path.exists(rizom_path):
		fname = cmds.fileDialog2(startingDirectory = 'C:/Program Files/Rizom Lab/', fileFilter="Executable (*.exe)", fileMode = 1)
		Config.set('Application', 'AppPath', fname[0])
		rizom_path = fname[0]

	cmd = '"' + rizom_path + '" -cf "' + rizom_script_path + '"'

	if platform.system() == "Windows":
		subprocess.Popen(cmd)
	else:
		subprocess.Popen(["open", "-a", rizom_path, "-cf", rizom_script_path])

	return True


def select_rizom_version(*arg):
	# Rizomuv -cf path/to/remote/control/script.lua
	# Each time the file date stamp, rizomuv will execute the script

	global rizom_path

	if not os.path.exists(config_path):
		reset_config()
	Config.read(config_path)

	fname = cmds.fileDialog2(startingDirectory = 'C:/Program Files/Rizom Lab/', fileFilter="Executable (*.exe)", fileMode = 1)
	Config.set('Application', 'AppPath', fname[0])
	rizom_path = fname[0]

	cmd = '"' + rizom_path + '" -cf "' + rizom_script_path + '"'

	if platform.system() == "Windows":
		subprocess.Popen(cmd)
	else:
		subprocess.Popen(["open", "-a", rizom_path, "-cf", rizom_script_path])

	return True

def export_to_rizom(*arg):
	exported_objects = cmds.ls(sl=True, tr=True)
	if len(exported_objects) == 0:
		cmds.confirmDialog(m = "Please select object in scene")
		return False
	# Export Options
	cmd = 'ZomLoad({File={Path="'+ export_file +'", ImportGroups=true, XYZUVW=true, UVWProps=true}})\n'

	# FBX Export
	if not cmds.pluginInfo("fbxmaya", loaded=True, query=True):
		cmds.loadPlugin("fbxmaya")

	cmds.undoInfo(openChunk=True)
	try:
		mel.eval("FBXExportSmoothingGroups -v true;")
		mel.eval("FBXExportTriangulate -v false;")
		mel.eval("FBXExportSmoothMesh -v false;")
		mel.eval("FBXExportUpAxis z;")
		mel.eval('FBXExport -f \"'+ export_file + '\" -s;')
	finally:
		cmds.undoInfo(closeChunk=True)
	cmds.undo()

	write_to_lua_file(cmd)

	return True

def import_to_maya(*arg):
	if not os.path.exists(export_file):
		cmds.confirmDialog(m = "Could not locate exported file: " + export_file)

	# FBX Import
	namespace = ':RIZOMUV'
	if not cmds.namespace(ex = namespace):
		cmds.namespace(add = namespace)
	cmds.namespace(set = namespace)
	mel.eval("FBXImportMode -v add;")
	mel.eval('FBXImport -f \"'+ export_file + '\"')
	# END FBX Import

	imported_objects = cmds.ls('RIZOMUV:*', long=True, type="mesh")

	original_matches = []

	for riz_obj in imported_objects:
		original = riz_obj.replace('RIZOMUV:', '')
		original_matches.append(original.rsplit('|', 1)[0])
		cmds.polyTransfer(original.rsplit('|', 1)[0], ao=riz_obj.rsplit('|', 1)[0], ch=False, uv=True)

	cmds.select(original_matches)
	cmds.bakePartialHistory()
	cmds.delete('RIZOMUV:*')
	cmds.namespace(rm = ':RIZOMUV', mnr = True, f = True)

def createUVSet(*arg):
	new_name = cmds.textField('rename_textbox', q = True, tx = True)
	if new_name != "":
		selected_objects = cmds.ls(sl=True, fl=True)
		for obj in selected_objects:
			all_uvsets = cmds.polyUVSet(obj, q=True, auv=True)
			if new_name not in all_uvsets:
				cmds.polyUVSet(obj, create=True, uvSet=new_name)
				cmds.warning("Create new UVSet: DONE!")
			else:
				cmds.warning("Object: " + obj + " already have this UVSet name!")
	else:
		cmds.warning("Please input name for create UVSet!")
	reloadUVSetTextScroll()

def renameUVSet(*arg):
	selected_objects = cmds.ls(sl=True, fl=True)
	try:
		selected_uvset = cmds.textScrollList("uvset_list_textscroll", q = True, si=True)[0]
	except:
		cmds.warning("Please select UVSet to rename UVSet!")
		return False
	new_name = cmds.textField('rename_textbox', q = True, tx = True)
	if new_name != "":
		for obj in selected_objects:
			all_uvsets = cmds.polyUVSet(obj, q=True, auv=True)
			if new_name not in all_uvsets and selected_uvset in all_uvsets:
				cmds.polyUVSet(obj, rename=True, newUVSet=new_name, uvSet= selected_uvset)
				cmds.warning("Rename UVSet: DONE!")
			else:
				cmds.warning("Object: " + obj + " already have this UVSet name!")
	else:
		cmds.warning("Please input name for rename UVSet!")
	reloadUVSetTextScroll()
	return True

def deleteUVSet(*arg):
	selected_object_list = cmds.ls(sl=True, fl=True)
	try:
		selected_uvset = cmds.textScrollList("uvset_list_textscroll", q = True, si=True)[0]
	except:
		cmds.warning("Please select UVSet to delete UVSet!")
		return False
	
	for obj in selected_object_list:
		all_uvsets = cmds.polyUVSet(obj, q=True, auv=True)
		if len(all_uvsets) == 1 and all_uvsets[0] == selected_uvset:
			cmds.warning("Object: " + obj +  " have only this one UVset!")
		elif all_uvsets[0] == selected_uvset:
			cmds.polyUVSet(obj, reorder=True, uvSet=selected_uvset, nuv=all_uvsets[1])
			cmds.polyUVSet(obj, delete=True, uvSet=selected_uvset)
			cmds.warning("Delete UVSet: DONE!")
		elif selected_uvset in all_uvsets:
			cmds.polyUVSet(obj, delete=True, uvSet=selected_uvset)
			cmds.warning("Delete UVSet: DONE!")
	reloadUVSetTextScroll()
	return True

def copyUVSet(*arg):
	selected_object_list = cmds.ls(sl=True, fl=True)
	new_name = cmds.textField('rename_textbox', q = True, tx = True)
	if new_name != "":
		selected_uvset = cmds.textScrollList("uvset_list_textscroll", q = True, si=True)[0]
		for obj in selected_object_list:
			all_uvsets = cmds.polyUVSet(obj, q=True, auv=True)
			if new_name not in all_uvsets:
				cmds.polyUVSet(obj, copy=True, nuv=new_name, uvSet=selected_uvset)
				cmds.warning("Copy UVSet: DONE!")
			else:
				cmds.warning("Object: " + obj + " already have this UVSet name!")
	else:
		cmds.warning("Please input name for copy UVSet!")
	reloadUVSetTextScroll()
	return True

def reloadUVSetTextScroll(*arg):
	try:
		cmds.textScrollList("uvset_list_textscroll", e = True, ra = True)
		if len(cmds.ls(sl=True, fl=True)) > 1:
			map1 = cmds.polyUVSet(q=True, auv=True)[0]
			uvset_list = sorted(list(set(cmds.polyUVSet(q=True, auv=True))))
			uvset_list.insert(0, uvset_list.pop(uvset_list.index(map1)))
		else:
			uvset_list = cmds.polyUVSet(q=True, auv=True)
		if uvset_list == None:
			uvset_list = []
		cmds.textScrollList("uvset_list_textscroll", e = True, a = uvset_list)
	except:
		pass

def selectUVSet(*arg):
	selected_object_list = cmds.ls(sl=True, fl=True)
	selected_uvset = cmds.textScrollList("uvset_list_textscroll", q = True, si=True)[0]
	for obj in selected_object_list:
		cmds.polyUVSet(obj, e=True, cuv=True, uvSet=selected_uvset)
	cmds.TextureViewWindow()

def selectObjectByUVSet(*arg):
	obj_list = []
	try:
		selected_uvset = cmds.textScrollList("uvset_list_textscroll", q = True, si=True)[0]
	except:
		cmds.warning("Please select UVSet to select objects!")
		return False
	
	selected_object_list = [m for m in cmds.ls(sl=True, fl=True)]
	for obj in selected_object_list:
		uvset_list = cmds.polyUVSet(obj, q=True, allUVSets=True)
		for uvset in uvset_list:
			if uvset == selected_uvset:
				obj_list.append(obj)
				cmds.polyUVSet(obj, e=True, cuv=True, uvSet=selected_uvset)
				break
	cmds.select(obj_list)
	cmds.warning("Select objects by selected UVSet: DONE!")
	return True

def setDefaultUVSet(*arg):
	try:
		selected_uvset = cmds.textScrollList("uvset_list_textscroll", q = True, si=True)[0]
	except:
		cmds.warning("Please select UVSet to set default UVSet!")
		return False
	
	selected_object_list = cmds.ls(sl=True, fl=True)
	for obj in selected_object_list:
		all_uvsets = cmds.polyUVSet(obj, q=True, auv=True)
		if selected_uvset in all_uvsets:
			if selected_uvset != all_uvsets[0]:
				cmds.polyUVSet(obj, reorder=True, uvSet=selected_uvset, nuv=all_uvsets[0])
			else:
				pass
			cmds.warning("Set Default UVSet: DONE!")
		else:
			cmds.warning("Object: " + obj +  " doesn't have UVset: " + selected_uvset + " !")
	reloadUVSetTextScroll()
	return True

def sortUVSetList(*arg):
	selected_object_list = cmds.ls(sl=True, fl=True)
	uvset_list = []
	for obj in selected_object_list:
		all_uvsets = cmds.polyUVSet(obj, q=True, auv=True)
		uvset_list = sorted(list(set(all_uvsets)))
		print(all_uvsets)
		print(uvset_list)
		for i in range(0, len(uvset_list)):
			all_uvsets = cmds.polyUVSet(obj, q=True, auv=True)
			if uvset_list[i] != all_uvsets[i]:
				cmds.polyUVSet(obj, reorder=True, uvSet=uvset_list[i], nuv=all_uvsets[i])
	reloadUVSetTextScroll()
	return True