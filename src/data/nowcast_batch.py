# -*- coding: utf-8 -*-
"""
Created on Tue Mar 29 10:09:10 2022

@author: Rohit Gandikota
"""

############## Using server (PREFER IF RUNNING WITHIN SERVER)
import requests
import pathlib
abspath = pathlib.Path(__file__).parent.resolve()

def batchrunWeb():
        
    authjson = { "username": "admin", "password": "admin123"}
    token = requests.post("http://127.0.0.1:8000/token", data = authjson)
    
    input_file = 'batchInputs.txt'
    try:
        with open(input_file,'rb') as f:
            json_list = f.read()
        
        json_list = eval(json_list)
    except Exception:
        raise Exception('Input Error: The input file {input_file} is corrupt or not in proper format')
    
    if token.status_code == 200:
        jwttoken = token.json()['access_token']
        headers = {"Authorization": f"Bearer {jwttoken}"}
        
        nowcast_test = requests.post("http://127.0.0.1:8000/nowcast/batch", headers=headers, data = json_list)
        sevir_output = nowcast_test.json()
        if 'nowcast_error' in sevir_output.keys():
            raise Exception({'nowcast_error': sevir_output['nowcast_error']})
        if 'gif_path' in sevir_output.keys():
            return 1
        else:
            raise Exception('Nowcast batch error !!')
        
    
    else:
        raise Exception(f"Login Failure. {token.json()['detail']}")
        
        
############## Using api (PREFER IF RUNNING INDEPENDENTLY)    
import os
from nowcast_helper import get_nowcast_data, run_model, writeDataToCloud, readDataFromCloud, flushCache
import dateutil.parser
import datetime
import numpy as np
# Use the following for testing nowcast(lat=37.318363, lon=-84.224203, radius=100, time_utc='2019-06-02 18:33:00', model_type='gan',closest_radius=True)
def nowcastBatch(list_params):
    filename_final = []
    data_final = []
    data_index = []
    display_path_final = []
    for param in list_params:
        Error = None
        # Parse time
        try:
            user_time = dateutil.parser.parse(param['time_utc'])
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
            exists, data, filename = get_nowcast_data(lat = param['lat'], lon = param['lon'], radius = param['radius'], time_utc = param['time_utc'], catalog_path = 'sevir-vil/CATALOG.csv', data_path = 'sevir-vil', closest_radius = param['closest_radius'], threshold_time_minutes = param['threshold_time_minutes'], force_refresh = True)
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
    output = run_model(data_final, 'sevir-vil/models/nowcast/', scale = True, model_type = param['model_type'])
    prev_index = 0
    for index,filename in zip(data_index,filename_final):
        # Timestamp when API is called and GIF is built
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        flushCache(folder = 'sevir-vil/cache', file = f'Predicted{filename}')
        # Output GIF
        display_path = writeDataToCloud(data = output[prev_index:prev_index+index], file_path = os.path.join('sevir-vil/cache',f'Predicted{filename}_{timestamp}.gif'), file_type='gif',time_utc=param['time_utc'])
        prev_index+=index
        display_path_final.append(display_path)
        
    
    # Return path for output
    return {'display':display_path_final}

def batchrunAPI():
    try:
        json_list = readDataFromCloud('sevir-vil/batchInputs.txt', file_type='input', fileindex=0)
    except Exception as e:
        raise Exception(f'Error in Input File: {e}')
    print('Running Nowcast Batch')
    output = nowcastBatch(json_list)        
    print('Run Successful')
    if 'Error' in output.keys():
        raise Exception(f'Error in Batch Generation {output["Error"]}')
    else:
         return output

#print(batchrunAPI())
