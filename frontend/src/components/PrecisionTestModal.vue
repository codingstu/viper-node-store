<template>
  <div v-if="show" class="fixed inset-0 z-40 flex items-center justify-center bg-black/60 backdrop-blur-sm">
    <div class="relative bg-gradient-to-br from-purple-900 to-gray-900 rounded-2xl p-8 max-w-lg w-full mx-4 border border-purple-500/50">
      <!-- 关闭按钮 -->
      <button
        @click="close"
        class="absolute top-4 right-4 text-gray-400 hover:text-white transition"
      >
        ✕
      </button>

      <!-- 标题 -->
      <div class="flex items-center gap-2 mb-6">
        <span class="text-2xl">⚡</span>
        <h2 class="text-2xl font-bold text-white">精确测速</h2>
      </div>

      <!-- 节点信息 -->
      <div v-if="!testRunning && !testCompleted" class="bg-white/5 p-4 rounded-lg mb-6 border border-white/10">
        <p class="text-sm text-gray-300">正在测速节点：</p>
        <p class="text-lg font-bold text-white mt-1">{{ node.name }}</p>
        <p class="text-xs text-gray-400 mt-1">{{ node.host }}:{{ node.port }}</p>
      </div>

      <!-- 文件大小选择 (初始状态) -->
      <div v-if="!testRunning && !testCompleted" class="space-y-4 mb-6">
        <p class="text-sm text-gray-300">选择测试文件大小</p>
        <div class="grid grid-cols-3 gap-2">
          <button
            v-for="size in fileSizes"
            :key="size"
            @click="selectedFileSize = size"
            :class="[
              'py-2 rounded-lg font-bold text-sm transition',
              selectedFileSize === size
                ? 'bg-purple-500 text-white'
                : 'bg-white/5 text-gray-300 hover:bg-white/10'
            ]"
          >
            {{ size }} MB
          </button>
        </div>
      </div>

      <!-- 测速进行中 -->
      <div v-if="testRunning" class="space-y-4">
        <p class="text-sm text-gray-300 text-center">测速中...</p>
        <div class="bg-gray-800 rounded-lg p-4">
          <div class="h-1.5 bg-gray-700 rounded-full overflow-hidden">
            <div
              :style="{ width: progress + '%' }"
              class="h-full bg-gradient-to-r from-purple-500 to-pink-500 transition-all duration-300"
            />
          </div>
          <p class="text-center text-xs text-gray-400 mt-2">{{ progress }}%</p>
        </div>
      </div>

      <!-- 测速结果 -->
      <div v-if="testCompleted && result" class="space-y-4">
        <!-- 状态标识 -->
        <div class="flex items-center justify-center">
          <div v-if="result.status === 'success'" class="text-center">
            <p class="text-4xl">✅</p>
            <p class="text-lg font-bold text-emerald-400 mt-2">精确测速完成</p>
          </div>
          <div v-else class="text-center">
            <p class="text-4xl">⚠️</p>
            <p class="text-lg font-bold text-rose-400 mt-2">测速遇到问题</p>
          </div>
        </div>

        <!-- 结果详情 -->
        <div class="grid grid-cols-2 gap-3">
          <div class="bg-white/5 p-3 rounded-lg border border-white/10">
            <p class="text-xs text-gray-400">下载速度</p>
            <p class="text-2xl font-bold text-purple-400 mt-1">{{ result.speed_mbps }}</p>
            <p class="text-xs text-gray-500">MB/s</p>
          </div>
          <div class="bg-white/5 p-3 rounded-lg border border-white/10">
            <p class="text-xs text-gray-400">耗时</p>
            <p class="text-2xl font-bold text-blue-400 mt-1">{{ result.download_time_seconds }}</p>
            <p class="text-xs text-gray-500">秒</p>
          </div>
          <div class="bg-white/5 p-3 rounded-lg border border-white/10 col-span-2">
            <p class="text-xs text-gray-400">流量消耗</p>
            <p class="text-2xl font-bold text-cyan-400 mt-1">{{ result.traffic_consumed_mb }}</p>
            <p class="text-xs text-gray-500">MB</p>
          </div>
        </div>

        <!-- 错误信息 -->
        <div v-if="result.message" class="bg-white/5 p-3 rounded-lg border border-white/10">
          <p class="text-xs text-gray-400">详细信息</p>
          <p class="text-sm text-gray-300 mt-1">{{ result.message }}</p>
        </div>
      </div>

      <!-- 底部按钮 -->
      <div class="flex gap-3 mt-6">
        <button
          v-if="!testRunning && !testCompleted"
          @click="startTest"
          class="flex-1 py-3 bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 text-white font-bold rounded-lg transition active:scale-95"
          :disabled="!node"
        >
          开始测速
        </button>
        <button
          v-if="testCompleted"
          @click="startTest"
          class="flex-1 py-3 bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 text-white font-bold rounded-lg transition active:scale-95"
        >
          重新测速
        </button>
        <button
          @click="close"
          class="flex-1 py-3 bg-gray-800 hover:bg-gray-700 text-gray-300 font-bold rounded-lg transition"
        >
          {{ testRunning ? '测速中...' : '关闭' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useNodeStore } from '../stores/nodeStore'

const props = defineProps({
  node: {
    type: Object,
    required: true
  },
  show: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['close', 'test-complete'])

const nodeStore = useNodeStore()

const fileSizes = [10, 50, 100]
const selectedFileSize = ref(50)
const testRunning = ref(false)
const testCompleted = ref(false)
const progress = ref(0)
const result = ref(null)
let progressInterval = null

/**
 * 启动进度条模拟
 */
function startProgressSimulation() {
  progress.value = 0
  progressInterval = setInterval(() => {
    if (progress.value < 95) {
      const increment = Math.max(0.5, (95 - progress.value) / 20)
      progress.value = Math.min(95, progress.value + increment)
    }
  }, 150)
}

/**
 * 停止进度条模拟
 */
function stopProgressSimulation() {
  if (progressInterval) {
    clearInterval(progressInterval)
  }
  progress.value = 100
}

/**
 * 开始测速
 */
async function startTest() {
  if (!props.node) return

  testRunning.value = true
  testCompleted.value = false
  result.value = null

  startProgressSimulation()

  try {
    console.log(`⚡ 开始精确测速 | 节点: ${props.node.name} | 文件大小: ${selectedFileSize.value}MB`)

    // 调用API
    const testResult = await nodeStore.precisionTest(props.node, selectedFileSize.value)

    stopProgressSimulation()
    await new Promise(resolve => setTimeout(resolve, 300))

    result.value = testResult
    testCompleted.value = true

    console.log('测速结果:', testResult)

    // 如果测速成功，更新节点速度
    if (testResult.status === 'success' || testResult.status === 'partial_success') {
      nodeStore.updateNodeSpeed(props.node.id, testResult.speed_mbps)
      console.log(`✅ 已更新节点速度: ${testResult.speed_mbps} MB/s`)
    }

    // 触发完成事件
    emit('test-complete', testResult)
  } catch (error) {
    console.error('❌ 测速异常:', error)
    stopProgressSimulation()
    result.value = {
      status: 'error',
      speed_mbps: 0,
      message: `测速异常: ${error.message}`
    }
    testCompleted.value = true
  } finally {
    testRunning.value = false
  }
}

/**
 * 关闭弹窗
 */
function close() {
  testRunning.value = false
  testCompleted.value = false
  progress.value = 0
  result.value = null
  if (progressInterval) clearInterval(progressInterval)
  emit('close')
}
</script>

<style scoped>
button:disabled {
  @apply opacity-50 cursor-not-allowed;
}
</style>
