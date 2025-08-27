"""
APS智慧排产系统 - API数据传输对象(DTO)

基于技术设计文档实现Pydantic模型，用于API请求和响应数据验证
确保API接口的类型安全和数据完整性
"""
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class ResponseStatus(str, Enum):
    """响应状态枚举"""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"


class BaseResponse(BaseModel):
    """基础响应模型"""
    code: int = Field(..., description="响应代码")
    message: str = Field(..., description="响应消息")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间")
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )


class SuccessResponse(BaseResponse):
    """成功响应模型"""
    code: int = Field(200, description="成功响应代码")
    status: ResponseStatus = Field(ResponseStatus.SUCCESS, description="响应状态")
    data: Optional[Dict[str, Any]] = Field(None, description="响应数据")


class ErrorResponse(BaseResponse):
    """错误响应模型"""
    code: int = Field(400, description="错误响应代码")
    status: ResponseStatus = Field(ResponseStatus.ERROR, description="响应状态")
    error_details: Optional[Dict[str, Any]] = Field(None, description="错误详情")


# 文件上传相关模型
class FileUploadResponse(SuccessResponse):
    """文件上传响应模型"""
    data: Dict[str, Any] = Field(..., description="上传结果数据")


class ImportBatchInfo(BaseModel):
    """导入批次信息"""
    import_batch_id: str = Field(..., description="导入批次ID")
    file_name: str = Field(..., description="文件名")
    file_size: int = Field(..., description="文件大小（字节）")
    total_records: int = Field(0, description="总记录数")
    upload_time: datetime = Field(default_factory=datetime.now, description="上传时间")


# Excel解析相关模型
class ParseRequest(BaseModel):
    """解析请求模型"""
    import_batch_id: str = Field(..., description="导入批次ID")
    force_reparse: bool = Field(False, description="是否强制重新解析")


class ParseResultRecord(BaseModel):
    """解析结果记录模型"""
    row_number: int = Field(..., description="行号")
    package_type: Optional[str] = Field(None, description="包装类型")
    specification: Optional[str] = Field(None, description="规格")
    feeder_codes: List[str] = Field(default_factory=list, description="喂丝机代码列表")
    maker_codes: List[str] = Field(default_factory=list, description="卷包机代码列表")
    production_unit: Optional[str] = Field(None, description="生产单元")
    article_name: Optional[str] = Field(None, description="牌号")
    article_nr: Optional[str] = Field(None, description="物料编号")
    material_input: Optional[int] = Field(None, description="投料量")
    final_quantity: Optional[int] = Field(None, description="成品量")
    production_date_range: Optional[str] = Field(None, description="生产日期范围")
    planned_start: Optional[datetime] = Field(None, description="计划开始时间")
    planned_end: Optional[datetime] = Field(None, description="计划结束时间")
    validation_status: str = Field("VALID", description="验证状态")
    validation_message: Optional[str] = Field(None, description="验证信息")


class ParseErrorInfo(BaseModel):
    """解析错误信息"""
    type: str = Field(..., description="错误类型")
    message: str = Field(..., description="错误消息")
    timestamp: datetime = Field(..., description="错误时间")


class ParseResult(BaseModel):
    """解析结果模型"""
    import_batch_id: str = Field(..., description="导入批次ID")
    total_records: int = Field(..., description="总记录数")
    valid_records: int = Field(..., description="有效记录数")
    error_records: int = Field(..., description="错误记录数")
    warning_records: int = Field(..., description="警告记录数")
    records: List[ParseResultRecord] = Field(..., description="解析记录列表")
    errors: List[ParseErrorInfo] = Field(..., description="错误列表")
    warnings: List[ParseErrorInfo] = Field(..., description="警告列表")
    parse_time: datetime = Field(default_factory=datetime.now, description="解析时间")


class ParseResponse(SuccessResponse):
    """解析响应模型"""
    data: ParseResult = Field(..., description="解析结果")


# 查询相关模型
class PaginationParams(BaseModel):
    """分页参数"""
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(20, ge=1, le=100, description="每页大小")


class ImportPlanQuery(PaginationParams):
    """导入计划查询参数"""
    import_status: Optional[str] = Field(None, description="导入状态过滤")
    file_name: Optional[str] = Field(None, description="文件名过滤")
    start_date: Optional[datetime] = Field(None, description="开始日期")
    end_date: Optional[datetime] = Field(None, description="结束日期")


class ImportPlanInfo(BaseModel):
    """导入计划信息"""
    id: int = Field(..., description="主键ID")
    import_batch_id: str = Field(..., description="导入批次ID")
    file_name: str = Field(..., description="文件名")
    file_size: Optional[int] = Field(None, description="文件大小")
    total_records: int = Field(0, description="总记录数")
    valid_records: int = Field(0, description="有效记录数")
    error_records: int = Field(0, description="错误记录数")
    import_status: str = Field(..., description="导入状态")
    import_start_time: Optional[datetime] = Field(None, description="导入开始时间")
    import_end_time: Optional[datetime] = Field(None, description="导入结束时间")
    created_time: datetime = Field(..., description="创建时间")
    
    model_config = ConfigDict(from_attributes=True)


class PaginatedResponse(BaseModel):
    """分页响应模型"""
    content: List[Any] = Field(..., description="数据内容")
    total_elements: int = Field(..., description="总元素数")
    total_pages: int = Field(..., description="总页数")
    pageable: Dict[str, int] = Field(..., description="分页信息")
    
    @classmethod
    def create(cls, items: List[Any], total: int, page: int, size: int):
        """创建分页响应"""
        total_pages = (total + size - 1) // size
        return cls(
            content=items,
            total_elements=total,
            total_pages=total_pages,
            pageable={
                "page_number": page,
                "page_size": size,
            }
        )


class ImportPlanListResponse(SuccessResponse):
    """导入计划列表响应"""
    data: PaginatedResponse = Field(..., description="分页数据")


# 健康检查相关模型
class HealthCheckItem(BaseModel):
    """健康检查项目"""
    status: str = Field(..., description="健康状态")
    response_time_ms: Optional[float] = Field(None, description="响应时间(毫秒)")
    details: Optional[Dict[str, Any]] = Field(None, description="详细信息")


class HealthCheckResponse(BaseModel):
    """健康检查响应"""
    status: str = Field(..., description="整体健康状态")
    timestamp: datetime = Field(default_factory=datetime.now, description="检查时间")
    version: str = Field(..., description="应用版本")
    checks: Dict[str, HealthCheckItem] = Field(..., description="各组件检查结果")


# 配置信息模型
class DatabaseConfig(BaseModel):
    """数据库配置信息"""
    type: str = Field(..., description="数据库类型")
    pool_size: int = Field(..., description="连接池大小")
    echo: bool = Field(..., description="是否回显SQL")


class RedisConfig(BaseModel):
    """Redis配置信息"""
    max_connections: int = Field(..., description="最大连接数")
    decode_responses: bool = Field(..., description="是否解码响应")


class UploadConfig(BaseModel):
    """上传配置信息"""
    max_size_mb: int = Field(..., description="最大文件大小(MB)")
    allowed_extensions: List[str] = Field(..., description="允许的文件扩展名")


class BusinessConfig(BaseModel):
    """业务配置信息"""
    default_efficiency_rate: float = Field(..., description="默认效率系数")
    max_retry_count: int = Field(..., description="最大重试次数")
    scheduling_timeout: int = Field(..., description="排产超时时间")


class SystemConfigResponse(BaseModel):
    """系统配置响应"""
    app_name: str = Field(..., description="应用名称")
    app_version: str = Field(..., description="应用版本")
    debug: bool = Field(..., description="调试模式")
    environment: str = Field(..., description="运行环境")
    database: DatabaseConfig = Field(..., description="数据库配置")
    redis: RedisConfig = Field(..., description="Redis配置")
    upload: UploadConfig = Field(..., description="上传配置")
    business: BusinessConfig = Field(..., description="业务配置")


# 机台和物料相关模型
class MachineInfo(BaseModel):
    """机台信息"""
    id: int = Field(..., description="主键ID")
    machine_code: str = Field(..., description="机台代码")
    machine_name: str = Field(..., description="机台名称")
    machine_type: str = Field(..., description="机台类型")
    equipment_type: Optional[str] = Field(None, description="设备型号")
    production_line: Optional[str] = Field(None, description="生产线")
    status: str = Field(..., description="机台状态")
    
    model_config = ConfigDict(from_attributes=True)


class MaterialInfo(BaseModel):
    """物料信息"""
    id: int = Field(..., description="主键ID")
    article_nr: str = Field(..., description="物料编号")
    article_name: str = Field(..., description="物料名称")
    material_type: str = Field(..., description="物料类型")
    package_type: Optional[str] = Field(None, description="包装类型")
    specification: Optional[str] = Field(None, description="规格")
    unit: str = Field(..., description="计量单位")
    status: str = Field(..., description="状态")
    
    model_config = ConfigDict(from_attributes=True)