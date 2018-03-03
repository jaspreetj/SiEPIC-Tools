'''
################################################################################
#
#  SiEPIC-Tools
#  
################################################################################

Circuit simulations using Lumerical INTERCONNECT and a Compact Model Library

- run_INTC: run INTERCONNECT using Python integration
- INTC_commandline: invoke INTC via the command line, with an lsf file as input.
- Setup_Lumerical_KLayoutPython_integration
    Configure PATH env, import lumapi, run interconnect, 
    Install technology CML, read CML elements
- circuit_simulation: netlist extract and run simulation
- circuit_simulation_update_netlist: update netlist and run simulation
- circuit_simulation_monte_carlo: perform many simulations
- component_simulation: single component simulation

usage:
 import SiEPIC.lumerical.interconnect


################################################################################
'''

try:
  INTC
except:
  INTC = None  
  # print('resetting Lumerical INTERCONNECT Python integration')

import sys
if 'pya' in sys.modules: # check if in KLayout
  import pya

def run_INTC(verbose=False):

  if verbose:
    print("SiEPIC.lumerical.interconnect.run_INTC()")  # Python Lumerical INTERCONNECT integration handle

  from . import load_lumapi
  lumapi = load_lumapi.LUMAPI
  global INTC

  if not lumapi:
    print("SiEPIC.lumerical.interconnect.run_INTC: lumapi not loaded; reloading load_lumapi.")
    import sys
    if sys.version_info[0] == 3:
        if sys.version_info[1] < 4:
            from imp import reload
        else:
            from importlib import reload
    elif sys.version_info[0] == 2:
        from imp import reload    
    reload(load_lumapi)

  if not lumapi:
    print("SiEPIC.lumerical.interconnect.run_INTC: lumapi not loaded")
    pya.MessageBox.warning("Cannot load Lumerical Python integration.", "Cannot load Lumerical Python integration. \nSome SiEPIC-Tools Lumerical functionality will not be available.", pya.MessageBox.Cancel)
      #    warning = pya.QMessageBox()
      #    warning.setStandardButtons(pya.QMessageBox.Cancel)
      #    warning.setText("Cannot load Lumerical Python integration.") 
      #    warning.setInformativeText("Some SiEPIC-Tools Lumerical functionality will not be available.")
      #    pya.QMessageBox_StandardButton(warning.exec_())
    return
    
  
  if verbose:
    print("Checking INTERCONNECT integration handle: %s" % INTC)  # Python Lumerical INTERCONNECT integration handle
  
  if not INTC: # Not running, start a new session
    INTC = lumapi.open('interconnect')
    if verbose:
      print("Started new session. INTERCONNECT integration handle: %s" % INTC)  # Python Lumerical INTERCONNECT integration handle
  else: # found open INTC session
    try:
      lumapi.evalScript(INTC, "?'Python integration test.';")
    except: # but can't communicate with INTC; perhaps it was closed by the user
      INTC = lumapi.open('interconnect') # run again.
      if verbose:
        print("Re-Started new session. INTERCONNECT integration handle: %s" % INTC)  # Python Lumerical INTERCONNECT integration handle
  try: # check again
    lumapi.evalScript(INTC, "?'Python integration test.';")
  except:
    raise Exception ("Can't run Lumerical INTERCONNECT via Python integration.")


def circuit_simulation(circuit_name, folder, num_detectors, matlab_data_files=[], simulate=True, verbose=False, ):
  if verbose:
    print('*** circuit_simulation()')
  
  import os
  filename_main = os.path.join(folder, '%s_main.spi' % circuit_name)
  print(filename_main)
  filename_subckt = os.path.join(folder,  '%s.spi' % circuit_name)
  if not os.path.exists(filename_main) or not os.path.exists(filename_subckt):
      print(" netlist files not found")
      return

  # Output files
  filename_lsf = os.path.join(folder, '%s.lsf' % circuit_name)
  filename_icp = os.path.join(folder, '%s.icp' % circuit_name)
  
  
  # Write the Lumerical INTERCONNECT start-up script.
  file = open(filename_lsf, 'w')
  text_lsf = 'switchtolayout;\n'
  text_lsf += 'deleteall;\n'
  text_lsf += "importnetlist('%s');\n" % filename_main
  text_lsf += 'addproperty("::Root Element::%s", "MC_uniformity_thickness", "wafer", "Matrix");\n' % circuit_name
  text_lsf += 'addproperty("::Root Element::%s", "MC_uniformity_width", "wafer", "Matrix");\n' % circuit_name
  text_lsf += 'addproperty("::Root Element::%s", "MC_grid", "wafer", "Number");\n' % circuit_name
  text_lsf += 'addproperty("::Root Element::%s", "MC_resolution_x", "wafer", "Number");\n' % circuit_name
  text_lsf += 'addproperty("::Root Element::%s", "MC_resolution_y", "wafer", "Number");\n' % circuit_name
  text_lsf += 'addproperty("::Root Element::%s", "MC_non_uniform", "wafer", "Number");\n'  % circuit_name
  text_lsf += 'select("::Root Element::%s");\n' % circuit_name
  text_lsf += 'set("run setup script",2);\n'
  text_lsf += "save('%s');\n" % filename_icp
  text_lsf += 'run;\n'
  for i in range(1, num_detectors+1):
    if matlab_data_files:
      # convert simulation data into simple datasets:
      wavelenth_scale = 1e9
      text_lsf += 'temp = getresult("ONA_1", "input %s/mode 1/gain");\n' % i
      text_lsf += 't%s = matrixdataset("Simulation");\n' % i
      text_lsf += 't%s.addparameter("wavelength",temp.wavelength*%s);\n' % (i, wavelenth_scale)
      text_lsf += 't%s.addattribute("Simulation, Detector %s",getresultdata("ONA_1", "input %s/mode 1/gain"));\n' % (i,i, i)
    else:
      text_lsf += 't%s = getresult("ONA_1", "input %s/mode 1/gain");\n' % (i, i)
      
  # load measurement data files
  m_count=0
  if matlab_data_files:
    for m in matlab_data_files:
      if '.mat' in m:
        m_count += 1
        # INTERCONNECT can't deal with our measurement files... load and save data.
        from scipy.io import loadmat, savemat        # used to load MATLAB data files
        # *** todo, use DFT rules to determine which measurements we should load.
        PORT=2 # Which Fibre array port is the output connected to?
        matData = loadmat(m, squeeze_me=True, struct_as_record=False)
        wavelength = matData['scandata'].wavelength
        power = matData['scandata'].power[:,PORT-1]
        savemat(m, {'wavelength': wavelength, 'power': power})
        
        # INTERCONNECT load data
        head, tail = os.path.split(m)
        tail = tail.split('.mat')[0]
        text_lsf += 'matlabload("%s");\n' % m
        text_lsf += 'm%s = matrixdataset("Measurement");\n' % m_count
        text_lsf += 'm%s.addparameter("wavelength",wavelength*%s);\n'  % (m_count, wavelenth_scale)
        text_lsf += 'm%s.addattribute("Measured: %s",power);\n'  % (m_count, tail)
  
  text_lsf += 'visualize(t1'
  for i in range(2, num_detectors+1):
    text_lsf += ', t%s' % i
  for i in range(1, m_count+1):
    text_lsf += ', m%s' % i
  text_lsf += ');\n'
  
  file.write (text_lsf)
  file.close()
  
  if verbose:
    print(text_lsf)

  if simulate:
    # Run using Python integration:
    try: 
      from . import load_lumapi
      lumapi = load_lumapi.LUMAPI
      global INTC
      # Launch INTERCONNECT:
      run_INTC()
      lumapi.evalScript(INTC, "?'Test';")
    except:
      import sys
      if 'pya' in sys.modules: # check if in KLayout
        from .. import scripts
        scripts.open_folder(tmp_folder)
        INTC_commandline(filename_main)
    try:
      lumapi.evalScript(INTC, "cd ('" + folder + "');")
      lumapi.evalScript(INTC, circuit_name + ";")
    except:
      pass
  else:
    import sys
    if 'pya' in sys.modules: # check if in KLayout
      from .. import scripts
      scripts.open_folder(tmp_folder)
    
  if verbose:
    print('Done Lumerical INTERCONNECT circuit simulation.')

  
 
  
def circuit_simulation_monte_carlo(params = None, topcell = None, verbose=True, opt_in_selection_text=[], matlab_data_files=[], simulate=True):
  print('*** circuit_simulation_monte_carlo()')
  from .. import _globals
  from ..utils import get_layout_variables
  if topcell is None:
    TECHNOLOGY, lv, ly, topcell = get_layout_variables()
  else:
    TECHNOLOGY, lv, _, _ = get_layout_variables()
    ly = topcell.layout()
  
  if params is None: params = _globals.MC_GUI.get_parameters()
  if params is None: 
    pya.MessageBox.warning("No MC parameters", "No Monte Carlo parameters. Cancelling.", pya.MessageBox.Cancel)
    return
  print(params)
  
  if int(params['num_wafers'])<1:
    pya.MessageBox.warning("Insufficient number of wafers", "The number of wafers for Monte Carlo simulations need to be 1 or more.", pya.MessageBox.Cancel)
    return
  if int(params['num_dies'])<1:
    pya.MessageBox.warning("Insufficient number of dies", "The number of die per wafer for Monte Carlo simulations need to be 1 or more.", pya.MessageBox.Cancel)
    return

  circuit_name = topcell.name.replace('.','') # remove "."
  circuit_name = ''.join(circuit_name.split('_', 1))  # remove leading _
  
  
  if verbose:
    print('*** circuit_simulation_monte_carlo()')
  
  # check for supported operating system, tested on:
  # Windows 7, 10
  # OSX Sierra, High Sierra
  # Linux
  import sys
  if not any([sys.platform.startswith(p) for p in {"win","linux","darwin"}]):
    raise Exception("Unsupported operating system: %s" % sys.platform)
    
  # Save the layout prior to running simulations, if there are changes.
  mw = pya.Application.instance().main_window()
  if mw.manager().has_undo():
    mw.cm_save()
  layout_filename = mw.current_view().active_cellview().filename()
  if len(layout_filename) == 0:
    pya.MessageBox.warning("Please save your layout before running the simulation.", "Please save your layout before running the simulation.", pya.MessageBox.Cancel)
    return
    
  # *** todo    
  #   Add the "disconnected" component to all disconnected pins
  #  optical_waveguides, optical_components = terminate_all_disconnected_pins()

  # Output the Spice netlist:
  text_Spice, text_Spice_main, num_detectors = \
    topcell.spice_netlist_export(verbose=verbose, opt_in_selection_text=opt_in_selection_text)
  if not text_Spice:
    pya.MessageBox.warning("No netlist available.", "No netlist available. Cannot run simulation.", pya.MessageBox.Cancel)
    return
  if verbose:   
    print(text_Spice)
  
  tmp_folder = _globals.TEMP_FOLDER
  import os    
  filename = os.path.join(tmp_folder, '%s_main.spi' % circuit_name)
  filename_subckt = os.path.join(tmp_folder,  '%s.spi' % circuit_name)
  filename2 = os.path.join(tmp_folder, '%s.lsf' % circuit_name)
  filename_icp = os.path.join(tmp_folder, '%s.icp' % circuit_name)
  
  text_Spice_main += '.INCLUDE "%s"\n\n' % (filename_subckt)
  
  # Write the Spice netlist to file
  file = open(filename, 'w')
  file.write (text_Spice_main)
  file.close()
  file = open(filename_subckt, 'w')
  file.write (text_Spice)
  file.close()
  
  # Write the Lumerical INTERCONNECT start-up script.
  file = open(filename2, 'w')

  text_lsf = '###DEVELOPER:Zeqin Lu, zqlu@ece.ubc.ca, University of British Columbia \n' 
  text_lsf += 'switchtolayout;\n'
  text_lsf += 'deleteall;\n'
  text_lsf += "importnetlist('%s');\n" % filename
  text_lsf += 'addproperty("::Root Element", "wafer_uniformity_thickness", "wafer", "Matrix");\n' 
  text_lsf += 'addproperty("::Root Element", "wafer_uniformity_width", "wafer", "Matrix");\n' 
  text_lsf += 'addproperty("::Root Element", "N", "wafer", "Number");\n'  
  text_lsf += 'addproperty("::Root Element", "selected_die", "wafer", "Number");\n' 
  text_lsf += 'addproperty("::Root Element", "wafer_length", "wafer", "Number");\n'   
  text_lsf += 'addproperty("::Root Element::%s", "MC_uniformity_thickness", "wafer", "Matrix");\n' % circuit_name
  text_lsf += 'addproperty("::Root Element::%s", "MC_uniformity_width", "wafer", "Matrix");\n' % circuit_name
  text_lsf += 'addproperty("::Root Element::%s", "MC_grid", "wafer", "Number");\n' % circuit_name
  text_lsf += 'addproperty("::Root Element::%s", "MC_resolution_x", "wafer", "Number");\n'  % circuit_name
  text_lsf += 'addproperty("::Root Element::%s", "MC_resolution_y", "wafer", "Number");\n' % circuit_name
  text_lsf += 'addproperty("::Root Element::%s", "MC_non_uniform", "wafer", "Number");\n'  % circuit_name
  text_lsf += 'select("::Root Element::%s");\n'  % circuit_name
  text_lsf += 'set("MC_non_uniform",99);\n'  
  text_lsf += 'n_wafer = %s;  \n'  % params['num_wafers']  #  GUI INPUT: Number of testing wafer
  text_lsf += 'n_die = %s;  \n'  % params['num_dies']  #  GUI INPUT: Number of testing die per wafer
  text_lsf += 'kk = 1;  \n'
  text_lsf += 'select("ONA_1");\n'
  text_lsf += 'num_points = get("number of points");\n'
  
  for i in range(0, num_detectors):
    text_lsf += 'mc%s = matrixdataset("mc%s"); # initialize visualizer data, mc%s \n' % (i+1, i+1, i+1)
    text_lsf += 'Gain_Data_input%s = matrix(num_points,n_wafer*n_die);  \n' % (i+1) 

  ###Define histograms datasets
  if(params['histograms']['fsr']==True):
    text_lsf += 'fsr_dataset = matrix(1,n_wafer*n_die,1);\n'
  if(params['histograms']['wavelength']==True):
    text_lsf += 'freq_dataset = matrix(1,n_wafer*n_die,1);\n'
  if(params['histograms']['gain']==True):
    text_lsf += 'gain_dataset = matrix(1,n_wafer*n_die,1);\n'
  
  text_lsf += '#Run Monte Carlo simulations; \n'
  text_lsf += 'for (jj=1; jj<=n_wafer; jj=jj+1) {   \n'
  ############################## Wafer generation ###########################################
  text_lsf += ' wafer_length = %s;  \n'  % 100e-3 # datadict["wafer_length_x"]  # [m], GUI INPUT: wafer length
  text_lsf += ' wafer_cl_width = %s;  \n' % params['waf_var']['width']['corr_len']  # [m],  GUI INPUT: wafer correlation length
  text_lsf += ' wafer_cl_thickness = %s;  \n' % params['waf_var']['height']['corr_len']  # [m],  GUI INPUT: wafer correlation length  
  text_lsf += ' wafer_clx_width = wafer_cl_width;  \n'  
  text_lsf += ' wafer_cly_width = wafer_cl_width; \n'   
  text_lsf += ' wafer_clx_thickness = wafer_cl_thickness;  \n'  
  text_lsf += ' wafer_cly_thickness = wafer_cl_thickness; \n'  
  text_lsf += ' N = 500;  \n'        
  text_lsf += ' wafer_grid=wafer_length/N; \n'   
  text_lsf += ' wafer_RMS_w = %s;     \n' % params['waf_var']['width']['std_dev'] # [nm], GUI INPUT: Within wafer Sigma RMS for width
  text_lsf += ' wafer_RMS_t = %s;   \n' % params['waf_var']['height']['std_dev']    # [nm], GUI INPUT: Within wafer Sigma RMS for thickness
  text_lsf += ' x = linspace(-wafer_length/2,wafer_length/2,N); \n'
  text_lsf += ' y = linspace(-wafer_length/2,wafer_length/2,N); \n'
  text_lsf += ' xx = meshgridx(x,y) ;  \n'
  text_lsf += ' yy = meshgridy(x,y) ;  \n'
  text_lsf += ' wafer_Z_thickness = wafer_RMS_t*randnmatrix(N,N);  \n'
  text_lsf += ' wafer_F_thickness = exp(-(xx^2/(wafer_clx_thickness^2/2)+yy^2/(wafer_cly_thickness^2/2))); \n'  # Gaussian filter
  text_lsf += ' wafer_uniformity_thickness = real( 2/sqrt(pi)*wafer_length/N/sqrt(wafer_clx_thickness)/sqrt(wafer_cly_thickness)*invfft(fft(wafer_Z_thickness,1,0)*fft(wafer_F_thickness,1,0), 1, 0)  );    \n' # wafer created using Gaussian filter   
  text_lsf += ' wafer_Z_width = wafer_RMS_w*randnmatrix(N,N);  \n'
  text_lsf += ' wafer_F_width = exp(-(xx^2/(wafer_clx_width^2/2)+yy^2/(wafer_cly_width^2/2))); \n'  # Gaussian filter
  text_lsf += ' wafer_uniformity_width = real( 2/sqrt(pi)*wafer_length/N/sqrt(wafer_clx_width)/sqrt(wafer_cly_width)*invfft(fft(wafer_Z_width,1,0)*fft(wafer_F_width,1,0), 1, 0)  );    \n' # wafer created using Gaussian filter 
  
  ######################## adjust Wafer mean ###################
  text_lsf += ' mean_RMS_w = %s;     \n' % params['waf_to_waf_var']['width']['std_dev'] # [nm], GUI INPUT:  wafer Sigma RMS for width
  text_lsf += ' mean_RMS_t = %s;   \n' % params['waf_to_waf_var']['thickness']['std_dev']    # [nm], GUI INPUT:  wafer Sigma RMS for thickness
  text_lsf += ' wafer_uniformity_thickness = wafer_uniformity_thickness + randn(0,mean_RMS_t); \n'
  text_lsf += ' wafer_uniformity_width = wafer_uniformity_width + randn(0,mean_RMS_w); \n'
  
  ##################################### pass wafer to Root ###################
  text_lsf += ' #pass wafers to object \n'
  text_lsf += ' select("::Root Element");  \n' 
  text_lsf += ' set("wafer_uniformity_thickness", wafer_uniformity_thickness);  \n'
  text_lsf += ' set("wafer_uniformity_width", wafer_uniformity_width);  \n'
  text_lsf += ' set("N",N);  \n'
  text_lsf += ' set("wafer_length",wafer_length);  \n'
  
  #################################### embed wafer selection script in Root ###################
  text_lsf += ' select("::Root Element");\n'
  text_lsf += ' set("setup script",'+ "'" +  ' \n'
  text_lsf += '  ######################## high resolution interpolation for dies ################# \n'
  text_lsf += '  MC_grid = 5e-6;  \n'   # [m], mesh grid
  text_lsf += '  die_span_x = %s; \n'  % 5e-3 # datadict["die_length_x"]  # [m]    GUI INPUT: die length X
  text_lsf += '  die_span_y = %s; \n'  % 5e-3 # datadict["die_length_y"]  # [m]    GUI INPUT: die length Y
  text_lsf += '  MC_resolution_x = die_span_x/MC_grid;  \n'
  text_lsf += '  MC_resolution_y = die_span_y/MC_grid;  \n'
  text_lsf += '  die_num_x = floor(wafer_length/die_span_x); \n'
  text_lsf += '  die_num_y = floor(wafer_length/die_span_y); \n'
  text_lsf += '  die_num_total = die_num_x*die_num_y; \n'
  text_lsf += '  x = linspace(-wafer_length/2,wafer_length/2,N); \n'
  text_lsf += '  y = linspace(-wafer_length/2,wafer_length/2,N); \n'
              # pick die for simulation, and do high resolution interpolation 
  text_lsf += '  j=selected_die; \n'
  text_lsf += '  die_min_x = -wafer_length/2+(j-1)*die_span_x -floor((j-1)/die_num_x)*wafer_length; \n'
  text_lsf += '  die_max_x = -wafer_length/2+j*die_span_x -floor((j-1)/die_num_x)*wafer_length; \n'
  text_lsf += '  die_min_y = wafer_length/2-ceil(j/die_num_y)*die_span_y; \n'
  text_lsf += '  die_max_y = wafer_length/2-(ceil(j/die_num_y)-1)*die_span_y; \n'
  text_lsf += '  x_die = linspace(die_min_x, die_max_x, MC_resolution_x); \n'
  text_lsf += '  y_die = linspace(die_min_y, die_max_y, MC_resolution_y); \n'
  text_lsf += '  die_xx = meshgridx(x_die,y_die) ;  \n'
  text_lsf += '  die_yy = meshgridy(x_die,y_die) ;  \n'
  text_lsf += '  MC_uniformity_thickness = interp(wafer_uniformity_thickness, x, y, x_die, y_die); # interpolation \n'
  text_lsf += '  MC_uniformity_width = interp(wafer_uniformity_width, x, y, x_die, y_die); # interpolation \n'
  ######################### pass die to object ####################################
  text_lsf += '  select("::Root Element::%s");  \n' % circuit_name
  text_lsf += '  set("MC_uniformity_thickness",MC_uniformity_thickness);  \n'
  text_lsf += '  set("MC_uniformity_width",MC_uniformity_width);  \n'
  text_lsf += '  set("MC_resolution_x",MC_resolution_x);  \n'
  text_lsf += '  set("MC_resolution_y",MC_resolution_y);  \n'
  text_lsf += '  set("MC_grid",MC_grid);  \n'
  text_lsf += '  set("MC_non_uniform",1);  \n'
  text_lsf += " '"+'); \n'
  
  text_lsf += ' for (ii=1;  ii<=n_die; ii=ii+1) {   \n'
  text_lsf += '  switchtodesign; \n'
  text_lsf += '  setnamed("ONA_1","peak analysis", "single");\n'
  text_lsf += '  select("::Root Element");  \n'
  text_lsf += '  set("selected_die",ii);  \n'
  text_lsf += '  run;\n'
  text_lsf += '  select("ONA_1");\n'
  text_lsf += '  T=getresult("ONA_1","input 1/mode 1/transmission");\n'
  text_lsf += '  wavelength = T.wavelength;\n'   
  
  for i in range(0, num_detectors):
    text_lsf += '  if (kk==1) { mc%s.addparameter("wavelength",wavelength);} \n' % (i+1) 
    text_lsf += '  mc%s.addattribute("run", getattribute( getresult("ONA_1", "input %s/mode 1/gain"), getattribute(getresult("ONA_1", "input %s/mode 1/gain")) ) );\n' % (i+1, i+1, i+1)
    text_lsf += '  Gain_Data_input%s(1:num_points, kk) = getattribute( getresult("ONA_1", "input %s/mode 1/gain"), getattribute(getresult("ONA_1", "input %s/mode 1/gain")) ); \n'  % (i+1, i+1, i+1)
    
  #add simulation data to their corresponding datalists  
  if(params['histograms']['fsr']==True):
      text_lsf += '  fsr_select = getresult("ONA_1", "input 1/mode 1/peak/free spectral range");\n'
      text_lsf += '  fsr_dataset(1,kk) = real(fsr_select.getattribute(getattribute(fsr_select)));\n'

  if(params['histograms']['wavelength']==True):
      text_lsf += '  freq_dataset(1,kk) = getresult("ONA_1", "input 1/mode 1/peak/frequency");\n'

  if(params['histograms']['gain']==True):
      text_lsf += '  gain_select = getresult("ONA_1", "input 1/mode 1/peak/gain");\n'
      text_lsf += '  gain_dataset(1,kk) = real(gain_select.getattribute(getattribute(gain_select)));\n'

  text_lsf += '  switchtodesign; \n'
  text_lsf += '  kk = kk + 1;  \n'
  text_lsf += ' }\n'   # end for wafer iteration
  text_lsf += '}\n'  # end for die iteration
  text_lsf += '?"Spectrum data for each input can be found in the Script Workspace tab:";\n'    
  for i in range(0, num_detectors): 
      text_lsf += '?"Gain_Data_input%s"; \n' %(i+1)
  text_lsf += '?"Plot spectrums using script: plot(wavelength, Gain_Data_input#)";\n'  
  for i in range(0, num_detectors):
    text_lsf += 'visualize(mc%s);\n' % (i+1)
  
  #### Display Histograms for the selected components
  #FSR
  if(params['histograms']['fsr']==True):
      text_lsf += 'dataset = fsr_dataset*1e9;\n'  #select fsr dataset defined above
      text_lsf += 'bin_hist = max( [ 10, (max(dataset)-min(dataset)) / std(dataset) * 10 ]);\n' #define number of bins according to the number of data
      text_lsf += 'histc(dataset, bin_hist, "Free Spectral Range (nm)", "Count", "Histogram - FSR");\n' #generate histogram 
      text_lsf += 'legend("Mean: " + num2str(mean(dataset)) + ", Std Dev: " + num2str(std(dataset)));\n' #define plot legends
      
  #wavelength
  if(params['histograms']['wavelength']==True):
      text_lsf += 'dataset = freq_dataset*1e9;\n'
      text_lsf += 'num_hist = max( [ 10, (max(dataset)-min(dataset)) / std(dataset) * 10 ]);\n'
      text_lsf += 'histc(dataset, bin_hist, "Wavelength (nm)", "Count", "Histogram - Peak wavelength");\n'
      text_lsf += 'legend("Mean: " + num2str(mean(dataset)) + ", Std Dev: " + num2str(std(dataset)));\n'

  #Gain
  if(params['histograms']['gain']==True):
      text_lsf += 'dataset = gain_dataset;\n'
      text_lsf += 'num_hist = max( [ 10, (max(dataset)-min(dataset)) / std(dataset) * 10 ]);\n'
      text_lsf += 'histc(dataset, bin_hist, "Gain (dB)", "Count", "Histogram - Peak gain");\n'
      text_lsf += 'legend("Mean: " + num2str(mean(dataset)) + ", Std Dev: " + num2str(std(dataset)));\n'





  '''

  for i in range(1, num_detectors+1):
    if matlab_data_files:
      # convert simulation data into simple datasets:
      wavelenth_scale = 1e9
      text_lsf += 'temp = getresult("ONA_1", "input %s/mode 1/gain");\n' % i
      text_lsf += 't%s = matrixdataset("Simulation");\n' % i
      text_lsf += 't%s.addparameter("wavelength",temp.wavelength*%s);\n' % (i, wavelenth_scale)
      text_lsf += 't%s.addattribute("Simulation, Detector %s",getresultdata("ONA_1", "input %s/mode 1/gain"));\n' % (i,i, i)
    else:
      text_lsf += 't%s = getresult("ONA_1", "input %s/mode 1/gain");\n' % (i, i)
      
  # load measurement data files
  m_count=0
  if matlab_data_files:
    for m in matlab_data_files:
      if '.mat' in m:
        m_count += 1
        # INTERCONNECT can't deal with our measurement files... load and save data.
        from scipy.io import loadmat, savemat        # used to load MATLAB data files
        # *** todo, use DFT rules to determine which measurements we should load.
        PORT=2 # Which Fibre array port is the output connected to?
        matData = loadmat(m, squeeze_me=True, struct_as_record=False)
        wavelength = matData['scandata'].wavelength
        power = matData['scandata'].power[:,PORT-1]
        savemat(m, {'wavelength': wavelength, 'power': power})
        
        # INTERCONNECT load data
        head, tail = os.path.split(m)
        tail = tail.split('.mat')[0]
        text_lsf += 'matlabload("%s");\n' % m
        text_lsf += 'm%s = matrixdataset("Measurement");\n' % m_count
        text_lsf += 'm%s.addparameter("wavelength",wavelength*%s);\n'  % (m_count, wavelenth_scale)
        text_lsf += 'm%s.addattribute("Measured: %s",power);\n'  % (m_count, tail)
  
  text_lsf += 'visualize(t1'
  for i in range(2, num_detectors+1):
    text_lsf += ', t%s' % i
  for i in range(1, m_count+1):
    text_lsf += ', m%s' % i
  text_lsf += ');\n'
  
  '''
  
  file.write (text_lsf)
  file.close()
  
  if verbose:
    print(text_lsf)

  if simulate:
    # Run using Python integration:
    try: 
      from .. import _globals
      run_INTC()
      # Run using Python integration:
      lumapi = _globals.LUMAPI
      lumapi.evalScript(_globals.INTC, "cd ('" + tmp_folder + "');")
      lumapi.evalScript(_globals.INTC, circuit_name + ";")
    except:
      from .. import scripts
      scripts.open_folder(tmp_folder)
      INTC_commandline(filename)
  else:
    from .. import scripts
    scripts.open_folder(tmp_folder)
    
  if verbose:
    print('Done Lumerical INTERCONNECT Monte Carlo circuit simulation.')

