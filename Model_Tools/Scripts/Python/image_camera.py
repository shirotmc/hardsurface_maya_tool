import maya.cmds as cmds
import maya.mel as mel
import sys, os

FRAME_BGC = [0.2, 0.1, 0.4]

def fnHelp(*args):
	os.startfile(r'\\virtuosgames.com\geh\TOOLS\Technical_Script\Projects\Hard_Surface\General_Tool\Document\ImageCamera\HuongDanSuDung_ImageCam.htm')

def getPathByTextField(*arg):
	textFieldDir = cmds.textField('textDir',q=True,text=True)

def getPathByDialog(*arg):        
	dialogDir = cmds.fileDialog2(fileMode=2, dialogStyle=2,returnFilter=True)
	cmds.textField('textDir',edit=True,text=dialogDir[0])

def getPathByDefault():
	sceneName = cmds.file(q=True,sn=True)
	carName = sceneName.split("/")[-1].split(".")[0]
	imagePath = sceneName.split(carName)[0] + carName + "/ImageCamera"
	return imagePath

def GetAllCamera(type):
	allCameras=[]
	OriginalCam = ['front','left','persp','side','top']
	ImageCam = ['']
	getAllCam = cmds.ls(cameras=True)
	if getAllCam:
		for cam in getAllCam:
			# nameCam = cam.split('Shape')[0]+cam.split('Shape')[-1]
			nameCam = cmds.listRelatives(cam,p=True)[0]
			if type == 'all':
				if nameCam not in OriginalCam:
					allCameras.append(nameCam)
			elif type =='imageCam':
				if 'ImageCameraFrame' in nameCam or 'MainCamera' in nameCam:
					allCameras.append(nameCam)
	return allCameras

def geNE_CameraSequencer(*args):
	matching_camera_list = []

	for cam in cmds.ls(type="camera" , long = True , flatten = True):
		if( ("persp" not in cam) and ("top" not in cam) and ("front" not in cam) and ("side" not in cam) ) :
			matching_camera_list.append(cam)

			cmds.setAttr(cam  + ".nearClipPlane" , 0.001)
			cmds.setAttr(cam  + ".farClipPlane" , 100000)
	mel.eval('SequenceEditor;')
	if cmds.ls(type = 'shot'):    
		return
	for cam_number in range(len(matching_camera_list)) : 
		cam_name = matching_camera_list[cam_number].split('|')[-1]
		cam_name = cam_name.replace('Shape' , '')
		
		cam_end_frame = 5*(cam_number + 1)
		cam_start_frame = cam_end_frame - 4
		
		cmds.shot(shotName = cam_name , currentCamera = matching_camera_list[cam_number] ,sequenceStartTime = cam_start_frame , sequenceEndTime = cam_end_frame)

def geNFS_SwapImageCam(_):
	index = int(cmds.intSliderGrp('campSlider',q=True,value=True))-1
	allCamera = GetAllCamera('all')
	
	camParent = allCamera[0]
	cmds.lookThru(allCamera[index])
	mel.eval('manipMoveContext -edit -mode 0 Move;')
	fnCreateCustomCam()


def setImagePlaneToFill(*args):
	imagePlane_list = cmds.ls(type = 'imagePlane' , long = True , flatten = True)
	for scene_imagePlane in imagePlane_list :
		try :
			cmds.setAttr("%s.fit"%scene_imagePlane , 0)
		except :
			pass

def DoDoubleClick(*arg):
	#Double Click Text Scroll List To Look Thru Cam
	selectedCam = cmds.textScrollList('textScrollCam',query=True,selectItem=True)
	cmds.lookThru(selectedCam[0])
	# cmds.lookThru('persp')

def DoDeleteAllImaCam(*arg):
	#delete all image Cam
	ImageCam = GetAllCamera('imageCam')
	cmds.delete(ImageCam)
	#reload camp
	ReloadPerspective()

def DoDeleteSelImaCam(*arg):
	#delete all image Cam
	selectedCam = cmds.textScrollList('textScrollCam',query=True,selectItem=True)
	cmds.delete(selectedCam)
	#reload camp
	ReloadPerspective()

def DoTearOff(*arg):
	selectedCam = cmds.textScrollList('textScrollCam',query=True,selectItem=True)
	
	cmds.lookThru(selectedCam[0])
	focusPanel =  cmds.getPanel( withFocus=True )
	cmds.panel(focusPanel,e=True,tearOffCopy=True)

def ReloadPerspective(*arg):
	#Reload the TextScrollList
	ImageCam = GetAllCamera('imageCam')
	cmds.textScrollList('textScrollCam',edit=True,removeAll =True )
	cmds.textScrollList('textScrollCam',edit = True,append =ImageCam )

def doRenameImage(*arg):
	#Rename Image in folder and change type
	path = cmds.textField('textDir',q=True,text=True)
	if path == "":
		path = getPathByDefault()
	allImage = os.listdir(path)
	try:
		for index in range(len(allImage)):
			newName = str(str(index+1) +'.jpg')
			os.rename(path+'/'+allImage[index+1],path+'/'+newName)
	except:
		pass
	
	allImage = sorted(os.listdir(path))
	allCamera = GetAllCamera('all')
	for index in range(len(allCamera)):
		newName = allCamera[index] +'_' + str(index+1)
		cmds.rename(allCamera[index],newName) 


def geNFS_ReLinkImageCam(_):
	allCamera = GetAllCamera('all')
	for camera in allCamera:
		child = cmds.listRelatives(camera,children=True)
		children = cmds.listRelatives(child,children=True,fullPath=True)
		cmds.delete(children)
	geNFS_LinkCameraAndImage(_)

def geNFS_LinkCameraAndImage(_):
	index = int(cmds.intSliderGrp('campSlider',q=True,value=True))-1
	allAttr = ["translateX","translateY","translateZ","rotateX","rotateY","rotateZ","scaleX","scaleY","scaleZ",
			   "horizontalFilmAperture","verticalFilmAperture",
			   "focalLength","focusDistance","centerOfInterest"]
	path = cmds.textField('textDir',q=True,text=True)
	allCamera = GetAllCamera('all')
	camParent = allCamera[0]
	for camera in allCamera:
		for attr in allAttr:
			cmds.setAttr(camera+'.'+attr, lock=True)
		
		image = camera + '.jpg'
		ImagePlane = cmds.imagePlane(camera = camera, fileName = path + "/" + image, name = "Image")
		ImageShape = cmds.listRelatives(ImagePlane, children = True)
		try:
			cmds.select(ImageShape)
			mel.eval("setAttr "+ ImageShape[0]+".displayOnlyIfCurrent on;optionMenu -edit -enable true AELookThroughCameraMenu;")
			mel.eval("AEchangeLookThroughCamera "+ ImageShape[0]+";")
			
		except:
			# cmds.warning( "need to do it manually")
			pass
		# cmds.setAttr(ImageShape[0] +".useFrameExtension",1)
		cmds.setAttr(ImageShape[0] +".depth", 500)

	cmds.lookThru(camParent)
	geNE_CameraSequencer()
	# cmds.deleteUI()

def GE_NE_ChangeImagePlaneFit(_):
	fit_value = 0 # as default is Fill
	selected_imagePlane_fit = cmds.optionMenu('ImagePlane_Placement_Fit_Options' , q = True , value = True)
	if selected_imagePlane_fit == "Best":
		fit_value = 1
	elif selected_imagePlane_fit == "Horizontal":
		fit_value = 2
	elif selected_imagePlane_fit == "Vertical":
		fit_value = 3
	elif selected_imagePlane_fit == "To Size":
		fit_value = 4

	imagePlane_list = cmds.ls(type = 'imagePlane' , long = True , flatten = True)
	for scene_imagePlane in imagePlane_list :
		try :
			cmds.setAttr("%s.fit"%scene_imagePlane , fit_value)
		except :
			pass

def geNFS_LookThruPersp(_):
	cmds.lookThru('persp')

def geNFS_HideUnselected(_):
	mel.eval('HideUnselectedObjects;')
	cmds.setAttr('ImageCam.visibility',1)

def geNFS_NextCam(_):
	index = int(cmds.intSliderGrp('campSlider',q=True,value=True)) 
	cmds.intSliderGrp('campSlider',e=True,value=index+1)
	geNFS_SwapImageCam(_)

def geNFS_PreviousCam(_):
	index = int(cmds.intSliderGrp('campSlider',q=True,value=True)) 
	if index -1 ==0:
		pass
	else:
		cmds.intSliderGrp('campSlider',e=True,value=index-1)
		geNFS_SwapImageCam(_)

def xray_selected_objects(*args):
	select_objects = cmds.ls(sl=True, l=True)
	if len(select_objects) >= 1:
		selected = cmds.ls(sl=True, dag=True, s=True)
		for s in selected:
			x_state = cmds.displaySurface(s, xRay=True, query=True)[0]
			cmds.displaySurface(s, xRay=(not x_state))
	if len(select_objects) < 1:
		all = cmds.select(ado=True)
		cmds.displaySurface(xRay=False)
		cmds.select(cl=True)
		current_panel = cmds.getPanel(wf=True)
		mode = cmds.modelEditor(current_panel, q=True, xray=True)
		cmds.modelEditor(current_panel, e=True, xray=(not mode))

def fnGetCurrentPanel(*args):
	viewports = cmds.getPanel(type='modelPanel')
	visible = cmds.getPanel(vis=True)
	active_panel = ''

	for i in viewports:
		if i in visible:
			active_panel = i
	viewport_cam = cmds.modelPanel(active_panel, q=True, camera=True)

	return viewport_cam

def fnSetImagePlaneDepth(*args):
	depth = cmds.intField('IPDepth', q=True, v=True)
	imagePlane_list = cmds.ls(type = 'imagePlane' , long = True , flatten = True)
	for img in imagePlane_list:
		cmds.setAttr(img +".depth", depth)

def fnCreateCustomCam(*args):
	cam_rot = [0, 0, 0]
	cam_index = cmds.intSliderGrp('campSlider', q=True, v=True) - 1
	camera_list = GetAllCamera('all')
	allCamAttr = ["translateX","translateY","translateZ","rotateX","rotateY","rotateZ","scaleX","scaleY","scaleZ",
			   "horizontalFilmAperture","verticalFilmAperture",
			   "focalLength","focusDistance","centerOfInterest"]
	current_cam = camera_list[cam_index]

	plane = cmds.polyPlane(name='image_camera_plane', w=1, h=1, sx=10 , sy=10 ,ax=[0, 0, 1],  cuv =2,  ch=1)
	cmds.setAttr(plane[0] + ".rotateOrder", 2)
	cmds.orientConstraint(current_cam, plane[0], offset= [0 ,0, 0] ,skip= 'none', weight=1)
	
	plane = [p for p in cmds.ls(g=True, dag=True) if 'image_camera_plane' in p.lower()]
	mesh = list(set([m for m in cmds.ls(g=True, dag=True)]) - set(plane))
	
	mesh = cmds.listRelatives(mesh, p=True)
	plane = cmds.listRelatives(plane[0], p=True)

	cmds.select(mesh)
	cmds.select(plane, add=True)
	copyPivot()
	cmds.delete(plane)
	
def copyPivot(*args):
	sourceObj = cmds.ls(sl = True)[len(cmds.ls(sl = True))-1]
	targetObj = cmds.ls(sl = True)[0:(len(cmds.ls(sl = True))-1)]
	
	parentList = []
	for obj in targetObj:
		if cmds.listRelatives( obj, parent = True):
			parentList.append(cmds.listRelatives( obj, parent = True)[0])
		else:
			parentList.append('')

	pivotTranslate = cmds.xform (sourceObj, q = True, ws = True, rotatePivot = True)
	cmds.parent(targetObj, sourceObj)
	cmds.makeIdentity(targetObj, a = True, t = True, r = True, s = True)
	cmds.xform (targetObj, ws = True, pivots = pivotTranslate)
	for ind in range(len(targetObj)):
		if parentList[ind] != '' : 
			cmds.parent(targetObj[ind], parentList[ind])
		else:
			cmds.parent(targetObj[ind], world = True)

def GUI(parent_window):
	if cmds.window('CreateCamera', ex = True):
		cmds.deleteUI('CreateCamera', window = True)
	if cmds.windowPref('CreateCamera', exists=True):
		cmds.windowPref('CreateCamera', remove=True)

	window = cmds.window('CreateCamera', title = 'Image Camera', p = parent_window, rtf = True, mnb = False, mxb = False)
	cmds.columnLayout()

	cmds.button(l='Help', w=400, c=fnHelp)

	cmds.rowColumnLayout(nc=2, adj=1, w=400)
	cmds.textField('textDir', cc=getPathByTextField)
	cmds.button(l='Open', c=getPathByDialog)
	cmds.setParent('..')

	cmds.frameLayout('Display', cl=False, cll=True, w=400, bgc=FRAME_BGC)
	cmds.columnLayout(adj=True)
	cmds.button(l='Toggle X-ray On Selection', h=50, c=xray_selected_objects)
	cmds.separator()
	cmds.setParent('..')
	cmds.setParent('..')

	cmds.frameLayout('Create Image Camera', cl=False, cll=True, w=400, bgc=FRAME_BGC)
	cmds.button(l='Rename Image', h=40, c= doRenameImage)
	cmds.button(l='Link Image Cam', h=40, c=geNFS_LinkCameraAndImage)
	cmds.button(l='Relink Image Cam', h=40, c=geNFS_ReLinkImageCam)
	cmds.button(l='Camera Sequencer', h=40, c=geNE_CameraSequencer)
	cmds.setParent('..')

	cmds.frameLayout('Testing', cl=False, cll=True, w=400, bgc=FRAME_BGC)
	cmds.rowColumnLayout(nc=2, adj=2)
	
	cmds.columnLayout()
	cmds.rowLayout(nc=2, adj=True)
	cmds.button('prev', l='<', w=60, h=40, c= geNFS_PreviousCam)
	cmds.button('next', l='>', w=60, h=40, c= geNFS_NextCam)
	cmds.setParent('..')
	cmds.rowLayout(nc=2, adj=True)
	cmds.button('persp', l='Persp', w=60, h=40, c= geNFS_LookThruPersp)
	cmds.button('hide', l='Hide', w=60, h=40, c= geNFS_HideUnselected)
	cmds.setParent('..')

	cmds.rowLayout(nc=2, adj=True)
	cmds.optionMenu('ImagePlane_Placement_Fit_Options' , label = 'Fit :' )
	cmds.menuItem(label = 'Fill')
	cmds.menuItem(label = 'Best')
	cmds.menuItem(label = 'Horizontal')
	cmds.menuItem(label = 'Vertical')
	cmds.menuItem(label = 'To Size')
	cmds.setParent('..')

	cmds.rowLayout(nc=2, adj=True)
	cmds.button(l='Set Fit', h=40, w=123, c=GE_NE_ChangeImagePlaneFit)
	cmds.setParent('..')

	cmds.setParent('..')

	cmds.columnLayout(adj=True)
	allCameras= GetAllCamera('all')
	camLen = len(allCameras)
	cmds.rowLayout(nc=3, adj=True)
	cmds.text(l='Image Plane Depth: ')
	cmds.intField('IPDepth', v=10, w=100)
	cmds.button(l='Set Depth', c=fnSetImagePlaneDepth)
	cmds.setParent('..')
	cmds.separator(h=50, style='out')
	cmds.intSliderGrp('campSlider', field=True, label='Camera Slider', cl3=['left', 'center', 'right'], cw3=[70, 30, 150], minValue=1, maxValue=camLen, fieldMinValue=0, fieldMaxValue=camLen, value=1 ,dragCommand =geNFS_SwapImageCam,vcc =geNFS_SwapImageCam)
	cmds.separator(h=50, style='out')
	cmds.setParent('..')

	cmds.setParent('..')
	cmds.setParent('..')

	cmds.setParent('..')
	cmds.showWindow('CreateCamera')
