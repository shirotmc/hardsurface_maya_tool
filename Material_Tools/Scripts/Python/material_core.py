# -*- coding: utf-8 -*-
"""
Material Manager - Maya logic (no UI).

Python port of "Material Manager" v5.2.0 by Dennis Porter (GPL-3.0)
https://github.com/Bartalon/Material-Manager

Differences from the MEL original
---------------------------------
* No global MEL state: the UI keeps the state, every function here takes plain arguments.
* Materials are created with shadingNode + sets (no hypershade / createRenderNodeCB), so nothing depends on
  the Hypershade being open.
* Channel attributes also cover Standard Surface (default material of Maya 2022+).
* StingrayPBS / DX11 Uber specific handling of the original is not ported (shaders removed from modern Maya).
"""
from __future__ import print_function

import os

import maya.cmds as cmds
import maya.api.OpenMaya as om

import material_data as data

STARTING_SG = 'initialShadingGroup'
# Material connected to the default shading group: lambert1 up to Maya 2021, standardSurface1 since Maya 2022
# (see default_material(), which asks the scene)
STARTING_MAT = 'lambert1'

# Nodes that must never be deleted / renamed
PROTECTED = set([
	'lambert1', 'standardSurface1', 'particleCloud1', 'initialShadingGroup', 'initialParticleSE',
	'initialMaterialInfo', 'defaultShaderList1', 'defaultTextureList1', 'defaultColorMgtGlobals',
	'defaultRenderUtilityList1', 'shaderBallGeomShape1',
])

QUICK_MATERIALS = ('lambert', 'phong', 'blinn', 'standardSurface')

CHECKER_PRESETS = (
	('Checker', (0.125, 0.125, 0.125), (0.5, 0.5, 0.5)),
	('Checker_Good', (0.0, 0.125, 0.0), (0.0, 0.5, 0.0)),
	('Checker_Bad', (0.125, 0.0, 0.0), (0.5, 0.0, 0.0)),
)


class MMError(Exception):
	"""A problem the user should read (shown as a warning, never a traceback)."""


#----------------------------------------------------------------------------- scene queries

def _exists(name):
	return bool(name) and cmds.objExists(name)


def is_material(name):
	return _exists(name) and name in set(cmds.ls(mat=True) or [])


def is_component(name):
	return '.' in name and bool(cmds.filterExpand(name, sm=[31, 32, 34, 35, 70]))


def all_materials(include_particle=False, sort='alpha'):
	"""All materials of the scene. sort: 'alpha' (case-insensitive) or 'scene' (creation order)."""
	mats = list(cmds.ls(mat=True) or [])
	if not include_particle:
		clouds = set(cmds.ls(type='particleCloud') or [])
		mats = [m for m in mats if m not in clouds]
	if sort == 'alpha':
		mats.sort(key=lambda m: m.lower())
	return mats


def filter_materials(mats, term):
	"""Keep the materials whose name contains ALL the words of the search text (case-insensitive)."""
	words = [w.lower() for w in (term or '').split()]
	if not words:
		return list(mats)
	return [m for m in mats if all(w in m.lower() for w in words)]


def default_material():
	"""The material of the default shading group (what faces fall back to when a material is deleted)."""
	if cmds.objExists(STARTING_SG):
		mats = cmds.listConnections(STARTING_SG + '.surfaceShader', s=True, d=False) or []
		if mats:
			return mats[0]
	return STARTING_MAT


def is_default_material(mat):
	return mat in (STARTING_MAT, default_material())


def shading_group(mat):
	if mat == default_material():
		return STARTING_SG
	if not _exists(mat):
		return None
	sgs = cmds.listConnections(mat, type='shadingEngine') or []
	return sgs[0] if sgs else None


def selection_shapes(nodes):
	"""Mesh shapes (full path) of objects / components."""
	shapes = []
	for n in nodes:
		base = n.split('.')[0]
		if not _exists(base):
			continue
		if cmds.objectType(base) == 'mesh':
			shapes.append(cmds.ls(base, l=True)[0])
		else:
			shapes += cmds.listRelatives(base, s=True, f=True, type='mesh', ni=True) or []
	seen, out = set(), []
	for s in shapes:
		if s not in seen:
			seen.add(s)
			out.append(s)
	return out


def assigned_materials(selection=None, report_children=False, per_component=True):
	"""Materials assigned to the selection (a selected material counts as assigned to itself)."""
	selection = cmds.ls(sl=True, l=True) if selection is None else selection
	mats, sets_ = [], []
	for obj in selection or []:
		if is_component(obj):
			target = obj if per_component else obj.split('.')[0]
			sets_ += cmds.listSets(type=1, ets=True, o=target) or []
		elif is_material(obj):
			mats.append(obj)
		elif report_children:
			shapes = cmds.listRelatives(obj, type='shape', f=True, ad=True) or []
			sets_ += cmds.listConnections(shapes, type='shadingEngine') or [] if shapes else []
		else:
			sets_ += cmds.listSets(type=1, ets=True, o=obj) or []
	for sg in dict.fromkeys(sets_) if hasattr(dict, 'fromkeys') else set(sets_):
		mats += cmds.listConnections(sg + '.surfaceShader', s=True, d=False) or []
	out, seen = [], set()
	for m in mats:
		if m not in seen:
			seen.add(m)
			out.append(m)
	return out


def material_color(mat):
	"""Colour used for the swatch of a material (falls back to a pink 'unknown')."""
	attr = channel_attr(mat, 'color')
	if attr:
		try:
			value = cmds.getAttr(mat + attr)
			if isinstance(value, list) and value and isinstance(value[0], (tuple, list)):
				value = value[0]
			if isinstance(value, (tuple, list)) and len(value) >= 3:
				return (value[0], value[1], value[2])
		except Exception:
			pass
	return (1.0, 0.6, 0.6)


def channel_attr(mat, channel):
	"""'.baseColor' etc. for the channel of this material, or None."""
	for attr in data.CHANNEL_ATTRS.get(channel, []):
		if cmds.objExists(mat + attr):
			return attr
	return None


def channel_source(mat, channel):
	"""Node connected to the channel (file / bump2d / ...), or None."""
	attr = channel_attr(mat, channel)
	if not attr:
		return None
	sources = cmds.listConnections(mat + attr, s=True, d=False) or []
	sources = [s for s in sources if cmds.objectType(s) != 'shadingEngine']
	return sources[0] if sources else None


def channel_is_empty(mat, channel):
	return channel_source(mat, channel) is None


def occupied_channels(mats):
	"""Channels used by at least one of the materials."""
	return [c for c in data.CHANNELS if any(not channel_is_empty(m, c) for m in mats)]


def handedness(shapes=None):
	"""'right', 'left', 'mixed' or 'none' for the tangent space of the selected meshes."""
	if shapes is None:
		sel = cmds.ls(sl=True, l=True) or []
		shapes = selection_shapes(sel)
		if not shapes:
			shapes = cmds.listRelatives(sel, ad=True, s=True, f=True, type='mesh') or []
	values = set()
	for s in shapes:
		if cmds.objExists(s + '.tangentSpace'):
			values.add(cmds.getAttr(s + '.tangentSpace'))
	if not values:
		return 'none'
	if len(values) > 1:
		return 'mixed'
	return 'left' if values.pop() == 2 else 'right'


#----------------------------------------------------------------------------- assignment

def _instance_components(nodes):
	"""Expand every object / component to all its instances."""
	out = []
	for item in nodes:
		base, _, comp = item.partition('.')
		shapes = selection_shapes([base])
		if shapes:
			parents = cmds.listRelatives(shapes[0], ap=True, f=True) or []
			if len(parents) > 1:
				out += [p + ('.' + comp if comp else '') for p in parents]
				continue
		out.append(item)
	return out


def assign_material(mat, targets=None, to_instances=True):
	"""Assign mat to the current selection (objects or faces). Returns the number of targets."""
	targets = cmds.ls(sl=True, l=True) if targets is None else targets
	targets = [t for t in targets if not is_material(t)]
	if not targets:
		raise MMError('Select objects or faces to assign %s to.' % mat)
	sg = shading_group(mat)
	if not sg:
		raise MMError('%s has no shading group.' % mat)
	if to_instances:
		targets = _instance_components(targets)
	cmds.sets(targets, e=True, forceElement=sg)
	return len(targets)


def select_material(mat, mode='replace', last=None, ordered=None):
	"""Select the material node. mode: replace | toggle | range | objects"""
	if mode == 'objects':
		sg = shading_group(mat)
		if sg:
			members = cmds.sets(sg, q=True) or []
			cmds.select(members, r=True) if members else cmds.select(clear=True)
			return len(members)
		return 0
	if mode == 'toggle':
		cmds.select(mat, tgl=True)
	elif mode == 'range' and last in (ordered or []) and mat in (ordered or []):
		a, b = sorted((ordered.index(last), ordered.index(mat)))
		cmds.select(ordered[a:b + 1], r=True)
	else:
		cmds.select(mat, r=True)
	return 1


def match_material(mats, selection_only=False):
	"""Select the objects / faces the materials are assigned to."""
	sel = cmds.ls(sl=True, l=True) or []
	members = []
	for mat in mats:
		sg = shading_group(mat)
		if sg:
			members += cmds.sets(sg, q=True) or []
	members = cmds.ls(members, l=True) if members else []
	if selection_only and sel:
		wanted_shapes = set(selection_shapes(sel))
		members = [m for m in members if (cmds.ls(m.split('.')[0], l=True) or [''])[0] in wanted_shapes
		           or any(s in wanted_shapes for s in selection_shapes([m]))]
		sel_faces = set(cmds.ls(cmds.polyListComponentConversion([s for s in sel if is_component(s)], tf=True) or [],
		                        fl=True, l=True) or []) if any(is_component(s) for s in sel) else None
		if sel_faces is not None:
			flat = cmds.ls(members, fl=True, l=True) or []
			members = [m for m in flat if (m in sel_faces) or '.' not in m]
	if not members:
		raise MMError('The marked materials are not assigned to any polygon.')
	cmds.select(members, r=True)
	return len(members)


#----------------------------------------------------------------------------- create / rename / delete

def unique_name(base):
	if not cmds.objExists(base):
		return base
	n = 1
	while cmds.objExists('%s%d' % (base, n)):
		n += 1
	return '%s%d' % (base, n)


def create_material(node_type, name):
	"""New shader + shading group named <name> / <name>_SG. Returns the material name."""
	name = data.sanitize_name(name) or 'Material'
	selection = cmds.ls(sl=True, l=True) or []
	mat = cmds.shadingNode(node_type, asShader=True, name=unique_name(name))
	sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=mat + '_SG')
	cmds.connectAttr(mat + '.outColor', sg + '.surfaceShader', force=True)
	# creating nodes must not change what the user has selected
	if selection:
		cmds.select(selection, r=True)
	else:
		cmds.select(clear=True)
	return mat


def default_surface_type():
	"""'standardSurface' on Maya 2020+, else 'lambert'."""
	return 'standardSurface' if 'standardSurface' in (cmds.allNodeTypes() or []) else 'lambert'


def quick_material(node_type, name, assign=True, prefix=False):
	if node_type == 'standardSurface' and 'standardSurface' not in (cmds.allNodeTypes() or []):
		raise MMError('Standard Surface needs Maya 2020 or newer.')
	if prefix and not name.startswith('M_'):
		name = 'M_' + name
	if cmds.objExists(name):
		raise MMError('%s already exists.' % name)
	sel = cmds.ls(sl=True, l=True) or []
	mat = create_material(node_type, name)
	assigned = 0
	if assign:
		targets = [s for s in sel if not is_material(s)]
		if targets:
			assigned = assign_material(mat, targets)
	cmds.select(sel, r=True) if sel else cmds.select(clear=True)
	return mat, assigned


def checker_material(kind, assign=True, prefix=False):
	"""Create (or reuse) the Checker / Checker_Good / Checker_Bad preset."""
	name, dark, light = CHECKER_PRESETS[kind]
	if prefix:
		name = 'M_' + name
	existing = [n for n in (name, 'M_' + name) if is_material(n)]
	sel = [s for s in (cmds.ls(sl=True, l=True) or []) if not is_material(s)]
	if existing:
		mat = existing[0]
		if assign and sel:
			assign_material(mat, sel)
		return mat, False
	mat = create_material('phong', name)
	tex = cmds.shadingNode('checker', asTexture=True, name=mat + '_C')
	p2d = cmds.shadingNode('place2dTexture', asUtility=True, name=mat + '_2D')
	_connect_place2d(p2d, tex)
	cmds.setAttr(tex + '.color1', *dark, type='double3')
	cmds.setAttr(tex + '.color2', *light, type='double3')
	cmds.setAttr(p2d + '.repeatU', 64)
	cmds.setAttr(p2d + '.repeatV', 64)
	cmds.connectAttr(tex + '.outColor', mat + '.color', force=True)
	cmds.setAttr(mat + '.specularColor', 0, 0, 0, type='double3')
	if assign and sel:
		assign_material(mat, sel)
	return mat, True


def apply_preset(entry, assign=True, prefix=False):
	"""Create the material described by a preset entry (data.parse_preset_line) and assign it."""
	node_type = entry['type']
	if node_type not in (cmds.allNodeTypes() or []):
		raise MMError('Material type "%s" is not available in this Maya.' % node_type)
	name = entry['name']
	if prefix:
		name = 'M_' + name
	for candidate in (name, 'M_' + name, data.unprefixed(name)):
		if is_material(candidate):
			if not assign:
				raise MMError('%s already exists in the scene.' % candidate)
			targets = [s for s in (cmds.ls(sl=True, l=True) or []) if not is_material(s)]
			if targets:
				assign_material(candidate, targets)
			return candidate, False
	mat = create_material(node_type, name)
	for attr, values in entry['attrs']:
		if not cmds.objExists(mat + attr):
			continue
		try:
			if len(values) == 1:
				cmds.setAttr(mat + attr, values[0])
			elif len(values) == 3:
				cmds.setAttr(mat + attr, values[0], values[1], values[2], type='double3')
		except RuntimeError:
			pass
	if assign:
		sel = [s for s in (cmds.ls(sl=True, l=True) or []) if not is_material(s)]
		if sel:
			assign_material(mat, sel)
	return mat, True


def rename_material(mat, new_name, prefix=False):
	"""Rename the material and everything that belongs to it (shading group, file and utility nodes)."""
	if mat in PROTECTED:
		raise MMError('%s cannot be renamed.' % mat)
	new_name = data.sanitize_name(new_name)
	if prefix and not new_name.startswith('M_'):
		new_name = 'M_' + new_name
	if not new_name:
		raise MMError('Invalid name.')
	if cmds.objExists(new_name) and new_name != mat:
		raise MMError('%s already exists.' % new_name)
	mat = cmds.rename(mat, new_name)
	relate_names(mat)
	return mat


def _restore_selection(selection):
	existing = [s for s in selection if cmds.objExists(s)]
	if existing:
		cmds.select(existing, r=True)
	else:
		cmds.select(clear=True)


def _unique(items):
	"""Same order, no duplicates (listConnections repeats a node once per connection)."""
	seen, out = set(), []
	for i in items or []:
		if i not in seen:
			seen.add(i)
			out.append(i)
	return out


def relate_names(mat):
	"""Name the shading group / file / place2d / bump nodes after the material."""
	for sg in _unique(cmds.listConnections(mat, type='shadingEngine')):
		if sg != STARTING_SG and sg != mat + '_SG' and cmds.objExists(sg):
			cmds.rename(sg, mat + '_SG')
	file_names = {}
	for channel in data.CHANNELS:
		src = channel_source(mat, channel)
		if not src:
			continue
		suffix = data.FILE_SUFFIX[channel]
		if cmds.objectType(src) == 'bump2d':
			files = cmds.listConnections(src, type='file', s=True, d=False) or []
			cmds.rename(src, mat + suffix + '_Tangent')
			src = files[0] if files else None
		if src and cmds.objExists(src) and src not in file_names:
			file_names[src] = suffix
	for node, suffix in file_names.items():
		if not cmds.objExists(node):
			continue
		if node != mat + suffix:
			node = cmds.rename(node, mat + suffix)
		for p2d in _unique(cmds.listConnections(node, type='place2dTexture', s=True, d=False)):
			if p2d != node + '_2D' and cmds.objExists(p2d):
				cmds.rename(p2d, node + '_2D')


def duplicate_material(mat, new_name, prefix=False):
	"""Duplicate the material with its whole network (textures are duplicated too)."""
	new_name = data.sanitize_name(new_name)
	if prefix and not new_name.startswith('M_'):
		new_name = 'M_' + new_name
	if cmds.objExists(new_name):
		raise MMError('%s already exists.' % new_name)
	sel = cmds.ls(sl=True, l=True) or []
	created = cmds.duplicate(mat, un=True) or []
	copies = [n for n in created if is_material(n)]
	if not copies:
		raise MMError('Could not duplicate %s.' % mat)
	new_mat = cmds.rename(copies[0], new_name)
	if not shading_group(new_mat):
		sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=new_mat + '_SG')
		cmds.connectAttr(new_mat + '.outColor', sg + '.surfaceShader', force=True)
	relate_names(new_mat)
	cmds.select(sel, r=True) if sel else cmds.select(clear=True)
	return new_mat


def _network(mat):
	"""The material and every node that feeds it (textures, utilities), without shading groups / globals."""
	nodes = cmds.listHistory(mat) or []
	return [n for n in nodes if n not in PROTECTED and cmds.objectType(n) not in ('shadingEngine', 'materialInfo')]


def _shared_nodes(mat, others):
	"""Nodes of mat's network that other materials also use."""
	mine = set(_network(mat))
	shared = set()
	for other in others:
		if other != mat:
			shared |= mine & set(_network(other))
	return shared


def delete_materials(mats):
	"""Delete materials with their texture / utility nodes. Faces using them go back to the default material."""
	mats = [m for m in mats if m not in PROTECTED and is_material(m)]
	if not mats:
		raise MMError('Nothing to delete (the default material cannot be deleted).')
	remaining = [m for m in all_materials(include_particle=True) if m not in mats]
	cmds.undoInfo(openChunk=True)
	try:
		for mat in mats:
			sg = shading_group(mat)
			members = (cmds.sets(sg, q=True) or []) if sg else []
			if members:
				cmds.sets(members, e=True, forceElement=STARTING_SG)
			shared = _shared_nodes(mat, remaining)
			doomed = [n for n in _network(mat) if n not in shared and cmds.objExists(n)]
			if sg and sg not in PROTECTED and cmds.objExists(sg):
				doomed.append(sg)
			if doomed:
				cmds.delete(doomed)
	finally:
		cmds.undoInfo(closeChunk=True)
	return len(mats)


#----------------------------------------------------------------------------- channels (textures)

def _connect_place2d(p2d, tex):
	# file nodes take all the place2dTexture outputs, procedural textures (checker...) only the two UV ones
	if cmds.objectType(tex) == 'file':
		for attr in ('coverage', 'translateFrame', 'rotateFrame', 'mirrorU', 'mirrorV', 'stagger', 'wrapU', 'wrapV',
		             'repeatUV', 'offset', 'rotateUV', 'noiseUV', 'vertexUvOne', 'vertexUvTwo', 'vertexUvThree',
		             'vertexCameraOne'):
			cmds.connectAttr(p2d + '.' + attr, tex + '.' + attr, force=True)
	cmds.connectAttr(p2d + '.outUV', tex + '.uvCoord', force=True)
	cmds.connectAttr(p2d + '.outUvFilterSize', tex + '.uvFilterSize', force=True)


def _connect_texture(mat, channel, attr, tex):
	"""Connect the file node to the channel attribute in the right way (bump for normals, alpha for scalars)."""
	plug = mat + attr
	if channel == 'normal' and attr in ('.normalCamera', '.miNormalCamera', '.bumpMap'):
		bump = cmds.shadingNode('bump2d', asUtility=True, name=mat + data.FILE_SUFFIX['normal'] + '_Tangent')
		cmds.setAttr(bump + '.bumpInterp', 1)          # tangent space normals
		cmds.connectAttr(tex + '.outAlpha', bump + '.bumpValue', force=True)
		cmds.connectAttr(bump + '.outNormal', plug, force=True)
		return
	attr_type = cmds.getAttr(plug, type=True)
	if attr_type in ('float', 'double', 'long', 'short', 'bool', 'doubleLinear'):
		cmds.connectAttr(tex + '.outAlpha', plug, force=True)
		cmds.setAttr(tex + '.alphaIsLuminance', True)  # greyscale maps drive scalar inputs by luminance
	else:
		cmds.connectAttr(tex + '.outColor', plug, force=True)


def connect_file(mat, channel, path=None):
	"""Create a file node (+place2d) for the channel and connect it. path=None opens a file dialog."""
	attr = channel_attr(mat, channel)
	if not attr:
		raise MMError('%s has no %s channel.' % (mat, data.CHANNEL_LABELS[channel].lower()))
	if not channel_is_empty(mat, channel):
		raise MMError('%s channel of %s is already occupied.' % (data.CHANNEL_LABELS[channel], mat))
	if path is None:
		picked = cmds.fileDialog2(fm=1, cap='Select %s texture for %s' % (data.CHANNEL_LABELS[channel].lower(), mat),
		                          ff='Images (*.png *.jpg *.jpeg *.tga *.tif *.tiff *.exr *.bmp *.psd *.dds);;All Files (*.*)')
		if not picked:
			return None
		path = picked[0]
	suffix = data.FILE_SUFFIX[channel]
	selection = cmds.ls(sl=True, l=True) or []          # creating nodes must not change the user's selection
	try:
		tex = cmds.shadingNode('file', asTexture=True, isColorManaged=True, name=mat + suffix)
		p2d = cmds.shadingNode('place2dTexture', asUtility=True, name=tex + '_2D')
		_connect_place2d(p2d, tex)
		cmds.setAttr(tex + '.fileTextureName', path, type='string')
		if channel == 'normal':
			cmds.setAttr(tex + '.ignoreColorSpaceFileRules', 1)
			cmds.setAttr(tex + '.colorSpace', 'Raw', type='string')
		elif channel in ('roughness', 'metallic', 'occlusion', 'specular', 'transparency') and cmds.getAttr(mat + attr, type=True) in ('float', 'double'):
			cmds.setAttr(tex + '.ignoreColorSpaceFileRules', 1)
			cmds.setAttr(tex + '.colorSpace', 'Raw', type='string')
		_connect_texture(mat, channel, attr, tex)
	finally:
		_restore_selection(selection)
	return tex


def delete_channel(mat, channel):
	"""Delete the texture network connected to the channel. Returns the number of deleted nodes."""
	attr = channel_attr(mat, channel)
	src = channel_source(mat, channel) if attr else None
	if not src:
		return 0
	if channel == 'transparency':
		color_src = channel_source(mat, 'color')
		if color_src and color_src == src:
			raise MMError('Opacity uses the same file as Color. Delete the Color channel instead.')
	nodes = [n for n in (cmds.listHistory(src) or []) if n not in PROTECTED]
	# do not delete nodes still used by another channel of this material
	keep = set()
	for other in data.CHANNELS:
		if other == channel:
			continue
		other_src = channel_source(mat, other)
		if other_src:
			keep |= set(cmds.listHistory(other_src) or [])
	nodes = [n for n in nodes if n not in keep and cmds.objExists(n)]
	if nodes:
		cmds.delete(nodes)
	return len(nodes)


def clear_channels(mat):
	return sum(delete_channel_safe(mat, c) for c in data.CHANNELS)


def delete_channel_safe(mat, channel):
	try:
		return delete_channel(mat, channel)
	except MMError:
		return 0


def load_textures_from_folder(mats, folder, suffixes, match_name=True):
	"""Find the textures of every material inside folder (and sub folders) and connect them.

	suffixes: {channel: [suffix, ...]}. Returns (connected, report lines)."""
	folders = data.walk_folders(folder)
	connected = 0
	report = []
	for mat in mats:
		base = data.unprefixed(mat)
		found = data.match_textures(base, folders, suffixes, match_name=match_name)
		if not found:
			report.append('%s: no matching texture' % mat)
			continue
		for channel, path in found.items():
			try:
				if connect_file(mat, channel, path):
					connected += 1
			except MMError as e:
				report.append('%s: %s' % (mat, e))
	return connected, report


#----------------------------------------------------------------------------- scene cleanup

def remove_unused_materials():
	"""Delete materials (and shading groups) assigned to nothing. Returns how many materials."""
	removed = 0
	for mat in all_materials(include_particle=False):
		if mat in PROTECTED:
			continue
		sg = shading_group(mat)
		if sg and not (cmds.sets(sg, q=True) or []):
			try:
				delete_materials([mat])
				removed += 1
			except MMError:
				pass
	for sg in cmds.ls(type='shadingEngine') or []:
		if sg in PROTECTED or not cmds.objExists(sg):
			continue
		if not cmds.listConnections(sg + '.surfaceShader', s=True, d=False):
			cmds.delete(sg)
	return removed


def remove_orphan_nodes():
	import maya.mel as mel
	mel.eval('source MLdeleteUnused.mel; MLdeleteUnused();')


def purge_scene():
	"""Everything back to the default material: all materials, textures and utilities are deleted. Not undoable."""
	meshes = cmds.ls(type='mesh', l=True) or []
	cmds.undoInfo(state=False)
	try:
		if meshes:
			cmds.sets(meshes, e=True, forceElement=STARTING_SG)
		mats = [m for m in all_materials(include_particle=False) if m not in PROTECTED]
		if mats:
			cmds.delete(mats)
		remove_orphan_nodes()
	finally:
		cmds.undoInfo(state=True)


def add_m_prefix():
	count = 0
	for mat in all_materials(include_particle=False):
		if mat not in PROTECTED and not mat.startswith('M_'):
			rename_material(mat, 'M_' + mat)
			count += 1
	return count


def relate_all_names():
	for mat in all_materials(include_particle=False):
		if mat not in PROTECTED:
			relate_names(mat)


#----------------------------------------------------------------------------- tools

def colorize(mats, restore=False, presets=None):
	"""Random colours for the materials that have no colour texture (restore=True: back to preset / grey)."""
	presets = presets or {}
	changed = 0
	for mat in mats:
		attr = channel_attr(mat, 'color')
		if not attr or channel_source(mat, 'color'):
			continue
		if restore:
			entry = presets.get(data.unprefixed(mat))
			rgb = data.preset_color(entry) if entry else (0.5, 0.5, 0.5)
		else:
			import random
			rgb = (random.random(), random.random(), random.random())
		try:
			cmds.setAttr(mat + attr, rgb[0], rgb[1], rgb[2], type='double3')
			changed += 1
		except RuntimeError:
			pass
	return changed


def _owner(component):
	"""Full path of the transform / shape a set member belongs to ('|box.f[3:5]' -> '|box')."""
	node = component.split('.')[0]
	full = cmds.ls(node, l=True) or [node]
	return full[0]


def vertex_color_from_material(objects=None):
	"""Paint each face with the colour of its material (vertex colours). Returns the number of material groups."""
	sel = cmds.ls(sl=True, l=True) or []
	objects = objects or [s for s in sel if not is_component(s) and not is_material(s)]
	if not objects:
		raise MMError('Select objects first.')
	owners = set()
	for shape in selection_shapes(objects):
		owners.add(shape)
		owners.update(cmds.listRelatives(shape, p=True, f=True) or [])
	painted = 0
	for sg in cmds.ls(type='shadingEngine') or []:
		mats = cmds.listConnections(sg + '.surfaceShader', s=True, d=False) or []
		members = [m for m in (cmds.sets(sg, q=True) or []) if _owner(m) in owners]
		if not mats or not members:
			continue
		rgb = material_color(mats[0])
		faces = cmds.polyListComponentConversion(members, tf=True) or members
		cmds.polyColorPerVertex(faces, r=rgb[0], g=rgb[1], b=rgb[2], a=1, cdo=True)
		painted += 1
	if sel:
		cmds.select(sel, r=True)
	return painted


def clear_vertex_color():
	for shape in selection_shapes(cmds.ls(sl=True, l=True) or []):
		cmds.polyColorPerVertex(shape, r=1, g=1, b=1, a=1, cdo=True)


def toggle_vertex_color_display():
	shapes = selection_shapes(cmds.ls(sl=True, l=True) or [])
	if not shapes:
		return
	current = cmds.polyOptions(shapes[0], q=True, colorShadedDisplay=True)
	state = bool(current[0]) if isinstance(current, (list, tuple)) else bool(current)
	cmds.polyOptions(shapes, colorShadedDisplay=not state)


def set_handedness(left):
	"""Switch the tangent space of the selected meshes (left = DirectX style / right = OpenGL style)."""
	sel = cmds.ls(sl=True, l=True) or []
	shapes = selection_shapes(sel) or (cmds.listRelatives(sel, ad=True, s=True, f=True, type='mesh') or [])
	value = 2 if left else 0
	for s in shapes:
		if cmds.objExists(s + '.tangentSpace'):
			cmds.setAttr(s + '.tangentSpace', value)
	return len(shapes)


def toggle_handedness():
	current = handedness()
	return set_handedness(left=(current != 'left'))


def remove_namespaces(nodes=None):
	nodes = cmds.ls(sl=True, l=True) if nodes is None else nodes
	removed = 0
	for n in nodes or []:
		short = n.split('|')[-1]
		if ':' in short:
			ns = short.rsplit(':', 1)[0].split(':')[0]
			if cmds.namespace(ex=ns):
				cmds.namespace(mnp=True, rm=ns)
				removed += 1
	return removed


def auto_match_name(use_scene_name=False, prefix=False):
	"""Name the single material of the single selected object after that object (or the scene)."""
	sel = cmds.ls(sl=True, l=True) or []
	mats = assigned_materials(sel)
	if len(sel) != 1 or len(mats) != 1:
		raise MMError('Auto match needs exactly one object with one material.')
	if use_scene_name:
		scene = os.path.splitext(os.path.basename(cmds.file(q=True, sn=True) or ''))[0] or 'untitled'
		base = scene
	else:
		base = data.strip_sm_prefix(data.strip_lod_suffix(sel[0].split('|')[-1]))
	new_name = data.sanitize_name(base)
	if prefix and not new_name.startswith('M_'):
		new_name = 'M_' + new_name
	mat = mats[0]
	if mat == new_name:
		return mat, 'unchanged'
	if is_material(new_name):
		assign_material(new_name, sel)
		return new_name, 'existing material assigned'
	if cmds.objExists(new_name):
		raise MMError('%s exists and is not a material.' % new_name)
	if mat in PROTECTED:
		created = create_material(default_surface_type(), new_name)
		assign_material(created, sel)
		return created, 'new material created (%s cannot be renamed)' % mat
	return rename_material(mat, new_name), 'renamed'


def harden_texture_borders(objects=None, progress=None):
	"""Hard edges on the UV shell borders, soft everywhere else (for consistent normal map bakes)."""
	objects = objects or [s for s in (cmds.ls(sl=True, l=True) or []) if not is_component(s) and not is_material(s)]
	shapes = selection_shapes(objects)
	if not shapes:
		raise MMError('Select one or more objects.')
	total_borders = 0
	for shape in shapes:
		borders = uv_border_edges(shape)
		cmds.polySoftEdge(shape, a=180, ch=False)             # everything soft
		if borders:
			cmds.polySoftEdge(component_names_of(shape, 'e', borders), a=0, ch=False)   # UV borders hard
		total_borders += len(borders)
	cmds.select(objects, r=True)
	return total_borders


def component_names_of(shape, kind, indices):
	return data.component_names(shape, kind, indices)


def uv_border_edges(shape, uv_set=None):
	"""Indices of the edges where the UVs of the two faces are not shared (UV shell borders / mesh borders)."""
	sl = om.MSelectionList()
	sl.add(shape)
	dag = sl.getDagPath(0)
	face_uv = {}
	it = om.MItMeshPolygon(dag)
	has_uv = True
	while not it.isDone():
		verts = it.getVertices()
		for i, v in enumerate(verts):
			try:
				face_uv[(it.index(), v)] = it.getUVIndex(i) if uv_set is None else it.getUVIndex(i, uv_set)
			except RuntimeError:
				has_uv = False
				face_uv[(it.index(), v)] = -1
		it.next()
	borders = []
	edge_it = om.MItMeshEdge(dag)
	while not edge_it.isDone():
		faces = edge_it.getConnectedFaces()
		a, b = edge_it.vertexId(0), edge_it.vertexId(1)
		if len(faces) != 2:
			borders.append(edge_it.index())
		elif has_uv and (face_uv[(faces[0], a)] != face_uv[(faces[1], a)] or face_uv[(faces[0], b)] != face_uv[(faces[1], b)]):
			borders.append(edge_it.index())
		edge_it.next()
	return borders


#----------------------------------------------------------------------------- Color ID baker

def split_shells(shape):
	"""Face index lists, one per connected polygon shell."""
	sl = om.MSelectionList()
	sl.add(shape)
	dag = sl.getDagPath(0)
	it = om.MItMeshPolygon(dag)
	count = om.MFnMesh(dag).numPolygons
	seen = [False] * count
	shells = []
	for start in range(count):
		if seen[start]:
			continue
		stack = [start]
		seen[start] = True
		shell = []
		while stack:
			f = stack.pop()
			shell.append(f)
			it.setIndex(f)
			for n in it.getConnectedFaces():
				if not seen[n]:
					seen[n] = True
					stack.append(n)
		shells.append(sorted(shell))
	return shells


def auto_assign_ids(objects, swatches, by_object=False, prefix=False, progress=None):
	"""Give every mesh element (or every object) a different colour ID material."""
	meshes = selection_shapes(cmds.listRelatives(objects, ad=True, f=True, type='mesh', ni=True) or []) or selection_shapes(objects)
	if not meshes:
		raise MMError('Select at least one mesh.')
	if not swatches:
		raise MMError('No colour swatches available.')
	index = 0
	assigned = 0
	cmds.undoInfo(openChunk=True)
	try:
		materials = {}
		def material_for(i):
			entry = swatches[i % len(swatches)]
			if entry['name'] not in materials:
				mat, _ = apply_preset(entry, assign=False, prefix=prefix) if not any(
					is_material(n) for n in (entry['name'], 'M_' + entry['name'])) else (
					entry['name'] if is_material(entry['name']) else 'M_' + entry['name'], False)
				materials[entry['name']] = mat
			return materials[entry['name']]
		if by_object:
			parents = []
			for s in meshes:
				p = (cmds.listRelatives(s, p=True, f=True) or [s])[0]
				if p not in parents:
					parents.append(p)
			for p in parents:
				assign_material(material_for(index), [p], to_instances=False)
				index += 1
				assigned += 1
				if progress and not progress(assigned, len(parents)):
					break
		else:
			for shape in meshes:
				shells = split_shells(shape)
				for shell in shells:
					faces = data.component_names(shape, 'f', shell)
					assign_material(material_for(index), faces, to_instances=False)
					index += 1
					assigned += 1
					if progress and not progress(assigned, None):
						break
	finally:
		cmds.undoInfo(closeChunk=True)
	return assigned


def bake_id_map(sources, target, cages, path, width, height, dilation, file_format):
	"""Bake the diffuse colours of the high poly meshes onto the UVs of the low poly mesh."""
	if not sources or not target:
		raise MMError('Load the high poly and the low poly meshes first.')
	if not path:
		raise MMError('Set the file destination first.')
	folder = os.path.dirname(path)
	if folder and not os.path.isdir(folder):
		os.makedirs(folder)
	base = os.path.splitext(path)[0]
	kwargs = dict(
		uvSet='map1', searchOffset=0, maxSearchDistance=20, mapOutput='diffuseRGB', mapWidth=int(width),
		mapHeight=int(height), maximumValue=1, mapSpace='tangent', mapMaterials=True, shadows=False,
		filename=base, fileFormat=file_format, superSampling=1, filterSize=0, overscan=int(dilation),
		searchMethod=0, useGeometryNormals=False, ignoreMirroredFaces=False, flipU=False, flipV=False,
		source=list(sources), target=list(target))
	if cages:
		kwargs['searchCage'] = list(cages)
	cmds.surfaceSampler(**kwargs)
	return base + '.' + file_format
