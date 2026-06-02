import emerge as em
import emerge._emerge.geometry as emergeGeo
import emerge._emerge.physics.microwave.microwave_bc as emergeMicrowaveBC

from typing import Callable, Literal
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

    def setSurfaceImpedanceBoundaryConditionToObject(self, objectName: str,
        material: em.Material | None = None,
        surface_conductance: float | None = None,
        surface_roughness: float = 0,
        thickness: float | None = None,
        sr_model: Literal['Hammerstad-Jensen'] = 'Hammerstad-Jensen',
        impedance_function: Callable | None = None,
    ):
        """Wrapper method specific for surface impedance, it call setBoundaryConditionToObject, this is to have method with proper named parameters."""

        self.setBoundaryConditionToObject(name=objectName, type="SurfaceImpedance", additionalParameters={
            "material": material,
            "surface_conductance": surface_conductance,
            "surface_roughness": surface_roughness,
            "thickness": thickness,
            "sr_model": sr_model,
            "impedance_function": impedance_function,
        })

    def setBoundaryConditionToObject(self, name: str, type: str, additionalParameters: dict = {}):
        """Assign boundary condition to object, if some extra params are required for boundary condition to be created they should be passed in additionalParameters
        dictionary and are unpacked, now used for SurfaceImpedance

        For PEC, PMC there are no params needed for SurfaceImpedance there are needed conductance, roughness, thickness and surface roughness model can be specified.
        """

        objectList = self.getObjectSurface(name)
        for obj in objectList:
            if type.lower() == "absorbing":
                self.simulationObj.mw.bc.AbsorbingBoundary(obj)
            elif type == "PEC":
                self.simulationObj.mw.bc.PEC(obj)
            elif type == "PMC":
                self.simulationObj.mw.bc.PMC(obj)
            elif type == "SurfaceImpedance":
                self.simulationObj.mw.bc.SurfaceImpedance(obj, **additionalParameters)
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

    def addMaterial(self, name, materialObj, color="#000000", opacity: float = 1.0):
        self.materialList[name] = materialObj
        self.materialList[name].color = color
        self.materialList[name].opacity = opacity

    def getMaterial(self, name):
        #
        #   Get material from internal material list
        #
        materialObj = self.materialList[name] if name in self.materialList.keys() else None

        #
        #   If material not found try to scan all geometries and their assigned materials if it will be found
        #
        if materialObj == None:
            for geometryObj in self.simulationObj.state.manager.geometry_list[self.simulationObj.modelname].values():
                if geometryObj.material.name == name:
                    materialObj = geometryObj.material
                    break

        return materialObj

    def setMaterialColor(self, name, color="#000000", opacity: float = 1.0):
        """Setter for color and opacity
        :param name: Name of material
        :param color: Color string in html for like #FF0000 (red)
        :param opacity: Makes material transparent (0.0) or non-transparent (1.0)
        """
        self.materialList[name].color = color
        self.materialList[name].opacity = opacity

    def addPort(
            self,
            name="",
            portStart=[0.0, 0.0, 0.0],
            width=0.0,
            height=0.0,
            R=50.0,
            direction=em.ZAX,
            excitationAmplitude:float=0.0,
            geometryObject:em._emerge.geometry.GeoObject=None,
            portNumber:int=-1,

            modalModeType: Literal['TE','TM','TEM'] | None = None,
            modalMixedMaterials: bool = False,
            modalImpedanceDefinition: Literal['PV','PI','VI'] = 'PV',

            rectangularWaveguideMode: tuple[int, int] = (0, 0),
            rectangularWaveguidePermittivity: float = 1.0,

            coaxPortInnerRadius: float  = 0.0,
            coaxPortOuterRadius: float = 0.0,
            coaxPortPermittivity: float = 1.0,
    ):
        self.portList[name] = {}
        self.portList[name]['portStart'] = portStart
        self.portList[name]['width'] = width
        self.portList[name]['height'] = height
        self.portList[name]['R'] = R
        self.portList[name]['direction'] = direction
        self.portList[name]['excitationAmplitude'] = excitationAmplitude
        self.portList[name]['object'] = geometryObject
        self.portList[name]['portNumber'] = self._generatedPortIndex if portNumber == -1 else portNumber

        self.portList[name]["modalModeType"] = modalModeType
        self.portList[name]["modalMixedMaterials"] = modalMixedMaterials
        self.portList[name]["modalImpedanceDefinition"] = modalImpedanceDefinition

        self.portList[name]["rectangularWaveguideMode"] = rectangularWaveguideMode
        self.portList[name]["rectangularWaveguidePermittivity"] = rectangularWaveguidePermittivity

        self.portList[name]["coaxPortInnerRadius"] = coaxPortInnerRadius
        self.portList[name]["coaxPortOuterRadius"] = coaxPortOuterRadius
        self.portList[name]["coaxPortPermittivity"] = coaxPortPermittivity

        if portNumber == -1:
            self._generatedPortIndex += 1

    def addLumpedPort(
        self,
        name = "",
        portStart = [0.0, 0.0, 0.0],
        width = 0.0,
        height = 0.0,
        R = 50.0,
        direction = em.ZAX,
        power:float = 0.0,
        geometryObject:em._emerge.geometry.GeoObject = None,
        portNumber:int = -1
    ):
        self.addPort(
            name=name,
            portStart=portStart,
            width=width,
            height=height,
            R=R,
            direction=direction,
            excitationAmplitude=power,
            geometryObject=geometryObject,
            portNumber=portNumber
        )

    def addModalPort(
        self,
        name = "",
        mode: Literal["TE", "TM", "TEM"] = "TE",
        mixedMaterials: bool = False,
        impedanceDefinition: Literal["PV", "PI", "VI"] = "PV",
        power:float = 0.0,
        geometryObject:em._emerge.geometry.GeoObject = None,
        portNumber:int = -1
    ):
        self.addPort(
            name=name,
            modalModeType=mode,
            modalMixedMaterials=mixedMaterials,
            modalImpedanceDefinition=impedanceDefinition,
            excitationAmplitude=power,
            geometryObject=geometryObject,
            portNumber=portNumber
        )

    def addRectangularWaveguidePort(
        self,
        name = "",
        mode: tuple[int, int] = (0,0),
        er: float = 1.0,
        power:float = 1.0,
        geometryObject:em._emerge.geometry.GeoObject = None,
        portNumber:int = -1
    ):
        self.addPort(
            name=name,
            rectangularWaveguideMode = mode,
            rectangularWaveguidePermittivity = er,
            excitationAmplitude=power,
            geometryObject=geometryObject,
            portNumber=portNumber
        )

    def addCoaxPort(
        self,
        name = "",
        inner_radius: float = 0.0,
        outer_radius: float = 0.0,
        er: float = 1.0,
        power:float = 1.0,
        geometryObject:em._emerge.geometry.GeoObject = None,
        portNumber:int = -1
    ):
        self.addPort(
            name=name,
            coaxPortInnerRadius = inner_radius,
            coaxPortOuterRadius = outer_radius,
            coaxPortPermittivity = er,
            excitationAmplitude=power,
            geometryObject=geometryObject,
            portNumber=portNumber
        )


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

    def setPortAsLumpedPort(self, name, searchObjectName="") -> list[emergeMicrowaveBC.LumpedPort]:
        portObj = self.getPort(name)
        resultBoundaryConditionList = []

        #
        # Port object can be splitted since there was fragmentation operation in EMerge
        #
        portGeometryObjectList = self.getAllObjectByName(name if searchObjectName == "" else searchObjectName)
        for geometryObj in portGeometryObjectList:
            if portObj['excitationAmplitude'] > 0.0:
                resultObj = self.simulationObj.mw.bc.LumpedPort(
                    face=geometryObj,
                    port_number=portObj['portNumber'],
                    width=portObj['width'],
                    height=portObj['height'],
                    direction=portObj['direction'],
                    Z0=portObj['R'],
                    power=portObj['excitationAmplitude']
                )
            else:
                resultObj = self.simulationObj.mw.bc.LumpedPort(
                    face=geometryObj,
                    port_number=portObj['portNumber'],
                    width=portObj['width'],
                    height=portObj['height'],
                    direction=portObj['direction'],
                    Z0=portObj['R']
                )
            resultBoundaryConditionList.append(resultObj)

            self._temporaryInternalPortIndex += 1

        return resultBoundaryConditionList

    def setPortAsModalPort(self, name, searchObjectName="") -> list[emergeMicrowaveBC.ModalPort]:
        """Experimental implementation not tested on real world example!!!"""

        resultBoundaryConditionList = []

        portObj = self.getPort(name)
        portGeometryObjectList = self.getAllObjectByName(name if searchObjectName == "" else searchObjectName)

        for geometryObj in portGeometryObjectList:
            resultObj = self.simulationObj.mw.bc.ModalPort(
                face = geometryObj,
                port_number=portObj['portNumber'],
                power = portObj['excitationAmplitude'],
                modetype = portObj["modalModeType"],
                number_of_modes = 1,
                mixed_materials = portObj["modalMixedMaterials"],
                impedance_definition = portObj["modalImpedanceDefinition"]
            )
            resultBoundaryConditionList.append(resultObj)

        return resultBoundaryConditionList

    def setPortAsRectangularWaveguidePort(self, name, searchObjectName="") -> list[emergeMicrowaveBC.RectangularWaveguide]:
        """Experimental implementation not tested on real world example!!!"""

        resultBoundaryConditionList = []

        portObj = self.getPort(name)
        portGeometryObjectList = self.getAllObjectByName(name if searchObjectName == "" else searchObjectName)

        for geometryObj in portGeometryObjectList:
            resultObj = self.simulationObj.mw.bc.RectangularWaveguide(
                face = geometryObj,
                port_number=portObj['portNumber'],
                power = portObj['excitationAmplitude'],
                mode = portObj["rectangularWaveguideMode"],
                er = portObj["rectangularWaveguidePermittivity"]
            )
        resultBoundaryConditionList.append(resultObj)

        return resultBoundaryConditionList

    def setPortAsCoaxPort(self, name, searchObjectName="") -> list[emergeMicrowaveBC.CoaxPort]:
        """Experimental implementation not tested on real world example!!!"""

        resultBoundaryConditionList = []

        portObj = self.getPort(name)
        portGeometryObjectList = self.getAllObjectByName(name if searchObjectName == "" else searchObjectName)

        for geometryObj in portGeometryObjectList:
            resultObj = self.simulationObj.mw.bc.CoaxPort(
                face = geometryObj,
                port_number=portObj['portNumber'],
                power = portObj['excitationAmplitude'],
                rad_in_out = (portObj["coaxPortInnerRadius"], portObj["coaxPortInnerRadius"]),
                er = portObj["coaxPortPermittivity"]
            )
            resultBoundaryConditionList.append(resultObj)

        return resultBoundaryConditionList

    def plotSParamUsingPortName(self, sourcePortName, targetPortName, dblim=[-40, 0], plotSmithChart=False):
        sourcePortNumber = self.getPortNumber(sourcePortName)
        targetPortNumber = self.getPortNumber(targetPortName)

        self.plotSParamUsingPortNumbers(sourcePortNumber, targetPortNumber, dblim, plotSmithChart)

    def plotSParamUsingPortNumbers(self, sourcePortNumber, targetPortNumber, dblim=[-40, 0], xunit="GHz", plotSmithChart=False, plotInterpolatedPoints:int=-1, plotS11=False):
        simulationResult = self.simulationObj.data.mw

        freqs = simulationResult.scalar.grid.freq
        fmin = freqs.min()
        fmax = freqs.max()

        if plotInterpolatedPoints > 0:
            #
            # Add points into frequency axis and interpolate computed S param over these points it makes graph line smooth but it can provide wrong result!!!
            #
            freq_dense = np.linspace(fmin, fmax, plotInterpolatedPoints)
            S_data = simulationResult.scalar.grid.model_S(sourcePortNumber, targetPortNumber, freq_dense)
            plotLabel = f'S{sourcePortNumber}{targetPortNumber}'
            plot_sp(freq_dense, S_data, labels=plotLabel, dblim=dblim)
        else:
            S21_data = simulationResult.scalar.grid.S(sourcePortNumber, targetPortNumber)
            S11_data = simulationResult.scalar.grid.S(sourcePortNumber, sourcePortNumber)
            plotLabel_S11 = f'S{sourcePortNumber}{sourcePortNumber}'
            plotLabel_S21 = f'S{targetPortNumber}{sourcePortNumber}'
            if plotS11:
                plot_sp(freqs, [S11_data, S21_data], labels=[plotLabel_S11, plotLabel_S21], dblim=dblim, xunit=xunit)
            else:
                plot_sp(freqs, [S21_data], labels=[plotLabel_S21], dblim=dblim, xunit=xunit)

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

    def create_emerge_plane_data(self, port_start, port_stop, normal):
        """
        Computes origin, u, and v vectors for an EMerge Plane using
        start/stop diagonal points and a surface normal vector.

        Inputs can be FreeCAD vectors or standard (x, y, z) tuples.
        """
        # 1. Convert everything to numpy arrays for clean math
        p1 = np.array([port_start[0], port_start[1], port_start[2]])
        p4 = np.array([port_stop[0], port_stop[1], port_stop[2]])
        n = np.array([normal[0], normal[1], normal[2]])

        # Normalize the normal vector to ensure it is a unit vector
        n = n / np.linalg.norm(n)

        # 2. Calculate the full diagonal vector across the port
        diag = p4 - p1

        # 3. Project the diagonal vector to eliminate any component pointing
        # along the normal (ensures the math stays strictly flat on the 2D plane)
        diag_planar = diag - np.dot(diag, n) * n

        # 4. Determine the primary coordinate alignment for the 'u' axis.
        # We choose an axis that isn't parallel to our normal vector.
        if abs(n[0]) < 0.9:
            ref_dir = np.array([1.0, 0.0, 0.0])  # Fallback to X axis alignment
        else:
            ref_dir = np.array([0.0, 1.0, 0.0])  # Fallback to Y axis alignment

        # Generate an orthogonal direction for 'u' using a cross product
        u_direction = np.cross(n, ref_dir)
        u_axis = u_direction / np.linalg.norm(u_direction)

        # Generate the perpendicular 'v' direction
        v_axis = np.cross(n, u_axis)

        # 5. Project the planar diagonal onto our newly established u and v axes
        u_magnitude = np.dot(diag_planar, u_axis)
        v_magnitude = np.dot(diag_planar, v_axis)

        # 6. Reconstruct the final u and v vectors as clean 3D tuples
        u = tuple(u_axis * u_magnitude)
        v = tuple(v_axis * v_magnitude)
        origin = tuple(p1)

        return origin, u, v

    def exportCSV_SParam(self, filename: str, sourcePortNumber: int, targetPortNumber: int, useMagnitude=True, delimiter=','):
        simulationResult = self.simulationObj.data.mw

        # get frequency axis from result
        freq = simulationResult.scalar.grid.freq

        # get S param, if magnitude compute it, normaly it's complex number
        if useMagnitude:
            sParam = 20 * np.log10(abs(simulationResult.scalar.grid.S(sourcePortNumber, targetPortNumber)))
        else:
            sParam = simulationResult.scalar.grid.S(sourcePortNumber, targetPortNumber)

        outFile = open(filename, "w")
        outFile.write(f"freq{delimiter}s{targetPortNumber}{sourcePortNumber}\n")
        for x in zip(freq, sParam):
            outFile.write(f"{x[0]}{delimiter}{x[1]}\n")
        outFile.close()
