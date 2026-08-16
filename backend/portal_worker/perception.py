# -*- coding: utf-8 -*-
"""Percepção em camadas e o validador determinístico — SPEC-073 Bloco E e F.

A escada, e por que a ordem é essa
==================================
    L0  fato determinístico ....... já sabemos. Não se pergunta a modelo o que
                                    já está no payload.
    L1  API legítima do portal .... a própria aplicação já responde estruturado
    L2  DOM semântico ............. Playwright lendo o que a tela declara
    L3  modelo textual ............ julgamento sobre estado estruturado
    L4  visão multimodal .......... quando o DOM não representa o que se vê
    L5  humano .................... com dossiê suficiente para agir

Sobe-se de degrau só quando o anterior **não resolve com confiança**. Isso não
é economia de token: é redução de aleatoriedade. Cada degrau acima troca uma
resposta determinística por uma probabilística.

🔴 O buraco que este módulo fecha
=================================
📊 Medido em 16/08/2026 no `adaptive.py`: `select` (nativo e `md-select`) tinha
validação forte — lê as opções reais, exige match confiante, devolve as opções
ao cérebro quando o campo é crítico. Mas:

    fill  ....... `apply_action` escrevia o `value` cru do modelo, sem checar
                  nada, num input casado por SUBSTRING nos dois sentidos
    click ....... `_click_button` clicava qualquer botão cujo label contivesse
                  o texto. A proibição de "Agendar na loja" / "Cancelar
                  atendimento" existia **só como frase no prompt**
    check ....... clicava o primeiro label visível que contivesse o texto,
                  sem consultar o vocabulário de atributo

Ou seja: três superfícies de ação com um terço do rigor da quarta. Um modelo
não precisa ser malicioso para clicar em "Agendar a domicílio" — basta ele
achar que é o próximo passo.

**Aqui as quatro passam pelo mesmo funil.**
"""
from __future__ import annotations

import logging
import os
import re
import unicodedata  # noqa: F401  (usado por _norm)
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, Sequence, Tuple

from portal_worker import guardrails as G

logger = logging.getLogger(__name__)

# Camadas, na ordem da escada.
L0_FATO = "deterministic"
L1_API = "api"
L2_DOM = "dom"
L3_TEXTO = "adaptive"
L4_VISAO = "vision"
L5_HUMANO = "human"

ESCADA: Tuple[str, ...] = (L0_FATO, L1_API, L2_DOM, L3_TEXTO, L4_VISAO, L5_HUMANO)

ACOES_VALIDAS: Tuple[str, ...] = ("fill", "select", "click", "check", "done", "ask_human")


def _norm(txt: Any) -> str:
    """minúsculas, sem acento, espaço colapsado — o mesmo normalizador do resto."""
    s = unicodedata.normalize("NFKD", str(txt or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().lower()


# --------------------------------------------------------------------------
# Botões que MUDAM O MUNDO. Antes disto, a lista vivia dentro do prompt.
# --------------------------------------------------------------------------
# 🔴 Uma proibição escrita em prompt é uma sugestão. O modelo obedece quase
# sempre — e "quase sempre" aplicado a "cancelar atendimento" é um incidente
# esperando data. Aqui a lista é código, e o guard é quem libera.
BOTOES_MATERIAIS: Tuple[str, ...] = (
    "confirmar", "confirmo", "finalizar", "concluir", "enviar solicitacao",
    "enviar pedido", "agendar", "agendamento", "marcar horario",
    "agendar na loja", "agendar a domicilio", "agendar em domicilio",
    "cancelar atendimento", "cancelar solicitacao", "excluir",
    "alterar pagamento", "trocar forma de pagamento", "gerar boleto",
    "aceito", "aceitar termo", "assinar", "contratar", "efetivar",
    "solicitar atendimento", "abrir atendimento", "salvar e enviar",
)

# Campos cujo valor errado é dano real, não retrabalho. Espelha `_CRITICOS` do
# adaptive e acrescenta o que a auditoria mostrou faltar.
CAMPOS_CRITICOS: Tuple[str, ...] = (
    "peca", "item", "danificad", "causa", "como ocorreu", "lado", "motorista",
    "carona", "dianteir", "traseir", "posicao", "trincad", "tamanho",
    "cobertura", "servico", "loja", "oficina", "data", "hora", "horario",
    "pagamento", "parcela", "vidro", "farol", "lanterna", "retrovisor",
    "pelicula", "local", "uf", "estado", "cidade",
)

# Checkbox que não pode ser marcada por iniciativa do modelo.
# 📊 O mapa §6 manda deixar a de WhatsApp desmarcada enquanto o telefone do
# passo 2 for o da corretora — senão a seguradora manda atualização de
# atendimento para o número do corretor, achando que é o do segurado.
CHECKBOXES_PROIBIDAS: Tuple[str, ...] = (
    "whatsapp", "receber atualizacoes", "receber informacoes", "aceito receber",
    "termo", "politica de privacidade", "autorizo",
)


# Sair de uma tela nunca criou nada em seguradora nenhuma. Esta lista existe
# para que a fronteira contextual (`tela_material`) não prenda o robô: sem ela,
# estando no 80%, nem `Voltar` passaria — e um robô que não consegue recuar de
# uma tela perigosa é pior que um que avança demais, porque perde o caminho de
# saída.
BOTOES_DE_VOLTA: Tuple[str, ...] = ("voltar", "anterior", "fechar", "sair", "corrigir")


def e_botao_material(texto: Any) -> bool:
    """O texto do botão indica efeito material?"""
    t = _norm(texto)
    if not t:
        return False
    return any(m in t for m in BOTOES_MATERIAIS)


def e_botao_de_volta(texto: Any) -> bool:
    """Recuar/fechar — inofensivo mesmo na tela que é fronteira de efeito.

    🔴 A lista explícita de materiais VENCE esta: `Cancelar atendimento` contém
    a ideia de sair e mesmo assim cancela um pedido de verdade na seguradora.
    Por isso quem chama pergunta `e_botao_material()` primeiro.
    """
    t = _norm(texto)
    if not t or e_botao_material(t):
        return False
    return any(v in t for v in BOTOES_DE_VOLTA)


def e_campo_critico(rotulo: Any) -> bool:
    t = _norm(rotulo)
    return bool(t) and any(c in t for c in CAMPOS_CRITICOS)


def e_checkbox_proibida(rotulo: Any) -> bool:
    t = _norm(rotulo)
    return bool(t) and any(c in t for c in CHECKBOXES_PROIBIDAS)


# --------------------------------------------------------------------------
# Leitura do `state` produzido por `capture_state()`
# --------------------------------------------------------------------------
def _lista(state: Dict[str, Any], chave: str) -> List[Dict[str, Any]]:
    v = (state or {}).get(chave)
    return [x for x in v if isinstance(x, dict)] if isinstance(v, list) else []


def _rotulos_de(item: Dict[str, Any]) -> List[str]:
    """Todos os jeitos de nomear o mesmo elemento."""
    return [_norm(item.get(k)) for k in
            ("label", "name", "id", "placeholder", "text", "aria-label", "ariaLabel")
            if item.get(k)]


def alvo_existe(target: Any, state: Dict[str, Any]) -> Tuple[bool, str]:
    """O alvo proposto existe MESMO na tela atual?

    Devolve `(existe, tipo)`. `tipo` diz onde foi encontrado, porque validar um
    `fill` contra um botão é tão errado quanto não validar.
    """
    alvo = _norm(target)
    if not alvo:
        return False, ""
    for chave, tipo in (("inputs", "input"), ("selects", "select"),
                        ("mdselects", "mdselect"), ("buttons", "button"),
                        ("radios", "radio"), ("checkboxes", "checkbox")):
        for it in _lista(state, chave):
            for r in _rotulos_de(it):
                if not r:
                    continue
                # casamento por continência nos dois sentidos, como o código
                # atual faz — mas agora o resultado é AUDITADO, não obedecido
                if alvo == r or alvo in r or r in alvo:
                    return True, tipo
    return False, ""


def opcoes_reais(target: Any, state: Dict[str, Any]) -> List[str]:
    """As opções que a tela realmente oferece para aquele campo."""
    alvo = _norm(target)
    for chave in ("selects", "mdselects", "radios"):
        for it in _lista(state, chave):
            if any(alvo == r or alvo in r or r in alvo for r in _rotulos_de(it) if r):
                ops = it.get("options") or it.get("opcoes") or []
                if isinstance(ops, list):
                    return [str(o.get("text") if isinstance(o, dict) else o)
                            for o in ops if o is not None]
    return []


def _valor_conhecido(valor: str, collected: Any) -> bool:
    """O valor proposto tem lastro no que já sabemos do segurado/corretora?"""
    alvo = _norm(valor)
    if not alvo:
        return False

    def _anda(v: Any, prof: int = 0) -> bool:
        if prof > 6:
            return False
        if isinstance(v, dict):
            return any(_anda(x, prof + 1) for x in v.values())
        if isinstance(v, (list, tuple)):
            return any(_anda(x, prof + 1) for x in v)
        s = _norm(v)
        if not s:
            return False
        return alvo == s or alvo in s or s in alvo

    return _anda(collected)


# --------------------------------------------------------------------------
# O validador — SPEC-073 E4
# --------------------------------------------------------------------------
@dataclass
class Veredito:
    ok: bool
    motivo: str = ""
    escalar: bool = False          # subir de camada em vez de simplesmente negar

    def __bool__(self) -> bool:    # `if veredito:` lê bem no call site
        return self.ok


def _ja_teve_sucesso(acao: Dict[str, Any], historico: Sequence[Any]) -> bool:
    """A mesma ação já deu certo antes, sem a tela mudar?

    Repetir uma ação bem-sucedida é o sintoma clássico do laço que gastava 22
    passos: o modelo não percebe que já preencheu e tenta de novo.
    """
    assinatura = f"{_norm(acao.get('action'))}|{_norm(acao.get('target'))}|{_norm(acao.get('value'))}"
    for h in list(historico or [])[-8:]:
        texto = _norm(h if isinstance(h, str) else str(h))
        if not texto:
            continue
        if assinatura.split("|")[0] in texto and _norm(acao.get("target")) in texto:
            if "ok" in texto or "filled" in texto or "clicked" in texto or "selected" in texto:
                return True
    return False


def validar_acao(acao: Dict[str, Any],
                 state: Dict[str, Any],
                 *,
                 collected: Optional[Dict[str, Any]] = None,
                 historico: Optional[Sequence[Any]] = None,
                 guard: Optional[G.PortalActionGuard] = None,
                 origem: str = L3_TEXTO,
                 tela_material: bool = False) -> Veredito:
    """O funil por onde TODA ação proposta por modelo passa antes de acontecer.

    Vale igual para `fill`, `select`, `click` e `check` — que é a correção
    central deste bloco. Devolve `Veredito`; quem executa só executa com `ok`.
    """
    collected = collected or {}
    historico = historico or []

    nome = _norm(acao.get("action"))
    target = acao.get("target") or ""
    valor = acao.get("value") or ""

    # (0) ação conhecida
    if nome not in ACOES_VALIDAS:
        return Veredito(False, f"acao desconhecida: {nome!r}")

    if nome in ("done", "ask_human"):
        return Veredito(True)

    # (1) o alvo existe na tela atual
    existe, tipo = alvo_existe(target, state)
    if not existe:
        return Veredito(False,
                        f"alvo {target!r} nao existe na tela atual",
                        escalar=True)

    # (5) não repetir passo que já deu certo sem mudança de estado
    if _ja_teve_sucesso(acao, historico):
        return Veredito(False,
                        f"acao {nome} em {target!r} ja teve sucesso e a tela nao mudou",
                        escalar=True)

    # (6) botão material exige autorização determinística
    if nome == "click":
        rotulo = _melhor_rotulo(target, state, "buttons") or str(target)
        # 🔴 Um botão é material por DUAS razões independentes, e a segunda é a
        # que a lista de rótulos jamais pegaria:
        #
        #   1. o rótulo diz o que ele faz ("Cancelar atendimento")
        #   2. a TELA é a fronteira do efeito
        #
        # No portal de vidros o clique que cria o pedido é `Avançar` — o mesmo
        # texto inofensivo dos passos 1 a 5. O que muda é estar no 80%, e quem
        # sabe disso é `is_confirm_screen()`, que é determinístico e já existia.
        # Sem este segundo caminho, uma blocklist de rótulos daria a falsa
        # sensação de cobertura e deixaria passar justamente o clique caro.
        explicito = e_botao_material(rotulo) or e_botao_material(target)
        por_contexto = tela_material and not e_botao_de_volta(rotulo)
        if explicito or por_contexto:
            if guard is None:
                return Veredito(False,
                                f"botao material {rotulo!r} sem guard: "
                                "recusado por construcao")
            # Pergunta 1 — pode haver efeito material agora?
            permitido, motivo = guard.avaliar(G.MATERIAL_SIDE_EFFECT, origem=origem)
            if not permitido:
                return Veredito(False, f"botao material {rotulo!r}: {motivo}")
            # Pergunta 2 — pode ser ESTE botão? A journey nomeou um só.
            certo, motivo2 = guard.acao_material_permitida(rotulo)
            if not certo:
                return Veredito(False, f"botao material {rotulo!r}: {motivo2}")
        return Veredito(True)

    # (2) a opção existe na lista real, quando aplicável
    if nome == "select":
        reais = opcoes_reais(target, state)
        if reais and not any(_norm(valor) == _norm(o) or _norm(valor) in _norm(o)
                             for o in reais):
            return Veredito(False,
                            f"opcao {valor!r} nao existe nas opcoes reais de {target!r}",
                            escalar=True)
        return Veredito(True)

    # (3) valor crítico não pode ser inventado
    if nome == "fill":
        rotulo = _melhor_rotulo(target, state, "inputs") or str(target)
        if e_campo_critico(rotulo):
            if not _valor_conhecido(valor, collected):
                return Veredito(False,
                                f"campo critico {rotulo!r} recebeu valor sem lastro "
                                "no que o segurado/corretora informou",
                                escalar=True)
        if not str(valor).strip():
            return Veredito(False, f"fill de {target!r} com valor vazio")
        return Veredito(True)

    if nome == "check":
        rotulo = _melhor_rotulo(target, state, "checkboxes") or str(target)
        if e_checkbox_proibida(rotulo) or e_checkbox_proibida(target):
            return Veredito(False,
                            f"checkbox {rotulo!r} nao pode ser marcada por decisao "
                            "de modelo (consentimento/canal do segurado)")
        if e_campo_critico(rotulo) and not _valor_conhecido(target, collected):
            return Veredito(False,
                            f"check em {rotulo!r} e resposta critica sem lastro "
                            "no relato do segurado",
                            escalar=True)
        return Veredito(True)

    return Veredito(True)


def _melhor_rotulo(target: Any, state: Dict[str, Any], chave: str) -> str:
    """O rótulo humano do elemento apontado — o que o guard e o log devem citar."""
    alvo = _norm(target)
    for it in _lista(state, chave):
        for r in _rotulos_de(it):
            if r and (alvo == r or alvo in r or r in alvo):
                return str(it.get("label") or it.get("text") or it.get("name") or target)
    return ""


# --------------------------------------------------------------------------
# Provider de percepção — trocável por config, nunca por arquitetura
# --------------------------------------------------------------------------
class PortalPerceptionProvider(Protocol):
    """Contrato único para texto e visão. Mesmo schema de ação nos dois."""

    async def decide(self,
                     *,
                     state: Dict[str, Any],
                     screenshot: Optional[bytes],
                     goal: str,
                     collected: Dict[str, Any],
                     history: List[Any]) -> Dict[str, Any]:
        ...


def visao_habilitada() -> bool:
    """`PORTAL_VISION_ENABLED` — nasce desligada (SPEC-073 L1)."""
    return str(os.getenv("PORTAL_VISION_ENABLED", "")).strip().lower() in ("1", "true", "yes", "on")


def provider_de_visao() -> str:
    """Qual provedor de visão usar. NÃO é decisão de arquitetura (E5).

    Fica em env para que o benchmark da SPEC-074 possa comparar candidatos com
    tarefa real — acerto da próxima ação, zero falso positivo material, respeito
    às opções reais, `ask_human` correto, latência, custo — em vez de alguém
    escolher por entusiasmo.
    """
    return str(os.getenv("PORTAL_VISION_PROVIDER", "openai")).strip().lower()


@dataclass
class EscadaDePercepcao:
    """Registra por qual degrau cada decisão foi resolvida.

    Serve à pergunta operacional que hoje não tem resposta: *"qual camada
    resolveu?"*. E serve ao alarme da SPEC-075 §40.2 — se a visão começar a
    responder por 90% dos passos de uma journey madura, o que quebrou foi o
    adapter de DOM, não a inteligência que melhorou.
    """

    usados: List[str] = field(default_factory=list)
    rejeicoes: List[Dict[str, Any]] = field(default_factory=list)

    def registrar(self, camada: str) -> None:
        if camada and (not self.usados or self.usados[-1] != camada):
            self.usados.append(camada)

    def rejeitar(self, acao: Dict[str, Any], veredito: Veredito, *, camada: str) -> None:
        self.rejeicoes.append({
            "layer": camada,
            "action": str(acao.get("action") or "")[:24],
            "target": str(acao.get("target") or "")[:80],
            "reject_reason": veredito.motivo[:200],
            "escalou": bool(veredito.escalar),
        })

    def proximo_degrau(self, atual: str) -> str:
        """O degrau seguinte da escada. Do topo, só sobra o humano."""
        try:
            i = ESCADA.index(atual)
        except ValueError:
            return L5_HUMANO
        return ESCADA[min(i + 1, len(ESCADA) - 1)]

    def resumo(self) -> Dict[str, Any]:
        return {
            "layers_used": list(self.usados),
            "layer_final": self.usados[-1] if self.usados else "",
            "fallback_count": max(0, len(self.usados) - 1),
            "rejected_actions": self.rejeicoes[:12],
        }


async def decidir_com_visao(provider: Any,
                            *,
                            imagem: Optional[bytes],
                            state: Dict[str, Any],
                            goal: str,
                            collected: Dict[str, Any],
                            history: List[Any]) -> Dict[str, Any]:
    """Chama o provedor multimodal e NUNCA deixa a falha dele derrubar o job.

    🔴 E7 — o gancho futuro: a função recebe `imagem: bytes`, não uma `page`. O
    mesmo interpretador poderá, no futuro, analisar uma foto que o segurado
    mandou no WhatsApp, sem duplicar motor multimodal. **Isso não liga visão ao
    WhatsApp agora** — só evita que a decisão de hoje impeça a de amanhã.
    """
    if provider is None or imagem is None:
        return {"action": "ask_human", "reason": "visao indisponivel"}
    try:
        resposta = await provider.decide(state=state, screenshot=imagem, goal=goal,
                                         collected=collected, history=history)
        if not isinstance(resposta, dict):
            return {"action": "ask_human", "reason": "resposta de visao ilegivel"}
        return resposta
    except Exception as e:  # noqa: BLE001
        # Provider fora do ar vira HITL honesto, não stack trace no meio de um
        # acionamento. Gate E exige exatamente isto.
        logger.warning("[PORTAL] provider de visao indisponivel: %s", type(e).__name__)
        return {"action": "ask_human",
                "reason": f"visao indisponivel ({type(e).__name__})"}
