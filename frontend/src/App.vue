<template>
  <div id="app">
    <el-container>
      <!-- 顶部导航栏 -->
      <el-header class="app-header">
        <div class="header-content">
          <div class="header-left">
            <div class="logo-section" @click="goHome">
              <el-icon class="logo-icon"><DataAnalysis /></el-icon>
              <span class="logo-text">APS 系统</span>
            </div>
          </div>

          <div class="header-center">
            <el-menu
              :default-active="activeMenuIndex"
              mode="horizontal"
              background-color="transparent"
              text-color="#ffffff"
              active-text-color="#ffd04b"
              :ellipsis="false"
              @select="handleMenuSelect"
            >
              <el-menu-item index="/">
                <el-icon><House /></el-icon>
                <span>首页</span>
              </el-menu-item>
              <el-sub-menu index="production">
                <template #title>
                  <el-icon><Setting /></el-icon>
                  <span>排产作业</span>
                </template>
                <el-menu-item index="/decade-plan/entry">
                  <el-icon><UploadFilled /></el-icon>
                  <span>卷包旬计划录入</span>
                </el-menu-item>
                <el-menu-item index="/scheduling">
                  <el-icon><Operation /></el-icon>
                  <span>智能排产管理</span>
                </el-menu-item>
                <el-menu-item index="/machine-config">
                  <el-icon><Setting /></el-icon>
                  <span>机台配置管理</span>
                </el-menu-item>
              </el-sub-menu>
            </el-menu>
          </div>

          <div class="header-right">
            <el-space>
              <el-badge :value="notificationCount" :hidden="notificationCount === 0">
                <el-button circle size="small" @click="showNotifications">
                  <el-icon><Bell /></el-icon>
                </el-button>
              </el-badge>

              <el-dropdown @command="handleUserAction">
                <el-button circle size="small">
                  <el-icon><User /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="profile">个人中心</el-dropdown-item>
                    <el-dropdown-item command="settings">系统设置</el-dropdown-item>
                    <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </el-space>
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
  Clock,
  InfoFilled,
  Bell,
  User,
  Setting,
  Operation,
  Monitor
} from '@element-plus/icons-vue'
import { formatDateTime } from '@/utils'

const router = useRouter()
const route = useRoute()

// 响应式数据
const notificationDrawer = ref(false)
const notifications = ref([
  {
    id: 1,
    title: '文件解析完成',
    content: '批次 BATCH_20241216_001 文件解析成功，共处理156条记录',
    time: '2024-12-16 14:31:05'
  },
  {
    id: 2,
    title: '系统更新',
    content: '系统已更新至 v1.0.0，新增了数据导出功能',
    time: '2024-12-16 09:00:00'
  }
])

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
  if (path.startsWith('/about')) {
    return '/about'
  }
  return '/'
})

const notificationCount = computed(() => notifications.value.length)

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

const showNotifications = () => {
  notificationDrawer.value = true
}

const handleUserAction = (command: string) => {
  switch (command) {
    case 'profile':
      ElMessage.info('个人中心功能开发中...')
      break
    case 'settings':
      ElMessage.info('系统设置功能开发中...')
      break
    case 'logout':
      ElMessage.info('退出登录功能开发中...')
      break
  }
}
</script>

<style scoped>
#app {
  min-height: 100vh;
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', '微软雅黑', Arial, sans-serif;
}

.app-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 0;
  height: 60px !important;
  line-height: 60px;
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 100%;
  padding: 0 20px;
}

.header-left {
  display: flex;
  align-items: center;
}

.logo-section {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  color: white;
  font-size: 18px;
  font-weight: 600;
  transition: opacity 0.3s ease;
}

.logo-section:hover {
  opacity: 0.8;
}

.logo-icon {
  font-size: 24px;
}

.header-center {
  flex: 1;
  display: flex;
  justify-content: center;
}

.header-right {
  display: flex;
  align-items: center;
}

.header-right .el-button {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.2);
  color: white;
}

.header-right .el-button:hover {
  background: rgba(255, 255, 255, 0.2);
  border-color: rgba(255, 255, 255, 0.3);
}

.app-main {
  background-color: #f5f5f5;
  min-height: calc(100vh - 120px);
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

/* Element Plus 样式覆盖 */
:deep(.el-menu--horizontal) {
  border-bottom: none !important;
}

:deep(.el-menu--horizontal .el-menu-item) {
  border-bottom: none !important;
  color: rgba(255, 255, 255, 0.8) !important;
}

:deep(.el-menu--horizontal .el-menu-item:hover) {
  background-color: rgba(255, 255, 255, 0.1) !important;
  color: white !important;
}

:deep(.el-menu--horizontal .el-menu-item.is-active) {
  border-bottom: 2px solid #ffd04b !important;
  color: #ffd04b !important;
}

:deep(.el-sub-menu .el-sub-menu__title) {
  border-bottom: none !important;
  color: rgba(255, 255, 255, 0.8) !important;
}

:deep(.el-sub-menu .el-sub-menu__title:hover) {
  background-color: rgba(255, 255, 255, 0.1) !important;
  color: white !important;
}

:deep(.el-sub-menu.is-active .el-sub-menu__title) {
  color: #ffd04b !important;
}

/* 子菜单下拉面板样式 - 使用更强的选择器优先级和动态类名 */
:deep(.el-popper),
:deep(.el-popper.el-menu--popup),
:deep(.el-menu--popup),
:deep(.el-popper[data-popper-placement]),
:deep(.el-popper[data-popper-placement^="bottom"]),
:deep(.el-menu.el-menu--popup),
:deep([role="menu"]),
:deep([class*="popper"]) {
  background: #ffffff !important;
  border: 1px solid #e8eaed !important;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12) !important;
  border-radius: 12px !important;
  padding: 8px !important;
  margin-top: 8px !important;
  min-width: 180px !important;
  z-index: 9999 !important;
}

:deep(.el-popper .el-menu),
:deep(.el-popper.el-menu--popup .el-menu),
:deep(.el-menu--popup .el-menu),
:deep(.el-menu.el-menu--popup),
:deep([role="menu"] ul),
:deep([class*="popper"] ul) {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}

/* 子菜单项样式 - 使用超高优先级和通用选择器 */
:deep(.el-popper .el-menu-item),
:deep(.el-popper.el-menu--popup .el-menu-item),
:deep(.el-menu--popup .el-menu-item),
:deep(.el-popper[data-popper-placement] .el-menu-item),
:deep(.el-popper[data-popper-placement^="bottom"] .el-menu-item),
:deep(.el-menu.el-menu--popup .el-menu-item),
:deep(.el-menu .el-menu-item),
:deep([role="menu"] li),
:deep([role="menuitem"]),
:deep([class*="popper"] li),
:deep(li[role="menuitem"]) {
  color: #2c3e50 !important;
  border-bottom: none !important;
  margin: 2px 0 !important;
  border-radius: 8px !important;
  padding: 12px 16px !important;
  transition: all 0.3s ease !important;
  background: transparent !important;
  font-weight: 500 !important;
  display: flex !important;
  align-items: center !important;
  gap: 10px !important;
  height: auto !important;
  line-height: 1.5 !important;
  font-size: 14px !important;
  opacity: 1 !important;
  visibility: visible !important;
  text-align: left !important;
  white-space: nowrap !important;
}

/* 子菜单项悬停效果 */
:deep(.el-popper .el-menu-item:hover),
:deep(.el-popper.el-menu--popup .el-menu-item:hover),
:deep(.el-menu--popup .el-menu-item:hover),
:deep(.el-popper[data-popper-placement] .el-menu-item:hover),
:deep(.el-popper[data-popper-placement^="bottom"] .el-menu-item:hover),
:deep(.el-menu.el-menu--popup .el-menu-item:hover),
:deep(.el-menu .el-menu-item:hover),
:deep([role="menu"] li:hover),
:deep([role="menuitem"]:hover),
:deep([class*="popper"] li:hover),
:deep(li[role="menuitem"]:hover) {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
  color: white !important;
  transform: translateY(-1px) !important;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3) !important;
}

/* 子菜单项激活状态 */
:deep(.el-popper .el-menu-item.is-active),
:deep(.el-popper.el-menu--popup .el-menu-item.is-active),
:deep(.el-menu--popup .el-menu-item.is-active),
:deep(.el-popper[data-popper-placement] .el-menu-item.is-active),
:deep(.el-popper[data-popper-placement^="bottom"] .el-menu-item.is-active),
:deep(.el-menu.el-menu--popup .el-menu-item.is-active),
:deep(.el-menu .el-menu-item.is-active),
:deep([role="menu"] li.is-active),
:deep([role="menuitem"].is-active),
:deep([class*="popper"] li.is-active),
:deep(li[role="menuitem"].is-active) {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
  color: white !important;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3) !important;
}

/* 子菜单图标样式 */
:deep(.el-popper .el-menu-item .el-icon),
:deep(.el-popper.el-menu--popup .el-menu-item .el-icon),
:deep(.el-menu--popup .el-menu-item .el-icon),
:deep(.el-popper[data-popper-placement] .el-menu-item .el-icon),
:deep(.el-popper[data-popper-placement^="bottom"] .el-menu-item .el-icon),
:deep(.el-menu.el-menu--popup .el-menu-item .el-icon),
:deep(.el-menu .el-menu-item .el-icon),
:deep([role="menu"] li .el-icon),
:deep([role="menuitem"] .el-icon),
:deep([class*="popper"] li .el-icon),
:deep(li[role="menuitem"] .el-icon) {
  font-size: 16px !important;
  width: 16px !important;
  margin-right: 0 !important;
  color: inherit !important;
}

/* 隐藏箭头 */
:deep(.el-popper .el-popper__arrow),
:deep(.el-popper[data-popper-placement] .el-popper__arrow),
:deep(.el-popper[data-popper-placement^="bottom"] .el-popper__arrow) {
  display: none !important;
}

/* 添加顶部装饰箭头 */
:deep(.el-popper::before),
:deep(.el-popper.el-menu--popup::before),
:deep(.el-menu--popup::before),
:deep(.el-popper[data-popper-placement]::before),
:deep(.el-popper[data-popper-placement^="bottom"]::before),
:deep(.el-menu.el-menu--popup::before),
:deep([role="menu"]::before),
:deep([class*="popper"]::before) {
  content: '';
  position: absolute;
  top: -8px;
  left: 50%;
  transform: translateX(-50%);
  width: 0;
  height: 0;
  border-left: 8px solid transparent;
  border-right: 8px solid transparent;
  border-bottom: 8px solid #ffffff;
  filter: drop-shadow(0 -2px 4px rgba(0, 0, 0, 0.1));
  z-index: 1;
}

/* 强制确保所有Element Plus子菜单组件可见 - 使用通配符和属性选择器 */
:deep([class*="el-menu"]) {
  color: #2c3e50 !important;
}

:deep([class*="el-menu"]:not(.el-menu--horizontal) .el-menu-item) {
  color: #2c3e50 !important;
  background: transparent !important;
}

:deep([class*="el-menu"]:not(.el-menu--horizontal) .el-menu-item:hover) {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
  color: white !important;
}

/* 针对可能的动态生成类名的全局覆盖 */
:deep(*[class*="menu"]) {
  color: #2c3e50 !important;
}

:deep(*[class*="menu"]:hover) {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
  color: white !important;
}

/* 使用最高优先级的内联样式覆盖 */
.el-menu .el-menu-item {
  color: #2c3e50 !important;
  background: transparent !important;
}

.el-menu .el-menu-item:hover {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
  color: white !important;
}
:deep(.el-badge__content){
  top: 10px !important;
}
</style>
