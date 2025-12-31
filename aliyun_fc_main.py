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
            
            # 将延迟转换为分数
            score = 0
            if success and latency > 0:
                # 延迟转分数：0-100ms -> 100分，100-300ms -> 80分，300-500ms -> 60分，500ms以上 -> 40分
                if latency < 100:
                    score = 100
                elif latency < 300:
                    score = max(80, 100 - (latency - 100) / 200 * 20)
                elif latency < 500:
                    score = max(60, 80 - (latency - 300) / 200 * 20)
                else:
                    score = max(40, 60 - (latency - 500) / 500 * 20)
            
            results.append({
                "id": node_id,
                "latency": latency,
                "score": int(score),
                "success": success
            })

        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e), "error_type": type(e).__name__}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=9000)
