"""
APS智慧排产系统 - 算法引擎模块

实现完整的烟草排产算法引擎，包括：
- 数据预处理算法
- 规则合并算法  
- 规则拆分算法
- 时间校正算法
- 并行切分算法
- 工单生成算法

所有算法遵循技术设计文档中定义的业务规则和性能要求。
"""

from .base import (
    AlgorithmBase,
    AlgorithmResult,
    ProcessingStage,
    ProcessingStatus
)

# 已实现的算法模块
from .data_preprocessing import DataPreprocessor
from .merge_algorithm import MergeAlgorithm
from .split_algorithm import SplitAlgorithm
from .time_correction import TimeCorrection
from .parallel_processing import ParallelProcessing
from .work_order_generation import WorkOrderGeneration

# 未来将实现的算法模块
# from .gantt_data_converter import GanttDataConverter
# from .performance_monitor import PerformanceMonitor

__version__ = "1.0.0"
__author__ = "APS Team"

# 导出主要算法接口
__all__ = [
    "AlgorithmBase",
    "AlgorithmResult", 
    "ProcessingStage",
    "ProcessingStatus",
    "DataPreprocessor",
    "MergeAlgorithm",
    "SplitAlgorithm",
    "TimeCorrection",
    "ParallelProcessing",
    "WorkOrderGeneration"
]