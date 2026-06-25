# 📦 Docker 配置与每周自动训练完整指南

> 给兄弟的 Docker 信息与操作指南


## 一、Docker 是什么？

**一句话说明：** Docker 是一个软件集装箱工具，让你**不用手动安装 Qdrant 数据库**，一条命令就能启动。


## 二、Qdrant 镜像信息

| 项目 | 信息 |
|:---|:---|
| 镜像名称 | `qdrant/qdrant` |
| 镜像版本 | `latest` |
| 内部端口 | `6333` |
| 映射端口 | `6333` |
| 数据卷路径 | `D:/Market-train/backend/data/qdrant` |


## 三、完整操作步骤

### 第 1 步：安装 Docker

**Windows 用户：**

1. 打开浏览器，访问 [docker.com](https://www.docker.com/products/docker-desktop/)
2. 点击 **Download for Windows**
3. 下载后双击安装
4. 安装时**勾选 "Use WSL 2 instead of Hyper-V"**
5. 安装完成后**重启电脑**

**验证安装：**
```bash
docker --version
```

### 第 2 步：创建数据目录

```bash
# 进入项目目录
cd D:\Market-train

# 创建 Qdrant 数据目录
mkdir -p backend/data/qdrant
```

### 第 3 步：拉取并启动 Qdrant

```bash
# 拉取镜像（约 50MB）
docker pull qdrant/qdrant:latest

# 启动容器
docker run -d -p 6333:6333 -v D:/Market-train/backend/data/qdrant:/qdrant/storage qdrant/qdrant:latest
```

### 第 4 步：验证是否启动成功

```bash
# 查看容器状态
docker ps

# 健康检查
curl http://localhost:6333/healthz
```


## 四、常用 Docker 命令

| 用途 | 命令 |
|:---|:---|
| 查看运行状态 | `docker ps` |
| 查看所有容器 | `docker ps -a` |
| 查看日志 | `docker logs -f <容器ID>` |
| 停止容器 | `docker stop <容器ID>` |
| 启动容器 | `docker start <容器ID>` |
| 重启容器 | `docker restart <容器ID>` |
| 删除容器 | `docker rm <容器ID>` |
| 查看镜像列表 | `docker images` |


## 五、常见问题与解决

| 问题 | 解决办法 |
|:---|:---|
| `docker: command not found` | Docker 没安装或没加到 PATH，重新安装 |
| `port is already allocated` | 端口被占用，换一个端口 `-p 6334:6333` |
| `permission denied` | 用管理员权限运行 PowerShell |
| 容器启动后立即退出 | 查看日志 `docker logs <容器ID>` |


## 六、验证 Qdrant API 是否正常

```bash
# 创建测试 collection
curl -X PUT "http://localhost:6333/collections/test" \
  -H "Content-Type: application/json" \
  -d '{"vectors": {"size": 512, "distance": "Cosine"}}'
```


## 七、Python 连接测试

```python
from qdrant_client import QdrantClient

client = QdrantClient(host="localhost", port=6333)
print(client.get_collections())
```


## 八、一键复制执行

```bash
# ========== 全部执行 ==========

# 1. 验证 Docker
docker --version

# 2. 创建目录
mkdir -p D:/Market-train/backend/data/qdrant

# 3. 拉取镜像
docker pull qdrant/qdrant:latest

# 4. 启动容器
docker run -d -p 6333:6333 -v D:/Market-train/backend/data/qdrant:/qdrant/storage qdrant/qdrant:latest

# 5. 验证
docker ps
curl http://localhost:6333/healthz
```


## 九、以图搜图索引

```bash
# 进入 backend 目录
cd D:\Market-train\backend

# 激活虚拟环境
..\.venv\Scripts\activate

# 首次运行批量索引（把已有商品入库）
python scripts/index_items.py --all
```


## 十、每周自动训练设置（Windows 任务计划器）

### ① 创建批处理脚本

新建文件 `D:\Market-train\run_weekly_train.bat`：

```bat
@echo off
echo [%date% %time%] 开始每周训练 >> D:\Market-train\logs\train.log

cd /d D:\Market-train\backend
call ..\.venv\Scripts\activate
python scripts/weekly_train.py >> D:\Market-train\logs\train.log 2>&1

echo [%date% %time%] 训练完成 >> D:\Market-train\logs\train.log
```

创建日志目录：
```bash
mkdir D:\Market-train\logs
```

### ② 打开任务计划器

按 `Win + R`，输入 `taskschd.msc`，回车

### ③ 创建基本任务

1. 点击右侧 **创建基本任务**
2. 名称：`每周模型训练`
3. 触发器：每周一 02:00
4. 操作：启动程序 → 浏览选择 `D:\Market-train\run_weekly_train.bat`

### ④ 修改属性

- 勾选 **不管用户是否登录都要运行**
- 取消勾选 **仅在计算机使用交流电源时启动**

### ⑤ 输入密码

输入你的 **Windows 登录密码**

### ⑥ 测试是否生效

在任务计划器中右键点击 `每周模型训练` → **运行**

查看 `D:\Market-train\logs\train.log`，如果有日志生成，说明配置成功。


## 📋 快速检查清单

- [ ] Docker Desktop 已安装并运行
- [ ] Qdrant 容器正常运行 (`docker ps` 可见)
- [ ] `http://localhost:6333/healthz` 返回正常
- [ ] `index_items.py` 索引执行成功
- [ ] 任务计划器已创建每周训练任务
- [ ] 测试手动运行任务有日志输出


## 🚀 附录：一键测试脚本

创建 `D:\Market-train\test_qdrant.py`：

```python
"""测试 Qdrant 是否正常工作"""
from qdrant_client import QdrantClient

def test_qdrant():
    try:
        client = QdrantClient(host="localhost", port=6333)
        collections = client.get_collections()
        print(f"✅ Qdrant 连接成功！")
        print(f"   当前 collections: {collections}")
        return True
    except Exception as e:
        print(f"❌ Qdrant 连接失败: {e}")
        return False

if __name__ == "__main__":
    test_qdrant()
```

运行测试：
```bash
cd D:\Market-train\backend
python ..\test_qdrant.py
```