# -*- coding: utf-8 -*-
"""O grupo de suporte recebe UM aviso por conversa — nao um por mensagem.

O DEFEITO, MEDIDO
=================
📊 Ate 18/08/2026 `HumanHandoffTool` NUNCA rodava: o executor a mandava para
`_run`, que estourava. Consertado o despacho (`exige_async`), ela passou a
rodar -- e a rodar em TODA chamada. `_arun` marcava a conversa e chamava
`_avisar_suporte` sem nunca perguntar se aquela conversa JA estava com a
equipe.

Resultado: cada nova mensagem do cliente numa conversa ja transferida virava
um WhatsApp novo no grupo. 📊 Em 19/08 havia 5 conversas em `HUMAN_REQUESTED`,
4 delas criadas depois do conserto -- e o Founder relatou "varias e varias
msgs" de ATENDIMENTO PRECISA DE VOCE sem entender o motivo.

O QUE ESTE GUARDA PROVA
=======================
1. o primeiro pedido AVISA
2. o segundo pedido na MESMA conversa ja transferida NAO avisa
3. uma conversa que VOLTOU da equipe volta a avisar (a trava nao vira mordaca)
4. aviso que FALHOU devolve a reserva (o Vigia nao fica mudo)
5. o estado novo carrega HANDOFF_OK -- senao a atendente seria proibida de
   dizer ao cliente uma coisa que e verdade
6. o estado novo PROIBE dizer "acabei de encaminhar" -- porque nao foi agora
7. o marcador e UM SO: a ferramenta e o Vigia usam a mesma chave

🔴 CONTROLE em cada bloco: antes de afirmar que a trava PRENDE, o teste prova
que ela DEIXA PASSAR no caso legitimo. Guarda que so sabe dizer "nao" nao
guarda -- emudece.
"""
from __future__ import annotations

import asyncio
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# O console do Windows e cp1252 e nao imprime emoji. Sem isto o teste morre no
# `print`, e um teste que morre imprimindo e um teste que ninguem roda.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 🔴 Os `__init__.py` de `app.agents` e `app.services` importam o mundo
# (langgraph, o grafo inteiro, todos os services). Nada disso e necessario
# para provar uma trava de repeticao, e exigi-lo tornaria este guarda
# impossivel de rodar fora do contêiner -- ou seja, nao rodaria nunca.
#
# Registrar pacotes VAZIOS com `__path__` deixa os submodulos carregarem por
# arquivo, um a um, sem executar o `__init__`. E o mesmo truque que
# `test_a_atendente_nao_mente_sobre_transferir.py` ja usa.
_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _pkg in ("app", "app.agents", "app.agents.tools", "app.core",
             "app.services", "app.tasks"):
    if _pkg not in sys.modules:
        _m = types.ModuleType(_pkg)
        _m.__path__ = [os.path.join(_RAIZ, *_pkg.split("."))]
        sys.modules[_pkg] = _m

OK = 0
FAIL = 0


def certo(condicao, rotulo):
    global OK, FAIL
    if condicao:
        OK += 1
        print(f"  ok   {rotulo}")
    else:
        FAIL += 1
        print(f"  FALHA {rotulo}")


# ===========================================================================
# Um Redis de mentira, com a semantica que importa: SET NX + TTL + DELETE.
#
# 🔴 Ele precisa MESMO implementar o `nx`. Um dublê que sempre grava faria o
# teste 2 passar pelo motivo errado -- a trava "funcionaria" porque o dublê
# mente, nao porque o codigo trava.
# ===========================================================================
class RedisDeMentira:
    def __init__(self):
        self.chaves = {}
        self.mortes = 0

    async def set(self, chave, valor, ex=None, nx=False):
        if nx and chave in self.chaves:
            return None          # ja existe: NAO gravou
        self.chaves[chave] = (valor, ex)
        return True

    async def delete(self, chave):
        self.chaves.pop(chave, None)
        self.mortes += 1


class RedisMorto:
    async def set(self, *a, **k):
        raise ConnectionError("redis fora do ar")

    async def delete(self, *a, **k):
        raise ConnectionError("redis fora do ar")


def com_redis(fake):
    """Instala um `app.core.redis` de mentira em `sys.modules`.

    O modulo real faz `import redis` no topo, e a biblioteca nao esta neste
    interpretador. O codigo sob teste importa `get_async_redis_client` DENTRO
    das funcoes (import tardio), entao substituir o modulo inteiro aqui e
    suficiente e nao exige o pacote.
    """
    mod = types.ModuleType("app.core.redis")

    async def _get():
        return fake

    mod.get_async_redis_client = _get
    sys.modules["app.core.redis"] = mod
    return mod


# ===========================================================================
# Um Supabase de mentira. Guarda o status e conta os UPDATEs.
# ===========================================================================
class TabelaFake:
    def __init__(self, banco, nome):
        self.banco, self.nome = banco, nome
        self._filtros, self._modo, self._dados = {}, None, None

    def select(self, *a):
        self._modo = "select"
        return self

    def update(self, dados):
        self._modo, self._dados = "update", dados
        return self

    def eq(self, campo, valor):
        self._filtros[campo] = valor
        return self

    def limit(self, n):
        return self

    def order(self, *a, **k):
        return self

    def execute(self):
        class R:
            pass
        r = R()
        linha = self.banco.linha
        bate = all(str(linha.get(c)) == str(v) for c, v in self._filtros.items())
        if not bate:
            r.data = []
            return r
        if self._modo == "update":
            self.banco.updates += 1
            linha.update(self._dados)
        r.data = [dict(linha)]
        return r


class SupabaseFake:
    def __init__(self, status="open"):
        self.linha = {"id": "conv-1234-5678", "company_id": "emp-1",
                      "session_id": "ses-1", "status": status,
                      "user_name": "Fulano", "user_phone": "5548999999999"}
        self.updates = 0

    def table(self, nome):
        return TabelaFake(self, nome)


def rodar(coro):
    return asyncio.run(coro)


# ===========================================================================
print()
print("=" * 68)
print("  1-2. A TRAVA: primeiro avisa, segundo cala")
print("=" * 68)

from app.agents.honestidade_do_handoff import (  # noqa: E402
    JA_ESTAVA_COM_A_EQUIPE, SUCESSO_DO_HANDOFF, afirma_transferencia,
    guardar_a_verdade_do_handoff)
from app.agents.tools import human_handoff as hh  # noqa: E402


def ferramenta(banco, avisos):
    """A tool real, com `_avisar_suporte` trocado por um contador."""
    t = hh.HumanHandoffTool(banco)

    async def _falso_avisar(company_id, conversa, motivo):
        avisos.append((company_id, str(conversa.get("id")), motivo))
        return {"avisado": True, "motivo": ""}

    t._avisar_suporte = _falso_avisar
    return t


redis = RedisDeMentira()
com_redis(redis)

# --- CONTROLE: conversa NOVA (status 'open') tem de AVISAR ---------------
banco = SupabaseFake(status="open")
avisos = []
r1 = rodar(ferramenta(banco, avisos)._arun(reason="quero humano",
                                           session_id="ses-1", company_id="emp-1"))
certo(len(avisos) == 1, "CONTROLE: primeiro pedido AVISA o grupo")
certo(r1 == SUCESSO_DO_HANDOFF, "CONTROLE: primeiro pedido devolve SUCESSO")
certo(banco.linha["status"] == "HUMAN_REQUESTED", "a conversa foi marcada")

# --- o SEGUNDO pedido, mesma conversa, agora ja em HUMAN_REQUESTED -------
r2 = rodar(ferramenta(banco, avisos)._arun(reason="quero humano de novo",
                                           session_id="ses-1", company_id="emp-1"))
certo(len(avisos) == 1, "🔴 segundo pedido NAO avisa o grupo de novo")
certo(r2 == JA_ESTAVA_COM_A_EQUIPE, "segundo pedido devolve JA_ESTAVA_COM_A_EQUIPE")
certo(r2 != SUCESSO_DO_HANDOFF, "e NAO devolve o mesmo estado do primeiro")

# --- terceiro, quarto, quinto: continua calado ---------------------------
for _ in range(3):
    rodar(ferramenta(banco, avisos)._arun(reason="oi", session_id="ses-1",
                                          company_id="emp-1"))
certo(len(avisos) == 1, "cinco pedidos seguidos = UM aviso, nao cinco")

print()
print("=" * 68)
print("  3. A TRAVA NAO E MORDACA: conversa que voltou volta a avisar")
print("=" * 68)

# A equipe resolveu: o status saiu de HUMAN_REQUESTED. O marcador do Redis
# CONTINUA la (ainda dentro das 6h). Um pedido novo tem de avisar mesmo assim.
banco.linha["status"] = "open"
r3 = rodar(ferramenta(banco, avisos)._arun(reason="problema novo",
                                           session_id="ses-1", company_id="emp-1"))
certo(len(avisos) == 2, "🔴 conversa que voltou da equipe AVISA de novo")
certo(r3 == SUCESSO_DO_HANDOFF, "e devolve SUCESSO, nao o estado de repetido")
certo("handoff_realerta:conv-1234-5678" in redis.chaves,
      "CONTROLE: o marcador existia e ainda assim avisou "
      "(a decisao NAO e so o marcador)")

print()
print("=" * 68)
print("  4. AVISO QUE FALHOU DEVOLVE A RESERVA")
print("=" * 68)

redis2 = RedisDeMentira()
com_redis(redis2)
banco2 = SupabaseFake(status="open")


def ferramenta_que_falha(banco):
    t = hh.HumanHandoffTool(banco)

    async def _falha(company_id, conversa, motivo):
        return {"avisado": False, "motivo": "a corretora nao tem grupo"}

    t._avisar_suporte = _falha
    return t


rodar(ferramenta_que_falha(banco2)._arun(reason="x", session_id="ses-1",
                                         company_id="emp-1"))
certo("handoff_realerta:conv-1234-5678" not in redis2.chaves,
      "🔴 falha no envio DEVOLVE o marcador (o Vigia nao fica mudo)")
certo(redis2.mortes == 1, "e devolveu exatamente uma vez")

# CONTROLE: quando o aviso DA certo, a reserva FICA de pe.
redis3 = RedisDeMentira()
com_redis(redis3)
banco3 = SupabaseFake(status="open")
rodar(ferramenta(banco3, [])._arun(reason="x", session_id="ses-1", company_id="emp-1"))
certo("handoff_realerta:conv-1234-5678" in redis3.chaves,
      "CONTROLE: aviso que DEU certo mantem a reserva")
certo(redis3.mortes == 0, "e nao devolve nada")

print()
print("=" * 68)
print("  5-6. O ESTADO NOVO DIZ A VERDADE — nem de menos, nem de mais")
print("=" * 68)

certo("HANDOFF_OK" in JA_ESTAVA_COM_A_EQUIPE,
      "🔴 carrega HANDOFF_OK: a transferencia É verdade, so nao foi agora")


class ToolMsg:
    def __init__(self, name, content):
        self.name, self.content = name, content


# 🔴 A frase tem de ser uma que o detector CASA. A primeira versao deste teste
# usava "Seu caso está com a equipe e alguém entra em contato" -- que nao casa
# padrao nenhum, e por isso passava com ou sem carimbo. O controle abaixo pegou.
frase_ok = "Seu caso foi encaminhado para a equipe."
certo(afirma_transferencia(frase_ok),
      "CONTROLE ZERO: a frase de teste REALMENTE aciona o detector "
      "(senao os dois testes seguintes nao medem nada)")

saida = guardar_a_verdade_do_handoff(
    frase_ok, [ToolMsg("request_human_agent", JA_ESTAVA_COM_A_EQUIPE)])
certo(saida == frase_ok,
      "o fiscal DEIXA a frase passar quando o estado novo esta presente")

# CONTROLE: a mesma frase, SEM tool nenhuma, tem de ser reescrita.
saida_sem = guardar_a_verdade_do_handoff(frase_ok, [])
certo(saida_sem != frase_ok,
      "CONTROLE: a MESMA frase sem handoff confirmado É reescrita "
      "(logo o teste acima mediu o carimbo, nao a frase)")

certo("PROIBIDO" in JA_ESTAVA_COM_A_EQUIPE
      and "acabou de" in JA_ESTAVA_COM_A_EQUIPE,
      "o estado proibe dar a entender que encaminhou AGORA")

# A instrucao nao pode conter a propria frase proibida em primeira pessoa,
# senao o detector a reescreveria se ela vazasse (licao do FALHA_DO_HANDOFF).


certo(not afirma_transferencia(JA_ESTAVA_COM_A_EQUIPE),
      "🔴 o proprio texto do estado NAO casa o detector "
      "(escrito para nao se auto-reescrever)")
certo(afirma_transferencia("acabei de encaminhar seu caso"),
      "CONTROLE: o detector CONSEGUE casar — ele nao esta cego")

print()
print("=" * 68)
print("  7. O MARCADOR E UM SO — ferramenta e Vigia na mesma chave")
print("=" * 68)

import app.tasks.handoff_watchdog as wd  # noqa: E402

redis4 = RedisDeMentira()
com_redis(redis4)

# A ferramenta reserva...
rodar(hh.reivindicar_o_aviso("conv-XYZ", 6))
chaves_depois_da_tool = set(redis4.chaves)
# ...e o Vigia tem de VER a reserva dela.
ja = rodar(wd._ja_avisado_recentemente("conv-XYZ", 6))
certo(ja is True,
      "🔴 o Vigia ENXERGA a reserva feita pela ferramenta (mesma chave)")
certo(len(redis4.chaves) == 1,
      "e nao criou uma segunda chave — uma definicao, nao duas")
certo(chaves_depois_da_tool == set(redis4.chaves), "a chave e literalmente a mesma")

# CONTROLE: conversa DIFERENTE nao herda a reserva.
outra = rodar(wd._ja_avisado_recentemente("conv-OUTRA", 6))
certo(outra is False,
      "CONTROLE: outra conversa NAO e silenciada pela reserva desta")

print()
print("=" * 68)
print("  8. REDIS FORA DO AR: avisa, nao cala")
print("=" * 68)

com_redis(RedisMorto())
certo(rodar(hh.reivindicar_o_aviso("qualquer", 6)) is False,
      "🔴 Redis morto devolve False = AVISA. O defeito grave e o silencio")
# e devolver a vez com Redis morto nao pode estourar
try:
    rodar(hh.devolver_a_vez("qualquer"))
    certo(True, "devolver a vez com Redis morto nao derruba o processo")
except Exception as e:  # noqa: BLE001
    certo(False, f"devolver a vez estourou: {type(e).__name__}")

print()
print("=" * 68)
print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
print("=" * 68)
sys.exit(1 if FAIL else 0)
