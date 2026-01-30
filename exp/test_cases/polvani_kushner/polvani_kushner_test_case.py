import numpy as np
import os
from isca import DryCodeBase, DiagTable, Experiment, Namelist, GFDL_BASE

NCORES = 16 # 16 cores is default
RESOLUTION = 'T42', 60  # T42 horizontal resolution, 40 levels in pressure is default

# a CodeBase can be a directory on the computer,
# useful for iterative development
cb = DryCodeBase.from_directory(GFDL_BASE)

# or it can point to a specific git repo and commit id.
# This method should ensure future, independent, reproducibility of results.
# cb = DryCodeBase.from_repo(repo='https://github.com/isca/isca', commit='isca1.1')

# compilation depends on computer specific settings.  The $GFDL_ENV
# environment variable is used to determine which `$GFDL_BASE/src/extra/env` file
# is used to load the correct compilers.  The env file is always loaded from
# $GFDL_BASE and not the checked out git repo.

cb.compile()  # compile the source code to working directory $GFDL_WORK/codebase

# create an Experiment object to handle the configuration of model parameters
# and output diagnostics

# if using local heating from file:
inputpath1 = 'input/asymmetry/' # INCLUDE THIS FOR HEATING or 'input/polar_heating/'
inputfile1 = 'q6m2y45l800u200' # INCLUDE THIS FOR HEATING
#inputpath2 = 'input/asymmetry/'  # INCLUDE THIS FOR TOPOGRAPHY
#inputfile2 = 'h4000m2l25u65' # INCLUDE THIS FOR TOPOGRAPHY

exp_name = 'PK_e0v4z13_'+inputfile1+'_L60' # experiment name
exp = Experiment(exp_name, codebase=cb)

exp.inputfiles = [os.path.join(GFDL_BASE,inputpath1+inputfile1+'.nc')] #,\ # INCLUDE THIS FOR HEATING
                    #os.path.join(GFDL_BASE,inputpath2+inputfile2+'.nc')] # INCLUDE THIS FOR TOPOGRAPHY/EXTRA HEATING

#Tell model how to write diagnostics
diag = DiagTable()
#diag.add_file('atmos_monthly', 30, 'days', time_units='days') 
diag.add_file('atmos_daily', 1, 'days', time_units='days') # added output of daily file
# diag.add_file('atmos_6_hourly', 6, 'hours', time_units='hours')
### See: docs/source/modules/diag_manager_mod.rst

#Tell model which diagnostics to write
diag.add_field('dynamics', 'ps', time_avg=True)
diag.add_field('dynamics', 'sphum', time_avg=True) # added diagnostic field for plevel_interp
diag.add_field('dynamics', 'zsurf') # added diagnostic field for plevel_interp - zsurf is static so can't get time average
diag.add_field('dynamics', 'bk') # required diagnostic field for plevel_interp
diag.add_field('dynamics', 'pk') # required diagnostic field for plevel_interp
diag.add_field('dynamics', 'ucomp', time_avg=True)
diag.add_field('dynamics', 'vcomp', time_avg=True)
diag.add_field('dynamics', 'omega', time_avg=True) # required diagnostic field vertical velocity for EP Flux
diag.add_field('dynamics', 'temp', time_avg=True)
diag.add_field('hs_forcing', 'teq', time_avg=True) # diagnostic field to double check Teq
diag.add_field('hs_forcing', 'local_heating', time_avg=True) # INCLUDE THIS FOR HEATING
diag.add_field('dynamics', 'height', time_avg=True) # diagnostic field geopotential height

exp.diag_table = diag

# define namelist values as python dictionary
# wrapped as a namelist object.
namelist = Namelist({
    'main_nml': {
        'dt_atmos': 240, # timestep in seconds - default: 600. Should divide into seconds per day.
        'days': 30, 
        'calendar': 'thirty_day',
        'current_date': [2000,1,1,0,0,0]
    },

    'atmosphere_nml': {
        'idealized_moist_model': False  # False for Newtonian Cooling.  True for Isca/Frierson
    },

    'spectral_dynamics_nml': {
        'damping_order'           : 4,                      # default: 2
        #'water_correction_limit'  : 200.e2,                 # default: 0
        'do_water_correction': False,                       
        'reference_sea_level_press': 1.0e5,                  # default: 101325
        'valid_range_t'           : [50., 800.],           # default: (100, 500) - NOTE: lower bound changed to 50
        'initial_sphum'           : 0.0,                  # default: 0
        'vert_coord_option'       : 'uneven_sigma',         # default: 'even_sigma'
        'scale_heights': 11.0,                               # NOTE: was changed to be 11.0, from 6.0
        'exponent': 3.0,                                    # NOTE: was changed to be 3.0, from 7.5
        'surf_res': 0.5
    },

    #'spectral_init_cond_nml': { # namelist required for topography added - INCLUDE THIS FOR TOPOGRAPHY
    #   'topog_file_name': inputfile2+'.nc', #input file name
    #    'topography_option': 'input' # take topography from input file
    #},

    # configure the relaxation profile
    'hs_forcing_nml': {
        't_zero': 315.,    # temperature at reference pressure at equator (default 315K)
        't_strat': 216.65,   # stratosphere temperature (default 200K) - NOTE: was changed to 216.65 consistent with US standard T at 20km
        'delh': 60.,       # equator-pole temp gradient (default 60K)
        'delv': 10.,       # lapse rate (default 10K)
        'sigma_b': 0.7,    # boundary layer friction height (default p/ps = sigma = 0.7)

        # negative sign is a flag indicating that the units are days
        'ka':   -40.,      # Constant Newtonian cooling timescale (default 40 days)
        'ks':    -4.,      # Boundary layer dependent cooling timescale (default 4 days)
        'kf':   -1.,       # BL momentum frictional timescale (default 1 days)

        # to control jet latitude, following Garfinkel et al. (2013)
        'A': 0., # takes values 0, ±5, ±10
        'B': 0., # takes values 0 to 20 in multiples of 4
        'P_opt': 'Option1', # Option 1 or 2 depending on jet location requirement

        # to have a stratosphere, following Polvani & Kushner (2002)
        'equilibrium_t_option': 'Polvani_Kushner',
        'strat_vtx': True, # default True - set to False to set w_vtx=0 for no polar vortex
        'eps': 0.,         # stratospheric latitudinal variation (default 0K) - NOTE: ±10 in PK paper
        'vtx_gamma': 4.0, # lapse rate of winter stratospheric cooling (default 4 K/km)
        'z_ozone': 13.,     # height of stratospheric heating source
        'do_conserve_energy':   True,  # convert dissipated momentum into heat (default True)
        'sponge_flag': True,      # sponge layer for simple damping in upper levels

        # variables for including heating
        'local_heating_option': 'from_file', # INCLUDE THIS FOR HEATING
        'local_heating_file': inputfile1 # INCLUDE THIS FOR HEATING
    },

    'diag_manager_nml': {
        'mix_snapshot_average_fields': False
    },

    'fms_nml': {
        'domains_stack_size': 600000                        # default: 0
    },

    'fms_io_nml': {
        'threading_write': 'single',                         # default: multi
        'fileset_write': 'single',                           # default: multi
    }
})

exp.namelist = namelist
exp.set_resolution(*RESOLUTION)

#Let's do a run!
if __name__ == '__main__':
    exp.run(1, num_cores=NCORES, use_restart=False)
    for i in range(2, 625): #624 + 1 months for 50y worth - NOTE: discard first 2y as spin-up
        exp.run(i, num_cores=NCORES)  # use the restart i-1 by default
