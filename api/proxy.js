export default async function handler(req, res) {
  const { url } = req.query;

  if (!url) {
    return res.status(400).send("Missing url");
  }

  try {
    const response = await fetch(url, {
      headers: {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://edge.cdn-live.ru/"
      }
    });

    const contentType = response.headers.get("content-type") || "";

    // --- HANDLE M3U8 ---
    if (contentType.includes("mpegurl")) {
      const body = await response.text();
      const base = `https://${req.headers.host}`;

      const rewritten = body.split("\n").map(line => {
        if (line.startsWith("#") || !line.trim()) return line;

        const absolute = new URL(line, url).href;

        return `${base}/api/proxy?url=${encodeURIComponent(absolute)}`;
      }).join("\n");

      res.setHeader("Content-Type", "application/vnd.apple.mpegurl");
      res.setHeader("Access-Control-Allow-Origin", "*");

      return res.status(200).send(rewritten);
    }

    // --- HANDLE VIDEO SEGMENTS ---
    const buffer = await response.arrayBuffer();

    res.setHeader("Content-Type", contentType);
    res.setHeader("Access-Control-Allow-Origin", "*");

    // 🔥 ADD THESE (CRITICAL FOR JELLYFIN)
    res.setHeader("Accept-Ranges", "bytes");

    const contentLength = response.headers.get("content-length");
    if (contentLength) {
      res.setHeader("Content-Length", contentLength);
    }

    return res.status(200).send(Buffer.from(buffer));

  } catch (e) {
    console.error(e);
    res.status(500).send("Proxy error");
  }
}
