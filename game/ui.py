"""
1945: 二戰空間（II War Space）
使用者介面與戰機選擇系統 (HUD & Fighter Selection UI)
支援開場戰機選擇、5 次完整生命顯示、10 分之一血量條、技能冷卻、BOSS 警告與過關結算
"""

import math
import pygame
from game.config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_WHITE, COLOR_RED, COLOR_GREEN,
    COLOR_BLUE, COLOR_YELLOW, COLOR_CYAN, COLOR_GOLD, FIGHTER_TYPES,
    HUD_TOP_HEIGHT, HUD_BOTTOM_HEIGHT
)
from game.sprites import create_player_sprite

import os
import sys

_CACHED_FONT_PATH = None

def get_font(size):
    global _CACHED_FONT_PATH
    if _CACHED_FONT_PATH is None:
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        meipass = getattr(sys, "_MEIPASS", None)
        win_dir = os.environ.get("WINDIR", r"C:\Windows")
        win_fonts = os.path.join(win_dir, "Fonts")

        candidates = []
        if meipass:
            candidates.append(os.path.join(meipass, "assets", "fonts", "wqy-microhei.ttc"))
        candidates.extend([
            os.path.join(root_dir, "assets", "fonts", "wqy-microhei.ttc"),
            os.path.join(os.getcwd(), "assets", "fonts", "wqy-microhei.ttc"),
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            os.path.join(win_fonts, "msjhbd.ttc"),
            os.path.join(win_fonts, "msjh.ttc"),
            os.path.join(win_fonts, "msyhbd.ttc"),
            os.path.join(win_fonts, "msyh.ttc"),
            os.path.join(win_fonts, "mingliu.ttc"),
            os.path.join(win_fonts, "simhei.ttf"),
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ])
        for p in candidates:
            if p and os.path.exists(p):
                _CACHED_FONT_PATH = p
                break
        if _CACHED_FONT_PATH is None:
            _CACHED_FONT_PATH = "fallback"

    if _CACHED_FONT_PATH != "fallback":
        try:
            return pygame.font.Font(_CACHED_FONT_PATH, size)
        except Exception:
            pass
    return pygame.font.Font(None, size)

class UIManager:
    def __init__(self):
        self.font_tiny = get_font(18)
        self.font_small = get_font(24)
        self.font_mid = get_font(30)
        self.font_large = get_font(44)
        self.font_huge = get_font(56)

        self.warning_timer = 0.0
        self.clear_timer = 0.0

    def draw_hud(self, surf, player, score, high_score, current_stage_data, boss=None, midboss=None):
        """
        繪製單人戰場 HUD：
        【核心規則】：螢幕上下顯示資訊的功能處需獨立切割開來以免擋到！
        頂部 (0 ~ HUD_TOP_HEIGHT) 與底部 (SCREEN_HEIGHT - HUD_BOTTOM_HEIGHT ~ SCREEN_HEIGHT)
        均獨立切割為專屬控制儀表列，並以高科技霓虹分割線切開，戰機飛行空域受保護完全不被遮擋！
        """
        w = surf.get_width()
        # 1. 頂部獨立切割控制列 (高度 HUD_TOP_HEIGHT = 58)
        top_bar = pygame.Surface((w, HUD_TOP_HEIGHT))
        top_bar.fill((8, 14, 24))
        surf.blit(top_bar, (0, 0))
        # 螢幕上方獨立切割邊界線 (Neon Cyan Line)
        pygame.draw.line(surf, (0, 220, 255), (0, HUD_TOP_HEIGHT - 1), (w, HUD_TOP_HEIGHT - 1), 2)
        pygame.draw.line(surf, (0, 80, 120), (0, HUD_TOP_HEIGHT), (w, HUD_TOP_HEIGHT), 1)

        # 頂部戰術膠囊：
        # 左翼：SCORE 分數膠囊
        sc_pill = pygame.Surface((210, 36), pygame.SRCALPHA)
        sc_pill.fill((16, 26, 42, 200))
        pygame.draw.rect(sc_pill, (60, 140, 210), (0, 0, 210, 36), 1, border_radius=6)
        surf.blit(sc_pill, (16, 10))
        score_lbl = self.font_tiny.render("SCORE", True, (160, 190, 220))
        score_val = self.font_small.render(f"{score:08d}", True, COLOR_GOLD)
        surf.blit(score_lbl, (26, 13))
        surf.blit(score_val, (26, 24))

        # 中間：STAGE 關卡進度膠囊
        st_num = current_stage_data["stage"]
        st_pill = pygame.Surface((180, 36), pygame.SRCALPHA)
        st_pill.fill((16, 26, 42, 200))
        pygame.draw.rect(st_pill, (40, 220, 255), (0, 0, 180, 36), 1, border_radius=6)
        surf.blit(st_pill, (w // 2 - 90, 10))
        stage_txt = self.font_mid.render(f"STAGE {st_num:02d} / 20", True, COLOR_CYAN)
        st_rect = stage_txt.get_rect(center=(w // 2, 28))
        surf.blit(stage_txt, st_rect)

        # 右翼：HIGH 最高紀錄膠囊
        hi_pill = pygame.Surface((210, 36), pygame.SRCALPHA)
        hi_pill.fill((16, 26, 42, 200))
        pygame.draw.rect(hi_pill, (200, 170, 70), (0, 0, 210, 36), 1, border_radius=6)
        surf.blit(hi_pill, (w - 226, 10))
        hi_lbl = self.font_tiny.render("HIGH", True, (160, 190, 220))
        hi_val = self.font_small.render(f"{max(score, high_score):08d}", True, COLOR_WHITE)
        surf.blit(hi_lbl, (w - 216, 13))
        surf.blit(hi_val, (w - 216, 24))

        # 2. 底部獨立切割控制列 (高度 HUD_BOTTOM_HEIGHT = 58)
        bot_y = SCREEN_HEIGHT - HUD_BOTTOM_HEIGHT
        bot_bar = pygame.Surface((w, HUD_BOTTOM_HEIGHT))
        bot_bar.fill((8, 14, 24))
        surf.blit(bot_bar, (0, bot_y))
        # 螢幕下方獨立切割邊界線 (Neon Cyan Line)
        pygame.draw.line(surf, (0, 220, 255), (0, bot_y), (w, bot_y), 2)
        pygame.draw.line(surf, (0, 80, 120), (0, bot_y - 1), (w, bot_y - 1), 1)

        by = bot_y + 10

        # 左側狀態膠囊 (生命力 5 次 + 10 格十分之一生命力條)
        left_pill = pygame.Surface((380, 38), pygame.SRCALPHA)
        left_pill.fill((16, 26, 42, 200))
        pygame.draw.rect(left_pill, (60, 140, 210), (0, 0, 380, 38), 1, border_radius=6)
        surf.blit(left_pill, (16, by))

        # 【核心規則】：五次完整生命力 (5條命)
        lives_lbl = self.font_tiny.render("LIVES", True, (200, 220, 240))
        surf.blit(lives_lbl, (24, by + 12))

        mini_spr = create_player_sprite(player.fighter_id, "center", 0)
        mini_spr = pygame.transform.scale(mini_spr, (20, 20))
        for i in range(5):
            lx = 68 + i * 22
            if i < player.lives:
                surf.blit(mini_spr, (lx, by + 9))
            else:
                pygame.draw.circle(surf, (60, 65, 75), (lx + 10, by + 19), 5)

        # 【核心規則】：十分之一生命力條 (10格，每中一彈扣十分之一)
        hp_lbl = self.font_tiny.render("HP", True, (200, 220, 240))
        surf.blit(hp_lbl, (190, by + 12))

        bar_x = 215
        bar_w = 13
        bar_h = 14
        gap = 3
        current_segments = int(math.ceil(player.hp / 10.0))

        for seg in range(10):
            sx = bar_x + seg * (bar_w + gap)
            pygame.draw.rect(surf, (40, 50, 60), (sx, by + 11, bar_w, bar_h), border_radius=2)
            if seg < current_segments:
                if current_segments > 6:
                    c = COLOR_GREEN
                elif current_segments > 3:
                    c = COLOR_YELLOW
                else:
                    c = COLOR_RED
                pygame.draw.rect(surf, c, (sx + 1, by + 12, bar_w - 2, bar_h - 2), border_radius=2)

        # 中央輔助狀態 (組合體編隊指示與自動追蹤雷射)
        mid_info = []
        if player.formation_units >= 2:
            mid_info.append(f"{player.formation_units}機組合體")
        if getattr(player, 'has_laser', False):
            mid_info.append("追蹤雷射")
        if mid_info:
            info_txt = " · ".join(mid_info)
            info_surf = self.font_small.render(info_txt, True, COLOR_CYAN)
            i_rect = info_surf.get_rect(center=(w // 2, by + 19))
            surf.blit(info_surf, i_rect)

        # 右側控制膠囊 (火力等級 PWR + 按鍵 Z 特技槽)
        right_pill = pygame.Surface((380, 38), pygame.SRCALPHA)
        right_pill.fill((16, 26, 42, 200))
        pygame.draw.rect(right_pill, (60, 140, 210), (0, 0, 380, 38), 1, border_radius=6)
        surf.blit(right_pill, (w - 396, by))

        rx = w - 386
        pwr_txt = self.font_small.render(f"PWR: LV.{player.power_level}", True, COLOR_GOLD)
        surf.blit(pwr_txt, (rx, by + 9))

        cd_ratio = 1.0 - (player.special_timer / player.special_cooldown)
        cd_ratio = max(0.0, min(1.0, cd_ratio))
        z_col = COLOR_CYAN if cd_ratio >= 1.0 else (120, 140, 160)

        spec_lbl = self.font_tiny.render(f"[Z] {player.config['special_name']}", True, z_col)
        surf.blit(spec_lbl, (rx + 115, by + 3))

        pygame.draw.rect(surf, (40, 50, 60), (rx + 115, by + 19, 130, 8), border_radius=2)
        if cd_ratio > 0:
            pygame.draw.rect(surf, z_col, (rx + 115, by + 19, int(130 * cd_ratio), 8), border_radius=2)

        # 3. 中型大魔王血量條 (當 MidBoss 出現時，於頂部切割列下方清晰呈現)
        if midboss and midboss.alive and not midboss.is_entering and not (boss and boss.alive and not boss.is_entering):
            mb_w = 420
            mb_x = (w - mb_w) // 2
            mb_y = HUD_TOP_HEIGHT + 10
            mb_ratio = max(0.0, midboss.hp / float(midboss.max_hp))

            # 底板
            mb_panel = pygame.Surface((mb_w, 32), pygame.SRCALPHA)
            mb_panel.fill((15, 25, 40, 220))
            pygame.draw.rect(mb_panel, (255, 170, 30), (0, 0, mb_w, 32), 2, border_radius=4)
            surf.blit(mb_panel, (mb_x, mb_y))

            mb_title = self.font_tiny.render(f"⚠️ MID-BOSS: {midboss.name}", True, (255, 210, 50))
            surf.blit(mb_title, (mb_x + 10, mb_y + 2))

            # 血條
            pygame.draw.rect(surf, (40, 30, 20), (mb_x + 10, mb_y + 18, mb_w - 20, 10), border_radius=2)
            pygame.draw.rect(surf, (255, 150, 20), (mb_x + 10, mb_y + 18, int((mb_w - 20) * mb_ratio), 10), border_radius=2)

        # 4. 終極 BOSS 血量條與持久戰 HUD (當 BOSS 出現時)
        if boss and boss.alive and not boss.is_entering:
            bw = 480
            bx = (w - bw) // 2 + 30
            by_boss = HUD_TOP_HEIGHT + 14
            b_ratio = max(0.0, boss.hp / boss.max_hp)
            phase_num = getattr(boss, 'current_phase', 1)

            # A. 穩定顯示敵艦外型戰術卡 (Stable Enemy Warship Tactical Display Frame)
            frame_w, frame_h = 76, 76
            frame_x = bx - 86
            frame_y = by_boss - 18
            frame_surf = pygame.Surface((frame_w, frame_h), pygame.SRCALPHA)
            frame_surf.fill((10, 20, 35, 220))
            pygame.draw.rect(frame_surf, (40, 210, 255), (0, 0, frame_w, frame_h), 2, border_radius=4)
            pygame.draw.line(frame_surf, (40, 210, 255, 120), (0, frame_h // 2), (frame_w, frame_h // 2), 1)
            pygame.draw.line(frame_surf, (40, 210, 255, 120), (frame_w // 2, 0), (frame_w // 2, frame_h), 1)
            surf.blit(frame_surf, (frame_x, frame_y))

            from game.sprites import create_boss_sprite
            boss_spr = create_boss_sprite(boss.boss_type, boss.stage, 0)
            orig_bw, orig_bh = boss_spr.get_size()
            scale = min((frame_w - 14) / float(orig_bw), (frame_h - 14) / float(orig_bh))
            scaled_bw = max(10, int(orig_bw * scale))
            scaled_bh = max(10, int(orig_bh * scale))
            target_spr = pygame.transform.smoothscale(boss_spr, (scaled_bw, scaled_bh))
            t_rect = target_spr.get_rect(center=(frame_x + frame_w // 2, frame_y + frame_h // 2))
            surf.blit(target_spr, t_rect)

            target_lbl = self.font_tiny.render("TARGET", True, (60, 240, 255))
            surf.blit(target_lbl, (frame_x + 5, frame_y + 2))

            # B. BOSS 名稱與階段
            phase_names = {
                1: "階段一：重裝巡弋",
                2: "階段二：全舷對空",
                3: "階段三：滅世狂暴"
            }
            phase_str = phase_names.get(phase_num, "階段一")
            b_name = self.font_small.render(f"BOSS: {boss.name} [{phase_str}]", True, (255, 120, 120))
            surf.blit(b_name, (bx, by_boss - 18))

            # C. 需多久會被擊斃的資訊 (以顯色醒目顯示：階1金黃、階2亮橘、階3霓虹赤紅)
            est_total_secs = max(3, int(boss.hp / 135.0))
            est_m = est_total_secs // 60
            est_s = est_total_secs % 60
            time_to_kill_str = f"{est_m:02d}分{est_s:02d}秒 ({est_total_secs}s)"

            if phase_num == 3:
                highlight_col = (255, 50, 70)     # 顯色：狂暴霓虹赤紅
                badge_bg = (160, 20, 30, 210)
            elif phase_num == 2:
                highlight_col = (255, 165, 20)    # 顯色：鮮豔螢光橘
                badge_bg = (160, 90, 15, 200)
            else:
                highlight_col = (255, 240, 40)    # 顯色：璀璨明亮金黃
                badge_bg = (20, 80, 140, 200)

            # 顯色資訊標籤底板
            info_w = 230
            info_h = 22
            info_x = bx + bw - info_w
            info_y = by_boss - 18
            badge_surf = pygame.Surface((info_w, info_h), pygame.SRCALPHA)
            badge_surf.fill(badge_bg)
            pygame.draw.rect(badge_surf, highlight_col, (0, 0, info_w, info_h), 2, border_radius=3)
            surf.blit(badge_surf, (info_x, info_y))

            est_info_txt = self.font_tiny.render(f"⏱ 預估擊斃: {time_to_kill_str}", True, highlight_col)
            surf.blit(est_info_txt, (info_x + 6, info_y + 2))

            # D. 雙層血條底板與高能血槽
            pygame.draw.rect(surf, (15, 15, 25), (bx - 2, by_boss - 2, bw + 4, 16), border_radius=4)
            pygame.draw.rect(surf, (50, 20, 20), (bx, by_boss, bw, 12), border_radius=3)
            pygame.draw.rect(surf, highlight_col, (bx, by_boss, int(bw * b_ratio), 12), border_radius=3)

            # 階段分段指示標記 (33% 與 66%)
            p1_mark = bx + int(bw * 0.33)
            p2_mark = bx + int(bw * 0.66)
            pygame.draw.line(surf, (255, 255, 255, 180), (p1_mark, by_boss), (p1_mark, by_boss + 12), 2)
            pygame.draw.line(surf, (255, 255, 255, 180), (p2_mark, by_boss), (p2_mark, by_boss + 12), 2)

    def draw_hud_2p(self, surf, p1, p2, score, high_score, current_stage_data, bosses=None, midboss=None):
        """
        繪製 2 人同時執行專屬 HUD (1024 寬度)：
        - 頂部：P1 分數、關卡進度 STAGE XX/20、P2/HIGH 分數
        - 底部：左側 P1 5命與HP條，右側 P2 5命與HP條
        - 中央：若其中一人陣亡，顯示醒目的 [按 Y 鍵補滿 5 命復活] 提示
        - BOSS：支援最後雙大魔王 (Boss 1 與 Boss 2) 同時呈現雙血條與戰術預估
        """
        w = surf.get_width()

        # 1. 頂部獨立切割控制列 (高度 HUD_TOP_HEIGHT = 58)
        top_bar = pygame.Surface((w, HUD_TOP_HEIGHT))
        top_bar.fill((8, 14, 24))
        surf.blit(top_bar, (0, 0))
        pygame.draw.line(surf, (0, 220, 255), (0, HUD_TOP_HEIGHT - 1), (w, HUD_TOP_HEIGHT - 1), 2)
        pygame.draw.line(surf, (0, 80, 120), (0, HUD_TOP_HEIGHT), (w, HUD_TOP_HEIGHT), 1)

        # 頂部戰術膠囊：
        # 左翼：1P SCORE
        sc_pill = pygame.Surface((220, 36), pygame.SRCALPHA)
        sc_pill.fill((16, 26, 42, 200))
        pygame.draw.rect(sc_pill, (60, 140, 210), (0, 0, 220, 36), 1, border_radius=6)
        surf.blit(sc_pill, (16, 10))
        p1_name = p1.name if p1 else "1P"
        score_lbl = self.font_tiny.render(f"1P · {p1_name}", True, (160, 190, 220))
        score_val = self.font_small.render(f"{score:08d}", True, COLOR_GOLD)
        surf.blit(score_lbl, (24, 13))
        surf.blit(score_val, (24, 24))

        # 中間：STAGE 關卡進度膠囊
        st_num = current_stage_data["stage"]
        st_pill = pygame.Surface((200, 36), pygame.SRCALPHA)
        st_pill.fill((16, 26, 42, 200))
        pygame.draw.rect(st_pill, (40, 220, 255), (0, 0, 200, 36), 1, border_radius=6)
        surf.blit(st_pill, (w // 2 - 100, 10))
        stage_txt = self.font_mid.render(f"STAGE {st_num:02d} / 20", True, COLOR_CYAN)
        st_rect = stage_txt.get_rect(center=(w // 2, 28))
        surf.blit(stage_txt, st_rect)

        # 右翼：2P / HIGH 膠囊
        hi_pill = pygame.Surface((220, 36), pygame.SRCALPHA)
        hi_pill.fill((16, 26, 42, 200))
        pygame.draw.rect(hi_pill, (200, 170, 70), (0, 0, 220, 36), 1, border_radius=6)
        surf.blit(hi_pill, (w - 236, 10))
        p2_name = p2.name if p2 else "2P"
        hi_lbl = self.font_tiny.render(f"2P · {p2_name} | HIGH", True, (160, 190, 220))
        hi_val = self.font_small.render(f"{max(score, high_score):08d}", True, COLOR_WHITE)
        surf.blit(hi_lbl, (w - 226, 13))
        surf.blit(hi_val, (w - 226, 24))

        # 2. 底部獨立切割控制列 (高度 HUD_BOTTOM_HEIGHT = 58)
        bot_y = SCREEN_HEIGHT - HUD_BOTTOM_HEIGHT
        bot_bar = pygame.Surface((w, HUD_BOTTOM_HEIGHT))
        bot_bar.fill((8, 14, 24))
        surf.blit(bot_bar, (0, bot_y))
        pygame.draw.line(surf, (0, 220, 255), (0, bot_y), (w, bot_y), 2)
        pygame.draw.line(surf, (0, 80, 120), (0, bot_y - 1), (w, bot_y - 1), 1)

        by = bot_y + 10

        # 左側：P1 狀態膠囊 (生命力 5 次 + 10 格十分之一生命力條)
        p1_pill = pygame.Surface((340, 38), pygame.SRCALPHA)
        p1_pill.fill((16, 26, 42, 200))
        pygame.draw.rect(p1_pill, (60, 140, 210), (0, 0, 340, 38), 1, border_radius=6)
        surf.blit(p1_pill, (16, by))

        p1_lbl = self.font_tiny.render("1P LIVES", True, (200, 220, 240))
        surf.blit(p1_lbl, (24, by + 12))

        if p1:
            mini_p1 = create_player_sprite(p1.fighter_id, "center", 0)
            mini_p1 = pygame.transform.scale(mini_p1, (18, 18))
            for i in range(5):
                lx = 76 + i * 18
                if i < p1.lives:
                    surf.blit(mini_p1, (lx, by + 10))
                else:
                    pygame.draw.circle(surf, (60, 65, 75), (lx + 9, by + 19), 4)

            p1_hp_lbl = self.font_tiny.render("HP", True, (200, 220, 240))
            surf.blit(p1_hp_lbl, (175, by + 12))

            bar_x = 198
            bar_w = 11
            bar_h = 13
            gap = 2
            current_segments = int(math.ceil(p1.hp / 10.0))
            for seg in range(10):
                sx = bar_x + seg * (bar_w + gap)
                pygame.draw.rect(surf, (40, 50, 60), (sx, by + 12, bar_w, bar_h), border_radius=2)
                if seg < current_segments:
                    c = COLOR_GREEN if current_segments > 6 else (COLOR_YELLOW if current_segments > 3 else COLOR_RED)
                    pygame.draw.rect(surf, c, (sx + 1, by + 13, bar_w - 2, bar_h - 2), border_radius=2)

        # 右側：P2 狀態膠囊 (生命力 5 次 + 10 格十分之一生命力條)
        p2_pill = pygame.Surface((340, 38), pygame.SRCALPHA)
        p2_pill.fill((16, 26, 42, 200))
        pygame.draw.rect(p2_pill, (210, 100, 200), (0, 0, 340, 38), 1, border_radius=6)
        surf.blit(p2_pill, (w - 356, by))

        p2_lbl = self.font_tiny.render("2P LIVES", True, (240, 200, 240))
        surf.blit(p2_lbl, (w - 348, by + 12))

        if p2:
            mini_p2 = create_player_sprite(p2.fighter_id, "center", 0)
            mini_p2 = pygame.transform.scale(mini_p2, (18, 18))
            for i in range(5):
                lx = w - 296 + i * 18
                if i < p2.lives:
                    surf.blit(mini_p2, (lx, by + 10))
                else:
                    pygame.draw.circle(surf, (60, 65, 75), (lx + 9, by + 19), 4)

            p2_hp_lbl = self.font_tiny.render("HP", True, (240, 200, 240))
            surf.blit(p2_hp_lbl, (w - 198, by + 12))

            bar_x = w - 176
            bar_w = 11
            bar_h = 13
            gap = 2
            p2_segments = int(math.ceil(p2.hp / 10.0))
            for seg in range(10):
                sx = bar_x + seg * (bar_w + gap)
                pygame.draw.rect(surf, (40, 50, 60), (sx, by + 12, bar_w, bar_h), border_radius=2)
                if seg < p2_segments:
                    c = COLOR_GREEN if p2_segments > 6 else (COLOR_YELLOW if p2_segments > 3 else COLOR_RED)
                    pygame.draw.rect(surf, c, (sx + 1, by + 13, bar_w - 2, bar_h - 2), border_radius=2)

        # 中央區域：【核心規則】陣亡時按 Y 鍵補滿 5 命提示
        need_revive_p1 = (p1 is not None and not p1.alive)
        need_revive_p2 = (p2 is not None and not p2.alive)

        if need_revive_p1 or need_revive_p2:
            rev_txt_str = "⚠️ 按 [Y] 鍵補滿 5 命復活！ ⚠️"
            if need_revive_p1 and need_revive_p2:
                rev_sub = "【P1 & P2 均陣亡】按 Y 鍵全員滿血復活"
            elif need_revive_p1:
                rev_sub = "【P1 陣亡】按 Y 鍵補滿 5 命復活"
            else:
                rev_sub = "【P2 陣亡】按 Y 鍵補滿 5 命復活"

            rev_pill = pygame.Surface((310, 42), pygame.SRCALPHA)
            rev_pill.fill((200, 20, 40, 230))
            pygame.draw.rect(rev_pill, (255, 240, 40), (0, 0, 310, 42), 2, border_radius=6)
            surf.blit(rev_pill, (w // 2 - 155, by - 2))

            t1 = self.font_tiny.render(rev_txt_str, True, COLOR_YELLOW)
            t2 = self.font_tiny.render(rev_sub, True, COLOR_WHITE)
            surf.blit(t1, t1.get_rect(center=(w // 2, by + 8)))
            surf.blit(t2, t2.get_rect(center=(w // 2, by + 25)))
        else:
            # 正常狀態顯示操作控制提示
            ctrl_txt = self.font_tiny.render("P1: 方向鍵/M射擊  ·  P2: WXAD/V射擊", True, (150, 210, 255))
            surf.blit(ctrl_txt, ctrl_txt.get_rect(center=(w // 2, by + 19)))

        # 3. 中型大魔王血量條 (當 MidBoss 出現時)
        if midboss and midboss.alive and not midboss.is_entering:
            active_bosses = [b for b in (bosses or []) if b and b.alive and not b.is_entering]
            if not active_bosses:
                mb_w = 460
                mb_x = (w - mb_w) // 2
                mb_y = HUD_TOP_HEIGHT + 10
                mb_ratio = max(0.0, midboss.hp / float(midboss.max_hp))

                mb_panel = pygame.Surface((mb_w, 32), pygame.SRCALPHA)
                mb_panel.fill((15, 25, 40, 220))
                pygame.draw.rect(mb_panel, (255, 170, 30), (0, 0, mb_w, 32), 2, border_radius=4)
                surf.blit(mb_panel, (mb_x, mb_y))

                mb_title = self.font_tiny.render(f"⚠️ MID-BOSS: {midboss.name}", True, (255, 210, 50))
                surf.blit(mb_title, (mb_x + 10, mb_y + 2))

                pygame.draw.rect(surf, (40, 30, 20), (mb_x + 10, mb_y + 18, mb_w - 20, 10), border_radius=2)
                pygame.draw.rect(surf, (255, 150, 20), (mb_x + 10, mb_y + 18, int((mb_w - 20) * mb_ratio), 10), border_radius=2)

        # 4. 【核心規則】：最後的大魔王需有兩隻 (雙魔王同時存在血量條 HUD)
        boss_list = bosses if isinstance(bosses, list) else ([bosses] if bosses else [])
        alive_bosses = [b for b in boss_list if b and b.alive and not b.is_entering]

        if len(alive_bosses) == 2:
            # 雙 BOSS 左右對稱展示
            for b_idx, b_obj in enumerate(alive_bosses):
                bw = 420
                bx = 16 if b_idx == 0 else (w - bw - 16)
                by_boss = HUD_TOP_HEIGHT + 14
                b_ratio = max(0.0, b_obj.hp / float(b_obj.max_hp))
                phase_num = getattr(b_obj, 'current_phase', 1)

                # 縮圖外框
                frame_w, frame_h = 60, 60
                frame_x = bx
                frame_y = by_boss - 10
                frame_surf = pygame.Surface((frame_w, frame_h), pygame.SRCALPHA)
                frame_surf.fill((10, 20, 35, 220))
                col_box = (40, 210, 255) if b_idx == 0 else (255, 120, 180)
                pygame.draw.rect(frame_surf, col_box, (0, 0, frame_w, frame_h), 2, border_radius=4)
                surf.blit(frame_surf, (frame_x, frame_y))

                from game.sprites import create_boss_sprite
                boss_spr = create_boss_sprite(b_obj.boss_type, b_obj.stage, 0)
                orig_bw, orig_bh = boss_spr.get_size()
                scale = min((frame_w - 10) / float(orig_bw), (frame_h - 10) / float(orig_bh))
                scaled_bw = max(10, int(orig_bw * scale))
                scaled_bh = max(10, int(orig_bh * scale))
                target_spr = pygame.transform.smoothscale(boss_spr, (scaled_bw, scaled_bh))
                surf.blit(target_spr, target_spr.get_rect(center=(frame_x + frame_w // 2, frame_y + frame_h // 2)))

                # 名稱與預估擊斃
                bar_x = frame_x + frame_w + 10
                bar_w = bw - frame_w - 10
                b_name = self.font_tiny.render(f"{b_obj.name} [階{phase_num}]", True, (255, 180, 180))
                surf.blit(b_name, (bar_x, by_boss - 10))

                est_total_secs = max(3, int(b_obj.hp / 135.0))
                est_txt = self.font_tiny.render(f"⏱ 預估: {est_total_secs}s", True, COLOR_YELLOW)
                surf.blit(est_txt, (bar_x + bar_w - 75, by_boss - 10))

                # 血條
                pygame.draw.rect(surf, (15, 15, 25), (bar_x - 2, by_boss + 12, bar_w + 4, 16), border_radius=3)
                pygame.draw.rect(surf, (50, 20, 20), (bar_x, by_boss + 14, bar_w, 12), border_radius=2)
                hp_col = (255, 50, 70) if phase_num == 3 else ((255, 165, 20) if phase_num == 2 else (255, 240, 40))
                pygame.draw.rect(surf, hp_col, (bar_x, by_boss + 14, int(bar_w * b_ratio), 12), border_radius=2)

        elif len(alive_bosses) == 1:
            # 單一 BOSS 置中展示 (比照原單人模式)
            b_obj = alive_bosses[0]
            bw = 500
            bx = (w - bw) // 2 + 30
            by_boss = HUD_TOP_HEIGHT + 14
            b_ratio = max(0.0, b_obj.hp / float(b_obj.max_hp))
            phase_num = getattr(b_obj, 'current_phase', 1)

            frame_w, frame_h = 76, 76
            frame_x = bx - 86
            frame_y = by_boss - 18
            frame_surf = pygame.Surface((frame_w, frame_h), pygame.SRCALPHA)
            frame_surf.fill((10, 20, 35, 220))
            pygame.draw.rect(frame_surf, (40, 210, 255), (0, 0, frame_w, frame_h), 2, border_radius=4)
            surf.blit(frame_surf, (frame_x, frame_y))

            from game.sprites import create_boss_sprite
            boss_spr = create_boss_sprite(b_obj.boss_type, b_obj.stage, 0)
            orig_bw, orig_bh = boss_spr.get_size()
            scale = min((frame_w - 14) / float(orig_bw), (frame_h - 14) / float(orig_bh))
            scaled_bw = max(10, int(orig_bw * scale))
            scaled_bh = max(10, int(orig_bh * scale))
            target_spr = pygame.transform.smoothscale(boss_spr, (scaled_bw, scaled_bh))
            surf.blit(target_spr, target_spr.get_rect(center=(frame_x + frame_w // 2, frame_y + frame_h // 2)))

            phase_names = {1: "階段一：重裝巡弋", 2: "階段二：全舷對空", 3: "階段三：滅世狂暴"}
            b_name = self.font_small.render(f"BOSS: {b_obj.name} [{phase_names.get(phase_num, '階段一')}]", True, (255, 120, 120))
            surf.blit(b_name, (bx, by_boss - 18))

            est_total_secs = max(3, int(b_obj.hp / 135.0))
            est_m = est_total_secs // 60
            est_s = est_total_secs % 60
            time_to_kill_str = f"{est_m:02d}分{est_s:02d}秒 ({est_total_secs}s)"
            highlight_col = (255, 50, 70) if phase_num == 3 else ((255, 165, 20) if phase_num == 2 else (255, 240, 40))

            est_info_txt = self.font_tiny.render(f"⏱ 預估擊斃: {time_to_kill_str}", True, highlight_col)
            surf.blit(est_info_txt, (bx + bw - 210, by_boss - 18))

            pygame.draw.rect(surf, (15, 15, 25), (bx - 2, by_boss - 2, bw + 4, 16), border_radius=4)
            pygame.draw.rect(surf, (50, 20, 20), (bx, by_boss, bw, 12), border_radius=3)
            pygame.draw.rect(surf, highlight_col, (bx, by_boss, int(bw * b_ratio), 12), border_radius=3)

    def draw_midboss_warning(self, surf, timer, midboss_name):
        """中型大魔王突入警報畫面 (不限制戰機控制)"""
        w = surf.get_width()
        if int(timer * 5) % 2 == 0:
            warn_bg = pygame.Surface((w, 72), pygame.SRCALPHA)
            warn_bg.fill((230, 110, 15, 190))
            surf.blit(warn_bg, (0, 210))

            warn_txt = self.font_large.render("⚠️ 警告：中型大魔王 突入接近！ ⚠️", True, COLOR_YELLOW)
            w_rect = warn_txt.get_rect(center=(w // 2, 232))
            surf.blit(warn_txt, w_rect)

            sub_txt = self.font_small.render(f"【{midboss_name}】", True, COLOR_WHITE)
            s_rect = sub_txt.get_rect(center=(w // 2, 262))
            surf.blit(sub_txt, s_rect)

    def draw_fleet_warning(self, surf, timer):
        """敵海上主力艦隊突入警報畫面"""
        w = surf.get_width()
        if int(timer * 4) % 2 == 0:
            warn_bg = pygame.Surface((w, 75), pygame.SRCALPHA)
            warn_bg.fill((220, 90, 15, 180))
            surf.blit(warn_bg, (0, 175))

            warn_txt = self.font_large.render("⚓ 警告：敵主力聯合艦隊 突入！ ⚓", True, COLOR_YELLOW)
            w_rect = warn_txt.get_rect(center=(w // 2, 200))
            surf.blit(warn_txt, w_rect)

            sub_txt = self.font_small.render("ENEMY NAVAL ARMADA DETECTED - PREPARE FOR BATTLE", True, COLOR_WHITE)
            s_rect = sub_txt.get_rect(center=(w // 2, 232))
            surf.blit(sub_txt, s_rect)

    def draw_boss_warning(self, surf, timer):
        """BOSS 登場警報畫面"""
        w = surf.get_width()
        if int(timer * 4) % 2 == 0:
            warn_bg = pygame.Surface((w, 90), pygame.SRCALPHA)
            warn_bg.fill((200, 20, 20, 160))
            surf.blit(warn_bg, (0, SCREEN_HEIGHT // 2 - 45))

            warn_txt = self.font_large.render("! ! WARNING : BOSS APPROACHING ! !", True, COLOR_YELLOW)
            w_rect = warn_txt.get_rect(center=(w // 2, SCREEN_HEIGHT // 2))
            surf.blit(warn_txt, w_rect)

    def draw_stage_clear(self, surf, stage_num, score):
        """過關結算畫面"""
        w = surf.get_width()
        overlay = pygame.Surface((w, 140), pygame.SRCALPHA)
        overlay.fill((10, 30, 50, 200))
        surf.blit(overlay, (0, SCREEN_HEIGHT // 2 - 70))

        c_txt = self.font_huge.render(f"STAGE {stage_num:02d} COMPLETED!", True, COLOR_GOLD)
        c_rect = c_txt.get_rect(center=(w // 2, SCREEN_HEIGHT // 2 - 25))
        surf.blit(c_txt, c_rect)

        sub_txt = self.font_mid.render(f"PREPARING FOR NEXT STAGE... CURRENT SCORE: {score}", True, COLOR_WHITE)
        s_rect = sub_txt.get_rect(center=(w // 2, SCREEN_HEIGHT // 2 + 25))
        surf.blit(sub_txt, s_rect)

    def draw_mode_select(self, surf, selected_mode, frame):
        """
        遊戲模式選擇畫面：
        【核心規則】：
        - 1 人模式：背景畫面以 960*10240 模式執行
        - 2 人模式：背景畫面以 1024*10240 模式執行
        """
        w = surf.get_width()
        surf.fill((10, 15, 26))

        title = self.font_large.render("1945: 二戰空間（II War Space）", True, COLOR_GOLD)
        surf.blit(title, title.get_rect(center=(w // 2, 90)))

        sub = self.font_mid.render("── 請選擇作戰人數模式 (SELECT GAME MODE) ──", True, COLOR_CYAN)
        surf.blit(sub, sub.get_rect(center=(w // 2, 145)))

        modes = [
            {
                "id": 1,
                "title": "【單人作戰模式 (1 PLAYER)】",
                "bg_spec": "背景畫面: 960 * 10240 實景長卷",
                "desc": "單人空戰傳奇，體驗經典二戰王牌縱深突擊！",
                "controls": "控制: 方向鍵 (或WASD) 移動 · M 鍵/空白鍵 射擊 · Z 鍵 特技",
                "color": (40, 220, 255)
            },
            {
                "id": 2,
                "title": "【雙人協同作戰模式 (2 PLAYERS)】",
                "bg_spec": "背景畫面: 1024 * 10240 寬屏實景長卷",
                "desc": "雙人同屏合作！敵機數量加倍四向突入，終極雙大魔王登場！",
                "controls": "1P: 方向鍵/M射擊/Z特技  ·  2P: WXAD/V射擊/C特技  ·  Y 鍵補滿 5 命復活",
                "color": (255, 180, 50)
            }
        ]

        card_w = min(760, w - 60)
        card_h = 160
        start_y = 230

        for i, m in enumerate(modes):
            cy = start_y + i * 190
            is_sel = (i == selected_mode)

            card = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
            if is_sel:
                pulse = int(180 + 75 * math.sin(frame * 0.12))
                card.fill((30, 50, 85, 230))
                pygame.draw.rect(card, (pulse, 215, 60), (0, 0, card_w, card_h), 3, border_radius=10)
            else:
                card.fill((18, 25, 42, 180))
                pygame.draw.rect(card, (60, 80, 110), (0, 0, card_w, card_h), 1, border_radius=10)

            t_col = COLOR_GOLD if is_sel else COLOR_WHITE
            m_title = self.font_large.render(m["title"], True, t_col)
            card.blit(m_title, (24, 18))

            spec_txt = self.font_mid.render(m["bg_spec"], True, m["color"])
            card.blit(spec_txt, (24, 60))

            d_txt = self.font_small.render(m["desc"], True, (220, 230, 240))
            c_txt = self.font_small.render(m["controls"], True, (160, 210, 255) if is_sel else (140, 160, 180))
            card.blit(d_txt, (24, 95))
            card.blit(c_txt, (24, 122))

            surf.blit(card, ((w - card_w) // 2, cy))

        hint_bar = pygame.Surface((w, 75), pygame.SRCALPHA)
        hint_bar.fill((15, 22, 35, 230))
        surf.blit(hint_bar, (0, SCREEN_HEIGHT - 75))

        h1 = self.font_mid.render("【 ↑ / ↓ 方向鍵 或 W / S 鍵】選擇模式    【空白鍵 / ENTER / M】確認", True, COLOR_WHITE)
        surf.blit(h1, h1.get_rect(center=(w // 2, SCREEN_HEIGHT - 45)))
        h2 = self.font_tiny.render("2人模式專屬：4機種不重複選擇 · 雙色子彈縮小二分之一 · 四向敵襲加倍 · 雙魔王 · Y鍵滿血補命", True, COLOR_CYAN)
        surf.blit(h2, h2.get_rect(center=(w // 2, SCREEN_HEIGHT - 18)))

    def draw_plane_select(self, surf, selected_idx, frame):
        """
        開場主戰機選擇介面 (單人模式)
        展示 4 款戰機、性能指標、武裝特色與特技說明
        """
        w = surf.get_width()
        surf.fill((12, 18, 30))

        title = self.font_large.render("1945: 二戰空間（II War Space）", True, COLOR_GOLD)
        surf.blit(title, title.get_rect(center=(w // 2, 70)))

        sub = self.font_mid.render("── 請選擇出擊主戰機 (CHOOSE YOUR FIGHTER) ──", True, COLOR_CYAN)
        surf.blit(sub, sub.get_rect(center=(w // 2, 120)))

        card_w = min(750, w - 40)
        card_h = 132
        start_y = 155

        for i, f_data in enumerate(FIGHTER_TYPES):
            cy = start_y + i * 145
            is_sel = (i == selected_idx)

            card = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
            if is_sel:
                pulse = int(180 + 70 * math.sin(frame * 0.1))
                bg_col = (30, 50, 80, 220)
                border_col = (pulse, 215, 60)
                border_width = 3
            else:
                bg_col = (20, 28, 45, 170)
                border_col = (60, 80, 110)
                border_width = 1

            card.fill(bg_col)
            pygame.draw.rect(card, border_col, (0, 0, card_w, card_h), border_width, border_radius=8)

            spr = create_player_sprite(f_data["id"], "center", frame // 3)
            spr_scaled = pygame.transform.scale(spr, (80, 80))
            card.blit(spr_scaled, (20, 26))

            name_col = COLOR_GOLD if is_sel else COLOR_WHITE
            f_name = self.font_mid.render(f_data["name"], True, name_col)
            f_sub = self.font_small.render(f_data["subtitle"], True, COLOR_CYAN)
            card.blit(f_name, (115, 14))
            card.blit(f_sub, (115, 42))

            desc = self.font_tiny.render(f_data["description"], True, (210, 220, 230))
            card.blit(desc, (115, 72))

            spec_txt = self.font_small.render(f"按鍵 [Z] 特技：{f_data['special_name']}", True, COLOR_YELLOW if is_sel else (180, 180, 140))
            card.blit(spec_txt, (115, 96))

            surf.blit(card, ((w - card_w) // 2, cy))

        hint_bar = pygame.Surface((w, 70), pygame.SRCALPHA)
        hint_bar.fill((15, 22, 35, 230))
        surf.blit(hint_bar, (0, SCREEN_HEIGHT - 70))

        hint1 = self.font_mid.render("【 ↑ / ↓ 方向鍵】切換戰機    【空白鍵 / ENTER / M】確認出擊", True, COLOR_WHITE)
        surf.blit(hint1, hint1.get_rect(center=(w // 2, SCREEN_HEIGHT - 45)))

        hint2 = self.font_tiny.render("遊戲操作：方向鍵移動，M鍵/空白鍵射擊，按鍵 Z 翻轉閃避/防護罩，P 暫停", True, (160, 180, 200))
        surf.blit(hint2, hint2.get_rect(center=(w // 2, SCREEN_HEIGHT - 18)))

    def draw_plane_select_2p(self, surf, p1_idx, p2_idx, selecting_player, frame):
        """
        雙人模式戰機選擇介面：
        【核心規則】：
        - 由第一人先選擇 4 種戰機中的一種戰機
        - 第二人只能選擇剩下三種的其中一種戰機 (第一人已選機種標記鎖定)
        """
        w = surf.get_width()
        surf.fill((12, 18, 30))

        title = self.font_large.render("1945: 二戰空間（II War Space）- 雙人協同出擊", True, COLOR_GOLD)
        surf.blit(title, title.get_rect(center=(w // 2, 60)))

        if selecting_player == 1:
            header_str = "【第 1 人選擇戰機】(PLAYER 1 SELECTING)"
            sub_str = "請第 1 人從 4 款戰機中選擇出擊機種"
            h_col = (40, 220, 255)
        else:
            header_str = "【第 2 人選擇戰機】(PLAYER 2 SELECTING)"
            sub_str = f"第 1 人已選擇【{FIGHTER_TYPES[p1_idx]['name']}】，請第 2 人從剩下 3 款戰機中選擇出擊"
            h_col = (255, 180, 50)

        hdr = self.font_mid.render(header_str, True, h_col)
        surf.blit(hdr, hdr.get_rect(center=(w // 2, 105)))
        sub = self.font_small.render(sub_str, True, COLOR_WHITE)
        surf.blit(sub, sub.get_rect(center=(w // 2, 133)))

        card_w = min(800, w - 40)
        card_h = 132
        start_y = 155

        for i, f_data in enumerate(FIGHTER_TYPES):
            cy = start_y + i * 145
            is_p1_picked = (selecting_player == 2 and i == p1_idx)
            is_sel = (i == (p1_idx if selecting_player == 1 else p2_idx))

            card = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
            if is_p1_picked:
                card.fill((30, 20, 25, 170))
                pygame.draw.rect(card, (180, 40, 50), (0, 0, card_w, card_h), 2, border_radius=8)
            elif is_sel:
                pulse = int(180 + 70 * math.sin(frame * 0.1))
                card.fill((30, 50, 80, 220))
                pygame.draw.rect(card, (pulse, 215, 60), (0, 0, card_w, card_h), 3, border_radius=8)
            else:
                card.fill((20, 28, 45, 170))
                pygame.draw.rect(card, (60, 80, 110), (0, 0, card_w, card_h), 1, border_radius=8)

            spr = create_player_sprite(f_data["id"], "center", frame // 3)
            spr_scaled = pygame.transform.scale(spr, (80, 80))
            if is_p1_picked:
                dark_overlay = pygame.Surface(spr_scaled.get_size(), pygame.SRCALPHA)
                dark_overlay.fill((0, 0, 0, 120))
                spr_scaled.blit(dark_overlay, (0, 0))
            card.blit(spr_scaled, (20, 26))

            name_col = COLOR_GOLD if is_sel else (COLOR_RED if is_p1_picked else COLOR_WHITE)
            f_name = self.font_mid.render(f_data["name"], True, name_col)
            f_sub = self.font_small.render(f_data["subtitle"], True, COLOR_CYAN if not is_p1_picked else (140, 140, 140))
            card.blit(f_name, (115, 14))
            card.blit(f_sub, (115, 42))

            if is_p1_picked:
                locked_tag = self.font_mid.render("🔒 [第 1 人已選擇 - 本機已鎖定]", True, (255, 100, 100))
                card.blit(locked_tag, (115, 75))
            else:
                desc = self.font_tiny.render(f_data["description"], True, (210, 220, 230))
                card.blit(desc, (115, 72))
                spec_key = "[Z]" if selecting_player == 1 else "[C]"
                spec_txt = self.font_small.render(f"特技 {spec_key}：{f_data['special_name']}", True, COLOR_YELLOW if is_sel else (180, 180, 140))
                card.blit(spec_txt, (115, 96))

            surf.blit(card, ((w - card_w) // 2, cy))

        hint_bar = pygame.Surface((w, 75), pygame.SRCALPHA)
        hint_bar.fill((15, 22, 35, 230))
        surf.blit(hint_bar, (0, SCREEN_HEIGHT - 75))

        if selecting_player == 1:
            h1 = self.font_mid.render("第 1 人：【 ↑ / ↓ 方向鍵】選擇戰機    【 M 鍵 / 空白鍵 / ENTER 】確認出擊", True, COLOR_WHITE)
            h2 = self.font_tiny.render("P1 控制方式：方向鍵控制移動，M 鍵射擊，Z 鍵翻轉閃避/防護罩", True, (160, 210, 255))
        else:
            h1 = self.font_mid.render("第 2 人：【 W / X 鍵】選擇剩餘戰機    【 V 鍵 / ENTER 】確認出擊", True, COLOR_GOLD)
            h2 = self.font_tiny.render("P2 控制方式：W(上) X(下) A(左) D(右) 控制移動，V 鍵射擊，C 鍵特技", True, (255, 210, 160))

        surf.blit(h1, h1.get_rect(center=(w // 2, SCREEN_HEIGHT - 45)))
        surf.blit(h2, h2.get_rect(center=(w // 2, SCREEN_HEIGHT - 18)))

    def draw_game_over(self, surf, score, stage_num):
        """遊戲結束畫面"""
        w = surf.get_width()
        overlay = pygame.Surface((w, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 10, 20, 210))
        surf.blit(overlay, (0, 0))

        go_txt = self.font_huge.render("MISSION FAILED", True, COLOR_RED)
        surf.blit(go_txt, go_txt.get_rect(center=(w // 2, SCREEN_HEIGHT // 2 - 80)))

        st_txt = self.font_mid.render(f"FINAL PROGRESS: STAGE {stage_num} / 20", True, COLOR_CYAN)
        surf.blit(st_txt, st_txt.get_rect(center=(w // 2, SCREEN_HEIGHT // 2 - 20)))

        sc_txt = self.font_mid.render(f"TOTAL SCORE: {score}", True, COLOR_GOLD)
        surf.blit(sc_txt, sc_txt.get_rect(center=(w // 2, SCREEN_HEIGHT // 2 + 20)))

        prompt_y = self.font_small.render("【提示：若在雙人模式中生命用盡，可按 Y 鍵補滿 5 命立即復活！】", True, COLOR_YELLOW)
        surf.blit(prompt_y, prompt_y.get_rect(center=(w // 2, SCREEN_HEIGHT // 2 + 60)))

        retry_txt = self.font_mid.render("PRESS [ENTER] TO RETRY  OR  [ESC] TO EXIT", True, COLOR_WHITE)
        surf.blit(retry_txt, retry_txt.get_rect(center=(w // 2, SCREEN_HEIGHT // 2 + 105)))

    def draw_victory_all(self, surf, score):
        """全 20 大關卡通關終極勝利畫面"""
        w = surf.get_width()
        overlay = pygame.Surface((w, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((5, 15, 30, 220))
        surf.blit(overlay, (0, 0))

        vic_txt = self.font_huge.render("ALL 20 STAGES CONQUERED!!", True, COLOR_GOLD)
        surf.blit(vic_txt, vic_txt.get_rect(center=(w // 2, SCREEN_HEIGHT // 2 - 90)))

        sub_txt = self.font_large.render("終極世界和平 - 空戰王牌傳奇誕生", True, COLOR_CYAN)
        surf.blit(sub_txt, sub_txt.get_rect(center=(w // 2, SCREEN_HEIGHT // 2 - 30)))

        sc_txt = self.font_mid.render(f"FINAL RECORD SCORE: {score}", True, COLOR_WHITE)
        surf.blit(sc_txt, sc_txt.get_rect(center=(w // 2, SCREEN_HEIGHT // 2 + 30)))

        prompt = self.font_mid.render("PRESS [ENTER] TO PLAY AGAIN", True, COLOR_YELLOW)
        surf.blit(prompt, prompt.get_rect(center=(w // 2, SCREEN_HEIGHT // 2 + 100)))
