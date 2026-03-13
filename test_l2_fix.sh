#!/bin/bash

# 测试L2缓存多期间查询修复

echo "=========================================="
echo "测试L2缓存多期间查询修复"
echo "=========================================="

# 清空L2缓存
echo ""
echo "清空L2缓存..."
rm -f cache/l2_*.json
echo "✓ L2缓存已清空"

# 登录获取token
echo ""
echo "登录..."
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"sys","password":"sys123"}' | jq -r '.access_token')

if [ "$TOKEN" = "null" ] || [ -z "$TOKEN" ]; then
  echo "❌ 登录失败"
  exit 1
fi
echo "✓ 登录成功"

# 测试查询
QUERY="去年第一季度各月管理费用和财务费用比较分析"

# 第一次查询 - TSE科技
echo ""
echo "=========================================="
echo "第1次查询: TSE科技有限公司"
echo "=========================================="
START=$(date +%s%N)
curl -s -X POST http://localhost:8000/api/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"query\": \"$QUERY\",
    \"company_id\": \"91310115MA2KZZZZZZ\",
    \"thinking_mode\": \"quick\",
    \"response_mode\": \"detailed\",
    \"multi_turn_enabled\": false,
    \"conversation_depth\": 3
  }" > /dev/null
END=$(date +%s%N)
TIME1=$((($END - $START) / 1000000))
echo "✓ 完成，耗时: ${TIME1}ms"
echo "  → 应该显示: [L2 Cache] Saved"

sleep 2

# 第二次查询 - 创智软件（应该命中L2）
echo ""
echo "=========================================="
echo "第2次查询: 创智软件股份有限公司"
echo "=========================================="
START=$(date +%s%N)
curl -s -X POST http://localhost:8000/api/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"query\": \"$QUERY\",
    \"company_id\": \"91330200MA2KXXXXXX\",
    \"thinking_mode\": \"quick\",
    \"response_mode\": \"detailed\",
    \"multi_turn_enabled\": false,
    \"conversation_depth\": 3
  }" > /dev/null
END=$(date +%s%N)
TIME2=$((($END - $START) / 1000000))
echo "✓ 完成，耗时: ${TIME2}ms"
echo "  → 应该显示: [L2 Cache] Hit: domain=profit"

sleep 2

# 第三次查询 - 华兴科技（应该命中L2）
echo ""
echo "=========================================="
echo "第3次查询: 华兴科技有限公司"
echo "=========================================="
START=$(date +%s%N)
curl -s -X POST http://localhost:8000/api/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"query\": \"$QUERY\",
    \"company_id\": \"91310000MA1FL8XQ30\",
    \"thinking_mode\": \"quick\",
    \"response_mode\": \"detailed\",
    \"multi_turn_enabled\": false,
    \"conversation_depth\": 3
  }" > /dev/null
END=$(date +%s%N)
TIME3=$((($END - $START) / 1000000))
echo "✓ 完成，耗时: ${TIME3}ms"
echo "  → 应该显示: [L2 Cache] Hit: domain=profit"

echo ""
echo "=========================================="
echo "测试完成"
echo "=========================================="
echo "耗时对比:"
echo "  第1次: ${TIME1}ms (pipeline)"
echo "  第2次: ${TIME2}ms (L2缓存)"
echo "  第3次: ${TIME3}ms (L2缓存)"
echo ""
echo "请检查后端日志确认L2缓存命中情况"
