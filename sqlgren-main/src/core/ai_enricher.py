"""Hook opcional de LLM (Ollama / OpenAI-compatível) para enriquecer descrições de negócio."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, Optional


SYSTEM_PROMPT = (
    "Você é um analista de dados de Atenção Primária e BI legado. "
    "Recebe SQL estático (nunca execute). Responda APENAS JSON válido com chaves: "
    "descricao_negocio (1-2 frases em português), falhas (lista de riscos lógicos), "
    "otimizacoes (lista de sugestões de desempenho). Seja concreto e conservador."
)


def _endpoint() -> Optional[str]:
    url = os.environ.get("ACERVO_LLM_URL") or os.environ.get("OPENAI_BASE_URL")
    if url:
        return url.rstrip("/")
    if os.environ.get("OPENAI_API_KEY"):
        return "https://api.openai.com/v1"
    if os.environ.get("OLLAMA_HOST"):
        return os.environ["OLLAMA_HOST"].rstrip("/")
    return None


def _model() -> str:
    return os.environ.get("ACERVO_LLM_MODEL") or os.environ.get("OPENAI_MODEL") or "gpt-4o-mini"


def _post_json(url: str, payload: Dict[str, Any], headers: Dict[str, str], timeout: float) -> Dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
    return json.loads(body)


def enrich_query(sql: str, titulo: str = "", timeout: float = 12.0) -> Optional[Dict[str, Any]]:
    """Gera descrição executiva quando um provedor LLM está configurado. None se desligado ou falha."""
    base = _endpoint()
    if not base or not (sql or "").strip():
        return None

    key = os.environ.get("ACERVO_LLM_KEY") or os.environ.get("OPENAI_API_KEY") or ""
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"

    user = f"Título: {titulo or 'sem título'}\n\nSQL:\n{sql[:6000]}"
    payload = {
        "model": _model(),
        "temperature": 0.1,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ],
    }

    urls = [
        f"{base}/chat/completions",
        f"{base}/v1/chat/completions",
        f"{base}/api/chat",
    ]
    last_error = None
    for url in urls:
        try:
            if url.endswith("/api/chat"):
                ollama = {
                    "model": _model(),
                    "stream": False,
                    "messages": payload["messages"],
                    "format": "json",
                }
                raw = _post_json(url, ollama, {"Content-Type": "application/json"}, timeout)
                content = (raw.get("message") or {}).get("content") or ""
            else:
                raw = _post_json(url, payload, headers, timeout)
                content = (((raw.get("choices") or [{}])[0].get("message") or {}).get("content")) or ""
            parsed = _parse_content(content)
            if parsed:
                return parsed
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError) as exc:
            last_error = exc
            continue
    if last_error:
        return {"erro": str(last_error)}
    return None


def _parse_content(content: str) -> Optional[Dict[str, Any]]:
    text = (content or "").strip()
    if not text:
        return None
    if text.startswith("```"):
        text = text.strip("`")
        text = text.replace("json", "", 1).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            data = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None
    if not isinstance(data, dict):
        return None
    return {
        "descricao_negocio": str(data.get("descricao_negocio") or data.get("descricao") or "").strip()[:600],
        "falhas": [str(x) for x in (data.get("falhas") or [])][:8],
        "otimizacoes": [str(x) for x in (data.get("otimizacoes") or [])][:8],
        "fonte": "llm",
    }


def maybe_enrich(block: Dict[str, Any], enabled: bool) -> Dict[str, Any]:
    if not enabled:
        return block
    comment = (block.get("comentario") or "").strip()
    if len(comment) >= 12:
        return block
    result = enrich_query(block.get("sql") or "", block.get("titulo") or "")
    if not result or result.get("erro"):
        if result and result.get("erro"):
            block["ai_erro"] = result["erro"]
        return block
    block["ai"] = result
    if result.get("descricao_negocio") and len(block.get("descricao") or "") < 40:
        block["descricao"] = result["descricao_negocio"]
    return block
