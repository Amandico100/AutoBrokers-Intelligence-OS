# -*- coding: utf-8 -*-
"""A cobranca da Zurich le o valor CERTO e nao cobra quem ja pagou.

UTF-8 e nao ASCII: as secoes [2] e [4] comparam o TEXTO que a atendente le, e
ele vem do portal com acento ("Debito nao autorizado", "Cartao de Credito").

O que estes testes seguram
==========================
    [1] o valor            "1,287,99" e R$ 1.287,99. O parser das OUTRAS
                           journeys devolve None para isso -- e None nao
                           estoura: o item seguiria sem valor.
    [2] `Aprovado` nao e divida. Cobrar quem ja pagou e o pior erro possivel.
    [3] valorJuros MENTE   e identico ao valorParcela em 37 de 37 itens reais.
                           A journey nao o usa para conta nenhuma.
    [4] a lista de permissao  so "Boleto" gera boleto. Pix e Carne existem no
                           filtro da tela e nunca apareceram nos dados.
    [5] a testemunha       o portal manda diasAtraso pronto e eu calculo o
                           mesmo da data. Se divergirem, a varredura para.
    [6] o PDF              FileContents e ARRAY DE BYTES, nao base64.
    [7] as chaves          as sete do boleto saem da lista, sem passo extra.
    [8] o CPF              a lista NAO traz; exige duas chamadas.
    [9] rotas proibidas    provado CHAMANDO, nao procurando palavra.
   [10] o mapa             a Zurich entra sem desmarcar as outras cinco.

CLAUDE.md 9.3 -- um guarda que nao tem como falhar nao guarda nada. Por isso
[1] compara com o parser ANTIGO (que consegue ser diferente), [5] tem um caso
que bate e outro que nao bate, e [9] prova que uma rota permitida PASSA.
"""
from __future__ import annotations

import ast
import asyncio
import re
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


from fixtures import zurich_parcelas as fx                 # noqa: E402
from portal_worker.journeys import zurich_corretor as zu    # noqa: E402
from portal_worker.journeys import mapfre_corretor as mp    # noqa: E402
from portal_worker.journeys import (                        # noqa: E402
    get_journey, portais_com_cobranca, tem_cobranca)

# 13/08/2026 — a data da captura. Fixa, para os dias de atraso baterem.
AGORA = datetime(2026, 8, 13, 12, 0, tzinfo=timezone.utc)


# ==========================================================================
print("\n[1] O VALOR — a virgula que e milhar E decimal na mesma string")
# ==========================================================================
CASOS = [("638,95", 638.95), ("1,287,99", 1287.99), ("1.287,99", 1287.99),
         ("209,50", 209.5), ("294.35", 294.35), ("1287.99", 1287.99),
         ("0,01", 0.01), ("1.000.000,00", 1000000.0)]
for bruto, esperado in CASOS:
    lido = zu.valor_brasileiro(bruto)
    check(f"{bruto!r} -> {esperado}", lido == esperado, lido)

check("vazio vira None", zu.valor_brasileiro("") is None)
check("texto vira None", zu.valor_brasileiro("abc") is None)
check("None vira None", zu.valor_brasileiro(None) is None)

# 🔴 A PROVA de que este teste consegue falhar: o parser ANTIGO erra o caso.
check("o parser das OUTRAS journeys devolve None para '1,287,99'",
      mp._valor("1,287,99") is None, mp._valor("1,287,99"))
check("e acerta os casos que ja sabia — o novo e um SUPERCONJUNTO",
      mp._valor("1.287,99") == zu.valor_brasileiro("1.287,99") == 1287.99)

quebrado = zu.extrair_parcelas(fx.LISTA_VALOR_QUEBRADO)
check("o item com valor grande e lido COM valor", quebrado[0]["valor"] == 1287.99,
      quebrado[0]["valor"])
check("nenhum item da lista fica sem valor",
      all(i["valor"] is not None for i in zu.extrair_parcelas(fx.LISTA)),
      [(i["recibo"], i["valor"]) for i in zu.extrair_parcelas(fx.LISTA)])


# ==========================================================================
print("\n[2] 'Aprovado' NAO e divida — cobrar quem pagou e o pior erro")
# ==========================================================================
itens = zu.extrair_parcelas(fx.LISTA)
check("a fixture tem os quatro casos", len(itens) == 4, len(itens))

# ⚠️ Indexar por `situacao` colapsaria as DUAS parcelas pendentes numa chave só,
# e o teste passaria a falar do item errado sem avisar. A chave e o `recibo`.
por_recibo = {i["recibo"]: i for i in itens}
check("nenhum item se perdeu na indexacao", len(por_recibo) == len(itens))
PENDENTE_BOLETO = por_recibo["10001-0-8"]     # era debito, virou boleto
PENDENTE_DEBITO = por_recibo["10002-0-6"]     # segue em debito, vence hoje
APROVADO = por_recibo["10003-0-7"]
PAGO = por_recibo["10004-0-10"]

check("as situacoes conseguem ser diferentes",
      {i["situacao"] for i in itens} == {"Parcela pendente", "Aprovado", "Pago"},
      sorted({i["situacao"] for i in itens}))
check("'Pago' fica de fora", not zu.esta_em_aberto(PAGO))
check("'Aprovado' fica de fora (esta em processamento)",
      not zu.esta_em_aberto(APROVADO))
check("'Parcela pendente' entra", zu.esta_em_aberto(PENDENTE_BOLETO))

em_aberto = [i for i in itens if zu.esta_em_aberto(i)]
check("so 2 dos 4 estao em aberto", len(em_aberto) == 2, len(em_aberto))

atrasados = [i for i in em_aberto
             if zu.vencido_ha_mais_de(i["vencimento"], 48, agora=AGORA)]
check("e so 1 esta vencido ha mais de 48h", len(atrasados) == 1,
      [(i["recibo"], i["vencimento"]) for i in atrasados])
check("o inadimplente e a apolice pendente-com-boleto", atrasados[0]["numero_apolice"] == "10001",
      atrasados[0]["numero_apolice"])


# ==========================================================================
print("\n[3] valorJuros MENTE — a journey nao usa para conta nenhuma")
# ==========================================================================
i = PENDENTE_BOLETO
check("na fixture valorJuros == valorParcela (como nos 37 reais)",
      i["valor"] == i["valor_juros_declarado"], (i["valor"], i["valor_juros_declarado"]))
fonte = (ROOT / "portal_worker" / "journeys" / "zurich_corretor.py").read_text(
    encoding="utf-8")


def _so_executavel(texto: str) -> str:
    arvore = ast.parse(texto)
    for no in ast.walk(arvore):
        if isinstance(no, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                           ast.ClassDef)) and ast.get_docstring(no) is not None:
            no.body = no.body[1:]
    return ast.unparse(arvore)


exec_src = _so_executavel(fonte)
check("o filtro de docstring devolve codigo de verdade",
      "async def cobranca_sweep" in exec_src and "FORMA_COM_BOLETO" in exec_src)
check("o valor cobrado sai de valorParcela, nunca de valorJuros",
      "'valor': valor_brasileiro(r.get('valorParcela'))" in exec_src
      or '"valor": valor_brasileiro(r.get("valorParcela"))' in exec_src
      or "valor_brasileiro(r.get('valorParcela'))" in exec_src,
      [l for l in exec_src.splitlines() if "valorParcela" in l])
check("valorJuros so vai para a EVIDENCIA, com nome que avisa",
      "valor_juros_declarado" in exec_src)


# ==========================================================================
print("\n[4] A LISTA DE PERMISSAO — so 'Boleto' gera boleto")
# ==========================================================================
check("Boleto pode ser cobrado",
      zu.motivo_para_reter(PENDENTE_BOLETO) == "")
motivo = zu.motivo_para_reter(PENDENTE_DEBITO)
check("Debito e RETIDO", motivo.startswith(zu.MARCA_REGRA), motivo)
check("o motivo carrega o O.B.S do portal para a atendente ler",
      "Débito agendado" in motivo, motivo)

# 🔴 Pix e Carne existem no filtro da tela e NUNCA apareceram nos dados.
desconhecidas = zu.extrair_parcelas(fx.LISTA_FORMA_DESCONHECIDA)
check("a fixture traz as duas formas que a tela oferece e o dado nunca mostrou",
      {i["forma_pagamento"] for i in desconhecidas} == {"Pix", "Carnê"})
for d in desconhecidas:
    check(f"{d['forma_pagamento']} e RETIDO (lista de permissao, nao de exclusao)",
          zu.motivo_para_reter(d).startswith(zu.MARCA_REGRA), zu.motivo_para_reter(d))

check("sem numero bancario, retem mesmo sendo boleto",
      zu.motivo_para_reter({"gera_boleto": True, "nosso_numero": "",
                            "forma_pagamento": "Boleto"}).startswith(zu.MARCA_REGRA))


# ==========================================================================
print("\n[5] A TESTEMUNHA — as duas contas de atraso tem de bater")
# ==========================================================================
bate = {"recibo": "x", "vencimento": "2026-08-06", "dias_atraso_portal": 7}
check("7 dias declarados e 7 calculados -> passa",
      zu.conferir_dias_de_atraso(bate, agora=AGORA) == "",
      zu.conferir_dias_de_atraso(bate, agora=AGORA))

folga = {"recibo": "x", "vencimento": "2026-08-06", "dias_atraso_portal": 8}
check("1 dia de folga e tolerado (o portal fecha em horario proprio)",
      zu.conferir_dias_de_atraso(folga, agora=AGORA) == "")

# 🔴 o caso que CONSEGUE falhar
mente = {"recibo": "y", "vencimento": "2026-08-06", "dias_atraso_portal": 60}
recusa = zu.conferir_dias_de_atraso(mente, agora=AGORA)
check("60 declarados contra 7 calculados -> PARA", bool(recusa), recusa)
check("a recusa diz que nao afirma nada sobre a divida", "NAO afirmo" in recusa, recusa)
check("sem diasAtraso nao inventa falha",
      zu.conferir_dias_de_atraso({"vencimento": "2026-08-06",
                                  "dias_atraso_portal": None}, agora=AGORA) == "")
check("sem vencimento nao inventa falha",
      zu.conferir_dias_de_atraso({"vencimento": "", "dias_atraso_portal": 7},
                                 agora=AGORA) == "")

check("a data vem do campo formatado, nao do /Date(ms)/",
      zu.data_iso("13/08/2026 03:00:00") == "2026-08-13")
check("data ausente vira vazio", zu.data_iso(None) == "")
check("data ilegivel vira vazio", zu.data_iso("/Date(1785985200000)/") == "")


# ==========================================================================
print("\n[6] O PDF — FileContents e ARRAY DE BYTES, nao base64")
# ==========================================================================
dados, erro = zu.pdf_do_boleto(fx.BOLETO)
check("o boleto vira bytes e comeca com %PDF",
      dados.startswith(b"%PDF") and not erro, (len(dados), erro))
d2, e2 = zu.pdf_do_boleto(fx.BOLETO_SEM_PDF)
check("conteudo que nao e PDF e RECUSADO", not d2 and "nao devolveu um PDF" in e2, e2)
d3, e3 = zu.pdf_do_boleto(fx.BOLETO_VAZIO)
check("resposta sem Boleto e recusada", not d3 and e3, e3)
d4, e4 = zu.pdf_do_boleto(fx.BOLETO_SEM_CONTEUDO)
check("FileContents vazio e recusado", not d4 and e4, e4)
d5, e5 = zu.pdf_do_boleto({})
check("resposta vazia e recusada", not d5 and e5, e5)


# ==========================================================================
print("\n[7] AS CHAVES DO BOLETO — todas saem da lista")
# ==========================================================================
p = zu.params_do_boleto(atrasados[0])
check("leva o payment_no", p["paymentNO"] == "900000001", p)
check("leva a apolice", p["numeroApolice"] == "10001", p)
check("leva a parcela", p["NumParcela"] == "8", p)
check("codigoCarteira recebe o RAMO (31), nao o CodigoCarteira da apolice",
      p["codigoCarteira"] == "31", p)
check("a data vai em dd/mm/aaaa", p["dataVencimento"] == "06/08/2026", p)
check("codSucursal vai vazio, como o portal manda", p["codSucursal"] == "")
check("nenhuma chave do boleto ficou vazia por engano",
      all(p[k] for k in ("paymentNO", "numeroApolice", "NumParcela",
                         "codigoCarteira", "dataVencimento")), p)

caminho = zu.build_boleto_storage_path(company_id="c1", job_id="j1",
                                       portal_key="zurich_corretor",
                                       recibo=atrasados[0]["recibo"])
check("o caminho no bucket segue o contrato das outras journeys",
      caminho == "c1/zurich_corretor/j1/boleto-10001-0-8.pdf", caminho)


# ==========================================================================
print("\n[8] O CPF — a lista NAO traz")
# ==========================================================================
check("nenhum item da lista vem com documento",
      all(not i["cpf_cnpj"] for i in itens))
check("as chaves da apolice saem do detalhe",
      zu.chaves_da_apolice(fx.DETALHE_APOLICE)["Sucursal"] == "042")
check("e o CodigoCarteira do detalhe (0531) e DIFERENTE do ramo (31)",
      zu.chaves_da_apolice(fx.DETALHE_APOLICE)["CodigoCarteira"] == "0531")
check("detalhe incompleto nao inventa chave",
      zu.chaves_da_apolice(fx.DETALHE_APOLICE_INCOMPLETO)["Sucursal"] == "")
check("o CNPJ da PJ e lido",
      zu.documento_do_segurado(fx.DETALHE_SEGURADO_PJ) == "11222333000181")
check("o CPF da PF e lido",
      zu.documento_do_segurado(fx.DETALHE_SEGURADO_PF) == "11122233344")
check("sem documento devolve vazio, nao lixo",
      zu.documento_do_segurado(fx.DETALHE_SEGURADO_SEM_DOC) == "")
check("resposta vazia devolve vazio", zu.documento_do_segurado(None) == "")


# ==========================================================================
print("\n[9] ROTAS PROIBIDAS — provado CHAMANDO")
# ==========================================================================
class _PaginaQueDelata:
    def __init__(self):
        self.chamou = False

    async def evaluate(self, *_a, **_k):
        self.chamou = True
        return {"status": 200, "json": {}, "bytes": 2}


for rota in ("/Renovacao1Click/Executar", "/Restituicao/Solicitar",
             "/DevolucaoProposta/Enviar", "/Usuario/SalvarAutoServicoDWUsuario",
             "/ParcelaVencidaCorretor/GerarExcel"):
    pag = _PaginaQueDelata()
    r = asyncio.run(zu._api(pag, rota))
    check(f"{rota.split('/')[-1]} e RECUSADA antes de sair",
          not pag.chamou and "proibida" in str(r.get("erro", "")), (rota, r))

pag_ok = _PaginaQueDelata()
asyncio.run(zu._api(pag_ok, zu.EP_LISTA))
check("a lista (permitida) CHEGA a sair — o guarda sabe diferenciar", pag_ok.chamou)

check("a renovacao 1-click esta barrada",
      any("renovacao" in r for r in zu.ROTAS_PROIBIDAS))
check("o log de auto-servico esta barrado",
      any("salvarautoservico" in r for r in zu.ROTAS_PROIBIDAS))


# ==========================================================================
print("\n[10] O MAPA — a Zurich entra sem desmarcar as outras")
# ==========================================================================
portais = portais_com_cobranca()
check("a Zurich aparece no conjunto", "zurich_corretor" in portais, portais)
for antigo in ("allianz_corretor", "hdi_corretor", "mapfre_corretor",
               "tokiomarine_corretor", "yelum_corretor"):
    check(f"{antigo} continua no conjunto", antigo in portais, portais)
check("sao SEIS seguradoras agora", len(portais) == 6, portais)
check("tem_cobranca reconhece a Zurich", tem_cobranca("zurich_corretor"))
check("a journey resolve pelo mapa",
      callable(get_journey("zurich_corretor", "cobranca_sweep")))
check("o login_check tambem resolve",
      callable(get_journey("zurich_corretor", "login_check")))


# ==========================================================================
print("\n[11] SEGREDO e SESSAO")
# ==========================================================================
# 🔴 O guarda procura o FORMATO, nao o valor: escrever a senha aqui para
# depois conferir que ela nao esta no modulo colocaria a senha no repositorio
# — o defeito que ele existe para impedir.
_literais = re.findall(r"""['"]([^'"]{4,40})['"]""", exec_src)
_suspeitos = [t for t in _literais
              if re.fullmatch(r"\d{6}", t)                       # codigo de corretor
              or re.search(r"[A-Za-z][A-Za-z0-9]*[*@#$][A-Za-z0-9*]{2,}", t)]  # senha
check("o modulo nao guarda credencial fixa (nem codigo, nem senha)",
      not _suspeitos, _suspeitos)
check("o guarda de credencial CONSEGUE achar — prova por plantio",
      bool(re.findall(r"""['"](\d{6})['"]""", exec_src + " x = '123456'")))
# `ast.unparse` normaliza aspas duplas em simples — comparar so uma forma daria
# vermelho falso. Comparar o miolo, que nao muda.
check("a credencial entra por params, nunca por constante",
      "params.get(" in exec_src and "username" in exec_src and "password" in exec_src)
check("usa cookie de mesma origem (a Zurich nao tem Bearer)",
      "same-origin" in exec_src)
check("le a corretora da tela para denunciar credencial trocada",
      "zurich_corretora_na_tela" in exec_src)

vazia = zu.extrair_parcelas(fx.LISTA_VAZIA)
check("lista vazia rende zero itens", vazia == [])
check("corpo ilegivel rende zero itens", zu.extrair_parcelas(fx.LISTA_ILEGIVEL) == [])
check("corpo sem a chave 'corretor' rende zero itens",
      zu.extrair_parcelas(fx.LISTA_SEM_A_CHAVE) == [])


# ==========================================================================
print("\n[12] A JANELA — 404 e 'estreite', 503 e 'pare'")
# ==========================================================================
check("o padrao e 90 dias (o maior MEDIDO que respondeu 200)",
      zu.JANELA_PADRAO_DIAS == 90, zu.JANELA_PADRAO_DIAS)
check("existe um piso, para nao estreitar ate zero",
      zu.JANELA_PISO_DIAS == 15, zu.JANELA_PISO_DIAS)
check("o padrao NAO e a janela curta que esconde divida",
      zu.JANELA_PADRAO_DIAS > 30)

j = zu.janela_de_busca(90, agora=AGORA)
check("a janela sai em dd/mm/aaaa", j["ate"] == "13/08/2026", j)
check("90 dias atras e 15/05/2026", j["de"] == "15/05/2026", j)


class _PortalComTeto:
    """Se comporta como o portal MEDIDO: 404 acima de 90 dias, 200 abaixo.

    📊 O 404 nao e 'sem dados' — e 'janela grande demais'. Uma journey que o
    lesse como lista vazia diria 'carteira em dia' com divida na tela: o pior
    desfecho possivel (SPEC-070 §2b).
    """

    def __init__(self, teto_dias=90):
        self.teto = teto_dias
        self.pedidos = []

    async def evaluate(self, _js, arg):
        params = (arg or {}).get("params") or {}
        de, ate = params.get("dataInicial", ""), params.get("dataFinal", "")
        self.pedidos.append((de, ate))
        d1 = datetime.strptime(de, "%d/%m/%Y")
        d2 = datetime.strptime(ate, "%d/%m/%Y")
        dias = (d2 - d1).days
        if dias > self.teto:
            return {"status": 404, "json": None, "bytes": 1245}
        return {"status": 200, "json": fx.LISTA, "bytes": 25328}

    async def goto(self, *_a, **_k):
        return None

    async def wait_for_timeout(self, *_a, **_k):
        return None


class _PortalDerrubado(_PortalComTeto):
    async def evaluate(self, _js, arg):
        self.pedidos.append("503")
        return {"status": 503, "json": None, "bytes": 326}


async def _varrer(pagina, **extra):
    ev = {}
    params = {"username": "u", "password": "p", "account_label": "principal",
              "_company_id": "c", "_job_id": "j", "_portal_key": "zurich_corretor",
              **extra}

    async def _login_ok(_p, _params, evid):
        evid["logged_in"] = True
        from portal_worker.journeys import JourneyResult
        return JourneyResult(status="done",
                             captured={"logged_in": True, "corretora": "TESTE"})

    original = zu.login_check
    zu.login_check = _login_ok
    try:
        return await zu.cobranca_sweep(pagina, params, ev), ev
    finally:
        zu.login_check = original


pagina = _PortalComTeto(teto_dias=90)
res, ev = asyncio.run(_varrer(pagina))
check("com teto de 90 dias, a primeira janela ja passa",
      ev.get("zurich_lista", {}).get("janelas_tentadas") == [90],
      ev.get("zurich_lista"))
check("e a varredura conclui", res.status == "done", res.message)

apertado = _PortalComTeto(teto_dias=20)
res2, ev2 = asyncio.run(_varrer(apertado))
tentadas = ev2.get("zurich_lista", {}).get("janelas_tentadas")
check("com teto de 20 dias, ESTREITA ate caber", tentadas == [90, 45, 22, 15], tentadas)
check("e ainda assim conclui, sem dizer 'carteira em dia' por engano",
      res2.status == "done", res2.message)
check("a mensagem final diz em QUE janela olhou",
      "janela de 15 dias" in res2.message, res2.message)
check("e AVISA que a janela estreitou — senao '1 inadimplente' e lido como 'so esse'",
      "NAO foi verificada" in res2.message, res2.message)

morto = _PortalDerrubado()
res3, ev3 = asyncio.run(_varrer(morto))
check("503 PARA na hora, sem insistir", len(morto.pedidos) == 1, morto.pedidos)
check("503 vira needs_human", res3.status == "needs_human", res3.status)
check("e diz que insistir piora", "insistir piora" in res3.message, res3.message)
check("nunca afirma que a carteira esta em dia", "NAO afirmo" in res3.message)


# ==========================================================================
print("\n[13] 🔴 HTTP 200 COM LISTA VAZIA — o desfecho mais perigoso")
# ==========================================================================
# 📊 Medido: a mesma janela de 90 dias deu 43 linhas e, 3 min depois, 200 com
# 46 bytes e ZERO linhas — com inadimplente real na carteira. Um `done` ali e
# mentira com aparencia de sucesso.
class _PortalQueMenteVazio(_PortalComTeto):
    """Responde 200 com lista vazia — como o portal real fez sob carga."""

    def __init__(self, vazio_sempre=True):
        super().__init__(teto_dias=999)
        self.vazio_sempre = vazio_sempre
        self.chamadas = 0

    async def evaluate(self, _js, arg):
        self.chamadas += 1
        if self.vazio_sempre or self.chamadas == 1:
            return {"status": 200, "json": {"corretor": [], "AcionamentoSinistroVida": None},
                    "bytes": 46, "amostra": '{"corretor":[],"AcionamentoSinistroVida":null}'}
        return {"status": 200, "json": fx.LISTA, "bytes": 25328, "amostra": "{...}"}


mentiroso = _PortalQueMenteVazio(vazio_sempre=True)
res4, ev4 = asyncio.run(_varrer(mentiroso))
check("200 com zero linhas NAO vira 'carteira em dia'",
      res4.status == "needs_human", (res4.status, res4.message))
check("ele confere com uma SEGUNDA leitura antes de desistir",
      ev4.get("zurich_segunda_leitura") is not None, ev4.keys())
check("a mensagem diz que o portal ja mentiu assim antes",
      "200 vazio estando com inadimplente" in res4.message, res4.message)
check("e nunca afirma que a carteira esta em dia",
      "NAO afirmo" in res4.message, res4.message)
check("a amostra do corpo vai para a evidencia, para diagnostico sem nova visita",
      "amostra" in (ev4.get("zurich_segunda_leitura") or {}))

# 🔴 A PROVA de que o guarda consegue NAO disparar: se a segunda leitura traz
# dados, a varredura segue normalmente. Sem isto, o guarda seria um bloqueio
# permanente disfarcado de zelo.
recuperado = _PortalQueMenteVazio(vazio_sempre=False)
res5, ev5 = asyncio.run(_varrer(recuperado))
check("se a SEGUNDA leitura traz dados, a varredura continua",
      res5.status == "done", (res5.status, res5.message))
check("e os itens da segunda leitura sao usados",
      (ev5.get("zurich_carteira") or {}).get("lidas") == 4,
      ev5.get("zurich_carteira"))


print("\n" + "=" * 66)
print(f"  {PASS} asserções verdes · {FAIL} vermelhas")
print("=" * 66)
sys.exit(1 if FAIL else 0)
