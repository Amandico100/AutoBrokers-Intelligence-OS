"""CARTÓGRAFO v1 (SPEC-034 Onda 2) — motor de exploração de URAs de seguradoras.

Conceito validado no mercado (Botium Crawler): conversar com o bot da seguradora
clicando/digitando cada opção e montar a árvore completa do fluxo (Mapa de URA).

Este módulo é o MOTOR PURO (decisões, freios, construção do mapa) — testável
offline. A fiação com a instância Evolution GO dedicada (número exclusivo de
exploração que o founder vai prover) entra num router fino por cima deste motor.

FREIOS INEGOCIÁVEIS (hard-coded, fora do alcance de LLM):
1. NUNCA responde afirmativamente a uma tela de confirmação final — responde a
   opção de SAIR/CANCELAR e marca o nó como 'finalize'.
2. NUNCA entra em ramo de SINISTRO além do primeiro nó (registra que existe e sai).
3. Máximo de mensagens por sessão de exploração (padrão 60) — estourou, encerra.
4. Se a URA pedir um dado que não temos, aborta o ramo educadamente ('needs_data').
5. Horário permitido (madrugada por padrão) — verificado pelo runner, não aqui.

Escopo atual: ASSISTÊNCIA via WhatsApp (decisão do founder 13/07 — sinistro e
vidros-portal ficam para depois).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.services.ura_map_service import node_hash, normalize_screen_text

MAX_MESSAGES_PER_SESSION = 60

# Telas de confirmação FINAL (freio 1) — mesmos padrões dos finalize_anchors.
_FINALIZE_RE = re.compile(
    r"podemos confirmar|posso confirmar|tudo est[áa] correto|como voc[êe] quer prosseguir"
    r"|confirmar o agendamento|posso continuar o agendamento|deseja confirmar",
    re.IGNORECASE,
)
_ABORT_PREFERENCES = ["Sair e não agendar", "Sair", "Cancelar", "Não", "Voltar", "0", "9"]

# Ramos proibidos de explorar a fundo (freio 2).
_SINISTRO_RE = re.compile(
    r"sinistro|colis[ãa]o com terceiro|aviso de acidente|avisar ou acompanhar", re.IGNORECASE)

# Pedidos de dados que sabemos preencher com o dataset COMPLETO (ordem importa:
# específico antes de genérico). Founder 14/07: "o Cartógrafo não pode ter
# dados incompletos" — cada ramo tem os obrigatórios no test_data.
_DATA_REPLIES = [
    (re.compile(r"cpf ou cnpj|digite o cpf|informe o cpf", re.IGNORECASE), "cpf"),
    (re.compile(r"placa", re.IGNORECASE), "placa"),
    (re.compile(r"complemento", re.IGNORECASE), "complemento"),
    (re.compile(r"ponto de refer[êe]ncia|refer[êe]ncia do local", re.IGNORECASE), "ponto_referencia"),
    (re.compile(r"para onde|destino|levar (?:o|seu) ve[íi]culo|onde o guincho deve", re.IGNORECASE), "endereco_destino"),
    (re.compile(r"endere[çc]o completo|onde (?:voc[êe]|o ve[íi]culo|o carro) est[áa]|local do atendimento"
                r"|informe o endere[çc]o|digite o endere[çc]o|endere[çc]o do local", re.IGNORECASE), "endereco_local"),
    (re.compile(r"telefone|celular|n[úu]mero (?:de|para) contato", re.IGNORECASE), "telefone"),
    (re.compile(r"nome completo|nome de quem|quem est[áa] no local|nome do (?:condutor|respons[áa]vel)", re.IGNORECASE), "nome"),
    (re.compile(r"cor do ve[íi]culo", re.IGNORECASE), "cor"),
    (re.compile(r"cep\b", re.IGNORECASE), "cep"),
]

# Re-identificação (fix 14/07 — URA lembra o número e saúda o cliente anterior):
# opção de trocar o CPF tem PRIORIDADE na 1ª visita ao menu.
_REIDENTIFY_RE = re.compile(r"informar outro cpf|outro cpf/?cnpj|n[ãa]o sou|trocar (?:de )?cpf", re.IGNORECASE)

# Humano entrou na conversa (freio novo): sair educadamente e ENCERRAR a
# exploração — nunca conversar com atendente humano usando nome de cliente.
_HUMANO_RE = re.compile(
    # Formas que a URA usa para dizer "daqui em diante é gente".
    #
    # Esta lista era estreita demais e deixava passar justamente a frase que a
    # Allianz mais repete — "Vou transferir seu caso para um especialista",
    # vista 233 vezes nas conversas da Resulta. O padrão exigia "vou TE
    # transferir" ou "transferindo para", e nenhum casava.
    #
    # O custo do erro: tudo que o especialista humano digitou depois disso
    # ("Boa tarde!", "Ok um momento", "Precisa de escada?") entrou no Atlas
    # como se fosse tela de URA. O mapa da Allianz tinha 930 telas quando a URA
    # real tem umas dezenas — o resto era conversa.
    # 03/08/2026 — A HDI TEM O MESMO DEFEITO, MAIOR.
    #
    # 📊 Medido em `observed_events` da HDI (1.965 eventos, 38 sessões, projeto
    # dcajcvlzcjbmyapmklil): das 23 formas distintas de anunciar transferência
    # este padrão pegava TRÊS — 3 ocorrências de 61. A frase canônica da
    # seguradora,
    #
    #     "Para seguir com o seu atendimento será necessário falar com um de
    #      nossos especialistas. Por favor, aguarde."
    #
    # passava batida porque o padrão espera `aguarde.{0,30}especialista` e a
    # HDI INVERTE A ORDEM: o especialista vem antes do aguarde.
    #
    # O padrão ficou organizado por FAMÍLIA. Uma seguradora nova traz uma
    # redação nova, quase nunca uma família nova.

    # (1) TRANSFERÊNCIA ANUNCIADA — "eu vou passar você adiante".
    r"transferindo (?:voc[êe] )?para"
    r"|vou (?:te |lhe )?transferir"
    r"|vou (?:transferir|encaminhar|direcionar) (?:seu |o seu |sua |a sua )?"
    r"(?:caso|atendimento|solicita[çc][ãa]o|chamado|contato)"
    # "vou te transferir para um DE NOSSOS analistas": o "de nossos" no meio
    # quebrava `para um (especialista|analista)`, que exigia o substantivo
    # colado no artigo. 📊 6 das formas cegas da HDI morriam exatamente aqui.
    r"|(?:transferir|transfiro|encaminhar|direcionar)"
    r".{0,25}(?:para|a) um(?:a)?(?: d[oe]s? nossos?| d[oe] nossas?)? ?"
    r"(?:especialista|atendente|consultor|analista|colaborador)"
    r"|(?:enquanto|assim que) (?:te |lhe )?transfiro"
    r"|(?:irei|vamos|iremos|preciso|precisar[ei]?) (?:te |lhe )?"
    r"(?:transferir|encaminhar|direcionar)"
    r"|voc[êe] foi transferid[oa]"
    r"|transferir para (?:o )?setor"

    # (2) FILA — ninguém põe cliente em fila para falar com robô.
    # 📊 A família mais comum da HDI: 12+10+7+5+4+2+2 ocorrências, variando só
    # o tempo médio de espera. E "antedimento" é typo DELES, não meu.
    r"|\bna fila\b|\bda fila\b|para fila de|fila de an?te?ndimento"
    r"|aguarde at[ée] que um d[oe]s? nossos?"
    r"|(?:procuramos|buscamos|localizamos) um (?:atendente|analista|especialista)"
    r"|toda (?:a )?nossa equipe est[áa] em atendimento"

    # (3) FALAR COM GENTE — a HDI diz "será necessário falar com".
    r"|falar com um(?:a)? (?:d[oe]s? nossos?|d[oe] nossas?) ?"
    r"(?:especialista|atendente|consultor|analista|colaborador)"
    # "será necessário a AJUDA DE UM DE nossos analistas" e "será necessário a
    # ANÁLISE DE nossos especialistas" — as duas na HDI, com e sem o "um de".
    r"|(?:ajuda|an[áa]lise|aux[íi]lio)\s+d[eo](?:\s+um\s+d[eo])?\s+nossos?\s+"
    r"(?:especialista|atendente|consultor|analista)"
    r"|um de nossos atendentes"
    r"|um de nossos analistas (?:vai|ir[áa]) seguir"
    r"|nossa equipe (?:vai|ir[áa]) (?:te )?atender"
    r"|aguarde.{0,30}(?:atendente|especialista|consultor)"
    r"|falar com um especialista agora"

    # (4) A PESSOA SE APRESENTA — já é ela escrevendo, não a URA.
    # 📊 11 nomes distintos na HDI: "Olá, meu nome é Camila Rossi e irei
    # realizar seu atendimento." Cada nome virava uma TELA nova do mapa.
    r"|meu nome [ée] .{1,60}?(?:irei realizar|vou realizar|darei continuidade"
    r"|dar continuidade|e irei|e vou|como posso|em que posso)"
    r"|dar[ei]? continuidade (?:no|ao) seu atendimento"

    # (5) A PESSOA ENCERRA — o fim da conversa humana também é fase humana.
    r"|conversa foi (?:encerrada|finalizada) pelo atendente"
    r"|conversa foi colocada em espera",
    re.IGNORECASE)

# A OFERTA CONDICIONAL NÃO É UM HANDOFF.
#
# 📊 A tela de BOAS-VINDAS da HDI — a primeira mensagem de toda sessão — diz:
#
#     "Ao final da abertura, após a pesquisa de satisfação, caso seja
#      necessário, você pode falar com um de nossos analistas digitando
#      'falar com atendente'."
#
# É instrução sobre o futuro, não passagem para gente. Sem este freio, alargar
# `_HUMANO_RE` marcaria a PRIMEIRA tela de toda sessão da HDI como handoff — e
# a URA INTEIRA viraria "conversa". É o estrago de 28/07/2026 na Allianz (782
# de 919 telas carimbadas como humano) entrando pela porta oposta.
#
# O sinal é o modo verbal: quem OFERECE diz "você pode", "caso precise", "se
# desejar", "digitando". Quem TRANSFERE diz "será necessário", "aguarde",
# "vou te transferir".
_HUMANO_HIPOTETICO = re.compile(
    r"caso (?:seja|precise|queira|deseje|necess[áa]rio)"
    r"|voc[êe] (?:pode|poder[áa]|consegue)"
    r"|se (?:precisar|desejar|preferir|quiser|for necess[áa]rio)"
    r"|digitando|basta (?:digitar|enviar|responder)"
    r"|a qualquer momento|sempre que (?:precisar|quiser)",
    re.IGNORECASE)

# A pergunta é feita FRASE A FRASE. Sobre o texto inteiro, o "caso seja
# necessário" da tela de boas-vindas absolveria uma transferência real escrita
# três linhas abaixo — e o inverso também: uma frase de transferência de
# verdade faria a oferta condicional passar por handoff.
_FIM_DE_FRASE = re.compile(r"(?<=[.!?;])\s+|\n+")


def entrou_humano(texto: str) -> bool:
    """A URA acabou e daqui em diante quem escreve é uma pessoa?

    É esta função — não `_HUMANO_RE` cru — que o Tecelão e o Cartógrafo devem
    perguntar. O regex sozinho não distingue "será necessário falar com um de
    nossos especialistas" (aconteceu) de "caso seja necessário, você pode falar
    com um de nossos analistas" (pode acontecer um dia), e as duas frases estão
    na MESMA seguradora — a segunda na tela de abertura de toda sessão.
    """
    for frase in _FIM_DE_FRASE.split(str(texto or "")):
        if not frase.strip():
            continue
        if _HUMANO_RE.search(frase) and not _HUMANO_HIPOTETICO.search(frase):
            return True
    return False


POLITE_EXIT = "Ah, me desculpe — era só uma dúvida sobre o menu e já consegui o que eu precisava. Pode encerrar por aqui. Muito obrigado! 🙂"


def _sem_negrito(texto: str) -> str:
    """Tira o negrito do WhatsApp (`*assim*`) sem mexer no resto.

    Isto é a raiz de um defeito caro. A Allianz manda o menu assim:

        *1 -* Automóvel, Moto ou Caminhão
        *2 -* Residência, Condomínio ou Empresa

    O asterisco vem ANTES do número. O regex de menu numerado espera o dígito
    logo após a quebra de linha, então não casava nada — e a tela mais
    importante da corretora (a que escolhe Residencial, Condomínio ou
    Empresarial) ficava com ZERO opções detectadas.

    Medido em 28/07/2026 sobre as conversas reais da Resulta: 930 telas
    capturadas e só 170 com opções. Não era "os clientes só pedem uma coisa" —
    era o leitor cego para o formato da seguradora.
    """
    # `*` só delimita negrito quando abraça conteúdo sem espaço na borda. Um
    # asterisco solto no meio de um endereço não deve ser tocado.
    return re.sub(r"\*(\S(?:[^*\n]*\S)?)\*", r"\1", str(texto or ""))


# `2` do menu, `2)` , `2 -` … O número é a CHAVE de casamento com o que o
# humano digita. Guardá-lo junto do rótulo é o que liga "a atendente digitou 2"
# à opção "Residência, Condomínio ou Empresa".
_NUMERADA = re.compile(r"(?:^|\n)\s*(\d{1,2})\s*[-–.)\]]\s*([^\n|]{2,80})")


# `Ex: ...`, `Assistência: 8923467`, `Data do vencimento: ...` — cabeça curta,
# dois-pontos, valor. Só usado no palpite por linha; menu numerado e lista
# estruturada não passam por aqui.
_ROTULO_VALOR = re.compile(r"^[^:\n]{1,40}:\s*\S")


# MENU SEM CHAMADA PARA ESCOLHER NÃO É MENU.
#
# O terceiro ramo de `parse_options` — o das linhas nuas — é um PALPITE: ele
# assume que duas ou mais linhas curtas no fim de uma mensagem são opções. É
# ele que lê as listas da Evolution quando a estrutura não vem, e é ele que
# produziu as duas piores invenções do mapa da HDI (📊 03/08/2026):
#
#     "Seguimos à disposição.\n\nFique tranquilo…\n\nHDI\nCerteza que te
#      deixa seguro"          →  menu de 2 opções. É o RODAPÉ DE ASSINATURA.
#
#     "so para confirmar\nLocalização do Cliente\nEndereço: …\nLocalização
#      de Destino\nEndereço: …"   →  menu de 2 opções. É o HUMANO digitando.
#
# Nenhuma das duas pede escolha nenhuma. A regra que separa é essa mesma: uma
# tela que oferece caminho SEMPRE convida a escolher — pergunta, ou manda
# selecionar, digitar, informar, indicar.
#
# 📊 Blast radius medido sobre os 10 mapas observados: dos 918 nós com opções,
# 19 caem por esta regra — e 16 deles são anotação de analista, dump de dados
# de prestador, assinatura ou lista de documentos. Dos 3 restantes, os menus
# reais (Bradesco, Yelum, Porto) vêm da estrutura `interactive`, que nem passa
# por aqui; e o da Porto ("Os horários mais próximos…") tem as três opções já
# classificadas como horário/navegação, então não muda cobertura.
_CHAMADA_PARA_ESCOLHER = re.compile(
    r"\?"
    r"|selecion|escolh|digit|inform|clique|toque|marque|respond"
    r"|me (?:diga|dizer)|poderia"
    r"|op[çc][ãa]o|op[çc][õo]es|qual|quais|prefere|abaixo|a seguir"
    r"|indique|indicando|envie|enviar",
    re.IGNORECASE)


# PESQUISA DE SATISFAÇÃO NÃO É ROTA — EM NENHUM FORMATO.
#
# 📊 Medido nos mapas observados em 03/08/2026. A HDI usa DOIS formatos na
# mesma seguradora, e nenhum era reconhecido:
#
#     "A sua opinião é muito importante. O que achou do atendimento prestado
#      pelo nosso analista?"        →  5 - Ótimo / 4 - Bom / … / 1 - Péssimo
#     "O quão satisfeito você está com este atendimento?"  →  1 / 2 / 3 / 4 / 5
#
# São 10 lacunas na HDI que nunca fecham: ninguém dá todas as notas, e a nota
# que não deu vira buraco eterno. Mesma família do "Voltar", e a Porto já
# tinha metade dela tratada por `_NOTA_DE_PESQUISA` ("09 = bom 🥰").
#
# O DETECTOR É DUPLO DE PROPÓSITO. A palavra "pesquisa" sozinha não serve —
# estas TRÊS telas falam de pesquisa e SÃO rota de verdade:
#
#     Zurich  "…ainda não respondeu nossa pesquisa. O que acha de fazer isso
#              agora?"                                    → Sim | Não
#     Mapfre  "O acompanhamento está sendo satisfatório?" → Sim | Não
#     Yelum   "…a pesquisa não foi respondida…"           → Responder pesquisa
#                                                           | Novo atendimento
#
# O que separa é a ESCALA. A tela de pesquisa oferece uma RÉGUA: números nus,
# ou os degraus ótimo/bom/neutro/ruim/péssimo. Quem oferece Sim/Não está
# perguntando o caminho — não pedindo nota.
_PEDIDO_DE_NOTA = re.compile(
    r"qu[ãa]o satisfeit|grau de satisfa[çc][ãa]o|pesquisa de satisfa[çc][ãa]o"
    r"|avalie|avaliar o atendimento|como voc[êe] avalia"
    r"|sua opini[ãa]o [ée] (?:muito )?importante"
    r"|o que achou do atendimento"
    r"|d[êe] (?:uma )?nota|nota de \d+ a \d+"
    r"|\d+ muito bom e \d+ muito ruim",
    re.IGNORECASE)

# Os degraus da régua. `bo[am]` cobre "Bom"/"Boa"; o número nu cobre a escala
# crua ("1\n2\n3\n4\n5") que a HDI manda sem rótulo nenhum.
_PALAVRA_DE_NOTA = re.compile(
    r"\b(?:[óo]tim[oa]|bo[am]|regular|neutr[oa]|indiferente|ruim|p[ée]ssim[oa]"
    r"|satisfeit[oa]|insatisfeit[oa]|excelente)\b",
    re.IGNORECASE)


def _e_degrau_de_escala(linha: str) -> bool:
    s = str(linha or "").strip()
    if not s:
        return False
    nu = re.sub(r"[^\w\s]", " ", s).strip()
    if re.fullmatch(r"\d{1,2}", nu):
        return True
    return bool(_PALAVRA_DE_NOTA.search(nu))


# LISTA GERADA PELO CLIENTE NÃO É ROTA.
#
# 📊 "Identificamos que há mais de um veículo para esta apólice, por favor,
# *digite o número* indicando o veículo…" — a HDI lista as placas DAQUELE
# segurado. Cada cliente recebe uma lista diferente, então cada item é uma
# lacuna que nunca fecha. É a mesma família da lista de oficinas próximas da
# Porto (`_ESCOLHA_DE_PRESTADOR`) e da lista de protocolos
# (`_PROTOCOLO_COMO_OPCAO`).
#
# O templatizador já apaga as placas reconhecíveis, mas sobrou "17 - Placa
# 0KM0000" (placa de zero-quilômetro, que não tem a forma de placa) e o
# "18 - Nenhuma das opções anteriores" que fecha a lista. Por isso a regra é
# de TELA e não de rótulo: "Nenhuma das anteriores" é opção LEGÍTIMA em dois
# menus reais da HDI ("Criança | Idoso | … | Nenhuma das anteriores") e não
# pode ser descartada pelo texto dela.
#
# Deliberadamente estreita: a Porto tem "Por favor, selecione o veículo." sem
# o "mais de um", e ali "Outro veículo" é rota de verdade — fica de fora.
_LISTA_DO_CLIENTE = re.compile(
    r"(?:identificamos|identifiquei|encontramos|encontrei)[^.\n]{0,60}"
    r"mais de (?:um ve[íi]culo|uma ap[óo]lice|um contrato)"
    r"|digite o n[úu]mero[^.\n]{0,40}indicando o ve[íi]culo",
    re.IGNORECASE)


def nao_e_rota(text: str) -> Optional[str]:
    """Esta TELA inteira não oferece caminho nenhum? Devolve o motivo, ou None.

    Difere de `acao_conhecida`, que julga um rótulo: aqui o veredito é da tela.
    Uma tela marcada assim continua no mapa com o texto e o motivo — é
    evidência, e apagá-la destruiria a prova de por que ela não conta. O que
    ela deixa de ter é OPÇÃO: e sem opção, ela sai dos dois lados da fração da
    cobertura (ver `weaver.compute_coverage`).
    """
    s = _sem_negrito(str(text or ""))
    if _PEDIDO_DE_NOTA.search(s) and sum(
            1 for ln in s.splitlines() if _e_degrau_de_escala(ln)) >= 3:
        return "pesquisa_de_satisfacao"
    if _LISTA_DO_CLIENTE.search(s):
        return "lista_do_cliente"
    return None


def parse_options(text: str) -> List[str]:
    """Extrai os rótulos clicáveis de uma tela renderizada.

    Formatos cobertos:
      1. `Botão 1: X` (botões da Evolution);
      2. menus numerados `1 - X`, `1) X`, `*1 -* X`, `*1 - X:* descrição`;
      3. listas da Evolution: corpo + um título por linha, sem prefixo.

    O rótulo devolvido vem **com o número na frente** quando o menu é numerado
    (`"2 - Residência, Condomínio ou Empresa"`). Sem o número, a aresta gravada
    como `"2"` — que é o que a atendente digitou — nunca casa com a opção, e a
    rota aparece como não percorrida mesmo tendo sido percorrida centenas de
    vezes.

    Telas que `nao_e_rota` reprova saem daqui SEM opção nenhuma — pesquisa de
    satisfação e lista gerada pelo cliente não têm caminho a percorrer, e o
    que elas produziam era lacuna que nunca fecha.
    """
    if nao_e_rota(text):
        return []

    limpo = _sem_negrito(text)
    labels: List[str] = []

    for m in re.finditer(r"bot[ãa]o\s*\d+\s*:\s*([^\n|]+)", limpo, re.IGNORECASE):
        labels.append(m.group(1).strip())

    for m in _NUMERADA.finditer(limpo):
        numero, rotulo = m.group(1), m.group(2).strip().rstrip(":")
        # O `:` do formato `1 - Residencial: Para sua casa...` separa o rótulo
        # da explicação. O que se clica é o rótulo.
        if ":" in rotulo:
            cabeca, _, cauda = rotulo.partition(":")
            if len(cabeca.strip()) >= 2:
                rotulo = cabeca.strip()
        labels.append(f"{numero} - {rotulo}" if rotulo else numero)

    # O RAMO DO PALPITE — e ele só corre se a tela CONVIDAR a escolher.
    # Ver `_CHAMADA_PARA_ESCOLHER`: sem convite, linha curta no fim da mensagem
    # é assinatura da seguradora ou frase de gente, não item de menu.
    if not labels and _CHAMADA_PARA_ESCOLHER.search(limpo):
        lines = [ln.strip() for ln in limpo.splitlines() if ln.strip()]
        candidates: List[str] = []
        for ln in lines[1:]:  # a 1ª linha é o corpo/pergunta
            # Marcador de LISTA (`- item`, `• item`) não é opção de menu. A
            # Allianz manda uma tela de instruções assim:
            #
            #     - Escolha a opção desejada digitando o número;
            #     - Ainda não consigo entender fotos, vídeos ou áudios;
            #
            # Sem esta exclusão, a tela de dicas viraria um "menu" de duas
            # opções que ninguém pode escolher — e opção que não existe vira
            # lacuna eterna na cobertura.
            if ln[0] in "-–•*·":
                continue
            # `Rótulo: valor` é LEITURA DE DADO, nunca escolha de menu.
            #
            # A tela de comprovante da Yelum ("Assistência: 8923467"), a da
            # Porto ("Agendamento: 28/01/2026, entre 10h00 e 12h00") e a da
            # Zurich ("Quantidade de parcelas restantes: 3") produziam 260
            # opções inventadas em 54 telas na conta de 28/07/2026. E uma
            # tela da HDI trazia um histórico colado — "10:56 - ALINE
            # FERNANDA ...: Isso que estou questionando" — que colocava o
            # NOME DE UMA PESSOA dentro de um rótulo de opção, num mapa que
            # é conhecimento global entre corretoras.
            #
            # Opção inventada é pior que opção perdida: a perdida aparece
            # como tela sem menu (dá para ver); a inventada vira rota que
            # ninguém pode percorrer e afunda a cobertura para sempre.
            if _ROTULO_VALOR.match(ln):
                continue
            # 80 e não 48: `*1 - Residencial:* Para sua casa ou apartamento
            # individual` tem 56 caracteres e era descartado por 8 — perdendo
            # justamente o menu de ramo da Allianz.
            if 2 <= len(ln) <= 80 and not ln.endswith((".", "?", "!", ":", ",", ";")) \
                    and not ln[0].islower() and len(ln.split()) <= 10:
                candidates.append(ln)
        if len(candidates) >= 2:
            labels = candidates

    seen, out = set(), []
    for lab in labels:
        k = lab.lower()
        if k not in seen:
            seen.add(k)
            out.append(lab)
    return out


# Opções cujo comportamento já é conhecido sem ninguém precisar percorrer.
#
# Medido nos mapas em 28/07/2026: "voltar" aparece 222 vezes em 5 seguradoras
# (190 delas contadas como lacuna), "sair" 73 vezes, "encerrar atendimento" 5.
# São ~270 lacunas que nunca fecham — porque ninguém clica em "Voltar" num
# atendimento de verdade, e se clicar não ensina nada: já se sabe o que
# acontece.
#
# O agente também precisa disso. "Voltar" não é uma rota a descobrir: é a
# saída de emergência quando ele errou o caminho, e "Sair" é como encerrar
# sem deixar a conversa pendurada.
_NAVEGACAO = (
    # "Responder novamente" é a irmã do "Voltar" na HDI: a tela "Não entendi.
    # Lembre-se que, para responder, você precisa selecionar o botão…" oferece
    # as duas, e só "Voltar" era reconhecida. 📊 A outra ficava como lacuna que
    # nunca fecha — ninguém erra de propósito num atendimento real, e se
    # errasse não ensinaria nada: já se sabe que ela repete a pergunta.
    ("voltar", re.compile(r"^(?:voltar|volta|retornar|voltar ao menu|menu anterior|"
                          r"voltar ao in[íi]cio|voltar para o in[íi]cio|"
                          r"responder novamente|tentar novamente)$", re.IGNORECASE)),
    ("sair",   re.compile(r"^(?:sair|encerrar|finalizar|encerrar atendimento|"
                          r"finalizar atendimento|encerrar conversa)$", re.IGNORECASE)),
    ("menu",   re.compile(r"^(?:menu principal|in[íi]cio|menu|come[çc]ar de novo)$",
                          re.IGNORECASE)),
)

# Escolha de data/horário de agendamento. Cada dia gera um rótulo diferente
# ("{DATA} (quarta-feira)", "entre 10h e 12h"), então essas opções NUNCA
# fecham: o mapa de amanhã cria lacunas novas que ninguém percorre. E todas
# levam ao mesmo lugar — a tela de confirmação do agendamento.
#
# 03/08/2026 — a faixa de horário também vem com NOME na frente.
#
# 📊 A HDI oferece "Manhã (08h às 12h)" e "Tarde (13h às 18h)". O padrão
# exigia que a faixa começasse a linha (`^\s*(?:entre\s+)?\d`), então as duas
# eram lacuna. É a mesma coisa que "entre 10h e 12h": qualquer período serve,
# e todos levam à confirmação do agendamento.
_ESCOLHA_DE_HORARIO = re.compile(
    r"\{DATA\}|(?:entre\s+)?\d{1,2}\s*h(?:\d{2})?\s*(?:[àa]s|as|at[ée]|e|-)\s*\d{1,2}\s*h|"
    r"(?:segunda|ter[çc]a|quarta|quinta|sexta|s[áa]bado|domingo)-?feira",
    re.IGNORECASE)


def acao_conhecida(label: str) -> Optional[str]:
    """O que esta opção faz, quando dá para saber sem observar.

    Devolve "voltar", "sair", "menu", "horario" — ou None quando a opção é
    conteúdo de verdade e só um atendimento real pode ensinar.

    É deliberadamente curto. "Cancelar serviço", "Mais opções" e "Outro
    assunto" FICAM de fora: parecem navegação e não são — abrem fluxo próprio,
    e marcá-las como conhecidas esconderia rota que falta mapear.
    """
    limpo = re.sub(r"^\s*\d{1,2}\s*[-–.)\]]\s*", "", str(label or "")).strip()
    limpo = re.sub(r"^[^\w{]+", "", limpo).strip()  # emoji/ícone na frente
    if not limpo:
        return None
    for acao, rx in _NAVEGACAO:
        if rx.match(limpo):
            return acao
    if _MAIS_NAVEGACAO.match(limpo):
        return "menu"
    if _ESCOLHA_DE_HORARIO.search(limpo):
        return "horario"
    if _ESCOLHA_DE_PRESTADOR.search(limpo):
        return "prestador"
    if _NOTA_DE_PESQUISA.match(str(label or "").strip()):
        return "pesquisa"
    if _PROTOCOLO_COMO_OPCAO.match(str(label or "").strip()):
        return "protocolo"
    # Contra o rótulo BRUTO, não o limpo: `limpo` já teve o "2 - " removido, e
    # "2 - Não, prefiro falar com um atendente" — opção legítima e numerada —
    # passaria a parecer texto corrido de 35 caracteres sem número.
    if numero_da_opcao(label) is None and _NAO_E_OPCAO.match(str(label or "").strip()):
        return "nao_e_opcao"
    return None


# LISTA DE PRESTADOR NÃO É MENU DA URA.
#
# A Porto oferece as oficinas mais próximas do cliente, com distância e
# endereço: "2 - Porto Alegre São João - 5.16km - Av Benjamin Constant, 1242".
# Cada cliente recebe uma lista diferente, então CADA ITEM é uma lacuna que
# nunca fecha — e são muitos por atendimento.
#
# Medido em 29/07/2026: das 372 lacunas distintas da Porto, boa parte é isso.
# É a mesma família de "Voltar" e da escolha de horário: o comportamento já se
# conhece (escolher um prestador leva à confirmação daquele prestador), e o
# rótulo muda a cada atendimento.
_ESCOLHA_DE_PRESTADOR = re.compile(
    r"\d+[.,]\d+\s*km"                                  # "5.16km"
    r"|\b(?:av|avenida|r|rua|rod|rodovia|estrada|al|alameda)\.?\s+[^,]{3,},\s*\d"
    r"|\s-\s[a-z]{2}$",                                 # "…, canoas - rs"
    re.IGNORECASE)

# TEXTO CORRIDO NÃO É OPÇÃO.
#
# O leitor de tela também capturou frase de pesquisa de satisfação ("peço
# gentilmente que avalie meu atendimento", "a pesquisa é super rápida e vai nos
# ajudar") e item de lista de documentos ("laudo técnico atestando a causa e
# extensão dos danos"). Nenhuma delas é escolha de menu — ninguém digita nada
# para "escolhê-las" — e todas contavam como buraco eterno na cobertura.
#
# A marca é dupla e tem de ser dupla: **sem número de opção** E longa.
#
# O limite de 32 caracteres não é palpite — é limite do WhatsApp. Título de
# linha de lista aceita 24 caracteres e título de botão aceita 20. Logo, opção
# interativa de verdade NUNCA passa de ~24 sem vir numerada. Acima disso, sem
# número, é texto que o leitor de tela pegou por engano.
#
# Exigir as duas condições é o que evita comer opção legítima — apagar rota de
# verdade seria pior do que a lacuna eterna que estamos consertando.
_NAO_E_OPCAO = re.compile(r"^(?![\d]).{32,}$", re.DOTALL)

# NOTA DE PESQUISA DE SATISFAÇÃO NÃO É ROTA.
#
# A Porto fecha o atendimento com uma escala de 0 a 10 — "09 = bom 🥰",
# "10 = ótimo 🤩". São ONZE opções por tela de pesquisa, e ninguém dá todas as
# notas: cada nota não dada fica lacuna para sempre. Mesma família de "Voltar".
# Navegação que faltava, achada nas lacunas reais da Porto em 29/07/2026.
# "Escolher outra opção" e "Encerrar a conversa" são o mesmo tipo de coisa que
# "Voltar" e "Sair": comportamento conhecido, e ninguém as clica num
# atendimento real porque o objetivo é resolver, não navegar.
_MAIS_NAVEGACAO = re.compile(
    r"^(?:escolher outra op|outra op[çc][ãa]o|encerrar (?:a )?conversa|"
    r"continuar o assunto|outros hor[áa]rios|fico no aguardo|"
    r"n[ãa]o sei o cep|informar outro cpf|recome[çc]ar com outro)",
    re.IGNORECASE)

_NOTA_DE_PESQUISA = re.compile(r"^\s*\d{1,2}\s*[=]\s*\S", re.IGNORECASE)

# PROTOCOLO DO CLIENTE COMO RÓTULO DE OPÇÃO.
#
# "1 - 124279107688" é a lista dos sinistros DAQUELE cliente. Cada atendimento
# traz números diferentes, então cada item é uma lacuna que nunca fecha — igual
# à lista de oficinas próximas. O comportamento se conhece: escolher um
# protocolo abre aquele protocolo.
_PROTOCOLO_COMO_OPCAO = re.compile(r"^\s*\d{1,2}\s*[-–.)\]]\s*\d{6,}\s*$")



def numero_da_opcao(label: str) -> Optional[str]:
    """O número que a pessoa digita para escolher esta opção, se houver."""
    m = re.match(r"\s*(\d{1,2})\s*[-–.)\]]", str(label or ""))
    return m.group(1) if m else None


def classify_screen(text: str, options: List[str]) -> str:
    if _FINALIZE_RE.search(text):
        return "finalize"
    if options:
        return "menu"
    if "?" in text or re.search(r"informe|digite|qual", text, re.IGNORECASE):
        return "pergunta"
    return "informativo"


def new_exploration(*, insurer_key: str, ramo: str, test_data: Dict[str, str]) -> Dict[str, Any]:
    """test_data: {'cpf': ..., 'placa': ..., 'cep': ...} da apólice de teste."""
    return {
        "insurer_key": insurer_key, "ramo": ramo, "test_data": dict(test_data or {}),
        "state": "exploring",  # exploring | done | aborted
        "nodes": {}, "root": None,
        "frontier": [],           # [(node_id, label_ainda_nao_explorado)]
        "current_path": [],       # labels escolhidos até aqui (p/ replay do ramo)
        "visited_edges": set(),   # {(node_id, label)} — em runtime vira list p/ JSON
        "msg_count": 0, "last_node": None,
        "transcript": [], "started_at": datetime.now(timezone.utc).isoformat(),
    }


def _pick_abort_reply(options: List[str]) -> str:
    for pref in _ABORT_PREFERENCES:
        for lab in options:
            if pref.lower() in lab.lower():
                return lab
    return _ABORT_PREFERENCES[0]


def handle_insurer_message(exp: Dict[str, Any], text: str) -> Optional[str]:
    """Processa uma tela da URA e devolve a resposta do Cartógrafo (ou None p/
    silêncio). Aplica os freios e registra o nó no mapa em construção."""
    exp["msg_count"] = int(exp.get("msg_count") or 0) + 1
    exp.setdefault("transcript", []).append(
        {"direction": "in", "text": str(text)[:2000], "at": datetime.now(timezone.utc).isoformat()}
    )

    # Freio 3: orçamento de mensagens da sessão.
    if exp["msg_count"] > MAX_MESSAGES_PER_SESSION:
        exp["state"] = "aborted"
        exp["abort_reason"] = "max_messages"
        return None

    options = parse_options(text)
    kind = classify_screen(text, options)
    h = node_hash(text)
    node_id = h
    if node_id not in exp["nodes"]:
        exp["nodes"][node_id] = {
            "text": normalize_screen_text(text)[:400], "kind": kind,
            "options": [{"label": lab, "reply": lab, "leads_to": None} for lab in options],
            "hash": h,
        }
        if exp.get("root") is None:
            exp["root"] = node_id
    # Liga a aresta percorrida: o nó anterior levou até aqui.
    prev = exp.get("last_node")
    prev_reply = exp.get("last_reply")
    if prev and prev_reply and prev in exp["nodes"]:
        for opt in exp["nodes"][prev]["options"]:
            if opt["label"].lower() == str(prev_reply).lower():
                opt["leads_to"] = node_id
    exp["last_node"] = node_id

    reply = _decide_reply(exp, node_id, text, options, kind)
    if reply is not None:
        exp["last_reply"] = reply
        exp["transcript"].append(
            {"direction": "out", "text": reply, "at": datetime.now(timezone.utc).isoformat()}
        )
    return reply


def _decide_reply(exp: Dict[str, Any], node_id: str, text: str,
                  options: List[str], kind: str) -> Optional[str]:
    # FORMULÁRIO NATIVO (app dentro do WhatsApp — família HDI/Yelum): não aceita
    # texto; registra o nó como 'app_form' (o mapa marca a fronteira do que a
    # Evolution API alcança — atravessar exige Evolution GO) e encerra o ramo.
    if "FORMULARIO NATIVO" in text.upper():
        exp["nodes"][node_id]["kind"] = "app_form"
        exp["state"] = "done"
        return None

    # HUMANO entrou (freio novo 14/07): saída educada e fim DEFINITIVO da
    # exploração desta seguradora — nunca conversar usando nome de cliente.
    if entrou_humano(text):
        exp["nodes"][node_id]["kind"] = "humano"
        exp["human_engaged"] = True
        exp["state"] = "done"
        return POLITE_EXIT

    # Freio 1: confirmação final → SAIR, nunca confirmar. Marca e encerra o ramo.
    if kind == "finalize":
        exp["nodes"][node_id]["kind"] = "finalize"
        exp["state"] = "done" if not exp.get("frontier") else "exploring"
        return _pick_abort_reply(options)

    # Perguntas de dados: respondemos com a apólice de teste (freio 4 se faltar).
    for rx, slot in _DATA_REPLIES:
        if rx.search(text):
            value = str((exp.get("test_data") or {}).get(slot) or "").strip()
            if value:
                return value
            exp["nodes"][node_id]["kind"] = "needs_data"
            return _pick_abort_reply(options) if options else None

    if not options:
        # Pergunta que não sabemos responder e SEM opções para recuar → fim de
        # ramo (needs_data): o multi-pass reinicia em vez de ficar mudo p/ sempre
        # (fix 14/07 — stall ao vivo na Porto).
        if kind == "pergunta":
            exp["nodes"][node_id]["kind"] = "needs_data"
            exp["state"] = "done"
        return None  # informativo — a URA segue sozinha

    visited = exp.setdefault("visited_edges", set())
    if isinstance(visited, list):  # sessão restaurada de JSON
        visited = set(tuple(v) for v in visited)
        exp["visited_edges"] = visited

    # RE-IDENTIFICAÇÃO primeiro (fix 14/07): a URA lembra o cliente anterior do
    # número — trocar para o CPF de teste tem prioridade sobre a exploração.
    for lab in options:
        if _REIDENTIFY_RE.search(lab) and (node_id, lab) not in visited:
            visited.add((node_id, lab))
            exp.setdefault("current_path", []).append(lab)
            return lab

    for lab in options:
        # Freio 2: ramo de sinistro — registra que existe e NÃO entra.
        if _SINISTRO_RE.search(lab):
            visited.add((node_id, lab))
            continue
        if (node_id, lab) not in visited:
            visited.add((node_id, lab))
            exp.setdefault("current_path", []).append(lab)
            return lab

    # Nada inexplorado aqui → encerra o ramo educadamente.
    exp["state"] = "done"
    return _pick_abort_reply(options)


def has_unexplored(exp: Dict[str, Any]) -> bool:
    """Ainda existem opções seguras não percorridas? (Base do multi-pass: o
    founder exige TODAS as combinações, não só uma rota por sessão.)"""
    visited = exp.get("visited_edges") or set()
    if isinstance(visited, list):
        visited = set(tuple(v) for v in visited)
    for node_id, node in (exp.get("nodes") or {}).items():
        if node.get("kind") in ("finalize", "needs_data"):
            continue
        for opt in node.get("options") or []:
            lab = str(opt.get("label") or "")
            if _SINISTRO_RE.search(lab):
                continue
            if (node_id, lab) not in visited:
                return True
    return False


def exploration_to_map(exp: Dict[str, Any]) -> Dict[str, Any]:
    """Converte a exploração no formato canônico do ura_map_service."""
    return {"root": exp.get("root"), "nodes": exp.get("nodes") or {},
            "meta": {"insurer_key": exp.get("insurer_key"), "ramo": exp.get("ramo"),
                     "msg_count": exp.get("msg_count"),
                     "started_at": exp.get("started_at")}}
