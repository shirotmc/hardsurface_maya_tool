import maya.cmds as cmds
from functools import partial

FRAME_NAME = 'normal_value_copy_frame_layout'
FRAME_LABEL = 'Vertex Normal Table'
SOFT_CB = 'normal_value_contained_soft_cb'
OPT_SOFT = 'normal_value_contained_soft'

EPS = 0.000001
LIST_HEIGHT = 170

# Table look
ROW_H = 24
SWATCH_W = 26
ACTION_W = 58
AXIS_COLORS = ((0.8, 0.27, 0.2), (0.2, 0.8, 0.5), (0.2, 0.43, 0.8))  # X, Y, Z header colours
CELL_BG = (0.15, 0.15, 0.15)
ROW_BG = ((0.23, 0.23, 0.23), (0.27, 0.27, 0.27))
HEADER_BG = (0.12, 0.12, 0.12)
PASTE_BG = (0.8, 0.5, 0)

_ui = {'list': None, 'empty': None, 'count': None}
_shown_keys = []


#----------------------------------------------------------------------------- core (no UI)

def _clean(vec):
	# Tiny values become exactly 0 (same as the MEL tool)
	return tuple(0.0 if abs(c) < EPS else float(c) for c in vec)


def _key(vec):
	return tuple(round(c, 6) + 0.0 for c in vec)


def _triplets(flat):
	return [flat[i:i + 3] for i in range(0, len(flat) - 2, 3)]


def _to_vertex_faces(components):
	converted = cmds.polyListComponentConversion(components, tvf=True) or []
	if not converted:
		return []
	return cmds.filterExpand(converted, sm=70) or []


def _average_vertex_normal(vertex):
	# Port of getNormalOneVertex: average of all normals around one vertex, normalized
	values = _triplets(cmds.polyNormalPerVertex(vertex, q=True, xyz=True) or [])
	if not values:
		return (0.0, 0.0, 0.0)
	total = [sum(v[i] for v in values) for i in range(3)]
	length = sum(c * c for c in total) ** 0.5
	if length < 1e-12:
		return (0.0, 0.0, 0.0)
	return tuple(c / length for c in total)


def get_normal_values(per_vertex=False):
	"""Return the list of distinct normal values (x, y, z) of the current selection."""
	selection = cmds.ls(sl=True) or []
	if not selection:
		cmds.warning('Vertex Normal Table: select vertices, edges or faces first.')
		return []

	if per_vertex:
		converted = cmds.polyListComponentConversion(selection, tv=True) or []
		vertices = cmds.filterExpand(converted, sm=31) or [] if converted else []
		raw = [_average_vertex_normal(v) for v in vertices]
	else:
		vertex_faces = _to_vertex_faces(selection)
		flat = cmds.polyNormalPerVertex(vertex_faces, q=True, xyz=True) if vertex_faces else []
		raw = _triplets(flat or [])

	values = []
	seen = set()
	for vec in raw:
		vec = _clean(vec)
		k = _key(vec)
		if k not in seen:
			seen.add(k)
			values.append(vec)
	return values


def _is_contained_soft():
	if cmds.checkBox(SOFT_CB, q=True, ex=True):
		return bool(cmds.checkBox(SOFT_CB, q=True, v=True))
	return bool(cmds.optionVar(q=OPT_SOFT)) if cmds.optionVar(ex=OPT_SOFT) else True


def paste_normal(vec, *args):
	"""Write the normal value vec = (x, y, z) onto the current selection."""
	selection = cmds.ls(sl=True) or []
	if not selection:
		cmds.warning('Vertex Normal Table: select vertices, edges or faces to paste to.')
		return

	faces = cmds.filterExpand(selection, sm=34) or []
	edges = cmds.filterExpand(selection, sm=32) or []
	vertex_like = cmds.filterExpand(selection, sm=[31, 70]) or []
	if faces or edges or not vertex_like:
		target = _to_vertex_faces(selection)
	else:
		target = selection
	if not target:
		cmds.warning('Vertex Normal Table: nothing to paste to.')
		return

	cmds.undoInfo(openChunk=True)
	try:
		cmds.polyNormalPerVertex(target, xyz=(vec[0], vec[1], vec[2]))
		if faces and _is_contained_soft():
			inner = cmds.polyListComponentConversion(faces, te=True, internal=True) or []
			inner = (cmds.filterExpand(inner, sm=32) or []) if inner else []
			if inner:
				cmds.polySoftEdge(inner, a=180, ch=False)
	finally:
		cmds.undoInfo(closeChunk=True)


#----------------------------------------------------------------------------- UI
# Table: [ swatch | X | Y | Z | Paste ]. Every row is a formLayout, so the X/Y/Z cells share
# the free width in equal parts and the table follows the window width on its own.

def _save_soft_option(*args):
	cmds.optionVar(iv=[OPT_SOFT, int(cmds.checkBox(SOFT_CB, q=True, v=True))])


def _update_count():
	if _ui['count'] and cmds.text(_ui['count'], q=True, ex=True):
		n = len(_shown_keys)
		cmds.text(_ui['count'], e=True, l='{0} value{1}'.format(n, '' if n == 1 else 's'))


def _attach_row(row, swatch, inner, action, cells):
	# X | Y | Z each take a third of the inner form, with a 1px gap between cells
	cmds.formLayout(inner, e=True,
	                af=[(cells[0], 'top', 0), (cells[0], 'bottom', 0), (cells[0], 'left', 0),
	                    (cells[1], 'top', 0), (cells[1], 'bottom', 0),
	                    (cells[2], 'top', 0), (cells[2], 'bottom', 0), (cells[2], 'right', 0)],
	                ap=[(cells[0], 'right', 1, 33), (cells[1], 'left', 1, 33),
	                    (cells[1], 'right', 1, 67), (cells[2], 'left', 1, 67)])
	cmds.formLayout(row, e=True,
	                af=[(swatch, 'left', 3), (swatch, 'top', 2), (swatch, 'bottom', 2),
	                    (action, 'right', 3), (action, 'top', 2), (action, 'bottom', 2),
	                    (inner, 'top', 2), (inner, 'bottom', 2)],
	                ac=[(inner, 'left', 4, swatch), (inner, 'right', 4, action)])


def _add_header(parent):
	row = cmds.formLayout(p=parent, h=ROW_H, bgc=HEADER_BG)
	swatch = cmds.text(l='', w=SWATCH_W)
	inner = cmds.formLayout(nd=100)
	cells = []
	for label, color in zip(('X', 'Y', 'Z'), AXIS_COLORS):
		cells.append(cmds.text(l=label, align='center', fn='boldLabelFont', bgc=color,
		                       ann='{0} component of the normal'.format(label)))
	cmds.setParent('..')
	action = cmds.text(l='', w=ACTION_W, align='center', fn='smallBoldLabelFont')
	cmds.setParent('..')
	_attach_row(row, swatch, inner, action, cells)
	return row


def _add_row(vec):
	index = len(_shown_keys) - 1
	color = [(c + 1.0) * 0.5 for c in vec]   # same normal -> RGB mapping as the MEL tool
	tip = 'Normal ({0:.4f}, {1:.4f}, {2:.4f})'.format(*vec)
	row = cmds.formLayout(p=_ui['list'], h=ROW_H, bgc=ROW_BG[index % 2])
	swatch = cmds.button(l='', w=SWATCH_W, bgc=color, ann=tip + ' - colour')
	inner = cmds.formLayout(nd=100)
	cells = [cmds.text(l='{0:.4f}'.format(c), align='center', bgc=CELL_BG, ann=tip) for c in vec]
	cmds.setParent('..')
	action = cmds.button(l='Paste', w=ACTION_W, bgc=PASTE_BG, ann='Paste this normal to the selection',
	                     c=partial(paste_normal, vec))
	cmds.setParent('..')
	_attach_row(row, swatch, inner, action, cells)


def _show_empty_hint():
	_ui['empty'] = cmds.text(p=_ui['list'], l='Select vertices / edges / faces, then press Get',
	                         align='center', h=40, enable=False)


def _remove_empty_hint():
	if _ui['empty'] and cmds.text(_ui['empty'], q=True, ex=True):
		cmds.deleteUI(_ui['empty'])
	_ui['empty'] = None


def _clear_rows():
	list_layout = _ui['list']
	if list_layout and cmds.layout(list_layout, q=True, ex=True):
		for child in cmds.layout(list_layout, q=True, ca=True) or []:
			try:
				cmds.deleteUI(list_layout + '|' + child)
			except RuntimeError:
				pass
	del _shown_keys[:]
	_ui['empty'] = None


def clear_values(*args):
	_clear_rows()
	if _ui['list'] and cmds.layout(_ui['list'], q=True, ex=True):
		_show_empty_hint()
	_update_count()


def get_values(*args):
	"""Get button: add the distinct normals of the selection to the table."""
	new_values = [v for v in get_normal_values() if _key(v) not in _shown_keys]
	if not new_values:
		return
	_remove_empty_hint()
	for vec in new_values:
		_shown_keys.append(_key(vec))
		_add_row(vec)
	_update_count()


def build_ui(parent):
	"""Create the 'Vertex Normal Table' frame inside the given layout and return its name."""
	if not cmds.optionVar(ex=OPT_SOFT):
		cmds.optionVar(iv=[OPT_SOFT, 1])
	del _shown_keys[:]

	frame = cmds.frameLayout(FRAME_NAME, p=parent, l=FRAME_LABEL, collapsable=False,
	                         ann='Copy distinct normal values and paste them onto other components')
	column = cmds.columnLayout(p=frame, adj=True, rs=4)

	# Options row: checkbox on the left, value counter on the right
	options = cmds.formLayout(p=column, h=24)
	soft_cb = cmds.checkBox(SOFT_CB, l='Contained Edge Soft', v=bool(cmds.optionVar(q=OPT_SOFT)),
	                        ann='When faces are selected, also set the edges inside them soft (angle 180)',
	                        cc=_save_soft_option)
	count = cmds.text('normal_value_count_txt', l='0 values', align='right', enable=False)
	cmds.formLayout(options, e=True,
	                af=[(soft_cb, 'left', 3), (soft_cb, 'top', 2), (count, 'right', 6), (count, 'top', 4)])
	_ui['count'] = count

	# Get / Clear
	buttons = cmds.formLayout(p=column, h=30)
	get_btn = cmds.button('normal_value_get_btn', l='Get', bgc=(0.6, 0.6, 1),
	                      ann='Add the distinct normals of the selection to the table', c=get_values)
	clear_btn = cmds.button('normal_value_clear_btn', l='Clear', ann='Empty the table', c=clear_values)
	cmds.formLayout(buttons, e=True,
	                af=[(get_btn, 'top', 0), (get_btn, 'left', 3), (get_btn, 'bottom', 0),
	                    (clear_btn, 'top', 0), (clear_btn, 'right', 3), (clear_btn, 'bottom', 0)],
	                ap=[(get_btn, 'right', 2, 50), (clear_btn, 'left', 2, 50)])

	# Table: fixed header + scrolling rows
	_add_header(column)
	cmds.scrollLayout(p=column, cr=True, hst=0, h=LIST_HEIGHT, bgc=(0.18, 0.18, 0.18))
	_ui['list'] = cmds.columnLayout('normal_value_list_layout', adj=True, rs=1)
	_show_empty_hint()
	cmds.setParent(frame)
	return frame
