"""认证路由：登录/登出/当前用户"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from api.auth import verify_password, create_access_token, get_current_user, get_user_company_ids
from api.schemas import LoginRequest, CaptchaVerifyRequest
from modules.db_utils import get_connection

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login(req: LoginRequest):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE username = ?", (req.username,)
    ).fetchone()
    if not row or not verify_password(req.password, row["password_hash"]):
        conn.close()
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    user = dict(row)
    if not user["is_active"]:
        conn.close()
        raise HTTPException(status_code=403, detail="账号已被禁用")
    conn.execute(
        "UPDATE users SET last_login = ? WHERE id = ?",
        (datetime.now(timezone.utc).isoformat(), user["id"]),
    )
    conn.commit()
    conn.close()
    token = create_access_token(user["id"], user["username"], user["role"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "role": user["role"],
            "display_name": user["display_name"],
            "company_ids": get_user_company_ids(user["id"], user["role"]),
        },
    }


@router.post("/logout")
async def logout():
    return {"ok": True}


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return {
        "id": user["id"],
        "username": user["username"],
        "role": user["role"],
        "display_name": user["display_name"],
        "is_active": user["is_active"],
        "created_at": user["created_at"],
        "last_login": user["last_login"],
        "company_ids": get_user_company_ids(user["id"], user["role"]),
    }


@router.post("/captcha/verify")
async def verify_captcha(req: CaptchaVerifyRequest):
    """验证验证码（使用user1的密码）"""
    conn = get_connection()
    row = conn.execute(
        "SELECT password_hash FROM users WHERE username = ?", ("user1",)
    ).fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=500, detail="系统配置错误")

    if verify_password(req.code, row["password_hash"]):
        return {"success": True, "message": "验证成功"}
    else:
        return {"success": False, "message": "验证码错误"}
