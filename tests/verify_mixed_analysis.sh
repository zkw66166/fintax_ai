#!/bin/bash
# 验证跨路由混合多轮查询功能

echo "=========================================="
echo "验证跨路由混合多轮查询功能"
echo "=========================================="
echo ""

# 1. 检查核心文件是否存在
echo "1. 检查核心文件..."
files=(
    "modules/mixed_analysis_detector.py"
    "modules/mixed_analysis_executor.py"
    "prompts/mixed_analysis_tax_planning.txt"
    "test_mixed_analysis.py"
    "test_mixed_analysis_e2e.py"
)

all_exist=true
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✓ $file"
    else
        echo "  ✗ $file (缺失)"
        all_exist=false
    fi
done

if [ "$all_exist" = false ]; then
    echo ""
    echo "❌ 部分文件缺失，请检查"
    exit 1
fi

echo ""
echo "2. 检查配置项..."
if grep -q "MIXED_ANALYSIS_ENABLED" config/settings.py; then
    echo "  ✓ 配置项已添加到 config/settings.py"
else
    echo "  ✗ 配置项未找到"
    exit 1
fi

echo ""
echo "3. 运行单元测试..."
python test_mixed_analysis.py
if [ $? -eq 0 ]; then
    echo "  ✓ 单元测试通过"
else
    echo "  ✗ 单元测试失败"
    exit 1
fi

echo ""
echo "4. 运行端到端测试..."
python test_mixed_analysis_e2e.py > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "  ✓ 端到端测试通过"
else
    echo "  ✗ 端到端测试失败"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ 所有验证通过！功能已就绪。"
echo "=========================================="
