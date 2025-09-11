"""Add SSO support fields to users table

Revision ID: add_sso_fields
Revises: 
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite, postgresql, mysql


# revision identifiers, used by Alembic.
revision = 'add_sso_fields'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Add SSO support fields to users table"""
    
    # Check if we're using SQLite, PostgreSQL, or MySQL
    conn = op.get_bind()
    engine_name = conn.engine.name
    
    try:
        # Add external_id column for SSO user mapping
        with op.batch_alter_table('users', schema=None) as batch_op:
            batch_op.add_column(sa.Column('external_id', sa.String(200), nullable=True))
            batch_op.create_unique_constraint('uq_users_external_id', ['external_id'])
            batch_op.create_index('idx_users_external_id', ['external_id'])
        
        # Add extra_metadata column for storing SSO-related information
        if engine_name == 'sqlite':
            # SQLite uses TEXT for JSON
            with op.batch_alter_table('users', schema=None) as batch_op:
                batch_op.add_column(sa.Column('extra_metadata', sa.Text(), nullable=True))
        elif engine_name == 'postgresql':
            # PostgreSQL has native JSON support
            with op.batch_alter_table('users', schema=None) as batch_op:
                batch_op.add_column(sa.Column('extra_metadata', postgresql.JSON(), nullable=True))
        elif engine_name == 'mysql':
            # MySQL 5.7+ has JSON support
            with op.batch_alter_table('users', schema=None) as batch_op:
                batch_op.add_column(sa.Column('extra_metadata', mysql.JSON(), nullable=True))
        else:
            # Fallback to TEXT for other databases
            with op.batch_alter_table('users', schema=None) as batch_op:
                batch_op.add_column(sa.Column('extra_metadata', sa.Text(), nullable=True))
                
        print("✅ SSO字段添加成功！")
        
    except Exception as e:
        print(f"⚠️  添加SSO字段时出错: {str(e)}")
        print("   可能字段已存在或数据库不支持此操作")


def downgrade():
    """Remove SSO support fields from users table"""
    
    try:
        with op.batch_alter_table('users', schema=None) as batch_op:
            # Remove indexes and constraints first
            batch_op.drop_index('idx_users_external_id')
            batch_op.drop_constraint('uq_users_external_id', type_='unique')
            
            # Remove columns
            batch_op.drop_column('external_id')
            batch_op.drop_column('extra_metadata')
            
        print("✅ SSO字段移除成功！")
        
    except Exception as e:
        print(f"⚠️  移除SSO字段时出错: {str(e)}")


if __name__ == "__main__":
    """直接运行此脚本进行数据库迁移（开发环境）"""
    import sys
    import os
    
    # 添加项目根目录到路径
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
    
    from app.core.database import engine
    from sqlalchemy import text
    
    print("🔧 开始数据库迁移...")
    
    # 直接执行SQL迁移（适用于开发环境）
    try:
        with engine.connect() as conn:
            # 检查是否已经有这些字段
            try:
                result = conn.execute(text("SELECT external_id FROM users LIMIT 1"))
                print("ℹ️  SSO字段已存在，跳过迁移")
                sys.exit(0)
            except:
                # 字段不存在，继续添加
                pass
            
            # 添加external_id字段
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN external_id VARCHAR(200)"))
                print("✅ 添加external_id字段")
            except Exception as e:
                if "duplicate column name" not in str(e).lower():
                    print(f"⚠️  添加external_id字段失败: {e}")
            
            # 添加唯一约束和索引
            try:
                conn.execute(text("CREATE UNIQUE INDEX idx_users_external_id ON users(external_id)"))
                print("✅ 添加external_id索引")
            except Exception as e:
                if "already exists" not in str(e).lower():
                    print(f"⚠️  添加索引失败: {e}")
            
            # 添加extra_metadata字段
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN extra_metadata TEXT"))
                print("✅ 添加extra_metadata字段")
            except Exception as e:
                if "duplicate column name" not in str(e).lower():
                    print(f"⚠️  添加extra_metadata字段失败: {e}")
            
            conn.commit()
            print("🎉 数据库迁移完成！")
            
    except Exception as e:
        print(f"❌ 数据库迁移失败: {e}")
        print("   请检查数据库连接或手动执行SQL语句")
