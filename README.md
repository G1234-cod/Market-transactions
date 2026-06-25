
# 智能二手商品发布助手

> AI 驱动的二手商品发布平台 —— 拍照即可自动生成商品信息、检测瑕疵、智能定价、一键发布


## 📖 项目简介

**一句话概括：让二手商品发布像拍照一样简单。**

用户只需上传一张商品图片，系统自动完成：

| 功能 | 说明 |
|:---|:---|
| 🖼️ **商品识别** | YOLO + Qwen 双模型并行识别品类/品牌/型号 |
| 🔍 **瑕疵检测** | 检测划痕/磕碰/污渍/裂痕/掉漆，用不同形状和颜色标注程度 |
| 💰 **智能定价** | DeepSeek 结合瑕疵程度和市场行情给出建议售价 |
| 📝 **自动文案** | AI 生成标题、描述，一键发布 |
| 🔎 **以图搜图** | CLIP + Qdrant 支持图搜图和文搜图 |
| 🔄 **持续进化** | 错误数据自动收集，每周迭代训练 |


## 🛠️ 技术栈

| 层级 | 技术 |
|:---|:---|
| 后端框架 | FastAPI |
| 前端框架 | Vue 3 + TailwindCSS |
| 数据库 | MySQL + Qdrant (向量数据库) |
| 目标检测 | YOLOv8 |
| 多模态检索 | CLIP |
| 大模型 | Qwen-VL (视觉识别) + DeepSeek (文案/定价) |
| 图像处理 | rembg + OpenCV |
| 深度学习 | PyTorch |


## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              前端（Vue 3）                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            API 层（FastAPI）                               │
│   /auth   /extract   /detect   /process   /search   /price   /history     │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            业务逻辑层                                       │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐            │
│  │ 用户系统 │ │ 图片处理 │ │ 瑕疵检测 │ │ 以图搜图 │ │ 数据飞轮 │            │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘            │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AI 模型层                                     │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐            │
│  │ YOLOv8  │ │  CLIP   │ │  Qwen   │ │ DeepSeek│ │  rembg  │            │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘            │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                             存储层                                         │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐                  │
│  │    MySQL      │  │    Qdrant     │  │   静态图片    │                  │
│  │   业务数据     │  │   向量索引    │  │   文件存储    │                  │
│  └───────────────┘  └───────────────┘  └───────────────┘                  │
└─────────────────────────────────────────────────────────────────────────────┘
```


## 📁 项目结构

```
Market-transactions/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── config.py            # 配置文件
│   │   ├── db/                  # 数据库层
│   │   ├── llm/                 # LLM 客户端 (Qwen/DeepSeek)
│   │   ├── models/              # Pydantic 数据模型
│   │   ├── routers/             # API 路由
│   │   ├── ml/                  # 机器学习模块
│   │   ├── services/            # 业务服务
│   │   └── utils/               # 工具函数
│   ├── static/uploads/          # 图片存储
│   ├── data/                    # 错误数据/索引
│   ├── train/                   # 训练脚本
│   ├── scripts/                 # 辅助脚本
│   ├── tests/                   # 单元测试
│   ├── sql/                     # 数据库脚本
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/                 # API 封装
│   │   ├── components/          # Vue 组件
│   │   ├── store/               # 状态管理
│   │   └── views/               # 页面视图
│   └── package.json
└── README.md
```


## 🚀 快速开始


### 后端启动

```bash
# 1. 进入后端目录
cd backend

# 2. 创建并激活虚拟环境
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置 .env（复制 .env.example 并填写配置）
cp .env.example .env

# 5. 创建数据库
mysql -u root -p < sql/schema.sql

# 6. 启动服务
uvicorn main:app --reload
```

### 前端启动

```bash
# 1. 进入前端目录
cd frontend

# 2. 安装依赖
npm install

# 3. 启动开发服务器
npm run dev
```

### 访问地址

| 服务 | 地址 |
|:---|:---|
| 后端 API | http://localhost:8000 |
| Swagger 文档 | http://localhost:8000/docs |
| 前端页面 | http://localhost:5173 |
| Qdrant 管理 | http://localhost:6333 |


## 📋 API 接口

| 模块 | 接口 | 方法 | 说明 |
|:---|:---|:---:|:---|
| 用户 | `/register` | POST | 注册 |
| 用户 | `/login` | POST | 登录 |
| 识别 | `/extract` | POST | Qwen 视觉识别 |
| 检测 | `/yolo/detect` | POST | YOLO 物品检测 |
| 瑕疵 | `/process/image` | POST | 全链路图片处理 |
| 搜图 | `/search/image` | POST | 以图搜图 |
| 搜图 | `/search/text` | POST | 以文搜图 |
| 价格 | `/price` | GET | 行情查询 |
| 历史 | `/history` | GET | 发布历史 |
| 历史 | `/history/save` | POST | 保存发布记录 |
| 商城 | `/market` | GET | 商品列表 |


## 📊 核心流程

```
用户上传图片
    ↓
图片预处理（尺寸统一 + 去背景 + 去噪）
    ↓
    ├── 物品识别（YOLO + Qwen 并行）
    │       ↓
    │   双模型比对 → 不一致 → 保存错误数据
    │
    ├── 瑕疵检测（YOLO）
    │       ↓
    │   画框标注（不同形状+颜色代表不同程度）
    │       ↓
    │   DeepSeek 定价（结合瑕疵程度 + 市场行情）
    │
    └── 以图搜图（CLIP 特征提取 + Qdrant 检索）
    ↓
自动填充标题 + 描述 + 价格 + 瑕疵标注图
    ↓
用户确认 → 一键发布到商城
```


## 🔧 环境变量

```env
# DeepSeek API
DEEPSEEK_API_KEY=your_api_key
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat

# Qwen API
DASHSCOPE_API_KEY=your_api_key
QWEN_VL_MODEL=qwen-vl-max

# MySQL
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=market_transactions

# 图片上传
UPLOAD_DIR=static/uploads
```


## 🧪 测试

```bash
# 安装测试依赖
pip install pytest pytest-asyncio pytest-cov httpx

# 运行测试
pytest backend/test/ -v

# 生成覆盖率报告
pytest backend/test/ --cov=app --cov-report=html
```


## 👥 团队

| 角色 | 职责 |
|:---|:---|
| 后端开发 | FastAPI + AI 模型集成 + 数据库 |
| 前端开发 | Vue 3 + TailwindCSS |
| AI 训练 | YOLO 模型训练（通用识别 + 瑕疵检测） |


## 📄 许可证

MIT License


## 🙏 致谢

- [Ultralytics YOLO](https://github.com/ultralytics/ultralytics) - 目标检测框架
- [OpenAI CLIP](https://github.com/openai/CLIP) - 多模态检索
- [Qdrant](https://github.com/qdrant/qdrant) - 向量数据库
- [FastAPI](https://fastapi.tiangolo.com/) - Web 框架
- [Vue 3](https://vuejs.org/) - 前端框架


## 📞 联系方式

遇到问题请提交 Issue 或联系项目维护者。

---

**⭐ 如果这个项目对你有帮助，请给一个 Star！**