"""测试 MySQL 数据库连接"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv()

import pymysql


def get_db_config():
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", 3306)),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", ""),
        "db": os.getenv("DB_NAME", "market_transactions"),
    }


def test_can_connect():
    """测试是否能连接到 MySQL"""
    cfg = get_db_config()
    conn = pymysql.connect(host=cfg["host"], port=cfg["port"], user=cfg["user"], password=cfg["password"], charset="utf8mb4")
    cur = conn.cursor()
    cur.execute("SELECT 1")
    assert cur.fetchone()[0] == 1
    cur.close()
    conn.close()
    print("  PASS: MySQL 连接成功")


def test_get_version():
    """测试获取 MySQL 版本"""
    cfg = get_db_config()
    conn = pymysql.connect(host=cfg["host"], port=cfg["port"], user=cfg["user"], password=cfg["password"], charset="utf8mb4")
    cur = conn.cursor()
    cur.execute("SELECT VERSION()")
    version = cur.fetchone()[0]
    cur.close()
    conn.close()
    print(f"  PASS: MySQL 版本 = {version}")


def test_users_table():
    """测试 users 表是否存在 + 数据"""
    cfg = get_db_config()
    conn = pymysql.connect(host=cfg["host"], port=cfg["port"], user=cfg["user"], password=cfg["password"], db=cfg["db"], charset="utf8mb4")
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    count = cur.fetchone()[0]
    print(f"  users 表: {count} 条记录")
    cur.execute("SELECT id, username FROM users")
    for row in cur.fetchall():
        print(f"    id={row[0]}, username={row[1]}")
    cur.close()
    conn.close()


def test_market_prices():
    """测试 market_prices 表是否存在 + 数据统计"""
    cfg = get_db_config()
    conn = pymysql.connect(host=cfg["host"], port=cfg["port"], user=cfg["user"], password=cfg["password"], db=cfg["db"], charset="utf8mb4")
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*), MIN(low_price), MAX(high_price) FROM market_prices")
    count, lo, hi = cur.fetchone()
    print(f"  market_prices 表: {count} 条记录, 最低价={lo}, 最高价={hi}")

    cur.execute("SELECT category, COUNT(*) as cnt FROM market_prices GROUP BY category")
    print("  按品类统计:")
    for row in cur.fetchall():
        print(f"    {row[0]}: {row[1]} 条")

    cur.close()
    conn.close()


def test_published_items():
    """测试 published_items 表是否存在"""
    cfg = get_db_config()
    conn = pymysql.connect(host=cfg["host"], port=cfg["port"], user=cfg["user"], password=cfg["password"], db=cfg["db"], charset="utf8mb4")
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM published_items")
    count = cur.fetchone()[0]
    print(f"  published_items 表: {count} 条记录（当前空表，待业务生成后才有数据）")
    cur.close()
    conn.close()


def test_ai_audit_logs():
    """测试 ai_audit_logs 表是否存在"""
    cfg = get_db_config()
    conn = pymysql.connect(host=cfg["host"], port=cfg["port"], user=cfg["user"], password=cfg["password"], db=cfg["db"], charset="utf8mb4")
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM ai_audit_logs")
    count = cur.fetchone()[0]
    print(f"  ai_audit_logs 表: {count} 条记录（当前空表，待业务运行后自动写入）")
    cur.close()
    conn.close()


# ============================================================
# 直接运行：python test_db.py
# ============================================================
if __name__ == "__main__":
    print("=== MySQL 数据库连接测试 ===\n")
    test_can_connect()
    test_get_version()
    print()
    print("=== 数据库建表验证 ===\n")
    test_users_table()
    test_market_prices()
    test_published_items()
    test_ai_audit_logs()
    print("\n=== 全部测试完成 ===")
