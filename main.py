from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Any, Dict
import uuid
import asyncio

app = FastAPI()

class ToolSpec(BaseModel):
    name: str
    description: str
    input_schema: Dict[str, Any]
    
CATALOG = {
    "tools": [
        ToolSpec(
            name="search",
            description="Search the web (dummy). Args: { query: string }",
            input_schema={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        ).model_dump()
    ]
}

# 簡易テスター（ブラウザで開ける）
HTML = """
<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<title>MCP-like WS Client</title>
<style>
  body{font-family:system-ui,-apple-system,"Segoe UI",Roboto,"Noto Sans JP",sans-serif;line-height:1.6;padding:20px}
  h1{margin-top:0}
  .row{margin:8px 0}
  button,input{font-size:14px}
  #status{margin-bottom:8px}
  .grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
  .card{border:1px solid #ddd;border-radius:8px;padding:12px;background:#fafafa}
  .log{white-space:pre-wrap;font-family:ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;background:#111;color:#eee;padding:8px;border-radius:6px;max-height:220px;overflow:auto}
  .pill{display:inline-block;padding:2px 8px;border-radius:999px;background:#eee;font-size:12px;margin-right:6px}
  .ok{background:#d1fae5}
  .err{background:#fee2e2}
</style>
</head>
<body>
<h1>MCP-like WS Client</h1>

<div id="status" class="pill">connecting…</div>

<div class="row">
  <button id="btnCatalog">Get Catalog</button>
</div>

<div class="row">
  <input id="query" placeholder="検索クエリ（例: Pythonとは？）" size="32" />
  <button id="btnCall">Call search</button>
</div>

<div class="grid">
  <div class="card">
    <h3>Event Log</h3>
    <div id="log" class="log"></div>
  </div>
  <div class="card">
    <h3>Requests</h3>
    <div id="reqs"></div>
  </div>
</div>

<script>
(function(){
  const status = document.getElementById('status');
  const logEl = document.getElementById('log');
  const reqsEl = document.getElementById('reqs');
  function log(line){ logEl.textContent += line + "\\n"; logEl.scrollTop = logEl.scrollHeight; }

  const ws = new WebSocket("ws://" + location.host + "/ws");
  window.ws = ws; // console からデバッグできるように

  ws.onopen = () => { status.textContent = "connected"; status.classList.add('ok'); log("[open]"); };
  ws.onclose = () => { status.textContent = "closed"; status.classList.remove('ok'); log("[close]"); };
  ws.onerror = (e) => { status.textContent = "error"; status.classList.add('err'); log("[error] " + e); };

  const cards = new Map(); // request_id -> card element

  function ensureCard(reqId, tool){
    if(!reqId){ return null; }
    if(cards.has(reqId)) return cards.get(reqId);
    const wrap = document.createElement('div');
    wrap.className = 'card';
    wrap.innerHTML = "<div class='pill'>req: "+reqId+"</div><div class='pill'>tool: "+(tool||"-")+
                     "</div><div class='log' id='log-"+reqId+"'></div>";
    reqsEl.prepend(wrap);
    cards.set(reqId, wrap);
    return wrap;
  }
  function logToCard(reqId, text){
    const card = cards.get(reqId);
    if(!card) return;
    const div = card.querySelector('#log-'+reqId);
    div.textContent += text + "\\n";
    div.scrollTop = div.scrollHeight;
  }

  ws.onmessage = (e) => {
    let msg = null;
    try { msg = JSON.parse(e.data); }
    catch { log("[recv] (non-JSON) " + e.data); return; }

    const t = msg.type;
    const rid = msg.request_id || "-";
    const tool = msg.tool || "-";

    log(`[recv] type=${t} req=${rid} tool=${tool}`);

    if(rid !== "-"){ ensureCard(rid, tool); }

    if(t === "catalog"){
      log(JSON.stringify(msg.data, null, 2));
    } else if(t === "tool_ack"){
      logToCard(rid, "ACK: accepted");
    } else if(t === "partial_result"){
      logToCard(rid, "PARTIAL: " + JSON.stringify(msg.data));
    } else if(t === "tool_result"){
      logToCard(rid, "RESULT: " + JSON.stringify(msg.result));
    } else if(t === "complete"){
      logToCard(rid, "✅ COMPLETE");
    } else if(t === "error"){
      logToCard(rid, "❌ ERROR: " + msg.error);
    }
  };

  document.getElementById('btnCatalog').onclick = () => {
    const payload = { type: "catalog_request" };
    if (ws.readyState !== 1){ log("[warn] websocket not open (state="+ws.readyState+")"); return; }
    ws.send(JSON.stringify(payload));
    log("[send] catalog_request");
  };

  document.getElementById('btnCall').onclick = () => {
    const q = document.getElementById('query').value || "Pythonとは？";
    const rid = (typeof crypto !== "undefined" && crypto.randomUUID)
      ? crypto.randomUUID()
      : String(Date.now());

    if (ws.readyState !== 1){
      log("[warn] websocket not open (state=" + ws.readyState + ")");
      return;
    }

    const payload = {
      type: "tool_call",
      tool: "search",
      arguments: { query: q },
      request_id: rid
    };
    ws.send(JSON.stringify(payload));
    log(`[send] tool_call search req=${rid} q="${q}"`);
    ensureCard(rid, "search");
  };
})();
</script>
</body>
</html>
"""



@app.get("/")
async def index():
    return HTMLResponse(HTML)

@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        await websocket.send_json({"type": "catalog", "data": CATALOG})
        
        while True:
            raw = await websocket.receive_text()
            try:
                import json
                msg = json.loads(raw)
            except Exception:
                await websocket.send_json({"type": "error", "error": "invalid_json"})
                continue
        
            if msg.get("type") == "catalog_request":
                await websocket.send_json({"type": "catalog", "data": CATALOG})
            
            elif msg.get("type") == "tool_call":
                tool = msg.get("tool")
                args = msg.get("arguments", {})
                req_id = msg.get("request_id") or str(uuid.uuid4())
                
                # 受理ACK
                await websocket.send_json({
                    "type": "tool_ack",
                    "tool": tool,
                    "request_id": req_id,
                    "status": "accepted"
                })
                
                if tool == "search":
                    q = args.get("query")
                    if not isinstance(q, str):
                        await websocket.send_json({
                            "type": "error", 
                            "error": "query must be string",
                            "request_id": req_id
                        })
                        continue
                    partials = [
                        {"title": "Result 1", "snippet": f"{q}の概説"},
                        {"title": "Result 2", "snippet": f"{q}の公式ドキュメント"},
                        {"title": "Result 3", "snippet": f"{q}の関連トピック"},
                    ]
                    for item in partials:
                        await websocket.send_json({
                            "type": "partial_result",
                            "tool": "search",
                            "data": item,
                            "request_id": req_id
                        })
                        await asyncio.sleep(0.3)
                    await websocket.send_json({
                        "type": "complete", 
                        "tool": "search",
                        "request_id": req_id
                    })
                else:
                    await websocket.send_json({
                        "type": "error", 
                        "error": f"unknown tool: {tool}",
                        "request_id": req_id
                    })
            else: 
                await websocket.send_json({"type": "error", "error": "unknown message type"})
        
    except WebSocketDisconnect:
        pass