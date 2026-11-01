"""
1945: 二戰空間（II War Space）
程序化音效與復古街機音樂合成器 (Synthesized Arcade Audio Engine)
使用 NumPy 產生純淨 8-bit/16-bit 復古音效與動態背景旋律，無需外部音檔，100% 穩定且相容 Docker/無音效卡環境
支援背景音樂 (BGM) 循環播放、我軍射擊音效、雷射音效與所有敵軍 (戰機/戰車/軍艦/BOSS) 被擊斃音效
"""

import math
import numpy as np
import pygame

class SoundManager:
    _instance = None

    def __init__(self):
        self.enabled = False
        self.sample_rate = 22050
        self.channels = 2
        self.sounds = {}
        self.bgm_playing = False
        self.bgm_channel = None
        self._init_audio()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = SoundManager()
        elif cls._instance.enabled and not pygame.mixer.get_init():
            cls._instance.bgm_playing = False
            cls._instance._init_audio()
        return cls._instance

    def _init_audio(self):
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.pre_init(22050, -16, 2, 512)
                pygame.mixer.init()
            init_info = pygame.mixer.get_init()
            if init_info:
                self.sample_rate = init_info[0]
                self.channels = init_info[2]
            pygame.mixer.set_num_channels(32)
            # 保留第 0 聲道專供 BGM 使用，防止密集射擊/爆炸音效搶佔導致背景音樂中斷
            pygame.mixer.set_reserved(1)
            self.bgm_channel = pygame.mixer.Channel(0)
            self.enabled = True
            self._generate_sounds()
            self._generate_bgm()
        except Exception:
            # 在無音效卡、無 PulseAudio 或 Headless Docker 環境中自動靜音安全回退
            self.enabled = False

    def _make_sound(self, samples, sample_rate=None):
        if not self.enabled:
            return None
        try:
            # 確保為 16-bit 整數陣列，並相容單聲道/立體聲與各版本 NumPy
            samples = np.clip(samples, -1.0, 1.0)
            int_samples = (samples * 32767).astype(np.int16)
            if self.channels == 2:
                arr = np.ascontiguousarray(np.column_stack((int_samples, int_samples)))
            else:
                arr = np.ascontiguousarray(int_samples)
            try:
                return pygame.sndarray.make_sound(arr)
            except Exception:
                return pygame.mixer.Sound(buffer=arr.tobytes())
        except Exception:
            return None

    def _generate_sounds(self):
        sr = self.sample_rate

        # 1. 我軍常規射擊音效 (短促高穿透機砲)
        t = np.linspace(0, 0.08, int(sr * 0.08), False)
        freq = np.linspace(1000, 220, len(t))
        wave = (0.7 * np.sin(2 * np.pi * freq * t) + 0.3 * np.sign(np.sin(2 * np.pi * (freq * 0.5) * t))) * np.exp(-t * 30)
        self.sounds['player_shoot'] = self._make_sound(wave)

        # 2. 我軍高能追蹤雷射射擊音效 (未來高能脈衝激光)
        t_l = np.linspace(0, 0.12, int(sr * 0.12), False)
        f_l = np.linspace(1400, 480, len(t_l))
        wave_l = np.sin(2 * np.pi * f_l * t_l) * (0.8 + 0.2 * np.sin(2 * np.pi * 90 * t_l)) * np.exp(-t_l * 18)
        self.sounds['laser_shoot'] = self._make_sound(wave_l)

        # 3. 敵方空軍戰機被擊斃音效 (中頻爆裂加白噪音)
        t = np.linspace(0, 0.28, int(sr * 0.28), False)
        noise = np.random.uniform(-1, 1, len(t))
        freq = np.linspace(180, 35, len(t))
        low = np.sin(2 * np.pi * freq * t)
        wave = (0.65 * noise + 0.35 * low) * np.exp(-t * 11)
        self.sounds['explosion'] = self._make_sound(wave)

        # 4. 敵方地面戰車被擊斃音效 (沉重金屬裝甲爆破、低頻重音與衝擊震盪)
        t_t = np.linspace(0, 0.48, int(sr * 0.48), False)
        noise_t = np.random.uniform(-1, 1, len(t_t))
        freq_t = np.linspace(95, 25, len(t_t))
        sub_t = np.sin(2 * np.pi * freq_t * t_t)
        clank = np.sin(2 * np.pi * 260 * t_t) * np.exp(-t_t * 22)
        wave_t = (0.55 * noise_t + 0.45 * sub_t + 0.15 * clank) * np.exp(-t_t * 6.5)
        self.sounds['tank_explosion'] = self._make_sound(wave_t)

        # 5. 敵方海上軍艦被擊沉/擊斃音效 (宏大海戰重裝爆炸、深水炸彈深沉轟鳴與海嘯共振)
        t_s = np.linspace(0, 0.75, int(sr * 0.75), False)
        noise_s = np.random.uniform(-1, 1, len(t_s))
        freq_s = np.linspace(80, 20, len(t_s))
        sub_s = np.sin(2 * np.pi * freq_s * t_s)
        sub_depth = np.sin(2 * np.pi * 38 * t_s) * np.exp(-t_s * 3.5)
        wave_s = (0.55 * noise_s + 0.5 * sub_s + 0.35 * sub_depth) * np.exp(-t_s * 4.2)
        self.sounds['ship_explosion'] = self._make_sound(wave_s)

        # 6. BOSS 巨型旗艦毀滅爆炸 (超低音震撼衝擊波，持續次聲波轟鳴)
        t_b = np.linspace(0, 1.2, int(sr * 1.2), False)
        noise_b = np.random.uniform(-1, 1, len(t_b))
        freq_b = np.linspace(90, 16, len(t_b))
        sub_b = np.sin(2 * np.pi * freq_b * t_b)
        sub_rumble = np.sin(2 * np.pi * 28 * t_b) * np.exp(-t_b * 2.2)
        wave_b = (0.6 * noise_b + 0.6 * sub_b + 0.4 * sub_rumble) * np.exp(-t_b * 3.0)
        self.sounds['boss_explosion'] = self._make_sound(wave_b)

        # 7. 戰利品撿取音 (雙音頻清脆上升和弦)
        t1 = np.linspace(0, 0.07, int(sr * 0.07), False)
        t2 = np.linspace(0, 0.12, int(sr * 0.12), False)
        w1 = np.sin(2 * np.pi * 587.33 * t1)  # D5
        w2 = np.sin(2 * np.pi * 880.00 * t2)  # A5
        wave = np.concatenate([w1 * np.exp(-t1 * 10), w2 * np.exp(-t2 * 10)])
        self.sounds['powerup'] = self._make_sound(wave)

        # 8. 雷射戰果吃到音效 (高亢能量充能琶音)
        t_l1 = np.linspace(0, 0.06, int(sr * 0.06), False)
        t_l2 = np.linspace(0, 0.06, int(sr * 0.06), False)
        t_l3 = np.linspace(0, 0.12, int(sr * 0.12), False)
        wl1 = np.sin(2 * np.pi * 659.25 * t_l1)   # E5
        wl2 = np.sin(2 * np.pi * 880.00 * t_l2)   # A5
        wl3 = np.sin(2 * np.pi * 1318.51 * t_l3)  # E6
        wave_lp = np.concatenate([wl1 * np.exp(-t_l1 * 8), wl2 * np.exp(-t_l2 * 8), wl3 * np.exp(-t_l3 * 8)])
        self.sounds['laser_powerup'] = self._make_sound(wave_lp)

        # 9. 翻轉閃避呼嘯聲 (急速都卜勒氣流音)
        t = np.linspace(0, 0.4, int(sr * 0.4), False)
        freq = 300 + 400 * np.sin(np.pi * t / 0.4)
        wave = np.sin(2 * np.pi * freq * t) * np.sin(np.pi * t / 0.4) * 0.6
        self.sounds['barrel_roll'] = self._make_sound(wave)

        # 10. 護盾防護力場開啟/中彈彈開音
        t = np.linspace(0, 0.18, int(sr * 0.18), False)
        freq = np.linspace(350, 750, len(t))
        wave = np.sin(2 * np.pi * freq * t) * np.exp(-t * 8)
        self.sounds['shield'] = self._make_sound(wave)

        # 11. 受到傷害警報扣血音 (沉悶撞擊與警示)
        t = np.linspace(0, 0.15, int(sr * 0.15), False)
        freq = np.linspace(220, 80, len(t))
        wave = (np.sin(2 * np.pi * freq * t) + 0.3 * np.random.uniform(-1, 1, len(t))) * np.exp(-t * 15)
        self.sounds['player_hit'] = self._make_sound(wave)

        # 12. BOSS 登場警報聲 (雙頻交替警報)
        t = np.linspace(0, 0.3, int(sr * 0.3), False)
        wave = np.sin(2 * np.pi * 440 * t) * 0.7
        self.sounds['boss_alert'] = self._make_sound(wave)

        # 13. 關卡獲勝慶祝和弦 (Fanfare)
        t_note = 0.12
        notes = [523.25, 659.25, 783.99, 1046.50]  # C5, E5, G5, C6
        parts = []
        for n in notes:
            tn = np.linspace(0, t_note, int(sr * t_note), False)
            parts.append(np.sin(2 * np.pi * n * tn) * np.exp(-tn * 6))
        wave = np.concatenate(parts)
        self.sounds['victory'] = self._make_sound(wave)

    def _generate_bgm(self):
        """
        合成豐富低頻多音軌交響戰鬥背景音樂 (Rich Multi-Track Arcade Shmup Symphony)
        【核心規則】：音訊需豐富低頻多音軌，不能單調的音樂！
        音軌架構包含：
        1. Track 1: Sub-Bass (40Hz~75Hz 超重超低音震盪)
        2. Track 2: Heavy Punch Kick Drum (渾厚大鼓底鼓)
        3. Track 3: Driving Synth Bassline (16分音符律動電貝斯)
        4. Track 4: Marching Drums & Cymbals (小軍鼓 + 碎音鈸 + 腳踏鈸)
        5. Track 5: Harmonic Chord Arpeggios (和聲琶音襯底軌)
        6. Track 6: Epic Brass Lead Melody (熱血英勇雙振盪器進行曲主旋律)
        """
        sr = self.sample_rate
        bpm = 140
        beat_dur = 60.0 / bpm
        step_dur = beat_dur / 2.0  # 八分音符步長
        total_steps = 64  # 32 拍大循環 (約 13.7 秒，分段主題展開，非單調循環)
        total_time = step_dur * total_steps

        total_samples = int(sr * total_time)
        bgm_wave = np.zeros(total_samples, dtype=np.float32)

        # 和弦進程 (Am -> F -> C -> G -> Dm -> Am -> F -> E7)
        # 對應 8 個小節，每小節 8 步 (共 64 步)
        chord_roots = [
            55.00,  # A1 (超重低頻)
            43.65,  # F1
            65.41,  # C2
            49.00,  # G1
            73.42,  # D2
            55.00,  # A1
            43.65,  # F1
            41.20   # E1
        ]

        # 64 步主旋律 (雙振盪器熱血軍事進行曲)
        lead_seq = [
            # 小節 1: A 小調序奏衝刺
            440.0, 0, 440.0, 523.25, 587.33, 0, 523.25, 440.0,
            # 小節 2: F 大調穿甲下潛
            349.23, 0, 392.00, 440.00, 392.00, 0, 349.23, 329.63,
            # 小節 3: C 大調昂揚爬升
            523.25, 0, 523.25, 587.33, 659.25, 0, 587.33, 523.25,
            # 小節 4: G 大調蓄勢待發
            392.00, 440.00, 493.88, 523.25, 587.33, 659.25, 698.46, 783.99,
            # 小節 5: D 小調激昂高潮
            880.00, 0, 880.00, 783.99, 698.46, 0, 659.25, 587.33,
            # 小節 6: A 小調迴旋壓制
            659.25, 0, 587.33, 523.25, 440.00, 0, 523.25, 587.33,
            # 小節 7: F 大調全火力齊射
            698.46, 0, 698.46, 659.25, 587.33, 0, 523.25, 440.00,
            # 小節 8: E7 終止式銜接循環
            493.88, 523.25, 587.33, 659.25, 783.99, 830.61, 880.00, 0
        ]

        # 琶音音高矩陣 (16分音符分解和弦)
        chord_triads = [
            [220.0, 261.63, 329.63, 440.0],  # Am
            [174.61, 220.0, 261.63, 349.23], # F
            [261.63, 329.63, 392.00, 523.25],# C
            [196.00, 246.94, 293.66, 392.00],# G
            [146.83, 220.0, 293.66, 349.23], # Dm
            [220.0, 261.63, 329.63, 440.0],  # Am
            [174.61, 220.0, 261.63, 349.23], # F
            [164.81, 207.65, 246.94, 329.63] # E7
        ]

        for s in range(total_steps):
            start_idx = int(s * step_dur * sr)
            n_samples = int(step_dur * sr)
            if start_idx + n_samples > total_samples:
                n_samples = total_samples - start_idx
            t_s = np.linspace(0, step_dur, n_samples, False)

            bar_idx = (s // 8) % len(chord_roots)
            root_f = chord_roots[bar_idx]

            # ----------------------------------------------------
            # 音軌 1: Sub-Bass (40~75Hz 極重低頻持續震波)
            # ----------------------------------------------------
            sub_bass = np.sin(2 * np.pi * root_f * t_s) * 0.38
            sub_bass += np.sin(2 * np.pi * (root_f * 0.5) * t_s) * 0.18  # 次音頻超重低音
            bgm_wave[start_idx:start_idx + n_samples] += sub_bass

            # ----------------------------------------------------
            # 音軌 2: Punchy Kick Drum (沉重有力底鼓，每拍或切分打擊)
            # ----------------------------------------------------
            if (s % 4 == 0) or (s % 8 == 6):
                kick_env = np.exp(-t_s * 18)
                kick_f = np.linspace(160, 42, n_samples)
                kick = np.sin(2 * np.pi * kick_f * t_s) * kick_env * 0.42
                bgm_wave[start_idx:start_idx + n_samples] += kick

            # ----------------------------------------------------
            # 音軌 3: Driving Synth Bassline (80~180Hz 16分音符律動電貝斯)
            # ----------------------------------------------------
            mid_f = root_f * 2.0
            # 鋸齒波加方波複合貝斯
            bass_env = np.exp(-t_s * 8)
            synth_bass = (0.6 * np.sign(np.sin(2 * np.pi * mid_f * t_s)) +
                          0.4 * (2 * (t_s * mid_f - np.floor(t_s * mid_f + 0.5)))) * bass_env * 0.22
            bgm_wave[start_idx:start_idx + n_samples] += synth_bass

            # ----------------------------------------------------
            # 音軌 4: Marching Drums & Percussion (軍鼓 + 碎音鈸 + 踩鈸)
            # ----------------------------------------------------
            # 小軍鼓 (在第 2 與第 4 拍強勁切入)
            if s % 4 == 2:
                snare_noise = np.random.uniform(-1, 1, n_samples) * np.exp(-t_s * 22) * 0.25
                snare_tone = np.sin(2 * np.pi * 185 * t_s) * np.exp(-t_s * 28) * 0.2
                bgm_wave[start_idx:start_idx + n_samples] += (snare_noise + snare_tone)

            # 金屬 16 分音符 Hi-Hat (提供高速戰鬥前進感)
            hat_env = np.exp(-t_s * 45)
            hi_hat = np.random.uniform(-1, 1, n_samples) * hat_env * 0.1
            bgm_wave[start_idx:start_idx + n_samples] += hi_hat

            # 樂段重音鈸 (Crash Cymbal on Bar 1 & Bar 5)
            if s in [0, 32]:
                crash_env = np.exp(-t_s * 5)
                crash = np.random.uniform(-1, 1, n_samples) * crash_env * 0.22
                bgm_wave[start_idx:start_idx + n_samples] += crash

            # ----------------------------------------------------
            # 音軌 5: Harmonic Chord Arpeggios (多聲部琶音和聲襯底)
            # ----------------------------------------------------
            triad = chord_triads[bar_idx]
            arp_note = triad[s % len(triad)]
            arp_wave = (0.7 * np.sin(2 * np.pi * arp_note * t_s) +
                        0.3 * np.sin(2 * np.pi * (arp_note * 2.0) * t_s)) * np.exp(-t_s * 10) * 0.16
            bgm_wave[start_idx:start_idx + n_samples] += arp_wave

            # ----------------------------------------------------
            # 音軌 6: Epic Brass Lead (熱血英雄銅管主旋律)
            # ----------------------------------------------------
            lf = lead_seq[s % len(lead_seq)]
            if lf > 0:
                # 雙振盪器微失諧 (Detuned Saw + Square)，呈現復古街機厚重銅管感
                detune1 = lf * 1.003
                detune2 = lf * 0.997
                lead_wave = (0.5 * np.sin(2 * np.pi * lf * t_s) +
                             0.3 * np.sin(2 * np.pi * detune1 * t_s) +
                             0.2 * np.sign(np.sin(2 * np.pi * detune2 * t_s))) * np.exp(-t_s * 3.8) * 0.28
                bgm_wave[start_idx:start_idx + n_samples] += lead_wave

        # 頂底端交叉平滑淡入淡出，保證無縫循環 (Looping Seamlessness)
        fade_len = int(sr * 0.08)
        fade_in = np.linspace(0, 1, fade_len)
        fade_out = np.linspace(1, 0, fade_len)
        bgm_wave[:fade_len] *= fade_in
        bgm_wave[-fade_len:] *= fade_out

        # 混音增益歸一化，保留充沛低頻下潛，防止削波失真
        max_val = np.max(np.abs(bgm_wave))
        if max_val > 0.85:
            bgm_wave = (bgm_wave / max_val) * 0.85

        self.sounds['bgm'] = self._make_sound(bgm_wave)

    def start_bgm(self):
        """啟動動態背景音樂循環"""
        if not self.enabled or self.bgm_playing:
            return
        snd = self.sounds.get('bgm')
        if snd and self.bgm_channel:
            try:
                self.bgm_channel.set_volume(0.35)
                self.bgm_channel.play(snd, loops=-1)
                self.bgm_playing = True
            except Exception:
                pass

    def stop_bgm(self):
        """停止背景音樂"""
        if self.bgm_channel and self.bgm_playing:
            try:
                self.bgm_channel.stop()
                self.bgm_playing = False
            except Exception:
                pass

    def play(self, sound_name):
        """播放指定音效 (支援備用語義與音效降級)"""
        if not self.enabled:
            return

        snd = self.sounds.get(sound_name)
        if not snd:
            # 安全回退匹配
            if "tank" in sound_name or "ship" in sound_name:
                snd = self.sounds.get("explosion")
            elif "laser" in sound_name:
                snd = self.sounds.get("player_shoot")

        if snd:
            try:
                snd.play()
            except Exception:
                pass
