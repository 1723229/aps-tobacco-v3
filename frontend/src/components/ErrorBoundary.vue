<template>
  <div class="error-boundary">
    <el-result 
      icon="error" 
      title="页面出现错误"
      :sub-title="errorMessage"
    >
      <template #extra>
        <el-space>
          <el-button type="primary" @click="handleRetry">
            <el-icon><Refresh /></el-icon>
            重试
          </el-button>
          <el-button @click="goHome">
            <el-icon><House /></el-icon>
            返回首页
          </el-button>
        </el-space>
      </template>
    </el-result>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Refresh, House } from '@element-plus/icons-vue'

interface Props {
  error?: Error | null
  errorMessage?: string
}

const props = withDefaults(defineProps<Props>(), {
  error: null,
  errorMessage: '发生了未知错误，请重试或联系管理员'
})

const emit = defineEmits<{
  retry: []
}>()

const router = useRouter()

const handleRetry = () => {
  emit('retry')
}

const goHome = () => {
  router.push('/')
}
</script>

<style scoped>
.error-boundary {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  padding: 40px;
}
</style>