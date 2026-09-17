# -*- coding: utf-8 -*-
"""🔴 GC-1 + GC-2 + GC-3 + GT · A ATENDENTE NA URA CALA O ROBÔ — SEM APRENDER PALAVRA.

📊 10/09/2026, sessão Allianz `432614de`: às 17:18:12 a atendente da corretora
digitou "1" à mão na conversa com a URA; às 17:18:14 e :16 o corredor digitou de
novo. `note_manual_outbound` fazia três escritas e NENHUM bloqueio.

🔴 **A REGRA MUDOU EM 17/09/2026 (Founder), e o guarda mudou com ela**
(CLAUDE.md §9.3: o fato mudou, o teste muda, a lição migra):

```
ANTES   1ª fala abre 60 s, renovável 2×; um AVISO ao grupo pede AGENTE ou EU CUIDO
AGORA   1ª fala abre 15 s e NADA SAI;  2ª fala dentro dos 15 s = ela assumiu, em silêncio
```

GC-1  a 1ª fala abre a janela: o motor não responde, o Cérebro não redige, o Vigia
      não chama o Sentinela — e NADA sai a ninguém. O eco da nossa voz não pausa.
GC-2  a 2ª fala DENTRO da janela assume (0 envios); depois dela, é uma janela nova.
GC-3  com a janela aberta, todo aviso ao grupo do acionamento cala na guarda ÚNICA
      (`o_grupo_pode_saber`, da 001.3) — e todo ponto de envio passa a sessão.
GT    duas corretoras, mesma seguradora, mesma tela: a janela de uma não cala a outra.

⛔ Nada sai da máquina: WhatsApp, banco, Redis, espelho e grupo são dublês.
"""
from __future__ import annotations

import ast
import asyncio
import json
import os
import sys
from datetime import datetime, timedelta, timezone

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.environ.setdefault("INSURER_DISPATCH_LIVE", "false")
os.environ["DISPATCH_MIRROR"] = "0"

from app.services import insurer_dispatch_service as D  # noqa: E402
from app.services import dispatch_router as R  # noqa: E402
from app.services import o_grupo_so_o_que_importa as G  # noqa: E402
from app.tasks import dispatch_watchdog as W  # noqa: E402

OK = FAIL = 0
REF = "allianz-residencial-whatsapp@v1"
URA = "5511999990000"
A, B = "empresa-a", "empresa-b"
CORPUS = os.path.join(RAIZ, "tests", "corpus", "telas_reais", "allianz-residencial.jsonl")


def checar(cond, rotulo, detalhe=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok    {rotulo}")
    else:
        FAIL += 1
        print(f"  FALHA {rotulo}" + (f"\n        {detalhe}" if detalhe else ""))


# ---- os dublês: Redis em memória, banco mudo, grupo e destino fixos ---------
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
        prefixo = match.rstrip("*")
        for k in list(self.d):
            if k.startswith(prefixo):
                yield k


REDIS = _Redis()


async def _redis_falso():
    return REDIS


import types  # noqa: E402

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


async def _banco_falso():
    return _Banco()


import app.core.redis as _core_redis  # noqa: E402

_core_redis.get_async_redis_client = _redis_falso
R._redis = _redis_falso
R._db = _banco_falso
GRUPO = []


async def _enviar_ao_grupo_real_ate_a_guarda(db, **kw):
    """A GUARDA É A REAL; o que vem depois dela é dublê."""
    pode, porque = await G.o_grupo_pode_saber(
        db, company_id=kw["company_id"], conversation_id=kw.get("conversation_id", ""),
        telefone=kw.get("telefone", ""), tipo=kw["tipo"], sessao=kw.get("sessao"))
    GRUPO.append({"tipo": kw["tipo"], "pode": pode, "porque": porque, "texto": kw.get("texto", "")})
    return {"enviado": pode, "calado": not pode, "motivo": porque, "destino_ok": True}


G.enviar_ao_grupo = _enviar_ao_grupo_real_ate_a_guarda


async def _diario(*a, **k):
    return True


G.anotar_no_diario = _diario


async def _destino(company_id):
    return {"destino": "120363000000000000@g.us", "fonte": "teste", "recusa": ""}


R.resolver_destino_de_suporte = _destino


async def _casa(db, company_id):
    return G._variantes("5548900000001")   # o número de alguém da equipe


G.numeros_da_casa = _casa
import app.core.database as _core_db  # noqa: E402

_core_db.get_supabase_client = lambda: None


def tela_real():
    for linha in open(CORPUS, encoding="utf-8"):
        t = json.loads(linha)["text"]
        if "qual seguro deseja utilizar" in D._norm_text(t) and "3 - empresarial" in D._norm_text(t):
            return t
    return ""


TELA = tela_real()


def nova_sessao(empresa):
    s = D.new_dispatch_session(
        case_id=f"gc-{empresa}", company_id=empresa, playbook_ref=REF, subservice="encanador",
        slots={"titular_cpf": "11122233344", "endereco_numero": "100",
               "telefone_contato": "48999998888", "ramo_da_apolice": "resi"})
    s.update({"state": "ura", "client_phone": "5548988887777", "work_run_id": "run-gc",
              "mirror_conversation_id": f"conv-{empresa}"})
    return s


ENVIADAS = []


def _para_ura(texto):
    ENVIADAS.append(texto)


def _para_cliente(fone, texto):
    ENVIADAS.append(("cliente", texto))


async def _cerebro(sessao, tela):
    ENVIADAS.append("CEREBRO_CHAMADO")
    return "1"


def saidas_do_robo(sessao):
    """As saídas NOSSAS (não manuais) — `_emit` as registra também em dry-run,
    então esta medida consegue ficar vermelha; o remetente, fora do ar, não."""
    return [t["text"] for t in sessao.get("transcript") or []
            if t.get("direction") == "out" and not t.get("manual")]


def rodar(corrotina):
    return asyncio.run(corrotina)


def envelhecer(sessao, segundos):
    """A última entrada do transcript fica `segundos` no passado."""
    sessao["transcript"][-1]["at"] = (datetime.now(timezone.utc)
                                      - timedelta(seconds=segundos)).isoformat()


print("=" * 74)
print("[GC-1] A 1ª FALA ABRE A JANELA DE 15 s — E NADA SAI A NINGUÉM")
print("=" * 74)
checar(bool(TELA), "📊 a tela real do menu 'Qual seguro' está no corpus")
checar(D.PAUSA_HUMANA_S == 15,
       "🔴 a janela é de 15 s (Founder, 17/09) — não de 60", str(D.PAUSA_HUMANA_S))
checar(not hasattr(D, "PAUSA_HUMANA_MAX_RENOVACOES") and not hasattr(D, "abrir_ou_renovar_pausa"),
       "🔴 a RENOVAÇÃO morreu com o nome: nem a constante nem a função sobreviveram")
checar(not hasattr(R, "aviso_da_pausa_humana"),
       "🔴 o aviso que pedia AGENTE / EU CUIDO não existe mais no produto")
REDIS.d.clear()
GRUPO.clear()
ENVIADAS.clear()
EVENTOS.clear()
s = nova_sessao(A)
rodar(R.save_active_dispatch(A, URA, s))
rodar(R.note_manual_outbound(A, URA, "1", foi_humano=True))
s = rodar(R.load_active_dispatch(A, URA))
checar(D.pausa_humana_aberta(s), "a 1ª fala manual abriu a janela")
checar(bool(s.get("silencio_deliberado_ate")), "e escreveu `silencio_deliberado_ate`, que o Vigia já honra")
checar(GRUPO == [] and ENVIADAS == [],
       "🔴 (a) NADA SAI: nem ao grupo, nem ao destino de suporte, nem ao segurado",
       f"grupo={GRUPO} enviadas={ENVIADAS}")
checar(not D.humano_assumiu(s), "com UMA fala, ninguém assumiu — o robô só espera")
rodar(R.try_route_insurer_inbound(company_id=A, from_phone=URA, text=TELA,
                                  send_to_insurer=_para_ura, send_to_client=_para_cliente,
                                  human_reply_provider=_cerebro))
s = rodar(R.load_active_dispatch(A, URA))
checar(saidas_do_robo(s) == [], "🔴 com a janela aberta, a tela real do menu NÃO recebe tecla",
       str(saidas_do_robo(s)))
# o Cérebro, na fase humana, com tela pendente: também não redige.
s["state"] = "human_phase"
s["pending_insurer_messages"] = ["Qual o ponto de referência do local?"]
rodar(R.save_active_dispatch(A, URA, s))
rodar(R.try_route_insurer_inbound(company_id=A, from_phone=URA, text="Pode me confirmar o bairro, por favor?",
                                  send_to_insurer=_para_ura, send_to_client=_para_cliente,
                                  human_reply_provider=_cerebro))
s = rodar(R.load_active_dispatch(A, URA))
checar("CEREBRO_CHAMADO" not in ENVIADAS and saidas_do_robo(s) == [],
       "🔴 com a janela aberta, o Cérebro NÃO é chamado na fase humana", str(ENVIADAS))
envelhecer(s, 10)
checar(W.diagnose(s) is None, "🔴 10 s depois, o Vigia NÃO chama o Sentinela", str(W.diagnose(s)))
# (a) AOS 15 s, O ROBÔ VOLTA A LER A TELA ATUAL — o Vigia age no próximo ciclo.
s["pausa_humana"]["ate"] = s["silencio_deliberado_ate"] = (
    datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
s["transcript"].append({"direction": "in", "text": TELA, "at": datetime.now(timezone.utc).isoformat()})
envelhecer(s, 35)
checar(not D.pausa_humana_aberta(s) and W.diagnose(s) == "stall_unanswered",
       "🔴 (a) vencida a janela, o robô continua lendo a TELA ATUAL (o Vigia age)", str(W.diagnose(s)))
# CONTROLE: o eco da nossa própria voz não pausa nada.
REDIS.d.clear()
GRUPO.clear()
s2 = nova_sessao(A)
rodar(R.save_active_dispatch(A, URA, s2))
rodar(R.note_manual_outbound(A, URA, "1", foi_humano=False))
s2 = rodar(R.load_active_dispatch(A, URA))
s2["transcript"].append({"direction": "in", "text": TELA, "at": datetime.now(timezone.utc).isoformat()})
envelhecer(s2, 45)
checar(not D.pausa_humana_aberta(s2) and W.diagnose(s2) == "stall_unanswered" and not GRUPO,
       "🔴 CONTROLE: `foi_humano=False` não abre janela — o Vigia age e o grupo não ouve nada",
       f"pausa={D.pausa_humana_aberta(s2)} diag={W.diagnose(s2)} grupo={GRUPO}")
# CONTROLE (d): `PAUSA_HUMANA_S=0` desliga tudo — a janela E a assunção.
_s = D.PAUSA_HUMANA_S
D.PAUSA_HUMANA_S = 0
_desligada = nova_sessao(A)
_e1 = D.uma_fala_da_atendente(_desligada)
_e2 = D.uma_fala_da_atendente(_desligada)
D.PAUSA_HUMANA_S = _s
checar(_e1 == _e2 == "desligada" and not D.pausa_humana_aberta(_desligada)
       and not D.humano_assumiu(_desligada),
       "🔴 (d) CONTROLE: `PAUSA_HUMANA_S=0` desliga a janela E a assunção", f"{_e1} {_e2}")

print()
print("=" * 74)
print("[GC-2] A 2ª FALA DENTRO DA JANELA ASSUME — em silêncio, e o robô sai")
print("=" * 74)
REDIS.d.clear()
GRUPO.clear()
ENVIADAS.clear()
EVENTOS.clear()
s = nova_sessao(A)
rodar(R.save_active_dispatch(A, URA, s))
rodar(R.note_manual_outbound(A, URA, "1", foi_humano=True))
rodar(R.note_manual_outbound(A, URA, "vou eu mesma falar com eles", foi_humano=True))
s = rodar(R.load_active_dispatch(A, URA))
checar(D.humano_assumiu(s) and s["state"] == "needs_human" and s["reason"] == D.HUMANO_ASSUMIU,
       "🔴 (b) 2 falas em 15 s → `needs_human` / `HUMANO_ASSUMIU`", f"{s['state']}/{s.get('reason')}")
checar(GRUPO == [] and ENVIADAS == [] and saidas_do_robo(s) == [],
       "🔴 (b) EM SILÊNCIO: 0 envios ao grupo, ao suporte, ao segurado e à seguradora",
       f"grupo={GRUPO} enviadas={ENVIADAS} robo={saidas_do_robo(s)}")
checar(any(e["event_type"] == "pausa_humana.assumiu" for e in EVENTOS),
       "🔴 (b) e o rastro grava `pausa_humana.assumiu` em `work_events`",
       str([e["event_type"] for e in EVENTOS]))
checar(not REDIS.d.get(G._CHAVE_DA_PAUSA.format(empresa=A, alvo="conv-%s" % A)),
       "🔴 o índice da janela SAI quando ela assume (quem cala o grupo agora é `humano_assumiu`)")
checar(W.diagnose(s) is None, "🔴 (b) o Vigia fica calado (needs_human é terminal para ele)",
       str(W.diagnose(s)))
ENVIADAS.clear()
rodar(R.try_route_insurer_inbound(company_id=A, from_phone=URA, text=TELA,
                                  send_to_insurer=_para_ura, send_to_client=_para_cliente,
                                  human_reply_provider=_cerebro))
s = rodar(R.load_active_dispatch(A, URA))
checar(ENVIADAS == [] and GRUPO == [] and saidas_do_robo(s) == [],
       "🔴 (b) depois disso nada sai: nem tecla, nem Cérebro, nem dossiê, nem aviso",
       f"{ENVIADAS} {GRUPO} {saidas_do_robo(s)}")
checar(not D.motivo_reentravel(s["reason"]),
       "🔴 e o robô NÃO retoma sozinho: uma pessoa da seguradora não reabre")
checar(not D.pode_retomar({**nova_sessao(A), "state": "needs_human", "reason": "insurer_closed",
                           "pausa_humana": {"ate": (datetime.now(timezone.utc)
                                                    + timedelta(seconds=30)).isoformat()}}),
       "🔴 com a janela aberta, a retomada automática NÃO reabre o acionamento por cima dela")
# (c) A 2ª FALA **DEPOIS** DOS 15 s É UMA NOVA 1ª FALA — o PAR do (b).
REDIS.d.clear()
GRUPO.clear()
ENVIADAS.clear()
s = nova_sessao(A)
rodar(R.save_active_dispatch(A, URA, s))
rodar(R.note_manual_outbound(A, URA, "1", foi_humano=True))
s = rodar(R.load_active_dispatch(A, URA))
_primeira = s["pausa_humana"]["ate"]
s["pausa_humana"]["ate"] = s["silencio_deliberado_ate"] = (
    datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
rodar(R.save_active_dispatch(A, URA, s))
rodar(R.note_manual_outbound(A, URA, "2", foi_humano=True))
s = rodar(R.load_active_dispatch(A, URA))
checar(not D.humano_assumiu(s) and D.pausa_humana_aberta(s)
       and s["pausa_humana"]["ate"] != _primeira and int(s.get("pausas_humanas") or 0) == 2,
       "🔴 (c) a 2ª fala DEPOIS dos 15 s é uma janela NOVA, não uma assunção",
       f"assumiu={D.humano_assumiu(s)} aberta={D.pausa_humana_aberta(s)} n={s.get('pausas_humanas')}")
checar(GRUPO == [] and ENVIADAS == [], "🔴 (c) e também nessa janela nova nada sai")

print()
print("=" * 74)
print("[GC-2b] A CORRIDA: ela entra enquanto o Cérebro do Sentinela pensa")
print("=" * 74)
REDIS.d.clear()
velha = nova_sessao(A)
velha["transcript"].append({"direction": "in", "text": TELA,
                            "at": (datetime.now(timezone.utc) - timedelta(seconds=40)).isoformat()})
rodar(R.save_active_dispatch(A, URA, velha))
velha = rodar(R.load_active_dispatch(A, URA))          # o Vigia leu ANTES


async def _cerebro_lento(company_id, session, texto):
    # enquanto "pensa", a atendente fala com a seguradora
    await R.note_manual_outbound(A, URA, "1", foi_humano=True)
    return "1"


W._adaptive_reply = _cerebro_lento
ENVIOS_WA = []


class _WaVigia:
    def send_message(self, fone, texto, integ=None, **k):
        ENVIOS_WA.append(texto)


acao = rodar(W._sentinela_recover(A, URA, velha, _WaVigia(), {"id": "canal"}))
checar(acao == "pausa_humana" and ENVIOS_WA == [],
       "🔴 o Sentinela relê a sessão e NÃO envia por cima dela", f"{acao} {ENVIOS_WA}")
checar(D.pausa_humana_aberta(velha) and int(velha.get("sentinela_attempts") or 0) == 0,
       "a cópia do Vigia herda a janela (a gravação não a apaga) e a tentativa não é gasta")
# 🔴 E O MESMO COM A ASSUNÇÃO — o leitor de `humano_assumiu` no Vigia. Sem esta
#    linha, o guarda ficava VERDE com o Vigia ignorando quem assumiu (mutação M4).
REDIS.d.clear()
velha2 = nova_sessao(A)
velha2["transcript"].append({"direction": "in", "text": TELA,
                             "at": (datetime.now(timezone.utc) - timedelta(seconds=40)).isoformat()})
rodar(R.save_active_dispatch(A, URA, velha2))
velha2 = rodar(R.load_active_dispatch(A, URA))          # o Vigia leu ANTES


async def _cerebro_lento_que_assume(company_id, session, texto):
    await R.note_manual_outbound(A, URA, "1", foi_humano=True)
    await R.note_manual_outbound(A, URA, "deixa comigo", foi_humano=True)   # a 2ª: assumiu
    return "1"


W._adaptive_reply = _cerebro_lento_que_assume
ENVIOS_WA.clear()
acao2 = rodar(W._sentinela_recover(A, URA, velha2, _WaVigia(), {"id": "canal"}))
checar(acao2 == "pausa_humana" and ENVIOS_WA == [] and D.humano_assumiu(velha2)
       and velha2.get("silencio_deliberado_ate") is None,
       "🔴 ela ASSUMIU enquanto o Cérebro pensava: o Sentinela NÃO envia e a cópia "
       "dele fica com `needs_human`/`humano_assumiu`", f"{acao2} {ENVIOS_WA} {velha2.get('state')}")

print()
print("=" * 74)
print("[GC-2c] A CORRIDA NO ROTEADOR (juiz fresco, B1): ela entra enquanto o Cérebro redige")
print("=" * 74)
_guarda_real = R.guard_human_phase_reply
R.guard_human_phase_reply = lambda reply, session, insurer_message=None: {"ok": True, "reply": reply}


async def _cerebro_com_corrida(sessao, tela):
    await R.note_manual_outbound(A, URA, "Centro", foi_humano=True)
    return "Centro"


async def _cerebro_sem_corrida(sessao, tela):
    return "Centro"


for provider, rotulo in ((_cerebro_sem_corrida, "controle"), (_cerebro_com_corrida, "corrida")):
    REDIS.d.clear()
    s = nova_sessao(A)
    s.update({"state": "human_phase", "pending_insurer_messages": ["Qual o bairro?"]})
    rodar(R.save_active_dispatch(A, URA, s))
    rodar(R.try_route_insurer_inbound(company_id=A, from_phone=URA, text="Pode confirmar o bairro?",
                                      send_to_insurer=_para_ura, send_to_client=_para_cliente,
                                      human_reply_provider=provider))
    s = rodar(R.load_active_dispatch(A, URA))
    if rotulo == "controle":
        checar(saidas_do_robo(s) == ["Centro"], "🔴 CONTROLE: sem ela, o Cérebro responde a tela",
               str(saidas_do_robo(s)))
    else:
        checar(saidas_do_robo(s) == [] and D.pausa_humana_aberta(s),
               "🔴 com ela entrando no meio, nada nosso sai e a janela fica gravada", str(saidas_do_robo(s)))
        checar(any(t.get("manual") for t in s["transcript"])
               and any(t.get("text") == "Pode confirmar o bairro?" for t in s["transcript"]),
               "a fala dela E a tela deste turno ficam no registro")
        _ordem = [(t.get("direction"), bool(t.get("manual"))) for t in s["transcript"][-2:]]
        checar(_ordem == [("in", False), ("out", True)] and D.tela_respondida(s) == ""
               and not any("_deste_turno" in t for t in s["transcript"]),
               "🔴 e na ORDEM certa — tela, depois a fala dela: o Sentinela não a responde de novo "
               "(confirmação pós-conserto)", str(_ordem))
        s["pausa_humana"]["ate"] = s["silencio_deliberado_ate"] = (
            datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        s["transcript"][-1]["at"] = (datetime.now(timezone.utc) - timedelta(seconds=40)).isoformat()
        checar(W.diagnose(s) != "stall_unanswered",
               "vencida a janela, o Vigia NÃO vê a tela que ela respondeu como pendente", str(W.diagnose(s)))
R.guard_human_phase_reply = _guarda_real

print()
print("=" * 74)
print("[GC-3] COM A JANELA ABERTA, O GRUPO CALA — pela guarda ÚNICA, em todo ponto de envio")
print("=" * 74)
aberta = nova_sessao(A)
D.uma_fala_da_atendente(aberta)
for tipo in (G.TIPO_PEDIDO_DE_AJUDA, G.TIPO_VIGIA, G.TIPO_RETOMADA, G.TIPO_ESPERA_VENCIDA):
    pode, porque = rodar(G.o_grupo_pode_saber(None, company_id=A, tipo=tipo, sessao=aberta))
    checar(not pode and porque == G.MOTIVO_PAUSA_HUMANA, f"`{tipo}` cala com a janela aberta", porque)
pode, _ = rodar(G.o_grupo_pode_saber(None, company_id=A, tipo=G.TIPO_SINISTRO, sessao=aberta))
checar(pode, "sinistro continua isento (a regra da 001.3 não muda)")
# a espera.vencida não tem a sessão: o índice por telefone a cala.
REDIS.d.clear()
rodar(G.marcar_pausa_humana(A, G.alvos_da_pausa("conv-a", "5548988887777"), 60))
pode, _ = rodar(G.o_grupo_pode_saber(None, company_id=A, tipo=G.TIPO_ESPERA_VENCIDA,
                                     telefone="48 98888-7777"))
checar(not pode, "a `espera.vencida` (só com o telefone, noutra forma) cala pelo índice")
# 🔴 CONTROLE: janela FECHADA não cala nada.
D.fechar_pausa(aberta, "assumiu")
pode, _ = rodar(G.o_grupo_pode_saber(None, company_id=A, tipo=G.TIPO_PEDIDO_DE_AJUDA, sessao=aberta))
checar(pode, "🔴 CONTROLE: com a janela fechada, o pedido de ajuda passa")
# todo ponto de envio do acionamento entrega a SESSÃO à guarda (AST — o guarda diz qual).
sem_sessao = []
for arq in ("app/services/dispatch_router.py", "app/tasks/dispatch_watchdog.py"):
    arvore = ast.parse(open(os.path.join(RAIZ, arq), encoding="utf-8").read())
    for no in ast.walk(arvore):
        if (isinstance(no, ast.Call) and getattr(no.func, "id", getattr(no.func, "attr", "")) == "enviar_ao_grupo"
                and not any(k.arg == "sessao" for k in no.keywords)):
            sem_sessao.append(f"{arq}:{no.lineno}")
checar(not sem_sessao, "🔴 todo `enviar_ao_grupo` do acionamento passa `sessao=`", str(sem_sessao))
# 🔴 E O AVISO DA PAUSA NÃO VOLTA PELA PORTA DOS FUNDOS: nenhum ponto do produto
#    manda `tipo=TIPO_PAUSA_HUMANA` ao grupo.
manda_pausa = []
for arq in ("app/services/dispatch_router.py", "app/tasks/dispatch_watchdog.py",
            "app/api/webhook.py"):
    arvore = ast.parse(open(os.path.join(RAIZ, arq), encoding="utf-8").read())
    for no in ast.walk(arvore):
        if isinstance(no, ast.Call) and getattr(no.func, "id", getattr(no.func, "attr", "")) == "enviar_ao_grupo":
            for k in no.keywords:
                if k.arg == "tipo" and "PAUSA_HUMANA" in ast.dump(k.value):
                    manda_pausa.append(f"{arq}:{no.lineno}")
checar(not manda_pausa,
       "🔴 NENHUM ponto do produto manda um aviso de pausa ao grupo", str(manda_pausa))

print()
print("=" * 74)
print("[GC-3b] O ATALHO OPCIONAL continua funcionando — e ninguém precisa dele")
print("=" * 74)
checar(R.palavra_da_equipe("EU CUIDO!") == "eu cuido" and R.palavra_da_equipe(" agente ") == "agente",
       "as duas palavras são lidas com pontuação e caixa")
checar(R.palavra_da_equipe("Responda AGENTE para eu seguir, ou EU CUIDO para eu sair") is None,
       "🔴 a LIÇÃO MIGRA (§9.3): uma frase que CONTÉM as duas palavras não é comando "
       "— o aviso que as citava morreu, o `in` que o barrava não")
REDIS.d.clear()
s = nova_sessao(A)
rodar(R.save_active_dispatch(A, URA, s))
rodar(R.note_manual_outbound(A, URA, "1", foi_humano=True))
checar(rodar(R.ler_palavra_da_equipe(A, "AGENTE", remetente="5548911112222")) is None,
       "quem não é da equipe não comanda o acionamento")
checar(rodar(R.ler_palavra_da_equipe(A, "AGENTE", chat="120363000000000000@g.us", eh_grupo=True)) == "agente",
       "AGENTE no grupo de suporte é aplicada")
s = rodar(R.load_active_dispatch(A, URA))
checar(not D.pausa_humana_aberta(s) and s.get("silencio_deliberado_ate") is None,
       "AGENTE fecha a janela na hora")
rodar(R.note_manual_outbound(A, URA, "2", foi_humano=True))
checar(rodar(R.ler_palavra_da_equipe(A, "eu cuido", remetente="48 90000-0001")) == "eu_cuido",
       "EU CUIDO de um número da casa, no privado, é aplicada")
s = rodar(R.load_active_dispatch(A, URA))
checar(s["state"] == "needs_human" and s["reason"] == D.HUMANO_ASSUMIU,
       "EU CUIDO faz o MESMO que a 2ª fala: needs_human/humano_assumiu")
checar(rodar(R.ler_palavra_da_equipe(A, "agente", remetente="5548900000001")) == "agente"
       and rodar(R.load_active_dispatch(A, URA))["state"] == "ura",
       "AGENTE devolve ao robô um acionamento assumido")
# travada antes, travada depois — COM o motivo (juiz fresco, P7)
REDIS.d.clear()
s = nova_sessao(A)
s.update({"state": "needs_human", "reason": "sentinela_stall"})
rodar(R.save_active_dispatch(A, URA, s))
rodar(R.note_manual_outbound(A, URA, "1", foi_humano=True))
rodar(R.note_manual_outbound(A, URA, "2", foi_humano=True))   # a 2ª fala assume
s = rodar(R.load_active_dispatch(A, URA))
checar(D.humano_assumiu(s), "a 2ª fala assume mesmo uma sessão JÁ travada")
rodar(R.ler_palavra_da_equipe(A, "AGENTE", remetente="5548900000001"))
s = rodar(R.load_active_dispatch(A, URA))
checar(s["state"] == "needs_human" and s.get("reason") == "sentinela_stall",
       "AGENTE devolve a sessão travada com o MOTIVO dela (reentrável de novo)",
       f"{s['state']} {s.get('reason')}")

print()
print("=" * 74)
print("[GC-3c] 🔴 O DOSSIÊ DO ROTEADOR VOLTA A SAIR (o import que faltava desde 16/09)")
print("=" * 74)
REDIS.d.clear()
GRUPO.clear()
s = nova_sessao(B)
s.update({"state": "needs_human", "reason": "sentinela_stall", "retry_count": 1})
rodar(R.save_active_dispatch(B, URA, s))
try:
    rodar(R.try_route_insurer_inbound(company_id=B, from_phone=URA, text="Olá, tudo bem?",
                                      send_to_insurer=_para_ura, send_to_client=_para_cliente))
    erro = ""
except Exception as e:  # noqa: BLE001
    erro = f"{type(e).__name__}: {e}"
s = rodar(R.load_active_dispatch(B, URA))
checar(not erro and [g["tipo"] for g in GRUPO] == [G.TIPO_PEDIDO_DE_AJUDA] and s.get("dossier_sent"),
       "needs_human sem janela: o pedido de ajuda chega à porta única e o dossiê é marcado", erro or str(GRUPO))

print()
print("=" * 74)
print("[GT] DUAS CORRETORAS, MESMA SEGURADORA, MESMA TELA — nada atravessa (CLAUDE.md §7)")
print("=" * 74)
REDIS.d.clear()
GRUPO.clear()
sa, sb = nova_sessao(A), nova_sessao(B)
sa["mirror_conversation_id"] = sb["mirror_conversation_id"] = "conv-igual"
rodar(R.save_active_dispatch(A, URA, sa))
rodar(R.save_active_dispatch(B, URA, sb))
rodar(R.note_manual_outbound(A, URA, "1", foi_humano=True))
sa, sb = rodar(R.load_active_dispatch(A, URA)), rodar(R.load_active_dispatch(B, URA))
checar(D.pausa_humana_aberta(sa) and not D.pausa_humana_aberta(sb), "a janela de A não existe em B")
rodar(R.try_route_insurer_inbound(company_id=B, from_phone=URA, text=TELA, send_to_insurer=_para_ura,
                                  send_to_client=_para_cliente))
checar(saidas_do_robo(rodar(R.load_active_dispatch(B, URA))) == ["1"],
       "🔴 CONTROLE: B, sem janela, responde a MESMA tela com a tecla do ramo (\"1\")",
       str(saidas_do_robo(rodar(R.load_active_dispatch(B, URA)))))
pode, _ = rodar(G.o_grupo_pode_saber(None, company_id=B, tipo=G.TIPO_PEDIDO_DE_AJUDA,
                                     conversation_id="conv-igual", telefone="5548988887777", sessao=sb))
checar(pode, "o índice da janela de A (mesma conversa, mesmo telefone) NÃO cala o grupo de B")
rodar(R.note_manual_outbound(A, URA, "2", foi_humano=True))     # A assume
sa, sb = rodar(R.load_active_dispatch(A, URA)), rodar(R.load_active_dispatch(B, URA))
checar(D.humano_assumiu(sa) and not D.humano_assumiu(sb),
       "🔴 a ASSUNÇÃO de A não assume o acionamento de B")
checar("pausa_humana" not in sb and sb.get("state") != "needs_human",
       "nada da sessão de A aparece na de B")

print()
print("=" * 74)
print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
print("=" * 74)
sys.exit(1 if FAIL else 0)
