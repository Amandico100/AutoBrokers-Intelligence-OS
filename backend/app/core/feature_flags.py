"""Feature flags da plataforma (somente leitura de ambiente, sem dependências).

POLICY_INTELLIGENCE_V2 — SPEC-016. OFF (default) = comportamento do baseline
e7c5044; ON = contexto anafórico v2 + Policy Facts + política de assistência +
compositor humano. Flag única de rollback da Onda 1.

🔴 SPEC-088 (rodada de conserto): `env_ligada()` passou a ser o ÚNICO leitor de
"esta variável liga alguma coisa?" desta casa. O registro de agentes declara
`desligado_quando={"env_falso": "ALFAIATE_AUTO_APPLY"}` e precisa da MESMA
resposta que o módulo do Alfaiate dá — duas listas de valores verdadeiros
divergiriam, e a que ficasse para trás pintaria o card ao contrário do produto
(CLAUDE.md §5: consolidar, nunca duplicar ao lado).
"""

import os

#: 🔴 LISTA FECHADA, e não `bool(valor)`. ⚠️ 📊 `bool("false")` é `True`, e foi
#: exatamente assim que a SPEC-093 quase ligou um agente de atendimento com um
#: `PATCH {"is_active": "false"}`. `sim` está aqui porque o Founder configura em
#: português.
_TRUTHY = {"1", "true", "yes", "on", "sim"}


def env_ligada(nome: str, padrao: str = "") -> bool:
    """A variável `nome` diz SIM? ⛔ Ausente, vazia ou desconhecida = desligada."""
    return str(os.getenv(nome, padrao) or "").strip().lower() in _TRUTHY


def policy_intelligence_v2_enabled() -> bool:
    return env_ligada("POLICY_INTELLIGENCE_V2")
