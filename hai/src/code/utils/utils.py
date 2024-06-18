import sys
import os
import yaml
import json
import requests
import re
import mido
import boto3
from pydub import AudioSegment
import librosa
from miditoolkit import MidiFile
import random
import string
from botocore.exceptions import ClientError
import subprocess

from tqdm import tqdm

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

def check_file_exists(bucket_name, file_key):
    s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
    
    try:
        s3.head_object(Bucket=bucket_name, Key=file_key)
        return True
    except Exception as e:
        return False



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


def change_instrument1(instrument: str, midi_object: pretty_midi.PrettyMIDI):
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

def change_instrument(instrument: str, mid: mido.MidiFile):
    # 악기 번호 설정
    if instrument == "p":
        instrument_no = 0
    elif instrument == "g":
        instrument_no = 24
    elif instrument == "b":
        instrument_no = 31
    elif instrument == "l":
        instrument_no = 79
    else:
        raise ValueError("Invalid instrument")

    # 프로그램 변경 메시지 생성
    program_change = mido.Message('program_change', program=instrument_no)

    # 모든 트랙에 프로그램 변경 메시지 추가
    for track in mid.tracks:
        track.insert(0, program_change)

    # 변경된 MIDI 파일 저장
    return mid



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
    
    return midi_file

def change_tempo_of_midi(mid):
    # Get the tempo from the first MIDI file
    tempo = get_tempo(mid)
    print("original tempo: ", tempo)
    
    set_tempo(mid, tempo)
    
    return mid

# def merge_midi_files(midi1, midi2, output_file):
    
#     for track in midi2.tracks:
#         midi1.tracks.append(track)

#     # 병합된 MIDI 파일 저장
#     midi1.save(output_file)

def merge_midi_files(midi1, midi2):
    # Create a new MIDI file to hold the merged tracks
    merged_midi = mido.MidiFile(ticks_per_beat=midi1.ticks_per_beat)

    # Helper function to convert time values based on ticks_per_beat
    def convert_time(msg, old_ticks_per_beat, new_ticks_per_beat):
        if msg.time == 0:
            return msg.time
        scale_factor = new_ticks_per_beat / old_ticks_per_beat
        return int(msg.time * scale_factor)

    # Add tracks from midi1 to the merged MIDI file
    for track in midi1.tracks:
        new_track = mido.MidiTrack()
        for msg in track:
            new_msg = msg.copy(time=convert_time(msg, midi1.ticks_per_beat, merged_midi.ticks_per_beat))
            new_track.append(new_msg)
        merged_midi.tracks.append(new_track)

    # Add tracks from midi2 to the merged MIDI file
    for track in midi2.tracks:
        new_track = mido.MidiTrack()
        for msg in track:
            new_msg = msg.copy(time=convert_time(msg, midi2.ticks_per_beat, merged_midi.ticks_per_beat))
            new_track.append(new_msg)
        merged_midi.tracks.append(new_track)

    return merged_midi


# def change_velocity(midi: mido.MidiFile, lead_instrument: str, instrument_set: str):

def change_velocity(midi: mido.MidiFile):
    # 악기 번호를 설정합니다.
    instrument_mapping = {
        'piano': 0,
        'guitar': 25,
        'bass': 32
    }

    # 설정할 벨로시티 값을 설정합니다.
    velocity_mapping = {
        'drum': 60,
        'piano': 80,
        'guitar': 80,
        'bass': 80
    }

    # 벨로시티를 변경하는 함수
    def set_velocity(msg, velocity):
        if msg.type in ['note_on', 'note_off']:
            return msg.copy(velocity=velocity)
        return msg

    # MIDI 파일의 각 트랙을 순회하면서 벨로시티를 변경합니다.
    for i, track in tqdm(enumerate(midi.tracks)):
        new_track = mido.MidiTrack()
        current_program = None

        for msg in track:
            if msg.type == 'program_change':
                current_program = msg.program
            elif msg.type in ['note_on', 'note_off']:
                if msg.channel == 9:
                    # 드럼 채널
                    msg = set_velocity(msg, velocity_mapping['drum'])
                elif current_program is not None:
                    for instrument, program in instrument_mapping.items():
                        if current_program == program:
                            msg = set_velocity(msg, velocity_mapping[instrument])
                            break
            new_track.append(msg)
        
        midi.tracks.append(new_track)

    return midi


def modify_midi_velocity(midi_data, piano_velocity=50, guitar_velocity=70, bass_velocity=90, drum_velocity=60):
    # 프로그램 채널 확인
    program_channels = [None] * 16

    # 트랙 순회
    for track in midi_data.tracks:
        for msg in track:
            if msg.type == 'program_change':
                program_channels[msg.channel] = msg.program

    # velocity 변경
    for i, track in enumerate(midi_data.tracks):
        for j, msg in enumerate(track):
            if msg.type == 'note_on' or msg.type == 'note_off':
                if msg.channel == 9:  # 드럼 채널
                    midi_data.tracks[i][j].velocity = drum_velocity
                else:
                    program = program_channels[msg.channel]
                    if program is not None:
                        if 0 <= program <= 7:  # 피아노
                            midi_data.tracks[i][j].velocity = piano_velocity
                        elif 24 <= program <= 31:  # 기타
                            midi_data.tracks[i][j].velocity = guitar_velocity
                        elif 32 <= program <= 39:  # 베이스
                            midi_data.tracks[i][j].velocity = bass_velocity

    return midi_data



def remove_instrument_events(mid, instrument, output_path):
    # 특정 악기 이벤트를 제거할 새로운 MIDI 파일 객체 생성

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

    # 입력 MIDI 파일의 각 트랙을 순회하면서 필요한 악기 이벤트를 제거하고 새로운 MIDI 파일에 추가
    for track in mid.tracks:
        new_msgs = []
        remove_flag = False

        for msg in track:
            # 프로그램 변경 이벤트(악기 변경)를 찾아 해당 악기 이벤트를 제거하거나 볼륨을 0으로 설정
            if isinstance(msg,mido.messages.messages.Message):
                if msg.type == 'program_change':
                    if (instrument == 'p' and msg.channel == 0 and msg.program == instrument_num) or msg.program == instrument_num:
                        remove_flag = True
                    else:
                        remove_flag = False

            if not remove_flag:
                new_msgs.append(msg)
                
        track.clear()
        track.extend(new_msgs)

    mid.save(output_path)
    return mid

def extract_tempo(audio_path: str):
    y, sr = librosa.load(audio_path)
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    return tempo

def make_audio_to_mp3(audio_path: str):
    output_file_path = audio_path.split('.')[0] + ".mp3"

    audio = AudioSegment.from_file(audio_path)
    audio.export(output_file_path, format="mp3")

    return output_file_path

def extract_key(audio_path: str):
    # 오디오 파일을 로드합니다.
    y, sr = librosa.load(audio_path)
    
    # 피치 클래스 (C, C#, D, D#, E, F, F#, G, G#, A, A#, B) 프로필을 추출합니다.
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    
    # 각 피치 클래스의 평균 값을 계산합니다.
    chroma_mean = chroma.mean(axis=1)
    
    # 가장 높은 값을 가진 피치 클래스를 찾습니다.
    key_index = chroma_mean.argmax()
    
    # 피치 클래스에 해당하는 키를 정의합니다.
    keys = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    
    # 키를 반환합니다.
    return keys[key_index]

def separate_melody(midi_file: mido.MidiFile, midi_path: str, resolution: int):

    # 멜로디와 반주를 위한 새로운 MIDI 파일 생성
    melody_file = mido.MidiFile(ticks_per_beat=resolution)
    accompaniment_file = mido.MidiFile(ticks_per_beat=resolution)

    # 원본 메타데이터 및 기타 비노트 이벤트를 새로운 파일에 복사
    for i, track in enumerate(midi_file.tracks):
        new_melody_track = mido.MidiTrack()
        new_accompaniment_track = mido.MidiTrack()
        
        melody_file.tracks.append(new_melody_track)
        accompaniment_file.tracks.append(new_accompaniment_track)
        
        for msg in track:
            if msg.type in ['note_on', 'note_off']:
                if msg.note > 59:
                    # 멜로디 노트를 멜로디 트랙에 복사
                    new_melody_track.append(msg)
                    # 반주 트랙에는 음소거된 노트 추가
                    if msg.type == 'note_on':
                        accompaniment_msg = msg.copy(velocity=0)
                        new_accompaniment_track.append(accompaniment_msg)
                    else:
                        melody_msg = msg.copy(velocity=80)
                        new_accompaniment_track.append(melody_msg)
                else:
                    # 반주 노트를 반주 트랙에 복사
                    new_accompaniment_track.append(msg)
                    # 멜로디 트랙에는 음소거된 노트 추가
                    if msg.type == 'note_on':
                        melody_msg = msg.copy(velocity=0)
                        new_melody_track.append(melody_msg)
                    else:
                        accompaniment_msg = msg.copy(velocity=80)
                        new_melody_track.append(accompaniment_msg)
            else:
                # 다른 메시지들(e.g., 컨트롤 체인지, 프로그램 체인지)은 두 트랙에 복사
                new_melody_track.append(msg)
                new_accompaniment_track.append(msg)
    
    # 새로운 MIDI 파일 저장
    accompaniment_path = midi_path.split('/')[-1].split('.')[0] + "_accompaniment.mid"
    melody_path = midi_path.split('/')[-1].split('.')[0] + "_melody.mid"

    accompaniment_file.save(accompaniment_path)
    melody_file.save(melody_path)

    return melody_path, accompaniment_path


def change_tempo(mid: mido.MidiFile, tempo: int):
    # BPM을 마이크로초 per 비트로 변환
    new_tempo = mido.bpm2tempo(tempo)
    
    # 새로운 트랙을 만들어 템포 메시지 추가
    for track in mid.tracks:
        for i, msg in enumerate(track):
            if msg.type == 'set_tempo':
                track[i] = mido.MetaMessage('set_tempo', tempo=new_tempo)
    
    # 수정된 MIDI 파일 저장
    return mid

def change_key_signature(mid: mido.MidiFile, key_signature: str):
    # 새로운 키 시그니처 메시지 생성
    new_key_msg = mido.MetaMessage('key_signature', key=key_signature)

    # 모든 트랙에 대해 반복
    for j, track in enumerate(mid.tracks):
        key_found = False  # 키 시그니처가 이미 있는지 여부를 나타내는 플래그
        
        # 트랙의 메시지를 순회하면서 키 시그니처를 찾음
        for i, msg in enumerate(track):
            if msg.type == 'key_signature':
                # 키 시그니처를 새로운 키로 변경
                track[i] = new_key_msg
                key_found = True  # 키 시그니처를 발견했음을 표시
                break
        
        # 키 시그니처가 발견되지 않은 경우, 트랙의 시작에 새로운 키 시그니처 추가
        if not key_found:
            track.insert(0, new_key_msg)
    
    # 수정된 MIDI 파일 반환
    return mid

def remove_pitchwheel(midi_path: str):
    midi_file = mido.MidiFile(midi_path)
    new_midi_file = mido.MidiFile()

    for i, track in enumerate(midi_file.tracks):
        new_track = mido.MidiTrack()
        new_midi_file.tracks.append(new_track)
        
        for msg in track:
            if msg.type != 'pitchwheel':
                new_track.append(msg)
    
    new_midi_file.save(midi_path)

def get_midi_division(midi_path: str) -> int:
    midi_file = mido.MidiFile(midi_path)
    return midi_file.ticks_per_beat

def generate_random_string(length=4):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def convert_midi_to_mp3(input_midi, output_mp3):
    timidity_process = subprocess.run(['timidity', input_midi, '-Ow', '-o', 'output.wav'])
    lame_process = subprocess.run(['lame', 'output.wav', output_mp3])
