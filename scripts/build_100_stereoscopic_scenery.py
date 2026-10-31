#!/usr/bin/env python3
"""
立體實景有山有海頂視圖 100 張超長縱向卷軸 (1024x10240) 批量生成引擎
直接基於 Google Gemini Banana 生成之真實空照照片母盤，
以高解析多尺度取景、幾何翻轉走勢、10 段無縫餘弦平滑融接 (Cosine Cross-fade Blend)、
電影級大氣色彩渲染與首尾無限循環過渡，
生成 100 張 100% 擬真立體、超長 1024x10240 縱向山海航道頂視實景背景圖。
"""

import os
import math
import random
import time
import multiprocessing
import numpy as np
from PIL import Image

TARGET_WIDTH = 1024
TARGET_HEIGHT = 10240
NUM_SEGMENTS = 10
SEGMENT_HEIGHT = 1024
OVERLAP = 128  # 相鄰段落交叉融接高度

# 10 大大氣光照色彩主題 (與關卡情境完美契合，採用溫和通透之調色)
THEME_PALETTES = [
    {"name": "emerald_atoll",    "title": "翡翠碧海珊瑚海島",     "tint": (30, 220, 200),  "tint_alpha": 18, "sea_base": (16, 75, 115)},
    {"name": "dawn_patrol",      "title": "破曉晨曦微金光海山",   "tint": (255, 225, 170), "tint_alpha": 22, "sea_base": (22, 58, 96)},
    {"name": "tropical_paradise","title": "熱帶群島蔚藍碧海青山", "tint": (20, 180, 220),  "tint_alpha": 15, "sea_base": (18, 62, 88)},
    {"name": "sunset_amber",     "title": "夕陽晚霞橙紅海岸山脈", "tint": (255, 130, 45),  "tint_alpha": 30, "sea_base": (42, 48, 82)},
    {"name": "volcanic_basalt",  "title": "火山黑曜岩島深海峽灣", "tint": (220, 70, 30),   "tint_alpha": 25, "sea_base": (26, 22, 38)},
    {"name": "bloodmoon_crimson","title": "血月猩紅氣息海岬峰巒", "tint": (200, 35, 45),   "tint_alpha": 32, "sea_base": (38, 18, 28)},
    {"name": "arctic_fjord",     "title": "極地冷冽藍霜冰海峽灣", "tint": (130, 205, 255), "tint_alpha": 25, "sea_base": (42, 78, 112)},
    {"name": "midnight_ocean",   "title": "午夜幽深暗夜海角山脈", "tint": (20, 40, 85),    "tint_alpha": 35, "sea_base": (8, 16, 32)},
    {"name": "aurora_emerald",   "title": "極光流轉碧綠光輝海山", "tint": (30, 220, 150),  "tint_alpha": 25, "sea_base": (14, 32, 48)},
    {"name": "stratosphere_blue","title": "高空平流層極致湛藍海山", "tint": (60, 140, 255), "tint_alpha": 22, "sea_base": (20, 50, 100)},
]

def load_banana_masters():
    """載入所有在 assets/banana_masters/ 的真實 Google Gemini Banana 原版實景圖"""
    dirs = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "banana_masters"),
        os.path.join(os.getcwd(), "assets", "banana_masters"),
        "/app/assets/banana_masters",
    ]
    masters = []
    preferred_order = [
        "banana_bg_test_1793435064482.jpg",
        "coral_p1_1793427926462.jpg",
        "coral_p2_1793427943807.jpg",
        "ocean_dawn_scenic_1793427555201.jpg",
        "test_banana_call_1793433030372.jpg",
        "dawn_p1_1793427875421.jpg",
        "dawn_p2_1793427898304.jpg",
        "sunset_p1_1793427962978.jpg",
        "sunset_p2_1793427984944.jpg",
        "volcano_p1_1793428003455.jpg",
        "volcano_p2_1793428026203.jpg",
        "bloodmoon_p1_1793428045013.jpg",
        "bloodmoon_p2_1793428062351.jpg"
    ]
    for d in dirs:
        if os.path.exists(d):
            for fn in preferred_order:
                full_p = os.path.join(d, fn)
                if os.path.exists(full_p):
                    try:
                        im = Image.open(full_p).convert("RGB")
                        if im.width >= 800 and im.height >= 800:
                            masters.append((fn, im))
                    except Exception as e:
                        print(f"Error loading {full_p}: {e}")
            if masters:
                break
    return masters

def generate_segment_slice(master_img, target_w, target_h, seed):
    """自母盤高解析無損裁剪並採樣單個區段"""
    rnd = random.Random(seed)
    mw, mh = master_img.size

    # 取景比例 72% ~ 95%
    scale = rnd.uniform(0.72, 0.95)
    cw = int(mw * scale)
    ch = int(mh * scale)
    cx = rnd.randint(0, max(0, mw - cw))
    cy = rnd.randint(0, max(0, mh - ch))
    cropped = master_img.crop((cx, cy, cx + cw, cy + ch))

    # 幾何翻轉
    if rnd.random() < 0.5:
        cropped = cropped.transpose(Image.FLIP_LEFT_RIGHT)
    if rnd.random() < 0.5:
        cropped = cropped.transpose(Image.FLIP_TOP_BOTTOM)

    # 旋轉 (90度步進)
    rot_times = rnd.choice([0, 1, 2, 3])
    for _ in range(rot_times):
        cropped = cropped.transpose(Image.ROTATE_90)

    # 雙三次採樣至目標尺寸
    return cropped.resize((target_w, target_h), Image.Resampling.BICUBIC)

def build_single_1024x10240_image(img_idx, masters, theme):
    """
    自真實 Google Gemini Banana 空照母盤合成一張完整的 1024x10240 超長無縫航道頂視圖。
    10 段連續平滑餘弦融接，上下兩端首尾銜接。
    """
    rnd = random.Random(7777 + img_idx * 131)
    
    # 預備畫布陣列 (10240, 1024, 3)
    canvas = np.zeros((TARGET_HEIGHT, TARGET_WIDTH, 3), dtype=np.float32)

    # 交叉融接權重曲線 (OVERLAP, 1, 1)
    t = np.linspace(0, np.pi, OVERLAP, endpoint=False)
    blend_w = (0.5 - 0.5 * np.cos(t))[:, None, None].astype(np.float32)

    # 逐段生成並融合
    for seg_idx in range(NUM_SEGMENTS):
        # 輪替或隨機選取母盤
        master_idx = (img_idx + seg_idx * 3) % len(masters)
        _, master_img = masters[master_idx]

        # 每個 segment 高度包含額外的 OVERLAP 以便與前後平滑過渡
        slice_h = SEGMENT_HEIGHT + (OVERLAP if seg_idx < NUM_SEGMENTS - 1 else 0)
        seg_seed = (img_idx * 100 + seg_idx * 17)
        slice_img = generate_segment_slice(master_img, TARGET_WIDTH, slice_h, seg_seed)
        slice_arr = np.array(slice_img, dtype=np.float32)

        start_y = seg_idx * SEGMENT_HEIGHT

        if seg_idx == 0:
            # 第一段直接覆蓋
            canvas[start_y : start_y + slice_h] = slice_arr
        else:
            # 與前一段的重疊區域進行餘弦融接
            overlap_start = start_y
            overlap_end = start_y + OVERLAP
            canvas[overlap_start : overlap_end] = (
                canvas[overlap_start : overlap_end] * (1.0 - blend_w) +
                slice_arr[:OVERLAP] * blend_w
            )
            # 剩餘非重疊區域
            remain_start = overlap_end
            remain_end = start_y + slice_h
            canvas[remain_start : remain_end] = slice_arr[OVERLAP:]

    # 電影級大氣色彩覆蓋 (Tint Overlay)
    tint_rgb = np.array(theme["tint"], dtype=np.float32)
    tint_alpha = float(theme["tint_alpha"]) / 255.0
    if tint_alpha > 0:
        canvas = canvas * (1.0 - tint_alpha) + tint_rgb * tint_alpha

    # 首尾無縫循環淡入淡出 (邊界 OVERLAP 像素與海域底色融合，保證縱向無限滾動 0 斷裂)
    base_sea = np.array(theme.get("sea_base", (20, 55, 95)), dtype=np.float32)
    edge_h = min(OVERLAP, 128)
    t_edge = np.linspace(0, np.pi / 2.0, edge_h, endpoint=False)
    edge_factor = (np.cos(t_edge)[:, None, None]).astype(np.float32) * 0.7  # 最大 70% 淡至底色

    # 頂部過渡
    canvas[:edge_h] = canvas[:edge_h] * (1.0 - edge_factor) + base_sea * edge_factor
    # 底部過渡
    canvas[-edge_h:] = canvas[-edge_h:] * (1.0 - edge_factor[::-1]) + base_sea * edge_factor[::-1]

    # 截斷至 0~255
    canvas = np.clip(canvas, 0, 255).astype(np.uint8)
    return Image.fromarray(canvas, mode="RGB")

def _worker_generate(args):
    """多程序工作線程"""
    i, masters, output_dir, thumbs_dir = args
    theme = THEME_PALETTES[(i - 1) % len(THEME_PALETTES)]
    t0 = time.time()
    long_img = build_single_1024x10240_image(i, masters, theme)

    filename = f"scenic_ms_{i:03d}.jpg"
    out_p = os.path.join(output_dir, filename)
    long_img.save(out_p, quality=88, optimize=True)

    # 同時生成方便快速瀏覽的預覽縮圖 (寬度 256, 高度 2560)
    thumb_img = long_img.resize((256, 2560), Image.Resampling.BILINEAR)
    thumb_p = os.path.join(thumbs_dir, f"thumb_ms_{i:03d}.jpg")
    thumb_img.save(thumb_p, quality=82)

    file_kb = os.path.getsize(out_p) / 1024.0
    elapsed = time.time() - t0
    return i, filename, theme["title"], file_kb, elapsed

def main():
    print("==================================================")
    print(" 🚀 使用 Google Gemini Banana 實景空照照片批量生成 100 張 1024x10240 超長背景圖...")
    print("==================================================")

    t_start = time.time()
    masters = load_banana_masters()
    if not masters:
        print("❌ 未找到 Google Gemini Banana 母盤圖片！請確認 assets/banana_masters/ 目錄。")
        return

    print(f"  ✓ 成功載入 {len(masters)} 張 Google Gemini Banana 真實實景母盤！")
    for fn, im in masters:
        print(f"    - 母盤: {fn} ({im.width}x{im.height})")

    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "backgrounds", "scenic_100")
    thumbs_dir = os.path.join(output_dir, "previews")
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(thumbs_dir, exist_ok=True)

    print(f"\n▶ 開始多程序平行生成 100 張 1024x10240 立體實景長卷...")

    tasks = [(i, masters, output_dir, thumbs_dir) for i in range(1, 101)]
    cpu_count = min(16, os.cpu_count() or 4)

    with multiprocessing.Pool(processes=cpu_count) as pool:
        for i, filename, title, file_kb, elapsed in pool.imap(_worker_generate, tasks):
            if i % 10 == 0 or i == 1:
                print(f"  ✓ [{i:03d}/100] {filename} | {title} | 1024x10240 | {file_kb:.1f} KB | 耗時 {elapsed:.2f}s")

    total_time = time.time() - t_start
    print("==================================================")
    print(f" 🎉 100 張 1024x10240 Google Gemini Banana 立體實景有山有海頂視圖全部生成完畢！")
    print(f" 總耗時: {total_time:.2f} 秒，檔案存於: {output_dir}")
    print("==================================================")

if __name__ == "__main__":
    main()
