#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar  7 10:59:57 2022

@author: krish
"""

import os
from nowcast_helper import get_nowcast_data, run_model, writeDataToCloud, flushCache
import dateutil.parser
import datetime
import numpy as np
# Use the following for testing nowcast(lat=37.318363, lon=-84.224203, radius=100, time_utc='2019-06-02 18:33:00', model_type='gan',closest_radius=True)
def nowcast(lat, lon, radius, time_utc, model_type, closest_radius=False, threshold_time_minutes= 60, force_refresh=False):
    Error = None
    # Parse time
    try:
        user_time = dateutil.parser.parse(time_utc)
    except Exception:
        Error = 'Invalid date time format. Please provide a valid format (refer to https://dateutil.readthedocs.io/en/stable/parser.html)'
        return {'Error': Error}
    # Data cannot be older than 2019 June 1st (As per paper)
    if user_time.month < 6:
        if user_time.year < 2019:
           Error = 'Request date is too old! Try dates after 2019, June 1st'
           return {'Error': Error}
    
    
    try:
        # Filter to get data
        exists, data, filename = get_nowcast_data(lat = lat, lon = lon, radius = radius, time_utc = time_utc, catalog_path = 'sevir-vil/CATALOG.csv', data_path = 'sevir-vil', closest_radius = closest_radius, threshold_time_minutes = threshold_time_minutes, force_refresh = force_refresh)
        if exists:
            return {'display':filename}
        # Run model
        output = run_model(data, 'sevir-vil/models/nowcast/', scale = True, model_type = model_type)
        # Timestamp when API is called and GIF is built
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # Output GIF
        display_path = writeDataToCloud(data = output, file_path = os.path.join('sevir-vil/output',f'Predicted{filename}_{timestamp}.gif'), file_type='gif',time_utc=time_utc)

    except Exception as e:
        return {'Error': str(e)}
    
    # Return path for output
    return {'display':display_path}


# Use the following for testing nowcast(lat=37.318363, lon=-84.224203, radius=100, time_utc='2019-06-02 18:33:00', model_type='gan',closest_radius=True)
def nowcastBatch(params_list):
    filename_final = []
    data_final = []
    data_index = []
    display_path_final = []
    for param in params_list:
        Error = None
        # Parse time
        try:
            print(param.time_utc)
            user_time = dateutil.parser.parse(param.time_utc)
        except Exception:
            Error = 'Invalid date time format. Please provide a valid format (refer to https://dateutil.readthedocs.io/en/stable/parser.html)'
            return {'Error': Error}
        # Data cannot be older than 2019 June 1st (As per paper)
        if user_time.month < 6:
            if user_time.year < 2019:
               Error = 'Request date is too old! Try dates after 2019, June 1st'
               return {'Error': Error}
    
    
        try:
            # Filter to get data
            exists, data, filename = get_nowcast_data(lat = param.lat, lon = param.lon, radius = param.radius, time_utc = param.time_utc, catalog_path = 'sevir-vil/CATALOG.csv', data_path = 'sevir-vil', closest_radius = param.closest_radius, threshold_time_minutes = param.threshold_time_minutes, force_refresh = True)
            if exists:
                return {'Error': 'Fatal schedule error, checking in existing directory for fresh batch'}
            if data_final == []:
                data_final = data
            else:
               data_final = np.vstack((data_final,data))
            data_index.append(data.shape[0])
            filename_final.append(filename)
        except Exception as e:
            return {'Error': str(e)}
            # Run model
    output = run_model(data_final, 'sevir-vil/models/nowcast/', scale = True, model_type = param.model_type)
    prev_index = 0
    for index,filename in zip(data_index,filename_final):
        # Timestamp when API is called and GIF is built
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # Flush already existing file in Cache
        flushCache(folder = 'sevir-vil/cache', file = f'Predicted{filename}')
        # Output GIF
        display_path = writeDataToCloud(data = output[prev_index:prev_index+index], file_path = os.path.join('sevir-vil/cache',f'Predicted{filename}_{timestamp}.gif'), file_type='gif',time_utc=param.time_utc)
        prev_index+=index
        display_path_final.append(display_path)
        
    
    # Return path for output
    return {'display':display_path_final}