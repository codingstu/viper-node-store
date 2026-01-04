<template>
  <div class="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-black">
    <!-- 背景装饰 -->
    <div class="fixed inset-0 overflow-hidden pointer-events-none">
      <div class="absolute top-0 right-0 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl" />
      <div class="absolute bottom-0 left-0 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl" />
    </div>

    <!-- 主容器 -->
    <div class="relative z-10">
      <!-- 顶部导航栏 -->
      <header class="sticky top-0 z-50 backdrop-blur border-b border-white/10 bg-black/40">
        <div class="max-w-7xl mx-auto px-4 py-4">
          <div class="flex items-center justify-between">
            <!-- Logo -->
            <div class="flex items-center gap-3">
              <span class="text-3xl">🐍</span>
              <div>
                <h1 class="text-2xl font-bold text-white">Viper Node Store</h1>
                <p class="text-xs text-gray-400">节点管理和测速平台</p>
              </div>
            </div>

            <!-- 右侧操作区 -->
            <div class="flex items-center gap-4">
              <!-- 手动刷新按钮 -->
              <ManualRefreshButton />

              <!-- 健康检测按钮 -->
              <button
                @click="showHealthCheckModal = true"
                class="px-4 py-1.5 bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 text-sm font-bold rounded-lg border border-emerald-500/50 transition"
                title="检测所有节点的健康状态"
              >
                🏥 健康检测
              </button>

              <!-- VIP 徽章 -->
              <div v-if="authStore.isAuthenticated" class="hidden sm:flex items-center gap-2">
                <span class="text-sm text-gray-300">{{ authStore.displayName }}</span>
                <div v-if="authStore.isVip" class="inline-flex items-center gap-1 bg-yellow-500/20 text-yellow-300 px-2.5 py-1 rounded-full text-xs font-bold border border-yellow-500/50">
                  ⭐ VIP
                </div>
                <div v-else class="inline-flex items-center gap-1 bg-gray-500/20 text-gray-300 px-2.5 py-1 rounded-full text-xs font-bold border border-gray-500/50">
                  📌 用户
                </div>
              </div>

              <!-- 同步状态 -->
              <div
                :class="[
                  'px-3 py-1.5 rounded-full text-xs font-bold transition',
                  syncInfo.status === 'success'
                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/50'
                    : 'bg-amber-500/20 text-amber-300 border border-amber-500/50'
                ]"
              >
                {{ syncStatusText }}
              </div>

              <!-- 刷新按钮 -->
              <button
                @click="nodeStore.refreshNodes()"
                :disabled="nodeStore.isLoading"
                class="px-4 py-1.5 bg-white/10 hover:bg-white/20 text-white text-sm font-bold rounded-lg transition disabled:opacity-50"
              >
                {{ nodeStore.isLoading ? '加载中...' : '🔄 刷新' }}
              </button>

              <!-- 账户下拉面板（替代 AuthModal） -->
              <AuthDropdown />
            </div>
          </div>
        </div>
      </header>

      <!-- 统计信息 -->
      <section class="max-w-7xl mx-auto px-4 py-3">
        <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div class="bg-gradient-to-br from-purple-500/10 to-purple-500/5 p-2 rounded-xl border border-purple-500/20">
            <p class="text-[10px] text-gray-400">总节点数</p>
            <p class="text-2xl font-bold text-purple-300 mt-0.5">{{ nodeStore.nodeCount }}</p>
          </div>
          <div class="bg-gradient-to-br from-emerald-500/10 to-emerald-500/5 p-2 rounded-xl border border-emerald-500/20">
            <p class="text-[10px] text-gray-400">健康节点</p>
            <p class="text-2xl font-bold text-emerald-300 mt-0.5">{{ nodeStore.healthyNodeCount }}</p>
          </div>
          <div class="bg-gradient-to-br from-blue-500/10 to-blue-500/5 p-2 rounded-xl border border-blue-500/20">
            <p class="text-[10px] text-gray-400">平均速度</p>
            <p class="text-2xl font-bold text-blue-300 mt-0.5">{{ nodeStore.avgSpeed }}</p>
            <p class="text-[10px] text-gray-500">MB/s</p>
          </div>
          <div class="bg-gradient-to-br from-pink-500/10 to-pink-500/5 p-2 rounded-xl border border-pink-500/20">
            <p class="text-[10px] text-gray-400">最后更新</p>
            <p class="text-xs font-bold text-pink-300 mt-0.5">{{ lastUpdateTime }}</p>
          </div>
        </div>
      </section>

      <!-- 搜索和过滤 -->
      <section class="max-w-7xl mx-auto px-4 py-6">
        <div class="space-y-4">
          <!-- 搜索框 -->
          <div class="relative">
            <input
              v-model="nodeStore.searchKeyword"
              type="text"
              placeholder="🔍 搜索节点名称、地址、国家..."
              class="w-full px-4 py-3 bg-white/5 border border-white/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/30 transition"
            />
          </div>

          <!-- 过滤器 -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <!-- 协议过滤 -->
            <div>
              <label class="block text-xs text-gray-400 mb-2">协议</label>
              <select
                v-model="nodeStore.selectedProtocol"
                class="w-full px-3 py-2 bg-white/5 border border-white/20 rounded-lg text-white text-sm focus:outline-none focus:border-purple-500/50 transition"
              >
                <option value="">所有协议</option>
                <option v-for="protocol in nodeStore.filters.protocols" :key="protocol" :value="protocol">
                  {{ protocol }}
                </option>
              </select>
            </div>

            <!-- 国家过滤 -->
            <div>
              <label class="block text-xs text-gray-400 mb-2">国家</label>
              <select
                v-model="nodeStore.selectedCountry"
                class="w-full px-3 py-2 bg-white/5 border border-white/20 rounded-lg text-white text-sm focus:outline-none focus:border-purple-500/50 transition"
              >
                <option value="">所有国家</option>
                <option v-for="country in nodeStore.filters.countries" :key="country" :value="country">
                  {{ country }}
                </option>
              </select>
            </div>
          </div>

          <!-- 清除过滤按钮 -->
          <button
            v-if="nodeStore.searchKeyword || nodeStore.selectedProtocol || nodeStore.selectedCountry"
            @click="nodeStore.clearFilters()"
            class="px-4 py-2 bg-white/10 hover:bg-white/20 text-gray-300 text-sm font-bold rounded-lg transition"
          >
            ✕ 清除过滤
          </button>
        </div>
      </section>

      <!-- 节点网格 - 使用虚拟滚动 -->
      <section class="max-w-7xl mx-auto px-4 pb-12">
        <div v-if="nodeStore.isLoading" class="text-center py-12">
          <p class="text-gray-400">加载中...</p>
        </div>

        <div v-else-if="nodeStore.displayedNodes.length === 0" class="text-center py-12">
          <p class="text-gray-400">未找到匹配的节点</p>
        </div>

        <RecycleScroller
          v-else
          :items="nodeStore.displayedNodes"
          :item-size="null"
          class="scroller"
          key-field="id"
        >
          <template #default="{ item: node }">
            <div class="node-item">
              <NodeCard
                :node="node"
                @show-qrcode="selectedNode = node; showQRCodeModal = true"
                @show-precision-test="selectedNode = node; showTestModal = true"
              />
            </div>
          </template>
        </RecycleScroller>
      </section>
    </div>

    <!-- 二维码弹窗 -->
    <QRCodeModal
      v-if="selectedNode"
      :node="selectedNode"
      :show="showQRCodeModal"
      @close="showQRCodeModal = false"
    />

    <!-- 精确测速弹窗 -->
    <PrecisionTestModal
      v-if="selectedNode"
      :node="selectedNode"
      :show="showTestModal"
      @close="showTestModal = false"
      @test-complete="handleTestComplete"
    />

    <!-- 健康检测弹窗 -->
    <HealthCheckModal
      :show="showHealthCheckModal"
      @close="showHealthCheckModal = false"
      @complete="handleHealthCheckComplete"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { RecycleScroller } from 'vue-virtual-scroller'
import 'vue-virtual-scroller/dist/vue-virtual-scroller.css'
import { useNodeStore } from './stores/nodeStore'
import { useAuthStore } from './stores/authStore'
import NodeCard from './components/NodeCard.vue'
import QRCodeModal from './components/QRCodeModal.vue'
import PrecisionTestModal from './components/PrecisionTestModal.vue'
import HealthCheckModal from './components/HealthCheckModal.vue'
import AuthDropdown from './components/AuthDropdown.vue'
import ManualRefreshButton from './components/ManualRefreshButton.vue'

const nodeStore = useNodeStore()
const authStore = useAuthStore()
const selectedNode = ref(null)
const showQRCodeModal = ref(false)
const showTestModal = ref(false)
const showHealthCheckModal = ref(false)
const lastUpdateTime = ref('--:--')

/**
 * 同步状态文本
 */
const syncStatusText = computed(() => {
  const status = nodeStore.syncInfo.status
  if (status === 'success') return '✓ 数据同步正常'
  if (status === 'syncing') return '⟳ 同步中...'
  if (status === 'error') return '✗ 同步异常'
  return '⟳ 同步状态检查中...'
})

/**
 * 获取同步信息
 */
const syncInfo = computed(() => nodeStore.syncInfo)

/**
 * 初始化应用
 */
onMounted(async () => {
  console.log('🚀 应用启动，初始化数据...')
  // 先初始化 Auth（检查 VIP 状态）
  await authStore.init()
  // 再初始化节点数据
  await nodeStore.init()
  updateLastUpdateTime()
  
  // 每12分钟刷新一次同步状态（与后端Supabase拉取同步）
  setInterval(async () => {
    await nodeStore.refreshNodes()
    updateLastUpdateTime()
  }, 720000)
})

/**
 * 更新最后更新时间
 */
function updateLastUpdateTime() {
  const now = new Date()
  lastUpdateTime.value = now.toLocaleTimeString('zh-CN', { 
    hour: '2-digit', 
    minute: '2-digit' 
  })
}

/**
 * 处理测速完成
 */
function handleTestComplete(result) {
  console.log('✅ 测速完成:', result)
  // 此时selectedNode的speed应该已经被更新了
}

/**
 * 处理健康检测完成
 */
function handleHealthCheckComplete(result) {
  console.log('✅ 健康检测完成:', result)
  // 节点列表已在 HealthCheckModal 中刷新
}

/**
 * 打开登录模态框
 */
function openAuthModal() {
  authModalRef.value?.open()
}

/**
 * 处理登录成功
 */
function handleLoginSuccess() {
  console.log('✅ 用户状态已更新')
  // 强制刷新节点以应用 VIP 限制
  nodeStore.refreshNodes()
}
</script>

<style>
* {
  scrollbar-width: thin;
  scrollbar-color: rgba(255, 255, 255, 0.2) transparent;
}

::-webkit-scrollbar {
  width: 6px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.3);
}

/* 虚拟滚动容器样式 */
.scroller {
  height: calc(100vh - 450px);
  min-height: 400px;
}

.node-item {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 1rem;
  padding: 0 0 1rem 0;
}

.node-item > * {
  grid-column: span 1;
}

/* 响应式适配 */
@media (max-width: 768px) {
  .node-item {
    grid-template-columns: 1fr;
  }
  
  .scroller {
    height: auto;
    min-height: auto;
  }
}
</style>
