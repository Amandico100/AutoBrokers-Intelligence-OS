# -*- coding: utf-8 -*-
"""SPEC-EXTRA-001.10.1 · o CONSERTO ÚNICO — os guardas dos achados do juiz e do red team.

Cada bloco aqui fica VERMELHO com o defeito que o laudo mediu reintroduzido e
VERDE com o conserto (mutação provada uma vez, restaurada por cópia). Tudo pelo
MOTOR real — tool `_arun` → `portal_jobs` → worker de costura → journey →
mensagem —, com dublê só na borda: a página é o replay dos HAR reais (LATERAL),
o banco é o `BancoDeMentira` do teste de costura (com a armadilha que falha alto
se o cliente Supabase REAL for alcançado). ⛔ Nenhuma rede, nenhum banco real,
nenhuma mensagem; nenhum dado pessoal impresso (`_limpo`).

    JUIZ B1 / RED B2(c)  agregado "Agendado para" ⇒ conclui LENDO, zero POST /agendamentos
    RED B1               hora explícita ("4 da tarde") ⇒ agenda SÓ aquela hora; loja ≠ data
    RED B2(a)            a releitura NUNCA agenda pela preferência
    RED B2(b)            a releitura de um `agendar` herda a ESCOLHA dele (e só ela)
    RED B3               500 na agenda ⇒ parada TÉCNICA, nunca "horário ocupado"
    RED B5               caminho DOM sem "técnico vai até você"
    pendências           P1 · P2 · P3 · J-P2 · J-P3

O harness (banco, worker de costura, tool com InfoCap derivada do HAR) é o do
`test_e001101_a_costura_da_continuacao.py` — carregado, não copiado: duas cópias
do mesmo dublê divergiriam em silêncio.
"""
from __future__ import annotations

import asyncio
import copy
import json
import os
import sys
import types
from datetime import date, datetime, timezone

sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # R-P5: nada de cp1252

_AQUI = os.path.dirname(os.path.abspath(__file__))
_COSTURA = os.path.join(_AQUI, "test_e001101_a_costura_da_continuacao.py")
_src = open(_COSTURA, encoding="utf-8").read()
_corte = _src.index("\ntry:\n    HAR_LAT = RV.carregar(")
H = types.ModuleType("costura_harness")
H.__file__ = _COSTURA
sys.modules["costura_harness"] = H
exec(compile(_src[:_corte], _COSTURA, "exec"), H.__dict__)   # só o harness, sem os checks

RV, PP, PT, AF, ST, API = H.RV, H.PP, H.PT, H.AF, H.ST, H.API
from app.tasks import vigia_do_portal as VG  # noqa: E402

# 🔴 os DOIS relógios no dia da captura (o harness já fixa AF.hoje).
PP._hoje_no_brasil = lambda: date(2026, 9, 21)
HOJE = date(2026, 9, 21)

try:
    HAR = RV.carregar("LATERAL")
except RV.HarAusente as e:
    print("\n[SKIP] " + str(e))
    sys.exit(0)
TOKEN = str((RV.primeira(HAR, "POST", "/atendimentos") or {}).get("Token") or "")
H.PII.add(TOKEN)
FALA = {"pelicula": "nao tem pelicula", "porta_dianteira_ou_traseira": "a de tras",
        "lado_motorista_ou_carona": "do lado do motorista"}
CUR = H.cursor_antes(HAR, "GET", "/agendamentos/opcoes-disponiveis")
# a página "já viveu" até o GET /atendimentos DEPOIS do POST /agendamentos [049]:
# o agregado diz "Agendado para 22/09/2026 às 16:00".
POS_AGENDADO = len(HAR) - 2
check = H.check
BANCOS: list = []


def flat_lateral(extra=None):
    flat, info, _ = H.agente_e_infocap(HAR, peca="vidro de porta",
                                       como="encontrou o veiculo danificado",
                                       onde="foi na cidade",
                                       especificos={**FALA, **(extra or {})})
    return flat, info


def abrir(extra=None):
    flat, info = flat_lateral(extra)
    banco = H.BancoDeMentira()
    BANCOS.append(banco)
    resp = H.chamar(banco, H.EMPRESA_A, H.SESSAO_A, flat, info, RV.PaginaDeReplay(HAR))
    ab = banco.jobs(journey="abrir_atendimento")[0]
    return banco, ab, flat, info, resp


class Hostil(RV.PaginaDeReplay):
    """O replay real + injeção na BORDA: `regras[(METODO, caminho)] = resposta`
    e `alias` que faz a agenda de um dia responder com a de outro."""

    def __init__(self, chamadas, *, cursor=0, regras=None, alias=None):
        super().__init__(chamadas, cursor=cursor)
        self.regras = dict(regras or {})
        self.alias = dict(alias or {})

    async def evaluate(self, js, arg):
        url = str(arg.get("url") or "")
        metodo = str(arg.get("metodo") or "GET").upper()
        caminho = url.split(RV.HOST_API, 1)[-1]
        caminho = caminho[len(RV.BASE):] if caminho.startswith(RV.BASE) else caminho
        base = caminho.split("?")[0]
        r = self.regras.get((metodo, base))
        if r is not None:
            self.registro.append({"metodo": metodo, "caminho": caminho,
                                  "corpo": arg.get("corpo"), "cabecalhos": {}})
            return dict(r)
        for de, para in self.alias.items():
            if f"DataAgendamento={de}" in url:
                arg = {**arg, "url": url.replace(f"DataAgendamento={de}",
                                                 f"DataAgendamento={para}")}
        return await super().evaluate(js, arg)


def r500():
    return {"ok": False, "status": 500, "text": json.dumps({"Message": "erro"})}


def continuacao(banco, origem, operacao, *, escolha=None, extra="guarda"):
    pedido_key = str((origem.get("params") or {}).get("_pedido_key")
                     or origem.get("idempotency_key") or "")
    return PP.montar_job_de_continuacao(
        company_id=H.EMPRESA_A, job_origem=origem, operacao=operacao, pedido_key=pedido_key,
        protocolo=PP.numero_do_pedido(origem.get("evidence")) or pedido_key,
        confirm=True, escolha=escolha, extra=extra)


def rodar(banco, linha, pagina):
    job_id, ja = PT.enfileirar_continuacao(banco, linha)
    assert job_id and ja is None, ("nao enfileirou", job_id, ja)
    job = [j for j in banco.tabelas["portal_jobs"] if j["id"] == job_id][0]
    banco.paginas.clear()
    banco.paginas.append(pagina)
    banco._worker(job)
    return job


def loja_1(ab):
    return str(ab["evidence"]["desfecho"]["lojas"][0]["codigo_cliente"])


# ==========================================================================
print("\n[JUIZ B1 / RED B2c] o agregado já diz 'Agendado para' ⇒ conclui LENDO")
# ==========================================================================
banco, ab, flat, info, _ = abrir()
check("preparo: abertura LATERAL termina em agenda, sem POST /agendamentos",
      (ab["evidence"].get("desfecho") or {}).get("tipo") == "agenda"
      and H.PAGINAS[ab["_pagina"]].quantas("POST", "/agendamentos") == 0)
# (a) a continuação `agendar` com OUTRA hora, sobre o pedido já agendado às 16:00
pag = RV.PaginaDeReplay(HAR, cursor=POS_AGENDADO)
j = rodar(banco, continuacao(banco, ab, "agendar",
                             escolha={"loja": loja_1(ab), "dia": "22/09", "horario": "08:00"}),
          pag)
ev = j.get("evidence") or {}
ag = (ev.get("desfecho") or {}).get("agendamento") or {}
check("JUIZ B1: agendar sobre 'Agendado para' => ZERO POST /agendamentos",
      pag.quantas("POST", "/agendamentos") == 0, pag.escritas())
check("JUIZ B1: desfecho 'agendado' LIDO (22/09/2026 16:00, confirmado pelo que esta escrito)",
      j["status"] == "done" and (ev.get("desfecho") or {}).get("tipo") == "agendado"
      and ag.get("data") == "22/09/2026" and ag.get("horario") == "16:00"
      and ag.get("confirmado_pelo_portal") is True and ag.get("ja_estava_agendado") is True,
      (j["status"], ev.get("stage"), ag))
msg = H.mensagem_ao_segurado(j)
check("JUIZ B1: a mensagem diz 'ja esta agendado' (nao 'Agendei'), e o horario certo",
      "já está agendado" in msg and "Agendei" not in msg and "16:00" in msg, H._limpo(msg)[:300])
check("JUIZ P3: a mensagem NAO promete reagendar pelo robo: 'passo para a nossa equipe'",
      "passo para a nossa equipe" in msg and "mudar o dia ou o horário" not in msg)
check("JUIZ B1: a continuacao fica CONCLUIDA (nada mais a continuar)",
      (ev.get("continuacao") or {}).get("possivel") is False
      and not (ev.get("continuacao") or {}).get("sessao_cifrada"))
# (b) a releitura com a preferência herdada, sobre o pedido já agendado (red A1.5)
banco5, ab5, *_ = abrir({"preferencia_agenda": "22/09 de tarde"})
pag5 = RV.PaginaDeReplay(HAR, cursor=POS_AGENDADO)
j5 = rodar(banco5, continuacao(banco5, ab5, "reler", extra="vigia"), pag5)
check("RED B2c: reler sobre 'Agendado para' => ZERO POST /agendamentos",
      pag5.quantas("POST", "/agendamentos") == 0
      and ((j5.get("evidence") or {}).get("desfecho") or {}).get("tipo") == "agendado",
      (pag5.escritas(), ((j5.get("evidence") or {}).get("desfecho") or {}).get("tipo")))
# (c) puro: o roteador com "Agendado para" e DisponibilizarAgendamento ligada
_opc = RV.primeira(HAR, "GET", "/agendamentos/opcoes-disponiveis")
_ag49 = RV.corpo_json(HAR[POS_AGENDADO])
check("RED B2c: ler_desfecho(opcoes com agenda, agregado 'Agendado para') => agendado",
      ST.ler_desfecho(_opc, _ag49)["tipo"] == ST.DESFECHO_AGENDADO)
# CONTROLE: o mesmo job ANTES do agendamento POSTa (o caminho consegue escrever)
pagc = RV.PaginaDeReplay(HAR, cursor=CUR)
jc = rodar(banco, continuacao(banco, ab, "agendar", extra="controle",
                              escolha={"loja": loja_1(ab), "dia": "22/09", "horario": "16:00"}),
           pagc)
check("CONTROLE: antes do agendamento, a mesma continuacao POSTa 1x e confirma lendo",
      pagc.quantas("POST", "/agendamentos") == 1
      and ((jc.get("evidence") or {}).get("desfecho") or {}).get("tipo") == "agendado",
      pagc.escritas())

# ==========================================================================
print("\n[RED B1] a HORA dita nao vira periodo; frase de loja nao vira data")
# ==========================================================================
_frases = {
    "4 da tarde": {"a_partir_de": "21/09/2026", "periodo": "tarde", "horario": "16:00"},
    "de tarde, umas 4 horas": {"a_partir_de": "21/09/2026", "periodo": "tarde", "horario": "16:00"},
    "amanhã às 9": {"a_partir_de": "22/09/2026", "periodo": "manha", "horario": "09:00"},
    "hoje 15:30": {"a_partir_de": "21/09/2026", "periodo": "tarde", "horario": "15:30"},
    "quarta 14h": {"a_partir_de": "23/09/2026", "periodo": "tarde", "horario": "14:00"},
    "quero a segunda loja": {},
    "a mais perto": {},
    "só depois das 15h": {},
    # CONTROLES: sem hora, o contrato de antes (D-E001101-02)
    "pode ser quarta de manhã": {"a_partir_de": "23/09/2026", "periodo": "manha"},
    "a segunda": {"a_partir_de": "28/09/2026", "periodo": "qualquer"},
    "dia 30 de manhã": {"a_partir_de": "30/09/2026", "periodo": "manha"},
}
for _f, _esp in _frases.items():
    _got = PP.normalizar_preferencia_agenda(_f, hoje=HOJE)
    check(f"RED B1: {_f!r} -> {_esp}", _got == _esp, _got)
# o FIO: "4 da tarde" agenda 16:00 — nunca o 1º bloco da tarde (13:00)
banco_h, ab_h, *_ = abrir({"preferencia_agenda": "4 da tarde"})
pag_h = H.PAGINAS[ab_h["_pagina"]]
corpo_h = H._body(pag_h, "/agendamentos") or {}
check("RED B1: FIO '4 da tarde' => POST /agendamentos 1x com Horario 16:00 (22/09, Encaixe do bloco)",
      pag_h.quantas("POST", "/agendamentos") == 1 and corpo_h.get("Horario") == "16:00"
      and corpo_h.get("DataDeAgendamento") == "2026-09-22" and corpo_h.get("Encaixe") is True,
      corpo_h)
# o FIO: hora que a loja não publica (15:30) => NADA sai; agenda com as opções
banco_n, ab_n, *_ = abrir({"preferencia_agenda": "hoje 15:30"})
pag_n = H.PAGINAS[ab_n["_pagina"]]
ev_n = ab_n.get("evidence") or {}
check("RED B1: FIO '15:30' (nao publicado) => ZERO POST; desfecho agenda com continuacao",
      pag_n.quantas("POST", "/agendamentos") == 0
      and (ev_n.get("desfecho") or {}).get("tipo") == "agenda"
      and (ev_n.get("continuacao") or {}).get("acao_esperada") == "agendar",
      (pag_n.escritas(), (ev_n.get("desfecho") or {}).get("tipo")))
# CONTROLE: 'de tarde' (sem hora) segue o desenho — o 1º bloco da tarde
banco_t, ab_t, *_ = abrir({"preferencia_agenda": "pode ser de tarde"})
corpo_t = H._body(H.PAGINAS[ab_t["_pagina"]], "/agendamentos") or {}
check("CONTROLE: 'de tarde' sem hora => 13:00 (o 1º bloco da tarde, D-E001101-02)",
      corpo_t.get("Horario") == "13:00", corpo_t)

# ==========================================================================
print("\n[RED B2a/b] a releitura nunca agenda por preferencia; herda a ESCOLHA")
# ==========================================================================
banco_r, ab_r, *_ = abrir({"preferencia_agenda": "a partir de 23/09 de manhã"})
check("preparo: a preferencia do dia 23 nao casou (agenda, sem POST)",
      (ab_r["evidence"].get("desfecho") or {}).get("tipo") == "agenda"
      and H.PAGINAS[ab_r["_pagina"]].quantas("POST", "/agendamentos") == 0)
# (a) o vigia relê a ABERTURA; o dia 23 "abriu" (alias 23→22)
# ⚠️ o agregado fica PRESO no de antes do agendamento: sem isto o replay, sem
# mais `GET /atendimentos` livre, reutiliza o ÚLTIMO do HAR ([049], "Agendado
# para") e o guarda ficaria verde pelo motivo errado (B2c, não B2a).
_AG_ANTES = {"ok": True, "status": 200, "text": HAR[CUR].corpo_resp or ""}
pag_a = Hostil(HAR, cursor=CUR, alias={"2026-09-23": "2026-09-22"},
               regras={("GET", "/atendimentos"): _AG_ANTES})
j_a = rodar(banco_r, continuacao(banco_r, ab_r, "reler", extra="vigia-a"), pag_a)
check("RED B2a: reler com preferencia herdada e o dia aberto => ZERO POST /agendamentos",
      pag_a.quantas("POST", "/agendamentos") == 0
      and ((j_a.get("evidence") or {}).get("desfecho") or {}).get("tipo") == "agenda",
      pag_a.escritas())
# (b) a escolha explícita 22/09 16:00 parou por 500 no roteador; o vigia relê
pag_b0 = Hostil(HAR, cursor=CUR, regras={("GET", "/agendamentos/opcoes-disponiveis"): r500()})
j_b0 = rodar(banco_r, continuacao(banco_r, ab_r, "agendar", extra="esc",
                                  escolha={"loja": loja_1(ab_r), "dia": "22/09",
                                           "horario": "16:00"}), pag_b0)
check("preparo: a escolha parou em roteador_ilegivel sem escrever",
      (j_b0.get("evidence") or {}).get("stage") == "roteador_ilegivel" and not pag_b0.escritas())
linha_rel = continuacao(banco_r, j_b0, "reler", extra=str(j_b0["id"]))
check("RED B2b: o reler de um 'agendar' HERDA a escolha dele (e so ela)",
      linha_rel["params"]["_continuacao"]["escolha"]
      == {"loja": loja_1(ab_r), "dia": "22/09", "horario": "16:00"}
      and linha_rel["params"]["_continuacao"]["respostas"] == {},
      linha_rel["params"]["_continuacao"]["escolha"])
pag_b = Hostil(HAR, cursor=CUR, alias={"2026-09-23": "2026-09-22"})
j_b = rodar(banco_r, linha_rel, pag_b)
corpo_b = H._body(pag_b, "/agendamentos") or {}
check("RED B2b: a releitura agenda A ESCOLHA dele (22/09 16:00), nunca a preferencia (23/09 08:00)",
      pag_b.quantas("POST", "/agendamentos") == 1 and corpo_b.get("Horario") == "16:00"
      and corpo_b.get("DataDeAgendamento") == "2026-09-22",
      corpo_b)
# CONTROLE puro: reler de uma ABERTURA (sem escolha) não inventa escolha
check("CONTROLE: reler da abertura (sem escolha) => escolha vazia",
      continuacao(banco_r, ab_r, "reler", extra="x")["params"]["_continuacao"]["escolha"] == {})

# ==========================================================================
print("\n[RED B3] a agenda NAO respondeu ⇒ parada tecnica, nunca 'horario ocupado'")
# ==========================================================================
banco_3, ab_3, *_ = abrir()
agora = datetime.now(timezone.utc)
for _ep in ("/agendamentos/datas-disponiveis", "/agendamentos/horarios-disponiveis"):
    pag_3 = Hostil(HAR, cursor=CUR, regras={("GET", _ep): r500()})
    j_3 = rodar(banco_3, continuacao(banco_3, ab_3, "agendar", extra="b3" + _ep,
                                     escolha={"loja": loja_1(ab_3), "dia": "22/09",
                                              "horario": "16:00"}), pag_3)
    ev_3 = j_3.get("evidence") or {}
    txt_3 = PP.format_result(j_3)
    check(f"RED B3: 500 em {_ep} => stage agenda_nao_respondeu (nunca horario_indisponivel)",
          ev_3.get("stage") == "agenda_nao_respondeu", ev_3.get("stage"))
    check(f"RED B3: {_ep}: nada escrito, e o texto NAO diz 'ocupado'",
          not [e for e in pag_3.escritas() if e[1] != "/lojas/consultar-distancias"]
          and "ocupado" not in txt_3.split("[para a equipe", 1)[0]
          and "não respondeu" in txt_3, H._limpo(txt_3)[:200])
    check(f"RED B3: {_ep}: o vigia RELE (tecnica) e a escolha fica no job",
          VG.pedir_releitura(j_3, agora)
          and ((j_3.get("params") or {}).get("_continuacao") or {}).get("escolha", {}).get("horario")
          == "16:00")
# CONTROLE: o horário que o portal NÃO publica continua `horario_indisponivel`
pag_c3 = RV.PaginaDeReplay(HAR, cursor=CUR)
j_c3 = rodar(banco_3, continuacao(banco_3, ab_3, "agendar", extra="b3c",
                                  escolha={"loja": loja_1(ab_3), "dia": "22/09",
                                           "horario": "07:00"}), pag_c3)
check("CONTROLE: horario nao publicado => horario_indisponivel, nada sai",
      (j_c3.get("evidence") or {}).get("stage") == "horario_indisponivel"
      and pag_c3.quantas("POST", "/agendamentos") == 0)
# a TOOL: a mesma escolha depois da parada técnica ganha tentativa nova (red A3.3)
banco_t3, ab_t3, flat_t3, info_t3, _ = abrir()
flat_e = copy.deepcopy(flat_t3)
flat_e["especificos"]["escolha_agenda"] = {"loja": "1", "dia": "22/09", "horario": "16:00"}
H.chamar(banco_t3, H.EMPRESA_A, H.SESSAO_A, flat_e, info_t3,
         Hostil(HAR, cursor=CUR, regras={("GET", "/agendamentos/datas-disponiveis"): r500()}))
pag_t3 = RV.PaginaDeReplay(HAR, cursor=CUR)
banco_t3.paginas.clear()
H.chamar(banco_t3, H.EMPRESA_A, H.SESSAO_A, flat_e, info_t3, pag_t3)
check("RED B3: pela TOOL, a mesma escolha depois do 500 => 2 continuacoes e 1 POST (nao fica presa)",
      len(banco_t3.jobs(journey="continuar_atendimento")) == 2
      and pag_t3.quantas("POST", "/agendamentos") == 1,
      (len(banco_t3.jobs(journey="continuar_atendimento")), pag_t3.escritas()))

# ==========================================================================
print("\n[RED B5] o caminho DOM nao oferece domicilio")
# ==========================================================================
_job_dom = {"id": "j", "status": "needs_human", "company_id": H.EMPRESA_A,
            "journey": "abrir_atendimento",
            "params": {"dano": {"peca": "vidro de porta"}, "placa": "X"},
            "evidence": {"protocolo": "12345678",
                         "vidros_estado": {"estado": "aguardando_escolha_do_segurado",
                                           "codigo_atendimento": "12345678",
                                           "existe_algo_na_seguradora": True}},
            "created_at": "2026-09-21T10:00:00Z"}
_d = VG.diagnosticar(_job_dom, agora) or {}
_fr = PP.format_result({"status": "needs_human", "evidence": {"protocolo": "12345678"}})
check("RED B5: o vigia NAO oferece domicilio e fala da loja credenciada",
      "vai até você" not in (_d.get("para_o_segurado") or "")
      and "domic" not in (_d.get("para_o_suporte") or "").lower()
      and "loja credenciada" in (_d.get("para_o_segurado") or ""), _d)
check("RED B5: format_result do DOM NAO manda confirmar domicilio",
      "domicilio" not in _fr.lower() and "loja credenciada" in _fr, _fr[:200])

# ==========================================================================
print("\n[pendencias] P1 · P2 · P3 · J-P2 · J-P4")
# ==========================================================================
check("R-P1: leitura_falhou e agenda_nao_respondeu sao TECNICAS (o vigia rele)",
      "leitura_falhou" in PP.ESTAGIOS_TECNICOS and "agenda_nao_respondeu" in PP.ESTAGIOS_TECNICOS)
_desf = {"lojas": [{"codigo_cliente": 1, "tem_agenda": True, "horarios": {}}]}
check("R-P2: dia 31/02 e recusado na escolha (dia_ilegivel)",
      PP.mapear_escolha_de_agenda({"loja": "1", "dia": "31/02", "horario": "16:00"}, _desf)
      == (None, "dia_ilegivel"))
check("R-P2 CONTROLE: 29/02 e 22/09 atravessam",
      PP.mapear_escolha_de_agenda({"loja": "1", "dia": "29/02", "horario": "16:00"}, _desf)[1] == ""
      and PP.mapear_escolha_de_agenda({"loja": "1", "dia": "22/09", "horario": "16:00"}, _desf)[1] == "")
check("R-P3: data PASSADA no dicionario vira HOJE; 31/02 no dicionario nao vai",
      PP.normalizar_preferencia_agenda({"a_partir_de": "01/01/2020", "periodo": "manha"}, hoje=HOJE)
      == {"a_partir_de": "21/09/2026", "periodo": "manha"}
      and PP.normalizar_preferencia_agenda({"a_partir_de": "31/02/2027", "periodo": "manha"},
                                           hoje=HOJE) == {})
_blocos = {"Blocos": [
    {"Horario": "09:00", "Turno": "Manha", "QuantidadeDisponivel": 0,
     "QuantidadeEncaixeParametrizadoDisponivel": 1, "PossuiEncaixeDisponivel": False},
    {"Horario": "10:00", "Turno": "Manha", "QuantidadeDisponivel": 0,
     "QuantidadeEncaixeParametrizadoDisponivel": 1, "PossuiEncaixeDisponivel": True}]}
check("J-P2: encaixe exige PossuiEncaixeDisponivel E quantidade (a aba do bundle)",
      API.blocos_livres(_blocos) == [{"horario": "10:00", "turno": "Manha", "encaixe": True}],
      API.blocos_livres(_blocos))
_h45 = RV.primeira(HAR, "GET", "/agendamentos/horarios-disponiveis")  # 1º dia (vazio)
_todos = [RV.corpo_json(c) for c in HAR
          if c.metodo == "GET" and RV.caminho_de(c).startswith("/agendamentos/horarios-disponiveis")]
_enc = [b["horario"] for h in _todos for b in API.blocos_livres(h) if b["encaixe"]]
check("J-P2 CONTROLE: no HAR real [045] os 8 encaixes seguem livres (os dois conjuntos coincidem)",
      len(_enc) == 8 and "16:00" in _enc, _enc)


class _BancoQueCai:
    def table(self, _n):
        return self

    def __getattr__(self, _n):
        def _f(*_a, **_k):
            if _n == "execute":
                raise RuntimeError("TESTE: leitura indisponivel")
            return self
        return _f


check("J-P4: _viva() em excecao NAO segue para o INSERT (fail-closed)",
      PT.enfileirar_continuacao(_BancoQueCai(), {"company_id": H.EMPRESA_A,
                                                 "idempotency_key": "cont:x"}) == (None, None))

# ==========================================================================
print("\n[G6/A17] token nunca em claro · o banco real nunca alcancado")
# ==========================================================================
_vaz = [i for i, b in enumerate(BANCOS)
        if TOKEN and TOKEN in json.dumps(b.tabelas, ensure_ascii=False, default=str)]
check("G6: o token do portal nao aparece em claro em nenhum banco", not _vaz, _vaz)
check("A17: zero chamadas ao cliente real", not H.ALCANCOU_O_REAL, H.ALCANCOU_O_REAL)

print("\n" + "=" * 66)
print(f"  {H.PASS} asserções verdes · {H.FAIL} vermelhas")
print("=" * 66)
sys.exit(1 if H.FAIL else 0)
