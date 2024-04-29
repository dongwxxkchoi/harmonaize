from fastapi import FastAPI, APIRouter, Response, HTTPException
from fastapi.responses import JSONResponse

import sys

from models.schemas import BasicPitchInputCreate, GetMusicInput
from models.music_models import WavToMIDIModel
from utils.utils import change_instrument, download_from_s3

router = APIRouter(default_response_class=JSONResponse)
model = WavToMIDIModel()

@router.post('/predict_basic_pitch/', tags=['basicpitch'])
def predict_basic_pitch(data: BasicPitchInputCreate) -> Response:
    ##### basic pitch 활용 부분 #####
    print("predicting basic_pitch")
    
    try:
        local_file_name = data.file_path
        key = f"hai/data/mp3/{data.file_path}.mp3"
        download_from_s3(bucket_name="temp_bucket",
                         local_file_name=local_file_name,
                         key=key)
    
        model_output, midi_data, note_events = model.pred(audio_path='key', parameters=[1])
    except Exception as e:
        # raise HTTPException(status_code=400, detail="Name and price are required")
        return {"status": "failure", "message": "aws file path wrong"}
    
    try:
        # instrument int와 mapping이 필요함
        processed_midi_data = change_instrument(instrument=data.instrument,
                                                midi_object=midi_data)

        processed_midi_data.write(f'target-{local_file_name}.mid')
        with open('target.mid', 'rb') as file:
            binary_midi_data = file.read()
    except Exception as e:
        return {"status": "failure", "message": "processing midi failed"}

    return {"status": "success", "message": "mp3 sended successfully"}


# 0 -> vocal
# 1 -> piano
# 2 -> guitar
# 3 -> bass
# 4 -> drum