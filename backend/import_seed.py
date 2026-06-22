"""种子数据灌入脚本 — 独立运行：python import_seed.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()
import pymysql

cfg = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "db": os.getenv("DB_NAME", "market_transactions"),
}
print(f"连接: {cfg['user']}@{cfg['host']}:{cfg['port']}/{cfg['db']}")

conn = pymysql.connect(**cfg, charset="utf8mb4")
cur = conn.cursor()

# 测试用户（重复执行也不报错）
cur.execute("INSERT IGNORE INTO users (id, username) VALUES (1, 'test_user')")

# 行情数据
items = [
    ("手机", "Apple", "iPhone 13", 3200, 2800, 3800),
    ("手机", "Apple", "iPhone 13 Pro", 4200, 3700, 4900),
    ("手机", "Apple", "iPhone 13 Pro Max", 5200, 4600, 6000),
    ("手机", "Apple", "iPhone 12", 2100, 1800, 2500),
    ("手机", "Apple", "iPhone 12 Pro", 2900, 2500, 3400),
    ("手机", "Apple", "iPhone 14", 4100, 3600, 4700),
    ("手机", "Apple", "iPhone 14 Pro Max", 6200, 5500, 7200),
    ("手机", "Xiaomi", "小米13", 2200, 1800, 2600),
    ("手机", "Xiaomi", "Redmi K60", 1400, 1100, 1700),
    ("手机", "HUAWEI", "Mate 40 Pro", 2500, 2000, 3100),
    ("手机", "HUAWEI", "P50 Pro", 2300, 1900, 2800),
    ("笔记本", "Apple", "MacBook Air M1 13寸", 4200, 3500, 5000),
    ("笔记本", "Apple", "MacBook Air M2 13寸", 5500, 4800, 6500),
    ("笔记本", "Apple", "MacBook Pro 14寸 M1 Pro", 7800, 6800, 9200),
    ("笔记本", "Lenovo", "ThinkPad X1 Carbon Gen9", 3500, 2800, 4300),
    ("笔记本", "Lenovo", "小新Pro 16 2023", 3200, 2700, 3800),
    ("笔记本", "Lenovo", "拯救者 Y9000P 2023", 5500, 4700, 6500),
    ("笔记本", "HUAWEI", "MateBook 14 2022", 3000, 2500, 3700),
    ("平板", "Apple", "iPad Air 4", 2200, 1800, 2700),
    ("平板", "Apple", "iPad Air 5", 3000, 2500, 3600),
    ("平板", "Apple", "iPad Pro 11寸 2022", 4500, 3800, 5400),
    ("平板", "HUAWEI", "MatePad Pro 11", 1800, 1500, 2200),
    ("外设", "Logitech", "G610 机械键盘", 220, 150, 300),
    ("外设", "Logitech", "G Pro X 机械键盘", 400, 300, 500),
    ("外设", "Logitech", "G502 鼠标", 150, 100, 200),
    ("外设", "Razer", "炼狱蝰蛇 V3", 250, 180, 320),
    ("外设", "Razer", "黑寡妇蜘蛛 V3", 350, 250, 450),
    ("耳机", "Apple", "AirPods Pro 2", 1000, 800, 1300),
    ("耳机", "Apple", "AirPods 3", 650, 500, 820),
    ("耳机", "Sony", "WH-1000XM5", 1400, 1100, 1700),
]

sql = "INSERT INTO market_prices (category, brand, model, avg_price, low_price, high_price) VALUES (%s, %s, %s, %s, %s, %s)"
cur.executemany(sql, items)
conn.commit()
print(f"种子数据灌入完成: {cur.rowcount} 条")
cur.close()
conn.close()
