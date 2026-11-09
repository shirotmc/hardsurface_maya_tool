import maya.cmds as cmds
import maya.mel as mel

#region PIVOT SETTING
def bake_pivot(*arg):
    mel.eval('BakeCustomPivot;')

def freeze_transforms(*arg):
    mel.eval('FreezeTransformations;')

def reset_pivot(*arg):
    mel.eval('ResetTransformations;')

#endregion

#region FLIP

def flip_geometry(sx, sy, sz):
    selected_objects = cmds.ls(sl=True)
    pivot_list = []
    for obj in selected_objects:
            pos = cmds.xform(obj, q=True, rp=True, ws=True)
            pivot_list.append(pos)

    if (len(selected_objects)== 0):
        cmds.confirmDialog(icn = 'warning', m = 'Please select object!')
        return False
    
    mirror_space = cmds.radioButtonGrp('mirror_setting_rbg', q=True, sl=True)
    mirror_uv_value = cmds.checkBox('mirror_uv_cb', q=True, v=True)


    if mirror_space == 1:
        cmds.xform(os=True, piv= [0, 0, 0])
        cmds.scale(sx, sy, sz, r=True)
        for i in range(0, len(selected_objects)):
            pivot_pos = pivot_list[i]
            cmds.move(pivot_pos[0]*sx, pivot_pos[1]*sy, pivot_pos[2]*sz, selected_objects[i] +".scalePivot", selected_objects[i] +".rotatePivot", absolute=True)
    else:
        cmds.scale(sx, sy, sz, r=True)


    mel.eval('FreezeTransformations;')
    mel.eval('SelectToggleMode;')
    mel.eval('SelectToggleMode;')
    cmds.select(hierarchy=True)
    
    cmds.select(selected_objects)
    
    if (mirror_uv_value == 1):
        cmds.select(hierarchy=True)
        cmds.select( "*Shape*",deselect=True)
        cmds.polyForceUV(flipHorizontal=True, local=True)
        cmds.performPolyMergeUV(0)
    
    mel.eval('DeleteHistory;')

def flip_X(*arg):
    flip_geometry(-1, 1, 1)

def flip_Y(*arg):
    flip_geometry(1, -1, 1)

def flip_Z(*arg):
    flip_geometry(1, 1, -1)

#endregion

#region MIRROR
def mirror_geometry(sx, sy, sz):
    selected_objects = cmds.ls(sl=True)

    if (len(selected_objects)== 0):
        cmds.confirmDialog(icn = 'warning', m = 'Please select object!')
        return False
    
    mirror_space = cmds.radioButtonGrp('mirror_setting_rbg', q=True, sl=True)
    mirror_uv_value = cmds.checkBox('mirror_uv_cb', q=True, v=True)
    
    for obj in selected_objects:
        dup_obj = cmds.duplicate(obj)[0]
        pivot_pos = cmds.xform(obj, q=True, rp=True, ws=True)
        if mirror_space == 1:
            cmds.scale(sx, sy, sz, dup_obj, pivot=(0,0,0), a=True)
            cmds.move(pivot_pos[0]*sx, pivot_pos[1]*sy, pivot_pos[2]*sz, dup_obj +".scalePivot", dup_obj +".rotatePivot", absolute=True)
        else:
            cmds.scale(sx, sy, sz, dup_obj, pivot=pivot_pos, a=True)

    mel.eval('FreezeTransformations;')
    mel.eval('SelectToggleMode;')
    mel.eval('SelectToggleMode;')
    cmds.select(hierarchy=True)
    
    cmds.select(selected_objects)
    
    if (mirror_uv_value == 1):
        cmds.select(hierarchy=True)
        cmds.select( "*Shape*",deselect=True)
        cmds.polyForceUV(flipHorizontal=True, local=True)
        cmds.performPolyMergeUV(0)
    
    mel.eval('DeleteHistory;')

def mirror_X(*arg):
    mirror_geometry(-1, 1, 1)

def mirror_Y(*arg):
    mirror_geometry(1, -1, 1)

def mirror_Z(*arg):
    mirror_geometry(1, 1, -1)

#endregion

#region MIRROR INSTANCE
def mirror_instance_geometry(sx, sy, sz):
    selected_objects = cmds.ls(sl=True)

    if (len(selected_objects)== 0):
        cmds.confirmDialog(icn = 'warning', m = 'Please select object!')
        return False
    
    mirror_space = cmds.radioButtonGrp('mirror_setting_rbg', q=True, sl=True)

    for obj in selected_objects:
        dup_obj = cmds.instance(obj)[0]
        pivot_pos = cmds.xform(obj, q=True, rp=True, ws=True)
        if mirror_space == 1:
            cmds.scale(sx, sy, sz, dup_obj, pivot=(0,0,0), a=True)
            cmds.move(pivot_pos[0]*sx, pivot_pos[1]*sy, pivot_pos[2]*sz, dup_obj +".scalePivot", dup_obj +".rotatePivot", absolute=True)
        else:
            cmds.scale(sx, sy, sz, dup_obj, pivot=pivot_pos, a=True)

    mel.eval('FreezeTransformations;')
    for obj in selected_objects:
        mel.eval('SelectToggleMode;')
        mel.eval('SelectToggleMode;')
    mel.eval('DeleteHistory;')

def mirror_instance_X(*arg):
    mirror_instance_geometry(-1, 1, 1)

def mirror_instance_Y(*arg):
    mirror_instance_geometry(1, -1, 1)

def mirror_instance_Z(*arg):
    mirror_instance_geometry(1, 1, -1)

#endregion

#region MIRROR MERGE
def mirror_merge(dir):
    mirror_merge_value = cmds.floatField('merge_tolerance_ff', q=True, v=True)
    selected_objects = cmds.ls(sl=True)
    mel.eval('PolySelectConvert 1;')
    selected_face = cmds.ls(sl=True)
    
    cmds.select(selected_objects)
    
    if (len(selected_objects)== 0):
        cmds.confirmDialog(icn = 'warning', m = 'Please select object!')
        return False
    
    mirror_space = cmds.radioButtonGrp('mirror_setting_rbg', q=True, sl=True)
    mirror_uv_value = cmds.checkBox('mirror_uv_cb', q=True, v=True)
    
    cmds.select(hierarchy=True)
    cmds.select( "*Shape*",deselect=True)
    selected_object_hierarchy = cmds.ls(sl=True)
    
    for obj in selected_object_hierarchy:
        opposite = obj + ".opposite"
        
        if cmds.objExists(opposite): # to bypass error on group nodes
            cmds.select(obj)
            object_center = list(cmds.getAttr (obj + ".rotatePivot")[0])
            if (mirror_space == 1):
                cmds.polyMirrorFace(ws=True, d=dir, mm=1, mergeThresholdType=1, mt=mirror_merge_value)
            else:
                mel.eval('channelBoxCommand -freezeScale;')
                cmds.polyMirrorFace(p=(object_center[0], object_center[1], object_center[2]), d=dir, mm=1, mergeThresholdType=1, mt=mirror_merge_value)

            mel.eval('SelectToggleMode;')
            mel.eval('SelectToggleMode;')
            
            if (mirror_space == 1):
                mel.eval('CenterPivot;')
    
    if (mirror_uv_value == 1):
        cmds.select(selected_objects)
        mel.eval('PolySelectConvert 1;')
        cmds.select(selected_face, deselect=True)
        cmds.polyForceUV(flipHorizontal=True, local=True)
        cmds.performPolyMergeUV(0)
    
    cmds.select(selected_objects)

def mirror_merge_X_pos(*args):
    mirror_merge(0)

def mirror_merge_X_neg(*args):
    mirror_merge(1)

def mirror_merge_Y_pos(*args):
    mirror_merge(2)

def mirror_merge_Y_neg(*args):
    mirror_merge(3)

def mirror_merge_Z_pos(*args):
    mirror_merge(4)

def mirror_merge_Z_neg(*args):
    mirror_merge(5)
#endregion

#region MIRROR CUT
def mirror_cut(*arg):
    selected_objects = cmds.ls(sl=True)
    
    if (len(selected_objects)== 0):
        cmds.confirmDialog(icn = 'warning', m = 'Please select object!')
        return False

    for obj in selected_objects:
        cmds.select(obj)
        mel.eval('MirrorCutPolygonGeometry;')
#endregion

#region REVOLVE
def revolve(dir):
    selected_objects = cmds.ls(sl=True)
    revolve_count = cmds.intField('revolve_count_if', q=True, v=True)
    is_instance = cmds.checkBox('revolve_instance_cb', q=True, v=True)
    mirror_space = cmds.radioButtonGrp('mirror_setting_rbg', q=True, sl=True)

    rotation = (360.0/revolve_count)
    
    if (is_instance == 0):
        cmds.duplicate(rr=True)
    else:
        cmds.instance()
    
    if (mirror_space == 1):
        # revolve in world space
        if (dir == 0):
            cmds.rotate(rotation, 0, 0, r=True)
        if (dir == 1):
            cmds.rotate(0, rotation, 0, r=True)
        if (dir == 2):
            cmds.rotate(0, 0, rotation, r=True)
    else:
        # revolve in object space
        
        if (dir == 0):
            cmds.rotate(rotation, 0, 0, r=True, os=True)
        if (dir == 1):
            cmds.rotate(0, rotation, 0, r=True, os=True)
        if (dir == 2):
            cmds.rotate(0, 0, rotation, r=True, os=True)
    
    for i in range(1,revolve_count-1):
        if (is_instance == 0):
            cmds.duplicate(rr=True, st=True)
        else:
            cmds.instance(st=True)
    cmds.select(selected_objects)


def revolve_X(*arg):
    revolve(0)

def revolve_Y(*arg):
    revolve(1)

def revolve_Z(*arg):
    revolve(2)

#endregion