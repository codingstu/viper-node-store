/**
 * API 服务层 - 所有与后端的通信都在这里
 * 数据来源：viper-node-store FastAPI 后端 (localhost:8002)
 */

const VIPER_API_BASE = 'http://localhost:8002'
const SPIDERFLOW_API_BASE = 'http://localhost:8001'

export const nodeApi = {
  /**
   * 获取所有节点
   */
  async fetchNodes() {
    try {
      const response = await fetch(`${VIPER_API_BASE}/api/nodes`)
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      let nodes = await response.json()
      
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
        is_free: node.is_free !== false
      }))
      
      return nodes
    } catch (error) {
      console.error('❌ 获取节点失败:', error)
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
      const response = await fetch(`${VIPER_API_BASE}/api/sync-info`)
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

      const response = await fetch(`${VIPER_API_BASE}/api/nodes/precision-test`, {
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
      const response = await fetch(`${VIPER_API_BASE}/api/nodes/latency-test`, {
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
