<template>
  <div class="shift-config-table-container">
    <!-- 操作栏 -->
    <div class="action-bar">
      <div class="search-filters">
        <input
          v-model="searchFilters.shift_name"
          type="text"
          placeholder="班次名称"
          class="search-input"
          @input="debounceSearch"
        />
        <select 
          v-model="searchFilters.is_active" 
          class="filter-select"
          @change="loadData"
        >
          <option value="">所有状态</option>
          <option :value="true">激活</option>
          <option :value="false">停用</option>
        </select>
      </div>
      <button @click="showCreateModal = true" class="btn btn-primary">
        <i class="fas fa-plus"></i>
        新增班次配置
      </button>
    </div>

    <!-- 数据表格 -->
    <div class="table-container">
      <table class="data-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>班次名称</th>
            <th>班次代码</th>
            <th>开始时间</th>
            <th>结束时间</th>
            <th>时长</th>
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
          <tr v-else-if="configs.length === 0">
            <td colspan="9" class="empty-cell">暂无数据</td>
          </tr>
          <tr v-else v-for="config in configs" :key="config.id">
            <td>{{ config.id }}</td>
            <td>{{ config.shift_name }}</td>
            <td>{{ config.shift_code }}</td>
            <td>{{ config.start_time }}</td>
            <td>{{ config.end_time }}</td>
            <td>{{ calculateDuration(config.start_time, config.end_time) }}</td>
            <td>
              <span :class="['status-badge', config.is_active ? 'active' : 'inactive']">
                {{ config.is_active ? '激活' : '停用' }}
              </span>
            </td>
            <td>{{ formatDateTime(config.created_time) }}</td>
            <td>
              <div class="action-buttons">
                <button @click="editConfig(config)" class="btn btn-small btn-secondary">编辑</button>
                <button @click="deleteConfig(config.id)" class="btn btn-small btn-danger">删除</button>
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
          <h3>{{ showCreateModal ? '新增班次配置' : '编辑班次配置' }}</h3>
          <button @click="closeModal" class="close-btn">
            <i class="fas fa-times"></i>
          </button>
        </div>
        <div class="modal-body">
          <form @submit.prevent="submitForm">
            <div class="form-group">
              <label>班次名称 *</label>
              <select 
                v-model="formData.shift_name" 
                required 
                class="form-select"
                @change="updateShiftCode"
              >
                <option value="">请选择班次名称</option>
                <option value="早班">早班</option>
                <option value="中班">中班</option>
                <option value="晚班">晚班</option>
                <option value="夜班">夜班</option>
                <option value="全天班">全天班</option>
              </select>
            </div>
            <div class="form-group">
              <label>班次代码 *</label>
              <input 
                v-model="formData.shift_code" 
                type="text" 
                required 
                class="form-input readonly-input"
                readonly
                placeholder="系统自动生成"
              />
            </div>
            <div class="form-group">
              <label>开始时间 *</label>
              <input 
                v-model="formData.start_time" 
                type="time" 
                required 
                class="form-input"
              />
            </div>
            <div class="form-group">
              <label>结束时间 *</label>
              <input 
                v-model="formData.end_time" 
                type="time" 
                required 
                class="form-input"
              />
            </div>
            <div class="form-group">
              <label>状态 *</label>
              <select v-model="formData.is_active" required class="form-select">
                <option :value="true">激活</option>
                <option :value="false">停用</option>
              </select>
            </div>
            <div class="form-group" v-if="formData.start_time && formData.end_time">
              <label>班次时长</label>
              <div class="duration-display">
                {{ calculateDuration(formData.start_time, formData.end_time) }}
              </div>
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
import { MachineConfigAPI, type ShiftConfig } from '@/services/api';

// 状态管理
const loading = ref(false);
const submitting = ref(false);
const configs = ref<ShiftConfig[]>([]);
const showCreateModal = ref(false);
const showEditModal = ref(false);
const editingConfig = ref<ShiftConfig | null>(null);

// 搜索过滤器
const searchFilters = reactive({
  shift_name: '',
  is_active: ''
});

// 分页信息
const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0
});

// 表单数据
const formData = reactive({
  shift_name: '',
  shift_code: '',
  start_time: '',
  end_time: '',
  is_active: true
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

    const response = await MachineConfigAPI.getShiftConfigs(params);
    configs.value = response.data.items;
    pagination.total = response.data.total;
  } catch (error) {
    console.error('加载班次配置数据失败:', error);
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

// 更新班次代码
const updateShiftCode = () => {
  const shiftCodeMap: { [key: string]: string } = {
    '早班': 'MORNING',
    '中班': 'AFTERNOON', 
    '晚班': 'EVENING',
    '夜班': 'NIGHT',
    '全天班': 'FULLDAY'
  };
  
  if (formData.shift_name && shiftCodeMap[formData.shift_name]) {
    formData.shift_code = shiftCodeMap[formData.shift_name];
  }
};

// 计算时长
const calculateDuration = (startTime: string, endTime: string): string => {
  if (!startTime || !endTime) return '-';
  
  const start = new Date(`2000-01-01 ${startTime}`);
  const end = new Date(`2000-01-01 ${endTime}`);
  
  // 处理跨天情况
  if (end < start) {
    end.setDate(end.getDate() + 1);
  }
  
  const diffMs = end.getTime() - start.getTime();
  const hours = Math.floor(diffMs / (1000 * 60 * 60));
  const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
  
  return `${hours}小时${minutes}分钟`;
};

// 格式化日期时间
const formatDateTime = (dateTime: string) => {
  return new Date(dateTime).toLocaleString('zh-CN');
};

// 编辑配置
const editConfig = (config: ShiftConfig) => {
  editingConfig.value = config;
  Object.assign(formData, {
    shift_name: config.shift_name,
    shift_code: config.shift_code,
    start_time: config.start_time,
    end_time: config.end_time,
    is_active: config.is_active
  });
  showEditModal.value = true;
};

// 删除配置
const deleteConfig = async (id: number) => {
  try {
    await ElMessageBox.confirm(
      '确定要删除这个班次配置吗？',
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
    await MachineConfigAPI.deleteShiftConfig(id);
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
  editingConfig.value = null;
  resetForm();
};

// 重置表单
const resetForm = () => {
  Object.assign(formData, {
    shift_name: '',
    shift_code: '',
    start_time: '',
    end_time: '',
    is_active: true
  });
};

// 提交表单
const submitForm = async () => {
  submitting.value = true;
  try {
    if (showCreateModal.value) {
      await MachineConfigAPI.createShiftConfig(formData);
      ElMessage.success('创建成功');
    } else if (showEditModal.value && editingConfig.value) {
      await MachineConfigAPI.updateShiftConfig(editingConfig.value.id, formData);
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
.shift-config-table-container {
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

.status-badge {
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.status-badge.active {
  background: #e8f5e8;
  color: #2e7d2e;
}

.status-badge.inactive {
  background: #f8d7da;
  color: #721c24;
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
  border-radius: 6px;
  font-size: 14px;
  box-sizing: border-box;
  transition: all 0.2s ease;
  background-color: #fff;
}

.form-input:focus,
.form-select:focus {
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

.readonly-input {
  background-color: #f8f9fa !important;
  color: #6c757d !important;
  cursor: not-allowed;
}

.duration-display {
  padding: 10px 12px;
  background: #f8f9fa;
  border-radius: 4px;
  color: #495057;
  font-weight: 500;
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
