"""
1945: 二戰空間（II War Space）
實景高解析度山脈與海景多層視差滾動背景系統 (Realistic Mountain & Ocean Parallax Background Engine)
支援 20 大關卡的主題實景：太平洋破曉群島、珊瑚礁海岸、火山熔岩、冰海峽灣、夜間深海與雷暴積雲
無縫連貫滾動設計：頂底色調平滑過渡，消弭視覺斷裂與接縫
環境共鳴低量浮雲層：雲朵量精簡為 3 朵，外觀與陰影色調自動依關卡氛圍融合
提供陸地海岸判別介面，供地面戰車巡邏與作戰部署
"""

import os
import math
import random
import pygame
from game.config import SCREEN_WIDTH, SCREEN_HEIGHT

class BackgroundManager:
    # 靜態快取載入的實景圖像，避免切換關卡時重複讀取磁碟
    _image_cache = {}

    # 支援同一關卡情境下多張頂視實景圖平順串接 (Part 1 + Part 2 連貫推進)
    THEME_SEGMENTS_MAP = {
        "ocean_dawn": ["bg_dawn_seg1.jpg", "bg_dawn_seg2.jpg"],
        "coral_reef": ["bg_coral_seg1.jpg", "bg_coral_seg2.jpg"],
        "sunset_coast": ["bg_sunset_seg1.jpg", "bg_sunset_seg2.jpg"],
        "volcano": ["bg_volcano_seg1.jpg", "bg_volcano_seg2.jpg"],
        "blood_moon": ["bg_bloodmoon_seg1.jpg", "bg_bloodmoon_seg2.jpg"],
        "desert": ["bg_desert_seg1.jpg", "bg_desert_seg2.jpg"],
        "jungle": ["bg_jungle_seg1.jpg", "bg_jungle_seg2.jpg"],
        "arctic_ice": ["bg_arctic_seg1.jpg", "bg_arctic_seg2.jpg"],
        "night_ocean": ["bg_night_seg1.jpg", "bg_night_seg2.jpg"],
        "thunderstorm": ["bg_storm_seg1.jpg", "bg_storm_seg2.jpg"],
        "aurora": ["bg_aurora_seg1.jpg", "bg_aurora_seg2.jpg"],
        "industrial": ["bg_industrial_seg1.jpg", "bg_industrial_seg2.jpg"],
        "stratosphere": ["bg_stratosphere_seg1.jpg", "bg_stratosphere_seg2.jpg"]
    }

    THEME_IMAGE_MAP = {
        "ocean_dawn": "bg_mountain_sea_dawn.jpg",
        "coral_reef": "bg_mountain_coastal.jpg",
        "sunset_coast": "bg_sunset_coast.jpg",
        "volcano": "bg_volcano_ocean.jpg",
        "blood_moon": "bg_blood_moon.jpg",
        "desert": "bg_desert_canyon.jpg",
        "jungle": "bg_jungle_fortress.jpg",
        "arctic_ice": "bg_arctic_ice.jpg",
        "night_ocean": "bg_night_ocean.jpg",
        "thunderstorm": "bg_thunderstorm.jpg",
        "aurora": "bg_aurora_fjord.jpg",
        "industrial": "bg_industrial_iron.jpg",
        "stratosphere": "bg_stratosphere_abyss.jpg"
    }

    THEME_TINT_MAP = {
        "ocean_dawn": (255, 240, 210, 15),     # 破曉晨曦微金光
        "coral_reef": (40, 200, 220, 25),      # 翡翠藍碧海色
        "sunset_coast": (255, 120, 40, 45),    # 夕陽晚霞橙紅光
        "volcano": (255, 50, 10, 50),          # 火山赤熱火光
        "blood_moon": (220, 20, 30, 65),       # 血月猩紅氣息
        "desert": (240, 200, 130, 35),         # 荒漠沙暴琥珀光
        "jungle": (30, 160, 60, 30),           # 熱帶雨林翠綠氛圍
        "arctic_ice": (160, 220, 255, 30),     # 極地冷冽藍霜
        "night_ocean": (10, 15, 35, 75),       # 午夜幽深深藍夜幕
        "thunderstorm": (30, 35, 55, 90),      # 雷暴陰鬱積雨雲黑調
        "aurora": (20, 180, 120, 40),          # 極光流轉碧綠光輝
        "industrial": (60, 65, 75, 45),        # 鋼鐵重工業煙嵐
        "stratosphere": (80, 140, 240, 30)     # 高空平流層湛藍
    }

    # 各主題海域基準底色 (用於頂底無縫過渡消弭斷裂接縫)
    THEME_BASE_SEA = {
        "ocean_dawn": (22, 58, 96),
        "coral_reef": (16, 75, 115),
        "sunset_coast": (42, 48, 82),
        "volcano": (26, 22, 38),
        "blood_moon": (38, 18, 28),
        "desert": (30, 65, 95),
        "jungle": (18, 62, 88),
        "arctic_ice": (42, 78, 112),
        "night_ocean": (8, 16, 32),
        "thunderstorm": (18, 22, 36),
        "aurora": (14, 32, 48),
        "industrial": (25, 35, 45),
        "stratosphere": (20, 50, 100)
    }

    # 與背景主題搭調之雲朵色系與陰影氛圍
    THEME_CLOUD_TINT_MAP = {
        "ocean_dawn": {"cloud": (255, 246, 230), "shadow": (35, 50, 75), "alpha": 65},
        "coral_reef": {"cloud": (242, 252, 255), "shadow": (20, 60, 95), "alpha": 70},
        "sunset_coast": {"cloud": (255, 215, 185), "shadow": (65, 35, 45), "alpha": 75},
        "volcano": {"cloud": (195, 175, 170), "shadow": (45, 22, 25), "alpha": 60},
        "blood_moon": {"cloud": (180, 140, 150), "shadow": (55, 18, 28), "alpha": 65},
        "desert": {"cloud": (252, 240, 220), "shadow": (75, 60, 40), "alpha": 65},
        "jungle": {"cloud": (238, 252, 242), "shadow": (28, 60, 40), "alpha": 70},
        "arctic_ice": {"cloud": (235, 250, 255), "shadow": (38, 65, 90), "alpha": 70},
        "night_ocean": {"cloud": (85, 105, 145), "shadow": (12, 18, 32), "alpha": 50},
        "thunderstorm": {"cloud": (75, 80, 105), "shadow": (15, 18, 28), "alpha": 75},
        "aurora": {"cloud": (115, 175, 155), "shadow": (16, 38, 38), "alpha": 55},
        "industrial": {"cloud": (125, 130, 140), "shadow": (32, 36, 42), "alpha": 60},
        "stratosphere": {"cloud": (248, 252, 255), "shadow": (32, 55, 95), "alpha": 65}
    }

    def __init__(self, theme="ocean_dawn", stage_idx=None, bg_images=None):
        self.theme = theme
        self.stage_idx = stage_idx
        self.bg_images = bg_images
        self.scroll_y_scenic = 0.0
        self.scroll_y_waves = 0.0
        self.scroll_y_clouds = 0.0
        self.scroll_speed = 55.0  # 實景滾動基準速度
        self.scroll_speed_mult = 1.0  # 戰機向前推進時動態加速倍率

        self.lightning_timer = 0.0
        self.lightning_alpha = 0

        # 動態高空浮雲層：精簡為 3 朵，視野開闊清爽，與背景調和不遮蔽彈幕
        self.clouds = []
        for _ in range(3):
            self.clouds.append({
                'x': random.randint(-20, SCREEN_WIDTH - 120),
                'y': random.randint(-150, SCREEN_HEIGHT * 2),
                'width': random.randint(180, 280),
                'height': random.randint(70, 105),
                'alpha': random.randint(45, 75),
                'speed': random.uniform(1.2, 1.8)
            })

        # 動態水面波光亮點
        self.wave_glints = []
        for _ in range(30):
            self.wave_glints.append({
                'x': random.randint(0, SCREEN_WIDTH),
                'y': random.randint(0, SCREEN_HEIGHT),
                'length': random.randint(15, 40),
                'speed': random.uniform(0.8, 1.2),
                'phase': random.uniform(0, math.pi * 2)
            })

        self.scenic_surfs = []
        self.scenic_surf = None
        self._load_theme_surface()

    def _get_asset_path(self, filename):
        """解析資源路徑，相容本機開發、Docker 容器與專案子目錄 (含 100 張山海實景庫)"""
        base_dirs = [
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "backgrounds"),
            os.path.join(os.getcwd(), "assets", "backgrounds"),
            os.path.join(os.getcwd(), "game1", "assets", "backgrounds"),
            "/app/assets/backgrounds",
        ]
        candidates = []
        for bd in base_dirs:
            candidates.append(os.path.join(bd, "scenic_100", filename))
            candidates.append(os.path.join(bd, filename))

        for p in candidates:
            if os.path.exists(p):
                return p
        return None

    @classmethod
    def get_scenic_100_filenames(cls):
        """傳回已生成之 100 張立體實景有山有海頂視背景圖檔名稱清單"""
        return [f"scenic_ms_{i:03d}.jpg" for i in range(1, 101)]

    def _apply_seamless_loop(self, surf):
        """
        將實景底圖上下兩端平滑過渡至海域基準底色，
        保證上下拼接時 row 0 與 row H-1 顏色完全一致，
        徹底消弭縱向循環滾動時的水平硬斷裂與接縫切線！
        """
        w, h = surf.get_size()
        base_color = self.THEME_BASE_SEA.get(self.theme, (20, 55, 95))
        blend_h = min(180, h // 6)

        seamless = surf.copy()
        for i in range(blend_h):
            # 餘弦平滑曲線 (y=0 時 weight=1.0 全純海色，y=blend_h 時 weight=0.0 原圖)
            factor = 1.0 - (0.5 - 0.5 * math.cos(math.pi * i / float(blend_h)))
            alpha = int(255 * factor)
            if alpha <= 0:
                continue

            line_surf = pygame.Surface((w, 1), pygame.SRCALPHA)
            line_surf.fill((*base_color, alpha))

            # 頂部過渡
            seamless.blit(line_surf, (0, i))
            # 底部過渡
            seamless.blit(line_surf, (0, h - 1 - i))

        return seamless

    def _load_single_surface(self, filename):
        """載入單張立體實景頂視圖或超長縱向長卷 (支援 960x10240 與 960x1024)，並施加邊界無縫平滑處理"""
        if filename in BackgroundManager._image_cache:
            return BackgroundManager._image_cache[filename]

        file_path = self._get_asset_path(filename)
        if file_path and os.path.exists(file_path):
            try:
                raw_surf = pygame.image.load(file_path)
                orig_w, orig_h = raw_surf.get_size()
                if orig_w == SCREEN_WIDTH:
                    scaled = raw_surf
                else:
                    target_h = int(orig_h * (SCREEN_WIDTH / float(orig_w)))
                    scaled = pygame.transform.smoothscale(raw_surf, (SCREEN_WIDTH, target_h))
                seamless_surf = self._apply_seamless_loop(scaled)
                BackgroundManager._image_cache[filename] = seamless_surf
                return seamless_surf
            except Exception:
                pass
        return None

    def _load_theme_surface(self):
        """載入對應主題或關卡的多張頂視立體實景照片（每關 5 張連貫平順串接，共 100 張純真實景頂視圖）"""
        loaded_surfs = []

        # 1. 優先使用關卡指定之 960x10240 超長立體實景圖清單 (bg_images)
        if getattr(self, 'bg_images', None):
            for fname in self.bg_images:
                surf = self._load_single_surface(fname)
                if surf:
                    loaded_surfs.append(surf)

        # 2. 優先使用 100 張 Google Gemini Banana 實景山海頂視圖庫 (20 關 x 5 張 = 100 張連貫平順串接)
        if not loaded_surfs and getattr(self, 'stage_idx', None) is not None:
            stage_num = int(self.stage_idx) % 20
            start_num = stage_num * 5 + 1
            stage_files = [f"scenic_ms_{start_num + i:03d}.jpg" for i in range(5)]
            for fname in stage_files:
                surf = self._load_single_surface(fname)
                if surf:
                    loaded_surfs.append(surf)

        # 3. 次選：若未指定 stage_idx 或載入不足，使用 THEME_SEGMENTS_MAP
        if not loaded_surfs:
            seg_names = self.THEME_SEGMENTS_MAP.get(self.theme, [])
            for name in seg_names:
                surf = self._load_single_surface(name)
                if surf:
                    loaded_surfs.append(surf)

        # 4. 若未成功載入多段，則嘗試傳統單圖映射
        if not loaded_surfs:
            fallback_name = self.THEME_IMAGE_MAP.get(self.theme, "bg_mountain_sea_dawn.jpg")
            surf = self._load_single_surface(fallback_name)
            if surf:
                loaded_surfs.append(surf)

        # 5. 若無圖檔，使用程序化備用底圖
        if not loaded_surfs:
            procedural = self._create_procedural_fallback_surface()
            loaded_surfs.append(procedural)

        self.scenic_surfs = loaded_surfs
        self.scenic_surf = loaded_surfs[0]

    def _create_procedural_fallback_surface(self):
        """備用高質感實景山海地形圖 (960x1024，保證上下端週期性無縫銜接，零拼接硬切)"""
        h = SCREEN_HEIGHT
        surf = pygame.Surface((SCREEN_WIDTH, h))
        base_color = self.THEME_BASE_SEA.get(self.theme, (20, 55, 95))

        # 蔚藍至深海漸層 (使用正弦函數確保 y=0 與 y=h-1 完全銜接無縫)
        for y in range(h):
            angle = (y / float(h)) * 2.0 * math.pi
            r = int(base_color[0] + 15 * math.sin(angle))
            g = int(base_color[1] + 25 * math.cos(angle))
            b = int(base_color[2] + 20 * math.sin(angle))
            r = max(0, min(255, r))
            g = max(0, min(255, g))
            b = max(0, min(255, b))
            pygame.draw.line(surf, (r, g, b), (0, y), (SCREEN_WIDTH, y))

        # 兩側防禦海岸地形與中央要塞島礁
        mountain_color = (45, 85, 55)
        sand_color = (225, 210, 155)

        # 1. 左側沿海陸地帶 (0 ~ 180)
        left_pts = [(0, 0)]
        for y in range(0, h + 20, 20):
            w_span = int(115 + 35 * math.sin((y / float(h)) * 2.0 * math.pi * 2))
            left_pts.append((w_span, y))
        left_pts.append((0, h))
        pygame.draw.polygon(surf, sand_color, [(px + 10, py) for px, py in left_pts])
        pygame.draw.polygon(surf, mountain_color, left_pts)

        # 2. 右側沿海群島陸地帶 (780 ~ 960)
        right_pts = [(SCREEN_WIDTH, 0)]
        for y in range(0, h + 20, 20):
            w_span = int(SCREEN_WIDTH - (115 + 35 * math.cos((y / float(h)) * 2.0 * math.pi * 2)))
            right_pts.append((w_span, y))
        right_pts.append((SCREEN_WIDTH, h))
        pygame.draw.polygon(surf, sand_color, [(px - 10, py) for px, py in right_pts])
        pygame.draw.polygon(surf, mountain_color, right_pts)

        # 3. 中央陸地陣地與島嶼走廊 (Middle Land: 380 ~ 580，供中間敵方戰車巡邏作戰)
        mid_x = SCREEN_WIDTH // 2
        mid_pts_left = []
        mid_pts_right = []
        for y in range(0, h + 20, 20):
            span = int(80 + 18 * math.sin((y / float(h)) * 2.0 * math.pi * 3))
            mid_pts_left.append((mid_x - span, y))
            mid_pts_right.append((mid_x + span, y))
        mid_pts = mid_pts_left + list(reversed(mid_pts_right))
        pygame.draw.polygon(surf, sand_color, mid_pts)
        inner_pts = []
        for px, py in mid_pts_left:
            inner_pts.append((px + 8, py))
        for px, py in reversed(mid_pts_right):
            inner_pts.append((px - 8, py))
        pygame.draw.polygon(surf, mountain_color, inner_pts)

        # 頂底端平滑消隱以徹底保證無縫
        return self._apply_seamless_loop(surf)

    def is_land_position(self, x, y=None):
        """
        判定特定座標是否位於陸地/海岸防禦陣地上
        嚴格規則：戰車只能在陸地上出現，在海上出現戰車是錯誤的！
        陸地區域包含：
        1. 左側防禦海岸陣地: 0 <= x <= 180
        2. 中央島嶼要塞走廊 (Middle Land): 380 <= x <= 580
        3. 右側防禦海岸陣地: 780 <= x <= SCREEN_WIDTH
        """
        x_val = float(x)
        if (0 <= x_val <= 180) or (380 <= x_val <= 580) or (780 <= x_val <= SCREEN_WIDTH):
            return True
        return False

    def is_sea_position(self, x, y=None):
        """
        判定特定座標是否位於深海航道上
        嚴格規則：敵方戰艦一定只能在海上出現，在陸上出現戰艦是錯誤的！
        海域航道包含：
        1. 西翼深海作戰航道 (Sea Lane 1): 180 < x < 380
        2. 東翼深海作戰航道 (Sea Lane 2): 580 < x < 780
        """
        x_val = float(x)
        if (180 < x_val < 380) or (580 < x_val < 780):
            return True
        return False

    def set_theme(self, theme, stage_idx=None, bg_images=None):
        """切換關卡主題背景與立體實景圖組"""
        need_reload = (self.theme != theme)
        if stage_idx is not None and getattr(self, 'stage_idx', None) != stage_idx:
            self.stage_idx = stage_idx
            need_reload = True
        if bg_images is not None:
            self.bg_images = bg_images
            need_reload = True
        self.theme = theme
        if need_reload:
            self._load_theme_surface()

    def update(self, dt):
        """滾動與環境特效推進 (支援戰機往前推進時畫面加速滾動)"""
        eff_mult = getattr(self, 'scroll_speed_mult', 1.0)
        self.scroll_y_scenic += self.scroll_speed * eff_mult * dt
        self.scroll_y_waves += 75.0 * eff_mult * dt
        self.scroll_y_clouds += 100.0 * eff_mult * dt

        # 雷暴主題閃電效果
        if self.theme == "thunderstorm":
            self.lightning_timer -= dt
            if self.lightning_timer <= 0:
                if random.random() < 0.06:
                    self.lightning_alpha = random.randint(180, 255)
                    self.lightning_timer = random.uniform(2.0, 5.0)
            if self.lightning_alpha > 0:
                self.lightning_alpha = max(0, self.lightning_alpha - int(850 * dt))

    def draw(self, surf):
        """繪製實景山脈海景與層次感豐富的多重視差 (徹底去除橫條紋)"""
        # 1. 繪製連續無縫多段實景頂視底圖 (Part 1 + Part 2 多張同一情境平順連貫串接)
        if self.scenic_surfs:
            num_segs = len(self.scenic_surfs)
            seg_h = self.scenic_surfs[0].get_height()
            total_cycle_h = num_segs * seg_h
            scroll_pos = int(self.scroll_y_scenic) % total_cycle_h

            for cycle_offset in [-total_cycle_h, 0, total_cycle_h]:
                for idx, seg_surf in enumerate(self.scenic_surfs):
                    y = scroll_pos + cycle_offset - idx * seg_h
                    if -seg_h < y < SCREEN_HEIGHT:
                        surf.blit(seg_surf, (0, y))
        elif self.scenic_surf:
            img_h = self.scenic_surf.get_height()
            offset_y = int(self.scroll_y_scenic) % img_h
            surf.blit(self.scenic_surf, (0, offset_y - img_h))
            surf.blit(self.scenic_surf, (0, offset_y))
            if offset_y < SCREEN_HEIGHT:
                surf.blit(self.scenic_surf, (0, offset_y + img_h))
        else:
            surf.fill(self.THEME_BASE_SEA.get(self.theme, (15, 60, 105)))

        # 2. 海洋微動柔和自然波光 (全面去除水平橫條紋，使用自然散射星芒亮點)
        wave_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        for wg in self.wave_glints:
            gy = (wg['y'] + self.scroll_y_waves * wg['speed']) % SCREEN_HEIGHT
            gx = wg['x']
            pulse = 0.5 + 0.5 * math.sin(self.scroll_y_waves * 0.05 + wg['phase'])
            alpha = int(40 * pulse)
            if alpha > 5:
                # 以圓形微暈光芒取代水平橫條線，絕無橫條紋干擾
                pygame.draw.circle(wave_surf, (255, 255, 255, alpha), (int(gx), int(gy)), 3)
        surf.blit(wave_surf, (0, 0))

        # 3. 關卡專屬大氣濾鏡色調 (Atmospheric Lighting Filter)
        tint = self.THEME_TINT_MAP.get(self.theme, (255, 255, 255, 0))
        if tint[3] > 0:
            tint_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            tint_overlay.fill(tint)
            surf.blit(tint_overlay, (0, 0))

        # 4. 高空半透明浮雲層與地面柔和雲影 (與背景色調完美搭調，數量精簡為 3 朵)
        cloud_cfg = self.THEME_CLOUD_TINT_MAP.get(self.theme, {
            "cloud": (250, 250, 255), "shadow": (30, 45, 65), "alpha": 65
        })
        cloud_rgb = cloud_cfg["cloud"]
        shadow_rgb = cloud_cfg["shadow"]
        base_cloud_alpha = cloud_cfg["alpha"]

        for c in self.clouds:
            cy = (c['y'] + self.scroll_y_clouds * c['speed']) % (SCREEN_HEIGHT + 350) - 170
            cx = c['x']
            cw, ch = c['width'], c['height']

            # 地面柔和半透明雲影 (柔美貼合地形，不顯生硬)
            shadow_surf = pygame.Surface((cw, ch), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow_surf, (*shadow_rgb, 30), (0, 0, cw, ch))
            surf.blit(shadow_surf, (cx + 35, cy + 50))

            # 主雲朵體：羽化立體層疊
            cloud_surf = pygame.Surface((cw, ch), pygame.SRCALPHA)
            # 外層薄氣溶膠霧暈
            pygame.draw.ellipse(cloud_surf, (*cloud_rgb, int(base_cloud_alpha * 0.6)), (0, 0, cw, ch))
            # 次外層
            pygame.draw.ellipse(cloud_surf, (*cloud_rgb, base_cloud_alpha),
                                (int(cw * 0.1), int(ch * 0.1), int(cw * 0.8), int(ch * 0.8)))
            # 核心亮光雲朵
            core_alpha = min(255, base_cloud_alpha + 45)
            pygame.draw.ellipse(cloud_surf, (min(255, cloud_rgb[0] + 15), min(255, cloud_rgb[1] + 15), min(255, cloud_rgb[2] + 15), core_alpha),
                                (int(cw * 0.22), int(ch * 0.18), int(cw * 0.56), int(ch * 0.64)))
            surf.blit(cloud_surf, (cx, cy))

        # 5. 極光 / 雷暴閃光特殊層
        if self.theme == "aurora":
            aurora_surf = pygame.Surface((SCREEN_WIDTH, 240), pygame.SRCALPHA)
            for x in range(0, SCREEN_WIDTH, 16):
                ah = int(80 + 50 * math.sin((x + self.scroll_y_scenic) * 0.025))
                pygame.draw.line(aurora_surf, (60, 250, 170, 50), (x, 0), (x, ah), 14)
                pygame.draw.line(aurora_surf, (140, 255, 220, 30), (x + 8, 0), (x + 8, ah - 20), 10)
            surf.blit(aurora_surf, (0, 0))

        if self.lightning_alpha > 0:
            flash = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            flash.fill((235, 245, 255, self.lightning_alpha))
            surf.blit(flash, (0, 0))
