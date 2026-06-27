# 智能二手商品发布助手

> 面向二手商品交易的一站式 AI 发布平台。上传一张商品图片，AI 自动识别品类/品牌/型号/成色、查询市场行情、检测瑕疵并智能定价、流式生成带货文案，一键发布到商城。

---

## 📌 这是什么项目

这是一个**毕业设计作品**，目标是让普通用户用最低门槛发布二手商品——只需要**拍一张照片**，剩下的识别、查价、检测、定价、写文案全部由 AI 自动完成。

**解决的核心痛点：**

| 痛点 | 传统做法 | 本项目 |
|------|---------|--------|
| 不知道卖多少钱 | 手动去闲鱼/转转翻半天比价 | AI 自动查市场行情 + 智能定价 |
| 不会写商品描述 | 绞尽脑汁想文案、怕漏关键信息 | AI 自动生成专业带货文案，逐字流出 |
| 看不出商品瑕疵 | 肉眼检查，容易遗漏或夸大 | YOLOv8 分割模型自动检测 7 类缺陷 |
| 搜不到相似商品 | 纯文字搜标题，匹配不准确 | 以图搜图，上传图片直接找到最像的商品 |

**设计目标：** 用户上传图片 → AI 全自动处理 → 用户确认 → 一键发布。整个过程用户只需要点 3 次按钮。

---

## ✨ 功能列表

### 核心流程（发布一条商品）

| 步骤 | 功能 | 技术实现 |
|------|------|---------|
| ① 上传图片 | 支持 JPG/PNG/WEBP，最大 10MB，拖拽或点击上传 | FastAPI + 文件安全校验 |
| ② AI 识别 | 自动识别品类、品牌、型号、成色 | Qwen-VL-Max 多模态大模型 |
| ③ 查行情 | 品牌+型号查询二手市场均价、最低价、最高价 | MySQL 三层匹配（精确→模糊→空） |
| ④ 瑕疵检测 | 自动检测 7 类缺陷，4 级严重程度分级 | YOLOv8 分割模型（Kaputt 分类） |
| ⑤ 智能定价 | 结合瑕疵数据+行情数据给出建议售价 | DeepSeek 大模型推理 |
| ⑥ 生成文案 | 逐字流式输出带货文案，打字机效果 | DeepSeek SSE 流式生成 |
| ⑦ 一键发布 | 保存到商城，自动加入以图搜图索引 | MySQL 事务 + Qdrant 向量入库 |

### 商城系统

| 功能 | 说明 |
|------|------|
| 商品列表 | 多用户共享商城，按时间倒序，最多 100 条 |
| 搜索筛选 | 关键词模糊搜索（标题+描述）+ 品类精确筛选 |
| 点赞 | 事务保证点赞数一致性，防重复点赞 |
| 下架/发布 | 商品所有者可随时上下架 |

### 视觉能力

| 功能 | 说明 |
|------|------|
| 通用物品检测 | YOLOv8 80 类 COCO 预训练，画框标注 + Base64 输出 |
| 瑕疵分割检测 | 7 类 Kaputt 缺陷（穿透/变形/功能故障/结构损坏/溢漏/表面瑕疵/部件缺失） |
| 严重程度分级 | 4 级（重度红圆/中度橙方/轻度金多边/轻微蓝虚线），内部使用不告知用户 |
| 图像预处理 | 6 步管道：去噪→亮度增强→对比度→锐化→等比缩放→主体检测 |
| 去背景 | rembg (U²-Net) 像素级背景分离 |

### 以图搜图

| 功能 | 说明 |
|------|------|
| 以图搜图 | 上传图片 → CLIP 提取特征 → Qdrant 向量检索 → 返回相似商品 |
| 以文搜图 | 输入文字描述 → CLIP 文本编码 → 向量检索 → 返回匹配商品 |
| 自动索引 | 发布商品时自动提取特征入库，下架时自动删除索引 |

### 自我进化（数据飞轮）

```
用户使用 → YOLO 与 Qwen-VL 并行识别
    → 结果不一致时存入 hard_cases 错题本
    → 每周自动训练微调 YOLO 模型
    → 模型准确率持续提升
    → 减少对云端大模型的依赖（降低成本）
```

### 安全防护

| 机制 | 实现 |
|------|------|
| 用户认证 | JWT (HS256)，30 分钟过期 |
| 密码安全 | PBKDF2-SHA256，16 字节随机盐，10 万次迭代 |
| 速率限制 | 滑动窗口限流（注册 5/min、登录 10/min、识别 10/min、生成 20/min） |
| SQL 注入防护 | 全参数化查询 + ORDER BY 白名单映射 |
| 文件上传安全 | MIME 校验 + PIL 内容解码验证 + 路径遍历防护 |
| 身份防伪造 | user_id 从 JWT 解析，忽略客户端传值 |
| 安全响应头 | X-Content-Type-Options, X-Frame-Options, HSTS（生产环境） |

---

## 🛠️ 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| **后端框架** | Python 3.11 · FastAPI · Uvicorn | 异步 Web 框架，原生 async/await |
| **数据库** | MySQL 8.0 · aiomysql | 异步连接池，8 张表，参数化查询 |
| **向量搜索** | Qdrant · CLIP ViT-B-32 | 512 维语义向量，COSINE 相似度 |
| **前端** | Vue 3 · Vite · Tailwind CSS · Axios | Composition API，ESM 原生热更新 |
| **AI 大模型** | DeepSeek · Qwen-VL-Max | 文案生成+定价+视觉识别 |
| **目标检测** | YOLOv8 (ultralytics) | 分类 + 实例分割（Kaputt 7 类缺陷） |
| **特征提取** | CLIP (open_clip) · ViT-B-32 | 图文统一语义向量空间 |
| **图像处理** | OpenCV · Pillow · rembg | 6 步预处理管道 + 背景移除 |
| **认证安全** | JWT · PBKDF2 · 滑动窗口限流 | 无状态认证 + 加盐哈希 + 速率保护 |
| **异步工具** | aiofiles · httpx | 全链路非阻塞 IO |
| **测试** | pytest · pytest-asyncio | 12 个测试文件，29 个测试用例 |

### 系统架构

```
用户浏览器 (Vue 3 :5173)
       │
       ▼
FastAPI (:8000)
   │    │    │
   │    │    ├── SSE 流式 ────────▶ DeepSeek API（文案生成 + 定价）
   │    │    │
   │    │    └── HTTP ───────────▶ Qwen-VL-Max API（视觉识别）
   │    │
   │    ├── MySQL 8.0 (用户/商品/行情/审计/点赞/错题本)
   │    ├── Qdrant (CLIP 512维向量搜索)
   │    ├── YOLOv8 本地推理（物品检测 + 瑕疵分割）
   │    └── CLIP 本地推理（图文特征提取）
```

---

## 🚀 从零开始运行

### 你需要先装好这些

| 软件 | 版本 | 怎么检查 | 下载 |
|------|------|---------|------|
| Python | 3.10～3.11 | `python --version` | https://www.python.org/downloads/ （安装时勾选 Add to PATH） |
| Node.js | 18+ | `node --version` | https://nodejs.org/en/download |
| MySQL | 8.0+ | 开始菜单搜 MySQL | https://dev.mysql.com/downloads/installer/ （记住 root 密码） |
| Docker | 新版 | `docker --version` | https://www.docker.com/products/docker-desktop/ |

> 确保 MySQL 服务已启动（安装时勾选开机自启最省事）。

---

### 第 1 步：克隆项目

```bash
git clone <仓库地址>
cd Market-transactions
```

---

### 第 2 步：配置环境变量

```bash
copy backend\.env.example backend\.env
```

用记事本打开 `backend\.env`，**必须修改的 4 项：**

```ini
DEEPSEEK_API_KEY=sk-xxxxx        ← 去 https://platform.deepseek.com 注册获取
DASHSCOPE_API_KEY=sk-xxxxx       ← 去 https://dashscope.aliyun.com 注册获取
DB_PASSWORD=你的MySQL密码          ← 安装 MySQL 时设的那个
SECRET_KEY=随便乱敲30个字符         ← JWT 签名密钥
```

> 不填 API Key 不影响登录和商城浏览，但图片识别、文案生成会报错。

---

### 第 3 步：自动安装 PyTorch 及依赖

进入环境依赖项目，运行终端或者右键，**一定要进入环境依赖项目**。

在 Trae 终端运行：

```cmd
cd 环境依赖
pip install -r requirements.txt
python torchzidong.py
```

这个脚本会自动：
- 检测 CUDA 版本
- 安装匹配的 PyTorch（含 GPU 支持）
- 安装 `requirements.txt` 中的其他依赖
- 验证 GPU 是否可用

> **如果 pip 下载太慢**，可临时使用清华源（脚本已内置回退逻辑）。

---

### 第 4 步：创建数据库

```bash
mysql -u root -p < database\schema.sql
```

输入 MySQL 密码后自动建库建表（8 张表 + 16 条种子行情数据）。

验证：

```bash
mysql -u root -p -e "USE market_transactions; SHOW TABLES;"
```

应看到 8 张表：`users`, `market_prices`, `published_items`, `ai_audit_logs`, `item_likes`, `hard_cases`, `feature_vectors`, `price_history`

---

### 第 5 步：启动 Qdrant（向量搜索）

```bash
docker run -d -p 6333:6333 qdrant/qdrant
```

验证：浏览器打开 http://localhost:6333 能看到 Qdrant 管理界面。

---

### 第 6 步：启动后端

```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

看到以下输出说明成功：

```
INFO: Uvicorn running on http://0.0.0.0:8000
INFO: ✅ MySQL 连接池创建成功
INFO: ✅ 应用启动完成
```

验证：浏览器打开 http://localhost:8000/docs 查看 Swagger 文档。

---

### 第 7 步：安装前端依赖 + 启动前端

新开一个终端（不要关后端）：

```bash
cd frontend
npm install
npm run dev
```

> npm 慢的话：`npm config set registry https://registry.npmmirror.com`

验证：浏览器打开 http://localhost:5173

---

### 第 8 步：注册体验

1. 打开 http://localhost:5173
2. 点击「注册」→ 创建账号
3. 登录后上传一张商品图片
4. 依次点「识别」→「查价」→「生成文案」→「发布」
5. 去商城页面能看到刚发布的商品

---

## 📖 怎么用

### 发布一件商品（3 步）

| 步骤 | 操作 | 发生了什么 |
|------|------|-----------|
| **① 上传** | 拖拽或点击上传商品图片 | 后端调用 Qwen-VL 识别品类/品牌/型号/成色，同时 YOLO 做双模型比对 |
| **② 确认** | 查看识别结果，可手动修改，可选查价和瑕疵检测 | 查价返回市场均价，瑕疵检测返回标注图 + AI 建议价 |
| **③ 发布** | 点击生成，看文案逐字流出，确认后点发布 | SSE 流式文案 → 保存到数据库 → 自动加入以图搜图索引 → 商城可见 |

### 逛商城

打开 **商城页**（不需要登录），可以：
- 浏览所有用户发布的商品
- 输入关键词搜索（匹配标题和描述）
- 选择品类筛选
- 点击商品查看详情

### 管理我的发布

打开 **历史页**（需要登录），可以：
- 查看自己的草稿、已发布、已下架商品
- 发布草稿
- 下架已发布商品

### 以图搜图

在商城页上传图片或输入文字，找到最相似的商品，按相似度排序。

---

## ⚠️ 常见问题

| 问题 | 怎么办 |
|------|--------|
| `uvicorn` 找不到 | 没激活虚拟环境 → `.venv\Scripts\activate` |
| 后端报 `Can't connect to MySQL` | MySQL 服务没启动 → `net start MySQL80` |
| 后端报 `Access denied` | `.env` 里 `DB_PASSWORD` 填错了 |
| 识别/生成失败 | API Key 没填或余额不足 |
| 搜索报 500 | Qdrant 没启动 → `docker run -d -p 6333:6333 qdrant/qdrant` |
| 瑕疵检测返回 0 个 | 还没训练模型，需要 `defect_best.pt` |
| `npm install` 报错 | Node.js 版本太低，需要 18+ |
| 前端白屏 | 后端没开，检查 http://localhost:8000/ 能不能打开 |
| pip 安装包失败 | 换清华源：`pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple` |

---

## 📁 项目结构速览

```
Market-transactions/
├── backend/                    # FastAPI 后端（48 个 Python 文件）
│   ├── main.py                 #   入口
│   ├── app/
│   │   ├── routers/            #   9 个路由，17 个端点
│   │   ├── services/           #   6 个业务服务
│   │   ├── db/                 #   连接池 + CRUD
│   │   ├── llm/                #   DeepSeek / Qwen-VL 客户端
│   │   ├── ml/                 #   YOLOv8 / CLIP / Qdrant
│   │   ├── middleware/         #   速率限制
│   │   └── utils/              #   图像处理 / 校验 / 后台任务
│   └── test/                   #   12 个测试文件
├── frontend/                   # Vue 3 前端（14 个源文件）
│   └── src/views/              #   5 个页面
├── database/schema.sql         # 数据库建表
├── trainzui/                   # 模型训练脚本
├── 项目文档/                    # 详细文档
└── 环境依赖/                    # Python 依赖清单
```

---

## 🔌 端口一览

| 服务 | 端口 | 说明 |
|------|------|------|
| 后端 API | 8000 | FastAPI + Swagger docs |
| 前端 | 5173 | Vue 3 + Vite 开发服务器 |
| MySQL | 3306 | 业务数据库 |
| Qdrant | 6333 | 向量搜索 + 管理界面 |

---

## 📖 文档导航

| 文档 | 内容 |
|------|------|
| [前端设计接口](项目文档/前端设计接口.md) | 17 个 API 端点详细定义（请求/响应/错误码） |
| [数据库结构说明书](项目文档/数据库结构说明书.md) | 8 张表完整设计 |
| [核心技术与设计理念](项目文档/核心技术.md) | 10 项技术的原理+实现讲解 |
| [操作手册](项目文档/操作手册.md) | 详细操作步骤 |
| [版本迭代记录](项目文档/版本迭代记录.md) | v0.1～v0.16 开发历史 |
| [项目结构说明书](项目文档/项目结构说明书.md) | 完整目录树 |