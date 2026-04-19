const http = require("http");
const fs = require("fs");
const path = require("path");

const PORT = 5000;

const routes = [
  require("./features/markets/routes"),
  require("./features/candles/routes"),
  require("./features/ticker/routes"),
];

const server = http.createServer(async (req, res) => {
  const parsed = new URL(req.url, `http://localhost:${PORT}`);
  const pathname = parsed.pathname;
  const query = Object.fromEntries(parsed.searchParams);

  res.setHeader("Access-Control-Allow-Origin", "*");

  const route = routes.find((r) => r.path === pathname);
  if (route) {
    try {
      await route.handle(req, res, query);
    } catch (err) {
      res.writeHead(500);
      res.end(JSON.stringify({ error: err.message }));
    }
    return;
  }

  // Static files
  let filePath;
  if (pathname === "/" || pathname === "/index.html") {
    filePath = path.join(__dirname, "templates", "index.html");
  } else {
    filePath = path.join(__dirname, "static", pathname);
  }

  fs.readFile(filePath, (err, content) => {
    if (err) {
      res.writeHead(404);
      return res.end("Not found");
    }
    const ext = path.extname(filePath);
    const mime = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css" };
    res.setHeader("Content-Type", mime[ext] || "text/plain");
    res.end(content);
  });
});

server.listen(PORT, () => {
  console.log(`✅ 업비트 차트 서버 실행 중: http://localhost:${PORT}`);
});
