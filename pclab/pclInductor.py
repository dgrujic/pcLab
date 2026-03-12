# Copyright 2026 Dušan Grujić (dusan.grujic@etf.bg.ac.rs)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from pclab.pclGeom import *
import math

###############################################################################
#
# Single ended inductor layout generator
#
###############################################################################

class inductorSE(geomBase):
    """
        Single-ended inductor
    """

    _r = None
    _w = None
    _s = None
    _n = None

    _connectLen = None
    _connectSpace = None
    
    _indType = 1    # Possible values: 1 and 2

    _signalLayer = None     # Name of signal layer
    _underPassLayer = None  # Name of under pass layer

    _viaLayer = None    # Name of via layer
    _viaEnc = 0
    _viaSize = 0
    _viaSpace = 0

    _geomType = None
    
    _centerX = 0.0
    _centerY = 0.0
    
    def __init__(self,tech=None):
        self._tech = tech   # Set the technology

    def setupGeometry(self, r, w, s, n, signalLayer, underPassLayer, geomType="octagon", connectLen = None, connectSpace = None, centerX = None, centerY = None, subRingSpace=0.0, subRingW=0.0, diffLayer=None, implantLayer=None, contSpaceMult=4.0):
        """
            Setup inductor geometry
            r : float
                outer inductor dimension
            w : float
                winding line width
            s : foat
                winding spacing
            n : float
                number of turns
            signalLayer : string
                signal layer name
            underPassLayer : string
                underpass layer name
            geomType : string
                Type of geometry. Allowed values : "rect", "octagon"
            connectLen : float
                Length of connect traces
            connectSpace : float
                Spacing of connect traces, used only for integer number of turns
            centerX : float
                Center of inductor x coordinate
            centerY : float
                Center of inductor y coordinate
            subRingSpace
            subRingW
            diffLayer
            implantLayer
        """
        self._r = r
        self._w = w
        self._s = s
        self._n = 0.25 * round(n/0.25)  # round to 0.25 turns
        self._signalLayer = signalLayer
        self._underPassLayer = underPassLayer
        if (geomType != "rect") and (geomType != "octagon"):
            print("WARNING:inductorSE::setupGeometry: Unknown geometry type. Setting to octagonal.")
            self._geomType = "octagon"
        else:
            self._geomType = geomType
        
        if connectLen == None:
            self._connectLen = w*2
        else:
            self._connectLen = connectLen
        
        if connectSpace == None:
            self._connectSpace = 0.5*w
        else:
            self._connectSpace = connectSpace
        
        if centerX == None:
            self._centerX = 0
        else:
            self._centerX = centerX
            
        if centerY == None:
            self._centerY = 0
        else:
            self._centerY = centerY
            
        # Find via, find via rules
        viaLay = self._tech.findViaTopMet(signalLayer)
        if viaLay == None:
            print("ERROR:inductorSE::setupGeometry: Signal layer " + signalLayer + " does not have any vias connecting to it from underside.")
            return
        
        viaName = viaLay.name
        self._viaLayer = viaName
        self._viaEnc = self._tech.getDRCRule(viaName, "viaEnc")
        self._viaSize = self._tech.getDRCRule(viaName, "viaSize")
        self._viaSpace = self._tech.getDRCRule(viaName, "viaSpace")

        #        
        # Substrate ring parameters
        #
        if diffLayer!=None:
            self._genSubstrateContact = True
            contLay = self._tech.findViaBotMet(diffLayer).name
            if contLay == None:
                print("ERROR:inductorSE::setupGeometry: Diffusion layer " + diffLayer + " does not have any vias connecting to it from top.")
                return

            self._diffLayer = diffLayer
            self._impLayer = implantLayer
            
            if implantLayer!=None:
                self._diffEnc = self._tech.getDRCRule(implantLayer, "enclosure")
            else:
                self._diffEnc = 0            

            self._contLayer = contLay
            self._contEnc = self._tech.getDRCRule(contLay, "viaEnc")
            self._contSize = self._tech.getDRCRule(contLay, "viaSize")
            self._contSpace = self._tech.getDRCRule(contLay, "viaSpace") * contSpaceMult

            self._m1Layer = self._tech.findTopMetVia(contLay).name
            self._subRingSpace = subRingSpace
            self._subRingW = subRingW
            
        else:
            self._genSubstrateContact = False
        
        # Dimension check: return False if diameter is too small
        return r>=self.get_min_diameter()


    def get_min_diameter(self):
        return SE_get_min_diameter(self)


    def _genOct(self):
        """
            Generate octagonal inductor.
            Returns a list ( signal poligon, list of via rectangles, underpass rectangle, second terminal connection rectangle)
            In some cases there might be no vias or underpasses, so they could be None.
        """
        sqrt=math.sqrt
        roundToGrid = self.roundToGrid

        w = roundToGrid(self._w)
        r = roundToGrid(self._r/2)
        s = roundToGrid(self._s)
        n = roundToGrid(self._n)

        connectLen = roundToGrid(self._connectLen)    # signal layer connection length
        connectSpace = roundToGrid(self._connectSpace)  # terminal spacing in case of whole number of turns

        indType=self._indType

        poly = list()   # list of points for singal layer polygon
        viaRect1 = list()    # rectangle to fill with vias
        viaRect2 = list()    # rectangle to fill with vias
        underRect = list()  # underside exit rectangle
        exitRect = list()   # signal layer exit connection

        # draw start
        if (n-round(n)) == 0:
            # Whole number of turns
            xstart = -w - connectSpace
            fracTurns = False
            P1X = -w/2 - connectSpace
        else:
            # Fractional number of turns
            xstart = -0.5 * w
            fracTurns = True
            P1X = 0.0
            
        ystart = -r - connectLen
        poly.append((xstart,ystart))
        poly.append((xstart,-r))

        #
        # Port labels
        #
        if (n-round(n)) == 0:
            # Whole number of turns
            P1X = -w/2 - connectSpace
        else:
            # Fractional number of turns
            P1X = 0.0
        port1Label = ((P1X, ystart), 'P1')

        if fracTurns:
            # Fractional number of turns
            frac = int((n-math.floor(n))/0.25)
            if frac==1:
                # Make underside exit on the left side
                P2X = -r-s-connectLen
                P2Y = 0
            elif frac==2:
                # Make underside exit on top
                P2X = 0
                P2Y = r+s+connectLen
            else:
                # Make underside exit on the right side
                P2X = r+s+connectLen
                P2Y = 0
        else:
            # Whole number of turns
            if n==1.0:
                # Single turn inductor, no vias or underside exit
                P2X = connectSpace+w/2
                P2Y = ystart
            else:
                # Multi turn inductor, underside exit on bottom
                P2X = connectSpace+w/2
                P2Y = -r-connectLen
        port2Label = ((P2X,P2Y), 'P2')
        portLabels = (port1Label, port2Label)
        #
        # end of port labels
        #

        N=int(n/0.25)

        crad = r; # current radius
        side = roundToGrid(r/(1+sqrt(2)))  # round to grid
         
        for nn in range(2*N):
            if nn>N-1:
                i=2*N-nn
                reverse = True
            else:
                i=nn+1
                reverse = False
            
            # Draw underside exit & vias
            if nn==N:
                ncrad = crad - w

                if fracTurns:
                    # Fractional number of turns
                    frac = int((n-math.floor(n))/0.25)
                    if frac==1:
                        # Make underside exit on the left side
                        poly.append( (-crad, w/2) )
                        poly.append( (-ncrad, w/2) )

                        viaRect1.append( (-ncrad, w/2) )
                        viaRect1.append( (-crad, -w/2) )
                        
                        viaRect2.append( (-r-s, w/2) )
                        viaRect2.append( (-r-s-w, -w/2) )
                        
                        underRect.append( (-r-s-w, -w/2) )
                        underRect.append( (-ncrad, w/2) )
                        
                        exitRect.append( (-r-s, w/2) )
                        exitRect.append( (-r-s-connectLen, -w/2) )
                        P2X = -r-s-connectLen
                        P2Y = 0
                        
                    elif frac==2:
                        # Make underside exit on top
                        poly.append( (w/2, crad) )
                        poly.append( (w/2, ncrad) )

                        viaRect1.append( (w/2, ncrad) )
                        viaRect1.append( (-w/2, crad) )
                        
                        viaRect2.append( (w/2, r+s) )
                        viaRect2.append( (-w/2, r+s+w) )
                        
                        underRect.append( (-w/2, r+s+w) )
                        underRect.append( (w/2, ncrad) )
                        
                        exitRect.append( (w/2, r+s) )
                        exitRect.append( (-w/2, r+s+connectLen) )

                        P2X = 0
                        P2Y = r+s+connectLen
                    else:
                        # Make underside exit on the right side
                        poly.append( (crad, -w/2) )
                        poly.append( (ncrad, -w/2) )

                        viaRect1.append( (ncrad, w/2) )
                        viaRect1.append( (crad, -w/2) )
                        
                        viaRect2.append( (r+s, w/2) )
                        viaRect2.append( (r+s+w, -w/2) )
                        
                        underRect.append( (+r+s+w, -w/2) )
                        underRect.append( (ncrad, w/2) )
                        
                        exitRect.append( (r+s, w/2) )
                        exitRect.append( (r+s+connectLen, -w/2) )
                        P2X = r+s+connectLen
                        P2Y = 0
                        
                else:
                    # Whole number of turns
                    if n==1.0:
                        # Single turn inductor, no vias or underside exit
                        poly.append((connectSpace+w, -r))
                        poly.append((connectSpace+w, ystart))
                        poly.append((connectSpace, ystart))
                        poly.append((connectSpace, -crad+w))

                        P2X = connectSpace+w/2
                        P2Y = ystart

                    else:
                        # Multi turn inductor, underside exit on bottom
                        poly.append((connectSpace, -crad))
                        poly.append((connectSpace, -crad+w))
                        
                        viaRect1.append( (connectSpace, -crad) )
                        viaRect1.append( (connectSpace+w, -crad+w) )

                        viaRect2.append( (connectSpace, -r) )
                        viaRect2.append( (connectSpace+w, -r+w) )

                        underRect.append( (connectSpace, -crad+w) )
                        underRect.append( (connectSpace+w, -r) )
                        
                        exitRect.append( (connectSpace, -r+w) )
                        exitRect.append( (connectSpace+w, -r-connectLen))

                        P2X = connectSpace+w/2
                        P2Y = -r-connectLen
  
                # start drawing winding inner edge
                crad = ncrad
                side = roundToGrid((crad)/(1+sqrt(2)))

            if i%4 == 1:
                if reverse:
                    poly.append( (-crad, -side) )        
                    poly.append( (-side, -crad) )
                else:
                    poly.append( (-side, -crad) )
                    poly.append( (-crad, -side) )        
            elif i%4 == 2:
                if reverse:    
                    poly.append( (-side, crad) )
                    poly.append( (-crad, side) )        
                else:
                    poly.append( (-crad, side) )        
                    poly.append( (-side, crad) )
                
            elif i%4 == 3:
                if reverse:
                    poly.append( (crad, side) )
                    poly.append( (side, crad) )        
                else:
                    poly.append( (side, crad) )        
                    poly.append( (crad, side) )
            else:
                if n==1.0:  # Single turn inductor
                    ncrad = crad
                else:   # Other inductors
                    if nn>N-1:
                        ncrad = crad + w + s
                    else:
                        ncrad = crad - w - s
                nside = roundToGrid(ncrad/(1+sqrt(2)))

                if reverse:
                    if indType==1:
                        poly.append( (nside, -crad) )
                        poly.append( (ncrad, -crad+ncrad-nside) )
                    else:
                        poly.append( (ncrad-crad+side, -crad) )
                        poly.append( (ncrad, -side) )
                else:
                    if indType==1:
                        poly.append( (crad, -ncrad+crad-side) )
                        poly.append( (side, -ncrad) )
                    else:
                        poly.append( (crad, -nside) )
                        poly.append( (crad-ncrad+nside, -ncrad) )

                crad = ncrad
                side = nside
                        
        # Finish the polygon
        poly.append((xstart+w,-crad))
        poly.append((xstart+w,ystart))

        port2Label = ((P2X, P2Y), 'P2')
        
        if len(viaRect1) != 0:
            # Draw vias
            viaEnc = self._viaEnc
            viaSize = self._viaSize
            viaSpace = self._viaSpace
            
            vias1 = self.fillVias(viaRect1, viaEnc, viaSize, viaSpace)
            vias2 = self.fillVias(viaRect2, viaEnc, viaSize, viaSpace)
            vias=vias1+vias2
        else:
            vias = None

        # Translate objects
        offset = (self._centerX, self._centerY)
        poly = self.translateObjs([poly], offset)[0]
        if vias != None:
            vias = self.translateObjs(vias, offset)
        if len(underRect) != 0:
            underRect = self.translateObjs([underRect], offset)[0]
        else:
            underRect = None
            
        if len(exitRect) != 0:
            exitRect = self.translateObjs([exitRect], offset)[0]
        else:
            exitRect = None
        
        return (poly, vias, underRect, exitRect, portLabels)

    def _genRect(self):
        """
            Generate rectangular inductor.
            Returns a list ( signal poligon, list of via rectangles, underpass rectangle, second terminal connection rectangle)
            In some cases there might be no vias or underpasses, so they could be None.
        """
        roundToGrid = self.roundToGrid

        w = roundToGrid(self._w)
        r = roundToGrid(self._r/2)
        s = roundToGrid(self._s)
        n = roundToGrid(self._n)

        connectLen = roundToGrid(self._connectLen)    # signal layer connection length
        connectSpace = roundToGrid(self._connectSpace)  # terminal spacing in case of whole number of turns

        poly = list()   # list of points for singal layer polygon
        viaRect1 = list()    # rectangle to fill with vias
        viaRect2 = list()    # rectangle to fill with vias
        underRect = list()  # underside exit rectangle
        exitRect = list()   # signal layer exit connection

        # draw start
        if (n-round(n)) == 0:
            # Whole number of turns
            xstart = -w - connectSpace
            fracTurns = False
        else:
            # Fractional number of turns
            xstart = -0.5 * w
            fracTurns = True
            
        ystart = -r - connectLen
        poly.append((xstart,ystart))
        poly.append((xstart,-r))

        N=int(n/0.25)
        
        #
        # Port labels
        #
        if (n-round(n)) == 0:
            # Whole number of turns
            P1X = -w/2 - connectSpace
        else:
            # Fractional number of turns
            P1X = 0.0
        port1Label = ((P1X, ystart), 'P1')

        if fracTurns:
            # Fractional number of turns
            frac = int((n-math.floor(n))/0.25)
            if frac==1:
                # Make underside exit on the left side
                P2X = -r-s-connectLen
                P2Y = 0
            elif frac==2:
                # Make underside exit on top
                P2X = 0
                P2Y = r+s+connectLen
            else:
                # Make underside exit on the right side
                P2X = r+s+connectLen
                P2Y = 0
        else:
            # Whole number of turns
            if n==1.0:
                # Single turn inductor, no vias or underside exit
                P2X = connectSpace+w/2
                P2Y = ystart
            else:
                # Multi turn inductor, underside exit on bottom
                P2X = connectSpace+w/2
                P2Y = -r-connectLen
        port2Label = ((P2X,P2Y), 'P2')
        portLabels = (port1Label, port2Label)
        #
        # end of port labels
        #

        crad = r; # current radius
        side = r
         
        for nn in range(2*N):
            if nn>N-1:
                i=2*N-nn
                reverse = True
            else:
                i=nn+1
                reverse = False
            
            # Draw underside exit & vias
            if nn==N:
                ncrad = crad - w

                if fracTurns:
                    # Fractional number of turns
                    frac = int((n-math.floor(n))/0.25)
                    if frac==1:
                        # Make underside exit on the left side
                        poly.append( (-crad, w/2) )
                        poly.append( (-ncrad, w/2) )

                        viaRect1.append( (-ncrad, w/2) )
                        viaRect1.append( (-crad, -w/2) )
                        
                        viaRect2.append( (-r-s, w/2) )
                        viaRect2.append( (-r-s-w, -w/2) )
                        
                        underRect.append( (-r-s-w, -w/2) )
                        underRect.append( (-ncrad, w/2) )
                        
                        exitRect.append( (-r-s, w/2) )
                        exitRect.append( (-r-s-connectLen, -w/2) )
                    elif frac==2:
                        # Make underside exit on top
                        poly.append( (w/2, crad) )
                        poly.append( (w/2, ncrad) )

                        viaRect1.append( (w/2, ncrad) )
                        viaRect1.append( (-w/2, crad) )
                        
                        viaRect2.append( (w/2, r+s) )
                        viaRect2.append( (-w/2, r+s+w) )
                        
                        underRect.append( (-w/2, r+s+w) )
                        underRect.append( (w/2, ncrad) )
                        
                        exitRect.append( (w/2, r+s) )
                        exitRect.append( (-w/2, r+s+connectLen) )
                    else:
                        # Make underside exit on the right side
                        poly.append( (crad, -w/2) )
                        poly.append( (ncrad, -w/2) )

                        viaRect1.append( (ncrad, w/2) )
                        viaRect1.append( (crad, -w/2) )
                        
                        viaRect2.append( (r+s, w/2) )
                        viaRect2.append( (r+s+w, -w/2) )
                        
                        underRect.append( (+r+s+w, -w/2) )
                        underRect.append( (ncrad, w/2) )
                        
                        exitRect.append( (r+s, w/2) )
                        exitRect.append( (r+s+connectLen, -w/2) )
                else:
                    # Whole number of turns
                    if n==1.0:
                        # Single turn inductor, no vias or underside exit
                        poly.append((connectSpace+w, -r))
                        poly.append((connectSpace+w, ystart))
                        poly.append((connectSpace, ystart))
                        poly.append((connectSpace, -crad+w))
                    else:
                        # Multi turn inductor, underside exit on bottom
                        poly.append((connectSpace, -crad))
                        poly.append((connectSpace, -crad+w))
                        
                        viaRect1.append( (connectSpace, -crad) )
                        viaRect1.append( (connectSpace+w, -crad+w) )

                        viaRect2.append( (connectSpace, -r) )
                        viaRect2.append( (connectSpace+w, -r+w) )

                        underRect.append( (connectSpace, -crad+w) )
                        underRect.append( (connectSpace+w, -r) )
                        
                        exitRect.append( (connectSpace, -r+w) )
                        exitRect.append( (connectSpace+w, -r-connectLen))
                        
                        
                # start drawing winding inner edge
                crad = ncrad
                side = crad

            if i%4 == 1:
                if reverse:
                    poly.append( (-side, -crad) )
                else:
                    poly.append( (-side, -crad) )
            elif i%4 == 2:
                if reverse:    
                    poly.append( (-crad, side) )        
                else:
                    poly.append( (-crad, side) )        
            elif i%4 == 3:
                if reverse:
                    poly.append( (side, crad) )        
                else:
                    poly.append( (side, crad) )        
            else:
                if n==1.0:  # Single turn inductor
                    ncrad = crad
                else:   # Other inductors
                    if nn>N-1:
                        ncrad = crad + w + s
                    else:
                        ncrad = crad - w - s
                nside = ncrad
                if reverse:
                    poly.append( (ncrad, -crad+ncrad-nside) )
                else:
                    poly.append( (crad, -ncrad+crad-side) )
                crad = ncrad
                side = nside
                        
        # Finish the polygon
        poly.append((xstart+w,-crad))
        poly.append((xstart+w,ystart))
        
        if len(viaRect1) != 0:
            # Draw vias
            viaEnc = self._viaEnc
            viaSize = self._viaSize
            viaSpace = self._viaSpace
            
            vias1 = self.fillVias(viaRect1, viaEnc, viaSize, viaSpace)
            vias2 = self.fillVias(viaRect2, viaEnc, viaSize, viaSpace)
            vias=vias1+vias2
        else:
            vias = None

        # Translate objects
        offset = (self._centerX, self._centerY)
        poly = self.translateObjs([poly], offset)[0]
        if vias != None:
            vias = self.translateObjs(vias, offset)
        if len(underRect) != 0:
            underRect = self.translateObjs([underRect], offset)[0]
        else:
            underRect = None
            
        if len(exitRect) != 0:
            exitRect = self.translateObjs([exitRect], offset)[0]
        else:
            exitRect = None
        
        return (poly, vias, underRect, exitRect, portLabels)

    def genGeometry(self):
        """
            Generate inductor geometry.
            Returns lists of polygons on signal and underpass layers and rectangle vias
        """
        
        if self._geomType == "octagon":
            # Octagonal inductor geometry
            indGeom = self._genOct()
        else:
            # Rectangular inductor geometry
            indGeom = self._genRect()

        if self._genSubstrateContact:
            # Generate substrate contact
            subRingSpace = self._subRingSpace
            subRingW = self._subRingW
            r = self._r/2+subRingSpace
            s = subRingW
            centerX = self._centerX
            centerY = self._centerY
            geomType = self._geomType
            contEnc = self._contEnc
            contSize = self._contSize
            contSpace = self._contSpace
            diffEnc = self._diffEnc
            subCont = self.makeSubstrateContacts(subRingW, r, s, centerX, centerY, geomType, contEnc, contSize, contSpace, diffEnc)
             #m1Polygons, diffPolygons, implantPolygons, subContacts, pinLabels
        else:
            subCont = [[], [], [], [], []]
        return list(indGeom) + list(subCont)

        
    def genGDSII(self, fileName, structName='ind_se', precision=1e-9):
        """
            Generate inductor GDSII
        """
        indGeom = self.genGeometry()
        poly = indGeom[0]
        vias = indGeom[1]
        underRect = indGeom[2]
        exitRect = indGeom[3]
        portLabels = indGeom[4]
        
        # Substrate contacts
        m1Polygons = indGeom[5]
        diffPolygons = indGeom[6]
        impPolygons = indGeom[7]
        subContacts = indGeom[8]
        subPinLabels = indGeom[9]

        sigGDSII = self._tech.getGDSIINumByName(self._signalLayer)  # get signal layer GDSII number
        
        indCell = gdspy.Cell(structName)
                
        signalPoly = gdspy.Polygon(poly, sigGDSII)
        indCell.add(signalPoly)

        if vias != None:
            viaGDSII = self._tech.getGDSIINumByName(self._viaLayer)  # get signal layer GDSII number
            # add vias
            for viaRect in vias:
                indCell.add(gdspy.Rectangle(viaRect[0], viaRect[1], viaGDSII))

        if underRect != None:
        # add underpass & connector
            upGDSII = self._tech.getGDSIINumByName(self._underPassLayer)  # get signal layer GDSII number
            indCell.add(gdspy.Rectangle(underRect[0], underRect[1], upGDSII))

        if exitRect != None:
            indCell.add(gdspy.Rectangle(exitRect[0], exitRect[1], sigGDSII))

        for portLabel in portLabels:
            xy, name = portLabel
            indCell.add(gdspy.Label(name, xy, layer=sigGDSII))

        #
        # Substrate contacts
        #

        if self._genSubstrateContact:
            m1GDSII = self._tech.getGDSIINumByName(self._m1Layer)
            for m1Polygon in m1Polygons:
                poly = gdspy.Polygon(m1Polygon, m1GDSII)
                indCell.add(poly)

            diffGDSII = self._tech.getGDSIINumByName(self._diffLayer)
            contGDSII = self._tech.getGDSIINumByName(self._contLayer)
            for diffPolygon in diffPolygons:
                poly = gdspy.Polygon(diffPolygon, diffGDSII)
                indCell.add(poly)
                if self.emVias:
                    contPolygon = self.oversize(diffPolygon, -self._contEnc)
                    poly = gdspy.Polygon(contPolygon, contGDSII)
                    indCell.add(poly)

            if not self.emVias:
                # add vias
                for viaRect in subContacts:
                    indCell.add(gdspy.Rectangle(viaRect[0], viaRect[1], contGDSII))
            
            impLayer = self._impLayer
            if impLayer != None:
                impGDSII = self._tech.getGDSIINumByName(impLayer)
                for impPolygon in impPolygons:
                    poly = gdspy.Polygon(impPolygon, impGDSII)
                    indCell.add(poly)

            for portLabel in subPinLabels:
                xy, name = portLabel
                indCell.add(gdspy.Label(name, xy, layer=sigGDSII))

        #
        # end of substrate contacts
        #

        lib = gdspy.GdsLibrary(structName, unit = 1.0e-6, precision=precision)
        lib.add(indCell)
        lib.write_gds(fileName)

###############################################################################
#
# Symmetric inductor layout generator
#
###############################################################################

class inductorSym(geomBase):
    """
        Symmetric inductor
    """

    _connectLen = None
    _connectSpace = None

    def __init__(self,tech=None):
        self._tech = tech   # Set the technology

    def setupGeometry(self, r, w, s, n, signalLayer, underPassLayer, geomType="octagon", centerX = None, centerY = None, subRingSpace=0.0, subRingW=0.0, diffLayer=None, implantLayer=None, contSpaceMult=4.0, connectLen=None, connectSpace=None):
        """
            Setup symmetric inductor geometry
            r : float
                outer inductor dimension
            w : float
                winding line width
            s : foat
                winding spacing
            n : integer
                number of turns
            signalLayer : string
                signal layer name
            underPassLayer : string
                underpass layer name
            geomType : string
                Type of geometry. Allowed values : "rect", "octagon"
            centerX : float
                Center of inductor x coordinate
            centerY : float
                Center of inductor y coordinate
                
        """
        self._r = r
        self._w = w
        self._s = s
        self._n = n
        self._signalLayer = signalLayer
        self._underPassLayer = underPassLayer

        if connectLen is None:
            self._connectLen = 2*w
        else:
            self._connectLen = connectLen
        if connectSpace is None:
            self._connectSpace = w
        else:
            self._connectSpace = connectSpace
        if (geomType != "rect") and (geomType != "octagon"):
            print("WARNING:inductorSym::setupGeometry: Unknown geometry type. Setting to octagonal.")
            self._geomType = "octagon"
        else:
            self._geomType = geomType

        if n not in [1,2,3]:
            print("ERROR:inductorSym::setupGeometry: n must be 1, 2 or 3.")
                
        if centerX == None:
            self._centerX = 0
        else:
            self._centerX = centerX
            
        if centerY == None:
            self._centerY = 0
        else:
            self._centerY = centerY
            
        # Find via, find via rules
        viaLay = self._tech.findViaTopMet(signalLayer)
        if viaLay == None:
            print("ERROR:inductorSym::setupGeometry: Signal layer " + signalLayer + " does not have any vias connecting to it from underside.")
            return
        
        viaName = viaLay.name
        self._viaLayer = viaName
        self._viaEnc = self._tech.getDRCRule(viaName, "viaEnc")
        self._viaSize = self._tech.getDRCRule(viaName, "viaSize")
        self._viaSpace = self._tech.getDRCRule(viaName, "viaSpace")

        #        
        # Substrate ring parameters
        #
        if diffLayer!=None:
            self._genSubstrateContact = True
            contLay = self._tech.findViaBotMet(diffLayer).name
            if contLay == None:
                print("ERROR:inductorSym::setupGeometry: Diffusion layer " + diffLayer + " does not have any vias connecting to it from top.")
                return

            self._diffLayer = diffLayer
            self._impLayer = implantLayer
            
            if implantLayer!=None:
                self._diffEnc = self._tech.getDRCRule(implantLayer, "enclosure")
            else:
                self._diffEnc = 0            

            self._contLayer = contLay

            self._contEnc = self._tech.getDRCRule(contLay, "viaEnc")
            self._contSize = self._tech.getDRCRule(contLay, "viaSize")
            self._contSpace = self._tech.getDRCRule(contLay, "viaSpace") * contSpaceMult

            self._m1Layer = self._tech.findTopMetVia(contLay).name
            self._subRingSpace = subRingSpace
            self._subRingW = subRingW
            
        else:
            self._genSubstrateContact = False
                    
        # Dimension check: return False if diameter is too small
        return self._r >= self.get_min_diameter()


    def get_min_diameter(self):
        return sym_get_min_diameter(self)
    
    

    def genGeometry(self):
        """
        Generate geometry for symetric inductor
        returns polygon collections
        
        """    

        roundToGrid = self.roundToGrid
        sqrt = math.sqrt
        
        if self._geomType == "octagon":
            makeSegment = self.octSegment
        else:
            makeSegment = self.rectSegment
    
        makeRect = self.makeRect
        make45Bridge = self.make45Bridge
            
        w = self._w
        s = self._s
        n = self._n
        r = roundToGrid(self._r/2)

        e=roundToGrid(w+s+w/(1+sqrt(2)) + 2*s*math.tan(math.radians(22.5))) 

        corner_w=roundToGrid((w+s)/2/(1+sqrt(2)))
        corner_w2=roundToGrid((w+s)/2.0/(1+sqrt(2.0)))

        centerX=self._centerX;
        centerY=self._centerY;

        signalMet = list()
        underMet = list()
        vias = list()
        
        viaEnc = self._viaEnc
        viaSize = self._viaSize
        viaSpace = self._viaSpace

        for i in range(0,int(n)):
           signalMet.append(makeSegment(w,r-i*(w+s), e/2, 0, centerX, centerY))
           signalMet.append(makeSegment(w,r-i*(w+s), e/2, 1, centerX, centerY))
           signalMet.append(makeSegment(w,r-i*(w+s), e/2, 2, centerX, centerY))
           signalMet.append(makeSegment(w,r-i*(w+s), e/2, 3, centerX, centerY))

        appendPoly = self.appendPoly  
        appendVias = self.appendVias 

        signalMet.append(makeRect( (-1*(-r+0*(w+s))+centerX, e/2+centerY), (-1*(-r+0*(w+s)+w)+centerX, -e/2+centerY)))
        signalMet.append(makeRect( (-r+0*(w+s)+centerX, e/2+centerY), (-r+0*(w+s)+w+centerX, -e/2+centerY)))


        if n==1:
            signalMet.append(makeRect( (e/2+centerX, r+centerY), (-e/2+centerX, r-w+centerY)))
            
        if n==2:
              #                  w   e  offx     offy      originX         originY            mir  r90   addVias
            p1,v1 = make45Bridge(w, e, (w+s), 0, centerX-e/2, r-2*(w+s)+s+centerY, True, True, True, viaEnc, viaSize, viaSpace) # Underpass
            p2,v2 = make45Bridge(w, e, (w+s), 0, centerX-e/2, r-2*(w+s)+s+centerY, False, True, False, viaEnc, viaSize, viaSpace) # Underpass
            signalMet.append(makeRect( (e/2+centerX, -r+1*(w+s)+centerY), (-e/2+centerX, -r+1*(w+s)+w+centerY)))

            appendPoly( signalMet, [p2])
            appendPoly( underMet, [p1])
            appendVias( vias, [v1, v2])
            
            signalMet.append(makeRect( (-r+(w+s)+centerX, e/2+centerY), (-r+(w+s)+w+centerX, -e/2+centerY)))
            signalMet.append(makeRect( (-1*(-r+(w+s))+centerX, e/2+centerY), (-1*(-r+(w+s)+w)+centerX, -e/2+centerY)))

        if n==3:
            p1,v1 = make45Bridge(w, e, (w+s), 0, centerX-e/2, r-2*(w+s)+s+centerY, True, True, True, viaEnc, viaSize, viaSpace) # Underpass
            p2,v2 = make45Bridge(w, e, (w+s), 0, centerX-e/2, r-2*(w+s)+s+centerY, False, True, False, viaEnc, viaSize, viaSpace) # Underpass
            signalMet.append(makeRect( (e/2+centerX, r-2*(w+s)+centerY), (-e/2+centerX, r-2*(w+s)-w+centerY)))

            appendPoly( signalMet, [p2])
            appendPoly( underMet, [p1])
            appendVias( vias, [v1, v2])

            p1,v1 = make45Bridge(w, e, (w+s), 0, centerX-e/2, -r+1*(w+s)+centerY, False, True, True, viaEnc, viaSize, viaSpace) # Underpass
            p2,v2 = make45Bridge(w, e, (w+s), 0, centerX-e/2, -r+1*(w+s)+centerY, True, True, False, viaEnc, viaSize, viaSpace) # Underpass

            appendPoly( signalMet, [p2])
            appendPoly( underMet, [p1])
            appendVias( vias, [v1, v2])
           
            signalMet.append(makeRect( (-r+(w+s)+centerX, e/2+centerY), (-r+(w+s)+w+centerX, -e/2+centerY)))
            signalMet.append(makeRect( (-1*(-r+(w+s))+centerX, e/2+centerY), (-1*(-r+(w+s)+w)+centerX, -e/2+centerY)))

            signalMet.append(makeRect( (r-2*(w+s)+centerX, e/2+centerY), (r-2*(w+s)-w+centerX, -e/2+centerY)))
            signalMet.append(makeRect( (-r+2*(w+s)+centerX, e/2+centerY), (-r+2*(w+s)+w+centerX, -e/2+centerY)))            

        # Draw connections

        connectSpace = self._connectSpace
        connectLen = self._connectLen
        pl = makeRect( (-w-e/2.0+centerX, -r+centerY+w), (-connectSpace/2.0+centerX, -r+centerY) )
        pr = makeRect( (w+e/2.0+centerX, -r+centerY+w), (connectSpace/2.0+centerX, -r+centerY) )
        

        p1 = makeRect( (-connectSpace/2+centerX, -r+centerY+w), (-w-connectSpace/2.0+centerX, -r-connectLen+centerY) )
        p2 = makeRect( (connectSpace/2.0+centerX, -r+centerY+w), (connectSpace/2.0+w+centerX, -r-connectLen+centerY) )

        #
        # Make port labels
        #
        portLabels = []
        # P1
        X = 0.5*w+connectSpace/2.0+centerX
        Y = -r-connectLen+centerY
        portLabels.append( ((X, Y), 'P1') )
        # P2
        X = -0.5*w-connectSpace/2.0+centerX
        Y = -r-connectLen+centerY
        portLabels.append( ((X, Y), 'P2') )
        #
        # end of port labels
        #

        appendPoly( signalMet, [p1, p2, pl, pr])

        appendPoly( signalMet, [p1, p2])
        Geom = (signalMet, vias, underMet, portLabels)        

        if self._genSubstrateContact:
            # Generate substrate contact
            subRingSpace = self._subRingSpace
            subRingW = self._subRingW
            r = self._r/2+subRingSpace
            s = subRingW
            centerX = self._centerX
            centerY = self._centerY
            geomType = self._geomType
            contEnc = self._contEnc
            contSize = self._contSize
            contSpace = self._contSpace
            diffEnc = self._diffEnc
            subCont = self.makeSubstrateContacts(subRingW, r, s, centerX, centerY, geomType, contEnc, contSize, contSpace, diffEnc)
        else:
            subCont = [[], [], [], [], []]
        return list(Geom) + list(subCont)

    def genGDSII(self, fileName, structName='ind_sym', precision=1e-9):
        """
            Generate symmetric inductor GDSII
        """
        balGeom = self.genGeometry()
        sigPolygons = balGeom[0]
        vias = balGeom[1]
        underPolygons = balGeom[2]
        portLabels = balGeom[3]
       
        balCell = gdspy.Cell(structName)

        sigGDSII = self._tech.getGDSIINumByName(self._signalLayer)  # get signal layer GDSII number
        polySet = gdspy.PolygonSet(sigPolygons, sigGDSII)
        # Merge polygons. If unmerged polygons are desired use balCell.add(polySet)
        result = gdspy.boolean(polySet, None, "or", layer=sigGDSII)
        balCell.add(result)

        upGDSII = self._tech.getGDSIINumByName(self._underPassLayer)  # get signal layer GDSII number
        polySet = gdspy.PolygonSet(underPolygons, upGDSII)
        balCell.add(polySet)

        viaGDSII = self._tech.getGDSIINumByName(self._viaLayer)  # get signal layer GDSII number
        # add vias
        for viaRect in vias:
            balCell.add(gdspy.Rectangle(viaRect[0], viaRect[1], viaGDSII))

        for portLabel in portLabels:
            xy, name = portLabel
            balCell.add(gdspy.Label(name, xy, layer=sigGDSII))

        #
        # Substrate contacts
        #

        # Substrate contacts
        m1Polygons = balGeom[4]
        diffPolygons = balGeom[5]
        impPolygons = balGeom[6]
        subContacts = balGeom[7]
        subPinLabels = balGeom[8]

        if self._genSubstrateContact:
            m1GDSII = self._tech.getGDSIINumByName(self._m1Layer)
            for m1Polygon in m1Polygons:
                poly = gdspy.Polygon(m1Polygon, m1GDSII)
                balCell.add(poly)

            diffGDSII = self._tech.getGDSIINumByName(self._diffLayer)
            contGDSII = self._tech.getGDSIINumByName(self._contLayer)
            for diffPolygon in diffPolygons:
                poly = gdspy.Polygon(diffPolygon, diffGDSII)
                balCell.add(poly)
                if self.emVias:
                    contPolygon = self.oversize(diffPolygon, -self._contEnc)
                    poly = gdspy.Polygon(contPolygon, contGDSII)
                    balCell.add(poly)

            if not self.emVias:
                # add vias
                for viaRect in subContacts:
                    balCell.add(gdspy.Rectangle(viaRect[0], viaRect[1], contGDSII))
             
            impLayer = self._impLayer
            if impLayer != None:
                impGDSII = self._tech.getGDSIINumByName(impLayer)
                for impPolygon in impPolygons:
                    poly = gdspy.Polygon(impPolygon, impGDSII)
                    balCell.add(poly)

            for portLabel in subPinLabels:
                xy, name = portLabel
                balCell.add(gdspy.Label(name, xy, layer=sigGDSII))

        #
        # end of substrate contacts
        #

        lib = gdspy.GdsLibrary(structName, unit = 1.0e-6, precision=precision)
        lib.add(balCell)
        lib.write_gds(fileName)

###############################################################################
#
# Symmetrical inductor with center tap
#
###############################################################################

class inductorSymCT(geomBase):
    """
        Symmetric inductor with center tap
    """

    def __init__(self,tech=None):
        self._tech = tech   # Set the technology

    def setupGeometry(self, r, w, s, n, signalLayer, bridgeLayer, tapLayer, geomType="octagon", centerX = None, centerY = None, subRingSpace=0.0, subRingW=0.0, diffLayer=None, implantLayer=None, contSpaceMult=4.0):
        """
            Setup symmetric inductor geometry
            r : float
                outer inductor dimension
            w : float
                winding line width
            s : foat
                winding spacing
            n : integer
                number of turns
            signalLayer : string
                signal layer name
            bridgeLayer : string
                underpass or overpass layer name
            tapLayer : string
                center tap layer name
            geomType : string
                Type of geometry. Allowed values : "rect", "octagon"
            centerX : float
                Center of inductor x coordinate
            centerY : float
                Center of inductor y coordinate
                
        """
        self._r = r
        self._w = w
        self._s = s
        self._n = n
        self._signalLayer = signalLayer
        self._bridgeLayer = bridgeLayer
        self._tapLayer = tapLayer
        if (geomType != "rect") and (geomType != "octagon"):
            print("WARNING:inductorSymCT::setupGeometry: Unknown geometry type. Setting to octagonal.")
            self._geomType = "octagon"
        else:
            self._geomType = geomType

        if n not in [1,2,3]:
            print("ERROR:inductorSymCT::setupGeometry: n must be 1, 2 or 3.")
            exit(1)

        if int(n) == 3 and (tapLayer in [signalLayer, bridgeLayer]):
            print("ERROR:inductorSymCT::setupGeometry: Signal or bridge layers cannot be the same as the center tap layer for n=3.")
            exit(1)

        if centerX == None:
            self._centerX = 0
        else:
            self._centerX = centerX
            
        if centerY == None:
            self._centerY = 0
        else:
            self._centerY = centerY
            
        # Find via, find via rules
        if self._tech.findViaTopMet(signalLayer) == self._tech.findViaBotMet(bridgeLayer): # try overpass
            bridgeViaLay = self._tech.findViaTopMet(signalLayer)
        elif self._tech.findViaBotMet(signalLayer) == self._tech.findViaTopMet(bridgeLayer): # try underpass
            bridgeViaLay = self._tech.findViaBotMet(signalLayer)              
        else:
            print("ERROR:inductorSymCT: Signal layer and bridge layer must be adjacent layers. ")
            exit(1)

        bridgeViaName = bridgeViaLay.name
        self._bridgeViaLayer = bridgeViaName
        self._bridgeViaEnc = self._tech.getDRCRule(bridgeViaName, "viaEnc")
        self._bridgeViaSize = self._tech.getDRCRule(bridgeViaName, "viaSize")
        self._bridgeViaSpace = self._tech.getDRCRule(bridgeViaName, "viaSpace")

        if signalLayer == tapLayer:
            tapViaLayer = None
        elif self._tech.findViaTopMet(signalLayer) == self._tech.findViaBotMet(tapLayer): # try overpass
            tapViaLayer = self._tech.findViaTopMet(signalLayer)
        elif self._tech.findViaBotMet(signalLayer) == self._tech.findViaTopMet(tapLayer): # try underpass
            tapViaLayer = self._tech.findViaBotMet(signalLayer)              
        else:
            print("ERROR:inductorSymCT: Signal layer and center tap layer must be adjacent layers. ")
            exit(1)
            
        tapViaName = tapViaLayer.name if tapViaLayer != None else None
        self._tapViaLayer = tapViaName if tapViaLayer != None else None
        self._tapViaEnc = self._tech.getDRCRule(tapViaName, "viaEnc") if tapViaLayer != None else None
        self._tapViaSize = self._tech.getDRCRule(tapViaName, "viaSize") if tapViaLayer != None else None
        self._tapViaSpace = self._tech.getDRCRule(tapViaName, "viaSpace") if tapViaLayer != None else None        
        
        #        
        # Substrate ring parameters
        #
        if diffLayer!=None:
            self._genSubstrateContact = True
            contLay = self._tech.findViaBotMet(diffLayer).name
            if contLay == None:
                print("ERROR:inductorSymCT::setupGeometry: Diffusion layer " + diffLayer + " does not have any vias connecting to it from top.")
                return

            self._diffLayer = diffLayer
            self._impLayer = implantLayer
            
            if implantLayer!=None:
                self._diffEnc = self._tech.getDRCRule(implantLayer, "enclosure")
            else:
                self._diffEnc = 0            

            self._contLayer = contLay

            self._contEnc = self._tech.getDRCRule(contLay, "viaEnc")
            self._contSize = self._tech.getDRCRule(contLay, "viaSize")
            self._contSpace = self._tech.getDRCRule(contLay, "viaSpace") * contSpaceMult

            self._m1Layer = self._tech.findTopMetVia(contLay).name
            self._subRingSpace = subRingSpace
            self._subRingW = subRingW
            
        else:
            self._genSubstrateContact = False
          
        # Dimension check: return False if diameter is too small
        return self._r >= self.get_min_diameter()

    def get_min_diameter(self):
        return sym_get_min_diameter(self)

    def genGeometry(self):
        """
        Generate geometry for symetric inductor
        returns polygon collections
        """    

        roundToGrid = self.roundToGrid
        sqrt = math.sqrt
        
        if self._geomType == "octagon":
            makeSegment = self.octSegment
        else:
            makeSegment = self.rectSegment
    
        makeRect = self.makeRect
        make45Bridge = self.make45Bridge
            
        w = self._w
        s = self._s
        n = self._n
        r = roundToGrid(self._r/2)   # outer dimension to radius conversion

        e=roundToGrid(w+s+2*w/(1+sqrt(2))+ 2*s*math.tan(math.radians(22.5)))

        corner_w=roundToGrid((w+s)/2/(1+sqrt(2)))
        corner_w2=roundToGrid((w+s)/2.0/(1+sqrt(2.0)))

        centerX=self._centerX;
        centerY=self._centerY;

        signalMet = list()
        bridgeMet = list()
        tapMet = list()
        bridgeVias = list()
        tapVias = list()
        
        bridgeViaEnc = self._bridgeViaEnc
        bridgeViaSize = self._bridgeViaSize
        bridgeViaSpace = self._bridgeViaSpace

        tapViaEnc = self._tapViaEnc
        tapViaSize = self._tapViaSize
        tapViaSpace = self._tapViaSpace

        for i in range(0,int(n)):
           signalMet.append(makeSegment(w,r-i*(w+s), e/2, 0, centerX, centerY))
           signalMet.append(makeSegment(w,r-i*(w+s), e/2, 1, centerX, centerY))
           signalMet.append(makeSegment(w,r-i*(w+s), e/2, 2, centerX, centerY))
           signalMet.append(makeSegment(w,r-i*(w+s), e/2, 3, centerX, centerY))

        appendPoly = self.appendPoly  
        appendVias = self.appendVias 

        signalMet.append(makeRect( (-1*(-r+0*(w+s))+centerX, e/2+centerY), (-1*(-r+0*(w+s)+w)+centerX, -e/2+centerY)))
        signalMet.append(makeRect( (-r+0*(w+s)+centerX, e/2+centerY), (-r+0*(w+s)+w+centerX, -e/2+centerY)))


        if n==1:
            signalMet.append(makeRect( (e/2+centerX, r+centerY), (-e/2+centerX, r-w+centerY)))
            tapMet.append(makeRect( (w/2+centerX, r-w+centerY), (-w/2+centerX, r+2*w+centerY))) #tap line
            if self._tapViaLayer != None:
                appendVias(tapVias, [self.fillVias(((w/2+centerX, r-w+centerY), (-w/2+centerX, r+centerY)), tapViaEnc, tapViaSize, tapViaSpace)]) #tap vias
            
        if n==2:
              #                  w   e  offx     offy      originX         originY            mir  r90   addVias
            p1,v1 = make45Bridge(w, e, (w+s), 0, centerX-e/2, r-2*(w+s)+s+centerY, True, True, True, bridgeViaEnc, bridgeViaSize, bridgeViaSpace) # Underpass
            p2,v2 = make45Bridge(w, e, (w+s), 0, centerX-e/2, r-2*(w+s)+s+centerY, False, True, False, bridgeViaEnc, bridgeViaSize, bridgeViaSpace) # Underpass
            signalMet.append(makeRect( (e/2+centerX, -r+1*(w+s)+centerY), (-e/2+centerX, -r+1*(w+s)+w+centerY)))

            appendPoly( signalMet, [p2])
            appendPoly( bridgeMet, [p1])
            appendVias( bridgeVias, [v1, v2])
            
            signalMet.append(makeRect( (-r+(w+s)+centerX, e/2+centerY), (-r+(w+s)+w+centerX, -e/2+centerY)))
            signalMet.append(makeRect( (-1*(-r+(w+s))+centerX, e/2+centerY), (-1*(-r+(w+s)+w)+centerX, -e/2+centerY)))

            if self._tapViaLayer != None:
                appendVias(tapVias, [self.fillVias(((w/2+centerX, -r+w+s+centerY), (-w/2+centerX, -r+2*w+s+centerY)), tapViaEnc, tapViaSize, tapViaSpace)])  #tap vias
            
            tapMet.append(makeRect( (w/2+centerX, -r-2*w+centerY), (-w/2+centerX, -r+2*w+s+centerY))) #tap line

        if n==3:
            p1,v1 = make45Bridge(w, e, (w+s), 0, centerX-e/2, r-2*(w+s)+s+centerY, True, True, True, bridgeViaEnc, bridgeViaSize, bridgeViaSpace) # Underpass
            p2,v2 = make45Bridge(w, e, (w+s), 0, centerX-e/2, r-2*(w+s)+s+centerY, False, True, False, bridgeViaEnc, bridgeViaSize, bridgeViaSpace) # Underpass
            signalMet.append(makeRect( (e/2+centerX, r-2*(w+s)+centerY), (-e/2+centerX, r-2*(w+s)-w+centerY)))

            appendPoly( signalMet, [p2])
            appendPoly( bridgeMet, [p1])
            appendVias( bridgeVias, [v1, v2])

            p1,v1 = make45Bridge(w, e, (w+s), 0, centerX-e/2, -r+1*(w+s)+centerY, False, True, True, bridgeViaEnc, bridgeViaSize, bridgeViaSpace) # Underpass
            p2,v2 = make45Bridge(w, e, (w+s), 0, centerX-e/2, -r+1*(w+s)+centerY, True, True, False, bridgeViaEnc, bridgeViaSize, bridgeViaSpace) # Underpass

            appendPoly( signalMet, [p2])
            appendPoly( bridgeMet, [p1])
            appendVias( bridgeVias, [v1, v2])
           
            signalMet.append(makeRect( (-r+(w+s)+centerX, e/2+centerY), (-r+(w+s)+w+centerX, -e/2+centerY)))
            signalMet.append(makeRect( (-1*(-r+(w+s))+centerX, e/2+centerY), (-1*(-r+(w+s)+w)+centerX, -e/2+centerY)))

            signalMet.append(makeRect( (r-2*(w+s)+centerX, e/2+centerY), (r-2*(w+s)-w+centerX, -e/2+centerY)))
            signalMet.append(makeRect( (-r+2*(w+s)+centerX, e/2+centerY), (-r+2*(w+s)+w+centerX, -e/2+centerY)))

            tapMet.append(makeRect( (w/2+centerX, r-3*w-2*s+centerY), (-w/2+centerX, r+2*w+centerY))) #tap line
            if self._tapViaLayer != None:
                appendVias(tapVias, [self.fillVias(((w/2+centerX, r-3*w-2*s+centerY), (-w/2+centerX, r-2*w-2*s+centerY)), tapViaEnc, tapViaSize, tapViaSpace)]) #tap vias                     

#        # Draw connections

        p1 = makeRect( (-e/2+centerX, -r+centerY), (-e/2-w+centerX, -r-2.0*w+centerY) )
        p2 = makeRect( (e/2+centerX, -r+centerY), (e/2+w+centerX, -r-2.0*w+centerY) )
        
        appendPoly( signalMet, [p1, p2])

        #
        # Make port labels
        #
        portLabels = []
        # P1
        X = -e/2-w/2+centerX
        Y = -r-2.0*w+centerY
        portLabels.append( ((X, Y), 'P1') )
        # P2
        X = e/2+w/2+centerX
        Y = -r-2.0*w+centerY
        portLabels.append( ((X, Y), 'P2') )
        if int(n) in [1,3]:
            Y = r + 2*w + centerY
        elif int(n)==2:
            Y = -r - 2*w + centerY
        X = centerX
        portLabels.append(((X, Y), 'CT'))    
        #
        # end of port labels
        #

        Geom = (signalMet, tapMet, bridgeMet, tapVias, bridgeVias, portLabels )        

        if self._genSubstrateContact:
            # Generate substrate contact
            subRingSpace = self._subRingSpace
            subRingW = self._subRingW
            r = self._r/2+subRingSpace
            s = subRingW
            centerX = self._centerX
            centerY = self._centerY
            geomType = self._geomType
            contEnc = self._contEnc
            contSize = self._contSize
            contSpace = self._contSpace
            diffEnc = self._diffEnc
            subCont = self.makeSubstrateContacts(subRingW, r, s, centerX, centerY, geomType, contEnc, contSize, contSpace, diffEnc)
        else:
            subCont = [[], [], [], [], []]
        return list(Geom) + list(subCont)

    def genGDSII(self, fileName, structName='ind_sym', precision=1e-9):
        """
            Generate symmetric inductor GDSII
        """
        balGeom = self.genGeometry()
        sigPolygons = balGeom[0]
        tapPolygons = balGeom[1]
        bridgePolygons = balGeom[2]
        tapVias = balGeom[3]
        bridgeVias = balGeom[4]
        portLabels = balGeom[5]
       
        balCell = gdspy.Cell(structName)

        sigLayerGDSIINum = self._tech.getGDSIINumByName(self._signalLayer)  # get signal layer GDSII number
        sigLayerGDSIIDType = self._tech.getGDSIITypeByName(self._signalLayer) # get signal layer GDSII data type
        polySet = gdspy.PolygonSet(sigPolygons, sigLayerGDSIINum, sigLayerGDSIIDType)
        # Merge polygons. If unmerged polygons are desired use balCell.add(polySet)
        balCell.add(gdspy.boolean(polySet, None, "or", layer = sigLayerGDSIINum, datatype =  sigLayerGDSIIDType))

        tapLayerGDSIINum = self._tech.getGDSIINumByName(self._tapLayer)  # get tap layer GDSII number
        tapLayerGDSIIDType = self._tech.getGDSIITypeByName(self._tapLayer) # get signal layer GDSII data type
        polySet = gdspy.PolygonSet(tapPolygons, tapLayerGDSIINum, tapLayerGDSIIDType)
        balCell.add(polySet)

        bridgeLayerGDSIINum = self._tech.getGDSIINumByName(self._bridgeLayer)  # get bridge layer GDSII number
        bridgeLayerGDSIIDType = self._tech.getGDSIITypeByName(self._bridgeLayer) # get bridge layer GDSII data type
        polySet = gdspy.PolygonSet(bridgePolygons, bridgeLayerGDSIINum, bridgeLayerGDSIIDType)
        balCell.add(polySet)

        bridgeViaGDSIINum = self._tech.getGDSIINumByName(self._bridgeViaLayer)  
        bridgeViaGDSIIDType = self._tech.getGDSIITypeByName(self._bridgeViaLayer)
        # add vias
        for viaRect in bridgeVias:
            balCell.add(gdspy.Rectangle(viaRect[0], viaRect[1], bridgeViaGDSIINum, bridgeViaGDSIIDType))

        tapViaGDSIINum = self._tech.getGDSIINumByName(self._tapViaLayer)  
        tapViaGDSIIDType = self._tech.getGDSIITypeByName(self._tapViaLayer)
        # add vias
        for viaRect in tapVias:
            balCell.add(gdspy.Rectangle(viaRect[0], viaRect[1], tapViaGDSIINum, tapViaGDSIIDType))

        for portLabel in portLabels:
            xy, name = portLabel
            if name in ["P1", "P2"]:
                balCell.add(gdspy.Label(name, xy, layer=sigLayerGDSIINum, texttype=sigLayerGDSIIDType))
            elif name=="CT":
                balCell.add(gdspy.Label(name, xy, layer=tapLayerGDSIINum, texttype=tapLayerGDSIIDType))

        #
        # Substrate contacts
        #

        # Substrate contacts
        m1Polygons = balGeom[6]
        diffPolygons = balGeom[7]
        impPolygons = balGeom[8]
        subContacts = balGeom[9]
        subPinLabels = balGeom[10]

        if self._genSubstrateContact:
            m1GDSII = self._tech.getGDSIINumByName(self._m1Layer)
            for m1Polygon in m1Polygons:
                poly = gdspy.Polygon(m1Polygon, m1GDSII)
                balCell.add(poly)

            diffGDSII = self._tech.getGDSIINumByName(self._diffLayer)
            contGDSII = self._tech.getGDSIINumByName(self._contLayer)
            for diffPolygon in diffPolygons:
                poly = gdspy.Polygon(diffPolygon, diffGDSII)
                balCell.add(poly)
                if self.emVias:
                    contPolygon = self.oversize(diffPolygon, -self._contEnc)
                    poly = gdspy.Polygon(contPolygon, contGDSII)
                    balCell.add(poly)

            if not self.emVias:
                # add vias
                for viaRect in subContacts:
                    balCell.add(gdspy.Rectangle(viaRect[0], viaRect[1], contGDSII))
             
            impLayer = self._impLayer
            if impLayer != None:
                impGDSII = self._tech.getGDSIINumByName(impLayer)
                for impPolygon in impPolygons:
                    poly = gdspy.Polygon(impPolygon, impGDSII)
                    balCell.add(poly)

            for portLabel in subPinLabels:
                xy, name = portLabel
                balCell.add(gdspy.Label(name, xy, layer=m1GDSII))

        #
        # end of substrate contacts
        #

        lib = gdspy.GdsLibrary(structName, unit = 1.0e-6, precision=precision)
        lib.add(balCell)
        lib.write_gds(fileName)



def sym_get_min_diameter(self):
# Calculate the minimum possible diameter for symmetric octagon and rect layout
    N = self._n
    w = self._w
    s = self._s

    crossover_size = 3*w + 2*s

    if hasattr(self, "_viaLayer"):
        viaName = self._viaLayer
    elif hasattr(self, "_bridgeViaLayer"):
        viaName = self._bridgeViaLayer
    else:
        print(f'Could not get via layer name for {self.__class__.__name__}')
        exit(1)

    
    viaEnc   = self._tech.getDRCRule(viaName, "viaEnc")
    viaSize  = self._tech.getDRCRule(viaName, "viaSize")
    viaSpace = self._tech.getDRCRule(viaName, "viaSpace")

    # make sure we don't create a single via 
    size_for_two_vias =  2*viaSize + viaSpace + 2*viaEnc
    overlap_size = w
    if w < size_for_two_vias:
        overlap_size = 1.1*size_for_two_vias

    # there is a minimum crossover width that must be respected
    if self._geomType == "octagon":
        min_crossover_size = (2*s+w)*(math.sqrt(2)-1) + (s+w) +  2*overlap_size
    
        if crossover_size < min_crossover_size:
            crossover_size = min_crossover_size

        if N>1:
            Di_min = crossover_size * (1 + math.sqrt(2))
        else:
            Di_min = 2*(w + s) *(1 + math.sqrt(2))  # for single turn inductor     
    else: 
        # rect
        crossover_size = 3*w + 2*s
        if N>1:
            Di_min = crossover_size + w 
        else:
            Di_min = 4*w*(1 + math.sqrt(2))  # for single turn inductor


    Do_min = (Di_min + 2*N*w + 2*(N-1)*s)
    # round to 2 decimal digits
    Do_min = math.ceil(100*Do_min)/100
    return Do_min


def SE_get_min_diameter(self):
# Calculate the minimum possible diameter for single ended octagon and rect layout
    N = self._n
    w = self._w
    s = self._s

    N_frac, N_full = math.modf(N)
    
    if self._geomType == "octagon":
        Di_min = 3*w+2*s 
    else:    
        Di_min = 2*w+s 

    Do_min = (Di_min + (2*N_full+1)*w + 2*(N-1)*s)
    if self._geomType == "octagon" and N_frac > 0.5:
        Do_min = Do_min + 3.5*w + 4*s
    else:    
        Do_min = Do_min + w + s
    
    # round to 2 decimal digits
    Do_min = math.ceil(100*Do_min)/100
    return Do_min