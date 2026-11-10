import re, os, copy, site, sys
import json
import math
from functools import partial
import tempfile
import itertools
from collections import OrderedDict as oDict
import maya.cmds as cmds
import maya.mel as mel
import maya.OpenMaya as OpenMaya
import maya.api.OpenMaya as omapi

try:
	# Python 3
	long = complex
	from importlib import reload
	from functools import reduce
	def itervalues(d):
		return iter(d.values())
	def iteritems(d):
		return iter(d.items())
	def iterkeys(d):
		return iter(d)
except:
	# Python 2
	def itervalues(d):
		return d.itervalues()
	def iteritems(d):
		return d.iteritems()
	def iterkeys(d):
		return d.iterkeys()

LOCAL_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace("\\", "/")  # HSTool root (self-locating)

site.addsitedir(LOCAL_PATH + "/Model_Tools/Scripts/Python")
import combine_detach_clone_port
reload(combine_detach_clone_port)
import circle_polygon_port
reload(circle_polygon_port)
import naming_tool
reload(naming_tool)
import selection_cleanup_port
reload(selection_cleanup_port)
import straight_line_tool
reload(straight_line_tool)
import slide_snap
reload(slide_snap)

#region SUPPORT FUNCTION

#region UI
def get_window_position_from_parent_window(current_window, parent_window):

	top_left = cmds.window(current_window, q=True, tlc=True)
	width_height = cmds.window(current_window, q=True, wh=True)

	top_left_parent = cmds.window(parent_window, q=True, tlc=True)
	width_height_parent = cmds.window(parent_window, q=True, wh=True)

	left_pos = top_left_parent[0] + (width_height[0] - width_height_parent[0]) / 2
	top_pos = top_left_parent[1] + (width_height[1] - width_height_parent[1]) / 2

	return [top_pos, left_pos]
#endregion

#region 3rdParty Tool

#region Line Tool
class new_vector(object):

	def __init__(self, *nums):
		if len(nums) == 1 and isinstance(nums[0], (list, tuple)) and len(nums[0]) == 3 and all((isinstance(i, (int, float, long)) for i in nums[0])):
			self.x = nums[0][0]
			self.y = nums[0][1]
			self.z = nums[0][2]
		elif len(nums) == 3 and all((isinstance(i, (int, long, float)) for i in nums)):
			self.x = nums[0]
			self.y = nums[1]
			self.z = nums[2]
		elif len(nums) == 0:
			self.x = 0
			self.y = 0
			self.z = 0

	def __str__(self):
		return '<<%s,%s,%s>>' % (self.x, self.y, self.z)

	__repr__ = __str__

	def __add__(self, other):
		if isinstance(other, self.__class__):
			return self.__class__(self.x + other.x, self.y + other.y, self.z + other.z)
		if isinstance(other, (tuple, list)) and len(other) == 3 and all((isinstance(i, (int, float, long)) for i in other)):
			return self.__class__(self.x + other[0], self.y + other[1], self.z + other[2])
		

	def __iadd__(self, other):
		if isinstance(other, self.__class__):
			self.x += other.x
			self.y += other.y
			self.z += other.z
			return self
		if isinstance(other, (tuple, list)) and len(other) == 3 and all((isinstance(i, (int, float, long)) for i in other)):
			self.x += other[0]
			self.y += other[1]
			self.z += other[2]
			return self
		

	__radd__ = __add__

	def __sub__(self, other):
		if isinstance(other, self.__class__):
			return self.__class__(self.x - other.x, self.y - other.y, self.z - other.z)
		if isinstance(other, (tuple, list)) and len(other) == 3 and all((isinstance(i, (int, float, long)) for i in other)):
			return self.__class__(self.x - other[0], self.y - other[1], self.z - other[2])
		

	def __isub__(self, other):
		if isinstance(other, self.__class__):
			self.x -= other.x
			self.y -= other.y
			self.z -= other.z
			return self
		if isinstance(other, (tuple, list)) and len(other) == 3 and all((isinstance(i, (int, float, long)) for i in other)):
			self.x -= other[0]
			self.y -= other[1]
			self.z -= other[2]
			return self
		

	__rsub__ = __sub__

	def __mul__(self, num):
		if isinstance(num, (int, long, float)):
			return self.__class__(self.x * num, self.y * num, self.z * num)
		

	def __imul__(self, num):
		if isinstance(num, (int, long, float)):
			self.x *= num
			self.y *= num
			self.z *= num
			return self
		

	__rmul__ = __mul__

	def __div__(self, num):
		if isinstance(num, (int, long, float)):
			return self.__class__(self.x / float(num), self.y / float(num), self.z / float(num))
		

	def __idiv__(self, num):
		if isinstance(num, (int, long, float)):
			self.x /= float(num)
			self.y /= float(num)
			self.z /= float(num)
			return self
		

	def __nonzero__(self):
		return self.x or self.y or self.z

	def __eq__(self, other):
		if self.x == other.x and self.y == other.y and self.z == other.z:
			return True
		return False

	def __neg__(self):
		return self * -1

	def module(self):
		return (self.x ** 2 + self.y ** 2 + self.z ** 2) ** 0.5

	def distance(self, *nums):
		if len(nums) == 1 and isinstance(nums[0], (list, tuple)) and len(nums[0]) == 3 and all((isinstance(i, (int, float, long)) for i in nums[0])):
			return ((self.x - nums[0][0]) ** 2 + (self.y - nums[0][2]) ** 2 + (self.z - nums[0][2]) ** 2) ** 0.5
		if len(nums) == 1 and isinstance(nums[0], self.__class__):
			return ((self.x - nums[0].x) ** 2 + (self.y - nums[0].y) ** 2 + (self.z - nums[0].z) ** 2) ** 0.5
		if len(nums) == 3 and all((isinstance(i, (int, long, float)) for i in nums)):
			return ((self.x - nums[0]) ** 2 + (self.y - nums[1]) ** 2 + (self.z - nums[2]) ** 2) ** 0.5
		

	def toList(self):
		return [self.x, self.y, self.z]

	def toTuple(self):
		return (self.x, self.y, self.z)

	def normalize(self):
		m = self.module()
		self.x /= m
		self.y /= m
		self.z /= m
		return self

	@staticmethod
	def center(*vectors):
		if vectors:
			sum = (0, 0, 0)
			for i in vectors:
				sum += i
			lenVec = len(vectors)
			# return sum / len(vectors)
			return new_vector([sum.x / lenVec , sum.y/lenVec, sum.z/lenVec])

	@staticmethod
	def vector_list(seq = []):
		if seq and len(seq) % 3 == 0:
			return [ new_vector(seq[i:i + 3]) for i in range(0, len(seq), 3) ]

def get_mesh():
	sel = cmds.ls(sl=True) + cmds.ls(hl=True)
	mesh = None
	if sel:
		if cmds.nodeType(sel[-1]) == 'transform':
			if cmds.nodeType(cmds.listRelatives(sel[-1], c=True)[0]) == 'mesh':
				mesh = sel[-1]
		elif cmds.nodeType(sel[-1]) == 'mesh':
			if '.' in sel[-1]:
				mesh = sel[-1].split('.')[0]
			else:
				mesh = cmds.listRelatives(sel[-1], p=True, type='transform')[0]
	return mesh

def get_mesh_list():
	mesh_list = []
	sel = cmds.ls(sl=True) + cmds.ls(hl=True)
	if sel:
		for each in sel:
			if cmds.nodeType(each) == 'transform':
				if cmds.nodeType(cmds.listRelatives(each, c=True)[0]) == 'mesh' and each not in mesh_list:
					mesh_list.append(each)
			elif cmds.nodeType(each) == 'mesh':
				if '.' in each:
					mesh = each.split('.')[0]
					if mesh not in mesh_list:
						mesh_list.append(mesh)
				else:
					mesh = cmds.listRelatives(each, p=True, type='transform')[0]
					if mesh not in mesh_list:
						mesh_list.append(mesh)
	return mesh_list

def delete_history():
	mel.eval("DeleteHistory;")

def get_component_name(comp_name):
	return int(comp_name.split('[')[1].split(']')[0])

def mode_to_character(mesh, mode, num):
	modeDict = {'face': 'f',
	 'edge': 'e',
	 'vtx': 'vtx'}
	return '%s.%s[%s]' % (mesh, modeDict[mode], num)

def get_vertex_edge_group(selEdges, mesh = None, returnMode = 'vtx', breakVtxs = None):
	if breakVtxs:
		breakVtxs = [get_component_name(vtx) for vtx in breakVtxs ]
	if selEdges and len(selEdges) > 1:
		if not mesh:
			mesh = get_mesh()
		e2vInfos = cmds.polyInfo(selEdges, ev=True)
		e2vDict = {}
		for info in e2vInfos:
			evList = [ int(i) for i in re.findall('\\d+', info) ]
			e2vDict.update(dict([(evList[0], evList[1:])]))

		openEdgesGrps = []
		closeEdgesGrps = []
		openVtxsGrps = []
		closeVtxsGrps = []
		while True:
			try:
				startEdge, startVtxs = e2vDict.popitem()
			except:
				break

			edgesGrp = [startEdge]
			vtxsGrp = []
			num = 0
			for vtx in startVtxs:
				curVtx = vtx
				while True:
					if num == 0:
						vtxsGrp.append(curVtx)
					else:
						vtxsGrp.insert(0, curVtx)
					if breakVtxs and curVtx in breakVtxs:
						break
					nextEdges = []
					for k in e2vDict:
						if curVtx in e2vDict[k]:
							nextEdges.append(k)

					if nextEdges:
						if len(nextEdges) == 1:
							if num == 0:
								edgesGrp.append(nextEdges[0])
							else:
								edgesGrp.insert(0, nextEdges[0])
							nextVtxs = e2vDict[nextEdges[0]]
							curVtx = [ vtx for vtx in nextVtxs if vtx != curVtx ][0]
							e2vDict.pop(nextEdges[0])
						else:
							return False
					else:
						break

				num += 1

			if len(vtxsGrp) >= 3:
				edgesGrp = [mode_to_character(mesh, 'edge', num) for num in edgesGrp ]
				vtxsGrp = [mode_to_character(mesh, 'vtx', num) for num in vtxsGrp ]
				if vtxsGrp[0] == vtxsGrp[-1]:
					closeEdgesGrps.append(edgesGrp)
					closeVtxsGrps.append(vtxsGrp[:-1])
				else:
					openEdgesGrps.append(edgesGrp)
					openVtxsGrps.append(vtxsGrp)

		if returnMode == 'vtx':
			return (openVtxsGrps, closeVtxsGrps)
		if returnMode == 'edge':
			return (openEdgesGrps, closeEdgesGrps)
		if returnMode == 'vtx_edge':
			return (openVtxsGrps,
			 closeVtxsGrps,
			 openEdgesGrps,
			 closeEdgesGrps)

def shrinkwrap_vertex(target, mesh, vtxNum, allVtxIds, progressBar = False):
	if progressBar:
		gMainProgressBar = mel.eval('$tmp=$gMainProgressBar')
		cmds.progressBar(gMainProgressBar, edit=True, beginProgress=True, isInterruptable=True, status='ShrinkWrapping...', maxValue=vtxNum)
	for vtxId in allVtxIds:
		if progressBar and cmds.progressBar(gMainProgressBar, query=True, isCancelled=True):
			break
		vtx = mode_to_character(mesh, 'vtx', vtxId)
		pos = cmds.xform(vtx, q=True, ws=True, t=True)
		null = cmds.group(w=True, em=True)
		cmds.xform(null, ws=True, t=pos)
		cmds.geometryConstraint(target, null)
		nPos = cmds.xform(null, q=True, ws=True, t=True)
		cmds.xform(vtx, ws=True, t=nPos)
		cmds.delete(null)
		if progressBar:
			cmds.progressBar(gMainProgressBar, edit=True, step=1)

	if progressBar:
		cmds.progressBar(gMainProgressBar, edit=True, endProgress=True)

def shrinkwrap_face(target, mesh, faceNum, allFaceIdsSet_1, progressBar = False):
	if progressBar:
		gMainProgressBar = mel.eval('$tmp=$gMainProgressBar')
		cmds.progressBar(gMainProgressBar, edit=True, beginProgress=True, isInterruptable=True, status='shrinkWrapping...', maxValue=faceNum)
	while allFaceIdsSet_1:
		if progressBar and cmds.progressBar(gMainProgressBar, query=True, isCancelled=True):
			break
		allFaceIdsSet_2 = copy.deepcopy(allFaceIdsSet_1)
		while allFaceIdsSet_2:
			if progressBar and cmds.progressBar(gMainProgressBar, query=True, isCancelled=True):
				break
			curFaceId = allFaceIdsSet_2.pop()
			allFaceIdsSet_1.remove(curFaceId)
			curFace = mesh + '.f[%d]' % curFaceId
			vector_list = new_vector.vector_list(cmds.xform(curFace, q=True, ws=True, t=True))
			center_pos = new_vector.center(*vector_list)
			null = cmds.group(w=True, em=True)
			cmds.xform(null, ws=True, t=center_pos.toTuple())
			cmds.geometryConstraint(target, null)
			nPos = new_vector(cmds.xform(null, q=True, ws=True, t=True))
			cmds.delete(null)
			cmds.polyMoveFacet(curFace, t=(nPos - center_pos).toTuple())
			toVtxs = cmds.polyListComponentConversion(curFace, ff=True, tv=True)
			toFaces = cmds.filterExpand(cmds.polyListComponentConversion(toVtxs, fv=True, tf=True), sm=34)
			allFaceIdsSet_2 -= set([get_component_name(face) for face in toFaces ])
			delete_history()
			if progressBar:
				cmds.progressBar(gMainProgressBar, edit=True, step=1)

	if progressBar:
		cmds.progressBar(gMainProgressBar, edit=True, endProgress=True)

def shrinkwrap_border_edge(target, mesh, selBorderEdges, progressBar = False):
	if progressBar:
		gMainProgressBar = mel.eval('$tmp=$gMainProgressBar')
		cmds.progressBar(gMainProgressBar, edit=True, beginProgress=True, isInterruptable=True, status='shrinkWrapping...', maxValue=len(selBorderEdges))
	allEdgeSet_1 = set(selBorderEdges)
	while allEdgeSet_1:
		if progressBar and cmds.progressBar(gMainProgressBar, query=True, isCancelled=True):
			break
		allEdgeSet_2 = copy.deepcopy(allEdgeSet_1)
		while allEdgeSet_2:
			if progressBar and cmds.progressBar(gMainProgressBar, query=True, isCancelled=True):
				break
			curEdge = allEdgeSet_2.pop()
			allEdgeSet_1.remove(curEdge)
			vector_list = new_vector.vector_list(cmds.xform(curEdge, q=True, ws=True, t=True))
			center_pos = new_vector.center(*vector_list)
			null = cmds.group(w=True, em=True)
			cmds.xform(null, ws=True, t=center_pos.toTuple())
			cmds.geometryConstraint(target, null)
			nPos = new_vector(cmds.xform(null, q=True, ws=True, t=True))
			cmds.delete(null)
			cmds.polyMoveEdge(curEdge, t=(nPos - center_pos).toTuple())
			toVtxs = cmds.polyListComponentConversion(curEdge, fe=True, tv=True)
			toEdges = cmds.filterExpand(cmds.polyListComponentConversion(toVtxs, fv=True, te=True), sm=32)
			allEdgeSet_2 -= set(toEdges)
			delete_history()
			if progressBar:
				cmds.progressBar(gMainProgressBar, edit=True, step=1)

	if progressBar:
		cmds.progressBar(gMainProgressBar, edit=True, endProgress=True)

def build_curve_for_average_line(vtxGrp, close, mesh, even, smooth, step, axis):
	vtxNum = len(vtxGrp)
	vtxPosGroup = [new_vector(cmds.xform(vtx, q=True, ws=True, t=True)) for vtx in vtxGrp ]
	vtxPosTupleGroup = [ vec.toTuple() for vec in vtxPosGroup ]
	center_pos = new_vector.center(*vtxPosGroup)
	distGroup = [ vec.distance(center_pos) for vec in vtxPosGroup ]
	if close:
		if axis == 'Auto':
			firstId = distGroup.index(min(distGroup))
		else:
			if axis == 'YZ':
				pos_axis_grp = [ abs(vec.x - center_pos.x) for vec in vtxPosGroup ]
			elif axis == 'XZ':
				pos_axis_grp = [ abs(vec.y - center_pos.y) for vec in vtxPosGroup ]
			elif axis == 'XY':
				pos_axis_grp = [ abs(vec.z - center_pos.z) for vec in vtxPosGroup ]
			firstId = pos_axis_grp.index(min(pos_axis_grp))
	else:
		firstId = 0
	if not close:
		span = vtxNum - 1
		averageVtxs = vtxGrp[1:-1]
		curve = cmds.curve(p=vtxPosTupleGroup, d=2 if vtxNum <= 3 else 3) if smooth else cmds.curve(ep=vtxPosTupleGroup, d=1)
	else:
		span = vtxNum
		averageVtxs = vtxGrp
		curve = cmds.circle(s=vtxNum, c=(0, 0, 0), d=3 if smooth else 1, ch=False)[0]
		for i in range(vtxNum):
			cmds.xform(curve + '.%s[%d]' % ('cv' if smooth else 'ep', (i + 1) % vtxNum if smooth else i), ws=True, t=vtxPosTupleGroup[(i + firstId) % vtxNum])

		if not smooth:
			cmds.xform(curve + '.ep[%d]' % vtxNum, ws=True, t=vtxPosTupleGroup[firstId])
	if even:
		curve = cmds.rebuildCurve(curve, s=span, d=3 if smooth or vtxNum <= 3 and not close else 1, ch=False)[0]
		vtxRange = range(1, vtxNum - 1) if not close else range(vtxNum)
		for i in vtxRange:
			cmds.xform(vtxGrp[(i + firstId) % vtxNum], ws=True, t=cmds.xform('%s.ep[%s]' % (curve, i), q=True, ws=True, t=True))

	else:
		for i in range(step):
			cmds.polyAverageVertex(averageVtxs)
			shrinkwrap_vertex(curve, mesh, len(averageVtxs), [get_component_name(vtx) for vtx in averageVtxs ])
			delete_history()
	cmds.delete(curve)

def move_vetex_group(vtxGrp, even):
	if not even:
		oldPosGroup = [new_vector(cmds.xform(vtx, q=True, os=True, t=True)) for vtx in vtxGrp ]
		edgeLenGroup = [ oldPosGroup[i].distance(oldPosGroup[i - 1]) for i in range(1, len(oldPosGroup)) ]
		oldLen = sum(edgeLenGroup)
		ratios = [i / oldLen for i in edgeLenGroup ]
		for i in range(1, len(vtxGrp) - 1):
			pos = oldPosGroup[0] + (oldPosGroup[-1] - oldPosGroup[0]) * sum(ratios[:i])
			cmds.xform(vtxGrp[i], os=True, t=pos.toTuple())

	else:
		div = len(vtxGrp) - 1
		startPos = new_vector(cmds.xform(vtxGrp[0], q=True, os=True, t=True))
		endPos = new_vector(cmds.xform(vtxGrp[-1], q=True, os=True, t=True))
		for i in range(1, len(vtxGrp)):
			pos = startPos + (endPos - startPos) / div * i
			cmds.xform(vtxGrp[i], os=True, t=pos.toTuple())

def add_wrap_target(*args):
	sel = cmds.ls(sl=True)
	target = None
	if sel:
		if cmds.nodeType(sel[0]) == 'transform':
			shape = cmds.listRelatives(sel[0], s=True)[0]
			if cmds.objectType(shape, isa='geometryShape'):
				target = sel[0]
			else:
				target = None
		elif cmds.objectType(sel[0], isa='geometryShape') and '.' not in sel[0]:
			transform = cmds.listRelatives(sel[0], p=True)[0]
			target = transform
	if target:
		cmds.textFieldButtonGrp('shrinkwrap_tfbg', e=True, tx=target)
		cmds.button('shrinkwrap_btn', e=True, en=True)
	else:
		cmds.textFieldButtonGrp('shrinkwrap_tfbg', e=True, tx='')
		cmds.button('shrinkwrap_btn', e=True, en=False)
	cmds.refresh()
	shrinkwrapUI_popup_menu()

def shrinkwrapUI_popup_menu():
	target = cmds.textFieldButtonGrp('shrinkwrap_tfbg', q=True, tx=True)
	if target and cmds.objExists(target):
		cmds.popupMenu('shrinkWrapUI_popupMenu', p='shrinkwrap_tfbg')
		cmds.menuItem(l='Enable', cb=True, c=enable_shrinkwrap)
		cmds.menuItem(d=True)
		cmds.menuItem(l='Select Target', c=selected_wrap_target)
		cmds.menuItem(l='Remove Target', c=remove_wrap_target)
		cmds.menuItem(d=True)
		cmds.menuItem(l='Make Target Live', c="cmds.makeLive('%s')" % cmds.listRelatives(target, s=True)[0])
		cmds.menuItem(l='Turn Off Live', c='cmds.makeLive(n=True)')
		cmds.menuItem(d=True)
		cmds.menuItem(l='Target Visibility', cb=cmds.getAttr(target + '.v'), c=toggle_wrap_target_vis)
		targetShape = cmds.listRelatives(target, s=True)[0]
		curShaderGrp = cmds.listConnections(targetShape, t='shadingEngine')
		if curShaderGrp:
			curShader = cmds.listConnections(curShaderGrp[0], t='lambert')
			if curShader:
				curShader = curShader[0]
				transparency = any(cmds.getAttr(curShader + '.transparency')[0])
		cmds.menuItem(l='Target Transparency', cb=transparency, c=toggle_wrap_target_transpency)
		cmds.radioMenuItemCollection(p='shrinkWrapUI_popupMenu')
		cmds.menuItem(l='Normal', rb=True if not cmds.getAttr(target + '.overrideEnabled') or cmds.getAttr('%s.overrideDisplayType' % target) == 0 else False, c=lambda *args: toggle_wrap_target_override(mode=0))
		cmds.menuItem(l='Template', rb=True if cmds.getAttr('%s.overrideDisplayType' % target) == 1 and cmds.getAttr(target + '.overrideEnabled') else False, c=lambda *args: toggle_wrap_target_override(mode=1))
		cmds.menuItem(l='Reference', rb=True if cmds.getAttr('%s.overrideDisplayType' % target) == 2 and cmds.getAttr(target + '.overrideEnabled') else False, c=lambda *args: toggle_wrap_target_override(mode=2))

def enable_shrinkwrap(*args):
	state = cmds.button('shrinkwrap_btn', q=True, en=True)
	cmds.button('shrinkwrap_btn', e=True, en=not state)

def selected_wrap_target(*args):
	target = cmds.textFieldButtonGrp('shrinkwrap_tfbg', q=True, tx=True)
	if cmds.objExists(target):
		cmds.select(target)
	refresh_wrap_target()

def refresh_wrap_target():
	target = cmds.textFieldButtonGrp('shrinkwrap_tfbg', q=True, tx=True)
	if not cmds.objExists(target):
		remove_wrap_target()
		cmds.confirmDialog(t = 'Notification', m = 'Not exists!')

def remove_wrap_target(*args):
	cmds.textFieldButtonGrp('shrinkwrap_tfbg', e=True, tx='')
	cmds.button('shrinkwrap_btn', e=True, en=False)
	shrinkwrapUI_popup_menu()

def toggle_wrap_target_vis(*args):
	target = cmds.textFieldButtonGrp('shrinkwrap_tfbg', q=True, tx=True)
	if cmds.objExists(target):
		state = cmds.getAttr(target + '.v')
		cmds.setAttr(target + '.v', not state)
	refresh_wrap_target()

def toggle_wrap_target_transpency(*args):
	target = cmds.textFieldButtonGrp('shrinkwrap_tfbg', q=True, tx=True)
	if cmds.objExists(target):
		targetShape = cmds.listRelatives(target, s=True)[0]
		curShaderGrp = cmds.listConnections(targetShape, t='shadingEngine')
		if curShaderGrp:
			curShader = cmds.listConnections(curShaderGrp[0], t='lambert')
			if curShader:
				curShader = curShader[0]
				transparency = any(cmds.getAttr(curShader + '.transparency')[0])
				if transparency:
					cmds.setAttr(curShader + '.transparency', 0, 0, 0)
				else:
					cmds.setAttr(curShader + '.transparency', 0.9, 0.9, 0.9)
	refresh_wrap_target()

def toggle_wrap_target_override(mode = 0):
	target = cmds.textFieldButtonGrp('shrinkwrap_tfbg', q=True, tx=True)
	if cmds.objExists(target):
		state = cmds.getAttr(target + '.overrideEnabled')
		if not state:
			cmds.setAttr(target + '.overrideEnabled', not state)
		cmds.setAttr(target + '.overrideDisplayType', mode)
	refresh_wrap_target()

def selected_mode(returnMode = 'vtx', expand = True):
	selVtxs = cmds.filterExpand(sm=31, expand=expand)
	selUVs = cmds.filterExpand(sm=35, expand=expand)
	selEdges = cmds.filterExpand(sm=32, expand=expand)
	selFaces = cmds.filterExpand(sm=34, expand=expand)
	numList = [ bool(sel) for sel in (selVtxs,
	 selUVs,
	 selEdges,
	 selFaces) ]
	if sum(numList) == 0:
		return False
	if sum(numList) > 1:
		selMode = 'meshComponents'
	elif sum(numList) == 1:
		if selVtxs:
			selMode = 'vertex'
		elif selUVs:
			selMode = 'puv'
		elif selEdges:
			selMode = 'edge'
		else:
			selMode = 'facet'
	if returnMode == 'selModeOnly':
		return selMode
	comps = []
	if selVtxs:
		comps += selVtxs
	if selUVs:
		comps += selUVs
	if selEdges:
		comps += selEdges
	if selFaces:
		comps += selFaces
	if returnMode == 'vtx':
		vtxs = []
		if selVtxs:
			vtxs += selVtxs
		if selUVs:
			vtxs += cmds.filterExpand(cmds.polyListComponentConversion(selUVs, fuv=True, tv=True), sm=31)
		if selEdges:
			vtxs += cmds.filterExpand(cmds.polyListComponentConversion(selEdges, fe=True, tv=True), sm=31)
		if selFaces:
			vtxs += cmds.filterExpand(cmds.polyListComponentConversion(selFaces, ff=True, tv=True), sm=31)
		return (comps, vtxs, selMode)
	if returnMode == 'puv':
		uvs = []
		if selUVs:
			uvs += selUVs
		if selVtxs:
			uvs += cmds.filterExpand(cmds.polyListComponentConversion(selVtxs, fv=True, tuv=True), sm=35)
		if selEdges:
			uvs += cmds.filterExpand(cmds.polyListComponentConversion(selEdges, fe=True, tuv=True), sm=35)
		if selFaces:
			uvs += cmds.filterExpand(cmds.polyListComponentConversion(selFaces, ff=True, tuv=True), sm=35)
		return (comps, uvs, selMode)
	if returnMode == 'edge':
		edges = []
		if selVtxs:
			edges += cmds.filterExpand(cmds.polyListComponentConversion(selVtxs, fv=True, te=True), sm=32)
		if selUVs:
			edges += cmds.filterExpand(cmds.polyListComponentConversion(selUVs, fuv=True, te=True), sm=32)
		if selEdges:
			edges += selEdges
		if selFaces:
			edges += cmds.filterExpand(cmds.polyListComponentConversion(selFaces, ff=True, te=True), sm=32)
		return (comps, edges, selMode)
	if returnMode == 'face':
		faces = []
		if selVtxs:
			faces += cmds.filterExpand(cmds.polyListComponentConversion(selVtxs, fv=True, tf=True), sm=34)
		if selUVs:
			faces += cmds.filterExpand(cmds.polyListComponentConversion(selUVs, fuv=True, tf=True), sm=34)
		if selEdges:
			faces += cmds.filterExpand(cmds.polyListComponentConversion(selEdges, fe=True, tf=True), sm=34)
		if selFaces:
			faces += selFaces
		return (comps, faces, selMode)

def border_edge(edge):
	e2fInfo = cmds.polyInfo(edge, ef=True)[0]
	if len(re.findall('\\d+', e2fInfo)) == 2:
		return True
	else:
		return False

def open_edge(mesh):
	openEdgeIds = []
	edgeNum = cmds.polyEvaluate(mesh, e=True)
	infos = iter(cmds.polyInfo('%s.e[0:%s]' % (mesh, edgeNum - 1), ef=True))
	for info in infos:
		nums = re.findall('\\d+', info)
		if len(nums) == 2:
			openEdgeIds.append(nums[0])
	if openEdgeIds:
		return ['%s.e[%s]' % (mesh, edgeId) for edgeId in openEdgeIds]

def shrinkwrap(*args):
	refresh_wrap_target()
	target = cmds.textFieldButtonGrp('shrinkwrap_tfbg', q=True, tx=True)
	if target and cmds.objExists(target):
		mesh = get_mesh()
		if mesh and mesh != target:
			delete_history()
			shrinkMode = cmds.radioButtonGrp('shrinkwrap_rbg', q=True, sl=True)
			selComps = selected_mode('selModeOnly')
			if selComps:
				if shrinkMode == 1:
					selComps, selVtxs, selMode = selected_mode('vtx')
					vtxNum = len(selVtxs)
					allVtxIds = [get_component_name(vtx) for vtx in selVtxs ]
				elif shrinkMode == 2:
					selComps, selFaces, selMode = selected_mode('face')
					faceNum = len(selFaces)
					allFaceIdsSet_1 = set([get_component_name(face) for face in selFaces ])
			else:
				msg = cmds.confirmDialog(t='Warnning!', m='Will ShrinkWrap the whole Mesh, are you sure?', b=['OK', 'Cancel'], db='OK', ds='Cancel', cb='Cancel')
				if msg == 'OK':
					if shrinkMode == 1:
						selComps, selMode = (None, 'mesh')
						vtxNum = cmds.polyEvaluate(mesh, v=True)
						allVtxIds = range(vtxNum)
					elif shrinkMode == 2:
						selComps, selMode = (None, 'mesh')
						faceNum = cmds.polyEvaluate(mesh, f=True)
						allFaceIdsSet_1 = set(range(faceNum))
				else:
					return False
			targetFaceNum = cmds.polyEvaluate(target, f=True)
			disableUndo = False
			if targetFaceNum > 5000 and (shrinkMode == 1 and vtxNum > 500 or shrinkMode == 2 and faceNum > 500):
				disableUndo = True
				cmds.undoInfo(swf=False)
			if shrinkMode == 1:
				shrinkwrap_vertex(target, mesh, vtxNum, allVtxIds, progressBar=True)
			elif shrinkMode == 2:
				shrinkwrap_face(target, mesh, faceNum, allFaceIdsSet_1, progressBar=True)
				fixBorder = cmds.checkBox('shrinkwrap_border_cb', q=True, v=True)
				if fixBorder:
					if selComps:
						selEdges = selected_mode('edge')[1]
						selBorderEdges = [edge for edge in selEdges if border_edge(edge)]
					else:
						selBorderEdges = open_edge(mesh)
					if selBorderEdges:
						shrinkwrap_border_edge(target, mesh, selBorderEdges, progressBar=True)
			if selMode == 'mesh':
				cmds.select(mesh)
			else:
				mel.eval('doMenuComponentSelection("%s", "%s")' % (mesh, selMode))
				cmds.select(selComps)
			if disableUndo:
				cmds.undoInfo(swf=True)

# def straighten_line(*args):
# 	selEdges = cmds.filterExpand(sm=32)
# 	selVtxs = cmds.filterExpand(sm=31)
# 	if selEdges and len(selEdges) > 1:
# 		vtxGrps = get_vertex_edge_group(selEdges, breakVtxs=selVtxs)
# 		if vtxGrps:
# 			openVtxGrps = vtxGrps[0]
# 			if openVtxGrps:
# 				grpsNum = len(openVtxGrps)
# 				mesh = get_mesh()
# 				even = cmds.checkBox('straighten_even_cb', q = True, v = True)
# 				gMainProgressBar = mel.eval('$tmp=$gMainProgressBar')
# 				cmds.progressBar(gMainProgressBar, edit=True, beginProgress=True, isInterruptable=True, status='Straightening...', maxValue=grpsNum)
# 				for vtxGrp in openVtxGrps:
# 					if cmds.progressBar(gMainProgressBar, query=True, isCancelled=True):
# 						break
# 					move_vetex_group(vtxGrp, even)
# 					cmds.progressBar(gMainProgressBar, edit=True, step=1)

# 				mel.eval('doMenuComponentSelection("%s", "edge")' % mesh)
# 				cmds.select(selEdges)
# 				if selVtxs:
# 					cmds.select(selVtxs, add=True)
# 				cmds.progressBar(gMainProgressBar, edit=True, endProgress=True)
# 				delete_history()

def average_line(*args):
	selected_edges = cmds.filterExpand(sm=32)
	selected_vertices = cmds.filterExpand(sm=31)
	if selected_edges and len(selected_edges) > 1:
		vtxGrps = get_vertex_edge_group(selected_edges, breakVtxs=selected_vertices)
		if vtxGrps:
			even = cmds.checkBox('averageLine_even_cb', q=True, v=True)
			keepShape = cmds.checkBox('averageLine_keepshape_cb', q=True, v=True)
			smooth = cmds.checkBox('averageLine_smooth_cb', q=True, v=True)
			openVtxGrps, closeVtxGrps = vtxGrps
			allVtxGrps = openVtxGrps + closeVtxGrps
			grpsNum = len(allVtxGrps)
			mesh = get_mesh()
			if keepShape:
				target = None
				# if cmds.button('shrinkwrap_btn', q=True, en=True):
				# 	target = cmds.textFieldButtonGrp('shrinkwrap_tfbg', q=True, tx=True)
				# 	if target:
				# 		if cmds.objExists(target):
				# 			targetMesh = target
				# 		else:
				# 			target = None
				if not target:
					targetMesh = cmds.duplicate(mesh)[0]
					cmds.setAttr(targetMesh + '.v', False)
			alignDict = {1: 'YZ',
			 2: 'XZ',
			 3: 'XY',
			 4: 'Auto'}
			align = alignDict[cmds.radioButtonGrp('averageLine_align_rbg', q=True, sl=True)]
			step = cmds.intSliderGrp('averageLine_step_sl', q=True, v=True)
			gMainProgressBar = mel.eval('$tmp=$gMainProgressBar')
			cmds.progressBar(gMainProgressBar, edit=True, beginProgress=True, isInterruptable=True, status='Averaging...', maxValue=grpsNum)
			for vtxGrp in allVtxGrps:
				if cmds.progressBar(gMainProgressBar, query=True, isCancelled=True):
					break
				build_curve_for_average_line(vtxGrp, vtxGrp in closeVtxGrps, mesh, even, smooth, step, align)
				if keepShape:
					shrinkwrap_vertex(targetMesh, mesh, len(vtxGrp), [get_component_name(vtx) for vtx in vtxGrp ])
				cmds.progressBar(gMainProgressBar, edit=True, step=1)

			if keepShape and not target:
				cmds.delete(targetMesh)
			mel.eval('doMenuComponentSelection("%s", "edge")' % mesh)
			cmds.select(selected_edges)
			if selected_vertices:
				cmds.select(selected_vertices, add=True)
			cmds.progressBar(gMainProgressBar, edit=True, endProgress=True)
			delete_history()
#endregion

#region Curve Deform
def arcDone(*args):
	global storeEdge
	global currentArcCurve
	if cmds.objExists('arcCurve*'):
		arcCurveList = cmds.ls( "arcCurve*", transforms =1  )
		a = arcCurveList[0]
		for a in arcCurveList:
			if 'BaseWire' not in a:
				shapeNode = cmds.listRelatives(a, fullPath=True )
				hist = cmds.listConnections(cmds.listConnections(shapeNode[0],sh=1, d=1 ) ,d=1 ,sh=1)
				cmds.delete(hist,ch=1)
		cmds.delete('arcCurve*')
	if len(currentArcCurve)>0:
		if cmds.objExists(currentArcCurve):
			shapeNode = cmds.listRelatives(currentArcCurve, fullPath=True )
			hist = cmds.listConnections(cmds.listConnections(shapeNode[0],sh=1, d=1 ) ,d=1 ,sh=1)
			cmds.delete(hist,ch=1)
	if cmds.objExists(currentArcCurve):
		cmds.select(currentArcCurve)
	cmds.select(storeEdge,add=1)
	if cmds.objExists(currentArcCurve + 'BaseWire'):
		cmds.delete(currentArcCurve + 'BaseWire')

def arcEdgeLoop(*args):
	global storeEdge
	global currentArcCurve
	currentDropOff = cmds.floatSliderGrp('dropOffSlider' ,q=1,v=1)
	snapCheck = cmds.checkBox('snapCurve',q = 1 ,v = 1)
	goEven = cmds.checkBox('evenSpace', q=1 ,v = 1)
	conP = cmds.intSliderGrp('CPSlider',q=1 , v = True )
	curveT = cmds.radioButtonGrp('curveType_rbg', q=1, sl=1)
	goArc = cmds.checkBox('makeArc', q=1 ,v = 1)
	cClean = cmds.checkBox('cleanCurve', q=1 ,v = 1)
	selEdge = cmds.filterExpand(expand=True ,sm=32)
	selCurve = cmds.filterExpand(expand=True ,sm=9)
	if selCurve:
		if len(selEdge)>0 and len(selCurve)== 1:
			storeEdge = selEdge
			cmds.select(selCurve,d=1)
			selMeshForDeformer = cmds.ls(sl=1,o=1)
			getCircleState,listVtx = vtxLoopOrderCheck()
			newCurve = cmds.duplicate(selCurve[0], rr=1)
			cmds.rename(newCurve[0],'newsnapCurve')
			currentArcCurve = 'newsnapCurve'
			cmds.rebuildCurve(currentArcCurve,ch=1, rpo=1, rt=0, end=1, kr=0, kcp=0, kep=1, kt=0, s = 100, d=1, tol=0.01)
			#check tip order
			curveTip = cmds.pointOnCurve(currentArcCurve , pr = 0, p=1)
			tipA = cmds.pointPosition(listVtx[0],w=1)
			tipB = cmds.pointPosition(listVtx[-1],w=1)
			distA = math.sqrt( ((tipA[0] - curveTip[0])**2)  + ((tipA[1] - curveTip[1])**2)  + ((tipA[2] - curveTip[2])**2) )
			distB = math.sqrt( ((tipB[0] - curveTip[0])**2)  + ((tipB[1] - curveTip[1])**2)  + ((tipB[2] - curveTip[2])**2) )
			if distA > distB:
				listVtx.reverse()
			#snap to curve
			if goEven == 1:
				for q in range(len(selEdge)+1):
					if q == 0:
						pp = cmds.pointOnCurve(currentArcCurve , pr = 0, p=1)
						cmds.move( pp[0], pp[1], pp[2],listVtx[q] , a =True, ws=True)
					else:
						pp = cmds.pointOnCurve(currentArcCurve , pr = (1.0/len(selEdge)*q), p=1)
						cmds.move( pp[0], pp[1], pp[2],listVtx[q] , a =True, ws=True)
			else:
				sum = 0
				totalEdgeLoopLength = 0
				Llist = []
				uList = []
				pList = []
				for i in range(len(listVtx)-1):
					pA = cmds.pointPosition(listVtx[i], w =1)
					pB = cmds.pointPosition(listVtx[i+1], w =1)
					checkDistance = math.sqrt( ((pA[0] - pB[0])**2)  + ((pA[1] - pB[1])**2)  + ((pA[2] - pB[2])**2) )
					Llist.append(checkDistance)
					totalEdgeLoopLength = totalEdgeLoopLength + checkDistance

				for j in Llist:
					sum = sum + j
					uList.append(sum)
				for k in uList:
					p = k / totalEdgeLoopLength
					pList.append(p)

				for q in range(len(selEdge)+1):
					if q == 0:
						pp = cmds.pointOnCurve(currentArcCurve , pr = 0, p=1)
						cmds.move( pp[0], pp[1], pp[2],listVtx[q] , a =True, ws=True)
					else:
						pp = cmds.pointOnCurve(currentArcCurve , pr = pList[q-1], p=1)
						cmds.move( pp[0], pp[1], pp[2],listVtx[q] , a =True, ws=True)
			cmds.delete('newsnapCurve')
			deformerNames  = cmds.wire(selMeshForDeformer, gw=0, en = 1, ce = 0, li= 0, dds = [(0,1)], dt=1, w = selCurve[0])
			cmds.connectControl("dropOffSlider", (deformerNames[0]+".dropoffDistance[0]"))
			if snapCheck == 0:
				cmds.setAttr((deformerNames[0] + '.dropoffDistance[0]'),1)
			else:
				cmds.setAttr((deformerNames[0] + '.dropoffDistance[0]'),currentDropOff)
			currentArcCurve = selCurve[0]
			cmds.select(selCurve[0])
	else:
		if selEdge:
			storeEdge = selEdge
			if cClean == 0:
				if cmds.objExists('arcCurve*'):
					arcDone()
			selMeshForDeformer = cmds.ls(sl=1,o=1)
			getCircleState,listVtx = vtxLoopOrderCheck()
			deformerNames = []
			#make nurbs curve
			if getCircleState == 0: #Arc
				if goArc == 1:
					midP = int(len(listVtx)/2)
					cmds.move(0.01, 0, 0,selEdge[midP],r=1, cs=1 ,ls=1, wd =1)
					p1 = cmds.pointPosition(listVtx[0], w =1)
					p2 = cmds.pointPosition(listVtx[midP], w =1)
					p3 = cmds.pointPosition(listVtx[-1], w =1)
					newNode = cmds.createNode('makeThreePointCircularArc')
					cmds.setAttr((newNode + '.pt1'), p1[0],  p1[1] , p1[2])
					cmds.setAttr((newNode + '.pt2'), p2[0],  p2[1] , p2[2])
					cmds.setAttr((newNode + '.pt3'), p3[0],  p3[1] , p3[2])
					cmds.setAttr((newNode + '.d'), 3)
					cmds.setAttr((newNode + '.s'), len(listVtx))
					newCurve = cmds.createNode('nurbsCurve')
					cmds.connectAttr((newNode+'.oc'), (newCurve+'.cr'))
					cmds.delete(ch=1)
					transformNode = cmds.listRelatives(newCurve, fullPath=True , parent=True )
					cmds.select(transformNode)
					cmds.rename(transformNode,'arcCurve0')
					getNewNode = cmds.ls(sl=1)
					currentArcCurve = getNewNode[0]
					numberP = 0
					if curveT == 2:#nubs curve
						numberP = int(conP) - 3
						if numberP < 1:
							numberP = 1
					else:
						numberP = int(conP) -1
					cmds.rebuildCurve(currentArcCurve,ch=1, rpo=1, rt=0, end=1, kr=0, kcp=0, kep=1, kt=0, s= numberP, d=3, tol=0.01)
				else:
					p1 = cmds.pointPosition(listVtx[0], w =1)
					cmds.curve(d= 1, p=p1)
					cmds.rename('arcCurve0')
					getNewNode = cmds.ls(sl=1)
					currentArcCurve = getNewNode[0]
					for l in range(1,len(listVtx)):
						p2 = cmds.pointPosition(listVtx[l], w =1)
						cmds.curve(currentArcCurve, a= 1, d= 1, p=p2)
					numberP = int(conP) -1
					cmds.rebuildCurve(currentArcCurve,ch=1, rpo=1, rt=0, end=1, kr=0, kcp=0, kep=1, kt=0, s= numberP, d=1, tol=0.01)
			else: #circle
				p1 = cmds.pointPosition(listVtx[0], w =1)
				cmds.curve(d= 1, p=p1)
				cmds.rename('arcCurve0')
				getNewNode = cmds.ls(sl=1)
				currentArcCurve = getNewNode[0]
				for l in range(1,len(listVtx)):
					p2 = cmds.pointPosition(listVtx[l], w =1)
					cmds.curve(currentArcCurve, a= 1, d= 1, p=p2)
				cmds.curve(currentArcCurve, a= 1, d= 1, p=p1)
				cmds.closeCurve(currentArcCurve,ch=0, ps=2, rpo=1, bb= 0.5, bki=0, p=0.1)
				conP = cmds.intSliderGrp('CPSlider',q=1 , v = True )
				numberP = int(conP)
				if numberP < 4:
					numberP = 4
					cmds.intSliderGrp('CPSlider',e=1 , v = 4 )
				cmds.rebuildCurve(currentArcCurve,ch=1, rpo=1, rt=0, end=1, kr=0, kcp=0, kep=1, kt=0, s = numberP, d=3, tol=0.01)
				###########################################################################
			cmds.delete(currentArcCurve ,ch=1)
			totalEdgeLoopLength = 0
			sum = 0
			Llist = []
			uList = []
			pList = []
			#cmds.select(selEdge)
			for i in range(len(listVtx)-1):
				pA = cmds.pointPosition(listVtx[i], w =1)
				pB = cmds.pointPosition(listVtx[i+1], w =1)
				checkDistance = math.sqrt( ((pA[0] - pB[0])**2)  + ((pA[1] - pB[1])**2)  + ((pA[2] - pB[2])**2) )
				Llist.append(checkDistance)
				totalEdgeLoopLength = totalEdgeLoopLength + checkDistance
			if goEven == 1:
				avg = totalEdgeLoopLength / (len(selEdge))
				for j in range(len(selEdge)):
					sum = ((j+1)*avg)
					uList.append(sum)
			else:
				for j in Llist:
					sum = sum + j
					uList.append(sum)
			for k in uList:
				p = k / totalEdgeLoopLength
				pList.append(p)
			#snap to curve
			if snapCheck == 1:
				for q in range(len(pList)):
					if q+1 == len(listVtx):
						pp = cmds.pointOnCurve(currentArcCurve, pr = 0, p=1)
						cmds.move( pp[0], pp[1], pp[2],listVtx[0] , a =True, ws=True)
					else:
						pp = cmds.pointOnCurve(currentArcCurve , pr = pList[q], p=1)
						cmds.move( pp[0], pp[1], pp[2],listVtx[q+1] , a =True, ws=True)
			#convert to Bezier Curve
			cmds.delete(currentArcCurve ,ch=1)
			cmds.select(currentArcCurve)
			if curveT == 1:
				cmds.nurbsCurveToBezier()
				if getCircleState == 1: #circle need to fix bug
					cmds.closeCurve(currentArcCurve,ch=0, ps=2, rpo=1, bb= 0.5, bki=0, p=0.1)
					cmds.closeCurve(currentArcCurve,ch=0, ps=2, rpo=1, bb= 0.5, bki=0, p=0.1)
			#wireWrap
			deformerNames  = cmds.wire( selMeshForDeformer, gw=0, en = 1, ce = 0, li= 0, dds = [(0,1)], dt=1, w = currentArcCurve)
			#select controllers
			if getCircleState == 0:
				cmds.setToolTo('moveSuperContext')
				degree = cmds.getAttr(currentArcCurve + '.degree')
				spans = cmds.getAttr(currentArcCurve + '.spans')
				numberCVs = degree + spans
				collect = []
				for x in range(int(numberCVs/3)-1):
					g = currentArcCurve + '.cv[' + str((x+1)*3) + ']'
					collect.append(g)
				cmds.select(collect ,r=1)

			else:
				cmds.select(currentArcCurve + '.cv[*]')
			cmd = 'doMenuNURBComponentSelection("' + currentArcCurve + '", "controlVertex");'
			mel.eval(cmd)
			cmds.connectControl("dropOffSlider", (deformerNames[0]+".dropoffDistance[0]"))
			if snapCheck == 0:
				cmds.setAttr((deformerNames[0] + '.dropoffDistance[0]'),1)
			else:
				cmds.setAttr((deformerNames[0] + '.dropoffDistance[0]'),currentDropOff)
			#add to viewport even in isolate mode
			for x in range(1,5):
				cmds.isolateSelect(('modelPanel' + str(x)), ado= currentArcCurve )

def makeArcSwitch(*args):# min point for Nurbs are 4 point
	goArc = cmds.checkBox('makeArc', q=1 ,v = 1)
	curveT = cmds.radioButtonGrp('curveType_rbg', q=1, sl=1)
	if goArc == 0:
		cmds.intSliderGrp('CPSlider', e=1, min= 4, v = 4 , fmx = 500)
	else:
		if curveT == 1:
			cmds.intSliderGrp('CPSlider', e=1, min= 2, v = 3, fmx = 500)
		else:
			cmds.intSliderGrp('CPSlider', e=1, min= 4, v = 4, fmx = 500)

def disableEvenSpaceCheckBox(*args):
	snapCheck = cmds.checkBox('snapCurve',q = 1 ,v = 1)
	if snapCheck == 0 :
		cmds.checkBox('evenSpace', e=1 ,en=0)
	else:
		cmds.checkBox('evenSpace', e=1 ,en=1)

def controlNumberSwitch(*args):# min point for Nurbs are 4 point
	curveT = cmds.radioButtonGrp('curveType_rbg', q=1, sl=1)
	getCurrentV = cmds.intSliderGrp('CPSlider', q=1 ,v = 1 )
	if curveT == 2:
		cmds.intSliderGrp('CPSlider', e=1, min= 4 )
		if getCurrentV < 4:
			cmds.intSliderGrp('CPSlider', e=1, v= 4 )
	else:
		cmds.intSliderGrp('CPSlider', e=1, min= 2 )

def vtxLoopOrderCheck(*args):
	selEdges = cmds.ls(sl=1,fl=1)
	shapeNode = cmds.listRelatives(selEdges[0], fullPath=True , parent=True )
	transformNode = cmds.listRelatives(shapeNode[0], fullPath=True , parent=True )
	edgeNumberList = []
	for a in selEdges:
		checkNumber = ((a.split('.')[1]).split('\n')[0]).split(' ')
		for c in checkNumber:
			findNumber = ''.join([n for n in c.split('|')[-1] if n.isdigit()])
			if findNumber:
				edgeNumberList.append(findNumber)
	getNumber = []
	for s in selEdges:
		evlist = cmds.polyInfo(s,ev=True)
		checkNumber = ((evlist[0].split(':')[1]).split('\n')[0]).split(' ')
		for c in checkNumber:
			findNumber = ''.join([n for n in c.split('|')[-1] if n.isdigit()])
			if findNumber:
				getNumber.append(findNumber)
	dup = set([x for x in getNumber if getNumber.count(x) > 1])
	getHeadTail = list(set(getNumber) - dup)
	checkCircleState = 0
	if not getHeadTail: #close curve
		checkCircleState = 1
		getHeadTail.append(getNumber[0])
	vftOrder = []
	vftOrder.append(getHeadTail[0])
	count = 0
	while len(dup)> 0 and count < 1000:
		checkVtx = transformNode[0]+'.vtx['+ vftOrder[-1] + ']'
		velist = cmds.polyInfo(checkVtx,ve=True)
		getNumber = []
		checkNumber = ((velist[0].split(':')[1]).split('\n')[0]).split(' ')
		for c in checkNumber:
			findNumber = ''.join([n for n in c.split('|')[-1] if n.isdigit()])
			if findNumber:
				getNumber.append(findNumber)
		findNextEdge = []
		for g in getNumber:
			if g in edgeNumberList:
				findNextEdge = g
		edgeNumberList.remove(findNextEdge)
		checkVtx = transformNode[0]+'.e['+ findNextEdge + ']'
		findVtx = cmds.polyInfo(checkVtx,ev=True)
		getNumber = []
		checkNumber = ((findVtx[0].split(':')[1]).split('\n')[0]).split(' ')
		for c in checkNumber:
			findNumber = ''.join([n for n in c.split('|')[-1] if n.isdigit()])
			if findNumber:
				getNumber.append(findNumber)
		gotNextVtx = []
		for g in getNumber:
			if g in dup:
				gotNextVtx = g
		dup.remove(gotNextVtx)
		vftOrder.append(gotNextVtx)
		count +=  1
	if checkCircleState == 0:
		vftOrder.append(getHeadTail[1])
	else:#close curve remove connected vtx
		if vftOrder[0] == vftOrder[1]:
			vftOrder = vftOrder[1:]
		elif vftOrder[0] == vftOrder[-1]:
			vftOrder = vftOrder[0:-1]
	finalList = []
	for v in vftOrder:
		finalList.append(transformNode[0]+'.vtx['+ v + ']' )

	return checkCircleState, finalList
#endregion

#region Cable
def normalize_vector(vector):
	vector_length = math.sqrt(sum([e**2 for e in vector]))
	normalize_vector = [e/vector_length for e in vector]
	return normalize_vector

def get_center_two_verts(Ver1, Ver2):
	x = (Ver1[0] + Ver2[0])/2.0
	y = (Ver1[1] + Ver2[1])/2.0
	z = (Ver1[2] + Ver2[2])/2.0
	return [x,y,z]

def distance(Ver1, Ver2):
	d = 0.0
	d = math.sqrt((Ver2[0] - Ver1[0])**2 + (Ver2[1] - Ver1[1])**2 + (Ver2[2] - Ver1[2])**2)
	return d

def get_vertex_normal_world(verSel):

	meshName = verSel.split(".vtx")[0]
	verID = int(verSel.split(".vtx[")[1][:-1])
	
	selectionList = omapi.MSelectionList()
	selectionList.add(meshName)
	dagPath = selectionList.getDagPath(0)
	mesh = omapi.MFnMesh(dagPath)
	vertexNormalW = mesh.getVertexNormal(verID, False, space=omapi.MSpace.kWorld)
	vertexNormalW = normalize_vector(vertexNormalW)
	return vertexNormalW

def get_center_pos_vertex_list(vtxList):
	vtxPosSum = [0, 0, 0]
	for vtx in vtxList:
		vtxPos = cmds.xform (vtx, q = True, ws = True, t = True)
		vtxPosSum[0] += vtxPos[0]
		vtxPosSum[1] += vtxPos[1]
		vtxPosSum[2] += vtxPos[2]
	
	centerPos = [vtxPosSum[0] / len(vtxList),
				  vtxPosSum[1] / len(vtxList),
				  vtxPosSum[2] / len(vtxList)]
									
	return centerPos

def create_curve(*arg):
	midCVH = cmds.floatField('create_cable_offset_ff', q=True, v=True)
	verSel = cmds.ls(sl=True, fl =True)
	polyFaces = cmds.filterExpand(sm=34)
	firstCVPos = []
	lastCVPos = []
	if len(verSel)== 2:
		if ".vtx" in verSel[0]:
			if len(verSel) == 2:
				firstCVPos = cmds.pointPosition(cmds.ls(sl=True)[0])
				lastCVPos = cmds.pointPosition(cmds.ls(sl=True)[1])
				firstCVDirection = normalize_vector(get_vertex_normal_world(cmds.ls(sl=True)[0]))
				lastCVDirection = normalize_vector(get_vertex_normal_world(cmds.ls(sl=True)[1]))
			else:
				cmds.confirmDialog(title='Confirm', m="Please select 2 Verts!")
		elif polyFaces:
			polyFaces = cmds.ls(polyFaces, fl =True)
			if len(polyFaces) == 2:
				meshName1 = polyFaces[0].split(".f")[0]
				cmds.makeIdentity(meshName1, apply=True, t=1, r=1, s=1, n=0)
				vertFaceSel_1 =cmds.polyListComponentConversion( polyFaces[0], ff=True, tv=True)
				vertFaceSel_1 = cmds.ls(vertFaceSel_1, fl =True)
				firstCVPos = get_center_pos_vertex_list(vertFaceSel_1)
				firstCVDirection = normalize_vector(get_face_normal(polyFaces[0]))
				
				meshName2 = polyFaces[1].split(".f")[0]
				if meshName2 != meshName1:
					cmds.makeIdentity(meshName2, apply=True, t=1, r=1, s=1, n=0)
				vertFaceSel_2 =cmds.polyListComponentConversion( polyFaces[1], ff=True, tv=True)
				vertFaceSel_2 = cmds.ls(vertFaceSel_2, fl =True)
				lastCVPos = get_center_pos_vertex_list(vertFaceSel_2)
				lastCVDirection = normalize_vector(get_face_normal(polyFaces[1]))
			else:
				cmds.confirmDialog(title='Confirm', m="Please select 2 Faces!")
	else:      
		cmds.confirmDialog(title='Confirm', m="Please select 2 Faces or Verts!")
		return    
	# Create Curve
	centerBase = get_center_two_verts(firstCVPos,lastCVPos)
	newCurve = cmds.curve(d=1, p=[firstCVPos, centerBase, lastCVPos])
	mel.eval("nurbsCurveToBezier;")
	cvFactor = midCVH   
	# Plug first CV Point
	cmds.select(newCurve +".cv[0]", r=True)
	cmds.move(firstCVPos[0], firstCVPos[1], firstCVPos[2])
	
	cmds.select(newCurve +".cv[1]", r=True)
	moveFirstPostion = [firstCVPos[0]+firstCVDirection[0]*cvFactor, firstCVPos[1]+firstCVDirection[1]*cvFactor, firstCVPos[2]+firstCVDirection[2]*cvFactor]
	cmds.move(moveFirstPostion[0], moveFirstPostion[1], moveFirstPostion[2])
		
	# Plug last CV Point
	cmds.select(newCurve +".cv[6]", r=True)
	cmds.move(lastCVPos[0], lastCVPos[1], lastCVPos[2])
	cmds.select(newCurve +".cv[5]", r=True)
	moveLastPostion = [lastCVPos[0]+lastCVDirection[0]*cvFactor, lastCVPos[1]+lastCVDirection[1]*cvFactor, lastCVPos[2]+lastCVDirection[2]*cvFactor]
	cmds.move(moveLastPostion[0], moveLastPostion[1], moveLastPostion[2])
		
	# Move mid CV Point
	cmds.select(newCurve +".cv[3]", r=True)
	Hdirection = normalize_vector([get_center_two_verts(moveLastPostion,moveFirstPostion)[i] - centerBase[i] for i in range(0, 3)])
	midCVPostion = [get_center_two_verts(moveLastPostion,moveFirstPostion)[i] + Hdirection[i]*midCVH for i in range(0, 3)]
	
	cmds.move(midCVPostion[0], midCVPostion[1], midCVPostion[2])
	midDirectionVector = normalize_vector([moveLastPostion[0] - moveFirstPostion[0], moveLastPostion[1] - moveFirstPostion[1], moveLastPostion[2] - moveFirstPostion[2]])

	cvFactor = distance(moveLastPostion,moveFirstPostion)/3
	cmds.select(newCurve +".cv[4]", r=True)
	cmds.move(midCVPostion[0]+midDirectionVector[0]*cvFactor, midCVPostion[1]+midDirectionVector[1]*cvFactor, midCVPostion[2]+midDirectionVector[2]*cvFactor)
		
	cmds.select(newCurve +".cv[2]", r=True)
	cmds.move(midCVPostion[0]-midDirectionVector[0]*cvFactor, midCVPostion[1]-midDirectionVector[1]*cvFactor, midCVPostion[2]-midDirectionVector[2]*cvFactor)

def edges_to_curve(*arg):
	listEdgeSelect = cmds.ls(sl=True, flatten=True)
	curveArray = []

	for e in listEdgeSelect:
		curveDup = cmds.duplicateCurve(e, ch=1, rn=0, local=0)
		curveArray.append(curveDup[0])
		
	cmds.select(curveArray, r=True)
	listCurveSelect = cmds.ls(sl=True)

	if len(listEdgeSelect) > 1:
		cmds.attachCurve(listCurveSelect, ch=0, rpo=0, kmk=1, m=1, bb=0.5, bki=0, p=0.1)
		cmds.delete(listCurveSelect)

#endregion

#endregion

#region Snap function

#endregion

#region Unbevel function

#region unbevel (Canh)
def line_line_intersect(a, b, c, d):
	a = OpenMaya.MVector(a[0], a[1], a[2])
	b = OpenMaya.MVector(b[0], b[1], b[2])
	c = OpenMaya.MVector(c[0], c[1], c[2])
	d = OpenMaya.MVector(d[0], d[1], d[2])
	ab = b - a
	cd = d  - c
	ac = c - a
	ab_cd_cross = ab ^ cd
	ac_cd_cross = ac ^ cd
	result =  a + (ab * ((ac_cd_cross * ab_cd_cross) / (ab_cd_cross.length()**2)))
	return result

def unbevel_two_edges(edge_list, modify):
	inside_vertex_list = []
	inside_edge_list = []
	edge_list_length = len(edge_list)
	# get inside edges
	for i in range(1, edge_list_length - 1):
		inside_edge_list.append(edge_list[i])
	# get inside vertices
	inside_vertex_list = cmds.ls(cmds.polyListComponentConversion(inside_edge_list, fe=True, tv=True), fl=True)
	# get 2 outmost edges
	start_edge = edge_list[0]
	end_edge = edge_list[edge_list_length-1]
	# get 4 points of 2 outmost edges
	start_vertex_list = cmds.ls(cmds.polyListComponentConversion(start_edge, fe=True, tv=True), fl=True)
	end_vertex_list = cmds.ls(cmds.polyListComponentConversion(end_edge, fe=True, tv=True), fl=True)
	
	a = cmds.pointPosition(start_vertex_list[0])
	b = cmds.pointPosition(start_vertex_list[1])
	c = cmds.pointPosition(end_vertex_list[0])
	d = cmds.pointPosition(end_vertex_list[1])
	
	first_mid_point = line_line_intersect(a, b, c, d)
	second_mid_point = line_line_intersect(c, d, a, b)
	
	mid_point = (first_mid_point + second_mid_point) / 2.0
	# move all inside vertices to the middle point
	
	if modify == 0:
		for v in inside_vertex_list:
			vertex = cmds.pointPosition(v)
			cmds.polyMoveVertex(v, ws=True, t=(mid_point.x - vertex[0], mid_point.y - vertex[1], mid_point.z - vertex[2]))
	elif modify == 1:
		value = cmds.floatField('unbevel_value_ff', q=True, v=True)
		for v in inside_vertex_list:
			vertex = cmds.pointPosition(v)
			cmds.polyMoveVertex(v, ws=True, t=((mid_point.x - vertex[0])*value, (mid_point.y - vertex[1])*value, (mid_point.z - vertex[2])*value))
	elif modify == 2:
		value = cmds.floatField('unbevel_value_ff', q=True, v=True)
		for v in inside_vertex_list:
			vertex = cmds.pointPosition(v)
			cmds.polyMoveVertex(v, ws=True, t=(-(mid_point.x - vertex[0])*value, -(mid_point.y - vertex[1])*value, -(mid_point.z - vertex[2])*value))
	return inside_vertex_list
	
def unchamfer(all_edges_selection, modify):
	selected_edges = all_edges_selection

	all_edges_selection_set = set(all_edges_selection)
	edge_list_length = len(all_edges_selection)
	outside_edge_list = []
	# get all vertices from selected edges
	vertex_list = cmds.ls(cmds.polyListComponentConversion(all_edges_selection, fe=True, tv=True), fl=True)
	# get all outmost edges
	for i in vertex_list:
		current_edges = cmds.ls(cmds.polyListComponentConversion(i, fv=True, te=True), fl=True)
		tmp = len(list(all_edges_selection_set - set(current_edges)))
		outside_edge = list(set(current_edges) - (set(current_edges) - all_edges_selection_set))
		if len(outside_edge) == 1:		
			outside_edge_list.append(outside_edge[0])

	selected_outside_edges = outside_edge_list

	weld_vertex_list = []
	loop_edge_list = []
	n = len(outside_edge_list) / 2
	# get ALL set of continuous edges and unchamfer
	for i in range(0,int(n)):
		# add 1 outmost edge to the set
		if len(loop_edge_list) == 0:
			loop_edge_list.append(outside_edge_list[0])
			current_edge = outside_edge_list[0]
			# delete current edge from outside edge list
			tmp_current_edge = []
			tmp_current_edge.append(current_edge)
			outside_edge_list = list(set(outside_edge_list) - set(tmp_current_edge))
			# delete current edge from all edges
			all_edges_selection = list(set(all_edges_selection) - set(tmp_current_edge))

		j = 0
		m = edge_list_length / n - 1
		# get a set of continuous edges
		while j < m:
			# get 2 vertices of the current edge
			two_vertices = cmds.ls(cmds.polyListComponentConversion(current_edge, fe=True, tv=True), fl=True)
			a_set = set(cmds.ls(cmds.polyListComponentConversion(two_vertices[0], fv=True, te=True), fl=True))
			b_set = set(cmds.ls(cmds.polyListComponentConversion(two_vertices[1], fv=True, te=True), fl=True))
			# get next edge from current edge and add to the set
			check_edge = list(a_set - (a_set - all_edges_selection_set) - set(loop_edge_list))
			if len(check_edge) != 0:
				current_edge = check_edge[0]
			else:
				current_edge = list(b_set - (b_set - all_edges_selection_set) - set(loop_edge_list))[0]
			loop_edge_list.append(current_edge)
			# delete current edge from all edges
			tmp_current_edge = []
			tmp_current_edge.append(current_edge)
			all_edges_selection = list(set(all_edges_selection) - set(tmp_current_edge))
			j += 1
		# delete current edge from outside edge list
		tmp_current_edge = []
		tmp_current_edge.append(current_edge)
		outside_edge_list = list(set(outside_edge_list) - set(tmp_current_edge))
		weld_vertex_list += unbevel_two_edges(loop_edge_list, modify)
		loop_edge_list = []
	
	cmds.polyMergeVertex(vertex_list, d=0.001)
	

	mel.eval('DeleteAllHistory')

	if modify == 0:
		return selected_outside_edges
	else:
		value = cmds.floatField('unbevel_value_ff', q=True, v=True)
		if value == 1.0:
			return selected_outside_edges
		else:
			return selected_edges
#endregion

#region unbevelv2
def line_intersect(A, B, C, D):
	A = OpenMaya.MVector(A[0], A[1], A[2])
	B = OpenMaya.MVector(B[0], B[1], B[2])
	C = OpenMaya.MVector(C[0], C[1], C[2])
	D = OpenMaya.MVector(D[0], D[1], D[2])

	AB = B - A
	CD = D - C
	AC = C - A
	cross1 = AB ^ CD
	cross2 = AC ^ CD
	if cross1.length() > 0.001 and abs(cross1.dot(C)) < 0.0001:
		intersect_point = A + AB * (cross2 * cross1)/math.pow(cross1.length(), 2)
		return intersect_point
	else:
		return 0

def line_plane_intersection(C, NormalFace, A, B):
	C = OpenMaya.MVector(C[0], C[1], C[2])
	A = OpenMaya.MVector(A[0], A[1], A[2])
	B = OpenMaya.MVector(B[0], B[1], B[2])
	NormalFace = OpenMaya.MVector(NormalFace[0], NormalFace[1], NormalFace[2])
	
	u = A - B
	w = B - C
	
	D = NormalFace * u
	N = -NormalFace * w
	if D != 0:  
		sI = N/D
		sIu = OpenMaya.MVector(sI* u[0], sI* u[1], sI* u[2])
		intersect_point = B + sIu
		return intersect_point
	else:
		return None

def line_intersect_for_bevel_edges(A, B, C, D):
	A = OpenMaya.MVector(A[0], A[1], A[2])
	B = OpenMaya.MVector(B[0], B[1], B[2])
	C = OpenMaya.MVector(C[0], C[1], C[2])
	D = OpenMaya.MVector(D[0], D[1], D[2])

	AB = B - A
	CD = D - C
	AC = C - A
	cross1 = AB ^ CD
	cross2 = AC ^ CD

	intersect_point = A + AB * (cross2 *cross1)/math.pow(cross1.length(),2)
	return intersect_point

def two_edges_intersect(selected_edge):
	# get two point on the first edges
	vert_set = cmds.polyListComponentConversion(selected_edge[0], tv = True)
	vert_set = cmds.ls(vert_set, fl = True)
	pointA = cmds.pointPosition(vert_set[0])
	pointB = cmds.pointPosition(vert_set[1])
	# get two point on the second edges
	vert_set2 = cmds.polyListComponentConversion(selected_edge[1], tv = True)
	vert_set2 = cmds.ls(vert_set2, fl = True)
	pointC = cmds.pointPosition(vert_set2[0])
	pointD = cmds.pointPosition(vert_set2[1])
	# get the intersect Point base on 4 point
	intersect_point = line_intersect(pointA, pointB, pointC, pointD)
	return intersect_point

def get_face_normal(selected_face):   
	normal_info= cmds.polyInfo(selected_face, fn=True)
	normal_info = normal_info[0].replace("\n","").split(" ")
	face_normal = [float(normal_info[-3]), float(normal_info[-2]), float(normal_info[-1])]
	return face_normal

def get_connected_edges():  
	selected_edges = cmds.ls(sl = True, fl = True)
	unconnected_selected_edges = list()
	while len(selected_edges) > 0:
		unconnected_selected_edges.append(list())
		unconnected_selected_edges[len(unconnected_selected_edges) - 1].append(selected_edges[0])
		selected_edges.remove(selected_edges[0])
		i = 0
		while i < len(unconnected_selected_edges[len(unconnected_selected_edges) - 1]):
			i += 1
			verts = cmds.polyListComponentConversion(unconnected_selected_edges[len(unconnected_selected_edges) - 1], tv = True)
			neighbor_edges = cmds.polyListComponentConversion(verts, te = True)
			neighbor_edges = cmds.ls(neighbor_edges, fl = True)
			for e in neighbor_edges:
				if e in selected_edges:
					selected_edges.remove(e)
					unconnected_selected_edges[len(unconnected_selected_edges) - 1].append(e)
	return unconnected_selected_edges 

def get_connected_edges_V2():
	'''
		Get edges set
	'''
	edge_sets = get_connected_edges()
	out_list = list()
	for connected_edge_set in edge_sets:
		cmds.select(connected_edge_set)
		mel.eval('PolySelectTraverse 5;')
		edges = cmds.ls(sl = True, fl = True)
		out_list.append(edges)
	return out_list

def unbevel(*arg):
	currentEdgeSel = cmds.ls(sl = True, fl = True)
	# Check Selection is edge
	currentEdgeSel =  cmds.filterExpand(sm=32)
	if currentEdgeSel:
		edge_sets = get_connected_edges_V2()
		merge_vertex=[]
		for connected_edge_set in edge_sets:
			verts = list()
			endVerts = list()
			midleVerts = list()
			intersect_point = 0
			for e in connected_edge_set:
				for vertStr in cmds.polyListComponentConversion(e, tv = True):
					cmds.select(vertStr)
					for v in cmds.ls(sl = True, fl = True):
						verts.append(v)
						# filter verts to separate endverts and midle
			
			for v in verts:
				if verts.count(v) > 1:
					midleVerts.append(v)
				else:
					endVerts.append(v)
			# get end edges
			edges = cmds.polyListComponentConversion(endVerts, te = True)
			execEdges = list()
			cmds.select(edges)
			for e in cmds.ls(sl = True, fl = True):
				if e in connected_edge_set:
					execEdges.append(e)
			cmds.select(execEdges)
			
			edgesExpand = [e for e in execEdges if e not in currentEdgeSel]
			edgeOld = [e for e in execEdges if e in currentEdgeSel]
			#twoEdges
			if len(edgesExpand) == 2:
				'''
				there are only two edges at the end
				'''
				# get two point on the first edges
				vert_set = cmds.polyListComponentConversion(execEdges[0], tv = True)
				vert_set = cmds.ls(vert_set, fl = True)
				pointA = cmds.pointPosition(vert_set[0])
				pointB = cmds.pointPosition(vert_set[1])
				# get two point on the second edges
				vert_set = cmds.polyListComponentConversion(execEdges[1], tv = True)
				vert_set = cmds.ls(vert_set, fl = True)
				pointC = cmds.pointPosition(vert_set[0])
				pointD = cmds.pointPosition(vert_set[1])
				# get the intersect Point base on 4 point
				intersect_point = line_intersect_for_bevel_edges(pointA, pointB, pointC, pointD)
				print(intersect_point)
				if not intersect_point:            
					vertexOfEdgesExpand0 = cmds.polyListComponentConversion(edgesExpand[0], tv = True)
					allEdgesConectedEdgesExpand0 = cmds.ls(cmds.polyListComponentConversion(vertexOfEdgesExpand0, te = True), fl = True)
					edgeOld = [i for i in currentEdgeSel if i in allEdgesConectedEdgesExpand0 ]
					execEdges = [edgeOld[0], edgesExpand[1]]      
					edgesExpand.remove(edgesExpand[0])
				else:
					for v in midleVerts:
						cmds.move(intersect_point[0], intersect_point[1], intersect_point[2], v)
						if v not in merge_vertex:
							merge_vertex.append(v)

			if len(edgesExpand) == 1:             
				'''
					In execEdges have one edgeOld of currentEdgeSel
				'''
				# Use edgeOld and vertexOld to find Face to Intersect
				vertexOld = cmds.ls(cmds.polyListComponentConversion(edgeOld, tv = True), fl=True)
				vertexOfFace = [v for v in vertexOld if v not in midleVerts]
				listFace_1 = cmds.ls(cmds.polyListComponentConversion(vertexOfFace, fv =True, tf = True), fl=True)
				listFace_2 = cmds.ls(cmds.polyListComponentConversion(edgeOld, fe =True, tf = True), fl=True)
				faceToIntersect = [f for f in listFace_1 if f not in listFace_2]    
				NormalFaceIntersect =[]
				allIntersectPoint = []
				#Find Normal of face To Intersect
				if faceToIntersect:
					trianCmd=cmds.polyTriangulate(faceToIntersect)
					trianFace =cmds.ls(sl=True, fl=True)
					for face in trianFace:
						listVert = cmds.ls(cmds.polyListComponentConversion( face, ff=True, tv=True), fl = True)
						if vertexOfFace[0] in listVert:
							NormalFaceIntersect.append(get_face_normal(face))
					cmds.delete(trianCmd)                
					for i in range(0, len(NormalFaceIntersect)):
						# Get two point of edgeToIntersect
						edgeToIntersect = [e for e in execEdges if e not in edgeOld]
						vert_set = cmds.polyListComponentConversion(edgeToIntersect[0], tv = True)
						cmds.select(vert_set)
						vert_set = cmds.ls(sl = True, fl = True)
						pointA = cmds.pointPosition(vert_set[0])
						pointB = cmds.pointPosition(vert_set[1])
						# Get Point and Normal of FaceIntersect
						pointC = cmds.pointPosition(vertexOfFace[0])
						NormalFace = NormalFaceIntersect[i]
						intersect_point = line_plane_intersection(pointC, NormalFace, pointA, pointB)
						allIntersectPoint.append(intersect_point)
	
					if allIntersectPoint:
						endVerts0_pos = cmds.pointPosition(endVerts[0])
						endVerts0 = OpenMaya.MVector(endVerts0_pos[0], endVerts0_pos[1], endVerts0_pos[2])
						endVerts1_pos = cmds.pointPosition(endVerts[1])
						endVerts1 = OpenMaya.MVector(endVerts1_pos[0], endVerts1_pos[1], endVerts1_pos[2])
					
						listLengthToEndVertsAndMidVerts = [(i - endVerts0).length() + (i - endVerts1).length() for i in allIntersectPoint]
						minLength = min(listLengthToEndVertsAndMidVerts)
						threshold = 7*(endVerts1 - endVerts0).length()
						if minLength < threshold:
							indexIPoint = listLengthToEndVertsAndMidVerts.index(minLength)
							intersect_point = allIntersectPoint[indexIPoint]                
						else:
							intersect_point = 0
	
					if intersect_point:
						midleVerts.append(vertexOfFace[0])
						for v in midleVerts:
							cmds.move(intersect_point[0], intersect_point[1], intersect_point[2], v)
							if v not in merge_vertex:
								merge_vertex.append(v)

			if len(edgesExpand) == 0:
				vertexSel = cmds.polyListComponentConversion(connected_edge_set, tv = True)
				allEdgesConected = cmds.ls(cmds.polyListComponentConversion(vertexSel, te = True), fl = True)
				edgesToIntersect = [e for e in allEdgesConected if e not in connected_edge_set]
				cmds.select(edgesToIntersect)
				edgesToIntersect1 = [i for i in edgesToIntersect if endVerts[0] in cmds.ls(cmds.polyListComponentConversion(i, tv = True), fl = True) and endVerts[1] not in cmds.ls(cmds.polyListComponentConversion(i, tv = True), fl = True)]
				edgesToIntersect2 = [i for i in edgesToIntersect if endVerts[1] in cmds.ls(cmds.polyListComponentConversion(i, tv = True), fl = True) and endVerts[0] not in cmds.ls(cmds.polyListComponentConversion(i, tv = True), fl = True)] 
				allPairEdges = list(itertools.product(edgesToIntersect1, edgesToIntersect2))
				allIntersectPoint = [two_edges_intersect(i) for i in allPairEdges if two_edges_intersect(i) != 0]

				if allIntersectPoint:
					endVerts0_pos = cmds.pointPosition(endVerts[0])
					endVerts0 = OpenMaya.MVector(endVerts0_pos[0], endVerts0_pos[1], endVerts0_pos[2])
					endVerts1_pos = cmds.pointPosition(endVerts[1])
					endVerts1 = OpenMaya.MVector(endVerts1_pos[0], endVerts1_pos[1], endVerts1_pos[2])

					listLengthToEndVertsAndMidVerts = [(i - endVerts0).length() + (i - endVerts1).length() for i in allIntersectPoint]
					minLength = min(listLengthToEndVertsAndMidVerts)
					threshold = 7*(endVerts1 - endVerts0).length()
					if minLength < threshold:
						indexIPoint = listLengthToEndVertsAndMidVerts.index(minLength)
						intersect_point = allIntersectPoint[indexIPoint]                
					else:
						intersect_point = 0
				if intersect_point:
					allVert = midleVerts + endVerts
					for v in allVert:
						cmds.move(v, intersect_point)                
						if v not in merge_vertex:
							merge_vertex.append(v)

		if merge_vertex:
			cmds.select(merge_vertex) 
			cmds.polyMergeVertex(merge_vertex, d = 0.001)
	else:
		cmds.confirmDialog(title='Confirm', m="Please Select Edge to unbevel!")

def unbevel_v2(*args):
	#cmds.scriptEditorInfo(clearHistory=True)
	my_ordered_selection = cmds.ls(sl=True, fl=True)
	current_select = unchamfer(my_ordered_selection, 0)
	cmds.select(current_select)

def bevel_modifier(modify):
	#cmds.scriptEditorInfo(clearHistory=True)
	my_ordered_selection = cmds.ls(sl=True, fl=True)
	current_select = unchamfer(my_ordered_selection, modify)
	cmds.select(current_select)

#endregion

#endregion

#region Circle function
global priority_vertex_components
priority_vertex_components = []

def select_contiguous_edges(*args):
	mel.eval('SelectContiguousEdges;')

def select_edge_ring(*args):
	mel.eval('SelectEdgeRingSp;')

def get_circle_priority_vertices(mode):
	global priority_vertex_components
	priority_vertex_components = []
	if mode == 1:
		select_list = cmds.ls(sl=True)
		vertex_list = cmds.polyListComponentConversion(select_list, tv=True)
		priority_vertex_components = cmds.filterExpand(vertex_list, selectionMask=31) or []
	update_circle_ui()
	
def update_circle_ui():
	vertex_list_length = len(priority_vertex_components)
	cmds.textField('circle_tf', e=True, tx=str(vertex_list_length) + ' Vertex')
	if(vertex_list_length==0):
		cmds.textField('circle_tf', e=True, bgc=(0.2, 0.2, 0.2))
		cmds.button('circle_clear_btn', l = 'Clear', e=True, en=False)
	else:
		cmds.textField('circle_tf', e=True, bgc=(0.4, 0.6, 1))
		cmds.button('circle_clear_btn', l = 'Clear', e=True, en=True)

def change_circle_diameter_value(value):
	cmds.floatField('circle_diameter_fl', e=True, v=value)

def change_circle_angle_value(value):
	cmds.floatField('circle_angle_fl', e=True, v=value)

#endregion

#region Pivot function

# Modify Pivot to object select
def set_pivot(*arg):
	# Get Pivot
	selected = cmds.ls(sl=True)
	if cmds.ls(sl=True, type = 'transform'):
		pivot_pos = cmds.xform(selected[-1], q=1, ws=1, rp=1)
	else:
		selected_vertex_list = cmds.filterExpand(cmds.polyListComponentConversion(tv = True), sm = 31)
		if selected_vertex_list:
			pivot_pos = [0,0,0]
			for vertex in selected_vertex_list:
				vertex_pos = cmds.xform(vertex, q=True, ws=True, t=True)
				pivot_pos[0] += vertex_pos[0]
				pivot_pos[1] += vertex_pos[1]
				pivot_pos[2] += vertex_pos[2]
			pivot_pos[0] /= len(selected_vertex_list)
			pivot_pos[1] /= len(selected_vertex_list)
			pivot_pos[2] /= len(selected_vertex_list)
			#toggleSelMode;
			mel.eval("dR_modeObject;")

	# Set Pivot
	if pivot_pos:
		selected = cmds.ls(sl = True)
		if selected:
			for obj in selected:
				if cmds.objectType(obj) == "transform" or cmds.objectType(obj) == "mesh":
					cmds.move(pivot_pos[0], pivot_pos[1], pivot_pos[2], obj +".scalePivot", obj +".rotatePivot", absolute=True)
				
				## This Command copy pivots to all chidren of group selected
				# if cmds.checkBox( 'descendentsCheckBox', q = True, v = True ):
				#     if cmds.listRelatives(objSel, allDescendents =True, type = "transform"):
				#         for i in cmds.listRelatives(objSel, allDescendents =True, type = "transform"):
				#             cmds.move(pivot_pos[0], pivot_pos[1], pivot_pos[2], i +".scalePivot", i +".rotatePivot", absolute=True)


def align_pivot(*arg):
	mel.eval('setToolTo Move;')
	pivpos = cmds.manipMoveContext('Move', q = True, p = True)
	sel = cmds.filterExpand(cmds.polyListComponentConversion(tv = True), sm = 31)
	object = cmds.ls(sel[0].split('.')[0], l = True)[0]
	parent = cmds.listRelatives(object, p = True, f = True)
	if len(sel) < 3:
		cmds.warning('Please select at least 3 Vertices, 2 Edges or 1 Face')
	else:
		planeHelper = cmds.polyPlane(n = 'rotationPlane', w = 10 ,h = 10, sx = 1, sy = 1, ax = [0, 1, 0], cuv = 2, ch =1)
		cmds.select([(planeHelper[0] + ".vtx[0:2]"), sel[0], sel[1], sel[2]])
		mel.eval('snap3PointsTo3Points(0);')
		cmds.rotate(-90, 0, 90, planeHelper, os = True, r = True)
		newObj = cmds.parent(object, planeHelper)
		cmds.makeIdentity(newObj[0], apply = True, t = 1, r = 1, s = 1, n = 2)
		cmds.xform( ws = True, piv = [pivpos[0], pivpos[1], pivpos[2]])
		cmds.parent(newObj[0], w = True)
		cmds.delete(planeHelper)
		if parent:
			cmds.parent(newObj[0], parent[0])	

def set_pivot_to_objects(position):
	selected_objects = cmds.ls(sl=True)
	if len(selected_objects) == 0:
		cmds.confirmDialog(t = 'Notification', m = 'Please select object!')
		return False
	for obj in selected_objects:
		# Set pivot to center object
		cmds.xform(obj, cp=True)
		# Get bounding box object
		bounding_box = cmds.xform(obj, q=True, bb=True, ws=True)
		# Set vars from bounding box value
		x_min, y_min, z_min, x_max, y_max, z_max = bounding_box
		# Move pivot object to bottom
		if position == 'x_max':
			cmds.move(x_max, [obj + '.scalePivot', obj + '.rotatePivot'], x=True, a=True)
		elif position == 'y_max':
			cmds.move(y_max, [obj + '.scalePivot', obj + '.rotatePivot'], y=True, a=True)
		elif position == 'z_max':
			cmds.move(z_max, [obj + '.scalePivot', obj + '.rotatePivot'], z=True, a=True)
		elif position == 'x_min':
			cmds.move(x_min, [obj + '.scalePivot', obj + '.rotatePivot'], x=True, a=True)
		elif position == 'y_min':
			cmds.move(y_min, [obj + '.scalePivot', obj + '.rotatePivot'], y=True, a=True)
		elif position == 'z_min':
			cmds.move(z_min, [obj + '.scalePivot', obj + '.rotatePivot'], z=True, a=True)
	return True

#endregion

#region Bridge function
def get_center_position(vertices):
	pivot_pos = [0,0,0]
	for vertex in vertices:
		vertex_pos = cmds.xform(vertex, q=True, ws=True, t=True)
		pivot_pos[0] += vertex_pos[0]
		pivot_pos[1] += vertex_pos[1]
		pivot_pos[2] += vertex_pos[2]
	pivot_pos[0] /= len(vertices)
	pivot_pos[1] /= len(vertices)
	pivot_pos[2] /= len(vertices)
	return OpenMaya.MVector(pivot_pos[0], pivot_pos[1], pivot_pos[2])

def get_distance(a,b):
	return math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2 + (a[2]-b[2])**2)

#endregion

#region Select Face Area function
def create_face_area_uvset(*args):
	face_area_uvset = "FaceArea"
	selected_edges = cmds.ls(sl=True, fl=True)
	selected_objects = cmds.ls(sl=True, o=True)
	delete_face_area_uvset()
	# checks for face selection(mask 34) & vertices(mask 31)
	if cmds.filterExpand(selected_edges, selectionMask=31) or cmds.filterExpand(selected_edges, selectionMask=34):
		cmds.warning("Please select edges")
		return False
	# create extra UV set to work in, and project new UVs
	cmds.polyUVSet(create=True, uvSet=face_area_uvset)
	cmds.polyUVSet(currentLastUVSet=True)
	cmds.polyProjection(selected_objects[0], type='Planar', md='p')
	cmds.polyMapCut(selected_edges)
	mel.eval("doMenuComponentSelection(\"" + selected_objects[0] + "\", \"meshUVShell\");")
	mel.eval('BakeNonDefHistory;')	
	return True

def delete_face_area_uvset(*args):
	selected_objects = cmds.ls(sl=True, o=True)
	all_uvset = cmds.polyUVSet(query=True, allUVSets=True)
	if "FaceArea" in all_uvset:
		cmds.polyUVSet(delete=True, uvSet="FaceArea")
	mel.eval('BakeNonDefHistory;')
	cmds.select(selected_objects)
	return True
#endregion

#region Selection Set
global selection_set_list
selection_set_list = []

def add_selection_set_to_list(*arg):
	global selection_set_list
	selected = cmds.ls(sl=True, fl=True)
	set_name = cmds.textField('set_name_tf', q=True, tx=True)
	# Add number if set name is exists
	set_name_list = [s["name"] for s in selection_set_list]
	i = 1
	current_name = set_name
	while current_name in set_name_list:
		current_name = set_name + str(i)
		i+=1
	# Change UI
	cmds.textScrollList('selection_set_tsl', e=True, a=current_name)
	item = {"name": current_name, "list": selected}
	selection_set_list.append(item)

def remove_item_in_selection_set_list(*arg):
	global selection_set_list
	selected_item = cmds.textScrollList('selection_set_tsl', q=True, selectItem=True)[0]
	if selected_item is not None:
		cmds.textScrollList('selection_set_tsl', edit=True, removeItem=selected_item)
		for s in selection_set_list:
			if s["name"] == selected_item:
				selection_set_list.remove(s)

def clear_selection_set_list(*arg):
	global selection_set_list
	number_of_items = cmds.textScrollList('selection_set_tsl', q=True, numberOfItems=True)
	if number_of_items != 0:
		cmds.textScrollList('selection_set_tsl', edit=True, ra=True)
		selection_set_list = []

def select_item_in_selection_set_list(*arg):
	global selection_set_list
	selected_item = cmds.textScrollList('selection_set_tsl', q=True, selectItem=True)[0]
	for s in selection_set_list:
		if s["name"] == selected_item:
			cmds.select(s["list"][0].rsplit(".", 1)[0], r=True)
			cmds.selectMode(component=True)
			cmds.select(s["list"])

#endregion

#region Grid Cut
def gridcut_function(division, bakepivot, x, y, z):
	mesh_list = cmds.ls(sl=True, l=True, o=True)
	object_center = cmds.objectCenter(gl=True)
	print(object_center)
	
	if bakepivot:
		mel.eval("BakeCustomPivot;")

	object_rotation = cmds.xform(mesh_list[0], q=True, rotation=True)
	
	cmds.setAttr(mesh_list[0] + ".rotate", 0, 0, 0)
	bounding_box = cmds.xform(q=True, os=True, bb=True)
		
	x_min = bounding_box[0]
	x_max = bounding_box[3]
	y_min = bounding_box[1]
	y_max = bounding_box[4]
	z_min = bounding_box[2]
	z_max = bounding_box[5]
	for c in range(1, division):
		if x:
			cmds.polyCut(cutPlaneCenter=[(object_center[0]), (object_center[1]), (z_min + (c * ((z_max - z_min)/division)))], cutPlaneRotate=[0, 0, 180], ws=True)
		if y:
			cmds.polyCut(cutPlaneCenter=[(object_center[0]), (y_min + (c * ((y_max - y_min)/division))), (object_center[2])], cutPlaneRotate=[90, 0, 0], ws=True)
		if z:
			cmds.polyCut(cutPlaneCenter=[(x_min + (c * ((x_max - x_min)/division))), (object_center[1]), (object_center[2])], cutPlaneRotate=[180, 90, 0], ws=True)
	cmds.setAttr(mesh_list[0] + ".rotate", object_rotation[0], object_rotation[1], object_rotation[2])

#region GridCut
def gridcut(*arg):
	division = cmds.intField('gridcut_if', q=True, v=True)
	bakepivot = cmds.checkBox('gridcut_bakepivot_cb', q=True, v=True)
	x = cmds.checkBox('gridcut_x_cb', q=True, v=True)
	y = cmds.checkBox('gridcut_y_cb', q=True, v=True)
	z = cmds.checkBox('gridcut_z_cb', q=True, v=True)
	if x==False and y==False and z==False:
		cmds.warning("Please select at least one axis!")
	else:
		gridcut_function(division, bakepivot, x, y, z)
#endregion

#endreigon

#endregion

#region Extend, Fill Hole

#region Fill Hole (Vertex) Function

def expand_vert_to_edge_along_border(vert):
	origSel = cmds.ls(sl=1)
	cmds.select(vert, r=1)
	try:
		cmds.polySelectConstraintMonitor(c=1)
		cmds.polySelectConstraint(t=1, m=2, w=1, pp=1)
		cmds.polySelectConstraint(t=1, m=0, w=0)
	except BaseException:
		print("ERROR!")
	finally:
		cmds.polySelectConstraintMonitor(d=1)

	edges = cmds.ls(cmds.polyListComponentConversion(cmds.ls(os=1, fl=1), fv=1, te=1, internal=1), fl=1)
	if len(edges) > 2:
		cmds.select(vert, r=1)
		try:
			cmds.polySelectConstraintMonitor(c=1)
			cmds.polySelectConstraint(t=1, m=2, pp=5)
			cmds.polySelectConstraint(t=1, m=0)
		except BaseException:
			print("ERROR!")
		finally:
			cmds.polySelectConstraintMonitor(d=1)

		verts = set(cmds.ls(sl=1, fl=1))
		vertLoop = set(cmds.ls(cmds.polySelectSp(loop=1), fl=1))
		borderPart = vertLoop - verts
		completeBorder = set(cmds.ls(cmds.polySelectSp(list(borderPart), loop=1), fl=1))
		finalVerts = completeBorder & verts
		edges = cmds.ls(cmds.polyListComponentConversion(list(finalVerts), fv=1, te=1, internal=1), fl=1)
	cmds.select(origSel, r=1)
	return edges

def find_node_transform(sel):
	""" Find Transform node from list of selections """
	sh = cmds.ls(sel, g=1, o=1, ni=1)
	if not sh:
		tr = cmds.ls(sel, tr=1, ni=1)
	else:
		tr = cmds.listRelatives(sh, p=1, pa=1, ni=1)
	if tr:
		return list(oDict.fromkeys(tr))
	else:
		return []

def get_verts_gstool(comp):
	edges = cmds.filterExpand(comp, sm=32)
	if edges:
		return cmds.ls(cmds.polyListComponentConversion(edges, fe=1, tv=1), fl=1)
	poly = cmds.filterExpand(comp, sm=34)
	if poly:
		return cmds.ls(cmds.polyListComponentConversion(poly, ff=1, tv=1), fl=1)

def get_edges_gstool(comp):
	verts = cmds.filterExpand(comp, sm=31)
	if verts:
		return cmds.ls(cmds.polyListComponentConversion(verts, fv=1, te=1), fl=1)
	poly = cmds.filterExpand(comp, sm=34)
	if poly:
		return cmds.ls(cmds.polyListComponentConversion(poly, fv=1, te=1), fl=1)

def expand_edge_to_border(edge):
	obj = cmds.ls(edge, o=1)[0]
	edges = cmds.ls(cmds.polySelect(obj, eb=return_components_id(edge), ns=1, ass=1), fl=1)
	return edges

def return_components_id(components):
	if not components:
		return False
	if not isinstance(components, list):
		components = [
		 components]
	compList = [ int(re.findall('[0-9]+', re.findall('[[0-9]+]', comp)[0])[0]) for comp in components ]
	if len(compList) == 1:
		compList = compList[0]
	return compList

def sortEdgeBorder(vertSel, edgeBorder, edgePair):
	border = []
	edgeBorder = set(edgeBorder)
	prevVert = vertSel[0]
	prevEdge = edgePair[1] if get_verts_gstool(edgePair[0])[0] == prevVert else edgePair[0]
	edgeBorder.remove(prevEdge)
	while edgeBorder:
		border.append(prevVert)
		temp = get_verts_gstool(prevEdge)
		temp.remove(prevVert)
		prevVert = temp[0]
		prevEdge = list(set(get_edges_gstool(prevVert)) & edgeBorder)[0]
		edgeBorder.remove(prevEdge)

	border.append(prevVert)
	return border

def get_row_count(borderLoop, vertSel):
	if len(vertSel) == 1:
		return (len(borderLoop) / 2 + 1) / 2
	else:
		index = borderLoop.index(vertSel[1])
		if index < len(borderLoop) / 2:
			return index
		return index - len(borderLoop) / 2

def get_sides_and_corners(borderLoop, rowCount, columnCount):
	pts = borderLoop
	side1 = [ pts[i] for i in range(rowCount + 1) ]
	side2 = [ pts[i] for i in range(rowCount, rowCount + columnCount + 1) ]
	side3 = [ pts[i] for i in range(rowCount + columnCount, 2 * rowCount + columnCount + 1) ]
	side4 = [ pts[i] for i in range(2 * rowCount + columnCount, len(pts)) ] + [borderLoop[0]]
	corner1 = side1[0]
	corner2 = side2[0]
	corner3 = side3[0]
	corner4 = side4[0]
	return [side1, side2, corner1, corner2, corner3, corner4]

def initMatrix(borderLoop, side1, side2, corner2, corner4):
	rows = len(side2)
	columns = len(side1)
	corner2_index = borderLoop.index(corner2)
	corner4_index = borderLoop.index(corner4)
	matrix = [ [ 0 for i in range(columns) ] for j in range(rows) ]
	for row in range(rows):
		for column in range(columns):
			if row == 0:
				matrix[row][column] = borderLoop[column]
			elif row == rows - 1:
				matrix[row][column] = borderLoop[(corner4_index - column)]
			elif column == 0:
				matrix[row][column] = borderLoop[(-row)]
			elif column == columns - 1:
				matrix[row][column] = borderLoop[(corner2_index + row)]
			else:
				matrix[row][column] = None

	#matrix = matrix
	
	return matrix, rows, columns

def addQuads(obj, mult, matrix, rows, columns, corner1, corner2, corner3, corner4):
	for row in range(0, rows - 1):
		for column in range(0, columns - 1):
			addQuad(obj, mult, matrix, rows, columns, row, column, corner1, corner2, corner3, corner4)

def addQuad(obj, mult, matrix, rows, columns, row, column, corner1, corner2, corner3, corner4):
	p1 = matrix[(row + 1)][column]
	p2 = matrix[row][column]
	p3 = matrix[row][(column + 1)]
	p4 = matrix[(row + 1)][(column + 1)]
	p1_ID = return_components_id(p1) if p1 else None
	p2_ID = return_components_id(p2) if p2 else None
	p3_ID = return_components_id(p3) if p3 else None
	p4_ID = return_components_id(p4) if p4 else None
	if not p4:
		left = matrix[(row + 1)][0]
		right = matrix[(row + 1)][(columns - 1)]
		up = matrix[0][(column + 1)]
		down = matrix[(rows - 1)][(column + 1)]
		left_pp = cmds.pointPosition(left, l=1)
		right_pp = cmds.pointPosition(right, l=1)
		up_pp = cmds.pointPosition(up, l=1)
		down_pp = cmds.pointPosition(down, l=1)
		corner1_pp = cmds.pointPosition(corner1, l=1)
		corner2_pp = cmds.pointPosition(corner2, l=1)
		corner3_pp = cmds.pointPosition(corner3, l=1)
		corner4_pp = cmds.pointPosition(corner4, l=1)
		a = vert_calc(row + 1, rows - 1, up_pp, down_pp)
		b = vert_calc(column + 1, columns - 1, left_pp, right_pp)
		c = vert_calc(row + 1, rows - 1, vert_calc(column + 1, columns - 1, corner1_pp, corner2_pp), vert_calc(column + 1, columns - 1, corner4_pp, corner3_pp))
		p4_ID = [ (a[i] + b[i] - c[i]) * mult for i in range(3) ]
		matrix[(row + 1)][column + 1] = '%s.vtx[%s]' % (obj[0], cmds.polyEvaluate(obj, v=1))
	cmds.polyAppendVertex(ch=0, a=[p1_ID, p2_ID, p3_ID, p4_ID])
	return

def vert_calc(vert, max_verts, pp_min, pp_max):
	return [(pp_min[i] * (max_verts - vert) + pp_max[i] * vert) / max_verts for i in range(3)]

#endregion

#region Fill Hole (Edge) + Extend
def check_component_type(selection):
	if '.vtx[' in selection[0]:
		return 'vertice'
	if '.e[' in selection[0]:
		return 'edge'
	if '.f[' in selection[0]:
		return 'face'

def MAS_list_points(A, B, operation):
	listbutton_response = []
	for i in range(3):
		if operation == '*':
			temp = A[i] * B
		elif operation == '+':
			temp = A[i] + B[i]
		elif operation == '-':
			temp = A[i] - B[i]
		listbutton_response.append(temp)

	return listbutton_response

def buKi_get_border_edges(base_edge):
	edge_number = int(base_edge.split('[', 1)[1].split(']')[0])
	border_edges = cmds.polySelect(q=True, eb=edge_number)
	if border_edges:
		if sys.version[:2] == '3.':
			border_edges = list(dict.fromkeys(border_edges))
		else:
			tmp_order = []
			[tmp_order.append(x) for x in border_edges if x not in tmp_order]
			border_edges = tmp_order
	return border_edges

def buKi_create_loop_list(edge_loop, base_edge):
	correct_loop_order = []
	object_name = base_edge.split('[', 1)[0]
	for e in edge_loop:
		tmp_edge = '%s[%s]' % (object_name, e)
		correct_loop_order.append(tmp_edge)
	return correct_loop_order

def buKi_get_face_neighbours_from_vtx(edge):
	vertices = cmds.ls(cmds.polyListComponentConversion(edge, tv=True), fl=True)
	info_A = cmds.polyInfo(vertices[0], vf=True)
	info_B = cmds.polyInfo(vertices[1], vf=True)
	face_list_A = [ int(s) for s in info_A[0].split() if s.isdigit() ]
	face_list_B = [ int(s) for s in info_B[0].split() if s.isdigit() ]
	return (face_list_A, face_list_B)

def buki_append_ring_loop():
	end_edges = cmds.ls(sl=True, fl=True)
	mesh_name = cmds.ls(end_edges, o=True)
	cmds.delete(mesh_name, ch=True)
	loop = cmds.ls(cmds.polySelectSp(end_edges[0], q=True, l=True), fl=True)
	loop.remove(end_edges[0])
	loop.remove(end_edges[1])
	try:
		cmds.polyBridgeEdge(loop, ch=False, sma=30, dv=0)
	except:
		OpenMaya.MGlobal.displayWarning('Not the same edge count')
#endregion

#endregion

#region Create Decal

def duplicate_selected_faces():
	# order of obj after duplicate is different when the mesh have more than 1 element. meshTYPE = 1 means there is only 1 element
	meshTYPE = 1
	
	faceList = cmds.ls(selection = True , long = True , flatten = True)
	obj = cmds.ls(selection = True , long = True , flatten = True , objectsOnly = True)
	cmds.select(obj)
	mel.eval('PolySelectConvert 1')
	allFacesCount = len(cmds.ls(selection = True , long = True , flatten = True))
	cmds.select(faceList[0])
	mel.eval('ConvertSelectionToShell;')
	anElementFacesCount = len(cmds.ls(selection = True , long = True , flatten = True))
	
	if allFacesCount != anElementFacesCount:
		meshTYPE = 2
	
	transform = str(obj[0])
	transform = cmds.listRelatives(transform, parent = True, fullPath = True)[0]

	parent = cmds.listRelatives(transform , parent = True, fullPath = True)
	# print parent
	cmds.polyChipOff(faceList , duplicate = 1 , keepFacesTogether = True)
	cmds.polySeparate(obj , removeShells = True , constructionHistory = False)
	cmds.parent(world = True)
	cmds.delete(transform)
	newObjList = cmds.ls(selection = True , long = True , flatten = True , type = 'transform')

	
	if meshTYPE == 2:
		cmds.select(newObjList[0:-1] , replace = True)
		tempSelectList = cmds.ls(selection = True, long = True, flatten = True)
		if len(tempSelectList)>1:
			mel.eval('flattenCombine;')

	else:
		cmds.select(newObjList[1:] , replace = True)
		tempSelectList = cmds.ls(selection = True, long = True, flatten = True)
		if len(tempSelectList)>1:
			mel.eval('flattenCombine;')

		# cmds.select(newObjList[-1] , replace = True)
	tempslList = cmds.ls(selection = True , long = True , flatten = True , type = 'transform')
	if parent:
		cmds.parent(tempslList[0] , parent)
		if meshTYPE == 2:
			cmds.parent(newObjList[-1] , parent)
			
			transformA = parent[0] + '|' + newObjList[-1]
			transformB = parent[0] + '|' + tempslList[0]
		else:
			cmds.parent(newObjList[0] , parent)
		
			transformA = parent[0] + '|' + newObjList[0]
			transformB = parent[0] + '|' + tempslList[0]
	else:
		
		if meshTYPE == 2:
			transformA = newObjList[-1]
			transformB = tempslList[0]
		else:
			transformA = newObjList[0]
			transformB = tempslList[0]
	
	cmds.select(transformB, replace = True)
	mel.eval('CenterPivot;')
	
	cmds.rename(transformA, transform.split('|')[-1])
	cmds.rename(transformB, transform.split('|')[-1])

	mel.eval("FreezeTransformations;")

def select_faces_after_bevel(segments, chamfer, offset):
	# Count vertex select
	edge_selected = cmds.ls(sl=True, fl=True)
	mel.eval("ConvertSelectionToVertices;")
	vertices_selected = cmds.ls(sl=True, fl=True)

	# Select object 
	obj = cmds.ls(objectsOnly=True, selection=True)[0]
	mesh = cmds.listRelatives(obj, parent=True)[0]
	cmds.select(mesh, replace=True) 

	# Duplicate mesh 
	mesh_duplicate = cmds.duplicate(mesh, smartTransform=True)[0]
	cmds.rename(mesh_duplicate, mesh+"_COPY")

	cmds.select(mesh, replace=True) 
	# cmds.hide(mesh+"_COPY")

	# Count all vertices in object
	mel.eval("ConvertSelectionToVertices;") #convert objec selected to Vertices
	all_vertecies_object = cmds.ls(sl=True, fl=True) 

	# Bevel edge select
	cmds.polyBevel3(edge_selected, segments=segments, chamfer=chamfer, offset=offset) #Bevel Edge selected

	# Count all vertices in new object
	cmds.select(mesh, replace=True) #Select object of edge 
	mel.eval("ConvertSelectionToVertices;") #convert objec selected to Vertices
	new_vertices_after_bevel = cmds.ls(sl=True, fl=True) 

	# Vertices need select
	vertices_need_selected = list(set(new_vertices_after_bevel) - set(all_vertecies_object))

	count = 0
	for i in vertices_selected:
		vertices_need_selected.append(all_vertecies_object[-1 + count])
		count += -1

	cmds.select(vertices_need_selected, replace=True)
	#mel.eval("ConvertSelectionToFacePerimeter;")

	array_faces = []
	for vertex in vertices_need_selected:
		cmds.select(vertex, replace=True)
		mel.eval("ConvertSelectionToFaces;")
		list_faces_handle = cmds.ls(sl=True, fl=True)
		
		for f in list_faces_handle:
			array_faces.append(f)
		
	cmds.select(array_faces, replace=True)

	array_faces = list(set(array_faces))
	list_faces_will_select = []

	for face in array_faces:
		err = []
		cmds.select(face, replace=True)
		mel.eval("ConvertSelectionToVertices;")
		list_vetices_selected = cmds.ls(sl=True, fl=True)
		for v in list_vetices_selected:
			if v not in vertices_need_selected:
				err.append(v)

		if err == []:
			list_faces_will_select.append(face)

	mel.eval("ConvertSelectionToFaces;")
	cmds.select(list_faces_will_select, replace=True)

def clean_old_mesh():
	all_mesh_in_scene = cmds.ls(type='transform')

	for trans in all_mesh_in_scene:
		if '_COPY' in trans:
			mesh_need_delete = trans.replace('_COPY', '')
			cmds.delete(mesh_need_delete)
			cmds.rename(trans, mesh_need_delete)

def move_face_bevel(spacing_value):
	mel.eval("DeleteHistory;")
	mel.eval("FreezeTransformations;")
	selected_object = cmds.ls(sl=True, fl=True)[0]
	cmds.select(selected_object +'.vtx[*]')
	selected_vertices = cmds.ls(sl=True,fl=True)
	cmds.polyMoveVertex(selected_vertices, lt=[0,0,spacing_value])
	cmds.select(selected_object)

def run_create_decal(*args):
	fraction_value = cmds.floatField('decal_fraction_ff', q=True, v=True)
	spacing_value = cmds.floatField('decal_spacing_ff', q=True, v=True)
	segment_value = cmds.intField('decal_segment_if', q=True, v=True)
	chamfer_value = cmds.checkBox('decal_chamfer_cb', q=True, v=True)
	
	cmds.undoInfo(openChunk=True)
	select_faces_after_bevel(segment_value, chamfer_value, fraction_value)
	duplicate_selected_faces()
	clean_old_mesh()
	move_face_bevel(spacing_value)
	cmds.undoInfo(closeChunk=True)

#endregion

#region Inflate
def run_inflate(inflate_operator):
	selected = cmds.ls(sl=True, fl=True)
	inflate_value = cmds.floatField('inflate_value_ff', q=True, v=True) * inflate_operator
	inflate_value_string = []

	tmp_vertex = cmds.ls(sl=True)
	select_vertex = cmds.polyListComponentConversion(tmp_vertex, tv=True)
	cmds.select(select_vertex)
	select_vertex = cmds.ls(sl=True, fl=True)

	for i in select_vertex:
		inflate_value_string.append(inflate_value)
	cmds.moveVertexAlongDirection(n=inflate_value_string)
	cmds.select(selected)
#endregion

#region LOD Tool
global object_lod_a
global object_lod_b
global current_lod_object

object_lod_a = ""
object_lod_b = ""

def store_object_a(*arg):
	global object_lod_a
	global current_lod_object
	object_lod_a = cmds.ls(sl=True, o=True)
	current_lod_object = object_lod_a
	cmds.warning("Object A has been stored!")
	
def store_object_b(*arg):
	global object_lod_b
	global current_lod_object
	object_lod_b = cmds.ls(sl=True, o=True)
	current_lod_object = object_lod_b
	cmds.warning("Object B has been stored!")

def swap_lod_object(*arg):
	global current_lod_object
	if object_lod_a != "" and object_lod_b != "":
		if current_lod_object == object_lod_a:
			cmds.hide(object_lod_b)
			cmds.showHidden(object_lod_a)
			current_lod_object = object_lod_b
		else:
			cmds.hide(object_lod_a)
			cmds.showHidden(object_lod_b)
			current_lod_object = object_lod_a
	else:
		cmds.warning("Please store 2 objects to swap!")	

#endregion

#region Screenshot Tool

screenshot_setting_data = {
	"top": {
		"rotation": [
			0.0,
			90.0,
			90.0
		]
	},
	"bottom": {
		"rotation": [
			180.0,
			-90.0,
			-90.0
		]
	},
	"front": {
		"rotation": [
			0.0,
			90.0,
			0.0
		]
	},
	"left": {
		"rotation": [
			0.0,
			0.0,
			0.0
		]
	},
	"right": {
		"rotation": [
			0.0,
			180.0,
			0.0
		]
	},
	"back": {
		"rotation": [
			0.0,
			-90.0,
			0.0
		]
	},
	"persp1": {
		"rotation": [
			-45.0,
			45.0,
			0.0
		]
	},
	"persp2": {
		"rotation": [
			-45.0,
			90.0,
			0.0
		]
	},
	"persp3": {
		"rotation": [
			-45.0,
			135.0,
			0.0
		]
	}
}

def write_json_file(path, content):
	# Serializing json 
	json_object = json.dumps(content, indent = 4)
	# Writing to sample.json
	with open(path, "w") as outfile:
		outfile.write(json_object)
	outfile.close()
	return True		

def get_screenshot_path(*arg):
	screenshot_path = cmds.file(q= True, sn= True)
	try:
		screenshot_path = cmds.fileDialog2(dir = screenshot_path, cap = 'Choose new screenshot path!', fm=3)[0]
	except:
		pass
	cmds.textField('screenshot_path_tf', e = True, tx = screenshot_path)

def create_new_camera(camera_name, *arg):
	obj = cmds.camera()
	cmds.rename(obj[0], camera_name)
	shape = cmds.listRelatives(camera_name, shapes=True)[0]
	cmds.rename(shape, camera_name + "Shape")
	cmds.hide(camera_name)
	return camera_name
 
def toggle_redundant_scene_element(mode):
	current_view = cmds.getPanel(withFocus=True)
	if mode == "Un-Hide":
		cmds.modelEditor(current_view, edit=True, grid=True)
		mel.eval('setCameraNamesVisibility(1);')
		mel.eval('setPolyCountVisibility(1);')
		mel.eval('setViewAxisVisibility(1);')
	else:
		cmds.modelEditor(current_view, edit=True, grid=False)
		mel.eval('setCameraNamesVisibility(0);')
		mel.eval('setPolyCountVisibility(0);')
		mel.eval('setViewAxisVisibility(0);')
		mel.eval('setViewportRendererVisibility(0);')

def modify_focus_camera(camera_name, camera_distance_threshold):
	camera_center = cmds.objectCenter(camera_name, gl=True)
	x_vector = camera_center[0]
	y_vector = camera_center[1]
	z_vector = camera_center[2]
	
	new_x = camera_center[0] + x_vector * camera_distance_threshold
	new_y = camera_center[1] + y_vector * camera_distance_threshold
	new_z = camera_center[2] + z_vector * camera_distance_threshold
	
	# Set attribute camera
	cmds.setAttr(camera_name + ".translateX", new_x)
	cmds.setAttr(camera_name + ".translateY", new_y)
	cmds.setAttr(camera_name + ".translateZ", new_z)

def screenshot_maya(destination_export, image_name, image_type, image_width, image_height):
	image_export = destination_export + "/" + image_name + "." + image_type
	mel.eval('setAttr "defaultRenderGlobals.imageFormat" 8;')
	cmds.playblast(completeFilename = image_export, 
					startTime=0,
					endTime=0,
					v=0,
					format="image",
					quality=100,
					percent=100,
					w=image_width,
					h=image_height,
					framePadding=0)
	return image_export

def screenshot_function(capture_mode, *arg):
	# Screenshot path
	screenshot_path = cmds.textField('screenshot_path_tf', q = True, tx = True).replace("\\", "/")
	# Screenshot type
	screenshot_type = "png"
	# Screenshot size
	screenshot_width = 3840
	screenshot_height = 2160
	# Screenshot filename
	file_name = cmds.file(q= True, sn= True).replace("\\", "/").rsplit("/", 1)[-1].rsplit(".", 1)[0]

	# Camera list
	list_camera_name = [key for key, value in screenshot_setting_data.items()]

	if capture_mode == "custom":
		tmp_image_name = file_name + "_custom_1"
		tmp_image_path = screenshot_path + "/" + file_name + "_custom_1.png"
		i = 1
		while os.path.exists(tmp_image_path):
			i += 1
			tmp_image_name = file_name + "_custom_" + str(i)
			tmp_image_path = screenshot_path + "/" + tmp_image_name + ".png"
		screenshot_maya(screenshot_path, tmp_image_name, screenshot_type, screenshot_width, screenshot_height)
	else:
		# Hide scene elements
		toggle_redundant_scene_element("Hide")
		
		# Capture multiple images
		for camera_name in list_camera_name:
			cmds.lookThru('persp')
			cmds.setAttr("persp.rotateX", screenshot_setting_data[camera_name]["rotation"][0])
			cmds.setAttr("persp.rotateY", screenshot_setting_data[camera_name]["rotation"][1])
			cmds.setAttr("persp.rotateZ", screenshot_setting_data[camera_name]["rotation"][2])
			selected_objects = cmds.ls(sl=True)
			zoom_value = float(cmds.intField('camera_zoom_value_if', q=True, v=True)) / 100
			if 'persp' not in camera_name:
				cmds.setAttr("perspShape.orthographic", 1)
				zoom_value = zoom_value - 0.2 # Balance value
			if cmds.ls(sl=True, fl=True):
				cmds.viewFit(f=zoom_value)
			else:
				cmds.viewFit(f=zoom_value, all=True)
			cmds.select(d=True)
			screenshot_maya(screenshot_path, file_name + "_"+ camera_name, screenshot_type, screenshot_width, screenshot_height)
			if len(selected_objects) > 0:
				cmds.select(selected_objects)
			cmds.setAttr("perspShape.orthographic", 0)
		
		# Hide scene elements
		toggle_redundant_scene_element("Un-Hide")

	# Open folder
	os.startfile(screenshot_path)

	return True

#endregion

#endregion

#region MAIN FUNCTION

#region Select

def select_dot_loop(*arg):
	# Get select mode
	try:
		select_mode = cmds.ls(sl=True, fl=True)[0].rsplit(".", 1)[-1].rsplit("[", 1)[0]
	except:
		select_mode = ""

	# Select dot loop
	if select_mode == "e":
		mel.eval("polySelectEdgesEveryN \"edgeLoopOrBorder\" " + str(cmds.intField('dot_loop_if', q=True, v=True)+1))
	elif select_mode == "f":
		selected_faces = cmds.ls(sl=True, fl=True)
		if len(selected_faces) != 2:
			message = "Please Select Two Adjacent Faces!"
			cmds.inViewMessage( amg='Error : <hl style=\"color:#FF0000;\">' + message + '</hl>', pos='midCenter', fade=True,bkc = 0X11550000,fit = 2)
			cmds.warning(message)
		else:
			mel.eval("ConvertSelectionToContainedEdges;")
			selected_edge = cmds.ls(sl=True, fl=True)[0]
			cmds.select(selected_edge)
			mel.eval('polySelectEdgesEveryN "edgeRing" 1;')
			tmp_edge = cmds.ls(sl=True, fl=True)
			dot_faces = cmds.ls(cmds.polyListComponentConversion(tmp_edge,tf=1),fl=1)
			edges = cmds.polyListComponentConversion(dot_faces,te=1)
			cmds.select(edges)
			final_edges = list(set(cmds.ls(sl=True, fl=True)) - set(tmp_edge))
			cmds.select(final_edges[-1])
			select_dot_loop()
			post_dot_face = cmds.ls(cmds.polyListComponentConversion(cmds.ls(sl=True, fl=True),tf=1),fl=1)
			final_faces = list(set(post_dot_face) & set(dot_faces))
			cmds.select(final_faces)
	elif select_mode == "vtx":
		message = "No support for vertex selection!"
		cmds.inViewMessage( amg='Error : <hl style=\"color:#FF0000;\">' + message + '</hl>', pos='midCenter', fade=True,bkc = 0X11550000,fit = 2)
		cmds.warning(message)
	else:
		message = "Invalid Selection!"
		cmds.inViewMessage( amg='Error : <hl style=\"color:#FF0000;\">' + message + '</hl>', pos='midCenter', fade=True,bkc = 0X11550000,fit = 2)
		cmds.warning(message)

def select_dot_ring(*arg):
	mel.eval("polySelectEdgesEveryN \"edgeRing\" " + str(cmds.intField('dot_ring_if', q=True, v=True)+1))

def select_similar(*arg):
		#  If objects selected then try to select all the same objects in the scene
	if cmds.filterExpand(sm=12):
			# empty array - adding all final similar objects.
		similarObjects = []
		
			# get selected object - base object to which you want to select all other similar ones
		selectedMainObj = cmds.ls (cmds.filterExpand(sm=12), sl=True, l=True, tr=True)
			
			# get all meshes in the scene (transforms)
		allSceneMeshes = cmds.filterExpand (cmds.ls (l=True, typ = 'transform'), sm=12)
		
		for i in range(len(selectedMainObj)):
			
			selVertices = cmds.polyEvaluate (selectedMainObj[i], vertex=True)         # get vertices count of base objects
			getArea = cmds.polyEvaluate (selectedMainObj[i], worldArea=True)          # get world Area (volume) 
			selecArea = round (getArea, 2)                                          # round worldArea numbers to 2 decimanls otherwise it will no select objects
			
			for j in range(len(allSceneMeshes)):
				toCompareVertices = cmds.polyEvaluate (allSceneMeshes[j], vertex=True)
				toGetArea = cmds.polyEvaluate (allSceneMeshes[j], worldArea=True)
				toCompareArea = round (toGetArea, 2)
				
				if selVertices == toCompareVertices and selecArea == toCompareArea:
					similarObjects.append(allSceneMeshes[j])
		  
		cmds.select (similarObjects, r=True)

		#  If components selected then use Maya defaul select similar tool.
	if cmds.filterExpand(sm=(31, 32, 34)):
		mel.eval ("SelectSimilar;")

def open_selection_set_tool(parent_window):
	if cmds.window('selection_set_tool_window', ex = True):
		cmds.deleteUI('selection_set_tool_window', window = True)

	cmds.window('selection_set_tool_window', title = 'Selection Set Tool', p=parent_window, rtf = True, mnb = False, mxb = False, ip=False)

	cmds.rowColumnLayout('selection_set_tool_layout', nr = 3, rh = [(1,35), (2,15), (3,100)], adj = 3, rs=[(1,5), (2,5), (3,10)])

	cmds.rowColumnLayout(nc = 2, cw = [(1, 100), (2,190)], adj = 2, cs = [(2,5)])
	cmds.button(l = 'Add Set:', h=30, bgc = (0.2, 0.8, 0.5), c=add_selection_set_to_list)
	cmds.textField('set_name_tf', tx='Set')
	cmds.setParent('..')
	cmds.rowColumnLayout(nc = 1, cw = [(1, 190)], adj = 1, cs = [(1,100)])
	cmds.text(l='Selection Set List', al='center')
	cmds.setParent('..')
	cmds.rowColumnLayout(nc = 2, cw = [(1, 100), (2,190)], adj = 2, cs = [(2,5)])
	cmds.columnLayout(columnAttach=('both', 1))
	cmds.button(l = 'Clear List', h=30, bgc = (0.8, 0.8, 0.8), c=clear_selection_set_list)
	cmds.setParent('..')
	cmds.textScrollList('selection_set_tsl', numberOfRows=6, allowMultiSelection=False)
	cmds.textScrollList('selection_set_tsl', edit=True, deleteKeyCommand=remove_item_in_selection_set_list, selectCommand=select_item_in_selection_set_list)
	cmds.setParent('..')

	cmds.window('selection_set_tool_window', e=True, s=False)
	cmds.showWindow('selection_set_tool_window')

def grow_selection_by_normal_angle(*arg):
	selection_cleanup_port.grow_selection_by_normal_angle(cmds.intSliderGrp('angle_selection_isg', q=True, value=True))

def update_selection_by_normal_angle(*arg):
	selection_cleanup_port.update_angle(cmds.intSliderGrp('angle_selection_isg', q=True, value=True))

#endregion

#region Instance
def instance_objects(*arg):
	cmds.undoInfo(openChunk = True)
	set_instance_objects()
	cmds.undoInfo(closeChunk = True) 

def set_instance_objects():
	array_three_points_verticies = []
	array_all_mesh = []

	mesh_select = cmds.ls(sl=True, l=True, fl=True)
	if len(mesh_select) == 1:
		cmds.warning("Please select at least 2 object")                        
		
	else:
		number = 0
		last_mesh = mesh_select[len(mesh_select)-1] 
		cmds.select(last_mesh, replace=True)

		mel.eval('ConvertSelectionToVertices;')
		list_verticies_select = cmds.ls(sl=True, fl=True) #Get all vertices of last mesh
		three_points_of_last_mesh = list_verticies_select[:3] #Get 3 first points of last mesh

		for mesh in mesh_select:
			if mesh != last_mesh:
				cmds.select(mesh, replace=True)
				mel.eval('ConvertSelectionToVertices;')
				list_verticies_of_mesh = cmds.ls(sl=True, fl=True) #Get all vertices of mesh
				three_points_of_mesh = list_verticies_of_mesh[:3] #Get 3 first points of mesh
				three_points_of_mesh.append(mesh)
				array_three_points_verticies.append(three_points_of_mesh) #Memorize 3 points of each mesh

		cmds.select(last_mesh, replace=True) #Select last mesh to prepare for instance
		array_all_mesh.append(last_mesh)

		while number < len(mesh_select)-1:
			old_mesh = array_three_points_verticies[number][3]
			name_old_mesh = array_three_points_verticies[number][3].split('|')[-1]
			parent_of_old_mesh = cmds.listRelatives(old_mesh, fullPath=True, parent=True)

			mesh_instance = cmds.instance(smartTransform=True) #Instance last mesh
			cmds.select(mesh_instance, replace=True)
			mel.eval('ConvertSelectionToVertices;')
			list_verticies_instance_mesh = cmds.ls(sl=True, fl=True) #Get all vertices of instance mesh
			three_points_of_instance_mesh = list_verticies_instance_mesh[:3] #Get 3 first points of instance mesh

			# Snap instance to current mesh
			cmds.select(array_three_points_verticies[number][:3], replace=True)
			cmds.select(three_points_of_instance_mesh, addFirst=True)
			mel.eval("snap3PointsTo3Points(0);")

			#replace instance to correct group
			parent_of_mesh_instance = cmds.listRelatives(mesh_instance, fullPath=True, parent=True)
			if parent_of_mesh_instance != parent_of_old_mesh:
				cmds.parent(mesh_instance, parent_of_old_mesh)

			#delete old mesh, rename instance
			cmds.delete(old_mesh)
			cmds.rename(mesh_instance, name_old_mesh)

			cmds.select(last_mesh, replace=True)
			array_all_mesh.append(mesh_instance)
			number = number+1   

def uninstance_objects(*arg):
	meshSelect = cmds.ls(sl=True)
	
	if meshSelect:
		for mesh in meshSelect:
			cmds.select(mesh, replace=True)
			mel.eval('convertInstanceToObject;')
			mel.eval('DeleteHistory;')
			mel.eval('FreezeTransformations;')
		
	else:
		cmds.headsUpMessage('PLEASE SELECT SOME MESH')

#endregion

#region Scene
def changeYZ(*args):
	current_axis = cmds.upAxis(q=True, axis=True) 
	if current_axis == "y": 
		cmds.upAxis(axis="z", rv=True) 
	elif current_axis == "z":
		cmds.upAxis(axis="y", rv=True)

def delete_history(*args):
	mel.eval('DeleteAllHistory')

def optimize_scene_size(*args):
	mel.eval('OptimizeScene;')

def FCC(*args):
	selection_cleanup_port.force_clean_up_by_combine_preprocess()

def unhide_all(*args):
	mel.eval('ShowAll;')
	mel.eval('hide `listCameras`;')


def toggle_pink_color(*args):
	# currentPanel = cmds.getPanel(withFocus=True)
	print(cmds.displayRGBColor("background", q=True))
	if (cmds.displayRGBColor("background", q=True) == [0.5, 0.5, 0.5]):
		cmds.displayRGBColor("background", 1, 0, 1)
		# cmds.modelEditor(currentPanel, dl="all")
	else:
		cmds.displayRGBColor("background", 0.5, 0.5, 0.5)
		# cmds.modelEditor(currentPanel, dl="default") 
	cmds.displayPref(displayGradient=False)

#endregion

#region Pivot
def freeze_transforms(*args):
	mel.eval('FreezeTransformations;')

def reset_transforms(*args):
	mel.eval('ResetTransformations;')

def center_pivot(*args):
	mel.eval('CenterPivot')

def show_set_maxmin_pivot_window(*arg):
	if cmds.window('set_center_pivot_window', ex = True):
		cmds.deleteUI('set_center_pivot_window', window = True)
	cmds.window('set_center_pivot_window', title = 'Set Center Pivot Tool', rtf = True, mnb = False, mxb = False)

	cmds.columnLayout('col',adj = 1, rs = 5)
	
	cmds.rowColumnLayout(nc = 3, cw = [(1, 60), (2, 60), (3, 60)], adj = 3, cs = [(2,5), (3,5)])	
	cmds.button(l = 'X Max', h=30, bgc=(0.8, 0.27, 0.2), c = lambda *args: set_pivot_to_objects('x_max'))
	cmds.button(l = 'Y Max', h=30, bgc = (0.2, 0.8, 0.5), c = lambda *args: set_pivot_to_objects('y_max'))
	cmds.button(l = 'Z Max', h=30, bgc=(0.2, 0.43, 0.8), c = lambda *args: set_pivot_to_objects('z_max'))
	cmds.setParent('..')
	
	cmds.rowColumnLayout(nc = 3, cw = [(1, 60), (2, 60), (3, 60)], adj = 3, cs = [(2,5), (3,5)])	
	cmds.button(l = 'X Min', h=30, bgc=(0.8, 0.27, 0.2), c = lambda *args: set_pivot_to_objects('x_min'))
	cmds.button(l = 'Y Min', h=30, bgc = (0.2, 0.8, 0.5), c = lambda *args: set_pivot_to_objects('y_min'))
	cmds.button(l = 'Z Min', h=30, bgc=(0.2, 0.43, 0.8), c = lambda *args: set_pivot_to_objects('z_min'))
	cmds.setParent('..')
	
	cmds.setParent('..')
	
	cmds.window('set_center_pivot_window', e=True, s=False)
	cmds.showWindow('set_center_pivot_window')
#endregion

#region Circle
def _circle_input_values():
	use_average_distance = not cmds.checkBox('circle_diameter_cb', q=True, v=True)
	use_average_angle = not cmds.checkBox('circle_angle_cb', q=True, v=True)
	diameter_value = cmds.floatField('circle_diameter_fl', q=True, v=True)
	angle_value = cmds.floatField('circle_angle_fl', q=True, v=True)
	return use_average_distance, use_average_angle, diameter_value, angle_value


def align_circle_vertices(*args):
	use_average_distance, use_average_angle, diameter_value, angle_value = _circle_input_values()
	circle_polygon_port.circle_vertices(0, use_average_distance, use_average_angle, diameter_value, angle_value, priority_vertex_components)


def get_circle_diameter_input(*args):
	use_average_distance, use_average_angle, diameter_value, angle_value = _circle_input_values()
	result = circle_polygon_port.circle_vertices(1, use_average_distance, use_average_angle, diameter_value, angle_value, priority_vertex_components)
	if 'distance' in result:
		change_circle_diameter_value(result['distance'])


def get_circle_angle_input(*args):
	use_average_distance, use_average_angle, diameter_value, angle_value = _circle_input_values()
	result = circle_polygon_port.circle_vertices(2, use_average_distance, use_average_angle, diameter_value, angle_value, priority_vertex_components)
	if 'angle' in result:
		change_circle_angle_value(result['angle'])

#endregion

#region Combine / Detach / Clone / Detach By Material
def combine_object(*arg):
	combine_detach_clone_port.combine_objects()

def detach_object(*arg):
	combine_detach_clone_port.detach_faces()

def clone_object(*arg):
	combine_detach_clone_port.clone_faces()

def getListShadingEngine(*arg):
	'''Selection mesh return Material assign for mesh'''
	sel_mesh = cmds.ls(sl=True, long = True, flatten = True)
	mesh_shapes = cmds.listRelatives(sel_mesh, shapes=True, type='mesh', fullPath = True ) # select Shape of Transform
	list_materials = cmds.listConnections( mesh_shapes, source=False, type='shadingEngine')  # query list Material assgin for Shape
	# listConnections -d on -s off mtl_PaintBlue.outColor
	return list(set(list_materials))  

def detachMaterial(*arg):
	count = len(getListShadingEngine())
	listNewMesh = []
	while count > 0:
		base_mesh =  cmds.ls(sl=True)[0]
		getListShadingEngine()
		list_materials =   getListShadingEngine()
		get_material = list_materials.pop(count -1) 
		name_material = cmds.listConnections(get_material + '.surfaceShader' ) # Get name material
		
		mel.eval('Duplicate;')
		list_faces = cmds.sets(list_materials , q=True )
		list_faces_del = []
		mesh_duplicate =  cmds.ls(sl=True)[0]
		if list_faces:
			for f in list_faces:
				if f.split('.f')[0] == mesh_duplicate:
					list_faces_del.append(f)
		# cmds.select(list_faces)
		cmds.delete(list_faces_del)
		cmds.select(base_mesh)
		listNewMesh.append(mesh_duplicate)
		count -= 1
	cmds.delete()
	cmds.rename(listNewMesh[-1], base_mesh)

def detach_by_material(*arg):
	list_mesh = cmds.ls(sl=True, long = True, flatten = True)
	for mesh in list_mesh:
		cmds.select(mesh, replace = True)
		shape_sel = cmds.listRelatives(mesh, shapes=True, fullPath = True)[0]
		if cmds.nodeType(shape_sel) == 'mesh':
			get_material = getListShadingEngine()
			name_material = cmds.listConnections(get_material[0] + '.surfaceShader' )

			detachMaterial()
	cmds.warning('Detach: Done!')

#endregion

#region Speed Tool
def change_cylinder_segment_value_ui(*args):
	height, radius, segment = get_cylinder_attributes()
	cmds.intField('cylinder_segment_if', e=True, v=segment)

def create_cylinder(*args):
	height, radius, segment = get_cylinder_attributes()
	name = 'Cylinder_' + str(radius*2).rstrip('0').replace('.', 'cm') + '_' + str(segment)
	if cmds.currentUnit(q=True, l=True) == 'm':
		cmds.polyCylinder(n=name, cch =True, ch=True, h=height* 0.01, r=radius* 0.01, sa=segment)
	else:
		cmds.polyCylinder(n=name, cch =True, ch=True, h=height, r=radius, sa=segment)

def get_cylinder_attributes(*args):
	diameter_list = [(1.25, 8), (2.5, 12), (5.0, 18), (10.0, 24), (20.0, 30), (30.0, 36), (40.0, 42), (50.0, 48), (60.0, 54), (70.0, 60), (80.0, 60), (90.0, 60), (100.0, 60)]
	# unit: meter
	diameter = cmds.floatField('cylinder_diameter_ff', q=True, v=True)

	for i in range(0, len(diameter_list)):
		if diameter < diameter_list[0][0]:
			segment = diameter_list[0][1]
			break
		if diameter > diameter_list[-1][0]:
			segment = diameter_list[-1][1]
			break
		if diameter == diameter_list[i][0]:
			segment = diameter_list[i][1]
			break
		if i < len(diameter_list) - 1:
			if diameter < diameter_list[i+1][0] and diameter > diameter_list[i][0]:
				segment = diameter_list[i][1] if (diameter - diameter_list[i][0] < ((diameter_list[i+1][0] - diameter_list[i][0]) / 2)) else diameter_list[i+1][1]
				break
	return diameter, diameter/2, segment

def get_edge_length(*args):
	selected_edges = cmds.filterExpand(sm=32)
	if selected_edges is not None:
		length_list = []
		for edge in selected_edges:
			length_list.append(cmds.arclen(edge))
		average_length = sum(length_list) / len(length_list)
		cmds.floatField('length_ff', v=average_length, e=True)
	else:
		cmds.error("Please select an edge.")

def set_edge_length(*args):
	all_lock_vertices = get_all_items_in_list('lock_vertex_list')
	puv_value = cmds.checkBox('check_preserve_UV_cb', q=True, v=True)
	selected_edges = cmds.filterExpand(sm=32)
	source_length = cmds.floatField('length_ff', q=True, v=True)
	symmetry_value = cmds.symmetricModelling(q=True, s=True)
	error_edges = []
	for edge in selected_edges:
		cmds.symmetricModelling(e=True, s=False)
		target_length = cmds.arclen(edge)
		scale_val = source_length / target_length
		cmds.select(cl=True)
		cmds.select(edge)
		if all_lock_vertices is not None:
			inc_vertices = cmds.ls(cmds.polyListComponentConversion(edge, tv=True), fl=True)
			locked_vertex = lock_vertex(inc_vertices, all_lock_vertices)
			if len(locked_vertex) == 1:
				pivot_pos = cmds.pointPosition(locked_vertex)
				cmds.scale(1, scale_val, 1, cs=True, a=True, p=pivot_pos, puv=puv_value)
			elif len(locked_vertex) >= 2:
				error_edges.append(edge)
			else:
				cmds.scale(1, scale_val, 1, cs=True, a=True, puv=puv_value)
		else:
			cmds.scale(1, scale_val, 1, cs=True, a=True, puv=puv_value)
	if len(error_edges) >= 1:
		cmds.select(cl=True)
		cmds.select(error_edges)
		cmds.symmetricModelling(e=True, s=symmetry_value)
		cmds.warning("Both vertices are locked.")
	else:
		cmds.select(cl=True)
		cmds.select(selected_edges)
		cmds.symmetricModelling(e=True, s=symmetry_value)

def lock_vertex(inc_vertices, all_lock_vertices, *args):
	match_vertices = []
	for inc_vertex in inc_vertices:
		if inc_vertex not in all_lock_vertices:
			continue
		else:
			match_vertices.append(inc_vertex)
	return match_vertices

def add_lock_vertex(*args):
	allItems = get_all_items_in_list('lock_vertex_list')
	sel = cmds.ls(os=True, fl=True)
	sel_vertices = cmds.ls(cmds.polyListComponentConversion(sel, tv=True), fl=True)
	cmds.select(sel_vertices)
	if sel_vertices is not None:
		if allItems is not None:
			for sel_vertex in sel_vertices:
				if sel_vertex not in allItems:
					cmds.textScrollList('lock_vertex_list', e=True, a=sel_vertex)
		else:
			cmds.textScrollList('lock_vertex_list', e=True, a=sel_vertices)
	else:
		cmds.error("Please Select Vertices.")

def select_item_in_list(*args):
	selItem = cmds.textScrollList('lock_vertex_list', q=True, selectItem=True)
	cmds.select(cl=True)
	cmds.select(selItem)

def clear_list(*args):
	cmds.textScrollList('lock_vertex_list', edit=True, removeAll=True)

def remove_item_in_list(*args):
	selected_item = cmds.textScrollList('lock_vertex_list', q=True, selectItem=True)
	if selected_item is not None:
		cmds.textScrollList('lock_vertex_list', edit=True, removeItem=selected_item)

def get_all_items_in_list(*args):
	all_items = cmds.textScrollList('lock_vertex_list', q=True, allItems=True)
	return all_items

def set_edge_length_ascending_descending(*args):
	all_lock_vertices = get_all_items_in_list('lock_vertex_list')
	error_edges = []
	selected_edges = cmds.filterExpand(sm=32)
	if selected_edges is not None:
		symmetry_value = cmds.symmetricModelling(q=True, s=True)
		if len(selected_edges) == 2:
			# Get diffrence length
			diffrence = abs(cmds.arclen(selected_edges[0]) - cmds.arclen(selected_edges[-1]))
			# Detect longer edge
			if cmds.arclen(selected_edges[0]) >= cmds.arclen(selected_edges[-1]):
				short_edge = selected_edges[-1]
				short_edge_length = cmds.arclen(selected_edges[-1])
			else:
				short_edge = selected_edges[0]
				short_edge_length = cmds.arclen(selected_edges[0])
			# Get order edge list
			checked_face_list = []
			ordered_edge_list = [short_edge]
			next_edge = short_edge
			mel.eval('SelectEdgeRingSp;')
			edges = cmds.ls(sl=True, fl=True)
			for i in range(0, len(edges)):
				adjacent_faces = cmds.ls(cmds.polyListComponentConversion(next_edge, tf=True), fl=True)
				for j in range(0, len(adjacent_faces)):
					if adjacent_faces[j] not in checked_face_list:
						checked_face_list.append(adjacent_faces[j])
						adjacent_edges = cmds.ls(cmds.polyListComponentConversion(adjacent_faces[j], te=True), fl=True)
						for k in range(0, len(adjacent_edges)):
							if (adjacent_edges[k] in edges) and (adjacent_edges[k] not in ordered_edge_list):
								ordered_edge_list.append(adjacent_edges[k])
								next_edge = adjacent_edges[k]
								break
			# Set Length
			del ordered_edge_list[0]
			for i in range(0, len(ordered_edge_list)):
				cmds.symmetricModelling(e=True, s=False)
				target_length = cmds.arclen(ordered_edge_list[i])
				source_length = short_edge_length + diffrence / len(ordered_edge_list) * (i+1)
				scale_val = source_length / target_length
				cmds.select(cl=True)
				cmds.select(ordered_edge_list[i])

				if all_lock_vertices is not None:
					inc_vertices = cmds.ls(cmds.polyListComponentConversion(ordered_edge_list[i], tv=True), fl=True)
					locked_vertex = lock_vertex(inc_vertices, all_lock_vertices)
					if len(locked_vertex) == 1:
						pivot_pos = cmds.pointPosition(locked_vertex)
						cmds.scale(1, scale_val, 1, cs=True, a=True, p=pivot_pos, puv=False)
					elif len(locked_vertex) >= 2:
						error_edges.append(ordered_edge_list[i])
					else:
						cmds.scale(1, scale_val, 1, cs=True, a=True, puv=False)
				else:
					cmds.scale(1, scale_val, 1, cs=True, a=True, puv=False)
		elif len(selected_edges) > 2 and (len(selected_edges)%2==0):
			# Edge Loop Selection
			selected_edges = cmds.ls(sl=True, fl=True)
			# Get number edge of loop
			edge_number = len(selected_edges) / 2
			# Detect first and last edge loop
			cmds.select(selected_edges[0])
			mel.eval('SelectEdgeLoopSp;')
			if len(cmds.ls(sl=True, fl=True)) != edge_number:
				cmds.polySelectConstraint(pp=4, m2a=180.0, m3a=89.0)
			first_edge_loop = cmds.ls(sl=True, fl=True)
			second_edge_loop = list(set(selected_edges) - set(first_edge_loop))
			# Detect bigger loop
			cmds.select(first_edge_loop)
			get_circle_diameter_input()
			first_loop_diameter = cmds.floatField('circle_diameter_fl', q=True, v=True)
			cmds.select(second_edge_loop)
			get_circle_diameter_input()
			second_loop_diameter = cmds.floatField('circle_diameter_fl', q=True, v=True)
			cmds.floatField('circle_diameter_fl', e=True, v=0.0)
			
			if first_loop_diameter >= second_loop_diameter:
				big_loop = first_edge_loop
				small_loop = second_edge_loop
				big_loop_diameter = first_loop_diameter
				small_loop_diameter = second_loop_diameter
			else:
				big_loop = second_edge_loop
				small_loop = first_edge_loop
				big_loop_diameter = second_loop_diameter
				small_loop_diameter = first_loop_diameter

			# Get order edge loop list
			edge_loop_list = []
			cmds.select(selected_edges)
			mel.eval('SelectEdgeRingSp;')
			all_edges = cmds.ls(sl=True, fl=True)
			edge_loop_list.append(small_loop)
			all_edges = list(set(all_edges) - set(small_loop))
			current_adjacent_faces = cmds.ls(cmds.polyListComponentConversion(small_loop, tf=True), fl=True)
			current_adjacent_edges = cmds.ls(cmds.polyListComponentConversion(current_adjacent_faces, te=True), fl=True)
			i = 0
			while len(all_edges) > 0:
				cmds.select(all_edges[i])
				mel.eval('SelectEdgeLoopSp;')
				if len(cmds.ls(sl=True, fl=True)) != edge_number:
					cmds.polySelectConstraint(pp=4, m2a=180.0, m3a=89.0)
				current_edge_loop = cmds.ls(sl=True, fl=True)
				check_adjacent = len(list(set(current_adjacent_edges) - set(current_edge_loop))) - len(current_adjacent_edges)
				if check_adjacent < 0:
					edge_loop_list.append(current_edge_loop)
					all_edges = list(set(all_edges) - set(current_edge_loop))
					current_adjacent_faces = cmds.ls(cmds.polyListComponentConversion(current_edge_loop, tf=True), fl=True)
					current_adjacent_edges = cmds.ls(cmds.polyListComponentConversion(current_adjacent_faces, te=True), fl=True)
					i = 0
				else:
					i += 1
			diameter_value = big_loop_diameter - small_loop_diameter
			# Set new edge loop diameter
			for i in range(0, len(edge_loop_list)):
				cmds.select(edge_loop_list[i])
				new_diameter = small_loop_diameter + i * diameter_value / (len(edge_loop_list)-1)
				circle_polygon_port.circle_vertices(0, False, True, new_diameter, 0.0, priority_vertex_components)

		# Clear
		if len(error_edges) >= 1:
			cmds.select(cl=True)
			cmds.select(error_edges)
			cmds.symmetricModelling(e=True, s=symmetry_value)
			cmds.warning("Some vertices are locked.")
		else:
			cmds.select(cl=True)
			cmds.select(selected_edges)
			cmds.symmetricModelling(e=True, s=symmetry_value)
	else:
		return False

def reset_object_rotation(*args):
	cmds.undoInfo(ock=True)
	selected = cmds.ls(sl=True, fl=True)
	if len(selected) == 0:
		cmds.warning('Please select 1 Object / 1 Face / 2 Edges / 3 Vertices!')
		return
	for s in selected:
		cmds.select(s)
		align_pivot()
	selected_obj = cmds.ls(sl=True)[0]
	cmds.setAttr(selected_obj + '.rotateX', 0)
	cmds.setAttr(selected_obj + '.rotateY', 0)
	cmds.setAttr(selected_obj + '.rotateZ', 0)
	cmds.undoInfo(cck=True)

def split_polygon(*args):
	cmds.undoInfo(ock=True)
	mel.eval("DeleteHistory;")
	circle_polygon_port.split_polygon()
	cmds.undoInfo(cck=True)

def quad_fill(*arg):
	cmds.undoInfo(ock=True)
	edge_selection = cmds.ls(os=True)
	if edge_selection:
		if '.e[' in edge_selection[0]:
			border_edges = buKi_get_border_edges(edge_selection[0])
			if len(border_edges) % 2 == 0:
				corner_edges = []
				if len(edge_selection) == 1:
					(face_list_A, face_list_B) = buKi_get_face_neighbours_from_vtx(edge_selection[0])
					if len(face_list_A) == 3 or len(face_list_B) == 3:
						edges_to_check = buKi_create_loop_list(border_edges, edge_selection[0])[1:]
						tmp_list = [
							edge_selection[0]]
						check_direction_val = 1
						direction = 'right'
						for e in edges_to_check:
							(face_list_C, face_list_D) = buKi_get_face_neighbours_from_vtx(e)
							if len(face_list_C) == 3 or len(face_list_D) == 3:
								if check_direction_val == 1:
									direction = 'left'
								tmp_list.append(e)
							check_direction_val += 1
						
						if direction == 'left':
							tmp_order = [
								tmp_list[0],
								tmp_list[3],
								tmp_list[4],
								tmp_list[7]]
							edge_selection = [
								tmp_order[0],
								tmp_order[3],
								tmp_order[1],
								tmp_order[2]]
						if direction == 'right':
							tmp_order = [
								tmp_list[0],
								tmp_list[1],
								tmp_list[4],
								tmp_list[5]]
							edge_selection = [
								tmp_order[0],
								tmp_order[1],
								tmp_order[3],
								tmp_order[2]]
						elif len(border_edges) % 4 == 0:
							side_length = int(len(border_edges) / 4)
							position = 0
							for i in range(4):
								if sys.version[:2] == '3.':
									corner_edges.append(int(float(border_edges[position])))
								else:
									corner_edges.append(int(border_edges[position]))
								position = position + side_length
							
							tmp_var = corner_edges.pop()
							corner_edges.insert(-1, tmp_var)
						else:
							side_long = round(len(border_edges) * 0.3)
							side_short = round(len(border_edges) * 0.2)
							positions = [
								0,
								side_long,
								2 * side_long + side_short,
								side_long + side_short]
							for pos in positions:
								if sys.version[:2] == '3.':
									corner_edges.append(int(float(border_edges[pos])))
								else:
									corner_edges.append(int(border_edges[pos]))
							
					edge_selection = buKi_create_loop_list(corner_edges, edge_selection[0])
				if len(edge_selection) == 4:
					for edge in edge_selection:
						tmp_var = ('%s' % edge).split('.e')
						number = tmp_var[1]
						number = number[1:]
						number = number[:-1]
						if sys.version[:2] == '3.':
							corner_edges.append(int(float(number)))
						else:
							corner_edges.append(int(number))
					
				if corner_edges:
					rowA = cmds.polySelect(q=True, ebp=(corner_edges[0], corner_edges[1]))
					rowA = buKi_create_loop_list(rowA, edge_selection[0])
					rowB = cmds.polySelect(q=True, ebp=(corner_edges[2], corner_edges[3]))
					rowB = buKi_create_loop_list(rowB, edge_selection[0])
					sideA = cmds.polySelect(q=True, ebp=(corner_edges[0], corner_edges[2]))
					sideA = buKi_create_loop_list(sideA, edge_selection[0])
					sideB = cmds.polySelect(q=True, ebp=(corner_edges[1], corner_edges[3]))
					sideB = buKi_create_loop_list(sideB, edge_selection[0])
					for i in edge_selection:
						if i in rowA:
							rowA.remove(i)
						if i in rowB:
							rowB.remove(i)
						if i in sideA:
							sideA.remove(i)
						if i in sideB:
							sideB.remove(i)
					divisionAmount = len(sideA) - 1
					cmds.polyBridgeEdge(rowA, rowB, dv=divisionAmount, ch=1, ctp=0, twt=0, tp=1, sma=30, d=0, sd=0, td=0)
					cmds.select(edge_selection[0], edge_selection[2])
					buki_append_ring_loop()
					cmds.select(edge_selection[1], edge_selection[3])
					buki_append_ring_loop()
				else:
					cmds.warning('Missing correct edge input.')
			else:
				cmds.warning('The amount of border edges is not an even number.')
		else:
			cmds.warning('Please select edges.')
	else:
		cmds.warning('Please select 1 or 4 corner edges.')
	cmds.undoInfo(cck=True)

def smart_fill_hole(*arg):
	cmds.undoInfo(ock=True)
	currentSel = cmds.ls(sl=True, fl=True)
	if len(currentSel) == 0:
		cmds.warning('Please select 2 vertices / 1 Edge at Hole!')
		return
	if check_component_type(currentSel) == 'vertice' and len(currentSel) == 2:
		mult = 1.0
		vertSel = cmds.ls(os=1, fl=1)
		vertSel = cmds.ls(cmds.filterExpand(vertSel, sm=31), fl=1)
		obj = find_node_transform(cmds.ls(sl=1, o=1))
		origPolyCount = cmds.polyEvaluate(obj, f=1)
		edgePair = expand_vert_to_edge_along_border(vertSel[0])
		if not edgePair:
			if int(cmds.about(version=True)) < 2018:
				cmds.warning('Verts that are adjacent to the other open borders can be incompatible in this vertion of Maya.\nAdd edgeloops to separate open borders.')
			else:
				cmds.warning('Could not find a compatible edge loop. Please try another vertex selection.')
			return 0
		edgeBorder = expand_edge_to_border(edgePair[0])
		if len(edgeBorder) < 4:
			cmds.warning('Could not find a compatible edge loop. Please try another vertex selection.')
			return 0
		if len(edgeBorder) % 2 != 0:
			cmds.warning('The number of edges must be even')
			return 0
		vertsBorder = get_verts_gstool(edgeBorder)
		if len(vertSel) > 1 and (vertSel[0] not in vertsBorder or vertSel[1] not in vertsBorder):
			cmds.warning('Both selected verts should be on the same border')
			return 0
		borderLoop = sortEdgeBorder(vertSel, edgeBorder, edgePair)
		rowCount = int(get_row_count(borderLoop, vertSel))
		columnCount = int((len(borderLoop) - 2 * rowCount) / 2)
		if rowCount == 0:
			cmds.warning('Row Count is 0. Please try another vertex selection')
			return 0
		cmds.delete(obj, ch=1)
		side1, side2, corner1, corner2, corner3, corner4 = get_sides_and_corners(borderLoop, rowCount, columnCount)
		matrix, rows, columns = initMatrix(borderLoop, side1, side2, corner2, corner4)
		addQuads(obj, mult, matrix, rows, columns, corner1, corner2, corner3, corner4)
		finalPolyCount = cmds.polyEvaluate(obj, f=1)
		capFaces = '%s.f[%s:%s]' % (obj[0], origPolyCount, finalPolyCount)
		capInternalEdges = cmds.polyListComponentConversion(capFaces, ff=1, te=1)
		cmds.polySoftEdge(capInternalEdges, a=30, ch=0)
		cmds.polyNormal(obj[0], nm=1, unm=0, ch=0)
		cmds.select(capFaces, r=1)
	elif check_component_type(currentSel) == 'edge' and len(currentSel) == 1:
		edge_selection = cmds.ls(os=True)
		if edge_selection:
			if '.e[' in edge_selection[0]:
				border_edges = buKi_get_border_edges(edge_selection[0])
				if len(border_edges) % 2 == 0:
					corner_edges = []
					if len(edge_selection) == 1:
						face_list_A, face_list_B = buKi_get_face_neighbours_from_vtx(edge_selection[0])
						if len(face_list_A) == 3 or len(face_list_B) == 3:
							edges_to_check = buKi_create_loop_list(border_edges, edge_selection[0])[1:]
							tmp_list = [edge_selection[0]]
							check_direction_val = 1
							direction = 'right'
							for e in edges_to_check:
								face_list_C, face_list_D = buKi_get_face_neighbours_from_vtx(e)
								if len(face_list_C) == 3 or len(face_list_D) == 3:
									if check_direction_val == 1:
										direction = 'left'
									tmp_list.append(e)
								check_direction_val += 1

							if direction == 'left':
								tmp_order = [tmp_list[0], tmp_list[3], tmp_list[4], tmp_list[7]]
								edge_selection = [tmp_order[0], tmp_order[3], tmp_order[1], tmp_order[2]]
							if direction == 'right':
								tmp_order = [tmp_list[0], tmp_list[1], tmp_list[4], tmp_list[5]]
								edge_selection = [tmp_order[0], tmp_order[1], tmp_order[3], tmp_order[2]]
						else:
							if len(border_edges) % 4 == 0:
								side_length = int(len(border_edges) / 4)
								position = 0
								for i in range(4):
									if sys.version[:2] == '3.':
										corner_edges.append(int(float(border_edges[position])))
									else:
										corner_edges.append(int(border_edges[position]))
									position = position + side_length

								tmp_var = corner_edges.pop()
								corner_edges.insert(-1, tmp_var)
							else:
								side_long = round(len(border_edges) * 0.3)
								side_short = round(len(border_edges) * 0.2)
								positions = [0, side_long, 2 * side_long + side_short, side_long + side_short]
								for pos in positions:
									if sys.version[:2] == '3.':
										corner_edges.append(int(float(border_edges[pos])))
									else:
										corner_edges.append(int(border_edges[pos]))

							edge_selection = buKi_create_loop_list(corner_edges, edge_selection[0])
					if len(edge_selection) == 4:
						for edge in edge_selection:
							tmp_var = ('%s' % edge).split('.e')
							number = tmp_var[1]
							number = number[1:]
							number = number[:-1]
							if sys.version[:2] == '3.':
								corner_edges.append(int(float(number)))
							else:
								corner_edges.append(int(number))

					if corner_edges:
						rowA = cmds.polySelect(q=True, ebp=(corner_edges[0], corner_edges[1]))
						rowA = buKi_create_loop_list(rowA, edge_selection[0])
						rowB = cmds.polySelect(q=True, ebp=(corner_edges[2], corner_edges[3]))
						rowB = buKi_create_loop_list(rowB, edge_selection[0])
						sideA = cmds.polySelect(q=True, ebp=(corner_edges[0], corner_edges[2]))
						sideA = buKi_create_loop_list(sideA, edge_selection[0])
						sideB = cmds.polySelect(q=True, ebp=(corner_edges[1], corner_edges[3]))
						sideB = buKi_create_loop_list(sideB, edge_selection[0])
						for i in edge_selection:
							if i in rowA:
								rowA.remove(i)
							if i in rowB:
								rowB.remove(i)
							if i in sideA:
								sideA.remove(i)
							if i in sideB:
								sideB.remove(i)

						divisionAmount = len(sideA) - 1
						cmds.polyBridgeEdge(rowA, rowB, dv=divisionAmount, ch=1, ctp=0, twt=0, tp=1, sma=30, d=0, sd=0, td=0)
						cmds.select(edge_selection[0], edge_selection[2])
						buki_append_ring_loop()
						cmds.select(edge_selection[1], edge_selection[3])
						buki_append_ring_loop()
					else:
						cmds.warning('Missing correct edge input.')
				else:
					cmds.warning('The amount of border edges is not an even number.')
			else:
				cmds.warning('Please select edges.')
		else:
			cmds.warning('Please select 1 or 4 corner edges.')
	else:
		cmds.warning('Please select 1 Edge / 2 Vertex')
	cmds.undoInfo(cck=True)

def match_scale(*args):
	edges = cmds.ls(sl=True, fl=True)
	if edges and len(edges) == 2 and edges[0].rsplit('.', 1)[0] != edges[-1].rsplit('.', 1)[0]:
		if (cmds.selectPref(tso=True, q=True)==0):
			cmds.selectPref(tso=True)
		edges = cmds.ls(orderedSelection=True, fl=True)
		scale_ratio = cmds.arclen(edges[-1]) / cmds.arclen(edges[0])
		scale_object = edges[0].rsplit('.', 1)[0]
		cmds.scale(scale_ratio, scale_ratio, scale_ratio, scale_object, absolute=True)
		cmds.select(scale_object)
	else:
		cmds.warning('Please select corresponding edge in each object!')

def smart_extend(*args):
	cmds.undoInfo(ock=True)
	currentSel = cmds.ls(sl=True, fl=True)
	if len(currentSel) == 0:
		cmds.warning('Please select 1 Vertex / 1 Edge / 2 Edges!')
		return
	mesh_name = cmds.ls(currentSel, o=True)
	cmds.delete(mesh_name, ch=True)
	if len(currentSel) == 2:
		buki_append_ring_loop()
	elif check_component_type(currentSel) == 'vertice':
		edgeSel = cmds.ls(cmds.polyListComponentConversion(currentSel, te=True), fl=True)
		borderEdges = []
		for i in edgeSel:
			faceConv = cmds.ls(cmds.polyListComponentConversion(i, tf=True), fl=True)
			if len(faceConv) == 1:
				borderEdges.append(i)
		V1 = cmds.ls(cmds.polyListComponentConversion(borderEdges[0], tv=True), fl=True)
		V1.remove(currentSel[0])
		P1 = cmds.pointPosition(V1[0], w=True)
		P2 = cmds.pointPosition(currentSel[0], w=True)
		V3 = cmds.ls(cmds.polyListComponentConversion(borderEdges[1], tv=True), fl=True)
		V3.remove(currentSel[0])
		P3 = cmds.pointPosition(V3[0], w=True)
		P4 = MAS_list_points(P2, P1, '-')
		P4 = MAS_list_points(P4, -1, '*')
		P4 = MAS_list_points(P3, P4, '+')
		edgeNum1 = re.split('\\[(.*?)\\]', borderEdges[0])
		edgeNum2 = re.split('\\[(.*?)\\]', borderEdges[1])
		mel.eval('polyAppend -ch 0 -ed %s -ed %s %s;' % (edgeNum2[1], edgeNum1[1], mesh_name[0]))
		cmds.select(V1, V3)
		mel.eval('ConvertSelectionToContainedEdges;')
		containEdge = cmds.ls(sl=True)
		cmds.polySubdivideEdge(containEdge, ws=False, s=False, dv=1, ch=False)
		V4 = cmds.ls(cmds.polyListComponentConversion(cmds.ls(sl=True), tv=True), fl=True)
		V4.remove(V1[0])
		V4.remove(V3[0])
		cmds.move(P4[0], P4[1], P4[2], V4, ws=True, a=True)
		if len(cmds.ls(cmds.polyListComponentConversion(V1, te=True), fl=True)) == 4 and len(cmds.ls(cmds.polyListComponentConversion(V3, te=True), fl=True)) == 4:
			cmds.select(V3)
		elif len(cmds.ls(cmds.polyListComponentConversion(V1, te=True), fl=True)) == 4:
			cmds.select(V1)
		else:
			cmds.select(V3)
	elif check_component_type(currentSel) == 'edge':
		currentSel = cmds.ls(sl=True, fl=True)
		if len(currentSel) != 1:
			return
		border_edges = []
		tmp_base_verts = cmds.ls(cmds.polyListComponentConversion(currentSel, tv=True), fl=True)
		tmp_border_edges = buKi_get_border_edges(currentSel[0])
		tmp_border_edges = buKi_create_loop_list(tmp_border_edges, currentSel[0])
		tmp_border_edges.remove(currentSel[0])
		for e in tmp_border_edges:
			tmp_verts = cmds.ls(cmds.polyListComponentConversion(e, tv=True), fl=True)
			for v in tmp_verts:
				if v in tmp_base_verts:
					border_edges.append(e)

		cmds.polyBridgeEdge(border_edges, ch=False, sma=30, dv=0)
		border_edges.append(currentSel[0])
		tmp_verts = cmds.ls(cmds.polyListComponentConversion(border_edges, tv=True), fl=True)
		cmds.select(tmp_verts)
		cmds.ConvertSelectionToContainedFaces()
		new_edge = cmds.ls(cmds.polyListComponentConversion(cmds.ls(sl=True), te=True), fl=True)
		for e in border_edges:
			new_edge.remove(e)

		cmds.select(new_edge)
	cmds.undoInfo(cck=True)

def smart_bridge(*args):
	# Check edge selection
	edges = cmds.filterExpand(sm=32)
	if edges and len(edges) >= 6:
		if (cmds.selectPref(tso=True, q=True)==0):
			cmds.selectPref(tso=True)
		edges = cmds.ls(orderedSelection=True, fl=True)
		cmds.polyCloseBorder()
		mel.eval("ConvertSelectionToContainedFaces;")
		faces = cmds.ls(sl=True, fl=True, l=True)
		if edges[0] in cmds.ls(cmds.polyListComponentConversion(faces[0], ff=1, te=1), fl=1):
			first_face = faces[0]
			second_face = faces[-1]
		else:
			first_face = faces[-1]
			second_face = faces[0]
		cmds.select(first_face)
		cmds.select(second_face, add=True)
	# Check Face selection
	if (cmds.selectPref(tso=True, q=True)==0):
		cmds.selectPref(tso=True)
	faces = cmds.ls(orderedSelection=True, fl=True)
	if faces and len(faces) == 2:
		# Get Selected Object
		selected_obj = faces[0].rsplit(".", 1)[0]

		# Get selected vertices
		start_vertices = cmds.ls(cmds.polyListComponentConversion(faces[0], ff=1, tv=1), fl=1)
		end_vertices = cmds.ls(cmds.polyListComponentConversion(faces[-1], ff=1, tv=1), fl=1)
		# Get face vector
		start_face_normal = get_face_normal(faces[0])
		start_vector = OpenMaya.MVector(start_face_normal[0], start_face_normal[1], start_face_normal[2])
		end_face_normal = get_face_normal(faces[-1])
		end_vector = OpenMaya.MVector(end_face_normal[0], end_face_normal[1], end_face_normal[2])
		# Get center position
		start_center_pos = get_center_position(start_vertices)
		end_center_pos = get_center_position(end_vertices)
		# Get mid point
		mid_start_center_pos = start_center_pos + start_vector
		mid_end_center_pos = end_center_pos + end_vector
		# Line Intersect
		mid_point = line_line_intersect(start_center_pos, mid_start_center_pos, end_center_pos, mid_end_center_pos)
		
		first_distance = get_distance(start_center_pos, mid_point)
		second_distance = get_distance(end_center_pos, mid_point)
		
		# if first_distance >= second_distance:
		change_distance = first_distance - second_distance
		for v in start_vertices:
			current_pos = cmds.pointPosition(v)
			new_x = change_distance * start_vector[0] / math.sqrt(start_vector[0] * start_vector[0] + start_vector[1] * start_vector[1] + start_vector[2] * start_vector[2])
			new_y = change_distance * start_vector[1] / math.sqrt(start_vector[0] * start_vector[0] + start_vector[1] * start_vector[1] + start_vector[2] * start_vector[2])
			new_z = change_distance * start_vector[2] / math.sqrt(start_vector[0] * start_vector[0] + start_vector[1] * start_vector[1] + start_vector[2] * start_vector[2])
			cmds.polyMoveVertex(v, ws=True, t=(new_x, new_y, new_z))
		cmds.select(faces)
		mel.eval('DeleteHistory;')
		mel.eval('BridgeEdge;')
		mel.eval('setAttr \"polyBridgeEdge1.divisions\" 4;')
		mel.eval('setAttr \"polyBridgeEdge1.curveType\" 1;')
	else:
		cmds.confirmDialog(title='Confirm', m='Select 2 RING EDGES or 2 FACES!')

def clear_support_edge(*args):
	cmds.undoInfo(ock=True)
	clean_angle = cmds.floatField('clear_support_edge_angle_ff', q=True, v=True)

	selected = cmds.ls(sl=True,fl=True)
	cmds.polySoftEdge(selected, ch=True, angle=clean_angle)
	mel.eval("ConvertSelectionToEdges;")

	cmds.polySelectConstraint(type=0x8000, m=3, sm=2)
	selectEdges = cmds.ls(sl=True)
	mel.eval("resetPolySelectConstraint;")	
	cmds.select(selectEdges)
	if len(selectEdges) > 0:
		cmds.polyDelEdge(selectEdges, cv=True)
	else:
		mel.eval("DeleteHistory;")
		return False

	# Clear wrong edge
	#????

	# Clear wrong vertex
	cmds.select(selected)
	mel.eval('ConvertSelectionToVertices;')
	mel.eval("doDelete;")
	mel.eval("changeSelectMode -object;")
	mel.eval("polyPerformAction \"polySoftEdge -a 45\" e 0;")
	cmds.select(selected)

	cmds.polySoftEdge(selected, ch=True, angle=30)
	# Clear history
	mel.eval("DeleteHistory;")
	# Reselect Object
	cmds.select(selected)
	cmds.undoInfo(cck=True)

def open_create_decal_tool(parent_window):
	if cmds.window('create_decal_window', ex = True):
		cmds.deleteUI('create_decal_window', window = True)
	cmds.window('create_decal_window', title = 'Create Decal Tool', p=parent_window, rtf = True, mnb = False, mxb = False, h=40)
	
	cmds.rowColumnLayout(nc = 3, cw = [(1,80), (2,100), (3,80)], adj = 4, cs = [(2,5), (3,5), (4,5)])
	
	cmds.rowColumnLayout(nr = 4, rh = [(1,20), (2,20), (3,20), (4,20)], adj = 4, cs = [(2,5), (3,5), (4,5)])
	cmds.text(l = 'Fraction:')
	cmds.text(l = 'Spacing:')
	cmds.text(l = 'Segment:')
	cmds.text(l = 'Chamfer:')
	cmds.setParent('..')
	
	cmds.rowColumnLayout(nr = 4, rh = [(1,20), (2,20), (3,20), (4,20)], adj = 4, cs = [(2,5), (3,5), (4,5)])
	cmds.floatField('decal_fraction_ff', pre=3, v=0.1)
	cmds.floatField('decal_spacing_ff', pre=3, v=0)
	cmds.intField('decal_segment_if', v=1)
	cmds.checkBox('decal_chamfer_cb', l='', v=True)
	cmds.setParent('..')

	cmds.button('create_decal_btn', l = 'Create Decal', bgc = (0.2, 0.8, 0.5), c=run_create_decal)
	cmds.setParent('..')
	
	cmds.showWindow('create_decal_window')

def open_snap_tool(parent_window):
	slide_snap.open_tool(parent_window)

def open_unbevel_tool(parent_window):
	if cmds.window('unbevel_tool_window', ex = True):
		cmds.deleteUI('unbevel_tool_window', window = True)
	cmds.window('unbevel_tool_window', title = 'Unbevel Tool', p=parent_window, rtf = True, mnb = False, mxb = False)

	cmds.rowColumnLayout('unbevel_tool_layout', nr = 2, rh = [(1, 35), (2, 35)], adj = 2, cs = [(2,15)])
	
	cmds.rowColumnLayout(nc=2, cw=[(1, 155), (2,155)], adj=2, cs=[(2,5)])
	cmds.button(l = 'Unbevel (Bevel Edge)', h=30, bgc = (0.2, 0.8, 0.5), c=unbevel)
	cmds.button(l = 'Unbevel (All Edge)', h=30, bgc = (0.2, 0.8, 0.5), c=unbevel_v2)
	cmds.setParent('..')

	cmds.rowColumnLayout(nc=3, cw=[(1, 90), (2, 100), (3, 100)], adj=3, cs=[(2,5), (3,5)])
	cmds.floatField('unbevel_value_ff', v=0.1, min=0.01, max=1.0)
	cmds.button(l = 'Bevel +', h=30, c=lambda *args: bevel_modifier(2))
	cmds.button(l = 'Bevel -', h=30, c=lambda *args: bevel_modifier(1))
	cmds.setParent('..')

	cmds.setParent('..')

	cmds.showWindow('unbevel_tool_window')	

def open_inflate_tool(parent_window):
	if cmds.window('inflate_tool_window', ex = True):
		cmds.deleteUI('inflate_tool_window', window = True)
	cmds.window('inflate_tool_window', title = 'Inflate Tool', p=parent_window, rtf = True, mnb = False, mxb = False)

	cmds.rowColumnLayout(nc=4, cw=[(1, 60), (2, 100), (3, 70), (4, 70)], adj=4, cs=[(2,5), (3,5), (4,5)])
	cmds.text(l='Value: ')
	cmds.floatField('inflate_value_ff', v=0.1)
	cmds.button(l = 'Inflate +', h=35, bgc = (0.2, 0.8, 0.5), c=lambda *args: run_inflate(1))
	cmds.button(l = 'Inflate -', h=35, bgc = (0.8, 0.5, 0), c=lambda *args: run_inflate(-1))
	cmds.setParent('..')

	cmds.showWindow('inflate_tool_window')

def open_edge_length_tool(parent_window):
	if cmds.window('edge_length_tool_window', ex = True):
		cmds.deleteUI('edge_length_tool_window', window = True)
	cmds.window('edge_length_tool_window', title = 'Edge Length Tool', p=parent_window, rtf = True, mnb = False, mxb = False)

	cmds.rowColumnLayout('edge_length_tool_layout', nr = 9, rh = [(1,30), (2,30), (3,30), (4,80), (5,30), (6,50), (7,10), (8,30), (9,30)], adj = 9)

	cmds.text(l='Edge Length (Multiple Selection: Average)', al='center')
	cmds.rowColumnLayout(nc = 2, cw = [(1, 100), (2,190)], adj = 2, cs = [(2,5)])
	cmds.button(l = 'Get Length', c=get_edge_length)
	cmds.floatField('length_ff', v=0.0)
	cmds.setParent('..')
	cmds.text(l='Lock vertex list', al='center')
	cmds.rowColumnLayout(nc = 2, cw = [(1, 100), (2,190)], adj = 2, cs = [(2,5)])
	cmds.columnLayout(columnAttach=('both', 1))
	cmds.button(l = 'Add Vertex', c=add_lock_vertex)
	cmds.button(l = 'Clear List', c=clear_list)
	cmds.setParent('..')
	cmds.textScrollList('lock_vertex_list', numberOfRows=6, allowMultiSelection=True)
	cmds.textScrollList('lock_vertex_list', edit=True, deleteKeyCommand=remove_item_in_list, selectCommand=select_item_in_list)
	cmds.setParent('..')
	cmds.rowColumnLayout(nc = 1, cw = [(1, 295)], adj = 1, cs = [(1,5)])
	cmds.checkBox('check_preserve_UV_cb', l='Preserve UVs')
	cmds.setParent('..')
	cmds.rowColumnLayout(nc = 1, cw = [(1, 295)], adj = 1)
	cmds.button(l = 'Set Length', h=50, bgc = (0.2, 0.8, 0.5), c=set_edge_length)
	cmds.setParent('..')
	cmds.separator(st='in')
	cmds.text(l='Select 2 Outside Edges / 2 Loop Edges', al='center')
	cmds.button(l = 'Set Edge Length Flow', bgc = (0.2, 0.8, 0.5), c=set_edge_length_ascending_descending)
	cmds.setParent('..')

	cmds.showWindow('edge_length_tool_window')

def open_create_cylinder_tool(parent_window):
	if cmds.window('create_cylinder_window', ex = True):
		cmds.deleteUI('create_cylinder_window', window = True)
	main_window = cmds.window('create_cylinder_window', title='Create Cylinder Tool', p=parent_window, rtf = True, mnb = False, mxb = False)
	cmds.rowColumnLayout("create_cylinder_layout", p = main_window)
	cmds.rowColumnLayout(nc=2, cw=[(1,80), (2,120)], adj=2, cs = [(1,5)])
	cmds.text(l='Diameter (cm):', h=30)
	cmds.floatField('cylinder_diameter_ff', h=30, precision=2, v=100.0, cc=change_cylinder_segment_value_ui)
	cmds.setParent('..')
	cmds.rowColumnLayout(nc=2, cw=[(1,80), (2,120)], adj=2, cs = [(1,5)])
	cmds.text(l='Segment:', h=30)
	cmds.intField('cylinder_segment_if', h=30, en=False, v=60)
	cmds.setParent('..')
	cmds.rowColumnLayout(nc=1, cw=[(1,200)], adj=1)
	cmds.button("auto_create_cylinder_button", l = "Create Cylinder", h=60, bgc = (0.2, 0.8, 0.5), c = create_cylinder)
	cmds.setParent('..')
	cmds.setParent('..')

	cmds.showWindow(main_window)

def open_screenshot_tool(parent_window):
	default_screenshot_path = cmds.file(q= True, sn= True).replace("\\", "/").rsplit("/", 1)[0]

	if cmds.window('screenshot_tool_window', ex = True):
		cmds.deleteUI('screenshot_tool_window', window = True)
	main_window = cmds.window('screenshot_tool_window', title='Screenshot Tool', p=parent_window, rtf = True, mnb = False, mxb = False)
	cmds.rowColumnLayout("screenshot_tool_layout", p = main_window)

	cmds.rowColumnLayout(nc=3, cw=[(1,60), (2,200), (3,40)], adj=3, cs = [(1,5), (2,5), (3,5)])
	cmds.text(l='Export Path:', h=30)
	cmds.textField('screenshot_path_tf', h=30, tx=default_screenshot_path)
	cmds.button("get_screenshot_path_button", l = "...", h=30, c=get_screenshot_path)
	cmds.setParent('..')
	cmds.separator(height=10, style='singleDash')
	cmds.rowColumnLayout(nc=3, cw=[(1,60), (2,60), (3,200)], adj=3, cs = [(1,5), (2,5), (3,5)])
	cmds.text(l='Zoom (%):', h=30)
	cmds.intField('camera_zoom_value_if', h=30, v=100)
	cmds.setParent('..')
	cmds.separator(height=10, style='singleDash')
	cmds.rowColumnLayout(nc=2, cw=[(1,150), (2,150)], adj=2, cs = [(1,5), (2,5)])
	cmds.button("auto_capture_button", l = "Auto Capture", h=60, bgc = (0.6, 0.6, 1), c=partial(screenshot_function, "auto"))
	cmds.button("custom_capture_button", l = "Custom Capture", h=60, bgc = (0.8, 0.8, 0.8), c=partial(screenshot_function, "custom"))
	cmds.setParent('..')
	cmds.setParent('..')

	cmds.showWindow(main_window)

def open_rename_tool(parent_window):
	naming_tool.show_window(parent_window)

def open_straighten_line_tool(parent_window):
	straight_line_tool.show_window(parent_window)

def open_average_line_tool(parent_window):
	if cmds.window('average_line_tool_window', ex = True):
		cmds.deleteUI('average_line_tool_window', window = True)
	cmds.window('average_line_tool_window', title = 'Average Line Tool', p=parent_window, rtf = True, mnb = False, mxb = False)
	
	cmds.rowColumnLayout('average_line_tool_layout', nr = 4, rh = [(1,30), (2,30), (3,30), (4,30)], adj = 4, cs = [(2,5), (3,5), (4,5)])

	cmds.rowColumnLayout(nc=3, cw=[(1, 80), (2, 120), (3, 80)], adj = 3, cs = [(1,5), (2,5), (3,5)])
	cmds.checkBox('averageLine_even_cb', l=' Even', al='left', v=cmds.optionVar(q='averageLine_even'), cc="cmds.optionVar(iv=['averageLine_even',cmds.checkBox(\'averageLine_even_cb\', q=True, v=True)]);cmds.intSliderGrp(\'averageLine_step_sl\', e=True, en=not cmds.optionVar(q='averageLine_even'))")
	cmds.checkBox('averageLine_keepshape_cb', l=' Keep Shape', al='left', v=cmds.optionVar(q='averageLine_keepshape'), cc="cmds.optionVar(iv=['averageLine_keepshape',cmds.checkBox(\'averageLine_keepshape_cb\', q=True, v=True)])")
	cmds.checkBox('averageLine_smooth_cb', l=' Smooth', al='left', v=cmds.optionVar(q='averageLine_smooth'), cc="cmds.optionVar(iv=['averageLine_smooth',cmds.checkBox(\'averageLine_smooth_cb\', q=True, v=True)])")
	cmds.setParent('..')
	cmds.rowColumnLayout(nc=1, cw=[(1, 290)], adj = 1, cs = [(1,5)])
	cmds.radioButtonGrp('averageLine_align_rbg', l=' Align:', nrb=4, la4=['YZ','XZ','XY','Auto'], cw5=[55,55,55,55,55], cl5=['left'] * 5, sl=cmds.optionVar(q='averageLine_align'), cc="cmds.optionVar(iv=['averageLine_align', cmds.radioButtonGrp(\'averageLine_align_rbg\',q=True,sl=True)])")
	cmds.setParent('..')
	cmds.rowColumnLayout(nc=1, cw=[(1, 290)], adj = 1, cs = [(1,5)])
	cmds.intSliderGrp('averageLine_step_sl', l=' Step:', f=True, min=1, max=10, cw=[(1, 55), (2, 40), (3,180)], cal=[(1, 'left')], rat=[1, 'top', 3], en=not cmds.optionVar(q='averageLine_even'), v=cmds.optionVar(q='averageLine_step'), cc="cmds.optionVar(iv=['averageLine_step',cmds.intSliderGrp(\'averageLine_step_sl\',q=True,v=True)])")
	cmds.setParent('..')
	cmds.rowColumnLayout(nc = 1, cw = [(1, 290)], adj = 1)
	cmds.button(l = 'Average Line', h=30, bgc = (0.2, 0.8, 0.5), c = average_line)
	cmds.setParent('..')
	
	cmds.setParent('..')

	cmds.showWindow('average_line_tool_window')

def open_shrinkwrap_tool(parent_window):
	if cmds.window('shrinkwrap_tool_window', ex = True):
		cmds.deleteUI('shrinkwrap_tool_window', window = True)
	cmds.window('shrinkwrap_tool_window', title = 'ShrinkWrap Tool', p=parent_window, rtf = True, mnb = False, mxb = False)
	
	cmds.rowColumnLayout('shrinkwrap_tool_layout', nr = 3, rh = [(1,30), (2,30), (3,30)], adj = 3, cs = [(2,5), (3,5)])

	cmds.textFieldButtonGrp('shrinkwrap_tfbg',tx='Target:', eb=True, bl='    Add    ', ed=False, cw=[(1,240)], bc=add_wrap_target)
	cmds.rowColumnLayout(nc=2, cw=[(1, 200), (2, 80)], cat=[2, 'left', 5])
	cmds.radioButtonGrp('shrinkwrap_rbg', nrb=2, l=' Mode:', la2=['Vertex', 'Face'], sl=1, cw3=[45, 60, 45], cal=[1, 'left'], on1='cmds.checkBox(\'shrinkwrap_border_cb\',e=True,en=False)', on2='cmds.checkBox(\'shrinkwrap_border_cb\',e=True,en=True)')
	cmds.checkBox('shrinkwrap_border_cb', l='Border', v=True, en=False)
	cmds.setParent('..')
	cmds.button('shrinkwrap_btn', l='ShrinkWrap', h=30, bgc = (0.2, 0.8, 0.5), en=False, c=shrinkwrap)
	cmds.setParent('..')
	
	cmds.setParent('..')

	cmds.showWindow('shrinkwrap_tool_window')

def open_curve_deform_tool(parent_window):
	if cmds.window('curve_deform_tool_window', ex = True):
		cmds.deleteUI('curve_deform_tool_window', window = True)
	cmds.window('curve_deform_tool_window', title = 'Curve Deform Tool', p=parent_window, rtf = True, mnb = False, mxb = False)
	
	cmds.rowColumnLayout('curve_deform_tool_layout', nr = 5, rh = [(1,30), (2,30), (3,30), (4,30), (5,30)], adj = 5, cs = [(2,5), (3,5), (4,5), (5,5)])

	cmds.rowColumnLayout(nc=3, cw=[(1,60),(2,220)], co=[(1, 'right', 0)], adj=2, cs=[(1,5), (2,5)])
	cmds.text(l ='Curve Type')
	cmds.radioButtonGrp('curveType_rbg', nrb=2, sl=1, labelArray2=['Bezier', 'Nurbs'], cw = [(1,100),(2,100)], cc= controlNumberSwitch)
	cmds.setParent( '..' )
	cmds.rowColumnLayout(nc=5, cw=[(1,60), (2,45), (3,45), (4,45), (5,45)], co=[(1, 'right', 0)], adj=5, cs=[(1,5), (2,5), (3,5), (4,5), (5,5)])
	cmds.text(l ='Options')
	cmds.checkBox('makeArc', label= "Arc" ,v = 1, cc = makeArcSwitch)
	cmds.checkBox('snapCurve', label= "Snap" ,v = 1, cc = disableEvenSpaceCheckBox)
	cmds.checkBox('evenSpace', label= "Even" ,v = 1)
	cmds.checkBox('cleanCurve', label= "Keep Curve" ,v = 1)
	cmds.setParent( '..' )
	cmds.rowColumnLayout(nc=1, cw=[(1,300)], adj=1, cs=[(1,5)])
	cmds.intSliderGrp('CPSlider', cw3=[60, 30, 200], label = 'Point',  field= 1, min= 2, max= 10, fmx = 500, v = 3)
	cmds.setParent( '..' )
	cmds.rowColumnLayout(nc=1, cw=[(1,300)], adj=1, cs=[(1,5)])
	cmds.floatSliderGrp('dropOffSlider' , label = 'DropOff', v = 0.01, cw3=[60, 30, 200], field=1 ,pre = 2, min= 0.01, max= 10)
	cmds.setParent( '..' )
	cmds.rowColumnLayout(nc=2 ,cw=[(1,160),(2,140)], adj=2, cs=[(2,5)])
	cmds.button( l= 'Run', h=30, bgc = (0.2, 0.8, 0.5),  c= arcEdgeLoop)
	cmds.button( l= 'Done', h=30,  c= arcDone)
	cmds.setParent( '..' )

	cmds.setParent('..')

	cmds.showWindow('curve_deform_tool_window')

def open_cable_tool(parent_window):
	if cmds.window('cable_tool_window', ex = True):
		cmds.deleteUI('cable_tool_window', window = True)
	cmds.window('cable_tool_window', title = 'Cable Tool', p=parent_window, rtf = True, mnb = False, mxb = False)
	
	cmds.rowColumnLayout('cable_tool_layout', nr = 6, rh = [(1,30), (2,35), (3,5), (4,35), (5,5), (6,35)], adj = 6, cs = [(2,5), (3,5), (4,5), (5,5), (6,5)])

	cmds.text('Please Select 2 Vertex Or 2 Face To Create Cable!')
	cmds.rowColumnLayout(nc = 3, cw = [(1, 90), (2,110), (3,90)], adj = 3, cs = [(2, 5), (3, 5)])
	cmds.text('Curve Offset:')
	cmds.floatField('create_cable_offset_ff', v=1.0)
	cmds.button(l='Create Curve', h=30, bgc = (0.2, 0.8, 0.5), c=create_curve)
	cmds.setParent('..')
	cmds.separator(st='in')
	cmds.button(l='Edge To Curve', h=30, bgc = (0.2, 0.8, 0.5), c=edges_to_curve)
	cmds.separator(st='in')
	cmds.setParent('..')

	cmds.setParent('..')

	cmds.showWindow('cable_tool_window')

def open_clear_support_edge_tool(parent_window):
	if cmds.window('clear_support_edge_tool_window', ex = True):
		cmds.deleteUI('clear_support_edge_tool_window', window = True)
	cmds.window('clear_support_edge_tool_window', title = 'Clear Support Edge Tool', p=parent_window, rtf = True, mnb = False, mxb = False)

	cmds.rowColumnLayout('clear_support_edge_tool_layout', nr = 1, rh = [(1, 35)], adj = 1)
	
	cmds.rowColumnLayout(nc=3, cw=[(1,100), (2,100), (3,100)], adj=2, cs=[(2,5)])
	cmds.text(l='Angle: ')
	cmds.floatField('clear_support_edge_angle_ff', v=0.3, min=0.01, max=180)
	cmds.button(l = 'Clear spEdge', h = 35, bgc = (0.2, 0.8, 0.5), c=clear_support_edge)
	cmds.setParent('..')

	cmds.setParent('..')

	cmds.showWindow('clear_support_edge_tool_window')	

def open_image_camera_tool(parent_window):
	import image_camera
	reload(image_camera)
	image_camera.GUI(parent_window)

def open_lod_tool(parent_window):
	if cmds.window("swap_lod_window", ex = True):
		cmds.deleteUI("swap_lod_window", window = True)

	main_window = cmds.window("swap_lod_window", title = "Swap LOD", p=parent_window, w = 200, h = 100)
	cmds.rowColumnLayout("main_layout", p = main_window, nr = 2, adj = 2, cs = [(1,5), (2,5)])

	cmds.rowColumnLayout(nc = 3, cw = [(1,80),(2,80)], adj = 3, cs = [(2,5), (3,5)])
	cmds.button("store_object_a_btn", h = 40, l = "Object A", c = store_object_a)
	cmds.button("store_object_b_btn", h = 40, l = "Object B", c = store_object_b)
	cmds.button("unhide_all_btn" , h = 40, bgc = (0.6, 0.6, 1), l = "Unhide All", c = unhide_all)
	cmds.setParent("..")

	cmds.rowColumnLayout(nc = 1, cw = [(1, 240)], adj = 1)
	cmds.button("swap_lod_btn" , l = "Swap LOD", h = 50, bgc = (0.2, 0.8, 0.5), c = swap_lod_object)
	cmds.setParent("..")
	
	cmds.setParent("..")
	
	cmds.showWindow('swap_lod_window')

#region Library
# def read_data_from_json(path):
# 	json_data = {}
# 	try:
# 		with open(path, 'r') as file:
# 			json_data = json.load(file)
# 			file.close()
# 	except:
# 		pass
# 	return json_data

# def open_library_tool(parent_window, LIBRARY_PATH):
# 	# LIBRARY FILE PATH
# 	LIBRARY_JSON_PATH = LIBRARY_PATH + "/HardSurfaceTool_Library.json"
# 	LIBRARY_FBX_PATH = LIBRARY_PATH + "/FBX"
# 	LIBRARY_IMAGE_PATH = LIBRARY_PATH + "/Image"

# 	if cmds.window('hs_library_window', ex = True):
# 		cmds.deleteUI('hs_library_window', window = True)
	
# 	data = read_data_from_json(LIBRARY_JSON_PATH)
# 	managers = data['managers']
# 	object_type = data['type']
	
# 	is_enable_edit_btn = True
# 	if int(cmds.about(version=True)) >= 2023:
# 		current_user = os.path.expanduser("~").replace("\\", "/").rsplit("/", 1)[-1]
# 	else:
# 		current_user = os.path.expanduser("~").replace("\\", "/").rsplit("/", 2)[-2]
# 	if current_user not in managers:
# 		is_enable_edit_btn = False

# 	library_window = cmds.window('hs_library_window', title='HardSurface Library', p=parent_window, rtf=True, mnb=False, mxb=False)

# 	cmds.rowColumnLayout(nc=2, cw=[(1, 300), (2, 150)], adj=2, cs=[(1,5), (2,5)])
# 	#ASSET LAYOUT
# 	cmds.columnLayout(adj=True)
# 	cmds.rowLayout(nc=2, adj=2)
# 	cmds.text(l='Asset Name: ')
# 	cmds.textField('search_library_tf', h=30, cc=lambda *args: search_in_object_list(LIBRARY_FBX_PATH))
# 	cmds.setParent('..')
# 	cmds.separator(h=10, st='in')
# 	model_scroll = cmds.scrollLayout('import_field', cr = True, hst=0, vst=0, h=170)
# 	import_field_layout = cmds.columnLayout('main_field', p=model_scroll, adj=True)

# 	images_on_lib = [i for i in os.listdir(LIBRARY_IMAGE_PATH) if i.split(".")[-1] == 'png']
	
# 	cmds.gridLayout('gridImport', nrc=[math.ceil(len(images_on_lib)/4), 4], cwh=[70, 70])

# 	for i in images_on_lib:
# 		button = cmds.iconTextButton("{}".format(i.split(".")[0])
# 			, style = "iconAndTextVertical"
# 			, scaleIcon=True
# 			, image1=LIBRARY_IMAGE_PATH+"/{}".format(i)
# 			, l=i.split(".")[0]
# 			, ann = i.split(".")[0]
# 			, c = partial(load_image_through_button, LIBRARY_IMAGE_PATH, i))

# 	cmds.setParent("..")
# 	cmds.setParent("..")
# 	cmds.setParent("..")
# 	cmds.separator(h=10, st='in')

# 	cmds.columnLayout('image_layout', adj=True, rs=5, cal='center')
# 	cmds.text(l="PREVIEW IMAGE", h=30, fn="smallFixedWidthFont", bgc = [0.2, 0.8, 0.5])
# 	cmds.image('object_image', w=280, h=300, p='image_layout')
# 	cmds.setParent("..")

# 	cmds.setParent('..')

# 	#MID LAYOUT
# 	cmds.columnLayout('mid_layout', rs=9, adj=True)
# 	cmds.text(l="FUNCTIONS", fn="smallFixedWidthFont", h=29,  bgc = [0.2, 0.8, 0.5])
# 	cmds.separator(st='in')
# 	#is_enable_edit_btn
# 	cmds.button("Delete", w=70, h=35, en=is_enable_edit_btn, c=lambda *args: delete_object_from_library(LIBRARY_FBX_PATH, LIBRARY_IMAGE_PATH))
# 	cmds.button("Edit", w=70, h=35, en=is_enable_edit_btn, c=lambda *args: edit_object_from_library(LIBRARY_FBX_PATH, LIBRARY_IMAGE_PATH))
# 	cmds.button("Import", w=70, h=35, c=lambda *args: import_object_from_library(LIBRARY_FBX_PATH))
# 	cmds.button("Export", w=70, h=35, c=lambda *args: export_object_to_library(LIBRARY_FBX_PATH, LIBRARY_IMAGE_PATH))
# 	cmds.checkBox('customExport', l='Custom Export', value=True)

# 	#Decal Frame
# 	cmds.separator(st='in')
# 	cmds.text(l="DECAL", fn="smallFixedWidthFont", h=30, bgc = [0.6, 0.6, 1])
# 	cmds.separator(st='in')
# 	cmds.rowLayout(nc=3, adj=2)
# 	cmds.text(l='Target: ')
# 	cmds.textField('targetObject')
# 	cmds.button(l='Pick', c=fnPickTarget)
# 	cmds.setParent("..")
# 	cmds.checkBox('decal', l='Decal Mode', value=True)
# 	cmds.button(l='Pick Decal', w=70, h=35, c=fnPickDecal)
# 	cmds.button(l='Assign', w=70, h=35, c=fnAssignDecal)
# 	cmds.separator(st='in')
# 	cmds.button('GlassEggLibs', l="GlassEgg Library", h=80, bgc=[0.1, 0.2, 0.4], command=GELibCall)
	
# 	#END Decal Frame

# 	cmds.setParent('..')
# 	##END MID_LAYOUT
# 	cmds.showWindow(library_window)

# def fnPickTarget(*args):
# 	obj = cmds.ls(sl=True, l=True)[0]
# 	targetObj = cmds.textField('targetObject', e=True, tx=str(obj))
# 	#-------Continue-------
	
# 	decal_mode = cmds.checkBox('decal', q=True, v=True)
	

# def fnPickDecal(*args):
# 	pivot = [0, 0, 0]
# 	decal_mode = cmds.checkBox('decal', q=True, v=True)
# 	decal_obj = cmds.ls(sl=True, l=True, objectsOnly=True)[0]
# 	target_obj = cmds.textField('targetObject', q=True, tx=True).split("|")[-1]
# 	avg_vtx = len(cmds.ls(cmds.polyListComponentConversion(target_obj, tv=True), fl=True))/2
# 	target_vtx_pos = cmds.xform(target_obj+".vtx[{}]".format(avg_vtx), q=True, t=True, ws=True)
# 	if decal_obj:
# 		decal_obj_pivot = cmds.xform(decal_obj, q=True, ws=True, rp=True)
# 		decal_obj_zMin = cmds.xform(decal_obj, q=True, bb=True)[2]
# 		pivot = [0, 0, 0+decal_obj_zMin]
# 		cmds.move(pivot[0], pivot[1], pivot[2], decal_obj + ".scalePivot", decal_obj + ".rotatePivot", a=True)
# 		if decal_mode == True:
# 			normal_constraint = cmds.normalConstraint(cmds.textField('targetObject', q=True, tx=True), decal_obj, aimVector = (0,0,1), upVector=[1.0, 0.0, 0.0], worldUpType='objectrotation', weight=20.0)
# 			cmds.move(target_vtx_pos[0], target_vtx_pos[1], target_vtx_pos[2]+(-1)*decal_obj_zMin, decal_obj)

# def fnAssignDecal(*args):
# 	normal_cons = cmds.ls(type='normalConstraint')
# 	cmds.delete(normal_cons)
# 	mel.eval('FreezeTransformations')
# 	mel.eval('DeleteAllHistory')

# def load_image_through_button(LIBRARY_IMAGE_PATH, index):
# 	cmds.image('object_image', e=True, image=LIBRARY_IMAGE_PATH + "/" +index)
# 	cmds.textField('search_library_tf', e=True, tx=str(index.split(".")[0]))

# def GELibCall(*args):
# 	import sys
# 	sys.path.append(r'//virtuosgames/geh/TOOLS/TECHNICAL_DEPLOYMENT/ReleaseLine/GE_ToolSet/plugin/_Default/maya')
# 	import library_tool.app.bin.maya_run as maya_run
# 	try:
# 		from importlib import reload
# 		reload(maya_run)
# 		maya_run.main()
# 	except:
# 		maya_run.main()

# def reload_library_scroll_list(LIBRARY_FBX_PATH):
# 	try:
# 		cmds.textScrollList('object_list_library_tscl', e = True, ra = True)
# 	except:
# 		pass
# 	fbx_list = [f.rsplit(".", 1)[0] for f in os.listdir(LIBRARY_FBX_PATH) if os.path.isfile(os.path.join(LIBRARY_FBX_PATH, f)) and f.rsplit(".", 1)[-1].lower() == "fbx"]
# 	cmds.textScrollList('object_list_library_tscl', e = True, a = fbx_list)

# def search_in_object_list(LIBRARY_FBX_PATH):
# 	current_fbx_list = []
# 	current_search_text = cmds.textField('search_library_tf', q=True, tx=True).lower()
# 	for f in os.listdir(LIBRARY_FBX_PATH):
# 		if os.path.isfile(os.path.join(LIBRARY_FBX_PATH, f)) and f.rsplit(".", 1)[-1].lower() == "fbx" and current_search_text in f.rsplit(".", 1)[0].lower():
# 			current_fbx_list.append(f.rsplit(".", 1)[0])
# 	cmds.textScrollList('object_list_library_tscl', e = True, ra = True)
# 	cmds.textScrollList('object_list_library_tscl', e = True, a = current_fbx_list)

# def show_object_image_library(LIBRARY_IMAGE_PATH):
# 	selected_object = cmds.textScrollList('object_list_library_tscl', q = True, si=True)[0]
# 	cmds.image('object_image', e=True, image=LIBRARY_IMAGE_PATH + "/" + selected_object + ".png")

# def create_new_persp_camera(camera_name, camera_setting):
# 	# Create camera
# 	new_camera =  cmds.camera(name = camera_name)

# 	# Select camera
# 	cmds.select(new_camera, r=True)
# 	selected_camera = cmds.ls(sl=True)[0]

# 	# Set attribute camera
# 	cmds.setAttr(selected_camera + ".rotateX", camera_setting[0])
# 	cmds.setAttr(selected_camera + ".rotateY", camera_setting[1])
# 	cmds.setAttr(selected_camera + ".rotateZ", camera_setting[2])

# 	return selected_camera

# def change_scene_settings(mode):
# 	customVal = cmds.checkBox('customExport', q=True, v=True)
# 	if customVal == True:
# 		current_view = cmds.getPanel(withFocus=True)
# 	else:
# 		current_view = 'modelPanel4'

# 	if mode == "reset":
# 		cmds.modelEditor(current_view, edit=True, grid=True)
# 		mel.eval('setCameraNamesVisibility(1);')
# 		mel.eval('setPolyCountVisibility(1);')
# 		mel.eval('setViewAxisVisibility(1);')
# 	elif mode == "change":
# 		cmds.modelEditor(current_view, edit=True, grid=False)
# 		mel.eval('setCameraNamesVisibility(0);')
# 		mel.eval('setPolyCountVisibility(0);')
# 		mel.eval('setViewAxisVisibility(0);')
# 		mel.eval('setViewportRendererVisibility(0);')

# def modify_focus_camera(camera_name): #While using camera in Export function
# 	camera_center = cmds.objectCenter(camera_name, gl=True)
# 	x_vector = camera_center[0]
# 	y_vector = camera_center[1]
# 	z_vector = camera_center[2]

# 	camera_distance_threshold = 80 / 100

# 	current_distance = math.sqrt(x_vector**2 + y_vector**2 + z_vector**2)
# 	new_distance = current_distance * camera_distance_threshold

# 	#current_vector = [x_vector, y_vector, z_vector]
# 	new_x = camera_center[0] + x_vector * camera_distance_threshold
# 	new_y = camera_center[1] + y_vector * camera_distance_threshold
# 	new_z = camera_center[2] + z_vector * camera_distance_threshold

# 	# Set attribute camera
# 	cmds.setAttr(camera_name + ".translateX", new_x)
# 	cmds.setAttr(camera_name + ".translateY", new_y)
# 	cmds.setAttr(camera_name + ".translateZ", new_z) 

# def screenshot_object(screenshot_path, screenshot_name, current_object):
# 	# Get file path
# 	customVal = cmds.checkBox('customExport', q=True, v=True)
# 	curPanel = cmds.getPanel(withFocus=True)
# 	file_path = screenshot_path + "/" + screenshot_name + ".png"
	
# 	# # Get persp camera
# 	persp_cam = [cam for cam in cmds.listRelatives(cmds.ls(ca=True), p=True) if 'persp' in cam]
# 	# # Set viewport
# 	if customVal == False:
# 		#Create camera
# 		current_camera = create_new_persp_camera("new_persp", [-45, 135,0])
# 		cmds.lookThru(current_camera)
# 		cmds.select(current_object)
# 		for obj in cmds.ls(type="transform"):
# 			cmds.hide(obj)
# 		change_scene_settings("change")
# 		cmds.showHidden(current_object, above=True)
# 		cmds.select(d=True)
# 		cmds.viewFit()

# 		cmds.setAttr("defaultRenderGlobals.imageFormat", 32)
# 		cmds.playblast(completeFilename = file_path, 
# 						startTime=1,
# 						endTime=1,
# 						v=0,
# 						format="image",
# 						quality=100,
# 						percent=100,
# 						w=300,
# 						h=300,
# 						framePadding=0)

# 		# Reset viewport
# 		change_scene_settings("reset")
# 		cmds.lookThru('persp')
# 		cmds.showHidden(all=True)
# 		cmds.delete(current_camera)
# 	else:
# 		for obj in cmds.ls(type="transform"):
# 			cmds.hide(obj)
# 		change_scene_settings("change")
# 		cmds.showHidden(current_object, above=True)
# 		cmds.select(d=True)
# 		cmds.viewFit()
# 		modify_focus_camera(persp_cam[0])
# 		mel.eval('modelEditor -e -grid false {};'.format(curPanel))
# 		# Create image 
# 		cmds.setAttr("defaultRenderGlobals.imageFormat", 32)
# 		cmds.playblast(completeFilename = file_path, 
# 						startTime=1,
# 						endTime=1,
# 						v=0,
# 						format="image",
# 						quality=100,
# 						percent=100,
# 						w=300,
# 						h=300,
# 						framePadding=0)

# 		# Reset viewport
# 		change_scene_settings("reset")
# 		cmds.showHidden(all=True)

# 		mel.eval('modelEditor -e -grid true {};'.format(curPanel))
# 		# Delete screenshot camera
# 		# cmds.delete(current_camera)

# def reset_selected_object(selected_object):
# 	# Reset Material
# 	try:
# 		mel.eval('sets -e -forceElement initialShadingGroup;')
# 	except:
# 		pass

# 	# Move object to 0,0,0
# 	pivs = cmds.xform(selected_object, q=True, piv=True)[:3]  # Get pivot offset values.
# 	for i in range(len(pivs)):
# 		pivs[i] *= -1
# 	cmds.xform(selected_object, ws=True, t=pivs)

# 	# Clean object
# 	mel.eval('CenterPivot')
# 	mel.eval('FreezeTransformations')
# 	mel.eval('DeleteAllHistory')
# 	mel.eval('BakeAllNonDefHistory')

# def export_object_fbx(folder_path, file_name):
# 	mel.eval('FBXProperty Export|IncludeGrp|Geometry|SmoothingGroups -v false')
# 	mel.eval('FBXProperty Export|IncludeGrp|Geometry|expHardEdges -v false')
# 	mel.eval('FBXProperty Export|IncludeGrp|Geometry|TangentsandBinormals -v true')
# 	mel.eval('FBXProperty Export|IncludeGrp|Geometry|SmoothMesh -v false')
# 	mel.eval('FBXProperty Export|IncludeGrp|Geometry|SelectionSet -v false')
# 	mel.eval('FBXProperty Export|IncludeGrp|Geometry|Instances -v false')
# 	mel.eval('FBXExportReferencedAssetsContent -v false')
# 	mel.eval('FBXExportTriangulate -v false')
# 	mel.eval('FBXExport -f "' + folder_path + '/' + file_name + '.fbx' + '" -s')		

# def import_object_from_library(LIBRARY_FBX_PATH):
# 	# selected_objects = cmds.textScrollList('object_list_library_tscl', q = True, si=True)
# 	selected_objects = cmds.textField('search_library_tf', q=True, tx=True)
# 	face_info = []
# 	selected_face = cmds.ls(sl=True, fl=True)
# 	#Import fbx
# 	if len(selected_objects) == 0:
# 		cmds.confirmDialog(icn="information", m = "Please select object in library to IMPORT!")
# 		return False	

# 	file_path = LIBRARY_FBX_PATH + "/" + selected_objects + ".fbx"
# 	if len(selected_face) == 0:
# 		fbx = cmds.file(file_path, i=True, type='Fbx', ignoreVersion=True)
# 	elif len(selected_face) == 1:
# 		fbx = cmds.file(file_path, i=True, type='Fbx', ignoreVersion=True)
# 		imported_mesh = fbx.split(".")[0].split("/")[-1]

# 		#Get center face position
# 		face_info = cmds.xform(selected_face, q=True, t=True)
# 		constr = cmds.normalConstraint(selected_face, imported_mesh, aimVector = (0,0,1), worldUpType=0)
		
# 		x = face_info[0] + face_info[3] + face_info[6] + face_info[9]
# 		y = face_info[1] + face_info[4] + face_info[7] + face_info[10]
# 		z = face_info[2] + face_info[5] + face_info[8] + face_info[11]
			
# 		cmds.move(x/4, y/4, z/4, imported_mesh)
# 		cmds.delete(constr)
# 		# cmds.select(cmds.listRelatives(cmds.ls(g=True, type='mesh'), p=True))

# 		# mel.eval('PolygonBooleanUnion;')
# 		# mel.eval('DeleteHistory;')

# 	elif len(selected_face) > 1:
# 		for s in range(0, len(selected_face)):
# 			fbx = cmds.file(file_path, i=True, type='Fbx', ignoreVersion=True)
# 			imported_mesh = fbx.split(".")[0].split("/")[-1]
# 			new_name = cmds.rename(imported_mesh, imported_mesh + "_" + str(s))
# 			face_info = cmds.xform(selected_face[s], q=True, t=True)
# 			constr = cmds.normalConstraint(selected_face[s], new_name, aimVector = (0,0,1), worldUpType= 0)
# 			x = face_info[0] + face_info[3] + face_info[6] + face_info[9]
# 			y = face_info[1] + face_info[4] + face_info[7] + face_info[10]
# 			z = face_info[2] + face_info[5] + face_info[8] + face_info[11]
# 			cmds.move(x/4, y/4, z/4, new_name)
# 			cmds.delete(constr)
	
# def export_object_to_library(LIBRARY_FBX_PATH, LIBRARY_IMAGE_PATH):
# 	selected_objects = cmds.ls(sl=True, l=True)
# 	mel.eval('DeleteHistory;')
# 	boundingBox = cmds.xform(selected_objects[0], q=True, bb=True, ws=True)
# 	cmds.move(0,0, float(boundingBox[2] + 0.1), selected_objects[0] + '.scalePivot', selected_objects[0] + '.rotatePivot', absolute=True)
# 	if len(selected_objects) == 0:
# 		cmds.confirmDialog(icn="information", m = "Please select 1 object in scene to EXPORT!")
# 		return False		
	
# 	fbx_list = [f.rsplit(".", 1)[0] for f in os.listdir(LIBRARY_FBX_PATH) if os.path.isfile(os.path.join(LIBRARY_FBX_PATH, f)) and f.rsplit(".", 1)[-1].lower() == "fbx"]
# 	image_list = [f.rsplit(".", 1)[0] for f in os.listdir(LIBRARY_IMAGE_PATH) if os.path.isfile(os.path.join(LIBRARY_IMAGE_PATH, f)) and f.rsplit(".", 1)[-1].lower() == "png"]

# 	# Get file name
# 	file_name = selected_objects[0].split("|")[-1] + "_1"
# 	i = 1
# 	while file_name in image_list:
# 		i+=1
# 		file_name = file_name.rsplit("_", 1)[0] + "_" + str(i)

# 	# Duplicate Object To Export
# 	cmds.duplicate(selected_objects[0])
# 	current_object = cmds.ls(sl=True, l=True)[0]
# 	reset_selected_object(current_object)

# 	# Export Image
# 	screenshot_object(LIBRARY_IMAGE_PATH, file_name, current_object)

# 	# Export FBX
# 	current_object = cmds.rename(current_object, file_name)
# 	cmds.select(current_object, r=True)
# 	export_object_fbx(LIBRARY_FBX_PATH, file_name)

# 	# Delete current object
# 	cmds.delete(current_object)

# 	# Reload Library Scroll List
# 	# reload_library_scroll_list(LIBRARY_FBX_PATH)

# def delete_object_from_library(LIBRARY_FBX_PATH, LIBRARY_IMAGE_PATH):
# 	selected_objects = cmds.textField('search_library_tf', q=True, tx=True)
# 	try:
# 		confirm = cmds.confirmDialog(m='Deleted {} !!!'.format(selected_objects), title='Deleted {} !!!'.format(selected_objects), button=['Yes', 'Cancel'], defaultButton='Yes', cancelButton='No', dismissString='No', icon='warning')
# 		if confirm == 'Yes':
# 			os.remove(LIBRARY_FBX_PATH + "/" + selected_objects + ".fbx")
# 			os.remove(LIBRARY_IMAGE_PATH + "/" + selected_objects + ".png")
# 			cmds.confirmDialog(m="{} has been deleted !!!".format(selected_objects), icon='information')
# 	except:
# 		pass

# 	# Reload Library Scroll List
# 	# reload_library_scroll_list(LIBRARY_FBX_PATH)

# def edit_object_from_library(LIBRARY_FBX_PATH, LIBRARY_IMAGE_PATH):
# 	selected_objects = cmds.ls(sl=True, l=True)
# 	if len(selected_objects) == 0:
# 		cmds.confirmDialog(icn="information", m = "Please select 1 object in scene to EDIT!")
# 		return False

# 	selected_object_in_library = cmds.textScrollList('object_list_library_tscl', q = True, si=True)
# 	if selected_object_in_library:
# 		if len(selected_object_in_library) != 1:
# 			cmds.confirmDialog(icn="information", m = "Please select 1 object in library to EDIT!")
# 			return False
# 	else:
# 			cmds.confirmDialog(icn="information", m = "Library have 0 object in list to EDIT!")
# 			return False
# 	# Get file name
# 	file_name = selected_object_in_library[0]

# 	# Duplicate Object To Export
# 	cmds.duplicate(selected_objects[0])
# 	current_object = cmds.ls(sl=True, l=True)[0]
# 	reset_selected_object(current_object)

# 	# Export Image
# 	screenshot_object(LIBRARY_IMAGE_PATH, file_name, current_object)

# 	# Export FBX
# 	current_object = cmds.rename(current_object, "HS_" + file_name)
# 	cmds.select(current_object, r=True)
# 	export_object_fbx(LIBRARY_FBX_PATH, file_name)

# 	# Delete current object
# 	cmds.delete(current_object)

# 	# Reload Library Scroll List
# 	reload_library_scroll_list(LIBRARY_FBX_PATH)

#endregion

#endregion

#region Maya - Blender
def MayaBlender_setting_path():
	folder_path = r'C:/Blender_ImportExport'
	if not os.path.exists(folder_path):
		os.makedirs(folder_path)
	return (folder_path)

def checking_FBXversion():
	mayaVersion = cmds.about(q=True, version=True)

	if int(mayaVersion) <= 2015:
		FBXVersion = 'FBX201500'
	else:
		FBXVersion = 'FBX{}00'.format(mayaVersion)

	return FBXVersion


def MayaBlender_FBXImport_setting():

	folder_path = MayaBlender_setting_path()
	temp_file_name = folder_path + '/BLENDER_MAYA_MAX.fbx'
	export_normal_mode = cmds.radioButtonGrp('export_normal_mode_rbg', q=True, sl=True)

	if export_normal_mode == 1:
		unlockNormal = 'false'
	else:
		unlockNormal = 'true'

	mel.eval('FBXImportAxisConversionEnable -v false;')
	mel.eval('FBXImportCacheFile -v false;')
	mel.eval('FBXImportCameras -v false;')
	mel.eval('FBXImportConstraints -v false;')
	mel.eval('FBXImportConvertDeformingNullsToJoint -v false;')
	mel.eval('FBXImportGenerateLog -v false;')
	mel.eval('FBXImportLights -v false;')
	mel.eval('FBXImportMode -v "add";')
	mel.eval('FBXImportScaleFactor 1.0;')
	mel.eval('FBXImportUpAxis "y";')
	mel.eval('FBXImportUnlockNormals -v {};'.format(unlockNormal))
	mel.eval('FBXImport -f "{}";'.format(temp_file_name))


def MayaBlender_FBXExport_setting():
	FBXVersion = checking_FBXversion()

	folder_path = MayaBlender_setting_path()
	temp_file_name = folder_path + '/BLENDER_MAYA_MAX.fbx'

	mel.eval('FBXExportSmoothingGroups -v false;')
	mel.eval('FBXExportHardEdges -v false;')
	mel.eval('FBXExportTangents -v true;')
	mel.eval('FBXExportSmoothMesh -v false;')
	mel.eval('FBXExportInstances -v false;')
	mel.eval('FBXExportReferencedAssetsContent -v false;')

	mel.eval('FBXExportAnimationOnly -v false;')
	mel.eval('FBXExportApplyConstantKeyReducer -v false;')
	mel.eval('FBXExportBakeComplexAnimation -v false;')
	mel.eval('FBXExportBakeResampleAnimation -v false;')
	mel.eval('FBXExportCacheFile -v false;')
	mel.eval('FBXExportColladaSingleMatrix false;')
	mel.eval('FBXExportColladaTriangulate false;')
	mel.eval('FBXExportConstraints -v false;')
	mel.eval('FBXExportInstances -v false;')
	mel.eval('FBXExportShapes -v false;')
	mel.eval('FBXExportSkins -v false;')
	mel.eval('FBXExportTriangulate -v false;')
	mel.eval('FBXExportUseSceneName -v false;')

	mel.eval('FBXExportInAscii -v false')
	mel.eval('FBXExportCameras -v false;')
	mel.eval('FBXExportLights -v false;')
	mel.eval('FBXExportEmbeddedTextures -v false;')
	mel.eval('FBXExportConvertUnitString "cm";')
	mel.eval('FBXExportFileVersion "{}";'.format(FBXVersion))
	mel.eval('FBXExportUpAxis "y";')
	mel.eval('FBXExportScaleFactor 1.0;')
	mel.eval('FBXExportGenerateLog -v false;')
	mel.eval('FBXExport -f "{0}" -s;'.format(temp_file_name))


def export_to_blender(*arg):
	if cmds.ls(sl=True):
		MayaBlender_FBXExport_setting()
		cmds.warning('EXPORT DONE!')
		cmds.select(cl=True)
	else:
		cmds.warning('Selection is empty! Please select some objects!!')


def import_from_blender(*arg):
	folder_path = MayaBlender_setting_path()
	temp_file_name = folder_path + '/BLENDER_MAYA_MAX.fbx'

	if os.path.isfile(temp_file_name):
		MayaBlender_FBXImport_setting()
#endregion

#region Import/Export
def remove_all_namespace(*arg):
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
	else:
		cmds.select(d=True)
	return err

def write_path_json_file(path, content):
	# Write json file
	dictionary = content
	# Serializing json 
	json_object = json.dumps(dictionary, indent = 4)
	# Writing to sample.json
	with open(path, "w") as outfile:
		outfile.write(json_object)
	outfile.close()
	return True		

def get_import_export_file_path(data, json_path):
	try:
		path = cmds.fileDialog2(startingDirectory = data['default_path'], fileFilter="Maya Files (*.ma *.mb);;Maya ASCII (*.ma);;Maya Binary (*.mb)", fileMode = 1)[0]
		data['default_path'] = path
		write_path_json_file(json_path, data)
		cmds.textField('import_export_path_tf', e = True, tx = data['default_path'])
		return True
	except:
		return False

def export_current_file(*arg):
	file_path = cmds.textField('import_export_path_tf', q = True, tx = True)
	file_type = file_path.rsplit('.', 1)[-1].lower()
	if file_type == 'ma':
		cmds.file(file_path, force = True, options = "v=0;", typ = "mayaAscii", preserveReferences = True, exportSelected = True, constructionHistory=False)
	elif file_type == 'mb':
		cmds.file(file_path, force = True, options = "v=0;", typ = "mayaBinary", preserveReferences = True, exportSelected = True, constructionHistory=False)

def import_current_file(*arg):
	file_path = cmds.textField('import_export_path_tf', q = True, tx = True)
	file_namespace = file_path.replace("\\", "/").rsplit("/", 1)[-1].rsplit(".", 1)[0]

	file_type = file_path.rsplit('.', 1)[-1].lower()
	if file_type == 'ma':
		cmds.file(file_path, i = True, ignoreVersion = True, renameAll = True, mergeNamespacesOnClash = False, namespace = file_namespace, options="v=0;", typ = "mayaAscii", preserveReferences = True, constructionHistory=False)
	elif file_type == 'mb':
		cmds.file(file_path, i = True, ignoreVersion = True, renameAll = True, mergeNamespacesOnClash = False, namespace = file_namespace, options="v=0;", typ = "mayaBinary", preserveReferences = True, constructionHistory=False)
	
	# Optimize layer
	layer_list = [layer for layer in cmds.ls(type='displayLayer',long=True) if not layer =='defaultLayer']
	old_layer_list = [layer for layer in layer_list if file_namespace + ":" in layer]
	new_layer_list = list(set(layer_list) - set(old_layer_list))

	for layer in old_layer_list:
		new_layer = layer.split(":", 1)[-1]
		if new_layer in new_layer_list:
			old_object_list = cmds.editDisplayLayerMembers(layer, query=True)
			for obj in old_object_list:
				cmds.editDisplayLayerMembers(new_layer, obj)
	cmds.delete(old_layer_list)

	# optimize Materials
	material_list = []
	for shading_engine in cmds.ls(type='shadingEngine'):
		if cmds.sets(shading_engine, q=True):
			for material in cmds.ls(cmds.listConnections(shading_engine), materials=True):
				material_list.append(material)
	
	old_material_list = [material for material in material_list if file_namespace + ":" in material]

	delete_material_list = []
	if old_material_list != None:
		for material in old_material_list:
			new_material = material.split(":", 1)[-1]
			if new_material in material_list:
				cmds.hyperShade(objects = material)
				# object connect new material
				if cmds.listConnections(new_material,type='shadingEngine') != None:
					shadingEngine = cmds.listConnections(new_material,type='shadingEngine')[0]
					cmds.sets(e=True, forceElement=shadingEngine)
				else:
					cmds.hyperShade(assign=new_material[0])
					cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=new_material[0]+'SG')
					shadingEngine=cmds.listConnections(new_material,type='shadingEngine')[0]
					cmds.sets(e=True, forceElement=shadingEngine)
				delete_material_list.append(material)
	cmds.delete(delete_material_list)
	mel.eval("MLdeleteUnused;")
	remove_all_namespace()

#endregion

#region Fix
def fix_error_maya_file(*arg):
	# Read
	current_file_path = cmds.file(q= True, loc = True)
	current_maya_file = open(current_file_path, "r")
	current_maya_file_content = current_maya_file.read()
	current_maya_file.close()
	# Write
	current_maya_file = open(current_file_path, "w")
	current_maya_file_content = current_maya_file_content.replace("-nan(ind)", "0.0")
	current_maya_file_content = current_maya_file_content.replace("nan(ind)", "0.0")
	current_maya_file.write(current_maya_file_content)
	current_maya_file.close()
	cmds.warning('Fix COMPLETE! please dont save current file and re-open it!')

def fix_cant_create_mesh(*arg):
	mel.eval('lockNode -l 0 -lu 0 initialShadingGroup;')
	cmds.warning('Fix COMPLETE!')

#endregion

#endregion