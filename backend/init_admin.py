#!/usr/bin/env python3
"""
初始化管理员用户脚本
用于创建系统的第一个管理员用户
"""

import asyncio
import sys
from sqlalchemy.orm import Session
from getpass import getpass

from app.core.database import SessionLocal, create_database
from app.models.user import User, UserRole
from app.core.security import get_password_hash


def create_admin_user():
    """创建管理员用户"""
    print("=== 数据浏览系统 - 初始化管理员用户 ===")
    print()
    
    # 确保数据库存在
    create_database()
    
    db = SessionLocal()
    
    try:
        # 检查是否已有管理员用户
        existing_admin = db.query(User).filter(User.role == UserRole.ADMIN).first()
        if existing_admin:
            print(f"系统中已存在管理员用户: {existing_admin.username}")
            overwrite = input("是否要创建新的管理员用户？(y/N): ").strip().lower()
            if overwrite != 'y':
                print("操作已取消")
                return
        
        print("请输入管理员用户信息：")
        
        # 获取用户输入
        while True:
            username = input("用户名 (3-50字符): ").strip()
            if len(username) >= 3 and len(username) <= 50:
                # 检查用户名是否已存在
                existing_user = db.query(User).filter(User.username == username).first()
                if existing_user:
                    print(f"用户名 '{username}' 已存在，请选择其他用户名")
                    continue
                break
            else:
                print("用户名长度应在 3-50 个字符之间")
        
        while True:
            email = input("邮箱地址: ").strip()
            if '@' in email and '.' in email:
                # 检查邮箱是否已存在
                existing_email = db.query(User).filter(User.email == email).first()
                if existing_email:
                    print(f"邮箱 '{email}' 已被注册，请使用其他邮箱")
                    continue
                break
            else:
                print("请输入有效的邮箱地址")
        
        name = input("真实姓名: ").strip()
        if not name:
            name = username
            
        company = input("公司/组织 (可选): ").strip()
        
        # 密码输入
        while True:
            password = getpass("密码 (至少8位): ")
            if len(password) >= 8:
                confirm_password = getpass("确认密码: ")
                if password == confirm_password:
                    break
                else:
                    print("两次输入的密码不一致，请重新输入")
            else:
                print("密码长度至少为8位")
        
        # 创建管理员用户
        hashed_password = get_password_hash(password)
        
        admin_user = User(
            username=username,
            email=email,
            name=name,
            company=company,
            hashed_password=hashed_password,
            role=UserRole.ADMIN,
            is_active=True,
            is_verified=True
        )
        
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        print()
        print("✅ 管理员用户创建成功！")
        print(f"   用户名: {admin_user.username}")
        print(f"   邮箱: {admin_user.email}")
        print(f"   姓名: {admin_user.name}")
        print(f"   角色: 管理员")
        print()
        print("现在可以使用此账户登录系统了。")
        
    except Exception as e:
        print(f"❌ 创建管理员用户失败: {e}")
        db.rollback()
    finally:
        db.close()


def list_users():
    """列出所有用户"""
    print("=== 系统用户列表 ===")
    print()
    
    db = SessionLocal()
    
    try:
        users = db.query(User).all()
        
        if not users:
            print("系统中暂无用户")
            return
        
        print(f"{'用户名':<15} {'邮箱':<25} {'姓名':<15} {'角色':<10} {'状态':<10}")
        print("-" * 80)
        
        for user in users:
            status = "激活" if user.is_active else "禁用"
            role_name = "管理员" if user.role == UserRole.ADMIN else "普通用户"
            
            print(f"{user.username:<15} {user.email:<25} {user.name:<15} {role_name:<10} {status:<10}")
        
        print(f"\n总共 {len(users)} 个用户")
        
    except Exception as e:
        print(f"❌ 获取用户列表失败: {e}")
    finally:
        db.close()


def main():
    """主函数"""
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "list":
            list_users()
            return
        elif command == "help":
            print("使用方法：")
            print("  python init_admin.py        - 创建管理员用户")
            print("  python init_admin.py list   - 列出所有用户")
            print("  python init_admin.py help   - 显示帮助信息")
            return
        else:
            print(f"未知命令: {command}")
            print("使用 'python init_admin.py help' 查看可用命令")
            return
    
    create_admin_user()


if __name__ == "__main__":
    main()
