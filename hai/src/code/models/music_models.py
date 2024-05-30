import asyncio

from basic_pitch.inference import predict, predict_and_save, Model
from basic_pitch import ICASSP_2022_MODEL_PATH
from typing import List

class Mp3ToMIDIModel:
    def __init__(self):
        self.model = Model(model_path = ICASSP_2022_MODEL_PATH)
    
    def pred(self, audio_path: str, parameters: List[float]):
        model_output, midi_data, note_events = predict(
            audio_path=audio_path,
            model_or_model_path=self.model,
            onset_threshold=0.7,
            frame_threshold=0.5,
            minimum_note_length=150
        )

        return model_output, midi_data, note_events
    
    def pred_and_save(self, audio_path: str, output_directory: str, parameters: List[float]=None):
        predict_and_save(
            audio_path_list=[audio_path],
            output_directory=output_directory,
            save_midi=True,
            sonify_midi=False,
            save_model_outputs=False,
            save_notes=False,
            model_or_model_path=self.model,
            onset_threshold=0.25,
            frame_threshold=0.25,
            minimum_note_length=70
        )