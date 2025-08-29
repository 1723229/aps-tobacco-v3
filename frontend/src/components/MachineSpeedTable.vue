<template>
  <div class="machine-speed-table-container">
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
        <input
          v-model="searchFilters.article_nr"
          type="text"
          placeholder="物料编号"
          class="search-input"
          @input="debounceSearch"
        />
      </div>
      <button @click="showCreateModal = true" class="btn btn-primary">
        <i class="fas fa-plus"></i>
        新增速度配置
      </button>
    </div>

    <!-- 数据表格 -->
    <div class="table-container">
      <table class="data-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>机台代码</th>
            <th>物料编号</th>
            <th>生产速度（箱/小时）</th>
            <th>效率率(%)</th>
            <th>创建时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="7" class="loading-cell">
              <div class="loading-spinner">
                <i class="fas fa-spinner fa-spin"></i>
                加载中...
              </div>
            </td>
          </tr>
          <tr v-else-if="speeds.length === 0">
            <td colspan="7" class="empty-cell">暂无数据</td>
          </tr>
          <tr v-else v-for="speed in speeds" :key="speed.id">
            <td>{{ speed.id }}</td>
            <td>{{ speed.machine_code }}</td>
            <td>{{ speed.article_nr }}</td>
            <td>{{ speed.speed }} 箱/小时</td>
            <td>
              <span class="efficiency-badge">{{ speed.efficiency_rate }}%</span>
            </td>
            <td>{{ formatDateTime(speed.created_time) }}</td>
            <td>
              <div class="action-buttons">
                <button @click="editSpeed(speed)" class="btn-action btn-edit">
                  <i class="fas fa-edit"></i>
                </button>
                <button @click="deleteSpeed(speed.id)" class="btn-action btn-delete">
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
          <h3>{{ showCreateModal ? '新增机台速度' : '编辑机台速度' }}</h3>
          <button @click="closeModal" class="close-btn">
            <i class="fas fa-times"></i>
          </button>
        </div>
        <div class="modal-body">
          <form @submit.prevent="submitForm">
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
              <label>物料编号 *</label>
              <select 
                v-model="formData.article_nr" 
                required 
                class="form-select"
              >
                <option value="">请选择物料编号</option>
                <option value="*">* (通用)</option>
                <option value="A01">A01</option>
                <option value="A02">A02</option>
                <option value="B01">B01</option>
                <option value="B02">B02</option>
                <option value="C01">C01</option>
                <option value="D01">D01</option>
              </select>
            </div>
            <div class="form-group">
              <label>生产速度 (箱/小时) *</label>
              <input 
                v-model.number="formData.speed" 
                type="number" 
                required 
                min="1"
                step="0.01"
                class="form-input"
                placeholder="请输入生产速度"
              />
            </div>
            <div class="form-group">
              <label>效率率 (%) *</label>
              <input 
                v-model.number="formData.efficiency_rate" 
                type="number" 
                required 
                min="0"
                max="100"
                step="0.01"
                class="form-input"
                placeholder="请输入效率率百分比"
              />
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
import { MachineConfigAPI, type MachineSpeed, type Machine } from '@/services/api';

// 状态管理
const loading = ref(false);
const submitting = ref(false);
const speeds = ref<MachineSpeed[]>([]);
const machines = ref<Machine[]>([]);
const showCreateModal = ref(false);
const showEditModal = ref(false);
const editingSpeed = ref<MachineSpeed | null>(null);

// 搜索过滤器
const searchFilters = reactive({
  machine_code: '',
  article_nr: ''
});

// 分页信息
const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0
});

// 表单数据
const formData = reactive({
  machine_code: '',
  article_nr: '',
  speed: 0,
  efficiency_rate: 0
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
    const params = {
      ...searchFilters,
      page: pagination.page,
      page_size: pagination.page_size
    };
    
    // 移除空值
    Object.keys(params).forEach(key => {
      if ((params as any)[key] === '') {
        delete (params as any)[key];
      }
    });

    const response = await MachineConfigAPI.getMachineSpeeds(params);
    speeds.value = response.data.items;
    pagination.total = response.data.total;
  } catch (error) {
    console.error('加载机台速度数据失败:', error);
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

// 格式化日期时间
const formatDateTime = (dateTime: string) => {
  return new Date(dateTime).toLocaleString('zh-CN');
};

// 编辑速度
const editSpeed = (speed: MachineSpeed) => {
  editingSpeed.value = speed;
  Object.assign(formData, {
    machine_code: speed.machine_code,
    article_nr: speed.article_nr,
    speed: speed.speed,
    efficiency_rate: speed.efficiency_rate
  });
  showEditModal.value = true;
};

// 删除速度
const deleteSpeed = async (id: number) => {
  if (!confirm('确定要删除这个机台速度配置吗？')) {
    return;
  }

  try {
    await MachineConfigAPI.deleteMachineSpeed(id);
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
  editingSpeed.value = null;
  resetForm();
};

// 重置表单
const resetForm = () => {
  Object.assign(formData, {
    machine_code: '',
    article_nr: '',
    speed: 0,
    efficiency_rate: 0
  });
};

// 提交表单
const submitForm = async () => {
  submitting.value = true;
  try {
    if (showCreateModal.value) {
      await MachineConfigAPI.createMachineSpeed(formData);
      ElMessage.success('创建成功');
    } else if (showEditModal.value && editingSpeed.value) {
      await MachineConfigAPI.updateMachineSpeed(editingSpeed.value.id, formData);
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
.machine-speed-table-container {
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

.search-input {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  min-width: 140px;
}

.search-input:focus {
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

.efficiency-badge {
  background: #e8f5e8;
  color: #2e7d2e;
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
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

  .search-input {
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
