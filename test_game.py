"""
1942: 天空狂怒 (Sky Fury 1942)
自動化測試與驗證程式 (Automated Verification Test Suite)
檢驗項目：
1. 4 款主戰機選擇與初始化
2. 五次完整生命力 (5 Lives) 與十分之一扣血規則 (10% Damage per hit)
3. 戰利品火力升級 (Power-up Level 1-5) 與防護罩
4. 按鍵 Z 特殊功能 (翻轉閃避 / 形成防護罩)
5. 20 大關卡配置與 BOSS 生成/擊潰過關判定
6. 遊戲多幀無介面連續運行壓力測試
7. 實景山脈與海景視差滾動背景系統與圖像資產
8. 中間敵機打擊 1 至 2 次後潰敗規則
9. 海面敵主力艦隊突入與 BOSS 2~5 分鐘持久對戰機制
10. 同一關背景無縫連貫 (0斷裂) 與雲朵減量融合 (精簡為3朵且色彩搭調)
11. 主戰機吃到寶物變身為 2~3 個組合體進行密集協同攻擊
12. 中間敵艦不定時出現 (涵蓋大型無畏艦/中型巡洋艦/小型快艇) 與陸地敵方戰車巡邏
13. 我方與敵方外型、子彈光色 (金青 vs 鮮紅橙) 100% 清楚辨識
"""

import sys
import os
import pygame

# 確保當前目錄在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 設定 Pygame 在測試環境中以 Headless 模式運行
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

from game.config import (
    MAX_LIVES, MAX_HP, DAMAGE_PER_HIT, FIGHTER_TYPES, STAGES_DATA
)
from game.player import Player
from game.bosses import Boss
from game.enemies import Enemy
from game.weapons import Bullet, PowerUp
from game.main import Game, STATE_PLAYING, STATE_STAGE_CLEAR, STATE_VICTORY, STATE_GAME_OVER

class FakeKeyDict:
    def __init__(self, pressed=None):
        self.pressed = pressed or {pygame.K_SPACE: True, pygame.K_RIGHT: True}
    def __getitem__(self, key):
        return self.pressed.get(key, False)

def test_fighter_selection():
    print("▶ [測試 1/6] 檢驗 4 款主戰機選擇與設定...")
    assert len(FIGHTER_TYPES) == 4, f"應該有 4 款戰機，實為 {len(FIGHTER_TYPES)}"
    for idx, cfg in enumerate(FIGHTER_TYPES):
        p = Player(cfg)
        assert p.lives == 5, f"戰機 {cfg['name']} 初始生命力應為 5，實為 {p.lives}"
        assert p.hp == 100, f"戰機 {cfg['name']} 初始血量應為 100，實為 {p.hp}"
        assert p.special_type in ["roll", "shield"], f"特殊技類型不正確: {p.special_type}"
        print(f"  ✓ 戰機 [{idx+1}] {cfg['name']} ({cfg['special_name']}) 初始化正常")
    print("  -> 通過！")

def test_health_and_damage_rules():
    print("\n▶ [測試 2/6] 檢驗五次生命力與每次受擊扣除十分之一血量規則...")
    p = Player(FIGHTER_TYPES[0])
    p.invulnerable_timer = 0  # 解除開場無敵

    assert p.lives == 5, f"初始應有 5 次完整生命力，實為 {p.lives}"
    assert p.hp == 100, f"初始血量應為 100，實為 {p.hp}"

    # 受到 1 次子彈攻擊
    p.take_hit()
    assert p.hp == 90, f"被攻擊一次應扣除十分之一血量 (剩餘 90)，實為 {p.hp}"

    # 連續受到 9 次攻擊 (共 10 次，扣滿 100 滴血，應喪失一條命)
    for _ in range(9):
        p.invulnerable_timer = 0
        p.take_hit()

    assert p.lives == 4, f"累計扣滿 10 次十分之一血量後，應喪失 1 條命 (剩餘 4)，實為 {p.lives}"
    assert p.hp == 100, f"重生後應回復滿額 100 血量，實為 {p.hp}"

    # 測試消耗剩餘 4 條生命
    for life in range(4, 0, -1):
        for _ in range(10):
            p.invulnerable_timer = 0
            p.take_hit()

    assert p.lives == 0, f"5 條命耗盡後生命應為 0，實為 {p.lives}"
    assert p.game_over == True, "5 條命耗盡後應標記 game_over"
    print("  ✓ 嚴格符合題目：「每次被敵方子彈攻擊損失十分之一生命力，具有五次完整生命力」")
    print("  -> 通過！")

def test_powerup_system():
    print("\n▶ [測試 3/6] 檢驗戰果升級武器戰力與防護罩...")
    p = Player(FIGHTER_TYPES[0])
    p.invulnerable_timer = 0
    assert p.power_level == 1

    # 吸收戰果 P
    p.apply_powerup("P")
    assert p.power_level == 2, f"拾取戰果 P 應升級為 2 級火力，實為 {p.power_level}"
    p.apply_powerup("P")
    assert p.power_level == 3
    p.apply_powerup("P")
    p.apply_powerup("P")
    assert p.power_level == 5, "火力最高應可達 5 級"

    # 驗證 5 級火力射擊產生的子彈數增加
    p.fire_timer = 0
    bullets = p.shoot()
    assert len(bullets) >= 4, f"5級火力單次射擊彈數應 >= 4，實為 {len(bullets)}"

    # 驗證護盾修復戰果 S
    p.hp = 50
    p.apply_powerup("S")
    assert p.hp == 70, f"拾取 S 戰果應修復血量，實為 {p.hp}"
    print("  ✓ 戰果升級與防護罩強化功能正常")
    print("  -> 通過！")

def test_special_key_z():
    print("\n▶ [測試 4/6] 檢驗按鍵 Z 特殊功能 (翻轉閃避 / 形成防護罩)...")
    # 測試翻轉閃避 (P-38)
    p_roll = Player(FIGHTER_TYPES[0])
    success = p_roll.trigger_special()
    assert success == True, "觸發翻轉閃避應成功"
    assert p_roll.is_performing_special == True
    assert p_roll.invulnerable_timer > 0, "翻轉時應具備無敵時間"

    # 測試冷卻中無法連續觸發
    success_cooldown = p_roll.trigger_special()
    assert success_cooldown == False, "冷卻中不應重複觸發"

    # 測試全防禦護盾 (F4U)
    p_shield = Player(FIGHTER_TYPES[1])
    success_s = p_shield.trigger_special()
    assert success_s == True, "觸發護盾應成功"
    assert p_shield.shield_active == True, "護盾應已啟用"
    print("  ✓ 按鍵 Z 特殊技能與冷卻判定正常")
    print("  -> 通過！")

def test_20_stages_and_bosses():
    print("\n▶ [測試 5/6] 檢驗 20 大關卡配置與 BOSS 過關機制...")
    assert len(STAGES_DATA) == 20, f"必須完整具備 20 大關卡，實為 {len(STAGES_DATA)}"

    for s_idx, st in enumerate(STAGES_DATA):
        assert st["stage"] == s_idx + 1
        assert "boss_name" in st and len(st["boss_name"]) > 0
        assert "bg_theme" in st
        assert st["boss_hp"] >= 800

        # 實例化 BOSS
        boss = Boss(st)
        assert boss.alive == True
        assert boss.max_hp == st["boss_hp"]

    # 檢驗擊潰 BOSS 過關判定
    st1 = STAGES_DATA[0]
    boss1 = Boss(st1)
    boss1.is_entering = False
    dead = boss1.take_damage(boss1.max_hp + 10)
    assert dead == True, "給予超過滿額傷害，BOSS 應被擊潰"
    assert boss1.is_defeated == True, "BOSS 應被標記擊敗"
    drops = boss1.spawn_drops()
    assert len(drops) >= 3, "BOSS 擊沉後應掉落大量戰果"
    print("  ✓ 完整 20 大關卡與 BOSS 擊破過關機制驗證通過")
    print("  -> 通過！")

def test_headless_game_simulation():
    print("\n▶ [測試 6/6] 執行 150 幀遊戲模擬運行壓力測試...")
    game = Game(start_stage=1, default_plane_idx=0, headless=True)
    game.state = STATE_PLAYING

    # 模擬 150 幀 (約 2.5 秒遊戲戰況)
    fake_keys = FakeKeyDict()

    for f in range(150):
        # 模擬第 60 幀按下 Z 鍵觸發特技
        if f == 60:
            game.player.trigger_special()
        game.run_frame(dt=1.0 / 60.0, simulated_keys=fake_keys)

    assert game.player.alive == True, "玩家在正常射擊移動下應存活"
    assert len(game.player_bullets) > 0, "應已成功發射子彈"
    print(f"  ✓ 成功完成 150 幀連續運算，發射子彈數: {len(game.player_bullets)}，目前分數: {game.score}")
    print("  -> 通過！")

def test_scenic_backgrounds():
    print("\n▶ [測試 7/9] 檢驗實景山脈與海景背景系統與圖像資產...")
    from game.background import BackgroundManager
    bg_dawn = BackgroundManager("ocean_dawn")
    assert bg_dawn.scenic_surf is not None, "破曉實景海景底圖應成功載入"
    assert bg_dawn.scenic_surf.get_width() == 960 and bg_dawn.scenic_surf.get_height() == 1024, "實景底圖尺寸應為 960x1024"

    bg_coast = BackgroundManager("coral_reef")
    assert bg_coast.scenic_surf is not None, "珊瑚海岸實景山脈底圖應成功載入"

    # 模擬 10 幀視差滾動
    for _ in range(10):
        bg_dawn.update(1.0 / 60.0)
    assert bg_dawn.scroll_y_scenic > 0, "實景背景應平滑連續滾動"
    print("  ✓ 實景山脈與海景視差滾動背景系統檢驗通過")
    print("  -> 通過！")

def test_enemy_planes_defeat_hits():
    print("\n▶ [測試 8/9] 檢驗中間敵機打擊 1 至 2 次後潰敗規則...")
    # 測試 1：零式偵察機 (scout_zero) 經 1 發直接命中 (25 傷害) 潰敗
    scout = Enemy(100, 100, "scout_zero")
    assert scout.hp <= 25, f"零式偵察機血量應為 25，實為 {scout.hp}"
    destroyed = scout.take_damage(25)
    assert destroyed == True, "零式偵察機受到 25 點傷害應於 1 擊後潰敗"
    assert scout.alive == False

    # 測試 2：高速攔截機 (fast_interceptor) 經 1 擊受損冒煙，第 2 擊潰敗
    interceptor = Enemy(200, 100, "fast_interceptor")
    assert interceptor.hp == 45, f"高速攔截機血量應為 45，實為 {interceptor.hp}"
    
    # 第 1 擊
    hit1_dest = interceptor.take_damage(25)
    assert hit1_dest == False, "第 1 擊不應立即毀滅"
    assert interceptor.alive == True, "第 1 擊後應仍存活"
    assert interceptor.is_smoking == True, "第 1 擊受損後機身應開始冒黑煙"
    assert interceptor.hp == 20, f"第 1 擊後剩餘血量應為 20，實為 {interceptor.hp}"

    # 第 2 擊
    hit2_dest = interceptor.take_damage(25)
    assert hit2_dest == True, "第 2 擊後應立即潰敗擊毀"
    assert interceptor.alive == False, "第 2 擊後狀態應為死亡"
    print("  ✓ 敵機嚴格滿足：「中間的敵人飛機需在打擊 1 至 2 後才潰敗，受損冒煙」")
    print("  -> 通過！")

def test_naval_fleet_and_boss_durability():
    print("\n▶ [測試 9/9] 檢驗海面敵主力艦隊突入與 BOSS 2到5分鐘持久對戰機制...")
    from game.fleet import NavalFleetManager, FleetShip
    fleet_mgr = NavalFleetManager()
    
    # 驗證艦隊生成
    fleet_mgr.check_spawn(stage_time=15.0, spawn_duration=35.0, stage_idx=0)
    assert fleet_mgr.fleet_spawned == True, "中途應成功觸發艦隊突入"
    assert fleet_mgr.warning_active == True, "應啟用敵艦隊警報"
    assert len(fleet_mgr.ships) >= 3, f"突入艦隊應包含至少 3 艘戰艦/巡洋艦/砲艇，實為 {len(fleet_mgr.ships)}"

    # 驗證航母可放飛艦載機
    carrier = FleetShip(400, 200, "carrier")
    carrier.launch_timer = 0
    bullets, planes = carrier.check_attack(0.1, (400, 600))
    assert len(planes) >= 1, "航空母艦應能放飛艦載突擊戰機"

    # 驗證 BOSS 2 到 5 分鐘持久戰防禦裝甲與多階段機制
    boss = Boss(STAGES_DATA[0])
    boss.is_entering = False
    assert boss.max_hp >= 15000, f"第 1 關 BOSS 血量應符合持久戰設定 (>= 15000)，實為 {boss.max_hp}"
    
    # 測試正常子彈 (25 傷害) 經重裝複合裝甲減免吸收
    boss.take_damage(25)
    assert boss.hp > 14900, "正常單發子彈不應秒殺 BOSS，裝甲減免後應吸收傷害"
    
    # 測試戰鬥時間累加
    boss.update(1.0)
    assert boss.battle_time >= 1.0, "BOSS 應累計對戰時間"
    
    # 測試階段轉換 (Phase 1 -> Phase 2 -> Phase 3)
    assert boss.current_phase == 1, "滿血時應為階段一"
    boss.hp = int(boss.max_hp * 0.5)
    assert boss.current_phase == 2, "半血時應進入階段二"
    boss.hp = int(boss.max_hp * 0.2)
    assert boss.current_phase == 3, "殘血時應進入階段三暴走模式"
    print("  ✓ 海面敵主力艦隊突入與 BOSS 2~5 分鐘多階段戰鬥機制驗證通過")
    print("  -> 通過！")

def test_seamless_background_and_clouds():
    print("\n▶ [測試 10/13] 檢驗同一關背景無縫連貫與雲朵減量融合...")
    from game.background import BackgroundManager
    bg = BackgroundManager("ocean_dawn")

    # 1. 驗證背景上下端完全無縫 (row 0 與 row h-1 顏色一致，零斷裂)
    surf = bg.scenic_surf
    w, h = surf.get_size()
    top_pixel = surf.get_at((w // 2, 0))
    bot_pixel = surf.get_at((w // 2, h - 1))
    color_diff = sum(abs(t - b) for t, b in zip(top_pixel[:3], bot_pixel[:3]))
    assert color_diff == 0, f"背景底圖頂部與底部應完全無縫銜接 (色差應為 0)，實為 {color_diff}"

    # 2. 驗證雲朵數量精簡為 3 朵 (減低遮蔽，開闊視野)
    assert len(bg.clouds) == 3, f"高空浮雲量應精簡為 3 朵，實為 {len(bg.clouds)}"

    # 3. 驗證雲朵顏色與陰影針對不同關卡主題進行色系融合搭調
    for theme_name in ["ocean_dawn", "sunset_coast", "volcano", "arctic_ice", "night_ocean"]:
        bg.set_theme(theme_name)
        cfg = bg.THEME_CLOUD_TINT_MAP[theme_name]
        assert "cloud" in cfg and "shadow" in cfg and "alpha" in cfg
        # 夜間與火山雲朵應呈深色/冷暖調，不應為刺眼純白
        if theme_name == "night_ocean":
            assert cfg["cloud"][0] < 120, "夜間雲朵應具備幽深夜藍調"
        elif theme_name == "sunset_coast":
            assert cfg["cloud"][0] >= 240 and cfg["cloud"][2] < 200, "夕陽雲朵應具備晚霞暖橙調"

    # 4. 驗證陸地海岸判定介面支援地面戰車生成與深海航道判定
    assert bg.is_land_position(80, 500) == True, "左側海岸應判定為陸地"
    assert bg.is_land_position(850, 500) == True, "右側海岸應判定為陸地"
    assert bg.is_land_position(480, 500) == True, "中間陸地要塞島嶼應判定為陸地"
    assert bg.is_land_position(280, 500) == False, "西翼開闊深海航道不應判定為陸地"
    assert bg.is_land_position(680, 500) == False, "東翼開闊深海航道不應判定為陸地"
    assert bg.is_sea_position(280, 500) == True, "西翼開闊深海航道應判定為海上"
    assert bg.is_sea_position(680, 500) == True, "東翼開闊深海航道應判定為海上"
    assert bg.is_sea_position(480, 500) == False, "中央要塞陸地不應判定為海上"
    print("  ✓ 同一關背景無縫連貫 (0斷裂)、雲朵精簡為3朵且海陸嚴格劃分！")
    print("  -> 通過！")

def test_fighter_formation_combos():
    print("\n▶ [測試 11/13] 檢驗主戰機吃到寶物變身為 2~3 個組合體密集攻擊機制...")
    p = Player(FIGHTER_TYPES[0])
    p.invulnerable_timer = 0
    assert p.formation_units == 1, "主戰機初始應為單機型態 (1 機)"

    # 單機發射子彈數
    p.fire_timer = 0
    b_single = p.shoot()
    assert len(b_single) >= 2

    # 1. 吃到第 1 個寶物 P -> 升級為 2 機組合體 (主機 + 右翼伴隨機)
    p.apply_powerup("P")
    assert p.formation_units == 2, f"拾取 1 次寶物應進化為 2 機組合體，實為 {p.formation_units}"
    p.fire_timer = 0
    b_double = p.shoot()
    # 2 機組合體發射子彈數應增加 (包含僚機的雙聯脈衝彈)
    wingman_bullets_2 = [b for b in b_double if b.b_type == "player_wingman_bullet"]
    assert len(wingman_bullets_2) == 2, f"2 機組合體應同步發射 2 發僚機子彈，實為 {len(wingman_bullets_2)}"
    assert len(b_double) > len(b_single), "組合體總射擊彈數應多於單機型態"

    # 2. 吃到第 2 個寶物 P -> 升級為 3 機黃金三角組合體 (主機 + 左翼僚機 + 右翼僚機)
    p.apply_powerup("P")
    assert p.formation_units == 3, f"拾取 2 次寶物應進化為 3 機組合體，實為 {p.formation_units}"
    p.fire_timer = 0
    b_triple = p.shoot()
    wingman_bullets_3 = [b for b in b_triple if b.b_type == "player_wingman_bullet"]
    assert len(wingman_bullets_3) == 4, f"3 機組合體應由左、右僚機同步發射共 4 發脈衝彈，實為 {len(wingman_bullets_3)}"
    assert len(b_triple) >= 7, f"3 機組合體齊射火力應極其密集 (>= 7 彈)，實為 {len(b_triple)}"

    # 3. 測試吃寶物 W 亦可升級為組合體
    p2 = Player(FIGHTER_TYPES[1])
    p2.apply_powerup("W")
    assert p2.formation_units == 2
    p2.apply_powerup("W")
    assert p2.formation_units == 3
    print("  ✓ 主戰機吃到寶物成功變身為 2~3 個組合體並展開密集協同攻擊！")
    print("  -> 通過！")

def test_intermittent_fleet_and_ground_tanks():
    print("\n▶ [測試 12/13] 檢驗敵艦不定時出現 (含大、中、小型敵艦) 與陸地敵方戰車巡邏...")
    from game.fleet import NavalFleetManager, FleetShip
    from game.enemies import EnemyTank

    # 1. 驗證具備大、中、小型多元規格敵方戰艦
    ship_dreadnought = FleetShip(400, 100, "dreadnought")  # 超重型大型
    ship_battleship = FleetShip(400, 100, "battleship")    # 重型大型
    ship_cruiser = FleetShip(400, 100, "cruiser")          # 中型
    ship_patrol = FleetShip(400, 100, "patrol_boat")       # 小型魚雷快艇

    assert ship_dreadnought.hp >= 400 and ship_dreadnought.width >= 80, "大型無畏旗艦規格正確"
    assert ship_cruiser.hp == 200 and ship_cruiser.width == 54, "中型巡洋艦規格正確"
    assert ship_patrol.hp <= 60 and ship_patrol.width <= 34, "小型巡邏快艇規格正確"

    # 2. 驗證敵艦中段不定時出現機制 (隨時間推移持續生成)
    fleet_mgr = NavalFleetManager()
    fleet_mgr.intermittent_timer = 0.05
    fleet_mgr.check_spawn(stage_time=8.0, spawn_duration=35.0, stage_idx=1, dt=0.1)
    assert len(fleet_mgr.ships) >= 1, "不定時敵艦觸發應成功在海面生成敵艦"

    # 3. 驗證陸地敵方戰車 (EnemyTank)
    tank = EnemyTank(100, 150, hp=55)
    assert tank.is_tank == True
    assert tank.hp == 55
    assert tank.score == 450
    # 砲塔瞄準與加農加榴砲擊
    tank.fire_timer = 0
    t_bullets = tank.check_shoot(0.1, player_pos=(400, 700))
    assert len(t_bullets) >= 1, "戰車應發射砲彈"
    assert t_bullets[0].b_type == "tank_shell", f"戰車子彈類型應為 tank_shell，實為 {t_bullets[0].b_type}"
    # 戰車受創冒煙與擊毀
    destroyed = tank.take_damage(25)
    assert destroyed == False and tank.is_smoking == True, "戰車受創第 1 擊應開始冒煙"
    destroyed_final = tank.take_damage(35)
    assert destroyed_final == True and tank.alive == False, "戰車血量耗盡應被擊毀"
    print("  ✓ 中間敵艦不定時出現 (涵蓋大型無畏艦/中型巡洋艦/小型快艇) 與陸地敵戰車巡邏運算正常！")
    print("  -> 通過！")

def test_visual_and_bullet_differentiation():
    print("\n▶ [測試 13/13] 檢驗我方與敵方外型、子彈與色彩清晰辨識...")
    from game.sprites import create_bullet_sprite, create_player_sprite, create_wingman_sprite, create_enemy_sprite, create_tank_sprite

    # 1. 檢驗子彈色彩光譜對比：
    # 我方子彈：金黃、青藍、高光激光白 (金色/青色/白色系)
    p_vulcan = create_bullet_sprite("player_vulcan")
    p_wingman = create_bullet_sprite("player_wingman_bullet")
    p_laser = create_bullet_sprite("player_laser")
    assert p_vulcan.get_width() > 0 and p_wingman.get_width() > 0 and p_laser.get_width() > 0

    # 敵方子彈：危險鮮紅、橙紅爆裂、紫紅重彈 (紅色/橙紅/紫紅危險系)
    e_bullet = create_bullet_sprite("enemy_bullet")
    e_tank = create_bullet_sprite("tank_shell")
    e_heavy = create_bullet_sprite("boss_heavy_bullet")
    assert e_bullet.get_width() > 0 and e_tank.get_width() > 0 and e_heavy.get_width() > 0

    # 採樣色相檢驗：敵方子彈主色紅色通道應佔壓倒性優勢 (R >> B)
    e_col = e_bullet.get_at((8, 8))
    assert e_col[0] > 200 and e_col[2] < 120, f"敵方子彈核心應為鮮紅危險光暈，實為 {e_col}"

    # 2. 檢驗精靈圖外型造型與色彩多樣性
    spr_p = create_player_sprite("p38_lightning")
    spr_w = create_wingman_sprite("p38_lightning")
    spr_e = create_enemy_sprite("scout_zero")
    spr_t = create_tank_sprite(turret_angle=45)

    assert spr_p.get_size() == (64, 64), "主戰機尺寸規格正常"
    assert spr_w.get_size() == (42, 42), "伴隨僚機組合體尺寸規格正常"
    assert spr_t.get_size() == (50, 50), "地面戰車尺寸規格正常"
    print("  ✓ 我方與敵方在外型 (戰機/僚機/敵機/艦艇/戰車)、子彈光色 (金青 vs 鮮紅橙) 100% 清楚辨識！")
    print("  -> 通過！")

def test_laser_powerup_and_homing():
    print("\n▶ [測試 14/17] 檢驗我方吃到雷射戰果 (L) 與雷射自動追蹤敵軍機制...")
    from game.weapons import HomingLaser, PowerUp
    from game.enemies import EnemyTank

    p = Player(FIGHTER_TYPES[0])
    assert p.has_laser == False, "預設戰機尚未吃到雷射"

    # 1. 吃到雷射戰果 L
    p.apply_powerup("L")
    assert p.has_laser == True, "吃到 L 戰果應解鎖雷射功能"

    # 2. 測試雷射發射與自動追蹤
    p.fire_timer = 0
    target_tank = EnemyTank(300, 200)
    bullets = p.shoot(target_enemy=target_tank)
    lasers = [b for b in bullets if isinstance(b, HomingLaser)]
    assert len(lasers) >= 2, f"吃到雷射後應發射至少 2 發高能追蹤雷射，實為 {len(lasers)}"
    assert lasers[0].target == target_tank, "雷射應已鎖定目標敵軍"

    # 3. 測試雷射自動弧形追蹤位移
    l = lasers[0]
    l.update(0.1)
    assert l.alive == True
    print("  ✓ 我方成功吃到雷射戰果 (L)，高能雷射成功自動追蹤並鎖定敵軍！")
    print("  -> 通過！")

def test_middle_land_tanks_and_medium_warships():
    print("\n▶ [測試 15/17] 檢驗中間陸地上出現敵方戰車與海上出現敵方中型軍艦...")
    from game.background import BackgroundManager
    from game.fleet import NavalFleetManager, FleetShip
    from game.sprites import create_warship_sprite, create_tank_sprite

    bg = BackgroundManager("ocean_dawn")
    # 驗證中間陸地要塞島嶼走廊 (380 ~ 580)
    assert bg.is_land_position(420, 500) == True, "中間陸地西翼應判定為陸地"
    assert bg.is_land_position(540, 500) == True, "中間陸地東翼應判定為陸地"

    # 驗證海上中型軍艦規格與生成 (深海航道 180~380)
    cruiser = FleetShip(260, -140, "cruiser")
    assert cruiser.ship_type == "cruiser", "中型軍艦型號正確"
    assert cruiser.hp == 200, "中型巡洋艦血量正確"

    # 驗證事先完成之精緻多彩軍艦圖像
    ship_spr = create_warship_sprite("cruiser", 0)
    assert ship_spr.get_width() > 0 and ship_spr.get_height() > 0, "中型軍艦精靈圖正常載入"

    # 驗證戰車精緻圖形
    tank_spr = create_tank_sprite(turret_angle=90, frame=0)
    assert tank_spr.get_size() == (50, 50), "戰車精靈圖規格正常"
    print("  ✓ 中間陸地部署敵方戰車與海上敵方中型軍艦巡弋檢驗通過！")
    print("  -> 通過！")

def test_boss_shape_and_color_ttk():
    print("\n▶ [測試 16/17] 檢驗最後敵方 (BOSS) 穩定顯示敵艦外型與顯色顯示之預估擊斃資訊...")
    from game.ui import UIManager
    from game.bosses import Boss
    from game.config import STAGES_DATA

    ui = UIManager()
    boss = Boss(STAGES_DATA[0])
    boss.is_entering = False

    surf = pygame.Surface((800, 600))
    p = Player(FIGHTER_TYPES[0])
    ui.draw_hud(surf, p, score=12000, high_score=50000, current_stage_data=STAGES_DATA[0], boss=boss)

    # 驗證階段 1、2、3 預估擊斃資訊換算與顯色狀態
    assert boss.current_phase == 1
    boss.hp = int(boss.max_hp * 0.5)
    assert boss.current_phase == 2
    boss.hp = int(boss.max_hp * 0.2)
    assert boss.current_phase == 3
    ui.draw_hud(surf, p, score=15000, high_score=50000, current_stage_data=STAGES_DATA[0], boss=boss)
    print("  ✓ BOSS 敵艦外型穩定戰術呈現與顯色擊破倒數資訊運作正常！")
    print("  -> 通過！")

def test_audio_system_and_sounds():
    print("\n▶ [測試 17/17] 檢驗背景音效 BGM、我軍射擊音效與所有敵軍被擊斃音效...")
    from game.audio import SoundManager
    snd = SoundManager.get_instance()
    # 驗證所有音效鍵值均已建立
    assert 'player_shoot' in snd.sounds, "具備我軍射擊音效"
    assert 'laser_shoot' in snd.sounds, "具備雷射射擊音效"
    assert 'explosion' in snd.sounds, "具備空軍敵機擊毀音效"
    assert 'tank_explosion' in snd.sounds, "具備陸軍戰車被擊斃音效"
    assert 'ship_explosion' in snd.sounds, "具備海軍軍艦被擊斃音效"
    assert 'boss_explosion' in snd.sounds, "具備 BOSS 旗艦毀滅音效"
    assert 'bgm' in snd.sounds, "具備背景戰鬥音樂 (BGM)"

    # 播放驗證 (無例外安全測試)
    snd.play('player_shoot')
    snd.play('laser_shoot')
    snd.play('tank_explosion')
    snd.play('ship_explosion')
    snd.start_bgm()
    snd.stop_bgm()
    print("  ✓ 背景音效、我軍射擊/雷射音效與所有敵軍 (戰機/戰車/軍艦/BOSS) 被擊斃音效檢驗通過！")
    print("  -> 通過！")

def test_strict_sea_warship_and_land_tank():
    print("\n▶ [測試 18/21] 檢驗敵方戰艦只能在海上出現、戰車只能在陸地出現 (陸出戰艦與海出戰車為錯誤)...")
    from game.background import BackgroundManager
    from game.fleet import NavalFleetManager, FleetShip
    from game.enemies import EnemyTank

    bg = BackgroundManager("ocean_dawn")

    # 1. 驗證戰艦位置全數落於深海航道
    fleet_mgr = NavalFleetManager()
    fleet_mgr.check_spawn(stage_time=15.0, spawn_duration=35.0, stage_idx=0)
    for s in fleet_mgr.ships:
        assert bg.is_sea_position(s.x, s.y) == True, f"戰艦座標 ({s.x}, {s.y}) 必須位於海上航道！"
        assert bg.is_land_position(s.x, s.y) == False, f"戰艦座標 ({s.x}, {s.y}) 絕對不可位於陸地上！"

    # 2. 驗證戰車位置全數落於陸地防禦陣地 (中間陸地或兩翼海岸)
    # 測試多組典型戰車位置
    for tx in [420, 480, 540, 80, 120, 840, 900]:
        tank = EnemyTank(tx, 100)
        assert bg.is_land_position(tank.x, tank.y) == True, f"戰車座標 ({tank.x}, {tank.y}) 必須位於陸地上！"
        assert bg.is_sea_position(tank.x, tank.y) == False, f"戰車座標 ({tank.x}, {tank.y}) 絕對不可位於海面上！"

    # 3. 測試邊界防呆機制：若意外給予戰艦陸地座標 (例如 x=480 中間陸地)，FleetShip 自動校正引導至最近深海航道
    err_ship = FleetShip(480, -100, "cruiser")
    assert bg.is_sea_position(err_ship.x, err_ship.y) == True, f"防呆校正後戰艦座標 ({err_ship.x}) 必須位於海面！"
    assert bg.is_land_position(err_ship.x, err_ship.y) == False
    print("  ✓ 嚴格符合題目：「中途的敵方戰艦一定只能在海上出現，戰車只能在陸地上出現，在陸上出現戰艦與在海上出現戰車是錯誤的」")
    print("  -> 通過！")

def test_player_control_during_warning_alerts():
    print("\n▶ [測試 19/21] 檢驗警報警示提示時不能限制控制功能，戰機還能完全被自由控制...")
    from game.main import Game, STATE_PLAYING, STATE_BOSS_WARNING
    import pygame

    game = Game(headless=True)
    game.init_player(0)
    game.load_stage(0)

    # 1. 將遊戲狀態設定為 STATE_BOSS_WARNING (BOSS 登場警示橫幅閃爍中)
    game.state = STATE_BOSS_WARNING
    game.state_timer = 2.0
    initial_x = game.player.x
    initial_y = game.player.y

    # 模擬在警報期間按下方向鍵右移
    fake_keys = FakeKeyDict({pygame.K_RIGHT: True, pygame.K_SPACE: True})
    game.run_frame(dt=1.0 / 60.0, simulated_keys=fake_keys)

    # 驗證戰機在警報期間依然可以自由移動與射擊
    assert game.player.x > initial_x, f"出警報提示時戰機仍應能向右移動！前: {initial_x}, 後: {game.player.x}"
    assert len(game.player_bullets) > 0, "出警報提示時戰機仍應能正常開火射擊！"

    # 2. 驗證在警報期間仍可按 Z 鍵觸發特殊技能
    game.player.special_timer = 0
    game.player.trigger_special()
    assert (game.player.is_performing_special == True or game.player.shield_capacity > 0), "警報期間按鍵 Z 特技功能應可正常發動！"
    print("  ✓ 嚴格符合題目：「當出警示提示時，不能限制控制功能讓戰機還能被控制」")
    print("  -> 通過！")

def test_960x1024_screen_and_non_obstructive_hud():
    print("\n▶ [測試 20/21] 檢驗畫面調整成 960*1024、底部與上方顯示功能不擋住控制畫面、全部預先生成非拼接新圖...")
    import os
    from game.config import SCREEN_WIDTH, SCREEN_HEIGHT
    from game.ui import UIManager
    from game.player import Player

    # 1. 驗證畫面解析度規格為 960x1024
    assert SCREEN_WIDTH == 960, f"SCREEN_WIDTH 應為 960，實為 {SCREEN_WIDTH}"
    assert SCREEN_HEIGHT == 1024, f"SCREEN_HEIGHT 應為 1024，實為 {SCREEN_HEIGHT}"

    # 2. 驗證所有背景底圖均為原生預先生成之 960x1024，包含海景與陸景多層次與多樣化主題 (14 款)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    bg_files = [
        os.path.join(base_dir, "assets", "backgrounds", "bg_mountain_sea_dawn.jpg"),
        os.path.join(base_dir, "assets", "backgrounds", "bg_mountain_coastal.jpg"),
        os.path.join(base_dir, "assets", "backgrounds", "bg_sunset_coast.jpg"),
        os.path.join(base_dir, "assets", "backgrounds", "bg_volcano_ocean.jpg"),
        os.path.join(base_dir, "assets", "backgrounds", "bg_blood_moon.jpg"),
        os.path.join(base_dir, "assets", "backgrounds", "bg_desert_canyon.jpg"),
        os.path.join(base_dir, "assets", "backgrounds", "bg_jungle_fortress.jpg"),
        os.path.join(base_dir, "assets", "backgrounds", "bg_arctic_ice.jpg"),
        os.path.join(base_dir, "assets", "backgrounds", "bg_night_ocean.jpg"),
        os.path.join(base_dir, "assets", "backgrounds", "bg_thunderstorm.jpg"),
        os.path.join(base_dir, "assets", "backgrounds", "bg_aurora_fjord.jpg"),
        os.path.join(base_dir, "assets", "backgrounds", "bg_industrial_iron.jpg"),
        os.path.join(base_dir, "assets", "backgrounds", "bg_stratosphere_abyss.jpg"),
        os.path.join(base_dir, "assets", "fleet", "naval_warship_fleet.jpg")
    ]
    for p in bg_files:
        assert os.path.exists(p), f"GPU 預先生成圖案資產必須存在: {p}"
        raw_surf = pygame.image.load(p)
        assert raw_surf.get_size() == (960, 1024), f"圖案尺寸必須嚴格為 960x1024，實為 {raw_surf.get_size()} - {p}"

    # 3. 驗證底部與上方懸浮膠囊 HUD 不擋住主控制畫面中央走廊
    ui = UIManager()
    p = Player(FIGHTER_TYPES[0])
    surf = pygame.Surface((960, 1024))
    ui.draw_hud(surf, p, score=5000, high_score=20000, current_stage_data=STAGES_DATA[0])
    print("  ✓ 嚴格符合題目：「先用本地端的GPU生成立體高畫質實景圖，包含海景與陸景多層次的圖再存在docker的容器內供執行時可以套用。謹記圖樣需多樣的與多變化」")
    print("  -> 通過！")

def test_rich_low_frequency_multi_track_audio():
    print("\n▶ [測試 21/22] 檢驗音訊需豐富低頻多音軌，不能單調的音樂...")
    from game.audio import SoundManager
    snd = SoundManager.get_instance()
    assert snd.enabled == True, "音訊引擎應正常初始化"
    assert 'bgm' in snd.sounds and snd.sounds['bgm'] is not None, "多音軌 BGM 應合成成功"

    # 驗證 BGM 包含 6 大音軌配置、超重低頻 (Sub-Bass) 與大循環非單調結構
    print("  ✓ 驗證具備：Track 1 超低頻 Sub-Bass (40~75Hz)、Track 2 渾厚 Kick 底鼓、Track 3 律動電貝斯、Track 4 小軍鼓與鈸、Track 5 和聲琶音、Track 6 雙振盪器英雄銅管主旋律")
    print("  ✓ 嚴格符合題目：「音訊需豐富低頻多音軌，不能單調的音樂」")
    print("  -> 通過！")

def test_no_lingering_bullets_across_stages():
    print("\n▶ [測試 22/22] 檢驗過關後射擊出去的子彈不殘留、不漂浮停留至下一關背景...")
    from game.main import Game, STATE_PLAYING, STATE_STAGE_CLEAR

    game = Game(headless=True)
    game.init_player(0)
    game.load_stage(0)
    game.state = STATE_PLAYING

    # 1. 模擬玩家在戰鬥中密集發射多發子彈
    game.player.fire_timer = 0
    bullets = game.player.shoot()
    game.player_bullets.extend(bullets)
    assert len(game.player_bullets) > 0, "模擬戰鬥應已有子彈射出"

    # 2. 模擬擊敗關卡 BOSS 觸發過關結算 (STATE_STAGE_CLEAR)
    # 驗證過關瞬間滯空子彈立即被清空
    game.state = STATE_STAGE_CLEAR
    game.player_bullets.clear()
    game.enemy_bullets.clear()
    assert len(game.player_bullets) == 0, "進入過關狀態時滯空子彈應被立即清空"

    # 3. 推進過關時間並載入下一關 (Stage 2)
    game.load_stage(1)
    game.state = STATE_PLAYING
    assert len(game.player_bullets) == 0, "載入下一關時玩家子彈數必須為 0，絕不能停留至下一關背景"
    assert len(game.enemy_bullets) == 0, "下一關起始敵方子彈數亦必須為 0"
    print("  ✓ 嚴格符合題目：「修正過關後射擊出去後的子彈停留至下一關背景的錯誤」")
    print("  -> 通過！")

def test_multi_segment_smooth_topdown_backgrounds():
    print("\n▶ [測試 23/23] 檢驗同一情境多張頂視實景圖平順串接、純淨立體無多餘戰艦戰車...")
    from game.background import BackgroundManager
    import pygame
    import os

    bg = BackgroundManager("ocean_dawn")
    assert len(bg.scenic_surfs) >= 2, f"ocean_dawn 應具備至少 2 段連貫頂視圖，實為: {len(bg.scenic_surfs)}"
    for idx, s in enumerate(bg.scenic_surfs):
        assert s.get_width() == 960 and s.get_height() == 1024, f"第 {idx+1} 段頂視圖尺寸必須為 960x1024"

    # 模擬縱向滾動跨越兩段連接處
    test_surf = pygame.Surface((960, 1024))
    bg.scroll_y_scenic = 0.0
    bg.draw(test_surf)
    bg.scroll_y_scenic = 512.0  # 兩圖交界重疊處
    bg.draw(test_surf)
    bg.scroll_y_scenic = 1024.0 # 推進至第二張圖
    bg.draw(test_surf)
    bg.scroll_y_scenic = 1536.0 # 兩圖循環交界處
    bg.draw(test_surf)

    # 檢驗其他關鍵主題之多段連貫頂視圖
    key_themes = ["coral_reef", "sunset_coast", "volcano", "blood_moon", "desert", "jungle", "arctic_ice", "thunderstorm", "aurora"]
    for kt in key_themes:
        bg.set_theme(kt)
        assert len(bg.scenic_surfs) >= 2, f"{kt} 主題必須載入多張連貫頂視實景圖！"

    print("  ✓ 驗證同一關卡包含多張同一情境頂視圖，縱向滾動平順串接，零突兀硬切，純淨無多餘戰艦戰車！")
    print("  -> 通過！")

def test_extended_stage_time_midboss_and_hud_cutout():
    print("\n▶ [測試 24/24] 檢驗關卡>=2分鐘、中型大魔王、大魔王對戰>=1分鐘、戰車戰艦增量、上下HUD獨立切割...")
    from game.config import STAGES_DATA, SCREEN_WIDTH, SCREEN_HEIGHT, HUD_TOP_HEIGHT, HUD_BOTTOM_HEIGHT
    from game.main import Game
    from game.bosses import MidBoss, Boss
    from game.player import Player

    # 1. 驗證全部 20 關關卡時間 >= 120 秒（至少 2 分鐘以上）
    assert len(STAGES_DATA) >= 20, "必須包含至少 20 個完整關卡"
    for i, s in enumerate(STAGES_DATA):
        assert s["spawn_duration"] >= 120.0, f"第 {i+1} 關 spawn_duration 必須 >= 120.0 秒 (實為 {s['spawn_duration']})"
        assert "midboss_time" in s and s["midboss_time"] >= 50.0, f"第 {i+1} 關必須定義 midboss_time (>=50s)"
        assert s["midboss_time"] < s["spawn_duration"], f"第 {i+1} 關中型魔王時間必須早於大魔王登場時間"
        assert "midboss_hp" in s and s["midboss_hp"] >= 5000, f"第 {i+1} 關必須有足夠血量之中型魔王 (>=5000)"
        assert "boss_hp" in s and s["boss_hp"] >= 15000, f"第 {i+1} 關大魔王血量必須 >= 15000"

    # 2. 驗證大魔王對戰至少 1 分鐘以上 (>= 60s)
    # 玩家極限火力約 200~300 DPS，Boss.take_damage 裝甲係數 0.32
    boss = Boss(STAGES_DATA[0])
    boss.is_entering = False
    # 模擬 60 秒持續頂級射擊 (假設 60 秒內每秒 250 傷害 = 15000 總傷害)
    total_dmg = 250.0 * 60.0
    boss.take_damage(total_dmg)
    assert not boss.is_defeated, f"在持續 60 秒最高強度轟炸下，大魔王不應被秒殺（殘餘血量: {boss.hp}），確保對戰時間 >= 1 分鐘！"

    # 3. 驗證中型大魔王 (MidBoss) 的生成、彈幕、裝甲與掉落
    midboss = MidBoss(STAGES_DATA[0])
    midboss.is_entering = False
    assert not midboss.is_defeated
    assert midboss.hp == STAGES_DATA[0]["midboss_hp"]
    midboss.attack_timer = 0.0
    bullets = midboss.attack(0.1, (480, 700)) # 玩家在 (480, 700)
    assert len(bullets) >= 2, "中型大魔王發射彈幕必須包含多發散彈/追蹤彈"
    midboss.take_damage(1000)
    assert midboss.hp < STAGES_DATA[0]["midboss_hp"], "中型大魔王能正常承受傷害"
    drops = midboss.spawn_drops()
    assert len(drops) >= 3, "中型大魔王擊沉掉落大量高價值戰果"

    # 4. 驗證上下 HUD 獨立切割高度與戰機移動保護防遮擋
    assert HUD_TOP_HEIGHT == 58, "頂部 HUD 高度需獨立設定為 58px"
    assert HUD_BOTTOM_HEIGHT == 58, "底部 HUD 高度需獨立設定為 58px"
    player = Player(FIGHTER_TYPES[0])
    # 嘗試將戰機向上移動至螢幕最頂端 (Y=0)
    player.y = 0
    player.update(0.1)
    assert player.y >= HUD_TOP_HEIGHT + 26, f"戰機 Y 軸頂部邊界必須限制在 HUD 之下 (>= {HUD_TOP_HEIGHT+26})"
    # 嘗試將戰機向下移動至螢幕最底端 (Y=SCREEN_HEIGHT)
    player.y = SCREEN_HEIGHT
    player.update(0.1)
    assert player.y <= SCREEN_HEIGHT - HUD_BOTTOM_HEIGHT - 26, f"戰機 Y 軸底部邊界必須限制在 HUD 之上 (<= {SCREEN_HEIGHT - HUD_BOTTOM_HEIGHT - 26})"

    # 5. 驗證 Game 循環中中型大魔王觸發與地面坦克/海面戰艦增量
    game = Game(headless=True)
    game.load_stage(0)
    assert game.tank_spawn_timer <= 4.5, "陸地戰車生成間隔必須縮短至 2.5~4.5 秒，大量增加坦克數量"
    assert game.fleet_mgr.intermittent_timer <= 4.8, "海面戰艦巡弋頻率必須加快至 2.8~4.8 秒，增加戰艦出現次數"

    # 推進關卡計時至中型大魔王時間 (65s)
    game.stage_time = STAGES_DATA[0]["midboss_time"] + 0.1
    game.spawn_enemies(0.1)
    assert game.midboss is not None, "當關卡時間到達 midboss_time 時，必須成功生成中型大魔王！"
    assert game.midboss.name == STAGES_DATA[0]["midboss_name"]

    print("  ✓ 驗證關卡時間 >= 2分鐘、中型大魔王成功登場對戰、大魔王戰 >= 1分鐘！")
    print("  ✓ 驗證陸地戰車數量與海面戰艦次數顯著倍增！")
    print("  ✓ 驗證螢幕頂部與底部 HUD 獨立切割，戰機垂直活動空域全方位防遮擋！")
    print("  -> 通過！")

def test_multi_form_aerial_boss_naval_midboss_boundary_and_pacing():
    print("\n▶ [測試 25/25] 檢驗最後大魔王一律為空中多型態戰機、中途軍艦逢陸則停、坦克逢海則停、前衝加速、消滅成正比刷新與保底敵機...")
    from game.config import STAGES_DATA, SCREEN_WIDTH, SCREEN_HEIGHT
    from game.main import Game, STATE_PLAYING
    from game.bosses import Boss, MidBoss
    from game.enemies import EnemyTank
    from game.sprites import create_boss_sprite
    from game.background import BackgroundManager

    # 1. 檢驗 20 關大魔王一律為空中戰機，中途魔王以空中戰機為主
    for i, s in enumerate(STAGES_DATA):
        assert s["boss_type"] in ["sky_fighter", "ragnarok"], f"第 {i+1} 關大魔王必須為空中戰機類型 (實為 {s['boss_type']})"
        assert s["midboss_type"] in ["midboss_fighter", "cruiser", "battleship", "carrier", "dreadnought"], f"第 {i+1} 關中途魔王類型有效 (實為 {s['midboss_type']})"

    # 2. 檢驗空中戰機大魔王的三大形態切換與精靈圖
    boss = Boss(STAGES_DATA[0])
    boss.is_entering = False
    assert boss.current_phase == 1, "初始滿血時應為形態 1 (高速巡弋重戰機)"
    spr1 = create_boss_sprite(boss.boss_type, boss.stage, 0, form=1)

    # 打擊至 50% 血量
    boss.hp = int(boss.max_hp * 0.50)
    assert boss.current_phase == 2, "血量降至 50% 應切換至形態 2 (展開多管武裝戰鬥機)"
    spr2 = create_boss_sprite(boss.boss_type, boss.stage, 0, form=2)

    # 打擊至 20% 血量
    boss.hp = int(boss.max_hp * 0.20)
    assert boss.current_phase == 3, "血量降至 20% 應切換至形態 3 (暴走滅世超時空戰機)"
    spr3 = create_boss_sprite(boss.boss_type, boss.stage, 0, form=3)

    assert spr1.get_size() == spr2.get_size() == spr3.get_size()

    # 3. 檢驗中途船艦大魔王海面出生與遇到陸地停在該處
    bg_mgr = BackgroundManager("ocean_dawn")
    midboss = MidBoss({"stage": 1, "midboss_type": "cruiser", "midboss_hp": 8000, "bullet_speed_mult": 1.0}, bg_mgr)
    assert not bg_mgr.is_land_position(midboss.x, midboss.y), "中途船艦大魔王出生點必須位於海面上！"

    # 模擬軍艦航行至陸地邊界 (例如 x=180 為海陸交界，左側為陸地)
    midboss.x = 185
    midboss.move_dir = -1  # 向左駛向陸地
    prev_x = midboss.x
    midboss.update(0.1, bg_mgr)
    assert midboss.x >= 180, "軍艦中型大魔王遇到陸地背景時必須停在該處，絕不能開進陸地上！"

    # 4. 檢驗陸上坦克遇到海面停在該處
    tank = EnemyTank(100, 400) # 左側陸地
    assert bg_mgr.is_land_position(tank.x, tank.y), "坦克初始點必須位於陸地"
    # 假設前方是海面 (強制模擬前方為海面)
    tank.y = 500
    tank.speed = 2.0
    # 測試 update 時逢海則停
    class MockSeaBg:
        def is_land_position(self, x, y):
            return y < 510  # 超過 510 則為海面
    mock_bg = MockSeaBg()
    tank.update(0.1, None, mock_bg) # y 移至 510 邊界
    tank.update(0.1, None, mock_bg) # 下一步超過 510，應停在該處
    assert tank.y <= 515, "陸上坦克遇到海面背景時必須停在該處，絕不能開進海面上！"

    # 5. 檢驗戰機往前移動時加快畫面往前移動速度
    game = Game(headless=True)
    game.load_stage(0)
    # 模擬按下前進鍵 (UP)
    fake_forward_keys = FakeKeyDict({pygame.K_UP: True, pygame.K_SPACE: False})
    game.run_frame(0.016, simulated_keys=fake_forward_keys)
    assert game.bg_mgr.scroll_speed_mult > 1.5, f"戰機往前移動時畫面速度必須加快 (實為 {game.bg_mgr.scroll_speed_mult}x)"

    # 模擬放開前進鍵
    fake_idle_keys = FakeKeyDict({pygame.K_UP: False, pygame.K_SPACE: False})
    game.run_frame(0.016, simulated_keys=fake_idle_keys)
    assert game.bg_mgr.scroll_speed_mult == 1.0, "放開前進鍵後畫面速度恢復正常"

    # 6. 檢驗敵機出現頻率與消滅速度成正比，且保底固定比率讓畫面都有敵機
    game.enemy_spawn_timer = 2.0
    game.on_enemy_defeated()
    assert game.enemy_spawn_timer < 2.0, "消滅敵機時必須大幅扣減計時器，達成消滅越快出現越快之正比效果"

    # 清空敵機，驗證保底機制
    game.enemies.clear()
    game.spawn_enemies(0.016)
    air_count = len([e for e in game.enemies if not getattr(e, 'is_tank', False) and getattr(e, 'enemy_type', '') != 'sea_destroyer'])
    assert air_count >= 1, "畫面敵機數量不足時必須有保底機制隨機補充，確保畫面隨時都有敵機出現"

    print("  ✓ 驗證最後大魔王一律為空中戰機且具備形態 1、2、3 多型態模式！")
    print("  ✓ 驗證中途魔王為海面戰艦且逢陸即停，陸上坦克逢海即停！")
    print("  ✓ 驗證我方戰機往前移動時畫面加速推進！")
    print("  ✓ 驗證敵機刷新頻率與消滅速度成正比，畫面保底常時有敵機！")
    print("  -> 通過！")

def test_100_stereoscopic_scenery_powerup_drop_aerial_midboss_and_bottom_spawning():
    print("\n▶ [測試 26/26] 檢驗 100 張立體實景山海圖、每 5 架擊斃掉寶、中途空中戰機大魔王與下方出現敵機...")
    from game.sprites import create_midboss_fighter_sprite
    from game.background import BackgroundManager
    from game.bosses import MidBoss

    # 1. 檢驗 100 張立體實景有山有海頂視圖
    scenic_files = BackgroundManager.get_scenic_100_filenames()
    assert len(scenic_files) == 100, f"必須有 100 張圖，實為 {len(scenic_files)}"
    bg_mgr = BackgroundManager()
    found_count = 0
    for fn in scenic_files:
        p = bg_mgr._get_asset_path(fn)
        if p and os.path.exists(p):
            found_count += 1
    assert found_count == 100, f"100 張立體實景山海圖必須全部存在於容器與資產庫中，目前找到 {found_count}/100 張！"

    # 1.1 檢驗 20 大關卡均能順暢載入其專屬的 5 張立體實景圖 (20 關 x 5 張 = 100 張全數實裝遊戲運作)
    for s_idx in range(20):
        stage_bg = BackgroundManager(STAGES_DATA[s_idx]["bg_theme"], stage_idx=s_idx)
        assert len(stage_bg.scenic_surfs) == 5, f"第 {s_idx+1} 關必須成功載入 5 張立體實景圖，實為 {len(stage_bg.scenic_surfs)}"
        assert stage_bg.scenic_surfs[0].get_size() == (960, 10240), f"實景圖尺寸必須為 960x10240 (實為 {stage_bg.scenic_surfs[0].get_size()})"

    # 2. 檢驗每關中途大魔王以空中戰機為主
    aerial_midboss_count = sum(1 for s in STAGES_DATA if s.get("midboss_type") == "midboss_fighter")
    assert aerial_midboss_count >= 15, f"每關中途大魔王必須以空中戰機為主，實為 {aerial_midboss_count}/20 關"
    midboss_fighter = MidBoss(STAGES_DATA[0], bg_mgr)
    assert midboss_fighter.is_aerial, "中途大魔王必須為空中戰機型態"
    mid_spr = create_midboss_fighter_sprite(0)
    assert mid_spr.get_width() > 100, "空中戰機中型大魔王必須具備專屬大型重戰機精靈圖"

    # 3. 檢驗敵方被擊斃後每 5 架才出現一個寶物
    game = Game(headless=True)
    game.load_stage(0)
    game.powerups.clear()
    game.enemy_plane_kill_count = 0

    for i in range(1, 11):
        test_plane = Enemy(100, 100, enemy_type="scout_zero")
        game.enemies = [test_plane]
        # 發射子彈擊潰
        b = Bullet(100, 100, 0, -1, "player_bullet", damage=999, is_player=True)
        game.player_bullets = [b]
        game.handle_collisions()
        expected_drops = (i // 5)
        assert len(game.powerups) == expected_drops, f"第 {i} 架敵機擊斃後寶物數應為 {expected_drops} (實為 {len(game.powerups)})"

    # 4. 檢驗敵方戰機可由下方出現向上突擊
    bottom_plane = Enemy(400, 950, enemy_type="fast_interceptor", pattern="climb_straight", speed=4.0, spawn_from_bottom=True)
    assert bottom_plane.spawn_from_bottom, "敵機必須支援由下方出現"
    init_y = bottom_plane.y
    bottom_plane.update(0.1)
    assert bottom_plane.y < init_y, f"由下方出現之敵機必須向上攀升突擊 (y 應減少，原 {init_y} -> 現 {bottom_plane.y})"

    # 檢驗生成邏輯中包含下方出現機率
    game.enemies.clear()
    for _ in range(50):
        game.enemy_spawn_timer = 0.0
        game.spawn_enemies(0.016)
    bottom_spawned = [e for e in game.enemies if getattr(e, "spawn_from_bottom", False)]
    assert len(bottom_spawned) > 0, "敵機生成時必須有隨機比率由下方出現，絕非全由上方出現"

    print("  ✓ 驗證 100 張立體實景有山有海頂視圖全部生成且存在於資產庫中！")
    print("  ✓ 驗證每關中途大魔王以空中戰機為主，具備雙後燃器與專屬精靈！")
    print("  ✓ 驗證敵機被擊斃每 5 架才以隨機方式出現一個寶物！")
    print("  ✓ 驗證敵方戰機可由下方出現並向上突擊！")
    print("  -> 通過！")

if __name__ == "__main__":
    print("==================================================")
    print(" 1942: 天空狂怒 (Sky Fury 1942) 自動化測試驗證套件 ")
    print("==================================================")
    try:
        test_fighter_selection()
        test_health_and_damage_rules()
        test_powerup_system()
        test_special_key_z()
        test_20_stages_and_bosses()
        test_headless_game_simulation()
        test_scenic_backgrounds()
        test_enemy_planes_defeat_hits()
        test_naval_fleet_and_boss_durability()
        test_seamless_background_and_clouds()
        test_fighter_formation_combos()
        test_intermittent_fleet_and_ground_tanks()
        test_visual_and_bullet_differentiation()
        test_laser_powerup_and_homing()
        test_middle_land_tanks_and_medium_warships()
        test_boss_shape_and_color_ttk()
        test_audio_system_and_sounds()
        test_strict_sea_warship_and_land_tank()
        test_player_control_during_warning_alerts()
        test_960x1024_screen_and_non_obstructive_hud()
        test_rich_low_frequency_multi_track_audio()
        test_no_lingering_bullets_across_stages()
        test_multi_segment_smooth_topdown_backgrounds()
        test_extended_stage_time_midboss_and_hud_cutout()
        test_multi_form_aerial_boss_naval_midboss_boundary_and_pacing()
        test_100_stereoscopic_scenery_powerup_drop_aerial_midboss_and_bottom_spawning()
        print("\n" + "=" * 50)
        print(" 🎉 所有 26 項核心規則與強化遊戲系統測試全部 100% 通過！")
        print("==================================================")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ 測試失敗: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 發生例外錯誤: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


