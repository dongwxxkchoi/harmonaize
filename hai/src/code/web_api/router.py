import sys
import os
import datetime
import json
from typing import List, Union
from argparse import Namespace

import miditoolkit
import numpy as np

from fastapi import FastAPI, APIRouter, Response, HTTPException
from fastapi.responses import JSONResponse
import torch

from models.schemas import BasicPitchInputCreate, GetMusicInput, GetMusicOutput, GenerationInput
from models.music_models import Mp3ToMIDIModel

from models.track_generation import tokens_to_ids, ids_to_tokens, empty_index, pad_index
from models.track_generation import F, encoding_to_MIDI, parse_condition, parse_content, process_octuple_midi
from models.getmusic.utils.misc import seed_everything, merge_opts_to_config, modify_config_for_debug
from models.getmusic.engine.logger import Logger
from models.getmusic.engine.solver import Solver
from models.getmusic.modeling.build import build_model
from models.initializing import initialize

from utils.utils import load_yaml_config, load_json_params, download_from_s3, upload_to_s3
from utils.utils import change_instrument, download_from_s3_requests, get_file_path_from_s3_url, make_and_get_user_folder, make_and_get_user_folder_path

router = APIRouter()
mp3_to_midi = Mp3ToMIDIModel()
args, Logger, solver, pad_index, empty_index = initialize()


@router.post("/start_generation/")
async def start_generation(data: GenerationInput):
    mp3_file_name = get_file_path_from_s3_url(s3_url=data.s3_url)
    mp3_file_path = make_and_get_user_folder(file_name=mp3_file_name, user=data.user)    

    download_from_s3_requests(s3_url=data.s3_url,
                              local_file_path=mp3_file_path)
    
    Mp3ToMIDIModel.pred_and_save(audio_path=mp3_file_path,
                                 output_directory=make_and_get_user_folder_path(user=data.user))

    # Generate Music - preprocessing
    conditional_track, condition_inst = parse_condition(data.instrument)
    content_track = parse_content(data.content_name)
    x, tempo, not_empty_pos, condition_pos, pitch_shift, tpc, have_cond = F(mp3_file_name, conditional_track, content_track, condition_inst, args.chord_from_single)

    # Generate Music - inference
    oct_line = solver.infer_sample(x, tempo, not_empty_pos, condition_pos, use_ema=args.no_ema)

    # Generate Music - post processing
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
    os.path.join(make_and_get_user_folder_path(user=data.user), mp3_file_name.split('.')[0])
    midi_obj.dump()
    save_path = os.path.join(args.file_path, '{}2{}-{}'.format(conditional_name, content_name, file_name.split('/')[-1]))
    midi_obj.dump(save_path)
    

    

    

class GenerationInput():
    s3_url: str
    user: str
    instrument: str
    content_name: str