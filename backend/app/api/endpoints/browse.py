from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io
import pymysql
import logging
import json

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.models.user import User
from app.models.datasource import DataSource, DataSourceType, DatabaseType
from app.schemas.datasource import (
    FileSystemItem,
    DatabaseTable,
    DatabaseColumn,
    DatabaseRecord,
    ObjectStorageObject
)
from app.schemas.base import DataResponse, ListResponse
from app.schemas.minio import (
    BucketInfo,
    ObjectInfo,
    CreateBucketRequest,
    ListObjectsQuery,
    UploadResult,
    MinIOConnectionTest
)
from app.services.minio_service import create_minio_service

router = APIRouter()


def parse_datasource_config(config):
    """解析数据源配置，确保返回字典格式"""
    if isinstance(config, str):
        try:
            return json.loads(config)
        except json.JSONDecodeError:
            raise Exception("数据源配置JSON格式无效")
    elif isinstance(config, dict):
        return config
    elif config is None:
        raise Exception("数据源配置为空")
    else:
        raise Exception(f"数据源配置类型无效: {type(config)}")

# 数据库连接工具函数
def create_mysql_connection(config: dict):
    """创建MySQL数据库连接"""
    try:
        print(f"🔧 创建MySQL连接，配置信息:")
        print(f"  - host: {config.get('host', 'localhost')}")
        print(f"  - port: {config.get('port', 3306)}")
        print(f"  - user: {config.get('user', 'root')}")
        print(f"  - database: {config.get('database', '')}")
        print(f"  - charset: {config.get('charset', 'utf8mb4')}")
        
        connection = pymysql.connect(
            host=config.get('host', 'localhost'),
            port=config.get('port', 3306),
            user=config.get('user', 'root'),
            password=config.get('password', ''),
            database=config.get('database', ''),
            charset=config.get('charset', 'utf8mb4'),
            autocommit=True
        )
        print(f"✅ MySQL连接创建成功")
        return connection
    except Exception as e:
        print(f"❌ 创建MySQL连接失败: {e}")
        print(f"❌ 错误类型: {type(e).__name__}")
        logging.error(f"创建MySQL连接失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"数据库连接失败: {str(e)}"
        )

def get_mysql_tables(connection):
    """获取MySQL数据库的表列表"""
    try:
        print(f"📋 开始获取MySQL表列表...")
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            # 执行SHOW TABLES命令
            sql_query = "SHOW TABLES"
            print(f"🔍 执行SQL: {sql_query}")
            cursor.execute(sql_query)
            tables_result = cursor.fetchall()
            print(f"📨 SHOW TABLES 结果: {tables_result}")
            print(f"📊 找到 {len(tables_result)} 个表")
            
            tables = []
            for i, row in enumerate(tables_result):
                table_name = list(row.values())[0]  # 获取表名
                print(f"  [{i+1}] 处理表: {table_name}")
                
                # 获取表的行数和注释
                info_sql = """
                    SELECT 
                        TABLE_ROWS as row_count,
                        TABLE_COMMENT as comment
                    FROM information_schema.TABLES 
                    WHERE TABLE_SCHEMA = DATABASE() 
                    AND TABLE_NAME = %s
                """
                print(f"🔍 执行表信息查询SQL: {info_sql}")
                print(f"🔍 参数: {table_name}")
                cursor.execute(info_sql, (table_name,))
                table_info = cursor.fetchone()
                print(f"📨 表信息查询结果: {table_info}")
                
                table_obj = DatabaseTable(
                    name=table_name,
                    schema=None,
                    row_count=table_info['row_count'] if table_info and table_info['row_count'] else 0,
                    comment=table_info['comment'] if table_info and table_info['comment'] else None
                )
                tables.append(table_obj)
                print(f"✅ 表 {table_name} 处理完成: {table_obj.row_count} 行")
            
            print(f"🎉 成功获取所有表信息，共 {len(tables)} 个表")
            return tables
    except Exception as e:
        print(f"❌ 获取MySQL表列表失败: {e}")
        print(f"❌ 错误类型: {type(e).__name__}")
        import traceback
        print(f"❌ 详细错误信息:")
        traceback.print_exc()
        logging.error(f"获取MySQL表列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取表列表失败: {str(e)}"
        )

def get_mysql_table_schema(connection, table_name):
    """获取MySQL表的结构信息"""
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(f"DESCRIBE {table_name}")
            columns_result = cursor.fetchall()
            
            columns = []
            for col in columns_result:
                columns.append(DatabaseColumn(
                    name=col['Field'],
                    type=col['Type'],
                    nullable=col['Null'] == 'YES',
                    default_value=col['Default'],
                    comment=None,
                    is_primary_key=col['Key'] == 'PRI',
                    is_auto_increment='auto_increment' in col['Extra'].lower() if col['Extra'] else False
                ))
            
            return columns
    except Exception as e:
        logging.error(f"获取MySQL表结构失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取表结构失败: {str(e)}"
        )

def get_mysql_table_data(connection, table_name, page=1, limit=20, where=None):
    """获取MySQL表的数据"""
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            # 构建查询语句
            query = f"SELECT * FROM {table_name}"
            count_query = f"SELECT COUNT(*) as total FROM {table_name}"
            
            params = []
            if where:
                query += f" WHERE {where}"
                count_query += f" WHERE {where}"
            
            # 获取总数
            cursor.execute(count_query, params)
            total = cursor.fetchone()['total']
            
            # 分页查询
            offset = (page - 1) * limit
            query += f" LIMIT {limit} OFFSET {offset}"
            
            cursor.execute(query, params)
            data = cursor.fetchall()
            
            # 获取列名
            cursor.execute(f"SHOW COLUMNS FROM {table_name}")
            columns_info = cursor.fetchall()
            columns = [col['Field'] for col in columns_info]
            
            return {
                'data': data,
                'total': total,
                'columns': columns
            }
    except Exception as e:
        logging.error(f"获取MySQL表数据失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取表数据失败: {str(e)}"
        )


@router.get("/filesystem/{datasource_id}/list", response_model=DataResponse[List[FileSystemItem]])
async def list_filesystem_files(
    datasource_id: str,
    path: str = Query("/", description="文件路径"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """获取文件系统目录列表"""
    
    # 验证数据源
    datasource = db.query(DataSource).filter(
        DataSource.id == datasource_id,
        DataSource.type == DataSourceType.FILESYSTEM
    ).first()
    
    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件系统数据源不存在"
        )
    
    try:
        # TODO: 实现文件系统浏览逻辑
        import os
        from datetime import datetime
        
        config = datasource.get_filesystem_config()
        base_path = config["path"]
        full_path = os.path.join(base_path, path.lstrip("/"))
        
        # 安全检查，防止路径遍历攻击
        if not full_path.startswith(base_path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="非法路径"
            )
        
        if not os.path.exists(full_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="路径不存在"
            )
        
        items = []
        for item_name in os.listdir(full_path):
            item_path = os.path.join(full_path, item_name)
            relative_path = os.path.join(path, item_name).replace("\\", "/")
            
            stat = os.stat(item_path)
            is_dir = os.path.isdir(item_path)
            
            # 获取文件权限信息
            permissions = ""
            try:
                mode = stat.st_mode
                if mode & 0o400: permissions += "r"  # 读权限
                if mode & 0o200: permissions += "w"  # 写权限  
                if mode & 0o100: permissions += "x"  # 执行权限
            except Exception:
                permissions = "r"  # 默认只读权限
            
            item = FileSystemItem(
                name=item_name,
                path=relative_path,
                type="directory" if is_dir else "file",
                size=0 if is_dir else stat.st_size,
                modified_at=datetime.fromtimestamp(stat.st_mtime),
                permissions=permissions,
                extension=os.path.splitext(item_name)[1] if not is_dir else None
            )
            items.append(item)
        
        # 按类型和名称排序（目录在前）
        items.sort(key=lambda x: (x.type == "file", x.name.lower()))
        
        return DataResponse(
            data=items,
            message="获取文件列表成功"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取文件列表失败: {str(e)}"
        )


@router.get("/filesystem/{datasource_id}/download")
async def download_file(
    datasource_id: str,
    path: str = Query(..., description="文件路径"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """下载文件"""
    
    # 验证数据源
    datasource = db.query(DataSource).filter(
        DataSource.id == datasource_id,
        DataSource.type == DataSourceType.FILESYSTEM
    ).first()
    
    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件系统数据源不存在"
        )
    
    try:
        import os
        import mimetypes
        
        config = datasource.get_filesystem_config()
        base_path = config["path"]
        full_path = os.path.join(base_path, path.lstrip("/"))
        
        # 安全检查
        if not full_path.startswith(base_path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="非法路径"
            )
        
        if not os.path.exists(full_path) or os.path.isdir(full_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文件不存在"
            )
        
        # 获取MIME类型
        mime_type, _ = mimetypes.guess_type(full_path)
        if mime_type is None:
            mime_type = "application/octet-stream"
        
        # 创建文件流
        def file_generator():
            with open(full_path, "rb") as file:
                while chunk := file.read(8192):
                    yield chunk
        
        filename = os.path.basename(full_path)
        
        return StreamingResponse(
            file_generator(),
            media_type=mime_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文件下载失败: {str(e)}"
        )


@router.get("/database/{datasource_id}/tables", response_model=DataResponse[List[DatabaseTable]])
async def list_database_tables(
    datasource_id: str,
    database: str = Query(None, description="数据库名"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """获取数据库表列表"""
    
    # 验证数据源
    datasource = db.query(DataSource).filter(
        DataSource.id == datasource_id,
        DataSource.type == DataSourceType.DATABASE
    ).first()
    
    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="数据库数据源不存在"
        )
    
    try:
        # 添加调试信息
        print("=" * 80)
        print("🎯 LIST DATABASE TABLES API CALLED!")
        print("=" * 80)
        print(f"📞 函数: list_database_tables")
        print(f"🆔 datasource_id: {datasource_id}")
        print(f"🗄️ database: {database}")
        print(f"👤 current_user: {current_user.username if current_user else 'None'}")
        print("=" * 80)
        
        # 实现数据库表列表获取逻辑
        print(f"🚀 开始获取数据库表列表...")
        print(f"📋 数据源名称: {datasource.name}")
        print(f"🏷️ 数据源类型: {datasource.type}")
        print(f"⚙️ 数据源配置: {datasource.config}")
        
        # 解析数据源配置
        db_config = datasource.config
        if not db_config:
            print(f"❌ 数据源配置为空!")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="数据源配置信息不完整"
            )
        
        # 根据数据库类型获取表列表
        tables = []
        db_type = db_config.get('db_type')
        print(f"🗄️ 检测到数据库类型: {db_type}")
        
        if db_type == 'MySQL':
            print(f"✅ 数据库类型匹配MySQL，开始连接...")
            connection = None
            try:
                connection = create_mysql_connection(db_config)
                tables = get_mysql_tables(connection)
                print(f"🎉 成功获取MySQL表列表，共{len(tables)}个表")
                for i, table in enumerate(tables):
                    print(f"  [{i+1}] {table.name} ({table.row_count}行) - {table.comment or '无注释'}")
            finally:
                if connection:
                    print(f"🔒 关闭MySQL连接")
                    connection.close()
        else:
            print(f"❌ 暂不支持的数据库类型: {db_type}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"暂不支持的数据库类型: {db_type}"
            )
        
        return DataResponse(
            data=tables,
            message="获取数据库表列表成功"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取数据库表列表失败: {str(e)}"
        )


@router.get("/database/{datasource_id}/tables/{table_name}/schema", response_model=DataResponse[List[DatabaseColumn]])
async def get_table_schema(
    datasource_id: str,
    table_name: str,
    database: str = Query(None, description="数据库名"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """获取数据库表结构"""
    print("=" * 80)
    print("🎯 GET TABLE SCHEMA API CALLED!")
    print("=" * 80)
    print(f"📞 函数: get_table_schema")
    print(f"🆔 datasource_id: {datasource_id}")
    print(f"📋 table_name: {table_name}")
    print(f"🗄️  database: {database}")
    
    # 验证数据源
    datasource = db.query(DataSource).filter(
        DataSource.id == datasource_id,
        DataSource.type == DataSourceType.DATABASE
    ).first()
    
    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="数据库数据源不存在"
        )
    
    print(f"✅ 找到数据源: {datasource.name}")
    print(f"🔧 数据源配置: {datasource.config}")
    
    try:
        # 解析数据源配置
        db_config = datasource.config
        if not db_config:
            print("❌ 数据源配置信息不完整")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="数据源配置信息不完整"
            )
        
        # 根据数据库类型获取表结构
        columns = []
        if db_config.get('db_type') == 'MySQL':
            print(f"🔗 连接MySQL数据库获取表 {table_name} 的结构...")
            connection = None
            try:
                connection = create_mysql_connection(db_config)
                columns = get_mysql_table_schema(connection, table_name)
                print(f"✅ 成功获取表结构，共{len(columns)}个字段")
                for col in columns:
                    print(f"  - {col.name}: {col.type} (primary: {col.is_primary_key}, nullable: {col.nullable})")
            finally:
                if connection:
                    connection.close()
                    print("🔌 已关闭数据库连接")
        else:
            print(f"❌ 暂不支持的数据库类型: {db_config.get('db_type')}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"暂不支持的数据库类型: {db_config.get('db_type')}"
            )
        
        return DataResponse(
            data=columns,
            message="获取表结构成功"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取表结构失败: {str(e)}"
        )


# MinIO对象存储API端点

@router.get("/object_storage/{datasource_id}/buckets", response_model=DataResponse[List[BucketInfo]])
async def list_buckets(
    datasource_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """获取对象存储桶列表"""
    
    # 验证数据源
    datasource = db.query(DataSource).filter(
        DataSource.id == datasource_id,
        DataSource.type == DataSourceType.OBJECT_STORAGE
    ).first()
    
    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="对象存储数据源不存在"
        )
    
    try:
        # 解析配置并创建MinIO服务实例
        config = parse_datasource_config(datasource.config)
        minio_service = create_minio_service(config)
        
        # 获取存储桶列表
        buckets = minio_service.list_buckets()
        
        # 转换为BucketInfo格式
        bucket_list = [BucketInfo(**bucket) for bucket in buckets]
        
        return DataResponse(
            data=bucket_list,
            message=f"获取存储桶列表成功，共找到 {len(bucket_list)} 个存储桶"
        )
        
    except Exception as e:
        logging.error(f"获取存储桶列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取存储桶列表失败: {str(e)}"
        )


@router.post("/object_storage/{datasource_id}/buckets", response_model=DataResponse[BucketInfo])
async def create_bucket(
    datasource_id: str,
    request: CreateBucketRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """创建存储桶"""
    
    # 验证数据源
    datasource = db.query(DataSource).filter(
        DataSource.id == datasource_id,
        DataSource.type == DataSourceType.OBJECT_STORAGE
    ).first()
    
    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="对象存储数据源不存在"
        )
    
    try:
        # 创建MinIO服务实例
        config = parse_datasource_config(datasource.config)
        minio_service = create_minio_service(config)
        
        # 创建存储桶
        success = minio_service.create_bucket(request.name, request.region)
        
        if success:
            bucket_info = BucketInfo(
                name=request.name,
                region=request.region,
                creation_date=None
            )
            
            return DataResponse(
                data=bucket_info,
                message=f"存储桶 '{request.name}' 创建成功"
            )
        else:
            raise Exception("创建存储桶失败")
            
    except Exception as e:
        logging.error(f"创建存储桶失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建存储桶失败: {str(e)}"
        )


@router.delete("/object_storage/{datasource_id}/buckets/{bucket_name}")
async def delete_bucket(
    datasource_id: str,
    bucket_name: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """删除存储桶"""
    
    # 验证数据源
    datasource = db.query(DataSource).filter(
        DataSource.id == datasource_id,
        DataSource.type == DataSourceType.OBJECT_STORAGE
    ).first()
    
    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="对象存储数据源不存在"
        )
    
    try:
        # 创建MinIO服务实例
        config = parse_datasource_config(datasource.config)
        minio_service = create_minio_service(config)
        
        # 删除存储桶
        success = minio_service.delete_bucket(bucket_name)
        
        if success:
            return DataResponse(
                data={"success": True},
                message=f"存储桶 '{bucket_name}' 删除成功"
            )
        else:
            raise Exception("删除存储桶失败")
            
    except Exception as e:
        logging.error(f"删除存储桶失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除存储桶失败: {str(e)}"
        )


@router.get("/object_storage/{datasource_id}/buckets/{bucket_name}/objects", response_model=DataResponse[List[ObjectInfo]])
async def list_objects(
    datasource_id: str,
    bucket_name: str,
    prefix: str = Query("", description="对象前缀"),
    delimiter: str = Query("", description="分隔符"),
    max_keys: int = Query(1000, ge=1, le=10000, description="最大返回数量"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """获取存储桶中的对象列表"""
    
    # 验证数据源
    datasource = db.query(DataSource).filter(
        DataSource.id == datasource_id,
        DataSource.type == DataSourceType.OBJECT_STORAGE
    ).first()
    
    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="对象存储数据源不存在"
        )
    
    try:
        # 创建MinIO服务实例
        config = parse_datasource_config(datasource.config)
        minio_service = create_minio_service(config)
        
        # 获取对象列表
        objects = minio_service.list_objects(bucket_name, prefix, delimiter, max_keys)
        
        # 转换为ObjectInfo格式
        object_list = [ObjectInfo(**obj) for obj in objects]
        
        return DataResponse(
            data=object_list,
            message=f"获取对象列表成功，共找到 {len(object_list)} 个对象"
        )
        
    except Exception as e:
        logging.error(f"获取对象列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取对象列表失败: {str(e)}"
        )


@router.post("/object_storage/{datasource_id}/buckets/{bucket_name}/objects", response_model=DataResponse[UploadResult])
async def upload_object(
    datasource_id: str,
    bucket_name: str,
    file: UploadFile = File(...),
    object_name: str = Form(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """上传对象到存储桶"""
    
    # 验证数据源
    datasource = db.query(DataSource).filter(
        DataSource.id == datasource_id,
        DataSource.type == DataSourceType.OBJECT_STORAGE
    ).first()
    
    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="对象存储数据源不存在"
        )
    
    try:
        # 创建MinIO服务实例
        config = parse_datasource_config(datasource.config)
        minio_service = create_minio_service(config)
        
        # 上传文件
        file_content = await file.read()
        file_stream = io.BytesIO(file_content)
        
        result = minio_service.upload_object(
            bucket_name=bucket_name,
            object_name=object_name,
            file_data=file_stream,
            content_type=file.content_type or "application/octet-stream"
        )
        
        upload_result = UploadResult(
            bucket_name=result["bucket_name"],
            object_name=result["object_name"],
            etag=result["etag"],
            version_id=result.get("version_id"),
            size=len(file_content)
        )
        
        return DataResponse(
            data=upload_result,
            message=f"文件 '{object_name}' 上传成功"
        )
        
    except Exception as e:
        logging.error(f"上传对象失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"上传对象失败: {str(e)}"
        )


@router.get("/object_storage/{datasource_id}/buckets/{bucket_name}/objects/{object_name}")
async def download_object(
    datasource_id: str,
    bucket_name: str,
    object_name: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> StreamingResponse:
    """下载对象"""
    
    # 验证数据源
    datasource = db.query(DataSource).filter(
        DataSource.id == datasource_id,
        DataSource.type == DataSourceType.OBJECT_STORAGE
    ).first()
    
    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="对象存储数据源不存在"
        )
    
    try:
        # 创建MinIO服务实例
        config = parse_datasource_config(datasource.config)
        minio_service = create_minio_service(config)
        
        # 获取对象信息
        obj_info = minio_service.get_object_info(bucket_name, object_name)
        
        # 下载对象
        response = minio_service.download_object(bucket_name, object_name)
        
        def iterfile():
            try:
                for chunk in response.stream(1024):
                    yield chunk
            finally:
                response.close()
                response.release_conn()
        
        return StreamingResponse(
            iterfile(),
            media_type=obj_info.get("content_type", "application/octet-stream"),
            headers={
                "Content-Disposition": f"attachment; filename={object_name}",
                "Content-Length": str(obj_info.get("size", 0))
            }
        )
        
    except Exception as e:
        logging.error(f"下载对象失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"下载对象失败: {str(e)}"
        )


@router.delete("/object_storage/{datasource_id}/buckets/{bucket_name}/objects/{object_name}")
async def delete_object(
    datasource_id: str,
    bucket_name: str,
    object_name: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """删除对象"""
    
    # 验证数据源
    datasource = db.query(DataSource).filter(
        DataSource.id == datasource_id,
        DataSource.type == DataSourceType.OBJECT_STORAGE
    ).first()
    
    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="对象存储数据源不存在"
        )
    
    try:
        # 创建MinIO服务实例
        config = parse_datasource_config(datasource.config)
        minio_service = create_minio_service(config)
        
        # 删除对象
        success = minio_service.delete_object(bucket_name, object_name)
        
        if success:
            return DataResponse(
                data={"success": True},
                message=f"对象 '{object_name}' 删除成功"
            )
        else:
            raise Exception("删除对象失败")
            
    except Exception as e:
        logging.error(f"删除对象失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除对象失败: {str(e)}"
        )


@router.get("/object_storage/{datasource_id}/buckets/{bucket_name}/objects/{object_name}/info", response_model=DataResponse[ObjectInfo])
async def get_object_info(
    datasource_id: str,
    bucket_name: str,
    object_name: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """获取对象信息"""
    
    # 验证数据源
    datasource = db.query(DataSource).filter(
        DataSource.id == datasource_id,
        DataSource.type == DataSourceType.OBJECT_STORAGE
    ).first()
    
    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="对象存储数据源不存在"
        )
    
    try:
        # 创建MinIO服务实例
        config = parse_datasource_config(datasource.config)
        minio_service = create_minio_service(config)
        
        # 获取对象信息
        obj_info = minio_service.get_object_info(bucket_name, object_name)
        
        object_info = ObjectInfo(
            key=obj_info["object_name"],
            size=obj_info["size"],
            last_modified=obj_info["last_modified"],
            etag=obj_info["etag"],
            content_type=obj_info["content_type"],
            metadata=obj_info["metadata"]
        )
        
        return DataResponse(
            data=object_info,
            message="获取对象信息成功"
        )
        
    except Exception as e:
        logging.error(f"获取对象信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取对象信息失败: {str(e)}"
        )


@router.post("/object_storage/{datasource_id}/test", response_model=DataResponse[MinIOConnectionTest])
async def test_minio_connection(
    datasource_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """测试MinIO连接"""
    
    # 验证数据源
    datasource = db.query(DataSource).filter(
        DataSource.id == datasource_id,
        DataSource.type == DataSourceType.OBJECT_STORAGE
    ).first()
    
    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="对象存储数据源不存在"
        )
    
    try:
        # 创建MinIO服务实例
        config = parse_datasource_config(datasource.config)
        minio_service = create_minio_service(config)
        
        # 测试连接
        result = minio_service.test_connection()
        
        connection_test = MinIOConnectionTest(
            success=result["success"],
            message=result["message"],
            details=result.get("details", {})
        )
        
        return DataResponse(
            data=connection_test,
            message="连接测试完成"
        )
        
    except Exception as e:
        logging.error(f"MinIO连接测试失败: {e}")
        connection_test = MinIOConnectionTest(
            success=False,
            message=f"连接测试失败: {str(e)}",
            details={"error": str(e)}
        )
        
        return DataResponse(
            data=connection_test,
            message="连接测试失败"
        )



@router.get("/database/{datasource_id}/tables/{table_name}/data")
async def get_table_data(
    datasource_id: str,
    table_name: str,
    database: str = Query(None, description="数据库名称"),
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    where: str = Query(None, description="查询条件"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """获取数据表数据"""
    
    try:
        # 获取数据源信息
        datasource = db.query(DataSource).filter(DataSource.id == datasource_id).first()
        if not datasource:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="数据源不存在"
            )
        
        if datasource.type != DataSourceType.DATABASE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="该数据源不是数据库类型"
            )
        
        # 根据数据库类型、表名和查询条件实现实际的数据查询逻辑
        logging.info(f"开始获取表数据，表名: {table_name}, 页码: {page}, 每页: {limit}")
        if where:
            logging.info(f"查询条件: {where}")
        
        # 解析数据源配置
        db_config = datasource.config
        if not db_config:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="数据源配置信息不完整"
            )
        
        # 根据数据库类型获取表数据
        if db_config.get('db_type') == 'MySQL':
            logging.info(f"连接MySQL数据库获取表 {table_name} 的数据...")
            connection = None
            try:
                connection = create_mysql_connection(db_config)
                result = get_mysql_table_data(connection, table_name, page, limit, where)
                paginated_data = result['data']
                total = result['total']
                columns = result['columns']
                logging.info(f"成功获取表数据，共{total}行，当前页{len(paginated_data)}行")
            finally:
                if connection:
                    connection.close()
        else:
            logging.warning(f"暂不支持的数据库类型: {db_config.get('db_type')}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"暂不支持的数据库类型: {db_config.get('db_type')}"
            )
        
        return {
            "code": 200,
            "data": paginated_data,
            "total": total,
            "page": page,
            "limit": limit,
            "columns": columns,
            "message": "获取表数据成功"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取表数据失败: {str(e)}"
        )
