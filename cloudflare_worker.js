/**
 * Cloudflare Worker: 回国节点国外测速
 * 部署到: https://your-worker.your-account.workers.dev
 * 
 * 用途: 为回国节点（CN 类）进行国外网络延迟测速
 */

export default {
  async fetch(request, env, ctx) {
    // 只接受 POST 请求
    if (request.method !== 'POST') {
      return new Response('Method not allowed', { status: 405 });
    }

    try {
      const data = await request.json();
      const nodes = data.nodes || [];

      if (!nodes.length) {
        return new Response(JSON.stringify({ error: 'No nodes provided' }), {
          status: 400,
          headers: { 'Content-Type': 'application/json' }
        });
      }

      const results = [];

      // 并发测试所有节点（Cloudflare Workers 天然支持）
      const promises = nodes.map(async (node) => {
        const { id, host, port } = node;
        const start = Date.now();

        try {
          // 使用 fetch 进行 HTTP 连接测试（比 TCP 握手更真实）
          const response = await fetch(`http://${host}:${port || 80}/`, {
            method: 'HEAD',
            timeout: 2500,
            cf: {
              cacheTtl: 0,
              mirage: false,
              minify: { javascript: false, css: false, html: false }
            }
          }).catch(() => null);

          const latency = Date.now() - start;
          const success = response && (response.status === 200 || response.status === 405);

          return {
            id,
            host,
            port,
            latency: success ? latency : -1,
            success: !!success,
            region: 'Global' // Cloudflare 节点遍布全球
          };
        } catch (e) {
          return {
            id,
            host,
            port,
            latency: -1,
            success: false,
            error: e.message
          };
        }
      });

      const allResults = await Promise.all(promises);
      
      return new Response(JSON.stringify(allResults), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });

    } catch (e) {
      return new Response(
        JSON.stringify({ error: e.message, type: 'ParseError' }),
        { status: 500, headers: { 'Content-Type': 'application/json' } }
      );
    }
  }
};
