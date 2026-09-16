# -*- coding: utf-8 -*-
"""G-A1 · G-A2 · G-A3 — a guarda unica "humano ja esta nesta conversa".

O DEFEITO, MEDIDO
=================
📊 10/09/2026, 17:14:18 → 18:29:59 UTC: **7 mensagens ao grupo da Resulta em
75,7 minutos, todas sobre UMA conversa.** E a Saionara digitou "1" as 17:18:14
(`work_events`, `travamento.assumido`, ator `user`): **6 das 7 sairam depois de
um humano da corretora ja estar dentro daquela conversa.**

📊 E a arma continuava carregada. Medido em 16/09/2026 sobre producao:

```
conversas em HUMAN_REQUESTED ................  254
elegiveis (ultima palavra do segurado) ......   99
dessas, com humano da corretora nos 7 dias ..   98   <- pelo MOTOR Python
```

🔴 O 98 foi medido pelo MOTOR (`ultima_palavra_humana` + a janela), nao por
SQL — CLAUDE.md §9.4: um padrao medido com um motor e aplicado com outro e um
padrao sobre outra coisa. A propria SQL da proposta dava 98 de 99 tambem, mas
so o motor exclui `#nota` e o eco do agente.

O QUE ESTE GUARDA PROVA
=======================
G-A1  rodando `o_grupo_pode_saber` sobre o ACERVO, as elegiveis CALAM — e a
      LINHA DE CONTROLE: uma conversa SEM palavra humana PASSA. ⛔ A assercao
      e contra o conjunto medido, NUNCA contra o literal `98`: um guarda que
      fixe o numero fica vermelho na primeira mensagem nova e ensina a equipe a
      ignorar o guarda — que e literalmente o defeito que esta SPEC conserta.
G-A2  TODO caminho que resolve destino de suporte passa pela porta unica.
      Varredura do backend: um envio novo ao grupo sem a guarda fica vermelho.
G-A3  `janela_de_silencio_dias` = 0 DEVOLVE todas as elegiveis (a regra desliga
      sem deploy), e NAO EXISTE no repositorio constante/env de janela so do
      grupo.

🔴 A MUTACAO que deixa este arquivo vermelho: desligar a pergunta 4 da guarda
(`silenciar_por_palavra_humana` sempre `(False, "")`) → as elegiveis voltam a
passar → G-A1 vermelho.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import types
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Os `__init__.py` de `app.services` importam o mundo. Pacotes VAZIOS com
# `__path__` deixam os submodulos carregarem por arquivo — o mesmo truque de
# `test_o_grupo_nao_recebe_o_mesmo_aviso_duas_vezes.py`.
_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _pkg in ("app", "app.agents", "app.agents.tools", "app.core",
             "app.services", "app.services.whatsapp", "app.tasks"):
    if _pkg not in sys.modules:
        _m = types.ModuleType(_pkg)
        _m.__path__ = [os.path.join(_RAIZ, *_pkg.split("."))]
        sys.modules[_pkg] = _m

from app.services.o_fim_do_atendimento import (  # noqa: E402
    janela_de_silencio_dias, silenciar_por_palavra_humana, ultima_palavra_humana,
)
from app.services.o_grupo_so_o_que_importa import (  # noqa: E402
    TIPOS_ISENTOS, TIPO_CONCLUSAO, TIPO_ESPERA_VENCIDA, TIPO_PEDIDO_DE_AJUDA,
    TIPO_RESUMO_DIARIO, TIPO_SINISTRO, TIPO_VIGIA, e_numero_da_casa,
    o_grupo_pode_saber,
)

OK = FAIL = 0


def certo(condicao, frase):
    global OK, FAIL
    if condicao:
        OK += 1
        print("  ✅", frase)
    else:
        FAIL += 1
        print("  ❌", frase)


def rodar(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


CORPUS = os.path.join(_RAIZ, "tests", "corpus", "acervo_do_grupo_2026-09-16.json")

print("=" * 70)
print("  G-A1 — sobre o ACERVO REAL, pelo MOTOR")
print("=" * 70)

with open(CORPUS, encoding="utf-8") as f:
    acervo = json.load(f)
conversas = acervo["conversas"]
certo(len(conversas) >= 50,
      "o corpus do acervo tem %d conversas elegiveis (📊 16/09/2026)" % len(conversas))

AGORA = datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc)
N = janela_de_silencio_dias()
certo(N == 7, "a janela padrao da plataforma e %d dias (a MESMA do atendimento)" % N)


def _cala_pela_janela(conversa, n_dias=None):
    """🔴 Pelo MOTOR: `ultima_palavra_humana` -> `silenciar_por_palavra_humana`.
    ⛔ Nada de regex sobre `payload` (CLAUDE.md §9.4)."""
    uh = ultima_palavra_humana(conversa["mensagens"])
    calar, _ = silenciar_por_palavra_humana(ultima_humana=uh, agora=AGORA,
                                            n_dias=N if n_dias is None else n_dias)
    return calar


calam = [c for c in conversas if _cala_pela_janela(c)]
passam = [c for c in conversas if not _cala_pela_janela(c)]
print("     📊 do acervo: %d calam · %d passam" % (len(calam), len(passam)))

certo(len(calam) >= int(len(conversas) * 0.8),
      "a MAIORIA das elegiveis cala — %d de %d" % (len(calam), len(conversas)))
certo(len(calam) > 0 and len(passam) >= 0,
      "🔴 o conjunto que cala NAO e vazio: a guarda tem efeito real")

# 🔴 A LINHA DE CONTROLE — sem ela, o teste provaria so que a funcao sempre
#    devolve `False`. Uma conversa cuja unica fala humana e ANTIGA passa.
velha = {"mensagens": [
    {"role": "assistant", "content": "oi", "created_at": (AGORA - timedelta(days=40)).isoformat(),
     "payload": {"origem": "espelho"}},
    {"role": "user", "content": "ola", "created_at": (AGORA - timedelta(hours=1)).isoformat(),
     "payload": {}},
]}
certo(_cala_pela_janela(velha) is False,
      "🔴 CONTROLE: conversa cuja fala humana e de 40 dias atras PASSA")

sem_humano = {"mensagens": [
    {"role": "user", "content": "ola", "created_at": (AGORA - timedelta(hours=2)).isoformat(),
     "payload": {}},
    {"role": "assistant", "content": "oi", "created_at": (AGORA - timedelta(hours=1)).isoformat(),
     "payload": {}},   # sem `origem` = fala do AGENTE, nao de gente
]}
certo(_cala_pela_janela(sem_humano) is False,
      "🔴 CONTROLE: conversa SEM palavra humana PASSA — a guarda nao cala tudo")

print()
print("=" * 70)
print("  G-A1b — a guarda inteira, com as quatro perguntas")
print("=" * 70)


class _Resposta:
    def __init__(self, data):
        self.data = data


class _Consulta:
    def __init__(self, banco, tabela):
        self.banco, self.tabela, self.filtros = banco, tabela, {}

    def select(self, *_a, **_k):
        return self

    def eq(self, coluna, valor):
        self.filtros[coluna] = valor
        return self

    def in_(self, *_a, **_k):
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def insert(self, linha):
        self.banco.escritas.append((self.tabela, linha))
        return self

    def execute(self):
        return _Resposta(self.banco.linhas(self.tabela, self.filtros))


class BancoDeMentira:
    """Dublê minimo. 🔴 Respeita `company_id` — e e por isso que ele prova §7."""

    def __init__(self, conversas=(), mensagens=(), internos=(), membros=(), fones=()):
        self.conversas, self.mensagens = list(conversas), list(mensagens)
        self.internos, self.membros, self.fones = list(internos), list(membros), list(fones)
        self.escritas = []

    def table(self, nome):
        return _Consulta(self, nome)

    def linhas(self, tabela, filtros):
        def _casa(linha):
            return all(str(linha.get(k)) == str(v) for k, v in filtros.items()
                       if k in linha)
        fonte = {"conversations": self.conversas, "messages": self.mensagens,
                 "company_internal_numbers": self.internos,
                 "company_members": self.membros, "users_v2": self.fones,
                 "work_events": []}.get(tabela, [])
        return [linha for linha in fonte if _casa(linha)]


EMPRESA_X = "11111111-1111-1111-1111-111111111111"
EMPRESA_Y = "22222222-2222-2222-2222-222222222222"
CONVERSA = "aaaaaaaa-0000-0000-0000-000000000001"

_msgs_com_humano = [
    {"conversation_id": CONVERSA, "role": "user", "content": "socorro",
     "created_at": (AGORA - timedelta(hours=3)).isoformat(), "payload": {}},
    {"conversation_id": CONVERSA, "role": "assistant", "content": "ja estou vendo",
     "created_at": (AGORA - timedelta(hours=2)).isoformat(),
     "payload": {"origem": "espelho"}},
    {"conversation_id": CONVERSA, "role": "user", "content": "obrigado",
     "created_at": (AGORA - timedelta(hours=1)).isoformat(), "payload": {}},
]
_conversa_limpa = {"id": CONVERSA, "company_id": EMPRESA_X, "user_phone": "5547999990001",
                   "claimed_by": None, "claimed_by_name": None, "claimed_at": None}

banco = BancoDeMentira(conversas=[_conversa_limpa], mensagens=_msgs_com_humano)

pode, porque = rodar(o_grupo_pode_saber(
    banco, company_id=EMPRESA_X, conversation_id=CONVERSA,
    tipo=TIPO_PEDIDO_DE_AJUDA, agora=AGORA))
certo(pode is False, "pergunta 4: humano falou ha 2h → o grupo NAO e avisado")
certo("atendente" in porque.lower(),
      "e o motivo e a FRASE que a janela ja produz, nao um codigo: %r" % porque[:60])

pode, _ = rodar(o_grupo_pode_saber(
    banco, company_id=EMPRESA_X, conversation_id=CONVERSA,
    tipo=TIPO_ESPERA_VENCIDA, agora=AGORA))
certo(pode is False, "e a espera vencida cala pela mesma guarda")

for tipo in (TIPO_SINISTRO, TIPO_CONCLUSAO, TIPO_RESUMO_DIARIO):
    pode, _ = rodar(o_grupo_pode_saber(
        banco, company_id=EMPRESA_X, conversation_id=CONVERSA, tipo=tipo, agora=AGORA))
    certo(pode is True,
          "🔴 `%s` PASSA mesmo com humano na conversa (§5.3 — e noticia, nao fila)" % tipo)

# CONTROLE: a mesma conversa SEM a fala humana volta a avisar
banco_sem = BancoDeMentira(conversas=[_conversa_limpa],
                           mensagens=[m for m in _msgs_com_humano
                                      if not m.get("payload")])
pode, _ = rodar(o_grupo_pode_saber(
    banco_sem, company_id=EMPRESA_X, conversation_id=CONVERSA,
    tipo=TIPO_PEDIDO_DE_AJUDA, agora=AGORA))
certo(pode is True, "🔴 CONTROLE: sem fala humana, o pedido de ajuda CHEGA")

# pergunta 3 — claim fresco cala; claim velho nao
_assumida = dict(_conversa_limpa, claimed_by="u-1", claimed_by_name="Regina",
                 claimed_at=(AGORA - timedelta(minutes=30)).isoformat())
banco_claim = BancoDeMentira(conversas=[_assumida],
                             mensagens=[m for m in _msgs_com_humano if not m.get("payload")])
pode, porque = rodar(o_grupo_pode_saber(
    banco_claim, company_id=EMPRESA_X, conversation_id=CONVERSA,
    tipo=TIPO_PEDIDO_DE_AJUDA, agora=AGORA))
certo(pode is False and "Regina" in porque,
      "pergunta 3: claim fresco cala, e o motivo diz quem assumiu")

_velho = dict(_assumida, claimed_at=(AGORA - timedelta(hours=9)).isoformat())
banco_velho = BancoDeMentira(conversas=[_velho],
                             mensagens=[m for m in _msgs_com_humano if not m.get("payload")])
pode, _ = rodar(o_grupo_pode_saber(
    banco_velho, company_id=EMPRESA_X, conversation_id=CONVERSA,
    tipo=TIPO_PEDIDO_DE_AJUDA, agora=AGORA))
certo(pode is True,
      "🔴 CONTROLE: claim de 9h (o dono nao voltou) NAO cala — senao vira mordaca")

# pergunta 2 — numero da casa
banco_casa = BancoDeMentira(
    conversas=[_conversa_limpa],
    mensagens=[m for m in _msgs_com_humano if not m.get("payload")],
    internos=[{"company_id": EMPRESA_X, "phone": "47999990001"}])
pode, porque = rodar(o_grupo_pode_saber(
    banco_casa, company_id=EMPRESA_X, conversation_id=CONVERSA,
    telefone="5547999990001", tipo=TIPO_PEDIDO_DE_AJUDA, agora=AGORA))
certo(pode is False and "corretora" in porque,
      "pergunta 2: numero da casa cala, e diz que e da casa")

# 🔴 §7 — DUAS CORRETORAS. O numero da casa de X nao cala Y.
pode, _ = rodar(o_grupo_pode_saber(
    banco_casa, company_id=EMPRESA_Y, conversation_id="", telefone="5547999990001",
    tipo=TIPO_PEDIDO_DE_AJUDA, agora=AGORA))
certo(pode is True,
      "🔴 §7: o numero da casa da corretora X NAO cala a corretora Y")

# FAIL-OPEN
class BancoMorto:
    def table(self, *_a, **_k):
        raise RuntimeError("banco fora")


pode, porque = rodar(o_grupo_pode_saber(
    BancoMorto(), company_id=EMPRESA_X, conversation_id=CONVERSA,
    tipo=TIPO_PEDIDO_DE_AJUDA, agora=AGORA))
certo(pode is True,
      "🔴 FAIL-OPEN: banco fora do ar AVISA (falar demais ao grupo e reversivel)")

print()
print("=" * 70)
print("  G-A2 — TODO caminho de envio ao grupo passa pela PORTA UNICA")
print("=" * 70)

PORTA = "enviar_ao_grupo"
#: Os 11 pontos da §3.2, conferidos um a um. Quem nao passa pela porta diz por que.
ISENTOS = {
    "app/api/admin_spec034.py":
        "alerta de TESTE — ferramenta de diagnostico do proprio Founder (§5.2)",
    "app/services/weekly_report.py":
        "fora do escopo (§2) — le so o legado; pendencia registrada",
    "app/services/proactive_suggestions.py":
        "fora do escopo (§2) — le so o legado; pendencia registrada",
    "app/services/atlas/route_sentinel.py":
        "vai ao FOUNDER (`_founder_alert_number`), nao ao grupo de corretora",
    "app/services/whatsapp/alerts.py":
        "§7.4 — muda de DESTINATARIO (o dono), nao de guarda; sai por provider",
    "app/services/dispatch_router.py":
        "e o dono do resolvedor; os dois pontos dele ja usam a porta",
    "app/main.py":
        "so CONTA corretoras sem destino no /health — nao envia nada",
}
GATILHOS = ("resolver_destino_de_suporte", "_support_contact",
            "human_support_destinations")

achados, fora = [], []
for raiz, _dirs, arquivos in os.walk(os.path.join(_RAIZ, "app")):
    for nome in arquivos:
        if not nome.endswith(".py"):
            continue
        caminho = os.path.join(raiz, nome)
        rel = os.path.relpath(caminho, _RAIZ).replace("\\", "/")
        texto = open(caminho, encoding="utf-8", errors="replace").read()
        if not any(g in texto for g in GATILHOS):
            continue
        achados.append(rel)
        # `_avisar_suporte` É a porta com outro nome: desde esta SPEC ele não
        # resolve destino nem envia — delega para `enviar_ao_grupo`. Aceitar os
        # dois nomes é o que impede o guarda de exigir refatoração cosmética
        # sem deixar de pegar o caminho NOVO que não passa por nenhum dos dois.
        if PORTA not in texto and "_avisar_suporte" not in texto \
                and rel not in ISENTOS:
            fora.append(rel)

certo(len(achados) >= 6,
      "a varredura encontrou %d arquivos que resolvem destino de suporte" % len(achados))
certo(not fora,
      "🔴 nenhum caminho novo manda ao grupo sem a porta unica — fora: %s" % (fora or "nenhum"))
certo(PORTA in open(os.path.join(_RAIZ, "app", "services",
                                 "o_grupo_so_o_que_importa.py"),
                    encoding="utf-8").read(),
      "e a porta e definida em UM lugar so")

# a guarda esta DENTRO da porta, nao no chamador
_porta = open(os.path.join(_RAIZ, "app", "services", "o_grupo_so_o_que_importa.py"),
              encoding="utf-8").read()
certo("o_grupo_pode_saber(" in _porta.split("async def enviar_ao_grupo")[1],
      "🔴 a guarda e chamada DENTRO de `enviar_ao_grupo` — nunca no chamador")

print()
print("=" * 70)
print("  G-A3 — uma regra, um numero, um lugar para mudar")
print("=" * 70)

todas_zero = [c for c in conversas if _cala_pela_janela(c, n_dias=0)]
certo(len(todas_zero) == 0,
      "🔴 `janela_de_silencio_dias`=0 DEVOLVE as %d elegiveis: a corretora "
      "desliga a regra sem deploy" % len(conversas))

# 🔴 A proibição é sobre a CONSTANTE e sobre a ENV — não sobre a frase que
# explica por que elas não existem. Procurar o nome solto deixava este guarda
# vermelho pela PRÓPRIA documentação do módulo, e um guarda que não consegue
# ficar verde é tão inútil quanto um que não consegue ficar vermelho.
_NOMES = r"JANELA_DO_GRUPO|GRUPO_SILENCIO|JANELA_GRUPO|SILENCIO_DO_GRUPO"
PROIBIDAS = re.compile(
    r"(?:" + _NOMES + r")\w*\s*=(?!=)"            # a constante, atribuída
    r"|getenv\(\s*['\"](?:" + _NOMES + r")"        # a env, lida
    r"|environ\[\s*['\"](?:" + _NOMES + r")"
    r"|environ\.get\(\s*['\"](?:" + _NOMES + r")")
suspeitos = []
for raiz, _dirs, arquivos in os.walk(os.path.join(_RAIZ, "app")):
    for nome in arquivos:
        if nome.endswith(".py"):
            caminho = os.path.join(raiz, nome)
            if PROIBIDAS.search(open(caminho, encoding="utf-8", errors="replace").read()):
                suspeitos.append(os.path.relpath(caminho, _RAIZ))
certo(not suspeitos,
      "⛔ NAO existe constante/env de janela so do grupo — achados: %s" % (suspeitos or "nenhum"))

_gporta = _porta
certo("janela_de_silencio_dias(companhia)" in _gporta,
      "🔴 a pergunta 4 chama `janela_de_silencio_dias(companhia)` — a MESMA "
      "funcao, a MESMA env, o MESMO override por corretora")

certo(TIPOS_ISENTOS == frozenset({TIPO_SINISTRO, TIPO_CONCLUSAO, TIPO_RESUMO_DIARIO,
                                  "queda_de_canal"}),
      "e a lista de isentos e literal e curta: %s" % sorted(TIPOS_ISENTOS))
certo(e_numero_da_casa({"47999990001"}, "+55 (47) 99999-0001") is True,
      "o casador aceita o telefone MAL FORMATADO do membro (mascara, +55, nono)")
certo(e_numero_da_casa({"4799990001"}, "554799990001") is True,
      "e casa com e sem o 55")
certo(TIPO_VIGIA not in TIPOS_ISENTOS,
      "`vigia` NAO e isento: ele responde a guarda como os outros")

print()
print("=" * 70)
print("  %d assercoes verdes · %d vermelhas" % (OK, FAIL))
print("=" * 70)
sys.exit(1 if FAIL else 0)
