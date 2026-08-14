# -*- coding: utf-8 -*-
"""A cobranca da MAPFRE le a corretora CERTA, e sabe quando nao viu tudo.

UTF-8 e nao ASCII: as secoes [3] e [4] comparam o TEXTO que a atendente le, e
ele vem do portal com acento ("DEBITO EM CONTA", "CARTAO DE CREDITO").

O que estes testes seguram
==========================
    [1] o gate cross-tenant  UM login enxerga DUAS corretoras. O brokerId sai
                             do account_label, exige UMA correspondencia, e
                             nunca e o que o portal deixou selecionado.
    [2] a segunda tranca     cada linha lida declara o broker dela; se vier de
                             outro, a leitura inteira e descartada.
    [3] a forma 5            existe no DADO e nao existe na TELA. A regra e
                             lista de permissao: so o 4 gera boleto.
    [4] pessoa juridica      legalPerson tem o documento noutro lugar; ler so
                             naturalPerson deixaria empresa sem CPF/CNPJ.
    [5] a paginacao          `total` maior que o lido NAO e carteira em dia.
    [6] a carencia de 48h    quem vence hoje nao e inadimplente.
    [7] o PDF                exige %PDF; o `size` do metadata MENTE.
    [8] rotas proibidas      nada que escreve aparece no codigo.
    [9] o token              so o FORMATO vai para a evidencia.
   [10] a janela             ampla de proposito: a padrao do portal escondia
                             inadimplente real.

CLAUDE.md 9.3 -- um guarda que nao tem como falhar nao guarda nada. Por isso a
fixture traz DUAS carteiras disjuntas e DUAS corretoras que conseguem ser
diferentes: se alguem trocar o brokerId por um valor fixo, [1] e [2] ficam
vermelhos.
"""
from __future__ import annotations

import ast
import asyncio
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


from fixtures import mapfre_parcelas as fx           # noqa: E402
from portal_worker.journeys import mapfre_corretor as mp  # noqa: E402
from portal_worker.journeys import (                 # noqa: E402
    JOURNEY_COBRANCA, JOURNEYS, get_journey, portais_com_cobranca, tem_cobranca)

AGORA = datetime(2026, 8, 13, 12, 0, tzinfo=timezone.utc)


# ==========================================================================
print("\n[1] O GATE CROSS-TENANT — o brokerId nasce do account_label")
# ==========================================================================
bid, erro = mp.escolher_broker(fx.BROKERS, fx.AUTOFLEET)
check("acha a AutoFleet e devolve o brokerId dela", bid == "55744776" and not erro,
      (bid, erro))

bid_r, erro_r = mp.escolher_broker(fx.BROKERS, fx.RESULTA)
check("acha a Resulta e devolve OUTRO brokerId", bid_r == "12542146" and not erro_r,
      (bid_r, erro_r))

# 🔴 O teste que prova que o guarda CONSEGUE distinguir: se alguem fixar o
# brokerId no codigo, os dois casos acima devolveriam o mesmo valor.
check("as duas corretoras dao brokerIds DIFERENTES", bid != bid_r, (bid, bid_r))

bid_x, erro_x = mp.escolher_broker(fx.BROKERS_SEM_ALVO, fx.AUTOFLEET)
check("sem correspondencia -> nao escolhe e explica", not bid_x and "nao enxerga" in erro_x,
      (bid_x, erro_x))
check("a mensagem lista o que o portal ofereceu", "OUTRA CORRETORA" in erro_x, erro_x)

bid_a, erro_a = mp.escolher_broker(fx.BROKERS_AMBIGUO, fx.AUTOFLEET)
check("duas com o mesmo nome -> ambiguo, nao adivinha",
      not bid_a and "adivinhar" in erro_a, (bid_a, erro_a))

bid_v, erro_v = mp.escolher_broker(fx.BROKERS_VAZIO, fx.AUTOFLEET)
check("lista vazia -> para", not bid_v and erro_v, (bid_v, erro_v))

bid_n, erro_n = mp.escolher_broker(fx.BROKERS, "")
check("sem account_label -> para (nao varre o default do portal)",
      not bid_n and "account_label" in erro_n, (bid_n, erro_n))

bid_c, _ = mp.escolher_broker(fx.BROKERS, "auto fleet r corretora de segu")
check("a comparacao ignora caixa", bid_c == "55744776", bid_c)


# ==========================================================================
print("\n[2] A SEGUNDA TRANCA — de quem sao as linhas que voltaram")
# ==========================================================================
meus = mp.extrair_inadimplentes(fx.LISTA_VENCIDAS)
check("a carteira propria passa", mp.conferir_broker_dos_itens(meus, "55744776") == "")

outros = mp.extrair_inadimplentes(fx.LISTA_DA_OUTRA_CORRETORA)
recusa = mp.conferir_broker_dos_itens(outros, "55744776")
check("linha de outro broker e RECUSADA", bool(recusa), recusa)
check("a recusa diz que nao grava nada", "NAO gravo" in recusa, recusa)

# as duas carteiras da fixture sao mesmo disjuntas — senao [2] nao guarda nada
docs_meus = {i["cpf_cnpj"] for i in meus}
docs_outros = {i["cpf_cnpj"] for i in outros}
check("as duas carteiras da fixture NAO tem cliente em comum",
      docs_meus and docs_outros and not (docs_meus & docs_outros))


# ==========================================================================
print("\n[3] A FORMA 5 — existe no dado e nao existe na tela")
# ==========================================================================
mistos = mp.extrair_inadimplentes(fx.LISTA_MISTA)
por_forma = {i["forma_pagamento"]: i for i in mistos}
check("a fixture tem as quatro formas vistas nos dados",
      set(por_forma) == {"1", "2", "4", "5"}, sorted(por_forma))

check("boleto (4) pode ser cobrado", mp.motivo_para_reter(por_forma["4"]) == "")
for forma in ("1", "2", "5"):
    motivo = mp.motivo_para_reter(por_forma[forma])
    check(f"forma {forma} e RETIDA com motivo escrito",
          motivo.startswith(mp.MARCA_REGRA), (forma, motivo))
check("a forma 5 (fora do dropdown) e retida como as outras",
      not por_forma["5"]["gera_boleto"], por_forma["5"])
check("o motivo nomeia a forma para a atendente ler",
      "DÉBITO EM CONTA" in mp.motivo_para_reter(por_forma["5"]),
      mp.motivo_para_reter(por_forma["5"]))


# ==========================================================================
print("\n[4] PESSOA JURIDICA — o documento mora noutro lugar")
# ==========================================================================
pj = [i for i in mistos if i["cliente_nome"] == "EMPRESA DE TESTE LTDA"]
check("a lista tem uma pessoa juridica", len(pj) == 1, [i["cliente_nome"] for i in mistos])
check("o CNPJ da PJ foi lido", pj and pj[0]["cpf_cnpj"] == "55566677788", pj)
check("o nome da PJ foi lido", pj and pj[0]["cliente_nome"] == "EMPRESA DE TESTE LTDA")
check("toda linha tem documento (nenhuma ficou sem)",
      all(i["cpf_cnpj"] for i in mistos),
      [(i["cliente_nome"], i["cpf_cnpj"]) for i in mistos if not i["cpf_cnpj"]])

# o portal manda telefone e e-mail vazios — o WhatsApp vem da gestao
check("o portal nao da telefone (por isso a InfoCap existe)",
      all(not (fx.LISTA_MISTA["list"][n]["client"].get("mainPhone") or "")
          for n in range(len(fx.LISTA_MISTA["list"]))))


# ==========================================================================
print("\n[5] A PAGINACAO — total maior que o lido NAO e carteira em dia")
# ==========================================================================
check("declarado 3 e lidos 1 -> leitura incompleta",
      bool(mp.leitura_incompleta(3, 1)))
check("a mensagem manda paginar", "paginar" in mp.leitura_incompleta(3, 1))
check("declarado 2 e lidos 2 -> completa", mp.leitura_incompleta(2, 2) == "")
check("declarado 0 e lidos 0 -> completa", mp.leitura_incompleta(0, 0) == "")
check("total ilegivel nao inventa falha", mp.leitura_incompleta(None, 0) == "")

# corpo ilegivel nao pode virar "nenhum inadimplente"
check("resposta vazia nao rende itens", mp.extrair_inadimplentes(fx.LISTA_ILEGIVEL) == [])
check("lista vazia rende zero itens", mp.extrair_inadimplentes(fx.LISTA_VAZIA) == [])

somadas = (mp.extrair_inadimplentes(fx.PAGINA_1) + mp.extrair_inadimplentes(fx.PAGINA_2)
           + mp.extrair_inadimplentes(fx.PAGINA_3))
check("as tres paginas somam o total declarado", len(somadas) == fx.PAGINA_1["total"])
check("a paginacao nao repete recibo", len({i["recibo"] for i in somadas}) == 3)

corpo = mp.corpo_da_busca(broker_id="55744776", de="01/01/2026", ate="13/08/2026",
                          pagina=2)
check("o corpo pede a pagina certa", corpo["pageIndex"] == "2")
check("o corpo leva o brokerId (vazio da HTTP 500)", corpo["brokerId"] == "55744776")
check("o corpo leva clientTypeCode (vazio da HTTP 400)", corpo["clientTypeCode"] == "01")
check("o corpo pede status Vencida", corpo["receiptStatusCode"] == mp.STATUS_VENCIDA)


# ==========================================================================
print("\n[6] A CARENCIA DE 48h")
# ==========================================================================
ontem = (AGORA - timedelta(days=1)).strftime("%Y-%m-%d")
tres = (AGORA - timedelta(days=3)).strftime("%Y-%m-%d")
hoje = AGORA.strftime("%Y-%m-%d")
check("vencido ha 3 dias e inadimplente", mp.vencido_ha_mais_de(tres, 48, agora=AGORA))
check("vencido ontem AINDA nao", not mp.vencido_ha_mais_de(ontem, 48, agora=AGORA))
check("vence hoje nao e inadimplente", not mp.vencido_ha_mais_de(hoje, 48, agora=AGORA))
check("data ilegivel nao vira inadimplente", not mp.vencido_ha_mais_de("", 48, agora=AGORA))
check("data absurda nao explode", not mp.vencido_ha_mais_de("nao-e-data", 48, agora=AGORA))


# ==========================================================================
print("\n[7] O PDF — e o metadata que mente")
# ==========================================================================
dados, erro = mp.pdf_do_documento(fx.DOCUMENTO_BOLETO)
check("o boleto decodifica e comeca com %PDF", dados.startswith(b"%PDF") and not erro,
      (len(dados), erro))
check("o tamanho lido e o REAL, nao o do metadata",
      len(dados) != fx.DOCUMENTO_BOLETO["documentMetadata"]["size"],
      (len(dados), fx.DOCUMENTO_BOLETO["documentMetadata"]["size"]))

d2, e2 = mp.pdf_do_documento(fx.DOCUMENTO_SEM_PDF)
check("conteudo que nao e PDF e RECUSADO", not d2 and "nao e um PDF" in e2, e2)
d3, e3 = mp.pdf_do_documento(fx.DOCUMENTO_VAZIO)
check("documento sem conteudo e recusado", not d3 and e3, e3)
d4, e4 = mp.pdf_do_documento({})
check("resposta vazia e recusada", not d4 and e4, e4)

item = meus[0]
check("o caminho do documento e BO_ + receiptId",
      mp.caminho_do_documento(item) == f"/policy/document/BO_{item['recibo']}",
      mp.caminho_do_documento(item))
check("o receiptId tem as tres chaves da lista",
      item["recibo"] == "1000000000001_0_8", item["recibo"])

caminho = mp.build_boleto_storage_path(company_id="c1", job_id="j1",
                                       portal_key="mapfre_corretor",
                                       recibo=item["recibo"])
check("o caminho no bucket segue o contrato das outras journeys",
      caminho == "c1/mapfre_corretor/j1/boleto-1000000000001_0_8.pdf", caminho)
check("recibo com barra nao escapa de pasta",
      "/" not in mp.build_boleto_storage_path(
          company_id="c1", job_id="j1", portal_key="p", recibo="a/b/../c").split("/")[-1])


# ==========================================================================
print("\n[8] ROTAS PROIBIDAS — o robo nao aperta botao que escreve")
# ==========================================================================
fonte = (ROOT / "portal_worker" / "journeys" / "mapfre_corretor.py").read_text(
    encoding="utf-8")


def _so_o_executavel(texto: str) -> str:
    """O codigo SEM docstrings nem comentarios.

    Um filtro por prefixo de linha nao serve: a docstring do modulo registra as
    MEDICOES ('brokerId=55744776 -> 59 parcelas'), e essas linhas nao comecam
    com aspas. Confundir o registro da medicao com um valor fixo no codigo
    daria um vermelho falso -- e um teste que da vermelho falso e desligado, e
    ai deixa de guardar (CLAUDE.md 9.3).
    """
    arvore = ast.parse(texto)
    for no in ast.walk(arvore):
        if isinstance(no, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                           ast.ClassDef)) and ast.get_docstring(no) is not None:
            no.body = no.body[1:]
    return ast.unparse(arvore)


corpo_exec = _so_o_executavel(fonte)
check("a reprogramacao (que custa R$ 50 ao segurado) esta barrada",
      "reschedule" in mp.ROTAS_PROIBIDAS)
check("a exportacao em lote esta barrada", "/receipts/export" in mp.ROTAS_PROIBIDAS)
check("o /actions esta barrado (e a porta das duas acoes)",
      "/actions" in mp.ROTAS_PROIBIDAS)


# 🔴 O guarda de verdade nao e procurar a palavra no arquivo -- `isRescheduled`
# e campo OBRIGATORIO do corpo da busca, e a propria lista de proibidas contem
# as palavras. O que importa e que a CHAMADA seja recusada. Entao chama-se.
class _PaginaQueDelata:
    """Se a journey chegar a `evaluate`, a rota proibida NAO foi barrada."""

    def __init__(self):
        self.chamou = False

    async def evaluate(self, *_a, **_k):
        self.chamou = True
        return {"ok": True, "status": 200, "text": "{}"}


def _rodar(coro):
    return asyncio.run(coro)


for rota in ("/distributor/1/receipts/8/actions",
             "/distributor/1/receipts/export",
             "/payment/reschedule",
             "/policy/simulateChangePaymentMethod"):
    pag = _PaginaQueDelata()
    r = _rodar(mp._api(pag, "token-de-mentira", rota))
    check(f"a chamada a {rota.split('/')[-1]} e RECUSADA antes de sair",
          not pag.chamou and "proibida" in str(r.get("erro", "")), (rota, r))

# ...e a prova de que este guarda consegue falhar: uma rota PERMITIDA passa.
pag_ok = _PaginaQueDelata()
_rodar(mp._api(pag_ok, "token-de-mentira", "/distributor/1/brokers"))
check("uma rota permitida CHEGA a sair (o guarda sabe diferenciar)", pag_ok.chamou)


# ==========================================================================
print("\n[9] O TOKEN e a EVIDENCIA — segredo nunca vai para o log")
# ==========================================================================
check("o modulo nao guarda token fixo",
      not any(t in fonte for t in ("eyJ0eXAi", "eyJhbGci")))

# 🔴 A PROVA DE QUE ESTE GUARDA CONSEGUE FALHAR. Sem ela, um `_so_o_executavel`
# que devolvesse "" faria os dois testes abaixo passarem para sempre — o guarda
# que nao tem como falhar nao guarda nada (CLAUDE.md §9.3).
check("o filtro de docstring devolve codigo de verdade",
      "FORMA_COM_BOLETO" in corpo_exec and "async def cobranca_sweep" in corpo_exec,
      len(corpo_exec))
check("o filtro ACHA um valor plantado no codigo executavel",
      "55744776" in _so_o_executavel(fonte + '\nPLANTADO = "55744776"\n'))
check("e o mesmo valor NAO aparece so por estar na docstring",
      "55744776" not in _so_o_executavel('"""brokerId=55744776"""\nX = 1\n'))

check("o modulo nao tem brokerId fixo no codigo executavel",
      "55744776" not in corpo_exec and "12542146" not in corpo_exec,
      [l for l in corpo_exec.splitlines() if "55744776" in l or "12542146" in l])
check("o modulo nao tem distributorId fixo", "10754" not in corpo_exec)
check("a evidencia do token guarda so o formato",
      "chars" in fonte and "tamanhos_vistos" in fonte)
check("captura o token MAIS LONGO (o de contexto completo)",
      "max(achados)" in fonte)


# ==========================================================================
print("\n[10] A JANELA — ampla de proposito")
# ==========================================================================
j = mp.janela_de_busca(365, agora=AGORA)
check("a janela devolve dd/mm/aaaa", j["ate"] == "13/08/2026", j)
check("365 dias atras e 13/08/2025", j["de"] == "13/08/2025", j)
check("o padrao NAO e a janela curta do portal", mp.JANELA_PADRAO_DIAS >= 90,
      mp.JANELA_PADRAO_DIAS)
check("a pagina pede 200 por vez (a API aceitou)", mp.PAGINA_TAMANHO == 200)

# 📊 A janela padrao do portal (15 dias) devolvia total=0 no MESMO dia em que
# 30 dias devolviam 2 vencidas reais. Este teste guarda esse fato.
check("a janela padrao cobre mais que os 15 dias do portal",
      mp.JANELA_PADRAO_DIAS > 15)


# ==========================================================================
print("\n[11] O MAPA — a MAPFRE entra sem desmarcar as outras")
# ==========================================================================
portais = portais_com_cobranca()
check("a MAPFRE aparece no conjunto do Cobrador", "mapfre_corretor" in portais, portais)
for antigo in ("allianz_corretor", "hdi_corretor", "tokiomarine_corretor",
               "yelum_corretor"):
    check(f"{antigo} continua no conjunto", antigo in portais, portais)

# ⚠️ Este teste ja afirmou "sao cinco seguradoras" — e era verdade, ate a Zurich
# existir. Contagem fixa envelhece e vira vermelho falso a cada seguradora nova;
# um vermelho falso e desligado, e ai o guarda deixa de guardar (CLAUDE.md §9.3).
# A licao MIGRA: o que importa nunca foi o numero, e sim que NINGUEM some.
sufixo = f".{JOURNEY_COBRANCA}"
no_mapa = sorted(k[: -len(sufixo)] for k in JOURNEYS if k.endswith(sufixo))
check("toda journey de cobranca do mapa chega ao conjunto do Cobrador",
      no_mapa == sorted(portais), (no_mapa, sorted(portais)))
check("e o conjunto so cresce — nenhuma das cinco anteriores caiu",
      len(portais) >= 5, portais)
check("tem_cobranca reconhece a MAPFRE", tem_cobranca("mapfre_corretor"))
check("a journey resolve pelo mapa",
      callable(get_journey("mapfre_corretor", "cobranca_sweep")))
check("o login_check tambem resolve",
      callable(get_journey("mapfre_corretor", "login_check")))
check("portal inexistente nao resolve", get_journey("nao_existe", "cobranca_sweep") is None)


# ==========================================================================
print("\n[12] O WORKER entrega o account_label — senao o gate fica sem entrada")
# ==========================================================================
worker = (ROOT / "portal_worker" / "worker.py").read_text(encoding="utf-8")
check("o worker injeta account_label nos params",
      'params.setdefault("account_label"' in worker)
check("ele vem da linha da conta, nao de constante",
      'account_row.get("account_label")' in worker)


# ==========================================================================
print("\n[13] VALORES e DATAS")
# ==========================================================================
check("294.35 (ponto) vira float", mp._valor("294.35") == 294.35)
check("1.672,62 (brasileiro) vira 1672.62", mp._valor("1.672,62") == 1672.62)
check("valor vazio vira None", mp._valor("") is None)
check("valor ilegivel nao explode", mp._valor("abc") is None)
check("a data corta em 10 chars, sem mexer no fuso",
      mp._data_iso("2026-07-26T00:00:00Z") == "2026-07-26")
check("data ausente vira vazio", mp._data_iso(None) == "")
check("o item lido traz o valor da lista",
      meus[0]["valor"] == 294.35, meus[0]["valor"])


print("\n" + "=" * 66)
print(f"  {PASS} asserções verdes · {FAIL} vermelhas")
print("=" * 66)
sys.exit(1 if FAIL else 0)
