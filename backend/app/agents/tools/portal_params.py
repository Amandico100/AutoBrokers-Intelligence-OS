"""SPEC-020 P3 + SPEC-025 — logica PURA da tool portal_action (sem langchain, testavel).

SPEC-025: os FATOS (placa, veiculo, chassi, endereco, seguradora) vem da InfoCap
(server-side, endpoint /itens + /cliente_cpf) — o LLM NUNCA fornece nem inventa
placa/local. O LLM so decide o que e julgamento: qual apolice (se varias), o dano
(peca/como/onde/descricao) e a data. normalize_insurer traduz o nome legado da
InfoCap para a marca que o portal usa (Liberty -> Yelum).

BLOCO 7.5 — A CONFERENCIA ACONTECE ANTES DE O PORTAL ABRIR.
📊 39 acionamentos, 33 paradas em `needs_human`, zero protocolos: o sistema abria
o portal e SO ENTAO descobria o que nao sabia. Agora `build_portal_params` so
devolve params quando nada do que o portal vai perguntar esta em aberto — e
quando falta, devolve a PERGUNTA pronta, em portugues de gente, para o agente
fazer ao segurado. O catalogo do que o portal pergunta mora num lugar so:
`app/services/perguntas_do_portal_de_vidros.py`.
"""
from __future__ import annotations

import unicodedata
from typing import Optional, Tuple

from app.services.perguntas_do_portal_de_vidros import (
    DESTINO_PREFERENCIA,
    DO_SEGURADO,
    ONDE_REALIZAR_O_SERVICO,
    ONDE_REALIZAR_PADRAO,
    PREFERENCIA_AGENDA,
    PREFERENCIA_VISTORIA,
    catalogo_de_familias,
    compor_descricao,
    mensagem_para_o_agente,
    o_que_falta,
    para_o_segurado,
    pergunta_do_campo,
)

# O QUE O AGENTE CONSEGUE DEVOLVER HOJE — e por que isso limita o que trava.
#
# Bloquear numa pergunta cuja resposta nao tem como chegar de volta cria o laco
# infinito que este repo ja pagou uma vez: o agente pergunta, o segurado
# responde, o schema da tool descarta a resposta, e a MESMA pergunta volta para
# sempre (era o defeito do `subservico_invalido` em `insurer_dispatch_tool`,
# provado em `test_o_acionamento_nao_pede_o_impossivel.py`).
#
# Estes cinco sao os campos de `PortalActionInput` que carregam resposta de
# pergunta. As especificas do 80% (pelicula, lado, trincado) NAO estao aqui
# porque a tool ainda nao tem campo para elas: elas continuam sendo COLETADAS
# (entram na mensagem que o agente le) e o transporte daqui para baixo ja existe
# — `params['especificos']` e lido por `vidros_lanternas.abrir_atendimento` e
# entregue ao cerebro adaptativo. Falta so um campo `especificos` na tool.
TRANSPORTAVEIS = ("cpf_cnpj", "data_dano", "peca", "como_ocorreu", "onde_ocorreu",
                  # 🔴 SPEC-EXTRA-001.10.1 (D-E001101-05) — AQUI MORAVA
                  # `onde_realizar_o_servico` (domicílio × loja), e ele TRAVAVA.
                  # O Founder tirou o domicílio do produto: o robô não pergunta
                  # e não oferece. `build_portal_params` manda "loja" sempre —
                  # travar numa pergunta que ninguém mais faz seria o laço do
                  # `subservico_invalido` de novo.
                  # 🔴 SPEC-EXTRA-001.10 P0-5 — A CIDADE DO SERVIÇO TRAVA.
                  #
                  # 📊 `CodigoCidade` é chave obrigatória do PATCH nas 4
                  # capturas de 20/09/2026, e a cidade é perguntada em 8 de 8
                  # blocos do roteiro da atendente humana. Sem ela o robô entra
                  # no portal e para numa tela que ninguém consegue responder
                  # por ele — o CEP da apólice é o de CASA, e quem quebra o
                  # vidro viajando conserta onde está.
                  "cidade_para_o_servico",
                  # 🔴 N-2 (D-E00110-02) — só existe para para-brisa, e por
                  # isso não precisa de exceção aqui: a pergunta só nasce na
                  # família do para-brisa (`_ESPECIFICAS_POR_IDENTIDADE`), e o
                  # que não nasce não trava. 📊 Sem ela a journey para DEPOIS de
                  # o número do atendimento existir.
                  "aceita_reparo",
                  # 🔴 P1-5 — na lataria o `CodigoAtendimento` nasce logo após
                  # o PATCH, e é o PATCH que leva `ServicosMartelinhoLataria`.
                  # Perguntar a lista de peças depois é conversar sobre um
                  # pedido que já nasceu. Mesma regra: só a família lataria a faz.
                  "pecas_lataria")

# ⚠️ ESTA É A VERDADE ÚNICA, e a `description` da tool é GERADA dela.
#
# 📊 Até 20/09/2026 três lugares discordavam: o prompt mandava chamar com 3
# coisas (`prompts.py:136`), `TRANSPORTAVEIS` recusava por 6, e a `description`
# listava tudo à mão. O modelo lia o prompt — o mais errado dos três — e
# recebia de volta um pedido do que o prompt dissera que não precisava.
#
# Venceu a lista que é CÓDIGO EXECUTADO. O prompt aponta para a ferramenta, e a
# ferramenta se descreve a partir daqui. Só há uma forma de as três voltarem a
# divergir: alguém reescrever o texto à mão — e o guarda de FORMA reprova isso.


def trava_o_pedido(pergunta) -> bool:
    """A falta DESTA resposta faz o pedido parar DEPOIS da fronteira A?

    🔴 A regra mudou em 20/09/2026, e a razão é a mais cara do produto: **não
    existe journey de continuação.** O `token_autorizacao` do portal vive só em
    memória e `EstadoDoAtendimento.safe_to_retry_open` é `False` depois do
    `POST /atendimentos` — então toda parada dali em diante termina em mão
    humana, dentro do portal, com o protocolo já emitido. Coletar antes não é
    capricho: é a diferença entre o robô finalizar e o robô abrir pendência.

    Duas portas, e as duas são medidas, não opinadas:

        1. o campo é de topo e o schema da tool o carrega  → `TRANSPORTAVEIS`
        2. a pergunta é ESPECÍFICA e está **confirmada**   → o portal a fez numa
           tela REAL que nós capturamos, e a resposta viaja em `especificos`
           (o campo existe em `PortalActionInput` desde a fatia C)

    ⚠️ `confirmada=False` continua NÃO travando, e isso é deliberado: são as
    perguntas que nenhuma captura viu (sensor de chuva, degradê, capa fosca).
    Elas são coletadas e vão junto; cobrá-las seria o agente exigir do segurado
    uma resposta que o portal talvez nem peça.

    📊 O efeito, por família: para-brisa passa a travar em posição do trincado,
    tamanho, sensor de direção/faixa e aceita-reparo — **exatamente as 3
    perguntas que o portal fez na captura, mais a do reparo**. Vidro lateral
    trava em película, dianteira/traseira e lado — **exatamente as 3 da
    captura**. Lanterna e farol travam no lado. Lataria, na lista de peças.
    Vigia não trava em nada, porque nenhuma captura mostrou o questionário dela.
    """
    # 🔴 SPEC-EXTRA-001.10.1 — a PREFERÊNCIA nunca trava, e a regra vem antes
    # de tudo: faltar "a partir de que dia" custa uma continuação (o portal
    # mostra a agenda e o robô continua quando o segurado escolher), nunca o
    # atendimento. Uma preferência que travasse recusaria quem diz "não sei".
    if getattr(pergunta, "destino", "") == DESTINO_PREFERENCIA:
        return False
    if getattr(pergunta, "campo", "") in TRANSPORTAVEIS:
        return True
    return bool(getattr(pergunta, "confirmada", False))


def _fold(s: Optional[str]) -> str:
    """ASCII-fold para o que sera DIGITADO no portal (cidade/endereco): o teste
    validado digitou 'Florianopolis' sem acento — formato comprovado no autocomplete."""
    return unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().strip()

# ===========================================================================
# A SEGURADORA TEM UMA TABELA SÓ — SPEC-EXTRA-001.10 P0-4 / P-E00110-C-02
# ===========================================================================
# 🔴 Aqui morava `_INSURER_ALIASES`, uma segunda tabela de sinônimos. Ela e a
# de `portal_worker.journeys.vidros_api` respondiam perguntas diferentes sobre
# a mesma coisa — uma dava o NOME DE TELA, a outra o SLUG da API — e por isso
# pareciam poder conviver. Não podiam: a primeira seguradora nova entraria numa
# e não na outra, e o sintoma seria um pedido aberto na seguradora errada.
#
# Hoje a tabela é UMA, e ela carrega as três coisas:
# `(fragmento, slug, nome_de_tela)`. Esta função lê o `nome_de_tela`; a journey
# lê o `slug`; ninguém lê uma cópia.
#
# ⚠️ Import TARDIO e tolerante: `portal_worker` viaja na imagem do smith-api
# (📊 `backend/Dockerfile:11 COPY . .`), mas um `ImportError` no topo tiraria a
# tool inteira do ar por causa de uma tabela de sinônimos. Sem ela, o nome vai
# como o corretor escreveu (`.title()`), que é o mesmo desfecho de uma
# seguradora desconhecida — e o preflight recusa antes de qualquer escrita.
def _apelidos_do_portal() -> Tuple[Tuple[str, str], ...]:
    """`(fragmento, nome_de_tela)` — a leitura de tela da tabela única."""
    try:
        from portal_worker.journeys.vidros_api import apelidos_de_seguradora

        return tuple((str(frag).upper(), str(tela))
                     for frag, _slug, tela in apelidos_de_seguradora())
    except Exception:  # noqa: BLE001
        return ()


def normalize_insurer(name: Optional[str]) -> str:
    """Nome da seguradora como o PORTAL a conhece. Fonte: seguradora da InfoCap.

    🔴 O casamento e por PALAVRA INTEIRA e sem acento, e quem o faz e a tabela
    unica (`vidros_api.casar_apelido`). 📊 Tres defeitos medidos pelo red team
    em 20/09/2026 morrem ai: `ITAU` nao casava com `ITAU` acentuado (e o DOM
    passava a digitar a razao social crua), `ZURICH SANTANDER` virava
    `Santander Auto`, e `BANCO`/`SEG` casavam por pedaco de palavra.
    """
    raw = str(name or "").strip()
    if not raw:
        return ""
    try:
        from portal_worker.journeys.vidros_api import nome_de_tela_do_apelido

        tela = nome_de_tela_do_apelido(raw)
    except Exception:  # noqa: BLE001
        tela = ""
    return tela or raw.title()


# ===========================================================================
# A CIDADE DO SERVIÇO — texto de gente virando {uf, cidade}
# ===========================================================================
# 📊 O segurado escreve "Joinville/SC", "Joinville - SC", "joinville sc" ou só
# "Joinville". Os quatro são a mesma cidade, e nenhum deles é um `CodigoCidade`:
# quem resolve o código é a journey, por `GET /ufs` → `GET /cidades?UF=`.
#
# ⚠️ Quando o texto não traz o estado, o padrão é o da APÓLICE — e isso fica
# DECLARADO em `local.cidade_servico_uf_de`, nunca silencioso. Um estado
# assumido em silêncio manda o pedido para a cidade homônima de outro estado, e
# "Campinas/SP" × "Campinas/RJ" não se desfaz depois de o pedido nascer.
_UFS = ("AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS",
        "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC",
        "SE", "SP", "TO")


def cidade_e_uf_do_servico(texto: Optional[str],
                           uf_da_apolice: Optional[str] = None) -> Tuple[str, str, str]:
    """(cidade, uf, de_onde_veio_a_uf). Tudo "" quando o texto não diz cidade.

    `de_onde_veio_a_uf` é "segurado" quando ele escreveu o estado e "apolice"
    quando caiu no padrão — a distinção existe para que a journey e o dossiê
    saibam o que foi ASSUMIDO.
    """
    bruto = _fold(texto)
    # Separadores que a gente usa na vida: "/", "-", vírgula e o próprio espaço.
    pedacos = [p.strip() for p in "".join(
        " " if c in "/,-–—|" else c for c in bruto).split() if p.strip()]
    if not pedacos:
        return "", "", ""

    uf = ""
    origem = ""
    if len(pedacos) > 1 and pedacos[-1].upper() in _UFS:
        uf, origem = pedacos[-1].upper(), "segurado"
        pedacos = pedacos[:-1]
    if not uf:
        padrao = _fold(uf_da_apolice).upper()
        if padrao in _UFS:
            uf, origem = padrao, "apolice"

    # "rio de janeiro" → "Rio de Janeiro", não "Rio De Janeiro": o autocomplete
    # do portal casa por texto, e a preposição maiúscula é ruído gratuito.
    palavras = [p.title() for p in pedacos]
    palavras = [palavras[0]] + [
        (p.lower() if p.lower() in _LIGACOES else p) for p in palavras[1:]]
    cidade = " ".join(palavras)
    if not cidade:
        return "", "", ""
    return cidade, uf, origem


def descricao_da_tool() -> str:
    """A `description` de `portal_action`, GERADA de `TRANSPORTAVEIS` + as famílias.

    🔴 P0-5, a reconciliação das três verdades. Enquanto este texto era escrito
    à mão, ele era a terceira opinião sobre o que o portal pede — e a que o
    modelo lia junto com o prompt. Agora ele é uma PROJEÇÃO da lista que
    realmente recusa o payload: acrescentar um campo a `TRANSPORTAVEIS` muda a
    descrição no mesmo commit, sem ninguém lembrar de nada.

    ⚠️ O que continua escrito à mão são as PROIBIÇÕES e o comportamento da
    ferramenta — eles não derivam de campo nenhum e não podem sumir numa
    geração automática.
    """
    trava = []
    for campo in TRANSPORTAVEIS:
        p = pergunta_do_campo(campo)
        if p is None or p.de_quem != DO_SEGURADO:
            continue
        trava.append(f"{campo} ({p.texto.split('?')[0].strip()[:90]}…)")
    familias = ", ".join(sorted(catalogo_de_familias()))
    return (
        "Abre o atendimento de VIDROS/farois/lanternas/retrovisores/para-choque/lataria "
        "no portal da seguradora. "
        "NAO decore a lista do que coletar: CHAME a ferramenta com o que voce ja tem e "
        "ela devolve, em portugues, EXATAMENTE a proxima pergunta que falta — uma por "
        "vez, para voce fazer ao segurado e chamar de novo. "
        "O que trava o pedido hoje, e que ela vai cobrar: "
        + "; ".join(trava) + ". "
        "Ha perguntas ESPECIFICAS por familia de peca (" + familias + "), e sao elas "
        "que decidem QUAL peca do catalogo da apolice sera pedida — a ferramenta diz "
        "quais quando souber a peca. Mande-as em `especificos`. "
        # 🔴 SPEC-EXTRA-001.10.1 — COMPORTAMENTO, não campo: por isso escrito à mão.
        "Quando o pedido JA foi aberto e parou esperando o segurado (loja, dia e "
        "horario da agenda, ou outra resposta), chame de novo com os MESMOS dados e a "
        "resposta em `especificos`: a ferramenta CONTINUA o mesmo pedido na seguradora "
        "— nunca abre outro — e diz exatamente como mandar a resposta. "
        "A ferramenta busca SOZINHA os dados reais da apolice (placa, veiculo, endereco, "
        "seguradora) no sistema da corretora — NAO peca placa/CEP/endereco ao cliente e NUNCA os "
        "invente. Se houver mais de uma apolice AUTO ativa, ela devolve as opcoes para "
        "voce perguntar qual. Ela avisa o cliente que esta abrindo e volta com o "
        "resultado. So diga que o servico esta AGENDADO quando ela devolver o "
        "agendamento CONFIRMADO pela seguradora."
    )


def _lista_de_pecas(bruto) -> list:
    """As peças amassadas como LISTA, venha como vier.

    O modelo às vezes devolve `["porta", "paralama"]` e às vezes
    `"porta e paralama"` — as duas são a mesma resposta do segurado. Aceitar só
    uma forma faria metade das respostas sumirem no transporte, que é o defeito
    que `TRANSPORTAVEIS` existe para não repetir.
    """
    if isinstance(bruto, (list, tuple, set)):
        itens = [str(x).strip() for x in bruto]
    else:
        texto = str(bruto or "")
        for sep in (";", " e ", ","):
            texto = texto.replace(sep, ",")
        itens = [p.strip() for p in texto.split(",")]
    return [p for p in itens if p and p.lower() not in ("none", "null")]



# ===========================================================================
# 🔴 RIGOR ANTES DA FRONTEIRA A — onde parar e de graca
# ===========================================================================
# O principio que o conserto de 20/09/2026 fixou, depois de juiz e red team:
#
#     ANTES da fronteira A   parar custa UMA PERGUNTA. O job nem nasce, o agente
#                            pergunta de novo, e ninguem no mundo soube de nada.
#     DEPOIS dela            parar custa O ATENDIMENTO: o pedido existe na
#                            seguradora, nao ha journey de continuacao, e quem
#                            termina e uma pessoa, no portal.
#
# Por isso toda classificacao de texto de gente mora AQUI, e o que atravessa a
# fronteira e sempre um ENUM ou uma IGUALDADE. 📊 O preco de nao fazer assim
# foi medido: "quebra acidental" virava QUEBRA INTENCIONAL (a seguradora nega
# sinistro), "na garagem de casa" virava Rodoviario, e "Curitiba" virava
# CURITIBANOS/SC.

_SIM_NO_REPARO = ("sim", "aceito", "aceita", "quero", "quero o reparo", "pode ser",
                  "pode reparar", "topo", "vamos", "ok", "claro", "isso",
                  "prefiro reparar", "quero reparar", "sim aceito", "s")
_NAO_NO_REPARO = ("nao", "nao quero", "prefiro trocar", "quero trocar", "trocar",
                  "troca", "nao aceito", "recuso", "melhor trocar", "n")

_URBANO = ("urbano", "cidade", "rua", "avenida", "bairro", "centro",
           "estacionamento", "garagem", "condominio", "shopping", "casa",
           "trabalho", "semaforo", "vila", "praca", "urbana")
# 🔴 SIGLA DE UF NAO E RODOVIA. 📊 "em Santos SP" era classificado como
# rodoviario porque `sp` estava nesta lista. Rodovia com sigla so conta quando
# vem com NUMERO (`SP-280`, `BR 101`) — e isso e um padrao, nao uma palavra.
_RODOVIARIO = ("rodoviario", "rodovia", "estrada", "freeway",
               "autoestrada", "viagem", "viajando", "pista", "marginal",
               "anel", "rodoviaria")
_RE_RODOVIA_NUMERADA = __import__("re").compile(
    r"\b(?:br|sp|rs|pr|sc|mg|rj|ba|go|pe|ce|ms|mt|pa|ma|pb|pi|rn|se|al|es|to|ro|rr|ac|am|ap|df)"
    r"\s*[-\u2013]?\s*\d{2,3}\b", __import__("re").I)


def _palavras_soltas(texto):
    """As palavras inteiras do texto, sem acento e sem pontuacao."""
    cru = _fold(str(texto or "")).lower()
    return [w for w in "".join(c if c.isalnum() else " " for c in cru).split() if w]


def normalizar_perimetro(texto):
    """Texto de gente -> `"urbano"` | `"rodoviario"` | `""` (nao deu para saber).

    🔴 Por PALAVRA INTEIRA, e o motivo esta medido: a versao por substring
    (`"br " in texto`) respondia **Rodoviario** para *"o vidro quebrou na
    garagem de casa"* — `br` dentro de `queBRou` — e **Urbano** para
    *"casado"*. O portal aceita os dois valores calado, e o analista le o
    errado.

    `""` faz o acionamento PARAR ANTES de abrir, que custa uma pergunta.
    """
    palavras = set(_palavras_soltas(texto))
    if not palavras:
        return ""
    tem_r = bool(palavras & set(_RODOVIARIO)) or bool(
        _RE_RODOVIA_NUMERADA.search(_fold(str(texto or ""))))
    tem_u = bool(palavras & set(_URBANO))
    if tem_r and not tem_u:
        return "rodoviario"
    if tem_u and not tem_r:
        return "urbano"
    return ""


def normalizar_aceita_reparo(texto):
    """Texto de gente -> `"sim"` | `"nao"` | `""`.

    A journey so ve `sim`/`nao`: ela nao interpreta frase nenhuma depois da
    fronteira. 📊 O red team mediu `"pode ser"`, `"quero o reparo"` e
    `"quero trocar"` chegando crus a journey, onde viravam "nao decidiu" e
    paravam o pedido ja aberto.
    """
    limpo = " ".join(_palavras_soltas(texto))
    if not limpo:
        return ""
    # 🔴 "nao sei" NAO e "nao quero". A primeira versao respondia `nao` para
    # quem disse que nao sabe — e ai o segurado perde o reparo (que costuma sair
    # sem franquia) por uma palavra que ele nem usou nesse sentido.
    if limpo in ("nao sei", "sei la", "nao faco ideia", "talvez", "nao lembro",
                 "nao sabe", "tanto faz", "voce decide", "o que for melhor"):
        return ""
    if limpo in _SIM_NO_REPARO or limpo in _NAO_NO_REPARO:
        return "sim" if limpo in _SIM_NO_REPARO else "nao"
    palavras = set(limpo.split())
    nega = bool(palavras & {"nao", "prefiro", "recuso"})
    troca = bool(palavras & {"trocar", "troca", "trocado"})
    repara = bool(palavras & {"reparo", "reparar", "conserto", "consertar"})
    if nega and not repara:
        return "nao"
    if troca and not repara:
        return "nao"
    if nega and repara:
        return "nao"
    if repara or palavras & {"sim", "aceito", "quero", "pode", "topo", "ok", "claro"}:
        return "sim"
    return ""


# ===========================================================================
# 🔴 SPEC-EXTRA-001.10.1 C2 — AS PREFERÊNCIAS viram ENUM antes da fronteira
# ===========================================================================
# Mesma regra do reparo e do perímetro: a journey não interpreta frase nenhuma
# depois do número. O que atravessa é `{"a_partir_de": "DD/MM/AAAA", "periodo":
# "manha"|"tarde"|"qualquer"}` e `"link"|"loja"`. Resposta que não vira enum NÃO
# vai — e isso não trava nada: sem preferência, o portal mostra a agenda e o
# robô continua quando o segurado escolher (contrato A↔C, SPEC §5).

_DIAS_DA_SEMANA = {"segunda": 0, "terca": 1, "quarta": 2, "quinta": 3,
                   "sexta": 4, "sabado": 5, "domingo": 6}
_MANHA = {"manha", "cedo", "cedinho", "manhazinha", "matutino"}
_TARDE = {"tarde", "tardinha", "vespertino"}
_TANTO_FAZ = ("tanto faz", "qualquer", "qualquer um", "qualquer horario",
              "qualquer periodo", "qualquer hora", "o que tiver", "pode ser qualquer",
              "o mais cedo possivel", "o quanto antes", "o mais rapido possivel")


def _hoje_no_brasil():
    """A data de HOJE no fuso do segurado. ⚠️ O servidor roda em UTC: às 22h de
    Brasília já é amanhã em UTC, e "hoje" viraria o dia seguinte."""
    from datetime import datetime, timedelta, timezone

    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo("America/Sao_Paulo")).date()
    except Exception:  # noqa: BLE001 — sem tzdata (Windows), o offset fixo basta
        return datetime.now(timezone(timedelta(hours=-3))).date()


#: Marca de "o segurado disse uma data que não existe" (31/02) — diferente de
#: `None` ("não disse data nenhuma").
_DATA_INEXISTENTE = "data_inexistente"

#: 🔴 RED B1 (conserto da 001.10.1) — frase sobre a LOJA, não sobre o dia:
#: "quero a segunda loja", "a mais perto". "segunda" ali é ordinal, nunca
#: segunda-feira; a preferência não vai, e a lista é mostrada.
_FALA_DA_LOJA = {"loja", "lojas", "perto", "pertinho", "longe", "oficina"}


def _hora_dita(bruto: str, palavras: list):
    """`(horario "HH:MM" | "", relativa: bool, ilegivel: bool)` — a HORA que o
    segurado disse, quando ele disse uma.

    🔴 RED B1 (conserto da 001.10.1): "4 da tarde", "16h", "às 9", "15:30" são
    um HORÁRIO, não um período. Antes esta função não existia e a hora se
    perdia: o motor marcava o 1º bloco da tarde (13:00) para quem pediu 16:00.

    `relativa` = "depois das 15h", "antes das 10", "a partir das 14h", "até as
    11": não é um horário, é um limite — e agendar o limite é adivinhar. Quem
    chama devolve `{}` (a lista é mostrada).
    """
    import re as _re

    t = bruto
    if _re.search(r"\b(depois|apos|antes|ate|partir)\s+(d[aoe]s?\s+|as\s+)?(\d{1,2})\s*"
                  r"(h|hs|hrs|horas?|:\d{2})?\b(?!\s*/)", t) and \
            not _re.search(r"\b(depois|apos|antes|ate|partir)\s+d[aoe]s?\s+dia\b", t):
        return "", True, False
    h = mi = None
    m = _re.search(r"\b(\d{1,2}):(\d{2})\b", t)
    if m:
        h, mi = int(m.group(1)), int(m.group(2))
    if h is None:
        m = _re.search(r"\b(\d{1,2})\s*(?:h|hs|hrs|horas?)\s*(\d{2})?\b", t)
        if m:
            h, mi = int(m.group(1)), int(m.group(2) or 0)
    if h is None:
        m = _re.search(r"(?<!dia )\b(\d{1,2})\s+da\s+(manha|tarde|noite)\b", t)
        if m:
            h, mi = int(m.group(1)), 0
    if h is None:
        m = _re.search(r"\bas\s+(\d{1,2})\b(?!\s*/)", t)
        if m:
            h, mi = int(m.group(1)), 0
    if h is None and _re.search(r"\bmeio\s*-?\s*dia\b", t):
        h, mi = 12, 0
    if h is None:
        return "", False, False
    # "4 da tarde" / "de tarde, umas 4 horas" / "8 da noite": o período DITO
    # desfaz a ambiguidade das 12 horas. Sem período dito, a hora vai como foi
    # dita ("às 4" = 04:00, que nenhuma loja publica — a lista é mostrada).
    if h < 12 and ({"tarde", "tardinha", "noite"} & set(palavras)):
        h += 12
    if h > 23 or mi > 59:
        return "", False, True
    return f"{h:02d}:{mi:02d}", False, False


def _data_dita(palavras: list, bruto: str, hoje):
    """A data que o segurado disse, ou None. Só o que tem UMA leitura.
    `_DATA_INEXISTENTE` quando ele disse uma data que não existe (31/02)."""
    import re as _re
    from datetime import date, timedelta

    texto = " ".join(palavras)
    if "depois de amanha" in texto:
        return hoje + timedelta(days=2)
    if "amanha" in palavras:
        return hoje + timedelta(days=1)
    if "hoje" in palavras:
        return hoje
    m = _re.search(r"\b(\d{1,2})\s*/\s*(\d{1,2})(?:\s*/\s*(\d{2,4}))?\b", bruto)
    if m:
        d, mes = int(m.group(1)), int(m.group(2))
        ano = int(m.group(3)) if m.group(3) else hoje.year
        if ano < 100:
            ano += 2000
        try:
            alvo = date(ano, mes, d)
        except ValueError:
            # 🔴 RED P2/P3 (conserto da 001.10.1): "31/02" é uma data DITA e
            # que não existe — não é "não disse data". Sem esta marca, a frase
            # "31/02 de manhã" virava "hoje de manhã" e o robô marcava o 1º
            # horário de hoje para quem pediu outro dia.
            return _DATA_INEXISTENTE
        if not m.group(3) and alvo < hoje:
            # "05/01" dito em dezembro é o janeiro que vem, não o que passou.
            try:
                alvo = date(ano + 1, mes, d)
            except ValueError:
                return None
        return alvo
    m = _re.search(r"\bdia (\d{1,2})\b", texto)
    if m:
        d = int(m.group(1))
        ano, mes = hoje.year, hoje.month
        for _ in range(2):
            try:
                alvo = date(ano, mes, d)
            except ValueError:
                alvo = None
            if alvo and alvo >= hoje:
                return alvo
            mes, ano = (1, ano + 1) if mes == 12 else (mes + 1, ano)
        return None
    if "semana que vem" in texto or "proxima semana" in texto:
        return hoje + timedelta(days=7 - hoje.weekday())
    for nome, indice in _DIAS_DA_SEMANA.items():
        if nome in palavras:
            # O PRÓXIMO dia com esse nome, nunca hoje: "sexta" dito numa sexta
            # é a que vem — quem quer hoje diz "hoje".
            return hoje + timedelta(days=((indice - hoje.weekday()) % 7) or 7)
    return None


def normalizar_preferencia_agenda(valor, hoje=None) -> dict:
    """Texto de gente -> `{"a_partir_de": "DD/MM/AAAA", "periodo": ...}` | `{}`.

    📊 O portal publica blocos por dia (`horarios-disponiveis`, HAR [045]) e o
    robô escolhe o PRIMEIRO que casa com isto (D-E001101-02). `{}` = não vai:
    a journey cai em "agenda" e a continuação espera a escolha do segurado.

    Aceita também o dicionário já no formato do contrato (o modelo às vezes o
    manda pronto) — mas só se as duas chaves forem válidas.

    🔴 RED B1 (conserto da 001.10.1) — HORA explícita ("4 da tarde", "16h", "às
    9", "15:30") atravessa como `"horario": "HH:MM"`, e o motor agenda SÓ esse
    horário (nunca "o 1º bloco do período"). Hora relativa ("depois das 15h")
    ou frase sobre a LOJA ("a segunda loja", "a mais perto") → `{}`: a lista
    é mostrada e ele escolhe. Data que não existe (31/02) → `{}`. Data PASSADA
    no dicionário vira HOJE (RED P3: é o que o motor já fazia — agora dito).
    """
    import re as _re

    hoje = hoje or _hoje_no_brasil()
    if isinstance(valor, dict):
        from datetime import datetime as _dt

        data = str(valor.get("a_partir_de") or "").strip()
        periodo = str(valor.get("periodo") or "").strip().lower()
        hora = str(valor.get("horario") or "").strip()
        if _re.fullmatch(r"\d{2}/\d{2}/\d{4}", data) and periodo in ("manha", "tarde", "qualquer"):
            try:
                dia = _dt.strptime(data, "%d/%m/%Y").date()
            except ValueError:
                return {}                  # 31/02/2027: data que não existe
            if hora and not _re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", hora):
                return {}                  # horário ilegível: nada de palpite
            saida = {"a_partir_de": max(dia, hoje).strftime("%d/%m/%Y"), "periodo": periodo}
            if hora:
                saida["horario"] = hora
            return saida
        valor = " ".join(str(v) for v in valor.values() if v)
    bruto = _fold(str(valor or "")).lower()
    palavras = _palavras_soltas(bruto)
    if not palavras:
        return {}
    if set(palavras) & _FALA_DA_LOJA:
        return {}                          # "a segunda loja" não é segunda-feira
    texto = " ".join(palavras)
    horario, relativa, hora_ilegivel = _hora_dita(bruto, palavras)
    if relativa or hora_ilegivel:
        return {}

    tem_manha = bool(set(palavras) & _MANHA)
    tem_tarde = bool(set(palavras) & _TARDE)
    tanto_faz = any(t in texto for t in _TANTO_FAZ)
    if tem_manha and tem_tarde:
        periodo = "qualquer"
    elif tem_manha:
        periodo = "manha"
    elif tem_tarde:
        periodo = "tarde"
    elif tanto_faz:
        periodo = "qualquer"
    else:
        periodo = ""

    data = _data_dita(palavras, bruto, hoje)
    if data == _DATA_INEXISTENTE:
        return {}                      # "31/02": disse um dia que não existe
    if data is None and not periodo and not horario:
        return {}                      # não disse nem dia, nem período, nem hora
    if data is None:
        data = hoje                    # "de manhã" / "tanto faz" / "16h" = a partir de já
    if not periodo:
        # disse o dia (ou a hora) e não o período
        periodo = ("manha" if int(horario[:2]) < 12 else "tarde") if horario else "qualquer"
    if data < hoje:
        return {}                      # "a partir de" um dia que já passou não existe
    saida = {"a_partir_de": data.strftime("%d/%m/%Y"), "periodo": periodo}
    if horario:
        saida["horario"] = horario
    return saida


_VISTORIA_LINK = {"link", "celular", "foto", "fotos", "online", "whatsapp", "zap",
                  "remoto", "remota", "app", "aplicativo"}
_VISTORIA_LOJA = {"loja", "levar", "levo", "levando", "oficina", "presencial",
                  "pessoalmente", "credenciada", "ir"}


def normalizar_preferencia_vistoria(valor) -> str:
    """Texto de gente -> `"link"` | `"loja"` | `""`.

    📊 O portal grava a preferência como ocorrência de texto fechado (bundle:
    "…REALIZAR VISTORIA EM LOJA" / "…ONLINE (LINK)"). Os dois ao mesmo tempo, ou
    nenhum, é `""`: o robô pergunta de novo em vez de escolher por ele.
    """
    palavras = set(_palavras_soltas(valor))
    link, loja = bool(palavras & _VISTORIA_LINK), bool(palavras & _VISTORIA_LOJA)
    if link and not loja:
        return "link"
    if loja and not link:
        return "loja"
    return ""


def causa_conhecida(peca, texto):
    """A causa dita e IGUAL (normalizada) a uma das causas MEDIDAS da familia?

    Devolve o texto CANONICO da causa, ou `""`.

    🔴 Igualdade, e so igualdade. 📊 A passada por "palavra distintiva" que
    existia na journey respondeu, na lista ao vivo do para-brisa:

        "quebra acidental do para-brisa"  -> QUEBRA INTENCIONAL OU VOLUNTARIA
        "na chuva o vidro trincou"        -> CHUVA DE GRANIZO

    A primeira e a pior coisa que este produto pode escrever numa seguradora:
    ela descreve fraude. A segunda inventa granizo. As duas passavam confiantes.
    """
    from app.services.perguntas_do_portal_de_vidros import causas_para_oferecer

    dito = " ".join(_palavras_soltas(texto))
    if not dito:
        return ""
    for causa in causas_para_oferecer(peca):
        if " ".join(_palavras_soltas(causa)) == dito:
            return causa
    return ""


def uf_explicita(texto):
    """A UF que o SEGURADO escreveu. `""` quando ele nao escreveu nenhuma.

    🔴 Acabou a UF assumida da apolice. 📊 O red team mediu o custo: o segurado
    digita `"Curitiba"`, a apolice e de SC, e o pedido ia para **CURITIBANOS/SC**
    — 300 km e outra cidade. O CEP da apolice e o de CASA; quem quebra o vidro
    viajando conserta onde esta.
    """
    palavras = _palavras_soltas(texto)
    for w in reversed(palavras):
        if len(w) == 2 and w.upper() in _UFS_DO_BRASIL:
            return w.upper()
    return ""


_UFS_DO_BRASIL = {"AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA",
                  "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN",
                  "RO", "RR", "RS", "SC", "SE", "SP", "TO"}

# Lixo que o segurado responde quando nao quer decidir. 📊 Todos foram medidos
# pelo red team passando pelo gate da cidade e virando `"Nao Sei"`, `"Tanto Faz"`.
_CIDADE_SEM_RESPOSTA = ("nao sei", "nao sei ainda", "tanto faz", "qualquer uma",
                        "qualquer", "perto de casa", "onde for mais perto",
                        "nao decidi", "depois eu digo", "voce escolhe",
                        "onde voce quiser", "sei la", "nao faco ideia")


#: Prefixos de FALA. 🔴 Sao PREFIXOS, e so: nada e removido do MEIO do nome.
#: 📊 O conserto de 20/09 tirava ("em","no","na","de","estou","cidade") de
#: qualquer posicao, e o resultado media assim:
#:
#:     "Passo de Torres/SC"   -> PASSO TORRES     (cidade que existe, nome errado)
#:     "Rio de Janeiro/RJ"    -> RIO JANEIRO
#:     "Cidade Ocidental GO"  -> OCIDENTAL
#:     "Pe de Serra/BA"       -> SERRA            ("pe" lido como a UF PE)
#:
#: Todas nasciam o job, abriam o pedido, e a igualdade falhava DEPOIS do
#: protocolo — que e exatamente o lugar onde falhar custa o atendimento.
#: ⚠️ `cidade de` sai; `cidade` sozinho NAO — senao "Cidade Ocidental" morre.
_PREFIXOS_DE_FALA = (
    "estou na cidade de ", "estou na cidade ", "estou em ", "estou no ",
    "estou na ", "to em ", "to na ", "aqui em ", "aqui na ", "moro em ",
    "moro na ", "na cidade de ", "cidade de ", "em ", "no ", "na ",
)

#: A UF so e reconhecida na ULTIMA posicao, e precisa de um SEPARADOR antes
#: (`/`, `-`, `,` ou espaco). Duas letras no comeco da frase nunca sao UF.
_RE_UF_NO_FIM = __import__("re").compile(
    r"[\/,\-\u2013\u2014\s]\s*([A-Za-z]{2})(?:\s*$|\s*[,\-/])")


def cidade_do_servico_valida(texto):
    """`(cidade, uf, erro)`. `erro` != "" faz o acionamento parar ANTES de abrir.

    O nome da cidade sai INTEIRO: `Passo de Torres`, `Rio de Janeiro`,
    `Cidade Ocidental`. O que se corta e so o prefixo de fala e o que vier
    DEPOIS da UF (`"Sao Jose, sc, perto do shopping"` -> `SAO JOSE`).
    """
    bruto = str(texto or "").strip()
    if not " ".join(_palavras_soltas(bruto)):
        return "", "", "cidade_ausente"
    if " ".join(_palavras_soltas(bruto)) in _CIDADE_SEM_RESPOSTA:
        return "", "", "cidade_sem_resposta"

    # 1) a UF, so no fim (a ULTIMA ocorrencia que seja uma UF de verdade)
    uf = ""
    corte = len(bruto)
    for m in _RE_UF_NO_FIM.finditer(_fold(bruto)):
        if m.group(1).upper() in _UFS_DO_BRASIL:
            uf, corte = m.group(1).upper(), m.start()
    if not uf:
        return "", "", "uf_ausente"

    # 2) o nome e o que vem ANTES da UF, inteiro
    nome = bruto[:corte].strip(" ,-/\u2013\u2014")

    # 3) so PREFIXO de fala sai, e o mais longo primeiro
    dobrado = _fold(nome).lower().strip()
    for pref in _PREFIXOS_DE_FALA:
        if dobrado.startswith(pref):
            nome = nome[len(pref):].strip()
            break

    nome = " ".join(_palavras_soltas(nome)).upper()
    if not nome:
        return "", uf, "cidade_ausente"
    return nome, uf, ""


def build_portal_params(flat: dict, profile: dict, infocap: dict,
                        *, enviar_de_verdade: bool = False) -> Tuple[Optional[dict], Optional[str]]:
    """(params, erro). flat = decisoes do LLM (cpf, data, dano, placa_informada
    fallback). profile = perfil de acionamento da corretora. infocap = retorno REAL
    do vehicle lookup (policy/vehicle/client). erro != None quando falta fato.

    P-90 — `enviar_de_verdade` e o que vira `params['confirm']`, e ele NASCE
    False. Aqui morava um `"confirm": False` CRAVADO: nenhum caminho do
    repositorio conseguia liga-lo, entao o acionamento percorria o formulario
    inteiro e parava no 80% para sempre. 📊 9 dos 39 jobs chegaram exatamente
    ali ("cheguei na confirmacao (80%) — aprove para enviar") e a aprovacao nao
    existia em lugar nenhum.

    Continua nascendo False de proposito: quem decide e o CHAMADOR, que sabe se
    o agente de atendimento da corretora esta ligado (`portal_tool._arun`).
    Um default True aqui faria com que qualquer chamada nova — um teste, uma
    rotina, um caminho que ainda nao existe — abrisse pedido de verdade na
    seguradora por esquecimento. Esquecer tem de custar um pedido a menos,
    nunca um pedido a mais.

    A ordem e deliberada: primeiro os fatos que NAO dependem do segurado (perfil
    da corretora, seguradora, placa) — recusar por eles e barato e nao gasta a
    paciencia de ninguem. So depois a FICHA DO ACIONAMENTO, que precisa da
    InfoCap ja lida (o veiculo e o CEP saem de la) para saber o que NAO perguntar."""
    flat = flat or {}
    profile = profile or {}
    sol = {
        "relacao": "Corretor",
        "nome": str(profile.get("nome") or "").strip(),
        "email": str(profile.get("email") or "").strip(),
        "telefone": str(profile.get("telefone") or "").strip(),
        "cpf_cnpj": str(profile.get("cpf_cnpj") or "").strip(),
    }
    if not (sol["nome"] and sol["email"]):
        return None, ("A corretora ainda nao configurou o Perfil de Acionamento (nome + e-mail). "
                      "Configure em Personalizacao -> Corretora antes de acionar portais.")

    infocap = infocap or {}
    pol = infocap.get("policy") or {}
    veh = infocap.get("vehicle") or {}
    cli = infocap.get("client") or {}

    insurer = normalize_insurer(pol.get("seguradora") or pol.get("seguradora_abrev"))
    if not insurer:
        return None, "A InfoCap nao retornou a seguradora da apolice AUTO. Verifique a apolice."

    # Placa: SEMPRE da InfoCap. Fallback unico: o cliente informou (placa_informada)
    # porque a InfoCap nao tem — nunca a LLM por conta propria.
    placa = str(veh.get("placa") or "").strip().upper() or str(flat.get("placa_informada") or "").strip().upper()
    if not placa:
        return None, ("A apolice na InfoCap nao trouxe a PLACA do veiculo. Pergunte a placa ao segurado "
                      "e chame de novo com placa_informada.")

    # -------------------------------------------------------------------
    # BLOCO 7.5 — A FICHA DO ACIONAMENTO, conferida ANTES de abrir o portal.
    #
    # `ja_sei` junta as duas fontes: o que o segurado respondeu (via LLM) e o
    # que a InfoCap trouxe (veiculo e cep). E a segunda fonte que faz o produto
    # NAO perguntar a versao do carro nem o CEP a quem acabou de ter o vidro
    # quebrado — eles ja estao na apolice (mapa §8.3).
    # -------------------------------------------------------------------
    bruto = flat.get("especificos")
    especificos = {str(k): v for k, v in bruto.items()} if isinstance(bruto, dict) else {}
    ja_sei = {
        "cpf_cnpj": flat.get("cpf_cnpj"),
        "data_dano": flat.get("data_dano"),
        "peca": flat.get("peca"),
        "como_ocorreu": flat.get("como_ocorreu"),
        "onde_ocorreu": flat.get("onde_ocorreu"),
        "descricao": flat.get("descricao"),
        # P0-5 — aceita o campo tanto no topo quanto em `especificos` (que é o
        # transporte declarado em `como_devolver`). `especificos` vence, porque
        # é o caminho que a pergunta ensina ao agente.
        "cidade_para_o_servico": flat.get("cidade_para_o_servico"),
        "veiculo": veh.get("veiculo"),
        "cep": cli.get("cep"),
        **especificos,
    }
    peca_dita = str(flat.get("peca") or "").strip()
    faltam = o_que_falta(peca_dita, ja_sei)
    # So trava no que o agente CONSEGUE responder de volta (ver `trava_o_pedido`).
    # O resto vai junto na mensagem, para ele coletar na mesma conversa.
    if [p for p in para_o_segurado(faltam) if trava_o_pedido(p)]:
        return None, mensagem_para_o_agente(faltam, peca_dita)

    # 🔴 A CIDADE E A UF SAO DO SEGURADO, E AS DUAS TEM DE VIR ESCRITAS.
    # `cidade_e_uf_do_servico` continua existindo para quem so quer formatar o
    # texto; quem DECIDE se o pedido pode nascer e `cidade_do_servico_valida`.
    cidade_servico, cidade_servico_uf, erro_da_cidade = cidade_do_servico_valida(
        ja_sei.get("cidade_para_o_servico"))
    if erro_da_cidade:
        p_cidade = pergunta_do_campo("cidade_para_o_servico")
        motivo = {
            "cidade_ausente": "Em qual CIDADE e ESTADO voce quer fazer o servico?",
            "uf_ausente": ("Me confirma o ESTADO dessa cidade (a sigla, tipo SC ou "
                           "PR)? Cidade com o mesmo nome existe em mais de um "
                           "estado, e o vidraceiro vai para o endereco errado."),
            "cidade_sem_resposta": ("Preciso de uma cidade de verdade para achar a "
                                    "loja mais perto: em qual cidade e estado voce "
                                    "quer fazer o servico?"),
        }[erro_da_cidade]
        return None, ("Falta a cidade do servico para eu abrir o pedido. PERGUNTE "
                      "AGORA, com estas palavras:\n\n  " + motivo
                      + "\n\n[para a equipe] `cidade_para_o_servico` recusada: "
                      + erro_da_cidade
                      + (f". A pergunta do catalogo e: {p_cidade.texto}" if p_cidade else ""))
    cidade_servico_origem = "segurado"

    # 🔴 O PERIMETRO e um ENUM, e a classificacao acontece AQUI.
    perimetro = normalizar_perimetro(ja_sei.get("onde_ocorreu"))
    if not perimetro:
        return None, ("Falta saber onde o dano aconteceu. PERGUNTE AGORA:\n\n"
                      "  Foi na cidade ou na estrada/rodovia?\n\n"
                      "[para a equipe] `onde_ocorreu` nao classificou como urbano "
                      "nem rodoviario, e o portal so aceita esses dois. Registre a "
                      "resposta em `onde_ocorreu` com uma dessas duas palavras.")

    # 🔴 A CAUSA tem de ser IGUAL a uma das causas MEDIDAS da familia.
    causa_canonica = causa_conhecida(peca_dita, ja_sei.get("como_ocorreu"))
    if not causa_canonica:
        from app.services.perguntas_do_portal_de_vidros import causas_para_oferecer

        lista = causas_para_oferecer(peca_dita)
        return None, ("A causa do dano precisa ser UMA da lista da seguradora, "
                      "escrita igual. Escolha pelo que ele ja contou; se o relato "
                      "nao decidir entre duas, PERGUNTE ao segurado oferecendo 3 ou "
                      "4 delas em lingua de gente.\n\n"
                      "Causas aceitas para esta peca:\n"
                      + "\n".join("  · " + c for c in lista)
                      + "\n\n[para a equipe] `como_ocorreu` nao e igual a nenhuma "
                      "causa medida. 🔴 Casar por semelhanca ja gravou QUEBRA "
                      "INTENCIONAL para quem disse `quebra acidental`.")

    # 🔴 O REPARO chega a journey como `sim`/`nao`, nunca como frase.
    if "aceita_reparo" in especificos:
        reparo_normalizado = normalizar_aceita_reparo(especificos.get("aceita_reparo"))
        if not reparo_normalizado:
            return None, ("Nao entendi se o segurado aceita o REPARO do vidro ou "
                          "prefere a troca. PERGUNTE AGORA:\n\n  A seguradora pode "
                          "consertar o vidro sem trocar (leva uns 30 minutos e "
                          "normalmente sai sem franquia — eu confirmo o valor quando "
                          "ela responder). Voce quer tentar o reparo?\n\n"
                          "[para a equipe] registre `aceita_reparo` como `sim` ou `nao`.")
        especificos["aceita_reparo"] = reparo_normalizado
        ja_sei["aceita_reparo"] = reparo_normalizado

    # 🔴 SPEC-EXTRA-001.10.1 C2 — as PREFERÊNCIAS atravessam como ENUM, ou não
    # atravessam. Resposta que não normaliza SAI de `especificos` (nunca vai a
    # frase crua): a journey cai em "agenda"/"vistoria" e o robô continua
    # quando o segurado escolher. Não trava — nem pergunta de novo aqui.
    if PREFERENCIA_AGENDA in especificos:
        pref = normalizar_preferencia_agenda(especificos.get(PREFERENCIA_AGENDA))
        if pref:
            especificos[PREFERENCIA_AGENDA] = pref
        else:
            especificos.pop(PREFERENCIA_AGENDA, None)
    if PREFERENCIA_VISTORIA in especificos:
        pref_v = normalizar_preferencia_vistoria(especificos.get(PREFERENCIA_VISTORIA))
        if pref_v:
            especificos[PREFERENCIA_VISTORIA] = pref_v
        else:
            especificos.pop(PREFERENCIA_VISTORIA, None)
    # 🔴 D-E001101-05 — domicílio FORA: a modalidade é SEMPRE loja. Sobrescreve
    # de propósito: um "domicilio" que ainda chegue (modelo com memória velha)
    # faria o caminho DOM recomendar o botão de domicílio que o produto não
    # entrega. 📊 `adaptive.preferencia_do_segurado` lê esta chave e
    # `vidros_lanternas.preferencia_de_atendimento("loja")` devolve "loja".
    especificos[ONDE_REALIZAR_O_SERVICO] = ONDE_REALIZAR_PADRAO

    # N-3 — o contato que vai ao portal. Tudo vem do banco: o segurado da
    # apólice, a corretora do Perfil de Acionamento. ⛔ Nada de constante de
    # corretora aqui (CLAUDE.md §13.9): `sol` já é o perfil daquela `company_id`.
    # 🔴 D-E001101-04 (Founder) — Corretor ("6") + celular e e-mail do SEGURADO
    # + WhatsApp marcado. 📊 B0.12: nas 6 capturas, `StatusEnvioWhatsapp:true`
    # só com Tipo 20 (CELULAR SEGURADO) fez o portal responder
    # `PossuiTelefoneRecebeWhatsapp:true`. O telefone e o e-mail vêm da InfoCap
    # (`/cliente_cpf`), nunca da conversa: quem fala no WhatsApp pode não ser o
    # titular.
    tel_segurado = str(cli.get("telefone") or "").strip()
    contato = {
        # 📊 "6" = Corretor na tabela `RelacaoTitular` do POST /solicitantes.
        # O número é do portal, não nosso — por isso vai como string literal.
        "relacao": "6",
        "telefone": tel_segurado or sol["telefone"],
        "tipo_telefone": "segurado" if tel_segurado else "corretora",
        # ⚠️ Só marca WhatsApp no celular do SEGURADO: marcar no número da
        # corretora mandaria as mensagens da seguradora para a corretora.
        "recebe_whatsapp": bool(tel_segurado),
        "email_segurado": str(cli.get("email") or "").strip(),
        "email_corretora": sol["email"],
        "nome_solicitante": sol["nome"],
        "documento_corretor": sol["cpf_cnpj"],
    }

    endereco_txt = _fold(", ".join(p for p in (
        " ".join(x for x in (cli.get("logradouro"), cli.get("numero")) if x),
        cli.get("bairro"), f"{cli.get('cidade') or ''} {cli.get('estado') or ''}".strip(),
    ) if p))
    chassi = str(veh.get("chassi") or "").strip()

    params = {
        "insurer_name": insurer,
        "cpf_cnpj": str(flat.get("cpf_cnpj") or "").strip(),
        "placa": placa,
        "data_dano": str(flat.get("data_dano") or "").strip(),
        "solicitante": sol,
        "segurado": {
            "nome": str(cli.get("nome") or "").strip(),
            "apolice": str(pol.get("numapo") or "").strip(),
            "chassi": chassi,
            "ultimos_6_chassi": chassi[-6:] if chassi else "",
            "veiculo": str(veh.get("veiculo") or "").strip(),
            "cep": str(cli.get("cep") or "").strip(),
            "endereco": endereco_txt,
            "telefone": str(cli.get("telefone") or "").strip(),
            "email": str(cli.get("email") or "").strip(),
        },
        "dano": {
            "peca": str(flat.get("peca") or "").strip(),
            # 🔴 CANONICO: igual a uma causa medida da familia. A journey casa
            # por IGUALDADE com a lista ao vivo e nao interpreta nada.
            "como": causa_canonica,
            # 🔴 ENUM: `urbano` | `rodoviario`. Nada de frase.
            "onde": perimetro,
            # 📊 O portal exige minimo de 30 caracteres aqui. Nao se pede ao
            # segurado que "escreva mais": o texto e COMPOSTO do que ele ja
            # disse (peca + relato + data + local). Relato dele com 30+ vai
            # inteiro, com as palavras dele.
            "descricao": compor_descricao(ja_sei),
            # P1-5 — a lista de peças amassadas do MESMO evento. Só a família
            # lataria a faz nascer, e por isso ela é `[]` em todo o resto: a
            # journey lê o tamanho, não a presença da chave.
            "pecas_lataria": _lista_de_pecas(ja_sei.get("pecas_lataria")),
        },
        # As respostas do passo 6 (80%), ja coletadas na conversa. A journey ja
        # le esta chave (`vidros_lanternas.abrir_atendimento`) e a entrega ao
        # cerebro adaptativo — era o unico pedaco do caminho que nascia vazio.
        "especificos": {k: v for k, v in especificos.items()
                        if (v if isinstance(v, (list, tuple)) else str(v or "").strip())},
        "local": {
            "estado": _fold(cli.get("estado")).upper(),
            "cidade": _fold(cli.get("cidade")).title(),
            "cep": str(cli.get("cep") or "").strip(),
            # 🔴 P0-5 — A CIDADE DO SERVIÇO, que NÃO é a cidade do cadastro.
            #
            # As duas convivem na mesma chave de propósito: `local.cidade` é
            # onde ele MORA (vai no cadastro e no cálculo de domicílio) e
            # `local.cidade_servico` é onde ele QUER o serviço (vira
            # `CodigoCidade` no PATCH). Guardá-las com o mesmo nome faria a
            # journey escolher uma por engano — e a escolha errada é um
            # vidraceiro em outra cidade.
            "cidade_servico": {"uf": cidade_servico_uf, "cidade": cidade_servico},
            "cidade_servico_uf_de": cidade_servico_origem,
        },
        # 🔴 N-3 (D-E00110-01) — QUEM A LOJA LIGA PARA ACHAR.
        #
        # 📊 Medido em 20/09/2026: 3 das 4 capturas gravaram o telefone com
        # `Tipo 21 = CELULAR CORRETOR`, e o portal respondeu
        # `PossuiTelefoneRecebeWhatsapp:false` — o segurado não recebe nada da
        # seguradora e a loja liga para a corretora, que então liga para ele.
        # `Tipo 20 = CELULAR SEGURADO` tem ZERO exercícios.
        #
        # O desenho: a RELAÇÃO declarada continua sendo a verdade (quem abre é
        # a corretora → "6" = Corretor; declarar "O Próprio" seria declaração
        # falsa), e o CONTATO passa a ser o do segurado, porque é ele que a
        # loja precisa achar para combinar o dia. O e-mail da corretora
        # continua indo junto — é assim que ela recebe a cópia.
        #
        # ⚠️ Sem telefone do segurado o contato CAI para o da corretora, com o
        # tipo dizendo a verdade. Um telefone vazio no portal é um pedido que
        # ninguém consegue agendar.
        "contato": contato,
        # P-90 — O QUE DECIDE SE O PEDIDO NASCE DE VERDADE.
        #
        # `confirm=False` faz `run_adaptive` parar em `is_confirm_screen` (o 80%)
        # e devolver `needs_human`; `confirm=True` deixa o fluxo seguir ate o
        # passo 7, onde o Nº do atendimento aparece
        # (docs/canon/O-PORTAL-DE-VIDROS-TELA-POR-TELA.md §7).
        #
        # O valor vem de fora, do agente ligado — nao de uma constante. Era a
        # constante que fazia 39 acionamentos morrerem a 20% do fim.
        "confirm": bool(enviar_de_verdade),
    }
    return params, None


# ===========================================================================
# O DESFECHO VIRA MENSAGEM — SPEC-EXTRA-001.10 N-1 / P1-1
# ===========================================================================
#
# 🔴 Quem decide o que acontece depois do pedido é o PORTAL, não nós. 📊 Medido
# em 20/09/2026 sobre 3 capturas: `GET /agendamentos/opcoes-disponiveis` devolve
# 20 chaves booleanas e o bundle as roteia — e duas apólices idênticas, na mesma
# seguradora e na mesma categoria, deram desfechos OPOSTOS (uma loja já
# atribuída × uma agenda com lojas). Não é atributo de peça, é decisão do portal.
#
# Este bloco só TRADUZ o que veio. Ele nunca escolhe loja, nunca promete dia e
# nunca inventa endereço: cada linha abaixo só aparece se o dado chegou.

#: 📊 Copy do HTML da tela final do portal (20/09/2026), reescrita em português
#: de gente. Vai em TODO desfecho, porque o golpe do "depósito da franquia"
#: chega justamente a quem acabou de abrir um atendimento de verdade.
AVISO_ANTIFRAUDE = (
    "Importante: a franquia, quando existe, é paga na hora do serviço, direto "
    "na loja. Ninguém vai te pedir depósito ou transferência antes — se pedirem, "
    "não pague nada e me chama aqui."
)


def _linhas_de_franquia(desfecho: dict) -> list:
    """Cada linha `{titulo, valor}` que o portal mandou, do jeito que ele mandou.

    ⚠️ "SEM FRANQUIA" é um VALOR válido, não ausência — 📊 a captura de
    20/09/2026 trouxe as três linhas juntas: *Valor para troca 630*, *Desconto
    para reparo 630* e *Valor para reparo SEM FRANQUIA*. Tratar texto como
    "vazio" apagaria justamente a linha que é boa notícia.
    """
    saida = []
    for item in (desfecho.get("franquias") or []):
        if not isinstance(item, dict):
            continue
        titulo = str(item.get("titulo") or "").strip()
        valor = item.get("valor")
        valor_txt = str(valor).strip() if valor is not None else ""
        if not (titulo and valor_txt):
            continue
        if valor_txt.replace(".", "").replace(",", "").isdigit():
            valor_txt = f"R$ {valor_txt}"
        saida.append(f"• {titulo}: {valor_txt}")
    return saida


def _bloco_da_loja(loja: dict) -> list:
    linhas = []
    nome = str(loja.get("nome") or "").strip()
    if nome:
        linhas.append(f"Loja: {nome}")
    endereco = str(loja.get("endereco") or "").strip()
    if endereco:
        linhas.append(f"Endereço: {endereco}")
    referencia = str(loja.get("referencia") or "").strip()
    if referencia:
        linhas.append(f"Ponto de referência: {referencia}")
    telefone = str(loja.get("telefone") or "").strip()
    if telefone:
        linhas.append(f"Telefone: {telefone}")
    return linhas


# ===========================================================================
# 🔴 SPEC-EXTRA-001.10.1 — A CONTINUAÇÃO, lida da evidence (contrato A→C §5)
# ===========================================================================
# `evidence["continuacao"] = {possivel, etapa, acao_esperada, emitida_em,
# sessao_guardada, motivo}` — escrito pela journey (builder A). Daqui só se LÊ:
# quem decide se dá para continuar é quem guardou o token, não o texto.


def continuacao_da_evidencia(evidence) -> dict:
    """O bloco `continuacao` da evidence, ou `{}`. ⛔ Nenhuma mensagem o
    imprime: quem o carrega adiante é `montar_job_de_continuacao`, inteiro."""
    ev = evidence if isinstance(evidence, dict) else {}
    bloco = ev.get("continuacao")
    return bloco if isinstance(bloco, dict) else {}


def continuacao_possivel(evidence) -> bool:
    """A journey disse, com todas as letras, que o pedido pode ser retomado?

    🔴 Só `possivel is True`. Um `"true"` em texto, `1` ou a chave ausente
    respondem NÃO — prometer "eu continuo daqui" sobre um token que não foi
    guardado é o texto mentindo ao segurado.
    """
    return continuacao_da_evidencia(evidence).get("possivel") is True


def acao_esperada(evidence) -> Tuple[str, str]:
    """`("agendar"|"responder"|"vistoria"|"reler"|"", slot)` — o que a
    continuação espera. `slot` só existe em `responder:<slot>`."""
    bruto = str(continuacao_da_evidencia(evidence).get("acao_esperada") or "").strip()
    operacao, _, slot = bruto.partition(":")
    operacao = operacao.strip().lower()
    if operacao not in ("agendar", "responder", "vistoria", "reler"):
        return "", ""
    return operacao, slot.strip()


#: 📊 SPEC §3 C4: as paradas TÉCNICAS depois do protocolo — nenhuma depende do
#: segurado; uma releitura pelo estado real do agregado pode resolvê-las.
ESTAGIOS_TECNICOS = ("corretor_recusado", "solicitante_recusado",
                     "tipo_de_telefone_desconhecido", "catalogo_indisponivel",
                     "motivos_indisponiveis", "roteador_ilegivel",
                     "desfecho_ilegivel", "patch_recusado",
                     # 🔴 conserto da 001.10.1: RED P1 — o `GET /atendimentos`
                     # da continuação sem 200 (nada foi escrito); RED B3 — a
                     # agenda não respondeu (500/timeout), nunca "ocupado".
                     "leitura_falhou", "agenda_nao_respondeu")

#: As paradas que dependem de uma RESPOSTA do segurado e que a continuação
#: resolve (contrato §5: `acao_esperada = responder:<slot>` / `vistoria`).
ESTAGIOS_QUE_O_SEGURADO_RESPONDE = (
    "peca_ambigua", "peca_de_lataria_ambigua", "pecas_de_lataria_ausentes",
    "cidade_sem_rede", "cidade_ambigua", "uf_desconhecida", "motivo_ambiguo",
    "questionario_incompleto", "decidir_reparo", "decidir_vistoria",
    # COSTURA: a escolha sumiu da agenda — quem escolhe de novo é o segurado.
    "horario_indisponivel")


def _hora_legivel(texto) -> str:
    """"HH:MM" ou "". ⛔ Nada que não seja hora entra na mensagem (G8: nem
    chave, nem colchete, nem `None`)."""
    import re as _re

    m = _re.fullmatch(r"\s*(\d{1,2})\s*(?::|h)\s*(\d{2})?\s*(?:h|hs|horas)?\s*",
                      str(texto or ""))
    if not m:
        m = _re.fullmatch(r"\s*(\d{1,2})()\s*(?:h|hs|horas)?\s*", str(texto or ""))
    if not m:
        return ""
    h, mi = int(m.group(1)), int(m.group(2) or 0)
    if h > 23 or mi > 59:
        return ""
    return f"{h:02d}:{mi:02d}"


def _dia_legivel(texto) -> str:
    """"DD/MM" ou ""."""
    import re as _re

    m = _re.fullmatch(r"\s*(\d{1,2})\s*/\s*(\d{1,2})(?:\s*/\s*\d{2,4})?\s*", str(texto or ""))
    if not m:
        return ""
    d, mes = int(m.group(1)), int(m.group(2))
    if not (1 <= d <= 31 and 1 <= mes <= 12):
        return ""
    # 🔴 RED P2 (conserto da 001.10.1): "31/02" passava, ia ao portal e voltava
    # como "esse horário acabou de ser ocupado" — falso. O dia tem de EXISTIR.
    # Ano bissexto de referência: 29/02 existe em algum ano próximo.
    from datetime import date as _date

    try:
        _date(2024, mes, d)
    except ValueError:
        return ""
    return f"{d:02d}/{mes:02d}"


#: Teto do que cabe numa mensagem de WhatsApp sem virar parede: 3 dias × 6
#: horários por loja (SPEC §3 C3).
_TETO_DIAS, _TETO_HORARIOS = 3, 6


def _horarios_da_loja(loja: dict) -> list:
    """`[("DD/MM", ["HH:MM", …]), …]` — só o que é legível, no teto."""
    bruto = loja.get("horarios") if isinstance(loja.get("horarios"), dict) else {}
    saida = []
    for dia, horas in bruto.items():
        d = _dia_legivel(dia)
        if not d or not isinstance(horas, (list, tuple)):
            continue
        legiveis = [h for h in (_hora_legivel(x) for x in horas
                                if isinstance(x, str)) if h]
        if legiveis:
            saida.append((d, legiveis[:_TETO_HORARIOS]))
        if len(saida) >= _TETO_DIAS:
            break
    return saida


def _bloco_da_agenda(desfecho: dict, pode_continuar: bool) -> str:
    """As lojas numeradas, com os horários por dia. "" sem lojas."""
    lojas = [l for l in (desfecho.get("lojas") or []) if isinstance(l, dict)]
    if not lojas:
        return ""
    linhas = ["Você escolhe onde quer fazer o serviço. Estas são as lojas "
              "credenciadas mais perto de você:"]
    alguma_com_horario = False
    for i, loja in enumerate(lojas, start=1):
        nome = str(loja.get("nome") or "").strip() or f"Loja {i}"
        endereco = str(loja.get("endereco") or "").strip()
        cidade = " ".join(x for x in (str(loja.get("cidade") or "").strip(),
                                      str(loja.get("uf") or "").strip()) if x)
        distancia = str(loja.get("distancia") or "").strip()
        tempo = str(loja.get("tempo") or "").strip()
        detalhe = ", ".join(x for x in (endereco, cidade) if x)
        perto = " · ".join(x for x in (distancia, tempo) if x)
        linha = f"{i}) {nome}"
        if detalhe:
            linha += f" — {detalhe}"
        if perto:
            linha += f" ({perto})"
        horarios = _horarios_da_loja(loja)
        dias = [str(d).strip() for d in (loja.get("dias") or []) if _dia_legivel(d)]
        if horarios:
            alguma_com_horario = True
            for dia, horas in horarios:
                linha += f"\n   {dia}: {', '.join(horas)}"
        elif dias:
            linha += f"\n   Dias com agenda: {', '.join(dias[:8])}"
        elif loja.get("tem_agenda") is False:
            linha += "\n   (sem agenda aberta no momento)"
        linhas.append(linha)
    if pode_continuar:
        # 🔴 SPEC-EXTRA-001.10.1 — o robô AGENDA: a continuação leva a escolha
        # ao portal e a confirmação é LIDA dele (`ScriptFinalizacao`, HAR [049]).
        linhas.append(
            "Me diga o número da loja, o dia e o horário que eu agendo para você."
            if alguma_com_horario else
            "Me diga o número da loja e o dia que fica melhor, que eu vejo os horários "
            "e agendo para você.")
    else:
        # A versão honesta de antes: sem sessão guardada, quem fecha é a equipe.
        linhas.append(
            "Me diz o NÚMERO da loja que você prefere e o DIA que fica melhor. "
            "⚠️ Quem confirma o horário com a loja é a nossa equipe — eu anoto a "
            "sua escolha e passo para eles fecharem, e te aviso quando estiver "
            "confirmado. Não considere agendado até eu te confirmar.")
    return "\n".join(linhas)


def _permanencia_legivel(valor) -> str:
    """📊 `TempoPermanencia 90` em `horarios-disponiveis` (HAR [045]) é em
    MINUTOS. Número puro ganha a unidade; texto vai como veio."""
    texto = str(valor if valor is not None else "").strip()
    if not texto or texto.lower() == "none":
        return ""
    return f"{texto} minutos" if texto.isdigit() else texto


def _bloco_do_agendamento(ag: dict) -> list:
    """As linhas do agendamento CONFIRMADO — cada uma só se o dado veio."""
    linhas = []
    for rotulo, chave in (("Loja", "loja"), ("Endereço", "endereco"),
                          ("Ponto de referência", "referencia"), ("Dia", "data"),
                          ("Horário", "horario")):
        valor = str(ag.get(chave) or "").strip()
        if valor and valor.lower() != "none":
            linhas.append(f"{rotulo}: {valor}")
    perm = _permanencia_legivel(ag.get("permanencia"))
    if perm:
        linhas.append(f"Tempo que o carro fica na loja: {perm}")
    return linhas


def mensagem_do_desfecho(desfecho: Optional[dict], continuacao: Optional[dict] = None) -> str:
    """O que o segurado lê quando o portal decidiu. "" = não há desfecho legível.

    🔴 NUNCA INVENTA LOJA. Toda loja citada sai de `desfecho["loja"]` ou de
    `desfecho["lojas"]`; sem elas, a mensagem diz o que sabe e para. Uma loja
    inventada manda uma pessoa dirigir até um endereço que não existe.

    `continuacao` é o bloco `evidence["continuacao"]` (SPEC-EXTRA-001.10.1):
    com `possivel: True` o texto convida a responder AQUI; sem ele, o texto
    honesto de antes (quem conclui é a equipe).
    """
    if not isinstance(desfecho, dict) or not desfecho:
        return ""
    pode_continuar = isinstance(continuacao, dict) and continuacao.get("possivel") is True

    tipo = str(desfecho.get("tipo") or "desconhecido").strip().lower()
    numero = str(desfecho.get("codigo_atendimento") or "").strip()

    partes = []
    if numero:
        partes.append(
            f"Seu atendimento foi aberto na seguradora ✅\n"
            f"Número do atendimento: {numero} — guarde esse número, é com ele que "
            f"você acompanha e cobra o serviço.")
    else:
        partes.append("Seu atendimento foi aberto na seguradora ✅")

    franquias = _linhas_de_franquia(desfecho)
    if franquias:
        partes.append("Sobre a franquia:\n" + "\n".join(franquias))

    if tipo == "agendado":
        ag = desfecho.get("agendamento") if isinstance(desfecho.get("agendamento"), dict) else {}
        bloco = _bloco_do_agendamento(ag)
        # 🔴 "Agendei" só com a confirmação LIDA do portal (📊 B0.5: o
        # `ScriptFinalizacao` traz "Agendado para 22/09/2026 às 16:00"). Sem
        # ela, dizer "agendei" seria mandar a pessoa a uma loja que não a espera.
        # 🔴 JUIZ P3 (conserto da 001.10.1): reagendar é FORA da SPEC — a frase
        # não promete que o robô muda o horário; ela passa para a equipe.
        # `ja_estava_agendado` (JUIZ B1): o portal JÁ estava agendado quando a
        # continuação leu — não fomos nós que marcamos agora, e o texto não
        # diz "Agendei".
        if ag.get("confirmado_pelo_portal") is True and bloco:
            titulo = ("Seu serviço já está agendado ✅" if ag.get("ja_estava_agendado") is True
                      else "Agendei o serviço ✅")
            partes.append(titulo + "\n" + "\n".join(bloco)
                          + "\n\nSe precisar mudar, me avise por aqui que eu passo "
                            "para a nossa equipe.")
        else:
            partes.append(
                "Pedi o agendamento, mas a seguradora ainda não me confirmou o horário. "
                "Não considere agendado até eu te confirmar — a nossa equipe confere "
                "direto com a seguradora e eu te aviso aqui.")

    elif tipo == "loja_direta":
        bloco = _bloco_da_loja(desfecho.get("loja") or {})
        if bloco:
            partes.append(
                "A seguradora já escolheu a loja que vai fazer o serviço:\n"
                + "\n".join(bloco)
                + "\n\nÉ a loja que combina o dia com você. Se preferir adiantar, "
                  "pode ligar direto para ela e agendar.")
        else:
            partes.append(
                "A seguradora já encaminhou seu pedido para uma loja credenciada. "
                "Eles entram em contato com você para combinar o dia — assim que eu "
                "tiver os dados da loja, eu te passo aqui.")

    elif tipo == "agenda":
        bloco = _bloco_da_agenda(desfecho, pode_continuar)
        if bloco:
            partes.append(bloco)
        else:
            partes.append(
                "A seguradora liberou o agendamento, mas não consegui ler a lista de "
                "lojas por aqui. Já passei para a nossa equipe buscar as opções e te "
                "retornar com elas.")

    elif tipo == "analista":
        # ⚠️ O texto do portal entra INTEIRO quando ele já diz o que precisa ser
        # dito, e só é substituído quando não diz. Repetir "está com o analista"
        # duas vezes na mesma mensagem soa a robô — e soar a robô é a única
        # coisa que o segurado nota antes do conteúdo.
        titulo = str(desfecho.get("titulo_portal") or "").strip()
        prazo = ("O retorno costuma sair até o próximo dia útil — assim que chegar, "
                 "eu te aviso aqui mesmo.")
        if "analista" in _fold(titulo).lower():
            partes.append(f"{titulo} {prazo}")
        else:
            partes.append("Seu pedido está com o analista da seguradora. " + prazo)

    elif tipo in _TIPOS_DE_VISTORIA_OPCIONAL or (tipo == "vistoria" and pode_continuar):
        # 🔴 SPEC-EXTRA-001.10.1 A5/C3 — 📊 lataria: `PermiteOpcaoVistoria:true`
        # e o portal quer a preferência (bundle: loja × link). O nome final do
        # tipo é do builder A; os dois nomes do contrato são aceitos.
        pergunta = ("A seguradora vai fazer uma vistoria antes de liberar o serviço. "
                    "Você prefere receber um link no celular para mandar as fotos, ou "
                    "levar o carro numa loja?")
        if pode_continuar:
            partes.append(pergunta + " Me responde por aqui que eu continuo o seu "
                                     "pedido de onde parou.")
        else:
            partes.append(pergunta + " A nossa equipe registra a sua escolha com a "
                                     "seguradora e te explica o passo seguinte — você "
                                     "não vai precisar repetir nada.")

    elif tipo == "vistoria":
        partes.append(
            "A seguradora pediu uma vistoria antes de liberar o serviço. Essa parte "
            "quem conduz é a nossa equipe: já passei o seu caso para eles, com tudo o "
            "que você me contou, e eles te explicam o passo seguinte. Você não vai "
            "precisar repetir nada.")

    else:
        partes.append(
            "O pedido está aberto, mas a seguradora respondeu de um jeito que eu não "
            "consigo interpretar sozinho — e eu prefiro te dizer isso do que te dar "
            "uma informação errada. Já passei para a nossa equipe conferir direto com "
            "eles, e te aviso assim que tiver a resposta certa.")

    link = str(desfecho.get("link_area_segurado") or "").strip()
    if link:
        partes.append(f"Você também acompanha por aqui: {link}")

    partes.append(AVISO_ANTIFRAUDE)
    return "\n\n".join(p for p in partes if str(p).strip()).strip()


#: Os dois nomes do contrato para "o portal quer saber loja × link".
_TIPOS_DE_VISTORIA_OPCIONAL = ("vistoria_opcional", "decidir_vistoria")


# ---------------------------------------------------------------------------
# AS PARADAS — desconhecido nunca vira silêncio
# ---------------------------------------------------------------------------
#
# Cada parada tem DUAS traduções: uma pergunta curta para o segurado (com as
# opções, quando o portal as deu) e um dossiê para quem vai resolver. A regra
# que nasceu aqui: **uma parada sem texto é uma parada que o segurado não vê**,
# e o que ele não vê ele cobra por outro canal.
# 🔴 REESCRITO em 20/09/2026 — juiz B4 / red B6.
#
# Tres regras, e as tres sairam de laudo com medicao:
#
# 1. **NENHUM texto promete continuacao SEM PROVA dela.** 🔴 SPEC-EXTRA-001.10.1:
#    a journey `continuar_atendimento` existe e o token vai CIFRADO em
#    `evidence["continuacao"]`. O texto passa a dizer "me responde que eu
#    continuo" SO quando `continuacao.possivel is True` (`texto_da_parada`); sem
#    essa prova, fica o texto honesto de antes — a equipe assume.
# 2. **A pergunta so aparece se a resposta for UTIL a equipe** — e o dossie diz
#    a equipe o que fazer com ela no portal.
# 3. **O numero vem primeiro** (quem garante e `format_result`, abaixo).
_A_EQUIPE_ASSUME = ("O pedido esta aberto na seguradora e quem conclui este ponto e a nossa equipe, que ja recebeu tudo — voce nao precisa repetir nada.")

_PARADAS = {
    "decidir_reparo": (
        "A seguradora ofereceu REPARAR o seu vidro em vez de trocar. O reparo "
        "leva uns 30 minutos, mantem o vidro original do carro e normalmente "
        "sai sem franquia — eu confirmo o valor assim que a seguradora "
        "responder. Voce quer que eu aceite o reparo? " + _A_EQUIPE_ASSUME,
        "O portal ofereceu o reparo (`regras-reparo` -> ExibirDialogDeReparo=true) "
        "e a resposta do segurado nao foi coletada antes. NADA foi materializado "
        "alem do que ja existia. No portal: retome o atendimento pelo numero, "
        "responda o dialogo de reparo e siga ate a conclusao.",
    ),
    "peca_ambigua": (
        "Qual peca exatamente foi danificada? Com o nome certinho a seguradora "
        "pede a peca certa. " + _A_EQUIPE_ASSUME,
        "O texto da peca nao casou com UMA linha do catalogo daquela apolice "
        "(zero ou mais de uma). As opcoes reais estao no dossie. No portal: "
        "escolha o item coberto pelo numero do atendimento e siga.",
    ),
    "peca_de_lataria_ambigua": (
        "Me diz de que lado fica a peca amassada (motorista ou carona) e se e a "
        "da frente ou a de tras? " + _A_EQUIPE_ASSUME,
        "Uma das pecas de lataria casou com mais de um servico do catalogo. "
        "No portal: marque os servicos de martelinho pelo numero do atendimento.",
    ),
    "pecas_de_lataria_ausentes": (
        "Quais pecas ficaram amassadas? " + _A_EQUIPE_ASSUME,
        "`dano.pecas_lataria` veio vazio e a categoria e `L`. No portal: "
        "marque os servicos de martelinho e conclua.",
    ),
    "cidade_sem_rede": (
        "Na cidade que voce me passou a seguradora nao tem loja credenciada. "
        "Tem outra cidade onde voce consiga levar o carro? " + _A_EQUIPE_ASSUME,
        "`GET /clientes/cidades` nao devolveu rede para a cidade informada. A "
        "resposta do segurado E util: com outra cidade, a equipe altera o local "
        "no portal e conclui. Nao escolha a cidade por ele.",
    ),
    "cidade_ambigua": (
        "Confirma para mim a cidade e o estado onde voce quer fazer o servico? "
        + _A_EQUIPE_ASSUME,
        "O nome da cidade nao casou por IGUALDADE com a lista do portal. No "
        "portal: escolha a cidade na lista e conclua.",
    ),
    "uf_desconhecida": (
        "Confirma para mim o estado (a sigla, tipo SC ou PR) da cidade onde "
        "voce quer fazer o servico? " + _A_EQUIPE_ASSUME,
        "A UF informada nao esta na lista de `GET /ufs`.",
    ),
    "motivo_ambiguo": (
        "Me conta com mais detalhe como o dano aconteceu? A seguradora tem uma "
        "lista fechada de causas e eu preciso marcar exatamente a certa. "
        + _A_EQUIPE_ASSUME,
        "O relato nao e IGUAL a nenhuma causa de `motivos-dano` daquela peca. As "
        "opcoes reais estao no dossie. 🔴 Escolher por semelhanca ja gravou "
        "`QUEBRA INTENCIONAL` para quem disse `quebra acidental`. No portal: "
        "escolha a causa pelo numero do atendimento.",
    ),
    "questionario_incompleto": (
        "A seguradora fez uma pergunta sobre o seu vidro que eu nao respondo por "
        "voce. " + _A_EQUIPE_ASSUME,
        "O questionario trouxe uma pergunta sem resposta coletada. A pergunta "
        "literal e TODAS as opcoes estao no dossie. No portal: responda o "
        "questionario pelo numero e conclua.",
    ),
    "reparo_nao_gravado": (
        "Seu pedido esta aberto. A escolha entre reparar e trocar o vidro ainda "
        "nao foi registrada pela seguradora. " + _A_EQUIPE_ASSUME,
        "O `PUT /atendimentos/alterar-reparo` NAO confirmou. No portal: abra o "
        "atendimento pelo numero e confira o campo de reparo antes de concluir.",
    ),
    "desfecho_ilegivel": (
        "Seu pedido esta aberto na seguradora. Ainda nao consegui ler o que ela "
        "decidiu (loja, agendamento ou analise). " + _A_EQUIPE_ASSUME,
        "O `GET /atendimentos` depois de `opcoes-disponiveis` nao respondeu. 🔴 "
        "NAO reexecute: o pedido existe. No portal: abra pelo numero e leia a "
        "tela de conclusao.",
    ),
    "desfecho_desconhecido": (
        "Seu pedido esta aberto na seguradora. Ela seguiu por um caminho que eu "
        "ainda nao sei ler. " + _A_EQUIPE_ASSUME,
        "`opcoes-disponiveis` veio com combinacao fora do roteador conhecido "
        "(inclusive bloqueio por fraude ou ilha). O roteador inteiro esta no "
        "dossie. No portal: abra pelo numero e leia a tela.",
    ),
    "roteador_ilegivel": (
        "Seu pedido esta aberto na seguradora e ela ainda nao me disse o proximo "
        "passo. " + _A_EQUIPE_ASSUME,
        "`GET /agendamentos/opcoes-disponiveis` nao respondeu. NAO reexecute.",
    ),
    "corretor_recusado": (
        "Seu pedido foi aberto. Falta um dado do cadastro da corretora para a "
        "seguradora liberar a continuacao. " + _A_EQUIPE_ASSUME,
        "`PUT /atendimentos/corretores` recusou o documento. NAO reexecute: o "
        "atendimento ja existe. Confira o CNPJ no Perfil de Acionamento.",
    ),
    "solicitante_recusado": (
        "Seu pedido foi aberto. A seguradora recusou os dados de contato. "
        + _A_EQUIPE_ASSUME,
        "`POST /solicitantes` recusou. NAO reexecute. Confira telefone e e-mail.",
    ),
    "tipo_de_telefone_desconhecido": (
        "Seu pedido foi aberto. " + _A_EQUIPE_ASSUME,
        "`GET /tipos-telefone` nao trouxe o tipo esperado (CELULAR SEGURADO / "
        "CELULAR CORRETOR). O contrato do portal mudou. NAO reexecute.",
    ),
    "catalogo_indisponivel": (
        "Seu pedido foi aberto e a lista de pecas da sua apolice nao carregou. "
        + _A_EQUIPE_ASSUME,
        "`GET /apolices/itens-cobertos` nao respondeu. NAO reexecute.",
    ),
    "motivos_indisponiveis": (
        "Seu pedido foi aberto e a lista de causas nao carregou. "
        + _A_EQUIPE_ASSUME,
        "`GET /motivos-dano` nao respondeu. NAO reexecute.",
    ),
    "item_com_formato_desconhecido": (
        "Seu pedido foi aberto e a seguradora descreveu a peca de um jeito que "
        "eu nao reconheco. " + _A_EQUIPE_ASSUME,
        "`CodigoItemCoberto` fora do formato de 7 partes. NAO reexecute.",
    ),
    "patch_recusado": (
        "Seu pedido foi aberto e a seguradora recusou os dados do dano. "
        + _A_EQUIPE_ASSUME,
        "`PATCH /atendimentos` recusou. NAO reexecute.",
    ),
    "maybe_committed": (
        "Seu pedido foi enviado e eu nao consegui confirmar a resposta da "
        "seguradora. " + _A_EQUIPE_ASSUME,
        "🔴 `maybe_committed`: a chamada material saiu e a resposta se perdeu. "
        "NAO REEXECUTE em hipotese nenhuma — reexecutar cria um SEGUNDO pedido "
        "pago. Consulte o atendimento no portal antes de qualquer coisa.",
    ),
    "pronto_para_abrir": (
        "Esta tudo conferido e a sua apolice cobre. Falta so a autorizacao "
        "interna para eu abrir o pedido — ja pedi.",
        "O guard recusou a fronteira A (confirm/approval ausente). NADA foi "
        "aberto: este e o unico stage em que o pedido ainda NAO existe.",
    ),
    "pronto_para_materializar": (
        "Seu pedido esta aberto e falta a autorizacao interna para eu concluir "
        "— ja pedi. " + _A_EQUIPE_ASSUME,
        "O guard recusou a fronteira B/PATCH. O `NumeroProtocolo` ja existe.",
    ),
    "coverage_absent": (
        "A sua apolice nao tem a cobertura necessaria para essa peca, entao NAO "
        "abri nenhum pedido. Se quiser, eu confiro a apolice com voce.",
        "Preflight `coverage_absent`: detectado ANTES de qualquer escrita. "
        "Nenhum atendimento nasceu e nenhum vai nascer por este caminho.",
    ),
    "tela_desconhecida": (
        "Comecei a abrir o seu pedido e a seguradora mostrou uma tela que eu ainda não "
        "conheço. Prefiro não arriscar e te dar informação errada: já passei para a "
        "nossa equipe concluir na mão, com tudo o que você me contou. Te aviso assim "
        "que estiver aberto. 🙏",
        "Tela/resposta fora do contrato conhecido. Vai para a fila de aprendizado "
        "(`tela_cega`, ramo vidros) e para um humano concluir. NÃO reexecute sem "
        "conferir se o atendimento já existe.",
    ),
}
_PARADAS["desconhecido"] = _PARADAS["tela_desconhecida"]

# 🔴 SPEC-EXTRA-001.10.1 — as paradas que só a CONTINUAÇÃO produz (contrato §5).
# Nenhuma promete o que o produto não faz: a sessão caiu, o pedido segue válido
# e quem conclui é a equipe; o horário sumiu, eis os de agora.
_PARADAS.update({
    "sessao_expirada": (
        "O sistema da seguradora encerrou a sessão do seu pedido antes de eu "
        "concluir por aqui. O seu pedido continua valendo, com o mesmo número — "
        "quem conclui agora é a nossa equipe, direto com a seguradora, e você "
        "pode acompanhar pelo link da Área do Segurado que a seguradora te mandou. "
        "Você não precisa repetir nada.",
        "🔴 A continuação recebeu 401 no `GET /atendimentos`: o token do portal "
        "EXPIROU. NADA foi escrito. NAO reexecute a abertura (criaria um segundo "
        "pedido). No portal: abra o atendimento pelo numero e conclua o passo "
        "pendente (a etapa esta no dossie).",
    ),
    "sessao_indisponivel": (
        "Não consegui retomar o seu pedido no sistema da seguradora por aqui. Ele "
        "continua aberto, com o mesmo número — a nossa equipe conclui direto com a "
        "seguradora e eu te aviso. Você não precisa repetir nada.",
        "A sessao guardada do portal esta ausente ou nao decifrou (PORTAL_VAULT_KEY?). "
        "NADA foi escrito. No portal: abra pelo numero e conclua o passo pendente.",
    ),
    "horario_indisponivel": (
        # 🔴 COSTURA: dizia "…que eu agendo para você" SEMPRE — promessa sem a
        # prova da sessão (📊 pega pelo guarda B4 reescrito). Agora o convite a
        # continuar entra por `texto_da_parada`, só com `possivel is True`.
        "Esse horário acabou de ser ocupado na loja, então eu NÃO agendei nada. Me "
        "diz qual das opções de agora fica melhor para você. " + _A_EQUIPE_ASSUME,
        "A escolha do segurado nao estava mais entre os blocos publicados pelo "
        "portal. NADA foi agendado. As opcoes atuais estao no desfecho.",
    ),
    "atendimento_cancelado": (
        "A seguradora mostra este atendimento como cancelado, então eu não consigo "
        "continuar por aqui. Já passei para a nossa equipe conferir com a seguradora "
        "e te retornar.",
        "O agregado do portal voltou com `Cancelado=true`. NADA foi escrito. "
        "Confira com a seguradora antes de qualquer novo pedido.",
    ),
    "agendamento_nao_confirmado": (
        "Pedi o agendamento, mas a seguradora não confirmou. Para não correr o risco "
        "de marcar duas vezes, eu não vou repetir o pedido: a nossa equipe confere "
        "direto com a seguradora e te confirma. Não considere agendado até eu te "
        "confirmar.",
        "🔴 `POST /agendamentos` saiu e a releitura nao mostrou o agendamento no "
        "`ScriptFinalizacao`. NAO repita o agendamento: consulte o atendimento no "
        "portal e confirme com o segurado.",
    ),
    "decidir_vistoria": (
        "A seguradora vai fazer uma vistoria antes de liberar o serviço. Você "
        "prefere receber um link no celular para mandar as fotos, ou levar o carro "
        "numa loja? " + _A_EQUIPE_ASSUME,
        "O portal ofereceu a opcao de vistoria (`PermiteOpcaoVistoria`) e a "
        "preferencia do segurado nao foi coletada antes. No portal: registre a "
        "preferencia (link x loja) pelo numero e conclua.",
    ),
})

# 🔴 COSTURA (EXTRA-001.10.1) — as paradas que as fases novas da journey (A)
# produzem e que não tinham texto: sem ele, `format_result` caía na frase
# genérica do DOM ("técnico a domicílio ou uma das lojas"), que fala de uma
# tela que a API-first nem abre e de um domicílio que o produto não oferece
# (D-E001101-05). 📊 Medido pelo guarda B4 de `test_e00110_a_escada_e_a_
# seguradora`: 9 stages sem texto. Nenhum promete continuação — quem troca
# "a equipe assume" por "eu continuo" é `texto_da_parada`, e só com a prova.
_PARADAS.update({
    "agenda_ilegivel": (
        "Seu pedido está aberto na seguradora, mas a agenda da loja veio "
        "incompleta — então eu NÃO marquei horário nenhum. " + _A_EQUIPE_ASSUME,
        "A agenda publicada pelo portal veio sem campos que o `POST /agendamentos` "
        "exige (a lista esta no motivo). NADA foi agendado. No portal: abra o "
        "atendimento pelo numero e agende pela tela de agenda.",
    ),
    "pronto_para_agendar": (
        "Achei o horário na agenda da loja, mas ainda falta uma autorização interna "
        "para eu confirmar — então NÃO está agendado ainda. " + _A_EQUIPE_ASSUME,
        "O guard recusou a fronteira de agendamento (confirm/approval ausente ou "
        "freio de efeito material). NADA foi agendado. O horario casado esta no motivo.",
    ),
    "leitura_falhou": (
        "Seu pedido continua aberto na seguradora, com o mesmo número, mas o sistema "
        "dela não respondeu quando fui continuar. Nada foi alterado no pedido. "
        + _A_EQUIPE_ASSUME,
        "A continuacao nao conseguiu LER o atendimento (`GET /atendimentos` sem 200 "
        "e sem 401). NADA foi escrito. Pode reler; NAO reabra o pedido.",
    ),
    "agenda_nao_respondeu": (
        "Seu pedido está aberto na seguradora, mas o sistema dela não respondeu a "
        "agenda da loja agora — então eu NÃO agendei nada, e o horário que você "
        "escolheu continua anotado. " + _A_EQUIPE_ASSUME,
        "`datas-disponiveis`/`horarios-disponiveis` sem 200 (500/timeout) na hora "
        "de agendar a escolha do segurado. NADA foi agendado; a escolha esta no "
        "motivo. Pode reler/repetir a escolha; NAO e horario ocupado.",
    ),
    "operacao_desconhecida": (
        "Seu pedido continua aberto na seguradora, com o mesmo número. "
        + _A_EQUIPE_ASSUME,
        "A continuacao recebeu uma operacao fora do contrato (agendar, responder, "
        "reler, vistoria). NADA foi enviado ao portal. Defeito de integracao: "
        "confira o job de continuacao.",
    ),
    "prioridade_nao_medida": (
        "Seu pedido está aberto e a seguradora pediu uma informação sobre a urgência "
        "do atendimento que eu não respondo por você. " + _A_EQUIPE_ASSUME,
        "O portal pediu a prioridade num caso nunca medido (veiculo de carga ou "
        "resposta ilegivel de `atendimentos-prioridades`). NADA foi gravado. No "
        "portal: abra pelo numero, responda a prioridade e a preferencia de vistoria.",
    ),
    "pronto_para_vistoria": (
        "Anotei a sua preferência para a vistoria e falta uma autorização interna "
        "para eu registrá-la na seguradora. " + _A_EQUIPE_ASSUME,
        "O guard recusou a fronteira de prioridade/ocorrencia. NADA foi gravado. No "
        "portal: registre a preferencia (loja x link) pelo numero do atendimento.",
    ),
    "vistoria_nao_confirmada": (
        "Registrei a sua preferência para a vistoria, mas a seguradora não confirmou. "
        "Para não registrar duas vezes, eu não vou repetir. " + _A_EQUIPE_ASSUME,
        "🔴 `POST /atendimentos-prioridades` ou `/ocorrencias` saiu e NAO confirmou. "
        "NAO repita (duas prioridades/ocorrencias nao se desfazem): consulte o "
        "atendimento no portal antes de qualquer coisa.",
    ),
    "reconciliar_antes": (
        "Seu pedido foi enviado à seguradora e eu não consegui confirmar a última "
        "etapa. Para não duplicar nada, eu não vou repetir. " + _A_EQUIPE_ASSUME,
        "🔴 A origem parou em `maybe_committed` e o agregado ainda nao mostra o "
        "numero do atendimento. NADA foi repetido. Consulte o atendimento no portal "
        "ANTES de qualquer nova tentativa.",
    ),
    "sessao_de_outro_atendimento": (
        "Não consegui retomar o seu pedido por aqui. Ele continua aberto na "
        "seguradora, com o mesmo número — a nossa equipe conclui direto com a "
        "seguradora e eu te aviso. Você não precisa repetir nada.",
        "🔴 A sessao guardada abriu OUTRO atendimento (codigo diferente do deste "
        "pedido). NADA foi escrito. Investigue: a sessao pode ter sido trocada entre "
        "pedidos. No portal: conclua este pedido pelo numero.",
    ),
})

#: O que substitui "a equipe assume" quando a continuação é POSSÍVEL.
_EU_CONTINUO = ("Me responde por aqui que eu continuo o seu pedido de onde parou "
                "— você não precisa repetir nada.")
_EU_TENTO_DE_NOVO = ("Já estou tentando de novo por aqui, pelo mesmo pedido — te "
                     "aviso assim que a seguradora responder. Você não precisa "
                     "repetir nada.")


def _cabecalho_do_numero(ev: dict) -> str:
    """A primeira linha de toda parada: o numero, quando ele existe.

    📊 Medido nas 4 capturas: o `CodigoAtendimento` tem 8 digitos e e o que a
    tela mostra; o `NumeroProtocolo` tem 16 e e interno. Chamar o de 16 de
    "numero do atendimento" faz o segurado citar no telefone um numero que a
    seguradora nao encontra.
    """
    e = ev if isinstance(ev, dict) else {}
    estado = e.get("vidros_estado") if isinstance(e.get("vidros_estado"), dict) else {}
    desfecho = e.get("desfecho") if isinstance(e.get("desfecho"), dict) else {}
    numero = ""
    for bruto in (desfecho.get("codigo_atendimento"), e.get("protocolo"),
                  e.get("codigo_atendimento"), estado.get("codigo_atendimento")):
        texto = "".join(ch for ch in str(bruto or "") if ch.isdigit())
        if len(texto) == 8:
            numero = texto
            break
    if numero:
        return (f"NUMERO DO ATENDIMENTO: {numero} — DIGA ESSE NUMERO AO SEGURADO "
                "ANTES DE QUALQUER OUTRA COISA; e com ele que ele acompanha e "
                "cobra o servico.\n\n")
    interno = "".join(ch for ch in str(e.get("protocolo") or "") if ch.isdigit())
    if len(interno) >= 12:
        return (f"PROTOCOLO INICIAL (interno): {interno}. ⚠️ NAO e o numero do "
                "atendimento e NAO adianta cita-lo por telefone — serve para a "
                "nossa equipe achar o pedido no portal.\n\n")
    return ""


def _frase_de_gente(texto) -> str:
    """"QUAL O LADO DO ITEM DANIFICADO?" -> "Qual o lado do item danificado?"."""
    t = " ".join(str(texto or "").split())
    return (t[:1].upper() + t[1:].lower()) if t else ""


def texto_da_parada(stage: Optional[str],
                    continuacao_possivel: bool = False) -> Optional[Tuple[str, str]]:
    """(o que o segurado lê, o que a equipe lê). None = parada sem texto próprio.

    🔴 SPEC-EXTRA-001.10.1 — com `continuacao_possivel` (e SÓ com ele, prova da
    journey), as paradas que a continuação resolve trocam "a equipe assume" por
    "me responde que eu continuo" (as do segurado) ou "já estou tentando de
    novo" (as técnicas, que o vigia relê). Sem a prova, o texto de hoje.
    """
    chave = str(stage or "").strip().lower()
    par = _PARADAS.get(chave)
    if not par or continuacao_possivel is not True:
        return par
    para_ele, para_equipe = par
    if chave in ESTAGIOS_QUE_O_SEGURADO_RESPONDE:
        return para_ele.replace(_A_EQUIPE_ASSUME, _EU_CONTINUO), para_equipe
    if chave in ESTAGIOS_TECNICOS:
        return para_ele.replace(_A_EQUIPE_ASSUME, _EU_TENTO_DE_NOVO), para_equipe
    return par


# ===========================================================================
# P-PILOTO-08 — o que vai para a FILA DE APRENDIZADO, e como
# ===========================================================================
#
# 🔴 PURO, e é o que o torna provável offline: quem decide "isto é tela
# desconhecida" não toca em banco nem em rede. A gravação é do chamador
# (`portal_tool` dentro da janela de 150s · `vigia_do_portal` fora dela), e os
# dois usam ESTA função — duas definições de "desconhecido" fariam a fila
# receber do caminho A e não receber do caminho B, sem ninguém notar.

#: Os desfechos que a journey sabe traduzir. Qualquer outro é aprendizado.
_DESFECHOS_CONHECIDOS = ("loja_direta", "agenda", "analista", "vistoria",
                         # SPEC-EXTRA-001.10.1 — os tipos novos do contrato A→C.
                         "agendado", "vistoria_opcional", "decidir_vistoria")

#: Quanto do texto do portal entra na fila. A tela é para uma pessoa LER e
#: transformar em passo; 1200 caracteres já são mais do que ela consegue ler.
_TETO_DO_RESUMO = 1200


def slug_da_seguradora(params: Optional[dict]) -> str:
    """O `insurer_key` da fila de aprendizado, a partir do nome da seguradora.

    ⛔ Nunca uma constante de corretora nem uma lista fixa de seguradoras
    (CLAUDE.md §13.9): o nome vem do `params` daquele job, que veio da apólice
    daquela `company_id`. Nome vazio vira `desconhecida`, que é uma informação —
    a fila mostra que chegou tela de alguém que não soubemos nomear.
    """
    nome = _fold((params or {}).get("insurer_name")).strip().lower()
    slug = "_".join(p for p in "".join(
        c if c.isalnum() else " " for c in nome).split())
    return slug or "desconhecida"


def _o_job_deu_certo(ev: dict) -> bool:
    """Ha prova de que o acionamento terminou bem? Entao nao ha o que aprender.

    Tres provas, e basta uma: desfecho conhecido, numero de atendimento, ou a
    marca de sucesso do caminho DOM. ⛔ Um job com `tela_desconhecida` explicita
    NUNCA e considerado sucesso, mesmo com numero: e o caso em que o pedido
    existe E a tela era nova.
    """
    e = ev if isinstance(ev, dict) else {}
    if isinstance(e.get("tela_desconhecida"), dict) and e.get("tela_desconhecida"):
        return False
    desfecho = e.get("desfecho") if isinstance(e.get("desfecho"), dict) else {}
    if str(desfecho.get("tipo") or "").strip().lower() in _DESFECHOS_CONHECIDOS:
        return True
    if str(e.get("protocolo") or "").strip():
        return True
    estado = e.get("vidros_estado") if isinstance(e.get("vidros_estado"), dict) else {}
    return bool(estado.get("tem_codigo_atendimento"))


def resumo_da_tela_desconhecida(evidence: Optional[dict]) -> Optional[dict]:
    """`{"onde", "texto"}` quando este job tem algo a ENSINAR. `None` quando não.

    Três entradas, e as três já existem no produto:

      `tela_desconhecida`  o caminho API disse, em contrato, que não entendeu
      `desfecho.tipo`      veio um tipo fora dos quatro que sabemos traduzir
      `debug_dom`/`final`  o caminho DOM parou sem desfecho conhecido

    ⛔ O texto tem de chegar aqui **já mascarado** pela origem (SPEC-087
    BLOCO C): escrever cru e mascarar depois é criar o vazamento e tapá-lo. Por
    isso esta função nunca inventa texto — ela só ESCOLHE qual dos resumos que a
    journey produziu vai para a fila, e corta no teto.
    """
    ev = evidence if isinstance(evidence, dict) else {}
    if not ev:
        return None

    # 🔴 JUIZ B1 — REGRESSAO EM PRODUCAO COM A FLAG DESLIGADA, 20/09/2026.
    #
    # 📊 O caminho DOM grava `evidence["final"]` na tela de SUCESSO (passo 7).
    # Como este leitor caia em ("debug_dom", "final") no fim, **todo job DOM
    # `done` virava linha de tela cega** — e o `_aprender_com_a_tela_cega`
    # regravava a evidence LIDA ANTES, apagando a marca `entregue_ao_agente`.
    # Resultado: o Vigia mandava uma SEGUNDA mensagem ao segurado.
    #
    # A porta que fecha isso e esta, e ela e a primeira coisa do arquivo:
    # trabalho que DEU CERTO nao ensina nada.
    if _o_job_deu_certo(ev):
        return None

    marca = ev.get("tela_desconhecida")
    if isinstance(marca, dict):
        texto = str(marca.get("resumo_mascarado") or marca.get("resumo") or "").strip()
        onde = str(marca.get("onde") or "api").strip() or "api"
        if texto:
            return {"onde": onde, "texto": texto[:_TETO_DO_RESUMO]}

    desfecho = ev.get("desfecho") if isinstance(ev.get("desfecho"), dict) else None
    if desfecho is not None:
        tipo = str(desfecho.get("tipo") or "").strip().lower()
        if tipo in _DESFECHOS_CONHECIDOS:
            # 🔴 O PAR DE CONTROLE do guarda: desfecho conhecido NÃO ensina nada.
            # Sem esta saída, todo acionamento bem-sucedido entraria na fila e a
            # fila deixaria de ser fila de trabalho.
            return None
        titulo = str(desfecho.get("titulo_portal") or "").strip()
        roteador = desfecho.get("roteador")
        corpo = titulo or (f"roteador: {roteador}" if roteador else "")
        if corpo:
            return {"onde": f"desfecho_{tipo or 'sem_tipo'}",
                    "texto": corpo[:_TETO_DO_RESUMO]}

    # O caminho DOM: parou numa tela e guardou o que viu. Só vira aprendizado
    # quando NÃO há desfecho conhecido — senão a tela de sucesso entra na fila.
    for chave in ("debug_dom", "final"):
        bruto = ev.get(chave)
        texto = str(bruto if isinstance(bruto, str) else (bruto or {}).get("texto")
                    if isinstance(bruto, dict) else "").strip()
        if texto:
            return {"onde": chave, "texto": texto[:_TETO_DO_RESUMO]}
    return None


def format_result(job: dict) -> str:
    """Traduz o job terminado para uma frase natural para o agente.

    🔴 O NUMERO VEM PRIMEIRO, EM QUALQUER STATUS.

    📊 O `Nº do atendimento` nasce no passo 7, no topo da tela, ANTES da escolha
    da loja (mapa §7). Logo o pedido pode EXISTIR na seguradora num job que
    terminou `needs_human` (travou depois) ou ate `failed` (o navegador caiu
    depois). Nesses casos o segurado tem um atendimento aberto — e a unica coisa
    que o torna rastreavel e este numero chegar ate ele.

    Por isso a checagem do protocolo vem ANTES do `switch` de status: amarrar o
    numero ao status `done` faria o caso mais perigoso (pedido aberto + fluxo
    quebrado) ser justamente o unico que nao o diria.

    E a frase avisa para NAO reexecutar: repetir o fluxo cria um SEGUNDO
    atendimento, e isso nao se desfaz (mapa §9.5).
    """
    status = str((job or {}).get("status") or "")
    ev = (job or {}).get("evidence") or {}
    protocolo = str(ev.get("protocolo") or "").strip()

    # ----------------------------------------------------------------------
    # 🔴 SPEC-EXTRA-001.10 N-1 — O DESFECHO VEM ANTES DE TUDO.
    #
    # Quando a journey leu o roteador do portal, ela já sabe MAIS do que
    # qualquer heurística daqui: o número, a franquia linha a linha, a loja
    # atribuída ou as lojas com agenda. Deixar o desfecho para depois do
    # `switch` de status faria o caso mais completo ser respondido pela frase
    # mais genérica — e o segurado receberia "cheguei numa etapa que precisa de
    # revisão" sobre um pedido que o portal já concluiu.
    # ----------------------------------------------------------------------
    pode_continuar = continuacao_possivel(ev)
    parada = texto_da_parada(ev.get("stage"), pode_continuar)
    if parada and status in ("needs_human", "failed"):
        para_ele, para_equipe = parada
        opcoes = [str(o)[:60] for o in (ev.get("opcoes") or [])][:12]
        extra = f"\nOpcoes que o portal ofereceu: {', '.join(opcoes)}" if opcoes else ""
        pergunta = str(ev.get("pergunta") or "").strip()
        if pergunta:
            extra += f"\nO portal perguntou, literalmente: \"{pergunta[:180]}\""
        # 🔴 O NUMERO VEM PRIMEIRO — juiz B4 / red B6, 20/09/2026.
        #
        # Toda parada DEPOIS da fronteira A acontece com o pedido ja existindo.
        # 📊 O laudo mediu paradas cujo texto nao trazia numero nenhum: o
        # segurado ouvia "seu pedido esta aberto" e nao tinha o que anotar, e a
        # equipe nao sabia por qual atendimento procurar no portal.
        #
        # ⚠️ E os dois numeros NAO sao a mesma coisa: o `CodigoAtendimento` (8
        # digitos) e o que a tela mostra e o segurado repete no telefone; o
        # `NumeroProtocolo` (16) e interno e NAO adianta no telefone. Apresentar
        # um pelo outro e mandar a pessoa citar um numero que ninguem acha.
        cabecalho = _cabecalho_do_numero(ev)
        # 🔴 COSTURA (EXTRA-001.10.1): com a continuação possível, o segurado é
        # convidado a RESPONDER — então ele precisa LER a pergunta. 📊 Medido na
        # costura: em `questionario_incompleto` o texto dele dizia "a seguradora
        # fez uma pergunta… me responde que eu continuo" e a pergunta literal só
        # aparecia no bloco "[para a equipe, nao mande ao segurado]".
        if (pode_continuar and pergunta
                and str(ev.get("stage") or "").strip().lower() in ESTAGIOS_QUE_O_SEGURADO_RESPONDE):
            para_ele += "\n\nA pergunta da seguradora: " + _frase_de_gente(pergunta[:180])
            if opcoes:
                para_ele += "\nAs opções dela: " + ", ".join(_frase_de_gente(o) for o in opcoes)
        # 🔴 SPEC-EXTRA-001.10.1 — o horário sumiu: as opções DE AGORA vão junto,
        # da mesma fonte da agenda (nenhuma opção inventada).
        desf_atual = ev.get("desfecho") if isinstance(ev.get("desfecho"), dict) else {}
        agenda_atual = (_bloco_da_agenda(desf_atual, pode_continuar)
                        if str(ev.get("stage") or "").strip().lower() == "horario_indisponivel"
                        else "")
        return (
            cabecalho + "O pedido PAROU numa etapa que precisa de uma resposta. "
            "DIGA AO SEGURADO, com estas palavras:\n\n" + para_ele
            + (("\n\n" + agenda_atual) if agenda_atual else "")
            + "\n\n[para a equipe, nao mande ao segurado] " + para_equipe + extra
            + instrucao_de_continuacao(ev)
        )

    desfecho = ev.get("desfecho") if isinstance(ev.get("desfecho"), dict) else None
    if desfecho:
        corpo = mensagem_do_desfecho(desfecho, continuacao_da_evidencia(ev))
        if corpo:
            numero = str(desfecho.get("codigo_atendimento") or "").strip()
            aviso = ("NAO peca para eu abrir de novo: o pedido ja existe e repetir "
                     "criaria um segundo atendimento na seguradora, que nao se desfaz.")
            aviso += instrucao_de_continuacao(ev)
            if (str(desfecho.get("tipo") or "").strip().lower() in ("desconhecido", "vistoria")
                    and not pode_continuar):
                aviso += (" Este caso VAI para a equipe humana: mande o dossie e diga ao "
                          "segurado, com estas palavras, o que esta abaixo.")
            return (
                "O atendimento FOI ABERTO na seguradora"
                + (f" (numero {numero})." if numero else ".")
                + " ENTREGUE AO SEGURADO A MENSAGEM ABAIXO, com estas palavras — ela ja "
                  "esta em portugues de gente e tem tudo o que ele precisa. Numero, "
                  "valor, telefone e link se copiam EXATOS.\n\n"
                + corpo
                + "\n\n" + aviso
            )

    # A parada tem texto próprio? Então ele vence a frase genérica de
    # `needs_human` — que é verdadeira e inútil ("uma etapa que precisa de
    # revisão" não diz ao segurado o que fazer).
    # 🔴 P1: a parada vence o ramo do desfecho quando ha as duas coisas. Um
    # `desfecho_ilegivel` com `evidence["desfecho"]` preenchido (tipo
    # `desconhecido`) caia no escritor do desfecho e perdia o cabecalho do
    # numero — justo nas duas paradas em que o pedido JA EXISTE.

    # ----------------------------------------------------------------------
    # SPEC-074 — o ESTADO DE NEGÓCIO vem antes do estado técnico.
    #
    # 🔴 O caminho API-first cria o pedido em DUAS fronteiras, e a segunda
    # produz o `CodigoAtendimento` — que é o número que a tela mostra e que o
    # extrator de texto grava em `evidence.protocolo`. Quando a journey roda
    # pela API, o número chega em `evidence.vidros_estado`, não pelo texto.
    #
    # Sem esta ponte, um job que criou o pedido pela API e falhou depois cairia
    # no ramo `failed` e diria "não consegui abrir" — exatamente o defeito que a
    # SPEC-074 P1 descreve, e o pior que se pode dizer a alguém cujo pedido
    # existe.
    #
    # A regra "o número vem primeiro" é preservada: este bloco só ACRESCENTA
    # uma segunda fonte para o mesmo número, nunca desloca a checagem original.
    # ----------------------------------------------------------------------
    est = ev.get("vidros_estado") if isinstance(ev.get("vidros_estado"), dict) else {}
    if not protocolo and est.get("tem_codigo_atendimento"):
        protocolo = str(est.get("codigo_atendimento") or "").strip()
    if not protocolo and est.get("existe_algo_na_seguradora"):
        # Existe pedido e não temos o número: dizer "não abriu" seria mentira, e
        # inventar um número seria pior. A frase fala a verdade incômoda.
        return ("O pedido FOI aberto no portal, mas não consegui ler o número do "
                "atendimento. NÃO reexecute — reabrir criaria um segundo pedido. "
                "Avise o segurado que a solicitação existe e que o número virá "
                "em seguida, e encaminhe para conferência humana.")

    if protocolo:
        passo7 = ev.get("passo7") if isinstance(ev.get("passo7"), dict) else {}
        recomendacao = str(passo7.get("recomendacao") or "").strip()
        if not recomendacao:
            # 🔴 RED B5 (conserto da 001.10.1) — D-E001101-05: domicílio FORA.
            # O caminho DOM (produção com a flag desligada) oferecia "técnico a
            # domicílio" ao segurado; o produto não entrega mais essa opção.
            recomendacao = ("Confirme com o segurado qual loja credenciada ele prefere "
                            "— essa escolha e dele, e ela ainda esta em aberto.")
        # 🔴 OS OUTROS DOIS DADOS DA MESMA TELA — SPEC-071 BLOCO 6, 15/08/2026.
        #
        # 📊 A tela traz TRES coisas e so o protocolo chegava ao segurado:
        # a FRANQUIA (quanto ele paga) e o LINK DA VISTORIA (por onde ele manda
        # as fotos) ficavam no portal, obrigando a atendente a abri-lo.
        #
        # ⚠️ Cada um so aparece se foi LIDO. Frase sobre franquia sem franquia
        # lida seria o agente inventando valor — e valor inventado numa conversa
        # de seguro e o segurado descobrindo na hora de pagar.
        franquia = str(ev.get("franquia") or "").strip()
        link = str(ev.get("link_vistoria") or "").strip()
        extras = ""
        if franquia:
            extras += (f" A FRANQUIA e R$ {franquia} — diga o valor ao segurado ANTES "
                       "de ele escolher onde fazer o servico, porque e ele quem paga.")
        if link:
            extras += (f" As fotos do veiculo vao por este link: {link} — mande-o ao "
                       "segurado exatamente como esta, sem encurtar nem reescrever.")
        return (
            f"O atendimento FOI ABERTO na seguradora. Numero do atendimento: {protocolo}. "
            f"DIGA ESSE NUMERO AO SEGURADO — e com ele que ele acompanha e cobra o servico."
            f"{extras} "
            f"{recomendacao} "
            "NAO peca para eu abrir de novo: o pedido ja existe e repetir criaria um segundo "
            "atendimento na seguradora, que nao se desfaz."
        ).strip()
    if status == "done":
        return f"Acionamento concluido no portal. {ev.get('message') or 'protocolo gerado'}".strip()
    if status == "needs_human":
        stage = str(((job or {}).get("evidence") or {}).get("stage_80") or "")
        captured = (ev.get("message") or "").lower()
        if stage or "80%" in captured or "confirmacao" in captured:
            return ("Abri o pedido no portal com os dados da apolice e cheguei ate a etapa final de "
                    "confirmacao da peca — falta so a aprovacao final para enviar. Diga isso ao cliente "
                    "com clareza (pedido aberto, em confirmacao final).")
        opts = ev.get("opcoes")
        base = ev.get("message") or "o portal parou numa etapa que preciso confirmar"
        if opts:
            return f"No portal, preciso decidir '{ev.get('campo')}' entre: {', '.join(opts[:12])}. ({base})"
        return f"Cheguei ate uma etapa que precisa de revisao no portal ({base})."
    if status == "failed":
        return f"Nao consegui concluir no portal: {job.get('error') or ev.get('message') or 'erro'}."
    return "Enfileirei o acionamento; o worker de portais ainda nao processou (o acesso a portais esta desligado?)."


# ===========================================================================
# SPEC-065 bloco 7.2 — o portal nunca abre duas vezes o mesmo pedido.
#
# 📊 O `Nº do atendimento` nasce no passo 7, no TOPO da tela, antes da escolha
# da loja (docs/canon/O-PORTAL-DE-VIDROS-TELA-POR-TELA.md §7). O pedido ja
# existe na seguradora antes de o fluxo terminar — reexecutar nao corrige, cria
# um SEGUNDO atendimento.
#
# 📊 E ja aconteceu, em escala: 39 jobs `abrir_atendimento` para 5 pedidos
# distintos (Supabase dcajcvlzcjbmyapmklil, 04/08/2026). Um unico pedido tem 30
# jobs. Nao machucou ninguem so porque o gate do worker esta desligado.
#
# A chave identifica o PEDIDO, nao o job: corretora + placa + peca + data do
# dano. Logica pura aqui para poder ser testada sem banco, sem langchain e sem
# LLM — o guarda que so existe dentro do `_arun` e um guarda que ninguem
# consegue provar.
# ===========================================================================

_CHAVE_VERSAO = "v1"

# "vidro DA porta" e "vidro DE porta" sao a mesma peca. Estas palavras so ligam
# as outras; se ficarem na chave, viram dois pedidos que sao um.
_LIGACOES = frozenset({
    "de", "da", "do", "das", "dos", "e", "a", "o", "as", "os",
    "no", "na", "nos", "nas", "em", "um", "uma", "ao", "aos", "com",
})

_PECA_MAX = 80  # limita a entrada do indice; o LLM as vezes escreve uma frase


def normalizar_peca(texto: Optional[str]) -> str:
    """A peca como IDENTIDADE, nao como texto.

    Tira acento, caixa e pontuacao; joga fora as palavras de ligacao; ordena o
    que sobra. 'Vidro da Porta', 'vidro de porta' e 'porta - vidro' viram a
    mesma coisa.

    O que NAO e jogado fora, de proposito: os qualificadores. 'dianteira',
    'traseira', 'esquerdo', 'direito' e 'motorista' continuam na chave, porque
    o portal exige um pedido por item e por lado (§3 do mapa) — dois vidros
    quebrados sao dois atendimentos, e uma chave que os fundisse deixaria um
    lado quebrado sem ninguem saber.

    Ordenar e seguro aqui e nao noutro lugar: para dois pedidos DIFERENTES
    colidirem depois da ordenacao, eles teriam de ser anagramas de token — e
    peca diferente sempre troca uma palavra (dianteira/traseira), nunca so a
    ordem delas.
    """
    bruto = _fold(texto).lower()
    palavras = sorted(
        p for p in ("".join(c if c.isalnum() else " " for c in bruto)).split()
        if p and p not in _LIGACOES
    )
    return " ".join(palavras)[:_PECA_MAX]


def normalizar_placa(texto: Optional[str]) -> str:
    """'aaa-0a91' e 'AAA0A91' sao o mesmo carro. So alfanumerico, maiusculo."""
    return "".join(c for c in _fold(texto).upper() if c.isalnum())


def normalizar_data(texto: Optional[str]) -> str:
    """'5/7/2026', '05-07-2026' e '05/07/2026' sao o mesmo dia.

    Nao vira digito puro: '5/7/2026' -> '572026' e '05/07/2026' -> '05072026'
    dariam chaves diferentes para a mesma data. Zero-padding resolve; formato
    que nao seja de tres partes cai no digito puro, que ao menos e estavel.
    """
    partes = [p for p in ("".join(c if c.isdigit() else " " for c in str(texto or ""))).split() if p]
    if len(partes) == 3:
        d, m, a = partes
        if len(a) == 2:
            a = "20" + a
        return f"{d.zfill(2)}{m.zfill(2)}{a.zfill(4)}"
    return "".join(partes)


def chave_de_idempotencia(params: Optional[dict], company_id: Optional[str] = None) -> str:
    """A impressao digital do PEDIDO. String vazia = sem chave (nao bloqueia nada).

    `company_id` vem separado porque `build_portal_params` nao o coloca em
    `params` — e mexer nela nao e desta tarefa. Aceita tambem `params['company_id']`
    para quem ja o tiver embutido.

    O que entra: corretora, placa, peca normalizada, data do dano.
    O que NAO entra, e por que:

      · a descricao livre — o segurado reconta a mesma historia com outras
        palavras ("quebraram o vidro" / "encontrei o carro arrombado") e isso
        criaria pedidos "diferentes" que sao o mesmo. Justamente o erro que
        custa caro: um segundo atendimento na seguradora nao se desfaz.
      · o `como_ocorreu` e o `onde_ocorreu` — mesma razao, sao julgamento do
        LLM sobre o mesmo fato.
      · a seguradora — ela e DERIVADA da apolice, que e derivada da placa. Se o
        `normalize_insurer` mudar de opiniao entre duas chamadas (Liberty ->
        Yelum), a chave mudaria sozinha e o guarda sumiria em silencio.
      · o CPF — tambem derivado: e o titular da apolice daquela placa.

    Retorna "" quando falta corretora, placa ou data — sem esses tres nao ha
    pedido para identificar, e uma chave meia-boca fundiria pedidos de carros
    diferentes. Na pratica e inalcancavel: `build_portal_params` ja recusa sem
    placa e sem data, e a tool sempre tem company_id. Fail-open de proposito:
    o guarda nunca pode ser o motivo de um atendimento nao acontecer.
    """
    params = params or {}
    empresa = str(company_id or params.get("company_id") or "").strip()
    placa = normalizar_placa(params.get("placa"))
    data = normalizar_data(params.get("data_dano"))
    if not (empresa and placa and data):
        return ""
    peca = normalizar_peca((params.get("dano") or {}).get("peca"))

    # 🔴 O LADO ENTRA NA CHAVE — SPEC-074, fechando a P-79.
    #
    # 📊 O portal diz, em texto na tela: *"se o item possuir lateralidade será
    # necessário abrir uma nova solicitação para o outro lado"*. Dois vidros
    # quebrados são DOIS pedidos legítimos.
    #
    # Sem o lado aqui, o segundo era barrado como repetição — e o segurado só
    # descobria quando o vidraceiro trocasse um vidro e fosse embora. A frase de
    # "já existe" ensinava a saída (*descreva a peça com o lado*), mas depender
    # de o modelo escrever a frase certa é exatamente o que esta SPEC desfaz.
    #
    # Só entra quando o lado NÃO está na peça: `normalizar_peca` já preserva
    # qualificadores (`esquerdo`, `motorista`, `dianteira`), então repetir aqui
    # criaria duas chaves para o mesmo pedido descrito de dois jeitos.
    lado = ""
    especificos = params.get("especificos")
    if isinstance(especificos, dict):
        bruto = str(especificos.get("lado_motorista_ou_carona") or "").strip()
        if bruto:
            marca = "motorista" if "motorista" in _fold(bruto) else (
                "carona" if "carona" in _fold(bruto) else _fold(bruto)[:16])
            if marca and marca not in peca:
                lado = marca

    # A versão sobe para `v2` porque a chave mudou de significado para peças com
    # lateralidade. As chaves `v1` históricas deixam de casar — e isso é o
    # desfecho desejado: 📊 são 34 jobs de julho, nenhum concluído, e um deles
    # bloquear um pedido legítimo de hoje é o defeito, não a proteção.
    return f"v2:{empresa}:{placa}:{data}:{peca}" + (f":{lado}" if lado else "")


def frase_de_pedido_ja_existente(job: Optional[dict], resposta_nova: bool = False) -> str:
    """O que o agente diz quando o pedido JA existe — sem mentir.

    Nao inventa protocolo nem status: para um job que TERMINOU, o fato vem de
    `format_result` sobre o job real. Para um job ainda em curso o fato e
    omitido de proposito — `format_result` diria "Enfileirei o acionamento", e
    nesta chamada nada foi enfileirado; a frase mentiria sobre quem fez o que.

    O que esta funcao acrescenta e a explicacao de por que NAO abrimos outro, e
    a saida legitima para o caso em que o segurado realmente tem um segundo
    pedido (outra peca, outro lado).
    """
    job = job or {}
    status = str(job.get("status") or "")
    outro_pedido = (
        "Se o segurado quebrou OUTRA peca ou o OUTRO lado, isso e um pedido "
        "separado (o portal so aceita um item por atendimento): descreva a peca "
        "com o lado — ex.: 'vidro da porta traseira esquerda' — e chame de novo."
    )
    if status in ("done", "needs_human"):
        # 🔴 SPEC-EXTRA-001.10.1 — a resposta nova que NÃO tem como continuar.
        # Sem sessão guardada (ou sem nada que responda o que o pedido espera),
        # a verdade é uma só: este pedido segue com a equipe. Dizer "anotei" e
        # calar seria o segurado esperando uma continuação que não vem.
        honesto = (
            " O segurado trouxe uma resposta nova, mas este pedido NAO pode ser "
            "continuado por aqui (a seguradora nao deixou a sessao dele aberta para "
            "mim). Diga a ele, com estas palavras: \"Anotei. O seu pedido continua "
            "aberto com o mesmo número, e quem conclui este passo é a nossa equipe, "
            "direto com a seguradora — eu te aviso assim que estiver resolvido.\" "
            "E NAO chame de novo com a mesma resposta."
        ) if resposta_nova else ""
        return (
            "Ja existe um atendimento aberto para este mesmo veiculo, peca e data do dano. "
            "NAO abri outro: o numero do atendimento nasce antes do fim do fluxo no portal, "
            "entao repetir criaria um SEGUNDO atendimento na seguradora, e isso nao se desfaz. "
            f"{format_result(job)} Repasse esse resultado ao segurado.{honesto} {outro_pedido}"
        )
    return (
        "Ja existe um acionamento EM ANDAMENTO para este mesmo veiculo, peca e data do dano — "
        "nao abri outro. Diga ao segurado que o pedido dele ja esta em curso e que voce avisa "
        f"assim que houver resposta. {outro_pedido}"
    )


# ===========================================================================
# 🔴 SPEC-EXTRA-001.10.1 C1 — A CONTINUAÇÃO: o MESMO pedido, nunca um segundo
# ===========================================================================
#
# 📊 Até 23/09/2026 a tool criava UM job `abrir_atendimento` e, quando o pedido
# parava depois do protocolo (peça ambígua, cidade, agenda para escolher,
# vistoria…), toda frase dizia "a equipe assume": não havia continuação. Agora a
# journey `vidros_lanternas.continuar_atendimento` (builder A) retoma com o token
# guardado CIFRADO em `evidence["continuacao"]["sessao_cifrada"]`.
#
# Tudo abaixo é PURO: monta a linha do job e a chave; quem escreve no banco é
# `portal_tool.enfileirar_continuacao` — um helper só, usado pela tool e pelo
# vigia (nada duplicado).
#
# Modelo (SPEC §8): Stripe — Idempotent requests. A continuação tem chave
# PRÓPRIA (empresa + protocolo + operação + o que foi respondido); reaproveitar
# a chave de criação faria o guarda achar que "o pedido já existe" e recusar a
# continuação legítima.

PORTAL_VIDROS = "vidros_lanternas"
JOURNEY_CONTINUAR = "continuar_atendimento"

#: Como a resposta VOLTA para a tool, por slot do contrato. O slot `peca` NÃO
#: volta pelo campo de topo: 🔴 `peca` entra na chave do pedido
#: (`chave_de_idempotencia`), e mudá-la lá faria a tool achar um pedido NOVO —
#: o segundo atendimento que esta SPEC existe para impedir.
_CAMPO_DO_SLOT = {
    "cidade_servico": "especificos.cidade_para_o_servico (cidade e estado, ex.: Joinville/SC)",
    "cidade_para_o_servico": "especificos.cidade_para_o_servico (cidade e estado, ex.: Joinville/SC)",
    "como": "como_ocorreu (UMA das causas da lista, escrita igual)",
    "como_ocorreu": "como_ocorreu (UMA das causas da lista, escrita igual)",
    "peca": "especificos.peca (a peca exata; o campo `peca` de cima fica IGUAL)",
    "pecas_lataria": "especificos.pecas_lataria (a LISTA de pecas)",
    "aceita_reparo": "especificos.aceita_reparo (sim ou nao)",
}


def instrucao_de_continuacao(evidence) -> str:
    """A linha, só para o AGENTE, que ensina como a resposta volta. "" quando o
    pedido não pode continuar — aí não há o que ensinar, e ensinar seria
    convidar a chamada que não vai a lugar nenhum."""
    if not continuacao_possivel(evidence):
        return ""
    operacao, slot = acao_esperada(evidence)
    base = ("\n\n[para voce, agente] Este pedido PODE CONTINUAR por aqui — a ferramenta "
            "retoma o MESMO atendimento na seguradora, nunca abre outro. ")
    if operacao == "agendar":
        return base + ("Quando o segurado escolher, chame portal_action de novo com os "
                       "MESMOS dados de antes e especificos.escolha_agenda = "
                       "{\"loja\": \"<o NUMERO da loja na lista>\", \"dia\": \"DD/MM\", "
                       "\"horario\": \"HH:MM\"}. So diga que esta agendado quando eu "
                       "devolver o agendamento CONFIRMADO pela seguradora.")
    if operacao == "responder":
        campo = _CAMPO_DO_SLOT.get(slot, f"especificos.{slot}" if slot else "especificos")
        if slot.startswith("pergunta_"):
            # 🔴 COSTURA: a resposta à pergunta do portal volta ETIQUETADA com o
            # código dela — é o que o motor do questionário casa (contrato §5).
            campo = (f"especificos.{slot} (a resposta dele a pergunta da seguradora, "
                     "de preferencia com as palavras de uma das opcoes)")
        return base + ("Faca a pergunta ao segurado e chame portal_action de novo com os "
                       "MESMOS dados de antes (a MESMA peca e a MESMA data) e a resposta em "
                       f"{campo}.")
    if operacao == "vistoria":
        return base + ("Quando o segurado responder, chame portal_action de novo com os "
                       "MESMOS dados de antes e especificos.preferencia_vistoria = "
                       "\"link\" ou \"loja\".")
    if operacao == "reler":
        return base + ("Nao pergunte nada ao segurado: eu mesmo tento de novo pelo mesmo "
                       "pedido e o resultado chega aqui.")
    return ""


def numero_do_pedido(evidence) -> str:
    """O número que identifica o pedido NA SEGURADORA, só dígitos. "" sem ele.

    Vem do que o portal devolveu (protocolo, código do atendimento), nunca do
    que o robô achou. É a metade "protocolo" da chave de continuação.
    """
    ev = evidence if isinstance(evidence, dict) else {}
    desf = ev.get("desfecho") if isinstance(ev.get("desfecho"), dict) else {}
    est = ev.get("vidros_estado") if isinstance(ev.get("vidros_estado"), dict) else {}
    cont = continuacao_da_evidencia(ev)
    for bruto in (ev.get("protocolo"), desf.get("codigo_atendimento"),
                  est.get("codigo_atendimento"), cont.get("protocolo"),
                  cont.get("codigo_atendimento"), cont.get("codigo")):
        digitos = "".join(ch for ch in str(bruto or "") if ch.isdigit())
        if digitos:
            return digitos
    return ""


def _mesmo_nome(a, b) -> bool:
    return bool(_palavras_soltas(a)) and _palavras_soltas(a) == _palavras_soltas(b)


def mapear_escolha_de_agenda(escolha, desfecho) -> Tuple[Optional[dict], str]:
    """`({"loja": CodigoCliente, "dia": "DD/MM", "horario": "HH:MM"}, "")` ou
    `(None, motivo)`.

    🔴 Por IGUALDADE, e só por ela (SPEC §3 A3): o segurado viu uma lista
    NUMERADA (`_bloco_da_agenda`), então "1" é a primeira loja DAQUELA lista —
    a do desfecho anterior, a mesma que ele leu. Nome só casa inteiro. O código
    que vai ao portal é o `CodigoCliente` que o PORTAL publicou; nada digitado.
    """
    if not isinstance(escolha, dict):
        return None, "escolha_sem_formato"
    desf = desfecho if isinstance(desfecho, dict) else {}
    lojas = [l for l in (desf.get("lojas") or []) if isinstance(l, dict)]
    if not lojas:
        return None, "sem_lista_de_lojas"
    bruto = str(escolha.get("loja") if escolha.get("loja") is not None else "").strip()
    loja = None
    if bruto.isdigit() and 1 <= int(bruto) <= len(lojas):
        loja = lojas[int(bruto) - 1]
    else:
        iguais = [l for l in lojas
                  if (str(l.get("codigo_cliente") or "").strip() == bruto and bruto)
                  or _mesmo_nome(l.get("nome"), bruto)]
        if len(iguais) == 1:
            loja = iguais[0]
    if loja is None:
        return None, "loja_fora_da_lista"
    codigo = str(loja.get("codigo_cliente") or "").strip()
    if not codigo:
        return None, "loja_sem_codigo"
    if loja.get("tem_agenda") is False:
        return None, "loja_sem_agenda"
    dia = _dia_legivel(escolha.get("dia"))
    if not dia:
        return None, "dia_ilegivel"
    horario = _hora_legivel(escolha.get("horario"))
    if not horario:
        return None, "horario_ilegivel"
    conhecidos = {}
    for d, horas in ((loja.get("horarios") or {}) if isinstance(loja.get("horarios"), dict)
                     else {}).items():
        if _dia_legivel(d) and isinstance(horas, (list, tuple)):
            conhecidos[_dia_legivel(d)] = {_hora_legivel(h) for h in horas if isinstance(h, str)}
    # ⚠️ Só recusa o que a lista CONHECIDA desmente. Dia fora da lista lida (a
    # journey só lê os horários do 1º dia) vai ao portal, que confere na hora
    # contra o publicado — e responde `horario_indisponivel`, legível.
    if dia in conhecidos and horario not in conhecidos[dia]:
        return None, "horario_fora_da_lista"
    return {"loja": codigo, "dia": dia, "horario": horario}, ""


def _valor_do_slot(params: dict, slot: str):
    """O valor (já NORMALIZADO por `build_portal_params`) que responde `slot`."""
    p = params if isinstance(params, dict) else {}
    esp = p.get("especificos") if isinstance(p.get("especificos"), dict) else {}
    dano = p.get("dano") if isinstance(p.get("dano"), dict) else {}
    local = p.get("local") if isinstance(p.get("local"), dict) else {}
    if slot in ("cidade_servico", "cidade_para_o_servico"):
        cid = local.get("cidade_servico") if isinstance(local.get("cidade_servico"), dict) else {}
        return dict(cid) if cid.get("cidade") else None
    if slot in ("como", "como_ocorreu"):
        return dano.get("como") or None
    if slot == "pecas_lataria":
        return list(dano.get("pecas_lataria") or []) or None
    if slot == "peca":
        return str(esp.get("peca") or "").strip() or None
    valor = esp.get(slot)
    if isinstance(valor, (list, tuple)):
        return list(valor) or None
    return str(valor).strip() if valor is not None and str(valor).strip() else None


def respostas_da_chamada(params_novos: dict, params_origem: dict, slot: str) -> dict:
    """`{slot: valor}` quando ESTA chamada responde o que o pedido espera. `{}` não.

    🔴 "Responder" é trazer um valor que o pedido de origem NÃO tinha, ou tinha
    diferente. Reenviar o mesmo valor com que o portal parou produziria a mesma
    parada — e um job a mais na seguradora por nada.
    """
    slot = str(slot or "").strip()
    if not slot:
        return {}
    novo = _valor_do_slot(params_novos, slot)
    if novo is None:
        return {}
    if novo == _valor_do_slot(params_origem, slot):
        return {}
    return {("cidade_servico" if slot == "cidade_para_o_servico" else
             "como" if slot == "como_ocorreu" else slot): novo}


def resumo_estavel(operacao: str, escolha: Optional[dict] = None,
                   respostas: Optional[dict] = None, extra: str = "") -> str:
    """O "o quê" da continuação, na mesma forma sempre: a MESMA resposta dada
    duas vezes gera o MESMO texto (G7), e uma resposta diferente, outro."""
    import json as _json

    return _json.dumps({"op": str(operacao or ""), "escolha": escolha or {},
                        "respostas": respostas or {}, "extra": str(extra or "")},
                       sort_keys=True, ensure_ascii=True, default=str)


def chave_de_continuacao(company_id, protocolo, operacao: str, resumo: str) -> str:
    """`"cont:" + vidros_estado.idempotencia_de_continuacao(...)`. "" sem protocolo.

    ⛔ A função de hash é UMA, e mora com o dono do estado do pedido
    (`vidros_estado`). Import tardio pelo mesmo motivo de `normalize_insurer`:
    `portal_worker` viaja na imagem do smith-api (📊 `backend/Dockerfile:11
    COPY . .`), mas um ImportError no topo derrubaria a tool inteira.
    """
    try:
        from portal_worker.journeys.vidros_estado import idempotencia_de_continuacao
    except Exception:  # noqa: BLE001
        return ""
    h = idempotencia_de_continuacao(company_id=company_id, protocolo=protocolo,
                                    operacao=f"{operacao}|{resumo}")
    return f"cont:{h}" if h else ""


def montar_job_de_continuacao(*, company_id: str, job_origem: dict, operacao: str,
                              pedido_key: str, protocolo: str, confirm: bool,
                              escolha: Optional[dict] = None,
                              respostas: Optional[dict] = None,
                              extra: str = "") -> dict:
    """A LINHA de `portal_jobs` da continuação — contrato C→A §5, sem banco.

    `params` = os do job de origem (o que carrega a sessão mais recente) +
    `_continuacao`. ⛔ A sessão vai INTEIRA e sem ser lida: `sessao_cifrada` é
    do cofre do worker (`PORTAL_VAULT_KEY`), e o smith-api não tem por que
    abri-la. Nenhum texto daqui a imprime.
    """
    origem = job_origem if isinstance(job_origem, dict) else {}
    ev = origem.get("evidence") if isinstance(origem.get("evidence"), dict) else {}
    cont_origem = (origem.get("params") or {}).get("_continuacao")
    cont_origem = cont_origem if isinstance(cont_origem, dict) else {}
    params = {k: v for k, v in dict(origem.get("params") or {}).items() if k != "_continuacao"}
    respostas = dict(respostas or {})
    escolha_origem = cont_origem.get("escolha")
    if (operacao == "reler" and not escolha
            and cont_origem.get("operacao") in ("agendar", "reler")
            and isinstance(escolha_origem, dict) and escolha_origem):
        # 🔴 RED B2(b) (conserto da 001.10.1): a releitura de uma continuação
        # `agendar` que parou por motivo TÉCNICO herda a ESCOLHA EXPLÍCITA do
        # segurado — e só ela. Sem isto o "já estou tentando de novo" mentia:
        # o reler voltava ao desfecho sem a escolha e agendava pela preferência
        # antiga (📊 red A4.3: 23/09 08:00 para quem escolheu 22/09 16:00).
        escolha = dict(cont_origem["escolha"])
    if operacao == "vistoria" and respostas.get(PREFERENCIA_VISTORIA):
        # A preferência vai nos DOIS lugares: em `respostas` (contrato) e em
        # `especificos`, que é onde a abertura já a lia (A5, mesma função).
        params["especificos"] = {**dict(params.get("especificos") or {}),
                                 PREFERENCIA_VISTORIA: respostas[PREFERENCIA_VISTORIA]}
    params["_continuacao"] = {
        "job_origem": str(origem.get("id") or ""),
        "operacao": operacao,
        "escolha": dict(escolha or {}),
        "respostas": respostas,
        "sessao": ev.get("continuacao") if isinstance(ev.get("continuacao"), dict) else None,
        "desfecho_anterior": ev.get("desfecho") if isinstance(ev.get("desfecho"), dict) else None,
    }
    # 🔴 A LIGA do pedido: toda continuação carrega a chave da ABERTURA. É por
    # ela que a próxima chamada acha a ÚLTIMA continuação (e não a evidence
    # velha da abertura) — sempre filtrando por `company_id`.
    params["_pedido_key"] = str(pedido_key or "")
    # O interruptor é lido AGORA, não herdado: agente desligado entre a abertura
    # e a resposta do segurado para a continuação também (P-90).
    params["confirm"] = bool(confirm)
    chave = chave_de_continuacao(company_id, protocolo or pedido_key, operacao,
                                 resumo_estavel(operacao, escolha, respostas, extra))
    return {
        "company_id": str(company_id),
        "portal_key": PORTAL_VIDROS,
        "journey": JOURNEY_CONTINUAR,
        "params": params,
        "status": "queued",
        "idempotency_key": chave or None,
        "session_id": origem.get("session_id") or None,
        "agent_id": origem.get("agent_id") or None,
        "work_run_id": origem.get("work_run_id") or params.get("_work_run_id") or None,
    }
