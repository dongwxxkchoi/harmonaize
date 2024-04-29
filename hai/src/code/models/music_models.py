import asyncio

from basic_pitch.inference import predict, Model
from basic_pitch import ICASSP_2022_MODEL_PATH
from typing import List

class WavToMIDIModel:
    def __init__(self):
        self.model = Model(model_path = ICASSP_2022_MODEL_PATH)
    
    def pred(self, audio_path: str, parameters: List[float]):        
        model_output, midi_data, note_events = predict(
            audio_path=audio_path,
            model_or_model_path=self.model,
            onset_threshold=0.25,
            frame_threshold=0.25,
            minimum_note_length=70
        )

        return model_output, midi_data, note_events
    