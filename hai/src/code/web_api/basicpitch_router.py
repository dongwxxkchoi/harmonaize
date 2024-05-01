import sys
from typing import List, Union

from fastapi import FastAPI, APIRouter, Response, HTTPException
from fastapi.responses import JSONResponse

from models.schemas import BasicPitchInputCreate, GetMusicInput
from models.music_models import Mp3ToMIDIModel
from utils.utils import change_instrument, download_from_s3

router = APIRouter(default_response_class=JSONResponse)
model = Mp3ToMIDIModel()

# mp3 to midi
# mp3 s3 주소 주면, midi로 변환해서 s3에 저장하고 status와 함께 그 주소 반환하기
@router.post('/predict_basic_pitch/', tags=['basicpitch'])
async def predict_basic_pitch(data: BasicPitchInputCreate) -> Response:
    ##### basic pitch 활용 부분 #####
    print("predicting basic_pitch")
    
    try:
        url = data.file_path
        file_name = url.split('.')[0].split('https://')[1]
        key = f"hai/data/mp3/{data.file_path}.mp3" # key 맞춰봐야 함
        # bucket_name도 맞춰야 함
        download_from_s3(bucket_name="temp_bucket",
                         local_file_name=file_name,
                         key=key)
    
        model_output, midi_data, note_events = model.pred(audio_path='key', parameters=[1])
    except Exception as e:
        # raise HTTPException(status_code=400, detail="Name and price are required")
        return {"status": "failure", "message": "aws file path wrong"}
    
    try:
        # instrument int와 mapping이 필요함
        processed_midi_data = change_instrument(instrument=data.instrument,
                                                midi_object=midi_data)

        processed_midi_data.write(f'target-{file_name}.mid')
        with open('target.mid', 'rb') as file:
            binary_midi_data = file.read()
    except Exception as e:
        return {"status": "failure", "message": "processing midi failed"}

    # file_path도 저장할 예정
    return {"status": "success", "message": "mp3 sended successfully"}


# 0 -> vocal / 80
# 1 -> piano
# 2 -> guitar
# 3 -> bass
# 4 -> drum
# 다 80으로 해봤을 때 체크해봐야 함
