import sys
import os
import yaml
import json
import requests
import re
import mido
import boto3
import librosa

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

# def download_from_s3_requests(s3_url: str, local_file_path: str):
#     response = requests.get(s3_url)
#     with open(local_file_path, 'wb') as f:
#         f.write(response.content)

#     return os.path.exists(local_file_path)

def download_from_s3_requests(s3_url: str, local_file_path: str):
    try:
        response = requests.get(s3_url)
        response.raise_for_status()  # 요청이 실패했을 경우 예외 발생
    except requests.exceptions.RequestException as e:
        print(f"Error downloading from S3: {e}")
        return False  # 다운로드 실패를 나타내는 값 반환

    try:
        with open(local_file_path, 'wb') as f:
            f.write(response.content)
    except IOError as e:
        print(f"Error writing to local file: {e}")
        return False  # 파일 쓰기 실패를 나타내는 값 반환

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

# def upload_to_s3(local_file_name: str, key: str):
#     s3_client = boto3.client(service_name='s3', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
#     res = s3_client.upload_file(local_file_name, BUCKET_NAME, key)

#     # s3_client.put_object_acl(ACL='public-read', Bucket=BUCKET_NAME, Key=key)
#     object_url = f"https://{BUCKET_NAME}.s3.ap-northeast-2.amazonaws.com/{key}"
    
#     return object_url

def upload_to_s3(local_file_name: str, key: str):
    try:
        s3_client = boto3.client(service_name='s3', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
        s3_client.upload_file(local_file_name, BUCKET_NAME, key)

        # 권한 설정을 위한 코드 (선택 사항)
        # s3_client.put_object_acl(ACL='public-read', Bucket=BUCKET_NAME, Key=key)
        
        object_url = f"https://{BUCKET_NAME}.s3.ap-northeast-2.amazonaws.com/{key}"
        return object_url

    except ClientError as e:
        # 업로드 중에 발생한 클라이언트 오류 처리
        print(f"Error uploading to S3: {e}")
        return None

    except Exception as e:
        # 기타 예외 처리
        print(f"Unexpected error uploading to S3: {e}")
        return None


def change_instrument(instrument: str, midi_object: pretty_midi.PrettyMIDI):
    if instrument == "p":
        instrument_no = 0
    elif instrument == "g":
        instrument_no = 25
    elif instrument == "b":
        instrument_no = 32
    elif instrument == "l":
        instrument_no = 80
        
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


def get_tempo(midi_file):
    for track in midi_file.tracks:
        for msg in track:
            if msg.type == 'set_tempo':
                return msg.tempo
    return 500000


def set_tempo(midi_file, new_tempo):
    for track in midi_file.tracks:
        for msg in track:
            if msg.type == 'set_tempo':
                msg.tempo = new_tempo

def change_tempo_of_midi(original_file_path, generated_file_path, output_path):
    # Load the MIDI files
    midi1 = mido.MidiFile(original_file_path)
    midi2 = mido.MidiFile(generated_file_path)
    
    # Get the tempo from the first MIDI file
    tempo = get_tempo(midi1)
    print("original tempo: ", tempo)
    
    # Set the tempo for the second MIDI file
    print("generated tempo: ", get_tempo(midi2))
    set_tempo(midi2, tempo)
    print("changed tempo: ", get_tempo(midi2))
    
    # Save the modified second MIDI file
    midi2.save(output_path)
    print(f"Tempo of the second MIDI file has been set to match the first MIDI file and saved as {output_path}")

def merge_midi_files(original_file_path, generated_file_path, output_file):
    # 첫 번째 MIDI 파일 로드
    midi1 = mido.MidiFile(original_file_path)
    # 두 번째 MIDI 파일 로드
    midi2 = mido.MidiFile(generated_file_path)
    
    for track in midi2.tracks:
        midi1.tracks.append(track)

    # 병합된 MIDI 파일 저장
    midi1.save(output_file)

def remove_instrument_events(midi_file_path, instrument, output_path):
    # 특정 악기 이벤트를 제거할 새로운 MIDI 파일 객체 생성
    new_midi = mido.MidiFile()
    midi = mido.MidiFile(midi_file_path)

    if instrument == 'p':
        instrument_num = 0
    elif instrument == 'g':
        instrument_num = 25
    elif instrument == 'b':
        instrument_num = 32
    elif instrument == 's':
        instrument_num = 48
    elif instrument == 'l':
        instrument_num = 80

    remove_flag = False

    # 입력 MIDI 파일의 각 트랙을 순회하면서 필요한 악기 이벤트를 제거하고 새로운 MIDI 파일에 추가
    for track in midi.tracks:
        new_track = mido.MidiTrack()
        for msg in track:
            # 프로그램 변경 이벤트(악기 변경)를 찾아 해당 악기 이벤트를 제거하거나 볼륨을 0으로 설정
            if isinstance(msg,mido.messages.messages.Message):
                if msg.type == 'program_change':
                    if instrument == 'p' and msg.channel == 0 and msg.program == instrument_num:
                        remove_flag = True
                    elif msg.program == instrument_num:
                        remove_flag = True
                    else:
                        remove_flag = False

            if remove_flag:
                continue
            else:
                new_track.append(msg)
                
        new_midi.tracks.append(new_track)

    new_midi.save(output_path)
    
def extract_tempo(file_path: str):
    y, sr = librosa.load(file_path)
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    return tempo

def process_instrument_train(midi_file):
    # 0 - 7, 16 - 23 -> Piano
    # 24 - 31 -> Guitar
    # 32 - 39 -> Bass
    # 40 - 47 -> Strings
    # 112 - 119 -> Drum

    new_midi = mido.MidiFile()
    
    for i, track in enumerate(midi_file.tracks):
        if i != track_number:  # 트랙 번호가 일치하지 않으면 무시하고 다음 트랙으로 이동
            new_midi.tracks.append(track)
            continue
        
        # 특정 트랙의 악기가 주어진 범위에 속하는지 확인
        keep_track = False
        for msg in track:
            if msg.type == 'program_change':
                if min_program <= msg.program <= max_program:
                    keep_track = True
                    break
        
        if keep_track:
            new_midi.tracks.append(track)
    
    return new_midi