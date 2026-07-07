$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host ""
Write-Host "============================================================"
Write-Host "  智能二手商品发布助手 - 测试报告"
Write-Host "============================================================"
Write-Host ""

conda activate image_recognition
python -m pytest test/test_auth.py test/test_db.py test/test_detect.py test/test_price.py -v --tb=short

Write-Host ""
Write-Host "============================================================"
Write-Host "  测试完成"
Write-Host "============================================================"
