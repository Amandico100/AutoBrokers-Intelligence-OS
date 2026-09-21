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

src_journey = inspect.getsource(AF.abrir_atendimento_api)
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
      "fronteira_b == ST.FRONTEIRA_MATERIALIZAR" in src_journey)

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

    for ep in (A.EP_AGENDAMENTOS_NAO_MEDIDO, A.EP_DIRECIONAMENTOS_NAO_MEDIDO,
               A.EP_FOTOGRAFIAS_WEB_NAO_MEDIDO, A.EP_FINALIZAR_NAO_MEDIDO):
        check(f"G7: {ep} tem ZERO exercicios e e CANDIDATE",
              EXERCICIOS[ep] == 0 and A.ESTADO_DO_ENDPOINT[ep] == A.CANDIDATE,
              (EXERCICIOS[ep], A.ESTADO_DO_ENDPOINT[ep]))

    # 🔴 A MUTAÇÃO, permanente: promover `agendamentos` sem captura deixa o
    # gate VERMELHO. Sem este par, o G7 seria um carimbo.
    original = dict(A.ESTADO_DO_ENDPOINT)
    try:
        A.ESTADO_DO_ENDPOINT[A.EP_AGENDAMENTOS_NAO_MEDIDO] = A.APPROVED
        promovidos = [ep for ep, n in EXERCICIOS.items()
                      if n == 0 and A.ESTADO_DO_ENDPOINT[ep] == A.APPROVED]
        check("G7 MUTACAO: promover `agendamentos` sem captura acusa",
              A.EP_AGENDAMENTOS_NAO_MEDIDO in promovidos, promovidos)
    finally:
        A.ESTADO_DO_ENDPOINT.clear()
        A.ESTADO_DO_ENDPOINT.update(original)
    check("G7: e o registro voltou ao estado original",
          A.ESTADO_DO_ENDPOINT[A.EP_AGENDAMENTOS_NAO_MEDIDO] == A.CANDIDATE)

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
r = asyncio.run(sessao.agendar({"CodigoCliente": 1}))
check("G7: `agendar` NAO toca a rede, mesmo com token e freio liberados",
      pagina.chamou is False, pagina.chamou)
check("G7: e devolve `endpoint_candidate`", r.get("erro") == "endpoint_candidate", r)
check("G7: `direcionar` idem",
      asyncio.run(sessao.direcionar({}))["erro"] == "endpoint_candidate")
check("G7: `abandonar` idem (1 exercicio medido, e AINDA assim CANDIDATE)",
      asyncio.run(sessao.abandonar("x"))["erro"] == "endpoint_candidate")
check("G7: `enviar_fotografias` (multipart) idem",
      asyncio.run(sessao.enviar_fotografias(codigo_atendimento="1", imagens=[])
                  )["erro"] == "endpoint_candidate")
check("G7: `gerar_link_vistoria` idem",
      asyncio.run(sessao.gerar_link_vistoria("0"))["erro"] == "endpoint_candidate")
check("G7 CONTROLE: um endpoint APPROVED CHEGA a tocar a pagina — os dois DIFEREM",
      (asyncio.run(sessao.opcoes_de_agendamento()) is not None) and pagina.chamou is True)
check("G7: `cancelar` sem motivo do catalogo nao sai",
      asyncio.run(sessao.cancelar(codigo_atendimento="1", codigo_motivo=None)
                  )["erro"] == "motivo_de_cancelamento_ausente")

print("\n" + "=" * 66)
print(f"  {PASS} asserções verdes · {FAIL} vermelhas")
print("=" * 66)
sys.exit(1 if FAIL else 0)
