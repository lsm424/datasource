"""
MinIO对象存储服务
"""
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from minio import Minio
from minio.error import S3Error
from urllib3.exceptions import MaxRetryError
import logging

logger = logging.getLogger(__name__)

class MinIOService:
    """MinIO对象存储服务类"""
    
    def __init__(self, endpoint: str, access_key: str, secret_key: str, 
                 secure: bool = True, region: Optional[str] = None):
        """
        初始化MinIO客户端
        
        Args:
            endpoint: MinIO服务端点，如：localhost:9000
            access_key: 访问密钥
            secret_key: 秘密密钥
            secure: 是否使用HTTPS
            region: 区域（可选）
        """
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.secure = secure
        self.region = region
        
        # 初始化MinIO客户端
        self.client = Minio(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
            region=region
        )
        
    def test_connection(self) -> Dict[str, Any]:
        """
        测试MinIO连接
        
        Returns:
            连接测试结果
        """
        try:
            # 尝试列出buckets来测试连接
            buckets = list(self.client.list_buckets())
            
            return {
                "success": True,
                "message": "MinIO连接成功",
                "details": {
                    "endpoint": self.endpoint,
                    "secure": self.secure,
                    "bucket_count": len(buckets),
                    "connected_at": datetime.now().isoformat()
                }
            }
        except MaxRetryError as e:
            return {
                "success": False,
                "message": f"连接失败：无法连接到MinIO服务器 {self.endpoint}",
                "details": {"error": str(e)}
            }
        except S3Error as e:
            return {
                "success": False,
                "message": f"MinIO服务错误：{e.message}",
                "details": {"code": e.code, "error": str(e)}
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"连接测试失败：{str(e)}",
                "details": {"error": str(e)}
            }

    def list_buckets(self) -> List[Dict[str, Any]]:
        """
        列出所有存储桶
        
        Returns:
            存储桶列表
        """
        try:
            buckets = self.client.list_buckets()
            bucket_list = []
            
            for bucket in buckets:
                bucket_list.append({
                    "name": bucket.name,
                    "creation_date": bucket.creation_date.isoformat() if bucket.creation_date else None,
                    "region": self.region or "us-east-1"
                })
                
            return bucket_list
            
        except S3Error as e:
            logger.error(f"列出存储桶失败: {e}")
            raise Exception(f"获取存储桶列表失败: {e.message}")
        except Exception as e:
            logger.error(f"列出存储桶失败: {e}")
            raise Exception(f"获取存储桶列表失败: {str(e)}")
    
    def list_objects(self, bucket_name: str, prefix: str = "", delimiter: str = "/", 
                    max_keys: int = 1000) -> List[Dict[str, Any]]:
        """
        列出存储桶中的对象（支持文件夹层级结构）
        
        Args:
            bucket_name: 存储桶名称  
            prefix: 对象前缀过滤
            delimiter: 分隔符，默认为"/"来支持文件夹结构
            max_keys: 最大返回数量
            
        Returns:
            对象列表（包括文件和文件夹）
        """
        try:
            # 检查存储桶是否存在
            if not self.client.bucket_exists(bucket_name):
                raise Exception(f"存储桶 '{bucket_name}' 不存在")
            
            logger.info(f"列出对象: bucket={bucket_name}, prefix='{prefix}', delimiter='{delimiter}'")
            
            # 获取所有对象（递归）
            all_objects = self.client.list_objects(
                bucket_name=bucket_name,
                prefix=prefix,
                recursive=True
            )
            
            object_list = []
            folders_set = set()  # 用于去重文件夹
            count = 0
            
            for obj in all_objects:
                if count >= max_keys:
                    break
                
                object_key = obj.object_name
                
                # 计算相对于当前prefix的路径
                if prefix:
                    if not object_key.startswith(prefix):
                        continue
                    relative_key = object_key[len(prefix):]
                else:
                    relative_key = object_key
                
                # 如果relative_key为空，跳过
                if not relative_key:
                    continue
                
                # 检查是否在子文件夹中（只有当delimiter不为空时才处理文件夹结构）
                if delimiter and delimiter in relative_key:
                    # 提取第一级文件夹名
                    folder_name = relative_key.split(delimiter)[0]
                    folder_key = prefix + folder_name + delimiter
                    
                    # 只添加一次文件夹
                    if folder_key not in folders_set:
                        folders_set.add(folder_key)
                        object_list.append({
                            "key": folder_key,
                            "size": 0,
                            "last_modified": None,
                            "etag": "",
                            "content_type": "application/x-directory", 
                            "is_dir": True,
                            "metadata": {}
                        })
                else:
                    # 这是当前目录下的文件
                    try:
                        # 获取对象的详细信息
                        stat = self.client.stat_object(bucket_name, object_key)
                        
                        object_list.append({
                            "key": object_key,
                            "size": obj.size or 0,
                            "last_modified": obj.last_modified.isoformat() if obj.last_modified else None,
                            "etag": obj.etag.replace('"', '') if obj.etag else "",
                            "content_type": stat.content_type if hasattr(stat, 'content_type') else "application/octet-stream",
                            "is_dir": False,
                            "metadata": stat.metadata if hasattr(stat, 'metadata') else {}
                        })
                    except Exception as e:
                        # 如果获取stat失败，使用基本信息
                        logger.warning(f"获取对象 {object_key} 的详细信息失败: {e}")
                        object_list.append({
                            "key": object_key,
                            "size": obj.size or 0,
                            "last_modified": obj.last_modified.isoformat() if obj.last_modified else None,
                            "etag": obj.etag.replace('"', '') if obj.etag else "",
                            "content_type": "application/octet-stream",
                            "is_dir": False,
                            "metadata": {}
                        })
                
                count += 1
                
            # 对结果进行排序：文件夹在前，然后按名称排序
            object_list.sort(key=lambda x: (not x["is_dir"], x["key"].lower()))
            
            logger.info(f"返回 {len(object_list)} 个对象/文件夹 (prefix='{prefix}')")
                
            return object_list
            
        except S3Error as e:
            logger.error(f"列出对象失败: {e}")
            raise Exception(f"获取对象列表失败: {e.message}")
        except Exception as e:
            logger.error(f"列出对象失败: {e}")
            raise Exception(f"获取对象列表失败: {str(e)}")
    
    def create_bucket(self, bucket_name: str, region: Optional[str] = None) -> bool:
        """
        创建存储桶
        
        Args:
            bucket_name: 存储桶名称
            region: 区域
            
        Returns:
            是否创建成功
        """
        try:
            if not self.client.bucket_exists(bucket_name):
                self.client.make_bucket(bucket_name, location=region or self.region)
                return True
            else:
                raise Exception(f"存储桶 '{bucket_name}' 已存在")
                
        except S3Error as e:
            logger.error(f"创建存储桶失败: {e}")
            # 检查是否是存储桶已存在的错误
            if "BucketAlreadyExists" in str(e) or "BucketAlreadyOwnedByYou" in str(e):
                raise Exception(f"存储桶 '{bucket_name}' 已存在")
            raise Exception(f"创建存储桶失败: {e}")
        except Exception as e:
            logger.error(f"创建存储桶失败: {e}")
            raise Exception(f"创建存储桶失败: {str(e)}")
    
    def delete_bucket(self, bucket_name: str) -> bool:
        """
        删除存储桶（必须为空）
        
        Args:
            bucket_name: 存储桶名称
            
        Returns:
            是否删除成功
        """
        try:
            if self.client.bucket_exists(bucket_name):
                self.client.remove_bucket(bucket_name)
                return True
            else:
                raise Exception(f"存储桶 '{bucket_name}' 不存在")
                
        except S3Error as e:
            logger.error(f"删除存储桶失败: {e}")
            raise Exception(f"删除存储桶失败: {e.message}")
        except Exception as e:
            logger.error(f"删除存储桶失败: {e}")
            raise Exception(f"删除存储桶失败: {str(e)}")
    
    def upload_object(self, bucket_name: str, object_name: str, file_data, 
                     content_type: str = "application/octet-stream") -> Dict[str, Any]:
        """
        上传对象
        
        Args:
            bucket_name: 存储桶名称
            object_name: 对象名称
            file_data: 文件数据流
            content_type: 内容类型
            
        Returns:
            上传结果
        """
        try:
            if not self.client.bucket_exists(bucket_name):
                raise Exception(f"存储桶 '{bucket_name}' 不存在")
            
            # 上传文件
            result = self.client.put_object(
                bucket_name=bucket_name,
                object_name=object_name,
                data=file_data,
                content_type=content_type
            )
            
            return {
                "bucket_name": bucket_name,
                "object_name": object_name,
                "etag": result.etag,
                "version_id": result.version_id
            }
            
        except S3Error as e:
            logger.error(f"上传对象失败: {e}")
            raise Exception(f"上传对象失败: {e.message}")
        except Exception as e:
            logger.error(f"上传对象失败: {e}")
            raise Exception(f"上传对象失败: {str(e)}")
    
    def download_object(self, bucket_name: str, object_name: str):
        """
        下载对象
        
        Args:
            bucket_name: 存储桶名称
            object_name: 对象名称
            
        Returns:
            文件数据流
        """
        try:
            if not self.client.bucket_exists(bucket_name):
                raise Exception(f"存储桶 '{bucket_name}' 不存在")
                
            response = self.client.get_object(bucket_name, object_name)
            return response
            
        except S3Error as e:
            logger.error(f"下载对象失败: {e}")
            raise Exception(f"下载对象失败: {e.message}")
        except Exception as e:
            logger.error(f"下载对象失败: {e}")
            raise Exception(f"下载对象失败: {str(e)}")
    
    def delete_object(self, bucket_name: str, object_name: str) -> bool:
        """
        删除对象
        
        Args:
            bucket_name: 存储桶名称
            object_name: 对象名称
            
        Returns:
            是否删除成功
        """
        try:
            if not self.client.bucket_exists(bucket_name):
                raise Exception(f"存储桶 '{bucket_name}' 不存在")
                
            self.client.remove_object(bucket_name, object_name)
            return True
            
        except S3Error as e:
            logger.error(f"删除对象失败: {e}")
            raise Exception(f"删除对象失败: {e.message}")
        except Exception as e:
            logger.error(f"删除对象失败: {e}")
            raise Exception(f"删除对象失败: {str(e)}")
    
    def get_object_info(self, bucket_name: str, object_name: str) -> Dict[str, Any]:
        """
        获取对象信息
        
        Args:
            bucket_name: 存储桶名称
            object_name: 对象名称
            
        Returns:
            对象信息
        """
        try:
            if not self.client.bucket_exists(bucket_name):
                raise Exception(f"存储桶 '{bucket_name}' 不存在")
                
            stat = self.client.stat_object(bucket_name, object_name)
            
            return {
                "bucket_name": bucket_name,
                "object_name": object_name,
                "size": stat.size,
                "last_modified": stat.last_modified.isoformat() if stat.last_modified else None,
                "etag": stat.etag.replace('"', '') if stat.etag else "",
                "content_type": stat.content_type if hasattr(stat, 'content_type') else "application/octet-stream",
                "metadata": stat.metadata if hasattr(stat, 'metadata') else {}
            }
            
        except S3Error as e:
            logger.error(f"获取对象信息失败: {e}")
            raise Exception(f"获取对象信息失败: {e.message}")
        except Exception as e:
            logger.error(f"获取对象信息失败: {e}")
            raise Exception(f"获取对象信息失败: {str(e)}")


def create_minio_service(config: Dict[str, Any]) -> MinIOService:
    """
    根据配置创建MinIO服务实例
    
    Args:
        config: MinIO配置
        
    Returns:
        MinIO服务实例
    """
    return MinIOService(
        endpoint=config.get("endpoint", "localhost:9000"),
        access_key=config.get("access_key", ""),
        secret_key=config.get("secret_key", ""),
        secure=config.get("ssl", config.get("use_ssl", True)),
        region=config.get("region", "us-east-1")
    )
