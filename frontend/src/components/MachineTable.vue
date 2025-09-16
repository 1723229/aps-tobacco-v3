<template>
  <div class="machine-table-container">
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
          v-model="searchFilters.machine_type" 
          class="filter-select"
          @change="loadData"
        >
          <option value="">所有类型</option>
          <option value="PACKING">卷包机</option>
          <option value="FEEDING">喂丝机</option>
        </select>
        <select 
          v-model="searchFilters.status" 
          class="filter-select"
          @change="loadData"
        >
          <option value="">所有状态</option>
          <option value="ACTIVE">活跃</option>
          <option value="INACTIVE">停用</option>
          <option value="MAINTENANCE">维护中</option>
        </select>
      </div>
      <button @click="showCreateModal = true" class="btn btn-primary">
        <i class="fas fa-plus"></i>
        新增机台
      </button>
    </div>

    <!-- 数据表格 -->
    <div class="table-container">
      <table class="data-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>机台代码</th>
            <th>机台名称</th>
            <th>机台类型</th>
            <th>设备型号</th>
            <th>生产线</th>
            <th>状态</th>
            <th>创建时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="9" class="loading-cell">
              <div class="loading-spinner">
                <i class="fas fa-spinner fa-spin"></i>
                加载中...
              </div>
            </td>
          </tr>
          <tr v-else-if="machines.length === 0">
            <td colspan="9" class="empty-cell">暂无数据</td>
          </tr>
          <tr v-else v-for="machine in machines" :key="machine.id">
            <td>{{ machine.id }}</td>
            <td>{{ machine.machine_code }}</td>
            <td>{{ machine.machine_name }}</td>
            <td>
              <span :class="['type-badge', machine.machine_type.toLowerCase()]">
                {{ machine.machine_type === 'PACKING' ? '卷包机' : '喂丝机' }}
              </span>
            </td>
            <td>{{ machine.equipment_type || '-' }}</td>
            <td>{{ machine.production_line || '-' }}</td>
            <td>
              <span :class="['status-badge', machine.status.toLowerCase()]">
                {{ getStatusText(machine.status) }}
              </span>
            </td>
            <td>{{ formatDateTime(machine.created_time) }}</td>
            <td>
              <div class="action-buttons">
                <button @click="editMachine(machine)" class="btn btn-small btn-secondary">编辑</button>
                <button @click="deleteMachine(machine.id)" class="btn btn-small btn-danger">删除</button>
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
          <h3>{{ showCreateModal ? '新增机台' : '编辑机台' }}</h3>
          <button @click="closeModal" class="close-btn">
            <i class="fas fa-times"></i>
          </button>
        </div>
        <div class="modal-body">
          <form @submit.prevent="submitForm">
            <div class="form-group">
              <label>机台代码 *</label>
              <input 
                v-model="formData.machine_code" 
                type="text" 
                required 
                class="form-input"
                placeholder="请输入机台代码"
              />
            </div>
            <div class="form-group">
              <label>机台名称 *</label>
              <input 
                v-model="formData.machine_name" 
                type="text" 
                required 
                class="form-input"
                placeholder="请输入机台名称"
              />
            </div>
            <div class="form-group">
              <label>机台类型 *</label>
              <select v-model="formData.machine_type" required class="form-select">
                <option value="">请选择机台类型</option>
                <option value="PACKING">卷包机</option>
                <option value="FEEDING">喂丝机</option>
              </select>
            </div>
            <div class="form-group">
              <label>设备型号</label>
              <input 
                v-model="formData.equipment_type" 
                type="text" 
                class="form-input"
                placeholder="请输入设备型号"
              />
            </div>
            <div class="form-group">
              <label>生产线</label>
              <input 
                v-model="formData.production_line" 
                type="text" 
                class="form-input"
                placeholder="请输入生产线"
              />
            </div>
            <div class="form-group">
              <label>状态 *</label>
              <select v-model="formData.status" required class="form-select">
                <option value="">请选择状态</option>
                <option value="ACTIVE">活跃</option>
                <option value="INACTIVE">停用</option>
                <option value="MAINTENANCE">维护中</option>
              </select>
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
import { ElMessage, ElMessageBox } from 'element-plus';
import { MachineConfigAPI, type Machine, type MachineRequest } from '@/services/api';

// 状态管理
const loading = ref(false);
const submitting = ref(false);
const machines = ref<Machine[]>([]);
const showCreateModal = ref(false);
const showEditModal = ref(false);
const editingMachine = ref<Machine | null>(null);

// 搜索过滤器
const searchFilters = reactive({
  machine_code: '',
  machine_type: '',
  status: ''
});

// 分页信息
const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0
});

// 表单数据
const formData = reactive<MachineRequest>({
  machine_code: '',
  machine_name: '',
  machine_type: 'PACKING',
  equipment_type: '',
  production_line: '',
  status: 'ACTIVE'
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

    const response = await MachineConfigAPI.getMachines(params);
    machines.value = response.data.items;
    pagination.total = response.data.total;
  } catch (error) {
    console.error('加载机台数据失败:', error);
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
    'ACTIVE': '活跃',
    'INACTIVE': '停用',
    'MAINTENANCE': '维护中'
  };
  return statusMap[status as keyof typeof statusMap] || status;
};

// 格式化日期时间
const formatDateTime = (dateTime: string) => {
  return new Date(dateTime).toLocaleString('zh-CN');
};

// 编辑机台
const editMachine = (machine: Machine) => {
  editingMachine.value = machine;
  Object.assign(formData, {
    machine_code: machine.machine_code,
    machine_name: machine.machine_name,
    machine_type: machine.machine_type,
    equipment_type: machine.equipment_type || '',
    production_line: machine.production_line || '',
    status: machine.status
  });
  showEditModal.value = true;
};

// 删除机台
const deleteMachine = async (id: number) => {
  try {
    await ElMessageBox.confirm(
      '确定要删除这台机台吗？',
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
    await MachineConfigAPI.deleteMachine(id);
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
  editingMachine.value = null;
  resetForm();
};

// 重置表单
const resetForm = () => {
  Object.assign(formData, {
    machine_code: '',
    machine_name: '',
    machine_type: 'PACKING',
    equipment_type: '',
    production_line: '',
    status: 'ACTIVE'
  });
};

// 提交表单
const submitForm = async () => {
  submitting.value = true;
  try {
    if (showCreateModal.value) {
      await MachineConfigAPI.createMachine(formData);
      ElMessage.success('创建成功');
    } else if (showEditModal.value && editingMachine.value) {
      await MachineConfigAPI.updateMachine(editingMachine.value.id, formData);
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

// 初始化
onMounted(() => {
  loadData();
});
</script>

<style scoped>
.machine-table-container {
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

.type-badge,
.status-badge {
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.type-badge.packing {
  background: #e3f2fd;
  color: #1976d2;
}

.type-badge.feeding {
  background: #f3e5f5;
  color: #7b1fa2;
}

.status-badge.active {
  background: #e8f5e8;
  color: #2e7d2e;
}

.status-badge.inactive {
  background: #fff3cd;
  color: #856404;
}

.status-badge.maintenance {
  background: #f8d7da;
  color: #721c24;
}

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
  max-width: 500px;
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
.form-select {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  box-sizing: border-box;
}

.form-input:focus,
.form-select:focus {
  outline: none;
  border-color: #007bff;
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
