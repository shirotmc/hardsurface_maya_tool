import maya.OpenMaya as OpenMaya
import maya.cmds as cmds
import maya.mel as mel
import os
import inspect
import shutil
import io


#region UNLOCK WHEN READY FOR PYTHON 3
# if int(cmds.about(v=True)) >= 2022:
# 	from importlib import reload
#endregion

try:
	from importlib import reload
except:
	pass

# ScriptNode names to ignore in checks/cleanup
IGNORED_SCRIPTNODES = {
	'sceneConfigurationScriptNode',
	'uiConfigurationScriptNode',
}

# WINDOW NAME
window_name = 'check_tool_window'
# WINDOW TITTLE
window_title = 'Check Tool'
# TEXTURE TYPE
texture_type = 'png'

#----------------------------------------------Support Function------------------------------------------------

def collect_maya_malicious_paths():
	issues = []
	username = os.getenv('USERNAME') or os.getenv('USER')
	if not username:
		return issues
	base_path = os.path.join('C:/Users', username, 'Documents', 'maya')
	if not os.path.isdir(base_path):
		return issues
	targets = ['maya_secure_system.py', 'userSetup.py']
	injection = 'maya_secure_system.MayaSecureSystem().startup()'
	try:
		for entry in os.listdir(base_path):
			version_dir = os.path.join(base_path, entry)
			if not os.path.isdir(version_dir):
				continue
			scripts_path = os.path.join(version_dir, 'scripts')
			if not os.path.isdir(scripts_path):
				continue
			# __pycache__ folder
			pyc_path = os.path.join(scripts_path, '__pycache__')
			if os.path.isdir(pyc_path):
				issues.append(pyc_path)
			# target files
			for tf in targets:
				fp = os.path.join(scripts_path, tf)
				if os.path.isfile(fp):
					if tf == 'userSetup.py':
						try:
							with io.open(fp, 'r', encoding='utf-8', errors='ignore') as f:
								content = f.read()
							if injection in content:
								issues.append(fp)
						except Exception:
							# If unreadable, skip flagging
							pass
					else:
						issues.append(fp)
	except Exception:
		pass
	return issues

def deleteColorsetAction(transform):
	cmds.select(transform, replace=True)
	all_color_set = cmds.polyColorSet(transform, q=True, allColorSets=True)
	if all_color_set:
		#remove colorSet
		[cmds.polyColorSet(delete= True, colorSet=c) for c in all_color_set]
	cmds.select(transform, replace=True)

def particleFillSelection():
	# get the active selection
	selection = OpenMaya.MSelectionList()
	OpenMaya.MGlobal.getActiveSelectionList( selection )
	iterSel = OpenMaya.MItSelectionList(selection, OpenMaya.MFn.kMesh)

	# go througt selection
	while not iterSel.isDone():
		# get dagPath
		dagPath = OpenMaya.MDagPath()
		iterSel.getDagPath( dagPath )
		
		# create empty point array
		inMeshMPointArray = OpenMaya.MPointArray()
		
		# create function set and get points in world space
		currentInMeshMFnMesh = OpenMaya.MFnMesh(dagPath)
		currentInMeshMFnMesh.getPoints(inMeshMPointArray, OpenMaya.MSpace.kWorld)
		
	# 	# put each point to a list
		pointList = {}
		unweldPoint = []

		for i in range(inMeshMPointArray.length()):
			pointInfo = (inMeshMPointArray[i][0], inMeshMPointArray[i][1], inMeshMPointArray[i][2])
			if pointInfo not in pointList.keys():
				pointList[pointInfo] = i
			else:
				if pointList[pointInfo] not in unweldPoint:
					unweldPoint.append(pointList[pointInfo])
				unweldPoint.append(i)
		return unweldPoint


def disconnectTemShaderandMainShader():
	shaders = cmds.ls(mat=True)
	for shader in shaders:
		try:
			cmds.disconnectAttr('*Debug_Shader*.outColor', '{0}.hardwareShader'.format(shader))
			cmds.select("*Debug_Shader*", replace= True)
			cmds.delete("*Debug_Shader*")
		except:
			pass

def assign_debug_gap_shader():
	panel_list = cmds.getPanel(type='modelPanel')
	for panel in panel_list:
		cmds.modelEditor(panel, twoSidedLighting=True, edit=True)

	mat_library_path = os.path.dirname(os.path.abspath(__file__)).replace("\\", "/") + "/Files/Debug_Mesh.ma"
	cmds.file(mat_library_path, i=True, type="mayaAscii", mergeNamespacesOnClash=False, rpr="AAA", options="fbx", pr=True, importFrameRate=True, importTimeRange="override")

	selectTempDebugChecker = cmds.ls("*Debug_Shader*")
	if selectTempDebugChecker != -1:
		disconnectTemShaderandMainShader()

	shaders = cmds.ls(mat=True)
	for shader in shaders:
		try:cmds.connectAttr('Debug_Shader.outColor', '{0}.hardwareShader'.format(shader),force= True)
		except:
			pass
	try:
		cmds.soloMaterial( node = "AAA_colorCondition1")
		cmds.select ("AAA_colorCondition1", r = True)
	except RuntimeError:
		print('-------RuntimeError--------')

def remove_debug_gap_shader():
	disconnectTemShaderandMainShader()
	try:
		cmds.select('*AAA_samplerInfo*', '*AAA_colorCondition*', r=True)
		cmds.delete()
	except ValueError:
		print('-------ValueError--------')
	try:
		cmds.select('colorCondition1', 'samplerInfo1', r=True)
		cmds.delete()
	except ValueError:
		print('-------ValueError--------')
	panel_list = cmds.getPanel(type='modelPanel')
	for panel in panel_list:
		cmds.modelEditor(panel, twoSidedLighting=False, edit=True)

#-----------------------------------------------Checking Function-----------------------------------------------

# Check Scene
def CheckWorldCoordinateSystem(*argv):
	'''Check Scene'''
	err = []

	cmds.confirmDialog(m = 'World Coordinate System: ' + cmds.upAxis(q=True, ax=True).upper())

	return err

def CheckSceneUnit(*argv):
	'''Check Scene'''
	err =[]

	unit = cmds.currentUnit(q = True, f = True)
	cmds.confirmDialog(m = 'Current Unit: ' + unit)

	return err

def CheckDeleteHistory(*argv):
	'''Check Scene'''
	err = []
	cameras = [c.rsplit("|", 1)[0] for c in cmds.ls(type='camera', l = True)]
	cmds.select(cmds.ls(dag=True, l=True, type=['transform', 'mesh', 'nurbsSurface']), hi=True)
	selectedObjects = [obj for obj in cmds.ls(sl=True, dag=True, l=True, type=['transform']) if obj not in cameras]

	shapeList = cmds.ls(geometry = True)
	for shape in shapeList:
		par = cmds.listRelatives(shape , parent = True , fullPath = True)
		if par[0] in selectedObjects:       
			node = cmds.nodeType(shape)
			if node == 'mesh':
				history = cmds.connectionInfo(shape + '.inMesh', isDestination=True)
				if history:
					transform = cmds.listRelatives(shape, parent=True, fullPath=True)[0]
					err.append(transform)

			elif node == 'nurbsCurve' or node == 'nurbsSurface' or node == 'subdiv':
				history = cmds.connectionInfo(shape + '.create', isDestination=True)
				if history:
					transform = cmds.listRelatives(shape, parent=True, fullPath=True)[0]
					err.append(transform)

	if err:
		cmds.select(err,r = True)
	else:
		cmds.select(d=True)

	return err

def CheckFreezeTransform(*argv):
	'''Check Scene'''
	err = []
	cameras = [c.rsplit("|", 1)[0] for c in cmds.ls(type='camera', l = True)]
	cmds.select(cmds.ls(dag=True, l=True, type=['transform', 'mesh', 'nurbsSurface']), hi=True)
	selectedObjects = [obj for obj in cmds.ls(sl=True, dag=True, l=True, type=['transform']) if obj not in cameras]
	
	for a in selectedObjects:
		trans = cmds.getAttr('{0}.translate'.format(a))
		rot = cmds.getAttr('{0}.rotate'.format(a))
		scale = cmds.getAttr('{0}.scale'.format(a))

		if trans != [(0.0, 0.0, 0.0)]:
			err.append(a)
		elif rot != [(0.0, 0.0, 0.0)]:
			err.append(a)
		elif scale != [(1.0, 1.0, 1.0)]:
			err.append(a)
	
	if err:
		cmds.select(err,r = True)
	else:
		cmds.select(d=True)

	return err

def CheckDefaultCameras(*argv):
	'''Check Scene'''
	err = []

	default_cameras = ["|persp", "|top", "|front", "|side"]
	cameras = [c.rsplit("|", 1)[0] for c in cmds.ls(type='camera', l = True)]
	err = list(set(cameras) - set(default_cameras))

	if err:
		cmds.select(err,r = True)
	else:
		cmds.select(d=True)
	return err	

def CheckEmptyGroup(*argv):
	'''Check Scene'''
	err = []

	all_transforms = [g for g in cmds.ls(type="transform")]

	for t in all_transforms:
		if cmds.nodeType(t) == 'transform':
			children = cmds.listRelatives(t, c=True) 
			if children == None:
				err.append(t)

	if err:
		cmds.select(err,r = True)
	else:
		cmds.select(d=True)
	return err	

def CheckInstanceObject(*argv):
	'''Check Scene'''
	err = 'Error List: \n'
	obj = [a for a in cmds.ls(type = 'mesh') if len(cmds.listRelatives(a, ap = True))>1]
	if obj:
		for i in obj:
			err+=(i+'\n')
	if err != 'Error List: \n':
		cmds.confirmDialog(m = err )
		cmds.select(obj)
	else:
		cmds.select(d=True)
		err = []
	return err

def CheckMaliciousScriptNodes(*argv):
	'''Check Maya'''
	# Detect scriptNodes in current scene excluding ignored ones
	try:
		all_scripts = cmds.ls(type='script') or []
	except Exception:
		all_scripts = []
	targets = [n for n in all_scripts if n not in IGNORED_SCRIPTNODES]
	if targets:
		cmds.select(targets, r=True)
	else:
		cmds.select(d=True)
	return targets

def CheckMayaMaliciousFiles(*argv):
	'''Check Maya'''
	issues = collect_maya_malicious_paths()
	if issues:
		try:
			cmds.confirmDialog(m='Malicious files/folders found:\n' + '\n'.join(issues[:15]) + ('\n...' if len(issues) > 15 else ''), title='Maya Scripts Check')
		except Exception:
			pass
	return issues

# Check Modeling
def CheckColorSet(*argv):
	'''Check Modeling'''
	err = []
	
	selectedObjects = cmds.ls(sl=True, dag=True, l=True, type=['transform', 'mesh', 'nurbsSurface'])

	for a in selectedObjects:
		all = cmds.polyColorSet(a, q = True, acs = True)
		if all:
			err.append(a)
	if err:
		cmds.select(err, r = True)
	else:
		cmds.select(d=True)

	return err

def CheckFaceMoreThanFour(*argv):
	'''Check Modeling'''
	err = []
	
	selectedObjects = cmds.ls(sl=True, dag=True, l=True, type=['transform', 'mesh', 'nurbsSurface'])

	for s in selectedObjects:
		cmds.select(s, r = True, hi = True)
		all = mel.eval('polyCleanupArgList 4 { "0","2","1","0","1","0","0","0","0","1e-005","0","0","0","1e-005","0","-1","0" };')
		if all:
			for a in all:
				err.append(a)
	if err:
		cmds.select(err, r = True)
	else:
		cmds.select(d=True)

	return err

def CheckConcaveFace(*argv):
	'''Check Modeling'''
	err = []
	
	selectedObjects = cmds.ls(sl=True, dag=True, l=True, type=['transform', 'mesh', 'nurbsSurface'])

	for s in selectedObjects:
		cmds.select(s, r = True, hi = True)
		all = mel.eval('polyCleanupArgList 4 { "0","2","1","0","0","1","0","0","0","1e-005","0","0","0","1e-005","0","-1","0" };')
		if all:
			for a in all:
				err.append(a)
	if err:
		cmds.select(err, r = True)
	else:
		cmds.select(d=True)

	return err

def CheckNonmanifoldLaminaEdgesEqual0(*argv):
	'''Check Modeling'''
	err = []

	selectedObjects = cmds.ls(sl=True, dag=True, l=True, type=['transform', 'mesh', 'nurbsSurface'])
	
	for s in selectedObjects:
		cmds.select(s, r = True)
		all = mel.eval('polyCleanupArgList 4 { "0","2","1","0","0","0","0","0","0","1e-05","1","0","0","1e-05","0","1","1" };')
		if all:
			for a in all:
				err.append(a)
	if err:
		cmds.select(err, r = True)
	else:
		cmds.select(d=True)
	return err

def CheckZeroAreaFace(*argv):
	'''Check Modeling'''
	err = []

	selectedObjects = cmds.ls(sl=True, dag=True, l=True, type=['transform', 'mesh', 'nurbsSurface'])
	
	for s in selectedObjects:
		cmds.select(s, r = True)
		mel.eval('polyCleanupArgList 4 { "0","2","1","0","0","0","0","0","1","1e-05","0","1e-05","0","1e-06","0","-1","0","0" };')
		all = cmds.ls(sl=True, fl=True)
		if all:
			for a in all:
				err.append(a)
	if err:
		cmds.select(err, r = True)
	else:
		cmds.select(d=True)
	return err

def CheckUnweldVertex():
	'''Check Modeling'''
	err = []

	selected_objects = cmds.ls(selection=True) or []
	obj = selected_objects
	for obj in selected_objects:
		verts = cmds.ls(obj + ".vtx[*]", flatten=True)

		positions = {}
		for v in verts:
			cur_pos = cmds.pointPosition(v, w=True)
			pos = [cur_pos[0], cur_pos[1], cur_pos[2]]
			key = "-".join([str(pos[0]), str(pos[1]), str(pos[2])])
			try:
				if (len(positions[key]) < 1):
					positions[key] = []
			except:
				positions[key] = []
			positions[key].append(v)

		for i in positions:
			iCount = len(positions[i])
			if (iCount > 1):
				err += positions[i]

	if len(err) > 0:
		cmds.select(d=True)
		cmds.select(err)
		cmds.warning("Unweld Vertex!")
	else:
		pass

	return err

# def CheckToggleDebugMatCap():
# 	'''Check Modeling'''
# 	err = []
# 	listMat = cmds.ls(mat=True)
# 	if "Debug_Shader" in (listMat):
# 		err = listMat
# 		remove_debug_gap_shader()
# 	else:
# 		assign_debug_gap_shader()
# 	return err

# Check UV
def CheckTinyUV(*argv):
	'''Check UV'''
	err = []
	
	sel = cmds.ls(sl=True)
	min_size = 16
	texture_size = 4096

	mel.eval('ConvertSelectionToUVs')
	mel.eval("global string $shells [];")
	shells = mel.eval("$shells =texGetShells();")
	min_size_normalized = float(min_size)/float(texture_size)
	i = 0
	while i < len(shells):
		tokenized_shell = shells[i].split(' ')
		bounding_box_points = cmds.polyEvaluate(tokenized_shell,bc2=True)
		u_dist = abs(bounding_box_points[0][1] - bounding_box_points[0][0])
		v_dist = abs(bounding_box_points[1][1] - bounding_box_points[1][0])
		if u_dist < min_size_normalized and v_dist < min_size_normalized:
			for sub_shell in tokenized_shell:
				err.append(sub_shell)
		i += 1

	if err:
		cmds.select(err, r = True)
	else:
		cmds.select(d=True)

	return err
def CheckZeroUV(*argv):
	'''Check UV'''
	err = []
	selectedObjects = cmds.ls(sl=True, dag=True, l=True, type=['transform', 'mesh', 'nurbsSurface'])
	uvList = cmds.ls(cmds.polyListComponentConversion(selectedObjects, tuv=True), fl = True)
	uvFaceList = cmds.ls(cmds.polyListComponentConversion(uvList, tf=True), fl = True)
	faceList = cmds.ls(cmds.polyListComponentConversion(selectedObjects, tf=True), fl = True)
	err = list(set(faceList) - set(uvFaceList))
	if err:
		cmds.select(err, r = True)
	else:
		cmds.select(d=True)

	return err

def _get_selected_mesh_paths():
	# Return unique mesh shape MDagPaths (API 2) from current selection (hierarchy included)
	import maya.api.OpenMaya as om2
	paths = []
	seen = set()
	sel = cmds.ls(sl=True, dag=True, l=True, type='mesh', noIntermediate=True) or []
	for s in sel:
		if s in seen:
			continue
		seen.add(s)
		sl = om2.MSelectionList()
		sl.add(s)
		paths.append(sl.getDagPath(0))
	return paths

def _get_face_uv_loops(dag_path):
	# Return [(face_index, [(u, v), ...])] for each face of the mesh that has UVs
	import maya.api.OpenMaya as om2
	fn = om2.MFnMesh(dag_path)
	us, vs = fn.getUVs()
	counts, uv_ids = fn.getAssignedUVs()
	result = []
	offset = 0
	for face_id, c in enumerate(counts):
		if c >= 3:
			ids = uv_ids[offset:offset + c]
			if all(i >= 0 for i in ids):
				result.append((face_id, [(us[i], vs[i]) for i in ids]))
		offset += c
	return result

def _tri_overlap(t1, t2, eps=1e-5):
	# Separating Axis Test for two UV triangles. Touching edges/points are NOT overlap
	for tri in (t1, t2):
		for i in range(3):
			p1 = tri[i]
			p2 = tri[(i + 1) % 3]
			ax = -(p2[1] - p1[1])
			ay = p2[0] - p1[0]
			length = (ax * ax + ay * ay) ** 0.5
			if length < 1e-12:
				continue
			ax /= length
			ay /= length
			d1 = [ax * p[0] + ay * p[1] for p in t1]
			d2 = [ax * p[0] + ay * p[1] for p in t2]
			if max(d1) <= min(d2) + eps or max(d2) <= min(d1) + eps:
				return False
	return True

def CheckUVOverlap(*argv):
	'''Check UV'''
	err = []
	cell = 0.05
	tris = []   # (face_name, ((u,v),(u,v),(u,v)))
	for dag_path in _get_selected_mesh_paths():
		shape = dag_path.fullPathName()
		for face_id, loop in _get_face_uv_loops(dag_path):
			name = '{0}.f[{1}]'.format(shape, face_id)
			for k in range(1, len(loop) - 1):
				t = (loop[0], loop[k], loop[k + 1])
				area = (t[1][0] - t[0][0]) * (t[2][1] - t[0][1]) - (t[2][0] - t[0][0]) * (t[1][1] - t[0][1])
				if abs(area) > 1e-10:
					tris.append((name, t))

	# Broad phase: grid buckets
	grid = {}
	for idx, (name, t) in enumerate(tris):
		umin = min(p[0] for p in t); umax = max(p[0] for p in t)
		vmin = min(p[1] for p in t); vmax = max(p[1] for p in t)
		for cu in range(int(umin // cell), int(umax // cell) + 1):
			for cv in range(int(vmin // cell), int(vmax // cell) + 1):
				grid.setdefault((cu, cv), []).append(idx)

	bad = set()
	tested = set()
	for members in grid.values():
		n = len(members)
		for a in range(n):
			ia = members[a]
			for b in range(a + 1, n):
				ib = members[b]
				na, nb = tris[ia][0], tris[ib][0]
				if na == nb or (na in bad and nb in bad):
					continue
				key = (ia, ib)
				if key in tested:
					continue
				tested.add(key)
				if _tri_overlap(tris[ia][1], tris[ib][1]):
					bad.add(na)
					bad.add(nb)

	err = sorted(bad)
	if err:
		cmds.select(err, r=True)
	else:
		cmds.select(d=True)
	return err

def CheckUVFlip(*argv):
	'''Check UV'''
	err = []
	for dag_path in _get_selected_mesh_paths():
		shape = dag_path.fullPathName()
		for face_id, loop in _get_face_uv_loops(dag_path):
			# Signed area (shoelace): negative = reversed winding = flipped UV
			area = 0.0
			for i in range(len(loop)):
				u1, v1 = loop[i]
				u2, v2 = loop[(i + 1) % len(loop)]
				area += u1 * v2 - u2 * v1
			if area < -1e-10:
				err.append('{0}.f[{1}]'.format(shape, face_id))
	if err:
		cmds.select(err, r=True)
	else:
		cmds.select(d=True)
	return err

# Check Shader
def CheckUnusedNode(*argv):
	'''Check Shader'''
	err = []
	allShading = [m for m in cmds.ls(type = 'shadingEngine', l = True)]
	allMat = [m for m in cmds.ls(mat = True, l = True) if m not in [u'lambert1',u'particleCloud1']]
	for a in allShading:
		if not cmds.listConnections(a, t = 'mesh'):
			for m in cmds.listConnections(a, s = True):
				if m in allMat:
					err.append(m)
	if err:
		message = ''
		for e in err:
			message += (e+'\n')
		cmds.confirmDialog(m = 'Materials Unused: \n' + message)
	else:
		cmds.select(d=True)

	return err

#-----------------------------------------------Fixing Function--------------------------------------------------

def FixDeleteHistory(*argv):
	mel.eval('DeleteAllHistory')
	mel.eval('BakeAllNonDefHistory')
	# mel.eval('hyperShadePanelMenuCommand("hyperShadePanel1","deleteUnusedNodes")')
	cmds.button('FixDeleteHistory', e = True, l = 'Fixed')
	return True

def FixFreezeTransform(*argv):
	mel.eval('FreezeTransformations')
	cmds.button('FixFreezeTransform', e = True, l = 'Fixed')
	return True

def FixUnusedNode(*argv):
	mel.eval('MLdeleteUnused;')

def FixDefaultCameras(*argv):
	default_cameras = ["|persp", "|top", "|front", "|side"]
	cameras = [c.rsplit("|", 1)[0] for c in cmds.ls(type='camera', l = True)]
	err = list(set(cameras) - set(default_cameras))
	cmds.delete(err)
	
	cmds.button('FixDefaultCameras', e = True, l = 'Fixed')

	return True

def FixEmptyGroup(*argv):
	err = []

	mel.eval('source cleanUpScene;')
	mel.eval('deleteEmptyGroups;')

	cmds.button('FixEmptyGroup', e = True, l = 'Fixed')
	
	return err

def FixColorSet(*argv):
	list_cameras = cmds.listCameras()
	all_trans_in_scene = cmds.ls(sl=True, l=True)

	all_trans_in_scene = set(all_trans_in_scene) - set(list_cameras)

	all_meshes_in_scene = [t for t in all_trans_in_scene if cmds.listRelatives(t, shapes=True)]

	[deleteColorsetAction(t) for t in all_meshes_in_scene]
	
	cmds.button('FixColorSet', e = True, l = 'Fixed')

	return True

def FixMaliciousScriptNodes(*argv):
	# Remove non-ignored scriptNodes from current scene
	try:
		all_scripts = cmds.ls(type='script') or []
	except Exception:
		all_scripts = []
	targets = [n for n in all_scripts if n not in IGNORED_SCRIPTNODES]
	removed = 0
	if targets:
		try:
			cmds.delete(targets)
			removed = len(targets)
		except Exception:
			pass
	try:
		# Update button label if present in UI
		cmds.button('FixMaliciousScriptNodes', e=True, l='Fixed')
	except Exception:
		pass
	try:
		cmds.inViewMessage(amg='Removed {0} scriptNode(s) from scene'.format(removed), pos='topCenter', fade=True)
	except Exception:
		pass
	return True

def FixMayaMaliciousFiles(*argv):
	# Delete flagged malicious files and __pycache__ folders
	removed_files = 0
	removed_dirs = 0
	# Collect without popping the summary dialog
	issues = collect_maya_malicious_paths()
	for path in issues:
		try:
			if os.path.isdir(path):
				shutil.rmtree(path)
				removed_dirs += 1
			elif os.path.isfile(path):
				# For userSetup.py we may have flagged only when injected
				os.remove(path)
				removed_files += 1
		except Exception:
			pass
	try:
		cmds.button('FixMayaMaliciousFiles', e=True, l='Fixed')
	except Exception:
		pass
	try:
		cmds.inViewMessage(amg='Removed {0} file(s), {1} folder(s) from Maya scripts'.format(removed_files, removed_dirs), pos='topCenter', fade=True)
	except Exception:
		pass
	return True

#-----------------------------------------------CleanUp Function--------------------------------------------------

def TurnOffDoubleSide(*argv):
	'''Clean UP'''
	err = []
	for m in cmds.ls(type='mesh'):
		cmds.setAttr(m + '.doubleSided', 0)
	cmds.select(d=True)
	return err
			
def ScanCurrentScene(*argv):
	'''Clean UP'''
	err = []
	mel.eval('ScanSceneNow;')
	cmds.select(d=True)
	return err

def OpimizeScene(*argv):
	'''Clean UP'''
	err = []
	mel.eval('OptimizeScene;')
	cmds.select(d=True)
	return err

def CleanAttribute(*argv):
	'''Clean UP'''
	err = []
	sel = cmds.ls(sl = True, l = True)

	for s in sel:
		for attr in cmds.listAttr(s):
			if 'MaxHandle' in attr or 'mrFBX' in attr:
				cmds.deleteAttr(s, at = attr)
	cmds.select(d=True)
	return err
				
def RemoveAllNameSpace(*argv):
	'''Clean UP'''
	err = []
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
	return err

#-------------------------------------------------------UI-------------------------------------------------------

def camelToSpaces(stringList): 
	spacedList = []
	if type(stringList) == type([]):
		for text in stringList:
			result = [] 
			pos = 0 
			while pos < len(text): 
				if text[pos].isupper() and text[pos-1].islower(): 
					if pos-1 > 0 and text[pos-1] or pos-1 > 0 and pos+1 < len(text) and text[pos+1]: 
						result.append(' %s' % text[pos]) 
					else:
						result.append(text[pos]) 
				else: 
					result.append(text[pos]) 
				pos += 1        
			spacedList.append( ''.join(result) )
		return spacedList
		
	else:
		result = [] 
		pos = 0 
		while pos < len(stringList): 
			if stringList[pos].isupper() and stringList[pos-1].islower(): 
				if pos-1 > 0 and stringList[pos-1] or pos-1 > 0 and pos+1 < len(stringList) and stringList[pos+1]: 
					result.append(' %s' % stringList[pos])
				else:
					result.append(stringList[pos])
			else: 
				result.append(stringList[pos])
			pos += 1        
		spacedList.append( ''.join(result) )
		return spacedList[0]

def getAllCheckFunction(module):
	reload(module)
	name_func_tuples = inspect.getmembers(module, inspect.isfunction)
	functions = {}
	for name in name_func_tuples:
		if name[0] != ('GUI') and name[0] != 'reload' and name[0] != 'getAllCheckFunction' and name[0] != 'getAllFixFunction' and name[0] != 'camelToSpaces' and name[0] != 'executeSelectedFunction' and "Fix" not in name[0]:
			functions[name[0]] = [inspect.getdoc(name[1]), name[1]]
	return functions

def getAllFixFunction(module):
	reload(module)
	name_func_tuples = inspect.getmembers(module, inspect.isfunction)
	functions = {}
	for name in name_func_tuples:
		if name[0] != ('GUI') and name[0] != 'reload' and name[0] != 'getAllCheckFunction' and name[0] != 'getAllFixFunction' and name[0] != 'camelToSpaces' and name[0] != 'executeSelectedFunction' and "Fix" in name[0]:
			functions[name[0]] = [inspect.getdoc(name[1]), name[1]]
	return functions

def executeSelectedFunction(listFunction, *args):
	selectedObjects = cmds.ls(sl=True)
	for f in listFunction:
		cmds.select(selectedObjects, hi = True)
		err = f()
		if err != []:
			cmds.button(f.__name__, e = True, bgc = [0.35,0,0])
		else:
			cmds.button(f.__name__, e = True, bgc = [0.00,0.80,0.00])
	return listFunction