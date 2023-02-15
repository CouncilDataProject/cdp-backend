FROM iterativeai/cml:0-dvc2-base1-gpu

# Install updates and OS deps
RUN apt update \
    && apt upgrade -y \
    && apt install -y --no-install-recommends \
    libsndfile1 \
    ffmpeg \
    && add-apt-repository -y ppa:deadsnakes/ppa \
    && apt install python3.10 -y

# Install deps
RUN python3 -m pip install --upgrade pip setuptools wheel
RUN pip3 install --no-cache-dir --pre cdp-backend[pipeline]
RUN pip3 install --no-cache-dir 'faster-whisper @ git+https://github.com/guillaumekln/faster-whisper.git'

# Build fast whisper model
# Set working dir
WORKDIR fast-whisper-models/
RUN ct2-transformers-converter --model openai/whisper-medium --output_dir whisper-medium-ct2 --quantization float16