import emerge as em
import emerge._emerge.geometry as emergeGeo
from typing import Callable
import gmsh
import os

import numpy as np
from emerge.plot import smith, plot_sp

class EMergeHelperFunctions:
    simulationObj = None
    materialList = {}
    portList = {}
    _generatedPortIndex = 1
    _temporaryInternalPortIndex = 1 #this shouldn't exists, but it's helper counter if port somehow will be from more objects

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

    def setMaterialColor(self, name, color="#000000", opacity: float = -89.0):
        """Setter for color and opacity
        :param name: Name of material
        :param color: Color string in html for like #FF0000 (red)
        :param opacity: Makes material transparent (0.0) or non-transparent (1.0)
        """
        self.materialList[name].color = color
        self.materialList[name].opacity = opacity

    def addPort(self, name="", portStart=[0.0, 0.0, 0.0], width=0.0, height=0.0, R=50.0, direction=em.ZAX, excitationAmplitude:float=0.0, geometryObject:em._emerge.geometry.GeoObject=None, portNumber:int=-1):
        self.portList[name] = {}
        self.portList[name]['portStart'] = portStart
        self.portList[name]['width'] = width
        self.portList[name]['height'] = height
        self.portList[name]['R'] = R
        self.portList[name]['direction'] = direction
        self.portList[name]['excitationAmplitude'] = excitationAmplitude
        self.portList[name]['object'] = geometryObject
        self.portList[name]['portNumber'] = self._generatedPortIndex if portNumber == -1 else portNumber

        if portNumber == -1:
            self._generatedPortIndex += 1

    def getPort(self, name):
        return self.portList[name]

    def getPortByNumber(self, portNumber):
        resultPortObj = None
        for portObj in self.portList:
            if portNumber == portObj['portNumber']:
                resultPortObj = portObj
        return resultPortObj

    def getPortNumber(self, name):
        for portObj in self.portList:
            if portObj['portNumber'] == name:
                return portObj['portNumber']

    def setPortAsLumpedPort(self, name, searchObjectName=""):
        portObj = self.getPort(name)

        #
        # Port object can be splitted since there was fragmentation operation in EMerge
        #
        portGeometryObjectList = self.getAllObjectByName(name if searchObjectName == "" else searchObjectName)
        for geometryObj in portGeometryObjectList:
            if portObj['excitationAmplitude'] > 0.0:
                self.simulationObj.mw.bc.LumpedPort(
                    geometryObj,
                    port_number=portObj['portNumber'],
                    width=portObj['width'],
                    height=portObj['height'],
                    direction=portObj['direction'],
                    Z0=portObj['R'],
                    power=portObj['excitationAmplitude']
                )
            else:
                self.simulationObj.mw.bc.LumpedPort(
                    geometryObj,
                    port_number=portObj['portNumber'],
                    width=portObj['width'],
                    height=portObj['height'],
                    direction=portObj['direction'],
                    Z0=portObj['R']
                )

            self._temporaryInternalPortIndex += 1

    def plotSParamUsingPortName(self, sourcePortName, targetPortName, dblim=[-40, 0], plotSmithChart=False):
        sourcePortNumber = self.getPortNumber(sourcePortName)
        targetPortNumber = self.getPortNumber(targetPortName)

        self.plotSParamUsingPortNumbers(sourcePortNumber, targetPortNumber, dblim, plotSmithChart)

    def plotSParamUsingPortNumbers(self, sourcePortNumber, targetPortNumber, dblim=[-40, 0], plotSmithChart=False, plotImproved=False, plotS11=False):
        simulationResult = self.simulationObj.data.mw

        freqs = simulationResult.scalar.grid.freq
        fmin = freqs.min()
        fmax = freqs.max()

        if plotImproved:
            freq_dense = np.linspace(fmin, fmax, 1001)
            S_data = simulationResult.scalar.grid.model_S(sourcePortNumber, targetPortNumber, freq_dense)  # reflection coefficient
            plotLabel = f'S{sourcePortNumber}{targetPortNumber}'
            plot_sp(freq_dense, S_data, labels=plotLabel, dblim=dblim)  # plot return loss in dB
        else:
            S21_data = simulationResult.scalar.grid.S(sourcePortNumber, targetPortNumber)  # reflection coefficient
            S11_data = simulationResult.scalar.grid.S(sourcePortNumber, sourcePortNumber)  # reflection coefficient
            plotLabel_S11 = f'S{sourcePortNumber}{sourcePortNumber}'
            plotLabel_S21 = f'S{targetPortNumber}{sourcePortNumber}'
            if plotS11:
                plot_sp(freqs, [S11_data, S21_data], labels=[plotLabel_S11, plotLabel_S21], dblim=dblim)  # plot return loss in dB
            else:
                plot_sp(freqs, [S21_data], labels=[plotLabel_S21], dblim=dblim)  # plot return loss in dB

        if plotSmithChart:
            smith(S_data, f=freq_dense, labels=plotLabel)  # smith chart

    def addObjectToView(self, nameOrList: str | list, opacity:float=0.1):
        objectList = []
        if type(nameOrList) == str:
            objectList = self.getAllObjectByName(nameOrList)
        if type(nameOrList) == list:
            for oneName in nameOrList:
                objectList.extend(self.getAllObjectByName(oneName))

        for geoObject in objectList:
            self.simulationObj.display.add_object(geoObject, opacity=opacity)
