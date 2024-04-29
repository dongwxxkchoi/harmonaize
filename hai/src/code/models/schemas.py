from pydantic import BaseModel
from typing import List

# BasicPitch
class BasicPitchInputCreate(BaseModel):
    instrument: int
    file_path: str

# GETMusic
class GetMusicInput(BaseModel):
    file_path: str
    conditional_track: List[int]
    content_track: List[int]
