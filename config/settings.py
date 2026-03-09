"""fintax_ai 配置文件"""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "database" / "fintax_ai.db"
PROMPTS_DIR = PROJECT_ROOT / "prompts"

# DeepSeek API (OpenAI-compatible)
LLM_API_KEY = "sk-6ba41d1831bd4c229d93e587a02d2414"
LLM_API_BASE = "https://api.deepseek.com"
LLM_MODEL = "deepseek-chat"  # DeepSeek-V3
LLM_MAX_RETRIES = 3
LLM_TIMEOUT = 60

# Pipeline defaults
MAX_ROWS = 1000
MAX_PERIOD_MONTHS = 36

# 内存缓存配置 (已弃用 - 与 L1/L2 持久化缓存冲突)
# 设置为 False 以避免跨公司缓存污染
# 原因：内存缓存使用 query + taxpayer_type 作为键，不包含 company_id，
# 导致不同公司的相同类型查询可能返回错误的缓存数据。
# L1/L2 持久化缓存已提供足够的性能优化，且是公司感知的。
CACHE_ENABLED = False  # DEPRECATED: Use L1/L2 persistent cache instead
CACHE_MAX_SIZE_INTENT = 500  # (保留用于向后兼容)
CACHE_MAX_SIZE_SQL = 500     # (保留用于向后兼容)
CACHE_MAX_SIZE_RESULT = 200  # (保留用于向后兼容)
CACHE_MAX_SIZE_CROSS = 100   # (保留用于向后兼容)
CACHE_TTL_INTENT = 1800      # (保留用于向后兼容)
CACHE_TTL_SQL = 3600          # (保留用于向后兼容)
CACHE_TTL_RESULT = 1800       # (保留用于向后兼容)
CACHE_TTL_CROSS = 1800        # (保留用于向后兼容)

# 税收优惠知识库
TAX_INCENTIVES_DB_PATH = PROJECT_ROOT / "database" / "tax_incentives.db"

# 外部法规知识库 (Coze API)
COZE_API_URL = "https://api.coze.cn/v3/chat"
COZE_PAT_TOKEN = "pat_gvTUOFnejLJMJ1grvxTScvI8dDVzZFMDac57A9R6Oa1llIm38AqcyG63wMb1Aw6o"
COZE_BOT_ID = "7592905400907989034"
COZE_USER_ID = "123"
COZE_TIMEOUT = 180

# 意图路由开关
ROUTER_ENABLED = True

# JWT 认证
JWT_SECRET_KEY = "fintax-ai-secret-change-in-production-2026"
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 1440  # 24小时

# 数据解读配置
INTERPRETATION_ENABLED = True
INTERPRETATION_MAX_TOKENS = 2000
INTERPRETATION_TEMPERATURE = 0.3

# 持久化查询缓存
QUERY_CACHE_DIR = PROJECT_ROOT / "cache"
QUERY_CACHE_ENABLED = True

# L1 缓存（完整结果）
QUERY_CACHE_MAX_FILES_L1 = 1500

# L2 缓存（SQL 模板）
QUERY_CACHE_ENABLED_L2 = True
QUERY_CACHE_MAX_FILES_L2 = 500
QUERY_CACHE_L2_PREFIX = "template_"

# 缓存失效策略
CACHE_INVALIDATE_L2_ON_DATA_UPDATE = False

# 智能适配开关（已废弃 - 2026-03-08）
# 原因：会计准则和纳税人类型的列结构差异导致适配不可靠
# 新策略：每个查询按域分层保存多个精确模板
# - 财务报表：每个查询2个模板（按会计准则区分）
# - VAT：每个查询2个模板（按纳税人类型区分）
# - EIT：每个查询1个模板（无类型/准则区分）
# - 跨域：每个查询4个模板（保守策略）
TAXPAYER_TYPE_SMART_ADAPT = False  # DEPRECATED: 保留用于向后兼容，但不再使用

# 对话上下文配置
CONVERSATION_ENABLED = True  # 功能开关（已启用）
CONVERSATION_MAX_TURNS = 3  # 默认：3轮（6条消息）
CONVERSATION_MIN_TURNS = 2  # 最小：2轮
CONVERSATION_MAX_TURNS_LIMIT = 5  # 最大：5轮
CONVERSATION_TOKEN_BUDGET = 4000  # 预留4K tokens用于历史
CONVERSATION_BETA_USERS = ["admin", "user1", "sys"]  # Beta用户白名单（用户名列表）

# 混合分析路由配置
MIXED_ANALYSIS_ENABLED = True  # 主开关
MIXED_ANALYSIS_MIN_ROUTES = 2  # 最少需要几种路由才触发
MIXED_ANALYSIS_LLM_MODEL = "deepseek-chat"  # 使用的LLM模型
MIXED_ANALYSIS_MAX_CONTEXT_TOKENS = 8000  # 历史上下文最大token数
MIXED_ANALYSIS_STREAM_CHUNK_SIZE = 50  # 流式输出chunk大小
