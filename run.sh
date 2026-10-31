#!/bin/bash
set -e

# 1945: 天空狂怒 (Sky Fury 1945) 一鍵智慧啟動與測試腳本
# 自動偵測 GPU / CPU 環境、自動授權 X11 顯示

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 顯示幫助訊息
if [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
    echo "使用方式: ./run.sh [選項]"
    echo ""
    echo "選項:"
    echo "  --test        執行自動化測試驗證套件 (檢驗 4種戰機、5條命、十分之一扣血、20關卡)"
    echo "  --gpu         強制以 GPU 硬體加速模式啟動"
    echo "  --cpu         強制以 CPU 軟體渲染模式啟動"
    echo "  --stage <1-20> 指定初始關卡 (預設: 1)"
    echo "  --plane <0-3>  指定初始戰機 (預設: 0)"
    echo "  --build       重新建置 Docker 映像檔"
    exit 0
fi

# 測試模式
if [ "$1" == "--test" ]; then
    echo "=================================================="
    echo " 🚀 正在啟動 Docker 容器進行自動化測試驗證..."
    echo "=================================================="
    docker compose build test
    docker compose run --rm test
    exit $?
fi

# 檢查 X11 DISPLAY
if [ -z "$DISPLAY" ]; then
    export DISPLAY=":0"
fi

# 授權 Docker 容器存取主機 X11 顯示畫面
if command -v xhost >/dev/null 2>&1; then
    echo "正在設定 X11 顯示存取權限..."
    xhost +local:root >/dev/null 2>&1 || xhost + >/dev/null 2>&1 || true
fi

# 自動檢測 NVIDIA GPU 與 Container Toolkit 支援
HAS_GPU=false
if command -v nvidia-smi >/dev/null 2>&1; then
    if docker run --rm --gpus all nvidia/cuda:12.8.1-base-ubuntu24.04 nvidia-smi >/dev/null 2>&1; then
        HAS_GPU=true
    fi
fi

# 判定啟動模式
MODE="auto"
EXTRA_ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --gpu)
            MODE="gpu"
            shift
            ;;
        --cpu)
            MODE="cpu"
            shift
            ;;
        --build)
            echo "重新建置 Docker 映像檔..."
            docker compose build
            shift
            ;;
        --stage|--plane)
            EXTRA_ARGS+=("$1" "$2")
            shift 2
            ;;
        *)
            EXTRA_ARGS+=("$1")
            shift
            ;;
    esac
done

if [ "$MODE" == "gpu" ] || ( [ "$MODE" == "auto" ] && [ "$HAS_GPU" = true ] ); then
    echo "=================================================="
    echo " 🎮 檢測到 NVIDIA GPU！以 GPU 硬體加速模式啟動遊戲"
    echo "=================================================="
    docker compose run --rm --name sky-fury-game game-gpu "${EXTRA_ARGS[@]}"
else
    echo "=================================================="
    echo " 💻 以 CPU 軟體渲染模式 (Mesa llvmpipe) 啟動遊戲"
    echo "=================================================="
    docker compose run --rm --name sky-fury-game game-cpu "${EXTRA_ARGS[@]}"
fi
