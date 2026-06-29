@echo off
echo ========================================
echo 每周自动模型训练
echo 开始时间: %date% %time%
echo ========================================

cd /d %~dp0

echo 激活虚拟环境...
call .venv\Scripts\activate

echo 开始训练...
cd backend
python weekly_train.py

echo ========================================
echo 训练完成！
echo 结束时间: %date% %time%
echo ========================================

pause