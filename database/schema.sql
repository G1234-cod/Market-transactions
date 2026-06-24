-- ============================================================
-- 智能二手商品发布助手 - 完整数据库建表
-- ============================================================

CREATE DATABASE IF NOT EXISTS `market_transactions`
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE `market_transactions`;

-- ------------------------------------------------------------
-- 1. users - 用户表
-- ------------------------------------------------------------
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
  `id`            BIGINT       NOT NULL AUTO_INCREMENT COMMENT '用户ID',
  `username`      VARCHAR(50)  NOT NULL UNIQUE                COMMENT '用户名',
  `password_hash` VARCHAR(128) NOT NULL DEFAULT ''             COMMENT '密码哈希',
  `email`         VARCHAR(100) NULL     DEFAULT NULL          COMMENT '邮箱',
  `phone`         VARCHAR(20)  NULL     DEFAULT NULL          COMMENT '手机号',
  `avatar_url`    VARCHAR(500) NULL     DEFAULT NULL          COMMENT '头像URL',
  `status`        VARCHAR(20)  NOT NULL DEFAULT 'active'      COMMENT '状态: active/inactive/locked/deleted',
  `role`          VARCHAR(20)  NOT NULL DEFAULT 'user'        COMMENT '角色: user/admin',
  `last_login`    DATETIME     NULL     DEFAULT NULL          COMMENT '最后登录时间',
  `created_at`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '注册时间',
  `updated_at`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  INDEX `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- ------------------------------------------------------------
-- 2. market_prices - 二手行情基准表
-- ------------------------------------------------------------
DROP TABLE IF EXISTS `market_prices`;
CREATE TABLE `market_prices` (
  `id`          BIGINT        NOT NULL AUTO_INCREMENT COMMENT '行情ID',
  `category`    VARCHAR(50)   NOT NULL                COMMENT '品类',
  `brand`       VARCHAR(50)   NOT NULL                COMMENT '品牌',
  `model`       VARCHAR(100)  NOT NULL                COMMENT '型号',
  `avg_price`   DECIMAL(10,2) NOT NULL                COMMENT '均价',
  `low_price`   DECIMAL(10,2) NOT NULL                COMMENT '最低参考价',
  `high_price`  DECIMAL(10,2) NOT NULL                COMMENT '最高参考价',
  `price_unit`  VARCHAR(10)   NOT NULL DEFAULT 'CNY'  COMMENT '货币单位',
  `data_source` VARCHAR(50)   NULL     DEFAULT NULL   COMMENT '数据来源',
  `is_active`   TINYINT(1)    NOT NULL DEFAULT 1      COMMENT '是否启用',
  `created_at`  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at`  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_brand_model` (`brand`, `model`),
  INDEX `idx_category` (`category`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='二手行情基准表';

-- ------------------------------------------------------------
-- 3. published_items - 商品发布表（核心业务表）
-- ------------------------------------------------------------
DROP TABLE IF EXISTS `published_items`;
CREATE TABLE `published_items` (
  `id`                 BIGINT        NOT NULL AUTO_INCREMENT COMMENT '商品ID',
  `user_id`            BIGINT        NOT NULL                COMMENT '发布者ID',
  `original_image_url` VARCHAR(500)  NOT NULL                COMMENT '原始图片URL',
  `bg_removed_url`     VARCHAR(500)  NULL     DEFAULT NULL   COMMENT '去背景图URL',
  `annotated_url`      VARCHAR(500)  NULL     DEFAULT NULL   COMMENT '标注图URL',
  `defect_count`       INT           NOT NULL DEFAULT 0      COMMENT '瑕疵数量',
  `defect_types`       JSON          NULL     DEFAULT NULL   COMMENT '瑕疵类型列表',
  `defect_data`        JSON          NULL     DEFAULT NULL   COMMENT '瑕疵详细数据(位置/程度)',
  `ai_generated_title` VARCHAR(200)  NOT NULL DEFAULT ''     COMMENT 'AI生成标题',
  `ai_generated_desc`  TEXT          NULL                    COMMENT 'AI生成描述',
  `suggested_price`    DECIMAL(10,2) NULL     DEFAULT NULL   COMMENT '建议价格',
  `category`           VARCHAR(50)   NULL     DEFAULT NULL   COMMENT '品类',
  `item_condition`     VARCHAR(20)   NOT NULL DEFAULT 'unknown' COMMENT '成色',
  `status`             VARCHAR(20)   NOT NULL DEFAULT 'draft' COMMENT 'draft/published/hidden/sold/deleted',
  `views`              INT           NOT NULL DEFAULT 0      COMMENT '浏览次数',
  `likes`              INT           NOT NULL DEFAULT 0      COMMENT '点赞数',
  `created_at`         DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at`         DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  INDEX `idx_user_id` (`user_id`),
  INDEX `idx_status` (`status`),
  INDEX `idx_category` (`category`),
  CONSTRAINT `fk_published_items_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='商品发布表';

-- ------------------------------------------------------------
-- 4. ai_audit_logs - AI审计日志表
-- ------------------------------------------------------------
DROP TABLE IF EXISTS `ai_audit_logs`;
CREATE TABLE `ai_audit_logs` (
  `id`                BIGINT       NOT NULL AUTO_INCREMENT COMMENT '日志ID',
  `user_id`           BIGINT       NOT NULL                COMMENT '用户ID',
  `action_type`       VARCHAR(30)  NOT NULL                COMMENT 'vision_extract/text_generate/price_query',
  `model_name`        VARCHAR(50)  NOT NULL                COMMENT '模型名称',
  `input_summary`     VARCHAR(500) NULL                    COMMENT '输入摘要',
  `raw_ai_response`   JSON         NULL                    COMMENT 'AI原始响应',
  `execution_time_ms` INT          NOT NULL DEFAULT 0      COMMENT '耗时(毫秒)',
  `status`            VARCHAR(10)  NOT NULL DEFAULT 'SUCCESS' COMMENT 'SUCCESS/FAILED',
  `error_message`     TEXT         NULL                    COMMENT '错误信息',
  `created_at`        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  INDEX `idx_user_id` (`user_id`),
  INDEX `idx_status` (`status`),
  INDEX `idx_action_type` (`action_type`),
  INDEX `idx_created_at` (`created_at`),
  CONSTRAINT `fk_audit_logs_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI审计日志表';

-- ------------------------------------------------------------
-- 5. item_likes - 点赞记录表
-- ------------------------------------------------------------
DROP TABLE IF EXISTS `item_likes`;
CREATE TABLE `item_likes` (
  `id`         BIGINT   NOT NULL AUTO_INCREMENT COMMENT '点赞ID',
  `item_id`    BIGINT   NOT NULL                COMMENT '商品ID',
  `user_id`    BIGINT   NOT NULL                COMMENT '用户ID',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '点赞时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_item_user` (`item_id`, `user_id`),
  INDEX `idx_item_id` (`item_id`),
  INDEX `idx_user_id` (`user_id`),
  CONSTRAINT `fk_likes_item` FOREIGN KEY (`item_id`) REFERENCES `published_items` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_likes_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='点赞记录表';

-- ------------------------------------------------------------
-- 6. hard_cases - 错题本（错误数据收集）
-- ------------------------------------------------------------
DROP TABLE IF EXISTS `hard_cases`;
CREATE TABLE `hard_cases` (
  `id`            BIGINT       NOT NULL AUTO_INCREMENT COMMENT '错题ID',
  `image_url`     VARCHAR(500) NOT NULL                COMMENT '错误图片URL',
  `wrong_label`   VARCHAR(100) NOT NULL                COMMENT '本地模型错误分类',
  `correct_label` VARCHAR(100) NOT NULL                COMMENT 'Qwen正确分类',
  `model_version` VARCHAR(50)  NULL     DEFAULT NULL   COMMENT '当时模型版本',
  `user_id`       BIGINT       NULL     DEFAULT NULL   COMMENT '触发用户ID',
  `item_id`       BIGINT       NULL     DEFAULT NULL   COMMENT '关联商品ID',
  `is_fixed`      TINYINT(1)   NOT NULL DEFAULT 0      COMMENT '是否已修复',
  `fixed_at`      DATETIME     NULL     DEFAULT NULL   COMMENT '修复时间',
  `created_at`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  INDEX `idx_wrong_label` (`wrong_label`),
  INDEX `idx_correct_label` (`correct_label`),
  INDEX `idx_is_fixed` (`is_fixed`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='错题本';

-- ------------------------------------------------------------
-- 7. feature_vectors - 特征向量表（以图搜图）
-- ------------------------------------------------------------
DROP TABLE IF EXISTS `feature_vectors`;
CREATE TABLE `feature_vectors` (
  `id`             BIGINT       NOT NULL AUTO_INCREMENT COMMENT '特征ID',
  `item_id`        BIGINT       NOT NULL UNIQUE           COMMENT '商品ID',
  `feature_vector` BLOB         NOT NULL                COMMENT '特征向量(二进制)',
  `model_name`     VARCHAR(50)  NOT NULL DEFAULT 'mobilenet_v3' COMMENT '特征提取模型',
  `created_at`     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at`     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  CONSTRAINT `fk_feature_item` FOREIGN KEY (`item_id`) REFERENCES `published_items` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='特征向量表';

-- ------------------------------------------------------------
-- 8. price_history - 价格历史表
-- ------------------------------------------------------------
DROP TABLE IF EXISTS `price_history`;
CREATE TABLE `price_history` (
  `id`          BIGINT        NOT NULL AUTO_INCREMENT COMMENT '历史ID',
  `brand`       VARCHAR(50)   NOT NULL                COMMENT '品牌',
  `model`       VARCHAR(100)  NOT NULL                COMMENT '型号',
  `price`       DECIMAL(10,2) NOT NULL                COMMENT '价格',
  `price_type`  VARCHAR(20)   NOT NULL DEFAULT 'avg'  COMMENT 'avg/low/high',
  `source`      VARCHAR(50)   NULL     DEFAULT NULL   COMMENT '数据来源',
  `recorded_at` DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录时间',
  PRIMARY KEY (`id`),
  INDEX `idx_brand_model` (`brand`, `model`),
  INDEX `idx_recorded_at` (`recorded_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='价格历史表';

-- ------------------------------------------------------------
-- 9. 测试数据
-- ------------------------------------------------------------

-- 测试用户（密码：test123）
INSERT INTO `users` (`username`, `password_hash`) VALUES ('test_user', '');

-- 行情数据
INSERT INTO `market_prices` (`category`, `brand`, `model`, `avg_price`, `low_price`, `high_price`) VALUES
('手机', 'Apple', 'iPhone 13', 3200.00, 2800.00, 3800.00),
('手机', 'Apple', 'iPhone 14', 4100.00, 3600.00, 4700.00),
('手机', 'HUAWEI', 'Mate 40 Pro', 2500.00, 2000.00, 3100.00),
('笔记本', 'Apple', 'MacBook Air M1', 4200.00, 3500.00, 5000.00),
('笔记本', 'Lenovo', 'ThinkPad X1', 3500.00, 2800.00, 4300.00),
('平板', 'Apple', 'iPad Air 5', 3000.00, 2500.00, 3600.00),
('外设', 'Logitech', 'G610 机械键盘', 220.00, 150.00, 300.00),
('耳机', 'Apple', 'AirPods Pro 2', 1000.00, 800.00, 1300.00);

-- ------------------------------------------------------------
-- 10. 验证
-- ------------------------------------------------------------
-- SHOW TABLES;
-- SELECT * FROM users;
-- SELECT * FROM market_prices;
-- SELECT COUNT(*) FROM published_items;
-- SELECT COUNT(*) FROM hard_cases;