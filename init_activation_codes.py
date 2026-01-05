#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
初始化 Supabase 激活码系统
"""

import os
from datetime import datetime, timedelta
from supabase import create_client, Client

# Supabase 配置
SUPABASE_URL = "https://hnlkwtkxbqiakeyienok.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhubGt3dGt4YnFpYWtleWllbm9rIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjY5MDQwNTksImV4cCI6MjA4MjQ4MDA1OX0.Xg9vQdUfBdUW-IJaomEIRGsX6tB_k2grhrF4dm_aNME"
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", SUPABASE_KEY)

# 初始化 Supabase 客户端（使用 Service Key 获得更高权限）
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def create_activation_codes_table():
    """创建激活码表"""
    print("📋 创建 activation_codes 表...")
    
    # 这个需要通过 SQL 执行，但 Python SDK 可能没有直接的 SQL 执行能力
    # 我们可以尝试直接在 Supabase 仪表板中执行，或者通过 admin API
    
    sql = """
    CREATE TABLE IF NOT EXISTS activation_codes (
        id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
        code VARCHAR(20) UNIQUE NOT NULL,
        vip_days INT DEFAULT 30,
        used BOOLEAN DEFAULT FALSE,
        used_by UUID,
        created_at TIMESTAMP DEFAULT NOW(),
        expires_at TIMESTAMP DEFAULT (NOW() + INTERVAL '90 days'),
        used_at TIMESTAMP,
        notes TEXT
    );
    
    CREATE INDEX IF NOT EXISTS idx_activation_codes_code ON activation_codes(code);
    CREATE INDEX IF NOT EXISTS idx_activation_codes_used ON activation_codes(used);
    """
    
    print("⚠️ 请在 Supabase 仪表板中手动执行以下 SQL:")
    print(sql)
    print()

def generate_test_codes():
    """生成测试激活码"""
    print("🔑 生成测试激活码...")
    
    test_codes = [
        {"code": "VIP7-2024-TEST-001", "vip_days": 7, "notes": "7天 VIP 测试码"},
        {"code": "VIP30-2024-TEST-001", "vip_days": 30, "notes": "30天 VIP 测试码"},
        {"code": "VIP90-2024-TEST-001", "vip_days": 90, "notes": "90天 VIP 测试码"},
        {"code": "VIP365-2024-TEST-001", "vip_days": 365, "notes": "1年 VIP 测试码"},
    ]
    
    for code_data in test_codes:
        try:
            # 插入激活码
            result = supabase.table("activation_codes").insert({
                "code": code_data["code"],
                "vip_days": code_data["vip_days"],
                "notes": code_data["notes"],
                "expires_at": (datetime.utcnow() + timedelta(days=90)).isoformat()
            }).execute()
            
            print(f"✅ 已创建: {code_data['code']} ({code_data['notes']})")
        except Exception as e:
            if "duplicate" in str(e).lower():
                print(f"⏭️ 已存在: {code_data['code']}")
            else:
                print(f"❌ 创建失败 {code_data['code']}: {e}")

def list_codes():
    """列出所有激活码"""
    print("\n📜 当前激活码列表:")
    print("-" * 60)
    
    try:
        result = supabase.table("activation_codes").select("*").execute()
        
        if not result.data:
            print("暂无激活码")
            return
        
        for code in result.data:
            status = "✅ 未使用" if not code.get("used") else f"❌ 已使用 (用户: {code.get('used_by')})"
            print(f"• {code['code']}: {code['vip_days']}天 {status}")
            if code.get("notes"):
                print(f"  备注: {code['notes']}")
            print()
    except Exception as e:
        print(f"❌ 查询失败: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("初始化 Supabase 激活码系统")
    print("=" * 60)
    print()
    
    create_activation_codes_table()
    generate_test_codes()
    list_codes()
    
    print()
    print("=" * 60)
    print("✅ 初始化完成！")
    print("=" * 60)
    print()
    print("🧪 测试激活码:")
    print("   VIP7-2024-TEST-001   (7天)")
    print("   VIP30-2024-TEST-001  (30天)")
    print("   VIP90-2024-TEST-001  (90天)")
    print("   VIP365-2024-TEST-001 (1年)")
