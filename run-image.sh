#!/bin/bash
set -e

# 1942: 天空狂怒 (Sky Fury 1942) - 純 Docker 映像檔直接啟動腳本
# 100% 獨立運行，無需本地源代碼，開箱即玩！

IMAGE_NAME="sky-fury-1942:latest"
TAR_FILE="sky-fury-1942-latest.tar.gz"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 檢查映像檔是否存在，若無但有 tar.gz 則自動載入
if ! docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
    if [ -f "$SCRIPT_DIR/$TAR_FILE" ]; then
        echo "正在從 $TAR_FILE 載入 Docker 映像檔..."
        docker load -i "$SCRIPT_DIR/$TAR_FILE"
    else
        echo "❌ 錯誤：未找到 Docker 映像檔 $IMAGE_NAME 且不存在 $TAR_FILE"
        exit 1
    fi
fi

# X11 顯示權限
if [ -z "$DISPLAY" ]; then
    export DISPLAY=":0"
fi
if command -v xhost >/dev/null 2>&1; then
    xhost +local:root >/dev/null 2>&1 || true
fi

# 測試模式
if [ "$1" == "--test" ]; then
    echo "=================================================="
    echo " 🚀 正在直接由 Docker 映像檔執行自動化測試驗證..."
    echo "=================================================="
    docker run --rm --entrypoint python3 "$IMAGE_NAME" /app/test_game.py
    exit $?
fi

# GPU 偵測
GPU_FLAGS=()
if command -v nvidia-smi >/dev/null 2>&1; then
    if docker run --rm --gpus all nvidia/cuda:12.8.1-base-ubuntu24.04 nvidia-smi >/dev/null 2>&1; then
        echo "🎮 偵測到 NVIDIA GPU 硬體加速！"
        GPU_FLAGS=(--gpus all)
    fi
fi

# 啟動遊戲
echo "=================================================="
echo " 🚀 正在直接由 Docker 映像檔 ($IMAGE_NAME) 啟動遊戲..."
echo "=================================================="

docker run --rm -it \
    "${GPU_FLAGS[@]}" \
    -e DISPLAY="$DISPLAY" \
    -e XAUTHORITY="$XAUTHORITY" \
    -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
    -v /dev/dri:/dev/dri \
    -v /dev/snd:/dev/snd \
    -v /dev/shm:/dev/shm \
    --ipc=host \
    --network=host \
    "$IMAGE_NAME" "$@"
