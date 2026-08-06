"""O nome de uma instância no Evolution Go nasce aqui, e em nenhum outro lugar.

POR QUE ISTO É UM MÓDULO, E NÃO TRÊS FUNÇÕES SOLTAS
====================================================
Nome de instância **não é detalhe de infraestrutura: é identidade de acervo.**
`observer_number` — metade da chave de deduplicação `(observer_number,
message_id)` — é `_digits()` do nome (`observer_intake._observer_number_of`):

    ab-obs-04b5cdbc04-1  →  045041
    ab-obs-6c9c55e22f-1  →  6955221

📊 86.801 linhas (69.150 transcrições + 17.651 eventos) dependem dessa derivação.
Trocar o nome troca a chave; trocar a chave faz o acervo deixar de casar, e o
repareamento seguinte **regrava tudo**.

📊 Auditoria de 06/08/2026 — três funções geravam nome, e as três discordavam:

    pairing_orchestrator._instance_name   base de 10   ab-obs-{b10}-1
    whatsapp_channel._go_instance_name    base de 12   ab-{b12}
    admin_atlas._obs_instance_name        base + seq   ab-obs-{b}-{seq}

E a prova estava viva no provedor: `ab-obs-04b5cdbc04-1` **e** `ab-04b5cdbc04cd`
coexistiam para a **mesma corretora e o mesmo WhatsApp**. Dois caminhos de código
criaram duas identidades para uma linha só. A segunda nunca foi pareada por
ninguém — era só confusão, esperando para virar acervo bifurcado.

A REGRA DO PRODUTO, QUE ESTE MÓDULO CODIFICA
=============================================
Decisão do Founder, 06/08/2026, com a decisão D-Canal-01 por trás:

    "Quero o mais simples possível para as corretoras. Não quero ter que toda
     hora parear uma coisa, depois outra."

    "O observador precisa ser ligado a hora, mas sempre ficar em silêncio e
     nunca responder. E também quero que o agente de atendimento esteja
     conectado, mas que ele não inicie ligado."

    "Só que precisam ser números separados [para cobrança] porque são serviços
     diferentes, mensagens diferentes."

Daí saem exatamente duas famílias:

**O número da corretora** — o WhatsApp que a equipe já atende. UM pareamento,
UM QR, servindo três funções sobre a mesma sessão:

    observador   sempre ligado, mudo, nunca responde
    atendimento  conectado desde o pareamento, DESLIGADO até o botão
    acionamento  fala com seguradora pelo mesmo número

Isso não é economia de instância: é o que o WhatsApp permite. 📊 No fork,
`/instance/*` e `/send/*` usam o **mesmo** `authMiddleware.Auth`
(`pkg/routes/routes.go:95-120`) — a mesma apikey que observa envia. Um segundo
pareamento para "poder responder" seria um segundo QR pedido à atendente para
obter um poder que a sessão já tem, gastando outro dos ~4 dispositivos vinculados
que o WhatsApp concede por número.

Quem garante o silêncio NÃO é uma instância separada — é
`observer_intake.observer_tap`, que consome o evento enquanto
`attendance_capture.attendance_agent_active` for falso, e falha para o lado do
silêncio quando não consegue confirmar.

**Os auxiliares** — cobrança à frente — são serviço diferente, mensagem
diferente e risco de bloqueio diferente. Esses têm número **próprio**, e por isso
nome próprio.
"""

from __future__ import annotations

from typing import Tuple

# Prefixo histórico do número da corretora. `-1` não é sequência: é o sufixo que
# o caminho normal sempre cravou, e é dele que saem os `observer_number` do
# acervo. Mudar qualquer um destes três pedaços é mudar a chave de dedup.
_PREFIXO_CORRETORA = "ab-obs"
_SUFIXO_CORRETORA = "1"
_PREFIXO_AUXILIAR = "ab-aux"

# Quantos caracteres do company_id entram no nome. Dez, e não doze, porque dez é
# o que as instâncias **em produção** já usam. O número certo aqui é o que o
# acervo já contém, não o que ficaria mais bonito.
_TAMANHO_DA_BASE = 10

# As funções que dividem o MESMO pareamento — o número da corretora.
FUNCOES_DO_NUMERO_DA_CORRETORA: Tuple[str, ...] = ("observer", "attendance", "dispatch")

PREFIXO_AUXILIAR = "auxiliary:"


def _base(company_id: str) -> str:
    return str(company_id or "").replace("-", "")[:_TAMANHO_DA_BASE]


def _slug(valor: str) -> str:
    return "".join(ch for ch in str(valor or "").lower() if ch.isalnum())[:10]


def escopo_de(purpose: str) -> str:
    """Normaliza o `purpose` para um dos dois escopos que existem de verdade.

    Devolve ``"corretora"`` ou ``"auxiliary:<slug>"``. Qualquer coisa que não
    seja auxiliar cai no número da corretora — inclusive valor desconhecido.
    O padrão é o conservador: um `purpose` novo e não previsto compartilha a
    linha existente em vez de criar um pareamento que ninguém pediu.
    """
    p = str(purpose or "observer").strip().lower()
    if p.startswith(PREFIXO_AUXILIAR):
        slug = _slug(p[len(PREFIXO_AUXILIAR):])
        return f"{PREFIXO_AUXILIAR}{slug}" if slug else "corretora"
    return "corretora"


def numero_proprio(purpose: str) -> bool:
    """Este propósito exige um WhatsApp SEPARADO (e portanto outro QR)?

    Verdadeiro só para auxiliares. Observador, atendimento e acionamento dividem
    a linha da corretora — pedir outro QR para eles seria pedir à atendente um
    pareamento a mais para um poder que a sessão dela já tem.
    """
    return escopo_de(purpose).startswith(PREFIXO_AUXILIAR)


def nome_da_instancia(company_id: str, purpose: str = "observer") -> str:
    """O nome desta corretora no Evolution Go, para este propósito.

    Determinístico: mesma corretora e mesmo escopo devolvem sempre o mesmo nome,
    hoje e daqui a um ano. É o que permite reencontrar a instância depois de a
    linha do banco ser desativada — e foi a falta disso que trancou o pareamento
    da Resulta (ver `identidade_da_instancia`).

    📊 Para `observer` o resultado é idêntico ao que produção já usa
    (`ab-obs-04b5cdbc04-1`), e isso é requisito, não coincidência: o acervo é
    indexado por ele.
    """
    base = _base(company_id)
    escopo = escopo_de(purpose)
    if escopo.startswith(PREFIXO_AUXILIAR):
        return f"{_PREFIXO_AUXILIAR}-{base}-{escopo[len(PREFIXO_AUXILIAR):]}"
    return f"{_PREFIXO_CORRETORA}-{base}-{_SUFIXO_CORRETORA}"


def purpose_canonico(purpose: str) -> str:
    """Sob qual `purpose` a linha de `integrations` deve ser procurada e gravada.

    Observador, atendimento e acionamento são UMA linha — a do `observer` — e não
    três. Manter três linhas para um pareamento foi o que produziu a instância
    órfã `ab-04b5cdbc04cd`: uma linha `attendance` ativa, com token e webhook
    próprios, apontando para um WhatsApp que nunca foi pareado por ninguém.
    """
    escopo = escopo_de(purpose)
    return "observer" if escopo == "corretora" else escopo


__all__ = [
    "nome_da_instancia",
    "purpose_canonico",
    "escopo_de",
    "numero_proprio",
    "FUNCOES_DO_NUMERO_DA_CORRETORA",
    "PREFIXO_AUXILIAR",
]
