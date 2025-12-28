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
        
        data_to_upsert = []
        for index, node in enumerate(new_nodes):
            # 唯一标识符
            node_id = f"{node['host']}:{node['port']}"
            
            # 前20个设为免费
            is_free = True if index < 20 else False
            
            # 🟢 修复核心：安全处理 speed 字段
            # API 可能会返回 "15.1" (字符串) 或 15.1 (浮点数)
            # 我们统一先转 float，再转 int (丢弃小数)，确保它是整数
            try:
                raw_speed = node.get('speed', 0)
                speed_int = int(float(raw_speed))
            except (ValueError, TypeError):
                speed_int = 0
            
            data_to_upsert.append({
                "id": node_id,
                "content": node,        # 完整存进去
                "is_free": is_free,     # 权限标记
                "speed": speed_int,     # ✅ 这里存的是处理后的整数
                "updated_at": datetime.now().isoformat()
            })

        # 3. 批量写入 Supabase
        batch_size = 100
        for i in range(0, len(data_to_upsert), batch_size):
            batch = data_to_upsert[i:i+batch_size]
            supabase.table("nodes").upsert(batch).execute()
            
        print(f"成功更新数据库: {len(data_to_upsert)} 个节点")

    except Exception as e:
        print(f"脚本执行出错: {e}")

if __name__ == "__main__":
    update()
