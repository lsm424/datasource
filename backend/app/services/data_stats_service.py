import os
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

import pymysql
import sqlite3
import psycopg2

from app.core.database import get_db
from app.models.datasource import DataSource, DataSourceType
from app.models.data_stats import DataSourceStats, DailyStats, StatsTask
from app.schemas.base import DataResponse
from app.services.minio_service import create_minio_service

logger = logging.getLogger(__name__)


class DataSizeCalculator:
    """数据源大小计算器"""
    
    @staticmethod
    async def calculate_filesystem_size(config: Dict[str, Any]) -> Tuple[int, int, int]:
        """计算文件系统数据源大小
        返回: (数据大小bytes, 文件数量, 数据条数)
        """
        try:
            path = config.get('path', '')
            if not path or not os.path.exists(path):
                return 0, 0, 0
            
            total_size = 0
            file_count = 0
            record_count = 0  # 文件系统暂时用文件数作为记录数
            
            # 遍历目录
            for root, dirs, files in os.walk(path):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        if os.path.isfile(file_path):
                            file_size = os.path.getsize(file_path)
                            total_size += file_size
                            file_count += 1
                    except (OSError, IOError) as e:
                        logger.warning(f"无法访问文件 {file_path}: {e}")
                        continue
            
            record_count = file_count  # 对于文件系统，记录数等于文件数
            
            logger.info(f"文件系统统计完成: {path}, 大小={total_size}, 文件数={file_count}")
            return total_size, file_count, record_count
            
        except Exception as e:
            logger.error(f"计算文件系统大小失败: {e}")
            return 0, 0, 0
    
    @staticmethod
    async def calculate_database_size(config: Dict[str, Any]) -> Tuple[int, int, int]:
        """计算数据库数据源大小
        返回: (数据大小bytes, 文件数量, 数据条数)
        """
        try:
            db_type = config.get('db_type', 'MySQL')
            
            if db_type == 'MySQL':
                return await DataSizeCalculator._calculate_mysql_size(config)
            elif db_type == 'SQLite':
                return await DataSizeCalculator._calculate_sqlite_size(config)
            elif db_type == 'PostgreSQL':
                return await DataSizeCalculator._calculate_postgresql_size(config)
            else:
                logger.warning(f"不支持的数据库类型: {db_type}")
                return 0, 0, 0
                
        except Exception as e:
            logger.error(f"计算数据库大小失败: {e}")
            return 0, 0, 0
    
    @staticmethod
    async def _calculate_mysql_size(config: Dict[str, Any]) -> Tuple[int, int, int]:
        """计算MySQL数据库大小"""
        connection = None
        try:
            connection = pymysql.connect(
                host=config.get('host', 'localhost'),
                port=config.get('port', 3306),
                user=config.get('user', 'root'),
                password=config.get('password', ''),
                database=config.get('database', ''),
                charset='utf8mb4'
            )
            
            with connection.cursor() as cursor:
                # 获取数据库大小
                cursor.execute("""
                    SELECT 
                        SUM(data_length + index_length) as size_bytes,
                        SUM(table_rows) as total_rows,
                        COUNT(*) as table_count
                    FROM information_schema.tables 
                    WHERE table_schema = %s
                """, (config.get('database'),))
                
                result = cursor.fetchone()
                if result:
                    size_bytes = result[0] or 0
                    total_rows = result[1] or 0
                    table_count = result[2] or 0
                    
                    logger.info(f"MySQL统计完成: 大小={size_bytes}, 行数={total_rows}, 表数={table_count}")
                    return int(size_bytes), int(table_count), int(total_rows)
                
            return 0, 0, 0
            
        except Exception as e:
            logger.error(f"MySQL统计失败: {e}")
            return 0, 0, 0
        finally:
            if connection:
                connection.close()
    
    @staticmethod
    async def _calculate_sqlite_size(config: Dict[str, Any]) -> Tuple[int, int, int]:
        """计算SQLite数据库大小"""
        try:
            db_path = config.get('path', '')
            if not db_path or not os.path.exists(db_path):
                return 0, 0, 0
            
            # 文件大小
            file_size = os.path.getsize(db_path)
            
            # 连接数据库获取表信息
            connection = sqlite3.connect(db_path)
            cursor = connection.cursor()
            
            # 获取表数量和行数
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            table_count = len(tables)
            
            total_rows = 0
            for table in tables:
                table_name = table[0]
                cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
                rows = cursor.fetchone()[0]
                total_rows += rows
            
            connection.close()
            
            logger.info(f"SQLite统计完成: 大小={file_size}, 行数={total_rows}, 表数={table_count}")
            return int(file_size), int(table_count), int(total_rows)
            
        except Exception as e:
            logger.error(f"SQLite统计失败: {e}")
            return 0, 0, 0
    
    @staticmethod
    async def _calculate_postgresql_size(config: Dict[str, Any]) -> Tuple[int, int, int]:
        """计算PostgreSQL数据库大小"""
        connection = None
        try:
            connection = psycopg2.connect(
                host=config.get('host', 'localhost'),
                port=config.get('port', 5432),
                user=config.get('user', 'postgres'),
                password=config.get('password', ''),
                database=config.get('database', '')
            )
            
            cursor = connection.cursor()
            
            # 获取数据库大小
            cursor.execute("SELECT pg_database_size(current_database())")
            db_size = cursor.fetchone()[0]
            
            # 获取表数量和行数
            cursor.execute("""
                SELECT 
                    COUNT(*) as table_count,
                    COALESCE(SUM(n_tup_ins + n_tup_upd), 0) as total_rows
                FROM pg_stat_user_tables
            """)
            
            result = cursor.fetchone()
            table_count = result[0] or 0
            total_rows = result[1] or 0
            
            connection.close()
            
            logger.info(f"PostgreSQL统计完成: 大小={db_size}, 行数={total_rows}, 表数={table_count}")
            return int(db_size), int(table_count), int(total_rows)
            
        except Exception as e:
            logger.error(f"PostgreSQL统计失败: {e}")
            return 0, 0, 0
        finally:
            if connection:
                connection.close()
    
    @staticmethod
    async def calculate_object_storage_size(config: Dict[str, Any]) -> Tuple[int, int, int]:
        """计算对象存储数据源大小
        返回: (数据大小bytes, 文件数量, 数据条数)
        """
        try:
            # 这里需要根据具体的对象存储类型（S3、MinIO、OSS等）来实现
            # 暂时返回模拟数据
            storage_type = config.get('type', 's3')
            
            if storage_type.lower() in ['s3', 'minio']:
                return await DataSizeCalculator._calculate_s3_size(config)
            elif storage_type.lower() == 'oss':
                return await DataSizeCalculator._calculate_oss_size(config)
            else:
                logger.warning(f"不支持的对象存储类型: {storage_type}")
                return 0, 0, 0
                
        except Exception as e:
            logger.error(f"计算对象存储大小失败: {e}")
            return 0, 0, 0
    
    @staticmethod
    async def _calculate_s3_size(config: Dict[str, Any]) -> Tuple[int, int, int]:
        """计算S3兼容存储(MinIO)大小"""
        try:
            logger.info("开始统计MinIO对象存储数据")
            
            # 解析配置 - 如果是字符串，先转为字典
            if isinstance(config, str):
                config = json.loads(config)
            
            # 创建MinIO服务实例
            minio_service = create_minio_service(config)
            
            total_size = 0
            total_files = 0
            
            # 检查配置中是否指定了特定的桶
            specific_bucket = config.get('bucket')
            
            if specific_bucket:
                # 只统计指定的桶
                buckets_to_check = [{'name': specific_bucket}]
                logger.info(f"统计指定存储桶: {specific_bucket}")
            else:
                # 获取所有存储桶
                buckets_to_check = minio_service.list_buckets()
                logger.info(f"找到 {len(buckets_to_check)} 个存储桶")
            
            for bucket in buckets_to_check:
                bucket_name = bucket['name']
                logger.info(f"统计存储桶: {bucket_name}")
                
                try:
                    # 使用MinIO客户端直接遍历，避免delimiter问题
                    bucket_size = 0
                    bucket_files = 0
                    
                    # 直接使用MinIO客户端的list_objects方法
                    all_objects = minio_service.client.list_objects(
                        bucket_name=bucket_name,
                        recursive=True  # 递归获取所有对象
                    )
                    
                    for obj in all_objects:
                        if obj.size is not None:  # 这是文件，不是文件夹
                            file_size = obj.size
                            total_size += file_size
                            total_files += 1
                            bucket_size += file_size
                            bucket_files += 1
                    
                    logger.info(f"存储桶 {bucket_name} 统计完成: {bucket_files} 个文件, {bucket_size} 字节")
                    
                except Exception as bucket_error:
                    logger.warning(f"统计存储桶 {bucket_name} 失败: {bucket_error}")
                    continue
            
            logger.info(f"MinIO统计完成: 总文件数={total_files}, 总大小={total_size}字节")
            
            # 返回: (数据大小bytes, 文件数量, 数据条数)
            # 对于对象存储，数据条数等于文件数量
            return total_size, total_files, total_files
            
        except Exception as e:
            logger.error(f"MinIO统计失败: {e}")
            return 0, 0, 0
    
    @staticmethod
    async def _calculate_oss_size(config: Dict[str, Any]) -> Tuple[int, int, int]:
        """计算阿里云OSS大小"""
        try:
            # TODO: 实现OSS API调用来获取实际大小
            # 这里需要使用oss2库
            logger.info("OSS存储统计功能待实现")
            return 0, 0, 0
        except Exception as e:
            logger.error(f"OSS统计失败: {e}")
            return 0, 0, 0


class DataStatsService:
    """数据统计服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.calculator = DataSizeCalculator()
    
    async def run_daily_stats(self, target_date: datetime = None) -> bool:
        """运行每日统计任务"""
        if target_date is None:
            target_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 创建任务记录
        task = StatsTask(
            task_type="daily_stats",
            task_date=target_date,
            status="running",
            started_at=datetime.now()
        )
        self.db.add(task)
        self.db.commit()
        
        try:
            logger.info(f"开始执行每日统计任务: {target_date}")
            
            # 获取所有活跃的数据源
            datasources = self.db.query(DataSource).filter(
                DataSource.is_active == True
            ).all()
            
            task.processed_count = len(datasources)
            success_count = 0
            failed_count = 0
            
            # 统计各个数据源
            datasource_stats = []
            for ds in datasources:
                try:
                    stats = await self._calculate_single_datasource(ds, target_date)
                    if stats:
                        datasource_stats.append(stats)
                        success_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    logger.error(f"统计数据源 {ds.name} 失败: {e}")
                    failed_count += 1
            
            # 生成每日汇总统计
            daily_stats = await self._generate_daily_summary(datasource_stats, target_date)
            
            # 更新任务状态
            task.status = "completed"
            task.completed_at = datetime.now()
            task.success_count = success_count
            task.failed_count = failed_count
            task.duration_seconds = int((task.completed_at - task.started_at).total_seconds())
            
            self.db.commit()
            
            logger.info(f"每日统计任务完成: 成功{success_count}, 失败{failed_count}")
            return True
            
        except Exception as e:
            logger.error(f"每日统计任务失败: {e}")
            task.status = "failed"
            task.error_message = str(e)
            task.completed_at = datetime.now()
            self.db.commit()
            return False
    
    async def _calculate_single_datasource(self, datasource: DataSource, stats_date: datetime) -> Optional[DataSourceStats]:
        """统计单个数据源"""
        try:
            logger.info(f"开始统计数据源: {datasource.name} ({datasource.type})")
            
            # 根据数据源类型计算大小
            if datasource.type == DataSourceType.FILESYSTEM:
                data_size, file_count, record_count = await self.calculator.calculate_filesystem_size(datasource.config)
            elif datasource.type == DataSourceType.DATABASE:
                data_size, file_count, record_count = await self.calculator.calculate_database_size(datasource.config)
            elif datasource.type == DataSourceType.OBJECT_STORAGE:
                data_size, file_count, record_count = await self.calculator.calculate_object_storage_size(datasource.config)
            else:
                logger.warning(f"不支持的数据源类型: {datasource.type}")
                return None
            
            # 创建统计记录
            stats = DataSourceStats(
                datasource_id=datasource.id,
                datasource_name=datasource.name,
                datasource_type=datasource.type.value,
                record_count=record_count,
                data_size=data_size,
                file_count=file_count,
                stats_date=stats_date,
                details={
                    'config_type': datasource.config.get('type') if datasource.config else None,
                    'calculation_time': datetime.now().isoformat()
                },
                status="completed"
            )
            
            self.db.add(stats)
            self.db.commit()
            
            logger.info(f"数据源统计完成: {datasource.name}, 大小={data_size}, 文件数={file_count}, 记录数={record_count}")
            return stats
            
        except Exception as e:
            logger.error(f"统计数据源 {datasource.name} 失败: {e}")
            
            # 创建失败记录
            stats = DataSourceStats(
                datasource_id=datasource.id,
                datasource_name=datasource.name,
                datasource_type=datasource.type.value,
                record_count=0,
                data_size=0,
                file_count=0,
                stats_date=stats_date,
                status="failed",
                error_message=str(e)
            )
            self.db.add(stats)
            self.db.commit()
            
            return None
    
    async def _generate_daily_summary(self, datasource_stats: List[DataSourceStats], stats_date: datetime) -> DailyStats:
        """生成每日汇总统计"""
        try:
            # 初始化统计数据
            total_datasources = len(datasource_stats)
            total_records = sum(stats.record_count for stats in datasource_stats)
            total_data_size = sum(stats.data_size for stats in datasource_stats)
            total_files = sum(stats.file_count for stats in datasource_stats)
            
            # 按类型分组统计
            filesystem_stats = [s for s in datasource_stats if s.datasource_type == 'filesystem']
            database_stats = [s for s in datasource_stats if s.datasource_type == 'database']
            object_storage_stats = [s for s in datasource_stats if s.datasource_type == 'object_storage']
            
            # 生成分布数据
            datasource_distribution = []
            type_distribution = {
                'filesystem': {
                    'count': len(filesystem_stats),
                    'size': sum(s.data_size for s in filesystem_stats),
                    'files': sum(s.file_count for s in filesystem_stats)
                },
                'database': {
                    'count': len(database_stats),
                    'size': sum(s.data_size for s in database_stats),
                    'records': sum(s.record_count for s in database_stats)
                },
                'object_storage': {
                    'count': len(object_storage_stats),
                    'size': sum(s.data_size for s in object_storage_stats),
                    'files': sum(s.file_count for s in object_storage_stats)
                }
            }
            
            # 数据源分布（按大小排序）
            for stats in sorted(datasource_stats, key=lambda x: x.data_size, reverse=True):
                datasource_distribution.append({
                    'name': stats.datasource_name,
                    'type': stats.datasource_type,
                    'size': stats.data_size,
                    'records': stats.record_count,
                    'files': stats.file_count
                })
            
            # 检查是否已存在当日统计
            existing_stats = self.db.query(DailyStats).filter(
                DailyStats.stats_date == stats_date
            ).first()
            
            if existing_stats:
                # 更新现有记录
                daily_stats = existing_stats
            else:
                # 创建新记录
                daily_stats = DailyStats(stats_date=stats_date)
                self.db.add(daily_stats)
            
            # 更新统计数据
            daily_stats.total_datasources = total_datasources
            daily_stats.total_records = total_records
            daily_stats.total_data_size = total_data_size
            daily_stats.total_files = total_files
            
            # 按类型统计
            daily_stats.filesystem_count = len(filesystem_stats)
            daily_stats.filesystem_size = sum(s.data_size for s in filesystem_stats)
            daily_stats.filesystem_files = sum(s.file_count for s in filesystem_stats)
            
            daily_stats.database_count = len(database_stats)
            daily_stats.database_size = sum(s.data_size for s in database_stats)
            daily_stats.database_records = sum(s.record_count for s in database_stats)
            
            daily_stats.object_storage_count = len(object_storage_stats)
            daily_stats.object_storage_size = sum(s.data_size for s in object_storage_stats)
            daily_stats.object_storage_files = sum(s.file_count for s in object_storage_stats)
            
            # 分布数据
            daily_stats.datasource_distribution = datasource_distribution
            daily_stats.type_distribution = type_distribution
            daily_stats.status = "completed"
            daily_stats.updated_at = datetime.now()
            
            self.db.commit()
            
            logger.info(f"每日汇总统计生成完成: 数据源={total_datasources}, 总大小={total_data_size}")
            return daily_stats
            
        except Exception as e:
            logger.error(f"生成每日汇总统计失败: {e}")
            raise e
