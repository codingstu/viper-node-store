/**
 * Pinia 认证存储 - 管理登录、VIP 状态和用户信息
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { createClient } from '@supabase/supabase-js'

// Supabase 配置（应该从环境变量读取，这里为示例）
const SUPABASE_URL = 'https://hnlkwtkxbqiakeyienok.supabase.co'
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhubGt3dGt4YnFpYWtleWllbm9rIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjY5MDQwNTksImV4cCI6MjA4MjQ4MDA1OX0.Xg9vQdUfBdUW-IJaomEIRGsX6tB_k2grhrF4dm_aNME'

// 初始化 Supabase 客户端
const supabaseClient = createClient(SUPABASE_URL, SUPABASE_ANON_KEY)

export const useAuthStore = defineStore('auth', () => {
  // ==================== 状态 ====================
  const currentUser = ref(null)
  const isVip = ref(false)
  const vipDate = ref(null)
  const isLoading = ref(false)
  const error = ref(null)

  // ==================== 计算属性 ====================
  const isAuthenticated = computed(() => currentUser.value !== null)
  const displayName = computed(() => {
    if (!currentUser.value) return 'GUEST'
    // 如果有用户名就显示，否则显示邮箱前缀
    return currentUser.value.user_metadata?.username || 
           currentUser.value.email?.split('@')[0].toUpperCase() || 
           'USER'
  })
  
  const vipStatus = computed(() => {
    if (!isAuthenticated.value) return 'GUEST (PREVIEW)'
    if (isVip.value) return 'VIP MEMBER'
    return 'FREE USER'
  })

  // ==================== 初始化 ====================
  async function init() {
    try {
      // 🔥 优化：增加重试机制，处理初始化延迟
      let retries = 3
      let lastError = null
      
      while (retries > 0) {
        try {
          console.log(`🔄 检查 VIP 状态... (尝试 ${4 - retries}/3)`)
          await checkVipStatus()
          console.log('✅ 认证系统初始化成功')
          return
        } catch (e) {
          lastError = e
          retries--
          
          if (retries > 0) {
            // 等待 2 秒后重试
            console.warn(`⚠️ 初始化失败，2秒后重试: ${e.message}`)
            await new Promise(resolve => setTimeout(resolve, 2000))
          }
        }
      }
      
      // 3次都失败
      console.error('❌ 认证系统初始化失败（3次重试均失败）:', lastError)
    } catch (e) {
      console.error('Auth init failed:', e)
    }
  }

  // ==================== 检查 VIP 状态 ====================
  async function checkVipStatus() {
    try {
      const { data: { user }, error: userError } = await supabaseClient.auth.getUser()
      
      // 🔥 优化：检查是否是网络错误
      if (userError && userError.message.includes('network')) {
        throw new Error('Supabase 连接超时 - 请检查网络连接')
      }
      
      if (!user) {
        currentUser.value = null
        isVip.value = false
        vipDate.value = null
        return { user: null, isVip: false }
      }

      currentUser.value = user

      // 查询 profiles 表获取 VIP 信息
      const { data, error: profileError } = await supabaseClient
        .from('profiles')
        .select('vip_until')
        .eq('id', user.id)
        .maybeSingle()

      if (profileError && profileError.code === 'PGRST') {
        // 权限错误，可能是 API KEY 过期
        throw new Error('Supabase 认证密钥过期或无效 - 请联系管理员')
      }

      const vipUntil = data?.vip_until
      const isVipNow = vipUntil && new Date(vipUntil) > new Date()
      
      isVip.value = isVipNow
      vipDate.value = vipUntil

      console.log(`✅ VIP 状态检查: ${isVipNow ? 'VIP' : 'FREE'}, 过期时间: ${vipUntil || 'N/A'}`)
      
      return { user, isVip: isVipNow, vipDate: vipUntil }
    } catch (e) {
      console.warn('❌ VIP 检查失败:', e)
      
      // 🔥 优化：更详细的错误消息
      if (e.message.includes('Supabase')) {
        error.value = e.message
      } else {
        error.value = '认证服务暂时不可用，请稍后重试'
      }
      
      return { user: null, isVip: false }
    }
  }

  // ==================== 登录 ====================
  async function login(email, password) {
    isLoading.value = true
    error.value = null
    try {
      const { data, error: signInError } = await supabaseClient.auth.signInWithPassword({
        email,
        password
      })

      if (signInError) throw signInError

      currentUser.value = data.user
      await checkVipStatus()
      
      console.log('✅ 登录成功')
      return { success: true }
    } catch (e) {
      error.value = e.message
      console.error('❌ 登录失败:', e)
      return { success: false, error: e.message }
    } finally {
      isLoading.value = false
    }
  }

  // ==================== 注册 ====================
  async function register(email, password, username = '') {
    isLoading.value = true
    error.value = null
    try {
      const { data, error: signUpError } = await supabaseClient.auth.signUp({
        email,
        password,
        options: {
          data: { username: username || email.split('@')[0] }
        }
      })

      if (signUpError) throw signUpError

      // 注册后可能会自动登录
      if (data.session) {
        currentUser.value = data.user
        await checkVipStatus()
      }

      console.log('✅ 注册成功')
      return { success: true, requiresEmailConfirmation: !data.session }
    } catch (e) {
      error.value = e.message
      console.error('❌ 注册失败:', e)
      return { success: false, error: e.message }
    } finally {
      isLoading.value = false
    }
  }

  // ==================== 极速注册 ====================
  async function quickStart() {
    isLoading.value = true
    error.value = null
    try {
      // 生成随机身份信息
      const timestamp = Date.now().toString().slice(-4)
      const randomStr = Math.random().toString(36).substring(2, 6).toUpperCase()
      const username = `VIPER-${randomStr}-${timestamp}`
      const password = `Viper#${Date.now().toString(36).slice(-8)}!`
      const email = `agent.${randomStr.toLowerCase()}.${timestamp}@shadow-network.com`

      console.log(`🚀 极速注册: ${username}`)

      // 注册账户
      const { data, error: signUpError } = await supabaseClient.auth.signUp({
        email,
        password,
        options: {
          data: { username }
        }
      })

      if (signUpError) throw signUpError

      // 自动登录
      if (!data.session) {
        const { error: loginError } = await supabaseClient.auth.signInWithPassword({
          email,
          password
        })
        if (loginError) throw loginError
      }

      currentUser.value = data.user
      await checkVipStatus()

      // 保存身份到本地（用于显示身份卡）
      localStorage.setItem('shadow_user_email', email)
      localStorage.setItem('shadow_user_pass', password)
      localStorage.setItem('shadow_user_name', username)

      console.log('✅ 极速注册成功，已自动登录')
      return { 
        success: true, 
        identity: { username, email, password }
      }
    } catch (e) {
      error.value = e.message
      console.error('❌ 极速注册失败:', e)
      return { success: false, error: e.message }
    } finally {
      isLoading.value = false
    }
  }

  // ==================== 激活码兑换 ====================
  async function redeemCode(code) {
    isLoading.value = true
    error.value = null
    try {
      // 获取当前用户 ID
      const { data: { user }, error: userError } = await supabaseClient.auth.getUser()
      if (userError || !user) {
        throw new Error('请先登录')
      }

      // 调用后端 API 处理激活码
      const apiUrl = import.meta.env.VITE_API_BASE || '/api'
      const response = await fetch(`${apiUrl}/auth/redeem-code`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          code: code.trim(),
          user_id: user.id
        })
      })

      const data = await response.json()

      if (data.status !== 'success') {
        throw new Error(data.message || '兑换失败')
      }

      // 重新检查 VIP 状态（刷新本地缓存）
      await checkVipStatus()

      console.log('✅ 激活码兑换成功:', data)
      return { success: true, message: data.message }
    } catch (e) {
      error.value = e.message
      console.error('❌ 激活码兑换失败:', e)
      return { success: false, error: e.message }
    } finally {
      isLoading.value = false
    }
  }

  // ==================== 登出 ====================
  async function logout() {
    isLoading.value = true
    error.value = null
    try {
      const { error: signOutError } = await supabaseClient.auth.signOut()
      if (signOutError) throw signOutError

      currentUser.value = null
      isVip.value = false
      vipDate.value = null
      localStorage.removeItem('shadow_user_email')
      localStorage.removeItem('shadow_user_pass')
      localStorage.removeItem('shadow_user_name')

      console.log('✅ 已登出')
      return { success: true }
    } catch (e) {
      error.value = e.message
      console.error('❌ 登出失败:', e)
      return { success: false, error: e.message }
    } finally {
      isLoading.value = false
    }
  }

  return {
    // 状态
    currentUser,
    isVip,
    vipDate,
    isLoading,
    error,
    
    // 计算属性
    isAuthenticated,
    displayName,
    vipStatus,
    
    // 方法
    init,
    checkVipStatus,
    login,
    register,
    quickStart,
    redeemCode,
    logout
  }
})
