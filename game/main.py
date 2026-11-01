"""
1945: 二戰空間（II War Space）
主遊戲引擎與循環 (Main Game Loop & State Machine)
支援 20 大關卡、4 款戰機選擇、5 次完整生命力、十分之一生命扣除判定、戰果升級、按鍵 Z 特殊技與 GPU/CPU 渲染
"""

import sys
import os
import math
import argparse
import random
import pygame

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game.config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_WIDTH_1P, SCREEN_WIDTH_2P,
    set_screen_width, FPS, TITLE, STAGES_DATA, FIGHTER_TYPES,
    MAX_LIVES, MAX_HP, DAMAGE_PER_HIT
)
from game.player import Player
from game.enemies import Enemy, EnemyTank
from game.bosses import Boss, MidBoss
from game.background import BackgroundManager
from game.particles import ParticleManager
from game.audio import SoundManager
from game.ui import UIManager
from game.fleet import NavalFleetManager
from game.sprites import prewarm_all_sprites
from game.weapons import Bullet, PowerUp

# 遊戲狀態定義
STATE_MODE_SELECT = "mode_select"
STATE_SELECT = "select"
STATE_PLANE_SELECT_2P = "plane_select_2p"
STATE_PLAYING = "playing"
STATE_BOSS_WARNING = "boss_warning"
STATE_STAGE_CLEAR = "stage_clear"
STATE_GAME_OVER = "game_over"
STATE_VICTORY = "victory"
STATE_PAUSED = "paused"

# SDL2 實體鍵盤掃描碼 (Scancode) 映射表：即使 Windows 11 中文注音輸入法 (IME) 攔截虛擬鍵碼為 VK_PROCESSKEY (229)，
# 實體 Scancode 仍可 100% 精準還原玩家按下的按鍵！
_SCANCODE_TO_KEY = {}
for _sc_attr, _k_attr in [
    ("KSCAN_UP", "K_UP"),
    ("KSCAN_DOWN", "K_DOWN"),
    ("KSCAN_LEFT", "K_LEFT"),
    ("KSCAN_RIGHT", "K_RIGHT"),
    ("KSCAN_KP8", "K_KP8"),
    ("KSCAN_KP2", "K_KP2"),
    ("KSCAN_KP4", "K_KP4"),
    ("KSCAN_KP6", "K_KP6"),
    ("KSCAN_KP0", "K_KP0"),
    ("KSCAN_W", "K_w"),
    ("KSCAN_A", "K_a"),
    ("KSCAN_S", "K_s"),
    ("KSCAN_D", "K_d"),
    ("KSCAN_X", "K_x"),
    ("KSCAN_M", "K_m"),
    ("KSCAN_J", "K_j"),
    ("KSCAN_V", "K_v"),
    ("KSCAN_B", "K_b"),
    ("KSCAN_Z", "K_z"),
    ("KSCAN_N", "K_n"),
    ("KSCAN_C", "K_c"),
    ("KSCAN_Y", "K_y"),
    ("KSCAN_P", "K_p"),
    ("KSCAN_SPACE", "K_SPACE"),
    ("KSCAN_RETURN", "K_RETURN"),
    ("KSCAN_KP_ENTER", "K_RETURN"),
    ("KSCAN_ESCAPE", "K_ESCAPE"),
    ("KSCAN_F11", "K_F11"),
    ("KSCAN_LCTRL", "K_LCTRL"),
    ("KSCAN_RCTRL", "K_RCTRL"),
]:
    if hasattr(pygame, _sc_attr) and hasattr(pygame, _k_attr):
        _SCANCODE_TO_KEY[getattr(pygame, _sc_attr)] = getattr(pygame, _k_attr)

_KEY_TO_SCANCODE = {v: k for k, v in _SCANCODE_TO_KEY.items()}

# Windows Win32 硬體虛擬鍵碼 (VK_*) 映射表：供 GetAsyncKeyState 直接向 Windows 核心查詢實體按鍵狀態，
# 徹底繞過 Windows 11 注音/中文輸入法緩衝區與訊息佇列延遲
_KEY_TO_WIN32_VK = {
    pygame.K_UP: 0x26,      # VK_UP
    pygame.K_DOWN: 0x28,    # VK_DOWN
    pygame.K_LEFT: 0x25,    # VK_LEFT
    pygame.K_RIGHT: 0x27,   # VK_RIGHT
    pygame.K_KP8: 0x68,     # VK_NUMPAD8
    pygame.K_KP2: 0x62,     # VK_NUMPAD2
    pygame.K_KP4: 0x64,     # VK_NUMPAD4
    pygame.K_KP6: 0x66,     # VK_NUMPAD6
    pygame.K_KP0: 0x60,     # VK_NUMPAD0
    pygame.K_SPACE: 0x20,   # VK_SPACE
    pygame.K_RETURN: 0x0D,  # VK_RETURN
    pygame.K_ESCAPE: 0x1B,  # VK_ESCAPE
    pygame.K_F11: 0x7A,     # VK_F11
    pygame.K_LCTRL: 0xA2,   # VK_LCONTROL
    pygame.K_RCTRL: 0xA3,   # VK_RCONTROL
    pygame.K_m: 0x4D,       # 'M'
    pygame.K_j: 0x4A,       # 'J'
    pygame.K_z: 0x5A,       # 'Z'
    pygame.K_n: 0x4E,       # 'N'
    pygame.K_w: 0x57,       # 'W'
    pygame.K_a: 0x41,       # 'A'
    pygame.K_s: 0x53,       # 'S'
    pygame.K_d: 0x44,       # 'D'
    pygame.K_x: 0x58,       # 'X'
    pygame.K_v: 0x56,       # 'V'
    pygame.K_b: 0x42,       # 'B'
    pygame.K_c: 0x43,       # 'C'
    pygame.K_y: 0x59,       # 'Y'
    pygame.K_p: 0x50,       # 'P'
}


class HybridKeyState:
    """
    整合 Pygame get_pressed()、SDL2 實體 Scancode、事件佇列狀態與 Windows 11 GetAsyncKeyState 硬體輪詢之複合按鍵讀取器。
    確保在 Windows 11 預設開啟中文注音輸入法 (IME) 時，射擊鍵 (M / V / Space) 與方向鍵 (↑↓←→ / WXAD) 100% 即時靈敏反應。
    """
    def __init__(self, raw_keys, held_keys, win32_down):
        self.raw_keys = raw_keys
        self.held_keys = held_keys
        self.win32_down = win32_down

    def __getitem__(self, k):
        if k in self.win32_down or k in self.held_keys:
            return True
        if self.raw_keys is not None:
            try:
                if self.raw_keys[k]:
                    return True
            except (KeyError, IndexError, TypeError):
                pass
            sc = _KEY_TO_SCANCODE.get(k)
            if sc is not None:
                try:
                    if self.raw_keys[sc]:
                        return True
                except (KeyError, IndexError, TypeError):
                    pass
        return False

class Game:
    def __init__(self, start_stage=1, default_plane_idx=0, headless=False, cpu_mode=False, fullscreen=False, num_players=1, p2_plane_idx=1):
        self.headless = headless
        self.cpu_mode = cpu_mode
        self.fullscreen = fullscreen
        self.num_players = num_players
        self.selected_mode = 0 if num_players == 1 else 1
        self.selected_plane_idx = default_plane_idx
        self.p1_plane_idx = default_plane_idx
        self.p2_plane_idx = p2_plane_idx if p2_plane_idx != default_plane_idx else (default_plane_idx + 1) % len(FIGHTER_TYPES)
        self.selecting_player = 1
        self.current_stage_idx = max(0, min(19, start_stage - 1))

        # 【核心規則】：當選擇為 2 人時背景以 1024*10240 模式執行，選擇 1 人時以 960*10240 模式執行
        self.screen_width = SCREEN_WIDTH_2P if self.num_players == 2 else SCREEN_WIDTH_1P
        self.screen_height = SCREEN_HEIGHT
        set_screen_width(self.screen_width)

        # 初始化 Pygame (相容 Windows 11 高 DPI、自動關閉中文輸入法 IME 攔截與 1ms 高精度計時器)
        if self.headless:
            os.environ["SDL_VIDEODRIVER"] = "dummy"
            os.environ["SDL_AUDIODRIVER"] = "dummy"
        else:
            os.environ.setdefault("SDL_VIDEO_CENTERED", "1")
            os.environ["SDL_IME_SHOW_UI"] = "0"
            if os.name == "nt":
                try:
                    import ctypes
                    # 1. 提升 Windows 11 系統排程與計時器精度至 1ms (消除 15.6ms 睡眠抖動導致移動不順)
                    try:
                        ctypes.windll.winmm.timeBeginPeriod(1)
                    except Exception:
                        pass
                    # 2. 全域停用本遊戲處理序之 Windows 11 中文輸入法 (IME)，防止注音攔截 M/V/Z/WASD 與方向鍵
                    try:
                        ctypes.windll.imm32.ImmDisableIME(0xFFFFFFFF)
                    except Exception:
                        pass
                    # 3. 啟用 Windows 11 高 DPI 感知
                    try:
                        ctypes.windll.shcore.SetProcessDpiAwareness(2)
                    except Exception:
                        ctypes.windll.user32.SetProcessDPIAware()
                except Exception:
                    pass
            if self.cpu_mode:
                # 強制 CPU 軟體渲染相容模式 (Mesa llvmpipe / Windows Software Renderer)
                os.environ["LIBGL_ALWAYS_SOFTWARE"] = "1"
                os.environ["SDL_RENDER_DRIVER"] = "software"

        try:
            pygame.mixer.pre_init(22050, -16, 2, 512)
        except Exception:
            pass
        pygame.init()
        pygame.display.set_caption(TITLE)

        # 輸入狀態追蹤與單擊射擊緩衝 (解決快速點按射擊鍵或 Windows 11 IME 吃鍵問題)
        self._held_keys = set()
        self._prev_win32_down = set()
        self._p1_shoot_latch = False
        self._p2_shoot_latch = False

        self.screen = self._init_display_surface()
        self.clock = pygame.time.Clock()
        self.running = True

        # 核心管理器
        self.sound_mgr = SoundManager.get_instance()
        self.ui_mgr = UIManager()
        self.particle_mgr = ParticleManager()
        stage_data = STAGES_DATA[self.current_stage_idx]
        self.bg_mgr = BackgroundManager(
            stage_data["bg_theme"],
            stage_idx=self.current_stage_idx,
            bg_images=stage_data.get("bg_images"),
            screen_width=self.screen_width
        )
        self.fleet_mgr = NavalFleetManager()

        # 遊戲進行中物件 (支援雙玩家與雙魔王)
        self.player = None
        self.player2 = None
        self.enemies = []
        self.midboss = None
        self.midboss_spawned = False
        self.midboss_warning_timer = 0.0
        self.boss = None
        self.bosses = []
        self.player_bullets = []
        self.enemy_bullets = []
        self.powerups = []

        # 遊戲統計與時間
        self.score = 0
        self.high_score = 50000
        self.state = STATE_MODE_SELECT if not self.headless else STATE_PLAYING
        self.state_timer = 0.0
        self.stage_time = 0.0
        self.frame_count = 0
        self.enemy_spawn_timer = 0.0
        self.tank_spawn_timer = random.uniform(2.5, 4.5)
        self.enemies_killed_count = 0
        self.enemy_plane_kill_count = 0  # 統計被擊斃敵機數，每 5 架出現 1 個寶物

        # 事先完成好所有精緻多彩精靈圖 (Pre-render and cache all sprites)
        prewarm_all_sprites()

        # 如果處於測試模式，直接初始化並啟動
        if self.headless:
            self.set_mode(self.num_players)
            self.init_players()
            self.state = STATE_PLAYING
            self.sound_mgr.start_bgm()

    def _disable_ime_and_text_input(self):
        """
        停用 SDL2 文字輸入模式與 Windows 11 中文注音輸入法 (IME) 關聯，
        防止按下 M / V / Z / WASD / 空白鍵 / 方向鍵時被中文輸入法候選字視窗攔截吃鍵！
        """
        try:
            pygame.key.stop_text_input()
        except Exception:
            pass
        if os.name == "nt" and not self.headless:
            try:
                import ctypes
                ctypes.windll.imm32.ImmDisableIME(0xFFFFFFFF)
                wm_info = pygame.display.get_wm_info()
                hwnd = wm_info.get("window")
                if hwnd:
                    ctypes.windll.imm32.ImmAssociateContext(ctypes.c_void_p(hwnd), ctypes.c_void_p(0))
                # 切換當前執行緒鍵盤佈局至美式英文 (0x04090409)，避免注音符號攔截按鍵
                ctypes.windll.user32.ActivateKeyboardLayout(ctypes.c_void_p(0x04090409), 0)
            except Exception:
                pass

    def _init_display_surface(self):
        """建立顯示視窗，使用原生高速雙緩衝 (DOUBLEBUF) 並自動關閉 Windows 11 IME 文字輸入攔截"""
        flags = 0
        if not self.headless:
            flags |= pygame.DOUBLEBUF
            if self.fullscreen:
                flags |= pygame.FULLSCREEN
        try:
            surf = pygame.display.set_mode((self.screen_width, self.screen_height), flags)
        except Exception:
            fallback_flags = pygame.FULLSCREEN if (self.fullscreen and not self.headless) else 0
            surf = pygame.display.set_mode((self.screen_width, self.screen_height), fallback_flags)
        if not self.headless:
            self._disable_ime_and_text_input()
        return surf

    def set_mode(self, num_players):
        """切換 1 人模式 (960*10240) 與 2 人模式 (1024*10240)"""
        self.num_players = num_players
        self.screen_width = SCREEN_WIDTH_2P if num_players == 2 else SCREEN_WIDTH_1P
        set_screen_width(self.screen_width)
        self.screen = self._init_display_surface()
        self.bg_mgr.set_screen_width(self.screen_width)

    def init_players(self):
        """依模式與選擇機型建立玩家戰機"""
        if self.num_players == 2:
            cfg1 = FIGHTER_TYPES[self.p1_plane_idx]
            cfg2 = FIGHTER_TYPES[self.p2_plane_idx]
            self.player = Player(cfg1, player_id=1, screen_width=self.screen_width)
            self.player2 = Player(cfg2, player_id=2, screen_width=self.screen_width)
        else:
            cfg1 = FIGHTER_TYPES[self.selected_plane_idx]
            self.player = Player(cfg1, player_id=1, screen_width=self.screen_width)
            self.player2 = None

    def init_player(self, plane_idx):
        """相容單機介面"""
        self.selected_plane_idx = plane_idx
        self.p1_plane_idx = plane_idx
        self.init_players()

    def get_closest_player(self, x, y):
        """取得距指定座標最近的存活玩家戰機"""
        active = [p for p in [self.player, self.player2] if p and p.alive]
        if not active:
            return self.player or self.player2
        return min(active, key=lambda p: math.hypot(p.x - x, p.y - y))

    def load_stage(self, stage_idx):
        """載入指定關卡"""
        self.current_stage_idx = stage_idx
        stage_data = STAGES_DATA[self.current_stage_idx]
        self.bg_mgr.set_theme(
            stage_data["bg_theme"],
            stage_idx=self.current_stage_idx,
            bg_images=stage_data.get("bg_images")
        )

        # 清除戰場上殘餘的敵機與所有子彈 (杜絕過關子彈停留至下一關背景)
        self.enemies.clear()
        self.boss = None
        self.bosses.clear()
        self.midboss = None
        self.midboss_spawned = False
        self.midboss_warning_timer = 0.0
        self.player_bullets.clear()
        self.enemy_bullets.clear()
        self.stage_time = 0.0
        self.enemy_spawn_timer = 0.0
        self.tank_spawn_timer = random.uniform(2.5, 4.5)
        self.enemies_killed_count = 0
        self.fleet_mgr.reset_for_stage()
        if self.player:
            self.player.fire_timer = 0.0
        if self.player2:
            self.player2.fire_timer = 0.0

    def on_enemy_defeated(self, enemy=None):
        """
        【核心規則】：敵方戰機出現的頻率以被消滅的速度成正比
        消滅得越快，敵機計時器冷卻縮短越多，下一波隨即迅速湧現！
        """
        self.enemies_killed_count += 1
        # 大幅動態縮短刷新間隔
        self.enemy_spawn_timer = max(0.06, self.enemy_spawn_timer - 0.42)

    def spawn_enemies(self, dt):
        """依關卡設定產生豐富敵機編隊、不定時大中小型敵艦、中型大魔王，並大幅增加陸地戰車數量"""
        stage_data = STAGES_DATA[self.current_stage_idx]
        self.enemy_spawn_timer -= dt

        # 1. 觸發中間敵方主力艦隊突入與不定時高頻率敵艦出現 (增加海面上出現戰艦的次數)
        self.fleet_mgr.check_spawn(self.stage_time, stage_data["spawn_duration"], self.current_stage_idx, dt=dt)

        # 2. 觸發關卡中段中型大魔王登場 (【核心規則】：以船艦為主，且需在海面上出現)
        mid_time = stage_data.get("midboss_time", 60.0)
        if self.stage_time >= mid_time and self.midboss is None and not self.midboss_spawned:
            self.midboss_spawned = True
            self.midboss = MidBoss(stage_data, self.bg_mgr, screen_width=self.screen_width)
            self.midboss_warning_timer = 3.0
            self.sound_mgr.play("boss_alert")

        # 3. 大幅增加陸地上坦克車出現的數量 (短間隔 + 多輛戰車編隊巡邏)
        self.tank_spawn_timer -= dt
        if self.tank_spawn_timer <= 0:
            self.tank_spawn_timer = random.uniform(2.5, 4.5) * (0.6 if self.num_players == 2 else 1.0)
            t_count = random.choice([1, 2, 2, 3]) * (2 if self.num_players == 2 else 1)
            right_max_x = max(820, self.screen_width - 40)
            for _ in range(t_count):
                tank_x = random.choice([
                    random.randint(400, 560),  # 中間陸地核心陣地
                    random.randint(400, 560),  # 加重中間陸地出現機率
                    random.randint(40, 150),   # 左側海岸防禦陣地
                    random.randint(810, right_max_x)  # 右側海岸防禦陣地 (相容 1P 960 與 2P 1024)
                ])
                if self.bg_mgr.is_land_position(tank_x):
                    self.enemies.append(EnemyTank(
                        tank_x, -35 - random.randint(0, 50),
                        hp=55,
                        speed=random.uniform(0.9, 1.3),
                        bullet_mult=stage_data["bullet_speed_mult"],
                        screen_width=self.screen_width
                    ))

        hp_map = {
            "scout_zero": 25,          # 1 擊潰敗 (或輕微擦彈 2 擊)
            "fast_interceptor": 45,    # 經 1 擊扣 25 滴血剩 20 滴 (機體受損冒黑煙)，第 2 擊立即潰敗！
            "twin_bomber": 48,         # 經 1 擊扣 25 滴剩 23 滴，第 2 擊立即潰敗！
            "heavy_gunship": 85,
            "sea_destroyer": 90
        }

        # 【核心規則】：各型戰機與船艦出現以隨機方式出現，且需有固定比率讓畫面都有敵機出現
        # 4. 固定比率保底敵機機制：2 人模式空中敵機數量保底加倍 (8 架)
        air_enemies = [e for e in self.enemies if not getattr(e, 'is_tank', False) and getattr(e, 'enemy_type', '') != "sea_destroyer"]
        MIN_AIR_ENEMIES_ON_SCREEN = 8 if self.num_players == 2 else 4
        has_boss_active = bool(self.bosses and any(b.alive and not b.is_entering for b in self.bosses))

        if len(air_enemies) < MIN_AIR_ENEMIES_ON_SCREEN and not has_boss_active:
            sup_type = random.choice(["scout_zero", "fast_interceptor", "twin_bomber", "heavy_gunship"])
            # 【核心規則】：敵方可由上下左右出現 (top, bottom, left, right)
            spawn_dir = random.choices(["top", "bottom", "left", "right"], weights=[40, 26, 17, 17])[0]
            if spawn_dir == "bottom":
                sup_pattern = random.choice(["climb_straight", "climb_sine", "climb_swoop_left", "climb_swoop_right", "dive_loop"])
                sx = random.randint(90, self.screen_width - 90)
                sy = SCREEN_HEIGHT + 45 + random.randint(0, 30)
            elif spawn_dir == "left":
                sup_pattern = random.choice(["straight", "sine", "swoop_up", "swoop_down", "dive_loop"])
                sx = -45 - random.randint(0, 30)
                sy = random.randint(120, SCREEN_HEIGHT - 220)
            elif spawn_dir == "right":
                sup_pattern = random.choice(["straight", "sine", "swoop_up", "swoop_down", "dive_loop"])
                sx = self.screen_width + 45 + random.randint(0, 30)
                sy = random.randint(120, SCREEN_HEIGHT - 220)
            else:
                sup_pattern = random.choice(["straight", "sine", "dive_loop", "swoop_left", "swoop_right"])
                sx = random.randint(90, self.screen_width - 90)
                sy = -45 - random.randint(0, 30)

            self.enemies.append(Enemy(
                sx, sy,
                enemy_type=sup_type,
                hp=hp_map.get(sup_type, 25),
                pattern=sup_pattern,
                speed=random.uniform(3.0, 4.2),
                bullet_mult=stage_data["bullet_speed_mult"],
                spawn_direction=spawn_dir,
                screen_width=self.screen_width
            ))

        # 5. 常規敵機波次隨機生成：【核心規則】2人模式敵機數量加倍出現
        if self.enemy_spawn_timer <= 0:
            density = stage_data["enemy_density"]
            rate_factor = 0.5 if self.num_players == 2 else 1.0
            self.enemy_spawn_timer = (random.uniform(1.2, 2.2) / density) * rate_factor

            # 依機率隨機選擇敵機種類與編隊型態
            e_type = random.choices(
                ["scout_zero", "fast_interceptor", "twin_bomber", "heavy_gunship", "sea_destroyer"],
                weights=[42, 28, 16, 8, 6]
            )[0]

            if e_type == "sea_destroyer":
                spawn_dir = "top"
                pattern = "hover"
                spawn_count = 1 if self.num_players == 1 else 2
                base_x = random.choice([random.randint(220, 340), random.randint(620, 740)])
                for i in range(spawn_count):
                    self.enemies.append(Enemy(
                        base_x + i * 80, -50 - i * 40,
                        enemy_type=e_type,
                        hp=hp_map[e_type],
                        pattern=pattern,
                        speed=random.uniform(2.5, 3.5),
                        bullet_mult=stage_data["bullet_speed_mult"],
                        spawn_direction="top",
                        screen_width=self.screen_width
                    ))
            else:
                # 【核心規則】：敵方可由上下左右出現
                spawn_dir = random.choices(["top", "bottom", "left", "right"], weights=[40, 26, 17, 17])[0]
                if spawn_dir == "bottom":
                    pattern = random.choice(["climb_straight", "climb_sine", "climb_swoop_left", "climb_swoop_right", "dive_loop"])
                elif spawn_dir in ["left", "right"]:
                    pattern = random.choice(["straight", "sine", "swoop_up", "swoop_down", "dive_loop"])
                else:
                    pattern = random.choice(["straight", "sine", "dive_loop", "swoop_left", "swoop_right", "hover"])

                # 編隊成行產生 (2人模式數量加倍)
                base_count = 1 if e_type in ["heavy_gunship", "twin_bomber"] else random.randint(1, 3)
                spawn_count = base_count * (2 if self.num_players == 2 else 1)

                if spawn_dir == "left":
                    base_y = random.randint(120, SCREEN_HEIGHT - 220)
                    for i in range(spawn_count):
                        self.enemies.append(Enemy(
                            -40 - i * 40, base_y + (i - (spawn_count - 1) / 2) * 45,
                            enemy_type=e_type,
                            hp=hp_map[e_type],
                            pattern=pattern,
                            speed=random.uniform(2.8, 4.2),
                            bullet_mult=stage_data["bullet_speed_mult"],
                            spawn_direction="left",
                            screen_width=self.screen_width
                        ))
                elif spawn_dir == "right":
                    base_y = random.randint(120, SCREEN_HEIGHT - 220)
                    for i in range(spawn_count):
                        self.enemies.append(Enemy(
                            self.screen_width + 40 + i * 40, base_y + (i - (spawn_count - 1) / 2) * 45,
                            enemy_type=e_type,
                            hp=hp_map[e_type],
                            pattern=pattern,
                            speed=random.uniform(2.8, 4.2),
                            bullet_mult=stage_data["bullet_speed_mult"],
                            spawn_direction="right",
                            screen_width=self.screen_width
                        ))
                elif spawn_dir == "bottom":
                    base_x = random.randint(80, self.screen_width - 80)
                    for i in range(spawn_count):
                        ox = (i - (spawn_count - 1) / 2) * 50
                        spawn_y = SCREEN_HEIGHT + 40 + i * 35
                        self.enemies.append(Enemy(
                            base_x + ox, spawn_y,
                            enemy_type=e_type,
                            hp=hp_map[e_type],
                            pattern=pattern,
                            speed=random.uniform(2.8, 4.2),
                            bullet_mult=stage_data["bullet_speed_mult"],
                            spawn_direction="bottom",
                            screen_width=self.screen_width
                        ))
                else:  # top
                    base_x = random.randint(80, self.screen_width - 80)
                    for i in range(spawn_count):
                        ox = (i - (spawn_count - 1) / 2) * 50
                        spawn_y = -40 - i * 35
                        self.enemies.append(Enemy(
                            base_x + ox, spawn_y,
                            enemy_type=e_type,
                            hp=hp_map[e_type],
                            pattern=pattern,
                            speed=random.uniform(2.8, 4.2),
                            bullet_mult=stage_data["bullet_speed_mult"],
                            spawn_direction="top",
                            screen_width=self.screen_width
                        ))

    def _trigger_tactical_bomb(self, plyr):
        """觸發 [B] 戰術炸彈：清除全畫面敵方彈幕並對畫面內敵軍造成爆破重創"""
        # 1. 清除全畫面敵方彈幕並轉化為火花特效
        for eb in self.enemy_bullets:
            if eb.alive:
                eb.alive = False
                self.particle_mgr.add_bullet_hit(eb.x, eb.y, (255, 220, 120))
        self.enemy_bullets.clear()

        # 2. 全畫面震撼爆破特效與音效
        cx = plyr.x if plyr else self.screen_width // 2
        cy = max(240, (plyr.y - 180) if plyr else SCREEN_HEIGHT // 2)
        self.particle_mgr.add_explosion(cx, cy, scale=3.0)
        self.sound_mgr.play("explosion")

        # 3. 重創畫面內一般敵機與地面戰車
        for e in self.enemies:
            if not e.alive:
                continue
            if -40 <= e.y <= SCREEN_HEIGHT + 40 and -40 <= e.x <= self.screen_width + 40:
                if e.take_damage(120):
                    self.score += e.score
                    self.particle_mgr.add_explosion(e.x, e.y, scale=1.0)
                    if not getattr(e, 'is_tank', False) and getattr(e, 'enemy_type', '') != "sea_destroyer":
                        self.enemy_plane_kill_count += 1
                        if self.enemy_plane_kill_count % 5 == 0:
                            self.powerups.append(PowerUp(e.x, e.y, random.choice(['P', 'S', 'B', 'W', 'L'])))
                    self.powerups.extend(e.spawn_drops())
                    self.on_enemy_defeated(e)

        # 4. 重創海面敵艦隊
        for s in self.fleet_mgr.ships:
            if s.alive and not s.is_sinking and -80 <= s.y <= SCREEN_HEIGHT + 80:
                if s.take_damage(120):
                    self.score += s.score
                    self.particle_mgr.add_explosion(s.x, s.y, scale=2.2)
                    self.powerups.extend(s.spawn_drops())

        # 5. 對中型大魔王與終極大魔王造成戰術轟炸傷害 (受裝甲減免，維持持久戰節奏)
        if self.midboss and self.midboss.alive and not self.midboss.is_entering and not self.midboss.is_defeated:
            if self.midboss.take_damage(180):
                self.score += 8000 + self.current_stage_idx * 500
                self.particle_mgr.add_explosion(self.midboss.x, self.midboss.y, scale=2.8)
                self.powerups.extend(self.midboss.spawn_drops())

        for b_obj in self.bosses:
            if b_obj and b_obj.alive and not b_obj.is_entering and not b_obj.is_defeated:
                if b_obj.take_damage(180):
                    self.score += 5000 + self.current_stage_idx * 1000
                    self.particle_mgr.add_explosion(b_obj.x, b_obj.y, scale=3.5, is_boss=True)
                    self.powerups.extend(b_obj.spawn_drops())
                    if all((not b_item.alive or b_item.is_defeated) for b_item in self.bosses):
                        self.sound_mgr.play("victory")
                        self.state = STATE_STAGE_CLEAR
                        self.state_timer = 4.0
                        self.player_bullets.clear()
                        self.enemy_bullets.clear()

    def _is_in_playfield(self, ent):
        """判定一般敵機或艦艇是否已進入可視戰場範圍 (避免場外待命隊列提前吸收子彈或被鎖定)"""
        margin = getattr(ent, "radius", 24)
        return (-margin <= ent.x <= self.screen_width + margin) and (-margin <= ent.y <= SCREEN_HEIGHT + margin)

    def handle_collisions(self):
        """碰撞檢測與傷害結算 (支援雙玩家、雙大魔王與核心規則)"""
        # 1. 玩家子彈 vs 敵機
        for b in self.player_bullets:
            if not b.alive:
                continue
            for e in self.enemies:
                if not e.alive or not self._is_in_playfield(e):
                    continue
                dist = math.hypot(b.x - e.x, b.y - e.y)
                if dist < b.radius + e.radius:
                    b.alive = False
                    self.particle_mgr.add_bullet_hit(b.x, b.y)
                    is_destroyed = e.take_damage(b.damage)
                    if is_destroyed:
                        self.score += e.score
                        self.particle_mgr.add_explosion(e.x, e.y, scale=1.0)
                        if getattr(e, 'is_tank', False):
                            # EnemyTank.take_damage 已播放 tank_explosion，避免重複疊音
                            pass
                        elif getattr(e, 'enemy_type', '') == "sea_destroyer":
                            self.sound_mgr.play("ship_explosion")
                        else:
                            self.sound_mgr.play("explosion")
                            # 【核心規則】：敵方被擊斃後以隨機方式出現寶物，每5架敵機被擊斃後才出現一個寶物的方式出現
                            self.enemy_plane_kill_count += 1
                            if self.enemy_plane_kill_count % 5 == 0:
                                self.powerups.append(PowerUp(e.x, e.y, random.choice(['P', 'S', 'B', 'W', 'L'])))
                        self.powerups.extend(e.spawn_drops())
                        self.on_enemy_defeated(e)
                    break

            if not b.alive:
                continue

            # 玩家子彈 vs 海面敵主力艦隊 (增加戰場複雜度)
            for s in self.fleet_mgr.ships:
                if not s.alive or s.is_sinking or not self._is_in_playfield(s):
                    continue
                s_dist = math.hypot(b.x - s.x, b.y - s.y)
                if s_dist < b.radius + s.radius:
                    b.alive = False
                    self.particle_mgr.add_bullet_hit(b.x, b.y)
                    is_sunk = s.take_damage(b.damage)
                    if is_sunk:
                        self.score += s.score
                        self.particle_mgr.add_explosion(s.x, s.y, scale=2.5)
                        self.powerups.extend(s.spawn_drops())
                    break

            if not b.alive:
                continue

            # 玩家子彈 vs 中型大魔王 (Mid-Boss)
            if self.midboss and self.midboss.alive and not self.midboss.is_entering:
                mb_dist = math.hypot(b.x - self.midboss.x, b.y - self.midboss.y)
                if mb_dist < b.radius + self.midboss.radius:
                    b.alive = False
                    self.particle_mgr.add_bullet_hit(b.x, b.y)
                    is_mb_dead = self.midboss.take_damage(b.damage)
                    if is_mb_dead:
                        self.score += 8000 + self.current_stage_idx * 500
                        self.particle_mgr.add_explosion(self.midboss.x, self.midboss.y, scale=2.8)
                        self.powerups.extend(self.midboss.spawn_drops())
                    continue

            if not b.alive:
                continue

            # 玩家子彈 vs BOSS (支援最後大魔王兩隻)
            for b_obj in self.bosses:
                if b_obj and b_obj.alive and not b_obj.is_entering and not b_obj.is_defeated:
                    b_dist = math.hypot(b.x - b_obj.x, b.y - b_obj.y)
                    if b_dist < b.radius + b_obj.radius:
                        b.alive = False
                        self.particle_mgr.add_bullet_hit(b.x, b.y)
                        is_boss_dead = b_obj.take_damage(b.damage)
                        if is_boss_dead:
                            self.score += 5000 + self.current_stage_idx * 1000
                            self.particle_mgr.add_explosion(b_obj.x, b_obj.y, scale=3.5, is_boss=True)
                            self.powerups.extend(b_obj.spawn_drops())
                            # 【核心規則】：當兩隻大魔王全部滅亡時，過關結算
                            if all((not b_item.alive or b_item.is_defeated) for b_item in self.bosses):
                                self.sound_mgr.play("victory")
                                self.state = STATE_STAGE_CLEAR
                                self.state_timer = 4.0
                                self.player_bullets.clear()
                                self.enemy_bullets.clear()
                        break

        # 2. 敵方子彈 vs 玩家 (遍歷 P1 與 P2)
        active_players = [p for p in [self.player, self.player2] if p and p.alive]
        for eb in self.enemy_bullets:
            if not eb.alive:
                continue
            for plyr in active_players:
                if not plyr.alive:
                    continue
                p_dist = math.hypot(eb.x - plyr.x, eb.y - plyr.y)
                if p_dist < eb.radius + plyr.radius:
                    eb.alive = False
                    hit_result = plyr.take_hit()
                    if hit_result == True:
                        self.particle_mgr.add_explosion(plyr.x, plyr.y, scale=2.5)
                        self.sound_mgr.play("explosion")
                        # 檢查是否所有玩家均已喪失全部 5 條命
                        if all(p is None or not p.alive for p in [self.player, self.player2]):
                            self.state = STATE_GAME_OVER
                            self.state_timer = 0.0
                    elif hit_result == "damaged":
                        self.particle_mgr.add_bullet_hit(plyr.x, plyr.y, (255, 100, 100))
                    break

        # 3. 玩家 vs 敵機撞擊
        for e in self.enemies:
            if not e.alive:
                continue
            for plyr in active_players:
                if not plyr.alive:
                    continue
                c_dist = math.hypot(plyr.x - e.x, plyr.y - e.y)
                if c_dist < plyr.radius + e.radius:
                    e.take_damage(999)
                    self.particle_mgr.add_explosion(e.x, e.y, scale=1.2)
                    if not getattr(e, 'is_tank', False):
                        self.sound_mgr.play("ship_explosion" if getattr(e, 'enemy_type', '') == "sea_destroyer" else "explosion")
                    if not getattr(e, 'is_tank', False) and getattr(e, 'enemy_type', '') != "sea_destroyer":
                        self.enemy_plane_kill_count += 1
                        if self.enemy_plane_kill_count % 5 == 0:
                            self.powerups.append(PowerUp(e.x, e.y, random.choice(['P', 'S', 'B', 'W', 'L'])))
                    self.on_enemy_defeated(e)
                    hit_res = plyr.take_hit()
                    if hit_res == True:
                        self.particle_mgr.add_explosion(plyr.x, plyr.y, scale=2.5)
                        if all(p is None or not p.alive for p in [self.player, self.player2]):
                            self.state = STATE_GAME_OVER
                    break

        # 4. 玩家 vs 戰果拾取
        for p in self.powerups:
            if not p.alive:
                continue
            for plyr in active_players:
                if not plyr.alive:
                    continue
                u_dist = math.hypot(plyr.x - p.x, plyr.y - p.y)
                if u_dist < plyr.radius + p.radius:
                    p.alive = False
                    self.score += 500
                    plyr.apply_powerup(p.type)
                    if p.type == "B":
                        self._trigger_tactical_bomb(plyr)
                    self.particle_mgr.add_bullet_hit(p.x, p.y, (100, 255, 200))
                    break

    def update(self, dt):
        """核心遊戲狀態更新"""
        if self.state == STATE_PAUSED:
            return

        self.frame_count += 1
        self.bg_mgr.update(dt)
        self.particle_mgr.update(dt)

        if self.state in [STATE_MODE_SELECT, STATE_SELECT, STATE_PLANE_SELECT_2P]:
            return

        if self.state in [STATE_PLAYING, STATE_BOSS_WARNING]:
            self.stage_time += dt
            stage_data = STAGES_DATA[self.current_stage_idx]

            # 戰機更新 (支援雙玩家)
            if self.player and self.player.alive:
                self.player.update(dt)
            if self.player2 and self.player2.alive:
                self.player2.update(dt)

            # BOSS 出現判斷：【核心規則】最後的大魔王需有兩隻
            if self.stage_time >= stage_data["spawn_duration"] and not self.bosses:
                self.state = STATE_BOSS_WARNING
                self.state_timer = 2.5
                self.sound_mgr.play("boss_alert")
                if self.num_players == 2:
                    # 雙魔王登場：Boss 1 與 Boss 2 分列左右
                    b1 = Boss(stage_data, boss_id=1, offset_x=-80, screen_width=self.screen_width)
                    b2 = Boss(stage_data, boss_id=2, offset_x=80, screen_width=self.screen_width)
                    self.bosses = [b1, b2]
                    self.boss = b1
                else:
                    b1 = Boss(stage_data, boss_id=1, offset_x=0, screen_width=self.screen_width)
                    self.bosses = [b1]
                    self.boss = b1

            # 警告倒數結束後進入 BOSS 戰
            if self.state == STATE_BOSS_WARNING:
                self.state_timer -= dt
                if self.state_timer <= 0:
                    self.state = STATE_PLAYING

            # 產生敵機 (BOSS 未出線前或戰況中定期增援)
            if not self.bosses or any(b.is_entering for b in self.bosses):
                self.spawn_enemies(dt)

            # 更新敵機 (坦克在陸地上推進，遇到海面邊界停在該處)
            for e in self.enemies:
                p_close = self.get_closest_player(e.x, e.y)
                p_pos = (p_close.x, p_close.y) if p_close else (self.screen_width // 2, SCREEN_HEIGHT - 100)
                if hasattr(e, 'is_tank'):
                    e.update(dt, p_pos, self.bg_mgr)
                else:
                    e.update(dt)
                if e.alive:
                    new_b = e.check_shoot(dt, p_pos)
                    self.enemy_bullets.extend(new_b)

            # 更新海面敵主力艦隊 (艦砲齊射與航母艦載機起飛)
            p_ref = self.get_closest_player(self.screen_width // 2, SCREEN_HEIGHT - 100)
            p_ref_pos = (p_ref.x, p_ref.y) if p_ref else (self.screen_width // 2, SCREEN_HEIGHT - 100)
            fleet_bullets, fleet_planes = self.fleet_mgr.update(dt, p_ref_pos)
            self.enemy_bullets.extend(fleet_bullets)
            for fp in fleet_planes:
                self.enemies.append(Enemy(
                    fp['x'], fp['y'],
                    enemy_type=fp['type'],
                    hp=25,
                    pattern=fp['pattern'],
                    speed=3.6,
                    bullet_mult=stage_data["bullet_speed_mult"],
                    spawn_direction="top",
                    screen_width=self.screen_width
                ))

            # 更新中型大魔王 (Mid-Boss 巡弋於海面，遇到陸地邊界停在該處)
            if self.midboss_warning_timer > 0:
                self.midboss_warning_timer -= dt

            if self.midboss:
                self.midboss.update(dt, self.bg_mgr)
                if self.midboss.alive:
                    target_p = self.get_closest_player(self.midboss.x, self.midboss.y)
                    p_pos = (target_p.x, target_p.y) if target_p else p_ref_pos
                    new_b = self.midboss.attack(dt, p_pos)
                    self.enemy_bullets.extend(new_b)
                elif not self.midboss.alive:
                    self.midboss = None

            # 更新 BOSS (支援雙大魔王)
            for b_obj in self.bosses:
                b_obj.update(dt)
                if b_obj.alive:
                    target_p = self.get_closest_player(b_obj.x, b_obj.y)
                    p_pos = (target_p.x, target_p.y) if target_p else p_ref_pos
                    new_b = b_obj.attack(dt, p_pos)
                    self.enemy_bullets.extend(new_b)

            # 更新玩家子彈 (雷射與追蹤飛彈自動搜尋最近目標)
            potential_targets = []
            if self.midboss and self.midboss.alive and not self.midboss.is_entering:
                potential_targets.append(self.midboss)
            for b_obj in self.bosses:
                if b_obj and b_obj.alive and not b_obj.is_entering:
                    potential_targets.append(b_obj)
            for e in self.enemies:
                if e.alive and self._is_in_playfield(e):
                    potential_targets.append(e)
            for s in self.fleet_mgr.ships:
                if s.alive and not s.is_sinking and self._is_in_playfield(s):
                    potential_targets.append(s)

            for b in self.player_bullets:
                if hasattr(b, 'target'):
                    if not getattr(b.target, 'alive', False) or getattr(b.target, 'is_sinking', False):
                        if potential_targets:
                            b.target = min(potential_targets, key=lambda t: math.hypot(b.x - t.x, b.y - t.y))
                        else:
                            b.target = None
                b.update(dt)

            # 更新敵方子彈
            for eb in self.enemy_bullets:
                eb.update(dt)

            # 更新戰果 (飄向最近玩家)
            for p in self.powerups:
                target_p = self.get_closest_player(p.x, p.y)
                p_pos = (target_p.x, target_p.y) if target_p else p_ref_pos
                p.update(dt, p_pos)

            # 清理失效物件
            self.enemies = [e for e in self.enemies if e.alive]
            self.player_bullets = [b for b in self.player_bullets if b.alive]
            self.enemy_bullets = [eb for eb in self.enemy_bullets if eb.alive]
            self.powerups = [p for p in self.powerups if p.alive]

            # 碰撞檢測
            self.handle_collisions()

        elif self.state == STATE_STAGE_CLEAR:
            self.player_bullets.clear()
            self.enemy_bullets.clear()
            self.state_timer -= dt
            if self.state_timer <= 0:
                if self.current_stage_idx + 1 < len(STAGES_DATA):
                    self.load_stage(self.current_stage_idx + 1)
                    self.state = STATE_PLAYING
                else:
                    self.state = STATE_VICTORY

    def draw(self):
        """畫面繪製與 GPU/CPU 渲染管線"""
        render_surf = self.screen

        if self.state == STATE_MODE_SELECT:
            self.ui_mgr.draw_mode_select(render_surf, self.selected_mode, self.frame_count)
            pygame.display.flip()
            return

        if self.state == STATE_SELECT:
            self.ui_mgr.draw_plane_select(render_surf, self.selected_plane_idx, self.frame_count)
            pygame.display.flip()
            return

        if self.state == STATE_PLANE_SELECT_2P:
            self.ui_mgr.draw_plane_select_2p(render_surf, self.p1_plane_idx, self.p2_plane_idx, self.selecting_player, self.frame_count)
            pygame.display.flip()
            return

        # 1. 繪製多層視差海洋與地表背景
        self.bg_mgr.draw(render_surf)

        # 2. 繪製海面敵主力聯合艦隊
        self.fleet_mgr.draw(render_surf)

        # 3. 繪製海面敵軍
        for e in self.enemies:
            if e.enemy_type == "sea_destroyer":
                e.draw(render_surf)

        # 4. 繪製戰利品寶物
        for p in self.powerups:
            p.draw(render_surf)

        # 5. 繪製空戰敵機、地面戰車、中型大魔王與雙大魔王
        for e in self.enemies:
            if e.enemy_type != "sea_destroyer":
                e.draw(render_surf)

        if self.midboss and (self.midboss.alive or self.midboss.is_defeated):
            self.midboss.draw(render_surf)

        for b_obj in self.bosses:
            if b_obj and (b_obj.alive or b_obj.is_defeated):
                b_obj.draw(render_surf)

        # 6. 繪製玩家戰機 (支援雙戰機同屏)
        if self.player:
            self.player.draw(render_surf, self.particle_mgr)
        if self.player2:
            self.player2.draw(render_surf, self.particle_mgr)

        # 7. 繪製子彈
        if self.state not in [STATE_STAGE_CLEAR, STATE_VICTORY]:
            for b in self.player_bullets:
                b.draw(render_surf)
            for eb in self.enemy_bullets:
                eb.draw(render_surf)

        # 8. 繪製粒子特效
        self.particle_mgr.draw(render_surf)

        # 9. 繪製 HUD 與 UI
        cur_stage = STAGES_DATA[self.current_stage_idx]
        if self.num_players == 2:
            self.ui_mgr.draw_hud_2p(render_surf, self.player, self.player2, self.score, self.high_score, cur_stage, self.bosses, midboss=self.midboss)
        else:
            self.ui_mgr.draw_hud(render_surf, self.player, self.score, self.high_score, cur_stage, self.boss, midboss=self.midboss)

        if self.midboss_warning_timer > 0:
            self.ui_mgr.draw_midboss_warning(render_surf, self.midboss_warning_timer, cur_stage.get("midboss_name", "中型先鋒巡弋艇"))

        if self.fleet_mgr.warning_active:
            self.ui_mgr.draw_fleet_warning(render_surf, self.fleet_mgr.warning_timer)

        if self.state == STATE_BOSS_WARNING:
            self.ui_mgr.draw_boss_warning(render_surf, self.state_timer)

        elif self.state == STATE_STAGE_CLEAR:
            self.ui_mgr.draw_stage_clear(render_surf, cur_stage["stage"], self.score)

        elif self.state == STATE_GAME_OVER:
            self.ui_mgr.draw_game_over(render_surf, self.score, cur_stage["stage"])

        elif self.state == STATE_VICTORY:
            self.ui_mgr.draw_victory_all(render_surf, self.score)

        elif self.state == STATE_PAUSED:
            self.ui_mgr.draw_paused(render_surf)

        pygame.display.flip()

    def _resolve_event_key(self, event):
        """
        解析鍵盤事件之真實按鍵：
        在 Windows 11 中文輸入法下，event.key 常變為 229 (VK_PROCESSKEY) 或大寫字元，
        此處優先結合 SDL2 實體 Scancode 與 Unicode 字元還原為標準 pygame.K_* 常數。
        """
        key = getattr(event, "key", 0)
        scancode = getattr(event, "scancode", None)
        if scancode in _SCANCODE_TO_KEY:
            # 若 event.key 被 IME 改寫為 VK_PROCESSKEY (229) 或未知值，直接使用實體 Scancode 映射
            if key in (0, 229) or key not in _KEY_TO_WIN32_VK:
                return _SCANCODE_TO_KEY[scancode]
        if 65 <= key <= 90:
            # 將大寫 ASCII ('A'~'Z') 統一轉為小寫 pygame.K_a ~ pygame.K_z
            return key + 32
        return key

    def _poll_win32_keys(self):
        """
        在 Windows 11 環境下直接透過 user32.GetAsyncKeyState 讀取實體鍵盤硬體狀態。
        即使輸入法 (IME) 攔截了視窗訊息，仍能 100% 讀取射擊鍵與方向鍵狀態。
        """
        if os.name != "nt" or self.headless:
            return set()
        try:
            if not pygame.key.get_focused():
                return set()
        except Exception:
            pass
        down = set()
        try:
            import ctypes
            get_async = ctypes.windll.user32.GetAsyncKeyState
            for k, vk in _KEY_TO_WIN32_VK.items():
                if get_async(vk) & 0x8000:
                    down.add(k)
        except Exception:
            pass
        return down

    def _handle_keydown_action(self, key):
        """處理單次按鍵觸發動作 (選單切換、射擊點按緩衝、特技 Z/C、暫停 P、復活 Y)"""
        if key == pygame.K_ESCAPE:
            self.running = False
            return

        # F11 快速切換全螢幕 / 視窗模式 (方便 Windows 11 玩家)
        if key == pygame.K_F11 and not self.headless:
            self.fullscreen = not self.fullscreen
            self.screen = self._init_display_surface()
            return

        # 【核心規則】：當其中一人的五個生命都損失後，透過 Y 鍵可以補滿。
        if key == pygame.K_y:
            revived = False
            if self.player and not self.player.alive:
                self.player.revive()
                revived = True
            if self.player2 and not self.player2.alive:
                self.player2.revive()
                revived = True
            if self.num_players == 1 and self.player and not self.player.alive:
                self.player.revive()
                revived = True
            if revived and self.state == STATE_GAME_OVER:
                self.state = STATE_PLAYING

        if self.state == STATE_MODE_SELECT:
            # 作戰模式選擇 (1人 vs 2人)
            if key in [pygame.K_UP, pygame.K_KP8, pygame.K_w]:
                self.selected_mode = 0
            elif key in [pygame.K_DOWN, pygame.K_KP2, pygame.K_s, pygame.K_x]:
                self.selected_mode = 1
            elif key in [pygame.K_SPACE, pygame.K_RETURN, pygame.K_m, pygame.K_j]:
                if self.selected_mode == 0:
                    self.set_mode(1)
                    self.state = STATE_SELECT
                else:
                    self.set_mode(2)
                    self.selecting_player = 1
                    self.state = STATE_PLANE_SELECT_2P

        elif self.state == STATE_SELECT:
            # 1人模式戰機選擇
            if key in [pygame.K_UP, pygame.K_KP8, pygame.K_w]:
                self.selected_plane_idx = (self.selected_plane_idx - 1) % len(FIGHTER_TYPES)
            elif key in [pygame.K_DOWN, pygame.K_KP2, pygame.K_s, pygame.K_x]:
                self.selected_plane_idx = (self.selected_plane_idx + 1) % len(FIGHTER_TYPES)
            elif key in [pygame.K_SPACE, pygame.K_RETURN, pygame.K_m, pygame.K_j]:
                self.init_players()
                self.load_stage(self.current_stage_idx)
                self.state = STATE_PLAYING
                self.sound_mgr.start_bgm()

        elif self.state == STATE_PLANE_SELECT_2P:
            # 2人模式戰機選擇：【核心規則】第一人先選4種之一，第二人只能選剩下3種之一
            if self.selecting_player == 1:
                if key in [pygame.K_UP, pygame.K_KP8, pygame.K_w]:
                    self.p1_plane_idx = (self.p1_plane_idx - 1) % len(FIGHTER_TYPES)
                elif key in [pygame.K_DOWN, pygame.K_KP2, pygame.K_s, pygame.K_x]:
                    self.p1_plane_idx = (self.p1_plane_idx + 1) % len(FIGHTER_TYPES)
                elif key in [pygame.K_m, pygame.K_SPACE, pygame.K_RETURN, pygame.K_j]:
                    self.selecting_player = 2
                    if self.p2_plane_idx == self.p1_plane_idx:
                        self.p2_plane_idx = (self.p1_plane_idx + 1) % len(FIGHTER_TYPES)
            else:
                # 第 2 人以 WX (或方向鍵) 選擇，跳過第 1 人已選之機型
                step = 0
                if key in [pygame.K_w, pygame.K_UP, pygame.K_KP8]:
                    step = -1
                elif key in [pygame.K_x, pygame.K_s, pygame.K_DOWN, pygame.K_KP2]:
                    step = 1

                if step != 0:
                    nxt = (self.p2_plane_idx + step) % len(FIGHTER_TYPES)
                    if nxt == self.p1_plane_idx:
                        nxt = (nxt + step) % len(FIGHTER_TYPES)
                    self.p2_plane_idx = nxt

                elif key in [pygame.K_v, pygame.K_RETURN, pygame.K_SPACE, pygame.K_b]:
                    self.init_players()
                    self.load_stage(self.current_stage_idx)
                    self.state = STATE_PLAYING
                    self.sound_mgr.start_bgm()

        elif self.state in [STATE_PLAYING, STATE_BOSS_WARNING]:
            # 點按射擊鍵立即鎖定觸發緩衝 (防止短按在兩幀間漏失)
            if key in [pygame.K_m, pygame.K_j, pygame.K_RCTRL, pygame.K_KP0] or (
                self.num_players == 1 and key in [pygame.K_SPACE, pygame.K_LCTRL]
            ):
                self._p1_shoot_latch = True
            if key in [pygame.K_v, pygame.K_b] or (self.num_players == 2 and key == pygame.K_LCTRL):
                self._p2_shoot_latch = True

            # 特殊技能觸發：P1 用 Z 或 N，P2 用 C
            if key in [pygame.K_z, pygame.K_n] and self.player:
                self.player.trigger_special()
            if key == pygame.K_c and self.player2:
                self.player2.trigger_special()
            if key == pygame.K_p:
                self.state = STATE_PAUSED

        elif self.state == STATE_PAUSED:
            if key == pygame.K_p:
                self.state = STATE_PLAYING

        elif self.state in [STATE_GAME_OVER, STATE_VICTORY]:
            if key in [pygame.K_RETURN, pygame.K_SPACE]:
                self.high_score = max(self.high_score, self.score)
                self.score = 0
                self.current_stage_idx = 0
                self.enemy_plane_kill_count = 0
                self.enemies.clear()
                self.bosses.clear()
                self.boss = None
                self.midboss = None
                self.midboss_spawned = False
                self.player_bullets.clear()
                self.enemy_bullets.clear()
                self.powerups.clear()
                self.fleet_mgr.reset_for_stage()
                self.state = STATE_MODE_SELECT

    def run_frame(self, dt=1.0 / 60.0, simulated_keys=None):
        """單幀更新 (供主循環或自動化測試使用)"""
        handled_keydowns = set()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return

            if hasattr(pygame, "WINDOWFOCUSGAINED") and event.type == pygame.WINDOWFOCUSGAINED:
                self._disable_ime_and_text_input()
            elif hasattr(pygame, "WINDOWFOCUSLOST") and event.type == pygame.WINDOWFOCUSLOST:
                self._held_keys.clear()
                self._prev_win32_down.clear()

            elif event.type == pygame.KEYDOWN:
                eff_key = self._resolve_event_key(event)
                self._held_keys.add(eff_key)
                handled_keydowns.add(eff_key)
                self._handle_keydown_action(eff_key)
                if not self.running:
                    return

            elif event.type == pygame.KEYUP:
                eff_key = self._resolve_event_key(event)
                self._held_keys.discard(eff_key)
                self._held_keys.discard(getattr(event, "key", 0))

        if simulated_keys is not None:
            keys = simulated_keys
        else:
            win32_down = self._poll_win32_keys()
            if os.name == "nt" and not self.headless:
                # 若 Windows 11 IME 攔截了 KEYDOWN 事件，由 Win32 硬體狀態上升沿自動補發按鍵動作
                for k in win32_down - self._prev_win32_down:
                    if k not in handled_keydowns:
                        self._handle_keydown_action(k)
                        if not self.running:
                            return
                # 同步釋放已放開之實體按鍵，徹底防止 Windows 11 方向鍵卡鍵或移動不順
                for k in list(self._held_keys):
                    if k in _KEY_TO_WIN32_VK and k not in win32_down:
                        self._held_keys.discard(k)
                self._prev_win32_down = win32_down
            raw_keys = pygame.key.get_pressed()
            keys = HybridKeyState(raw_keys, self._held_keys, win32_down)

        def is_down(k):
            try:
                return bool(keys[k])
            except (KeyError, IndexError, TypeError):
                return False

        # 【核心規則】：當其中一人的五個生命都損失後，透過 Y 鍵可以補滿 (支援連續按鍵與模擬按鍵)
        if is_down(pygame.K_y):
            revived = False
            if self.player and not self.player.alive:
                self.player.revive()
                revived = True
            if self.player2 and not self.player2.alive:
                self.player2.revive()
                revived = True
            if self.num_players == 1 and self.player and not self.player.alive:
                self.player.revive()
                revived = True
            if revived and self.state == STATE_GAME_OVER:
                self.state = STATE_PLAYING

        # 處理連續按鍵輸入 (移動與射擊)
        if self.state in [STATE_PLAYING, STATE_BOSS_WARNING]:

            # 鎖定最近目標庫
            potential_targets = []
            if self.midboss and self.midboss.alive and not self.midboss.is_entering:
                potential_targets.append(self.midboss)
            for b_obj in self.bosses:
                if b_obj.alive and not b_obj.is_entering:
                    potential_targets.append(b_obj)
            for e in self.enemies:
                if e.alive and self._is_in_playfield(e):
                    potential_targets.append(e)
            for s in self.fleet_mgr.ships:
                if s.alive and not s.is_sinking and self._is_in_playfield(s):
                    potential_targets.append(s)

            # 1. 第一人 (P1) 控制：【核心規則】以上下左右為主要控制方式，以 M 鍵作為射擊控制
            if self.player and self.player.alive:
                self.player.handle_input(keys, dt, is_2p=(self.num_players == 2))

                if self.player.check_shoot(keys, is_2p=(self.num_players == 2)) or self._p1_shoot_latch:
                    closest = min(potential_targets, key=lambda t: math.hypot(self.player.x - t.x, self.player.y - t.y)) if potential_targets else None
                    bullets = self.player.shoot(closest)
                    self.player_bullets.extend(bullets)

                if is_down(pygame.K_UP) or is_down(pygame.K_KP8) or (self.num_players == 1 and is_down(pygame.K_w)):
                    self.bg_mgr.scroll_speed_mult = 2.4
                else:
                    self.bg_mgr.scroll_speed_mult = 1.0

            # 2. 第二人 (P2) 控制：【核心規則】以 WXAD 作為上下左右控制鍵，以 V 鍵作為射擊控制鍵
            if self.player2 and self.player2.alive:
                self.player2.handle_input(keys, dt, is_2p=True)

                if self.player2.check_shoot(keys, is_2p=True) or self._p2_shoot_latch:
                    closest = min(potential_targets, key=lambda t: math.hypot(self.player2.x - t.x, self.player2.y - t.y)) if potential_targets else None
                    bullets = self.player2.shoot(closest)
                    self.player_bullets.extend(bullets)

                if is_down(pygame.K_w):
                    self.bg_mgr.scroll_speed_mult = 2.4

        self._p1_shoot_latch = False
        self._p2_shoot_latch = False

        # 遊戲循環更新與繪製
        self.update(dt)
        if not self.headless:
            self.draw()

    def run(self, max_frames=None):
        """標準遊戲循環 (支援指定幀數健康檢查，並於 Windows 11 使用高精度時鐘消除掉幀抖動)"""
        current_frame = 0
        target_dt = 1.0 / float(FPS)
        try:
            while self.running:
                if os.name == "nt" and not self.headless:
                    raw_dt = self.clock.tick_busy_loop(FPS) / 1000.0
                else:
                    raw_dt = self.clock.tick(FPS) / 1000.0
                # 當幀率穩定在 ~60 FPS 區間時，鎖定固定時間步長 1/60s，使上下左右移動達到 100% 絲滑等速
                if 0.011 <= raw_dt <= 0.024:
                    dt = target_dt
                else:
                    dt = min(0.05, max(0.001, raw_dt))
                self.run_frame(dt)
                current_frame += 1
                if max_frames and current_frame >= max_frames:
                    print(f"✓ 成功完成 {max_frames} 幀健康檢查運行！狀態: {self.state}, 分數: {self.score}")
                    break
        finally:
            if os.name == "nt" and not self.headless:
                try:
                    import ctypes
                    ctypes.windll.winmm.timeEndPeriod(1)
                except Exception:
                    pass
            pygame.quit()


def main():
    parser = argparse.ArgumentParser(description="1945: 二戰空間（II War Space）")
    parser.add_argument("--test", action="store_true", help="執行無介面自動測試模式")
    parser.add_argument("--frames", type=int, default=0, help="限制運行幀數 (用於健康檢查)")
    parser.add_argument("--stage", type=int, default=1, help="指定起始關卡 (1-20)")
    parser.add_argument("--plane", type=int, default=0, help="指定第1人預選戰機 (0-3)")
    parser.add_argument("--players", type=int, choices=[1, 2], default=1, help="指定玩家人數 (1 或 2)")
    parser.add_argument("--p2-plane", type=int, default=1, help="指定第2人預選戰機 (0-3)")
    parser.add_argument("--cpu-mode", action="store_true", help="啟用 CPU 軟體渲染相容模式")
    parser.add_argument("--fullscreen", action="store_true", help="全螢幕顯示")
    args = parser.parse_args()

    game = Game(
        start_stage=args.stage,
        default_plane_idx=args.plane,
        headless=args.test,
        cpu_mode=args.cpu_mode,
        fullscreen=args.fullscreen,
        num_players=args.players,
        p2_plane_idx=args.p2_plane_idx if hasattr(args, 'p2_plane_idx') else args.p2_plane
    )
    max_frames = args.frames if args.frames > 0 else (120 if args.test else None)
    game.run(max_frames=max_frames)


if __name__ == "__main__":
    main()
