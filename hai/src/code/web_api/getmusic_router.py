from argparse import Namespace

import miditoolkit
import os
import numpy as np
import datetime

from fastapi import FastAPI, Response, APIRouter
import torch

from models.track_generation import tokens_to_ids, ids_to_tokens, empty_index, pad_index
from models.track_generation import F, encoding_to_MIDI, parse_condition_inst, process_octuple_midi
from models.getmusic.utils.misc import seed_everything, merge_opts_to_config, modify_config_for_debug
from models.getmusic.engine.logger import Logger
from models.getmusic.engine.solver import Solver
from models.getmusic.modeling.build import build_model

from models.schemas import GetMusicInput
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


async def generate_music(data, solver):
    file_name = data.file_path
    conditional_track = data.conditional_track
    content_track = data.content_track

    download_res = download_from_s3(bucket_name='for-capstone-test', 
                                    local_file_name='piano.mid', 
                                    key=file_name)
    
    if not download_res:
        return False
    
    condition_inst = parse_condition_inst(conditional_track)
    file_name, conditional_track, content_track, condition_inst

    x, tempo, not_empty_pos, condition_pos, pitch_shift, tpc, have_cond = F(file_name, conditional_track, content_track, condition_inst, args.chord_from_single)
    
    if not have_cond:
        print('chord error')
        return 'chord error'

    # inference
    oct_line = solver.infer_sample(x, tempo, not_empty_pos, condition_pos, use_ema=args.no_ema)
    
    # process octuple midi
    oct_final = process_octuple_midi(oct_line, pitch_shift)
    midi_obj = encoding_to_MIDI(oct_final, tpc, args.decode_chord)
    midi_obj.save('output.mid')

    upload_res = upload_to_s3(bucket_name='for-capstone-test', 
                              local_file_name='output.mid', 
                              key='Viva_La_Vida_by_Coldplay.mid')

    if not upload_res:
        return False
    
    return upload_res


# initialize router
router = APIRouter()

# Load parameters and configuration
args = load_parameters()
config = load_yaml_config('configs/train.yaml')
config = merge_opts_to_config(config, args.opts)

# Initialize logger
logger = Logger(args)

# Initialize model and solver
solver = initialize_model_and_solver(args, config)

# Load tokens from file
vocab_file_path = config['solver']['vocab_path']
tokens_to_ids, ids_to_tokens = load_tokens_from_file(vocab_file_path)

# Get special indices
pad_index = get_pad_index(tokens_to_ids)
empty_index = get_empty_index(ids_to_tokens)

@router.post('/generate_music', tags=['getmusic'])
async def generate_music(data: GetMusicInput):
    return await generate_music(data, solver)

