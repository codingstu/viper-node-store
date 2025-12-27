# update_nodes.py
import requests
import json
import os
from datetime import datetime

# 配置
SHADOW_VIPER_API = os.environ["SHADOW_VIPER_API"] # 从环境变量读取
DATA_FILE = "public/nodes.json" # 数据存放在 public 目录，方便前端读取
MAX_NODES = 800

def update():
    # 1. 读取旧数据
    old_nodes = []
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                old_nodes = json.load(f)
        except:
            pass
            
    # 转为字典方便去重 { "host:port": node_dict }
    node_map = {f"{n['host']}:{n['port']}": n for n in old_nodes}
    
    # 2. 从 Azure 拉取新数据
    print("正在从 Shadow Viper 拉取...")
    try:
        resp = requests.get(SHADOW_VIPER_API, timeout=10)
        if resp.status_code == 200:
            new_nodes = resp.json()
            print(f"拉取到 {len(new_nodes)} 个新节点")
            
            for node in new_nodes:
                key = f"{node['host']}:{node['port']}"
                node['updated_at'] = datetime.now().isoformat()
                # 更新或插入
                node_map[key] = node
        else:
            print("拉取失败")
    except Exception as e:
        print(f"请求错误: {e}")

    # 3. 排序与截断 (保留最新的 800 个)
    # 按 updated_at 倒序
    all_nodes = list(node_map.values())
    all_nodes.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
    
    final_nodes = all_nodes[:MAX_NODES]
    
    # 4. 保存文件
    os.makedirs("public", exist_ok=True)
    with open(DATA_FILE, 'w') as f:
        json.dump(final_nodes, f, indent=2, ensure_ascii=False)
    
    print(f"更新完成，当前库存: {len(final_nodes)}")

if __name__ == "__main__":
    update()
