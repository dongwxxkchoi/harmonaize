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

from utils.utils import load_yaml_config, load_json_params, download_from_s3, upload_to_s3
from utils.utils import change_instrument, download_from_s3_requests, get_file_path_from_s3_url, make_and_get_user_folder

router = APIRouter()
mp3_to_midi = Mp3ToMIDIModel()



@router.post("/start_generation/")
async def start_generation(data: GenerationInput):
    mp3_file_name = get_file_path_from_s3_url(s3_url=data.s3_url)
    mp3_file_path = make_and_get_user_folder(file_name=mp3_file_name, user=data.user)    

    download_from_s3_requests(s3_url=data.s3_url,
                              local_file_path=mp3_file_path)
    
    model_output, midi_data, note_events = Mp3ToMIDIModel.pred(audio_path=mp3_file_path,
                                                               parameters=[])
    


    

    

    

class GenerationInput():
    s3_url: str
    user: str
    instrument: str
    content_name: str