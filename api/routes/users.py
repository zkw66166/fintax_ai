"""用户管理路由：CRUD + 企业权限"""
import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from api.auth import (
    get_current_user, require_admin, hash_password,
    ADMIN_ROLES, CREATABLE_ROLES, get_user_company_ids,
    get_default_companies_for_role,
)
from api.schemas import UserCreate, UserUpdate
from config.settings import DB_PATH

router = APIRouter(prefix="/users", tags=["users"])

USER_FIELDS = "id, username, role, display_name, is_active, created_at, last_login, created_by"


def _conn():
    from modules.db_utils import get_connection
    return get_connection()


@router.get("")
async def list_users(user: dict = Depends(get_current_user)):
    """所有登录用户可浏览用户列表。非 sys 用户看不到 sys 行。"""
    conn = _conn()
    if user["role"] == "sys":
        rows = conn.execute(f"SELECT {USER_FIELDS} FROM users ORDER BY id").fetchall()
    else:
        rows = conn.execute(
            f"SELECT {USER_FIELDS} FROM users WHERE role != 'sys' ORDER BY id"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.post("")
async def create_user(body: UserCreate, user: dict = Depends(get_current_user)):
    """按角色校验创建权限。"""
    allowed = CREATABLE_ROLES.get(user["role"], set())
    if body.role not in allowed:
        raise HTTPException(status_code=403, detail=f"您的角色无权创建「{body.role}」用户")

    conn = _conn()
    existing = conn.execute("SELECT id FROM users WHERE username = ?", (body.username,)).fetchone()
    if existing:
        conn.close()
        raise HTTPException(status_code=409, detail="用户名已存在")

    pw_hash = hash_password(body.password)
    conn.execute(
        "INSERT INTO users (username, password_hash, role, display_name, is_active, created_by) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (body.username, pw_hash, body.role, body.display_name or body.username, body.is_active, user["id"]),
    )
    conn.commit()
    new_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    # 写入企业权限
    company_ids_to_assign = body.company_ids
    if not company_ids_to_assign:
        # 未指定企业时，自动分配角色默认企业
        company_ids_to_assign = get_default_companies_for_role(
            body.role, user["id"], user["role"]
        )

    if company_ids_to_assign:
        # 非 admin 只能分配自己有权限的企业子集
        if user["role"] not in ADMIN_ROLES:
            my_ids = set(get_user_company_ids(user["id"], user["role"]))
            invalid = set(company_ids_to_assign) - my_ids
            if invalid:
                conn.close()
                raise HTTPException(status_code=403, detail=f"无权分配企业: {', '.join(invalid)}")
        for tid in company_ids_to_assign:
            conn.execute(
                "INSERT OR IGNORE INTO user_company_access (user_id, taxpayer_id, created_by) VALUES (?, ?, ?)",
                (new_id, tid, user["id"]),
            )
        conn.commit()

    row = conn.execute(f"SELECT {USER_FIELDS} FROM users WHERE id = ?", (new_id,)).fetchone()
    conn.close()
    result = dict(row)
    result["company_ids"] = get_user_company_ids(new_id, body.role)
    return result


@router.put("/{user_id}")
async def update_user(user_id: int, body: UserUpdate, user: dict = Depends(get_current_user)):
    """非 admin 仅可改自己密码；admin/sys 可改全部字段。"""
    is_self = user["id"] == user_id
    is_admin = user["role"] in ADMIN_ROLES

    if not is_self and not is_admin:
        raise HTTPException(status_code=403, detail="无权修改此用户")

    conn = _conn()
    target = conn.execute("SELECT id, role FROM users WHERE id = ?", (user_id,)).fetchone()
    if not target:
        conn.close()
        raise HTTPException(status_code=404, detail="用户不存在")

    # 保护 sys 用户角色不被非 sys 修改
    if target["role"] == "sys" and user["role"] != "sys":
        conn.close()
        raise HTTPException(status_code=403, detail="无权修改超级管理员")

    updates, params = [], []

    if is_admin:
        # admin/sys 可改所有字段
        if body.password is not None:
            updates.append("password_hash = ?")
            params.append(hash_password(body.password))
        if body.display_name is not None:
            updates.append("display_name = ?")
            params.append(body.display_name)
        if body.role is not None:
            updates.append("role = ?")
            params.append(body.role)
        if body.is_active is not None:
            updates.append("is_active = ?")
            params.append(body.is_active)
    else:
        # 非 admin 仅可改自己密码
        if body.password is not None:
            updates.append("password_hash = ?")
            params.append(hash_password(body.password))

    if updates:
        params.append(user_id)
        conn.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()

    # 企业权限更新 (仅 admin/sys)
    if is_admin and body.company_ids is not None:
        conn.execute("DELETE FROM user_company_access WHERE user_id = ?", (user_id,))
        for tid in body.company_ids:
            conn.execute(
                "INSERT OR IGNORE INTO user_company_access (user_id, taxpayer_id, created_by) VALUES (?, ?, ?)",
                (user_id, tid, user["id"]),
            )
        conn.commit()

    row = conn.execute(f"SELECT {USER_FIELDS} FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    result = dict(row)
    result["company_ids"] = get_user_company_ids(user_id, result["role"])
    return result


@router.delete("/{user_id}")
async def delete_user(user_id: int, user: dict = Depends(require_admin)):
    if user["id"] == user_id:
        raise HTTPException(status_code=400, detail="不能删除自己")
    conn = _conn()
    target = conn.execute("SELECT id, role FROM users WHERE id = ?", (user_id,)).fetchone()
    if not target:
        conn.close()
        raise HTTPException(status_code=404, detail="用户不存在")
    if target["role"] == "sys":
        conn.close()
        raise HTTPException(status_code=403, detail="不可删除超级管理员")
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return {"ok": True}


@router.get("/{user_id}/companies")
async def get_user_companies(user_id: int, user: dict = Depends(get_current_user)):
    """获取用户的企业权限列表。非 admin 仅可查自己。"""
    if user["role"] not in ADMIN_ROLES and user["id"] != user_id:
        raise HTTPException(status_code=403, detail="无权查看他人企业权限")
    conn = _conn()
    target = conn.execute("SELECT id, role FROM users WHERE id = ?", (user_id,)).fetchone()
    if not target:
        conn.close()
        raise HTTPException(status_code=404, detail="用户不存在")
    conn.close()
    return {"company_ids": get_user_company_ids(user_id, target["role"])}


@router.put("/{user_id}/companies")
async def set_user_companies(user_id: int, body: dict, user: dict = Depends(require_admin)):
    """替换用户的企业权限（仅 admin/sys）。"""
    company_ids = body.get("company_ids", [])
    conn = _conn()
    target = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
    if not target:
        conn.close()
        raise HTTPException(status_code=404, detail="用户不存在")
    conn.execute("DELETE FROM user_company_access WHERE user_id = ?", (user_id,))
    for tid in company_ids:
        conn.execute(
            "INSERT OR IGNORE INTO user_company_access (user_id, taxpayer_id, created_by) VALUES (?, ?, ?)",
            (user_id, tid, user["id"]),
        )
    conn.commit()
    conn.close()
    return {"ok": True, "company_ids": company_ids}
