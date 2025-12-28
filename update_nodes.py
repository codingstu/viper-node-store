import requests
import os
import json
from datetime import datetime
from supabase import create_client, Client

# 从环境变量获取配置
API_URL = os.environ["SHADOW_VIPER_API"]
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

# 连接数据库
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def update():
    print("🚀 正在拉取新节点...")
    try:
        # 🔥 修改处：将 timeout 从 30 改为 120 (秒)
        # 给后端更多时间去处理数据或进行测速
        resp = requests.get(API_URL, timeout=120)
        
        if resp.status_code != 200:
            print(f"❌ API 请求失败: {resp.status_code}")
            return
        
        new_nodes = resp.json()
        print(f"📦 获取到 {len(new_nodes)} 个节点")
        
        data_to_upsert = []
        
        # 🟢 1. 处理所有数据准备入库
        for index, node in enumerate(new_nodes):
            node_id = f"{node['host']}:{node['port']}"
            
            # 设定前 10 个为免费，其余为付费
            is_free = True if index < 10 else False
            
            # 处理速度字段
            try:
                raw_speed = node.get('speed', 0)
                speed_int = int(float(raw_speed))
            except (ValueError, TypeError):
                speed_int = 0
            
            data_to_upsert.append({
                "id": node_id,
                "content": node,        
                "is_free": is_free,     
                "speed": speed_int,     
                "updated_at": datetime.now().isoformat()
            })

        # 🟢 2. 全部写入 Supabase (真数据)
        if data_to_upsert:
            batch_size = 100
            for i in range(0, len(data_to_upsert), batch_size):
                batch = data_to_upsert[i:i+batch_size]
                supabase.table("nodes").upsert(batch).execute()
            print(f"✅ 数据库更新成功: {len(data_to_upsert)} 条数据")

        # 🟢 3. 生成 '阉割版' public/nodes.json (只含前 5 个)
        os.makedirs("public", exist_ok=True)
        safe_nodes = new_nodes[:5] 
        
        with open("public/nodes.json", "w", encoding="utf-8") as f:
            json.dump(safe_nodes, f, indent=2, ensure_ascii=False)
        print(f"🛡️ 安全文件生成成功 (仅包含 {len(safe_nodes)} 个试用节点)")

    except Exception as e:
        print(f"❌ 脚本执行出错: {e}")
        exit(1)

if __name__ == "__main__":
    update()
