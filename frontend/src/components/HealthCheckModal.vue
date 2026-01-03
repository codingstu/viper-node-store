<template>
  <div v-if="show" class="fixed inset-0 z-40 flex items-center justify-center bg-black/60 backdrop-blur-sm">
    <div class="relative bg-gradient-to-br from-purple-900 to-gray-900 rounded-2xl p-8 max-w-2xl w-full mx-4 border border-purple-500/50 max-h-[80vh] overflow-hidden flex flex-col">
      <!-- 关闭按钮 -->
      <button
        @click="close"
        :disabled="isRunning"
        class="absolute top-4 right-4 text-gray-400 hover:text-white transition disabled:opacity-50 disabled:cursor-not-allowed"
      >
        ✕
      </button>

      <!-- 标题 -->
      <div class="flex items-center gap-2 mb-6">
        <span class="text-2xl">🏥</span>
        <h2 class="text-2xl font-bold text-white">全局健康检测</h2>
      </div>

      <!-- 初始状态 -->
      <div v-if="!isRunning && !isCompleted" class="space-y-4">
        <div class="bg-white/5 p-4 rounded-lg border border-white/10">
          <p class="text-sm text-gray-300">将检测所有节点的连通性</p>
          <p class="text-xs text-gray-400 mt-2">• 轻量级 TCP + HTTP 检测</p>
          <p class="text-xs text-gray-400">• 不可用节点会重试 2 次</p>
          <p class="text-xs text-gray-400">• 离线节点将被标记为 "offline"</p>
        </div>

        <div class="bg-amber-500/10 p-3 rounded-lg border border-amber-500/30">
          <p class="text-xs text-amber-300">⚠️ 检测过程可能需要几分钟，请耐心等待</p>
        </div>
      </div>

      <!-- 检测进行中 -->
      <div v-if="isRunning" class="space-y-4">
        <div class="bg-gray-800 rounded-lg p-4">
          <div class="flex justify-between text-xs text-gray-400 mb-2">
            <span>检测进度</span>
            <span>{{ progress.checked }} / {{ progress.total }}</span>
          </div>
          <div class="h-2 bg-gray-700 rounded-full overflow-hidden">
            <div
              :style="{ width: progressPercent + '%' }"
              class="h-full bg-gradient-to-r from-purple-500 to-pink-500 transition-all duration-300"
            />
          </div>
        </div>

        <div class="text-center">
          <div class="inline-flex items-center gap-2 text-sm text-gray-300">
            <span class="animate-spin">⟳</span>
            <span>{{ currentStatus }}</span>
          </div>
        </div>

        <!-- 实时统计 -->
        <div class="grid grid-cols-3 gap-3">
          <div class="bg-emerald-500/10 p-3 rounded-lg border border-emerald-500/20 text-center">
            <p class="text-2xl font-bold text-emerald-400">{{ progress.online }}</p>
            <p class="text-xs text-gray-400">在线</p>
          </div>
          <div class="bg-amber-500/10 p-3 rounded-lg border border-amber-500/20 text-center">
            <p class="text-2xl font-bold text-amber-400">{{ progress.suspect }}</p>
            <p class="text-xs text-gray-400">可疑</p>
          </div>
          <div class="bg-rose-500/10 p-3 rounded-lg border border-rose-500/20 text-center">
            <p class="text-2xl font-bold text-rose-400">{{ progress.offline }}</p>
            <p class="text-xs text-gray-400">离线</p>
          </div>
        </div>
      </div>

      <!-- 检测完成 -->
      <div v-if="isCompleted && result" class="space-y-4 flex-1 overflow-hidden flex flex-col">
        <!-- 状态标识 -->
        <div class="flex items-center justify-center">
          <div class="text-center">
            <p class="text-4xl">✅</p>
            <p class="text-lg font-bold text-emerald-400 mt-2">健康检测完成</p>
          </div>
        </div>

        <!-- 结果统计 -->
        <div class="grid grid-cols-4 gap-3">
          <div class="bg-white/5 p-3 rounded-lg border border-white/10 text-center">
            <p class="text-2xl font-bold text-purple-400">{{ result.total }}</p>
            <p class="text-xs text-gray-400">总节点</p>
          </div>
          <div class="bg-emerald-500/10 p-3 rounded-lg border border-emerald-500/20 text-center">
            <p class="text-2xl font-bold text-emerald-400">{{ result.online }}</p>
            <p class="text-xs text-gray-400">在线</p>
          </div>
          <div class="bg-amber-500/10 p-3 rounded-lg border border-amber-500/20 text-center">
            <p class="text-2xl font-bold text-amber-400">{{ result.suspect }}</p>
            <p class="text-xs text-gray-400">可疑</p>
          </div>
          <div class="bg-rose-500/10 p-3 rounded-lg border border-rose-500/20 text-center">
            <p class="text-2xl font-bold text-rose-400">{{ result.offline }}</p>
            <p class="text-xs text-gray-400">离线</p>
          </div>
        </div>

        <!-- 问题节点列表 -->
        <div v-if="problemNodes.length > 0" class="flex-1 overflow-hidden flex flex-col">
          <p class="text-sm text-gray-300 mb-2">问题节点 ({{ problemNodes.length }})</p>
          <div class="flex-1 overflow-y-auto space-y-2 pr-2">
            <div
              v-for="node in problemNodes"
              :key="node.id"
              :class="[
                'p-2 rounded-lg text-xs flex justify-between items-center',
                node.status === 'offline' ? 'bg-rose-500/10 border border-rose-500/20' : 'bg-amber-500/10 border border-amber-500/20'
              ]"
            >
              <div>
                <p class="text-white font-medium truncate max-w-xs">{{ node.name }}</p>
                <p class="text-gray-400">{{ node.host }}:{{ node.port }}</p>
              </div>
              <span
                :class="[
                  'px-2 py-0.5 rounded text-xs font-bold',
                  node.status === 'offline' ? 'bg-rose-500/30 text-rose-300' : 'bg-amber-500/30 text-amber-300'
                ]"
              >
                {{ node.status === 'offline' ? '离线' : '可疑' }}
              </span>
            </div>
          </div>
        </div>

        <!-- 无问题节点 -->
        <div v-else class="text-center py-4">
          <p class="text-emerald-400">🎉 所有节点都正常运行！</p>
        </div>
      </div>

      <!-- 底部按钮 -->
      <div class="flex gap-3 mt-6">
        <button
          v-if="!isRunning && !isCompleted"
          @click="startHealthCheck"
          class="flex-1 py-3 rounded-lg font-bold bg-gradient-to-r from-purple-500 to-pink-500 text-white hover:opacity-90 transition"
        >
          🏥 开始检测
        </button>

        <button
          v-if="isCompleted"
          @click="reset"
          class="flex-1 py-3 rounded-lg font-bold bg-white/10 text-gray-300 hover:bg-white/20 transition"
        >
          🔄 重新检测
        </button>

        <button
          @click="close"
          :disabled="isRunning"
          class="flex-1 py-3 rounded-lg font-bold bg-white/10 text-gray-300 hover:bg-white/20 transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {{ isCompleted ? '关闭' : '取消' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { healthCheckApi } from '../services/api'
import { useNodeStore } from '../stores/nodeStore'

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['close', 'complete'])

const nodeStore = useNodeStore()

// 状态
const isRunning = ref(false)
const isCompleted = ref(false)
const currentStatus = ref('准备中...')
const progress = ref({
  total: 0,
  checked: 0,
  online: 0,
  suspect: 0,
  offline: 0
})
const result = ref(null)
const problemNodes = ref([])

// 计算属性
const progressPercent = computed(() => {
  if (progress.value.total === 0) return 0
  return Math.round((progress.value.checked / progress.value.total) * 100)
})

// 关闭弹窗
function close() {
  if (isRunning.value) return
  emit('close')
}

// 重置状态
function reset() {
  isRunning.value = false
  isCompleted.value = false
  currentStatus.value = '准备中...'
  progress.value = { total: 0, checked: 0, online: 0, suspect: 0, offline: 0 }
  result.value = null
  problemNodes.value = []
}

// 开始健康检测
async function startHealthCheck() {
  isRunning.value = true
  isCompleted.value = false
  currentStatus.value = '正在获取节点列表...'

  try {
    currentStatus.value = '正在发起健康检测...'

    // 调用后端 API 进行批量检测
    const response = await healthCheckApi.checkAll()

    if (response.status === "success" && response.data) {
      const data = response.data
      
      // 处理结果
      result.value = {
        total: data.total || 0,
        online: data.online || 0,
        suspect: data.suspect || 0,
        offline: data.offline || 0
      }

      // 更新进度
      progress.value = {
        total: result.value.total,
        checked: result.value.total,
        online: result.value.online,
        suspect: result.value.suspect,
        offline: result.value.offline
      }

      // 获取问题节点列表
      if (data.problem_nodes) {
        problemNodes.value = data.problem_nodes
      }

      currentStatus.value = '正在刷新节点列表...'
      
      // 刷新节点列表以获取最新状态
      await nodeStore.refreshNodes()
      
      currentStatus.value = '✅ 检测完成'
      
      emit('complete', result.value)
    } else {
      currentStatus.value = `检测失败: ${response.message || '未知错误'}`
    }
  } catch (error) {
    console.error('健康检测失败:', error)
    currentStatus.value = `检测失败: ${error.message}`
  } finally {
    isRunning.value = false
    isCompleted.value = true
  }
}

// 当弹窗打开时重置状态
watch(() => props.show, (newVal) => {
  if (newVal) {
    reset()
  }
})
</script>
