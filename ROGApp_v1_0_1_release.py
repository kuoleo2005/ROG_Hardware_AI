import customtkinter as ctk
import psutil
import GPUtil
import cpuinfo
import multiprocessing
import requests
import threading
import subprocess
import re
import time
import urllib.parse
import os
import json
import webbrowser
import tkinter as tk
import difflib
import math
import textwrap
0

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class StatusTextbox(ctk.CTkTextbox):
    """可複製的狀態輸出框；相容原本 Label 的 configure(text=..., text_color=...) 寫法。"""
    def __init__(self, *args, **kwargs):
        initial_text = kwargs.pop("text", "")
        super().__init__(*args, **kwargs)
        self._text_color = kwargs.get("text_color", "#ffffff")
        self.insert("end", initial_text)
        self.configure(state="disabled")

    def configure(self, **kwargs):
        text = kwargs.pop("text", None)
        text_color = kwargs.pop("text_color", None)
        if text_color is not None:
            kwargs["text_color"] = text_color
        super().configure(**kwargs)
        if text is not None:
            super().configure(state="normal")
            self.delete("1.0", "end")
            self.insert("end", text)
            super().configure(state="disabled")

    config = configure

# ==========================================
# 1. 硬體數據庫 (Database)
# ==========================================
UPGRADE_DB = {
    "SSD_GEN4": ["256GB", "512GB", "1TB", "2TB", "4TB", "8TB"],
    "SSD_GEN5": ["512GB", "1TB", "2TB", "4TB", "8TB"],
    "SSD_SATA": ["500GB", "1TB", "2TB", "4TB", "8TB"],
    "RAM_CAPACITY": ["8G", "16G", "24G", "32G", "48G", "64G", "96G", "128G", "192G"]
}

PC_BUILD_DB = {
    "CPU": {
        "Intel": {
            "LGA1851": [
                "Core Ultra 9 285K", "Core Ultra 7 265K", "Core Ultra 7 265KF", "Core Ultra 5 245K", "Core Ultra 5 245KF",
                "Core Ultra 9 285", "Core Ultra 7 265", "Core Ultra 5 245"
            ],
            "LGA1700": [
                "Core i9-14900K", "Core i9-14900KF", "Core i9-14900", "Core i7-14700K", "Core i7-14700KF", "Core i7-14700",
                "Core i5-14600K", "Core i5-14600KF", "Core i5-14500", "Core i5-14400F", "Core i5-13400F", "Core i3-14100F"
            ]
        },
        "AMD": {
            "AM5": [
                "Ryzen 9 9950X", "Ryzen 9 9950X3D", "Ryzen 9 9900X", "Ryzen 7 9800X3D", "Ryzen 7 9700X",
                "Ryzen 7 7800X3D", "Ryzen 7 7700", "Ryzen 5 9600X", "Ryzen 5 7600X", "Ryzen 5 7500F"
            ],
            "AM4": [
                "Ryzen 7 5700X3D", "Ryzen 7 5800X", "Ryzen 5 5600X", "Ryzen 5 5600", "Ryzen 5 5500"
            ]
        }
    },
    "MOBO": {
        "LGA1851": [
            "[ASUS] ROG MAXIMUS Z890 HERO (DDR5)", "[ASUS] ROG STRIX Z890-E GAMING WIFI (DDR5)", "[ASUS] ROG STRIX Z890-A GAMING WIFI (DDR5)",
            "[ASUS] TUF GAMING Z890-PLUS WIFI (DDR5)", "[MSI] MEG Z890 ACE (DDR5)", "[MSI] MPG Z890 EDGE TI WIFI (DDR5)",
            "[GIGABYTE] Z890 AORUS MASTER (DDR5)", "[GIGABYTE] Z890 AORUS ELITE WIFI7 (DDR5)"
        ],
        "LGA1700": [
            "[ASUS] ROG MAXIMUS Z790 HERO (DDR5)", "[ASUS] ROG STRIX Z790-E GAMING WIFI II (DDR5)", "[ASUS] TUF GAMING Z790-PLUS WIFI (DDR5)",
            "[ASUS] TUF GAMING B760M-PLUS WIFI (DDR5)", "[ASUS] TUF GAMING B760M-E D4 (DDR4)", "[MSI] MAG Z790 TOMAHAWK WIFI (DDR5)",
            "[MSI] B760M MORTAR WIFI II (DDR5)", "[GIGABYTE] Z790 AORUS MASTER (DDR5)", "[GIGABYTE] B760M AORUS ELITE AX (DDR5)"
        ],
        "AM5": [
            "[ASUS] ROG CROSSHAIR X870E HERO (DDR5)", "[ASUS] ROG STRIX X870E-E GAMING WIFI (DDR5)", "[ASUS] ROG STRIX B850-F GAMING WIFI (DDR5)",
            "[ASUS] ROG STRIX B650-A GAMING WIFI (DDR5)", "[ASUS] TUF GAMING B650-PLUS WIFI (DDR5)", "[MSI] MAG X870 TOMAHAWK WIFI (DDR5)",
            "[MSI] MAG B650 TOMAHAWK WIFI (DDR5)", "[GIGABYTE] X870E AORUS MASTER (DDR5)", "[GIGABYTE] B650 AORUS ELITE AX (DDR5)"
        ],
        "AM4": [
            "[ASUS] ROG STRIX B550-F GAMING WIFI II (DDR4)", "[ASUS] TUF GAMING B550M-PLUS WIFI II (DDR4)",
            "[MSI] MAG B550 TOMAHAWK MAX WIFI (DDR4)", "[GIGABYTE] B550 AORUS ELITE V2 (DDR4)"
        ]
    },
    "GPU": [
        "ASUS ROG Astral RTX 5090 32G", "ASUS TUF RTX 5090 32G", "MSI RTX 5090 SUPRIM 32G", "GIGABYTE RTX 5090 AORUS MASTER 32G",
        "ASUS ROG Astral RTX 5080 16G", "ASUS TUF RTX 5080 16G", "MSI RTX 5080 SUPRIM 16G", "GIGABYTE RTX 5080 GAMING OC 16G",
        "ASUS TUF RTX 5070 Ti 16G", "MSI RTX 5070 Ti GAMING TRIO 16G", "GIGABYTE RTX 5070 Ti AERO OC 16G",
        "ASUS DUAL RTX 5070 12G", "MSI RTX 5070 VENTUS 12G", "GIGABYTE RTX 5070 WINDFORCE 12G",
        "RTX 5060 Ti 16G", "RTX 5060 Ti 8G", "RTX 5060 8G", "RTX 5050 8G",
        "ASUS ROG STRIX RTX 4090 24G", "ASUS TUF RTX 4080 SUPER 16G", "MSI RTX 4070 Ti SUPER 16G", "GIGABYTE RTX 4070 SUPER 12G",
        "RTX 4060 Ti 16G", "RTX 4060 8G", "RTX 3060 12G", "RX 7900 XTX", "RX 7900 XT", "RX 7800 XT", "RX 7600 XT"
    ],
    "COOLER": [
        "ROG Ryujin III 360 ARGB 水冷", "ROG Strix LC III 360 ARGB 水冷", "NZXT Kraken Elite 360 RGB 水冷", "Corsair iCUE H150i Elite 水冷",
        "MSI MAG CORELIQUID E360 水冷", "DeepCool LT720 水冷", "貓頭鷹 NH-D15 G2 雙塔風冷", "利民 Phantom Spirit 120 EVO 風冷",
        "利民 Peerless Assassin 120 SE 風冷", "原廠散熱器"
    ],
    "PSU": [
        "ROG THOR 1600W Titanium", "ROG THOR 1200W Platinum II", "ROG STRIX 1000W Gold Aura", "海韻 PRIME TX-1300 Titanium",
        "海韻 VERTEX GX-1000 Gold", "Corsair RM1200x SHIFT Gold", "Corsair RM1000x Gold", "FSP Hydro G Pro 1000W Gold",
        "MSI MPG A850G PCIE5 850W Gold", "be quiet! Pure Power 12 M 850W", "台達 750W 金牌", "650W 銅牌"
    ],
    "CASE": [
        "ROG Hyperion GR701", "ROG Strix Helios", "Fractal Design North XL", "Lian Li O11 Dynamic EVO RGB", "NZXT H9 Flow",
        "Corsair 5000D Airflow", "Montech KING 95 PRO", "酷碼 TD500 Mesh V2", "聯力 LANCOOL 216", "不需要機殼"
    ],
    "MONITOR": {
        "ASUS ROG": ["ROG Swift OLED PG27AQDM 27吋 2K 240Hz", "ROG Swift OLED PG32UCDM 32吋 4K 240Hz", "ROG Strix XG27ACS 27吋 2K 180Hz", "ROG Strix XG32UQ 32吋 4K 160Hz"],
        "ASUS TUF": ["TUF Gaming VG27AQ3A 27吋 2K 180Hz", "TUF Gaming VG28UQL1A 28吋 4K 144Hz", "TUF Gaming VG249QM1A 24吋 1080p 270Hz"],
        "MSI": ["MSI MAG 274QRF QD E2 27吋 2K 180Hz", "MSI MAG 321UPX QD-OLED 32吋 4K 240Hz", "MSI G274F 27吋 1080p 180Hz"],
        "BenQ": ["BenQ MOBIUZ EX2710Q 27吋 2K 165Hz", "BenQ MOBIUZ EX3210U 32吋 4K 144Hz", "BenQ ZOWIE XL2566K 24.5吋 360Hz"],
        "GIGABYTE": ["GIGABYTE M27Q 27吋 2K 170Hz", "GIGABYTE M32U 32吋 4K 144Hz", "AORUS FO32U2 32吋 4K OLED 240Hz"],
        "LG": ["LG UltraGear 27GR95QE 27吋 OLED 240Hz", "LG UltraGear 32GQ950 32吋 4K 144Hz", "LG 34GS95QE 34吋 OLED 240Hz"],
        "Samsung": ["Samsung Odyssey OLED G8 32吋 4K 240Hz", "Samsung Odyssey G7 32吋 2K 240Hz", "Samsung Odyssey Neo G9 49吋"],
        "Acer Predator": ["Predator XB273U 27吋 2K 240Hz", "Predator X32Q FS 32吋 4K 144Hz", "Nitro XV272U 27吋 2K 180Hz"]
    },
    "EXTRA": [
        "不需要附加商品",
        "Windows 11 家用彩盒版", "Windows 11 專業彩盒版",
        "4TB HDD 3.5吋傳統硬碟", "8TB HDD 3.5吋傳統硬碟", "16TB HDD 3.5吋傳統硬碟",
        "Wi-Fi 7 PCIe 無線網卡", "2.5GbE PCIe 網卡", "USB-C 擴充卡",
        "ROG 顯卡支撐架", "Lian Li Strimer RGB 延長線", "ARGB 風扇 3入組",
        "外接式 DVD 光碟機", "外接式藍光燒錄機",
        "Logitech G Pro X Superlight 2 滑鼠", "Razer Viper V3 Pro 滑鼠", "ROG Harpe Ace 滑鼠",
        "Logitech G Pro X TKL 鍵盤", "Razer BlackWidow V4 鍵盤", "ROG Azoth 鍵盤",
        "HyperX Cloud III 耳機", "SteelSeries Arctis Nova 7 耳機", "ROG Delta II 耳機",
        "Elgato Stream Deck", "Elgato HD60 X 擷取卡", "Blue Yeti 麥克風",
        "APC 1000VA UPS 不斷電系統", "羅技 Brio 4K 網路攝影機", "筆電散熱墊"
    ]
}


# 額外擴充：讓選項更接近原價屋估價系統的零組件覆蓋率。
PC_BUILD_DB["CPU"]["Intel"]["LGA1851"].extend([
    "Core Ultra 9 285KS", "Core Ultra 7 265F", "Core Ultra 5 235", "Core Ultra 5 225F"
])
PC_BUILD_DB["CPU"]["Intel"]["LGA1700"].extend([
    "Core i9-13900K", "Core i9-13900KF", "Core i7-13700K", "Core i7-13700F",
    "Core i5-13600K", "Core i5-13500", "Core i5-12400F", "Core i3-13100F"
])
PC_BUILD_DB["CPU"]["AMD"]["AM5"].extend([
    "Ryzen 9 7900X", "Ryzen 9 7900", "Ryzen 7 7700X", "Ryzen 5 9600", "Ryzen 5 7600", "Ryzen 5 8400F", "Ryzen 5 8500G", "Ryzen 7 8700G"
])
PC_BUILD_DB["CPU"]["AMD"]["AM4"].extend([
    "Ryzen 9 5900X", "Ryzen 7 5700X", "Ryzen 5 5600G", "Ryzen 5 4600G"
])
PC_BUILD_DB["GPU"].extend([
    "ASUS PRIME RTX 5070 Ti 16G", "MSI RTX 5070 Ti VENTUS 3X 16G", "ZOTAC RTX 5070 Ti SOLID 16G",
    "ASUS PRIME RTX 5070 12G", "ZOTAC RTX 5070 SOLID 12G", "INNO3D RTX 5070 TWIN X2 12G",
    "ASUS DUAL RTX 5060 Ti 16G", "MSI RTX 5060 Ti VENTUS 2X 16G", "GIGABYTE RTX 5060 Ti WINDFORCE 16G",
    "ASUS DUAL RTX 4060 EVO 8G", "MSI RTX 4060 VENTUS 2X 8G", "GIGABYTE RTX 4060 WINDFORCE OC 8G",
    "SAPPHIRE RX 9070 XT 16G", "ASUS TUF RX 9070 XT 16G", "SAPPHIRE RX 9060 XT 16G",
    "RX 7900 GRE", "RX 7700 XT", "RX 7600", "Intel Arc B580 12G", "Intel Arc A770 16G"
])
PC_BUILD_DB["COOLER"].extend([
    "Arctic Liquid Freezer III 360 水冷", "Lian Li Galahad II Trinity 360 水冷",
    "be quiet! Dark Rock Pro 5 風冷", "DeepCool AK620 風冷", "Thermalright Assassin X 120 風冷"
])
PC_BUILD_DB["PSU"].extend([
    "海韻 FOCUS GX-850 ATX3.0 Gold", "海韻 FOCUS GX-750 Gold", "Corsair RM850e ATX3.0 Gold",
    "FSP VITA GM 850W Gold", "Antec NE1000G M ATX3.0 Gold", "MSI MAG A750GL PCIE5 750W Gold",
    "be quiet! Straight Power 12 1000W Platinum", "酷碼 MWE Gold V3 850W"
])
PC_BUILD_DB["CASE"].extend([
    "Fractal Design Meshify 2", "Fractal Design Pop Air", "Lian Li LANCOOL III", "Lian Li A3-mATX",
    "NZXT H6 Flow", "Corsair 4000D Airflow", "Montech AIR 903 MAX", "Montech XR",
    "Antec C8", "be quiet! Shadow Base 800", "酷碼 NR200P V2", "華碩 A21"
])
PC_BUILD_DB["MONITOR"].update({
    "AOC": ["AOC Q27G4 27吋 2K 180Hz", "AOC AGON PRO AG276QZD 27吋 OLED 240Hz", "AOC 24G4 24吋 180Hz"],
    "ViewSonic": ["ViewSonic VX2728J-2K 27吋 2K 180Hz", "ViewSonic XG2431 24吋 240Hz", "ViewSonic VX3219-4K 32吋 4K"],
    "Philips": ["Philips Evnia 27M2N8500 27吋 OLED", "Philips 27M2N5500 27吋 2K 180Hz"],
    "Dell": ["Dell Alienware AW2725DF 27吋 OLED 360Hz", "Dell G2724D 27吋 2K 165Hz", "Dell U2724D 27吋 2K IPS"],
    "Sony INZONE": ["Sony INZONE M10S 27吋 OLED 480Hz", "Sony INZONE M9 II 27吋 4K 160Hz"]
})
PC_BUILD_DB["EXTRA"].extend([
    "Intel AX210 Wi-Fi 6E PCIe 無線網卡", "TP-Link Archer TXE75E Wi-Fi 6E 網卡",
    "Samsung 990 PRO 2TB Gen4 SSD", "Crucial T705 2TB Gen5 SSD", "WD Black SN850X 2TB Gen4 SSD",
    "Logitech MX Master 3S 滑鼠", "Keychron Q1 HE 鍵盤", "Wooting 60HE+ 鍵盤", "SteelSeries Apex Pro TKL 鍵盤",
    "Razer DeathAdder V3 Pro 滑鼠", "Logitech G502 X PLUS 滑鼠", "Finalmouse UltralightX 滑鼠",
    "Shure MV7+ 麥克風", "Elgato Wave:3 麥克風", "Elgato 4K X 擷取卡",
    "Creative Sound Blaster X4 外接音效卡", "APC 1500VA UPS 不斷電系統", "CyberPower 1000VA UPS 不斷電系統",
    "Windows 11 家用隨機版", "Windows 11 專業隨機版", "Microsoft 365 個人版"
])


LAPTOP_BRANDS = [
    "ASUS ROG 玩家共和國", "ASUS TUF Gaming", "ASUS ProArt 創作者", "MSI 微星", "Acer Predator 掠奪者",
    "GIGABYTE AORUS", "Lenovo Legion", "HP OMEN", "DELL Alienware", "Razer Blade", "Acer Nitro", "ASUS Zenbook"
]
LAPTOP_GPUS = [
    "RTX 5090 頂規機皇", "RTX 5080 高階旗艦", "RTX 5070 Ti 效能本", "RTX 5070 主流高階", "RTX 5060 主流甜點",
    "RTX 4090 上代機皇", "RTX 4080 上代高階", "RTX 4070 上代主流", "RTX 4060 入門電競", "輕薄文書本 (無獨顯)", "創作者筆電 OLED"
]

LAPTOP_MODEL_DB = {
    "ASUS ROG 玩家共和國": ["ROG Strix SCAR 18", "ROG Strix SCAR 16", "ROG Strix G16", "ROG Strix G18", "ROG Zephyrus G14", "ROG Zephyrus G16", "ROG Flow Z13", "ROG Flow X16"],
    "ASUS TUF Gaming": ["TUF Gaming A14", "TUF Gaming A15", "TUF Gaming A16", "TUF Gaming F15", "TUF Gaming F16", "TUF Gaming F17"],
    "ASUS ProArt 創作者": ["ProArt P16", "ProArt PX13", "ProArt Studiobook 16 OLED", "ProArt PZ13"],
    "MSI 微星": ["MSI Titan 18 HX", "MSI Raider 18 HX", "MSI Vector 16 HX", "MSI Stealth 16 AI Studio", "MSI Cyborg 15", "MSI Katana 15"],
    "Acer Predator 掠奪者": ["Acer Predator Helios 18", "Acer Predator Helios 16", "Acer Predator Triton 14", "Acer Predator Triton Neo 16"],
    "GIGABYTE AORUS": ["AORUS MASTER 18", "AORUS MASTER 16", "AORUS 16X", "GIGABYTE G6X", "GIGABYTE AERO 16 OLED"],
    "Lenovo Legion": ["Lenovo Legion Pro 7i", "Lenovo Legion Pro 5i", "Lenovo Legion 7i", "Lenovo Legion 5i", "Lenovo LOQ 15"],
    "HP OMEN": ["HP OMEN Transcend 16", "HP OMEN 17", "HP OMEN 16", "HP Victus 16"],
    "DELL Alienware": ["Alienware m18", "Alienware m16", "Alienware x16", "Alienware Area-51m"],
    "Razer Blade": ["Razer Blade 18", "Razer Blade 16", "Razer Blade 14"],
    "Acer Nitro": ["Acer Nitro V 15", "Acer Nitro 16", "Acer Nitro 17"],
    "ASUS Zenbook": ["Zenbook Pro 16X OLED", "Zenbook S 16 OLED", "Zenbook 14 OLED", "Vivobook Pro 16X OLED"]
}

def extract_gpu_label(gpu_tier):
    """把「RTX 5070 Ti 效能本」轉成真正可查價的 RTX 5070 Ti，避免只剩 RTX。"""
    text = gpu_tier or ""
    m = re.search(r'RTX\s?\d{4}\s?Ti|RTX\s?\d{4}', text, flags=re.I)
    if m:
        return re.sub(r'\s+', ' ', m.group(0).upper()).replace('TI', 'Ti')
    if "創作者" in text:
        return "OLED Creator"
    if "輕薄" in text or "無獨顯" in text:
        return "Intel Core Ultra"
    return text.split(" ")[0] if text else ""

def get_laptop_models(brand, gpu_tier):
    gpu = extract_gpu_label(gpu_tier)
    base_models = LAPTOP_MODEL_DB.get(brand, [f"{brand.split(' ')[0]} 旗艦電競特仕版", f"{brand.split(' ')[0]} 效能主流機"])
    return [f"{model} - {gpu}" for model in base_models]

def clean_display_name(text):
    return text.replace("[ASUS]", "ASUS").replace("[MSI]", "MSI").replace("[GIGABYTE]", "GIGABYTE").strip()

def parse_budget(text):
    if not text:
        return None
    raw = text.replace(",", "").replace("，", "")
    m = re.search(r'(\d+(?:\.\d+)?)\s*(萬|k|K|千)?', raw)
    if not m:
        return None
    value = float(m.group(1))
    unit = m.group(2)
    if unit == "萬":
        value *= 10000
    elif unit in ["k", "K", "千"]:
        value *= 1000
    return int(value)

def local_ai_recommendation(user_text, specs):
    """無外部 AI 時的本機顧問；以回答問題為主，硬體資料只當背景。"""
    text = (user_text or "").lower()
    budget = parse_budget(user_text)
    is_laptop = specs.get('is_laptop', False)
    scores = calculate_score(specs)
    game = scores.get('GameGrade', 'F')
    prod = scores.get('ProductivityGrade', 'F')
    ram_txt = ram_label(specs.get('ram_total', 0))
    gpu = specs.get('gpu_name', '未知 GPU')
    cpu = specs.get('cpu_name', '未知 CPU')

    wants_laptop = any(k in text for k in ['筆電', 'notebook', 'laptop', '攜帶', '上課'])
    wants_desktop = any(k in text for k in ['桌機', '組', '主機', 'diy', '套裝'])
    wants_game = any(k in text for k in ['遊戲', 'gaming', '黑神話', '2077', '3a', '4k', '2k', 'fps', '傳說'])
    wants_ai = any(k in text for k in ['ai', 'llm', 'stable diffusion', '繪圖', '推論', '訓練', '模型'])
    wants_edit = any(k in text for k in ['剪輯', 'premiere', 'davinci', '影片', '直播', '創作'])
    wants_upgrade = any(k in text for k in ['升級', '加裝', '換', 'ssd', 'ram', '記憶體', '容量'])

    lines = ['🧠 AI 建議：']

    if budget:
        lines.append(f'以 NT$ {budget:,} 來看：')
        if budget >= 120000:
            lines.append('• 桌機優先：Ryzen 7 9800X3D / Ryzen 9 9950X3D + RTX 5080 / RTX 5090。')
            lines.append('• 若還要螢幕：建議 RTX 5080 + 2K OLED 240Hz；若只追極限 4K/AI 再上 RTX 5090。')
            lines.append('• 筆電：可看 RTX 5080 / RTX 5090 筆電，但同價位桌機效能通常更強。')
        elif budget >= 90000:
            lines.append('• 桌機甜點高階：Ryzen 7 9800X3D + RTX 5080，或 RTX 5070 Ti + 高階螢幕。')
            lines.append('• 筆電：RTX 5070 Ti / RTX 5080 機型較合理。')
        elif budget >= 60000:
            lines.append('• 桌機：Ryzen 7 7800X3D / 9700X + RTX 5070 / 5070 Ti。')
            lines.append('• 筆電：RTX 5070 級距；若重視 AI，優先選 VRAM 較大的款式。')
        elif budget >= 35000:
            lines.append('• 桌機：Ryzen 5 / Core i5 + RTX 5060 Ti / RTX 5070 入門。')
            lines.append('• 筆電：RTX 5060 / 5070；不要把預算全花在外觀。')
        else:
            lines.append('• 建議以局部升級 RAM / SSD 或二手/促銷機為主，不建議硬追旗艦。')
    elif wants_upgrade:
        if is_laptop:
            lines.append('你的裝置是筆電，優先檢查 RAM / SSD 可否加裝；CPU/GPU 通常不能換。')
            lines.append('• 最有感：SSD 擴到 1TB/2TB、RAM 補到 32G。')
            lines.append('• 若目標是 3A / AI 明顯提升，通常直接換 RTX 5070 Ti 以上筆電或桌機更有效。')
        else:
            lines.append('你的裝置是桌機，可分段升級：GPU > SSD/RAM > PSU > CPU/平台。')
            lines.append('• 換顯卡前先確認電供瓦數、PCIe 供電線、機殼長度。')
    elif wants_game or wants_ai or wants_edit:
        if wants_game and wants_ai:
            lines.append('遊戲 + AI 雙需求：優先買 NVIDIA GPU，VRAM 越大越好，其次 RAM 32G+。')
        elif wants_game:
            lines.append('遊戲需求：先看顯卡等級，再看螢幕解析度；2K 高刷比硬追 4K 更均衡。')
        elif wants_ai:
            lines.append('AI 需求：先看 NVIDIA GPU / VRAM；RAM 建議 32G 起跳，模型越大越吃 VRAM。')
        else:
            lines.append('剪輯/創作：CPU、RAM、SSD 容量與顯卡都重要；4K 剪輯建議 32G RAM + 2TB SSD。')
    else:
        lines.append('你可以直接輸入預算與用途，例如「10萬含螢幕遊戲桌機」或「5萬筆電剪輯上課」。')

    lines.append(f'目前硬體評價：遊戲 {game}｜生產力 {prod}｜AI {scores.get("AICalcGrade", "F")}｜綜合 {scores.get("OverallGrade", "F")}。')
    lines.append(short_hardware_verdict(specs, scores).replace('簡短評價：\n', ''))
    return "\n".join(lines)

def compact_specs_for_ai(specs):
    """把硬體資料壓成 AI 容易讀、也不會太長的摘要。"""
    scores = calculate_score(specs)
    disks = specs.get("disks", []) or []
    ram_modules = specs.get("ram_modules", []) or []
    return {
        "device_type": "筆電" if specs.get("is_laptop") else "桌機",
        "cpu": specs.get("cpu_name", "Unknown CPU"),
        "gpu": specs.get("gpu_name", "Unknown GPU"),
        "vram_mb": specs.get("gpu_vram", 0),
        "ram": ram_label(specs.get("ram_total", 0)),
        "ram_used_gb": specs.get("ram_used", 0),
        "ram_type": specs.get("ram_type", "未知"),
        "ram_modules": ram_modules[:8],
        "storage": disks[:8],
        "motherboard": specs.get("mobo", specs.get("baseboard", "未知")),
        "psu_note": specs.get("psu", "Windows 通常無法直接讀取電供瓦數"),
        "game_grade": scores.get("GameGrade", "F"),
        "productivity_grade": scores.get("ProductivityGrade", "F"),
        "ai_grade": scores.get("AICalcGrade", "F"),
        "overall_grade": scores.get("OverallGrade", "F"),
        "game_score_100": scores.get("game_score_100", 0),
        "productivity_score_100": scores.get("prod_score_100", 0),
        "ai_score_100": scores.get("ai_score_100", 0),
        "overall_score_100": scores.get("overall_score_100", 0),
    }



def build_ai_prompt(user_text, specs):
    compact = compact_specs_for_ai(specs)
    scores = calculate_score(specs)
    compact["short_verdict"] = short_hardware_verdict(specs, scores).replace("簡短評價:" + chr(10), "").replace("簡短評價：" + chr(10), "")
    compact["upgrade_hint"] = hardware_upgrade_suggestions(specs, scores)
    compact["limits"] = hardware_limit_flags(specs)
    compact["rating_logic"] = "遊戲=GPU/VRAM/解析度體感；生產力=CPU+RAM+SSD；AI=GPU+VRAM+RAM；綜合=前三項加權。"
    hardware_context = json.dumps(compact, ensure_ascii=False, indent=2)
    return f"""
你是台灣高階電競硬體架構師與採購顧問。請直接回答使用者真正的問題，硬體資料只是背景參考。
回答要白話、精準、像懂硬體的玩家，不要客服腔，不要只重複規格。

【判斷規則】
1. 必須參考硬體評級、short_verdict、upgrade_hint，前後不能矛盾。
2. 不要只看跑分；也要用玩家體感判斷解析度、畫質、光追、DLSS/FSR。
3. 筆電通常只能升級 RAM/SSD/清灰重上散熱膏；不要建議換筆電 CPU/GPU。
4. 若沒有獨顯、老 CPU/GPU、或整體分數很低：不要把 RAM/SSD 說成主要解法；要明確說 RAM/SSD 只能延命，想玩 3A/AI 應買新機/桌機。
5. 若使用者預算/需求很高，請直接給桌機/筆電取捨與查價關鍵字。
6. 不限制行數，但請控制在 1000 字內；重點式，主流好懂。

【建議格式】
💡 結論：
🎮 遊戲/🧠 AI剪輯：
🛠️ 建議方案：
🔑 查價關鍵字：

【目前硬體與評價】
{hardware_context}

【使用者問題】
{user_text or ''}
"""


def _call_gemini_ai(prompt):
    api_key = (
        os.getenv("GEMINI_API_KEY", "").strip()
        or os.getenv("GOOGLE_API_KEY", "").strip()
        or os.getenv("GOOGLE_AI_API_KEY", "").strip()
        or ""
    )
    if not api_key:
        raise RuntimeError("未設定 Gemini API Key")
    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}

    def clean_model_name(name):
        name = (name or "").strip()
        return name.split("/", 1)[1] if name.startswith("models/") else name

    def list_models(api_version):
        url = f"https://generativelanguage.googleapis.com/{api_version}/models"
        r = requests.get(url, headers=headers, timeout=(8, 25))
        if r.status_code in (401, 403):
            raise RuntimeError("Gemini API Key 無效、未啟用，或沒有 Gemini API 權限")
        if r.status_code == 429:
            raise RuntimeError("Gemini API 429：配額或速率限制，程式無法強制突破，請稍後或換專案/Key")
        r.raise_for_status()
        arr = []
        for m in r.json().get("models", []):
            name = clean_model_name(m.get("name", ""))
            methods = m.get("supportedGenerationMethods", []) or []
            if name and "generateContent" in methods:
                arr.append(name)
        return arr

    discovered = []
    model_error = None
    for v in ("v1beta", "v1"):
        try:
            for m in list_models(v):
                discovered.append((v, m))
        except Exception as e:
            model_error = e

    preferred_static = [
        ("v1beta", "gemini-2.5-flash"),
        ("v1beta", "gemini-2.5-flash-lite"),
        ("v1beta", "gemini-2.0-flash"),
        ("v1", "gemini-2.5-flash"),
        ("v1", "gemini-2.5-flash-lite"),
        ("v1", "gemini-2.0-flash"),
    ]
    env_model = os.getenv("GEMINI_MODEL", "").strip()
    if env_model:
        preferred_static.insert(0, ("v1beta", clean_model_name(env_model)))
        preferred_static.insert(1, ("v1", clean_model_name(env_model)))
    blocked = ("embed", "embedding", "image", "imagen", "veo", "tts", "audio", "live")
    ranked = []
    for v, m in preferred_static + discovered:
        ml = m.lower()
        if any(b in ml for b in blocked):
            continue
        if "2.5-flash-lite" in ml:
            weight = 0
        elif "2.5-flash" in ml:
            weight = 1
        elif "2.0-flash" in ml:
            weight = 2
        elif "flash" in ml:
            weight = 3
        elif "pro" in ml:
            weight = 4
        else:
            weight = 5
        ranked.append((weight, v, m))
    ranked.sort()
    candidates = []
    seen = set()
    for _, v, m in ranked:
        key = (v, m)
        if key not in seen:
            seen.add(key)
            candidates.append(key)
    if not candidates:
        raise RuntimeError("Gemini models endpoint 沒回傳可用文字模型" + (f"：{model_error}" if model_error else ""))
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.35, "topP": 0.9, "maxOutputTokens": 2200}
    }
    errors = []
    for api_version, model in candidates[:8]:
        url = f"https://generativelanguage.googleapis.com/{api_version}/models/{model}:generateContent"
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=(8, 45))
            if r.status_code in (404, 410):
                errors.append(f"{model}:404")
                continue
            if r.status_code in (401, 403):
                raise RuntimeError("Gemini API Key 無效或權限不足")
            if r.status_code == 429:
                raise RuntimeError("Gemini API 429：配額或速率限制，程式無法強制突破，請稍後或換專案/Key")
            if r.status_code in (500, 502, 503, 504):
                errors.append(f"{model}:{r.status_code}")
                continue
            r.raise_for_status()
            data = r.json()
            parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
            answer = "".join(p.get("text", "") for p in parts).strip()
            if answer:
                return answer
            errors.append(f"{model}:空白")
        except RuntimeError:
            raise
        except Exception as e:
            errors.append(f"{model}:{str(e)[:80]}")
    raise RuntimeError("Gemini 外部 AI 無回覆：" + " | ".join(errors[:4]))

def _call_openai_ai(prompt):
    """OpenAI 備用；支援 OPENAI_API_KEY。"""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你是台灣電腦賣場的資深硬體採購顧問。請用繁體中文直接給結論。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.4,
        "max_tokens": 900
    }
    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=(6, 35)
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()



def external_ai_recommendation(user_text, specs):
    prompt = build_ai_prompt(user_text, specs)
    provider = os.getenv("AI_PROVIDER", "gemini").strip().lower()
    try:
        if provider == "openai":
            result = _call_openai_ai(prompt)
        else:
            result = _call_gemini_ai(prompt)
        if result:
            return "🧠 AI 建議:" + chr(10) + result.strip()
        return "⚠️ 外部 AI 回覆空白，請稍後再試。"
    except Exception as e:
        msg = str(e)
        msg = re.sub(r'AIza[0-9A-Za-z_\-]+', 'AIza***', msg)
        msg = re.sub(r'key=[A-Za-z0-9_\-]+', 'key=***', msg)
        return "⚠️ 外部 AI 連線失敗，未啟用本機備援。" + chr(10) + msg

# ==========================================
# 2. 系統偵測模組
# ==========================================

def _run_wmic_value(command, fallback=""):
    """讀取 Windows WMI 單欄資料；失敗時回傳 fallback。"""
    try:
        out = subprocess.check_output(
            command,
            shell=True,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
            timeout=4
        ).decode("utf-8", errors="ignore")
        lines = [x.strip() for x in out.splitlines() if x.strip()]
        if len(lines) >= 2:
            return lines[1]
    except Exception:
        pass
    return fallback


def _run_wmic_table(command):
    """讀取 Windows WMI 表格資料；回傳已去空白的資料列。"""
    try:
        out = subprocess.check_output(
            command,
            shell=True,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
            timeout=5
        ).decode("utf-8", errors="ignore")
        return [x.strip() for x in out.splitlines()[1:] if x.strip()]
    except Exception:
        return []


def detect_physical_disks():
    """盡量分開列出實體 SSD/HDD。Windows 用 wmic，其他系統退回磁碟分割區。"""
    disks = []
    rows = _run_wmic_table('wmic diskdrive get Model,Size,MediaType,InterfaceType')
    for row in rows:
        parts = re.split(r'\s{2,}', row)
        size_bytes = None
        for p in reversed(parts):
            if re.fullmatch(r'\d{9,}', p):
                size_bytes = int(p)
                break
        size_gb = round(size_bytes / (1024**3), 1) if size_bytes else 0
        model = row
        if size_bytes:
            model = row.replace(str(size_bytes), '').strip()
        for token in ['Fixed hard disk media', 'External hard disk media', 'NVMe', 'SCSI', 'IDE', 'USB']:
            model = model.replace(token, '').strip()
        model = re.sub(r'\s{2,}', ' ', model).strip()
        if model or size_gb:
            disks.append({'model': model or 'Unknown Disk', 'size_gb': size_gb})
    if not disks:
        seen = set()
        for p in psutil.disk_partitions(all=False):
            if not p.fstype or p.device in seen:
                continue
            seen.add(p.device)
            try:
                u = psutil.disk_usage(p.mountpoint)
                disks.append({'model': p.device, 'size_gb': round(u.total/(1024**3), 1), 'used_gb': round(u.used/(1024**3), 1)})
            except Exception:
                pass
    return disks


def detect_memory_slots():
    """讀取記憶體插槽資訊。筆電常會被 BIOS 隱藏，所以只作輔助判斷。"""
    rows = _run_wmic_table('wmic memorychip get Capacity,Speed,PartNumber,Manufacturer')
    sticks = []
    for row in rows:
        caps = re.findall(r'\d{9,}', row)
        cap_gb = round(int(caps[0])/(1024**3), 1) if caps else 0
        speed = ''
        m = re.search(r'\b(2400|2666|2933|3000|3200|3600|4800|5200|5600|6000|6400|7200|7600|8000)\b', row)
        if m:
            speed = m.group(1)
        cleaned = re.sub(r'\d{9,}', '', row).strip()
        sticks.append({'capacity_gb': cap_gb, 'speed': speed, 'raw': cleaned})
    return sticks


def classify_grade(value, thresholds):
    """thresholds: [(min_score, grade)]，由高到低。"""
    for minimum, grade in thresholds:
        if value >= minimum:
            return grade
    return 'F'


def nominal_capacity_gb(real_gb):
    """把 Windows 可用容量 31.4 / 63.7 轉成人看得懂的標稱 32 / 64。"""
    try:
        real = float(real_gb)
    except Exception:
        return real_gb
    common = [4, 8, 12, 16, 24, 32, 48, 64, 96, 128, 192, 256]
    return min(common, key=lambda x: abs(x - real))


def ram_label(real_gb, include_real=True):
    nominal = nominal_capacity_gb(real_gb)
    if include_real and abs(float(nominal) - float(real_gb)) > 0.15:
        return f"{nominal}G（系統可用 {real_gb}G）"
    return f"{nominal}G"


# v29：Benchmark 參考表（離線內建級距，可自行擴充）。
# 分數來源概念：GPU 參考 3DMark / PassMark 類公開排行級距；CPU 參考 Geekbench 6 / Cinebench 2024 / PassMark 類公開排行級距。
# 不再把單一 5090 / 9950X3D 當唯一滿分，而是以「目前消費級與工作站高階跑分天花板」作為 100 分級距。
GPU_BENCHMARKS = [
    (['rtx 5090'], 46923),
    (['rtx 4090'], 36500),
    (['rtx 5080'], 34000),
    (['rtx 4080 super'], 29000),
    (['rtx 4080'], 28500),
    (['rx 7900 xtx'], 31000),
    (['rtx 5070 ti'], 27821),
    (['rtx 4070 ti super'], 24500),
    (['rx 7900 xt'], 27500),
    (['rtx 5070'], 22221),
    (['rtx 4070 super'], 21000),
    (['rx 7800 xt'], 20500),
    (['rtx 4070'], 18000),
    (['rtx 5060 ti'], 16500),
    (['rtx 4060 ti'], 13500),
    (['rx 7700 xt'], 17000),
    (['arc b580'], 14500),
    (['rtx 5060'], 12500),
    (['rx 7600 xt'], 11500),
    (['rtx 4060'], 10800),
    (['rtx 3060'], 8800),
    (['rtx 3050'], 6200),
    (['gtx 1660 ti'], 6400),
    (['gtx 1650 ti'], 3700),
    (['gtx 1650'], 3500),
    (['radeon graphics', 'vega', 'integrated'], 1800),
]

CPU_BENCHMARKS = [
    (['threadripper 7995wx'], {'gb6_single': 3000, 'gb6_multi': 33000, 'cb2024_multi': 6100}),
    (['threadripper 7980x'], {'gb6_single': 3000, 'gb6_multi': 31000, 'cb2024_multi': 5200}),
    (['core ultra 9 285k', '285k'], {'gb6_single': 3350, 'gb6_multi': 23000, 'cb2024_multi': 2450}),
    (['9950x3d'], {'gb6_single': 3394, 'gb6_multi': 22223, 'cb2024_multi': 2423}),
    (['9950x'], {'gb6_single': 3410, 'gb6_multi': 21500, 'cb2024_multi': 2300}),
    (['core ultra 9 275hx', '275hx'], {'gb6_single': 3100, 'gb6_multi': 20500, 'cb2024_multi': 2100}),
    (['14900ks', '14900k', '14900'], {'gb6_single': 3100, 'gb6_multi': 20500, 'cb2024_multi': 2200}),
    (['7950x3d'], {'gb6_single': 3000, 'gb6_multi': 20500, 'cb2024_multi': 2100}),
    (['14700k', '14700'], {'gb6_single': 2900, 'gb6_multi': 19000, 'cb2024_multi': 2000}),
    (['core ultra 7 265k', '265k'], {'gb6_single': 3100, 'gb6_multi': 18500, 'cb2024_multi': 1900}),
    (['9800x3d'], {'gb6_single': 3350, 'gb6_multi': 16500, 'cb2024_multi': 1360}),
    (['9700x'], {'gb6_single': 3200, 'gb6_multi': 16000, 'cb2024_multi': 1250}),
    (['7800x3d'], {'gb6_single': 2850, 'gb6_multi': 15000, 'cb2024_multi': 1100}),
    (['7700x', '7700'], {'gb6_single': 2700, 'gb6_multi': 14000, 'cb2024_multi': 1100}),
    (['9600x'], {'gb6_single': 3150, 'gb6_multi': 13200, 'cb2024_multi': 1050}),
    (['7600x', '7600'], {'gb6_single': 2700, 'gb6_multi': 12000, 'cb2024_multi': 900}),
    (['14400'], {'gb6_single': 2450, 'gb6_multi': 12500, 'cb2024_multi': 1000}),
    (['13400'], {'gb6_single': 2300, 'gb6_multi': 11200, 'cb2024_multi': 900}),
    (['5700x3d'], {'gb6_single': 2100, 'gb6_multi': 10500, 'cb2024_multi': 820}),
    (['3750h'], {'gb6_single': 1100, 'gb6_multi': 3800, 'cb2024_multi': 330}),
]

GRADE_THRESHOLDS = [
    (93, 'SSS'), (88, 'SS+'), (82, 'SS'), (76, 'S+'), (70, 'S'),
    (64, 'A++'), (58, 'A+'), (52, 'A'), (46, 'B++'), (40, 'B+'),
    (34, 'B'), (27, 'C'), (20, 'D'), (12, 'E')
]

GPU_SCORE_CEILING = 46923     # 以目前公開 3DMark Time Spy Graphics 高階旗艦級距作為 100 參考。
CPU_SINGLE_CEILING = 3600
CPU_MULTI_CEILING = 33000
CPU_CB2024_CEILING = 6100


def _match_benchmark(name, table, default):
    n = (name or '').lower()
    for keys, val in table:
        if any(k in n for k in keys):
            return val
    return default


def _laptop_gpu_factor(gpu_name):
    g = (gpu_name or '').lower()
    if 'laptop' not in g:
        return 1.0
    # 筆電同名 GPU 受 TGP/散熱限制，不能等同桌機。
    if '5090' in g: return 0.76
    if '5080' in g: return 0.74
    if '5070 ti' in g: return 0.72
    if '5070' in g: return 0.72
    if '5060' in g or '4060' in g: return 0.76
    return 0.75


def _gpu_practical_floor(gpu_name):
    """跑分之外補上玩家體感下限，避免中高階筆電 GPU 被純分數過度低估。"""
    g = (gpu_name or '').lower()
    laptop = 'laptop' in g
    if '5090' in g: return 92 if laptop else 96
    if '4090' in g: return 88 if laptop else 93
    if '5080' in g: return 84 if laptop else 88
    if '4080' in g: return 80 if laptop else 84
    if '5070 ti' in g or '4070 ti' in g: return 64 if laptop else 72
    if '5070' in g or '4070 super' in g: return 58 if laptop else 66
    if '4070' in g: return 54 if laptop else 60
    if '5060 ti' in g or '4060 ti' in g: return 48 if laptop else 54
    if '5060' in g or '4060' in g: return 42 if laptop else 48
    if '3060' in g: return 38
    if '3050' in g or '1650' in g: return 22
    return 0

def gpu_benchmark_score(gpu_name):
    raw = _match_benchmark(gpu_name, GPU_BENCHMARKS, 2500)
    adjusted = raw * _laptop_gpu_factor(gpu_name)
    ratio = min(100, adjusted / GPU_SCORE_CEILING * 100)
    # 依型號級距補上實際遊戲體感下限；跑分仍是主體，但不讓 2K 主力卡被誤判成低階。
    ratio = max(ratio, _gpu_practical_floor(gpu_name))
    return round(ratio, 1), int(adjusted), int(raw)


def cpu_benchmark_score(cpu_name):
    data = _match_benchmark(cpu_name, CPU_BENCHMARKS, None)
    if not data:
        c = (cpu_name or '').lower()
        if 'ultra 9' in c or 'i9' in c or 'ryzen 9' in c:
            data = {'gb6_single': 2900, 'gb6_multi': 17000, 'cb2024_multi': 1750}
        elif 'ultra 7' in c or 'i7' in c or 'ryzen 7' in c:
            data = {'gb6_single': 2450, 'gb6_multi': 12500, 'cb2024_multi': 1100}
        elif 'ultra 5' in c or 'i5' in c or 'ryzen 5' in c:
            data = {'gb6_single': 2200, 'gb6_multi': 9500, 'cb2024_multi': 800}
        else:
            data = {'gb6_single': 1200, 'gb6_multi': 4500, 'cb2024_multi': 350}
    single_ratio = data['gb6_single'] / CPU_SINGLE_CEILING * 100
    multi_ratio = data['gb6_multi'] / CPU_MULTI_CEILING * 100
    cb_ratio = data['cb2024_multi'] / CPU_CB2024_CEILING * 100
    score = min(100, single_ratio * 0.22 + multi_ratio * 0.38 + cb_ratio * 0.40)
    return round(score, 1), data


def score_to_rank(score):
    return classify_grade(score, GRADE_THRESHOLDS)


def smart_hardware_grades(specs):
    """以多項公開跑分級距估算：1遊戲、2生產力/剪輯、3AI、4綜合。"""
    gpu_score, gpu_adj, gpu_raw = gpu_benchmark_score(specs.get('gpu_name', ''))
    cpu_score, cpu_data = cpu_benchmark_score(specs.get('cpu_name', ''))
    ram_nom = nominal_capacity_gb(specs.get('ram_total', 0))
    vram_gb = (specs.get('gpu_vram', 0) or 0) / 1024

    ram_score = min(100, 30 + ram_nom * 1.35)      # 32G 約 73、64G 約 100
    vram_score = min(100, 25 + vram_gb * 4.8)      # 12G 約 83、16G 約 100
    npu_score = 0
    cpu_lower = (specs.get('cpu_name', '') or '').lower()
    if 'ultra' in cpu_lower or 'ai' in cpu_lower:
        npu_score = 5

    game_score = min(100, gpu_score * 0.74 + cpu_score * 0.17 + ram_score * 0.09)
    prod_score = min(100, cpu_score * 0.40 + gpu_score * 0.25 + ram_score * 0.20 + vram_score * 0.12 + npu_score * 0.03)
    ai_score = min(100, gpu_score * 0.38 + vram_score * 0.34 + ram_score * 0.15 + cpu_score * 0.10 + npu_score * 0.03)
    overall_score = min(100, game_score * 0.34 + prod_score * 0.33 + ai_score * 0.33)
    return {
        'game_score_100': round(game_score, 1),
        'prod_score_100': round(prod_score, 1),
        'ai_score_100': round(ai_score, 1),
        'overall_score_100': round(overall_score, 1),
        'GameGrade': score_to_rank(game_score),
        'ProductivityGrade': score_to_rank(prod_score),
        'AICalcGrade': score_to_rank(ai_score),
        'OverallGrade': score_to_rank(overall_score),
        'gpu_benchmark_ratio': gpu_score,
        'gpu_benchmark_adjusted': gpu_adj,
        'gpu_benchmark_raw': gpu_raw,
        'cpu_benchmark_ratio': cpu_score,
        'cpu_benchmark_data': cpu_data,
        'ram_nominal': ram_nom,
        'npu_bonus': npu_score,
    }

def get_specs():
    specs = {}
    try:
        specs['cpu_name'] = cpuinfo.get_cpu_info().get('brand_raw', 'Unknown CPU')
    except Exception:
        specs['cpu_name'] = "Unknown CPU"

    specs['cpu_count'] = psutil.cpu_count(logical=False) or 4
    specs['cpu_threads'] = psutil.cpu_count(logical=True) or specs['cpu_count']

    ram_info = psutil.virtual_memory()
    specs['ram_total'] = round(ram_info.total / (1024**3), 1)
    specs['ram_used'] = round(ram_info.used / (1024**3), 1)
    specs['ram_nominal'] = nominal_capacity_gb(specs['ram_total'])
    specs['memory_sticks'] = detect_memory_slots()

    gpus = GPUtil.getGPUs()
    specs['gpu_name'] = gpus[0].name if gpus else "Integrated Graphics"
    specs['gpu_vram'] = round(gpus[0].memoryTotal, 0) if gpus else 0
    specs['gpu_vram_used'] = round(gpus[0].memoryUsed, 0) if gpus else 0

    try:
        disk_info = psutil.disk_usage('/')
        specs['disk_total'] = round(disk_info.total / (1024**3), 1)
        specs['disk_used'] = round(disk_info.used / (1024**3), 1)
    except Exception:
        specs['disk_total'], specs['disk_used'] = 0, 0
    specs['disks'] = detect_physical_disks()

    manufacturer = _run_wmic_value('wmic computersystem get Manufacturer', '')
    model = _run_wmic_value('wmic computersystem get Model', '')
    board_manu = _run_wmic_value('wmic baseboard get Manufacturer', '')
    board_product = _run_wmic_value('wmic baseboard get Product', '')
    board_version = _run_wmic_value('wmic baseboard get Version', '')
    if not board_manu or board_manu.lower() in ['unknown', 'to be filled by o.e.m.']:
        board_manu = _powershell_value('(Get-CimInstance Win32_BaseBoard).Manufacturer', board_manu)
    if not board_product or board_product.lower() in ['unknown', 'base board product name', 'to be filled by o.e.m.']:
        board_product = _powershell_value('(Get-CimInstance Win32_BaseBoard).Product', board_product)
    chassis = _run_wmic_value('wmic systemenclosure get ChassisTypes', '')

    specs['system_manufacturer'] = manufacturer or 'Unknown'
    specs['system_model'] = model or 'Unknown'
    specs['board_manufacturer'] = board_manu or 'Unknown'
    specs['board_product'] = board_product or 'Unknown'
    specs['board_version'] = board_version or ''

    try:
        has_battery = psutil.sensors_battery() is not None
    except Exception:
        has_battery = False
    laptop_chassis_tokens = ['8', '9', '10', '14', '30', '31', '32']
    specs['is_laptop'] = has_battery or any(x in chassis for x in laptop_chassis_tokens)

    if specs['is_laptop']:
        specs['mobo'] = f"{manufacturer} {model}".strip() if model else "筆電型號未讀取"
        specs['device_model_label'] = (f"筆電型號：{manufacturer} {model}".strip() if model and model.lower() not in ['unknown', 'system product name'] else f"筆電型號：未完整讀取，推測依 CPU/GPU 規格判斷升級能力")
    else:
        specs['mobo'] = f"{board_manu} {board_product}".strip()
        specs['device_model_label'] = (f"桌機主機板：{board_manu} {board_product}".strip() if board_product and board_product.lower() not in ['unknown', 'base board product name'] else '桌機主機板：未完整讀取，推測需以主機板型號或 BIOS 資訊確認')

    specs['psu'] = '一般 Windows 無法可靠讀取 PSU 瓦數；升級顯卡前請看電源本體標籤或購買紀錄。'
    specs['cooling_fans'] = detect_cooling_sensors()
    specs['cooler_note'] = '散熱器型號/風扇 RPM 一般需主機板感測器或 OpenHardwareMonitor/LibreHardwareMonitor；讀不到屬正常。'

    cpu_str = specs['cpu_name'].lower()
    specs['support_gen5'] = bool("ultra" in cpu_str or re.search(r'i[3579]-1[234]', cpu_str) or re.search(r'ryzen \d [789]\d{3}', cpu_str))
    specs['ram_type'] = "DDR5" if specs['support_gen5'] else "DDR4"
    return specs


def calculate_score(specs):
    scores = {}
    cpu_threads = specs.get('cpu_threads', specs.get('cpu_count', 4) * 2)
    cpu_cores = specs.get('cpu_count', 4)
    ram_total = specs.get('ram_total', 0)
    vram = specs.get('gpu_vram', 0)
    gpu_name = specs.get('gpu_name', '').lower()

    scores['CPU'] = int((cpu_cores ** 1.2) * 1500 + cpu_threads * 450)
    scores['RAM'] = int(ram_total * 350)
    scores['GPU'] = int(vram * 1.8)
    scores['AI_Score'] = int(vram * 2.5 + cpu_cores * 400 + ram_total * 120)
    scores['Total'] = scores['CPU'] + scores['RAM'] + scores['GPU'] + scores['AI_Score']

    gpu_tier_bonus = 0
    if any(x in gpu_name for x in ['5090', '4090']): gpu_tier_bonus = 45000
    elif any(x in gpu_name for x in ['5080', '4080']): gpu_tier_bonus = 36000
    elif any(x in gpu_name for x in ['5070 ti', '4070 ti']): gpu_tier_bonus = 30000
    elif any(x in gpu_name for x in ['5070', '4070']): gpu_tier_bonus = 24000
    elif any(x in gpu_name for x in ['5060 ti', '4060 ti']): gpu_tier_bonus = 17000
    elif any(x in gpu_name for x in ['5060', '4060']): gpu_tier_bonus = 14000
    elif any(x in gpu_name for x in ['3060', '4050', '3050']): gpu_tier_bonus = 9000
    elif 'integrated' in gpu_name or 'radeon graphics' in gpu_name: gpu_tier_bonus = 2500

    scores['Game'] = int(gpu_tier_bonus + vram * 2.2 + cpu_cores * 1200 + min(ram_total, 64) * 420)
    scores['Productivity'] = int(gpu_tier_bonus * 0.75 + vram * 3.1 + cpu_threads * 1300 + min(ram_total, 128) * 650)
    # v29：等級不再用總分硬切，改用「9950X3D + RTX 5090 = SSS」為參考天花板。
    ranks = smart_hardware_grades(specs)
    scores.update(ranks)
    return scores



def hardware_limit_flags(specs):
    cpu = (specs.get('cpu_name', '') or '').lower()
    gpu = (specs.get('gpu_name', '') or '').lower()
    vram = specs.get('gpu_vram', 0) or 0
    is_laptop = specs.get('is_laptop', False)
    flags = []
    old_cpu_keys = ['i7-7', 'i5-7', 'i3-7', 'i7-8', 'i5-8', 'ryzen 5 2500', 'ryzen 7 2700', 'ryzen 7 3750h', 'ryzen 5 3550h']
    old_gpu_keys = ['gtx 1050', 'gtx 1050 ti', 'gtx 1060', 'gtx 1070', 'gtx 1080', 'gtx 1650', 'gtx 1650 ti', 'gtx 1660', 'mx150', 'mx250']
    if any(k in cpu for k in old_cpu_keys):
        flags.append('CPU 已屬 6~10 年前平台或低功耗舊平台')
    if any(k in gpu for k in old_gpu_keys):
        flags.append('GPU 已屬舊世代，3A/AI 不建議硬撐')
    if 'integrated' in gpu or 'radeon graphics' in gpu or vram <= 0:
        flags.append('未偵測到可用獨立顯卡/VRAM，遊戲與 AI 上限很低')
    if is_laptop:
        flags.append('筆電多數只能升級 RAM/SSD/散熱維護，CPU/GPU 通常不能換')
    return flags


def is_very_limited_machine(specs, scores=None):
    scores = scores or calculate_score(specs)
    flags = hardware_limit_flags(specs)
    overall = scores.get('overall_score_100', 0)
    game = scores.get('game_score_100', 0)
    return bool(overall < 28 or game < 25 or any('未偵測到可用獨立顯卡' in f for f in flags))


def detect_cooling_sensors():
    command = "powershell -NoProfile -Command \"try { Get-WmiObject -Namespace root\\OpenHardwareMonitor -Class Sensor | Where-Object {$_.SensorType -eq \'Fan\'} | Select-Object -First 8 Name,Value | ForEach-Object { $_.Name + \':\' + [int]$_.Value + \'RPM\' } } catch {}\""
    rows = _run_wmic_table(command)
    return rows[:8]


def _powershell_value(command, fallback=''):
    try:
        out = subprocess.check_output(
            f'powershell -NoProfile -Command "{command}"',
            shell=True,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
            timeout=5
        ).decode('utf-8', errors='ignore')
        return out.strip() or fallback
    except Exception:
        return fallback


def short_hardware_verdict(specs, scores):
    game = scores.get('game_score_100', 0)
    ai = scores.get('ai_score_100', 0)
    prod = scores.get('prod_score_100', 0)
    vram = (specs.get('gpu_vram', 0) or 0) / 1024
    ram = nominal_capacity_gb(specs.get('ram_total', 0))
    limited = is_very_limited_machine(specs, scores)
    if limited:
        g_txt = "主要適合文書、影音、網遊；3A/AI 不建議硬撐。"
    elif game >= 86:
        g_txt = "2K 高刷與 4K 高畫質都很穩；光追視遊戲搭 DLSS/FSR。"
    elif game >= 70:
        g_txt = "2K 滿/高畫質主力；4K 可玩但建議調整光追與特效。"
    elif game >= 55:
        g_txt = "1080p/2K 中高畫質可用；4K 需降畫質或開升頻。"
    elif game >= 38:
        g_txt = "適合 1080p 與輕中度遊戲；大型 3A 建議明顯降設定。"
    else:
        g_txt = "偏文書影音與網遊定位；大型遊戲體驗受限。"
    if limited:
        a_txt = "AI/重剪輯不適合本機硬跑；建議雲端或換新平台。"
    elif ai >= 78 and vram >= 12 and ram >= 32:
        a_txt = "AI、剪輯、多工可本機處理中高階工作流。"
    elif ai >= 55 and ram >= 32:
        a_txt = "剪輯與 AI 入門/中階可用；大模型、長影片建議雲端輔助。"
    elif prod >= 45:
        a_txt = "剪輯與多工可用；AI 以小模型或雲端輔助較合理。"
    else:
        a_txt = "生產力只適合輕量工作；重度剪輯/AI 不建議投太多升級。"
    if limited:
        u_txt = "升級 RAM/SSD 只能改善流暢度；想玩 3A/AI 建議直接買新機或桌機。"
    elif specs.get('is_laptop'):
        u_txt = "筆電升級重點是 RAM/SSD/散熱；CPU/GPU 通常不可換。"
    else:
        u_txt = "桌機可依需求升 GPU/SSD/電供；平台升級要連主板與 RAM 一起看。"
    return "簡短評價:" + chr(10) + "• " + g_txt + chr(10) + "• " + a_txt + chr(10) + "• " + u_txt

def hardware_scene_analysis(specs, scores):
    game_grade = scores.get('GameGrade', 'F')
    prod_grade = scores.get('ProductivityGrade', 'F')
    ai_grade = scores.get('AICalcGrade', 'F')
    overall_grade = scores.get('OverallGrade', 'F')

    lines = [
        "硬體評價：",
        f"1. 遊戲：{game_grade}（{scores.get('game_score_100', 0)}/100）",
        f"2. 生產力/剪輯：{prod_grade}（{scores.get('prod_score_100', 0)}/100）",
        f"3. AI：{ai_grade}（{scores.get('ai_score_100', 0)}/100）",
        f"4. 綜合：{overall_grade}（{scores.get('overall_score_100', 0)}/100）",
        "",
        short_hardware_verdict(specs, scores),
        "",
        "評分方式：",
        "GPU 參考 3DMark / PassMark 類跑分級距；CPU 參考 Geekbench / Cinebench / PassMark 類級距。",
        "遊戲偏重 GPU；生產力偏重 CPU+RAM；AI 偏重 GPU+VRAM。",
        "綜合分由前 3 項加權平均；分級：SSS > SS+ > SS > S+ > S > A++ > A+ > A > B++ > B+ > B > C > D > E > F。",
    ]
    return "\n".join(lines)


def hardware_upgrade_suggestions(specs, scores):
    is_laptop = specs.get("is_laptop", False)
    ram = specs.get("ram_total", 0)
    disk_total = specs.get("disk_total", 0)
    disk_used = specs.get("disk_used", 0)
    vram = specs.get("gpu_vram", 0)
    total = scores.get("Total", 0)
    support_gen5 = specs.get("support_gen5", False)
    limited = is_very_limited_machine(specs, scores)
    flags = hardware_limit_flags(specs)
    items = []
    if limited:
        items.append("整機判斷：目前平台/顯示能力偏弱，RAM/SSD 只能延命，不能讓 3A 或 AI 體驗大幅起飛。")
        if ram < 16:
            items.append("RAM：若此機可擴充，可補到 16G；若是板載不可升級，就不建議再投太多。")
        if disk_total and (disk_total < 900 or (disk_used / max(disk_total, 1)) > 0.75):
            items.append("SSD：可補 1TB 當資料/遊戲碟，但這是容量改善，不是效能翻身。")
        if is_laptop:
            items.append("筆電限制：CPU/GPU 多半不能換；若要 2K/4K 3A、剪輯或 AI，建議直接買 RTX 5070 以上筆電或桌機。")
        else:
            items.append("桌機方向：若機殼/電供/主板太舊，與其零碎升級，不如整機重組較乾脆。")
        return "可升級建議:" + chr(10) + chr(10).join(["• " + x for x in items]) + chr(10) + "整體建議：先確認是否可升 RAM/SSD；若目標是遊戲/AI，優先看新機。"
    if ram < 16:
        items.append(f"RAM：優先升到 16G 或 32G（目前 {ram_label(ram, include_real=False)}，體感提升最大）。")
    elif ram < 32:
        items.append(f"RAM：若要剪輯、AI、多開遊戲，建議升到 32G（目前 {ram_label(ram, include_real=False)}）。")
    else:
        items.append(f"RAM：目前 {ram_label(ram, include_real=False)} 已夠用，除非重度剪輯/AI 才考慮 64G+。")
    if disk_total and (disk_total < 900 or (disk_used / max(disk_total, 1)) > 0.75):
        gen = "Gen5" if support_gen5 else "Gen4"
        items.append(f"SSD：建議加 1TB / 2TB {gen} NVMe，遊戲與素材庫會更舒服。")
    else:
        items.append("SSD：容量暫時可用，可等價格好再補 2TB 遊戲碟。")
    if is_laptop:
        if vram < 8000:
            items.append("筆電 GPU/CPU 多半不能換；若要 2K/4K 3A 或 AI，建議直接看 RTX 5070 / 5080 / 5090 筆電或桌機。")
        items.append("筆電可升級重點：RAM、SSD、散熱清灰/重上散熱膏、外接螢幕與鍵鼠。")
        if flags:
            items.append("限制提醒：" + "；".join(flags[:2]) + "。")
    else:
        if vram < 8000:
            items.append("顯卡：若要遊戲分數大幅提升，建議 RTX 4060 Ti / 5070 / 5070 Ti 以上。")
        elif vram < 12000:
            items.append("顯卡：2K 高刷可考慮 RTX 5070 Ti / 5080；AI 則看 VRAM 16G+。")
        else:
            items.append("顯卡：目前 VRAM 充足，可先看 CPU/RAM/SSD 是否拖後腿。")
        items.append("電供：升級中高階顯卡前，確認 750W/850W/1000W 與 12V-2x6/PCIe 5.0 線材。")
        items.append("主機板/平台：若 CPU 分數偏低，可評估 AM5 / LGA1851 新平台，但要連 RAM/主板一起看。")
    if total < 35000:
        verdict = "整體建議：若只是文書可補 RAM/SSD；若要 3A/AI，建議新機。"
    elif total < 65000:
        verdict = "整體建議：中階可用，升級 GPU/SSD 會最有感。"
    else:
        verdict = "整體建議：效能已不差，升級要針對你的場景，不必盲目全換。"
    return "可升級建議:" + chr(10) + chr(10).join(["• " + x for x in items]) + chr(10) + verdict

def get_ram_options_for_build(socket, ddr):
    capacities = ["16G", "32G", "48G", "64G", "96G"]
    if ddr == "DDR4":
        freqs = ["3200", "3600"] if socket in ["AM4", "LGA1700"] else ["3200"]
    else:
        if socket == "AM5":
            freqs = ["5600", "6000", "6400"]
        elif socket == "LGA1851":
            freqs = ["5600", "6000", "6400", "7200"]
        else:
            freqs = ["5600", "6000", "6400"]
    return [f"{ddr} {freq} {cap}" for freq in freqs for cap in capacities]

# ==========================================
# 3. 主應用程式 UI
# ==========================================
class ROGApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.specs = get_specs()
        self.scores = calculate_score(self.specs)
        self.is_laptop = self.specs['is_laptop']
        
        self.cart_items = {} 
        self.build_step = 0
        self.build_max_steps = 0
        self.build_context = {} 
        self.current_mode = ""
        
        device_type = "筆記型電腦" if self.is_laptop else "桌上型電腦"
        self.title(f"電腦檢測升級工具 v30_ai_advisor_rating_fix - [{device_type}]")
        self.geometry("1840x1040")
        self.minsize(1600, 900)
        self.resizable(True, True)
        try:
            self.after(150, lambda: self.state("zoomed"))
        except Exception:
            pass
        
        # v22.1：改成 grid 版面，左側與中間使用 CTkScrollableFrame。
        # 不對 ScrollableFrame 使用 pack_propagate(False)，避免內容被吃掉只剩空白。
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=15, pady=5)
        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(0, weight=0, minsize=500)
        self.main_container.grid_columnconfigure(1, weight=1, minsize=860)
        self.main_container.grid_columnconfigure(2, weight=0, minsize=540)

        self.left_frame = ctk.CTkScrollableFrame(self.main_container, width=480, corner_radius=10)
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.setup_left_panel()

        self.mid_frame = ctk.CTkScrollableFrame(self.main_container, width=840, corner_radius=10)
        self.mid_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.setup_mid_panel()

        self.right_frame = ctk.CTkFrame(self.main_container, width=540, corner_radius=10)
        self.right_frame.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)
        self.right_frame.grid_propagate(False)
        self.setup_right_panel()

        # 滑鼠停在哪個可滾動區，滾輪就滾那個區。
        self.bind_all("<MouseWheel>", self._on_mousewheel, add="+")
        self.bind_all("<Button-4>", self._on_mousewheel, add="+")
        self.bind_all("<Button-5>", self._on_mousewheel, add="+")

    def _find_scrollable_parent(self, widget):
        while widget is not None:
            if isinstance(widget, ctk.CTkScrollableFrame):
                return widget
            widget = getattr(widget, "master", None)
        return None

    def _on_mousewheel(self, event):
        # Textbox / Entry / OptionMenu 下拉清單不搶事件，避免影響選字、複製、下拉操作。
        if isinstance(event.widget, (ctk.CTkTextbox, ctk.CTkEntry)):
            return
        scrollable = self._find_scrollable_parent(event.widget)
        if scrollable is None:
            return
        try:
            if getattr(event, "num", None) == 5 or getattr(event, "delta", 0) < 0:
                direction = 1
            elif getattr(event, "num", None) == 4 or getattr(event, "delta", 0) > 0:
                direction = -1
            else:
                return
            scrollable._parent_canvas.yview_scroll(direction * 3, "units")
        except Exception:
            pass

    def setup_left_panel(self):
        ctk.CTkLabel(self.left_frame, text="[ SYSTEM SPECS ]", font=ctk.CTkFont(size=16, weight="bold"), text_color="#00ffff").pack(anchor="w", padx=20, pady=(15, 2))
        ctk.CTkLabel(self.left_frame, text=f"CPU: {self.specs['cpu_name']}", justify="left", wraplength=440).pack(anchor="w", padx=20, pady=2)
        freq = "5600" if self.specs['support_gen5'] else "3200"
        ctk.CTkLabel(self.left_frame, text=f"RAM: {ram_label(self.specs['ram_total'])} (已用: {self.specs['ram_used']}G) [{self.specs['ram_type']} {freq}]", justify="left").pack(anchor="w", padx=20, pady=2)
        ctk.CTkLabel(self.left_frame, text=f"GPU: {self.specs['gpu_name']}\nVRAM: {self.specs['gpu_vram']} MB (已用: {self.specs['gpu_vram_used']} MB)", justify="left", wraplength=430).pack(anchor="w", padx=20, pady=2)
        disk_lines = []
        for idx, d in enumerate(self.specs.get('disks', []), 1):
            size = d.get('size_gb', 0)
            model = d.get('model', 'Unknown Disk')
            disk_lines.append(f"Disk {idx}: {model} / {size} GB（已用: {d.get('used_gb', 0)}G）")
        if not disk_lines:
            disk_lines.append(f"Disk: 總共 {self.specs['disk_total']} GB (已用: {self.specs['disk_used']}G)")
        ctk.CTkLabel(self.left_frame, text="\n".join(disk_lines), justify="left", text_color="#aaaaaa", wraplength=430).pack(anchor="w", padx=20, pady=2)
        if not self.specs.get('is_laptop'):
            ctk.CTkLabel(self.left_frame, text=f"MOBO: {self.specs.get('mobo', '未知')}", justify="left", text_color="#aaaaaa", wraplength=430).pack(anchor="w", padx=20, pady=2)
            ctk.CTkLabel(self.left_frame, text=f"PSU: {self.specs.get('psu', '未知')}", justify="left", text_color="#aaaaaa", wraplength=430).pack(anchor="w", padx=20, pady=2)
            fan_rows = self.specs.get('cooling_fans', [])
            fan_text = '散熱/風扇: ' + (' / '.join(fan_rows) if fan_rows else self.specs.get('cooler_note', '讀不到風扇感測器'))
            ctk.CTkLabel(self.left_frame, text=fan_text, justify="left", text_color="#aaaaaa", wraplength=430).pack(anchor="w", padx=20, pady=2)
        mem_sticks = self.specs.get('memory_sticks', [])
        if mem_sticks:
            mem_text = "RAM 模組：" + " / ".join([f"{s.get('capacity_gb')}G {s.get('speed','')}" for s in mem_sticks if s.get('capacity_gb')])
            ctk.CTkLabel(self.left_frame, text=mem_text, justify="left", text_color="#aaaaaa", wraplength=430).pack(anchor="w", padx=20, pady=2)
        
        ctk.CTkLabel(self.left_frame, text="[ BENCHMARK SCORES ]", font=ctk.CTkFont(size=16, weight="bold"), text_color="#00ffff").pack(anchor="w", padx=20, pady=(15, 2))
        ctk.CTkLabel(self.left_frame, text=f"CPU Score: {self.scores['CPU']:,} pts").pack(anchor="w", padx=30, pady=1)
        ctk.CTkLabel(self.left_frame, text=f"RAM Score: {self.scores['RAM']:,} pts").pack(anchor="w", padx=30, pady=1)
        ctk.CTkLabel(self.left_frame, text=f"GPU Score: {self.scores['GPU']:,} pts").pack(anchor="w", padx=30, pady=1)
        ctk.CTkLabel(self.left_frame, text=f"AI Score:    {self.scores['AI_Score']:,} pts", text_color="#ff55ff").pack(anchor="w", padx=30, pady=1)
        
        total_color = "#00ff00" if self.scores['Total'] > 80000 else "#ffaa00"
        ctk.CTkLabel(self.left_frame, text=f"TOTAL: {self.scores['Total']:,}", font=ctk.CTkFont(size=22, weight="bold"), text_color=total_color).pack(anchor="w", padx=20, pady=(10, 10))
        ctk.CTkLabel(self.left_frame, text=hardware_scene_analysis(self.specs, self.scores), text_color="#00ff99", justify="left", wraplength=440).pack(anchor="w", padx=20, pady=(0, 6))
        ctk.CTkLabel(self.left_frame, text=hardware_upgrade_suggestions(self.specs, self.scores), text_color="#ffee88", justify="left", wraplength=440).pack(anchor="w", padx=20, pady=(0, 10))
        
        ctk.CTkLabel(self.left_frame, text="[ 結構化 AI 顧問 ]", font=ctk.CTkFont(size=16, weight="bold"), text_color="#ff55ff").pack(anchor="w", padx=20, pady=5)
        self.ai_input = ctk.CTkEntry(self.left_frame, placeholder_text="輸入需求 (例: 預算5萬, 跑黑神話)", width=430)
        self.ai_input.pack(padx=20, pady=5)
        self.ai_button = ctk.CTkButton(self.left_frame, text="🧠 AI 分析與決策", command=self.run_ai_advisor, fg_color="#660066")
        self.ai_button.pack(pady=5)
        self.clear_ai_memory_btn = ctk.CTkButton(self.left_frame, text="🧹 清空 AI 記憶", command=self.clear_ai_memory, fg_color="#444444", width=160)
        self.clear_ai_memory_btn.pack(pady=(0, 5))
        
        self.ai_response = ctk.CTkLabel(self.left_frame, text="等待輸入...", text_color="#cccccc", justify="left", wraplength=430)
        self.ai_response.pack(anchor="w", padx=20, pady=10)
        
        self.mode_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.mode_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(self.mode_frame, text="🔧 局部升級現有", command=self.mode_upgrade, width=150).pack(side="left", padx=5)
        ctk.CTkButton(self.mode_frame, text="🛒 新裝機/買新機", command=self.mode_build_select, width=150, fg_color="#cc5500").pack(side="right", padx=5)

    def setup_mid_panel(self):
        self.mid_title = ctk.CTkLabel(self.mid_frame, text="[ 操作面板 ]", font=ctk.CTkFont(size=18, weight="bold"), text_color="#00ffff")
        self.mid_title.pack(anchor="w", padx=20, pady=(15, 10))
        
        self.upgrade_container = ctk.CTkFrame(self.mid_frame, fg_color="transparent")
        self.upg_cat = ctk.CTkOptionMenu(self.upgrade_container, values=["固態硬碟 (SSD)", "記憶體 (RAM)"], command=self.update_upg_options, width=400)
        self.upg_cat.pack(pady=10)
        self.upg_item = ctk.CTkOptionMenu(self.upgrade_container, values=["請選擇"], width=400)
        self.upg_item.pack(pady=10)
        
        self.build_select_container = ctk.CTkFrame(self.mid_frame, fg_color="transparent")
        ctk.CTkButton(self.build_select_container, text="🖥️ 組裝全新客製化桌機", command=self.start_desktop_builder, height=50, width=300).pack(pady=15)
        ctk.CTkButton(self.build_select_container, text="💻 尋找全新電競/高效筆電", command=self.start_laptop_builder, height=50, width=300, fg_color="#0066cc").pack(pady=15)
        
        self.build_container = ctk.CTkFrame(self.mid_frame, fg_color="transparent")
        self.step_label = ctk.CTkLabel(self.build_container, text="步驟指示", font=ctk.CTkFont(size=15, weight="bold"), text_color="#ffff00")
        self.step_label.pack(pady=10)
        self.build_menu_1 = ctk.CTkOptionMenu(self.build_container, values=[], command=self.on_build_menu1_change, width=400)
        self.build_menu_2 = ctk.CTkOptionMenu(self.build_container, values=[], width=400)
        
        self.manual_query_frame = ctk.CTkFrame(self.mid_frame, fg_color="transparent")
        ctk.CTkLabel(self.manual_query_frame, text="[ 自訂型號 / 查價關鍵字 ]", text_color="#00ffff").pack(anchor="w", padx=20, pady=(8, 2))
        self.manual_query_entry = ctk.CTkEntry(
            self.manual_query_frame,
            placeholder_text="例如：ROG Strix G16 RTX 5070、RTX 5070 Ti、Ryzen 7 7800X3D",
            width=770
        )
        self.manual_query_entry.pack(padx=20, pady=5)
        ctk.CTkButton(self.manual_query_frame, text="🧹 清除自訂型號", command=lambda: self.manual_query_entry.delete(0, "end"), width=160, fg_color="#444444").pack(anchor="e", padx=20, pady=(0, 5))
        
        self.nav_frame = ctk.CTkFrame(self.build_container, fg_color="transparent")
        self.nav_frame.pack(fill="x", pady=15)
        ctk.CTkButton(self.nav_frame, text="⬅️ 上一步", command=self.prev_step, width=110, fg_color="#555555").pack(side="left", padx=5)
        ctk.CTkButton(self.nav_frame, text="⏭️ 跳過此項", command=self.skip_step, width=110, fg_color="#555555").pack(side="left", padx=5)
        ctk.CTkButton(self.nav_frame, text="下一步 ➡️", command=self.next_step, width=110, fg_color="#0066cc").pack(side="right", padx=5)
        
        self.action_frame = ctk.CTkFrame(self.mid_frame, fg_color="transparent")
        self.search_btn = ctk.CTkButton(self.action_frame, text="🔍 查詢時價", command=self.execute_search, fg_color="#cc5500", width=180)
        self.search_btn.pack(side="left", padx=12)
        self.open_link_btn = ctk.CTkButton(self.action_frame, text="🌐 開啟商品/搜尋", command=self.open_current_link, fg_color="#005599", state="disabled", width=180)
        self.open_link_btn.pack(side="left", padx=12)
        self.add_cart_btn = ctk.CTkButton(self.action_frame, text="🛒 確定加入清單", command=self.add_to_cart, fg_color="#008800", state="disabled", width=180)
        self.add_cart_btn.pack(side="right", padx=12)
        
        self.price_label = StatusTextbox(self.mid_frame, text="請選擇規格並點擊 [查詢時價]", font=ctk.CTkFont(size=14), text_color="#ffffff", width=790, height=340, wrap="word")
        
        self.current_fetch = None
        self.current_mode = ""
        self.is_searching = False  # 防止查詢按鈕連點造成多執行緒互相打架
        self.search_keywords = {} # 🐛 關鍵修復：把初始化字典加回來！

    def ui_safe(self, func):
        """所有 tkinter / customtkinter UI 更新都必須回主執行緒執行。"""
        try:
            self.after(0, func)
        except Exception:
            pass

    def set_search_busy(self, busy):
        """統一管理查詢按鈕狀態，避免按鈕被 disable 後回不來。"""
        self.is_searching = busy
        self.search_btn.configure(state="disabled" if busy else "normal")
        if busy:
            self.add_cart_btn.configure(state="disabled")
            self.open_link_btn.configure(state="disabled")

    def setup_right_panel(self):
        ctk.CTkLabel(self.right_frame, text="[ 智慧清單 CART ]", font=ctk.CTkFont(size=16, weight="bold"), text_color="#00ff00").pack(anchor="w", padx=20, pady=(15, 5))
        self.cart_textbox = ctk.CTkTextbox(self.right_frame, width=500, height=600, font=ctk.CTkFont(size=14), state="disabled")
        self.cart_textbox.pack(padx=20, pady=5, fill="both", expand=True)
        
        self.jump_menu = ctk.CTkOptionMenu(self.right_frame, values=["-- 返回特定步驟修改 --"], command=self.jump_to_step, width=500, fg_color="#333333")
        self.jump_menu.pack(pady=5, padx=20)
        
        self.total_cost_label = ctk.CTkLabel(self.right_frame, text="總計: NT$ 0", font=ctk.CTkFont(size=24, weight="bold"), text_color="#ffff00")
        self.total_cost_label.pack(pady=5)
        
        self.checkout_btn = ctk.CTkButton(self.right_frame, text="🛍️ 結帳與生成購買連結", command=self.generate_links, fg_color="#aa00aa", hover_color="#880088", height=40)
        self.checkout_btn.pack(pady=5, fill="x", padx=20)
        
        ctk.CTkButton(self.right_frame, text="🗑️ 清空重來", command=self.clear_cart, fg_color="#880000").pack(pady=5, fill="x", padx=20)

    def repack_bottom_actions(self):
        self.action_frame.pack_forget()
        self.price_label.pack_forget()
        self.manual_query_frame.pack_forget()
        self.manual_query_frame.pack(fill="x", padx=5, pady=(5, 0))
        self.action_frame.pack(fill="x", pady=12)
        self.price_label.pack(fill="both", expand=True, padx=20, pady=10)

    # ==========================================
    # 4. 模式切換邏輯
    # ==========================================
    def run_ai_advisor(self):
        user_text = self.ai_input.get().strip()
        if not user_text:
            self.ai_response.configure(text="請先輸入需求，例如：4K 2077 240FPS、預算5萬剪輯、AI繪圖。", text_color="#ffaa00")
            return

        self.ai_response.configure(text="⏳ AI 顧問分析中...\n有設定 OPENAI_API_KEY 會優先使用外部 AI，否則使用本機 AI。", text_color="#cccccc")

        def task():
            result = external_ai_recommendation(user_text, self.specs)
            if not result:
                result = local_ai_recommendation(user_text, self.specs)
            # 根據需求幫小白自動提示該點哪個模式
            lower = user_text.lower()
            if any(k in lower for k in ["4k", "240", "2077", "5090", "5080", "全新", "新機", "組", "桌機"]):
                result += "\n\n✅ 操作建議：先點「新裝機/買新機」。若要 4K 2077 240FPS，建議優先走桌機 RTX 5090 / 5080 級別，筆電會受功耗限制。"
            elif any(k in lower for k in ["ram", "ssd", "容量", "不夠", "升級"]):
                result += "\n\n✅ 操作建議：先點「局部升級現有」，再選 RAM 或 SSD。"
            self.ui_safe(lambda result=result: self.ai_response.configure(text=result, text_color="#00ff00"))

        threading.Thread(target=task, daemon=True).start()

    def mode_upgrade(self):
        self.current_fetch = None
        self.build_select_container.pack_forget()
        self.build_container.pack_forget()
        self.upgrade_container.pack(fill="x", padx=20, pady=10)
        self.repack_bottom_actions()
        
        self.mid_title.configure(text="[ 局部升級模式 (Upgrade) ]")
        self.current_mode = "UPGRADE"
        
        cats = ["固態硬碟 (SSD)", "記憶體 (RAM)"]
        if not self.is_laptop: cats.extend(["顯示卡 (GPU)", "電源供應器 (PSU)", "CPU 處理器", "CPU 散熱器", "機殼", "螢幕", "周邊/附加商品"])
        self.upg_cat.configure(values=cats)
        self.upg_cat.set(cats[0])
        self.update_upg_options(cats[0])

    def update_upg_options(self, cat):
        opts = []
        self.search_keywords.clear()
        
        if cat == "記憶體 (RAM)":
            freq = "5600" if self.specs['support_gen5'] else "3200"
            opts = [f"{self.specs['ram_type']} {freq} {s}" for s in UPGRADE_DB["RAM_CAPACITY"]]
        elif cat == "固態硬碟 (SSD)":
            opts = [f"Gen4 SSD {s}" for s in UPGRADE_DB["SSD_GEN4"]]
            if self.specs['support_gen5']: opts.extend([f"Gen5 SSD {s}" for s in UPGRADE_DB["SSD_GEN5"]])
        elif cat == "顯示卡 (GPU)":
            opts = PC_BUILD_DB["GPU"]
        elif cat == "電源供應器 (PSU)":
            opts = PC_BUILD_DB["PSU"]
        elif cat == "CPU 處理器":
            opts = []
            for vendor in PC_BUILD_DB["CPU"].values():
                for models in vendor.values():
                    opts.extend(models)
        elif cat == "CPU 散熱器":
            opts = PC_BUILD_DB["COOLER"]
        elif cat == "機殼":
            opts = PC_BUILD_DB["CASE"]
        elif cat == "螢幕":
            opts = self.get_monitor_options()
        elif cat == "周邊/附加商品":
            opts = PC_BUILD_DB["EXTRA"]
            
        self.upg_item.configure(values=opts)
        self.upg_item.set(opts[0])
        self.price_label.configure(text="請點擊 [🔍 查詢時價]", text_color="#ffffff")
        self.add_cart_btn.configure(state="disabled")

    def mode_build_select(self):
        self.current_fetch = None
        self.upgrade_container.pack_forget()
        self.build_container.pack_forget()
        self.build_select_container.pack(fill="x", padx=20, pady=20)
        self.repack_bottom_actions()
        
        self.mid_title.configure(text="[ 選擇設備類型 ]")
        self.search_btn.configure(state="disabled")
        self.add_cart_btn.configure(state="disabled")
        self.price_label.configure(text="")

    def start_desktop_builder(self):
        self.current_fetch = None
        self.current_mode = "BUILD_PC"
        self.build_select_container.pack_forget()
        self.build_container.pack(fill="x", padx=20, pady=10)
        self.repack_bottom_actions()
        
        self.mid_title.configure(text="[ 🖥️ 桌機配單精靈 ]")
        self.build_max_steps = 10
        self.build_step = 0
        self.build_context.clear()
        self.clear_cart()
        self.load_step_ui()

    def start_laptop_builder(self):
        self.current_fetch = None
        self.current_mode = "BUILD_LAPTOP"
        self.build_select_container.pack_forget()
        self.build_container.pack(fill="x", padx=20, pady=10)
        self.repack_bottom_actions()
        
        self.mid_title.configure(text="[ 💻 筆電 3 步驟選購精靈 ]")
        self.build_max_steps = 3
        self.build_step = 0
        self.build_context.clear()
        self.clear_cart()
        self.load_step_ui()

    def load_step_ui(self):
        self.add_cart_btn.configure(state="disabled")
        self.search_btn.configure(state="normal")
        self.build_menu_1.pack_forget()
        self.build_menu_2.pack_forget()
        
        if self.current_mode == "BUILD_PC":
            steps = ["1. CPU 陣營與型號", "2. 主機板", "3. 記憶體", "4. SSD", "5. 顯示卡", "6. 散熱器", "7. 電源", "8. 機殼", "9. 螢幕", "10. 附加選項"]
            self.step_label.configure(text=steps[self.build_step])
            
            if self.build_step == 0: 
                self.build_menu_1.pack(pady=5); self.build_menu_2.pack(pady=5)
                self.build_menu_1.configure(values=["Intel", "AMD"])
                self.build_menu_1.set("Intel")
                self.on_build_menu1_change("Intel")
            else:
                if self.build_step == 8:
                    self.build_menu_1.pack(pady=5)
                    monitor_brands = list(PC_BUILD_DB.get("MONITOR", {}).keys())
                    self.build_menu_1.configure(values=monitor_brands)
                    self.build_menu_1.set(monitor_brands[0])
                    self.on_build_menu1_change(monitor_brands[0])
                self.build_menu_2.pack(pady=5)
                if self.build_step == 1: 
                    socket = self.build_context.get("SOCKET", "LGA1700")
                    opts = PC_BUILD_DB["MOBO"].get(socket, ["無相容主板"])
                elif self.build_step == 2: 
                    socket = self.build_context.get("SOCKET", "LGA1700")
                    ddr = self.build_context.get("DDR", "DDR5")
                    opts = get_ram_options_for_build(socket, ddr)
                elif self.build_step == 3: opts = [f"Gen4 SSD {s}" for s in UPGRADE_DB["SSD_GEN4"]]
                elif self.build_step == 4: opts = PC_BUILD_DB["GPU"]
                elif self.build_step == 5: opts = PC_BUILD_DB["COOLER"]
                elif self.build_step == 6: opts = PC_BUILD_DB["PSU"]
                elif self.build_step == 7: opts = PC_BUILD_DB["CASE"]
                elif self.build_step == 8: opts = PC_BUILD_DB["MONITOR"].get(self.build_menu_1.get(), [])
                elif self.build_step == 9: opts = PC_BUILD_DB["EXTRA"]
                
                self.build_menu_2.configure(values=opts)
                self.build_menu_2.set(opts[0])
                
        elif self.current_mode == "BUILD_LAPTOP":
            steps = ["步驟 1/3: 選擇 筆電品牌", "步驟 2/3: 選擇 顯卡效能等級", "步驟 3/3: 挑選 推薦機型"]
            self.step_label.configure(text=steps[self.build_step])
            self.build_menu_2.pack(pady=5)
            
            if self.build_step == 0:
                self.build_menu_2.configure(values=LAPTOP_BRANDS)
                self.build_menu_2.set(LAPTOP_BRANDS[0])
                self.price_label.configure(text="請選擇品牌，然後直接點擊 [下一步 ➡️]", text_color="#ffffff")
                self.search_btn.configure(state="disabled")
            elif self.build_step == 1:
                self.build_menu_2.configure(values=LAPTOP_GPUS)
                self.build_menu_2.set(LAPTOP_GPUS[0])
                self.price_label.configure(text="請選擇效能等級，然後直接點擊 [下一步 ➡️]", text_color="#ffffff")
                self.search_btn.configure(state="disabled")
            elif self.build_step == 2:
                brand = self.build_context.get("BRAND", LAPTOP_BRANDS[0])
                gpu = self.build_context.get("GPU_TIER", LAPTOP_GPUS[0])
                models = get_laptop_models(brand, gpu)
                self.build_menu_2.configure(values=models)
                self.build_menu_2.set(models[0])
                self.price_label.configure(text="✨ 已為您鎖定專屬型號！請點擊 [🔍 查詢時價] 確認電商是否有現貨。", text_color="#00ffff")

    def on_build_menu1_change(self, val):
        if self.current_mode == "BUILD_PC" and self.build_step == 0:
            cpus = []
            for socket, models in PC_BUILD_DB["CPU"][val].items(): cpus.extend(models)
            self.build_menu_2.configure(values=cpus)
            self.build_menu_2.set(cpus[0])
        elif self.current_mode == "BUILD_PC" and self.build_step == 8:
            models = PC_BUILD_DB.get("MONITOR", {}).get(val, ["不需要螢幕"])
            self.build_menu_2.configure(values=models)
            self.build_menu_2.set(models[0])

    def next_step(self):
        if self.current_mode == "BUILD_PC":
            if self.build_step == 0:
                cpu = self.build_menu_2.get()
                if any(x in cpu for x in ["285", "265", "245"]):
                    self.build_context["SOCKET"] = "LGA1851"
                elif "Intel" in self.build_menu_1.get():
                    self.build_context["SOCKET"] = "LGA1700"
                elif any(x in cpu for x in ["5700", "5800", "5600", "5500"]):
                    self.build_context["SOCKET"] = "AM4"
                else:
                    self.build_context["SOCKET"] = "AM5"
            elif self.build_step == 1:
                self.build_context["DDR"] = "DDR4" if "DDR4" in self.build_menu_2.get() else "DDR5"
        elif self.current_mode == "BUILD_LAPTOP":
            if self.build_step == 0: self.build_context["BRAND"] = self.build_menu_2.get()
            elif self.build_step == 1: self.build_context["GPU_TIER"] = self.build_menu_2.get()

        if self.build_step < self.build_max_steps - 1:
            self.build_step += 1
            self.load_step_ui()
        else:
            self.price_label.configure(text="🎉 所有步驟已完成！請至右側確認最終清單。", text_color="#00ff00")

    def prev_step(self):
        if self.build_step > 0:
            self.build_step -= 1
            self.load_step_ui()

    def skip_step(self):
        self.next_step()

    def jump_to_step(self, val):
        if "步驟" in val:
            self.build_step = int(re.search(r'\d+', val).group()) - 1
            self.load_step_ui()

    # ==========================================
    # 5. 絕對嚴苛防呆搜尋引擎 (加入三段報價)
    # ==========================================

    def get_monitor_options(self):
        opts = ["不需要螢幕"]
        for brand, models in PC_BUILD_DB.get("MONITOR", {}).items():
            opts.extend([f"{brand} {model}" for model in models])
        return opts

    def open_current_link(self):
        link = None
        if self.current_fetch:
            link = self.current_fetch.get("link") or self.current_fetch.get("search_link")
        if not link:
            selected_target = self.get_selected_target()
            keyword = self.build_search_keyword(selected_target)
            link = self.platform_search_links(keyword).get("PChome 24h") if keyword else None
        if link:
            webbrowser.open(link)

    def get_selected_target(self):
        if self.current_mode == "UPGRADE":
            return self.upg_item.get()
        if self.current_mode == "BUILD_PC" and self.build_step == 8:
            return f"{self.build_menu_1.get()} {self.build_menu_2.get()}".strip()
        return self.build_menu_2.get()

    def get_manual_query(self):
        try:
            return self.manual_query_entry.get().strip()
        except Exception:
            return ""

    def build_search_keyword(self, selected_target):
        manual = self.get_manual_query()
        if manual:
            return manual
        keyword = clean_display_name(selected_target).split(" - ")[0].strip()
        return keyword

    def make_filters(self, selected_target, keyword):
        must_have = []
        reject = [
            "隨身碟", "外接硬碟", "二手", "福利品", "保護套", "保護殼", "水之鏡", "防窺片", "鏡片",
            "散熱片", "轉接卡", "貼膜", "鍵盤膜", "包膜", "螢幕保護", "保護貼",
            "綁售", "搭機", "搭購", "組合價", "套餐", "加購", "拆封", "展示品"
        ]
        target = f"{selected_target} {keyword}".upper()

        # 桌機分項嚴格排除：選 CPU 就只買 CPU，不吃主機板搭售 / C+M 套餐。
        if self.current_mode == "BUILD_PC" and self.build_step == 0:
            reject.extend(["主機板", "MAINBOARD", "MOTHERBOARD", "C+M", "超值組", "套組", "組合", "搭", "B650", "B850", "X870", "X670", "Z790", "Z890", "B760"])
            cpu_tokens = re.findall(r'(RYZEN\s?[579]\s?\d{4}X?3?D?|CORE\s?I[3579]-?\d{4,5}[A-Z]*|CORE\s?ULTRA\s?[579]\s?\d{3}[A-Z]*)', target)
            must_have.extend([t.replace(" ", "") for t in cpu_tokens[:1]])

        # 手動輸入型號時，不做太嚴格的分類過濾，避免把正確商品誤殺。
        if self.get_manual_query():
            tokens = re.findall(r'(RTX\s?\d{4}|RX\s?\d{4}\s?XT?X?|I[3579]-?\d{4,5}[A-Z]*|ULTRA\s?[579]\s?\d{3}[A-Z]*|RYZEN\s?[579]\s?\d{4}X?3?D?|DDR[45]|\d+TB|\d+GB)', target)
            must_have.extend([t.replace(" ", "") for t in tokens[:3]])
            return must_have, reject

        if self.current_mode == "BUILD_LAPTOP":
            brand_text = self.build_context.get("BRAND", "")
            gpu_tier = self.build_context.get("GPU_TIER", "")
            brand_up = brand_text.upper()
            if "ROG" in brand_up:
                must_have.append("ROG")
                reject.append("TUF")
            elif "TUF" in brand_up:
                must_have.append("TUF")
                reject.append("ROG")
            elif "MSI" in brand_up:
                must_have.append("MSI")
            elif "ACER" in brand_up or "PREDATOR" in brand_up:
                must_have.append("ACER")
            elif "LENOVO" in brand_up or "LEGION" in brand_up:
                must_have.append("LEGION")
            elif "HP" in brand_up or "OMEN" in brand_up:
                must_have.append("OMEN")
            elif "ALIENWARE" in brand_up or "DELL" in brand_up:
                must_have.append("ALIENWARE")

            gpu_label = extract_gpu_label(gpu_tier).upper()
            gpu_match = re.search(r'RTX\s?(\d{4})(\s?TI)?', gpu_label)
            if gpu_match:
                must_have.append(gpu_match.group(1))
                if gpu_match.group(2):
                    must_have.append("TI")
        else:
            words = selected_target.split()
            if words and ("GB" in words[-1].upper() or "G" in words[-1].upper() or "TB" in words[-1].upper()):
                must_have.append(words[-1].upper().replace("GB", "").replace("G", "").replace("TB", "T"))

            if "GEN4" in target:
                must_have.append("GEN4")
                reject.extend(["GEN3", "GEN5", "GEN 3", "GEN 5"])
            elif "GEN5" in target:
                must_have.append("GEN5")
                reject.extend(["GEN3", "GEN4", "GEN 3", "GEN 4"])

            if self.current_mode == "UPGRADE" and self.is_laptop and "記憶體" in self.upg_cat.get():
                must_have.append("筆")
                reject.extend(["桌上型", "U-DIMM", "UDIMM"])

            freq_match = re.search(r'DDR\d\s+(\d+)', selected_target)
            if freq_match:
                must_have.append(freq_match.group(1))

        return must_have, reject

    def product_match_score(self, name, keyword, must_have, reject):
        name_up = name.upper().replace(" ", "")
        keyword_up = keyword.upper().replace(" ", "")
        if any(r.upper().replace(" ", "") in name_up for r in reject):
            return -999
        if self.current_mode == "BUILD_PC" and self.build_step == 0:
            # CPU 查價嚴格排除任何主機板/套裝訊號。
            bad_cpu_bundle = ["主機板", "C+M", "超值組", "搭", "套餐", "套組", "B650", "B850", "X870", "X670", "Z790", "Z890", "B760"]
            if any(b.upper().replace(" ", "") in name_up for b in bad_cpu_bundle):
                return -999
        score = 0
        if keyword_up and keyword_up in name_up:
            score += 50
        for token in must_have:
            t = token.upper().replace(" ", "")
            if t and (t in name_up or t.replace("T", "TB") in name_up):
                score += 20
            elif t:
                score -= 25
        # 型號查價要重視精準度：抓 RTX/CPU/容量等共同 token。
        for token in re.findall(r'[A-Z]+|\d{3,5}|\d+TB|\d+GB', keyword_up):
            if len(token) >= 3 and token in name_up:
                score += 3
        return score

    # ==========================================
    # 5. 型號優先查價引擎
    # ==========================================
    def search_pchome_products(self, keyword):
        """PChome 24h 有公開搜尋 JSON，可取得實際價格。"""
        url = f"https://ecshweb.pchome.com.tw/search/v3.3/all/results?q={urllib.parse.quote(keyword)}&page=1&sort=sale/dc"
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=(3, 8))
        response.raise_for_status()
        data = response.json()
        items = []
        for item in data.get('prods', [])[:40]:
            name = item.get('name', '')
            price = int(item.get('price', 0) or 0)
            if not name or not price:
                continue
            prod_id = item.get('Id') or item.get('id') or ""
            link = f"https://24h.pchome.com.tw/prod/{prod_id}" if prod_id else f"https://24h.pchome.com.tw/search/q={urllib.parse.quote(keyword)}"
            items.append({"platform": "PChome 24h", "name": name, "price": price, "link": link})
        return items


    def search_momo_products(self, keyword):
        """momo 沒有穩定公開 API，這裡採輕量 HTML/JSON 文字抓取；失敗就回空陣列，不影響主流程。"""
        url = f"https://www.momoshop.com.tw/search/searchShop.jsp?keyword={urllib.parse.quote(keyword)}"
        try:
            r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=(3, 8))
            text = r.text
            items = []
            # 嘗試抓常見的 goodsName / goodsPrice 結構；網站改版時可能抓不到。
            names = re.findall(r'"goodsName"\s*:\s*"([^"]{4,120})"', text)
            prices = re.findall(r'"goodsPrice"\s*:\s*"?([0-9,]+)"?', text)
            for name, price in zip(names[:20], prices[:20]):
                price_num = int(price.replace(',', ''))
                items.append({"platform": "momo購物網", "name": name.encode('utf-8').decode('unicode_escape', errors='ignore'), "price": price_num, "link": url})
            return items
        except Exception:
            return []

    def search_yahoo_products(self, keyword):
        """Yahoo 搜尋頁面也可能改版；抓不到時回空陣列，仍保留可點搜尋連結。"""
        url = f"https://tw.buy.yahoo.com/search/product?p={urllib.parse.quote(keyword)}"
        try:
            r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=(3, 8))
            text = r.text
            items = []
            # 粗略抓取頁面中的商品名稱與價格，避免過度依賴單一平台。
            chunks = re.findall(r'"name"\s*:\s*"([^"]{4,120})".*?"price"\s*:\s*"?([0-9,]+)"?', text, flags=re.S)
            for name, price in chunks[:20]:
                try:
                    price_num = int(price.replace(',', ''))
                except Exception:
                    continue
                items.append({"platform": "Yahoo購物中心", "name": name.encode('utf-8').decode('unicode_escape', errors='ignore'), "price": price_num, "link": url})
            return items
        except Exception:
            return []

    def search_multi_platform_products(self, keyword):
        products = []
        # PChome 有較穩定 JSON，作為主來源。
        try:
            products.extend(self.search_pchome_products(keyword))
        except Exception:
            pass
        # 其他平台用輕量抓取補樣本；抓不到就只提供搜尋入口。
        products.extend(self.search_momo_products(keyword))
        products.extend(self.search_yahoo_products(keyword))
        return products

    def platform_search_links(self, keyword):
        q = urllib.parse.quote(keyword)
        return {
            "PChome 24h": f"https://24h.pchome.com.tw/search/q={q}",
            "momo購物網": f"https://www.momoshop.com.tw/search/searchShop.jsp?keyword={q}",
            "Yahoo購物中心": f"https://tw.buy.yahoo.com/search/product?p={q}",
            "蝦皮商城": f"https://shopee.tw/search?keyword={q}",
            "原價屋估價系統": "https://www.coolpc.com.tw/evaluate.php",
            "欣亞線上購物": f"https://www.sinya.com.tw/search?keyword={q}",
            "AUTOBUY 購物": f"https://www.autobuy.tw/search.php?keyword={q}",
            "良興 EcLife": f"https://www.eclife.com.tw/Search/Keyword?keyword={q}"
        }

    def is_laptop_query(self, selected_target):
        return self.current_mode == "BUILD_LAPTOP" or any(k in selected_target.upper() for k in ["ROG", "TUF", "LEGION", "OMEN", "ALIENWARE", "PREDATOR", "筆電"])

    def execute_search(self):
        if self.is_searching:
            return

        selected_target = self.get_selected_target()
        keyword = self.build_search_keyword(selected_target)

        if not selected_target or "不需要" in selected_target:
            self.price_label.configure(text="此項目已跳過，不需要查詢。", text_color="#aaaaaa")
            self.add_cart_btn.configure(state="disabled")
            self.current_fetch = None
            return

        if not keyword:
            self.price_label.configure(text="請先選擇品牌/規格，或輸入完整型號再查價。", text_color="#ffaa00")
            return

        self.current_fetch = None
        self.price_label.configure(
            text=f"⏳ 多平台型號查價中：{keyword}\n選單項目：{selected_target}",
            text_color="#cccccc"
        )
        self.set_search_busy(True)

        def task():
            try:
                must_have, reject = self.make_filters(selected_target, keyword)
                products = self.search_multi_platform_products(keyword)

                scored = []
                for item in products:
                    score = self.product_match_score(item['name'], keyword, must_have, reject)
                    # 筆電查價採嚴格模式：必須有品牌與 GPU 數字，避免 5090 筆電抓到保護貼。
                    name_up = item['name'].upper().replace(" ", "")
                    if self.is_laptop_query(selected_target):
                        gpu_need = [m for m in must_have if re.fullmatch(r'\d{4}', m)]
                        if gpu_need and not all(g in name_up for g in gpu_need):
                            score = -999
                        if "TI" in must_have and "TI" not in name_up:
                            score = -999
                        # 筆電本體通常會有 CPU/RAM/SSD/作業系統等資訊；純配件排除。
                        accessory_words = ["保護", "貼", "防窺", "鍵盤膜", "水之鏡", "包膜", "殼"]
                        if any(w in item['name'] for w in accessory_words):
                            score = -999
                    if score > 0:
                        scored.append((score, item))

                scored.sort(key=lambda x: (x[0], -x[1]['price']), reverse=True)
                valid_items = [item for score, item in scored[:10]]
                platform_links = self.platform_search_links(keyword)
                link_text = "\n".join([f"- {k}: {v}" for k, v in platform_links.items()])

                if not products:
                    result = (
                        f"❌ 目前電商缺貨 / 已售完：{keyword}\n\n"
                        "目前自動查價來源沒有回傳商品。可用下方平台連結再人工確認：\n"
                        f"{link_text}"
                    )
                    def no_product_ui(result=result, platform_links=platform_links, keyword=keyword, selected_target=selected_target):
                        self.price_label.configure(text=result, text_color="#ff4444")
                        self.current_fetch = {"step": self.build_step if self.current_mode != "UPGRADE" else selected_target, "target": selected_target, "name": keyword, "price": 0, "link": platform_links.get("PChome 24h"), "search_link": platform_links.get("PChome 24h"), "keyword": keyword}
                        self.open_link_btn.configure(state="normal")
                    self.ui_safe(no_product_ui)
                    return

                if not valid_items:
                    result = (
                        f"❌ 目前電商缺貨 / 已售完，或沒有精準對應型號：{keyword}\n\n"
                        "已排除保護貼、綁售、搭機、福利品、二手與不對應 GPU/型號的商品。\n"
                        "如果你確定有上市，請改用更短但精準的關鍵字，例如：ROG Strix G18 RTX 5070、RTX 5070 Ti、Ryzen 9 9950X3D。\n\n"
                        f"其他平台查詢連結：\n{link_text}"
                    )
                    def no_valid_ui(result=result, platform_links=platform_links, keyword=keyword, selected_target=selected_target):
                        self.price_label.configure(text=result, text_color="#ff4444")
                        self.current_fetch = {"step": self.build_step if self.current_mode != "UPGRADE" else selected_target, "target": selected_target, "name": keyword, "price": 0, "link": platform_links.get("PChome 24h"), "search_link": platform_links.get("PChome 24h"), "keyword": keyword}
                        self.open_link_btn.configure(state="normal")
                    self.ui_safe(no_valid_ui)
                    return

                prices = [item['price'] for item in valid_items]
                sample_item = valid_items[0]
                name = sample_item['name']
                this_price = sample_item['price']
                min_price = min(prices)
                avg_price = int(sum(prices) / len(prices))
                avg_text = f"NT$ {avg_price:,}" if len(valid_items) > 1 else "樣本不足"

                top_list = "\n".join([
                    f"{idx+1}. [{item['platform']}] {item['name'][:42]} / NT$ {item['price']:,}"
                    for idx, item in enumerate(valid_items[:5])
                ])
                result = (
                    f"✅ 多平台精準型號查價完成！\n查詢：{keyword}\n\n"
                    f"最佳匹配：\n[{sample_item['platform']}] {name}\n\n"
                    f"🏷️ 本商品定價: NT$ {this_price:,}\n"
                    f"📉 市場最低價: NT$ {min_price:,}\n"
                    f"📊 市場均價: {avg_text}\n\n"
                    f"前五筆候選：\n{top_list}\n\n"
                    "其他平台搜尋入口：\n"
                    f"{link_text}"
                )
                fetch_payload = {
                    "step": self.build_step if self.current_mode != "UPGRADE" else selected_target,
                    "target": selected_target,
                    "name": name,
                    "price": this_price,
                    "link": sample_item['link'],
                    "search_link": platform_links.get("PChome 24h"),
                    "keyword": keyword
                }

                def success_ui():
                    self.price_label.configure(text=result, text_color="#ffffff")
                    self.current_fetch = fetch_payload
                    self.add_cart_btn.configure(state="normal")
                    self.open_link_btn.configure(state="normal")

                self.ui_safe(success_ui)

            except requests.exceptions.Timeout:
                self.ui_safe(lambda: self.price_label.configure(text="⚠️ 查詢逾時：電商 API 回應太慢，請稍後再試。", text_color="#ff4444"))
            except requests.exceptions.RequestException as e:
                msg = str(e)
                self.ui_safe(lambda msg=msg: self.price_label.configure(text=f"⚠️ 網路錯誤：{msg}", text_color="#ff4444"))
            except Exception as e:
                msg = str(e)
                self.ui_safe(lambda msg=msg: self.price_label.configure(text=f"⚠️ 程式錯誤：{msg}", text_color="#ff4444"))
            finally:
                self.ui_safe(lambda: self.set_search_busy(False))

        threading.Thread(target=task, daemon=True).start()

    # ==========================================
    # 6. 購物車與購買連結系統
    # ==========================================
    def add_to_cart(self):
        if self.current_fetch and self.current_fetch.get("price", 0) <= 0:
            self.price_label.configure(text="此商品目前缺貨 / 未取得有效價格，不能加入清單。", text_color="#ffaa00")
            return
        if self.current_fetch:
            self.cart_items[self.current_fetch["step"]] = self.current_fetch
            self.refresh_cart_ui()
            self.add_cart_btn.configure(state="disabled")
            self.price_label.configure(text="✅ 已成功加入清單！請繼續下一步。", text_color="#00ff00")

    def clear_cart(self):
        self.cart_items.clear()
        self.refresh_cart_ui()

    def refresh_cart_ui(self):
        self.cart_textbox.configure(state="normal")
        self.cart_textbox.delete("0.0", "end")
        
        total = 0
        jump_options = ["-- 返回特定步驟修改 --"]
        
        if not self.cart_items:
            self.cart_textbox.insert("end", "🛒 購物車目前空空如也...\n")
        else:
            for k, v in self.cart_items.items():
                total += v['price']
                step_name = f"步驟 {k+1}" if isinstance(k, int) else "局部升級"
                short_name = v['name'][:25] + "..." if len(v['name']) > 25 else v['name']
                self.cart_textbox.insert("end", f"[{step_name}] {v['target']}\n ↳ {short_name}\n NT$ {v['price']:,}\n\n")
                if isinstance(k, int): jump_options.append(f"返回修改: {step_name}")
                
        self.cart_textbox.configure(state="disabled")
        self.total_cost_label.configure(text=f"總計估價: NT$ {total:,}")
        self.jump_menu.configure(values=jump_options)
        self.jump_menu.set(jump_options[0])

    def generate_links(self):
        if not self.cart_items:
            self.price_label.configure(text="⚠️ 購物車是空的，無法生成連結！", text_color="#ff4444")
            return
            
        link_window = ctk.CTkToplevel(self)
        link_window.title("🛍️ 結帳與官方資訊連結")
        link_window.geometry("980x720")
        link_window.attributes("-topmost", True)
        
        ctk.CTkLabel(link_window, text="複製下方連結至瀏覽器即可購買或查看官方資訊", font=ctk.CTkFont(size=18, weight="bold"), text_color="#00ff00").pack(pady=15)
        
        link_textbox = ctk.CTkTextbox(link_window, font=ctk.CTkFont(size=14), wrap="word")
        link_textbox.pack(fill="both", expand=True, padx=20, pady=10)
        
        link_textbox.insert("end", "【🛒 PChome 電商直達車】\n")
        for k, v in self.cart_items.items():
            link_textbox.insert("end", f"▪ {v['name']}\n  {v['link']}\n\n")
            
        link_textbox.insert("end", "----------------------------------------\n【🌐 原廠官方網站參考】\n")
        
        brands = {
            "ROG": "https://rog.asus.com/tw/",
            "TUF": "https://www.asus.com/tw/displays-desktops/all-series/filter?Series=TUF-Gaming",
            "ASUS": "https://www.asus.com/tw/",
            "MSI": "https://tw.msi.com/",
            "Acer": "https://www.acer.com/tw-zh/",
            "GIGABYTE": "https://www.gigabyte.com/tw",
            "Lenovo": "https://www.lenovo.com/tw/zh/"
        }
        
        found_brands = set()
        for v in self.cart_items.values():
            for b in brands.keys():
                if b in v['target'] or b in v['name']:
                    found_brands.add(b)
                    
        for b in found_brands:
            link_textbox.insert("end", f"▪ {b} 官方網站: {brands[b]}\n")
            
        link_textbox.configure(state="disabled")

# ==========================================================
# v20 強化補丁：全步驟品牌→型號、更多選項、Gen5 SSD、多頁 PChome 查價、CPU 單品優先
# ==========================================================

BRAND_MODEL_DB = {
    "CPU": {
        "Intel": PC_BUILD_DB["CPU"]["Intel"].get("LGA1851", []) + PC_BUILD_DB["CPU"]["Intel"].get("LGA1700", []),
        "AMD": PC_BUILD_DB["CPU"]["AMD"].get("AM5", []) + PC_BUILD_DB["CPU"]["AMD"].get("AM4", []),
    },
    "MOBO": {
        "ASUS": [], "MSI": [], "GIGABYTE": [], "ASRock": []
    },
    "RAM": {
        "Kingston Fury": [], "G.SKILL": [], "Corsair": [], "ADATA XPG": [], "TeamGroup T-Force": [], "Crucial": []
    },
    "SSD": {
        "Samsung": ["Samsung 990 PRO Gen4 SSD 1TB", "Samsung 990 PRO Gen4 SSD 2TB", "Samsung 990 PRO Gen4 SSD 4TB", "Samsung 9100 PRO Gen5 SSD 1TB", "Samsung 9100 PRO Gen5 SSD 2TB", "Samsung 9100 PRO Gen5 SSD 4TB"],
        "WD_BLACK": ["WD_BLACK SN850X Gen4 SSD 1TB", "WD_BLACK SN850X Gen4 SSD 2TB", "WD_BLACK SN850X Gen4 SSD 4TB", "WD_BLACK SN8100 Gen5 SSD 1TB", "WD_BLACK SN8100 Gen5 SSD 2TB", "WD_BLACK SN8100 Gen5 SSD 4TB"],
        "Crucial": ["Crucial T500 Gen4 SSD 1TB", "Crucial T500 Gen4 SSD 2TB", "Crucial P310 Gen4 SSD 2TB", "Crucial T705 Gen5 SSD 1TB", "Crucial T705 Gen5 SSD 2TB", "Crucial T705 Gen5 SSD 4TB"],
        "Kingston": ["Kingston KC3000 Gen4 SSD 1TB", "Kingston KC3000 Gen4 SSD 2TB", "Kingston FURY Renegade Gen4 SSD 2TB", "Kingston FURY Renegade G5 Gen5 SSD 1TB", "Kingston FURY Renegade G5 Gen5 SSD 2TB"],
        "ADATA XPG": ["XPG GAMMIX S70 Blade Gen4 SSD 1TB", "XPG GAMMIX S70 Blade Gen4 SSD 2TB", "XPG MARS 980 Gen5 SSD 1TB", "XPG MARS 980 Gen5 SSD 2TB"],
        "Seagate": ["Seagate FireCuda 530 Gen4 SSD 1TB", "Seagate FireCuda 530 Gen4 SSD 2TB", "Seagate FireCuda 540 Gen5 SSD 1TB", "Seagate FireCuda 540 Gen5 SSD 2TB"],
        "TeamGroup": ["TeamGroup MP44 Gen4 SSD 1TB", "TeamGroup MP44 Gen4 SSD 2TB", "TeamGroup GE PRO Gen5 SSD 1TB", "TeamGroup GE PRO Gen5 SSD 2TB"],
        "Solidigm": ["Solidigm P44 Pro Gen4 SSD 1TB", "Solidigm P44 Pro Gen4 SSD 2TB"]
    },
    "GPU": {
        "ASUS": [x for x in PC_BUILD_DB["GPU"] if "ASUS" in x or x.startswith("RTX")][:] + ["ASUS ROG Astral RTX 5090 OC 32G", "ASUS TUF RTX 5070 Ti OC 16G", "ASUS PRIME RTX 5070 12G"],
        "MSI": [x for x in PC_BUILD_DB["GPU"] if "MSI" in x] + ["MSI RTX 5090 GAMING TRIO 32G", "MSI RTX 5080 VENTUS 3X 16G", "MSI RTX 5070 Ti SHADOW 3X 16G"],
        "GIGABYTE": [x for x in PC_BUILD_DB["GPU"] if "GIGABYTE" in x] + ["GIGABYTE RTX 5090 WINDFORCE 32G", "GIGABYTE RTX 5080 AERO OC 16G", "GIGABYTE RTX 5070 Ti GAMING OC 16G"],
        "ZOTAC": ["ZOTAC RTX 5090 SOLID OC 32G", "ZOTAC RTX 5080 SOLID OC 16G", "ZOTAC RTX 5070 Ti SOLID 16G", "ZOTAC RTX 5070 SOLID 12G", "ZOTAC RTX 5060 Ti Twin Edge 16G"],
        "INNO3D": ["INNO3D RTX 5070 Ti X3 16G", "INNO3D RTX 5070 TWIN X2 12G", "INNO3D RTX 5060 Ti TWIN X2 16G"],
        "SAPPHIRE": ["SAPPHIRE NITRO+ RX 9070 XT 16G", "SAPPHIRE PULSE RX 9070 XT 16G", "SAPPHIRE PULSE RX 9060 XT 16G", "SAPPHIRE PULSE RX 7900 XT 20G"],
        "PowerColor": ["PowerColor Red Devil RX 9070 XT 16G", "PowerColor Hellhound RX 9070 XT 16G", "PowerColor Fighter RX 9060 XT 16G"],
        "Intel": ["Intel Arc B580 12G", "Intel Arc A770 16G"]
    },
    "COOLER": {
        "ASUS ROG": ["ROG Ryujin III 360 ARGB 水冷", "ROG Ryuo III 360 ARGB 水冷", "ROG Strix LC III 360 ARGB 水冷"],
        "NZXT": ["NZXT Kraken Elite 360 RGB 水冷", "NZXT Kraken 360 RGB 水冷", "NZXT Kraken 240 RGB 水冷"],
        "Corsair": ["Corsair iCUE H150i Elite 水冷", "Corsair iCUE H100i Elite 水冷", "Corsair A115 雙塔風冷"],
        "Thermalright 利民": ["利民 Phantom Spirit 120 EVO 風冷", "利民 Peerless Assassin 120 SE 風冷", "利民 Frozen Prism 360 水冷", "Thermalright Assassin X 120 風冷"],
        "Noctua 貓頭鷹": ["貓頭鷹 NH-D15 G2 雙塔風冷", "貓頭鷹 NH-U12A 風冷", "貓頭鷹 NH-L9x65 風冷"],
        "Arctic": ["Arctic Liquid Freezer III 360 水冷", "Arctic Liquid Freezer III 280 水冷", "Arctic Freezer 36 風冷"],
        "DeepCool": ["DeepCool LT720 水冷", "DeepCool LS720 水冷", "DeepCool AK620 風冷"]
    },
    "PSU": {
        "ASUS ROG": ["ROG THOR 1600W Titanium", "ROG THOR 1200W Platinum II", "ROG STRIX 1000W Gold Aura", "ROG STRIX 850W Gold Aura"],
        "Seasonic 海韻": ["海韻 PRIME TX-1300 Titanium", "海韻 VERTEX GX-1200 Gold", "海韻 VERTEX GX-1000 Gold", "海韻 FOCUS GX-850 ATX3.0 Gold", "海韻 FOCUS GX-750 Gold"],
        "Corsair": ["Corsair RM1200x SHIFT Gold", "Corsair RM1000x Gold", "Corsair RM850e ATX3.0 Gold", "Corsair SF1000 SFX Platinum"],
        "FSP 全漢": ["FSP Hydro G Pro 1000W Gold", "FSP VITA GM 850W Gold", "FSP Hydro PTM X PRO 1200W Platinum"],
        "MSI": ["MSI MEG Ai1300P PCIE5 1300W Platinum", "MSI MPG A1000G PCIE5 1000W Gold", "MSI MPG A850G PCIE5 850W Gold", "MSI MAG A750GL PCIE5 750W Gold"],
        "be quiet!": ["be quiet! Straight Power 12 1000W Platinum", "be quiet! Pure Power 12 M 850W", "be quiet! Dark Power 13 1000W Titanium"],
        "Cooler Master 酷碼": ["酷碼 MWE Gold V3 850W", "酷碼 XG Plus Platinum 1000W", "酷碼 V SFX Platinum 1100W"]
    },
    "CASE": {
        "ASUS ROG": ["ROG Hyperion GR701", "ROG Strix Helios", "ROG Z11", "華碩 A21"],
        "Fractal Design": ["Fractal Design North XL", "Fractal Design North", "Fractal Design Meshify 2", "Fractal Design Pop Air", "Fractal Design Terra"],
        "Lian Li 聯力": ["Lian Li O11 Dynamic EVO RGB", "Lian Li LANCOOL III", "聯力 LANCOOL 216", "Lian Li A3-mATX", "Lian Li O11 Vision"],
        "NZXT": ["NZXT H9 Flow", "NZXT H6 Flow", "NZXT H7 Flow", "NZXT H5 Flow"],
        "Corsair": ["Corsair 5000D Airflow", "Corsair 4000D Airflow", "Corsair 6500X", "Corsair 2500D Airflow"],
        "Montech 君主": ["Montech KING 95 PRO", "Montech AIR 903 MAX", "Montech XR", "Montech SKY TWO"],
        "Cooler Master 酷碼": ["酷碼 TD500 Mesh V2", "酷碼 NR200P V2", "Cooler Master HAF 700", "Cooler Master QUBE 500"],
        "Antec": ["Antec C8", "Antec Performance 1 FT", "Antec CX700 RGB"]
    },
    "MONITOR": PC_BUILD_DB.get("MONITOR", {}),
    "EXTRA": {
        "作業系統/軟體": ["Windows 11 家用彩盒版", "Windows 11 專業彩盒版", "Windows 11 家用隨機版", "Windows 11 專業隨機版", "Microsoft 365 個人版"],
        "傳統硬碟 HDD": ["WD Black 4TB HDD", "WD Red Plus 8TB HDD", "Seagate IronWolf 8TB HDD", "Seagate Exos 16TB HDD"],
        "網卡/擴充卡": ["Intel AX210 Wi-Fi 6E PCIe 無線網卡", "TP-Link Archer TXE75E Wi-Fi 6E 網卡", "Wi-Fi 7 PCIe 無線網卡", "2.5GbE PCIe 網卡", "USB-C 擴充卡"],
        "鍵盤": ["Logitech G Pro X TKL 鍵盤", "Razer BlackWidow V4 鍵盤", "ROG Azoth 鍵盤", "Keychron Q1 HE 鍵盤", "Wooting 60HE+ 鍵盤", "SteelSeries Apex Pro TKL 鍵盤"],
        "滑鼠": ["Logitech G Pro X Superlight 2 滑鼠", "Razer Viper V3 Pro 滑鼠", "ROG Harpe Ace 滑鼠", "Logitech MX Master 3S 滑鼠", "Razer DeathAdder V3 Pro 滑鼠", "Logitech G502 X PLUS 滑鼠"],
        "耳機/麥克風": ["HyperX Cloud III 耳機", "SteelSeries Arctis Nova 7 耳機", "ROG Delta II 耳機", "Blue Yeti 麥克風", "Shure MV7+ 麥克風", "Elgato Wave:3 麥克風"],
        "直播/影音": ["Elgato Stream Deck", "Elgato HD60 X 擷取卡", "Elgato 4K X 擷取卡", "羅技 Brio 4K 網路攝影機", "Creative Sound Blaster X4 外接音效卡"],
        "供電/支架/線材": ["APC 1000VA UPS 不斷電系統", "APC 1500VA UPS 不斷電系統", "CyberPower 1000VA UPS 不斷電系統", "ROG 顯卡支撐架", "Lian Li Strimer RGB 延長線", "ARGB 風扇 3入組"],
        "不需要": ["不需要附加商品"]
    }
}

# 依主機板資料自動拆品牌，並補更多常見板子。
for socket_name, boards in PC_BUILD_DB.get("MOBO", {}).items():
    for b in boards:
        brand = "ASUS" if "ASUS" in b else "MSI" if "MSI" in b else "GIGABYTE" if "GIGABYTE" in b else "ASRock" if "ASROCK" in b.upper() else "其他"
        BRAND_MODEL_DB.setdefault("MOBO", {}).setdefault(brand, []).append(b)
for b in [
    "[ASRock] X870E Taichi (DDR5)", "[ASRock] X870 Steel Legend WiFi (DDR5)", "[ASRock] B850 Steel Legend WiFi (DDR5)",
    "[ASRock] B650M Pro RS WiFi (DDR5)", "[ASRock] Z890 Taichi AQUA (DDR5)", "[ASRock] Z890 Steel Legend WiFi (DDR5)",
    "[ASRock] B760M Steel Legend WiFi (DDR5)", "[ASRock] B550M Steel Legend (DDR4)"
]:
    BRAND_MODEL_DB["MOBO"].setdefault("ASRock", []).append(b)


def _uniq(seq):
    out = []
    seen = set()
    for x in seq:
        if x and x not in seen:
            out.append(x); seen.add(x)
    return out
for _cat, _brands in BRAND_MODEL_DB.items():
    if isinstance(_brands, dict):
        for _b in list(_brands.keys()):
            _brands[_b] = _uniq(_brands[_b])


def v20_ddr_freqs(socket, ddr):
    if ddr == "DDR4" or socket == "AM4":
        return ["3200", "3600"]
    if socket == "AM5":
        return ["5200", "5600", "6000", "6400"]
    if socket == "LGA1851":
        return ["5600", "6000", "6400", "7200", "7600", "8000"]
    return ["4800", "5200", "5600", "6000", "6400", "7200"]


def v20_ram_models(socket, ddr, brand):
    freqs = v20_ddr_freqs(socket, ddr)
    capacities = ["8G", "16G", "24G", "32G", "48G", "64G", "96G"] if ddr == "DDR5" else ["8G", "16G", "32G", "64G"]
    names = []
    for f in freqs:
        for c in capacities:
            if brand == "G.SKILL":
                series = "Trident Z5 Neo" if ddr == "DDR5" and socket == "AM5" else "Ripjaws S5" if ddr == "DDR5" else "Ripjaws V"
            elif brand == "Kingston Fury":
                series = "Beast"
            elif brand == "Corsair":
                series = "Vengeance"
            elif brand == "ADATA XPG":
                series = "Lancer Blade" if ddr == "DDR5" else "D50"
            elif brand == "TeamGroup T-Force":
                series = "Delta RGB"
            else:
                series = "Pro"
            names.append(f"{brand} {series} {ddr} {f} {c}")
    return names


def v20_socket_from_cpu(cpu, vendor):
    if any(x in cpu for x in ["285", "265", "245", "235", "225"]): return "LGA1851"
    if vendor == "Intel": return "LGA1700"
    if any(x in cpu for x in ["5900", "5800", "5700", "5600", "5500", "4600"]): return "AM4"
    return "AM5"


def v20_component_key(app):
    if app.current_mode == "BUILD_PC":
        return ["CPU", "MOBO", "RAM", "SSD", "GPU", "COOLER", "PSU", "CASE", "MONITOR", "EXTRA"][app.build_step]
    return ""


def v20_get_brands_for_step(app):
    key = v20_component_key(app)
    if key == "MOBO":
        socket = app.build_context.get("SOCKET", "AM5")
        brands = []
        for b, models in BRAND_MODEL_DB["MOBO"].items():
            if any(socket in m or (socket == "AM5" and any(chip in m for chip in ["X870", "B850", "B650", "X670"])) or (socket == "LGA1700" and any(chip in m for chip in ["Z790", "B760"])) or (socket == "LGA1851" and "Z890" in m) or (socket == "AM4" and "B550" in m) for m in models):
                brands.append(b)
        return brands or list(BRAND_MODEL_DB["MOBO"].keys())
    if key == "RAM": return list(BRAND_MODEL_DB["RAM"].keys())
    if key == "SSD": return list(BRAND_MODEL_DB["SSD"].keys())
    if key in BRAND_MODEL_DB and isinstance(BRAND_MODEL_DB[key], dict): return list(BRAND_MODEL_DB[key].keys())
    return []


def v20_get_models_for_step(app, brand):
    key = v20_component_key(app)
    if key == "CPU": return BRAND_MODEL_DB["CPU"].get(brand, [])
    if key == "MOBO":
        socket = app.build_context.get("SOCKET", "AM5")
        models = BRAND_MODEL_DB["MOBO"].get(brand, [])
        def ok(m):
            mu = m.upper()
            if socket == "AM5": return any(chip in mu for chip in ["X870", "B850", "B650", "X670"])
            if socket == "AM4": return "B550" in mu or "X570" in mu
            if socket == "LGA1851": return "Z890" in mu or "B860" in mu
            if socket == "LGA1700": return "Z790" in mu or "B760" in mu or "H610" in mu
            return True
        return [m for m in models if ok(m)] or models
    if key == "RAM":
        socket = app.build_context.get("SOCKET", "AM5")
        ddr = app.build_context.get("DDR", "DDR5")
        return v20_ram_models(socket, ddr, brand)
    if key == "SSD":
        return BRAND_MODEL_DB["SSD"].get(brand, [])
    if key in BRAND_MODEL_DB:
        return BRAND_MODEL_DB[key].get(brand, [])
    return ["請選擇"]


def v20_load_step_ui(self):
    self.add_cart_btn.configure(state="disabled")
    self.search_btn.configure(state="normal")
    self.open_link_btn.configure(state="disabled")
    self.current_fetch = None
    self.build_menu_1.pack_forget(); self.build_menu_2.pack_forget()
    if self.current_mode == "BUILD_PC":
        steps = ["1. CPU 品牌與型號", "2. 主機板品牌與型號", "3. 記憶體品牌 / 頻率 / 容量", "4. SSD 品牌與型號", "5. 顯示卡品牌與型號", "6. 散熱器品牌與型號", "7. 電源品牌與瓦數", "8. 機殼品牌與型號", "9. 螢幕品牌與型號", "10. 附加商品分類與型號"]
        self.step_label.configure(text=steps[self.build_step])
        self.build_menu_1.pack(pady=5); self.build_menu_2.pack(pady=5)
        brands = v20_get_brands_for_step(self)
        if not brands: brands = ["請選擇"]
        self.build_menu_1.configure(values=brands)
        self.build_menu_1.set(brands[0])
        self.on_build_menu1_change(brands[0])
        self.price_label.configure(text="已改成每一步先選品牌/分類，再選型號；可直接查價或輸入更精準關鍵字。", text_color="#ffffff")
    elif self.current_mode == "BUILD_LAPTOP":
        steps = ["步驟 1/3: 選擇筆電品牌", "步驟 2/3: 選擇顯卡效能等級", "步驟 3/3: 挑選推薦機型"]
        self.step_label.configure(text=steps[self.build_step])
        self.build_menu_2.pack(pady=5)
        if self.build_step == 0:
            self.build_menu_2.configure(values=LAPTOP_BRANDS); self.build_menu_2.set(LAPTOP_BRANDS[0])
            self.price_label.configure(text="請選擇品牌，然後點下一步。", text_color="#ffffff")
            self.search_btn.configure(state="disabled")
        elif self.build_step == 1:
            self.build_menu_2.configure(values=LAPTOP_GPUS); self.build_menu_2.set(LAPTOP_GPUS[0])
            self.price_label.configure(text="請選擇 GPU 等級，然後點下一步。", text_color="#ffffff")
            self.search_btn.configure(state="disabled")
        else:
            brand = self.build_context.get("BRAND", LAPTOP_BRANDS[0]); gpu = self.build_context.get("GPU_TIER", LAPTOP_GPUS[0])
            models = get_laptop_models(brand, gpu)
            self.build_menu_2.configure(values=models); self.build_menu_2.set(models[0])
            self.price_label.configure(text="請查詢時價；若找不到，可手動輸入完整型號。", text_color="#00ffff")


def v20_on_build_menu1_change(self, val):
    if self.current_mode == "BUILD_PC":
        models = v20_get_models_for_step(self, val)
        if not models: models = ["請選擇"]
        self.build_menu_2.configure(values=models)
        self.build_menu_2.set(models[0])
    elif self.current_mode == "BUILD_LAPTOP":
        pass


def v20_next_step(self):
    if self.current_mode == "BUILD_PC":
        key = v20_component_key(self)
        if self.build_step == 0:
            self.build_context["CPU_VENDOR"] = self.build_menu_1.get()
            self.build_context["CPU"] = self.build_menu_2.get()
            self.build_context["SOCKET"] = v20_socket_from_cpu(self.build_menu_2.get(), self.build_menu_1.get())
        elif self.build_step == 1:
            self.build_context["MOBO"] = self.build_menu_2.get()
            self.build_context["DDR"] = "DDR4" if "DDR4" in self.build_menu_2.get() else "DDR5"
        elif self.build_step == 2:
            self.build_context["RAM"] = self.build_menu_2.get()
    elif self.current_mode == "BUILD_LAPTOP":
        if self.build_step == 0: self.build_context["BRAND"] = self.build_menu_2.get()
        elif self.build_step == 1: self.build_context["GPU_TIER"] = self.build_menu_2.get()
    if self.build_step < self.build_max_steps - 1:
        self.build_step += 1
        self.load_step_ui()
    else:
        self.price_label.configure(text="🎉 所有步驟已完成！請至右側確認最終清單。", text_color="#00ff00")


def v20_get_selected_target(self):
    if self.current_mode == "UPGRADE":
        return self.upg_item.get()
    if self.current_mode == "BUILD_PC":
        b = self.build_menu_1.get() if hasattr(self, "build_menu_1") else ""
        m = self.build_menu_2.get() if hasattr(self, "build_menu_2") else ""
        return f"{b} {m}".strip() if b and b not in ["請選擇", "不需要"] else m
    return self.build_menu_2.get()


def v20_build_search_keyword(self, selected_target):
    manual = self.get_manual_query()
    if manual: return manual
    s = clean_display_name(selected_target).strip()
    # 避免 CPU 查成「AMD Ryzen...」也可以，但保留品牌詞能提升搜尋。
    s = re.sub(r'\[(ASUS|MSI|GIGABYTE|ASRock)\]\s*', r'\1 ', s, flags=re.I)
    return s


def v20_component_from_current(self):
    if self.current_mode == "BUILD_PC":
        return v20_component_key(self)
    if self.current_mode == "UPGRADE":
        cat = self.upg_cat.get() if hasattr(self, "upg_cat") else ""
        if "CPU" in cat: return "CPU"
        if "SSD" in cat: return "SSD"
        if "RAM" in cat or "記憶體" in cat: return "RAM"
        if "GPU" in cat or "顯示卡" in cat: return "GPU"
        if "PSU" in cat or "電源" in cat: return "PSU"
        if "散熱" in cat: return "COOLER"
        if "機殼" in cat: return "CASE"
        if "螢幕" in cat: return "MONITOR"
    if self.current_mode == "BUILD_LAPTOP": return "LAPTOP"
    return ""


def v20_make_filters(self, selected_target, keyword):
    must_have = []
    reject = ["隨身碟", "外接硬碟", "二手", "福利品", "保護套", "保護殼", "水之鏡", "防窺片", "鏡片", "貼膜", "鍵盤膜", "包膜", "螢幕保護", "保護貼", "拆封", "展示品"]
    component = v20_component_from_current(self)
    target = f"{selected_target} {keyword}".upper()
    # CPU 單品：只排除明確板U/套裝，不排除「代理商貨」等正常字眼。
    if component == "CPU":
        reject.extend(["主機板", "MAINBOARD", "MOTHERBOARD", "C+M", "板U", "板+U", "超值組", "套組", "套餐", "組合", "搭售", "搭購", "B650", "B850", "X870", "X670", "Z790", "Z890", "B760"])
        m = re.search(r'(9950X3D|9950X|9900X|9800X3D|9700X|7800X3D|7700X|7600X|7500F|14900K|14900KF|14700K|14700KF|14600K|14400F|285K|265K|245K)', target.replace(" ", ""))
        if m: must_have.append(m.group(1))
    elif component == "SSD":
        reject.extend(["外接", "硬碟盒", "轉接", "散熱片", "隨身碟"])
        if "GEN5" in target or "PCIE5" in target or "PCI-E5" in target:
            must_have.append("GEN5")
            reject.extend(["GEN3", "GEN 3"])
        elif "GEN4" in target or "PCIE4" in target or "PCI-E4" in target:
            must_have.append("GEN4")
            reject.extend(["GEN3", "GEN 3"])
        cap = re.search(r'(\d+)\s*(TB|GB)', target)
        if cap: must_have.append(cap.group(1) + ("T" if cap.group(2)=="TB" else "G"))
    elif component == "RAM":
        reject.extend(["筆電" if self.current_mode == "BUILD_PC" else "桌上型", "U-DIMM" if self.current_mode == "BUILD_LAPTOP" else "SO-DIMM"])
        m = re.search(r'(DDR[45])\s*(\d{4})?\s*(\d+G)?', target)
        if m:
            must_have.append(m.group(1))
            if m.group(2): must_have.append(m.group(2))
            if m.group(3): must_have.append(m.group(3))
    elif component == "LAPTOP":
        brand_text = self.build_context.get("BRAND", "").upper()
        if "ROG" in brand_text: must_have.append("ROG"); reject.append("TUF")
        elif "TUF" in brand_text: must_have.append("TUF"); reject.append("ROG")
        for token in ["5090", "5080", "5070", "5060", "4090", "4080", "4070", "4060"]:
            if token in target: must_have.append(token)
        if "TI" in target: must_have.append("TI")
        reject.extend(["保護", "貼", "防窺", "鍵盤膜", "水之鏡", "包膜", "殼"])
    else:
        for token in re.findall(r'(RTX\s?\d{4}\s?TI|RTX\s?\d{4}|RX\s?\d{4}\s?XT?X?|DDR[45]|\d+TB|\d+GB|\d+W|\d{3,4}HZ|\dK)', target):
            must_have.append(token.replace(" ", ""))
    return _uniq(must_have), _uniq(reject)


def v20_product_match_score(self, name, keyword, must_have, reject):
    name_up = name.upper().replace(" ", "")
    keyword_up = keyword.upper().replace(" ", "")
    if any(r.upper().replace(" ", "") in name_up for r in reject):
        return -999
    component = v20_component_from_current(self)
    if component == "CPU":
        # CPU 頁嚴格不吃板U組合，但允許「代理商貨 / 盒裝 / 原廠」單品。
        bad = ["主機板", "MAINBOARD", "MOTHERBOARD", "C+M", "板U", "板+U", "超值組", "套組", "套餐", "組合", "搭售", "搭購", "B650", "B850", "X870", "X670", "Z790", "Z890", "B760"]
        if any(x.upper().replace(" ", "") in name_up for x in bad): return -999
    score = 0
    if keyword_up and keyword_up in name_up: score += 70
    # CPU 只要精準型號存在就給高分，解決網站有貨卻被誤判沒貨。
    if component == "CPU":
        for m in re.findall(r'(9950X3D|9950X|9900X|9800X3D|9700X|7800X3D|7700X|7600X|7500F|14900K|14900KF|14700K|14700KF|14600K|14400F|285K|265K|245K)', keyword_up):
            if m in name_up: score += 90
    for token in must_have:
        t = token.upper().replace(" ", "")
        alt = t.replace("T", "TB") if re.fullmatch(r'\d+T', t) else t.replace("G", "GB") if re.fullmatch(r'\d+G', t) else t
        if t and (t in name_up or alt in name_up): score += 25
        elif t: score -= 10
    for token in re.findall(r'[A-Z]+|\d{3,5}|\d+TB|\d+GB', keyword_up):
        if len(token) >= 3 and token in name_up: score += 3
    return score


def v20_search_pchome_products(self, keyword):
    """多頁 PChome 搜尋；避免正確商品在第 2 頁後被漏掉。"""
    queries = [keyword]
    compact = keyword.replace("Ryzen 9", "Ryzen9").replace("Ryzen 7", "Ryzen7").replace("Core i", "i")
    if compact != keyword: queries.append(compact)
    m = re.search(r'(9950X3D|9950X|9900X|9800X3D|7800X3D|14900K|14700K|285K|265K|245K)', keyword.upper().replace(" ", ""))
    if m: queries.append(m.group(1))
    seen = set(); items = []
    for q0 in _uniq(queries):
        for page in range(1, 4):
            url = f"https://ecshweb.pchome.com.tw/search/v3.3/all/results?q={urllib.parse.quote(q0)}&page={page}&sort=sale/dc"
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=(3, 8))
            response.raise_for_status()
            data = response.json()
            for item in data.get('prods', [])[:80]:
                name = item.get('name', '')
                price = int(item.get('price', 0) or 0)
                prod_id = item.get('Id') or item.get('id') or ""
                if not name or not price or (prod_id, name) in seen: continue
                seen.add((prod_id, name))
                link = f"https://24h.pchome.com.tw/prod/{prod_id}" if prod_id else f"https://24h.pchome.com.tw/search/q={urllib.parse.quote(q0)}"
                items.append({"platform": "PChome 24h", "name": name, "price": price, "link": link})
    return items


def v20_update_upg_options(self, cat):
    # 局部升級也補 Gen5 SSD 與更多型號；仍保留單選單，使用者可用自訂關鍵字更精準。
    opts = []
    self.search_keywords.clear()
    if cat == "記憶體 (RAM)":
        freq = "5600" if self.specs['support_gen5'] else "3200"
        opts = [f"{self.specs['ram_type']} {freq} {s}" for s in UPGRADE_DB["RAM_CAPACITY"]]
    elif cat == "固態硬碟 (SSD)":
        opts = []
        for models in BRAND_MODEL_DB["SSD"].values(): opts.extend(models)
        opts.extend([f"Gen4 SSD {s}" for s in UPGRADE_DB["SSD_GEN4"]] + [f"Gen5 SSD {s}" for s in UPGRADE_DB["SSD_GEN5"]])
    elif cat == "顯示卡 (GPU)":
        opts = [m for models in BRAND_MODEL_DB["GPU"].values() for m in models]
    elif cat == "電源供應器 (PSU)":
        opts = [m for models in BRAND_MODEL_DB["PSU"].values() for m in models]
    elif cat == "CPU 處理器":
        opts = [m for models in BRAND_MODEL_DB["CPU"].values() for m in models]
    elif cat == "CPU 散熱器":
        opts = [m for models in BRAND_MODEL_DB["COOLER"].values() for m in models]
    elif cat == "機殼":
        opts = [m for models in BRAND_MODEL_DB["CASE"].values() for m in models]
    elif cat == "螢幕":
        opts = self.get_monitor_options()
    elif cat == "周邊/附加商品":
        opts = [m for models in BRAND_MODEL_DB["EXTRA"].values() for m in models]
    opts = _uniq(opts) or ["請選擇"]
    self.upg_item.configure(values=opts)
    self.upg_item.set(opts[0])
    self.price_label.configure(text="請點擊 [🔍 查詢時價]。若要更準，可輸入完整型號。", text_color="#ffffff")
    self.add_cart_btn.configure(state="disabled")


# 套用 v20 方法覆寫
ROGApp.load_step_ui = v20_load_step_ui
ROGApp.on_build_menu1_change = v20_on_build_menu1_change
ROGApp.next_step = v20_next_step
ROGApp.get_selected_target = v20_get_selected_target
ROGApp.build_search_keyword = v20_build_search_keyword
ROGApp.make_filters = v20_make_filters
ROGApp.product_match_score = v20_product_match_score
ROGApp.search_pchome_products = v20_search_pchome_products
ROGApp.update_upg_options = v20_update_upg_options


# ==========================================================
# v29 強化補丁：局部升級三段式、附加商品三段式、更多周邊/零組件選項
# ==========================================================

SSD_CAPACITY_BY_GEN_V21 = {
    "Gen4 NVMe SSD": ["256GB", "512GB", "1TB", "2TB", "4TB", "8TB"],
    "Gen5 NVMe SSD": ["512GB", "1TB", "2TB", "4TB", "8TB"],
    "SATA 2.5吋 SSD": ["500GB", "1TB", "2TB", "4TB", "8TB"],
}

EXTRA_V21 = {
    "鍵盤": {
        "Logitech": ["G Pro X TKL", "G915 X LIGHTSPEED", "G512", "MX Keys S"],
        "Razer": ["BlackWidow V4", "Huntsman V3 Pro TKL", "DeathStalker V2 Pro", "Ornata V3"],
        "ASUS ROG": ["Azoth", "Azoth Extreme", "Falchion RX Low Profile", "Strix Scope II 96"],
        "SteelSeries": ["Apex Pro TKL", "Apex 9 TKL", "Apex 7"],
        "Keychron": ["Q1 HE", "Q3 Max", "K2 HE", "K8 Pro", "V1 Max"],
        "Wooting": ["60HE+", "80HE"],
        "Corsair": ["K70 MAX", "K65 PLUS Wireless", "K100 RGB"],
        "HyperX": ["Alloy Origins", "Alloy Rise", "Alloy Core RGB"],
        "Ducky": ["One 3", "ProjectD Tinker 65", "Zero 6108"],
        "Akko": ["MOD 007B HE", "5075B Plus", "MU01"],
    },
    "滑鼠": {
        "Logitech": ["G Pro X Superlight 2", "G502 X PLUS", "G903 LIGHTSPEED", "MX Master 3S", "G304"],
        "Razer": ["Viper V3 Pro", "DeathAdder V3 Pro", "Basilisk V3 Pro", "Cobra Pro", "Naga V2 Pro"],
        "ASUS ROG": ["Harpe Ace Aim Lab", "KerIS II Ace", "Gladius III Wireless", "Chakram X"],
        "SteelSeries": ["Aerox 5 Wireless", "Prime Wireless", "Rival 5"],
        "Zowie": ["EC2-CW", "U2", "S2-C", "FK2-C"],
        "Pulsar": ["X2V2", "Xlite V3", "X2H"],
        "Glorious": ["Model O 2", "Model D 2", "Model I 2"],
        "Finalmouse": ["UltralightX", "Starlight-12"],
        "VAXEE": ["XE Wireless", "NP-01S Wireless", "OUTSET AX Wireless"],
    },
    "耳機": {
        "HyperX": ["Cloud III Wireless", "Cloud Alpha Wireless", "Cloud Stinger 2"],
        "SteelSeries": ["Arctis Nova 7", "Arctis Nova Pro Wireless", "Arctis Nova 5"],
        "ASUS ROG": ["Delta II", "Delta S Wireless", "Fusion II 500", "Cetia True Wireless"],
        "Logitech": ["G Pro X 2 LIGHTSPEED", "G733", "G435"],
        "Razer": ["BlackShark V2 Pro", "Kraken V4", "Barracuda X"],
        "Corsair": ["Virtuoso Pro", "HS80 Max", "VOID RGB Elite"],
        "Sony": ["INZONE H9", "INZONE H5"],
    },
    "麥克風": {
        "Blue": ["Yeti", "Yeti X", "Snowball iCE"],
        "Shure": ["MV7+", "MV7", "SM7B"],
        "Elgato": ["Wave:3", "Wave DX", "Wave Neo"],
        "HyperX": ["QuadCast S", "SoloCast"],
        "Razer": ["Seiren V3 Chroma", "Seiren Mini"],
        "RODE": ["NT-USB+", "PodMic USB", "XDM-100"],
        "Audio-Technica": ["AT2020USB-X", "ATR2500x-USB"],
    },
    "直播/擷取": {
        "Elgato": ["Stream Deck MK.2", "Stream Deck XL", "Stream Deck Neo", "HD60 X", "4K X", "Game Capture 4K Pro"],
        "AVerMedia": ["Live Gamer Ultra 2.1", "Live Gamer 4K 2.1", "Live Streamer CAP 4K"],
        "Razer": ["Stream Controller X", "Ripsaw HD"],
        "Logitech": ["Mevo Start", "Brio 4K"],
    },
    "網路/擴充卡": {
        "Intel": ["AX210 Wi-Fi 6E PCIe", "BE200 Wi-Fi 7 PCIe", "I225 2.5GbE PCIe"],
        "TP-Link": ["Archer TXE75E", "Archer TBE550E", "TX201 2.5GbE"],
        "ASUS": ["PCE-BE92BT Wi-Fi 7", "XG-C100C 10GbE"],
        "QNAP": ["QXG-2G1T-I225", "QXG-10G1T"],
        "Orico": ["USB-C PCIe 擴充卡", "M.2 NVMe PCIe 轉接卡"],
    },
    "UPS/電源保護": {
        "APC": ["BX1000M-TW 1000VA", "BR1500G-TW 1500VA", "BVX1200LI-MS 1200VA"],
        "CyberPower": ["UT1000E 1000VA", "CP1500PFCLCD", "OL1000ERTXL2U"],
        "Eaton": ["5E 1100i USB", "5SC 1000i"],
        "台達": ["VX-1000VA", "Amplon R Series 1kVA"],
    },
    "作業系統/軟體": {"Microsoft": ["Windows 11 家用彩盒版", "Windows 11 專業彩盒版", "Windows 11 家用隨機版", "Windows 11 專業隨機版", "Microsoft 365 個人版", "Microsoft 365 家用版"]},
    "傳統硬碟 HDD": {
        "WD": ["Blue 2TB HDD", "Black 4TB HDD", "Red Plus 8TB HDD", "Red Pro 16TB HDD"],
        "Seagate": ["Barracuda 2TB HDD", "IronWolf 8TB HDD", "IronWolf Pro 16TB HDD", "Exos 16TB HDD"],
        "Toshiba": ["P300 2TB HDD", "N300 8TB HDD", "X300 10TB HDD"],
    },
    "線材/支架/風扇": {
        "Lian Li": ["Strimer Plus V2 24Pin", "Strimer Plus V2 12VHPWR", "UNI FAN SL-INF 120 三入"],
        "ASUS ROG": ["Herculx 顯卡支撐架", "ROG Aura Terminal"],
        "Cooler Master": ["MasterFan MF120 Halo 三入", "Vertical GPU Holder Kit V3"],
        "Thermalright": ["TL-C12C 三入風扇", "LGA1700-BCF 扣具"],
        "Noctua": ["NF-A12x25 PWM", "NF-A14 PWM"],
    },
    "不需要": {"不需要": ["不需要附加商品"]},
}

BRAND_MODEL_DB["EXTRA_V21"] = EXTRA_V21


def _v29_ensure_extra_widgets(app):
    if not hasattr(app, "build_menu_3"):
        app.build_menu_3 = ctk.CTkOptionMenu(app.build_container, values=["請選擇"], width=600)
    if not hasattr(app, "upg_sub"):
        app.upg_sub = ctk.CTkOptionMenu(app.upgrade_container, values=["請選擇"], command=app.on_upgrade_sub_change, width=400)


def v29_extra_brands(category):
    return list(EXTRA_V21.get(category, {"請選擇": ["請選擇"]}).keys())


def v29_extra_models(category, brand):
    return EXTRA_V21.get(category, {}).get(brand, ["請選擇"])


def v29_build_extra_brand_change(self, val):
    category = self.build_menu_1.get()
    models = v29_extra_models(category, val)
    self.build_menu_3.configure(values=models)
    self.build_menu_3.set(models[0])


def v29_on_build_menu2_change(self, val):
    _v29_ensure_extra_widgets(self)
    if self.current_mode == "BUILD_PC" and self.build_step == 9:
        v29_build_extra_brand_change(self, val)


def v29_on_build_menu1_change(self, val):
    _v29_ensure_extra_widgets(self)
    if self.current_mode == "BUILD_PC" and self.build_step == 9:
        brands = v29_extra_brands(val)
        self.build_menu_2.configure(values=brands, command=self.on_build_menu2_change)
        self.build_menu_2.set(brands[0])
        v29_build_extra_brand_change(self, brands[0])
        return
    if self.current_mode == "BUILD_PC":
        try: self.build_menu_2.configure(command=None)
        except Exception: pass
        models = v20_get_models_for_step(self, val)
        if not models: models = ["請選擇"]
        self.build_menu_2.configure(values=models)
        self.build_menu_2.set(models[0])


def v29_load_step_ui(self):
    _v29_ensure_extra_widgets(self)
    self.build_menu_3.pack_forget()
    self.add_cart_btn.configure(state="disabled")
    self.search_btn.configure(state="normal")
    self.open_link_btn.configure(state="disabled")
    self.current_fetch = None
    self.build_menu_1.pack_forget(); self.build_menu_2.pack_forget()
    if self.current_mode == "BUILD_PC":
        steps = ["1. CPU 品牌與型號", "2. 主機板品牌與型號", "3. 記憶體品牌 / 頻率 / 容量", "4. SSD 品牌與型號", "5. 顯示卡品牌與型號", "6. 散熱器品牌與型號", "7. 電源品牌與瓦數", "8. 機殼品牌與型號", "9. 螢幕品牌與型號", "10. 附加商品：分類 → 品牌 → 型號"]
        self.step_label.configure(text=steps[self.build_step])
        self.build_menu_1.pack(pady=5); self.build_menu_2.pack(pady=5)
        if self.build_step == 9:
            self.build_menu_3.pack(pady=5)
            cats = list(EXTRA_V21.keys())
            self.build_menu_1.configure(values=cats, command=self.on_build_menu1_change)
            self.build_menu_1.set(cats[0])
            self.on_build_menu1_change(cats[0])
            self.price_label.configure(text="第 10 頁已改成：先選商品類別，再選品牌，最後選型號。", text_color="#ffffff")
        else:
            self.build_menu_1.configure(command=self.on_build_menu1_change)
            brands = v20_get_brands_for_step(self)
            if not brands: brands = ["請選擇"]
            self.build_menu_1.configure(values=brands)
            self.build_menu_1.set(brands[0])
            self.on_build_menu1_change(brands[0])
            self.price_label.configure(text="每一步先選品牌/分類，再選型號；可直接查價或輸入更精準關鍵字。", text_color="#ffffff")
    else:
        v20_load_step_ui(self)


def v29_on_upgrade_sub_change(self, val):
    cat = self.upg_cat.get() if hasattr(self, "upg_cat") else ""
    opts = ["請選擇"]
    if cat == "固態硬碟 (SSD)":
        opts = [f"{val} {cap}" for cap in SSD_CAPACITY_BY_GEN_V21.get(val, ["1TB", "2TB"])]
    elif cat == "記憶體 (RAM)":
        opts = [f"{val} {cap}" for cap in UPGRADE_DB.get("RAM_CAPACITY", ["16G", "32G", "64G"])]
    elif cat == "CPU 處理器": opts = BRAND_MODEL_DB["CPU"].get(val, [])
    elif cat == "顯示卡 (GPU)": opts = BRAND_MODEL_DB["GPU"].get(val, [])
    elif cat == "電源供應器 (PSU)": opts = BRAND_MODEL_DB["PSU"].get(val, [])
    elif cat == "CPU 散熱器": opts = BRAND_MODEL_DB["COOLER"].get(val, [])
    elif cat == "機殼": opts = BRAND_MODEL_DB["CASE"].get(val, [])
    elif cat == "螢幕": opts = BRAND_MODEL_DB["MONITOR"].get(val, [])
    elif cat == "周邊/附加商品":
        opts = []
        for brand, models in EXTRA_V21.get(val, {}).items():
            opts.extend([f"{brand} {m}" for m in models])
    opts = _uniq(opts) or ["請選擇"]
    self.upg_item.configure(values=opts)
    self.upg_item.set(opts[0])


def v29_update_upg_options(self, cat):
    _v29_ensure_extra_widgets(self)
    self.search_keywords.clear()
    self.upg_sub.configure(command=self.on_upgrade_sub_change)
    if cat == "固態硬碟 (SSD)":
        subs = list(SSD_CAPACITY_BY_GEN_V21.keys())
    elif cat == "記憶體 (RAM)":
        ddr = self.specs.get('ram_type', 'DDR5')
        freqs = ["5600", "6000", "6400"] if ddr == "DDR5" else ["2666", "3200", "3600"]
        subs = [f"{ddr} {f}" for f in freqs]
    elif cat == "CPU 處理器": subs = list(BRAND_MODEL_DB["CPU"].keys())
    elif cat == "顯示卡 (GPU)": subs = list(BRAND_MODEL_DB["GPU"].keys())
    elif cat == "電源供應器 (PSU)": subs = list(BRAND_MODEL_DB["PSU"].keys())
    elif cat == "CPU 散熱器": subs = list(BRAND_MODEL_DB["COOLER"].keys())
    elif cat == "機殼": subs = list(BRAND_MODEL_DB["CASE"].keys())
    elif cat == "螢幕": subs = list(BRAND_MODEL_DB["MONITOR"].keys())
    elif cat == "周邊/附加商品": subs = list(EXTRA_V21.keys())
    else: subs = ["請選擇"]
    self.upg_sub.configure(values=subs)
    self.upg_sub.set(subs[0])
    self.on_upgrade_sub_change(subs[0])
    self.price_label.configure(text="局部升級已改成三段式。SSD：SSD → Gen4/Gen5/SATA → 容量；周邊：周邊 → 類別 → 品牌型號。", text_color="#ffffff")
    self.add_cart_btn.configure(state="disabled")


def v29_mode_upgrade(self):
    _v29_ensure_extra_widgets(self)
    self.current_fetch = None
    self.build_select_container.pack_forget(); self.build_container.pack_forget()
    self.upgrade_container.pack(fill="x", padx=20, pady=10)
    self.upg_cat.pack_forget(); self.upg_sub.pack_forget(); self.upg_item.pack_forget()
    self.upg_cat.pack(pady=8); self.upg_sub.pack(pady=8); self.upg_item.pack(pady=8)
    self.repack_bottom_actions()
    self.mid_title.configure(text="[ 局部升級模式：三段式選單 ]")
    self.current_mode = "UPGRADE"
    cats = ["固態硬碟 (SSD)", "記憶體 (RAM)"]
    if not self.is_laptop:
        cats.extend(["CPU 處理器", "顯示卡 (GPU)", "電源供應器 (PSU)", "CPU 散熱器", "機殼"])
    cats.extend(["螢幕", "周邊/附加商品"])
    self.upg_cat.configure(values=cats, command=self.update_upg_options)
    self.upg_cat.set(cats[0])
    self.update_upg_options(cats[0])


def v29_get_selected_target(self):
    if self.current_mode == "UPGRADE":
        cat = self.upg_cat.get(); sub = self.upg_sub.get() if hasattr(self, "upg_sub") else ""; item = self.upg_item.get()
        if cat in ["固態硬碟 (SSD)", "記憶體 (RAM)", "周邊/附加商品"]: return item
        if sub and sub not in item: return f"{sub} {item}".strip()
        return item
    if self.current_mode == "BUILD_PC" and self.build_step == 9:
        brand = self.build_menu_2.get(); model = self.build_menu_3.get()
        if brand == "不需要" or model == "不需要附加商品": return "不需要附加商品"
        return f"{brand} {model}".strip()
    return v20_get_selected_target(self)


def v29_build_search_keyword(self, selected_target):
    manual = self.get_manual_query()
    if manual: return manual
    s = clean_display_name(selected_target).strip().replace("NVMe", "").replace("固態硬碟", "SSD")
    s = re.sub(r'\s+', ' ', s).strip()
    s = re.sub(r'\[(ASUS|MSI|GIGABYTE|ASRock)\]\s*', r'\1 ', s, flags=re.I)
    return s


def v29_component_from_current(self):
    if self.current_mode == "UPGRADE":
        cat = self.upg_cat.get() if hasattr(self, "upg_cat") else ""
        if "SSD" in cat: return "SSD"
        if "RAM" in cat or "記憶體" in cat: return "RAM"
        if "CPU 處理器" in cat: return "CPU"
        if "GPU" in cat or "顯示卡" in cat: return "GPU"
        if "PSU" in cat or "電源" in cat: return "PSU"
        if "散熱" in cat: return "COOLER"
        if "機殼" in cat: return "CASE"
        if "螢幕" in cat: return "MONITOR"
        if "周邊" in cat: return "EXTRA"
    return v20_component_from_current(self)


def v29_start_desktop_builder(self):
    self.current_fetch = None; self.current_mode = "BUILD_PC"
    self.build_select_container.pack_forget(); self.build_container.pack(fill="x", padx=20, pady=10)
    self.repack_bottom_actions(); self.mid_title.configure(text="[ 🖥️ 桌機配單精靈 v25 ]")
    self.build_max_steps = 10; self.build_step = 0; self.build_context.clear(); self.clear_cart(); self.load_step_ui()

ROGApp.mode_upgrade = v29_mode_upgrade
ROGApp.update_upg_options = v29_update_upg_options
ROGApp.on_upgrade_sub_change = v29_on_upgrade_sub_change
ROGApp.load_step_ui = v29_load_step_ui
ROGApp.on_build_menu1_change = v29_on_build_menu1_change
ROGApp.on_build_menu2_change = v29_on_build_menu2_change
ROGApp.get_selected_target = v29_get_selected_target
ROGApp.build_search_keyword = v29_build_search_keyword
ROGApp.start_desktop_builder = v29_start_desktop_builder
ROGApp.component_from_current = v29_component_from_current



# ==========================================
# v33：AI 記憶、冷卻機制、Gemini 修復、可拉動三欄與字體縮放
# ==========================================
AI_MEMORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai_chat_memory.json")
AI_MEMORY_MAX_TURNS = 12
AI_KEY_BUILTIN = ""

GRADE_RULES_V33 = [
    (93, "SSS"), (88, "SS+"), (82, "SS"), (76, "S+"), (70, "S"),
    (64, "A++"), (58, "A+"), (52, "A"), (46, "B++"), (40, "B+"),
    (34, "B"), (27, "C"), (20, "D"), (12, "E"), (0, "F")
]

GAME_ALIAS_MAP = {
    "異環": "異環 / NTE / Neverness to Everness。這不是 Fallout: New Vegas，不要把 NTE 誤判成 New Vegas。若官方配備資訊不完整，請以大型 3D 開放世界動作 RPG 來估算。",
    "nte": "異環 / NTE / Neverness to Everness。這不是 Fallout: New Vegas，不要把 NTE 誤判成 New Vegas。若官方配備資訊不完整，請以大型 3D 開放世界動作 RPG 來估算。",
    "neverness": "異環 / NTE / Neverness to Everness。若官方配備資訊不完整，請以大型 3D 開放世界動作 RPG 來估算。",
    "黑神話": "黑神話：悟空，偏重 GPU 與顯存，光追/高解析度需求高。",
    "2077": "Cyberpunk 2077，光追/路徑追蹤非常吃 GPU 與 DLSS。",
    "電馭叛客": "Cyberpunk 2077，光追/路徑追蹤非常吃 GPU 與 DLSS。",
    "原神": "原神，主流獨顯可高畫質，重點是穩定與散熱。",
    "崩鐵": "崩壞：星穹鐵道，主流獨顯可高畫質，重點是穩定與散熱。",
}


def grade_threshold_text():
    return "｜".join([f"{g}≥{s}" for s, g in GRADE_RULES_V33[:-1]]) + "｜F<12"


def load_ai_memory():
    try:
        if os.path.exists(AI_MEMORY_FILE):
            with open(AI_MEMORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data[-AI_MEMORY_MAX_TURNS:]
    except Exception:
        pass
    return []


def save_ai_memory(history):
    try:
        with open(AI_MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history[-AI_MEMORY_MAX_TURNS:], f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def normalize_user_query(user_text):
    text = (user_text or "").strip()
    # 常見錯字/縮寫整理，讓外部 AI 不會把 NTE 誤判成 Fallout: New Vegas。
    replacements = {
        "異環nte": "異環 NTE",
        "異環 NTE": "異環 NTE",
        "NTE": "NTE",
        "nte": "NTE",
    }
    for a, b in replacements.items():
        text = text.replace(a, b)
    return text


def infer_game_context(user_text):
    low = (user_text or "").lower()
    hits = []
    for k, desc in GAME_ALIAS_MAP.items():
        if k.lower() in low or k in (user_text or ""):
            hits.append(desc)
    return "\n".join(dict.fromkeys(hits))


def compact_history_for_ai(history):
    if not history:
        return "無"
    rows = []
    for h in history[-8:]:
        q = str(h.get("user", "")).strip().replace("\n", " ")[:160]
        a = str(h.get("assistant", "")).strip().replace("\n", " ")[:280]
        if q or a:
            rows.append(f"使用者：{q}\n顧問：{a}")
    return "\n---\n".join(rows) if rows else "無"


def build_ai_prompt(user_text, specs, history=None):
    user_text = normalize_user_query(user_text)
    compact = compact_specs_for_ai(specs)
    scores = calculate_score(specs)
    compact["short_verdict"] = short_hardware_verdict(specs, scores).replace("簡短評價:" + chr(10), "").replace("簡短評價：" + chr(10), "")
    compact["upgrade_hint"] = hardware_upgrade_suggestions(specs, scores)
    compact["limits"] = hardware_limit_flags(specs)
    compact["rating"] = {
        "game": f"{scores.get('GameGrade')} {scores.get('game_score_100')}/100",
        "productivity": f"{scores.get('ProductivityGrade')} {scores.get('prod_score_100')}/100",
        "ai": f"{scores.get('AICalcGrade')} {scores.get('ai_score_100')}/100",
        "overall": f"{scores.get('OverallGrade')} {scores.get('overall_score_100')}/100",
        "scale": grade_threshold_text(),
    }
    compact["rating_logic"] = "遊戲偏重 GPU/VRAM 與解析度體感；生產力偏重 CPU/RAM/SSD；AI 偏重 NVIDIA GPU/VRAM/RAM；綜合以前三項加權平均。"
    hardware_context = json.dumps(compact, ensure_ascii=False, indent=2)
    game_context = infer_game_context(user_text)
    chat_context = compact_history_for_ai(history or [])
    return f"""
你是台灣高階電競硬體架構師、電腦賣場採購顧問與 AI 工作站規劃師。
請直接回答使用者真正想問的問題，硬體資料只當背景參考，不要重複規格，不要客服腔。

【重要辨識】
{game_context or '沒有特別遊戲別名。'}

【前文記憶】
{chat_context}

【判斷規則】
1. 必須參考硬體評級、簡短評價、升級限制，回答不可前後矛盾。
2. 若使用者問特定遊戲，先辨識遊戲名稱；不知道官方需求時要說「以同類型遊戲估算」，不要亂套其他遊戲。
3. 低分、無獨顯、老平台：不要把 RAM/SSD 講成大幅提升遊戲/AI 的解法；要明講只能改善流暢度或容量。
4. 筆電通常只能升 RAM/SSD/散熱維護；CPU/GPU 多半不能換。若可能板載 RAM，要提醒查型號。
5. 回答可長可短，依問題複雜度調整，最多 1000 字。重點式、主流好懂。

【目前硬體與評價】
{hardware_context}

【使用者最新問題】
{user_text}
""".strip()


def _call_gemini_ai(prompt):
    """v33：減少模型列表請求，優先用穩定模型；429 時退避重試。"""
    api_key = (
        os.getenv("GEMINI_API_KEY", "").strip()
        or os.getenv("GOOGLE_API_KEY", "").strip()
        or os.getenv("GOOGLE_AI_API_KEY", "").strip()
        or AI_KEY_BUILTIN
    )
    if not api_key:
        raise RuntimeError("未設定 Gemini API Key")

    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
    static_models = []
    env_model = os.getenv("GEMINI_MODEL", "").strip()
    if env_model:
        static_models.append(env_model.replace("models/", ""))
    static_models += [
        "gemini-2.5-flash-lite",
        "gemini-2.5-flash",
        "gemini-2.0-flash-lite",
        "gemini-2.0-flash",
        "gemini-1.5-flash",
    ]

    # 只有在靜態模型都失敗時才抓 models，避免每次多打 API 造成速率壓力。
    def discover_models():
        found = []
        for api_version in ("v1beta", "v1"):
            try:
                r = requests.get(
                    f"https://generativelanguage.googleapis.com/{api_version}/models",
                    headers=headers,
                    timeout=(6, 20),
                )
                if r.status_code in (401, 403):
                    raise RuntimeError("Gemini API Key 無效、未啟用，或沒有 Gemini API 權限")
                if r.status_code == 429:
                    continue
                r.raise_for_status()
                for m in r.json().get("models", []):
                    name = (m.get("name", "") or "").replace("models/", "")
                    methods = m.get("supportedGenerationMethods", []) or []
                    low = name.lower()
                    if "generateContent" in methods and "flash" in low and not any(x in low for x in ["audio", "tts", "image", "embed", "live"]):
                        found.append((api_version, name))
            except RuntimeError:
                raise
            except Exception:
                pass
        return found

    candidates = []
    for m in static_models:
        for api_version in ("v1beta", "v1"):
            candidates.append((api_version, m))
    candidates += discover_models()

    # 去重
    seen = set(); dedup = []
    for c in candidates:
        if c not in seen:
            seen.add(c); dedup.append(c)

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.35, "topP": 0.9, "maxOutputTokens": 2800},
    }
    errors = []
    for api_version, model in dedup[:12]:
        url = f"https://generativelanguage.googleapis.com/{api_version}/models/{model}:generateContent"
        for attempt in range(2):
            try:
                r = requests.post(url, headers=headers, json=payload, timeout=(8, 50))
                if r.status_code in (404, 410):
                    errors.append(f"{model}:404")
                    break
                if r.status_code in (401, 403):
                    raise RuntimeError("Gemini API Key 無效或權限不足")
                if r.status_code == 429:
                    # 429 常見於瞬間太多請求/免費配額/模型速率，退避後換模型。
                    time.sleep(1.2 + attempt * 2.0)
                    errors.append(f"{model}:429")
                    continue
                if r.status_code in (500, 502, 503, 504):
                    time.sleep(0.8)
                    errors.append(f"{model}:{r.status_code}")
                    continue
                r.raise_for_status()
                data = r.json()
                parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                answer = "".join(p.get("text", "") for p in parts).strip()
                if answer:
                    return answer
                errors.append(f"{model}:空白")
                break
            except RuntimeError:
                raise
            except Exception as e:
                errors.append(f"{model}:{str(e)[:60]}")
                break
    detail = " | ".join(errors[:8])
    if "429" in detail:
        raise RuntimeError("Gemini 目前回傳 429：短時間請求過多、免費層速率限制或該 Key 配額受限。程式已退避重試，請等冷卻或換 Key/專案。")
    raise RuntimeError("Gemini 外部 AI 無回覆：" + detail)


def external_ai_recommendation(user_text, specs, history=None):
    prompt = build_ai_prompt(user_text, specs, history=history)
    result = _call_gemini_ai(prompt)
    return "🧠 AI 建議:" + chr(10) + result.strip()


def _similar_text(a, b):
    a = re.sub(r"\s+", "", (a or "").lower())
    b = re.sub(r"\s+", "", (b or "").lower())
    if not a or not b:
        return 0
    return difflib.SequenceMatcher(None, a, b).ratio()


def v33_init(self):
    super(ROGApp, self).__init__()
    self.specs = get_specs()
    self.scores = calculate_score(self.specs)
    self.is_laptop = self.specs['is_laptop']
    self.cart_items = {}
    self.build_step = 0
    self.build_max_steps = 0
    self.build_context = {}
    self.current_mode = ""
    self.ai_history = load_ai_memory()
    self.ai_request_times = []
    self.ai_recent_prompts = []
    self.ai_cooldown_until = 0
    self.ui_scale_percent = 100

    device_type = "筆記型電腦" if self.is_laptop else "桌上型電腦"
    self.title(f"電腦檢測升級工具 v33.1_panedwindow_fixed - [{device_type}]")
    self.geometry("1840x1040")
    self.minsize(1400, 820)
    self.resizable(True, True)
    try:
        self.after(150, lambda: self.state("zoomed"))
    except Exception:
        pass

    self.topbar = ctk.CTkFrame(self, fg_color="#202020", height=38, corner_radius=0)
    self.topbar.pack(fill="x", side="top")
    ctk.CTkLabel(self.topbar, text="電腦硬體 AI 顧問 v33.1", text_color="#00ffff", font=ctk.CTkFont(size=15, weight="bold")).pack(side="left", padx=14)
    ctk.CTkLabel(self.topbar, text="字體/介面比例", text_color="#cccccc").pack(side="right", padx=(8, 4))
    self.scale_menu = ctk.CTkOptionMenu(
        self.topbar,
        values=["25%", "50%", "75%", "100%", "125%", "150%", "175%", "200%", "250%", "300%", "400%", "500%"],
        command=self.set_ui_scale,
        width=95,
    )
    self.scale_menu.set("100%")
    self.scale_menu.pack(side="right", padx=10, pady=5)

    self.main_pane = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashwidth=8, bd=0, bg="#1f1f1f", relief="flat")
    self.main_pane.pack(fill="both", expand=True, padx=8, pady=8)

    # 注意：CTkScrollableFrame 是複合元件，不能直接 add 到 tk.PanedWindow，
    # 否則會出現 TclError: can't add ...!canvas.!ctkscrollableframe to .!panedwindow。
    # 正確做法：先建立 PanedWindow 的直接子容器，再把 CTkScrollableFrame 放進容器內。
    self.left_pane_holder = ctk.CTkFrame(self.main_pane, fg_color="transparent", corner_radius=0)
    self.mid_pane_holder = ctk.CTkFrame(self.main_pane, fg_color="transparent", corner_radius=0)
    self.right_pane_holder = ctk.CTkFrame(self.main_pane, fg_color="transparent", corner_radius=0)

    self.main_pane.add(self.left_pane_holder, minsize=360, width=540, stretch="first")
    self.main_pane.add(self.mid_pane_holder, minsize=560, width=860, stretch="always")
    self.main_pane.add(self.right_pane_holder, minsize=360, width=520, stretch="last")

    self.left_frame = ctk.CTkScrollableFrame(self.left_pane_holder, width=520, corner_radius=10)
    self.mid_frame = ctk.CTkScrollableFrame(self.mid_pane_holder, width=850, corner_radius=10)
    self.right_frame = ctk.CTkFrame(self.right_pane_holder, width=520, corner_radius=10)

    self.left_frame.pack(fill="both", expand=True)
    self.mid_frame.pack(fill="both", expand=True)
    self.right_frame.pack(fill="both", expand=True)

    self.setup_left_panel()
    self.setup_mid_panel()
    self.setup_right_panel()

    if hasattr(self, "ai_response") and self.ai_history:
        self.ai_response.configure(text=f"已載入 AI 對話記憶 {len(self.ai_history)} 則，可直接接續問。", text_color="#00ff00")

    self.bind_all("<MouseWheel>", self._on_mousewheel, add="+")
    self.bind_all("<Button-4>", self._on_mousewheel, add="+")
    self.bind_all("<Button-5>", self._on_mousewheel, add="+")


def v33_set_ui_scale(self, value):
    try:
        pct = int(str(value).replace("%", ""))
        pct = max(25, min(500, pct))
        self.ui_scale_percent = pct
        ctk.set_widget_scaling(pct / 100)
    except Exception:
        pass


def v33_clear_ai_memory(self):
    self.ai_history = []
    save_ai_memory([])
    if hasattr(self, "ai_response"):
        self.ai_response.configure(text="AI 記憶已清空。", text_color="#ffaa00")


def v33_ai_guard(self, user_text):
    now = time.time()
    if now < getattr(self, "ai_cooldown_until", 0):
        remain = int(self.ai_cooldown_until - now)
        return False, f"AI 顧問冷卻中，約 {remain} 秒後可再問。"

    self.ai_request_times = [t for t in getattr(self, "ai_request_times", []) if now - t <= 600]
    self.ai_recent_prompts = [(t, p) for t, p in getattr(self, "ai_recent_prompts", []) if now - t <= 180]

    def lock(seconds, reason):
        self.ai_cooldown_until = time.time() + seconds
        if hasattr(self, "ai_button"):
            self.ai_button.configure(state="disabled")
            self.after(seconds * 1000, lambda: self.ai_button.configure(state="normal"))
        return False, f"觸發 AI 使用冷卻：{reason}\n冷卻時間：{seconds} 秒。"

    if self.ai_request_times and now - self.ai_request_times[-1] < 4:
        return lock(20, "兩次提問間隔低於 4 秒")
    if len([t for t in self.ai_request_times if now - t <= 30]) >= 3:
        return lock(60, "30 秒內已提問 3 次")
    if len([t for t in self.ai_request_times if now - t <= 120]) >= 6:
        return lock(180, "120 秒內已提問 6 次")
    if len(self.ai_request_times) >= 12:
        return lock(600, "10 分鐘內已提問 12 次")
    similar_count = sum(1 for _, p in self.ai_recent_prompts if _similar_text(p, user_text) >= 0.92)
    if similar_count >= 2:
        return lock(120, "短時間內重複或高度相似問題達 3 次")

    self.ai_request_times.append(now)
    self.ai_recent_prompts.append((now, user_text))
    return True, ""


def render_ai_history(history):
    if not history:
        return ""
    blocks = []
    for h in history[-4:]:
        q = h.get("user", "")
        a = h.get("assistant", "")
        blocks.append(f"你：{q}\nAI：{a}")
    return "\n\n────────────\n\n".join(blocks)


def v33_run_ai_advisor(self):
    user_text = self.ai_input.get().strip()
    if not user_text:
        self.ai_response.configure(text="請先輸入需求，例如：可以跑異環 NTE 嗎、10萬含螢幕怎麼配、想剪輯要升什麼。", text_color="#ffaa00")
        return
    user_text = normalize_user_query(user_text)
    ok, msg = self.v33_ai_guard(user_text)
    if not ok:
        self.ai_response.configure(text=msg, text_color="#ffaa00")
        return

    if hasattr(self, "ai_button"):
        self.ai_button.configure(state="disabled")
    self.ai_response.configure(text="⏳ 外部 Gemini AI 分析中...\n會接續前文記憶，並參考目前硬體評價。", text_color="#cccccc")

    def task():
        try:
            result = external_ai_recommendation(user_text, self.specs, history=self.ai_history)
            clean_answer = result.replace("🧠 AI 建議:\n", "", 1).strip()
            self.ai_history.append({"time": int(time.time()), "user": user_text, "assistant": clean_answer})
            self.ai_history = self.ai_history[-AI_MEMORY_MAX_TURNS:]
            save_ai_memory(self.ai_history)
            display = render_ai_history(self.ai_history)
            self.ui_safe(lambda display=display: self.ai_response.configure(text=display, text_color="#00ff00"))
        except Exception as e:
            msg = str(e)
            msg = re.sub(r"AIza[0-9A-Za-z_\-]+", "AIza***", msg)
            self.ui_safe(lambda msg=msg: self.ai_response.configure(text="⚠️ 外部 AI 連線失敗：\n" + msg, text_color="#ff5555"))
        finally:
            def unlock():
                if hasattr(self, "ai_button") and time.time() >= getattr(self, "ai_cooldown_until", 0):
                    self.ai_button.configure(state="normal")
            self.ui_safe(unlock)

    threading.Thread(target=task, daemon=True).start()


def v33_hardware_limit_flags(specs):
    flags = hardware_limit_flags.__globals__.get('_v32_hardware_limit_flags_backup', None)
    base = flags(specs) if flags else []
    cpu = (specs.get('cpu_name', '') or '').lower()
    gpu = (specs.get('gpu_name', '') or '').lower()
    model = ((specs.get('system_manufacturer', '') or '') + ' ' + (specs.get('system_model', '') or '')).lower()
    # 以型號代碼粗判老平台。不能取代正式規格表，但比純分數更接近實務判斷。
    if re.search(r'i[3579][-\s]?(6|7|8|9)\d{3}', cpu) or re.search(r'ryzen\s+[3579]\s+[23]\d{3}', cpu):
        if not any('6~10 年前' in x for x in base):
            base.append('CPU/平台推測已接近 6~10 年前級距')
    if any(k in gpu for k in ['gtx 10', 'gtx 16', 'mx150', 'mx250', 'mx350', 'uhd graphics', 'iris xe']):
        if not any('舊世代' in x for x in base):
            base.append('GPU 推測屬舊世代或入門顯示能力')
    soldered_keywords = ['zenbook', 'vivobook', 'surface', 'xps', 'swift', 'gram', 'yoga', 'ideapad slim', 'macbook']
    if specs.get('is_laptop') and any(k in model for k in soldered_keywords):
        base.append('此類輕薄筆電常見板載 RAM，升級前必須查精確型號')
    return list(dict.fromkeys(base))

# 備份並覆寫限制判斷
if '_v32_hardware_limit_flags_backup' not in globals():
    _v32_hardware_limit_flags_backup = hardware_limit_flags
hardware_limit_flags = v33_hardware_limit_flags

# 覆寫 ROGApp 方法
ROGApp.__init__ = v33_init
ROGApp.set_ui_scale = v33_set_ui_scale
ROGApp.clear_ai_memory = v33_clear_ai_memory
ROGApp.v33_ai_guard = v33_ai_guard
ROGApp.run_ai_advisor = v33_run_ai_advisor



# ==========================================
# v34：外部 AI only、視窗內記憶、無關問題鎖定、API Key 外部化、評分機制重定義
# ==========================================
V34_VERSION = "v34_external_only_guard_rating"

# API Key 不寫死在程式碼內，避免原始碼/反編譯直接看到。
# 讀取順序：環境變數 GEMINI_API_KEY / GOOGLE_API_KEY → 使用者 AppData key 檔 → 專案 secrets key 檔。
def _app_config_dir_v34():
    base = os.getenv("APPDATA") or os.path.expanduser("~")
    path = os.path.join(base, "ROGHardwareAI")
    try:
        os.makedirs(path, exist_ok=True)
    except Exception:
        pass
    return path


def gemini_key_paths_v34():
    here = os.path.dirname(os.path.abspath(__file__))
    return [
        os.path.join(_app_config_dir_v34(), "gemini_api_key.txt"),
        os.path.join(here, "secrets", "gemini_api_key.txt"),
    ]


def get_gemini_api_key_v34():
    for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_AI_API_KEY"):
        val = os.getenv(name, "").strip()
        if val:
            return val
    for p in gemini_key_paths_v34():
        try:
            if os.path.exists(p):
                val = open(p, "r", encoding="utf-8").read().strip().splitlines()[0].strip()
                if val:
                    return val
        except Exception:
            pass
    return ""


def missing_gemini_key_message_v34():
    p = gemini_key_paths_v34()[0]
    return (
        "未設定 Gemini API Key。\n"
        "請用以下其中一種方式設定後重開程式：\n"
        f"1. 建立檔案：{p}\n"
        "   第一行貼上你的 Gemini API Key。\n"
        "2. 或在 Windows 環境變數設定 GEMINI_API_KEY。\n"
        "提醒：桌面程式無法 100% 防止 Key 被高手取出；最安全是不要寫入程式碼，並在 Google Cloud 對 Key 做 API/配額限制。"
    )


# 視窗內記憶：關閉程式就重來，不再寫 ai_chat_memory.json。
def load_ai_memory():
    return []


def save_ai_memory(history):
    return None


# v34 分級：消費級旗艦約 100 分 = SS；超過 100 但未達伺服器級距 = SS+；非消費/伺服器級明顯超越 = SSS。
GRADE_RULES_V34 = [
    (115, "SSS"), (101, "SS+"), (95, "SS"), (88, "S+"), (82, "S"),
    (76, "A++"), (70, "A+"), (64, "A"), (56, "B++"), (48, "B+"),
    (40, "B"), (30, "C"), (20, "D"), (10, "E"), (0, "F")
]


def score_to_rank(score):
    return classify_grade(score, GRADE_RULES_V34)


def grade_threshold_text():
    return "SSS≥115｜SS+101-114｜SS95-100｜S+88｜S82｜A++76｜A+70｜A64｜B++56｜B+48｜B40｜C30｜D20｜E10｜F<10"


# GPU 以四項常見公開跑分概念做離線估算：3DMark Time Spy Graphics / Steel Nomad / PassMark G3D / Blender GPU。
# 100 分級距以 RTX 5090 類消費級旗艦作為 SS 基準；GB200/B200/H100 等非消費級會超過 100。
GPU_BENCHMARKS_V34 = [
    (['gb200', 'b200', 'blackwell ultra'], {'ts': 160000, 'nomad': 12000, 'passmark': 160000, 'blender': 36000, 'class': 'datacenter'}),
    (['h200', 'h100'], {'ts': 90000, 'nomad': 7000, 'passmark': 98000, 'blender': 24000, 'class': 'datacenter'}),
    (['rtx pro 6000 blackwell', 'pro 6000'], {'ts': 56000, 'nomad': 5200, 'passmark': 78000, 'blender': 17000, 'class': 'workstation'}),
    (['rtx 6000 ada'], {'ts': 36000, 'nomad': 3300, 'passmark': 65000, 'blender': 12500, 'class': 'workstation'}),
    (['rtx 5090'], {'ts': 46923, 'nomad': 4200, 'passmark': 70000, 'blender': 15000, 'class': 'consumer'}),
    (['rtx 4090'], {'ts': 36500, 'nomad': 3300, 'passmark': 59000, 'blender': 11800, 'class': 'consumer'}),
    (['rtx 5080'], {'ts': 34000, 'nomad': 3100, 'passmark': 56000, 'blender': 10300, 'class': 'consumer'}),
    (['rtx 4080 super'], {'ts': 29000, 'nomad': 2600, 'passmark': 52000, 'blender': 8400, 'class': 'consumer'}),
    (['rtx 4080'], {'ts': 28500, 'nomad': 2520, 'passmark': 50000, 'blender': 8200, 'class': 'consumer'}),
    (['rx 7900 xtx'], {'ts': 31000, 'nomad': 2700, 'passmark': 51000, 'blender': 5200, 'class': 'consumer'}),
    (['rtx 5070 ti'], {'ts': 27821, 'nomad': 2350, 'passmark': 47000, 'blender': 7200, 'class': 'consumer'}),
    (['rtx 4070 ti super'], {'ts': 24500, 'nomad': 2200, 'passmark': 45500, 'blender': 7200, 'class': 'consumer'}),
    (['rx 7900 xt'], {'ts': 27500, 'nomad': 2300, 'passmark': 47000, 'blender': 4600, 'class': 'consumer'}),
    (['rtx 5070'], {'ts': 22221, 'nomad': 2000, 'passmark': 41000, 'blender': 6100, 'class': 'consumer'}),
    (['rtx 4070 super'], {'ts': 21000, 'nomad': 1900, 'passmark': 39000, 'blender': 6100, 'class': 'consumer'}),
    (['rx 7800 xt'], {'ts': 20500, 'nomad': 1750, 'passmark': 36000, 'blender': 3300, 'class': 'consumer'}),
    (['rtx 4070'], {'ts': 18000, 'nomad': 1650, 'passmark': 35000, 'blender': 5400, 'class': 'consumer'}),
    (['rtx 5060 ti'], {'ts': 16500, 'nomad': 1450, 'passmark': 30000, 'blender': 4500, 'class': 'consumer'}),
    (['rtx 4060 ti'], {'ts': 13500, 'nomad': 1200, 'passmark': 27000, 'blender': 3900, 'class': 'consumer'}),
    (['rtx 5060'], {'ts': 12500, 'nomad': 1080, 'passmark': 24500, 'blender': 3300, 'class': 'consumer'}),
    (['rtx 4060'], {'ts': 10800, 'nomad': 980, 'passmark': 22500, 'blender': 3000, 'class': 'consumer'}),
    (['rtx 3060'], {'ts': 8800, 'nomad': 760, 'passmark': 17000, 'blender': 2100, 'class': 'consumer'}),
    (['rtx 3050'], {'ts': 6200, 'nomad': 510, 'passmark': 13000, 'blender': 1300, 'class': 'consumer'}),
    (['gtx 1660 ti'], {'ts': 6400, 'nomad': 470, 'passmark': 12000, 'blender': 600, 'class': 'consumer'}),
    (['gtx 1650 ti'], {'ts': 3700, 'nomad': 260, 'passmark': 7600, 'blender': 350, 'class': 'consumer'}),
    (['gtx 1650'], {'ts': 3500, 'nomad': 240, 'passmark': 7200, 'blender': 330, 'class': 'consumer'}),
    (['radeon graphics', 'vega', 'integrated', 'uhd graphics', 'iris xe'], {'ts': 1800, 'nomad': 120, 'passmark': 3000, 'blender': 60, 'class': 'integrated'}),
]

GPU_BASELINE_V34 = {'ts': 46923, 'nomad': 4200, 'passmark': 70000, 'blender': 15000}

# CPU 以四項常見公開跑分概念做離線估算：Geekbench 6 單核 / Geekbench 6 多核 / Cinebench 2024 多核 / PassMark CPU。
CPU_BENCHMARKS_V34 = [
    (['epyc 9755', 'epyc 9654', 'xeon 6980p', 'xeon 6972p'], {'gb6s': 3000, 'gb6m': 38000, 'cb2024': 7200, 'passmark': 160000, 'class': 'server'}),
    (['threadripper pro 7995wx', 'threadripper 7995wx'], {'gb6s': 3000, 'gb6m': 33000, 'cb2024': 6100, 'passmark': 155000, 'class': 'workstation'}),
    (['threadripper 7980x'], {'gb6s': 3000, 'gb6m': 31000, 'cb2024': 5200, 'passmark': 135000, 'class': 'workstation'}),
    (['core ultra 9 285k', '285k'], {'gb6s': 3350, 'gb6m': 23000, 'cb2024': 2450, 'passmark': 68000, 'class': 'consumer'}),
    (['9950x3d'], {'gb6s': 3394, 'gb6m': 22223, 'cb2024': 2423, 'passmark': 66000, 'class': 'consumer'}),
    (['9950x'], {'gb6s': 3410, 'gb6m': 21500, 'cb2024': 2300, 'passmark': 65000, 'class': 'consumer'}),
    (['core ultra 9 275hx', '275hx'], {'gb6s': 3100, 'gb6m': 20500, 'cb2024': 2100, 'passmark': 59000, 'class': 'mobile'}),
    (['14900ks', '14900k', '14900'], {'gb6s': 3100, 'gb6m': 20500, 'cb2024': 2200, 'passmark': 60000, 'class': 'consumer'}),
    (['7950x3d'], {'gb6s': 3000, 'gb6m': 20500, 'cb2024': 2100, 'passmark': 61000, 'class': 'consumer'}),
    (['14700k', '14700'], {'gb6s': 2900, 'gb6m': 19000, 'cb2024': 2000, 'passmark': 53500, 'class': 'consumer'}),
    (['core ultra 7 265k', '265k'], {'gb6s': 3100, 'gb6m': 18500, 'cb2024': 1900, 'passmark': 52000, 'class': 'consumer'}),
    (['9800x3d'], {'gb6s': 3350, 'gb6m': 16500, 'cb2024': 1360, 'passmark': 42500, 'class': 'consumer'}),
    (['9700x'], {'gb6s': 3200, 'gb6m': 16000, 'cb2024': 1250, 'passmark': 39000, 'class': 'consumer'}),
    (['7800x3d'], {'gb6s': 2850, 'gb6m': 15000, 'cb2024': 1100, 'passmark': 35000, 'class': 'consumer'}),
    (['7700x', '7700'], {'gb6s': 2700, 'gb6m': 14000, 'cb2024': 1100, 'passmark': 36500, 'class': 'consumer'}),
    (['9600x'], {'gb6s': 3150, 'gb6m': 13200, 'cb2024': 1050, 'passmark': 31000, 'class': 'consumer'}),
    (['7600x', '7600'], {'gb6s': 2700, 'gb6m': 12000, 'cb2024': 900, 'passmark': 28000, 'class': 'consumer'}),
    (['14400'], {'gb6s': 2450, 'gb6m': 12500, 'cb2024': 1000, 'passmark': 26000, 'class': 'consumer'}),
    (['13400'], {'gb6s': 2300, 'gb6m': 11200, 'cb2024': 900, 'passmark': 23500, 'class': 'consumer'}),
    (['5600h'], {'gb6s': 1700, 'gb6m': 7200, 'cb2024': 620, 'passmark': 17000, 'class': 'mobile'}),
    (['5700x3d'], {'gb6s': 2100, 'gb6m': 10500, 'cb2024': 820, 'passmark': 25000, 'class': 'consumer'}),
    (['3750h'], {'gb6s': 1100, 'gb6m': 3800, 'cb2024': 330, 'passmark': 8200, 'class': 'mobile'}),
]

CPU_BASELINE_V34 = {'gb6s': 3400, 'gb6m': 23000, 'cb2024': 2450, 'passmark': 68000}


def _match_benchmark_v34(name, table, default):
    n = (name or '').lower()
    # 先比長關鍵字，避免 5070 ti 被 5070 提前吃掉。
    rows = []
    for keys, val in table:
        rows.append((sorted(keys, key=len, reverse=True), val))
    for keys, val in rows:
        if any(k in n for k in keys):
            return val
    return default


def _metric_percent_v34(data, baseline, weights):
    total = 0.0
    for key, weight in weights.items():
        total += (float(data.get(key, 0)) / max(float(baseline.get(key, 1)), 1)) * 100 * weight
    return round(total, 1)


def _gpu_practical_floor(gpu_name):
    g = (gpu_name or '').lower()
    laptop = 'laptop' in g
    if any(k in g for k in ['gb200', 'b200', 'h100', 'h200']): return 118
    if 'rtx pro 6000' in g: return 104
    if 'rtx 5090' in g: return 92 if laptop else 100
    if 'rtx 4090' in g: return 84 if laptop else 90
    if 'rtx 5080' in g: return 82 if laptop else 88
    if 'rtx 4080' in g: return 78 if laptop else 84
    if '5070 ti' in g or '4070 ti' in g: return 64 if laptop else 72
    if '5070' in g or '4070 super' in g: return 58 if laptop else 66
    if '4070' in g: return 54 if laptop else 60
    if '5060 ti' in g or '4060 ti' in g: return 48 if laptop else 54
    if '5060' in g or '4060' in g: return 42 if laptop else 48
    if '3060' in g: return 38
    if '3050' in g or '1650' in g: return 22
    return 0


def gpu_benchmark_score(gpu_name):
    default = {'ts': 2500, 'nomad': 160, 'passmark': 4500, 'blender': 80, 'class': 'unknown'}
    raw = _match_benchmark_v34(gpu_name, GPU_BENCHMARKS_V34, default).copy()
    adjusted = raw.copy()
    factor = _laptop_gpu_factor(gpu_name)
    if factor != 1.0:
        for k in ('ts', 'nomad', 'passmark', 'blender'):
            adjusted[k] = adjusted[k] * factor
    score = _metric_percent_v34(adjusted, GPU_BASELINE_V34, {'ts': 0.42, 'nomad': 0.22, 'passmark': 0.18, 'blender': 0.18})
    score = max(score, _gpu_practical_floor(gpu_name))
    # 消費級桌機 RTX 5090 附近壓在 SS；非消費/伺服器級才合理進 SSS。
    if raw.get('class') == 'consumer':
        score = min(score, 100)
    return round(score, 1), int(adjusted.get('ts', 0)), int(raw.get('ts', 0))


def cpu_benchmark_score(cpu_name):
    default = None
    data = _match_benchmark_v34(cpu_name, CPU_BENCHMARKS_V34, default)
    if not data:
        c = (cpu_name or '').lower()
        if 'xeon' in c or 'epyc' in c:
            data = {'gb6s': 2600, 'gb6m': 30000, 'cb2024': 4500, 'passmark': 95000, 'class': 'server'}
        elif 'threadripper' in c:
            data = {'gb6s': 2900, 'gb6m': 28000, 'cb2024': 4200, 'passmark': 110000, 'class': 'workstation'}
        elif 'ultra 9' in c or 'i9' in c or 'ryzen 9' in c:
            data = {'gb6s': 2900, 'gb6m': 17000, 'cb2024': 1750, 'passmark': 45000, 'class': 'consumer'}
        elif 'ultra 7' in c or 'i7' in c or 'ryzen 7' in c:
            data = {'gb6s': 2450, 'gb6m': 12500, 'cb2024': 1100, 'passmark': 30000, 'class': 'consumer'}
        elif 'ultra 5' in c or 'i5' in c or 'ryzen 5' in c:
            data = {'gb6s': 2200, 'gb6m': 9500, 'cb2024': 800, 'passmark': 22000, 'class': 'consumer'}
        else:
            data = {'gb6s': 1200, 'gb6m': 4500, 'cb2024': 350, 'passmark': 9000, 'class': 'unknown'}
    score = _metric_percent_v34(data, CPU_BASELINE_V34, {'gb6s': 0.18, 'gb6m': 0.34, 'cb2024': 0.26, 'passmark': 0.22})
    if data.get('class') in ('consumer', 'mobile'):
        score = min(score, 100)
    return round(score, 1), data


def smart_hardware_grades(specs):
    gpu_score, gpu_adj, gpu_raw = gpu_benchmark_score(specs.get('gpu_name', ''))
    cpu_score, cpu_data = cpu_benchmark_score(specs.get('cpu_name', ''))
    ram_nom = nominal_capacity_gb(specs.get('ram_total', 0))
    vram_gb = (specs.get('gpu_vram', 0) or 0) / 1024
    ram_score = min(100, 28 + ram_nom * 1.30)
    vram_score = min(100, 18 + vram_gb * 5.2)
    npu_score = 0
    cpu_lower = (specs.get('cpu_name', '') or '').lower()
    if 'ultra' in cpu_lower or 'ai' in cpu_lower:
        npu_score = 5
    # 1 遊戲、2 生產力剪輯、3 AI、4 綜合。
    game_score = gpu_score * 0.76 + cpu_score * 0.15 + ram_score * 0.09
    prod_score = cpu_score * 0.42 + gpu_score * 0.24 + ram_score * 0.20 + vram_score * 0.11 + npu_score * 0.03
    ai_score = gpu_score * 0.40 + vram_score * 0.36 + ram_score * 0.13 + cpu_score * 0.08 + npu_score * 0.03
    overall_score = game_score * 0.34 + prod_score * 0.33 + ai_score * 0.33
    # 分數可超過 100，供 SSS/SS+ 使用，但 UI 仍容易理解。
    return {
        'game_score_100': round(game_score, 1),
        'prod_score_100': round(prod_score, 1),
        'ai_score_100': round(ai_score, 1),
        'overall_score_100': round(overall_score, 1),
        'GameGrade': score_to_rank(game_score),
        'ProductivityGrade': score_to_rank(prod_score),
        'AICalcGrade': score_to_rank(ai_score),
        'OverallGrade': score_to_rank(overall_score),
        'gpu_benchmark_ratio': round(gpu_score, 1),
        'gpu_benchmark_adjusted': gpu_adj,
        'gpu_benchmark_raw': gpu_raw,
        'cpu_benchmark_ratio': round(cpu_score, 1),
        'cpu_benchmark_data': cpu_data,
        'ram_nominal': ram_nom,
        'npu_bonus': npu_score,
    }


def calculate_score(specs):
    scores = {}
    cpu_threads = specs.get('cpu_threads', specs.get('cpu_count', 4) * 2)
    cpu_cores = specs.get('cpu_count', 4)
    ram_total = specs.get('ram_total', 0)
    vram = specs.get('gpu_vram', 0)
    scores['CPU'] = int((cpu_cores ** 1.2) * 1500 + cpu_threads * 450)
    scores['RAM'] = int(ram_total * 350)
    scores['GPU'] = int(vram * 1.8)
    scores['AI_Score'] = int(vram * 2.5 + cpu_cores * 400 + ram_total * 120)
    scores['Total'] = scores['CPU'] + scores['RAM'] + scores['GPU'] + scores['AI_Score']
    scores.update(smart_hardware_grades(specs))
    return scores


def hardware_scene_analysis(specs, scores):
    lines = [
        "硬體評價：",
        f"1. 遊戲：{scores.get('GameGrade', 'F')}（{scores.get('game_score_100', 0)}/100）",
        f"2. 生產力/剪輯：{scores.get('ProductivityGrade', 'F')}（{scores.get('prod_score_100', 0)}/100）",
        f"3. AI：{scores.get('AICalcGrade', 'F')}（{scores.get('ai_score_100', 0)}/100）",
        f"4. 綜合：{scores.get('OverallGrade', 'F')}（{scores.get('overall_score_100', 0)}/100）",
        "",
        short_hardware_verdict(specs, scores),
        "",
        "評分方式：",
        "GPU：Time Spy / Steel Nomad / PassMark G3D / Blender；RTX 5090 級距約 100 分=SS。",
        "CPU：Geekbench6 單核/多核 + Cinebench2024 + PassMark；旗艦消費級約 100 分=SS。",
        "綜合：遊戲/生產力/AI 加權；分級：" + grade_threshold_text(),
    ]
    return "\n".join(lines)


def compact_specs_for_ai(specs):
    scores = calculate_score(specs)
    return {
        "device_type": "laptop" if specs.get("is_laptop") else "desktop",
        "cpu": specs.get("cpu_name"),
        "gpu": specs.get("gpu_name"),
        "vram_gb": round((specs.get("gpu_vram", 0) or 0) / 1024, 1),
        "ram": ram_label(specs.get("ram_total", 0), include_real=False),
        "ram_usable_gb": specs.get("ram_total"),
        "ram_type": specs.get("ram_type"),
        "disks": specs.get("disks", []),
        "ratings": {
            "game": f"{scores.get('GameGrade')} {scores.get('game_score_100')}",
            "productivity_editing": f"{scores.get('ProductivityGrade')} {scores.get('prod_score_100')}",
            "ai": f"{scores.get('AICalcGrade')} {scores.get('ai_score_100')}",
            "overall": f"{scores.get('OverallGrade')} {scores.get('overall_score_100')}",
        },
        "short_verdict": short_hardware_verdict(specs, scores).replace("簡短評價:\n", ""),
        "limits": hardware_limit_flags(specs),
        "upgrade_hint": hardware_upgrade_suggestions(specs, scores),
        "rating_scale": grade_threshold_text(),
    }


def _is_first_turn(history):
    return not history


def build_ai_prompt(user_text, specs, history=None):
    user_text = normalize_user_query(user_text)
    scores = calculate_score(specs)
    hardware_context = json.dumps(compact_specs_for_ai(specs), ensure_ascii=False, indent=2)
    game_context = infer_game_context(user_text)
    chat_context = compact_history_for_ai(history or [])
    first = _is_first_turn(history or [])
    first_rule = (
        "這是本視窗第一次回答。若使用者只是打招呼，先簡短回應招呼，再提供一次完整的硬體顧問總覽。"
        "若使用者第一次就問具體問題，先回答該問題，再補一段總覽。總覽風格參考：結論、遊戲/AI剪輯、建議方案、查價關鍵字。"
        if first else
        "這不是第一次回答。請接續前文，只回答最新問題，不要重複完整總覽。"
    )
    return f"""
你是台灣高階電競硬體架構師、電腦賣場採購顧問與 AI 工作站規劃師。
只使用外部 AI 回答，不要假裝執行本地規則；硬體資料是背景，請用人話判斷。

【本輪規則】
{first_rule}

【重要辨識】
{game_context or '沒有特別遊戲別名。'}

【前文記憶】
{chat_context}

【回答原則】
1. 先回答使用者真正問的問題，不要只重複硬體規格。
2. 必須參考目前硬體評級、簡短評價、升級限制，避免前後矛盾。
3. 問遊戲時，若官方需求不明，請說「以同類型遊戲估算」；不要把異環/NTE 誤判成 Fallout。
4. 低分、無獨顯、老平台，不要把 RAM/SSD 說成大幅提升遊戲/AI；只能說改善流暢度/容量。
5. 筆電通常只能升 RAM/SSD/散熱維護；CPU/GPU 多半不能換。
6. 回答 1000 字內，主流好懂、重點式，不要廢話。

【目前硬體與評價】
{hardware_context}

【使用者最新問題】
{user_text}
""".strip()


def _discover_gemini_models_v34(headers):
    found = []
    for api_version in ("v1beta", "v1"):
        try:
            r = requests.get(f"https://generativelanguage.googleapis.com/{api_version}/models", headers=headers, timeout=(8, 25))
            if r.status_code in (401, 403):
                raise RuntimeError("Gemini API Key 無效、未啟用，或沒有 Gemini API 權限")
            if r.status_code == 429:
                continue
            r.raise_for_status()
            for m in r.json().get("models", []):
                name = (m.get("name", "") or "").replace("models/", "")
                methods = m.get("supportedGenerationMethods", []) or []
                low = name.lower()
                if "generateContent" in methods and "gemini" in low and not any(x in low for x in ["embed", "image", "audio", "tts", "live"]):
                    found.append((api_version, name))
        except RuntimeError:
            raise
        except Exception:
            pass
    def model_priority(item):
        _, name = item
        low = name.lower()
        if "2.5" in low and "flash" in low: return 0
        if "2.0" in low and "flash" in low: return 1
        if "1.5" in low and "flash" in low: return 2
        if "pro" in low: return 3
        return 9
    return sorted(found, key=model_priority)


def _call_gemini_ai(prompt):
    api_key = get_gemini_api_key_v34()
    if not api_key:
        raise RuntimeError(missing_gemini_key_message_v34())
    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
    env_model = os.getenv("GEMINI_MODEL", "").strip().replace("models/", "")
    candidates = []
    if env_model:
        candidates.extend([("v1beta", env_model), ("v1", env_model)])
    candidates.extend(_discover_gemini_models_v34(headers))
    if not candidates:
        candidates = [("v1beta", "gemini-2.5-flash"), ("v1beta", "gemini-2.0-flash"), ("v1beta", "gemini-1.5-flash")]
    seen = set(); dedup = []
    for c in candidates:
        if c not in seen:
            seen.add(c); dedup.append(c)
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.38, "topP": 0.9, "maxOutputTokens": 3200},
    }
    errors = []
    for api_version, model in dedup[:10]:
        url = f"https://generativelanguage.googleapis.com/{api_version}/models/{model}:generateContent"
        for attempt in range(2):
            try:
                r = requests.post(url, headers=headers, json=payload, timeout=(8, 60))
                if r.status_code in (404, 410):
                    errors.append(f"{model}:404")
                    break
                if r.status_code in (401, 403):
                    raise RuntimeError("Gemini API Key 無效或權限不足")
                if r.status_code == 429:
                    time.sleep(1.5 + attempt * 2.5)
                    errors.append(f"{model}:429")
                    continue
                if r.status_code in (500, 502, 503, 504):
                    time.sleep(1.0)
                    errors.append(f"{model}:{r.status_code}")
                    continue
                r.raise_for_status()
                data = r.json()
                parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                answer = "".join(p.get("text", "") for p in parts).strip()
                if answer:
                    return answer
                errors.append(f"{model}:空白")
                break
            except RuntimeError:
                raise
            except Exception as e:
                errors.append(f"{model}:{str(e)[:50]}")
                break
    detail = " | ".join(errors[:8])
    if "429" in detail:
        raise RuntimeError("Gemini 回傳 429：目前請求太密、免費層速率限制或專案配額受限。請等冷卻後再問，或換一組 Key/提高配額。")
    raise RuntimeError("Gemini 外部 AI 無回覆：" + detail)


def external_ai_recommendation(user_text, specs, history=None):
    prompt = build_ai_prompt(user_text, specs, history=history)
    result = _call_gemini_ai(prompt)
    return "🧠 AI 建議:" + chr(10) + result.strip()


COMPUTER_KEYWORDS_V34 = [
    '電腦','筆電','桌機','主機','硬體','配單','組裝','升級','顯卡','gpu','cpu','處理器','ram','記憶體','ssd','硬碟','nvme','螢幕','鍵盤','滑鼠','電源','psu','散熱','風扇',
    '遊戲','跑得動','幀','fps','2k','4k','1080','1440','光追','dlss','fsr','剪輯','直播','ai','模型','推論','生產力',
    '原神','崩鐵','異環','nte','neverness','黑神話','2077','gta','valorant','lol','apex','minecraft','steam',
    'rtx','gtx','radeon','intel','amd','ryzen','core','ultra','xeon','epyc','nvidia','asus','rog','tuf','msi','aorus','legion'
]
GREETING_KEYWORDS_V34 = ['你好','嗨','hi','hello','哈囉','安安']
IRRELEVANT_HINTS_V34 = ['對象','女友','男友','戀愛','告白','星座','算命','政治','股票明牌','色情','黃色笑話']


def looks_like_garbage_v34(text):
    t = re.sub(r'\s+', '', text or '')
    if not t:
        return False
    if len(t) <= 5 and re.fullmatch(r'[0-9a-zA-Z]+', t):
        return True
    ascii_only = re.fullmatch(r'[a-zA-Z0-9_\-]+', t or '') is not None
    if ascii_only and len(t) >= 12:
        vowels = sum(ch in 'aeiouAEIOU' for ch in t)
        if vowels / max(len(t), 1) < 0.22:
            return True
    return False


def is_computer_related_v34(text):
    low = (text or '').lower()
    if any(k.lower() in low for k in COMPUTER_KEYWORDS_V34):
        return True
    if any(g.lower() in low for g in GREETING_KEYWORDS_V34):
        return True
    return False


def is_irrelevant_query_v34(text):
    low = (text or '').lower().strip()
    if not low:
        return False, ""
    if any(k in low for k in IRRELEVANT_HINTS_V34):
        return True, "非電腦硬體/配單/效能問題"
    if looks_like_garbage_v34(text):
        return True, "疑似亂碼或測試字串"
    if not is_computer_related_v34(text):
        # 很短的日常招呼放行；其他無關問題累計。
        if len(low) <= 6 and any(g in low for g in GREETING_KEYWORDS_V34):
            return False, ""
        return True, "和電腦硬體主題無關"
    return False, ""


def v34_ai_guard(self, user_text):
    now = time.time()
    if getattr(self, "ai_locked_until_close", False):
        return False, "AI 顧問已鎖定到本次視窗關閉。原因：無關/亂碼問題累計達 3 次。請關閉程式後重新開啟。"
    bad, reason = is_irrelevant_query_v34(user_text)
    if bad:
        self.ai_irrelevant_count = getattr(self, "ai_irrelevant_count", 0) + 1
        if self.ai_irrelevant_count >= 3:
            self.ai_locked_until_close = True
            if hasattr(self, "ai_button"):
                self.ai_button.configure(state="disabled")
            return False, "AI 顧問已鎖定到本次視窗關閉。原因：無關/亂碼問題累計達 3 次。"
        return False, f"這個工具只回答電腦硬體、配單、升級、遊戲效能、AI/剪輯工作站。\n本次判定：{reason}。\n無關/亂碼累計：{self.ai_irrelevant_count}/3。"
    if now < getattr(self, "ai_cooldown_until", 0):
        remain = int(self.ai_cooldown_until - now)
        return False, f"AI 顧問冷卻中，約 {remain} 秒後可再問。"
    self.ai_request_times = [t for t in getattr(self, "ai_request_times", []) if now - t <= 600]
    self.ai_recent_prompts = [(t, p) for t, p in getattr(self, "ai_recent_prompts", []) if now - t <= 180]
    def lock(seconds, reason):
        self.ai_cooldown_until = time.time() + seconds
        if hasattr(self, "ai_button"):
            self.ai_button.configure(state="disabled")
            self.after(seconds * 1000, lambda: self.ai_button.configure(state="normal") if not getattr(self, "ai_locked_until_close", False) else None)
        return False, f"觸發 AI 使用冷卻：{reason}\n冷卻時間：{seconds} 秒。"
    if self.ai_request_times and now - self.ai_request_times[-1] < 4:
        return lock(20, "兩次提問間隔低於 4 秒")
    if len([t for t in self.ai_request_times if now - t <= 30]) >= 3:
        return lock(60, "30 秒內已提問 3 次")
    if len([t for t in self.ai_request_times if now - t <= 120]) >= 6:
        return lock(180, "120 秒內已提問 6 次")
    if len(self.ai_request_times) >= 12:
        return lock(600, "10 分鐘內已提問 12 次")
    similar_count = sum(1 for _, p in self.ai_recent_prompts if _similar_text(p, user_text) >= 0.92)
    if similar_count >= 2:
        return lock(120, "短時間內重複或高度相似問題達 3 次")
    self.ai_request_times.append(now)
    self.ai_recent_prompts.append((now, user_text))
    return True, ""


def render_ai_history(history):
    if not history:
        return ""
    blocks = []
    for h in history[-5:]:
        q = h.get("user", "")
        a = h.get("assistant", "")
        blocks.append(f"你：{q}\nAI：{a}")
    return "\n\n────────────\n\n".join(blocks)


# 包裝 v33 init：保留可拉動三欄/縮放，但取消持久記憶與清空按鈕。
_v33_1_init_for_v34 = v33_init

def v34_init(self):
    _v33_1_init_for_v34(self)
    self.title(f"電腦檢測升級工具 {V34_VERSION} - [{'筆記型電腦' if self.is_laptop else '桌上型電腦'}]")
    self.ai_history = []
    self.ai_irrelevant_count = 0
    self.ai_locked_until_close = False
    if hasattr(self, "clear_ai_memory_btn"):
        try:
            self.clear_ai_memory_btn.destroy()
        except Exception:
            pass
    if hasattr(self, "ai_response"):
        self.ai_response.configure(text="等待輸入...", text_color="#cccccc")


def v34_run_ai_advisor(self):
    user_text = self.ai_input.get().strip()
    if not user_text:
        self.ai_response.configure(text="請先輸入需求，例如：可以跑異環 NTE 嗎、10萬含螢幕怎麼配、想剪輯要升什麼。", text_color="#ffaa00")
        return
    user_text = normalize_user_query(user_text)
    ok, msg = self.v34_ai_guard(user_text)
    if not ok:
        self.ai_response.configure(text=msg, text_color="#ffaa00")
        return
    if hasattr(self, "ai_button"):
        self.ai_button.configure(state="disabled")
    self.ai_response.configure(text="⏳ 外部 Gemini AI 分析中...\n本次視窗內會保留前文記憶；關閉程式後自動重來。", text_color="#cccccc")
    def task():
        try:
            result = external_ai_recommendation(user_text, self.specs, history=self.ai_history)
            clean_answer = result.replace("🧠 AI 建議:\n", "", 1).strip()
            self.ai_history.append({"time": int(time.time()), "user": user_text, "assistant": clean_answer})
            self.ai_history = self.ai_history[-AI_MEMORY_MAX_TURNS:]
            display = render_ai_history(self.ai_history)
            self.ui_safe(lambda display=display: self.ai_response.configure(text=display, text_color="#00ff00"))
        except Exception as e:
            msg = re.sub(r"AIza[0-9A-Za-z_\-]+", "AIza***", str(e))
            self.ui_safe(lambda msg=msg: self.ai_response.configure(text="⚠️ 外部 AI 連線失敗：\n" + msg, text_color="#ff5555"))
        finally:
            def unlock():
                if hasattr(self, "ai_button") and time.time() >= getattr(self, "ai_cooldown_until", 0) and not getattr(self, "ai_locked_until_close", False):
                    self.ai_button.configure(state="normal")
            self.ui_safe(unlock)
    threading.Thread(target=task, daemon=True).start()


# 覆寫 ROGApp 方法
ROGApp.__init__ = v34_init
ROGApp.v34_ai_guard = v34_ai_guard
ROGApp.run_ai_advisor = v34_run_ai_advisor



# ==========================================
# v35：公用帳 API 輕度隱藏、免設定啟用、保留外部 AI only / 記憶 / 冷卻 / 防濫用
# ==========================================
V35_VERSION = "v35_public_api_hidden_guard"

# 說明：桌面程式無法真正保護 API Key，只能避免在 .py / exe 字串中被一眼搜到。
# 這裡採用：Base85 + XOR + 分段重組。可擋一般使用者與簡單反編譯搜尋，不是絕對防護。
# 進階保護仍應搭配 Google Cloud API 限額、用量監控、來源限制與必要時停用/輪替 Key。
import base64 as _v35_b64
import hashlib as _v35_hashlib

_V35_KEY_CHUNKS = [
    "MWLRnFiXw", "5Zqld8<Ju", "osCf", "uc|IUBm~_", "4!rT35Gz_", "$4O|Ro}nC"
]
_V35_KEY_ORDER = [1, 3, 5, 0, 4, 2]
_V35_SECRET = b"ROGHardwareAI_v35_public_desktop_guard"


def _embedded_gemini_key_v35():
    try:
        token = "".join(_V35_KEY_CHUNKS[i] for i in _V35_KEY_ORDER)
        raw = _v35_b64.b85decode(token.encode("ascii"))
        mask = _v35_hashlib.sha256(_V35_SECRET).digest()
        out = bytes((b ^ mask[i % len(mask)] ^ ((i * 17 + 53) & 0xFF)) for i, b in enumerate(raw))
        val = out.decode("utf-8", errors="ignore").strip()
        if val.startswith("AIza") and len(val) >= 30:
            return val
    except Exception:
        pass
    return ""


# v35 讀取順序：環境變數 / AppData檔 / secrets檔 / 內建輕度隱藏公用 Key。
def get_gemini_api_key_v35():
    for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_AI_API_KEY"):
        val = os.getenv(name, "").strip()
        if val:
            return val
    for p in gemini_key_paths_v34():
        try:
            if os.path.exists(p):
                val = open(p, "r", encoding="utf-8").read().strip().splitlines()[0].strip()
                if val:
                    return val
        except Exception:
            pass
    return _embedded_gemini_key_v35()


def missing_gemini_key_message_v35():
    return (
        "Gemini API Key 無法載入。\n"
        "正常版本會自動使用內建公用 Key；若你看到這段，代表內建 Key 解碼失敗或已被移除。\n"
        "可改用環境變數 GEMINI_API_KEY，或在 AppData/ROGHardwareAI/gemini_api_key.txt 放入 Key。"
    )


# 覆寫 v34 的 Key 讀取函式，讓既有 _call_gemini_ai 直接吃 v35 的免設定 Key。
get_gemini_api_key_v34 = get_gemini_api_key_v35
missing_gemini_key_message_v34 = missing_gemini_key_message_v35


# v35：更保守一點的 API 防刷，避免公用 Key 被短時間大量打爆。
def v35_ai_guard(self, user_text):
    now = time.time()
    if getattr(self, "ai_locked_until_close", False):
        return False, "AI 顧問已鎖定到本次視窗關閉。原因：無關/亂碼問題累計達 3 次。請關閉程式後重新開啟。"

    bad, reason = is_irrelevant_query_v34(user_text)
    if bad:
        self.ai_irrelevant_count = getattr(self, "ai_irrelevant_count", 0) + 1
        if self.ai_irrelevant_count >= 3:
            self.ai_locked_until_close = True
            if hasattr(self, "ai_button"):
                self.ai_button.configure(state="disabled")
            return False, "AI 顧問已鎖定到本次視窗關閉。原因：無關/亂碼問題累計達 3 次。"
        return False, (
            "這個 AI 顧問只回答電腦硬體、配單、升級、遊戲效能、AI/剪輯工作站。\n"
            f"本次判定：{reason}\n"
            f"無關/亂碼累計：{self.ai_irrelevant_count}/3。"
        )

    if now < getattr(self, "ai_cooldown_until", 0):
        remain = int(self.ai_cooldown_until - now)
        return False, f"AI 顧問冷卻中，約 {remain} 秒後可再問。"

    self.ai_request_times = [t for t in getattr(self, "ai_request_times", []) if now - t <= 900]
    self.ai_recent_prompts = [(t, p) for t, p in getattr(self, "ai_recent_prompts", []) if now - t <= 240]

    def lock(seconds, reason):
        self.ai_cooldown_until = time.time() + seconds
        if hasattr(self, "ai_button"):
            self.ai_button.configure(state="disabled")
            self.after(seconds * 1000, lambda: self.ai_button.configure(state="normal") if not getattr(self, "ai_locked_until_close", False) else None)
        return False, f"觸發 AI 使用冷卻：{reason}\n冷卻時間：{seconds} 秒。"

    # 公用 Key 版：比 v34 稍微更保守，防止連點或腳本刷問。
    if self.ai_request_times and now - self.ai_request_times[-1] < 5:
        return lock(30, "兩次提問間隔低於 5 秒")
    if len([t for t in self.ai_request_times if now - t <= 45]) >= 3:
        return lock(90, "45 秒內已提問 3 次")
    if len([t for t in self.ai_request_times if now - t <= 180]) >= 6:
        return lock(240, "180 秒內已提問 6 次")
    if len([t for t in self.ai_request_times if now - t <= 900]) >= 14:
        return lock(900, "15 分鐘內已提問 14 次")

    similar_count = sum(1 for _, p in self.ai_recent_prompts if _similar_text(p, user_text) >= 0.92)
    if similar_count >= 2:
        return lock(180, "短時間內重複或高度相似問題達 3 次")

    self.ai_request_times.append(now)
    self.ai_recent_prompts.append((now, user_text))
    return True, ""


# v35：錯誤訊息不要吐出模型完整技術細節，也避免任何 Key 外洩。
def v35_run_ai_advisor(self):
    user_text = self.ai_input.get().strip()
    if not user_text:
        self.ai_response.configure(text="請先輸入需求，例如：可以跑異環 NTE 嗎、10萬含螢幕怎麼配、想剪輯要升什麼。", text_color="#ffaa00")
        return
    user_text = normalize_user_query(user_text)
    ok, msg = self.v35_ai_guard(user_text)
    if not ok:
        self.ai_response.configure(text=msg, text_color="#ffaa00")
        return
    if hasattr(self, "ai_button"):
        self.ai_button.configure(state="disabled")
    self.ai_response.configure(text="⏳ 外部 Gemini AI 分析中...", text_color="#cccccc")

    def task():
        try:
            result = external_ai_recommendation(user_text, self.specs, history=self.ai_history)
            clean_answer = result.replace("🧠 AI 建議:\n", "", 1).strip()
            self.ai_history.append({"time": int(time.time()), "user": user_text, "assistant": clean_answer})
            self.ai_history = self.ai_history[-AI_MEMORY_MAX_TURNS:]
            display = render_ai_history(self.ai_history)
            self.ui_safe(lambda display=display: self.ai_response.configure(text=display, text_color="#00ff00"))
        except Exception as e:
            raw = str(e)
            raw = re.sub(r"AIza[0-9A-Za-z_\-]+", "AIza***", raw)
            if "429" in raw or "quota" in raw.lower() or "rate" in raw.lower():
                msg = "外部 AI 目前請求過密或配額暫時受限，請稍等 1～3 分鐘再試。"
            elif "401" in raw or "403" in raw or "權限" in raw or "Key" in raw:
                msg = "外部 AI 金鑰或權限異常，請確認公用 Key 是否仍可用。"
            else:
                msg = "外部 AI 暫時連線失敗，請稍後再試。"
            self.ui_safe(lambda msg=msg: self.ai_response.configure(text="⚠️ " + msg, text_color="#ff5555"))
        finally:
            def unlock():
                if hasattr(self, "ai_button") and time.time() >= getattr(self, "ai_cooldown_until", 0) and not getattr(self, "ai_locked_until_close", False):
                    self.ai_button.configure(state="normal")
            self.ui_safe(unlock)

    threading.Thread(target=task, daemon=True).start()


_v34_init_for_v35 = v34_init

def v35_init(self):
    _v34_init_for_v35(self)
    self.title(f"電腦檢測升級工具 {V35_VERSION} - [{'筆記型電腦' if self.is_laptop else '桌上型電腦'}]")
    # 記憶只存在本次視窗，不落地，不寫 json。
    self.ai_history = []
    self.ai_irrelevant_count = 0
    self.ai_locked_until_close = False
    self.ai_cooldown_until = 0
    self.ai_request_times = []
    self.ai_recent_prompts = []


ROGApp.__init__ = v35_init
ROGApp.v35_ai_guard = v35_ai_guard
ROGApp.run_ai_advisor = v35_run_ai_advisor



# ==========================================
# v35.1：放寬 AI 顧問主題判定，允許未知遊戲名稱 / 最低配備 / 系統需求查詢
# ==========================================
V35_1_VERSION = "v35_1_looser_game_query"

# 額外放行關鍵字：避免像「納克園最低效能需求」被判成無關。
COMPUTER_KEYWORDS_V35_1_EXTRA = [
    '效能','需求','最低需求','最低配備','推薦配備','系統需求','硬體需求','配置','配備','規格','需求是什麼','能不能跑','能跑嗎','跑得起','順跑','流暢','畫質','特效','解析度','幀數','fps',
    'steam','epic','pc','windows','directx','ue5','虛幻5','nexon','遊戲需求','配備需求','開放世界','射擊','rpg','mmo',
    '納克園','nakwon','last paradise','納克園最後的樂園','最後的樂園','異環','neverness to everness','nte'
]

# 明確垃圾 / 明確無關才攔；未知遊戲名、遊戲最低配備、能不能跑，一律交給外部 AI 判斷。
def is_irrelevant_query_v35_1(text):
    raw = text or ''
    low = raw.lower().strip()
    compact = re.sub(r'\s+', '', low)
    if not compact:
        return False, ''

    # 招呼、簡短追問全部放行，讓第一次問「你好」可以正常進外部 AI。
    if any(g in low for g in GREETING_KEYWORDS_V34):
        return False, ''

    # 明確私人/非電腦類問題才算無關。
    if any(k in low for k in IRRELEVANT_HINTS_V34):
        return True, '非電腦硬體/配單/效能問題'

    # 亂碼判定改嚴一點：純短數字不再當亂碼，避免測試/預算輸入被誤殺。
    if re.fullmatch(r'\d{1,8}', compact):
        return False, ''
    ascii_only = re.fullmatch(r'[a-zA-Z0-9_\-]+', compact or '') is not None
    if ascii_only and len(compact) >= 16:
        vowels = sum(ch in 'aeiouAEIOU' for ch in compact)
        if vowels / max(len(compact), 1) < 0.18:
            return True, '疑似亂碼或測試字串'

    # 原本關鍵字 + 新增關鍵字，任一命中就放行。
    keyword_pool = COMPUTER_KEYWORDS_V34 + COMPUTER_KEYWORDS_V35_1_EXTRA
    if any(k.lower() in low for k in keyword_pool):
        return False, ''

    # 放行「某遊戲/某軟體 + 最低/推薦/需求/配備/效能」這種未知名稱查詢。
    if any(x in low for x in ['最低','推薦','需求','配備','配置','規格','效能']) and any(y in low for y in ['是什麼','多少','要什麼','需要什麼','能不能','可以跑','跑得動','跑得起']):
        return False, ''

    # 放行「可以跑 XX 嗎」型句子，就算遊戲名資料庫沒有。
    if ('跑' in low or '玩' in low) and any(x in low for x in ['嗎','不動','得動','得起','順','順跑','可以','能不能']):
        return False, ''

    # 其餘不直接攔截，改交給外部 AI 用電腦顧問身份處理；避免過度誤判。
    return False, ''


def v35_1_ai_guard(self, user_text):
    now = time.time()
    if getattr(self, 'ai_locked_until_close', False):
        return False, 'AI 顧問已鎖定到本次視窗關閉。原因：無關/亂碼問題累計達 3 次。請關閉程式後重新開啟。'

    bad, reason = is_irrelevant_query_v35_1(user_text)
    if bad:
        self.ai_irrelevant_count = getattr(self, 'ai_irrelevant_count', 0) + 1
        if self.ai_irrelevant_count >= 3:
            self.ai_locked_until_close = True
            if hasattr(self, 'ai_button'):
                self.ai_button.configure(state='disabled')
            return False, 'AI 顧問已鎖定到本次視窗關閉。原因：無關/亂碼問題累計達 3 次。'
        return False, (
            '這個 AI 顧問主要回答電腦硬體、配單、升級、遊戲效能、AI/剪輯工作站。\n'
            f'本次判定：{reason}\n'
            f'無關/亂碼累計：{self.ai_irrelevant_count}/3。'
        )

    if now < getattr(self, 'ai_cooldown_until', 0):
        remain = int(self.ai_cooldown_until - now)
        return False, f'AI 顧問冷卻中，約 {remain} 秒後可再問。'

    self.ai_request_times = [t for t in getattr(self, 'ai_request_times', []) if now - t <= 900]
    self.ai_recent_prompts = [(t, p) for t, p in getattr(self, 'ai_recent_prompts', []) if now - t <= 240]

    def lock(seconds, reason):
        self.ai_cooldown_until = time.time() + seconds
        if hasattr(self, 'ai_button'):
            self.ai_button.configure(state='disabled')
            self.after(seconds * 1000, lambda: self.ai_button.configure(state='normal') if not getattr(self, 'ai_locked_until_close', False) else None)
        return False, f'觸發 AI 使用冷卻：{reason}\n冷卻時間：{seconds} 秒。'

    # 保留防刷，但不再因未知遊戲查詢而擋住。
    if self.ai_request_times and now - self.ai_request_times[-1] < 5:
        return lock(30, '兩次提問間隔低於 5 秒')
    if len([t for t in self.ai_request_times if now - t <= 45]) >= 3:
        return lock(90, '45 秒內已提問 3 次')
    if len([t for t in self.ai_request_times if now - t <= 180]) >= 6:
        return lock(240, '180 秒內已提問 6 次')
    if len([t for t in self.ai_request_times if now - t <= 900]) >= 14:
        return lock(900, '15 分鐘內已提問 14 次')

    # 重複問題冷卻稍微放寬，避免使用者修正遊戲名/追問時被誤擋。
    similar_count = sum(1 for _, p in self.ai_recent_prompts if _similar_text(p, user_text) >= 0.96)
    if similar_count >= 3:
        return lock(120, '短時間內重複或高度相似問題過多')

    self.ai_request_times.append(now)
    self.ai_recent_prompts.append((now, user_text))
    return True, ''


def v35_1_run_ai_advisor(self):
    user_text = self.ai_input.get().strip()
    if not user_text:
        self.ai_response.configure(text='請先輸入需求，例如：納克園最低配備是什麼、可以跑異環 NTE 嗎、10萬含螢幕怎麼配。', text_color='#ffaa00')
        return
    user_text = normalize_user_query(user_text)
    ok, msg = self.v35_1_ai_guard(user_text)
    if not ok:
        self.ai_response.configure(text=msg, text_color='#ffaa00')
        return
    if hasattr(self, 'ai_button'):
        self.ai_button.configure(state='disabled')
    self.ai_response.configure(text='⏳ 外部 Gemini AI 分析中...', text_color='#cccccc')

    def task():
        try:
            result = external_ai_recommendation(user_text, self.specs, history=self.ai_history)
            clean_answer = result.replace('🧠 AI 建議:\n', '', 1).strip()
            self.ai_history.append({'time': int(time.time()), 'user': user_text, 'assistant': clean_answer})
            self.ai_history = self.ai_history[-AI_MEMORY_MAX_TURNS:]
            display = render_ai_history(self.ai_history)
            self.ui_safe(lambda display=display: self.ai_response.configure(text=display, text_color='#00ff00'))
        except Exception as e:
            raw = re.sub(r'AIza[0-9A-Za-z_\-]+', 'AIza***', str(e))
            if '429' in raw or 'quota' in raw.lower() or 'rate' in raw.lower():
                msg = '外部 AI 目前請求過密或配額暫時受限，請稍等 1～3 分鐘再試。'
            elif '401' in raw or '403' in raw or '權限' in raw or 'Key' in raw:
                msg = '外部 AI 金鑰或權限異常，請確認公用 Key 是否仍可用。'
            else:
                msg = '外部 AI 暫時連線失敗，請稍後再試。'
            self.ui_safe(lambda msg=msg: self.ai_response.configure(text='⚠️ ' + msg, text_color='#ff5555'))
        finally:
            def unlock():
                if hasattr(self, 'ai_button') and time.time() >= getattr(self, 'ai_cooldown_until', 0) and not getattr(self, 'ai_locked_until_close', False):
                    self.ai_button.configure(state='normal')
            self.ui_safe(unlock)

    threading.Thread(target=task, daemon=True).start()


_v35_init_for_v35_1 = v35_init

def v35_1_init(self):
    _v35_init_for_v35_1(self)
    self.title(f"電腦檢測升級工具 {V35_1_VERSION} - [{'筆記型電腦' if self.is_laptop else '桌上型電腦'}]")


ROGApp.__init__ = v35_1_init
ROGApp.v35_1_ai_guard = v35_1_ai_guard
ROGApp.run_ai_advisor = v35_1_run_ai_advisor



# ==========================================
# v35.2：AI 對話排版優化 - 固定聊天框、可滾輪往上看歷史、送出後自動跳到最新回答
# ==========================================
V35_2_VERSION = "v35_2_ai_chat_scroll_fixed"


def ai_textbox_set(self, text, color="#00ff00"):
    """兼容 CTkTextbox / CTkLabel 的 AI 輸出函式。
    v35.2 之後 AI 回覆會放在固定高度 Textbox 中，避免整個左側面板被歷史訊息拉長。
    每次更新後自動捲到底部，使用者若要看舊問題可在聊天框內往上滾。
    """
    widget = getattr(self, "ai_response", None)
    if widget is None:
        return
    try:
        if isinstance(widget, ctk.CTkTextbox):
            widget.configure(state="normal")
            try:
                widget.configure(text_color=color)
            except Exception:
                pass
            widget.delete("1.0", "end")
            widget.insert("end", str(text))
            widget.configure(state="disabled")
            widget.see("end")
        else:
            widget.configure(text=str(text), text_color=color)
    except Exception:
        try:
            widget.configure(text=str(text), text_color=color)
        except Exception:
            pass


def render_ai_history_v35_2(history):
    if not history:
        return "等待輸入..."
    blocks = []
    for i, h in enumerate(history[-AI_MEMORY_MAX_TURNS:], 1):
        q = str(h.get("user", "")).strip()
        a = str(h.get("assistant", "")).strip()
        blocks.append(f"你：{q}\n\nAI：{a}")
    return "\n\n" + ("\n\n" + "─" * 28 + "\n\n").join(blocks) + "\n"


def v35_2_install_ai_chat_box(self):
    """把原本會一直拉長版面的 Label 換成固定高度、可滾動的聊天框。"""
    old = getattr(self, "ai_response", None)
    if old is None or isinstance(old, ctk.CTkTextbox):
        return
    try:
        parent = old.master
        pack_info = old.pack_info()
        old.destroy()
    except Exception:
        parent = getattr(self, "left_frame", self)
        pack_info = {"anchor": "w", "padx": 20, "pady": 10}

    self.ai_response = ctk.CTkTextbox(
        parent,
        width=430,
        height=360,
        corner_radius=8,
        wrap="word",
        font=ctk.CTkFont(size=14),
        text_color="#00ff00",
        fg_color="#1f1f1f",
        border_width=1,
        border_color="#444444",
    )
    try:
        self.ai_response.pack(**pack_info)
    except Exception:
        self.ai_response.pack(anchor="w", padx=20, pady=10, fill="x")
    ai_textbox_set(self, "等待輸入...", "#cccccc")


_v35_1_init_for_v35_2 = v35_1_init

def v35_2_init(self):
    _v35_1_init_for_v35_2(self)
    self.title(f"電腦檢測升級工具 {V35_2_VERSION} - [{'筆記型電腦' if self.is_laptop else '桌上型電腦'}]")
    v35_2_install_ai_chat_box(self)
    self.ai_history = []
    ai_textbox_set(self, "等待輸入...", "#cccccc")


def v35_2_run_ai_advisor(self):
    user_text = self.ai_input.get().strip()
    if not user_text:
        ai_textbox_set(self, "請先輸入需求，例如：納克園最低配備是什麼、可以跑異環 NTE 嗎、10萬含螢幕怎麼配。", "#ffaa00")
        return

    user_text = normalize_user_query(user_text)
    ok, msg = self.v35_1_ai_guard(user_text)
    if not ok:
        ai_textbox_set(self, msg, "#ffaa00")
        return

    if hasattr(self, 'ai_button'):
        self.ai_button.configure(state='disabled')

    preview_history = list(getattr(self, "ai_history", []))
    preview_history.append({'time': int(time.time()), 'user': user_text, 'assistant': '⏳ 外部 Gemini AI 分析中...'})
    ai_textbox_set(self, render_ai_history_v35_2(preview_history), "#00ff00")

    def task():
        try:
            result = external_ai_recommendation(user_text, self.specs, history=self.ai_history)
            clean_answer = result.replace('🧠 AI 建議:\n', '', 1).strip()
            self.ai_history.append({'time': int(time.time()), 'user': user_text, 'assistant': clean_answer})
            self.ai_history = self.ai_history[-AI_MEMORY_MAX_TURNS:]
            display = render_ai_history_v35_2(self.ai_history)
            self.ui_safe(lambda display=display: ai_textbox_set(self, display, '#00ff00'))
        except Exception as e:
            raw = re.sub(r'AIza[0-9A-Za-z_\-]+', 'AIza***', str(e))
            if '429' in raw or 'quota' in raw.lower() or 'rate' in raw.lower():
                msg = '外部 AI 目前請求過密或配額暫時受限，請稍等 1～3 分鐘再試。'
            elif '401' in raw or '403' in raw or '權限' in raw or 'Key' in raw:
                msg = '外部 AI 金鑰或權限異常，請確認公用 Key 是否仍可用。'
            else:
                msg = '外部 AI 暫時連線失敗，請稍後再試。'
            fail_history = list(getattr(self, "ai_history", []))
            fail_history.append({'time': int(time.time()), 'user': user_text, 'assistant': '⚠️ ' + msg})
            self.ui_safe(lambda fail_history=fail_history: ai_textbox_set(self, render_ai_history_v35_2(fail_history), '#ff5555'))
        finally:
            def unlock():
                if hasattr(self, 'ai_button') and time.time() >= getattr(self, 'ai_cooldown_until', 0) and not getattr(self, 'ai_locked_until_close', False):
                    self.ai_button.configure(state='normal')
            self.ui_safe(unlock)

    threading.Thread(target=task, daemon=True).start()


ROGApp.__init__ = v35_2_init
ROGApp.run_ai_advisor = v35_2_run_ai_advisor


# ==========================================
# v36：AI 聊天框滾輪隔離、公告視窗、版本同步、對話雙色、RAM 升級判斷修復
# ==========================================
V36_VERSION = "v36_ui_ai_scroll_notice"


def _is_descendant_of_ctk_textbox_v36(widget):
    """判斷事件來源是否在 CTkTextbox 內部。
    CTkTextbox 裡面包著原生 tkinter Text，event.widget 常常不是 CTkTextbox 本體，
    所以要往 master 一路找，才能避免聊天框滾輪同時帶動左側整頁。
    """
    cur = widget
    while cur is not None:
        try:
            if isinstance(cur, ctk.CTkTextbox):
                return True
        except Exception:
            pass
        cur = getattr(cur, "master", None)
    return False


def _textbox_wheel_break_v36(event):
    """讓 AI 聊天框自己滾，不往外層 ScrollableFrame 冒泡。"""
    try:
        widget = event.widget
        if getattr(event, "num", None) == 5 or getattr(event, "delta", 0) < 0:
            direction = 1
        elif getattr(event, "num", None) == 4 or getattr(event, "delta", 0) > 0:
            direction = -1
        else:
            return "break"
        widget.yview_scroll(direction * 3, "units")
    except Exception:
        pass
    return "break"


# 覆蓋全域滾輪：若來源在 CTkTextbox 內，直接放過/阻斷，不再滾外層。
def v36_on_mousewheel(self, event):
    if _is_descendant_of_ctk_textbox_v36(event.widget):
        return "break"
    if isinstance(event.widget, ctk.CTkEntry):
        return "break"
    scrollable = self._find_scrollable_parent(event.widget)
    if scrollable is None:
        return None
    try:
        if getattr(event, "num", None) == 5 or getattr(event, "delta", 0) < 0:
            direction = 1
        elif getattr(event, "num", None) == 4 or getattr(event, "delta", 0) > 0:
            direction = -1
        else:
            return None
        scrollable._parent_canvas.yview_scroll(direction * 3, "units")
    except Exception:
        pass
    return "break"


def hardware_upgrade_suggestions_v36(specs, scores):
    """修正 31.4G 被判斷小於 32G 的問題：升級邏輯改用標稱容量。"""
    is_laptop = specs.get("is_laptop", False)
    ram_real = specs.get("ram_total", 0)
    try:
        ram_nominal = float(nominal_capacity_gb(ram_real))
    except Exception:
        ram_nominal = float(ram_real or 0)
    disk_total = specs.get("disk_total", 0)
    disk_used = specs.get("disk_used", 0)
    vram = specs.get("gpu_vram", 0)
    total = scores.get("Total", 0)
    support_gen5 = specs.get("support_gen5", False)
    limited = is_very_limited_machine(specs, scores)
    flags = hardware_limit_flags(specs)
    items = []

    if limited:
        items.append("整機判斷：目前平台/顯示能力偏弱，RAM/SSD 只能延命，不能讓 3A 或 AI 體驗大幅起飛。")
        if ram_nominal < 16:
            items.append("RAM：若此機可擴充，可補到 16G；若是板載不可升級，就不建議再投太多。")
        elif ram_nominal < 32:
            items.append("RAM：若此機可擴充，可補到 32G；但這只改善多工，不會讓遊戲/AI 效能翻身。")
        else:
            items.append(f"RAM：目前 {ram_label(ram_real, include_real=False)} 已足夠，不是優先瓶頸。")
        if disk_total and (disk_total < 900 or (disk_used / max(disk_total, 1)) > 0.75):
            items.append("SSD：可補 1TB 當資料/遊戲碟，但這是容量改善，不是效能翻身。")
        if is_laptop:
            items.append("筆電限制：CPU/GPU 多半不能換；若要 2K/4K 3A、剪輯或 AI，建議直接買 RTX 5070 以上筆電或桌機。")
        else:
            items.append("桌機方向：若機殼/電供/主板太舊，與其零碎升級，不如整機重組較乾脆。")
        return "可升級建議:" + chr(10) + chr(10).join(["• " + x for x in items]) + chr(10) + "整體建議：先確認是否可升 RAM/SSD；若目標是遊戲/AI，優先看新機。"

    if ram_nominal < 16:
        items.append(f"RAM：優先升到 16G 或 32G（目前 {ram_label(ram_real, include_real=False)}，體感提升最大）。")
    elif ram_nominal < 32:
        items.append(f"RAM：若要剪輯、AI、多開遊戲，建議升到 32G（目前 {ram_label(ram_real, include_real=False)}）。")
    elif ram_nominal < 64:
        items.append(f"RAM：目前 {ram_label(ram_real, include_real=False)} 已夠用，除非重度剪輯/AI 才考慮 64G+。")
    else:
        items.append(f"RAM：目前 {ram_label(ram_real, include_real=False)} 屬於充裕，不是升級優先項。")

    if disk_total and (disk_total < 900 or (disk_used / max(disk_total, 1)) > 0.75):
        gen = "Gen5" if support_gen5 else "Gen4"
        items.append(f"SSD：建議加 1TB / 2TB {gen} NVMe，遊戲與素材庫會更舒服。")
    else:
        items.append("SSD：容量暫時可用，可等價格好再補 2TB 遊戲碟。")

    if is_laptop:
        if vram < 8000:
            items.append("筆電 GPU/CPU 多半不能換；若要 2K/4K 3A 或 AI，建議直接看 RTX 5070 / 5080 / 5090 筆電或桌機。")
        items.append("筆電可升級重點：RAM、SSD、散熱清灰/重上散熱膏、外接螢幕與鍵鼠。")
        if flags:
            items.append("限制提醒：" + "；".join(flags[:2]) + "。")
    else:
        if vram < 8000:
            items.append("顯卡：若要遊戲分數大幅提升，建議 RTX 4060 Ti / 5070 / 5070 Ti 以上。")
        elif vram < 12000:
            items.append("顯卡：2K 高刷可考慮 RTX 5070 Ti / 5080；AI 則看 VRAM 16G+。")
        else:
            items.append("顯卡：目前 VRAM 充足，可先看 CPU/RAM/SSD 是否拖後腿。")
        items.append("電供：升級中高階顯卡前，確認 750W/850W/1000W 與 12V-2x6/PCIe 5.0 線材。")
        items.append("主機板/平台：若 CPU 分數偏低，可評估 AM5 / LGA1851 新平台，但要連 RAM/主板一起看。")

    if total < 35000:
        verdict = "整體建議：若只是文書可補 RAM/SSD；若要 3A/AI，建議新機。"
    elif total < 65000:
        verdict = "整體建議：中階可用，升級 GPU/SSD 會最有感。"
    else:
        verdict = "整體建議：效能已不差，升級要針對你的場景，不必盲目全換。"
    return "可升級建議:" + chr(10) + chr(10).join(["• " + x for x in items]) + chr(10) + verdict


# 讓後續所有地方都用 v36 的升級建議邏輯。
hardware_upgrade_suggestions = hardware_upgrade_suggestions_v36


def _refresh_topbar_version_v36(self):
    try:
        self.title(f"電腦檢測升級工具 {V36_VERSION} - [{'筆記型電腦' if self.is_laptop else '桌上型電腦'}]")
    except Exception:
        pass
    try:
        for child in getattr(self, "topbar", []).winfo_children():
            try:
                txt = child.cget("text")
            except Exception:
                continue
            if "電腦硬體 AI 顧問" in str(txt):
                child.configure(text=f"電腦硬體 AI 顧問 {V36_VERSION}")
                break
    except Exception:
        pass


def show_startup_notice_v36(self):
    """啟動公告：確認後才進入主程式。"""
    dialog = ctk.CTkToplevel(self)
    dialog.title("v36 版本公告")
    dialog.geometry("620x320")
    dialog.resizable(False, False)
    dialog.attributes("-topmost", True)
    try:
        dialog.transient(self)
        dialog.grab_set()
    except Exception:
        pass

    frame = ctk.CTkFrame(dialog, corner_radius=14)
    frame.pack(fill="both", expand=True, padx=18, pady=18)
    ctk.CTkLabel(frame, text="電腦檢測升級工具 v36", font=ctk.CTkFont(size=22, weight="bold"), text_color="#00ffff").pack(anchor="w", padx=22, pady=(18, 10))
    notice = (
        "• AI 對話框滾輪獨立，查看回覆時不會帶動整頁。\n"
        "• 新回覆會從最新問題開頭顯示，可自行往下看完整內容。\n"
        "• 修正 32G 記憶體仍建議升 32G，並同步版本顯示。\n\n"
        "因為近期 AI 市場需求大幅提升，有無貨或未上架價格不正確，還請以購買網站為準。\n\n"
        "研發版本不代表最終品質。"
    )
    ctk.CTkLabel(frame, text=notice, justify="left", wraplength=560, font=ctk.CTkFont(size=15), text_color="#dddddd").pack(anchor="w", padx=22, pady=6)
    btn = ctk.CTkButton(frame, text="確認進入", width=160, height=38, fg_color="#0066cc", command=dialog.destroy)
    btn.pack(pady=(10, 18))

    try:
        dialog.update_idletasks()
        x = self.winfo_screenwidth() // 2 - 310
        y = self.winfo_screenheight() // 2 - 160
        dialog.geometry(f"620x320+{x}+{y}")
    except Exception:
        pass
    self.wait_window(dialog)


def _configure_ai_text_tags_v36(widget):
    try:
        t = widget._textbox
    except Exception:
        t = widget
    try:
        t.tag_configure("user", foreground="#6bb6ff")
        t.tag_configure("ai", foreground="#00ff66")
        t.tag_configure("wait", foreground="#cccccc")
        t.tag_configure("error", foreground="#ff6666")
        t.tag_configure("warn", foreground="#ffaa00")
        t.tag_configure("sep", foreground="#777777")
    except Exception:
        pass


def ai_chat_render_v36(self, history=None, pending=None, warning=None, error=None):
    """AI 聊天框雙色顯示，並捲到最新問題開頭，而不是直接跳到底部。"""
    widget = getattr(self, "ai_response", None)
    if widget is None:
        return
    if not isinstance(widget, ctk.CTkTextbox):
        try:
            widget.configure(text=str(warning or error or "等待輸入..."), text_color="#cccccc")
        except Exception:
            pass
        return

    history = list(history or getattr(self, "ai_history", []))
    rows = []
    for h in history[-AI_MEMORY_MAX_TURNS:]:
        rows.append((str(h.get("user", "")).strip(), str(h.get("assistant", "")).strip(), "normal"))
    if pending:
        rows.append((str(pending.get("user", "")).strip(), str(pending.get("assistant", "⏳ 外部 Gemini AI 分析中...")).strip(), "pending"))
    if warning:
        rows.append(("系統", str(warning), "warn"))
    if error:
        rows.append(("系統", str(error), "error"))

    try:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        _configure_ai_text_tags_v36(widget)
        t = widget._textbox if hasattr(widget, "_textbox") else widget
        latest_start = "1.0"
        if not rows:
            t.insert("end", "等待輸入...", "wait")
        else:
            for i, (q, a, kind) in enumerate(rows):
                latest_start = t.index("end-1c")
                if i > 0:
                    t.insert("end", "\n\n" + "─" * 28 + "\n\n", "sep")
                    latest_start = t.index("end-1c")
                if kind in ("warn", "error") and q == "系統":
                    tag = "warn" if kind == "warn" else "error"
                    t.insert("end", str(a), tag)
                else:
                    t.insert("end", "你：", "user")
                    t.insert("end", q + "\n\n", "user")
                    tag = "wait" if kind == "pending" else "ai"
                    t.insert("end", "AI：", tag)
                    t.insert("end", a, tag)
        widget.configure(state="disabled")
        try:
            # 顯示最新問答的開頭，讓使用者自然往下滾看完整回答。
            t.see(latest_start)
        except Exception:
            widget.see(latest_start)
    except Exception:
        try:
            widget.configure(state="disabled")
        except Exception:
            pass


# 為舊呼叫提供兼容，但不再直接 see('end')。
def ai_textbox_set_v36(self, text, color="#00ff00"):
    if color in ("#ff5555", "#ff6666"):
        ai_chat_render_v36(self, error=text)
    elif color in ("#ffaa00", "#ffff00"):
        ai_chat_render_v36(self, warning=text)
    elif str(text).strip() == "等待輸入...":
        ai_chat_render_v36(self, history=[])
    else:
        widget = getattr(self, "ai_response", None)
        if isinstance(widget, ctk.CTkTextbox):
            try:
                widget.configure(state="normal")
                widget.delete("1.0", "end")
                _configure_ai_text_tags_v36(widget)
                t = widget._textbox if hasattr(widget, "_textbox") else widget
                t.insert("end", str(text), "ai")
                widget.configure(state="disabled")
                t.see("1.0")
                return
            except Exception:
                pass
        try:
            widget.configure(text=str(text), text_color=color)
        except Exception:
            pass


ai_textbox_set = ai_textbox_set_v36


_old_v35_2_install_ai_chat_box = v35_2_install_ai_chat_box

def v36_install_ai_chat_box(self):
    _old_v35_2_install_ai_chat_box(self)
    widget = getattr(self, "ai_response", None)
    if isinstance(widget, ctk.CTkTextbox):
        _configure_ai_text_tags_v36(widget)
        try:
            inner = widget._textbox if hasattr(widget, "_textbox") else widget
            inner.bind("<MouseWheel>", _textbox_wheel_break_v36, add="+")
            inner.bind("<Button-4>", _textbox_wheel_break_v36, add="+")
            inner.bind("<Button-5>", _textbox_wheel_break_v36, add="+")
            widget.bind("<MouseWheel>", _textbox_wheel_break_v36, add="+")
            widget.bind("<Button-4>", _textbox_wheel_break_v36, add="+")
            widget.bind("<Button-5>", _textbox_wheel_break_v36, add="+")
        except Exception:
            pass
        ai_chat_render_v36(self, history=[])


_old_v35_2_run_ai_advisor = v35_2_run_ai_advisor

def v36_run_ai_advisor(self):
    user_text = self.ai_input.get().strip()
    if not user_text:
        ai_chat_render_v36(self, warning="請先輸入需求，例如：納克園最低配備是什麼、可以跑異環 NTE 嗎、10萬含螢幕怎麼配。")
        return

    user_text = normalize_user_query(user_text)
    ok, msg = self.v35_1_ai_guard(user_text)
    if not ok:
        ai_chat_render_v36(self, warning=msg)
        return

    if hasattr(self, "ai_button"):
        self.ai_button.configure(state="disabled")

    pending = {"time": int(time.time()), "user": user_text, "assistant": "⏳ 外部 Gemini AI 分析中..."}
    ai_chat_render_v36(self, history=getattr(self, "ai_history", []), pending=pending)

    def task():
        try:
            result = external_ai_recommendation(user_text, self.specs, history=self.ai_history)
            clean_answer = result.replace("🧠 AI 建議:\n", "", 1).strip()
            self.ai_history.append({"time": int(time.time()), "user": user_text, "assistant": clean_answer})
            self.ai_history = self.ai_history[-AI_MEMORY_MAX_TURNS:]
            self.ui_safe(lambda: ai_chat_render_v36(self, history=self.ai_history))
        except Exception as e:
            raw = re.sub(r"AIza[0-9A-Za-z_\-]+", "AIza***", str(e))
            if "429" in raw or "quota" in raw.lower() or "rate" in raw.lower():
                msg = "外部 AI 目前請求過密或配額暫時受限，請稍等 1～3 分鐘再試。"
            elif "401" in raw or "403" in raw or "權限" in raw or "Key" in raw:
                msg = "外部 AI 金鑰或權限異常，請確認公用 Key 是否仍可用。"
            else:
                msg = "外部 AI 暫時連線失敗，請稍後再試。"
            self.ui_safe(lambda msg=msg: ai_chat_render_v36(self, history=getattr(self, "ai_history", []), error="⚠️ " + msg))
        finally:
            def unlock():
                if hasattr(self, "ai_button") and time.time() >= getattr(self, "ai_cooldown_until", 0) and not getattr(self, "ai_locked_until_close", False):
                    self.ai_button.configure(state="normal")
            self.ui_safe(unlock)

    threading.Thread(target=task, daemon=True).start()


_old_v35_2_init = v35_2_init

def v36_init(self):
    # 先隱藏主視窗，初始化完成後跳公告，按確認才顯示主程式。
    try:
        self.withdraw()
    except Exception:
        pass
    _old_v35_2_init(self)
    _refresh_topbar_version_v36(self)
    v36_install_ai_chat_box(self)
    try:
        show_startup_notice_v36(self)
    except Exception:
        pass
    try:
        self.deiconify()
        self.after(120, lambda: self.state("zoomed"))
    except Exception:
        pass


ROGApp.__init__ = v36_init
ROGApp._on_mousewheel = v36_on_mousewheel
ROGApp.run_ai_advisor = v36_run_ai_advisor
v35_2_install_ai_chat_box = v36_install_ai_chat_box



# ============================================================
# v37：AI 區獨立中欄、購物車整合到操作面板、修復聊天顯示與分析中字樣
# ============================================================
V37_VERSION = "v37"
AI_PENDING_TEXT_V37 = "⏳ 分析中..."


# 保留原本操作面板建構函式，v37 會把它放到右側工作區。
_v37_original_setup_mid_panel = ROGApp.setup_mid_panel


def setup_left_panel_v37(self):
    """左側只保留硬體檢測 / 評分 / 升級建議，不再塞 AI 顧問。"""
    ctk.CTkLabel(self.left_frame, text="[ SYSTEM SPECS ]", font=ctk.CTkFont(size=17, weight="bold"), text_color="#00ffff").pack(anchor="w", padx=20, pady=(15, 2))
    ctk.CTkLabel(self.left_frame, text=f"CPU: {self.specs['cpu_name']}", justify="left", wraplength=460).pack(anchor="w", padx=20, pady=2)
    freq = "5600" if self.specs.get('support_gen5') else "3200"
    ctk.CTkLabel(self.left_frame, text=f"RAM: {ram_label(self.specs['ram_total'])} (已用: {self.specs['ram_used']}G) [{self.specs['ram_type']} {freq}]", justify="left", wraplength=460).pack(anchor="w", padx=20, pady=2)
    ctk.CTkLabel(self.left_frame, text=f"GPU: {self.specs['gpu_name']}\nVRAM: {self.specs['gpu_vram']} MB (已用: {self.specs['gpu_vram_used']} MB)", justify="left", wraplength=460).pack(anchor="w", padx=20, pady=2)

    disk_lines = []
    for idx, d in enumerate(self.specs.get('disks', []), 1):
        size = d.get('size_gb', 0)
        model = d.get('model', 'Unknown Disk')
        disk_lines.append(f"Disk {idx}: {model} / {size} GB（已用: {d.get('used_gb', 0)}G）")
    if not disk_lines:
        disk_lines.append(f"Disk: 總共 {self.specs['disk_total']} GB (已用: {self.specs['disk_used']}G)")
    ctk.CTkLabel(self.left_frame, text="\n".join(disk_lines), justify="left", text_color="#aaaaaa", wraplength=460).pack(anchor="w", padx=20, pady=2)

    if not self.specs.get('is_laptop'):
        ctk.CTkLabel(self.left_frame, text=f"MOBO: {self.specs.get('mobo', '未知')}", justify="left", text_color="#aaaaaa", wraplength=460).pack(anchor="w", padx=20, pady=2)
        ctk.CTkLabel(self.left_frame, text=f"PSU: {self.specs.get('psu', '未知')}", justify="left", text_color="#aaaaaa", wraplength=460).pack(anchor="w", padx=20, pady=2)
        fan_rows = self.specs.get('cooling_fans', [])
        fan_text = '散熱/風扇: ' + (' / '.join(fan_rows) if fan_rows else self.specs.get('cooler_note', '讀不到風扇感測器'))
        ctk.CTkLabel(self.left_frame, text=fan_text, justify="left", text_color="#aaaaaa", wraplength=460).pack(anchor="w", padx=20, pady=2)

    mem_sticks = self.specs.get('memory_sticks', [])
    if mem_sticks:
        mem_text = "RAM 模組：" + " / ".join([f"{s.get('capacity_gb')}G {s.get('speed','')}" for s in mem_sticks if s.get('capacity_gb')])
        ctk.CTkLabel(self.left_frame, text=mem_text, justify="left", text_color="#aaaaaa", wraplength=460).pack(anchor="w", padx=20, pady=2)

    ctk.CTkLabel(self.left_frame, text="[ BENCHMARK SCORES ]", font=ctk.CTkFont(size=17, weight="bold"), text_color="#00ffff").pack(anchor="w", padx=20, pady=(15, 2))
    ctk.CTkLabel(self.left_frame, text=f"CPU Score: {self.scores['CPU']:,} pts").pack(anchor="w", padx=30, pady=1)
    ctk.CTkLabel(self.left_frame, text=f"RAM Score: {self.scores['RAM']:,} pts").pack(anchor="w", padx=30, pady=1)
    ctk.CTkLabel(self.left_frame, text=f"GPU Score: {self.scores['GPU']:,} pts").pack(anchor="w", padx=30, pady=1)
    ctk.CTkLabel(self.left_frame, text=f"AI Score:    {self.scores['AI_Score']:,} pts", text_color="#ff55ff").pack(anchor="w", padx=30, pady=1)
    total_color = "#00ff00" if self.scores['Total'] > 80000 else "#ffaa00"
    ctk.CTkLabel(self.left_frame, text=f"TOTAL: {self.scores['Total']:,}", font=ctk.CTkFont(size=24, weight="bold"), text_color=total_color).pack(anchor="w", padx=20, pady=(10, 10))
    ctk.CTkLabel(self.left_frame, text=hardware_scene_analysis(self.specs, self.scores), text_color="#00ff99", justify="left", wraplength=460).pack(anchor="w", padx=20, pady=(0, 8))
    ctk.CTkLabel(self.left_frame, text=hardware_upgrade_suggestions(self.specs, self.scores), text_color="#ffee88", justify="left", wraplength=460).pack(anchor="w", padx=20, pady=(0, 16))


def setup_ai_panel_v37(self):
    """中間靠左的 AI 對話欄。"""
    self.ai_frame.grid_columnconfigure(0, weight=1)
    self.ai_frame.grid_rowconfigure(5, weight=1)

    ctk.CTkLabel(self.ai_frame, text="[ 結構化 AI 顧問 ]", font=ctk.CTkFont(size=18, weight="bold"), text_color="#ff55ff").grid(row=0, column=0, sticky="w", padx=18, pady=(16, 10))
    self.ai_input = ctk.CTkEntry(
        self.ai_frame,
        placeholder_text="輸入需求：例 10萬含螢幕、納克園最低配備、可以跑異環 NTE 嗎",
        height=34,
    )
    self.ai_input.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 10))

    btn_row = ctk.CTkFrame(self.ai_frame, fg_color="transparent")
    btn_row.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 8))
    btn_row.grid_columnconfigure((0, 1), weight=1)
    self.ai_button = ctk.CTkButton(btn_row, text="🧠 AI 分析與決策", command=self.run_ai_advisor, fg_color="#660066", height=36)
    self.ai_button.grid(row=0, column=0, sticky="ew", padx=(0, 8))
    ctk.CTkButton(btn_row, text="↵ 送出", command=self.run_ai_advisor, fg_color="#444444", height=36).grid(row=0, column=1, sticky="ew", padx=(8, 0))

    ctk.CTkLabel(
        self.ai_frame,
        text="本次開啟期間會記住上下文；關閉視窗後重置。",
        text_color="#aaaaaa",
        font=ctk.CTkFont(size=12),
    ).grid(row=3, column=0, sticky="w", padx=20, pady=(0, 6))

    self.ai_response = ctk.CTkTextbox(
        self.ai_frame,
        corner_radius=10,
        wrap="word",
        font=ctk.CTkFont(size=14),
        fg_color="#1f1f1f",
        border_width=1,
        border_color="#444444",
        activate_scrollbars=True,
    )
    self.ai_response.grid(row=5, column=0, sticky="nsew", padx=14, pady=(4, 14))
    _configure_ai_text_tags_v36(self.ai_response)
    try:
        inner = self.ai_response._textbox if hasattr(self.ai_response, "_textbox") else self.ai_response
        inner.bind("<MouseWheel>", _textbox_wheel_break_v36, add="+")
        inner.bind("<Button-4>", _textbox_wheel_break_v36, add="+")
        inner.bind("<Button-5>", _textbox_wheel_break_v36, add="+")
        self.ai_response.bind("<MouseWheel>", _textbox_wheel_break_v36, add="+")
        self.ai_response.bind("<Button-4>", _textbox_wheel_break_v36, add="+")
        self.ai_response.bind("<Button-5>", _textbox_wheel_break_v36, add="+")
    except Exception:
        pass
    ai_chat_render_v37(self, history=[])

    try:
        self.ai_input.bind("<Return>", lambda event: self.run_ai_advisor())
    except Exception:
        pass


def setup_right_panel_v37(self):
    """把智慧清單整合到操作面板下方；空車時縮小。"""
    self.cart_section = ctk.CTkFrame(self.mid_frame, corner_radius=10)
    self.cart_section.pack(fill="x", padx=20, pady=(16, 18))
    ctk.CTkLabel(self.cart_section, text="[ 智慧清單 CART ]", font=ctk.CTkFont(size=16, weight="bold"), text_color="#00ff00").pack(anchor="w", padx=16, pady=(12, 4))
    self.cart_textbox = ctk.CTkTextbox(self.cart_section, height=80, font=ctk.CTkFont(size=13), state="disabled", wrap="word")
    self.cart_textbox.pack(fill="x", padx=16, pady=(4, 8))
    self.jump_menu = ctk.CTkOptionMenu(self.cart_section, values=["-- 返回特定步驟修改 --"], command=self.jump_to_step, fg_color="#333333")
    self.jump_menu.pack(fill="x", padx=16, pady=(0, 8))
    self.total_cost_label = ctk.CTkLabel(self.cart_section, text="總計估價: NT$ 0", font=ctk.CTkFont(size=22, weight="bold"), text_color="#ffff00")
    self.total_cost_label.pack(pady=(0, 8))
    cart_btns = ctk.CTkFrame(self.cart_section, fg_color="transparent")
    cart_btns.pack(fill="x", padx=16, pady=(0, 14))
    cart_btns.grid_columnconfigure((0, 1), weight=1)
    self.checkout_btn = ctk.CTkButton(cart_btns, text="🛍️ 結帳與生成購買連結", command=self.generate_links, fg_color="#aa00aa", hover_color="#880088", height=36)
    self.checkout_btn.grid(row=0, column=0, sticky="ew", padx=(0, 8))
    ctk.CTkButton(cart_btns, text="🗑️ 清空重來", command=self.clear_cart, fg_color="#880000", height=36).grid(row=0, column=1, sticky="ew", padx=(8, 0))
    self.refresh_cart_ui()


def refresh_cart_ui_v37(self):
    if not hasattr(self, "cart_textbox"):
        return
    self.cart_textbox.configure(state="normal")
    self.cart_textbox.delete("0.0", "end")
    total = 0
    jump_options = ["-- 返回特定步驟修改 --"]
    if not self.cart_items:
        self.cart_textbox.insert("end", "🛒 尚未加入商品。選完零組件後會在這裡整理清單。\n")
        try:
            self.cart_textbox.configure(height=70)
        except Exception:
            pass
    else:
        try:
            self.cart_textbox.configure(height=220)
        except Exception:
            pass
        for k, v in self.cart_items.items():
            total += v.get('price', 0)
            step_name = f"步驟 {k+1}" if isinstance(k, int) else "局部升級"
            short_name = v.get('name', '')[:48] + "..." if len(v.get('name', '')) > 48 else v.get('name', '')
            self.cart_textbox.insert("end", f"[{step_name}] {v.get('target','')}\n ↳ {short_name}\n NT$ {v.get('price',0):,}\n\n")
            if isinstance(k, int):
                jump_options.append(f"返回修改: {step_name}")
    self.cart_textbox.configure(state="disabled")
    self.total_cost_label.configure(text=f"總計估價: NT$ {total:,}")
    self.jump_menu.configure(values=jump_options)
    self.jump_menu.set(jump_options[0])


def _configure_ai_text_tags_v37(widget):
    _configure_ai_text_tags_v36(widget)
    try:
        t = widget._textbox if hasattr(widget, "_textbox") else widget
        t.tag_configure("user", foreground="#5ab0ff")
        t.tag_configure("ai", foreground="#00ff66")
        t.tag_configure("wait", foreground="#dddddd")
        t.tag_configure("error", foreground="#ff6666")
        t.tag_configure("warn", foreground="#ffaa00")
        t.tag_configure("sep", foreground="#777777")
    except Exception:
        pass


def ai_chat_render_v37(self, history=None, pending=None, warning=None, error=None):
    """固定聊天框：新問題顯示在該問答開頭，不跳到整段最底；你/AI 雙色。"""
    widget = getattr(self, "ai_response", None)
    if widget is None:
        return
    if not isinstance(widget, ctk.CTkTextbox):
        try:
            widget.configure(text=str(warning or error or "等待輸入..."), text_color="#cccccc")
        except Exception:
            pass
        return

    history = list(history or getattr(self, "ai_history", []))
    rows = []
    for h in history[-AI_MEMORY_MAX_TURNS:]:
        rows.append((str(h.get("user", "")).strip(), str(h.get("assistant", "")).strip(), "normal"))
    if pending:
        rows.append((str(pending.get("user", "")).strip(), str(pending.get("assistant", AI_PENDING_TEXT_V37)).strip(), "pending"))
    if warning:
        rows.append(("系統", str(warning), "warn"))
    if error:
        rows.append(("系統", str(error), "error"))

    try:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        _configure_ai_text_tags_v37(widget)
        t = widget._textbox if hasattr(widget, "_textbox") else widget
        latest_start = "1.0"
        if not rows:
            t.insert("end", "等待輸入...", "wait")
        else:
            for i, (q, a, kind) in enumerate(rows):
                if i > 0:
                    t.insert("end", "\n\n" + "─" * 30 + "\n\n", "sep")
                latest_start = t.index("end-1c")
                if kind in ("warn", "error") and q == "系統":
                    tag = "warn" if kind == "warn" else "error"
                    t.insert("end", str(a), tag)
                else:
                    t.insert("end", "你：", "user")
                    t.insert("end", q + "\n\n", "user")
                    tag = "wait" if kind == "pending" else "ai"
                    t.insert("end", "AI：", tag)
                    t.insert("end", a, tag)
        widget.configure(state="disabled")
        try:
            t.see(latest_start)
        except Exception:
            widget.see(latest_start)
    except Exception:
        try:
            widget.configure(state="disabled")
        except Exception:
            pass


# 兼容舊名稱，後續呼叫統一走 v37。
ai_chat_render_v36 = ai_chat_render_v37


def show_startup_notice_v37(self):
    dialog = ctk.CTkToplevel(self)
    dialog.title("v37 版本公告")
    dialog.geometry("760x440")
    dialog.minsize(720, 400)
    dialog.resizable(False, False)
    dialog.attributes("-topmost", True)
    try:
        dialog.transient(self)
        dialog.grab_set()
    except Exception:
        pass

    frame = ctk.CTkFrame(dialog, corner_radius=14)
    frame.pack(fill="both", expand=True, padx=20, pady=20)
    ctk.CTkLabel(frame, text="電腦檢測升級工具 v37", font=ctk.CTkFont(size=26, weight="bold"), text_color="#00ffff").pack(anchor="w", padx=26, pady=(22, 12))
    notice = (
        "• AI 顧問移到獨立中欄，操作面板與智慧清單整合到右側工作區。\n"
        "• AI 回覆框修正滾動與截字問題，新問題會從最新問答開頭顯示。\n"
        "• 智慧清單空車時自動縮小，已加入商品時才展開。\n\n"
        "因為近期 AI 市場需求大幅提升，有無貨或未上架價格不正確，還請以購買網站為準。\n\n"
        "研發版本不代表最終品質。"
    )
    ctk.CTkLabel(frame, text=notice, justify="left", wraplength=690, font=ctk.CTkFont(size=17), text_color="#dddddd").pack(anchor="w", padx=26, pady=8)
    ctk.CTkButton(frame, text="確認進入", width=180, height=42, fg_color="#0066cc", command=dialog.destroy).pack(pady=(14, 22))
    try:
        dialog.update_idletasks()
        x = self.winfo_screenwidth() // 2 - 380
        y = self.winfo_screenheight() // 2 - 220
        dialog.geometry(f"760x440+{x}+{y}")
    except Exception:
        pass
    self.wait_window(dialog)


def _call_gemini_ai_v37(prompt):
    """加大輸出 token，解析多候選，降低回覆到一半消失的機率。"""
    api_key = get_gemini_api_key_v34()
    if not api_key:
        raise RuntimeError(missing_gemini_key_message_v34())
    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
    env_model = os.getenv("GEMINI_MODEL", "").strip().replace("models/", "")
    candidates = []
    if env_model:
        candidates.extend([("v1beta", env_model), ("v1", env_model)])
    try:
        candidates.extend(_discover_gemini_models_v34(headers))
    except Exception:
        pass
    if not candidates:
        candidates = [("v1beta", "gemini-2.5-flash"), ("v1beta", "gemini-2.0-flash"), ("v1beta", "gemini-1.5-flash")]
    seen = set(); dedup = []
    for c in candidates:
        if c not in seen:
            seen.add(c); dedup.append(c)
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.32, "topP": 0.9, "maxOutputTokens": 8192},
    }
    errors = []
    for api_version, model in dedup[:10]:
        url = f"https://generativelanguage.googleapis.com/{api_version}/models/{model}:generateContent"
        for attempt in range(2):
            try:
                r = requests.post(url, headers=headers, json=payload, timeout=(8, 90))
                if r.status_code in (404, 410):
                    errors.append(f"{model}:404")
                    break
                if r.status_code in (401, 403):
                    raise RuntimeError("Gemini API Key 無效或權限不足")
                if r.status_code == 429:
                    time.sleep(1.5 + attempt * 2.5)
                    errors.append(f"{model}:429")
                    continue
                if r.status_code in (500, 502, 503, 504):
                    time.sleep(1.0)
                    errors.append(f"{model}:{r.status_code}")
                    continue
                r.raise_for_status()
                data = r.json()
                answers = []
                for cand in data.get("candidates", []) or []:
                    parts = cand.get("content", {}).get("parts", []) or []
                    txt = "".join(p.get("text", "") for p in parts).strip()
                    if txt:
                        finish = cand.get("finishReason", "")
                        if finish == "MAX_TOKENS":
                            txt += "\n\n（回覆已接近模型輸出上限，建議縮小問題或分段追問。）"
                        answers.append(txt)
                if answers:
                    return answers[0]
                errors.append(f"{model}:空白")
                break
            except RuntimeError:
                raise
            except Exception as e:
                errors.append(f"{model}:{str(e)[:60]}")
                break
    detail = " | ".join(errors[:8])
    if "429" in detail:
        raise RuntimeError("Gemini 目前請求過密或配額暫時受限，請稍等冷卻後再問。")
    raise RuntimeError("Gemini 外部 AI 無回覆：" + detail)


def external_ai_recommendation_v37(user_text, specs, history=None):
    prompt = build_ai_prompt(user_text, specs, history=history)
    result = _call_gemini_ai_v37(prompt)
    return "🧠 AI 建議:" + chr(10) + result.strip()


external_ai_recommendation = external_ai_recommendation_v37


def v37_run_ai_advisor(self):
    user_text = self.ai_input.get().strip()
    if not user_text:
        ai_chat_render_v37(self, warning="請先輸入需求，例如：納克園最低配備是什麼、可以跑異環 NTE 嗎、10萬含螢幕怎麼配。")
        return

    user_text = normalize_user_query(user_text)
    ok, msg = self.v35_1_ai_guard(user_text)
    if not ok:
        ai_chat_render_v37(self, warning=msg)
        return

    if hasattr(self, "ai_button"):
        self.ai_button.configure(state="disabled")

    pending = {"time": int(time.time()), "user": user_text, "assistant": AI_PENDING_TEXT_V37}
    ai_chat_render_v37(self, history=getattr(self, "ai_history", []), pending=pending)

    def task():
        try:
            result = external_ai_recommendation_v37(user_text, self.specs, history=self.ai_history)
            clean_answer = result.replace("🧠 AI 建議:\n", "", 1).strip()
            self.ai_history.append({"time": int(time.time()), "user": user_text, "assistant": clean_answer})
            self.ai_history = self.ai_history[-AI_MEMORY_MAX_TURNS:]
            self.ui_safe(lambda: ai_chat_render_v37(self, history=self.ai_history))
        except Exception as e:
            raw = re.sub(r"AIza[0-9A-Za-z_\-]+", "AIza***", str(e))
            if "429" in raw or "quota" in raw.lower() or "rate" in raw.lower():
                msg = "外部 AI 目前請求過密或配額暫時受限，請稍等 1～3 分鐘再試。"
            elif "401" in raw or "403" in raw or "權限" in raw or "Key" in raw:
                msg = "外部 AI 金鑰或權限異常，請確認公用 Key 是否仍可用。"
            else:
                msg = "外部 AI 暫時連線失敗，請稍後再試。"
            self.ui_safe(lambda msg=msg: ai_chat_render_v37(self, history=getattr(self, "ai_history", []), error="⚠️ " + msg))
        finally:
            def unlock():
                if hasattr(self, "ai_button") and time.time() >= getattr(self, "ai_cooldown_until", 0) and not getattr(self, "ai_locked_until_close", False):
                    self.ai_button.configure(state="normal")
            self.ui_safe(unlock)

    threading.Thread(target=task, daemon=True).start()


def v37_init(self):
    try:
        self.withdraw()
    except Exception:
        pass

    # 不呼叫舊版 init，避免先建立 v36 版三欄再拆；直接建 v37 版面。
    super(ROGApp, self).__init__()
    self.specs = get_specs()
    self.scores = calculate_score(self.specs)
    self.is_laptop = self.specs['is_laptop']
    self.cart_items = {}
    self.build_step = 0
    self.build_max_steps = 0
    self.build_context = {}
    self.current_mode = ""
    self.ai_history = []
    self.ai_request_times = []
    self.ai_recent_prompts = []
    self.ai_cooldown_until = 0
    self.ai_locked_until_close = False
    self.irrelevant_count = 0
    self.ui_scale_percent = 100

    device_type = "筆記型電腦" if self.is_laptop else "桌上型電腦"
    self.title(f"電腦檢測升級工具 {V37_VERSION} - [{device_type}]")
    self.geometry("1920x1040")
    self.minsize(1450, 850)
    self.resizable(True, True)

    self.topbar = ctk.CTkFrame(self, fg_color="#202020", height=38, corner_radius=0)
    self.topbar.pack(fill="x", side="top")
    ctk.CTkLabel(self.topbar, text=f"電腦硬體 AI 顧問 {V37_VERSION}", text_color="#00ffff", font=ctk.CTkFont(size=15, weight="bold")).pack(side="left", padx=14)
    ctk.CTkLabel(self.topbar, text="字體/介面比例", text_color="#cccccc").pack(side="right", padx=(8, 4))
    self.scale_menu = ctk.CTkOptionMenu(
        self.topbar,
        values=["25%", "50%", "75%", "100%", "125%", "150%", "175%", "200%", "250%", "300%", "400%", "500%"],
        command=self.set_ui_scale,
        width=95,
    )
    self.scale_menu.set("100%")
    self.scale_menu.pack(side="right", padx=10, pady=5)

    self.main_pane = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashwidth=8, bd=0, bg="#1f1f1f", relief="flat")
    self.main_pane.pack(fill="both", expand=True, padx=8, pady=8)

    self.left_pane_holder = ctk.CTkFrame(self.main_pane, fg_color="transparent", corner_radius=0)
    self.ai_pane_holder = ctk.CTkFrame(self.main_pane, fg_color="transparent", corner_radius=0)
    self.work_pane_holder = ctk.CTkFrame(self.main_pane, fg_color="transparent", corner_radius=0)
    self.main_pane.add(self.left_pane_holder, minsize=380, width=520, stretch="first")
    self.main_pane.add(self.ai_pane_holder, minsize=420, width=560, stretch="always")
    self.main_pane.add(self.work_pane_holder, minsize=560, width=840, stretch="last")

    self.left_frame = ctk.CTkScrollableFrame(self.left_pane_holder, width=510, corner_radius=10)
    self.ai_frame = ctk.CTkFrame(self.ai_pane_holder, corner_radius=10)
    self.mid_frame = ctk.CTkScrollableFrame(self.work_pane_holder, width=830, corner_radius=10)
    self.left_frame.pack(fill="both", expand=True)
    self.ai_frame.pack(fill="both", expand=True)
    self.mid_frame.pack(fill="both", expand=True)

    self.setup_left_panel()
    self.setup_ai_panel_v37()

    # 模式按鈕放到右側工作區最上方。
    self.mode_frame = ctk.CTkFrame(self.mid_frame, fg_color="transparent")
    self.mode_frame.pack(fill="x", padx=18, pady=(14, 6))
    self.mode_frame.grid_columnconfigure((0, 1), weight=1)
    ctk.CTkButton(self.mode_frame, text="🔧 局部升級現有", command=self.mode_upgrade, height=38).grid(row=0, column=0, sticky="ew", padx=(0, 8))
    ctk.CTkButton(self.mode_frame, text="🛒 新裝機/買新機", command=self.mode_build_select, height=38, fg_color="#cc5500").grid(row=0, column=1, sticky="ew", padx=(8, 0))

    _v37_original_setup_mid_panel(self)
    setup_right_panel_v37(self)

    self.bind_all("<MouseWheel>", self._on_mousewheel, add="+")
    self.bind_all("<Button-4>", self._on_mousewheel, add="+")
    self.bind_all("<Button-5>", self._on_mousewheel, add="+")

    try:
        show_startup_notice_v37(self)
    except Exception:
        pass
    try:
        self.deiconify()
        self.after(140, lambda: self.state("zoomed"))
    except Exception:
        pass



# ============================================================
# v38：AI 區排版、購物車視窗化、版本公告與主按鈕位置重整
# ============================================================
V38_VERSION = "v38"
AI_PENDING_TEXT_V38 = "⏳ 分析中..."


def setup_ai_panel_v38(self):
    """中間 AI 對話欄：只保留一顆送出按鈕，模式按鈕移到此區。"""
    self.ai_frame.grid_columnconfigure(0, weight=1)
    self.ai_frame.grid_rowconfigure(7, weight=1)

    ctk.CTkLabel(
        self.ai_frame,
        text="[ 結構化 AI 顧問 ]",
        font=ctk.CTkFont(size=18, weight="bold"),
        text_color="#ff55ff",
    ).grid(row=0, column=0, sticky="w", padx=18, pady=(16, 8))

    self.ai_input = ctk.CTkEntry(
        self.ai_frame,
        placeholder_text="輸入需求：例 10萬含螢幕、納克園最低配備、可以跑異環 NTE 嗎",
        height=38,
        font=ctk.CTkFont(size=14),
    )
    self.ai_input.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 8))

    self.ai_button = ctk.CTkButton(
        self.ai_frame,
        text="🧠 AI 分析與決策",
        command=self.run_ai_advisor,
        fg_color="#660066",
        height=40,
        font=ctk.CTkFont(size=14, weight="bold"),
    )
    self.ai_button.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 8))

    ctk.CTkLabel(
        self.ai_frame,
        text="AI 分析需花費數秒，請耐心等待。",
        text_color="#cccccc",
        font=ctk.CTkFont(size=13),
    ).grid(row=3, column=0, sticky="w", padx=20, pady=(0, 8))

    self.mode_frame = ctk.CTkFrame(self.ai_frame, fg_color="transparent")
    self.mode_frame.grid(row=4, column=0, sticky="ew", padx=18, pady=(0, 8))
    self.mode_frame.grid_columnconfigure((0, 1), weight=1)
    ctk.CTkButton(
        self.mode_frame,
        text="🔧 局部升級現有",
        command=self.mode_upgrade,
        height=38,
        font=ctk.CTkFont(size=13, weight="bold"),
    ).grid(row=0, column=0, sticky="ew", padx=(0, 8))
    ctk.CTkButton(
        self.mode_frame,
        text="🛒 新裝機/買新機",
        command=self.mode_build_select,
        height=38,
        fg_color="#cc5500",
        font=ctk.CTkFont(size=13, weight="bold"),
    ).grid(row=0, column=1, sticky="ew", padx=(8, 0))

    ctk.CTkLabel(
        self.ai_frame,
        text="本次開啟期間會記住上下文；關閉視窗後重置。",
        text_color="#aaaaaa",
        font=ctk.CTkFont(size=12),
    ).grid(row=5, column=0, sticky="w", padx=20, pady=(0, 6))

    self.ai_response = ctk.CTkTextbox(
        self.ai_frame,
        corner_radius=10,
        wrap="word",
        font=ctk.CTkFont(size=15),
        fg_color="#1f1f1f",
        border_width=1,
        border_color="#444444",
        activate_scrollbars=True,
        spacing1=4,
        spacing2=2,
        spacing3=7,
    )
    self.ai_response.grid(row=7, column=0, sticky="nsew", padx=14, pady=(4, 14))
    _configure_ai_text_tags_v38(self.ai_response)
    try:
        inner = self.ai_response._textbox if hasattr(self.ai_response, "_textbox") else self.ai_response
        inner.bind("<MouseWheel>", _textbox_wheel_break_v36, add="+")
        inner.bind("<Button-4>", _textbox_wheel_break_v36, add="+")
        inner.bind("<Button-5>", _textbox_wheel_break_v36, add="+")
        self.ai_response.bind("<MouseWheel>", _textbox_wheel_break_v36, add="+")
        self.ai_response.bind("<Button-4>", _textbox_wheel_break_v36, add="+")
        self.ai_response.bind("<Button-5>", _textbox_wheel_break_v36, add="+")
    except Exception:
        pass
    ai_chat_render_v38(self, history=[])

    try:
        self.ai_input.bind("<Return>", lambda event: self.run_ai_advisor())
    except Exception:
        pass


def setup_cart_button_v38(self):
    """右側操作面板底部只放查看購物車，不直接展開智慧清單。"""
    self.cart_bar = ctk.CTkFrame(self.mid_frame, corner_radius=10)
    self.cart_bar.pack(fill="x", padx=20, pady=(16, 18))
    self.cart_summary_label = ctk.CTkLabel(
        self.cart_bar,
        text="智慧清單：目前 0 件，總計 NT$ 0",
        text_color="#00ff00",
        font=ctk.CTkFont(size=15, weight="bold"),
    )
    self.cart_summary_label.pack(anchor="w", padx=16, pady=(12, 6))
    self.checkout_btn = ctk.CTkButton(
        self.cart_bar,
        text="🛒 查看購物車",
        command=self.generate_links,
        fg_color="#aa00aa",
        hover_color="#880088",
        height=40,
        font=ctk.CTkFont(size=14, weight="bold"),
    )
    self.checkout_btn.pack(fill="x", padx=16, pady=(0, 14))
    self.refresh_cart_ui()


def _cart_totals_v38(self):
    total = 0
    count = 0
    for v in getattr(self, "cart_items", {}).values():
        count += 1
        try:
            total += int(v.get("price", 0) or 0)
        except Exception:
            pass
    return count, total


def refresh_cart_ui_v38(self):
    count, total = _cart_totals_v38(self)
    if hasattr(self, "cart_summary_label"):
        self.cart_summary_label.configure(text=f"智慧清單：目前 {count} 件，總計 NT$ {total:,}")
    if hasattr(self, "checkout_btn"):
        self.checkout_btn.configure(text=f"🛒 查看購物車（{count} 件 / NT$ {total:,}）")
    # 若購物車視窗已開啟，順手刷新。
    if getattr(self, "cart_window", None) is not None:
        try:
            if self.cart_window.winfo_exists():
                _render_cart_window_v38(self)
        except Exception:
            pass


def _cart_item_key_text_v38(k):
    if isinstance(k, int):
        return f"步驟 {k+1}"
    return "局部升級"


def _cart_display_options_v38(self):
    opts = []
    key_map = {}
    for k, v in getattr(self, "cart_items", {}).items():
        step = _cart_item_key_text_v38(k)
        target = str(v.get("target", ""))
        label = f"{step}｜{target}"
        opts.append(label)
        key_map[label] = k
    return opts, key_map


def _build_cart_text_v38(self):
    if not getattr(self, "cart_items", {}):
        return "智慧清單目前是空的。\n\n請先回到操作面板查詢時價，確認商品後按「確定加入清單」。"

    lines = ["【智慧清單 CART】"]
    total = 0
    for k, v in self.cart_items.items():
        price = int(v.get("price", 0) or 0)
        total += price
        step = _cart_item_key_text_v38(k)
        lines.append(f"\n[{step}] {v.get('target', '')}")
        lines.append(f"商品：{v.get('name', '')}")
        lines.append(f"價格：NT$ {price:,}")
        link = v.get("link") or ""
        if link:
            lines.append(f"連結：{link}")
    lines.append("\n----------------------------------------")
    lines.append(f"總計估價：NT$ {total:,}")
    lines.append("\n提醒：價格與庫存請以實際購買網站為準。")
    return "\n".join(lines)


def _render_cart_window_v38(self):
    text = getattr(self, "cart_popup_text", None)
    if text is not None:
        text.configure(state="normal")
        text.delete("0.0", "end")
        text.insert("end", _build_cart_text_v38(self))
        text.configure(state="disabled")
    count, total = _cart_totals_v38(self)
    if hasattr(self, "cart_popup_total"):
        self.cart_popup_total.configure(text=f"總計估價：NT$ {total:,}")
    opts, key_map = _cart_display_options_v38(self)
    self.cart_popup_key_map = key_map
    if hasattr(self, "cart_popup_select"):
        values = opts or ["-- 目前沒有商品 --"]
        self.cart_popup_select.configure(values=values)
        self.cart_popup_select.set(values[0])


def cart_add_current_v38(self):
    if not getattr(self, "current_fetch", None):
        if hasattr(self, "price_label"):
            self.price_label.configure(text="目前沒有可加入的查價結果。", text_color="#ffaa00")
        return
    if self.current_fetch.get("price", 0) <= 0:
        if hasattr(self, "price_label"):
            self.price_label.configure(text="此商品目前缺貨 / 未取得有效價格，不能加入清單。", text_color="#ffaa00")
        return
    self.cart_items[self.current_fetch["step"]] = self.current_fetch
    self.refresh_cart_ui()
    if hasattr(self, "add_cart_btn"):
        self.add_cart_btn.configure(state="disabled")
    if hasattr(self, "price_label"):
        self.price_label.configure(text="✅ 已成功加入清單！可按「查看購物車」確認。", text_color="#00ff00")


def cart_remove_selected_v38(self):
    label = getattr(self, "cart_popup_select", None).get() if hasattr(self, "cart_popup_select") else ""
    key = getattr(self, "cart_popup_key_map", {}).get(label)
    if key in getattr(self, "cart_items", {}):
        del self.cart_items[key]
        self.refresh_cart_ui()


def clear_cart_v38(self):
    self.cart_items.clear()
    self.refresh_cart_ui()


def copy_cart_links_v38(self):
    data = _build_cart_text_v38(self)
    try:
        self.clipboard_clear()
        self.clipboard_append(data)
        if hasattr(self, "cart_popup_status"):
            self.cart_popup_status.configure(text="已複製購物車內容。", text_color="#00ff00")
    except Exception as e:
        if hasattr(self, "cart_popup_status"):
            self.cart_popup_status.configure(text=f"複製失敗：{e}", text_color="#ff6666")


def open_selected_cart_link_v38(self):
    label = getattr(self, "cart_popup_select", None).get() if hasattr(self, "cart_popup_select") else ""
    key = getattr(self, "cart_popup_key_map", {}).get(label)
    item = getattr(self, "cart_items", {}).get(key)
    if item and item.get("link"):
        webbrowser.open(item.get("link"))
    elif hasattr(self, "cart_popup_status"):
        self.cart_popup_status.configure(text="此項目沒有可開啟連結。", text_color="#ffaa00")


def open_cart_window_v38(self):
    if getattr(self, "cart_window", None) is not None:
        try:
            if self.cart_window.winfo_exists():
                self.cart_window.focus()
                _render_cart_window_v38(self)
                return
        except Exception:
            pass

    win = ctk.CTkToplevel(self)
    self.cart_window = win
    win.title("智慧清單 / 購物車")
    win.geometry("980x720")
    win.minsize(760, 560)
    try:
        win.attributes("-topmost", True)
        win.after(250, lambda: win.attributes("-topmost", False))
    except Exception:
        pass

    win.grid_columnconfigure(0, weight=1)
    win.grid_rowconfigure(2, weight=1)

    ctk.CTkLabel(win, text="[ 智慧清單 CART ]", font=ctk.CTkFont(size=22, weight="bold"), text_color="#00ff00").grid(row=0, column=0, sticky="w", padx=22, pady=(18, 8))

    top = ctk.CTkFrame(win, fg_color="transparent")
    top.grid(row=1, column=0, sticky="ew", padx=22, pady=(0, 8))
    top.grid_columnconfigure(0, weight=1)
    self.cart_popup_select = ctk.CTkOptionMenu(top, values=["-- 目前沒有商品 --"], width=420)
    self.cart_popup_select.grid(row=0, column=0, sticky="ew", padx=(0, 10))
    ctk.CTkButton(top, text="開啟商品/搜尋", command=lambda: open_selected_cart_link_v38(self), height=34).grid(row=0, column=1, padx=4)
    ctk.CTkButton(top, text="刪除此項", command=lambda: cart_remove_selected_v38(self), fg_color="#880000", height=34).grid(row=0, column=2, padx=4)
    ctk.CTkButton(top, text="加入目前查價結果", command=lambda: cart_add_current_v38(self), fg_color="#008800", height=34).grid(row=0, column=3, padx=(4, 0))

    self.cart_popup_text = ctk.CTkTextbox(win, wrap="word", font=ctk.CTkFont(size=14), corner_radius=10)
    self.cart_popup_text.grid(row=2, column=0, sticky="nsew", padx=22, pady=8)

    bottom = ctk.CTkFrame(win, fg_color="transparent")
    bottom.grid(row=3, column=0, sticky="ew", padx=22, pady=(8, 18))
    bottom.grid_columnconfigure((0, 1, 2), weight=1)
    self.cart_popup_total = ctk.CTkLabel(bottom, text="總計估價：NT$ 0", font=ctk.CTkFont(size=20, weight="bold"), text_color="#ffff00")
    self.cart_popup_total.grid(row=0, column=0, sticky="w", padx=(0, 8), pady=(0, 8))
    ctk.CTkButton(bottom, text="複製清單/連結", command=lambda: copy_cart_links_v38(self), fg_color="#0066cc", height=36).grid(row=1, column=0, sticky="ew", padx=(0, 8))
    ctk.CTkButton(bottom, text="清空購物車", command=lambda: clear_cart_v38(self), fg_color="#880000", height=36).grid(row=1, column=1, sticky="ew", padx=8)
    ctk.CTkButton(bottom, text="關閉", command=win.destroy, fg_color="#555555", height=36).grid(row=1, column=2, sticky="ew", padx=(8, 0))
    self.cart_popup_status = ctk.CTkLabel(bottom, text="", text_color="#aaaaaa")
    self.cart_popup_status.grid(row=2, column=0, columnspan=3, sticky="w", pady=(8, 0))

    _render_cart_window_v38(self)


def _configure_ai_text_tags_v38(widget):
    _configure_ai_text_tags_v37(widget)
    try:
        t = widget._textbox if hasattr(widget, "_textbox") else widget
        t.tag_configure("user", foreground="#53a7ff", spacing1=4, spacing3=4)
        t.tag_configure("ai", foreground="#00ff66", spacing1=4, spacing3=8)
        t.tag_configure("wait", foreground="#dddddd")
        t.tag_configure("error", foreground="#ff6666")
        t.tag_configure("warn", foreground="#ffaa00")
        t.tag_configure("sep", foreground="#777777")
    except Exception:
        pass


def ai_chat_render_v38(self, history=None, pending=None, warning=None, error=None):
    widget = getattr(self, "ai_response", None)
    if widget is None:
        return
    history = history if history is not None else getattr(self, "ai_history", [])
    try:
        _configure_ai_text_tags_v38(widget)
        widget.configure(state="normal")
        widget.delete("0.0", "end")
        rows = []
        for item in history[-AI_MEMORY_MAX_TURNS:]:
            rows.append((str(item.get("user", "")).strip(), str(item.get("assistant", "")).strip(), "normal"))
        if pending:
            rows.append((str(pending.get("user", "")).strip(), str(pending.get("assistant", AI_PENDING_TEXT_V38)).strip(), "pending"))
        if warning:
            widget.insert("end", str(warning).strip() + "\n", "warn")
        elif error:
            widget.insert("end", str(error).strip() + "\n", "error")
        elif not rows:
            widget.insert("end", "", "ai")
        for idx, (u, a, kind) in enumerate(rows):
            if idx:
                widget.insert("end", "\n────────────────────────\n\n", "sep")
            widget.insert("end", f"你：{u}\n", "user")
            widget.insert("end", f"AI：{a}\n", "wait" if kind == "pending" else "ai")
        widget.configure(state="disabled")
        try:
            # 新回覆顯示在該問答開頭；不要直接跳到長回答最後。
            if rows:
                widget.see("end-2l")
                widget.yview_moveto(max(0.0, widget.yview()[1] - 0.35))
        except Exception:
            pass
    except Exception:
        pass


def show_startup_notice_v38(self):
    dialog = ctk.CTkToplevel(self)
    dialog.title("v38 版本公告")
    dialog.transient(self)
    dialog.grab_set()
    dialog.resizable(False, False)
    frame = ctk.CTkFrame(dialog, corner_radius=18)
    frame.pack(fill="both", expand=True, padx=22, pady=22)
    ctk.CTkLabel(frame, text="電腦檢測升級工具 v38", font=ctk.CTkFont(size=26, weight="bold"), text_color="#00ffff").pack(anchor="w", padx=26, pady=(22, 12))
    notice = (
        "AI 顧問移至中欄，操作面板與購物車流程重新整理。\n"
        "購物車改為獨立視窗，可查看、複製、刪除與開啟商品連結。\n"
        "修復文字卡住與 32G 記憶體仍建議升 32G 的問題。\n\n"
        "因為近期 AI 市場需求大幅提升，有無貨或未上架價格不正確，還請以購買網站為準。\n\n"
        "研發版本不代表最終品質。"
    )
    ctk.CTkLabel(frame, text=notice, justify="left", wraplength=720, font=ctk.CTkFont(size=17), text_color="#dddddd").pack(anchor="w", padx=26, pady=8)
    ctk.CTkButton(frame, text="確認進入", width=190, height=44, fg_color="#0066cc", command=dialog.destroy).pack(pady=(14, 22))
    try:
        dialog.update_idletasks()
        x = self.winfo_screenwidth() // 2 - 410
        y = self.winfo_screenheight() // 2 - 235
        dialog.geometry(f"820x470+{x}+{y}")
    except Exception:
        pass
    self.wait_window(dialog)


def v38_run_ai_advisor(self):
    user_text = self.ai_input.get().strip()
    if not user_text:
        ai_chat_render_v38(self, warning="請先輸入需求，例如：納克園最低配備是什麼、可以跑異環 NTE 嗎、10萬含螢幕怎麼配。")
        return

    user_text = normalize_user_query(user_text)
    ok, msg = self.v35_1_ai_guard(user_text)
    if not ok:
        ai_chat_render_v38(self, warning=msg)
        return

    if hasattr(self, "ai_button"):
        self.ai_button.configure(state="disabled")

    pending = {"time": int(time.time()), "user": user_text, "assistant": AI_PENDING_TEXT_V38}
    ai_chat_render_v38(self, history=getattr(self, "ai_history", []), pending=pending)

    def task():
        try:
            result = external_ai_recommendation_v37(user_text, self.specs, history=self.ai_history)
            clean_answer = result.replace("🧠 AI 建議:\n", "", 1).replace("🧠 AI 建議:", "", 1).strip()
            self.ai_history.append({"time": int(time.time()), "user": user_text, "assistant": clean_answer})
            self.ai_history = self.ai_history[-AI_MEMORY_MAX_TURNS:]
            self.ui_safe(lambda: ai_chat_render_v38(self, history=self.ai_history))
        except Exception as e:
            raw = re.sub(r"AIza[0-9A-Za-z_\-]+", "AIza***", str(e))
            if "429" in raw or "quota" in raw.lower() or "rate" in raw.lower():
                msg = "外部 AI 目前請求過密或配額暫時受限，請稍等 1～3 分鐘再試。"
            elif "401" in raw or "403" in raw or "權限" in raw or "Key" in raw:
                msg = "外部 AI 金鑰或權限異常，請確認公用 Key 是否仍可用。"
            else:
                msg = "外部 AI 暫時連線失敗，請稍後再試。"
            self.ui_safe(lambda msg=msg: ai_chat_render_v38(self, history=getattr(self, "ai_history", []), error="⚠️ " + msg))
        finally:
            def unlock():
                if hasattr(self, "ai_button") and time.time() >= getattr(self, "ai_cooldown_until", 0) and not getattr(self, "ai_locked_until_close", False):
                    self.ai_button.configure(state="normal")
            self.ui_safe(unlock)

    threading.Thread(target=task, daemon=True).start()


def v38_init(self):
    try:
        self.withdraw()
    except Exception:
        pass

    super(ROGApp, self).__init__()
    self.specs = get_specs()
    self.scores = calculate_score(self.specs)
    self.is_laptop = self.specs['is_laptop']
    self.cart_items = {}
    self.build_step = 0
    self.build_max_steps = 0
    self.build_context = {}
    self.current_mode = ""
    self.ai_history = []
    self.ai_request_times = []
    self.ai_recent_prompts = []
    self.ai_cooldown_until = 0
    self.ai_locked_until_close = False
    self.irrelevant_count = 0
    self.ui_scale_percent = 100
    self.cart_window = None

    device_type = "筆記型電腦" if self.is_laptop else "桌上型電腦"
    self.title(f"電腦檢測升級工具 {V38_VERSION} - [{device_type}]")
    self.geometry("1920x1040")
    self.minsize(1450, 850)
    self.resizable(True, True)

    self.topbar = ctk.CTkFrame(self, fg_color="#202020", height=38, corner_radius=0)
    self.topbar.pack(fill="x", side="top")
    ctk.CTkLabel(self.topbar, text=f"電腦硬體 AI 顧問 {V38_VERSION}", text_color="#00ffff", font=ctk.CTkFont(size=15, weight="bold")).pack(side="left", padx=14)
    ctk.CTkLabel(self.topbar, text="字體/介面比例", text_color="#cccccc").pack(side="right", padx=(8, 4))
    self.scale_menu = ctk.CTkOptionMenu(
        self.topbar,
        values=["25%", "50%", "75%", "100%", "125%", "150%", "175%", "200%", "250%", "300%", "400%", "500%"],
        command=self.set_ui_scale,
        width=95,
    )
    self.scale_menu.set("100%")
    self.scale_menu.pack(side="right", padx=10, pady=5)

    self.main_pane = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashwidth=8, bd=0, bg="#1f1f1f", relief="flat")
    self.main_pane.pack(fill="both", expand=True, padx=8, pady=8)

    self.left_pane_holder = ctk.CTkFrame(self.main_pane, fg_color="transparent", corner_radius=0)
    self.ai_pane_holder = ctk.CTkFrame(self.main_pane, fg_color="transparent", corner_radius=0)
    self.work_pane_holder = ctk.CTkFrame(self.main_pane, fg_color="transparent", corner_radius=0)
    self.main_pane.add(self.left_pane_holder, minsize=380, width=520, stretch="first")
    self.main_pane.add(self.ai_pane_holder, minsize=420, width=560, stretch="always")
    self.main_pane.add(self.work_pane_holder, minsize=560, width=840, stretch="last")

    self.left_frame = ctk.CTkScrollableFrame(self.left_pane_holder, width=510, corner_radius=10)
    self.ai_frame = ctk.CTkFrame(self.ai_pane_holder, corner_radius=10)
    self.mid_frame = ctk.CTkScrollableFrame(self.work_pane_holder, width=830, corner_radius=10)
    self.left_frame.pack(fill="both", expand=True)
    self.ai_frame.pack(fill="both", expand=True)
    self.mid_frame.pack(fill="both", expand=True)

    self.setup_left_panel()
    self.setup_ai_panel_v38()
    _v37_original_setup_mid_panel(self)
    setup_cart_button_v38(self)

    self.bind_all("<MouseWheel>", self._on_mousewheel, add="+")
    self.bind_all("<Button-4>", self._on_mousewheel, add="+")
    self.bind_all("<Button-5>", self._on_mousewheel, add="+")

    try:
        show_startup_notice_v38(self)
    except Exception:
        pass
    try:
        self.deiconify()
        self.after(140, lambda: self.state("zoomed"))
    except Exception:
        pass


# 套用 v38 覆蓋。
ROGApp.__init__ = v38_init
ROGApp.setup_left_panel = setup_left_panel_v37
ROGApp.setup_ai_panel_v38 = setup_ai_panel_v38
ROGApp.setup_right_panel = lambda self: setup_cart_button_v38(self)
ROGApp.refresh_cart_ui = refresh_cart_ui_v38
ROGApp.clear_cart = clear_cart_v38
ROGApp.generate_links = open_cart_window_v38
ROGApp.run_ai_advisor = v38_run_ai_advisor
ROGApp._on_mousewheel = v36_on_mousewheel




# ============================================================
# v41：基於 v38 穩定版補強硬體分析（雷達圖 / 最值得升級 / 老舊設備換新建議）
# ============================================================
V41_VERSION = "v41.4"


def _v41_has_dedicated_gpu(gpu_name: str) -> bool:
    name = (gpu_name or "").lower()
    bad_tokens = [
        "integrated", "radeon graphics", "vega", "uhd", "iris", "intel graphics",
        "mx", "quadro p", "embedded"
    ]
    if any(t in name for t in bad_tokens):
        return False
    good_tokens = ["rtx", "gtx", "rx ", "arc ", "radeon rx", "geforce"]
    return any(t in name for t in good_tokens)


def _v41_is_old_hardware(specs, scores):
    cpu = (specs.get('cpu_name', '') or '').lower()
    gpu = (specs.get('gpu_name', '') or '').lower()
    overall_grade = (scores.get('OverallGrade', 'F') or 'F').upper()

    old_cpu_patterns = [
        r'i[3579]-[67]\d{3}', r'i[3579]-8\d{3}',
        r'ryzen [3579] [12]\d{3}', r'ryzen [3579] 3\d{3}',
        r'fx-\d+', r'athlon', r'pentium', r'celeron'
    ]
    old_gpu_tokens = [
        'gtx 9', 'gtx 10', 'gtx 16', 'rtx 20', 'rx 4', 'rx 5', 'rx 5', 'rx 6',
        'mx', 'integrated', 'radeon graphics', 'vega', 'uhd', 'iris'
    ]
    old_cpu = any(re.search(p, cpu) for p in old_cpu_patterns)
    old_gpu = any(t in gpu for t in old_gpu_tokens)
    no_dgpu = not _v41_has_dedicated_gpu(specs.get('gpu_name', ''))
    low_grade = overall_grade in ['C', 'D', 'E', 'F']
    return old_cpu or old_gpu or no_dgpu or low_grade


def _v41_replace_reasons(specs, scores):
    reasons = []
    cpu = specs.get('cpu_name', '')
    gpu = specs.get('gpu_name', '')
    overall = scores.get('OverallGrade', 'F')
    game = scores.get('GameGrade', 'F')

    if not _v41_has_dedicated_gpu(gpu):
        reasons.append('目前沒有可用的獨立顯卡，遊戲與 AI 空間有限。')
    if re.search(r'rtx 20|gtx 16|gtx 10', (gpu or '').lower()):
        reasons.append('顯示卡世代偏舊，升級單一零件的效益通常不如直接換新。')
    if re.search(r'i[3579]-[67]\d{3}|ryzen [3579] [123]\d{3}|fx-|athlon|pentium|celeron', (cpu or '').lower()):
        reasons.append('處理器平台年紀偏大，後續升級常會卡在主機板 / 記憶體相容性。')
    if overall in ['C', 'D', 'E', 'F'] or game in ['D', 'E', 'F']:
        reasons.append('整體評價已落在入門或偏低區間，繼續補零件的投報率不高。')
    if not reasons:
        reasons.append('如果目標是明顯提升 3A / AI 體驗，通常整機更新會比零件補強更有效。')
    return reasons[:3]


def _v41_best_upgrade(specs, scores):
    if _v41_is_old_hardware(specs, scores):
        return '目前最值得做的不是單點升級，而是直接規劃換新 / 換平台。'

    ram_nom = nominal_capacity_gb(specs.get('ram_total', 0))
    disk_total = float(specs.get('disk_total', 0) or 0)
    game_grade = scores.get('GameGrade', 'F')
    prod_grade = scores.get('ProductivityGrade', 'F')
    gpu_name = (specs.get('gpu_name', '') or '').lower()

    if ram_nom < 32 and (prod_grade in ['A', 'B++', 'B+', 'B', 'C'] or 'ai' in gpu_name):
        return '最值得升級：RAM。先補到 32G，對多工、剪輯與 AI 體感最直接。'
    if disk_total and disk_total < 1000:
        return '最值得升級：SSD。建議補 1TB / 2TB NVMe，容量與遊戲安裝空間會舒服很多。'
    if (not specs.get('is_laptop')) and game_grade in ['B', 'B+', 'B++', 'C'] and _v41_has_dedicated_gpu(specs.get('gpu_name', '')):
        return '最值得升級：顯示卡。若目標是明顯提升遊戲張數，桌機先升 GPU 最有效。'
    fan_rows = specs.get('cooling_fans', [])
    if fan_rows:
        return '最值得優化：散熱 / 清灰。若長時間高負載，先把溫度與噪音控制好也很值得。'
    return '最值得升級：SSD 或散熱維護。現況夠用時，優先補容量與穩定度。'


def _v41_extra_hardware_notes(specs, scores):
    lines = []
    if _v41_is_old_hardware(specs, scores):
        lines.append('補充建議：')
        lines.append('• 建議換新原因：' + '；'.join(_v41_replace_reasons(specs, scores)))
        lines.append('• 建議方向：若預算有限，可先看主流中階平台；若要 2K / 4K、3A 或 AI，建議直接規劃新機。')
        if specs.get('is_laptop'):
            lines.append('• 筆電補充：多數筆電僅能升級 RAM / SSD，CPU / GPU 通常不可更換。')
        else:
            lines.append('• 桌機補充：若平台太舊，升級顯卡也可能受限於電供、主機板與處理器。')
        return '\n'.join(lines)

    lines.append('目前最值得升級的一項：')
    lines.append('• ' + _v41_best_upgrade(specs, scores))
    if not specs.get('is_laptop'):
        mobo = specs.get('mobo', '未知')
        ver = specs.get('board_version', '')
        if ver:
            lines.append(f'• 主機板補充：{mobo} / 版本 {ver}')
        else:
            lines.append(f'• 主機板補充：{mobo}')
    fan_rows = specs.get('cooling_fans', [])
    fan_text = ' / '.join(fan_rows[:3]) if fan_rows else '目前未讀到風扇 RPM，屬 Windows 常見情況。'
    lines.append('• 散熱 / 風扇補充：' + fan_text)
    return '\n'.join(lines)


def _v41_storage_score(specs):
    disks = specs.get("disks", []) or []
    total = float(specs.get("disk_total", 0) or 0)
    text_blob = ' '.join([(d.get('model', '') or '') for d in disks]).lower()
    is_ssd = any(k in text_blob for k in ['ssd', 'nvme', 'pcie', 'sn850', '990 pro', 't500', 'kc3000'])
    if not disks:
        return 55.0
    base = 45.0
    if total >= 4000:
        base = 92.0
    elif total >= 2000:
        base = 84.0
    elif total >= 1000:
        base = 74.0
    elif total >= 512:
        base = 62.0
    else:
        base = 48.0
    if is_ssd:
        base += 8.0
    return max(25.0, min(100.0, base))


def _v41_component_scores(specs, scores):
    ram_nom = nominal_capacity_gb(specs.get('ram_total', 0))
    ram_score = min(100, 30 + ram_nom * 1.35)
    items = {
        'CPU': float(scores.get('cpu_benchmark_ratio', 0) or 0),
        'GPU': float(scores.get('gpu_benchmark_ratio', 0) or 0),
        'RAM': float(ram_score),
        'SSD': float(_v41_storage_score(specs)),
    }
    return items


def _v41_bottleneck_result(specs, scores):
    items = _v41_component_scores(specs, scores)
    if _v41_is_old_hardware(specs, scores):
        return {
            'key': '整機',
            'scores': items,
            'headline': '平台偏舊，單點升級效益有限',
            'detail': '這台設備的限制不只一個零件，若要明顯提升 3A / AI 體驗，建議直接規劃新機。',
        }

    ordered = sorted(items.items(), key=lambda kv: kv[1])
    key, score = ordered[0]
    top_key, top_score = max(items.items(), key=lambda kv: kv[1])
    gap = round(top_score - score, 1)

    if key == 'GPU':
        headline = 'CPU 夠力，但 GPU 是主要瓶頸' if items['CPU'] >= items['GPU'] + 8 else 'GPU 是目前最明顯的限制點'
        detail = '若想提高遊戲張數、2K/4K 畫質或 AI 顯存負載表現，優先補強顯示卡最有感。'
    elif key == 'CPU':
        headline = 'GPU 還跟得上，但 CPU 是主要瓶頸'
        detail = '若常遇到多人場景、模擬、編譯或高幀率瓶頸，處理器會先限制整體體感。'
    elif key == 'RAM':
        headline = 'RAM 是目前最值得先補的瓶頸'
        detail = '多工、剪輯、AI 與大型遊戲切換時，記憶體不足會先拖慢體感。'
    else:
        headline = 'SSD / 儲存空間是目前最值得先補的瓶頸'
        detail = '容量太小或儲存介面較慢時，安裝空間、載入與素材管理都會先卡住。'

    return {
        'key': key,
        'gap': gap,
        'scores': items,
        'headline': headline,
        'detail': detail,
    }


def _v41_draw_radar(canvas, values, labels):
    canvas.delete('all')
    w = max(320, int(canvas.winfo_width() or 360))
    h = max(280, int(canvas.winfo_height() or 300))
    canvas.configure(bg='white', highlightthickness=0)
    canvas.create_rectangle(6, 6, w - 6, h - 6, fill='white', outline='#d8d8d8', width=1)

    title_y = 24
    cx, cy = w // 2, h // 2 + 12
    radius = min(w * 0.28, h * 0.26)
    levels = 5

    def point(angle_deg, r):
        rad = math.radians(angle_deg)
        return cx + r * math.cos(rad), cy - r * math.sin(rad)

    angles = [90, 0, 270, 180]

    for i in range(1, levels + 1):
        r = radius * i / levels
        pts = []
        for a in angles:
            pts.extend(point(a, r))
        canvas.create_polygon(pts, outline='#d6dce5', fill='', width=1)

    for a in angles:
        x, y = point(a, radius)
        canvas.create_line(cx, cy, x, y, fill='#c3cad5', width=1)

    pts = []
    for a, v in zip(angles, values):
        x, y = point(a, radius * max(0, min(100, float(v))) / 100.0)
        pts.extend([x, y])
    canvas.create_polygon(pts, fill='#bdf9ff', outline='#00b7ff', width=2)

    for a, v, lab in zip(angles, values, labels):
        tx, ty = point(a, radius + 34)
        value = f'{v:.0f}'
        if a == 90:
            ty -= 6
        elif a == 270:
            ty += 6
        elif a == 0:
            tx += 4
        else:
            tx -= 4
        canvas.create_text(tx, ty, text=f'{lab}\n{value}', fill='#222222', font=('Arial', 10, 'bold'), justify='center')

    canvas.create_text(cx, title_y, text='硬體能力雷達圖', fill='#333333', font=('Arial', 12, 'bold'))
    canvas.create_text(cx, h - 16, text='分數越接近外圈，代表該項能力越強', fill='#6b7280', font=('Arial', 9))


def _v41_draw_bottleneck_chart(canvas, specs, scores):
    canvas.delete('all')
    w = max(360, int(canvas.winfo_width() or 420))
    h = max(250, int(canvas.winfo_height() or 260))
    canvas.configure(bg='white', highlightthickness=0)
    canvas.create_rectangle(6, 6, w - 6, h - 6, fill='white', outline='#d8d8d8', width=1)

    result = _v41_bottleneck_result(specs, scores)
    items = result['scores']
    order = ['CPU', 'GPU', 'RAM', 'SSD']
    colors = {'CPU': '#4f8ef7', 'GPU': '#ff5c8a', 'RAM': '#00b894', 'SSD': '#f5a623'}
    bottleneck = result['key']

    canvas.create_text(18, 22, text='硬體瓶頸分析圖', anchor='w', fill='#333333', font=('Arial', 12, 'bold'))
    canvas.create_text(18, 44, text=result['headline'], anchor='w', fill='#111111', font=('Arial', 11, 'bold'), width=w - 36)
    canvas.create_text(18, 66, text=result['detail'], anchor='w', fill='#5b6470', font=('Arial', 9), width=w - 36)

    bar_x = 38
    bar_y0 = 102
    bar_w = w - 130
    bar_h = 18
    gap = 28

    for idx, key in enumerate(order):
        y = bar_y0 + idx * gap
        value = max(0, min(100, float(items.get(key, 0))))
        canvas.create_text(bar_x - 8, y + bar_h / 2, text=key, anchor='e', fill='#222222', font=('Arial', 10, 'bold'))
        canvas.create_rectangle(bar_x, y, bar_x + bar_w, y + bar_h, fill='#eef2f7', outline='#d7dde7')
        fill_w = max(6, bar_w * value / 100.0)
        fill = colors[key]
        outline = '#111111' if key == bottleneck else fill
        width = 2 if key == bottleneck else 1
        canvas.create_rectangle(bar_x, y, bar_x + fill_w, y + bar_h, fill=fill, outline=outline, width=width)
        suffix = ' ← 主要瓶頸' if key == bottleneck else ''
        canvas.create_text(bar_x + bar_w + 10, y + bar_h / 2, text=f'{value:.0f}{suffix}', anchor='w', fill='#222222', font=('Arial', 9, 'bold' if key == bottleneck else 'normal'))

    foot = '判讀方式：看哪一項明顯偏低；若整體平台過舊，會直接判定為「整機偏舊，建議換新」。'
    canvas.create_text(18, h - 16, text=foot, anchor='w', fill='#6b7280', font=('Arial', 8), width=w - 36)


def _v41_draw_performance_cards(canvas, specs, scores):
    # 預留未來擴充用，先不啟用。
    pass

def _v41_bind_wrap(self):
    def update(event=None):
        try:
            width = max(260, self.left_frame.winfo_width() - 60)
            for widget in getattr(self, '_v41_wrap_widgets', []):
                try:
                    widget.configure(wraplength=width)
                except Exception:
                    pass
        except Exception:
            pass
    self.left_frame.bind('<Configure>', update, add='+')
    self.after(200, update)


def setup_left_panel_v41(self):
    self._v41_wrap_widgets = []

    def add_label(text, color='#ffffff', font=None, padx=20, pady=2, bold=False):
        if font is None:
            font = ctk.CTkFont(size=15, weight='bold' if bold else 'normal')
        lbl = ctk.CTkLabel(self.left_frame, text=text, justify='left', anchor='w', text_color=color, font=font, wraplength=460)
        lbl.pack(anchor='w', padx=padx, pady=pady, fill='x')
        self._v41_wrap_widgets.append(lbl)
        return lbl

    add_label('[ SYSTEM SPECS ]', color='#00ffff', font=ctk.CTkFont(size=17, weight='bold'), pady=(15, 2))
    add_label(f"CPU: {self.specs['cpu_name']}")
    freq = '5600' if self.specs.get('support_gen5') else '3200'
    add_label(f"RAM: {ram_label(self.specs['ram_total'])} (系統可用 {self.specs.get('ram_total',0)}G)  (已用: {self.specs['ram_used']}G) [{self.specs['ram_type']} {freq}]")
    add_label(f"GPU: {self.specs['gpu_name']}\nVRAM: {self.specs['gpu_vram']} MB (已用: {self.specs['gpu_vram_used']} MB)")

    disk_lines = []
    for idx, d in enumerate(self.specs.get('disks', []), 1):
        size = d.get('size_gb', 0)
        model = d.get('model', f'磁碟 {idx}')
        disk_lines.append(f"Disk {idx}: {model} / {size} GB（已用: {d.get('used_gb', 0)}G）")
    if not disk_lines:
        disk_lines.append(f"Disk: 總共 {self.specs['disk_total']} GB (已用: {self.specs['disk_used']}G)")
    add_label('\n'.join(disk_lines), color='#cccccc')

    if not self.specs.get('is_laptop'):
        board_extra = self.specs.get('board_version', '')
        board_line = f"MOBO: {self.specs.get('mobo', '未知')}" + (f" / Ver {board_extra}" if board_extra else '')
        add_label(board_line, color='#aaaaaa')
        add_label(f"PSU: {self.specs.get('psu', '未知')}", color='#aaaaaa')
        fan_rows = self.specs.get('cooling_fans', [])
        fan_text = '散熱/風扇: ' + (' / '.join(fan_rows) if fan_rows else self.specs.get('cooler_note', '讀不到風扇感測器'))
        add_label(fan_text, color='#aaaaaa')
    mem_sticks = self.specs.get('memory_sticks', [])
    if mem_sticks:
        mem_text = 'RAM 模組：' + ' / '.join([f"{s.get('capacity_gb')}G {s.get('speed','')}" for s in mem_sticks if s.get('capacity_gb')])
        add_label(mem_text, color='#aaaaaa')

    add_label('[ BENCHMARK SCORES ]', color='#00ffff', font=ctk.CTkFont(size=17, weight='bold'), pady=(15, 2))
    add_label(f"CPU Score: {self.scores['CPU']:,} pts", padx=30, pady=1)
    add_label(f"RAM Score: {self.scores['RAM']:,} pts", padx=30, pady=1)
    add_label(f"GPU Score: {self.scores['GPU']:,} pts", padx=30, pady=1)
    add_label(f"AI Score:    {self.scores['AI_Score']:,} pts", color='#ff55ff', padx=30, pady=1)
    total_color = '#00ff00' if self.scores['Total'] > 80000 else '#ffaa00'
    add_label(f"TOTAL: {self.scores['Total']:,}", color=total_color, font=ctk.CTkFont(size=24, weight='bold'), pady=(10, 10))

    add_label(hardware_scene_analysis(self.specs, self.scores), color='#00ff99', pady=(0, 8))
    add_label(hardware_upgrade_suggestions(self.specs, self.scores), color='#ffee88', pady=(0, 10))

    add_label(_v41_extra_hardware_notes(self.specs, self.scores), color='#ffd966', pady=(0, 8))

    # 雷達圖區
    values = [
        float(self.scores.get('game_score_100', 0)),
        float(self.scores.get('prod_score_100', 0)),
        float(self.scores.get('ai_score_100', 0)),
        float(self.scores.get('overall_score_100', 0)),
    ]
    labels = ['遊戲', '生產力', 'AI', '綜合']

    radar_holder = ctk.CTkFrame(self.left_frame, fg_color='#242424', corner_radius=10)
    radar_holder.pack(fill='x', padx=16, pady=(4, 10))
    radar_canvas = tk.Canvas(radar_holder, width=360, height=300, bg='white', highlightthickness=0)
    radar_canvas.pack(fill='x', expand=True, padx=10, pady=10)
    radar_canvas.bind('<Configure>', lambda e: _v41_draw_radar(radar_canvas, values, labels), add='+')
    self.after(200, lambda: _v41_draw_radar(radar_canvas, values, labels))

    bottleneck_holder = ctk.CTkFrame(self.left_frame, fg_color='#242424', corner_radius=10)
    bottleneck_holder.pack(fill='x', padx=16, pady=(0, 18))
    bottleneck_canvas = tk.Canvas(bottleneck_holder, width=420, height=255, bg='white', highlightthickness=0)
    bottleneck_canvas.pack(fill='x', expand=True, padx=10, pady=10)
    bottleneck_canvas.bind('<Configure>', lambda e: _v41_draw_bottleneck_chart(bottleneck_canvas, self.specs, self.scores), add='+')
    self.after(220, lambda: _v41_draw_bottleneck_chart(bottleneck_canvas, self.specs, self.scores))

    _v41_bind_wrap(self)


def v41_post_setup_mid_panel(self):
    # 基於 v38 版面，不動主流程；先停用「開啟商品/搜尋」與手動關鍵字輸入區，避免誤觸。
    try:
        self.open_link_btn.configure(state='disabled')
        self.open_link_btn.pack_forget()
    except Exception:
        pass
    try:
        self.manual_query_frame.pack_forget()
    except Exception:
        pass
    try:
        self.repack_bottom_actions()
    except Exception:
        pass
    try:
        self.price_label.configure(text='請選擇規格並點擊 [查詢時價]。\n已先停用「開啟商品/搜尋」與手動關鍵字輸入。')
    except Exception:
        pass


def show_startup_notice_v41_1(parent):
    """v41.2 啟動公告；不隱藏主視窗，避免使用者覺得按執行沒反應。"""
    win = ctk.CTkToplevel(parent)
    win.title("v41.4 版本公告")
    win.geometry("780x560")
    win.transient(parent)
    win.attributes("-topmost", True)

    frame = ctk.CTkFrame(win, corner_radius=14)
    frame.pack(fill="both", expand=True, padx=18, pady=18)

    ctk.CTkLabel(
        frame,
        text="電腦檢測升級工具 v41.4",
        text_color="#00ffff",
        font=ctk.CTkFont(size=24, weight="bold"),
    ).pack(anchor="w", padx=24, pady=(20, 12))

    box = ctk.CTkTextbox(frame, wrap="word", font=ctk.CTkFont(size=15), height=350)
    box.pack(fill="both", expand=True, padx=24, pady=(0, 14))
    box.insert("end", "新增與強化\n")
    box.insert("end", "• 新增硬體能力雷達圖，依遊戲、生產力、AI、綜合四項能力繪製。\n")
    box.insert("end", "• 新增目前最值得升級的一項，放在升級建議下方，方便小白快速判斷。\n")
    box.insert("end", "• 桌機端補強主機板資訊、風扇 / 散熱資訊顯示。\n\n")
    box.insert("end", "錯誤修正與強化\n")
    box.insert("end", "• 修正 v41 啟動時可能因公告視窗與主視窗隱藏順序造成看起來沒反應。\n")
    box.insert("end", "• 啟動時不再先隱藏主視窗，公告會在主視窗可見後顯示。\n")
    box.insert("end", "• 雷達圖持續保留白底、深色文字與淡色格線，提升可讀性。\n\n")
    box.insert("end", "注意事項\n")
    box.insert("end", "• AI 市場與硬體價格波動大，有無貨、未上架或價格不正確，仍以實際購買網站為準。\n")
    box.insert("end", "• 研發版本不代表最終品質。\n")
    box.configure(state="disabled")

    ctk.CTkButton(frame, text="確認進入", command=win.destroy, height=42, width=220).pack(pady=(0, 20))

    try:
        win.grab_set()
        win.focus_force()
    except Exception:
        pass


def v41_init(self):
    # v41.1：不再 withdraw 主視窗；先讓主 UI 出現，再用 after 顯示公告。
    # 這樣即使公告視窗被系統擋住，也不會看起來像「按執行沒反應」。
    super(ROGApp, self).__init__()
    self.specs = get_specs()
    self.scores = calculate_score(self.specs)
    self.is_laptop = self.specs['is_laptop']
    self.cart_items = {}
    self.build_step = 0
    self.build_max_steps = 0
    self.build_context = {}
    self.current_mode = ""
    self.ai_history = []
    self.ai_request_times = []
    self.ai_recent_prompts = []
    self.ai_cooldown_until = 0
    self.ai_locked_until_close = False
    self.irrelevant_count = 0
    self.ui_scale_percent = 100
    self.cart_window = None

    device_type = '筆記型電腦' if self.is_laptop else '桌上型電腦'
    self.title(f'電腦檢測升級工具 {V41_VERSION} - [{device_type}]')
    self.geometry('1920x1040')
    self.minsize(1450, 850)
    self.resizable(True, True)

    self.topbar = ctk.CTkFrame(self, fg_color='#202020', height=38, corner_radius=0)
    self.topbar.pack(fill='x', side='top')
    ctk.CTkLabel(self.topbar, text=f'電腦硬體 AI 顧問 {V41_VERSION}', text_color='#00ffff', font=ctk.CTkFont(size=15, weight='bold')).pack(side='left', padx=14)
    ctk.CTkLabel(self.topbar, text='字體/介面比例', text_color='#cccccc').pack(side='right', padx=(8, 4))
    self.scale_menu = ctk.CTkOptionMenu(
        self.topbar,
        values=['25%', '50%', '75%', '100%', '125%', '150%', '175%', '200%', '250%', '300%', '400%', '500%'],
        command=self.set_ui_scale,
        width=95,
    )
    self.scale_menu.set('100%')
    self.scale_menu.pack(side='right', padx=10, pady=5)

    self.main_pane = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashwidth=8, bd=0, bg='#1f1f1f', relief='flat')
    self.main_pane.pack(fill='both', expand=True, padx=8, pady=8)

    self.left_pane_holder = ctk.CTkFrame(self.main_pane, fg_color='transparent', corner_radius=0)
    self.ai_pane_holder = ctk.CTkFrame(self.main_pane, fg_color='transparent', corner_radius=0)
    self.work_pane_holder = ctk.CTkFrame(self.main_pane, fg_color='transparent', corner_radius=0)
    self.main_pane.add(self.left_pane_holder, minsize=380, width=520, stretch='first')
    self.main_pane.add(self.ai_pane_holder, minsize=420, width=560, stretch='always')
    self.main_pane.add(self.work_pane_holder, minsize=560, width=840, stretch='last')

    self.left_frame = ctk.CTkScrollableFrame(self.left_pane_holder, width=510, corner_radius=10)
    self.ai_frame = ctk.CTkFrame(self.ai_pane_holder, corner_radius=10)
    self.mid_frame = ctk.CTkScrollableFrame(self.work_pane_holder, width=830, corner_radius=10)
    self.left_frame.pack(fill='both', expand=True)
    self.ai_frame.pack(fill='both', expand=True)
    self.mid_frame.pack(fill='both', expand=True)

    self.setup_left_panel()
    self.setup_ai_panel_v38()
    _v37_original_setup_mid_panel(self)
    v41_post_setup_mid_panel(self)
    setup_cart_button_v38(self)

    self.bind_all('<MouseWheel>', self._on_mousewheel, add='+')
    self.bind_all('<Button-4>', self._on_mousewheel, add='+')
    self.bind_all('<Button-5>', self._on_mousewheel, add='+')

    try:
        self.after(140, lambda: self.state('zoomed'))
    except Exception:
        pass
    try:
        self.after(320, lambda: show_startup_notice_v41_1(self))
    except Exception:
        pass


# 套用 v41.1 覆蓋（保留 v38 既有穩定 UI 與 AI 流程，修正啟動公告與補強左側分析）。
ROGApp.__init__ = v41_init
ROGApp.setup_left_panel = setup_left_panel_v41




# ============================================================
# v41.4：matplotlib 白底圖表 + 縮放同步 + 公告內容同步
# ============================================================
try:
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib import rcParams
    rcParams["font.sans-serif"] = [
        "Microsoft JhengHei", "Microsoft YaHei", "Noto Sans CJK TC", "Noto Sans CJK SC",
        "SimHei", "Arial Unicode MS", "DejaVu Sans"
    ]
    rcParams["axes.unicode_minus"] = False
    MPL_AVAILABLE = True
except Exception:
    MPL_AVAILABLE = False
    Figure = None
    FigureCanvasTkAgg = None


def _v41_chart_scale(scale_pct=100):
    try:
        pct = float(scale_pct)
    except Exception:
        pct = 100.0
    return max(0.75, min(3.0, pct / 100.0))


def _v41_chart_font_bundle(scale_pct=100):
    s = _v41_chart_scale(scale_pct)
    return {
        'title': max(16, int(17 * s)),
        'subtitle': max(12, int(12 * s)),
        'tick': max(11, int(11 * s)),
        'label': max(12, int(12 * s)),
        'value': max(12, int(12 * s)),
        'note': max(9, int(9 * s)),
    }


def _v41_clear_children(container):
    try:
        for child in container.winfo_children():
            child.destroy()
    except Exception:
        pass


def _v41_render_chart_fallback(container, title, message):
    _v41_clear_children(container)
    lbl = ctk.CTkLabel(
        container,
        text=f"{title}\n{message}\n\n請安裝：pip install matplotlib",
        text_color="#ffdd88",
        justify="center",
        wraplength=420,
    )
    lbl.pack(fill="both", expand=True, padx=14, pady=14)


def _v41_render_radar_mpl(container, values, labels, scale_pct=100):
    if not MPL_AVAILABLE:
        _v41_render_chart_fallback(container, "硬體能力雷達圖", "matplotlib 尚未安裝，暫時無法顯示新版白底圖表。")
        return

    _v41_clear_children(container)
    fonts = _v41_chart_font_bundle(scale_pct)
    scale = _v41_chart_scale(scale_pct)
    width_px = max(520, int(container.winfo_width() or 560))
    height_px = max(int(330 * scale), int(container.winfo_height() or 340))

    fig = Figure(figsize=(width_px / 100, height_px / 100), dpi=100, facecolor="white", constrained_layout=True)
    ax = fig.add_subplot(111, polar=True)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    vals = [max(0, min(100, float(v))) for v in values]
    n = len(labels)
    angles = [i / n * 2 * math.pi for i in range(n)]
    closed_angles = angles + angles[:1]
    closed_vals = vals + vals[:1]

    ax.set_theta_offset(math.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_ylim(0, 100)

    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(["20", "40", "60", "80", "100"], fontsize=fonts['tick'], color="#7b8794")
    ax.tick_params(axis="y", pad=6 * scale)

    xtick_labels = [f"{lab}\n{int(round(v))}" for lab, v in zip(labels, vals)]
    ax.set_xticks(angles)
    ax.set_xticklabels(xtick_labels, fontsize=fonts['label'], color="#111827", fontweight="bold")
    ax.tick_params(axis="x", pad=14 * scale)

    ax.grid(color="#d6dde8", linestyle="-", linewidth=0.9)
    ax.spines["polar"].set_color("#ccd5e1")
    ax.spines["polar"].set_linewidth(1.0)

    ax.plot(closed_angles, closed_vals, color="#008cff", linewidth=2.8)
    ax.fill(closed_angles, closed_vals, color="#9be7ff", alpha=0.72)
    ax.scatter(angles, vals, s=max(24, 36 * scale), color="#008cff", zorder=3)

    ax.set_title("硬體能力雷達圖", fontsize=fonts['title'], color="#111827", pad=22 * scale, fontweight="bold")
    fig.text(0.5, 0.025, "分數越接近外圈，代表該項能力越強", ha="center", fontsize=fonts['note'], color="#64748b")

    canvas = FigureCanvasTkAgg(fig, master=container)
    widget = canvas.get_tk_widget()
    widget.configure(bg="white", highlightthickness=0)
    widget.pack(fill="both", expand=True, padx=8, pady=8)
    canvas.draw_idle()
    container._mpl_canvas = canvas
    container._mpl_fig = fig


def _v41_render_bottleneck_mpl(container, specs, scores, scale_pct=100):
    if not MPL_AVAILABLE:
        _v41_render_chart_fallback(container, "硬體瓶頸分析圖", "matplotlib 尚未安裝，暫時無法顯示新版白底圖表。")
        return

    _v41_clear_children(container)
    fonts = _v41_chart_font_bundle(scale_pct)
    scale = _v41_chart_scale(scale_pct)
    width_px = max(560, int(container.winfo_width() or 620))
    height_px = max(int(330 * scale), int(container.winfo_height() or 360))

    result = _v41_bottleneck_result(specs, scores)
    items = result['scores']
    order = ['CPU', 'GPU', 'RAM', 'SSD']
    vals = [max(0, min(100, float(items.get(k, 0)))) for k in order]
    colors = {'CPU': '#4f8ef7', 'GPU': '#ff5c8a', 'RAM': '#14b8a6', 'SSD': '#f59e0b'}
    bottleneck = result['key']

    fig = Figure(figsize=(width_px / 100, height_px / 100), dpi=100, facecolor="white", constrained_layout=True)
    gs = fig.add_gridspec(2, 1, height_ratios=[1.0, 1.6], hspace=0.04)
    ax_text = fig.add_subplot(gs[0])
    ax = fig.add_subplot(gs[1])
    fig.patch.set_facecolor("white")
    ax_text.axis("off")

    ax_text.text(0.01, 0.90, "硬體瓶頸分析圖", fontsize=fonts['title'], fontweight="bold", color="#111827", ha="left", va="top")
    ax_text.text(0.01, 0.57, result['headline'], fontsize=fonts['subtitle'] + 1, fontweight="bold", color="#111827", ha="left", va="top")
    ax_text.text(0.01, 0.18, result['detail'], fontsize=fonts['note'] + 1, color="#475569", ha="left", va="bottom", wrap=True)

    y = list(range(len(order)))
    ax.barh(y, [100] * len(order), color="#eef2f7", edgecolor="#d8dee9", height=0.58)
    bars = ax.barh(y, vals, color=[colors[k] for k in order], height=0.58)

    ax.set_xlim(0, 115)
    ax.set_yticks(y)
    ax.set_yticklabels(order, fontsize=fonts['label'], color="#111827", fontweight="bold")
    ax.set_xticks([0, 20, 40, 60, 80, 100])
    ax.set_xticklabels(["0", "20", "40", "60", "80", "100"], fontsize=fonts['tick'], color="#64748b")
    ax.grid(axis="x", color="#e2e8f0", linestyle="--", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_facecolor("white")
    for spine in ["top", "right", "left", "bottom"]:
        ax.spines[spine].set_visible(False)
    ax.invert_yaxis()

    for idx, (bar, key, value) in enumerate(zip(bars, order, vals)):
        if key == bottleneck:
            bar.set_edgecolor("#111827")
            bar.set_linewidth(1.8)
        suffix = " ← 主要瓶頸" if key == bottleneck else ""
        ax.text(min(value + 1.5, 109), idx, f"{value:.0f}{suffix}", va="center", ha="left", fontsize=fonts['value'], color="#111827", fontweight="bold" if key == bottleneck else "normal")

    fig.text(0.5, 0.025, "判讀：哪一項明顯偏低，通常就是目前最拖累體感的地方。", ha="center", fontsize=fonts['note'], color="#64748b")

    canvas = FigureCanvasTkAgg(fig, master=container)
    widget = canvas.get_tk_widget()
    widget.configure(bg="white", highlightthickness=0)
    widget.pack(fill="both", expand=True, padx=8, pady=8)
    canvas.draw_idle()
    container._mpl_canvas = canvas
    container._mpl_fig = fig


def _v41_update_chart_heights(self):
    scale = _v41_chart_scale(getattr(self, 'ui_scale_percent', 100))
    radar_h = int(360 * scale)
    bottleneck_h = int(355 * scale)
    try:
        self.radar_holder.configure(height=radar_h)
        self.radar_holder.pack_propagate(False)
    except Exception:
        pass
    try:
        self.bottleneck_holder.configure(height=bottleneck_h)
        self.bottleneck_holder.pack_propagate(False)
    except Exception:
        pass


def _v41_redraw_matplotlib_charts(self):
    try:
        _v41_update_chart_heights(self)
        if hasattr(self, 'radar_holder') and hasattr(self, '_radar_values'):
            _v41_render_radar_mpl(self.radar_holder, self._radar_values, self._radar_labels, getattr(self, 'ui_scale_percent', 100))
        if hasattr(self, 'bottleneck_holder'):
            _v41_render_bottleneck_mpl(self.bottleneck_holder, self.specs, self.scores, getattr(self, 'ui_scale_percent', 100))
    except Exception:
        pass


def _v41_schedule_chart_redraw(self, delay=120):
    try:
        if hasattr(self, '_chart_redraw_job') and self._chart_redraw_job:
            self.after_cancel(self._chart_redraw_job)
    except Exception:
        pass
    try:
        self._chart_redraw_job = self.after(delay, lambda: _v41_redraw_matplotlib_charts(self))
    except Exception:
        pass


def v41_set_ui_scale_with_charts(self, value):
    try:
        v33_set_ui_scale(self, value)
    finally:
        _v41_schedule_chart_redraw(self, delay=180)


def setup_left_panel_v41_mpl(self):
    self._v41_wrap_widgets = []

    def add_label(text, color='#ffffff', font=None, padx=20, pady=2, bold=False):
        if font is None:
            font = ctk.CTkFont(size=15, weight='bold' if bold else 'normal')
        lbl = ctk.CTkLabel(self.left_frame, text=text, justify='left', anchor='w', text_color=color, font=font, wraplength=460)
        lbl.pack(anchor='w', padx=padx, pady=pady, fill='x')
        self._v41_wrap_widgets.append(lbl)
        return lbl

    add_label('[ SYSTEM SPECS ]', color='#00ffff', font=ctk.CTkFont(size=17, weight='bold'), pady=(15, 2))
    add_label(f"CPU: {self.specs['cpu_name']}")
    freq = '5600' if self.specs.get('support_gen5') else '3200'
    add_label(f"RAM: {ram_label(self.specs['ram_total'])} (系統可用 {self.specs.get('ram_total',0)}G)  (已用: {self.specs['ram_used']}G) [{self.specs['ram_type']} {freq}]")
    add_label(f"GPU: {self.specs['gpu_name']}\nVRAM: {self.specs['gpu_vram']} MB (已用: {self.specs['gpu_vram_used']} MB)")

    disk_lines = []
    for idx, d in enumerate(self.specs.get('disks', []), 1):
        size = d.get('size_gb', 0)
        model = d.get('model', f'磁碟 {idx}')
        disk_lines.append(f"Disk {idx}: {model} / {size} GB（已用: {d.get('used_gb', 0)}G）")
    if not disk_lines:
        disk_lines = [f"Disk: 總共 {self.specs.get('disk_total', 0)} GB（已用: {self.specs.get('disk_used', 0)}G）"]
    add_label('\n'.join(disk_lines), color="#cccccc")

    if not self.specs.get('is_laptop'):
        board_extra = self.specs.get('board_version', '')
        board_line = f"MOBO: {self.specs.get('mobo', '未知')}" + (f" / Ver {board_extra}" if board_extra else '')
        add_label(board_line, color='#aaaaaa')
        add_label(f"PSU: {self.specs.get('psu', '未知')}", color='#aaaaaa')
        fan_rows = self.specs.get('cooling_fans', [])
        fan_text = '散熱/風扇: ' + (' / '.join(fan_rows) if fan_rows else self.specs.get('cooler_note', '讀不到風扇感測器'))
        add_label(fan_text, color='#aaaaaa')
    mem_sticks = self.specs.get('memory_sticks', [])
    if mem_sticks:
        mem_text = 'RAM 模組：' + ' / '.join([f"{s.get('capacity_gb')}G {s.get('speed','')}" for s in mem_sticks if s.get('capacity_gb')])
        add_label(mem_text, color='#aaaaaa')

    add_label('[ BENCHMARK SCORES ]', color='#00ffff', font=ctk.CTkFont(size=17, weight='bold'), pady=(15, 2))
    add_label(f"CPU Score: {self.scores['CPU']:,} pts", padx=30, pady=1)
    add_label(f"RAM Score: {self.scores['RAM']:,} pts", padx=30, pady=1)
    add_label(f"GPU Score: {self.scores['GPU']:,} pts", padx=30, pady=1)
    add_label(f"AI Score:    {self.scores['AI_Score']:,} pts", color='#ff55ff', padx=30, pady=1)
    total_color = '#00ff00' if self.scores['Total'] > 80000 else '#ffaa00'
    add_label(f"TOTAL: {self.scores['Total']:,}", color=total_color, font=ctk.CTkFont(size=24, weight='bold'), pady=(10, 10))

    add_label(hardware_scene_analysis(self.specs, self.scores), color='#00ff99', pady=(0, 8))
    add_label(hardware_upgrade_suggestions(self.specs, self.scores), color='#ffee88', pady=(0, 10))
    add_label(_v41_extra_hardware_notes(self.specs, self.scores), color='#ffd966', pady=(0, 8))

    self._radar_values = [
        float(self.scores.get('game_score_100', 0)),
        float(self.scores.get('prod_score_100', 0)),
        float(self.scores.get('ai_score_100', 0)),
        float(self.scores.get('overall_score_100', 0)),
    ]
    self._radar_labels = ['遊戲', '生產力', 'AI', '綜合']

    self.radar_holder = ctk.CTkFrame(self.left_frame, fg_color='#242424', corner_radius=10)
    self.radar_holder.pack(fill='x', padx=16, pady=(4, 10))
    self.radar_holder.pack_propagate(False)
    self.radar_holder.bind('<Configure>', lambda e: _v41_schedule_chart_redraw(self, delay=120), add='+')

    self.bottleneck_holder = ctk.CTkFrame(self.left_frame, fg_color='#242424', corner_radius=10)
    self.bottleneck_holder.pack(fill='x', padx=16, pady=(0, 18))
    self.bottleneck_holder.pack_propagate(False)
    self.bottleneck_holder.bind('<Configure>', lambda e: _v41_schedule_chart_redraw(self, delay=120), add='+')

    _v41_update_chart_heights(self)
    self.after(300, lambda: _v41_redraw_matplotlib_charts(self))
    _v41_bind_wrap(self)


def show_startup_notice_v41_4(parent):
    """v41.4 更新公告：以後每版都在這裡同步新增 / 修復內容。"""
    win = ctk.CTkToplevel(parent)
    win.title("v41.4 版本公告")
    win.geometry("820x620")
    win.transient(parent)
    win.attributes("-topmost", True)

    frame = ctk.CTkFrame(win, corner_radius=14)
    frame.pack(fill="both", expand=True, padx=18, pady=18)

    ctk.CTkLabel(
        frame,
        text="電腦檢測升級工具 v41.4",
        text_color="#00ffff",
        font=ctk.CTkFont(size=24, weight="bold"),
    ).pack(anchor="w", padx=24, pady=(20, 12))

    box = ctk.CTkTextbox(frame, wrap="word", font=ctk.CTkFont(size=15), height=390)
    box.pack(fill="both", expand=True, padx=24, pady=(0, 14))
    box.insert("end", "新增與強化\n")
    box.insert("end", "• 雷達圖改用 matplotlib 白底圖表，字體與標籤更清楚。\n")
    box.insert("end", "• 瓶頸分析圖同步改用 matplotlib，能更明確看出 CPU / GPU / RAM / SSD 誰在拖累。\n")
    box.insert("end", "• 圖表會跟右上角 25%～500% 字體/介面比例同步重繪。\n")
    box.insert("end", "• 保留目前最值得升級項目、老舊設備換新補充、主機板與風扇資訊。\n\n")
    box.insert("end", "錯誤修正與強化\n")
    box.insert("end", "• 修正 v41.3 圖表覆蓋點在主程式啟動後才套用，導致看起來沒有變化的問題。\n")
    box.insert("end", "• 修正雷達圖中文字太小、標籤容易被擋住的問題。\n")
    box.insert("end", "• 公告內容已同步更新，之後每次改版都會更新這裡。\n\n")
    box.insert("end", "注意事項\n")
    box.insert("end", "• 若沒有安裝 matplotlib，圖表區會提示安裝指令。\n")
    box.insert("end", "• AI 市場與硬體價格波動大，有無貨或未上架價格不正確，仍以實際購買網站為準。\n")
    box.insert("end", "• 研發版本不代表最終品質。\n")
    box.configure(state="disabled")

    ctk.CTkButton(win, text="確認進入", command=win.destroy, width=280, height=44).pack(pady=(0, 24))
    win.grab_set()
    win.focus_force()


def v41_4_init(self):
    try:
        self.withdraw()
    except Exception:
        pass

    super(ROGApp, self).__init__()
    self.specs = get_specs()
    self.scores = calculate_score(self.specs)
    self.is_laptop = self.specs['is_laptop']
    self.cart_items = {}
    self.build_step = 0
    self.build_max_steps = 0
    self.build_context = {}
    self.current_mode = ""
    self.ai_history = []
    self.ai_request_times = []
    self.ai_recent_prompts = []
    self.ai_cooldown_until = 0
    self.ai_locked_until_close = False
    self.irrelevant_count = 0
    self.ui_scale_percent = 100
    self.cart_window = None

    device_type = '筆記型電腦' if self.is_laptop else '桌上型電腦'
    self.title(f'電腦檢測升級工具 v41.4 - [{device_type}]')
    self.geometry('1920x1040')
    self.minsize(1450, 850)
    self.resizable(True, True)

    self.topbar = ctk.CTkFrame(self, fg_color='#202020', height=38, corner_radius=0)
    self.topbar.pack(fill='x', side='top')
    ctk.CTkLabel(self.topbar, text='電腦硬體 AI 顧問 v41.4', text_color='#00ffff', font=ctk.CTkFont(size=15, weight='bold')).pack(side='left', padx=14)
    ctk.CTkLabel(self.topbar, text='字體/介面比例', text_color='#cccccc').pack(side='right', padx=(8, 4))
    self.scale_menu = ctk.CTkOptionMenu(
        self.topbar,
        values=['25%', '50%', '75%', '100%', '125%', '150%', '175%', '200%', '250%', '300%', '400%', '500%'],
        command=self.set_ui_scale,
        width=95,
    )
    self.scale_menu.set('100%')
    self.scale_menu.pack(side='right', padx=10, pady=5)

    self.main_pane = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashwidth=8, bd=0, bg='#1f1f1f', relief='flat')
    self.main_pane.pack(fill='both', expand=True, padx=8, pady=8)

    self.left_pane_holder = ctk.CTkFrame(self.main_pane, fg_color='transparent', corner_radius=0)
    self.ai_pane_holder = ctk.CTkFrame(self.main_pane, fg_color='transparent', corner_radius=0)
    self.work_pane_holder = ctk.CTkFrame(self.main_pane, fg_color='transparent', corner_radius=0)
    self.main_pane.add(self.left_pane_holder, minsize=380, width=520, stretch='first')
    self.main_pane.add(self.ai_pane_holder, minsize=420, width=560, stretch='always')
    self.main_pane.add(self.work_pane_holder, minsize=560, width=840, stretch='last')

    self.left_frame = ctk.CTkScrollableFrame(self.left_pane_holder, width=510, corner_radius=10)
    self.ai_frame = ctk.CTkFrame(self.ai_pane_holder, corner_radius=10)
    self.mid_frame = ctk.CTkScrollableFrame(self.work_pane_holder, width=830, corner_radius=10)
    self.left_frame.pack(fill='both', expand=True)
    self.ai_frame.pack(fill='both', expand=True)
    self.mid_frame.pack(fill='both', expand=True)

    self.setup_left_panel()
    self.setup_ai_panel_v38()
    _v37_original_setup_mid_panel(self)
    v41_post_setup_mid_panel(self)
    setup_cart_button_v38(self)

    self.bind_all('<MouseWheel>', self._on_mousewheel, add='+')
    self.bind_all('<Button-4>', self._on_mousewheel, add='+')
    self.bind_all('<Button-5>', self._on_mousewheel, add='+')

    try:
        self.deiconify()
        self.after(140, lambda: self.state('zoomed'))
    except Exception:
        pass
    try:
        self.after(320, lambda: show_startup_notice_v41_4(self))
    except Exception:
        pass


# 套用 v41.4：注意要放在 app = ROGApp() 前，否則圖表覆蓋不會生效。
ROGApp.__init__ = v41_4_init
ROGApp.setup_left_panel = setup_left_panel_v41_mpl
ROGApp.set_ui_scale = v41_set_ui_scale_with_charts




# ============================================================
# v42：UI 可讀性 / 換行 / 主題模式 / 圖表裁切修復
# ============================================================
V42_VERSION = "v42"


def _v42_safe_text(text):
    """讓左側長文字更容易換行，避免拖拉欄位或放大字體後被吃掉。"""
    if text is None:
        return ""
    s = str(text)
    replacements = {
        " | ": " ｜ ",
        "；": "；\n",
        "。": "。\n",
        "，": "，",
    }
    for a, b in replacements.items():
        s = s.replace(a, b)
    # 評分方式與分級制特別容易太長，先主動斷行。
    s = s.replace("GPU：Time Spy", "GPU：Time Spy")
    s = s.replace("CPU：Geekbench6", "\nCPU：Geekbench6")
    s = s.replace("綜合：", "\n綜合：")
    s = s.replace("加權；", "加權；\n")
    s = s.replace("分級：", "分級：\n")
    s = s.replace("SSS>115", "SSS>115")
    s = s.replace(" SS+", "\nSS+")
    s = s.replace(" SS95", "\nSS95")
    s = s.replace(" S+88", "\nS+88")
    s = s.replace(" S82", "\nS82")
    s = s.replace(" A++76", "\nA++76")
    s = s.replace(" A+70", "\nA+70")
    s = s.replace(" A64", "\nA64")
    s = s.replace(" B++56", "\nB++56")
    s = s.replace(" B+48", "\nB+48")
    s = s.replace(" B40", "\nB40")
    s = s.replace(" C30", "\nC30")
    s = s.replace(" D20", "\nD20")
    s = s.replace(" E10", "\nE10")
    s = s.replace(" F<10", "\nF<10")
    # 去掉多餘空行。
    lines = [ln.rstrip() for ln in s.splitlines()]
    out = []
    for ln in lines:
        if ln or (out and out[-1]):
            out.append(ln)
    return "\n".join(out).strip()


def _v42_widget_scale(self):
    return max(0.5, min(5.0, getattr(self, 'ui_scale_percent', 100) / 100.0))


def _v42_current_wrap_width(self):
    try:
        holder_w = self.left_pane_holder.winfo_width()
    except Exception:
        holder_w = 520
    try:
        frame_w = self.left_frame.winfo_width()
        if frame_w > 80:
            holder_w = min(holder_w if holder_w > 80 else frame_w, frame_w)
    except Exception:
        pass
    # 字體放大時 CTk 也會放大 padding，所以 wrap 要保守一點。
    scale = _v42_widget_scale(self)
    return max(140, int(holder_w - 70 * scale))


def _v42_refresh_wraps(self):
    try:
        width = _v42_current_wrap_width(self)
        for widget in getattr(self, '_v41_wrap_widgets', []):
            try:
                widget.configure(wraplength=width)
            except Exception:
                pass
    except Exception:
        pass


def _v42_bind_wrap(self):
    def update(event=None):
        _v42_refresh_wraps(self)
    for target in [getattr(self, 'left_frame', None), getattr(self, 'left_pane_holder', None), getattr(self, 'main_pane', None)]:
        try:
            target.bind('<Configure>', update, add='+')
        except Exception:
            pass
    self.after(200, update)
    self.after(800, update)


def _v42_chart_font_bundle(scale_pct=100):
    # 圖表不完全跟 UI 一起巨大化，避免 500% 時文字把圖吃掉。
    s = max(0.95, min(2.4, float(scale_pct) / 100.0))
    return {
        'title': max(16, int(15 * s)),
        'subtitle': max(13, int(12 * s)),
        'tick': max(11, int(9.5 * s)),
        'label': max(12, int(10.5 * s)),
        'value': max(12, int(10.5 * s)),
        'note': max(10, int(8.5 * s)),
    }


def _v42_chart_scale(scale_pct=100):
    return max(1.0, min(2.2, float(scale_pct) / 100.0))


def _v42_update_chart_heights(self):
    scale = _v42_chart_scale(getattr(self, 'ui_scale_percent', 100))
    radar_h = int(430 * scale)
    bottleneck_h = int(390 * scale)
    try:
        self.radar_holder.configure(height=radar_h)
        self.radar_holder.pack_propagate(False)
    except Exception:
        pass
    try:
        self.bottleneck_holder.configure(height=bottleneck_h)
        self.bottleneck_holder.pack_propagate(False)
    except Exception:
        pass


def _v42_render_radar_mpl(container, values, labels, scale_pct=100):
    if not MPL_AVAILABLE:
        _v41_render_chart_fallback(container, "硬體能力雷達圖", "matplotlib 尚未安裝，暫時無法顯示新版白底圖表。")
        return
    _v41_clear_children(container)
    fonts = _v42_chart_font_bundle(scale_pct)
    scale = _v42_chart_scale(scale_pct)
    width_px = max(620, int(container.winfo_width() or 680))
    height_px = max(int(420 * scale), int(container.winfo_height() or 430))

    fig = Figure(figsize=(width_px / 100, height_px / 100), dpi=100, facecolor='white')
    ax = fig.add_subplot(111, polar=True)
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')
    fig.subplots_adjust(left=0.16, right=0.84, top=0.78, bottom=0.22)

    vals = [max(0, min(100, float(v))) for v in values]
    n = len(labels)
    angles = [i / n * 2 * math.pi for i in range(n)]
    closed_angles = angles + angles[:1]
    closed_vals = vals + vals[:1]

    ax.set_theta_offset(math.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(['20', '40', '60', '80', '100'], fontsize=fonts['tick'], color='#64748b')
    ax.tick_params(axis='y', pad=8)

    xtick_labels = [f'{lab}\n{int(round(v))}' for lab, v in zip(labels, vals)]
    ax.set_xticks(angles)
    ax.set_xticklabels(xtick_labels, fontsize=fonts['label'], color='#111827', fontweight='bold')
    ax.tick_params(axis='x', pad=22)

    ax.grid(color='#d6dde8', linestyle='-', linewidth=0.95)
    ax.spines['polar'].set_color('#ccd5e1')
    ax.spines['polar'].set_linewidth(1.0)
    ax.plot(closed_angles, closed_vals, color='#008cff', linewidth=3.0)
    ax.fill(closed_angles, closed_vals, color='#9be7ff', alpha=0.72)
    ax.scatter(angles, vals, s=max(32, 44 * scale), color='#008cff', zorder=3)
    ax.set_title('硬體能力雷達圖', fontsize=fonts['title'], color='#111827', pad=34, fontweight='bold')
    fig.text(0.5, 0.08, '分數越接近外圈，代表該項能力越強', ha='center', fontsize=fonts['note'], color='#64748b')

    canvas = FigureCanvasTkAgg(fig, master=container)
    widget = canvas.get_tk_widget()
    widget.configure(bg='white', highlightthickness=0)
    widget.pack(fill='both', expand=True, padx=10, pady=10)
    canvas.draw_idle()
    container._mpl_canvas = canvas
    container._mpl_fig = fig


def _v42_render_bottleneck_mpl(container, specs, scores, scale_pct=100):
    if not MPL_AVAILABLE:
        _v41_render_chart_fallback(container, "硬體瓶頸分析圖", "matplotlib 尚未安裝，暫時無法顯示新版白底圖表。")
        return
    _v41_clear_children(container)
    fonts = _v42_chart_font_bundle(scale_pct)
    scale = _v42_chart_scale(scale_pct)
    width_px = max(640, int(container.winfo_width() or 720))
    height_px = max(int(390 * scale), int(container.winfo_height() or 390))

    result = _v41_bottleneck_result(specs, scores)
    items = result['scores']
    order = ['CPU', 'GPU', 'RAM', 'SSD']
    vals = [max(0, min(100, float(items.get(k, 0)))) for k in order]
    colors = {'CPU': '#4f8ef7', 'GPU': '#ff5c8a', 'RAM': '#14b8a6', 'SSD': '#f59e0b'}
    bottleneck = result['key']

    fig = Figure(figsize=(width_px / 100, height_px / 100), dpi=100, facecolor='white')
    fig.subplots_adjust(left=0.12, right=0.90, top=0.90, bottom=0.16)
    ax_text = fig.add_axes([0.04, 0.71, 0.92, 0.24])
    ax = fig.add_axes([0.10, 0.20, 0.80, 0.45])
    fig.patch.set_facecolor('white')
    ax_text.axis('off')
    ax_text.text(0.0, 0.96, '硬體瓶頸分析圖', fontsize=fonts['title'], fontweight='bold', color='#111827', ha='left', va='top')
    ax_text.text(0.0, 0.60, result['headline'], fontsize=fonts['subtitle'] + 1, fontweight='bold', color='#111827', ha='left', va='top')
    ax_text.text(0.0, 0.22, result['detail'], fontsize=fonts['note'] + 1, color='#475569', ha='left', va='top', wrap=True)

    y = list(range(len(order)))
    ax.barh(y, [100] * len(order), color='#eef2f7', edgecolor='#d8dee9', height=0.58)
    bars = ax.barh(y, vals, color=[colors[k] for k in order], height=0.58)
    ax.set_xlim(0, 122)
    ax.set_yticks(y)
    ax.set_yticklabels(order, fontsize=fonts['label'], color='#111827', fontweight='bold')
    ax.set_xticks([0, 20, 40, 60, 80, 100])
    ax.set_xticklabels(['0', '20', '40', '60', '80', '100'], fontsize=fonts['tick'], color='#64748b')
    ax.grid(axis='x', color='#e2e8f0', linestyle='--', linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_facecolor('white')
    for spine in ['top', 'right', 'left', 'bottom']:
        ax.spines[spine].set_visible(False)
    ax.invert_yaxis()

    for idx, (bar, key, value) in enumerate(zip(bars, order, vals)):
        if key == bottleneck:
            bar.set_edgecolor('#111827')
            bar.set_linewidth(1.8)
        suffix = ' ← 主要瓶頸' if key == bottleneck else ''
        ax.text(min(value + 1.8, 116), idx, f'{value:.0f}{suffix}', va='center', ha='left', fontsize=fonts['value'], color='#111827', fontweight='bold' if key == bottleneck else 'normal')
    fig.text(0.5, 0.06, '判讀：哪一項明顯偏低，通常就是目前最拖累體感的地方。', ha='center', fontsize=fonts['note'], color='#64748b')

    canvas = FigureCanvasTkAgg(fig, master=container)
    widget = canvas.get_tk_widget()
    widget.configure(bg='white', highlightthickness=0)
    widget.pack(fill='both', expand=True, padx=10, pady=10)
    canvas.draw_idle()
    container._mpl_canvas = canvas
    container._mpl_fig = fig


def _v42_redraw_charts(self):
    try:
        _v42_update_chart_heights(self)
        if hasattr(self, 'radar_holder') and hasattr(self, '_radar_values'):
            _v42_render_radar_mpl(self.radar_holder, self._radar_values, self._radar_labels, getattr(self, 'ui_scale_percent', 100))
        if hasattr(self, 'bottleneck_holder'):
            _v42_render_bottleneck_mpl(self.bottleneck_holder, self.specs, self.scores, getattr(self, 'ui_scale_percent', 100))
    except Exception:
        pass


def _v42_schedule_redraw(self, delay=160):
    try:
        if hasattr(self, '_chart_redraw_job') and self._chart_redraw_job:
            self.after_cancel(self._chart_redraw_job)
    except Exception:
        pass
    try:
        self._chart_redraw_job = self.after(delay, lambda: (_v42_refresh_wraps(self), _v42_redraw_charts(self)))
    except Exception:
        pass


def v42_set_ui_scale(self, value):
    try:
        pct = int(str(value).replace('%', ''))
        pct = max(25, min(500, pct))
        self.ui_scale_percent = pct
        ctk.set_widget_scaling(pct / 100)
    except Exception:
        pass
    _v42_schedule_redraw(self, delay=220)


def v42_set_theme_mode(self, value):
    mode = 'Light' if str(value) in ['白色', 'Light', 'light'] else 'Dark'
    try:
        ctk.set_appearance_mode(mode)
        self.theme_mode_value = mode
    except Exception:
        pass
    # 圖表維持白底，App 本體切換黑/白。
    try:
        if mode == 'Light':
            self.topbar.configure(fg_color='#eeeeee')
            self.main_pane.configure(bg='#eeeeee')
        else:
            self.topbar.configure(fg_color='#202020')
            self.main_pane.configure(bg='#1f1f1f')
    except Exception:
        pass
    _v42_schedule_redraw(self, delay=160)


def setup_left_panel_v42(self):
    self._v41_wrap_widgets = []

    def add_label(text, color='#ffffff', font=None, padx=20, pady=2, bold=False):
        if font is None:
            font = ctk.CTkFont(size=15, weight='bold' if bold else 'normal')
        lbl = ctk.CTkLabel(
            self.left_frame,
            text=_v42_safe_text(text),
            justify='left',
            anchor='w',
            text_color=color,
            font=font,
            wraplength=_v42_current_wrap_width(self),
        )
        lbl.pack(anchor='w', padx=padx, pady=pady, fill='x')
        self._v41_wrap_widgets.append(lbl)
        return lbl

    add_label('[ SYSTEM SPECS ]', color='#00ffff', font=ctk.CTkFont(size=17, weight='bold'), pady=(15, 2))
    add_label(f"CPU: {self.specs['cpu_name']}")
    freq = '5600' if self.specs.get('support_gen5') else '3200'
    add_label(f"RAM: {ram_label(self.specs['ram_total'])} (系統可用 {self.specs.get('ram_total',0)}G)（已用: {self.specs['ram_used']}G）[{self.specs['ram_type']} {freq}]")
    add_label(f"GPU: {self.specs['gpu_name']}\nVRAM: {self.specs['gpu_vram']} MB（已用: {self.specs['gpu_vram_used']} MB）")

    disk_lines = []
    for idx, d in enumerate(self.specs.get('disks', []), 1):
        size = d.get('size_gb', 0)
        model = d.get('model', f'磁碟 {idx}')
        disk_lines.append(f"Disk {idx}: {model} / {size} GB（已用: {d.get('used_gb', 0)}G）")
    if not disk_lines:
        disk_lines = [f"Disk: 總共 {self.specs.get('disk_total', 0)} GB（已用: {self.specs.get('disk_used', 0)}G）"]
    add_label('\n'.join(disk_lines), color='#cccccc')

    if not self.specs.get('is_laptop'):
        board_extra = self.specs.get('board_version', '')
        board_line = f"MOBO: {self.specs.get('mobo', '未知')}" + (f" / Ver {board_extra}" if board_extra else '')
        add_label(board_line, color='#aaaaaa')
        add_label(f"PSU: {self.specs.get('psu', '未知')}", color='#aaaaaa')
        fan_rows = self.specs.get('cooling_fans', [])
        fan_text = '散熱/風扇: ' + (' / '.join(fan_rows) if fan_rows else self.specs.get('cooler_note', '讀不到風扇感測器'))
        add_label(fan_text, color='#aaaaaa')
    mem_sticks = self.specs.get('memory_sticks', [])
    if mem_sticks:
        mem_text = 'RAM 模組：' + ' / '.join([f"{s.get('capacity_gb')}G {s.get('speed','')}" for s in mem_sticks if s.get('capacity_gb')])
        add_label(mem_text, color='#aaaaaa')

    add_label('[ BENCHMARK SCORES ]', color='#00ffff', font=ctk.CTkFont(size=17, weight='bold'), pady=(15, 2))
    add_label(f"CPU Score: {self.scores['CPU']:,} pts", padx=30, pady=1)
    add_label(f"RAM Score: {self.scores['RAM']:,} pts", padx=30, pady=1)
    add_label(f"GPU Score: {self.scores['GPU']:,} pts", padx=30, pady=1)
    add_label(f"AI Score:    {self.scores['AI_Score']:,} pts", color='#ff55ff', padx=30, pady=1)
    total_color = '#00ff00' if self.scores['Total'] > 80000 else '#ffaa00'
    add_label(f"TOTAL: {self.scores['Total']:,}", color=total_color, font=ctk.CTkFont(size=24, weight='bold'), pady=(10, 10))

    add_label(hardware_scene_analysis(self.specs, self.scores), color='#00ff99', pady=(0, 8))
    add_label(hardware_upgrade_suggestions(self.specs, self.scores), color='#ffee88', pady=(0, 10))
    add_label(_v41_extra_hardware_notes(self.specs, self.scores), color='#ffd966', pady=(0, 8))

    self._radar_values = [
        float(self.scores.get('game_score_100', 0)),
        float(self.scores.get('prod_score_100', 0)),
        float(self.scores.get('ai_score_100', 0)),
        float(self.scores.get('overall_score_100', 0)),
    ]
    self._radar_labels = ['遊戲', '生產力', 'AI', '綜合']

    self.radar_holder = ctk.CTkFrame(self.left_frame, fg_color='#242424', corner_radius=10)
    self.radar_holder.pack(fill='x', padx=16, pady=(4, 10))
    self.radar_holder.pack_propagate(False)
    self.radar_holder.bind('<Configure>', lambda e: _v42_schedule_redraw(self, delay=120), add='+')

    self.bottleneck_holder = ctk.CTkFrame(self.left_frame, fg_color='#242424', corner_radius=10)
    self.bottleneck_holder.pack(fill='x', padx=16, pady=(0, 18))
    self.bottleneck_holder.pack_propagate(False)
    self.bottleneck_holder.bind('<Configure>', lambda e: _v42_schedule_redraw(self, delay=120), add='+')

    _v42_update_chart_heights(self)
    self.after(260, lambda: _v42_redraw_charts(self))
    _v42_bind_wrap(self)


def show_startup_notice_v42(parent):
    """v42 只顯示當版更新內容，不再堆疊舊版資訊。"""
    win = ctk.CTkToplevel(parent)
    win.title('v42 版本公告')
    win.geometry('820x560')
    win.transient(parent)
    win.attributes('-topmost', True)

    frame = ctk.CTkFrame(win, corner_radius=14)
    frame.pack(fill='both', expand=True, padx=18, pady=18)

    ctk.CTkLabel(
        frame,
        text='電腦檢測升級工具 v42',
        text_color='#00ffff',
        font=ctk.CTkFont(size=24, weight='bold'),
    ).pack(anchor='w', padx=24, pady=(20, 12))

    box = ctk.CTkTextbox(frame, wrap='word', font=ctk.CTkFont(size=15), height=330)
    box.pack(fill='both', expand=True, padx=24, pady=(0, 14))
    box.insert('end', 'v42 更新重點\n')
    box.insert('end', '• 修復左側硬體分析在拖拉欄位或放大字體時，文字被裁切、不自動換行的問題。\n')
    box.insert('end', '• 圖表重新調整留白與字級，改善雷達圖 / 瓶頸圖文字被擋住的問題。\n')
    box.insert('end', '• 右上角新增「主題模式」，可在黑色 / 白色 App 外觀間切換。\n')
    box.insert('end', '• 版本公告改為只顯示當前版本修復與新增內容，不再混入舊版更新紀錄。\n\n')
    box.insert('end', '注意事項\n')
    box.insert('end', '• AI 市場與硬體價格波動大，有無貨或未上架價格不正確，仍以實際購買網站為準。\n')
    box.insert('end', '• 研發版本不代表最終品質。\n')
    box.configure(state='disabled')

    ctk.CTkButton(win, text='確認進入', command=win.destroy, width=280, height=44).pack(pady=(0, 24))
    win.grab_set()
    win.focus_force()


def v42_init(self):
    try:
        self.withdraw()
    except Exception:
        pass

    super(ROGApp, self).__init__()
    self.specs = get_specs()
    self.scores = calculate_score(self.specs)
    self.is_laptop = self.specs['is_laptop']
    self.cart_items = {}
    self.build_step = 0
    self.build_max_steps = 0
    self.build_context = {}
    self.current_mode = ''
    self.ai_history = []
    self.ai_request_times = []
    self.ai_recent_prompts = []
    self.ai_cooldown_until = 0
    self.ai_locked_until_close = False
    self.irrelevant_count = 0
    self.ui_scale_percent = 100
    self.theme_mode_value = 'Dark'
    self.cart_window = None

    device_type = '筆記型電腦' if self.is_laptop else '桌上型電腦'
    self.title(f'電腦檢測升級工具 v42 - [{device_type}]')
    self.geometry('1920x1040')
    self.minsize(1450, 850)
    self.resizable(True, True)

    self.topbar = ctk.CTkFrame(self, fg_color='#202020', height=42, corner_radius=0)
    self.topbar.pack(fill='x', side='top')
    ctk.CTkLabel(self.topbar, text='電腦硬體 AI 顧問 v42', text_color='#00ffff', font=ctk.CTkFont(size=15, weight='bold')).pack(side='left', padx=14)

    ctk.CTkLabel(self.topbar, text='主題', text_color='#cccccc').pack(side='right', padx=(8, 4))
    self.theme_menu = ctk.CTkOptionMenu(
        self.topbar,
        values=['黑色', '白色'],
        command=self.set_theme_mode,
        width=90,
    )
    self.theme_menu.set('黑色')
    self.theme_menu.pack(side='right', padx=8, pady=5)

    ctk.CTkLabel(self.topbar, text='字體/介面比例', text_color='#cccccc').pack(side='right', padx=(8, 4))
    self.scale_menu = ctk.CTkOptionMenu(
        self.topbar,
        values=['25%', '50%', '75%', '100%', '125%', '150%', '175%', '200%', '250%', '300%', '400%', '500%'],
        command=self.set_ui_scale,
        width=95,
    )
    self.scale_menu.set('100%')
    self.scale_menu.pack(side='right', padx=8, pady=5)

    self.main_pane = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashwidth=8, bd=0, bg='#1f1f1f', relief='flat')
    self.main_pane.pack(fill='both', expand=True, padx=8, pady=8)

    self.left_pane_holder = ctk.CTkFrame(self.main_pane, fg_color='transparent', corner_radius=0)
    self.ai_pane_holder = ctk.CTkFrame(self.main_pane, fg_color='transparent', corner_radius=0)
    self.work_pane_holder = ctk.CTkFrame(self.main_pane, fg_color='transparent', corner_radius=0)
    self.main_pane.add(self.left_pane_holder, minsize=420, width=620, stretch='first')
    self.main_pane.add(self.ai_pane_holder, minsize=420, width=560, stretch='always')
    self.main_pane.add(self.work_pane_holder, minsize=560, width=820, stretch='last')

    self.left_frame = ctk.CTkScrollableFrame(self.left_pane_holder, width=610, corner_radius=10)
    self.ai_frame = ctk.CTkFrame(self.ai_pane_holder, corner_radius=10)
    self.mid_frame = ctk.CTkScrollableFrame(self.work_pane_holder, width=810, corner_radius=10)
    self.left_frame.pack(fill='both', expand=True)
    self.ai_frame.pack(fill='both', expand=True)
    self.mid_frame.pack(fill='both', expand=True)

    self.setup_left_panel()
    self.setup_ai_panel_v38()
    _v37_original_setup_mid_panel(self)
    v41_post_setup_mid_panel(self)
    setup_cart_button_v38(self)

    self.bind_all('<MouseWheel>', self._on_mousewheel, add='+')
    self.bind_all('<Button-4>', self._on_mousewheel, add='+')
    self.bind_all('<Button-5>', self._on_mousewheel, add='+')

    try:
        self.deiconify()
        self.after(140, lambda: self.state('zoomed'))
    except Exception:
        pass
    try:
        self.after(320, lambda: show_startup_notice_v42(self))
    except Exception:
        pass


# 套用 v42：UI 換行、圖表裁切修復、主題切換、公告更新。
ROGApp.__init__ = v42_init
ROGApp.setup_left_panel = setup_left_panel_v42
ROGApp.set_ui_scale = v42_set_ui_scale
ROGApp.set_theme_mode = v42_set_theme_mode




# ============================================================
# v42.3：UI 換行修復 / 圖表裁切修復 / 關閉後 harmless TclError 抑制
# ============================================================
V421_VERSION = "v42.3"


def _v421_safe_text(text):
    """比 v42 更保守的換行處理：避免把「4. 綜合」拆成兩行，也避免長英文/分級列吃字。"""
    if text is None:
        return ""
    s = str(text)
    # 先整理多餘空白，但不要破壞硬體評價 1~4 行。
    s = s.replace(" ｜ ", " | ").replace(" | ", " ｜ ")
    s = s.replace("；", "；\n")
    s = s.replace("。", "。\n")

    # 評分方式：主動分段，避免 Time Spy / Steel Nomad / PassMark / Blender 擠成一長行。
    s = s.replace("GPU：Time Spy / Steel Nomad / PassMark G3D / Blender；", "GPU：Time Spy / Steel Nomad / PassMark G3D / Blender；\n")
    s = s.replace("CPU：Geekbench6 單核/多核 + Cinebench2024 + PassMark；", "CPU：Geekbench6 單核/多核 + Cinebench2024 + PassMark；\n")
    s = s.replace("綜合：遊戲/生產力/AI 加權；", "綜合：遊戲/生產力/AI 加權；\n")

    # 分級列分成多行，但不要在一般「4. 綜合」前硬插換行。
    s = s.replace("分級：SSS>115", "分級：\nSSS>115")
    s = s.replace(" | SS+101-114", " ｜ SS+101-114")
    s = s.replace(" | SS95-100", " ｜ SS95-100\n")
    s = s.replace(" | S+88", "S+88")
    s = s.replace(" | S82", " ｜ S82")
    s = s.replace(" | A++76", " ｜ A++76")
    s = s.replace(" | A+70", " ｜ A+70\n")
    s = s.replace(" | A64", "A64")
    s = s.replace(" | B++56", " ｜ B++56")
    s = s.replace(" | B+48", " ｜ B+48")
    s = s.replace(" | B40", " ｜ B40\n")
    s = s.replace(" | C30", "C30")
    s = s.replace(" | D20", " ｜ D20")
    s = s.replace(" | E10", " ｜ E10")
    s = s.replace(" | F<10", " ｜ F<10")

    # 對明顯很長的符號串補可斷點。
    s = s.replace(" / ", " / ")
    s = s.replace("+", "+")
    lines = [ln.rstrip() for ln in s.splitlines()]
    out = []
    for ln in lines:
        if ln or (out and out[-1]):
            out.append(ln)
    return "\n".join(out).strip()


# 覆蓋 v42 使用的名稱，setup_left_panel_v42 會動態吃到新版函式。
_v42_safe_text = _v421_safe_text


def _v42_current_wrap_width(self):
    """使用 CTkScrollableFrame 內部 canvas 實際寬度，修正拖拉面板後 wraplength 還抓舊寬度的問題。"""
    widths = []
    for obj in [getattr(self, 'left_pane_holder', None), getattr(self, 'left_frame', None)]:
        try:
            w = obj.winfo_width()
            if w and w > 80:
                widths.append(w)
        except Exception:
            pass
    try:
        canvas = getattr(self.left_frame, '_parent_canvas', None)
        if canvas:
            w = canvas.winfo_width()
            if w and w > 80:
                widths.append(w)
    except Exception:
        pass
    base = min(widths) if widths else 520
    scale = max(0.65, min(2.2, getattr(self, 'ui_scale_percent', 100) / 100.0))
    # 字體越大，左右安全距離越保守；避免被右側捲軸或 paned sash 吃掉。
    return max(120, int(base - 64 * scale))


def _v42_chart_font_bundle(scale_pct=100):
    # 讓圖表字體跟 UI 有感變動，但不要 500% 爆版。
    s = max(0.95, min(1.85, (float(scale_pct) / 100.0) ** 0.45))
    return {
        'title': max(17, int(17 * s)),
        'subtitle': max(13, int(13 * s)),
        'tick': max(11, int(10.5 * s)),
        'label': max(12, int(12 * s)),
        'value': max(12, int(12 * s)),
        'note': max(10, int(10 * s)),
    }


def _v42_chart_scale(scale_pct=100):
    return max(1.0, min(1.65, (float(scale_pct) / 100.0) ** 0.35))


def _v42_update_chart_heights(self):
    scale = _v42_chart_scale(getattr(self, 'ui_scale_percent', 100))
    # 增加高度，避免雷達圖底部 AI / 說明被裁切。
    radar_h = int(500 * scale)
    bottleneck_h = int(450 * scale)
    try:
        self.radar_holder.configure(height=radar_h)
        self.radar_holder.pack_propagate(False)
    except Exception:
        pass
    try:
        self.bottleneck_holder.configure(height=bottleneck_h)
        self.bottleneck_holder.pack_propagate(False)
    except Exception:
        pass


def _v421_is_alive(widget):
    try:
        return bool(widget and widget.winfo_exists())
    except Exception:
        return False


def _v42_render_radar_mpl(container, values, labels, scale_pct=100):
    if not _v421_is_alive(container):
        return
    if not MPL_AVAILABLE:
        _v41_render_chart_fallback(container, "硬體能力雷達圖", "matplotlib 尚未安裝，暫時無法顯示新版白底圖表。")
        return
    _v41_clear_children(container)
    if not _v421_is_alive(container):
        return
    fonts = _v42_chart_font_bundle(scale_pct)
    scale = _v42_chart_scale(scale_pct)
    width_px = max(560, int(container.winfo_width() or 660))
    height_px = max(int(480 * scale), int(container.winfo_height() or 500))

    fig = Figure(figsize=(width_px / 100, height_px / 100), dpi=100, facecolor='white')
    ax = fig.add_subplot(111, polar=True)
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')
    # 留出上下空間，避免「AI 71」與底部說明重疊。
    fig.subplots_adjust(left=0.20, right=0.80, top=0.78, bottom=0.24)

    vals = [max(0, min(100, float(v))) for v in values]
    n = len(labels)
    angles = [i / n * 2 * math.pi for i in range(n)]
    closed_angles = angles + angles[:1]
    closed_vals = vals + vals[:1]

    ax.set_theta_offset(math.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(['20', '40', '60', '80', '100'], fontsize=fonts['tick'], color='#64748b')
    ax.tick_params(axis='y', pad=6)

    xtick_labels = [f'{lab}\n{int(round(v))}' for lab, v in zip(labels, vals)]
    ax.set_xticks(angles)
    ax.set_xticklabels(xtick_labels, fontsize=fonts['label'], color='#111827', fontweight='bold')
    ax.tick_params(axis='x', pad=18)

    ax.grid(color='#d6dde8', linestyle='-', linewidth=0.95)
    ax.spines['polar'].set_color('#ccd5e1')
    ax.spines['polar'].set_linewidth(1.0)
    ax.plot(closed_angles, closed_vals, color='#008cff', linewidth=3.0)
    ax.fill(closed_angles, closed_vals, color='#9be7ff', alpha=0.72)
    ax.scatter(angles, vals, s=max(32, 42 * scale), color='#008cff', zorder=3)
    ax.set_title('硬體能力雷達圖', fontsize=fonts['title'], color='#111827', pad=30, fontweight='bold')
    fig.text(0.5, 0.075, '分數越接近外圈，代表該項能力越強', ha='center', fontsize=fonts['note'], color='#64748b')

    canvas = FigureCanvasTkAgg(fig, master=container)
    widget = canvas.get_tk_widget()
    widget.configure(bg='white', highlightthickness=0)
    widget.pack(fill='both', expand=True, padx=10, pady=10)
    canvas.draw_idle()
    container._mpl_canvas = canvas
    container._mpl_fig = fig


def _v42_render_bottleneck_mpl(container, specs, scores, scale_pct=100):
    if not _v421_is_alive(container):
        return
    if not MPL_AVAILABLE:
        _v41_render_chart_fallback(container, "硬體瓶頸分析圖", "matplotlib 尚未安裝，暫時無法顯示新版白底圖表。")
        return
    _v41_clear_children(container)
    if not _v421_is_alive(container):
        return
    fonts = _v42_chart_font_bundle(scale_pct)
    scale = _v42_chart_scale(scale_pct)
    width_px = max(590, int(container.winfo_width() or 700))
    height_px = max(int(430 * scale), int(container.winfo_height() or 450))

    result = _v41_bottleneck_result(specs, scores)
    items = result['scores']
    order = ['CPU', 'GPU', 'RAM', 'SSD']
    vals = [max(0, min(100, float(items.get(k, 0)))) for k in order]
    colors = {'CPU': '#4f8ef7', 'GPU': '#ff5c8a', 'RAM': '#14b8a6', 'SSD': '#f59e0b'}
    bottleneck = result['key']

    fig = Figure(figsize=(width_px / 100, height_px / 100), dpi=100, facecolor='white')
    fig.patch.set_facecolor('white')
    # 多留底部給 x 軸，不讓說明蓋住 40 / 60 / 80。
    fig.subplots_adjust(left=0.10, right=0.92, top=0.92, bottom=0.18)
    ax_text = fig.add_axes([0.045, 0.72, 0.91, 0.23])
    ax = fig.add_axes([0.10, 0.22, 0.80, 0.43])
    ax_text.axis('off')
    ax_text.text(0.0, 0.96, '硬體瓶頸分析圖', fontsize=fonts['title'], fontweight='bold', color='#111827', ha='left', va='top')
    ax_text.text(0.0, 0.60, result['headline'], fontsize=fonts['subtitle'] + 1, fontweight='bold', color='#111827', ha='left', va='top')
    ax_text.text(0.0, 0.22, result['detail'], fontsize=fonts['note'], color='#475569', ha='left', va='top', wrap=True)

    y = list(range(len(order)))
    ax.barh(y, [100] * len(order), color='#eef2f7', edgecolor='#d8dee9', height=0.58)
    bars = ax.barh(y, vals, color=[colors[k] for k in order], height=0.58)
    ax.set_xlim(0, 122)
    ax.set_yticks(y)
    ax.set_yticklabels(order, fontsize=fonts['label'], color='#111827', fontweight='bold')
    ax.set_xticks([0, 20, 40, 60, 80, 100])
    ax.set_xticklabels(['0', '20', '40', '60', '80', '100'], fontsize=fonts['tick'], color='#64748b')
    ax.tick_params(axis='x', pad=6)
    ax.grid(axis='x', color='#e2e8f0', linestyle='--', linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_facecolor('white')
    for spine in ['top', 'right', 'left', 'bottom']:
        ax.spines[spine].set_visible(False)
    ax.invert_yaxis()

    for idx, (bar, key, value) in enumerate(zip(bars, order, vals)):
        if key == bottleneck:
            bar.set_edgecolor('#111827')
            bar.set_linewidth(1.8)
        suffix = ' ← 主要瓶頸' if key == bottleneck else ''
        ax.text(min(value + 1.8, 116), idx, f'{value:.0f}{suffix}', va='center', ha='left', fontsize=fonts['value'], color='#111827', fontweight='bold' if key == bottleneck else 'normal')

    fig.text(0.5, 0.055, '判讀：哪一項明顯偏低，通常就是目前最拖累體感的地方。', ha='center', fontsize=fonts['note'], color='#64748b')
    canvas = FigureCanvasTkAgg(fig, master=container)
    widget = canvas.get_tk_widget()
    widget.configure(bg='white', highlightthickness=0)
    widget.pack(fill='both', expand=True, padx=10, pady=10)
    canvas.draw_idle()
    container._mpl_canvas = canvas
    container._mpl_fig = fig


def _v42_refresh_wraps(self):
    try:
        width = _v42_current_wrap_width(self)
        for widget in getattr(self, '_v41_wrap_widgets', []):
            try:
                widget.configure(wraplength=width)
            except Exception:
                pass
    except Exception:
        pass


def _v42_bind_wrap(self):
    def update(event=None):
        if getattr(self, '_closing', False):
            return
        _v42_refresh_wraps(self)
    targets = [getattr(self, 'left_frame', None), getattr(self, 'left_pane_holder', None), getattr(self, 'main_pane', None)]
    try:
        canvas = getattr(self.left_frame, '_parent_canvas', None)
        if canvas:
            targets.append(canvas)
    except Exception:
        pass
    for target in targets:
        try:
            target.bind('<Configure>', update, add='+')
        except Exception:
            pass
    try:
        self.after(200, update)
        self.after(800, update)
    except Exception:
        pass


def _v42_schedule_redraw(self, delay=180):
    if getattr(self, '_closing', False):
        return
    try:
        if hasattr(self, '_chart_redraw_job') and self._chart_redraw_job:
            self.after_cancel(self._chart_redraw_job)
    except Exception:
        pass
    def job():
        if getattr(self, '_closing', False):
            return
        if not _v421_is_alive(getattr(self, 'left_frame', None)):
            return
        _v42_refresh_wraps(self)
        _v42_redraw_charts(self)
    try:
        self._chart_redraw_job = self.after(delay, job)
    except Exception:
        pass


def v421_set_ui_scale(self, value):
    try:
        pct = int(str(value).replace('%', ''))
        pct = max(25, min(500, pct))
        self.ui_scale_percent = pct
        ctk.set_widget_scaling(pct / 100)
    except Exception:
        pass
    _v42_refresh_wraps(self)
    _v42_schedule_redraw(self, delay=240)


def v421_report_callback_exception(self, exc, val, tb):
    # 關閉視窗或圖表重繪後，Tk 偶爾會留下已銷毀 widget 的 focus after callback。
    # 這是 harmless callback，不影響功能，這裡避免在終端刷紅字。
    if exc is tk.TclError and 'invalid command name' in str(val):
        return
    try:
        import traceback
        traceback.print_exception(exc, val, tb)
    except Exception:
        pass


def v421_on_close(self):
    self._closing = True
    try:
        if hasattr(self, '_chart_redraw_job') and self._chart_redraw_job:
            self.after_cancel(self._chart_redraw_job)
    except Exception:
        pass
    try:
        self.destroy()
    except Exception:
        pass


def show_startup_notice_v421(parent):
    win = ctk.CTkToplevel(parent)
    win.title('v42.3 版本公告')
    win.geometry('820x520')
    win.transient(parent)
    win.attributes('-topmost', True)

    frame = ctk.CTkFrame(win, corner_radius=14)
    frame.pack(fill='both', expand=True, padx=18, pady=18)
    ctk.CTkLabel(
        frame,
        text='電腦檢測升級工具 v42.3',
        text_color='#00ffff',
        font=ctk.CTkFont(size=24, weight='bold'),
    ).pack(anchor='w', padx=24, pady=(20, 12))
    box = ctk.CTkTextbox(frame, wrap='word', font=ctk.CTkFont(size=15), height=300)
    box.pack(fill='both', expand=True, padx=24, pady=(0, 14))
    box.insert('end', 'v42.3 更新重點\n')
    box.insert('end', '• 修復關閉程式時偶發 invalid command name / focus callback 紅字。\n')
    box.insert('end', '• 修復左側硬體分析在拖拉欄位、縮小面板或放大字體時，部分文字被吃掉的問題。\n')
    box.insert('end', '• 修正硬體評價第 4 項「綜合」被拆成兩行的問題。\n')
    box.insert('end', '• 雷達圖與瓶頸圖重新調整上下留白，改善 AI 標籤、底部說明與刻度重疊。\n')
    box.insert('end', '• 圖表字體會跟右上角縮放同步調整，但最高會限制比例，避免 500% 時爆版。\n\n')
    box.insert('end', '注意事項\n')
    box.insert('end', '• AI 市場與硬體價格波動大，有無貨或未上架價格不正確，仍以實際購買網站為準。\n')
    box.insert('end', '• 研發版本不代表最終品質。\n')
    box.configure(state='disabled')
    ctk.CTkButton(win, text='確認進入', command=win.destroy, width=280, height=44).pack(pady=(0, 24))
    win.grab_set()
    try:
        win.focus_force()
    except Exception:
        pass


def v421_init(self):
    try:
        self.withdraw()
    except Exception:
        pass

    super(ROGApp, self).__init__()
    self.report_callback_exception = v421_report_callback_exception.__get__(self, self.__class__)
    self._closing = False
    self.specs = get_specs()
    self.scores = calculate_score(self.specs)
    self.is_laptop = self.specs['is_laptop']
    self.cart_items = {}
    self.build_step = 0
    self.build_max_steps = 0
    self.build_context = {}
    self.current_mode = ''
    self.ai_history = []
    self.ai_request_times = []
    self.ai_recent_prompts = []
    self.ai_cooldown_until = 0
    self.ai_locked_until_close = False
    self.irrelevant_count = 0
    self.ui_scale_percent = 100
    self.theme_mode_value = 'Dark'
    self.cart_window = None

    device_type = '筆記型電腦' if self.is_laptop else '桌上型電腦'
    self.title(f'電腦檢測升級工具 v42.3 - [{device_type}]')
    self.geometry('1920x1040')
    self.minsize(1450, 850)
    self.resizable(True, True)
    self.protocol('WM_DELETE_WINDOW', lambda: v421_on_close(self))

    self.topbar = ctk.CTkFrame(self, fg_color='#202020', height=42, corner_radius=0)
    self.topbar.pack(fill='x', side='top')
    ctk.CTkLabel(self.topbar, text='電腦硬體 AI 顧問 v42.3', text_color='#00ffff', font=ctk.CTkFont(size=15, weight='bold')).pack(side='left', padx=14)

    ctk.CTkLabel(self.topbar, text='主題', text_color='#cccccc').pack(side='right', padx=(8, 4))
    self.theme_menu = ctk.CTkOptionMenu(self.topbar, values=['黑色', '白色'], command=self.set_theme_mode, width=90)
    self.theme_menu.set('黑色')
    self.theme_menu.pack(side='right', padx=8, pady=5)

    ctk.CTkLabel(self.topbar, text='字體/介面比例', text_color='#cccccc').pack(side='right', padx=(8, 4))
    self.scale_menu = ctk.CTkOptionMenu(
        self.topbar,
        values=['25%', '50%', '75%', '100%', '125%', '150%', '175%', '200%', '250%', '300%', '400%', '500%'],
        command=self.set_ui_scale,
        width=95,
    )
    self.scale_menu.set('100%')
    self.scale_menu.pack(side='right', padx=8, pady=5)

    self.main_pane = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashwidth=8, bd=0, bg='#1f1f1f', relief='flat')
    self.main_pane.pack(fill='both', expand=True, padx=8, pady=8)

    self.left_pane_holder = ctk.CTkFrame(self.main_pane, fg_color='transparent', corner_radius=0)
    self.ai_pane_holder = ctk.CTkFrame(self.main_pane, fg_color='transparent', corner_radius=0)
    self.work_pane_holder = ctk.CTkFrame(self.main_pane, fg_color='transparent', corner_radius=0)
    # 左欄最低寬度略加大，避免硬體分析在預設縮放下太容易被裁切。
    self.main_pane.add(self.left_pane_holder, minsize=500, width=680, stretch='first')
    self.main_pane.add(self.ai_pane_holder, minsize=420, width=560, stretch='always')
    self.main_pane.add(self.work_pane_holder, minsize=560, width=820, stretch='last')

    self.left_frame = ctk.CTkScrollableFrame(self.left_pane_holder, width=660, corner_radius=10)
    self.ai_frame = ctk.CTkFrame(self.ai_pane_holder, corner_radius=10)
    self.mid_frame = ctk.CTkScrollableFrame(self.work_pane_holder, width=810, corner_radius=10)
    self.left_frame.pack(fill='both', expand=True)
    self.ai_frame.pack(fill='both', expand=True)
    self.mid_frame.pack(fill='both', expand=True)

    self.setup_left_panel()
    self.setup_ai_panel_v38()
    _v37_original_setup_mid_panel(self)
    v41_post_setup_mid_panel(self)
    setup_cart_button_v38(self)

    self.bind_all('<MouseWheel>', self._on_mousewheel, add='+')
    self.bind_all('<Button-4>', self._on_mousewheel, add='+')
    self.bind_all('<Button-5>', self._on_mousewheel, add='+')

    try:
        self.deiconify()
        self.after(140, lambda: self.state('zoomed') if not getattr(self, '_closing', False) else None)
    except Exception:
        pass
    try:
        self.after(340, lambda: show_startup_notice_v421(self) if not getattr(self, '_closing', False) else None)
    except Exception:
        pass


# 套用 v42.3
ROGApp.__init__ = v421_init
ROGApp.set_ui_scale = v421_set_ui_scale
ROGApp.setup_left_panel = setup_left_panel_v42
ROGApp.set_theme_mode = v42_set_theme_mode




# ============================================================
# v42.3：左側硬體分析改成自動高度文字區塊，解決縮放/拖拉時吃字
# ============================================================

def _v422_scale_ratio(self):
    # CTk 全域縮放可能到 500%，但左側報告字體不宜等比例爆大。
    return max(0.75, min(2.15, getattr(self, 'ui_scale_percent', 100) / 100.0))


def _v422_font_size(self, base):
    return max(9, int(round(base * _v422_scale_ratio(self))))


def _v422_left_content_width(self):
    widths = []
    for obj in [getattr(self, 'left_pane_holder', None), getattr(self, 'left_frame', None)]:
        try:
            w = obj.winfo_width()
            if w and w > 100:
                widths.append(w)
        except Exception:
            pass
    try:
        canvas = getattr(self.left_frame, '_parent_canvas', None)
        if canvas:
            w = canvas.winfo_width()
            if w and w > 100:
                widths.append(w)
    except Exception:
        pass
    base = min(widths) if widths else 660
    # 扣掉 padx、捲軸與 PanedWindow sash。用保守值，不然會看起來像被右邊吃掉。
    return max(170, int(base - 94 * _v422_scale_ratio(self)))


def _v422_char_width_units(s):
    # 粗略估計中英文寬度；用來決定每行最多塞幾個字。
    total = 0
    for ch in str(s):
        if '\u4e00' <= ch <= '\u9fff' or '\u3000' <= ch <= '\u303f' or '\uff00' <= ch <= '\uffef':
            total += 2
        else:
            total += 1
    return total


def _v422_wrap_line(line, max_units):
    line = str(line).rstrip()
    if not line:
        return ['']
    out, buf, units = [], '', 0
    for ch in line:
        u = 2 if ('\u4e00' <= ch <= '\u9fff' or '\u3000' <= ch <= '\u303f' or '\uff00' <= ch <= '\uffef') else 1
        if units + u > max_units and buf:
            out.append(buf.rstrip())
            buf, units = ch, u
        else:
            buf += ch
            units += u
    if buf:
        out.append(buf.rstrip())
    return out or ['']


def _v422_prepare_report_text(text):
    s = _v421_safe_text(text)
    # 加一些自然斷點，避免長型號/英文串或分級列黏成一大段。
    for token in [' / ', ' ｜ ', '；', '：', '，']:
        s = s.replace(token, token)
    # 修掉 RAM 顯示重複「系統可用」的情況。
    s = re.sub(r'\(系統可用 ([0-9.]+G)\)\s*\(系統可用 \1\)', r'(系統可用 \1)', s)
    return s


def _v422_reflow_report_blocks(self):
    width_px = _v422_left_content_width(self)
    for rec in getattr(self, '_v422_text_blocks', []):
        box = rec.get('widget')
        try:
            if not box or not box.winfo_exists():
                continue
        except Exception:
            continue
        base_size = rec.get('base_size', 15)
        font_size = _v422_font_size(self, base_size)
        max_units = max(10, int(width_px / max(7.2, font_size * 0.55)))
        raw = _v422_prepare_report_text(rec.get('raw', ''))
        wrapped_lines = []
        for raw_line in raw.splitlines():
            # 標題和短行保留，不要過度拆。
            if _v422_char_width_units(raw_line) <= max_units:
                wrapped_lines.append(raw_line)
            else:
                wrapped_lines.extend(_v422_wrap_line(raw_line, max_units))
        wrapped = '\n'.join(wrapped_lines).strip()
        line_count = max(1, wrapped.count('\n') + 1)
        line_px = max(17, int(font_size * 1.42))
        height = max(28, line_count * line_px + int(10 * _v422_scale_ratio(self)))
        try:
            box.configure(state='normal')
            box.delete('1.0', 'end')
            box.configure(font=ctk.CTkFont(size=font_size, weight=rec.get('weight', 'normal')))
            box.insert('end', wrapped)
            box.configure(width=width_px, height=height)
            box.configure(state='disabled')
        except Exception:
            pass


def _v422_make_report_block(self, text, color='#ffffff', base_size=15, weight='normal', padx=20, pady=2):
    fg = '#2b2b2b' if getattr(self, 'theme_mode_value', 'Dark') == 'Dark' else '#f2f2f2'
    box = ctk.CTkTextbox(
        self.left_frame,
        wrap='char',
        activate_scrollbars=False,
        border_width=0,
        fg_color=fg,
        text_color=color,
        corner_radius=0,
        height=30,
        font=ctk.CTkFont(size=base_size, weight=weight),
    )
    box.pack(anchor='w', padx=padx, pady=pady, fill='x')
    box.configure(state='disabled')
    rec = {'widget': box, 'raw': text, 'color': color, 'base_size': base_size, 'weight': weight, 'padx': padx}
    self._v422_text_blocks.append(rec)
    return box


def _v422_bind_reflow(self):
    def schedule(event=None):
        try:
            if hasattr(self, '_v422_reflow_job') and self._v422_reflow_job:
                self.after_cancel(self._v422_reflow_job)
        except Exception:
            pass
        try:
            self._v422_reflow_job = self.after(90, lambda: (_v422_reflow_report_blocks(self), _v42_schedule_redraw(self, delay=120)))
        except Exception:
            pass
    try:
        self.left_pane_holder.bind('<Configure>', schedule, add='+')
        self.left_frame.bind('<Configure>', schedule, add='+')
        canvas = getattr(self.left_frame, '_parent_canvas', None)
        if canvas:
            canvas.bind('<Configure>', schedule, add='+')
    except Exception:
        pass
    self.after(160, lambda: _v422_reflow_report_blocks(self))


def setup_left_panel_v422(self):
    self._v422_text_blocks = []

    def add(text, color='#ffffff', size=15, weight='normal', padx=20, pady=2):
        return _v422_make_report_block(self, text, color=color, base_size=size, weight=weight, padx=padx, pady=pady)

    add('[ SYSTEM SPECS ]', color='#00ffff', size=17, weight='bold', pady=(15, 2))
    add(f"CPU: {self.specs['cpu_name']}")
    freq = '5600' if self.specs.get('support_gen5') else '3200'
    add(f"RAM: {ram_label(self.specs['ram_total'])}（已用: {self.specs['ram_used']}G）[{self.specs['ram_type']} {freq}]")
    add(f"GPU: {self.specs['gpu_name']}\nVRAM: {self.specs['gpu_vram']} MB（已用: {self.specs['gpu_vram_used']} MB）")

    disk_lines = []
    for idx, d in enumerate(self.specs.get('disks', []), 1):
        size = d.get('size_gb', 0)
        model = d.get('model', f'磁碟 {idx}')
        disk_lines.append(f"Disk {idx}: {model} / {size} GB（已用: {d.get('used_gb', 0)}G）")
    if not disk_lines:
        disk_lines = [f"Disk: 總共 {self.specs.get('disk_total', 0)} GB（已用: {self.specs.get('disk_used', 0)}G）"]
    add('\n'.join(disk_lines), color='#cccccc')

    if not self.specs.get('is_laptop'):
        board_extra = self.specs.get('board_version', '')
        board_line = f"MOBO: {self.specs.get('mobo', '未知')}" + (f" / Ver {board_extra}" if board_extra else '')
        add(board_line, color='#aaaaaa')
        add(f"PSU: {self.specs.get('psu', '未知')}", color='#aaaaaa')
        fan_rows = self.specs.get('cooling_fans', [])
        fan_text = '散熱/風扇: ' + (' / '.join(fan_rows) if fan_rows else self.specs.get('cooler_note', '讀不到風扇感測器'))
        add(fan_text, color='#aaaaaa')
    mem_sticks = self.specs.get('memory_sticks', [])
    if mem_sticks:
        mem_text = 'RAM 模組：' + ' / '.join([f"{s.get('capacity_gb')}G {s.get('speed','')}" for s in mem_sticks if s.get('capacity_gb')])
        add(mem_text, color='#aaaaaa')

    add('[ BENCHMARK SCORES ]', color='#00ffff', size=17, weight='bold', pady=(15, 2))
    add(f"CPU Score: {self.scores['CPU']:,} pts", padx=30)
    add(f"RAM Score: {self.scores['RAM']:,} pts", padx=30)
    add(f"GPU Score: {self.scores['GPU']:,} pts", padx=30)
    add(f"AI Score:    {self.scores['AI_Score']:,} pts", color='#ff55ff', padx=30)
    total_color = '#00ff00' if self.scores['Total'] > 80000 else '#ffaa00'
    add(f"TOTAL: {self.scores['Total']:,}", color=total_color, size=24, weight='bold', pady=(10, 10))

    add(hardware_scene_analysis(self.specs, self.scores), color='#00ff99', pady=(0, 8))
    add(hardware_upgrade_suggestions(self.specs, self.scores), color='#ffee88', pady=(0, 10))
    add(_v41_extra_hardware_notes(self.specs, self.scores), color='#ffd966', pady=(0, 8))

    self._radar_values = [
        float(self.scores.get('game_score_100', 0)),
        float(self.scores.get('prod_score_100', 0)),
        float(self.scores.get('ai_score_100', 0)),
        float(self.scores.get('overall_score_100', 0)),
    ]
    self._radar_labels = ['遊戲', '生產力', 'AI', '綜合']

    self.radar_holder = ctk.CTkFrame(self.left_frame, fg_color='#242424', corner_radius=10)
    self.radar_holder.pack(fill='x', padx=16, pady=(4, 10))
    self.radar_holder.pack_propagate(False)
    self.radar_holder.bind('<Configure>', lambda e: _v42_schedule_redraw(self, delay=120), add='+')

    self.bottleneck_holder = ctk.CTkFrame(self.left_frame, fg_color='#242424', corner_radius=10)
    self.bottleneck_holder.pack(fill='x', padx=16, pady=(0, 18))
    self.bottleneck_holder.pack_propagate(False)
    self.bottleneck_holder.bind('<Configure>', lambda e: _v42_schedule_redraw(self, delay=120), add='+')

    _v42_update_chart_heights(self)
    _v422_bind_reflow(self)
    self.after(220, lambda: (_v422_reflow_report_blocks(self), _v42_redraw_charts(self)))


def v422_set_ui_scale(self, value):
    try:
        v33_set_ui_scale(self, value)
    finally:
        try:
            _v422_reflow_report_blocks(self)
        except Exception:
            pass
        _v42_schedule_redraw(self, delay=220)


def v422_set_theme_mode(self, value):
    try:
        v42_set_theme_mode(self, value)
    finally:
        # 主題切換後重建左側文字底色，避免 Textbox 仍停在舊底色。
        try:
            for child in self.left_frame.winfo_children():
                child.destroy()
            self.setup_left_panel()
        except Exception:
            pass
        _v42_schedule_redraw(self, delay=180)


def show_startup_notice_v422(parent):
    win = ctk.CTkToplevel(parent)
    win.title('v42.3 版本公告')
    win.geometry('820x500')
    win.transient(parent)
    win.attributes('-topmost', True)
    frame = ctk.CTkFrame(win, corner_radius=14)
    frame.pack(fill='both', expand=True, padx=18, pady=18)
    ctk.CTkLabel(frame, text='電腦檢測升級工具 v42.3', text_color='#00ffff', font=ctk.CTkFont(size=24, weight='bold')).pack(anchor='w', padx=24, pady=(20, 12))
    box = ctk.CTkTextbox(frame, wrap='word', font=ctk.CTkFont(size=15), height=280)
    box.pack(fill='both', expand=True, padx=24, pady=(0, 14))
    box.insert('end', 'v42.3 更新重點\n')
    box.insert('end', '• 左側硬體分析改用自動高度文字區塊，縮小欄位與放大字體時不再直接吃字。\n')
    box.insert('end', '• 長型號、評分方式、分級列與升級建議會依面板寬度重新斷行。\n')
    box.insert('end', '• 右上角縮放後會同步重排文字與圖表。\n')
    box.insert('end', '• 主題切換後會重建左側文字底色，避免黑白模式殘留。\n\n')
    box.insert('end', '注意事項\n')
    box.insert('end', '• AI 市場與硬體價格波動大，有無貨或未上架價格不正確，仍以實際購買網站為準。\n')
    box.insert('end', '• 研發版本不代表最終品質。\n')
    box.configure(state='disabled')
    ctk.CTkButton(win, text='確認進入', command=win.destroy, width=280, height=44).pack(pady=(0, 24))
    win.grab_set()
    try:
        win.focus_force()
    except Exception:
        pass


def v422_init(self):
    v421_init(self)
    # v421_init 已排程舊公告，這裡不再取消，改用新公告覆蓋會太吵；因此只更新標題/版本。
    try:
        self.title(self.title().replace('v42.3', 'v42.3'))
    except Exception:
        pass


# 套用 v42.3
ROGApp.setup_left_panel = setup_left_panel_v422
ROGApp.set_ui_scale = v422_set_ui_scale
ROGApp.set_theme_mode = v422_set_theme_mode
# 讓 v421_init 內排程的公告函式名稱仍能呼叫，但內容改為 v42.3。
show_startup_notice_v421 = show_startup_notice_v422



# ============================================================
# v42.3：左側報告 UI 美化 / 白色模式可讀性 / 去除一塊一塊底色
# ============================================================
V423_VERSION = "v42.3"


def _v423_color_tuple(original):
    """讓同一段文字在白色/黑色模式都有足夠對比。tuple = (Light, Dark)。"""
    key = (original or '').lower()
    mapping = {
        '#00ffff': ('#006d78', '#00ffff'),
        '#00ff99': ('#007a55', '#00ff99'),
        '#ffee88': ('#6f5700', '#ffee88'),
        '#ffd966': ('#705500', '#ffd966'),
        '#ff55ff': ('#9b1a9b', '#ff55ff'),
        '#00ff00': ('#168a16', '#00ff00'),
        '#aaaaaa': ('#4a5563', '#aaaaaa'),
        '#cccccc': ('#374151', '#cccccc'),
        '#ffffff': ('#111827', '#ffffff'),
        '#ffaa00': ('#9a5a00', '#ffaa00'),
    }
    return mapping.get(key, ('#111827', original or '#ffffff'))


def _v423_bg_tuple():
    # 和 CTkScrollableFrame 預設底色接近，避免每個文字區塊像一張卡片。
    return ('#e5e5e5', '#2b2b2b')


def _v423_panel_bg_tuple():
    return ('#e5e5e5', '#2b2b2b')


def _v423_left_content_width(self):
    widths = []
    for obj in [getattr(self, 'left_pane_holder', None), getattr(self, 'left_frame', None), getattr(getattr(self, 'left_frame', None), '_parent_canvas', None)]:
        try:
            w = obj.winfo_width()
            if w and w > 120:
                widths.append(w)
        except Exception:
            pass
    base = min(widths) if widths else 620
    # Label 只需要 wraplength，不要硬塞 widget width；扣掉左右 padding、scrollbar、保守安全距。
    return max(170, int(base - 64))


def _v423_font_size(self, base_size):
    # 文字可以跟縮放走，但限制最大值，避免 300%/500% 時整個版面爆掉。
    pct = getattr(self, 'ui_scale_percent', 100)
    visual = max(0.75, min(2.15, pct / 100.0))
    return max(9, int(base_size * visual))


def _v423_prepare_report_text(text):
    s = _v421_safe_text(text)
    s = re.sub(r'\(系統可用 ([0-9.]+G)\)\s*\(系統可用 \1\)', r'(系統可用 \1)', s)
    # 長分級列增加自然換行點，避免整串被擠到右側消失。
    s = s.replace('SSS≥115 | SS+101-114 | SS95-100 | S+88 | S82 | A++76 | A+70 | A64 | B++56 | B+48 | B40 | C30 | D20 | E10 | F<10',
                  'SSS≥115 | SS+101-114 | SS95-100 | S+88 | S82\nA++76 | A+70 | A64 | B++56 | B+48 | B40\nC30 | D20 | E10 | F<10')
    s = s.replace('GPU : Time Spy / Steel Nomad / PassMark G3D / Blender；RTX 5090',
                  'GPU : Time Spy / Steel Nomad / PassMark G3D / Blender\nRTX 5090')
    s = s.replace('CPU : Geekbench6 單核/多核 + Cinebench2024 + PassMark；',
                  'CPU : Geekbench6 單核/多核 + Cinebench2024 + PassMark\n')
    return s


def _v423_make_report_block(self, text, color='#ffffff', base_size=15, weight='normal', padx=20, pady=2):
    lbl = ctk.CTkLabel(
        self.left_frame,
        text=_v423_prepare_report_text(text),
        justify='left',
        anchor='w',
        text_color=_v423_color_tuple(color),
        fg_color='transparent',
        corner_radius=0,
        font=ctk.CTkFont(size=_v423_font_size(self, base_size), weight=weight),
        wraplength=_v423_left_content_width(self),
    )
    lbl.pack(anchor='w', padx=padx, pady=pady, fill='x')
    rec = {'widget': lbl, 'raw': text, 'color': color, 'base_size': base_size, 'weight': weight, 'padx': padx}
    self._v422_text_blocks.append(rec)
    return lbl


def _v423_reflow_report_blocks(self):
    wrap_width = _v423_left_content_width(self)
    for rec in getattr(self, '_v422_text_blocks', []):
        widget = rec.get('widget')
        try:
            if not widget or not widget.winfo_exists():
                continue
            widget.configure(
                text=_v423_prepare_report_text(rec.get('raw', '')),
                wraplength=wrap_width,
                text_color=_v423_color_tuple(rec.get('color', '#ffffff')),
                fg_color='transparent',
                font=ctk.CTkFont(size=_v423_font_size(self, rec.get('base_size', 15)), weight=rec.get('weight', 'normal')),
            )
        except Exception:
            pass


def _v42_refresh_wraps(self):
    # 覆蓋舊版 refresh：現在左側改用 Label，直接重算 wraplength 與顏色即可。
    try:
        _v423_reflow_report_blocks(self)
    except Exception:
        pass


def setup_left_panel_v423(self):
    self._v422_text_blocks = []
    try:
        self.left_frame.configure(fg_color=_v423_panel_bg_tuple())
        self.left_pane_holder.configure(fg_color='transparent')
    except Exception:
        pass

    def add(text, color='#ffffff', size=15, weight='normal', padx=20, pady=2):
        return _v423_make_report_block(self, text, color=color, base_size=size, weight=weight, padx=padx, pady=pady)

    add('[ SYSTEM SPECS ]', color='#00ffff', size=17, weight='bold', pady=(15, 2))
    add(f"CPU: {self.specs['cpu_name']}")
    freq = '5600' if self.specs.get('support_gen5') else '3200'
    add(f"RAM: {ram_label(self.specs['ram_total'])}（已用: {self.specs['ram_used']}G）[{self.specs['ram_type']} {freq}]")
    add(f"GPU: {self.specs['gpu_name']}\nVRAM: {self.specs['gpu_vram']} MB（已用: {self.specs['gpu_vram_used']} MB）")

    disk_lines = []
    for idx, d in enumerate(self.specs.get('disks', []), 1):
        size = d.get('size_gb', 0)
        model = d.get('model', f'磁碟 {idx}')
        disk_lines.append(f"Disk {idx}: {model} / {size} GB（已用: {d.get('used_gb', 0)}G）")
    if not disk_lines:
        disk_lines = [f"Disk: 總共 {self.specs.get('disk_total', 0)} GB（已用: {self.specs.get('disk_used', 0)}G）"]
    add('\n'.join(disk_lines), color='#cccccc')

    if not self.specs.get('is_laptop'):
        board_extra = self.specs.get('board_version', '')
        board_line = f"MOBO: {self.specs.get('mobo', '未知')}" + (f" / Ver {board_extra}" if board_extra else '')
        add(board_line, color='#aaaaaa')
        add(f"PSU: {self.specs.get('psu', '未知')}", color='#aaaaaa')
        fan_rows = self.specs.get('cooling_fans', [])
        fan_text = '散熱/風扇: ' + (' / '.join(fan_rows) if fan_rows else self.specs.get('cooler_note', '讀不到風扇感測器'))
        add(fan_text, color='#aaaaaa')
    mem_sticks = self.specs.get('memory_sticks', [])
    if mem_sticks:
        mem_text = 'RAM 模組：' + ' / '.join([f"{s.get('capacity_gb')}G {s.get('speed','')}" for s in mem_sticks if s.get('capacity_gb')])
        add(mem_text, color='#aaaaaa')

    add('[ BENCHMARK SCORES ]', color='#00ffff', size=17, weight='bold', pady=(15, 2))
    add(f"CPU Score: {self.scores['CPU']:,} pts", padx=30)
    add(f"RAM Score: {self.scores['RAM']:,} pts", padx=30)
    add(f"GPU Score: {self.scores['GPU']:,} pts", padx=30)
    add(f"AI Score:    {self.scores['AI_Score']:,} pts", color='#ff55ff', padx=30)
    total_color = '#00ff00' if self.scores['Total'] > 80000 else '#ffaa00'
    add(f"TOTAL: {self.scores['Total']:,}", color=total_color, size=24, weight='bold', pady=(10, 10))

    add(hardware_scene_analysis(self.specs, self.scores), color='#00ff99', pady=(0, 8))
    add(hardware_upgrade_suggestions(self.specs, self.scores), color='#ffee88', pady=(0, 10))
    add(_v41_extra_hardware_notes(self.specs, self.scores), color='#ffd966', pady=(0, 8))

    self._radar_values = [
        float(self.scores.get('game_score_100', 0)),
        float(self.scores.get('prod_score_100', 0)),
        float(self.scores.get('ai_score_100', 0)),
        float(self.scores.get('overall_score_100', 0)),
    ]
    self._radar_labels = ['遊戲', '生產力', 'AI', '綜合']

    self.radar_holder = ctk.CTkFrame(self.left_frame, fg_color='transparent', corner_radius=0)
    self.radar_holder.pack(fill='x', padx=14, pady=(8, 12))
    self.radar_holder.pack_propagate(False)
    self.radar_holder.bind('<Configure>', lambda e: _v42_schedule_redraw(self, delay=120), add='+')

    self.bottleneck_holder = ctk.CTkFrame(self.left_frame, fg_color='transparent', corner_radius=0)
    self.bottleneck_holder.pack(fill='x', padx=14, pady=(0, 18))
    self.bottleneck_holder.pack_propagate(False)
    self.bottleneck_holder.bind('<Configure>', lambda e: _v42_schedule_redraw(self, delay=120), add='+')

    _v42_update_chart_heights(self)
    _v422_bind_reflow(self)
    self.after(220, lambda: (_v423_reflow_report_blocks(self), _v42_redraw_charts(self)))


def v423_set_ui_scale(self, value):
    try:
        v42_set_ui_scale(self, value)
    finally:
        try:
            _v423_reflow_report_blocks(self)
        except Exception:
            pass
        _v42_schedule_redraw(self, delay=220)


def v423_set_theme_mode(self, value):
    mode = 'Light' if str(value) in ['白色', 'Light', 'light'] else 'Dark'
    try:
        ctk.set_appearance_mode(mode)
        self.theme_mode_value = mode
        if mode == 'Light':
            self.configure(fg_color='#e5e5e5')
            self.topbar.configure(fg_color='#f0f0f0')
            self.main_pane.configure(bg='#e5e5e5')
        else:
            self.configure(fg_color='#242424')
            self.topbar.configure(fg_color='#202020')
            self.main_pane.configure(bg='#1f1f1f')
    except Exception:
        pass
    try:
        for child in self.left_frame.winfo_children():
            child.destroy()
        self.setup_left_panel()
    except Exception:
        pass
    _v42_schedule_redraw(self, delay=200)


def show_startup_notice_v423(parent):
    win = ctk.CTkToplevel(parent)
    win.title('v42.3 版本公告')
    win.geometry('820x500')
    win.transient(parent)
    win.attributes('-topmost', True)
    frame = ctk.CTkFrame(win, corner_radius=14)
    frame.pack(fill='both', expand=True, padx=18, pady=18)
    ctk.CTkLabel(frame, text='電腦檢測升級工具 v42.3', text_color='#00ffff', font=ctk.CTkFont(size=24, weight='bold')).pack(anchor='w', padx=24, pady=(20, 12))
    box = ctk.CTkTextbox(frame, wrap='word', font=ctk.CTkFont(size=15), height=280)
    box.pack(fill='both', expand=True, padx=24, pady=(0, 14))
    box.insert('end', 'v42.3 更新重點\n')
    box.insert('end', '• 左側硬體分析改用透明 Label 排版，不再出現一塊一塊的灰色文字底。\n')
    box.insert('end', '• 修復白色模式下文字太淡、難以辨識的問題。\n')
    box.insert('end', '• 縮放與拖拉左欄時，硬體規格、評分方式與升級建議會重新換行。\n')
    box.insert('end', '• 圖表區改成透明外框，和背景更一致。\n\n')
    box.insert('end', '注意事項\n')
    box.insert('end', '• AI 市場與硬體價格波動大，有無貨或未上架價格不正確，仍以實際購買網站為準。\n')
    box.insert('end', '• 研發版本不代表最終品質。\n')
    box.configure(state='disabled')
    ctk.CTkButton(win, text='確認進入', command=win.destroy, width=280, height=44).pack(pady=(0, 24))
    win.grab_set()
    try:
        win.focus_force()
    except Exception:
        pass


# 套用 v42.3
ROGApp.setup_left_panel = setup_left_panel_v423
ROGApp.set_ui_scale = v423_set_ui_scale
ROGApp.set_theme_mode = v423_set_theme_mode
show_startup_notice_v421 = show_startup_notice_v423
show_startup_notice_v422 = show_startup_notice_v423


# ============================================================
# v42.4：左側文字最終換行修復 / Message 自適應寬度 / 乾淨背景
# ============================================================
V424_VERSION = "v42.4"


def _v424_appearance_is_light(self=None):
    try:
        mode = getattr(self, 'theme_mode_value', None) or ctk.get_appearance_mode()
        return str(mode).lower().startswith('light')
    except Exception:
        return False


def _v424_actual_color(self, color):
    if isinstance(color, tuple):
        return color[0] if _v424_appearance_is_light(self) else color[1]
    if color in ['transparent', None]:
        return _v424_panel_bg(self)
    return color


def _v424_panel_bg(self=None):
    return '#e5e5e5' if _v424_appearance_is_light(self) else '#2b2b2b'


def _v424_font(base_size=15, weight='normal', self=None):
    pct = getattr(self, 'ui_scale_percent', 100) if self is not None else 100
    # 自訂 tk.Message 不吃 CTk scaling，所以這裡自己算；上限避免 500% 直接爆版。
    factor = max(0.80, min(2.20, pct / 100.0))
    size = max(9, int(base_size * factor))
    return ('Microsoft JhengHei UI', size, weight)


def _v424_left_content_width(self):
    widths = []
    for obj in [getattr(self, 'left_pane_holder', None), getattr(self, 'left_frame', None), getattr(getattr(self, 'left_frame', None), '_parent_canvas', None)]:
        try:
            w = obj.winfo_width()
            if w and w > 160:
                widths.append(w)
        except Exception:
            pass
    base = min(widths) if widths else 640
    # 扣掉左右 padding、scrollbar、PanedWindow 邊界，給 Message 真正可用寬度。
    return max(180, int(base - 92))


def _v424_soft_break_text(text):
    s = _v421_safe_text(text)
    s = re.sub(r'\(系統可用 ([0-9.]+G)\)\s*\(系統可用 \1\)', r'(系統可用 \1)', s)
    # 加一些換行機會，避免英文 benchmark / 分級列整串吃到右側。
    s = s.replace(' / ', ' /\n')
    s = s.replace(' | ', ' |\n')
    s = s.replace('；', '；\n')
    s = s.replace('，', '，')
    # 避免過度空行。
    s = re.sub(r'\n{3,}', '\n\n', s)
    return s.strip()


def _v424_make_message(self, text, color='#ffffff', base_size=15, weight='normal', padx=20, pady=2, bg=None):
    bg = bg or _v424_panel_bg(self)
    fg = _v424_actual_color(self, _v423_color_tuple(color) if isinstance(color, str) else color)
    msg = tk.Message(
        self.left_frame,
        text=_v424_soft_break_text(text),
        width=_v424_left_content_width(self),
        anchor='w',
        justify='left',
        bg=bg,
        fg=fg,
        font=_v424_font(base_size, weight, self),
        borderwidth=0,
        highlightthickness=0,
        padx=0,
        pady=0,
    )
    msg.pack(anchor='w', fill='x', padx=padx, pady=pady)
    if not hasattr(self, '_v424_message_widgets'):
        self._v424_message_widgets = []
    self._v424_message_widgets.append((msg, text, color, base_size, weight))
    return msg


def _v424_reflow_messages(self):
    try:
        width = _v424_left_content_width(self)
        bg = _v424_panel_bg(self)
        for item in getattr(self, '_v424_message_widgets', []):
            msg, text, color, base_size, weight = item
            if not msg.winfo_exists():
                continue
            fg = _v424_actual_color(self, _v423_color_tuple(color) if isinstance(color, str) else color)
            msg.configure(
                width=width,
                bg=bg,
                fg=fg,
                font=_v424_font(base_size, weight, self),
                text=_v424_soft_break_text(text),
            )
        try:
            self.left_frame.configure(fg_color=bg)
            canvas = getattr(self.left_frame, '_parent_canvas', None)
            if canvas is not None:
                canvas.configure(bg=bg, highlightthickness=0)
        except Exception:
            pass
    except Exception:
        pass


def _v424_bind_reflow(self):
    def schedule(event=None):
        try:
            if hasattr(self, '_v424_reflow_job') and self._v424_reflow_job:
                self.after_cancel(self._v424_reflow_job)
        except Exception:
            pass
        try:
            self._v424_reflow_job = self.after(80, lambda: (_v424_reflow_messages(self), _v42_schedule_redraw(self, delay=120)))
        except Exception:
            pass
    for target in [getattr(self, 'left_frame', None), getattr(self, 'left_pane_holder', None), getattr(self, 'main_pane', None)]:
        try:
            target.bind('<Configure>', schedule, add='+')
        except Exception:
            pass
    try:
        canvas = getattr(self.left_frame, '_parent_canvas', None)
        if canvas is not None:
            canvas.bind('<Configure>', schedule, add='+')
    except Exception:
        pass
    self.after(160, lambda: _v424_reflow_messages(self))


def setup_left_panel_v424(self):
    self._v424_message_widgets = []
    bg = _v424_panel_bg(self)
    try:
        self.left_frame.configure(fg_color=bg)
        canvas = getattr(self.left_frame, '_parent_canvas', None)
        if canvas is not None:
            canvas.configure(bg=bg, highlightthickness=0)
    except Exception:
        pass

    def add(text, color='#ffffff', base=15, weight='normal', padx=20, pady=2):
        return _v424_make_message(self, text, color=color, base_size=base, weight=weight, padx=padx, pady=pady, bg=bg)

    add('[ SYSTEM SPECS ]', '#00ffff', 18, 'bold', pady=(15, 8))
    add(f"CPU: {self.specs['cpu_name']}")
    freq = '5600' if self.specs.get('support_gen5') else '3200'
    add(f"RAM: {ram_label(self.specs['ram_total'])}（已用: {self.specs['ram_used']}G）[{self.specs['ram_type']} {freq}]")
    add(f"GPU: {self.specs['gpu_name']}\nVRAM: {self.specs['gpu_vram']} MB（已用: {self.specs['gpu_vram_used']} MB）")

    disk_lines = []
    for idx, d in enumerate(self.specs.get('disks', []), 1):
        size = d.get('size_gb', 0)
        model = d.get('model', f'Disk {idx}')
        disk_lines.append(f"Disk {idx}: {model} / {size} GB（已用: {d.get('used_gb', 0)}G）")
    if not disk_lines:
        disk_lines.append(f"Disk: 總共 {self.specs['disk_total']} GB（已用: {self.specs['disk_used']}G）")
    add('\n'.join(disk_lines), '#cccccc')

    if not self.specs.get('is_laptop'):
        board_extra = self.specs.get('board_version', '')
        board_line = f"MOBO: {self.specs.get('mobo', '未知')}" + (f" / Ver {board_extra}" if board_extra else '')
        add(board_line, '#aaaaaa')
        add(f"PSU: {self.specs.get('psu', '未知')}", '#aaaaaa')
        fan_rows = self.specs.get('cooling_fans', [])
        fan_text = '散熱/風扇: ' + (' / '.join(fan_rows) if fan_rows else self.specs.get('cooler_note', '讀不到風扇感測器'))
        add(fan_text, '#aaaaaa')

    mem_sticks = self.specs.get('memory_sticks', [])
    if mem_sticks:
        mem_text = 'RAM 模組：' + ' / '.join([f"{s.get('capacity_gb')}G {s.get('speed','')}" for s in mem_sticks if s.get('capacity_gb')])
        add(mem_text, '#aaaaaa')

    add('[ BENCHMARK SCORES ]', '#00ffff', 18, 'bold', pady=(18, 8))
    add(f"CPU Score: {self.scores['CPU']:,} pts", '#ffffff', padx=30, pady=3)
    add(f"RAM Score: {self.scores['RAM']:,} pts", '#ffffff', padx=30, pady=3)
    add(f"GPU Score: {self.scores['GPU']:,} pts", '#ffffff', padx=30, pady=3)
    add(f"AI Score: {self.scores['AI_Score']:,} pts", '#ff55ff', padx=30, pady=3)
    total_color = '#00ff00' if self.scores['Total'] > 80000 else '#ffaa00'
    add(f"TOTAL: {self.scores['Total']:,}", total_color, 24, 'bold', pady=(12, 10))

    add(hardware_scene_analysis(self.specs, self.scores), '#00ff99', base=15, pady=(0, 10))
    add(hardware_upgrade_suggestions(self.specs, self.scores), '#ffee88', base=15, pady=(0, 10))
    add(_v41_extra_hardware_notes(self.specs, self.scores), '#ffd966', base=15, pady=(0, 12))

    self._radar_values = [
        float(self.scores.get('game_score_100', 0)),
        float(self.scores.get('prod_score_100', 0)),
        float(self.scores.get('ai_score_100', 0)),
        float(self.scores.get('overall_score_100', 0)),
    ]
    self._radar_labels = ['遊戲', '生產力', 'AI', '綜合']

    self.radar_holder = ctk.CTkFrame(self.left_frame, fg_color='transparent', corner_radius=0)
    self.radar_holder.pack(fill='x', padx=16, pady=(4, 12))
    self.radar_holder.configure(height=330)
    self.radar_holder.bind('<Configure>', lambda e: _v42_schedule_redraw(self, delay=120), add='+')

    self.bottleneck_holder = ctk.CTkFrame(self.left_frame, fg_color='transparent', corner_radius=0)
    self.bottleneck_holder.pack(fill='x', padx=16, pady=(0, 18))
    self.bottleneck_holder.configure(height=320)
    self.bottleneck_holder.bind('<Configure>', lambda e: _v42_schedule_redraw(self, delay=120), add='+')

    _v424_bind_reflow(self)
    self.after(220, lambda: (_v424_reflow_messages(self), _v42_redraw_charts(self)))


def v424_set_ui_scale(self, value):
    try:
        v42_set_ui_scale(self, value)
    finally:
        try:
            _v424_reflow_messages(self)
        except Exception:
            pass
        _v42_schedule_redraw(self, delay=180)


def v424_set_theme_mode(self, value):
    mode = 'Light' if str(value) in ['白色', 'Light', 'light'] else 'Dark'
    try:
        ctk.set_appearance_mode(mode)
        self.theme_mode_value = mode
        if mode == 'Light':
            self.configure(fg_color='#e5e5e5')
            self.topbar.configure(fg_color='#f0f0f0')
            self.main_pane.configure(bg='#e5e5e5')
        else:
            self.configure(fg_color='#242424')
            self.topbar.configure(fg_color='#202020')
            self.main_pane.configure(bg='#1f1f1f')
    except Exception:
        pass
    try:
        for child in self.left_frame.winfo_children():
            child.destroy()
        self.setup_left_panel()
    except Exception:
        pass
    _v42_schedule_redraw(self, delay=200)


def show_startup_notice_v424(parent):
    win = ctk.CTkToplevel(parent)
    win.title('v42.4 版本公告')
    win.geometry('820x500')
    win.transient(parent)
    win.attributes('-topmost', True)
    frame = ctk.CTkFrame(win, corner_radius=14)
    frame.pack(fill='both', expand=True, padx=18, pady=18)
    ctk.CTkLabel(frame, text='電腦檢測升級工具 v42.4', text_color='#00ffff', font=ctk.CTkFont(size=24, weight='bold')).pack(anchor='w', padx=24, pady=(20, 12))
    box = ctk.CTkTextbox(frame, wrap='word', font=ctk.CTkFont(size=15), height=280)
    box.pack(fill='both', expand=True, padx=24, pady=(0, 14))
    box.insert('end', 'v42.4 更新重點\n')
    box.insert('end', '• 左側硬體分析改用 Message 自適應文字排版，縮放或拖拉欄寬時會重新排版。\n')
    box.insert('end', '• 修復長型號、評分方式、分級制與升級建議在窄欄位被吃字的問題。\n')
    box.insert('end', '• 黑色 / 白色主題下，左側背景維持乾淨一致，不再出現文字塊狀底色。\n')
    box.insert('end', '• 保留 v42 系列圖表與主題切換功能。\n\n')
    box.insert('end', '注意事項\n')
    box.insert('end', '• AI 市場與硬體價格波動大，有無貨或未上架價格不正確，仍以實際購買網站為準。\n')
    box.insert('end', '• 研發版本不代表最終品質。\n')
    box.configure(state='disabled')
    ctk.CTkButton(win, text='確認進入', command=win.destroy, width=280, height=44).pack(pady=(0, 24))
    win.grab_set()
    try:
        win.focus_force()
    except Exception:
        pass


def v424_init(self):
    v421_init(self)
    try:
        self.title(self.title().replace('v42.3', 'v42.4').replace('v42.2', 'v42.4').replace('v42.1', 'v42.4').replace('v42', 'v42.4'))
        for child in self.topbar.winfo_children():
            try:
                if isinstance(child, ctk.CTkLabel) and '電腦硬體 AI 顧問' in child.cget('text'):
                    child.configure(text='電腦硬體 AI 顧問 v42.4')
            except Exception:
                pass
    except Exception:
        pass


# 套用 v42.4
ROGApp.__init__ = v424_init
ROGApp.setup_left_panel = setup_left_panel_v424
ROGApp.set_ui_scale = v424_set_ui_scale
ROGApp.set_theme_mode = v424_set_theme_mode
show_startup_notice_v421 = show_startup_notice_v424
show_startup_notice_v422 = show_startup_notice_v424
show_startup_notice_v423 = show_startup_notice_v424



# ============================================================
# v1.0.0：正式版 / UI 主題 / 字重 / 查價功能暫停 / 白色模式 AI 對話修正
# ============================================================
APP_VERSION = "v1.0.1-t4"


def _v430_is_light(self=None):
    return str(getattr(self, 'theme_mode_value', 'Dark')).lower() == 'light'


def _v430_font_family(self=None):
    mode = str(getattr(self, 'font_weight_mode', 'normal'))
    if mode == 'thin':
        return 'Microsoft JhengHei UI Light'
    return 'Microsoft JhengHei UI'


def _v430_font(base_size=15, weight='normal', self=None):
    pct = getattr(self, 'ui_scale_percent', 100) if self is not None else 100
    # Message 不吃 CTk scaling，自己算字體；限制最大避免 500% 直接爆版。
    factor = max(0.78, min(2.05, pct / 100.0))
    size = max(9, int(base_size * factor))
    mode = str(getattr(self, 'font_weight_mode', 'normal')) if self is not None else 'normal'
    if mode == 'bold' and weight != 'bold':
        weight = 'bold'
    elif mode == 'thin':
        weight = 'normal'
    return (_v430_font_family(self), size, weight)


# 覆蓋 v42.4 文字字體函式，讓左側硬體分析跟右上角「字重」同步。
_v424_font = _v430_font


def _v430_left_content_width(self):
    """更保守地抓可視寬度，避免 Message 寬度大於實際左欄而被右側吃掉。"""
    try:
        canvas = getattr(self.left_frame, '_parent_canvas', None)
        if canvas is not None:
            w = canvas.winfo_width()
            if w and w > 120:
                return max(145, int(w - 64))
    except Exception:
        pass
    try:
        w = self.left_pane_holder.winfo_width()
        if w and w > 120:
            return max(145, int(w - 72))
    except Exception:
        pass
    try:
        w = self.left_frame.winfo_width()
        if w and w > 120:
            return max(145, int(w - 80))
    except Exception:
        pass
    return 360


_v424_left_content_width = _v430_left_content_width


def _v430_soft_break_text(text):
    """對長英文 / 路徑 / 評分列加斷行機會，但不要把中文切太碎。"""
    s = _v421_safe_text(text)
    s = re.sub(r'\(系統可用 ([0-9.]+G)\)\s*\(系統可用 \1\)', r'(系統可用 \1)', s)
    # 特定長段落才切，不要所有逗號都切，避免變成一塊一塊。
    s = s.replace(' / ', ' /\n')
    s = s.replace(' | ', ' |\n')
    s = s.replace('；', '；\n')
    # 英文 benchmark 長串加換行機會。
    s = s.replace('PassMark G3D /\nBlender', 'PassMark G3D /\nBlender')
    s = s.replace('Cinebench2024 + PassMark', 'Cinebench2024 +\nPassMark')
    # 分級列拆成兩行，避免縮小左欄時右側吃字。
    s = s.replace('SS95-100 | S+88', 'SS95-100 |\nS+88')
    s = s.replace('A++76 | A+70', 'A++76 |\nA+70')
    s = s.replace('B++56 | B+48', 'B++56 |\nB+48')
    s = re.sub(r'\n{3,}', '\n\n', s)
    return s.strip()


_v424_soft_break_text = _v430_soft_break_text


def _v430_ai_colors(self=None):
    if _v430_is_light(self):
        return {
            'bg': '#f7f7f7', 'border': '#b8b8b8', 'text': '#111111',
            'user': '#005bbb', 'ai': '#006b3c', 'wait': '#555555',
            'error': '#b00020', 'warn': '#9a5a00', 'sep': '#999999'
        }
    return {
        'bg': '#1f1f1f', 'border': '#444444', 'text': '#ffffff',
        'user': '#53a7ff', 'ai': '#00ff66', 'wait': '#dddddd',
        'error': '#ff6666', 'warn': '#ffaa00', 'sep': '#777777'
    }


def _configure_ai_text_tags_v430(widget, owner=None):
    try:
        colors = _v430_ai_colors(owner)
        widget.configure(fg_color=colors['bg'], text_color=colors['text'], border_color=colors['border'])
        t = widget._textbox if hasattr(widget, '_textbox') else widget
        t.configure(bg=colors['bg'], fg=colors['text'], insertbackground=colors['text'])
        t.tag_configure('user', foreground=colors['user'], spacing1=4, spacing3=4)
        t.tag_configure('ai', foreground=colors['ai'], spacing1=4, spacing3=8)
        t.tag_configure('wait', foreground=colors['wait'])
        t.tag_configure('error', foreground=colors['error'])
        t.tag_configure('warn', foreground=colors['warn'])
        t.tag_configure('sep', foreground=colors['sep'])
    except Exception:
        pass


def ai_chat_render_v430(self, history=None, pending=None, warning=None, error=None):
    widget = getattr(self, 'ai_response', None)
    if widget is None:
        return
    history = history if history is not None else getattr(self, 'ai_history', [])
    try:
        _configure_ai_text_tags_v430(widget, self)
        widget.configure(state='normal')
        widget.delete('0.0', 'end')
        rows = []
        for item in history[-AI_MEMORY_MAX_TURNS:]:
            rows.append((str(item.get('user', '')).strip(), str(item.get('assistant', '')).strip(), 'normal'))
        if pending:
            rows.append((str(pending.get('user', '')).strip(), str(pending.get('assistant', AI_PENDING_TEXT_V38)).strip(), 'pending'))
        if warning:
            widget.insert('end', warning + '\n', 'warn')
        if error:
            widget.insert('end', error + '\n', 'error')
        for i, (u, a, mode) in enumerate(rows):
            if i > 0:
                widget.insert('end', '\n' + '─' * 30 + '\n', 'sep')
            if u:
                widget.insert('end', '你：' + u + '\n', 'user')
            if a:
                tag = 'wait' if mode == 'pending' else 'ai'
                widget.insert('end', 'AI：' + a + '\n', tag)
        widget.configure(state='disabled')
        # 新回覆時顯示最新問題開頭，不強制跳到最底。
        if rows:
            try:
                widget.see('end-8l')
            except Exception:
                pass
    except Exception:
        pass


# 覆蓋所有 AI 渲染入口，白色模式不再黑底綠字。
ai_chat_render_v38 = ai_chat_render_v430


def _v430_disable_price_ui(self):
    """暫停查價相關 UI。只保留選規格 / 加入清單相關流程骨架。"""
    for name in ['manual_query_frame', 'action_frame', 'price_label']:
        obj = getattr(self, name, None)
        try:
            if obj is not None:
                obj.pack_forget()
                obj.grid_forget()
        except Exception:
            pass
    for name in ['search_btn', 'open_link_btn', 'add_cart_btn']:
        obj = getattr(self, name, None)
        try:
            if obj is not None:
                obj.configure(state='disabled')
        except Exception:
            pass


def v430_repack_bottom_actions(self):
    # 查價功能 v1.0.0 暫時停用，不把查詢時價、自訂型號、價格輸出框放出來。
    _v430_disable_price_ui(self)


ROGApp.repack_bottom_actions = v430_repack_bottom_actions


def v430_set_font_weight(self, value):
    mapping = {'細體': 'thin', '標準': 'normal', '粗體': 'bold', 'Thin': 'thin', 'Normal': 'normal', 'Bold': 'bold'}
    self.font_weight_mode = mapping.get(str(value), 'normal')
    try:
        _v424_reflow_messages(self)
    except Exception:
        pass
    try:
        if hasattr(self, 'ai_response'):
            pct = getattr(self, 'ui_scale_percent', 100)
            factor = max(0.85, min(1.8, pct / 100.0))
            ai_size = max(12, int(15 * factor))
            weight = 'bold' if self.font_weight_mode == 'bold' else 'normal'
            self.ai_response.configure(font=ctk.CTkFont(family=_v430_font_family(self), size=ai_size, weight=weight))
    except Exception:
        pass
    _v42_schedule_redraw(self, delay=160)


def v430_set_theme_mode(self, value):
    mode = 'Light' if str(value) in ['白色', 'Light', 'light'] else 'Dark'
    try:
        ctk.set_appearance_mode(mode)
        self.theme_mode_value = mode
        if mode == 'Light':
            self.configure(fg_color='#e5e5e5')
            self.topbar.configure(fg_color='#f0f0f0')
            self.main_pane.configure(bg='#e5e5e5')
        else:
            self.configure(fg_color='#242424')
            self.topbar.configure(fg_color='#202020')
            self.main_pane.configure(bg='#1f1f1f')
    except Exception:
        pass
    try:
        if hasattr(self, 'ai_response'):
            _configure_ai_text_tags_v430(self.ai_response, self)
            ai_chat_render_v430(self, history=getattr(self, 'ai_history', []))
    except Exception:
        pass
    try:
        for child in self.left_frame.winfo_children():
            child.destroy()
        self.setup_left_panel()
    except Exception:
        pass
    _v42_schedule_redraw(self, delay=180)


def v430_set_ui_scale(self, value):
    try:
        v424_set_ui_scale(self, value)
    finally:
        try:
            v430_set_font_weight(self, getattr(self, 'font_weight_display', '標準'))
        except Exception:
            pass
        _v42_schedule_redraw(self, delay=180)


def _v430_add_font_weight_menu(self):
    try:
        ctk.CTkLabel(self.topbar, text='字重', text_color='#cccccc').pack(side='right', padx=(10, 4))
        self.font_weight_menu = ctk.CTkOptionMenu(
            self.topbar,
            values=['細體', '標準', '粗體'],
            command=lambda v: (setattr(self, 'font_weight_display', v), v430_set_font_weight(self, v)),
            width=95,
        )
        self.font_weight_menu.set('標準')
        self.font_weight_display = '標準'
        self.font_weight_mode = 'normal'
        self.font_weight_menu.pack(side='right', padx=(0, 8), pady=5)
    except Exception:
        pass


def show_startup_notice_v430(parent):
    win = ctk.CTkToplevel(parent)
    win.title(f'{APP_VERSION} 版本公告')
    win.geometry('820x500')
    win.transient(parent)
    win.attributes('-topmost', True)
    frame = ctk.CTkFrame(win, corner_radius=14)
    frame.pack(fill='both', expand=True, padx=18, pady=18)
    ctk.CTkLabel(
        frame,
        text=f'電腦檢測升級工具 {APP_VERSION}',
        text_color='#00ffff',
        font=ctk.CTkFont(size=24, weight='bold'),
    ).pack(anchor='w', padx=24, pady=(20, 12))
    box = ctk.CTkTextbox(frame, wrap='word', font=ctk.CTkFont(size=15), height=280)
    box.pack(fill='both', expand=True, padx=24, pady=(0, 14))
    box.insert('end', f'{APP_VERSION} 正式版更新重點\n')
    box.insert('end', '• 正式版版本號改為 v1.0.0，作為第一個穩定發行版本。\n')
    box.insert('end', '• 保留硬體檢測、跑分評價、AI 顧問、雷達圖與瓶頸圖。\n')
    box.insert('end', '• 右上角保留字體縮放、字重與黑白主題切換。\n')
    box.insert('end', '• 白色主題下 AI 回覆區改為淺底深色文字，提升可讀性。\n')
    box.insert('end', '• 查價功能與自訂查價關鍵字區塊暫停顯示，避免未完成流程干擾正式版使用。\n')
    box.insert('end', '• 持續修正左側硬體分析在縮放與拖拉欄寬時的換行問題。\n\n')
    box.insert('end', '注意事項\n')
    box.insert('end', '• AI 市場與硬體價格波動大，有無貨或未上架價格不正確，仍以實際購買網站為準。\n')
    box.insert('end', '• 本工具提供估算與建議，不代表實際跑分或保證相容性。\n')
    box.configure(state='disabled')
    ctk.CTkButton(win, text='確認進入', command=win.destroy, width=280, height=44).pack(pady=(0, 24))
    win.grab_set()
    try:
        win.focus_force()
    except Exception:
        pass


def v430_init(self):
    v424_init(self)
    self.font_weight_mode = getattr(self, 'font_weight_mode', 'normal')
    self.font_weight_display = getattr(self, 'font_weight_display', '標準')
    try:
        device_type = '筆記型電腦' if getattr(self, 'is_laptop', False) else '桌上型電腦'
        self.title(f'電腦檢測升級工具 {APP_VERSION} - [{device_type}]')
        for child in self.topbar.winfo_children():
            try:
                if isinstance(child, ctk.CTkLabel) and '電腦硬體 AI 顧問' in child.cget('text'):
                    child.configure(text=f'電腦硬體 AI 顧問 {APP_VERSION}')
            except Exception:
                pass
        _v430_add_font_weight_menu(self)
    except Exception:
        pass
    try:
        # 左側預設寬一點，降低硬體型號被擋住的機率。
        self.main_pane.paneconfigure(self.left_pane_holder, minsize=420, width=620)
    except Exception:
        pass
    _v430_disable_price_ui(self)
    try:
        if hasattr(self, 'ai_response'):
            _configure_ai_text_tags_v430(self.ai_response, self)
    except Exception:
        pass


# 套用 v1.0.0
ROGApp.__init__ = v430_init
ROGApp.set_theme_mode = v430_set_theme_mode
ROGApp.set_ui_scale = v430_set_ui_scale
ROGApp.set_font_weight = v430_set_font_weight
show_startup_notice_v421 = show_startup_notice_v430
show_startup_notice_v422 = show_startup_notice_v430
show_startup_notice_v423 = show_startup_notice_v430
show_startup_notice_v424 = show_startup_notice_v430



# ============================================================
# v1.0.1 Hotfix：修復加入購物車按鈕被暫停查價流程一起隱藏
# ============================================================

def _v101_selected_product_payload(self):
    """在查價功能暫停時，直接把目前選到的規格加入智慧清單。"""
    try:
        selected = self.get_selected_target()
    except Exception:
        selected = ""
    selected = str(selected or "").strip()

    if not selected or selected in ["請選擇", "請先選擇", "--"] or "請選擇" in selected:
        return None, "請先選擇要加入購物車的項目。"
    if "不需要" in selected:
        return None, "此項目已設定為不需要，無需加入購物車。"

    try:
        keyword = self.build_search_keyword(selected)
    except Exception:
        keyword = clean_display_name(selected).strip() if 'clean_display_name' in globals() else selected
    keyword = str(keyword or selected).strip()

    mode = getattr(self, "current_mode", "")
    if mode == "UPGRADE":
        try:
            step_key = f"UPGRADE-{self.upg_cat.get()}-{selected}"
            target = f"{self.upg_cat.get()}：{selected}"
        except Exception:
            step_key = f"UPGRADE-{selected}"
            target = selected
    elif mode in ["BUILD_PC", "BUILD_LAPTOP", "LAPTOP"]:
        try:
            step_key = self.build_step
        except Exception:
            step_key = f"BUILD-{selected}"
        target = selected
    else:
        step_key = f"ITEM-{selected}"
        target = selected

    payload = {
        "step": step_key,
        "target": target,
        "name": keyword,
        "price": 0,
        "link": "",
        "search_link": "",
        "keyword": keyword,
        "note": "v1.0.1：查價功能暫停開發中，價格暫以 NT$0 顯示。",
    }
    return payload, None


def v101_add_to_cart(self):
    payload, error = _v101_selected_product_payload(self)
    if error:
        try:
            self._v101_cart_notice.configure(text=error, text_color="#ffaa00")
        except Exception:
            pass
        return

    try:
        self.current_fetch = payload
        self.cart_items[payload["step"]] = payload
        self.refresh_cart_ui()
        if hasattr(self, "add_cart_btn"):
            self.add_cart_btn.configure(text="✅ 已加入購物車", state="normal")
            self.after(1200, lambda: self.add_cart_btn.configure(text="🛒 加入購物車", state="normal"))
        try:
            self._v101_cart_notice.configure(
                text="已加入智慧清單。查價/搜尋商品功能目前仍在開發，價格暫以 NT$0 顯示。",
                text_color="#00ff66",
            )
        except Exception:
            pass
    except Exception as e:
        try:
            self._v101_cart_notice.configure(text=f"加入購物車失敗：{e}", text_color="#ff6666")
        except Exception:
            pass


def _v101_hide_widget(widget):
    try:
        widget.pack_forget()
    except Exception:
        pass
    try:
        widget.grid_forget()
    except Exception:
        pass


def _v101_disable_price_ui(self):
    """v1.0.1：停用查價/搜尋欄位，但保留加入購物車按鈕。"""
    # 查價與自訂搜尋仍處開發階段，避免正式版誤用。
    for name in ["manual_query_frame", "price_label"]:
        obj = getattr(self, name, None)
        if obj is not None:
            _v101_hide_widget(obj)

    # 重新整理 action_frame，只留下加入購物車。
    action = getattr(self, "action_frame", None)
    if action is not None:
        try:
            action.pack_forget()
        except Exception:
            pass
        try:
            action.pack(fill="x", pady=12, padx=12)
        except Exception:
            pass

    for name in ["search_btn", "open_link_btn"]:
        obj = getattr(self, name, None)
        if obj is not None:
            _v101_hide_widget(obj)
            try:
                obj.configure(state="disabled")
            except Exception:
                pass

    btn = getattr(self, "add_cart_btn", None)
    if btn is not None:
        try:
            btn.pack_forget()
        except Exception:
            pass
        try:
            btn.configure(text="🛒 加入購物車", command=lambda: v101_add_to_cart(self), state="normal", fg_color="#008800", width=220)
            btn.pack(side="right", padx=12)
        except Exception:
            pass

    # 小提示文字：放在操作面板內，不影響正式流程。
    if not hasattr(self, "_v101_cart_notice"):
        try:
            self._v101_cart_notice = ctk.CTkLabel(
                self.mid_frame,
                text="已知問題：搜尋特定商品與查詢商品功能目前仍處開發階段，預計 v1.1.0 加入。",
                text_color="#ffaa00",
                justify="left",
                anchor="w",
            )
            self._v101_cart_notice.pack(fill="x", padx=22, pady=(0, 8))
        except Exception:
            pass
    else:
        try:
            self._v101_cart_notice.configure(text="已知問題：搜尋特定商品與查詢商品功能目前仍處開發階段，預計 v1.1.0 加入。")
        except Exception:
            pass


def v101_repack_bottom_actions(self):
    _v101_disable_price_ui(self)


def show_startup_notice_v101(parent):
    win = ctk.CTkToplevel(parent)
    win.title(f'{APP_VERSION} 版本公告')
    win.geometry('840x540')
    win.transient(parent)
    win.attributes('-topmost', True)

    frame = ctk.CTkFrame(win, corner_radius=14)
    frame.pack(fill='both', expand=True, padx=18, pady=18)

    ctk.CTkLabel(
        frame,
        text=f'電腦檢測升級工具 {APP_VERSION}',
        text_color='#00ffff',
        font=ctk.CTkFont(size=24, weight='bold'),
    ).pack(anchor='w', padx=24, pady=(20, 12))

    box = ctk.CTkTextbox(frame, wrap='word', font=ctk.CTkFont(size=15), height=310)
    box.pack(fill='both', expand=True, padx=24, pady=(0, 14))
    box.insert('end', f'{APP_VERSION} 修復內容\n')
    box.insert('end', '• 修復「加入購物車 / 確定加入清單」按鈕在正式版中被一起隱藏的問題。\n')
    box.insert('end', '• 查價與自訂商品搜尋功能仍先暫停顯示，但可先把目前選取規格加入智慧清單。\n')
    box.insert('end', '• 加入購物車時，價格暫以 NT$0 顯示，後續待 v1.1.0 查價功能完成後補上。\n')
    box.insert('end', '• 版本號更新為 v1.0.1，作為 v1.0.0 的修正版。\n\n')
    box.insert('end', '已知問題\n')
    box.insert('end', '• 搜尋特定商品功能目前處於開發階段，預計 v1.1.0 加入。\n')
    box.insert('end', '• 查詢商品 / 即時查價功能目前處於開發階段，預計 v1.1.0 加入。\n')
    box.insert('end', '• 目前購物車內的價格僅作為佔位顯示，實際購買仍需以電商網站為準。\n')
    box.configure(state='disabled')

    ctk.CTkButton(win, text='確認進入', command=win.destroy, width=280, height=44).pack(pady=(0, 24))
    win.grab_set()
    try:
        win.focus_force()
    except Exception:
        pass


# 套用 v1.0.1 hotfix
_v430_disable_price_ui = _v101_disable_price_ui
ROGApp.repack_bottom_actions = v101_repack_bottom_actions
ROGApp.add_to_cart = v101_add_to_cart
show_startup_notice_v430 = show_startup_notice_v101
show_startup_notice_v421 = show_startup_notice_v101
show_startup_notice_v422 = show_startup_notice_v101
show_startup_notice_v423 = show_startup_notice_v101
show_startup_notice_v424 = show_startup_notice_v101




# ============================================================
# v1.0.1-t4 Test：公告改為 版本重點 / 已知問題 / 注意事項，無數字編號
# ============================================================
APP_VERSION = "v1.0.1-t4"


def _v101t1_hide_widget(widget):
    try:
        widget.pack_forget()
    except Exception:
        pass
    try:
        widget.grid_forget()
    except Exception:
        pass


def _v101t1_place_cart_bottom(self):
    """把購物車摘要固定移到操作面板內容最下方。"""
    bar = getattr(self, 'cart_bar', None)
    if bar is None:
        return
    try:
        bar.pack_forget()
    except Exception:
        pass
    try:
        bar.pack(fill='x', padx=20, pady=(14, 20), side='bottom')
    except Exception:
        try:
            bar.pack(fill='x', padx=20, pady=(14, 20))
        except Exception:
            pass


def _v101t1_enable_query_ui(self):
    """修復查詢時價/商品結果/加入購物車，只隱藏自訂型號搜尋欄。"""
    # 只拿掉「自訂型號 / 查價關鍵字」區塊；查詢商品功能保留。
    manual = getattr(self, 'manual_query_frame', None)
    if manual is not None:
        _v101t1_hide_widget(manual)
    try:
        if hasattr(self, 'manual_query_entry'):
            self.manual_query_entry.delete(0, 'end')
    except Exception:
        pass

    # 還原按鈕列：查詢時價 + 確定加入清單；先不顯示「開啟商品/搜尋」。
    action = getattr(self, 'action_frame', None)
    if action is not None:
        try:
            action.pack_forget()
        except Exception:
            pass
        try:
            action.pack(fill='x', pady=(12, 6), padx=12)
        except Exception:
            pass

    search = getattr(self, 'search_btn', None)
    if search is not None:
        try:
            search.pack_forget()
        except Exception:
            pass
        try:
            search.configure(text='🔍 查詢時價', command=self.execute_search, fg_color='#cc5500', state='normal', width=180)
            search.pack(side='left', padx=12)
        except Exception:
            pass

    # 這個先不要出現，避免使用者誤以為可以直接輸入任意商品搜尋。
    open_btn = getattr(self, 'open_link_btn', None)
    if open_btn is not None:
        _v101t1_hide_widget(open_btn)
        try:
            open_btn.configure(state='disabled')
        except Exception:
            pass

    add_btn = getattr(self, 'add_cart_btn', None)
    if add_btn is not None:
        try:
            add_btn.pack_forget()
        except Exception:
            pass
        try:
            add_btn.configure(text='🛒 確定加入清單', command=lambda: cart_add_current_v38(self), fg_color='#008800', state='disabled', width=180)
            add_btn.pack(side='right', padx=12)
        except Exception:
            pass

    price = getattr(self, 'price_label', None)
    if price is not None:
        try:
            price.pack_forget()
        except Exception:
            pass
        try:
            price.pack(fill='both', expand=False, padx=20, pady=(8, 10))
        except Exception:
            pass
        try:
            if not getattr(self, 'current_fetch', None):
                price.configure(text='請選擇規格並點擊 [🔍 查詢時價]。\n提醒：查詢商品 / 即時查價目前為測試功能，價格與庫存以實際網站為準。', text_color='#ffffff')
        except Exception:
            pass

    # 移除 v1.0.1 hotfix 文字提示，避免卡在中間。
    notice = getattr(self, '_v101_cart_notice', None)
    if notice is not None:
        _v101t1_hide_widget(notice)

    _v101t1_place_cart_bottom(self)


def v101t1_repack_bottom_actions(self):
    _v101t1_enable_query_ui(self)


def v101t1_setup_cart_button(self):
    """購物車摘要永遠在操作面板下方。"""
    try:
        setup_cart_button_v38(self)
        _v101t1_place_cart_bottom(self)
    except Exception:
        pass


def show_startup_notice_v101t1(parent):
    win = ctk.CTkToplevel(parent)
    win.title(f'{APP_VERSION} 正式版公告')
    win.geometry('860x560')
    win.transient(parent)
    win.attributes('-topmost', True)

    frame = ctk.CTkFrame(win, corner_radius=14)
    frame.pack(fill='both', expand=True, padx=18, pady=18)

    ctk.CTkLabel(
        frame,
        text=f'電腦檢測升級工具 {APP_VERSION}',
        text_color='#00ffff',
        font=ctk.CTkFont(size=24, weight='bold'),
    ).pack(anchor='w', padx=24, pady=(20, 12))

    box = ctk.CTkTextbox(frame, wrap='word', font=ctk.CTkFont(size=15), height=320)
    box.pack(fill='both', expand=True, padx=24, pady=(0, 14))
    box.insert('end', f'{APP_VERSION} 正式版公告\n\n')
    box.insert('end', '版本重點\n')
    box.insert('end', '• 修復「查詢時價 / 查詢商品」流程，避免 v1.0.1 誤把查詢功能整段隱藏。\n')
    box.insert('end', '• 修復「確定加入清單」按鈕，查價成功後可加入智慧清單。\n')
    box.insert('end', '• 購物車摘要固定移到操作面板下方，符合先選規格、再查價、最後看購物車的流程。\n')
    box.insert('end', '• 版本號暫定為 v1.0.1-t4，確認穩定後再整理成正式 v1.0.1。\n\n')
    box.insert('end', '操作步驟\n')
    box.insert('end', '1. 先選規格：依頁面選擇品類、世代 / 規格、容量或型號。\n')
    box.insert('end', '2. 再查詢：點擊「查詢時價」，確認目前抓到的商品與價格資訊。\n')
    box.insert('end', '3. 加入清單：確認結果可用後，點擊「確定加入清單」，最後到購物車查看整理結果。\n\n')
    box.insert('end', '已知問題\n')
    box.insert('end', '• 搜尋特定商品功能目前仍處於開發階段，預計 v1.1.0 完整加入。\n\n')
    box.insert('end', '注意事項\n')
    box.insert('end', '• 查詢商品 / 即時查價功能目前為測試階段，價格、庫存、平台比對仍可能不精準。\n')
    box.insert('end', '• 購物與價格資訊仍以實際電商網站為準。\n')
    box.configure(state='disabled')

    ctk.CTkButton(win, text='確認進入', command=win.destroy, width=280, height=44).pack(pady=(0, 24))
    win.grab_set()
    try:
        win.focus_force()
    except Exception:
        pass


def v101t1_init(self):
    # 仍沿用 v1.0.1 初始化，初始化後再修復查詢 UI。
    v430_init(self)
    try:
        device_type = '筆記型電腦' if getattr(self, 'is_laptop', False) else '桌上型電腦'
        self.title(f'電腦檢測升級工具 {APP_VERSION} - [{device_type}]')
        for child in self.topbar.winfo_children():
            try:
                if isinstance(child, ctk.CTkLabel) and '電腦硬體 AI 顧問' in child.cget('text'):
                    child.configure(text=f'電腦硬體 AI 顧問 {APP_VERSION}')
            except Exception:
                pass
    except Exception:
        pass
    _v101t1_enable_query_ui(self)


# 套用 v1.0.1-t4 正式版覆蓋
_v430_disable_price_ui = _v101t1_enable_query_ui
ROGApp.__init__ = v101t1_init
ROGApp.repack_bottom_actions = v101t1_repack_bottom_actions
ROGApp.add_to_cart = cart_add_current_v38
ROGApp.setup_right_panel = lambda self: v101t1_setup_cart_button(self)
show_startup_notice_v430 = show_startup_notice_v101t1
show_startup_notice_v421 = show_startup_notice_v101t1
show_startup_notice_v422 = show_startup_notice_v101t1
show_startup_notice_v423 = show_startup_notice_v101t1
show_startup_notice_v424 = show_startup_notice_v101t1






# ============================================================
# v1.0.1 Release：乾淨公告與查詢/購物車流程確認版
# ============================================================
APP_VERSION = "v1.0.1"



def _v101t5_add_operation_steps_hint(self):
    """把操作步驟放到 App 操作面板內，而不是啟動公告。"""
    try:
        old = getattr(self, '_v101t5_steps_frame', None)
        if old is not None:
            try:
                old.destroy()
            except Exception:
                pass

        parent = getattr(self, 'mid_frame', None)
        if parent is None:
            return

        frame = ctk.CTkFrame(parent, corner_radius=10, fg_color=('#eeeeee', '#2b2b2b'))
        self._v101t5_steps_frame = frame

        pack_kwargs = dict(fill='x', padx=22, pady=(4, 14))
        try:
            if hasattr(self, 'mid_title'):
                frame.pack(after=self.mid_title, **pack_kwargs)
            else:
                frame.pack(**pack_kwargs)
        except Exception:
            frame.pack(**pack_kwargs)

        ctk.CTkLabel(
            frame,
            text='操作步驟',
            text_color='#00ffff',
            font=ctk.CTkFont(size=15, weight='bold'),
            anchor='w',
            justify='left',
        ).pack(anchor='w', padx=14, pady=(10, 4))

        steps = (
            '1. 先選規格：依頁面選擇品類、世代 / 規格、容量或型號。\n'
            '2. 再查詢：點擊「查詢時價」，確認目前抓到的商品與價格資訊。\n'
            '3. 加入清單：確認結果可用後，點擊「確定加入清單」，最後到購物車查看整理結果。'
        )
        ctk.CTkLabel(
            frame,
            text=steps,
            text_color=('#222222', '#dddddd'),
            font=ctk.CTkFont(size=13),
            anchor='w',
            justify='left',
            wraplength=760,
        ).pack(fill='x', padx=14, pady=(0, 12))
    except Exception:
        pass


def show_startup_notice_v101release(parent):
    """v1.0.1：只保留乾淨公告，避免舊公告函式殘留內容被呼叫。"""
    win = ctk.CTkToplevel(parent)
    win.title(f'{APP_VERSION} 版本公告')
    win.geometry('840x540')
    win.transient(parent)
    win.attributes('-topmost', True)

    frame = ctk.CTkFrame(win, corner_radius=14)
    frame.pack(fill='both', expand=True, padx=18, pady=18)

    ctk.CTkLabel(
        frame,
        text=f'電腦檢測升級工具 {APP_VERSION}',
        text_color='#00ffff',
        font=ctk.CTkFont(size=24, weight='bold'),
    ).pack(anchor='w', padx=24, pady=(20, 12))

    box = ctk.CTkTextbox(frame, wrap='word', font=ctk.CTkFont(size=15), height=300)
    box.pack(fill='both', expand=True, padx=24, pady=(0, 14))
    box.insert('end', f'{APP_VERSION} 版本公告\n\n')
    box.insert('end', '版本重點\n')
    box.insert('end', '• 修復「查詢時價 / 查詢商品」流程。\n')
    box.insert('end', '• 修復「確定加入清單」按鈕，查價成功後可加入智慧清單。\n')
    box.insert('end', '• 購物車摘要固定移到操作面板下方。\n\n')
    box.insert('end', '已知問題\n')
    box.insert('end', '• 搜尋特定商品功能目前仍處於開發階段，預計 v1.1.0 完整加入。\n\n')
    box.insert('end', '注意事項\n')
    box.insert('end', '• 查詢商品 / 即時查價功能目前為測試階段，價格、庫存、平台比對仍可能不精準。\n')
    box.insert('end', '• 購物與價格資訊仍以實際電商網站為準。\n')
    box.configure(state='disabled')

    ctk.CTkButton(win, text='確認進入', command=win.destroy, width=280, height=44).pack(pady=(0, 24))
    win.grab_set()
    try:
        win.focus_force()
    except Exception:
        pass


def v101release_init(self):
    # 沿用 t1 查詢 UI 修復：保留查詢時價、查詢結果、確定加入清單；隱藏任意自訂搜尋輸入。
    v101t1_init(self)
    try:
        device_type = '筆記型電腦' if getattr(self, 'is_laptop', False) else '桌上型電腦'
        self.title(f'電腦檢測升級工具 {APP_VERSION} - [{device_type}]')
        for child in self.topbar.winfo_children():
            try:
                if isinstance(child, ctk.CTkLabel) and '電腦硬體 AI 顧問' in child.cget('text'):
                    child.configure(text=f'電腦硬體 AI 顧問 {APP_VERSION}')
            except Exception:
                pass
    except Exception:
        pass
    _v101t5_add_operation_steps_hint(self)


# 套用 v1.0.1 正式版覆蓋：所有舊公告入口都指向 t11，避免舊文字殘留。
ROGApp.__init__ = v101release_init
show_startup_notice_v101release_final = show_startup_notice_v101release
show_startup_notice_v101t5 = show_startup_notice_v101release
show_startup_notice_v101t1 = show_startup_notice_v101release
show_startup_notice_v101 = show_startup_notice_v101release
show_startup_notice_v430 = show_startup_notice_v101release
show_startup_notice_v421 = show_startup_notice_v101release
show_startup_notice_v422 = show_startup_notice_v101release
show_startup_notice_v423 = show_startup_notice_v101release
show_startup_notice_v424 = show_startup_notice_v101release


if __name__ == "__main__":
    multiprocessing.freeze_support()
    app = ROGApp()
    app.mainloop()
