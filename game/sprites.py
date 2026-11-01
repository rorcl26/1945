"""
1945: 二戰空間（II War Space）
精靈圖形模組 (Sprites & Visual Assets)
高品質程序化繪製：包含 4 款玩家戰機（支援左傾/右傾/翻轉）、各式敵機、20 關巨型 BOSS、戰利品寶物與特效
"""

import math
import pygame
from game.config import (
    COLOR_WHITE, COLOR_BLACK, COLOR_RED, COLOR_GREEN, COLOR_BLUE,
    COLOR_YELLOW, COLOR_ORANGE, COLOR_PURPLE, COLOR_CYAN, COLOR_GOLD,
    COLOR_SHIELD, COLOR_SHIELD_BORDER
)

class SpriteCache:
    """快取預先繪製好的高解析度 Surface，以確保 60 FPS 流暢度與 GPU/CPU 高效能"""
    _cache = {}

    @classmethod
    def get(cls, key):
        return cls._cache.get(key)

    @classmethod
    def set(cls, key, surf):
        cls._cache[key] = surf
        return surf


def draw_propeller(surf, center, radius, angle, color=(220, 240, 255)):
    """繪製動態旋轉螺旋槳效果"""
    cx, cy = center
    # 兩葉或三葉半透明高速旋轉弧光
    blade_len = radius
    for i in range(3):
        rad = math.radians(angle + i * 120)
        ex = cx + blade_len * math.cos(rad)
        ey = cy + blade_len * math.sin(rad)
        pygame.draw.line(surf, color, (cx, cy), (int(ex), int(ey)), 2)
    # 旋轉光暈圓環
    pygame.draw.circle(surf, (200, 230, 255, 60), (int(cx), int(cy)), int(radius), 1)
    pygame.draw.circle(surf, (80, 80, 80), (int(cx), int(cy)), 3)


def create_player_sprite(fighter_id, bank_state="center", frame=0):
    """
    建立主戰機圖形
    bank_state: 'center', 'left', 'right'
    """
    key = f"player_{fighter_id}_{bank_state}_{frame % 8}"
    cached = SpriteCache.get(key)
    if cached:
        return cached

    # 基礎尺寸
    w, h = 64, 64
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    cx, cy = w // 2, h // 2

    prop_angle = (frame * 45) % 360
    tilt_offset = -4 if bank_state == "left" else (4 if bank_state == "right" else 0)
    wing_scale = 0.85 if bank_state != "center" else 1.0

    if fighter_id == "p38_lightning":
        # P-38 閃電號：雙機身 (Twin Boom) 經典雙發攔截機
        body_color = (130, 150, 175)
        dark_metal = (90, 110, 130)
        yellow_trim = (255, 215, 0)

        # 雙尾樑 (左右兩側機身)
        for offset_x in [-18, 18]:
            bx = cx + offset_x + tilt_offset
            # 發動機艙與尾部
            pygame.draw.rect(surf, dark_metal, (bx - 4, cy - 14, 8, 38), border_radius=3)
            pygame.draw.rect(surf, body_color, (bx - 3, cy - 12, 6, 34), border_radius=2)
            # 兩側螺旋槳
            draw_propeller(surf, (bx, cy - 16), 11, prop_angle)
            # 垂直尾翼
            pygame.draw.polygon(surf, yellow_trim, [(bx - 3, cy + 22), (bx + 3, cy + 22), (bx, cy + 28)])

        # 主機翼 (橫貫雙機身)
        wing_span = int(28 * wing_scale)
        pygame.draw.polygon(surf, body_color, [
            (cx - wing_span + tilt_offset, cy + 2),
            (cx + wing_span + tilt_offset, cy + 2),
            (cx + wing_span - 4 + tilt_offset, cy - 5),
            (cx - wing_span + 4 + tilt_offset, cy - 5)
        ])
        # 機翼黃色識別邊緣
        pygame.draw.line(surf, yellow_trim, (cx - wing_span + tilt_offset, cy), (cx - wing_span + 6 + tilt_offset, cy), 2)
        pygame.draw.line(surf, yellow_trim, (cx + wing_span + tilt_offset, cy), (cx + wing_span - 6 + tilt_offset, cy), 2)

        # 水平尾翼
        pygame.draw.rect(surf, dark_metal, (cx - 18 + tilt_offset, cy + 22, 36, 4))

        # 中央座艙與機砲艙
        pygame.draw.ellipse(surf, body_color, (cx - 7 + tilt_offset, cy - 18, 14, 30))
        # 玻璃座艙
        pygame.draw.ellipse(surf, (100, 220, 255), (cx - 4 + tilt_offset, cy - 10, 8, 14))
        pygame.draw.ellipse(surf, COLOR_WHITE, (cx - 2 + tilt_offset, cy - 9, 3, 5))
        # 4聯裝機鼻機砲口
        for gx in [-3, -1, 1, 3]:
            pygame.draw.line(surf, (40, 40, 40), (cx + gx + tilt_offset, cy - 18), (cx + gx + tilt_offset, cy - 22), 2)

    elif fighter_id == "f4u_corsair":
        # F4U 海盜號：深藍海軍折翼機 (Bent Wing) 重型裝甲
        navy_blue = (25, 45, 110)
        light_blue = (50, 90, 180)
        metal = (200, 210, 225)

        # 巨大的折翼機翼
        ws = int(30 * wing_scale)
        pts = [
            (cx - ws + tilt_offset, cy + 6),
            (cx - 14 + tilt_offset, cy + 1),
            (cx + 14 + tilt_offset, cy + 1),
            (cx + ws + tilt_offset, cy + 6),
            (cx + ws - 4 + tilt_offset, cy - 3),
            (cx + 12 + tilt_offset, cy - 5),
            (cx - 12 + tilt_offset, cy - 5),
            (cx - ws + 4 + tilt_offset, cy - 3)
        ]
        pygame.draw.polygon(surf, navy_blue, pts)
        # 白色海軍軍徽星星
        pygame.draw.circle(surf, COLOR_WHITE, (cx - 20 + tilt_offset, cy), 4)
        pygame.draw.circle(surf, COLOR_WHITE, (cx + 20 + tilt_offset, cy), 4)

        # 粗壯圓筒形機身
        pygame.draw.ellipse(surf, navy_blue, (cx - 9 + tilt_offset, cy - 22, 18, 44))
        pygame.draw.ellipse(surf, light_blue, (cx - 6 + tilt_offset, cy - 18, 12, 36))
        # 巨大單發前置螺旋槳
        draw_propeller(surf, (cx + tilt_offset, cy - 22), 16, prop_angle)
        # 大型水泡座艙
        pygame.draw.ellipse(surf, (80, 200, 255), (cx - 4 + tilt_offset, cy - 8, 8, 14))
        pygame.draw.ellipse(surf, COLOR_WHITE, (cx - 2 + tilt_offset, cy - 7, 3, 5))
        # 翼砲 (左右各三門 12.7mm 機槍)
        for ox in [-22, -18, -14, 14, 18, 22]:
            pygame.draw.line(surf, metal, (cx + ox + tilt_offset, cy - 3), (cx + ox + tilt_offset, cy - 8), 2)
        # 尾翼
        pygame.draw.polygon(surf, navy_blue, [(cx - 14 + tilt_offset, cy + 20), (cx + 14 + tilt_offset, cy + 20), (cx + tilt_offset, cy + 26)])

    elif fighter_id == "bf109_falcon":
        # BF-109 獵鷹號：銳利流線空優機
        camo_green = (75, 105, 75)
        camo_light = (115, 145, 100)
        yellow_nose = (255, 215, 20)

        # 銳角機翼
        ws = int(27 * wing_scale)
        pygame.draw.polygon(surf, camo_green, [
            (cx - ws + tilt_offset, cy + 4),
            (cx + ws + tilt_offset, cy + 4),
            (cx + ws - 6 + tilt_offset, cy - 6),
            (cx - ws + 6 + tilt_offset, cy - 6)
        ])
        # 兩翼下掛微型追蹤火箭巢
        pygame.draw.rect(surf, (60, 60, 60), (cx - 22 + tilt_offset, cy - 2, 5, 10), border_radius=2)
        pygame.draw.rect(surf, (60, 60, 60), (cx + 17 + tilt_offset, cy - 2, 5, 10), border_radius=2)

        # 纖細流線機身
        pygame.draw.polygon(surf, camo_green, [
            (cx + tilt_offset, cy - 24),
            (cx - 7 + tilt_offset, cy - 10),
            (cx - 5 + tilt_offset, cy + 22),
            (cx + 5 + tilt_offset, cy + 22),
            (cx + 7 + tilt_offset, cy - 10)
        ])
        pygame.draw.polygon(surf, camo_light, [
            (cx + tilt_offset, cy - 20),
            (cx - 4 + tilt_offset, cy - 8),
            (cx - 3 + tilt_offset, cy + 18),
            (cx + 3 + tilt_offset, cy + 18),
            (cx + 4 + tilt_offset, cy - 8)
        ])
        # 黃色機鼻整流罩
        pygame.draw.polygon(surf, yellow_nose, [
            (cx + tilt_offset, cy - 25),
            (cx - 4 + tilt_offset, cy - 16),
            (cx + 4 + tilt_offset, cy - 16)
        ])
        draw_propeller(surf, (cx + tilt_offset, cy - 25), 14, prop_angle)
        # 座艙方框罩
        pygame.draw.rect(surf, (90, 210, 255), (cx - 3 + tilt_offset, cy - 9, 6, 11), border_radius=2)
        # 尾翼配紅色方向舵
        pygame.draw.polygon(surf, COLOR_RED, [
            (cx + tilt_offset, cy + 22),
            (cx - 10 + tilt_offset, cy + 24),
            (cx + 10 + tilt_offset, cy + 24)
        ])

    else:
        # zero_phantom 零式改 幻影號：高科技能量改裝戰機
        dark_body = (35, 55, 60)
        emerald = (30, 160, 120)
        cyan_glow = (50, 230, 240)

        ws = int(28 * wing_scale)
        # 飛翼主體
        pygame.draw.polygon(surf, dark_body, [
            (cx - ws + tilt_offset, cy + 5),
            (cx + ws + tilt_offset, cy + 5),
            (cx + ws - 7 + tilt_offset, cy - 8),
            (cx + tilt_offset, cy - 24),
            (cx - ws + 7 + tilt_offset, cy - 8)
        ])
        pygame.draw.polygon(surf, emerald, [
            (cx - ws + 4 + tilt_offset, cy + 3),
            (cx + ws - 4 + tilt_offset, cy + 3),
            (cx + ws - 8 + tilt_offset, cy - 6),
            (cx + tilt_offset, cy - 20),
            (cx - ws + 8 + tilt_offset, cy - 6)
        ])
        # 能量光路迴紋
        pygame.draw.line(surf, cyan_glow, (cx - ws + 10 + tilt_offset, cy), (cx + tilt_offset, cy - 14), 2)
        pygame.draw.line(surf, cyan_glow, (cx + ws - 10 + tilt_offset, cy), (cx + tilt_offset, cy - 14), 2)
        # 前端能量聚焦環
        pygame.draw.circle(surf, cyan_glow, (cx + tilt_offset, cy - 23), 4)
        pygame.draw.circle(surf, COLOR_WHITE, (cx + tilt_offset, cy - 23), 2)
        # 雙翼能量脈衝發射器
        pygame.draw.rect(surf, cyan_glow, (cx - ws + 3 + tilt_offset, cy - 10, 3, 14))
        pygame.draw.rect(surf, cyan_glow, (cx + ws - 6 + tilt_offset, cy - 10, 3, 14))
        # 玻璃座艙
        pygame.draw.ellipse(surf, (150, 255, 255), (cx - 4 + tilt_offset, cy - 10, 8, 12))

    return SpriteCache.set(key, surf)


def create_wingman_sprite(fighter_id="p38_lightning", bank_state="center", frame=0):
    """
    建立伴隨主戰機作戰之僚機精靈圖 (2~3 機組合體)
    具備銀藍/青金機身、旋轉前置螺旋槳、雙挺前進機砲與航行指示燈
    """
    key = f"wingman_{fighter_id}_{bank_state}_{frame % 6}"
    cached = SpriteCache.get(key)
    if cached:
        return cached

    w, h = 42, 42
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    cx, cy = w // 2, h // 2
    tilt_offset = -2 if bank_state == "left" else (2 if bank_state == "right" else 0)
    prop_angle = (frame * 50) % 360

    body_color = (110, 160, 215)
    trim_color = (255, 220, 60)
    wing_color = (80, 130, 190)

    # 左右機翼
    pygame.draw.polygon(surf, wing_color, [
        (cx - 16 + tilt_offset, cy + 2),
        (cx + 16 + tilt_offset, cy + 2),
        (cx + 13 + tilt_offset, cy - 3),
        (cx - 13 + tilt_offset, cy - 3)
    ])
    # 機翼青金識別邊
    pygame.draw.line(surf, trim_color, (cx - 16 + tilt_offset, cy), (cx - 10 + tilt_offset, cy), 2)
    pygame.draw.line(surf, trim_color, (cx + 16 + tilt_offset, cy), (cx + 10 + tilt_offset, cy), 2)

    # 機身中央
    pygame.draw.ellipse(surf, body_color, (cx - 4 + tilt_offset, cy - 14, 8, 26))
    # 藍色晶瑩座艙罩
    pygame.draw.ellipse(surf, (140, 240, 255), (cx - 2 + tilt_offset, cy - 8, 5, 9))
    pygame.draw.ellipse(surf, COLOR_WHITE, (cx - 1 + tilt_offset, cy - 7, 2, 4))

    # 雙聯機砲管
    pygame.draw.line(surf, (50, 60, 75), (cx - 6 + tilt_offset, cy - 2), (cx - 6 + tilt_offset, cy - 14), 2)
    pygame.draw.line(surf, (50, 60, 75), (cx + 6 + tilt_offset, cy - 2), (cx + 6 + tilt_offset, cy - 14), 2)

    # 旋轉螺旋槳
    draw_propeller(surf, (cx + tilt_offset, cy - 14), 8, prop_angle, (220, 245, 255))

    # 尾翼
    pygame.draw.polygon(surf, trim_color, [
        (cx - 6 + tilt_offset, cy + 12),
        (cx + 6 + tilt_offset, cy + 12),
        (cx + tilt_offset, cy + 16)
    ])

    return SpriteCache.set(key, surf)


def create_tank_sprite(turret_angle=90, frame=0):
    """
    建立敵方地面裝甲戰車精靈圖 (Tank)
    事先完成精緻與多彩圖形：多彩森林/荒漠迷彩、重裝甲裙板、動態齒輪履帶、車燈光暈、敵方紅星軍徽與多角度旋轉砲塔
    """
    angle_snap = int(round(turret_angle / 5.0) * 5) % 360
    key = f"tank_{angle_snap}_{frame % 4}"
    cached = SpriteCache.get(key)
    if cached:
        return cached

    w, h = 50, 50
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    cx, cy = w // 2, h // 2

    camo_dark = (42, 58, 36)
    camo_mid = (70, 92, 52)
    camo_light = (112, 135, 78)
    camo_amber = (180, 130, 50)
    track_col = (28, 30, 32)
    metal_dark = (22, 24, 26)

    # 1. 左右兩側雙層厚重履帶 (Crawler Tracks with Steel Road Wheels)
    track_offset = (frame * 3) % 6
    for ox in [-18, 14]:
        # 履帶基座底板
        pygame.draw.rect(surf, track_col, (cx + ox, cy - 19, 9, 38), border_radius=3)
        # 負重輪與主動輪 (Road Wheels with Steel/Bronze Hubs)
        for wy in range(cy - 14, cy + 18, 7):
            pygame.draw.circle(surf, (60, 65, 70), (cx + ox + 4, wy), 3)
            pygame.draw.circle(surf, (140, 110, 50), (cx + ox + 4, wy), 1)
        # 動態履帶防滑齒紋
        for ty in range(int(cy - 17 + track_offset), int(cy + 17), 5):
            pygame.draw.line(surf, (85, 90, 95), (cx + ox + 1, ty), (cx + ox + 8, ty), 1)

    # 2. 車身底盤 (Armored Chassis with Multi-color Camouflage & Rivets)
    pygame.draw.rect(surf, camo_dark, (cx - 13, cy - 16, 26, 32), border_radius=3)
    # 多彩幾何迷彩塊 (Jungle/Desert Multitone Camouflage)
    pygame.draw.polygon(surf, camo_mid, [(cx - 11, cy - 14), (cx + 2, cy - 14), (cx - 4, cy + 4), (cx - 11, cy - 2)])
    pygame.draw.polygon(surf, camo_light, [(cx + 2, cy - 14), (cx + 10, cy - 14), (cx + 10, cy - 4), (cx - 1, cy - 6)])
    pygame.draw.polygon(surf, camo_amber, [(cx - 10, cy + 5), (cx + 9, cy + 8), (cx + 9, cy + 14), (cx - 10, cy + 14)])

    # 兩側防護裝甲裙板與裝甲鉚釘
    pygame.draw.line(surf, (30, 40, 28), (cx - 13, cy - 15), (cx - 13, cy + 15), 1)
    pygame.draw.line(surf, (30, 40, 28), (cx + 12, cy - 15), (cx + 12, cy + 15), 1)
    for ry in [-12, -4, 4, 12]:
        pygame.draw.circle(surf, (130, 140, 120), (cx - 11, cy + ry), 1)
        pygame.draw.circle(surf, (130, 140, 120), (cx + 10, cy + ry), 1)

    # 前探照車燈 (Front Headlights with Amber Glow)
    pygame.draw.circle(surf, (255, 230, 120), (cx - 8, cy - 15), 2)
    pygame.draw.circle(surf, (255, 230, 120), (cx + 8, cy - 15), 2)

    # 敵方鮮紅星軍徽 (Red Star Insignia Badge)
    pygame.draw.circle(surf, COLOR_WHITE, (cx - 5, cy + 2), 4)
    pygame.draw.circle(surf, COLOR_RED, (cx - 5, cy + 2), 3)

    # 3. 旋轉砲塔 (360-Degree Rotatable Dual Turret)
    turret_rad = math.radians(turret_angle)
    barrel_len = 19
    bx = cx + math.cos(turret_rad) * barrel_len
    by = cy + math.sin(turret_rad) * barrel_len

    # 主加農砲管與雙重防盾
    pygame.draw.line(surf, metal_dark, (cx, cy), (int(bx), int(by)), 4)
    pygame.draw.line(surf, (60, 65, 70), (cx, cy), (int(bx), int(by)), 2)
    # 砲口雙室制退器
    pygame.draw.circle(surf, (20, 20, 20), (int(bx), int(by)), 3)
    pygame.draw.circle(surf, (255, 120, 40), (int(bx), int(by)), 1)

    # 圓形複合裝甲砲塔
    pygame.draw.circle(surf, (32, 42, 28), (cx, cy), 10)
    pygame.draw.circle(surf, camo_mid, (cx, cy), 8)
    pygame.draw.circle(surf, camo_light, (cx - 2, cy - 2), 5)

    # 車長指揮塔與光學潛望鏡 (Commander Periscope with Ruby Lens)
    pygame.draw.circle(surf, (20, 20, 20), (cx + 2, cy - 2), 3)
    pygame.draw.circle(surf, (0, 240, 255), (cx + 2, cy - 2), 1)

    return SpriteCache.set(key, surf)


def create_warship_sprite(ship_type="cruiser", frame=0):
    """
    事先完成敵方軍艦精緻與多彩圖形 (Pre-rendered Exquisite & Colorful Naval Warships)
    包含海軍吃水紅線、柚木甲板、深海迷彩、雙聯裝重砲塔、 brass 防空砲、艦橋訊號旗與航行舷寬
    """
    key = f"warship_{ship_type}_{frame % 6}"
    cached = SpriteCache.get(key)
    if cached:
        return cached

    # 尺寸映射
    dims = {
        "dreadnought": (106, 230, 86, 210),
        "battleship": (96, 200, 76, 180),
        "carrier": (92, 190, 72, 170),
        "cruiser": (74, 150, 54, 130),
        "patrol_boat": (46, 78, 30, 58),
        "gunboat": (54, 95, 38, 75)
    }
    sw, sh, bw, bl = dims.get(ship_type, (74, 150, 54, 130))
    surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
    cx, cy = sw // 2, sh // 2
    hw, hl = bw // 2, bl // 2

    # 多彩海軍色盤
    camo_hull_dark = (35, 48, 68)       # 皇家深海藍鋼
    camo_hull_light = (75, 95, 120)     # 眩暈迷彩淺灰藍
    camo_white = (210, 220, 230)        # 迷彩象牙白
    waterline_red = (185, 35, 35)       # 船身吃水赤紅底線 (Waterline Crimson)
    deck_wood = (195, 155, 105)         # 暖金柚木甲板 (Teak Deck)
    bridge_col = (50, 65, 80)           # 艦橋重裝甲
    turret_metal = (40, 50, 60)         # 砲塔深鋼

    # 1. 鮮豔吃水線外廓 (Waterline Crimson Hull Edge)
    hull_outer = [
        (cx, cy + hl + 4),
        (cx - hw - 3, cy + hl * 0.4),
        (cx - hw - 1, cy - hl * 0.8),
        (cx - hw * 0.65 - 2, cy - hl - 3),
        (cx + hw * 0.65 + 2, cy - hl - 3),
        (cx + hw + 1, cy - hl * 0.8),
        (cx + hw + 3, cy + hl * 0.4)
    ]
    pygame.draw.polygon(surf, waterline_red, hull_outer)

    # 2. 鋼鐵船身主體與幾何迷彩 (Dazzle Geometric Camouflage)
    hull_pts = [
        (cx, cy + hl),
        (cx - hw, cy + hl * 0.4),
        (cx - hw + 2, cy - hl * 0.8),
        (cx - hw * 0.6, cy - hl),
        (cx + hw * 0.6, cy - hl),
        (cx + hw - 2, cy - hl * 0.8),
        (cx + hw, cy + hl * 0.4)
    ]
    pygame.draw.polygon(surf, camo_hull_dark, hull_pts)

    # 幾何迷彩條塊 (Dazzle Camo Patterns)
    camo_poly1 = [(cx - hw, cy - int(hl * 0.2)), (cx - int(hw * 0.2), cy - int(hl * 0.5)),
                  (cx - int(hw * 0.2), cy + int(hl * 0.1)), (cx - hw, cy + int(hl * 0.3))]
    pygame.draw.polygon(surf, camo_hull_light, camo_poly1)
    camo_poly2 = [(cx + int(hw * 0.1), cy - int(hl * 0.6)), (cx + hw - 2, cy - int(hl * 0.4)),
                  (cx + hw, cy - int(hl * 0.1)), (cx + int(hw * 0.2), cy + int(hl * 0.2))]
    pygame.draw.polygon(surf, camo_white, camo_poly2)

    # 3. 柚木甲板 (Teak Wood Deck with Planking Details)
    deck_pts = [
        (cx, cy + hl - 5),
        (cx - hw + 4, cy + hl * 0.38),
        (cx - hw + 6, cy - hl * 0.76),
        (cx - hw * 0.5, cy - hl + 4),
        (cx + hw * 0.5, cy - hl + 4),
        (cx + hw - 6, cy - hl * 0.76),
        (cx + hw - 4, cy + hl * 0.38)
    ]
    deck_color = deck_wood if ship_type != "carrier" else (55, 60, 68)
    pygame.draw.polygon(surf, deck_color, deck_pts)

    # 4. 甲板特定細節 (航母跑道 vs 巡洋艦/戰艦砲塔)
    if ship_type == "carrier":
        # 航母飛行甲板：亮黃與雪白雙色起降標線
        for ry in range(int(cy - hl + 15), int(cy + hl - 18), 20):
            pygame.draw.line(surf, (255, 230, 40), (cx, ry), (cx, ry + 12), 2)
            pygame.draw.line(surf, (240, 245, 255), (cx - 16, ry + 4), (cx - 16, ry + 14), 1)
            pygame.draw.line(surf, (240, 245, 255), (cx + 16, ry + 4), (cx + 16, ry + 14), 1)
        # 升降機 (Aircraft Elevator)
        pygame.draw.rect(surf, (38, 42, 48), (cx - 14, cy - 30, 28, 24), border_radius=2)
        # 艦島 (Island Bridge)
        pygame.draw.rect(surf, bridge_col, (cx + hw - 15, cy - 22, 12, 38), border_radius=2)
        pygame.draw.circle(surf, (80, 230, 255), (cx + hw - 9, cy - 10), 3)
    else:
        # 中型巡洋艦 / 重戰列艦：雙聯裝迴轉巨砲與 brass 金色副砲
        # 艦橋指揮塔 (Armored Bridge Citadel)
        bw_b = 20 if ship_type == "cruiser" else 26
        bh_b = 26 if ship_type == "cruiser" else 34
        pygame.draw.rect(surf, bridge_col, (cx - bw_b // 2, cy - bh_b // 2, bw_b, bh_b), border_radius=3)
        # 艦橋海藍觀察窗
        pygame.draw.rect(surf, (80, 220, 255), (cx - bw_b // 2 + 3, cy - bh_b // 2 + 2, bw_b - 6, 4))
        # 測距儀與通訊天線
        pygame.draw.line(surf, (255, 215, 0), (cx - 10, cy), (cx + 10, cy), 2)

        # 橙白色救生艇 (Lifeboats)
        pygame.draw.ellipse(surf, (255, 120, 30), (cx - hw + 2, cy - 8, 6, 16))
        pygame.draw.ellipse(surf, COLOR_WHITE, (cx - hw + 3, cy - 6, 4, 12))
        pygame.draw.ellipse(surf, (255, 120, 30), (cx + hw - 8, cy - 8, 6, 16))
        pygame.draw.ellipse(surf, COLOR_WHITE, (cx + hw - 7, cy - 6, 4, 12))

        # 主砲塔位置
        turret_list = [cy + hl * 0.35, cy - hl * 0.4]
        if ship_type in ["battleship", "dreadnought"]:
            turret_list.append(cy + hl * 0.6)
        if ship_type == "dreadnought":
            turret_list.append(cy - hl * 0.65)

        for ty in turret_list:
            t_radius = 8 if ship_type == "cruiser" else 11
            # 砲塔座圈與砲體
            pygame.draw.circle(surf, turret_metal, (cx, int(ty)), t_radius)
            pygame.draw.circle(surf, (65, 80, 95), (cx, int(ty)), t_radius - 2)
            # 砲塔頂部紅金飾紋 (Red/Gold Crown Insignia)
            pygame.draw.circle(surf, COLOR_RED, (cx, int(ty)), 4)
            pygame.draw.circle(surf, COLOR_GOLD, (cx, int(ty)), 2)
            # 雙聯裝加農長砲管 (Dual Heavy Naval Cannons)
            pygame.draw.line(surf, (15, 18, 22), (cx - 3, int(ty)), (cx - 3, int(ty) + 16), 3)
            pygame.draw.line(surf, (15, 18, 22), (cx + 3, int(ty)), (cx + 3, int(ty) + 16), 3)
            # 白色防水砲布 (White Blast Bags)
            pygame.draw.circle(surf, COLOR_WHITE, (cx - 3, int(ty) + 4), 2)
            pygame.draw.circle(surf, COLOR_WHITE, (cx + 3, int(ty) + 4), 2)

    return SpriteCache.set(key, surf)



def create_enemy_sprite(enemy_type, frame=0):
    """建立各式豐富的敵機與敵艦圖形"""
    key = f"enemy_{enemy_type}_{frame % 6}"
    cached = SpriteCache.get(key)
    if cached:
        return cached

    prop_angle = (frame * 60) % 360

    if enemy_type == "scout_zero":
        # 敏捷零式偵察機 (綠身/紅太陽機徽)
        surf = pygame.Surface((44, 44), pygame.SRCALPHA)
        cx, cy = 22, 22
        # 機翼
        pygame.draw.polygon(surf, (40, 95, 45), [(4, cy - 2), (40, cy - 2), (36, cy + 6), (8, cy + 6)])
        # 紅日軍徽
        pygame.draw.circle(surf, COLOR_RED, (12, cy + 2), 3)
        pygame.draw.circle(surf, COLOR_RED, (32, cy + 2), 3)
        # 機身 (朝下飛行)
        pygame.draw.ellipse(surf, (50, 110, 55), (cx - 5, cy - 18, 10, 36))
        pygame.draw.ellipse(surf, (200, 220, 200), (cx - 3, cy - 8, 6, 12))
        # 螺旋槳在底部 (朝下飛行)
        draw_propeller(surf, (cx, cy + 18), 10, prop_angle, (255, 200, 200))
        # 尾翼
        pygame.draw.polygon(surf, (40, 95, 45), [(cx - 10, cy - 14), (cx + 10, cy - 14), (cx, cy - 18)])

    elif enemy_type == "fast_interceptor":
        # 高速攔截突擊機 (黃黑條紋蜂鳥型)
        surf = pygame.Surface((48, 48), pygame.SRCALPHA)
        cx, cy = 24, 24
        # 後掠翼
        pygame.draw.polygon(surf, (230, 170, 20), [(2, cy - 8), (46, cy - 8), (28, cy + 8), (20, cy + 8)])
        # 黑色斑紋
        pygame.draw.polygon(surf, (20, 20, 20), [(10, cy - 6), (16, cy - 6), (22, cy + 4), (16, cy + 4)])
        pygame.draw.polygon(surf, (20, 20, 20), [(38, cy - 6), (32, cy - 6), (26, cy + 4), (32, cy + 4)])
        # 機身尖錐
        pygame.draw.polygon(surf, (200, 30, 30), [(cx, cy + 22), (cx - 6, cy - 16), (cx + 6, cy - 16)])
        pygame.draw.circle(surf, (255, 255, 100), (cx, cy + 10), 3)

    elif enemy_type == "twin_bomber":
        # 雙發中型轟炸機 (迷彩重型戰機)
        surf = pygame.Surface((68, 68), pygame.SRCALPHA)
        cx, cy = 34, 34
        # 寬大平直機翼
        pygame.draw.rect(surf, (70, 85, 65), (4, cy - 6, 60, 12), border_radius=3)
        # 雙螺旋槳發動機艙
        for ox in [-16, 16]:
            pygame.draw.rect(surf, (50, 60, 50), (cx + ox - 4, cy - 12, 8, 24), border_radius=2)
            draw_propeller(surf, (cx + ox, cy + 14), 10, prop_angle)
        # 粗大機身
        pygame.draw.ellipse(surf, (85, 100, 80), (cx - 8, cy - 26, 16, 52))
        # 玻璃觀察機鼻
        pygame.draw.circle(surf, (120, 210, 255), (cx, cy + 24), 5)
        # 機尾十字翼
        pygame.draw.rect(surf, (70, 85, 65), (cx - 14, cy - 24, 28, 5))

    elif enemy_type == "heavy_gunship":
        # 四發空中砲艇 / 巨型護衛機
        surf = pygame.Surface((84, 84), pygame.SRCALPHA)
        cx, cy = 42, 42
        # 重裝暗黑金屬裝甲
        pygame.draw.polygon(surf, (60, 65, 75), [
            (8, cy - 10), (76, cy - 10), (60, cy + 14), (24, cy + 14)
        ])
        # 4具螺旋槳引擎
        for ox in [-28, -14, 14, 28]:
            pygame.draw.rect(surf, (40, 45, 55), (cx + ox - 3, cy - 14, 6, 26))
            draw_propeller(surf, (cx + ox, cy + 14), 8, prop_angle)
        # 重型機身與旋轉機砲塔
        pygame.draw.ellipse(surf, (80, 85, 100), (cx - 12, cy - 32, 24, 64))
        # 砲塔
        pygame.draw.circle(surf, (200, 60, 60), (cx, cy), 7)
        pygame.draw.circle(surf, (40, 40, 40), (cx, cy), 4)
        pygame.draw.line(surf, (30, 30, 30), (cx, cy), (cx, cy + 18), 3)

    elif enemy_type == "sea_destroyer":
        # 海面巡邏驅逐艦 / 護航快艇 (在深海背景上航行)
        surf = pygame.Surface((50, 75), pygame.SRCALPHA)
        cx, cy = 25, 37
        # 艦身灰鋼
        pygame.draw.polygon(surf, (80, 95, 110), [
            (cx, cy + 34), (cx - 10, cy + 18), (cx - 10, cy - 30),
            (cx + 10, cy - 30), (cx + 10, cy + 18)
        ])
        # 甲板
        pygame.draw.rect(surf, (110, 125, 140), (cx - 7, cy - 25, 14, 48), border_radius=2)
        # 艦橋
        pygame.draw.rect(surf, (60, 75, 90), (cx - 5, cy - 8, 10, 16))
        # 主砲塔
        pygame.draw.circle(surf, (40, 40, 40), (cx, cy - 16), 5)
        pygame.draw.line(surf, (20, 20, 20), (cx, cy - 16), (cx, cy + 8), 3)
        # 航行白色浪花
        pygame.draw.line(surf, (255, 255, 255, 150), (cx - 12, cy + 30), (cx - 18, cy + 10), 2)
        pygame.draw.line(surf, (255, 255, 255, 150), (cx + 12, cy + 30), (cx + 18, cy + 10), 2)

    else:
        # 預設通用紅隼敵機
        surf = pygame.Surface((36, 36), pygame.SRCALPHA)
        cx, cy = 18, 18
        pygame.draw.polygon(surf, (180, 40, 40), [(cx, cy + 16), (4, cy - 8), (32, cy - 8)])
        pygame.draw.circle(surf, (255, 200, 50), (cx, cy), 4)

    return SpriteCache.set(key, surf)


def create_midboss_fighter_sprite(frame=0):
    """
    【核心規則】：每關的中途大魔王以空中戰機為主 (Mid-Boss Aerial Fighter)
    大型雙發重型空戰突擊機，配備全向向量推進器、翼端重火炮、前翼掠角與高亮座艙罩
    """
    key = f"midboss_fighter_{frame % 6}"
    cached = SpriteCache.get(key)
    if cached:
        return cached

    w, h = 136, 110
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    cx, cy = w // 2, h // 2

    body_dark = (38, 42, 52)
    body_mid = (65, 72, 88)
    body_light = (98, 108, 130)
    crimson_trim = (220, 45, 55)
    gold_trim = (245, 190, 50)
    flame_blue = (60, 180, 255)
    flame_orange = (255, 130, 40)

    # 1. 雙後燃器噴射烈焰 (Pulsing Jet Afterburners)
    pulse = (frame % 4) * 2
    for ox in [-24, 24]:
        # 外層橙紅焰
        pygame.draw.polygon(surf, flame_orange, [
            (cx + ox - 6, cy + 28), (cx + ox + 6, cy + 28),
            (cx + ox, cy + 44 + pulse)
        ])
        # 內層高能青藍核心
        pygame.draw.polygon(surf, flame_blue, [
            (cx + ox - 3, cy + 28), (cx + ox + 3, cy + 28),
            (cx + ox, cy + 38 + pulse)
        ])

    # 2. 前掠前翼 (Canards)
    pygame.draw.polygon(surf, body_dark, [(cx, cy - 28), (cx - 36, cy - 14), (cx - 18, cy - 8)])
    pygame.draw.polygon(surf, body_dark, [(cx, cy - 28), (cx + 36, cy - 14), (cx + 18, cy - 8)])

    # 3. 主翼與後掠三角翼 (Main Delta Wings)
    wing_pts = [
        (cx, cy - 38),                  # 機頭尖端
        (cx - 16, cy - 16),
        (cx - 62, cy + 18),             # 左翼尖端
        (cx - 56, cy + 28),
        (cx - 24, cy + 30),
        (cx - 18, cy + 38),             # 左噴口
        (cx + 18, cy + 38),             # 右噴口
        (cx + 24, cy + 30),
        (cx + 56, cy + 28),
        (cx + 62, cy + 18),             # 右翼尖端
        (cx + 16, cy - 16),
    ]
    pygame.draw.polygon(surf, body_mid, wing_pts)
    pygame.draw.polygon(surf, body_dark, wing_pts, 2)

    # 4. 裝甲迷彩與赤紅警戒塗裝
    pygame.draw.polygon(surf, crimson_trim, [
        (cx - 52, cy + 14), (cx - 60, cy + 18), (cx - 40, cy + 25), (cx - 32, cy + 22)
    ])
    pygame.draw.polygon(surf, crimson_trim, [
        (cx + 52, cy + 14), (cx + 60, cy + 18), (cx + 40, cy + 25), (cx + 32, cy + 22)
    ])
    pygame.draw.polygon(surf, gold_trim, [
        (cx - 14, cy - 10), (cx - 22, cy + 15), (cx - 16, cy + 18), (cx - 10, cy - 5)
    ])
    pygame.draw.polygon(surf, gold_trim, [
        (cx + 14, cy - 10), (cx + 22, cy + 15), (cx + 16, cy + 18), (cx + 10, cy - 5)
    ])

    # 5. 中央重裝機身脊樑 (Central Fuselage Spine)
    fuse_pts = [
        (cx, cy - 44),
        (cx - 14, cy - 20),
        (cx - 12, cy + 32),
        (cx + 12, cy + 32),
        (cx + 14, cy - 20),
    ]
    pygame.draw.polygon(surf, body_light, fuse_pts)
    pygame.draw.polygon(surf, body_dark, fuse_pts, 2)

    # 6. 雙側發動機導風口與向量噴嘴 (Twin Turbofan Intakes & Nozzles)
    for ox in [-22, 22]:
        pygame.draw.rect(surf, (30, 32, 38), (cx + ox - 7, cy + 24, 14, 10))
        pygame.draw.rect(surf, (80, 85, 95), (cx + ox - 6, cy + 24, 12, 8), 1)

    # 7. 翼端 30mm 旋轉重機砲與外掛飛彈架
    for ox in [-58, 58]:
        # 重機砲管向前伸出
        pygame.draw.line(surf, (25, 25, 30), (cx + ox, cy + 16), (cx + ox, cy - 8), 3)
        pygame.draw.line(surf, (80, 85, 90), (cx + ox, cy + 16), (cx + ox, cy - 8), 1)
        # 飛彈莢艙
        pygame.draw.circle(surf, (255, 60, 60), (cx + ox, cy + 2), 3)

    # 8. 鍍金/深藍晶體抗荷座艙罩 (Armored Crystal Canopy)
    pygame.draw.polygon(surf, (20, 40, 60), [
        (cx, cy - 32), (cx - 6, cy - 14), (cx, cy - 6), (cx + 6, cy - 14)
    ])
    pygame.draw.polygon(surf, (60, 220, 255), [
        (cx, cy - 30), (cx - 4, cy - 15), (cx, cy - 8), (cx + 4, cy - 15)
    ])
    # 座艙高光反光
    pygame.draw.line(surf, (255, 255, 255), (cx - 2, cy - 26), (cx - 2, cy - 12), 1)

    return SpriteCache.set(key, surf)


def create_boss_sprite(boss_type="sky_fighter", stage_num=1, frame=0, form=1):
    """
    【核心規則】：每關最後的大魔王一律為空中戰機且多型態的模式 (Multi-Form Aerial Boss Fighter)
    形態 1 (Form 1): 高速巡弋重戰機形態 (HP > 65%)
    形態 2 (Form 2): 展開式多管武裝戰鬥機形態 (30% < HP <= 65%)
    形態 3 (Form 3): 暴走滅世超時空神魔戰機形態 (HP <= 30%)
    """
    key = f"boss_fighter_{boss_type}_{stage_num}_{form}_{frame % 8}"
    cached = SpriteCache.get(key)
    if cached:
        return cached

    w, h = 230, 180
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    cx, cy = w // 2, h // 2

    # 各主題對應的空中戰機專屬塗裝色系
    stage_colors = [
        ((45, 65, 95), (65, 95, 140), (255, 120, 40)),    # Stage 1: 太平洋風暴藍
        ((40, 80, 75), (55, 120, 110), (0, 230, 240)),    # Stage 2: 珊瑚青玉
        ((25, 28, 42), (40, 45, 70), (140, 100, 255)),    # Stage 3: 午夜深暗
        ((65, 30, 25), (105, 45, 35), (255, 80, 30)),     # Stage 4: 熔岩赤紅
        ((35, 60, 35), (50, 95, 50), (220, 200, 50)),     # Stage 5: 密林深綠
        ((35, 40, 60), (55, 65, 95), (255, 240, 60)),     # Stage 6: 雷暴電紫
        ((85, 45, 35), (135, 70, 50), (255, 160, 50)),    # Stage 7: 夕陽烈橙
        ((45, 75, 110), (90, 135, 185), (220, 245, 255)), # Stage 8: 急凍極冰
        ((80, 65, 40), (120, 95, 55), (255, 200, 70)),    # Stage 9: 荒漠沙珀
        ((30, 50, 80), (45, 80, 130), (0, 240, 200)),     # Stage 10: 直布羅陀旗艦
    ]
    theme_idx = (stage_num - 1) % len(stage_colors)
    col_dark, col_mid, col_accent = stage_colors[theme_idx]

    # 1. 噴射尾焰引擎 (Engine Thruster Flames)
    thrust_len = 16 + int(8 * math.sin(frame * 0.8))
    flame_col = (255, 200, 50) if form < 3 else (255, 50, 50)
    for ox in [-38, -18, 18, 38]:
        pygame.draw.polygon(surf, flame_col, [
            (cx + ox - 5, cy - 50), (cx + ox + 5, cy - 50), (cx + ox, cy - 50 - thrust_len)
        ])
        pygame.draw.polygon(surf, COLOR_WHITE, [
            (cx + ox - 2, cy - 50), (cx + ox + 2, cy - 50), (cx + ox, cy - 50 - int(thrust_len * 0.6))
        ])

    # 2. 形態特有大型機翼 (Wings per Form)
    if form == 1:
        # 形態 1：流線高速巡弋前掠主翼
        wing_pts = [
            (cx, cy + 45), (cx - 95, cy - 10), (cx - 90, cy - 35),
            (cx - 30, cy - 38), (cx + 30, cy - 38),
            (cx + 90, cy - 35), (cx + 95, cy - 10)
        ]
        pygame.draw.polygon(surf, col_dark, wing_pts)
        pygame.draw.polygon(surf, col_mid, [
            (cx, cy + 35), (cx - 80, cy - 12), (cx - 75, cy - 30),
            (cx - 25, cy - 32), (cx + 25, cy - 32),
            (cx + 75, cy - 30), (cx + 80, cy - 12)
        ])
        # 翼尖導流板
        pygame.draw.polygon(surf, col_accent, [(cx - 95, cy - 10), (cx - 98, cy + 12), (cx - 88, cy - 5)])
        pygame.draw.polygon(surf, col_accent, [(cx + 95, cy - 10), (cx + 98, cy + 12), (cx + 88, cy - 5)])

    elif form == 2:
        # 形態 2：副翼重武裝全面展開 (雙段可變幾何翼 + 翼下掛架)
        wing_pts = [
            (cx, cy + 50), (cx - 108, cy + 5), (cx - 110, cy - 40),
            (cx - 40, cy - 42), (cx + 40, cy - 42),
            (cx + 110, cy - 40), (cx + 108, cy + 5)
        ]
        pygame.draw.polygon(surf, col_dark, wing_pts)
        pygame.draw.polygon(surf, col_mid, [
            (cx, cy + 38), (cx - 96, cy + 2), (cx - 98, cy - 34),
            (cx - 32, cy - 36), (cx + 32, cy - 36),
            (cx + 98, cy - 34), (cx + 96, cy + 2)
        ])
        # 展開武裝外掛吊艙與雙重導彈槽
        for side in [-80, -55, 55, 80]:
            pygame.draw.rect(surf, (30, 30, 35), (cx + side - 6, cy - 25, 12, 35), border_radius=3)
            pygame.draw.line(surf, (220, 40, 40), (cx + side, cy - 22), (cx + side, cy + 18), 3)

    else:
        # 形態 3：暴走超時空滅世戰機形態 (全幅光子能量羽翼爆發)
        pulse = int(180 + 75 * math.sin(frame * 0.7))
        energy_glow = (255, pulse, 60) if stage_num % 2 == 1 else (pulse, 80, 255)

        # 展開巨大能量光翼
        glow_wing = [
            (cx, cy + 60), (cx - 115, cy + 25), (cx - 112, cy - 48),
            (cx - 45, cy - 45), (cx + 45, cy - 45),
            (cx + 112, cy - 48), (cx + 115, cy + 25)
        ]
        pygame.draw.polygon(surf, energy_glow, glow_wing)
        pygame.draw.polygon(surf, (20, 20, 28), [
            (cx, cy + 48), (cx - 100, cy + 16), (cx - 98, cy - 38),
            (cx - 35, cy - 38), (cx + 35, cy - 38),
            (cx + 98, cy - 38), (cx + 100, cy + 16)
        ])
        # 4 道高能離子光束發生翼
        for deg in [-65, -35, 35, 65]:
            rad = math.radians(deg)
            ex = cx + int(105 * math.sin(rad))
            ey = cy + int(45 * math.cos(rad))
            pygame.draw.circle(surf, energy_glow, (ex, ey), 8)
            pygame.draw.circle(surf, COLOR_WHITE, (ex, ey), 4)

    # 3. 空中戰機主機身軀幹 (Heavy Fighter Main Fuselage)
    fuselage_pts = [
        (cx, cy + 70),          # 銳利機頭 (朝下)
        (cx - 18, cy + 42),
        (cx - 24, cy - 15),
        (cx - 20, cy - 52),
        (cx + 20, cy - 52),
        (cx + 24, cy - 15),
        (cx + 18, cy + 42)
    ]
    pygame.draw.polygon(surf, (30, 36, 45), fuselage_pts)
    pygame.draw.polygon(surf, col_mid, [
        (cx, cy + 62), (cx - 13, cy + 36), (cx - 18, cy - 12),
        (cx - 14, cy - 46), (cx + 14, cy - 46),
        (cx + 18, cy - 12), (cx + 13, cy + 36)
    ])

    # 4. 戰機重型駕駛座艙 / 戰術感應眼 (Armored Cockpit Canopy)
    canopy_col = (0, 230, 255) if form < 3 else (255, 40, 40)
    pygame.draw.ellipse(surf, canopy_col, (cx - 8, cy + 10, 16, 32))
    pygame.draw.ellipse(surf, COLOR_WHITE, (cx - 4, cy + 14, 8, 12))

    # 5. 前向航空機砲與重型主砲口 (Forward Heavy Autocannons)
    gun_len = 22 if form == 1 else (32 if form == 2 else 40)
    for ox in [-14, 14]:
        pygame.draw.line(surf, (20, 20, 20), (cx + ox, cy + 35), (cx + ox, cy + 35 + gun_len), 4)
        pygame.draw.circle(surf, col_accent, (cx + ox, cy + 35 + gun_len), 3)

    # 形態 2 與形態 3 追加翼下雙重砲
    if form >= 2:
        for ox in [-45, 45]:
            pygame.draw.line(surf, (20, 20, 20), (cx + ox, cy + 5), (cx + ox, cy + 5 + gun_len), 4)
            pygame.draw.circle(surf, (255, 50, 50), (cx + ox, cy + 5 + gun_len), 3)

    return SpriteCache.set(key, surf)

def create_powerup_sprite(powerup_type, frame=0):
    """
    建立掉落戰果 (Power-up Item)
    P: 升級武器火力
    S: 護盾修復/增強
    B: 戰術大炸彈
    W: 武器切換/強化
    """
    key = f"powerup_{powerup_type}_{frame % 12}"
    cached = SpriteCache.get(key)
    if cached:
        return cached

    size = 32
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx, cy = size // 2, size // 2

    # 旋轉閃爍外光圈
    ring_radius = 14 + int(2 * math.sin(frame * 0.6))
    if powerup_type == "P":
        # 武器威力升級 (金色/橙色)
        bg_col = (255, 180, 20)
        ring_col = (255, 230, 80)
        letter = "P"
    elif powerup_type == "S":
        # 護盾 (藍色/青色)
        bg_col = (40, 160, 255)
        ring_col = (140, 240, 255)
        letter = "S"
    elif powerup_type == "B":
        # 炸彈 (紅色/紫紅)
        bg_col = (230, 50, 50)
        ring_col = (255, 140, 140)
        letter = "B"
    elif powerup_type == "L":
        # 自動追蹤高能雷射 (極光青藍/霓虹光輝)
        bg_col = (0, 210, 230)
        ring_col = (130, 255, 240)
        letter = "L"
    else:  # "W"
        # 武器強化 (綠色/金色)
        bg_col = (40, 200, 100)
        ring_col = (160, 255, 180)
        letter = "W"

    pygame.draw.circle(surf, ring_col, (cx, cy), ring_radius, 2)
    pygame.draw.circle(surf, bg_col, (cx, cy), 12)
    pygame.draw.circle(surf, COLOR_WHITE, (cx, cy), 12, 1)

    # 繪製字母 (確保字型子系統已初始化)
    if not pygame.font.get_init():
        pygame.font.init()
    font = pygame.font.Font(None, 22)
    txt = font.render(letter, True, COLOR_WHITE)
    trect = txt.get_rect(center=(cx, cy))
    surf.blit(txt, trect)

    return SpriteCache.set(key, surf)


def create_bullet_sprite(b_type="player_vulcan", angle=0, player_id=1):
    """
    各種類型的子彈圖形 (我方 vs 敵方在色彩與造型上極致分明)
    【核心規則】：
    1. 二人戰機射出的子彈顏色需不一樣 (P1 金藍光 vs P2 翠綠粉紫電)
    2. 子彈尺寸大小縮小為原本的二分之一 (1/2 size 精細化彈幕)
    """
    is_circular = b_type in ["enemy_bullet", "boss_heavy_bullet"]
    norm_ang = 0 if is_circular else ((int(round(angle / 5.0)) * 5) % 360)
    key = f"bullet_{b_type}_{norm_ang}_p{player_id}"
    cached = SpriteCache.get(key)
    if cached:
        return cached

    if norm_ang != 0:
        base_surf = create_bullet_sprite(b_type, 0, player_id=player_id)
        rot_surf = pygame.transform.rotate(base_surf, norm_ang)
        return SpriteCache.set(key, rot_surf)

    if b_type == "player_vulcan":
        # 尺寸縮小為二分之一 (6x12，原 12x24)
        surf = pygame.Surface((6, 12), pygame.SRCALPHA)
        if player_id == 1:
            # P1：經典金黃高穿透機砲
            pygame.draw.ellipse(surf, (255, 190, 40, 180), (0, 0, 6, 12))
            pygame.draw.ellipse(surf, (255, 245, 90), (1, 1, 4, 10))
            pygame.draw.ellipse(surf, COLOR_WHITE, (2, 2, 2, 8))
        else:
            # P2：翡翠極光綠高能機砲 (鮮明對比 P1 金黃)
            pygame.draw.ellipse(surf, (40, 240, 110, 180), (0, 0, 6, 12))
            pygame.draw.ellipse(surf, (110, 255, 170), (1, 1, 4, 10))
            pygame.draw.ellipse(surf, COLOR_WHITE, (2, 2, 2, 8))

    elif b_type == "player_wingman_bullet":
        # 尺寸縮小為二分之一 (5x11，原 10x22)
        surf = pygame.Surface((5, 11), pygame.SRCALPHA)
        if player_id == 1:
            # P1：青藍高光
            pygame.draw.ellipse(surf, (60, 220, 255, 180), (0, 0, 5, 11))
            pygame.draw.ellipse(surf, (160, 245, 255), (1, 1, 3, 9))
        else:
            # P2：嫩黃綠脈衝光
            pygame.draw.ellipse(surf, (180, 255, 60, 180), (0, 0, 5, 11))
            pygame.draw.ellipse(surf, (220, 255, 140), (1, 1, 3, 9))
        pygame.draw.ellipse(surf, COLOR_WHITE, (1, 2, 3, 6))

    elif b_type == "player_spread":
        # 尺寸縮小為二分之一 (7x9，原 14x18)
        surf = pygame.Surface((7, 9), pygame.SRCALPHA)
        if player_id == 1:
            # P1：晶藍散彈
            pygame.draw.ellipse(surf, (40, 160, 255, 170), (0, 0, 7, 9))
            pygame.draw.ellipse(surf, (90, 210, 255), (1, 1, 5, 7))
        else:
            # P2：紫電耀斑散彈 (霓虹紫)
            pygame.draw.ellipse(surf, (210, 60, 255, 170), (0, 0, 7, 9))
            pygame.draw.ellipse(surf, (240, 150, 255), (1, 1, 5, 7))
        pygame.draw.ellipse(surf, COLOR_WHITE, (2, 2, 3, 5))

    elif b_type in ["player_laser", "player_homing_laser"]:
        # 尺寸縮小為二分之一 (6x18，原 12x36)
        surf = pygame.Surface((6, 18), pygame.SRCALPHA)
        if player_id == 1:
            # P1：耀眼極光碧藍高能雷射
            pygame.draw.ellipse(surf, (0, 240, 220, 180), (0, 0, 6, 18))
            pygame.draw.ellipse(surf, (80, 255, 235), (1, 1, 4, 16))
            pygame.draw.circle(surf, COLOR_WHITE, (3, 3), 2)
        else:
            # P2：霓虹玫瑰洋紅熱射線 (鮮明對比 P1 碧藍)
            pygame.draw.ellipse(surf, (255, 50, 190, 180), (0, 0, 6, 18))
            pygame.draw.ellipse(surf, (255, 140, 225), (1, 1, 4, 16))
            pygame.draw.circle(surf, COLOR_WHITE, (3, 3), 2)

    elif b_type == "player_missile":
        # 尺寸縮小為二分之一 (6x12，原 12x24)
        surf = pygame.Surface((6, 12), pygame.SRCALPHA)
        pygame.draw.rect(surf, (150, 165, 180), (1, 2, 4, 8), border_radius=1)
        tip_color = (255, 215, 0) if player_id == 1 else (255, 80, 160)
        pygame.draw.polygon(surf, tip_color, [(3, 0), (1, 3), (5, 3)])
        # 尾焰
        pygame.draw.polygon(surf, COLOR_ORANGE, [(3, 12), (1, 9), (5, 9)])
    elif b_type == "enemy_bullet":
        surf = pygame.Surface((16, 16), pygame.SRCALPHA)
        # 【敵方危險血紅能量彈】：醒目紅色外光圈與亮橙核心，極度易於辨認與閃避
        pygame.draw.circle(surf, (255, 20, 20, 140), (8, 8), 7)
        pygame.draw.circle(surf, (255, 30, 30), (8, 8), 5)
        pygame.draw.circle(surf, (255, 60, 40), (8, 8), 3)
        pygame.draw.circle(surf, (255, 110, 60), (8, 8), 1)
    elif b_type == "tank_shell":
        surf = pygame.Surface((14, 20), pygame.SRCALPHA)
        # 敵方戰車燃燒加農砲彈 (烈焰橙紅彈頭與黑煙尾)
        pygame.draw.ellipse(surf, (255, 50, 20), (2, 0, 10, 18))
        pygame.draw.ellipse(surf, (255, 190, 40), (4, 2, 6, 12))
        pygame.draw.circle(surf, (50, 45, 45), (7, 17), 2)
    elif b_type == "boss_heavy_bullet":
        surf = pygame.Surface((22, 22), pygame.SRCALPHA)
        # BOSS 巨型紫紅毀滅重彈
        pygame.draw.circle(surf, (220, 20, 140, 120), (11, 11), 10)
        pygame.draw.circle(surf, (210, 30, 240), (11, 11), 8)
        pygame.draw.circle(surf, (255, 160, 240), (11, 11), 5)
        pygame.draw.circle(surf, COLOR_WHITE, (11, 11), 2)
    elif b_type == "boss_laser":
        surf = pygame.Surface((14, 38), pygame.SRCALPHA)
        # BOSS 猩紅連發重型光束
        pygame.draw.rect(surf, (255, 30, 70), (2, 0, 10, 38), border_radius=4)
        pygame.draw.rect(surf, (255, 200, 210), (4, 2, 6, 34), border_radius=2)
    else:
        surf = pygame.Surface((12, 12), pygame.SRCALPHA)
        pygame.draw.circle(surf, (255, 40, 40), (6, 6), 5)

    return SpriteCache.set(key, surf)


def prewarm_all_sprites():
    """
    事先完成所有敵方戰車、軍艦、戰機與武器圖像快取 (Pre-render and Cache All Sprites)
    保證遊戲運行時 100% 零卡頓、零延遲，外觀精緻且多彩
    """
    # 1. 預先產生戰車各角度與動態履帶精靈圖
    for angle in range(0, 360, 15):
        for frame in range(4):
            create_tank_sprite(angle, frame)

    # 2. 預先產生各式精緻多彩軍艦圖形
    for s_type in ["cruiser", "battleship", "carrier", "dreadnought", "patrol_boat", "gunboat"]:
        for frame in range(6):
            create_warship_sprite(s_type, frame)

    # 3. 預先產生戰果寶物圖形 (包含全新 L 雷射戰果)
    for p in ['P', 'S', 'B', 'W', 'L']:
        for frame in range(12):
            create_powerup_sprite(p, frame)

    # 4. 預先產生子彈圖形
    for b in ["player_vulcan", "player_wingman_bullet", "player_spread", "player_laser",
              "player_homing_laser", "player_missile", "enemy_bullet", "tank_shell",
              "boss_heavy_bullet", "boss_laser"]:
        for ang in range(0, 360, 30):
            create_bullet_sprite(b, ang)

