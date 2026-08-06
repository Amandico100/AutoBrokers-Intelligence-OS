# -*- coding: utf-8 -*-
"""O acervo das seguradoras pode virar conhecimento sem levar gente junto.

Por que este arquivo existe
---------------------------
São 551 conversas reais com a URA de dez seguradoras, 19.421 eventos, e nenhuma
delas tinha virado conhecimento até 06/08/2026. Para lê-las é preciso exportá-las
mascaradas — e este material tem PII que o acervo de atendimento não tinha, em
formas que o `templatize` de então não conhecia.

📊 Medido em 06/08/2026 sobre as 319 sessões substanciais, antes dos consertos:

    ~240 ocorrências   primeiro nome de segurado, escrito pela própria URA
     266 ocorrências   logradouro com número, em prosa, sem rótulo nenhum
    ~750 ocorrências   palavra de MENU na mesma posição do nome

A última linha é o problema inteiro. "Magda, só mais uma informação:" e
"Guincho, borracheiro e chaveiro" têm exatamente a mesma forma, e um mascarador
que não separe as duas ou vaza nome ou apaga o vocabulário da URA — que é o
conhecimento que este acervo existe para extrair.

O caminho até a regra que separa
--------------------------------
Quatro hipóteses foram medidas, e três foram REFUTADAS pela própria medição:

| hipótese | o que dizia | o que a medição respondeu |
|---|---|---|
| forma | capitalizada + vírgula é nome | 76% dos casamentos eram menu |
| raridade | nome aparece em poucas sessões | "Saionara" em 97, "Microondas" em 9 |
| vocativo puro | nome só aparece como vocativo | Roubo, Chaveiro e Vidros caíram junto |
| **vocabulário** | **o que a seguradora OFERECE como opção nunca é gente** | **separa: menor opção 4 sessões, maior nome 3** |

Cada guarda aqui vem com um CONTROLE
------------------------------------
Um mascarador testado só contra vazamento fica mais guloso a cada correção, e o
custo aparece onde ninguém olha: no conhecimento que silenciosamente não existe.
Por isso todo caso proibido tem ao lado um caso permitido, com a mesma forma,
que PRECISA sobreviver. É o que dá direito de dizer que a regra separa as duas
coisas em vez de recusar tudo.

Os textos são reais, copiados de `observed_events` de produção — com os nomes de
pessoa trocados por outros nomes de pessoa.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FALHAS: list[str] = []

for _n, _p in (("app", ("app",)), ("app.services", ("app", "services")),
               ("app.services.atlas", ("app", "services", "atlas"))):
    if _n not in sys.modules:
        _m = types.ModuleType(_n)
        _m.__path__ = [os.path.join(RAIZ, *_p)]
        _m.__package__ = _n
        sys.modules[_n] = _m


def _carregar(nome: str, caminho: str):
    spec = importlib.util.spec_from_file_location(nome, caminho)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nome] = mod
    spec.loader.exec_module(mod)
    return mod


DESTILACAO = os.path.join(RAIZ, "scripts", "destilacao_max")
sys.path.insert(0, DESTILACAO)
M = _carregar("mascarar_seg", os.path.join(DESTILACAO, "mascarar.py"))
templatize = M.templatize


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def _ev(direcao: str, hora: str, texto: str, tipo: str = "text",
        interativo=None, sessao: str = "s1") -> dict:
    return {"session_id": sessao, "direction": direcao, "wa_timestamp": hora,
            "msg_type": tipo, "text": texto, "interactive": interativo}


# ── 1. o prefixo de papel não pode virar rótulo ───────────────────────────────

def teste_remascarar_conhece_os_papeis_do_acervo_de_seguradora():
    print("\n[1] `remascarar` não come a instrução da seguradora")
    # `_LABELED_VALUE` casa `segurado` no começo da linha. Sem o prefixo
    # `SEGURADORA` na lista de papéis de `remascarar`, o templatize vê
    # "SEGURADORA: Por favor, informe o CPF..." como "rótulo: valor" e a
    # instrução inteira colapsa em `SEGURADO{VALOR}` — que é exatamente o
    # conhecimento que o acervo existe para extrair.
    linha = "SEGURADORA: Por favor, informe o *CPF ou CNPJ* do(a) titular."
    checar(M.remascarar(linha) == linha,
           "a instrução da seguradora atravessa `remascarar` intacta",
           f"virou {M.remascarar(linha)!r}")
    checar(M.remascarar("NOS: oi") == "NOS: oi",
           "e a nossa fala também")

    # CONTROLE: prove que o colapso É REAL, com a MESMA linha. `templatize`
    # aplicado direto no transcript montado destrói a instrução; `remascarar`
    # não. A diferença entre os dois é só arrancar o prefixo de papel antes —
    # e é ela que este teste existe para guardar. Sem esta linha, o caso acima
    # passaria igual se o `_LABELED_VALUE` estivesse morto.
    checar(templatize(linha) != linha,
           "CONTROLE: `templatize` DIRETO na mesma linha destrói a instrução",
           f"sobreviveu como {templatize(linha)!r} — então a regra 1 não prova nada")
    checar("{VALOR}" in templatize(linha),
           "e o que sobra dela é um {VALOR}", templatize(linha))


# ── 2. nome depois de saudação: os dois lados ─────────────────────────────────

def teste_saudacao_mascara_nome_e_devolve_o_verbo():
    print("\n[2] Depois da saudação: nome sai, instrução fica")
    for frase, esperado in (
            ("Olá, Magda! Como posso ajudar?", "Olá, {NOME}! Como posso ajudar?"),
            ("Ola, Magda! Como posso ajudar?", "Ola, {NOME}! Como posso ajudar?")):
        checar(templatize(frase) == esperado, f"{frase[:22]!r} → nome mascarado",
               f"virou {templatize(frase)!r}")

    # CONTROLE que conserta perda de conhecimento REAL. O `(?i)` valia para o
    # padrão inteiro, então `[A-ZÀ-Ú][a-zà-ú]{2,}` casava minúscula também:
    # 📊 em 06/08/2026, `templatize("Ola, quero abrir um sinistro")` devolvia
    # "Ola, {NOME} um sinistro" — duas palavras de conhecimento apagadas por
    # uma regra de PII, na frase em que o segurado diz o que quer.
    for frase in ("Ola, quero abrir um sinistro",
                  "Oi, preciso de guincho agora",
                  "Olá, digite o CPF",
                  "Bem-vindo à Central de Atendimento"):
        checar(templatize(frase) == frase,
               f"CONTROLE: {frase[:28]!r} sobrevive inteira",
               f"virou {templatize(frase)!r}")


def teste_tratamento_mascara_nome_e_poupa_papel():
    print("\n[3] 'Sr. Fulano' vira {NOME}; 'Sr. Corretor' não")
    checar(templatize("Sr Gustavo, o guincho chegou") == "Sr {NOME}, o guincho chegou",
           "nome depois de tratamento é mascarado",
           templatize("Sr Gustavo, o guincho chegou"))
    # CONTROLE: tratamento também precede PAPEL, e papel é conhecimento.
    for frase in ("Sr. Corretor, segue o boleto",
                  "A senhora poderia informar o CEP",
                  "A segurada informou o sinistro"):
        checar(templatize(frase) == frase, f"CONTROLE: {frase[:26]!r} sobrevive",
               templatize(frase))


# ── 3. logradouro: o dígito é a regra inteira ─────────────────────────────────

def teste_logradouro_com_numero_sai_e_prosa_fica():
    print("\n[4] Endereço em prosa sai; a palavra 'rua' continua sendo palavra")
    # 📊 266 ocorrências nas 319 sessões substanciais, 195 logradouros
    # distintos, todos com número — residência ou local de sinistro de gente.
    for frase in ("R. Manoel Loureiro, 1653 - Barreiros",
                  "Av. Santos Dumont, 4828 - Joinville",
                  "Rua das Flores, 123",
                  "Rua Joinville 13777"):
        saida = templatize(frase)
        checar("{ENDERECO}" in saida, f"{frase[:26]!r} → mascarado", saida)
        checar(saida.split()[0] == frase.split()[0],
               "e o TIPO do logradouro fica (é ele que ensina o que a URA pede)",
               saida)

    # CONTROLE: sem número não é endereço, é prosa — e prosa é conhecimento.
    # Sem esta metade, a regra viraria um comedor de vocabulário: 📊 das 345
    # ocorrências que a busca por vocabulário achava, 79 não tinham número e
    # nenhuma delas era endereço.
    for frase in ("a rua é conhecida na região",
                  "O condomínio está vazando",
                  "apartamento individual",
                  "A Porto pede rua e numero do local",
                  "A cobertura vale para rodovia pedagiada"):
        checar(templatize(frase) == frase, f"CONTROLE: {frase[:30]!r} sobrevive",
               templatize(frase))


# ── 3b. os sete buracos medidos em 06/08/2026 ─────────────────────────────────
#
# Cada um foi achado em material real, com lote e linha, e cada um tem aqui o
# par obrigatório: o que PRECISA ser mascarado e o que PRECISA sobreviver.
# Um teste que só mostrasse a máscara aprovaria uma regra que apaga a conversa
# inteira — foi o que quase aconteceu duas vezes na escrita destas regras.


def teste_a_regra_de_nome_nao_atravessa_a_quebra_de_linha():
    print("\n[4b] O rótulo de uma linha não captura a palavra da linha seguinte")
    # 📊 5 ocorrências reais (lote_018 conversas 6/7/8/9, lote_011 l.7) contra
    # 3.082 `Botão N` intactos. `\s` casa `\n`, e o separador entre rótulo e
    # nome atravessava a linha: o item de menu virava `{NOME}` e a instrução de
    # navegação sumia sem deixar rastro.
    menu = ("Posso te ajudar em algo mais?\nBotão 1: Novo atendimento\n"
            "Botão 2: Falar com atendente\nBotão 3: Encerrar")
    checar(templatize(menu) == menu,
           "o menu inteiro atravessa intacto — inclusive o 'Botão 3' depois de "
           "'atendente'", templatize(menu))
    for frase in ("Olá!\nBotão 1: Guincho\nBotão 2: Bateria",
                  "Bem-vindo\nVoltar ao menu",
                  "Prezado\nConfirmar agendamento",
                  "Sr.\nAgendar vistoria"):
        checar(templatize(frase) == frase,
               f"CONTROLE: {frase.splitlines()[0]!r} + item de menu na linha de "
               f"baixo sobrevive", templatize(frase))

    # CONTROLE INVERSO — a regra continua viva na MESMA linha. Sem esta metade,
    # trocar `\s` por espaço horizontal poderia ter desligado a regra inteira e
    # os quatro casos acima passariam por motivo errado.
    checar(templatize("atendente Fernanda") == "atendente {NOME}",
           "e o nome na MESMA linha do rótulo continua sendo mascarado",
           templatize("atendente Fernanda"))
    checar(templatize("Olá, Magda!") == "Olá, {NOME}!",
           "e a saudação com o nome ao lado também", templatize("Olá, Magda!"))


def teste_o_bloco_de_confirmacao_cadastral_nao_sai_em_claro():
    print("\n[4c] 'Nome do titular da apólice: FULANO' — 📊 71 ocorrências")
    # O rótulo `nome` SEMPRE esteve na lista. O que escapava era o qualificador
    # entre ele e os dois-pontos: o grupo terminava em "Nome ", o valor virava
    # "do titular da apólice: MARIELLA…", e a heurística do "sem dois-pontos"
    # via um "do" minúsculo e devolvia a linha inteira.
    for frase in ("Nome do titular da apólice: MARIELLA VALERIO MEIRA",
                  "Nome do titular da apólice: CONDOMINIO EDIFICIO EUGENIO MULLER",
                  "Titular: EDUARDO NOMURA",
                  "Nome do responsável: Carlos Augusto Nogueira",
                  "Nome completo do condutor: ANDREZZA HAUTSCH OIKAWA"):
        saida = templatize(frase)
        checar("{VALOR}" in saida or "{NOME}" in saida,
               f"{frase[:34]!r} → valor mascarado", saida)
        checar(saida.split(":")[0] == frase.split(":")[0],
               "e o RÓTULO fica — é ele que ensina o que a URA pede", saida)

    # A razão social do CONDOMÍNIO segurado sai junto, e é de propósito: quem
    # está no campo "titular da apólice" é o cliente, seja pessoa ou empresa.
    checar("EUGENIO" not in templatize(
        "Nome do titular da apólice: CONDOMINIO EDIFICIO EUGENIO MULLER"),
        "razão social de condomínio segurado também é mascarada")

    # CONTROLE — a INSTRUÇÃO com as mesmas palavras precisa sobreviver inteira.
    # É a frase que a URA repete em toda apólice, e é o conhecimento que este
    # acervo existe para extrair. 📊 261 ocorrências dela nos 27 lotes.
    for frase in ("Digite o *CPF* ou *CNPJ* do(a) titular da apólice.",
                  "Por favor digite o CPF ou CNPJ do(a) titular da apólice ou "
                  "pressione *9* para voltar",
                  "Confirme se os dados a seguir estão corretos, por gentileza:"):
        checar(templatize(frase) == frase, f"CONTROLE: {frase[:38]!r} sobrevive",
               templatize(frase))

    # CONTROLE 1b — RÓTULO ESPECÍFICO VENCE RÓTULO GENÉRICO (§12.1).
    # 📊 77 ocorrências de `Telefone do responsável: ({TELEFONE}`. Quando o
    # qualificador entrou na lista, esta linha passou a cair no rótulo genérico
    # e virava `{VALOR}` — proteção igual, informação a menos: quem lê a carta
    # deixava de saber que ali havia um telefone. Se o valor que sobrou é só
    # pontuação e placeholder, não há o que mascarar.
    for frase in ("Telefone do responsável: ({TELEFONE}",
                  "*Telefone principal*: ({TELEFONE}",
                  "Endereço do local: {ENDERECO}"):
        checar(templatize(frase) == frase,
               f"CONTROLE: {frase[:34]!r} mantém o rótulo específico",
               templatize(frase))

    # CONTROLE 2 — a seguradora NÃO é mascarada. "Porto Seguro" e "Yelum" são
    # empresas do mercado: conhecimento. O que separa não é uma lista de nomes
    # de seguradora, é a POSIÇÃO — o que está depois de um rótulo de titular é
    # o cliente; o que está solto na frase, não.
    for frase in ("A Porto Seguro pede o CPF do titular",
                  "Olá, seja bem-vindo ao atendimento digital da Yelum Seguradora!",
                  "A Maxpar é a rede credenciada da Tokio Marine"):
        checar(templatize(frase) == frase,
               f"CONTROLE: {frase[:34]!r} sobrevive", templatize(frase))


def teste_a_pergunta_de_identidade_da_porto():
    print("\n[4d] 'Eu estou falando com Nair?' — 📊 33 ocorrências, 8 sessões")
    for frase in ("Eu estou falando com Nair?",
                  "Eu estou falando com Rivadavia?",
                  "Boa tarde, falo com Maria Silva ?"):
        checar("{NOME}" in templatize(frase), f"{frase[:30]!r} → nome mascarado",
               templatize(frase))

    # CONTROLE — e este a própria Porto escreve. Quando ela NÃO sabe o nome,
    # imprime o papel na mesma tela: `"Eu estou falando com Segurado(a)?"`.
    # É a mesma frase, e precisa sobreviver — ela é a versão genérica da tela,
    # a que vale para todo mundo, e por isso a que mais ensina.
    #
    # 📊 6 ocorrências. Uma primeira escrita desta regra as comeu (a exclusão
    # era `segurad\b`, e depois de "segurad" vem "o", não uma fronteira).
    for frase in ("Eu estou falando com Segurado(a)?",
                  "Falo com o corretor ou segurado?",
                  "Estou falando com o titular da apólice?"):
        checar(templatize(frase) == frase, f"CONTROLE: {frase[:34]!r} sobrevive",
               templatize(frase))


def teste_o_sobrenome_nao_sobrevive_ao_placeholder():
    print("\n[4e] '{NOME} SALES' — meio nome mascarado é pior que nenhum")
    # 📊 6 linhas do acervo saíram assim (lote_015 l.6, lote_025 l.2/8/10,
    # lote_026 l.1). O quantificador aceitava UMA repetição, e nome brasileiro
    # tem três a cinco palavras. A linha PARECIA tratada e o sobrenome — que é
    # o que individualiza a pessoa dentro da família — seguia em claro.
    for frase in ("Olá, meu nome é ANDREZA MOURA TERRA e irei realizar",
                  "Olá, meu nome é Rogerio DIAS DOS SANTOS e irei realizar",
                  "meu nome é Maria de Fatima Guimaraes Gomes",
                  "me chamo Tereza Silva Santos"):
        saida = templatize(frase)
        checar("{NOME}" in saida, f"{frase[:34]!r} → mascarado", saida)
        sobrou = [p for p in saida.replace("{NOME}", " ").split()
                  if p.strip(",.!?:").capitalize() not in ("Olá", "Ola", "Oi")
                  and p[:1].isupper() and len(p) > 2]
        checar(not sobrou, "e NENHUM pedaço do nome sobra na linha", str(sobrou))

    # CONTROLE — a repetição precisa PARAR. Sem freio, ela comeria a frase que
    # vem depois do nome, que é onde a URA diz o que vai fazer.
    saida = templatize("Olá, meu nome é ANDREZA e irei realizar seu atendimento.")
    checar(saida == "Olá, meu nome é {NOME} e irei realizar seu atendimento.",
           "CONTROLE: o que vem DEPOIS do nome sobrevive inteiro", saida)
    saida = templatize("me chamo Saionara, darei continuidade em seu atendimento")
    checar(saida.endswith(", darei continuidade em seu atendimento"),
           "CONTROLE: a vírgula fecha o nome e a frase segue", saida)


def teste_telefone_e_documento_com_a_forma_errada():
    print("\n[4f] O que o humano digita não tem a forma que a regra esperava")
    # 📊 lote_019 l.11 — DDD com zero E hífen: as duas metades do mesmo defeito.
    for frase in ("048-99147-8922", "48 99972-2935", "(48) 99972-2935",
                  "*Charles* *048-99147-8922*"):
        checar("{TELEFONE}" in templatize(frase),
               f"{frase[:26]!r} → {{TELEFONE}}", templatize(frase))
    # 📊 lote_026 l.11 — CNPJ com os pontos no lugar errado. A URA respondeu
    # "sua resposta não corresponde a nenhuma opção": o documento nem funcionou,
    # e mesmo assim atravessou o portão em claro.
    checar(templatize("056.087.72/0001-77") == "{CNPJ}",
           "CNPJ com agrupamento errado também é documento",
           templatize("056.087.72/0001-77"))
    checar(templatize("05.608.772/0001-77") == "{CNPJ}",
           "e o agrupamento certo continua sendo", templatize("05.608.772/0001-77"))

    # CONTROLE — o que tem forma parecida e é conhecimento.
    for frase in ("o prazo é de 30 dias",
                  "a franquia é de 10% da cobertura",
                  "a vistoria vale por 90 dias",
                  "válido até 12/2028"):
        checar(templatize(frase) == frase, f"CONTROLE: {frase[:30]!r} sobrevive",
               templatize(frase))


def teste_o_telefone_da_central_e_conhecimento():
    print("\n[4g] 0800 da seguradora FICA; celular de segurado SAI")
    # O erro OPOSTO ao vazamento, e o mais caro dos dois porque não deixa
    # rastro. 📊 A URA da Tokio imprime o telefone da central numa linha só
    # (lote_021 l.5/8/9/10/12, lote_022 l.1) e a linha saía como `{NUMERO}` ou
    # `{CPF}` — o corredor deixando de descobrir que ali existe um canal.
    for frase in ("0800 727 2007", "0800 701 2757", "4004 2757", "4003-2532",
                  "0800-888-2532", "0300 313 3000"):
        checar(templatize(frase) == frase,
               f"CONTROLE: {frase!r} sozinho na linha sobrevive", templatize(frase))
    checar(templatize("Para solicitar assistência:\n0800 727 2007")
           == "Para solicitar assistência:\n0800 727 2007",
           "e o bloco inteiro da Tokio também",
           templatize("Para solicitar assistência:\n0800 727 2007"))

    # CONTROLE INVERSO — é o que dá direito à conclusão. Um celular de segurado
    # com a MESMA quantidade de dígitos precisa continuar sendo mascarado; se
    # ele sobrevivesse, a proteção teria sido desligada em vez de afinada.
    for frase in ("48 99972-2935", "(11) 98765-4321", "11987654321"):
        checar(templatize(frase) != frase,
               f"CONTROLE: celular {frase!r} continua mascarado", templatize(frase))

    # O MECANISMO da reserva, e não só o resultado dela. O trecho protegido é
    # retirado do texto por um marcador `\x00n\x00` antes de as regras rodarem
    # e devolvido no fim. Se um marcador escapasse, ele iria para o RAG e para
    # o `node_hash` da tela — e um caractere nulo no meio de uma carta é um
    # defeito que ninguém vê até quebrar um índice.
    #
    # 📊 Varrido nas 40.234 linhas dos 27 lotes: zero marcadores vazados, zero
    # linhas não idempotentes.
    for frase in ("0800 727 2007", "ligue 0800 701 2757 ou 4004 2757",
                  "Fale conosco / SAC:\n0800 729 1400\nSinistro: {CPF}"):
        saida = templatize(frase)
        checar("\x00" not in saida, "o marcador da reserva não escapa para o texto",
               repr(saida))
        checar(templatize(saida) == saida,
               "e mascarar de novo dá o mesmo texto (idempotente)", repr(saida))
    # E o 0800 escrito SEM separador nenhum é indistinguível de um CPF que
    # comece por 080. A regra escolhe o lado seguro e mascara — o custo está
    # registrado no relatório.
    checar(templatize("08007272007") == "{CPF}",
           "0800 corrido, sem separador, é tratado como documento",
           templatize("08007272007"))


def teste_endereco_ecoado_complemento_e_coordenada():
    print("\n[4h] O endereço que a URA lê de volta, o apartamento e o plus-code")
    # 📊 22 ocorrências: a URA ecoa o endereço numa FRASE, e o valor às vezes
    # cai na linha seguinte entre asteriscos — fora do alcance de `^rótulo:`.
    for frase in ("O endereço é: \n\n*Estr. Geral Coqueiros, 1963 - Angelina - SC*.",
                  "O endereço é: \n\n*Br-101, 205 - Sao Jose - SC*.",
                  "Localização: R. João Antônio da Silveira, 1500, Florianópolis",
                  "*1 - Endereço da apólice:* RD 46-105, SÃO JOSÉ - SC"):
        checar("{ENDERECO}" in templatize(frase) or "{VALOR}" in templatize(frase),
               f"{frase[:36]!r} → mascarado", templatize(frase))
    # 📊 217 ocorrências de complemento em claro. Metade do endereço protegida
    # e metade não é o pior estado: a linha PARECE tratada.
    for frase in ("apto 1104", "Bloco 2 apartamento 24", "Bl 15 ap 203",
                  "ap 1301", "APTO 302"):
        saida = templatize(frase)
        checar("{NUM}" in saida, f"{frase!r} → complemento mascarado", saida)
        checar(saida.split()[0].lower() == frase.split()[0].lower(),
               "e a PALAVRA fica — 'a Porto pede bloco e apartamento' ensina",
               saida)
    # 📊 3 plus-codes, todos de zona rural — onde é a única forma de endereço
    # que existe, e por isso a mais reveladora.
    for frase in ("88V9+6XW", "W9JJ+R3G Capão Alto - SC"):
        checar("{ENDERECO}" in templatize(frase), f"{frase[:20]!r} → coordenada",
               templatize(frase))

    # A RODOVIA POR SIGLA, sem rótulo de endereço em volta — é o único caminho
    # que a alcança. 📊 lote_019 l.11 e lote_004 l.7. A primeira escrita deste
    # teste usava "O endereço é: *Br-101, 205*", que quem mascara é a regra do
    # endereço anunciado: o guarda passava com a regra da rodovia desligada, e
    # um guarda que não tem como falhar não guarda nada (§9.3).
    for frase in ("*Destino:* BR-101, 205 - SAO JOSE - SC",
                  "o veículo está na SC-281, 1500"):
        saida = templatize(frase)
        checar("{ENDERECO}" in saida, f"{frase[:32]!r} → número do imóvel sai",
               saida)
        checar(frase.split(",")[0].split()[-1] in saida,
               "e a SIGLA da rodovia fica — ela diz onde a assistência atende",
               saida)
    # CONTROLE: sem o número, a rodovia é cobertura, não morada.
    for frase in ("a cobertura vale na BR-101", "atendemos toda a SC-281"):
        checar(templatize(frase) == frase, f"CONTROLE: {frase[:30]!r} sobrevive",
               templatize(frase))

    # CONTROLE — a linha que se declara EXEMPLO é instrução, não morada.
    # 📊 Uma primeira escrita desta regra comeu 109 ocorrências de instrução da
    # Porto antes de a medição pegá-la.
    for frase in ("( Ex: Bloco 2, apartamento 24, Casa 11, em frente ao shopping )",
                  "_(Ex: em frente ao shopping, Casa 11)_",
                  "Exemplo: Rua das Flores"):
        checar(templatize(frase) == frase, f"CONTROLE: {frase[:40]!r} sobrevive",
               templatize(frase))
    # CONTROLE 2 — sem dígito não é endereço, e a instrução do formulário fica.
    for frase in ("Endereço de Origem e destino (rua/av., número, bairro, cidade "
                  "e estado;",
                  "Vamos começar a preencher o endereço aproximado do ocorrido",
                  "o apartamento estava vazio",
                  "a cobertura vale na BR-101",
                  "logradouro é o nome da rua, avenida, praça ou quadra"):
        checar(templatize(frase) == frase, f"CONTROLE: {frase[:38]!r} sobrevive",
               templatize(frase))


def teste_nome_colado_a_documento_e_papel_de_pessoa():
    print("\n[4i] Quem encosta num CPF é o titular dele; quem encosta na placa "
          "é o carro")
    # 📊 21 casamentos no acervo. A medição que decidiu a regra: junto de
    # {CPF}/{CNPJ} aparece gente; junto de {PLACA} aparecem marca e modelo.
    for frase in ("{CPF} - ALTAMIRO OSMAR KOERICH",
                  "JESSICA LUANA GRIGGIO - {CPF}",
                  "{CPF}  SEG SONIA DE LOURDES PRASS",
                  "Motorista Allan Souza Silveira",
                  "Condutor : ANDREZZA HAUTSCH OIKAWA ROCHA"):
        saida = templatize(frase)
        checar("{NOME}" in saida, f"{frase[:34]!r} → nome mascarado", saida)
        sobrou = [p for p in saida.replace("{NOME}", " ").split()
                  if len(p) > 2 and p[0].isupper() and not p.startswith("{")
                  and p not in ("SEG", "Motorista", "Condutor")]
        checar(not sobrou, "e o nome sai INTEIRO, sem sobrenome órfão", str(sobrou))

    # CONTROLE — quatro linhas do acervo com a MESMA forma que são conhecimento.
    # Incluir a placa custava estes quatro e não ganhava um nome sequer que o
    # CPF já não pegasse.
    for frase in ("Exemplo de CPF: {CPF}", "Exemplo de CNPJ: {CNPJ}",
                  "Voltar RAM, {PLACA}", "DOLPHIN Placa {PLACA}",
                  "{PLACA} - MITSUBISHI OUTLANDER"):
        checar(templatize(frase) == frase, f"CONTROLE: {frase[:30]!r} sobrevive",
               templatize(frase))
    # CONTROLE 2 — a nota de andamento em caixa alta. Um papel seguido de UMA
    # palavra é operação, não gente; e a vírgula depois do papel diz que ali
    # começou uma frase, não uma etiqueta.
    for frase in ("SEGURADA, FICOU DE RETORNAR",
                  "CONDUTOR IRÁ JUNTO",
                  "Titular da apólice deve estar presente"):
        checar("{NOME}" not in templatize(frase),
               f"CONTROLE: {frase[:32]!r} não vira nome", templatize(frase))


# ── 4. o transcript diz quem é quem ───────────────────────────────────────────

PORTO_MENU = ("O que você precisa?\nGuincho (reboque)\nBateria\nTroca de pneu\n"
              "Conserto de vidro\nChaveiro para o veículo")


def teste_o_transcript_nao_chama_a_seguradora_de_cliente():
    print("\n[5] `direction` significa outra coisa neste acervo")
    # No acervo de atendimento, `out` é a atendente e `in` é o segurado. Aqui
    # `out` somos NÓS acionando e `in` é a SEGURADORA respondendo. Reusar o
    # rotulador de lá faria o destilador ler o robô da Porto como se fosse um
    # segurado — o erro que a regra 8 do prompt antigo levou cinco destiladores
    # para descobrir. Aqui o rótulo sai certo da fonte.
    eventos = [_ev("out", "1", "oi"), _ev("in", "2", "Aguarde um momento")]
    saida = M.transcript_seguradora(eventos).split("\n")
    checar(saida[0] == "NOS: oi", "o que nós enviamos é NOS", saida[0])
    checar(saida[1] == "SEGURADORA: Aguarde um momento",
           "o que a seguradora respondeu é SEGURADORA", saida[1])

    # CONTROLE: o rotulador do acervo ANTIGO continua vivo e continua dizendo
    # o contrário — as duas leituras existem de propósito, para acervos
    # diferentes. Se este controle quebrar, alguém unificou o que não devia.
    antigo = M.transcript(eventos).split("\n")
    checar(antigo[0].startswith("ATENDENTE:") and antigo[1].startswith("CLIENTE:"),
           "CONTROLE: `transcript` (atendimento) mantém ATENDENTE/CLIENTE",
           str(antigo))


def teste_o_clique_sem_texto_recupera_o_rotulo():
    print("\n[6] O clique mudo tem rótulo em `interactive` — e às vezes não tem")
    # 📊 937 dos 1.861 `button_reply` do acervo têm texto vazio; 914 têm o
    # rótulo em `interactive.title`. Sem lê-lo, metade dos cliques vira
    # `[button_reply]` e o transcript perde o caminho percorrido dentro da URA.
    eventos = [
        # Uma linha só de propósito: a tela real da Porto tem quebras de linha,
        # e o transcript é quebrado por mensagem, não por evento — comparar por
        # índice de linha num menu multilinha testaria o `split`, não a regra.
        _ev("in", "1", "O que você precisa?", "list"),
        _ev("out", "2", "", "button_reply", {"kind": "button_reply", "title": "Guincho (reboque)"}),
        _ev("out", "3", "", "button_reply", {"kind": "button_reply", "id": "btn_3a9f"}),
    ]
    saida = M.transcript_seguradora(eventos).split("\n")
    checar(saida[1] == "NOS: Guincho (reboque)",
           "o rótulo do clique vem de `interactive.title`", saida[1])
    # CONTROLE: sem rótulo em lugar nenhum, o transcript DIZ que não sabe.
    # Escrever `btn_3a9f` faria o destilador ler um id opaco como se a
    # seguradora tivesse escrito isso — rótulo não se inventa.
    checar(saida[2] == "NOS: [clique sem rótulo]",
           "CONTROLE: sem rótulo, o transcript se declara ignorante", saida[2])
    checar("btn_3a9f" not in "\n".join(saida),
           "e o id opaco NÃO aparece no lugar do rótulo")


# ── 5. o vocativo: a regra que custou quatro hipóteses ────────────────────────

MENU = frozenset({"guincho", "reboque", "roubo", "chaveiro", "vidros",
                  "borracheiro", "conserto", "bateria"})


def _uma_linha(texto: str, vocab=MENU, direcao: str = "in") -> str:
    return M.transcript_seguradora([_ev(direcao, "1", texto)], vocab).split(": ", 1)[1]


def teste_o_vocativo_sai_e_o_menu_fica():
    print("\n[7] 'Magda,' vira {NOME}; 'Guincho,' continua sendo guincho")
    checar(_uma_linha("Magda, só mais uma informação:") == "{NOME}, só mais uma informação:",
           "o vocativo da URA é mascarado", _uma_linha("Magda, só mais uma informação:"))
    checar(_uma_linha("Certo, Magda! Antes de continuar") == "Certo, {NOME}! Antes de continuar",
           "e o vocativo ATRÁS de uma interjeição também",
           _uma_linha("Certo, Magda! Antes de continuar"))

    # CONTROLE — é a linha que dá direito à conclusão. A palavra de menu tem a
    # MESMA forma do nome e precisa sobreviver; se ela cair, a regra não separa
    # nada, só recusa tudo, e passaria no teste de cima sem separar coisa alguma.
    for frase in ("Guincho, borracheiro e chaveiro estão disponíveis",
                  "Roubo, furto e incêndio têm franquia própria",
                  "Vidros, retrovisores e faróis entram no mesmo pedido"):
        checar("{NOME}" not in _uma_linha(frase),
               f"CONTROLE: {frase[:30]!r} não perde a primeira palavra",
               _uma_linha(frase))

    # CONTROLE 2: e as interjeições, que não são menu nem nome, também ficam.
    for frase in ("Agora, me informe o CEP do local",
                  "Certo, vou verificar",
                  "Perfeito, seu protocolo está gerado"):
        checar("{NOME}" not in _uma_linha(frase),
               f"CONTROLE: interjeição {frase.split(',')[0]!r} sobrevive",
               _uma_linha(frase))


def teste_a_resposta_a_uma_pergunta_por_nome_e_um_nome():
    print("\n[8] Quem sabe o que a resposta é não é ela, é a pergunta")
    # "Nesse caso, qual é o nome de quem estará na residência?" / "Magda".
    # Nenhuma regra de forma alcança isso: a resposta é uma palavra capitalizada
    # solta, igual a "Guincho". A pergunta está na linha de cima.
    eventos = [
        _ev("in", "1", "Nesse caso, qual é o nome de quem estará na residência?"),
        _ev("out", "2", "Fernanda"),
        _ev("in", "3", "Certo. Informe um número de celular com DDD, por favor."),
        _ev("out", "4", "Conserto de vidro"),
    ]
    saida = M.transcript_seguradora(eventos, MENU).split("\n")
    checar(saida[1] == "NOS: {NOME}", "a resposta à pergunta por nome é mascarada",
           saida[1])
    # CONTROLE: a resposta à pergunta SEGUINTE não é nome e não pode ser
    # mascarada. Sem isto, a regra poderia estar mascarando toda resposta nossa.
    checar(saida[3] == "NOS: Conserto de vidro",
           "CONTROLE: a resposta à pergunta seguinte NÃO é tocada", saida[3])


def teste_o_disparo_ativo_poe_o_nome_fora_da_primeira_linha():
    print("\n[8b] Quando a seguradora começa a conversa, o nome não está no topo")
    # 📊 lote_019 l.9 e lote_018 l.3. `_VOCATIVO` está ancorado no começo da
    # MENSAGEM, e o disparo ativo abre com a marca da seguradora:
    #
    #     "Olá! Aqui é a Porto Seguro 👋\n\nRafael, a vistoria do seu veículo…"
    #
    # A medição quase matou esta regra: olhar toda linha que comece por palavra
    # capitalizada e vírgula dá 125 casamentos nos 27 lotes, e **123 são menu**.
    # O que separa não é a vírgula — é a SEGUNDA PESSOA: um disparo fala com
    # alguém sobre a coisa DELE.
    disparo = ("Olá! Aqui é a Porto Seguro 👋\n\nRafael, a vistoria do seu "
               "veículo para o sinistro 531202690931 está em andamento.")
    saida = M.transcript_seguradora([_ev("in", "1", disparo)], MENU)
    checar("{NOME}, a vistoria do seu veículo" in saida,
           "o nome do disparo ativo é mascarado mesmo fora da primeira linha",
           saida[:120])
    checar("Porto Seguro" in saida,
           "e a marca da seguradora, na linha de cima, NÃO é tocada", saida[:60])
    checar("531202690931" not in saida,
           "o número do sinistro (12 dígitos) também sai — não casava em regra "
           "nenhuma: {NUMERO} parava em 11 e {CARTAO} só começa em 13",
           saida[:160])

    # CONTROLE — as duas linhas do acervo que têm a MESMA forma e possessivo,
    # e que precisam sobreviver: uma protegida pelo vocabulário de menu, outra
    # pela lista de interjeição. Se caírem, a regra não separa nada.
    for frase in ("Elogios, reclamações e informações de como cancelar seu seguro",
                  "Pronto, sua assistência está em andamento!",
                  "Guincho, técnico e chaveiro"):
        saida = _uma_linha(frase, MENU | frozenset({"elogios"}))
        checar("{NOME}" not in saida, f"CONTROLE: {frase[:34]!r} sobrevive", saida)


def teste_o_ok_no_meio_nao_gasta_a_pergunta_por_nome():
    print("\n[8c] 'ok' não é resposta — e o nome vem na mensagem seguinte")
    # 📊 lote_026 l.1. A marca `perguntaram_nome` era consumida pela PRIMEIRA
    # fala nossa, e a primeira foi "ok". O nome vinha na segunda e saía inteiro.
    eventos = [
        _ev("in", "1", "Me informa o CPF e nome completo dos passageiros"),
        _ev("out", "2", "ok"),
        _ev("out", "3", "Ricardo Fernando Ferreira"),
    ]
    saida = M.transcript_seguradora(eventos, MENU).split("\n")
    checar(saida[1] == "NOS: ok",
           "o aceite atravessa intacto — é a evidência de que houve um sim",
           saida[1])
    checar(saida[2] == "NOS: {NOME}",
           "e a marca continuava de pé quando o nome chegou", saida[2])

    # 📊 lote_027 l.4 — a mesma pergunta em NEGRITO. Um asterisco entre "o" e
    # "nome" e a pergunta deixava de ser reconhecida.
    eventos = [
        _ev("in", "1", "Qual é o *nome completo do condutor*?\n\n"
                       "*Exemplo*: Maria dos Santos"),
        _ev("out", "2", "RAFAELA LIDIA SANTOS IWAMOTO"),
        _ev("in", "3", "Em qual *cidade*?"),
        _ev("out", "4", "São Paulo"),
    ]
    saida = M.transcript_seguradora(eventos, MENU).split("\n")
    checar(saida[-3] == "NOS: {NOME}",
           "a pergunta em negrito volta a ser reconhecida", saida[-3])
    # CONTROLE: a marca é gasta pelo nome, e a resposta seguinte NÃO é tocada.
    # Sem isto, a regra poderia estar mascarando toda resposta nossa depois de
    # uma pergunta por nome — para sempre.
    checar(saida[-1] == "NOS: São Paulo",
           "CONTROLE: a resposta à pergunta SEGUINTE não é mascarada", saida[-1])


def teste_o_vocabulario_de_menu_precisa_se_repetir_entre_sessoes():
    print("\n[9] Opção de verdade se repete; eco do cadastro aparece uma vez")
    # 📊 Sem limiar, um nome entrava no vocabulário porque a URA o ECOA dentro
    # de uma linha de lista. Medido: menor palavra de menu = 4 sessões
    # (elogios), maior nome = 3 (joao). O limiar é 4.
    eventos = []
    for i in range(4):
        eventos.append(_ev("in", "1", "O que você precisa?\nBotão 1: Guincho\nBotão 2: Bateria",
                           "buttons", {"kind": "buttons"}, sessao=f"s{i}"))
    # o eco do cadastro: uma linha de lista com o nome do titular, em UMA sessão
    eventos.append(_ev("in", "2", "Escolha:\nBotão 1: Falar com Gustavo", "buttons",
                       {"kind": "buttons"}, sessao="s0"))
    vocab = M.vocabulario_de_menu(eventos)
    checar("guincho" in vocab and "bateria" in vocab,
           "a opção que aparece em 4 sessões entra no vocabulário",
           str(sorted(vocab)))
    checar("gustavo" not in vocab,
           "CONTROLE: o nome ecoado em 1 sessão NÃO entra",
           "se entrasse, o vocabulário protegeria justamente quem devia denunciar")

    # CONTROLE 2: prove que o limiar É o que separa — com limiar 1, o nome
    # entra. Sem isto, o caso acima passaria igual se o vocabulário estivesse
    # sempre vazio.
    frouxo = M.vocabulario_de_menu(eventos, min_sessoes=1)
    checar("gustavo" in frouxo,
           "CONTROLE: com limiar 1 o nome entraria — é o limiar que decide",
           str(sorted(frouxo)))


# ── 6. a marca de já-destilada e o corte ──────────────────────────────────────

def teste_o_exportador_nao_corta_em_silencio():
    print("\n[10] O exportador sabe dizer o que deixou de fora")
    fonte = open(os.path.join(DESTILACAO, "exportar_seguradoras.py"),
                 encoding="utf-8").read()
    checar('"já destilada"' in fonte,
           "sessão já destilada é contada como descarte, não some")
    checar("distill_falhas" in fonte,
           "e a que falhou três vezes também — a mesma marca do `exportar.py`")
    checar("fora do cap de --lotes" in fonte,
           "o cap por `--lotes` se declara no índice",
           "cap silencioso é defeito (CLAUDE.md §11)")
    checar("truncadas" in fonte and "INDICE" in fonte,
           "e o transcript cortado no teto vai para o índice com o id")
    # CONTROLE: o exportador NÃO pode escrever no banco. Uma reindexação de
    # 10.818 cartas estava rodando em produção quando ele foi escrito.
    #
    # `sys.path.insert` é descontado à mão: um guarda que confunde manipulação
    # de caminho com escrita em banco cria alarme falso, e alarme falso é o que
    # ensina a ignorar alarme.
    escritas = fonte.replace("sys.path.insert(", "").replace("path.insert(", "")
    for proibido in (".update(", ".insert(", ".upsert(", ".delete(", ".rpc("):
        checar(proibido not in escritas,
               f"CONTROLE: o exportador não chama {proibido!r} em lugar nenhum",
               "ele lê, mascara e larga arquivo — quem grava é outro script")
    checar("path.insert(" in fonte,
           "CONTROLE do controle: `path.insert` existe mesmo e foi descontado",
           "se ele sumir, o desconto acima passa a esconder uma escrita real")


def main() -> int:
    print("=" * 74)
    print("A CONVERSA COM A SEGURADORA VIRA CONHECIMENTO SEM LEVAR GENTE JUNTO")
    print("=" * 74)
    for teste in (teste_remascarar_conhece_os_papeis_do_acervo_de_seguradora,
                  teste_saudacao_mascara_nome_e_devolve_o_verbo,
                  teste_tratamento_mascara_nome_e_poupa_papel,
                  teste_logradouro_com_numero_sai_e_prosa_fica,
                  teste_a_regra_de_nome_nao_atravessa_a_quebra_de_linha,
                  teste_o_bloco_de_confirmacao_cadastral_nao_sai_em_claro,
                  teste_a_pergunta_de_identidade_da_porto,
                  teste_o_sobrenome_nao_sobrevive_ao_placeholder,
                  teste_telefone_e_documento_com_a_forma_errada,
                  teste_o_telefone_da_central_e_conhecimento,
                  teste_endereco_ecoado_complemento_e_coordenada,
                  teste_nome_colado_a_documento_e_papel_de_pessoa,
                  teste_o_transcript_nao_chama_a_seguradora_de_cliente,
                  teste_o_clique_sem_texto_recupera_o_rotulo,
                  teste_o_vocativo_sai_e_o_menu_fica,
                  teste_a_resposta_a_uma_pergunta_por_nome_e_um_nome,
                  teste_o_disparo_ativo_poe_o_nome_fora_da_primeira_linha,
                  teste_o_ok_no_meio_nao_gasta_a_pergunta_por_nome,
                  teste_o_vocabulario_de_menu_precisa_se_repetir_entre_sessoes,
                  teste_o_exportador_nao_corta_em_silencio):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {teste.__name__} EXPLODIU: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 74)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("O NOME SAI, O MENU FICA — E CADA GUARDA PROVOU AS DUAS DIREÇÕES")
    return 0


if __name__ == "__main__":
    sys.exit(main())
