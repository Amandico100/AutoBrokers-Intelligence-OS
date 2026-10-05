# -*- coding: utf-8 -*-
"""O ROBÔ do Agger — SPEC-129-B U3 (interface §6.4).

    disparar(sessao, pedido, coberturas, negocio_ref=None) → Disparo      POST calcularV2 (negócio novo ou versão)
    acompanhar(sessao, disparo, ao_evento=..., anterior=...) → Rodada     GET calculos/{negocio}/{versao}
    recalcular(sessao, negocio_ref, versao_base=..., ajuste=...) → Disparo nova versão a partir da versão CERTA
    pessoa_mexeu_recentemente(sessao, negocio_ref, versoes_do_robo=...)   a regra D-MC-47 (§4.1)
    copiar_pdfs(sessao, disparo) → {(seguradora, pacote, tipo): bytes}     baixado DENTRO da página

🔴 D-129B-02: TODA leitura e montagem acontece DENTRO da página (`Sessao.avaliar`, montador.js). O que volta ao
Python já passou pela lista branca do endpoint em JS (`window.__abM.filtrar`) e é conferido DE NOVO aqui:
caminho fora da lista, marca de PDF trocada, URL/chave em texto (`redaction.tem_url_ou_chave`) ou chave proibida
(`contrato.CHAVES_PROIBIDAS_NA_OFERTA`) → o item é DESCARTADO e sai um evento `erro_de_leitura`.

O tempo (`t_s` das rodadas e eventos) = segundos desde `Disparo.t0` (época, `time.time()`): cresce entre
processos, então a rodada de uma retomada nunca é "atrasada" para o leitor.
⛔ Nada aqui loga pedido, corpo, token ou resposta. Exceções carregam só códigos e nomes de campo.
"""
from __future__ import annotations

import asyncio
import base64
import dataclasses
import logging
import re
import time
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Optional, Set, Tuple

from ..redaction import sem_url_nem_chave, tem_url_ou_chave
from .contrato import CHAVES_PROIBIDAS_NA_OFERTA, RAMO_AUTO, Ajuste, Evento, RodadaDoCalculo
from .leitor_agger import (
    LISTA_BRANCA_POR_ENDPOINT, caminho_permitido, caminhos_de, eventos_entre, ler_resposta, ler_rodada,
)
from .presets import CHAVES_DE_COBERTURA

logger = logging.getLogger("portal_worker.multicalculo")

# 🔴 A MARCA do robô (D-MC-47, §4.1): o negócio do Agger não tem observação/etiqueta (📊 0 em 24 leituras), mas o
# `correlationId` que o cliente gera volta GRAVADO na versão e no negócio (📊 15/15 na 128; 8/8 em 05/10). O robô
# gera todo correlationId com este prefixo — "pessoa mexeu" = versão SEM ele. Hex, para o id continuar com cara de
# UUID (o app manda UUID). ⚠️ Não é pesquisável (📊 busca/v2?textoBusca=ab0b → 0): serve para LER, não para achar.
PREFIXO_DA_MARCA = "ab0b"

ERRO_DE_LEITURA = "erro_de_leitura"
LISTA_CALCULOS = list(LISTA_BRANCA_POR_ENDPOINT["cotacao_calculos"])
LISTA_RESPOSTA = list(LISTA_BRANCA_POR_ENDPOINT["calcularV2_resposta"])
# O que a página troca por MARCA. As de PDF são conferidas à letra (a URL do PDF é segredo: leva assinatura/caminho
# do arquivo). O nº de cálculo da seguradora não é segredo — o JS o marca por economia; aqui só se exige que não
# traga URL/chave (as fixtures da 128 o trazem pseudonimizado, "<calculo#0009>").
MARCAS_PERMITIDAS = {"pathPdf": "<removido:pdf>", "pdfFileNameAgger": "<removido:pdf>"}
POST_TIMEOUT_S = 60
PDF_MAX_BYTES = 15 * 1024 * 1024


class DisparoIncerto(Exception):
    """O POST PODE ter saído (timeout, rede, 5xx): nunca repetir."""


class DisparoRecusado(Exception):
    """Nada saiu, ou o servidor recusou com resposta clara."""


@dataclass(frozen=True)
class Disparo:
    negocio_ref: str
    versao: int
    t0: float


# ======================================================================================================================
# O pedido (dict decifrado pelo motor, `PedidoDeCalculo.para_dict()`) → a cotação, SEM credencial nenhuma
# ======================================================================================================================
def correlation_id() -> str:
    u = uuid.uuid4().hex
    return f"{PREFIXO_DA_MARCA}{u[4:8]}-{u[8:12]}-4{u[13:16]}-a{u[17:20]}-{u[20:32]}"


def _iso(d: Any) -> Optional[str]:
    """'AAAA-MM-DD' → '…T03:00:00.000Z' (📊 15/15 corpos da tela: meia-noite de Brasília em UTC)."""
    if d in (None, ""):
        return None
    s = str(d)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return f"{s}T03:00:00.000Z"
    return s


def _int(v: Any, campo: str) -> Optional[int]:
    if v is None or v == "":
        return None
    if isinstance(v, bool):
        raise DisparoRecusado(f"campo {campo}: código esperado")
    if isinstance(v, int):
        return v
    if isinstance(v, str) and v.strip().isdigit():
        return int(v.strip())
    raise DisparoRecusado(f"campo {campo}: sem código medido para o valor recebido")


_SEXO = {"m": "M", "masculino": "M", "f": "F", "feminino": "F"}
# 📊 relacComSegurado = 1 em 15/15 corpos de condutor = o próprio segurado ("Próprio" é a 2ª opção da tela,
# índice 1). Os outros códigos não foram medidos: chegam como código ou o disparo é recusado ANTES do POST.
_RELACAO = {"proprio": 1, "próprio": 1}
# 📊 Os padrões do questionário que a TELA manda quando ninguém responde (15/15 corpos da 128).
PADROES_DO_QUESTIONARIO = {"kmAnual": 6000, "tpUso": 1, "garagemResidencia": "2", "garagemTrabalho": "0",
                           "garagemEstudo": "0", "rastreador": "0", "antiFurto": "0", "periodoUso": "0",
                           "pctAjuste": 100, "tpResidencia": 1}


def cotacao_do_pedido(pedido: Dict[str, Any], *, agora: Optional[datetime] = None) -> Dict[str, Any]:
    """PURA. O que a página completa depois: veículo (buscaPlaca/fipeModelo), endereço (cep), seguradora anterior
    (seguradorasRenovacao) e o `calculos[]` (config + coberturas). Levanta `DisparoRecusado` antes de qualquer rede."""
    seg = dict(pedido.get("segurado") or {})
    vei = dict(pedido.get("veiculo") or {})
    per = dict(pedido.get("pernoite") or {})
    con = dict(pedido.get("condutor") or {})
    ren = dict(pedido.get("renovacao") or {})
    que = dict(pedido.get("questionario") or {})
    faltam = [c for c, v in (("segurado.cpf_cnpj", seg.get("cpf_cnpj")), ("segurado.nome", seg.get("nome")),
                             ("segurado.cep", seg.get("cep"))) if not v]
    if not (vei.get("placa") or vei.get("fipe")):
        faltam.append("veiculo.placa|veiculo.fipe")
    if faltam:
        raise DisparoRecusado("pedido sem: " + ", ".join(faltam))
    doc = re.sub(r"\D", "", str(seg.get("cpf_cnpj")))
    sexo = _SEXO.get(str(seg.get("sexo") or "").strip().lower(), seg.get("sexo"))
    segurado = {
        "nome": seg.get("nome"), "tipoPessoa": seg.get("tipo_pessoa") or ("J" if len(doc) == 14 else "F"),
        "cpfCnpj": doc, "estadoCivil": _int(seg.get("estado_civil"), "segurado.estado_civil"),
        "dataNasc": _iso(seg.get("nascimento")), "sexo": sexo, "fone1": seg.get("telefone") or "",
        "cep": re.sub(r"\D", "", str(seg.get("cep"))), "email": seg.get("email") or "",
        "residLogradouro": None, "residNumero": None, "residBairro": None, "residCidade": None, "residUF": None,
        "isPCD": bool(seg.get("pcd")) if seg.get("pcd") is not None else False,
    }
    hoje = (agora or datetime.now(timezone.utc)).date()
    tempo = _int(con.get("tempo_habilitacao"), "condutor.tempo_habilitacao")
    prim = None
    if tempo is not None:
        try:
            prim = hoje.replace(year=hoje.year - tempo).isoformat()
        except ValueError:
            prim = hoje.replace(year=hoje.year - tempo, day=28).isoformat()
    relacao = con.get("relacao_com_segurado")
    relacao = _RELACAO.get(str(relacao).strip().lower(), relacao) if isinstance(relacao, str) else relacao
    condutor = {
        "relacComSegurado": _int(relacao, "condutor.relacao_com_segurado") or 1,
        "tpResidencia": PADROES_DO_QUESTIONARIO["tpResidencia"], "dataPrimHabil": _iso(prim), "principal": True,
        "cpfCnpj": re.sub(r"\D", "", str(con.get("cpf") or doc)), "nome": con.get("nome") or seg.get("nome"),
        "dataNasc": _iso(con.get("nascimento") or seg.get("nascimento")),
        "sexo": _SEXO.get(str(con.get("sexo") or "").strip().lower(), con.get("sexo") or sexo),
        "estadoCivil": _int(con.get("estado_civil", seg.get("estado_civil")), "condutor.estado_civil"),
        "tempoHabilitacao": tempo,
    }
    km = que.get("km_mensal")
    km_anual = (int(km) * 12) if isinstance(km, (int, float)) and not isinstance(km, bool) else None
    jovem = con.get("jovem_condutor")
    automovel = {
        "descricao": vei.get("modelo"), "fabricante": _int(vei.get("fabricante"), "veiculo.fabricante"),
        "anoFabricacao": _int(vei.get("ano_fabricacao"), "veiculo.ano_fabricacao"),
        "anoModelo": _int(vei.get("ano_modelo"), "veiculo.ano_modelo"),
        "combustivel": _int(vei.get("combustivel"), "veiculo.combustivel"),
        "fipe": (re.sub(r"\D", "", str(vei["fipe"])) or None) if vei.get("fipe") else None,
        "chassi": vei.get("chassi"), "placa": vei.get("placa"),
        "pctAjuste": _int(vei.get("percentual_fipe"), "veiculo.percentual_fipe") or PADROES_DO_QUESTIONARIO["pctAjuste"],
        "financiado": None, "cepCirculacao": None,
        "cepPernoite": re.sub(r"\D", "", str(per.get("cep_pernoite") or seg.get("cep"))),
        "tpLocalPernoite": None, "kmAnual": km_anual or PADROES_DO_QUESTIONARIO["kmAnual"], "passageiros": None,
        "portas": None, "jovemSexo": None, "zeroKm": bool(vei.get("zero_km")), "jovemCondutor": bool(jovem),
        "jovemIdade": None, "tpUso": _int(vei.get("uso"), "veiculo.uso") or PADROES_DO_QUESTIONARIO["tpUso"],
        "gasInstalValor": 0, "tipoIsencao": 0, "tipo": "v", "condutores": [condutor],
        "blindado": bool(vei.get("blindado")), "alienado": bool(vei.get("alienado")), "kitGas": bool(vei.get("kit_gas")),
        "rastreador": PADROES_DO_QUESTIONARIO["rastreador"], "antiFurto": PADROES_DO_QUESTIONARIO["antiFurto"],
        "valReferenciado": None,
        "garagemResidencia": str(per["garagem_residencia"]) if per.get("garagem_residencia") is not None else PADROES_DO_QUESTIONARIO["garagemResidencia"],
        "garagemTrabalho": str(per["garagem_trabalho"]) if per.get("garagem_trabalho") is not None else PADROES_DO_QUESTIONARIO["garagemTrabalho"],
        "garagemEstudo": str(per["garagem_estudo"]) if per.get("garagem_estudo") is not None else PADROES_DO_QUESTIONARIO["garagemEstudo"],
        "associado": False, "periodoUso": PADROES_DO_QUESTIONARIO["periodoUso"],
    }
    renovacao = ren.get("renovacao") is True
    agora_utc = (agora or datetime.now(timezone.utc)).replace(microsecond=0)
    vig_ini = _iso(ren.get("vigencia_inicio")) or agora_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    vig_fim = _iso(ren.get("vigencia_fim"))
    if not vig_fim:
        try:
            vig_fim = agora_utc.replace(year=agora_utc.year + 1).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        except ValueError:
            vig_fim = (agora_utc + timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    cid = correlation_id()
    cot = {
        "segurado": segurado, "automoveis": [automovel],
        "results": {k: {"errors": [], "successes": []} for k in ("main", "alternatives", "all", "porAssinatura", "ofertaCruzada")},
        "loaded": False, "isClearDraft": False, "tipo": 5, "integracaoInfo": 1,
        "vigenciaIni": vig_ini, "vigenciaFim": vig_fim,
        "renovacao": renovacao, "renovacaoGarantida": False,
        "bonusAnterior": (_int(ren.get("bonus_anterior"), "renovacao.bonus_anterior") or 0) if renovacao else 0,
        "sinistrosAnterior": (_int(ren.get("sinistros_anterior"), "renovacao.sinistros_anterior") or 0) if renovacao else 0,
        "numeroRenovacao": (str(ren["numero_apolice_anterior"]) if renovacao and ren.get("numero_apolice_anterior") else None),
        "seguradoraAnteriorId": None,   # a página resolve pelo `seguradorasRenovacao` (o id é do Agger)
        "vigFimAnterior": _iso(ren.get("fim_vigencia_anterior")) if renovacao else None,
        "CI": None, "tpCobertura": 1, "ramo": RAMO_AUTO, "correlationId": cid,
    }
    if renovacao and not ren.get("seguradora_anterior"):
        raise DisparoRecusado("pedido sem: renovacao.seguradora_anterior")
    return {"cotacao": cot, "seguradora_anterior": str(ren.get("seguradora_anterior")) if renovacao else None,
            "seguradoras": [int(s) for s in (pedido.get("seguradoras") or [])],
            "comissao": (pedido.get("comissao_desconto") or {}).get("comissao_percentual"),
            "desconto": (pedido.get("comissao_desconto") or {}).get("desconto_percentual")}


# ======================================================================================================================
# O JavaScript (roda em `Sessao.avaliar`; `window.__abM` = montador.js)
# ======================================================================================================================
_JS_COMUM = """
  const M = window.__abM;
  const pegar = async (u, a) => { try { const r = await fetch(u, {headers: {Authorization: a}});
      const t = await r.text(); let d = null; try { d = JSON.parse(t) } catch (e) {} return [r.status, d]; }
    catch (e) { return [0, null]; } };
  const norm = s => String(s || '').normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').toLowerCase().trim();
"""

# PREPARA o corpo (window.__abCorpo). Nada sai ainda. Devolve só o resumo (códigos de seguradora, contagem).
JS_PREPARAR = """async (a) => {""" + _JS_COMUM + """
  const [s1, segs] = await pegar(a.api + '/calculo/seguradoras', a.tApi);
  if (s1 !== 200 || !Array.isArray(segs)) return {erro: 'seguradoras_http_' + s1};
  const cot = a.cot;
  let negocio = null;
  if (a.negocio_ref) {
    const [sv, vs] = await pegar(a.pdocs + '/calculo/cotacao/versoes/' + encodeURIComponent(a.negocio_ref), a.tPdocs);
    if (sv !== 200 || !Array.isArray(vs) || !vs.length) return {erro: 'versoes_http_' + sv};
    let v = null;
    if (a.versao_base != null) v = vs.find(x => x && x.versao === a.versao_base);
    else v = vs.reduce((m, x) => (x && (!m || x.versao > m.versao)) ? x : m, null);
    if (!v) return {erro: 'versao_base_inexistente'};
    if (a.da_versao) {           // RECÁLCULO: a cotação da versão-base (sem os campos do servidor)
      const FORA = new Set(['aplicacaoId', 'corretoraId', 'customerId', 'customerIp', 'customerName', 'dataCriacao',
        'createdAt', 'updatedAt', 'usuario', 'usuarioId', 'status', 'textoBusca', 'ofertasCruzadas', 'versaoAtual',
        'versaoOrigem', 'numeroRenovacaoTxt', 'vigenciaFimTxt', 'vigenciaIniTxt', 'isAgger', 'calculos', 'correlationId']);
      for (const k of Object.keys(cot)) if (!['results', 'loaded', 'isClearDraft', 'correlationId'].includes(k)) delete cot[k];
      for (const [k, x] of Object.entries(v)) if (!FORA.has(k)) cot[k] = x;
      cot.calculos = M.montarDaVersao(segs, v);
    }
    cot.id = v.id; cot.negocioId = v.negocioId; cot.idIntegracao = v.idIntegracao; cot.versao = v.versao;
    negocio = {id: v.negocioId};
  }
  if (!a.da_versao) {
    const auto = cot.automoveis[0];
    let bp = null, fm = null;
    if (auto.placa) {
      const [sp, d] = await pegar(a.pdocs + '/calculo/buscaPlaca?placa=' + encodeURIComponent(auto.placa), a.tPdocs);
      if (sp === 200 && d && d.fipe) bp = d;
    }
    const fipe = auto.fipe || (bp && bp.fipe);
    const ano = auto.anoModelo || (bp && bp.anoMod);
    if (!fipe || !ano) return {erro: 'veiculo_sem_fipe_ou_ano'};
    const f = String(fipe); const fipeFmt = f.slice(0, f.length - 1) + '-' + f.slice(-1);
    const [sf, d2] = await pegar(a.pdocs + '/calculo/fipeModelo?ano=' + ano + '&fipe=' + fipeFmt + '&zero=' + (!!auto.zeroKm), a.tPdocs);
    if (sf !== 200 || !Array.isArray(d2) || !d2.length) return {erro: 'fipe_modelo_http_' + sf};
    fm = d2;
    cot.automoveis = [M.montarAutomovel(auto, bp, fm)];
    const [sc, ce] = await pegar(a.pdocs + '/calculo/cep?cep=' + encodeURIComponent(cot.segurado.cep), a.tPdocs);
    if (sc === 200 && ce) for (const k of ['logradouro', 'cidade', 'bairro', 'uf']) if (ce[k] != null) cot.segurado[k] = ce[k];
    if (cot.renovacao) {
      const [sr, rs] = await pegar(a.pdocs + '/calculo/seguradorasRenovacao', a.tPdocs);
      if (sr !== 200 || !Array.isArray(rs)) return {erro: 'seguradoras_renovacao_http_' + sr};
      const alvo = norm(a.seguradora_anterior);
      let achou = rs.filter(x => x && String(x.id) === String(a.seguradora_anterior));
      if (!achou.length) achou = rs.filter(x => x && x.auto !== false && (norm(x.nome) === alvo || norm(x.nome).startsWith(alvo + ' ')));
      if (achou.length !== 1) return {erro: achou.length ? 'seguradora_anterior_ambigua' : 'seguradora_anterior_desconhecida'};
      cot.seguradoraAnteriorId = String(achou[0].id); cot.seguradoraSelectedId = String(achou[0].id);
    }
    let calc = M.montarCalculos(segs, a.cob, a.comissao, a.desconto);
    if (a.seguradoras && a.seguradoras.length) calc = calc.filter(c => a.seguradoras.includes(c.seguradora));
    cot.calculos = calc;
  }
  if (a.ajuste) { if (!M.aplicarAjuste(cot, a.ajuste)) return {erro: 'ajuste_sem_alvo'}; }
  if (!cot.calculos || !cot.calculos.length) return {erro: 'nenhuma_seguradora'};
  window.__abCorpo = {cotacao: cot, negocio: negocio, correlationId: cot.correlationId};
  return {ok: true, seguradoras: cot.calculos.map(c => c.seguradora)};
}"""

# ENVIA o corpo preparado. Devolve só o status e o que a lista branca de `calcularV2_resposta` deixa.
JS_ENVIAR = """async (a) => {
  const M = window.__abM; const corpo = window.__abCorpo; window.__abCorpo = null;
  if (!corpo) return {fase: 'antes', erro: 'sem_corpo'};
  let r;
  try {
    r = await fetch(a.api + '/calculo/calcularV2', {method: 'POST', body: JSON.stringify(corpo),
      headers: {Authorization: a.tApi, 'Content-Type': 'application/json', Accept: 'application/json, text/plain, */*'}});
  } catch (e) { return {fase: 'post', erro: 'rede'}; }
  const t = await r.text(); let d = null; try { d = JSON.parse(t) } catch (e) {}
  let msg = null;
  if (r.status >= 400 && d && typeof d === 'object') {
    const m = d.message || d.mensagem || d.error;
    if (typeof m === 'string') msg = m.slice(0, 160);
  }
  return {fase: 'post', status: r.status, resposta: d && typeof d === 'object' ? M.filtrar(d, a.lista) : null, mensagem: msg};
}"""

JS_LER_CALCULOS = """async (a) => {""" + _JS_COMUM + """
  const [s, d] = await pegar(a.pdocs + '/calculo/cotacao/calculos/' + encodeURIComponent(a.ref) + '/' + a.versao, a.tPdocs);
  if (s !== 200 || !Array.isArray(d)) return {status: s, corpo: null};
  return {status: s, corpo: M.filtrar(d, a.lista)};
}"""

JS_PESSOA_MEXEU = """async (a) => {""" + _JS_COMUM + """
  const [s, vs] = await pegar(a.pdocs + '/calculo/cotacao/versoes/' + encodeURIComponent(a.ref), a.tPdocs);
  if (s !== 200 || !Array.isArray(vs)) return {erro: 'versoes_http_' + s};
  const limite = Date.now() - a.horas * 3600 * 1000;
  const doRobo = new Set(a.versoes_do_robo);
  const marcada = v => String(v.correlationId || '').toLowerCase().startsWith(a.prefixo);
  let usuarios = new Set(vs.filter(v => v && doRobo.has(v.versao)).map(v => v.usuarioId).filter(x => x != null));
  if (!usuarios.size) usuarios = new Set(vs.filter(v => v && marcada(v)).map(v => v.usuarioId).filter(x => x != null));
  let recentes = 0, semMarca = 0, outroUsuario = 0;
  for (const v of vs) {
    if (!v) continue;
    const t = Date.parse(v.createdAt || v.dataCriacao || v.updatedAt || '');
    if (!isNaN(t) && t < limite) continue;      // sem data = conta como recente (na dúvida, a pessoa mexeu)
    recentes++;
    if (!marcada(v)) semMarca++;
    else if (a.conta_ativa && usuarios.size && !usuarios.has(v.usuarioId)) outroUsuario++;
  }
  return {recentes, semMarca, outroUsuario};
}"""

JS_PDFS = """async (a) => {""" + _JS_COMUM + """
  const [s, d] = await pegar(a.pdocs + '/calculo/cotacao/calculos/' + encodeURIComponent(a.ref) + '/' + a.versao, a.tPdocs);
  if (s !== 200 || !Array.isArray(d)) return {erro: 'calculos_http_' + s, pdfs: []};
  const out = []; let falhas = 0;
  for (const it of d) {
    for (const r of (it && it.resultados) || []) {
      if (!r || !(Number(r.premio) > 0) || !r.pathPdf) continue;
      try {
        const resp = await fetch(r.pathPdf);
        if (!resp.ok) { falhas++; continue; }
        const buf = new Uint8Array(await resp.arrayBuffer());
        if (buf.length > a.max || !(buf[0] === 0x25 && buf[1] === 0x50 && buf[2] === 0x44 && buf[3] === 0x46)) { falhas++; continue; }
        let bin = ''; for (let i = 0; i < buf.length; i += 0x8000) bin += String.fromCharCode.apply(null, buf.subarray(i, i + 0x8000));
        out.push([it.seguradora, r.identificacao || '', r.packageType == null ? null : r.packageType, btoa(bin)]);
      } catch (e) { falhas++; }
    }
  }
  return {pdfs: out, falhas};
}"""


# ======================================================================================================================
# A 2ª rede em Python
# ======================================================================================================================
def _limpo_da_lista(valor: Any, endpoint: str) -> bool:
    """Todo caminho do retorno está na lista branca do endpoint, e toda MARCA de PDF/nº de cálculo é a marca."""
    lista = frozenset(LISTA_BRANCA_POR_ENDPOINT[endpoint])
    if not all(caminho_permitido(c, lista) for c in caminhos_de(valor)):
        return False

    def anda(x: Any) -> bool:
        if isinstance(x, dict):
            for k, v in x.items():
                if str(k).lower() in CHAVES_PROIBIDAS_NA_OFERTA and k not in MARCAS_PERMITIDAS:
                    return False
                if k in MARCAS_PERMITIDAS and v not in (None, "", False, MARCAS_PERMITIDAS[k]):
                    return False
                if k == "nroCalculo" and tem_url_ou_chave(v):
                    return False
                if not anda(v):
                    return False
        elif isinstance(x, list):
            return all(anda(i) for i in x)
        return True
    return anda(valor)


def _textos_da_resposta(resp: Any) -> Iterable[str]:
    yield resp.seguradora
    yield from resp.mensagens
    for o in resp.ofertas:
        yield o.seguradora
        yield o.pacote
        yield o.franquia_tipo or ""
        yield from o.alertas
        for _, v in o.coberturas:
            if isinstance(v, str):
                yield v


def _oferta_sem_proibida(o: Any) -> bool:
    nomes = {f.name.lower() for f in dataclasses.fields(o)}
    return not (nomes & set(CHAVES_PROIBIDAS_NA_OFERTA)) and not any(
        str(k).lower() in CHAVES_PROIBIDAS_NA_OFERTA for k, _ in o.coberturas)


def separar_itens(corpo: Any, ramo: int = RAMO_AUTO) -> Tuple[List[dict], List[Tuple[Any, Optional[int]]]]:
    """(itens limpos, [(seguradora, código) descartados]). Pura — o G5 a usa com a mutação."""
    limpos: List[dict] = []
    sujos: List[Tuple[Any, Optional[int]]] = []
    for item in corpo if isinstance(corpo, list) else []:
        if not isinstance(item, dict):
            continue
        cod = item.get("seguradora") if isinstance(item.get("seguradora"), int) else None
        ok = _limpo_da_lista([item], "cotacao_calculos")
        if ok:
            r = ler_resposta(item, ramo)
            ok = all(not tem_url_ou_chave(t) for t in _textos_da_resposta(r)) and all(
                _oferta_sem_proibida(o) for o in r.ofertas)
        if ok:
            limpos.append(item)
        else:
            sujos.append((sem_url_nem_chave(item.get("seguradoraTxt") or item.get("nomeSeguradora") or ""), cod))
    return limpos, sujos


# ======================================================================================================================
# A interface §6.4
# ======================================================================================================================
def _args_base(sessao: Any) -> Dict[str, Any]:
    return {"api": sessao.bases["api"], "pdocs": sessao.bases["pdocs"], "tApi": sessao.token("api"),
            "tPdocs": sessao.token("pdocs")}


async def _preparar_e_enviar(sessao: Any, args: Dict[str, Any]) -> Disparo:
    await sessao.garantir_token()
    try:
        prep = await sessao.avaliar(JS_PREPARAR, {**_args_base(sessao), **args})
    except Exception as e:  # noqa: BLE001 — nada saiu
        raise DisparoRecusado(f"preparo falhou ({type(e).__name__})") from None
    if not isinstance(prep, dict) or not prep.get("ok"):
        raise DisparoRecusado(f"preparo: {(prep or {}).get('erro', 'sem_resposta') if isinstance(prep, dict) else 'sem_resposta'}")
    antes = sessao.contagem_de_escritas()["calcularV2"]
    t0 = time.time()
    try:
        r = await asyncio.wait_for(sessao.avaliar(JS_ENVIAR, {**_args_base(sessao), "lista": LISTA_RESPOSTA}),
                                   timeout=POST_TIMEOUT_S)
    except Exception as e:  # noqa: BLE001
        if sessao.contagem_de_escritas()["calcularV2"] == antes and not isinstance(e, asyncio.TimeoutError):
            raise DisparoRecusado(f"o POST não saiu ({type(e).__name__})") from None
        raise DisparoIncerto(f"o POST pode ter saído ({type(e).__name__})") from None
    saiu = sessao.contagem_de_escritas()["calcularV2"] > antes
    if not isinstance(r, dict) or r.get("fase") != "post":
        raise DisparoRecusado("o corpo preparado sumiu")
    if r.get("erro") == "rede":
        if not saiu:
            raise DisparoRecusado("o POST foi barrado antes de sair (guarda)")
        raise DisparoIncerto("rede caiu durante o POST")
    status = int(r.get("status") or 0)
    resp = r.get("resposta")
    if 200 <= status < 300:
        if not (isinstance(resp, dict) and _limpo_da_lista(resp, "calcularV2_resposta")
                and resp.get("idIntegracao") and isinstance(resp.get("versao"), int)):
            raise DisparoIncerto(f"HTTP {status} sem idIntegracao/versão legíveis")
        ref = str(resp["idIntegracao"])
        sessao.registrar_negocio(ref)
        return Disparo(negocio_ref=ref, versao=int(resp["versao"]), t0=t0)
    if 400 <= status < 500:
        msg = sem_url_nem_chave(r.get("mensagem") or "")
        raise DisparoRecusado(f"HTTP {status}" + (f": {msg}" if msg else ""))
    raise DisparoIncerto(f"HTTP {status}")


async def disparar(sessao: Any, pedido: Dict[str, Any], coberturas: Dict[str, Any], *,
                   negocio_ref: Optional[str] = None) -> Disparo:
    """Negócio NOVO (negocio_ref=None) ou nova VERSÃO do negócio do robô (a econômica, D-129B-03)."""
    base = cotacao_do_pedido(pedido)
    cob = {k: v for k, v in (coberturas or {}).items() if k in CHAVES_DE_COBERTURA}
    # ⛔ NÃO registra `negocio_ref` aqui: a guarda só deixa a versão passar se o negócio JÁ é do robô (registrado
    # pelo disparo da padrão, ou por `Sessoes.obter(negocios_do_robo=...)` na retomada).
    return await _preparar_e_enviar(sessao, {
        "cot": base["cotacao"], "cob": cob, "comissao": base["comissao"], "desconto": base["desconto"],
        "seguradoras": base["seguradoras"], "seguradora_anterior": base["seguradora_anterior"],
        "negocio_ref": negocio_ref, "versao_base": None, "da_versao": False, "ajuste": None})


async def recalcular(sessao: Any, negocio_ref: str, *, versao_base: int, ajuste: Ajuste) -> Disparo:
    """Nova versão do MESMO negócio partindo da `versao_base` (as coberturas e a comissão DELA), mais o ajuste."""
    aj = {"tipo": ajuste.tipo, "valor": ajuste.valor, "seguradora": ajuste.seguradora}
    return await _preparar_e_enviar(sessao, {
        "cot": {"results": {k: {"errors": [], "successes": []} for k in ("main", "alternatives", "all", "porAssinatura", "ofertaCruzada")},
                "loaded": False, "isClearDraft": False, "correlationId": correlation_id()},
        "negocio_ref": negocio_ref, "versao_base": int(versao_base), "da_versao": True, "ajuste": aj})


async def acompanhar(sessao: Any, disparo: Disparo, *, ao_evento: Callable[[Evento], Awaitable[Any]],
                     anterior: Optional[RodadaDoCalculo] = None, quadro_s: float = 60, teto_s: float = 480,
                     intervalo_s: float = 3, ao_quadro: Optional[Callable[[], Awaitable[Any]]] = None) -> RodadaDoCalculo:
    """Lê `calculos/{negocio}/{versao}` aos poucos (📊 184 KB constante × 373 KB das versões). Cada rodada → o
    leitor PURO → `eventos_entre(anterior, nova)` → `ao_evento`. Fecha quando tudo respondeu ou no teto."""
    atual = anterior
    quadro = False
    descartadas: Set[Any] = set()
    while True:
        await sessao.garantir_token()
        t = time.time() - disparo.t0
        try:
            r = await sessao.avaliar(JS_LER_CALCULOS, {**_args_base(sessao), "ref": disparo.negocio_ref,
                                                       "versao": int(disparo.versao), "lista": LISTA_CALCULOS})
        except Exception as e:  # noqa: BLE001
            logger.warning("multicalculo.robo leitura falhou (%s)", type(e).__name__)
            r = None
        nova = None
        if isinstance(r, dict) and r.get("status") == 200 and isinstance(r.get("corpo"), list):
            limpos, sujos = separar_itens(r["corpo"])
            for nome, cod in sujos:
                chave = cod if cod is not None else nome
                if chave not in descartadas:
                    descartadas.add(chave)
                    await ao_evento(Evento(ERRO_DE_LEITURA, t, nome or None, cod))
            nova = ler_rodada(limpos, t_s=t)
            if limpos or not r["corpo"]:
                for e in eventos_entre(atual, nova):
                    await ao_evento(e)
                atual = nova
        fechado = bool(atual is not None and atual.fechado)
        if ao_quadro is not None and not quadro and (t >= quadro_s or fechado):
            quadro = True
            await ao_quadro()
        if fechado or t >= teto_s:
            return atual if atual is not None else RodadaDoCalculo(t_s=t, respostas=(), fechado=False)
        await asyncio.sleep(intervalo_s)


async def pessoa_mexeu_recentemente(sessao: Any, negocio_ref: str, *, horas: int = 24,
                                    versoes_do_robo: Set[int]) -> bool:
    """D-MC-47 (§4.1): existe versão nas últimas `horas` cujo correlationId NÃO tem a marca do robô, OU (conta
    `ativo`) cujo usuarioId ≠ o do robô. Falha de leitura → True (na dúvida, não se recalcula por cima da pessoa)."""
    try:
        r = await sessao.avaliar(JS_PESSOA_MEXEU, {
            **_args_base(sessao), "ref": negocio_ref, "horas": horas, "prefixo": PREFIXO_DA_MARCA,
            "versoes_do_robo": sorted(int(v) for v in versoes_do_robo or ()),
            "conta_ativa": getattr(sessao, "robo_estado", None) == "ativo"})
    except Exception as e:  # noqa: BLE001
        logger.warning("multicalculo.robo pessoa_mexeu: leitura falhou (%s) → assume que sim", type(e).__name__)
        return True
    if not isinstance(r, dict) or "erro" in r:
        return True
    return bool(int(r.get("semMarca") or 0) or int(r.get("outroUsuario") or 0))


async def copiar_pdfs(sessao: Any, disparo: Disparo) -> Dict[tuple, bytes]:
    """O PDF de cada oferta, baixado DENTRO da página: a URL nunca sai; só os bytes (e só se for PDF)."""
    r = await sessao.avaliar(JS_PDFS, {**_args_base(sessao), "ref": disparo.negocio_ref,
                                       "versao": int(disparo.versao), "max": PDF_MAX_BYTES})
    saida: Dict[tuple, bytes] = {}
    for cod, pacote, tipo, b64 in (r or {}).get("pdfs") or []:
        chave = (int(cod) if isinstance(cod, int) else cod, sem_url_nem_chave(pacote), tipo)
        if chave in saida:
            continue
        dados = base64.b64decode(b64)
        if dados[:4] == b"%PDF" and len(dados) <= PDF_MAX_BYTES:
            saida[chave] = dados
    if (r or {}).get("falhas"):
        logger.info("multicalculo.robo pdfs: %s não copiados", int(r["falhas"]))
    return saida
