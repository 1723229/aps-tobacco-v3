#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
月度容量计算器命令行工具

提供月度生产容量计算、瓶颈分析和优化建议的命令行接口。
支持多种计算方法和输出格式。

使用示例：
    python capacity_cli.py --year 2024 --month 1 --method practical --output console
    python capacity_cli.py --machines JBJ001 JBJ002 --benchmark
    python capacity_cli.py --help
"""

import sys
import os
import asyncio
import argparse
import json
import time
from pathlib import Path

# 添加项目路径到sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from app.algorithms.monthly_scheduling.monthly_capacity_calculator import (
        MonthlyCapacityCalculator,
        CapacityCalculationMethod,
        main as calculator_main,
        run_benchmark,
        print_report_summary
    )
except ImportError as e:
    print(f"❌ 导入模块失败: {e}")
    print("请确保在正确的项目目录中运行此脚本")
    sys.exit(1)


def print_welcome():
    """打印欢迎信息"""
    print("="*60)
    print("🏭 APS烟草生产系统 - 月度容量计算器")
    print("="*60)
    print("功能特性:")
    print("  ✅ 多种容量计算方法 (理论/实际/优化)")
    print("  ✅ 智能瓶颈识别与分析")
    print("  ✅ 资源配置优化建议")
    print("  ✅ 容量预测与趋势分析")
    print("  ✅ 性能基准测试")
    print("  ✅ 多格式输出 (控制台/JSON/文件)")
    print("="*60)


def print_usage_examples():
    """打印使用示例"""
    print("\n📚 使用示例:")
    print("  基础计算:")
    print("    python capacity_cli.py --year 2024 --month 1")
    print("")
    print("  指定机台和产品:")
    print("    python capacity_cli.py --machines JBJ001 JBJ002 --products 香烟")
    print("")
    print("  理论容量计算:")
    print("    python capacity_cli.py --method theoretical --output json")
    print("")
    print("  性能基准测试:")
    print("    python capacity_cli.py --benchmark")
    print("")
    print("  保存报告到文件:")
    print("    python capacity_cli.py --output file --year 2024 --month 12")


def create_parser():
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description="APS烟草生产系统 - 月度容量计算器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  %(prog)s --year 2024 --month 1                    # 基础计算
  %(prog)s --machines JBJ001 JBJ002 --output json   # 指定机台
  %(prog)s --benchmark                               # 性能测试
  %(prog)s --help                                    # 查看帮助
        """
    )
    
    # 基础参数
    parser.add_argument(
        '--year', 
        type=int, 
        default=2024,
        help='计算年份 (默认: 2024)'
    )
    parser.add_argument(
        '--month', 
        type=int, 
        default=1,
        help='计算月份 (默认: 1)'
    )
    
    # 过滤参数
    parser.add_argument(
        '--machines', 
        nargs='*', 
        help='机台ID列表 (例: JBJ001 JBJ002)'
    )
    parser.add_argument(
        '--products', 
        nargs='*', 
        help='产品类型列表 (例: 香烟 烟丝)'
    )
    
    # 计算方法
    parser.add_argument(
        '--method', 
        choices=['theoretical', 'practical', 'optimized', 'historical'], 
        default='practical',
        help='容量计算方法 (默认: practical)'
    )
    
    # 输出控制
    parser.add_argument(
        '--output', 
        choices=['console', 'json', 'file'], 
        default='console',
        help='输出格式 (默认: console)'
    )
    parser.add_argument(
        '--no-forecast', 
        action='store_true',
        help='不包含容量预测分析'
    )
    parser.add_argument(
        '--verbose', '-v', 
        action='store_true',
        help='详细输出模式'
    )
    
    # 测试和调试
    parser.add_argument(
        '--benchmark', 
        action='store_true',
        help='运行性能基准测试'
    )
    parser.add_argument(
        '--test', 
        action='store_true',
        help='运行快速功能测试'
    )
    parser.add_argument(
        '--examples', 
        action='store_true',
        help='显示使用示例'
    )
    
    return parser


async def run_quick_test():
    """运行快速功能测试"""
    print("🧪 运行快速功能测试...")
    
    try:
        calculator = MonthlyCapacityCalculator()
        print("✅ 计算器初始化成功")
        
        # 测试缓存键生成
        cache_key = calculator._generate_cache_key(
            2024, 1, ['JBJ001'], ['香烟'], CapacityCalculationMethod.PRACTICAL
        )
        print(f"✅ 缓存键生成: {cache_key}")
        
        # 测试工作日历
        calendar = await calculator._get_work_calendar(2024, 1)
        print(f"✅ 工作日历获取: {calendar['working_days']} 工作日")
        
        # 测试机台配置
        machines = await calculator._get_machine_configs(['JBJ001'])
        print(f"✅ 机台配置获取: {len(machines)} 台机器")
        
        # 测试月度计划
        plans = await calculator._get_monthly_plans(2024, 1, ['香烟'])
        print(f"✅ 月度计划获取: {len(plans)} 个计划")
        
        # 测试季节性因子
        factor = calculator._calculate_seasonality_factor(1)
        print(f"✅ 季节性因子计算: {factor}")
        
        print("🎉 所有快速测试通过!")
        
    except Exception as e:
        print(f"❌ 快速测试失败: {e}")
        return False
    
    return True


async def main():
    """主函数"""
    parser = create_parser()
    args = parser.parse_args()
    
    # 显示欢迎信息
    if not args.benchmark and not args.test and not args.examples:
        print_welcome()
    
    # 显示使用示例
    if args.examples:
        print_usage_examples()
        return
    
    # 运行快速测试
    if args.test:
        success = await run_quick_test()
        sys.exit(0 if success else 1)
    
    # 运行基准测试
    if args.benchmark:
        await run_benchmark()
        return
    
    # 参数验证
    if args.month < 1 or args.month > 12:
        print("❌ 错误: 月份必须在1-12之间")
        sys.exit(1)
    
    if args.year < 2020 or args.year > 2030:
        print("⚠️  警告: 年份超出建议范围 (2020-2030)")
    
    try:
        # 创建计算器实例
        calculator = MonthlyCapacityCalculator()
        
        if args.verbose:
            print(f"📊 开始计算 {args.year} 年 {args.month} 月的容量...")
            print(f"   计算方法: {args.method}")
            print(f"   机台过滤: {args.machines or '全部'}")
            print(f"   产品过滤: {args.products or '全部'}")
            print(f"   包含预测: {'否' if args.no_forecast else '是'}")
        
        # 执行容量计算
        start_time = time.time()
        
        calculation_method = CapacityCalculationMethod(args.method)
        report = await calculator.calculate_monthly_capacity(
            year=args.year,
            month=args.month,
            machine_ids=args.machines,
            product_types=args.products,
            calculation_method=calculation_method,
            include_forecast=not args.no_forecast
        )
        
        calculation_time = time.time() - start_time
        
        if args.verbose:
            print(f"✅ 计算完成，耗时: {calculation_time:.2f}秒")
        
        # 输出结果
        if args.output == 'console':
            print_report_summary(report)
            
            if args.verbose:
                # 显示性能指标
                metrics = calculator.get_performance_metrics()
                print(f"\n📈 性能指标:")
                print(f"   计算次数: {metrics['calculations_performed']}")
                print(f"   平均耗时: {metrics['average_calculation_time']:.3f}秒")
                print(f"   缓存命中率: {metrics['cache_hit_rate']:.1%}")
        
        elif args.output == 'json':
            # JSON输出
            from dataclasses import asdict
            json_data = asdict(report)
            print(json.dumps(json_data, ensure_ascii=False, indent=2, default=str))
        
        elif args.output == 'file':
            # 文件输出
            from dataclasses import asdict
            filename = f"capacity_report_{args.year}_{args.month:02d}_{int(time.time())}.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json_data = asdict(report)
                json.dump(json_data, f, ensure_ascii=False, indent=2, default=str)
            
            print(f"📄 报告已保存到: {filename}")
            print(f"   文件大小: {os.path.getsize(filename)} 字节")
            
            if args.verbose:
                print(f"   报告ID: {report.report_id}")
                print(f"   机台数量: {len(report.machine_capacities)}")
                print(f"   瓶颈数量: {len(report.bottleneck_analyses)}")
                print(f"   优化建议: {len(report.optimization_recommendations)}")
    
    except KeyboardInterrupt:
        print("\n⚠️  用户中断操作")
        sys.exit(1)
    
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # 检查Python版本
    if sys.version_info < (3, 8):
        print("❌ 错误: 需要Python 3.8或更高版本")
        sys.exit(1)
    
    # 运行主程序
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 再见!")
        sys.exit(0)