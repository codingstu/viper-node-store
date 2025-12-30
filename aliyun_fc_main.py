from flask import Flask, request, jsonify
import socket
import time
import json

app = Flask(__name__)

# 校验暗号，保持与 GitHub Secret 一致
SECRET = "viper-aliyun-2025"

@app.route('/', methods=['POST'])
def probe():
    # 1. 鉴权 - 从 POST body 中读取密钥
    data = request.get_json()
    if not data:
        return jsonify({"error": "Empty request body", "received_data": None}), 400
    
    client_secret = data.get('secret')
    
    # 调试：返回收到的 secret 信息
    if client_secret != SECRET:
        return jsonify({
            "error": "Unauthorized", 
            "expected_secret_type": type(SECRET).__name__,
            "received_secret_type": type(client_secret).__name__,
            "received_secret_length": len(client_secret) if client_secret else 0,
            "received_secret_first_10": client_secret[:10] if client_secret else None,
            "data_keys": list(data.keys())
        }), 401

    # 2. 获取节点列表
    try:
        nodes = data.get('nodes', [])
        results = []

        for node in nodes:
            host = node.get('host')
            port = int(node.get('port'))
            node_id = node.get('id')

            start = time.perf_counter()
            success = False
            try:
                # 真实 TCP 握手测试
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(2.5)
                res = s.connect_ex((host, port))
                success = (res == 0)
                s.close()
            except:
                success = False

            latency = int((time.perf_counter() - start) * 1000) if success else -1
            results.append({
                "id": node_id,
                "latency": latency,
                "success": success
            })

        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=9000)
