"""
APS智慧排产系统 - 月度排产算法模块包

本模块实现了专门针对月计划Excel直接排产的算法套件，包含7个核心算法模块：

1. calendar_service.py - 工作日历服务模块
2. machine_selector.py - 机台选择算法  
3. capacity_calculator.py - 容量计算模块
4. time_allocator.py - 时间分配算法
5. constraint_solver.py - 约束求解模块
6. load_balancer.py - 负载均衡算法
7. monthly_engine.py - 月度引擎编排

所有模块遵循以下设计原则：
- 库优先架构：每个模块都是独立的库，可单独使用
- CLI支持：支持 --help, --version, --format, --json 标志
- 异步设计：使用 async/await 支持高并发处理
- 类型安全：使用 Python 类型提示
- 错误处理：完整的异常处理和日志记录
- 测试覆盖：每个模块都有对应的单元测试

版本: 1.0.0
作者: APS开发团队
许可: MIT
"""

__version__ = "1.0.0"
__author__ = "APS Development Team"

# 导入核心算法模块
from .monthly_calendar_service import MonthlyCalendarService

# 尝试导入其他模块，如果不存在则跳过
try:
    from .monthly_machine_selector import MonthlyMachineSelector
except ImportError:
    MonthlyMachineSelector = None

try:
    from .monthly_capacity_calculator import MonthlyCapacityCalculator
except ImportError:
    MonthlyCapacityCalculator = None

try:
    from .capacity_calculator import CapacityCalculatorEngine
except ImportError:
    CapacityCalculatorEngine = None

try:
    from .time_allocator import TimeAllocationAlgorithm
except ImportError:
    TimeAllocationAlgorithm = None

try:
    from .constraint_solver import ConstraintSolverEngine
except ImportError:
    ConstraintSolverEngine = None

try:
    from .monthly_constraint_solver import MonthlyConstraintSolver
except ImportError:
    MonthlyConstraintSolver = None

try:
    from .load_balancer import LoadBalancerAlgorithm
except ImportError:
    LoadBalancerAlgorithm = None

try:
    from .monthly_engine import MonthlySchedulingEngine
except ImportError:
    MonthlySchedulingEngine = None

try:
    from .monthly_resource_optimizer import MonthlyResourceOptimizer
except ImportError:
    MonthlyResourceOptimizer = None

try:
    from .monthly_timeline_generator import MonthlyTimelineGenerator
except ImportError:
    MonthlyTimelineGenerator = None

try:
    from .monthly_result_formatter import MonthlyResultFormatter
except ImportError:
    MonthlyResultFormatter = None

# 导出主要类
__all__ = [
    "MonthlyCalendarService",
    "MonthlyCapacityCalculator", 
    "MonthlyConstraintSolver",
    "MonthlyResourceOptimizer",
    "MonthlyTimelineGenerator",
    "MonthlyResultFormatter"
]

# 添加存在的类到导出列表
if MonthlyMachineSelector:
    __all__.append("MonthlyMachineSelector")
if CapacityCalculatorEngine:
    __all__.append("CapacityCalculatorEngine")
if TimeAllocationAlgorithm:
    __all__.append("TimeAllocationAlgorithm")
if MonthlyConstraintSolver:
    __all__.append("MonthlyConstraintSolver")
if LoadBalancerAlgorithm:
    __all__.append("LoadBalancerAlgorithm")
if MonthlySchedulingEngine:
    __all__.append("MonthlySchedulingEngine")
if MonthlyTimelineGenerator:
    __all__.append("MonthlyTimelineGenerator")
if MonthlyResultFormatter:
    __all__.append("MonthlyResultFormatter")

# 算法模块信息
ALGORITHM_MODULES = {
    "calendar_service": {
        "name": "工作日历服务",
        "description": "提供工作日历查询和约束检查功能",
        "version": "1.0.0",
        "dependencies": ["aiomysql", "datetime"]
    },
    "machine_selector": {
        "name": "月度机台选择算法", 
        "description": "基于月度容量选择最优机台组合，支持卷包机和喂丝机联合优化",
        "version": "1.0.0",
        "dependencies": ["sqlalchemy", "asyncio", "decimal"]
    },
    "capacity_calculator": {
        "name": "容量计算引擎",
        "description": "计算月度生产容量和机台利用率",
        "version": "1.0.0", 
        "dependencies": ["pandas", "numpy"]
    },
    "monthly_capacity_calculator": {
        "name": "月度容量计算器",
        "description": "提供日产能、月产能计算和完工时间预估，支持多产品多机台复合容量分析",
        "version": "1.0.0",
        "dependencies": ["sqlalchemy", "asyncio", "decimal", "datetime"]
    },
    "time_allocator": {
        "name": "时间分配算法",
        "description": "优化时间窗口分配和排产时序",
        "version": "1.0.0",
        "dependencies": ["datetime", "heapq"]
    },
    "constraint_solver": {
        "name": "月度约束求解引擎",
        "description": "处理复杂多约束优化问题，支持软硬约束、线性规划和启发式算法混合求解",
        "version": "1.0.0",
        "dependencies": ["ortools", "numpy", "scipy"]
    },
    "monthly_constraint_solver": {
        "name": "月度约束求解算法",
        "description": "专门针对月度排产的复杂约束求解，支持时间、容量、机台、工作日历等多种约束类型",
        "version": "1.0.0",
        "dependencies": ["sqlalchemy", "asyncio", "ortools", "numpy", "scipy"]
    },
    "load_balancer": {
        "name": "负载均衡算法",
        "description": "平衡机台负载和生产效率",
        "version": "1.0.0", 
        "dependencies": ["numpy", "statistics"]
    },
    "monthly_engine": {
        "name": "月度排产引擎",
        "description": "编排和协调所有算法模块的执行",
        "version": "1.0.0",
        "dependencies": ["asyncio", "concurrent.futures"]
    },
    "monthly_timeline_generator": {
        "name": "月度时间线生成器",
        "description": "生成精确的月度生产时间线，支持甘特图数据和冲突解决",
        "version": "1.0.0",
        "dependencies": ["asyncio", "heapq", "datetime", "decimal"]
    },
    "monthly_result_formatter": {
        "name": "月度结果格式化器",
        "description": "将排产结果转换为各种业务需要的格式，支持甘特图、工单、报告、Excel/PDF导出",
        "version": "1.0.0",
        "dependencies": ["asyncio", "json", "csv", "decimal", "collections"]
    }
}

# 算法执行管道配置
ALGORITHM_PIPELINE = [
    "calendar_service",           # 1. 工作日历初始化
    "monthly_capacity_calculator", # 2. 月度容量计算 (T023)
    "capacity_calculator",        # 3. 传统容量计算
    "machine_selector",           # 4. 机台选择
    "time_allocator",            # 5. 时间分配
    "constraint_solver",         # 6. 约束求解
    "load_balancer",             # 7. 负载均衡
    "monthly_timeline_generator", # 8. 时间线生成 (T025)
    "monthly_result_formatter",   # 9. 结果格式化 (T027)
    "monthly_engine"             # 10. 结果汇总
]

def get_algorithm_info(module_name: str = None) -> dict:
    """
    获取算法模块信息
    
    Args:
        module_name: 模块名称，如果为None则返回所有模块信息
        
    Returns:
        算法模块信息字典
    """
    if module_name:
        return ALGORITHM_MODULES.get(module_name, {})
    return ALGORITHM_MODULES

def get_pipeline_order() -> list:
    """
    获取算法执行管道顺序
    
    Returns:
        算法执行顺序列表
    """
    return ALGORITHM_PIPELINE.copy()

# 版本兼容性检查
def check_compatibility() -> bool:
    """
    检查模块间的版本兼容性
    
    Returns:
        是否兼容
    """
    required_python_version = (3, 8)
    import sys
    
    if sys.version_info < required_python_version:
        raise RuntimeError(f"需要Python {required_python_version[0]}.{required_python_version[1]}或更高版本")
    
    return True

# 初始化检查
check_compatibility()