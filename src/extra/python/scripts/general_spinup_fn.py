#Calculate vertical integrals of area mean, annual mean specific humidity for whole atmosphere and levels above 100hPa (strat wv)
#Could set a threshold to determine spin-up end, e.g. require changes of less than 1% seems plausible. Need more data to confirm this is appropriate however

from netCDF4 import Dataset
import numpy as np
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt
from cell_area import cell_area
import cftime
import pdb
import os

def q_spinup(run_fol, var_to_integrate, start_month, end_month, t_resolution=42, data_dir_type = 'isca', power=1.):

    #personalise
    #model directory
    model_dir = '/home/links/ct715/Isca/'
    #data directory
    if data_dir_type=='isca':
        data_dir = '/scratch/ct715/isca_data'
    # elif data_dir_type == 'isca_cpu':
    #     data_dir = '/scratch/ct715/data_from_isca_cpu/'
    # else:
    #     data_dir = '/scratch/ct715/Data_2013/'    
    
    #file name
    file_name='atmos_daily.nc'
    #time-resolution of plotting
    group='days'
    scaling=1.
    gravity=9.8

    if t_resolution == 42:
        nlon=128
        nlat=64
    elif t_resolution == 85:
        nlon=256
        nlat=128

    years=int(np.ceil((end_month-start_month)/12.))

    #get cell areas and pressure thicknesses
    possible_format_strs = [[data_dir+'/'+run_fol+'/run%03d/' % m for m in range(start_month, end_month+1)],
                            [data_dir+'/'+run_fol+'/run%04d/' % m for m in range(start_month, end_month+1)],
                            [data_dir+'/'+run_fol+'/run%d/' % m for m in range(start_month, end_month+1)]]

    for format_str_files in possible_format_strs:
        files_temp = format_str_files
        names = [s + file_name for s in files_temp]
        thd_files_exist=[os.path.isfile(s) for s in names]
        
        if thd_files_exist[0]:
            break
        
        if not thd_files_exist[0] and format_str_files==possible_format_strs[-2]:
            raise EOFError('EXITING BECAUSE NO APPROPRIATE FORMAT STR', [names[elem] for elem in [0] if not thd_files_exist[elem]])
    
    print(names[0])
    
    if not(all(thd_files_exist)):
        raise EOFError('EXITING BECAUSE OF MISSING FILES', [names[elem] for elem in range(len(thd_files_exist)) if not thd_files_exist[elem]])
    
    rundata = xr.open_dataset(names[0],
                 decode_times=False)  # no calendar so tell netcdf lib


    area = cell_area(t_resolution, model_dir)
    area_xr = xr.DataArray(area, [('lat', rundata.lat.values ), ('lon', rundata.lon.values )])
    dp = xr.DataArray( np.diff(rundata.phalf.values), [('pfull',rundata.pfull.values) ])

    #read data into xarray 
    print('opening dataset')
    rundata = xr.open_mfdataset( names,
                decode_times=False,  # no calendar so tell netcdf lib
            # choose how data will be broken down into manageable chunks.
            chunks={'time': 30, 'lon': nlon//4, 'lat': nlat//2})

    time_arr = rundata.time
    
    # Make array of days since 0000-00-00 0:0:0
    days_since_0 = xr.DataArray(
                        np.full(rundata.time.size, 719640.5),
                        dims='time'
                        )

    rundata.coords['days'] = time_arr - days_since_0
    rundata.coords['months'] = ((time_arr-days_since_0) // 30) + 1
    rundata.coords['years'] = ((time_arr // 360) +1)*scaling

    q_yr = (rundata[var_to_integrate]**power).groupby(group).mean(('time'))

    #take area mean of q
    q_av = q_yr*area_xr
    q_avs = q_av.sum(('lat','lon'))/area_xr.sum(('lat','lon'))

    try:
        q_avs.pfull
    except AttributeError:
        print('data is 2d')
        q_vint=q_avs
        q_vint.load()
        q_strat=q_vint
    else:
        #integrate over pressure levels above 100hPa and over whole atmosphere
    #    q_strat = (q_avs[:,0:24]*dp[0:24]*100).sum(('pfull'))/gravity
        min_id=np.min(np.where(q_avs.pfull.to_index() < 100.))
        max_id=np.max(np.where(q_avs.pfull.to_index() < 100.))+1

        q_strat = (q_avs[:,min_id:max_id]*dp[min_id:max_id]*100).sum(('pfull'))/gravity
        q_vint = (q_avs*dp).sum(('pfull'))/gravity

        q_strat.load()
        q_vint.load()

    time_arr=q_vint.days.values
    
    rundata.close()

    return q_strat, q_vint, time_arr



if __name__ == "__main__":

    start_month_offset=[0, 0]
    
    exp_list = ['P-K_delh60_1y_T42', 'P-K_delh60_1y_T85']

    label_arr = ['pk_T42_1y', 'pk_T85_1y']

    res_arr = [42, 85]

    data_type_arr = ['isca', 'isca']

    exp_name=exp_list

    #number of years to read
    start_month_arr=[1, 1]
    end_month_arr=[12, 12]

    len_list=[len(start_month_offset), len(exp_list), len(label_arr), len(start_month_arr), len(end_month_arr), \
                    len(res_arr), len(data_type_arr)]

    if not all(x==len_list[0] for x in len_list):
        raise IndexError("Input arrays to routine are not all the same length")


    variable_to_integrate='temp'
    power_to_scale_variable_by=1.

    plt.figure()

    for exp_number in exp_list:
        #set run name
        run_fol = str(exp_number)
        # plt_dir = '/scratch/ct715/spinup_test/'+run_fol
        # if not os.path.exists(plt_dir):
        #     os.makedirs(plt_dir)
        idx=exp_list.index(exp_number)
        print('running '+ exp_number)
        #return integral of area mean q over stratosphere and whole atmosphere
        q_strat, q_vint, time = q_spinup(run_fol, variable_to_integrate, start_month_arr[idx]+start_month_offset[idx], end_month_arr[idx]+start_month_offset[idx], res_arr[idx], data_type_arr[idx], power_to_scale_variable_by )
        plt.plot(time,q_vint,label=label_arr[idx])
#         plt.plot(time,q_strat,label='strat '+label_arr[idx])
        

plt.xlabel('time (days)')
plt.ylabel('Global average '+variable_to_integrate+'**'+str(power_to_scale_variable_by))
plt.legend(loc='upper left')
plt.savefig('/scratch/ct715/spinup_test/polvani-kushner_spinup.pdf')
# plt.show()