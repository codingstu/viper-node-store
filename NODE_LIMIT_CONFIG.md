# 节点限制配置文档

## 概述
本文档说明 viper-node-store 中节点数量限制的配置。

## 当前配置

### 非 VIP 用户
- **节点限制**：20个节点
- **位置**：[app_fastapi.py](app_fastapi.py#L341) 中的 `/api/nodes` 端点
- **实现方式**：
  - 默认limit：20个
  - 手动指定limit时：上限为20个（超过则被限制）

### VIP 用户  
- **节点限制**：500个节点（全部）
- **位置**：[app_fastapi.py](app_fastapi.py#L341) 中的 `/api/nodes` 端点
- **实现方式**：
  - 默认limit：500个
  - 可以手动指定更大的limit

## 限制验证

限制在 **后端** 实现，确保安全性：

```python
# 非 VIP 用户最多 20 个
if not is_vip and limit > 20:
    limit = 20
```

用户无法通过以下方式绕过限制：
- ❌ 修改前端代码
- ❌ 使用浏览器开发者工具(F12)修改参数
- ❌ 直接调用API时添加超大limit值

## 修改方法

若要改变节点限制数量，只需修改 [app_fastapi.py](app_fastapi.py) 中的以下两处数字：

**第1处** - 非VIP默认limit（大约第341行）：
```python
default_limit = 500 if is_vip else 20  # 改这里的 20
```

**第2处** - 非VIP最大limit（大约第346行）：
```python
if not is_vip and limit > 20:  # 改这里的 20
    limit = 20  # 和这里的 20
```

## 测试验证

### 非 VIP 用户（无X-User-ID）
```bash
curl -s 'http://localhost:8002/api/nodes' | jq '. | length'
# 结果：20
```

### VIP 用户（有有效X-User-ID）
```bash
curl -s -H 'X-User-ID: d822d196-be21-47ce-b8d6-aba28dd894d7' \
  'http://localhost:8002/api/nodes' | jq '. | length'
# 结果：68（数据库中的所有节点）
```

## 相关代码

- **检查VIP状态**：[check_user_vip_status()](app_fastapi.py#L192)
- **获取节点API**：[/api/nodes](app_fastapi.py#L323)
- **前端请求**：[nodeStore.js](frontend/src/stores/nodeStore.js) 和 [api.js](frontend/src/services/api.js)

## 更新历史

| 日期 | 版本 | 改动 |
|------|------|------|
| 2026-01-02 | 1.0 | 非VIP限制改为20个节点 |
