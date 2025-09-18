"""
APS月度排产算法 - 基础配置和公共工具

提供所有算法模块共享的配置、常量、工具函数和基类
"""

import logging
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from enum import Enum

# =============================================================================
# 算法配置常量
# =============================================================================

class AlgorithmType(Enum):
    """算法类型枚举"""
    CALENDAR_SERVICE = "calendar_service"
    MACHINE_SELECTOR = "machine_selector"  
    CAPACITY_CALCULATOR = "capacity_calculator"
    TIME_ALLOCATOR = "time_allocator"
    CONSTRAINT_SOLVER = "constraint_solver"
    LOAD_BALANCER = "load_balancer"
    MONTHLY_ENGINE = "monthly_engine"

class Priority(Enum):
    """任务优先级枚举"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4

class MachineType(Enum):
    """机台类型枚举"""
    FEEDER = "feeder"    # 喂丝机
    MAKER = "maker"      # 卷包机

# 算法性能配置
ALGORITHM_CONFIG = {
    "performance": {
        "max_concurrent_tasks": 10,
        "timeout_seconds": 300,  # 5分钟超时
        "retry_attempts": 3,
        "batch_size": 100
    },
    "optimization": {
        "target_efficiency": 0.85,    # 目标效率85%
        "max_overtime_hours": 2.0,    # 最大加班2小时
        "min_setup_time": 0.5,        # 最小换产时间30分钟
        "capacity_buffer": 0.1         # 容量缓冲10%
    },
    "constraints": {
        "max_continuous_hours": 16,   # 最大连续工作16小时
        "min_break_time": 1.0,        # 最小休息时间1小时
        "max_daily_orders": 50,       # 每日最大工单数
        "min_batch_size": 10          # 最小批次大小
    }
}

# 班次配置
SHIFT_CONFIG = {
    "day_shift": {
        "name": "白班",
        "start_time": "08:00",
        "end_time": "16:00",
        "capacity_factor": 1.0,
        "break_periods": [("12:00", "13:00")]
    },
    "night_shift": {
        "name": "夜班", 
        "start_time": "20:00",
        "end_time": "04:00",  # 次日
        "capacity_factor": 0.95,
        "break_periods": [("00:00", "00:30")]
    }
}

# =============================================================================
# 数据类定义
# =============================================================================

@dataclass
class MonthlyPlanItem:
    """月计划项数据类"""
    plan_id: int
    batch_id: str
    work_order_nr: str
    article_nr: str
    article_name: str
    target_quantity: float
    planned_boxes: int
    feeder_codes: List[str]
    maker_codes: List[str] 
    planned_start: Optional[datetime]
    planned_end: Optional[datetime]
    priority: Priority = Priority.MEDIUM
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "plan_id": self.plan_id,
            "batch_id": self.batch_id,
            "work_order_nr": self.work_order_nr,
            "article_nr": self.article_nr,
            "article_name": self.article_name,
            "target_quantity": self.target_quantity,
            "planned_boxes": self.planned_boxes,
            "feeder_codes": self.feeder_codes,
            "maker_codes": self.maker_codes,
            "planned_start": self.planned_start.isoformat() if self.planned_start else None,
            "planned_end": self.planned_end.isoformat() if self.planned_end else None,
            "priority": self.priority.value
        }

@dataclass 
class MachineInfo:
    """机台信息数据类"""
    machine_code: str
    machine_type: MachineType
    capacity_per_hour: float
    efficiency_factor: float
    maintenance_windows: List[Tuple[datetime, datetime]]
    is_available: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "machine_code": self.machine_code,
            "machine_type": self.machine_type.value,
            "capacity_per_hour": self.capacity_per_hour,
            "efficiency_factor": self.efficiency_factor,
            "maintenance_windows": [
                (start.isoformat(), end.isoformat()) 
                for start, end in self.maintenance_windows
            ],
            "is_available": self.is_available
        }

@dataclass
class ScheduleResult:
    """排产结果数据类"""
    schedule_id: str
    plan_id: int
    assigned_feeder: str
    assigned_maker: str
    scheduled_start: datetime
    scheduled_end: datetime
    allocated_quantity: float
    estimated_duration: float
    priority_score: float
    constraints_satisfied: bool
    notes: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "schedule_id": self.schedule_id,
            "plan_id": self.plan_id,
            "assigned_feeder": self.assigned_feeder,
            "assigned_maker": self.assigned_maker, 
            "scheduled_start": self.scheduled_start.isoformat(),
            "scheduled_end": self.scheduled_end.isoformat(),
            "allocated_quantity": self.allocated_quantity,
            "estimated_duration": self.estimated_duration,
            "priority_score": self.priority_score,
            "constraints_satisfied": self.constraints_satisfied,
            "notes": self.notes
        }

# =============================================================================
# 基础算法类
# =============================================================================

class BaseAlgorithm(ABC):
    """算法基类 - 所有算法模块的公共接口"""
    
    def __init__(self, algorithm_type: AlgorithmType, config: Optional[Dict] = None):
        """
        初始化算法
        
        Args:
            algorithm_type: 算法类型
            config: 算法配置
        """
        self.algorithm_type = algorithm_type
        self.config = config or ALGORITHM_CONFIG
        self.logger = self._setup_logger()
        self.version = "1.0.0"
        
    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger(f"aps.monthly.{self.algorithm_type.value}")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
        
    @abstractmethod
    async def execute(self, input_data: Any, **kwargs) -> Any:
        """
        执行算法
        
        Args:
            input_data: 输入数据
            **kwargs: 额外参数
            
        Returns:
            算法执行结果
        """
        pass
        
    @abstractmethod
    def validate_input(self, input_data: Any) -> bool:
        """
        验证输入数据
        
        Args:
            input_data: 输入数据
            
        Returns:
            是否有效
        """
        pass
        
    def get_info(self) -> Dict[str, Any]:
        """获取算法信息"""
        return {
            "algorithm_type": self.algorithm_type.value,
            "version": self.version,
            "config": self.config,
            "description": self.__doc__ or "无描述"
        }
        
    def export_result(self, result: Any, format_type: str = "json") -> str:
        """
        导出结果
        
        Args:
            result: 结果数据
            format_type: 导出格式（json/csv/xml）
            
        Returns:
            格式化的结果字符串
        """
        if format_type.lower() == "json":
            return json.dumps(result, ensure_ascii=False, indent=2, default=str)
        elif format_type.lower() == "csv":
            # 简化的CSV导出，实际项目中可使用pandas
            if isinstance(result, list) and result:
                if hasattr(result[0], 'to_dict'):
                    headers = result[0].to_dict().keys()
                    lines = [",".join(headers)]
                    for item in result:
                        values = [str(v) for v in item.to_dict().values()]
                        lines.append(",".join(values))
                    return "\n".join(lines)
            return str(result)
        else:
            return str(result)

# =============================================================================
# 工具函数
# =============================================================================

def calculate_working_hours(start_time: datetime, end_time: datetime, 
                          shift_config: Dict = None) -> float:
    """
    计算工作时间（排除休息时间）
    
    Args:
        start_time: 开始时间
        end_time: 结束时间
        shift_config: 班次配置
        
    Returns:
        实际工作小时数
    """
    if start_time >= end_time:
        return 0.0
        
    total_hours = (end_time - start_time).total_seconds() / 3600
    
    # 如果有班次配置，扣除休息时间
    if shift_config and "break_periods" in shift_config:
        break_hours = 0
        for break_start, break_end in shift_config["break_periods"]:
            # 简化计算，假设休息时间在工作时间范围内
            break_hours += 1  # 假设每个休息时间段1小时
        total_hours -= break_hours
        
    return max(0.0, total_hours)

def generate_schedule_id(plan_id: int, timestamp: datetime = None) -> str:
    """
    生成排产ID
    
    Args:
        plan_id: 计划ID
        timestamp: 时间戳
        
    Returns:
        排产ID字符串
    """
    if timestamp is None:
        timestamp = datetime.now()
    return f"MONTHLY_SCH_{plan_id}_{timestamp.strftime('%Y%m%d%H%M%S')}"

def validate_time_window(start_time: datetime, end_time: datetime) -> bool:
    """
    验证时间窗口的有效性
    
    Args:
        start_time: 开始时间
        end_time: 结束时间
        
    Returns:
        是否有效
    """
    if not isinstance(start_time, datetime) or not isinstance(end_time, datetime):
        return False
        
    if start_time >= end_time:
        return False
        
    # 检查时间范围是否合理（不超过30天）
    max_duration = timedelta(days=30)
    if (end_time - start_time) > max_duration:
        return False
        
    return True

def calculate_priority_score(plan_item: MonthlyPlanItem, 
                           current_time: datetime = None) -> float:
    """
    计算任务优先级分数
    
    Args:
        plan_item: 月计划项
        current_time: 当前时间
        
    Returns:
        优先级分数（0-100）
    """
    if current_time is None:
        current_time = datetime.now()
        
    base_score = plan_item.priority.value * 20  # 基础分数
    
    # 紧急程度调整
    if plan_item.planned_start and plan_item.planned_start <= current_time:
        base_score += 30  # 已到达计划时间
    elif plan_item.planned_start:
        days_until_start = (plan_item.planned_start - current_time).days
        if days_until_start <= 1:
            base_score += 20  # 即将开始
        elif days_until_start <= 3:
            base_score += 10  # 较快开始
            
    # 数量规模调整
    if plan_item.target_quantity > 1000:
        base_score += 10  # 大订单优先
        
    return min(100.0, max(0.0, base_score))

# =============================================================================
# 异常类定义
# =============================================================================

class MonthlySchedulingError(Exception):
    """月度排产基础异常类"""
    pass

class InvalidInputError(MonthlySchedulingError):
    """无效输入异常"""
    pass

class ConstraintViolationError(MonthlySchedulingError):
    """约束违反异常"""
    pass

class ResourceConflictError(MonthlySchedulingError):
    """资源冲突异常"""
    pass

class AlgorithmTimeoutError(MonthlySchedulingError):
    """算法超时异常"""
    pass