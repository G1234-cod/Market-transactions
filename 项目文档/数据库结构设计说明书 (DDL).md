# 数据库结构设计说明书 (DDL)

下面详细说明 4 张核心业务表的结构、作用及工程设计意图。

## 表关系总览

```
users (1) ──┬── (N) published_items
            └── (N) ai_audit_logs

market_prices (独立只读，由后端查询匹配)
```

---

### 1. `users` (用户信息表)

- **作用：** 系统的账号基石。所有商品发布、AI 调用行为均绑定到具体用户。
- **核心结构：**

| **字段名**      | **数据类型**     | **作用说明**                       |
| --------------- | ---------------- | ---------------------------------- |
| `id`            | BIGINT AUTO_INCREMENT | 用户唯一标识（主键）。         |
| `username`      | VARCHAR(50)      | 用户昵称或账号名。                 |
| `password_hash` | VARCHAR(128)     | PBKDF2-SHA256 密码哈希（格式：`salt:hash`）。 |
| `created_at`    | DATETIME         | 账号注册时间。                     |
| `updated_at`    | DATETIME         | 最近更新时间，`ON UPDATE CURRENT_TIMESTAMP`。 |

- **工程视角：** 通过 PBKDF2-SHA256（100,000 迭代 + 16 字节随机 salt）哈希存储密码，无法反推明文。提供 `POST /api/v1/register` 注册 + `POST /api/v1/login` 登录鉴权。前端登录/注册页使用 Vue Router 路由守卫实现未登录拦截。

---

### 2. `market_prices` (二手行情基准表 —— 核心引擎)

- **作用：** 系统的"内部物价局"。大模型负责识别物品，后端拿识别结果来此表匹配真实市场行情。
- **核心结构：**

| **字段名**   | **数据类型**         | **作用说明**                           |
| ------------ | -------------------- | -------------------------------------- |
| `id`         | BIGINT AUTO_INCREMENT | 行情记录主键。                         |
| `category`   | VARCHAR(50)          | 物品大类（如：手机、笔记本、外设）。   |
| `brand`      | VARCHAR(50)          | 品牌（如：Apple、罗技）。              |
| `model`      | VARCHAR(100)         | 具体型号（如：iPhone 13、G610）。      |
| `avg_price`  | DECIMAL(10,2)        | 近期二手市场**均价**。                 |
| `low_price`  | DECIMAL(10,2)        | 近期二手市场最低参考价。               |
| `high_price` | DECIMAL(10,2)        | 近期二手市场最高参考价。               |
| `created_at` | DATETIME             | 记录创建时间。                         |
| `updated_at` | DATETIME             | 最近更新时间。                         |

- **索引设计：**
  - 联合索引 `idx_brand_model (brand, model)` —— 查价高频路径。
- **工程视角：** 该表对 C 端用户为**只读**。开发前期手动灌入 20-30 条校园常见二手物品数据。查询时优先精确匹配，未命中则用 `difflib` 模糊匹配。

---

### 3. `published_items` (商品发布记录表 —— 业务产物)

- **作用：** 记录 AI 生成的最终成果。用户可在"我的发布历史"页面查阅。
- **核心结构：**

| **字段名**           | **数据类型**         | **作用说明**                                       |
| -------------------- | -------------------- | -------------------------------------------------- |
| `id`                 | BIGINT AUTO_INCREMENT | 发布记录主键。                                     |
| `user_id`            | BIGINT               | 发布者 ID（关联 `users.id`）。                     |
| `original_image_url` | VARCHAR(500)         | 用户上传原图的本地存储路径。                       |
| `ai_generated_title` | VARCHAR(200)         | AI 生成的吸睛标题（如："99新女生自用iPhone13..."）。|
| `ai_generated_desc`  | TEXT                 | AI 生成的详细带货文案。                            |
| `suggested_price`    | DECIMAL(10,2)        | 系统结合行情给出的最终建议定价。                   |
| `status`             | VARCHAR(20)          | 当前状态（如：`draft`-草稿, `published`-已发布, `delisted`-已下架）。 |
| `created_at`         | DATETIME             | 创建时间。                                         |
| `updated_at`         | DATETIME             | 最近更新时间。                                     |

- **索引设计：**
  - 普通索引 `idx_user_id (user_id)` —— 按用户查询发布历史。
  - 普通索引 `idx_status (status)` —— 按状态筛选。
- **工程视角：** `status` 用 `VARCHAR` 而非 `TINYINT`，语义明确、免去魔法数字的维护成本。

---

### 4. `ai_audit_logs` (AI 调用审计表 —— 面试亮点)

- **作用：** 系统的"黑匣子"。记录每次大模型调用的完整过程，用于 Bug 排查、成本分析和安全审计。
- **核心结构：**

| **字段名**          | **数据类型**         | **作用说明**                                               |
| ------------------- | -------------------- | ---------------------------------------------------------- |
| `id`                | BIGINT AUTO_INCREMENT | 日志主键。                                                 |
| `user_id`           | BIGINT               | 触发调用的用户 ID。                                        |
| `action_type`       | VARCHAR(30)          | 调用类型（如：`vision_extract`-视觉提取, `text_generate`-生成文案）。 |
| `model_name`        | VARCHAR(50)          | 使用的模型名称（如 `qwen-vl-max`, `deepseek-v4-pro`）。     |
| `input_summary`     | VARCHAR(500)         | 输入内容摘要（避免图片 Base64 撑爆字段）。                  |
| `raw_ai_response`   | JSON                 | 大模型返回的**最原始完整内容**。JSON 类型，无惧格式变更。  |
| `execution_time_ms` | INT                  | 执行耗时（毫秒），用于性能分析。                           |
| `status`            | VARCHAR(10)          | 执行状态（`SUCCESS` / `FAILED`）。                         |
| `error_message`     | TEXT                 | 失败时的报错信息（`NULLABLE`）。                           |
| `created_at`        | DATETIME             | 日志创建时间。                                             |

- **索引设计：**
  - 普通索引 `idx_user_id (user_id)` —— 按用户追踪调用。
  - 普通索引 `idx_status (status)` —— 快速筛选失败记录。
  - 普通索引 `idx_action_type (action_type)` —— 按调用类型分析。
  - 普通索引 `idx_created_at (created_at)` —— 按时间范围检索。
- **工程视角：** 
  - `raw_ai_response` 存 JSON 原生报文，未来模型输出格式变化时无需改表结构，扩展性极强。
  - `input_summary` 存文字摘要而非原始图片 Base64，避免数据库急剧膨胀。
  - `model_name` 字段记录具体模型，便于多模型场景下的成本归因。

---

## 数据流转闭环

```
1. 用户（users）注册/登录
2. AI 提取特征 → 查行情（market_prices）
3. 用户确认 → AI 生成文案 → 存入发布记录（published_items）
4. 全过程被审计日志记录（ai_audit_logs）
5. 商城（market）展示所有用户已发布商品
```
