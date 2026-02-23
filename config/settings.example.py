"""fintax_ai 配置文件 - 模板"""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "database" / "fintax_ai.db"
PROMPTS_DIR = PROJECT_ROOT / "prompts"

# DeepSeek API (OpenAI-compatible)
LLM_API_KEY = "your-deepseek-api-key"
LLM_API_BASE = "https://api.deepseek.com"
LLM_MODEL = "deepseek-chat"  # DeepSeek-V3
LLM_MAX_RETRIES = 3
LLM_TIMEOUT = 60

# Pipeline defaults
MAX_ROWS = 1000
MAX_PERIOD_MONTHS = 36

# 缓存配置
CACHE_ENABLED = True
CACHE_MAX_SIZE_INTENT = 500  # Stage 1意图缓存最大条目数
CACHE_MAX_SIZE_SQL = 500     # Stage 2 SQL缓存最大条目数
CACHE_MAX_SIZE_RESULT = 200  # SQL执行结果缓存最大条目数
CACHE_MAX_SIZE_CROSS = 100   # 跨域合并结果缓存最大条目数
CACHE_TTL_INTENT = 1800      # Stage 1缓存过期时间（秒）- 30分钟
CACHE_TTL_SQL = 3600          # Stage 2缓存过期时间（秒）- 1小时
CACHE_TTL_RESULT = 1800       # 结果缓存过期时间（秒）- 30分钟
CACHE_TTL_CROSS = 1800        # 跨域缓存过期时间（秒）- 30分钟

# 税收优惠知识库
TAX_INCENTIVES_DB_PATH = PROJECT_ROOT / "database" / "tax_incentives.db"

# 外部法规知识库 (Coze API)
COZE_API_URL = "https://api.coze.cn/v3/chat"
COZE_PAT_TOKEN = "your-coze-pat-token"
COZE_BOT_ID = "your-coze-bot-id"
COZE_USER_ID = "123"
COZE_TIMEOUT = 180

# 意图路由开关
ROUTER_ENABLED = True
