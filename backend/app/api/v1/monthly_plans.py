"""
APS智慧排产系统 - 月度计划API端点

月度计划相关的FastAPI路由，包括文件上传、解析和数据查询功能。
支持月度Excel计划的完整处理流程。

主要端点：
- POST /monthly-plans/upload - 月度计划文件上传
- GET /monthly-plans - 查询月度计划列表

技术特性：
- 基于FastAPI异步框架
- Pydantic数据验证
- 完整的错误处理和中文错误信息
- 符合现有API设计模式
- 集成月度特化数据模型
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from decimal import Decimal
import logging
import os
import hashlib
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from pydantic import BaseModel, Field

from app.db.connection import get_async_session
from app.models.monthly_plan_models import MonthlyPlan
from app.schemas.base import APIResponse

# 设置日志
logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/monthly-plans", tags=["月度计划"])


# Pydantic 响应模型
class MonthlyPlanUploadResponse(BaseModel):
    """月度计划上传响应模型"""
    batch_id: str = Field(..., description="批次ID")
    file_name: str = Field(..., description="文件名")
    file_size: int = Field(..., description="文件大小（字节）")
    upload_time: datetime = Field(..., description="上传时间")
    message: str = Field(..., description="响应消息")


class MonthlyPlanDetail(BaseModel):
    """月度计划详情模型"""
    monthly_plan_id: int = Field(..., description="月度计划ID")
    article_nr: str = Field(..., description="品牌规格代码")
    article_name: str = Field(..., description="品牌规格名称")
    plan_year: int = Field(..., description="计划年份")
    plan_month: int = Field(..., description="计划月份")
    target_quantity_boxes: int = Field(..., description="原计划目标产量（箱）")
    hard_pack_boxes: int = Field(..., description="硬包数量（箱）")
    soft_pack_boxes: int = Field(..., description="软包数量（箱）")

    class Config:
        from_attributes = True


# 工具函数
def generate_monthly_batch_id() -> str:
    """生成月度批次ID"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"MONTHLY_{timestamp}_{hash(timestamp) % 10000:04d}"


def get_upload_dir() -> str:
    """获取上传目录"""
    # 使用backend目录下的uploads文件夹
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    upload_dir = os.path.join(base_dir, "uploads", "monthly")
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir


async def save_uploaded_file(upload_file: UploadFile, batch_id: str) -> str:
    """保存上传的文件"""
    upload_dir = get_upload_dir()
    
    # 生成文件路径
    file_extension = os.path.splitext(upload_file.filename)[1]
    file_path = os.path.join(upload_dir, f"{batch_id}{file_extension}")
    
    # 保存文件
    try:
        with open(file_path, "wb") as buffer:
            content = await upload_file.read()
            buffer.write(content)
        
        logger.info(f"文件已保存: {file_path}")
        return file_path
    
    except Exception as e:
        logger.error(f"文件保存失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"文件保存失败: {str(e)}"
        )


# API 端点实现
@router.post("/upload", response_model=APIResponse)
async def upload_monthly_plan(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_async_session)
):
    """
    月度计划文件上传
    
    支持.xlsx和.xls格式的月度计划Excel文件上传。
    文件上传后会创建导入记录，后续可以调用解析接口进行数据解析。
    """
    try:
        # 1. 验证文件格式
        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail="文件名不能为空"
            )
        
        file_extension = os.path.splitext(file.filename)[1].lower()
        allowed_extensions = ['.xlsx', '.xls']
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件格式: {file_extension}。支持的格式: {', '.join(allowed_extensions)}"
            )
        
        # 2. 检查文件大小 (50MB)
        max_size = 50 * 1024 * 1024  # 50MB
        if file.size and file.size > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"文件大小超过限制: {file.size} > {max_size}"
            )
        
        # 3. 生成批次ID
        batch_id = generate_monthly_batch_id()
        
        # 4. 保存文件
        file_path = await save_uploaded_file(file, batch_id)
        
        # 5. 自动解析并创建计划记录
        parse_result = await _parse_and_save_monthly_plan(
            file_path, batch_id, file.filename, db
        )
        
        if not parse_result["success"]:
            raise HTTPException(
                status_code=400,
                detail=f"文件解析失败: {parse_result.get('error', '未知错误')}"
            )
        
        logger.info(f"月度计划文件上传并解析成功: {batch_id}")
        
        return APIResponse(
            code=200,
            message=f"文件上传并解析成功，批次ID: {batch_id}",
            data={
                "batch_id": batch_id,
                "file_name": file.filename,
                "file_size": file.size or 0,
                "upload_time": datetime.now().isoformat(),
                "parsed_records": parse_result.get("valid_rows", 0),
                "total_records": parse_result.get("total_rows", 0)
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"月度计划文件上传失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"文件上传失败: {str(e)}"
        )


@router.get("", response_model=APIResponse)
async def list_monthly_plans(
    batch_id: Optional[str] = Query(None, description="批次ID筛选"),
    article_nr: Optional[str] = Query(None, description="牌号代码筛选"),
    plan_year: Optional[int] = Query(None, description="计划年份筛选"),
    plan_month: Optional[int] = Query(None, description="计划月份筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    db: AsyncSession = Depends(get_async_session)
):
    """
    查询月度计划列表
    
    支持多种筛选条件的月度计划查询，包括分页功能。
    """
    try:
        # 构建查询条件
        conditions = []
        
        if batch_id:
            conditions.append(MonthlyPlan.monthly_batch_id == batch_id)
        
        if article_nr:
            conditions.append(MonthlyPlan.article_nr.like(f"%{article_nr}%"))
        
        if plan_year:
            conditions.append(MonthlyPlan.plan_year == plan_year)
        
        if plan_month:
            conditions.append(MonthlyPlan.plan_month == plan_month)
        
        # 计算总记录数
        count_stmt = select(func.count(MonthlyPlan.monthly_plan_id))
        if conditions:
            count_stmt = count_stmt.where(and_(*conditions))
        
        count_result = await db.execute(count_stmt)
        total_count = count_result.scalar()
        
        # 分页查询
        offset = (page - 1) * page_size
        plans_stmt = select(MonthlyPlan)
        
        if conditions:
            plans_stmt = plans_stmt.where(and_(*conditions))
        
        plans_stmt = plans_stmt.order_by(
            MonthlyPlan.created_time.desc()
        ).offset(offset).limit(page_size)
        
        plans_result = await db.execute(plans_stmt)
        plans = plans_result.scalars().all()
        
        # 构建响应
        plan_details = []
        for plan in plans:
            plan_details.append({
                "monthly_plan_id": plan.monthly_plan_id,
                "article_nr": plan.article_nr,
                "article_name": plan.article_name,
                "plan_year": plan.plan_year,
                "plan_month": plan.plan_month,
                "target_quantity_boxes": plan.target_quantity_boxes,
                "hard_pack_boxes": plan.hard_pack_boxes,
                "soft_pack_boxes": plan.soft_pack_boxes
            })
        
        total_pages = (total_count + page_size - 1) // page_size
        
        return APIResponse(
            code=200,
            message="查询月度计划列表成功",
            data={
                "plans": plan_details,
                "pagination": {
                    "total_count": total_count,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": total_pages
                }
            }
        )
    
    except Exception as e:
        logger.error(f"查询月度计划列表失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"查询失败: {str(e)}"
        )


# 辅助函数
async def _parse_and_save_monthly_plan(
    file_path: str, 
    batch_id: str, 
    file_name: str,
    db: AsyncSession
) -> Dict[str, Any]:
    """
    解析月度Excel文件并保存到数据库
    """
    try:
        # 导入Excel解析器
        from app.services.monthly_excel_parser import MonthlyExcelParser
        
        logger.info(f"开始解析月度Excel文件: {file_path}")
        
        # 创建解析器实例
        parser = MonthlyExcelParser()
        
        # 解析Excel文件
        parse_result = parser.parse_excel_file(file_path)
        
        if not parse_result["success"]:
            logger.error(f"Excel文件解析失败: {parse_result.get('message', '未知错误')}")
            return parse_result
        
        # 保存解析的记录到数据库
        valid_count = 0
        for record_data in parse_result["records"]:
            try:
                plan = MonthlyPlan(
                    monthly_batch_id=batch_id,
                    source_file=file_name,
                    created_time=datetime.now(),
                    created_by="system",
                    **record_data
                )
                db.add(plan)
                valid_count += 1
                
            except Exception as e:
                logger.error(f"保存记录失败: {str(e)}")
                continue
        
        # 提交到数据库
        await db.commit()
        
        logger.info(f"月度计划解析完成: 总行数={parse_result['total_rows']}, 有效记录={valid_count}")
        
        return {
            "success": True,
            "total_rows": parse_result["total_rows"],
            "valid_rows": valid_count,
            "error_rows": parse_result["error_rows"],
            "plans_created": valid_count,
            "errors": parse_result.get("errors", [])
        }
    
    except Exception as e:
        logger.error(f"Excel文件解析过程失败: {str(e)}")
        return {
            "success": False,
            "total_rows": 0,
            "valid_rows": 0,
            "error_rows": 1,
            "plans_created": 0,
            "error": str(e)
        }