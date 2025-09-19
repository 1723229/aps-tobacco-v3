"""
APS智慧排产系统 - 文件上传API

实现Excel文件上传、解析和验证功能
支持异步文件处理和详细的错误报告
"""
import os
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.connection import get_async_session
from app.schemas.base import (
    FileUploadResponse, ImportBatchInfo, ParseRequest, ParseResponse,
    SuccessResponse, ErrorResponse
)
from app.services.excel_parser import parse_production_plan_excel, ExcelParseError
from app.models.base_models import ImportPlan, DecadePlan

router = APIRouter(prefix="/plans", tags=["计划文件管理"])


async def validate_excel_file(file: UploadFile) -> None:
    """验证Excel文件"""
    # 检查文件扩展名
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")
    
    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in settings.upload_allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"不支持的文件格式：{file_extension}，支持的格式：{settings.upload_allowed_extensions}"
        )
    
    # 检查文件大小
    if file.size and file.size > settings.upload_max_size:
        raise HTTPException(
            status_code=400,
            detail=f"文件大小超过限制：{file.size}字节，最大允许：{settings.upload_max_size}字节"
        )


async def check_filename_uniqueness(
    db: AsyncSession, 
    filename: str, 
    allow_overwrite: bool = False
) -> Optional[ImportPlan]:
    """
    检查文件名唯一性
    
    Args:
        db: 数据库会话
        filename: 要检查的文件名
        allow_overwrite: 是否允许覆盖已存在的文件
        
    Returns:
        如果需要覆盖，返回已存在的ImportPlan记录；否则返回None
        
    Raises:
        HTTPException: 当文件名重复且不允许覆盖时
    """
    from sqlalchemy import select, desc
    
    # 查询是否存在相同文件名的记录
    result = await db.execute(
        select(ImportPlan)
        .where(ImportPlan.file_name == filename)
        .order_by(desc(ImportPlan.created_time))
    )
    existing_plan = result.scalar_one_or_none()
    
    if existing_plan:
        # 如果不允许覆盖，直接报错
        if not allow_overwrite:
            raise HTTPException(
                status_code=400,
                detail=f"文件名 '{filename}' 已存在，上传时间：{existing_plan.created_time.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        
        # 如果允许覆盖，返回已存在的记录用于后续处理
        return existing_plan
    
    return None


async def save_uploaded_file(file: UploadFile) -> str:
    """保存上传的文件并返回文件路径"""
    # 生成唯一文件名
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(settings.upload_temp_dir, unique_filename)
    
    # 保存文件
    try:
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        return file_path
    except Exception as e:
        # 清理失败的文件
        if os.path.exists(file_path):
            os.unlink(file_path)
        raise HTTPException(status_code=500, detail=f"文件保存失败：{str(e)}")


async def create_import_record(
    db: AsyncSession, 
    import_batch_id: str,
    file_name: str,
    file_path: str,
    file_size: int
) -> ImportPlan:
    """创建导入记录"""
    import_plan = ImportPlan(
        import_batch_id=import_batch_id,
        plan_type="DECADE",  # 设置为旬计划类型
        file_name=file_name,
        file_path=file_path,
        file_size=file_size,
        import_status="UPLOADING",
        import_start_time=datetime.now(),
        created_by="api_user"
    )
    
    db.add(import_plan)
    await db.commit()
    await db.refresh(import_plan)
    return import_plan


@router.post("/upload", response_model=FileUploadResponse)
async def upload_excel_file(
    file: UploadFile = File(..., description="Excel文件"),
    allow_overwrite: bool = False,
    db: AsyncSession = Depends(get_async_session)
):
    """
    上传Excel文件接口
    
    支持的文件格式：.xlsx, .xls
    最大文件大小：50MB
    
    Args:
        file: Excel文件
        allow_overwrite: 是否允许覆盖已存在的同名文件（默认False）
        db: 数据库会话
    """
    try:
        # 验证文件
        await validate_excel_file(file)
        
        # 检查文件名唯一性
        existing_plan = await check_filename_uniqueness(db, file.filename, allow_overwrite)
        
        # 生成导入批次ID
        import_batch_id = f"IMPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        # 如果需要覆盖已存在的文件，先处理旧记录
        if existing_plan:
            # 删除旧的文件
            if existing_plan.file_path and os.path.exists(existing_plan.file_path):
                try:
                    os.unlink(existing_plan.file_path)
                except Exception as e:
                    print(f"⚠️ 删除旧文件失败: {e}")
            
            # 删除旧的decade_plan记录
            from sqlalchemy import delete
            await db.execute(
                delete(DecadePlan).where(DecadePlan.import_batch_id == existing_plan.import_batch_id)
            )
            
            # 删除旧的import_plan记录
            await db.execute(
                delete(ImportPlan).where(ImportPlan.id == existing_plan.id)
            )
            await db.commit()
        
        # 保存文件
        file_path = await save_uploaded_file(file)
        
        # 创建导入记录
        import_plan = await create_import_record(
            db=db,
            import_batch_id=import_batch_id,
            file_name=file.filename,
            file_path=file_path,
            file_size=file.size or 0
        )
        
        # 准备响应数据
        upload_info = ImportBatchInfo(
            import_batch_id=import_batch_id,
            file_name=file.filename,
            file_size=file.size or 0,
            upload_time=import_plan.created_time
        )
        
        # 根据是否覆盖文件生成不同的响应消息
        message = "文件覆盖上传成功" if existing_plan else "文件上传成功"
        
        return FileUploadResponse(
            code=200,
            message=message,
            data=upload_info.model_dump()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件上传失败：{str(e)}")


async def parse_excel_background(
    import_batch_id: str,
    file_path: str,
    db: AsyncSession
):
    """后台解析Excel文件"""
    try:
        # 更新状态为解析中
        from sqlalchemy import update
        await db.execute(
            update(ImportPlan)
            .where(ImportPlan.import_batch_id == import_batch_id)
            .values(
                import_status="PARSING",
                import_start_time=datetime.now()
            )
        )
        await db.commit()
        
        # 解析Excel文件
        parse_result = parse_production_plan_excel(file_path)
        
        # 更新导入记录
        await db.execute(
            update(ImportPlan)
            .where(ImportPlan.import_batch_id == import_batch_id)
            .values(
                total_records=parse_result['total_records'],
                valid_records=parse_result['valid_records'],
                error_records=parse_result['error_records'],
                import_status="COMPLETED",
                import_end_time=datetime.now()
            )
        )
        await db.commit()
        
        # TODO: 将解析结果保存到数据库中的详细表
        # 这里可以将 parse_result['records'] 保存到 aps_decade_plan 表
        
    except Exception as e:
        # 更新状态为失败
        await db.execute(
            update(ImportPlan)
            .where(ImportPlan.import_batch_id == import_batch_id)
            .values(
                import_status="FAILED",
                import_end_time=datetime.now(),
                error_message=str(e)
            )
        )
        await db.commit()


@router.post("/{import_batch_id}/parse", response_model=ParseResponse)
async def parse_excel_file(
    import_batch_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_session),
    force_reparse: bool = False
):
    """
    解析Excel文件接口
    
    支持后台异步解析，返回解析任务信息
    """
    try:
        # 查找导入记录
        from sqlalchemy import select
        result = await db.execute(
            select(ImportPlan).where(ImportPlan.import_batch_id == import_batch_id)
        )
        import_plan = result.scalar_one_or_none()
        
        if not import_plan:
            raise HTTPException(status_code=404, detail=f"导入批次不存在：{import_batch_id}")
        
        if not os.path.exists(import_plan.file_path):
            raise HTTPException(status_code=404, detail="源文件不存在")
        
        # 检查是否已经解析过
        if import_plan.import_status == "COMPLETED" and not force_reparse:
            raise HTTPException(status_code=400, detail="文件已经解析完成，如需重新解析请设置force_reparse=true")
        
        # 如果正在解析中
        if import_plan.import_status == "PARSING":
            return ParseResponse(
                code=202,
                message="文件正在解析中，请稍后查询结果",
                data={
                    "import_batch_id": import_batch_id,
                    "status": "PARSING",
                    "message": "解析进行中..."
                }
            )
        
        # 直接解析（同步方式，适合小文件）
        try:
            parse_result = parse_production_plan_excel(import_plan.file_path)
            
            # 更新导入记录
            from sqlalchemy import update
            await db.execute(
                update(ImportPlan)
                .where(ImportPlan.import_batch_id == import_batch_id)
                .values(
                    total_records=parse_result['total_records'],
                    valid_records=parse_result['valid_records'],
                    error_records=parse_result['error_records'],
                    import_status="COMPLETED",
                    import_end_time=datetime.now()
                )
            )
            await db.commit()
            
            # 保存解析结果到aps_decade_plan表
            await save_parse_results_to_decade_plan(db, import_batch_id, parse_result)
            
            # 转换解析结果为响应格式
            from app.schemas.base import ParseResult, ParseResultRecord, ParseErrorInfo
            
            records = []
            for record_data in parse_result['records']:
                record = ParseResultRecord(**record_data)
                records.append(record)
            
            errors = []
            for error_data in parse_result['errors']:
                error = ParseErrorInfo(**error_data)
                errors.append(error)
            
            warnings = []
            for warning_data in parse_result['warnings']:
                warning = ParseErrorInfo(**warning_data)
                warnings.append(warning)
            
            result_data = ParseResult(
                import_batch_id=import_batch_id,
                total_records=parse_result['total_records'],
                valid_records=parse_result['valid_records'],
                error_records=parse_result['error_records'],
                warning_records=parse_result['warning_records'],
                records=records,
                errors=errors,
                warnings=warnings
            )
            
            return ParseResponse(
                code=200,
                message="文件解析成功",
                data=result_data
            )
            
        except ExcelParseError as e:
            # 更新状态为失败
            from sqlalchemy import update
            await db.execute(
                update(ImportPlan)
                .where(ImportPlan.import_batch_id == import_batch_id)
                .values(
                    import_status="FAILED",
                    import_end_time=datetime.now(),
                    error_message=str(e)
                )
            )
            await db.commit()
            
            raise HTTPException(status_code=400, detail=f"Excel解析失败：{str(e)}")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解析请求处理失败：{str(e)}")


@router.get("/{import_batch_id}/status")
async def get_parse_status(
    import_batch_id: str,
    db: AsyncSession = Depends(get_async_session)
):
    """
    查询解析状态接口
    """
    try:
        from sqlalchemy import select
        result = await db.execute(
            select(ImportPlan).where(ImportPlan.import_batch_id == import_batch_id)
        )
        import_plan = result.scalar_one_or_none()
        
        if not import_plan:
            raise HTTPException(status_code=404, detail=f"导入批次不存在：{import_batch_id}")
        
        return SuccessResponse(
            code=200,
            message="查询成功",
            data={
                "import_batch_id": import_batch_id,
                "file_name": import_plan.file_name,
                "import_status": import_plan.import_status,
                "total_records": import_plan.total_records,
                "valid_records": import_plan.valid_records,
                "error_records": import_plan.error_records,
                "import_start_time": import_plan.import_start_time.isoformat() if import_plan.import_start_time else None,
                "import_end_time": import_plan.import_end_time.isoformat() if import_plan.import_end_time else None,
                "error_message": import_plan.error_message,
                "created_time": import_plan.created_time.isoformat()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"状态查询失败：{str(e)}")


async def save_parse_results_to_decade_plan(db: AsyncSession, import_batch_id: str, parse_result: dict):
    """
    将解析结果保存到aps_decade_plan表，处理聚合字段的分配逻辑
    
    Args:
        db: 数据库会话
        import_batch_id: 导入批次ID
        parse_result: 解析结果字典
    """
    try:
        # 先删除同一批次的旧数据（如果存在）
        from sqlalchemy import delete
        await db.execute(
            delete(DecadePlan).where(DecadePlan.import_batch_id == import_batch_id)
        )
        
        # 获取从Excel中提取的年份
        extracted_year = parse_result.get('extracted_year')
        print(f"📅 从解析结果获取到的年份: {extracted_year}")
        
        # 收集所有记录数据
        all_records = []
        if 'sheet_details' in parse_result and parse_result['sheet_details']:
            # 多工作表的结果
            for sheet_detail in parse_result['sheet_details']:
                for record_data in sheet_detail['records']:
                    if 'extracted_year' not in record_data and extracted_year:
                        record_data['extracted_year'] = extracted_year
                    all_records.append(record_data)
        else:
            # 单工作表的结果
            for record_data in parse_result['records']:
                if 'extracted_year' not in record_data and extracted_year:
                    record_data['extracted_year'] = extracted_year
                all_records.append(record_data)
        
        # 预处理：识别和分配聚合数值
        # Excel中同一牌号的多台机器记录需要分配聚合的"本次投料"和"本次成品"
        processed_records = await _allocate_aggregate_values_corrected(all_records)
        
        # 批量创建decade_plan记录
        decade_plans = []
        for record_data in processed_records:
            decade_plan = create_decade_plan_record(import_batch_id, record_data)
            decade_plans.append(decade_plan)
        
        # 批量插入
        if decade_plans:
            db.add_all(decade_plans)
            await db.commit()
            
        print(f"✅ 成功保存 {len(decade_plans)} 条旬计划记录到数据库（已处理聚合数值分配）")
        
    except Exception as e:
        await db.rollback()
        print(f"❌ 保存旬计划数据失败: {str(e)}")
        # 不抛出异常，避免影响解析流程
        
        

async def _allocate_aggregate_values_corrected(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    修正的聚合数值分配逻辑
    
    关键识别规则：
    1. 连续的相同牌号记录且有相同的投料/成品数值 = 需要分配的聚合组
    2. 不同牌号或数值不同的记录 = 独立记录，保持原样
    3. 只有投料或成品为0/None的记录 = 独立记录，保持原样
    
    Args:
        records: 原始记录列表
        
    Returns:
        处理后的记录列表
    """
    from collections import defaultdict
    import copy
    
    print(f"🔄 开始修正的聚合数值分配，共 {len(records)} 条记录")
    
    if not records:
        return []
    
    # 按连续的相同牌号和相同数值进行分组
    groups = []
    current_group = []
    
    for i, record in enumerate(records):
        article_name = record.get('article_name', 'UNKNOWN')
        material_input = record.get('material_input', 0) or 0
        final_quantity = record.get('final_quantity', 0) or 0
        
        print(f"  处理记录 {i+1}: {article_name} - 投料:{material_input}, 成品:{final_quantity}")
        
        # 检查是否与当前组匹配
        should_group = False
        if current_group:
            last_record = current_group[-1]
            last_article = last_record.get('article_name', 'UNKNOWN')
            last_material = last_record.get('material_input', 0) or 0
            last_final = last_record.get('final_quantity', 0) or 0
            
            # 分组条件：相同牌号 AND 相同数值 AND 数值不为0 AND 行号连续
            row_diff = record.get('row_number', 0) - last_record.get('row_number', 0)
            should_group = (
                article_name == last_article and
                material_input == last_material and
                final_quantity == last_final and
                (material_input > 0 or final_quantity > 0) and  # 至少一个不为0
                (last_material > 0 or last_final > 0) and  # 前一个记录也至少一个不为0
                1 <= row_diff <= 2  # 行号必须是递增且相近的（考虑合并单元格但不允许跳跃）
            )
        
        if should_group:
            # 加入当前组
            current_group.append(record.copy())
            print(f"    ✓ 加入当前组（组大小: {len(current_group)}）")
        else:
            # 结束当前组，开始新组
            if current_group:
                groups.append(current_group)
                print(f"    📦 完成组: {len(current_group)}条记录")
            
            current_group = [record.copy()]
            print(f"    🆕 开始新组")
    
    # 添加最后一组
    if current_group:
        groups.append(current_group)
        print(f"    📦 最后一组: {len(current_group)}条记录")
    
    print(f"📊 分组完成: 共 {len(groups)} 个组")
    
    # 处理每个组
    processed_records = []
    
    for group_idx, group_records in enumerate(groups):
        if len(group_records) == 1:
            # 单个记录，保持原样
            print(f"🎯 组 {group_idx+1}: 单条记录，保持原样")
            processed_records.append(group_records[0])
            continue
        
        # 多个记录，需要分配
        first_record = group_records[0]
        article_name = first_record.get('article_name', 'UNKNOWN')
        total_material = first_record.get('material_input', 0) or 0
        total_final = first_record.get('final_quantity', 0) or 0
        
        print(f"🎯 组 {group_idx+1}: {article_name}，{len(group_records)}条记录需要分配")
        print(f"   📦 聚合数值 - 投料:{total_material}, 成品:{total_final}")
        
        if total_material == 0 and total_final == 0:
            # 都是0，保持原样
            print(f"   ⚠️ 数值全为0，保持原样")
            processed_records.extend(group_records)
            continue
        
        # 平均分配
        machine_count = len(group_records)
        
        # 基础分配（整除）
        material_per_machine = total_material // machine_count if total_material > 0 else 0
        final_per_machine = total_final // machine_count if total_final > 0 else 0
        
        # 余数处理
        material_remainder = total_material % machine_count if total_material > 0 else 0
        final_remainder = total_final % machine_count if total_final > 0 else 0
        
        print(f"   🎲 分配策略 - 每台基础: 投料{material_per_machine}, 成品{final_per_machine}")
        print(f"   📈 余数: 投料余数{material_remainder}, 成品余数{final_remainder}")
        
        # 执行分配
        for i, record in enumerate(group_records):
            # 基础分配
            allocated_material = material_per_machine
            allocated_final = final_per_machine
            
            # 余数分配给前几个记录
            if i < material_remainder:
                allocated_material += 1
            if i < final_remainder:
                allocated_final += 1
            
            # 更新记录
            record['material_input'] = allocated_material
            record['final_quantity'] = allocated_final
            record['_allocation_info'] = {
                'original_material_input': total_material,
                'original_final_quantity': total_final,
                'machine_count': machine_count,
                'allocation_method': 'equal_distribution'
            }
            
            print(f"   ✅ 记录 {i+1}: 分配 投料{allocated_material}, 成品{allocated_final}")
            processed_records.append(record)
        
        # 验证总量
        verify_material = sum(r.get('material_input', 0) for r in group_records)
        verify_final = sum(r.get('final_quantity', 0) for r in group_records)
        
        if verify_material == total_material and verify_final == total_final:
            print(f"   ✅ 分配验证成功")
        else:
            print(f"   ❌ 分配验证失败: 投料{verify_material}/{total_material}, 成品{verify_final}/{total_final}")
    
    print(f"🎊 修正的聚合分配完成，处理后共 {len(processed_records)} 条记录")
    return processed_records


def create_decade_plan_record(import_batch_id: str, record_data: dict) -> DecadePlan:
    """
    创建旬计划记录对象，适配标准表结构
    
    Args:
        import_batch_id: 导入批次ID
        record_data: 记录数据字典
        
    Returns:
        DecadePlan: 旬计划记录对象
    """
    from datetime import datetime
    import uuid
    import re
    
    # 解析日期 - 优先从production_date_range拆解
    planned_start = None
    planned_end = None
    year = None
    
    # 获取年份 - 优先从Excel解析器提供的planned_start/planned_end数据中获取
    print(f"🔍 检查记录数据: planned_start={record_data.get('planned_start')}, planned_end={record_data.get('planned_end')}")
    
    if record_data.get('planned_start'):
        try:
            original_planned_start = datetime.fromisoformat(record_data['planned_start'])
            year = original_planned_start.year
            print(f"✅ 从planned_start获取年份: {year}")
        except Exception as e:
            print(f"❌ 解析planned_start失败: {e}")
    
    if not year and record_data.get('planned_end'):
        try:
            original_planned_end = datetime.fromisoformat(record_data['planned_end'])
            year = original_planned_end.year
            print(f"✅ 从planned_end获取年份: {year}")
        except Exception as e:
            print(f"❌ 解析planned_end失败: {e}")
    
    # 如果还没有年份，尝试从其他途径获取
    if not year:
        # 方法1：检查Excel解析器是否提供了年份信息
        if 'extracted_year' in record_data and record_data['extracted_year']:
            year = record_data['extracted_year']
            print(f"✅ 从Excel解析器获取年份: {year}")
        # 方法2：尝试从日期范围字符串中提取年份
        elif record_data.get('production_date_range'):
            date_range = record_data['production_date_range']
            # 查找可能的年份模式，如"2024.10.16-10.31"
            year_match = re.search(r'(\d{4})', str(date_range))
            if year_match:
                year = int(year_match.group(1))
                print(f"✅ 从日期范围提取年份: {year}")
        
        # 最后备选：使用2024年（根据Excel标题显示的年份）
        if not year:
            year = 2024  # 根据Excel标题"2024年10月16～31日生产作业计划表"
            print(f"⚠️ 使用默认年份2024（从Excel标题获得）: {year}")
    
    # 从production_date_range解析日期范围
    production_date_range = record_data.get('production_date_range', '')
    if production_date_range and '-' in production_date_range:
        try:
            # 解析格式如 "10.16-10.31" 或 "10.16 - 10.31"
            date_parts = production_date_range.strip().split('-')
            if len(date_parts) == 2:
                start_str = date_parts[0].strip()
                end_str = date_parts[1].strip()
                
                # 解析开始日期 "10.16"
                if '.' in start_str:
                    start_month, start_day = start_str.split('.')
                    planned_start = datetime(year, int(start_month), int(start_day))
                    print(f"✅ 从production_date_range构建planned_start: {planned_start}")
                
                # 解析结束日期 "10.31"
                if '.' in end_str:
                    end_month, end_day = end_str.split('.')
                    planned_end = datetime(year, int(end_month), int(end_day))
                    print(f"✅ 从production_date_range构建planned_end: {planned_end}")
                
        except (ValueError, IndexError) as e:
            print(f"⚠️ 解析production_date_range失败: {production_date_range}, 错误: {e}")
    
    # 如果production_date_range解析失败，尝试从原始字段解析
    if not planned_start and record_data.get('planned_start'):
        try:
            planned_start = datetime.fromisoformat(record_data['planned_start'])
        except:
            pass
    if not planned_end and record_data.get('planned_end'):
        try:
            planned_end = datetime.fromisoformat(record_data['planned_end'])
        except:
            pass
    
    # 如果还是没有日期，使用默认日期
    if not planned_start:
        planned_start = datetime(year, 11, 1)  # 使用解析出的年份，默认11月1日
        print(f"⚠️ 使用默认planned_start: {planned_start}")
    if not planned_end:
        planned_end = datetime(year, 11, 15)  # 使用解析出的年份，默认11月15日
        print(f"⚠️ 使用默认planned_end: {planned_end}")
    
    print(f"🎯 最终日期结果: planned_start={planned_start}, planned_end={planned_end}, 年份={year}")
    
    # 获取机台代码并转换为逗号分隔字符串
    feeder_codes = record_data.get('feeder_codes', [])
    maker_codes = record_data.get('maker_codes', [])
    
    # 转换为逗号分隔的字符串格式（无空格）
    feeder_code = ','.join(feeder_codes) if feeder_codes else 'UNKNOWN'
    maker_code = ','.join(maker_codes) if maker_codes else 'UNKNOWN'
    
    # 生成工作订单号（使用行号即可，不需要机台后缀）
    row_number = record_data.get('row_number', 0)
    work_order_nr = f"WO_{row_number}"
    
    # 获取数量，确保不为None
    quantity_total = record_data.get('material_input') or 0
    final_quantity = record_data.get('final_quantity') or 0
    
    # 获取牌号，使用article_name作为article_nr
    article_name = record_data.get('article_name') or 'UNKNOWN'
    article_nr = record_data.get('article_nr') or article_name
    
    # 确定验证状态
    validation_status = 'VALID'
    validation_message = None
    
    # 检查必要字段
    if not record_data.get('article_name'):
        validation_status = 'ERROR'
        validation_message = '缺少牌号信息'
    elif feeder_code == 'UNKNOWN' and maker_code == 'UNKNOWN':
        validation_status = 'ERROR'
        validation_message = '缺少机台信息'
    # 移除数量检查 - 允许继承的空值
    
    return DecadePlan(
        import_batch_id=import_batch_id,
        work_order_nr=work_order_nr,
        article_nr=article_nr,
        package_type=record_data.get('package_type'),
        specification=record_data.get('specification'),
        quantity_total=quantity_total,
        final_quantity=final_quantity,
        production_unit=record_data.get('production_unit'),
        maker_code=maker_code,
        feeder_code=feeder_code,
        planned_start=planned_start,
        planned_end=planned_end,
        production_date_range=record_data.get('production_date_range'),
        row_number=record_data.get('row_number'),
        validation_status=validation_status,
        validation_message=validation_message
    )


@router.get("/history")
async def get_upload_history(
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    scheduling_status: Optional[str] = None,  # 新增：排产状态过滤
    db: AsyncSession = Depends(get_async_session)
):
    """
    获取上传历史记录，包含排产状态信息
    
    Args:
        page: 页码，从1开始
        page_size: 每页大小，默认20
        status: 过滤状态，可选值：UPLOADING, PARSING, COMPLETED, FAILED
        scheduling_status: 排产状态过滤
            - unscheduled: 未排产
            - scheduling: 排产中  
            - completed: 排产完成
            - failed: 排产失败
        db: 数据库会话
    """
    try:
        from sqlalchemy import select, and_, desc, func, outerjoin
        from app.models.scheduling_models import SchedulingTask, SchedulingTaskStatus
        
        # 构建联合查询：ImportPlan + SchedulingTask
        base_query = select(
            ImportPlan,
            SchedulingTask.task_id,
            SchedulingTask.task_status,
            SchedulingTask.result_summary
        ).outerjoin(
            SchedulingTask, 
            ImportPlan.import_batch_id == SchedulingTask.import_batch_id
        )
        
        # 构建查询条件
        conditions = [ImportPlan.plan_type == 'DECADE']  # 只查询旬计划记录
        if status:
            conditions.append(ImportPlan.import_status == status)
            
        # 排产状态过滤
        if scheduling_status == 'unscheduled':
            conditions.append(SchedulingTask.task_id == None)
        elif scheduling_status == 'scheduling':
            conditions.append(SchedulingTask.task_status == SchedulingTaskStatus.RUNNING)
        elif scheduling_status == 'completed':
            conditions.append(SchedulingTask.task_status == SchedulingTaskStatus.COMPLETED)
        elif scheduling_status == 'failed':
            conditions.append(SchedulingTask.task_status == SchedulingTaskStatus.FAILED)
        
        if conditions:
            base_query = base_query.where(and_(*conditions))
        
        # 获取总数
        count_query = select(func.count()).select_from(ImportPlan).where(ImportPlan.plan_type == 'DECADE')
        if conditions[1:]:  # 排除第一个plan_type条件，避免重复
            count_query = count_query.outerjoin(
                SchedulingTask, 
                ImportPlan.import_batch_id == SchedulingTask.import_batch_id
            ).where(and_(*conditions))
        
        count_result = await db.execute(count_query)
        total_count = count_result.scalar()
        
        # 分页查询
        offset = (page - 1) * page_size
        query = base_query.order_by(desc(ImportPlan.created_time)).offset(offset).limit(page_size)
        
        result = await db.execute(query)
        records_with_tasks = result.fetchall()
        
        # 转换为响应格式
        records = []
        for plan, task_id, task_status, result_summary in records_with_tasks:
            # 确定排产状态
            if not task_id:
                scheduling_status_value = 'unscheduled'
                scheduling_text = '未排产'
            else:
                scheduling_status_value = task_status.value.lower()
                scheduling_text = {
                    'pending': '待排产',
                    'running': '排产中',
                    'completed': '已完成',
                    'failed': '排产失败',
                    'cancelled': '已取消'
                }.get(task_status.value.lower(), task_status.value)
            
            records.append({
                "batch_id": plan.import_batch_id,
                "file_name": plan.file_name,
                "file_size": plan.file_size,
                "upload_time": plan.created_time.isoformat(),
                "import_start_time": plan.import_start_time.isoformat() if plan.import_start_time else None,
                "import_end_time": plan.import_end_time.isoformat() if plan.import_end_time else None,
                "status": plan.import_status,
                "total_records": plan.total_records,
                "valid_records": plan.valid_records,
                "error_records": plan.error_records,
                "error_message": plan.error_message,
                
                # 新增排产相关信息
                "task_id": task_id,
                "scheduling_status": scheduling_status_value,
                "scheduling_text": scheduling_text,
                "work_orders_summary": result_summary.get('total_work_orders', 0) if result_summary else 0,
                "can_schedule": (plan.import_status == 'COMPLETED' and 
                               not task_id and 
                               plan.valid_records > 0),  # 已解析、未排产且有有效记录
            })
        
        # 计算分页信息
        total_pages = (total_count + page_size - 1) // page_size
        
        return SuccessResponse(
            code=200,
            message="查询成功",
            data={
                "records": records,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total_count": total_count,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询历史记录失败：{str(e)}")


@router.get("/statistics")
async def get_upload_statistics(
    db: AsyncSession = Depends(get_async_session)
):
    """
    获取上传统计信息
    """
    try:
        from sqlalchemy import select, func, and_
        from datetime import datetime, timedelta
        
        # 今日统计
        today = datetime.now().date()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())
        
        # 本月统计
        month_start = today.replace(day=1)
        month_start_dt = datetime.combine(month_start, datetime.min.time())
        
        # 今日上传数量
        today_uploads_result = await db.execute(
            select(func.count()).select_from(ImportPlan)
            .where(and_(
                ImportPlan.created_time >= today_start,
                ImportPlan.created_time <= today_end,
                ImportPlan.plan_type == 'DECADE'  # 只统计旬计划
            ))
        )
        today_uploads = today_uploads_result.scalar() or 0
        
        # 本月处理记录数
        monthly_records_result = await db.execute(
            select(func.sum(ImportPlan.total_records)).select_from(ImportPlan)
            .where(and_(
                ImportPlan.created_time >= month_start_dt,
                ImportPlan.import_status == 'COMPLETED',
                ImportPlan.plan_type == 'DECADE'  # 只统计旬计划
            ))
        )
        monthly_processed = monthly_records_result.scalar() or 0
        
        # 成功率计算（最近30天）
        thirty_days_ago = datetime.now() - timedelta(days=30)
        total_recent_result = await db.execute(
            select(func.count()).select_from(ImportPlan)
            .where(and_(
                ImportPlan.created_time >= thirty_days_ago,
                ImportPlan.plan_type == 'DECADE'  # 只统计旬计划
            ))
        )
        total_recent = total_recent_result.scalar() or 0
        
        success_recent_result = await db.execute(
            select(func.count()).select_from(ImportPlan)
            .where(and_(
                ImportPlan.created_time >= thirty_days_ago,
                ImportPlan.import_status == 'COMPLETED',
                ImportPlan.plan_type == 'DECADE'  # 只统计旬计划
            ))
        )
        success_recent = success_recent_result.scalar() or 0
        
        success_rate = round((success_recent / total_recent * 100), 1) if total_recent > 0 else 0
        
        # 活跃批次（解析中或最近完成的）
        active_batches_result = await db.execute(
            select(func.count()).select_from(ImportPlan)
            .where(and_(
                ImportPlan.import_status.in_(['PARSING', 'UPLOADING']),
                ImportPlan.plan_type == 'DECADE'  # 只统计旬计划
            ))
        )
        active_batches = active_batches_result.scalar() or 0
        
        return SuccessResponse(
            code=200,
            message="统计信息获取成功",
            data={
                "today_uploads": today_uploads,
                "monthly_processed": monthly_processed,
                "success_rate": success_rate,
                "active_batches": active_batches
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败：{str(e)}")


@router.get("/scheduling-statistics")
async def get_scheduling_statistics(
    db: AsyncSession = Depends(get_async_session)
):
    """
    获取排产相关的全局统计信息
    """
    try:
        from sqlalchemy import select, func, and_, outerjoin
        from app.models.scheduling_models import SchedulingTask, SchedulingTaskStatus
        
        # 构建联合查询：ImportPlan + SchedulingTask
        base_query = select(
            ImportPlan,
            SchedulingTask.task_id,
            SchedulingTask.task_status
        ).outerjoin(
            SchedulingTask, 
            ImportPlan.import_batch_id == SchedulingTask.import_batch_id
        ).where(and_(
            ImportPlan.import_status == 'COMPLETED',
            ImportPlan.plan_type == 'DECADE'  # 只统计旬计划
        ))
        
        result = await db.execute(base_query)
        all_plans = result.fetchall()
        
        # 统计各种状态
        available_plans_count = 0  # 待排产计划
        running_tasks_count = 0    # 进行中
        completed_tasks_count = 0  # 已完成
        
        for plan, task_id, task_status in all_plans:
            if not task_id:
                # 未排产的记录
                if plan.valid_records > 0:  # 只有有有效记录的才算待排产
                    available_plans_count += 1
            else:
                # 已排产的记录，根据任务状态分类
                if task_status in [SchedulingTaskStatus.PENDING, SchedulingTaskStatus.RUNNING]:
                    running_tasks_count += 1
                elif task_status == SchedulingTaskStatus.COMPLETED:
                    completed_tasks_count += 1
        
        return SuccessResponse(
            code=200,
            message="排产统计信息获取成功",
            data={
                "available_plans_count": available_plans_count,
                "running_tasks_count": running_tasks_count,
                "completed_tasks_count": completed_tasks_count
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取排产统计信息失败：{str(e)}")


@router.get("/{import_batch_id}/decade-plans")
async def get_decade_plans(
    import_batch_id: str,
    db: AsyncSession = Depends(get_async_session)
):
    """
    查询旬计划记录接口
    """
    try:
        from sqlalchemy import select
        result = await db.execute(
            select(DecadePlan).where(DecadePlan.import_batch_id == import_batch_id)
        )
        decade_plans = result.scalars().all()
        
        if not decade_plans:
            raise HTTPException(status_code=404, detail=f"未找到导入批次的旬计划记录：{import_batch_id}")
        
        # 转换为响应格式
        plans_data = []
        for plan in decade_plans:
            plans_data.append({
                "work_order_nr": plan.work_order_nr,
                "article_nr": plan.article_nr,
                "package_type": plan.package_type,
                "specification": plan.specification,
                "feeder_code": plan.feeder_code,
                "maker_code": plan.maker_code,
                "quantity_total": plan.quantity_total,
                "final_quantity": plan.final_quantity,
                "planned_start": plan.planned_start.isoformat() if plan.planned_start else None,
                "planned_end": plan.planned_end.isoformat() if plan.planned_end else None,
                "row_number": plan.row_number,
                "validation_status": plan.validation_status,
                "validation_message": plan.validation_message
            })
        
        return SuccessResponse(
            code=200,
            message="查询成功",
            data={
                "import_batch_id": import_batch_id,
                "total_plans": len(plans_data),
                "plans": plans_data
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询旬计划失败：{str(e)}")


@router.get("/available-for-scheduling")
async def get_available_batches_for_scheduling(
    db: AsyncSession = Depends(get_async_session)
):
    """
    获取可用于排产的批次列表
    条件：import_status = 'COMPLETED' 且没有对应的排产任务
    """
    try:
        from sqlalchemy import select, and_, desc, outerjoin
        from app.models.scheduling_models import SchedulingTask
        
        # 查询已解析完成但未排产的批次（必须有有效记录）
        query = select(ImportPlan).outerjoin(
            SchedulingTask, 
            ImportPlan.import_batch_id == SchedulingTask.import_batch_id
        ).where(and_(
            ImportPlan.import_status == 'COMPLETED',
            ImportPlan.plan_type == 'DECADE',  # 只查询旬计划
            ImportPlan.valid_records > 0,  # 必须有有效记录
            SchedulingTask.task_id == None  # 未排产
        )).order_by(desc(ImportPlan.created_time))
        
        result = await db.execute(query)
        import_plans = result.scalars().all()
        
        # 转换为响应格式
        available_batches = []
        for plan in import_plans:
            available_batches.append({
                "batch_id": plan.import_batch_id,
                "file_name": plan.file_name,
                "total_records": plan.total_records,
                "valid_records": plan.valid_records,
                "import_end_time": plan.import_end_time.isoformat() if plan.import_end_time else None,
                "display_name": f"{plan.file_name} ({plan.valid_records}条记录)",
                "can_schedule": True
            })
        
        return SuccessResponse(
            code=200,
            message="查询成功",
            data={
                "available_batches": available_batches,
                "total_count": len(available_batches)
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询可排产批次失败：{str(e)}")


@router.get("/{import_batch_id}/scheduling-history")
async def get_batch_scheduling_history(
    import_batch_id: str,
    db: AsyncSession = Depends(get_async_session)
):
    """
    获取特定批次的所有排产历史记录
    """
    try:
        from sqlalchemy import select, desc
        from app.models.scheduling_models import SchedulingTask
        
        # 查询该批次的所有排产任务
        query = select(SchedulingTask).where(
            SchedulingTask.import_batch_id == import_batch_id
        ).order_by(desc(SchedulingTask.created_time))
        
        result = await db.execute(query)
        tasks = result.scalars().all()
        
        # 转换为响应格式
        history_records = []
        for task in tasks:
            history_records.append({
                "task_id": task.task_id,
                "task_name": task.task_name,
                "status": task.task_status.value,
                "progress": task.progress,
                "start_time": task.start_time.isoformat() if task.start_time else None,
                "end_time": task.end_time.isoformat() if task.end_time else None,
                "execution_duration": task.execution_duration,
                "error_message": task.error_message,
                "result_summary": task.result_summary
            })
        
        return SuccessResponse(
            code=200,
            message="查询成功",
            data={
                "import_batch_id": import_batch_id,
                "total_tasks": len(history_records),
                "history": history_records
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询批次排产历史失败：{str(e)}")