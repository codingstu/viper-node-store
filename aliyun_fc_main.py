from flask import Flask, request, jsonify
import socket
import time
import json

app = Flask(__name__)

@app.route('/', methods=['POST'])
def probe():
    """
    阿里云函数：大陆节点测速
    输入: {"nodes": [{"id": "...", "host": "...", "port": 443}, ...]}
    输出: [{"id": "...", "latency": 100, "success": true}, ...]
    """
    try:
        # 直接从 POST body 获取节点列表
        data = request.get_json()
        if not data:
            return jsonify({"error": "Empty request body"}), 400
        
        nodes = data.get('nodes', [])
        if not nodes:
            return jsonify({"error": "No nodes to test"}), 400
        
        results = []

        for node in nodes:
            host = node.get('host')
            port = node.get('port')
            node_id = node.get('id')
            
            if not host or not port:
                results.append({
                    "id": node_id,
                    "latency": -1,
                    "success": False,
                    "error": "Missing host or port"
                })
                continue

            start = time.perf_counter()
            success = False
            try:
                # 真实 TCP 握手测试
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(2.5)
                res = s.connect_ex((host, int(port)))
                success = (res == 0)
                s.close()
            except Exception as e:
                success = False

            latency = int((time.perf_counter() - start) * 1000) if success else -1
            results.append({
                "id": node_id,
                "latency": latency,
                "success": success
            })

        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e), "error_type": type(e).__name__}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=9000)
