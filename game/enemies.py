"""
1945: 二戰空間（II War Space）
多樣化敵機與編隊系統 (Enemies & Formation Spawner)
包含零式偵察機、黃黑高速截擊機、雙發重型轟炸機、空中砲艇與海面驅逐艦
"""

import math
import random
import pygame
import game.config as cfg
from game.config import SCREEN_HEIGHT
from game.sprites import create_enemy_sprite, create_tank_sprite
from game.weapons import Bullet, PowerUp
from game.audio import SoundManager

class Enemy:
    def __init__(self, x, y, enemy_type="scout_zero", hp=None, pattern="straight", speed=3.0, bullet_mult=1.0, spawn_from_bottom=False, spawn_direction=None, screen_width=None):
        self.x = x
        self.y = y
        self.enemy_type = enemy_type
        self.screen_width = cfg.SCREEN_WIDTH if screen_width is None else screen_width

        # 【核心規則】：敵方可由上下左右出現 (top, bottom, left, right)
        if spawn_direction is None:
            self.spawn_direction = "bottom" if spawn_from_bottom else "top"
        else:
            self.spawn_direction = spawn_direction
        self.spawn_from_bottom = (self.spawn_direction == "bottom")

        # 敵機血量設定：中間的敵人飛機在打擊 1 至 2 次後才潰敗 (玩家單發子彈傷害約 25~35)
        if hp is None:
            if enemy_type == "scout_zero":
                hp = 25          # 1 擊潰敗 (或輕微擦彈 2 擊)
            elif enemy_type == "fast_interceptor":
                hp = 45          # 經 1 擊扣 25 滴剩 20 滴 (機體受損冒煙)，第 2 擊立即潰敗！
            elif enemy_type == "twin_bomber":
                hp = 48          # 經 1 擊扣 25 滴剩 23 滴，第 2 擊立即潰敗！
            elif enemy_type == "heavy_gunship":
                hp = 85
            elif enemy_type == "sea_destroyer":
                hp = 90
            else:
                hp = 25

        self.hp = hp
        self.max_hp = hp
        self.pattern = pattern
        self.speed = speed
        self.bullet_mult = bullet_mult
        self.alive = True
        self.frame = random.randint(0, 100)

        # 受創與冒煙狀態 (1 擊受損冒煙，2 擊擊潰)
        self.hits_taken = 0
        self.is_smoking = False
        self.flash_timer = 0.0
        self.smoke_particles = []

        # 軌跡運算
        self.init_x = x
        self.init_y = y
        self.time = 0.0

        # 射擊計時
        self.fire_timer = random.uniform(0.6, 2.2)

        # 幾何尺寸
        if enemy_type == "scout_zero":
            self.radius = 18
            self.score = 100
        elif enemy_type == "fast_interceptor":
            self.radius = 20
            self.score = 180
        elif enemy_type == "twin_bomber":
            self.radius = 28
            self.score = 350
        elif enemy_type == "heavy_gunship":
            self.radius = 36
            self.score = 600
        elif enemy_type == "sea_destroyer":
            self.radius = 26
            self.score = 450
        else:
            self.radius = 18
            self.score = 100

        self.rect = pygame.Rect(int(self.x - self.radius), int(self.y - self.radius), self.radius * 2, self.radius * 2)

    def update(self, dt):
        self.time += dt
        self.frame += 1
        self.flash_timer = max(0.0, self.flash_timer - dt)

        # 受損引擎黑煙粒子更新
        if self.is_smoking:
            if random.random() < 0.4:
                if self.spawn_direction == "bottom":
                    smoke_vx, smoke_vy = 0, random.uniform(1.0, 2.5)
                    ox, oy = random.randint(-4, 4), 10
                elif self.spawn_direction == "top":
                    smoke_vx, smoke_vy = 0, -random.uniform(1.0, 2.5)
                    ox, oy = random.randint(-4, 4), -10
                elif self.spawn_direction == "left":
                    smoke_vx, smoke_vy = -random.uniform(1.0, 2.5), 0
                    ox, oy = -10, random.randint(-4, 4)
                else:  # right
                    smoke_vx, smoke_vy = random.uniform(1.0, 2.5), 0
                    ox, oy = 10, random.randint(-4, 4)

                self.smoke_particles.append({
                    'x': self.x + ox,
                    'y': self.y + oy,
                    'radius': random.uniform(3.0, 7.0),
                    'alpha': 180,
                    'vx': smoke_vx,
                    'vy': smoke_vy
                })

        for p in self.smoke_particles:
            p['x'] += p.get('vx', 0) * dt * 60
            p['y'] += p.get('vy', 0) * dt * 60
            p['radius'] += 0.25
            p['alpha'] = max(0, p['alpha'] - int(350 * dt))
        self.smoke_particles = [p for p in self.smoke_particles if p['alpha'] > 0]

        # 【核心規則】：敵方戰機可由上下左右出現 (top, bottom, left, right)
        if self.spawn_direction == "bottom":
            if self.pattern in ["climb_straight", "straight"]:
                self.y -= self.speed * dt * 60
            elif self.pattern in ["climb_sine", "sine"]:
                self.y -= self.speed * dt * 60
                self.x = self.init_x + 90 * math.sin(self.time * 2.5)
            elif self.pattern in ["climb_swoop_left", "swoop_left"]:
                self.y -= self.speed * dt * 60
                self.x -= 2.2 * dt * 60
            elif self.pattern in ["climb_swoop_right", "swoop_right"]:
                self.y -= self.speed * dt * 60
                self.x += 2.2 * dt * 60
            elif self.pattern == "dive_loop":
                self.y -= self.speed * dt * 60
                if self.y < SCREEN_HEIGHT - 180 and self.time < 3.0:
                    self.x += 4.0 * math.sin(self.time * 3.5) * dt * 60
                    self.y += 1.5 * dt * 60
            else:
                self.y -= self.speed * dt * 60

        elif self.spawn_direction == "left":
            # 由左方出現向右方突進
            if self.pattern == "straight":
                self.x += self.speed * dt * 60
            elif self.pattern == "sine":
                self.x += self.speed * dt * 60
                self.y = self.init_y + 80 * math.sin(self.time * 2.5)
            elif self.pattern in ["swoop_left", "swoop_up"]:
                self.x += self.speed * dt * 60
                self.y -= 2.0 * dt * 60
            elif self.pattern in ["swoop_right", "swoop_down"]:
                self.x += self.speed * dt * 60
                self.y += 2.0 * dt * 60
            elif self.pattern == "dive_loop":
                self.x += self.speed * dt * 60
                if self.x > 180 and self.time < 3.0:
                    self.y += 3.5 * math.sin(self.time * 3.5) * dt * 60
                    self.x -= 1.0 * dt * 60
            else:
                self.x += self.speed * dt * 60

        elif self.spawn_direction == "right":
            # 由右方出現向左方突進
            if self.pattern == "straight":
                self.x -= self.speed * dt * 60
            elif self.pattern == "sine":
                self.x -= self.speed * dt * 60
                self.y = self.init_y + 80 * math.sin(self.time * 2.5)
            elif self.pattern in ["swoop_left", "swoop_up"]:
                self.x -= self.speed * dt * 60
                self.y -= 2.0 * dt * 60
            elif self.pattern in ["swoop_right", "swoop_down"]:
                self.x -= self.speed * dt * 60
                self.y += 2.0 * dt * 60
            elif self.pattern == "dive_loop":
                self.x -= self.speed * dt * 60
                if self.x < self.screen_width - 180 and self.time < 3.0:
                    self.y += 3.5 * math.sin(self.time * 3.5) * dt * 60
                    self.x += 1.0 * dt * 60
            else:
                self.x -= self.speed * dt * 60

        else:
            # 依不同移動路徑由上方進行航行 (Formation Flight Paths from Top)
            if self.pattern == "straight":
                self.y += self.speed * dt * 60
            elif self.pattern == "sine":
                self.y += self.speed * dt * 60
                self.x = self.init_x + 90 * math.sin(self.time * 2.5)
            elif self.pattern == "dive_loop":
                # 經典 1945 俯衝大迴旋
                self.y += self.speed * dt * 60
                if self.y > 180 and self.time < 3.0:
                    self.x += 4.0 * math.sin(self.time * 3.5) * dt * 60
                    self.y -= 1.5 * dt * 60
            elif self.pattern == "swoop_left":
                self.y += self.speed * dt * 60
                self.x -= 2.2 * dt * 60
            elif self.pattern == "swoop_right":
                self.y += self.speed * dt * 60
                self.x += 2.2 * dt * 60
            elif self.pattern == "hover":
                # 戰艦慢速巡航
                self.y += (self.speed * 0.4) * dt * 60
                self.x = self.init_x + 30 * math.sin(self.time * 1.2)

        self.rect.center = (int(self.x), int(self.y))

        # 超出螢幕邊界刪除 (上下左右四向判定)
        if self.spawn_direction == "bottom":
            if self.y < -80 or self.x < -80 or self.x > self.screen_width + 80:
                self.alive = False
        elif self.spawn_direction == "top":
            if self.y > SCREEN_HEIGHT + 80 or self.x < -80 or self.x > self.screen_width + 80:
                self.alive = False
        elif self.spawn_direction == "left":
            if self.x > self.screen_width + 80 or self.y < -80 or self.y > SCREEN_HEIGHT + 80:
                self.alive = False
        elif self.spawn_direction == "right":
            if self.x < -80 or self.y < -80 or self.y > SCREEN_HEIGHT + 80:
                self.alive = False

    def check_shoot(self, dt, player_pos):
        """依敵機類型向玩家方向開火射擊"""
        if not self.alive or self.y < 40 or self.y > SCREEN_HEIGHT - 40:
            return []

        self.fire_timer -= dt
        if self.fire_timer > 0:
            return []

        # 重設射擊週期
        safe_mult = max(0.1, self.bullet_mult)
        if self.enemy_type == "scout_zero":
            self.fire_timer = random.uniform(1.8, 3.0) / safe_mult
        elif self.enemy_type == "fast_interceptor":
            self.fire_timer = random.uniform(1.4, 2.4) / safe_mult
        elif self.enemy_type == "twin_bomber":
            self.fire_timer = random.uniform(1.6, 2.5) / safe_mult
        else:
            self.fire_timer = random.uniform(1.5, 2.2) / safe_mult

        bullets = []
        px, py = player_pos
        ang = math.atan2(py - self.y, px - self.x)
        spd = 5.5 * self.bullet_mult

        if self.enemy_type == "scout_zero":
            # 單發精準瞄準彈
            vx = math.cos(ang) * spd
            vy = math.sin(ang) * spd
            bullets.append(Bullet(self.x, self.y + 10, vx, vy, "enemy_bullet", is_player=False))
        elif self.enemy_type == "fast_interceptor":
            # 雙連發突擊彈
            for ox in [-6, 6]:
                bullets.append(Bullet(self.x + ox, self.y + 8, math.cos(ang) * (spd + 1.0), math.sin(ang) * (spd + 1.0), "enemy_bullet", is_player=False))
        elif self.enemy_type in ["twin_bomber", "heavy_gunship"]:
            # 3向或5向扇形彈幕
            count = 3 if self.enemy_type == "twin_bomber" else 5
            spread = 18
            for i in range(count):
                cur_ang = ang + math.radians((i - (count - 1) / 2) * spread)
                bullets.append(Bullet(self.x, self.y + 12, math.cos(cur_ang) * spd, math.sin(cur_ang) * spd, "enemy_bullet", is_player=False))
        elif self.enemy_type == "sea_destroyer":
            # 艦砲向兩側與前方齊射
            for cur_ang in [ang - 0.25, ang, ang + 0.25]:
                bullets.append(Bullet(self.x, self.y + 15, math.cos(cur_ang) * (spd - 0.5), math.sin(cur_ang) * (spd - 0.5), "enemy_bullet", is_player=False))

        return bullets

    def take_damage(self, dmg):
        self.hits_taken += 1
        self.hp -= dmg
        self.flash_timer = 0.08
        if self.hp <= 0:
            self.alive = False
            return True  # 擊毀 (打擊 1 至 2 次後潰敗)
        else:
            self.is_smoking = True
            return False

    def spawn_drops(self):
        """敵機被擊潰時掉落戰果 (由 Game 統一管理每 5 架擊斃出現 1 個寶物)"""
        return []

    def draw(self, surf):
        if not self.alive:
            return

        # 繪製受損時的引擎黑煙粒子
        for p in self.smoke_particles:
            r = max(1, int(p['radius']))
            s_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(s_surf, (40, 40, 45, max(0, min(255, int(p['alpha'])))), (r, r), r)
            surf.blit(s_surf, (int(p['x'] - r), int(p['y'] - r)))

        spr = create_enemy_sprite(self.enemy_type, self.frame // 3)

        # 【核心規則】：依敵方出現方向 (上下左右) 朝向行進方向
        if self.spawn_direction == "bottom":
            spr = pygame.transform.flip(spr, False, True)
        elif self.spawn_direction == "left":
            spr = pygame.transform.rotate(spr, 90)
        elif self.spawn_direction == "right":
            spr = pygame.transform.rotate(spr, -90)

        # 受創白熱/紅閃爍
        if self.flash_timer > 0:
            spr = spr.copy()
            flash_overlay = pygame.Surface(spr.get_size(), pygame.SRCALPHA)
            flash_overlay.fill((255, 200, 200, 140))
            spr.blit(flash_overlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        rect = spr.get_rect(center=(int(self.x), int(self.y)))
        surf.blit(spr, rect)


class EnemyTank:
    """
    敵方地面裝甲戰車 (Enemy Ground Armored Tank)
    偶而在陸地海岸線上出現，具備活動履帶與可 360 度鎖定玩家的旋轉砲塔，向我方開火重型加農加榴砲彈
    """
    def __init__(self, x, y, hp=55, speed=1.1, bullet_mult=1.0, screen_width=None):
        self.x = x
        self.y = y
        self.hp = hp
        self.max_hp = hp
        self.speed = speed
        self.bullet_mult = bullet_mult
        self.screen_width = cfg.SCREEN_WIDTH if screen_width is None else screen_width
        self.alive = True
        self.is_tank = True
        self.enemy_type = "ground_tank"
        self.score = 450
        self.radius = 22
        self.rect = pygame.Rect(int(self.x - 22), int(self.y - 22), 44, 44)

        # 砲塔旋轉與砲擊冷卻
        self.turret_angle = 90.0
        self.fire_timer = random.uniform(1.2, 2.5)
        self.frame = random.randint(0, 100)

        # 受創與黑煙/履帶塵土
        self.hits_taken = 0
        self.is_smoking = False
        self.flash_timer = 0.0
        self.smoke_particles = []
        self.dust_particles = []

    def update(self, dt, player_pos=None, bg_mgr=None):
        self.frame += 1
        self.flash_timer = max(0.0, self.flash_timer - dt)

        # 【核心規則】：陸上的坦克遇到背景是海面時就停在該處就好，不要跑到背景圖的海面上
        next_y = self.y + self.speed * dt * 60
        if bg_mgr and not bg_mgr.is_land_position(self.x, next_y):
            # 下一步是海面，停在該處陸地邊緣 (原地作為岸防要塞砲台)，不進入海面！
            pass
        else:
            self.y = next_y

        self.rect.center = (int(self.x), int(self.y))

        if player_pos:
            px, py = player_pos
            desired_angle = math.degrees(math.atan2(py - self.y, px - self.x))
            diff = (desired_angle - self.turret_angle + 180) % 360 - 180
            self.turret_angle += max(-4.0, min(4.0, diff))

        # 履帶揚塵粒子
        if random.random() < 0.25:
            self.dust_particles.append({
                'x': self.x + random.choice([-14, 14]),
                'y': self.y - 12,
                'radius': random.uniform(2.5, 5.0),
                'alpha': 140,
                'vy': -random.uniform(0.5, 1.5)
            })

        for p in self.dust_particles:
            p['y'] += p['vy'] * dt * 60
            p['radius'] += 0.2
            p['alpha'] = max(0, p['alpha'] - int(280 * dt))
        self.dust_particles = [p for p in self.dust_particles if p['alpha'] > 0]

        # 受創濃煙粒子
        if self.is_smoking:
            if random.random() < 0.35:
                self.smoke_particles.append({
                    'x': self.x + random.randint(-6, 6),
                    'y': self.y - 6,
                    'radius': random.uniform(3.0, 7.0),
                    'alpha': 180,
                    'vy': -random.uniform(1.0, 2.2)
                })

        for p in self.smoke_particles:
            p['y'] += p['vy'] * dt * 60
            p['radius'] += 0.25
            p['alpha'] = max(0, p['alpha'] - int(320 * dt))
        self.smoke_particles = [p for p in self.smoke_particles if p['alpha'] > 0]

        # 超出螢幕邊界刪除 (相容 1P 960 與 2P 1024 寬度)
        max_w = max(self.screen_width, cfg.SCREEN_WIDTH)
        if self.y > SCREEN_HEIGHT + 60 or self.x < -60 or self.x > max_w + 60:
            self.alive = False

    def check_shoot(self, dt, player_pos):
        """戰車旋轉砲塔鎖定玩家戰機並開火"""
        if not self.alive or self.y < 30 or self.y > SCREEN_HEIGHT - 60:
            return []

        # 平滑轉向玩家
        px, py = player_pos
        desired_angle = math.degrees(math.atan2(py - self.y, px - self.x))
        diff = (desired_angle - self.turret_angle + 180) % 360 - 180
        self.turret_angle += max(-6.0, min(6.0, diff))

        self.fire_timer -= dt
        if self.fire_timer > 0:
            return []

        safe_mult = max(0.1, self.bullet_mult)
        self.fire_timer = random.uniform(1.8, 3.0) / safe_mult
        ang = math.atan2(py - self.y, px - self.x)
        spd = 5.2 * safe_mult

        # 加農砲口發射點
        turret_rad = math.radians(self.turret_angle)
        muzzle_x = self.x + math.cos(turret_rad) * 18
        muzzle_y = self.y + math.sin(turret_rad) * 18

        # 發射敵方專屬燃燒加農砲彈 (鮮紅橙烈焰彈頭)
        return [Bullet(muzzle_x, muzzle_y, math.cos(ang) * spd, math.sin(ang) * spd, "tank_shell", is_player=False)]

    def take_damage(self, dmg):
        self.hits_taken += 1
        self.hp -= dmg
        self.flash_timer = 0.08
        if self.hp <= 0:
            self.alive = False
            snd = SoundManager.get_instance()
            snd.play("tank_explosion")
            return True  # 擊毀
        else:
            self.is_smoking = True
            return False

    def spawn_drops(self):
        """地面戰車擊毀掉落戰果 (由 Game 統一管理每 5 架擊斃出現 1 個寶物)"""
        return []

    def draw(self, surf):
        if not self.alive:
            return

        # 1. 履帶揚塵
        for p in self.dust_particles:
            r = max(1, int(p['radius']))
            d_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(d_surf, (140, 125, 95, max(0, min(255, int(p['alpha'])))), (r, r), r)
            surf.blit(d_surf, (int(p['x'] - r), int(p['y'] - r)))

        # 2. 受損黑煙
        for p in self.smoke_particles:
            r = max(1, int(p['radius']))
            s_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(s_surf, (40, 40, 45, max(0, min(255, int(p['alpha'])))), (r, r), r)
            surf.blit(s_surf, (int(p['x'] - r), int(p['y'] - r)))

        # 3. 戰車精靈圖 (旋轉砲塔與動態履帶)
        spr = create_tank_sprite(self.turret_angle, self.frame // 3)

        if self.flash_timer > 0:
            spr = spr.copy()
            flash_overlay = pygame.Surface(spr.get_size(), pygame.SRCALPHA)
            flash_overlay.fill((255, 200, 200, 140))
            spr.blit(flash_overlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        rect = spr.get_rect(center=(int(self.x), int(self.y)))
        surf.blit(spr, rect)

