<template>
  <div id="app">
    <el-container>
      <!-- 顶部导航栏 -->
      <el-header class="app-header">
        <div class="header-content">
          <div class="header-left">
            <div class="logo-section" @click="goHome">
              <div class="logo-container">
                <el-icon class="logo-icon"><DataAnalysis /></el-icon>
              </div>
              <div class="logo-text-group">
                <span class="logo-title">APS系统</span>
                <span class="logo-subtitle">烟草生产计划</span>
              </div>
            </div>
          </div>

          <div class="header-center">
            <nav class="modern-nav">
              <div class="nav-item" :class="{ active: activeMenuIndex === '/' }" @click="handleMenuSelect('/')">
                <div class="nav-icon">
                  <el-icon><House /></el-icon>
                </div>
                <span class="nav-text">首页</span>
              </div>
              
              <div class="nav-item" :class="{ active: activeMenuIndex === '/machine-config' }" @click="handleMenuSelect('/machine-config')">
                <div class="nav-icon">
                  <el-icon><Setting /></el-icon>
                </div>
                <span class="nav-text">机台配置</span>
              </div>
              
              <div class="nav-dropdown" :class="{ active: activeMenuIndex.includes('/decade-plan') || activeMenuIndex.includes('/scheduling') }">
                <div class="nav-item dropdown-trigger">
                  <div class="nav-icon">
                    <el-icon><Operation /></el-icon>
                  </div>
                  <span class="nav-text">排产作业</span>
                  <el-icon class="dropdown-arrow"><ArrowDown /></el-icon>
                </div>
                <div class="dropdown-menu">
                  <div class="dropdown-item" @click="handleMenuSelect('/decade-plan/entry')">
                    <el-icon><UploadFilled /></el-icon>
                    <span>卷包旬计划录入</span>
                  </div>
                  <div class="dropdown-item" @click="handleMenuSelect('/scheduling')">
                    <el-icon><TrendCharts /></el-icon>
                    <span>智能排产管理</span>
                  </div>
                </div>
              </div>
            </nav>
          </div>

          <div class="header-right">
            <div class="header-actions">
              <div class="action-item notification" @click="notificationDrawer = true">
                <el-icon><Bell /></el-icon>
                <span class="notification-badge" v-if="notifications.length > 0">{{ notifications.length }}</span>
              </div>
              <div class="user-section">
                <div class="user-avatar">
                  <el-icon><User /></el-icon>
                </div>
                <span class="user-name">管理员</span>
              </div>
            </div>
          </div>
        </div>
      </el-header>

      <!-- 主体内容 -->
      <el-main class="app-main">
        <RouterView />
      </el-main>

      <!-- 底部信息 -->
      <el-footer class="app-footer">
        <div class="footer-content">
          <div class="footer-left">
            <span>© 2024 APS 烟草生产计划系统. All rights reserved.</span>
          </div>
          <div class="footer-right">
            <span>Version 1.0.0</span>
          </div>
        </div>
      </el-footer>
    </el-container>

    <!-- 通知抽屉 -->
    <el-drawer
      v-model="notificationDrawer"
      title="系统通知"
      direction="rtl"
      size="400px"
    >
      <div class="notification-content">
        <el-empty v-if="notifications.length === 0" description="暂无新通知" />
        <div v-else>
          <div
            v-for="notification in notifications"
            :key="notification.id"
            class="notification-item"
          >
            <div class="notification-header">
              <span class="notification-title">{{ notification.title }}</span>
              <span class="notification-time">{{ formatDateTime(notification.time, 'datetime') }}</span>
            </div>
            <div class="notification-content">{{ notification.content }}</div>
          </div>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  DataAnalysis,
  House,
  UploadFilled,
  Setting,
  Operation,
  ArrowDown,
  Bell,
  User,
  TrendCharts
} from '@element-plus/icons-vue'
import { formatDateTime } from '@/utils'

const router = useRouter()
const route = useRoute()

// 定义通知类型
interface Notification {
  id: string
  title: string
  content: string
  time: string
}

// 响应式数据
const notificationDrawer = ref(false)
const notifications = ref<Notification[]>([])

// 计算属性
const activeMenuIndex = computed(() => {
  const path = route.path
  if (path.startsWith('/decade-plan/entry')) {
    return '/decade-plan/entry'
  }
  if (path === '/scheduling') {
    return '/scheduling'
  }
  if (path.startsWith('/scheduling/history')) {
    return '/scheduling/history'
  }
  if (path.startsWith('/scheduling/task')) {
    return '/scheduling/history'
  }
  if (path.startsWith('/gantt-chart')) {
    return '/gantt-chart'
  }
  if (path.startsWith('/machine-config')) {
    return '/machine-config'
  }
  return '/'
})

// 方法
const goHome = () => {
  router.push('/')
}

const handleMenuSelect = (index: string) => {
  if (index.startsWith('/')) {
    router.push(index)
  } else {
    // 处理其他菜单项
    ElMessage.info(`${index} 功能开发中...`)
  }
}
</script>

<style scoped>
#app {
  min-height: 100vh;
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', '微软雅黑', Arial, sans-serif;
}

/* 现代化导航栏样式 */
.app-header {
  background: #ffffff;
  padding: 0;
  height: 72px !important;
  line-height: normal;
  border-bottom: 1px solid #e8eaed;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  position: relative;
  z-index: 1000;
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 100%;
  padding: 0 32px;
  max-width: 1400px;
  margin: 0 auto;
}

/* Logo区域样式 */
.header-left {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.logo-section {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  padding: 8px 12px;
  border-radius: 12px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.logo-section:hover {
  background: rgba(59, 130, 246, 0.06);
  transform: translateY(-1px);
}

.logo-container {
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

.logo-icon {
  font-size: 24px;
  color: white;
}

.logo-text-group {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.logo-title {
  font-size: 20px;
  font-weight: 700;
  color: #1f2937;
  line-height: 1;
}

.logo-subtitle {
  font-size: 12px;
  font-weight: 500;
  color: #6b7280;
  line-height: 1;
}

/* 导航中心区域 */
.header-center {
  flex: 1;
  display: flex;
  justify-content: center;
  max-width: 600px;
  margin: 0 auto;
}

.modern-nav {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #f8fafc;
  padding: 6px;
  border-radius: 16px;
  border: 1px solid #e2e8f0;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  font-weight: 500;
  color: #64748b;
  min-width: 110px;
  justify-content: center;
}

.nav-item:hover {
  background: #ffffff;
  color: #3b82f6;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
}

.nav-item.active {
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  color: white;
  box-shadow: 0 6px 20px rgba(59, 130, 246, 0.4);
}

.nav-item.active:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(59, 130, 246, 0.5);
}

.nav-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
}

.nav-text {
  font-size: 14px;
  white-space: nowrap;
}

/* 下拉菜单样式 */
.nav-dropdown {
  position: relative;
}

.nav-dropdown.active .nav-item {
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  color: white;
  box-shadow: 0 6px 20px rgba(59, 130, 246, 0.4);
}

.dropdown-trigger {
  position: relative;
}

.dropdown-arrow {
  font-size: 12px;
  margin-left: 4px;
  transition: transform 0.3s ease;
}

.nav-dropdown:hover .dropdown-arrow {
  transform: rotate(180deg);
}

.dropdown-menu {
  position: absolute;
  top: calc(100% + 8px);
  left: 50%;
  transform: translateX(-50%);
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);
  padding: 8px;
  min-width: 200px;
  opacity: 0;
  visibility: hidden;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  z-index: 1000;
}

.nav-dropdown:hover .dropdown-menu {
  opacity: 1;
  visibility: visible;
  transform: translateX(-50%) translateY(0);
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  color: #374151;
  font-weight: 500;
}

.dropdown-item:hover {
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  color: white;
  transform: translateX(4px);
}

/* 右侧操作区域 */
.header-right {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.action-item {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  color: #6b7280;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}

.action-item:hover {
  background: #3b82f6;
  color: white;
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(59, 130, 246, 0.3);
}

.notification-badge {
  position: absolute;
  top: -2px;
  right: -2px;
  background: #ef4444;
  color: white;
  font-size: 10px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 10px;
  min-width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.user-section {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 16px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}

.user-section:hover {
  background: #ffffff;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transform: translateY(-1px);
}

.user-avatar {
  width: 36px;
  height: 36px;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 16px;
}

.user-name {
  font-size: 14px;
  font-weight: 600;
  color: #374151;
}

.app-main {
  background-color: #f8fafc;
  min-height: calc(100vh - 132px);
  padding: 0;
}

.app-footer {
  background-color: #303133;
  color: #909399;
  height: 60px !important;
  line-height: 60px;
  padding: 0;
}

.footer-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 100%;
  padding: 0 20px;
  font-size: 14px;
}

.notification-content {
  padding: 20px;
}

.notification-item {
  padding: 16px;
  border-bottom: 1px solid #ebeef5;
  margin-bottom: 12px;
}

.notification-item:last-child {
  border-bottom: none;
  margin-bottom: 0;
}

.notification-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.notification-title {
  font-weight: 500;
  color: #303133;
}

.notification-time {
  font-size: 12px;
  color: #909399;
}

.notification-content {
  color: #606266;
  font-size: 14px;
  line-height: 1.5;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .header-content {
    padding: 0 16px;
  }
  
  .logo-container {
    width: 40px;
    height: 40px;
  }
  
  .logo-title {
    font-size: 16px;
  }
  
  .logo-subtitle {
    font-size: 10px;
  }
  
  .modern-nav {
    gap: 4px;
    padding: 4px;
  }
  
  .nav-item {
    padding: 8px 12px;
    min-width: 80px;
  }
  
  .nav-text {
    font-size: 12px;
  }
  
  .header-actions {
    gap: 8px;
  }
  
  .user-name {
    display: none;
  }
  
  .action-item {
    width: 36px;
    height: 36px;
  }
  
  .user-avatar {
    width: 32px;
    height: 32px;
  }
}
</style>
