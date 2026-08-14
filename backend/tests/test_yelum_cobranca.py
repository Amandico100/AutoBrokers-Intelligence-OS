# -*- coding: utf-8 -*-
"""A cobranca da Yelum le a janela certa e sabe quando NAO viu tudo.

UTF-8 e nao ASCII: as secoes [3] e [5] comparam o TEXTO que a atendente le, e
ele vem do portal com acento ("Debito em conta", "Cartao de credito").

O que estes testes seguram
==========================
    [1] a testemunha        o contador NAO tem filtro de data e a busca TEM.
                            Se o contador diz mais, ficou gente para tras.
    [2] os dois formatos    a MESMA API devolve "1.672,62" num endpoint e
                            "1672.62" noutro. Ler errado e errar mil vezes.
    [3] debito e cartao     nunca viram boleto.
    [4] a carencia de 48h   quem vence amanha nao e inadimplente.
    [5] o telefone          o portal manda vazio; o WhatsApp vem da gestao.
    [6] a URL do boleto     tres chaves da lista, sem passo intermediario.
    [7] rotas proibidas     nada que escreve aparece no codigo.
    [8] o token             so o FORMATO vai para a evidencia, nunca o valor.

CLAUDE.md 9.3 -- um guarda que nao tem como falhar nao guarda nada. Por isso a
fixture tem CONTADOR e CONTADOR_MAIOR: os dois casos conseguem ser diferentes.
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


yl = _load("yelum_corretor", "portal_worker/journeys/yelum_corretor.py")
from fixtures import yelum_parcelas as fx  # noqa: E402

AGORA = datetime.now(timezone.utc)
VENC_ATRASADA = (AGORA - timedelta(days=30)).strftime("%Y-%m-%dT03:00:00.000Z")
VENC_AMANHA = (AGORA + timedelta(days=1)).strftime("%Y-%m-%dT03:00:00.000Z")
LISTA = fx.lista(VENC_ATRASADA, VENC_AMANHA)
ITENS = yl.extrair_inadimplentes(LISTA)
por_nome = {i["cliente_nome"].split()[0]: i for i in ITENS}


# ==========================================================================
print("\n[1] A TESTEMUNHA — duas fontes independentes tem que bater")
# ==========================================================================
check("leu os 4 registros", len(ITENS) == 4, len(ITENS))
check("o contador do portal nao tem filtro de data", "filter=count" in yl.EP_CONTA_ATRASADAS
      and "Due" not in yl.EP_CONTA_ATRASADAS, yl.EP_CONTA_ATRASADAS)
check("contador 4 e lista 4: sem divergencia",
      yl.conferir_testemunha(fx.CONTADOR["Total"], ITENS, 89) is None)

div = yl.conferir_testemunha(fx.CONTADOR_MAIOR["Total"], ITENS, 89)
check("contador 9 e lista 4: RECUSADO", bool(div), div)
check("a recusa diz os dois numeros", div and "9" in div and "4" in div, div)
check("a recusa explica que as que faltam sao mais velhas",
      div and "velhas" in div.lower(), div)
check("a recusa NAO afirma nada sobre a carteira",
      div and "nao afirmo" in div.lower(), div)
check("contador ausente nao inventa falha", yl.conferir_testemunha(None, ITENS, 89) is None)
check("contador MENOR que a lista nao e falha (o portal e que atrasa)",
      yl.conferir_testemunha(1, ITENS, 89) is None)

# A janela: de N dias atras ate ONTEM — nunca hoje, que a tela nao aceita.
j = yl.janela_de_busca(89, agora=AGORA)
check("a janela termina ONTEM", j["lte"][:10] == (AGORA - timedelta(days=1)).strftime("%Y-%m-%d"), j)
check("e comeca 89 dias antes", j["gte"][:10] == (AGORA - timedelta(days=89)).strftime("%Y-%m-%d"), j)
check("o formato e o que a API pede", j["gte"].endswith("T00:00:00.000Z")
      and j["lte"].endswith("T23:59:59.000Z"), j)


# ==========================================================================
print("\n[2] OS DOIS FORMATOS DE VALOR — da MESMA API")
# ==========================================================================
check("le o formato brasileiro da lista", por_nome["ARINALDO"]["valor"] == 1672.62,
      por_nome["ARINALDO"]["valor"])
check("le tambem o formato com ponto (getPaymentInstallments)",
      yl._valor(fx.PARCELAS_DA_APOLICE["response"][1]["Amount"]) == 1672.62)
check("os dois textos sao DIFERENTES e dao o mesmo numero",
      fx.PARCELAS_DA_APOLICE["response"][1]["Amount"] != LISTA["response"][0]["Amount"]
      and yl._valor("1672.62") == yl._valor("1.672,62"))
check("valor de milhar nao vira centavo", yl._valor("1.229,63") == 1229.63)
check("valor vazio devolve None", yl._valor("") is None)
check("IOF tambem e lido", por_nome["ARINALDO"]["iof"] == 114.96, por_nome["ARINALDO"]["iof"])

# A data: o portal manda 03:00Z, que e meia-noite de Brasilia. Cortar preserva
# o DIA que a tela mostra; converter fuso moveria um dia para tras.
check("a data preserva o dia da tela",
      yl._data_iso("2026-08-08T03:00:00.000Z") == "2026-08-08")
check("data ausente devolve vazio", yl._data_iso(None) == "")


# ==========================================================================
print("\n[3] DEBITO E CARTAO NUNCA VIRAM BOLETO")
# ==========================================================================
check("os 4 casos chegaram", sorted(por_nome) ==
      ["ARINALDO", "BENEDITA", "CLARISSE", "DOMINGOS"], sorted(por_nome))
check("FB gera boleto", por_nome["ARINALDO"]["gera_boleto"] is True)
check("DC nao gera", por_nome["BENEDITA"]["gera_boleto"] is False)
check("CC nao gera", por_nome["CLARISSE"]["gera_boleto"] is False)
check("FB e DC CONSEGUEM ser diferentes",
      por_nome["ARINALDO"]["gera_boleto"] != por_nome["BENEDITA"]["gera_boleto"])

m_dc = yl.motivo_para_reter(por_nome["BENEDITA"])
check("DC e retido", bool(m_dc), m_dc)
check("o motivo carrega a marca que o servico reconhece", yl.MARCA_REGRA in m_dc, m_dc)
check("e diz a forma por extenso, com acento", "Débito em conta" in m_dc, m_dc)
check("e carrega o motivo que a Yelum deu", "SALDO INSUFICIENTE" in m_dc, m_dc)

m_cc = yl.motivo_para_reter(por_nome["CLARISSE"])
check("CC tambem e retido, com o motivo dele", "CARTAO EXPIRADO" in m_cc, m_cc)
check("FB NAO e retido", yl.motivo_para_reter(por_nome["ARINALDO"]) == "")
check("as formas sem boleto estao declaradas",
      set(yl.FORMAS_SEM_BOLETO) == {"DC", "CC"} and yl.FORMA_COM_BOLETO == "FB")


# ==========================================================================
print("\n[4] CARENCIA DE 48 H")
# ==========================================================================
atrasados = [i for i in ITENS if yl.vencido_ha_mais_de(i["vencimento"], 48)]
check("3 dos 4 estao vencidos ha mais de 48h", len(atrasados) == 3,
      [(i["cliente_nome"], i["vencimento"]) for i in atrasados])
check("quem vence amanha ficou de fora",
      "DOMINGOS" not in [i["cliente_nome"].split()[0] for i in atrasados])
check("vencido hoje NAO passa",
      yl.vencido_ha_mais_de(AGORA.strftime("%Y-%m-%d"), 48) is False)
check("vencimento sujo nao explode", yl.vencido_ha_mais_de("nao e data", 48) is False)


# ==========================================================================
print("\n[5] O TELEFONE DO PORTAL VEM VAZIO — o WhatsApp vem da gestao")
# ==========================================================================
cli = fx.CLIENTE["response"][0]
check("o registro real traz e-mail preenchido", bool(cli["EmailAddress"]))
check("e telefone VAZIO nos dois campos",
      cli["TelephoneAreaCode"] == "" and cli["TelePhoneNumber"] == "")
check("nenhum item sai com a chave 'whatsapp'", all("whatsapp" not in i for i in ITENS))
check("a lista de inadimplentes nem traz documento",
      all(i["cpf_cnpj"] == "" for i in ITENS))
fonte = (ROOT / "portal_worker" / "journeys" / "yelum_corretor.py").read_text(encoding="utf-8")
check("o codigo busca o documento no endpoint de cliente",
      "searchCustomerPolicy" in fonte and "CustomerID" in fonte)
check("a docstring registra que o telefone vem vazio",
      "TelephoneAreaCode" in fonte and "TelePhoneNumber" in fonte)


# ==========================================================================
print("\n[6] A URL DO BOLETO — tres chaves, nenhum passo intermediario")
# ==========================================================================
u = yl.url_do_boleto(por_nome["ARINALDO"])
check("monta o caminho medido no HAR",
      u == "/printdoc/policy/600000000000101/issuance/2?installmentID=2", u)
check("usa a apolice como ela veio (sem tirar zeros)",
      "600000000000101" in u, u)
outra = yl.url_do_boleto(por_nome["DOMINGOS"])
check("emissao e parcela mudam com o item",
      "issuance/3" in outra and "installmentID=11" in outra, outra)
check("as duas URLs CONSEGUEM ser diferentes", u != outra)
check("o recibo junta as tres chaves",
      por_nome["ARINALDO"]["recibo"] == "600000000000101-2-2",
      por_nome["ARINALDO"]["recibo"])
check("nao existe passo de GERAR boleto no codigo",
      "gerarBoleto" not in fonte and "prorrogacao" not in fonte)


# ==========================================================================
print("\n[7] ROTAS PROIBIDAS — nada que escreve aparece no codigo")
# ==========================================================================
executavel = "\n".join(l for l in fonte.splitlines() if not l.strip().startswith("#"))
for rota in yl.ROTAS_PROIBIDAS:
    check("nao ha chamada para " + rota, executavel.count(rota) <= 1, executavel.count(rota))
check("a lista de proibidas nao esta vazia", len(yl.ROTAS_PROIBIDAS) >= 4)
check("reprogramar boleto esta na lista", any("reschedule" in r for r in yl.ROTAS_PROIBIDAS))
check("trocar forma de pagamento esta na lista",
      any("paymentmethodchange" in r.lower() for r in yl.ROTAS_PROIBIDAS))


# ==========================================================================
print("\n[8] O TOKEN — credencial nunca vira log")
# ==========================================================================
# Conta o padrao de CODIGO (com a virgula do objeto de init). As mencoes na
# documentacao aparecem entre crases e sem virgula -- e a primeira versao deste
# teste contava as quatro juntas e reprovava a propria explicacao.
check("as DUAS chamadas vao com credentials 'omit' (senao o CORS recusa)",
      fonte.count("credentials: 'omit',") == 2, fonte.count("credentials: 'omit',"))
# `include` aparece UMA vez de proposito: na docstring que avisa por que nao
# usar. Contar ocorrencia crua reprovaria o aviso -- entao o teste separa
# documentacao de codigo, que era o defeito da primeira versao dele.
usos_include = [l for l in fonte.splitlines()
                if "credentials: 'include'" in l and not l.lstrip().startswith(">")]
check("nenhuma CHAMADA usa credentials include", usos_include == [], usos_include)
check("mas o aviso sobre ele continua escrito",
      "credentials: 'include'" in fonte and "quebra" in fonte)
check("a evidencia guarda so o formato do token",
      '"chars": len(token)' in fonte or "'chars'" in fonte or '"chars"' in fonte)
check("o token NAO e escrito inteiro na evidencia",
      'evidence["yelum_token"] = {"capturado"' in fonte)


# ==========================================================================
print("\n[9] O REGISTRO — a Yelum existe para o resto do sistema")
# ==========================================================================
from portal_worker.journeys import get_journey, portais_com_cobranca, tem_cobranca  # noqa: E402

check("yelum_corretor sabe varrer cobranca", tem_cobranca("yelum_corretor"))
check("resolve a funcao real", callable(get_journey("yelum_corretor", "cobranca_sweep")))
check("resolve o login_check", callable(get_journey("yelum_corretor", "login_check")))
check("as QUATRO seguradoras estao na lista",
      {"allianz_corretor", "hdi_corretor", "tokiomarine_corretor", "yelum_corretor"}
      <= set(portais_com_cobranca()), portais_com_cobranca())

bc = _load("billing_collection", "app/services/billing_collection.py")
check("entra sozinha no padrao da varredura",
      "yelum_corretor" in bc.DEFAULT_PORTAL_KEYS, bc.DEFAULT_PORTAL_KEYS)
check("tem nome legivel para a mensagem do grupo",
      bc._portal_insurer_name({"portal": "yelum_corretor"}, {}) == "YELUM")
check("e o nome difere do da Tokio (o teste consegue falhar)",
      bc._portal_insurer_name({"portal": "yelum_corretor"}, {})
      != bc._portal_insurer_name({"portal": "tokiomarine_corretor"}, {}))
check("o item retido e reconhecido pelo servico",
      bc.sem_boleto_por_regra(dict(por_nome["BENEDITA"], sem_boleto_motivo=m_dc)))

print("\n" + "=" * 62)
print("  Yelum Seguros: %d asserções verdes, %d vermelhas" % (PASS, FAIL))
print("=" * 62)
sys.exit(1 if FAIL else 0)
