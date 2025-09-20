"""
APS智慧排产系统 - 月度排产算法模块

本模块实现完整的月度排产算法，包含：
1. 机台关系正确理解：1喂丝机→多卷包机
2. 产能计算：只计算卷包机产能，喂丝机不参与
3. 时间分配：严格保证卷包机时间不重叠
4. 全覆盖：确保所有产品都被安排进排产
5. 结果保存：基于卷包机分配查询对应喂丝机保存结果

数据表使用：
- 输入表：aps_monthly_plan, aps_machine, aps_machine_speed, aps_machine_relation,
          aps_shift_config, aps_monthly_work_calendar, aps_maintenance_plan
- 输出表：aps_monthly_schedule_result, aps_monthly_scheduling_task

核心组件：
- MonthlySchedulingEngine: 主算法引擎，协调所有组件
- DatabaseLoader: 数据库访问层，负责9个表的数据加载
- TimeWindowCalculator: 时间窗口计算器，基于工作日历和班次
- CapacityCalculator: 产能计算器，只计算卷包机产能
- SchedulingOptimizer: 调度优化器，实现时间不重叠分配
- ConstraintValidator: 约束验证器，确保结果正确性
- ResultProcessor: 结果处理器，处理机台映射和数据保存

技术特性：
- 完整的约束求解和验证
- 零时间重叠的严格保证
- 100%产品覆盖验证
- 正确的机台关系映射
- 完善的错误处理机制
- 高性能的数据处理
"""

from .monthly_scheduling_engine import MonthlySchedulingEngine

__all__ = ["MonthlySchedulingEngine"]

__version__ = "v2.0_complete"
__author__ = "APS Team"
__description__ = "月度排产算法完整实现 - 正确理解机台关系，只计算卷包机产能，严格时间不重叠"