"""
1942: 天空狂怒 (Sky Fury 1942)
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
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, TITLE, STAGES_DATA, FIGHTER_TYPES,
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
STATE_SELECT = "select"
STATE_PLAYING = "playing"
STATE_BOSS_WARNING = "boss_warning"
STATE_STAGE_CLEAR = "stage_clear"
STATE_GAME_OVER = "game_over"
STATE_VICTORY = "victory"
STATE_PAUSED = "paused"

class Game:
    def __init__(self, start_stage=1, default_plane_idx=0, headless=False, cpu_mode=False, fullscreen=False):
        self.headless = headless
        self.cpu_mode = cpu_mode
        self.fullscreen = fullscreen
        self.selected_plane_idx = default_plane_idx
        self.current_stage_idx = max(0, min(19, start_stage - 1))

        # 初始化 Pygame
        if self.headless:
            os.environ["SDL_VIDEODRIVER"] = "dummy"
            os.environ["SDL_AUDIODRIVER"] = "dummy"
        elif self.cpu_mode:
            # 強制 CPU 軟體渲染相容模式 (Mesa llvmpipe)
            os.environ["LIBGL_ALWAYS_SOFTWARE"] = "1"

        pygame.init()
        pygame.display.set_caption(TITLE)

        flags = 0
        if self.fullscreen and not self.headless:
            flags |= pygame.FULLSCREEN

        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), flags)
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
            bg_images=stage_data.get("bg_images")
        )
        self.fleet_mgr = NavalFleetManager()

        # 遊戲進行中物件
        self.player = None
        self.enemies = []
        self.midboss = None
        self.midboss_spawned = False
        self.midboss_warning_timer = 0.0
        self.boss = None
        self.player_bullets = []
        self.enemy_bullets = []
        self.powerups = []

        # 遊戲統計與時間
        self.score = 0
        self.high_score = 50000
        self.state = STATE_SELECT
        self.state_timer = 0.0
        self.stage_time = 0.0
        self.frame_count = 0
        self.enemy_spawn_timer = 0.0
        self.tank_spawn_timer = random.uniform(2.5, 4.5)
        self.enemies_killed_count = 0
        self.enemy_plane_kill_count = 0  # 統計被擊斃敵機數，每 5 架出現 1 個寶物

        # 事先完成好所有精緻多彩精靈圖 (Pre-render and cache all sprites)
        prewarm_all_sprites()

        # 如果透過命令列指定了預選戰機且處於測試模式，可直接進遊戲
        if self.headless:
            self.init_player(self.selected_plane_idx)
            self.state = STATE_PLAYING
            self.sound_mgr.start_bgm()

    def init_player(self, plane_idx):
        """依玩家選擇的機型建立戰機"""
        fighter_cfg = FIGHTER_TYPES[plane_idx]
        self.player = Player(fighter_cfg)

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
            self.midboss = MidBoss(stage_data, self.bg_mgr)
            self.midboss_warning_timer = 3.0
            self.sound_mgr.play("boss_alert")

        # 3. 大幅增加陸地上坦克車出現的數量 (短間隔 + 多輛戰車編隊巡邏)
        self.tank_spawn_timer -= dt
        if self.tank_spawn_timer <= 0:
            self.tank_spawn_timer = random.uniform(2.5, 4.5)
            # 每次生成 1~3 輛戰車部署於陸地防線
            t_count = random.choice([1, 2, 2, 3])
            for _ in range(t_count):
                tank_x = random.choice([
                    random.randint(400, 560),  # 中間陸地核心陣地
                    random.randint(400, 560),  # 加重中間陸地出現機率
                    random.randint(40, 150),   # 左側海岸防禦陣地
                    random.randint(810, 920)   # 右側海岸防禦陣地
                ])
                if self.bg_mgr.is_land_position(tank_x):
                    self.enemies.append(EnemyTank(
                        tank_x, -35 - random.randint(0, 50),
                        hp=55,
                        speed=random.uniform(0.9, 1.3),
                        bullet_mult=stage_data["bullet_speed_mult"]
                    ))

        hp_map = {
            "scout_zero": 25,          # 1 擊潰敗 (或輕微擦彈 2 擊)
            "fast_interceptor": 45,    # 經 1 擊扣 25 滴血剩 20 滴 (機體受損冒黑煙)，第 2 擊立即潰敗！
            "twin_bomber": 48,         # 經 1 擊扣 25 滴剩 23 滴，第 2 擊立即潰敗！
            "heavy_gunship": 85,
            "sea_destroyer": 90
        }

        # 【核心規則】：各型戰機與船艦出現以隨機方式出現，且需有固定比率讓畫面都有敵機出現
        # 4. 固定比率保底敵機機制：檢驗畫面中空中敵機數量，若低於保底閾值立即隨機補充
        air_enemies = [e for e in self.enemies if not getattr(e, 'is_tank', False) and getattr(e, 'enemy_type', '') != "sea_destroyer"]
        MIN_AIR_ENEMIES_ON_SCREEN = 4
        if len(air_enemies) < MIN_AIR_ENEMIES_ON_SCREEN and (not self.boss or self.boss.is_entering):
            sup_type = random.choice(["scout_zero", "fast_interceptor", "twin_bomber", "heavy_gunship"])
            # 【核心規則】：敵方戰機可由下方出現，不是全由上方出現
            from_bottom = (random.random() < 0.35)
            if from_bottom:
                sup_pattern = random.choice(["climb_straight", "climb_sine", "climb_swoop_left", "climb_swoop_right", "dive_loop"])
                spawn_y = SCREEN_HEIGHT + 45 + random.randint(0, 30)
            else:
                sup_pattern = random.choice(["straight", "sine", "dive_loop", "swoop_left", "swoop_right"])
                spawn_y = -45 - random.randint(0, 30)

            self.enemies.append(Enemy(
                random.randint(90, SCREEN_WIDTH - 90), spawn_y,
                enemy_type=sup_type,
                hp=hp_map.get(sup_type, 25),
                pattern=sup_pattern,
                speed=random.uniform(3.0, 4.2),
                bullet_mult=stage_data["bullet_speed_mult"],
                spawn_from_bottom=from_bottom
            ))

        # 5. 常規敵機波次隨機生成
        if self.enemy_spawn_timer <= 0:
            density = stage_data["enemy_density"]
            self.enemy_spawn_timer = random.uniform(1.2, 2.2) / density

            # 依機率隨機選擇敵機種類與編隊型態
            e_type = random.choices(
                ["scout_zero", "fast_interceptor", "twin_bomber", "heavy_gunship", "sea_destroyer"],
                weights=[42, 28, 16, 8, 6]
            )[0]

            # 【核心規則】：敵方戰機可由下方出現，不是全由上方出現 (海軍戰艦除外)
            spawn_from_bottom = (random.random() < 0.32) if e_type != "sea_destroyer" else False
            if spawn_from_bottom:
                pattern = random.choice(["climb_straight", "climb_sine", "climb_swoop_left", "climb_swoop_right", "dive_loop"])
            else:
                pattern = random.choice(["straight", "sine", "dive_loop", "swoop_left", "swoop_right", "hover"])

            # 編隊成行產生 (一次出動 1~3 架)
            spawn_count = 1 if e_type in ["heavy_gunship", "twin_bomber", "sea_destroyer"] else random.randint(1, 3)
            # 【核心規則】：敵方戰艦 (含驅逐巡防艦 sea_destroyer) 一定只能在海上出現！
            if e_type == "sea_destroyer":
                base_x = random.choice([random.randint(220, 340), random.randint(620, 740)])
            else:
                base_x = random.randint(80, SCREEN_WIDTH - 80)
            for i in range(spawn_count):
                ox = (i - (spawn_count - 1) / 2) * 50
                spawn_y = (SCREEN_HEIGHT + 40 + i * 35) if spawn_from_bottom else (-40 - i * 35)
                self.enemies.append(Enemy(
                    base_x + ox, spawn_y,
                    enemy_type=e_type,
                    hp=hp_map[e_type],
                    pattern=pattern,
                    speed=random.uniform(2.8, 4.2),
                    bullet_mult=stage_data["bullet_speed_mult"],
                    spawn_from_bottom=spawn_from_bottom
                ))

    def handle_collisions(self):
        """碰撞檢測與傷害結算 (嚴格滿足核心規則)"""
        # 1. 玩家子彈 vs 敵機
        for b in self.player_bullets:
            if not b.alive:
                continue
            for e in self.enemies:
                if not e.alive:
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
                            self.sound_mgr.play("tank_explosion")
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

            # 玩家子彈 vs 海面敵主力艦隊 (增加戰場複雜度)
            for s in self.fleet_mgr.ships:
                if not s.alive or s.is_sinking:
                    continue
                s_dist = math.hypot(b.x - s.x, b.y - s.y)
                if s_dist < b.radius + s.radius:
                    b.alive = False
                    self.particle_mgr.add_bullet_hit(b.x, b.y)
                    is_sunk = s.take_damage(b.damage)
                    if is_sunk:
                        self.score += s.score
                        self.particle_mgr.add_explosion(s.x, s.y, scale=2.5)
                        self.sound_mgr.play("ship_explosion")
                        self.powerups.extend(s.spawn_drops())
                    break

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
                        self.sound_mgr.play("boss_explosion")
                    continue

            # 玩家子彈 vs BOSS
            if self.boss and self.boss.alive and not self.boss.is_entering:
                b_dist = math.hypot(b.x - self.boss.x, b.y - self.boss.y)
                if b_dist < b.radius + self.boss.radius:
                    b.alive = False
                    self.particle_mgr.add_bullet_hit(b.x, b.y)
                    is_boss_dead = self.boss.take_damage(b.damage)
                    if is_boss_dead:
                        self.score += 5000 + self.current_stage_idx * 1000
                        self.particle_mgr.add_explosion(self.boss.x, self.boss.y, scale=3.5, is_boss=True)
                        self.powerups.extend(self.boss.spawn_drops())
                        self.sound_mgr.play("victory")
                        self.state = STATE_STAGE_CLEAR
                        self.state_timer = 4.0
                        # 【核心修復】：BOSS 被擊潰過關時，立即清空滯空的所有子彈，杜絕殘留漂浮至下一關背景
                        self.player_bullets.clear()
                        self.enemy_bullets.clear()

        # 2. 敵方子彈 vs 玩家 (【核心規則】：損失十分之一生命力，五次完整生命力)
        if self.player and self.player.alive:
            for eb in self.enemy_bullets:
                if not eb.alive:
                    continue
                p_dist = math.hypot(eb.x - self.player.x, eb.y - self.player.y)
                if p_dist < eb.radius + self.player.radius:
                    eb.alive = False
                    hit_result = self.player.take_hit()
                    if hit_result == True:
                        # 喪失一次完整生命力：產生劇烈爆炸與震動
                        self.particle_mgr.add_explosion(self.player.x, self.player.y, scale=2.5)
                        self.sound_mgr.play("explosion")
                        if self.player.game_over:
                            self.state = STATE_GAME_OVER
                            self.state_timer = 0.0
                    elif hit_result == "damaged":
                        # 損失十分之一生命力 (10 HP)：產生火星
                        self.particle_mgr.add_bullet_hit(self.player.x, self.player.y, (255, 100, 100))

            # 3. 玩家 vs 敵機撞擊
            for e in self.enemies:
                if not e.alive:
                    continue
                c_dist = math.hypot(self.player.x - e.x, self.player.y - e.y)
                if c_dist < self.player.radius + e.radius:
                    e.take_damage(999)
                    self.particle_mgr.add_explosion(e.x, e.y, scale=1.2)
                    self.sound_mgr.play("tank_explosion" if getattr(e, 'is_tank', False) else "explosion")
                    if not getattr(e, 'is_tank', False) and getattr(e, 'enemy_type', '') != "sea_destroyer":
                        self.enemy_plane_kill_count += 1
                        if self.enemy_plane_kill_count % 5 == 0:
                            self.powerups.append(PowerUp(e.x, e.y, random.choice(['P', 'S', 'B', 'W', 'L'])))
                    self.on_enemy_defeated(e)
                    hit_res = self.player.take_hit()
                    if hit_res == True:
                        self.particle_mgr.add_explosion(self.player.x, self.player.y, scale=2.5)
                        if self.player.game_over:
                            self.state = STATE_GAME_OVER

            # 4. 玩家 vs 戰果拾取 (【核心規則】：增加射擊戰力與防護罩)
            for p in self.powerups:
                if not p.alive:
                    continue
                u_dist = math.hypot(self.player.x - p.x, self.player.y - p.y)
                if u_dist < self.player.radius + p.radius:
                    p.alive = False
                    self.score += 500
                    self.player.apply_powerup(p.type)
                    self.particle_mgr.add_bullet_hit(p.x, p.y, (100, 255, 200))

    def update(self, dt):
        """核心遊戲狀態更新"""
        self.frame_count += 1
        self.bg_mgr.update(dt)
        self.particle_mgr.update(dt)

        if self.state == STATE_SELECT:
            # 戰機選擇選單狀態
            return

        if self.state == STATE_PAUSED:
            return

        if self.state == STATE_PLAYING or self.state == STATE_BOSS_WARNING:
            self.stage_time += dt
            stage_data = STAGES_DATA[self.current_stage_idx]

            # 戰機更新
            if self.player and self.player.alive:
                self.player.update(dt)

            # BOSS 出現判斷
            if self.stage_time >= stage_data["spawn_duration"] and not self.boss:
                self.state = STATE_BOSS_WARNING
                self.state_timer = 2.5
                self.sound_mgr.play("boss_alert")
                self.boss = Boss(stage_data)

            # 警告倒數結束後進入 BOSS 戰
            if self.state == STATE_BOSS_WARNING:
                self.state_timer -= dt
                if self.state_timer <= 0:
                    self.state = STATE_PLAYING

            # 產生敵機 (BOSS 未出線前或戰況中定期增援)
            if not self.boss or self.boss.is_entering:
                self.spawn_enemies(dt)

            # 更新敵機 (坦克在陸地上推進，遇到海面邊界停在該處)
            p_pos = (self.player.x, self.player.y) if self.player else (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 100)
            for e in self.enemies:
                if hasattr(e, 'is_tank'):
                    e.update(dt, p_pos, self.bg_mgr)
                else:
                    e.update(dt)
                if e.alive:
                    new_b = e.check_shoot(dt, p_pos)
                    self.enemy_bullets.extend(new_b)

            # 更新海面敵主力艦隊 (艦砲齊射與航母艦載機起飛)
            fleet_bullets, fleet_planes = self.fleet_mgr.update(dt, p_pos)
            self.enemy_bullets.extend(fleet_bullets)
            for fp in fleet_planes:
                self.enemies.append(Enemy(
                    fp['x'], fp['y'],
                    enemy_type=fp['type'],
                    hp=25,
                    pattern=fp['pattern'],
                    speed=3.6,
                    bullet_mult=stage_data["bullet_speed_mult"]
                ))

            # 更新中型大魔王 (Mid-Boss 巡弋於海面，遇到陸地邊界停在該處)
            if self.midboss_warning_timer > 0:
                self.midboss_warning_timer -= dt

            if self.midboss:
                self.midboss.update(dt, self.bg_mgr)
                if self.midboss.alive:
                    new_b = self.midboss.attack(dt, p_pos)
                    self.enemy_bullets.extend(new_b)
                elif not self.midboss.alive:
                    self.midboss = None

            # 更新 BOSS
            if self.boss:
                self.boss.update(dt)
                if self.boss.alive:
                    new_b = self.boss.attack(dt, p_pos)
                    self.enemy_bullets.extend(new_b)

            # 更新玩家子彈 (雷射與追蹤飛彈自動搜尋最近敵機、戰車、軍艦、中型大魔王或 BOSS)
            potential_targets = []
            if self.midboss and self.midboss.alive and not self.midboss.is_entering:
                potential_targets.append(self.midboss)
            if self.boss and self.boss.alive and not self.boss.is_entering:
                potential_targets.append(self.boss)
            for e in self.enemies:
                if e.alive:
                    potential_targets.append(e)
            for s in self.fleet_mgr.ships:
                if s.alive and not s.is_sinking:
                    potential_targets.append(s)

            for b in self.player_bullets:
                if hasattr(b, 'target'):
                    # 若現有目標已死或不存在，動態重新鎖定最近目標
                    if not getattr(b.target, 'alive', False) or getattr(b.target, 'is_sinking', False):
                        if potential_targets:
                            b.target = min(potential_targets, key=lambda t: math.hypot(b.x - t.x, b.y - t.y))
                        else:
                            b.target = None
                b.update(dt)

            # 更新敵方子彈
            for eb in self.enemy_bullets:
                eb.update(dt)

            # 更新戰果
            for p in self.powerups:
                p.update(dt, p_pos)

            # 清理失效物件
            self.enemies = [e for e in self.enemies if e.alive]
            self.player_bullets = [b for b in self.player_bullets if b.alive]
            self.enemy_bullets = [eb for eb in self.enemy_bullets if eb.alive]
            self.powerups = [p for p in self.powerups if p.alive]

            # 碰撞檢測
            self.handle_collisions()

        elif self.state == STATE_STAGE_CLEAR:
            # 過關展示期間持續清空殘留子彈，杜絕漂浮停滯至下一關
            self.player_bullets.clear()
            self.enemy_bullets.clear()
            self.state_timer -= dt
            if self.state_timer <= 0:
                if self.current_stage_idx + 1 < len(STAGES_DATA):
                    # 前往下一大關！(共 20 大關)
                    self.load_stage(self.current_stage_idx + 1)
                    self.state = STATE_PLAYING
                else:
                    # 突破全 20 大關！終極通關！
                    self.state = STATE_VICTORY

    def draw(self):
        """畫面繪製與 GPU/CPU 渲染管線"""
        # 取得震動偏移量
        ox, oy = self.particle_mgr.get_shake_offset()
        render_surf = self.screen

        if self.state == STATE_SELECT:
            self.ui_mgr.draw_plane_select(render_surf, self.selected_plane_idx, self.frame_count)
            pygame.display.flip()
            return

        # 1. 繪製多層視差海洋與地表背景
        self.bg_mgr.draw(render_surf)

        # 2. 繪製海面敵主力聯合艦隊 (在海洋層上航行，具備洶湧航跡浪花)
        self.fleet_mgr.draw(render_surf)

        # 3. 繪製海面或地表敵軍 (海軍巡邏艇)
        for e in self.enemies:
            if e.enemy_type == "sea_destroyer":
                e.draw(render_surf)

        # 4. 繪製戰利品寶物 (P, S, B, W, L)
        for p in self.powerups:
            p.draw(render_surf)

        # 5. 繪製空戰敵機、地面戰車、中型大魔王與終極 BOSS
        for e in self.enemies:
            if e.enemy_type != "sea_destroyer":
                e.draw(render_surf)

        if self.midboss and (self.midboss.alive or self.midboss.is_defeated):
            self.midboss.draw(render_surf)

        if self.boss and (self.boss.alive or self.boss.is_defeated):
            self.boss.draw(render_surf)

        # 6. 繪製玩家戰機
        if self.player:
            self.player.draw(render_surf, self.particle_mgr)

        # 7. 繪製子彈 (我軍自動追蹤雷射與機砲，過關結算與通關期間不繪製任何殘留子彈)
        if self.state not in [STATE_STAGE_CLEAR, STATE_VICTORY]:
            for b in self.player_bullets:
                b.draw(render_surf)
            for eb in self.enemy_bullets:
                eb.draw(render_surf)

        # 8. 繪製粒子特效 (火花、濃煙、殘影、衝擊波)
        self.particle_mgr.draw(render_surf)

        # 9. 繪製 HUD 與 UI (上下獨立切割防遮擋、中型魔王血條、終極敵艦外型與擊破倒數)
        cur_stage = STAGES_DATA[self.current_stage_idx]
        if self.player:
            self.ui_mgr.draw_hud(render_surf, self.player, self.score, self.high_score, cur_stage, self.boss, midboss=self.midboss)

        # 中型大魔王警報橫幅
        if self.midboss_warning_timer > 0:
            self.ui_mgr.draw_midboss_warning(render_surf, self.midboss_warning_timer, cur_stage.get("midboss_name", "中型先鋒巡弋艇"))

        # 敵海上主力艦隊警報橫幅
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

        # 僅調用單次 flip，杜絕雙緩衝衝突產生的橫條紋與畫面撕裂
        pygame.display.flip()

    def run_frame(self, dt=1.0 / 60.0, simulated_keys=None):
        """單幀更新 (供主循環或自動化測試使用)"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                    return

                if self.state == STATE_SELECT:
                    # 戰機選擇操作
                    if event.key in [pygame.K_UP, pygame.K_w]:
                        self.selected_plane_idx = (self.selected_plane_idx - 1) % len(FIGHTER_TYPES)
                    elif event.key in [pygame.K_DOWN, pygame.K_s]:
                        self.selected_plane_idx = (self.selected_plane_idx + 1) % len(FIGHTER_TYPES)
                    elif event.key in [pygame.K_SPACE, pygame.K_RETURN]:
                        # 確認出擊！啟動動態背景音樂
                        self.init_player(self.selected_plane_idx)
                        self.load_stage(self.current_stage_idx)
                        self.state = STATE_PLAYING
                        self.sound_mgr.start_bgm()

                elif self.state in [STATE_PLAYING, STATE_BOSS_WARNING]:
                    if event.key == pygame.K_z:
                        # 【核心規則】：當出警示提示時，不能限制控制功能讓戰機還能被控制 (翻轉閃避 / 形成防護罩)
                        if self.player:
                            self.player.trigger_special()
                    elif event.key == pygame.K_p:
                        self.state = STATE_PAUSED

                elif self.state == STATE_PAUSED:
                    if event.key == pygame.K_p:
                        self.state = STATE_PLAYING

                elif self.state in [STATE_GAME_OVER, STATE_VICTORY]:
                    if event.key == pygame.K_RETURN:
                        # 重新開始遊戲
                        self.score = 0
                        self.selected_plane_idx = 0
                        self.state = STATE_SELECT

        # 處理連續按鍵輸入 (移動與射擊)
        # 【核心規則】：當出警示提示時 (如 STATE_BOSS_WARNING 或敵艦隊突入警報)，不能限制控制功能，戰機必須還能被自由控制！
        if self.state in [STATE_PLAYING, STATE_BOSS_WARNING] and self.player and self.player.alive:
            keys = simulated_keys if simulated_keys is not None else pygame.key.get_pressed()
            # 上下左右移動
            self.player.handle_input(keys, dt)

            # 【核心規則】：當我方戰機往前移動時加快畫面往前移動速度
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                self.bg_mgr.scroll_speed_mult = 2.4
            else:
                self.bg_mgr.scroll_speed_mult = 1.0

            # 空白鍵發射子彈 (高能追蹤雷射自動鎖定最近之敵軍：BOSS、空中敵機、陸地戰車或海上戰艦)
            if keys[pygame.K_SPACE]:
                potential_targets = []
                if self.boss and self.boss.alive and not self.boss.is_entering:
                    potential_targets.append(self.boss)
                for e in self.enemies:
                    if e.alive:
                        potential_targets.append(e)
                for s in self.fleet_mgr.ships:
                    if s.alive and not s.is_sinking:
                        potential_targets.append(s)

                closest = min(potential_targets, key=lambda t: math.hypot(self.player.x - t.x, self.player.y - t.y)) if potential_targets else None
                bullets = self.player.shoot(closest)
                self.player_bullets.extend(bullets)

        # 遊戲循環更新與繪製
        self.update(dt)
        if not self.headless:
            self.draw()

    def run(self, max_frames=None):
        """標準遊戲循環 (支援指定幀數健康檢查)"""
        current_frame = 0
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(0.1, dt)  # 防止切換視窗時的時間突波
            self.run_frame(dt)
            current_frame += 1
            if max_frames and current_frame >= max_frames:
                print(f"✓ 成功完成 {max_frames} 幀健康檢查運行！狀態: {self.state}, 分數: {self.score}")
                break

        pygame.quit()


def main():
    parser = argparse.ArgumentParser(description="1942: 天空狂怒 (Sky Fury 1942)")
    parser.add_argument("--test", action="store_true", help="執行無介面自動測試模式")
    parser.add_argument("--frames", type=int, default=0, help="限制運行幀數 (用於健康檢查)")
    parser.add_argument("--stage", type=int, default=1, help="指定起始關卡 (1-20)")
    parser.add_argument("--plane", type=int, default=0, help="指定預選戰機 (0-3)")
    parser.add_argument("--cpu-mode", action="store_true", help="啟用 CPU 軟體渲染相容模式")
    parser.add_argument("--fullscreen", action="store_true", help="全螢幕顯示")
    args = parser.parse_args()

    game = Game(
        start_stage=args.stage,
        default_plane_idx=args.plane,
        headless=args.test,
        cpu_mode=args.cpu_mode,
        fullscreen=args.fullscreen
    )
    max_frames = args.frames if args.frames > 0 else (120 if args.test else None)
    game.run(max_frames=max_frames)


if __name__ == "__main__":
    main()
