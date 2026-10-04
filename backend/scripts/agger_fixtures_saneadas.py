# -*- coding: utf-8 -*-
"""Gerador das fixtures saneadas do Agger — SPEC-128 U1.

    python backend/scripts/agger_fixtures_saneadas.py              # as 3 gravações (HAR)
    python backend/scripts/agger_fixtures_saneadas.py --conferir   # roda tudo, NÃO grava
    python backend/scripts/agger_fixtures_saneadas.py --jsonl ARQ --rotulo vivo_xxx [--conta conta_a]

O fio: BRUTO (HAR fora do git / JSONL de captura) → PROJEÇÃO POR LISTA BRANCA
(caminho completo até a folha, por endpoint — `leitor_agger.LISTA_BRANCA_POR_ENDPOINT`)
→ pseudônimo por ORDEM DE APARIÇÃO, sem chave → crivo de nome + `redaction.redigir`
→ `tem_vazamento()==[]` ou ABORTA → DIFERENCIAL contra o bruto (cada valor sensível
procurado na saída) ou ABORTA → grava `backend/tests/fixtures/agger/`.

🔴 Nunca imprime um VALOR do bruto: só TIPO, CAMINHO e contagens.
🔴 O bruto nunca entra no repositório; o MANIFESTO guarda só rótulo e sha256.
🔴 Idempotente: sem relógio, sem aleatório — duas rodadas, bytes iguais.
🔴 Nenhum nome de corretora/pessoa aqui: as contas são `conta_a`/`conta_b`.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import urlparse

RAIZ = Path(__file__).resolve().parents[2]
BACKEND = RAIZ / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from portal_worker.redaction import (  # noqa: E402  (o redator ÚNICO)
    redigir_texto, sem_url_nem_chave, tem_url_ou_chave, tem_vazamento,
)
from portal_worker.multicalculo.leitor_agger import (  # noqa: E402
    LISTA_BRANCA_POR_ENDPOINT, caminho_permitido, caminhos_de, dobra,
    lista_branca_do_arquivo,
)

SAIDA_PADRAO = BACKEND / "tests" / "fixtures" / "agger"
INTAKE = RAIZ / "docs" / "intake" / "MULTICALCULO AGGER"
# rótulo → (caminho relativo ao intake, conta). Nenhum nome de cliente no rótulo.
GRAVACOES: Tuple[Tuple[str, str, str], ...] = (
    ("gravacao_r1", "RENOVAÇÃO 1/aggilizador.com.br.har", "conta_a"),
    ("gravacao_r2", "RENOVAÇÃO 2/aggilizador.com.br.har", "conta_a"),
    ("gravacao_config", "GERAL/aggilizador.com.br TELA DE SEGURADORAS.har", "conta_a"),
)
FORMATO = "agger_fixture_v1"
HOSTS = ("aggilizador.com.br", "multicalculo.net")  # pdocs.* · api-prod.* · api.multicalculo.net

# ---------------------------------------------------------------------------
# Transformações por NOME da última chave (só dentro de caminho da lista branca)
# ---------------------------------------------------------------------------
PSEUDONIMO_POR_CHAVE: Dict[str, str] = {
    "cpfCnpj": "cpf", "nome@pessoa": "pessoa", "dataNasc": "data",
    "dataPrimHabil": "data", "vigenciaIni": "data", "vigenciaFim": "data",
    "vigFimAnterior": "data", "fone1": "telefone", "email": "email",
    "cep": "cep", "cepPernoite": "cep", "cepCirculacao": "cep",
    "cidade": "endereco", "bairro": "endereco", "logradouro": "endereco",
    "residLogradouro": "endereco", "residNumero": "endereco",
    "residBairro": "endereco", "residCidade": "endereco",
    "placa": "placa", "chassi": "chassi", "numeroRenovacao": "apolice",
    "CI": "ci", "negocioId": "negocio", "idIntegracao": "negocio",
    "nroCalculo": "calculo",
}
# caminhos (sufixo) cujo `nome` é de PESSOA — os outros `nome` são de seguradora
CAMINHOS_DE_NOME_DE_PESSOA = ("segurado.nome", "condutores[].nome")
CHAVES_DE_PDF = ("pathPdf", "pdfFileNameAgger")
PARCELAMENTOS_POR_OFERTA = 3
CANONICO = {"percComissao": 10, "percDesconto": 0}  # presença e tipo; nunca o número real

# chaves cujo valor é nome de pessoa/corretora em QUALQUER endpoint do bruto
CHAVES_DE_NOME = {"nome", "seguradonome", "customername", "usuario", "corretora",
                  "razaosocial", "nomefantasia", "nomecorretora", "apelido"}
# 🔴 palavras COMUNS do ramo que nunca são parte de nome (conserto P3/P4 da SPEC-128).
# 📊 04/10: o nome de um negócio de teste da conta_b tem a palavra "auto"; o crivo a
# tratava como parte de nome e trocava "Auto" por <nome> em 495 folhas da vivo_conta_b
# ("Azul Auto Roubo" → "Azul <nome> Roubo"): a Oferta.pacote deixava de ser a tela.
# Sozinha, nenhuma destas palavras identifica alguém; o resto do nome continua no crivo.
PALAVRAS_COMUNS_DO_RAMO = frozenset((
    "auto", "autos", "automovel", "automoveis", "carro", "carros", "veiculo", "moto",
    "seguro", "seguros", "segurado", "seguradora", "corretora", "negocio", "negocios",
    "roubo", "furto", "vidro", "vidros", "pacote", "plano", "perfil", "basico", "basica",
    "completo", "completa", "compreensivo", "prata", "ouro", "diamante", "bronze",
    "platina", "premium", "essencial", "assistencia", "servico", "servicos", "reserva",
    "residencial", "empresarial", "teste", "para", "dias", "mais", "super", "total",
))
# endpoints de IDENTIDADE da conta (não viram fixture; alimentam o diferencial)
RE_IDENTIDADE = re.compile(r"/usuario/(login|listaUsuarios|usuarioBuscarPreferencias)|/cadastros/cliente")


class Abortar(SystemExit):
    pass


def _versao(v: Any) -> Optional[int]:
    """a versão do cálculo (int, ou string de dígitos) — qualquer outra coisa: None."""
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, str) and v.strip().isdigit():
        return int(v.strip())
    return None


# ---------------------------------------------------------------------------
# Leitura do bruto → registros {t, m, u, s, req, body}
# ---------------------------------------------------------------------------
def _epoch(iso: str) -> float:
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()


def registros_do_har(caminho: Path) -> List[Dict[str, Any]]:
    har = json.loads(caminho.read_text(encoding="utf-8"))
    saida = []
    for e in har["log"]["entries"]:
        req, resp = e["request"], e["response"]
        if req["method"] == "OPTIONS":
            continue
        body = resp.get("content", {}).get("text")
        if body and resp.get("content", {}).get("encoding") == "base64":
            body = base64.b64decode(body).decode("utf-8", "replace")
        saida.append({
            "t": _epoch(e["startedDateTime"]) + (e.get("time") or 0) / 1000.0,
            "t0": _epoch(e["startedDateTime"]),
            "m": req["method"], "u": req["url"], "s": resp.get("status"),
            "req": (req.get("postData") or {}).get("text"), "body": body,
        })
    return saida


def registros_do_jsonl(caminho: Path) -> List[Dict[str, Any]]:
    saida = []
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        if linha.strip():
            r = json.loads(linha)
            r.setdefault("t0", r.get("t"))
            saida.append(r)
    return saida


def _json(texto: Any) -> Any:
    if texto is None or isinstance(texto, (dict, list)):
        return texto
    try:
        return json.loads(texto)
    except (TypeError, ValueError):
        return None


def endpoint_de(m: str, u: str) -> Optional[str]:
    p = urlparse(u)
    if not any(p.netloc.endswith(h) for h in HOSTS):
        return None
    caminho = p.path.rstrip("/")
    if m == "POST" and caminho.endswith("/calculo/calcularV2"):
        return "calcularV2"
    if m != "GET":
        return None
    if re.search(r"/calculo/cotacao/calculos/[^/]+/\d+$", caminho):
        return "cotacao_calculos"
    if re.search(r"/calculo/cotacao/versoes/[^/]+$", caminho):
        return "cotacao_versoes"
    if caminho.endswith("/calculo/negocio/busca/v2"):
        return "negocio_busca_v2"
    if re.search(r"/calculo/negocio/(?!busca|orcamentos)[^/]+$", caminho):
        return "negocio"
    if caminho.endswith("/cfg/seguradora/config"):
        return "cfg_seguradora_config"
    if caminho.endswith("/calculo/seguradorasRenovacao"):
        return "seguradoras_renovacao"
    if caminho.endswith("/calculo/fipeModelo"):
        return "fipe_modelo"
    return None


# ---------------------------------------------------------------------------
# O saneador de UMA gravação
# ---------------------------------------------------------------------------
class Saneador:
    def __init__(self, registros: List[Dict[str, Any]]):
        self.registros = registros
        self.pseudo: Dict[Tuple[str, str], str] = {}
        self.contadores: Dict[str, int] = {}
        # o conjunto do DIFERENCIAL: (tipo, caminho, valor) — o valor NUNCA é impresso
        self.sensiveis: List[Tuple[str, str, str]] = []
        self.partes_de_nome: Set[str] = set()
        self.palavras_protegidas: Set[str] = set()
        self._colher_nomes()

    # -- nomes do bruto (crivo e diferencial) --------------------------------
    def _colher_nomes(self) -> None:
        def anda(v: Any, caminho: str, ep: Optional[str]) -> None:
            if isinstance(v, dict):
                for k, s in v.items():
                    anda(s, f"{caminho}.{k}" if caminho else k, ep)
            elif isinstance(v, list):
                for s in v:
                    anda(s, caminho + "[]", ep)
            elif isinstance(v, str) and v.strip():
                chave = caminho.rsplit(".", 1)[-1].replace("[]", "").lower()
                if "permiss" in caminho.lower():
                    return
                pessoa = (any(caminho.endswith(c) for c in CAMINHOS_DE_NOME_DE_PESSOA)
                          or chave in ("customername", "seguradonome")
                          or (ep in ("negocio_busca_v2", "identidade") and chave in CHAVES_DE_NOME))
                if pessoa:
                    for parte in re.findall(r"[^\W\d_]+", v):
                        if len(parte) >= 4 and dobra(parte) not in PALAVRAS_COMUNS_DO_RAMO:
                            self.partes_de_nome.add(dobra(parte))
                if ep == "identidade" and len(v.strip()) >= 4:
                    self.sensiveis.append(("identidade_da_conta", caminho, v.strip()))
                if chave in ("seguradoratxt", "nomeseguradora") or (
                        ep == "seguradoras_renovacao" and chave == "nome"):
                    for parte in re.findall(r"[^\W\d_]+", v):
                        self.palavras_protegidas.add(dobra(parte))

        for r in self.registros:
            u = r.get("u") or ""
            ep = endpoint_de(r.get("m"), u)
            if ep is None and RE_IDENTIDADE.search(urlparse(u).path) and any(
                    urlparse(u).netloc.endswith(h) for h in HOSTS):
                ep = "identidade"
            if ep is None:
                continue
            anda(_json(r.get("req")), "req", ep)
            anda(_json(r.get("body")), "", ep)
        self.excluidas_do_crivo = sorted(self.partes_de_nome & self.palavras_protegidas)
        self.partes_de_nome -= self.palavras_protegidas
        if self.partes_de_nome:
            alt = "|".join(sorted((re.escape(p) for p in self.partes_de_nome), key=lambda s: (-len(s), s)))
            self._re_nome = re.compile(r"(?<![a-z0-9])(?:" + alt + r")(?![a-z0-9])")
        else:
            self._re_nome = None

    # -- primitivas -----------------------------------------------------------
    def pseudonimo(self, classe: str, valor: Any) -> str:
        bruto = str(valor).strip()
        chave = re.sub(r"\D", "", bruto) if classe in ("cpf", "telefone", "cep") else dobra(bruto)
        k = (classe, chave)
        if k not in self.pseudo:
            self.contadores[classe] = self.contadores.get(classe, 0) + 1
            self.pseudo[k] = f"<{classe}#{self.contadores[classe]:04d}>"
        return self.pseudo[k]

    def texto(self, s: str) -> str:
        """URL/chave fora → crivo de nome (posição a posição sobre o texto DOBRADO) → redigir.

        🔴 B1 (SPEC-128): a URL sai ANTES do crivo — 📊 04/10 uma seguradora devolveu, no
        texto do erro dela, a URL interna com `?key=` e a chave de API (8× na vivo_conta_b)."""
        s = sem_url_nem_chave(s)
        if self._re_nome is not None:
            dob = dobra(s)
            partes, fim = [], 0
            for m in self._re_nome.finditer(dob):
                partes.append(s[fim:m.start()])
                partes.append("<nome>")
                fim = m.end()
            partes.append(s[fim:])
            s = "".join(partes)
        return redigir_texto(s)

    def _sensivel(self, tipo: str, caminho: str, valor: Any) -> None:
        if valor is None or isinstance(valor, bool) or isinstance(valor, (dict, list)):
            return
        s = str(valor).strip()
        if len(s) >= 4:
            self.sensiveis.append((tipo, caminho, s))

    def _descartar(self, valor: Any, caminho: str) -> None:
        if isinstance(valor, dict):
            for k, v in valor.items():
                self._descartar(v, f"{caminho}.{k}")
        elif isinstance(valor, list):
            for v in valor:
                self._descartar(v, caminho + "[]")
        else:
            self._sensivel("descartado", caminho, valor)

    # -- projeção pela lista branca ------------------------------------------
    def projetar(self, valor: Any, lista: frozenset, caminho: str = "") -> Any:
        if isinstance(valor, dict):
            saida: Dict[str, Any] = {}
            for k, v in valor.items():
                c = f"{caminho}.{k}" if caminho else str(k)
                if isinstance(v, (dict, list)):
                    if any(w == c or w.startswith(c + ".") or w.startswith(c + "[]") for w in lista):
                        saida[str(k)] = self.projetar(v, lista, c)
                    else:
                        self._descartar(v, c)
                elif c in lista:
                    saida[str(k)] = self.folha(str(k), c, v)
                else:
                    self._sensivel("descartado", c, v)
            return saida
        if isinstance(valor, list):
            if caminho.endswith("resultados[].parcelamentos"):
                # 📊 os parcelamentos eram 1,3 MB dos 2,5 MB da R1 (22 opções por oferta,
                # repetidas em 28 rodadas). O contrato prova a LEITURA: 3 bastam. São
                # preços (folha mantida), não segredo — não entram no diferencial.
                valor = valor[:PARCELAMENTOS_POR_OFERTA]
            return [self.projetar(v, lista, caminho + "[]") for v in valor]
        return self.folha(caminho.rsplit(".", 1)[-1], caminho, valor)

    def folha(self, chave: str, caminho: str, v: Any) -> Any:
        chave = chave.replace("[]", "")
        if chave in CHAVES_DE_PDF:
            self._sensivel("pdf", caminho, v)
            return "<removido:pdf>" if v else v
        if chave in CANONICO:
            if v is None:
                return None
            c = CANONICO[chave]
            return float(c) if isinstance(v, float) else (str(c) if isinstance(v, str) else c)
        classe = PSEUDONIMO_POR_CHAVE.get(chave)
        if chave == "nome" and any(caminho.endswith(c) for c in CAMINHOS_DE_NOME_DE_PESSOA):
            classe = "pessoa"
        if caminho.endswith("negocio.id"):
            classe = "negocio"
        if classe is None and isinstance(v, str) and _RE_UUID.search(v):
            classe = "id"  # uuid em caminho mantido nunca sai cru
        if classe:
            if v is None or v == "" or isinstance(v, bool):
                return v
            self._sensivel(classe, caminho, v)  # numérica vira string ANTES de conferir
            return self.pseudonimo(classe, v)
        if isinstance(v, str):
            return self.texto(v)
        return v

    # -- a gravação inteira ---------------------------------------------------
    def fixture(self, rotulo: str, conta: str) -> Dict[str, Any]:
        regs = [r for r in self.registros if endpoint_de(r.get("m"), r.get("u") or "")]
        pedidos = [r for r in regs if endpoint_de(r["m"], r["u"]) == "calcularV2"]
        t_ref = pedidos[0]["t0"] if pedidos else (regs[0]["t0"] if regs else 0.0)

        def t_s(r: Dict[str, Any]) -> float:
            return round(float(r["t"]) - float(t_ref), 3)

        lb = {ep: frozenset(ps) for ep, ps in LISTA_BRANCA_POR_ENDPOINT.items()}
        saida: Dict[str, Any] = {"formato": FORMATO, "rotulo": rotulo, "conta": conta, "calculos": []}
        # 🔴 P5: a rodada se liga ao cálculo por (id do negócio, VERSÃO) — 📊 E7: dois
        # recálculos SIMULTÂNEOS no mesmo negócio existem; pelo id só, as rodadas da v3 iam
        # para o cálculo da v4.
        por_id: Dict[Tuple[str, Optional[int]], Dict[str, Any]] = {}
        secoes: Dict[str, List[Any]] = {k: [] for k in (
            "versoes", "negocio", "busca_v2", "config", "seguradoras_renovacao", "fipe_modelo")}
        vistos_cfg: Set[str] = set()
        for r in sorted(regs, key=lambda x: (x["t0"], x["t"])):
            ep = endpoint_de(r["m"], r["u"])
            corpo = _json(r.get("body"))
            if ep == "calcularV2":
                pedido = _json(r.get("req")) or {}
                resp = corpo if isinstance(corpo, dict) else {}
                id_bruto = str(resp.get("idIntegracao") or f"sem_id_{len(por_id)}")
                versao_pedida = _versao(resp.get("versao"))
                calc = {"id": self.pseudonimo("negocio", id_bruto),
                        "pedido": {"t_s": t_s(r), "corpo": self.projetar(pedido, lb["calcularV2"])},
                        "resposta_pedido": {"t_s": t_s(r), "corpo": self.projetar(resp, lb["calcularV2_resposta"])},
                        "rodadas": []}
                por_id[(id_bruto, versao_pedida)] = calc
                saida["calculos"].append(calc)
            elif ep == "cotacao_calculos":
                partes = urlparse(r["u"]).path.rstrip("/").split("/")
                id_bruto, versao = partes[-2], int(partes[-1])
                # a resposta do pedido sem versão (None) é a de qualquer versão do negócio
                calc = por_id.get((id_bruto, versao)) or por_id.get((id_bruto, None))
                if calc is None:  # rodada sem o pedido na captura: um cálculo só de rodadas
                    calc = {"id": self.pseudonimo("negocio", id_bruto), "rodadas": []}
                    por_id[(id_bruto, versao)] = calc
                    saida["calculos"].append(calc)
                calc["rodadas"].append({"t_s": t_s(r), "versao": versao, "status": r.get("s"),
                                        "corpo": self.projetar(corpo if isinstance(corpo, list) else [], lb[ep])})
            elif ep == "cotacao_versoes":
                secoes["versoes"].append({"t_s": t_s(r), "corpo": self.projetar(
                    corpo if isinstance(corpo, list) else [], lb[ep])})
            elif ep == "negocio":
                secoes["negocio"].append({"t_s": t_s(r), "corpo": self.projetar(
                    corpo if isinstance(corpo, dict) else {}, lb[ep])})
            elif ep == "negocio_busca_v2":
                secoes["busca_v2"].append({"t_s": t_s(r), "corpo": self.contagens_da_busca(corpo)})
            elif ep == "cfg_seguradora_config":
                cfg = self.config(corpo)
                assinatura = json.dumps(cfg, sort_keys=True)
                if assinatura not in vistos_cfg:  # 📊 a tela repete a mesma lista
                    vistos_cfg.add(assinatura)
                    secoes["config"].append({"t_s": t_s(r), "corpo": cfg})
            elif ep in ("seguradoras_renovacao", "fipe_modelo"):
                proj = self.projetar(corpo if isinstance(corpo, list) else [], lb[ep])
                if all(json.dumps(x["corpo"], sort_keys=True) != json.dumps(proj, sort_keys=True)
                       for x in secoes[ep]):
                    secoes[ep].append({"t_s": t_s(r), "corpo": proj})
        for k, v in secoes.items():
            if v:
                saida[k] = v
        return saida

    def contagens_da_busca(self, corpo: Any) -> Dict[str, Any]:
        linhas = corpo.get("data") if isinstance(corpo, dict) else None
        linhas = linhas if isinstance(linhas, list) else []
        self._descartar(corpo, "busca_v2")
        ramos: Dict[int, int] = {}
        status: Dict[int, int] = {}
        qtd = 0
        for ln in linhas:
            for n in (ln.get("negocios") or []) if isinstance(ln, dict) else []:
                if isinstance(n, dict):
                    qtd += 1
                    ramos[n.get("ramo")] = ramos.get(n.get("ramo"), 0) + 1
                    status[n.get("status")] = status.get(n.get("status"), 0) + 1
        return {"qtd_linhas": len(linhas), "qtd_negocios": qtd,
                "por_ramo": [{"ramo": k, "qtd": v} for k, v in sorted(ramos.items(), key=lambda x: str(x[0]))],
                "por_status": [{"status": k, "qtd": v} for k, v in sorted(status.items(), key=lambda x: str(x[0]))]}

    def config(self, corpo: Any) -> List[Dict[str, Any]]:
        itens = corpo if isinstance(corpo, list) else []
        self._descartar(corpo, "config")
        saida = []
        nao_codigo = re.compile(r"^(perc|ativo|configsGlobais|apolicesBaixar|parcelasBaixar|cargaIniciada|"
                                r"credenciaisValidas|customStatusRamo|cartaoSeguradora|grupoAfinidade|"
                                r"ambienteCalculo|senha|senhaWs|login|loginWs|usuario)", re.IGNORECASE)
        for it in itens:
            if not isinstance(it, dict):
                continue
            cs = it.get("configsSeg") if isinstance(it.get("configsSeg"), dict) else {}
            campos = sorted(k for k, v in cs.items()
                            if v not in (None, "", [], {}) and not isinstance(v, bool) and not nao_codigo.match(k))
            saida.append({
                "seguradora": it.get("seguradora"),
                "nomeSeguradora": self.texto(str(it.get("nomeSeguradora") or "")),
                "ativo": it.get("ativo"),
                "credenciaisValidas": cs.get("credenciaisValidas"),
                "campos_de_codigo": campos,
            })
        return sorted(saida, key=lambda x: (str(x["seguradora"]), x["nomeSeguradora"]))


# ---------------------------------------------------------------------------
# Conferências
# ---------------------------------------------------------------------------
def folhas_texto(valor: Any) -> List[str]:
    saida: List[str] = []
    if isinstance(valor, dict):
        for v in valor.values():
            saida.extend(folhas_texto(v))
    elif isinstance(valor, list):
        for v in valor:
            saida.extend(folhas_texto(v))
    elif valor is not None and not isinstance(valor, bool):
        saida.append(str(valor))
    return saida


_RE_UUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
_RE_MARCA = re.compile(r"<(?:[a-z_]+#\d{4}|removido:[a-z]+|redacted:[a-z_\-]+|nome)>")


def diferencial(fixture: Dict[str, Any], san: Saneador) -> Tuple[List[Tuple[str, str]], int, int]:
    """Procura cada valor sensível do BRUTO na SAÍDA, em 3 formas + partes de nome.
    Devolve ([(tipo, caminho)] achados, N procurados, excluídos por serem folha MANTIDA)."""
    folhas = [_RE_MARCA.sub(" ", f) for f in folhas_texto(fixture)]
    dobradas = [dobra(f) for f in folhas]
    digitos = [re.sub(r"[.\-/\s()]", "", f) for f in folhas]
    mantidas = set(folhas) | set(dobradas)
    achados: List[Tuple[str, str]] = []
    excluidos = 0
    vistos: Set[str] = set()
    n = 0
    for tipo, caminho, valor in san.sensiveis:
        if valor in vistos:
            continue
        vistos.add(valor)
        dob = dobra(valor)
        palavras = set(re.findall(r"[a-z]+", dob))
        if tipo == "descartado" and (valor in mantidas or dob in mantidas) or tipo == "descartado" and (
                palavras and palavras <= san.palavras_protegidas and not re.search(r"\d", valor)):
            # folha MANTIDA, ou só palavras de NOME DE SEGURADORA (ex.: o `nome` da
            # config "Liberty" dentro do mantido "Liberty Site") — não é segredo
            excluidos += 1
            continue
        n += 1
        so_dig = re.sub(r"\D", "", valor)
        if re.fullmatch(r"[\d.\-/\s()]+", valor):
            pad = re.compile(r"(?<![\d.,])" + re.escape(so_dig) + r"(?![\d.,])") if len(so_dig) >= 4 else None
            hit = bool(pad) and (any(pad.search(f) for f in folhas) or
                                 (len(so_dig) >= 8 and any(so_dig in d for d in digitos)))
        else:
            hit = any(valor in f for f in folhas) or (len(dob) >= 4 and any(dob in d for d in dobradas))
            if not hit and len(so_dig) >= 8:
                hit = any(so_dig in d for d in digitos)
        if hit:
            achados.append((tipo, caminho))
    for parte in sorted(san.partes_de_nome):
        n += 1
        pad = re.compile(r"(?<![a-z0-9])" + re.escape(parte) + r"(?![a-z0-9])")
        if any(pad.search(d) for d in dobradas):
            achados.append(("parte_de_nome", "(texto livre)"))
    excluidos += len(san.excluidas_do_crivo)
    return achados, n, excluidos


def caminhos_fora_da_lista(fixture: Dict[str, Any]) -> List[str]:
    lb = lista_branca_do_arquivo()
    return sorted({c for c in caminhos_de(fixture) if not caminho_permitido(c, lb)})


def _sem_cr(b: bytes) -> bytes:
    """o checkout do Windows (core.autocrlf) pode devolver CRLF: o conteudo e o mesmo."""
    return b.replace(bytes((13, 10)), bytes((10,)))


def serializar(obj: Any, compacto: bool = True) -> bytes:
    if compacto:  # fixture: compacta (o juiz lê com `python -m json.tool`)
        return (json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    return (json.dumps(obj, ensure_ascii=False, indent=1) + "\n").encode("utf-8")


def sanear(registros: List[Dict[str, Any]], rotulo: str, conta: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    san = Saneador(registros)
    fx = san.fixture(rotulo, conta)
    fora = caminhos_fora_da_lista(fx)
    if fora:
        raise Abortar(f"[{rotulo}] ABORTA: {len(fora)} caminho(s) fora da lista branca: {fora[:10]}")
    if any(_RE_UUID.search(f) for f in folhas_texto(fx)):
        raise Abortar(f"[{rotulo}] ABORTA: uuid cru na saída")
    url = sorted({t for f in folhas_texto(fx) for t in tem_url_ou_chave(f)})
    if url:
        raise Abortar(f"[{rotulo}] ABORTA: URL/chave em texto mantido, TIPOS {url}")
    vaz = tem_vazamento(fx)
    if vaz:
        raise Abortar(f"[{rotulo}] ABORTA: tem_vazamento acusou os TIPOS {vaz}")
    achados, n, excl = diferencial(fx, san)
    print(f"[{rotulo}] diferencial: {len(achados)} de {n} (excluídos por serem folha mantida: {excl})")
    if achados:
        for tipo, caminho in sorted(set(achados))[:40]:
            print(f"   ACHOU  tipo={tipo}  caminho={caminho}")
        raise Abortar(f"[{rotulo}] ABORTA: o diferencial achou {len(achados)} valor(es) do bruto na saída")
    rodadas = sum(len(c.get("rodadas", [])) for c in fx["calculos"])
    meta = {"rodadas": rodadas, "calculos": len(fx["calculos"]),
            "pseudonimos": dict(sorted(san.contadores.items()))}
    return fx, meta


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--conferir", action="store_true", help="roda tudo, NÃO grava; compara com o que está em disco")
    ap.add_argument("--saida", default=str(SAIDA_PADRAO))
    ap.add_argument("--intake", default=str(INTAKE))
    ap.add_argument("--jsonl", help="captura ao vivo (uma resposta por linha)")
    ap.add_argument("--rotulo", help="rótulo da captura ao vivo (vivo_xxx)")
    ap.add_argument("--conta", default="conta_a", choices=("conta_a", "conta_b"))
    a = ap.parse_args(argv)
    saida = Path(a.saida)

    trabalhos: List[Tuple[str, str, List[Dict[str, Any]], str]] = []
    if a.jsonl:
        if not a.rotulo or not re.fullmatch(r"vivo_[a-z0-9_]+", a.rotulo):
            raise Abortar("--jsonl exige --rotulo vivo_<a-z0-9_>")
        p = Path(a.jsonl)
        trabalhos.append((a.rotulo, a.conta, registros_do_jsonl(p), hashlib.sha256(p.read_bytes()).hexdigest()))
    else:
        for rotulo, rel, conta in GRAVACOES:
            p = Path(a.intake) / rel
            if not p.exists():
                raise Abortar(f"[{rotulo}] bruto ausente nesta máquina (G2 só roda onde há intake)")
            trabalhos.append((rotulo, conta, registros_do_har(p), hashlib.sha256(p.read_bytes()).hexdigest()))

    arquivos: Dict[str, bytes] = {}
    manifesto_novo: Dict[str, Any] = {}
    for rotulo, conta, regs, sha in trabalhos:
        fx, meta = sanear(regs, rotulo, conta)
        nome = f"{rotulo}.json"
        arquivos[nome] = serializar(fx)
        manifesto_novo[rotulo] = {"arquivo": nome, "origem": "har" if not a.jsonl else "jsonl",
                                  "conta": conta, "entradas_lidas": len(regs), **meta,
                                  "parcelamentos_por_oferta": PARCELAMENTOS_POR_OFERTA,
                                  "sha256_do_bruto": sha}

    man_path = saida / "MANIFESTO.json"
    manifesto = {"formato": FORMATO, "gerador": "backend/scripts/agger_fixtures_saneadas.py", "fixtures": {}}
    if man_path.exists():
        manifesto["fixtures"].update(json.loads(man_path.read_text(encoding="utf-8")).get("fixtures", {}))
    manifesto["fixtures"].update(manifesto_novo)
    manifesto["fixtures"] = dict(sorted(manifesto["fixtures"].items()))
    if tem_vazamento(manifesto):
        raise Abortar("MANIFESTO: tem_vazamento acusou")
    arquivos["MANIFESTO.json"] = serializar(manifesto, compacto=False)

    if a.conferir:
        iguais = all((saida / n).exists() and _sem_cr((saida / n).read_bytes()) == b for n, b in arquivos.items())
        print(f"conferir: {len(arquivos)} arquivo(s) gerado(s) em memória; idênticos ao disco: {iguais}")
        return 0
    saida.mkdir(parents=True, exist_ok=True)
    for n, b in arquivos.items():
        (saida / n).write_bytes(b)
    print(f"gravados: {sorted(arquivos)} em {saida.relative_to(RAIZ) if saida.is_relative_to(RAIZ) else saida}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Abortar as e:
        print(str(e), file=sys.stderr)
        sys.exit(2)
