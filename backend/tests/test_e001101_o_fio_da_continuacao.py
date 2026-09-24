# -*- coding: utf-8 -*-
"""🔴 O TESTE DO FIO da EXTRA-001.10.1 — a continuação do portal de vidros.

Protocolo AAA v13 §5 ②: a primeira entrega, nasce vermelho e fica verde.

O que ele atravessa, com o MOTOR REAL
=====================================
`abrir_atendimento_api` → sessão durável cifrada (`vault`, Fernet) →
`evidence["continuacao"]` → `continuar_atendimento` (journey nova) →
`SessaoVidros(modo_continuacao=True)` → `GET /atendimentos` → agenda /
ramo 7 → `POST /agendamentos` · `POST /atendimentos-prioridades` ·
`POST /ocorrencias` → confirmação LIDA do portal → desfecho.

O único dublê é a BORDA: a `page` de `_replay_vidros` (HAR real, lido por
`trafego.importar_har`) e o RELÓGIO — `AF.hoje` fixado no dia da captura
(21/09/2026), porque "a primeira data ≥ hoje" tem de ler a agenda que o humano
leu. A chave do cofre é gerada AQUI (`Fernet.generate_key()`), nunca lida do env.

Gates: G1 (agendar na mesma sessão) · G2 (agendar em DOIS jobs) · G3 (a
continuação nunca cria pedido) · G4 (sessão indecifrável / 401) · G5 (lataria:
prioridade + ocorrência) · G6 (o token nunca aparece em claro).

⛔ PII: nada pessoal em código, asserção ou saída. O token do replay é lido do
HAR em memória e só é COMPARADO — nunca impresso. Sem os HAR: SKIP.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from cryptography.fernet import Fernet  # noqa: E402

os.environ["PORTAL_VAULT_KEY"] = Fernet.generate_key().decode()

import _replay_vidros as RV                                  # noqa: E402
from portal_worker import guardrails as G                    # noqa: E402
from portal_worker import redaction as RED                   # noqa: E402
from portal_worker import vault                              # noqa: E402
from portal_worker.journeys import vidros_api as API         # noqa: E402
from portal_worker.journeys import vidros_apifirst as AF     # noqa: E402
from portal_worker.journeys import vidros_continuacao as VC  # noqa: E402
from portal_worker.journeys import vidros_estado as ST       # noqa: E402
from portal_worker.journeys.vidros_sessao import SessaoVidros  # noqa: E402

PASS = FAIL = 0


def _sem_numeros(x):
    """⛔ Nenhum número de 4+ dígitos na saída (protocolo, código, CPF, token…)."""
    return re.sub(r"[0-9a-fA-F-]{16,}|\d{4,}", "{n}", str(x))


def check(nome, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [ok] " + nome)
    else:
        FAIL += 1
        print("  [FALHOU] " + nome + ("  " + _sem_numeros(extra)[:300] if extra else ""))


# 📊 O relógio da captura: os HAR LATERAL/LATARIA são de 21/09/2026.
AF.hoje = lambda: date(2026, 9, 21)


class RuntimeDeReplay:
    """O que o worker injeta em `params["_runtime"]`: guard + checkpoint."""

    def __init__(self, *, liberado=True):
        self.gravacoes: list = []
        self.guard = G.PortalActionGuard(material_liberado=liberado,
                                         _checkpoint=self.checkpoint)

    async def checkpoint(self, patch):
        self.gravacoes.append(json.loads(json.dumps(patch, default=str)))


# 📊 As escritas que MUDAM o pedido. `consultar-distancias`, `perguntas` e
# `regras-reparo` são POST de LEITURA (SPEC-073: semântica vence verbo).
POST_DE_LEITURA = {"/lojas/consultar-distancias", "/questionarios/perguntas",
                   "/questionarios/regras-reparo"}


def _abre(cifra):
    """A cifra abre o token? Falha de decifração vira `""` (e a asserção fica
    VERMELHA), em vez de derrubar o arquivo inteiro com `InvalidToken`."""
    try:
        return vault.decrypt(cifra or "")
    except Exception:  # noqa: BLE001
        return ""


def escritas_de_negocio(page):
    return [(m, c.split("?")[0]) for m, c in page.escritas()
            if c.split("?")[0] not in POST_DE_LEITURA]


# 📊 No LATERAL o humano marcou `PerimetroDano: "N"` (Não Sabe). Por decisão da
# 001.10 o motor NUNCA manda `N` — a conversa pergunta "cidade ou estrada?"
# antes da fronteira A. O teste dá a resposta que a conversa teria colhido.
RESPOSTA_DA_CONVERSA = {"LATERAL": {"dano": {"onde": "urbano"}}}


def abrir(nome, *, extra=None, page=None):
    chamadas = RV.carregar(nome)
    page = page or RV.PaginaDeReplay(chamadas)
    extra = {**RESPOSTA_DA_CONVERSA.get(nome, {}), **(extra or {})}
    params = RV.params_do_har(chamadas, extra=extra)
    rt = RuntimeDeReplay()
    params["_runtime"] = rt
    ev: dict = {}
    r = asyncio.run(AF.abrir_atendimento_api(page, params, ev))
    return r, ev, page, chamadas, params, rt


def continuar(params_origem, ev_origem, *, page, operacao, escolha=None,
              respostas=None, sessao=None):
    params = {k: v for k, v in params_origem.items() if k != "_runtime"}
    params["_continuacao"] = {
        "job_origem": "job-de-origem-do-teste", "operacao": operacao,
        "escolha": escolha or {}, "respostas": respostas or {},
        "sessao": dict(ev_origem.get("continuacao") or {}) if sessao is None else sessao,
        "desfecho_anterior": ev_origem.get("desfecho"),
    }
    rt = RuntimeDeReplay()
    params["_runtime"] = rt
    ev: dict = {}
    r = asyncio.run(VC.continuar_atendimento(page, params, ev))
    return r, ev, rt


def cursor_antes_do_roteador(chamadas):
    """A continuação retoma um pedido JÁ materializado: a página "já viveu" o
    HAR até o último `GET /atendimentos` antes de `opcoes-disponiveis`."""
    i_opc = RV.indice(chamadas, "GET", "/agendamentos/opcoes-disponiveis")
    return max(i for i in range(i_opc)
               if RV._chave(chamadas[i].metodo, RV.caminho_de(chamadas[i]))
               == ("GET", "/atendimentos"))


# ==========================================================================
try:
    HAR_LAT = RV.carregar("LATERAL")
    HAR_LAT2 = RV.carregar("LATARIA2")
except RV.HarAusente as e:
    print("\n[SKIP] " + str(e))
    sys.exit(0)

TOKEN = str((RV.primeira(HAR_LAT, "POST", "/atendimentos") or {}).get("Token") or "")
AGENDA_HAR = RV.primeira(HAR_LAT, "POST", "/agendamentos", requisicao=True) or {}
HORARIOS_HAR = RV.todas(HAR_LAT, "GET", "/agendamentos/horarios-disponiveis")
RESULTADOS = []   # (evidence, captured, message, gravacoes) de TODAS as execuções

# ==========================================================================
print("\n[G1] LATERAL com preferência (a partir de 21/09, tarde) — agenda na MESMA sessão")
# ==========================================================================
PREF = {"especificos": {"preferencia_agenda": {"a_partir_de": "21/09/2026",
                                               "periodo": "tarde"}}}
r1, ev1, p1, _, prm1, rt1 = abrir("LATERAL", extra=PREF)
RESULTADOS.append((ev1, r1.captured, r1.message, rt1.gravacoes))
check("G1: o acervo tem o POST /agendamentos medido (7 chaves)", len(AGENDA_HAR) == 7,
      list(AGENDA_HAR))
check("G1: POST /agendamentos saiu UMA vez", p1.quantas("POST", "/agendamentos") == 1,
      p1.escritas())
corpo1 = p1.corpo_de("POST", "/agendamentos") or {}
check("G1: as 7 chaves, na MESMA ordem que o portal recebeu",
      list(corpo1) == list(AGENDA_HAR), (list(corpo1), list(AGENDA_HAR)))
for k in ("CodigoCliente", "CodigoProduto", "DataDeAgendamento",
          "QuantidadeTempoServico", "QuantidadeTempoPermanencia", "Encaixe"):
    check(f"G1: {k} igual ao do HAR", corpo1.get(k) == AGENDA_HAR.get(k),
          (k, type(corpo1.get(k)).__name__))
# O horário que a REGRA escolhe, recalculado por um caminho INDEPENDENTE do
# motor: o 1º bloco da TARDE com vaga (normal OU encaixe) no 1º dia ≥ 21/09.
_esperado_hora = ""
for _h in HORARIOS_HAR:
    for _b in (_h or {}).get("Blocos") or []:
        if (_b["QuantidadeDisponivel"] > 0 or _b["QuantidadeEncaixeParametrizadoDisponivel"] > 0) \
                and _b["Turno"]["Value"] == "Tarde":
            _esperado_hora = _b["Horario"]
            break
    if _esperado_hora:
        break
check("G1: o horario e o 1o da TARDE com vaga (recalculado do HAR)",
      bool(_esperado_hora) and corpo1.get("Horario") == _esperado_hora,
      (corpo1.get("Horario"), _esperado_hora))
# 🔴 CONTROLE que prova que a confirmação é LIDA: o script do HAR diz 16:00 (o
# que o humano escolheu); o motor pediu outro horário — então NÃO pode dizer
# "agendado". E não repete o POST.
check("G1 CONTROLE: o script do HAR confirma OUTRO horario -> NAO declara agendado",
      r1.captured.get("stage") == "agendamento_nao_confirmado", r1.captured.get("stage"))
check("G1 CONTROLE: e a continuacao e RELER, nunca repetir o POST",
      (ev1.get("continuacao") or {}).get("acao_esperada") == "reler"
      and p1.quantas("POST", "/agendamentos") == 1,
      {k: (ev1.get("continuacao") or {}).get(k) for k in ("etapa", "acao_esperada", "possivel")})
check("G1 CONTROLE: o efeito ficou INCERTO (reconciliar antes de repetir)",
      G.fase_do_efeito(rt1.guard.evidence) == G.FASE_UNKNOWN,
      G.fase_do_efeito(rt1.guard.evidence))


class PaginaQueEscreveOAgendado(RV.PaginaDeReplay):
    """📊 Medido: `POST /agendamentos` [048] com 16:00 → o `GET /atendimentos`
    [049] diz "Agendado para 22/09/2026 às 16:00" — o portal escreve no script o
    que RECEBEU. O dublê repete essa regra (e só ela) para o horário que o
    humano não escolheu. Todo o resto é o HAR."""

    agendado = None

    async def evaluate(self, js, arg):
        r = await super().evaluate(js, arg)
        caminho = str(arg.get("url") or "").split("web-app", 1)[-1].split("?")[0]
        if arg.get("metodo") == "POST" and caminho == "/agendamentos":
            self.agendado = arg.get("corpo")
        elif self.agendado and arg.get("metodo") == "GET" and caminho == "/atendimentos":
            corpo = json.loads(r["text"])
            iso = self.agendado["DataDeAgendamento"]
            for info in corpo["ScriptFinalizacao"]["InformacoesAdicionais"]:
                if info["Titulo"] == "Agendado para":
                    info["Valor"] = f"{iso[8:10]}/{iso[5:7]}/{iso[:4]} às {self.agendado['Horario']}"
            r["text"] = json.dumps(corpo, ensure_ascii=False)
        return r


r1b, ev1b, p1b, _, _, rt1b = abrir("LATERAL", extra=PREF,
                                    page=PaginaQueEscreveOAgendado(RV.carregar("LATERAL")))
RESULTADOS.append((ev1b, r1b.captured, r1b.message, rt1b.gravacoes))
d1b = ev1b.get("desfecho") or {}
ag1b = d1b.get("agendamento") or {}
check("G1: com o script refletindo o POST, o desfecho e `agendado`",
      d1b.get("tipo") == ST.DESFECHO_AGENDADO and r1b.status == "done",
      (d1b.get("tipo"), r1b.status, r1b.captured.get("stage")))
check("G1: dia e hora LIDOS do script = os enviados",
      ag1b.get("data") == "22/09/2026" and ag1b.get("horario") == _esperado_hora,
      (ag1b.get("data"), ag1b.get("horario")))
check("G1: confirmado_pelo_portal e True", ag1b.get("confirmado_pelo_portal") is True)
check("G1: loja, endereco, referencia e permanencia vieram do portal",
      all(ag1b.get(k) for k in ("loja", "endereco", "referencia"))
      and ag1b.get("permanencia") == "01:30 Hrs.", sorted(ag1b))
check("G1: o comprovante foi emitido DEPOIS do agendamento",
      d1b.get("comprovante_emitido") is True
      and p1b.ordem_de("POST", "/atendimentos/emitir-atendimento-formalizado/{codigo}")
      > p1b.ordem_de("POST", "/agendamentos"))
check("G1: o segurado NAO precisa mais escolher",
      r1b.captured.get("customer_choice_needed") is False)
check("G1: a continuacao acabou (concluido, sem sessao guardada)",
      (ev1b.get("continuacao") or {}).get("etapa") == ST.ETAPA_CONCLUIDO
      and not (ev1b.get("continuacao") or {}).get("sessao_cifrada"))

# ==========================================================================
print("\n[G2] LATERAL em DOIS jobs — abertura mostra a agenda; a continuação agenda")
# ==========================================================================
r2, ev2, p2, _, prm2, rt2 = abrir("LATERAL")
RESULTADOS.append((ev2, r2.captured, r2.message, rt2.gravacoes))
d2 = ev2.get("desfecho") or {}
c2 = ev2.get("continuacao") or {}
check("G2: a abertura termina em `agenda`", d2.get("tipo") == ST.DESFECHO_AGENDA,
      d2.get("tipo"))
check("G2: e SEM POST /agendamentos", p2.quantas("POST", "/agendamentos") == 0)
check("G2: continuacao possivel, etapa agendar",
      c2.get("possivel") is True and c2.get("etapa") == ST.ETAPA_AGENDAR
      and c2.get("acao_esperada") == "agendar", {k: c2.get(k) for k in
                                                  ("possivel", "etapa", "acao_esperada")})
check("G2: a sessao foi guardada CIFRADA — e a cifra abre o token do portal",
      c2.get("sessao_guardada") is True and bool(TOKEN)
      and _abre(c2.get("sessao_cifrada")) == TOKEN)
check("G2: e o checkpoint gravou a sessao JUNTO do protocolo (antes do contato)",
      any("continuacao" in g and "protocolo" in g for g in rt2.gravacoes))
for campo in ("emitida_em", "seguradora", "protocolo", "codigo_atendimento", "categoria"):
    check(f"G2: continuacao.{campo} preenchido", bool(c2.get(campo)))
# lojas[].horarios — o contrato A→C novo, recalculado do HAR por fora
_livres_22 = [b["Horario"] for b in (HORARIOS_HAR[1] or {}).get("Blocos") or []
              if b["QuantidadeDisponivel"] > 0 or b["QuantidadeEncaixeParametrizadoDisponivel"] > 0]
loja2 = (d2.get("lojas") or [{}])[0]
check("G2: lojas[].horarios = {'DD/MM': ['HH:MM', ...]} so com blocos LIVRES",
      loja2.get("horarios") == {"22/09": _livres_22} and len(_livres_22) == 8,
      loja2.get("horarios"))
check("G2: nenhum dict cru dentro de horarios (a mensagem imprime direto)",
      all(isinstance(h, str) for v in (loja2.get("horarios") or {}).values() for h in v))
# o contato: termo e WhatsApp pela regra do bundle
_sol_har = RV.primeira(HAR_LAT, "POST", "/solicitantes", requisicao=True) or {}
_sol = p2.corpo_de("POST", "/solicitantes") or {}
check("G2: TermoExibido = o do portal (false: Corretor sem e-mail de corretor)",
      _sol.get("TermoExibido") is False and _sol_har.get("TermoExibido") is False)
check("G2: o telefone vai com StatusEnvioWhatsapp=true (medido 1x no LATERAL)",
      [sorted(t) for t in _sol.get("Telefones") or []]
      == [sorted(t) for t in _sol_har.get("Telefones") or []]
      and (_sol.get("Telefones") or [{}])[0].get("StatusEnvioWhatsapp") is True)

# ---- o 2º job: a continuação com a escolha que o humano fez ------------
ESCOLHA = {"loja": str(AGENDA_HAR.get("CodigoCliente")), "dia": "22/09", "horario": "16:00"}
cur = cursor_antes_do_roteador(HAR_LAT)
pc = RV.PaginaDeReplay(RV.carregar("LATERAL"), cursor=cur)
rc, evc, rtc = continuar(prm2, ev2, page=pc, operacao="agendar", escolha=ESCOLHA)
RESULTADOS.append((evc, rc.captured, rc.message, rtc.gravacoes))
dc = evc.get("desfecho") or {}
check("G2: a continuacao agenda (`agendado`, done)",
      rc.status == "done" and dc.get("tipo") == ST.DESFECHO_AGENDADO,
      (rc.status, rc.captured.get("stage"), dc.get("tipo")))
check("G2: o POST /agendamentos e IGUAL, chave a chave e na ordem, ao do HAR",
      list((pc.corpo_de("POST", "/agendamentos") or {}).items()) == list(AGENDA_HAR.items()))
check("G2: e saiu UMA vez", pc.quantas("POST", "/agendamentos") == 1)
check("G2: o 'Agendado para' LIDO e o do HAR (22/09/2026 16:00), sem dubla-lo",
      (dc.get("agendamento") or {}).get("data") == "22/09/2026"
      and (dc.get("agendamento") or {}).get("horario") == "16:00")
_hdr = [r["cabecalhos"].get(API.HEADER_TOKEN) for r in pc.registro
        if r["metodo"] == "POST" and r["caminho"].split("?")[0] == "/agendamentos"]
check("G2: o token que viajou no POST e o DECIFRADO da sessao guardada",
      _hdr == [TOKEN])
check("G2: a continuacao LEU o atendimento antes de qualquer escrita",
      pc.registro and (pc.registro[0]["metodo"], pc.registro[0]["caminho"].split("?")[0])
      == ("GET", "/atendimentos"))

# ---- escolha que o portal NÃO publica: 16:15 (bloco sem vaga) ----------
pc2 = RV.PaginaDeReplay(RV.carregar("LATERAL"), cursor=cur)
rc2, evc2, rtc2 = continuar(prm2, ev2, page=pc2, operacao="agendar",
                            escolha={**ESCOLHA, "horario": "16:15"})
RESULTADOS.append((evc2, rc2.captured, rc2.message, rtc2.gravacoes))
check("G2: 16:15 (sem vaga) -> `horario_indisponivel`",
      rc2.captured.get("stage") == "horario_indisponivel", rc2.captured.get("stage"))
check("G2: e NENHUMA escrita de negocio saiu", escritas_de_negocio(pc2) == [],
      escritas_de_negocio(pc2))
check("G2: com as opcoes REAIS de agora no mesmo contrato (lojas[].horarios)",
      ((evc2.get("desfecho") or {}).get("lojas") or [{}])[0].get("horarios")
      == {"22/09": _livres_22})
check("G2: e a continuacao segue possivel (o segurado escolhe de novo)",
      (evc2.get("continuacao") or {}).get("acao_esperada") == "agendar"
      and (evc2.get("continuacao") or {}).get("possivel") is True)
pc3 = RV.PaginaDeReplay(RV.carregar("LATERAL"), cursor=cur)
rc3, evc3, _ = continuar(prm2, ev2, page=pc3, operacao="agendar",
                         escolha={**ESCOLHA, "loja": "1"})
check("G2: loja fora das publicadas -> `horario_indisponivel`, nada sai",
      rc3.captured.get("stage") == "horario_indisponivel" and escritas_de_negocio(pc3) == [])

# ==========================================================================
print("\n[G3] a continuação NUNCA emite POST /atendimentos")
# ==========================================================================
check("G3: nenhuma continuacao deste arquivo emitiu POST /atendimentos",
      all(p.quantas("POST", "/atendimentos") == 0 for p in (pc, pc2, pc3)))


class PaginaQueConta:
    def __init__(self):
        self.chamou = 0

    async def evaluate(self, *a, **k):
        self.chamou += 1
        return {"ok": True, "status": 200, "text": "{\"NumeroProtocolo\": \"1\"}"}


_pg = PaginaQueConta()
_r = asyncio.run(SessaoVidros(page=_pg, token="t", modo_continuacao=True)
                 .criar_atendimento({"Seguradora": "X"}))
check("G3: em modo continuacao, criar_atendimento NAO toca a rede",
      _pg.chamou == 0 and _r.get("erro") == "continuacao_nao_cria_atendimento", _r)
_pg2 = PaginaQueConta()
asyncio.run(SessaoVidros(page=_pg2).criar_atendimento({"Seguradora": "X"}))
check("G3 CONTROLE: fora do modo continuacao a MESMA chamada sai — os dois DIFEREM",
      _pg2.chamou == 1)

# ==========================================================================
print("\n[G4] sessão indecifrável e sessão expirada (401)")
# ==========================================================================
pg4 = RV.PaginaDeReplay(RV.carregar("LATERAL"), cursor=cur)
r4, ev4, _ = continuar(prm2, ev2, page=pg4, operacao="agendar", escolha=ESCOLHA,
                       sessao={**ev2["continuacao"], "sessao_cifrada": "gAAAAA-nao-e-cifra"})
RESULTADOS.append((ev4, r4.captured, r4.message, []))
check("G4: cifra que o cofre nao abre -> `sessao_indisponivel`",
      r4.captured.get("stage") == "sessao_indisponivel", r4.captured.get("stage"))
check("G4: e a pagina NEM foi tocada", pg4.registro == [])
check("G4: continuacao impossivel e legivel",
      (ev4.get("continuacao") or {}).get("possivel") is False
      and bool((ev4.get("continuacao") or {}).get("motivo")))
r4b, ev4b, _ = continuar(prm2, ev2, page=pg4, operacao="agendar", escolha=ESCOLHA,
                         sessao={**ev2["continuacao"], "sessao_cifrada": "",
                                 "sessao_guardada": False})
check("G4: sem sessao guardada -> `sessao_indisponivel`",
      r4b.captured.get("stage") == "sessao_indisponivel" and pg4.registro == [])


class Pagina401(RV.PaginaDeReplay):
    async def evaluate(self, js, arg):
        await super().evaluate(js, arg)
        return {"ok": False, "status": 401, "text": "{\"Message\":\"nao autorizado\"}"}


pg401 = Pagina401(RV.carregar("LATERAL"), cursor=cur)
r4c, ev4c, _ = continuar(prm2, ev2, page=pg401, operacao="agendar", escolha=ESCOLHA)
RESULTADOS.append((ev4c, r4c.captured, r4c.message, []))
check("G4: GET /atendimentos 401 -> `sessao_expirada`",
      r4c.captured.get("stage") == "sessao_expirada", r4c.captured.get("stage"))
check("G4: e ZERO escritas", pg401.escritas() == [], pg401.escritas())
check("G4: e SO uma leitura (nao insiste, nao renova)",
      [(m, c.split("?")[0]) for m, c in pg401.emitidas()] == [("GET", "/atendimentos")])
check("G4: a sessao morta nao fica guardada",
      (ev4c.get("continuacao") or {}).get("possivel") is False
      and not (ev4c.get("continuacao") or {}).get("sessao_cifrada"))

# o cofre ausente NUNCA derruba o acionamento
_chave = os.environ.pop("PORTAL_VAULT_KEY")
try:
    r4d, ev4d, p4d, _, _, _ = abrir("LATERAL")
finally:
    os.environ["PORTAL_VAULT_KEY"] = _chave
RESULTADOS.append((ev4d, r4d.captured, r4d.message, []))
check("G4: sem PORTAL_VAULT_KEY o pedido segue ate o desfecho (agenda)",
      r4d.status == "done" and (ev4d.get("desfecho") or {}).get("tipo") == ST.DESFECHO_AGENDA,
      (r4d.status, r4d.captured.get("stage")))
check("G4: e a continuacao diz, legivel, que a sessao NAO foi guardada",
      (ev4d.get("continuacao") or {}).get("sessao_guardada") is False
      and (ev4d.get("continuacao") or {}).get("possivel") is False
      and "PORTAL_VAULT_KEY" in (ev4d.get("continuacao") or {}).get("motivo", ""))

# ==========================================================================
print("\n[G5] LATARIA [61–113] — ilha normal + opção de vistoria (ramo 7)")
# ==========================================================================
PRIO_HAR = RV.primeira(HAR_LAT2, "POST", "/atendimentos-prioridades", requisicao=True) or {}
OCOR_HAR = RV.primeira(HAR_LAT2, "POST", "/ocorrencias", requisicao=True) or {}
r5, ev5, p5, _, prm5, rt5 = abrir("LATARIA2",
                                  extra={"especificos": {"preferencia_vistoria": "loja"}})
RESULTADOS.append((ev5, r5.captured, r5.message, rt5.gravacoes))
check("G5: a faixa e a 2a execucao (lataria, categoria L)",
      (ev5.get("peca") or {}).get("categoria") == "L", ev5.get("peca"))
check("G5: o roteador tinha BloqueadoIlhaNormal=true e o motor SEGUIU (como o portal)",
      ((ev5.get("desfecho") or {}).get("roteador") or {}).get("BloqueadoIlhaNormal") is True)
check("G5: prioridade: o corpo e IGUAL ao do HAR [092]",
      p5.corpo_de("POST", "/atendimentos-prioridades") == PRIO_HAR and bool(PRIO_HAR))
check("G5: ocorrencia: o corpo e IGUAL ao do HAR [093] (texto LITERAL do bundle)",
      p5.corpo_de("POST", "/ocorrencias") == OCOR_HAR and bool(OCOR_HAR))
check("G5: e o texto e o do bundle para 'L'",
      (p5.corpo_de("POST", "/ocorrencias") or {}).get("Ocorrencia")
      == "SEGURADO TEM PREFERÊNCIA POR REALIZAR VISTORIA EM LOJA")
_ordem = [p5.ordem_de("GET", "/atendimentos-prioridades/{codigo}"),
          p5.ordem_de("POST", "/atendimentos-prioridades"),
          p5.ordem_de("POST", "/ocorrencias"),
          p5.ordem_de("POST", "/atendimentos/emitir-atendimento-formalizado/{codigo}")]
check("G5: na ordem do SPA: GET prioridade < POST prioridade < ocorrencia < comprovante",
      -1 < _ordem[0] < _ordem[1] < _ordem[2] < _ordem[3], _ordem)
d5 = ev5.get("desfecho") or {}
check("G5: desfecho `analista` (o portal concluiu)",
      d5.get("tipo") == ST.DESFECHO_ANALISTA and r5.status == "done",
      (d5.get("tipo"), r5.status, r5.captured.get("stage")))
check("G5: e o titulo e o do portal ('com o analista')",
      "analista" in (d5.get("titulo_portal") or "").lower())
check("G5: nenhuma chamada ficou sem resposta no acervo", not p5.sem_resposta,
      p5.sem_resposta)

r5b, ev5b, p5b, _, prm5b, rt5b = abrir("LATARIA2")
RESULTADOS.append((ev5b, r5b.captured, r5b.message, rt5b.gravacoes))
check("G5: sem preferencia -> `decidir_vistoria`",
      r5b.captured.get("stage") == "decidir_vistoria", r5b.captured.get("stage"))
check("G5: e NENHUMA das duas escritas saiu",
      p5b.quantas("POST", "/atendimentos-prioridades") == 0
      and p5b.quantas("POST", "/ocorrencias") == 0, p5b.escritas())
check("G5: a continuacao fica pronta para a pergunta (etapa vistoria)",
      (ev5b.get("continuacao") or {}).get("etapa") == ST.ETAPA_VISTORIA
      and (ev5b.get("continuacao") or {}).get("possivel") is True)
check("G5: o desfecho gravado e `vistoria_opcional`",
      (ev5b.get("desfecho") or {}).get("tipo") == ST.DESFECHO_VISTORIA_OPCIONAL)

# ---- a resposta chega depois: continuação `vistoria` com LINK ----------
pv = RV.PaginaDeReplay(RV.carregar("LATARIA2"), cursor=cursor_antes_do_roteador(HAR_LAT2))
rv, evv, rtv = continuar(prm5b, ev5b, page=pv, operacao="vistoria",
                         respostas={"preferencia_vistoria": "link"})
RESULTADOS.append((evv, rv.captured, rv.message, rtv.gravacoes))
check("G5: a continuacao grava a ocorrencia ONLINE (LINK), texto do bundle",
      (pv.corpo_de("POST", "/ocorrencias") or {}).get("Ocorrencia")
      == "SEGURADO TEM PREFERÊNCIA POR REALIZAR VISTORIA ONLINE (LINK)")
check("G5: e conclui com o analista, sem POST /atendimentos",
      (evv.get("desfecho") or {}).get("tipo") == ST.DESFECHO_ANALISTA
      and pv.quantas("POST", "/atendimentos") == 0,
      ((evv.get("desfecho") or {}).get("tipo"), rv.captured.get("stage")))

# ==========================================================================
print("\n[G6] o token do portal NUNCA aparece em claro")
# ==========================================================================
check("G6: o acervo tem token (a varredura consegue achar)", len(TOKEN) >= 16)
_vazou = []
for i, (ev, cap, msg, grav) in enumerate(RESULTADOS):
    for nome, alvo in (("evidence", ev), ("captured", cap), ("message", msg),
                       ("checkpoints", grav)):
        if TOKEN in json.dumps(alvo, ensure_ascii=False, default=str):
            _vazou.append((i, nome))
check(f"G6: token ausente de evidence/captured/message/checkpoint ({len(RESULTADOS)} execucoes)",
      not _vazou, _vazou)
check("G6: o repr da sessao nao carrega o token",
      TOKEN not in repr(SessaoVidros(page=None, token=TOKEN)))
_env = RED.redigir_envelope(ev2)
check("G6: o redator do worker deixa a cifra INTACTA (a continuacao sobrevive a ele)",
      _env.get("continuacao", {}).get("sessao_cifrada") == c2.get("sessao_cifrada")
      and _abre(_env["continuacao"]["sessao_cifrada"]) == TOKEN)
check("G6: e a trilha da sessao nao tem token (so metodo, path, status)",
      TOKEN not in json.dumps((ev2.get("api_first") or {}).get("trilha")))

print("\n" + "=" * 66)
print(f"  {PASS} asserções verdes · {FAIL} vermelhas")
print("=" * 66)
sys.exit(1 if FAIL else 0)
