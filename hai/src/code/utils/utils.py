import sys
import os
import yaml
import json
import requests
import re

import boto3
from botocore.exceptions import ClientError

import pretty_midi

# 0. 환경설정 parameter들

current_dir = os.path.dirname(os.path.abspath(__file__))
config_file_path = os.path.join(current_dir, '../../../..', 'configs', 'config.json')
    
with open(config_file_path, 'r') as f:
    config = json.load(f)
    
AWS_ACCESS_KEY_ID = config['AWS_ACCESS_KEY_ID']
AWS_SECRET_ACCESS_KEY = config['AWS_SECRET_ACCESS_KEY']
BUCKET_NAME = config['BUCKET_NAME']
FOLDER_NAME = config['FOLDER_NAME']


def download_from_s3(bucket_name: str, local_file_name: str, key: str):    
    s3_client = boto3.client(service_name='s3', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
    res = s3_client.download_file(Bucket=bucket_name, Key=key, Filename=local_file_name)

    return res

def download_from_s3_requests(s3_url: str, local_file_path: str):
    response = requests.get(s3_url)
    with open(local_file_path, 'wb') as f:
        f.write(response.content)

    return os.path.exists(local_file_path)

def get_bucket_region_from_s3_url(s3_url: str):
    pattern = r'^https://([^.]+)\.s3\.([^.]+)\.amazonaws\.com'
    match = re.match(pattern, s3_url)
    if match:
        bucket_name = match.group(1)
        region = match.group(2)
        return bucket_name, region
    else:
        return None, None

def get_file_path_from_s3_url(s3_url: str):
    file_path = s3_url.split('/')[-1]
    return os.path.basename(file_path)

def get_s3_client():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_file_path = os.path.join(current_dir, '../../../..', 'configs', 'config.json')
    
    with open(config_file_path, 'r') as f:
        config = json.load(f)
    
    s3_client = boto3.client('s3',
                             aws_access_key_id=config['AWS_ACCESS_KEY_ID'],
                             aws_secret_access_key=config['AWS_SECRET_ACCESS_KEY'])
    
    return s3_client

def make_s3_folder(s3_client: boto3.client, user: str):

    try:
        # 해당 경로의 객체를 가져와서 예외가 발생하지 않으면 폴더가 이미 존재한다는 것
        s3_client.head_object(Bucket=BUCKET_NAME, Key=(FOLDER_NAME+user+'/'))
        print("created!")
    except ClientError as e:
        # 폴더가 없는 경우에만 폴더 생성
        if e.response['Error']['Code'] == '404':
            s3_client.put_object(Bucket=BUCKET_NAME, Key=(FOLDER_NAME+user+'/'))
            print(f"{BUCKET_NAME} 버킷에 {FOLDER_NAME+user} 폴더가 생성되었습니다.")
        else:
            # 다른 에러인 경우 예외 발생
            raise
    else:
        print(f"{BUCKET_NAME} 버킷에 {FOLDER_NAME+user} 폴더는 이미 존재합니다.")
    
    return FOLDER_NAME+user+'/'

def make_and_get_user_folder(file_name: str, user: str):
    data_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../data'))
    user_folder = os.path.join(data_path, user)
    os.makedirs(user_folder, exist_ok=True)
    file_path = os.path.join(user_folder, file_name)

    return file_path

def make_and_get_user_folder_path(user: str):
    data_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../data'))
    user_folder = os.path.join(data_path, user)
    os.makedirs(user_folder, exist_ok=True)

    return user_folder

def upload_to_s3(local_file_name: str, key: str):
    s3_client = boto3.client(service_name='s3', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
    res = s3_client.upload_file(local_file_name, BUCKET_NAME, key)

    # s3_client.put_object_acl(ACL='public-read', Bucket=BUCKET_NAME, Key=key)
    object_url = f"https://{BUCKET_NAME}.s3.ap-northeast-2.amazonaws.com/{key}"
    
    return object_url


def change_instrument(instrument: str, midi_object: pretty_midi.PrettyMIDI):
    if instrument == "p":
        instrument_no = 0
    elif instrument == "g":
        instrument_no = 25
    elif instrument == "b":
        instrument_no = 32
        
    if len(midi_object.instruments) == 1:
        midi_object.instruments[0].program = instrument_no
    else:
        pass

    print("instrument changed")
    return midi_object




def load_yaml_config(path):
    with open(path) as f:
        config = yaml.full_load(f)
    return config

def load_json_params(path):
    with open(path) as f:
        params = json.load(f)
    return params

def merge_opts_to_config(config, opts):
    def modify_dict(c, nl, v):
        if len(nl) == 1:
            c[nl[0]] = type(c[nl[0]])(v)
        else:
            # print(nl)
            c[nl[0]] = modify_dict(c[nl[0]], nl[1:], v)
        return c

    if opts is not None and len(opts) > 0:
        assert len(opts) % 2 == 0, "each opts should be given by the name and values! The length shall be even number!"
        for i in range(len(opts) // 2):
            name = opts[2*i]
            value = opts[2*i+1]
            config = modify_dict(config, name.split('.'), value)
    return config 

