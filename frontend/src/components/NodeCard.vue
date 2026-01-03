<template>
  <div :class="[
    'glass-card group p-4 rounded-xl bg-gradient-to-br backdrop-blur border transition-all duration-300 hover:shadow-lg',
    nodeStatusClass
  ]">
    <!-- 显示模式：正常卡片或 QR 码卡片 -->
    <div v-if="!showingQRCode">
      <!-- 头部：名称和协议 + 状态徽章 -->
      <div class="flex justify-between items-start mb-3">
        <div class="flex-1">
          <div class="flex items-center gap-2">
            <h3 class="text-sm font-bold text-white truncate group-hover:text-purple-300 transition">
              {{ node.name }}
            </h3>
            <!-- 状态徽章 -->
            <span
              v-if="node.status === 'offline'"
              class="px-1.5 py-0.5 rounded text-[10px] font-bold bg-rose-500/30 text-rose-300 border border-rose-500/50"
            >
              离线
            </span>
            <span
              v-else-if="node.status === 'suspect'"
              class="px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-500/30 text-amber-300 border border-amber-500/50"
            >
              可疑
            </span>
          </div>
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
          @click="toggleQRCode"
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
          @click="emit('show-precision-test')"
          class="col-span-2 py-1.5 rounded-lg text-xs font-bold bg-white/5 hover:bg-orange-500/20 text-gray-300 hover:text-orange-300 border border-white/10 hover:border-orange-500/30 transition-all active:scale-[0.98]"
          title="进行精确测速"
        >
          ⚡ 精确测速
        </button>
      </div>
    </div>

    <!-- QR 码显示模式 -->
    <div v-else class="flex flex-col items-center gap-3 py-4">
      <div class="text-center">
        <p class="text-xs text-gray-400 mb-2">{{ node.name }}</p>
        <div v-if="qrCodeGenerated" class="bg-white p-2 rounded-lg inline-block">
          <img :src="qrCodeData" :alt="node.name" class="w-32 h-32" />
        </div>
        <div v-else class="w-32 h-32 bg-gray-700/50 rounded-lg flex items-center justify-center">
          <p class="text-xs text-gray-400">生成中...</p>
        </div>
      </div>

      <!-- QR 码下方的按钮 -->
      <div class="grid grid-cols-2 gap-2 w-full">
        <!-- 关闭 QR 码 -->
        <button
          @click="toggleQRCode"
          class="py-1.5 rounded-lg text-xs font-bold bg-white/5 hover:bg-gray-500/20 text-gray-300 hover:text-gray-300 border border-white/10 transition-all"
        >
          ✕ 关闭
        </button>

        <!-- 复制链接按钮（从 QR 码页面也能复制） -->
        <button
          @click="copyLink"
          class="py-1.5 rounded-lg text-xs font-bold bg-white/5 hover:bg-emerald-500/20 text-gray-300 hover:text-emerald-300 border border-white/10 hover:border-emerald-500/30 transition-all"
        >
          📋 复制
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'

const props = defineProps({
  node: {
    type: Object,
    required: true,
    validator: (node) => node.host && node.port
  }
})

const emit = defineEmits(['show-precision-test', 'show-qrcode'])

// QR 码状态
const showingQRCode = ref(false)
const qrCodeGenerated = ref(false)
const qrCodeData = ref('')

// ==================== 计算属性 ====================

const hasValidLink = computed(() => {
  if (!props.node.link) return false
  const link = String(props.node.link).trim()
  return link.length > 0 && link !== 'null' && link !== 'undefined' && link !== 'N/A'
})

// 节点状态样式
const nodeStatusClass = computed(() => {
  const status = props.node.status
  if (status === 'offline') {
    return 'from-rose-500/10 to-rose-500/5 border-rose-500/30 hover:border-rose-500/50 hover:shadow-rose-500/20 opacity-60'
  }
  if (status === 'suspect') {
    return 'from-amber-500/10 to-amber-500/5 border-amber-500/30 hover:border-amber-500/50 hover:shadow-amber-500/20'
  }
  return 'from-white/10 to-white/5 border-white/20 hover:border-white/40 hover:shadow-purple-500/20'
})

const speedColor = computed(() => {
  if (props.node.speed >= 10) return 'text-emerald-400'
  if (props.node.speed >= 5) return 'text-amber-400'
  if (props.node.speed > 0) return 'text-red-400'
  return 'text-gray-500'
})

const barColor = computed(() => {
  if (props.node.speed >= 10) return 'bg-emerald-500'
  if (props.node.speed >= 5) return 'bg-amber-500'
  if (props.node.speed > 0) return 'bg-rose-500'
  return 'bg-gray-700'
})

const latencyColor = computed(() => {
  if (props.node.latency < 100) return 'text-emerald-400'
  if (props.node.latency < 300) return 'text-amber-400'
  return 'text-red-400'
})

const latencyBarColor = computed(() => {
  if (props.node.latency < 100) return 'bg-emerald-500'
  if (props.node.latency < 300) return 'bg-amber-500'
  return 'bg-rose-500'
})

const qualityScore = computed(() => {
  const latencyScore = Math.max(0, 100 - props.node.latency)
  const speedScore = Math.min(100, (props.node.speed / 50) * 100)
  return Math.round((latencyScore + speedScore) / 2)
})

const qualityColor = computed(() => {
  const score = qualityScore.value
  if (score >= 80) return 'text-emerald-400'
  if (score >= 60) return 'text-amber-400'
  return 'text-red-400'
})

const qualityBarColor = computed(() => {
  const score = qualityScore.value
  if (score >= 80) return 'bg-emerald-500'
  if (score >= 60) return 'bg-amber-500'
  return 'bg-rose-500'
})

// ==================== 方法 ====================

/**
 * 生成二维码
 */
async function generateQRCode() {
  if (!hasValidLink.value) {
    alert('❌ 此节点没有可用链接')
    return
  }

  try {
    const link = String(props.node.link).trim()
    qrCodeGenerated.value = false

    // 使用 CDN 的 QR 码服务
    const encodedLink = encodeURIComponent(link)
    const qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodedLink}`

    // 预加载图片
    const img = new Image()
    img.onload = () => {
      qrCodeData.value = qrUrl
      qrCodeGenerated.value = true
    }
    img.onerror = () => {
      alert('❌ 二维码生成失败')
      showingQRCode.value = false
    }
    img.src = qrUrl
  } catch (error) {
    console.error('❌ 生成二维码出错:', error)
    alert('❌ 生成二维码失败')
    showingQRCode.value = false
  }
}

/**
 * 切换 QR 码显示
 */
function toggleQRCode() {
  if (!showingQRCode.value) {
    // 显示 QR 码
    showingQRCode.value = true
    generateQRCode()
  } else {
    // 隐藏 QR 码
    showingQRCode.value = false
    qrCodeGenerated.value = false
  }
}

/**
 * 显示友好提示
 */
function showToast(message, type = 'info') {
  // 创建临时 toast 元素
  const toast = document.createElement('div')
  const colors = {
    success: 'bg-emerald-500',
    error: 'bg-rose-500',
    info: 'bg-blue-500'
  }
  
  toast.className = `${colors[type] || colors.info} text-white px-4 py-2 rounded-lg text-sm font-medium shadow-lg fixed top-4 right-4 z-50 animate-fade-in-out`
  toast.textContent = message
  document.body.appendChild(toast)
  
  // 2 秒后自动移除
  setTimeout(() => {
    toast.remove()
  }, 2000)
}

/**
 * 复制链接
 */
async function copyLink() {
  if (!hasValidLink.value) {
    showToast('此节点没有可用链接', 'info')
    return
  }

  try {
    const link = String(props.node.link).trim()
    await navigator.clipboard.writeText(link)
    showToast('链接已复制到剪贴板 ✨', 'success')
  } catch (err) {
    console.error('❌ 复制失败:', err)
    showToast('复制失败，请手动复制', 'error')
  }
}

// 当 node 改变时，重置 QR 码状态
watch(
  () => props.node.id,
  () => {
    showingQRCode.value = false
    qrCodeGenerated.value = false
  }
)
</script>

<style scoped>
.glass-card {
  transition: all 0.3s ease;
}

.glass-card:hover {
  transform: translateY(-2px);
}

@keyframes fadeInOut {
  0% {
    opacity: 0;
    transform: translateY(-10px);
  }
  10% {
    opacity: 1;
    transform: translateY(0);
  }
  90% {
    opacity: 1;
    transform: translateY(0);
  }
  100% {
    opacity: 0;
    transform: translateY(-10px);
  }
}

:global(.animate-fade-in-out) {
  animation: fadeInOut 2s ease-in-out;
}
</style>
