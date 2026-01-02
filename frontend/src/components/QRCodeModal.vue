<template>
  <div v-if="show" class="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
    <div class="relative bg-gray-900 rounded-2xl p-8 max-w-lg w-full mx-4 border border-white/10">
      <!-- 关闭按钮 -->
      <button
        @click="close"
        class="absolute top-4 right-4 text-gray-400 hover:text-white transition"
      >
        ✕
      </button>

      <!-- 标题 -->
      <h2 class="text-2xl font-bold text-white mb-4">{{ node.name }}</h2>

      <!-- 内容区域 -->
      <div class="space-y-4">
        <!-- 节点地址 -->
        <div class="bg-gray-800/50 p-4 rounded-lg">
          <p class="text-xs text-gray-400 mb-1">节点地址</p>
          <p class="text-white font-mono text-sm break-all">{{ node.host }}:{{ node.port }}</p>
        </div>

        <!-- 二维码 -->
        <div class="flex justify-center py-4">
          <div
            v-if="link && link.trim()"
            ref="qrcodeContainer"
            class="bg-white p-2 rounded-lg"
          />
          <div v-else class="w-64 h-64 bg-gray-800 rounded-lg flex items-center justify-center">
            <div class="text-center">
              <p class="text-gray-400 text-sm">🔗 链接不可用</p>
              <p class="text-gray-500 text-xs mt-2">此节点没有有效的配置链接</p>
            </div>
          </div>
        </div>

        <!-- 链接信息 -->
        <div v-if="link && link.trim()" class="bg-gray-800/50 p-4 rounded-lg">
          <p class="text-xs text-gray-400 mb-2">分享链接</p>
          <div class="flex gap-2">
            <input
              type="text"
              :value="link"
              readonly
              class="flex-1 bg-gray-700 text-white text-xs p-2 rounded border border-gray-600 font-mono"
            />
            <button
              @click="copyLink"
              class="px-4 py-2 bg-emerald-500 hover:bg-emerald-600 text-white text-xs font-bold rounded transition"
            >
              📋 Copy
            </button>
          </div>
          <p v-if="copied" class="text-emerald-400 text-xs mt-2">✓ 已复制</p>
        </div>

        <!-- 节点详情 -->
        <div class="grid grid-cols-2 gap-3">
          <div class="bg-gray-800/50 p-3 rounded-lg">
            <p class="text-xs text-gray-400">协议</p>
            <p class="text-white font-bold">{{ node.protocol }}</p>
          </div>
          <div class="bg-gray-800/50 p-3 rounded-lg">
            <p class="text-xs text-gray-400">国家</p>
            <p class="text-white font-bold">{{ node.country }}</p>
          </div>
          <div class="bg-gray-800/50 p-3 rounded-lg">
            <p class="text-xs text-gray-400">速度</p>
            <p class="text-emerald-400 font-bold">{{ node.speed }} MB/s</p>
          </div>
          <div class="bg-gray-800/50 p-3 rounded-lg">
            <p class="text-xs text-gray-400">延迟</p>
            <p class="text-white font-bold">{{ node.latency }} ms</p>
          </div>
        </div>
      </div>

      <!-- 关闭按钮 -->
      <button
        @click="close"
        class="w-full mt-6 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg transition font-bold"
      >
        CLOSE
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { copyToClipboard } from '../services/api'

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

const emit = defineEmits(['close'])

const qrcodeContainer = ref(null)
const copied = ref(false)
const link = ref('')

/**
 * 监听node变化，重新生成二维码
 */
watch(
  () => props.node,
  (newNode) => {
    link.value = newNode.link || ''
    if (props.show && link.value && link.value.trim()) {
      generateQRCode()
    }
  },
  { immediate: true }
)

/**
 * 监听show变化
 */
watch(
  () => props.show,
  (isShow) => {
    if (isShow) {
      // 清除旧的二维码
      if (qrcodeContainer.value) {
        qrcodeContainer.value.innerHTML = ''
      }
      // 延迟生成二维码，确保DOM已更新
      setTimeout(() => {
        if (link.value && link.value.trim()) {
          generateQRCode()
        }
      }, 0)
    }
  }
)

/**
 * 生成二维码
 */
function generateQRCode() {
  if (!qrcodeContainer.value || !link.value) return

  try {
    // 确保容器为空
    qrcodeContainer.value.innerHTML = ''

    // 使用 easyqrcodejs 生成二维码
    new window.QRCode(qrcodeContainer.value, {
      text: link.value,
      width: 280,
      height: 280,
      colorDark: '#000000',
      colorLight: '#ffffff',
      correctLevel: window.QRCode.CorrectLevel.L,
      quietZone: 2,
      quietZoneColor: '#ffffff'
    })

    console.log('✅ 二维码生成成功')
  } catch (error) {
    console.error('❌ 二维码生成失败:', error)
  }
}

/**
 * 复制链接
 */
async function copyLink() {
  const success = await copyToClipboard(link.value)
  if (success) {
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2000)
  }
}

/**
 * 关闭弹窗
 */
function close() {
  emit('close')
}
</script>

<style scoped>
/* 确保二维码容器大小 */
:deep(#qrcode) {
  display: flex;
  justify-content: center;
  align-items: center;
}

:deep(#qrcode img),
:deep(#qrcode canvas) {
  max-width: 100%;
  max-height: 100%;
}
</style>
