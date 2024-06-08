FROM python:3.9-slim

# 작업 디렉토리 설정
WORKDIR /app

# 필요한 파일 복사
COPY . /app



RUN apt-get update && apt-get install ffmpeg 
RUN pip install -U pip &&\
    pip install basic-pitch  && \
    pip install uvicorn fastapi pyyaml boto3 pretty_midi miditoolkit tensorboard tqdm transformers einops mido && \
    pip install pydub librosa  && \    
    pip install torch --index-url https://download.pytorch.org/whl/cu118

ENTRYPOINT ["uvicorn", "hai.src.code.bin.app:app", "--host", "0.0.0.0", "--port", "8080"]
