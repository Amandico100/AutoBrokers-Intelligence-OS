# -*- coding: utf-8 -*-
"""SPEC-123 F1a — O DESTRAVADOR: quando o roteiro fixo trava, o agente pensa e decide UMA tela.

O agente continua DETERMINÍSTICO até travar (tela sem passo, dado que falta, `sem_chute`,
`NAO_SEI`, recusa do conferente, tela desconhecida). Travou → `destravar(...)`:

    CONTEXTO COMPLETO  o prompt do PRODUTO (`build_human_phase_messages`, importado, nunca
                       copiado) + o caso em palavras + o que a seguradora vai pedir + a conversa
                       com o segurado + as telas anteriores + um RECORTE do mapa da URA + as
                       rotas irmãs + a memória da corretora
    → UM modelo (papel `destravador`, pela fábrica do produto — nunca modelo por env)
    → saída ESTRUTURADA `{"classe","acao","valor","nota","motivo"}` (parser ESTRITO: qualquer
      desvio → PESSOA)
    → A POLÍTICA EM CÓDIGO (`decidir_destravamento`) — D1–D3 do Founder, 30/09/2026:
        CONDUZIR              livre, se o valor é uma opção de NAVEGAÇÃO da tela
                              (`rotulo_e_de_navegacao`) ou confirma um eco do caso; senão → DEDUZIR
        RESPONDER_COM_DADO    livre, se o valor É um dado do caso (e o conferente aprova); senão → DEDUZIR
        DEDUZIR               só com nota ≥ limiar (≥ 70) E a 2ª opinião de OUTRO PROVEDOR (o que
                              decidiu DE FATO) escolhendo a MESMA opção; senão → pergunta ao segurado
                              (se a seguradora espera) ou pessoa
        PERGUNTAR_AO_SEGURADO a pergunta em 2ª pessoa + as opções de CONTEÚDO da tela
        NUNCA_SOZINHO         só o IRREVERSÍVEL (`NUNCA_SOZINHO`): custo → pergunta ao segurado com o
                              valor da tela; o resto → pessoa
    → UMA linha no diário (`diario_de_decisoes.registrar_decisao`) → a decisão volta ao chamador.

⛔ ESTE MÓDULO NUNCA ENVIA NADA. Não recebe sender, não toca a sessão viva, não grava a sessão.
   Quem age é o roteador (F1b) — e só no modo `on`. Em `sombra` a decisão vai ao diário com
   `acao='nao_agiu'` e nada muda no envio.
⛔ Nunca levanta: qualquer falha vira PESSOA (falha fechada).
⛔ Todo import do `app` é TARDE (dentro da função): os testes montam o fio coerente em
   `sys.modules` (P-121-28) e este módulo tem de enxergar o MESMO objeto que o roteador.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ═════════════════════════════════════════════════════════════════════════════
# O CONTRATO (CONTRATO-123 — F1a implementa · F1b chama · F4 grava)
# ═════════════════════════════════════════════════════════════════════════════
CLASSES = ("conduzir", "responder_com_dado", "deduzir", "perguntar_ao_segurado", "nunca_sozinho")

#: constante_justificada: D2 do Founder (30/09/2026) — "se tiver acima de 70% de certeza, decide e
#: continua". A calibração (F2) pode SUBIR por seguradora/ramo (`cerebro_modos.limiar`); baixar
#: abaixo de 70 exige ordem dele. ⚠️ É a MUTAÇÃO do guarda: baixar este número deixa vermelho
#: `test_spec123_destravador_politica.py::test_nota_69_nao_age_nem_com_limiar_pedido_abaixo`.
LIMIAR_MINIMO = 70
LIMIAR_MAXIMO = 100

#: As ações FINAIS (depois da política). As mesmas palavras de `acao_do_cerebro.ACOES`, menos
#: RECUSA — recusa de cobertura é gatilho do MOTOR (`recusa_de_cobertura:*`), nunca destravável.
ACOES = ("RESPONDER", "PERGUNTAR_AO_SEGURADO", "PESSOA", "SILENCIO")

#: O papel de modelo que decide e o da 2ª opinião (migration 20260930_03, `llm_papeis`).
PAPEL = "destravador"
PAPEL_SEGUNDA = "destravador_segunda"
#: O `service_type` do ledger (`token_usage_logs`) — o custo do destravador medido à parte.
SERVICE_TYPE = "destravador"
SERVICE_TYPE_SEGUNDA = "destravador_segunda"

#: Quanto uma chamada ao modelo pode demorar. 💭 A URA da Allianz encerra com mediana 254 s
#: (📊 D6 da SPEC-123); 60 s por chamada deixam folga para a 2ª opinião e a resposta.
TETO_DA_CHAMADA_S = 60.0
#: Quanto cada fonte de contexto pode demorar (banco). Contexto é enfeite: não pode segurar a URA.
TETO_DO_CONTEXTO_S = 5.0

#: Os pares (classe → ações) que fazem sentido. Um par fora disto é saída INVÁLIDA (→ PESSOA):
#: "deduzir + PESSOA" ou "conduzir + PERGUNTAR" são o modelo dizendo duas coisas ao mesmo tempo.
_PARES_VALIDOS = {
    "conduzir": ("RESPONDER", "SILENCIO"),
    "responder_com_dado": ("RESPONDER",),
    "deduzir": ("RESPONDER",),
    "perguntar_ao_segurado": ("PERGUNTAR_AO_SEGURADO",),
    "nunca_sozinho": ("PESSOA", "PERGUNTAR_AO_SEGURADO"),
}
_CHAVES = frozenset({"classe", "acao", "valor", "nota", "motivo"})
_OBRIGATORIAS = frozenset({"classe", "acao", "nota"})

# ═════════════════════════════════════════════════════════════════════════════
# O NUNCA SOZINHO — curto de propósito: só o IRREVERSÍVEL (D1 do Founder)
# ═════════════════════════════════════════════════════════════════════════════
#
# A lista da SPEC-122 (`acao_do_cerebro.PROIBICOES`) proibia ESCOLHER O SERVIÇO e toda tela que
# "abre/agenda/cancela" — e com isso nada destravava. Aqui ela é ENXUGADA ao que não tem volta:
#   · escolher o serviço deixa de ser proibido → vira DEDUZIR (nota + 2ª opinião);
#   · agendar data/período → PERGUNTA ao segurado (a agenda é DELE, e dá para refazer);
#   · o "abre/agenda/cancela" fica só para CANCELAR e ABRIR NOVO atendimento.
# ⚠️ Tirar uma chave daqui é a MUTAÇÃO do G2: o teste do item correspondente fica vermelho.
NUNCA_SOZINHO = (
    "aceite_de_custo",           # dinheiro do segurado — ELE decide (pergunta com o valor da tela)
    "abrir_sinistro",            # sinistro é outro processo, com consequência na apólice
    "cancelar_pedido",           # cancelar desmarca o prestador — a tecla mais cara do corredor
    "novo_atendimento",          # um segundo atendimento perde o protocolo do primeiro
    "condominio_ou_empresarial", # D10: condomínio e empresarial ficam com a atendente
    "confirmacao_final",         # confirmar/abrir de fato, fora do modo que o autoriza
    "inventar_dado",             # número/CPF/dado que não está no caso
    "afirma_cobertura",          # só a seguradora afirma cobertura
)

PORQUE = {
    "aceite_de_custo": "a seguradora falou de custo ou pagamento — quem decide é o segurado",
    "abrir_sinistro": "a resposta abriria um sinistro — isso é com uma pessoa",
    "cancelar_pedido": "a resposta cancelaria o pedido — isso é com uma pessoa",
    "novo_atendimento": "a resposta abriria um NOVO atendimento e perderia o que está em curso",
    "condominio_ou_empresarial": "condomínio e empresarial ficam com a atendente",
    "confirmacao_final": "a tela confirma a abertura do serviço e o modo de ensaio não autoriza",
    "inventar_dado": "a resposta traria um número que não está no caso",
    "afirma_cobertura": "a resposta falava de cobertura — só a seguradora afirma cobertura",
}

#: constante_justificada: o gatilho do MOTOR que NUNCA vem ao destravador (CONTRATO-123, BLOCO 0):
#: sinistro, recusa de cobertura, consultora humana da seguradora, carro reserva (fora do horário /
#: documento), condomínio/empresa, corredor inexistente, confirmação barrada, formulário nativo e
#: encaminhamento. O roteador (F1b) não chama; se chamar, a resposta é PESSOA sem gastar modelo.
GATILHOS_NUNCA_DESTRAVAVEIS = (
    "handoff_trigger", "recusa_de_cobertura", "consultora_da_seguradora", "fora_do_horario",
    "exige_documento", "apolice_de_condominio_ou_empresa", "playbook_not_found",
    "confirmacao_bloqueada", "formulario_", "encaminhamento_exige_pessoa",
)

#: constante_justificada: a opção/valor que ABRE SINISTRO. 📊 As redações reais do acervo
#: (`tests/corpus/telas_reais`): "Sinistro / Sinistro para roubo, furto ou acidente" (azul-auto
#: 6c5280df), "Sinistro de Veículos" (porto-auto), "Aviso de ocorrência" (mapfre-auto).
_RX_SINISTRO = re.compile(r"\bsinistro|\baviso de ocorrencia\b|\bcomunicar (?:o )?acidente\b")
#: constante_justificada: a TELA que pergunta se abre o sinistro (a resposta afirmativa abriria).
_RX_TELA_ABRE_SINISTRO = re.compile(
    r"abr(?:ir|a|e|imos)\s+(?:o\s+|um\s+)?(?:aviso\s+de\s+)?sinistro|registrar\s+(?:o\s+)?sinistro")
#: constante_justificada: CANCELAR — o mesmo radical de `_RX_ABRE_AGENDA_CANCELA` do produto
#: (`cancelar` / `cancelad`), agora só sobre a OPÇÃO escolhida e a tela que pergunta.
_RX_CANCELA = re.compile(r"\bcancel")
#: constante_justificada: ESCOLHER data/período (sobre texto normalizado, sem acento). 📊 porto-auto
#: 910b6295: "selecione a data para quando você quer o serviço". ⚠️ NÃO é o radical `agendad` do
#: produto: 📊 allianz-residencial "O serviço … deverá ser AGENDADO. 1 - Continuar 2 - Voltar" só
#: CONDUZ — perguntar ao segurado ali seria travar por excesso de zelo (o que o Founder proibiu).
_RX_AGENDA = re.compile(
    r"selecione a data|escolha (?:a |uma )?data|datas disponiveis|horarios disponiveis|"
    r"(?:qual|informe|escolha|selecione) (?:a |o )?(?:melhor )?(?:data|dia|horario|periodo)\b|"
    r"\bmanha\b[\s\S]{0,80}\btarde\b")
#: constante_justificada: o "sim" que CONCORDA com a pergunta da tela (a resposta que executa o que
#: a tela propõe). Largo de propósito: o falso positivo custa uma pessoa; o negativo, um cancelamento.
_RX_AFIRMATIVO = re.compile(r"^(?:\d\s*[-.)]?\s*)?(?:sim|confirmo|confirmar|pode|isso|ok|quero|desejo|aceito)\b")


class LimiarRecusado(ValueError):
    """O limiar pedido está fora de 70..100 (D2: nunca abaixo de 70 sem ordem do Founder)."""


def validar_limiar(limiar: Any) -> int:
    """70..100 → ele mesmo (int). Fora disso, ou não-inteiro → LimiarRecusado."""
    if isinstance(limiar, bool):
        raise LimiarRecusado(f"limiar inválido {limiar!r}")
    try:
        n = int(limiar)
    except (TypeError, ValueError):
        raise LimiarRecusado(f"limiar inválido {limiar!r}") from None
    if isinstance(limiar, float) and limiar != n:
        raise LimiarRecusado(f"limiar inválido {limiar!r}")
    if n < LIMIAR_MINIMO or n > LIMIAR_MAXIMO:
        raise LimiarRecusado(
            f"limiar {n} fora de {LIMIAR_MINIMO}..{LIMIAR_MAXIMO} (D2 do Founder: nunca abaixo de "
            f"{LIMIAR_MINIMO} sem ordem dele)")
    return n


def _limiar_efetivo(limiar: Any) -> int:
    """O limiar que VALE numa chamada: o pedido, nunca abaixo do mínimo (o código não confia)."""
    try:
        n = int(limiar) if not isinstance(limiar, bool) else LIMIAR_MINIMO
    except (TypeError, ValueError):
        n = LIMIAR_MINIMO
    return min(LIMIAR_MAXIMO, max(LIMIAR_MINIMO, n))


# ═════════════════════════════════════════════════════════════════════════════
# A DECISÃO
# ═════════════════════════════════════════════════════════════════════════════
@dataclass
class Destravamento:
    classe: str                 # uma de CLASSES
    acao: str                   # "RESPONDER" | "PERGUNTAR_AO_SEGURADO" | "PESSOA" | "SILENCIO" (FINAL)
    valor: str = ""             # o que vai à URA (RESPONDER) ou a pergunta ao segurado (PERGUNTAR)
    opcoes: Optional[list] = None   # PERGUNTAR: as opções de CONTEÚDO da tela ([[tecla, rótulo], …])
    nota: Optional[int] = None  # 0–100 do modelo
    limiar: int = LIMIAR_MINIMO
    motivo: str = ""            # curto, do modelo
    explicacao: str = ""        # a frase para GENTE (D7)
    segunda_opiniao: Optional[dict] = None   # {"modelo","provedor","valor","nota","concordou"}
    modelo: str = ""
    proibicao: str = ""         # por que a política rebaixou
    modo: str = "on"            # "on" | "sombra"
    diario_id: Optional[str] = None
    custo_usd: float = 0.0
    # — além do contrato (campos com padrão: nenhum chamador quebra) —
    acao_do_modelo: str = ""    # o que o modelo PROPÔS, antes da política
    valor_do_modelo: str = ""
    formato_ok: bool = True
    provedor: str = ""          # o provedor que DECIDIU de fato (a reserva pode ter decidido)
    modelo_chamado: bool = False   # False = nenhuma resposta do modelo (falha/disjuntor) — nada medido
    gatilho: str = ""

    def para_dict(self) -> dict:
        return asdict(self)


@dataclass
class Proposta:
    """A saída do modelo, lida pelo parser estrito."""
    classe: str = "nunca_sozinho"
    acao: str = "PESSOA"
    valor: str = ""
    nota: Optional[int] = None
    motivo: str = ""
    formato_ok: bool = True
    erro: str = ""


def ler_destravamento(texto: Any) -> Proposta:
    """O JSON do modelo → a proposta. ESTRITO, no molde de `acao_do_cerebro.ler_acao`.

    Tolerado só o que não muda o sentido: espaço em volta e UMA cerca ```json … ```. Um objeto,
    chaves conhecidas (classe, acao e nota obrigatórias), classe e ação das listas, o PAR coerente,
    nota inteira 0–100. Qualquer outra coisa → ``formato_ok=False`` e PESSOA (falha fechada).
    """
    bruto = str(texto if texto is not None else "").strip()
    m = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", bruto, flags=re.S | re.I)
    if m:
        bruto = m.group(1).strip()

    def _ruim(erro: str) -> Proposta:
        return Proposta(formato_ok=False, erro=erro)

    try:
        obj = json.loads(bruto)
    except (ValueError, TypeError):
        return _ruim("nao_e_json")
    if not isinstance(obj, dict):
        return _ruim("nao_e_objeto")
    if set(obj) - _CHAVES or not _OBRIGATORIAS <= set(obj):
        return _ruim("chaves_invalidas")
    classe = str(obj.get("classe") or "").strip().lower()
    acao = str(obj.get("acao") or "").strip().upper()
    if classe not in CLASSES:
        return _ruim("classe_desconhecida")
    if acao not in ACOES:
        return _ruim("acao_desconhecida")
    if acao not in _PARES_VALIDOS[classe]:
        return _ruim("classe_e_acao_incoerentes")
    nota = obj.get("nota")
    if isinstance(nota, bool) or not isinstance(nota, (int, float)):
        return _ruim("nota_invalida")
    if isinstance(nota, float) and nota != int(nota):
        return _ruim("nota_invalida")
    nota = int(nota)
    if not 0 <= nota <= 100:
        return _ruim("nota_fora_de_0_100")
    valor, motivo = obj.get("valor", ""), obj.get("motivo", "")
    if not isinstance(valor, (str, int)) or isinstance(valor, bool) \
            or not isinstance(motivo, (str, type(None))):
        return _ruim("tipo_invalido")
    valor = str(valor).strip()
    if acao in ("RESPONDER", "PERGUNTAR_AO_SEGURADO") and not valor:
        return _ruim("valor_vazio")
    return Proposta(classe, acao, valor, nota, str(motivo or "").strip()[:200])


# ═════════════════════════════════════════════════════════════════════════════
# O MODO (cerebro_modos) — um leitor só, o de `acao_do_cerebro`
# ═════════════════════════════════════════════════════════════════════════════
async def modo_do_destravador(company_id: str, insurer_key: str, ramo: str) -> Tuple[str, int]:
    """('off'|'sombra'|'on', limiar) de `cerebro_modos`, precedência (seg,ramo) > (seg,'todos') > off.

    Filtro por `company_id` no CÓDIGO (CLAUDE.md §7), cache curto (60 s por corretora). Qualquer
    falha → ('off', 70). ⛔ O leitor é o de `acao_do_cerebro` (um só — CLAUDE.md §5)."""
    try:
        from app.services import acao_do_cerebro as AC

        modo, limiar = await AC.modo_e_limiar(company_id, insurer_key, ramo)
        return modo, _limiar_efetivo(limiar)
    except Exception as e:  # noqa: BLE001 — sem saber, desligado
        logger.warning("[DESTRAVADOR] modo ilegível (%s) — off", type(e).__name__)
        return "off", LIMIAR_MINIMO


# ═════════════════════════════════════════════════════════════════════════════
# O CONTEXTO — o que o sistema sabe, para um modelo inteligente
# ═════════════════════════════════════════════════════════════════════════════
def _palavras(texto: Any) -> set:
    from app.services.insurer_dispatch_service import _norm_text

    return {p for p in re.findall(r"[a-z]{4,}", _norm_text(str(texto or "")))}


def _parecido(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / float(len(a | b))


def _gatilho_legivel(gatilho: str) -> str:
    g = str(gatilho or "").strip()
    if g in ("", "cerebro"):
        return ("o roteiro automático não conhece esta tela (ou o conferente recusou a resposta "
                "anterior) e a conversa não pode parar")
    if g == "sentinela":
        return "a conversa com a seguradora parou — ninguém respondeu a última tela"
    try:
        from app.services.insurer_dispatch_service import motivo_em_portugues

        return motivo_em_portugues(g)
    except Exception:  # noqa: BLE001
        return "o roteiro automático travou nesta tela"


def _caso_em_palavras(sessao: Dict[str, Any]) -> str:
    from app.services.insurer_dispatch_service import _rotulo

    slots = sessao.get("slots") or {}
    padrao = set(sessao.get("slots_padrao") or ())
    linhas = []
    for k, v in slots.items():
        if v in (None, "") or str(k).endswith("_opcao"):
            continue
        marca = "  (preenchido pelo sistema — o segurado NÃO confirmou)" if k in padrao else ""
        linhas.append(f"- {_rotulo(str(k))}: {str(v)[:200]}{marca}")
    for k, v in (sessao.get("captured") or {}).items():
        if v not in (None, ""):
            linhas.append(f"- capturado da seguradora — {k}: {str(v)[:120]}")
    sub = str(sessao.get("subservice") or "").strip()
    cab = f"Serviço pedido: {sub.replace('_', ' ') or 'não informado'}.\n"
    return cab + ("\n".join(linhas) if linhas else "(o caso não tem dados além do serviço)")


def _o_que_vai_pedir(playbook: Dict[str, Any], sessao: Dict[str, Any]) -> str:
    from app.services.insurer_dispatch_service import _rotulo

    slots = sessao.get("slots") or {}
    pede = [str(x) for x in (playbook.get("required_slots") or [])]
    sub = ((playbook.get("subservices") or {}).get(str(sessao.get("subservice") or "")) or {})
    pede += [str(x) for x in (sub.get("required_slots") or []) if str(x) not in pede]
    if not pede:
        return ""
    return "\n".join(f"- {_rotulo(x)} {'✔ o caso tem' if slots.get(x) not in (None, '') else '✘ falta'}"
                     for x in pede[:20])


def _telas_antes(sessao: Dict[str, Any]) -> str:
    """As falas ANTERIORES às 6 que o prompt do produto já mostra (até 20 no total)."""
    linhas = []
    for e in (sessao.get("transcript") or [])[-20:-6]:
        if isinstance(e, dict) and str(e.get("text") or "").strip():
            quem = "você" if str(e.get("direction")) == "out" else "seguradora"
            linhas.append(f"[{quem}] {' '.join(str(e['text']).split())[:300]}")
    return "\n".join(linhas)


async def _conversa_do_segurado(company_id: str, sessao: Dict[str, Any]) -> List[str]:
    """As últimas ~15 mensagens da conversa do SEGURADO com a corretora (P-122-07).

    🔴 ⛔ NÃO é `mirror_conversation_id` (essa é a conversa com a SEGURADORA). A do segurado se
    acha pelo telefone dele, em TODAS as formas (`_variantes_do_telefone`), com o `company_id` no
    filtro E conferido no código (CLAUDE.md §7). Os helpers são os do produto
    (`o_fim_do_atendimento`, os mesmos de `dispatch_router._texto_da_conversa_do_segurado`).
    Best-effort: qualquer falha → a lista que a sessão já trouxer (`conversa_segurado`) ou nada.
    ⛔ Nada disto vai a log.
    """
    ja = [str(x)[:300] for x in (sessao.get("conversa_segurado") or []) if str(x or "").strip()]
    fone = re.sub(r"\D", "", str(sessao.get("client_phone") or ""))
    empresa = str(company_id or "").strip()
    if not fone or not empresa:
        return ja[-15:]
    try:
        from app.core.database import get_supabase_client
        from app.services.o_fim_do_atendimento import (
            _cliente, _executar, _variantes_do_telefone, janela_de_mensagens,
        )

        db = get_supabase_client()
        if db is None:
            return ja[-15:]
        formas = sorted(_variantes_do_telefone(fone) or {fone})
        achado = await _executar(_cliente(db).table("conversations")
                                 .select("id, company_id")
                                 .eq("company_id", empresa)      # 🔴 CLAUDE.md §7
                                 .eq("channel", "whatsapp")
                                 .in_("user_phone", formas)
                                 .limit(5))
        linhas = [x for x in (getattr(achado, "data", None) or [])
                  if str(x.get("company_id") or "") == empresa]   # cinto: nunca outra corretora
        if not linhas:
            return ja[-15:]
        mensagens, erro = await janela_de_mensagens(db, str(linhas[0].get("id") or ""), teto=15)
        if erro:
            return ja[-15:]
        fora = []
        for m in reversed(mensagens or []):
            texto = " ".join(str(m.get("content") or "").split())
            if not texto:
                continue
            papel = str(m.get("role") or "")
            quem = "segurado" if papel in ("user", "human", "cliente") else "corretora"
            fora.append(f"[{quem}] {texto[:300]}")
        return (fora or ja)[-15:]
    except Exception as e:  # noqa: BLE001
        logger.warning("[DESTRAVADOR] conversa do segurado ilegível (%s)", type(e).__name__)
        return ja[-15:]


async def _recorte_do_mapa(playbook: Dict[str, Any], tela: str) -> str:
    """As 2 telas do MAPA da URA mais parecidas com a de agora, com o que cada opção faz.

    🔴 O mapa INTEIRO não entra (decisão do Founder, 05/08/2026, em `build_human_phase_messages`):
    📊 5.220 caracteres, 19 de 30 telas sem opção, ramo misturado. O que ele pediu para rever
    "quando o mapa souber recortar por caso" é isto: só as telas parecidas com ESTA, ≤ 900 chars.
    """
    try:
        from app.services.ura_map_service import get_active_map

        row = await get_active_map(str(playbook.get("insurer_key") or ""),
                                   str(playbook.get("line_kind") or "auto"))
    except Exception:  # noqa: BLE001 — mapa é opcional
        return ""
    nos = ((row or {}).get("map") or {}).get("nodes") or {}
    if not isinstance(nos, dict) or not nos:
        return ""
    alvo = _palavras(tela)
    notas = []
    for n in nos.values():
        if not isinstance(n, dict) or len(n.get("options") or []) < 2:
            continue
        s = _parecido(alvo, _palavras(n.get("text")))
        if s >= 0.3:
            notas.append((s, n))
    notas.sort(key=lambda x: -x[0])
    blocos = []
    for _s, n in notas[:2]:
        ops = []
        for o in (n.get("options") or [])[:8]:
            rot = str(o.get("label") or "").strip()
            prox = nos.get(str(o.get("leads_to") or "")) or {}
            depois = " ".join(str(prox.get("text") or "").split())[:70]
            ops.append(f"“{rot}”" + (f" → leva a “{depois}”" if depois else ""))
        blocos.append(f"- tela já vista: “{' '.join(str(n.get('text') or '').split())[:160]}”\n  "
                      + "; ".join(ops))
    return "\n".join(blocos)[:900]


def _ancora_legivel(ancora: str) -> str:
    t = re.sub(r"\(\?[a-z]+\)|\\[bBdswDSW]|[\\^$.*+?()\[\]{}|]", " ", str(ancora or ""))
    return " ".join(t.split())


def _rotas_irmas(playbook: Dict[str, Any], sessao: Dict[str, Any], tela: str,
                 limite: int = 6) -> str:
    """Passos CONHECIDOS parecidos com esta tela: da mesma seguradora (outros corredores) e do
    mesmo serviço em outras seguradoras — "tela sobre … → responde …". Os mais parecidos primeiro.

    O corredor ATUAL fica de fora: ele já está inteiro no "CONHECIMENTO DO FLUXO" do produto."""
    from app.services import corridor_playbooks as CP

    atual = str(sessao.get("playbook_ref") or "")
    seg = str(playbook.get("insurer_key") or "")
    try:
        sub = CP.canonical_subservice(str(sessao.get("subservice") or ""))
    except Exception:  # noqa: BLE001
        sub = str(sessao.get("subservice") or "")
    slots = {k: str(v) for k, v in (sessao.get("slots") or {}).items() if v not in (None, "")}
    alvo = _palavras(tela)
    achados = []
    for ref in list(getattr(CP, "_PLAYBOOKS", {}) or {}):
        if ref == atual:
            continue
        pb = CP.get_playbook(ref) or {}
        mesma = str(pb.get("insurer_key") or "") == seg
        for st in pb.get("ura_steps") or []:
            if st.get("noop") or not str(st.get("reply") or "").strip():
                continue
            so = [str(x) for x in (st.get("only_subservices") or [])]
            if not mesma and (not sub or sub not in so):
                continue
            ancora = _ancora_legivel(st.get("anchor"))
            s = _parecido(alvo, _palavras(ancora + " " + str(st.get("notes") or "")))
            if s < 0.08:
                continue
            try:
                resp = str(st.get("reply") or "").format(**slots)
            except Exception:  # noqa: BLE001 — slot que falta fica como está
                resp = str(st.get("reply") or "")
            nota = " ".join(str(st.get("notes") or "").split())[:120]
            linha = (f"- {str(pb.get('insurer_key') or '')} ({ref.split('@')[0]}) · tela sobre "
                     f"“{ancora[:90]}” → responde “{resp[:60]}”" + (f" — {nota}" if nota else "")
                     + (" (o dado vem do segurado: pergunta a ele)" if st.get("sem_chute") else ""))
            achados.append((s, linha))
    achados.sort(key=lambda x: -x[0])
    return "\n".join(l for _s, l in achados[:limite])


async def _memoria_da_corretora(company_id: str) -> List[str]:
    """Os fatos ATIVOS que a corretora ensinou (`company_memories`, pela `MemoryFabric` do produto,
    que filtra por `company_id`). Best-effort; 📊 30/09/2026 a tabela tinha 0 linhas."""
    try:
        from app.core.database import get_supabase_client
        from app.services.memory_fabric import MemoryFabric

        db = get_supabase_client()
        if db is None:
            return []
        fatos = await asyncio.to_thread(MemoryFabric(db).fatos_da_corretora, str(company_id), limite=8)
        return [f"- {' '.join(str(f.get('statement') or '').split())[:200]}"
                for f in (fatos or []) if str(f.get("status") or "") == "active"
                and str(f.get("statement") or "").strip()]
    except Exception as e:  # noqa: BLE001
        logger.warning("[DESTRAVADOR] memória ilegível (%s)", type(e).__name__)
        return []


async def _com_teto(coro, padrao):
    try:
        return await asyncio.wait_for(coro, timeout=TETO_DO_CONTEXTO_S)
    except Exception:  # noqa: BLE001 — contexto é enfeite; nunca segura a URA
        return padrao


INSTRUCAO_DO_DESTRAVADOR = (
    "\n\n══════ VOCÊ FOI CHAMADO PORQUE O ROTEIRO AUTOMÁTICO TRAVOU ══════\n"
    "O objetivo: levar este acionamento até o PROTOCOLO da seguradora sem chamar uma pessoa da "
    "corretora — com a resposta CERTA. O que está em jogo: cada pessoa chamada é um segurado "
    "esperando mais, e a URA encerra a conversa se ninguém responde; cada resposta errada pode "
    "virar um chamado recusado no local, depois de o segurado esperar horas.\n"
    "Leia TUDO abaixo (o caso, a conversa com o segurado, as telas anteriores, as rotas parecidas "
    "de outras seguradoras) e decida esta tela como um atendente experiente decidiria. Suas regras "
    "acima sobre NAO_SEI e SEM_RESPOSTA são SUBSTITUÍDAS por esta instrução.\n\n"
    "Classifique a sua decisão em UMA de cinco classes:\n"
    "- conduzir: a tela só move o fluxo (Continuar, \"quer seguir?\", voltar ao menu quando a "
    "conversa se perdeu). valor = a opção exata da tela.\n"
    "- responder_com_dado: a tela pede um dado que ESTÁ no caso (placa, endereço, CPF, quem está "
    "no local). valor = o dado, como está no caso.\n"
    "- deduzir: a tela pede para escolher entre alternativas e o caso/relato indica qual. valor = o "
    "número ou o rótulo da opção.\n"
    "- perguntar_ao_segurado: só o segurado sabe (a situação no local, o detalhe do problema, uma "
    "escolha que o caso não diz). valor = a pergunta a ELE, curta, em segunda pessoa (\"você\"), "
    "sem prometer cobertura.\n"
    "- nunca_sozinho: aceitar custo, franquia ou pagamento; abrir sinistro; cancelar um pedido; "
    "abrir um NOVO atendimento; informar dado que não está no caso; afirmar cobertura. Isso não é "
    "seu: acao PESSOA — ou PERGUNTAR_AO_SEGURADO quando é ele quem decide (um custo, uma data).\n\n"
    "nota: de 0 a 100, a chance REAL de a sua resposta estar certa. Seja calibrado — 90 quer dizer "
    "que você erraria 1 em cada 10 vezes. A nota decide se você age sozinho; inflar a nota é o erro "
    "mais caro. Tudo o que você propõe é conferido por código antes de sair.\n\n"
    "FORMATO DA SUA RESPOSTA (obrigatório): UM objeto JSON numa linha, sem texto antes ou depois:\n"
    '{"classe": "<conduzir|responder_com_dado|deduzir|perguntar_ao_segurado|nunca_sozinho>", '
    '"acao": "<RESPONDER|PERGUNTAR_AO_SEGURADO|PESSOA|SILENCIO>", "valor": "<texto>", '
    '"nota": <0-100>, "motivo": "<até 15 palavras>"}\n'
    "- RESPONDER: o valor vai à seguradora exatamente como escrito.\n"
    "- SILENCIO (classe conduzir): a tela só avisa e não pede nada; valor vazio.\n"
    "- PESSOA (classe nunca_sozinho): valor vazio."
)


def compor_mensagens(sessao: Dict[str, Any], tela: str, *, gatilho: str = "cerebro",
                     conversa: Optional[List[str]] = None, mapa: str = "",
                     memoria: Optional[List[str]] = None) -> Dict[str, str]:
    """O prompt do destravador: o do PRODUTO + o que o destravador ACRESCENTA. Puro (sem banco).

    A bancada (F2) importa ESTA função — o prompt que ela mede é, byte a byte, o que o produto roda.
    """
    from app.services.insurer_dispatch_service import build_human_phase_messages, get_playbook

    msgs = dict(build_human_phase_messages(sessao, tela))
    playbook = get_playbook(str(sessao.get("playbook_ref") or "")) or {}
    msgs["system"] = msgs["system"] + INSTRUCAO_DO_DESTRAVADOR
    bloco = f"\n\n🔴 POR QUE VOCÊ FOI CHAMADO: {_gatilho_legivel(gatilho)}."
    bloco += "\n\nO CASO, EM PALAVRAS:\n" + _caso_em_palavras(sessao)
    pede = _o_que_vai_pedir(playbook, sessao)
    if pede:
        bloco += "\n\nO QUE A SEGURADORA COSTUMA PEDIR NESTE SERVIÇO:\n" + pede
    conversa = list(conversa or [])
    bloco += ("\n\nA CONVERSA COM O SEGURADO (as últimas mensagens, a mais antiga primeiro):\n"
              + "\n".join(conversa) if conversa
              else "\n\nA CONVERSA COM O SEGURADO: (não disponível neste caso)")
    antes = _telas_antes(sessao)
    if antes:
        bloco += "\n\nANTES DISSO NA CONVERSA COM A SEGURADORA (as falas mais antigas):\n" + antes
    if mapa:
        bloco += ("\n\nTELAS PARECIDAS QUE JÁ VIMOS NESTA SEGURADORA (o mapa da URA, recortado):\n"
                  + mapa)
    irmas = _rotas_irmas(playbook, sessao, tela)
    if irmas:
        bloco += ("\n\nROTAS IRMÃS (passos conhecidos parecidos com esta tela, em outros corredores "
                  "desta seguradora ou deste serviço em outras):\n" + irmas)
    if memoria:
        bloco += "\n\nO QUE A CORRETORA JÁ ENSINOU:\n" + "\n".join(memoria)
    marca = "\n\nTela da seguradora agora"
    u = msgs["user"]
    msgs["user"] = u.replace(marca, bloco + marca, 1) if marca in u else u + bloco
    msgs["user"] = msgs["user"].replace("\n\nSua resposta:", "\n\nSua resposta (o JSON):")
    return msgs


async def mensagens_do_destravador(company_id: str, sessao: Dict[str, Any], tela: str, *,
                                   gatilho: str = "cerebro") -> Dict[str, str]:
    """`compor_mensagens` com o contexto que mora no banco (conversa, mapa, memória), em paralelo
    e com teto — nenhuma fonte segura a URA."""
    from app.services.insurer_dispatch_service import get_playbook

    playbook = get_playbook(str(sessao.get("playbook_ref") or "")) or {}
    conversa, mapa, memoria = await asyncio.gather(
        _com_teto(_conversa_do_segurado(company_id, sessao), []),
        _com_teto(_recorte_do_mapa(playbook, tela), ""),
        _com_teto(_memoria_da_corretora(company_id), []),
    )
    return compor_mensagens(sessao, tela, gatilho=gatilho, conversa=conversa, mapa=mapa,
                            memoria=memoria)


# ═════════════════════════════════════════════════════════════════════════════
# A POLÍTICA EM CÓDIGO — `decidir_destravamento` (a função única da SPEC §5 F1)
# ═════════════════════════════════════════════════════════════════════════════
def _n(s: Any) -> str:
    from app.services.insurer_dispatch_service import _norm_text

    return " ".join(re.sub(r"[^\w ]+", " ", _norm_text(str(s or ""))).split())


def opcoes_de_conteudo(tela: str) -> List[List[str]]:
    """As opções de CONTEÚDO da tela ([[tecla, rótulo], …]), sem navegação — o MESMO critério da
    pergunta do `sem_chute` (`sem_chute_ao_segurado`): numerada guarda o dígito da tela; lista de
    botões é renumerada 1..n (a volta casa pelo rótulo). "Nenhuma das anteriores" fica: é resposta."""
    from app.services import insurer_dispatch_service as IDS

    num = IDS.opcoes_numeradas(str(tela or ""))
    if num:
        return [[str(d), str(r)] for d, r in num if not IDS.navega_para_o_segurado(r)]
    conteudo = [str(r) for r in IDS._rotulos_da_tela(str(tela or "")) if not IDS.navega_para_o_segurado(r)]
    return [[str(i), r] for i, r in enumerate(conteudo, 1)]


def _pergunta_da_tela(tela: str) -> str:
    linhas = [" ".join(l.replace("*", "").split()) for l in str(tela or "").splitlines()]
    linhas = [l for l in linhas if l]
    com = [l for l in linhas if "?" in l]
    q = (com[-1] if com else (linhas[0] if linhas else "")).strip()
    return q[:200]


def _pergunta_ao_segurado(tela: str, opcoes: List[List[str]]) -> str:
    q = _pergunta_da_tela(tela)
    if opcoes:
        return f"A seguradora está perguntando: “{q}” — qual destas opções vale para você?"
    return f"A seguradora está perguntando: “{q}” — pode me responder?"


def _pergunta_do_custo(tela: str) -> str:
    """A pergunta ao segurado que MOSTRA o custo da tela — ele decide (D1)."""
    from app.services import insurer_dispatch_service as IDS

    linhas = [" ".join(l.replace("*", "").split()) for l in str(tela or "").splitlines()]
    dinheiro = [l for l in linhas if l and IDS._RX_DINHEIRO_NA_TELA.search(IDS._norm_text(l))]
    trecho = " / ".join(dinheiro)[:300] or _pergunta_da_tela(tela)
    return (f"A seguradora informou algo que envolve custo ou pagamento e precisa da sua decisão: "
            f"“{trecho}”. Como você quer seguir?")


def _rotulo_escolhido(tela: str, valor: str) -> str:
    from app.services.acao_do_cerebro import rotulo_de

    return rotulo_de(tela, valor)[1]


def _e_dado_do_caso(valor: str, sessao: Dict[str, Any]) -> bool:
    """O valor É um dado do caso? Os slots (sem tecla de menu `*_opcao`, sem o que o SISTEMA
    preencheu — `slots_padrao`) e o que foi capturado da seguradora."""
    v = _n(valor)
    if len(v) < 2:
        return False
    padrao = set(sessao.get("slots_padrao") or ())
    fontes = [(k, x) for k, x in (sessao.get("slots") or {}).items()
              if not str(k).endswith("_opcao") and k not in padrao]
    fontes += list((sessao.get("captured") or {}).items())
    for _k, x in fontes:
        if not isinstance(x, (str, int)) or isinstance(x, bool):
            continue
        d = _n(x)
        if not d:
            continue
        if v == d or (len(v) >= 3 and v in d) or (len(d) >= 4 and d in v and len(v) <= len(d) + 30):
            return True
    return False


def _digitos_do_caso(sessao: Dict[str, Any]) -> str:
    vals = list((sessao.get("slots") or {}).values()) + list((sessao.get("captured") or {}).values())
    return " ".join(re.sub(r"\D", "", str(x)) for x in vals if x not in (None, ""))


def _provedor_diferente(segunda: Optional[dict], provedor: str) -> bool:
    p2 = str((segunda or {}).get("provedor") or "").strip().lower()
    p1 = str(provedor or "").strip().lower()
    return bool(p1) and bool(p2) and p1 != p2


def decidir_destravamento(proposta: Proposta, sessao: Dict[str, Any], tela: str, *,
                          gatilho: str = "cerebro", limiar: int = LIMIAR_MINIMO, modo: str = "on",
                          provedor: str = "", segunda_opiniao: Optional[dict] = None,
                          pedir_segunda: bool = False, nunca=None) -> Destravamento:
    """A POLÍTICA (D1–D3 do Founder), em CÓDIGO. Pura: não chama modelo nem banco.

    `segunda_opiniao`: {"provedor","modelo","classe","acao","valor","nota"} do papel
    `destravador_segunda` (o que ele respondeu à MESMA tela, sem ver a primeira).
    `pedir_segunda=True`: quando o DEDUZIR chegou até a 2ª opinião e ela ainda não existe, a
    decisão volta com `proibicao="precisa_segunda_opiniao"` e `valor` = o candidato — quem chama
    busca a 2ª opinião e chama de novo. `nunca`: as chaves do NUNCA ligadas (a MUTAÇÃO do G2).
    """
    from app.services import acao_do_cerebro as AC
    from app.services import corridor_playbooks as CP
    from app.services import insurer_dispatch_service as IDS

    ligadas = NUNCA_SOZINHO if nunca is None else tuple(nunca)
    lim = _limiar_efetivo(limiar)
    playbook = IDS.get_playbook(str(sessao.get("playbook_ref") or "")) or {}
    ida = IDS.ida_e_volta_permitida(playbook) and bool(str(sessao.get("client_phone") or "").strip())
    conteudo = opcoes_de_conteudo(tela)
    p = proposta
    base = dict(classe=p.classe if p.classe in CLASSES else "nunca_sozinho", nota=p.nota, limiar=lim,
                motivo=p.motivo, modo=modo, acao_do_modelo=p.acao if p.formato_ok else "",
                valor_do_modelo=p.valor, formato_ok=p.formato_ok, provedor=provedor,
                segunda_opiniao=segunda_opiniao, gatilho=str(gatilho or ""))

    def pessoa(porque: str, classe: Optional[str] = None) -> Destravamento:
        d = Destravamento(acao="PESSOA", proibicao=porque, **base)
        if classe:
            d.classe = classe
        return d

    def perguntar(pergunta: str, porque: str = "", opcoes=None) -> Destravamento:
        if not ida:
            return pessoa(porque or "ida_e_volta_proibida")
        return Destravamento(acao="PERGUNTAR_AO_SEGURADO", valor=pergunta[:400],
                             opcoes=conteudo if opcoes is None else opcoes, proibicao=porque, **base)

    def rebaixar(porque: str) -> Destravamento:
        """DEDUZIR que não passou: pergunta ao segurado se a tela pergunta algo; senão pessoa."""
        if ida and (len(conteudo) >= 2 or re.search(IDS._MARCA_DE_PERGUNTA, IDS._norm_text(tela))):
            return perguntar(_pergunta_ao_segurado(tela, conteudo), porque)
        return pessoa(porque)

    # ① A saída do modelo não é a pedida → PESSOA. E o gatilho que nunca se destrava, idem.
    if not p.formato_ok:
        return pessoa(f"saida_invalida:{p.erro}", "nunca_sozinho")
    g = str(gatilho or "")
    if any(g == x or g.startswith(x + ":") or (x.endswith("_") and g.startswith(x))
           for x in GATILHOS_NUNCA_DESTRAVAVEIS):
        return pessoa("gatilho_nao_destravavel", "nunca_sozinho")

    norm_tela = IDS._norm_text(str(tela or ""))
    tem_pergunta = bool(re.search(IDS._MARCA_DE_PERGUNTA, norm_tela, re.IGNORECASE))
    valor = p.valor
    custo = "aceite_de_custo" in ligadas and bool(
        AC.proibicao(tela, valor if p.acao == "RESPONDER" else "", playbook=playbook, session=sessao,
                     proibicoes=("aceite_de_custo",)))

    # ② SILENCIO — o código prova que cabe (o MESMO discriminador do produto).
    if p.acao == "SILENCIO":
        gs = IDS.guard_human_phase_reply("SEM_RESPOSTA", sessao, insurer_message=tela)
        if gs.get("silencio"):
            return Destravamento(acao="SILENCIO", **base)
        return pessoa("silencio_numa_tela_que_pede")

    # ③ O NUNCA SOZINHO — antes de qualquer classe. Custo: o segurado decide, vendo o valor.
    if custo:
        return perguntar(_pergunta_do_custo(tela), "custo_e_do_segurado")
    if "afirma_cobertura" in ligadas and AC._RX_AFIRMA_COBERTURA.search(valor or ""):
        return pessoa("afirma_cobertura")
    if p.acao == "PESSOA":
        return pessoa("o_modelo_chamou_uma_pessoa")
    if p.acao == "RESPONDER":
        rot = _rotulo_escolhido(tela, valor)
        alvo = _n(rot or valor)
        afirma = bool(_RX_AFIRMATIVO.search(_n(valor)) or _RX_AFIRMATIVO.search(alvo))
        if "abrir_sinistro" in ligadas and (
                _RX_SINISTRO.search(alvo) or (afirma and _RX_TELA_ABRE_SINISTRO.search(norm_tela))):
            return pessoa("abrir_sinistro")
        if "cancelar_pedido" in ligadas and (
                _RX_CANCELA.search(alvo) or (afirma and tem_pergunta and _RX_CANCELA.search(norm_tela))):
            return pessoa("cancelar_pedido")
        if "novo_atendimento" in ligadas and CP._RX_COMECA_TRABALHO_NOVO.search(alvo):
            return pessoa("novo_atendimento")
        if "condominio_ou_empresarial" in ligadas and rot:
            try:
                from app.providers.policy_data_provider import familia_de_ramo_do_rotulo

                if familia_de_ramo_do_rotulo(rot) in ("cond", "empr"):
                    return pessoa("condominio_ou_empresarial")
            except Exception:  # noqa: BLE001 — sem o dono da pergunta, não se decide ramo
                return pessoa("condominio_ou_empresarial")
        if "confirmacao_final" in ligadas and playbook and IDS.detect_finalize_anchor(playbook, str(tela)) \
                and not IDS._finalize_allowed(sessao):
            return pessoa("confirmacao_final")
        if "inventar_dado" in ligadas:
            do_caso = _digitos_do_caso(sessao)
            if any(r not in do_caso for r in re.findall(r"\d{3,}", re.sub(r"[.\-/ ]", "", valor))):
                return pessoa("inventar_dado")
            # a tela pede um DADO (placa, CPF, telefone, endereço… — a tabela do PRODUTO,
            # `_PERGUNTAS_DE_DADO`) e o valor não é opção da tela nem dado do caso
            if not rot and not _e_dado_do_caso(valor, sessao) and any(
                    re.search(rx, norm_tela, re.IGNORECASE) for _c, rx, _s in IDS._PERGUNTAS_DE_DADO):
                return pessoa("inventar_dado")
        # agendar data/período → a agenda é do SEGURADO (D1: reversível, mas dele)
        if _RX_AGENDA.search(norm_tela) and not sessao.get("agendamento_autorizado"):
            return perguntar(_pergunta_ao_segurado(tela, conteudo), "agenda_e_do_segurado")

    # ④ A tela de um passo `sem_chute`: o modelo NUNCA a responde (SPEC-122 F2, em código).
    passo_sc = AC.passo_sem_chute_da_tela(tela, playbook, sessao)
    if (passo_sc is not None or g.startswith("sem_chute:")) and p.acao == "RESPONDER":
        passo = str((passo_sc or {}).get("step") or "")
        texto = IDS.SEM_CHUTE_PERGUNTAVEL.get(passo)
        if passo and not texto:
            # ⛔ D-122: os `sem_chute` de DECISÃO (escolher serviço/veículo/motivo) vão a uma pessoa.
            return pessoa("passo_sem_chute_de_decisao")
        pergunta = (f"Preciso de uma informação para a seguradora: {texto}?" if texto
                    else _pergunta_ao_segurado(tela, conteudo))
        return perguntar(pergunta, "passo_sem_chute")

    # ⑤ PERGUNTAR — a pergunta do modelo (2ª pessoa) + as opções de CONTEÚDO da tela.
    if p.acao == "PERGUNTAR_AO_SEGURADO":
        return perguntar(valor, "")

    # ⑥ RESPONDER, por classe.
    classe = p.classe
    if classe == "conduzir":
        rot = _rotulo_escolhido(tela, valor)
        eco = IDS.classe_da_tela(playbook, str(tela), slots=sessao.get("slots")).get("chave") == "eco_de_dado"
        if not ((rot and IDS.rotulo_e_de_navegacao(rot)) or eco):
            classe = "deduzir"        # não é navegação: é escolha — a régua do DEDUZIR
    if classe == "responder_com_dado" and not _e_dado_do_caso(valor, sessao):
        classe = "deduzir"            # não é dado do caso: é dedução
    base["classe"] = classe
    if classe == "deduzir":
        if conteudo and not _rotulo_escolhido(tela, valor):
            return rebaixar("valor_fora_das_opcoes")
        if p.nota is None or p.nota < lim:
            return rebaixar("nota_abaixo_do_limiar")
        if segunda_opiniao is None:
            if pedir_segunda:
                return Destravamento(acao="PESSOA", valor=valor, proibicao="precisa_segunda_opiniao", **base)
            return rebaixar("sem_segunda_opiniao")
        if not _provedor_diferente(segunda_opiniao, provedor):
            return rebaixar("segunda_opiniao_do_mesmo_provedor")
        concordou = (str(segunda_opiniao.get("acao") or "") == "RESPONDER"
                     and AC._mesma_resposta(tela, valor, str(segunda_opiniao.get("valor") or "")))
        segunda_opiniao["concordou"] = bool(concordou)
        if not concordou:
            return rebaixar("segunda_opiniao_discordou")

    # ⑦ O conferente do PRODUTO sobre o valor (invented_number, protocolo sem captura, frase…).
    gr = IDS.guard_human_phase_reply(valor, sessao, insurer_message=tela)
    if not gr.get("ok"):
        return pessoa(f"conferente:{gr.get('reason') or 'recusou'}")
    return Destravamento(acao="RESPONDER", valor=str(gr.get("reply") or valor), **base)


# ═════════════════════════════════════════════════════════════════════════════
# O MODELO — pela fábrica do produto, com o papel; em sombra, ISOLADO da produção
# ═════════════════════════════════════════════════════════════════════════════
def _provedor_da_resposta(resposta: Any, resolvido: Any) -> Tuple[str, str]:
    """(provedor, modelo) de quem RESPONDEU de fato — a reserva pode ter respondido.

    `response_metadata.model_provider` (langchain ≥ 1.1: "openai"/"anthropic"); senão o nome do
    modelo contra o primário e a reserva resolvidos. Desconhecido → ("", modelo) — e o DEDUZIR
    não passa (a 2ª opinião não pode provar que é de outro provedor)."""
    meta = getattr(resposta, "response_metadata", None) or {}
    nome = str(meta.get("model_name") or meta.get("model") or "")
    candidatos = [c for c in (resolvido, getattr(resolvido, "reserva", None)) if c is not None]
    prov = str(meta.get("model_provider") or "").strip().lower()
    conhecidos = {str(getattr(c, "provider", "")) for c in candidatos}
    if prov and prov in conhecidos:
        modelo = next((c.model for c in candidatos if c.provider == prov), nome)
        return prov, (nome or modelo)
    for c in candidatos:
        if nome and nome.startswith(str(c.model)):
            return str(c.provider), nome
    return "", nome


def _custo(resposta: Any, modelo: str) -> float:
    try:
        from app.factories import model_policy as MP

        uso = dict(getattr(resposta, "usage_metadata", None) or {})
        if not uso:
            bruto = (getattr(resposta, "response_metadata", None) or {})
            bruto = bruto.get("usage") or bruto.get("token_usage") or {}
            uso = {"input_tokens": bruto.get("input_tokens") or bruto.get("prompt_tokens"),
                   "output_tokens": bruto.get("output_tokens") or bruto.get("completion_tokens")}
        cat = MP.catalogo()
        # o provedor devolve o nome DATADO ("…-2026-09-27"): o preço é o da chave do catálogo
        chave = modelo if modelo in cat else max(
            (k for k in cat if str(modelo or "").startswith(k)), key=len, default="")
        linha = cat.get(chave) or {}
        pin = float(linha.get("input_price_per_million") or 0)
        pout = float(linha.get("output_price_per_million") or 0)
        return round(int(uso.get("input_tokens") or 0) * pin / 1e6
                     + int(uso.get("output_tokens") or 0) * pout / 1e6, 6)
    except Exception:  # noqa: BLE001
        return 0.0


async def _chamar_isolado(resolvido: Any, mensagens: list, company_id: str, service_type: str):
    """UMA chamada SEM reserva e SEM o relógio do disjuntor de produção (a SOMBRA).

    🔴 O mesmo isolamento da SPEC-122 (red team P4, juiz P2): disjuntor do provedor aberto ou em
    sonda → não chama (não disputa o provedor caído); o relógio sai do modelo
    (`acao_do_cerebro._sem_o_relogio_de_producao`). O custo continua no ledger, com a corretora."""
    from app.core.relogio_do_modelo import estado_do_breaker
    from app.factories.llm_factory import LLMFactory
    from app.services.acao_do_cerebro import _sem_o_relogio_de_producao

    try:
        estado = (await estado_do_breaker(resolvido.provider)).get("estado")
    except Exception:  # noqa: BLE001 — sem saber, a sombra fica de fora
        estado = "desconhecido"
    if estado != "fechado":
        logger.info("[DESTRAVADOR] sombra: disjuntor de %s %s — não chama", resolvido.provider, estado)
        return None
    llm = LLMFactory.create_llm({}, {}, company_id=company_id, service_type=service_type,
                                modelo_resolvido=resolvido)
    return await _sem_o_relogio_de_producao(llm).ainvoke(mensagens)


async def _chamar_quem_decide(mensagens: list, company_id: str, modo: str):
    """(resposta, provedor, modelo). `on`: pela RESERVA do papel (`invocar_com_reserva`).
    `sombra`: só o primário, isolado."""
    from app.factories import llm_factory as LF

    resolvido = LF.LLMFactory.resolver_para({}, {}, papel=PAPEL)
    if modo == "sombra":
        r = await asyncio.wait_for(_chamar_isolado(resolvido, mensagens, company_id, SERVICE_TYPE),
                                   timeout=TETO_DA_CHAMADA_S)
    else:
        r = await asyncio.wait_for(LF.invocar_com_reserva(PAPEL, mensagens, company_id=company_id,
                                                          service_type=SERVICE_TYPE),
                                   timeout=TETO_DA_CHAMADA_S)
    if r is None:
        return None, "", ""
    prov, modelo = _provedor_da_resposta(r, resolvido)
    return r, prov, modelo


def candidatos_da_segunda(provedor_de_quem_decidiu: str) -> list:
    """Os modelos do papel `destravador_segunda` de provedor DIFERENTE do que decidiu, em ordem.

    🔴 D3: "o conselho de LLMs DIFERENTES". Se a reserva decidiu (provedor trocou), a 2ª opinião
    troca de lado junto. Provedor de quem decidiu desconhecido → nenhum candidato (não se prova)."""
    from app.factories.llm_factory import LLMFactory

    p1 = str(provedor_de_quem_decidiu or "").strip().lower()
    if not p1:
        return []
    r = LLMFactory.resolver_para({}, {}, papel=PAPEL_SEGUNDA)
    return [c for c in (r, getattr(r, "reserva", None)) if c is not None and c.provider != p1]


async def _segunda_opiniao(mensagens: list, company_id: str, modo: str, provedor: str,
                           tela: str) -> Tuple[Optional[dict], float]:
    """A 2ª opinião: a MESMA tela, o MESMO contexto, sem ver a primeira (independente)."""
    from app.core.relogio_do_modelo import motivo_de_reserva
    from app.factories.llm_factory import LLMFactory
    from app.agents.utils import extract_text_from_content

    custo = 0.0
    for cand in candidatos_da_segunda(provedor):
        try:
            if modo == "sombra":
                r = await asyncio.wait_for(_chamar_isolado(cand, mensagens, company_id,
                                                           SERVICE_TYPE_SEGUNDA),
                                           timeout=TETO_DA_CHAMADA_S)
            else:
                llm = LLMFactory.create_llm({}, {}, company_id=company_id,
                                            service_type=SERVICE_TYPE_SEGUNDA, modelo_resolvido=cand)
                r = await asyncio.wait_for(llm.ainvoke(mensagens), timeout=TETO_DA_CHAMADA_S)
        except Exception as e:  # noqa: BLE001
            logger.warning("[DESTRAVADOR] 2ª opinião (%s) falhou: %s", cand.provider, type(e).__name__)
            if modo == "sombra" or motivo_de_reserva(e) is None:
                return None, custo
            continue
        if r is None:
            return None, custo
        prov, modelo = _provedor_da_resposta(r, cand)
        custo += _custo(r, cand.model)
        pr = ler_destravamento(extract_text_from_content(getattr(r, "content", None)) or "")
        return ({"provedor": prov or "", "modelo": modelo or cand.model, "classe": pr.classe,
                 "acao": pr.acao if pr.formato_ok else "PESSOA", "valor": pr.valor, "nota": pr.nota,
                 "formato_ok": pr.formato_ok, "concordou": False}, custo)
        # (a 2ª opinião que decidiu por um provedor inesperado é recusada pela política)
    return None, custo


# ═════════════════════════════════════════════════════════════════════════════
# O DIÁRIO — uma linha por decisão (F4 é a dona da tabela; aqui só se CHAMA)
# ═════════════════════════════════════════════════════════════════════════════
ACAO_NO_DIARIO = {
    "RESPONDER": "respondeu_ura",
    "PERGUNTAR_AO_SEGURADO": "perguntou_segurado",
    "PESSOA": "chamou_pessoa",
    # constante_justificada: SILENCIO não é nenhuma das três — o agente decidiu NÃO responder a uma
    # tela que só avisa. Dos quatro valores do contrato, o que diz isso é `nao_agiu`.
    "SILENCIO": "nao_agiu",
}


def chave_de_idempotencia(company_id: str, sessao: Dict[str, Any], tela: str) -> str:
    """empresa + acionamento + tela (CONTRATO-123): a mesma tela no mesmo acionamento, UMA linha."""
    run = str((sessao or {}).get("work_run_id") or (sessao or {}).get("case_id") or "")
    t = " ".join(_n(tela).split())
    return f"destravador:{company_id}:{run}:{hashlib.sha256(t.encode()).hexdigest()[:24]}"


def _frase_propria(*, seguradora: str, tela: str, classe: str, acao: str, valor: str, nota,
                   segunda_opiniao, motivo: str) -> str:
    """A frase para GENTE (D7), no formato do contrato — quando o diário ainda não a tem."""
    nome = (seguradora or "a seguradora").strip().capitalize()
    q = _pergunta_da_tela(tela)[:120] or "uma tela que o robô não conhecia"
    fez = {"respondeu_ura": f"respondeu “{valor[:80]}”",
           "perguntou_segurado": "perguntou ao segurado",
           "chamou_pessoa": "chamou uma pessoa da equipe",
           "nao_agiu": "não respondeu (a tela só avisava)"}.get(acao, "decidiu")
    extra = []
    if nota is not None:
        extra.append(f"certeza {nota}%")
    if segunda_opiniao:
        extra.append("a segunda opinião concordou" if segunda_opiniao.get("concordou")
                     else "a segunda opinião discordou")
    porque = f" porque {motivo.rstrip('.')}" if motivo else ""
    return f"A {nome} perguntou “{q}”. O agente {fez}{porque}" + (f" ({', '.join(extra)})." if extra else ".")


async def _registrar(company_id: str, sessao: Dict[str, Any], tela: str, d: Destravamento,
                     playbook: Dict[str, Any]) -> Optional[str]:
    """UMA linha no diário. Best-effort: sem o módulo (ainda) ou com falha, loga e segue."""
    try:
        from app.services import diario_de_decisoes as DD
    except Exception as e:  # noqa: BLE001 — a F4 costura depois
        logger.warning("[DESTRAVADOR] diário indisponível (%s) — decisão sem linha", type(e).__name__)
        return None
    acao_diario = "nao_agiu" if d.modo == "sombra" else ACAO_NO_DIARIO.get(d.acao, "chamou_pessoa")
    seguradora = str(playbook.get("insurer_key") or "")
    try:
        frase = getattr(DD, "frase_para_gente", _frase_propria)(
            seguradora=seguradora, tela=tela, classe=d.classe,
            acao=ACAO_NO_DIARIO.get(d.acao, "chamou_pessoa"), valor=d.valor, nota=d.nota,
            segunda_opiniao=d.segunda_opiniao, motivo=d.motivo)
    except Exception:  # noqa: BLE001
        frase = _frase_propria(seguradora=seguradora, tela=tela, classe=d.classe,
                               acao=ACAO_NO_DIARIO.get(d.acao, "chamou_pessoa"), valor=d.valor,
                               nota=d.nota, segunda_opiniao=d.segunda_opiniao, motivo=d.motivo)
    if d.modo == "sombra":
        frase += " (Em sombra: nada foi enviado.)"
    d.explicacao = frase
    try:
        return await DD.registrar_decisao(
            company_id=str(company_id), origem="acionamento",
            work_run_id=str(sessao.get("work_run_id") or "") or None,
            conversation_id=str(sessao.get("mirror_conversation_id") or "") or None,
            seguradora=seguradora, ramo=str(playbook.get("line_kind") or ""),
            rota=str(sessao.get("playbook_ref") or ""), servico=str(sessao.get("subservice") or ""),
            tela=str(tela or ""), classe=d.classe, acao=acao_diario, valor=d.valor, nota=d.nota,
            limiar=d.limiar, motivo=(d.motivo + (f" [{d.proibicao}]" if d.proibicao else ""))[:300],
            explicacao_para_gente=frase, modelo=d.modelo, segunda_opiniao=d.segunda_opiniao,
            modo=d.modo, gatilho=d.gatilho or "cerebro",
            chave_idempotencia=chave_de_idempotencia(company_id, sessao, tela), sessao=sessao)
    except Exception as e:  # noqa: BLE001
        logger.warning("[DESTRAVADOR] diário falhou (%s)", type(e).__name__)
        return None


# ═════════════════════════════════════════════════════════════════════════════
# O FIO — `destravar`
# ═════════════════════════════════════════════════════════════════════════════
async def destravar(company_id: str, sessao: dict, tela: str, *, gatilho: str, modo: str,
                    limiar: int = 70) -> Destravamento:
    """UMA trava → UMA decisão. `gatilho` = o reason do motor (ponto B) ou "cerebro"/"sentinela"
    (ponto A). Monta o contexto COMPLETO, chama o modelo do papel `destravador`, aplica a POLÍTICA
    EM CÓDIGO, registra no diário e devolve a decisão. ⛔ Nunca envia nada. Nunca levanta."""
    try:
        return await _destravar(company_id, sessao, tela, gatilho=gatilho, modo=modo, limiar=limiar)
    except Exception as e:  # noqa: BLE001 — falha fechada
        logger.error("[DESTRAVADOR] falhou (%s) — pessoa", type(e).__name__)
        return Destravamento(classe="nunca_sozinho", acao="PESSOA", proibicao="falha_do_destravador",
                             limiar=_limiar_efetivo(limiar),
                             modo=modo if modo in ("on", "sombra") else "on", gatilho=str(gatilho or ""))


async def _destravar(company_id: str, sessao: dict, tela: str, *, gatilho: str, modo: str,
                     limiar: int) -> Destravamento:
    from langchain_core.messages import HumanMessage, SystemMessage

    from app.agents.utils import extract_text_from_content
    from app.services.insurer_dispatch_service import get_playbook

    m = str(modo or "").strip().lower()
    lim = _limiar_efetivo(limiar)
    cid = str(company_id or "").strip()
    sessao = dict(sessao or {})
    if m not in ("on", "sombra") or not cid or not str(tela or "").strip():
        return Destravamento(classe="nunca_sozinho", acao="PESSOA", proibicao="chamada_invalida",
                             limiar=lim, modo=m if m in ("on", "sombra") else "on", gatilho=str(gatilho or ""))
    playbook = get_playbook(str(sessao.get("playbook_ref") or "")) or {}
    g = str(gatilho or "")
    if not playbook or any(g == x or g.startswith(x + ":") or (x.endswith("_") and g.startswith(x))
                           for x in GATILHOS_NUNCA_DESTRAVAVEIS):
        # Nem se gasta o modelo: a regra é de código.
        return Destravamento(classe="nunca_sozinho", acao="PESSOA",
                             proibicao="gatilho_nao_destravavel" if playbook else "sem_corredor",
                             limiar=lim, modo=m, gatilho=g)

    msgs = await mensagens_do_destravador(cid, sessao, tela, gatilho=g)
    conversa = [SystemMessage(content=msgs["system"]), HumanMessage(content=msgs["user"])]
    try:
        resposta, provedor, modelo = await _chamar_quem_decide(conversa, cid, m)
    except Exception as e:  # noqa: BLE001 — o modelo caiu: nada foi decidido
        logger.warning("[DESTRAVADOR] modelo falhou (%s) — pessoa", type(e).__name__)
        return Destravamento(classe="nunca_sozinho", acao="PESSOA", proibicao="modelo_falhou",
                             limiar=lim, modo=m, gatilho=g)
    if resposta is None:
        return Destravamento(classe="nunca_sozinho", acao="PESSOA", proibicao="modelo_nao_chamado",
                             limiar=lim, modo=m, gatilho=g)
    custo = _custo(resposta, modelo)
    proposta = ler_destravamento(extract_text_from_content(getattr(resposta, "content", None)) or "")
    d = decidir_destravamento(proposta, sessao, tela, gatilho=g, limiar=lim, modo=m,
                              provedor=provedor, pedir_segunda=True)
    if d.proibicao == "precisa_segunda_opiniao":
        segunda, c2 = await _segunda_opiniao(conversa, cid, m, provedor, tela)
        custo += c2
        if segunda is None:
            d = decidir_destravamento(proposta, sessao, tela, gatilho=g, limiar=lim, modo=m,
                                      provedor=provedor, pedir_segunda=False)
        else:
            d = decidir_destravamento(proposta, sessao, tela, gatilho=g, limiar=lim, modo=m,
                                      provedor=provedor, segunda_opiniao=segunda)
    d.modelo = modelo
    d.custo_usd = round(custo, 6)
    d.modelo_chamado = True
    d.diario_id = await _registrar(cid, sessao, tela, d, playbook)
    return d


# ═════════════════════════════════════════════════════════════════════════════
# O PONTO B EM SOMBRA — a F1b só CHAMA; a cota, o dedupe e o isolamento são os da sombra
# ═════════════════════════════════════════════════════════════════════════════
def agendar_em_sombra(company_id: str, sessao_copia: dict, tela: str, *,
                      gatilho: str) -> Optional["asyncio.Task"]:
    """Agenda o destravador em SOMBRA para uma trava do MOTOR (ponto B), sem esperar.

    O sistema FEZ o de hoje (uma pessoa). Pela MESMA sombra de `acao_do_cerebro.agendar_sombra`:
    mesma cota em voo, mesmo dedupe por acionamento+tela, mesmo isolamento do disjuntor, e a
    chave `cerebro_modos` tem de dizer `sombra`. ⛔ Nunca levanta; nunca envia."""
    try:
        from app.services.acao_do_cerebro import agendar_sombra

        return agendar_sombra(company_id, sessao_copia, tela,
                              {"acao": "PESSOA", "valor": "", "gatilho": str(gatilho or "")})
    except Exception as e:  # noqa: BLE001
        logger.warning("[DESTRAVADOR] sombra não agendada (%s)", type(e).__name__)
        return None
