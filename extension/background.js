// dirsubmit Bridge — 连接本地 WebSocket，接收命令并在当前标签页执行填表/点击。
const WS_URL = "ws://127.0.0.1:8721";

let ws = null;
let reconnectTimer = null;
let heartbeatTimer = null;
let taskTabId = null;
let commandQueue = Promise.resolve();

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
    const operation = commandQueue.then(() => handle(msg));
    commandQueue = operation.catch(() => {});
    const resp = await operation.catch((e) => ({ status: "error", error: String(e) }));
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
  if (heartbeatTimer) clearInterval(heartbeatTimer);
  heartbeatTimer = setInterval(() => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      try { ws.send(JSON.stringify({ id: "hb", cmd: "ping" })); } catch {}
    }
  }, 20000);
}

async function handle(msg) {
  let tab;
  if (msg.cmd !== "ping" && msg.cmd !== "navigate" && msg.cmd !== "wait") {
    if (taskTabId === null) return { status: "error", error: "no task tab; navigate first" };
    try { tab = await chrome.tabs.get(taskTabId); }
    catch { return { status: "error", error: "task tab closed; do not submit again automatically" }; }
  }

  switch (msg.cmd) {
    case "ping":
      return { status: "ok", result: "pong" };

    case "navigate":
      try {
        const url = new URL(msg.url);
        if (!["http:", "https:"].includes(url.protocol)) throw new Error("only http(s) task URLs allowed");
        tab = await chrome.tabs.create({ url: msg.url, active: true });
        taskTabId = tab.id;
        const deadline = Date.now() + 25000;
        while (Date.now() < deadline) {
          const current = await chrome.tabs.get(taskTabId);
          if (current.status === "complete" && current.url !== "about:blank") {
            return { status: "ok", tab_id: taskTabId, url: current.url };
          }
          await new Promise((resolve) => setTimeout(resolve, 200));
        }
        return { status: "error", error: "navigation timed out" };
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

    case "inspect": {
      try {
        const results = await chrome.scripting.executeScript({
          target: { tabId: tab.id, allFrames: true },
          func: inspectPage,
          args: [msg.selector || "", msg.text || "", msg.url_contains || ""],
        });
        return { status: "ok", result: {
          found: results.some(r => r.result?.found),
          confirmed: results.some(r => r.result?.confirmed),
          url: tab.url,
          frames: results.map(r => r.result),
        }};
      } catch (e) { return { status: "error", error: String(e) }; }
    }

    case "click": {
      try {
        const matches = await chrome.scripting.executeScript({
          target: { tabId: tab.id, allFrames: true }, func: inspectPage,
          args: [msg.selector, "", ""],
        });
        const match = matches.find(r => r.result?.found);
        if (!match) return { status: "error", error: "no visible click target" };
        const results = await chrome.scripting.executeScript({
          target: { tabId: tab.id, frameIds: [match.frameId] },
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
  const el = [...document.querySelectorAll(selector)].find(e => e.getClientRects().length && !e.disabled);
  if (!el) return false;
  try {
    if (type === "select") {
      const option = [...el.options].find(o => o.value === value || o.label === value);
      if (!option) return false;
      el.value = option.value;
      el.dispatchEvent(new Event("change", { bubbles: true }));
      return true;
    }
    if (type === "checkbox") {
      el.checked = ["true", "yes", "1"].includes(String(value).toLowerCase());
      el.dispatchEvent(new Event("change", { bubbles: true }));
      return true;
    }
    if (type === "radio") { el.click(); return el.checked; }
    if (el.isContentEditable) {
      el.textContent = value;
      el.dispatchEvent(new Event("input", { bubbles: true }));
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
  const el = [...document.querySelectorAll(selector)].find(e => e.getClientRects().length && !e.disabled);
  if (!el) return false;
  try { el.click(); return true; } catch (e) { return false; }
}

function inspectPage(selector, text, urlContains) {
  const found = !!selector && [...document.querySelectorAll(selector)]
    .some(el => el.getClientRects().length && !el.disabled);
  return { found, confirmed: found || (!!text && document.body.innerText.includes(text)) ||
    (!!urlContains && location.href.includes(urlContains)), url: location.href };
}

connect();
