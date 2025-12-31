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
      
      // 将 latency 转换为 score（延迟越低，分数越高）
      const scoredResults = allResults.map(result => {
        let score = 0;
        if (result.success && result.latency > 0) {
          // 延迟转分数：0-100ms -> 100分，100-300ms -> 80分，300-500ms -> 60分，500ms以上 -> 40分
          if (result.latency < 100) score = 100;
          else if (result.latency < 300) score = Math.max(80, 100 - (result.latency - 100) / 200 * 20);
          else if (result.latency < 500) score = Math.max(60, 80 - (result.latency - 300) / 200 * 20);
          else score = Math.max(40, 60 - (result.latency - 500) / 500 * 20);
        }
        return {
          id: result.id,
          host: result.host,
          port: result.port,
          latency: result.latency,
          score: Math.round(score),
          success: result.success,
          region: 'Global'
        };
      });
      
      return new Response(JSON.stringify(scoredResults), {
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
