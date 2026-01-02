#!/usr/bin/env python3
"""
直接同步脚本 - 从本地 nodes.json 同步到 Supabase
"""

import json
import os
from datetime import datetime
from pathlib import Path

# Supabase 配置 (从环境变量读取)
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://hnlkwtkxbqiakeyienok.supabase.co")
# 使用 service_role key 绕过 RLS 限制
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")
if not SUPABASE_KEY:
    SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhubGt3dGt4YnFpYWtleWllbm9rIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NjkwNDA1OSwiZXhwIjoyMDgyNDgwMDU5fQ.VXnH4suGKI6wBLCUi5cHYHO27PUJE_I-iPS3HAhYtSk"

def sync_nodes_from_file(json_file_path):
    """
    从本地 JSON 文件同步节点到 Supabase
    """
    print("\n" + "="*70)
    print("🔄 开始从本地文件同步数据到 Supabase")
    print("="*70 + "\n")

    # 读取本地 JSON 文件
    if not Path(json_file_path).exists():
        print(f"❌ 文件不存在: {json_file_path}")
        return False

    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            nodes = json.load(f)
    except Exception as e:
        print(f"❌ 读取文件失败: {e}")
        return False

    if not isinstance(nodes, list) or len(nodes) == 0:
        print(f"❌ 文件格式错误或为空")
        return False

    print(f"✅ 成功加载 {len(nodes)} 个节点")
    print(f"   文件: {json_file_path}")
    print()

    # 连接 Supabase
    try:
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ 已连接到 Supabase")
    except Exception as e:
        print(f"❌ Supabase 连接失败: {e}")
        return False

    # 准备数据
    data = []
    seen_ids = set()

    for i, node in enumerate(nodes):
        # ✅ 修复：只同步已测速的节点（latency_ms 不为 9999）
        latency = node.get("latency_ms", 9999)
        if latency == 9999:
            # 跳过未测速的节点
            continue
        
        # 构造唯一ID
        node_id = f"{node.get('host', 'unknown')}:{node.get('port', 'unknown')}"

        # 跳过重复
        if node_id in seen_ids:
            print(f"⚠️ 跳过重复: {node_id}")
            continue

        seen_ids.add(node_id)

        # 获取 link 字段 (优先从节点本身，否则为空)
        link = node.get("link", "")
        
        data.append({
            "id": node_id,
            "content": node,
            "link": link,
            "is_free": len(data) < 15,  # 前 15 个免费
            "speed": int(float(node.get("speed", 0))),
            "latency": int(latency),
            "updated_at": datetime.now().isoformat()
        })

    if not data:
        print("❌ 没有有效数据需要保存")
        return False

    # 批量保存
    batch_size = 50
    total_saved = 0
    failed_batches = []

    print(f"\n📤 开始保存 {len(data)} 条数据到 Supabase...\n")

    for i in range(0, len(data), batch_size):
        batch = data[i:i + batch_size]
        batch_num = i // batch_size + 1

        try:
            supabase.table("nodes").upsert(batch).execute()
            total_saved += len(batch)
            
            # 显示保存结果
            for node_data in batch:
                node_id = node_data["id"]
                link = node_data["link"]
                link_status = "✅ 有" if link else "❌ 无"
                print(f"   {batch_num}.{batch[0]['id']} - {link_status} link 字段")
            
            print(f"✅ 批次 {batch_num}: 保存 {len(batch)} 条")

        except Exception as e:
            print(f"❌ 批次 {batch_num} 失败: {e}")
            failed_batches.append(batch_num)

    print()
    print("="*70)
    if failed_batches:
        print(f"⚠️ 完成! 保存 {total_saved}/{len(data)} 条数据 (失败批次: {failed_batches})")
    else:
        print(f"✅ 完成! 成功保存 {total_saved}/{len(data)} 条数据到 Supabase")
    print("="*70 + "\n")

    return True


if __name__ == "__main__":
    # 支持多个路径
    paths = [
        "public/nodes.json",
        "/Users/ikun/study/Learning/viper-node-store/public/nodes.json",
        "/Users/ikun/study/Learning/SpiderFlow/backend/verified_nodes.json"
    ]

    success = False
    for path in paths:
        if Path(path).exists():
            success = sync_nodes_from_file(path)
            if success:
                break

    if not success:
        print(f"❌ 无法从任何来源同步数据")
        print(f"   尝试的路径: {', '.join(paths)}")
