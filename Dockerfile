# 1945: 二戰空間（II War Space）
# 支援 Ubuntu 26.04 與 24.04，相容 GPU (NVIDIA OpenGL 硬體加速) 與 無 GPU (Mesa CPU 軟體渲染)
FROM nvidia/cuda:12.8.1-base-ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_BREAK_SYSTEM_PACKAGES=1 \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=all \
    SDL_VIDEODRIVER=x11

# 安裝 Python3、Pygame、NumPy、SDL2、現代 OpenGL (GLVND)、Mesa、音效、繁中/簡中開源字體與 X11
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-numpy \
        python3-pygame \
        fonts-wqy-microhei \
        fonts-wqy-zenhei \
        libgl1-mesa-dri \
        libglx-mesa0 \
        libglvnd0 \
        libgl1 \
        libglx0 \
        libegl1 \
        libgles2 \
        mesa-utils \
        libasound2t64 \
        libpulse0 \
        x11-utils \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 複製依賴與專案代碼
COPY requirements.txt /app/
RUN pip3 install --no-cache-dir -r requirements.txt || true

COPY . /app/

# 預設執行遊戲主程式
ENTRYPOINT ["python3", "-m", "game.main"]
