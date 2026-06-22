-- ============================================================
-- 智能二手商品发布助手 - 数据库建表 DDL
-- 版本: v2.0
-- 数据库: MySQL 8.0+
-- ============================================================

CREATE DATABASE IF NOT EXISTS `market_transactions`
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE `market_transactions`;

-- ------------------------------------------------------------
-- 1. users - 用户信息表
-- ------------------------------------------------------------
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
  `id`            BIGINT       NOT NULL AUTO_INCREMENT COMMENT '用户唯一标识（主键）',
  `username`      VARCHAR(50)  NOT NULL                COMMENT '用户昵称或账号名',
  `password_hash` VARCHAR(128) NOT NULL DEFAULT ''     COMMENT 'PBKDF2 密码哈希（salt:hash）',
  `created_at`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '账号注册时间',
  `updated_at`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最近更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户信息表';

-- ------------------------------------------------------------
-- 2. market_prices - 二手行情基准表（核心引擎）
-- ------------------------------------------------------------
DROP TABLE IF EXISTS `market_prices`;
CREATE TABLE `market_prices` (
  `id`         BIGINT        NOT NULL AUTO_INCREMENT COMMENT '行情记录主键',
  `category`   VARCHAR(50)   NOT NULL                COMMENT '物品大类（如：手机、笔记本、外设）',
  `brand`      VARCHAR(50)   NOT NULL                COMMENT '品牌（如：Apple、罗技）',
  `model`      VARCHAR(100)  NOT NULL                COMMENT '具体型号（如：iPhone 13、G610）',
  `avg_price`  DECIMAL(10,2) NOT NULL                COMMENT '近期二手市场均价',
  `low_price`  DECIMAL(10,2) NOT NULL                COMMENT '近期二手市场最低参考价',
  `high_price` DECIMAL(10,2) NOT NULL                COMMENT '近期二手市场最高参考价',
  `created_at` DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
  `updated_at` DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最近更新时间',
  PRIMARY KEY (`id`),
  INDEX `idx_brand_model` (`brand`, `model`),
  INDEX `idx_category` (`category`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='二手行情基准表';

-- ------------------------------------------------------------
-- 3. published_items - 商品发布记录表（业务产物）
-- ------------------------------------------------------------
DROP TABLE IF EXISTS `published_items`;
CREATE TABLE `published_items` (
  `id`                 BIGINT        NOT NULL AUTO_INCREMENT COMMENT '发布记录主键',
  `user_id`            BIGINT        NOT NULL                COMMENT '发布者ID（关联users.id）',
  `original_image_url` VARCHAR(500)  NOT NULL                COMMENT '用户上传原图的本地存储路径',
  `ai_generated_title` VARCHAR(200)  NOT NULL DEFAULT ''     COMMENT 'AI生成的吸睛标题',
  `ai_generated_desc`  TEXT          NULL                    COMMENT 'AI生成的详细带货文案',
  `suggested_price`    DECIMAL(10,2) NULL                    COMMENT '系统结合行情给出的最终建议定价',
  `status`             VARCHAR(20)   NOT NULL DEFAULT 'draft' COMMENT '状态: draft-草稿, published-已发布, delisted-已下架',
  `created_at`         DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at`         DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最近更新时间',
  PRIMARY KEY (`id`),
  INDEX `idx_user_id` (`user_id`),
  INDEX `idx_status` (`status`),
  CONSTRAINT `fk_published_items_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='商品发布记录表';

-- ------------------------------------------------------------
-- 4. ai_audit_logs - AI调用审计表（黑匣子）
-- ------------------------------------------------------------
DROP TABLE IF EXISTS `ai_audit_logs`;
CREATE TABLE `ai_audit_logs` (
  `id`                BIGINT       NOT NULL AUTO_INCREMENT COMMENT '日志主键',
  `user_id`           BIGINT       NOT NULL                COMMENT '触发调用的用户ID',
  `action_type`       VARCHAR(30)  NOT NULL                COMMENT '调用类型: vision_extract-视觉提取, text_generate-生成文案',
  `model_name`        VARCHAR(50)  NOT NULL                COMMENT '使用的模型名称（如qwen-vl-max, deepseek-v4-pro）',
  `input_summary`     VARCHAR(500) NULL                    COMMENT '输入内容摘要（避免图片Base64撑爆字段）',
  `raw_ai_response`   JSON         NULL                    COMMENT '大模型返回的最原始完整内容（JSON类型，无惧格式变更）',
  `execution_time_ms` INT          NOT NULL DEFAULT 0      COMMENT '执行耗时（毫秒）',
  `status`            VARCHAR(10)  NOT NULL DEFAULT 'SUCCESS' COMMENT '执行状态: SUCCESS / FAILED',
  `error_message`     TEXT         NULL                    COMMENT '失败时的报错信息',
  `created_at`        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '日志创建时间',
  PRIMARY KEY (`id`),
  INDEX `idx_user_id` (`user_id`),
  INDEX `idx_status` (`status`),
  INDEX `idx_action_type` (`action_type`),
  INDEX `idx_created_at` (`created_at`),
  CONSTRAINT `fk_audit_logs_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI调用审计表';
