<template>
  <div class="maintenance-plan-table">
    <!-- 筛选器 -->
    <div class="filters">
      <div class="filter-group">
        <input
          v-model="searchFilters.machine_code"
          placeholder="机台代码"
          class="filter-input"
          @input="debounceSearch"
        />
        <select
          v-model="searchFilters.status"
          class="filter-select"
          @change="debounceSearch"
        >
          <option value="">所有状态</option>
          <option value="PLANNED">计划中</option>
          <option value="IN_PROGRESS">执行中</option>
          <option value="COMPLETED">已完成</option>
          <option value="CANCELLED">已取消</option>
        </select>
        <input
          v-model="searchFilters.maintenance_type"
          placeholder="维护类型"
          class="filter-input"
          @input="debounceSearch"
        />
        <button @click="showCreateModal = true" class="btn btn-primary">新增维护计划</button>
      </div>
    </div>

    <!-- 数据表格 -->
    <div class="table-container">
      <table class="data-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>计划编号</th>
            <th>机台代码</th>
            <th>维护类型</th>
            <th>计划时间</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="7" class="loading">加载中...</td>
          </tr>
          <tr v-else-if="plans.length === 0">
            <td colspan="7" class="no-data">暂无数据</td>
          </tr>
          <tr v-else v-for="plan in plans" :key="plan.id">
            <td>{{ plan.id }}</td>
            <td>{{ plan.plan_code }}</td>
            <td>{{ plan.machine_code }}</td>
            <td>{{ plan.maintenance_type }}</td>
            <td>
              <div class="time-range">
                <div>{{ formatDateTime(plan.planned_start_time) }}</div>
                <div class="time-separator">-</div>
                <div>{{ formatDateTime(plan.planned_end_time) }}</div>
              </div>
            </td>
            <td>
              <span :class="['status', plan.status.toLowerCase()]">{{ getStatusText(plan.status) }}</span>
            </td>
            <td>
              <div class="action-buttons">
                <button @click="editPlan(plan)" class="btn btn-small btn-secondary">编辑</button>
                <button @click="deletePlan(plan.id)" class="btn btn-small btn-danger">删除</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 分页 -->
    <div class="pagination">
      <span class="pagination-info">共 {{ pagination.total }} 条记录，第 {{ pagination.page }} / {{ Math.ceil(pagination.total / pagination.page_size) || 1 }} 页</span>
      <div class="pagination-controls">
        <button 
          @click="changePage(pagination.page - 1)" 
          :disabled="pagination.page <= 1"
          class="btn btn-small"
        >
          上一页
        </button>
        <button 
          @click="changePage(pagination.page + 1)" 
          :disabled="pagination.page * pagination.page_size >= pagination.total"
          class="btn btn-small"
        >
          下一页
        </button>
      </div>
    </div>

    <!-- 创建/编辑模态框 -->
    <div v-if="showCreateModal || showEditModal" class="modal-overlay" @click="closeModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>{{ showEditModal ? '编辑维护计划' : '新增维护计划' }}</h3>
          <button @click="closeModal" class="modal-close">×</button>
        </div>
        <form @submit.prevent="submitForm" class="modal-body">
          <div class="form-grid">
            <div class="form-group">
              <label>计划编号 *</label>
              <input 
                v-model="formData.plan_code" 
                type="text" 
                required 
                class="form-input"
                placeholder="输入计划编号"
              />
            </div>
            <div class="form-group">
              <label>机台代码 *</label>
              <select v-model="formData.machine_code" required class="form-select">
                <option value="">请选择机台</option>
                <option v-for="machine in machines" :key="machine.machine_code" :value="machine.machine_code">
                  {{ machine.machine_code }} - {{ machine.machine_name }}
                </option>
              </select>
            </div>
            <div class="form-group">
              <label>维护类型 *</label>
              <select v-model="formData.maintenance_type" required class="form-select">
                <option value="">请选择维护类型</option>
                <option value="日常保养">日常保养</option>
                <option value="预防性维护">预防性维护</option>
                <option value="故障维修">故障维修</option>
                <option value="大修">大修</option>
              </select>
            </div>
            <div class="form-group">
              <label>计划开始时间 *</label>
              <input 
                v-model="formData.planned_start_time" 
                type="datetime-local" 
                required 
                class="form-input"
              />
            </div>
            <div class="form-group">
              <label>计划结束时间 *</label>
              <input 
                v-model="formData.planned_end_time" 
                type="datetime-local" 
                required 
                class="form-input"
              />
            </div>
            <div class="form-group">
              <label>状态 *</label>
              <select v-model="formData.status" required class="form-select">
                <option value="">请选择状态</option>
                <option value="PLANNED">计划中</option>
                <option value="IN_PROGRESS">执行中</option>
                <option value="COMPLETED">已完成</option>
                <option value="CANCELLED">已取消</option>
              </select>
            </div>
            <div class="form-group form-group-full">
              <label>维护描述</label>
              <textarea 
                v-model="formData.description" 
                class="form-textarea"
                placeholder="输入维护描述"
                rows="3"
              ></textarea>
            </div>
          </div>
        </form>
        <div class="modal-footer">
          <button @click="closeModal" class="btn btn-secondary">取消</button>
          <button @click="submitForm" :disabled="submitting" class="btn btn-primary">
            {{ submitting ? '提交中...' : '确定' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { MachineConfigAPI } from '../services/api';

// 数据接口
interface MaintenancePlan {
  id: number;
  plan_code: string;
  machine_code: string;
  maintenance_type: string;
  planned_start_time: string;
  planned_end_time: string;
  status: string;
  description?: string;
  created_time: string;
  updated_time: string;
}

interface Machine {
  id: number;
  machine_code: string;
  machine_name: string;
  machine_type: string;
  status: string;
}

// 响应式数据
const loading = ref(false);
const submitting = ref(false);
const plans = ref<MaintenancePlan[]>([]);
const machines = ref<Machine[]>([]);
const showCreateModal = ref(false);
const showEditModal = ref(false);
const editingPlan = ref<MaintenancePlan | null>(null);

// 搜索过滤器
const searchFilters = reactive({
  machine_code: '',
  status: '',
  maintenance_type: ''
});

// 分页信息
const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0
});

// 表单数据
const formData = reactive({
  plan_code: '',
  machine_code: '',
  maintenance_type: '',
  planned_start_time: '',
  planned_end_time: '',
  status: 'PLANNED',
  description: ''
});

// 防抖搜索
let searchTimeout: number;
const debounceSearch = () => {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => {
    pagination.page = 1;
    loadData();
  }, 500);
};

// 加载数据
const loadData = async () => {
  loading.value = true;
  try {
    const params: Record<string, any> = {
      ...searchFilters,
      page: pagination.page,
      page_size: pagination.page_size
    };
    
    // 移除空值
    Object.keys(params).forEach(key => {
      if (params[key] === '') {
        delete params[key];
      }
    });
    
    const response = await MachineConfigAPI.getMaintenancePlans(params);
    plans.value = response.data.items;
    pagination.total = response.data.total;
  } catch (error) {
    console.error('加载维护计划数据失败:', error);
    ElMessage.error('加载数据失败，请稍后重试');
  } finally {
    loading.value = false;
  }
};

// 分页切换
const changePage = (page: number) => {
  pagination.page = page;
  loadData();
};

// 重置表单
const resetForm = () => {
  Object.assign(formData, {
    plan_code: '',
    machine_code: '',
    maintenance_type: '',
    planned_start_time: '',
    planned_end_time: '',
    status: 'PLANNED',
    description: ''
  });
};

// 关闭模态框
const closeModal = () => {
  showCreateModal.value = false;
  showEditModal.value = false;
  editingPlan.value = null;
  resetForm();
};

// 编辑计划
const editPlan = (plan: MaintenancePlan) => {
  editingPlan.value = plan;
  Object.assign(formData, {
    plan_code: plan.plan_code,
    machine_code: plan.machine_code,
    maintenance_type: plan.maintenance_type,
    planned_start_time: plan.planned_start_time ? plan.planned_start_time.slice(0, 16) : '',
    planned_end_time: plan.planned_end_time ? plan.planned_end_time.slice(0, 16) : '',
    status: plan.status,
    description: plan.description || ''
  });
  showEditModal.value = true;
};

// 删除计划
const deletePlan = async (id: number) => {
  try {
    await ElMessageBox.confirm(
      '确定要删除这个维护计划吗？',
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    );
  } catch (action) {
    if (action === 'cancel') {
      return;
    }
    throw action;
  }

  try {
    await MachineConfigAPI.deleteMaintenancePlan(id);
    ElMessage.success('删除成功');
    loadData();
  } catch (error) {
    console.error('删除维护计划失败:', error);
    ElMessage.error('删除失败，请稍后重试');
  }
};

// 提交表单
const submitForm = async () => {
  submitting.value = true;
  try {
    const submitData = { ...formData };
    
    // 转换日期时间格式
    if (submitData.planned_start_time) {
      submitData.planned_start_time = new Date(submitData.planned_start_time).toISOString();
    }
    if (submitData.planned_end_time) {
      submitData.planned_end_time = new Date(submitData.planned_end_time).toISOString();
    }

    if (showEditModal.value && editingPlan.value) {
      await MachineConfigAPI.updateMaintenancePlan(editingPlan.value.id, submitData);
      ElMessage.success('更新成功');
    } else {
      await MachineConfigAPI.createMaintenancePlan(submitData);
      ElMessage.success('创建成功');
    }
    
    closeModal();
    loadData();
  } catch (error) {
    console.error('提交维护计划失败:', error);
    ElMessage.error('操作失败，请稍后重试');
  } finally {
    submitting.value = false;
  }
};

// 加载机台列表
const loadMachines = async () => {
  try {
    const response = await MachineConfigAPI.getMachines({ page: 1, page_size: 100 });
    machines.value = response.data.items;
  } catch (error) {
    console.error('加载机台列表失败:', error);
  }
};

// 格式化日期时间
const formatDateTime = (dateTime: string) => {
  return new Date(dateTime).toLocaleString('zh-CN');
};

// 获取状态文本
const getStatusText = (status: string) => {
  const statusMap = {
    'PLANNED': '计划中',
    'IN_PROGRESS': '执行中',
    'COMPLETED': '已完成',
    'CANCELLED': '已取消'
  };
  return statusMap[status] || status;
};

// 初始化
onMounted(() => {
  loadData();
  loadMachines();
});
</script>

<style scoped>
.maintenance-plan-table {
  padding: 20px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.filters {
  margin-bottom: 20px;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 6px;
  border: 1px solid #e9ecef;
}

.filter-group {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.filter-input, .filter-select {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  min-width: 120px;
}

.filter-input:focus, .filter-select:focus {
  outline: none;
  border-color: #409eff;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.2);
}

.table-container {
  margin-bottom: 20px;
  border: 1px solid #e9ecef;
  border-radius: 6px;
  overflow: hidden;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  background: white;
}

.data-table th {
  background: #f8f9fa;
  padding: 12px;
  text-align: left;
  font-weight: 600;
  color: #495057;
  border-bottom: 2px solid #dee2e6;
}

.data-table td {
  padding: 12px;
  border-bottom: 1px solid #dee2e6;
  vertical-align: top;
}

.data-table tr:hover {
  background: #f8f9fa;
}

.time-range {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.time-separator {
  color: #6c757d;
  font-weight: 500;
}

.status {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  text-transform: uppercase;
}

.status.planned { background: #e3f2fd; color: #1976d2; }
.status.in_progress { background: #fff3e0; color: #f57c00; }
.status.completed { background: #e8f5e8; color: #388e3c; }
.status.cancelled { background: #ffebee; color: #d32f2f; }

.action-buttons {
  display: flex;
  gap: 8px;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.btn-small {
  padding: 6px 12px;
  font-size: 12px;
}

.btn-primary {
  background: #409eff;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #337ecc;
}

.btn-secondary {
  background: #6c757d;
  color: white;
}

.btn-secondary:hover:not(:disabled) {
  background: #545b62;
}

.btn-danger {
  background: #dc3545;
  color: white;
}

.btn-danger:hover:not(:disabled) {
  background: #c82333;
}

.pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 0;
}

.pagination-info {
  color: #6c757d;
  font-size: 14px;
}

.pagination-controls {
  display: flex;
  gap: 8px;
}

.loading, .no-data {
  text-align: center;
  padding: 40px;
  color: #6c757d;
  font-style: italic;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 8px;
  width: 90%;
  max-width: 600px;
  max-height: 90%;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #e9ecef;
}

.modal-header h3 {
  margin: 0;
  color: #495057;
}

.modal-close {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #6c757d;
  padding: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-body {
  padding: 20px;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group-full {
  grid-column: 1 / -1;
}

.form-group label {
  font-weight: 500;
  color: #495057;
  font-size: 14px;
}

.form-input, .form-select, .form-textarea {
  padding: 10px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.form-input:focus, .form-select:focus, .form-textarea:focus {
  outline: none;
  border-color: #409eff;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.2);
}

.form-textarea {
  resize: vertical;
  min-height: 80px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 20px;
  border-top: 1px solid #e9ecef;
}

@media (max-width: 768px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
  
  .filter-group {
    flex-direction: column;
    align-items: stretch;
  }
  
  .action-buttons {
    flex-direction: column;
  }
  
  .pagination {
    flex-direction: column;
    gap: 12px;
  }
}
</style>