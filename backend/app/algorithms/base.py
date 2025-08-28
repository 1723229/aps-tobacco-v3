"""
APS智慧排产系统 - 算法基础框架

定义算法接口、基类、数据结构和枚举类型
为所有排产算法提供统一的接口规范
"""
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import uuid


class ProcessingStage(str, Enum):
    """处理阶段枚举"""
    DATA_PREPROCESSING = "data_preprocessing"
    RULE_MERGING = "rule_merging"
    RULE_SPLITTING = "rule_splitting"  
    TIME_CORRECTION = "time_correction"
    PARALLEL_PROCESSING = "parallel_processing"
    WORK_ORDER_GENERATION = "work_order_generation"


class ProcessingStatus(str, Enum):
    """处理状态枚举"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AlgorithmMetrics:
    """算法执行指标"""
    execution_time: float = 0.0
    processed_records: int = 0
    success_records: int = 0
    error_records: int = 0
    custom_metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AlgorithmResult:
    """算法执行结果"""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    stage: ProcessingStage = ProcessingStage.DATA_PREPROCESSING
    status: ProcessingStatus = ProcessingStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    success: bool = True
    
    input_data: List[Dict[str, Any]] = field(default_factory=list)
    output_data: List[Dict[str, Any]] = field(default_factory=list)
    metrics: AlgorithmMetrics = field(default_factory=AlgorithmMetrics)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    
    def add_error(self, message: str, context: Dict[str, Any] = None):
        """添加错误信息"""
        error_entry = {
            'message': message,
            'timestamp': datetime.now(),
            'context': context or {}
        }
        self.errors.append(error_entry)


class AlgorithmBase(ABC):
    """算法基类"""
    
    def __init__(self, stage: ProcessingStage):
        self.stage = stage
        
    @abstractmethod
    def process(self, input_data: List[Dict[str, Any]], **kwargs) -> AlgorithmResult:
        """算法主处理方法"""
        pass
    
    def create_result(self) -> AlgorithmResult:
        """创建算法结果对象"""
        result = AlgorithmResult(stage=self.stage)
        result.start_time = datetime.now()
        return result
    
    def finalize_result(self, result: AlgorithmResult) -> AlgorithmResult:
        """完成结果对象"""
        result.end_time = datetime.now()
        if result.start_time:
            result.metrics.execution_time = (result.end_time - result.start_time).total_seconds()
        
        result.metrics.success_records = result.metrics.processed_records - result.metrics.error_records
        result.status = ProcessingStatus.COMPLETED
        
        return result