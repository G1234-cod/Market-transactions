"""平台预设的80个商品类别定义

系统将同时运行自研模型与阿里云视觉大模型进行图像识别。
若识别结果属于平台预设的80个类别，则直接返回；
否则由视觉大模型进行自主识别。
"""

# ============================================================
# 预设商品类别（80个）
# ============================================================
PRESET_CATEGORIES = {
    # 数码-手机
    "手机": [
        "iPhone 15 Pro Max", "iPhone 15 Pro", "iPhone 15", "iPhone 15 Plus",
        "iPhone 14 Pro Max", "iPhone 14 Pro", "iPhone 14", "iPhone 14 Plus",
        "iPhone 13 Pro Max", "iPhone 13 Pro", "iPhone 13", "iPhone 13 mini",
        "iPhone 12 Pro Max", "iPhone 12 Pro", "iPhone 12", "iPhone 12 mini",
        "华为 Mate 60 Pro", "华为 Mate 60", "华为 Mate 50 Pro", "华为 Mate 50",
        "华为 Pura 80 Pro", "华为 Pura 80", "华为 P60 Pro", "华为 P60",
        "小米 14 Ultra", "小米 14 Pro", "小米 14", "小米 13 Ultra",
        "OPPO Find X7 Ultra", "OPPO Find X7", "OPPO Find X6 Ultra",
        "vivo X100 Ultra", "vivo X100 Pro", "vivo X100",
    ],
    # 数码-笔记本
    "笔记本": [
        "MacBook Pro 16", "MacBook Pro 14", "MacBook Air 15", "MacBook Air 13",
        "ThinkPad X1 Carbon", "ThinkPad X1 Yoga", "ThinkPad T14",
        "戴尔 XPS 15", "戴尔 XPS 13", "戴尔 Precision 5570",
        "联想拯救者 Y9000X", "联想拯救者 Y7000",
        "华硕 ROG Zephyrus", "华硕 ROG Strix",
        "惠普暗影精灵 9", "惠普战66",
    ],
    # 数码-平板
    "平板": [
        "iPad Pro 12.9", "iPad Pro 11", "iPad Air", "iPad", "iPad mini",
        "华为 MatePad Pro", "华为 MatePad",
        "小米平板 6 Pro", "小米平板 6",
        "三星 Galaxy Tab S9", "三星 Galaxy Tab S8",
    ],
    # 数码-外设
    "外设": [
        "罗技 G915", "罗技 G610", "罗技 MX Keys",
        "雷蛇黑寡妇", "雷蛇猎魂光蛛",
        "樱桃 MX 3.0", "樱桃 MX 8.0",
        "罗技 GPW", "罗技 G502", "罗技 MX Master",
        "雷蛇炼狱蝰蛇", "雷蛇毒蝰",
        "赛睿 Sensei", "赛睿 Rival",
        "达尔优 A970", "达尔优 EK815",
    ],
    # 数码-耳机
    "耳机": [
        "AirPods Pro 2", "AirPods Pro", "AirPods 3", "AirPods 2",
        "AirPods Max",
        "索尼 WH-1000XM5", "索尼 WH-1000XM4", "索尼 WF-1000XM5",
        "Bose QuietComfort", "Bose QC Ultra",
        "华为 FreeBuds Pro 3", "华为 FreeBuds Pro 2",
        "小米 Buds 5 Pro", "小米 Buds 5",
        "漫步者 LolliPods", "漫步者 NeoBuds",
    ],
    # 数码-手表
    "手表": [
        "Apple Watch Ultra 2", "Apple Watch Series 9", "Apple Watch Series 8",
        "Apple Watch SE 2",
        "华为 Watch GT 4", "华为 Watch GT 3", "华为 Watch 4 Pro",
        "小米 Watch S3", "小米 Watch S2",
        "三星 Galaxy Watch 6", "三星 Galaxy Watch 5",
        "Amazfit GTS 4", "Amazfit GTR 4",
    ],
    # 数码-相机
    "相机": [
        "索尼 A7M4", "索尼 A7M3", "索尼 A7R5", "索尼 ZV-E1",
        "佳能 R6 Mark II", "佳能 R5", "佳能 R7", "佳能 M50",
        "尼康 Z8", "尼康 Z9", "尼康 Z6 III",
        "富士 X-T5", "富士 X-T4", "富士 X100V",
        "大疆 Pocket 3", "大疆 Action 4",
    ],
    # 数码-游戏机
    "游戏机": [
        "PlayStation 5", "PlayStation 4", "PlayStation VR2",
        "Xbox Series X", "Xbox Series S",
        "Switch OLED", "Switch", "Switch Lite",
    ],
}


def get_all_categories() -> list[str]:
    """获取所有品类名称"""
    return list(PRESET_CATEGORIES.keys())


def get_all_models() -> list[str]:
    """获取所有预设型号"""
    models = []
    for category in PRESET_CATEGORIES.values():
        models.extend(category)
    return models


def get_models_by_category(category: str) -> list[str]:
    """根据品类获取预设型号"""
    return PRESET_CATEGORIES.get(category, [])


def is_preset_model(model: str, category: str = "") -> bool:
    """检查型号是否属于预设类别"""
    if not model:
        return False
    
    model_lower = model.lower().strip()
    
    if category:
        for preset_model in PRESET_CATEGORIES.get(category, []):
            # ✅ 修复：使用相等或 token 匹配，避免子串误匹配
            preset_lower = preset_model.lower()
            if model_lower == preset_lower or model_lower in preset_lower.split():
                return True
        return False

    for category_models in PRESET_CATEGORIES.values():
        for preset_model in category_models:
            preset_lower = preset_model.lower()
            if model_lower == preset_lower or model_lower in preset_lower.split():
                return True
    return False


def is_preset_category(category: str) -> bool:
    """检查品类是否属于预设类别"""
    if not category:
        return False
    return category in PRESET_CATEGORIES


def get_category_from_model(model: str) -> str:
    """根据型号推断品类"""
    if not model:
        return ""
    
    model_lower = model.lower().strip()
    
    for category, models in PRESET_CATEGORIES.items():
        for preset_model in models:
            if model_lower in preset_model.lower() or preset_model.lower() in model_lower:
                return category
    
    return ""


def match_preset(model: str, category: str = "") -> dict:
    """匹配预设类别和型号"""
    matched_category = get_category_from_model(model) if not category else category
    matched_model = ""
    
    if matched_category:
        for preset_model in PRESET_CATEGORIES.get(matched_category, []):
            preset_lower = preset_model.lower()
            model_lower = model.lower().strip()
            if model_lower in preset_lower or preset_lower in model_lower:
                matched_model = preset_model
                break
    
    return {
        "is_preset": bool(matched_category),
        "category": matched_category,
        "model": matched_model,
    }
