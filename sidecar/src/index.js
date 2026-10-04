// POOL iMessage sidecar. Only process that talks to Photon.
// Receives Spectrum messages, forwards normalized JSON to the Python agent,
// exposes POST /send so Python can reply. No trading logic here.
//
// Photon API notes (Stable docs, connection-and-routing):
// - inbound narrowing: imessage(space), imessage(message); sender via imessage(message).sender
// - outbound: imessage(app).user(phone) -> im.space.create(user) -> space.send(text)
// - quotas: 5,000 msgs/server/day; 50 new conversations/line/day
import http from "node:http";
import { Spectrum } from "spectrum-ts";
import { imessage } from "spectrum-ts/providers/imessage";

const PROJECT_ID = process.env.SPECTRUM_PROJECT_ID;
const PROJECT_SECRET = process.env.SPECTRUM_PROJECT_SECRET;
const AGENT_URL = process.env.POOL_AGENT_URL ?? "http://127.0.0.1:8000/internal/inbound";
const SIDECAR_SECRET = process.env.POOL_SIDECAR_SECRET ?? "";
const PORT = Number(process.env.PORT ?? 8788);

if (!PROJECT_ID || !PROJECT_SECRET) {
  console.error("missing SPECTRUM_PROJECT_ID / SPECTRUM_PROJECT_SECRET");
  process.exit(1);
}

const app = await Spectrum({
  projectId: PROJECT_ID,
  projectSecret: PROJECT_SECRET,
  providers: [imessage.config()],
});

const seen = new Set();
const spaces = new Map(); // phone -> Space (DMs are stable per line)

async function forwardToAgent(phone, text, messageId) {
  if (messageId && seen.has(messageId)) return;
  if (messageId) {
    seen.add(messageId);
    if (seen.size > 2000) seen.clear();
  }
  const res = await fetch(AGENT_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json", "x-sidecar-secret": SIDECAR_SECRET },
    body: JSON.stringify({ phone, text, messageId }),
  });
  if (!res.ok) console.error("agent forward failed", res.status, await res.text());
}

// Inbound: Spectrum stream -> Python
(async () => {
  for await (const [space, message] of app.messages) {
    try {
      if (message.platform !== "imessage") continue;
      if (message.content?.type !== "text") continue;
      const im = imessage(space);
      spaces.set(im.phone, space); // cache live space for replies
      const sender = imessage(message).sender;
      const phone = sender?.address ?? sender?.id ?? space.id;
      await forwardToAgent(phone, message.content.text ?? "", message.id);
    } catch (e) {
      console.error("inbound error", e);
    }
  }
})();

async function spaceFor(phone) {
  if (spaces.has(phone)) return spaces.get(phone);
  const im = imessage(app);
  const user = await im.user(phone);
  const space = await im.space.create(user); // DM; counts toward 50 new convos/line/day
  spaces.set(phone, space);
  return space;
}

// Outbound: Python -> space.send
const server = http.createServer(async (req, res) => {
  if (req.method === "POST" && req.url === "/send") {
    if (SIDECAR_SECRET && req.headers["x-sidecar-secret"] !== SIDECAR_SECRET) {
      res.writeHead(401).end("bad secret");
      return;
    }
    let body = "";
    for await (const chunk of req) body += chunk;
    const { phone, texts } = JSON.parse(body || "{}");
    if (!phone || !Array.isArray(texts)) {
      res.writeHead(400).end("need {phone, texts[]}");
      return;
    }
    try {
      const space = await spaceFor(phone);
      for (const t of texts) await space.send(t);
      res.writeHead(200, { "Content-Type": "application/json" }).end(JSON.stringify({ ok: true }));
    } catch (e) {
      console.error("send error", e);
      res.writeHead(500).end("send failed");
    }
    return;
  }
  if (req.method === "GET" && req.url === "/health") {
    res.writeHead(200).end("ok");
    return;
  }
  res.writeHead(404).end("not found");
});

server.listen(PORT, () => console.log(`pool sidecar on :${PORT}`));
