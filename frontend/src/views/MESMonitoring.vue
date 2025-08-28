<template>
  <div class="mes-dashboard">
    <div class="page-header">
      <h1>MES系统监控</h1>
      <p>实时监控MES系统状态、机台运行情况和维护计划</p>
    </div>

    <!-- 系统状态 -->
    <div class="status-section">
      <el-card class="status-card">
        <template #header>
          <div class="card-header">
            <span>MES系统状态</span>
            <el-button size="small" @click="refreshMESStatus">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
        </template>
        
        <div class="status-content">
          <div class="status-item">
            <el-tag :type="mesStatus.status === 'connected' ? 'success' : 'danger'" size="large">
              {{ mesStatus.status === 'connected' ? '已连接' : '连接异常' }}
            </el-tag>
          </div>
          <div class="status-details">
            <p>版本: {{ mesStatus.version }}</p>
            <p>响应时间: {{ mesStatus.response_time_ms }}ms</p>
            <p>最后心跳: {{ formatTime(mesStatus.last_heartbeat) }}</p>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 机台状态 -->
    <div class="machines-section">
      <el-card>
        <template #header>
          <div class="card-header">
            <span>机台状态监控</span>
            <el-button size="small" @click="refreshMachineStatus">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
        </template>
        
        <div class="machines-grid">
          <div 
            v-for="machine in machines" 
            :key="machine.machine_code"
            class="machine-card"
            :class="{'machine-error': machine.status === 'ERROR'}"
          >
            <div class="machine-header">
              <h3>{{ machine.machine_code }}</h3>
              <el-tag 
                :type="getMachineStatusType(machine.status)"
                size="small"
              >
                {{ getMachineStatusText(machine.status) }}
              </el-tag>
            </div>
            
            <div class="machine-details">
              <div class="metric">
                <label>利用率:</label>
                <el-progress 
                  :percentage="Math.round(machine.utilization_rate * 100)"
                  :color="getProgressColor(machine.utilization_rate)"
                />
              </div>
              
              <div class="metric">
                <label>效率:</label>
                <el-progress 
                  :percentage="Math.round(machine.efficiency_rating * 100)"
                  :color="getProgressColor(machine.efficiency_rating)"
                />
              </div>
              
              <div class="metric">
                <label>今日产量:</label>
                <span class="metric-value">{{ machine.production_count_today }}</span>
              </div>
              
              <div v-if="machine.current_work_order" class="metric">
                <label>当前工单:</label>
                <span class="metric-value">{{ machine.current_work_order }}</span>
              </div>
              
              <div v-if="machine.error_message" class="error-message">
                <el-icon color="red"><Warning /></el-icon>
                {{ machine.error_message }}
              </div>
            </div>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 维护计划 -->
    <div class="maintenance-section">
      <el-card>
        <template #header>
          <div class="card-header">
            <span>维护计划</span>
            <el-button size="small" @click="refreshMaintenanceSchedule">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
        </template>
        
        <el-table :data="maintenancePlans" stripe>
          <el-table-column prop="maintenance_id" label="维护ID" width="150" />
          <el-table-column prop="machine_code" label="机台" width="100" />
          <el-table-column prop="maintenance_type" label="类型" width="100">
            <template #default="scope">
              <el-tag 
                :type="scope.row.maintenance_type === 'ROUTINE' ? 'info' : 'warning'"
                size="small"
              >
                {{ scope.row.maintenance_type === 'ROUTINE' ? '例行' : '预防性' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="priority" label="优先级" width="100">
            <template #default="scope">
              <el-tag 
                :type="scope.row.priority === 'HIGH' ? 'danger' : 'info'"
                size="small"
              >
                {{ scope.row.priority }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="planned_start" label="开始时间" width="160">
            <template #default="scope">
              {{ formatTime(scope.row.planned_start) }}
            </template>
          </el-table-column>
          <el-table-column prop="estimated_duration_hours" label="预计耗时(小时)" width="120" />
          <el-table-column prop="assigned_technician" label="技术员" width="100" />
          <el-table-column prop="description" label="描述" show-overflow-tooltip />
        </el-table>
      </el-card>
    </div>

    <!-- 生产事件 -->
    <div class="events-section">
      <el-card>
        <template #header>
          <div class="card-header">
            <span>最近事件</span>
            <el-button size="small" @click="refreshEvents">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
        </template>
        
        <div class="events-list">
          <div 
            v-for="event in events" 
            :key="event.event_id"
            class="event-item"
            :class="{'event-alarm': event.severity === 'HIGH'}"
          >
            <div class="event-header">
              <el-tag 
                :type="event.severity === 'HIGH' ? 'danger' : 'info'"
                size="small"
              >
                {{ event.event_type }}
              </el-tag>
              <span class="event-time">{{ formatTime(event.timestamp) }}</span>
            </div>
            <div class="event-content">
              <span class="event-machine">{{ event.machine_code }}</span>
              <span class="event-message">{{ event.message }}</span>
            </div>
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Warning } from '@element-plus/icons-vue'
import { MESAPI } from '@/services/api'

// 响应式数据
const mesStatus = reactive({
  status: 'disconnected',
  response_time_ms: 0,
  last_heartbeat: '',
  version: '',
  capabilities: []
})

const machines = ref([])
const maintenancePlans = ref([])
const events = ref([])

// 方法定义
const formatTime = (timeStr: string) => {
  if (!timeStr) return '--'
  const date = new Date(timeStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const getMachineStatusType = (status: string) => {
  const typeMap: Record<string, any> = {
    'RUNNING': 'success',
    'IDLE': 'info',
    'MAINTENANCE': 'warning',
    'ERROR': 'danger',
    'STOPPED': 'info'
  }
  return typeMap[status] || 'info'
}

const getMachineStatusText = (status: string) => {
  const textMap: Record<string, string> = {
    'RUNNING': '运行中',
    'IDLE': '空闲',
    'MAINTENANCE': '维护中',
    'ERROR': '故障',
    'STOPPED': '停机'
  }
  return textMap[status] || status
}

const getProgressColor = (value: number) => {
  if (value >= 0.8) return '#67c23a'
  if (value >= 0.6) return '#e6a23c'
  return '#f56c6c'
}

// API调用方法
const refreshMESStatus = async () => {
  try {
    const response = await MESAPI.checkHealth()
    if (response.data) {
      Object.assign(mesStatus, response.data)
    }
    ElMessage.success('MES状态刷新成功')
  } catch (error) {
    console.error('刷新MES状态失败:', error)
    ElMessage.error('刷新MES状态失败')
  }
}

const refreshMachineStatus = async () => {
  try {
    const response = await MESAPI.getMachineStatus()
    if (response.data?.machine_statuses) {
      machines.value = response.data.machine_statuses
    }
    ElMessage.success('机台状态刷新成功')
  } catch (error) {
    console.error('刷新机台状态失败:', error)
    ElMessage.error('刷新机台状态失败')
  }
}

const refreshMaintenanceSchedule = async () => {
  try {
    const response = await MESAPI.getMaintenanceSchedule()
    if (response.data?.maintenance_plans) {
      maintenancePlans.value = response.data.maintenance_plans
    }
    ElMessage.success('维护计划刷新成功')
  } catch (error) {
    console.error('刷新维护计划失败:', error)
    ElMessage.error('刷新维护计划失败')
  }
}

const refreshEvents = async () => {
  try {
    const response = await MESAPI.getRecentEvents()
    if (response.data?.events) {
      events.value = response.data.events
    }
    ElMessage.success('事件列表刷新成功')
  } catch (error) {
    console.error('刷新事件列表失败:', error)
    ElMessage.error('刷新事件列表失败')
  }
}

// 组件挂载时加载数据
onMounted(() => {
  refreshMESStatus()
  refreshMachineStatus()
  refreshMaintenanceSchedule()
  refreshEvents()
})
</script>

<style scoped>
.mes-dashboard {
  padding: 20px;
}

.page-header {
  margin-bottom: 24px;
}

.page-header h1 {
  margin: 0 0 8px 0;
  color: #303133;
}

.page-header p {
  margin: 0;
  color: #606266;
}

.status-section,
.machines-section,
.maintenance-section,
.events-section {
  margin-bottom: 24px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.status-card .status-content {
  display: flex;
  align-items: center;
  gap: 20px;
}

.status-details p {
  margin: 4px 0;
  color: #606266;
  font-size: 14px;
}

.machines-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.machine-card {
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  padding: 16px;
  background: #fafafa;
}

.machine-card.machine-error {
  border-color: #f56c6c;
  background: #fef0f0;
}

.machine-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.machine-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.machine-details .metric {
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.machine-details label {
  font-size: 14px;
  color: #606266;
  min-width: 60px;
}

.metric-value {
  font-weight: 600;
  color: #303133;
}

.error-message {
  color: #f56c6c;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 8px;
}

.events-list {
  max-height: 300px;
  overflow-y: auto;
}

.event-item {
  border-bottom: 1px solid #e4e7ed;
  padding: 12px 0;
}

.event-item:last-child {
  border-bottom: none;
}

.event-item.event-alarm {
  background: #fef0f0;
  margin: 0 -16px;
  padding: 12px 16px;
  border-radius: 4px;
}

.event-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.event-time {
  font-size: 12px;
  color: #909399;
}

.event-content {
  display: flex;
  gap: 16px;
  align-items: center;
}

.event-machine {
  font-weight: 600;
  color: #409eff;
  min-width: 80px;
}

.event-message {
  color: #606266;
  font-size: 14px;
}
</style>