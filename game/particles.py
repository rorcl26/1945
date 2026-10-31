"""
1942: 天空狂怒 (Sky Fury 1942)
高效粒子系統與畫面特效 (Particles & Visual FX Engine)
強化豐富度與畫面生動感：多層次爆炸火光、噴射尾焰、殘影、衝擊波與護盾力場
"""

import math
import random
import pygame
from game.config import (
    COLOR_WHITE, COLOR_YELLOW, COLOR_ORANGE, COLOR_RED, COLOR_SHIELD, COLOR_CYAN
)

class Particle:
    __slots__ = ('x', 'y', 'vx', 'vy', 'color', 'radius', 'max_life', 'life', 'decay', 'gravity', 'shrink')

    def __init__(self, x, y, vx, vy, color, radius, life, decay=1.0, gravity=0.0, shrink=True):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.radius = radius
        self.max_life = life
        self.life = life
        self.decay = decay
        self.gravity = gravity
        self.shrink = shrink

    def update(self, dt):
        self.x += self.vx * dt * 60
        self.y += self.vy * dt * 60
        self.vy += self.gravity * dt * 60
        self.life -= self.decay * dt * 60
        return self.life > 0

    def draw(self, surf):
        if self.life <= 0:
            return
        progress = max(0.0, min(1.0, self.life / self.max_life))
        r = self.radius * progress if self.shrink else self.radius
        if r < 1:
            return
        # 繪製半透明火光粒子
        alpha = int(255 * progress)
        c = self.color
        if len(c) == 3:
            col = (c[0], c[1], c[2], alpha)
        else:
            col = (c[0], c[1], c[2], min(c[3], alpha))

        s = pygame.Surface((int(r * 2) + 2, int(r * 2) + 2), pygame.SRCALPHA)
        pygame.draw.circle(s, col, (int(r) + 1, int(r) + 1), int(r))
        surf.blit(s, (int(self.x - r), int(self.y - r)))


class Shockwave:
    """爆炸衝擊波圓環"""
    def __init__(self, x, y, max_radius=60, color=(255, 220, 100), duration=0.4, width=3):
        self.x = x
        self.y = y
        self.max_radius = max_radius
        self.color = color
        self.duration = duration
        self.timer = 0.0
        self.width = width

    def update(self, dt):
        self.timer += dt
        return self.timer < self.duration

    def draw(self, surf):
        prog = self.timer / self.duration
        r = int(self.max_radius * math.sqrt(prog))
        alpha = int(255 * (1.0 - prog))
        if r < 2 or alpha <= 0:
            return
        c = self.color
        s = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(s, (c[0], c[1], c[2], alpha), (r + 2, r + 2), r, self.width)
        surf.blit(s, (int(self.x - r - 2), int(self.y - r - 2)))


class ParticleManager:
    """管理所有戰場上的粒子特效"""
    def __init__(self):
        self.particles = []
        self.shockwaves = []
        self.afterimages = []
        self.screen_shake = 0.0

    def add_screen_shake(self, amount):
        self.screen_shake = min(20.0, self.screen_shake + amount)

    def get_shake_offset(self):
        if self.screen_shake > 0.5:
            ox = random.uniform(-self.screen_shake, self.screen_shake)
            oy = random.uniform(-self.screen_shake, self.screen_shake)
            return int(ox), int(oy)
        return 0, 0

    def add_engine_exhaust(self, x, y, color=(255, 180, 50), boost=False):
        """戰機推進器火花微粒子"""
        count = 3 if boost else 1
        for _ in range(count):
            vx = random.uniform(-0.8, 0.8)
            vy = random.uniform(2.5, 4.5) if not boost else random.uniform(4.0, 7.0)
            rad = random.uniform(2.5, 4.5) if boost else random.uniform(1.5, 3.0)
            life = random.uniform(8.0, 16.0)
            col = random.choice([color, (255, 230, 100), (255, 80, 20)])
            self.particles.append(Particle(x, y, vx, vy, col, rad, life, decay=1.2))

    def add_bullet_hit(self, x, y, color=COLOR_YELLOW):
        """子彈擊中產生的四射火星"""
        for _ in range(8):
            ang = random.uniform(0, 2 * math.pi)
            spd = random.uniform(1.5, 4.0)
            vx = math.cos(ang) * spd
            vy = math.sin(ang) * spd
            self.particles.append(Particle(
                x, y, vx, vy, color, random.uniform(1.5, 3.0),
                random.uniform(10, 20), decay=1.5
            ))

    def add_explosion(self, x, y, scale=1.0, is_boss=False):
        """爆炸火球與濃煙 (scale=1.0 為一般敵機，3.0 為 BOSS)"""
        count = int(25 * scale)
        # 火焰核心
        for _ in range(count):
            ang = random.uniform(0, 2 * math.pi)
            spd = random.uniform(1.0, 5.0) * scale
            col = random.choice([
                COLOR_WHITE, (255, 240, 100), (255, 160, 30),
                (255, 60, 20), (180, 20, 20)
            ])
            self.particles.append(Particle(
                x, y, math.cos(ang) * spd, math.sin(ang) * spd,
                col, random.uniform(3.0, 7.0) * scale,
                random.uniform(15, 30) * scale, decay=1.0
            ))
        # 煙霧
        smoke_count = int(12 * scale)
        for _ in range(smoke_count):
            ang = random.uniform(0, 2 * math.pi)
            spd = random.uniform(0.5, 2.5) * scale
            col = random.choice([(70, 70, 70), (100, 100, 100), (40, 40, 40)])
            self.particles.append(Particle(
                x, y, math.cos(ang) * spd, math.sin(ang) * spd - 0.5,
                col, random.uniform(5.0, 11.0) * scale,
                random.uniform(25, 45) * scale, decay=0.8
            ))

        # 衝擊波
        self.shockwaves.append(Shockwave(
            x, y, max_radius=int(50 * scale),
            color=(255, 230, 120), duration=0.35 * min(scale, 1.8)
        ))
        # 震動螢幕
        self.add_screen_shake(2.5 * scale)

    def add_afterimage(self, surf, x, y, alpha=160, duration=0.25):
        """翻轉閃避時留下的光影殘影"""
        self.afterimages.append({
            'surf': surf.copy(),
            'x': x,
            'y': y,
            'alpha': alpha,
            'max_alpha': alpha,
            'duration': duration,
            'timer': 0.0
        })

    def update(self, dt):
        if self.screen_shake > 0:
            self.screen_shake = max(0.0, self.screen_shake - dt * 25.0)

        self.particles = [p for p in self.particles if p.update(dt)]
        self.shockwaves = [sw for sw in self.shockwaves if sw.update(dt)]

        # 更新殘影
        new_after = []
        for af in self.afterimages:
            af['timer'] += dt
            if af['timer'] < af['duration']:
                new_after.append(af)
        self.afterimages = new_after

    def draw(self, surf):
        # 繪製殘影
        for af in self.afterimages:
            prog = 1.0 - (af['timer'] / af['duration'])
            alpha = int(af['max_alpha'] * prog)
            s = af['surf'].copy()
            s.set_alpha(alpha)
            surf.blit(s, (af['x'], af['y']))

        # 繪製衝擊波
        for sw in self.shockwaves:
            sw.draw(surf)

        # 繪製所有粒子
        for p in self.particles:
            p.draw(surf)
