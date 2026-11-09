//Maya ASCII 2020 scene
//Name: Debug_Mesh.ma
//Last modified: Fri, Jun 09, 2023 03:00:29 PM
//Codeset: 1252
requires maya "2020";
requires -nodeType "colorCondition" "lookdevKit" "1.0";
requires "stereoCamera" "10.0";
requires "mtoa" "3.1.2.1";
currentUnit -l centimeter -a degree -t film;
fileInfo "application" "maya";
fileInfo "product" "Maya 2020";
fileInfo "version" "2020";
fileInfo "cutIdentifier" "202011110415-b1e20b88e2";
fileInfo "osv" "Microsoft Windows 10 Technical Preview  (Build 19045)\n";
fileInfo "UUID" "05CD8CFE-4275-ADF5-5B6C-2A9ADC36F05B";
createNode blinn -n "Debug_Shader";
	rename -uid "92C2C59D-4FD0-53CE-CB90-D69473C0027A";
createNode colorCondition -n "colorCondition1";
	rename -uid "94DB29F4-4842-4A8E-6724-3ABAC619BD3E";
	setAttr "._cb" -type "float3" 0.0517 0.0517 0.0517 ;
createNode samplerInfo -n "samplerInfo1";
	rename -uid "63748BB4-4E9E-7525-1F7F-1EB3A93CCBC9";
select -ne :time1;
	setAttr ".o" 0;
select -ne :hardwareRenderingGlobals;
	setAttr ".otfna" -type "stringArray" 22 "NURBS Curves" "NURBS Surfaces" "Polygons" "Subdiv Surface" "Particles" "Particle Instance" "Fluids" "Strokes" "Image Planes" "UI" "Lights" "Cameras" "Locators" "Joints" "IK Handles" "Deformers" "Motion Trails" "Components" "Hair Systems" "Follicles" "Misc. UI" "Ornaments"  ;
	setAttr ".otfva" -type "Int32Array" 22 0 1 1 1 1 1
		 1 1 1 0 0 0 0 0 0 0 0 0
		 0 0 0 0 ;
	setAttr ".fprt" yes;
select -ne :renderPartition;
	setAttr -s 3 ".st";
select -ne :renderGlobalsList1;
select -ne :defaultShaderList1;
	setAttr -s 6 ".s";
select -ne :postProcessList1;
	setAttr -s 2 ".p";
select -ne :defaultRenderUtilityList1;
	setAttr -s 2 ".u";
select -ne :defaultRenderingList1;
select -ne :initialShadingGroup;
	setAttr ".ro" yes;
select -ne :initialParticleSE;
	setAttr ".ro" yes;
select -ne :defaultResolution;
	setAttr ".pa" 1;
select -ne :hardwareRenderGlobals;
	setAttr ".ctrs" 256;
	setAttr ".btrs" 512;
connectAttr "colorCondition1.oc" "Debug_Shader.c";
connectAttr "samplerInfo1.fn" "colorCondition1._cnd";
connectAttr "Debug_Shader.msg" ":defaultShaderList1.s" -na;
connectAttr "colorCondition1.msg" ":defaultRenderUtilityList1.u" -na;
connectAttr "samplerInfo1.msg" ":defaultRenderUtilityList1.u" -na;
connectAttr "colorCondition1.oc" ":internal_soloShader.ic";
// End of Debug_Mesh.ma
