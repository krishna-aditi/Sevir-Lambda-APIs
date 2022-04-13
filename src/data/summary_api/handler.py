# -*- coding: utf-8 -*-
"""
Created on Thu Apr  7 13:09:06 2022

@author: krish
"""

import dateutil.parser
import pandas as pd
from geopy import distance
from transformers import T5ForConditionalGeneration, T5Tokenizer
# import gcsfs
import json

# import os
# import pathlib
# abspath = pathlib.Path(__file__).parent.resolve()

def serverless_pipeline():
    # initialize the model architecture and weights
    model = T5ForConditionalGeneration.from_pretrained("./model")
    
    # initialize the model tokenizer
    tokenizer = T5Tokenizer.from_pretrained("./model")
    
    def summary(lat, lon, radius, time_utc, closest_radius):
        episode_text, event_text =  filterEvents(lat, lon, radius, time_utc, closest_radius)
        print(f'episode_text: {episode_text}')
        # encode the text into tensor of integers using the appropriate tokenizer
        episode_inputs = tokenizer.encode("summarize: " + episode_text, return_tensors="pt", max_length=150, truncation=True)
        events_inputs = tokenizer.encode("summarize: " + event_text, return_tensors="pt", max_length=150, truncation=True)
    
        # generate the summarization episode output
        episode_outputs = model.generate(
            episode_inputs, 
            max_length=150, 
            min_length=40, 
            length_penalty=2.0, 
            num_beams=4, 
            early_stopping=True)
        # just for debugging
        episode_summary = tokenizer.decode(episode_outputs[0])
        print(f"Episode Summary: {episode_summary}")
        
        # generate the summarization event output
        
        event_outputs = model.generate(
            events_inputs, 
            max_length=150, 
            min_length=4, 
            length_penalty=2.0, 
            num_beams=4, 
            early_stopping=True)
        event_summary = tokenizer.decode(event_outputs[0])
        print(f"Event Summary: {event_summary}")
        
        return episode_summary, event_summary
    return summary
    
def filterEvents(lat, lon, radius, time_utc, closest_radius):
    # read catalog from cloud
    # credentials
    # project_name = 'Assignment-4'
    # #credentials = os.path.join(abspath,"cred.json")
    # credentials = 'cred.json'
    # # File object
    # FS = gcsfs.GCSFileSystem(project=project_name, token=credentials)
    # # Define file path in bucket
    # events_path = "sevir-vil/noaa.csv"
    # # Read file
    # with FS.open(events_path, 'rb') as event_file:
    #     events = pd.read_csv(event_file, parse_dates=['time_utc'], low_memory=False)

    events = pd.read_csv("noaa.csv", parse_dates=['time_utc'], low_memory=False)
    # parse date
    time = dateutil.parser.parse(time_utc)
    
    # image_type filter
    events = events[events.img_type == 'vil']
    
    # datetime filter
    events = events.loc[(events.time_utc.dt.hour <= time.hour)&(events.time_utc.dt.hour >= time.hour - 1)]
    
    events = events[events.pct_missing == 0]
    if len(events) == 0:
        raise Exception('Event Error: Requested time not present in the given location')
    
    # aoi filter, get center lat/lon
    events['cntrlat'] = events.apply(lambda row: (row.llcrnrlat + row.urcrnrlat)/2, axis=1)
    events['cntrlon'] = events.apply(lambda row: (row.llcrnrlon + row.urcrnrlon)/2, axis=1)
    
    # applying geopy.diatance.distance
    events['distance'] = events.apply(lambda row: distance.distance((row.cntrlat,row.cntrlon), (lat,lon)).miles, axis=1)
    events = events.sort_values(by=['distance'])
    
    # next closest point check
    if closest_radius == True:
        close_dist = events.iloc[0].distance
        events = events[events.distance <= close_dist]
    else:
        events = events[events.distance < radius]
        if len(events) == 0:
            raise Exception('Event Error: Requested location not present in the given radius. Try increasing the radius or set closest_radius=True in the query')
    
    event = events.iloc[0]
    
    return str(event.EPISODE_NARRATIVE), str(event.EVENT_NARRATIVE)

# initializes the pipeline
summarize_pipeline = serverless_pipeline()

# handler
def handler(event, context):
    try:
        # loads the incoming event into a dictonary
        
        event = json.loads(event['body'])
        print('Printing event for debugging: ',event)
        lat = event['lat']
        lon = event['lon']
        radius = event['radius']
        time_utc = event['time_utc']
        closest_radius = event['closest_radius']
        
        print(f'summarize_pipeline({lat}, {lon}, {radius}, {time_utc}, {closest_radius})')
        # uses the pipeline to predict the answer
        episode_text, event_text = summarize_pipeline(lat, lon, radius, time_utc, closest_radius)
        print(f"episode_text_final:{episode_text} \n event_text_final:{event_text}")
        return {
            "statusCode": 200,
            "headers": {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                "Access-Control-Allow-Credentials": True

            },
            "body": json.dumps({'episode_summary': episode_text, 'event_summary': event_text})
            # #"summary": json.dumps({'episode_summary': episode_text, 'event_summary': event_text})
            # "episode_summary": episode_text,
            # "event_summary" : event_text
        }
    except Exception as e:
        print("Check ECR error here: ",repr(e))
        return {
            "statusCode": 200,
            "headers": {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                "Access-Control-Allow-Credentials": True

            },
            "body": repr(e)
        }
# lat = 37.318363
# lon = -84.224203
# radius = 200
# time_utc = "2019-06-02 18:33:00"
# closest_radius = True
# events_path = "C:\\Users\\krish\\Desktop\\summarize\\noaa.csv"

# summary(37.318363, -84.224203, 200, "2019-06-02 18:33:00", True)
