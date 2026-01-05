// 快速测试节点数据完整性
const testData = {
    "id": "vless_103.173.155.212_443",
    "protocol": "vless",
    "host": "103.173.155.212",
    "port": 443,
    "country": "DE",
    "name": "Test Node",
    "link": "vless://test@103.173.155.212:443",
    "mainland_score": 100,
    "overseas_score": 0
};

console.log("✅ link 字段存在:", !!testData.link);
console.log("✅ link 值:", testData.link);
console.log("✅ country 值:", testData.country);
console.log("✅ mainland_score > 0:", testData.mainland_score > 0);
console.log("✅ 应该在大陆区域显示:", testData.mainland_score > 0 && testData.country !== 'CN');

// 测试 CN 节点
testData.country = 'CN';
console.log("\n✅ CN 节点 country:", testData.country);
console.log("✅ 应该在大陆区域显示:", testData.mainland_score > 0 && testData.country !== 'CN');
console.log("✅ 应该在 CN 弹窗显示:", testData.country === 'CN' && testData.mainland_score > 0);
