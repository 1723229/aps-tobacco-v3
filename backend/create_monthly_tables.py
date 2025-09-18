#!/usr/bin/env python3
"""
APS智慧排产系统 - 月度任务表创建脚本

通过Python执行SQL脚本，创建月度排产任务相关表结构
解决外键约束问题，支持独立的月度排产任务管理
"""

import asyncio
import sys
import os
sys.path.append('/Users/spuerman/work/self_code/aps-tobacco-v3/backend')

from sqlalchemy.ext.asyncio import create_async_engine
from app.models.monthly_task_models import MonthlySchedulingTask, MonthlyProcessingLog
from app.db.connection import Base

# 数据库连接配置
DATABASE_URL = "mysql+aiomysql://aps:Aps%40123456@10.0.0.99:3306/aps"

async def create_monthly_tables():
    """创建月度任务相关表"""
    print("开始创建月度排产任务表...")
    
    # 创建异步引擎
    engine = create_async_engine(
        DATABASE_URL,
        echo=True,
        pool_pre_ping=True,
        pool_recycle=3600
    )
    
    try:
        # 创建表结构
        async with engine.begin() as conn:
            # 创建月度任务相关表
            await conn.run_sync(Base.metadata.create_all, 
                              tables=[
                                  MonthlySchedulingTask.__table__,
                                  MonthlyProcessingLog.__table__
                              ])
        
        print("✅ 月度排产任务表创建成功！")
        
        # 验证表创建
        async with engine.begin() as conn:
            # 检查表是否存在
            from sqlalchemy import text
            result = await conn.execute(
                text("SELECT COUNT(*) as count FROM information_schema.tables "
                     "WHERE table_schema='aps' AND table_name='aps_monthly_scheduling_task'")
            )
            task_table_exists = (await result.fetchone())[0] > 0
            
            result = await conn.execute(
                text("SELECT COUNT(*) as count FROM information_schema.tables "
                     "WHERE table_schema='aps' AND table_name='aps_monthly_processing_log'")
            )
            log_table_exists = (await result.fetchone())[0] > 0
            
            if task_table_exists and log_table_exists:
                print("✅ 表结构验证成功！")
                print(f"   - aps_monthly_scheduling_task: {'存在' if task_table_exists else '不存在'}")
                print(f"   - aps_monthly_processing_log: {'存在' if log_table_exists else '不存在'}")
            else:
                print("❌ 表结构验证失败！")
                return False
            
    except Exception as e:
        print(f"❌ 创建表失败: {e}")
        return False
    finally:
        await engine.dispose()
    
    return True

async def test_monthly_task_model():
    """测试月度任务模型"""
    print("\n开始测试月度任务模型...")
    
    engine = create_async_engine(DATABASE_URL, echo=False)
    
    try:
        from sqlalchemy.ext.asyncio import AsyncSession
        from sqlalchemy.orm import sessionmaker
        
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as session:
            # 创建测试任务
            test_task = MonthlySchedulingTask.create_task(
                task_id="TEST_MONTHLY_TASK_001",
                monthly_batch_id="MONTHLY_20250918_134432_1362",
                task_name="测试月度排产任务",
                algorithm_config={
                    "optimization_level": "medium",
                    "enable_load_balancing": True,
                    "max_execution_time": 300,
                    "target_efficiency": 0.85
                },
                constraints={
                    "working_hours_limit": 16,
                    "maintenance_windows": [],
                    "priority_articles": []
                },
                created_by="test_script"
            )
            
            session.add(test_task)
            await session.commit()
            await session.refresh(test_task)
            
            print(f"✅ 测试任务创建成功: {test_task.task_id}")
            
            # 测试任务状态更新
            test_task.start_execution()
            test_task.update_progress(5, 10, "测试阶段")
            await session.commit()
            
            print(f"✅ 任务状态更新成功: {test_task.task_status}, 进度: {test_task.progress}%")
            
            # 测试任务完成
            test_task.complete_execution({
                "test_result": "success",
                "processed_plans": 10
            })
            await session.commit()
            
            print(f"✅ 任务完成测试成功: {test_task.task_status}")
            
            # 清理测试数据
            await session.delete(test_task)
            await session.commit()
            
            print("✅ 测试数据清理完成")
            
    except Exception as e:
        print(f"❌ 模型测试失败: {e}")
        return False
    finally:
        await engine.dispose()
    
    return True

async def main():
    """主函数"""
    print("=== APS月度排产任务表创建和测试 ===\n")
    
    # 1. 创建表结构
    success = await create_monthly_tables()
    if not success:
        print("❌ 表创建失败，退出")
        return
    
    # 2. 测试模型功能
    success = await test_monthly_task_model()
    if not success:
        print("❌ 模型测试失败")
        return
    
    print("\n🎉 月度排产任务表创建和测试完成！")
    print("\n现在可以使用修复后的月度排产API了：")
    print("- POST /api/v1/monthly-scheduling/execute")
    print("- GET /api/v1/monthly-scheduling/tasks")

if __name__ == "__main__":
    asyncio.run(main())