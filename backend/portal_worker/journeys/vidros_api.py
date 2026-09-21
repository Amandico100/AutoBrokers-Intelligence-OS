# -*- coding: utf-8 -*-
"""Contrato MEDIDO da API do portal Maxpar/Autoglass — SPEC-074.

De onde vem cada linha deste arquivo
====================================
📊 Mineração offline de 16/08/2026 sobre 58 MB de HAR capturados em sessão real
(`docs/intake/MATERIAIS/PORTAL VIDROS/`, fora do Git):

    YELUM/abraseuatendimento.com.br.har ...  378 entries · 34 endpoints exercidos
    PORTO/VIDRO LANTERNA.har ..............  254 entries · fluxo até o 80%
    PORTO/PORTO RODA SEM COBERTURA.har ....   96 entries · morre no passo 1

Nada aqui é suposição sobre "como um portal REST costuma ser". Cada path, cada
nome de campo e cada código foi lido de uma requisição que aconteceu.

🔴 A descoberta que reorganiza a SPEC
=====================================
O portal **é API-first nativo**. O AngularJS é uma casca sobre
`api.autoglass.com.br`. Isso muda a escada de percepção da SPEC-073 em vidros:

    L1 (API legítima)  passa a resolver a MAIOR PARTE do fluxo
    L2 (DOM)           vira fallback, não caminho principal
    L3/L4              só onde há julgamento de verdade

E muda o desenho transacional, porque a API revela **duas fronteiras** onde a
tela sugeria uma só (ver `vidros_estado.py`).

O que este módulo NÃO faz
=========================
Não executa nada. É contrato: paths, enums, classificadores puros. Quem executa
é a journey, com a sessão legítima do browser — nunca um token inventado nem um
host fora da allowlist.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlsplit

# --------------------------------------------------------------------------
# Hosts — allowlist fechada (SPEC-073 G2 / SPEC-075 §25.5)
# --------------------------------------------------------------------------
HOST_SPA = "abraseuatendimento.com.br"
HOST_API = "api.autoglass.com.br"
HOST_AREA_SEGURADO = "areadosegurado.autoglass.com.br"
# 📊 Declarado no bundle e NUNCA exercido nas capturas. Fica listado para que,
# se um dia aparecer, o profiler não o classifique como terceiro desconhecido —
# mas continua fora da allowlist de execução até ser medido.
HOST_API_MAXASSIST_NAO_MEDIDO = "api.autoglass.com.br/maxassist-api"

HOSTS_PERMITIDOS: Tuple[str, ...] = (HOST_SPA, HOST_API, HOST_AREA_SEGURADO)

BASE_API = f"https://{HOST_API}/atendimentos/api/web-app"

# 📊 Header custom. NÃO é `Authorization: Bearer` — quem procurar Bearer não acha
# nada. O valor é o `Token` devolvido por `POST /atendimentos`, um GUID.
HEADER_TOKEN = "token_autorizacao"


def host_permitido(url: Any) -> bool:
    """Allowlist fechada. Descoberta não vira cliente HTTP de URL livre.

    🔴 A primeira versão fazia `f"//{h}" in url`, e isso é um furo clássico:

        https://api.autoglass.com.br.evil.com/x

    contém `//api.autoglass.com.br` como prefixo e **passava**. Um atacante que
    controlasse `evil.com` receberia o `token_autorizacao` da sessão.

    Pegou no teste, não em produção — mas só porque escrevi o caso adversarial.
    A lição é que allowlist por substring nunca é allowlist; é sugestão.

    Agora o host é EXTRAÍDO e comparado por igualdade ou por sufixo de ponto
    (`app.maxpar…` casa `maxpar…`; `maxpar….evil.com` não casa nada).
    """
    try:
        host = (urlsplit(str(url or "")).hostname or "").strip().lower()
    except ValueError:
        return False
    if not host:
        return False
    for h in HOSTS_PERMITIDOS:
        alvo = h.split("/")[0].strip().lower()   # ignora path em entradas compostas
        if host == alvo or host.endswith("." + alvo):
            return True
    return False


# --------------------------------------------------------------------------
# Endpoints medidos
# --------------------------------------------------------------------------
EP_SEGURADORAS = "/seguradoras/"
EP_APOLICES = "/apolices"
EP_ITENS_COBERTOS = "/apolices/itens-cobertos"
EP_MOTIVOS_DANO = "/motivos-dano"
EP_ATENDIMENTOS = "/atendimentos"
EP_ATENDIMENTOS_ABERTOS = "/atendimentos/atendimentos-abertos-existentes"
EP_CORRETORES = "/atendimentos/corretores"
EP_SOLICITANTES = "/solicitantes"
EP_QUESTIONARIO_PERGUNTAS = "/questionarios/perguntas"
EP_QUESTIONARIO = "/questionarios"
EP_REGRAS_REPARO = "/questionarios/regras-reparo"
EP_TIPOS_TELEFONE = "/tipos-telefone"
EP_UFS = "/ufs"
EP_CIDADES = "/cidades"
EP_CLIENTES_CIDADES = "/clientes/cidades"
EP_ABANDONAR = "/atendimentos/abandonar"
EP_CANCELAR = "/atendimentos/cancelar"

# --------------------------------------------------------------------------
# Endpoints acrescentados pela EXTRA-001.10 — todos MEDIDOS nos 4 HAR de
# 20/09/2026, lidos por `app.services.portals.lab.trafego.importar_har`.
# 📊 A contagem de exercícios por endpoint está no registro ESTADO_DO_ENDPOINT
# mais abaixo, e o gate G7 a reconta a partir do HAR — nenhum destes números
# vive só num comentário.
# --------------------------------------------------------------------------
EP_ALTERAR_REPARO = "/atendimentos/alterar-reparo"          # PUT  {"Reparo": bool}
EP_SERVICOS_ITENS = "/atendimentos/servicos-itens"          # lataria: as peças
EP_SERVICOS_DETALHES = "/atendimentos/servicos-detalhes"    # tamanho do amassado
EP_OBJETOS_CAUSA = "/atendimentos/objetos-causa"            # lataria: causas
EP_OFERTAS_POLIMENTO = "/atendimentos/ofertas-polimentos-farois"
EP_EMITIR_FORMALIZADO = "/atendimentos/emitir-atendimento-formalizado"
EP_LIVRES_ESCOLHAS_VALIDAR = "/atendimentos/livres-escolhas/validar"
EP_STATUS_SEGURADORAS = "/atendimentos/status-seguradoras/"
EP_LIMITES_BLOQUEIOS = "/atendimentos/limites-monetarios/bloqueios"
EP_OPCOES_DISPONIVEIS = "/agendamentos/opcoes-disponiveis"  # 🔴 O ROTEADOR
EP_DATAS_DISPONIVEIS = "/agendamentos/datas-disponiveis"
EP_HORARIOS_DISPONIVEIS = "/agendamentos/horarios-disponiveis"
EP_CONSULTAR_DISTANCIAS = "/lojas/consultar-distancias"     # POST de LEITURA
EP_CONSULTA_CEP = "/transportes-proprios/consultas-cep"

# 📊 Declarados no bundle, NÃO exercidos em nenhuma captura. Só entram em uso
# depois de medidos — SPEC-073 G3: candidato ≠ aprovado.
EP_FINALIZAR_NAO_MEDIDO = "/atendimentos/finalizar"
EP_VISTORIA_MOBILE_NAO_MEDIDO = "/atendimentos/vistoriamobile"
EP_AGENDAMENTOS_NAO_MEDIDO = "/agendamentos"
EP_DIRECIONAMENTOS_NAO_MEDIDO = "/direcionamentos"
EP_FOTOGRAFIAS_WEB_NAO_MEDIDO = "/atendimentos-fotografias/web"
EP_MOTIVOS_CANCELAMENTO_NAO_MEDIDO = "/atendimentos/motivos-cancelamento"
# 📊 Exercidos nas capturas, mas FORA do contrato desta SPEC: a tela os dispara
# e nenhum campo que o motor lê muda com eles. Um robô que abre reclamação
# sozinho é efeito que ninguém pediu.
EP_VISTORIAS_PREVIAS_FORA = "/atendimentos/{codigo}/vistorias-previas/processar"
EP_CORRETORES_RECLAMACOES_FORA = "/corretores-reclamacoes"

# --------------------------------------------------------------------------
# 🔴 A ESCADA DA SPEC-077, escrita: OBSERVED → CANDIDATE → APPROVED
# --------------------------------------------------------------------------
# `APPROVED` significa UMA coisa só: **este endereço foi exercido numa captura
# real e nós sabemos o que ele faz**. `CANDIDATE` significa que ele existe no
# bundle (ou na tela) e que nós NUNCA o vimos acontecer.
#
# 🔴 A regra que fecha a porta: `SessaoVidros.chamar` recusa endpoint
# `CANDIDATE` **mesmo com o freio liberado e a aprovação humana dada**. Escrever
# o código contra o contrato do bundle é barato; deixá-lo sair sem captura é
# mandar um efeito que ninguém mediu para dentro de uma seguradora.
APPROVED = "APPROVED"
CANDIDATE = "CANDIDATE"

ESTADO_DO_ENDPOINT: Dict[str, str] = {
    # ---- leituras exercidas ------------------------------------------------
    EP_SEGURADORAS: APPROVED,
    EP_APOLICES: APPROVED,
    EP_ITENS_COBERTOS: APPROVED,
    EP_MOTIVOS_DANO: APPROVED,
    EP_ATENDIMENTOS: APPROVED,
    EP_ATENDIMENTOS_ABERTOS: APPROVED,
    EP_TIPOS_TELEFONE: APPROVED,
    EP_UFS: APPROVED,
    EP_CIDADES: APPROVED,
    EP_CLIENTES_CIDADES: APPROVED,
    EP_SERVICOS_ITENS: APPROVED,
    EP_SERVICOS_DETALHES: APPROVED,
    EP_OBJETOS_CAUSA: APPROVED,
    EP_OFERTAS_POLIMENTO: APPROVED,
    EP_LIVRES_ESCOLHAS_VALIDAR: APPROVED,
    EP_STATUS_SEGURADORAS: APPROVED,
    EP_LIMITES_BLOQUEIOS: APPROVED,
    EP_OPCOES_DISPONIVEIS: APPROVED,
    EP_DATAS_DISPONIVEIS: APPROVED,
    EP_HORARIOS_DISPONIVEIS: APPROVED,
    EP_CONSULTA_CEP: APPROVED,
    # ---- escritas exercidas e contratadas ----------------------------------
    EP_CORRETORES: APPROVED,
    EP_SOLICITANTES: APPROVED,
    EP_QUESTIONARIO_PERGUNTAS: APPROVED,   # POST que LÊ a próxima pergunta
    EP_QUESTIONARIO: APPROVED,
    EP_REGRAS_REPARO: APPROVED,            # POST que LÊ {ExibirDialogDeReparo}
    EP_ALTERAR_REPARO: APPROVED,
    EP_EMITIR_FORMALIZADO: APPROVED,
    EP_CONSULTAR_DISTANCIAS: APPROVED,     # POST de LEITURA (rota, não negócio)
    EP_CANCELAR: APPROVED,                 # 📊 2 exercícios (NOVO, ANT)
    # ---- escritas que NUNCA vimos acontecer --------------------------------
    EP_AGENDAMENTOS_NAO_MEDIDO: CANDIDATE,
    EP_DIRECIONAMENTOS_NAO_MEDIDO: CANDIDATE,
    EP_FOTOGRAFIAS_WEB_NAO_MEDIDO: CANDIDATE,
    EP_FINALIZAR_NAO_MEDIDO: CANDIDATE,
    EP_VISTORIA_MOBILE_NAO_MEDIDO: CANDIDATE,
    EP_MOTIVOS_CANCELAMENTO_NAO_MEDIDO: CANDIDATE,
    # 📊 `abandonar` TEM 1 exercício (HAR da PORTO, `PATCH /atendimentos/abandonar
    # {"MotivoAbandono": …}`, status 200) — a proposta dizia "zero capturas" e o
    # número medido aqui vence. Ele continua CANDIDATE mesmo assim, e a razão não
    # é falta de medição: é que desistir de um pedido no lugar do segurado não é
    # um efeito que esta SPEC autoriza. Promover exige decisão de produto, não
    # mais uma captura.
    EP_ABANDONAR: CANDIDATE,
    # exercidos, mas fora do contrato (a tela os dispara; o motor não)
    EP_VISTORIAS_PREVIAS_FORA: CANDIDATE,
    EP_CORRETORES_RECLAMACOES_FORA: CANDIDATE,
}

# 📊 O método com que cada ESCRITA foi medida (ou declarada no bundle). O gate
# G7 usa esta tabela para recontar exercícios no HAR: endpoint de escrita com
# ZERO exercícios e estado APPROVED deixa o gate VERMELHO.
METODO_DA_ESCRITA: Dict[str, str] = {
    EP_ATENDIMENTOS: "POST",
    EP_CORRETORES: "PUT",
    EP_SOLICITANTES: "POST",
    EP_QUESTIONARIO_PERGUNTAS: "POST",
    EP_QUESTIONARIO: "POST",
    EP_REGRAS_REPARO: "POST",
    EP_ALTERAR_REPARO: "PUT",
    EP_EMITIR_FORMALIZADO: "POST",
    EP_CONSULTAR_DISTANCIAS: "POST",
    EP_CANCELAR: "PUT",
    EP_ABANDONAR: "PATCH",
    EP_AGENDAMENTOS_NAO_MEDIDO: "POST",
    EP_DIRECIONAMENTOS_NAO_MEDIDO: "POST",
    EP_FOTOGRAFIAS_WEB_NAO_MEDIDO: "POST",
    EP_FINALIZAR_NAO_MEDIDO: "PATCH",
    EP_VISTORIAS_PREVIAS_FORA: "POST",
    EP_CORRETORES_RECLAMACOES_FORA: "POST",
}

_RE_CODIGO_NA_URL = re.compile(r"/\d{4,}")

# 📊 Os verbos que MUDAM o mundo. `POST /questionarios/perguntas` é leitura, e
# por isso quem decide o que é material continua sendo o guard — esta lista só
# escolhe quem precisa estar NO REGISTRO para poder sair.
METODOS_DE_ESCRITA: Tuple[str, ...] = ("POST", "PUT", "PATCH", "DELETE")


def _caminho_normalizado(caminho: Any) -> str:
    """O caminho como o servidor o veria. 🔴 A allowlist não pode ser burlada
    por caixa, espaço, barra dupla ou `;`.

    📊 Medido pelo red team em 20/09/2026: `/Agendamentos`, `//agendamentos`,
    `/agendamentos ` e `/atendimentos/Abandonar` **saíam para a rede** — os
    quatro são o mesmo endereço para o servidor e eram desconhecidos para o
    registro.
    """
    from urllib.parse import unquote

    c = unquote(str(caminho or "")).strip().lower()
    c = c.split("?")[0].split("#")[0].split(";")[0]
    c = re.sub(r"/{2,}", "/", c)
    c = re.sub(r"/\./", "/", c)
    if len(c) > 1 and c.endswith("/"):
        c = c[:-1]
    return c


def endpoint_do_caminho(caminho: Any) -> str:
    """Do caminho chamado para a CHAVE do registro. `""` = desconhecido.

    O código de atendimento aparece no meio (`/atendimentos/<cod>/vistorias…`)
    e no fim (`/emitir-atendimento-formalizado/<cod>`) — por isso a
    normalização troca todo bloco de 4+ dígitos por `{codigo}` antes de casar, e
    o casamento é pelo prefixo MAIS LONGO: `/atendimentos/abandonar` não pode
    cair em `/atendimentos`.
    """
    c = _RE_CODIGO_NA_URL.sub("/{codigo}", _caminho_normalizado(caminho))
    for ep in ESTADO_DO_ENDPOINT:
        if _caminho_normalizado(ep) == c:
            return ep
    melhor = ""
    for ep in ESTADO_DO_ENDPOINT:
        base = _caminho_normalizado(ep)
        if c == base or c.startswith(base + "/"):
            if len(base) > len(_caminho_normalizado(melhor or "")):
                melhor = ep
    return melhor


def estado_do_endpoint(caminho: Any) -> str:
    """`APPROVED` · `CANDIDATE` · `""` (fora do registro)."""
    return ESTADO_DO_ENDPOINT.get(endpoint_do_caminho(caminho), "")


def pode_sair(caminho: Any, metodo: Any = "GET") -> bool:
    """A chamada pode sair para a rede?

    🔴 FAIL-CLOSED para ESCRITA, e a regra mudou em 20/09/2026 por medição: a
    versão anterior devolvia `True` para endpoint fora do registro, e o red team
    mostrou o que isso significava na prática — `/Agendamentos`, `//agendamentos`
    e `/atendimentos/Abandonar` **saíram para a rede**, porque bastava escrever o
    caminho de outro jeito para o registro não o reconhecer.

        endpoint CANDIDATE            → nunca sai
        fora do registro + ESCRITA    → nunca sai (é isto que mudou)
        fora do registro + leitura    → sai; ler é reversível, e a allowlist de
                                        host continua valendo
    """
    estado = estado_do_endpoint(caminho)
    if estado == CANDIDATE:
        return False
    if not estado and str(metodo or "").upper() in METODOS_DE_ESCRITA:
        return False
    return True


# --------------------------------------------------------------------------

# --------------------------------------------------------------------------
# Preflight de apólice — SPEC-074 §E, o gate que decide se PODE haver escrita
# --------------------------------------------------------------------------
POLICY_OK = "policy_ok"
POLICY_NOT_FOUND = "policy_not_found"
POLICY_AMBIGUOUS = "policy_ambiguous"
COVERAGE_ABSENT = "coverage_absent"
BUSINESS_RULE_UNKNOWN = "business_rule_rejection_unknown"
PREFLIGHT_ERRO = "preflight_error"

# 📊 Discriminador de exceção do backend .NET. Medido uma vez, com um valor.
# Tratado como enum ABERTO de propósito: um `Tipo` novo tem de virar
# `business_rule_rejection_unknown` e parar, nunca ser lido como sucesso.
TIPO_REGRA_DE_NEGOCIO = "regradenegocioexcecao"

_RE_SEM_CLAUSULA = re.compile(
    r"nao possui (?:clausula|cobertura) de (?P<escopo>.+?) contratad", re.I)


def _norm(txt: Any) -> str:
    """Sem acento, sem caixa, espaço colapsado.

    📊 Obrigatório aqui: o `<body ui-sentence-case-text>` do portal reescreve a
    caixa em runtime — o template diz `Nº do Atendimento:` e o DOM entrega
    `Nº do atendimento:`. E as respostas de erro vêm com escapes `\\u00E1`.
    Caixa NUNCA carrega significado de negócio.
    """
    s = unicodedata.normalize("NFKD", str(txt or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().lower()


def classificar_preflight(status: int, corpo: Any) -> Dict[str, Any]:
    """`GET /apolices` → estado de negócio determinístico. **Sem LLM.**

    🔴 Esta função é o gate mais importante da SPEC-074, e ela existe porque a
    medição mostrou algo que a tela escondia:

    📊 No HAR `PORTO RODA SEM COBERTURA`, o fluxo inteiro tem 96 entries e
    apenas DUAS chamadas de API. A segunda devolve 400 e o fluxo morre ali.
    **Nenhum `POST /atendimentos` aconteceu. Nenhum protocolo nasceu.**

    Ou seja: ausência de cobertura é detectável **antes de qualquer escrita**.
    Um robô que só olhasse a tela veria um `md-dialog` genérico "Atenção" e
    teria de adivinhar; aqui a resposta é estruturada e inequívoca.

    Os quatro estados vizinhos não se confundem, e a diferença é o status HTTP:

        200 + ApoliceNaoEncontrada=true        → policy_not_found
        200 + MaisDeUmaApoliceEncontrada=true  → policy_ambiguous
        200 + ambos false                      → policy_ok
        400 + Tipo=RegraDeNegocioExcecao       → coverage_absent (se a mensagem casar)
        400 + Tipo desconhecido                → business_rule_rejection_unknown
    """
    st = int(status or 0)

    if st == 400:
        dados = corpo if isinstance(corpo, dict) else {}
        tipo = _norm(dados.get("Tipo"))
        msg = str(dados.get("Message") or "")
        if tipo == TIPO_REGRA_DE_NEGOCIO:
            m = _RE_SEM_CLAUSULA.search(_norm(msg))
            if m:
                return {"estado": COVERAGE_ABSENT,
                        "escopo": m.group("escopo").strip(),
                        "mensagem_portal": msg,
                        "pode_escrever": False}
            # Mesma classe de exceção, outra regra. Não inventamos qual.
            return {"estado": BUSINESS_RULE_UNKNOWN,
                    "escopo": "",
                    "mensagem_portal": msg,
                    "pode_escrever": False}
        return {"estado": BUSINESS_RULE_UNKNOWN, "escopo": "",
                "mensagem_portal": msg, "pode_escrever": False,
                "tipo_desconhecido": str(dados.get("Tipo") or "")}

    if st != 200:
        return {"estado": PREFLIGHT_ERRO, "escopo": "",
                "mensagem_portal": f"http {st}", "pode_escrever": False}

    dados = corpo if isinstance(corpo, dict) else {}
    if dados.get("ApoliceNaoEncontrada") is True:
        return {"estado": POLICY_NOT_FOUND, "escopo": "",
                "mensagem_portal": "", "pode_escrever": False}
    if dados.get("MaisDeUmaApoliceEncontrada") is True:
        return {"estado": POLICY_AMBIGUOUS, "escopo": "",
                "mensagem_portal": "", "pode_escrever": False}

    # 🔴 `pode_escrever=True` é a ÚNICA porta para `POST /atendimentos`, que é a
    # primeira fronteira material. Exigir os dois flags explicitamente `false`
    # — e não apenas "não é true" — é deliberado: um corpo malformado que não
    # traga os campos não pode virar permissão de escrita.
    if dados.get("ApoliceNaoEncontrada") is False and dados.get("MaisDeUmaApoliceEncontrada") is False:
        return {"estado": POLICY_OK, "escopo": "", "mensagem_portal": "",
                "pode_escrever": True}

    return {"estado": PREFLIGHT_ERRO, "escopo": "",
            "mensagem_portal": "resposta 200 sem os flags de apolice",
            "pode_escrever": False}


# --------------------------------------------------------------------------
# TipoAtendimento — só a Porto oferece a escolha
# --------------------------------------------------------------------------
TIPO_VIDROS_FAROIS = 1
TIPO_RODA_PNEU_SUSPENSAO = 2

# 📊 Das 42 seguradoras roteadas no bundle, só a Porto sobrescreve o passo 1
# (`seguradoras/porto/passo1.html`) com o bloco `campo-cobertura`. Para todas as
# outras a camada de serviço envia `TipoAtendimento: t.TipoAtendimento || null`.
#
# 🔴 Nunca generalizar 1/2. Mandar `TipoAtendimento=1` para uma seguradora que
# não oferece a escolha é inventar um campo que a tela dela não tem.
SEGURADORAS_COM_ESCOLHA_DE_COBERTURA: Tuple[str, ...] = ("PORTO",)

COBERTURAS_PORTO: Dict[int, str] = {
    TIPO_VIDROS_FAROIS: "Vidros, Faróis/Lanternas e Retrovisores",
    TIPO_RODA_PNEU_SUSPENSAO: "Roda, Pneu e Suspensão",
}


# --------------------------------------------------------------------------
# 🔴 A seguradora sai de um DADO AO VIVO, não de uma lista no código
# --------------------------------------------------------------------------
# 📊 `GET /seguradoras/` devolveu **38 itens** em 20/09/2026 (HAR do para-brisa,
# lido por `trafego.importar_har`). Cada item tem `Codigo`, `CodigoSeguradora`
# (o slug que a API usa em toda query), `Nome` e `NomeFantasia`. **Não existe
# campo `Ativo`**: a inatividade vem escrita no próprio nome, entre parênteses.
#
# 🔴 A lista fechada de 3 slugs que existia aqui (`PORTO`, `AZUL`, `ITAU`)
# morreu, e com ela o defeito que ela carregava: `ITAU` **não está entre as 38**.
# Um corretor que digitasse "Itaú" recebia o slug `ITAU`, o portal respondia
# sobre uma seguradora que ele não publica, e o preflight decidia a escrita em
# cima disso. Produto multi-corretora não decora catálogo de ninguém.
FORA_DO_API_FIRST: Tuple[str, ...] = (
    # D-PILOTO-17: a Bradesco resolve na lista (slug `BRADESCO`, código 52) —
    # ela aparece, é exibível e o corretor pode nomeá-la. O que NÃO acontece é
    # a escrita automática: `abrir_atendimento_api` devolve `None` para ela e o
    # caminho DOM assume. A decisão é de produto, não de contrato.
    "BRADESCO",
)

_MARCA_INATIVA = "(inativo)"

# Palavras que aparecem em quase toda razão social e não identificam ninguém.
_PALAVRAS_GENERICAS = {"seguros", "seguro", "seguradora", "cia", "companhia",
                       "s", "sa", "ltda", "auto", "brasil", "do", "de", "da",
                       "e", "nacional", "gerais", "previdencia"}


def apelidos_de_seguradora() -> Tuple[Tuple[str, str, str], ...]:
    """A TABELA ÚNICA de seguradora: `(fragmento, slug, nome_de_tela)`.

    Três coisas que antes moravam em dois lugares e agora moram num só:

        fragmento     o que a InfoCap/o corretor escrevem (CAIXA ALTA, sem acento)
        slug          o que a **API** usa em toda query (`CodigoSeguradora`)
        nome_de_tela  o que o caminho **DOM** digita no `#seguradora-input`,
                      e que casa com o `NomeFantasia` publicado

    🔴 Isto é **dica**, nunca autoridade: o `slug` só vale se aparecer na lista
    ao vivo de `GET /seguradoras/`. Um apelido que aponte para uma seguradora
    que o portal não publica **não resolve nada** — é o que acontece com `ITAU`,
    que continua aqui para o caminho DOM saber o que digitar e continua
    devolvendo `None` em `resolver_seguradora`.

    ⚠️ **O formato é uma sequência de TRIPLAS, não um dicionário, de propósito.**
    Quem consome de fora é `app/agents/tools/portal_params._apelidos_do_portal`,
    que testa o fragmento com `in` sobre o nome em CAIXA ALTA — por isso a ordem
    é **da mais específica para a mais genérica** (`PORTO SEGURO` antes de
    `PORTO`; `TOKIO MARINE` antes de `TOKIO`). Um `dict` faria aquele laço
    levantar `ValueError` e cair num `except`, e a consolidação pareceria feita
    sem estar.
    """
    return _triplas_de_apelido(_APELIDOS_MEDIDOS)


def _triplas_de_apelido(bruto: Dict[str, Tuple[str, str]]
                        ) -> Tuple[Tuple[str, str, str], ...]:
    """Mais específico primeiro: `PORTO SEGURO` antes de `PORTO`."""
    return tuple(sorted(((k.upper(), v[0], v[1]) for k, v in bruto.items()),
                        key=lambda t: (-len(t[0].split()), -len(t[0]), t[0])))


def _palavras_de(texto: Any) -> list:
    """Palavras comparáveis, sem acento e sem pontuação. Ordem preservada."""
    return "".join(c if c.isalnum() else " " for c in _norm(texto)).split()


def casar_apelido(nome: Any) -> Optional[Tuple[str, str, str]]:
    """O apelido que casa com este nome, por PALAVRA INTEIRA. `None` se nenhum.

    🔴 Três defeitos medidos pelo red team em 20/09/2026, e os três morrem aqui:

        "ITAÚ SEGUROS…"      o acento fazia o fragmento `ITAU` não casar, e o
                             DOM passava a digitar o nome cru — 📊 mudou o que
                             a tela recebia, com a flag DESLIGADA
        "ZURICH SANTANDER"   virava `Santander Auto` porque a ordenação por
                             tamanho punha `SANTANDER` na frente. Empate em
                             número de palavras resolve por QUEM APARECE ANTES
                             no texto, que é como uma pessoa lê
        "BANCO" / "SEG"      casavam por pedaço de palavra. Agora o apelido tem
                             de aparecer como SEQUÊNCIA DE PALAVRAS INTEIRAS

    Mais palavras vence menos (`PORTO SEGURO` > `PORTO`); empate vence quem
    aparece primeiro.
    """
    palavras = _palavras_de(nome)
    if not palavras:
        return None
    melhor: Optional[Tuple[int, int, Tuple[str, str, str]]] = None
    for tripla in apelidos_de_seguradora():
        alvo = _palavras_de(tripla[0])
        if not alvo:
            continue
        for i in range(len(palavras) - len(alvo) + 1):
            if palavras[i:i + len(alvo)] == alvo:
                chave = (-len(alvo), i)
                if melhor is None or chave < melhor[:2]:
                    melhor = (chave[0], chave[1], tripla)
                break
    return melhor[2] if melhor else None


def nome_de_tela_do_apelido(nome: Any) -> str:
    """O nome que o caminho DOM digita. `""` quando nenhum apelido casa."""
    achado = casar_apelido(nome)
    return achado[2] if achado else ""


# 📊 `{fragmento: (slug, nome_de_tela)}`. Cada linha tem a medição que a
# justifica; as sem comentário vieram direto da lista ao vivo de 20/09/2026
# (`CodigoSeguradora` + `NomeFantasia`).
_APELIDOS_MEDIDOS: Dict[str, Tuple[str, str]] = {
    # 📊 `CodigoSeguradora = "LIBERTY"`, `Nome = "YELUM SEGUROS S.A"`,
    # `NomeFantasia = "YELUM SEGURADORA"`, `Codigo = 56`. A Liberty virou
    # Yelum e o portal guardou o slug antigo. Quem digita "Yelum" — que é o
    # que está na apólice de hoje — precisa chegar em `LIBERTY`.
    "yelum": ("LIBERTY", "Yelum"),
    "liberty": ("LIBERTY", "Yelum"),
    # 📊 A InfoCap abrevia. `LIBE` é o que 📊 `test_spec020_portal_action.py`
    # mede vindo de apólice real.
    "libe": ("LIBERTY", "Yelum"),
    # 📊 `NomeFantasia = "TOKIO MARINE SEGURADORA"`, slug `TOKIOMARINE`:
    # o nome de tela tem espaço e o slug não.
    "tokio marine": ("TOKIOMARINE", "Tokio Marine"),
    "tokio": ("TOKIOMARINE", "Tokio Marine"),
    # 📊 `NomeFantasia = "SOMPO SEGUROS"`, slug `SOMPO`, código 281.
    # ⚠️ No bundle do SPA existe uma ROTA `seguradoras/sompo/…` que carrega
    # os templates de `GRUPO_HDI`. Isso é rota de tela (quem desenhou
    # reaproveitou o layout do grupo), **não** é o slug da API. Ninguém deve
    # "consertar" `SOMPO` para `GRUPO_HDI`: a query da API usa `SOMPO`, e é
    # com `SOMPO` que a lista ao vivo responde.
    "sompo": ("SOMPO", "Sompo"),
    "porto seguro": ("PORTO", "Porto Seguro"),
    "porto": ("PORTO", "Porto Seguro"),
    "sul america": ("SULAMERICA", "SulAmerica"),
    "sulamerica": ("SULAMERICA", "SulAmerica"),
    "hdi": ("HDI", "HDI"),
    "mitsui": ("MITSUI", "Mitsui"),
    # 📊 A InfoCap usa a sigla do grupo Mitsui Sumitomo.
    "msig": ("MITSUI", "Mitsui"),
    "toyota": ("TOYOTA", "Seguro Toyota"),
    "santander": ("SANTANDERAUTO", "Santander Auto"),
    "banco do brasil": ("BB", "BB Seguros"),
    "allianz": ("ALLIANZ", "Allianz"),
    "bradesco": ("BRADESCO", "Bradesco"),
    "mapfre": ("MAPFRE", "Mapfre"),
    "zurich": ("ZURICH", "Zurich"),
    "azul": ("AZUL", "Azul"),
    # ⛔ Estas DUAS não estão entre as 38 que o portal publica hoje. Elas ficam
    # para o caminho DOM saber o que digitar, e 📊 `resolver_seguradora`
    # devolve `None` para as duas — porque o apelido só resolve quando o slug
    # aparece na lista AO VIVO. Apagá-las daqui não as faria existir no portal;
    # mantê-las não as faz existir na API. É a lista viva que decide.
    "itau": ("ITAU", "Itau"),
    "suhai": ("SUHAI", "Suhai"),
}


def _itens_de_seguradora(lista_ao_vivo: Any) -> list:
    if isinstance(lista_ao_vivo, dict):
        lista_ao_vivo = lista_ao_vivo.get("json") or []
    return [i for i in (lista_ao_vivo or []) if isinstance(i, dict)] \
        if isinstance(lista_ao_vivo, list) else []


def _slug_do_item(item: Dict[str, Any]) -> str:
    return str(item.get("CodigoSeguradora") or "").strip().upper()


def _item_inativo(item: Dict[str, Any]) -> bool:
    """📊 Não há campo `Ativo`. A inatividade vem no nome: o item de código 146
    chega como `NomeFantasia = "NUBANK AUTO (INATIVO)"` e
    `Nome = "USEBENS SEGUROS S.A. (INATIVO)"`. Um pedido aberto para uma
    seguradora inativa é um pedido que ninguém atende."""
    return any(_MARCA_INATIVA in _norm(item.get(c))
               for c in ("Nome", "NomeFantasia", "DescricaoAtendimentoWeb"))


def resolver_seguradora(nome: Any, lista_ao_vivo: Any) -> Optional[Dict[str, Any]]:
    """O nome que a corretora escreveu → `{slug, codigo, nome_de_tela}` ou `None`.

    A lista vem de `GET /seguradoras/` **desta execução**. `None` é uma resposta
    legítima e frequente, e significa sempre a mesma coisa: *não dá para provar
    de qual seguradora ele está falando* — e aí o caminho DOM assume, que é
    quem sabe navegar a tela de seleção.

    A ordem das tentativas é do mais forte para o mais fraco:

        1. igualdade com slug, `Nome` ou `NomeFantasia` (sem acento, sem caixa)
        2. apelido MEDIDO, desde que o slug exista na lista ao vivo
        3. prefixo/continência — e só resolve se sobrar **um** slug

    🔴 Dois candidatos devolvem `None`, nunca "o primeiro". Escolher por posição
    é como se manda o pedido para a seguradora errada com todos os testes verdes.
    """
    itens = [i for i in _itens_de_seguradora(lista_ao_vivo) if not _item_inativo(i)]
    alvo = _norm(nome)
    if not alvo or not itens:
        return None

    def devolver(item: Dict[str, Any]) -> Dict[str, Any]:
        return {"slug": _slug_do_item(item),
                "codigo": item.get("Codigo"),
                "nome_de_tela": str(item.get("NomeFantasia")
                                    or item.get("Nome") or "").strip()}

    # 1. igualdade
    for item in itens:
        if alvo in (_norm(_slug_do_item(item)), _norm(item.get("Nome")),
                    _norm(item.get("NomeFantasia"))):
            return devolver(item)

    # 2. apelido medido, por PALAVRA INTEIRA — vale só se o slug estiver
    #    publicado hoje
    achado = casar_apelido(nome)
    if achado:
        for item in itens:
            if _slug_do_item(item) == achado[1]:
                return devolver(item)

    # 3. o nome dito é uma SEQUÊNCIA DE PALAVRAS INTEIRAS do item, e só com UM
    #    candidato.
    # 🔴 Aqui morava um `alvo in campo` por pedaço de palavra, e o red team
    # mediu o que ele fazia: 📊 `"BANCO"` resolvia para `BB` e `"SEG"` para
    # `TOYOTA` — três letras escolhendo a seguradora de alguém.
    ditas = [p for p in _palavras_de(nome) if p not in _PALAVRAS_GENERICAS]
    if not ditas:
        return None
    candidatos: Dict[str, Dict[str, Any]] = {}
    for item in itens:
        for campo in (_slug_do_item(item), item.get("Nome"), item.get("NomeFantasia")):
            do_item = _palavras_de(campo)
            if any(do_item[i:i + len(ditas)] == ditas
                   for i in range(len(do_item) - len(ditas) + 1)):
                candidatos[_slug_do_item(item)] = item
                break
    if len(candidatos) == 1:
        return devolver(next(iter(candidatos.values())))
    return None


def nomes_de_tela_das_seguradoras(lista_ao_vivo: Any) -> list:
    """Os nomes que o portal publica hoje — para o agente perguntar com a lista
    na mão em vez de adivinhar. Inativas ficam de fora."""
    return sorted({str(i.get("NomeFantasia") or i.get("Nome") or "").strip()
                   for i in _itens_de_seguradora(lista_ao_vivo)
                   if not _item_inativo(i) and (i.get("NomeFantasia") or i.get("Nome"))})


# --------------------------------------------------------------------------
# 🔴 `DataSinistro` — o portal recebe um INSTANTE, não uma data
# --------------------------------------------------------------------------
# 📊 Medido em 20/09/2026 nos 4 HAR, com `importar_har`, nos DOIS lugares em que
# a data viaja — e os dois vieram idênticos em 4 de 4:
#
#     GET  /apolices?…&DataSinistro=2026-09-20T03:00:00.000Z   (o PREFLIGHT)
#     POST /atendimentos  {"DataSinistro": "2026-09-20T03:00:00.000Z"}
#
# 🔴 `AAAA-MM-DD` tem **ZERO exercícios**, inclusive no preflight — que é o
# portão que decide se pode haver escrita. Mandar um formato que nunca foi visto
# funcionar, justo ali, é apostar o pedido inteiro num palpite.
#
# O `03:00Z` não é constante: é a **meia-noite local de São Paulo** convertida
# para UTC. Por isso o offset é DERIVADO do fuso, nunca escrito. A prova de que
# a derivação é real e não um `+3` disfarçado: para uma data de 2018, quando o
# Brasil ainda tinha horário de verão, a mesma função devolve `T02:00:00.000Z`.
FUSO_DO_PORTAL = "America/Sao_Paulo"


def instante_do_sinistro(data: Any) -> str:
    """`AAAA-MM-DD` → `AAAA-MM-DDT03:00:00.000Z` (meia-noite local em UTC).

    Devolve `""` para entrada que não seja uma data ISO — quem chamou já tratou
    o vazio como "não dá para abrir", e é o comportamento certo.
    """
    from datetime import datetime, timedelta, timezone

    txt = str(data or "").strip()[:10]
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", txt):
        return ""
    ano, mes, dia = (int(p) for p in txt.split("-"))
    try:
        from zoneinfo import ZoneInfo

        local = datetime(ano, mes, dia, tzinfo=ZoneInfo(FUSO_DO_PORTAL))
    except Exception:  # noqa: BLE001
        # Sem a base de fusos (imagem enxuta), cai para o offset que 4 de 4
        # capturas mostraram. Degradar para o MEDIDO é melhor que degradar para
        # um formato nunca exercido.
        local = datetime(ano, mes, dia, tzinfo=timezone(timedelta(hours=-3)))
    return local.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def tipo_atendimento_para(seguradora_slug: Any, familia: Any = "") -> Optional[int]:
    """`1`, `2` ou `None`. `None` é a resposta certa para 41 das 42."""
    slug = str(seguradora_slug or "").strip().upper()
    if slug not in SEGURADORAS_COM_ESCOLHA_DE_COBERTURA:
        return None
    f = _norm(familia)
    if any(t in f for t in ("roda", "pneu", "suspensao")):
        return TIPO_RODA_PNEU_SUSPENSAO
    return TIPO_VIDROS_FAROIS


# --------------------------------------------------------------------------
# CodigoItemCoberto — a chave composta
# --------------------------------------------------------------------------
# 📊 Formato medido: `CodigoScript|CodigoTipoScript|Flag|Grupo|N|N|Categoria`
#    ex.: `3|129|N|10700|1|0|V`  (vidro de porta, Yelum)
#         `4|132|S|11402|1|0|V`  (lanterna de mala, Porto)
#
# Os dois primeiros campos viram `CodigoScript`/`CodigoTipoScript` nas queries
# seguintes — foi confirmado comparando o item escolhido com o `GET /atendimentos`
# posterior. Os demais são constantes por apólice.
CATEGORIA_VIDRACARIA = "V"
CATEGORIA_RODA_PNEU = "U"
CATEGORIA_LATARIA = "L"


def partes_do_item_coberto(codigo: Any) -> Dict[str, Any]:
    """Quebra a chave composta. Devolve `{}` quando o formato não bate.

    Fail-closed: um formato que mudou não pode virar `CodigoScript` errado numa
    query — isso traria o catálogo de outra peça sem ninguém perceber.
    """
    partes = str(codigo or "").split("|")
    if len(partes) != 7:
        return {}
    try:
        return {
            "codigo_script": int(partes[0]),
            "codigo_tipo_script": int(partes[1]),
            "flag": partes[2],
            "grupo": partes[3],
            "categoria": partes[6],
            "bruto": str(codigo),
        }
    except (TypeError, ValueError):
        return {}


# --------------------------------------------------------------------------
# Onde ocorreu o dano — estático no template, não vem da API
# --------------------------------------------------------------------------
# 📊 `ng-repeat="opcao in ['Urbano (Cidade)', 'Rodoviário', 'Não Sabe']"` com
# `value="{{opcao.substring(0,1)}}"`. O valor enviado é a PRIMEIRA LETRA.
PERIMETRO_DANO: Dict[str, str] = {
    "U": "Urbano (Cidade)",
    "R": "Rodoviário",
    "N": "Não Sabe",
}

# --------------------------------------------------------------------------
# 🔴 AS CAUSAS DO DANO, MEDIDAS — para COLETAR antes, nunca para DECIDIR
# --------------------------------------------------------------------------
# 📊 União dos textos de `GET /motivos-dano` nos 4 HAR de 20/09/2026, lidos por
# `app.services.portals.lab.trafego.importar_har`, agrupados pela família da
# peça que a query pediu:
#
#     parabrisa  ← HAR YELUM PARA BRISA   item `1|129|S|10700|1|0|V`  (11 causas)
#     lateral    ← HAR YELUM VIDROS ANTIGO item `3|129|N|10700|1|0|V` (12 causas)
#     lanterna   ← HAR PORTO VIDRO LANTERNA item `4|132|S|11402|1|0|V`(14 causas)
#     lataria    ← HAR YELUM 1             item `1|142|S|11335|1|0|L` ( 7 causas)
#
# ⛔ **ISTO É DICA PARA A COLETA. QUEM MANDA É A LISTA AO VIVO DAQUELA PEÇA.**
# A lista muda por peça E por apólice — 📊 a mesma seguradora devolveu 11 causas
# para o para-brisa e 12 para o vidro de porta, e a lataria tem um `OUTROS` que
# não existe em nenhuma das outras três. Nada aqui é enviado ao portal: o que
# viaja é sempre o `CodigoObjetoCausa` casado contra `GET /motivos-dano` na hora.
#
# Para que serve, então: para o agente PERGUNTAR ANTES com as palavras que o
# portal vai usar. Sem isso, o relato livre do segurado ("uma pedra bateu no
# vidro") não casa com nada, e o pedido nasce e trava em `motivo_ambiguo` — com
# o protocolo já emitido e sem journey de continuação.
CAUSAS_MEDIDAS: Dict[str, Tuple[str, ...]] = {
    "parabrisa": (
        "CHOQUE TERMICO",
        "CHUVA DE GRANIZO",
        "COLISÃO ACIDENTAL",
        "DANO ACIDENTAL CAUSADO POR PEDRA, OBJETO OU FRUTA",
        "DANO DESCARACTERIZADO - FOI REALIZADO ALGUM REPARO",
        "DURANTE FORTE VENTANIA,TEMPESTADE OU ENCHENTE",
        "ENCONTROU O VEICULO DANIFICADO",
        "PEÇA AMARELADA, MANCHADA OU ARRANHADA",
        "QUEBRA INTENCIONAL OU VOLUNTÁRIA",
        "QUEDA DO RETROVISOR INTERNO DANIFICOU O VIDRO",
        "REPARO INSATISFATÓRIO",
    ),
    "lateral": (
        "CHOQUE TERMICO",
        "CHUVA DE GRANIZO",
        "COLISÃO ACIDENTAL",
        "DANO ACIDENTAL CAUSADO POR PEDRA, OBJETO OU FRUTA",
        "DANO DESCARACTERIZADO - FOI REALIZADO ALGUM REPARO",
        "DURANTE FORTE VENTANIA,TEMPESTADE OU ENCHENTE",
        "ENCONTROU O VEICULO DANIFICADO",
        "ESQUECIMENTO DE CHAVE OU PESSOA DENTRO DO VEÍCULO",
        "PEÇA AMARELADA, MANCHADA OU ARRANHADA",
        "QUEBRA DO VIDRO PARA TENTATIVA DE ROUBO OU FURTO",
        "QUEBRA INTENCIONAL OU VOLUNTÁRIA",
        "VIDRO NÃO SOBE OU DESCE",
    ),
    "lanterna": (
        "AO TROCAR A LÂMPADA QUEBROU O ITEM",
        "CHUVA DE GRANIZO",
        "COLISÃO ACIDENTAL",
        "DANO ACIDENTAL CAUSADO POR PEDRA, OBJETO OU FRUTA",
        "DANO DESCARACTERIZADO - FOI REALIZADO ALGUM REPARO",
        "DANO NA PARTE ELETRICA",
        "DURANTE FORTE VENTANIA,TEMPESTADE OU ENCHENTE",
        "ENCONTROU O VEICULO DANIFICADO",
        "GARRA DANIFICADA",
        "INFILTRAÇÃO SEM TRINCA OU QUEBRA",
        "PELO TRANSPORTE DE CARGA",
        "PEÇA AMARELADA, MANCHADA OU ARRANHADA",
        "QUEBRA INTENCIONAL OU VOLUNTÁRIA",
        "ROUBO OU FURTO DA PEÇA",
    ),
    "lataria": (
        "CHUVA DE GRANIZO",
        "COLISÃO ACIDENTAL",
        "DANO DESCARACTERIZADO - FOI REALIZADO ALGUM REPARO",
        "DURANTE FORTE VENTANIA,TEMPESTADE OU ENCHENTE",
        "ENCONTROU O VEICULO DANIFICADO",
        "OUTROS",
        "QUEBRA INTENCIONAL OU VOLUNTÁRIA",
    ),
    # A UNIÃO das quatro (21 textos distintos), para as famílias que nenhuma
    # captura cobriu — vigia, farol, retrovisor, teto, para-choque. Oferecer a
    # união é melhor que oferecer nada: o agente pergunta com palavras que o
    # portal usa, e a lista ao vivo continua sendo quem decide.
    "": (
        "AO TROCAR A LÂMPADA QUEBROU O ITEM",
        "CHOQUE TERMICO",
        "CHUVA DE GRANIZO",
        "COLISÃO ACIDENTAL",
        "DANO ACIDENTAL CAUSADO POR PEDRA, OBJETO OU FRUTA",
        "DANO DESCARACTERIZADO - FOI REALIZADO ALGUM REPARO",
        "DANO NA PARTE ELETRICA",
        "DURANTE FORTE VENTANIA,TEMPESTADE OU ENCHENTE",
        "ENCONTROU O VEICULO DANIFICADO",
        "ESQUECIMENTO DE CHAVE OU PESSOA DENTRO DO VEÍCULO",
        "GARRA DANIFICADA",
        "INFILTRAÇÃO SEM TRINCA OU QUEBRA",
        "OUTROS",
        "PELO TRANSPORTE DE CARGA",
        "PEÇA AMARELADA, MANCHADA OU ARRANHADA",
        "QUEBRA DO VIDRO PARA TENTATIVA DE ROUBO OU FURTO",
        "QUEBRA INTENCIONAL OU VOLUNTÁRIA",
        "QUEDA DO RETROVISOR INTERNO DANIFICOU O VIDRO",
        "REPARO INSATISFATÓRIO",
        "ROUBO OU FURTO DA PEÇA",
        "VIDRO NÃO SOBE OU DESCE",
    ),
}


def causas_medidas_de(familia: Any = "") -> Tuple[str, ...]:
    """As causas MEDIDAS daquela família, ou a união quando não há captura dela.

    ⛔ Nunca é a lista final. É a dica com que o agente PERGUNTA antes de abrir.
    """
    return CAUSAS_MEDIDAS.get(str(familia or "").strip().lower(),
                              CAUSAS_MEDIDAS[""])


# 📊 Medido nas 4 capturas: `PerimetroDano` = `U` 3× e `R` 1×. **`N` nunca.**
#
# 🔴 O CAMPO É UM ENUM, E ESTA FUNÇÃO SÓ ACEITA O ENUM.
#
# A versão anterior tentava classificar o texto de gente aqui dentro, com
# `palavra in texto` — e o red team mediu o preço em 20/09/2026:
#
#     "o vidro quebrou na garagem de casa"  → R (rodoviário!)  ← "br " em "queBRou"
#     "abri a porta em casa"                → R                ← idem
#     "casado"                              → U                ← "casa" dentro
#     "pista de kart do shopping"           → R
#
# Substring não é vocabulário. A classificação do texto de gente MUDOU DE LUGAR:
# ela agora acontece **antes da fronteira A**, em
# `portal_params.normalizar_perimetro`, onde errar custa uma pergunta a mais e
# não um pedido gravado errado. Aqui, depois da fronteira, só entra o enum.
PERIMETRO_POR_ENUM: Dict[str, str] = {"urbano": "U", "rodoviario": "R"}


def perimetro_do_texto(valor: Any) -> str:
    """`"urbano"` → `"U"` · `"rodoviario"` → `"R"` · qualquer outra coisa → `""`.

    ⛔ Não classifica frase. Quem classifica é a coleta, antes de escrever.
    `""` faz o chamador PARAR — nunca cair em `"N"` (= "Não Sabe" no portal),
    que é uma resposta que o portal aceita e que mente sobre o segurado.
    """
    t = _norm(valor)
    if t in ("u", "r"):
        return t.upper()
    return PERIMETRO_POR_ENUM.get(t, "")

# 📊 Estático no `passo2.html`. Note que `6` está fora de sequência e **não
# existe 4** — decorar "é o quarto da lista" daria Corretor onde se queria Filho.
RELACAO_TITULAR: Dict[str, str] = {
    "1": "O Próprio",
    "2": "Cônjuge",
    "3": "Filho",
    "5": "Outros",
    "6": "Corretor",
}


# --------------------------------------------------------------------------
# 🔴 O corpo do `PATCH /atendimentos` — a regra é POR CAMPO, não uma regra só
# --------------------------------------------------------------------------
# 📊 Medido nas 4 capturas de 20/09/2026, com `importar_har`: o corpo tem
# **8 chaves, sempre as mesmas e sempre nesta ordem**, em 4 de 4 —
# `['CodigoItemCoberto', 'CodigoCidade', 'CodigoZona', 'CodigoObjetoCausa',
#   'AvaliacaoDano', 'PerimetroDano', 'Cep', 'ServicosMartelinhoLataria']`.
#
# O contrato do bundle tem 11 campos. Os 3 que somem não somem por serem
# `None`: eles somem porque o bundle os lê de `passo3.dados.X` sem ternário, e
# `JSON.stringify` **descarta `undefined`**. Dois campos escapam disso e sempre
# viajam, e é por isso que a regra não pode ser "omitir se None":
#
#     CodigoZona                  ternário explícito para `null` → viaja como null
#     ServicosMartelinhoLataria   `(t || []).map(…)` → array vazio ainda é array
#     ItemRemovido/EventoComposto/PolimentoFarol   → undefined, somem
#
# 🔴 Uma regra cega de "omitir se None" manda **6** chaves; mandar
# `"ItemRemovido": null` manda **11**. As duas quebram o gate, por lados opostos.
CHAVES_DO_PATCH: Tuple[str, ...] = (
    "CodigoItemCoberto", "CodigoCidade", "CodigoZona", "CodigoObjetoCausa",
    "AvaliacaoDano", "PerimetroDano", "Cep", "ServicosMartelinhoLataria",
)

# 📊 O portal exige relato com no mínimo 30 caracteres (a captura da lataria
# chegou com `COLISAO` preenchido com pontos até passar do limite). Saber disso
# ANTES da fronteira A é o que evita abrir um pedido e travar no passo 3.
MINIMO_AVALIACAO_DANO = 30


def corpo_de_atualizacao(*, codigo_item_coberto: str, codigo_cidade: Any,
                         codigo_objeto_causa: Any, avaliacao_dano: str,
                         perimetro_dano: str, cep: str = "",
                         codigo_zona: Optional[int] = None,
                         servicos_martelinho_lataria: Optional[list] = None,
                         item_removido: Optional[bool] = None,
                         evento_composto: Optional[bool] = None,
                         polimento_farol: Optional[bool] = None) -> Dict[str, Any]:
    """O corpo do PATCH, com a regra por campo aplicada. Função PURA."""
    corpo: Dict[str, Any] = {
        "CodigoItemCoberto": str(codigo_item_coberto or ""),
        "CodigoCidade": codigo_cidade,
        # sempre presente, ainda que `null`
        "CodigoZona": codigo_zona,
        "CodigoObjetoCausa": codigo_objeto_causa,
        "AvaliacaoDano": str(avaliacao_dano or ""),
        # 📊 o `value` do template é `opcao.substring(0,1)`: viaja a PRIMEIRA LETRA
        "PerimetroDano": str(perimetro_dano or "")[:1].upper(),
        "Cep": str(cep or ""),
        # sempre lista, nunca `null`
        "ServicosMartelinhoLataria": list(servicos_martelinho_lataria or []),
    }
    # 🔴 Estes três só existem no corpo quando foram RESPONDIDOS.
    if item_removido is not None:
        corpo["ItemRemovido"] = bool(item_removido)
    if evento_composto is not None:
        corpo["EventoComposto"] = bool(evento_composto)
    if polimento_farol is not None:
        corpo["PolimentoFarol"] = bool(polimento_farol)
    return corpo


# --------------------------------------------------------------------------
# ScriptFinalizacao — o texto que o portal manda dar ao segurado
# --------------------------------------------------------------------------
def script_de_finalizacao(atendimento: Any) -> Dict[str, Any]:
    """Lê o `ScriptFinalizacao` do agregado. **QUANDO se lê importa.**

    🔴 📊 Medido no HAR do para-brisa (20/09/2026): o mesmo `GET /atendimentos`
    devolve conteúdos diferentes conforme o momento.

        logo que o CodigoAtendimento nasce   Titulo "Seu atendimento já está com
                                             o analista responsável…",
                                             PrioridadeRetorno=true,
                                             InformacoesAdicionais = []  (0 itens)
        DEPOIS de `GET /agendamentos/opcoes-disponiveis`, com
        PossuiOrdemServico=true              Titulo "As informações abaixo serão
                                             encaminhadas por e-mail ou SMS.",
                                             PrioridadeRetorno=false,
                                             InformacoesAdicionais = 4 itens
                                             (Loja · Endereço · Ponto de
                                              Referência · Telefone)

    Ler antes é ler a versão sem loja — e entregar ao segurado "aguarde o
    analista" quando o portal já tinha decidido a oficina dele.
    """
    a = atendimento if isinstance(atendimento, dict) else {}
    sf = a.get("ScriptFinalizacao")
    sf = sf if isinstance(sf, dict) else {}
    infos = [i for i in (sf.get("InformacoesAdicionais") or []) if isinstance(i, dict)]
    por_titulo = {_norm(i.get("Titulo")): str(i.get("Valor") or "").strip()
                  for i in infos}
    loja_nome = por_titulo.get("loja", "")
    return {
        "titulo": str(sf.get("Titulo") or "").strip(),
        "rodape": str(sf.get("Rodape") or "").strip(),
        "mensagem_adas": str(sf.get("MensagemAdas") or "").strip(),
        "prioridade_retorno": sf.get("PrioridadeRetorno"),
        "informacoes": [{"titulo": str(i.get("Titulo") or "").strip(),
                         "valor": str(i.get("Valor") or "").strip()} for i in infos],
        "tem_loja": bool(loja_nome),
        "loja": {
            "nome": loja_nome,
            "endereco": por_titulo.get("endereco", ""),
            "referencia": por_titulo.get("ponto de referencia", ""),
            # 📊 o telefone vem com a orientação colada: "(NN) NNNNNNNNN (Entre
            # em contato com a loja para agendar o serviço)". Separar aqui evita
            # que a orientação vire parte do número numa mensagem de WhatsApp.
            "telefone": por_titulo.get("telefone", "").split("(Entre")[0].strip(),
            "orientacao": ("(Entre" + por_titulo["telefone"].split("(Entre")[1]).strip()
            if "(Entre" in por_titulo.get("telefone", "") else "",
        } if loja_nome else None,
    }


def descricao_da_franquia(atendimento: Any) -> Dict[str, Any]:
    """Extrai franquia do agregado `GET /atendimentos` — não da tela.

    🔴 Por que isto existe, e é importante:

    📊 Na interface, a franquia só aparece na tela de **conclusão (100%)**, no
    card `.aw-passo5-conclusao-card--franquia-acompanhar`. Mas o fluxo normal
    PARA antes disso, no 99%, aguardando o segurado escolher loja ou domicílio —
    que é exatamente o estado `REQUEST_CREATED_AWAITING_CUSTOMER_CHOICE` da
    SPEC-074.

    Ou seja: **raspando a tela, a franquia nunca chegaria ao segurado no momento
    em que ele pergunta.**

    📊 E a API já tem o fato muito antes: `Franquias.Franquias[]` vem populado
    logo após o `PATCH /atendimentos`, ainda no passo 3.

    Ler daqui não é otimização — é a diferença entre responder e não responder.
    """
    if not isinstance(atendimento, dict):
        return {"tem": False, "itens": [], "requer": None, "em_verificacao": None}
    bloco = atendimento.get("Franquias")
    if not isinstance(bloco, dict):
        return {"tem": False, "itens": [], "requer": None, "em_verificacao": None}
    itens = bloco.get("Franquias")
    lista = [
        {"titulo": str(i.get("Titulo") or ""), "valor": str(i.get("Valor") or "")}
        for i in (itens or []) if isinstance(i, dict)
    ] if isinstance(itens, list) else []
    return {
        "tem": bool(lista),
        "itens": lista,
        "requer": bloco.get("RequerFranquia"),
        "exibir_valor": bloco.get("ExibirValorDeFranquia"),
        "em_verificacao": None,   # a UI deriva de outro sinal; não inventamos
    }


def vistoria_do_atendimento(atendimento: Any) -> Dict[str, Any]:
    """Os campos de vistoria, exatamente como a API os nomeia.

    📊 `vistoria.mobi` **não aparece em nenhuma das três capturas** — nem no
    HAR, nem no HTML, nem no bundle. Aparece só no PDF que a atendente montou.

    O motivo está medido: nas sessões capturadas
    `PermiteVistoriaMobile: false` e `LinkVistoriaMobile: ""`. A seguradora não
    habilitou vistoria, então o link nunca foi gerado.

    🔴 Portanto: o campo é conhecido, o valor não. Nunca inventar o link; se
    vier vazio, o resultado diz que não há link — e é P-186/a atendente quem fecha
    isso com uma apólice que tenha vistoria habilitada.
    """
    a = atendimento if isinstance(atendimento, dict) else {}
    link = str(a.get("LinkVistoriaMobile") or "").strip()
    return {
        "link": link,
        "tem_link": bool(link),
        "permite_mobile": a.get("PermiteVistoriaMobile"),
        "permite_loja": a.get("PermiteVistoriaLoja"),
        "existe_criada": a.get("ExisteVistoriaCriada"),
        "finalizada": a.get("VistoriaFinalizada"),
        "online": a.get("VistoriaOnline"),
        "mensagem": a.get("MensagemVistoria"),
    }
