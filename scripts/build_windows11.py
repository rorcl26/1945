#!/usr/bin/env python3
"""
1945: 二戰空間（II War Space）
Windows 11 x64 獨立免安裝可執行版建置工具 (Windows 11 Native Portable Executable Builder)

功能：
1. 生成高解析度多尺寸 Windows 圖示 (assets/icon.ico)
2. 透過 MinGW-w64 交叉編譯原生 64-bit Windows GUI 啟動器 (1945-II-WarSpace.exe)
   - 內嵌 Windows 11 Per-Monitor V2 高 DPI 感知清單 (Manifest) 與 UTF-8 支援
   - 內嵌遊戲專屬戰機圖示與版本資訊
   - 支援完整 Unicode 路徑（含中文資料夾路徑）與命令列參數轉發
3. 整合官方 Python 3.12 Windows Embeddable Runtime (win_amd64)
   + Pygame 2.6.1 (win_amd64, 含 SDL2 完整 DLL) + NumPy (win_amd64)
4. 封裝全套 100 張山海實景長卷、程序化音頻引擎與繁體中文字型 (wqy-microhei.ttc)
5. 產出可直接於 Windows 11 雙擊執行的資料夾與獨立壓縮包 II-WarSpace-1945-Win11-x64.zip
"""

import os
import sys
import shutil
import struct
import zlib
import zipfile
import subprocess

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = "/tmp/win_build_cache"
RELEASE_BASE = os.path.join(PROJECT_ROOT, "Windows11_Release")
DIST_DIR = os.path.join(RELEASE_BASE, "1945-II-WarSpace-Win11-x64")
ZIP_OUTPUT = os.path.join(PROJECT_ROOT, "II-WarSpace-1945-Win11-x64.zip")


def create_png_bytes(width, height, rgba_func):
    """生成純淨 RGBA PNG 二進位資料 (不依賴外部繪圖庫)"""
    raw_rows = []
    for y in range(height):
        row = bytearray([0])  # Filter type 0 (None)
        for x in range(width):
            r, g, b, a = rgba_func(x, y, width, height)
            row.extend((r, g, b, a))
        raw_rows.append(bytes(row))
    raw_data = b"".join(raw_rows)

    def make_chunk(chunk_type, data):
        chunk = struct.pack(">I", len(data)) + chunk_type + data
        crc = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
        return chunk + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    idat = zlib.compress(raw_data, 9)
    return (
        b"\x89PNG\r\n\x1a\n"
        + make_chunk(b"IHDR", ihdr)
        + make_chunk(b"IDAT", idat)
        + make_chunk(b"IEND", b"")
    )


def draw_fighter_icon_pixel(x, y, w, h):
    """繪製 1945 P-38 閃電戰機與金色徽章圖示像素"""
    nx = (x + 0.5) / w * 2.0 - 1.0
    ny = (y + 0.5) / h * 2.0 - 1.0
    dist = (nx * nx + ny * ny) ** 0.5

    # 外圈圓角徽章背景
    if dist > 0.95:
        return (0, 0, 0, 0)
    if dist > 0.86:
        # 金色金屬外框
        return (245, 200, 45, 255)

    # 深海藍漸層底色
    bg_r = int(12 + 15 * (1.0 - (ny + 1.0) * 0.5))
    bg_g = int(28 + 38 * (1.0 - (ny + 1.0) * 0.5))
    bg_b = int(68 + 65 * (1.0 - (ny + 1.0) * 0.5))

    ax = abs(nx)

    # 主翼 (水平展開略帶後掠)
    wing_top = -0.15 + ax * 0.18
    wing_bot = 0.12 + ax * 0.12
    in_main_wing = (ax < 0.78) and (wing_top <= ny <= wing_bot)

    # 雙尾椼 (Twin Booms of P-38)
    in_boom = (0.24 <= ax <= 0.36) and (-0.25 <= ny <= 0.58)

    # 水平尾翼
    in_tail = (ax <= 0.44) and (0.46 <= ny <= 0.60)

    # 中央座艙與機鼻
    in_fuselage = (ax <= 0.13 * (1.0 - max(0.0, (-ny - 0.15) * 1.4))) and (-0.68 <= ny <= 0.25)
    in_canopy = (ax <= 0.08) and (-0.22 <= ny <= 0.06)

    # 雙螺旋槳高光
    in_prop = (0.20 <= ax <= 0.40) and (-0.32 <= ny <= -0.24)

    # 雙發機砲火光
    in_laser = (ax <= 0.05) and (-0.84 <= ny < -0.66)

    if in_laser:
        return (80, 245, 255, 255)
    if in_canopy:
        return (90, 230, 255, 255)
    if in_prop:
        return (255, 235, 110, 255)
    if in_fuselage or in_boom or in_tail or in_main_wing:
        # 機翼兩端金色識別條紋
        if in_main_wing and (0.52 <= ax <= 0.66):
            return (255, 210, 40, 255)
        # 鋼鐵亮藍機身
        shade = 1.0 - ax * 0.25
        return (
            min(255, int(85 * shade + 25)),
            min(255, int(155 * shade + 30)),
            min(255, int(225 * shade + 30)),
            255,
        )

    return (bg_r, bg_g, bg_b, 255)


def generate_ico_file(ico_path):
    """生成標準多尺寸 Windows ICO 圖示檔 (64x64, 48x48, 32x32, 16x16)"""
    sizes = [64, 48, 32, 16]
    png_blobs = [create_png_bytes(s, s, draw_fighter_icon_pixel) for s in sizes]

    header = struct.pack("<HHH", 0, 1, len(sizes))
    offset = 6 + 16 * len(sizes)
    entries = []
    for s, blob in zip(sizes, png_blobs):
        w_byte = 0 if s >= 256 else s
        h_byte = 0 if s >= 256 else s
        entry = struct.pack(
            "<BBBBHHII",
            w_byte,
            h_byte,
            0,
            0,
            1,
            32,
            len(blob),
            offset,
        )
        entries.append(entry)
        offset += len(blob)

    os.makedirs(os.path.dirname(ico_path), exist_ok=True)
    with open(ico_path, "wb") as f:
        f.write(header)
        for e in entries:
            f.write(e)
        for b in png_blobs:
            f.write(b)
    print(f"✓ 已生成 Windows 11 圖示: {ico_path} ({os.path.getsize(ico_path)} bytes)")


LAUNCHER_C_CODE = r"""
#ifndef UNICODE
#define UNICODE
#endif
#ifndef _UNICODE
#define _UNICODE
#endif
#include <windows.h>
#include <stdio.h>
#include <wchar.h>

static int has_console_flag(const wchar_t *cmd) {
    if (!cmd) return 0;
    if (wcsstr(cmd, L"--test") || wcsstr(cmd, L"--help") || wcsstr(cmd, L"-h") || wcsstr(cmd, L"--frames")) {
        return 1;
    }
    return 0;
}

static int file_exists(const wchar_t *path) {
    DWORD attr = GetFileAttributesW(path);
    return (attr != INVALID_FILE_ATTRIBUTES && !(attr & FILE_ATTRIBUTE_DIRECTORY));
}

int WINAPI wWinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, PWSTR lpCmdLine, int nCmdShow) {
    (void)hInstance;
    (void)hPrevInstance;
    (void)nCmdShow;

    wchar_t exe_path[MAX_PATH * 4];
    DWORD len = GetModuleFileNameW(NULL, exe_path, MAX_PATH * 4);
    if (len == 0) {
        MessageBoxW(NULL, L"無法取得執行檔路徑 (GetModuleFileNameW failed).", L"1945: 二戰空間", MB_ICONERROR);
        return 1;
    }

    // 取得所在目錄
    wchar_t base_dir[MAX_PATH * 4];
    wcscpy(base_dir, exe_path);
    wchar_t *last_slash = wcsrchr(base_dir, L'\\');
    if (last_slash) {
        *last_slash = L'\0';
    }

    SetCurrentDirectoryW(base_dir);
    SetEnvironmentVariableW(L"PYGAME_HIDE_SUPPORT_PROMPT", L"1");
    SetEnvironmentVariableW(L"PYTHONUTF8", L"1");
    SetEnvironmentVariableW(L"SDL_VIDEO_CENTERED", L"1");
    SetEnvironmentVariableW(L"SDL_IME_SHOW_UI", L"0");

    int console_mode = has_console_flag(lpCmdLine);
    if (console_mode) {
        if (!AttachConsole(ATTACH_PARENT_PROCESS)) {
            AllocConsole();
        }
        FILE *fp;
        _wfreopen_s(&fp, L"CONOUT$", L"w", stdout);
        _wfreopen_s(&fp, L"CONOUT$", L"w", stderr);
    }

    wchar_t py_exe[MAX_PATH * 4];
    if (console_mode) {
        _snwprintf(py_exe, MAX_PATH * 4, L"%s\\runtime\\python.exe", base_dir);
    } else {
        _snwprintf(py_exe, MAX_PATH * 4, L"%s\\runtime\\pythonw.exe", base_dir);
        if (!file_exists(py_exe)) {
            _snwprintf(py_exe, MAX_PATH * 4, L"%s\\runtime\\python.exe", base_dir);
        }
    }

    wchar_t main_script[MAX_PATH * 4];
    _snwprintf(main_script, MAX_PATH * 4, L"%s\\game\\main.py", base_dir);
    if (!file_exists(main_script)) {
        MessageBoxW(
            NULL,
            L"找不到遊戲主程式 game\\main.py！\n請確認壓縮包已完整解壓縮，且未將 .exe 單獨移出資料夾。",
            L"1945: 二戰空間（II War Space）",
            MB_ICONERROR | MB_OK
        );
        return 2;
    }

    wchar_t cmd_line[MAX_PATH * 8];
    if (file_exists(py_exe)) {
        if (lpCmdLine && lpCmdLine[0] != L'\0') {
            _snwprintf(cmd_line, MAX_PATH * 8, L"\"%s\" \"%s\" %s", py_exe, main_script, lpCmdLine);
        } else {
            _snwprintf(cmd_line, MAX_PATH * 8, L"\"%s\" \"%s\"", py_exe, main_script);
        }
    } else {
        // Fallback: 嘗試系統 Python
        const wchar_t *sys_py = console_mode ? L"python.exe" : L"pythonw.exe";
        if (lpCmdLine && lpCmdLine[0] != L'\0') {
            _snwprintf(cmd_line, MAX_PATH * 8, L"%s \"%s\" %s", sys_py, main_script, lpCmdLine);
        } else {
            _snwprintf(cmd_line, MAX_PATH * 8, L"%s \"%s\"", sys_py, main_script);
        }
    }

    STARTUPINFOW si;
    PROCESS_INFORMATION pi;
    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    ZeroMemory(&pi, sizeof(pi));

    DWORD flags = console_mode ? 0 : CREATE_NO_WINDOW;
    BOOL ok = CreateProcessW(
        NULL,
        cmd_line,
        NULL,
        NULL,
         console_mode ? TRUE : FALSE,
        flags,
        NULL,
        base_dir,
        &si,
        &pi
    );

    if (!ok) {
        MessageBoxW(
            NULL,
            L"無法啟動遊戲執行環境 (runtime\\pythonw.exe)！\n請確認 runtime 資料夾完整存在。",
            L"1945: 二戰空間（II War Space）",
            MB_ICONERROR | MB_OK
        );
        return 3;
    }

    WaitForSingleObject(pi.hProcess, INFINITE);
    DWORD exit_code = 0;
    GetExitCodeProcess(pi.hProcess, &exit_code);
    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);
    return (int)exit_code;
}
"""

APP_MANIFEST_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0" xmlns:asmv3="urn:schemas-microsoft-com:asm.v3">
  <assemblyIdentity version="1.0.0.0" processorArchitecture="amd64" name="IIWarSpace.1945.Game" type="win32"/>
  <description>1945: II War Space - Windows 11 Edition</description>
  <compatibility xmlns="urn:schemas-microsoft-com:compatibility.v1">
    <application>
      <!-- Windows 10 and Windows 11 -->
      <supportedOS Id="{8e0f7a12-bfb3-4fe8-b9a5-48fd50a15a9a}"/>
    </application>
  </compatibility>
  <asmv3:application>
    <asmv3:windowsSettings>
      <dpiAware xmlns="http://schemas.microsoft.com/SMI/2005/WindowsSettings">true/pm</dpiAware>
      <dpiAwareness xmlns="http://schemas.microsoft.com/SMI/2016/WindowsSettings">PerMonitorV2, PerMonitor</dpiAwareness>
      <activeCodePage xmlns="http://schemas.microsoft.com/SMI/2019/WindowsSettings">UTF-8</activeCodePage>
    </asmv3:windowsSettings>
  </asmv3:application>
</assembly>
"""

RESOURCE_RC = """#include <winuser.h>
1 ICON "icon.ico"
1 RT_MANIFEST "app.manifest"
"""


def compile_windows_exe(ico_path, output_exe_path):
    """使用 Alpine 容器中的 MinGW-w64 編譯原生 64-bit Windows GUI 執行檔"""
    build_tmp = os.path.join(CACHE_DIR, "exe_src")
    os.makedirs(build_tmp, exist_ok=True)

    shutil.copy2(ico_path, os.path.join(build_tmp, "icon.ico"))
    with open(os.path.join(build_tmp, "launcher.c"), "w", encoding="utf-8") as f:
        f.write(LAUNCHER_C_CODE)
    with open(os.path.join(build_tmp, "app.manifest"), "w", encoding="utf-8") as f:
        f.write(APP_MANIFEST_XML)
    with open(os.path.join(build_tmp, "resource.rc"), "w", encoding="utf-8") as f:
        f.write(RESOURCE_RC)

    cmd = [
        "docker", "run", "--rm",
        "-v", f"{build_tmp}:/src",
        "-w", "/src",
        "alpine:latest",
        "sh", "-c",
        (
            "apk add --no-cache mingw-w64-gcc >/dev/null && "
            "x86_64-w64-mingw32-windres resource.rc -O coff -o resource.res && "
            "x86_64-w64-mingw32-gcc -O2 -Wall -municode -mwindows "
            "launcher.c resource.res -o 1945-II-WarSpace.exe -s"
        ),
    ]
    subprocess.run(cmd, check=True)
    os.makedirs(os.path.dirname(output_exe_path), exist_ok=True)
    shutil.copy2(os.path.join(build_tmp, "1945-II-WarSpace.exe"), output_exe_path)
    print(f"✓ 已編譯原生 Windows 11 64-bit 執行檔: {output_exe_path} ({os.path.getsize(output_exe_path)} bytes)")


def ensure_cached_wheels():
    """確保 Windows 64-bit Python Embeddable 與 Pygame/NumPy Wheels 已下載至快取目錄"""
    import urllib.request
    import json
    os.makedirs(CACHE_DIR, exist_ok=True)
    py_url = "https://www.python.org/ftp/python/3.12.7/python-3.12.7-embed-amd64.zip"
    py_dest = os.path.join(CACHE_DIR, "python-3.12.7-embed-amd64.zip")
    if not os.path.exists(py_dest):
        print(f"  -> 下載 {py_url} ...")
        urllib.request.urlretrieve(py_url, py_dest)

    for pkg in ["pygame", "numpy"]:
        existing = [f for f in os.listdir(CACHE_DIR) if f.startswith(pkg + "-") and f.endswith(".whl")]
        if existing:
            continue
        req = urllib.request.urlopen(f"https://pypi.org/pypi/{pkg}/json")
        data = json.loads(req.read().decode("utf-8"))
        matched = []
        for v in reversed(list(data["releases"].keys())):
            matched = [
                u for u in data["releases"][v]
                if "cp312" in u["filename"] and "win_amd64" in u["filename"] and u["filename"].endswith(".whl")
            ]
            if matched:
                break
        u = matched[0]
        dest = os.path.join(CACHE_DIR, u["filename"])
        print(f"  -> 下載 {u['filename']} ...")
        urllib.request.urlretrieve(u["url"], dest)


def build_embedded_runtime(runtime_dir):
    """解壓並配置 Windows 11 64-bit Python Embeddable + Pygame + NumPy"""
    if os.path.exists(os.path.join(runtime_dir, "pythonw.exe")) and os.path.exists(
        os.path.join(runtime_dir, "Lib", "site-packages", "pygame")
    ):
        print(f"✓ 偵測到既有 Windows 11 內嵌執行環境，直接沿用: {runtime_dir}")
        return

    ensure_cached_wheels()
    if os.path.exists(runtime_dir):
        shutil.rmtree(runtime_dir)
    os.makedirs(runtime_dir, exist_ok=True)

    py_zip = os.path.join(CACHE_DIR, "python-3.12.7-embed-amd64.zip")
    with zipfile.ZipFile(py_zip, "r") as z:
        z.extractall(runtime_dir)

    site_packages = os.path.join(runtime_dir, "Lib", "site-packages")
    os.makedirs(site_packages, exist_ok=True)

    for fname in os.listdir(CACHE_DIR):
        if fname.endswith(".whl") and "win_amd64" in fname:
            whl_path = os.path.join(CACHE_DIR, fname)
            print(f"  -> 解壓縮 Windows 64-bit 套件: {fname}")
            with zipfile.ZipFile(whl_path, "r") as z:
                z.extractall(site_packages)

    # 配置 python312._pth 以載入上層專案目錄 (..) 與 Lib\site-packages
    pth_path = os.path.join(runtime_dir, "python312._pth")
    pth_content = "python312.zip\r\n.\r\n..\r\nLib\\site-packages\r\nimport site\r\n"
    with open(pth_path, "w", encoding="utf-8", newline="") as f:
        f.write(pth_content)

    print(f"✓ 已完成 Windows 11 內嵌執行環境配置: {runtime_dir}")


def write_crlf_file(path, content):
    """以 UTF-8 與 Windows CRLF 換行格式寫入批次檔或說明文件"""
    text = content.replace("\r\n", "\n").replace("\n", "\r\n")
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def create_windows_batch_and_docs(dist_dir):
    """建立 Windows 11 專用批次啟動腳本與使用說明"""
    bat_normal = """@echo off
chcp 65001 >nul
cd /d "%~dp0"
start "" "%~dp01945-II-WarSpace.exe" %*
"""
    bat_fullscreen = """@echo off
chcp 65001 >nul
cd /d "%~dp0"
start "" "%~dp01945-II-WarSpace.exe" --fullscreen %*
"""
    bat_2p = """@echo off
chcp 65001 >nul
cd /d "%~dp0"
start "" "%~dp01945-II-WarSpace.exe" --players 2 %*
"""
    bat_cpu = """@echo off
chcp 65001 >nul
cd /d "%~dp0"
start "" "%~dp01945-II-WarSpace.exe" --cpu-mode %*
"""
    bat_test = """@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================================
echo   1945: 二戰空間（II War Space）- Windows 11 自動化驗證測試
echo ============================================================
"%~dp0runtime\\python.exe" "%~dp0test_game.py"
echo.
pause
"""

    write_crlf_file(os.path.join(dist_dir, "啟動遊戲 (視窗模式).bat"), bat_normal)
    write_crlf_file(os.path.join(dist_dir, "啟動遊戲 (全螢幕模式).bat"), bat_fullscreen)
    write_crlf_file(os.path.join(dist_dir, "啟動遊戲 (雙人協同模式).bat"), bat_2p)
    write_crlf_file(os.path.join(dist_dir, "啟動遊戲 (CPU相容模式).bat"), bat_cpu)
    write_crlf_file(os.path.join(dist_dir, "執行自動驗證測試.bat"), bat_test)

    readme_win11 = """========================================================================
  1945: 二戰空間（II War Space） - Windows 11 (64-bit) 免安裝直接執行版
========================================================================

【快速啟動方式】
本版本已完整內嵌 Windows 11 64-bit 執行環境 (Python 3.12 + Pygame 2.6 SDL2
+ NumPy 音頻合成器 + 繁體中文字型 + 100 張山海立體實景圖資)，無須安裝 Python、
無須安裝 Docker 或任何第三方套件，解壓縮後即可直接執行：

  1. 直接雙擊 【1945-II-WarSpace.exe】 即可進入遊戲！
  2. 或雙擊以下快速啟動腳本：
     - 啟動遊戲 (視窗模式).bat      ：標準視窗模式（自動適應 Windows 11 螢幕比例與高 DPI）
     - 啟動遊戲 (全螢幕模式).bat    ：全螢幕沉浸模式（遊戲中亦可隨時按 F11 切換全螢幕）
     - 啟動遊戲 (雙人協同模式).bat  ：直接以雙人 1024x10240 寬屏模式啟動
     - 啟動遊戲 (CPU相容模式).bat   ：無獨立顯卡或虛擬機環境之軟體渲染相容模式
     - 執行自動驗證測試.bat         ：執行完整 26 項遊戲核心規則自動化測試

------------------------------------------------------------------------
【操作按鍵一覽】
  ◆ 1P 單人模式：
    - 移動：↑ ↓ ← → 方向鍵（或 W A S D）
    - 射擊：M 鍵 或 空白鍵 (Space)
    - 特技：Z 鍵（360度翻轉閃避 / 全防禦能量護盾）

  ◆ 2P 雙人協同作戰模式：
    - 第一人 (P1)：↑ ↓ ← → 方向鍵移動 · M 鍵射擊 · Z 鍵特技
    - 第二人 (P2)：W(上) X(下) A(左) D(右) 移動 · V 鍵射擊 · C 鍵特技
    - 滿血補命復活：當任一玩家 5 條命耗盡陣亡時，按下 【Y 鍵】 立即補滿 5 命滿血復活！

  ◆ 系統熱鍵：
    - F11 鍵  ：隨時切換 視窗 / 全螢幕 模式
    - P 鍵    ：暫停 / 繼續遊戲
    - Enter 鍵：確認選單 / 過關或結束後重新開始
    - ESC 鍵  ：退出遊戲

------------------------------------------------------------------------
【命令列參數（進階）】
  1945-II-WarSpace.exe --fullscreen        # 全螢幕模式啟動
  1945-II-WarSpace.exe --players 2         # 雙人模式啟動
  1945-II-WarSpace.exe --stage 5           # 直接從第 5 關開始 (1~20)
  1945-II-WarSpace.exe --plane 1           # 預選第 2 款戰機 (0~3)
  1945-II-WarSpace.exe --cpu-mode          # 強制 CPU 軟體渲染模式
========================================================================
"""
    write_crlf_file(os.path.join(dist_dir, "README-Windows11.txt"), readme_win11)


def copy_game_files(dist_dir):
    """複製遊戲程式碼、100張實景背景圖、艦隊圖資與中文字型至發布目錄"""
    # 1. game/
    dst_game = os.path.join(dist_dir, "game")
    if os.path.exists(dst_game):
        shutil.rmtree(dst_game)
    shutil.copytree(
        os.path.join(PROJECT_ROOT, "game"),
        dst_game,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )

    # 2. assets/ (backgrounds, fleet, fonts, icon.ico)
    dst_assets = os.path.join(dist_dir, "assets")
    if os.path.exists(dst_assets):
        shutil.rmtree(dst_assets)
    os.makedirs(dst_assets, exist_ok=True)

    for sub in ["backgrounds", "fleet", "fonts"]:
        src_sub = os.path.join(PROJECT_ROOT, "assets", sub)
        if os.path.exists(src_sub):
            shutil.copytree(
                src_sub,
                os.path.join(dst_assets, sub),
                ignore=shutil.ignore_patterns("previews", "gallery.html"),
            )

    shutil.copy2(
        os.path.join(PROJECT_ROOT, "assets", "icon.ico"),
        os.path.join(dst_assets, "icon.ico"),
    )

    # 3. test_game.py & README.md
    shutil.copy2(os.path.join(PROJECT_ROOT, "test_game.py"), os.path.join(dist_dir, "test_game.py"))
    shutil.copy2(os.path.join(PROJECT_ROOT, "README.md"), os.path.join(dist_dir, "README.md"))


def package_zip(dist_dir, zip_path):
    """將 Windows 11 可執行版本打包為標準 ZIP 壓縮檔"""
    if os.path.exists(zip_path):
        os.remove(zip_path)
    parent_dir = os.path.dirname(dist_dir)
    print(f"▶ 正在封裝 Windows 11 獨立壓縮包: {zip_path} ...")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for root, _, files in os.walk(dist_dir):
            for file in files:
                abs_p = os.path.join(root, file)
                rel_p = os.path.relpath(abs_p, parent_dir)
                zf.write(abs_p, rel_p)
    size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    print(f"✓ 封裝完成: {zip_path} ({size_mb:.2f} MB)")


def main():
    os.makedirs(DIST_DIR, exist_ok=True)
    ico_path = os.path.join(PROJECT_ROOT, "assets", "icon.ico")
    generate_ico_file(ico_path)

    exe_path = os.path.join(DIST_DIR, "1945-II-WarSpace.exe")
    compile_windows_exe(ico_path, exe_path)

    runtime_dir = os.path.join(DIST_DIR, "runtime")
    build_embedded_runtime(runtime_dir)

    copy_game_files(DIST_DIR)
    create_windows_batch_and_docs(DIST_DIR)
    package_zip(DIST_DIR, ZIP_OUTPUT)
    print("\n🎉 Windows 11 可直接執行版本建置完成！")


if __name__ == "__main__":
    main()

