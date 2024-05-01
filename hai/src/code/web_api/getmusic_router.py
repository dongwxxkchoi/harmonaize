from argparse import Namespace

import miditoolkit
import os
import numpy as np
import datetime
import json

from fastapi import FastAPI, Response, APIRouter
import torch

from models.track_generation import tokens_to_ids, ids_to_tokens, empty_index, pad_index
from models.track_generation import F, encoding_to_MIDI, parse_condition, parse_content, process_octuple_midi
from models.getmusic.utils.misc import seed_everything, merge_opts_to_config, modify_config_for_debug
from models.getmusic.engine.logger import Logger
from models.getmusic.engine.solver import Solver
from models.getmusic.modeling.build import build_model

from models.schemas import GetMusicInput, GetMusicOutput
from utils.utils import load_yaml_config, load_json_params, download_from_s3, upload_to_s3

# Load parameters
def load_parameters():
    params = load_json_params('configs/params.json')
    args = Namespace(**params)

    args.cwd = os.path.abspath(os.path.dirname(__file__))

    seed = args.seed
    os.environ['PYTHONHASHSEED'] = str(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)

    if args.name == '':
        args.name = os.path.basename(args.config_file).replace('.yaml', '')

    random_seconds_shift = datetime.timedelta(seconds=np.random.randint(60))
    now = (datetime.datetime.now() - random_seconds_shift).strftime('%Y-%m-%dT%H-%M-%S')
    args.save_dir = os.path.join(args.output, args.name, now)

    seed_everything(args.seed, args.cudnn_deterministic)
    device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
    torch.cuda.set_device(device)
    args.local_rank = 0
    args.ngpus_per_node = args.world_size = args.local_rank = args.node_rank = 1
    args.global_rank = args.local_rank + args.node_rank * args.ngpus_per_node
    args.distributed = args.world_size > 1
    return args

# Initialize logger
def initialize_logger(args):
    return Logger(args)

# Initialize model and solver
def initialize_model_and_solver(args, config):
    model = build_model(config, args)
    logger = Logger(args)
    solver = Solver(config=config, args=args, model=model, dataloader=None, logger=logger, is_sample=True)
    assert args.load_path is not None
    solver.resume(path=args.load_path) # resume model
    return solver

def load_tokens_from_file(file_path):
    tokens_to_ids = {}
    ids_to_tokens = []

    with open(file_path, 'r') as f:
        lines = f.readlines()

        for id, line in enumerate(lines):
            token, freq = line.strip().split('\t')
            tokens_to_ids[token] = id
            ids_to_tokens.append(token)

    return tokens_to_ids, ids_to_tokens

def get_pad_index(tokens_to_ids):
    return tokens_to_ids.get('<pad>')

def get_empty_index(ids_to_tokens):
    return len(ids_to_tokens)

# Load parameters and configuration
args = load_parameters()
config = load_yaml_config('configs/train.yaml')
config = merge_opts_to_config(config, args.opts)

# Initialize logger
Logger = initialize_logger(args)

# Initialize model and solver
solver = initialize_model_and_solver(args, config)

# Load tokens from file
vocab_file_path = config['solver']['vocab_path']
tokens_to_ids, ids_to_tokens = load_tokens_from_file(vocab_file_path)

# Get special indices
pad_index = get_pad_index(tokens_to_ids)
empty_index = get_empty_index(ids_to_tokens)


# initialize and load model on memory
######################################################################

# initialize router
router = APIRouter()

# 다시 backend에서 해당 주소 받기
@router.post('/generate_music', tags=['getmusic'])
async def generate_music(data: GetMusicInput):
    url = data.file_path 
    file_name = url.split('.')[0].split('https://')[1]
    conditional_name = data.conditional_name # 지금 조건
    content_name = data.content_name # 생성할 content
    
    # bucket name은 환경변수? 아니면 어차피 지정되어 있으니 넣어줄까
    # local_file_name은 받은걸로
    try:
        download_res = download_from_s3(bucket_name='for-capstone-test', 
                                        key=file_name,
                                        local_file_name="규칙에맞게.mid")
    
    except Exception as e:
        pass

    # preprocessing
    conditional_track, condition_inst = parse_condition(conditional_name)
    content_track = parse_content(content_name)
    x, tempo, not_empty_pos, condition_pos, pitch_shift, tpc, have_cond = F(file_name, conditional_track, content_track, condition_inst, args.chord_from_single)

    # inference
    oct_line = solver.infer_sample(x, tempo, not_empty_pos, condition_pos, use_ema=args.no_ema)

    # post processing
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
    save_path = os.path.join(args.file_path, '{}2{}-{}'.format(conditional_name, content_name, file_name.split('/')[-1]))
    midi_obj.dump(save_path)

    return GetMusicOutput(file_path = save_path)

