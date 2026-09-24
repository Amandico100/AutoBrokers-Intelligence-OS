# -*- coding: utf-8 -*-
"""SPEC-EXTRA-001.10 — G2, G3, G7 e a régua do trincado (P2-1).

Quatro guardas que não precisam do fio inteiro, e um que precisa do acervo:

    G2   a fronteira material é CALCULADA a partir da peça, não é constante fixa
    G3   a seguradora sai do `GET /seguradoras/` AO VIVO, e a lista fechada morreu
    G7   a escada da SPEC-077: endpoint de ESCRITA `APPROVED` com ZERO exercícios
         medidos no acervo deixa este arquivo VERMELHO
    P2-1 nenhum arquivo do caminho API-first declara régua numérica de trincado

⛔ PII: G3 e G7 leem os HAR por `trafego.importar_har` e afirmam sobre CHAVES,
CONTAGENS e valores de CATÁLOGO (slug, código, nome de seguradora — que é dado
público do portal, não dado de segurado). Sem os HAR, esses blocos dão SKIP.
"""
from __future__ import annotations

import io
import sys
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import _replay_vidros as RV                              # noqa: E402
from portal_worker.journeys import vidros_api as A       # noqa: E402
from portal_worker.journeys import vidros_apifirst as AF  # noqa: E402
from portal_worker.journeys import vidros_estado as E    # noqa: E402

PASS = FAIL = 0


def check(nome, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [ok] " + nome)
    else:
        FAIL += 1
        print("  [FALHOU] " + nome + ("  " + str(extra)[:300] if extra else ""))


# ==========================================================================
print("\n[G2] a fronteira material sai da PECA, nunca de uma constante fixa")
# ==========================================================================
# 📊 Dois casos, mesma superfície, veredito oposto — é o que separa uma função
# de uma constante.
check("G2: `…|L` arma ANTES do PATCH",
      E.fronteira_materializar_de("1|142|S|11335|1|0|L") == E.FRONTEIRA_ATUALIZAR)
check("G2: `…|V` arma antes do POST /questionarios",
      E.fronteira_materializar_de("3|129|N|10700|1|0|V") == E.FRONTEIRA_MATERIALIZAR)
check("G2: `…|U` (roda/pneu) cai na MAIS conservadora",
      E.fronteira_materializar_de("2|121|S|11359|1|0|U") == E.FRONTEIRA_ATUALIZAR)
check("G2: chave quebrada cai na MAIS conservadora (fail-closed)",
      E.fronteira_materializar_de("isto nao e uma chave") == E.FRONTEIRA_ATUALIZAR)
check("G2 CONTROLE: os dois vereditos SAO diferentes — a funcao consegue diferir",
      E.fronteira_materializar_de("1|142|S|11335|1|0|L")
      != E.fronteira_materializar_de("3|129|N|10700|1|0|V"))

# 🔴 E o guarda que fecha a porta da regressão: a journey não pode voltar a
# NOMEAR `FRONTEIRA_MATERIALIZAR` como constante fixa para a fronteira B. Sem
# isto a volta é invisível — o código compila, a vidraçaria passa, e só a
# lataria quebra, em produção, com dinheiro.
import inspect  # noqa: E402

# 🔴 ATUALIZADO na EXTRA-001.10.1 (CLAUDE.md §9.3): a abertura virou FASES para
# a continuação reusar o MESMO código (§5, nenhum segundo motor). A fronteira B
# mora agora em `_fase_materializar` — a lição migra com ela, e um guarda novo
# prova que a abertura ainda passa por essa fase.
src_journey = inspect.getsource(AF._fase_materializar)
check("G2: a abertura delega as fases pos-protocolo a `rodar_fases`",
      "rodar_fases(" in inspect.getsource(AF.abrir_atendimento_api)
      and "_fase_materializar" in inspect.getsource(AF.rodar_fases))
check("G2: a journey CALCULA a fronteira (`fronteira_materializar_de` no corpo)",
      "fronteira_materializar_de" in src_journey)
i_calculo = src_journey.find("fronteira_materializar_de")
i_patch = src_journey.find("atualizar_atendimento(corpo_patch")
check("G2: e calcula ANTES de mandar o PATCH", -1 < i_calculo < i_patch,
      (i_calculo, i_patch))
# A fronteira B de vidraçaria continua sendo nomeada — mas DERIVADA, dentro do
# `if` que a calculou, nunca como decisão única do fluxo.
check("G2: o PATCH so arma o guard quando a fronteira calculada e a dele",
      "fronteira_b == ST.FRONTEIRA_ATUALIZAR" in src_journey)
check("G2: e o questionario so roda quando a fronteira calculada e a dele",
      "fronteira_b == ST.FRONTEIRA_MATERIALIZAR" in src_journey
      or "fronteira_b != ST.FRONTEIRA_MATERIALIZAR" in src_journey)

# ==========================================================================
print("\n[P2-1] nenhuma regua numerica de trincado no caminho API-first")
# ==========================================================================
# 📊 Havia três números para "trincado grande", e dois eram sobre coisas
# diferentes. A régua vem do portal (está escrita na pergunta dele) ou não
# existe. O guarda olha o CÓDIGO, não os comentários: citar a pergunta real do
# portal numa docstring é documentação; escrever o número no código é a régua.
CAMINHO_API_FIRST = ("vidros_api.py", "vidros_sessao.py", "vidros_estado.py",
                     "vidros_apifirst.py", "vidros_questionario.py")


def codigo_sem_comentarios(caminho: Path) -> str:
    """Só o código: comentários e literais de texto fora."""
    saida = []
    with caminho.open(encoding="utf-8") as fh:
        for tok in tokenize.generate_tokens(fh.readline):
            if tok.type in (tokenize.COMMENT, tokenize.STRING):
                continue
            saida.append(tok.string)
    return " ".join(saida)


import re  # noqa: E402

RE_CM = re.compile(r"\d+(?:\.\d+)?\s*(?:cm|centimetro)", re.I)
# 🔴 "DECLARAR" é definir, não mencionar. `vidros_questionario` IMPORTA o
# `_LIMITE_CM` do vocabulário do caminho DOM para **conferir** se a régua que o
# portal mandou é a mesma — e conferir é o oposto de declarar. O que este guarda
# proíbe é um `X_CM = <numero>` nascer aqui.
RE_DECLARA = re.compile(r"^\s*[A-Za-z_]*_CM\s*=\s*[-\d.]", re.M)
for nome in CAMINHO_API_FIRST:
    arquivo = ROOT / "portal_worker" / "journeys" / nome
    codigo = codigo_sem_comentarios(arquivo)
    bruto = arquivo.read_text(encoding="utf-8")
    check(f"P2-1: {nome} nao tem literal de centimetro no codigo",
          not RE_CM.search(codigo), RE_CM.search(codigo))
    check(f"P2-1: {nome} nao DECLARA constante de limite em cm",
          not RE_DECLARA.search(bruto), RE_DECLARA.search(bruto))

# E o par que prova que o guarda CONSEGUE ficar vermelho: os mesmos regexes,
# aplicados a um texto que tem a régua, acusam.
check("P2-1 CONTROLE: o regex acusa quando a regua ESTA no codigo",
      bool(RE_CM.search("limite = 10.0 cm"))
      and bool(RE_DECLARA.search("_LIMITE_CM = 10.0\n")))
check("P2-1 CONTROLE: e NAO acusa uma importacao de conferencia",
      not RE_DECLARA.search("from x import _LIMITE_CM as assumido\n"))

# A régua que o motor usa vem da PERGUNTA do portal.
from portal_worker.journeys import vidros_questionario as QZ  # noqa: E402

check("P2-1: o motor le a regua da pergunta real do portal",
      QZ.regua_da_pergunta("O TRINCADO ESTÁ MAIOR OU MENOR QUE 10 CM?") == 10.0)
check("P2-1: e le OUTRO numero quando o portal perguntar outro",
      QZ.regua_da_pergunta("MAIOR OU MENOR QUE 15 CM?") == 15.0)
check("P2-1: pergunta sem regua devolve None",
      QZ.regua_da_pergunta("QUAL O LADO DO ITEM DANIFICADO?") is None)
# 🔴 E se a régua do portal mudar, o motor PARA em vez de converter errado.
_p = QZ.Pergunta(codigo=8, texto="O TRINCADO ESTA MAIOR OU MENOR QUE 25 CM?",
                 tipo="A", opcoes=[
                     {"CodigoResposta": 1, "DescricaoResposta": "MAIOR (TROCA DO VIDRO)"},
                     {"CodigoResposta": 2, "DescricaoResposta": "MENOR (POSSIBILIDADE DE REPARO)"}])
_r = QZ.escolher_resposta(_p, respostas_do_segurado={"tamanho": "20 cm"})
check("P2-1: com a regua do portal diferente da assumida, o motor PARA",
      _r["situacao"] == QZ.FALTA_RESPOSTA, _r)
_p2 = QZ.Pergunta(codigo=8, texto="O TRINCADO ESTA MAIOR OU MENOR QUE 10 CM?",
                  tipo="A", opcoes=_p.opcoes)
_r2 = QZ.escolher_resposta(_p2, respostas_do_segurado={"tamanho": "20 cm"})
check("P2-1 CONTROLE: com a regua do portal igual, ele responde — os dois DIFEREM",
      _r2["situacao"] == "ok" and _r["situacao"] != "ok", (_r2["situacao"], _r["situacao"]))

# 📊 `StatusReparo` lido da OPÇÃO, como o portal o manda.
check("P2-1: `StatusReparo` da opcao de reparo e lido",
      QZ.Pergunta(codigo=8, texto="", tipo="A", opcoes=[
          {"CodigoResposta": 2, "DescricaoResposta": "MENOR (POSSIBILIDADE DE REPARO)",
           "StatusReparo": "S"}]).status_reparo_de("MENOR (POSSIBILIDADE DE REPARO)") == "S")

# ==========================================================================
print("\n[G3] a seguradora sai do dado AO VIVO — a lista fechada morreu")
# ==========================================================================
check("G3: `SLUGS_DE_SEGURADORA` nao existe mais na journey",
      not hasattr(AF, "SLUGS_DE_SEGURADORA"))
check("G3: `slug_da_seguradora` (lista fechada) nao existe mais na journey",
      not hasattr(AF, "slug_da_seguradora"))
# 🔴 ATUALIZADO em 20/09/2026 — a FATIA DE INTEGRAÇÃO (CLAUDE.md §9.3).
# O FATO mudou: os apelidos eram PARES `(fragmento, slug)` e passaram a ser
# TRIPLAS `(fragmento, slug, nome_de_tela)`, porque a tabela local de
# `portal_params` (que guardava o nome de tela) MORREU e a tradução virou uma
# só. A lição não mudou: continua sendo sequência (nunca `dict`) e continua
# ordenada do mais específico para o mais genérico.
check("G3: os apelidos sao TRIPLAS (fragmento, slug, nome_de_tela)",
      all(isinstance(t, tuple) and len(t) == 3
          for t in A.apelidos_de_seguradora()),
      A.apelidos_de_seguradora()[:2])
check("G3: e vem do mais especifico para o mais generico",
      [len(f) for f, _s, _t in A.apelidos_de_seguradora()]
      == sorted((len(f) for f, _s, _t in A.apelidos_de_seguradora()), reverse=True))
# 🔴 ATUALIZADO: `ITAU` VOLTOU à tabela — e a regra que importa não mudou.
# 📊 Ela não está entre as 38 que o portal publica, então `resolver_seguradora`
# continua devolvendo `None` para ela (asserção mais abaixo). O que a linha faz
# é dar ao caminho DOM o nome para digitar. Guardar a AUSÊNCIA na tabela seria
# guardar uma regra nossa no lugar da regra do portal; quem decide é a lista viva.
check("G3: `ITAU` esta na tabela so para o DOM saber o que digitar",
      [t for f, _s, t in A.apelidos_de_seguradora() if f == "ITAU"] == ["Itau"],
      [t for f, _s, t in A.apelidos_de_seguradora() if f == "ITAU"])

try:
    CHAMADAS = RV.carregar("NOVO")
except RV.HarAusente as e:
    print("  [SKIP] " + str(e))
    CHAMADAS = None

if CHAMADAS:
    LISTA = RV.primeira(CHAMADAS, "GET", "/seguradoras/") or []
    check("G3: o acervo tem a lista viva do portal", len(LISTA) == 38, len(LISTA))

    falhas = []
    inativas = 0
    for item in LISTA:
        nome_de_tela = item.get("NomeFantasia")
        resolvido = A.resolver_seguradora(nome_de_tela, LISTA)
        e_inativa = "(INATIVO)" in f"{item.get('Nome')}{nome_de_tela}".upper()
        if e_inativa:
            inativas += 1
            if resolvido is not None:
                falhas.append(("inativa resolveu", item.get("CodigoSeguradora")))
        elif not resolvido or resolvido["slug"] != item.get("CodigoSeguradora"):
            falhas.append((nome_de_tela, item.get("CodigoSeguradora"), resolvido))
    check("G3: TODA seguradora ativa resolve para o proprio slug", not falhas, falhas)
    check("G3: e a lista tem pelo menos uma INATIVA, que nao resolve",
          inativas >= 1, inativas)

    # Os casos nomeados na SPEC, um a um.
    def slug(nome):
        r = A.resolver_seguradora(nome, LISTA)
        return r["slug"] if r else None

    check("G3: 'yelum' resolve para LIBERTY (a marca mudou, o slug nao)",
          slug("yelum") == "LIBERTY")
    check("G3: 'Yelum Seguradora' tambem", slug("Yelum Seguradora") == "LIBERTY")
    check("G3: 'liberty' resolve para LIBERTY", slug("liberty") == "LIBERTY")
    check("G3: 'tokio' resolve para TOKIOMARINE", slug("tokio") == "TOKIOMARINE")
    check("G3: 'sompo' resolve para SOMPO (a rota `sompo`→GRUPO_HDI e de TELA)",
          slug("sompo") == "SOMPO")
    check("G3: 'porto' resolve para PORTO", slug("porto") == "PORTO")
    check("G3: 'itau' NAO resolve — o portal nao a publica", slug("itau") is None)
    check("G3: 'itaú' com acento tambem nao", slug("itaú") is None)
    check("G3: nome inventado nao resolve",
          slug("SEGURADORA QUE NAO EXISTE LTDA") is None)
    check("G3: 'nubank' nao resolve (o item esta marcado INATIVO)",
          slug("nubank") is None)
    check("G3: BRADESCO resolve na lista", slug("Bradesco") == "BRADESCO")
    check("G3: mas o API-first a devolve para o DOM (D-PILOTO-17)",
          "BRADESCO" in A.FORA_DO_API_FIRST)

    # `TipoAtendimento`: 📊 só a Porto sobrescreve.
    porto = RV.primeira(RV.carregar("PORTO"), "POST", "/atendimentos", requisicao=True)
    yelum = RV.primeira(CHAMADAS, "POST", "/atendimentos", requisicao=True)
    check("G3: a PORTO mandou TipoAtendimento = 1", porto.get("TipoAtendimento") == 1)
    check("G3 CONTROLE: a Yelum mandou null", yelum.get("TipoAtendimento") is None)
    check("G3: e o motor reproduz os dois",
          A.tipo_atendimento_para("PORTO", "lanterna") == 1
          and A.tipo_atendimento_para("LIBERTY", "para-brisa") is None)

# ==========================================================================
print("\n[G7] a escada da SPEC-077: APPROVED exige exercicio MEDIDO")
# ==========================================================================
if CHAMADAS is None:
    print("  [SKIP] sem o acervo nao da para contar exercicio nenhum")
else:
    def contar_exercicios():
        """📊 Conta, no acervo INTEIRO, quantas vezes cada endpoint de ESCRITA
        aconteceu de verdade. O acervo é lido por `importar_har`, que é um
        caminho independente do motor."""
        contagem = {ep: 0 for ep in A.METODO_DA_ESCRITA}
        for nome in RV.HARS:
            try:
                chamadas = RV.carregar(nome)
            except RV.HarAusente:
                continue
            # 🔴 `carregar` corta na desistência (o motor não cancela). Para
            # CONTAR exercícios a gente precisa do HAR inteiro — inclusive o
            # cancelamento e o abandono, que é o que prova que eles existem.
            from app.services.portals.lab.trafego import importar_har
            trafego = importar_har(RV.HARS[nome], host_portal=RV.HOST_PORTAL)
            for c in trafego:
                if c.host != RV.HOST_API or not c.escreve:
                    continue
                caminho = RV.caminho_de(c)
                ep = A.endpoint_do_caminho(caminho)
                if ep in contagem and A.METODO_DA_ESCRITA[ep] == c.metodo.upper():
                    contagem[ep] += 1
        return contagem

    EXERCICIOS = contar_exercicios()
    print("      📊 exercicios medidos no acervo, por endpoint de escrita:")
    for ep in sorted(EXERCICIOS):
        print(f"         {A.ESTADO_DO_ENDPOINT[ep]:<9} {EXERCICIOS[ep]:>2}x  "
              f"{A.METODO_DA_ESCRITA[ep]:<6} {ep}")

    aprovados_sem_exercicio = [ep for ep, n in EXERCICIOS.items()
                               if n == 0 and A.ESTADO_DO_ENDPOINT[ep] == A.APPROVED]
    check("G7: NENHUM endpoint de escrita APPROVED tem zero exercicios",
          not aprovados_sem_exercicio, aprovados_sem_exercicio)

    for ep in (A.EP_DIRECIONAMENTOS_NAO_MEDIDO,
               A.EP_FOTOGRAFIAS_WEB_NAO_MEDIDO, A.EP_FINALIZAR_NAO_MEDIDO,
               A.EP_AGENDAMENTOS_ENCAIXES_NAO_MEDIDO):
        check(f"G7: {ep} tem ZERO exercicios e e CANDIDATE",
              EXERCICIOS[ep] == 0 and A.ESTADO_DO_ENDPOINT[ep] == A.CANDIDATE,
              (EXERCICIOS[ep], A.ESTADO_DO_ENDPOINT[ep]))
    # 🔴 ATUALIZADO na EXTRA-001.10.1 (CLAUDE.md §9.3): `agendamentos` TINHA zero
    # exercícios e era CANDIDATE; as capturas de 21/09 o exercitaram (LATERAL
    # [048]) e ele foi PROMOVIDO. A lição não morre: a promoção só vale porque
    # a contagem, feita no acervo por `importar_har`, AGORA é ≥ 1.
    for ep in (A.EP_AGENDAMENTOS, A.EP_PRIORIDADES, A.EP_OCORRENCIAS):
        check(f"G7: {ep} foi PROMOVIDO porque o acervo o exercita (>= 1x)",
              EXERCICIOS[ep] >= 1 and A.ESTADO_DO_ENDPOINT[ep] == A.APPROVED,
              (EXERCICIOS[ep], A.ESTADO_DO_ENDPOINT[ep]))

    # 🔴 A MUTAÇÃO, permanente: promover um endpoint sem captura deixa o gate
    # VERMELHO. Sem este par, o G7 seria um carimbo. (Era `agendamentos`; hoje é
    # `direcionamentos`, que continua sem nenhum exercício.)
    original = dict(A.ESTADO_DO_ENDPOINT)
    try:
        A.ESTADO_DO_ENDPOINT[A.EP_DIRECIONAMENTOS_NAO_MEDIDO] = A.APPROVED
        promovidos = [ep for ep, n in EXERCICIOS.items()
                      if n == 0 and A.ESTADO_DO_ENDPOINT[ep] == A.APPROVED]
        check("G7 MUTACAO: promover `direcionamentos` sem captura acusa",
              A.EP_DIRECIONAMENTOS_NAO_MEDIDO in promovidos, promovidos)
    finally:
        A.ESTADO_DO_ENDPOINT.clear()
        A.ESTADO_DO_ENDPOINT.update(original)
    check("G7: e o registro voltou ao estado original",
          A.ESTADO_DO_ENDPOINT[A.EP_DIRECIONAMENTOS_NAO_MEDIDO] == A.CANDIDATE)

# ---- a recusa na SESSAO, que e onde a chamada morre -------------------
import asyncio  # noqa: E402

from portal_worker.journeys.vidros_sessao import SessaoVidros  # noqa: E402


class PaginaQueNaoDeviaSerChamada:
    def __init__(self):
        self.chamou = False

    async def evaluate(self, *a, **k):
        self.chamou = True
        return {"ok": True, "status": 200, "text": "{}"}


pagina = PaginaQueNaoDeviaSerChamada()
sessao = SessaoVidros(page=pagina, token="tok")
# 🔴 ATUALIZADO na EXTRA-001.10.1 (§9.3): o exemplo da recusa era `agendar`,
# que agora é APPROVED. A lição — CANDIDATE morre na SESSÃO, antes da rede,
# mesmo com token e freio liberados — continua provada com `direcionar`.
r = asyncio.run(sessao.direcionar({"CodigoCliente": 1}))
check("G7: `direcionar` NAO toca a rede, mesmo com token e freio liberados",
      pagina.chamou is False, pagina.chamou)
check("G7: e devolve `endpoint_candidate`", r.get("erro") == "endpoint_candidate", r)
check("G7: `abandonar` idem (1 exercicio medido, e AINDA assim CANDIDATE)",
      asyncio.run(sessao.abandonar("x"))["erro"] == "endpoint_candidate")
check("G7: `enviar_fotografias` (multipart) idem",
      asyncio.run(sessao.enviar_fotografias(codigo_atendimento="1", imagens=[])
                  )["erro"] == "endpoint_candidate")
check("G7: `gerar_link_vistoria` idem",
      asyncio.run(sessao.gerar_link_vistoria("0"))["erro"] == "endpoint_candidate")
check("G7 CONTROLE: um endpoint APPROVED CHEGA a tocar a pagina — os dois DIFEREM",
      (asyncio.run(sessao.opcoes_de_agendamento()) is not None) and pagina.chamou is True)
_pg_ag = PaginaQueNaoDeviaSerChamada()
asyncio.run(SessaoVidros(page=_pg_ag, token="tok").agendar({"CodigoCliente": 1}))
check("G7: `agendar` (promovido pela 001.10.1) agora SAI — a escada anda por medicao",
      _pg_ag.chamou is True)
check("G7: `cancelar` sem motivo do catalogo nao sai",
      asyncio.run(sessao.cancelar(codigo_atendimento="1", codigo_motivo=None)
                  )["erro"] == "motivo_de_cancelamento_ausente")

# ==========================================================================
print("\n[B1] o job que DEU CERTO nao entra na fila de aprendizado")
# ==========================================================================
# 🔴 Juiz B1, 20/09/2026 — REGRESSAO EM PRODUCAO COM A FLAG DESLIGADA.
# 📊 O caminho DOM grava `evidence["final"]` na tela de SUCESSO. O leitor da
# fila caia em ("debug_dom", "final") e transformava TODO job DOM `done` em
# linha de tela cega; o gravador da marca regravava a evidence LIDA ANTES e
# apagava `entregue_ao_agente` — e o Vigia mandava uma SEGUNDA mensagem ao
# segurado sobre o atendimento que ele ja tinha recebido.
from app.agents.tools import portal_params as PP2  # noqa: E402

_DOM_DONE = {"final": {"texto": "No do atendimento: 23298628 - CONFIRMADO"},
             "protocolo": "23298628", "entregue_ao_agente": True}
check("B1: DOM `done` com `final` NAO vira linha de tela cega",
      PP2.resumo_da_tela_desconhecida(_DOM_DONE) is None,
      PP2.resumo_da_tela_desconhecida(_DOM_DONE))
check("B1: nem com desfecho conhecido",
      PP2.resumo_da_tela_desconhecida(
          {"desfecho": {"tipo": "loja_direta"}, "final": {"texto": "x" * 40}}) is None)
check("B1: nem com o estado dizendo que o numero nasceu",
      PP2.resumo_da_tela_desconhecida(
          {"vidros_estado": {"tem_codigo_atendimento": True},
           "debug_dom": "tela qualquer"}) is None)
check("B1 CONTROLE: mas tela REALMENTE desconhecida continua ensinando",
      (PP2.resumo_da_tela_desconhecida(
          {"tela_desconhecida": {"onde": "/x", "resumo": ["A", "B"]},
           "protocolo": "23298628"}) or {}).get("onde") == "/x")
check("B1 CONTROLE: e um job que parou SEM numero tambem ensina",
      PP2.resumo_da_tela_desconhecida({"debug_dom": "tela nova que ninguem viu"})
      is not None)
# 🔴 E a marca de entrega sobrevive ao gravador da fila: as duas marcas juntas.
import inspect as _insp  # noqa: E402

from app.agents.tools import portal_tool as PT  # noqa: E402

_src_aprender = _insp.getsource(PT.PortalActionTool._aprender_com_a_tela_cega)
check("B1: o gravador RELE a evidence do banco antes de escrever",
      "select(\"evidence\")" in _src_aprender or 'select("evidence")' in _src_aprender,
      _src_aprender[:200])
check("B1: e preserva `entregue_ao_agente` explicitamente",
      "entregue_ao_agente" in _src_aprender)
_i_update = _src_aprender.find(".update(")
_i_rele = _src_aprender.find("select")
check("B1: e a releitura vem ANTES do update", -1 < _i_rele < _i_update,
      (_i_rele, _i_update))

# ==========================================================================
print("\n[B4] TODA parada da journey tem texto proprio, e nenhum promete continuacao")
# ==========================================================================
# 🔴 Os stages sao EXTRAIDOS do codigo, nunca listados a mao: uma parada nova
# sem texto proprio cairia na frase generica do DOM ("confirme onde o servico
# sera feito... domicilio"), que fala de uma tela que a API-first nem abre.
import re as _re  # noqa: E402

# 🔴 ATUALIZADO na EXTRA-001.10.1 (§9.3): as paradas viraram `_parar(ex, "…")`
# (fases reusadas pela continuação) e a journey nova `vidros_continuacao` tem
# as dela (`stage="…"`). A extração acompanha a forma nova e lê os DOIS
# arquivos — sem isso ela acharia 3 stages e o guarda viraria carimbo.
_src_journey = "\n".join(
    (ROOT / "portal_worker" / "journeys" / f).read_text(encoding="utf-8")
    for f in ("vidros_apifirst.py", "vidros_continuacao.py"))
_stages = sorted(set(_re.findall(r'parar\(\s*(?:ex,\s*)?"([a-z_]+)"', _src_journey))
                 | set(_re.findall(r'"stage": "([a-z_]+)"', _src_journey))
                 | set(_re.findall(r'stage="([a-z_]+)"', _src_journey)))
check("B4: a extracao achou os stages da journey (>= 15)", len(_stages) >= 15,
      len(_stages))
_sem_texto = [st for st in _stages if PP2.texto_da_parada(st) is None]
check("B4: TODO stage da journey tem texto proprio", not _sem_texto, _sem_texto)

# 🔴 VERDADE VENCIDA atualizada na EXTRA-001.10.1 (CLAUDE.md §9.3). A asserção
# era "NENHUM texto promete continuação (ela não existe)" — e a continuação
# passou a existir (`vidros_continuacao.continuar_atendimento`). A LIÇÃO não
# morre, migra: prometer "eu continuo" sobre um token que não foi guardado é o
# texto mentindo ao segurado. Então: nenhum texto promete continuação SEM A
# PROVA (`evidence.continuacao.possivel is True`) — nem o de `texto_da_parada`,
# nem o que `format_result` entrega ao agente, e "possivel" em TEXTO não é prova.
_PROMESSAS = ("sigo daqui", "continua do mesmo ponto", "chame de novo",
              "me chame de novo", "proximo dia util", "próximo dia útil",
              "eu continuo", "me responde por aqui", "ja estou tentando de novo",
              "já estou tentando de novo", "que eu agendo", "pode continuar por aqui")


def _promessas_em(texto):
    return [pr for pr in _PROMESSAS if pr in str(texto or "").lower()]


_promete = []
for _st in _stages:
    for _sem_prova in ({}, {"possivel": False}, {"possivel": "true"}, {"possivel": 1}):
        _flag = PP2.continuacao_possivel({"continuacao": _sem_prova})
        _txt = " ".join(PP2.texto_da_parada(_st, _flag) or [])
        _fr = PP2.format_result({"status": "needs_human", "evidence": {
            "stage": _st, "protocolo": "23298628",
            "continuacao": {**_sem_prova, "acao_esperada": "responder:peca"}}})
        if _promessas_em(_txt) or _promessas_em(_fr):
            _promete.append((_st, _sem_prova, _promessas_em(_txt) + _promessas_em(_fr)))
check("B4: NENHUM texto promete continuacao SEM a prova (continuacao.possivel is True)",
      not _promete, _promete[:4])
# CONTROLE (§9.3 corolário: o guarda tem de CONSEGUIR ficar vermelho): COM a
# prova, as paradas que o segurado responde passam a prometer — então a
# varredura acima enxerga a promessa quando ela está lá.
_com_prova = [st for st in PP2.ESTAGIOS_QUE_O_SEGURADO_RESPONDE
              if _promessas_em(PP2.format_result({"status": "needs_human", "evidence": {
                  "stage": st, "protocolo": "23298628",
                  "continuacao": {"possivel": True, "acao_esperada": "responder:peca"}}}))]
check("B4 CONTROLE: COM a prova, toda parada que o segurado responde promete (a varredura ve)",
      sorted(_com_prova) == sorted(PP2.ESTAGIOS_QUE_O_SEGURADO_RESPONDE),
      sorted(set(PP2.ESTAGIOS_QUE_O_SEGURADO_RESPONDE) - set(_com_prova)))
# O numero vem primeiro, e o de 16 digitos nao e apresentado como o de 8.
_msg8 = PP2.format_result({"status": "needs_human",
                           "evidence": {"stage": "motivo_ambiguo", "protocolo": "23298628"}})
check("B4: a mensagem ABRE com o numero do atendimento",
      _msg8.strip().startswith("NUMERO DO ATENDIMENTO: 23298628"), _msg8[:80])
_msg16 = PP2.format_result({"status": "needs_human",
                            "evidence": {"stage": "maybe_committed",
                                         "protocolo": "1234567890123456"}})
check("B4: com so o protocolo de 16, ele e chamado de PROTOCOLO INICIAL",
      "PROTOCOLO INICIAL" in _msg16 and "NUMERO DO ATENDIMENTO" not in _msg16,
      _msg16[:120])
check("B4: e a mensagem avisa que ele nao serve por telefone",
      "nao adianta" in _msg16.lower() or "não adianta" in _msg16.lower())
# E nenhuma parada cai na frase do DOM.
for _st in _stages:
    _m = PP2.format_result({"status": "needs_human",
                            "evidence": {"stage": _st, "protocolo": "23298628"}})
    if _st == "pronto_para_abrir":
        continue
    check(f"B4: {_st} nao cai na frase do DOM (domicilio/loja a escolher)",
          "tecnico a domicilio" not in _m.lower() and "técnico a domicílio" not in _m.lower(),
          _m[:120])

# ==========================================================================
print("\n[B-freio] allowlist so com separadores BARRA TUDO (fail-closed)")
# ==========================================================================
import os as _os  # noqa: E402

from portal_worker import journeys as _JN  # noqa: E402

_antes = (_os.environ.get("PORTAL_EFEITO_MATERIAL_LIBERADO"),
          _os.environ.get("PORTAL_CANARIO_ALLOWLIST"))
try:
    _os.environ["PORTAL_EFEITO_MATERIAL_LIBERADO"] = "true"
    _h = _JN.cpf_hash_de("01234567890")
    for _valor in (",", " , ", ",,", "job:", "cpf:", "abc-1", _h):
        _os.environ["PORTAL_CANARIO_ALLOWLIST"] = _valor
        _barrou = bool(_JN.motivo_para_barrar("vidros_lanternas", "abrir_atendimento",
                                              job_id="abc-1", cpf_hash=_h))
        check(f"B-freio: allowlist {_valor!r} BARRA ate o job alvo", _barrou, _valor)
    _os.environ["PORTAL_CANARIO_ALLOWLIST"] = "job:abc-1"
    check("B-freio CONTROLE: allowlist bem escrita deixa o job alvo passar",
          not _JN.motivo_para_barrar("vidros_lanternas", "abrir_atendimento",
                                     job_id="abc-1", cpf_hash=_h))
    check("B-freio CONTROLE: e barra o outro job",
          bool(_JN.motivo_para_barrar("vidros_lanternas", "abrir_atendimento",
                                      job_id="outro", cpf_hash="")))
    _os.environ["PORTAL_CANARIO_ALLOWLIST"] = ""
    check("B-freio CONTROLE: allowlist AUSENTE continua sendo o comportamento de hoje",
          not _JN.motivo_para_barrar("vidros_lanternas", "abrir_atendimento",
                                     job_id="abc-1", cpf_hash=_h))
finally:
    for _k, _v in zip(("PORTAL_EFEITO_MATERIAL_LIBERADO", "PORTAL_CANARIO_ALLOWLIST"),
                      _antes):
        if _v is None:
            _os.environ.pop(_k, None)
        else:
            _os.environ[_k] = _v

# ==========================================================================
print("\n[B-rota] a allowlist de endpoint nao se burla por caixa nem por barra")
# ==========================================================================
# 🔴 ATUALIZADO na EXTRA-001.10.1 (§9.3): as variações eram de `/agendamentos`,
# que virou APPROVED. A lição (caixa, barra, espaço e `;` não burlam o
# registro) migra para `/direcionamentos`, que continua CANDIDATE.
for _c in ("/Direcionamentos", "/DIRECIONAMENTOS", "//direcionamentos",
           "/direcionamentos ", " /direcionamentos", "/direcionamentos/",
           "/./direcionamentos", "/direcionamentos;v=1", "/direcionamentos?x=1",
           "/atendimentos/Abandonar", "/atendimentos-fotografias/WEB"):
    check(f"B-rota: {_c!r} NAO pode sair", not A.pode_sair(_c, "POST"), _c)
# 🔴 E a porta que a promoção abriria: com `/agendamentos` APPROVED, o casamento
# pelo prefixo deixava sair QUALQUER `POST /agendamentos/…` — escrita só sai
# no endereço EXATO (ou + `/{codigo}`).
for _c in ("/agendamentos/encaixes", "/agendamentos/insatisfacao",
           "/agendamentos/qualquer-coisa", "/atendimentos/livres-escolhas"):
    check(f"B-rota: {_c!r} NAO pode sair (prefixo de endpoint APPROVED)",
          not A.pode_sair(_c, "POST"), _c)
check("B-rota CONTROLE: o agendamento medido sai, e sai por qualquer grafia dele",
      A.pode_sair("/agendamentos", "POST") and A.pode_sair("/Agendamentos/", "POST"))
check("B-rota: escrita em endpoint FORA do registro tambem nao sai (fail-closed)",
      not A.pode_sair("/rota/que/ninguem/mediu", "POST"))
check("B-rota CONTROLE: leitura fora do registro continua podendo",
      A.pode_sair("/rota/que/ninguem/mediu", "GET"))
check("B-rota CONTROLE: e um endpoint APPROVED de escrita sai",
      A.pode_sair("/solicitantes", "POST"))

# ==========================================================================
print("\n[B-fraude] bloqueio do portal nunca vira 'pode ligar para a loja'")
# ==========================================================================
_CONCLUSAO_OK = {"IrParaConclusaoDeAtendimento": True, "ExisteOrdemServico": True,
                 "DisponibilizarAgendamento": False, "OpcoesAgendamento": []}
_AGREGADO = {"ScriptFinalizacao": {"Titulo": "As informacoes abaixo",
                                   "InformacoesAdicionais": [
                                       {"Titulo": "Loja", "Valor": "LOJA X"},
                                       {"Titulo": "Endereço", "Valor": "RUA Y"}]}}
check("B-fraude CONTROLE: sem bloqueio, esta resposta da loja_direta",
      E.ler_desfecho(_CONCLUSAO_OK, _AGREGADO)["tipo"] == E.DESFECHO_LOJA_DIRETA)
# 🔴 ATUALIZADO na EXTRA-001.10.1 (§9.3): `BloqueadoIlhaNormal` SAIU das travas.
# 📊 Zero ocorrências nos 3 bundles do SPA (laudo §2), e no HAR LATARIA [089]
# ele veio `true` e o portal SEGUIU até a conclusão ([092]→[093]→[094]). A
# lição (bloqueio de fraude nunca vira "pode ir à loja") continua nas outras.
_d_ilha = E.ler_desfecho({**_CONCLUSAO_OK, "BloqueadoIlhaNormal": True}, _AGREGADO)
check("B-fraude: `BloqueadoIlhaNormal` sozinho NAO trava (o portal segue)",
      _d_ilha["tipo"] == E.DESFECHO_LOJA_DIRETA and not _d_ilha.get("bloqueios"),
      _d_ilha["tipo"])
for _trava in ("BloqueadoPorFraude", "ExibirAvisoVistoriaPorRegraDeFraude"):
    _d = E.ler_desfecho({**_CONCLUSAO_OK, _trava: True}, _AGREGADO)
    check(f"B-fraude: com {_trava} o desfecho e `desconhecido`",
          _d["tipo"] == E.DESFECHO_DESCONHECIDO, _d["tipo"])
    check(f"B-fraude: e {_trava} fica registrado para o dossie",
          _trava in (_d.get("bloqueios") or []), _d.get("bloqueios"))
    check(f"B-fraude: e NENHUMA loja e prometida com {_trava}",
          not _d.get("loja") and not _d.get("lojas"))

# ==========================================================================
print("\n[B-cancelar] cancelar exige guard armado e motivo do catalogo")
# ==========================================================================
class _PaginaQueContaTudo:
    def __init__(self):
        self.saiu = []

    async def evaluate(self, js, arg):
        self.saiu.append(arg.get("url"))
        return {"ok": True, "status": 200, "text": "{}"}


_pg = _PaginaQueContaTudo()
_ses = SessaoVidros(page=_pg, token="tok")
_r = asyncio.run(_ses.cancelar(codigo_atendimento="1", codigo_motivo=39))
check("B-cancelar: sem guard, NAO sai", _pg.saiu == [] and _r.get("erro"), _r)
check("B-cancelar: e o erro diz que falta o guard",
      _r.get("erro") == "cancelamento_sem_guard", _r.get("erro"))
from portal_worker import guardrails as G  # noqa: E402

_guard_fechado = G.PortalActionGuard(material_liberado=False,
                                     acao_material_esperada=E.FRONTEIRA_CANCELAR)
_r2 = asyncio.run(_ses.cancelar(codigo_atendimento="1", codigo_motivo=39,
                                guard=_guard_fechado))
check("B-cancelar: com guard FECHADO, NAO sai", _pg.saiu == [], _pg.saiu)
check("B-cancelar: e o erro diz que foi bloqueado",
      _r2.get("erro") == "cancelamento_bloqueado", _r2.get("erro"))
_guard_aberto = G.PortalActionGuard(material_liberado=True,
                                    acao_material_esperada=E.FRONTEIRA_CANCELAR)
_r3 = asyncio.run(_ses.cancelar(codigo_atendimento="1", codigo_motivo=39,
                                guard=_guard_aberto,
                                motivos_do_catalogo=[{"Codigo": 12, "Descricao": "OUTRO"}]))
check("B-cancelar: motivo fora do catalogo lido NAO sai", _pg.saiu == [], _pg.saiu)
check("B-cancelar: e o erro nomeia o catalogo",
      _r3.get("erro") == "motivo_fora_do_catalogo", _r3.get("erro"))
_r4 = asyncio.run(_ses.cancelar(codigo_atendimento="1", codigo_motivo=39,
                                guard=_guard_aberto,
                                motivos_do_catalogo=[{"Codigo": 39, "Descricao": "X"}]))
check("B-cancelar CONTROLE: guard aberto + motivo do catalogo SAI — os casos DIFEREM",
      len(_pg.saiu) == 1 and _r4.get("status") == 200, (_pg.saiu, _r4.get("status")))


print("\n" + "=" * 66)
print(f"  {PASS} asserções verdes · {FAIL} vermelhas")
print("=" * 66)
sys.exit(1 if FAIL else 0)
