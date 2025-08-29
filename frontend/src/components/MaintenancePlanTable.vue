<template>
  <div class="maintenance-plan-table-container">
    <!-- 操作栏 -->
    <div class="action-bar">
      <div class="search-filters">
        <input
          v-model="searchFilters.machine_code"
          type="text"
          placeholder="机台代码"
          class="search-input"
          @input="debounceSearch"
        />
        <select 
          v-model="searchFilters.status" 
          class="filter-select"
          @change="loadData"
        >
          <option value="">所有状态</option>
          <option value="PLANNED">计划中</option>
          <option value="IN_PROGRESS">执行中</option>
          <option value="COMPLETED">已完成</option>
          <option value="CANCELLED">已取消</option>
        </select>
        <input
          v-model="searchFilters.maintenance_type"
          type="text"
          placeholder="维护类型"
          class="search-input"
          @input="debounceSearch"
        />
      </div>
      <button @click="showCreateModal = true" class="btn btn-primary">
        <i class="fas fa-plus"></i>
        新增维护计划
      </button>
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
            <th>实际时间</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="8" class="loading-cell">
              <div class="loading-spinner">
                <i class="fas fa-spinner fa-spin"></i>
                加载中...
              </div>
            </td>
          </tr>
          <tr v-else-if="plans.length === 0">
            <td colspan="8" class="empty-cell">暂无数据</td>
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
              <div class="time-range" v-if="plan.actual_start_time">
                <div>{{ formatDateTime(plan.actual_start_time) }}</div>
                <div class="time-separator">-</div>
                <div>{{ plan.actual_end_time ? formatDateTime(plan.actual_end_time) : '进行中' }}</div>
              </div>
              <span v-else class="no-actual-time">未开始</span>
            </td>
            <td>
              <span :class="['status-badge', plan.status.toLowerCase()]">
                {{ getStatusText(plan.status) }}
              </span>
            </td>
            <td>
              <div class="action-buttons">
                <button @click="editPlan(plan)" class="btn-action btn-edit">
                  <i class="fas fa-edit"></i>
                </button>
                <button @click="deletePlan(plan.id)" class="btn-action btn-delete">
                  <i class="fas fa-trash"></i>
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 分页 -->
    <div class="pagination-container">
      <div class="pagination-info">
        共 {{ pagination.total }} 条记录，第 {{ pagination.page }} / {{ Math.ceil(pagination.total / pagination.page_size) }} 页
      </div>
      <div class="pagination">
        <button 
          @click="changePage(pagination.page - 1)" 
          :disabled="pagination.page <= 1"
          class="btn btn-pagination"
        >
          上一页
        </button>
        <button 
          @click="changePage(pagination.page + 1)" 
          :disabled="pagination.page >= Math.ceil(pagination.total / pagination.page_size)"
          class="btn btn-pagination"
        >
          下一页
        </button>
      </div>
    </div>

    <!-- 新增/编辑模态框 -->
    <div v-if="showCreateModal || showEditModal" class="modal-overlay" @click="closeModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>{{ showCreateModal ? '新增维护计划' : '编辑维护计划' }}</h3>
          <button @click="closeModal" class="close-btn">
            <i class="fas fa-times"></i>
          </button>
        </div>
        <div class="modal-body">
          <form @submit.prevent="submitForm">
            <div class="form-group">
              <label>计划编号 *</label>
              <input 
                v-model="formData.plan_code" 
                type="text" 
                required 
                class="form-input"
                placeholder="请输入计划编号"
              />
            </div>
            <div class="form-group">
              <label>机台代码 *</label>
              <select 
                v-model="formData.machine_code" 
                required 
                class="form-select"
              >
                <option value="">请选择机台代码</option>
                <option 
                  v-for="machine in machines" 
                  :key="machine.id" 
                  :value="machine.machine_code"
                >
                  {{ machine.machine_code }} - {{ machine.machine_name }}
                </option>
              </select>
            </div>
            <div class="form-group">
              <label>维护类型 *</label>
              <select 
                v-model="formData.maintenance_type" 
                required 
                class="form-select"
              >
                <option value="">请选择维护类型</option>
                <option value="日常保养">日常保养</option>
                <option value="预防性维护">预防性维护</option>
                <option value="故障维修">故障维修</option>
                <option value="大修">大修</option>
                <option value="清洁维护">清洁维护</option>
                <option value="安全检查">安全检查</option>
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
              <label>实际开始时间</label>
              <input 
                v-model="formData.actual_start_time" 
                type="datetime-local" 
                class="form-input"
              />
            </div>
            <div class="form-group">
              <label>实际结束时间</label>
              <input 
                v-model="formData.actual_end_time" 
                type="datetime-local" 
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
            <div class="form-group">
              <label>维护描述</label>
              <textarea 
                v-model="formData.description" 
                class="form-textarea"
                placeholder="请输入维护描述"
                rows="3"
              ></textarea>
            </div>
            <div class="form-actions">
              <button type="button" @click="closeModal" class="btn btn-cancel">取消</button>
              <button type="submit" :disabled="submitting" class="btn btn-primary">
                <i v-if="submitting" class="fas fa-spinner fa-spin"></i>
                {{ submitting ? '提交中...' : (showCreateModal ? '创建' : '更新') }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import { ElMessage } from 'element-plus';
import { MachineConfigAPI, type MaintenancePlan, type Machine } from '@/services/api';

// 状态管理
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
  actual_start_time: '',
  actual_end_time: '',
  status: 'PLANNED',
  description: ''
});

// 防抖搜索
let searchTimeout: NodeJS.Timeout;
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
    const params = {
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

// 获取状态文本
const getStatusText = (status: string) => {
  const statusMap = {
    'PLANNED': '计划中',
    'IN_PROGRESS': '执行中',
    'COMPLETED': '已完成',
    'CANCELLED': '已取消'
  };
  return statusMap[status as keyof typeof statusMap] || status;
};

// 格式化日期时间
const formatDateTime = (dateTime: string) => {
  return new Date(dateTime).toLocaleString('zh-CN');
};

// 编辑计划
const editPlan = (plan: MaintenancePlan) => {
  editingPlan.value = plan;
  Object.assign(formData, {
    plan_code: plan.plan_code,
    machine_code: plan.machine_code,
    maintenance_type: plan.maintenance_type,
    planned_start_time: plan.planned_start_time.slice(0, 16), // 转换为datetime-local格式
    planned_end_time: plan.planned_end_time.slice(0, 16),
    actual_start_time: plan.actual_start_time ? plan.actual_start_time.slice(0, 16) : '',
    actual_end_time: plan.actual_end_time ? plan.actual_end_time.slice(0, 16) : '',
    status: plan.status,
    description: plan.description || ''
  });
  showEditModal.value = true;
};

// 删除计划
const deletePlan = async (id: number) => {
  if (!confirm('确定要删除这个维护计划吗？')) {
    return;
  }

  try {
    await MachineConfigAPI.deleteMaintenancePlan(id);
    ElMessage.success('删除成功');
    loadData();
  } catch (error) {
    console.error('删除失败:', error);
    ElMessage.error('删除失败，请稍后重试');
  }
};

// 关闭模态框
const closeModal = () => {
  showCreateModal.value = false;
  showEditModal.value = false;
  editingPlan.value = null;
  resetForm();
};

// 重置表单
const resetForm = () => {
  Object.assign(formData, {
    plan_code: '',
    machine_code: '',
    maintenance_type: '',
    planned_start_time: '',
    planned_end_time: '',
    actual_start_time: '',
    actual_end_time: '',
    status: 'PLANNED',
    description: ''
  });
};

// 提交表单
const submitForm = async () => {
  submitting.value = true;
  try {
    const submitData = { ...formData };
    
    // 转换时间格式
    if (submitData.planned_start_time) {
      submitData.planned_start_time = new Date(submitData.planned_start_time).toISOString();
    }
    if (submitData.planned_end_time) {
      submitData.planned_end_time = new Date(submitData.planned_end_time).toISOString();
    }
    if (submitData.actual_start_time) {
      submitData.actual_start_time = new Date(submitData.actual_start_time).toISOString();
    }
    if (submitData.actual_end_time) {
      submitData.actual_end_time = new Date(submitData.actual_end_time).toISOString();
    }

    if (showCreateModal.value) {
      await MachineConfigAPI.createMaintenancePlan(submitData);
      ElMessage.success('创建成功');
    } else if (showEditModal.value && editingPlan.value) {
      await MachineConfigAPI.updateMaintenancePlan(editingPlan.value.id, submitData);
      ElMessage.success('更新成功');
    }
    closeModal();
    loadData();
  } catch (error) {
    console.error('提交失败:', error);
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

// 初始化
onMounted(() => {
  loadData();
  loadMachines();
});
</script>

<style scoped>
.maintenance-plan-table-container {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.action-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #eee;
  flex-wrap: wrap;
  gap: 16px;
}

.search-filters {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.search-input, .filter-select {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  min-width: 120px;
}

.search-input:focus, .filter-select:focus {
  outline: none;
  border-color: #007bff;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.btn-primary {
  background: #007bff;
  color: white;
}

.btn-primary:hover {
  background: #0056b3;
}

.btn-primary:disabled {
  background: #6c757d;
  cursor: not-allowed;
}

.table-container {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th,
.data-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #eee;
}

.data-table th {
  background: #f8f9fa;
  font-weight: 600;
  color: #495057;
}

.loading-cell,
.empty-cell {
  text-align: center;
  padding: 40px 12px;
  color: #6c757d;
}

.loading-spinner {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.time-range {
  font-size: 12px;
  line-height: 1.4;
}

.time-separator {
  color: #6c757d;
  margin: 2px 0;
}

.no-actual-time {
  color: #6c757d;
  font-style: italic;
}

.status-badge {
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.status-badge.planned {
  background: #e3f2fd;
  color: #1976d2;
}

.status-badge.in_progress {
  background: #fff3cd;
  color: #856404;
}

.status-badge.completed {
  background: #e8f5e8;
  color: #2e7d2e;
}

.status-badge.cancelled {
  background: #f8d7da;
  color: #721c24;
}

.action-buttons {
  display: flex;
  gap: 8px;
}

.btn-action {
  padding: 6px 8px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;
}

.btn-edit {
  background: #28a745;
  color: white;
}

.btn-edit:hover {
  background: #218838;
}

.btn-delete {
  background: #dc3545;
  color: white;
}

.btn-delete:hover {
  background: #c82333;
}

.pagination-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-top: 1px solid #eee;
}

.pagination-info {
  color: #6c757d;
  font-size: 14px;
}

.pagination {
  display: flex;
  gap: 8px;
}

.btn-pagination {
  background: #f8f9fa;
  color: #495057;
  border: 1px solid #dee2e6;
}

.btn-pagination:hover:not(:disabled) {
  background: #e9ecef;
}

.btn-pagination:disabled {
  opacity: 0.5;
  cursor: not-allowed;
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
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #eee;
}

.modal-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.close-btn {
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
  color: #6c757d;
  padding: 4px;
}

.close-btn:hover {
  color: #495057;
}

.modal-body {
  padding: 20px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  font-weight: 500;
  color: #495057;
}

.form-input,
.form-select,
.form-textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  box-sizing: border-box;
  transition: all 0.2s ease;
  background-color: #fff;
}

.form-input:focus,
.form-select:focus,
.form-textarea:focus {
  outline: none;
  border-color: #007bff;
  box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.1);
}

.form-select {
  cursor: pointer;
  background-image: url('data:image/svg+xml;charset=US-ASCII,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 4 5"><path fill="%23666" d="M2 0L0 2h4zm0 5L0 3h4z"/></svg>');
  background-repeat: no-repeat;
  background-position: right 12px center;
  background-size: 12px;
  padding-right: 40px;
  appearance: none;
}

.form-select:hover {
  border-color: #80bdff;
}

.form-textarea {
  resize: vertical;
  font-family: inherit;
}

.form-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 24px;
}

.btn-cancel {
  background: #6c757d;
  color: white;
}

.btn-cancel:hover {
  background: #5a6268;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .action-bar {
    flex-direction: column;
    align-items: stretch;
  }

  .search-filters {
    flex-direction: column;
  }

  .search-input,
  .filter-select {
    min-width: auto;
  }

  .data-table {
    font-size: 12px;
  }

  .data-table th,
  .data-table td {
    padding: 8px 6px;
  }

  .pagination-container {
    flex-direction: column;
    gap: 12px;
  }

  .modal-content {
    width: 95%;
    margin: 20px;
  }

  .form-actions {
    flex-direction: column;
  }
}
</style>
