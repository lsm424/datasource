#!/usr/bin/env python3
"""
重置管理员密码脚本
"""

import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(__file__))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine
from app.models.user import User
from app.core.security import get_password_hash

def reset_admin_password(new_password: str = "admin"):
    """重置管理员密码"""
    
    db = SessionLocal()
    try:
        # 查找admin用户
        admin_user = db.query(User).filter(User.username == "admin").first()
        
        if admin_user:
            # 更新密码
            admin_user.hashed_password = get_password_hash(new_password)
            db.commit()
            print(f"✅ 管理员密码已重置为: {new_password}")
        else:
            # 创建新的admin用户
            from app.models.user import UserRole
            import uuid
            
            admin_user = User(
                id=str(uuid.uuid4()),
                username="admin",
                email="admin@example.com",
                name="Administrator",
                hashed_password=get_password_hash(new_password),
                role=UserRole.ADMIN,
                is_active=True,
                is_verified=True
            )
            
            db.add(admin_user)
            db.commit()
            print(f"✅ 已创建管理员用户，密码: {new_password}")
            
    except Exception as e:
        print(f"❌ 操作失败: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    password = sys.argv[1] if len(sys.argv) > 1 else "admin"
    reset_admin_password(password)
