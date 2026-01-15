/**
 * API 服务层 - 所有与后端的通信都在这里
 * 数据来源：viper-node-store FastAPI 后端
 */

import { useAuthStore } from '../stores/authStore'

const VIPER_API_BASE = '/api'  // 相对路径，自动指向当前域名的 /api
const SPIDERFLOW_API_BASE = '/api/proxy'  // 通过 viper-node-store 代理 SpiderFlow 请求

/**
 * 获取当前用户 ID（从 authStore）
 */
function getUserId() {
  try {
    const authStore = useAuthStore()
    return authStore.currentUser?.id || null
  } catch (e) {
    return null
  }
}

export const nodeApi = {
  /**
   * 获取所有节点（海外用户节点）
   */
  async fetchNodes() {
    try {
      const userId = getUserId()
      const headers = {
        'Content-Type': 'application/json'
      }
      
      // 如果获取到了用户ID，在header中发送
      if (userId) {
        headers['X-User-ID'] = userId
      }
      
      const response = await fetch(`${VIPER_API_BASE}/nodes`, { headers })
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      let nodes = await response.json()
      
      console.log('📦 获取海外节点数据，示例节点:', nodes.length > 0 ? nodes[0] : 'empty')
      
      // 规范化数据格式
      nodes = nodes.map(node => ({
        id: node.id || `${node.host}:${node.port}`,
        protocol: node.protocol || 'unknown',
        host: node.host,
        port: node.port,
        name: node.name || `${node.host}:${node.port}`,
        country: node.country || 'Unknown',
        link: node.link || '',
        speed: Number(node.speed) || 0,
        latency: Number(node.latency) || 0,
        updated_at: node.updated_at || new Date().toISOString(),
        is_free: node.is_free !== false,
        status: node.status || 'online',  // 健康状态：online/suspect/offline
        last_health_check: node.last_health_check || null,
        health_latency: node.health_latency || null
      }))
      
      return nodes
    } catch (error) {
      console.error('❌ 获取海外节点失败:', error)
      return []
    }
  },

  /**
   * 获取大陆节点（Telegram 节点）
   */
  async fetchTelegramNodes() {
    try {
      const userId = getUserId()
      const headers = {
        'Content-Type': 'application/json'
      }
      
      // 如果获取到了用户ID，在header中发送
      if (userId) {
        headers['X-User-ID'] = userId
      }
      
      const response = await fetch(`${VIPER_API_BASE}/telegram-nodes`, { headers })
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      let nodes = await response.json()
      
      console.log('📦 获取大陆节点数据，示例节点:', nodes.length > 0 ? nodes[0] : 'empty')
      
      // 规范化数据格式（与海外节点保持一致）
      nodes = nodes.map(node => ({
        id: node.id || `${node.host}:${node.port}`,
        protocol: node.protocol || 'unknown',
        host: node.host,
        port: node.port,
        name: node.name || `${node.host}:${node.port}`,
        country: node.country || 'Unknown',
        link: node.link || '',
        speed: Number(node.speed) || 0,
        latency: Number(node.latency) || 0,
        updated_at: node.updated_at || new Date().toISOString(),
        is_free: node.is_free !== false,
        status: node.status || 'online',
        last_health_check: node.last_health_check || null,
        quality_score: node.quality_score || 50,
        source_channel: node.source_channel || null
      }))
      
      return nodes
    } catch (error) {
      console.error('❌ 获取大陆节点失败:', error)
      return []
    }
  },

  /**
   * 获取节点过滤选项
   */
  async fetchFilters() {
    try {
      // 如果API不支持filters，就从节点数据中推导
      const nodes = await this.fetchNodes()
      const protocols = [...new Set(nodes.map(n => n.protocol))].sort()
      const countries = [...new Set(nodes.map(n => n.country))].sort()
      
      return { 
        protocols, 
        countries 
      }
    } catch (error) {
      console.error('❌ 获取过滤选项失败:', error)
      return { protocols: [], countries: [] }
    }
  },

  /**
   * 获取同步信息
   */
  async fetchSyncInfo() {
    try {
      const response = await fetch(`${VIPER_API_BASE}/sync-info`)
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      return await response.json()
    } catch (error) {
      console.error('❌ 获取同步信息失败:', error)
      return { status: 'success', message: '数据同步正常' }
    }
  },

  /**
   * 精确测速 - 用户发起的测速
   */
  async precisionSpeedTest(node, fileSizeMs = 50) {
    try {
      // 构建代理URL：优先使用link，否则基于host:port生成
      let proxyUrl = node.link
      if (!proxyUrl || proxyUrl.trim() === '') {
        const protocol = node.protocol || 'socks5'
        proxyUrl = `${protocol}://${node.host}:${node.port}`
        console.log('✅ 自动构建代理URL:', proxyUrl)
      }

      const response = await fetch(`${VIPER_API_BASE}/nodes/precision-test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          proxy_url: proxyUrl,
          test_file_size: fileSizeMs
        })
      })

      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      return await response.json()
    } catch (error) {
      console.error('❌ 精确测速失败:', error)
      return {
        status: 'error',
        speed_mbps: 0,
        message: `测速失败: ${error.message}`
      }
    }
  },

  /**
   * 延迟测试
   */
  async latencyTest(proxyUrl) {
    try {
      const response = await fetch(`${VIPER_API_BASE}/nodes/latency-test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ proxy_url: proxyUrl })
      })

      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      return await response.json()
    } catch (error) {
      console.error('❌ 延迟测试失败:', error)
      return { status: 'error', latency: 9999 }
    }
  }
}

/**
 * 健康检测 API
 */
export const healthCheckApi = {
  /**
   * 检测所有节点的健康状态（仅限管理员）
   * @param {string} source - 数据源: 'overseas' 或 'china'
   */
  async checkAll(source = 'overseas') {
    try {
      const userId = getUserId()
      const headers = {
        'Content-Type': 'application/json'
      }
      
      // 发送用户ID用于权限验证
      if (userId) {
        headers['X-User-ID'] = userId
      }
      
      const response = await fetch(`${VIPER_API_BASE}/health-check`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ 
          check_all: true,
          source: source
        })
      })

      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const result = await response.json()
      
      // 统一返回格式
      if (result.status === 'success' && result.data) {
        return {
          status: 'success',
          data: result.data,
          message: '检测成功'
        }
      } else {
        return {
          status: 'error',
          message: result.message || '检测失败'
        }
      }
    } catch (error) {
      console.error('❌ 健康检测失败:', error)
      return {
        status: 'error',
        message: error.message
      }
    }
  },

  /**
   * 获取健康检测统计信息
   */
  async getStats() {
    try {
      const response = await fetch(`${VIPER_API_BASE}/health-check/stats`)
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      return await response.json()
    } catch (error) {
      console.error('❌ 获取健康统计失败:', error)
      return {
        total: 0,
        online: 0,
        offline: 0,
        suspect: 0
      }
    }
  },

  /**
   * 检测单个节点
   */
  async checkNode(nodeId) {
    try {
      const response = await fetch(`${VIPER_API_BASE}/health-check`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ node_ids: [nodeId] })
      })

      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      return await response.json()
    } catch (error) {
      console.error('❌ 节点健康检测失败:', error)
      return {
        success: false,
        error: error.message
      }
    }
  }
}

/**
 * 工具函数：复制到剪贴板
 */
export async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch (error) {
    console.error('❌ 复制失败:', error)
    return false
  }
}

/**
 * 工具函数：生成节点的唯一ID
 */
export function generateNodeId(node) {
  return `node-${node.host}-${node.port}`.replace(/\./g, '-').replace(/:/g, '-')
}
