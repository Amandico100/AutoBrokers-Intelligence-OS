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
        checar(_limpo(carta, valor_e_conhecimento=True),
               f"passa no acervo: {carta[:46]!r}", T.templatize(
                   carta, valor_e_conhecimento=True)[:60])

    # 🔴 CONTROLE — a rodada que repete o cenário anterior. Sem ela, o bloco
    # acima passaria também se a regra de valor tivesse sido APAGADA do
    # templater, e ninguém veria: a conversa perderia a máscara em silêncio.
    for carta in cartas:
        checar(not _limpo(carta),
               f"CONTROLE — e continua mascarada na conversa: {carta[:34]!r}",
               "a mudança é da ressalva, não da regra")


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
        checar(not _limpo(frase, valor_e_conhecimento=True),
               f"CONTROLE — {rotulo} recusado mesmo com a ressalva ligada",
               T.templatize(frase, valor_e_conhecimento=True)[:56])


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


def teste_a_lista_de_documentos_pode_ser_longa():
    print("\n[6] A lista de documentos é longa porque a exigência é longa")

    with open(os.path.join(RAIZ, "scripts", "acervo", "publicar_cartas.py"),
              encoding="utf-8") as arquivo:
        publicador = arquivo.read()

    # 📊 2 das 1.121 cartas da Porto foram recusadas por tamanho, e as duas são
    # `documento`: o que a fiança exige para danos ao imóvel (940 caracteres) e
    # o que o vida exige para invalidez por acidente (952).
    checar("MAX_CARACTERES_DOCUMENTO = 1200" in publicador,
           "`documento` tem teto próprio",
           "cortada ao meio, a lista manda juntar metade dos papéis")
    checar('teto = MAX_CARACTERES_DOCUMENTO if faceta == "documento" else MAX_CARACTERES'
           in publicador,
           "e o teto é escolhido PELA FACETA",
           "uma ideia só: 'o que você precisa juntar'")

    # CONTROLE — a exceção é de UMA faceta. Se o teto maior valesse para todas,
    # o limite deixaria de impedir o que ele existe para impedir: alguém colar
    # o pedaço do contrato e chamar de carta.
    checar("MAX_CARACTERES = 900" in publicador,
           "CONTROLE — e as outras facetas mantêm o teto de 900",
           "`escopo` e `exclusao` longos continuam sendo contrato copiado")
    checar(publicador.count("MAX_CARACTERES_DOCUMENTO") == 2,
           "CONTROLE — a exceção é citada em UM lugar só",
           "exceção espalhada vira regra sem ninguém decidir")


def teste_quem_liga_a_ressalva_e_a_procedencia():
    print("\n[5] Só a carta que veio de documento público ganha a ressalva")

    with open(os.path.join(RAIZ, "app", "services", "attendance_distiller.py"),
              encoding="utf-8") as arquivo:
        distiller = arquivo.read()

    checar('valor_e_conhecimento=bool(card.get("source_unit_id"))' in distiller,
           "`publish_card_sync` liga a ressalva pela PROCEDÊNCIA",
           "`source_unit_id` só existe na carta destilada de condição geral")

    # CONTROLE — a carta de conversa não tem esse campo, então a ressalva fica
    # desligada nela. Se algum caminho passasse `valor_e_conhecimento=True`
    # fixo, o valor da parcela de um segurado entraria no RAG global.
    checar("valor_e_conhecimento=True" not in distiller,
           "CONTROLE — e nenhum caminho do destilador a liga fixa",
           "seria o valor da parcela do segurado indo para o RAG global")

    with open(os.path.join(RAIZ, "scripts", "acervo", "publicar_cartas.py"),
              encoding="utf-8") as arquivo:
        publicador = arquivo.read()
    checar("valor_e_conhecimento=True" in publicador,
           "e o publicador do acervo a liga — ele só lê PDF da SUSEP",
           "é o único lugar onde a origem do texto é conhecida e pública")

    # CONTROLE DO MECANISMO — a ressalva precisa MESMO existir do outro lado.
    # Sem isto, os dois `checar` acima passariam com o parâmetro sendo ignorado
    # em silêncio, e o teste inteiro viraria decoração.
    import inspect

    assinatura = inspect.signature(T.templatize)
    checar("valor_e_conhecimento" in assinatura.parameters,
           "CONTROLE — e `templatize` aceita mesmo o parâmetro",
           str(assinatura))
    checar(assinatura.parameters["valor_e_conhecimento"].default is False,
           "CONTROLE — e o padrão é DESLIGADO",
           "quem esquecer de passar fica protegido, não exposto")


def main() -> int:
    print("=" * 74)
    print("O VALOR DA CONDIÇÃO GERAL NÃO É DE NINGUÉM")
    print("=" * 74)
    teste_a_cifra_da_condicao_geral_sobrevive()
    teste_a_ressalva_nao_abriu_a_porta_para_gente()
    teste_bom_dia_tambem_e_saudacao()
    teste_o_ramo_nao_e_um_logradouro()
    teste_o_que_vem_depois_do_cargo_pode_ser_o_cargo()
    teste_a_lista_de_documentos_pode_ser_longa()
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
