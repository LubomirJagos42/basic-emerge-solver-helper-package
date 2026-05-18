import emerge as em
import emerge._emerge.geometry as emergeGeo
from typing import Callable
import gmsh
import os

class EMergeHelperFunctions:
    simulationObj = None
    materialList = {}

    def __init__(self, simulationObj):
        self.simulationObj = simulationObj
        print("EMerge helper created")

    def getAllObjectByName(self, name: str):
        resultObjList = []
        for geometryObj in self.simulationObj.state.manager.geometry_list[self.simulationObj.modelname].values():
            if geometryObj.name == name or geometryObj.name.startswith(name+"_"):
                resultObjList.append(geometryObj)

        return resultObjList

    def getObjectSurface(self, name: str):
        boundaryObjList = []
        for geometryObj in self.simulationObj.state.manager.geometry_list[self.simulationObj.modelname].values():
            if geometryObj.name == name or geometryObj.name.startswith(name+"_"):
                if isinstance(geometryObj, emergeGeo.GeoSurface):
                    boundaryObjList.append(geometryObj)
                else:
                    boundaryObjList.append(geometryObj.boundary())

        return boundaryObjList

    def getObjectVolume(self, name: str):
        resultObjList = []
        for geometryObj in self.simulationObj.state.manager.geometry_list[self.simulationObj.modelname].values():
            if geometryObj.name == name or geometryObj.name.startswith(name+"_"):
                if isinstance(geometryObj, emergeGeo.GeoVolume):
                    resultObjList.append(geometryObj)

        return resultObjList

    def importStepFile(self, name:str, filename:str,directory:list[str] | str = "", unit:float=1.0, priority:int=-1, materialName:str = ""):
        targetDirectory:str = ""
        if directory != "" and directory != []:
            if type(directory) == str:
                targetDirectory = directory
            elif type(directory) == list:
                for dirName in directory:
                    targetDirectory = os.path.join(targetDirectory, dirName)

        stepObjectGroup = em.geo.step.STEPItems(name=name, filename=os.path.join(targetDirectory, filename), unit=unit)

        for geoObj in stepObjectGroup.objects:
            geoObj.prio_set(priority)
            if materialName != "":
                geoObj.set_material(self.materialList[materialName])

    def setObjSize(self, name:str, size:float):
        objectList = self.getAllObjectByName(name)
        for obj in objectList:
            self.simulationObj.mesher.set_size(obj, size)

    def setObjBoundarySize(self, name:str, size:float):
        objectList = self.getObjectSurface(name)
        for obj in objectList:
            self.simulationObj.mesher.set_boundary_size(obj, size)

    def setObjFaceSize(self, name:str, size:float):
        objectList = self.getObjectSurface(name)
        for obj in objectList:
            self.simulationObj.mesher.set_face_size(obj, size)

    def setObjVolumeSize(self, name:str, size:float):
        objectList = self.getObjectVolume(name)
        for obj in objectList:
            self.simulationObj.mesher.set_domain_size(obj, size)

    def setLumpedElementToObject(
        self,
        name: str,
        impedance_function: Callable | None = None,
        width: float | None = None,
        height: float | None = None,
    ):
        objectList = self.getObjectSurface(name)
        for obj in objectList:
            self.simulationObj.mw.bc.LumpedElement(face=obj, impedance_function=impedance_function, width=width, height=height)

    def setBoundaryConditionToObject(self, name: str, type: str):
        objectList = self.getObjectSurface(name)
        for obj in objectList:
            if type.lower() == "absorbing":
                self.simulationObj.mw.bc.AbsorbingBoundary(obj)
            elif type == "PEC":
                self.simulationObj.mw.bc.PEC(obj)
            elif type == "PMC":
                self.simulationObj.mw.bc.PMC(obj)
            else:
                raise Exception(f"ERROR: Unknown type of boundary condition: {type}")

    def createGmshNamedGroup(self, geometryObjName: str, groupName: str, groupTag: int = -1, useBoundary: bool = False, useSuffixToRecognizeGeometryName: bool = True):
        objectTag1DList = []
        objectTag2DList = []
        objectTag3DList = []

        for geometryObj in self.simulationObj.state.manager.geometry_list[self.simulationObj.modelname].values():
            if geometryObj.name == geometryObjName or geometryObj.name.startswith(geometryObjName + ('_' if useSuffixToRecognizeGeometryName else '')):
                for tagTuple in (geometryObj.boundary().dimtags if (useBoundary and not isinstance(geometryObj, emergeGeo.GeoSurface)) else geometryObj.dimtags):
                    if tagTuple[0] == 1:
                        objectTag1DList.append(tagTuple[1])
                    if tagTuple[0] == 2:
                        objectTag2DList.append(tagTuple[1])
                    if tagTuple[0] == 3:
                        objectTag3DList.append(tagTuple[1])

        if groupTag > -1:
            gmsh.model.addPhysicalGroup(1, objectTag1DList, name=groupName, tag=groupTag)
            gmsh.model.addPhysicalGroup(2, objectTag2DList, name=groupName, tag=groupTag + 1)
            gmsh.model.addPhysicalGroup(3, objectTag3DList, name=groupName, tag=groupTag + 2)
        else:
            gmsh.model.addPhysicalGroup(1, objectTag1DList, name=groupName)
            gmsh.model.addPhysicalGroup(2, objectTag2DList, name=groupName)
            gmsh.model.addPhysicalGroup(3, objectTag3DList, name=groupName)

    def addMaterial(self, name, materialObj, color="#000000", opacity: float = -89.0):
        self.materialList[name] = materialObj
        self.materialList[name].color = color
        self.materialList[name].opacity = opacity
