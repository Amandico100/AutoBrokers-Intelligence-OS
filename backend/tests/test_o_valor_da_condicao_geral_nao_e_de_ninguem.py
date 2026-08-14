"""O mesmo número é dado de uma pessoa ou regra do produto — depende de onde está escrito.

A HISTÓRIA
==========
Em 08/08/2026, seis subagentes Opus 5 leram as Condições Gerais vigentes da
Porto e escreveram 783 cartas de conhecimento. Antes de publicar, rodei a mesma
verificação de dado pessoal que protege as cartas de atendimento.

📊 Ela recusou 36 delas. Todas pelo mesmo motivo: **trazem um valor em reais.**

    "Pequenos Reparos (10A e 10B): o limite é de R$ 2.500,00 por vigência"
    "Troca de Para-choque (11A e 11B): o limite é de R$ 25.000,00"
    "cláusula 83, só retrovisores externos: limite de R$ 2.000,00"

A regra que as barrava está escrita no `templater` e a justificativa dela é
correta — para conversa. "Sua franquia é de R$ 2.480,00" é o caso de UM
segurado, e mascarar é ganho puro: o que ensina em seguro é percentual e prazo,
não cifra. Foi medido nos lotes 007 e 008 e continua valendo.

**Numa condição geral o mesmo número é o oposto.** Está no contrato registrado
na SUSEP, vale para toda apólice que contratou a cláusula, é público — e é
exatamente a pergunta que o corretor faz. As cartas barradas eram justamente as
de `limite`, as mais consultadas do acervo.

Sem a ressalva havia só dois caminhos, e os dois perdem: recusar a carta na
porta, ou publicar "o limite é de {VALOR_RS}" — que é pior, porque parece
resposta e não responde nada.

QUEM DECIDE É O CHAMADOR, NUNCA O TEXTO
=======================================
Nenhuma heurística lê a frase e adivinha se aquele R$ é de uma pessoa. Errar
para o lado permissivo publica dado de cliente no RAG global. Então a ressalva
é um parâmetro explícito, e só o caminho do acervo — que sabe que está lendo um
PDF baixado do registro da SUSEP — o liga.

OS DOIS FUROS QUE APARECERAM DE LADO
====================================
Nenhum dos dois foi procurado. Os dois vieram da **linha de controle** (§9.2) —
a rodada que repete o cenário anterior para provar que o mérito é do fator que
mudou e de mais nada.

**1. `Bom dia, <nome>` não era mascarado.** Testando se a ressalva do valor
tinha aberto buraco, o caso do nome passou. O controle — o MESMO texto com a
ressalva desligada — mostrou que ele já passava antes, e que era a cifra que
vinha salvando aquele caso por acidente. A lista de gatilhos tinha `olá`, `oi`,
`bem-vindo` e `prezado`, e não tinha a saudação mais comum do português
brasileiro. 📊 Sem o controle, eu teria creditado o furo à mudança do dia e
consertado o lugar errado.

**2. `residencial da Porto em até 7 dias` virava `{ENDERECO}`.** O miolo do
padrão de logradouro aceitava `[^\\n,;]{2,45}` — qualquer coisa entre o tipo e
um número. E **três dos tipos da lista são nomes de ramo do nosso produto**:
`residencial`, `condomínio` e `edifício`. 📊 3 das 783 cartas foram destruídas
assim, e o que sobra continua parecendo uma carta — o formato pior, porque
ninguém percebe que a resposta foi comida.

CADA GUARDA AQUI PROVA AS DUAS DIREÇÕES
=======================================
Um mascarador tem duas formas de falhar, e elas puxam para lados opostos:
deixar passar dado de pessoa, e comer conhecimento. Um teste que só olha uma
delas autoriza o conserto a estragar a outra — foi assim que os dois furos
acima nasceram. Então todo bloco tem CONTROLE.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PROBLEMAS: list = []


def checar(condicao: bool, o_que: str, evidencia: str = "") -> None:
    if condicao:
        print(f"  OK  {o_que}" + (f"  ({evidencia})" if evidencia else ""))
    else:
        print(f"  X   {o_que}" + (f"  ({evidencia})" if evidencia else ""))
        _PROBLEMAS.append(o_que)


def _templater():
    """Carrega o templater sem subir `app.services` (que puxa o SDK da OpenAI)."""
    for nome in ("app", "app.services", "app.services.atlas"):
        if nome not in sys.modules:
            m = types.ModuleType(nome)
            m.__path__ = [os.path.join(RAIZ, *nome.split("."))]
            sys.modules[nome] = m
    caminho = os.path.join(RAIZ, "app", "services", "atlas", "templater.py")
    spec = importlib.util.spec_from_file_location("app.services.atlas.templater", caminho)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["app.services.atlas.templater"] = mod
    spec.loader.exec_module(mod)
    return mod


T = _templater()


def _limpo(texto: str, **kw) -> bool:
    return T.templatize(texto, **kw) == texto


# ---------------------------------------------------------------------------
def teste_a_cifra_da_condicao_geral_sobrevive():
    print("\n[1] O limite escrito no contrato chega inteiro ao RAG")

    cartas = [
        "No Porto Auto o limite de Pequenos Reparos é de R$ 2.500,00 por vigência.",
        "Na cláusula 83 do Porto Auto o limite máximo de indenização é de R$ 2.000,00.",
        # sem o "R$" — a segunda regra de valor, dos lotes 032/033
        "No Porto Auto o limite de Pequenos Reparos é de 2.500,00 por vigência.",
    ]
    for carta in cartas:
        checar(_limpo(carta, documento_publico=True),
               f"passa no acervo: {carta[:46]!r}", T.templatize(
                   carta, documento_publico=True)[:60])

    # 🔴 CONTROLE — a rodada que repete o cenário anterior. Sem ela, o bloco
    # acima passaria também se a regra de valor tivesse sido APAGADA do
    # templater, e ninguém veria: a conversa perderia a máscara em silêncio.
    for carta in cartas:
        checar(not _limpo(carta),
               f"CONTROLE — e continua mascarada na conversa: {carta[:34]!r}",
               "a mudança é da ressalva, não da regra")


def teste_a_reserva_do_valor_nao_e_um_esconderijo():
    print("\n[1b] O `,00` no fim não transforma CPF em dinheiro")

    # 🔴 O BURACO QUE A CONTAGEM DE REGRAS NÃO ENXERGAVA.
    #
    # No modo `documento_publico`, `_VALOR_SEM_RS` roda ANTES das outras 36
    # regras e RETIRA o valor do texto. O que sai do texto não é examinado por
    # mais ninguém. Com o padrão antigo (`\d{3,}`, sem teto), qualquer
    # sequência longa de dígitos com `,00` era retirada como se fosse dinheiro:
    #
    #     "pagar 98765432100,00 ao favorecido"  →  passava INTEIRO
    #
    # 📊 Achado em 11/08/2026 por auditoria de método. A métrica que estava em
    # uso — "36 de 38 regras ativas" — marcava seguro, porque nenhuma regra
    # tinha sido desligada. O texto é que era retirado antes delas.
    disfarcados = [
        ("pagar 98765432100,00 ao favorecido", "CPF de 11 dígitos"),
        ("cartão 4111111111111111,00 usado", "cartão de 16 dígitos"),
        ("ligue 11987654321,00 hoje", "telefone de 11 dígitos"),
    ]
    for frase, o_que in disfarcados:
        checar(not _limpo(frase, documento_publico=True),
               f"{o_que} com sufixo de centavos NÃO atravessa o acervo",
               T.templatize(frase, documento_publico=True)[:70])

    # 🔴 CONTROLE — e a cifra do contrato continua passando. Sem esta metade,
    # o bloco acima passaria também se a reserva tivesse sido simplesmente
    # APAGADA, e as 36 cartas de limite da Porto voltariam a ser recusadas na
    # porta — o defeito que a ressalva nasceu para consertar.
    dinheiro_de_verdade = [
        ("o limite é de R$ 2.500.000,00 por evento", "com R$ e separador"),
        ("franquia de 2.480,00 por evento", "sem R$, 4 dígitos"),
        ("indenização de 999999,00 no total", "6 dígitos, o teto da regra"),
        ("até 1.250.000,00 por vigência", "7 dígitos COM separador"),
    ]
    for frase, o_que in dinheiro_de_verdade:
        checar(_limpo(frase, documento_publico=True),
               f"CONTROLE — valor do contrato passa ({o_que})",
               T.templatize(frase, documento_publico=True)[:70])

    # 🔴 CONTROLE 2 — na CONVERSA nada disso mudou. O `,00` nunca protegeu
    # ninguém ali, e continua não protegendo.
    checar("{CPF}" in T.templatize("pagar 98765432100,00 ao favorecido"),
           "CONTROLE 2 — na conversa o CPF disfarçado já era mascarado",
           T.templatize("pagar 98765432100,00 ao favorecido"))

    # E a prova de que o teto é o mecanismo, não um acidente: o mesmo número
    # com um dígito a menos É dinheiro plausível e passa.
    checar(_limpo("valor de 987654,00 apurado", documento_publico=True),
           "CONTROLE 3 — 6 dígitos é dinheiro; 11 não é",
           T.templatize("valor de 987654,00 apurado", documento_publico=True))


def teste_o_numero_do_processo_susep_e_a_fonte_nao_o_cnpj():
    print("\n[1c] O processo SUSEP é a PROVA da carta, não dado de ninguém")

    # 🔴 O GUARDA BARRAVA A CARTA QUE FAZIA A COISA CERTA.
    #
    # 📊 Na publicação da HDI, 14/08/2026: **58 de 977 cartas recusadas**, e
    # todas pelo mesmo motivo — o número do processo SUSEP casava com o padrão
    # de CNPJ. Entre elas, as 54 do Sompo Imobiliário, que carregam o processo
    # justamente porque a HDI tem QUATRO residenciais parecidos e o processo é
    # o único desempate.
    #
    # A §10.3 regra 3 manda toda carta citar a fonte. Mascarar o processo apaga
    # exatamente a prova que o corretor abre para mostrar ao cliente.
    #
    # A separação é ESTRUTURAL, não heurística de contexto:
    #     SUSEP   15414.900228/2017-63    5 dígitos · UM ponto
    #     CNPJ    12.345.678/0001-90      2 dígitos · DOIS pontos
    for frase in (
        "Condições Gerais do processo SUSEP 15414.900228/2017-63",
        "No Sompo Imobiliário Residencial versão 1.6 (SUSEP 15414.900228/2017-63)",
    ):
        checar(_limpo(frase, documento_publico=True),
               f"o processo SUSEP atravessa o acervo: {frase[:44]!r}",
               T.templatize(frase, documento_publico=True)[:70])

    # 🔴 CONTROLE — e o CNPJ de verdade continua barrado. Sem esta metade, a
    # reserva poderia ter sido escrita larga demais e o teste passaria igual.
    checar(not _limpo("a empresa 12.345.678/0001-90 contratou",
                      documento_publico=True),
           "CONTROLE — CNPJ de verdade continua mascarado no acervo",
           T.templatize("a empresa 12.345.678/0001-90 contratou",
                        documento_publico=True))
    checar(not _limpo("o segurado 123.456.789-00 pediu", documento_publico=True),
           "CONTROLE — e o CPF também",
           T.templatize("o segurado 123.456.789-00 pediu", documento_publico=True))

    # 🔴 CONTROLE 2 — na CONVERSA nada mudou. Um número nesse formato não tem
    # por que existir num chat, e lá ele continua sendo mascarado.
    checar(not _limpo("SUSEP 15414.900228/2017-63"),
           "CONTROLE 2 — na conversa o processo continua mascarado",
           T.templatize("SUSEP 15414.900228/2017-63"))


def teste_motorista_amigo_e_o_nome_do_servico_nao_de_uma_pessoa():
    print("\n[1d] `Motorista Amigo` é serviço; `motorista Allan Souza` é gente")

    # 📊 A 59ª recusa da HDI. A regra leu "Motorista" como cargo e "Amigo da
    # HDI" como a pessoa que o ocupa. Mas numa condição geral o que vem depois
    # do papel costuma ser a MARCA do serviço — como `Carro Reserva` e
    # `Motorista Substituto`, que já estavam na lista negativa.
    for frase in ("O Motorista Amigo da HDI atende quando o segurado",
                  "o Motorista Particular leva o segurado até em casa",
                  "na rede de Oficina Credenciada do produto"):
        checar(_limpo(frase, documento_publico=True),
               f"nome de serviço passa: {frase[:42]!r}",
               T.templatize(frase, documento_publico=True)[:70])

    # 🔴 CONTROLE — e é aqui que a lista negativa se paga ou custa caro: cada
    # palavra acrescentada é uma pessoa a menos protegida se eu errar. Estas
    # três frases têm de continuar sendo mascaradas.
    for frase, quem in (
        ("o motorista Allan Souza Silveira dirigia", "motorista + nome"),
        ("o condutor Maria Silva Santos declarou", "condutor + nome"),
        ("o porteiro João Batista viu tudo", "porteiro + nome"),
    ):
        checar("{NOME}" in T.templatize(frase, documento_publico=True),
               f"CONTROLE — {quem} continua mascarado",
               T.templatize(frase, documento_publico=True))


def teste_a_ressalva_nao_abriu_a_porta_para_gente():
    print("\n[2] CONTROLE — com a ressalva LIGADA, dado de pessoa continua barrado")

    # Cada linha traz um R$ de propósito: é o cenário em que a ressalva está
    # ativa e ainda assim o texto tem de ser recusado por OUTRO motivo.
    perigos = [
        ("CPF", "O segurado portador do CPF 123.456.789-00 pediu o boleto de R$ 500,00."),
        ("telefone", "Ligar para (11) 98765-4321 e informar o valor de R$ 500,00."),
        ("e-mail", "Mandar para fulano.silva@gmail.com o comprovante de R$ 500,00."),
        ("placa", "Placa: QJQ0A91 com franquia de R$ 500,00."),
        ("nome", "Bom dia, Maria Aparecida da Silva! Seu limite é de R$ 500,00."),
        ("endereço", "Rua das Flores, 220 — sinistro de R$ 500,00."),
        ("CNPJ", "A empresa 12.345.678/0001-90 recebeu R$ 500,00."),
        ("cartão", "Cartão 4111 1111 1111 1111, cobrança de R$ 500,00."),
    ]
    for rotulo, frase in perigos:
        checar(not _limpo(frase, documento_publico=True),
               f"CONTROLE — {rotulo} recusado mesmo com a ressalva ligada",
               T.templatize(frase, documento_publico=True)[:56])


def teste_bom_dia_tambem_e_saudacao():
    print("\n[3] `Bom dia, <nome>` mascara o nome")

    for frase, esperado in [
        ("Bom dia, Maria Aparecida da Silva! Seu pedido foi registrado.", "{NOME}"),
        ("Boa tarde, João Carlos! Sua vistoria foi agendada.", "{NOME}"),
        ("Boa noite, Fernanda.", "{NOME}"),
    ]:
        checar(esperado in T.templatize(frase),
               f"{frase[:34]!r} → nome mascarado", T.templatize(frase)[:56])

    # CONTROLE — o conhecimento da URA não pode ser comido. Cada uma destas
    # frases é o primeiro turno de uma URA real, e todas começam com a mesma
    # saudação que acabou de virar gatilho.
    print("\n    CONTROLE — o menu da URA sobrevive à saudação nova")
    for frase in [
        "Bom dia! Digite seu CPF para continuar.",
        "Bom dia, escolha uma das opções abaixo.",
        "Boa tarde! Sou o assistente virtual da Porto Seguro.",
        "Bom dia, seja bem-vindo à Central de Atendimento.",
        "Boa noite! Informe o número da sua apólice.",
        "Bom dia, você optou por guincho.",
        "Bom dia! Aguarde enquanto localizamos seu cadastro.",
        "Boa tarde, senhor.",
    ]:
        checar(_limpo(frase), f"CONTROLE — {frase[:42]!r} intacta",
               T.templatize(frase)[:56])


def teste_o_ramo_nao_e_um_logradouro():
    print("\n[4] `residencial`, `condomínio` e `edifício` são ramos, não ruas")

    for frase in [
        "O segurado pode desistir do residencial da Porto em até 7 dias corridos.",
        "A garantia da mão de obra da assistência residencial da Porto é de 90 dias.",
        "As centrais da assistência residencial da Porto funcionam 24 horas por dia.",
        "O seguro condomínio da Porto em até 30 dias exige aviso.",
        "A cobertura de edifício da Porto é de 12 meses.",
        # 🔴 SEM ACENTO — achado pela prova de mutação, 08/08/2026.
        #
        # Uma das mutações do dia reintroduziu o defeito e o teste PASSOU. O
        # motivo: as frases acima escrevem "é de", e `é` não é conectivo. Sem
        # acento vira "e de" — dois conectivos seguidos de número, que era
        # exatamente o casamento que comia a carta.
        #
        # Transcrição de URA e texto colado de PDF chegam sem acento o tempo
        # todo. Um guarda que só cobre a grafia bonita não guarda o caso real.
        "A garantia da assistencia residencial da Porto e de 90 dias.",
        "A cobertura de edificio da Porto e de 12 meses.",
        "O condominio da Porto e de 24 meses.",
    ]:
        checar(_limpo(frase), f"{frase[:48]!r} intacta", T.templatize(frase)[:60])

    # 🔴 CONTROLE — o endereço de verdade continua saindo. Esta é a metade que
    # o conserto podia ter quebrado, e é a metade que protege uma pessoa. Os
    # nomes vêm dos 27 lotes medidos: `Geral Coqueiros`, `das Flores`, `Sertão
    # do Maruim` — com conectivo no meio, que é o caso difícil.
    print("\n    CONTROLE — o endereço de uma pessoa continua mascarado")
    for endereco in [
        "Rua das Flores, 123",
        "Estr. Geral Coqueiros, 1963",
        "Av. Paulista, 1000",
        "Residencial Vila Nova, 45",
        "Condomínio Green Park, 210",
        "Rua Marechal Deodoro da Fonseca, 1500",
        "Alameda dos Anjos, 77",
        "Rua Sertão do Maruim, 300",
        "Edifício Solar, 305",
        "Travessa São Jorge, 88",
    ]:
        checar("{ENDERECO}" in T.templatize(endereco),
               f"CONTROLE — {endereco!r} → {{ENDERECO}}", T.templatize(endereco))


def teste_o_que_vem_depois_do_cargo_pode_ser_o_cargo():
    print("\n[5] `porteiro substituto` é um serviço, não uma pessoa")

    # 📊 Achado no ensaio seco da publicação da Porto, 08/08/2026: a carta de
    # PORTEIRO SUBSTITUTO do condomínio — um serviço de assistência com regra
    # própria (5 dias, atestado, CID) — virava `porteiro {NOME}` e era
    # recusada na porta. 1 das 1.121.
    for frase in [
        "O serviço de PORTEIRO SUBSTITUTO do Porto Seguro Condomínio é por reembolso.",
        "O porteiro substituto é reembolsado por até 5 dias.",
        "A cobertura de motorista reserva vale por 30 dias.",
        "O condutor eventual está coberto.",
        "porteiro temporário contratado pelo condomínio",
    ]:
        checar(_limpo(frase), f"{frase[:46]!r} intacta", T.templatize(frase)[:58])

    # 🔴 CONTROLE — a regra existe para "porteiro João Silva", e ela tem de
    # continuar fazendo isso. Esta é a metade que protege uma pessoa, e é a que
    # o conserto podia ter quebrado.
    print("\n    CONTROLE — o cargo seguido de PESSOA continua mascarado")
    for frase in [
        "porteiro João Silva informou o ocorrido",
        "O condutor Maria Aparecida da Silva dirigia o veículo",
        "motorista Carlos Eduardo Souza",
        "proprietário Roberto Lima autorizou",
        "segurado Fernando Alves Pereira",
        "beneficiária Ana Paula Ribeiro",
        "responsável Marcos Antonio Ferreira",
    ]:
        checar("{NOME}" in T.templatize(frase),
               f"CONTROLE — {frase[:38]!r} → {{NOME}}", T.templatize(frase)[:58])


def teste_o_que_separa_carta_de_copia_e_o_bloco_literal():
    print("\n[6] Tamanho não separa carta de cópia — bloco literal separa")

    # ⚠️ ATUALIZADO em 09/08/2026 (CLAUDE.md §9.3). Este bloco guardava a
    # exceção de teto da faceta `documento`, criada ontem porque 2 cartas da
    # Porto passavam de 900 caracteres.
    #
    # 📊 O ensaio seco da Allianz mostrou que a exceção resolvia o caso e não o
    # problema: 25 cartas foram recusadas por tamanho, em SEIS facetas
    # diferentes, e a mais longa tinha 1.630 caracteres — a lista de doenças que
    # limita a 90 diárias. Todas eram listas TAXATIVAS do contrato, e cortar uma
    # lista taxativa faz a carta **mentir por omissão**: o corretor lê "não
    # cobre fusível, relé, lâmpada" e conclui que bateria é coberta.
    #
    # 📊 A medição que decidiu: comparei as 25 com o pedaço de origem procurando
    # o maior bloco LITERAL em comum. Nenhuma é cópia — o maior foi 105
    # caracteres (11%). Todas reescritas de verdade.
    #
    # **A afirmação que este bloco guarda não mudou:** o pedaço do contrato
    # colado não pode entrar como carta. O que mudou é como se mede isso — e
    # onde. Tamanho ficou sendo só um limite físico; a prova de cópia foi para
    # `conferir_ancoragem.py`, que **tem os pedaços na mão** para comparar. O
    # publicador roda no servidor e não tem.
    with open(os.path.join(RAIZ, "scripts", "acervo", "publicar_cartas.py"),
              encoding="utf-8") as arquivo:
        publicador = arquivo.read()
    with open(os.path.join(RAIZ, "scripts", "acervo", "conferir_ancoragem.py"),
              encoding="utf-8") as arquivo:
        conferidor = arquivo.read()

    checar("MAX_CARACTERES = 1800" in publicador,
           "o teto virou um limite FÍSICO, não um juízo sobre a carta",
           "📊 a maior lista taxativa legítima tem 1.630 caracteres")
    checar("MAX_CARACTERES_DOCUMENTO" not in publicador,
           "e a exceção por faceta saiu",
           "ela resolvia 2 casos da Porto e falhava em 25 da Allianz")

    checar("def _fracao_copiada(" in conferidor,
           "a prova de cópia mora onde os pedaços estão",
           "o publicador roda no servidor e não tem o texto do contrato")
    checar("BLOCO_LITERAL_DE_COPIA = 250" in conferidor
           and "copiado > LIMIAR_DE_COPIA and bloco >= BLOCO_LITERAL_DE_COPIA" in conferidor,
           "e ela exige as DUAS condições: fração alta E bloco longo",
           "📊 só a fração acusou 6 cartas curtas legítimas")

    # 🔴 CONTROLE — a fração sozinha pune a carta curta, que é justamente a que
    # fez o trabalho certo. Quando a regra do contrato já é uma linha, não
    # existe como reescrever sem repetir as palavras.
    curta = ("O Porto Seguro Empresa se aplica somente a danos ou prejuízos "
             "ocorridos e reclamados no Território Nacional.")
    checar(len(curta) < 250,
           "CONTROLE — a carta curta legítima fica abaixo do bloco de 250",
           f"{len(curta)} caracteres: nem que fosse cópia inteira ela acusaria")

    # CONTROLE — e o guarda continua sabendo acusar. Um parágrafo inteiro do
    # contrato transplantado passa dos 250 com folga.
    checar("CÓPIAS" in conferidor and "return 1 if (orfas_total or copias_total) else 0"
           in conferidor,
           "CONTROLE — e cópia REPROVA o lote, como a órfã",
           "as duas são defeito, não sinal para leitura")


def teste_carta_sem_acento_e_encoding_quebrado():
    print("\n[6b] Carta longa sem um único acento não entra no RAG")

    import re as _re

    with open(os.path.join(RAIZ, "scripts", "acervo", "publicar_cartas.py"),
              encoding="utf-8") as arquivo:
        publicador = arquivo.read()

    checar("_RE_ACENTO = re.compile" in publicador,
           "o publicador confere acentuação",
           "📊 4 destiladores gravaram por heredoc de shell e perderam os acentos")
    checar("len(texto) >= 200 and not _RE_ACENTO.search(texto)" in publicador,
           "e a régua é o TAMANHO da carta",
           "frase curta pode legitimamente não ter acento")

    # A prova nas duas direções, com a MESMA carta. Não é um par escolhido: é o
    # texto real que saiu do destilador do condomínio da Allianz, e a versão
    # dele com os acentos onde deviam estar.
    acento = _re.compile(r"[áàâãéêíóôõúüçÁÀÂÃÉÊÍÓÔÕÚÜÇ]")

    def recusa(t: str) -> bool:
        return len(t) >= 200 and not acento.search(t)

    quebrada = ("No Allianz Condominio a cobertura Basica Simples de Incendio e de "
                "contratacao obrigatoria, e junto com ela o condominio precisa "
                "contratar uma ou mais coberturas adicionais para o predio ou para "
                "o conteudo das areas comuns.")
    correta = ("No Allianz Condomínio a cobertura Básica Simples de Incêndio é de "
               "contratação obrigatória, e junto com ela o condomínio precisa "
               "contratar uma ou mais coberturas adicionais para o prédio ou para "
               "o conteúdo das áreas comuns.")
    checar(recusa(quebrada), "a carta com encoding quebrado é recusada",
           f"{len(quebrada)} caracteres, zero acentos")
    checar(not recusa(correta),
           "CONTROLE — a MESMA carta, com os acentos, passa",
           "as duas têm o mesmo tamanho: o que muda é só o acento")

    # 🔴 CONTROLE — o guarda não pode acusar frase curta. Uma carta de uma linha
    # sobre "desgaste pelo uso" legitimamente não tem acento nenhum.
    for curta in [
        "O seguro de equipamentos da Allianz nao cobre desgaste pelo uso.",
        "A cobertura de RC Familiar da Allianz tem limite proprio na apolice.",
    ]:
        checar(not recusa(curta), f"CONTROLE — {len(curta)} caracteres sem acento passa",
               "abaixo de 200 não é evidência de encoding quebrado")

    # 🔴 CONTROLE DE REGRESSÃO — o guarda entrou depois de 1.121 cartas da Porto
    # já publicadas. Se ele reprovasse alguma delas, estaria calibrado errado.
    porto = os.path.join(RAIZ, "scripts", "acervo", "cartas", "porto")
    if os.path.isdir(porto):
        import glob as _glob
        import json as _json

        total = reprovadas = 0
        for caminho in _glob.glob(os.path.join(porto, "*_CARTAS.jsonl")):
            with open(caminho, encoding="utf-8") as arquivo:
                for linha in arquivo:
                    if not linha.strip():
                        continue
                    total += 1
                    if recusa(" ".join(_json.loads(linha)["texto"].split())):
                        reprovadas += 1
        checar(total > 1000 and reprovadas == 0,
               f"CONTROLE — nenhuma das {total} cartas da Porto é reprovada",
               "o guarda entrou depois delas; reprovar seria calibragem errada")


def teste_a_carta_corrigida_entra_e_a_errada_sai():
    print("\n[7] A versão antiga da carta reescrita sai do índice")

    # 📊 Achado em 09/08/2026, conferindo o banco DEPOIS de publicar: a Allianz
    # tinha 1.967 cartas publicadas e 1.938 no arquivo. As 29 de diferença eram
    # as versões ANTIGAS das cartas que a auditoria de fidelidade reescreveu — e
    # continuavam no ar, respondendo.
    #
    # A causa é a chave do upsert: `card_hash` é o hash do TEXTO. Reescrever a
    # carta muda o texto, muda o hash, e a linha nova entra AO LADO da velha em
    # vez de por cima. As duas ficam no índice, com o mesmo endereço de origem,
    # dizendo coisas diferentes — e a busca devolve uma ou outra por sorte.
    #
    # É o defeito que a SPEC-070 existe para impedir (documento revogado que
    # continua respondendo), agora na escala da carta. E é pior aqui: alguém
    # leu, decidiu que estava errada, e ela continuou no ar mesmo assim.
    with open(os.path.join(RAIZ, "scripts", "acervo", "publicar_cartas.py"),
              encoding="utf-8") as arquivo:
        publicador = arquivo.read()

    checar("despublicar_carta_sync" in publicador,
           "o publicador retira as cartas de rodadas anteriores",
           "e usa o MESMO caminho de qualquer carta rejeitada")
    checar("sobrando = [c for c in publicadas if c.get(\"card_hash\") not in vistos]"
           in publicador,
           "e a régua é o arquivo: o que não está nele é resto",
           "`vistos` são os hashes das cartas desta rodada")

    # 🔴 CONTROLE — a varredura NÃO pode alcançar as cartas de conversa. Elas
    # também têm `insurer_key` e não estão neste arquivo; sem o filtro, a
    # limpeza apagaria o acervo inteiro de atendimento.
    checar('not_.is_("source_unit_id", "null")' in publicador,
           "CONTROLE — só alcança quem tem `source_unit_id`",
           "📊 as 12.063 cartas de conversa não têm, e sobreviveriam")

    # 🔴 CONTROLE DE ORDEM — publicar ANTES de limpar. Ao contrário haveria um
    # instante com a carta velha fora e a nova ainda não gravada, e uma falha no
    # meio deixaria o ramo sem resposta nenhuma.
    checar(publicador.index("gravando e publicando")
           < publicador.index("procurando cartas de rodadas anteriores"),
           "CONTROLE — publica primeiro, limpa depois",
           "ao contrário, uma falha no meio deixa o ramo mudo")

    # 🔴 CONTROLE — a varredura precisa ver o ACERVO INTEIRO.
    #
    # 📊 A primeira versão não paginava, e o Supabase devolve no máximo 1.000
    # linhas. A saída denunciou sozinha, com um número bonito demais:
    #
    #     cartas do acervo publicadas : 1000   ← nas DUAS seguradoras
    #
    # Porto tinha 1.127 publicadas contra 1.121 no arquivo; Allianz 1.944 contra
    # 1.938. Seis versões antigas ficaram no ar em cada uma — e ficaram porque a
    # varredura que existe para tirá-las não as viu.
    #
    # Uma limpeza que só olha parte do acervo é PIOR que não ter limpeza: ela
    # imprime "despublicadas: 37" e dá a impressão de que terminou.
    checar(".range(pagina * 1000" in publicador and "if len(lote) < 1000:" in publicador,
           "CONTROLE — a varredura pagina até o fim",
           "📊 sem isso ela parou em 1.000 e deixou 12 cartas antigas no ar")
    checar('.order("id")' in publicador,
           "CONTROLE — e com ordem estável",
           "sem ordenar, a página 2 pode repetir linhas da 1 e pular outras")


def teste_quem_liga_a_ressalva_e_a_procedencia():
    print("\n[5] Só a carta que veio de documento público ganha a ressalva")

    with open(os.path.join(RAIZ, "app", "services", "attendance_distiller.py"),
              encoding="utf-8") as arquivo:
        distiller = arquivo.read()

    checar('documento_publico=bool(card.get("source_unit_id"))' in distiller,
           "`publish_card_sync` liga a ressalva pela PROCEDÊNCIA",
           "`source_unit_id` só existe na carta destilada de condição geral")

    # CONTROLE — a carta de conversa não tem esse campo, então a ressalva fica
    # desligada nela. Se algum caminho passasse `documento_publico=True`
    # fixo, o valor da parcela de um segurado entraria no RAG global.
    checar("documento_publico=True" not in distiller,
           "CONTROLE — e nenhum caminho do destilador a liga fixa",
           "seria o valor da parcela do segurado indo para o RAG global")

    with open(os.path.join(RAIZ, "scripts", "acervo", "publicar_cartas.py"),
              encoding="utf-8") as arquivo:
        publicador = arquivo.read()
    checar("documento_publico=True" in publicador,
           "e o publicador do acervo a liga — ele só lê PDF da SUSEP",
           "é o único lugar onde a origem do texto é conhecida e pública")

    # CONTROLE DO MECANISMO — a ressalva precisa MESMO existir do outro lado.
    # Sem isto, os dois `checar` acima passariam com o parâmetro sendo ignorado
    # em silêncio, e o teste inteiro viraria decoração.
    import inspect

    assinatura = inspect.signature(T.templatize)
    checar("documento_publico" in assinatura.parameters,
           "CONTROLE — e `templatize` aceita mesmo o parâmetro",
           str(assinatura))
    checar(assinatura.parameters["documento_publico"].default is False,
           "CONTROLE — e o padrão é DESLIGADO",
           "quem esquecer de passar fica protegido, não exposto")


def main() -> int:
    print("=" * 74)
    print("O VALOR DA CONDIÇÃO GERAL NÃO É DE NINGUÉM")
    print("=" * 74)
    teste_a_cifra_da_condicao_geral_sobrevive()
    teste_a_reserva_do_valor_nao_e_um_esconderijo()
    teste_o_numero_do_processo_susep_e_a_fonte_nao_o_cnpj()
    teste_motorista_amigo_e_o_nome_do_servico_nao_de_uma_pessoa()
    teste_a_ressalva_nao_abriu_a_porta_para_gente()
    teste_bom_dia_tambem_e_saudacao()
    teste_o_ramo_nao_e_um_logradouro()
    teste_o_que_vem_depois_do_cargo_pode_ser_o_cargo()
    teste_o_que_separa_carta_de_copia_e_o_bloco_literal()
    teste_carta_sem_acento_e_encoding_quebrado()
    teste_a_carta_corrigida_entra_e_a_errada_sai()
    teste_quem_liga_a_ressalva_e_a_procedencia()

    print("\n" + "=" * 74)
    if _PROBLEMAS:
        print(f"{len(_PROBLEMAS)} PROBLEMA(S):")
        for p in _PROBLEMAS:
            print(f"  - {p}")
        return 1
    print("TUDO VERDE — a cifra do contrato passa, a cifra de uma pessoa não.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
