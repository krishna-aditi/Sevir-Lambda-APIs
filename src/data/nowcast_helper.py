#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar  7 10:59:57 2022
@author: krish
"""
import tensorflow as tf
import numpy as np
import os
import h5py
import dateutil.parser
import matplotlib as mpl
import pandas as pd
import gcsfs
from geopy import distance
import datetime
import imageio
import tempfile
#mpl.use("TkAgg")
import matplotlib.pyplot as plt
import io
plt.rcParams["figure.figsize"] = (10,10)
import pathlib
abspath = pathlib.Path(__file__).parent.resolve()
##############################################################################
# Filtering Catalog 

def filterCatalog(lat, lon, radius, time_utc, catalog_path, closest_radius):
    # Read CATALOG from cloud
    catalog = readDataFromCloud(file_path= catalog_path, file_type='catalog')
    time = dateutil.parser.parse(time_utc)
    catalog = catalog[catalog.img_type=='vil']
    
    # datetime filter
    catalog = catalog.loc[(catalog.time_utc.dt.day == time.day)&(catalog.time_utc.dt.month == time.month)&(catalog.time_utc.dt.year == time.year)&(catalog.time_utc.dt.hour <= time.hour)&(catalog.time_utc.dt.hour >= time.hour - 1)]
    
    # pct_missing filter
    catalog = catalog[catalog.pct_missing==0]
    if len(catalog)==0:
        raise Exception('Catalog Error: Requested time not present in the given location')
    
    # aoi filter
    catalog['cntrlat'] = catalog.apply(lambda row: (row.llcrnrlat + row.urcrnrlat)/2, axis=1)
    catalog['cntrlon'] = catalog.apply(lambda row: (row.llcrnrlon + row.urcrnrlon)/2, axis=1)
    
    # Calculate distance using Geopy
    catalog['distance'] = catalog.apply(lambda row: distance.distance((row.cntrlat,row.cntrlon), (lat,lon)).miles, axis=1)
    # Sort values to get shortest distance
    catalog = catalog.sort_values(by=['distance'])
    
    if closest_radius==True:
        close_dist = catalog.iloc[0].distance
        catalog = catalog[catalog.distance<=close_dist]
    else:
        catalog = catalog[catalog.distance<radius]
        if len(catalog)==0:
            raise Exception('Catalog Error: Requested location not present in the given radius. Try increasing the radius or set closest_radius=True in the query')
       
    catalog = catalog.iloc[0]
    return str(catalog.file_name), int(catalog.file_index), str(catalog.time_utc)

##############################################################################
# Google Cloud Storage Functions
#data_path = 'sevir-vil/'
#filename = 'vil/2019/SEVIR_VIL_STORMEVENTS_2019_0101_0630.h5'
#filename = 'CATALOG.csv'
#filename = 'models/nowcast/gan_generator.h5'
    
def flushCache(folder, file):
    try:
        project_name = 'Assignment-4'
        credentials = os.path.join(abspath,"cred.json")
        FS = gcsfs.GCSFileSystem(project=project_name, token=credentials)
        
        files = FS.ls(folder)
        
        flushFile = [f for f in files if file in f]
        
        for f in flushFile:
            FS.rm_file(f)
        return 1
    except Exception:
        raise Exception('Cache Error: Could not flush Cache')
    
def readDataFromCloud(file_path, file_type, fileindex=0):
    project_name = 'Assignment-4'
    credentials = os.path.join(abspath,"cred.json")
    FS = gcsfs.GCSFileSystem(project=project_name, token=credentials)
    try:
        with FS.open(file_path, 'rb') as data_file:
            if file_type=='catalog':
                catalog = pd.read_csv(data_file,parse_dates=['time_utc'],low_memory=False)
                return catalog
            elif file_type=='model':
                model_file = h5py.File(data_file,'r')
                return tf.keras.models.load_model(model_file, compile=False, custom_objects = {"tf": tf})
            elif file_type=='input':
                json_ = eval(data_file.read())
                return json_
            elif file_type=='data':
                f = h5py.File(data_file,'r')
                try:
                    data = f['vil'][fileindex]
                    x1,x2,x3 = data[:,:,:13], data[:,:,13:26], data[:,:,26:39]
                except Exception:
                    raise Exception(f'Data Error: {file_path} File Corrupt. Check fileindex {fileindex}')
                return np.stack((x1,x2,x3))
            else:
                return data_file.read()
    except Exception:
        raise Exception(f'Data Error: Could not find the file {file_path}')

def writeDataToCloud(data, file_path, file_type,time_utc=''):
    project_name = 'Assignment-4'
    credentials = os.path.join(abspath,"cred.json")
    FS = gcsfs.GCSFileSystem(project=project_name, token=credentials)
    file_path = file_path.replace('\\','/')
    try:
        if file_type=='data': 
            try:
                # For storing output as H5 file
                temp = tempfile.NamedTemporaryFile(delete=False,mode='w',suffix='.h5') 
                hf = h5py.File(temp.name, 'w')
                hf.create_dataset('nowcast_predict', data = data)
                hf.close()
                FS.upload(temp.name, file_path)
                temp.close()
                os.unlink(temp.name)
            except:
                raise Exception('IO Error: Could not write H5 file. Check the out_path correctly or try reinstalling h5py')
        elif file_type=='gif':
            try:
                # For storing output as GIF
                # Store predicted images in a temp file, use delete = False because we need to store these images to make a GIF
                # If delete = True then all temp data gets deleted as soon as you temp.close()
                temp = tempfile.NamedTemporaryFile(delete=False, mode='w',suffix='.gif')
                count = 0
                # From visualize_result function in AnalyzeNowcast notebook
                cmap_dict = lambda s: {'cmap':get_cmap(s,encoded=True)[0],
                                        'norm':get_cmap(s,encoded=True)[1],
                                        'vmin':get_cmap(s,encoded=True)[2],
                                        'vmax':get_cmap(s,encoded=True)[3]}
                images = []
                for pred in data:
                    for i in range(pred.shape[-1]):
                        buf = io.BytesIO()
                        plt.imshow(pred[:,:,i],**cmap_dict('vil'))
                        plt.axis('off')
                        plt.title(f'Nowcast prediction at time {time_utc}+{(count+1)*5}minutes')
                        plt.savefig(buf, bbox_inches='tight')
                        buf.seek(0)
                        images.append(imageio.imread(buf))
                        plt.close()
                        buf.close()
                        count+=1
                # Store coloured images into temp.name
                imageio.mimsave(temp.name, images)
                # Upload using GCSFileSystem object
                FS.upload(temp.name, file_path)
                temp.close()
                # Delete file path of temp file
                os.unlink(temp.name)
                # Saving files as GIF (https://stackoverflow.com/questions/41228209/making-gif-from-images-using-imageio-in-python)
            except Exception as e:
                raise Exception(f'IO Error: Could not write GIF. Try reinstalling matplotlib (version<=3.2.0) and imageio {e}')
        else:
            pass
        # Return cloud path of saved GIF file
        return FS.url(file_path).replace('googleapis','cloud.google')
    except Exception as e:
        raise Exception(f'Output Error: Error writing data to Google Cloud Bucket {e}')

############################################################################## 
# Defining our own data generator with the help of make_nowcast_dataset 
# Functions to filter the catalog and reading data in desired format

def get_nowcast_data(lat, lon, radius, time_utc, catalog_path, data_path, closest_radius, threshold_time_minutes, force_refresh):
    # "exists" == True ==> if output GIF already present in output location
    exists = False
    # Access GCP bucket
    project_name = 'Assignment-4'
    credentials = os.path.join(abspath,"cred.json")
    FS = gcsfs.GCSFileSystem(project=project_name, token=credentials)
    # Threshold to check if GIFs are older than x minutes
    threshold = threshold_time_minutes*60
    try:    
        filename, fileindex, filetime = filterCatalog(lat, lon, radius, time_utc, catalog_path, closest_radius)
        if not force_refresh:
            try:
                # Ignoring 1st element of list, which is the sevir-vil/output bucket itself    
                outfiles = FS.ls('sevir-vil/cache')[1:]
                # Outfiles contains of list of files in output folder for the same location and date as requested by user
                # If existing output GIF has same naming convention as the one expected for the given filename, then add to list
                outfiles = [file for file in outfiles if 'Predicted'+filename.split('/')[-1].split('.')[0].replace('_','')+str(fileindex) == file.split('/')[-1].split('_')[0] and file.endswith('.gif')]
                for file in outfiles:
                    # Date in exsisting output files (stored in their name after '_')
                    
                    # Time_utc on input h5 file initially
                    # Output generation datetime
                    gendate = dateutil.parser.parse(file.split('_')[2][:-4])
                    # Check if file is older than acceptable threshold
                    if (datetime.datetime.now() - gendate).seconds < threshold:
                        # Match found!
                        print('With in threshold')
                        exists = True
                        break
            except Exception:
                # If matching file not found, need to generate new output, use force_refresh!
                raise Exception('Output Catalog Error: Try using force_refresh="True"')
            if exists == True:
                # Return matching file link is there is a hit
                print('Returning File')
                return exists, [], FS.url(file).replace('googleapis','cloud.google')
            
        path = os.path.join(data_path,filename) # comes as 'sevir-vil\\SEVIR_VIL_STORMEVENTS_2019_0101_0630.h5'
        data = readDataFromCloud(file_path=path.replace('\\','/'),fileindex=fileindex, file_type='data') # returns filename as 'sevir-vil/SEVIR_VIL_STORMEVENTS_2019_0101_0630.h5'

    except Exception as e:
        raise Exception(e)
    
    return exists, data, filename.split('/')[-1].split('.')[0].replace('_','')+f'{fileindex}_'+filetime

##############################################################################
# Initializing and running the model
# Link to download pre-trained model (https://www.dropbox.com/s/9y3m4axfc3ox9i7/gan_generator.h5?dl=0Downloading%20mse_and_style.h5)

def run_model(data, model_path, scale, model_type):
    MEAN=33.44
    SCALE=47.54
    data = (data.astype(np.float32)-MEAN)/SCALE
    norm = {'scale':47.54, 'shift':33.44}
    file = None
    # Model type
    try:
        if model_type == 'gan':
            file = os.path.join(model_path, 'gan_generator.h5')
            model = readDataFromCloud(file_path=file.replace('\\','/'), file_type='model')
        elif model_type == 'mse':    
            file  = os.path.join(model_path, 'mse_model.h5')
            model = readDataFromCloud(file_path=file.replace('\\','/'), file_type='model')
        elif model_type == 'style':    
            file = os.path.join(model_path, 'style_model.h5')
            model = readDataFromCloud(file_path=file.replace('\\','/'), file_type='model')
        elif model_type in ['mse+style', 'style+mse']:    
            file = os.path.join(model_path, 'mse_and_style.h5')
            model = readDataFromCloud(file_path=file.replace('\\','/'), file_type='model')
        else:
            raise Exception('Model Error: Did not find the specified model for nowcast!')
    except:
        raise Exception(f"Model Error: Model file {file} does not exist")
        
    # Output
    try:
        output = model.predict(data)
        if scale:
            output = output*norm['scale'] + norm['shift']
    except:
        raise Exception('Model Error: Run Error in Model. Try re-downloading the model file')
    return output

##############################################################################
# Display VIL images through matplotlib

# get_cmap function from src.display.display
# vil_cmap function from src.display.display

def get_cmap(type, encoded=True):
   
    if type.lower() == 'vil':
        cmap, norm = vil_cmap(encoded)
        vmin, vmax = None, None
    else:
        cmap, norm = 'jet', None
        vmin, vmax = (-7000, 2000) if encoded else (-70, 20)

    return cmap, norm, vmin, vmax


def vil_cmap(encoded = True):
    cols=[   [0,0,0],
              [0.30196078431372547, 0.30196078431372547, 0.30196078431372547],
              [0.1568627450980392,  0.7450980392156863,  0.1568627450980392],
              [0.09803921568627451, 0.5882352941176471,  0.09803921568627451],
              [0.0392156862745098,  0.4117647058823529,  0.0392156862745098],
              [0.0392156862745098,  0.29411764705882354, 0.0392156862745098],
              [0.9607843137254902,  0.9607843137254902,  0.0],
              [0.9294117647058824,  0.6745098039215687,  0.0],
              [0.9411764705882353,  0.43137254901960786, 0.0],
              [0.6274509803921569,  0.0, 0.0],
              [0.9058823529411765,  0.0, 1.0]]
    lev = [0.0, 16.0, 31.0, 59.0, 74.0, 100.0, 133.0, 160.0, 181.0, 219.0, 255.0]
    #TODO:  encoded=False
    nil = cols.pop(0)
    under = cols[0]
    over = cols.pop()
    cmap = mpl.colors.ListedColormap(cols)
    cmap.set_bad(nil)
    cmap.set_under(under)
    cmap.set_over(over)
    norm = mpl.colors.BoundaryNorm(lev, cmap.N)
    return cmap, norm
       
