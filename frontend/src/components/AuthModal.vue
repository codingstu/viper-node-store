<template>
  <!-- 🔐 Auth Modal 模态框 -->
  <div 
    v-if="isOpen"
    class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
    @click.self="close"
  >
    <div class="bg-white rounded-lg shadow-2xl w-full max-w-md mx-4 max-h-[90vh] overflow-y-auto">
      <!-- 关闭按钮 -->
      <div class="flex justify-between items-center p-6 border-b">
        <h2 class="text-xl font-bold text-gray-900">账户系统</h2>
        <button 
          @click="close"
          class="text-gray-500 hover:text-gray-700 text-2xl"
        >
          ×
        </button>
      </div>

      <!-- 🔥 故障排除提示 -->
      <div v-if="authStore.error && authStore.error.includes('supabase')" class="bg-yellow-100 border-l-4 border-yellow-500 p-4 mx-4 mt-4">
        <p class="text-sm text-yellow-800 font-semibold">⚠️ 数据库连接超时</p>
        <p class="text-xs text-yellow-700 mt-1">Supabase 服务可能暂时不可用。请：</p>
        <ul class="text-xs text-yellow-700 mt-2 ml-2">
          <li>• 刷新页面重试 (Cmd+Shift+R)</li>
          <li>• 检查网络连接</li>
          <li>• 稍后再试</li>
        </ul>
      </div>

      <!-- 标签页 -->
      <div class="flex border-b">
        <button 
          @click="activeTab = 'login'"
          :class="[
            'flex-1 py-3 font-medium transition-colors',
            activeTab === 'login' 
              ? 'bg-blue-50 text-blue-600 border-b-2 border-blue-600'
              : 'text-gray-600 hover:text-gray-900'
          ]"
        >
          登录
        </button>
        <button 
          @click="activeTab = 'register'"
          :class="[
            'flex-1 py-3 font-medium transition-colors',
            activeTab === 'register' 
              ? 'bg-blue-50 text-blue-600 border-b-2 border-blue-600'
              : 'text-gray-600 hover:text-gray-900'
          ]"
        >
          注册
        </button>
        <button 
          v-if="authStore.isAuthenticated"
          @click="activeTab = 'redeem'"
          :class="[
            'flex-1 py-3 font-medium transition-colors',
            activeTab === 'redeem' 
              ? 'bg-blue-50 text-blue-600 border-b-2 border-blue-600'
              : 'text-gray-600 hover:text-gray-900'
          ]"
        >
          激活码
        </button>
      </div>

      <!-- 内容区域 -->
      <div class="p-6">
        <!-- 已登录状态 -->
        <div v-if="authStore.isAuthenticated" class="mb-4">
          <div class="bg-blue-50 rounded-lg p-4 mb-4">
            <p class="text-sm text-gray-600">当前账户</p>
            <p class="text-lg font-bold text-blue-600 mb-2">{{ authStore.displayName }}</p>
            <div v-if="authStore.isVip" class="inline-block bg-yellow-400 text-black px-3 py-1 rounded-full text-sm font-bold">
              ⭐ VIP 用户
            </div>
            <div v-else class="inline-block bg-gray-300 text-black px-3 py-1 rounded-full text-sm font-bold">
              📌 普通用户
            </div>
          </div>
        </div>

        <!-- 登录表单 -->
        <form v-if="activeTab === 'login'" @submit.prevent="handleLogin">
          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">邮箱</label>
              <input 
                v-model="loginForm.email"
                type="email"
                placeholder="user@example.com"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                required
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">密码</label>
              <input 
                v-model="loginForm.password"
                type="password"
                placeholder="••••••••"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                required
              />
            </div>
            <button 
              type="submit"
              :disabled="authStore.isLoading"
              class="w-full bg-blue-600 text-white py-2 rounded-lg font-bold hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {{ authStore.isLoading ? '登录中...' : '登录' }}
            </button>
          </div>
          <p v-if="authStore.error" class="mt-3 text-red-600 text-sm">{{ authStore.error }}</p>
        </form>

        <!-- 注册表单 -->
        <form v-if="activeTab === 'register'" @submit.prevent="handleRegister">
          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">邮箱</label>
              <input 
                v-model="registerForm.email"
                type="email"
                placeholder="user@example.com"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                required
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">用户名</label>
              <input 
                v-model="registerForm.username"
                type="text"
                placeholder="用户名"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                required
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">密码</label>
              <input 
                v-model="registerForm.password"
                type="password"
                placeholder="••••••••"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                required
              />
            </div>
            <button 
              type="submit"
              :disabled="authStore.isLoading"
              class="w-full bg-blue-600 text-white py-2 rounded-lg font-bold hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {{ authStore.isLoading ? '注册中...' : '注册' }}
            </button>
          </div>

          <!-- 极速注册分隔线 -->
          <div class="relative my-4">
            <div class="absolute inset-0 flex items-center">
              <div class="w-full border-t border-gray-300"></div>
            </div>
            <div class="relative flex justify-center text-sm">
              <span class="px-2 bg-white text-gray-500">或</span>
            </div>
          </div>

          <!-- 极速注册按钮 -->
          <button 
            type="button"
            @click="handleQuickStart"
            :disabled="authStore.isLoading"
            class="w-full bg-gradient-to-r from-purple-500 to-pink-500 text-white py-2 rounded-lg font-bold hover:from-purple-600 hover:to-pink-600 disabled:opacity-50 transition-colors mb-3"
          >
            {{ authStore.isLoading ? '接入中...' : '🚀 极速注册 (一键接入)' }}
          </button>
          <p class="text-xs text-gray-500 text-center">
            极速注册将为您生成临时账户，无需验证邮箱
          </p>

          <p v-if="authStore.error" class="mt-3 text-red-600 text-sm">{{ authStore.error }}</p>
        </form>

        <!-- 激活码兑换表单 -->
        <form v-if="activeTab === 'redeem'" @submit.prevent="handleRedeemCode">
          <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-4">
            <p class="text-sm text-yellow-800">
              🎁 <strong>已登录状态</strong> - 在下方输入激活码升级为 VIP 用户，解锁所有节点访问权限
            </p>
          </div>
          
          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">激活码</label>
              <input 
                v-model="redeemForm.code"
                type="text"
                placeholder="XXXX-XXXX-XXXX"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono"
                required
              />
            </div>
            <button 
              type="submit"
              :disabled="authStore.isLoading || !redeemForm.code.trim()"
              class="w-full bg-yellow-500 text-white py-2 rounded-lg font-bold hover:bg-yellow-600 disabled:opacity-50 transition-colors"
            >
              {{ authStore.isLoading ? '兑换中...' : '兑换激活码' }}
            </button>
          </div>
          <p v-if="authStore.error" class="mt-3 text-red-600 text-sm">{{ authStore.error }}</p>
          <p v-if="redeemSuccess" class="mt-3 text-green-600 text-sm font-bold">✅ {{ redeemSuccess }}</p>
        </form>
      </div>

      <!-- 登出按钮（已登录时显示） -->
      <div v-if="authStore.isAuthenticated" class="border-t p-6">
        <button 
          @click="handleLogout"
          class="w-full bg-red-100 text-red-600 py-2 rounded-lg font-bold hover:bg-red-200 transition-colors"
        >
          登出
        </button>
      </div>
    </div>
  </div>

  <!-- 身份卡模态框（极速注册后显示） -->
  <div 
    v-if="showIdentityCard"
    class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
    @click.self="showIdentityCard = false"
  >
    <div class="bg-white rounded-lg shadow-2xl w-full max-w-md mx-4 p-6">
      <h3 class="text-2xl font-bold text-center mb-4 text-blue-600">🎉 接入成功</h3>
      
      <div class="bg-gray-900 text-white rounded-lg p-6 space-y-4 font-mono mb-6 border-2 border-blue-400">
        <div class="space-y-2 text-sm">
          <div>
            <span class="text-gray-400">账户ID ▸</span>
            <span class="text-green-400 font-bold">{{ identityCard.username }}</span>
          </div>
          <div>
            <span class="text-gray-400">密码 ▸</span>
            <span class="text-green-400 font-bold">{{ identityCard.password }}</span>
          </div>
          <div class="pt-2 border-t border-gray-700">
            <span class="text-gray-400">邮箱 ▸</span>
            <span class="text-blue-400 font-bold text-xs break-all">{{ identityCard.email }}</span>
          </div>
        </div>
      </div>

      <div class="space-y-3">
        <button 
          @click="copyIdentity"
          class="w-full bg-blue-600 text-white py-2 rounded-lg font-bold hover:bg-blue-700 transition-colors"
        >
          📋 复制账户信息
        </button>
        <button 
          @click="showIdentityCard = false"
          class="w-full bg-gray-200 text-gray-900 py-2 rounded-lg font-bold hover:bg-gray-300 transition-colors"
        >
          关闭
        </button>
      </div>

      <p class="text-xs text-gray-500 text-center mt-4">
        ⚠️ 请妥善保管账户信息，本页面关闭后无法再次显示
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useAuthStore } from '../stores/authStore'

const authStore = useAuthStore()
const emit = defineEmits(['close', 'login-success'])

// 状态
const activeTab = ref('login')
const showIdentityCard = ref(false)
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

const identityCard = ref({
  username: '',
  password: '',
  email: ''
})

// 模态框控制
const isOpen = ref(false)

const open = () => {
  isOpen.value = true
  redeemSuccess.value = ''
}

const close = () => {
  isOpen.value = false
  activeTab.value = 'login'
  loginForm.value = { email: '', password: '' }
  registerForm.value = { email: '', username: '', password: '' }
  redeemForm.value = { code: '' }
  redeemSuccess.value = ''
}

// 登录处理
const handleLogin = async () => {
  const result = await authStore.login(loginForm.value.email, loginForm.value.password)
  if (result.success) {
    console.log('✅ 登录成功，强制刷新状态')
    // 强制更新认证状态
    await authStore.checkVipStatus()
    // 延迟关闭确保状态更新
    setTimeout(() => {
      close()
      emit('login-success')
    }, 100)
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
    console.log('✅ 注册成功，强制刷新状态')
    // 强制更新认证状态
    await authStore.checkVipStatus()
    // 延迟关闭确保状态更新
    setTimeout(() => {
      close()
      emit('login-success')
    }, 100)
  }
}

// 极速注册处理
const handleQuickStart = async () => {
  const result = await authStore.quickStart()
  if (result.success) {
    console.log('✅ 极速注册成功，强制刷新状态')
    identityCard.value = {
      username: result.username,
      password: result.password,
      email: result.email
    }
    showIdentityCard.value = true
    // 强制更新认证状态
    await authStore.checkVipStatus()
    // 3秒后关闭Auth模态框
    setTimeout(() => {
      close()
      emit('login-success')
    }, 3000)
  }
}

// 复制账户信息
const copyIdentity = () => {
  const text = `账户: ${identityCard.value.username}\n密码: ${identityCard.value.password}\n邮箱: ${identityCard.value.email}`
  navigator.clipboard.writeText(text).then(() => {
    alert('✅ 账户信息已复制到剪贴板')
  })
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
    setTimeout(() => {
      redeemSuccess.value = ''
      close()
      emit('login-success')
    }, 2000)
  }
}

// 登出处理
const handleLogout = async () => {
  const result = await authStore.logout()
  if (result.success) {
    console.log('✅ 登出成功')
    close()
    emit('login-success')
  }
}

// 导出方法供父组件调用
defineExpose({
  open,
  close
})
</script>

<style scoped>
/* 平滑过渡 */
.border-b-2 {
  transition: all 0.3s ease;
}
</style>
