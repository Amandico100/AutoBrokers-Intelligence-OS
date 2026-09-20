# -*- coding: utf-8 -*-
"""🔴 O TESTE DO FIO — SPEC-EXTRA-001.7, unidades B e C.

```
linhas do banco → ler_o_dia → MOTOR importado → medir_o_dia → regua_por_dimensao → saída
```

O que este guarda prova, e por que cada afirmação existe:

```
G-P1  o NÚMERO FINAL por dia × corretora sai do dublê REAL atravessando o motor
G-P2  a medição RECONCILIA com `contagens_do_dia` — dois contadores divergindo
      sobre o mesmo dia seriam, eles mesmos, o defeito
G-P3  o título do silêncio é o que o PRODUTO escreve (casado contra o fonte), e
      a classe do motivo sintético é a MESMA do motivo real
G-P4  zero PII: um dublê com telefone, CPF e nome nas linhas não vaza um byte
G-P5  isolamento: separado == junto, e uma linha da B não mexe na A
G-P6  NÃO AVALIADA consegue sair dos DOIS jeitos (mutação nos dois sentidos)
G-P7  🔴 menos dado NUNCA melhora a nota — e a única subida permitida é a de
      quem removeu uma FALHA, o que o teste EXIGE provar linha a linha
G-P8  o dia é o dia LOCAL da corretora, não o dia UTC
G-P9  antes de 14/09/2026 "conversas atendidas" é NÃO MENSURÁVEL, e não zero
G-P10 a nota do bloco só sai com a MAIORIA das dimensões avaliada
```

🔴 **O dublê é GERADO** (`scripts/gerar_recorte_do_piloto.py`), nunca escrito à
mão: ele é um recorte real de 17–18/09/2026 das duas corretoras, anonimizado na
origem. As linhas que o recorte real **não tem** (protocolo, handoff entregue,
fala do agente) são acrescentadas a partir das CONSTANTES DO PRODUTO —
`TITULO_HANDOFF_ENTREGUE`, `KIND_PROTOCOLO`, `ORIGEM_DO_AGENTE` — e não de
texto inventado: se o produto renomear qualquer uma, este teste muda junto.

```
cd backend
PYTHONIOENCODING=utf-8 python tests/test_o_piloto_e_medido.py
PYTHONIOENCODING=utf-8 python -m pytest tests/test_o_piloto_e_medido.py -q
```
"""
from __future__ import annotations

import asyncio
import copy
import io
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.services.o_fim_do_atendimento import classe_do_silencio  # noqa: E402
from app.services.os_modelos_do_grupo import contagens_do_dia  # noqa: E402
from scripts.medir_o_piloto import (  # noqa: E402
    KIND_PROTOCOLO,
    NAO_AVALIADA,
    NAO_MENSURAVEL,
    ORIGEM_DO_AGENTE,
    TITULO_HANDOFF_ENTREGUE,
    TITULO_HANDOFF_FALHOU,
    TITULO_SILENCIO,
    em_markdown,
    janela_padrao,
    limites_do_dia,
    medir,
    medir_o_dia,
    procurar_pii,
    regua_por_dimensao,
    somar_os_dias,
    _DB,
)
from app.services.platform_outbound import fuso_da_corretora  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECORTE = os.path.join(RAIZ, "tests", "corpus", "piloto", "recorte.json")

OK = FAIL = 0
FALHAS = []


def certo(cond, nome):
    global OK, FAIL
    if cond:
        OK += 1
        print("   ✅ %s" % nome)
    else:
        FAIL += 1
        FALHAS.append(nome)
        print("   ❌ %s" % nome)
    return bool(cond)


def rodar(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


# =========================================================================== #
# O DUBLÊ — SÓ na borda: o cliente do banco. Nada mais é dublado.
# =========================================================================== #

class _Consulta:
    def __init__(self, linhas):
        self._linhas = list(linhas)

    def select(self, _colunas):
        return self

    def eq(self, coluna, valor):
        self._linhas = [l for l in self._linhas if str(l.get(coluna)) == str(valor)]
        return self

    def in_(self, coluna, valores):
        alvo = {str(v) for v in valores}
        self._linhas = [l for l in self._linhas if str(l.get(coluna)) in alvo]
        return self

    def gte(self, coluna, valor):
        self._linhas = [l for l in self._linhas
                        if l.get(coluna) and str(l[coluna]) >= str(valor)]
        return self

    def lt(self, coluna, valor):
        self._linhas = [l for l in self._linhas
                        if l.get(coluna) and str(l[coluna]) < str(valor)]
        return self

    def limit(self, n):
        self._linhas = self._linhas[:n]
        return self

    def order(self, coluna, desc=False):
        self._linhas.sort(key=lambda l: str(l.get(coluna) or ""), reverse=bool(desc))
        return self

    def range(self, a, b):
        self._linhas = self._linhas[a:b + 1]
        return self

    async def execute(self):
        return type("R", (), {"data": copy.deepcopy(self._linhas)})()


class ClienteDeCorpus:
    """O banco, dublado NA BORDA. ⚠️ Ele não sabe nada de piloto: só serve
    linhas e aplica os mesmos filtros que o PostgREST aplicaria."""

    def __init__(self, tabelas, quebrada=None):
        self.tabelas = tabelas
        #: 🔴 A tabela que FALHA. Ela existe porque `ler_paginado` devolve
        #: `truncou=True` também quando a página estoura — e era por esse
        #: caminho que uma nota SUBIA (B4).
        self.quebrada = quebrada

    def table(self, nome):
        if nome == self.quebrada:
            raise RuntimeError("timeout simulado em %s" % nome)
        return _Consulta(self.tabelas.get(nome) or [])


def carregar():
    with io.open(RECORTE, "r", encoding="utf-8") as fh:
        return json.load(fh)


CORPO = carregar()
EMPRESAS = {c["company_name"]: c["id"] for c in CORPO["tabelas"]["companies"]}
NOMES = sorted(EMPRESAS)
DE, ATE = date(2026, 9, 17), date(2026, 9, 18)


def com(tabelas_extras=None, remover=None):
    """Uma cópia do recorte, com linhas acrescentadas ou removidas."""
    t = copy.deepcopy(CORPO["tabelas"])
    for tabela, linhas in (tabelas_extras or {}).items():
        t.setdefault(tabela, []).extend(copy.deepcopy(linhas))
    for tabela, ids in (remover or {}).items():
        t[tabela] = [l for l in t[tabela] if l.get("id") not in set(ids)]
    return t


def medir_com(tabelas, nomes=None, de=DE, ate=ATE, quebrada=None):
    cliente = ClienteDeCorpus(tabelas, quebrada=quebrada)
    corretoras = [(n, EMPRESAS[n]) for n in (nomes or NOMES)]
    return rodar(medir(cliente, corretoras, de, ate))


def _em(nome, corpo):
    return corpo["corretoras"][nome]


def _dim(bloco, chave):
    for d in bloco["dimensoes"]:
        if d["chave"] == chave:
            return d
    raise KeyError(chave)


# --------------------------------------------------------------------------- #
# As linhas que o recorte real NÃO TEM, montadas a partir das constantes do
# produto. 🔴 Elas existem para provar que a dimensão CONSEGUE sair com nota —
# sem elas, G-P6 só saberia dizer "NÃO AVALIADA", e um guarda que só sabe dizer
# não, não guarda (CLAUDE.md §9.3).
# --------------------------------------------------------------------------- #
QUANDO = "2026-09-17T15:00:00+00:00"


def envios(cid, n, kind=KIND_PROTOCOLO):
    return [{"id": "ps-%s-%d" % (kind[:4], i), "company_id": cid, "kind": kind,
             "created_at": QUANDO} for i in range(n)]


def runs(cid, n, status="completed"):
    return [{"id": "wr-ac-%d" % i, "company_id": cid, "runtime_kind": "acionamento",
             "status": status, "created_at": QUANDO} for i in range(n)]


def handoffs(cid, entregues, falhados):
    linhas = [{"id": "aa-ok-%d" % i, "company_id": cid, "category": "atendimentos",
               "title": TITULO_HANDOFF_ENTREGUE, "detail": "",
               "created_at": QUANDO} for i in range(entregues)]
    linhas += [{"id": "aa-nok-%d" % i, "company_id": cid,
                "category": "atendimentos", "title": TITULO_HANDOFF_FALHOU,
                "detail": "", "created_at": QUANDO} for i in range(falhados)]
    return linhas


# =========================================================================== #
def bloco_1_o_fio():
    print("\n1. O FIO — o número final sai do dublê real, pelo motor")
    corpo = medir_com(com())
    for nome in NOMES:
        bloco = _em(nome, corpo)
        certo(len(bloco["dias"]) == 2, "%s: dois dias medidos" % nome)
        certo([d["dia"] for d in bloco["dias"]] == ["2026-09-17", "2026-09-18"],
              "%s: os dias são os pedidos, em ordem" % nome)
    af = _em("AutoFleet", corpo)["agregado"]
    re_ = _em("Resulta Seguros", corpo)["agregado"]
    # 📊 O recorte real: grupo.calado só na AutoFleet, 7 linhas em 17–18/09.
    certo(af["grupo_calados"] == 7,
          "AutoFleet: 7 conversas em que o agente calou o grupo (medido)")
    certo(re_["grupo_calados"] == 0,
          "Resulta: nenhuma — e zero aqui é uma MEDIÇÃO, não ausência de leitura")
    certo(af["conversas_com_agente"] == 0 and re_["conversas_com_agente"] == 0,
          "nenhuma conversa com fala do agente: o agente estava desligado")
    # 🔴 O NÚMERO FINAL de quem FALOU. Ele depende do discriminador do
    #    motor (`e_origem_humana`): sem ele, "só com pessoa" vira ZERO e a
    #    página diria que ninguém atendeu ninguém em dois dias inteiros.
    certo([d["atendidas"]["so_com_pessoa"] for d in _em("AutoFleet", corpo)["dias"]]
          == [60, 50] and
          [d["atendidas"]["so_com_pessoa"] for d in
           _em("Resulta Seguros", corpo)["dias"]] == [18, 35],
          "conversas só com pessoa por dia: AutoFleet 60/50 · Resulta 18/35")
    # 🔴 E o TOTAL de conversas que falaram no dia bate com a LENTE DO
    #    DADO (SELECT independente, subindo de `messages`): 64/53 e 25/38.
    certo([d["atendidas"]["conversas_mexidas"] for d in _em("AutoFleet", corpo)["dias"]]
          == [64, 53] and
          [d["atendidas"]["conversas_mexidas"] for d in
           _em("Resulta Seguros", corpo)["dias"]] == [25, 38],
          "conversas com mensagem no dia: AutoFleet 64/53 · Resulta 25/38 "
          "(os mesmos números da lente do dado)")
    certo(re_["silencios_total"] == 0 and af["silencios_total"] == 0,
          "nenhum silêncio do agente em 17–18/09 — o único do acervo é de OUTRO "
          "dia, e a medição não o puxa para dentro da janela")
    # 🔴 E ele APARECE no dia dele: a linha é real, o `detail` é real, e a
    #    classe sai do motor. Sem esta asserção, o zero acima seria indistinguível
    #    de "a medição não lê silêncio nenhum" (CLAUDE.md §9.3).
    linha = [l for l in CORPO["tabelas"]["agent_activities"]
             if l["title"] == TITULO_SILENCIO][0]
    dia_dele = datetime.fromisoformat(linha["created_at"]).astimezone(
        fuso_da_corretora()).date()
    dono = [n for n in NOMES if EMPRESAS[n] == linha["company_id"]][0]
    no_dia = _em(dono, medir_com(com(), nomes=[dono], de=dia_dele,
                                 ate=dia_dele))["agregado"]
    certo(no_dia["silencios_por_classe"] == {"janela": 1},
          "%s em %s: 1 silêncio do agente, classe 'janela' vinda do MOTOR"
          % (dono, dia_dele.isoformat()))
    certo(af["rajadas_coalescidas"] == 0 and re_["rajadas_coalescidas"] == 0,
          "nenhuma rajada fundida no recorte — o rastro existe e está vazio")


def bloco_2_reconciliacao():
    print("\n2. RECONCILIAÇÃO — a medição usa o MESMO contador das 19h")
    tz = fuso_da_corretora()
    cliente = ClienteDeCorpus(com())
    for nome in NOMES:
        cid = EMPRESAS[nome]
        do_motor = {"calados_total": 0, "acionamentos_entregues": 0,
                    "sinistros_com_dossie": 0}
        d = DE
        while d <= ATE:
            inicio, fim = limites_do_dia(d, tz)
            c = rodar(contagens_do_dia(_DB(cliente), cid, inicio, fim))
            for k in do_motor:
                do_motor[k] += int(c.get(k) or 0)
            d += timedelta(days=1)
        a = _em(nome, medir_com(com(), nomes=[nome]))["agregado"]
        certo(a["grupo_calados"] == do_motor["calados_total"],
              "%s: calados publicados == contagens_do_dia (%d)"
              % (nome, do_motor["calados_total"]))
        certo(a["acionamentos_entregues_motor"] == do_motor["acionamentos_entregues"],
              "%s: acionamentos entregues == o número das 19h" % nome)


def bloco_3_o_silencio_vem_do_produto():
    print("\n3. O TÍTULO E A CLASSE SÃO OS DO PRODUTO")
    fonte = io.open(os.path.join(RAIZ, "app", "services", "o_fim_do_atendimento.py"),
                    "r", encoding="utf-8").read()
    certo(('"%s"' % TITULO_SILENCIO) in fonte,
          "o título que a medição procura é o LITERAL que o produto escreve")
    esperados = CORPO.get("silencios_esperados") or []
    certo(bool(esperados), "o recorte trouxe pelo menos um silêncio real")
    from scripts.gerar_recorte_do_piloto import MOTIVO_SINTETICO
    todas = [c for c in MOTIVO_SINTETICO if c != "sem_motivo"]
    iguais = all(classe_do_silencio(MOTIVO_SINTETICO[c]) == c for c in todas)
    certo(iguais, "cada motivo sintético do dublê é classificado pelo MOTOR na "
                  "MESMA classe que ele representa (%d classes)" % len(todas))
    # CONTROLE: as classes CONSEGUEM ser diferentes — senão a igualdade acima
    # não provaria nada (CLAUDE.md §9.3).
    certo(len({classe_do_silencio(MOTIVO_SINTETICO[c]) for c in todas}) == len(todas),
          "CONTROLE: as classes são distintas entre si — o motor sabe discordar")


def bloco_4_zero_pii():
    print("\n4. G3 — ZERO PII, com um dublê que CARREGA PII")
    venenosas = {
        "conversations": [{"id": "c-veneno", "company_id": EMPRESAS[NOMES[0]],
                           "status": "open", "resolucao_motivo": None,
                           "resolvido_em": None, "updated_at": QUANDO,
                           "ficha_atendimento": {
                               "apolice_confirmada": True,
                               "nome": "Maria Aparecida da Silva",
                               "telefone": "+55 11 98765-4321",
                               "cpf": "123.456.789-09", "placa": "BRA2E19"}}],
        "agent_activities": [{"id": "aa-veneno", "company_id": EMPRESAS[NOMES[0]],
                              "category": "atendimentos", "title": TITULO_SILENCIO,
                              "detail": "Saionara Ferreira assumiu a conversa "
                                        "com o 11987654321",
                              "created_at": QUANDO}],
        "platform_sends": [{"id": "ps-veneno", "company_id": EMPRESAS[NOMES[0]],
                            "kind": KIND_PROTOCOLO, "created_at": QUANDO,
                            "phone": "5511987654321",
                            "summary": "protocolo 99 para joao@exemplo.com"}],
    }
    corpo = medir_com(com(venenosas))
    texto_md = em_markdown(corpo, comando="teste", gerado_em="17/09/2026")
    texto_js = json.dumps(corpo, ensure_ascii=False, sort_keys=True)
    achados = procurar_pii(texto_md) + procurar_pii(texto_js)
    certo(not achados, "nenhum telefone, CPF, placa ou e-mail na saída "
                       "(markdown + json) — achados: %s" % achados[:3])
    certo("Saionara" not in texto_md and "Saionara" not in texto_js,
          "o nome que estava no `detail` não atravessou o motor")
    # CONTROLE: a varredura CONSEGUE achar — senão ela não guarda nada.
    certo(len(procurar_pii(json.dumps(venenosas, ensure_ascii=False))) >= 3,
          "CONTROLE: a varredura acha a PII quando ela ESTÁ lá")
    # e o dado envenenado foi de fato LIDO (o silêncio dele entrou na conta)
    a = _em(NOMES[0], corpo)["agregado"]
    certo(a["silencios_total"] >= 1 and "takeover" in a["silencios_por_classe"],
          "a linha envenenada FOI lida: o silêncio virou classe 'takeover'")


def bloco_5_isolamento():
    print("\n5. G4 — ISOLAMENTO entre as duas corretoras REAIS")
    tabelas = com()
    junto = medir_com(tabelas)
    separado = {n: medir_com(tabelas, nomes=[n]) for n in NOMES}
    for nome in NOMES:
        certo(_em(nome, junto)["agregado"] == _em(nome, separado[nome])["agregado"],
              "%s: medida junto == medida sozinha" % nome)
    a, b = NOMES[0], NOMES[1]
    antes = _em(a, medir_com(tabelas, nomes=[a]))["agregado"]
    injetado = com({"platform_sends": envios(EMPRESAS[b], 9),
                    "agent_activities": handoffs(EMPRESAS[b], 4, 1)})
    depois = _em(a, medir_com(injetado, nomes=[a]))["agregado"]
    certo(antes == depois,
          "%d linhas da %s não mexem em NENHUM número da %s"
          % (14, b, a))
    do_b = _em(b, medir_com(injetado, nomes=[b]))["agregado"]
    certo(do_b["acionamentos_com_protocolo"] == 9 and do_b["handoffs_entregues"] == 4,
          "CONTROLE: as mesmas linhas APARECEM na corretora certa (9 e 4)")


def bloco_6_nao_avaliada_dos_dois_lados():
    print("\n6. G5 — NÃO AVALIADA consegue sair, e consegue NÃO sair")
    a = NOMES[0]
    cid = EMPRESAS[a]
    magro = _em(a, medir_com(com(), nomes=[a]))["regua"]
    certo(_dim(magro["atendimento"], "atendimento.aciona")["nota"] == NAO_AVALIADA,
          "sem acionamento nenhum: 'aciona' sai NÃO AVALIADA (amostra)")
    certo(_dim(magro["atendimento"],
               "atendimento.sabe_pedir_ajuda")["nota"] == NAO_AVALIADA,
          "🔴 sem pedido de ajuda nenhum: 'sabe pedir ajuda' NÃO dá 100")
    gordo_t = com({"platform_sends": envios(cid, 6),
                   "work_runs": runs(cid, 8),
                   "agent_activities": handoffs(cid, 7, 3)})
    gordo = _em(a, medir_com(gordo_t, nomes=[a]))["regua"]
    aciona = _dim(gordo["atendimento"], "atendimento.aciona")
    ajuda = _dim(gordo["atendimento"], "atendimento.sabe_pedir_ajuda")
    certo(aciona["nota"] == 75, "com 6 protocolos em 8 acionamentos: nota 75")
    certo(ajuda["nota"] == 70, "com 7 entregues de 10 pedidos: nota 70")
    certo(bool(aciona["criterio"]) and bool(ajuda["criterio"]),
          "toda dimensão com nota traz o CRITÉRIO escrito ao lado")
    semfonte = [d for d in magro["atendimento"]["dimensoes"] + magro["chat_principal"]["dimensoes"]
                if d["nota"] == NAO_AVALIADA and "amostra" not in d["fonte"]]
    certo(all(len(d["fonte"]) > 30 for d in semfonte),
          "toda dimensão sem fonte durável diz POR QUE (%d delas)" % len(semfonte))


def bloco_7_menos_dado_nunca_melhora():
    print("\n7. 🔴 G6 — MENOS DADO NUNCA MELHORA A NOTA")
    a = NOMES[0]
    cid = EMPRESAS[a]
    base_t = com({"platform_sends": envios(cid, 6), "work_runs": runs(cid, 8),
                  "agent_activities": handoffs(cid, 7, 3)})
    base = _em(a, medir_com(base_t, nomes=[a]))["regua"]

    def notas(regua):
        saida = {}
        for b in ("atendimento", "chat_principal"):
            for d in regua[b]["dimensoes"]:
                saida[d["chave"]] = d["nota"]
            saida[b] = regua[b]["nota"]
        return saida

    antes = notas(base)
    # 🔴 As linhas que, se removidas, PODEM subir a nota são exatamente as de
    #    FALHA — e o teste exige que a subida só aconteça por elas.
    falhas = {l["id"] for l in handoffs(cid, 0, 3)}
    falhas |= {l["id"] for l in runs(cid, 8)}          # acionamento sem protocolo
    subiu_indevido = []
    for tabela in ("platform_sends", "work_runs", "agent_activities",
                   "work_events", "conversations", "conversation_logs"):
        for linha in list(base_t[tabela])[:60]:
            depois = notas(_em(a, medir_com(
                com({"platform_sends": envios(cid, 6), "work_runs": runs(cid, 8),
                     "agent_activities": handoffs(cid, 7, 3)},
                    remover={tabela: [linha["id"]]}), nomes=[a]))["regua"])
            for chave, valor in depois.items():
                velho = antes.get(chave)
                if velho == NAO_AVALIADA and valor != NAO_AVALIADA:
                    subiu_indevido.append(("criou nota do nada", tabela,
                                           linha["id"], chave))
                elif velho != NAO_AVALIADA and valor != NAO_AVALIADA \
                        and int(valor) > int(velho) and linha["id"] not in falhas:
                    subiu_indevido.append(("subiu sem ser falha", tabela,
                                           linha["id"], chave))
    certo(not subiu_indevido,
          "remover qualquer linha nunca cria nota nem sobe nota — salvo remover "
          "uma FALHA. Violações: %s" % subiu_indevido[:3])
    # CONTROLE: remover uma FALHA de fato SOBE — senão a exceção acima seria
    # uma porta aberta que ninguém atravessa, e o guarda estaria vazio.
    sem_falha = notas(_em(a, medir_com(
        com({"platform_sends": envios(cid, 6), "work_runs": runs(cid, 8),
             "agent_activities": handoffs(cid, 7, 3)},
            remover={"agent_activities": ["aa-nok-0"]}), nomes=[a]))["regua"])
    certo(int(sem_falha["atendimento.sabe_pedir_ajuda"])
          > int(antes["atendimento.sabe_pedir_ajuda"]),
          "CONTROLE: remover uma FALHA sobe a nota (é a única subida legítima)")
    # e o vazio absoluto não dá 100 em lugar nenhum
    vazio = medir_com({"companies": CORPO["tabelas"]["companies"]}, nomes=[a])
    r = _em(a, vazio)["regua"]
    certo(all(d["nota"] == NAO_AVALIADA
              for b in ("atendimento", "chat_principal") for d in r[b]["dimensoes"]),
          "🔴 recorte VAZIO: TODAS as 11 dimensões saem NÃO AVALIADA — nenhuma "
          "vira 100 por não ter havido nada")


def bloco_8_o_dia_e_o_local():
    print("\n8. O DIA É O DIA LOCAL DA CORRETORA, E VEM DA MENSAGEM (B1)")
    a0 = NOMES[0]
    cid0 = EMPRESAS[a0]
    # 🔴 B1 — a conversa entra no dia em que ELA FALOU, não no dia em que
    #    alguém a tocou pela última vez. O `updated_at` daqui é D+2.
    conversa = {"id": "c-b1", "company_id": cid0, "status": "open",
                "resolucao_motivo": None, "resolvido_em": None,
                "updated_at": "2026-09-20T12:00:00+00:00",
                "ficha_atendimento": {"apolice_confirmada": False}}
    fala = {"id": "m-b1", "conversation_id": "c-b1", "role": "assistant",
            "payload": {"origem": ORIGEM_DO_AGENTE},
            "created_at": "2026-09-18T12:00:00+00:00"}
    t = com({"conversations": [conversa], "messages": [fala]})
    dias = {d["dia"]: d for d in _em(a0, medir_com(t, nomes=[a0]))["dias"]}
    certo(dias["2026-09-18"]["atendidas"]["com_agente"] == 1,
          "🔴 conversa com mensagem em 18/09 e `updated_at` em 20/09 CONTA "
          "no dia 18 — o dia é o da mensagem")
    certo(dias["2026-09-17"]["atendidas"]["com_agente"] == 0,
          "CONTROLE: e não aparece no dia 17, onde ela não falou")
    # 🔴 E um dia FECHADO não se mexe quando alguém toca a conversa depois:
    #    era isto que quebrava G2 (a mesma rodada dava outro número amanhã).
    antes = _em(a0, medir_com(com(), nomes=[a0]))["agregado"]
    futuro = com()
    for c_ in futuro["conversations"]:
        c_["updated_at"] = "2027-01-01T00:00:00+00:00"
    depois = _em(a0, medir_com(futuro, nomes=[a0]))["agregado"]
    certo(antes == depois,
          "mover o `updated_at` de TODAS as conversas para 2027 não muda "
          "NENHUM número de 17–18/09")
    certo(antes["conversas_mexidas"] > 0,
          "CONTROLE: e há conversas nesses dias (%d) — a igualdade acima não é "
          "de dois zeros" % antes["conversas_mexidas"])


def bloco_11_leitura_que_falha(_=None):
    print("\n11. 🔴 B4 — TABELA QUE NÃO FOI LIDA NÃO VIRA NOTA (nem zero)")
    a = NOMES[0]
    cid = EMPRESAS[a]
    extras = {"platform_sends": envios(cid, 5), "work_runs": runs(cid, 10),
              "agent_activities": handoffs(cid, 5, 5)}
    bom = _em(a, medir_com(com(extras), nomes=[a]))
    certo(_dim(bom["regua"]["atendimento"], "atendimento.aciona")["nota"] == 50,
          "com tudo lido: 5 protocolos de 10 acionamentos = 50")
    # 🔴 O defeito medido: com `work_runs` fora do ar a conta virava 5/5 = 100.
    for tabela, chave in (("work_runs", "atendimento.aciona"),
                          ("platform_sends", "atendimento.aciona"),
                          ("agent_activities", "atendimento.sabe_pedir_ajuda"),
                          ("work_events", "atendimento.coleta_e_age"),
                          ("conversation_logs", "chat.velocidade"),
                          ("agents", "chat.velocidade")):
        r = _em(a, medir_com(com(extras), nomes=[a], quebrada=tabela))["regua"]
        bloco = ("chat_principal" if chave.startswith("chat") else "atendimento")
        d = _dim(r[bloco], chave)
        certo(d["nota"] == NAO_AVALIADA,
              "`%s` fora do ar → `%s` sai NÃO AVALIADA, e não 100" % (tabela, chave))
    # e nenhuma nota SOBE com a tabela quebrada
    def notas(regua):
        return {d["chave"]: d["nota"] for b in ("atendimento", "chat_principal")
                for d in regua[b]["dimensoes"]}
    antes = notas(bom["regua"])
    for tabela in ("work_runs", "platform_sends", "agent_activities",
                   "work_events", "conversation_logs", "agents", "conversations",
                   "messages"):
        depois = notas(_em(a, medir_com(com(extras), nomes=[a],
                                        quebrada=tabela))["regua"])
        subiu = [k for k, v in depois.items()
                 if v != NAO_AVALIADA and antes.get(k) != NAO_AVALIADA
                 and int(v) > int(antes[k])]
        if subiu:
            certo(False, "nota SUBIU com `%s` fora do ar: %s" % (tabela, subiu))
            break
    else:
        certo(True, "🔴 nenhuma nota sobe quando QUALQUER das 8 tabelas falha")
    # e a célula do dia diz NÃO LIDO, não 0
    corpo = medir_com(com(extras), nomes=[a], quebrada="platform_sends")
    md = em_markdown(corpo, comando="teste", gerado_em="18/09/2026")
    certo("NÃO LIDO" in md and "não consegui ler" in md,
          "a tabela do dia mostra NÃO LIDO e a página explica que não foi lida")
    certo("NÃO LIDO" not in em_markdown(
        medir_com(com(extras), nomes=[a]), comando="t", gerado_em="x"),
        "CONTROLE: com tudo lido, nenhuma célula diz NÃO LIDO")

    # 🔴 O RESÍDUO DO B4: a nota sumia e a célula dizia NÃO LIDO, mas as
    #    frases 📊 do agregado e o MOTIVO da dimensão continuavam publicando
    #    ZERO com cara de medido — "amostra insuficiente (0 de 20)" culpa o
    #    piloto por um silêncio da CONSULTA.
    DEPENDENTES = {
        "agents": (["chat_perguntas", "chat_de_outros_agentes", "chat_p90_ms"],
                   ["Perguntas ao chat principal"], ["chat.velocidade"]),
        "conversation_logs": (["chat_perguntas", "chat_p90_ms"],
                              ["Perguntas ao chat principal"], ["chat.velocidade"]),
        "agent_activities": (["handoffs_entregues", "handoffs_sem_ninguem",
                              "silencios_total"],
                             ["Handoffs:"], ["atendimento.sabe_pedir_ajuda"]),
        "messages": (["conversas_com_agente", "conversas_so_com_pessoa"],
                     ["No período inteiro"], []),
        "conversations": (["conversas_com_agente", "conversas_so_com_pessoa"],
                          ["No período inteiro"], []),
    }
    problemas = []
    for tabela, (campos, frases, dims) in DEPENDENTES.items():
        corpo = medir_com(com(extras), nomes=[a], quebrada=tabela)
        bloco = _em(a, corpo)
        for campo in campos:
            if bloco["agregado"][campo] != "NÃO LIDO":
                problemas.append("%s: campo %s = %r" % (tabela, campo,
                                                        bloco["agregado"][campo]))
        texto = em_markdown(corpo, comando="t", gerado_em="x")
        for frase in frases:
            linha = [l for l in texto.splitlines() if frase in l][0]
            if "NÃO LIDO" not in linha:
                problemas.append("%s: frase %r ainda traz número" % (tabela, frase))
        for chave in dims:
            b = "chat_principal" if chave.startswith("chat") else "atendimento"
            fonte = _dim(bloco["regua"][b], chave)["fonte"]
            if "não consegui ler" not in fonte and "parou no teto" not in fonte:
                problemas.append("%s: motivo de %s é %r" % (tabela, chave,
                                                            fonte[:40]))
    certo(not problemas,
          "🔴 com CADA tabela fora do ar, nenhum campo do JSON, nenhuma frase "
          "📊 e nenhum motivo de dimensão traz número. Resíduos: %s"
          % problemas[:3])
    # CONTROLE: com tudo lido, a prosa traz os números de sempre.
    ok = em_markdown(medir_com(com(extras), nomes=[a]), comando="t",
                     gerado_em="x")
    certo("Handoffs: 5 entregues, 5 sem ninguém" in ok,
          "CONTROLE: com tudo lido a prosa diz 'Handoffs: 5 entregues, 5 sem "
          "ninguém' — os números voltam")


def bloco_12_o_chat_principal(_=None):
    print("\n12. 🔴 B2/B3/B6 — O CHAT PRINCIPAL, O P90 DO PERÍODO E A SOMA")
    a = NOMES[0]
    cid = EMPRESAS[a]
    core = [x["id"] for x in CORPO["tabelas"]["agents"]
            if x["company_id"] == cid and x["agent_role"] == "core"][0]
    outro = [x["id"] for x in CORPO["tabelas"]["agents"]
             if x["company_id"] == cid and x["agent_role"] != "core"][0]

    def log(i, agente, ms, quando):
        return {"id": "cl-%s-%d" % (agente[:4], i), "company_id": cid,
                "agent_id": agente, "status": "success",
                "response_time_ms": ms, "created_at": quando}

    # 🔴 B3: 24 perguntas rápidas no dia 17 e UMA lenta no dia 18. O "p90 do
    #    pior dia" antigo lia 31 s e dava 0; o p90 do PERÍODO lê a cauda real.
    rapidas = ([log(i, core, 1000, "2026-09-17T13:00:00+00:00") for i in range(22)]
               + [log(50 + i, core, 20000, "2026-09-17T13:00:00+00:00")
                  for i in range(2)])
    lenta = [log(99, core, 31000, "2026-09-18T13:00:00+00:00")]
    do_outro = [log(i, outro, 60000, "2026-09-17T13:00:00+00:00") for i in range(30)]
    r = _em(a, medir_com(com({"conversation_logs": rapidas + lenta + do_outro}),
                         nomes=[a]))
    vel = _dim(r["regua"]["chat_principal"], "chat.velocidade")
    certo(r["agregado"]["chat_perguntas"] == 25,
          "🔴 só as 25 perguntas do agente `core` contam (as 30 do atendimento "
          "ficam de fora)")
    certo(r["agregado"]["chat_de_outros_agentes"] == 30,
          "e as outras 30 aparecem como INFORMAÇÃO, com nome próprio")
    # 22×1s + 2×20s no dia 17 e 1×31s no dia 18.
    #   p90 do PERÍODO = 20.000 ms   (o certo)
    #   p90 do PIOR DIA = 31.000 ms  (o defeito antigo — um dia de 1 pergunta)
    #   MÍNIMO          =  1.000 ms  (o outro jeito de errar)
    certo(r["agregado"]["chat_p90_ms"] == 20000,
          "🔴 p90 do PERÍODO = 20.000 ms — não os 31.000 do 'pior dia' "
          "(1 pergunta) nem os 1.000 do mínimo")
    certo(vel["nota"] == 40, "logo a nota é 40 (0 pelo pior dia, 100 pelo mínimo)")
    certo("tempo do modelo" in vel["criterio"],
          "e o critério diz que é o tempo do MODELO, não o relógio da pessoa")
    # 🔴 B6: a soma dos estados atravessa os dias em vez de sobrescrever.
    certo(r["agregado"]["chat_estados"] == {"success": 25},
          "🔴 os estados do chat SOMAM os 2 dias (25), não sobrescrevem (1)")
    # CONTROLE: com só o agente do atendimento, a dimensão cai de amostra.
    so_outro = _em(a, medir_com(com({"conversation_logs": do_outro}),
                                nomes=[a]))["regua"]
    certo(_dim(so_outro["chat_principal"],
               "chat.velocidade")["nota"] == NAO_AVALIADA,
          "CONTROLE: 30 perguntas SÓ do atendimento = amostra 0 para o chat "
          "principal → NÃO AVALIADA")


def bloco_8b_o_dia_e_o_local():
    print("\n8b. O DIA LOCAL")
    a = NOMES[0]
    cid = EMPRESAS[a]
    # 02:00 UTC de 18/09 é 23:00 de 17/09 em São Paulo.
    t = com({"platform_sends": [{"id": "ps-vira", "company_id": cid,
                                 "kind": KIND_PROTOCOLO,
                                 "created_at": "2026-09-18T02:00:00+00:00"}]})
    dias = {d["dia"]: d for d in _em(a, medir_com(t, nomes=[a]))["dias"]}
    certo(dias["2026-09-17"]["acionamentos"]["com_protocolo"] == 1,
          "02:00 UTC de 18/09 conta no dia 17 — o dia da corretora, não o do UTC")
    certo(dias["2026-09-18"]["acionamentos"]["com_protocolo"] == 0,
          "CONTROLE: e não conta duas vezes")


def bloco_9_antes_de_14_nao_e_zero():
    print("\n9. ANTES DE 14/09 A MÉTRICA É 'NÃO MENSURÁVEL', E NÃO ZERO")
    a = NOMES[0]
    cid = EMPRESAS[a]
    conversa = {"id": "c-velha", "company_id": cid, "status": "open",
                "resolucao_motivo": None, "resolvido_em": None,
                "updated_at": "2026-09-10T12:00:00+00:00",
                "ficha_atendimento": {"apolice_confirmada": False}}
    fala = {"id": "m-velha", "conversation_id": "c-velha", "role": "assistant",
            "payload": {"origem": ORIGEM_DO_AGENTE},
            "created_at": "2026-09-10T12:00:00+00:00"}
    t = com({"conversations": [conversa], "messages": [fala]})
    velho = _em(a, medir_com(t, nomes=[a], de=date(2026, 9, 10),
                             ate=date(2026, 9, 10)))["dias"][0]
    certo(velho["atendidas"]["com_agente"] == NAO_MENSURAVEL,
          "10/09: NÃO MENSURÁVEL — o produto não marcava quem respondeu")
    certo(len(velho["atendidas"]["porque"]) > 30, "e diz por quê")
    novo = {**conversa, "id": "c-nova", "updated_at": "2026-09-17T12:00:00+00:00"}
    fala_nova = {**fala, "id": "m-nova", "conversation_id": "c-nova",
                 "created_at": "2026-09-17T12:00:00+00:00"}
    t2 = com({"conversations": [novo], "messages": [fala_nova]})
    dia17 = [d for d in _em(a, medir_com(t2, nomes=[a]))["dias"]
             if d["dia"] == "2026-09-17"][0]
    certo(dia17["atendidas"]["com_agente"] == 1,
          "CONTROLE: 17/09 a MESMA fala é contada — a marca de origem existe")


def bloco_10_o_bloco_so_com_maioria():
    print("\n10. A NOTA DO BLOCO SÓ SAI COM A MAIORIA AVALIADA")
    a = NOMES[0]
    cid = EMPRESAS[a]
    t = com({"platform_sends": envios(cid, 6), "work_runs": runs(cid, 8),
             "agent_activities": handoffs(cid, 7, 3)})
    r = _em(a, medir_com(t, nomes=[a]))["regua"]
    avaliadas = [d for d in r["atendimento"]["dimensoes"] if d["nota"] != NAO_AVALIADA]
    certo(len(avaliadas) == 2 and r["atendimento"]["nota"] == NAO_AVALIADA,
          "2 de 6 dimensões avaliadas: o BLOCO sai NÃO AVALIADA")
    certo("6" in r["atendimento"]["porque"], "e diz quantas de quantas")
    # CONTROLE: com a maioria avaliada, a nota do bloco SAI.
    forcado = regua_por_dimensao(somar_os_dias([]))
    forcado["atendimento"]["dimensoes"] = [
        {"chave": "x%d" % i, "nota": 80, "criterio": "", "fonte": "", "n": 9,
         "n_minimo": 5, "palpite_antigo": None} for i in range(4)] + \
        forcado["atendimento"]["dimensoes"][:2]
    from scripts.medir_o_piloto import _bloco
    b = _bloco(forcado["atendimento"]["dimensoes"], "controle")
    certo(b["nota"] == 80,
          "CONTROLE: com 4 de 6 avaliadas a nota do bloco SAI (80)")


_SIMULA_O_CONTEINER = r'''
import runpy, sys
from datetime import date

class BloqueiaPortalWorker:
    """O `/app` da imagem do smith-api: `portal_worker` nao existe la dentro."""
    def find_spec(self, nome, caminho=None, alvo=None):
        if nome == "portal_worker" or nome.startswith("portal_worker."):
            raise ImportError("No module named 'portal_worker' (conteiner simulado)")
        return None

sys.meta_path.insert(0, BloqueiaPortalWorker())
MOD = runpy.run_path(sys.argv[1], run_name="dentro_do_conteiner")
print("IMPORTOU=1")
HOJE = date(2026, 9, 20)
print("PADRAO=%s..%s" % MOD["janela_padrao"](hoje=HOJE))
print("DIAS3=%s..%s" % MOD["janela_padrao"](dias=3, hoje=HOJE))
print("SO_DE=%s..%s" % MOD["janela_padrao"](date(2026, 9, 1), hoje=HOJE))
'''


def bloco_13_o_ambiente_do_conteiner():
    """🔴 G-P13 — a medição tem de RODAR onde o Founder a roda.

    📊 Em 20/09/2026 o script vizinho (`conferir_o_que_esta_no_ar.py`) morreu no
    console do EasyPanel com `ModuleNotFoundError: portal_worker` — um import
    que TODO teste via existir, porque todo teste roda da árvore do repositório.
    Este guarda monta o mundo de lá: `portal_worker` bloqueado no `meta_path` e
    `cwd` fora do repositório. ⛔ Só leitura: nada de banco, nada de rede.
    """
    print("\n[13] o ambiente de uso — o conteiner, simulado")
    import subprocess
    import tempfile
    caminho = os.path.join(RAIZ, "scripts", "medir_o_piloto.py")
    # 🔴 NO CONTÊINER AS VARIÁVEIS VÊM DO AMBIENTE, não de um arquivo. 📊 Sem
    #    isto o gate falhava por um motivo FALSO: `app.core.config` lê o `.env`
    #    pelo CWD, e com o cwd fora da árvore ele acusava `MINIO_ROOT_USER
    #    Field required`. Lá dentro o EasyPanel exporta as variáveis; aqui,
    #    quem as exporta é o `.env` da árvore, lido e passado por `env=`.
    from dotenv import dotenv_values
    ambiente = {**os.environ,
                **{k: v for k, v in dotenv_values(
                    os.path.join(RAIZ, ".env")).items() if v is not None},
                "PYTHONIOENCODING": "utf-8"}
    with tempfile.TemporaryDirectory() as longe:
        r = subprocess.run([sys.executable, "-c", _SIMULA_O_CONTEINER, caminho],
                           cwd=longe, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=180,
                           env=ambiente)
    saida = (r.stdout or "") + (r.stderr or "")
    certo("ModuleNotFoundError" not in saida and "IMPORTOU=1" in saida,
          "sem `portal_worker` e fora do repositório, o script CARREGA%s"
          % ("" if "IMPORTOU=1" in saida else " → " + saida[-400:]))
    # 🔴 A JANELA PADRÃO, calculada LÁ DENTRO, com o relógio FIXO.
    certo("PADRAO=2026-09-13..2026-09-19" in saida,
          "sem datas: os 7 dias FECHADOS, até ONTEM (13→19, com hoje=20)")
    certo("DIAS3=2026-09-17..2026-09-19" in saida,
          "--dias 3: 17→19, e nunca o dia de hoje")
    certo("SO_DE=2026-09-01..2026-09-19" in saida,
          "--de sozinho vai até ontem")
    # CONTROLE: o relógio é REALMENTE injetado — outro hoje, outra janela.
    certo(janela_padrao(hoje=date(2026, 9, 21)) == (date(2026, 9, 14),
                                                    date(2026, 9, 20)),
          "CONTROLE: com hoje=21 a janela anda um dia (14→20)")
    certo(janela_padrao(date(2026, 9, 5), date(2026, 9, 6), 99,
                        hoje=date(2026, 9, 20)) == (date(2026, 9, 5),
                                                    date(2026, 9, 6)),
          "CONTROLE: com as DUAS datas escritas, --dias não manda em nada")


def test_o_piloto_e_medido():
    for bloco in (bloco_1_o_fio, bloco_2_reconciliacao,
                  bloco_3_o_silencio_vem_do_produto, bloco_4_zero_pii,
                  bloco_5_isolamento, bloco_6_nao_avaliada_dos_dois_lados,
                  bloco_7_menos_dado_nunca_melhora, bloco_8_o_dia_e_o_local,
                  bloco_9_antes_de_14_nao_e_zero, bloco_10_o_bloco_so_com_maioria,
                  bloco_11_leitura_que_falha, bloco_12_o_chat_principal,
                  bloco_13_o_ambiente_do_conteiner):
        bloco()
    print("\n%s  %d verdes · %d vermelhas" % ("=" * 60, OK, FAIL))
    assert not FAIL, "guardas vermelhos: %s" % FALHAS


if __name__ == "__main__":
    try:
        test_o_piloto_e_medido()
    except AssertionError as erro:
        print(erro)
        sys.exit(1)
    sys.exit(0)
