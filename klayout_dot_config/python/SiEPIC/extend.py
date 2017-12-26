#################################################################################
#                SiEPIC Class Extension of KLayout PYA Library                  #
#################################################################################
'''
This module extends several pya classes that are useful for the library.

pya.Path and pya.DPath Extensions:
  - get_points(), returns list of pya.Points
  - get_dpoints(), returns list of pya.DPoints
  - is_manhattan(), tests to see if the path is manhattan (only the 1st and last segments)
  - radius_check(radius), tests to see of all path segments are long enough to be
    converted to a waveguide with bends of radius 'radius'
  - remove_colinear_points(), removes all colinear points in place
  - unique_points(), remove all but one colinear points
  - translate_from_center(offset), returns a new path whose points have been offset
    by 'offset' from the center of the original path
  - snap(pins), snaps the path in place to the nearest pin
  - to_dtype(dbu), for KLayout < 0.25, integer using dbu to float 
  
pya.Polygon and pya.DPolygon Extensions:
  - get_points(), returns list of pya.Points
  - get_dpoints(), returns list of pya.DPoints
  - to_dtype(dbu), for KLayout < 0.25, integer using dbu to float 
  
pya.PCellDeclarationHelper Extensions:
  - print_parameter_list, prints parameter list
  
pya.Cell Extensions:
  - print_parameter_values, if this cell is a pcell, prints the parameter values
  - find_pins: find Pin object of either the specified name or all pins in a cell
  - find_pin
  - find_pins_component 
  - find_components
  - identify_nets
  - get_LumericalINTERCONNECT_analyzers
  - spice_netlist_export
  - check_component_models

pya.Instance Extensions:
  - find_pins: find Pin objects for all pins in a cell instance

pya.Point Extensions:
  - to_dtype(dbu): for KLayout < 0.25, convert integer Point using dbu to float DPoint

'''
#################################################################################

import pya

warning = pya.QMessageBox()
warning.setStandardButtons(pya.QMessageBox.Ok)
warning.setDefaultButton(pya.QMessageBox.Ok)

#################################################################################
#                SiEPIC Class Extension of Path & DPath Class                   #
#################################################################################

# Function Definitions
#################################################################################

def to_dtype(self, dbu):
  Dpath = pya.DPath(self.get_dpoints(), self.width) * dbu
  Dpath.width = self.width * dbu
  return Dpath

def get_points(self):
  return [pya.Point(pt.x, pt.y) for pt in self.each_point()]

def get_dpoints(self):
  return [pya.DPoint(pt.x, pt.y) for pt in self.each_point()]

def is_manhattan(self):
  if self.__class__ == pya.Path:
    pts = self.get_points()
  else:
    pts = self.get_dpoints()
  check = 1 if len(pts) == 2 else 0
  for i, pt in enumerate(pts):
    if (i==1 or pts[i] == pts[-1]):
      if(pts[i].x == pts[i-1].x or pts[i].y == pts[i-1].y): check += 1
  return check==2
  
def radius_check(self, radius):
  def all2(iterable):
    for element in iterable:
        if not element:
            return False
    return True

  points = self.get_points()
  lengths = [ points[i].distance(points[i-1]) for i, pt in enumerate(points) if i > 0]

  # first and last segment must be >= radius
  check1=(lengths[0] >= radius)
  check2=(lengths[-1] >= radius)
  # middle segments must accommodate two bends, hence >= 2 radius
  check3=[length >= 2*radius for length in lengths[1:-1]]
  return check1 and check2 and all(check3)

# remove all but 1 colinear point
def remove_colinear_points(self):
  from .utils import pt_intersects_segment
  if self.__class__ == pya.Path:
    pts = self.get_points()
  else:
    pts = self.get_dpoints()

  # this version removed all colinear points, which doesn't make sense for a path
  self.points = [pts[0]]+[pts[i] for i in range(1, len(pts)-1) if not pt_intersects_segment(pts[i+1], pts[i-1], pts[i])]+[pts[-1]]

def unique_points(self):
  if self.__class__ == pya.Path:
    pts = self.get_points()
  else:
    pts = self.get_dpoints()

  # only keep unique path points:
  output = []
  for pt in pts:
    if pt not in output:
        output.append(pt)
  self.points = output

  
def translate_from_center(self, offset):
  from math import pi, cos, sin, acos, sqrt
  from .utils import angle_vector
  pts = [pt for pt in self.get_dpoints()]
  tpts = [pt for pt in self.get_dpoints()]
  for i in range(0,len(pts)):
    if i == 0:
      u = pts[i]-pts[i+1]
      v = -u
    elif i == (len(pts) - 1):
      u = pts[i-1]-pts[i]
      v = -u
    else:
      u = pts[i-1]-pts[i]
      v = pts[i+1]-pts[i]

    if offset < 0:
      o1 = pya.DPoint(abs(offset)*cos(angle_vector(u)*pi/180-pi/2), abs(offset)*sin(angle_vector(u)*pi/180-pi/2))
      o2 = pya.DPoint(abs(offset)*cos(angle_vector(v)*pi/180+pi/2), abs(offset)*sin(angle_vector(v)*pi/180+pi/2))
    else:
      o1 = pya.DPoint(abs(offset)*cos(angle_vector(u)*pi/180+pi/2), abs(offset)*sin(angle_vector(u)*pi/180+pi/2))
      o2 = pya.DPoint(abs(offset)*cos(angle_vector(v)*pi/180-pi/2), abs(offset)*sin(angle_vector(v)*pi/180-pi/2))
      
    p1 = u+o1
    p2 = o1
    p3 = v+o2
    p4 = o2
    d = (p1.x-p2.x)*(p3.y-p4.y)-(p1.y-p2.y)*(p3.x-p4.x)

    if round(d,10) == 0:
      tpts[i] += p2
    else:
      tpts[i] += pya.DPoint(((p1.x*p2.y-p1.y*p2.x)*(p3.x-p4.x)-(p1.x-p2.x)*(p3.x*p4.y-p3.y*p4.x))/d,
                           ((p1.x*p2.y-p1.y*p2.x)*(p3.y-p4.y)-(p1.y-p2.y)*(p3.x*p4.y-p3.y*p4.x))/d)

  if self.__class__ == pya.Path:
    return pya.Path([pya.Point(pt.x, pt.y) for pt in tpts], self.width)
  elif self.__class__ == pya.DPath:
    return pya.DPath(tpts, self.width)
    
'''
snap - pya.Path extension
This function snaps the two path endpoints to the nearest pins by adjusting the end segments

Input: 
 - self: the Path object
 - pins: an array of Pin objects, which are paths with 2 points, 
         with the vector giving the direction (out of the component)
Output:
 - modifies the original Path

'''
def snap(self, pins):
  # Import functionality from SiEPIC-Tools:
  from .utils import angle_vector, get_technology
  from . import _globals
  TECHNOLOGY = get_technology()
    
  # Search for pins within this distance to the path endpoints, e.g., 10 microns
  d_min = _globals.PATH_SNAP_PIN_MAXDIST/TECHNOLOGY['dbu'];

  if not len(pins): return

  # array of path vertices:
  pts = self.get_points()

  # angles of all segments:
  ang = angle_vector(pts[1]-pts[0])
  
  # sort all the pins based on distance to the Path endpoint
  # only consider pins that are facing each other, 180 degrees 
  pins_sorted = sorted([pin for pin in pins if round((ang - pin.rotation)%360) == 180 and pin.type == _globals.PIN_TYPES.OPTICAL], key=lambda x: x.center.distance(pts[0]))

  if len(pins_sorted):
    # pins_sorted[0] is the closest one
    dpt = pins_sorted[0].center - pts[0]
    # check if the pin is close enough to the path endpoint
    if dpt.abs() <= d_min:
      # snap the endpoint to the pin
      pts[0] += dpt
      # move the first corner
      if(round(ang % 180) == 0):
        pts[1].y += dpt.y
      else:
        pts[1].x += dpt.x
        
  # do the same thing on the other end:  
  ang = angle_vector(pts[-2]-pts[-1])
  pins_sorted = sorted([pin for pin in pins if round((ang - pin.rotation)%360) == 180 and pin.type == _globals.PIN_TYPES.OPTICAL], key=lambda x: x.center.distance(pts[-1]))
  if len(pins_sorted):
    dpt = pins_sorted[0].center - pts[-1]
    if dpt.abs() <= d_min:
      pts[-1] += dpt
      if(round(ang % 180) == 0):
        pts[-2].y += dpt.y
      else:
        pts[-2].x += dpt.x

  # check that the path has non-zero length after the snapping operation
  test_path = pya.Path()
  test_path.points = pts
  if test_path.length() > 0:
    self.points = pts

# Path Extension
#################################################################################

pya.Path.to_dtype = to_dtype
pya.Path.get_points = get_points
pya.Path.get_dpoints = get_dpoints
pya.Path.is_manhattan = is_manhattan
pya.Path.radius_check = radius_check
pya.Path.remove_colinear_points = remove_colinear_points
pya.Path.unique_points = unique_points
pya.Path.translate_from_center = translate_from_center
pya.Path.snap = snap;

# DPath Extension
#################################################################################

pya.DPath.to_dtype = to_dtype
pya.DPath.get_points = get_points
pya.DPath.get_dpoints = get_dpoints
pya.DPath.is_manhattan = is_manhattan
pya.DPath.radius_check = radius_check
pya.DPath.remove_colinear_points = remove_colinear_points
pya.DPath.unique_points = unique_points
pya.DPath.translate_from_center = translate_from_center
pya.DPath.snap = snap;

#################################################################################
#            SiEPIC Class Extension of Polygon & DPolygon Class                 #
#################################################################################

# Function Definitions
#################################################################################

def get_points(self):
  return [pya.Point(pt.x, pt.y) for pt in self.each_point_hull()]

def get_dpoints(self):
  return [pya.DPoint(pt.x, pt.y) for pt in self.each_point_hull()]

def to_dtype(self,dbu):
  pts = self.get_points()
  pts1 = [ p.to_dtype(dbu) for p in pts ]
  return pya.DPolygon(pts1)

#################################################################################

pya.Polygon.get_points = get_points;
pya.Polygon.get_dpoints = get_dpoints;
pya.Polygon.to_dtype = to_dtype;

#################################################################################

pya.DPolygon.get_points = get_points;
pya.DPolygon.get_dpoints = get_dpoints;

#################################################################################
#                    SiEPIC Class Extension of PCell Class                      #
#################################################################################

# Function Definitions
#################################################################################

def print_parameter_list(self):
  types = ['TypeBoolean', 'TypeDouble', 'TypeInt', 'TypeLayer', 'TypeList', 'TypeNone', 'TypeShape', 'TypeString']
  for p in self.get_parameters():
    if ~p.readonly:
      print( "Name: %s, %s, unit: %s, default: %s, description: %s%s" % \
        (p.name, types[p.type], p.unit, p.default, p.description, ", hidden" if p.hidden else ".") )

#################################################################################

pya.PCellDeclarationHelper.print_parameter_list = print_parameter_list
  
#################################################################################
#                    SiEPIC Class Extension of Cell Class                       #
#################################################################################

# Function Definitions
#################################################################################

def print_parameter_values(self):
  print(self.pcell_parameters())
  params = self.pcell_parameters_by_name()
  for key in params.keys():
    print("Parameter: %s, Value: %s") % (key, params[key])

'''
Optical Pins have: 
 1) path on layer PinRec, indicating direction (out of component)
 2) text on layer PinRec, inside the path
Electrical Pins have: 
 1) box on layer PinRec, indicating direction (out of component)
 2) text on layer PinRec, inside the path
'''
def find_pins(self, verbose=False):
  from .core import Pin
  from . import _globals
  from .utils import get_technology
  TECHNOLOGY = get_technology()

  # array to store Pin objects
  pins = []
  
  # Pin Recognition layer
  LayerPinRecN = self.layout().layer(TECHNOLOGY['PinRec'])

  # iterate through all the PinRec shapes in the cell
  it = self.begin_shapes_rec(LayerPinRecN)
  while not(it.at_end()):
    # Assume a PinRec Path is an optical pin
    if it.shape().is_path():
      if verbose:
        print ("Path: %s" % it.shape() )
      # get the pin path
      pin_path = it.shape().path.transformed(it.itrans())
      # Find text label (pin name) for this pin by searching inside the Path bounding box
      # Text label must be on DevRec layer
      pin_name = None
      subcell = it.cell()  # cell (component) to which this shape belongs
      iter2 = subcell.begin_shapes_rec_touching(LayerPinRecN, it.shape().bbox())
      while not(iter2.at_end()):
        if iter2.shape().is_text():
          pin_name = iter2.shape().text.string
        iter2.next()
      if pin_name == None:
        raise Exception("Invalid pin Path detected: %s.\nOptical Pins must have a pin name." % pin_path)
      # Store the pin information in the pins array
      pins.append(Pin(path=pin_path, _type=_globals.PIN_TYPES.OPTICAL, pin_name=pin_name))

    # Assume a PinRec Box is an electrical pin
    # similar to optical pin
    if it.shape().is_box():
#      print ("Box: %s" % it.shape() )
      pin_box = it.shape().box.transformed(it.itrans())
      pin_name = None
      subcell = it.cell()  # cell (component) to which this shape belongs
      iter2 = subcell.begin_shapes_rec_touching(LayerPinRecN, it.shape().bbox())
#      print ("Box: %s" % it.shape().bbox() )
      while not(iter2.at_end()):
#        print ("shape touching: %s" % iter2.shape() )
        if iter2.shape().is_text():
          pin_name = iter2.shape().text.string
        iter2.next()
      if pin_name == None:
        raise Exception("Invalid pin Box detected: %s.\nElectrical Pins must have a pin name." % pin_box)
      pins.append(Pin(box=pin_box, _type=_globals.PIN_TYPES.ELECTRICAL, pin_name=pin_name))
      
    it.next()

  # Optical IO (Fibre) Recognition layer
  LayerFbrTgtN = self.layout().layer(TECHNOLOGY['FbrTgt'])

  # iterate through all the FbrTgt shapes in the cell
  it = self.begin_shapes_rec(LayerFbrTgtN)
  while not(it.at_end()):
    # Assume a FbrTgt Path is an optical pin
    if it.shape().is_polygon():
      # Store the pin information in the pins array
      pins.append(Pin(path=it.shape().polygon.transformed(it.itrans()),
         _type=_globals.PIN_TYPES.OPTICALIO, 
         pin_name=self.basic_name().replace(' ', '_')))
#         pin_name=it.cell().basic_name())) # 'OpticalFibre 9micron'
    it.next()

  # return the array of pins
  return pins
  
def find_pin(self, name):
  from . import _globals
  from .core import Pin
  pins = []
  label = None
  it = self.begin_shapes_rec(self.layout().layer(_globals.TECHNOLOGY['PinRec']))
  while not(it.at_end()):
    if it.shape().is_path():
      pins.append(it.shape().path.transformed(it.itrans()))
    if it.shape().is_text() and it.shape().text.string == name:
      label = it.shape().text.transformed(it.itrans())
    it.next()
    
  if label is None: return None
  
  for pin in pins:
    pts = pin.get_points()
    if (pts[0]+pts[1])*0.5 == pya.Point(label.x, label.y):
      return Pin(pin, _globals.PIN_TYPES.OPTICAL)
    
  return None

# find the pins inside a component
def find_pins_component(self, component):
  pins = self.find_pins()
  for p in pins:
    # add component to the pin
    p.component = component
  return pins

'''
Components:
'''
def find_components(self, verbose=False):
  '''
  Function to traverse the cell's hierarchy and find all the components
  returns list of components (class Component)
  Use the DevRec shapes.  Assumption: One DevRec shape per component.
  
  Find all the DevRec shapes; identify the component it belongs; record the info as a Component 
  for each component instance, also find the Pins and Fibre ports.
  
  Find all the pins for the component, save in components and also return pin list.
  Use the pin names on layer PinRec to sort the pins in alphabetical order
  '''
  if verbose:
    print('*** Cell.find_components:')
  
  components = []

  from .core import Component
  from . import _globals
  from .utils import get_technology
  TECHNOLOGY = get_technology()
  dbu = TECHNOLOGY['dbu']

  # Find all the DevRec shapes
  LayerDevRecN = self.layout().layer(TECHNOLOGY['DevRec'])
  iter1 = self.begin_shapes_rec(LayerDevRecN)
  
  while not(iter1.at_end()):
    idx = len(components) # component index value to be assigned to Component.idx
    subcell = iter1.cell() # cell (component) to which this shape belongs
    component = subcell.basic_name().replace(' ','_')   # name library component
    instance = subcell.name      
#    subcell.name                # name of the cell; for PCells, different from basic_name

    found_component = False
    # DevRec must be either a Box or a Polygon:
    if iter1.shape().is_box():
      box= iter1.shape().box.transformed(iter1.itrans())
      if verbose:
        print("%s: DevRec in cell {%s}, box -- %s; %s" % (idx, subcell.basic_name(), box.p1, box.p2) )
      polygon = pya.Polygon(box) # Save the component outline polygon
      found_component = True
    if iter1.shape().is_polygon():
      polygon = iter1.shape().polygon.transformed(iter1.itrans()) # Save the component outline polygon
      if verbose:
        print("%s: DevRec in cell {%s}, polygon -- %s" % (idx, subcell.basic_name(), polygon))
      found_component = True

    # A component was found. record the instance info as an Optical_component 
    if found_component:
      # check if the component is flattened, or a hierarchical sub-cell
      if self == subcell: 
        # Save the flattened component into the components list
        components.append( Component(component = "Flattened", basic_name = "Flattened", idx=idx, polygon=polygon, trans=iter1.trans() ) )
      else:
        # Find text label for DevRec, to get Library name
        library = None
        # *** use of subcell assumes that the shapes are hierarchical within the component
        # for flat layout... check within the DevRec shape.
        iter2 = subcell.begin_shapes_rec(LayerDevRecN)
        spice_params = ""
        while not(iter2.at_end()):
          if iter2.shape().is_text():
            text = iter2.shape().text
            if verbose:
              print("%s: DevRec label: %s" % (idx, text))
            if text.string.find("Lumerical_INTERCONNECT_library=") > -1:
              library = text.string[len("Lumerical_INTERCONNECT_library="):]
            if text.string.find("Lumerical_INTERCONNECT_component=") > -1:
              component = text.string[len("Lumerical_INTERCONNECT_component="):]
            if text.string.find("Spice_param:") > -1:
              spice_params = text.string[len("Spice_param:"):]
          iter2.next()
        if library == None:
          if verbose:
            print("Missing library information for component: %s" % component )
  
        # Save the component into the components list      
        components.append(Component(idx=idx, \
           component=component, instance=instance, trans=iter1.trans(), library=library, params=spice_params, polygon=polygon, cell=subcell, basic_name=subcell.basic_name()) )
  
        # find the component pins, and Sort by pin text labels
        pins = sorted(subcell.find_pins_component(components[-1]), key=lambda  p: p.pin_name)
  
        # find_pins returns pin locations within the subcell; transform to the top cell:
        [p.transform(iter1.trans()) for p in pins]
  
        # store the pins in the component
        components[-1].pins=pins

    iter1.next()
  # end while iter1 
  return components
# end def find_components
  


def identify_nets(self, verbose=False):
  # function to identify all the nets in the cell layout
  # use the data in Optical_pin, Optical_waveguide to find overlaps
  # and save results in components

  from . import _globals
  from .core import Net

  # output: array of Net[]
  nets = []

  # find components and pins in the cell layout
  components = self.find_components()
  pins = self.find_pins()
  
  # Optical Pins:
  optical_pins = [p for p in pins if p.type==_globals.PIN_TYPES.OPTICAL]
  
  # Loop through all pairs components (c1, c2); only look at touching components
  for c1 in components:
    for c2 in components [ c1.idx+1: len(components) ]:
      if verbose:
        print( " - Components: [%s-%s], [%s-%s]"
          % (c1.component, c1.idx, c2.component, c2.idx) )      

      if c1.polygon.bbox().overlaps(c2.polygon.bbox()) or c1.polygon.bbox().touches(c2.polygon.bbox()):
        # Loop through all the pins (p1) in c1
        # - Compare to all other pins, find other overlapping pins (p2) in c2
        for p1 in c1.pins:
          for p2 in c2.pins:
            if 0:
              print( " - Components, pins: [%s-%s, %s, %s, %s], [%s-%s, %s, %s, %s]"
                % (c1.component, c1.idx, p1.pin_name, p1.center, p1.rotation, c2.component, c2.idx, p2.pin_name, p2.center, p2.rotation) )      
      
            # check that pins are facing each other, 180 degree
            check1 = ((p1.rotation - p2.rotation)%360) == 180
      
            # check that the pin centres are perfectly overlapping 
            # (to avoid slight disconnections, and phase errors in simulations)
            check2 = (p1.center == p2.center)
      
            if check1 and check2:  # found connected pins:
              # make a new optical net index
              net_idx = len(nets)
              # optical net connects two pins; keep track of the pins, Pin[] :
              nets.append ( Net ( idx=net_idx, pins=[p1, p2] ) )
              # assign this net number to the pins
              p1.net = nets[-1]
              p2.net = nets[-1]
              
              if verbose:
                print( " - pin-pin, net: %s, component, pin: [%s-%s, %s, %s, %s], [%s-%s, %s, %s, %s]" 
                  % (net_idx, c1.component, c1.idx, p1.pin_name, p1.center, p1.rotation, c2.component, c2.idx, p2.pin_name, p2.center, p2.rotation) )      
      
  return nets, components

def get_LumericalINTERCONNECT_analyzers(self, components, verbose=None):
  """
  Find - LumericalINTERCONNECT_Laser
       - LumericalINTERCONNECT_Detector
  get their parameters
  determine which OpticalIO they are connected to, and find their nets
  Assume that the detectors and laser are on the topcell (not subcells); don't perform transformations.
  
  returns: parameters, nets in order
  
  usage:
  laser_net, detector_nets, wavelength_start, wavelength_stop, wavelength_points, ignoreOpticalIOs = get_LumericalINTERCONNECT_analyzers(topcell, optical_pins)
  """

  topcell = self

  from . import _globals
  from .utils import select_paths, get_technology
  from .core import Net
  TECHNOLOGY = get_technology()
  
  layout = topcell.layout()
  LayerLumericalN = self.layout().layer(TECHNOLOGY['Lumerical'])

  # data structure used to find the detectors and which optical nets they are connected to.
  class Detector_info:
    def __init__(self, detector_net, detector_number):
      self.detector_net = detector_net
      self.detector_number = detector_number
  detectors_info = []  
  
  # default is the 1st polarization
  orthogonal_identifier = 1
      
  # Find the laser and detectors in the layout.
  iter1 = topcell.begin_shapes_rec(LayerLumericalN)
  n_IO = 0
  laser_net = None
  wavelength_start, wavelength_stop, wavelength_points, orthogonal_identifier, ignoreOpticalIOs = 0,0,0,0,0
  while not(iter1.at_end()):
    subcell = iter1.cell()             # cell (component) to which this shape belongs
    if iter1.shape().is_box():
      box = iter1.shape().box.transformed(iter1.itrans())
      if iter1.cell().basic_name() == "Lumerical INTERCONNECT Detector":
        n_IO += 1
        # *** todo read parameters from Text labels rather than PCell:
        detector_number = subcell.pcell_parameters_by_name()["number"]
        if verbose:
          print("%s: Detector {%s} %s, box -- %s; %s"   % (n_IO, subcell.basic_name(), detector_number, box.p1, box.p2) )
        # find components which have an IO pin inside the Lumerical box:
        components_IO = [ c for c in components if any( [box.contains(p.center) for p in c.pins if p.type == _globals.PIN_TYPES.OPTICALIO] ) ]
        if len(components_IO) > 1:
          raise Exception("Error - more than 1 optical IO connected to the detector.")
        if len(components_IO) == 0:
           print("Warning - No optical IO connected to the detector.") 
#          raise Exception("Error - 0 optical IO connected to the detector.")
        else:
          p = [p for p in components_IO[0].pins if p.type == _globals.PIN_TYPES.OPTICALIO]
          p[0].pin_name += '_detector' + str(n_IO)
          p[0].net=Net(idx=p[0].pin_name, pins=p)
          detectors_info.append(Detector_info(p[0].net, detector_number) )
          if verbose:
            print(" - pin_name: %s"   % (p[0].pin_name) )

      if iter1.cell().basic_name() == "Lumerical INTERCONNECT Laser":
        n_IO += 1
        # *** todo read parameters from Text labels rather than PCell:
        wavelength_start = subcell.pcell_parameters_by_name()["wavelength_start"]
        wavelength_stop = subcell.pcell_parameters_by_name()["wavelength_stop"]
        wavelength_points = subcell.pcell_parameters_by_name()["npoints"]
        orthogonal_identifier = subcell.pcell_parameters_by_name()["orthogonal_identifier"]
        ignoreOpticalIOs = subcell.pcell_parameters_by_name()["ignoreOpticalIOs"]
        if verbose:
          print("%s: Laser {%s}, box -- %s; %s"   % (n_IO, subcell.basic_name(), box.p1, box.p2) )
        # find components which have an IO pin inside the Lumerical box:
        components_IO = [ c for c in components if any( [box.contains(p.center) for p in c.pins if p.type == _globals.PIN_TYPES.OPTICALIO] ) ]
        if len(components_IO) > 1:
          raise Exception("Error - more than 1 optical IO connected to the laser.")
        if len(components_IO) == 0:
          print("Warning - No optical IO connected to the laser.")
#          raise Exception("Error - 0 optical IO connected to the laser.")
        else:
          p = [p for p in components_IO[0].pins if p.type == _globals.PIN_TYPES.OPTICALIO]
          p[0].pin_name += '_laser' + str(n_IO)
          laser_net = p[0].net=Net(idx=p[0].pin_name, pins=p)
          if verbose:
            print(" - pin_name: %s"   % (p[0].pin_name) )

    iter1.next()
    
  # Sort the detectors:
  detectors_info2 = sorted(detectors_info, key=lambda  d: d.detector_number)
    
  # output:
  detector_nets = []
  for d in detectors_info2:
    detector_nets.append (d.detector_net)

  return laser_net, detector_nets, wavelength_start, wavelength_stop, wavelength_points, orthogonal_identifier, ignoreOpticalIOs
    

def spice_netlist_export(self, verbose = False):
  # list all Optical_component objects from an array
  # input array, optical_components
  # example output:         
  # X_grating_coupler_1 N$7 N$6 grating_coupler library="custom/genericcml" sch_x=-1.42 sch_y=-0.265 sch_r=0 sch_f=false
  import SiEPIC
  from . import _globals
  from time import strftime 
  from .utils import eng_str

  text_main = '* Spice output from KLayout SiEPIC-Tools v%s, %s.\n\n' % (SiEPIC.__version__, strftime("%Y-%m-%d %H:%M:%S") )
  text_subckt = text_main

  nets, components = self.identify_nets ()

  # convert KLayout GDS rotation/flip to Lumerical INTERCONNECT
  # KLayout defines mirror as an x-axis flip, whereas INTERCONNECT does y-axis flip
  # KLayout defines rotation as counter-clockwise, whereas INTERCONNECT does clockwise
  # input is KLayout Rotation,Flip; output is INTERCONNECT:
  KLayoutInterconnectRotFlip = \
      {(0, False):[0, False], \
       (90, False):[270, False], \
       (180, False):[180, False], \
       (270, False):[90, False], \
       (0, True):[180,True], \
       (90, True):[90, True], \
       (180, True):[0,True], \
       (270, True):[270, False]}

  # Determine the Layout-to-Schematic (x,y) coordinate scaling       
  # Find the distances between all the components, in order to determine scaling
  sch_positions = [o.Dcenter for o in components]
  sch_distances = [1e6]
  for j in range(len(sch_positions)):
    for k in range(j+1,len(sch_positions)):
      dist = (sch_positions[j] - sch_positions[k]).abs()
      sch_distances.append ( dist )
  sch_distances.sort()
  if verbose:
    print("Distances between components: %s" % sch_distances)
  # remove any 0 distances:
  while 0.0 in sch_distances: sch_distances.remove(0.0)
  # scaling based on nearest neighbour:
  Lumerical_schematic_scaling = 0.0006 / min(sch_distances)
  # but if the layout is too big, limit the size
  MAX_size = 0.05
  if max(sch_distances)*Lumerical_schematic_scaling > MAX_size:
    Lumerical_schematic_scaling = MAX_size / max(sch_distances) 
  print ("Scaling for Lumerical INTERCONNECT schematic: %s" % Lumerical_schematic_scaling)

  # find electrical IO pins
  electricalIO_pins = ""
  DCsources = "" # string to create DC sources for each pin
  Vn = 1
  SINGLE_DC_SOURCE = 2
  # (1) attach all electrical pins to the same DC source
  # (2) or to individual DC sources
  # (3) or choose based on number of DC sources, if &gt; 5, use single DC source
  for c in components:
    for p in c.pins:
      if p.type == _globals.PIN_TYPES.ELECTRICAL:
        NetName = " " + c.component +'_' + str(c.idx) + '_' + p.pin_name
        electricalIO_pins += NetName
        DCsources += "N" + str(Vn) + NetName + " 0 dcsource amplitude=0 sch_x=%s sch_y=%s\n" % (-2-Vn/10., -2+Vn/8.)
        Vn += 1
  electricalIO_pins_subckt = electricalIO_pins

  if (SINGLE_DC_SOURCE == 1) or ( (SINGLE_DC_SOURCE == 2) and (Vn > 5)):
    electricalIO_pins_subckt = ""
    for c in components:
      for p in c.pins:
        if p.type == _globals.PIN_TYPES.ELECTRICAL:
          NetName = " " + c.component +'_' + str(c.idx) + '_' + p.pin_name
          electricalIO_pins_subckt += NetName
          DCsources = "N1" + NetName + " 0 dcsource amplitude=0 sch_x=-2 sch_y=0\n"

  # Get information about the laser and detectors:
  # this updates the Optical IO Net
  laser_net, detector_nets, wavelength_start, wavelength_stop, wavelength_points, orthogonal_identifier, ignoreOpticalIOs = \
        get_LumericalINTERCONNECT_analyzers(self, components, verbose=verbose)

  # find optical IO pins
  opticalIO_pins=''
  for c in components:
    for p in c.pins:
      if p.type == _globals.PIN_TYPES.OPTICALIO:
        NetName =  ' ' + p.pin_name
        print(p.pin_name)
        opticalIO_pins += NetName

  # create the top subckt:
  text_subckt += '.subckt %s%s%s\n' % (self.name, electricalIO_pins, opticalIO_pins)
  text_subckt += '.param MC_uniformity_width=0 \n' # assign MC settings before importing netlist components
  text_subckt += '.param MC_uniformity_thickness=0 \n' 
  text_subckt += '.param MC_resolution_x=100 \n' 
  text_subckt += '.param MC_resolution_y=100 \n' 
  text_subckt += '.param MC_grid=10e-6 \n' 
  text_subckt += '.param MC_non_uniform=99 \n' 

  for c in components:
    # optical nets: must be ordered electrical, optical IO, then optical
    nets_str = ''
    for p in c.pins:
      if p.type == _globals.PIN_TYPES.ELECTRICAL:
        nets_str += " " + c.component +'_' + str(c.idx) + '_' + p.pin_name
    for p in c.pins:
      if p.type == _globals.PIN_TYPES.OPTICALIO:
        nets_str += " " + str(p.net.idx)
    for p in c.pins:
      if p.type == _globals.PIN_TYPES.OPTICAL:
        nets_str += " N$" + str(p.net.idx)


    trans = KLayoutInterconnectRotFlip[(c.trans.angle, c.trans.is_mirror())]
     
    flip = ' sch_f=true' if trans[1] else ''
    if trans[0] > 0:
      rotate = ' sch_r=%s' % str(trans[0])
    else:
      rotate = ''

    # Check to see if this component is an Optical IO type.
    pinIOtype = any([p for p in c.pins if p.type == _globals.PIN_TYPES.OPTICALIO])
        
    if ignoreOpticalIOs and pinIOtype:
      # Replace the Grating Coupler or Edge Coupler with a 0-length waveguide.
      component1 = "ebeam_wg_strip_1550"
      params1 = "wg_length=0u wg_width=0.500u"
    else:
      component1 =  o.component 
      params1 = o.params
      
    text_subckt += ' %s %s %s ' % ( c.component.replace(' ', '_') +"_"+str(c.idx), nets_str, c.component.replace(' ', '_') ) 
    if c.library != None:
      text_subckt += 'library="%s" ' % c.library
    x, y = c.Dcenter.x, c.Dcenter.y
    text_subckt += '%s lay_x=%s lay_y=%s sch_x=%s sch_y=%s %s%s\n' % \
       ( c.params,
         eng_str(x * 1e-6), eng_str(y * 1e-6), \
         eng_str(x * Lumerical_schematic_scaling), eng_str(y * Lumerical_schematic_scaling), \
         rotate, flip)


  text_subckt += '.ends %s\n\n' % (self.name)

  if laser_net:
    text_main += '* Optical Network Analyzer:\n'
    text_main += '.ona input_unit=wavelength input_parameter=start_and_stop\n  + minimum_loss=80\n  + analysis_type=scattering_data\n  + multithreading=user_defined number_of_threads=1\n' 
    text_main += '  + orthogonal_identifier=%s\n' % orthogonal_identifier
    text_main += '  + start=%4.3fe-9\n' % wavelength_start
    text_main += '  + stop=%4.3fe-9\n' % wavelength_stop
    text_main += '  + number_of_points=%s\n' % wavelength_points
    for i in range(0,len(detector_nets)):
      text_main += '  + input(%s)=%s,%s\n' % (i+1, self.name, detector_nets[i].idx)
    text_main += '  + output=%s,%s\n' % (self.name, laser_net.idx)

  # main circuit
  text_main += '%s %s %s %s sch_x=-1 sch_y=-1 ' % (self.name, electricalIO_pins_subckt, opticalIO_pins, self.name)
  if len(DCsources) > 0:
    text_main += 'sch_r=270\n\n'
  else:
    text_main += '\n\n'

  text_main += DCsources

  return text_subckt, text_main, len(detector_nets)

def check_components_models():
  
  # Check if all the components in the cell have compact models loaded in INTERCONNECT
  
  # test for Component.has_compactmodel()
  from .utils import get_layout_variables
  TECHNOLOGY, lv, ly, cell = get_layout_variables()
  
  print ("* find_components()" )
  components = cell.find_components ()
  print ("* Display list of components" )
  
  if not all([c.has_model() for c in components]):
    # missing models, find which one
    components_havemodels = [[c.has_model(), c.component, c.instance] for c in components]
    missing_models = []
    for c in components_havemodels:
      if c[0] == False:
        missing_models.append([c[1],c[2]])
    missing = ("We have %s component(s) missing models, as follows: %s" % (len(missing_models), missing_models))
    v = pya.MessageBox.warning("Errors", missing, pya.MessageBox.Ok)
  else:
    print('check_components_models(): all models are present.')



#################################################################################

pya.Cell.print_parameter_values = print_parameter_values
pya.Cell.find_pin = find_pin
pya.Cell.find_pins = find_pins
pya.Cell.find_pins_component = find_pins_component
pya.Cell.find_components = find_components
pya.Cell.identify_nets = identify_nets
pya.Cell.get_LumericalINTERCONNECT_analyzers = get_LumericalINTERCONNECT_analyzers
pya.Cell.spice_netlist_export = spice_netlist_export

#################################################################################
#                    SiEPIC Class Extension of Instance Class                   #
#################################################################################

# Function Definitions
#################################################################################

def find_pins(self):

  return [pin.transform(self.trans) for pin in self.cell.find_pins()]
  
#################################################################################

pya.Instance.find_pins = find_pins


#################################################################################
#                    SiEPIC Class Extension of Point Class                      #
#################################################################################

# multiply an integer Point by a constant to get a float DPoint
# new DPoint = Point.to_dtype(TECHNOLOGY['dbu'])
# in v > 0.25, is built-in to KLayout
if int(pya.Application.instance().version().split('.')[1]) < 25:
  def to_dtype(self,dbu):
    # create a new empty list.  Otherwise, this function would modify the original list
    # http://stackoverflow.com/questions/240178/python-list-of-lists-changes-reflected-across-sublists-unexpectedly
    return pya.DPoint(self.x * dbu, self.y * dbu)

  # KLayout v0.25 introduced technology variable:
  pya.Point.to_dtype = to_dtype
