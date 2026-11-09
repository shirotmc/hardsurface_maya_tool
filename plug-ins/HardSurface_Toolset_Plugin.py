import os
import maya.OpenMayaMPx as OpenMayaMPx
import maya.cmds as cmds

usd = cmds.internalVar(usd=True)
# module_path = usd + '/module_path.txt'
# with open(module_path, 'r') as f:
#     mainModulePath = f.readlines()[0]

commandName = 'create_toolset'
try:
    from importlib import reload
except:
    pass
    
import sys
# HSTool root = parent of this plug-ins folder (self-locating, no fixed install path)
HSTOOL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace("\\", "/")
if HSTOOL_ROOT not in sys.path:
    sys.path.insert(0, HSTOOL_ROOT)

command = """
from HardSurface_Tool import HardSurfaceTool
try:
    from importlib import reload
except:
    pass

reload(HardSurfaceTool)
HardSurfaceTool.GUI()
"""

def createToolset():
    # import site

    # site.addsitedir(mainModulePath.replace('/', '\\'))
    # print (mainModulePath.replace('/', '\\'))

    import maya.cmds as cmds
    import maya.mel as mel

    # create a new tool disabled menu if one doesn't exist already.
    if cmds.menu("HardSurface_Tools", exists=True):
        cmds.deleteUI("HardSurface_Tools")
    sg_menu = cmds.menu("HardSurface_Tools", label="HardSurface_Tools", parent=mel.eval("$retvalue = $gMainWindow;"))
    cmds.menuItem(label="HardSurface Toolset", parent=sg_menu, c = command)

def cmdCreator():
    return OpenMayaMPx.asMPxPtr(createToolset())

def initializePlugin( mobject ):

    ''' Initialize the plug-in when Maya loads it. '''
    mplugin = OpenMayaMPx.MFnPlugin( mobject )
    try:
        mplugin.registerCommand( commandName, cmdCreator() )
    except:
        print( 'Failed to register command HS_Tools' )

def uninitializePlugin( mobject ):
    ''' Uninitialize the plug-in when Maya un-loads it. '''
    mplugin = OpenMayaMPx.MFnPlugin( mobject )
    try:
        mplugin.deregisterCommand( commandName )
    except:
        print( 'Failed to unregister command HS_Tools' )