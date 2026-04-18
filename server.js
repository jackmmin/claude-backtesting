const http = require("http");
const fs = require("fs");
const path = require("path");
const { handleUpbitRoutes } = require("./routes/upbit");

const PORT = 5000;

const server = http.createServer(async (req, res) => {
  const parsed = new URL(req.url, `http://localhost:${PORT}`);
  const pathname = parsed.pathname;
  const query = Object.fromEntries(parsed.searchParams);

  res.setHeader("Access-Control-Allow-Origin", "*");

  try {
    const handled = await handleUpbitRoutes(req, res, pathname, query);
    if (handled !== false) return;
  } catch (err) {
    res.writeHead(500);
    return res.end(JSON.stringify({ error: err.message }));
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
