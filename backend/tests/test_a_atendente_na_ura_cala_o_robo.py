# -*- coding: utf-8 -*-
"""🔴 GC-1 + GC-2 + GC-3 + GT (SPEC-EXTRA-001.4 C) · A ATENDENTE NA URA CALA O ROBÔ.

📊 10/09/2026, sessão Allianz `432614de`: às 17:18:12 a atendente da corretora
digitou "1" à mão na conversa com a URA; às 17:18:14 e :16 o corredor digitou de
novo. `note_manual_outbound` fazia três escritas e NENHUM bloqueio.

GC-1  a fala dela abre a pausa: o motor não responde, o Cérebro não redige, o Vigia
      não chama o Sentinela — e o eco da nossa voz (`foi_humano=False`) NÃO pausa.
GC-2  a pausa tem teto (D-PILOTO-10: 2 renovações); vencida, o corredor retoma.
GC-3  com a pausa aberta, todo aviso ao grupo do acionamento cala na guarda ÚNICA
      (`o_grupo_pode_saber`, da 001.3) — e todo ponto de envio passa a sessão.
      AGENTE retoma; EU CUIDO tira o agente do acionamento, e nada mais sai.
GT    duas corretoras, mesma seguradora, mesma tela: a pausa de uma não cala a outra.

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


async def _sem_banco():
    return None


import app.core.redis as _core_redis  # noqa: E402

_core_redis.get_async_redis_client = _redis_falso
R._redis = _redis_falso
R._db = _sem_banco
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
    s.update({"state": "ura", "client_phone": "5548988887777",
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
print("[GC-1] A FALA DA ATENDENTE ABRE A PAUSA — e o eco da nossa voz não")
print("=" * 74)
checar(bool(TELA), "📊 a tela real do menu 'Qual seguro' está no corpus")
REDIS.d.clear()
s = nova_sessao(A)
rodar(R.save_active_dispatch(A, URA, s))
rodar(R.note_manual_outbound(A, URA, "1", foi_humano=True))
s = rodar(R.load_active_dispatch(A, URA))
checar(D.pausa_humana_aberta(s), "note_manual_outbound(foi_humano=True) abriu a pausa")
checar(bool(s.get("silencio_deliberado_ate")), "e escreveu `silencio_deliberado_ate`, que o Vigia já honra")
checar([g["tipo"] for g in GRUPO] == [G.TIPO_PAUSA_HUMANA] and GRUPO[0]["pode"],
       "o grupo recebeu UM aviso — o da pausa, o único que passa por ela", str(GRUPO))
checar("AGENTE" in GRUPO[0]["texto"] and "EU CUIDO" in GRUPO[0]["texto"]
       and "60 segundos" in GRUPO[0]["texto"], "o aviso diz 60 s, AGENTE e EU CUIDO")
ENVIADAS.clear()
rodar(R.try_route_insurer_inbound(company_id=A, from_phone=URA, text=TELA,
                                  send_to_insurer=_para_ura, send_to_client=_para_cliente,
                                  human_reply_provider=_cerebro))
s = rodar(R.load_active_dispatch(A, URA))
checar(saidas_do_robo(s) == [], "🔴 com a pausa aberta, a tela real do menu NÃO recebe tecla",
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
       "🔴 com a pausa aberta, o Cérebro NÃO é chamado na fase humana", str(ENVIADAS))
envelhecer(s, 45)
checar(W.diagnose(s) is None, "🔴 45 s depois, o Vigia NÃO chama o Sentinela (hoje: 30 s)",
       str(W.diagnose(s)))
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
       "🔴 CONTROLE: `foi_humano=False` não abre pausa — o Vigia age em 45 s e o grupo não ouve nada",
       f"pausa={D.pausa_humana_aberta(s2)} diag={W.diagnose(s2)} grupo={GRUPO}")

print()
print("=" * 74)
print("[GC-2] A PAUSA TEM TETO: 2 renovações (D-PILOTO-10); vencida, o corredor retoma")
print("=" * 74)
REDIS.d.clear()
GRUPO.clear()
s = nova_sessao(A)
rodar(R.save_active_dispatch(A, URA, s))
eventos = []
for _ in range(4):
    s = rodar(R.load_active_dispatch(A, URA))
    antes = dict(s.get("pausa_humana") or {})
    rodar(R.note_manual_outbound(A, URA, "texto dela", foi_humano=True))
    depois = rodar(R.load_active_dispatch(A, URA))["pausa_humana"]
    eventos.append((depois.get("renovacoes"), depois.get("ate") != antes.get("ate"),
                    bool(depois.get("esgotada_em"))))
checar([e[0] for e in eventos] == [0, 1, 2, 2], "abre · renova · renova · e a 4ª fala NÃO renova",
       str(eventos))
checar(eventos[3][1] is False and eventos[3][2], "a 4ª fala não mexe no prazo e marca `esgotada_em`",
       str(eventos[3]))
checar(len(GRUPO) == 1, "o grupo ouviu UMA vez em toda a pausa", str(len(GRUPO)))
s = rodar(R.load_active_dispatch(A, URA))
checar(s.get("silencio_deliberado_ate") == s["pausa_humana"]["ate"],
       "🔴 a RENOVAÇÃO também move o silêncio que o Vigia lê", f"{s.get('silencio_deliberado_ate')} × {s['pausa_humana']['ate']}")
_velho = dict(s, silencio_deliberado_ate=(datetime.now(timezone.utc) - timedelta(seconds=5)).isoformat())
_velho["transcript"] = s["transcript"] + [{"direction": "in", "text": TELA,
                                           "at": (datetime.now(timezone.utc) - timedelta(seconds=45)).isoformat()}]
checar(W.diagnose(_velho) is None, "🔴 e o Vigia respeita a PAUSA mesmo com o silêncio vencido (duas defesas)",
       str(W.diagnose(_velho)))
s["pausa_humana"]["ate"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
s["silencio_deliberado_ate"] = s["pausa_humana"]["ate"]
s["transcript"].append({"direction": "in", "text": TELA, "at": datetime.now(timezone.utc).isoformat()})
envelhecer(s, 35)
checar(not D.pausa_humana_aberta(s) and W.diagnose(s) == "stall_unanswered",
       "vencida a pausa, o corredor retoma lendo a tela atual (o Vigia age)", str(W.diagnose(s)))
checar(not D.pode_retomar({**s, "state": "needs_human", "reason": "insurer_closed",
                           "pausa_humana": {"ate": (datetime.now(timezone.utc) + timedelta(seconds=30)).isoformat()}}),
       "🔴 com a pausa aberta, a retomada automática NÃO reabre o acionamento por cima dela")

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
       "a cópia do Vigia herda a pausa (a gravação não a apaga) e a tentativa não é gasta")

print()
print("=" * 74)
print("[GC-3] COM A PAUSA ABERTA, O GRUPO CALA — pela guarda ÚNICA, em todo ponto de envio")
print("=" * 74)
aberta = nova_sessao(A)
D.abrir_ou_renovar_pausa(aberta)
for tipo in (G.TIPO_PEDIDO_DE_AJUDA, G.TIPO_VIGIA, G.TIPO_RETOMADA, G.TIPO_ESPERA_VENCIDA):
    pode, porque = rodar(G.o_grupo_pode_saber(None, company_id=A, tipo=tipo, sessao=aberta))
    checar(not pode and porque == G.MOTIVO_PAUSA_HUMANA, f"`{tipo}` cala com a pausa aberta", porque)
pode, _ = rodar(G.o_grupo_pode_saber(None, company_id=A, tipo=G.TIPO_PAUSA_HUMANA, sessao=aberta))
checar(pode, "o aviso DA PRÓPRIA pausa passa")
pode, _ = rodar(G.o_grupo_pode_saber(None, company_id=A, tipo=G.TIPO_SINISTRO, sessao=aberta))
checar(pode, "sinistro continua isento (a regra da 001.3 não muda)")
# a espera.vencida não tem a sessão: o índice por telefone a cala.
REDIS.d.clear()
rodar(G.marcar_pausa_humana(A, G.alvos_da_pausa("conv-a", "5548988887777"), 60))
pode, _ = rodar(G.o_grupo_pode_saber(None, company_id=A, tipo=G.TIPO_ESPERA_VENCIDA,
                                     telefone="48 98888-7777"))
checar(not pode, "a `espera.vencida` (só com o telefone, noutra forma) cala pelo índice")
# 🔴 CONTROLE: pausa FECHADA não cala nada.
D.fechar_pausa(aberta, "agente")
pode, _ = rodar(G.o_grupo_pode_saber(None, company_id=A, tipo=G.TIPO_PEDIDO_DE_AJUDA, sessao=aberta))
checar(pode, "🔴 CONTROLE: com a pausa fechada, o pedido de ajuda passa")
# todo ponto de envio do acionamento entrega a SESSÃO à guarda (AST — o guarda diz qual).
sem_sessao = []
for arq in ("app/services/dispatch_router.py", "app/tasks/dispatch_watchdog.py"):
    arvore = ast.parse(open(os.path.join(RAIZ, arq), encoding="utf-8").read())
    for no in ast.walk(arvore):
        if (isinstance(no, ast.Call) and getattr(no.func, "id", getattr(no.func, "attr", "")) == "enviar_ao_grupo"
                and not any(k.arg == "sessao" for k in no.keywords)):
            sem_sessao.append(f"{arq}:{no.lineno}")
checar(not sem_sessao, "🔴 todo `enviar_ao_grupo` do acionamento passa `sessao=`", str(sem_sessao))

print()
print("=" * 74)
print("[GC-3b] AGENTE retoma · EU CUIDO tira o agente — e nada mais sai")
print("=" * 74)
checar(R.palavra_da_equipe("EU CUIDO!") == "eu cuido" and R.palavra_da_equipe(" agente ") == "agente",
       "as duas palavras são lidas com pontuação e caixa")
checar(R.palavra_da_equipe(R.aviso_da_pausa_humana(nova_sessao(A), 60)) is None,
       "🔴 o próprio aviso (que CONTÉM as duas palavras) não é lido como resposta")
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
       "AGENTE fecha a pausa na hora")
rodar(R.note_manual_outbound(A, URA, "2", foi_humano=True))
checar(rodar(R.ler_palavra_da_equipe(A, "eu cuido", remetente="48 90000-0001")) == "eu_cuido",
       "EU CUIDO de um número da casa, no privado, é aplicada")
s = rodar(R.load_active_dispatch(A, URA))
checar(s["state"] == "needs_human" and s["reason"] == D.HUMANO_ASSUMIU, "EU CUIDO → needs_human/humano_assumiu")
ENVIADAS.clear()
GRUPO.clear()
rodar(R.try_route_insurer_inbound(company_id=A, from_phone=URA, text=TELA,
                                  send_to_insurer=_para_ura, send_to_client=_para_cliente,
                                  human_reply_provider=_cerebro))
rodar(R.try_route_insurer_inbound(company_id=A, from_phone=URA,
                                  text="Olá, meu nome é Fulana e darei continuidade em seu atendimento",
                                  send_to_insurer=_para_ura, send_to_client=_para_cliente,
                                  human_reply_provider=_cerebro))
s = rodar(R.load_active_dispatch(A, URA))
checar(ENVIADAS == [] and GRUPO == [] and saidas_do_robo(s) == [],
       "🔴 depois do EU CUIDO nada sai: nem tecla, nem Cérebro, nem dossiê, nem aviso",
       f"{ENVIADAS} {GRUPO} {saidas_do_robo(s)}")
checar(s["state"] == "needs_human" and not D.motivo_reentravel(s["reason"]),
       "🔴 e EU CUIDO NÃO é reentrável: uma pessoa da seguradora não reabre", s["state"])
checar(W.diagnose(s) is None, "o Vigia também não age (needs_human é terminal para ele)")
checar(rodar(R.ler_palavra_da_equipe(A, "agente", remetente="5548900000001")) == "agente"
       and rodar(R.load_active_dispatch(A, URA))["state"] == "ura",
       "AGENTE depois de EU CUIDO devolve o acionamento ao agente")

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
       "needs_human sem pausa: o pedido de ajuda chega à porta única e o dossiê é marcado", erro or str(GRUPO))

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
checar(D.pausa_humana_aberta(sa) and not D.pausa_humana_aberta(sb), "a pausa de A não existe em B")
rodar(R.try_route_insurer_inbound(company_id=B, from_phone=URA, text=TELA, send_to_insurer=_para_ura,
                                  send_to_client=_para_cliente))
checar(saidas_do_robo(rodar(R.load_active_dispatch(B, URA))) == ["1"],
       "🔴 CONTROLE: B, sem pausa, responde a MESMA tela com a tecla do ramo (\"1\")",
       str(saidas_do_robo(rodar(R.load_active_dispatch(B, URA)))))
pode, _ = rodar(G.o_grupo_pode_saber(None, company_id=B, tipo=G.TIPO_PEDIDO_DE_AJUDA,
                                     conversation_id="conv-igual", telefone="5548988887777", sessao=sb))
checar(pode, "o índice da pausa de A (mesma conversa, mesmo telefone) NÃO cala o grupo de B")
checar(rodar(R.ler_palavra_da_equipe(B, "EU CUIDO", remetente="5548900000001")) is None
       and rodar(R.load_active_dispatch(A, URA))["state"] == "ura",
       "EU CUIDO em B não encontra a pausa de A e não mexe nela")
sb = rodar(R.load_active_dispatch(B, URA))
checar("pausa_humana" not in sb and not sb.get("menu_pendente", {}).get("nossa_resposta") == "texto dela",
       "nada da sessão de A aparece na de B")

print()
print("=" * 74)
print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
print("=" * 74)
sys.exit(1 if FAIL else 0)
