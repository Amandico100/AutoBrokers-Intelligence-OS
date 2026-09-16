# -*- coding: utf-8 -*-
"""G-D1 · G-D2 — os quatro modelos, e a conta das 19h que diz a verdade.

O DEFEITO, MEDIDO
=================
📊 **P-PILOTO-12:** a régua de língua humana (`problemas_de_lingua`,
`test_o_caso_se_explica_sozinho.py:1181`) rodava só nas cartas e na novidade ao
cliente. O dossiê — o que a Regina lê no celular — nunca passou por ela.

📊 **16/09/2026, sobre produção:** `grep -rn "motivo_classe" backend/app` → **0**.
`human_handoff_reason` preenchido em **2 de 254** conversas `HUMAN_REQUESTED`.
O campo que a conta das 19h precisa **não existia e não tinha escritor**.

⚠️ **E um motivo desconhecido NÃO pode cair em `regra`.** Se caísse, hoje —
com zero escritores — TODO pedido de ajuda sairia do denominador e a eficiência
daria ~100% sem medir nada.

O QUE ESTE GUARDA PROVA
=======================
G-D1  os quatro modelos renderizados: `problemas_de_lingua` VAZIA · `wa.me/55…`
      presente e sem `+` · AUSÊNCIA de link de painel e de bloco de mensagens ·
      ✅ curto (≤ 3 linhas).
G-D2  a fórmula, reconstruída sobre `work_events`: ajuda por REGRA fora do
      denominador · sinistro no numerador · denominador 0 vira "sem
      acionamentos", não 0% · 🔴 `desconhecido` fora dos DOIS, com linha
      própria · acima do limite de fatia o resumo NÃO publica o número.
"""
from __future__ import annotations

import asyncio
import importlib.util as _il
import os
import re
import sys
import types
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _pkg in ("app", "app.agents", "app.agents.tools", "app.core", "app.services",
             "app.services.whatsapp", "app.tasks"):
    if _pkg not in sys.modules:
        _m = types.ModuleType(_pkg)
        _m.__path__ = [os.path.join(_RAIZ, *_pkg.split("."))]
        sys.modules[_pkg] = _m

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


from app.services.os_modelos_do_grupo import (  # noqa: E402
    LIMITE_DE_DESCONHECIDOS, contagens_do_dia, eficiencia_do_dia, link_do_whatsapp,
    modelo_atendimento_concluido, modelo_novo_sinistro, modelo_resumo_do_dia,
)

# 🔴 A RÉGUA DE VERDADE, importada do guarda que a define — ⛔ não uma cópia.
# O arquivo dela é um guarda-script com `sys.exit` no fim; carregamos SÓ a
# função, por AST, para não executar o módulo inteiro.
_FONTE_REGUA = open(os.path.join(_RAIZ, "tests", "test_o_caso_se_explica_sozinho.py"),
                    encoding="utf-8").read()
_ns: dict = {"re": re}
import ast  # noqa: E402

_arv = ast.parse(_FONTE_REGUA)
_QUERO = {"problemas_de_lingua", "_SNAKE", "_CHAVE", "_APOLICE", "_ACAO_COM_DONO"}
for _no in _arv.body:
    if isinstance(_no, ast.FunctionDef) and _no.name in _QUERO:
        exec(compile(ast.Module([_no], []), "<regua>", "exec"), _ns)
    elif isinstance(_no, ast.Assign):
        for _alvo in _no.targets:
            if isinstance(_alvo, ast.Name) and _alvo.id in _QUERO:
                exec(compile(ast.Module([_no], []), "<regua>", "exec"), _ns)
problemas_de_lingua = _ns["problemas_de_lingua"]

#: ⚠️ *"não termina numa próxima ação COM DONO"* é regra da CARTA ao segurado,
#: não do dossiê que a atendente lê. O ✅ ATENDIMENTO CONCLUÍDO termina de
#: propósito com o desfecho e a assinatura. ⛔ As outras quatro verificações —
#: snake_case, chave/versão, `@N` e língua de apólice — valem inteiras.
_SO_DA_CARTA = "nao termina numa proxima acao COM DONO"


def problemas_no_grupo(texto):
    return [p for p in problemas_de_lingua(texto) if p != _SO_DA_CARTA]


print("=" * 70)
print("  G-D1 — os quatro modelos falam português")
print("=" * 70)

SINISTRO = modelo_novo_sinistro(
    tipo="colisão com terceiro", segurado="Fulano de Tal",
    documento="000.000.000-00",
    apolice="Porto Seguro · auto · vigente até 12/03/2027",
    quando="hoje, 16/09, por volta das 13h30",
    resumo=("O segurado bateu na traseira de outro carro numa avenida, com chuva. "
            "Ninguém se feriu e os dois carros andam."),
    pontos_de_atencao=["há terceiro envolvido — precisa dos dados dele",
                       "ainda não há boletim de ocorrência"],
    telefone="5547988880001")

CONCLUSAO = modelo_atendimento_concluido(
    segurado="Fulano de Tal", servico="encanador pela Allianz",
    protocolo="2026-1234567", minutos=34, de="14:07", ate="14:41")

CONCLUSAO_HUMANA = modelo_atendimento_concluido(
    segurado="Fulano de Tal", servico="encanador pela Allianz",
    minutos=72, por_humano="Regina")

RESUMO = modelo_resumo_do_dia("16/09", {
    "acionamentos_entregues": 9, "sinistros_com_dossie": 2,
    "ajudas_incapacidade": 2, "ajudas_regra": 3, "ajudas_desconhecidas": 1,
    "duvidas": 12, "ja_com_a_equipe": 4, "calados_pela_janela": 6,
    "vigia_ura": 2, "vigia_prazo": 1})

# O 🆘 é montado por `human_handoff._montar_dossie`; aqui provamos o CONTRATO
# dele (o que saiu e o que entrou) pelo código que o produz.
DOSSIE = open(os.path.join(_RAIZ, "app", "agents", "tools", "human_handoff.py"),
              encoding="utf-8").read()

for rotulo, texto in (("🚨 NOVO SINISTRO", SINISTRO),
                      ("✅ CONCLUÍDO", CONCLUSAO),
                      ("✅ CONCLUÍDO por humano", CONCLUSAO_HUMANA),
                      ("📊 RESUMO das 19h", RESUMO)):
    problemas = problemas_no_grupo(texto)
    certo(not problemas, "%s passa na régua de língua humana %s" % (
        rotulo, ("— achados: %s" % problemas[:3]) if problemas else ""))

certo("https://wa.me/5547988880001" in SINISTRO,
      "🔴 o 🚨 leva o WhatsApp do segurado CLICÁVEL")
certo("wa.me/+" not in SINISTRO and "+55" not in SINISTRO,
      "⛔ sem `+`, sem espaço, sem parêntese (§8.5)")
certo("http" not in CONCLUSAO and "http" not in RESUMO,
      "o ✅ e o 📊 não levam link nenhum")
certo(len([l for l in CONCLUSAO.splitlines() if l.strip()]) <= 3,
      "🔴 o ✅ é CURTO: %d linhas (uma mensagem que ninguém precisa abrir)"
      % len([l for l in CONCLUSAO.splitlines() if l.strip()]))
certo("🤖 agente" in CONCLUSAO and "Regina" in CONCLUSAO_HUMANA
      and "🤖" not in CONCLUSAO_HUMANA,
      "🔴 a atendente aparece pelo NOME; o agente assina 🤖 (D-PILOTO-12)")

# §8.0 — as duas reversões da SPEC-071, provadas no código que monta o 🆘.
_corpo = DOSSIE.split("def _montar_dossie", 1)[1].split("\n    def ", 1)[0]
certo("_link_da_conversa(conversa)" not in _corpo,
      "🔴 o 🆘 NÃO leva mais o link do painel (§8.0 — no celular o número custa "
      "um toque e o painel custa uma página)")
certo("*CONVERSA*" not in _corpo,
      "🔴 e NÃO leva mais as últimas mensagens (viravam 4 balões)")
certo("link_do_whatsapp(" in _corpo and "WhatsApp do segurado" in _corpo,
      "🔴 e leva o `wa.me` do segurado no lugar")

# O formato do link, nos casos que o §8.5 congela.
certo(link_do_whatsapp("47988880001") == "https://wa.me/5547988880001",
      "sem 55 → o 55 entra")
certo(link_do_whatsapp("5547988880001") == "https://wa.me/5547988880001",
      "🔴 já com 55 → NÃO duplica")
certo(link_do_whatsapp("+55 (47) 98888-0001") == "https://wa.me/5547988880001",
      "com máscara → sai limpo")
certo(link_do_whatsapp("4738880001") == "https://wa.me/554738880001",
      "🔴 10 dígitos saem ASSIM MESMO — ⛔ não se inventa o nono dígito")
certo(link_do_whatsapp("") == "" and link_do_whatsapp("abc") == "",
      "CONTROLE: vazio e lixo não viram link")

print()
print("=" * 70)
print("  G-D1b — o classificador do motivo lê PALAVRA, não substring")
print("=" * 70)

# 🔴 O PAR QUE O JUIZ FRESCO PEDIU — 16/09/2026. `classificar_o_motivo` fazia
# `alvo in texto`, e "ura" ⊂ "segURAdora". ⚠️ Não é cosmético: `motivo_classe`
# decide o DENOMINADOR da eficiência que a corretora lê às 19h.
import importlib.util as _il2  # noqa: E402

_sp = _il2.spec_from_file_location(
    "_hh_classificador",
    os.path.join(_RAIZ, "app", "agents", "tools", "human_handoff.py"))
_hh = _il2.module_from_spec(_sp)
try:
    _sp.loader.exec_module(_hh)
except Exception as _e:  # noqa: BLE001 — só a função pura interessa
    pass
classificar = getattr(_hh, "classificar_o_motivo", None)
certo(callable(classificar), "o escritor de `motivo_classe` existe e é chamável")

PARES = [
    # (motivo, classe esperada, por quê)
    ("a seguradora não respondeu", "desconhecido",
     '🔴 "ura" ⊂ segURAdora — o defeito que o juiz pegou'),
    ("cuidado com o valor da fatura", "regra",
     '"valor" solto continua sendo alçada — é a palavra, não o acaso'),
    ("sentinela esgotou o tempo limite", "incapacidade",
     '🔴 "tempo limite" (expressão) ganha de "limite" (palavra solta)'),
    ("procura de vaga no estacionamento", "desconhecido",
     '"procura" não contém a palavra ura'),
    # CONTROLE — os casos de verdade continuam classificados
    ("Travou na URA e a recuperação automática esgotou", "incapacidade",
     "CONTROLE: o motivo REAL do Vigia continua incapacidade"),
    ("o segurado tem vítima no local", "regra",
     "CONTROLE: vítima continua regra"),
    ("cliente_pediu_humano", "regra",
     "CONTROLE: a chave técnica continua classificada"),
    ("faltou um dado que o segurado não tinha", "incapacidade",
     "CONTROLE: dado faltante continua incapacidade"),
]
for motivo, esperada, porque in PARES:
    classe, chave = classificar(motivo)
    certo(classe == esperada,
          "%-58s → %s/%s   %s" % (repr(motivo)[:56], classe, chave, porque))

certo(classificar("")[0] == "desconhecido" and classificar(None)[0] == "desconhecido",
      "⛔ e no escuro é `desconhecido` — nunca `regra`, que daria ~100% sem medir")

print()
print("=" * 70)
print("  G-D2 — a eficiência das 19h diz a verdade")
print("=" * 70)

certo(eficiencia_do_dia(acionamentos_entregues=9, sinistros_com_dossie=2,
                        ajudas_por_incapacidade=2) == 85,
      "🔴 (9+2) / (9+2+2) = 85% — a fórmula de D-PILOTO-13")
certo("Eficiência: 85%" in RESUMO and "(11 de 13)" in RESUMO,
      "e o resumo publica exatamente isso")

# 🔴 AJUDA POR REGRA FORA DO DENOMINADOR — contar contra pune o agente por obedecer.
com_regra = eficiencia_do_dia(acionamentos_entregues=9, sinistros_com_dossie=2,
                              ajudas_por_incapacidade=2 + 3)
certo(com_regra != 85,
      "🔴 CONTROLE: se `vitima` entrasse no denominador o número MUDARIA "
      "(85%% → %d%%) — a fórmula CONSEGUE ser diferente" % com_regra)

# 🔴 SINISTRO NO NUMERADOR.
certo(eficiencia_do_dia(acionamentos_entregues=0, sinistros_com_dossie=1,
                        ajudas_por_incapacidade=1) == 50,
      "🔴 sinistro conta como SUCESSO (coleta feita + dossiê entregue)")

# ⚠️ DENOMINADOR ZERO NÃO É 0%.
certo(eficiencia_do_dia(acionamentos_entregues=0, sinistros_com_dossie=0,
                        ajudas_por_incapacidade=0) is None,
      "🔴 denominador zero devolve None — não 0%")
so_duvidas = modelo_resumo_do_dia("16/09", {"duvidas": 12})
certo("Sem acionamentos hoje" in so_duvidas and "0%" not in so_duvidas,
      "e o resumo diz *sem acionamentos hoje*, nunca *0%*")
certo("12 dúvidas respondidas" in so_duvidas,
      "CONTROLE: e o volume do dia continua aparecendo")

# 🔴 `desconhecido` FORA DOS DOIS, COM LINHA PRÓPRIA.
certo("1 ajuda sem motivo registrado" in RESUMO,
      "🔴 `desconhecido` tem LINHA PRÓPRIA e visível")
certo("(11 de 13)" in RESUMO,
      "e não entra nem no numerador nem no denominador (13, não 14)")

# 🔴 ACIMA DO LIMITE DE FATIA, O NÚMERO NÃO É PUBLICADO.
muitos_desconhecidos = modelo_resumo_do_dia("16/09", {
    "acionamentos_entregues": 2, "ajudas_incapacidade": 1,
    "ajudas_desconhecidas": 4})
certo("Eficiência" not in muitos_desconhecidos,
      "🔴 com 4 de 5 ajudas sem motivo, o resumo NÃO publica a eficiência")
certo("Ainda não dá para medir" in muitos_desconhecidos,
      "e diz por quê: %r" % muitos_desconhecidos.splitlines()[2][:70])
certo(0 < LIMITE_DE_DESCONHECIDOS < 1,
      "o limite é uma fração declarada: %.0f%%" % (LIMITE_DE_DESCONHECIDOS * 100))

# ⛔ Tratar `desconhecido` como `regra` daria ~100% com o acervo de hoje.
como_regra = eficiencia_do_dia(acionamentos_entregues=2, sinistros_com_dossie=0,
                               ajudas_por_incapacidade=1)
certo(como_regra == 67,
      "CONTROLE: com 1 incapacidade o número é 67%%; se os 4 desconhecidos "
      "virassem `regra` ele saltaria para perto de 100 sem medir nada")

print()
print("=" * 70)
print("  G-D2b — a conta vem de `work_events`, reconstruída")
print("=" * 70)

AGORA = datetime(2026, 9, 16, 22, 0, tzinfo=timezone.utc)
EMPRESA = "11111111-1111-1111-1111-111111111111"


_SEQ = [0]


def _ev(evento, **carga):
    _SEQ[0] += 1
    return {"id": _SEQ[0], "event_type": evento, "payload_redacted": carga,
            "created_at": (AGORA - timedelta(hours=2)).isoformat()}


LINHAS = [
    _ev("grupo.enviado", tipo="conclusao", motivo_classe="conclusao"),
    _ev("grupo.enviado", tipo="conclusao", motivo_classe="conclusao"),
    _ev("grupo.enviado", tipo="sinistro", motivo_classe="desconhecido"),
    _ev("grupo.enviado", tipo="pedido_de_ajuda", motivo_classe="incapacidade"),
    _ev("grupo.enviado", tipo="pedido_de_ajuda", motivo_classe="regra"),
    _ev("grupo.enviado", tipo="pedido_de_ajuda", motivo_classe="desconhecido"),
    _ev("grupo.calado", tipo="pedido_de_ajuda", calou_porque="Regina assumiu esta conversa"),
    _ev("grupo.calado", tipo="espera_vencida",
        calou_porque="a atendente falou nesta conversa hoje"),
    _ev("grupo.calado", tipo="pedido_de_ajuda", calou_porque="repetido"),
    _ev("vigia.ura_silent"),
    _ev("vigia.deadline"),
]


class _Q:
    """⚠️ O dublê PAGINA, porque a leitura real pagina.

    🔴 `contagens_do_dia` deixou de usar `.limit(5000)` — o PostgREST devolve
    no máximo 1000 por resposta, e um dia movimentado perderia eventos em
    silêncio, publicando um número menor que a verdade com cara de medição. Ela
    usa `ler_paginado_async`, que manda `.order(...).range(...)` e faz `await`
    no `execute()`. Um dublê que ignorasse isso provaria outra coisa.
    """

    def __init__(self, t):
        self.t, self.faixa = t, None

    def select(self, *_a, **_k):
        return self

    def eq(self, *_a, **_k):
        return self

    def gte(self, *_a, **_k):
        return self

    def lt(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def order(self, *_a, **_k):
        return self

    def range(self, inicio, fim):
        self.faixa = (int(inicio), int(fim))
        return self

    async def execute(self):
        linhas = LINHAS if self.t == "work_events" else []
        if self.faixa:
            linhas = linhas[self.faixa[0]:self.faixa[1] + 1]
        return types.SimpleNamespace(data=linhas)


c = rodar(contagens_do_dia(types.SimpleNamespace(table=lambda n: _Q(n)),
                           EMPRESA, AGORA - timedelta(days=1), AGORA))
print("     📊 reconstruído:", {k: v for k, v in c.items() if v})
certo(c["acionamentos_entregues"] == 2 and c["sinistros_com_dossie"] == 1,
      "as conclusões e o sinistro vêm do diário")
certo(c["ajudas_incapacidade"] == 1 and c["ajudas_regra"] == 1
      and c["ajudas_desconhecidas"] == 1,
      "🔴 as três classes de ajuda são contadas SEPARADAS")
certo(c["ja_com_a_equipe"] == 1 and c["calados_pela_janela"] == 1,
      "🔴 o que a guarda CALOU reaparece — e as duas razões viram linhas diferentes")
certo(c["calados_total"] == 3 and (c["ja_com_a_equipe"] + c["calados_pela_janela"]) == 2,
      "e o `repetido` não vira linha do resumo (é a mesma notícia, não um silêncio novo)")
certo(c["vigia_ura"] == 1 and c["vigia_prazo"] == 1,
      "os achados do Vigia viram as linhas ⏱️ em vez de mensagem na hora")
certo(c.get("truncou") == 0,
      "🔴 e a leitura NÃO truncou — quem mostra número para gente precisa saber "
      "quando parou no teto (`ler_paginado_async`, não `.limit(5000)`)")

texto = modelo_resumo_do_dia("16/09", c)
certo("🤝 1 conversa que a equipe já conduzia" in texto
      and "🔕 1 conversa em que fiquei em silêncio pela janela" in texto,
      "🔴 RECONCILIÁVEL: a soma das linhas 'fora da conta' bate com os "
      "`grupo.calado` do dia")
certo(modelo_resumo_do_dia("16/09", {}) == "",
      "⛔ CONTROLE: dia sem movimento não manda mensagem dizendo que não houve nada")

print()
print("=" * 70)
print("  %d assercoes verdes · %d vermelhas" % (OK, FAIL))
print("=" * 70)
sys.exit(1 if FAIL else 0)
