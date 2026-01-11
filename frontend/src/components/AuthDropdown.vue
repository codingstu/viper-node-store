<template>
  <!-- 账户下拉面板（内联形式，仿 HTML 实现） -->
  <div class="relative">
    <!-- 触发按钮 -->
    <button
      @click="isOpen = !isOpen"
      :class="[
        'px-4 py-1.5 rounded-lg font-bold text-sm transition flex items-center gap-2',
        !authStore.isAuthenticated
          ? 'bg-blue-600 hover:bg-blue-700 text-white'
          : 'bg-purple-600 hover:bg-purple-700 text-white'
      ]"
    >
      <template v-if="!authStore.isAuthenticated">
        🔐 登录
      </template>
      <template v-else>
        <span class="text-xs text-gray-200">{{ authStore.displayName }}</span>
        <div v-if="authStore.isVip"
          class="inline-flex items-center gap-1 bg-yellow-500/20 text-yellow-300 px-2 py-0.5 rounded-full text-xs font-bold border border-yellow-500/50">
          ⭐ VIP
        </div>
        <div v-else
          class="inline-flex items-center gap-1 bg-gray-500/20 text-gray-300 px-2 py-0.5 rounded-full text-xs font-bold border border-gray-500/50">
          👤 用户
        </div>
      </template>
    </button>

    <!-- 下拉面板 -->
    <transition name="dropdown">
      <div
        v-if="isOpen"
        class="absolute right-0 mt-2 w-96 bg-white rounded-lg shadow-2xl border border-gray-200 z-50 max-h-[70vh] overflow-y-auto"
        @click.stop
      >
        <!-- 关闭按钮 -->
        <div class="flex justify-between items-center p-4 border-b border-gray-200 sticky top-0 bg-white rounded-t-lg">
          <h3 class="text-lg font-bold text-gray-900">账户系统</h3>
          <button
            @click="isOpen = false"
            class="text-gray-500 hover:text-gray-700 text-2xl"
          >
            ×
          </button>
        </div>

        <!-- 已登录状态 -->
        <div v-if="authStore.isAuthenticated" class="p-4">
          <div class="bg-blue-50 rounded-lg p-3 mb-4">
            <p class="text-sm text-gray-600">当前账户</p>
            <p class="text-lg font-bold text-blue-600 mb-2">{{ authStore.displayName }}</p>
            <div v-if="authStore.isVip" class="inline-block bg-yellow-400 text-black px-3 py-1 rounded-full text-xs font-bold">
              ⭐ VIP 用户
            </div>
            <div v-else class="inline-block bg-gray-300 text-black px-3 py-1 rounded-full text-xs font-bold">
              📌 普通用户
            </div>
          </div>

          <!-- 已登录标签页 -->
          <div class="flex border-b gap-0">
            <button
              @click="activeTab = 'redeem'"
              :class="[
                'flex-1 py-2 text-sm font-medium transition-colors',
                activeTab === 'redeem'
                  ? 'text-blue-600 border-b-2 border-blue-600'
                  : 'text-gray-600 hover:text-gray-900'
              ]"
            >
              激活码
            </button>
            <button
              @click="activeTab = 'account'"
              :class="[
                'flex-1 py-2 text-sm font-medium transition-colors',
                activeTab === 'account'
                  ? 'text-blue-600 border-b-2 border-blue-600'
                  : 'text-gray-600 hover:text-gray-900'
              ]"
            >
              信息
            </button>
          </div>

          <!-- 激活码兑换 -->
          <form v-if="activeTab === 'redeem'" @submit.prevent="handleRedeemCode" class="p-4 space-y-3">
            <div>
              <label class="block text-xs font-medium text-gray-700 mb-1">激活码</label>
              <input
                v-model="redeemForm.code"
                type="text"
                placeholder="XXXX-XXXX-XXXX"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
              />
            </div>
            <button
              type="submit"
              :disabled="authStore.isLoading || !redeemForm.code.trim()"
              class="w-full bg-yellow-500 text-white py-2 rounded-lg font-bold hover:bg-yellow-600 disabled:opacity-50 transition text-sm"
            >
              {{ authStore.isLoading ? '兑换中...' : '兑换激活码' }}
            </button>
            <p v-if="redeemSuccess" class="text-green-600 text-xs font-bold">✅ {{ redeemSuccess }}</p>
            <p v-if="authStore.error && activeTab === 'redeem'" class="text-red-600 text-xs">{{ authStore.error }}</p>
          </form>

          <!-- 账户信息 -->
          <div v-if="activeTab === 'account'" class="p-4 space-y-3">
            <div class="bg-gray-50 p-3 rounded-lg text-sm">
              <p class="text-gray-600">邮箱</p>
              <p class="font-mono text-gray-900 break-all">{{ authStore.currentUser?.email }}</p>
            </div>
            <button
              @click="handleLogout"
              class="w-full bg-red-100 text-red-600 py-2 rounded-lg font-bold hover:bg-red-200 transition text-sm"
            >
              登出
            </button>
          </div>
        </div>

        <!-- 未登录状态：登录/注册表单 -->
        <div v-else class="p-4">
          <!-- 登录标签页 -->
          <div class="flex border-b gap-0 mb-4">
            <button
              @click="activeTab = 'login'"
              :class="[
                'flex-1 py-2 text-sm font-medium transition-colors',
                activeTab === 'login'
                  ? 'text-blue-600 border-b-2 border-blue-600'
                  : 'text-gray-600 hover:text-gray-900'
              ]"
            >
              登录
            </button>
            <button
              @click="activeTab = 'register'"
              :class="[
                'flex-1 py-2 text-sm font-medium transition-colors',
                activeTab === 'register'
                  ? 'text-blue-600 border-b-2 border-blue-600'
                  : 'text-gray-600 hover:text-gray-900'
              ]"
            >
              注册
            </button>
          </div>

          <!-- 登录表单 -->
          <form v-if="activeTab === 'login'" @submit.prevent="handleLogin" class="space-y-3">
            <div>
              <label class="block text-xs font-medium text-gray-700 mb-1">邮箱</label>
              <input
                v-model="loginForm.email"
                type="email"
                placeholder="user@example.com"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
              />
            </div>
            <div>
              <label class="block text-xs font-medium text-gray-700 mb-1">密码</label>
              <input
                v-model="loginForm.password"
                type="password"
                placeholder="••••••••"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
              />
            </div>
            <button
              type="submit"
              :disabled="authStore.isLoading"
              class="w-full bg-blue-600 text-white py-2 rounded-lg font-bold hover:bg-blue-700 disabled:opacity-50 transition text-sm"
            >
              {{ authStore.isLoading ? '登录中...' : '登录' }}
            </button>
            <p v-if="authStore.error && activeTab === 'login'" class="text-red-600 text-xs">{{ authStore.error }}</p>
          </form>

          <!-- 注册表单 -->
          <form v-if="activeTab === 'register'" @submit.prevent="handleRegister" class="space-y-3">
            <div>
              <label class="block text-xs font-medium text-gray-700 mb-1">邮箱</label>
              <input
                v-model="registerForm.email"
                type="email"
                placeholder="user@example.com"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
              />
            </div>
            <div>
              <label class="block text-xs font-medium text-gray-700 mb-1">用户名</label>
              <input
                v-model="registerForm.username"
                type="text"
                placeholder="用户名"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
              />
            </div>
            <div>
              <label class="block text-xs font-medium text-gray-700 mb-1">密码</label>
              <input
                v-model="registerForm.password"
                type="password"
                placeholder="••••••••"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
              />
            </div>
            <button
              type="submit"
              :disabled="authStore.isLoading"
              class="w-full bg-blue-600 text-white py-2 rounded-lg font-bold hover:bg-blue-700 disabled:opacity-50 transition text-sm"
            >
              {{ authStore.isLoading ? '注册中...' : '注册' }}
            </button>

            <!-- 极速注册分隔线 -->
            <div class="relative my-3">
              <div class="absolute inset-0 flex items-center">
                <div class="w-full border-t border-gray-300"></div>
              </div>
              <div class="relative flex justify-center text-xs">
                <span class="px-2 bg-white text-gray-500">或</span>
              </div>
            </div>

            <!-- 极速注册按钮 -->
            <button
              type="button"
              @click="handleQuickStart"
              :disabled="authStore.isLoading"
              class="w-full bg-gradient-to-r from-purple-500 to-pink-500 text-white py-2 rounded-lg font-bold hover:from-purple-600 hover:to-pink-600 disabled:opacity-50 transition text-sm"
            >
              {{ authStore.isLoading ? '接入中...' : '🚀 极速注册' }}
            </button>
            <p class="text-xs text-gray-500 text-center">
              无需邮箱验证，一键接入
            </p>

            <p v-if="authStore.error && activeTab === 'register'" class="text-red-600 text-xs">{{ authStore.error }}</p>
          </form>
        </div>
      </div>
    </transition>

    <!-- 外部点击关闭 -->
    <div v-if="isOpen" class="fixed inset-0 z-40" @click="isOpen = false"></div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useAuthStore } from '../stores/authStore'
import { useNodeStore } from '../stores/nodeStore'

const authStore = useAuthStore()
const nodeStore = useNodeStore()
const isOpen = ref(false)
const activeTab = ref('login')
const redeemSuccess = ref('')

const loginForm = ref({
  email: '',
  password: ''
})

const registerForm = ref({
  email: '',
  username: '',
  password: ''
})

const redeemForm = ref({
  code: ''
})

// 登录处理
const handleLogin = async () => {
  const result = await authStore.login(loginForm.value.email, loginForm.value.password)
  if (result.success) {
    loginForm.value = { email: '', password: '' }
    redeemSuccess.value = ''
    
    // 登录成功后刷新节点列表，以应用VIP状态
    await nodeStore.refreshNodes()
    
    setTimeout(() => {
      isOpen.value = false
    }, 500)
  }
}

// 注册处理
const handleRegister = async () => {
  const result = await authStore.register(
    registerForm.value.email,
    registerForm.value.password,
    registerForm.value.username
  )
  if (result.success) {
    registerForm.value = { email: '', username: '', password: '' }
    redeemSuccess.value = ''
    setTimeout(() => {
      isOpen.value = false
    }, 500)
  }
}

// 极速注册处理
const handleQuickStart = async () => {
  const result = await authStore.quickStart()
  if (result.success) {
    registerForm.value = { email: '', username: '', password: '' }
    redeemSuccess.value = '✅ 已自动登录！'
    
    // 极速注册成功后刷新节点列表
    await nodeStore.refreshNodes()
    
    setTimeout(() => {
      isOpen.value = false
    }, 1000)
  }
}

// 激活码兑换处理
const handleRedeemCode = async () => {
  if (!redeemForm.value.code.trim()) {
    authStore.error = '请输入激活码'
    return
  }
  const result = await authStore.redeemCode(redeemForm.value.code)
  if (result.success) {
    redeemSuccess.value = '✅ 激活成功！您已升级为 VIP 用户'
    redeemForm.value.code = ''
    
    // 激活VIP成功后，刷新节点列表以获取更多节点
    await nodeStore.refreshNodes()
    
    // 等待 2 秒后关闭下拉面板，让用户看到成功提示
    setTimeout(() => {
      redeemSuccess.value = ''
      isOpen.value = false
    }, 2000)
  }
}

// 登出处理
const handleLogout = async () => {
  const result = await authStore.logout()
  if (result.success) {
    isOpen.value = false
  }
}
</script>

<style scoped>
.dropdown-enter-active, .dropdown-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.dropdown-enter-from, .dropdown-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
