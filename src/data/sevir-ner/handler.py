import dateutil.parser
import pandas as pd
from geopy import distance
from transformers import AutoModelForTokenClassification, AutoTokenizer, pipeline
import json

def serverless_pipeline():
    # initialize the model architecture and weights
    model = AutoModelForTokenClassification.from_pretrained("./model")
    
    # initialize the model tokenizer
    tokenizer = AutoTokenizer.from_pretrained("./model")
    
    def summary(lat, lon, radius, time_utc, closest_radius):
        episode_text, event_text =  filterEvents(lat, lon, radius, time_utc, closest_radius)
        print(f'episode_text: {episode_text}')
        NER = pipeline("ner",model=model,tokenizer=tokenizer)
        episode_ner = NER(episode_text)
        print(f"Episode NER: {episode_ner}")
        
        # generate the summarization event output
        print(f'event_text: {event_text}')
        NER = pipeline("ner",model=model,tokenizer=tokenizer)
        event_ner = NER(event_text)
        
        print(f"Event NER: {event_ner}")
        
        return episode_ner, event_ner
    return summary
    
def filterEvents(lat, lon, radius, time_utc, closest_radius):
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
ner_pipeline = serverless_pipeline()

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
        
        print(f'ner_pipeline({lat}, {lon}, {radius}, {time_utc}, {closest_radius})')
        # uses the pipeline to predict the answer
        episode_ner, event_ner = ner_pipeline(lat, lon, radius, time_utc, closest_radius)
        print(f"episode_text_final:{episode_ner} \n event_text_final:{event_ner}")
        return {
            "statusCode": 200,
            "headers": {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                "Access-Control-Allow-Credentials": True

            },
            "body": json.dumps({'episode_ner': episode_ner, 'event_ner': event_ner})
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
# events_path = "C:\\Users\\krish\\Desktop\\ner\\noaa.csv"

# summary(37.318363, -84.224203, 200, "2019-06-02 18:33:00", True)