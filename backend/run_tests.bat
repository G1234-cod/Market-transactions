@echo off
chcp 65001 >nul
echo ============================================================
echo   智能二手商品发布助手 - 测试报告
echo ============================================================
echo.

call conda activate image_recognition
python -m pytest test/test_auth.py test/test_db.py test/test_detect.py test/test_price.py -v --tb=short

echo.
echo ============================================================
echo   测试完成，按任意键退出...
echo ============================================================
pause >nul
