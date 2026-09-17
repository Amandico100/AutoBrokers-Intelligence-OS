# -*- coding: utf-8 -*-
"""🔴 GD-1 · GD-2 · GD-3 · GD-4 · D3 (SPEC-EXTRA-001.4 D) · O HUMANO DA SEGURADORA É ATENDIDO.

📊 10/09/2026, sessão Allianz `432614de`: a sessão travou em `needs_human` às
17:21:35; às 17:35:40 a atendente da Allianz se apresentou e o motor produziu ZERO
eventos — o resumo do caso estava pronto. Às 17:38:18 a URA encerrou "por falta de
contato", frase que a regex de encerramento não conhecia; o grupo recebeu 3 alertas
sobre um caso morto. E `work_events` tinha ZERO linhas `agente.*` na base inteira.

GD-1  `needs_human` reentra E o resumo sai (uma fonte só: a tabela medida, com o
      controle negativo do robô).
GD-2  encerrada é encerrada: as redações MEDIDAS reconhecidas, e nada reabre depois.
GD-3  fila (absoluta, sem cutucada) × pessoa sumida (deslizante); heartbeat < timeout.
GD-4  o Cérebro, o Sentinela e o Vigia deixam linha `agente.*` — acerto OU não.
D3    a tela pede um dado que só o segurado sabe: pergunta, "um instante", volta.

⛔ Nada sai da máquina. As telas vêm do corpus; a frase de encerramento da Allianz
vem do BANCO (📊 17/09, 9 eventos — o corpus não a tem: limitação nomeada).
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import types
from datetime import datetime, timedelta, timezone

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.environ.setdefault("INSURER_DISPATCH_LIVE", "false")
os.environ["DISPATCH_MIRROR"] = "0"

from app.services import corridor_playbooks as CP  # noqa: E402
from app.services import insurer_dispatch_service as D  # noqa: E402
from app.services import dispatch_router as R  # noqa: E402
from app.services import o_grupo_so_o_que_importa as G  # noqa: E402
from app.services import quem_fala_na_seguradora as QF  # noqa: E402
from app.tasks import dispatch_watchdog as W  # noqa: E402

OK = FAIL = 0
REF = "allianz-residencial-whatsapp@v1"
URA = "5511999990000"
EMPRESA = "empresa-d"
CORPUS = os.path.join(RAIZ, "tests", "corpus", "telas_reais")
AGORA = lambda: datetime.now(timezone.utc)  # noqa: E731


def checar(cond, rotulo, detalhe=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok    {rotulo}")
    else:
        FAIL += 1
        print(f"  FALHA {rotulo}" + (f"\n        {detalhe}" if detalhe else ""))


def telas(nome):
    with open(os.path.join(CORPUS, f"{nome}.jsonl"), encoding="utf-8") as fh:
        return [json.loads(linha)["text"] for linha in fh]


# ---- dublês ----------------------------------------------------------------
class _Redis:
    def __init__(self):
        self.d = {}

    async def get(self, k):
        return self.d.get(k)

    async def set(self, k, v, ex=None, nx=False):
        if nx and k in self.d:
            return None
        self.d[k] = v
        return True

    async def delete(self, k):
        self.d.pop(k, None)

    async def lpop(self, k):
        return None

    async def scan_iter(self, match="*"):
        for k in list(self.d):
            if k.startswith(match.rstrip("*")):
                yield k


REDIS = _Redis()
EVENTOS = []


class _Consulta:
    def __init__(self, tabela):
        self.tabela, self.linha = tabela, None

    def insert(self, linha):
        self.linha = linha
        return self

    def __getattr__(self, _nome):
        return lambda *a, **k: self

    async def execute(self):
        if self.tabela == "work_events" and self.linha:
            EVENTOS.append(self.linha)
        return types.SimpleNamespace(data=[])


class _Banco:
    class client:  # noqa: N801
        @staticmethod
        def table(nome):
            return _Consulta(nome)


async def _redis_falso():
    return REDIS


async def _banco_falso():
    return _Banco()


import app.core.redis as _core_redis  # noqa: E402
import app.core.database as _core_db  # noqa: E402

_core_redis.get_async_redis_client = _redis_falso
_core_db.get_supabase_client = lambda: None
R._redis = _redis_falso
R._db = _banco_falso
GRUPO, ENVIADAS, WA = [], [], []


async def _porta(db, **kw):
    pode, porque = await G.o_grupo_pode_saber(
        db, company_id=kw["company_id"], tipo=kw["tipo"], sessao=kw.get("sessao"))
    GRUPO.append(kw["tipo"])
    return {"enviado": pode, "calado": not pode, "motivo": porque}


async def _destino(company_id):
    return {"destino": "120363000000000000@g.us", "fonte": "teste", "recusa": ""}


async def _diario(*a, **k):
    return True


G.enviar_ao_grupo = _porta
G.anotar_no_diario = _diario
R.resolver_destino_de_suporte = _destino


class _Wa:
    def send_message(self, fone, texto, integ=None, **k):
        WA.append((fone, texto))


_ws = types.ModuleType("app.services.whatsapp_service")
_ws.get_whatsapp_service = lambda: _Wa()
sys.modules["app.services.whatsapp_service"] = _ws
_is = types.ModuleType("app.services.integration_service")
_is.get_integration_service = lambda *a: types.SimpleNamespace()
sys.modules["app.services.integration_service"] = _is
W._canal_da_conversa = lambda integrations, company_id, session: {"id": "canal-teste"}


def rodar(c):
    return asyncio.run(c)


def ura(texto):
    ENVIADAS.append(texto)


def cliente(fone, texto):
    ENVIADAS.append(("cliente", texto))


def saidas(s):
    return [t for t in s.get("transcript") or [] if t.get("direction") == "out" and not t.get("manual")]


def sessao(estado="ura", **extra):
    s = D.new_dispatch_session(
        case_id="gd", company_id=EMPRESA, playbook_ref=REF, subservice="encanador",
        slots={"titular_cpf": "11122233344", "endereco_numero": "100",
               "telefone_contato": "48999998888", "ramo_da_apolice": "resi",
               "problema_descricao": "vazamento no banheiro"})
    s.update({"state": estado, "client_phone": "5548988887777", "work_run_id": "run-gd",
              "mirror_conversation_id": "conv-gd", "retry_count": 1})
    s.update(extra)
    return s


def rodar_inbound(texto, provider=None):
    return rodar(R.try_route_insurer_inbound(company_id=EMPRESA, from_phone=URA, text=texto,
                                             send_to_insurer=ura, send_to_client=cliente,
                                             human_reply_provider=provider))


RES = telas("allianz-residencial")
AUTO = telas("allianz-auto")
# ⚠️ O corpus guarda só a zona da URA (a fala humana fica fora dele, por desenho).
# 📊 A apresentação vem do BANCO, 17/09 (lente do dado): a redação mais frequente da
#    Allianz — "(boa tarde|bom dia), meu nome é {NOME} sou da assistência 24 horas e estou
#    aqui para te ajudar!" (233 dos 239 eventos marcados) —, com um nome fictício.
PESSOA = "Boa tarde, meu nome é Fulana sou da assistência 24 horas e estou aqui para te ajudar!"
TRANSFERENCIA = next(t for t in RES + AUTO if QF.e_transferencia_para_pessoa("allianz", t))
ROBO = next(t for t in RES + AUTO if QF.e_o_robo_se_apresentando(t))

print("=" * 74)
print("[GD-1] needs_human REENTRA e o RESUMO SAI — o relógio da atendente do 10/09")
print("=" * 74)
checar(bool(PESSOA and TRANSFERENCIA and ROBO), "📊 o corpus tem apresentação humana, transferência e o robô")
REDIS.d.clear()
rodar(R.save_active_dispatch(EMPRESA, URA, sessao("needs_human", reason="sentinela_stall",
                                                  dossier_sent=True)))
t0 = AGORA()
rodar_inbound(PESSOA)
s = rodar(R.load_active_dispatch(EMPRESA, URA))
resumo = [t for t in saidas(s) if t.get("step") == "resumo_analista"]
checar(s["state"] == "human_phase", "a sessão travada REENTROU em human_phase", s["state"])
checar(len(resumo) == 1 and (AGORA() - t0).total_seconds() <= 30, "e o resumo do caso SAIU, uma vez, em ≤ 30 s",
       str(len(resumo)))
checar(GRUPO == [G.TIPO_RETOMADA], "o grupo, que tinha o pedido de ajuda, ouviu 'retomei' — uma vez", str(GRUPO))
checar(any(e["event_type"] == "agente.cerebro" and e["payload_redacted"].get("reentrada") for e in EVENTOS),
       "a reentrada deixou linha `agente.cerebro`")
rodar_inbound(PESSOA)
s = rodar(R.load_active_dispatch(EMPRESA, URA))
checar(len([t for t in saidas(s) if t.get("step") == "resumo_analista"]) == 1,
       "a segunda fala da mesma pessoa NÃO repete o resumo")
# 🔴 CONTROLE NEGATIVO: o robô se apresentando não reabre nada.
REDIS.d.clear()
GRUPO.clear()
rodar(R.save_active_dispatch(EMPRESA, URA, sessao("needs_human", reason="sentinela_stall", dossier_sent=True)))
ROBO_SE_APRESENTA = ("Olá! Eu sou a assistente virtual da Allianz. Meu nome é Laura e darei "
                     "continuidade em seu atendimento.")
checar(D.pode_reentrar_em_fase_humana(sessao("needs_human", reason="sentinela_stall"), PESSOA, "allianz")
       and not D.pode_reentrar_em_fase_humana(sessao("needs_human", reason="sentinela_stall"),
                                               ROBO_SE_APRESENTA, "allianz"),
       "🔴 CONTROLE: a MESMA regra reabre com a pessoa e NÃO com 'sou a assistente virtual' + nome")
rodar_inbound(ROBO_SE_APRESENTA)
s = rodar(R.load_active_dispatch(EMPRESA, URA))
checar(s["state"] != "human_phase" and GRUPO == []
       and not [t for t in saidas(s) if t.get("step") == "resumo_analista"],
       "🔴 CONTROLE: pelo roteador, o robô se apresentando não reabre, não resume, não avisa", s["state"])
# 🔴 o robô que ANUNCIA a transferência na mesma mensagem (porto: a tabela negativa
#    da porto não traz o robô) também não reabre — o controle é da regra, não da tabela.
checar(not D.pode_reentrar_em_fase_humana(
    sessao("needs_human", reason="sentinela_stall"),
    "Olá! Sou a assistente virtual da Porto. Vou transferir seu atendimento.", "porto"),
    "🔴 CONTROLE: 'sou a assistente virtual' + 'vou transferir' (porto) NÃO reabre")
# 🔴 e na fase humana, o robô se apresentando não dispara o resumo.
REDIS.d.clear()
rodar(R.save_active_dispatch(EMPRESA, URA, sessao("human_phase")))
rodar_inbound(ROBO_SE_APRESENTA)
checar(not [t for t in saidas(rodar(R.load_active_dispatch(EMPRESA, URA))) if t.get("step") == "resumo_analista"],
       "🔴 CONTROLE: na fase humana, o robô se apresentando NÃO recebe o resumo do caso")
# a fonte é UMA: a tabela casa o que a regex inline antiga não casaria.
for texto in ("Seja bem-vindo(a) ao atendimento da Allianz, estou assumindo seu atendimento.",):
    REDIS.d.clear()
    rodar(R.save_active_dispatch(EMPRESA, URA, sessao("human_phase")))
    rodar_inbound(texto)
    s = rodar(R.load_active_dispatch(EMPRESA, URA))
    checar(any(t.get("step") == "resumo_analista" for t in saidas(s)),
           "🔴 o resumo sai por uma apresentação que SÓ a tabela conhece (a inline morreu)", texto[:40])
for motivo in ("insurer_closed", D.HUMANO_ASSUMIU, "handoff_trigger:sinistro"):
    checar(not D.pode_reentrar_em_fase_humana(sessao("needs_human", reason=motivo), PESSOA, "allianz"),
           f"`{motivo}` NÃO reentra")
for texto, seg in (("Olá, meu nome é _Fulana_ e vou iniciar seu atendimento", "yelum"),
                  ("Boa tarde! Darei continuidade ao seu atendimento", "porto")):
    checar(D.pode_reentrar_em_fase_humana(sessao("needs_human", reason="sentinela_stall"), texto, seg),
           f"a pessoa que só a regex antiga pegava ({seg}) reabre a sessão (lente)")
checar(not QF.uma_pessoa_se_apresentou("porto", "Para dar continuidade ao seu atendimento, digite o CPF do titular."),
       "🔴 CONTROLE: 'para DAR continuidade AO seu atendimento, digite…' é o robô (confirmação)")
checar(QF.e_transferencia_para_pessoa("allianz", "vou transferir seu caso para um espe­cialista"),
       "🔴 o dialeto: o soft hyphen do acervo não esconde a transferência (a MESMA normalização da régua)")

print()
print("=" * 74)
print("[GD-2] ENCERRADA É ENCERRADA — pelas redações MEDIDAS")
print("=" * 74)
# 📊 BANCO, 17/09 (`observed_events`, normalizado, sem PII): 9 eventos allianz.
FALTA_DE_CONTATO = ("Olá! Este canal é exclusivo para atendimento emergencial. Por falta de "
                    "contato, estou encerrando o nosso atendimento. Fique tranquilo!")
checar(D.seguradora_encerrou(FALTA_DE_CONTATO), "a frase do 10/09 ('por falta de contato') é encerramento")
checar(D.seguradora_encerrou("Vou encerrar a conversa." + chr(10) + "Quando precisar, é só chamar de novo 👋"),
       "a porto que quebra a linha antes do 'quando precisar' também encerra (lente)")
# 🔴 O FUTURO CONDICIONAL É AVISO (lente do dado): 📊 51 eventos, a conversa seguiu.
avisos_futuros = [t for nome in ("hdi-auto", "hdi-residencial", "yelum-auto", "yelum-residencial", "mapfre-auto")
                  for t in telas(nome) if "sera encerrada" in D._norm_text(t)
                  and "por isso, esta conversa sera encerrada" not in D._norm_text(t)]
checar(len(avisos_futuros) >= 10 and not any(D.seguradora_encerrou(t) for t in avisos_futuros),
       f"🔴 as {len(avisos_futuros)} telas do corpus com 'será encerrada' condicional NÃO encerram",
       str([t[:60] for t in avisos_futuros if D.seguradora_encerrou(t)][:2]))
_s = D.handle_insurer_message(sessao("ura"), avisos_futuros[0]) if avisos_futuros else {}
checar(_s.get("reason") != "insurer_closed", "🔴 e o motor NÃO fecha a sessão numa delas", str(_s.get("reason")))
checar(D.seguradora_encerrou("Sua resposta não corresponde a nossa pergunta. Por isso, esta conversa será encerrada."),
       "o futuro SECO (yelum) continua sendo encerramento")
todas = [t for nome in ("porto-auto", "porto-residencial", "azul-auto", "zurich-auto") for t in telas(nome)]
fechos = [t for t in todas if "precisar encerrar a conversa" in D._norm_text(t)
          or "vou encerrar nosso atendimento" in D._norm_text(t)]
checar(fechos and all(D.seguradora_encerrou(t) for t in fechos),
       f"📊 as {len(fechos)} telas de encerramento do corpus (porto/azul/zurich) são reconhecidas")
avisos = [t for t in telas("bradesco-auto") + telas("mapfre-auto") + todas
          if "digitar sair" in D._norm_text(t) or "vou encerrar seu atendimento em" in D._norm_text(t)]
checar(avisos and not any(D.seguradora_encerrou(t) for t in avisos),
       f"🔴 CONTROLE: as {len(avisos)} telas de AVISO/INSTRUÇÃO ('digitar sair', 'em ## minutos') não encerram")
checar(not D.seguradora_encerrou("Olá cliente. Infelizmente por falta de contato, sua conversa foi colocada em espera."),
       "🔴 CONTROLE: a hdi 'colocada em espera' não é encerramento")
REDIS.d.clear()
rodar(R.save_active_dispatch(EMPRESA, URA, sessao("needs_human", reason="sentinela_stall", dossier_sent=True)))
rodar_inbound(FALTA_DE_CONTATO)
rodar_inbound(PESSOA)
checar(rodar(R.load_active_dispatch(EMPRESA, URA)) is None,
       "🔴 depois do encerramento, ZERO human_phase: a sessão foi liberada e a apresentação não a reabre")

print()
print("=" * 74)
print("[GD-3] DOIS RELÓGIOS — fila ≠ pessoa sumida")
print("=" * 74)
checar(W.HUMAN_NUDGE_S < W.FILA_ALERTA_S, "🔴 invariante: heartbeat (600) < timeout da fila (1200)")
s = sessao("ura")
s = D.handle_insurer_message(s, TRANSFERENCIA)
checar(s["state"] == "human_phase" and s.get("fila_desde") and not saidas(s),
       "a TRANSFERÊNCIA medida põe em fase humana, liga a fila e não responde")
s["transcript"][-1]["at"] = (AGORA() - timedelta(seconds=45)).isoformat()
checar(W.diagnose(s) is None, "🔴 45 s depois da transferência, o Sentinela NÃO responde a ela")
s["fila_desde"] = (AGORA() - timedelta(minutes=15)).isoformat()
s["transcript"].append({"direction": "out", "text": "resumo", "at": (AGORA() - timedelta(minutes=11)).isoformat()})
checar(W.diagnose(s) is None, "🔴 fila de 15 min, nosso último envio há 11 min: NENHUMA cutucada")
s["fila_desde"] = (AGORA() - timedelta(minutes=21)).isoformat()
checar(W.diagnose(s) == "fila_longa", "fila de 21 min: o alerta da fila, no prazo medido", str(W.diagnose(s)))
s["humano_falou_em"] = (AGORA() - timedelta(minutes=12)).isoformat()
checar(W.diagnose(s) == "human_silent_nudge", "a pessoa falou e sumiu 11 min: cutucada", str(W.diagnose(s)))

print()
print("=" * 74)
print("[GD-4] O AGENTE DEIXA RASTRO — acerto ou não")
print("=" * 74)
EVENTOS.clear()
REDIS.d.clear()
_SO_O_CEREBRO = "Entendi. Pode me explicar um pouco melhor como o problema começou?"
rodar(R.save_active_dispatch(EMPRESA, URA, sessao("human_phase", pending_insurer_messages=[_SO_O_CEREBRO])))


async def _nao_sei(sessao_, tela):
    return "NAO_SEI"


rodar_inbound(_SO_O_CEREBRO, provider=_nao_sei)
checar(any(e["event_type"] == "agente.cerebro" and e["payload_redacted"].get("desfecho") == "recusado"
           for e in EVENTOS), "o Cérebro RECUSADO deixa `agente.cerebro`",
       str([e["event_type"] for e in EVENTOS]))


async def _sem_resposta(*a, **k):
    return None


W._adaptive_reply = _sem_resposta


async def _dossie(*a, **k):
    return False


W._entregar_dossie_com_marcador = _dossie
EVENTOS.clear()
s = sessao("ura")
s["transcript"].append({"direction": "in", "text": "tela sem resposta", "at": AGORA().isoformat()})
rodar(W._sentinela_recover(EMPRESA, URA, s, _Wa(), {"id": "x"}))
checar([e["payload_redacted"].get("desfecho") for e in EVENTOS if e["event_type"] == "agente.sentinela"]
       == ["sem_resposta_aprovada", "esgotou"], "o Sentinela que não conseguiu deixa `agente.sentinela` (2 linhas)",
       str([(e["event_type"], e["payload_redacted"].get("desfecho")) for e in EVENTOS]))
EVENTOS.clear()
rodar(W._ato_do_vigia(EMPRESA, sessao("human_phase"), "fila_longa"))
checar([e["event_type"] for e in EVENTOS] == ["agente.vigia"], "o Vigia deixa `agente.vigia`")
checar(all(e["actor_type"] == "agent" and "payload_redacted" in e for e in EVENTOS), "ator `agent`, sem PII no evento")

print()
print("=" * 74)
print("[D3] A TELA PEDE O QUE SÓ O SEGURADO SABE — pergunta, segura, volta")
print("=" * 74)
_PB = CP.get_playbook(REF)
PEDE = next((t for t in RES if CP.match_ura_step(_PB, t, subservice="encanador") is None
             and D.responder_da_ficha(_PB, t, {}).get("motivo") == "sem_dado_na_ficha"
             and not str(D.responder_da_ficha(_PB, t, {}).get("slot") or "").endswith("_opcao")
             and CP._COMO_PERGUNTAR.get(str(D.responder_da_ficha(_PB, t, {}).get("slot") or ""))), "")
SLOT = str(D.responder_da_ficha(_PB, PEDE, {}).get("slot") or "")
checar(bool(PEDE), "📊 o corpus tem uma tela que pede um dado fora da ficha", SLOT)
# 🔴 EM ENSAIO (o portão de `_emit` fechado), a pergunta é registrada e NÃO sai (juiz, P6).
REDIS.d.clear()
ENVIADAS.clear()
s = sessao("human_phase", humano_falou_em=AGORA().isoformat())
s["slots"].pop(SLOT, None)
rodar(R.save_active_dispatch(EMPRESA, URA, s))
rodar_inbound(PEDE, provider=_nao_sei)
s = rodar(R.load_active_dispatch(EMPRESA, URA))
checar(ENVIADAS == [] and any(t.get("step") == "pergunta_ao_segurado" and t.get("dry_run") for t in saidas(s)),
       "🔴 em ensaio, a pergunta fica no registro (dry_run) e nada sai", str(ENVIADAS)[:80])
# daqui em diante, AO VIVO — os remetentes são todos dublês.
os.environ["INSURER_DISPATCH_LIVE"] = "true"
REDIS.d.clear()
ENVIADAS.clear()
s = sessao("human_phase", humano_falou_em=AGORA().isoformat())
s["slots"].pop(SLOT, None)
rodar(R.save_active_dispatch(EMPRESA, URA, s))
rodar_inbound(PEDE, provider=_nao_sei)
s = rodar(R.load_active_dispatch(EMPRESA, URA))
checar(any(isinstance(x, tuple) and "me diga" in x[1] for x in ENVIADAS),
       "① a pergunta saiu pelo canal do SEGURADO", str(ENVIADAS)[:120])
checar(R.HOLDING_A_SEGURADORA in ENVIADAS, "② o 'um instante' saiu para a SEGURADORA")
checar((s.get("esperando_do_segurado") or {}).get("slot") == SLOT and "CEREBRO" not in str(ENVIADAS),
       "③ a espera está na sessão, e o Cérebro não respondeu NAO_SEI no lugar dele")
checar(not rodar(R.responder_pergunta_do_acionamento(EMPRESA, "5548911112222", "perto da padaria",
                                                     send_to_client=cliente)),
       "🔴 CONTROLE: a mensagem de OUTRO telefone não é a resposta")
WA.clear()
for solto in ("Ok!", "obrigada 🙏", "Como assim?",
              "[Cliente enviou uma mídia que não consegui baixar — peça para reenviar]"):
    checar(not rodar(R.responder_pergunta_do_acionamento(EMPRESA, "5548988887777", solto, send_to_client=cliente))
           and WA == [], f"🔴 {solto[:20]!r} não é levado à seguradora como resposta")
WA.clear()
checar(rodar(R.responder_pergunta_do_acionamento(EMPRESA, "48 98888-7777", "perto da padaria",
                                                 send_to_client=cliente)),
       "④ a resposta do segurado (noutra forma do número) é reconhecida")
s = rodar(R.load_active_dispatch(EMPRESA, URA))
checar(WA == [(URA, "perto da padaria")] and s["slots"].get(SLOT) == "perto da padaria"
       and not s.get("esperando_do_segurado") and not s.get("falta_para_a_ura"),
       "e VOLTOU: a seguradora recebeu, o slot foi preenchido, a espera e a 'falta' fecharam",
       str(WA))
# prazo vencido: segura até o teto e, esgotado, uma pessoa com o que falta.
s = sessao("human_phase", humano_falou_em=AGORA().isoformat(),
                   esperando_do_segurado={"slot": SLOT, "rotulo": "o dado", "client_phone": "5548988887777",
                                                   "ate": (AGORA() - timedelta(seconds=1)).isoformat(), "holdings": 0})
s["transcript"].append({"direction": "out", "text": "x", "at": AGORA().isoformat()})
desfechos = []
for _ in range(3):
    checar(W.diagnose(s) == "segurado_sem_resposta", "o Vigia vê o prazo vencido", str(W.diagnose(s)))
    desfechos.append(rodar(W._segurar_ou_desistir(EMPRESA, URA, s, _Wa(), {"id": "x"})))
    if s.get("esperando_do_segurado"):
        s["esperando_do_segurado"]["ate"] = (AGORA() - timedelta(seconds=1)).isoformat()
checar(desfechos == ["segurou", "segurou", "desistiu"], "segura · segura · e desiste (teto 2)", str(desfechos))
checar(s["state"] == "needs_human" and s["reason"] == "segurado_nao_respondeu"
       and "não respondeu" in s["falta_para_a_ura"]["rotulo"], "o dossiê diz exatamente o que falta")
checar(D.motivo_reentravel("segurado_nao_respondeu"), "e a seguradora que voltar a falar reabre o caso")
s = sessao("human_phase", humano_falou_em=AGORA().isoformat(),
                   esperando_do_segurado={"slot": SLOT, "rotulo": "o dado", "client_phone": "5548988887777",
                                                   "ate": (AGORA() + timedelta(seconds=50)).isoformat(), "holdings": 0})
s = D.handle_insurer_message(s, FALTA_DE_CONTATO)
checar(s["reason"] == "insurer_closed" and "encerrou enquanto eu esperava" in s["falta_para_a_ura"]["rotulo"],
       "a seguradora encerrou antes: para tudo, e o dossiê diz isso")
REDIS.d.clear()
ENVIADAS.clear()
s = sessao("human_phase", humano_falou_em=AGORA().isoformat())
s["slots"].pop(SLOT, None)
s["falta_para_a_ura"] = {"slot": "qual_seguro_opcao", "campo": "x", "rotulo": "x"}
rodar(R.save_active_dispatch(EMPRESA, URA, s))
rodar_inbound("Pode aguardar um momento?")
checar(not any(isinstance(x, tuple) for x in ENVIADAS), "🔴 CONTROLE: tecla de menu (`*_opcao`) NUNCA vira pergunta ao segurado")


print()
print("=" * 74)
print("[D3-B] O 'UM INSTANTE' SÓ COM PESSOA — com robô, NADA sai à seguradora")
print("=" * 74)
# 🔴 O PAR. A MESMA tela, o MESMO slot, a MESMA pergunta ao segurado — muda só
#    quem está do outro lado. Com robô (`ura`) o holding é um texto solto num
#    menu; com pessoa (`human_phase`) é o que segura os 103 s da Allianz.
os.environ["INSURER_DISPATCH_LIVE"] = "true"
# 📊 17/09: `state == "human_phase"` NÃO distingue os dois — o motor promove
#    QUALQUER tela sem âncora de URA. Quem prova que há gente é `humano_falou_em`.
for estado, marca, holdings_esperados in (("robô", {}, 0),
                                          ("pessoa", {"humano_falou_em": AGORA().isoformat()}, 1)):
    REDIS.d.clear()
    ENVIADAS.clear()
    s = sessao("ura", **marca)
    s["slots"].pop(SLOT, None)
    rodar(R.save_active_dispatch(EMPRESA, URA, s))
    rodar_inbound(PEDE, provider=_nao_sei)
    s = rodar(R.load_active_dispatch(EMPRESA, URA))
    _holdings = [x for x in ENVIADAS if x == R.HOLDING_A_SEGURADORA]
    _ao_segurado = [x for x in ENVIADAS if isinstance(x, tuple)]
    checar(len(_holdings) == holdings_esperados,
           f"🔴 `{estado}`: {holdings_esperados} 'um instante' à seguradora",
           f"{len(_holdings)} — {ENVIADAS}")
    checar(len(_ao_segurado) == 1 and (s.get("esperando_do_segurado") or {}).get("slot") == SLOT,
           f"🔴 CONTROLE do par: em `{estado}` a pergunta ao segurado sai igual, "
           "e a espera fica na sessão", str(_ao_segurado)[:100])
# e o Vigia segue a mesma regra: com robô ele espera CALADO
for estado, marca, desfecho in (("robô", {}, "esperou_calado"),
                                ("pessoa", {"humano_falou_em": AGORA().isoformat()}, "segurou")):
    WA.clear()
    s = sessao("human_phase",
                   esperando_do_segurado={
        "slot": SLOT, "rotulo": "o dado", "client_phone": "5548988887777",
        "ate": (AGORA() - timedelta(seconds=1)).isoformat(), "holdings": 0}, **marca)
    s["transcript"].append({"direction": "out", "text": "x", "at": AGORA().isoformat()})
    checar(rodar(W._segurar_ou_desistir(EMPRESA, URA, s, _Wa(), {"id": "x"})) == desfecho
           and len(WA) == (0 if desfecho == "esperou_calado" else 1),
           f"🔴 o Vigia em `{estado}`: {desfecho} — {0 if desfecho == 'esperou_calado' else 1} envio",
           str(WA))
    checar(R._idade_segundos(s["esperando_do_segurado"]["ate"]) < 0,
           f"🔴 e o relógio do segurado corre IGUAL em `{estado}` (o prazo foi estendido)")

print()
print("=" * 74)
print("[D3-C] O CÉREBRO ANTES DO SEGURADO — e a PROVA DE ORIGEM")
print("=" * 74)


class _Resposta:
    def __init__(self, texto):
        self.content = texto


class _LLM:
    def __init__(self, texto):
        self.texto, self.chamadas = texto, 0

    async def ainvoke(self, msgs):
        self.chamadas += 1
        self.pedido = "\n".join(str(getattr(m, "content", "")) for m in msgs)
        return _Resposta(self.texto)


_real_cerebro = R.o_cerebro_ja_sabe
LLM_ATUAL = [None]


async def _cerebro_com_llm_falso(company_id, session, *, slot, rotulo, tela, llm=None):
    """🔴 O MOTOR é o de verdade (fontes + prova de origem); só o MODELO é dublê."""
    return await _real_cerebro(company_id, session, slot=slot, rotulo=rotulo,
                              tela=tela, llm=LLM_ATUAL[0])


R.o_cerebro_ja_sabe = _cerebro_com_llm_falso
# a conversa do segurado, do banco (SELECT com `company_id` — CLAUDE.md §7)
CONVERSA = ["Boa tarde, preciso de um encanador",
            "o ponto de referencia e em frente a padaria Sao Jorge",
            "obrigado"]
FILTROS = []


class _ConsultaLendo(_Consulta):
    def __init__(self, tabela):
        super().__init__(tabela)
        self.eqs = {}

    def eq(self, campo, valor):
        self.eqs[campo] = valor
        return self

    async def execute(self):
        if self.tabela == "conversations":
            FILTROS.append(dict(self.eqs))
            return types.SimpleNamespace(
                data=[{"id": "conv-do-segurado"}] if self.eqs.get("company_id") == EMPRESA else [])
        if self.tabela == "messages":
            return types.SimpleNamespace(
                data=[{"role": "user", "content": t} for t in reversed(CONVERSA)])
        return await super().execute()


class _BancoLendo:
    class client:  # noqa: N801
        @staticmethod
        def table(nome):
            return _ConsultaLendo(nome)


_core_db.get_supabase_client = lambda: _BancoLendo()


def _rodar_d3(estado="human_phase"):
    REDIS.d.clear()
    ENVIADAS.clear()
    EVENTOS.clear()
    FILTROS.clear()
    s = sessao(estado)
    s["slots"].pop(SLOT, None)
    rodar(R.save_active_dispatch(EMPRESA, URA, s))
    rodar_inbound(PEDE, provider=_nao_sei)
    return rodar(R.load_active_dispatch(EMPRESA, URA))


# ① o Cérebro ACHA o valor na conversa → 0 perguntas ao segurado, origem gravada
LLM_ATUAL[0] = _LLM("em frente a padaria Sao Jorge")
s = _rodar_d3()
checar(not any(isinstance(x, tuple) for x in ENVIADAS)
       and not s.get("esperando_do_segurado"),
       "🔴 o Cérebro achou: ZERO perguntas ao segurado", str(ENVIADAS)[:120])
checar(s["slots"].get(SLOT) == "em frente a padaria Sao Jorge"
       and str(s.get("origem_das_teclas", {}).get(SLOT) or "").startswith("cerebro:"),
       "🔴 o valor foi para a seguradora E a ORIGEM ficou gravada",
       str(s.get("origem_das_teclas", {}).get(SLOT)))
checar(s["slots"].get(SLOT) in ENVIADAS, "② a resposta saiu à seguradora", str(ENVIADAS)[:120])
checar(any(f.get("company_id") == EMPRESA for f in FILTROS),
       "🔴 CLAUDE.md §7: a conversa do segurado é lida COM `company_id` no filtro", str(FILTROS))
checar(any(e["event_type"] == "acionamento.dado_faltou"
           and e["payload_redacted"].get("origem_da_resposta") == "cerebro" for e in EVENTOS),
       "③ o rastro diz `origem_da_resposta=cerebro`",
       str([(e["event_type"], e["payload_redacted"].get("origem_da_resposta")) for e in EVENTOS]))
_rastro = next(e for e in EVENTOS if e["event_type"] == "acionamento.dado_faltou")
checar(set(_rastro["payload_redacted"]) >= {"rota", "tela", "slot", "origem_da_resposta",
                                            "ja_perguntado_antes_do_acionamento"}
       and len(_rastro["payload_redacted"]["tela"]) <= 300
       and _rastro["payload_redacted"]["slot"] == SLOT
       and s["slots"][SLOT] not in json.dumps(_rastro["payload_redacted"], ensure_ascii=False),
       "🔴 o rastro tem os cinco campos, a tela cabe em 300 e o VALOR não entra nele",
       str(sorted(_rastro["payload_redacted"])))
# ② o Cérebro NÃO acha → 1 pergunta ao segurado (o PAR do ①)
LLM_ATUAL[0] = _LLM("NAO_SEI")
s = _rodar_d3()
checar(len([x for x in ENVIADAS if isinstance(x, tuple)]) == 1
       and (s.get("esperando_do_segurado") or {}).get("slot") == SLOT,
       "🔴 CONTROLE: o Cérebro não achou → UMA pergunta ao segurado", str(ENVIADAS)[:120])
checar(any(e["event_type"] == "acionamento.dado_faltou"
           and e["payload_redacted"].get("origem_da_resposta") == "segurado" for e in EVENTOS),
       "e o rastro diz `origem_da_resposta=segurado`")
# ③ valor que NÃO está em fonte nenhuma → RECUSADO (a trava contra inventar)
LLM_ATUAL[0] = _LLM("ao lado do posto de gasolina Ipiranga")
s = _rodar_d3()
checar(len([x for x in ENVIADAS if isinstance(x, tuple)]) == 1
       and s["slots"].get(SLOT) is None
       and "posto de gasolina" not in str(ENVIADAS),
       "🔴 PROVA DE ORIGEM: valor que não está em fonte nenhuma é RECUSADO — e o "
       "segurado é perguntado", str(ENVIADAS)[:140])
# ④ a função pura, nos dois sentidos
_fontes = [("ficha", "titular_cpf: 111 | endereco_numero: 100"),
           ("conversa", "o ponto de referencia e em frente a padaria Sao Jorge")]
checar(R.valor_tem_origem("Padaria São Jorge", _fontes) == "conversa"
       and R.valor_tem_origem("100", _fontes) == "ficha"
       and R.valor_tem_origem("posto Ipiranga", _fontes) is None
       and R.valor_tem_origem("a", _fontes) is None,
       "🔴 `valor_tem_origem` acha com acento e pontuação diferentes, e recusa o que não está lá")
# ⑤ CONTROLE: desligado por env, o Cérebro não é nem consultado
os.environ["CEREBRO_ANTES_DO_SEGURADO"] = "0"
LLM_ATUAL[0] = _LLM("em frente a padaria Sao Jorge")
s = _rodar_d3()
checar(LLM_ATUAL[0].chamadas == 0 and len([x for x in ENVIADAS if isinstance(x, tuple)]) == 1,
       "🔴 CONTROLE: `CEREBRO_ANTES_DO_SEGURADO=0` volta ao comportamento de antes",
       f"chamadas={LLM_ATUAL[0].chamadas}")
os.environ.pop("CEREBRO_ANTES_DO_SEGURADO")

print()
print("=" * 74)
print("[D3-D] NINGUÉM FICA NO VÁCUO — e a resposta tardia não se perde")
print("=" * 74)
LLM_ATUAL[0] = _LLM("NAO_SEI")
REDIS.d.clear()
GRUPO.clear()
EVENTOS.clear()
WA.clear()
_dossies = []


async def _dossie_pela_porta(company_id, session, dossier, wa, integration):
    """A PORTA ÚNICA da 001.3 é a real: o dossiê passa por `o_grupo_pode_saber`."""
    pode, _ = await G.o_grupo_pode_saber(None, company_id=company_id,
                                         tipo=G.TIPO_PEDIDO_DE_AJUDA, sessao=session)
    _dossies.append({"pode": pode, "texto": dossier})
    return pode


W._entregar_dossie_com_marcador = _dossie_pela_porta
s = sessao("human_phase", humano_falou_em=AGORA().isoformat(),
                   esperando_do_segurado={
    "slot": SLOT, "rotulo": "o ponto de referência", "client_phone": "5548988887777",
    "ate": (AGORA() - timedelta(seconds=1)).isoformat(), "holdings": 0})
s["transcript"].append({"direction": "out", "text": "x", "at": AGORA().isoformat()})
desfechos = []
for _ in range(3):
    desfechos.append(rodar(W._segurar_ou_desistir(EMPRESA, URA, s, _Wa(), {"id": "x"})))
    if s.get("esperando_do_segurado"):
        s["esperando_do_segurado"]["ate"] = (AGORA() - timedelta(seconds=1)).isoformat()
checar(desfechos == ["segurou", "segurou", "desistiu"], "segura · segura · e desiste (teto 2)",
       str(desfechos))
checar(s["state"] == "needs_human" and s["reason"] == "segurado_nao_respondeu",
       "esgotado o prazo, a sessão vai a `needs_human`")
checar(len(_dossies) == 1 and _dossies[0]["pode"]
       and "não respondeu o ponto de referência" in _dossies[0]["texto"],
       "🔴 o dossiê sai pela PORTA ÚNICA da 001.3 e diz, em português, o que faltou",
       str(_dossies)[:160])
checar((s.get("espera_vencida") or {}).get("slot") == SLOT and not s.get("esperando_do_segurado"),
       "🔴 a espera vencida FICA na sessão — é o que impede a resposta tardia de se perder")
# a resposta TARDIA chega depois do handoff
rodar(R.save_active_dispatch(EMPRESA, URA, s))
rodar(R._indexar_pergunta(EMPRESA, "5548988887777", URA, 600))
EVENTOS.clear()
WA.clear()
ENVIADAS.clear()
checar(rodar(R.responder_pergunta_do_acionamento(EMPRESA, "5548988887777",
                                                 "em frente a padaria Sao Jorge",
                                                 send_to_client=cliente)),
       "🔴 a resposta que chega DEPOIS do prazo é reconhecida (não se perde)")
s = rodar(R.load_active_dispatch(EMPRESA, URA))
_tardio = [e for e in EVENTOS if e["event_type"] == "pergunta_ao_segurado.respondida_tarde"]
checar(s["slots"].get(SLOT) == "em frente a padaria Sao Jorge" and not s.get("espera_vencida"),
       "o dado entrou na ficha do caso e a espera vencida fechou")
checar(len(_tardio) == 1 and _tardio[0]["payload_redacted"].get("retomada") == "guardada"
       and WA == [],
       "🔴 e o RASTRO diz o que aconteceu (`retomada=guardada`): o caso já é de uma "
       "pessoa, e nada foi mandado à seguradora por cima dela", str(_tardio)[:160])
# 🔴 CONTROLE: com o acionamento AINDA DE PÉ, a mesma porta LEVA a resposta
REDIS.d.clear()
EVENTOS.clear()
WA.clear()
s = sessao("human_phase", espera_vencida={
    "slot": SLOT, "rotulo": "o ponto de referência", "client_phone": "5548988887777",
    "ate": (AGORA() - timedelta(seconds=90)).isoformat(), "holdings": 2})
rodar(R.save_active_dispatch(EMPRESA, URA, s))
rodar(R._indexar_pergunta(EMPRESA, "5548988887777", URA, 600))
rodar(R.responder_pergunta_do_acionamento(EMPRESA, "5548988887777", "em frente a padaria",
                                          send_to_client=cliente))
_tardio = [e for e in EVENTOS if e["event_type"] == "pergunta_ao_segurado.respondida_tarde"]
checar(WA == [(URA, "em frente a padaria")] and len(_tardio) == 1
       and _tardio[0]["payload_redacted"].get("retomada") == "levada",
       "🔴 CONTROLE do par: com o acionamento de pé, a resposta tardia é LEVADA à "
       "seguradora e o rastro diz `retomada=levada`", f"{WA} {_tardio}"[:160])
R.o_cerebro_ja_sabe = _real_cerebro
print()
print("=" * 74)
print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
print("=" * 74)
sys.exit(1 if FAIL else 0)
