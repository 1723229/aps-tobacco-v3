<template>
  <div class="work-calendar-container">
    <!-- 工作日历配置头部 -->
    <div class="calendar-header">
      <div class="header-info">
        <h2>
          <i class="fas fa-calendar-alt"></i>
          工作日历管理
        </h2>
        <p class="description">
          配置月度生产工作日历，管理工作日、休息日、节假日和维护日
        </p>
      </div>
      <div class="header-actions">
        <div class="date-selector">
          <label>选择年月：</label>
          <el-date-picker
            v-model="selectedMonth"
            type="month"
            placeholder="选择月份"
            format="YYYY年MM月"
            value-format="YYYY-MM"
            @change="loadCalendarData"
          />
        </div>
        <el-button type="primary" icon="Refresh" @click="refreshCalendar">
          刷新
        </el-button>
      </div>
    </div>

    <!-- 日历概览卡片 -->
    <div class="calendar-stats">
      <div class="stat-card">
        <div class="stat-icon work">
          <i class="fas fa-briefcase"></i>
        </div>
        <div class="stat-content">
          <div class="stat-number">{{ calendarStats.totalWorkDays }}</div>
          <div class="stat-label">工作日</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon holiday">
          <i class="fas fa-umbrella-beach"></i>
        </div>
        <div class="stat-content">
          <div class="stat-number">{{ calendarStats.totalHolidays }}</div>
          <div class="stat-label">节假日</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon maintenance">
          <i class="fas fa-tools"></i>
        </div>
        <div class="stat-content">
          <div class="stat-number">{{ calendarStats.totalMaintenanceDays }}</div>
          <div class="stat-label">维护日</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon hours">
          <i class="fas fa-clock"></i>
        </div>
        <div class="stat-content">
          <div class="stat-number">{{ calendarStats.totalWorkingHours }}</div>
          <div class="stat-label">总工时</div>
        </div>
      </div>
    </div>

    <!-- 日历展示 -->
    <div class="calendar-display">
      <el-card>
        <template #header>
          <div class="calendar-title">
            <h3>{{ currentMonthTitle }} 工作日历</h3>
            <div class="legend">
              <span class="legend-item workday">
                <span class="legend-color"></span>
                工作日
              </span>
              <span class="legend-item weekend">
                <span class="legend-color"></span>
                周末
              </span>
              <span class="legend-item holiday">
                <span class="legend-color"></span>
                节假日
              </span>
              <span class="legend-item maintenance">
                <span class="legend-color"></span>
                维护日
              </span>
            </div>
          </div>
        </template>

        <!-- 日历网格 -->
        <div class="calendar-grid">
          <!-- 星期头部 -->
          <div class="week-header">
            <div class="day-header">一</div>
            <div class="day-header">二</div>
            <div class="day-header">三</div>
            <div class="day-header">四</div>
            <div class="day-header">五</div>
            <div class="day-header">六</div>
            <div class="day-header">日</div>
          </div>

          <!-- 日期网格 -->
          <div class="days-grid">
            <div
              v-for="day in calendarDays"
              :key="day.date"
              :class="[
                'day-cell',
                day.dayType.toLowerCase(),
                { 'other-month': !day.isCurrentMonth }
              ]"
              @click="editDayConfig(day)"
            >
              <div class="day-number">{{ day.day }}</div>
              <div class="day-info">
                <div class="work-hours" v-if="day.workingHours > 0">
                  {{ day.workingHours }}h
                </div>
                <div class="day-note" v-if="day.note">
                  {{ day.note }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 日历详情表格 -->
    <div class="calendar-table">
      <el-card>
        <template #header>
          <div class="table-header">
            <h3>日历详情配置</h3>
            <el-button type="primary" icon="Plus" @click="addCustomDay">
              添加特殊日期
            </el-button>
          </div>
        </template>

        <el-table
          :data="calendarTableData"
          v-loading="loading"
          @selection-change="handleSelectionChange"
        >
          <el-table-column type="selection" width="55" />
          <el-table-column prop="date" label="日期" width="120">
            <template #default="scope">
              {{ formatDate(scope.row.calendar_date) }}
            </template>
          </el-table-column>
          <el-table-column prop="weekDay" label="星期" width="80">
            <template #default="scope">
              {{ getWeekDayName(scope.row.calendar_week_day) }}
            </template>
          </el-table-column>
          <el-table-column prop="dayType" label="日期类型" width="120">
            <template #default="scope">
              <el-tag
                :type="getDayTypeColor(scope.row.monthly_day_type)"
                size="small"
              >
                {{ getDayTypeName(scope.row.monthly_day_type) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="isWorking" label="是否工作" width="100">
            <template #default="scope">
              <el-switch
                v-model="scope.row.monthly_is_working"
                :active-value="1"
                :inactive-value="0"
                @change="updateWorkingStatus(scope.row)"
              />
            </template>
          </el-table-column>
          <el-table-column prop="workingHours" label="工作时长" width="100">
            <template #default="scope">
              <span>{{ scope.row.monthly_total_hours }}h</span>
            </template>
          </el-table-column>
          <el-table-column prop="shifts" label="班次配置" min-width="200">
            <template #default="scope">
              <div class="shifts-display">
                <el-tag
                  v-for="shift in scope.row.monthly_shifts"
                  :key="shift.shift_name"
                  size="small"
                  class="shift-tag"
                >
                  {{ shift.shift_name }}: {{ shift.start }}-{{ shift.end }}
                </el-tag>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="holidayName" label="节假日名称" width="120">
            <template #default="scope">
              {{ scope.row.monthly_holiday_name || '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="notes" label="备注" min-width="150">
            <template #default="scope">
              {{ scope.row.monthly_notes || '-' }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="160" fixed="right">
            <template #default="scope">
              <el-button
                size="small"
                type="primary"
                icon="Edit"
                @click="editDayConfig(scope.row)"
              >
                编辑
              </el-button>
              <el-button
                size="small"
                type="danger"
                icon="Delete"
                @click="deleteDayConfig(scope.row)"
              >
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <!-- 分页 -->
        <div class="pagination">
          <el-pagination
            v-model:current-page="pagination.page"
            v-model:page-size="pagination.pageSize"
            :page-sizes="[20, 50, 100]"
            :total="pagination.total"
            layout="total, sizes, prev, pager, next, jumper"
            @size-change="handleSizeChange"
            @current-change="handleCurrentChange"
          />
        </div>
      </el-card>
    </div>

    <!-- 编辑对话框 -->
    <el-dialog
      v-model="editDialogVisible"
      title="编辑日期配置"
      width="600px"
      :before-close="handleDialogClose"
    >
      <el-form
        :model="editForm"
        :rules="editFormRules"
        ref="editFormRef"
        label-width="120px"
      >
        <el-form-item label="日期" prop="date">
          <el-date-picker
            v-model="editForm.date"
            type="date"
            placeholder="选择日期"
            value-format="YYYY-MM-DD"
            :disabled="!editForm.isNew"
            style="width: 100%;"
          />
        </el-form-item>
        
        <el-form-item label="日期类型" prop="dayType">
          <el-select v-model="editForm.dayType" placeholder="请选择日期类型" style="width: 100%;">
            <el-option label="工作日" value="WORKDAY" />
            <el-option label="节假日" value="HOLIDAY" />
            <el-option label="维护日" value="MAINTENANCE" />
            <el-option label="特殊日" value="SPECIAL" />
          </el-select>
        </el-form-item>

        <el-form-item label="是否工作" prop="isWorking">
          <el-switch
            v-model="editForm.isWorking"
            :active-value="1"
            :inactive-value="0"
          />
        </el-form-item>

        <el-form-item label="工作时长" prop="workingHours" v-if="editForm.isWorking">
          <el-input-number
            v-model="editForm.workingHours"
            :min="0"
            :max="24"
            :step="0.5"
            style="width: 100%;"
          />
          <span style="margin-left: 10px;">小时</span>
        </el-form-item>

        <el-form-item label="节假日名称" prop="holidayName" v-if="editForm.dayType === 'HOLIDAY'">
          <el-input v-model="editForm.holidayName" placeholder="请输入节假日名称" />
        </el-form-item>

        <el-form-item label="备注" prop="notes">
          <el-input
            v-model="editForm.notes"
            type="textarea"
            placeholder="请输入备注信息"
            :rows="3"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="handleDialogClose">取消</el-button>
          <el-button type="primary" @click="saveDayConfig" :loading="saving">
            保存
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/services/api'

// 响应式数据
const loading = ref(false)
const selectedMonth = ref('')
const calendarData = ref<any[]>([])
const calendarTableData = ref<any[]>([])
const selectedRows = ref<any[]>([])

// 分页数据
const pagination = reactive({
  page: 1,
  pageSize: 31,
  total: 0
})

// 日历统计数据
const calendarStats = reactive({
  totalWorkDays: 0,
  totalHolidays: 0,
  totalMaintenanceDays: 0,
  totalWorkingHours: 0
})

// 编辑对话框相关
const editDialogVisible = ref(false)
const saving = ref(false)
const editFormRef = ref()

// 编辑表单数据
const editForm = reactive({
  id: null,
  date: '',
  dayType: 'WORKDAY',
  isWorking: 1,
  workingHours: 8,
  holidayName: '',
  notes: '',
  isNew: false
})

// 表单验证规则
const editFormRules = {
  date: [
    { required: true, message: '请选择日期', trigger: 'blur' }
  ],
  dayType: [
    { required: true, message: '请选择日期类型', trigger: 'change' }
  ],
  workingHours: [
    { required: true, message: '请输入工作时长', trigger: 'blur' },
    { type: 'number', min: 0, max: 24, message: '工作时长必须在0-24小时之间', trigger: 'blur' }
  ]
}

// 计算属性
const currentMonthTitle = computed(() => {
  if (!selectedMonth.value) return ''
  const [year, month] = selectedMonth.value.split('-')
  return `${year}年${month}月`
})

const calendarDays = computed(() => {
  if (!calendarData.value.length) return []
  
  const [year, month] = selectedMonth.value.split('-')
  const firstDay = new Date(parseInt(year), parseInt(month) - 1, 1)
  const lastDay = new Date(parseInt(year), parseInt(month), 0)
  const startOfWeek = new Date(firstDay)
  startOfWeek.setDate(firstDay.getDate() - (firstDay.getDay() === 0 ? 6 : firstDay.getDay() - 1))
  
  const days = []
  const current = new Date(startOfWeek)
  
  for (let i = 0; i < 42; i++) {
    const dateStr = current.toISOString().split('T')[0]
    const dayData = calendarData.value.find(d => d.calendar_date === dateStr)
    
    days.push({
      date: dateStr,
      day: current.getDate(),
      isCurrentMonth: current.getMonth() === parseInt(month) - 1,
      dayType: dayData?.monthly_day_type || 'WORKDAY',
      workingHours: dayData?.monthly_total_hours || 0,
      note: dayData?.monthly_notes || '',
      data: dayData
    })
    
    current.setDate(current.getDate() + 1)
  }
  
  return days
})

// 生命周期
onMounted(() => {
  // 设置默认月份为当前月份
  const now = new Date()
  selectedMonth.value = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
  loadCalendarData()
})

// 方法
const loadCalendarData = async () => {
  if (!selectedMonth.value) return
  
  loading.value = true
  try {
    const [year, month] = selectedMonth.value.split('-')
    const response = await api.get(`/api/v1/work-calendar?year=${year}&month=${month}`)
    
    if (response.data.code === 200) {
      const data = response.data.data
      calendarData.value = data.calendar_days || []
      calendarTableData.value = data.calendar_days || []
      
      // 更新统计数据
      calendarStats.totalWorkDays = data.total_work_days || 0
      calendarStats.totalHolidays = data.total_holidays || 0
      calendarStats.totalMaintenanceDays = data.total_maintenance_days || 0
      calendarStats.totalWorkingHours = data.total_working_hours || 0
      
      pagination.total = calendarTableData.value.length
    }
  } catch (error) {
    console.error('加载工作日历失败:', error)
    ElMessage.error('加载工作日历失败')
  } finally {
    loading.value = false
  }
}

const refreshCalendar = () => {
  loadCalendarData()
}

const editDayConfig = (day: any) => {
  // 重置表单
  resetEditForm()
  
  if (day.data) {
    // 编辑现有日期
    editForm.id = day.data.monthly_calendar_id
    editForm.date = day.data.calendar_date
    editForm.dayType = day.data.monthly_day_type
    editForm.isWorking = day.data.monthly_is_working
    editForm.workingHours = day.data.monthly_total_hours || 8
    editForm.holidayName = day.data.monthly_holiday_name || ''
    editForm.notes = day.data.monthly_notes || ''
    editForm.isNew = false
  } else {
    // 新增日期配置
    editForm.date = day.date || ''
    editForm.isNew = true
  }
  
  editDialogVisible.value = true
}

const addCustomDay = () => {
  // 重置表单并设置为新增模式
  resetEditForm()
  editForm.isNew = true
  editDialogVisible.value = true
}

const updateWorkingStatus = async (row: any) => {
  try {
    const requestData = {
      calendar_date: row.calendar_date,
      monthly_day_type: row.monthly_day_type,
      monthly_is_working: row.monthly_is_working,
      monthly_total_hours: row.monthly_is_working ? (row.monthly_total_hours || 8) : 0,
      monthly_holiday_name: row.monthly_holiday_name,
      monthly_notes: row.monthly_notes
    }
    
    await api.put(`/api/v1/work-calendar/${row.monthly_calendar_id}`, requestData)
    ElMessage.success('工作状态更新成功')
    await loadCalendarData()
  } catch (error) {
    console.error('工作状态更新失败:', error)
    ElMessage.error('工作状态更新失败')
    // 恢复原状态
    row.monthly_is_working = row.monthly_is_working === 1 ? 0 : 1
  }
}

const deleteDayConfig = async (row: any) => {
  try {
    await ElMessageBox.confirm('确认删除此日期配置?', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await api.delete(`/api/v1/work-calendar/${row.monthly_calendar_id}`)
    ElMessage.success('删除成功')
    await loadCalendarData()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
      ElMessage.error('删除失败')
    }
  }
}

const handleSelectionChange = (selection: any[]) => {
  selectedRows.value = selection
}

const handleSizeChange = (val: number) => {
  pagination.pageSize = val
  loadCalendarData()
}

const handleCurrentChange = (val: number) => {
  pagination.page = val
  loadCalendarData()
}

// 编辑对话框相关方法
const resetEditForm = () => {
  editForm.id = null
  editForm.date = ''
  editForm.dayType = 'WORKDAY'
  editForm.isWorking = 1
  editForm.workingHours = 8
  editForm.holidayName = ''
  editForm.notes = ''
  editForm.isNew = false
}

const handleDialogClose = () => {
  editDialogVisible.value = false
  resetEditForm()
}

const saveDayConfig = async () => {
  try {
    // 表单验证
    await editFormRef.value?.validate()
    
    saving.value = true
    
    // 构建请求数据
    const requestData = {
      calendar_date: editForm.date,
      monthly_day_type: editForm.dayType,
      monthly_is_working: editForm.isWorking,
      monthly_total_hours: editForm.isWorking ? editForm.workingHours : 0,
      monthly_holiday_name: editForm.dayType === 'HOLIDAY' ? editForm.holidayName : null,
      monthly_notes: editForm.notes
    }
    
    if (editForm.isNew) {
      // 新增日期配置
      await api.post('/api/v1/work-calendar', requestData)
      ElMessage.success('新增日期配置成功')
    } else {
      // 更新日期配置
      await api.put(`/api/v1/work-calendar/${editForm.id}`, requestData)
      ElMessage.success('更新日期配置成功')
    }
    
    // 关闭对话框并刷新数据
    editDialogVisible.value = false
    await loadCalendarData()
    
  } catch (error: any) {
    console.error('保存日期配置失败:', error)
    ElMessage.error('保存失败: ' + (error.message || '请检查网络连接'))
  } finally {
    saving.value = false
  }
}

// 辅助方法
const formatDate = (date: string) => {
  return date.replace(/-/g, '/')
}

const getWeekDayName = (weekDay: number) => {
  const names = ['', '一', '二', '三', '四', '五', '六', '日']
  return names[weekDay] || ''
}

const getDayTypeName = (type: string) => {
  const types: Record<string, string> = {
    'WORKDAY': '工作日',
    'WEEKEND': '周末',
    'HOLIDAY': '节假日',
    'MAINTENANCE': '维护日'
  }
  return types[type] || type
}

const getDayTypeColor = (type: string) => {
  const colors: Record<string, string> = {
    'WORKDAY': '',
    'WEEKEND': 'info',
    'HOLIDAY': 'warning',
    'MAINTENANCE': 'danger'
  }
  return colors[type] || ''
}
</script>

<style scoped>
.work-calendar-container {
  padding: 20px;
}

.calendar-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid #e4e7ed;
}

.header-info h2 {
  margin: 0 0 8px 0;
  color: #303133;
  font-size: 24px;
  font-weight: 600;
}

.header-info h2 i {
  margin-right: 8px;
  color: #409eff;
}

.description {
  color: #909399;
  margin: 0;
  font-size: 14px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.date-selector {
  display: flex;
  align-items: center;
  gap: 8px;
}

.date-selector label {
  color: #606266;
  font-size: 14px;
  white-space: nowrap;
}

.calendar-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  transition: all 0.3s ease;
}

.stat-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  color: #fff;
}

.stat-icon.work {
  background: linear-gradient(135deg, #409eff, #66b1ff);
}

.stat-icon.holiday {
  background: linear-gradient(135deg, #f56c6c, #f78989);
}

.stat-icon.maintenance {
  background: linear-gradient(135deg, #e6a23c, #ebb563);
}

.stat-icon.hours {
  background: linear-gradient(135deg, #67c23a, #85ce61);
}

.stat-content {
  flex: 1;
}

.stat-number {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 4px;
}

.stat-label {
  color: #909399;
  font-size: 14px;
}

.calendar-display {
  margin-bottom: 24px;
}

.calendar-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.calendar-title h3 {
  margin: 0;
  color: #303133;
  font-size: 18px;
  font-weight: 600;
}

.legend {
  display: flex;
  gap: 16px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #606266;
}

.legend-color {
  width: 12px;
  height: 12px;
  border-radius: 2px;
}

.legend-item.workday .legend-color {
  background: #67c23a;
}

.legend-item.weekend .legend-color {
  background: #909399;
}

.legend-item.holiday .legend-color {
  background: #e6a23c;
}

.legend-item.maintenance .legend-color {
  background: #f56c6c;
}

.calendar-grid {
  max-width: 100%;
}

.week-header {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 1px;
  margin-bottom: 8px;
}

.day-header {
  text-align: center;
  padding: 12px;
  font-weight: 600;
  color: #606266;
  background: #f5f7fa;
  border-radius: 4px;
}

.days-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 1px;
}

.day-cell {
  min-height: 80px;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  padding: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
}

.day-cell:hover {
  border-color: #409eff;
  box-shadow: 0 2px 4px rgba(64, 158, 255, 0.2);
}

.day-cell.workday {
  background: #f0f9ff;
  border-color: #67c23a;
}

.day-cell.weekend {
  background: #f5f5f5;
  border-color: #909399;
}

.day-cell.holiday {
  background: #fdf6ec;
  border-color: #e6a23c;
}

.day-cell.maintenance {
  background: #fef0f0;
  border-color: #f56c6c;
}

.day-cell.other-month {
  opacity: 0.3;
}

.day-number {
  font-weight: 600;
  font-size: 16px;
  color: #303133;
  margin-bottom: 4px;
}

.day-info {
  font-size: 12px;
}

.work-hours {
  color: #67c23a;
  font-weight: 500;
}

.day-note {
  color: #909399;
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.calendar-table {
  margin-bottom: 24px;
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.table-header h3 {
  margin: 0;
  color: #303133;
  font-size: 18px;
  font-weight: 600;
}

.shifts-display {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.shift-tag {
  margin: 0;
}

.pagination {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .calendar-header {
    flex-direction: column;
    gap: 16px;
    align-items: stretch;
  }
  
  .header-actions {
    flex-direction: column;
    gap: 12px;
  }
  
  .calendar-stats {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .calendar-title {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }
  
  .legend {
    flex-wrap: wrap;
    gap: 8px;
  }
  
  .day-cell {
    min-height: 60px;
    padding: 4px;
  }
  
  .day-number {
    font-size: 14px;
  }
  
  .day-info {
    font-size: 10px;
  }
}
</style>