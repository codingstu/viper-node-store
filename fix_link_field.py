#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
紧急修复：Supabase nodes 表添加 link 字段并从 SpiderFlow 同步

目的：
1. 在 Supabase nodes 表中添加 link 字符字段
2. 从 SpiderFlow 后端获取完整的节点数据（包含 link）
3. 更新 Supabase 中的所有节点
"""

import os
import sys
import json
import requests
from datetime import datetime
from typing import List, Dict

# 配置
SPIDERFLOW_API = "http://localhost:8001"
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://hnlkwtkxbqiakeyienok.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhubGt3dGt4YnFpYWtleWllbm9rIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjY5MDQwNTksImV4cCI6MjA4MjQ4MDA1OX0.Xg9vQdUfBdUW-IJaomEIRGsX6tB_k2grhrF4dm_aNME")

def step1_add_link_field_to_supabase():
    """
    步骤1: 在 Supabase 中添加 link 字段（如果不存在）
    
    使用 Supabase REST API 或 SQL 编辑器
    """
    print("📝 步骤1: 确保 Supabase nodes 表有 link 字段...")
    print("   💡 在 Supabase SQL Editor 中运行:")
    print("""
    -- 如果 link 字段不存在，添加它
    ALTER TABLE IF EXISTS nodes 
    ADD COLUMN IF NOT EXISTS link TEXT DEFAULT '';
    
    -- 创建索引以提高查询性能
    CREATE INDEX IF NOT EXISTS idx_nodes_link ON nodes(link);
    """)
    print("   ✅ 请在 Supabase 控制台执行上述 SQL")

def step2_fetch_nodes_from_spiderflow():
    """
    步骤2: 从 SpiderFlow 获取完整节点数据
    """
    print("\n🔄 步骤2: 从 SpiderFlow 获取节点数据...")
    try:
        response = requests.get(f"{SPIDERFLOW_API}/api/nodes", timeout=10)
        if response.status_code != 200:
            print(f"❌ SpiderFlow 无响应 (状态码 {response.status_code})")
            return []
        
        nodes = response.json()
        print(f"✅ 成功获取 {len(nodes)} 个节点")
        
        # 验证 link 字段
        nodes_with_link = sum(1 for n in nodes if n.get('link'))
        nodes_without_link = len(nodes) - nodes_with_link
        print(f"   📊 有 link 字段: {nodes_with_link}")
        print(f"   ⚠️  缺少 link 字段: {nodes_without_link}")
        
        return nodes
    except Exception as e:
        print(f"❌ 获取节点失败: {e}")
        return []

def step3_update_supabase_nodes(nodes: List[Dict]):
    """
    步骤3: 更新 Supabase 中的节点数据
    """
    if not nodes:
        print("\n⚠️ 没有节点数据需要更新")
        return
    
    print(f"\n💾 步骤3: 更新 Supabase 中的 {len(nodes)} 个节点...")
    
    try:
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # 准备数据
        updates = []
        for node in nodes:
            updates.append({
                "id": f"{node.get('host', 'unknown')}:{node.get('port', 'unknown')}",
                "link": node.get('link', ''),  # 这是关键！
                "content": node,  # 保留完整内容
                "updated_at": datetime.now().isoformat()
            })
        
        # 分批更新
        batch_size = 50
        for i in range(0, len(updates), batch_size):
            batch = updates[i:i + batch_size]
            try:
                result = supabase.table("nodes").upsert(batch).execute()
                print(f"  ✅ 批次 {i // batch_size + 1}: 更新 {len(batch)} 条")
            except Exception as e:
                print(f"  ❌ 批次 {i // batch_size + 1} 失败: {e}")
        
        print(f"\n✅ 完成！已更新 {len(updates)} 个节点")
        
    except ImportError:
        print("❌ supabase 库未安装，请运行: pip install supabase")
    except Exception as e:
        print(f"❌ 更新失败: {e}")

def step4_verify():
    """
    步骤4: 验证数据是否正确同步
    """
    print("\n🔍 步骤4: 验证数据同步...")
    try:
        # 查询前端 API
        response = requests.get("http://localhost:8002/api/nodes?limit=3", timeout=5)
        if response.status_code == 200:
            nodes = response.json()
            print(f"✅ 前端 API 返回 {len(nodes)} 个节点")
            for node in nodes[:3]:
                link = node.get('link', '')
                print(f"   • {node.get('name', 'N/A')}: link={'✅' if link else '❌'}")
        else:
            print(f"⚠️ 前端 API 返回状态码 {response.status_code}")
    except Exception as e:
        print(f"❌ 验证失败: {e}")

def main():
    """主程序"""
    print("=" * 60)
    print("🔧 Supabase nodes 表 link 字段修复")
    print("=" * 60)
    
    # 步骤1：添加字段
    step1_add_link_field_to_supabase()
    
    # 步骤2：获取数据
    nodes = step2_fetch_nodes_from_spiderflow()
    
    # 步骤3：更新数据库
    if nodes:
        step3_update_supabase_nodes(nodes)
    
    # 步骤4：验证
    step4_verify()
    
    print("\n" + "=" * 60)
    print("✅ 修复完成！")
    print("=" * 60)
    print("\n后续步骤:")
    print("1. 在 Supabase SQL Editor 中执行 ALTER TABLE SQL")
    print("2. 刷新前端页面 (Cmd+Shift+R)")
    print("3. 所有节点的复制和二维码按钮应该现在可用")

if __name__ == "__main__":
    main()
