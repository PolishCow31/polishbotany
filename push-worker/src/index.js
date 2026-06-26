// botany-push — always-on Web Push sender for Botany (the AI tracker).
// Botany's static site is on GitHub Pages (no backend), so this standalone Cloudflare Worker holds
// subscriptions (KV) and sends. A cron polls Botany's PUBLIC data each hour and pushes on:
//   (1) a new model, (2) breaking news (new news item), (3) a new #1 on the AA Index.
// PushForge handles VAPID signing + RFC-8291 encryption. Mirrors the CyMCAT push worker, but
// KV-backed (not D1) and cross-origin (the PWA POSTs subscriptions here from github.io).
import { buildPushHTTPRequest } from "@pushforge/builder";

const SUBJECT   = "mailto:cozog02@gmail.com";
const DATA_BASE = "https://polishcow31.github.io/polishbotany/data";
const ORIGIN    = "https://polishcow31.github.io";   // CORS: the Botany PWA origin

const cors = {
  "Access-Control-Allow-Origin": ORIGIN,
  "Access-Control-Allow-Methods": "POST, DELETE, OPTIONS",
  "Access-Control-Allow-Headers": "content-type",
};
const json = (o, status) => new Response(JSON.stringify(o), {
  status: status || 200, headers: { "content-type": "application/json", ...cors }
});
const subKey = (endpoint) => "sub:" + endpoint;

async function listSubs(env) {
  const out = []; let cursor;
  while (true) {
    const r = await env.SUBS.list({ prefix: "sub:", cursor });
    for (const k of r.keys) { const v = await env.SUBS.get(k.name); if (v) out.push(JSON.parse(v)); }
    if (r.list_complete) break;
    cursor = r.cursor;
  }
  return out;
}

async function sendToAll(env, payload) {
  const subs = await listSubs(env);
  if (!subs.length) return { subs: 0, sent: 0, dead: 0, errors: 0 };
  let privateJWK;
  try { privateJWK = JSON.parse(env.VAPID_PRIVATE_JWK); }
  catch (e) { return { error: "VAPID_PRIVATE_JWK secret missing or not JSON" }; }
  let sent = 0, dead = 0, errors = 0;
  for (const s of subs) {
    try {
      const { endpoint, headers, body } = await buildPushHTTPRequest({
        privateJWK,
        subscription: { endpoint: s.endpoint, keys: { p256dh: s.p256dh, auth: s.auth } },
        message: { payload, adminContact: SUBJECT }
      });
      const res = await fetch(endpoint, { method: "POST", headers, body });
      if (res.status === 404 || res.status === 410) { await env.SUBS.delete(subKey(s.endpoint)); dead++; }
      else if (res.ok) sent++;
      else errors++;
    } catch (e) { errors++; }
  }
  return { subs: subs.length, sent, dead, errors };
}

// Fetch Botany's public data and diff against the stored snapshot; push on real changes.
async function poll(env) {
  let models, news;
  try {
    models = await (await fetch(DATA_BASE + "/models.json", { cf: { cacheTtl: 0 } })).json();
    news   = await (await fetch(DATA_BASE + "/news.json",   { cf: { cacheTtl: 0 } })).json();
  } catch (e) { return { error: "data fetch failed" }; }

  const mlist = models.models || models || [];
  const names = mlist.map(m => m.name).filter(Boolean);
  const aa = m => (m.benchmarks && (m.benchmarks["AA-Index"] ?? m.benchmarks.aa));
  const live = mlist.filter(m => m.status === "live" && aa(m) != null);
  const top = live.slice().sort((a, b) => aa(b) - aa(a))[0];
  const topName = top ? top.name : null, topAA = top ? aa(top) : null;
  const newsItems = news.items || news || [];
  const newsIds = newsItems.map(n => n.url || n.title).filter(Boolean);

  const prevRaw = await env.SUBS.get("state:lastseen");
  const prev = prevRaw ? JSON.parse(prevRaw) : null;
  const snap = { names, top: topName, topAA, news: newsIds };
  if (!prev) { await env.SUBS.put("state:lastseen", JSON.stringify(snap)); return { first: true, models: names.length }; }

  const out = { newModels: 0, rankChange: false, newNews: 0 };
  const newModels = names.filter(n => !prev.names.includes(n));
  if (newModels.length) {
    out.newModels = newModels.length;
    const head = newModels.slice(0, 2).join(", ");
    const body = newModels.length === 1 ? newModels[0] + " was just added."
      : `${newModels.length} new models: ${head}${newModels.length > 2 ? ` +${newModels.length - 2} more` : ""}.`;
    await sendToAll(env, { title: "New AI model", body, url: "/", tag: "botany-model" });
  }
  if (topName && prev.top && topName !== prev.top) {
    out.rankChange = true;
    await sendToAll(env, { title: "New #1 on the AA Index", body: `${topName} now leads${topAA != null ? ` at ${topAA}` : ""}.`, url: "/", tag: "botany-rank" });
  }
  const newNews = newsItems.filter(n => !prev.news.includes(n.url || n.title));
  if (newNews.length) {
    out.newNews = newNews.length;
    const t = newNews[0].title || "New AI story";
    await sendToAll(env, { title: "Breaking AI news", body: newNews.length === 1 ? t : `${t} (+${newNews.length - 1} more)`, url: "/", tag: "botany-news" });
  }
  await env.SUBS.put("state:lastseen", JSON.stringify(snap));
  return out;
}

export default {
  async scheduled(event, env, ctx) { ctx.waitUntil(poll(env).catch(() => {})); },
  async fetch(req, env) {
    const url = new URL(req.url);
    if (req.method === "OPTIONS") return new Response(null, { headers: cors });
    if (url.pathname === "/subscribe" && req.method === "POST") {
      let sub; try { sub = await req.json(); } catch (e) { return json({ ok: false, error: "bad json" }, 400); }
      if (!sub || !sub.endpoint || !sub.keys || !sub.keys.p256dh || !sub.keys.auth) return json({ ok: false, error: "incomplete subscription" }, 400);
      await env.SUBS.put(subKey(sub.endpoint), JSON.stringify({ endpoint: sub.endpoint, p256dh: sub.keys.p256dh, auth: sub.keys.auth }));
      return json({ ok: true });
    }
    if (url.pathname === "/unsubscribe" && (req.method === "POST" || req.method === "DELETE")) {
      let b; try { b = await req.json(); } catch (e) { return json({ ok: false }, 400); }
      if (b && b.endpoint) await env.SUBS.delete(subKey(b.endpoint));
      return json({ ok: true });
    }
    const keyOK = env.TEST_KEY && url.searchParams.get("key") === env.TEST_KEY;
    if (url.pathname === "/test" && keyOK) return json(await sendToAll(env, { title: "Botany", body: "Push is working.", url: "/", tag: "botany-test" }));
    if (url.pathname === "/run" && keyOK) return json(await poll(env));
    return new Response("botany-push", { status: 200, headers: cors });
  }
};
