"""
迁移脚本: 添加爬虫相关字段
日期: 2026-06-29
"""
import asyncio
import aiomysql


async def migrate():
    """执行迁移"""
    conn = await aiomysql.connect(
        host='localhost',
        port=3306,
        user='root',
        password='123456',
        db='market_transactions',
        charset='utf8mb4'
    )
    
    async with conn.cursor() as cur:
        await cur.execute("DESCRIBE market_prices;")
        market_columns = {row[0] for row in await cur.fetchall()}
        
        await cur.execute("DESCRIBE price_history;")
        history_columns = {row[0] for row in await cur.fetchall()}
        
        if 'crawled_at' not in market_columns:
            await cur.execute("""
                ALTER TABLE `market_prices` 
                ADD COLUMN `crawled_at` DATETIME NULL DEFAULT NULL COMMENT '爬取时间(用于TTL判断)' AFTER `updated_at`;
            """)
            print("Add crawled_at column success")
        else:
            print("crawled_at column already exists, skip")
            
        try:
            await cur.execute("""
                ALTER TABLE `market_prices` ADD INDEX `idx_crawled_at` (`crawled_at`);
            """)
            print("Add idx_crawled_at index success")
        except:
            print("idx_crawled_at index may already exist, skip")
            
        if 'low_price' not in history_columns:
            await cur.execute("""
                ALTER TABLE `price_history` 
                ADD COLUMN `low_price` DECIMAL(10,2) NULL DEFAULT NULL COMMENT '最低价' AFTER `price`;
            """)
            print("Add low_price column success")
        else:
            print("low_price column already exists, skip")
            
        if 'high_price' not in history_columns:
            await cur.execute("""
                ALTER TABLE `price_history` 
                ADD COLUMN `high_price` DECIMAL(10,2) NULL DEFAULT NULL COMMENT '最高价' AFTER `low_price`;
            """)
            print("Add high_price column success")
        else:
            print("high_price column already exists, skip")
            
        await conn.commit()
        print("\nMigration completed")
        
    conn.close()


if __name__ == "__main__":
    asyncio.run(migrate())