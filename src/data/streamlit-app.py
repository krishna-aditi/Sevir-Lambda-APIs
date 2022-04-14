# -*- coding: utf-8 -*-
"""
Created on Wed Mar 23 14:31:40 2022

@author: krish
"""
import streamlit as st
import requests
import base64
import gcsfs
from urllib.parse import unquote
import pathlib
import os
abspath = pathlib.Path(__file__).parent.resolve()

def summarize(params_test,st):
    summary_test = requests.post("https://l9s96iqa91.execute-api.us-east-1.amazonaws.com/dev/summary", json = params_test)      
    sevir_output_summary = summary_test.json()
    print('sevir_output_summary: ', sevir_output_summary)
    if 'episode_summary' and 'event_summary' in sevir_output_summary.keys():
        st.subheader('Episode summary: \n')
        episode = sevir_output_summary['episode_summary']
        st.markdown(f'{episode}')
        st.subheader('Event summary: \n')
        event = sevir_output_summary['event_summary']
        st.markdown(f'{event}')
    else:
        st.error({'ECR error': sevir_output_summary['message']})
def ner(params_test,st):
    summary_test = requests.post("https://g0sjzf2dz6.execute-api.us-east-1.amazonaws.com/dev/ner", json = params_test)      
    sevir_output_ner = summary_test.json()
    print('sevir_output_ner: ', sevir_output_ner)
    if 'episode_ner' and 'event_ner' in sevir_output_ner.keys():
        st.subheader('Episode NER: \n')
        episode = sevir_output_ner['episode_ner']
        st.markdown(f'{episode}')
        st.subheader('Event NER: \n')
        event = sevir_output_ner['event_ner']
        st.markdown(f'{event}')
    else:
        st.error({'ECR error': sevir_output_ner['message']})
def main():
    st.title("API for Federal Avaiation Administration")
    html_temp = """
        <div style="background-color:steelblue;padding:2px">
        <h2 style="color:white;text-align:center;">SEVIR Nowcasting</h2>
        </div>
        """
    
    page = st.sidebar.radio("Select Operation:", ("Nowcast Login", "Live dashboard"))
    if page == 'Live dashboard':
        username = st.text_input("User Name: ")
        password = st.text_input("Password: ", type="password")
        
        authjson = { "username": f"{username}", "password": f"{password}"}
        headers = {"Authorization": f"Basic Og=="}
        s = st.session_state
        if not s:
            s.authenticated = False
        col1, col2 = st.columns([0.2,1])
        if col1.button("Login")  or s.authenticated:
            s.authenticated = True
            token = requests.post("https://sevir-nlp.ue.r.appspot.com/token", data = authjson)
            if col2.button("Log Out"):
                s.authenticated = False
                token = None
                jwttoken = None
                st.markdown(f"Log Out Successful")
                return None
                    
                
                            
            if token.status_code == 200: 
                jwttoken = token.json()['access_token']
                headers = {"Authorization": f"Bearer {jwttoken}"}
                response = requests.post("https://sevir-nlp.ue.r.appspot.com/nowcast/dashboard", headers=headers)
                if response.status_code == 200:
                    url = response.json()['url']
                    st.markdown(f"""
                                <iframe width="600" height="450" src={url} frameborder="0" style="border:0" allowfullscreen></iframe>
                                """, unsafe_allow_html=True)
                else:
                    st.markdown(f"Not an Admin. Not Dashboard is only for admin users.")
            else:
                st.markdown(f"Login Failure. {token.json()['detail']}")
    else:
        st.markdown(html_temp, unsafe_allow_html=True)
        username = st.text_input("User Name: ")
        password = st.text_input("Password: ", type="password")
        
        authjson = { "username": f"{username}", "password": f"{password}"}
        headers = {"Authorization": f"Basic Og=="}
        s = st.session_state
        if not s:
            s.authenticated = False
        col1, col2 = st.columns([0.2,1])
        if col1.button("Login")  or s.authenticated:
            s.authenticated = True
            token = requests.post("https://sevir-nlp.ue.r.appspot.com/token", data = authjson)
            if col2.button("Log Out"):
                s.authenticated = False
                token = None
                jwttoken = None
                st.markdown(f"Log Out Successful")
                return None
                    
                
                            
            if token.status_code == 200: 
                jwttoken = token.json()['access_token']
                headers = {"Authorization": f"Bearer {jwttoken}"}
                lat = st.number_input("Latitude:", format="%.6f")
                lon = st.number_input("Longitude:", format="%.6f")
                radius = st.number_input("Radius:")
                time_utc = st.text_input("Time in UTC:")
                model_type = st.text_input("Model Type:")
                threshold_time_minutes = st.number_input("Threshold Time in Minutes:", format="%.2f")
                closest_radius = st.radio("Would you like to get the closest point, if location not found in chosen radius?", (True, False))
                forced_refresh = st.radio("Would you like to get a fresh generation of output?", (True, False))
                
                # Parameters as JSON
                params_test = {"lat": lat, "lon": lon, "radius": radius, "time_utc": time_utc, "model_type": model_type, "threshold_time_minutes": threshold_time_minutes, "closest_radius": bool(closest_radius), "forced_refresh": bool(forced_refresh)}
                
                params_test_summary = {"lat": lat, "lon": lon, "radius": radius, "time_utc": time_utc, "closest_radius": bool(closest_radius)}
                if st.button("Predict"):
                    nowcast_test = requests.post("https://sevir-nlp.ue.r.appspot.com/nowcast/predict", headers=headers, json = params_test)      
                    sevir_output_test = nowcast_test.json()
                    if 'nowcast_error' in sevir_output_test.keys():
                        st.error({'nowcast_error': sevir_output_test['nowcast_error']})
                    else:
                        st.success('Nowcasted GIF for the requested inputs: ')
                        decoded = unquote(sevir_output_test['gif_path'])
                        path = ''
                        append=False
                        for a in decoded.split('/'):
                            if append and a!='o':
                                path+='/'+a.split('?')[0]
                            if a=='sevir-vil':
                                path+=a
                                append=True
                        project_name = 'Assignment-4'
                        
                        FS = gcsfs.GCSFileSystem(project=project_name)
                        with FS.open(path, 'rb') as data_file:                
                            gif_content = data_file.read()
                        data_url = base64.b64encode(gif_content).decode("utf-8")
                        st.markdown(f'<p align="center"><img src="data:image/gif;base64,{data_url}" alt="Nowcasted GIF"></p>', unsafe_allow_html=True)
                        summarize(params_test_summary,st)
                        ner(params_test_summary,st)
            else:
                st.markdown(f"Login Failure. {token.json()['detail']}")
    return None
        
    
if __name__ == '__main__':
    main()
