<template>
  <div class="machine-config-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1>机台配置管理</h1>
      <p class="page-description">
        管理机台基础信息、机台关系、速度配置、维护计划、班次配置和工作日历
      </p>
    </div>

    <!-- 标签页导航 -->
    <div class="tabs-container">
      <div class="tabs">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          :class="['tab-button', { active: activeTab === tab.key }]"
          @click="activeTab = tab.key"
        >
          <i :class="tab.icon"></i>
          <span>{{ tab.label }}</span>
        </button>
      </div>
    </div>

    <!-- 标签页内容 -->
    <div class="tab-content">
      <!-- 机台基础信息 -->
      <div v-if="activeTab === 'machines'" class="tab-panel">
        <MachineTable />
      </div>

      <!-- 机台关系 -->
      <div v-if="activeTab === 'relations'" class="tab-panel">
        <MachineRelationTable />
      </div>

      <!-- 机台速度 -->
      <div v-if="activeTab === 'speeds'" class="tab-panel">
        <MachineSpeedTable />
      </div>

      <!-- 维护计划 -->
      <div v-if="activeTab === 'maintenance'" class="tab-panel">
        <MaintenancePlanTable />
      </div>

      <!-- 班次配置 -->
      <div v-if="activeTab === 'shifts'" class="tab-panel">
        <ShiftConfigTable />
      </div>

      <!-- 工作日历 -->
      <div v-if="activeTab === 'calendar'" class="tab-panel">
        <WorkCalendarTable />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import MachineTable from '@/components/MachineTable.vue';
import MachineRelationTable from '@/components/MachineRelationTable.vue';
import MachineSpeedTable from '@/components/MachineSpeedTable.vue';
import MaintenancePlanTable from '@/components/MaintenancePlanTable.vue';
import ShiftConfigTable from '@/components/ShiftConfigTable.vue';
import WorkCalendarTable from '@/components/WorkCalendarTable.vue';

// 标签页配置
const tabs = [
  {
    key: 'machines',
    label: '机台信息',
    icon: 'fas fa-cogs'
  },
  {
    key: 'relations',
    label: '机台关系',
    icon: 'fas fa-project-diagram'
  },
  {
    key: 'speeds',
    label: '机台速度',
    icon: 'fas fa-tachometer-alt'
  },
  {
    key: 'maintenance',
    label: '维护计划',
    icon: 'fas fa-tools'
  },
  {
    key: 'shifts',
    label: '班次配置',
    icon: 'fas fa-clock'
  },
  {
    key: 'calendar',
    label: '工作日历',
    icon: 'fas fa-calendar-alt'
  }
];

// 当前激活的标签页
const activeTab = ref('machines');
</script>

<style scoped>
.machine-config-page {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
}

.page-header {
  margin-bottom: 30px;
}

.page-header h1 {
  font-size: 28px;
  font-weight: 600;
  color: #2c3e50;
  margin: 0 0 8px 0;
}

.page-description {
  color: #7f8c8d;
  font-size: 16px;
  margin: 0;
}

.tabs-container {
  border-bottom: 1px solid #e1e8ed;
  margin-bottom: 24px;
}

.tabs {
  display: flex;
  gap: 0;
  overflow-x: auto;
  padding-bottom: 0;
}

.tab-button {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px 24px;
  border: none;
  background: none;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  color: #6c757d;
  border-bottom: 3px solid transparent;
  transition: all 0.2s ease;
  white-space: nowrap;
  position: relative;
}

.tab-button:hover {
  color: #495057;
  background-color: #f8f9fa;
}

.tab-button.active {
  color: #007bff;
  border-bottom-color: #007bff;
  background-color: #f8f9ff;
}

.tab-button i {
  font-size: 16px;
  width: 16px;
  text-align: center;
}

.tab-content {
  min-height: 500px;
}

.tab-panel {
  animation: fadeIn 0.3s ease-in-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 响应式设计 */
@media (max-width: 768px) {
  .machine-config-page {
    padding: 16px;
  }
  
  .page-header h1 {
    font-size: 24px;
  }
  
  .page-description {
    font-size: 14px;
  }
  
  .tab-button {
    padding: 12px 16px;
    font-size: 13px;
  }
  
  .tab-button span {
    display: none;
  }
  
  .tab-button i {
    font-size: 18px;
  }
}
</style>
