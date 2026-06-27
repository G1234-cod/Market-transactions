@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo.
echo =====================================================
echo   COCO 2017 数据集自动准备 + YOLO 格式转换
echo =====================================================
echo.

:: ==========================================
:: 1. 检查 Python 环境
:: ==========================================
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] 请先安装 Python 3.8+
    echo          https://www.python.org/downloads/
    pause
    exit /b 1
)
echo [OK] Python 已就绪

:: ==========================================
:: 2. 安装依赖
:: ==========================================
echo.
echo [*] 检查 Python 依赖...

python -c "import torch" >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] 安装 PyTorch + ultralytics (首次可能需要几分钟)...
    pip install torch torchvision ultralytics -q
) else (
    python -c "import ultralytics" >nul 2>&1
    if %errorlevel% neq 0 (
        echo [!] 安装 ultralytics...
        pip install ultralytics -q
    ) else (
        echo [OK] 依赖已就绪
    )
)

python -c "import tqdm" >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] 安装 tqdm（进度条）...
    pip install tqdm -q
)

:: ==========================================
:: 3. 下载 COCO 2017（如果还没有）
:: ==========================================
set DOWNLOAD=0

if not exist "train2017\" set DOWNLOAD=1
if not exist "val2017\"   set DOWNLOAD=1
if not exist "annotations\instances_train2017.json" set DOWNLOAD=1
if not exist "annotations\instances_val2017.json"   set DOWNLOAD=1

if !DOWNLOAD!==1 (
    echo.
    echo [*] 开始下载 COCO 2017 数据集 (~20GB，请耐心等待)
    echo.

    :: train2017 (~18GB)
    if not exist "train2017\" (
        if not exist "train2017.zip" (
            echo [↓] 下载 train2017.zip (18GB)...
            curl -L -o train2017.zip http://images.cocodataset.org/zips/train2017.zip
            if %errorlevel% neq 0 (
                echo [ERROR] 下载 train2017.zip 失败，请检查网络
                pause
                exit /b 1
            )
        )
        echo [↦] 解压 train2017.zip...
        tar -xf train2017.zip
        if not exist "train2017\" (
            echo [ERROR] 解压 train2017.zip 失败
            pause
            exit /b 1
        )
    )

    :: val2017 (~1GB)
    if not exist "val2017\" (
        if not exist "val2017.zip" (
            echo [↓] 下载 val2017.zip (1GB)...
            curl -L -o val2017.zip http://images.cocodataset.org/zips/val2017.zip
            if %errorlevel% neq 0 (
                echo [ERROR] 下载 val2017.zip 失败，请检查网络
                pause
                exit /b 1
            )
        )
        echo [↦] 解压 val2017.zip...
        tar -xf val2017.zip
        if not exist "val2017\" (
            echo [ERROR] 解压 val2017.zip 失败
            pause
            exit /b 1
        )
    )

    :: annotations (~250MB)
    if not exist "annotations\instances_train2017.json" (
        if not exist "annotations_trainval2017.zip" (
            echo [↓] 下载 annotations_trainval2017.zip (250MB)...
            curl -L -o annotations_trainval2017.zip http://images.cocodataset.org/annotations/annotations_trainval2017.zip
            if %errorlevel% neq 0 (
                echo [ERROR] 下载 annotations_trainval2017.zip 失败，请检查网络
                pause
                exit /b 1
            )
        )
        echo [↦] 解压 annotations_trainval2017.zip...
        tar -xf annotations_trainval2017.zip
    )

    echo [OK] 下载完成
) else (
    echo.
    echo [OK] 数据集已存在，跳过下载
)

:: ==========================================
:: 4. COCO → YOLO 格式转换
:: ==========================================
echo.
echo =====================================================
echo   格式转换: COCO → YOLO
echo =====================================================
echo.

set CONVERT_ERR=0

echo [1/2] 转换训练集 (train2017 → dataset/images/train + dataset/labels/train)...
python coco2yolo.py ^
    --coco_json annotations/instances_train2017.json ^
    --images_dir train2017 ^
    --subset train
if %errorlevel% neq 0 set CONVERT_ERR=1

echo.
echo [2/2] 转换验证集 (val2017 → dataset/images/val + dataset/labels/val)...
python coco2yolo.py ^
    --coco_json annotations/instances_val2017.json ^
    --images_dir val2017 ^
    --subset val
if %errorlevel% neq 0 set CONVERT_ERR=1

if !CONVERT_ERR!==1 (
    echo.
    echo [ERROR] 转换失败，请检查上面的错误信息
    pause
    exit /b 1
)

echo.
echo =====================================================
echo   [完成] 数据集已就绪！
echo =====================================================
echo.
echo   下一步: python train.py
echo.
pause
