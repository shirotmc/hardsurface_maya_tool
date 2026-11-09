
import maya.cmds as cmds
import math

#-------------------#
#     MatchUV UI        #
#-------------------#
def sortDist(tuple):
	return tuple[1]

def getOtherUVS(allSelected,suvs):
	objects = [i.split('.')[0] for i in allSelected]
	objects = [i for i in set(objects)]
	uvs = cmds.ls(cmds.polyListComponentConversion(objects,tuv=True),fl=True)
	return sorted(set.difference(set(uvs)-set(suvs)))

def matchUVs():
	maxDist = 0.15


	### SETUP ###
	allSelected = cmds.ls(sl = True)
	# Create list of uvs
	suvs = cmds.ls(cmds.polyListComponentConversion(tuv=True), fl=True)
	ouvs= getOtherUVS(allSelected,suvs)

	# Create list of positions
	spos = [cmds.polyEditUV(i,query=True) for i in suvs]
	opos = [cmds.polyEditUV(i,query=True) for i in ouvs]

	### PERFORM ###
	for i in range(len(suvs)):
		withinRange = []
		for j in range(len(ouvs)):
			x = spos[i][0]-opos[j][0]
			y = spos[i][1]-opos[j][1]
			dist =  math.sqrt((x**2) + (y**2))
			if dist < maxDist:
				withinRange.append((opos[j],dist))

		withinRange = sorted(withinRange,key=sortDist)
		if len(withinRange):
			cmds.polyEditUV(suvs[i],u=withinRange[0][0][0],v=withinRange[0][0][1],relative=False)
	return