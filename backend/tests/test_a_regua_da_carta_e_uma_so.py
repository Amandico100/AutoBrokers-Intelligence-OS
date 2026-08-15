"""A régua de uma carta é UMA só — e o portão de PII fecha no eixo certo.

DOIS DEFEITOS, UMA CAUSA: A REGRA MORAVA EM VÁRIOS LUGARES
===========================================================

DEFEITO 1 — o teto de 400 caracteres, escrito à mão em quatro pontos
--------------------------------------------------------------------
`attendance_distiller`, `aplicar.py`, `aplicar_sql.py` e
`atribuir_seguradora.py` cada um carregava `if len(texto) < 15 or > 400`. O
caminho do acervo (`publicar_cartas.py`) usava 40–1800. **Duas réguas para a
mesma tabela**, e a que matava era a de 400.

📊 Medido em 15/08/2026 sobre a leva 5 (72 lotes, 1.527 fatos destilados):

    23 mortos    TODOS por passar de 400
     0 mortos    por ficar abaixo de 15

O piso nunca descartou nada — em lugar nenhum. 📊 Das 18.598 cartas já gravadas
no acervo, **uma** tem menos de 40 caracteres e **zero** têm menos de 15.

E o padrão do que o teto matava é perverso: **quanto mais completa a carta,
maior a chance de morrer.** Os 23 são listas de documentos, conjuntos fechados
de exigências, relações de itens — longos PORQUE são completos, que é
exatamente o que os torna úteis. Três eram inéditos no acervo.

DEFEITO 2 — `rejected_pii` disparava por vocabulário, não por dado pessoal
--------------------------------------------------------------------------
A regra era `templatize(texto) != texto`: **qualquer coisa que o mascarador
encostasse** derrubava a carta.

📊 As 320 cartas em `rejected_pii` passaram por todos os detectores: ZERO têm
CPF, CNPJ, telefone, placa, e-mail ou nome de pessoa. E medidas contra o
`templatize` de hoje, 315 das 320 não são tocadas por regra nenhuma — as regras
que as derrubaram já foram consertadas, e a rejeição ficou de pé sozinha porque
foi gravada uma vez e nunca reavaliada.

O QUE ESTE TESTE GUARDA
=======================
Ele anda nas DUAS direções de propósito, que é a única forma de um guarda de
PII não virar decoração:

  * conhecimento longo e limpo SOBREVIVE       (senão o acervo empobrece calado)
  * identificador de pessoa continua BARRADO   (senão o portão não guarda nada)

E o teste de MUTAÇÃO existe porque **um guarda que não tem como falhar não
guarda nada** (CLAUDE.md §9.3): ele prova que os quatro casos de PII de verdade
CONSEGUEM ser rejeitados, e não que a função devolve sempre a mesma coisa.

A LINHA DE CONTROLE (§9.2)
--------------------------
`teste_o_teto_de_400_nao_volta` compara a carta de 900 caracteres com a MESMA
carta em 401 caracteres. As duas passariam de 400. Se as duas sobrevivem, o
fator "passar de 400" deixou de importar — e é isso que dá direito à conclusão.
Sem a linha de controle, uma carta de 900 que passa poderia estar passando por
qualquer outro motivo.
"""

from __future__ import annotations

import importlib.util
import os
import re
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FALHAS: list[str] = []

# O console do Windows abre em cp1252 e os marcadores 📊/⚠️ do CLAUDE.md §12.1
# não cabem nele. Sem esta linha o teste MORRE de UnicodeEncodeError no meio de
# uma asserção que passou — e um teste que explode ao imprimir o resultado é
# indistinguível de um teste que reprovou.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Pacotes de fachada: `app/__init__.py` real arrasta openai e pydantic_settings.
# O mesmo desenho de `mascarar.py` e dos outros testes deste diretório.
for _n, _p in (("app", ("app",)), ("app.services", ("app", "services")),
               ("app.services.atlas", ("app", "services", "atlas"))):
    if _n not in sys.modules:
        _m = types.ModuleType(_n)
        _m.__path__ = [os.path.join(RAIZ, *_p)]
        _m.__package__ = _n
        sys.modules[_n] = _m


def _carregar(nome: str, *partes: str):
    caminho = os.path.join(RAIZ, *partes)
    spec = importlib.util.spec_from_file_location(nome, caminho)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nome] = mod
    spec.loader.exec_module(mod)
    return mod


_carregar("app.services.atlas.templater", "app", "services", "atlas", "templater.py")
C = _carregar("app.services.curadoria_cartas", "app", "services", "curadoria_cartas.py")


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


# ─────────────────────────────────────────────────────────────────────────────
# O material real: uma das 23 cartas que o teto de 400 matou.
# ─────────────────────────────────────────────────────────────────────────────
# Esta é a relação de documentos de indenização integral do lote_025 — 429
# caracteres. Cortá-la pela metade faz a carta MENTIR POR OMISSÃO: o corretor lê
# metade da lista e conclui que o resto não é exigido.
LISTA_DE_DOCUMENTOS = (
    "Relacao de documentos de indenizacao integral: CRV/DUT ou ATPV-e com "
    "reconhecimento de firma por autenticidade, chave de seguranca do documento "
    "digital, comprovante de quitacao de financiamento quando houver gravame, "
    "certidao negativa de multas e IPVA do exercicio, laudo de vistoria previa "
    "de baixa de chassi emitido pelo Detran do estado de registro, procuracao "
    "com poderes especificos para transferencia quando o titular nao assinar "
    "pessoalmente, e comprovante bancario em nome do proprio segurado para o "
    "deposito da indenizacao."
)

# 📊 Não é exemplo inventado: são 900+ caracteres de lista taxativa, o formato
# que `publicar_cartas.py` já tinha medido e defendido em 09/08/2026 quando
# subiu o próprio teto de 900 para 1.800.
LISTA_DE_900 = LISTA_DE_DOCUMENTOS + " " + (
    "Quando o veiculo esta em nome de pessoa juridica, acrescentam-se o contrato "
    "social consolidado, a ata de eleicao da diretoria vigente e o documento de "
    "identificacao do representante legal que assina a transferencia. Quando ha "
    "consorcio ou arrendamento mercantil, a carta de liberacao da instituicao "
    "credora substitui o comprovante de quitacao, e ela precisa citar o chassi "
    "do veiculo para ser aceita pela seguradora na conferencia final do processo."
)

# A LINHA DE CONTROLE: a mesma carta, cortada logo depois de 400. Se ela
# sobrevive e a de 900 também, o fator "passar de 400" não decide mais nada.
CONTROLE_401 = LISTA_DE_DOCUMENTOS[:401]

# ─────────────────────────────────────────────────────────────────────────────
# Os quatro casos de PII de verdade. O portão TEM de fechar em cada um.
# ─────────────────────────────────────────────────────────────────────────────
# Todos com 40+ caracteres de propósito: o teste tem de provar que a rejeição
# vem do DADO, não do tamanho.
MUTACOES = {
    "CPF": "Para abrir o sinistro a seguradora pediu o CPF 123.456.789-00 "
           "do condutor principal informado na apolice do veiculo.",
    "telefone": "A central de assistencia retornou a ligacao no telefone "
                "(48) 99147-8922 informado pelo segurado no acionamento.",
    "placa": "O guincho foi acionado para o veiculo de placa ABC1D23 que "
             "estava parado na oficina credenciada desde a semana passada.",
    "nome de corretora": "Maria Regina - Autofleet Seguros confirmou a "
                         "abertura do processo junto a seguradora responsavel.",
}

# Cartas legítimas que o gate DERRUBAVA por vocabulário de contexto. Todas são
# texto real das 320 `rejected_pii`.
CONHECIMENTO_QUE_ERA_BARRADO = [
    "Antes de perguntar o que aconteceu, a Yelum exige nome de quem esta no "
    "local, celular com DDD confirmado por botao, cor do veiculo e se o "
    "veiculo esta em condicoes de rodar.",
    "A senha que libera a visita tecnica na Yelum sao os 4 ULTIMOS DIGITOS do "
    "celular informado de quem esta no local, ou do WhatsApp que pediu a "
    "assistencia.",
    "O acesso ao chat de sinistros do Bradesco depende do e-mail cadastrado da "
    "corretora, que recebe o codigo de acesso; se esse e-mail e de outra pessoa "
    "e ela esta indisponivel, nao ha caminho alternativo pelo chat e o "
    "atendimento tem de ser feito pelo 0800.",
    "CORRECAO DE ACERVO: encerramento do canal de atendimento nao e "
    "encerramento do direito. A reanalise continua possivel depois dele, e o "
    "segurado precisa ser avisado disso.",
    "Veiculo 100% eletrico na Yelum nao muda o fluxo de pneu furado: ela faz as "
    "mesmas perguntas de estepe, chave de roda e macaco e abre troca de pneus "
    "no mesmo caminho.",
]

# Os quatro pontos de ingestão que carregavam o literal. Se alguém reintroduzir
# um `400` num deles, este teste tem de acusar.
INGESTORES = (
    ("app/services/attendance_distiller.py", "_store_card_sync"),
    ("scripts/destilacao_max/aplicar.py", "_cartas_de"),
    ("scripts/destilacao_max/aplicar_sql.py", "main"),
    ("scripts/destilacao_max/atribuir_seguradora.py", "main"),
    ("scripts/acervo/publicar_cartas.py", "_conferir"),
)

# ⚠️ A FAIXA É ESTREITA DE PROPÓSITO, e a primeira escrita deste guarda estava
# larga demais: `len\(\w+\)\s*[<>]=?\s*\d+` acusava `len(lote) < 1000` (paginação
# do banco), `len(text) < 80` (sessão sem conteúdo) e `len(texto) >= 200` (a
# checagem de encoding quebrado do acervo). Nenhum é corte de carta.
#
# Um guarda que grita em tudo é desligado na primeira semana, e aí ele não
# guarda mais nada. O que este teste tem de pegar é a REINTRODUÇÃO do par que
# matou as 23 — então a faixa é a do par:
#
#     piso  `len(x) <  N`  com N entre 10 e 39   (o 15 antigo, ou vizinho dele)
#     teto  `len(x) >  N`  com N entre 300 e 500 (o 400 antigo, ou vizinho dele)
#
# 💭 Se alguém reintroduzir um teto de 2.000, este guarda não acusa — e está
# certo que não acuse: 2.000 não é o defeito, é outra decisão, e ela cai no
# `checar` de que o arquivo usa a régua compartilhada.
_PISO_A_MAO = re.compile(r"len\(\s*\w+\s*\)\s*<=?\s*(\d+)")
_TETO_A_MAO = re.compile(r"len\(\s*\w+\s*\)\s*>=?\s*(\d+)")


def _cortes_de_carta_a_mao(codigo: str) -> list:
    """Comparações de tamanho na faixa em que uma carta é cortada."""
    achados = []
    for m in _PISO_A_MAO.finditer(codigo):
        if 10 <= int(m.group(1)) <= 39:
            achados.append(m.group(0))
    for m in _TETO_A_MAO.finditer(codigo):
        if 300 <= int(m.group(1)) <= 500:
            achados.append(m.group(0))
    return achados


def teste_o_teto_de_400_nao_volta():
    print("\n[1] O teto de 400 não volta — e a lista de 900 sobrevive")
    checar(C.MAX_CARACTERES == 1800,
           "o teto da régua única é 1.800 (limite físico de uma mensagem)",
           f"é {C.MAX_CARACTERES}")
    checar(C.MIN_CARACTERES == 40,
           "o piso é 40 — o mesmo do acervo, e 📊 nunca descartou nada",
           f"é {C.MIN_CARACTERES}")

    checar(len(LISTA_DE_900) > 900,
           f"a carta de exemplo tem {len(LISTA_DE_900)} caracteres (>900)")
    checar(C.fora_do_tamanho(LISTA_DE_900) is None,
           "uma LISTA DE DOCUMENTOS de 900+ caracteres SOBREVIVE",
           str(C.fora_do_tamanho(LISTA_DE_900)))

    # A LINHA DE CONTROLE. Ver o cabeçalho: é ela que dá direito à conclusão.
    checar(len(CONTROLE_401) == 401, "o controle tem exatamente 401 caracteres")
    checar(C.fora_do_tamanho(CONTROLE_401) is None,
           "CONTROLE: a mesma carta em 401 caracteres também sobrevive "
           "— logo 'passar de 400' deixou de ser o fator",
           str(C.fora_do_tamanho(CONTROLE_401)))

    # E o guarda continua guardando NAS DUAS PONTAS: um teto que aceita tudo
    # não é teto. 1.801 é onde o texto deixa de caber numa mensagem.
    checar(C.fora_do_tamanho("x" * 1801) is not None,
           "MUTAÇÃO: 1.801 caracteres CONTINUA sendo recusado "
           "— o teto existe, só mudou de lugar")
    checar(C.fora_do_tamanho("x" * 39) is not None,
           "MUTAÇÃO: 39 caracteres continua sendo recusado")


def teste_nenhum_ingestor_carrega_a_regua_propria():
    print("\n[2] Nenhum dos cinco pontos de ingestão escreve o número à mão")
    for caminho, funcao in INGESTORES:
        corpo = open(os.path.join(RAIZ, caminho), encoding="utf-8").read()
        # Só o CÓDIGO: os comentários contam a história de por que o 400 morreu,
        # e apagá-los para o teste passar seria trocar a memória pelo verde.
        codigo = "\n".join(l for l in corpo.splitlines()
                           if not l.lstrip().startswith("#"))
        cortes = _cortes_de_carta_a_mao(codigo)
        checar(not cortes,
               f"{caminho} não corta carta por tamanho com literal próprio",
               f"achei {cortes}")
        checar("fora_do_tamanho" in corpo or "MIN_CARACTERES" in corpo,
               f"{caminho} usa a régua compartilhada de curadoria_cartas")
        checar(funcao in corpo, f"{caminho} ainda tem {funcao}()")

    # 🔴 MUTAÇÃO DO PRÓPRIO GUARDA — §9.3: "um guarda que não tem como falhar
    # não guarda nada". Se o detector não CONSEGUE ver o corte antigo, os cinco
    # OKs acima não valem nada. Aqui está o corte exato que existia.
    reintroduzido = "if len(texto) < 15 or len(texto) > 400:\n    continue"
    checar(len(_cortes_de_carta_a_mao(reintroduzido)) == 2,
           "MUTAÇÃO: o detector ACUSA o corte 15/400 se alguém o reintroduzir",
           f"achou {_cortes_de_carta_a_mao(reintroduzido)}")
    checar(not _cortes_de_carta_a_mao("if len(lote) < 1000: pass"),
           "CONTROLE: e NÃO acusa a paginação do banco (len(lote) < 1000)")


def teste_o_descarte_por_tamanho_conta():
    print("\n[3] O descarte diz o que perdeu — filtro mudo não se audita")
    motivo = C.fora_do_tamanho("x" * 2000)
    checar(isinstance(motivo, str) and "2000" in motivo and "1800" in motivo,
           "o motivo traz o tamanho medido E o limite violado", repr(motivo))
    checar(C.fora_do_tamanho.__doc__ and "auditad" in C.fora_do_tamanho.__doc__,
           "a função registra por que devolve texto e não booleano")
    for caminho, _ in INGESTORES[:4]:
        corpo = open(os.path.join(RAIZ, caminho), encoding="utf-8").read()
        checar("DESCARTAD" in corpo.upper(),
               f"{caminho} registra o descarte em log")


def teste_o_portao_de_pii_continua_fechando():
    print("\n[4] MUTAÇÃO: o portão fecha em PII de verdade")
    for nome, texto in MUTACOES.items():
        mascarado, achados = C.veredito_de_pii(texto)
        checar(bool(achados),
               f"carta com {nome} CONTINUA sendo rejeitada",
               f"achados={achados} · {mascarado[:70]}")
        # E o dado sai do texto mesmo na rejeição: o que a tabela guarda é o
        # mascarado, nos dois caminhos. Um CPF em `rejected_pii` continua sendo
        # um CPF guardado.
        checar(mascarado != texto,
               f"o dado de {nome} SAI do texto que seria guardado")


def teste_o_conhecimento_barrado_por_vocabulario_volta():
    print("\n[5] O que era barrado por vocabulário de contexto agora passa")
    for texto in CONHECIMENTO_QUE_ERA_BARRADO:
        _, achados = C.veredito_de_pii(texto)
        checar(not achados,
               f"passa: {texto[:58]}…", f"achados={achados}")

    # A CAUSA, nomeada: a regra antiga era `templatize(t) == t`. Se ela ainda
    # valesse, estas cartas continuariam barradas. É o controle que separa
    # "consertei" de "mudei alguma coisa e melhorou".
    from app.services.atlas.templater import templatize
    pela_regra_antiga = [t for t in CONHECIMENTO_QUE_ERA_BARRADO
                         if templatize(t) != t]
    checar(len(pela_regra_antiga) >= 4,
           "CONTROLE: a regra ANTIGA (templatize(t)==t) barrava ao menos 4 "
           "destas — o mérito é do eixo novo, não de outra coisa",
           f"a regra antiga barrava {len(pela_regra_antiga)}")


def teste_as_duas_familias_de_regra_sao_disjuntas():
    print("\n[6] Identificador e heurística não se misturam")
    comuns = C.PII_QUE_REJEITA & C.PII_QUE_SO_MASCARA
    checar(not comuns, "nenhum placeholder está nas duas listas", str(comuns))
    for obrigatorio in ("{CPF}", "{CNPJ}", "{TELEFONE}", "{PLACA}", "{EMAIL}",
                        "{CORRETORA}"):
        checar(obrigatorio in C.PII_QUE_REJEITA,
               f"{obrigatorio} rejeita — é identificador de forma determinística")
    # ⚠️ `{NOME}` NÃO rejeita, e isto é uma decisão medida, não um esquecimento.
    # 📊 As 4 ocorrências de `{NOME}` entre as 320 são `DDD`, `WhatsApp`,
    # `ANTES` e uma quarta palavra comum — precisão 0/4 neste acervo. E o nome,
    # se houver nome, já saiu no mascaramento: o que a tabela guarda é limpo.
    checar("{NOME}" in C.PII_QUE_SO_MASCARA,
           "{NOME} mascara e segue — 📊 0/4 de precisão nas 320 medidas")


def main() -> int:
    print("=" * 74)
    print("A RÉGUA DA CARTA É UMA SÓ — E O PORTÃO DE PII FECHA NO EIXO CERTO")
    print("=" * 74)
    for teste in (teste_o_teto_de_400_nao_volta,
                  teste_nenhum_ingestor_carrega_a_regua_propria,
                  teste_o_descarte_por_tamanho_conta,
                  teste_o_portao_de_pii_continua_fechando,
                  teste_o_conhecimento_barrado_por_vocabulario_volta,
                  teste_as_duas_familias_de_regra_sao_disjuntas):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {teste.__name__} explodiu: {type(exc).__name__}: {exc}")
    print("\n" + "=" * 74)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("A LISTA DE 900 PASSA; O CPF, O TELEFONE, A PLACA E A CORRETORA, NÃO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
