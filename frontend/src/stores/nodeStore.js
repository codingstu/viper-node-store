/**
 * Pinia 状态管理 - 节点数据存储
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { nodeApi } from '../services/api'
import { useAuthStore } from './authStore'

export const useNodeStore = defineStore('nodes', () => {
  // ==================== 状态 ====================
  const nodes = ref([])
  const allNodesBackup = ref([]) // 备份原始数据用于搜索
  const isLoading = ref(false)
  const filters = ref({ protocols: [], countries: [] })
  const searchKeyword = ref('')
  const selectedProtocol = ref('')
  const selectedCountry = ref('')
  const syncInfo = ref({ status: 'unknown', message: '初始化中...' })

  // ==================== 计算属性 ====================
  const displayedNodes = computed(() => {
    const authStore = useAuthStore()
    let result = allNodesBackup.value

    // 搜索过滤
    if (searchKeyword.value.trim()) {
      const keyword = searchKeyword.value.toLowerCase()
      result = result.filter(node => {
        return (
          node.name.toLowerCase().includes(keyword) ||
          node.host.includes(keyword) ||
          node.country.toLowerCase().includes(keyword) ||
          node.id.includes(keyword)
        )
      })
    }

    // 协议过滤
    if (selectedProtocol.value) {
      result = result.filter(node => node.protocol === selectedProtocol.value)
    }

    // 国家过滤
    if (selectedCountry.value) {
      result = result.filter(node => node.country === selectedCountry.value)
    }

    // VIP 限制：非VIP用户只能看20个节点
    if (!authStore.isVip) {
      result = result.slice(0, 20)
    }

    return result
  })

  const nodeCount = computed(() => displayedNodes.value.length)
  const avgSpeed = computed(() => {
    const speeds = displayedNodes.value
      .filter(n => n.speed > 0)
      .map(n => n.speed)
    if (speeds.length === 0) return 0
    return (speeds.reduce((a, b) => a + b, 0) / speeds.length).toFixed(2)
  })

  const healthyNodeCount = computed(() => {
    return displayedNodes.value.filter(n => n.speed >= 5).length
  })

  // ==================== 方法 ====================

  /**
   * 初始化 - 获取节点和过滤选项
   */
  async function init() {
    isLoading.value = true
    try {
      // 初始化 Auth 状态（检查 VIP）
      const authStore = useAuthStore()
      await authStore.init()

      // 获取节点和同步信息
      const [nodesList, syncData] = await Promise.all([
        nodeApi.fetchNodes(),
        nodeApi.fetchSyncInfo()
      ])

      nodes.value = nodesList
      allNodesBackup.value = JSON.parse(JSON.stringify(nodesList)) // 深拷贝
      syncInfo.value = syncData

      // 从节点数据中提取过滤选项
      const protocols = [...new Set(nodesList.map(n => n.protocol))].sort()
      const countries = [...new Set(nodesList.map(n => n.country))].sort()
      filters.value = { protocols, countries }

      console.log(`✅ 已加载 ${nodesList.length} 个节点 (${authStore.isVip ? 'VIP用户看全部' : '非VIP用户只看20个'})`)
    } catch (error) {
      console.error('❌ 初始化失败:', error)
    } finally {
      isLoading.value = false
    }
  }

  /**
   * 刷新节点列表
   */
  async function refreshNodes() {
    isLoading.value = true
    try {
      const nodesList = await nodeApi.fetchNodes()
      nodes.value = nodesList
      allNodesBackup.value = JSON.parse(JSON.stringify(nodesList))
      
      // 更新过滤选项
      const protocols = [...new Set(nodesList.map(n => n.protocol))].sort()
      const countries = [...new Set(nodesList.map(n => n.country))].sort()
      filters.value = { protocols, countries }
      
      console.log(`✅ 已刷新节点列表`)
    } catch (error) {
      console.error('❌ 刷新失败:', error)
    } finally {
      isLoading.value = false
    }
  }

  /**
   * 更新节点速度 (精确测速后调用)
   */
  function updateNodeSpeed(nodeId, speed) {
    const node = nodes.value.find(n => n.id === nodeId)
    if (node) {
      node.speed = speed
      // 同时更新备份
      const backupNode = allNodesBackup.value.find(n => n.id === nodeId)
      if (backupNode) backupNode.speed = speed
    }
  }

  /**
   * 获取单个节点
   */
  function getNode(nodeId) {
    return nodes.value.find(n => n.id === nodeId)
  }

  /**
   * 精确测速
   */
  async function precisionTest(node, fileSizeMs = 50) {
    return await nodeApi.precisionSpeedTest(node, fileSizeMs)
  }

  /**
   * 清除搜索和过滤
   */
  function clearFilters() {
    searchKeyword.value = ''
    selectedProtocol.value = ''
    selectedCountry.value = ''
  }

  return {
    // 状态
    nodes,
    allNodesBackup,
    isLoading,
    filters,
    searchKeyword,
    selectedProtocol,
    selectedCountry,
    syncInfo,

    // 计算属性
    displayedNodes,
    nodeCount,
    avgSpeed,
    healthyNodeCount,

    // 方法
    init,
    refreshNodes,
    updateNodeSpeed,
    getNode,
    precisionTest,
    clearFilters
  }
})
