"""A ficha do atendimento — o que o sistema já sabe, e que não pode esquecer.

O defeito que esta peça desfaz
------------------------------
📊 `grep -niE "\\bfase|phase|etapa|stage|slot" backend/app/agents/*.py` → **ZERO**.

O `AgentState` carrega mensagens, empresa, usuário, sessão, prompts e métricas.
E **nenhum campo** de fase, de dado já confirmado, ou de objetivo do atendimento.

A memória do que já foi perguntado **é a janela de contexto**: 60 mensagens.
Passou disso, o que o cliente respondeu no começo some, e o único remédio no
código é o prompt mandando *"RELEIA a conversa"*. O próprio comentário do
`langchain_service` registra que isso **já quebrou em produção** com janela
menor: o agente repediu o CPF do mesmo cliente.

E a tool de acionamento obriga o modelo a **re-declarar 15+ campos a cada
chamada**, reconstruídos do texto. Perdeu a janela, perdeu a coleta.

Num sinistro real — que passa de 60 mensagens com facilidade — isso significa
pedir de novo o CPF de alguém que acabou de bater o carro.

O laço que fecha
----------------
```
o modelo declara os slots na tool  →  a ficha GRAVA
                                          ↓
        o turno seguinte MOSTRA de volta  →  o modelo não repergunta
```

Duas propriedades que este módulo não abre mão:

**Nunca esquece um dado confirmado.** Merge é sempre aditivo: valor novo só
sobrescreve valor antigo se o novo não for vazio. Um turno em que o modelo
omite um campo não pode apagar o que o cliente já disse.

**A fase é DERIVADA, nunca declarada pelo modelo.** Ela é função do que existe
na ficha. Modelo não decide em que ponto o atendimento está — ele só informa o
que descobriu. Deixar o modelo escrever a fase seria deixá-lo dizer "já
acionei" sem ter acionado.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# As fases, na ordem em que um atendimento anda. Nomes em português porque
# aparecem na tela do corretor.
FASE_INTAKE = "intake"                  # chegou, ainda não se sabe o que é
FASE_IDENTIFICACAO = "identificacao"    # sabe-se o que é; falta saber quem é
FASE_COLETA = "coleta"                  # identificado; faltam dados do serviço
FASE_PRONTO = "pronto_para_acionar"     # tem tudo — pode acionar
FASE_ACIONADO = "acionado"              # a seguradora foi acionada
FASE_ACOMPANHANDO = "acompanhando"      # há protocolo; espera-se o prestador
FASE_COM_HUMANO = "com_humano"          # devolvido a uma pessoa
FASE_RESOLVIDO = "resolvido"            # acabou, com motivo escrito

ORDEM_DAS_FASES: List[str] = [
    FASE_INTAKE, FASE_IDENTIFICACAO, FASE_COLETA, FASE_PRONTO,
    FASE_ACIONADO, FASE_ACOMPANHANDO, FASE_COM_HUMANO, FASE_RESOLVIDO,
]

# Rótulos legíveis para o bloco que vai ao modelo. Chave técnica não ajuda o
# modelo a conversar: "titular_cpf" vira "CPF do titular".
ROTULOS = {
    "titular_cpf": "CPF do titular",
    "titular_nome": "nome do titular",
    "telefone_contato": "telefone de contato",
    "veiculo_placa": "placa do veículo",
    "local_atual": "onde o veículo está",
    "local_destino": "para onde levar",
    "endereco_numero": "número do endereço",
    "problema_descricao": "o que aconteceu",
    "periodo_preferido": "período preferido",
    "risco_confirmado_sem_fumaca": "confirmação de que não há fumaça/faísca",
    "aparelho_marca_modelo": "marca e modelo do aparelho",
    "aparelho_idade": "idade do aparelho",
}

_VAZIOS = ("", "none", "null", "nao informado", "não informado", "n/a", "-")


def _tem_valor(v: Any) -> bool:
    """Um slot só conta como confirmado se tiver conteúdo de verdade.

    O modelo às vezes preenche com `"não informado"` para não deixar o campo em
    branco. Aceitar isso como confirmado faria a ficha declarar completo um
    atendimento que não está — e o acionamento sairia sem o dado.
    """
    if v is None or isinstance(v, bool):
        return bool(v) if isinstance(v, bool) else False
    s = str(v).strip()
    return bool(s) and s.lower() not in _VAZIOS


def ficha_vazia() -> Dict[str, Any]:
    return {
        "fase": FASE_INTAKE,
        "ramo": "", "servico": "", "seguradora": "",
        "confirmados": {},
        "apolice_confirmada": False,
        "acionamento": {},
        "atualizada_em": None,
        "historico": [],
    }


def derivar_fase(ficha: Dict[str, Any], obrigatorios: Optional[List[str]] = None) -> str:
    """A fase é consequência do que se sabe — não uma opinião do modelo.

    Ordem de precedência de cima para baixo: um caso resolvido não volta a ser
    coleta porque o cliente mandou mais uma mensagem; um caso com humano não
    volta a ser automático sozinho.
    """
    if ficha.get("resolvido_em"):
        return FASE_RESOLVIDO
    if ficha.get("fase") == FASE_COM_HUMANO:
        return FASE_COM_HUMANO

    acion = ficha.get("acionamento") or {}
    if acion.get("protocolo"):
        return FASE_ACOMPANHANDO
    if acion.get("enviado_em"):
        return FASE_ACIONADO

    confirmados = ficha.get("confirmados") or {}
    faltando = [s for s in (obrigatorios or []) if not _tem_valor(confirmados.get(s))]

    if obrigatorios and not faltando and ficha.get("apolice_confirmada"):
        return FASE_PRONTO
    if confirmados or ficha.get("servico"):
        return FASE_COLETA
    if ficha.get("ramo"):
        return FASE_IDENTIFICACAO
    return FASE_INTAKE


def fundir(ficha: Dict[str, Any], novidades: Dict[str, Any],
           obrigatorios: Optional[List[str]] = None) -> Dict[str, Any]:
    """Junta o que o turno descobriu ao que já se sabia. **Sempre aditivo.**

    Um turno em que o modelo não repete um campo NÃO pode apagar o que o cliente
    já respondeu — é literalmente o defeito que estamos consertando. Valor novo
    só entra se tiver conteúdo.
    """
    nova = dict(ficha or ficha_vazia())
    nova.setdefault("confirmados", {})
    nova.setdefault("historico", [])
    fase_antes = nova.get("fase")

    for campo in ("ramo", "servico", "seguradora"):
        if _tem_valor(novidades.get(campo)):
            nova[campo] = str(novidades[campo]).strip().lower()

    for chave, valor in (novidades.get("confirmados") or {}).items():
        if _tem_valor(valor):
            nova["confirmados"][chave] = valor

    if novidades.get("apolice_confirmada") is True:
        nova["apolice_confirmada"] = True          # confirmação não se desfaz sozinha
    if novidades.get("acionamento"):
        nova["acionamento"] = {**(nova.get("acionamento") or {}),
                               **(novidades["acionamento"] or {})}
    if novidades.get("fase") == FASE_COM_HUMANO:
        nova["fase"] = FASE_COM_HUMANO
    if novidades.get("resolvido_em"):
        nova["resolvido_em"] = novidades["resolvido_em"]
        nova["resolucao_motivo"] = novidades.get("resolucao_motivo") or ""

    nova["fase"] = derivar_fase(nova, obrigatorios)
    nova["atualizada_em"] = datetime.now(timezone.utc).isoformat()

    if nova["fase"] != fase_antes:
        # O histórico é curto de propósito: serve para explicar o caso a um
        # humano, não para virar log de auditoria (esse é o `agent_activities`).
        nova["historico"] = (nova["historico"] + [{
            "fase": nova["fase"], "em": nova["atualizada_em"],
        }])[-12:]
    return nova


def bloco_para_o_prompt(ficha: Dict[str, Any],
                        obrigatorios: Optional[List[str]] = None) -> str:
    """O que o modelo vê no começo do turno. Curto, e sem enfeite.

    Não repetimos a conversa — ela já está no histórico. Repetimos só o que o
    histórico pode ter perdido: o que foi CONFIRMADO e o que ainda FALTA.
    """
    if not ficha or ficha.get("fase") in (None, FASE_INTAKE):
        if not (ficha or {}).get("confirmados"):
            return ""

    confirmados = ficha.get("confirmados") or {}
    linhas = ["=== 📋 FICHA DESTE ATENDIMENTO (já apurado) ==="]

    cabeca = " · ".join(x for x in (ficha.get("ramo"), ficha.get("servico"),
                                    ficha.get("seguradora")) if x)
    if cabeca:
        linhas.append(f"Caso: {cabeca}")
    linhas.append(f"Fase: {ficha.get('fase')}")

    if confirmados:
        linhas.append("JÁ CONFIRMADO com o cliente — **não pergunte de novo**:")
        for chave, valor in confirmados.items():
            linhas.append(f"  · {ROTULOS.get(chave, chave)}: {valor}")

    faltando = [s for s in (obrigatorios or []) if not _tem_valor(confirmados.get(s))]
    if faltando:
        linhas.append("AINDA FALTA para poder acionar:")
        for s in faltando:
            linhas.append(f"  · {ROTULOS.get(s, s)}")

    acion = ficha.get("acionamento") or {}
    if acion.get("protocolo"):
        linhas.append(f"Protocolo já obtido: {acion['protocolo']} — "
                      "acompanhe, não acione de novo.")

    linhas.append("Se um dado acima estiver errado, o cliente vai corrigir. "
                  "Até lá, trate como verdade e siga do ponto em que parou.")
    return "\n".join(linhas)


# --------------------------------------------------------------------- #
# I/O — sempre com company_id (CLAUDE.md §7)
# --------------------------------------------------------------------- #

async def carregar(supabase, company_id: str, session_id: str) -> Dict[str, Any]:
    """Lê a ficha da conversa. Falha de leitura devolve ficha vazia.

    Ficha vazia faz o agente perguntar de novo — chato, mas correto. Inventar
    dado que não foi lido seria pior: o acionamento sairia com informação que
    ninguém confirmou.
    """
    import asyncio

    if not company_id or not session_id:
        return ficha_vazia()
    try:
        def _q():
            return (supabase.table("conversations")
                    .select("ficha_atendimento")
                    .eq("company_id", str(company_id))
                    .eq("session_id", str(session_id))
                    .limit(1).execute())

        res = await asyncio.to_thread(_q)
        if res.data and isinstance(res.data[0].get("ficha_atendimento"), dict):
            base = ficha_vazia()
            base.update(res.data[0]["ficha_atendimento"])
            return base
    except Exception as exc:  # noqa: BLE001
        logger.warning("[FICHA] leitura falhou (%s) — seguindo sem ficha",
                       type(exc).__name__)
    return ficha_vazia()


async def gravar(supabase, company_id: str, session_id: str,
                 novidades: Dict[str, Any],
                 obrigatorios: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
    """Funde e grava. Nunca derruba o turno: a resposta ao cliente vale mais."""
    import asyncio

    if not company_id or not session_id or not novidades:
        return None
    try:
        atual = await carregar(supabase, company_id, session_id)
        nova = fundir(atual, novidades, obrigatorios)

        def _u():
            dados: Dict[str, Any] = {"ficha_atendimento": nova}
            if nova.get("resolvido_em"):
                dados["resolvido_em"] = nova["resolvido_em"]
                dados["resolucao_motivo"] = nova.get("resolucao_motivo") or ""
            return (supabase.table("conversations").update(dados)
                    .eq("company_id", str(company_id))
                    .eq("session_id", str(session_id)).execute())

        await asyncio.to_thread(_u)
        logger.info("[FICHA] empresa=%s fase=%s confirmados=%d",
                    company_id, nova.get("fase"), len(nova.get("confirmados") or {}))
        return nova
    except Exception as exc:  # noqa: BLE001
        logger.error("[FICHA] gravação falhou (%s) — o atendimento segue, mas "
                     "este turno não deixou memória", type(exc).__name__)
        return None
