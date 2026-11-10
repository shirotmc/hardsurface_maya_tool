# -*- coding: utf-8 -*-
"""
Material Manager - pure data helpers (no Maya import, so it can be unit tested anywhere).

Python port of "Material Manager" v5.2.0 by Dennis Porter (GPL-3.0)
https://github.com/Bartalon/Material-Manager

Contents: channel tables, material preset parsing, name helpers, texture file matching.
"""
from __future__ import print_function

import os
import re

#----------------------------------------------------------------------------- channels

CHANNELS = ('color', 'normal', 'roughness', 'metallic', 'specular', 'occlusion', 'emissive', 'transparency')

CHANNEL_LABELS = {
	'color': 'Color', 'normal': 'Normal', 'roughness': 'Roughness', 'metallic': 'Metallic',
	'specular': 'Specular', 'occlusion': 'Occlusion', 'emissive': 'Emissive', 'transparency': 'Opacity',
}

# suffix of the file node created for each channel: <material><suffix>
FILE_SUFFIX = {
	'color': '_C', 'normal': '_N', 'roughness': '_R', 'metallic': '_M',
	'specular': '_S', 'occlusion': '_AO', 'emissive': '_E', 'transparency': '_T',
}

# Attributes tried for each channel, most relevant first. The first one that exists on the material wins.
# (Original list of Material Manager + Standard Surface / Arnold / USD preview surface names)
CHANNEL_ATTRS = {
	'color': ['.TEX_color_map', '.baseColor', '.diffuse_color', '.DiffuseTexture', '.overallTex', '.viewportColor',
	          '.color', '.surfaceColor', '.diffuse', '.diffuseColor', '.outColor', '.miColor', '.hardwareColor'],
	'normal': ['.TEX_normal_map', '.NormalTexture', '.base_bumpMap', '.normalCamera', '.normalMap',
	           '.miNormalCamera', '.bumpMap', '.normal'],
	'roughness': ['.TEX_roughness_map', '.refl_roughness', '.base_glossiness', '.primaryGlossiness',
	              '.specularRoughness', '.roughness', '.diffuseRoughness', '.cosinePower', '.eccentricity'],
	'metallic': ['.TEX_metallic_map', '.refl_metalness', '.ReflectionMask', '.metalness', '.metallic'],
	'specular': ['.refl_color', '.refl_reflectivity', '.SpecularTexture', '.specularColor', '.primarySpecular',
	             '.KsColor', '.miSpecularColor', '.reflection', '.reflectionColor', '.primaryReflectionColor',
	             '.reflectivity'],
	'emissive': ['.TEX_emissive_map', '.EmissiveTexture', '.illumColor', '.incandescence', '.emission',
	             '.emissionColor', '.emissiveColor'],
	'transparency': ['.OpacityMaskTexture', '.inputs[0].transparency', '.transparency', '.transparencyColor',
	                 '.miTransparency', '.opacity', '.opacityMap'],
	'occlusion': ['.TEX_ao_map', '.AmbientOcclusionTexture'],
}

# Default file name suffixes used by "Load Files From Folder" (comma separated list per channel)
DEFAULT_SUFFIXES = {
	'color': '_A', 'normal': '_N', 'specular': '_S', 'metallic': '_M',
	'roughness': '_R', 'emissive': '_E', 'transparency': '_O', 'occlusion': '_AO',
}

IMAGE_EXTENSIONS = ('jpg', 'jpeg', 'png', 'dds', 'tga', 'tif', 'tiff', 'exr', 'bmp', 'psd')

# attributes that hold the colour of a preset (used for the swatch colour)
PRESET_COLOR_ATTRS = ('.color', '.baseColor', '.diffuse_color', '.base_color', '.diffuseColor', '.outColor')


#----------------------------------------------------------------------------- presets

_SWATCH_HEADER = re.compile(r'^//\s*Material ID Swatches\s*$', re.I)
_PRESET_HEADER = re.compile(r'^//\s*Material Presets\s*$', re.I)
_ATTR_TOKEN = re.compile(r'^\.[A-Za-z_]')


def _to_float(token):
	try:
		return float(token)
	except ValueError:
		return None


def parse_preset_line(line):
	"""'Brick phong .color 0.6 0.2 0.15 .cosinePower 2' -> {'name','type','attrs':[(attr,[values])]} or None."""
	tokens = line.split()
	if len(tokens) < 2:
		return None
	entry = {'name': tokens[0], 'type': tokens[1], 'attrs': []}
	current = None
	for token in tokens[2:]:
		if _ATTR_TOKEN.match(token):
			current = (token, [])
			entry['attrs'].append(current)
		elif current is not None:
			value = _to_float(token)
			if value is not None:
				current[1].append(value)
	return entry


def parse_presets(text):
	"""Parse the content of mm_material_presets.txt -> (swatches, presets), each a list of entries."""
	swatches, presets = [], []
	section = None
	for raw in text.splitlines():
		line = raw.strip()
		if not line:
			continue
		if line.startswith('//'):
			if _SWATCH_HEADER.match(line):
				section = 'swatches'
			elif _PRESET_HEADER.match(line):
				section = 'presets'
			continue
		if section is None:
			continue
		entry = parse_preset_line(line)
		if entry:
			(swatches if section == 'swatches' else presets).append(entry)
	return swatches, presets


def preset_color(entry, default=(0.5, 0.5, 0.5)):
	"""RGB of a preset entry (first colour-like attribute with 3 values)."""
	for attr, values in entry['attrs']:
		if attr in PRESET_COLOR_ATTRS and len(values) >= 3:
			return (values[0], values[1], values[2])
	return default


#----------------------------------------------------------------------------- names

def sanitize_name(name):
	"""Replace every character Maya does not like by '_' (a leading digit gets an 'M_' prefix)."""
	name = re.sub(r'[^A-Za-z0-9_]', '_', name.strip())
	if name and name[0].isdigit():
		name = 'M_' + name
	return name


def is_valid_name(name):
	return bool(name) and name == sanitize_name(name)


def strip_sm_prefix(name):
	"""'SM_Crate' -> 'Crate'"""
	return re.sub(r'^sm_', '', name, flags=re.I)


def strip_lod_suffix(name):
	"""'Crate_LOD0' -> 'Crate'"""
	return re.sub(r'_lod\d*$', '', name, flags=re.I)


def unprefixed(name):
	return name[2:] if name.startswith('M_') else name


def parse_suffixes(text):
	"""'_A, _BaseColor' -> ['_A', '_BaseColor']"""
	return [s.strip() for s in (text or '').split(',') if s.strip()]


#----------------------------------------------------------------------------- component names

def compress_indices(indices):
	"""[0,1,2,5,7,8] -> [(0, 2), (5, 5), (7, 8)]"""
	ordered = sorted(set(indices))
	ranges = []
	for i in ordered:
		if ranges and i == ranges[-1][1] + 1:
			ranges[-1] = (ranges[-1][0], i)
		else:
			ranges.append((i, i))
	return ranges


def component_names(node, kind, indices):
	"""component_names('pCubeShape1', 'f', [0,1,2,5]) -> ['pCubeShape1.f[0:2]', 'pCubeShape1.f[5]']"""
	names = []
	for a, b in compress_indices(indices):
		names.append('%s.%s[%d]' % (node, kind, a) if a == b else '%s.%s[%d:%d]' % (node, kind, a, b))
	return names


#----------------------------------------------------------------------------- texture files

class TooManyFolders(Exception):
	pass


def walk_folders(root, max_folders=500, max_entries=20000):
	"""root + all its sub folders. Raises TooManyFolders when the tree is too big to search quickly."""
	folders = []
	entries = 0
	for dirpath, dirnames, filenames in os.walk(root):
		folders.append(dirpath.replace('\\', '/'))
		entries += len(dirnames) + len(filenames)
		if len(folders) > max_folders or entries > max_entries:
			raise TooManyFolders('%d folders / %d files' % (len(folders), entries))
	return sorted(folders)


def match_textures(base_name, folders, suffixes, match_name=True):
	"""Find the texture files of one material.

	suffixes : {channel: [suffix, ...]}
	Returns {channel: path}. A file belongs to the channel whose (longest) suffix its name ends with.
	With match_name the file name must also contain the material name."""
	base = base_name.lower()
	found = {}
	for folder in folders:
		try:
			names = sorted(os.listdir(folder))
		except OSError:
			continue
		for filename in names:
			stem, ext = os.path.splitext(filename)
			if ext.lstrip('.').lower() not in IMAGE_EXTENSIONS:
				continue
			full = os.path.join(folder, filename)
			if not os.path.isfile(full):
				continue
			low = stem.lower()
			if match_name and base and base not in low:
				continue
			best = None
			for channel, suffix_list in suffixes.items():
				for suffix in suffix_list:
					s = suffix.lower()
					if s and low.endswith(s) and (best is None or len(s) > best[1]):
						best = (channel, len(s))
			if best and best[0] not in found:
				found[best[0]] = full.replace('\\', '/')
	return found
