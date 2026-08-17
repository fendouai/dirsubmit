// dirsubmit Bridge — 连接本地 WebSocket，接收命令并在当前标签页执行填表/点击。
const WS_URL = "ws://127.0.0.1:8721";

let ws = null;
let reconnectTimer = null;

function connect() {
  try {
    ws = new WebSocket(WS_URL);
  } catch (e) {
    scheduleReconnect();
    return;
  }
  ws.onopen = () => {
    console.log("[dirsubmit] connected");
    startHeartbeat();
  };
  ws.onmessage = async (e) => {
    let msg;
    try { msg = JSON.parse(e.data); } catch { return; }
    const resp = await handle(msg);
    try {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ id: msg.id, ...resp }));
      }
    } catch {}
  };
  ws.onclose = () => scheduleReconnect();
  ws.onerror = () => { try { ws.close(); } catch {} };
}

function scheduleReconnect() {
  if (reconnectTimer) return;
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    connect();
  }, 2000);
}

function startHeartbeat() {
  setInterval(() => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      try { ws.send(JSON.stringify({ id: "hb", cmd: "ping" })); } catch {}
    }
  }, 20000);
}

async function handle(msg) {
  let tab;
  try {
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tabs.length) return { status: "error", error: "no active tab" };
    tab = tabs[0];
  } catch (e) {
    return { status: "error", error: String(e) };
  }

  switch (msg.cmd) {
    case "ping":
      return { status: "ok", result: "pong" };

    case "navigate":
      try {
        await chrome.tabs.update(tab.id, { url: msg.url });
        return { status: "ok" };
      } catch (e) {
        return { status: "error", error: String(e) };
      }

    case "wait":
      await new Promise((r) => setTimeout(r, msg.ms || 1000));
      return { status: "ok" };

    case "fill": {
      try {
        const results = await chrome.scripting.executeScript({
          target: { tabId: tab.id, allFrames: true },
          func: fillField,
          args: [msg.selector, msg.value || "", msg.type || "text"],
        });
        const ok = (results || []).some((r) => r.result === true);
        return ok ? { status: "ok" }
                  : { status: "error", error: "not found: " + msg.selector };
      } catch (e) {
        return { status: "error", error: String(e) };
      }
    }

    case "click": {
      try {
        const results = await chrome.scripting.executeScript({
          target: { tabId: tab.id, allFrames: true },
          func: clickElement,
          args: [msg.selector],
        });
        const ok = (results || []).some((r) => r.result === true);
        return ok ? { status: "ok" }
                  : { status: "error", error: "not found: " + msg.selector };
      } catch (e) {
        return { status: "error", error: String(e) };
      }
    }

    default:
      return { status: "error", error: "unknown cmd: " + msg.cmd };
  }
}

// 下面两个函数会被序列化注入页面执行，必须是独立、自包含的。

function fillField(selector, value, type) {
  const el = document.querySelector(selector);
  if (!el) return false;
  try {
    if (type === "select") {
      el.value = value;
      el.dispatchEvent(new Event("change", { bubbles: true }));
      return true;
    }
    if (type === "checkbox") {
      if (value && String(value).toLowerCase() !== "false") el.checked = true;
      el.dispatchEvent(new Event("change", { bubbles: true }));
      return true;
    }
    // text / textarea / url / email / search
    const proto = el.tagName === "TEXTAREA"
      ? HTMLTextAreaElement.prototype
      : HTMLInputElement.prototype;
    const setter = Object.getOwnPropertyDescriptor(proto, "value").set;
    setter.call(el, value);
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  } catch (e) {
    return false;
  }
}

function clickElement(selector) {
  const el = document.querySelector(selector);
  if (!el) return false;
  try { el.click(); return true; } catch (e) { return false; }
}

connect();
