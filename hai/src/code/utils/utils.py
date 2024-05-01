import sys
import os
import yaml
import json
import requests
import re

import boto3
import pretty_midi

# 0. 환경설정 parameter들
AWS_BUCKET = "for-capstone-test"

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

def make_and_get_user_folder(file_name: str, user: str):
    data_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data'))
    user_folder = os.path.join(data_path, user)
    os.makedirs(user_folder, exist_ok=True)
    file_path = os.path.join(user_folder, file_name)

    return file_path

def upload_to_s3(bucket_name: str, local_file_name: str, key: str):
    s3_client = boto3.client(service_name='s3', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
    res = s3_client.upload_file(local_file_name, bucket_name, key)

    return res


def change_instrument(instrument: int, midi_object: pretty_midi.PrettyMIDI):
    if len(midi_object.instruments) == 1:
        midi_object.instruments[0].program = instrument
    else:
        pass

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

