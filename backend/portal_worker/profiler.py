# -*- coding: utf-8 -*-
"""Portal Profiler — Network + DOM + screenshot seletivo + trace. SPEC-073 Bloco D.

Por que ele existe
==================
As jornadas que funcionam hoje foram descobertas à mão: F12, aba Network, HAR,
HTML salvo, inspeção. Funcionou — e não escala. O profiler é a mesma observação,
feita pelo próprio worker, toda vez que ele entra no portal, de graça.

🔴 **Ele é PASSIVO.** Escuta eventos de `page`/`context` e não intercepta, não
reescreve, não bloqueia e não repete request. Um profiler que altera o tráfego
deixa de medir o portal e passa a medir a si mesmo — e o dia em que ele quebrar
uma journey de cobrança, ninguém vai suspeitar do observador.

O que ele NUNCA persiste
========================
Header sensível, corpo de request/response, CPF, placa, nome, apólice, token.
O corpo vira **forma** (`{"cpf": "<string:11>"}`), nunca conteúdo. Tudo passa
pelo redator único de `redaction.py`.

Candidato de API não é API aprovada
===================================
O profiler diz *"esta chamada parece a fonte estruturada desta tela"*. Quem
transforma isso em adapter é uma journey, depois de reproduzir com sessão
legítima e criar fixture anonimizada. A SPEC-073 G3 é explícita, e este módulo
respeita: `confidence` nasce `"candidate"` e nada aqui executa nada.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import urlsplit

from portal_worker import redaction as R

logger = logging.getLogger(__name__)

# Teto do trace. 80 eventos cobrem um fluxo de portal inteiro com folga; o que
# passa disso é laço, e laço se diagnostica pelo contador, não relendo 400 linhas.
MAX_EVENTOS_TRACE = 80
MAX_REQUESTS = 200
TRUNCAR_EM = 200

# Hosts que só servem métrica/anúncio. Não são o portal e poluem o candidato.
_TELEMETRIA = (
    "google-analytics", "googletagmanager", "doubleclick", "facebook",
    "hotjar", "clarity.ms", "newrelic", "sentry.io", "datadoghq",
    "segment.io", "mixpanel", "amplitude", "intercom", "zendesk",
    "cloudflareinsights", "bing.com", "linkedin.com", "adservice",
)

_ASSET_TYPES = ("image", "stylesheet", "font", "media", "manifest", "other")

# --------------------------------------------------------------------------
# Normalização de path — o que faz duas visitas à mesma tela terem a mesma
# assinatura, mesmo com id diferente no meio da URL.
# --------------------------------------------------------------------------
_RE_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)
_RE_HEX_LONGO = re.compile(r"\b[0-9a-f]{16,}\b", re.I)
_RE_NUMERO = re.compile(r"\b\d{2,}\b")


def normalizar_path(path: str) -> str:
    """`/atendimento/9f2a-.../passo5` → `/atendimento/{uuid}/passo{n}`.

    Sem isso, cada execução produz uma assinatura nova e o profiler nunca
    consegue dizer "esta tela é a mesma de ontem" — que é a única pergunta que
    ele precisa responder bem.
    """
    p = str(path or "")
    p = _RE_UUID.sub("{uuid}", p)
    p = _RE_HEX_LONGO.sub("{hash}", p)
    p = _RE_NUMERO.sub("{n}", p)
    return p or "/"


def classificar_origem(host: str, host_portal: str, resource_type: str = "") -> str:
    """`first_party` · `asset` · `telemetry` · `third_party` · `unknown`.

    A classificação existe para que o candidato de API não venha afogado em
    pixel de analytics e fonte web.
    """
    h = str(host or "").strip().lower()
    hp = str(host_portal or "").strip().lower()
    if not h:
        return "unknown"
    if any(t in h for t in _TELEMETRIA):
        return "telemetry"
    rt = str(resource_type or "").strip().lower()
    mesma_casa = bool(hp) and (h == hp or h.endswith("." + hp) or hp.endswith("." + h))
    if rt in _ASSET_TYPES:
        return "asset"
    if mesma_casa:
        return "first_party"
    return "third_party"


def _host_de(url: str) -> str:
    try:
        return (urlsplit(str(url or "")).hostname or "").lower()
    except ValueError:
        return ""


def _path_de(url: str) -> str:
    try:
        return urlsplit(str(url or "")).path or "/"
    except ValueError:
        return "/"


# --------------------------------------------------------------------------
# Assinatura de tela — SPEC-073 D5
# --------------------------------------------------------------------------
def screen_fingerprint(state: Dict[str, Any]) -> str:
    """Hash do SENTIDO da tela, não do seu HTML.

    🔴 O que entra é deliberadamente pobre: rota normalizada, heading, rótulos
    de campo, rótulos de select, textos de botão. O que fica de fora é o que
    muda sozinho — `input_1`, uuid de sessão, contador, timestamp. Se ids
    dinâmicos entrassem no hash, toda visita seria "tela nova" e o detector de
    drift viraria ruído.
    """
    if not isinstance(state, dict):
        return ""
    partes: List[str] = []
    partes.append(normalizar_path(_path_de(state.get("url") or "")))
    partes.append(str(state.get("heading") or "").strip().lower()[:120])

    def _rotulos(chave: str, campo: str = "label") -> List[str]:
        itens = state.get(chave) or []
        out: List[str] = []
        if isinstance(itens, list):
            for it in itens:
                if isinstance(it, dict):
                    v = str(it.get(campo) or it.get("name") or it.get("text") or "").strip().lower()
                    # ids gerados (`input_3`) não descrevem a tela
                    if v and not re.fullmatch(r"(input|campo|field)[_-]?\d+", v):
                        out.append(v[:60])
        return sorted(set(out))

    partes.extend(_rotulos("inputs"))
    partes.extend(_rotulos("selects"))
    partes.extend(_rotulos("mdselects"))
    partes.extend(_rotulos("buttons", "text"))

    crua = "|".join(p for p in partes if p)
    return R.digest(crua) if crua else ""


def classificar_drift(atual: str, esperada: str) -> str:
    """`none` quando as assinaturas batem; `unknown` quando falta referência."""
    if not esperada:
        return "unknown"
    if not atual:
        return "unknown"
    return "none" if atual == esperada else "semantic"


# --------------------------------------------------------------------------
@dataclass
class PortalProfiler:
    """Observa. Não age.

    Uso pelo worker:

        prof = PortalProfiler(portal_key="mapfre_corretor", host_portal="...")
        prof.attach(page)          # liga os ouvintes
        ...
        evidence["profiler"] = prof.resumo()
    """

    portal_key: str = ""
    host_portal: str = ""
    habilitado: bool = True
    discovery: bool = False

    requests: List[Dict[str, Any]] = field(default_factory=list)
    eventos: List[Dict[str, Any]] = field(default_factory=list)
    telas: List[Dict[str, Any]] = field(default_factory=list)
    _pendentes: Dict[str, float] = field(default_factory=dict)
    _descartados: int = 0
    _n: int = 0

    # -- trace ------------------------------------------------------------
    def evento(self, **campos: Any) -> None:
        """Uma linha do trace. Redigida, truncada e com teto."""
        if not self.habilitado:
            return
        if len(self.eventos) >= MAX_EVENTOS_TRACE:
            self._descartados += 1
            return
        self._n += 1
        limpo: Dict[str, Any] = {"n": self._n}
        for k, v in campos.items():
            if v is None:
                continue
            if isinstance(v, str):
                limpo[k] = R.redigir_texto(v)[:TRUNCAR_EM]
            elif isinstance(v, (int, float, bool)):
                limpo[k] = v
            else:
                limpo[k] = R.redigir_texto(str(v))[:TRUNCAR_EM]
        self.eventos.append(limpo)

    # -- rede -------------------------------------------------------------
    def registrar_response(self, *, url: str, method: str, status: int,
                           content_type: str = "", resource_type: str = "",
                           latency_ms: Optional[float] = None,
                           request_size: Optional[int] = None,
                           response_size: Optional[int] = None) -> None:
        """Uma resposta observada. Só metadado — nunca corpo, nunca header."""
        if not self.habilitado or len(self.requests) >= MAX_REQUESTS:
            return
        host = _host_de(url)
        origem = classificar_origem(host, self.host_portal, resource_type)
        if origem in ("telemetry", "asset"):
            return  # ruído: não ajuda a entender o portal e enche o artefato
        self.requests.append({
            "method": str(method or "").upper()[:8],
            "host": host,
            "path": normalizar_path(_path_de(url)),
            "resource_type": str(resource_type or "")[:24],
            "status": int(status or 0),
            "content_type": str(content_type or "").split(";")[0][:64],
            "latency_ms": int(latency_ms) if latency_ms is not None else None,
            "request_size": request_size,
            "response_size": response_size,
            "origem": origem,
        })

    def attach(self, page: Any) -> None:
        """Liga os ouvintes passivos. Falha aqui NUNCA derruba a journey.

        🔴 O `try` largo é intencional: o profiler é diagnóstico. Se a versão do
        Playwright mudar um nome de evento, o worker precisa continuar cobrando
        boleto — cego, mas de pé.
        """
        if not self.habilitado or page is None:
            return
        try:
            def _on_response(resp: Any) -> None:
                try:
                    req = getattr(resp, "request", None)
                    self.registrar_response(
                        url=getattr(resp, "url", "") or "",
                        method=getattr(req, "method", "") or "",
                        status=getattr(resp, "status", 0) or 0,
                        content_type=(resp.headers or {}).get("content-type", ""),
                        resource_type=getattr(req, "resource_type", "") or "",
                    )
                except Exception:  # noqa: BLE001
                    pass

            def _on_failed(req: Any) -> None:
                try:
                    self.evento(layer="network", event="requestfailed",
                                host=_host_de(getattr(req, "url", "") or ""),
                                path=normalizar_path(_path_de(getattr(req, "url", "") or "")))
                except Exception:  # noqa: BLE001
                    pass

            def _on_nav(frame: Any) -> None:
                try:
                    self.evento(layer="nav", event="framenavigated",
                                path=normalizar_path(_path_de(getattr(frame, "url", "") or "")))
                except Exception:  # noqa: BLE001
                    pass

            page.on("response", _on_response)
            page.on("requestfailed", _on_failed)
            page.on("framenavigated", _on_nav)
        except Exception as e:  # noqa: BLE001
            logger.warning("[PORTAL] profiler nao pode observar: %s", type(e).__name__)
            self.habilitado = False

    # -- tela -------------------------------------------------------------
    def registrar_tela(self, state: Dict[str, Any], *, esperada: str = "") -> Dict[str, Any]:
        """Guarda a assinatura da tela e devolve o veredito de drift."""
        fp = screen_fingerprint(state)
        drift = classificar_drift(fp, esperada)
        reg = {
            "fingerprint": fp,
            "heading": R.redigir_texto(str(state.get("heading") or ""))[:120],
            "path": normalizar_path(_path_de(state.get("url") or "")),
            "drift": drift,
        }
        if self.habilitado and len(self.telas) < MAX_EVENTOS_TRACE:
            self.telas.append(reg)
        self.evento(layer="dom", screen=reg["path"], drift=drift)
        return reg

    # -- candidatos de API ------------------------------------------------
    def candidatos_de_api(self) -> List[Dict[str, Any]]:
        """Chamadas que PARECEM a fonte estruturada de uma tela.

        Critério deliberadamente conservador: primeira parte, XHR/fetch, resposta
        JSON ou PDF, status de sucesso. `confidence` nasce `"candidate"` — a
        palavra importa, porque um endpoint descoberto não é um endpoint
        aprovado (SPEC-073 G3).
        """
        vistos: Dict[str, Dict[str, Any]] = {}
        for r in self.requests:
            if r.get("origem") != "first_party":
                continue
            ct = str(r.get("content_type") or "")
            if not (ct.startswith("application/json")
                    or ct == "application/pdf"
                    or r.get("resource_type") in ("xhr", "fetch")):
                continue
            if not (200 <= int(r.get("status") or 0) < 400):
                continue
            chave = f"{r['method']} {r['path']}"
            if chave in vistos:
                vistos[chave]["vezes"] = vistos[chave].get("vezes", 1) + 1
                continue
            vistos[chave] = {
                "method": r["method"],
                "path": r["path"],
                "status": r["status"],
                "content_type": ct,
                "confidence": "candidate",
                "reason": "first_party xhr/fetch com resposta estruturada",
                "vezes": 1,
            }
        return sorted(vistos.values(), key=lambda c: (-c["vezes"], c["path"]))[:20]

    # -- saída ------------------------------------------------------------
    def resumo(self) -> Dict[str, Any]:
        """O bloco que vai para `portal_jobs.evidence`. Compacto e sem PII."""
        if not self.habilitado:
            return {"enabled": False}
        cands = self.candidatos_de_api()
        return {
            "enabled": True,
            "screens": len(self.telas),
            "requests_relevant": len(self.requests),
            "api_candidates": len(cands),
            "candidates": cands[:8],
            "drifts": [t for t in self.telas if t.get("drift") not in ("none", "unknown")][:8],
            "trace": self.eventos,
            "trace_truncated": self._descartados,
        }

    def discovery_block(self, *, esperada: str = "", recomendacao: str = "") -> Dict[str, Any]:
        """`evidence.discovery` — SPEC-073 C3. Nada de HTML inteiro."""
        atual = self.telas[-1]["fingerprint"] if self.telas else ""
        return {
            "enabled": bool(self.discovery),
            "screen_signature": atual,
            "expected_signature": esperada,
            "drift": classificar_drift(atual, esperada),
            "network_candidates": self.candidatos_de_api()[:8],
            "fallback_path": [e.get("layer") for e in self.eventos if e.get("layer")][:12],
            "unknown_elements": [],
            "recommendation": R.redigir_texto(recomendacao)[:300],
        }
