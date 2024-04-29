from fastapi import FastAPI, APIRouter, Response
from fastapi.responses import JSONResponse

import sys

from models.schemas import BasicPitchInputCreate, GetMusicInput
from models.music_models import WavToMIDIModel
from utils.utils import change_instrument

router = APIRouter(default_response_class=JSONResponse)
model = WavToMIDIModel()

@router.post('/predict_basic_pitch/', tags=['basicpitch'])
def predict_basic_pitch(data: BasicPitchInputCreate) -> Response:
    ##### basic pitch 활용 부분 #####
    model_output, midi_data, note_events = model.pred(audio_path='data/guitar_1.mp3', 
                                                                  parameters=[1])
    processed_midi_data = change_instrument(instrument=data.instrument,
                                            midi_object=midi_data)
    
    processed_midi_data.write('target.mid')
    with open('target.mid', 'rb') as file:
        binary_midi_data = file.read()

    return Response(content=binary_midi_data, media_type="application/octet-stream")