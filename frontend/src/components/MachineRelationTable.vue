<template>
  <div class="machine-relation-table-container">
    <!-- 操作栏 -->
    <div class="action-bar">
      <div class="search-filters">
        <input
          v-model="searchFilters.feeder_code"
          type="text"
          placeholder="喂丝机代码"
          class="search-input"
          @input="debounceSearch"
        />
        <input
          v-model="searchFilters.maker_code"
          type="text"
          placeholder="卷包机代码"
          class="search-input"
          @input="debounceSearch"
        />
      </div>
      <button @click="showCreateModal = true" class="btn btn-primary">
        <i class="fas fa-plus"></i>
        新增关系
      </button>
    </div>

    <!-- 数据表格 -->
    <div class="table-container">
      <table class="data-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>喂丝机代码</th>
            <th>卷包机代码</th>
            <th>关系类型</th>
            <th>优先级</th>
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
          <tr v-else-if="relations.length === 0">
            <td colspan="7" class="empty-cell">暂无数据</td>
          </tr>
          <tr v-else v-for="relation in relations" :key="relation.id">
            <td>{{ relation.id }}</td>
            <td>{{ relation.feeder_code }}</td>
            <td>{{ relation.maker_code }}</td>
            <td>{{ relation.relation_type }}</td>
            <td>
              <span class="priority-badge">{{ relation.priority }}</span>
            </td>
            <td>{{ formatDateTime(relation.created_time) }}</td>
            <td>
              <div class="action-buttons">
                <button @click="editRelation(relation)" class="btn-action btn-edit">
                  <i class="fas fa-edit"></i>
                </button>
                <button @click="deleteRelation(relation.id)" class="btn-action btn-delete">
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
          <h3>{{ showCreateModal ? '新增机台关系' : '编辑机台关系' }}</h3>
          <button @click="closeModal" class="close-btn">
            <i class="fas fa-times"></i>
          </button>
        </div>
        <div class="modal-body">
          <form @submit.prevent="submitForm">
            <div class="form-group">
              <label>喂丝机代码 *</label>
              <input 
                v-model="formData.feeder_code" 
                type="text" 
                required 
                class="form-input"
                placeholder="请输入喂丝机代码"
              />
            </div>
            <div class="form-group">
              <label>卷包机代码 *</label>
              <input 
                v-model="formData.maker_code" 
                type="text" 
                required 
                class="form-input"
                placeholder="请输入卷包机代码"
              />
            </div>
            <div class="form-group">
              <label>关系类型 *</label>
              <input 
                v-model="formData.relation_type" 
                type="text" 
                required 
                class="form-input"
                placeholder="请输入关系类型"
              />
            </div>
            <div class="form-group">
              <label>优先级 *</label>
              <input 
                v-model.number="formData.priority" 
                type="number" 
                required 
                min="1"
                class="form-input"
                placeholder="请输入优先级"
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
import { MachineConfigAPI, type MachineRelation } from '@/services/api';

// 状态管理
const loading = ref(false);
const submitting = ref(false);
const relations = ref<MachineRelation[]>([]);
const showCreateModal = ref(false);
const showEditModal = ref(false);
const editingRelation = ref<MachineRelation | null>(null);

// 搜索过滤器
const searchFilters = reactive({
  feeder_code: '',
  maker_code: ''
});

// 分页信息
const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0
});

// 表单数据
const formData = reactive({
  feeder_code: '',
  maker_code: '',
  relation_type: '',
  priority: 1
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

    const response = await MachineConfigAPI.getMachineRelations(params);
    relations.value = response.data.items;
    pagination.total = response.data.total;
  } catch (error) {
    console.error('加载机台关系数据失败:', error);
    alert('加载数据失败，请稍后重试');
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

// 编辑关系
const editRelation = (relation: MachineRelation) => {
  editingRelation.value = relation;
  Object.assign(formData, {
    feeder_code: relation.feeder_code,
    maker_code: relation.maker_code,
    relation_type: relation.relation_type,
    priority: relation.priority
  });
  showEditModal.value = true;
};

// 删除关系
const deleteRelation = async (id: number) => {
  if (!confirm('确定要删除这个机台关系吗？')) {
    return;
  }

  try {
    await MachineConfigAPI.deleteMachineRelation(id);
    alert('删除成功');
    loadData();
  } catch (error) {
    console.error('删除失败:', error);
    alert('删除失败，请稍后重试');
  }
};

// 关闭模态框
const closeModal = () => {
  showCreateModal.value = false;
  showEditModal.value = false;
  editingRelation.value = null;
  resetForm();
};

// 重置表单
const resetForm = () => {
  Object.assign(formData, {
    feeder_code: '',
    maker_code: '',
    relation_type: '',
    priority: 1
  });
};

// 提交表单
const submitForm = async () => {
  submitting.value = true;
  try {
    if (showCreateModal.value) {
      await MachineConfigAPI.createMachineRelation(formData);
      alert('创建成功');
    } else if (showEditModal.value && editingRelation.value) {
      await MachineConfigAPI.updateMachineRelation(editingRelation.value.id, formData);
      alert('更新成功');
    }
    closeModal();
    loadData();
  } catch (error) {
    console.error('提交失败:', error);
    alert('操作失败，请稍后重试');
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
.machine-relation-table-container {
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

.priority-badge {
  background: #e3f2fd;
  color: #1976d2;
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

.form-input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  box-sizing: border-box;
}

.form-input:focus {
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
