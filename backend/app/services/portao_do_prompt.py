"""O portão do prompt, do lado do BACKEND — a mesma regra, não uma segunda.

P-38. Havia um portão, e ele era de um runtime só.
--------------------------------------------------
A SPEC-063 Bloco P construiu o portão que impede um agente de nascer mudo, e
P-36 o levou aos quatro caminhos de TypeScript que escrevem
``agents.agent_system_prompt``. Sobrou o que nenhum deles alcança:

    backend/app/services/agent_service.py   update_agent / create_agent
    backend/app/api/agent_config.py         companies.agent_system_prompt (legado)

📊 Provado por execução em 04/08/2026: ``AgentUpdate(agent_system_prompt='')``
produz ``model_dump(exclude_unset=True) == {'agent_system_prompt': ''}`` — uma
string vazia gravada por cima de um prompt que funcionava, sem validação de
tamanho, sem releitura, e (até este commit) sem sequer ``.eq("company_id")``.
A rota existe e é alcançável pela UI de super-admin:

    app/admin/companies/[companyId]/agents/page.tsx
      → app/api/admin/proxy/agents/[[...path]]/route.ts   (repassa cego)
        → backend/app/api/agents.py  PUT /{agent_id}      (:260)

É a hipótese mais forte para a AutoFleet ter ficado com agente ATIVO e prompt
de ZERO caracteres (📊 auditoria de 02/08/2026,
``docs/canon/reports/SPEC-063-BLOCO-0-AUDITORIA.md``, Parte C.6).

Por que este arquivo não é um segundo portão (CLAUDE.md §5)
-----------------------------------------------------------
Um portão em Python não pode ser um ``import`` de TypeScript. O que se espelha
é o CONTRATO — as medidas, os marcadores de bloco e os NOMES dos motivos —, e
ele vive num arquivo só: ``lib/admin/portao-do-prompt.contract.json``.

O TypeScript o importa. Este módulo NÃO consegue: a imagem do backend é
construída com contexto ``backend/`` (``backend/Dockerfile``: ``COPY . .``) e
não enxerga ``lib/``. Ler o arquivo em runtime daria um módulo que funciona no
repositório e explode em produção. Então os valores são declarados aqui, e
``backend/tests/test_o_portao_vale_no_backend.py`` lê o JSON e prova que são os
mesmos — número por número, nome por nome. Divergir passou a exigir passar por
um teste vermelho.

A regra, inteira
----------------
    1. prompt não-vazio
    2. e que não seja SÓ a casca de guardrails
    3. e com um mínimo de caracteres
    4. releitura pós-escrita — "gravei" é fato lido de volta, não requisição
    5. e o que ficou mudo é DESLIGADO, não deixado ativo-e-mudo

Este módulo não importa nada de ``app.*`` de propósito: o teste o carrega
sozinho, sem supabase, sem FastAPI e sem variável de ambiente.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence

# ---------------------------------------------------------------------------
# O CONTRATO — espelho de lib/admin/portao-do-prompt.contract.json
# ---------------------------------------------------------------------------
# Mexer num número aqui sem mexer lá (ou o contrário) deixa
# test_o_portao_vale_no_backend.py VERMELHO. É essa a trava.

#: Prompt final composto (personalização + guardrails). 📊 O menor agente REAL
#: em produção tem 636 caracteres (query em 04/08/2026 sobre `agents`,
#: `select length(agent_system_prompt) ... order by 1` → 636, 638, 650, 813,
#: 1533, 1535, 1539, 7914). A barra de 400 não recusa nada que exista.
PROMPT_MINIMO_CHARS = 400

#: Só a parte personalizada, sem a casca. 📊 A menor real hoje passa de 60.
PERSONALIZACAO_MINIMA_CHARS = 120

CABECALHO_PERSONALIZACAO = "=== PERSONALIZACAO DA CORRETORA"
CABECALHO_GUARDRAILS = "=== REGRAS IMUTAVEIS DO AUTOBROKERS"

PLACEHOLDER_PENDENTE = r"\{\{\s*[a-z0-9_]+\s*\}\}"

MOTIVOS: Dict[str, str] = {
    "prompt_vazio": "prompt_vazio",
    "prompt_so_guardrails": "prompt_so_guardrails",
    "prompt_curto_demais": "prompt_curto_demais",
    "personalizacao_vazia": "personalizacao_vazia",
    "personalizacao_curta": "personalizacao_curta",
    "placeholder_nao_resolvido": "placeholder_nao_resolvido",
    "prompt_de_autoria_vazio": "prompt_de_autoria_vazio",
    "prompt_de_autoria_curto": "prompt_de_autoria_curto",
    "prompt_vazio_apos_escrita": "prompt_vazio_apos_escrita",
    "agente_desligado": "agente_desligado",
}

_PLACEHOLDER_RE = re.compile(PLACEHOLDER_PENDENTE, re.IGNORECASE)


# ---------------------------------------------------------------------------
# 1. A MEDIDA — o que a corretora efetivamente instruiu
# ---------------------------------------------------------------------------

def personalizacao_do_prompt(prompt: Optional[str]) -> str:
    """A parte de cima do prompt composto — sem o bloco de regras imutáveis.

    Espelho exato de ``personalizacaoDoPrompt`` em ``lib/admin/agent-health.ts``.
    Prompt escrito à mão (sem a moldura) devolve o texto inteiro: quem digitou
    a instrução na unha instruiu de verdade, e a ausência de cabeçalho não pode
    ser lida como ausência de voz.
    """
    texto = str(prompt or "")
    fim = texto.find(CABECALHO_GUARDRAILS)
    acima = texto[:fim] if fim >= 0 else texto
    inicio = acima.find(CABECALHO_PERSONALIZACAO)
    if inicio < 0:
        return acima.strip()
    quebra = acima.find("\n", inicio)
    return "" if quebra < 0 else acima[quebra + 1:].strip()


def estado_da_voz(prompt: Optional[str]) -> str:
    """``ok`` · ``vazio`` · ``so_guardrails``. Os dois últimos são MUDO.

    Espelho de ``estadoDaVoz`` em ``lib/admin/agent-health.ts``. O segundo é o
    que uma checagem ingênua deixa passar: ~560 caracteres de moldura e regras,
    e nenhuma linha sobre o que o agente é ou faz.
    """
    if not str(prompt or "").strip():
        return "vazio"
    return "ok" if personalizacao_do_prompt(prompt) else "so_guardrails"


# ---------------------------------------------------------------------------
# 2. O PORTÃO — antes de qualquer escrita
# ---------------------------------------------------------------------------

def problemas_do_prompt(prompt_final: Optional[str], personalizado: Optional[str]) -> List[str]:
    """Espelho de ``problemasDoPrompt`` (provision-tenant.ts). Vazia = pode gravar."""
    problemas: List[str] = []
    final = str(prompt_final or "").strip()
    pessoal = str(personalizado or "").strip()

    if not final:
        problemas.append(MOTIVOS["prompt_vazio"])
    elif len(final) < PROMPT_MINIMO_CHARS:
        problemas.append(f'{MOTIVOS["prompt_curto_demais"]}:{len(final)}')

    if not pessoal:
        problemas.append(MOTIVOS["personalizacao_vazia"])
    elif len(pessoal) < PERSONALIZACAO_MINIMA_CHARS:
        problemas.append(f'{MOTIVOS["personalizacao_curta"]}:{len(pessoal)}')

    # `{{company_name}}` sobrando significa que a variável não chegou: o agente
    # se apresentaria com as chaves literais na frente do corretor.
    if final and _PLACEHOLDER_RE.search(final):
        problemas.append(MOTIVOS["placeholder_nao_resolvido"])

    return problemas


def problemas_do_prompt_de_autoria(prompt: Optional[str], minimo_chars: int) -> List[str]:
    """Espelho de ``problemasDoPromptDeAutoria``. Para prompt TIPADO por gente.

    É o portão certo para o backend: quem edita pela UI de super-admin escreve o
    texto FINAL na unha — ninguém soma a casca de guardrails por cima, então a
    medida dupla de ``problemas_do_prompt`` não se aplica. O que sobra, e é o
    que mata, é o vazio.

    O chamador escolhe o mínimo porque os dois casos são legítimos e diferentes:
    um agente CORE/ATENDIMENTO vale ``PERSONALIZACAO_MINIMA_CHARS``; um auxiliar
    nasce com um esboço de uma frase de propósito, e ali o mínimo é 1 — a mesma
    escolha que ``createSourceAuxiliary`` já faz do lado TypeScript.
    """
    texto = str(prompt or "").strip()
    if not texto:
        return [MOTIVOS["prompt_de_autoria_vazio"]]
    if len(texto) < minimo_chars:
        return [f'{MOTIVOS["prompt_de_autoria_curto"]}:{len(texto)}']
    # Casca sem instrução é muda por dentro, tenha o tamanho que tiver.
    if estado_da_voz(texto) == "so_guardrails":
        return [MOTIVOS["prompt_so_guardrails"]]
    return []


def problemas_da_escrita_de_prompt(
    valor: Any, minimo_chars: int = PERSONALIZACAO_MINIMA_CHARS
) -> List[str]:
    """O portão na forma em que o backend precisa dele: sobre o VALOR a gravar.

    ``None`` é ausência — quem não mandou a chave não está escrevendo o prompt, e
    um PATCH de ``llm_model`` não pode ser recusado por causa de um campo que ele
    nem tocou. String vazia é o contrário: é uma escrita, e é a que emudece.
    """
    if valor is None:
        return []
    return problemas_do_prompt_de_autoria(str(valor), minimo_chars)


# ---------------------------------------------------------------------------
# 3. A RELEITURA — "gravei" é fato lido de volta
# ---------------------------------------------------------------------------

class ResultadoDaConferencia:
    """Veredito da releitura. ``ok=False`` significa que o agente foi DESLIGADO."""

    __slots__ = ("ok", "chars", "reason")

    def __init__(self, ok: bool, chars: int, reason: Optional[str] = None) -> None:
        self.ok = ok
        self.chars = chars
        self.reason = reason

    def __repr__(self) -> str:  # pragma: no cover - conveniência de depuração
        return f"ResultadoDaConferencia(ok={self.ok}, chars={self.chars}, reason={self.reason!r})"


#: Como se desliga cada tabela que guarda um prompt.
#:
#: 🔴 CORRIGIDO EM 17/08/2026 (SPEC-078 A.4). Este comentário dizia que
#: `companies` era "ainda lida pelo runtime em `backend/app/agents/nodes.py:438`".
#: 📊 `grep agent_enabled backend/app/agents/nodes.py` → **ZERO ocorrências**.
#: A linha 438 daquele arquivo monta o system prompt e não olha coluna nenhuma
#: de liga/desliga. O comentário mandava o próximo leitor conferir um
#: interruptor que não existe — e é assim que se ganha um segundo interruptor
#: por engano, onde a SPEC-045 estabeleceu que há UM só.
#:
#: A VERDADE MEDIDA: `agent_enabled` (em `companies` e em `agents`) é coluna
#: **LEGADA, sem leitor no runtime**. Quem decide se o agente responde é
#: `agents.is_active` do papel `attendance`, lido por
#: `attendance_capture.attendance_agent_active()`. É por isso que os quatro
#: agentes desligados do produto estão com `agent_enabled = true` sem
#: contradição nenhuma: esse `true` não liga nada.
#:
#: Continuo escrevendo `agent_enabled: False` aqui de propósito — desligar uma
#: coluna morta não custa nada, e no dia em que alguém a ressuscitar ela já
#: nasce do lado seguro. `is_active` de `companies` NÃO serve para isso: numa
#: empresa ela significa outra coisa (a corretora existir).
_DESLIGA_POR_TABELA: Dict[str, Dict[str, Any]] = {
    "agents": {"is_active": False, "agent_enabled": False},
    "companies": {"agent_enabled": False},
}


def conferir_prompt_gravado(
    client: Any, company_id: Optional[str], agent_id: str, origem: str,
    tabela: str = "agents",
) -> ResultadoDaConferencia:
    """Relê do BANCO o que ficou gravado e DESLIGA quem ficou mudo.

    Espelho de ``conferirPromptGravado`` (provision-tenant.ts). Trigger, default
    de coluna, RPC que ignora um campo ou coluna truncada aparecem aqui — não na
    primeira conversa do segurado.

    Silêncio é melhor que um agente ativo sem uma linha de instrução e sem
    nenhuma trava: por isso a consequência é desligar, não só reportar.

    ``company_id`` entra em TODAS as consultas quando é conhecido (CLAUDE.md §7:
    o backend usa service role, e RLS sem policy não protege contra erro de
    filtro no código). Em ``tabela='companies'`` o id JÁ É o tenant, e repetir o
    filtro seria a mesma coluna duas vezes.
    """
    desliga = _DESLIGA_POR_TABELA.get(tabela)
    if desliga is None:
        return ResultadoDaConferencia(False, 0, f"tabela_desconhecida:{tabela}")
    escopar = bool(company_id) and tabela != "companies"

    try:
        q = client.table(tabela).select("agent_system_prompt").eq("id", str(agent_id))
        if escopar:
            q = q.eq("company_id", str(company_id))
        res = q.limit(1).execute()
        linhas = getattr(res, "data", None) or []
        gravado = str((linhas[0] or {}).get("agent_system_prompt") or "") if linhas else ""
    except Exception as exc:  # noqa: BLE001
        # Não dá para afirmar que gravou nem que não gravou. Fail-closed: quem
        # chamou trata como falha, e o agente NÃO é declarado saudável.
        return ResultadoDaConferencia(False, 0, f"releitura_falhou:{origem}:{type(exc).__name__}")

    if estado_da_voz(gravado) == "ok":
        return ResultadoDaConferencia(True, len(gravado))

    try:
        upd = client.table(tabela).update(dict(desliga)).eq("id", str(agent_id))
        if escopar:
            upd = upd.eq("company_id", str(company_id))
        upd.execute()
        desligou = MOTIVOS["agente_desligado"]
    except Exception:  # noqa: BLE001
        desligou = "nao_consegui_desligar"

    return ResultadoDaConferencia(
        False, len(gravado),
        f'{MOTIVOS["prompt_vazio_apos_escrita"]}:{origem}:{desligou}',
    )


# ---------------------------------------------------------------------------
# 4. Nascer desligado — o equivalente de `materializarAgente` no insert
# ---------------------------------------------------------------------------

def desligar_se_nascer_mudo(payload: Dict[str, Any], minimo_chars: int = 1) -> Dict[str, Any]:
    """Devolve o payload de insert com ``is_active``/``agent_enabled`` em False
    quando o prompt que vem nele não serve.

    📊 É o furo do ``lib/admin/agent-blueprints.ts:40`` visto do outro lado do
    fio: ``agent_system_prompt: s('agent_system_prompt') || undefined`` faz a
    CHAVE SUMIR do JSON, e a linha seguinte manda ``is_active: true``. O agente
    nasce com prompt NULL e ativo. O backend é o último a poder impedir isso, e
    é o único que vê o payload já montado.

    Não levanta erro: criar um auxiliar mudo e DESLIGADO é recuperável (alguém
    escreve o prompt e liga); recusar a criação inteira quebraria o fluxo de
    publicação de auxiliar, que hoje aceita esboço de uma frase.
    """
    novo = dict(payload or {})
    if problemas_da_escrita_de_prompt(novo.get("agent_system_prompt"), minimo_chars):
        novo["is_active"] = False
        novo["agent_enabled"] = False
    elif novo.get("agent_system_prompt") is None:
        # Chave ausente: não há prompt nenhum, e o default da coluna é NULL.
        novo["is_active"] = False
        novo["agent_enabled"] = False
    return novo


__all__: Sequence[str] = (
    "PROMPT_MINIMO_CHARS", "PERSONALIZACAO_MINIMA_CHARS",
    "CABECALHO_PERSONALIZACAO", "CABECALHO_GUARDRAILS",
    "PLACEHOLDER_PENDENTE", "MOTIVOS",
    "personalizacao_do_prompt", "estado_da_voz",
    "problemas_do_prompt", "problemas_do_prompt_de_autoria",
    "problemas_da_escrita_de_prompt",
    "ResultadoDaConferencia", "conferir_prompt_gravado",
    "desligar_se_nascer_mudo",
)
