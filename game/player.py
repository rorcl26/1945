"""
1945: 天空狂怒 (Sky Fury 1945)
玩家戰機核心邏輯 (Player Fighter Class)
實現 4 種戰機選擇、五次完整生命力、被擊中損失十分之一血量、戰果升級武器與護盾、按鍵 Z 翻轉閃避/護盾特殊技
支援吃到寶物後變身為 2~3 個戰機組合體協同密集攻擊 (Formation Combo Wingmen)
"""

import math
import random
import pygame
from game.config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, MAX_LIVES, MAX_HP, DAMAGE_PER_HIT,
    RESPAWN_INVULNERABLE_TIME, COLOR_WHITE, COLOR_SHIELD, COLOR_CYAN,
    FIGHTER_TYPES, HUD_TOP_HEIGHT, HUD_BOTTOM_HEIGHT
)
from game.sprites import create_player_sprite, create_wingman_sprite
from game.weapons import Bullet, HomingMissile, HomingLaser
from game.audio import SoundManager

class Player:
    def __init__(self, fighter_config):
        self.config = fighter_config
        self.fighter_id = fighter_config["id"]
        self.name = fighter_config["name"]
        self.speed = fighter_config["speed"]
        self.base_fire_rate = fighter_config["fire_rate"]
        self.weapon_type = fighter_config["weapon_type"]
        self.has_laser = False  # 吃到 L 寶物後解鎖全自動追蹤雷射

        # 生命力與防禦核心規則 (嚴格滿足題目要求)
        self.lives = MAX_LIVES           # 每次遊戲具有五次完整的生命力 (5條命)
        self.hp = MAX_HP                 # 當前生命完整血量 (100)
        self.max_hp = MAX_HP
        self.alive = True
        self.game_over = False

        # 戰果威力升級 (Power Level 1 ~ 5)
        self.power_level = 1
        self.max_power_level = 5

        # 組合體編隊戰機 (1=單機, 2=雙機連線組合體, 3=三機黃金三角組合體)
        # 吃到寶物後升級為 2~3 個組合體共同前進並進行密集齊射
        self.formation_units = 1

        # 座標與移動
        self.x = SCREEN_WIDTH // 2
        self.y = SCREEN_HEIGHT - 120
        self.radius = 20
        self.rect = pygame.Rect(int(self.x - 24), int(self.y - 24), 48, 48)

        # 姿態與動畫
        self.bank_state = "center"  # 'left', 'right', 'center'
        self.frame = 0

        # 射擊計時
        self.fire_timer = 0.0

        # 特殊功能鍵 (Z 鍵)：翻轉閃避 (Barrel Roll) 或 能量防護罩 (Shield)
        self.special_type = fighter_config["special_type"]
        self.special_cooldown = fighter_config["special_cooldown"]
        self.special_duration = fighter_config["special_duration"]
        self.special_timer = 0.0      # 當前冷卻計時
        self.is_performing_special = False
        self.special_active_timer = 0.0
        self.roll_angle = 0.0

        # 無敵狀態 (重生保護或閃避無敵)
        self.invulnerable_timer = RESPAWN_INVULNERABLE_TIME

        # 全防禦能力與防護罩
        self.shield_active = False
        self.shield_capacity = 100.0  # 額外護盾能量槽
        self.shield_pulse = 0.0

    def trigger_special(self):
        """按鍵 Z 觸發特殊功能"""
        if self.special_timer <= 0 and not self.is_performing_special and self.alive:
            self.is_performing_special = True
            self.special_active_timer = self.special_duration
            self.special_timer = self.special_cooldown
            self.invulnerable_timer = max(self.invulnerable_timer, self.special_duration)

            snd = SoundManager.get_instance()
            if self.special_type == "roll":
                self.roll_angle = 0.0
                snd.play("barrel_roll")
            else:
                self.shield_active = True
                snd.play("shield")
            return True
        return False

    def take_hit(self):
        """
        受敵方子彈或碰撞攻擊判定
        嚴格遵循：「被敵方子彈攻擊後會損失十分之一的生命力，直到滅亡。每次的遊戲具有五次完整的生命力。」
        """
        if self.invulnerable_timer > 0 or not self.alive:
            return False  # 無敵狀態免疫

        # 損失十分之一生命力 (100 的 1/10 = 10 點傷害)
        self.hp -= DAMAGE_PER_HIT
        snd = SoundManager.get_instance()
        snd.play("player_hit")

        # 短暫中彈閃爍保護 (0.3 秒)
        self.invulnerable_timer = 0.3

        if self.hp <= 0:
            # 喪失一次完整的生命力
            self.lives -= 1
            if self.lives > 0:
                # 重新獲得滿額血量與重生無敵
                self.hp = MAX_HP
                self.x = SCREEN_WIDTH // 2
                self.y = SCREEN_HEIGHT - 120
                self.invulnerable_timer = RESPAWN_INVULNERABLE_TIME
                self.power_level = max(1, self.power_level - 1)  # 死亡輕微掉落一級火力
                self.formation_units = 1  # 死亡重生後重新組裝組合體
            else:
                self.alive = False
                self.game_over = True
            return True  # 發生了爆炸重創
        return "damaged"

    def apply_powerup(self, p_type):
        """
        接收到戰果寶物後升級戰力與防護罩，並變身為 2~3 個組合體
        """
        snd = SoundManager.get_instance()
        snd.play("powerup")

        if p_type == "P":
            # 增加子彈射擊戰力 (最多 5 級)
            self.power_level = min(self.max_power_level, self.power_level + 1)
            # 吃到寶物後進化為 2~3 個組合體進行協同攻擊
            self.formation_units = min(3, max(2, self.formation_units + 1))
        elif p_type == "S":
            # 修復生命力並強化防護罩
            self.hp = min(self.max_hp, self.hp + 20)
            self.shield_capacity = min(150.0, self.shield_capacity + 50.0)
            self.invulnerable_timer = max(self.invulnerable_timer, 2.0)
        elif p_type == "B":
            # 戰術炸彈 / 爆破能量全滿
            self.invulnerable_timer = max(self.invulnerable_timer, 1.5)
        elif p_type in ["W", "F"]:
            # 增幅威力與變身為 2~3 個組合體
            self.power_level = min(self.max_power_level, self.power_level + 1)
            self.formation_units = min(3, max(2, self.formation_units + 1))
        elif p_type == "L":
            # 吃到自動追蹤雷射戰果 (Auto-Targeting Homing Laser)
            self.has_laser = True
            self.power_level = min(self.max_power_level, self.power_level + 1)
            self.formation_units = min(3, max(2, self.formation_units + 1))
            snd.play("laser_powerup")

    def handle_input(self, keys, dt):
        """使用上下左右按鍵控制戰機飛行 (同時相容 WASD)"""
        if not self.alive:
            return

        dx = 0
        dy = 0

        def is_down(k):
            try:
                return bool(keys[k])
            except (KeyError, IndexError, TypeError):
                return False

        # 方向控制
        if is_down(pygame.K_LEFT) or is_down(pygame.K_a):
            dx -= 1
        if is_down(pygame.K_RIGHT) or is_down(pygame.K_d):
            dx += 1
        if is_down(pygame.K_UP) or is_down(pygame.K_w):
            dy -= 1
        if is_down(pygame.K_DOWN) or is_down(pygame.K_s):
            dy += 1

        # 更新機身傾斜狀態 (Bank State)
        if dx < 0:
            self.bank_state = "left"
        elif dx > 0:
            self.bank_state = "right"
        else:
            self.bank_state = "center"

        # 斜向移動速度歸一化
        if dx != 0 and dy != 0:
            dx *= 0.7071
            dy *= 0.7071

        spd = self.speed * (1.2 if self.is_performing_special and self.special_type == "roll" else 1.0)
        self.x += dx * spd * dt * 60
        self.y += dy * spd * dt * 60

        # 邊界限制 (考慮組合體翼展與上下獨立 HUD 切割防遮擋空域)
        margin_x = 48 if self.formation_units >= 2 else 32
        self.x = max(margin_x, min(SCREEN_WIDTH - margin_x, self.x))
        min_y = HUD_TOP_HEIGHT + 26
        max_y = SCREEN_HEIGHT - HUD_BOTTOM_HEIGHT - 26
        self.y = max(min_y, min(max_y, self.y))
        self.rect.center = (int(self.x), int(self.y))

    def shoot(self, target_enemy=None):
        """
        空白鍵發射武器子彈 (依戰果等級增加射擊戰力)
        當擁有 2~3 個組合體時，僚機同時同步發射密集前向能量彈幕！
        """
        if not self.alive:
            return []
        if self.fire_timer > 0:
            return []

        # 射擊間隔依等級加速
        rate = max(0.06, self.base_fire_rate - (self.power_level - 1) * 0.015)
        self.fire_timer = rate

        bullets = []
        lvl = self.power_level
        dmg = 20 + lvl * 5

        snd = SoundManager.get_instance()

        # 1. 主戰機火力發射 (若吃到雷射戰果 L，則發射自動追蹤高能雷射)
        if self.has_laser:
            snd.play("laser_shoot")
            bullets.append(HomingLaser(self.x - 12, self.y - 20, -2.5, -16, dmg + 12, target=target_enemy))
            bullets.append(HomingLaser(self.x + 12, self.y - 20, 2.5, -16, dmg + 12, target=target_enemy))
            if lvl >= 2:
                bullets.append(HomingLaser(self.x, self.y - 25, 0, -18, dmg + 15, target=target_enemy))
            if lvl >= 4:
                bullets.append(HomingLaser(self.x - 24, self.y - 12, -4.5, -15, dmg + 10, target=target_enemy))
                bullets.append(HomingLaser(self.x + 24, self.y - 12, 4.5, -15, dmg + 10, target=target_enemy))

        elif self.weapon_type == "vulcan":
            snd.play("player_shoot")
            # P-38 閃電號：前向密集高速機砲
            if lvl == 1:
                bullets.append(Bullet(self.x - 8, self.y - 18, 0, -14, "player_vulcan", dmg))
                bullets.append(Bullet(self.x + 8, self.y - 18, 0, -14, "player_vulcan", dmg))
            elif lvl == 2:
                bullets.append(Bullet(self.x - 12, self.y - 18, 0, -15, "player_vulcan", dmg))
                bullets.append(Bullet(self.x, self.y - 24, 0, -16, "player_vulcan", dmg + 5))
                bullets.append(Bullet(self.x + 12, self.y - 18, 0, -15, "player_vulcan", dmg))
            elif lvl >= 3:
                bullets.append(Bullet(self.x - 16, self.y - 16, -1.5, -15, "player_vulcan", dmg))
                bullets.append(Bullet(self.x - 6, self.y - 22, 0, -16, "player_vulcan", dmg))
                bullets.append(Bullet(self.x + 6, self.y - 22, 0, -16, "player_vulcan", dmg))
                bullets.append(Bullet(self.x + 16, self.y - 16, 1.5, -15, "player_vulcan", dmg))
            if lvl >= 4:
                bullets.append(Bullet(self.x - 24, self.y - 10, -3.5, -13, "player_vulcan", dmg - 5))
                bullets.append(Bullet(self.x + 24, self.y - 10, 3.5, -13, "player_vulcan", dmg - 5))
            if lvl >= 5:
                bullets.append(HomingMissile(self.x - 20, self.y, -3, -6, dmg + 10, target_enemy))
                bullets.append(HomingMissile(self.x + 20, self.y, 3, -6, dmg + 10, target_enemy))

        elif self.weapon_type == "spread":
            snd.play("player_shoot")
            # F4U 海盜號：扇形廣角強大擴散彈
            base_count = 3 if lvl == 1 else (5 if lvl <= 3 else 7)
            spread_angle = 12 if lvl <= 2 else 16
            for i in range(base_count):
                angle = (i - (base_count - 1) / 2) * spread_angle
                rad = math.radians(-90 + angle)
                vx = math.cos(rad) * 13.0
                vy = math.sin(rad) * 13.0
                bullets.append(Bullet(self.x, self.y - 16, vx, vy, "player_spread", dmg))

        elif self.weapon_type == "missile":
            snd.play("player_shoot")
            # BF-109 獵鷹號：前向機砲加自動追蹤火箭
            bullets.append(Bullet(self.x - 10, self.y - 18, 0, -14, "player_vulcan", dmg))
            bullets.append(Bullet(self.x + 10, self.y - 18, 0, -14, "player_vulcan", dmg))
            if lvl >= 2:
                bullets.append(HomingMissile(self.x - 18, self.y, -4, -4, dmg + 5, target_enemy))
                bullets.append(HomingMissile(self.x + 18, self.y, 4, -4, dmg + 5, target_enemy))
            if lvl >= 4:
                bullets.append(Bullet(self.x - 5, self.y - 24, 0, -16, "player_vulcan", dmg + 8))
                bullets.append(Bullet(self.x + 5, self.y - 24, 0, -16, "player_vulcan", dmg + 8))

        else:
            snd.play("laser_shoot")
            # 零式改 幻影號：高能自動追蹤雷射
            bullets.append(HomingLaser(self.x - 10, self.y - 22, -2, -18, dmg + 12, target=target_enemy))
            bullets.append(HomingLaser(self.x + 10, self.y - 22, 2, -18, dmg + 12, target=target_enemy))
            if lvl >= 2:
                bullets.append(HomingLaser(self.x, self.y - 28, 0, -20, dmg + 16, target=target_enemy))
            if lvl >= 3:
                bullets.append(Bullet(self.x - 22, self.y - 14, -2.5, -16, "player_vulcan", dmg))
                bullets.append(Bullet(self.x + 22, self.y - 14, 2.5, -16, "player_vulcan", dmg))
            if lvl >= 5:
                bullets.append(HomingLaser(self.x - 30, self.y - 10, -5.0, -15, dmg + 10, target=target_enemy))
                bullets.append(HomingLaser(self.x + 30, self.y - 10, 5.0, -15, dmg + 10, target=target_enemy))

        # 2. 組合體 (2~3 機) 僚機同步進行密集火力攻擊！
        wingman_dmg = 15 + lvl * 3
        if self.formation_units >= 2:
            # 右翼伴隨機開火
            rx = self.x + 38
            ry = self.y + 12
            if self.has_laser:
                bullets.append(HomingLaser(rx, ry - 14, 1.5, -16, wingman_dmg + 5, target=target_enemy))
            else:
                bullets.append(Bullet(rx - 5, ry - 12, 0, -15, "player_wingman_bullet", wingman_dmg))
                bullets.append(Bullet(rx + 5, ry - 12, 0, -15, "player_wingman_bullet", wingman_dmg))

        if self.formation_units >= 3:
            # 左翼伴隨機開火
            lx = self.x - 38
            ly = self.y + 12
            if self.has_laser:
                bullets.append(HomingLaser(lx, ly - 14, -1.5, -16, wingman_dmg + 5, target=target_enemy))
            else:
                bullets.append(Bullet(lx - 5, ly - 12, 0, -15, "player_wingman_bullet", wingman_dmg))
                bullets.append(Bullet(lx + 5, ly - 12, 0, -15, "player_wingman_bullet", wingman_dmg))

        return bullets

    def update(self, dt):
        self.frame += 1
        self.fire_timer = max(0.0, self.fire_timer - dt)
        self.invulnerable_timer = max(0.0, self.invulnerable_timer - dt)
        self.special_timer = max(0.0, self.special_timer - dt)
        self.shield_pulse += dt * 5.0

        # 特殊技能狀態更新
        if self.is_performing_special:
            self.special_active_timer -= dt
            if self.special_type == "roll":
                # 360 度急速迴轉動畫
                prog = 1.0 - (self.special_active_timer / self.special_duration)
                self.roll_angle = prog * 360.0

            if self.special_active_timer <= 0:
                self.is_performing_special = False
                self.shield_active = False
                self.roll_angle = 0.0

        # 邊界保護 (戰機活動空域獨立於上下 HUD 切割列，絕不遮擋)
        min_y = HUD_TOP_HEIGHT + 26
        max_y = SCREEN_HEIGHT - HUD_BOTTOM_HEIGHT - 26
        self.y = max(min_y, min(max_y, self.y))
        self.rect.center = (int(self.x), int(self.y))

    def draw(self, surf, particle_mgr=None):
        if not self.alive:
            return

        # 重生或無敵閃爍效果
        if self.invulnerable_timer > 0 and int(self.invulnerable_timer * 15) % 2 == 1:
            return

        # 主機引擎噴氣粒子
        if particle_mgr and self.frame % 2 == 0:
            boost = self.is_performing_special
            particle_mgr.add_engine_exhaust(self.x - 14, self.y + 22, boost=boost)
            particle_mgr.add_engine_exhaust(self.x + 14, self.y + 22, boost=boost)

        # 獲取主機精靈圖
        spr = create_player_sprite(self.fighter_id, self.bank_state, self.frame // 2)

        # 1. 繪製伴隨僚機 (形成 2~3 個戰機組合體)
        wing_sway = math.sin(self.frame * 0.1) * 2.0
        wingman_positions = []
        if self.formation_units == 2:
            # 2 機組合體：主機 + 右翼僚機
            wingman_positions.append((self.x + 38, self.y + 12 + wing_sway))
        elif self.formation_units >= 3:
            # 3 機黃金三角組合體：主機 + 左翼僚機 + 右翼僚機
            wingman_positions.append((self.x - 38, self.y + 12 + wing_sway))
            wingman_positions.append((self.x + 38, self.y + 12 - wing_sway))

        wing_spr = create_wingman_sprite(self.fighter_id, self.bank_state, self.frame // 2)

        for wx, wy in wingman_positions:
            if particle_mgr and self.frame % 3 == 0:
                particle_mgr.add_engine_exhaust(wx, wy + 16, boost=self.is_performing_special)

            if self.is_performing_special and self.special_type == "roll":
                scale_y = abs(math.cos(math.radians(self.roll_angle)))
                ww, wh = wing_spr.get_size()
                scaled_wh = max(4, int(wh * scale_y))
                anim_wspr = pygame.transform.scale(wing_spr, (ww, scaled_wh))
                wrect = anim_wspr.get_rect(center=(int(wx), int(wy)))
                surf.blit(anim_wspr, wrect)
            else:
                wrect = wing_spr.get_rect(center=(int(wx), int(wy)))
                surf.blit(wing_spr, wrect)

        # 2. 繪製主戰機本體
        if self.is_performing_special and self.special_type == "roll":
            scale_y = abs(math.cos(math.radians(self.roll_angle)))
            w, h = spr.get_size()
            scaled_h = max(4, int(h * scale_y))
            anim_spr = pygame.transform.scale(spr, (w, scaled_h))
            rect = anim_spr.get_rect(center=(int(self.x), int(self.y)))
            surf.blit(anim_spr, rect)
            if particle_mgr:
                particle_mgr.add_afterimage(anim_spr, rect.x, rect.y, alpha=100, duration=0.15)
        else:
            surf.blit(spr, self.rect)

        # 3. 防護罩力場 (全防禦力場光球，若有組合體則展開涵蓋整個編隊)
        if self.shield_active or (self.invulnerable_timer > 0 and not self.is_performing_special):
            s_radius = (48 if self.formation_units >= 2 else 34) + int(2 * math.sin(self.shield_pulse))
            shield_surf = pygame.Surface((s_radius * 2 + 4, s_radius * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(shield_surf, (80, 200, 255, 60), (s_radius + 2, s_radius + 2), s_radius)
            pygame.draw.circle(shield_surf, (150, 240, 255, 140), (s_radius + 2, s_radius + 2), s_radius, 2)
            pygame.draw.circle(shield_surf, (255, 255, 255, 200), (s_radius + 2, s_radius + 2), s_radius - 4, 1)
            surf.blit(shield_surf, (int(self.x - s_radius - 2), int(self.y - s_radius - 2)))
