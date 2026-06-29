-- ============================================================
-- 智能二手商品发布助手 — 数据库建表脚本
-- ============================================================
-- 使用方法（在新机器上）：
--   1. 安装 MySQL 8.0+
--   2. 打开终端，进入此文件所在目录
--   3. mysql -u root -p < schema.sql
--   4. 输入 root 密码，等待执行完成
-- ============================================================

-- 创建数据库
CREATE DATABASE IF NOT EXISTS `market_transactions`
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE `market_transactions`;

-- ============================================================
-- 1. users — 用户表
-- ============================================================
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `username` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `password_hash` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `email` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `phone` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `avatar_url` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'active',
  `role` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'user',
  `last_login` datetime DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`),
  KEY `idx_status` (`status`),
  KEY `idx_role` (`role`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 2. published_items — 已发布商品表
-- ============================================================
DROP TABLE IF EXISTS `published_items`;
CREATE TABLE `published_items` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL,
  `original_image_url` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL,
  `bg_removed_url` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `annotated_url` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `defect_count` int NOT NULL DEFAULT '0',
  `defect_types` json DEFAULT NULL,
  `defect_data` json DEFAULT NULL,
  `ai_generated_title` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `ai_generated_desc` text COLLATE utf8mb4_unicode_ci,
  `suggested_price` decimal(10,2) DEFAULT NULL,
  `category` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `brand` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `model` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `condition` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'draft',
  `review_status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'normal',
  `views` int NOT NULL DEFAULT '0',
  `likes` int NOT NULL DEFAULT '0',
  `retry_count` int NOT NULL DEFAULT '0',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_status` (`status`),
  KEY `idx_category` (`category`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_status_category` (`status`,`category`),
  KEY `idx_brand_model` (`brand`,`model`),
  KEY `idx_status_category_brand` (`status`,`category`,`brand`),
  CONSTRAINT `fk_pub_items_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 3. market_prices — 市场行情表
-- ============================================================
DROP TABLE IF EXISTS `market_prices`;
CREATE TABLE `market_prices` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `category` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `brand` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `model` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `avg_price` decimal(10,2) NOT NULL,
  `low_price` decimal(10,2) NOT NULL,
  `high_price` decimal(10,2) NOT NULL,
  `price_unit` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'CNY',
  `data_source` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_brand_model` (`brand`,`model`),
  KEY `idx_category` (`category`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 4. price_history — 价格历史表
-- ============================================================
DROP TABLE IF EXISTS `price_history`;
CREATE TABLE `price_history` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `brand` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `model` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `price` decimal(10,2) NOT NULL,
  `price_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'avg',
  `source` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `recorded_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_brand_model` (`brand`,`model`),
  KEY `idx_recorded_at` (`recorded_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 5. feature_vectors — 图片特征向量表（以图搜图）
-- ============================================================
DROP TABLE IF EXISTS `feature_vectors`;
CREATE TABLE `feature_vectors` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `item_id` bigint NOT NULL,
  `feature_vector` blob NOT NULL,
  `model_name` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'clip_ViT-B/32',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `item_id` (`item_id`),
  CONSTRAINT `fk_feature_item` FOREIGN KEY (`item_id`) REFERENCES `published_items` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 6. hard_cases — 模型错误案例表（数据飞轮）
-- ============================================================
DROP TABLE IF EXISTS `hard_cases`;
CREATE TABLE `hard_cases` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `image_url` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL,
  `wrong_label` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `correct_label` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `model_version` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `user_id` bigint DEFAULT NULL,
  `item_id` bigint DEFAULT NULL,
  `confidence` decimal(5,4) DEFAULT NULL,
  `retry_count` int NOT NULL DEFAULT '0',
  `is_fixed` tinyint(1) NOT NULL DEFAULT '0',
  `fixed_at` datetime DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_error_case` (`image_url`(255),`wrong_label`,`correct_label`),
  KEY `idx_wrong_label` (`wrong_label`),
  KEY `idx_correct_label` (`correct_label`),
  KEY `idx_is_fixed` (`is_fixed`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 7. ai_audit_logs — AI 调用审计日志表
-- ============================================================
DROP TABLE IF EXISTS `ai_audit_logs`;
CREATE TABLE `ai_audit_logs` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL,
  `action_type` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  `model_name` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `input_summary` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `raw_ai_response` json DEFAULT NULL,
  `execution_time_ms` int NOT NULL DEFAULT '0',
  `status` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'SUCCESS',
  `error_message` text COLLATE utf8mb4_unicode_ci,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_status` (`status`),
  KEY `idx_action_type` (`action_type`),
  KEY `idx_created_at` (`created_at`),
  CONSTRAINT `fk_audit_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 8. category_brands — 品类品牌对照表
-- ============================================================
DROP TABLE IF EXISTS `category_brands`;
CREATE TABLE `category_brands` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `category` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `brand` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_category_brand` (`category`,`brand`),
  KEY `idx_category` (`category`),
  KEY `idx_brand` (`brand`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 9. model_disagreements — 模型分歧记录表
-- ============================================================
DROP TABLE IF EXISTS `model_disagreements`;
CREATE TABLE `model_disagreements` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `image_url` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL,
  `yolo_category` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `yolo_model` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `qwen_category` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `qwen_model` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `qwen_brand` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `user_id` bigint DEFAULT NULL,
  `item_id` bigint DEFAULT NULL,
  `confidence` decimal(5,4) DEFAULT NULL,
  `is_used_for_training` tinyint(1) NOT NULL DEFAULT '0',
  `training_used_at` datetime DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_yolo_category` (`yolo_category`),
  KEY `idx_qwen_category` (`qwen_category`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_is_used_for_training` (`is_used_for_training`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 10. model_metrics — 模型训练指标表
-- ============================================================
DROP TABLE IF EXISTS `model_metrics`;
CREATE TABLE `model_metrics` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `model_name` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `training_date` datetime NOT NULL,
  `accuracy` decimal(5,4) DEFAULT NULL,
  `precision` decimal(5,4) DEFAULT NULL,
  `recall` decimal(5,4) DEFAULT NULL,
  `f1_score` decimal(5,4) DEFAULT NULL,
  `training_data_count` int DEFAULT NULL,
  `epoch` int DEFAULT NULL,
  `notes` text COLLATE utf8mb4_unicode_ci,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_model_name` (`model_name`),
  KEY `idx_training_date` (`training_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 11. notifications — 通知表
-- ============================================================
DROP TABLE IF EXISTS `notifications`;
CREATE TABLE `notifications` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL,
  `item_id` bigint DEFAULT NULL,
  `type` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  `title` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `message` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `is_read` tinyint(1) NOT NULL DEFAULT '0',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_is_read` (`is_read`),
  KEY `idx_created_at` (`created_at`),
  CONSTRAINT `fk_notif_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
