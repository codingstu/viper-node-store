// 前端诊断工具 - 检查节点数据结构
console.log('🔍 前端诊断工具已加载')

// 获取节点数据并显示
async function diagnoseNodes() {
  console.log('📊 正在诊断节点数据...')
  
  try {
    const response = await fetch('http://localhost:8002/api/nodes?limit=5')
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    
    const nodes = await response.json()
    console.log('✅ 获取成功，共', nodes.length, '个节点')
    console.log('详细信息：')
    console.table(nodes)
    
    // 分析 link 字段
    console.log('\n🔗 链接分析：')
    nodes.forEach((node, i) => {
      console.log(`节点 ${i}: ${node.name}`)
      console.log(`  - link: ${JSON.stringify(node.link)}`)
      console.log(`  - link 类型: ${typeof node.link}`)
      console.log(`  - link 是否有效: ${node.link && String(node.link).trim().length > 0}`)
    })
    
    // 统计无效链接
    const invalidLinkCount = nodes.filter(n => !n.link || String(n.link).trim() === '').length
    console.log(`\n⚠️  无效链接数: ${invalidLinkCount} / ${nodes.length}`)
    
  } catch (error) {
    console.error('❌ 诊断失败:', error)
  }
}

// 导出函数到全局
window.diagnoseNodes = diagnoseNodes

console.log('💡 运行: diagnoseNodes() 来诊断节点数据')
