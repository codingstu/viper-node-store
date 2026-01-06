export default {
  async fetch(request) {
    const url = new URL(request.url);
    const targetDomain = "node.peachx.tech";
    
    // 检查是否已访问过
    const hasVisited = request.headers.get('cookie')?.includes('visited=true');

    // 首次访问显示加载页
    if (!hasVisited) {
      const html = `
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="UTF-8">
          <style>
            body { 
              background: #000; 
              margin: 0; 
              display: flex;
              align-items: center;
              justify-content: center;
              height: 100vh;
            }
            .loader { 
              border: 3px solid #333; 
              border-top: 3px solid #0f0; 
              border-radius: 50%; 
              width: 50px; 
              height: 50px; 
              animation: spin 1s linear infinite;
            }
            @keyframes spin { to { transform: rotate(360deg); } }
          </style>
        </head>
        <body>
          <div class="loader"></div>
          <script>
            setTimeout(() => {
              document.cookie = 'visited=true; path=/';
              location.reload();
            }, 1500);
          </script>
        </body>
        </html>
      `;
      return new Response(html, { 
        status: 200,
        headers: { "content-type": "text/html;charset=UTF-8" } 
      });
    }

    // 已访问：代理到目标网站
    url.hostname = targetDomain;

    const newRequest = new Request(url, {
      method: request.method,
      headers: request.headers,
      body: request.body,
      redirect: 'follow'
    });

    newRequest.headers.set("Host", targetDomain);
    newRequest.headers.delete("X-Forwarded-Host");
    newRequest.headers.delete("X-Real-IP");

    const response = await fetch(newRequest);

    const finalResponse = new Response(response.body, response);
    finalResponse.headers.set("Access-Control-Allow-Origin", "*");
    finalResponse.headers.set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS, PATCH");
    finalResponse.headers.set("Access-Control-Allow-Headers", "*");

    return finalResponse;
  }
};