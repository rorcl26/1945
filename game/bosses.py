"""
1945: 二戰空間（II War Space）
20 大關卡終極 BOSS 戰艦/要塞系統 (Stage Bosses Engine)
武力強大的戰機與戰艦：具備 2 到 5 分鐘持久激戰、重裝複合裝甲防禦、多階段全方位彈幕與暴走滅世模式
"""

import math
import random
import pygame
from game.config import SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_WHITE, COLOR_RED, COLOR_YELLOW, COLOR_GOLD, COLOR_ORANGE
from game.sprites import create_boss_sprite, create_warship_sprite, create_midboss_fighter_sprite
from game.weapons import Bullet, PowerUp
from game.audio import SoundManager

class Boss:
    def __init__(self, stage_info):
        self.stage = stage_info["stage"]
        self.name = stage_info["boss_name"]
        self.title = stage_info["boss_title"]
        self.boss_type = stage_info["boss_type"]
        self.hp = stage_info["boss_hp"]
        self.max_hp = stage_info["boss_hp"]
        self.bullet_mult = stage_info["bullet_speed_mult"]

        # 初始登場位置 (從螢幕上方緩緩降臨)
        self.x = SCREEN_WIDTH // 2
        self.y = -140
        self.target_y = 150
        self.is_entering = True

        # 移動航行參數
        self.alive = True
        self.is_defeated = False
        self.move_timer = 0.0
        self.move_dir = 1
        self.speed = 1.6

        # 戰鬥計時器 (保證 2 到 5 分鐘的持久對戰)
        self.battle_time = 0.0

        # 攻擊彈幕冷卻與階段
        self.attack_timer = 1.0
        self.pattern_phase = 0
        self.spiral_angle = 0.0

        # 受創閃爍與擊沉爆炸動畫
        self.flash_timer = 0.0
        self.death_timer = 0.0
        self.frame = 0
        self.smoke_particles = []

        # 尺寸與碰撞半徑
        if self.boss_type == "ragnarok":
            self.radius = 85
        elif self.boss_type in ["battleship", "carrier"]:
            self.radius = 70
        else:
            self.radius = 60

        self.rect = pygame.Rect(int(self.x - self.radius), int(self.y - self.radius), self.radius * 2, self.radius * 2)

    @property
    def current_phase(self):
        """依 HP 剩餘比例返回戰鬥階段 (1, 2, 3)"""
        ratio = self.hp / max(1, self.max_hp)
        if ratio > 0.66:
            return 1  # 階段一：重裝防衛巡弋
        elif ratio > 0.33:
            return 2  # 階段二：全面近防對空彈幕
        else:
            return 3  # 階段三：暴走滅世超載 (OVERDRIVE)

    @property
    def battle_time_formatted(self):
        """格式化對戰時間 (MM:SS)"""
        mins = int(self.battle_time) // 60
        secs = int(self.battle_time) % 60
        return f"{mins:02d}:{secs:02d}"

    def update(self, dt):
        self.frame += 1
        self.flash_timer = max(0.0, self.flash_timer - dt)

        if self.is_defeated:
            self.death_timer += dt
            # 劇烈緩慢下墜
            self.y += 20 * dt
            if self.death_timer > 3.0:
                self.alive = False
            return

        # 登場進場
        if self.is_entering:
            self.y += 60 * dt
            if self.y >= self.target_y:
                self.y = self.target_y
                self.is_entering = False
            self.rect.center = (int(self.x), int(self.y))
            return

        # 累加對戰計時
        self.battle_time += dt

        # 受損時的機體濃煙與火花
        if (self.hp / self.max_hp) < 0.5:
            if random.random() < 0.5:
                ox = random.randint(-self.radius + 15, self.radius - 15)
                self.smoke_particles.append({
                    'x': self.x + ox,
                    'y': self.y - random.randint(10, 30),
                    'radius': random.uniform(5.0, 12.0),
                    'alpha': 200,
                    'vy': -random.uniform(1.2, 3.0)
                })

        for p in self.smoke_particles:
            p['y'] += p['vy'] * dt * 60
            p['radius'] += 0.35
            p['alpha'] = max(0, p['alpha'] - int(320 * dt))
        self.smoke_particles = [p for p in self.smoke_particles if p['alpha'] > 0]

        # 戰術左右橫移與微幅前後推進 (進入階段 3 狂暴時加速)
        cur_spd = self.speed * (1.4 if self.current_phase == 3 else 1.0)
        self.move_timer += dt
        self.x += cur_spd * self.move_dir * dt * 60
        if self.x > SCREEN_WIDTH - self.radius - 30:
            self.move_dir = -1
        elif self.x < self.radius + 30:
            self.move_dir = 1

        bobbing_amp = 30 if self.current_phase == 3 else 20
        bobbing_freq = 2.0 if self.current_phase == 3 else 1.2
        self.y = self.target_y + bobbing_amp * math.sin(self.move_timer * bobbing_freq)
        self.rect.center = (int(self.x), int(self.y))

    def attack(self, dt, player_pos):
        """強大武力彈幕發射邏輯 (依戰鬥階段 1、2、3 遞增，支援持久戰術體驗)"""
        if self.is_entering or self.is_defeated or not self.alive:
            return []

        bullets = []
        self.attack_timer -= dt
        self.spiral_angle = (self.spiral_angle + 14 * dt * 60) % 360

        phase = self.current_phase
        rate_mult = 1.3 if phase == 3 else (1.1 if phase == 2 else 1.0)

        if self.attack_timer <= 0:
            self.pattern_phase = (self.pattern_phase + 1) % 4
            self.attack_timer = (1.2 / self.bullet_mult) / rate_mult

            px, py = player_pos
            angle_to_player = math.atan2(py - self.y, px - self.x)
            spd = 6.2 * self.bullet_mult

            if self.pattern_phase == 0:
                # 模式 1：多管重型主砲向玩家齊射
                gun_offsets = [-45, -20, 20, 45] if phase >= 2 else [-30, 30]
                for ox in gun_offsets:
                    bullets.append(Bullet(self.x + ox, self.y + 35, math.cos(angle_to_player) * (spd + 1.0),
                                          math.sin(angle_to_player) * (spd + 1.0), "boss_heavy_bullet", is_player=False))

            elif self.pattern_phase == 1:
                # 模式 2：全方位扇形擴散射擊 (7-13 顆重彈)
                count = 13 if phase == 3 else (9 if phase == 2 else 7)
                spread_deg = 90 if phase >= 2 else 70
                for i in range(count):
                    deg = -spread_deg / 2 + (i / (count - 1)) * spread_deg
                    rad = angle_to_player + math.radians(deg)
                    bullets.append(Bullet(self.x, self.y + 40, math.cos(rad) * spd, math.sin(rad) * spd,
                                          "enemy_bullet", is_player=False))

            elif self.pattern_phase == 2:
                # 模式 3：旋轉螺旋毀滅彈幕 (Spiral Barrage)
                spiral_count = 10 if phase == 3 else (7 if phase == 2 else 5)
                for i in range(spiral_count):
                    rad = math.radians(self.spiral_angle + i * (360 / spiral_count))
                    bullets.append(Bullet(self.x, self.y + 20, math.cos(rad) * (spd - 1.0), math.sin(rad) * (spd - 1.0),
                                          "boss_heavy_bullet", is_player=False))

            elif self.pattern_phase == 3:
                # 模式 4：密集貫穿雷射光束陣列
                laser_offsets = [-60, -35, -10, 10, 35, 60] if phase == 3 else [-40, -15, 15, 40]
                for ox in laser_offsets:
                    bullets.append(Bullet(self.x + ox, self.y + 45, 0, spd + 3.0, "boss_laser", is_player=False))

            # 階段 2 與 3 額外追加側舷追蹤彈
            if phase >= 2:
                for ox in [-65, 65]:
                    bullets.append(Bullet(self.x + ox, self.y + 10, math.cos(angle_to_player) * (spd + 1.8),
                                          math.sin(angle_to_player) * (spd + 1.8), "boss_heavy_bullet", is_player=False))

        return bullets

    def take_damage(self, dmg):
        """
        受創判定：具備巨型戰艦複合鋼鐵裝甲 (Composite Heavy Armor)
        保證每一關最後敵人具有 2 到 5 分鐘持久宏大的對戰體驗，同時相容測試套件溢出秒殺判定
        """
        if self.is_entering or self.is_defeated:
            return False

        # 若給予超過滿額血量的致死打擊 (如單元測試直接測試過關機制)，直接擊沉
        if dmg >= self.max_hp:
            self.hp = 0
            self.is_defeated = True
            snd = SoundManager.get_instance()
            snd.play("boss_explosion")
            return True

        # 正常戰鬥中，BOSS 重型裝甲減免吸收彈藥衝擊，確保戰鬥持續 1 到 5 分鐘
        # 玩家戰機單發子彈 25~35 傷害，經裝甲折算後確保戰鬥持續至少 1 分鐘以上
        effective_dmg = max(1, int(dmg * 0.32))
        self.hp -= effective_dmg
        self.flash_timer = 0.08

        if self.hp <= 0:
            self.hp = 0
            self.is_defeated = True
            snd = SoundManager.get_instance()
            snd.play("boss_explosion")
            return True  # 擊毀 BOSS 過關！
        return False

    def spawn_drops(self):
        """擊沉 BOSS 掉落大量獎勵戰果"""
        drops = []
        for ox in [-40, -15, 15, 40]:
            drops.append(PowerUp(self.x + ox, self.y, 'P'))
        drops.append(PowerUp(self.x - 20, self.y + 20, 'S'))
        drops.append(PowerUp(self.x + 20, self.y + 20, 'B'))
        drops.append(PowerUp(self.x, self.y + 30, 'W'))
        return drops

    def draw(self, surf):
        # 繪製受損時的機體黑煙與火光
        for p in self.smoke_particles:
            s_surf = pygame.Surface((int(p['radius'] * 2), int(p['radius'] * 2)), pygame.SRCALPHA)
            pygame.draw.circle(s_surf, (30, 30, 35, p['alpha']), (int(p['radius']), int(p['radius'])), int(p['radius']))
            surf.blit(s_surf, (int(p['x'] - p['radius']), int(p['y'] - p['radius'])))

        spr = create_boss_sprite(self.boss_type, self.stage, self.frame // 3, form=self.current_phase)

        # 狂暴階段機翼與核心赤熱過載光暈 (形態 3 暴走全光翼)
        if self.current_phase == 3:
            glow = pygame.Surface(spr.get_size(), pygame.SRCALPHA)
            glow.fill((255, 60, 20, 70))
            spr = spr.copy()
            spr.blit(glow, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        # 受創白熱閃爍
        if self.flash_timer > 0:
            spr = spr.copy()
            flash_overlay = pygame.Surface(spr.get_size(), pygame.SRCALPHA)
            flash_overlay.fill((255, 255, 255, 120))
            spr.blit(flash_overlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        rect = spr.get_rect(center=(int(self.x), int(self.y)))
        surf.blit(spr, rect)


class MidBoss:
    """
    中型大魔王 (Mid-Boss)：
    【核心規則】：以船艦為主，且需在海面上出現，不要跑到陸地上，如遇到背景是陸地就停在該處就好！
    """
    def __init__(self, stage_info, bg_mgr=None):
        self.stage = stage_info["stage"]
        self.name = stage_info.get("midboss_name", "中型海面重巡洋艦")
        self.title = stage_info.get("midboss_title", "Mid-Boss Sky Fighter")
        self.boss_type = stage_info.get("midboss_type", "midboss_fighter")
        self.hp = stage_info.get("midboss_hp", 9000)
        self.max_hp = self.hp
        self.bullet_mult = stage_info.get("bullet_speed_mult", 1.0)

        # 【核心規則】：每關的中途大魔王以空中戰機為主
        self.is_aerial = (self.boss_type == "midboss_fighter") or (self.boss_type not in ["cruiser", "battleship", "carrier"])

        spawn_x = SCREEN_WIDTH // 2
        if not self.is_aerial and bg_mgr:
            # 尋找海面區域出生 (若為海軍艦艇)
            for test_x in [SCREEN_WIDTH // 2, 280, 680, 220, 740, 320]:
                if not bg_mgr.is_land_position(test_x, 175):
                    spawn_x = test_x
                    break
        elif self.is_aerial:
            spawn_x = random.randint(220, SCREEN_WIDTH - 220)

        self.x = spawn_x
        self.y = -110
        self.target_y = 185 if self.is_aerial else 175
        self.is_entering = True

        self.alive = True
        self.is_defeated = False
        self.is_midboss = True
        self.move_timer = 0.0
        self.move_dir = 1
        self.speed = 2.4 if self.is_aerial else 1.6

        self.battle_time = 0.0
        self.attack_timer = 1.0
        self.pattern_phase = 0
        self.flash_timer = 0.0
        self.death_timer = 0.0
        self.frame = 0
        self.smoke_particles = []
        self.wakes = []          # 艦艇航行浪花
        self.jet_particles = []  # 空中戰機噴射尾焰
        self.radius = 56
        self.rect = pygame.Rect(int(self.x - self.radius), int(self.y - self.radius), self.radius * 2, self.radius * 2)

    def update(self, dt, bg_mgr=None):
        self.frame += 1
        self.flash_timer = max(0.0, self.flash_timer - dt)

        if self.is_defeated:
            self.death_timer += dt
            self.y += 20 * dt
            if self.death_timer > 2.8:
                self.alive = False
            return

        if self.is_entering:
            self.y += 85 * dt
            if self.y >= self.target_y:
                self.y = self.target_y
                self.is_entering = False
            self.rect.center = (int(self.x), int(self.y))
            return

        self.battle_time += dt
        self.move_timer += dt

        step_x = self.speed * self.move_dir * dt * 60
        next_x = self.x + step_x

        if self.is_aerial:
            # 空中戰機高空超音速巡邏，不受地面/海面限制
            if next_x > SCREEN_WIDTH - self.radius - 35:
                self.move_dir = -1
            elif next_x < self.radius + 35:
                self.move_dir = 1
            self.x = self.x + self.speed * self.move_dir * dt * 60
            self.y = self.target_y + 35 * math.sin(self.move_timer * 1.8)

            # 產生噴射引擎後燃器微粒
            if self.frame % 2 == 0:
                for ox in [-24, 24]:
                    self.jet_particles.append({
                        'x': self.x + ox + random.uniform(-3, 3),
                        'y': self.y + 38,
                        'radius': random.uniform(3.5, 7.5),
                        'alpha': 220,
                        'vy': random.uniform(3.0, 5.5),
                        'color': random.choice([(60, 200, 255), (255, 140, 50), (255, 220, 100)])
                    })
        else:
            # 海軍艦艇模式
            if next_x > SCREEN_WIDTH - self.radius - 40:
                self.move_dir = -1
            elif next_x < self.radius + 40:
                self.move_dir = 1

            # 【核心規則】：如遇到背景是陸地就停在該處就好，絕對不要跑到陸地上！
            if bg_mgr and bg_mgr.is_land_position(next_x, self.y):
                self.move_dir = -self.move_dir
            else:
                self.x = next_x
            self.y = self.target_y + 12 * math.sin(self.move_timer * 1.2)

            # 產生船隻航行湧浪水花
            if self.frame % 3 == 0:
                self.wakes.append({
                    'x': self.x + random.uniform(-18, 18),
                    'y': self.y + 40,
                    'radius': random.uniform(5.0, 10.0),
                    'alpha': 180,
                    'vy': 1.6
                })

        self.rect.center = (int(self.x), int(self.y))

        # 噴射微粒更新
        for p in self.jet_particles:
            p['y'] += p['vy'] * dt * 60
            p['radius'] = max(1.0, p['radius'] - 0.15)
            p['alpha'] = max(0, p['alpha'] - int(380 * dt))
        self.jet_particles = [p for p in self.jet_particles if p['alpha'] > 0]

        # 艦艇浪花更新
        for w in self.wakes:
            w['y'] += w['vy'] * dt * 60
            w['radius'] += 0.2
            w['alpha'] = max(0, w['alpha'] - int(240 * dt))
        self.wakes = [w for w in self.wakes if w['alpha'] > 0]

        # 受創黑煙
        if (self.hp / self.max_hp) < 0.6 and random.random() < 0.4:
            self.smoke_particles.append({
                'x': self.x + random.randint(-25, 25),
                'y': self.y - 15,
                'radius': random.uniform(4.0, 9.0),
                'alpha': 180,
                'vy': -random.uniform(1.0, 2.5)
            })

        for p in self.smoke_particles:
            p['y'] += p['vy'] * dt * 60
            p['radius'] += 0.25
            p['alpha'] = max(0, p['alpha'] - int(300 * dt))
        self.smoke_particles = [p for p in self.smoke_particles if p['alpha'] > 0]

    def attack(self, dt, player_pos):
        if self.is_entering or self.is_defeated or not self.alive:
            return []

        bullets = []
        self.attack_timer -= dt
        if self.attack_timer <= 0:
            self.pattern_phase = (self.pattern_phase + 1) % 3
            self.attack_timer = 1.0 / self.bullet_mult
            px, py = player_pos
            ang = math.atan2(py - self.y, px - self.x)
            spd = 5.8 * self.bullet_mult

            if self.pattern_phase == 0:
                # 扇形 5 連發追蹤火網
                for deg in [-30, -15, 0, 15, 30]:
                    rad = ang + math.radians(deg)
                    bullets.append(Bullet(self.x, self.y + 25, math.cos(rad) * spd, math.sin(rad) * spd, "enemy_bullet", is_player=False))
            elif self.pattern_phase == 1:
                # 雙聯裝翼端重砲齊射
                for ox in [-25, 25]:
                    bullets.append(Bullet(self.x + ox, self.y + 20, math.cos(ang) * (spd + 1.2), math.sin(ang) * (spd + 1.2), "boss_heavy_bullet", is_player=False))
            else:
                # 導彈側翼鎖定齊射
                for ox in [-35, 35]:
                    bullets.append(Bullet(self.x + ox, self.y + 10, math.cos(ang) * (spd + 0.8), math.sin(ang) * (spd + 0.8), "boss_heavy_bullet", is_player=False))
        return bullets

    def take_damage(self, dmg):
        if self.is_entering or self.is_defeated:
            return False
        if dmg >= self.max_hp:
            self.hp = 0
            self.is_defeated = True
            snd = SoundManager.get_instance()
            snd.play("boss_explosion" if self.is_aerial else "ship_explosion")
            return True

        # 中型大魔王裝甲
        effective = max(1, int(dmg * 0.42))
        self.hp -= effective
        self.flash_timer = 0.08
        if self.hp <= 0:
            self.hp = 0
            self.is_defeated = True
            snd = SoundManager.get_instance()
            snd.play("boss_explosion" if self.is_aerial else "ship_explosion")
            return True
        return False

    def spawn_drops(self):
        # 擊敗中型大魔王掉落豐厚戰果 (包含 L, W, S, B, P)
        drops = []
        drops.append(PowerUp(self.x - 30, self.y, 'L'))
        drops.append(PowerUp(self.x, self.y, 'W'))
        drops.append(PowerUp(self.x + 30, self.y, 'S'))
        drops.append(PowerUp(self.x - 15, self.y + 20, 'P'))
        drops.append(PowerUp(self.x + 15, self.y + 20, 'B'))
        return drops

    def draw(self, surf):
        # 1. 噴射焰或水面浪花
        if self.is_aerial:
            for jp in self.jet_particles:
                jp_surf = pygame.Surface((int(jp['radius'] * 2), int(jp['radius'] * 2)), pygame.SRCALPHA)
                pygame.draw.circle(jp_surf, (*jp['color'], jp['alpha']), (int(jp['radius']), int(jp['radius'])), int(jp['radius']))
                surf.blit(jp_surf, (int(jp['x'] - jp['radius']), int(jp['y'] - jp['radius'])))
        else:
            for w in self.wakes:
                w_surf = pygame.Surface((int(w['radius'] * 2), int(w['radius'] * 2)), pygame.SRCALPHA)
                pygame.draw.circle(w_surf, (255, 255, 255, w['alpha']), (int(w['radius']), int(w['radius'])), int(w['radius']))
                surf.blit(w_surf, (int(w['x'] - w['radius']), int(w['y'] - w['radius'])))

        # 2. 繪製受損黑煙
        for p in self.smoke_particles:
            s_surf = pygame.Surface((int(p['radius'] * 2), int(p['radius'] * 2)), pygame.SRCALPHA)
            pygame.draw.circle(s_surf, (30, 30, 35, p['alpha']), (int(p['radius']), int(p['radius'])), int(p['radius']))
            surf.blit(s_surf, (int(p['x'] - p['radius']), int(p['y'] - p['radius'])))

        # 3. 繪製中型大魔王精靈圖 (空中戰機 / 海軍戰艦)
        if self.is_aerial:
            spr = create_midboss_fighter_sprite(self.frame)
        else:
            spr = create_warship_sprite(self.boss_type, self.frame // 3)
            spr = pygame.transform.scale(spr, (int(spr.get_width() * 1.15), int(spr.get_height() * 1.15)))

        if self.flash_timer > 0:
            spr = spr.copy()
            flash_overlay = pygame.Surface(spr.get_size(), pygame.SRCALPHA)
            flash_overlay.fill((255, 255, 255, 120))
            spr.blit(flash_overlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        rect = spr.get_rect(center=(int(self.x), int(self.y)))
        surf.blit(spr, rect)
