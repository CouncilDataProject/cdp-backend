FROM iterativeai/cml:0-dvc2-base1-gpu

# Install updates and OS deps
RUN apt update && apt install -y --no-install-recommends \
    libsndfile1 \
    ffmpeg

# Set working dir
WORKDIR cdp-backend/
COPY ./cdp_backend/tests/resources/example_audio.wav .

# Install deps
RUN python3 -m pip install --upgrade pip setuptools wheel
RUN pip3 install --no-cache-dir 'cdp-backend[pipeline]>=v4.0.0.rc7'

# Install faster whisper
RUN pip3 install --no-cache-dir faster-whisper@git+https://github.com/guillaumekln/faster-whisper.git

# Build fast whisper model
RUN ct2-transformers-converter --model openai/whisper-medium --output_dir whisper-medium-ct2 --quantization float16

# COPY TEST FILES
COPY ./test-faster-whisper.py .
COPY ./test-normal-whisper.py .