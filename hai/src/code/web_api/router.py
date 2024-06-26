import os
import json
import subprocess
import copy

import miditoolkit
import numpy as np

<<<<<<< HEAD
from fastapi import APIRouter, Request
import music21
=======
from fastapi import FastAPI, APIRouter, Response, HTTPException, Request
from fastapi.responses import JSONResponse
import torch
>>>>>>> acf6a3b79554c974d03c97b5e3ae8924912c0720

from models.schemas import GenerationInput
from models.music_models import Mp3ToMIDIModel

from models.track_generation import tokens_to_ids, ids_to_tokens, empty_index, pad_index
<<<<<<< HEAD
from models.track_generation import F, encoding_to_MIDI, parse_condition, parse_content
=======
from models.track_generation import F, encoding_to_MIDI, parse_condition, parse_content, process_octuple_midi

from models.getmusic.utils.misc import seed_everything, merge_opts_to_config, modify_config_for_debug
from models.getmusic.engine.logger import Logger
from models.getmusic.engine.solver import Solver
from models.getmusic.modeling.build import build_model
>>>>>>> acf6a3b79554c974d03c97b5e3ae8924912c0720
from models.initializing import initialize

from utils.utils import *

import pickle
import miditoolkit
from models.getmusic.utils.midi_config import *
from models.getmusic.utils.magenta_chord_recognition import infer_chords_for_sequence, _key_chord_distribution,\
    _key_chord_transition_distribution, _CHORDS, _PITCH_CLASS_NAMES, NO_CHORD

NODE_RANK = os.environ['INDEX'] if 'INDEX' in os.environ else 0
NODE_RANK = int(NODE_RANK)
MASTER_ADDR, MASTER_PORT = (os.environ['CHIEF_IP'], 22275) if 'CHIEF_IP' in os.environ else ("127.0.0.1", 29500)
MASTER_PORT = int(MASTER_PORT)
DIST_URL = 'tcp://%s:%s' % (MASTER_ADDR, MASTER_PORT)
NUM_NODE = os.environ['HOST_NUM'] if 'HOST_NUM' in os.environ else 1

inst_to_row = { '80':0, '32':1, '128':2,  '25':3, '0':4, '48':5, '129':6}
prog_to_abrv = {'0':'P','25':'G','32':'B','48':'S','80':'M','128':'D'}
track_name = ['lead', 'bass', 'drum', 'guitar', 'piano', 'string']

root_dict = {'C': 0, 'C#': 1, 'D': 2, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7, 'Ab': 8, 'A': 9, 'Bb': 10, 'B': 11}
kind_dict = {'null': 0, 'm': 1, '+': 2, 'dim': 3, 'seven': 4, 'maj7': 5, 'm7': 6, 'm7b5': 7}
root_list = list(root_dict.keys())
kind_list = list(kind_dict.keys())

_CHORD_KIND_PITCHES = {
    'null': [0, 4, 7],
    'm': [0, 3, 7],
    '+': [0, 4, 8],
    'dim': [0, 3, 6],
    'seven': [0, 4, 7, 10],
    'maj7': [0, 4, 7, 11],
    'm7': [0, 3, 7, 10],
    'm7b5': [0, 3, 6, 10],
}

ts_dict = dict()
ts_list = list()
for i in range(0, max_ts_denominator + 1):  # 1 ~ 64
    for j in range(1, ((2 ** i) * max_notes_per_bar) + 1):
        ts_dict[(j, 2 ** i)] = len(ts_dict)
        ts_list.append((j, 2 ** i))
dur_enc = list()
dur_dec = list()
for i in range(duration_max):
    for j in range(pos_resolution):
        dur_dec.append(len(dur_enc))
        for k in range(2 ** i):
            dur_enc.append(len(dur_dec) - 1)

tokens_to_ids = {}
ids_to_tokens = []
pad_index = None
empty_index = None

current_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(current_dir, '../models/getmusic/utils/key_profile.pickle')
key_profile = pickle.load(open(file_path, 'rb'))

pos_in_bar = beat_note_factor * max_notes_per_bar * pos_resolution

chord_pitch_out_of_key_prob = 0.01
key_change_prob = 0.001
chord_change_prob = 0.5
key_chord_distribution = _key_chord_distribution(
    chord_pitch_out_of_key_prob=chord_pitch_out_of_key_prob)
key_chord_loglik = np.log(key_chord_distribution)
key_chord_transition_distribution = _key_chord_transition_distribution(
    key_chord_distribution,
    key_change_prob=key_change_prob,
    chord_change_prob=chord_change_prob)
key_chord_transition_loglik = np.log(key_chord_transition_distribution)

router = APIRouter()
mp3_to_midi = Mp3ToMIDIModel()
args, Logger, solver, tokens_to_ids, ids_to_tokens, pad_index, empty_index = initialize()

<<<<<<< HEAD

=======
>>>>>>> acf6a3b79554c974d03c97b5e3ae8924912c0720
# mp3 input, midi input 나눠서
@router.post("/start_generation/")
async def start_generation(json_input: Request):

    # 1. audio 다운로드 수행
    body = await json_input.body()
    body_dict = json.loads(body)
    input = GenerationInput(**body_dict)
<<<<<<< HEAD
    print(input)
    input_file_name = get_file_path_from_s3_url(s3_url=input.s3_url)
    input_file_path = make_and_get_user_folder(file_name=input_file_name, user=input.user)    
    print(input_file_path)
=======

    input_file_name = get_file_path_from_s3_url(s3_url=input.s3_url)
    input_file_path = make_and_get_user_folder(file_name=input_file_name, user=input.user)    
>>>>>>> acf6a3b79554c974d03c97b5e3ae8924912c0720
    
    download_from_s3_requests(s3_url=input.s3_url,
                              local_file_path=input_file_path)
    
    # 2. mp3 -> midi 예측 수행
    if input_file_name.endswith('mid'):
<<<<<<< HEAD
        midi_obj = miditoolkit.midi.parser.MidiFile(input_file_path)
        
        resolution = midi_obj.ticks_per_beat
        origin_tempo = midi_obj.tempo_changes[0].tempo
        midi_file_path = input_file_path

        midi_data = mido.MidiFile(midi_file_path, ticks_per_beat=resolution)
        midi_data_origin = copy.deepcopy(midi_data)

        midi_data = change_instrument(instrument=input.instrument, mid=midi_data)
        midi_data.save(midi_file_path)

        if len(midi_data.tracks) >= 2:
            new_track = mido.MidiTrack()
            for msg in midi_data.tracks[0]:
                if isinstance(msg, mido.MetaMessage):
                    new_track.append(msg)
                else:
                    if 'velocity' in msg.dict():
                        msg.velocity = 0
                        new_track.append(msg)
            
            second_track = midi_data.tracks[1:]
            midi_data.tracks = [new_track]
            for t in second_track:
                midi_data.tracks.append(t)
        
        midi_file_path = midi_file_path.split('.')[0] + "_acc.mid"
        midi_data.save(midi_file_path)
        midi_path = midi_file_path

    elif input_file_name.endswith('pdf'):
        gradle_cmd = "./audiveris/gradlew"
        mxl_path = '/'.join(input_file_path.split('/')[:-1])
        cmd_args = f"-batch,-export,-output,{mxl_path},--,{input_file_path}"
        gradle_args = f"-PcmdLineArgs=\"{cmd_args}\""
        java_args = "-Dorg.gradle.jvmargs='-Djava.awt.headless=true'"
        full_command = f"{gradle_cmd} run {gradle_args} {java_args}" 
        
        os.system(full_command)
        
        mxl_file = mxl_path + "/" + input_file_name.split('.')[0] + '.mxl'
        midi_path = mxl_path + "/" + input_file_name.split('.')[0] + '.mid'
        
        mxl_to_mid_command = f"xvfb-run -a mscore -o {midi_path} {mxl_file}"
        os.system(mxl_to_mid_command)
        
        midi_data = mido.MidiFile(midi_path)

        origin_tempo = input.tempo
        midi_data = change_tempo(midi_data, origin_tempo)
        midi_data_origin = copy.deepcopy(midi_data)
        
        if len(midi_data.tracks) >= 2:
            new_track = mido.MidiTrack()
            for msg in midi_data.tracks[0]:
                if isinstance(msg, mido.MetaMessage):
                    new_track.append(msg)
                else:
                    if 'velocity' in msg.dict():
                        msg.velocity = 0
                        new_track.append(msg)

            second_track=midi_data.tracks[1:]
            midi_data.tracks = [new_track]
            for t in second_track:
                midi_data.tracks.append(t)
        
        midi_file_path = midi_path.split('.')[0] + "_acc.mid"
        midi_data.save(midi_file_path)
        midi_path = midi_file_path
        resolution = 480

    else:
        if not input_file_path.endswith('.mp3'):
            audio_file_path = make_audio_to_mp3(audio_path=input_file_path)

        audio_file_path = input_file_path
        tempo = extract_tempo(audio_path=audio_file_path)[0]
        
        key = extract_key(audio_path=audio_file_path)

        model_output, midi_data, note_events = mp3_to_midi.pred(audio_path=audio_file_path, tempo=tempo)
        resolution = midi_data.resolution

        midi_file_path = f"{input_file_path.split('.')[0]}.mid"
        midi_data.write(midi_file_path)
        midi_data_origin = copy.deepcopy(midi_data)

        # change to mido.MidiFile
        midi_data = mido.MidiFile(midi_file_path, ticks_per_beat=resolution)
        midi_data = change_tempo(mid=midi_data, tempo=tempo)
        midi_data = change_key_signature(mid=midi_data, key_signature=key)
        midi_data.save(midi_file_path)
    
        # 3. instrument 변경 (midi의 instrument 바꿔주기)   
        midi_data = change_instrument(instrument=input.instrument, mid=midi_data)

        # 4. 반주가 있는 경우는 반주 활용, 멜로디만 있는 경우는 멜로디 활용 반주 생성
        midi_data.save('origin.mid')
 
        melody_path, accompaniment_path = separate_melody(midi_file=midi_data, midi_path=midi_file_path, resolution=resolution)    
        midi_path = accompaniment_path
    


    # preprocessing 라인 # 반주만 넣어주기
    ###########################################################################################

    # 4. encoding
=======
        midi_data = pretty_midi.PrettyMIDI(input_file_path)
    else:
        audio_file_path = make_audio_to_mp3(audio_path=input_file_path)
        tempo = extract_tempo(file_path=audio_file_path)
        key = extract_key(file_path=audio_file_path)

        model_output, midi_data, note_events = mp3_to_midi.pred(audio_path=audio_file_path, tempo=tempo)
        midi_file_path = f"{input_file_path.split('.')[0]}.mid"
        midi_data.write(midi_file_path)
        
        change_tempo(midi_path=midi_file_path, tempo=tempo)
        change_key_signature(midi_path=midi_file_path, key_signature=key)

        
        midi_data = mido.MidiFile(midi_file_path)
        # 2-1. tempo, key, beat 등등 정보 추가

    # 3. instrument 변경 (midi의 instrument 바꿔주기)
    processed_midi_data = change_instrument(instrument=input.instrument,
                                            midi_object=midi_data)

    # 4. 반주가 있는 경우는 반주 활용, 멜로디만 있는 경우는 멜로디 활용 반주 생성
    # if 반주?:
        # melody_path, accompaniment_path = separate_melody(midi_file_path)    
    # else:
        # make accompaniment
    
    ### 최종 저장
    midi_file_path = f"{input_file_path.split('.')[0]}_after.mid"
    processed_midi_data.write(midi_file_path)
    
    # preprocessing 라인 # 반주만 넣어주기
    ###########################################################################################

    # 4. condition / midi parsing
>>>>>>> acf6a3b79554c974d03c97b5e3ae8924912c0720
    conditional_track, condition_inst = parse_condition(input.instrument)
    content_track = parse_content(input.content_name)
    
    print("###############################################################")
    print("encoding start")
    x, tempo, not_empty_pos, condition_pos, pitch_shift, tpc, have_cond = F(midi_path, conditional_track, content_track, 
                                                                            condition_inst, args.chord_from_single, tokens_to_ids,
                                                                            ids_to_tokens, empty_index, pad_index)

    # 5. inference
    oct_line = solver.infer_sample(x, tempo, not_empty_pos, condition_pos, use_ema=args.no_ema)

    # 6. decoding
    data = oct_line.split(' ')
    oct_final_list = []
    for start in range(3, len(data),8):
        if 'pad' not in data[start] and 'pad' not in data[start+1]:
            pitch = int(data[start][:-1].split('-')[1])
            if data[start-1] != '<2-129>' and data[start-1] != '<2-128>':
                pitch -= pitch_shift
            data[start] = '<3-{}>'.format(pitch) # re-normalize            
            oct_final_list.append(' '.join(data[start-3:start+5]))
    oct_final = ' '.join(oct_final_list)
    
    midi_obj = encoding_to_MIDI(oct_final, tpc, args.decode_chord)

    # 7. storing files
    generated_midi_file_path = f"{input_file_path.split('.')[0]}_generated.mid"
    midi_obj.dump(generated_midi_file_path)

    s3_client = get_s3_client()
    folder_path = make_s3_folder(s3_client=s3_client, user=input.user)
<<<<<<< HEAD
=======
    # s3_url = upload_to_s3(local_file_name=midi_file_path_1,
    #                       key=f"{folder_path}{input_file_name.split('.')[0]}_origin_before.mid")
>>>>>>> acf6a3b79554c974d03c97b5e3ae8924912c0720
    s3_url = upload_to_s3(local_file_name=midi_file_path,
                          key=f"{folder_path}{input_file_name.split('.')[0]}_origin_after.mid")
    s3_url = upload_to_s3(local_file_name=generated_midi_file_path,
                          key=f"{folder_path}{input_file_name.split('.')[0]}_generated.mid")
<<<<<<< HEAD

    # 8. midi post processing
    ### 8-1. sync

    midi_data = mido.MidiFile(generated_midi_file_path, ticks_per_beat=resolution)
    midi_origin_data = mido.MidiFile(midi_file_path, ticks_per_beat=resolution)

    output_path = f"{input_file_path.split('.')[0]}_generated_sync.mid"
    midi_data = change_tempo_of_midi(mid=midi_data)
    midi_data.save(output_path)
    s3_url = upload_to_s3(local_file_name=output_path,
                          key=f"{folder_path}{input_file_name.split('.')[0]}_generated_sync.mid")
=======

    ####################################################################################################
    # 멜로디와 합쳐주기
    # 합쳐준 것 1개, 안 합친 것 1개
    # 결과물 velocity 조절하기


    # 8. midi post processing
    ### 8-1. sync
    output_path = f"{input_file_path.split('.')[0]}_generated_sync.mid"
    change_tempo_of_midi(original_file_path=midi_file_path, generated_file_path=generated_midi_file_path, output_path=output_path)
    s3_url = upload_to_s3(local_file_name=output_path,
                          key=f"{folder_path}{input_file_name.split('.')[0]}_generated_sync.mid")
    
    ### 8-2. remove the created
    file_path = generated_midi_file_path
    output_path = f"{input_file_path.split('.')[0]}_generated_sync_remove.mid"
    remove_instrument_events(file_path, input.instrument, output_path)
    s3_url = upload_to_s3(local_file_name=generated_midi_file_path,
                          key=f"{folder_path}{input_file_name.split('.')[0]}_fin.mid")
    
    ### 8-3. mp3 변환
    def convert_midi_to_mp3(input_midi, output_mp3):
        subprocess.run(['timidity', input_midi, '-Ow', '-o', 'output.wav'])
        subprocess.run(['lame', 'output.wav', output_mp3])
    
    output_path = f"{input_file_path.split('.')[0]}_generated_sync_remove_fin.mp3"
    convert_midi_to_mp3(generated_midi_file_path, output_path)
    s3_url = upload_to_s3(local_file_name=output_path,
                          key=f"{folder_path}{input_file_name.split('.')[0]}_generated.mp3")
>>>>>>> acf6a3b79554c974d03c97b5e3ae8924912c0720

    ### 8-3. mix with original
    output_path = f"{midi_file_path.split('.')[0]}_generated_sync_remove_fin.mid"
    midi_data_fin = modify_midi_velocity(midi_data)
    midi_data_fin.ticks_per_beat = resolution
    
    try:
        midi_data_origin.save('origin.mid')
    except Exception as e:
        midi_data_origin.write('origin.mid')
    midi_data_fin.save('generated.mid')
    midi_origin_data.save('origin_acc.mid')

    convert_midi_to_mp3('generated.mid', 'generated.mp3')
    convert_midi_to_mp3('origin.mid', 'origin.mp3')

    sound1 = AudioSegment.from_file("origin.mp3")
    sound2 = AudioSegment.from_file("generated.mp3")
    min_length = min(len(sound1), len(sound2))

    sound1 = sound1[:min_length]
    sound2 = sound2[:min_length]
    combined = sound1.overlay(sound2)
    combined.export("combined.mp3", format="mp3")
    random_no=generate_random_string(4)

    if check_file_exists('capstone-midi-generated', f"{folder_path}{input_file_name.split('.')[0]}_acc.mp3"):
        acc_name = f"{input_file_name.split('.')[0]}_acc_{random_no}.mp3"
        s3_acc_url = upload_to_s3(local_file_name="generated.mp3", key=f"{folder_path}{acc_name}")
    else:
        s3_acc_url = upload_to_s3(local_file_name="generated.mp3",
                                  key=f"{folder_path}{input_file_name.split('.')[0]}_acc.mp3")

    if check_file_exists('capstone-midi-generated', f"{folder_path}{input_file_name.split('.')[0]}_ai.mp3"):
        ai_name = f"{input_file_name.split('.')[0]}_ai_{random_no}.mp3"
        s3_ai_url = upload_to_s3(local_file_name="combined.mp3",
                                 key=f"{folder_path}{ai_name}")
    else:
        s3_ai_url = upload_to_s3(local_file_name="combined.mp3",
                                  key=f"{folder_path}{input_file_name.split('.')[0]}_ai.mp3")
    
    return {"status": "200", "url": s3_acc_url, "url2": s3_ai_url}