import os
import json
import subprocess
import time
import maya.cmds as cmds
import maya.mel as mel
from functools import partial

try:
	dict.iteritems
except AttributeError:
	# Python 3
	from importlib import reload
	def itervalues(d):
		return iter(d.values())
	def iteritems(d):
		return iter(d.items())
	def iterkeys(d):
		return iter(d)

else:
	# Python 2
	def itervalues(d):
		return d.itervalues()
	def iteritems(d):
		return d.iteritems()
	def iterkeys(d):
		return d.iterkeys()

# HSTool root folder (self-locating: works wherever HSTool is installed)
LOCAL_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace("\\", "/")
LOCAL_PREF_PATH = os.path.expanduser("~").replace("\\", "/") + "/maya/" + str(cmds.about(version=True)) + "/prefs"
if int(cmds.about(version=True)) >= 2023:
	LOCAL_PREF_PATH = os.path.expanduser("~").replace("\\", "/") + "/Documents/maya/" + str(cmds.about(version=True)) + "/prefs"

# DATABASE PATH
DATABASE_PATH = LOCAL_PATH + "/HardSurface_Tool/Database"

# SETTING PATH
LOCAL_SETTING_PATH = DATABASE_PATH + "/Setting/HardSurfaceTool_Setting.json"

# DOCUMENT PATH
DOCUMENT_PATH = DATABASE_PATH + "/Document/HardSurfaceTool_Document.html"

# HOTKEY PATH
LOCAL_RUNTIME_COMMAND_PATH = LOCAL_PREF_PATH + "/userRunTimeCommands.mel" 
ROOT_RUNTIME_COMMAND_PATH = DATABASE_PATH + "/Hotkey/userRunTimeCommands.mel"
LOCAL_NAMED_COMMAND_PATH = LOCAL_PREF_PATH + "/userNamedCommands.mel" 
ROOT_NAMED_COMMAND_PATH = DATABASE_PATH + "/Hotkey/userNamedCommands.mel"

# LIBRARY PATH
LIBRARY_PATH = DATABASE_PATH + "/Library"

# WINDOW NAME
WINDOW_NAME = "hardsurface_tool_window"
# TOOL VERSION
from Updater import updater
TOOL_VERSION = updater.get_local_version()
# WINDOW TITLE
WINDOW_TITLE = "Non-Vehicle Tool " + TOOL_VERSION +  " - Maya " + cmds.about(version=True)
# WINDOW SIZE
WINDOW_HEIGHT = 860
WINDOW_WIDTH = 325
# Resizable UI (set False to go back to the old fixed-size window)
RESIZABLE_UI = True
MIN_WINDOW_WIDTH = 325
MIN_WINDOW_HEIGHT = 300
# Check tab rows: [Check button][gap][Fix button]
CHECK_ROW_HEIGHT = 30
CHECK_FIX_WIDTH = 60
CHECK_FIX_GAP = 5
CHECK_ROW_RIGHT_MARGIN = 14   # space between the Fix buttons and the scrollbar (kept at every window width)

# TEMPLATE UI
TEMPLATE_NAME = "HSTemplate"

# TAB LIST
DEFAULT_TAB_LIST = [1,2,3,4,5,6]

# Optional: Custom order for Check tab frames (by frame title/docstring from CheckTool)
# Any frames not listed here will be appended alphabetically.
CHECK_FRAME_ORDER = [
	'Check Scene',
	'Check Modeling',
	'Check UV',
	'Check Shader',
	'Clean UP',
]

from HardSurface_Tool import ui_resize
reload(ui_resize)
cmds = ui_resize.record(cmds)   # remembers rowColumnLayout/columnLayout widths so columns can be scaled

from Check_Tools import CheckTool
reload(CheckTool)

from Model_Tools import ModelTool
reload(ModelTool)

from Material_Tools import MaterialTool
reload(MaterialTool)

from Mirror_Tools import MirrorTool
reload(MirrorTool)

from UV_Tools import UVToolsMain
reload(UVToolsMain)

from Normal_Tools import NormalTools_Main
reload(NormalTools_Main)

from BakeSet_Tools import BakeSetTool
reload(BakeSetTool)

#region SAVE PARAMETERS
if not cmds.optionVar(ex='straightenLine_even'):
	cmds.optionVar(iv=['straightenLine_even', 0])
if not cmds.optionVar(ex='averageLine_even'):
	cmds.optionVar(iv=['averageLine_even', 0])
if not cmds.optionVar(ex='averageLine_keepshape'):
	cmds.optionVar(iv=['averageLine_keepshape', 1])
if not cmds.optionVar(ex='averageLine_smooth'):
	cmds.optionVar(iv=['averageLine_smooth', 0])
if not cmds.optionVar(ex='averageLine_align'):
	cmds.optionVar(iv=['averageLine_align', 4])
if not cmds.optionVar(ex='averageLine_step'):
	cmds.optionVar(iv=['averageLine_step', 1])
if not cmds.optionVar(ex='connect_div'):
	cmds.optionVar(iv=['connect_div', 1])
if not cmds.optionVar(ex='circle_clear_btn'):
	cmds.optionVar(iv=['circle_clear_btn', False])
if not cmds.optionVar(ex='mirror_uv'):
	cmds.optionVar(iv=['mirror_uv', 0])
if not cmds.optionVar(q='mirror_space'):
	cmds.optionVar(iv=['mirror_space', 1])
if not cmds.optionVar(q='merge_tolerance'):
	cmds.optionVar(fv=['merge_tolerance', 0.1])
if not cmds.optionVar(q='revolve_instance'):
	cmds.optionVar(iv=['revolve_instance', 0])
if not cmds.optionVar(q='revolve_count'):
	cmds.optionVar(iv=['revolve_count', 8])
if not cmds.optionVar(ex='export_bakeset_mode'):
	cmds.optionVar(iv=['export_bakeset_mode', 2])
if not cmds.optionVar(q='dot_loop_value'):
	cmds.optionVar(iv=['dot_loop_value', 1])
if not cmds.optionVar(q='dot_ring_value'):
	cmds.optionVar(iv=['dot_ring_value', 1])
if not cmds.optionVar(q='bakeset_lock_normal'):
	cmds.optionVar(iv=['bakeset_lock_normal', 1])
if not cmds.optionVar(ex='export_normal_mode_rbg'):
	cmds.optionVar(iv=['export_normal_mode_rbg', 1])


# Tab Layout
if not cmds.optionVar(ex='select_tab'):
	cmds.optionVar(iv=['select_tab', 2])

# Frame Layout
if not cmds.optionVar(ex='scene_cl'):
	cmds.optionVar(iv=['scene_cl', True])
if not cmds.optionVar(ex='modify_object_cl'):
	cmds.optionVar(iv=['modify_object_cl', True])
if not cmds.optionVar(ex='circle_cl'):
	cmds.optionVar(iv=['circle_cl', True])
if not cmds.optionVar(ex='select_component_cl'):
	cmds.optionVar(iv=['select_component_cl', True])
if not cmds.optionVar(ex='instance_object_cl'):
	cmds.optionVar(iv=['instance_object_cl', True])
if not cmds.optionVar(ex='fast_function_cl'):
	cmds.optionVar(iv=['fast_function_cl', True])
if not cmds.optionVar(ex='fix_cl'):
	cmds.optionVar(iv=['fix_cl', True])
if not cmds.optionVar(ex='maya_blender_cl'):
	cmds.optionVar(iv=['maya_blender_cl', True])
if not cmds.optionVar(ex='import_export_cl'):
	cmds.optionVar(iv=['import_export_cl', True])
if not cmds.optionVar(ex='support_tool_cl'):
	cmds.optionVar(iv=['support_tool_cl', True])

#endregion

def GUI():

	# Online update check (background thread, never blocks the UI)
	updater.check_on_startup(TOOL_VERSION)

	global tab_list
	tab_list = DEFAULT_TAB_LIST

	# Clear old UI
	clear_old_ui()

	# Get setting json file
	if not os.path.exists(LOCAL_SETTING_PATH):
		create_hs_tool_setting_file(LOCAL_SETTING_PATH)
	data = read_data_from_json(LOCAL_SETTING_PATH)
	frame_bgc = data['ui']['frame_color']
	button_bgc = data['ui']['button_color']

	# Main Window
	main_window = cmds.window(WINDOW_NAME, title=WINDOW_TITLE, menuBar=True, rtf=(not RESIZABLE_UI), mnb=False, mxb=False, s=RESIZABLE_UI, cc=save_window_size)

	# Create uiTemplate
	cmds.uiTemplate(TEMPLATE_NAME)
	cmds.frameLayout(defineTemplate=TEMPLATE_NAME, bgc=frame_bgc)
	cmds.button(defineTemplate=TEMPLATE_NAME, bgc=button_bgc)

	# Apply UI Template
	cmds.setUITemplate(TEMPLATE_NAME, pushTemplate=True)

	# Menu
	cmds.menu(l='Update', tearOff=False)
	cmds.menuItem(l='Update Tool', c=update_tool_for_maya)
	cmds.menuItem(l='Check For Updates', c=lambda *a: updater.check_for_updates_ui(TOOL_VERSION, silent=False))
	cmds.menu(l='UI', tearOff=False)
	cmds.menuItem(l='Frame Color', c=change_frame_color)
	cmds.menuItem(l='Button Color', c=change_button_color)
	cmds.menuItem(l='Reset Color', c=reset_tool_color)
	cmds.menu(l='Hotkey', tearOff=False)
	cmds.menuItem(l='Get Hotkey Command', c=change_user_command_file)
	cmds.menuItem(l='Open Hotkey Editor', c=open_hotkey_editor)
	cmds.menu(l='Help', tearOff=False)
	cmds.menuItem(l='Document', c=open_hs_tool_document)
	cmds.menuItem(l='About', c=show_contact_information)

	# Main Layout
	button_form = cmds.formLayout('button_form')
	main_tab = cmds.tabLayout('main_tablayout', parent = button_form, cr=True)
	cmds.formLayout(button_form, e=True, af=[(main_tab, 'top', 0), (main_tab, 'left', 0), (main_tab, 'right', 0), (main_tab, 'bottom', 0)])
	
	check_layout = create_tab_container('Check', main_tab)
	model_layout = create_tab_container('Model', main_tab)
	mirror_layout = create_tab_container('Mirror', main_tab)
	normal_layout = create_tab_container('Normal', main_tab)
	uv_layout = create_tab_container('UV', main_tab)
	bake_layout = create_tab_container('Bake', main_tab)

	cmds.tabLayout('main_tablayout', e=True, sti = cmds.optionVar(q='select_tab'), sc='cmds.optionVar(iv=[\'select_tab\', cmds.tabLayout(\'main_tablayout\', q=True, sti=True)])', dcc=detach_tab_to_window)

	create_check_tab(check_layout)
	create_model_tab(model_layout)
	create_mirror_tab(mirror_layout)
	create_normal_tab(normal_layout)
	create_uv_tab(uv_layout)
	create_bake_tab(bake_layout)

	# Resize
	saved_w, saved_h = get_saved_window_size()
	cmds.window(main_window, e=True, w=saved_w, h=saved_h)
	cmds.window(main_window, e=True, s=RESIZABLE_UI)
	# Show
	cmds.showWindow(main_window)
	set_window_min_size(main_window)
	enable_width_scaling(main_window)
	cmds.scriptJob(e=['SceneOpened', GUI], parent=main_window)

def create_check_tab(check_layout):
	#region Check Tab
	check_function = CheckTool.getAllCheckFunction(CheckTool)
	fix_function = CheckTool.getAllFixFunction(CheckTool)
	opened_time = time.strftime('%Y-%m-%d %H:%M:%S')
	global check_button_names
	check_button_names = [k for k, v in iteritems(check_function) if v[0] is not None]
	all_check_functions = [v[1] for k, v in iteritems(check_function) if v[0] is not None]

	running_time_frame = cmds.frameLayout('running_time_frame_layout', l='Running Time', p=check_layout, cll=False)
	running_time_content = cmds.columnLayout('running_time_content', p=running_time_frame, adj=True, rs=6)
	running_time_layout = cmds.rowColumnLayout('running_time_layout', p=running_time_content, nc=2, cw=[(1, 90), (2, 210)], cs=[(2, 5)])
	cmds.text(l='Opened at:', p=running_time_layout, align='right', h=30, fn='boldLabelFont')
	cmds.textField('running_time_textfield', p=running_time_layout, tx=opened_time, ed=False, h=30)
	cmds.textField('running_time_textfield', e=True, bgc=[0.8, 0.5, 0])
	cmds.text(l='Checked at:', p=running_time_layout, align='right', h=30, fn='boldLabelFont')
	cmds.textField('checked_time_textfield', p=running_time_layout, tx='Pending', ed=False, h=30, bgc=[0.2, 0.2, 0.2])
	cmds.separator(p=running_time_content, st='in', h=6)
	cmds.button('check_all_button', p=running_time_content, l='Check All', h=36, bgc = (0.2, 0.8, 0.5), c=partial(execute_check_and_update_time, all_check_functions))
	cmds.separator(p=running_time_content, st='in', h=6)

	# Collect frame titles from function docstrings, preserving discovery order
	_frame_list = [v[0] for k, v in iteritems(check_function) if v[0] is not None]
	_seen = set()
	_unique_frames = []
	for f in _frame_list:
		if f not in _seen:
			_seen.add(f)
			_unique_frames.append(f)

	# Apply custom ordering, then append any remaining frames alphabetically for stability
	_order_pref = CHECK_FRAME_ORDER if 'CHECK_FRAME_ORDER' in globals() else []
	_pref_frames = [f for f in _unique_frames if f in _order_pref]
	# Ensure order matches preference list exactly
	_pref_frames_sorted = []
	for f in _order_pref:
		if f in _pref_frames:
			_pref_frames_sorted.append(f)
	_rest_frames = sorted([f for f in _unique_frames if f not in _order_pref])
	all_frame = _pref_frames_sorted + _rest_frames
	checking_scroll = cmds.scrollLayout('checking_scroll_layout', p=check_layout, cr=True, hst=0)
	cmds.formLayout(check_layout, e=True, af=[(running_time_frame, 'top', 0), (running_time_frame, 'left', 0), (running_time_frame, 'right', 0), (checking_scroll, 'left', 0), (checking_scroll, 'right', 0), (checking_scroll, 'bottom', 0)], ac=[(checking_scroll, 'top', 0, running_time_frame)])
	checking_main_frame = cmds.formLayout('checking_main_frame', p=checking_scroll)
	checking_main_layout = cmds.columnLayout('checking_main_layout', p=checking_main_frame, adj=True, rs=5)
	cmds.formLayout(checking_main_frame, e=True, af=[(checking_main_layout, 'left', 5), (checking_main_layout, 'right', 5), (checking_main_layout, 'top', 5), (checking_main_layout, 'bottom', 5)])

	for frame in all_frame:
		frame_layout = cmds.frameLayout(frame, l=frame, p=checking_main_layout, cll=True)
		col_frame = cmds.columnLayout('column_' + frame, p=frame_layout, adj=True, rs=5)
		# Button FormLayout
		main_button = cmds.formLayout('main_button', p=col_frame)
		button_layout_position = 0
		for k,v in iteritems(check_function):
			if v[0] != None and v[0] == frame:
				# One row = formLayout: [ Check button (fills) ][gap][ Fix button (fixed width) ]
				# Fixed widths are not used for the Check button, so the row fits any window width
				# and the Fix button always keeps its right margin to the scrollbar.
				button_layout = cmds.formLayout(k.replace("Check", "") + "_layout", p=main_button, h=CHECK_ROW_HEIGHT)
				
				# Set button_layout
				cmds.formLayout(main_button, e=True, af=[(button_layout, 'left', 5), (button_layout, 'right', CHECK_ROW_RIGHT_MARGIN), (button_layout, 'top', button_layout_position + 5)])
				button_layout_position += CHECK_ROW_HEIGHT
				
				# Check & Fix Button
				check_name = k
				fix_name = k.replace("Check", "Fix")

				# Check Button
				check_button = cmds.button(check_name, l=CheckTool.camelToSpaces(check_name).replace("Check", ""), h=30, p=button_layout, c=partial(execute_check_and_update_time, [v[1]]), bgc=[0.2,0.2,0.2])
				cmds.formLayout(button_layout, e=True, af=[(check_button, 'left', 0), (check_button, 'top', 0), (check_button, 'bottom', 0)])

				# Fix Button (the column stays reserved even when a check has no Fix, so all rows line up)
				fix_button = None
				for fk, fv in iteritems(fix_function):
					if fk == fix_name:
						fix_button = cmds.button(fix_name, l="Fix", p=button_layout, w=CHECK_FIX_WIDTH, h=30, c=fv[1], bgc=[0.2,0.2,0.2])
						break
				if fix_button:
					cmds.formLayout(button_layout, e=True, af=[(fix_button, 'right', 0), (fix_button, 'top', 0), (fix_button, 'bottom', 0)], ac=[(check_button, 'right', CHECK_FIX_GAP, fix_button)])
				else:
					cmds.formLayout(button_layout, e=True, af=[(check_button, 'right', CHECK_FIX_WIDTH + CHECK_FIX_GAP)])
	#endregion

def create_model_tab(model_layout):
	model_scroll = cmds.scrollLayout('model_scroll',p=model_layout, cr = True, hst=0)
	cmds.formLayout(model_layout, e=True, af=[(model_scroll, 'top', 0), (model_scroll, 'left', 0), (model_scroll, 'right', 0), (model_scroll, 'bottom', 0)])
	main_model_layout = cmds.columnLayout('frame_column_layout', p=model_scroll, adj=True)

	#region Circle
	cmds.frameLayout('circle_frame_layout', p = main_model_layout, l = 'Circle', collapsable = True, ann = 'Circle', cl=cmds.optionVar(q='circle_cl'), w=300, cc=lambda *args: get_current_frame_status('circle_frame_layout', 'circle_cl'), ec=lambda *args: get_current_frame_status('circle_frame_layout', 'circle_cl'))
	
	cmds.rowColumnLayout(nc=3, cw=[(1, 120), (2, 90), (3, 80)], adj=3, cs=[(2,5), (3,5)])
	cmds.checkBox('circle_diameter_cb', l = 'Diameter Input', ofc='cmds.floatField(\'circle_diameter_fl\', e=True, en=False)', onc='cmds.floatField(\'circle_diameter_fl\', e=True, en=True)')
	cmds.floatField('circle_diameter_fl', v=1.0, en=False)
	cmds.button(l = 'Get', c=make_tracked_callback(ModelTool.get_circle_diameter_input, 'Get Circle Diameter', 5.0))
	cmds.setParent('..')

	cmds.rowColumnLayout(nc=3, cw=[(1, 120), (2, 90), (3, 80)], adj=3, cs=[(2,5), (3,5)])
	cmds.checkBox('circle_angle_cb', l = 'Angle Input', ofc='cmds.floatField(\'circle_angle_fl\', e=True, en=False)', onc='cmds.floatField(\'circle_angle_fl\', e=True, en=True)')
	cmds.floatField('circle_angle_fl', v=180.0, en=False)
	cmds.button(l = 'Get', c=make_tracked_callback(ModelTool.get_circle_angle_input, 'Get Circle Angle', 5.0))
	cmds.setParent('..')

	cmds.rowColumnLayout(nc=3, cw=[(1, 120), (2, 70), (3, 100)], adj=3, cs=[(2,5), (3,5)])
	cmds.textField('circle_tf', ed=False, tx='')
	cmds.button('circle_clear_btn', l = 'Clear', en=cmds.optionVar(q='circle_clear_btn'), c= make_tracked_callback(ModelTool.get_circle_priority_vertices, 'Circle Clear', 5.0, 0))
	cmds.button(l = 'Get Priority', c= make_tracked_callback(ModelTool.get_circle_priority_vertices, 'Circle Get Priority', 5.0, 1))
	cmds.setParent('..')

	cmds.rowColumnLayout(nc = 2, cw = [(1, 190), (2,100)], adj = 2, cs = [(2,5), (3,5)])
	cmds.button(l = 'Alignment', bgc = (0.2, 0.8, 0.5), h=50, c=make_tracked_callback(ModelTool.align_circle_vertices, 'Circle Alignment', 5.0))
	cmds.columnLayout(columnAttach=('both', 0), rs=5, adj=True)
	cmds.button(l = 'Contiguous', c=make_tracked_callback(ModelTool.select_contiguous_edges, 'Select Contiguous Edges', 5.0))
	cmds.button(l = 'Ring', c=make_tracked_callback(ModelTool.select_edge_ring, 'Select Edge Ring', 5.0))
	cmds.setParent('..')

	cmds.setParent('..')
	#endregion

	#region Select
	cmds.frameLayout('select_component_frame_layout', p = main_model_layout, l = 'Select', collapsable = True, ann = 'Select Component', cl=cmds.optionVar(q='select_component_cl'), w=300, cc=lambda *args: get_current_frame_status('select_component_frame_layout', 'select_component_cl'), ec=lambda *args: get_current_frame_status('select_component_frame_layout', 'select_component_cl'))
	cmds.rowColumnLayout(nc=4, cw=[(1, 35), (2, 110), (3, 35), (4, 110)], adj=4, cs=[(2,5), (3,5), (4,5)])
	cmds.intField('dot_loop_if', v=cmds.optionVar(q='dot_loop_value'), cc='cmds.optionVar(iv=[\'dot_loop_value\', cmds.intField(\'dot_loop_if\', q=True, v=True)])')
	cmds.button(l='Dot Loop', h = 25, c = make_tracked_callback(ModelTool.select_dot_loop, 'Dot Loop', 5.0))
	cmds.intField('dot_ring_if', v=cmds.optionVar(q='dot_ring_value'), cc='cmds.optionVar(iv=[\'dot_ring_value\', cmds.intField(\'dot_ring_if\', q=True, v=True)])')
	cmds.button(l='Dot Ring', h = 25, c = make_tracked_callback(ModelTool.select_dot_ring, 'Dot Ring', 5.0))
	cmds.setParent('..')

	cmds.separator(st='in')

	cmds.rowColumnLayout(nc=2, cw=[(1, 230), (2,70)], adj=2)
	cmds.intSliderGrp('angle_selection_isg', label='Co-planar Angle:', field=True, cw3 = [90,50,90], adj = 3, minValue=0, maxValue=180, fieldMinValue=0, fieldMaxValue=180, value=5, cc=ModelTool.update_selection_by_normal_angle)
	cmds.button('angle_selection_btn', l='Select', c=make_tracked_callback(ModelTool.grow_selection_by_normal_angle, 'Select By Angle', 5.0))
	cmds.setParent('..')

	cmds.separator(st='in')

	cmds.rowColumnLayout(nc=2, cw=[(1, 150), (2, 150)], adj=2, cs=[(2,5)])
	cmds.button(l='Select Similar Object', h = 25, ann='Select Object To Find Similar Objects', c = make_tracked_callback(ModelTool.select_similar, 'Select Similar Object', 5.0))
	cmds.button(l='Selection Set', h = 25, ann='Save Selection And Re-Selection', c = make_tracked_callback(ModelTool.open_selection_set_tool, 'Selection Set Tool', 5.0, WINDOW_NAME))
	cmds.setParent('..')

	cmds.setParent('..')
	#endregion

	#region Modify Object
	cmds.frameLayout('modify_object_frame_layout', p = main_model_layout, l = 'Modify Object', collapsable = True, ann = 'Modify Object', cl=cmds.optionVar(q='modify_object_cl'), w=300, cc=lambda *args: get_current_frame_status('modify_object_frame_layout', 'modify_object_cl'), ec=lambda *args: get_current_frame_status('modify_object_frame_layout', 'modify_object_cl'))

	cmds.rowColumnLayout(nc=4, cw=[(1, 75), (2, 75), (3, 75), (4, 75)], adj=4)
	cmds.iconTextButton("combine_button", style = "iconAndTextVertical", image1 = LOCAL_PATH + "/Model_Tools/Icons/combine.png", l="Combine", ann = "Combine", c=make_tracked_callback(ModelTool.combine_object, 'Combine Objects', 5.0))
	cmds.iconTextButton("detach_button", style = "iconAndTextVertical", image1 = LOCAL_PATH + "/Model_Tools/Icons/detach.png", l="Detach", ann = "Detach", c=make_tracked_callback(ModelTool.detach_object, 'Detach Objects', 5.0))
	cmds.iconTextButton("clone_button", style = "iconAndTextVertical", image1 = LOCAL_PATH + "/Model_Tools/Icons/clone.png", l="Clone", ann = "Clone", c=make_tracked_callback(ModelTool.clone_object, 'Clone Objects', 5.0))
	cmds.iconTextButton("detach_by_material_button", style = "iconAndTextVertical", image1 = LOCAL_PATH + "/Model_Tools/Icons/detach_by_material.png", l="Detach By Mat", ann = "Detach By Material", c=make_tracked_callback(ModelTool.detach_by_material, 'Detach By Material', 5.0))
	cmds.setParent('..')

	cmds.separator(st='in')

	cmds.rowColumnLayout(nc=4, cw=[(1, 75), (2, 75), (3, 75), (4, 75)], adj=4)
	cmds.iconTextButton("CP_button", style = "iconAndTextVertical", image1 = LOCAL_PATH + "/Model_Tools/Icons/center_pivot.png", l="Center Pivot", ann = "Center Pivot", c = make_tracked_callback(ModelTool.center_pivot, 'Center Pivot', 5.0))
	cmds.iconTextButton("RT_button", style = "iconAndTextVertical", image1 = LOCAL_PATH + "/Model_Tools/Icons/reset_pivot.png", l="Reset Pivot", ann = "Reset Transforms", c = make_tracked_callback(ModelTool.reset_transforms, 'Reset Transforms', 5.0))
	cmds.iconTextButton("set_pivot_button", style = "iconAndTextVertical", image1 = LOCAL_PATH + "/Model_Tools/Icons/set_pivot.png", l="Set Pivot", ann = "Set Pivot Position", c = make_tracked_callback(ModelTool.set_pivot, 'Set Pivot', 5.0))
	cmds.iconTextButton("maxmin_pivot_button", style = "iconAndTextVertical", image1 = LOCAL_PATH + "/Model_Tools/Icons/pivot.png", l="Object Pivot", ann = "Max/Min X/Y/Z Pivot", c = make_tracked_callback(ModelTool.show_set_maxmin_pivot_window, 'Object Pivot', 5.0))
	cmds.setParent('..')

	cmds.setParent('..')
	#endregion   

	#region Scene
	cmds.frameLayout('scene_frame_layout', p = main_model_layout, l = 'Scene', collapsable = True, ann = 'Clean Scene', cl=cmds.optionVar(q='scene_cl'), w=300, cc=lambda *args: get_current_frame_status('scene_frame_layout', 'scene_cl'), ec=lambda *args: get_current_frame_status('scene_frame_layout', 'scene_cl'))
	
	cmds.rowColumnLayout(nc=3, cw=[(1, 100), (2, 100), (3, 100)], adj=3)
	cmds.iconTextButton("unhide_all_button", style = "iconAndTextVertical", image1 = LOCAL_PATH + "/Model_Tools/Icons/unhide_all.png", l="Unhide All", ann = "Y or Z", c = make_tracked_callback(ModelTool.unhide_all, 'Unhide All', 5.0))
	cmds.iconTextButton("FT_button", style = "iconAndTextVertical", image1 = LOCAL_PATH + "/Model_Tools/Icons/FT.png", l="Freeze Transforms", ann = "Freeze Transform", c = make_tracked_callback(ModelTool.freeze_transforms, 'Freeze Transforms', 5.0))
	cmds.iconTextButton("YorZ_button", style = "iconAndTextVertical", image1 = LOCAL_PATH + "/Model_Tools/Icons/YorZ.png", l="Y/Z", ann = "Y or Z", c = make_tracked_callback(ModelTool.changeYZ, 'Y or Z', 5.0))
	cmds.setParent('..')
	
	cmds.rowColumnLayout(nc=3, cw=[(1, 100), (2, 100), (3, 100)], adj=3)
	cmds.iconTextButton("fcc_button", style = "iconAndTextVertical", image1 = LOCAL_PATH + "/Model_Tools/Icons/FCC.png", l="FCC", ann = "Force Clean Combine", c = make_tracked_callback(ModelTool.FCC, 'Force Clean Combine', 5.0))
	cmds.iconTextButton("delete_history_button", style = "iconAndTextVertical", image1 = LOCAL_PATH + "/Model_Tools/Icons/history.png", l="History", ann = "Delete History", c = make_tracked_callback(ModelTool.delete_history, 'Delete History', 5.0))
	cmds.iconTextButton("toggle_pink_color_button", style = "iconAndTextVertical", image1 = LOCAL_PATH + "/Model_Tools/Icons/silhouette.png", l="Silhouette", ann = "Toggle pink color", c = make_tracked_callback(ModelTool.toggle_pink_color, 'Toggle Silhouette', 5.0))
	cmds.setParent('..')

	cmds.setParent('..')
	#endregion

	#region Instance
	cmds.frameLayout('instance_object_frame_layout', p = main_model_layout, l = 'Instance', collapsable = True, ann = 'Instance', cl=cmds.optionVar(q='instance_object_cl'), w=300, cc=lambda *args: get_current_frame_status('instance_object_frame_layout', 'instance_object_cl'), ec=lambda *args: get_current_frame_status('instance_object_frame_layout', 'instance_object_cl'))
	cmds.rowColumnLayout(nc=2, cw=[(1, 150), (2, 150)], adj=2)
	cmds.iconTextButton("set_instance_button", style = "iconAndTextVertical", image1 = LOCAL_PATH + "/Model_Tools/Icons/set_instance.png", l="Set Instance", ann = "Set Instance", c = make_tracked_callback(ModelTool.instance_objects, 'Set Instance', 5.0))
	cmds.iconTextButton("uninstance_button", style = "iconAndTextVertical", image1 = LOCAL_PATH + "/Model_Tools/Icons/uninstance.png", l="Un-Instance", ann = "Un-Instance", c = make_tracked_callback(ModelTool.uninstance_objects, 'Un-Instance', 5.0))
	cmds.setParent('..')
	cmds.setParent('..')
	#endregion

	#region Support Tool
	cmds.frameLayout('support_tool_frame_layout', p = main_model_layout, l = 'Speed Tool', collapsable = True, ann = 'Speed Tool', cl=cmds.optionVar(q='support_tool_cl'), w=300, cc=lambda *args: get_current_frame_status('support_tool_frame_layout', 'support_tool_cl'), ec=lambda *args: get_current_frame_status('support_tool_frame_layout', 'support_tool_cl'))

	cmds.rowColumnLayout(nc=4, cw=[(1, 75), (2, 75), (3, 75), (4, 75)], adj=4)
	cmds.iconTextButton("edge_length_tool_button", style = "iconAndTextVertical", image1 = LOCAL_PATH + "/Model_Tools/Icons/edge_length.png", l="Edge Length", ann = "Open Edge Length Tool", c = make_tracked_callback(ModelTool.open_edge_length_tool, "Edge Length Tool", 5.0, WINDOW_NAME))
	cmds.iconTextButton("straighten_line_tool_button", style = "iconAndTextVertical", image1 = LOCAL_PATH + "/Model_Tools/Icons/straighten_line.png", l="Straighten", ann = "Open Straighten Line Tool", c = make_tracked_callback(ModelTool.open_straighten_line_tool, "Straighten Line Tool", 5.0, WINDOW_NAME))
	cmds.iconTextButton("average_line_tool_button", style = "iconAndTextVertical", image1 = LOCAL_PATH + "/Model_Tools/Icons/average_line.png", l="Average", ann = "Open Average Line Tool", c = make_tracked_callback(ModelTool.open_average_line_tool, "Average Line Tool", 5.0, WINDOW_NAME))
	cmds.iconTextButton("shrinkwrap_tool_button", style = "iconAndTextVertical", image1 = LOCAL_PATH + "/Model_Tools/Icons/shrinkwrap.png", l="ShrinkWrap", ann = "Open ShrinkWrap Tool", c = make_tracked_callback(ModelTool.open_shrinkwrap_tool, "ShrinkWrap Tool", 5.0, WINDOW_NAME))
	cmds.setParent('..')

	cmds.separator(st='in')

	cmds.rowColumnLayout(nc=4, cw=[(1, 75), (2, 75), (3, 75), (4, 75)], adj=4)
	cmds.iconTextButton("unbevel_tool_button", style = "iconAndTextVertical", image1 = LOCAL_PATH + "/Model_Tools/Icons/unbevel.png", l="Unbevel", ann = "Open Unbevel Tool", c = make_tracked_callback(ModelTool.open_unbevel_tool, "Unbevel Tool", 5.0, WINDOW_NAME))
	cmds.iconTextButton("snap_tool_button", style = "iconAndTextVertical", image1 = LOCAL_PATH + "/Model_Tools/Icons/snap.png", l="Snap", ann = "Slide Snap: snap vertices onto a face by sliding along edges / axes", c = make_tracked_callback(ModelTool.open_snap_tool, "Slide Snap", 5.0, WINDOW_NAME))
	cmds.iconTextButton("cable_tool_button", style = "iconAndTextVertical", image1 = LOCAL_PATH + "/Model_Tools/Icons/cable.png", l="Cable", ann = "Open Cable Tool", c=make_tracked_callback(ModelTool.open_cable_tool, "Cable Tool", 5.0, WINDOW_NAME))	
	cmds.iconTextButton("material_manager_button", style = "iconAndTextVertical", image1 = LOCAL_PATH + "/Model_Tools/Icons/shader.png", l="Material", ann = "Open Material Manager: assign / create / rename materials, texture channels, colour presets, ID map baker", c = make_tracked_callback(MaterialTool.open_tool, "Material Manager", 5.0, WINDOW_NAME))
	cmds.setParent('..')

	cmds.separator(st='in')

	cmds.rowColumnLayout(nc=4, cw=[(1, 75), (2, 75), (3, 75), (4, 75)], adj=4)
	cmds.iconTextButton("clean_mesh_button", style = "iconAndTextVertical", image1 = LOCAL_PATH + "/Model_Tools/Icons/clean_mesh.png", l="Clear spEdge", ann = "Select Mesh", c=make_tracked_callback(ModelTool.open_clear_support_edge_tool, "Clear Support Edge Tool", 5.0, WINDOW_NAME))
	cmds.iconTextButton("swap_lod_button", style = "iconAndTextVertical", image1 = LOCAL_PATH + "/Model_Tools/Icons/LOD.png", l="Swap LOD", ann = "Open LOD Tool", c = make_tracked_callback(ModelTool.open_lod_tool, "LOD Tool", 5.0, WINDOW_NAME))
	cmds.iconTextButton("rename_button", style = "iconAndTextVertical", image1 = LOCAL_PATH + "/Model_Tools/Icons/rename.png", l="Rename", ann = "Rename Objects", c = make_tracked_callback(ModelTool.open_rename_tool, "Rename Tool", 5.0, WINDOW_NAME))
	cmds.iconTextButton("screenshot_button", style = "iconAndTextVertical", image1 = LOCAL_PATH + "/Model_Tools/Icons/screenshot.png", l="Screenshot", ann = "Open Screenshot Tool", c = make_tracked_callback(ModelTool.open_screenshot_tool, "Screenshot Tool", 5.0, WINDOW_NAME))
	cmds.setParent('..')

	cmds.separator(st='in')

	cmds.setParent('..')
	#endregion

	#region Fast Function Frame
	cmds.frameLayout('fast_function_layout', p = main_model_layout, l = 'Fast Function', collapsable = True, ann = 'fast function', cl=cmds.optionVar(q='fast_function_cl'), w=300, cc=lambda *args: get_current_frame_status('fast_function_layout', 'fast_function_cl'), ec=lambda *args: get_current_frame_status('fast_function_layout', 'fast_function_cl'))
	cmds.rowColumnLayout(nc=4, cw=[(1, 75), (2, 75), (3, 75), (4, 75)], adj=4)
	cmds.iconTextButton("split_polygon_button", style = "iconAndTextVertical", image1 = LOCAL_PATH + "/Model_Tools/Icons/split_polygon.png", l="Split Polygon", ann = "Select 2 vertices/edges to connect", c = make_tracked_callback(ModelTool.split_polygon, 'Split Polygon', 5.0))	
	cmds.iconTextButton("extend_face_button", style = "iconAndTextVertical", image1 = LOCAL_PATH + "/Model_Tools/Icons/extend_face.png", l="Extend Face", ann = "Select 1 Vertex/Edge to extend face", c = make_tracked_callback(ModelTool.smart_extend, 'Extend Face', 5.0))
	cmds.iconTextButton("fill_hole_button", style = "iconAndTextVertical", image1 = LOCAL_PATH + "/Model_Tools/Icons/fill_hole.png", l="Fill Face", ann = "Select 2 Vertices same line in hole", c = make_tracked_callback(ModelTool.smart_fill_hole, 'Fill Face', 5.0))
	cmds.iconTextButton("match_scale_button", style = "iconAndTextVertical", image1 = LOCAL_PATH + "/Model_Tools/Icons/match_scale.png", l="Match Scale", ann = "Select corresponding edge in each object", c=make_tracked_callback(ModelTool.match_scale, 'Match Scale', 5.0))
	#cmds.iconTextButton("reset_object_tool_button", style = "iconAndTextVertical", image1 = LOCAL_PATH + "/Model_Tools/Icons/reset_object.png", l="Reset Object", ann = "Select 3 Point/2 Edge/ 1 Face", c = ModelTool.reset_object_rotation)
	cmds.setParent('..')
	#endregion	

	#region Fix Frame
	cmds.frameLayout('fix_layout', p = main_model_layout, l = 'Fix Maya', collapsable = True, ann = 'Fix any maya error', cl=cmds.optionVar(q='fix_cl'), w=300, cc=lambda *args: get_current_frame_status('fix_layout', 'fix_cl'), ec=lambda *args: get_current_frame_status('fix_layout', 'fix_cl'))
	cmds.rowColumnLayout(nc=2, cw=[(1, 150), (2, 150)], adj=2, cs=[(2,5)])
	cmds.button("fix_cant_create_mesh_btn", h = 25, l = "Fix Can't Create Mesh", c = make_tracked_callback(ModelTool.fix_cant_create_mesh, "Fix Can't Create Mesh", 5.0))
	cmds.button("fix_error_maya_file_btn", h = 25, l = "Fix Green/Missing Object", c = make_tracked_callback(ModelTool.fix_error_maya_file, 'Fix Maya File Errors', 5.0))
	cmds.setParent('..')
	cmds.setParent('..')
	#endregion	

	#region Blender <-> Maya
	cmds.frameLayout('maya_blender_frame_layout', p = main_model_layout, l = 'Maya - Blender', collapsable = True, ann = 'Maya - Blender', cl=cmds.optionVar(q='maya_blender_cl'), w=300, cc=lambda *args: get_current_frame_status('maya_blender_frame_layout', 'maya_blender_cl'), ec=lambda *args: get_current_frame_status('maya_blender_frame_layout', 'maya_blender_cl'))
	cmds.rowColumnLayout("maya_blender_btn_layout", nc = 1, cw = [(1, 300)], adj = 1)
	cmds.radioButtonGrp('export_normal_mode_rbg', l='Normal:', h=30, nrb=2, la2=['Lock','Unlock'], cw3=[100,100,100], cl3=['left'] * 3, sl=cmds.optionVar(q='export_normal_mode_rbg'), cc="cmds.optionVar(iv=['export_normal_mode_rbg', cmds.radioButtonGrp(\'export_normal_mode_rbg\',q=True,sl=True)])")
	cmds.rowColumnLayout("maya_blender_btn_layout", nc = 2, cw = [(1, 150), (2,150)], adj = 2, cs = [(2,5)])
	cmds.button("import_blender_btn", l = "Import", h = 25, bgc = (0.6, 0.6, 1), c = make_tracked_callback(ModelTool.import_from_blender, 'Import From Blender', 5.0))
	cmds.button("export_blender_btn" , l = "Export", h = 25, bgc = (0.8, 0.8, 0.8), c = make_tracked_callback(ModelTool.export_to_blender, 'Export To Blender', 5.0))
	cmds.setParent('..')
	cmds.setParent('..')
	#endregion

	#region Import Export	
	default_import_export_path = read_data_from_json(LOCAL_SETTING_PATH)["default_path"]
	if default_import_export_path == "":
		default_import_export_path = LOCAL_PATH + "/Model_Tools/Files/Temp.ma"
	
	data = read_data_from_json(LOCAL_SETTING_PATH)
	data['default_path'] = default_import_export_path

	cmds.frameLayout('import_export_frame_layout', p = main_model_layout, l = 'Import/Export', collapsable = True, ann = 'Import/Export', cl=cmds.optionVar(q='import_export_cl'), w=300, cc=lambda *args: get_current_frame_status('import_export_frame_layout', 'import_export_cl'), ec=lambda *args: get_current_frame_status('import_export_frame_layout', 'import_export_cl'))
	cmds.rowColumnLayout('import_export_file_path_layout', nc = 3, cw = [(1,65), (2,195), (3,45)], adj=3, cs = [(2,5), (3,5)])
	cmds.text('File Path:')
	cmds.textField('import_export_path_tf', tx = default_import_export_path)
	cmds.button('get_import_export_btn', l='...', h = 25, c=make_tracked_callback(ModelTool.get_import_export_file_path, 'Get Import/Export Path', 5.0, data, LOCAL_SETTING_PATH))
	cmds.setParent('..')
	cmds.rowColumnLayout("import_export_btn_layout", nc = 2, cw = [(1, 150), (2,150)], adj = 2, cs = [(2,5)])
	cmds.button("import_btn", l = "Import Source To Current", h = 25, bgc = (0.2, 0.8, 0.5), c = make_tracked_callback(ModelTool.import_current_file, "Import Current File", 5.0))
	cmds.button("export_btn" , l = "Export Current To Source", h = 25, bgc = (0.8, 0.5, 0), c = make_tracked_callback(ModelTool.export_current_file, "Export Current File", 5.0))
	cmds.setParent('..')
	cmds.setParent('..')
	#endregion

def create_mirror_tab(mirror_layout):
	#region Mirror Tab
	cmds.columnLayout('mirror_setting_layout', p = mirror_layout, cw = 315, columnAttach=('both', 0), rowSpacing= 5)

	cmds.rowColumnLayout(nc=2, cw=[(1, 200), (2, 80)], cat=[2, 'left', 5])
	cmds.radioButtonGrp('mirror_setting_rbg', h=30, nrb=2, l=' Space:', la2=['World', 'Local'], sl=cmds.optionVar(q='mirror_space'), cw3=[45, 60, 45], cal=[1, 'left'], on1='cmds.optionVar(iv=[\'mirror_space\', 1])', on2='cmds.optionVar(iv=[\'mirror_space\', 2])')
	cmds.checkBox('mirror_uv_cb', l='UV', h=30, v=cmds.optionVar(q='mirror_uv'), cc='cmds.optionVar(iv=[\'mirror_uv\', cmds.checkBox(\'mirror_uv_cb\', q=True, v=True)])')
	cmds.setParent('..')

	#region BAKE PIVOT
	cmds.rowColumnLayout('pivot_setting_layout', nc = 3, cw = [(1,105), (2,105), (3,105)], adj=3, cs = [(2,5),(3,5)])
	cmds.button('bake_pivot_button', l='Bake Pivot', h=30, c=make_tracked_callback(MirrorTool.bake_pivot, 'Bake Pivot', 5.0))
	cmds.button('freeze_tranformations_button', l='Freeze Transforms', h=30, c=make_tracked_callback(MirrorTool.freeze_transforms, 'Freeze Transforms', 5.0))
	cmds.button('reset_pivot_button', l='Reset Pivot', h=30, c=make_tracked_callback(MirrorTool.reset_pivot, 'Reset Pivot', 5.0))
	cmds.setParent('..')
	#endregion

	#region MIRROR FLIP
	cmds.frameLayout('mirror_flip_frame_layout', p = mirror_layout, l = 'FLIP', collapsable = False, ann = 'FLIP')
	cmds.rowColumnLayout('mirror_flip_layout', nc = 3, cw = [(1,105), (2,105), (3,105)], adj=3, cs = [(2,5),(3,5)])
	cmds.button(l = 'Flip X', bgc=(0.8, 0.27, 0.2), h=30, c = make_tracked_callback(MirrorTool.flip_X, 'Mirror Flip X', 5.0))
	cmds.button(l = 'Flip Y', bgc = (0.2, 0.8, 0.5), h=30, c = make_tracked_callback(MirrorTool.flip_Y, 'Mirror Flip Y', 5.0))
	cmds.button(l = 'Flip Z', bgc=(0.2, 0.43, 0.8), h=30, c = make_tracked_callback(MirrorTool.flip_Z, 'Mirror Flip Z', 5.0))
	cmds.setParent('..')
	cmds.setParent('..')
	#endregion

	#region MIRROR SELECTION
	cmds.frameLayout('mirror_selection_frame_layout', p = mirror_layout, l = 'MIRROR', collapsable = False, ann = 'MIRROR')
	cmds.rowColumnLayout('mirror_selection_layout', nc = 3, cw = [(1,105), (2,105), (3,105)], adj=3, cs = [(2,5),(3,5)])
	cmds.button(l = 'Mirror X', bgc=(0.8, 0.27, 0.2), h=30, c = make_tracked_callback(MirrorTool.mirror_X, 'Mirror X', 5.0))
	cmds.button(l = 'Mirror Y', bgc = (0.2, 0.8, 0.5), h=30, c = make_tracked_callback(MirrorTool.mirror_Y, 'Mirror Y', 5.0))
	cmds.button(l = 'Mirror Z', bgc=(0.2, 0.43, 0.8), h=30, c = make_tracked_callback(MirrorTool.mirror_Z, 'Mirror Z', 5.0))
	cmds.setParent('..')
	cmds.setParent('..')
	#endregion

	#region MIRROR INSTANCE
	cmds.frameLayout('instance_frame_layout', p = mirror_layout, l = 'INSTANCE', collapsable = False, ann = 'INSTANCE')
	cmds.rowColumnLayout('instance_layout', nc = 3, cw = [(1,105), (2,105), (3,105)], adj=3, cs = [(2,5),(3,5)])
	cmds.button(l = 'Instance X', bgc=(0.8, 0.27, 0.2), h=30, c=make_tracked_callback(MirrorTool.mirror_instance_X, 'Mirror Instance X', 5.0))
	cmds.button(l = 'Instance Y', bgc = (0.2, 0.8, 0.5), h=30, c=make_tracked_callback(MirrorTool.mirror_instance_Y, 'Mirror Instance Y', 5.0))
	cmds.button(l = 'Instance Z', bgc=(0.2, 0.43, 0.8), h=30, c=make_tracked_callback(MirrorTool.mirror_instance_Z, 'Mirror Instance Z', 5.0))
	cmds.setParent('..')
	cmds.setParent('..')
	#endregion

	#region MIRROR MERGE
	cmds.frameLayout('merge_frame_layout', p = mirror_layout, l = 'MERGE', collapsable = False, ann = 'MERGE')

	cmds.rowColumnLayout('merge_tolerance_layout', nc = 3, cw = [(1,105), (2,105), (3,105)], adj=3, cs = [(2,5),(3,5)])
	cmds.text(l = 'Merge Tolerance:', h=30)
	cmds.floatField('merge_tolerance_ff', h=30 , v = cmds.optionVar(q='merge_tolerance'), cc='cmds.optionVar(iv=[\'merge_tolerance\', cmds.floatField(\'merge_tolerance_ff\', q=True, v=True)])')
	cmds.setParent('..')

	cmds.rowColumnLayout('merge_up_layout', nc = 3, cw = [(1,105), (2,105), (3,105)], adj=3, cs = [(2,5),(3,5)])
	cmds.button(l = 'Merge +X', bgc=(0.8, 0.27, 0.2), h=30, c = make_tracked_callback(MirrorTool.mirror_merge_X_pos, 'Mirror Merge +X', 5.0))
	cmds.button(l = 'Merge +Y', bgc = (0.2, 0.8, 0.5), h=30, c = make_tracked_callback(MirrorTool.mirror_merge_Y_pos, 'Mirror Merge +Y', 5.0))
	cmds.button(l = 'Merge +Z', bgc=(0.2, 0.43, 0.8), h=30, c = make_tracked_callback(MirrorTool.mirror_merge_Z_pos, 'Mirror Merge +Z', 5.0))
	cmds.setParent('..')

	cmds.rowColumnLayout('merge_down_layout', nc = 3, cw = [(1,105), (2,105), (3,105)], adj=3, cs = [(2,5),(3,5)])
	cmds.button(l = 'Merge -X', bgc=(0.8, 0.27, 0.2), h=30, c = make_tracked_callback(MirrorTool.mirror_merge_X_neg, 'Mirror Merge -X', 5.0))
	cmds.button(l = 'Merge -Y', bgc = (0.2, 0.8, 0.5), h=30, c = make_tracked_callback(MirrorTool.mirror_merge_Y_neg, 'Mirror Merge -Y', 5.0))
	cmds.button(l = 'Merge -Z', bgc=(0.2, 0.43, 0.8), h=30, c = make_tracked_callback(MirrorTool.mirror_merge_Z_neg, 'Mirror Merge -Z', 5.0))
	cmds.setParent('..')
	cmds.setParent('..')
	#endregion

	#region MIRROR CUT
	cmds.frameLayout('mirror_cut_frame_layout', p = mirror_layout, l = 'CUT', collapsable = False, ann = 'CUT')
	cmds.rowColumnLayout('mirror_cut_layout', nc = 1, cw = [(1,315)], adj=1)
	cmds.button('mirror_cut_button', l='Mirror Cut', h=30, c = make_tracked_callback(MirrorTool.mirror_cut, 'Mirror Cut', 5.0))
	cmds.setParent('..')
	cmds.setParent('..')
	#endregion

	#region MIRROR REVOLVE
	cmds.frameLayout('mirror_revolve_frame_layout', p = mirror_layout, l = 'REVOLVE', collapsable = False, ann = 'REVOLVE')
	cmds.rowColumnLayout('mirror_revolve_setting_layout', nc = 3, cw = [(1,155), (1,105), (3,55)], adj=3, cs = [(2,5), (3,25)])
	cmds.text('Revolve Count:')
	cmds.intField('revolve_count_if', h=30, v=cmds.optionVar(q='revolve_count_value'), cc='cmds.optionVar(iv=[\'revolve_count_value\', cmds.intField(\'revolve_count_if\', q=True, v=True)])')
	cmds.checkBox('revolve_instance_cb', h=30, l='Instance', v=cmds.optionVar(q='revolve_instance'), cc='cmds.optionVar(iv=[\'revolve_instance\', cmds.checkBox(\'revolve_instance_cb\', q=True, v=True)])')
	cmds.setParent('..')

	cmds.rowColumnLayout('mirror_revolve_layout', nc = 3, cw = [(1,105), (2,105), (3,105)], adj=3, cs = [(2,5),(3,5)])
	cmds.button(l = 'Revolve X', bgc=(0.8, 0.27, 0.2), h=30, c=make_tracked_callback(MirrorTool.revolve_X, 'Revolve X', 5.0))
	cmds.button(l = 'Revolve Y', bgc = (0.2, 0.8, 0.5), h=30, c=make_tracked_callback(MirrorTool.revolve_Y, 'Revolve Y', 5.0))
	cmds.button(l = 'Revolve Z', bgc=(0.2, 0.43, 0.8), h=30, c=make_tracked_callback(MirrorTool.revolve_Z, 'Revolve Z', 5.0))
	cmds.setParent('..')

	cmds.setParent('..')
	#endregion

	cmds.setParent('..')
	#endregion

def create_normal_tab(normal_layout):
	#region Normal Tab
	display_vertex_normal_frame_layout = cmds.frameLayout('display_vertex_normal_frame_layout', p = normal_layout, l = 'Display Vertex Normal', collapsable = False, ann = 'Display Vertex Normal')
	cmds.rowColumnLayout('normal_size_layout', p = display_vertex_normal_frame_layout, nc = 2, cw = [(1,115), (2,195)], adj=2, cs = [(2,5)])
	cmds.text(l = 'Normal Size:', h=30)
	cmds.floatField('normal_size_textfield', h=30, v = 2, min = 0, max = 100, step = 0.1)
	cmds.setParent('..')

	cmds.rowColumnLayout('toggle_normal_layout', p = display_vertex_normal_frame_layout, nc = 2, cw = [(1,155), (2,155)], adj=2, cs = [(2,5)])
	cmds.button('toggle_selected_button', l = 'Toggle Selected', h=30, c = make_tracked_callback(NormalTools_Main.toggle_selected_normal, 'Toggle Selected Normal', 5.0))
	cmds.button('toggle_everything_button', l = 'Toggle Everything', h=30, c = make_tracked_callback(NormalTools_Main.toggle_everything_normal, 'Toggle Everything Normal', 5.0))
	cmds.setParent('..')

	# Normal Value Copy (port of AriNormalValueCopy.mel)
	NormalTools_Main.normal_value_copy.build_ui(normal_layout)

	copy_paste_normal_frame_layout = cmds.frameLayout('copy_paste_normal_frame_layout', p = normal_layout, l = 'Copy/Paste Normal', collapsable = False, ann = 'Copy/Paste Normal')
	
	cmds.rowColumnLayout(p = copy_paste_normal_frame_layout, nc = 3, cw = [(1,105), (2,105), (3,105)], adj=3, cs = [(2,5), (3,5)])
	cmds.button('copy_normal_button', l = 'Copy', h=30, c = make_tracked_callback(NormalTools_Main.copy_vertex_normal, 'Copy Vertex Normal', 5.0))
	cmds.button('copy_average_button', l = 'Copy Average', h=30, c = make_tracked_callback(NormalTools_Main.copy_average_normal, 'Copy Average Normal', 5.0))
	cmds.button('paste_normal_button', l = 'Paste', h=30, c = make_tracked_callback(NormalTools_Main.paste_vertex_normal, 'Paste Vertex Normal', 5.0))
	cmds.setParent('..')

	cmds.rowColumnLayout(p = copy_paste_normal_frame_layout, nc = 1, cw = [(1,315)])
	cmds.button('copy_average_paste_3_vertices_button', l = 'Copy Paste Average 3 Vertex Normals', h=30, c = make_tracked_callback(NormalTools_Main.copy_paste_average_3_vetices_normals, 'Copy Paste Average 3 Vert Normals', 5.0))
	cmds.setParent('..')
	cmds.rowColumnLayout(p = copy_paste_normal_frame_layout, nc = 1, cw = [(1,315)])
	cmds.button('paste_average_normals_button', l = 'Copy Paste Average Normals', h=30, c = make_tracked_callback(NormalTools_Main.copy_paste_average_normals, 'Copy Paste Average Normals', 5.0))
	cmds.setParent('..')
	cmds.rowColumnLayout(p = copy_paste_normal_frame_layout, nc = 1, cw = [(1,315)])
	cmds.button('set_average_normal_merge_vertex_button', l = 'Set Average Normal & Merge Selected Vertices', h=30, c = make_tracked_callback(NormalTools_Main.set_average_normal_and_merge_vertices, 'Set Average Normal & Merge Selected Vertices', 5.0))
	cmds.setParent('..')
	cmds.rowColumnLayout(p = copy_paste_normal_frame_layout, nc = 1, cw = [(1,315)])
	cmds.button('target_weld_keep_normal_button', l = 'Target Weld Keep Normal', h=30, c = make_tracked_callback(NormalTools_Main.target_weld_keep_normal, 'Target Weld Keep Normal', 5.0))
	cmds.setParent('..')
	cmds.rowColumnLayout(p = copy_paste_normal_frame_layout, nc = 1, cw = [(1,315)])
	cmds.button('collapse_edge_average_normal_button', l = 'Collapse Selected Edges + Avg Normal', h=30, c = make_tracked_callback(NormalTools_Main.collapse_selected_edges_with_average_normals, 'Collapse Selected Edges With Average Normals', 5.0))
	cmds.setParent('..')
	cmds.rowColumnLayout(p = copy_paste_normal_frame_layout, nc = 1, cw = [(1,315)])
	cmds.button('inverse_selected_vertex_normals_button', l = 'Inverse Selected Vertex Normals', h=30, c = make_tracked_callback(NormalTools_Main.inverse_selected_vertex_normals, 'Inverse Selected Vertex Normals', 5.0))
	cmds.setParent('..')


	lock_normal_frame_layout = cmds.frameLayout('lock_normal_frame_layout', p = normal_layout, l = 'Lock Normal', collapsable = False, ann = 'Lock Normal')

	cmds.rowColumnLayout(p = lock_normal_frame_layout, nc = 2, cw = [(1,155), (2,155)], adj=2, cs = [(2,5)])
	cmds.button('lock_button', l = 'Lock', h=30, c = make_tracked_callback(NormalTools_Main.lock_normals, 'Lock Normals', 5.0))
	cmds.button('unlock_button', l = 'Unlock', h=30, c = make_tracked_callback(NormalTools_Main.unlock_normals, 'Unlock Normals', 5.0))
	cmds.setParent('..')

	cmds.rowColumnLayout(p = lock_normal_frame_layout, nc = 2, cw = [(1,155), (2,155)], adj=2, cs = [(2,5)])
	cmds.button('lock_normals_with_hard_soft_edges_button', l = 'Lock Keep Hard/Soft', h=30, c = make_tracked_callback(NormalTools_Main.lock_normals_keep_hard_soft_edges, 'Lock Keep Hard/Soft', 5.0))
	cmds.button('locked_normals_to_hard_soft_edges_button', l = 'Locked Normal -> H/S Edges', h=30, c = make_tracked_callback(NormalTools_Main.locked_normals_to_hard_soft_edges, 'Locked Normal to H/S Edges', 5.0))
	cmds.setParent('..')

	# cmds.rowColumnLayout(p = lock_normal_frame_layout, nc = 2, cw = [(1,315)], adj=1)
	# cmds.button('boolean_lock_normal_button', l = 'Boolean - Lock Normal', h=30, c = NormalTools_Main.boolean_lock_normal)
	# cmds.setParent('..')

	# cmds.rowColumnLayout(p = lock_normal_frame_layout, nc = 2, cw = [(1,155), (2,155)], adj=2, cs = [(2,5)])
	# cmds.button('lock_follow_small_face_button', l = 'Lock follow SMALL face', h=30, c = NormalTools_Main.lock_follow_small_face)
	# cmds.button('lock_follow_large_face_button', l = 'Lock follow LARGE face', h=30, c = NormalTools_Main.lock_follow_large_face)
	# cmds.setParent('..')

	cmds.rowColumnLayout(p = lock_normal_frame_layout, nc = 2, cw = [(1,155), (2,155)], adj=2, cs = [(2,5)])
	cmds.button('smooth_bevelled_faces_button', l = 'Smooth Bevelled Faces', h=30, c = make_tracked_callback(NormalTools_Main.smooth_bevelled_faces, 'Smooth Bevelled Faces', 5.0))
	cmds.button('smooth_flatten_face_button', l = 'Smooth Flatten Faces', h=30, c = make_tracked_callback(NormalTools_Main.smooth_flatten_faces, 'Smooth Flatten Faces', 5.0))
	cmds.setParent('..')	

	cmds.rowColumnLayout(p = lock_normal_frame_layout, nc = 2, cw = [(1,155), (2,155)], adj=2, cs = [(2,5)])
	cmds.button('lock_face_90_button', l = 'Lock Face 90 Angle', h=30, c = make_tracked_callback(NormalTools_Main.lock_face_90_angle, 'Lock Face 90 Angle', 5.0))
	cmds.button('lock_large_face_button', l = 'Lock LARGE Face', h=30, c = make_tracked_callback(NormalTools_Main.lock_follow_large_face, 'Lock Large Face', 5.0))
	cmds.setParent('..')

	transfer_normal_frame_layout = cmds.frameLayout('transfer_normal_normal_frame_layout', p = normal_layout, l = 'Transfer Normal', collapsable = False, ann = 'Transfer Normal')
	cmds.rowColumnLayout(p = transfer_normal_frame_layout, nc = 2, cw = [(1,115), (2,195)], adj=2, cs = [(2,5)])
	cmds.button('pick_source_button', l = 'Pick SOURCE:', h=30, c = make_tracked_callback(NormalTools_Main.pick_source_for_transfer, 'Pick Source Normal', 5.0))
	cmds.textField('source_normal_textfield', h=30)
	cmds.setParent('..')

	cmds.rowColumnLayout(p = transfer_normal_frame_layout, nc = 2, cw = [(1,155), (2,155)], adj=2, cs = [(2,5)])
	cmds.button('transfer_to_mesh_button', l = 'Transfer To MESH', h=30, c = make_tracked_callback(NormalTools_Main.transfer_normals_to_object, 'Transfer Normals To Object', 5.0))
	cmds.button('transfer_to_vertex_button', l = 'Transfer To VERTEX', h=30, c = make_tracked_callback(NormalTools_Main.transfer_normals_to_selected_vertices, 'Transfer To Vertex', 5.0))
	cmds.setParent('..')
	
	cmds.separator(h=1, p = transfer_normal_frame_layout)

	cmds.rowColumnLayout(p = transfer_normal_frame_layout, nc = 1, cw = [(1,315)], adj=1)
	cmds.button('transfer_vertices_select_target_then_source_button', l = 'Transfer VERTICES - Select TARGET(s) Then SOURCE', h=30, c = make_tracked_callback(NormalTools_Main.transfer_normal, 'Transfer Vertices (Target then Source)', 5.0))
	cmds.setParent('..')
	
	connect_normal_frame_layout = cmds.frameLayout('connect_normal_frame_layout', p = normal_layout, l = 'Connect Normal', collapsable = False, ann = 'Connect Normal')
	cmds.rowColumnLayout(p = connect_normal_frame_layout, nc = 2, cw = [(1,155), (2,155)], adj=2, cs = [(2,5)])
	cmds.button('connect_with_flow_button', l = 'Connect With Flow', h=30, c = make_tracked_callback(NormalTools_Main.connect_with_follow, 'Connect With Flow', 5.0))
	cmds.button('connect_without_flow_button', l = 'Connect Without Flow', h=30, c = make_tracked_callback(NormalTools_Main.connect_without_follow, 'Connect Without Flow', 5.0))
	cmds.setParent('..')
	#endregion 

def create_uv_tab(uv_layout):
	#region UV Tab
	UVToolsMain.config_for_rizom()
	#region Select & Set Frame
	select_frame_layout = cmds.frameLayout("select_frame_layout", p = uv_layout, l = "Select & Set", collapsable = False, ann = "Select") 
	select_row_column_layout = cmds.rowColumnLayout("select_row_column_layout", p = select_frame_layout, nc = 2, cw = [(1,155), (2,155)], cs = [(2,5)])
	cmds.button("HE_button", p = select_row_column_layout, l = "Hard Edge", h=30, c = make_tracked_callback(UVToolsMain.selectHardEdge, "Select Hard Edge", 5.0))
	cmds.button("HENB_button", p = select_row_column_layout, l = "Hard Edge (Not Border)", h=30, c = make_tracked_callback(UVToolsMain.get_hard_edges_without_uv_border, "Hard Edge (Not Border)", 5.0))
	set_row_column_layout = cmds.rowColumnLayout("set_row_column_layout", p = select_frame_layout, nc = 2, cw = [(1,155), (2,155)], cs = [(2,5)])
	cmds.button("BE_button", p = set_row_column_layout, l = "Open Edge", h=30, c = make_tracked_callback(UVToolsMain.selectBorderEdge, "Open Edge", 5.0))
	cmds.button("UB_button", p = set_row_column_layout, l = "Set UV Border", h=30, c = make_tracked_callback(UVToolsMain.selectUVBorder, "Set UV Border", 5.0))
	#endregion

	#region Unwarp Frame
	unwrap_frame_layout = cmds.frameLayout("unwrap_frame_layout", p = uv_layout, l = "Unwrap", collapsable = False, ann = "Unwrap") 
	
	# Unwarp button
	UW1_column_layout = cmds.rowColumnLayout("UW1_column_layout", p = unwrap_frame_layout, nc = 2, cw = [(1,155), (2,155)], adj=2, cs = [(2,5)])
	cmds.iconTextButton("UW_select_button", p = UW1_column_layout, style = "iconAndTextHorizontal", image1 = LOCAL_PATH + "/UV_Tools/Icons/US.png", l = "UW Select Edge", c = make_tracked_callback(UVToolsMain.unwrapSelectEdge, "UV Unwrap Select Edge", 5.0))
	cmds.iconTextButton("UW_hard_edge_button", p = UW1_column_layout, style = "iconAndTextHorizontal", image1 = LOCAL_PATH + "/UV_Tools/Icons/UH.png", l = "UW Hard Edge", c = make_tracked_callback(UVToolsMain.unwrapHardEdge, "UV Unwrap Hard Edge", 5.0))

	#endregion

	#region Edit Frame
	edit_frame_layout = cmds.frameLayout("edit_frame_layout", p = uv_layout, l = "Edit", collapsable = False, collapse = False, ann = "Edit")

	# Edit UVs button
	edit2_column_layout = cmds.rowColumnLayout("edit2_column_layout", p = edit_frame_layout, nc = 2, cw = [(1,155), (2,155)], adj=2, cs = [(2,5)])
	cmds.button("UV_grid_button", p = edit2_column_layout, l = "UV Grid", h=30, c = make_tracked_callback(UVToolsMain.UVGridding, "UV Grid", 5.0))
	cmds.button("UF_smart_button", p = edit2_column_layout, l = "Unfold", h=30, c = make_tracked_callback(UVToolsMain.smartUnfold, "UV Unfold", 5.0))

	edit_uf_layout = cmds.rowColumnLayout("edit_uf_layout", p = edit_frame_layout, nc = 2, cw = [(1,155), (2,155)], cs = [(2,5)])
	cmds.button("transfer_uv_button", p = edit_uf_layout, l = "Transfer UV", h=30, c = make_tracked_callback(UVToolsMain.transferUV, "Transfer UV", 5.0))
	cmds.button("match_uv_button", p = edit_uf_layout, l = "Match UV", h=30, c = make_tracked_callback(UVToolsMain.matchUV, "Match UV", 5.0))

	cmds.separator(st='in', p=edit_frame_layout)
	scale_uv_layout = cmds.rowColumnLayout("scale_uv_layout", p = edit_frame_layout, nc = 5, cw = [(1,75), (2,55), (3,55), (4,55), (5,55)], cs = [(2,5), (3,5), (4,5), (5,5)])
	cmds.text('Texel Density: ')
	cmds.floatField("texel_density_ff", min=0, max=10000, pre=2, v=0)
	cmds.text('Size Map: ')
	cmds.intField("size_map_tf", min=1, max=10000, v=2048)
	cmds.button("get_texel_density_button", p = scale_uv_layout, l = "Get", h=30, c = make_tracked_callback(UVToolsMain.show_texel_density, "Get Texel Density", 5.0))
	scale2_uv_layout = cmds.rowColumnLayout("scale2_uv_layout", p = edit_frame_layout, nc = 2, cw = [(1,155), (2,155)], cs = [(2,5)])
	cmds.button("scale_center_element_button", p = scale2_uv_layout, l = "Scale", h=30, c = make_tracked_callback(UVToolsMain.scale_by_center_element, "Scale By Center Element", 5.0))
	cmds.button("scale_center_group_button", p = scale2_uv_layout, l = "Group Scale", h=30, c = make_tracked_callback(UVToolsMain.scale_by_center_group, "Scale By Center Group", 5.0))
	cmds.separator(st='in', p=edit_frame_layout)
	#endregion

	#region Photoshop Frame
	pts_frame_layout = cmds.frameLayout("pts_frame_layout", p = uv_layout, l = "Photoshop", collapsable = False, ann = "UV To Photoshop") 
	pts_layout = cmds.columnLayout("pts_layout", p = pts_frame_layout, cw = 315, columnAttach=('both', 0), rowSpacing= 5)
	cmds.button("uv_to_pts_button", p = pts_layout, l = "UV To PTS", h=45, c = make_tracked_callback(UVToolsMain.UVtoPSD, "UV to Photoshop", 5.0))
	#endregion

	#region rizom Frame
	rizom_frame_layout = cmds.frameLayout("rizom_frame_layout", p = uv_layout, l = "Rizom", collapsable = False, collapse = False, ann = "Rizom")
	open_rizom_layout = cmds.rowColumnLayout("open_rizom_layout", p = rizom_frame_layout, nc = 2, cw = [(1,150), (2,150)], adj=2, cs = [(2,5)])
	cmds.button("open_rizom_button,", p = open_rizom_layout, l = "Open RizomUV", h=30, c = make_tracked_callback(UVToolsMain.open_rizom, "Open RizomUV", 5.0))
	cmds.button("select_rizom_button,", p = open_rizom_layout, l = "Select Version (exe)", h=30, c = UVToolsMain.select_rizom_version)
	transfer_rizom_layout = cmds.rowColumnLayout("transfer_rizom_layout", p = rizom_frame_layout, nc = 2, cw = [(1,150), (2,150)], adj=2, cs = [(2,5)])
	cmds.button("export_to_rizom_button", p = transfer_rizom_layout, l = "Export To Rizom", h=30, c = make_tracked_callback(UVToolsMain.export_to_rizom, "Export To Rizom", 5.0))
	cmds.button("import_to_maya_button", p = transfer_rizom_layout, l = "Import To Maya", h=30, c = make_tracked_callback(UVToolsMain.import_to_maya, "Import To Maya", 5.0))
	#endregion

	#region Checker Frame
	checker_frame_layout = cmds.frameLayout("checker_frame_layout", p = uv_layout, l = "Checker", collapsable = False, collapse = False, ann = "Checker")
	checker_layout = cmds.columnLayout("checker_layout", p = checker_frame_layout, cw = 315, columnAttach=('both', 0), rowSpacing= 5)
	cmds.button("checker_button", p = checker_layout, l = "UV Checker", h=45, c = make_tracked_callback(UVToolsMain.UVChecker, "UV Checker", 5.0))
	#endregion

	#region UVSet Frame
	uvset_frame_layout = cmds.frameLayout("uvset_frame_layout", p = uv_layout, l = "UVSet", collapsable = False, ann = "UVSet") 
	uvset_layout = cmds.rowColumnLayout("uvset_layout", p = uvset_frame_layout, nc = 2, cw = [(1,210), (2,115)], adj=2, cs = [(1,5)])
	cmds.textScrollList("uvset_list_textscroll", p = uvset_layout, ams = True, vcc=UVToolsMain.reloadUVSetTextScroll, dcc=UVToolsMain.selectUVSet)
	uvset_event_btn_layout = cmds.columnLayout("uvset_event_btn_layout", p = uvset_layout, adj=True, columnAttach=('both', 1), rowSpacing=1)
	cmds.button("select_object_by_uvset_button", p = uvset_event_btn_layout, l = "Select Objects", h=30, c = make_tracked_callback(UVToolsMain.selectObjectByUVSet, "Select Objects By UVSet", 5.0))
	cmds.button("set_default_uvset", p = uvset_event_btn_layout, l = "Set Default UVSet", h=30, c = make_tracked_callback(UVToolsMain.setDefaultUVSet, "Set Default UVSet", 5.0))
	cmds.button("sort_uvset_list", p = uvset_event_btn_layout, l = "Sort UVSet List", h=30, c = make_tracked_callback(UVToolsMain.sortUVSetList, "Sort UVSet List", 5.0))
	cmds.separator(st='in', p = uvset_event_btn_layout)
	cmds.textField('rename_textbox', p = uvset_event_btn_layout, h=30)
	cmds.button("rename_button", p = uvset_event_btn_layout, l = "Rename", h=30, c = make_tracked_callback(UVToolsMain.renameUVSet, "Rename UVSet", 5.0))
	cmds.button("copy_button", p = uvset_event_btn_layout, l = "Copy", h=30, c = make_tracked_callback(UVToolsMain.copyUVSet, "Copy UVSet", 5.0))
	cmds.button("delete_button", p = uvset_event_btn_layout, l = "Delete", h=30, c = make_tracked_callback(UVToolsMain.deleteUVSet, "Delete UVSet", 5.0))
	#endregion

	#region UV Editor
	editor_button_layout = cmds.rowColumnLayout("editor_button_layout", p = uv_layout, nc = 1, cw = [(1,315)])
	cmds.button("editor_button", p = editor_button_layout, label = "Editor", bgc = (0.2, 0.8, 0.5), c = make_tracked_callback(UVToolsMain.OpenUVEditor, "Open UV Editor", 5.0), h=50)
	#endregion

	cmds.scriptJob(ct=["SomethingSelected", UVToolsMain.reloadUVSetTextScroll], parent=WINDOW_NAME)
	cmds.scriptJob(e=["SelectionChanged", UVToolsMain.reloadUVSetTextScroll], parent=WINDOW_NAME)
	cmds.scriptJob(e=["PolyUVSetChanged", UVToolsMain.reloadUVSetTextScroll], parent=WINDOW_NAME)
	cmds.scriptJob(e=["PolyUVSetDeleted", UVToolsMain.reloadUVSetTextScroll], parent=WINDOW_NAME)
	#endregion

def create_bake_tab(bake_layout):
	#region BakeSet Tab
	export_path = BakeSetTool.auto_fill_export_path()

	cmds.frameLayout('apply_normal_map_frame_layout', p = bake_layout, l = 'Normal Map', collapsable = False, ann = 'Apply Normal Map')
	cmds.rowColumnLayout('set_normal_map_layout', nc = 3, cw = [(1,65), (2,205), (3,35)], adj=3, cs = [(2,5), (3,5)])
	cmds.text('Map Path:', h=30)
	cmds.textField('normal_map_path_tf', h=30, tx='')
	cmds.button('get_normal_path_btn', h=30, l='...', c=make_tracked_callback(BakeSetTool.get_normal_map_path, 'Get Normal Map Path', 10.0))
	cmds.setParent('..')
	cmds.rowColumnLayout('apply_normal_button_layout', nc = 2, cw = [(1,155), (2,155)], adj=2, cs = [(2,5)])
	cmds.button('apply_normal_map_to_object_btn', l='Apply Normal To Object', h=30, c=make_tracked_callback(BakeSetTool.assign_normal_map, 'Apply Normal Map', 10.0))
	cmds.button('clear_normal_map_from_object_btn', l='Clear', h=30, c=make_tracked_callback(BakeSetTool.clear_normal_map, 'Clear Normal Map', 5.0))
	cmds.setParent('..')
	cmds.setParent('..')

	cmds.frameLayout('apply_ao_map_frame_layout', p = bake_layout, l = 'AO Map', collapsable = False, ann = 'Apply AO Map')
	cmds.rowColumnLayout('set_ao_map_layout', nc = 3, cw = [(1,65), (2,205), (3,35)], adj=3, cs = [(2,5), (3,5)])
	cmds.text('Map Path:', h=30)
	cmds.textField('ao_map_path_tf', h=30, tx='')
	cmds.button('get_ao_path_btn', h=30, l='...', c=make_tracked_callback(BakeSetTool.get_ao_map_path, 'Get AO Map Path', 10.0))
	cmds.setParent('..')
	cmds.rowColumnLayout('apply_ao_button_layout', nc = 2, cw = [(1,155), (2,155)], adj=2, cs = [(2,5)])
	cmds.button('apply_ao_map_to_object_btn', l='Apply AO To Object', h=30, c=make_tracked_callback(BakeSetTool.assign_ao_map, 'Apply AO Map', 10.0))
	cmds.button('clear_ao_map_from_object_btn', l='Clear', h=30, c=make_tracked_callback(BakeSetTool.clear_ao_map, 'Clear AO Map', 10.0))
	cmds.setParent('..')
	cmds.setParent('..')

	cmds.frameLayout('tangent_space_frame_layout', p = bake_layout, l = 'Tangent Space', collapsable = False, ann = 'Tangent Space')
	cmds.rowColumnLayout('tangent_space_layout', nc = 2, cw = [(1,155), (2,155)], adj=2, cs = [(2,5)])
	cmds.button("right_handed_btn", l = "Right Handed", h=30, c = make_tracked_callback(BakeSetTool.set_right_handed, 'Right Handed Tangent', 10.0))
	cmds.button("left_handed_btn", l = "Left Handed", h=30, c = make_tracked_callback(BakeSetTool.set_left_handed, 'Left Handed Tangent', 10.0))
	cmds.setParent('..')
	cmds.setParent('..')

	cmds.frameLayout('setup_scene_frame_layout', p = bake_layout, l = 'Setup Bake Scene', collapsable = False, ann = 'Setup Bake Scene')
	cmds.columnLayout("setup_scene_layout", columnAttach=('both', 0), rowSpacing= 5, cw=315)
	cmds.rowColumnLayout('bakeset_name_layout', nc = 4, cw = [(1,85), (2,105), (3, 65), (4,45)], adj= 4, cs = [(2,5), (3,5)])
	cmds.text('BakeSet Name:', h=30)
	cmds.textField('bakeset_name_tf', h=30, tx="BakeSet_")
	cmds.text('Threshold:', h=30)
	cmds.floatField('bakeset_auto_threshold_ff', h=30, v=0.01)
	cmds.setParent('..')
	cmds.button("rename_highpoly_btn", l = "Rename Highpoly", h=30, c = make_tracked_callback(BakeSetTool.rename_highpoly, 'Rename Highpoly', 10.0))
	cmds.button("create_bakeset_group_manual_btn", l = "Create BakeSet (Select High+Low)", h=30, c = make_tracked_callback(BakeSetTool.create_bakeset_group_manual, 'Create BakeSet Manual', 10.0))
	cmds.button("create_bakeset_group_auto_btn", l = "Auto Create BakeSet (Select All High+Low)", h=30, c = make_tracked_callback(BakeSetTool.create_bakeset_group_auto, 'Create BakeSet Auto', 10.0))
	cmds.button("create_highlow_layer_btn", l = "Create HighLow Layer", h=30, c = make_tracked_callback(BakeSetTool.create_highlow_layer, 'Create HighLow Layer', 10.0))
	cmds.rowColumnLayout('toggle_bakesetgroup_layout', nc = 2, cw = [(1,155), (2,155)], adj=2, cs = [(2,5)])
	cmds.button("expand_all_bakeset_btn", l = "Expand All Group", h=30, c = make_tracked_callback(BakeSetTool.expand_all_bakeset, 'Expand All BakeSet', 10.0))
	cmds.button("collapse_all_bakeset_btn", l = "Collapse All Group", h=30, c = make_tracked_callback(BakeSetTool.collapse_all_bakeset, 'Collapse All BakeSet', 10.0))
	cmds.setParent('..')
	cmds.setParent('..')
	cmds.setParent('..')

	cmds.frameLayout('export_fbx_frame_layout', p = bake_layout, l = 'Export FBX', collapsable = False, ann = 'Export FBX')
	cmds.rowColumnLayout('set_export_fbx_path_layout', nc = 3, cw = [(1,60), (2,205), (3,35)], adj=3, cs = [(2,5), (3,5)])
	cmds.text('FBX Path:', h=30)
	cmds.textField('export_fbx_path_tf', h=30, tx=export_path)
	cmds.button('export_fbx_path_btn', h=30, l='...', c=make_tracked_callback(BakeSetTool.get_export_fbx_path, 'Get Export FBX Path', 10.0))
	cmds.setParent('..')
	cmds.columnLayout("export_fbx_layout", columnAttach=('both', 0), rowSpacing= 5, cw=315)
	cmds.radioButtonGrp('export_bakeset_mode_rbg', l='Export Mode:', h=30, nrb=2, la2=['1 File','Multiple Files'], cw3=[100,100,100], cl3=['left'] * 3, sl=cmds.optionVar(q='export_bakeset_mode'), cc="cmds.optionVar(iv=['export_bakeset_mode', cmds.radioButtonGrp(\'export_bakeset_mode_rbg\',q=True,sl=True)])")
	cmds.rowColumnLayout('bakeset_name_layout', nc = 2, cw = [(1,75), (2,105)], adj= 2, cs = [(2,35),(3,105)])
	cmds.text('Lock Normal:')
	cmds.checkBox('bakeset_lock_normal_cb', l='Keep', v=cmds.optionVar(q='bakeset_lock_normal'), cc="cmds.optionVar(iv=[\'bakeset_lock_normal\', cmds.checkBox(\'bakeset_lock_normal_cb\', q=True, v=True)])")
	cmds.setParent('..')
	cmds.button("export_selected_btn", l = "Export Selected BakeSet", h=30, c = make_tracked_callback(BakeSetTool.export_selected_bakeset, 'Export Selected BakeSet', 10.0))
	cmds.button("export_bakeset_btn", l = "Export All BakeSet", h=30, c = make_tracked_callback(BakeSetTool.export_bakeset, 'Export All BakeSet', 10.0))
	cmds.setParent('..')
	cmds.setParent('..')
	#endregion

#region SUPPORT FUNCTION

def make_tracked_callback(fn, tool_name, seconds_saved=5.0, *fixed_args, **fixed_kwargs):
	def _callback(*args):
		return fn(*fixed_args, **fixed_kwargs)
	return _callback

def is_check_pass_color(color, tolerance=0.001):
	pass_color = (0.0, 0.8, 0.0)
	return len(color) == len(pass_color) and all(abs(value - expected) <= tolerance for value, expected in zip(color, pass_color))

def execute_check_and_update_time(check_functions, *args):
	CheckTool.executeSelectedFunction(check_functions)
	if not cmds.textField('checked_time_textfield', ex=True):
		return

	all_checks_passed = all(is_check_pass_color(cmds.button(check_name, q=True, bgc=True)) for check_name in check_button_names)
	if all_checks_passed:
		cmds.textField('checked_time_textfield', e=True, tx=time.strftime('%Y-%m-%d %H:%M:%S'), bgc=[0.0, 0.8, 0.0])
	else:
		cmds.textField('checked_time_textfield', e=True, tx='Pending', bgc=[0.35, 0.0, 0.0])

#region UI FUNCTION
#region RESIZE HELPERS
def create_tab_container(tab_name, parent):
	# Every tab content sits in a formLayout so its scroll area can follow the window size.
	# (A tab is deleted/recreated by this name when it is detached / returned.)
	if not RESIZABLE_UI:
		return cmds.rowColumnLayout(tab_name, parent = parent, nc = 1, cw = [(1, WINDOW_WIDTH)])
	if tab_name in ('Check', 'Model'):
		# These tabs build their own scrollLayout; the formLayout stretches it to the window
		return cmds.formLayout(tab_name, parent = parent)
	# Other tabs stack their frames top to bottom: scroll area named after the tab, content column inside
	cmds.scrollLayout(tab_name, parent = parent, cr = True, hst = 0)
	return cmds.columnLayout(adj = True, rs = 0)

def get_saved_window_size():
	w = cmds.optionVar(q='hs_window_width') if cmds.optionVar(ex='hs_window_width') else WINDOW_WIDTH
	h = cmds.optionVar(q='hs_window_height') if cmds.optionVar(ex='hs_window_height') else WINDOW_HEIGHT
	if not RESIZABLE_UI:
		return WINDOW_WIDTH, WINDOW_HEIGHT
	return max(int(w), MIN_WINDOW_WIDTH), max(int(h), MIN_WINDOW_HEIGHT)

def save_window_size(*args):
	try:
		if RESIZABLE_UI and cmds.window(WINDOW_NAME, ex=True):
			w = cmds.window(WINDOW_NAME, q=True, w=True)
			h = cmds.window(WINDOW_NAME, q=True, h=True)
			if w >= MIN_WINDOW_WIDTH and h >= MIN_WINDOW_HEIGHT:
				cmds.optionVar(iv=['hs_window_width', int(w)])
				cmds.optionVar(iv=['hs_window_height', int(h)])
	except Exception:
		pass

def enable_width_scaling(window_name):
	# Phase 2: column widths follow the window width (see ui_resize.py). Original widths = design at MIN width.
	if not RESIZABLE_UI:
		return
	try:
		ui_resize.reset_window(window_name)
		if not ui_resize.install(window_name):
			cmds.warning('HSTool: window width scaling is unavailable (Qt hook failed, see Script Editor)')
		ui_resize.apply_scale(window_name)
	except Exception:
		pass

def set_window_min_size(window_name):
	# Never allow the window to be smaller than the original design (buttons would be clipped)
	if not RESIZABLE_UI:
		return
	try:
		try:
			from PySide2 import QtWidgets
			from shiboken2 import wrapInstance
		except ImportError:
			from PySide6 import QtWidgets
			from shiboken6 import wrapInstance
		import maya.OpenMayaUI as omui
		ptr = omui.MQtUtil.findControl(window_name)
		if ptr:
			widget = wrapInstance(int(ptr), QtWidgets.QWidget)
			top = widget.window()
			top.setMinimumSize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
	except Exception:
		pass
#endregion

def clear_old_ui():
	ui_resize.forget()
	if cmds.window(WINDOW_NAME, ex = True):
		save_window_size()
		cmds.deleteUI(WINDOW_NAME, window = True)

	if cmds.window('check_tool_window', ex=True):
		cmds.deleteUI('check_tool_window', window = True)
	if cmds.window('model_tool_window', ex=True):
		cmds.deleteUI('model_tool_window', window = True)
	if cmds.window('mirror_tool_window', ex=True):
		cmds.deleteUI('mirror_tool_window', window = True)
	if cmds.window('normal_tool_window', ex=True):
		cmds.deleteUI('normal_tool_window', window = True)
	if cmds.window('uv_tool_window', ex=True):
		cmds.deleteUI('uv_tool_window', window = True)
	if cmds.window('bake_tool_window', ex=True):
		cmds.deleteUI('bake_tool_window', window = True)

	if cmds.uiTemplate(TEMPLATE_NAME, ex=True):
		cmds.deleteUI(TEMPLATE_NAME, uiTemplate=True)

def create_tab(tab_name, layout):
	cmds.setUITemplate(TEMPLATE_NAME, pushTemplate=True)
	if tab_name == 'Check':
		create_check_tab(layout)
	elif tab_name == 'Model':
		create_model_tab(layout)
	elif tab_name == 'Mirror':
		create_mirror_tab(layout)
	elif tab_name == 'Normal':
		create_normal_tab(layout)
	elif tab_name == 'UV':
		create_uv_tab(layout)
	elif tab_name == 'Bake':
		create_bake_tab(layout)

def get_index_from_tab_name(tab_name):
	if tab_name == 'Check':
		return 1
	elif tab_name == 'Model':
		return 2
	elif tab_name == 'Mirror':
		return 3
	elif tab_name == 'Normal':
		return 4
	elif tab_name == 'UV':
		return 5
	elif tab_name == 'Bake':
		return 6

def get_current_frame_status(frame_layout, option_var):
	cmds.optionVar(iv=[option_var, cmds.frameLayout(frame_layout,q=True,cl=True)])

def return_to_tool_window(tab_name, tab_index):
	try:
		global tab_list
		# Create layout
		layout = create_tab_container(tab_name, 'main_tablayout')
		# Create Tab
		create_tab(tab_name, layout)

		# Change tab order
		num_of_tab = cmds.tabLayout('main_tablayout', q=True, nch=True)
		
		tab_list.append(tab_index)
		tab_list = list(set(tab_list))

		for index in range(0, len(tab_list)):
			if tab_list[index] == tab_index:
				cmds.tabLayout('main_tablayout', e=True, mt=[num_of_tab, index+1])
				break
		# Select Tab
		cmds.tabLayout('main_tablayout', e=True, sti=index+1)
		enable_width_scaling(WINDOW_NAME)
	except:
		pass

def detach_tab_to_window(*arg):
	global tab_list
	current_tab_name = cmds.tabLayout('main_tablayout', q=True, st=True)
	current_tab_index = get_index_from_tab_name(current_tab_name)
	tab_list.remove(current_tab_index)

	# Delete current tabLayout
	if cmds.layout(current_tab_name, ex=True):
		cmds.deleteUI(current_tab_name, layout = True)
	
	# Create child window
	child_window_name = current_tab_name.lower() + '_tool_window'
	child_window_tittle = current_tab_name + ' Tool'
	child_window = cmds.window(child_window_name, title = child_window_tittle, rtf=(not RESIZABLE_UI), mnb=False, mxb=False, s=RESIZABLE_UI, w=WINDOW_WIDTH, h=WINDOW_HEIGHT, cc=partial(return_to_tool_window, current_tab_name, current_tab_index))
	child_layout = create_tab_container(current_tab_name, child_window)
	create_tab(current_tab_name, child_layout)
	cmds.showWindow(child_window)
	set_window_min_size(child_window)
	enable_width_scaling(child_window)

def change_user_runtime_command_file():
	# Read root user command data
	root_runtime_command_file  = open(ROOT_RUNTIME_COMMAND_PATH, "r")
	root_runtime_command_content = root_runtime_command_file.read()
	root_runtime_command_file.close()

	# Check and update user command file
	local_runtime_command_file  = open(LOCAL_RUNTIME_COMMAND_PATH, "r+")
	local_runtime_command_content = local_runtime_command_file.read()

	# Get diff list
	local_runtime_command_list = local_runtime_command_content.split("runTimeCommand")
	root_runtime_command_list = root_runtime_command_content.split("runTimeCommand")
	different_runtime_command_list = list(set(root_runtime_command_list) - set(local_runtime_command_content))
	# Check root commmand in local file
	if root_runtime_command_content not in local_runtime_command_content:
		if len(different_runtime_command_list) != len(root_runtime_command_list):
			# Get HardSurfaceTool command in local File
			same_runtime_command_list = [command for command in root_runtime_command_list if command in local_runtime_command_list]
			# Delete old HardSurfaceTool command in local File 
			delete_part = "".join(same_runtime_command_list)
			local_runtime_command_content = local_runtime_command_content.replace(delete_part, "")
			local_runtime_command_file.seek(0)
			local_runtime_command_file.write(local_runtime_command_content)
			local_runtime_command_file.truncate()
		# Write root command in local File
		local_runtime_command_file.write(root_runtime_command_content)

	local_runtime_command_file.close()

def change_user_named_command_file():
	# Read root user command data
	root_named_command_file  = open(ROOT_NAMED_COMMAND_PATH, "r")
	root_named_command_content = root_named_command_file.read()
	root_named_command_file.close()

	# Check and update user command file
	local_named_command_file  = open(LOCAL_NAMED_COMMAND_PATH, "r+")
	local_named_command_content = local_named_command_file.read()

	# Get diff list
	local_named_command_list = local_named_command_content.split("nameCommand")
	root_named_command_list = root_named_command_content.split("nameCommand")
	different_named_command_list = list(set(root_named_command_list) - set(local_named_command_content))
	# Check root commmand in local file
	if root_named_command_content not in local_named_command_content:
		if len(different_named_command_list) != len(root_named_command_list):
			# Get HardSurfaceTool command in local File
			same_named_command_list = [command for command in root_named_command_list if command in local_named_command_list]
			# Delete old HardSurfaceTool command in local File 
			delete_part = "".join(same_named_command_list)
			local_named_command_content = local_named_command_content.replace(delete_part, "")
			local_named_command_file.seek(0)
			local_named_command_file.write(local_named_command_content)
			local_named_command_file.truncate()
		# Write root command in local File
		local_named_command_file.write(root_named_command_content)

	local_named_command_file.close()

def change_user_command_file(*arg):
	change_user_runtime_command_file()
	change_user_named_command_file()
	mel.eval("savePrefs -hk;")
	cmds.confirmDialog(icn="information", m = "Hotkeys has been updated! Please re-open Maya!")

def open_hotkey_editor(*arg):
	mel.eval("hotkeyEditorWindow;")

def get_readme_content(url):
	
	os.system(DATABASE_PATH + "/Install/Get_HardSurface_Tool_Maya_Version.bat")
	readme = "1111"
	return readme

#endregion

#region SETTING FUNCTION

def create_hs_tool_setting_file(path):
	# Write json file
	default_path = LOCAL_PATH + "/Model_Tools/Files/Temp.ma"

	dictionary = {
		"default_path": default_path,
		"ui": {"frame_color": [0.7, 0.3, 0.0],
		 		 "button_color": [0.4, 0.4, 0.4]
		}
	}
	# Serializing json 
	json_object = json.dumps(dictionary, indent = 4)
	# Writing to sample.json
	with open(path, "w") as outfile:
		outfile.write(json_object)
	outfile.close()
	return True

def read_data_from_json(path):
	json_data = {}
	try:
		with open(path, 'r') as file:
			json_data = json.load(file)
			file.close()
	except:
		pass
	return json_data

def save_ui_setting_to_json(json_path, key_name, value):
	data_json = read_data_from_json(json_path)
	for key in data_json['ui'].keys():
		if key == key_name:
			data_json['ui'][key] = value

	with open(json_path, 'w') as json_file:
		json.dump(data_json, json_file)

def change_frame_color(*arg):
	cmds.colorEditor(p=WINDOW_NAME)
	if cmds.colorEditor(q=True, r=True):
		values = cmds.colorEditor(q=True, rgb=True)
		save_ui_setting_to_json(LOCAL_SETTING_PATH, 'frame_color', values)
		cmds.frameLayout(defineTemplate=TEMPLATE_NAME, bgc=values)
		cmds.confirmDialog(icn="information", m = "Frame color has been changed! Please re-open Tool!")

def change_window_color(*arg):
	cmds.colorEditor(p=WINDOW_NAME)
	if cmds.colorEditor(q=True, r=True):
		values = cmds.colorEditor(q=True, rgb=True)
		save_ui_setting_to_json(LOCAL_SETTING_PATH,'window_color', values)
		cmds.window(defineTemplate=TEMPLATE_NAME, bgc=values)
		cmds.confirmDialog(icn="information", m = "Window color has been changed! Please re-open Tool!")

def change_button_color(*arg):
	cmds.colorEditor(p=WINDOW_NAME)
	if cmds.colorEditor(q=True, r=True):
		values = cmds.colorEditor(q=True, rgb=True)
		save_ui_setting_to_json(LOCAL_SETTING_PATH,'button_color', values)
		cmds.button(defineTemplate=TEMPLATE_NAME, bgc=values)
		cmds.confirmDialog(icn="information", m = "Button color has been changed! Please re-open Tool!")

def reset_tool_color(*arg):
	default_button_color = [0.4, 0.4, 0.4]
	default_frame_color = [0.7, 0.3, 0.0]
	default_window_color = [0.25, 0.25, 0.25]
	cmds.button(defineTemplate=TEMPLATE_NAME, bgc=default_button_color)
	save_ui_setting_to_json(LOCAL_SETTING_PATH,'button_color', default_button_color)
	cmds.frameLayout(defineTemplate=TEMPLATE_NAME, bgc=default_frame_color)
	save_ui_setting_to_json(LOCAL_SETTING_PATH,'frame_color', default_frame_color)
	cmds.window(defineTemplate=TEMPLATE_NAME, bgc=default_window_color)
	save_ui_setting_to_json(LOCAL_SETTING_PATH,'window_color', default_window_color)
	cmds.confirmDialog(icn="information", m = "Reset Color: Done! Please re-open Tool!")

def update_tool_for_maya(*arg):
	updater.check_for_updates_ui(TOOL_VERSION, silent=False)

def open_hs_tool_document(*arg):
	os.system('start ' + DOCUMENT_PATH)

def show_contact_information(*arg):
	cmds.confirmDialog(icn="information", m = "Contact: Canh Tran (shiro.tmc@gmail.com)")

def robocopy(source, des):
	#source is list full file name or folder
	#des is full folder path destination
	file = {}
	folder = []
	for f in source:
		if os.path.isfile(f):
			file[os.path.split(f)[1]] = os.path.split(f)[0]
		else:
			folder.append(f)
	folder_from_file = {}
	
	for key, value in iteritems(file):
		if value not in folder_from_file:
			folder_from_file[value] = [key]
		else:
			folder_from_file[value].append(key)
	cmd =  r"C:\Windows\System32\Robocopy.exe "
	if file:
		for k, v in iteritems(folder_from_file):
			cmd += '"' + k + '" "' + des + '" '
			for f in v:
				cmd += '"' + f + '" '
			cmd += "/Z" + " /MT"
			out = subprocess.call(cmd, shell = False)
			cmd = r"C:\Windows\System32\Robocopy.exe "
	if folder:
		for f in folder:
			cmd += '"' + f + '" "' + des + '/' + os.path.split(f)[1] + '"' + " /S" + " /Z" + " /MT"
			subprocess.call(cmd, shell = False)
			cmd = r"C:\Windows\System32\Robocopy.exe "
	return True

#endregion

#endregion