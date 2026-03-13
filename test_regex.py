import re

cur_year = 2026
query = "前年3月和去年3月"

print(f"Original: {query}")

# Step 1: 前年X月 → 2024年X月
pattern1 = r"前年(\d{1,2})月"
query = re.sub(pattern1, lambda m: f"{cur_year - 2}年{m.group(1)}月", query)
print(f"After 前年X月: {query}")

# Step 2: 去年X月 → 2025年X月
pattern2 = r"去年(\d{1,2})月"
query = re.sub(pattern2, lambda m: f"{cur_year - 1}年{m.group(1)}月", query)
print(f"After 去年X月: {query}")
