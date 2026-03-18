"""JWT 认证工具函数"""
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from config.settings import DB_PATH, JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRE_MINUTES
from pathlib import Path as _Path
from config.config_loader import load_json as _load_json

security = HTTPBearer(auto_error=False)

_CFG_roles = _load_json(_Path(__file__).resolve().parent.parent / "config" / "auth" / "roles.json", {})

# ── 角色常量 ──────────────────────────────────────────────
ROLES = _CFG_roles.get("roles", ['sys', 'admin', 'firm', 'group', 'enterprise'])
ADMIN_ROLES = set(_CFG_roles.get("admin_roles", ['sys', 'admin']))
ROLE_LABELS = _CFG_roles.get("role_labels", {
    'sys': '超级管理员',
    'admin': '系统管理员',
    'firm': '事务所用户',
    'group': '集团企业用户',
    'enterprise': '普通企业用户',
})
_cr_raw = _CFG_roles.get("creatable_roles", None)
if _cr_raw:
    CREATABLE_ROLES = {k: set(v) for k, v in _cr_raw.items()}
else:
    CREATABLE_ROLES = {
        'sys':        {'admin', 'firm', 'group', 'enterprise'},
        'admin':      {'admin', 'firm', 'group', 'enterprise'},
        'firm':       {'firm', 'enterprise'},
        'group':      {'group', 'enterprise'},
        'enterprise': {'enterprise'},
    }

# ── 角色默认企业映射 ──────────────────────────────────────
ROLE_DEFAULT_COMPANIES = _CFG_roles.get("role_default_companies", {
    'firm': [
        '91310000MA1FL8XQ30',  # 华兴科技有限公司
        '92440300MA5EQXL17P',  # 鑫源贸易商行
    ],
    'group': [
        '91330200MA2KXXXXXX',  # 创智软件股份有限公司
        '91330200MA2KYYYYYY',  # 大华智能制造厂
        '91310115MA2KZZZZZZ',  # TSE科技有限公司
        '91330100MA2KWWWWWW',  # 环球机械有限公司
    ],
    'enterprise': [
        '91310000MA1FL8XQ30',  # 华兴科技有限公司
    ],
})


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(user_id: int, username: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "username": username, "role": role, "exp": expire}
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None


def get_user_by_id(user_id: int) -> Optional[dict]:
    from modules.db_utils import get_connection
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    if credentials is None:
        raise HTTPException(status_code=401, detail="未提供认证凭据")
    payload = decode_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=401, detail="无效的认证凭据")
    user = get_user_by_id(int(payload["sub"]))
    if user is None or not user["is_active"]:
        raise HTTPException(status_code=401, detail="用户不存在或已禁用")
    return user


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user["role"] not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user


# ── 企业数据权限 ──────────────────────────────────────────

def get_user_company_ids(user_id: int, role: str) -> list[str]:
    """返回用户可访问的 taxpayer_id 列表。sys/admin 返回全部。"""
    from modules.db_utils import get_connection
    conn = get_connection()
    if role in ADMIN_ROLES:
        rows = conn.execute("SELECT taxpayer_id FROM taxpayer_info").fetchall()
    else:
        rows = conn.execute(
            "SELECT taxpayer_id FROM user_company_access WHERE user_id = ?",
            (user_id,),
        ).fetchall()
    conn.close()
    return [r[0] for r in rows]


def require_company_access(user: dict, company_id: str):
    """校验用户是否有权访问指定企业，无权则抛 403。"""
    if not company_id:
        return
    allowed = get_user_company_ids(user["id"], user["role"])
    if company_id not in allowed:
        raise HTTPException(status_code=403, detail="无权访问该企业数据")


def get_default_companies_for_role(
    role: str,
    requester_id: Optional[int] = None,
    requester_role: Optional[str] = None,
) -> list:
    """返回角色的默认企业列表。非 admin 请求者返回交集（自身权限 ∩ 角色默认）。"""
    defaults = ROLE_DEFAULT_COMPANIES.get(role, [])
    if not defaults:
        return []
    if requester_role and requester_role not in ADMIN_ROLES and requester_id:
        my_ids = set(get_user_company_ids(requester_id, requester_role))
        return [tid for tid in defaults if tid in my_ids]
    return list(defaults)
