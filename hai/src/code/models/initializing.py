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

def initialize():
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

    return args, Logger, solver, tokens_to_ids, ids_to_tokens, pad_index, empty_index