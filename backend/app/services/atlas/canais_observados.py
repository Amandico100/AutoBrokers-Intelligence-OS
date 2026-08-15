"""Quem é a contraparte, quando ela NÃO é um cliente.

📊 O ACHADO — 15/08/2026, sobre 150.734 linhas de `attendance_transcripts`:
**`insurer_key` estava nulo em 100% delas.** O sistema capturava e não sabia o
que tinha capturado.

A consequência não era estética. `espelho_chat.deve_espelhar` recusa mensagem de
seguradora com `if e_grupo or e_seguradora: return False`, e `e_seguradora` vem
de `bool(linha.get("insurer_key"))`. Com a coluna nula, `bool(None)` é False em
TODAS as linhas: o portão existia, tinha teste, e nunca disparou uma vez.

📊 O preço, medido na mesa de trabalho das atendentes:
    Resulta  ... 10,9% do que ela vê é robô de seguradora  (714 mensagens)
    AutoFleet ..  6,8%                                      (652 mensagens)

A Saionara abre a mesa e encontra a fila de espera da MAPFRE, o menu da Maxpar e
a pesquisa de satisfação da Localiza no meio das pessoas que precisam dela.

POR QUE ESTE ARQUIVO EXISTE — e por que ele NÃO é um segundo registro
=====================================================================
`insurer_registry.py` é o catálogo de **assistência 24h**: um `whatsapp` por
seguradora, o número que a corretora liga para pedir guincho. É o que ele diz
que é, e continua sendo a autoridade disso.

📊 O que a Regina e a Saionara realmente usam é **outro conjunto de canais**:
atendimento ao corretor, sinistro, financeiro, carro reserva, vidros. Medido:
o MAPFRE registrado é `551140040101`; o que aparece 2.197 vezes no acervo é
`551140029000`. Números diferentes, propósitos diferentes, mesma companhia.

Por isso aqui não há telefone de assistência nenhum: este arquivo é o
**observado**, aquele é o **catalogado**. `insurer_allowlist()` lê os dois e
continua sendo o único resolvedor telefone→seguradora do produto (CLAUDE.md §5).

AS TRÊS REGRAS QUE O JUIZ IMPÔS — 15/08/2026
=============================================
**R1 · Prestadora NUNCA recebe `insurer_key`.** Não é opinião minha: já estava
decidido em `curadoria_cartas.py`, *"Prestadora atende VÁRIAS seguradoras. Em
`insurer_key` ela faria o filtro devolver a companhia errada"*. As linhas 18 e
19 provam sozinhas — a MESMA Localiza, com o MESMO roteiro, atende HDI e Tokio.
"15 diárias" é regra da Localiza, não da HDI. Arquivar sob a seguradora
duplicaria o mesmo fato e ficaria indefensável no dia em que uma terceira
seguradora contratasse a Localiza com prazo diferente.

**R2 · `natureza` responde "é cliente?"; `insurer_key` responde "de quem é?".**
São duas perguntas, e reusar uma coluna para as duas foi o defeito que produziu
a coluna nula. Tirar da mesa precisa só da primeira.

**R3 · Só entra o que se identificou em PRIMEIRA PESSOA.** O juiz reprovou
quatro classificações minhas por isso, e uma delas ensina mais que as outras
três: eu classifiquei `551130030319` como Suhai por causa de um LINK para
`i4pro.suhaiseguradora.com.br`. URL não identifica quem MANDOU — identifica o
dono do destino, e aquele link pode ter sido colado pela própria corretora.

⚠️ E o inverso também: eu havia rebaixado a Bradesco Assistência a "parceiro"
por causa do CARDÁPIO (encanador, chaveiro, caixa d'água), quando a mensagem diz
*"Eu sou a Assistente Virtual da Bradesco Seguros"* em primeira pessoa.
Encanador é LINHA DE SERVIÇO, não outra empresa. Julguei pelo conteúdo do menu
— exatamente o critério que eu tinha escrito que não se deve usar.

O QUE FICOU DE FORA, E FICA DITO EM VOZ ALTA
=============================================
Dez canais NÃO entraram por falta de prova em primeira pessoa: os dois da Suhai,
a Essor, a Porto, a Localiza sem dono, o `551126997171` (nomeia uma funilaria e
mais nada), o `558000483500` (UGF — não estabelece quem é), e três sem marca
nenhuma. **Silêncio não é confirmação.** Eles continuam como estão, e voltam
quando houver uma mensagem em que o remetente diga o próprio nome.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# As três naturezas que decidem o destino de uma conversa.
#
# `prestadora` é a que mais importa entender: ela NÃO é cliente (sai da mesa) e
# NÃO é a seguradora (não recebe `insurer_key`). É a Localiza, a Maxpar, a
# reguladora VIX — quem a seguradora contrata.
SEGURADORA = "seguradora"
PRESTADORA = "prestadora"
FORA_DO_DOMINIO = "fora_do_dominio"

NATUREZAS_QUE_NAO_SAO_CLIENTE = frozenset({SEGURADORA, PRESTADORA, FORA_DO_DOMINIO})

# Identificadores do WhatsApp. 📊 Nove dos 28 canais achados não são telefone:
# são `@lid`, o identificador opaco do WhatsApp — `numero_pareado.py:43` já
# registra que "dele não se deduz número". Tratar os dois como "dígitos" é o
# erro que faria `55701598638082` passar por número brasileiro: ele começa com
# 55 e engana qualquer parser ingênuo, mas 70 não é DDD.
TELEFONE = "phone"
LID = "lid"


def _c(kind: str, valor: str, natureza: str, evidencia: str,
       insurer_key: str = "", prestadora_key: str = "",
       insurer_contexto: str = "", proposito: str = "",
       company_id: str = "") -> Dict[str, Any]:
    return {"kind": kind, "valor": valor, "natureza": natureza,
            "evidencia": evidencia, "insurer_key": insurer_key,
            "prestadora_key": prestadora_key, "insurer_contexto": insurer_contexto,
            "proposito": proposito, "company_id": company_id}


# ⚠️ `company_id` vazio = GLOBAL (vale para toda corretora).
#
# 📊 A medição que autoriza isso: telefone real REPETE entre corretoras — o
# `551140029000` aparece 2.197 vezes, nas duas. Já os nove `@lid` aparecem, cada
# um, em UMA corretora só. Não é coincidência: `@lid` é opaco e não carrega
# significado entre tenants. Por isso todo `@lid` aqui é escopado, e nenhum
# telefone é.
#
# ⚠️ E a guarda que o juiz exigiu contra a AMANDUS: este catálogo é escrito à
# mão, com citação, e revisado. Ele NÃO aprende do acervo sozinho — se
# aprendesse, ingeriria os ensaios da corretora de teste como se fossem prova
# sobre seguradora real, e a env var que exclui a Amandus é do destilador e não
# cobriria isto.
CANAIS_OBSERVADOS: List[Dict[str, Any]] = [
    # ---------------------------------------------------------------- #
    # SEGURADORAS — a mensagem diz o próprio nome, em primeira pessoa.
    # ---------------------------------------------------------------- #
    _c(TELEFONE, "551140029000", SEGURADORA, insurer_key="mapfre",
       proposito="corretor",
       evidencia="'*Lembrete*: você também pode acessar o link abaixo no "
                 "*Portal MAPFRE Negócios*' · 2.197 msgs nas duas corretoras"),
    _c(TELEFONE, "5511916418784", SEGURADORA, insurer_key="youse",
       proposito="financeiro",
       evidencia="'A Youse agradece o contato' · boletos e Pix · 2.199 msgs"),
    _c(TELEFONE, "551134609000", SEGURADORA, insurer_key="sompo",
       proposito="corretor",
       evidencia="'Sou a assistente virtual da Sompo Seguros' · 69 msgs"),
    _c(TELEFONE, "551151862030", SEGURADORA, insurer_key="hdi",
       proposito="sinistro",
       evidencia="'Somos da HDI Seguros e estamos entrando em contato para "
                 "tratar sobre o seu processo de sinistro' · 43 msgs"),
    _c(TELEFONE, "558007247722", SEGURADORA, insurer_key="tokio",
       proposito="sinistro",
       evidencia="'TOKIO MARINE Informa Atendimento de número' · 55 msgs"),
    _c(TELEFONE, "551132061515", SEGURADORA, insurer_key="yelum",
       proposito="corretor",
       evidencia="'A Yelum permanece a sua disposição!' + 'este canal é de uso "
                 "exclusivo para Corretores' · 446 msgs · ⚠️ é um TERCEIRO "
                 "número da Yelum: o registro já tem 551131321001 e "
                 "551132061414"),

    # Os `@lid` — escopados por corretora, porque é o que a medição sustenta.
    _c(LID, "122089361150161", SEGURADORA, insurer_key="bradesco",
       proposito="sinistro", company_id="04b5cdbc-04cd-4ddf-8e4b-f43efb062fab",
       evidencia="'BRADESCO AUTO/RE informa: O sinistro 114202604151116 em "
                 "referência teve sua análise concluída' · 59 msgs"),
    _c(LID, "121311485501521", SEGURADORA, insurer_key="bradesco",
       proposito="corretor", company_id="04b5cdbc-04cd-4ddf-8e4b-f43efb062fab",
       evidencia="'Agradecemos por usar o WhatsApp Bradesco Seguros!' · 39 msgs"),
    # 🔴 Esta é a linha que eu havia REBAIXADO por engano, e o juiz devolveu.
    # Eu li o cardápio (encanador, chaveiro, limpeza de caixa d'água) e concluí
    # "parceiro de assistência". A mensagem diz, em primeira pessoa, que É a
    # Bradesco. Linha de serviço não é outra empresa.
    _c(LID, "29377626669274", SEGURADORA, insurer_key="bradesco",
       proposito="assistencia", company_id="04b5cdbc-04cd-4ddf-8e4b-f43efb062fab",
       evidencia="'Eu sou a Assistente Virtual da Bradesco Seguros!' + menu "
                 "'Encanador Eletricista Reparo equipamentos Chaveiro Limpeza' "
                 "· 67 msgs"),
    _c(LID, "61027827896494", SEGURADORA, insurer_key="axa",
       proposito="corretor", company_id="04b5cdbc-04cd-4ddf-8e4b-f43efb062fab",
       evidencia="'A Central AXA Seguros agradece o seu contato' · 71 msgs"),
    _c(LID, "167624000442568", SEGURADORA, insurer_key="metlife",
       proposito="sinistro", company_id="04b5cdbc-04cd-4ddf-8e4b-f43efb062fab",
       evidencia="'Muito obrigado por confiar na MetLife' · 7 msgs"),

    # ---------------------------------------------------------------- #
    # PRESTADORAS — não é cliente, e NÃO é a seguradora (R1).
    # ---------------------------------------------------------------- #
    # 🔴 `maxpar` já tem chave canônica no produto, e ela é `autoglass`
    # (`curadoria_cartas._PRESTADORAS`). Inventar `maxpar_vidros`, como eu havia
    # proposto, seria um segundo nome para coisa já nomeada.
    _c(TELEFONE, "552733204114", PRESTADORA, prestadora_key="autoglass",
       proposito="vidros",
       evidencia="'Bem-vindo ao atendimento virtual da *Maxpar*, parceira das "
                 "seguradoras no atendimento aos segurados' — o PLURAL é a "
                 "prova de que não é canal de nenhuma · 1.516 msgs"),
    _c(TELEFONE, "553198987950", PRESTADORA, prestadora_key="localiza",
       insurer_contexto="hdi", proposito="carro_reserva",
       evidencia="'aqui é da Localiza, parceira da *HDI*!' · 101 msgs"),
    _c(LID, "55701598638082", PRESTADORA, prestadora_key="localiza",
       insurer_contexto="tokio", proposito="carro_reserva",
       company_id="04b5cdbc-04cd-4ddf-8e4b-f43efb062fab",
       evidencia="'eu sou a Assistente Virtual da Localiza, parceira da *Tokio "
                 "Marine*!' · 47 msgs · ⚠️ começa com 55 e NÃO é telefone: 70 "
                 "não é DDD"),
    _c(TELEFONE, "552740424371", PRESTADORA, prestadora_key="vix",
       insurer_contexto="allianz", proposito="sinistro",
       evidencia="'sou da reguladora VIX, e, a partir de agora, estou "
                 "encarregado da regulação do aviso Nº 300689226, aberto na "
                 "Allianz Seguros' · 98 msgs"),

    # ---------------------------------------------------------------- #
    # FORA DO DOMÍNIO — não é cliente, não é seguro, não é do produto.
    # ---------------------------------------------------------------- #
    # A armadilha central: nem tudo que manda botão é seguradora. Sem esta
    # seção, o RAG do produto aprenderia prazo de troca de eletrodoméstico e
    # agendamento de consulta como se fossem conhecimento de seguros.
    _c(LID, "133912835686649", FORA_DO_DOMINIO,
       company_id="04b5cdbc-04cd-4ddf-8e4b-f43efb062fab",
       evidencia="'Bem-vindo (a) ao atendimento da Casas Bahia!' — varejo"),
    _c(LID, "241506195623943", FORA_DO_DOMINIO,
       company_id="04b5cdbc-04cd-4ddf-8e4b-f43efb062fab",
       evidencia="'Sou a assistente virtual da *Clínica Palhoça*' — clínica"),
]


# 📊 Os que ficaram FORA, e por quê. Não é lista morta: é o que volta a ser
# olhado quando aparecer prova. `SEM_EVIDENCIA` existe para que "não sabemos"
# seja uma resposta escrita, e não um silêncio que alguém confunde com "não é".
SEM_EVIDENCIA: Dict[str, str] = {
    "551130030319": "link i4pro.suhaiseguradora.com.br — URL identifica o dono "
                    "do DESTINO, não quem mandou; pode ter sido colado pela corretora",
    "551130030335": "'Tenho seguro Suhai' é rótulo de botão na voz do CLIENTE — "
                    "nomeia o produto, não o remetente",
    "81364246388844": "'Selecione a opção Cadastrar na Essor' é copy instrucional, "
                      "o que um intermediário diz SOBRE a Essor; nada em 1ª pessoa",
    "553171508212": "'Sou cliente Porto e quero solicitar um carro reserva Localiza' "
                    "— a Porto não escreveria 'Localiza' para o próprio cliente; "
                    "tem cara de parceiro desambiguando o principal",
    "553196158666": "'a Localiza poderá ofertar' está em TERCEIRA pessoa — é o que "
                    "a seguradora diz sobre a Localiza, não a Localiza falando",
    "551126997171": "nomeia 'loja MEGA MARTELINHO' e um número de atendimento, e "
                    "mais nada — funilaria, sem identidade do remetente",
    "558000483500": "'plano UGF', 'perícia médica' — não estabelece QUEM é UGF",
    "5511975669867": "atendentes humanos nomeados falando de apólice e boleto, "
                     "sem marca nenhuma · ⚠️ perfil de CORRETORA, não de "
                     "seguradora — se for a segunda linha de um tenant, marcar "
                     "esconderia conversa de cliente de verdade",
    "551131959334": "só um link encurtado e 'Preciso da placa'. Não resolver o "
                    "encurtador: pode carregar token por destinatário",
    "551138485096": "pesquisa de satisfação pós-acionamento — é seguro, mas de "
                    "quem? E mesmo resolvido cairia em prestadora de NPS",
    "0": "não é remetente: é o próprio WhatsApp Business mandando dica de "
         "marketing. Some na EXTRAÇÃO, não na classificação",
}


def _indice() -> Dict[str, Dict[str, Any]]:
    """`{(kind:valor:escopo): canal}` — montado uma vez, lido muitas."""
    global _CACHE
    if _CACHE is None:
        _CACHE = {f"{c['kind']}:{c['valor']}:{c['company_id']}": c
                  for c in CANAIS_OBSERVADOS}
    return _CACHE


_CACHE: Optional[Dict[str, Dict[str, Any]]] = None


def canal_observado(valor: str, company_id: str = "") -> Optional[Dict[str, Any]]:
    """O canal, se este identificador for um dos observados.

    Procura primeiro o GLOBAL e depois o escopado nesta corretora. Nunca lê o
    escopo de outra: um `@lid` que a Resulta viu não diz nada sobre a AutoFleet,
    e responder com ele seria dado de um tenant vazando no outro (CLAUDE.md §7).
    """
    bruto = str(valor or "").strip()
    if not bruto:
        return None
    idx = _indice()
    empresa = str(company_id or "").strip()
    for kind in (TELEFONE, LID):
        achado = idx.get(f"{kind}:{bruto}:")
        if achado:
            return achado
        if empresa:
            achado = idx.get(f"{kind}:{bruto}:{empresa}")
            if achado:
                return achado
    return None


def natureza_da_contraparte(valor: str, company_id: str = "") -> Optional[str]:
    """`seguradora` · `prestadora` · `fora_do_dominio` — ou None se for gente.

    ⚠️ None significa DUAS coisas diferentes e é assim de propósito: "é uma
    pessoa" e "ainda não sabemos". Quem chama trata as duas igual — na dúvida, a
    conversa fica na mesa da atendente. Errar para o lado de mostrar uma
    conversa a mais é barato; esconder um cliente não é.
    """
    canal = canal_observado(valor, company_id)
    return canal["natureza"] if canal else None


def seguradora_observada(valor: str, company_id: str = "") -> Optional[str]:
    """A `insurer_key`, e SÓ quando a contraparte É a companhia (R1).

    Prestadora devolve None de propósito. A Localiza atende HDI e Tokio com o
    mesmo roteiro: gravar `hdi` faria a regra da Localiza virar regra da HDI.
    """
    canal = canal_observado(valor, company_id)
    if not canal or canal["natureza"] != SEGURADORA:
        return None
    return canal["insurer_key"] or None


__all__ = [
    "CANAIS_OBSERVADOS", "SEM_EVIDENCIA", "SEGURADORA", "PRESTADORA",
    "FORA_DO_DOMINIO", "NATUREZAS_QUE_NAO_SAO_CLIENTE", "TELEFONE", "LID",
    "canal_observado", "natureza_da_contraparte", "seguradora_observada",
]
