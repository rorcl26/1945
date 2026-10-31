"""
1945: 二戰空間（II War Space）
彈幕與武器系統 (Weapons & Projectiles System)
包含機砲、散彈、追蹤飛彈、高能雷射、敵方扇形彈幕以及戰利品寶物
"""

import math
import random
import pygame
from game.config import SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_YELLOW, COLOR_CYAN
from game.sprites import create_bullet_sprite, create_powerup_sprite

class Bullet:
    def __init__(self, x, y, vx, vy, b_type="player_vulcan", damage=25, is_player=True):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.b_type = b_type
        self.damage = damage
        self.is_player = is_player
        self.alive = True

        # 碰撞矩形
        if is_player:
            self.radius = 6 if "laser" not in b_type else 8
        else:
            self.radius = 5 if "heavy" not in b_type else 9

        # 圖形
        angle = math.degrees(math.atan2(-vy, vx)) - 90
        self.sprite = create_bullet_sprite(b_type, angle)
        self.rect = self.sprite.get_rect(center=(int(x), int(y)))

    def update(self, dt):
        self.x += self.vx * dt * 60
        self.y += self.vy * dt * 60
        self.rect.center = (int(self.x), int(self.y))

        # 移出螢幕外銷毀
        if (self.x < -30 or self.x > SCREEN_WIDTH + 30 or
            self.y < -40 or self.y > SCREEN_HEIGHT + 40):
            self.alive = False

    def draw(self, surf):
        surf.blit(self.sprite, self.rect)


class HomingMissile(Bullet):
    """追蹤微型火箭：朝向最近的敵機或 BOSS 轉向追擊"""
    def __init__(self, x, y, vx, vy, damage=40, target=None):
        super().__init__(x, y, vx, vy, "player_missile", damage, is_player=True)
        self.target = target
        self.speed = 9.0
        self.turn_rate = 0.08
        self.angle = math.atan2(vy, vx)

    def update(self, dt):
        # 尋找或更新目標
        if self.target and getattr(self.target, 'alive', False):
            tx, ty = self.target.x, self.target.y
            desired_angle = math.atan2(ty - self.y, tx - self.x)
            # 漸進平滑轉向
            diff = (desired_angle - self.angle + math.pi) % (2 * math.pi) - math.pi
            self.angle += max(-self.turn_rate, min(self.turn_rate, diff))
            self.vx = math.cos(self.angle) * self.speed
            self.vy = math.sin(self.angle) * self.speed
        else:
            # 原方向持續加速前進
            self.vy = -self.speed

        self.x += self.vx * dt * 60
        self.y += self.vy * dt * 60
        self.rect.center = (int(self.x), int(self.y))

        if (self.x < -30 or self.x > SCREEN_WIDTH + 30 or
            self.y < -40 or self.y > SCREEN_HEIGHT + 40):
            self.alive = False


class HomingLaser(Bullet):
    """
    我方高能自動追蹤雷射 (Auto-Targeting Homing Laser)
    吃到雷射戰果 (L) 後獲得，雷射光柱具備自動搜尋敵機、地面戰車、海上戰艦與 BOSS 並弧形鎖定追蹤能力
    """
    def __init__(self, x, y, vx=0, vy=-16, damage=35, target=None):
        super().__init__(x, y, vx, vy, "player_homing_laser", damage, is_player=True)
        self.target = target
        self.speed = 16.0
        self.turn_rate = 0.16  # 靈敏高響應追蹤鎖定
        self.angle = math.atan2(vy, vx)
        self.radius = 9
        self.trail = []

    def update(self, dt):
        # 目標若失效，動態重新校正鎖定
        if self.target and getattr(self.target, 'alive', False) and not getattr(self.target, 'is_sinking', False):
            tx, ty = self.target.x, self.target.y
            desired_angle = math.atan2(ty - self.y, tx - self.x)
            diff = (desired_angle - self.angle + math.pi) % (2 * math.pi) - math.pi
            self.angle += max(-self.turn_rate, min(self.turn_rate, diff))
            self.vx = math.cos(self.angle) * self.speed
            self.vy = math.sin(self.angle) * self.speed
        else:
            self.vy = -self.speed

        self.x += self.vx * dt * 60
        self.y += self.vy * dt * 60
        self.rect.center = (int(self.x), int(self.y))

        # 更新雷射能量光痕
        self.trail.append((int(self.x), int(self.y)))
        if len(self.trail) > 5:
            self.trail.pop(0)

        if (self.x < -40 or self.x > SCREEN_WIDTH + 40 or
            self.y < -50 or self.y > SCREEN_HEIGHT + 50):
            self.alive = False

    def draw(self, surf):
        # 繪製高能雷射殘影光軌
        for i, (tx, ty) in enumerate(self.trail):
            rad = max(2, int(4 * (i + 1) / len(self.trail)))
            alpha = int(120 * (i + 1) / len(self.trail))
            t_surf = pygame.Surface((rad * 2 + 2, rad * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(t_surf, (0, 255, 230, alpha), (rad + 1, rad + 1), rad)
            surf.blit(t_surf, (tx - rad - 1, ty - rad - 1))
        surf.blit(self.sprite, self.rect)


class PowerUp:
    """敵機擊破後掉落的戰果 (P: 武器威力、S: 防護罩/血量修復、B: 炸彈、W: 武器變換、L: 自動追蹤雷射)"""
    def __init__(self, x, y, p_type=None):
        self.x = x
        self.y = y
        self.vx = random.uniform(-0.8, 0.8)
        self.vy = random.uniform(1.2, 2.2)
        self.type = p_type if p_type else random.choices(['P', 'S', 'B', 'W', 'L'], weights=[35, 25, 10, 10, 20])[0]
        self.alive = True
        self.frame = 0
        self.radius = 16
        self.rect = pygame.Rect(int(x - 16), int(y - 16), 32, 32)

    def update(self, dt, player_pos=None):
        self.frame += 1
        # 當玩家靠近時產生磁吸效果 (自動吸附戰果)
        if player_pos:
            px, py = player_pos
            dist = math.hypot(px - self.x, py - self.y)
            if dist < 160:
                self.vx += ((px - self.x) / dist) * 0.4
                self.vy += ((py - self.y) / dist) * 0.4

        self.x += self.vx * dt * 60
        self.y += self.vy * dt * 60
        self.rect.center = (int(self.x), int(self.y))

        # 碰觸螢幕左右邊界彈跳
        if self.x < 20 or self.x > SCREEN_WIDTH - 20:
            self.vx = -self.vx

        if self.y > SCREEN_HEIGHT + 40:
            self.alive = False

    def draw(self, surf):
        spr = create_powerup_sprite(self.type, self.frame // 3)
        surf.blit(spr, self.rect)

