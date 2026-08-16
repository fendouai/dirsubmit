"""多后端 LLM 客户端：OpenAI / DeepSeek / Gemini / Ollama。

统一 `chat(messages, json_mode)` 接口，返回纯文本。
无 API key 时抛出 `LLMUnavailable`，由 copywriter 回退到模板文案。
"""

from __future__ import annotations

import json
import re
from typing import List

import requests


class LLMUnavailable(Exception):
    pass


_PROVIDERS = {
    "openai": {
        "base": "https://api.openai.com/v1/chat/completions",
        "key_env": "OPENAI_API_KEY",
        "model_env": "OPENAI_MODEL",
        "model": "gpt-4o-mini",
    },
    "deepseek": {
        "base": "https://api.deepseek.com/chat/completions",
        "key_env": "DEEPSEEK_API_KEY",
        "model_env": "DEEPSEEK_MODEL",
        "model": "deepseek-chat",
    },
    "gemini": {
        "base": "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        "key_env": "GEMINI_API_KEY",
        "model_env": "GEMINI_MODEL",
        "model": "gemini-2.0-flash",
    },
    "ollama": {
        "base": "http://localhost:11434/api/chat",
        "key_env": None,
        "model_env": "OLLAMA_MODEL",
        "model": "llama3.2",
    },
}


class LLMClient:
    def __init__(self, provider: str = "openai"):
        if provider not in _PROVIDERS:
            raise ValueError(f"未知 provider: {provider}，可选 {list(_PROVIDERS)}")
        self.provider = provider
        cfg = _PROVIDERS[provider]
        import os

        self.key = os.environ.get(cfg["key_env"], "") if cfg["key_env"] else ""
        self.model = os.environ.get(cfg["model_env"], cfg["model"])
        self.base = cfg["base"]

    def available(self) -> bool:
        if self.provider == "ollama":
            return True  # 本地服务，chat() 里再探测
        return bool(self.key)

    def chat(self, messages: List[dict], json_mode: bool = False) -> str:
        if self.provider == "ollama":
            return self._ollama(messages)
        if self.provider == "gemini":
            return self._gemini(messages)
        return self._openai_compatible(messages, json_mode)

    def _openai_compatible(self, messages: List[dict], json_mode: bool) -> str:
        if not self.key:
            raise LLMUnavailable(f"未设置 {self.provider.upper()} API key")
        payload = {"model": self.model, "messages": messages, "temperature": 0.7}
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        headers = {"Authorization": f"Bearer {self.key}"}
        r = requests.post(self.base, json=payload, headers=headers, timeout=60)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()

    def _gemini(self, messages: List[dict]) -> str:
        if not self.key:
            raise LLMUnavailable("未设置 GEMINI_API_KEY")
        url = self.base.format(model=self.model) + f"?key={self.key}"
        contents = []
        for m in messages:
            contents.append({"role": "user" if m["role"] != "assistant" else "model",
                             "parts": [{"text": m["content"]}]})
        r = requests.post(url, json={"contents": contents}, timeout=60)
        r.raise_for_status()
        data = r.json()
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()

    def _ollama(self, messages: List[dict]) -> str:
        payload = {"model": self.model, "messages": messages, "stream": False}
        try:
            r = requests.post(self.base, json=payload, timeout=120)
            r.raise_for_status()
            return r.json()["message"]["content"].strip()
        except requests.RequestException as e:
            raise LLMUnavailable(f"Ollama 服务不可用（{e}），请先启动 ollama serve") from e


def extract_json(text: str):
    """从 LLM 输出里稳健地抽出第一个 JSON 对象。"""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
    return None
