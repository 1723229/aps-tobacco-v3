"""
月度排产算法基础框架

完全独立的月度排产基类和枚举，不依赖旬计划代码
"""
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import uuid
import logging


class MonthlyAlgorithmType(str, Enum):
    """月度算法类型"""
    SIMPLE = "simple"
    COMPLEX = "complex"
    OPTIMIZED = "optimized"


class MonthlyPriority(str, Enum):
    """月度优先级"""
    HIGH = "high" 
    MEDIUM = "medium"
    LOW = "low"
    URGENT = "urgent"


class MonthlyMachineType(str, Enum):
    """月度机台类型"""
    PACKING = "PACKING"  # 卷包机
    FEEDING = "FEEDING"  # 喂丝机
    COMBINED = "COMBINED"  # 合并计划


class MonthlyProcessingStage(str, Enum):
    """月度处理阶段"""
    DATA_VALIDATION = "data_validation"
    MACHINE_SELECTION = "machine_selection"
    TIME_CALCULATION = "time_calculation"
    TIME_ALLOCATION = "time_allocation"
    CAPACITY_SPLITTING = "capacity_splitting"
    SCHEDULE_GENERATION = "schedule_generation"


class MonthlyProcessingStatus(str, Enum):
    """月度处理状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class MonthlyAlgorithmResult:
    """月度算法执行结果"""
    stage: MonthlyProcessingStage
    status: MonthlyProcessingStatus = MonthlyProcessingStatus.PENDING
    success: bool = False
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    execution_time: float = 0.0
    
    # 数据结果
    input_data: List[Dict[str, Any]] = field(default_factory=list)
    output_data: List[Dict[str, Any]] = field(default_factory=list)
    
    # 错误和警告
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)
    
    # 性能指标
    processed_records: int = 0
    successful_records: int = 0
    failed_records: int = 0
    custom_metrics: Dict[str, Any] = field(default_factory=dict)
    
    def add_error(self, message: str, context: Dict[str, Any] = None):
        """添加错误信息"""
        error_entry = {
            'id': str(uuid.uuid4()),
            'timestamp': datetime.now(),
            'message': message,
            'context': context or {}
        }
        self.errors.append(error_entry)
    
    def add_warning(self, message: str, context: Dict[str, Any] = None):
        """添加警告信息"""
        warning_entry = {
            'id': str(uuid.uuid4()),
            'timestamp': datetime.now(),
            'message': message,
            'context': context or {}
        }
        self.warnings.append(warning_entry)


class MonthlyAlgorithmBase(ABC):
    """月度算法基类，完全独立于旬计划"""
    
    def __init__(self, stage: MonthlyProcessingStage, name: str = None):
        self.stage = stage
        self.name = name or self.__class__.__name__
        self.logger = self._setup_logger()
    
    def _setup_logger(self):
        """设置算法日志器"""
        logger = logging.getLogger(f"monthly_algorithm.{self.name}")
        return logger
    
    @abstractmethod
    async def execute(self, *args, **kwargs) -> MonthlyAlgorithmResult:
        """算法执行方法，子类必须实现"""
        pass
    
    def create_result(self) -> MonthlyAlgorithmResult:
        """创建算法结果对象"""
        result = MonthlyAlgorithmResult(stage=self.stage)
        result.start_time = datetime.now()
        result.status = MonthlyProcessingStatus.RUNNING
        return result
    
    def finalize_result(self, result: MonthlyAlgorithmResult) -> MonthlyAlgorithmResult:
        """完成结果对象"""
        result.end_time = datetime.now()
        if result.start_time:
            result.execution_time = (result.end_time - result.start_time).total_seconds()
        
        # 设置最终状态
        if result.errors:
            result.status = MonthlyProcessingStatus.FAILED
            result.success = False
        else:
            result.status = MonthlyProcessingStatus.COMPLETED
            result.success = True
        
        # 计算成功率
        if result.processed_records > 0:
            success_rate = result.successful_records / result.processed_records
            result.custom_metrics["success_rate"] = success_rate
        
        return result


# 月度计划项数据类
@dataclass
class MonthlyPlanItem:
    """月度计划项"""
    monthly_plan_id: str
    article_nr: str
    article_name: str
    plan_year: int
    plan_month: int
    target_quantity_boxes: int
    hard_pack_boxes: int = 0
    soft_pack_boxes: int = 0
    source_row: Optional[int] = None
    created_time: Optional[datetime] = None


# 月度调度结果数据类
@dataclass
class MonthlyScheduleResult:
    """月度调度结果"""
    work_order_nr: str
    machine_code: str
    article_nr: str
    scheduled_start_time: datetime
    scheduled_end_time: datetime
    target_quantity_boxes: int
    assigned_machines: Dict[str, str]  # {"feeder": "D1", "maker": "A1"}
    algorithm_version: str = "v2.0"
    calculation_details: Dict[str, Any] = field(default_factory=dict)


# 月度排产异常类
class MonthlySchedulingError(Exception):
    """月度排产相关异常"""
    
    def __init__(self, message: str, stage: MonthlyProcessingStage = None, context: Dict[str, Any] = None):
        super().__init__(message)
        self.stage = stage
        self.context = context or {}
        self.timestamp = datetime.now()


class MonthlyValidationError(MonthlySchedulingError):
    """月度数据验证异常"""
    pass


class MonthlyCalculationError(MonthlySchedulingError):
    """月度计算异常"""
    pass


class MonthlyAllocationError(MonthlySchedulingError):
    """月度分配异常"""
    pass
