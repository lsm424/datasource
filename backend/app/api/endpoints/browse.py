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
        connection = pymysql.connect(
            host=config.get('host', 'localhost'),
            port=config.get('port', 3306),
            user=config.get('user', 'root'),
            password=config.get('password', ''),
            database=config.get('database', ''),
            charset=config.get('charset', 'utf8mb4'),
            autocommit=True
        )
        return connection
    except Exception as e:
        logging.error(f"创建MySQL连接失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"数据库连接失败: {str(e)}"
        )

def get_mysql_tables(connection):
    """获取MySQL数据库的表列表"""
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            # 执行SHOW TABLES命令
            sql_query = "SHOW TABLES"
            cursor.execute(sql_query)
            tables_result = cursor.fetchall()
            
            tables = []
            for i, row in enumerate(tables_result):
                table_name = list(row.values())[0]  # 获取表名
                
                # 获取表的行数和注释
                info_sql = """
                    SELECT 
                        TABLE_ROWS as row_count,
                        TABLE_COMMENT as comment
                    FROM information_schema.TABLES 
                    WHERE TABLE_SCHEMA = DATABASE() 
                    AND TABLE_NAME = %s
                """
                cursor.execute(info_sql, (table_name,))
                table_info = cursor.fetchone()
                
                table_obj = DatabaseTable(
                    name=table_name,
                    schema=None,
                    row_count=table_info['row_count'] if table_info and table_info['row_count'] else 0,
                    comment=table_info['comment'] if table_info and table_info['comment'] else None
                )
                tables.append(table_obj)
            
            return tables
    except Exception as e:
        logging.error(f"获取MySQL表列表失败: {e}")
        import traceback
        logging.error(f"详细错误信息: {traceback.format_exc()}")
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
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(100, ge=1, le=1000, description="每页数量"),
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
        base_path = os.path.normpath(config["path"])  # 规范化基础路径
        
        # 对于网络挂载的路径，尝试使用实际网络路径
        try:
            real_path = os.path.realpath(base_path)
            # 如果是网络路径，使用网络路径进行访问
            if real_path.startswith('\\\\'):
                base_path = real_path
        except Exception:
            pass  # 如果无法获取实际路径，使用原路径
        
        # 处理路径分隔符，支持Windows和Linux
        if path == "/" or path == "":
            relative_path = ""
        else:
            # 移除前导斜杠，并统一使用系统路径分隔符
            relative_path = path.lstrip("/").replace("/", os.sep)
        
        full_path = os.path.join(base_path, relative_path)
        full_path = os.path.normpath(full_path)  # 规范化完整路径
        
        # 安全检查，防止路径遍历攻击
        # 使用os.path.commonpath来确保路径在基础路径内
        try:
            common_path = os.path.commonpath([base_path, full_path])
            if common_path != base_path:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="非法路径"
                )
        except ValueError:
            # 如果路径不在同一驱动器上，直接比较
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
        
        # 获取所有文件列表
        all_items = []
        for item_name in os.listdir(full_path):
            # 跳过Zone.Identifier文件（Windows安全标识文件）
            if item_name.endswith(':Zone.Identifier'):
                continue
                
            item_path = os.path.join(full_path, item_name)
            relative_path = os.path.join(path, item_name).replace("\\", "/")
            
            try:
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
                    extension=os.path.splitext(item_name)[1] if not is_dir else None,
                    status="accessible"
                )
                all_items.append(item)
                
            except (OSError, IOError) as e:
                # 处理文件锁定或其他访问错误
                if e.winerror == 33:  # Windows文件锁定错误
                    # 创建基本信息，不包含详细统计
                    item = FileSystemItem(
                        name=item_name,
                        path=relative_path,
                        type="file",  # 假设是文件
                        size=0,
                        modified_at=datetime.now(),
                        permissions="r",  # 默认只读
                        extension=os.path.splitext(item_name)[1],
                        status="locked"
                    )
                    all_items.append(item)
                else:
                    # 其他错误，跳过该文件
                    continue
        
        # 按类型和名称排序（目录在前）
        all_items.sort(key=lambda x: (x.type == "file", x.name.lower()))
        
        # 计算分页
        total_items = len(all_items)
        start_index = (page - 1) * limit
        end_index = start_index + limit
        paginated_items = all_items[start_index:end_index]
        
        return DataResponse(
            data=paginated_items,
            message=f"获取文件列表成功，共找到 {total_items} 个项目，当前页显示 {len(paginated_items)} 个",
            total=total_items,
            page=page,
            limit=limit
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
        base_path = os.path.normpath(config["path"])  # 规范化基础路径
        
        # 对于网络挂载的路径，尝试使用实际网络路径
        try:
            real_path = os.path.realpath(base_path)
            # 如果是网络路径，使用网络路径进行访问
            if real_path.startswith('\\\\'):
                base_path = real_path
        except Exception:
            pass  # 如果无法获取实际路径，使用原路径
        
        # 处理路径分隔符，支持Windows和Linux
        if path == "/" or path == "":
            relative_path = ""
        else:
            # 移除前导斜杠，并统一使用系统路径分隔符
            relative_path = path.lstrip("/").replace("/", os.sep)
        
        full_path = os.path.join(base_path, relative_path)
        full_path = os.path.normpath(full_path)  # 规范化完整路径
        
        # 安全检查，防止路径遍历攻击
        try:
            common_path = os.path.commonpath([base_path, full_path])
            if common_path != base_path:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="非法路径"
                )
        except ValueError:
            # 如果路径不在同一驱动器上，直接比较
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

        
        # 解析数据源配置
        db_config = datasource.config
        if not db_config:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="数据源配置信息不完整"
            )
        
        # 根据数据库类型获取表列表
        tables = []
        db_type = db_config.get('db_type')
        
        if db_type == 'MySQL':
            connection = None
            try:
                connection = create_mysql_connection(db_config)
                tables = get_mysql_tables(connection)
            finally:
                if connection:
                    connection.close()
        else:
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
        # 解析数据源配置
        db_config = datasource.config
        if not db_config:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="数据源配置信息不完整"
            )
        
        # 根据数据库类型获取表结构
        columns = []
        if db_config.get('db_type') == 'MySQL':
            connection = None
            try:
                connection = create_mysql_connection(db_config)
                columns = get_mysql_table_schema(connection, table_name)
            finally:
                if connection:
                    connection.close()
        else:
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


@router.get("/object_storage/{datasource_id}/download")
async def download_object(
    datasource_id: str,
    bucket: str = Query(..., description="存储桶名称"),
    key: str = Query(..., description="对象键名"),
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
        obj_info = minio_service.get_object_info(bucket, key)
        
        # 下载对象
        response = minio_service.download_object(bucket, key)
        
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
                "Content-Disposition": f"attachment; filename={key}",
                "Content-Length": str(obj_info.get("size", 0))
            }
        )
        
    except Exception as e:
        logging.error(f"下载对象失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"下载对象失败: {str(e)}"
        )


@router.delete("/object_storage/{datasource_id}")
async def delete_object(
    datasource_id: str,
    bucket: str = Query(..., description="存储桶名称"),
    key: str = Query(..., description="对象键名"),
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
        success = minio_service.delete_object(bucket, key)
        
        if success:
            return DataResponse(
                data={"success": True},
                message=f"对象 '{key}' 删除成功"
            )
        else:
            raise Exception("删除对象失败")
            
    except Exception as e:
        logging.error(f"删除对象失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除对象失败: {str(e)}"
        )


@router.get("/object_storage/{datasource_id}/info", response_model=DataResponse[ObjectInfo])
async def get_object_info(
    datasource_id: str,
    bucket: str = Query(..., description="存储桶名称"),
    key: str = Query(..., description="对象键名"),
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
        obj_info = minio_service.get_object_info(bucket, key)
        
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


@router.get("/object_storage/{datasource_id}/preview")
async def preview_object(
    datasource_id: str,
    bucket: str = Query(..., description="存储桶名称"),
    key: str = Query(..., description="对象键名"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> StreamingResponse:
    """预览对象（支持图片、视频等媒体文件直接预览）"""
    
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
        obj_info = minio_service.get_object_info(bucket, key)
        
        # 下载对象用于预览
        response = minio_service.download_object(bucket, key)
        
        def iterfile():
            try:
                for chunk in response.stream(1024):
                    yield chunk
            finally:
                response.close()
                response.release_conn()
        
        # 根据文件类型设置适当的Content-Type
        content_type = obj_info.get("content_type", "application/octet-stream")
        
        # 预览模式，不设置attachment下载头
        return StreamingResponse(
            iterfile(),
            media_type=content_type,
            headers={
                "Cache-Control": "max-age=3600",
                "Content-Length": str(obj_info.get("size", 0))
            }
        )
        
    except Exception as e:
        logging.error(f"预览对象失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"预览对象失败: {str(e)}"
        )


@router.get("/object_storage/{datasource_id}/content")
async def get_object_content(
    datasource_id: str,
    bucket: str = Query(..., description="存储桶名称"),
    key: str = Query(..., description="对象键名"),
    encoding: str = Query("utf-8", description="文本编码"),
    max_size: int = Query(1024*1024, description="最大读取大小(字节)"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """获取对象文本内容（用于文本文件预览）"""
    
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
        obj_info = minio_service.get_object_info(bucket, key)
        
        # 检查文件大小
        if obj_info.get("size", 0) > max_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"文件太大，无法预览。最大支持 {max_size/1024/1024:.1f}MB"
            )
        
        # 下载对象内容
        response = minio_service.download_object(bucket, key)
        content_bytes = response.data
        
        try:
            # 尝试解码为文本
            content_text = content_bytes.decode(encoding)
            return {"content": content_text, "encoding": encoding, "size": len(content_bytes)}
        except UnicodeDecodeError:
            # 如果无法解码，尝试其他编码
            for fallback_encoding in ['gbk', 'latin1', 'ascii']:
                try:
                    content_text = content_bytes.decode(fallback_encoding)
                    return {"content": content_text, "encoding": fallback_encoding, "size": len(content_bytes)}
                except UnicodeDecodeError:
                    continue
            
            # 如果所有编码都失败，返回错误
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="无法解码文件内容，可能不是文本文件"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"获取对象内容失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取对象内容失败: {str(e)}"
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
