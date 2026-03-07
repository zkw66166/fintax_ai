#!/bin/bash
# 验证 CLAUDE.md 更新完整性

echo "=========================================="
echo "验证 CLAUDE.md 更新完整性"
echo "=========================================="
echo ""

# 检查关键章节是否存在
echo "1. 检查关键章节..."
sections=(
    "Multi-Turn Conversation System"
    "Tier 1: Financial Data Multi-Turn"
    "Tier 2: Cross-Route Mixed Analysis"
    "Routing Decision Flow"
    "## Multi-Turn Conversation"
)

all_exist=true
for section in "${sections[@]}"; do
    if grep -q "$section" CLAUDE.md; then
        echo "  ✓ $section"
    else
        echo "  ✗ $section (缺失)"
        all_exist=false
    fi
done

if [ "$all_exist" = false ]; then
    echo ""
    echo "❌ 部分章节缺失"
    exit 1
fi

echo ""
echo "2. 检查配置项..."
configs=(
    "CONVERSATION_ENABLED"
    "CONVERSATION_MAX_TURNS"
    "CONVERSATION_TOKEN_BUDGET"
    "MIXED_ANALYSIS_ENABLED"
    "MIXED_ANALYSIS_MIN_ROUTES"
)

all_exist=true
for config in "${configs[@]}"; do
    if grep -q "$config" CLAUDE.md; then
        echo "  ✓ $config"
    else
        echo "  ✗ $config (缺失)"
        all_exist=false
    fi
done

if [ "$all_exist" = false ]; then
    echo ""
    echo "❌ 部分配置项缺失"
    exit 1
fi

echo ""
echo "3. 检查测试命令..."
if grep -q "test_mixed_analysis.py" CLAUDE.md && grep -q "test_mixed_analysis_e2e.py" CLAUDE.md; then
    echo "  ✓ 测试命令已添加"
else
    echo "  ✗ 测试命令缺失"
    exit 1
fi

echo ""
echo "4. 统计文档行数..."
total_lines=$(wc -l < CLAUDE.md)
echo "  总行数: $total_lines"

if [ $total_lines -lt 500 ]; then
    echo "  ⚠️ 文档行数偏少，可能有内容缺失"
fi

echo ""
echo "5. 检查示例代码块..."
code_blocks=$(grep -c '```' CLAUDE.md)
echo "  代码块数量: $code_blocks"

if [ $code_blocks -lt 10 ]; then
    echo "  ⚠️ 代码块数量偏少"
fi

echo ""
echo "=========================================="
echo "✅ CLAUDE.md 更新验证通过！"
echo "=========================================="
echo ""
echo "文档统计："
echo "  - 总行数: $total_lines"
echo "  - 代码块: $code_blocks"
echo "  - 关键章节: ${#sections[@]}"
echo "  - 配置项: ${#configs[@]}"
