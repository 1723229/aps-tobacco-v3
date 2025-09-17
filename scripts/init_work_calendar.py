#!/usr/bin/env python3
"""
APS智慧排产系统 - 月计划工作日历初始化Python脚本

目的: 为2024-2026年生成完整的工作日历数据
功能:
1. 生成所有日期的基础记录（工作日、周末、节假日）
2. 配置标准班次（两班制：白班08:00-16:00，夜班20:00-04:00）
3. 设置产能系数（节假日前后调整、维护日等）
4. 验证和统计工作日历数据

依赖: MySQL数据库连接，aps_monthly_work_calendar表已创建
"""

import sys
import json
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
import calendar
import asyncio

# 尝试导入数据库依赖
try:
    import aiomysql
    from aiomysql import Pool
except ImportError:
    print("❌ 错误: 缺少aiomysql依赖")
    print("请安装: pip install aiomysql")
    sys.exit(1)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('monthly_calendar_init.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class MonthlyCalendarInitializer:
    """月度工作日历初始化器"""
    
    def __init__(self, db_config: Dict[str, str]):
        """
        初始化日历生成器
        
        Args:
            db_config: 数据库连接配置
        """
        self.db_config = db_config
        self.pool: Optional[Pool] = None
        
        # 标准班次配置（两班制）
        self.standard_shifts = [
            {
                "shift_name": "白班",
                "start": "08:00",
                "end": "16:00", 
                "capacity_factor": 1.0,
                "break_time": ["12:00", "13:00"]  # 午休时间
            },
            {
                "shift_name": "夜班",
                "start": "20:00", 
                "end": "04:00",  # 次日凌晨4点
                "capacity_factor": 0.95,  # 夜班效率稍低
                "break_time": ["00:00", "00:30"]  # 夜宵时间
            }
        ]
        
        # 已知节假日（从SQL脚本中提取，用于识别已存在的节假日）
        self.known_holidays_2024 = {
            '2024-01-01': '元旦',
            '2024-02-10': '春节', '2024-02-11': '春节', '2024-02-12': '春节', 
            '2024-02-13': '春节', '2024-02-14': '春节', '2024-02-15': '春节',
            '2024-02-16': '春节', '2024-02-17': '春节',
            '2024-04-04': '清明节', '2024-04-05': '清明节', '2024-04-06': '清明节',
            '2024-05-01': '劳动节', '2024-05-02': '劳动节', '2024-05-03': '劳动节',
            '2024-05-04': '劳动节', '2024-05-05': '劳动节',
            '2024-06-10': '端午节',
            '2024-09-17': '中秋节',
            '2024-10-01': '国庆节', '2024-10-02': '国庆节', '2024-10-03': '国庆节',
            '2024-10-04': '国庆节', '2024-10-05': '国庆节', '2024-10-06': '国庆节',
            '2024-10-07': '国庆节'
        }
        
    async def connect_db(self) -> None:
        """创建数据库连接池"""
        try:
            self.pool = await aiomysql.create_pool(
                host=self.db_config['host'],
                port=self.db_config['port'], 
                user=self.db_config['user'],
                password=self.db_config['password'],
                db=self.db_config['database'],
                charset='utf8mb4',
                autocommit=True,
                minsize=1,
                maxsize=5
            )
            logger.info("✅ 数据库连接池创建成功")
        except Exception as e:
            logger.error(f"❌ 数据库连接失败: {e}")
            raise
            
    async def close_db(self) -> None:
        """关闭数据库连接池"""
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            logger.info("✅ 数据库连接池已关闭")
            
    def get_week_day(self, date_obj: date) -> int:
        """获取星期几（1=星期一，7=星期日）"""
        # Python的weekday(): 0=星期一，6=星期日
        # 转换为: 1=星期一，7=星期日 
        return date_obj.weekday() + 1
        
    def is_weekend(self, date_obj: date) -> bool:
        """判断是否为周末"""
        week_day = self.get_week_day(date_obj)
        return week_day in [6, 7]  # 6=星期六，7=星期日
        
    def get_day_type(self, date_obj: date) -> Tuple[str, bool, str]:
        """
        获取日期类型
        
        Returns:
            Tuple[日期类型, 是否工作日, 节假日名称]
        """
        date_str = date_obj.strftime('%Y-%m-%d')
        
        # 检查是否为已知节假日
        if date_str in self.known_holidays_2024:
            return 'HOLIDAY', False, self.known_holidays_2024[date_str]
            
        # 检查是否为周末
        if self.is_weekend(date_obj):
            return 'WEEKEND', False, None
            
        # 普通工作日
        return 'WORKDAY', True, None
        
    def calculate_capacity_factor(self, date_obj: date, day_type: str) -> float:
        """
        计算产能系数
        
        Args:
            date_obj: 日期对象
            day_type: 日期类型
            
        Returns:
            产能系数（0.0-2.0）
        """
        # 节假日和周末产能为0
        if day_type in ['HOLIDAY', 'WEEKEND']:
            return 0.0
            
        # 节假日前一天产能稍低（员工状态）
        next_day = date_obj + timedelta(days=1)
        next_day_type, _, _ = self.get_day_type(next_day)
        if next_day_type == 'HOLIDAY':
            return 0.9
            
        # 节假日后第一个工作日产能稍低（恢复状态）
        prev_day = date_obj - timedelta(days=1)
        prev_day_type, _, _ = self.get_day_type(prev_day)
        if prev_day_type == 'HOLIDAY':
            return 0.85
            
        # 月初产能稍高（新月开始）
        if date_obj.day <= 3:
            return 1.1
            
        # 月末产能稍低（完成月度任务后）
        if date_obj.day >= 28:
            return 0.95
            
        # 普通工作日标准产能
        return 1.0
        
    def get_total_hours(self, day_type: str, capacity_factor: float) -> float:
        """计算当日总工作小时数"""
        if day_type in ['HOLIDAY', 'WEEKEND']:
            return 0.0
        elif day_type == 'MAINTENANCE':
            return 6.0  # 维护日减少工作时间
        else:
            # 标准两班制：16小时
            base_hours = 16.0
            return base_hours * min(capacity_factor, 1.0)  # 容量系数不会增加总工时，只影响效率
            
    async def generate_calendar_data(self, start_year: int, end_year: int) -> List[Dict]:
        """
        生成指定年份范围的日历数据
        
        Args:
            start_year: 开始年份
            end_year: 结束年份
            
        Returns:
            日历记录列表
        """
        records = []
        total_days = 0
        working_days = 0
        
        logger.info(f"🗓️ 开始生成 {start_year}-{end_year} 年工作日历数据...")
        
        for year in range(start_year, end_year + 1):
            year_working_days = 0
            logger.info(f"📅 处理 {year} 年...")
            
            # 遍历一年中的每一天
            current_date = date(year, 1, 1)
            end_date = date(year, 12, 31)
            
            while current_date <= end_date:
                # 获取日期基础信息
                week_day = self.get_week_day(current_date)
                day_type, is_working, holiday_name = self.get_day_type(current_date)
                capacity_factor = self.calculate_capacity_factor(current_date, day_type)
                total_hours = self.get_total_hours(day_type, capacity_factor)
                
                # 创建记录
                record = {
                    'calendar_date': current_date,
                    'calendar_year': current_date.year,
                    'calendar_month': current_date.month,
                    'calendar_day': current_date.day,
                    'calendar_week_day': week_day,
                    'monthly_day_type': day_type,
                    'monthly_is_working': 1 if is_working else 0,
                    'monthly_shifts': json.dumps(self.standard_shifts, ensure_ascii=False) if is_working else None,
                    'monthly_total_hours': total_hours,
                    'monthly_capacity_factor': capacity_factor,
                    'monthly_holiday_name': holiday_name,
                    'monthly_maintenance_type': None,
                    'monthly_notes': self._generate_notes(current_date, day_type, capacity_factor)
                }
                
                records.append(record)
                total_days += 1
                if is_working:
                    working_days += 1
                    year_working_days += 1
                    
                current_date += timedelta(days=1)
                
            logger.info(f"✅ {year} 年完成: 工作日 {year_working_days} 天")
            
        logger.info(f"🎉 日历数据生成完成: 总计 {total_days} 天，工作日 {working_days} 天")
        return records
        
    def _generate_notes(self, date_obj: date, day_type: str, capacity_factor: float) -> Optional[str]:
        """生成日期备注信息"""
        notes = []
        
        if day_type == 'HOLIDAY':
            notes.append('法定节假日')
        elif day_type == 'WEEKEND':
            notes.append('周末休息')
        elif day_type == 'WORKDAY':
            if capacity_factor > 1.0:
                notes.append(f'高效工作日(系数{capacity_factor})')
            elif capacity_factor < 1.0:
                notes.append(f'效率调整日(系数{capacity_factor})')
                
        # 特殊日期标记
        if date_obj.day == 1:
            notes.append('月初')
        elif date_obj.day >= 28:
            notes.append('月末') 
            
        return '; '.join(notes) if notes else None
        
    async def batch_insert_records(self, records: List[Dict], batch_size: int = 100) -> None:
        """
        批量插入日历记录
        
        Args:
            records: 日历记录列表
            batch_size: 批次大小
        """
        if not self.pool:
            raise Exception("数据库连接未建立")
            
        total_records = len(records)
        inserted_count = 0
        skipped_count = 0
        
        logger.info(f"📊 开始批量插入 {total_records} 条日历记录...")
        
        # SQL插入语句
        insert_sql = """
        INSERT IGNORE INTO aps_monthly_work_calendar (
            calendar_date, calendar_year, calendar_month, calendar_day, calendar_week_day,
            monthly_day_type, monthly_is_working, monthly_shifts, monthly_total_hours,
            monthly_capacity_factor, monthly_holiday_name, monthly_maintenance_type, monthly_notes
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        """
        
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # 分批插入
                for i in range(0, total_records, batch_size):
                    batch = records[i:i + batch_size]
                    batch_data = []
                    
                    for record in batch:
                        batch_data.append((
                            record['calendar_date'],
                            record['calendar_year'], 
                            record['calendar_month'],
                            record['calendar_day'],
                            record['calendar_week_day'],
                            record['monthly_day_type'],
                            record['monthly_is_working'],
                            record['monthly_shifts'],
                            record['monthly_total_hours'],
                            record['monthly_capacity_factor'],
                            record['monthly_holiday_name'],
                            record['monthly_maintenance_type'],
                            record['monthly_notes']
                        ))
                    
                    try:
                        affected_rows = await cursor.executemany(insert_sql, batch_data)
                        inserted_count += affected_rows
                        logger.info(f"✅ 批次 {i//batch_size + 1}: 插入 {affected_rows}/{len(batch)} 条记录")
                    except Exception as e:
                        logger.error(f"❌ 批次 {i//batch_size + 1} 插入失败: {e}")
                        skipped_count += len(batch)
                        
        logger.info(f"🎉 批量插入完成: 成功 {inserted_count} 条，跳过 {skipped_count} 条")
        
    async def generate_statistics(self) -> Dict:
        """生成工作日历统计信息"""
        if not self.pool:
            raise Exception("数据库连接未建立")
            
        stats = {}
        
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # 总体统计
                await cursor.execute("""
                SELECT 
                    COUNT(*) as total_days,
                    SUM(monthly_is_working) as working_days,
                    SUM(CASE WHEN monthly_day_type = 'HOLIDAY' THEN 1 ELSE 0 END) as holiday_days,
                    SUM(CASE WHEN monthly_day_type = 'WEEKEND' THEN 1 ELSE 0 END) as weekend_days,
                    ROUND(AVG(monthly_capacity_factor), 3) as avg_capacity_factor,
                    ROUND(SUM(monthly_total_hours), 1) as total_work_hours
                FROM aps_monthly_work_calendar
                """)
                result = await cursor.fetchone()
                stats['overall'] = {
                    'total_days': result[0],
                    'working_days': result[1], 
                    'holiday_days': result[2],
                    'weekend_days': result[3],
                    'avg_capacity_factor': result[4],
                    'total_work_hours': result[5]
                }
                
                # 按年统计
                await cursor.execute("""
                SELECT 
                    calendar_year,
                    COUNT(*) as total_days,
                    SUM(monthly_is_working) as working_days,
                    ROUND(AVG(monthly_capacity_factor), 3) as avg_capacity_factor
                FROM aps_monthly_work_calendar
                GROUP BY calendar_year
                ORDER BY calendar_year
                """)
                yearly_stats = await cursor.fetchall()
                stats['yearly'] = [
                    {
                        'year': row[0],
                        'total_days': row[1],
                        'working_days': row[2], 
                        'avg_capacity_factor': row[3]
                    }
                    for row in yearly_stats
                ]
                
                # 节假日统计
                await cursor.execute("""
                SELECT monthly_holiday_name, COUNT(*) as days
                FROM aps_monthly_work_calendar
                WHERE monthly_day_type = 'HOLIDAY' AND monthly_holiday_name IS NOT NULL
                GROUP BY monthly_holiday_name
                ORDER BY days DESC
                """)
                holiday_stats = await cursor.fetchall()
                stats['holidays'] = [
                    {'holiday_name': row[0], 'days': row[1]}
                    for row in holiday_stats
                ]
                
        return stats
        
    async def validate_calendar_data(self) -> bool:
        """验证日历数据的完整性和正确性"""
        if not self.pool:
            raise Exception("数据库连接未建立")
            
        logger.info("🔍 开始验证日历数据...")
        is_valid = True
        
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # 检查1：日期唯一性
                await cursor.execute("""
                SELECT calendar_date, COUNT(*) as cnt
                FROM aps_monthly_work_calendar
                GROUP BY calendar_date
                HAVING cnt > 1
                LIMIT 5
                """)
                duplicates = await cursor.fetchall()
                if duplicates:
                    logger.error(f"❌ 发现重复日期: {duplicates}")
                    is_valid = False
                else:
                    logger.info("✅ 日期唯一性检查通过")
                    
                # 检查2：周末工作日标记
                await cursor.execute("""
                SELECT calendar_date, calendar_week_day, monthly_is_working
                FROM aps_monthly_work_calendar
                WHERE calendar_week_day IN (6, 7) AND monthly_is_working = 1
                  AND monthly_day_type != 'MAINTENANCE'
                LIMIT 5
                """)
                weekend_work = await cursor.fetchall()
                if weekend_work:
                    logger.warning(f"⚠️ 发现周末标记为工作日: {weekend_work}")
                    
                # 检查3：节假日工作标记
                await cursor.execute("""
                SELECT calendar_date, monthly_holiday_name, monthly_is_working
                FROM aps_monthly_work_calendar
                WHERE monthly_day_type = 'HOLIDAY' AND monthly_is_working = 1
                LIMIT 5
                """)
                holiday_work = await cursor.fetchall()
                if holiday_work:
                    logger.error(f"❌ 发现节假日标记为工作日: {holiday_work}")
                    is_valid = False
                else:
                    logger.info("✅ 节假日工作日标记检查通过")
                    
                # 检查4：产能系数范围
                await cursor.execute("""
                SELECT calendar_date, monthly_capacity_factor
                FROM aps_monthly_work_calendar
                WHERE monthly_capacity_factor < 0 OR monthly_capacity_factor > 2
                LIMIT 5
                """)
                invalid_factor = await cursor.fetchall()
                if invalid_factor:
                    logger.error(f"❌ 发现无效产能系数: {invalid_factor}")
                    is_valid = False
                else:
                    logger.info("✅ 产能系数范围检查通过")
                    
        logger.info(f"{'✅ 日历数据验证通过' if is_valid else '❌ 日历数据验证失败'}")
        return is_valid


async def main():
    """主函数"""
    logger.info("🚀 开始APS月计划工作日历初始化...")
    
    # 数据库配置（实际使用时从配置文件或环境变量读取）
    db_config = {
        'host': 'localhost',
        'port': 3306,
        'user': 'aps_user', 
        'password': 'aps_password',
        'database': 'aps_tobacco_v3'
    }
    
    # 创建初始化器
    initializer = MonthlyCalendarInitializer(db_config)
    
    try:
        # 连接数据库
        await initializer.connect_db()
        
        # 生成2024-2026年日历数据
        calendar_records = await initializer.generate_calendar_data(2024, 2026)
        
        # 批量插入数据
        await initializer.batch_insert_records(calendar_records)
        
        # 验证数据
        is_valid = await initializer.validate_calendar_data()
        
        if is_valid:
            # 生成统计报告
            stats = await initializer.generate_statistics()
            
            logger.info("📊 工作日历统计报告:")
            logger.info(f"  总计天数: {stats['overall']['total_days']}")
            logger.info(f"  工作日: {stats['overall']['working_days']}")
            logger.info(f"  节假日: {stats['overall']['holiday_days']}")
            logger.info(f"  周末: {stats['overall']['weekend_days']}")
            logger.info(f"  平均产能系数: {stats['overall']['avg_capacity_factor']}")
            logger.info(f"  总工作时数: {stats['overall']['total_work_hours']}")
            
            for year_stat in stats['yearly']:
                logger.info(f"  {year_stat['year']}年: {year_stat['working_days']} 个工作日")
                
            logger.info("🎉 APS月计划工作日历初始化成功完成！")
        else:
            logger.error("❌ 数据验证失败，请检查数据质量")
            
    except Exception as e:
        logger.error(f"❌ 初始化过程出现错误: {e}")
        raise
    finally:
        # 关闭数据库连接
        await initializer.close_db()


if __name__ == "__main__":
    # 检查Python版本
    if sys.version_info < (3, 7):
        print("❌ 需要Python 3.7或更高版本")
        sys.exit(1)
        
    # 运行主函数
    asyncio.run(main())