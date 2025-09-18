"""
APS智慧排产系统 - 工作日历管理API

实现工作日历查询和管理的API端点
提供月度工作日历查询、工作日配置和节假日管理功能

端点:
- GET /api/v1/work-calendar - 工作日历查询

业务特点:
- 支持年月参数查询
- 月度特化字段管理
- 工作日类型和班次配置
- 与合约测试完全兼容
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from calendar import monthrange
import logging

from app.db.connection import get_async_session
from app.models.monthly_work_calendar_models import MonthlyWorkCalendar
from app.schemas.base import APIResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/work-calendar", tags=["工作日历管理"])


@router.get("", response_model=APIResponse)
async def get_work_calendar(
    year: Optional[int] = Query(None, ge=2020, le=2030, description="年份"),
    month: Optional[int] = Query(None, ge=1, le=12, description="月份"),
    day_type: Optional[str] = Query(None, description="日期类型过滤(WORKDAY/WEEKEND/HOLIDAY/MAINTENANCE)"),
    is_working: Optional[int] = Query(None, ge=0, le=1, description="是否工作日过滤(0/1)"),
    page: Optional[int] = Query(None, ge=1, description="页码"),
    page_size: Optional[int] = Query(None, ge=1, le=1000, description="每页数量"),
    db: AsyncSession = Depends(get_async_session)
):
    """
    工作日历查询
    
    获取指定年月的工作日历信息，支持多种过滤条件和分页
    """
    try:
        # 设置默认年月为当前年月
        current_date = datetime.now()
        if year is None:
            year = current_date.year
        if month is None:
            month = current_date.month
        
        # 验证年份范围
        if year < 2020 or year > 2030:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"年份超出支持范围(2020-2030): {year}"
            )
        
        # 验证月份范围
        if month < 1 or month > 12:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的月份值(1-12): {month}"
            )
        
        # 验证日期类型
        valid_day_types = ["WORKDAY", "WEEKEND", "HOLIDAY", "MAINTENANCE"]
        if day_type and day_type not in valid_day_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的日期类型，支持的类型: {', '.join(valid_day_types)}"
            )
        
        # 构建查询条件
        query_conditions = [
            MonthlyWorkCalendar.calendar_year == year,
            MonthlyWorkCalendar.calendar_month == month
        ]
        
        if day_type:
            query_conditions.append(MonthlyWorkCalendar.monthly_day_type == day_type)
        
        if is_working is not None:
            query_conditions.append(MonthlyWorkCalendar.monthly_is_working == is_working)
        
        # 构建查询
        query = select(MonthlyWorkCalendar).where(and_(*query_conditions)).order_by(
            MonthlyWorkCalendar.calendar_date
        )
        
        # 如果支持分页
        if page is not None and page_size is not None:
            # 查询总数
            count_query = select(func.count()).select_from(MonthlyWorkCalendar).where(and_(*query_conditions))
            count_result = await db.execute(count_query)
            total_count = count_result.scalar()
            
            # 分页查询
            offset = (page - 1) * page_size
            query = query.offset(offset).limit(page_size)
            
            # 计算分页信息
            total_pages = (total_count + page_size - 1) // page_size
            pagination = {
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": total_pages
            }
        else:
            pagination = None
        
        # 执行查询
        result = await db.execute(query)
        calendar_days_records = result.scalars().all()
        
        # 如果没有找到日历数据，可能需要生成默认日历
        if not calendar_days_records:
            # 检查是否是系统中不存在的日期
            await _ensure_calendar_exists(year, month, db)
            
            # 重新查询
            result = await db.execute(query)
            calendar_days_records = result.scalars().all()
        
        # 构建日历条目列表
        calendar_days = []
        for record in calendar_days_records:
            calendar_days.append({
                "monthly_calendar_id": record.monthly_calendar_id,
                "calendar_date": record.calendar_date.isoformat(),
                "calendar_year": record.calendar_year,
                "calendar_month": record.calendar_month,
                "calendar_day": record.calendar_day,
                "calendar_week_day": record.calendar_week_day,
                "monthly_day_type": record.monthly_day_type,
                "monthly_is_working": record.monthly_is_working,
                "monthly_shifts": record.get_shifts_config(),
                "monthly_total_hours": float(record.monthly_total_hours or 0),
                "monthly_capacity_factor": float(record.monthly_capacity_factor or 1),
                "monthly_holiday_name": record.monthly_holiday_name,
                "monthly_maintenance_type": record.monthly_maintenance_type,
                "monthly_notes": record.monthly_notes
            })
        
        # 计算统计信息
        total_work_days = len([d for d in calendar_days if d["monthly_day_type"] == "WORKDAY"])
        total_holidays = len([d for d in calendar_days if d["monthly_day_type"] == "HOLIDAY"])
        total_maintenance_days = len([d for d in calendar_days if d["monthly_day_type"] == "MAINTENANCE"])
        total_working_hours = sum(d["monthly_total_hours"] for d in calendar_days if d["monthly_is_working"] == 1)
        
        # 构建响应数据
        response_data = {
            "year": year,
            "month": month,
            "calendar_days": calendar_days,
            "total_work_days": total_work_days,
            "total_holidays": total_holidays,
            "total_maintenance_days": total_maintenance_days,
            "total_working_hours": total_working_hours
        }
        
        # 添加分页信息（如果有）
        if pagination:
            response_data["pagination"] = pagination
        
        return APIResponse(
            code=200,
            message=f"工作日历查询成功，查询到 {len(calendar_days)} 条记录",
            data=response_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询工作日历失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询工作日历失败: {str(e)}"
        )


async def _ensure_calendar_exists(year: int, month: int, db: AsyncSession):
    """
    确保指定年月的日历数据存在，如果不存在则生成默认日历
    """
    try:
        # 检查是否已存在该年月的日历数据
        check_query = select(func.count()).select_from(MonthlyWorkCalendar).where(
            and_(
                MonthlyWorkCalendar.calendar_year == year,
                MonthlyWorkCalendar.calendar_month == month
            )
        )
        count_result = await db.execute(check_query)
        existing_count = count_result.scalar()
        
        if existing_count > 0:
            return  # 已存在数据，无需生成
        
        # 生成该月的默认日历
        _, days_in_month = monthrange(year, month)
        
        calendar_records = []
        for day in range(1, days_in_month + 1):
            calendar_date = date(year, month, day)
            week_day = calendar_date.isoweekday()  # 1=星期一, 7=星期日
            
            # 判断日期类型
            if week_day in [6, 7]:  # 周六周日
                day_type = 'WEEKEND'
                is_working = 0
                total_hours = 0.0
                capacity_factor = 0.0
            else:
                day_type = 'WORKDAY'
                is_working = 1
                total_hours = 8.0
                capacity_factor = 1.0
            
            # 创建日历记录
            calendar_record = MonthlyWorkCalendar(
                calendar_date=calendar_date,
                calendar_year=year,
                calendar_month=month,
                calendar_day=day,
                calendar_week_day=week_day,
                monthly_day_type=day_type,
                monthly_is_working=is_working,
                monthly_total_hours=total_hours,
                monthly_capacity_factor=capacity_factor
            )
            
            calendar_records.append(calendar_record)
        
        # 批量插入
        db.add_all(calendar_records)
        await db.commit()
        
        logger.info(f"为 {year}-{month:02d} 生成了 {len(calendar_records)} 条默认日历记录")
        
    except Exception as e:
        logger.error(f"生成默认日历失败: {str(e)}")
        await db.rollback()
        # 不抛出异常，允许查询继续进行