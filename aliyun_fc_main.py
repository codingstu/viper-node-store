from flask import Flask, request, jsonify
import socket
import time
import json

app = Flask(__name__)

# 校验暗号，保持与 GitHub Secret 一致
SECRET = "viper-aliyun-2025"

@app.route('/', methods=['POST'])
def probe():
    # 1. 鉴权 - 优先检查 URL 参数，其次检查请求头
    client_secret = request.args.get('secret') or request.headers.get('x-secret')
    if client_secret != SECRET:
        return jsonify({"error": "Unauthorized", "received": client_secret}), 401

    # 2. 获取节点列表
    try:
        nodes = request.get_json()
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
