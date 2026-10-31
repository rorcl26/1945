"""
1942: 天空狂怒 (Sky Fury 1942)
海面敵主力聯合艦隊系統 (Naval Armada & Fleet Battle Group Engine)
中間突入敵方海上艦隊：包含超重無畏艦、戰列艦、航空母艦、巡洋艦與高速魚雷砲艇
具備不定時出現的大、中、小型敵艦突襲、艦砲齊射、防空彈幕與艦載機起飛
"""

import math
import random
import pygame
from game.config import SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_WHITE, COLOR_RED, COLOR_YELLOW, COLOR_GOLD
from game.weapons import Bullet, PowerUp
from game.audio import SoundManager
from game.sprites import create_warship_sprite

class FleetShip:
    def __init__(self, x, y, ship_type="battleship", speed=1.2, bullet_mult=1.0):
        self.x = x
        self.y = y
        self.ship_type = ship_type
        self.speed = speed
        self.bullet_mult = bullet_mult
        self.alive = True
        self.is_sinking = False
        self.sink_timer = 0.0
        self.frame = random.randint(0, 100)

        # 尺寸、血量與分數設定 (涵蓋大型、中型、小型戰艦)
        if ship_type == "dreadnought":
            # 超重型無畏旗艦 (大型)
            self.width = 86
            self.length = 210
            self.hp = 480
            self.max_hp = 480
            self.score = 3500
            self.radius = 46
        elif ship_type == "battleship":
            # 重型戰列艦 (大型)
            self.width = 76
            self.length = 180
            self.hp = 360
            self.max_hp = 360
            self.score = 2500
            self.radius = 42
        elif ship_type == "carrier":
            # 航空母艦 (大型)
            self.width = 72
            self.length = 170
            self.hp = 300
            self.max_hp = 300
            self.score = 2200
            self.radius = 38
        elif ship_type == "cruiser":
            # 重巡洋艦 (中型)
            self.width = 54
            self.length = 130
            self.hp = 200
            self.max_hp = 200
            self.score = 1500
            self.radius = 30
        elif ship_type == "patrol_boat":
            # 高速巡邏魚雷艇 (小型)
            self.width = 30
            self.length = 58
            self.hp = 50
            self.max_hp = 50
            self.score = 500
            self.radius = 16
        else:  # gunboat
            # 先鋒防空砲艇 (小型)
            self.width = 38
            self.length = 75
            self.hp = 80
            self.max_hp = 80
            self.score = 700
            self.radius = 20

        # 【核心規則】：中途的敵方戰艦一定只能在海上出現，在陸上出現戰艦是錯誤的！
        # 若傳入之 x 座標落於陸地區域 (0~180, 380~580, 780~960)，自動依距離引導至最近深海航道 (180~380 或 580~780)
        if self.x <= 180:
            self.x = 260
        elif 380 <= self.x <= 480:
            self.x = 320
        elif 480 < self.x <= 580:
            self.x = 640
        elif self.x >= 780:
            self.x = 700

        self.rect = pygame.Rect(int(self.x - self.width // 2), int(self.y - self.length // 2), self.width, self.length)

        # 艦砲與艦載機冷卻計時
        self.fire_timer = random.uniform(1.0, 2.4)
        self.launch_timer = random.uniform(2.5, 4.0)

        # 航行航跡浪花 (Wake foam particles)
        self.wakes = []
        self.flash_timer = 0.0
        self.smoke_particles = []

    def update(self, dt):
        self.frame += 1
        self.flash_timer = max(0.0, self.flash_timer - dt)

        if self.is_sinking:
            self.sink_timer += dt
            self.y += (self.speed * 0.3) * dt * 60
            if self.sink_timer > 2.5:
                self.alive = False
            return

        # 艦隊巡弋航行
        self.y += self.speed * dt * 60
        self.rect.center = (int(self.x), int(self.y))

        # 航行白色浪花生成 (船尾產生洶湧航跡浪)
        if random.random() < 0.6:
            self.wakes.append({
                'x': self.x + random.uniform(-self.width * 0.3, self.width * 0.3),
                'y': self.y - self.length * 0.45,
                'radius': random.uniform(5.0, 13.0),
                'alpha': 210,
                'expand': random.uniform(0.3, 0.7)
            })

        # 船艏破浪白花
        if random.random() < 0.4:
            self.wakes.append({
                'x': self.x + random.choice([-1, 1]) * (self.width * 0.35),
                'y': self.y + self.length * 0.4,
                'radius': random.uniform(4.0, 8.0),
                'alpha': 180,
                'expand': 0.4
            })

        # 更新浪花淡出
        for w in self.wakes:
            w['y'] -= 1.0 * dt * 60
            w['radius'] += w['expand']
            w['alpha'] = max(0, w['alpha'] - int(240 * dt))
        self.wakes = [w for w in self.wakes if w['alpha'] > 0]

        # 受創濃煙
        if self.hp < self.max_hp * 0.5:
            if random.random() < 0.4:
                self.smoke_particles.append({
                    'x': self.x + random.randint(-15, 15),
                    'y': self.y + random.randint(-self.length // 4, self.length // 4),
                    'radius': random.uniform(4.0, 9.0),
                    'alpha': 190,
                    'vy': -random.uniform(1.0, 2.5)
                })

        for p in self.smoke_particles:
            p['y'] += p['vy'] * dt * 60
            p['radius'] += 0.3
            p['alpha'] = max(0, p['alpha'] - int(300 * dt))
        self.smoke_particles = [p for p in self.smoke_particles if p['alpha'] > 0]

        # 駛出螢幕邊界
        if self.y > SCREEN_HEIGHT + self.length:
            self.alive = False

    def check_attack(self, dt, player_pos):
        """艦砲開火砲擊玩家或航母放飛戰機"""
        if not self.alive or self.is_sinking or self.y < 50 or self.y > SCREEN_HEIGHT - 60:
            return [], []

        bullets = []
        new_planes = []

        self.fire_timer -= dt
        if self.fire_timer <= 0:
            px, py = player_pos
            ang = math.atan2(py - self.y, px - self.x)
            spd = 5.2 * self.bullet_mult

            if self.ship_type in ["battleship", "dreadnought"]:
                # 重型戰列艦 / 超重無畏艦：3~4 連裝重型主砲齊射
                self.fire_timer = random.uniform(1.8, 2.8) / self.bullet_mult
                spreads = [-0.28, -0.1, 0.1, 0.28] if self.ship_type == "dreadnought" else [-0.22, 0.0, 0.22]
                for spread in spreads:
                    rad = ang + spread
                    bullets.append(Bullet(self.x, self.y + 20, math.cos(rad) * spd, math.sin(rad) * spd,
                                          "boss_heavy_bullet", is_player=False))

            elif self.ship_type == "carrier":
                # 航空母艦：防空機槍與高角砲齊射
                self.fire_timer = random.uniform(2.0, 3.2) / self.bullet_mult
                for ox in [-25, 25]:
                    bullets.append(Bullet(self.x + ox, self.y + 10, math.cos(ang) * spd, math.sin(ang) * spd,
                                          "enemy_bullet", is_player=False))

            elif self.ship_type == "cruiser":
                # 巡洋艦：快速雙聯裝艦砲齊射
                self.fire_timer = random.uniform(1.4, 2.2) / self.bullet_mult
                for ox in [-12, 12]:
                    bullets.append(Bullet(self.x + ox, self.y + 15, math.cos(ang) * (spd + 0.6), math.sin(ang) * (spd + 0.6),
                                          "enemy_bullet", is_player=False))

            elif self.ship_type == "patrol_boat":
                # 巡邏快艇：高速靈動速射
                self.fire_timer = random.uniform(0.9, 1.4) / self.bullet_mult
                bullets.append(Bullet(self.x, self.y + 8, math.cos(ang) * (spd + 1.2), math.sin(ang) * (spd + 1.2),
                                      "enemy_bullet", is_player=False))

            else:  # gunboat
                # 砲艇：突擊速射
                self.fire_timer = random.uniform(1.2, 1.8) / self.bullet_mult
                bullets.append(Bullet(self.x, self.y + 10, math.cos(ang) * (spd + 1.0), math.sin(ang) * (spd + 1.0),
                                      "enemy_bullet", is_player=False))

        # 航空母艦定期從甲板彈射零式敵機升空！
        if self.ship_type == "carrier":
            self.launch_timer -= dt
            if self.launch_timer <= 0:
                self.launch_timer = random.uniform(4.5, 6.5)
                new_planes.append({
                    'x': self.x,
                    'y': self.y - 20,
                    'type': "scout_zero",
                    'pattern': random.choice(["swoop_left", "swoop_right", "dive_loop"])
                })

        return bullets, new_planes

    def take_damage(self, dmg):
        """承受傷害判定"""
        if not self.alive or self.is_sinking:
            return False

        self.hp -= dmg
        self.flash_timer = 0.08

        if self.hp <= 0:
            self.hp = 0
            self.is_sinking = True
            snd = SoundManager.get_instance()
            snd.play("ship_explosion")
            return True  # 擊沉
        return False

    def spawn_drops(self):
        """擊沉戰艦掉落豐厚戰果 (包含 P, S, B, W 與自動追蹤雷射 L)"""
        drops = []
        if self.ship_type == "dreadnought":
            drops.append(PowerUp(self.x - 24, self.y, 'P'))
            drops.append(PowerUp(self.x + 24, self.y, 'L'))
            drops.append(PowerUp(self.x, self.y + 20, 'S'))
            drops.append(PowerUp(self.x, self.y - 20, 'B'))
        elif self.ship_type == "battleship":
            drops.append(PowerUp(self.x - 20, self.y, 'P'))
            drops.append(PowerUp(self.x + 20, self.y, 'L'))
            drops.append(PowerUp(self.x, self.y + 20, 'S'))
        elif self.ship_type == "carrier":
            drops.append(PowerUp(self.x - 15, self.y, 'L'))
            drops.append(PowerUp(self.x + 15, self.y, 'W'))
        elif self.ship_type == "cruiser":
            drops.append(PowerUp(self.x, self.y, random.choice(['P', 'S', 'L'])))
        else:
            if random.random() < 0.6:
                drops.append(PowerUp(self.x, self.y, random.choice(['P', 'L'])))
        return drops

    def draw(self, surf):
        # 1. 繪製船體尾部湧浪與白色航跡水花
        for w in self.wakes:
            w_surf = pygame.Surface((int(w['radius'] * 2), int(w['radius'] * 2)), pygame.SRCALPHA)
            pygame.draw.circle(w_surf, (255, 255, 255, w['alpha']), (int(w['radius']), int(w['radius'])), int(w['radius']))
            surf.blit(w_surf, (int(w['x'] - w['radius']), int(w['y'] - w['radius'])))

        # 2. 繪製事先完成好之精緻多彩軍艦精靈圖 (Pre-rendered Exquisite & Colorful Naval Warship Sprite)
        cx, cy = int(self.x), int(self.y)
        ship_spr = create_warship_sprite(self.ship_type, self.frame // 3)

        if self.flash_timer > 0:
            ship_spr = ship_spr.copy()
            flash_overlay = pygame.Surface(ship_spr.get_size(), pygame.SRCALPHA)
            flash_overlay.fill((255, 255, 255, 130))
            ship_spr.blit(flash_overlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        if self.is_sinking:
            sink_alpha = max(0, int(255 * (1.0 - self.sink_timer / 2.5)))
            ship_spr = ship_spr.copy()
            ship_spr.set_alpha(sink_alpha)

        rect = ship_spr.get_rect(center=(cx, cy))
        surf.blit(ship_spr, rect)

        # 3. 繪製受損冒煙
        for p in self.smoke_particles:
            s_surf = pygame.Surface((int(p['radius'] * 2), int(p['radius'] * 2)), pygame.SRCALPHA)
            pygame.draw.circle(s_surf, (35, 35, 40, p['alpha']), (int(p['radius']), int(p['radius'])), int(p['radius']))
            surf.blit(s_surf, (int(p['x'] - p['radius']), int(p['y'] - p['radius'])))


class NavalFleetManager:
    """管理每關突入之敵主力聯合艦隊與不定時出現之大、中、小型敵艦"""
    def __init__(self):
        self.ships = []
        self.fleet_spawned = False
        self.second_fleet_spawned = False
        self.warning_active = False
        self.warning_timer = 0.0
        self.intermittent_timer = random.uniform(2.8, 4.8)

    def reset_for_stage(self):
        self.ships.clear()
        self.fleet_spawned = False
        self.second_fleet_spawned = False
        self.warning_active = False
        self.warning_timer = 0.0
        self.intermittent_timer = random.uniform(2.8, 4.8)

    def check_spawn(self, stage_time, spawn_duration, stage_idx, dt=0.016):
        """
        1. 在關卡前半段觸發敵主力聯合艦隊突入
        2. 在中途高頻率隨機出現大有小的敵方艦隊 (海面上大幅增加出現次數)
        3. 在關卡後半段觸發第二波敵主力特遣艦隊突入
        """
        # 1. 第一波主力艦隊突入 (約 25~35 秒)
        trigger_time = min(30.0, spawn_duration * 0.25)
        if stage_time >= trigger_time and not self.fleet_spawned:
            self.fleet_spawned = True
            self.warning_active = True
            self.warning_timer = 3.0

            snd = SoundManager.get_instance()
            snd.play("boss_alert")

            capital_type = "carrier" if stage_idx % 2 == 1 else "battleship"
            speed = 1.1 + stage_idx * 0.03
            mult = 1.0 + stage_idx * 0.03

            # 西翼海面航道戰鬥群 (Sea Lane 1: 180 ~ 380)
            self.ships.append(FleetShip(280, -180, capital_type, speed=speed, bullet_mult=mult))
            self.ships.append(FleetShip(225, -260, "cruiser", speed=speed + 0.15, bullet_mult=mult))
            self.ships.append(FleetShip(335, -260, "gunboat", speed=speed + 0.35, bullet_mult=mult))

            # 東翼海面航道突擊群 (Sea Lane 2: 580 ~ 780)
            self.ships.append(FleetShip(680, -220, "cruiser", speed=speed + 0.15, bullet_mult=mult))
            self.ships.append(FleetShip(625, -290, "gunboat", speed=speed + 0.35, bullet_mult=mult))
            self.ships.append(FleetShip(735, -290, "patrol_boat", speed=speed + 0.45, bullet_mult=mult))

        # 2. 第二波主力特遣艦隊突入 (約 85~95 秒，於中型大魔王後續推進時展開)
        second_trigger = max(75.0, spawn_duration * 0.70)
        if stage_time >= second_trigger and not self.second_fleet_spawned:
            self.second_fleet_spawned = True
            speed = 1.15 + stage_idx * 0.03
            mult = 1.05 + stage_idx * 0.03

            # 雙航道全面夾擊巡弋
            self.ships.append(FleetShip(270, -200, "dreadnought", speed=speed, bullet_mult=mult))
            self.ships.append(FleetShip(330, -280, "cruiser", speed=speed + 0.2, bullet_mult=mult))
            self.ships.append(FleetShip(670, -200, "carrier", speed=speed, bullet_mult=mult))
            self.ships.append(FleetShip(720, -280, "patrol_boat", speed=speed + 0.3, bullet_mult=mult))

        # 3. 海面密集巡弋出現敵方中型軍艦 (Cruiser) 與各型艦隊 (高頻率不定時生成)
        if stage_time >= 3.0 and stage_time < max(8.0, spawn_duration - 4.0):
            self.intermittent_timer -= dt
            if self.intermittent_timer <= 0:
                self.intermittent_timer = random.uniform(2.8, 5.2)  # 大幅增加海面上出現戰艦的次數
                speed = 1.0 + stage_idx * 0.02
                mult = 1.0 + stage_idx * 0.02

                # 航道隨機選擇：西翼深海航道 (220~340) 或 東翼深海航道 (620~740)
                lane = random.choice([
                    random.randint(220, 340),
                    random.randint(620, 740)
                ])

                scale_choice = random.choices(["medium", "small", "large"], weights=[55, 30, 15])[0]

                if scale_choice == "medium":
                    # 海上中型軍艦 (中型巡洋艦)
                    self.ships.append(FleetShip(lane, -140, "cruiser", speed=speed + 0.2, bullet_mult=mult))
                    if random.random() < 0.6:
                        sub_lane = 250 if lane > 500 else 690
                        self.ships.append(FleetShip(sub_lane, -190, "gunboat", speed=speed + 0.35, bullet_mult=mult))
                elif scale_choice == "small":
                    # 小型先鋒艇 / 魚雷快艇突襲 (1~2 艘)
                    self.ships.append(FleetShip(lane, -90, "patrol_boat", speed=speed + 0.6, bullet_mult=mult))
                    if random.random() < 0.6:
                        offset = 35 if lane < 300 or (580 < lane < 670) else -35
                        self.ships.append(FleetShip(lane + offset, -140, "gunboat", speed=speed + 0.45, bullet_mult=mult))
                else:
                    # 大型戰列艦、超重無畏旗艦或航母
                    big_type = random.choice(["battleship", "carrier", "dreadnought"])
                    self.ships.append(FleetShip(lane, -180, big_type, speed=speed, bullet_mult=mult))

    def update(self, dt, player_pos):
        if self.warning_active:
            self.warning_timer -= dt
            if self.warning_timer <= 0:
                self.warning_active = False

        bullets = []
        new_planes = []

        for s in self.ships:
            s.update(dt)
            if s.alive and not s.is_sinking:
                b_list, p_list = s.check_attack(dt, player_pos)
                bullets.extend(b_list)
                new_planes.extend(p_list)

        self.ships = [s for s in self.ships if s.alive]
        return bullets, new_planes

    def draw(self, surf):
        for s in self.ships:
            s.draw(surf)

    def draw_warning(self, surf):
        """繪製敵艦隊接近警報橫幅"""
        if self.warning_active and int(self.warning_timer * 4) % 2 == 0:
            bar = pygame.Surface((SCREEN_WIDTH, 60), pygame.SRCALPHA)
            bar.fill((180, 80, 20, 180))
            surf.blit(bar, (0, 180))

            from game.ui import get_font
            font = get_font(28)
            txt = font.render("! ! 警告：敵方海上主力艦隊接近中 ! !", True, COLOR_YELLOW)
            rect = txt.get_rect(center=(SCREEN_WIDTH // 2, 210))
            surf.blit(txt, rect)
