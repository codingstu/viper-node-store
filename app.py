#!/usr/bin/env python3
"""
Simple proxy server to bypass CORS issues with Supabase API
"""
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json
import urllib.request

SUPABASE_URL = 'https://RLS.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhubGt3dGt4YnFpYWtleWllbm9rIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjY5MDQwNTksImV4cCI6MjA4MjQ4MDA1OX0.Xg9vQdUfBdUW-IJaomEIRGsX6tB_k2grhrF4dm_aNME'

class ProxyHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        # 处理 /api/nodes 代理请求
        if self.path.startswith('/api/nodes'):
            try:
                # 构造 Supabase URL
                supabase_url = f'{SUPABASE_URL}/rest/v1/nodes?limit=100'
                
                # 发送请求到 Supabase
                req = urllib.request.Request(
                    supabase_url,
                    headers={
                        'apikey': SUPABASE_KEY,
                        'Authorization': f'Bearer {SUPABASE_KEY}',
                        'Content-Type': 'application/json'
                    }
                )
                
                with urllib.request.urlopen(req) as response:
                    data = response.read().decode('utf-8')
                    
                    # 返回结果给客户端
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(data.encode('utf-8'))
                return
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                error_response = json.dumps({'error': str(e)})
                self.wfile.write(error_response.encode('utf-8'))
                return
        
        # 处理静态文件
        super().do_GET()

    def do_OPTIONS(self):
        # 处理 CORS 预检请求
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

if __name__ == '__main__':
    server_address = ('', 8080)
    httpd = HTTPServer(server_address, ProxyHandler)
    print('Server running on http://localhost:8080')
    httpd.serve_forever()
