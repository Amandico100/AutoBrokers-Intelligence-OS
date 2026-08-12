# -*- coding: utf-8 -*-
"""A cobranca da Tokio Marine le o relatorio certo e nao gera boleto proibido.

UTF-8 e nao ASCII pelo mesmo motivo do vizinho: as secoes [3] e [6] comparam
TEXTO que gente le -- o motivo de retencao e a forma de pagamento vem do portal
com acento (`DEBITO` sai como `D&#201;BITO` no XML). Um teste que so consegue
afirmar sobre texto sem acento nao guarda o texto que sai de verdade.

O que estes testes seguram
==========================
Cada um nasceu de uma coisa que ja quebrou, ou que quebraria na primeira vez:

    [1] a testemunha        o relatorio DIZ quantas parcelas mandou. Se o
                            parser ler menos, a varredura para -- em vez de
                            afirmar "carteira em dia" por engano.
    [2] a parcela certa     CLARISSE tem as parcelas 3 E 4 `Pendente`. Pegar
                            "a primeira pendente" gera boleto da parcela errada.
                            Foi exatamente o que aconteceu na captura real.
    [3] debito nunca vira   gerar boleto em parcela de DEBITO queima a unica
                            troca de forma de pagamento da vigencia.
    [4] repique = S segura  a Tokio ainda vai tentar debitar; as atendentes
                            esperam esgotar (decisao do founder, 12/08/2026).
    [5] carencia de 48 h    quem vence amanha nao e inadimplente.
    [6] o menor acrescimo   entre as datas oferecidas, a mais proxima.
    [7] telefone do portal  NUNCA vira destinatario de WhatsApp.
    [8] rotas proibidas     nenhuma tela que escreve aparece no codigo.

CLAUDE.md 9.3 -- um guarda que nao tem como falhar nao guarda nada. Por isso a
fixture tem um relatorio TRUNCADO (secao 1) e duas parcelas pendentes (secao 2):
os dois casos CONSEGUEM ser diferentes do esperado.
"""
from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

PASS = FAIL = 0


def check(nome, condicao, extra=""):
    global PASS, FAIL
    if condicao:
        PASS += 1
        print("  [ok] " + nome)
    else:
        FAIL += 1
        print("  [FALHOU] " + nome + ("  " + str(extra)[:220] if extra else ""))


def _load(nome, caminho):
    spec = importlib.util.spec_from_file_location(nome, str(ROOT / caminho))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


tk = _load("tokio_corretor", "portal_worker/journeys/tokio_corretor.py")
from fixtures import tokio_inadimplentes as fx  # noqa: E402

AGORA = datetime.now(timezone.utc)
VENC_ATRASADA = (AGORA - timedelta(days=30)).strftime("%d/%m/%Y")
VENC_AMANHA = (AGORA + timedelta(days=1)).strftime("%d/%m/%Y")
XML = fx.relatorio(VENC_ATRASADA, VENC_AMANHA)
ITENS = tk.extrair_inadimplentes(XML)


# ==========================================================================
print("\n[1] A TESTEMUNHA — o relatorio diz quantas mandou")
# ==========================================================================
totais = tk.totais_do_relatorio(XML)
check("le quantidadeParcelas", totais["parcelas"] == "4", totais)
check("le quantidadeClientes", totais["clientes"] == "4", totais)
check("le valorPremios como numero", abs((totais["premios"] or 0) - 2371.09) < 0.01, totais)
check("parser leu tudo que o documento declara", len(ITENS) == 4, len(ITENS))
check("com o numero batendo, nao ha divergencia",
      tk._conferir_testemunha(XML, ITENS) is None)

# O guarda CONSEGUE falhar — senao nao guarda nada.
XML_TRUNCADO = fx.relatorio(VENC_ATRASADA, VENC_AMANHA, truncado=True)
divergencia = tk._conferir_testemunha(XML_TRUNCADO, tk.extrair_inadimplentes(XML_TRUNCADO))
check("relatorio que declara 7 e entrega 4 e RECUSADO", bool(divergencia), divergencia)
check("a recusa diz os dois numeros", divergencia and "7" in divergencia and "4" in divergencia,
      divergencia)
check("a recusa NAO afirma nada sobre a carteira",
      divergencia and "nao afirmo" in divergencia.lower(), divergencia)


# ==========================================================================
print("\n[2] A PARCELA CERTA — duas pendentes, so uma e a do relatorio")
# ==========================================================================
linhas = tk.extrair_parcelas_do_detalhe(fx.DETALHE_HTML)
check("leu as 4 linhas da tabela", len(linhas) == 4, len(linhas))
check("as pagas nao tem botao de boleto",
      [l["tem_botao_boleto"] for l in linhas] == [False, False, True, True],
      [(l["parcela"], l["tem_botao_boleto"]) for l in linhas])
check("duas parcelas estao Pendente",
      sum(1 for l in linhas if l["situacao"].lower() == "pendente") == 2,
      [l["situacao"] for l in linhas])

escolhida = tk.escolher_parcela(linhas, "3")
check("a parcela 3 traz o titulo 7200000003",
      escolhida and escolhida["numero_titulo"] == "7200000003", escolhida)
outra = tk.escolher_parcela(linhas, "4")
check("a parcela 4 traz OUTRO titulo", outra and outra["numero_titulo"] == "7200000004", outra)
check("os dois titulos CONSEGUEM ser diferentes",
      escolhida["numero_titulo"] != outra["numero_titulo"])
check("pedir uma parcela que nao existe devolve nada",
      tk.escolher_parcela(linhas, "9") is None)
check("pedir uma parcela PAGA devolve nada (nao tem botao)",
      tk.escolher_parcela(linhas, "1") is None)


# ==========================================================================
print("\n[3] DEBITO NUNCA VIRA BOLETO — queima a troca da vigencia")
# ==========================================================================
por_nome = {i["cliente_nome"].split()[0]: i for i in ITENS}
check("os 4 casos da fixture chegaram", sorted(por_nome) ==
      ["ARINALDO", "BENEDITA", "CLARISSE", "DOMINGOS"], sorted(por_nome))

debito = por_nome["BENEDITA"]
check("a forma de pagamento com acento foi decodificada",
      "DÉBITO" in debito["forma_pagamento"], debito["forma_pagamento"])
check("DEBITO nao gera boleto", debito["gera_boleto"] is False)
motivo_debito = tk.motivo_para_reter(debito)
check("DEBITO e retido", bool(motivo_debito), motivo_debito)
check("o motivo carrega a marca que o servico reconhece",
      tk.MARCA_REGRA in motivo_debito, motivo_debito)
check("o motivo carrega o que o portal disse",
      "INSUFICIENCIA DE FUNDOS" in motivo_debito, motivo_debito)

ficha = por_nome["ARINALDO"]
check("FICHA gera boleto", ficha["gera_boleto"] is True)
check("FICHA sem repique NAO e retida", tk.motivo_para_reter(ficha) == "",
      tk.motivo_para_reter(ficha))
check("FICHA e DEBITO CONSEGUEM ser diferentes",
      ficha["gera_boleto"] != debito["gera_boleto"])


# ==========================================================================
print("\n[4] REPIQUE = S SEGURA — a Tokio ainda vai tentar debitar")
# ==========================================================================
check("o repique foi lido", debito["repique"] == "S", debito["repique"])
check("repique N nos demais", [i["repique"] for i in ITENS].count("N") == 3,
      [i["repique"] for i in ITENS])

# Um FICHA com repique S tambem segura — a regra nao e "so debito".
ficha_repique = dict(ficha, repique="S")
motivo = tk.motivo_para_reter(ficha_repique)
check("FICHA com repique S tambem e retida", bool(motivo), motivo)
check("e o motivo fala de esgotar o debito", "esgotar" in motivo.lower(), motivo)
check("o mesmo item sem repique passa", tk.motivo_para_reter(dict(ficha, repique="N")) == "")


# ==========================================================================
print("\n[5] CARENCIA DE 48 H — quem vence amanha nao e inadimplente")
# ==========================================================================
atrasados = [i for i in ITENS if tk.vencido_ha_mais_de(i["vencimento"], 48)]
check("3 dos 4 estao vencidos ha mais de 48h", len(atrasados) == 3,
      [(i["cliente_nome"], i["vencimento"]) for i in atrasados])
check("quem vence amanha ficou de fora",
      "DOMINGOS" not in [i["cliente_nome"].split()[0] for i in atrasados])
check("vencido ha 30 dias passa", tk.vencido_ha_mais_de(
    (AGORA - timedelta(days=30)).strftime("%Y-%m-%d"), 48))
check("vencido ha 10 horas NAO passa", tk.vencido_ha_mais_de(
    AGORA.strftime("%Y-%m-%d"), 48) is False)
check("vencimento vazio nao passa", tk.vencido_ha_mais_de("", 48) is False)
check("vencimento sujo nao explode", tk.vencido_ha_mais_de("nao e data", 48) is False)


# ==========================================================================
print("\n[6] O MENOR ACRESCIMO — entre as datas oferecidas, a mais proxima")
# ==========================================================================
escolha = tk.escolher_vencimento(fx.PRORROGACAO_VENCIDA)
check("escolheu a data mais proxima", escolha["dataComparacao"] == "2026-08-14", escolha)
check("que e tambem a de menor valor total",
      escolha["valorTotalProrrogacao"] == min(
          d["valorTotalProrrogacao"] for d in fx.PRORROGACAO_VENCIDA["ListaVencimentosProrrogacao"]),
      escolha)
check("a lista tinha alternativas MAIS CARAS (o teste consegue falhar)",
      len(fx.PRORROGACAO_VENCIDA["ListaVencimentosProrrogacao"]) == 3
      and escolha["dataComparacao"] != "2026-08-27")
check("a data original ja vencida NAO estava entre as opcoes",
      "2026-08-10" not in [d["dataComparacao"]
                           for d in fx.PRORROGACAO_VENCIDA["ListaVencimentosProrrogacao"]])

limpa = tk.escolher_vencimento(fx.PRORROGACAO_LIMPA)
check("parcela a vencer: multa e juros zero", limpa["valorMulta"] == 0 and limpa["valorJuros"] == 0)
check("lista vazia devolve vazio, sem explodir",
      tk.escolher_vencimento(fx.PRORROGACAO_RECUSADA) == {})
check("resposta sem a chave devolve vazio", tk.escolher_vencimento({}) == {})

# Nao recalculamos juros: o numero e o que a Tokio imprime.
fonte = (ROOT / "portal_worker" / "journeys" / "tokio_corretor.py").read_text(encoding="utf-8")
check("o codigo NAO tem formula de multa de 2%", "0.02" not in fonte and "* 2 /" not in fonte)
check("o codigo NAO tem formula de juros ao dia", "0.116667" not in fonte)


# ==========================================================================
print("\n[7] O TELEFONE DO PORTAL NUNCA VIRA DESTINATARIO")
# ==========================================================================
check("nenhum item tem a chave 'whatsapp'", all("whatsapp" not in i for i in ITENS),
      [k for i in ITENS for k in i if "whats" in k.lower()])
check("os telefones ficam num campo com nome que avisa",
      all("telefones_portal" in i for i in ITENS))
check("e sao lidos de verdade (ddd + numero)",
      por_nome["CLARISSE"]["telefones_portal"] == ["4899990003", "48991310003"],
      por_nome["CLARISSE"]["telefones_portal"])
check("o cpf_cnpj vai limpo — e por ele que o sistema de gestao acha o WhatsApp",
      por_nome["ARINALDO"]["cpf_cnpj"] == "11122233344", por_nome["ARINALDO"]["cpf_cnpj"])
check("CNPJ tambem sai com 14 digitos",
      por_nome["DOMINGOS"]["cpf_cnpj"] == "44555666000177", por_nome["DOMINGOS"]["cpf_cnpj"])
check("a docstring avisa que os telefones do portal discordam entre si",
      "999381576" in fonte and "991314388" in fonte)


# ==========================================================================
print("\n[8] ROTAS PROIBIDAS — nada que escreve aparece no codigo")
# ==========================================================================
executavel = "\n".join(l for l in fonte.splitlines()
                       if not l.strip().startswith("#"))
for rota in tk.ROTAS_PROIBIDAS:
    # a constante em si conta uma vez; qualquer segunda ocorrencia e uso
    check("nao ha chamada para " + rota, executavel.count(rota) <= 1,
          executavel.count(rota))
check("a lista de proibidas nao esta vazia", len(tk.ROTAS_PROIBIDAS) >= 4)
check("o endpoint de e-mail do relatorio esta na lista",
      any("email" in r for r in tk.ROTAS_PROIBIDAS))


# ==========================================================================
print("\n[9] A URL DO DETALHE — a ponte entre o relatorio e o titulo")
# ==========================================================================
url = tk.url_detalhe("008.614.499-59", "75111063")
check("monta o caminho medido no HAR",
      url == "/portais/visao-cliente-corretor/detalhe/apolice/00861449959/75111063?cdpn=null", url)
check("preserva os zeros a esquerda do CPF", "/00861449959/" in url, url)
check("CNPJ vai com 14 digitos",
      "/44555666000177/" in tk.url_detalhe("44.555.666/0001-77", "70000004"))


# ==========================================================================
print("\n[10] O REGISTRO — a Tokio existe para o resto do sistema")
# ==========================================================================
from portal_worker.journeys import get_journey, portais_com_cobranca, tem_cobranca  # noqa: E402

check("tokiomarine_corretor sabe varrer cobranca", tem_cobranca("tokiomarine_corretor"))
check("resolve a funcao real", callable(get_journey("tokiomarine_corretor", "cobranca_sweep")))
check("resolve o login_check", callable(get_journey("tokiomarine_corretor", "login_check")))
check("esta na lista de portais com cobranca",
      "tokiomarine_corretor" in portais_com_cobranca(), portais_com_cobranca())
check("e a lista tem as tres seguradoras",
      {"allianz_corretor", "hdi_corretor", "tokiomarine_corretor"} <= set(portais_com_cobranca()),
      portais_com_cobranca())

bc = _load("billing_collection", "app/services/billing_collection.py")
check("entra sozinha no padrao da varredura",
      "tokiomarine_corretor" in bc.DEFAULT_PORTAL_KEYS, bc.DEFAULT_PORTAL_KEYS)
check("tem nome legivel para a mensagem do grupo",
      bc._portal_insurer_name({"portal": "tokiomarine_corretor"}, {}) == "TOKIO MARINE")
check("e o nome difere do da HDI (o teste consegue falhar)",
      bc._portal_insurer_name({"portal": "tokiomarine_corretor"}, {})
      != bc._portal_insurer_name({"portal": "hdi_corretor"}, {}))


# ==========================================================================
print("\n[11] O ITEM RETIDO CHEGA NA TAREFA HUMANA")
# ==========================================================================
retido = dict(debito, sem_boleto_motivo=tk.motivo_para_reter(debito))
check("o servico reconhece o item como sem boleto por regra",
      bc.sem_boleto_por_regra(retido), retido.get("sem_boleto_motivo"))
check("e um item normal NAO e reconhecido como tal",
      bc.sem_boleto_por_regra(dict(ficha, sem_boleto_motivo="")) is False)

print("\n" + "=" * 62)
print("  Tokio Marine: %d asserções verdes, %d vermelhas" % (PASS, FAIL))
print("=" * 62)
sys.exit(1 if FAIL else 0)
