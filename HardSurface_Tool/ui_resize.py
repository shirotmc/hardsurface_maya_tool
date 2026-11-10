# -*- coding: utf-8 -*-
"""
Width scaling for the fixed-column layouts of HSTool.

Most layouts use rowColumnLayout / columnLayout with pixel widths (cw=[(1, 155), (2, 155)]),
which do not follow the window width. This module makes every column grow together:

1. record(cmds) wraps maya.cmds: when a rowColumnLayout / columnLayout is CREATED, its arguments
   (cw, nc, cs, adj) are remembered. Nothing is queried back from Maya.
2. install(window) listens to the window's Qt resize event (debounced).
3. apply_scale(window) measures the real width of the scroll area that holds the layout and gives each
   column  design_width * factor  (factor = available / sum of design widths), so 2 / 3 / 4 equal buttons
   share the extra width equally. The LAST column (or the one marked `adj`) is left adjustable, so it takes
   exactly what remains: the row always reaches the right edge, whatever the scrollbar / margin is.
   Single-column columnLayouts are made adjustable, so their buttons fill the width.

Buttons / fields are never touched, only the layouts holding them.
"""
import maya.cmds as cmds

MARGIN = 26          # fallback only (window border + scrollbar) when the scroll area cannot be measured
FRAME_PAD = 4        # frame border around the content, taken off the measured scroll width
MIN_SCALE = 0.9
MAX_SCALE = 6.0
DEBOUNCE_MS = 60

try:
	_STR = (str, unicode)  # noqa: F821  (Python 2)
except NameError:
	_STR = (str,)

_specs = {}      # layout full path -> spec
_filters = {}    # window name -> Qt event filter (kept alive here)
_last_width = {}


#----------------------------------------------------------------------------- argument parsing (pure)

def _norm_pairs(value):
	"""cw / cs argument -> {column: number}. Accepts [(1,155),(2,155)], (1,155) or a plain number."""
	if value is None:
		return {}
	if isinstance(value, (int, float)):
		return {1: int(value)}
	if isinstance(value, (tuple, list)):
		if len(value) == 2 and all(isinstance(x, (int, float)) for x in value):
			value = [value]
		out = {}
		for item in value:
			if isinstance(item, (tuple, list)) and len(item) == 2:
				out[int(item[0])] = int(item[1])
		return out
	return {}


def _kw(kwargs, *names):
	for n in names:
		if n in kwargs:
			return kwargs[n]
	return None


def make_spec(kind, kwargs):
	"""Build the spec of a layout from the keyword arguments it was created with (None = ignore)."""
	cw = _norm_pairs(_kw(kwargs, 'cw', 'columnWidth'))
	if not cw:
		return None
	adj = _kw(kwargs, 'adj', 'adjustableColumn')
	if kind == 'columnLayout':
		if adj:
			return None   # adjustable columnLayout already stretches by itself
		return {'kind': kind, 'cw': {1: cw[1] if 1 in cw else max(cw.values())}, 'nc': 1,
		        'adj': 0, 'spacing': 0}
	nc = int(_kw(kwargs, 'nc', 'numberOfColumns') or 1)
	adj = int(adj) if isinstance(adj, (int, float)) and not isinstance(adj, bool) else 0
	spacing = sum(_norm_pairs(_kw(kwargs, 'cs', 'columnSpacing')).values())
	return {'kind': kind, 'cw': cw, 'nc': nc, 'adj': adj, 'spacing': spacing}


def compute_widths(spec, avail):
	"""rowColumnLayout: (adjustable column, {column: width}) for `avail` pixels; None if cw is incomplete.

	The adjustable column is not listed: Maya gives it whatever is left, so rounding / margin errors end up
	there and the row always fills the layout exactly."""
	cols = spec['cw']
	nc = spec['nc']
	adj = spec['adj'] or nc          # no adjustable column given -> the last one absorbs the remainder
	if not all(c in cols for c in range(1, nc + 1)):
		return None
	total = float(sum(cols.values()))
	if total <= 0:
		return None
	g = (avail - spec['spacing']) / total
	g = min(max(g, MIN_SCALE), MAX_SCALE)
	return adj, dict((c, int(w * g)) for c, w in cols.items() if c != adj)


#----------------------------------------------------------------------------- recording proxy

def _recording(kind, func):
	def wrapper(*args, **kwargs):
		result = func(*args, **kwargs)
		if any(k in kwargs for k in ('q', 'query', 'e', 'edit')):
			return result
		if isinstance(result, _STR):
			spec = make_spec(kind, kwargs)
			if spec:
				_specs[result] = spec
		return result
	return wrapper


class _Recorder(object):
	"""Behaves exactly like maya.cmds, but remembers how layouts were created."""
	def __init__(self, real):
		self.__dict__['_real'] = real

	def __getattr__(self, name):
		attr = getattr(self.__dict__['_real'], name)
		if name in ('rowColumnLayout', 'columnLayout'):
			return _recording(name, attr)
		return attr


def record(real_cmds):
	"""Return a cmds-like object that records layout creation (use it instead of maya.cmds)."""
	if isinstance(real_cmds, _Recorder):
		return real_cmds
	return _Recorder(real_cmds)


def forget(window_name=None):
	"""Drop remembered layouts of one window (or of all windows)."""
	for path in list(_specs):
		if window_name is None or path.startswith(window_name + '|'):
			del _specs[path]
	if window_name is None:
		_last_width.clear()
	else:
		_last_width.pop(window_name, None)


#----------------------------------------------------------------------------- apply

def _qt():
	try:
		from PySide2 import QtWidgets
		from shiboken2 import wrapInstance
	except ImportError:
		from PySide6 import QtWidgets
		from shiboken6 import wrapInstance
	import maya.OpenMayaUI as omui
	return QtWidgets, wrapInstance, omui


def _scroll_of(path):
	"""Nearest scrollLayout above the layout (the area whose width the content must fill)."""
	parts = path.split('|')
	for i in range(len(parts) - 1, 0, -1):
		parent = '|'.join(parts[:i])
		try:
			if cmds.objectTypeUI(parent) == 'scrollLayout':
				return parent
		except Exception:
			pass
	return None


def _viewport_width(scroll_path):
	try:
		QtWidgets, wrap, omui = _qt()
		ptr = omui.MQtUtil.findControl(scroll_path)
		if not ptr:
			return None
		widget = wrap(int(ptr), QtWidgets.QWidget)
		viewport = widget.viewport() if hasattr(widget, 'viewport') else None
		w = (viewport or widget).width()
		return w if w > 250 else None     # hidden / not laid out yet
	except Exception:
		return None


def _is_nested(path):
	"""True if the layout sits inside a cell of another recorded rowColumnLayout (its space is a cell, not the page)."""
	parts = path.split('|')
	for i in range(len(parts) - 1, 0, -1):
		parent = _specs.get('|'.join(parts[:i]))
		if parent and parent['kind'] == 'rowColumnLayout':
			return True
	return False


def apply_scale(window_name, width=None):
	if not cmds.window(window_name, ex=True):
		return
	if width is None:
		width = cmds.window(window_name, q=True, w=True)
	_last_width[window_name] = width
	measured = {}
	stale = []
	for path, spec in list(_specs.items()):
		if not path.startswith(window_name + '|'):
			continue
		if 'nested' not in spec:
			spec['nested'] = _is_nested(path)
			spec['scroll'] = _scroll_of(path)
		if spec['nested']:
			continue          # keep the design widths of layouts living inside another layout's cell
		try:
			if spec['kind'] == 'columnLayout':
				cmds.columnLayout(path, e=True, adj=True)   # children fill the width
				continue
			scroll = spec['scroll']
			if scroll not in measured:
				measured[scroll] = _viewport_width(scroll) if scroll else None
			vw = measured[scroll]
			avail = (vw - FRAME_PAD) if vw else (width - MARGIN)
			result = compute_widths(spec, avail)
			if not result:
				continue
			adj, widths = result
			kwargs = {'adj': adj}
			if widths:
				kwargs['cw'] = sorted(widths.items())
			cmds.rowColumnLayout(path, e=True, **kwargs)
		except Exception:
			stale.append(path)   # layout no longer exists (tab detached, UI rebuilt...)
	for path in stale:
		_specs.pop(path, None)


def reset_window(window_name):
	_last_width.pop(window_name, None)


#----------------------------------------------------------------------------- Qt resize hook

def install(window_name):
	"""Call apply_scale() (debounced) whenever the window is resized. Returns False if Qt is unavailable."""
	try:
		try:
			from PySide2 import QtCore, QtWidgets
			from shiboken2 import wrapInstance
		except ImportError:
			from PySide6 import QtCore, QtWidgets
			from shiboken6 import wrapInstance
		import maya.OpenMayaUI as omui

		ptr = omui.MQtUtil.findControl(window_name)
		if not ptr:
			return False
		top = wrapInstance(int(ptr), QtWidgets.QWidget).window()

		old = _filters.pop(window_name, None)
		if old is not None:
			try:
				top.removeEventFilter(old)
			except Exception:
				pass

		class _ResizeFilter(QtCore.QObject):
			def __init__(self, parent):
				QtCore.QObject.__init__(self, parent)
				self._timer = QtCore.QTimer(self)
				self._timer.setSingleShot(True)
				self._timer.timeout.connect(self._fire)

			def eventFilter(self, obj, event):
				if event.type() == QtCore.QEvent.Type.Resize:
					self._timer.start(DEBOUNCE_MS)
				return False

			def _fire(self):
				try:
					apply_scale(window_name, top.width())
				except Exception:
					pass

		flt = _ResizeFilter(top)
		top.installEventFilter(flt)
		_filters[window_name] = flt
		return True
	except Exception as e:
		print('HSTool ui_resize: Qt resize hook failed: {0}'.format(e))
		return False
