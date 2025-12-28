import requests
import os
from datetime import datetime
from supabase import create_client, Client

# 从环境变量获取配置
API_URL = os.environ["SHADOW_VIPER_API"]
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

# 连接数据库
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def update():
    print("正在拉取新节点...")
    try:
        # 1. 拉取数据
        resp = requests.get(API_URL, timeout=15)
        if resp.status_code != 200:
            print("API 请求失败")
            return
        
        new_nodes = resp.json()
        
        # 2. 简单清洗和排序
        # 假设 API 返回里有 speed 字段，或者你自己测速后排序
        # 这里演示：直接按列表顺序，前20个免费
        
        data_to_upsert = []
        for index, node in enumerate(new_nodes):
            # 唯一标识符
            node_id = f"{node['host']}:{node['port']}"
            
            # 核心逻辑：前20个设为免费
            is_free = True if index < 20 else False
            
            data_to_upsert.append({
                "id": node_id,
                "content": node,        # 完整存进去
                "is_free": is_free,     # 权限标记
                "speed": node.get('speed', 0),
                "updated_at": datetime.now().isoformat()
            })

        # 3. 批量写入 Supabase
        # Supabase 建议分批写入，避免包太大
        batch_size = 100
        for i in range(0, len(data_to_upsert), batch_size):
            batch = data_to_upsert[i:i+batch_size]
            supabase.table("nodes").upsert(batch).execute()
            
        print(f"成功更新数据库: {len(data_to_upsert)} 个节点")

        # 4. (可选) 清理旧节点
        # supabase.table("nodes").delete().lt("updated_at", "2023-01-01...").execute()

    except Exception as e:
        print(f"脚本执行出错: {e}")

if __name__ == "__main__":
    update()
