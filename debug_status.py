"""Backend self-diagnostics for the debug dashboard.

Each check runs in isolation and never raises — a failing dependency is reported
as an "error"/"warn" result rather than taking the whole endpoint down. The
dashboard HTML (served at /debug) polls collect_status() via /api/debug/status.

This is intentionally served by the backend itself (not the React frontend) so
it still works when the frontend, Vite, or nginx are broken.
"""
import os
import time
import asyncio
import socket
from datetime import datetime


# ---------------------------------------------------------------------------
# Result helpers
# ---------------------------------------------------------------------------
def _result(status: str, detail: str, t0: float, extra: dict | None = None) -> dict:
    r = {
        "status": status,  # "ok" | "warn" | "error"
        "detail": detail,
        "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
    }
    if extra:
        r["extra"] = extra
    return r


def _ok(detail, t0, extra=None):
    return _result("ok", detail, t0, extra)


def _warn(detail, t0, extra=None):
    return _result("warn", detail, t0, extra)


def _err(detail, t0, extra=None):
    return _result("error", detail, t0, extra)


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------
def check_database() -> dict:
    """Verify the Postgres connection with a trivial query."""
    t0 = time.perf_counter()
    try:
        from sqlalchemy import text
        from database import SessionLocal

        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
        finally:
            db.close()
        return _ok("Connected (SELECT 1 succeeded)", t0)
    except Exception as e:
        return _err(f"{type(e).__name__}: {e}", t0)


async def check_llm(ai_client) -> dict:
    """Verify the vLLM/OpenAI endpoint is reachable and serves the configured model."""
    t0 = time.perf_counter()
    try:
        resp = await asyncio.wait_for(ai_client.client.models.list(), timeout=8)
        ids = [m.id for m in resp.data]
        if ai_client.model in ids:
            return _ok(f"Reachable; model '{ai_client.model}' is served", t0, {"served_models": ids})
        return _warn(
            f"Reachable, but configured model '{ai_client.model}' is NOT served. Served: {ids}",
            t0,
            {"served_models": ids},
        )
    except Exception as e:
        return _err(f"Unreachable — {type(e).__name__}: {e}", t0)


def check_tts_japanese(tts_engine) -> dict:
    """Verify the baked-in Style-Bert-VITS2 model files exist (and note if loaded)."""
    t0 = time.perf_counter()
    try:
        from tts_sbv2 import _VOICE_CONFIG, _ASSETS_DIR, StyleBertVITS2Engine

        missing = []
        for gender, cfg in _VOICE_CONFIG.items():
            local_dir = _ASSETS_DIR / cfg["local_dir"]
            if not StyleBertVITS2Engine._model_files_exist(local_dir, cfg):
                missing.append(gender)

        loaded = bool(getattr(tts_engine, "_sbv2", None) and getattr(tts_engine._sbv2, "_models", None))

        if missing:
            return _err(f"Model files MISSING for: {missing} (not baked in?)", t0, {"loaded_in_memory": loaded})

        detail = "Model files present (baked into image)"
        if loaded:
            detail += "; engine loaded in memory"
        return _ok(detail, t0, {"loaded_in_memory": loaded})
    except Exception as e:
        return _err(f"{type(e).__name__}: {e}", t0)


def check_stt() -> dict:
    """Verify the speech-to-text library is importable."""
    t0 = time.perf_counter()
    try:
        import speech_recognition  # noqa: F401
        return _ok("SpeechRecognition importable", t0)
    except Exception as e:
        return _err(f"{type(e).__name__}: {e}", t0)


async def check_internet() -> dict:
    """Verify outbound HTTPS works (required for the Edge-TTS fallback)."""
    t0 = time.perf_counter()
    host = "speech.platform.bing.com"
    try:
        fut = asyncio.open_connection(host, 443)
        reader, writer = await asyncio.wait_for(fut, timeout=5)
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        return _ok(f"Outbound HTTPS to {host} OK (Edge-TTS fallback available)", t0)
    except Exception as e:
        # Not fatal: Japanese TTS is baked in; only fallback voices need this.
        return _warn(f"No outbound internet to {host} — Edge-TTS fallback will fail: {e}", t0)


# ---------------------------------------------------------------------------
# Aggregate
# ---------------------------------------------------------------------------
async def collect_status(ai_client, tts_engine, connections=None, errors=None) -> dict:
    database = check_database()
    stt = check_stt()
    tts_japanese = check_tts_japanese(tts_engine)
    llm, internet = await asyncio.gather(check_llm(ai_client), check_internet())

    checks = {
        "database": database,
        "llm_vllm": llm,
        "tts_japanese": tts_japanese,
        "stt": stt,
        "internet_edge_tts": internet,
    }

    overall = "ok"
    for c in checks.values():
        if c["status"] == "error":
            overall = "error"
            break
        if c["status"] == "warn":
            overall = "warn"

    return {
        "overall": overall,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "config": {
            "model": getattr(ai_client, "model", "?"),
            "vllm_url": os.environ.get("VLLM_URL", ""),
            "hostname": socket.gethostname(),
        },
        "checks": checks,
        "connections": connections or [],
        "errors": errors or [],
    }


# ---------------------------------------------------------------------------
# Dashboard HTML (self-contained; fetches /api/debug/status)
# ---------------------------------------------------------------------------
DEBUG_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Polyglot Backend — Debug</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body { margin:0; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
         background:#0b0f19; color:#e6edf3; padding:24px; }
  h1 { font-size:18px; margin:0 0 4px; }
  .sub { color:#8b98a9; font-size:12px; margin-bottom:20px; }
  .banner { padding:14px 18px; border-radius:10px; font-weight:700; font-size:15px;
            margin-bottom:20px; display:flex; align-items:center; gap:10px; }
  .banner.ok    { background:#0f2e1a; color:#4ade80; border:1px solid #1f6f3f; }
  .banner.warn  { background:#332a08; color:#fbbf24; border:1px solid #7a5c10; }
  .banner.error { background:#3a1113; color:#f87171; border:1px solid #7f1d1d; }
  .grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(320px,1fr)); gap:14px; }
  .card { background:#111827; border:1px solid #1f2937; border-radius:10px; padding:16px; }
  .card h2 { font-size:14px; margin:0 0 8px; display:flex; align-items:center; gap:8px; }
  .dot { width:10px; height:10px; border-radius:50%; flex:0 0 auto; }
  .dot.ok{background:#22c55e;} .dot.warn{background:#f59e0b;} .dot.error{background:#ef4444;}
  .detail { font-size:12px; color:#cbd5e1; line-height:1.5; word-break:break-word; }
  .meta { font-size:11px; color:#64748b; margin-top:8px; }
  .cfg { font-size:12px; color:#94a3b8; margin-bottom:18px; }
  .cfg b { color:#e2e8f0; }
  h3 { font-size:14px; margin:26px 0 12px; color:#e2e8f0; }
  table { width:100%; border-collapse:collapse; font-size:12px; }
  th, td { text-align:left; padding:8px 10px; border-bottom:1px solid #1f2937; }
  th { color:#64748b; font-weight:600; }
  td { color:#cbd5e1; }
  .badge { font-size:10px; padding:2px 7px; border-radius:999px; font-weight:700; }
  .badge.admin { background:#3b1d5e; color:#c4b5fd; }
  .badge.student { background:#0e3a4a; color:#7dd3fc; }
  .empty { color:#64748b; font-size:12px; padding:10px; }
  .err { background:#1a1113; border:1px solid #7f1d1d; border-radius:8px; padding:10px 12px; margin-bottom:8px; }
  .err .top { display:flex; justify-content:space-between; gap:10px; font-size:12px; }
  .err .ctx { color:#fca5a5; font-weight:700; }
  .err .when { color:#64748b; white-space:nowrap; }
  .err .msg { color:#fecaca; font-size:12px; margin-top:4px; word-break:break-word; }
  .err .tb { color:#7f8ea3; font-size:11px; margin-top:6px; white-space:pre-wrap; }
  button { background:#1f2937; color:#e6edf3; border:1px solid #374151; border-radius:8px;
           padding:6px 12px; font:inherit; cursor:pointer; }
  button:hover { background:#374151; }
  .row { display:flex; align-items:center; gap:12px; margin-bottom:18px; }
  .pill { font-size:11px; padding:2px 8px; border-radius:999px; background:#1f2937; color:#94a3b8; }
</style>
</head>
<body>
  <h1>Polyglot Backend — Debug Dashboard</h1>
  <div class="sub">Served directly by FastAPI. Works even if the frontend / nginx are down.</div>
  <div class="row">
    <button onclick="load()">Refresh now</button>
    <span class="pill" id="auto">auto-refresh: 5s</span>
    <span class="pill" id="ts">—</span>
  </div>
  <div id="banner" class="banner warn">Loading…</div>
  <div class="cfg" id="cfg"></div>
  <div class="grid" id="grid"></div>

  <h3>Active connections (<span id="conncount">0</span>)</h3>
  <div id="conns"></div>

  <h3>Recent errors (<span id="errcount">0</span>)</h3>
  <div id="errs"></div>

<script>
const LABELS = {
  database: "PostgreSQL Database",
  llm_vllm: "LLM (vLLM endpoint)",
  tts_japanese: "TTS — Japanese (SBV2)",
  stt: "Speech-to-Text",
  internet_edge_tts: "Internet / Edge-TTS fallback",
};
function esc(s){ return String(s).replace(/[&<>]/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c])); }
async function load(){
  try {
    const res = await fetch('/api/debug/status', {cache:'no-store'});
    const data = await res.json();
    render(data);
  } catch (e) {
    document.getElementById('banner').className = 'banner error';
    document.getElementById('banner').textContent = 'Cannot reach /api/debug/status — backend down? ' + e;
  }
}
function render(d){
  const b = document.getElementById('banner');
  b.className = 'banner ' + d.overall;
  b.textContent = d.overall === 'ok' ? 'All systems operational'
                : d.overall === 'warn' ? 'Degraded — some non-critical checks failing'
                : 'Problems detected — see red cards below';
  document.getElementById('ts').textContent = new Date(d.timestamp).toLocaleTimeString();
  document.getElementById('cfg').innerHTML =
    'Model: <b>'+esc(d.config.model)+'</b> &nbsp;·&nbsp; vLLM: <b>'+esc(d.config.vllm_url)+'</b> &nbsp;·&nbsp; host: <b>'+esc(d.config.hostname)+'</b>';
  const grid = document.getElementById('grid');
  grid.innerHTML = '';
  for (const [key, c] of Object.entries(d.checks)){
    const div = document.createElement('div');
    div.className = 'card';
    div.innerHTML =
      '<h2><span class="dot '+c.status+'"></span>'+esc(LABELS[key]||key)+'</h2>'+
      '<div class="detail">'+esc(c.detail)+'</div>'+
      '<div class="meta">'+c.status.toUpperCase()+' · '+c.latency_ms+' ms</div>';
    grid.appendChild(div);
  }
  renderConns(d.connections || []);
  renderErrors(d.errors || []);
}
function renderErrors(errs){
  document.getElementById('errcount').textContent = errs.length;
  const el = document.getElementById('errs');
  if (!errs.length){ el.innerHTML = '<div class="empty">No recent errors. 🎉</div>'; return; }
  el.innerHTML = errs.map(e =>
    '<div class="err">'+
    '<div class="top"><span class="ctx">'+esc(e.context)+'</span><span class="when">'+new Date(e.timestamp).toLocaleTimeString()+' ('+ago(e.timestamp)+' ago)</span></div>'+
    '<div class="msg">'+esc(e.error)+'</div>'+
    (e.traceback && e.traceback.length ? '<div class="tb">'+esc(e.traceback.join('\\n'))+'</div>' : '')+
    '</div>'
  ).join('');
}
function ago(iso){
  const s = Math.max(0, Math.round((Date.now() - new Date(iso).getTime())/1000));
  if (s < 60) return s + 's';
  if (s < 3600) return Math.floor(s/60) + 'm ' + (s%60) + 's';
  return Math.floor(s/3600) + 'h ' + Math.floor((s%3600)/60) + 'm';
}
function renderConns(conns){
  document.getElementById('conncount').textContent = conns.length;
  const el = document.getElementById('conns');
  if (!conns.length){ el.innerHTML = '<div class="empty">No active WebSocket connections.</div>'; return; }
  let rows = conns.map(c =>
    '<tr>'+
    '<td><span class="badge '+(c.is_admin?'admin':'student')+'">'+(c.is_admin?'ADMIN':'STUDENT')+'</span></td>'+
    '<td>'+esc(c.username)+' <span style="color:#64748b">#'+esc(c.user_id)+'</span></td>'+
    '<td>'+esc(c.language || '—')+'</td>'+
    '<td>'+esc(c.messages)+'</td>'+
    '<td>'+ago(c.connected_at)+'</td>'+
    '<td>'+ago(c.last_activity)+' ago</td>'+
    '</tr>'
  ).join('');
  el.innerHTML =
    '<table><thead><tr><th>Role</th><th>User</th><th>Language</th><th>Msgs</th><th>Connected</th><th>Last activity</th></tr></thead>'+
    '<tbody>'+rows+'</tbody></table>';
}
load();
setInterval(load, 5000);
</script>
</body>
</html>"""
