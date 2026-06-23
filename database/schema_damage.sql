-- ============================================================
-- 损伤检测功能 - 数据库增量 DDL
-- 版本: v1.0
-- ============================================================

USE `market_transactions`;

-- ------------------------------------------------------------
-- 1. damage_detections - 损伤检测记录表
-- ------------------------------------------------------------
DROP TABLE IF EXISTS `damage_detections`;
CREATE TABLE `damage_detections` (
  `id`                    BIGINT       NOT NULL AUTO_INCREMENT COMMENT '检测记录主键',
  `published_item_id`     BIGINT       NULL                    COMMENT '关联的发布记录ID（关联published_items.id）',
  `original_image_url`    VARCHAR(500)  NOT NULL                COMMENT '原图路径',
  `annotated_image_url`   VARCHAR(500)  NOT NULL                COMMENT '标注后图片路径',
  `total_regions`        INT          NOT NULL DEFAULT 0       COMMENT '检测到的损伤区域总数',
  `has_damage`           TINYINT(1)   NOT NULL DEFAULT 0       COMMENT '是否有损伤: 0-无, 1-有',
  `created_at`           DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  INDEX `idx_published_item_id` (`published_item_id`),
  INDEX `idx_has_damage` (`has_damage`),
  CONSTRAINT `fk_damage_detections_item` FOREIGN KEY (`published_item_id`)
    REFERENCES `published_items` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='损伤检测记录表';

-- ------------------------------------------------------------
-- 2. damage_regions - 损伤区域详情表
-- ------------------------------------------------------------
DROP TABLE IF EXISTS `damage_regions`;
CREATE TABLE `damage_regions` (
  `id`                  BIGINT       NOT NULL AUTO_INCREMENT COMMENT '损伤区域主键',
  `detection_id`       BIGINT       NOT NULL                COMMENT '所属检测记录ID（关联damage_detections.id）',
  `damage_type`        VARCHAR(20)  NOT NULL                COMMENT '损伤类型: scratch/dent/crack/stain/other',
  `confidence`         DECIMAL(5,4) NOT NULL                COMMENT '置信度 0-1',
  `polygon_coords`     JSON         NOT NULL                COMMENT '多边形顶点坐标 JSON',
  `created_at`         DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  INDEX `idx_detection_id` (`detection_id`),
  INDEX `idx_damage_type` (`damage_type`),
  CONSTRAINT `fk_damage_regions_detection` FOREIGN KEY (`detection_id`)
    REFERENCES `damage_detections` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='损伤区域详情表';
