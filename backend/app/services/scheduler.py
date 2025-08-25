import asyncio
import logging
from datetime import datetime, time
from typing import Optional
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.executors.asyncio import AsyncIOExecutor

from app.core.database import SessionLocal
from app.services.data_stats_service import DataStatsService

logger = logging.getLogger(__name__)


class DataStatsScheduler:
    """数据统计定时任务调度器"""
    
    def __init__(self):
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.is_running = False
    
    def start(self):
        """启动调度器"""
        if self.is_running:
            logger.warning("调度器已经在运行中")
            return
        
        try:
            # 创建调度器
            executors = {
                'default': AsyncIOExecutor()
            }
            
            job_defaults = {
                'coalesce': False,  # 不合并相同的任务
                'max_instances': 1,  # 同时只运行一个实例
                'misfire_grace_time': 3600  # 错过执行时间1小时内仍可执行
            }
            
            self.scheduler = AsyncIOScheduler(
                executors=executors,
                job_defaults=job_defaults,
                timezone='Asia/Shanghai'
            )
            
            # 添加每日统计任务 - 每天凌晨2点执行
            self.scheduler.add_job(
                func=self.run_daily_stats,
                trigger=CronTrigger(hour=2, minute=0),
                id='daily_stats',
                name='每日数据统计任务',
                replace_existing=True
            )
            
            # 添加每小时检查任务 - 每小时检查是否有遗漏的统计
            self.scheduler.add_job(
                func=self.check_missing_stats,
                trigger=CronTrigger(minute=0),
                id='hourly_check',
                name='每小时检查任务',
                replace_existing=True
            )
            
            # 启动调度器
            self.scheduler.start()
            self.is_running = True
            
            logger.info("数据统计调度器启动成功")
            logger.info("每日统计任务: 每天凌晨2:00执行")
            logger.info("检查任务: 每小时执行一次")
            
        except Exception as e:
            logger.error(f"启动调度器失败: {e}")
            raise e
    
    def stop(self):
        """停止调度器"""
        if not self.is_running or not self.scheduler:
            return
        
        try:
            self.scheduler.shutdown(wait=False)
            self.scheduler = None
            self.is_running = False
            logger.info("数据统计调度器已停止")
        except Exception as e:
            logger.error(f"停止调度器失败: {e}")
    
    async def run_daily_stats(self):
        """执行每日统计任务"""
        try:
            logger.info("开始执行每日统计任务")
            
            # 创建数据库会话
            db = SessionLocal()
            try:
                service = DataStatsService(db)
                
                # 执行统计
                success = await service.run_daily_stats()
                
                if success:
                    logger.info("每日统计任务执行成功")
                else:
                    logger.error("每日统计任务执行失败")
                    
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"每日统计任务异常: {e}")
    
    async def check_missing_stats(self):
        """检查是否有遗漏的统计任务"""
        try:
            logger.debug("检查遗漏的统计任务")
            
            db = SessionLocal()
            try:
                service = DataStatsService(db)
                
                # 检查昨天是否有统计数据
                yesterday = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                
                from app.models.data_stats import DailyStats
                
                existing_stats = db.query(DailyStats).filter(
                    DailyStats.stats_date == yesterday
                ).first()
                
                if not existing_stats:
                    logger.info(f"发现遗漏的统计任务，开始补充执行: {yesterday}")
                    await service.run_daily_stats(yesterday)
                    
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"检查遗漏统计任务异常: {e}")
    
    async def run_manual_stats(self, target_date: datetime = None):
        """手动执行统计任务"""
        try:
            logger.info(f"手动执行统计任务: {target_date}")
            
            db = SessionLocal()
            try:
                service = DataStatsService(db)
                success = await service.run_daily_stats(target_date)
                return success
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"手动统计任务异常: {e}")
            return False
    
    def get_scheduler_status(self) -> dict:
        """获取调度器状态"""
        if not self.scheduler or not self.is_running:
            return {
                'status': 'stopped',
                'jobs': [],
                'next_run_time': None
            }
        
        jobs_info = []
        for job in self.scheduler.get_jobs():
            jobs_info.append({
                'id': job.id,
                'name': job.name,
                'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            })
        
        return {
            'status': 'running',
            'jobs': jobs_info,
            'scheduler_state': str(self.scheduler.state)
        }


# 全局调度器实例
stats_scheduler = DataStatsScheduler()


@asynccontextmanager
async def get_scheduler():
    """获取调度器上下文管理器"""
    if not stats_scheduler.is_running:
        stats_scheduler.start()
    
    try:
        yield stats_scheduler
    finally:
        pass  # 不在这里关闭调度器，让其持续运行


def init_scheduler():
    """初始化调度器"""
    try:
        stats_scheduler.start()
        return True
    except Exception as e:
        logger.error(f"初始化调度器失败: {e}")
        return False


def shutdown_scheduler():
    """关闭调度器"""
    try:
        stats_scheduler.stop()
        return True
    except Exception as e:
        logger.error(f"关闭调度器失败: {e}")
        return False
