<template>
  <div class="refresh-button-container">
    <!-- 手动刷新数据按钮 -->
    <button
      @click="handleManualRefresh"
      :class="['refresh-btn', { 'is-loading': isLoading, 'is-success': lastRefreshSuccess }]"
      :disabled="isLoading"
      :title="isLoading ? '正在刷新...' : '手动从 Supabase 拉取最新节点数据'"
    >
      <span class="refresh-icon">{{ refreshIcon }}</span>
      {{ buttonText }}
    </button>

    <!-- 刷新状态提示 -->
    <div v-if="refreshStatus" :class="['refresh-status', lastRefreshSuccess ? 'success' : 'error']">
      {{ refreshStatus }}
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const isLoading = ref(false)
const lastRefreshSuccess = ref(false)
const refreshStatus = ref('')

const buttonText = computed(() => {
  if (isLoading.value) return '正在刷新...'
  if (lastRefreshSuccess.value) return '✅ 已刷新'
  return '🔄 手动刷新'
})

const refreshIcon = computed(() => {
  if (isLoading.value) return '⏳'
  if (lastRefreshSuccess.value) return '✅'
  return '🔄'
})

const handleManualRefresh = async () => {
  if (isLoading.value) return

  isLoading.value = true
  lastRefreshSuccess.value = false
  refreshStatus.value = '正在拉取数据...'

  try {
    // 方法1: 通过前端 API 拉取最新数据fetch(`${VIPER_API_BASE}/
    const response = await fetch(`${VIPER_API_BASE}/nodes?limit=500`)
    
    if (!response.ok) {
      throw new Error(`API 返回 ${response.status}`)
    }

    const data = await response.json()
    
    // ✅ 修复: API 返回的是直接数组，不是 { data: [...] }
    const nodes = Array.isArray(data) ? data : (data.data || [])
    const nodeCount = nodes.length

    console.log('📊 刷新结果:', { nodeCount, nodes })

    if (nodeCount > 0) {
      lastRefreshSuccess.value = true
      refreshStatus.value = `✅ 成功拉取 ${nodeCount} 个节点！(${new Date().toLocaleTimeString()})`
      
      // 触发全局事件，通知其他组件刷新
      window.dispatchEvent(new CustomEvent('nodesRefreshed', { detail: { count: nodeCount } }))
      
      // 重新加载页面以显示新数据
      setTimeout(() => {
        location.reload()
      }, 1500)
    } else {
      lastRefreshSuccess.value = false
      refreshStatus.value = '❌ 未获取到节点数据'
    }
  } catch (error) {
    lastRefreshSuccess.value = false
    refreshStatus.value = `❌ 刷新失败: ${error.message}`
    console.error('刷新错误:', error)
  } finally {
    isLoading.value = false
  }
}
</script>

<style scoped>
.refresh-button-container {
  display: flex;
  flex-direction: column;
  gap: 6px;
  align-items: center;
}

.refresh-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 6px;
  font-weight: 600;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.3s ease;
  white-space: nowrap;
}

.refresh-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 12px rgba(102, 126, 234, 0.4);
}

.refresh-btn:active:not(:disabled) {
  transform: translateY(0);
}

.refresh-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.refresh-btn.is-loading {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  animation: spin 1s linear infinite;
}

.refresh-btn.is-success {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
}

.refresh-icon {
  font-size: 14px;
  display: inline-block;
}

.refresh-status {
  font-size: 11px;
  padding: 4px 8px;
  border-radius: 3px;
  white-space: nowrap;
  min-height: 20px;
  display: flex;
  align-items: center;
}

.refresh-status.success {
  background-color: rgba(76, 175, 80, 0.1);
  color: #4caf50;
}

.refresh-status.error {
  background-color: rgba(244, 67, 54, 0.1);
  color: #f44336;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
