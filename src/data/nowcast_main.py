#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar  7 10:59:57 2022

@author: krish
"""
from fastapi import FastAPI
from nowcast_api import nowcast, nowcastBatch
from pydantic import BaseModel # Pydantic is used for data handling
from passlib.context import CryptContext
from typing import Optional, List
from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from google.cloud import bigquery
import os
# User database
users_db = {
    "aditikrishna": {
        "username": "aditikrishna",
        "full_name": "Aditi Krishna",
        "email": "krishna.ad@northeastern.edu",
        "hashed_password": '$2b$12$A19ccgQBlxIDs8OsSyBQR.dSOFfOTY6WnyrA9GQDOs/oVDLaRMmf2',
        "disabled": False,
        "admin": False,
        "limit": 3
    },
    "admin": {
        "username": "admin",
        "full_name": "Administrator",
        "email": "krishna.ad@northeastern.edu",
        "hashed_password": '$2b$12$25DfJDB.uXAUBkVd7W1U2OKPk9q8yO4IGZEL77zLJjPFxrWf3q/Nm',
        "disabled": False,
        "admin": True,
        "limit": -1
    },
    "inactive": {
        "username": "inactive",
        "full_name": "Inactive User",
        "email": "krishna.ad@northeastern.edu",
        "hashed_password": '$2b$12$A19ccgQBlxIDs8OsSyBQR.dSOFfOTY6WnyrA9GQDOs/oVDLaRMmf2',
        "disabled": True,
        "admin": False,
        "limit": 3
    },
    "bigdata": {
        "username": "bigdata",
        "full_name": "Big Data",
        "email": "krishna.ad@northeastern.edu",
        "hashed_password": '$2b$12$A19ccgQBlxIDs8OsSyBQR.dSOFfOTY6WnyrA9GQDOs/oVDLaRMmf2',
        "disabled": False,
        "admin": False,
        "limit": 3
    },
    "mowgu": {
        "username": "mowgu",
        "full_name": "Mowgli Krishna",
        "email": "krishna.ad@northeastern.edu",
        "hashed_password": '$2b$12$A19ccgQBlxIDs8OsSyBQR.dSOFfOTY6WnyrA9GQDOs/oVDLaRMmf2',
        "disabled": False,
        "admin": False,
        "limit": 3
    }
}
# To sign the JWT token we need a secret key like a signature generate one by typing this in yout console " !openssl rand -hex 32 "
SECRET_KEY = 'a4e1f06420e88c39c20d056455c6dcab62f33b5c21761c8327599d0c6fd455ee' #signature to JWT
ALGORITHM = "HS256" #algorithm to validate JWT        
ACCESS_TOKEN_EXPIRE_MINUTES = 60 # 30 minutes token validity time

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    
class User(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None
    admin: Optional[bool] = None
    limit: Optional[int] = None
    
class UserInDB(User):
    hashed_password: str

# Creating a passlib context to hash and verify passwords
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI()

# Functions from https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
# Verify password
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# Create hashed password
def get_password_hash(password):
    return pwd_context.hash(password)

# Get user from database
def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)

# Add new user to database with credentials
def add_user(username, full_name, email, password):    
    hashed = get_password_hash(password)
    users_db.update({username:{"username": f"{username}", "full_name":f"{full_name}", "email":f"{email}", "hashed_password":f"{hashed}"}})
    
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def authenticate_user(fake_db, username: str, password: str):
    user = get_user(fake_db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

async def authenticate(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials!",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = get_user(users_db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: User = Depends(authenticate)):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_current_active_admin(current_user: User = Depends(authenticate)):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    if not current_user.admin:
        raise HTTPException(status_code=400, detail="Not an Admin User")
    return current_user

@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(users_db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password!",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/")
def read_main():
    return 'SEVIR API designed by Aditi and Team'

@app.get("/nowcast/")
def read_nowcast():
    return 'Nowcast API endpoint designed for Federal Aviation Administration'

# Define data shapes that you want to receive using BaseModel
class NowCastParams(BaseModel):
    lat: float
    lon: float
    radius: float
    time_utc: str
    model_type:str = "gan"
    threshold_time_minutes:int = 60
    closest_radius:bool = False
    force_refresh:bool= False


# We need to send JSON data, hence POST method which is our write method
# Endpoint
@app.post("/nowcast/predict")
def nowcast_predict(params: NowCastParams, current_user: User = Depends(get_current_active_user)): # Receive whatever is in the body
    """
    **SEVIR Nowcast API using FastAPI, for Federal Aviation Administration usecase.**
    
    Submitted by - Team 2
    * Aditi Krishna
    * Abhishek Jaiswal
    * Sushrut Mujumdar
    """
    username = current_user.username
    credentials_path = 'sevir-nlp-cred.json'
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
    current_hits = 0
    today = datetime.now().strftime('%Y-%m-%d')
    bq_client = bigquery.Client()
    query= f"""
    SELECT API_call_count
    FROM `sevir-nlp.api_record.logs`
    WHERE Username= '{username}' AND DATE(In_time) = '{today}'
    ORDER BY API_call_count DESC 
    LIMIT 1
    """
    results = bq_client.query(query).result()
    for result in results:
        current_hits = result.API_call_count
        
    
    if current_user.limit > current_hits or current_user.limit<0:
        pass
    else:
        return {"rate_limit_error": "Maximum tries reached"}
    api_name = 'Nowcast'
    
    intime = datetime.now()
    output = nowcast(params.lat, params.lon, params.radius, params.time_utc, params.model_type, params.closest_radius, params.threshold_time_minutes, params.force_refresh)
    outtime = datetime.now()
    totalproctime = (outtime-intime).seconds
    api_call_count = current_hits+1
    table = bq_client.get_table("{}.{}.{}".format('sevir-nlp', 'api_record', 'logs'))
    if 'Error' in output.keys():
        status = output['Error']
        key = 'nowcast_error'
        value = output['Error']
    else:
        status = 'Success'
        key = 'gif_path'
        value = output['display']
    rows_to_insert = [
    {u'Username':username,u'API_name':api_name, u'In_time':intime.strftime('%Y-%m-%d %H:%M:%S'), u'Out_time': outtime.strftime('%Y-%m-%d %H:%M:%S'), 
     u'Status':status, u'API_call_count': api_call_count, u'Processing_time': totalproctime}
    ]
    
    errors = bq_client.insert_rows_json(table, rows_to_insert)

    if errors != []:
        key = 'nowcast_error'
        value = f'Fatal Issue as Logging Failed: {errors}'
    return {key:value}

# Sample json body
'''
{
 "lat":37.318363,
 "lon":-84.224203, 
 "radius":200,
 "time_utc":"2019-06-02 18:33:00",
 "model_type":"gan",
 "threshold_time_minutes":30,
 "closest_radius":true,
 "force_refresh":false
}
'''
@app.post("/nowcast/batch") # authentication only for the admin
def nowcast_list(params_list: List[NowCastParams], current_user: User = Depends(get_current_active_admin)):
    # call out original nowcast function 
    # pass the list of input
    output = nowcastBatch(params_list)
    if 'Error' in output.keys():
        return {'nowcast_error': output['Error']}
    else:
        return {"gif_path": output['display']}
    
@app.post("/nowcast/dashboard") # authentication only for the admin
def dashboardURL(current_user: User = Depends(get_current_active_admin)):
    # call out original nowcast function 
    # pass the list of input
    return {'url':'https://datastudio.google.com/embed/reporting/aba0d648-f51e-4817-87bc-c8dd5c8bf1af/page/iFzpC'}