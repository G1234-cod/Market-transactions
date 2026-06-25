@echo off
echo ========================================
echo 每周自动模型训练
echo 开始时间: %date% %time%
echo ========================================

cd /d D:\Market-train

echo 激活虚拟环境...
call venv\Scripts\activate

echo 开始训练...
python scripts/weekly_train.py

echo ========================================
echo 训练完成！
echo 结束时间: %date% %time%
echo ========================================

pause