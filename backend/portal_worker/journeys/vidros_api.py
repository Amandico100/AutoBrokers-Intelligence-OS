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
    """Allowlist fechada. Descoberta não vira cliente HTTP de URL livre."""
    u = str(url or "").lower()
    return any(f"//{h}" in u or f".{h}" in u for h in HOSTS_PERMITIDOS)


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

# 📊 Declarado no bundle, não exercido em nenhuma captura. Só entra em uso
# depois de medido — SPEC-073 G3: candidato ≠ aprovado.
EP_FINALIZAR_NAO_MEDIDO = "/atendimentos/finalizar"
EP_VISTORIA_MOBILE_NAO_MEDIDO = "/atendimentos/vistoriamobile"

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

# 📊 Estático no `passo2.html`. Note que `6` está fora de sequência e **não
# existe 4** — decorar "é o quarto da lista" daria Corretor onde se queria Filho.
RELACAO_TITULAR: Dict[str, str] = {
    "1": "O Próprio",
    "2": "Cônjuge",
    "3": "Filho",
    "5": "Outros",
    "6": "Corretor",
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
    HAR, nem no HTML, nem no bundle. Aparece só no PDF que a Regina montou.

    O motivo está medido: nas sessões capturadas
    `PermiteVistoriaMobile: false` e `LinkVistoriaMobile: ""`. A seguradora não
    habilitou vistoria, então o link nunca foi gerado.

    🔴 Portanto: o campo é conhecido, o valor não. Nunca inventar o link; se
    vier vazio, o resultado diz que não há link — e é P-186/Regina quem fecha
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
