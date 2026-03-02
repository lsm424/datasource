"""
按 datasource_id 聚合返回三类数据源的全部数据：
- 对象存储(MinIO)：按桶递归列出所有对象
- 本地文件系统：递归列出目录下所有文件/目录
- 数据库：所有表及其表结构、表数据
"""
from typing import Any, List, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from urllib.parse import quote
import os
import logging
from datetime import datetime

from app.core.database import get_db
from app.core.deps import get_current_active_user, get_token_from_request
from app.models.user import User
from app.models.datasource import DataSource, DataSourceType
from app.schemas.base import DataResponse

# 复用 browse 中的配置解析与数据库工具
from app.api.endpoints.browse import (
    parse_datasource_config,
    create_mysql_connection,
    get_mysql_tables,
)
from app.services.minio_service import create_minio_service_with_retry

router = APIRouter()
logger = logging.getLogger(__name__)


def _collect_filesystem_recursive(
    base_path: str,
    base_path_norm: str,
    datasource_id: str,
    access_token: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """递归收集文件系统下所有项（目录与文件），返回可序列化的字典列表。"""
    items = []
    try:
        for root, dirs, filenames in os.walk(base_path, topdown=True):
            # 相对于 base_path 的路径（用于 path 字段）
            rel_root = os.path.relpath(root, base_path_norm)
            if rel_root == ".":
                rel_root = ""
            rel_root = rel_root.replace("\\", "/")
            if rel_root and not rel_root.endswith("/"):
                rel_root += "/"

            # for d in dirs:
            #     if d.endswith(":Zone.Identifier"):
            #         continue
            #     dir_path = os.path.join(root, d)
            #     try:
            #         stat = os.stat(dir_path)
            #         item_path = (rel_root + d).strip("/") or d
            #         items.append({
            #             "name": d,
            #             "path": "/" + item_path if item_path else "/",
            #             "type": "directory",
            #             "size": 0,
            #             "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            #             "permissions": "r",
            #             "extension": None,
            #             "status": "accessible",
            #         })
            #     except (OSError, IOError):
            #         continue

            for f in filenames:
                if f.endswith(":Zone.Identifier"):
                    continue
                file_path = os.path.join(root, f)
                try:
                    stat = os.stat(file_path)
                    item_path = (rel_root + f).replace("\\", "/")
                    url = f'http://localhost:5173/browse/filesystem/{datasource_id}/?path=/{quote(item_path, safe="/")}'
                    if access_token:
                        url += f'&token={quote(access_token, safe="")}'
                    items.append({
                        "name": f,
                        "path": "/" + item_path,
                        "type": "file",
                        "size": stat.st_size,
                        "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "permissions": "r",
                        "extension": os.path.splitext(f)[1] or None,
                        "status": "accessible",
                        "url": url,
                    })
                except (OSError, IOError):
                    items.append({
                        "name": f,
                        "path": "/" + (rel_root + f).replace("\\", "/"),
                        "type": "file",
                        "size": 0,
                        "modified_at": datetime.now().isoformat(),
                        "permissions": "r",
                        "extension": os.path.splitext(f)[1] or None,
                        "status": "locked",
                    })
    except Exception as e:
        logger.warning(f"filesystem walk error: {e}")
        raise
    return items


def _collect_object_storage_all(
    minio_service,
    datasource_id,
    access_token: Optional[str] = None,
    max_objects_per_bucket: int = 50000,
    config: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """列出桶并递归收集对象，返回 [{ bucket_name, objects }]。
    若 config 中指定了 bucket，则只读取该指定桶；否则读取所有桶。"""
    if config and config.get("bucket"):
        buckets_to_list = [{"name": config["bucket"]}]
    else:
        buckets_to_list = minio_service.list_buckets()
    result = []
    for bucket in buckets_to_list:
        bucket_name = bucket.get("name") if isinstance(bucket, dict) else getattr(bucket, "name", None)
        if not bucket_name:
            continue
        objects = []
        try:
            it = minio_service.client.list_objects(
                bucket_name=bucket_name,
                prefix="",
                recursive=True,
            )
            count = 0
            for obj in it:
                if count >= max_objects_per_bucket:
                    logger.warning(f"bucket {bucket_name} 达到单桶上限 {max_objects_per_bucket}，已截断")
                    break
                # 跳过“目录”占位对象（size=0 且 key 以 / 结尾的常见约定，或仅作前缀的 key）
                key = obj.object_name
                if not key or (getattr(obj, "size", None) == 0 and key.rstrip("/").find("/") == -1 and key.endswith("/")):
                    continue
                url = f'http://localhost:5173/browse/object_storage/{datasource_id}?bucket={bucket_name}&prefix={key}'
                if access_token:
                    url += f'&token={quote(access_token, safe="")}'
                objects.append({
                    "key": key,
                    "url": url,
                    # "size": getattr(obj, "size", None) or 0,
                    # "last_modified": obj.last_modified.isoformat() if getattr(obj, "last_modified", None) else None,
                    # "etag": (obj.etag or "").replace('"', ""),
                    # "content_type": "application/octet-stream",
                    # "is_dir": False,
                    # "metadata": {},
                })
                count += 1
        except Exception as e:
            logger.warning(f"list_objects bucket {bucket_name} error: {e}")
            result.append({"bucket_name": bucket_name, "objects": [], "error": str(e)})
            continue
        result.append({"bucket_name": bucket_name, "objects": objects})
    return result


def _collect_database_all(datasource: DataSource, datasource_id: str, access_token: Optional[str] = None,
    max_rows_per_table: int = 10000) -> List[Dict[str, Any]]:
    """
    获取数据库所有表的基本信息列表：表名称、comment、数据条数。
    """
    db_config = datasource.config
    if not db_config or db_config.get("db_type") != "MySQL":
        return []

    connection = None
    try:
        connection = create_mysql_connection(db_config)
        tables = get_mysql_tables(connection)
        result = []
        for tbl in tables:
            name = tbl.name if hasattr(tbl, "name") else tbl.get("name")
            row_count = getattr(tbl, "row_count", None) or tbl.get("row_count")
            comment = getattr(tbl, "comment", None) or tbl.get("comment")
            if row_count is None:
                row_count = 0
            result.append({
                "name": name,
                "comment": comment,
                "row_count": row_count,
                'url': f'http://localhost:5173/browse/database/{datasource_id}?table={name}&&token={quote(access_token, safe="")}',
            })
        return result
    finally:
        if connection:
            connection.close()


@router.get(
    "/datasource/{datasource_id}/all-data",
    response_model=DataResponse[Dict[str, Any]],
    summary="获取指定数据源的全部数据",
    description="根据数据源类型返回：对象存储(按桶递归)、文件系统(递归)、数据库(所有表及数据)",
)
async def get_datasource_all_data(
    datasource_id: str,
    max_rows_per_table: int = Query(10000, ge=1, le=100000, description="数据库每表最大返回行数"),
    max_objects_per_bucket: int = Query(50000, ge=1, le=100000, description="对象存储每桶最大对象数"),
    current_user: User = Depends(get_current_active_user),
    access_token: Optional[str] = Depends(get_token_from_request),
    db: Session = Depends(get_db),
) -> Any:
    """返回指定 datasource_id 下的全部数据（按类型分别处理）。"""
    datasource = db.query(DataSource).filter(DataSource.id == datasource_id).first()
    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="数据源不存在",
        )

    payload = {
        "datasource_id": datasource_id,
        "datasource_type": datasource.type.value,
        "datasource_name": datasource.name,
        "data": None,
    }

    if datasource.type == DataSourceType.FILESYSTEM:
        try:
            config = parse_datasource_config(datasource.config)
            base_path = os.path.normpath(config["path"])
            try:
                real_path = os.path.realpath(base_path)
                if real_path.startswith("\\\\"):
                    base_path = real_path
            except Exception:
                pass
            if not os.path.exists(base_path):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="配置的根路径不存在",
                )
            items = _collect_filesystem_recursive(base_path, base_path, datasource_id, access_token)
            payload["data"] = {"items": items, "total": len(items)}
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("filesystem all-data error")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"文件系统数据获取失败: {str(e)}",
            )

    elif datasource.type == DataSourceType.OBJECT_STORAGE:
        try:
            config = parse_datasource_config(datasource.config)
            minio_service = create_minio_service_with_retry(config)
            buckets_with_objects = _collect_object_storage_all(
                minio_service,
                datasource_id,
                access_token,
                max_objects_per_bucket=max_objects_per_bucket,
                config=config,
            )
            total_objects = sum(len(b.get("objects", [])) for b in buckets_with_objects)
            payload["data"] = {
                "buckets": buckets_with_objects,
                "total_buckets": len(buckets_with_objects),
                "total_objects": total_objects,
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("object_storage all-data error")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"对象存储数据获取失败: {str(e)}",
            )

    elif datasource.type == DataSourceType.DATABASE:
        try:
            tables_with_data = _collect_database_all(datasource, datasource_id, access_token, max_rows_per_table=max_rows_per_table)
            payload["data"] = {
                "tables": tables_with_data,
                "total_tables": len(tables_with_data),
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("database all-data error")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"数据库数据获取失败: {str(e)}",
            )

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的数据源类型: {datasource.type}",
        )

    return DataResponse(
        data=payload,
        message=f"已获取 {datasource.type.value} 数据源全部数据",
    )
