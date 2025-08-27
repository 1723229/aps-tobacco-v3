<template>
  <div class="loading-wrapper" :class="{ 'is-fullscreen': fullscreen }">
    <div class="loading-content">
      <el-icon class="loading-icon" :size="iconSize">
        <Loading />
      </el-icon>
      <div class="loading-text">{{ text }}</div>
      <div v-if="subText" class="loading-sub-text">{{ subText }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Loading } from '@element-plus/icons-vue'

interface Props {
  text?: string
  subText?: string
  fullscreen?: boolean
  size?: 'small' | 'default' | 'large'
}

const props = withDefaults(defineProps<Props>(), {
  text: '加载中...',
  subText: '',
  fullscreen: false,
  size: 'default'
})

const iconSize = computed(() => {
  switch (props.size) {
    case 'small':
      return 24
    case 'large':
      return 48
    case 'default':
    default:
      return 32
  }
})
</script>

<style scoped>
.loading-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  min-height: 200px;
}

.loading-wrapper.is-fullscreen {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(255, 255, 255, 0.9);
  z-index: 2000;
  min-height: 100vh;
}

.loading-content {
  text-align: center;
}

.loading-icon {
  color: #409eff;
  animation: rotate 1s linear infinite;
  margin-bottom: 12px;
}

.loading-text {
  font-size: 16px;
  color: #303133;
  margin-bottom: 8px;
}

.loading-sub-text {
  font-size: 14px;
  color: #909399;
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>