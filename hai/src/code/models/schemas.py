from pydantic import BaseModel
from typing import List

class GenerationInput(BaseModel):
    s3_url: str
    user: str
    instrument: str
    content_name: str


# BasicPitch
class BasicPitchInputCreate(BaseModel):
    file_path: str
    instrument: str


# GETMusic
class GetMusicInput(BaseModel):
    conditional_name: str
    content_name: str

# GETMusic
class GetMusicOutput(BaseModel):
    file_path: str