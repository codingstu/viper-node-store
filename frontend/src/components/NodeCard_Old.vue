<template>
  <div class="glass-card group p-4 rounded-xl bg-gradient-to-br from-white/10 to-white/5 backdrop-blur border border-white/20 hover:border-white/40 transition-all duration-300 hover:shadow-lg hover:shadow-purple-500/20">
    <!-- 头部：名称和协议 -->
    <div class="flex justify-between items-start mb-3">
      <div class="flex-1">
        <h3 class="text-sm font-bold text-white truncate group-hover:text-purple-300 transition">
          {{ node.name }}
        </h3>
        <p class="text-xs text-gray-400 mt-0.5">{{ node.protocol.toUpperCase() }}</p>
      </div>
      <div class="text-right ml-2">
        <p class="text-xs text-gray-400">{{ node.country }}</p>
      </div>
    </div>

    <!-- 节点地址 -->
    <div class="mb-3 text-xs">
      <span class="text-gray-400">地址: </span>
      <span class="text-white font-mono">{{ node.host }}:{{ node.port }}</span>
    </div>

    <!-- 速度和延迟指标 -->
    <div class="grid grid-cols-2 gap-2 mb-3">
      <!-- 速度 -->
      <div>
        <div class="flex items-baseline justify-between mb-1">
          <span class="text-xs text-gray-400">速度</span>
          <span :class="['text-xs font-bold', speedColor]">
            {{ node.speed.toFixed(1) }} MB/s
          </span>
        </div>
        <div class="h-1.5 bg-gray-700 rounded-full overflow-hidden">
          <div
            :style="{ width: Math.min((node.speed / 100) * 100, 100) + '%' }"
            :class="['h-full transition-all duration-500', barColor]"
          />
        </div>
      </div>

      <!-- 延迟 -->
      <div>
        <div class="flex items-baseline justify-between mb-1">
          <span class="text-xs text-gray-400">延迟</span>
          <span :class="['text-xs font-bold', latencyColor]">
            {{ node.latency }} ms
          </span>
        </div>
        <div class="h-1.5 bg-gray-700 rounded-full overflow-hidden">
          <div
            :style="{ width: Math.min((Math.max(0, 500 - node.latency) / 500) * 100, 100) + '%' }"
            :class="['h-full transition-all duration-500', latencyBarColor]"
          />
        </div>
      </div>
    </div>

    <!-- 质量评分 -->
    <div class="mb-4 p-2 bg-white/5 rounded-lg">
      <div class="flex items-center justify-between">
        <span class="text-xs text-gray-400">质量评分</span>
        <span :class="['text-sm font-bold', qualityColor]">{{ qualityScore }}/100</span>
      </div>
      <div class="h-1 bg-gray-700 rounded-full overflow-hidden mt-1">
        <div
          :style="{ width: qualityScore + '%' }"
          :class="['h-full transition-all duration-500', qualityBarColor]"
        />
      </div>
    </div>

    <!-- 按钮组 -->
    <div class="grid grid-cols-2 gap-2">
      <!-- 复制链接按钮 -->
      <button
        @click="copyLink"
        :class="[
          'py-1.5 rounded-lg text-xs font-bold transition-all active:scale-[0.98]',
          hasValidLink ? 'bg-white/5 hover:bg-emerald-500/20 text-gray-300 hover:text-emerald-300 border border-white/10 hover:border-emerald-500/30' : 'bg-gray-800/50 text-gray-500 cursor-not-allowed border border-gray-700'
        ]"
        :disabled="!hasValidLink"
        :title="hasValidLink ? '复制节点链接到剪贴板' : '此节点没有可用链接'"
      >
        📋 COPY
      </button>

      <!-- 二维码按钮 -->
      <button
        @click="showQRCode"
        :class="[
          'py-1.5 rounded-lg text-xs font-bold transition-all active:scale-[0.98]',
          hasValidLink ? 'bg-white/5 hover:bg-blue-500/20 text-gray-300 hover:text-blue-300 border border-white/10 hover:border-blue-500/30' : 'bg-gray-800/50 text-gray-500 cursor-not-allowed border border-gray-700'
        ]"
        :disabled="!hasValidLink"
        :title="hasValidLink ? '显示节点二维码' : '此节点没有可用链接'"
      >
        📱 QR CODE
      </button>

      <!-- 精确测速按钮 (占两列) -->
      <button
        @click="showPrecisionTest"
        :class="[
          'col-span-2 py-1.5 rounded-lg text-xs font-bold transition-all active:scale-[0.98]',
          'bg-gradient-to-r from-purple-500/20 to-pink-500/20',
          'hover:from-purple-500/40 hover:to-pink-500/40',
          'text-purple-300 hover:text-purple-200',
          'border border-purple-500/30 hover:border-purple-500/60'
        ]"
        title="开始精确测速"
      >
        ⚡ 精确测速
      </button>
    </div>

    <!-- 最后更新时间 -->
    <p class="text-xs text-gray-500 mt-2 text-center">
      更新: {{ formatTime(node.updated_at) }}
    </p>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  node: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['show-qrcode', 'show-precision-test'])

/**
 * 检查链接是否有效
 */
const hasValidLink = computed(() => {
  if (!props.node.link) return false
  const link = String(props.node.link).trim()
  return link.length > 0 && link !== 'null' && link !== 'undefined' && link !== 'N/A'
})

/**
 * 计算速度显示颜色
 */
const speedColor = computed(() => {
  if (props.node.speed >= 10) return 'text-emerald-400'
  if (props.node.speed >= 5) return 'text-amber-400'
  if (props.node.speed > 0) return 'text-rose-400'
  return 'text-gray-500'
})

const barColor = computed(() => {
  if (props.node.speed >= 10) return 'bg-emerald-500'
  if (props.node.speed >= 5) return 'bg-amber-500'
  if (props.node.speed > 0) return 'bg-rose-500'
  return 'bg-gray-700'
})

/**
 * 计算延迟显示颜色
 */
const latencyColor = computed(() => {
  if (props.node.latency < 100) return 'text-emerald-400'
  if (props.node.latency < 300) return 'text-amber-400'
  if (props.node.latency < 500) return 'text-rose-400'
  return 'text-gray-500'
})

const latencyBarColor = computed(() => {
  if (props.node.latency < 100) return 'bg-emerald-500'
  if (props.node.latency < 300) return 'bg-amber-500'
  if (props.node.latency < 500) return 'bg-rose-500'
  return 'bg-gray-700'
})

/**
 * 计算质量评分
 */
const qualityScore = computed(() => {
  const speedScore = Math.min((props.node.speed / 10) * 50, 50)
  const latencyScore = Math.min((Math.max(0, 500 - props.node.latency) / 500) * 50, 50)
  return Math.round(speedScore + latencyScore)
})

const qualityColor = computed(() => {
  if (qualityScore.value >= 70) return 'text-emerald-400'
  if (qualityScore.value >= 40) return 'text-amber-400'
  return 'text-rose-400'
})

const qualityBarColor = computed(() => {
  if (qualityScore.value >= 70) return 'bg-emerald-500'
  if (qualityScore.value >= 40) return 'bg-amber-500'
  return 'bg-rose-500'
})

/**
 * 格式化时间
 */
function formatTime(dateString) {
  if (!dateString) return '未知'
  try {
    const date = new Date(dateString)
    const now = new Date()
    const diffSeconds = Math.floor((now - date) / 1000)

    if (diffSeconds < 60) return '刚刚'
    if (diffSeconds < 3600) return `${Math.floor(diffSeconds / 60)}分钟前`
    if (diffSeconds < 86400) return `${Math.floor(diffSeconds / 3600)}小时前`
    return `${Math.floor(diffSeconds / 86400)}天前`
  } catch {
    return '未知'
  }
}

/**
 * 复制链接
 */
async function copyLink() {
  if (!hasValidLink.value) {
    console.warn('❌ 链接无效')
    return
  }
  try {
    const link = String(props.node.link).trim()
    // 使用原生 navigator.clipboard API
    await navigator.clipboard.writeText(link)
    console.log('✅ 链接已复制:', link)
    // 显示提示信息
    alert('✅ 链接已复制到剪贴板')
  } catch (err) {
    console.error('❌ 复制失败:', err)
    alert('❌ 复制失败，请手动复制')
  }
}

/**
 * 显示二维码
 */
function showQRCode() {
  if (!hasValidLink.value) {
    console.warn('❌ 链接无效，无法生成二维码')
    alert('❌ 此节点没有可用链接，无法生成二维码')
    return
  }
  emit('show-qrcode')
}

/**
 * 显示精确测速
 */
function showPrecisionTest() {
  emit('show-precision-test')
}
</script>

<style scoped>
.glass-card {
  transition: all 0.3s ease;
}

.glass-card:hover {
  transform: translateY(-2px);
}
</style>
