# -*- coding: utf-8 -*-
"""
Slide Snap - snap the selected vertices onto a target face by SLIDING them.

Each vertex moves along a line until it meets the face:
  * Along Edge : an edge of the vertex (the one that reaches the face first, or only the selected edges)
  * X / Y / Z  : a world axis
  * Normal     : the normal of the target face (shortest way to the face)

The vertex always lands on the PLANE of the target face (the face's border is not a limit).
The maths lives in slide_snap_core.py (pure python, unit tested); this file only talks to Maya.
"""
import re

import maya.cmds as cmds
import maya.api.OpenMaya as om

import slide_snap_core as core
try:
	from importlib import reload
except ImportError:
	pass
reload(core)

WINDOW = 'snap_tool_window'
TITLE = 'Slide Snap'
OPT = 'slide_snap_'

DIRECTIONS = ('edge', 'x', 'y', 'z', 'normal')
DIR_LABELS = {'edge': 'Along Edge', 'x': 'X', 'y': 'Y', 'z': 'Z', 'normal': 'Normal'}
DIR_TIPS = {
	'edge': 'Slide along the edges of each vertex',
	'x': 'Slide along the world X axis',
	'y': 'Slide along the world Y axis',
	'z': 'Slide along the world Z axis',
	'normal': 'Slide straight along the normal of the target face (shortest distance)',
}
AXES = {'x': (1.0, 0.0, 0.0), 'y': (0.0, 1.0, 0.0), 'z': (0.0, 0.0, 1.0)}

_state = {'face': None}      # (full dag path of the mesh shape, polygon index)


#----------------------------------------------------------------------------- small helpers

def _opt(name, default):
	key = OPT + name
	return cmds.optionVar(q=key) if cmds.optionVar(ex=key) else default


def _save_opt(name, value):
	key = OPT + name
	if isinstance(value, float):
		cmds.optionVar(fv=[key, value])
	else:
		cmds.optionVar(iv=[key, int(value)])


def _dag_from_name(name):
	sel = om.MSelectionList()
	sel.add(name)
	return sel.getDagPath(0)


_COMPONENT = re.compile(r'^(?P<node>.+)\.(?P<kind>vtx|e|f)\[(?P<a>\d+)(?::(?P<b>\d+))?\]$')


def _shape_path(node):
	"""Full path of the mesh shape of a transform / shape name."""
	if cmds.objectType(node) == 'mesh':
		return (cmds.ls(node, l=True) or [node])[0]
	shapes = cmds.listRelatives(node, s=True, f=True, type='mesh', ni=True) or []
	return shapes[0] if shapes else None


def _selection():
	"""Selected components: ([(path, vertex id)], [(path, edge id)], [(path, face id)]) with path = full shape path.

	Read with cmds.ls: MGlobal.getActiveSelectionList() keeps only ONE component type per mesh when vertices and
	edges are selected together (multi selection mode), so the edges would silently be lost."""
	verts, edges, faces = [], [], []
	shape_cache = {}
	for item in cmds.ls(sl=True, fl=False, l=True) or []:
		m = _COMPONENT.match(item)
		if not m:
			continue
		node = m.group('node')
		if node not in shape_cache:
			shape_cache[node] = _shape_path(node)
		path = shape_cache[node]
		if not path:
			continue
		first = int(m.group('a'))
		last = int(m.group('b')) if m.group('b') is not None else first
		target = {'vtx': verts, 'e': edges, 'f': faces}[m.group('kind')]
		target += [(path, i) for i in range(first, last + 1)]
	return verts, edges, faces


def _face_polygon():
	"""(centroid, normal, points, tolerance) of the stored target face, or None."""
	face = _state['face']
	if not face:
		return None
	try:
		dag = _dag_from_name(face[0])
		it = om.MItMeshPolygon(dag)
		it.setIndex(face[1])
		pts = [(p.x, p.y, p.z) for p in it.getPoints(om.MSpace.kWorld)]
	except Exception:
		return None
	centroid, normal = core.polygon_plane(pts)
	if normal is None:
		return None
	return centroid, normal, pts, core.polygon_tolerance(pts)


def _face_label(face):
	try:
		return '{0}.f[{1}]'.format(_dag_from_name(face[0]).partialPathName(), face[1])
	except Exception:
		return ''


#----------------------------------------------------------------------------- UI state

def _current_direction():
	sel = cmds.radioCollection(OPT + 'dir_rc', q=True, sl=True)
	for d in DIRECTIONS:
		if sel and sel.endswith('_' + d):
			return d
	return 'edge'


def _refresh_status(*args):
	if not cmds.window(WINDOW, ex=True):
		return
	problems = []
	if not _face_polygon():
		problems.append('pick a target face')
	verts = _selection()[0]
	if not verts:
		problems.append('select the vertices to snap')
	if problems:
		msg = 'Next: ' + ', then '.join(problems)
		color = (0.45, 0.35, 0.1)
	else:
		msg = 'Ready: {0} {1} -> {2}'.format(len(verts), 'vertex' if len(verts) == 1 else 'vertices', _face_label(_state['face']))
		color = (0.15, 0.4, 0.2)
	cmds.text(OPT + 'status', e=True, l=msg, bgc=color)
	cmds.button(OPT + 'snap_btn', e=True, en=not problems)


def _refresh_enabled(*args):
	edge_mode = _current_direction() == 'edge'
	cmds.optionMenu(OPT + 'edge_om', e=True, en=edge_mode)
	cmds.checkBox(OPT + 'both_cb', e=True, en=edge_mode)
	cmds.checkBox(OPT + 'keep_cb', e=True, en=edge_mode)
	# "Keep on edge only" and "both directions" make no sense when only the selected edge's own range counts
	if edge_mode and cmds.checkBox(OPT + 'keep_cb', q=True, v=True):
		cmds.checkBox(OPT + 'both_cb', e=True, en=False)
	_save_opt('dir', DIRECTIONS.index(_current_direction()))
	_save_opt('edge', cmds.optionMenu(OPT + 'edge_om', q=True, sl=True) - 1)
	_save_opt('both', cmds.checkBox(OPT + 'both_cb', q=True, v=True))
	_save_opt('keep', cmds.checkBox(OPT + 'keep_cb', q=True, v=True))
	_save_opt('max', float(cmds.floatField(OPT + 'max_ff', q=True, v=True)))


def pick_face(*args):
	faces = _selection()[2]
	if not faces:
		cmds.warning('Slide Snap: select a face first, then press Pick Face.')
		return
	_state['face'] = faces[0]
	cmds.textField(OPT + 'face_tf', e=True, tx=_face_label(faces[0]))
	if len(faces) > 1:
		cmds.inViewMessage(amg='Slide Snap: {0} faces selected, using the first one'.format(len(faces)), pos='topCenter', fade=True)
	_refresh_status()


def show_face(*args):
	face = _state['face']
	if face and _face_polygon():
		cmds.select('{0}.f[{1}]'.format(face[0], face[1]), r=True)
	else:
		cmds.warning('Slide Snap: no valid target face.')


#----------------------------------------------------------------------------- the snap

def snap(*args):
	plane = _face_polygon()
	if not plane:
		cmds.warning('Slide Snap: pick a target face first.')
		return
	centroid, normal, poly, tol = plane
	verts, edges, _faces = _selection()
	if not verts:
		cmds.warning('Slide Snap: select the vertices to snap.')
		return

	direction = _current_direction()
	selected_edges_only = cmds.optionMenu(OPT + 'edge_om', q=True, sl=True) == 2
	keep_on_edge = cmds.checkBox(OPT + 'keep_cb', q=True, v=True)
	both = cmds.checkBox(OPT + 'both_cb', q=True, v=True)
	max_dist = float(cmds.floatField(OPT + 'max_ff', q=True, v=True))

	# neighbours through the selected edges (only needed for "Selected edges only")
	edge_neighbors = {}
	if direction == 'edge' and selected_edges_only:
		meshes = {}
		for path, eid in edges:
			dag = meshes.setdefault(path, _dag_from_name(path))
			it = om.MItMeshEdge(dag)
			it.setIndex(eid)
			a, b = it.vertexId(0), it.vertexId(1)
			edge_neighbors.setdefault((path, a), []).append(b)
			edge_neighbors.setdefault((path, b), []).append(a)

	# Phase 1: compute every new position from the ORIGINAL positions (so the order of vertices never matters)
	moves = []                   # (component name, new position)
	skipped = {}                 # reason -> [component names]
	mesh_cache = {}
	unique = []
	seen = set()
	for item in verts:
		if item not in seen:
			seen.add(item)
			unique.append(item)

	for path, vid in unique:
		if path not in mesh_cache:
			dag = _dag_from_name(path)
			mesh_cache[path] = (dag, om.MFnMesh(dag), om.MItMeshVertex(dag))
		dag, fn, it = mesh_cache[path]
		name = '{0}.vtx[{1}]'.format(path, vid)
		pt = fn.getPoint(vid, om.MSpace.kWorld)
		p = (pt.x, pt.y, pt.z)

		if direction == 'edge':
			if selected_edges_only:
				ids = edge_neighbors.get((path, vid), [])
				if not ids:
					skipped.setdefault('no selected edge on this vertex', []).append(name)
					continue
			else:
				it.setIndex(vid)
				ids = list(it.getConnectedVertices())
			neighbors = []
			for n in ids:
				q = fn.getPoint(n, om.MSpace.kWorld)
				neighbors.append((q.x, q.y, q.z))
			candidates = core.edge_candidates(p, neighbors, both=both, keep_on_edge=keep_on_edge)
		elif direction == 'normal':
			candidates = core.line_candidate(normal)
		else:
			candidates = core.line_candidate(AXES[direction])

		hit, _t, reason = core.solve_vertex(p, candidates, centroid, normal, poly, False, max_dist, tol)
		if hit is None:
			skipped.setdefault(reason, []).append(name)
		else:
			moves.append((name, hit))

	# Phase 2: apply (single undo step)
	cmds.undoInfo(openChunk=True)
	try:
		for name, hit in moves:
			cmds.xform(name, ws=True, t=hit)
	finally:
		cmds.undoInfo(closeChunk=True)

	# Report
	skipped_total = sum(len(v) for v in skipped.values())
	text = '<hl>{0}</hl>: {1} snapped'.format(TITLE, len(moves))
	if skipped_total:
		text += ', {0} skipped'.format(skipped_total)
		cmds.select([n for names in skipped.values() for n in names], r=True)   # leave the problems selected
		for reason, names in skipped.items():
			print('Slide Snap: {0} vertex(es) skipped - {1}: {2}'.format(len(names), reason, ', '.join(names[:8]) + (' ...' if len(names) > 8 else '')))
		text += ' ({0})'.format('; '.join('{0}: {1}'.format(len(v), k) for k, v in skipped.items()))
	cmds.inViewMessage(amg=text, pos='topCenter', fade=True)
	_refresh_status()


#----------------------------------------------------------------------------- window

def open_tool(parent_window=None):
	if cmds.window(WINDOW, ex=True):
		cmds.deleteUI(WINDOW, window=True)
	_state['face'] = None
	kwargs = {'title': TITLE, 'rtf': True, 'mnb': False, 'mxb': False}
	if parent_window and cmds.window(parent_window, ex=True):
		kwargs['p'] = parent_window
	cmds.window(WINDOW, **kwargs)
	root = cmds.columnLayout(OPT + 'root', adj=True, rs=4, cw=330)

	# 1. Target
	cmds.frameLayout(l='1. Target Face', collapsable=False, p=root, mw=4, mh=4)
	cmds.rowColumnLayout(nc=3, cw=[(1, 205), (2, 55), (3, 65)], adj=1, cs=[(2, 4), (3, 4)])
	cmds.textField(OPT + 'face_tf', ed=False, tx='', ann='The face the vertices will be snapped onto')
	cmds.button(l='Pick Face', bgc=(0.2, 0.8, 0.5), ann='Select a face, then press: it becomes the target', c=pick_face)
	cmds.button(l='Show', ann='Select the target face again', c=show_face)
	cmds.setParent(root)

	# 2. Direction
	cmds.frameLayout(l='2. Slide Direction', collapsable=False, p=root, mw=4, mh=4)
	cmds.rowColumnLayout(nc=5, cw=[(1, 90), (2, 40), (3, 40), (4, 40), (5, 75)], adj=5)
	rc = cmds.radioCollection(OPT + 'dir_rc')
	current = DIRECTIONS[int(_opt('dir', 0))]
	for d in DIRECTIONS:
		cmds.radioButton(OPT + 'dir_rb_' + d, l=DIR_LABELS[d], cl=rc, sl=(d == current), ann=DIR_TIPS[d], onc=_refresh_enabled)
	cmds.setParent('..')
	cmds.rowColumnLayout(nc=2, cw=[(1, 70), (2, 255)], adj=2)
	cmds.text(l='Edge choice:', align='left', ann='Which edge of the vertex to slide along')
	cmds.optionMenu(OPT + 'edge_om', cc=_refresh_enabled, ann='Auto: use the edge that reaches the face first')
	cmds.menuItem(l='Auto (edge that reaches the face first)')
	cmds.menuItem(l='Selected edges only (select edges + vertices)')
	cmds.optionMenu(OPT + 'edge_om', e=True, sl=int(_opt('edge', 0)) + 1)
	cmds.setParent('..')
	cmds.rowColumnLayout(nc=2, cw=[(1, 150), (2, 175)], adj=2)
	cmds.checkBox(OPT + 'both_cb', l='Both directions (±)', v=bool(_opt('both', 1)), cc=_refresh_enabled,
	              ann='Also slide backwards, extending the edge past the vertex')
	cmds.checkBox(OPT + 'keep_cb', l='Stay on the edge', v=bool(_opt('keep', 0)), cc=_refresh_enabled,
	              ann='Only snap when the plane of the face is reached within the edge itself (no overshoot)')
	cmds.setParent(root)

	# 3. Options
	cmds.frameLayout(l='3. Options', collapsable=False, p=root, mw=4, mh=4)
	cmds.rowColumnLayout(nc=2, cw=[(1, 150), (2, 175)], adj=2)
	cmds.text(l='Max Distance:', align='left', ann='Vertices that would move farther than this are skipped (0 = unlimited)')
	cmds.floatField(OPT + 'max_ff', min=0, v=float(_opt('max', 0.0)), pre=3, cc=_refresh_enabled,
	                ann='0 = unlimited')
	cmds.setParent(root)

	# Action
	cmds.text(OPT + 'status', l='', h=24, p=root)
	cmds.button(OPT + 'snap_btn', l='Snap Vertices', h=36, bgc=(0.2, 0.8, 0.5), p=root, c=snap,
	            ann='Slide the selected vertices onto the target face (one undo step)')

	cmds.scriptJob(e=['SelectionChanged', _refresh_status], p=WINDOW)
	_refresh_enabled()
	_refresh_status()
	cmds.showWindow(WINDOW)
