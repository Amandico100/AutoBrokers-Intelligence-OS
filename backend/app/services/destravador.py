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

#: constante_justificada: a PORTA do DEDUZIR autônomo é a CALIBRAÇÃO (SPEC-123 G3 / D2: "na faixa de
#: nota em que age, acerto ≥ 90%"), e ela NÃO existe. 📊 bancada real de 30/09
#: (`docs/canon/reports/SPEC-123-BANCADA.md` §4, `scripts/bancada.py --resumo-destravador`): o
#: modelo principal do papel acerta 5/14 = 36 % [16–61] das propostas DEDUZIR com nota ≥ 70 — e dá nota 90–99 a
#: TODAS, inclusive às 9 erradas (a nota não discrimina); nenhum limiar 70..100 chega a 90 %. E o único
#: grave da bancada (`cer-T-ura_recomeca-porto-092`, nota 99, 2ª opinião CONCORDANDO) é DEDUZIR.
#: Com False, todo DEDUZIR é rebaixado (pergunta ao segurado quando a tela pergunta, senão pessoa) com
#: `proibicao="deduzir_sem_calibracao"` — e a 2ª opinião nem é chamada. CONDUZIR, RESPONDER COM DADO e
#: PERGUNTAR seguem livres. ⚠️ Só vira True com uma rodada de calibração que passe o G3 (decisão do
#: gerente/Founder). MUTAÇÃO: True → `test_spec123_f5a_costura.py::test_o_grave_porto_092_...` VERMELHO.
DEDUZIR_AUTONOMO_CALIBRADO = False

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
    "trocar_titular",            # "Informar outro CPF/CNPJ": é o "inventar CPF" do D1 (titular errado)
    "afirma_cobertura",          # só a seguradora afirma cobertura
    "confirmar_abertura",        # conserto X: confirmar a abertura sem o caso completo (ou com o resumo divergente)
)

PORQUE = {
    "aceite_de_custo": "a seguradora falou de custo ou pagamento — quem decide é o segurado",
    "abrir_sinistro": "a resposta abriria um sinistro — isso é com uma pessoa",
    "cancelar_pedido": "a resposta cancelaria o pedido — isso é com uma pessoa",
    "novo_atendimento": "a resposta abriria um NOVO atendimento e perderia o que está em curso",
    "condominio_ou_empresarial": "condomínio e empresarial ficam com a atendente",
    "confirmacao_final": "a tela confirma a abertura do serviço e o modo de ensaio não autoriza",
    "inventar_dado": "a resposta traria um número que não está no caso",
    "trocar_titular": "a resposta trocaria o CPF/CNPJ do titular — isso é com uma pessoa",
    "afirma_cobertura": "a resposta falava de cobertura — só a seguradora afirma cobertura",
    "confirmar_abertura": ("a tela confirma a abertura do serviço e o caso não está completo (ou o resumo "
                           "não bate com o caso) — isso é com uma pessoa"),
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
#: constante_justificada: TROCAR O TITULAR (sobre o rótulo escolhido, normalizado). 📊 A redação real
#: (`tests/corpus/bancada/cerebro/casos.jsonl`, cer-T-ura_recomeca-porto-091/092 — o menu raiz da
#: Porto que reaparece com "bom ter você de volta"): "Informar outro CPF/CNPJ". A bancada de 30/09
#: mediu os dois braços (notas 99 e 88) escolhendo-a com a 2ª opinião CONCORDANDO — o único grave.
#: D1 do Founder: "inventar CPF" é NUNCA SOZINHO; um CPF que não é o do caso é isso. A mesma família
#: do juiz da bancada (`evals/bancada._RX_OPCAO_GRAVE`: outro cpf · outro titular · outro cnpj).
_RX_TROCA_TITULAR = re.compile(
    r"\b(?:outr[oa]|nov[oa]|diferente)\s+(?:cpf|cnpj|titular|documento)\b|"
    r"\b(?:trocar|alterar|mudar)\s+(?:o\s+)?(?:cpf|cnpj|titular)\b")
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

# ── CONSERTO ÚNICO · parte X (juiz B1/B2 · red team B1/B2/B3) — o vocabulário que passou ──────────
# Todas sobre texto NORMALIZADO (`_norm_text`: minúsculo, sem acento). 📊 As redações vêm das
# reproduções do red team (`rt-scripts/pol.py` C1–C13) e do acervo (`tests/corpus/telas_reais`).
#: constante_justificada: CUSTO sem as palavras de `_RX_DINHEIRO_NA_TELA` do produto — 📊 pol.py
#: C1 "participação de 150 reais", C2/C3 "o prestador poderá cobrar pelo excedente" (azul-auto, tela
#: REAL "superior ao limite … cobrar pelo excedente"), C6 "custará cento e cinquenta reais", e "valor
#: de". Responder a uma OPÇÃO (ou afirmar) numa tela destas é aceitar o custo: quem decide é o segurado.
_RX_CUSTO_DA_TELA_EXTRA = re.compile(
    r"\bparticipac(?:ao|oes)\b|\breais\b|\bcobrar\b|\bexcedente\b|\bvalor de\b|\bcustar(?:a|ao)?\b")
#: constante_justificada: a TELA que abre SINISTRO com outras palavras — 📊 pol.py C7 "Deseja
#: registrar a ocorrência agora?", C8 "acionar o seguro para o conserto do veículo".
_RX_TELA_ABRE_SINISTRO_EXTRA = re.compile(
    r"registrar (?:a |uma )?ocorrencia|acionar (?:o |a )?(?:seguro|apolice) para")
#: constante_justificada: a TELA que CANCELA com outras palavras — 📊 pol.py C9 "Deseja desistir da
#: solicitação?", C10 "Deseja encerrar a solicitação em andamento?" (o produto já lista `desistir` e
#: `encerrar` como DECISÃO em `_PERGUNTAS_DE_DECISAO`; aqui é a resposta AFIRMATIVA que executa).
_RX_TELA_CANCELA_EXTRA = re.compile(
    r"\bdesist|\bencerrar (?:a |o |sua |seu )?(?:solicitacao|pedido|servico|chamado|assistencia)")
#: constante_justificada: a TELA que abre OUTRO trabalho com outras palavras — 📊 pol.py C11 "Gostaria
#: de fazer uma nova solicitação?". "nova solicitação" sozinha basta: 0 telas do acervo a usam para
#: o pedido EM CURSO (é sempre o segundo).
_RX_TELA_NOVO_EXTRA = re.compile(r"\bnov[oa] solicitac|\bfazer (?:um |uma )?(?:nov[oa]|outr[oa]) ")
#: constante_justificada: a TELA que CONFIRMA A ABERTURA do serviço — 📊 acervo: allianz/alfa
#: "Podemos confirmar o atendimento?", bradesco "Posso confirmar a abertura da sua assistência?",
#: "Posso confirmar o agendamento da assistência?". Afirmar aqui ABRE o serviço: só com o caso
#: completo e sem o conferente ter dito que o resumo diverge (red team e2e_conf: "Sim" a um resumo
#: com a origem errada mandava o guincho a outro endereço).
_RX_TELA_CONFIRMA_ABERTURA = re.compile(
    r"(?:podemos|posso|vamos|deseja|quer) confirmar (?:a |o )?(?:abertura|atendimento|agendamento|"
    r"servico|solicitacao|assistencia|pedido)|confirmar a abertura")
#: constante_justificada: a OPÇÃO que nunca vai ao segurado nem volta dele à URA (X1). O mesmo
#: irreversível do NUNCA — sinistro, cancelar, outro CPF/titular, novo atendimento — e o humano DA
#: SEGURADORA (D10: 📊 o corredor azul diz que "Falar com atendente" joga o caso na fila dela).
_RX_OPCAO_QUE_NAO_VAI_AO_SEGURADO = re.compile(
    r"\bsinistro|\baviso de ocorrencia\b|\bcancel|\bdesist|\b(?:falar|conversar) com (?:um |uma |o |a )?"
    r"(?:atendente|consultor|consultora|especialista|pessoa|humano)|\batendente\b")
#: constante_justificada: o SIM/NÃO genérico — nunca é "dado do caso" numa tela que não declara o
#: slot (juiz B2 · red team B1: com `pessoa_no_local="Sim"`, "Sim" passava por dado em QUALQUER tela).
_RX_SIM_NAO = re.compile(r"^(?:sim|nao|s|n|ok|confirmo|correto|isso|claro|certo)$")


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


def _caso_em_palavras(sessao: Dict[str, Any], playbook: Optional[Dict[str, Any]] = None) -> str:
    """O serviço pedido + o que a seguradora costuma pedir nele (✔ o caso tem / ✘ falta).

    F1c: os VALORES do caso NÃO se repetem aqui — já estão inteiros nos "Dados do caso" do
    produto (todo slot, a marca de padrão e o capturado da seguradora). 📊 A lista repetida
    custava tokens em toda chamada e não acrescentava nenhum dado."""
    sub = str(sessao.get("subservice") or "").strip()
    txt = (f"o serviço pedido é {sub.replace('_', ' ') or 'não informado'} (os valores estão nos "
           "dados do caso, acima).")
    pede = _o_que_vai_pedir(playbook or {}, sessao)
    if pede:
        txt += "\nO que a seguradora costuma pedir neste serviço:\n" + pede
    return txt


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


#: 🔴 A PARTE FIXA do prompt — a MESMA em TODA chamada (toda corretora, seguradora, caso e tela) e o
#: COMEÇO do `system`. O cache de prompt casa por PREFIXO (OpenAI: automático; Anthropic: desligado
#: pelo número — ver `mensagens_para_o_provedor`): nada que varia pode vir antes dela.
#: ⛔ Não interpolar nada aqui (nem seguradora, nem data): um byte variável no começo zera o cache.
INSTRUCAO_DO_DESTRAVADOR = (
    "══════ VOCÊ FOI CHAMADO PORQUE O ROTEIRO AUTOMÁTICO TRAVOU ══════\n"
    "OBJETIVO: levar este acionamento até o PROTOCOLO da seguradora sem chamar uma pessoa da "
    "corretora — com a resposta CERTA. Cada pessoa chamada é um segurado esperando mais, e a URA "
    "encerra a conversa se ninguém responde; cada resposta errada pode virar um chamado recusado no "
    "local, depois de o segurado esperar horas.\n"
    "Leia TUDO (o caso, a conversa com o segurado, as falas anteriores, as rotas parecidas) e decida "
    "ESTA tela como um atendente experiente decidiria. Esta instrução SUBSTITUI as regras do roteiro "
    "abaixo sobre NAO_SEI e SEM_RESPOSTA: a sua resposta é sempre o JSON pedido no fim.\n\n"
    "CLASSES — escolha UMA:\n"
    "- conduzir: a tela só move o fluxo (Continuar, \"quer seguir?\", voltar ao menu quando a "
    "conversa se perdeu). valor = a opção exata da tela. Se a tela só avisa e não pede nada: acao "
    "SILENCIO, valor vazio.\n"
    "- responder_com_dado: a tela pede um dado que ESTÁ no caso (placa, endereço, CPF, quem está "
    "no local). valor = o dado, como está no caso.\n"
    "- deduzir: a tela pede para escolher entre alternativas e o caso/relato indica qual. valor = o "
    "número ou o rótulo da opção.\n"
    "- perguntar_ao_segurado: só o segurado sabe (a situação no local, o detalhe do problema, uma "
    "escolha que o caso não diz). valor = a pergunta a ELE, curta, em segunda pessoa (\"você\"), "
    "sem prometer cobertura.\n"
    "- nunca_sozinho: o que NÃO TEM VOLTA — aceitar custo, franquia ou pagamento; abrir sinistro; "
    "cancelar um pedido; abrir um NOVO atendimento quando já há um; informar dado que não está no "
    "caso; afirmar cobertura. acao PESSOA (valor vazio) — ou PERGUNTAR_AO_SEGURADO quando é ele quem "
    "decide (um custo, uma data).\n\n"
    "NOTA (0 a 100): a chance REAL de a sua resposta estar certa. Calibre: 90 quer dizer que você "
    "erraria 1 em cada 10. A nota decide se você age sozinho; inflá-la é o erro mais caro. O código "
    "confere tudo antes de sair.\n\n"
    "RESPOSTA: UM objeto JSON numa linha, sem texto antes ou depois (o valor de RESPONDER vai à "
    "seguradora exatamente como escrito):\n"
    '{"classe": "<conduzir|responder_com_dado|deduzir|perguntar_ao_segurado|nunca_sozinho>", '
    '"acao": "<RESPONDER|PERGUNTAR_AO_SEGURADO|PESSOA|SILENCIO>", "valor": "<texto>", '
    '"nota": <0-100>, "motivo": "<até 15 palavras>"}\n\n'
    "══════ O ROTEIRO DESTA SEGURADORA ══════\n"
)

#: Onde começa a parte do `user` que MUDA a cada tela (o porquê desta chamada, as falas antigas, o
#: mapa, as rotas irmãs, o que o produto diz sobre esta tela, a tela). Tudo ANTES dela é o mesmo
#: dentro de um acionamento (os dados do caso, o conhecimento do fluxo, a memória, a conversa com o
#: segurado) — o prefixo estável do acionamento (o cache automático da OpenAI casa por prefixo).
_MARCA_DO_VARIAVEL = "\n\n🔴 POR QUE VOCÊ FOI CHAMADO: "

#: constante_justificada: os blocos do prompt do PRODUTO (`build_human_phase_messages`) que mudam a
#: cada TELA — os títulos exatos com que ele os abre. O que vem antes do primeiro deles (dados do
#: caso + CONHECIMENTO DO FLUXO + ORIENTAÇÃO DO CORREDOR) é estável no acionamento e vai para o
#: prefixo. Se o produto mudar um título, nada se perde: o corte só cai mais cedo (a tela sempre casa).
_BLOCOS_VARIAVEIS_DO_PRODUTO = (
    "\n\n🔴 ONDE O AUTOMÁTICO EMPACOU", "\n\n🟢 ESTA TELA APENAS CONDUZ",
    "\n\n🔴 A SUA ÚLTIMA RESPOSTA FOI RECUSADA", "\n\nOPÇÕES NUMERADAS DO MENU",
    "\nMensagens anteriores da seguradora ainda sem resposta", "\n\nO QUE JÁ FOI DITO NESTA CONVERSA",
    "\n\nTela da seguradora agora",
)


def _cortar_o_produto(user: str) -> Tuple[str, str]:
    """O `user` do produto → (o que é estável no acionamento, o que muda a cada tela). Nada se perde:
    as duas partes somadas são o texto original, byte a byte."""
    pos = [i for i in (user.find(m) for m in _BLOCOS_VARIAVEIS_DO_PRODUTO) if i >= 0]
    i = min(pos) if pos else 0
    return user[:i], user[i:]


def compor_mensagens(sessao: Dict[str, Any], tela: str, *, gatilho: str = "cerebro",
                     conversa: Optional[List[str]] = None, mapa: str = "",
                     memoria: Optional[List[str]] = None) -> Dict[str, str]:
    """O prompt do destravador: o do PRODUTO + o que o destravador ACRESCENTA. Puro (sem banco).

    A bancada (F2) importa ESTA função — o prompt que ela mede é, byte a byte, o que o produto roda.

    A ORDEM é a do cache de prompt (F1c): do que nunca muda ao que muda a cada tela —
      system = INSTRUCAO_DO_DESTRAVADOR (fixa) + o system do produto (seguradora, serviço, freio)
      user   = dados do caso + conhecimento do fluxo (produto) + o caso em palavras, a memória, a
               conversa com o segurado ║ _MARCA_DO_VARIAVEL ║ o porquê, as falas antigas, o mapa,
               as rotas irmãs, o resto do produto e a tela.
    """
    from app.services.insurer_dispatch_service import build_human_phase_messages, get_playbook

    msgs = dict(build_human_phase_messages(sessao, tela))
    playbook = get_playbook(str(sessao.get("playbook_ref") or "")) or {}
    msgs["system"] = INSTRUCAO_DO_DESTRAVADOR + msgs["system"]
    estavel, variavel = _cortar_o_produto(msgs["user"])
    fixo = "\n\nO CASO, EM PALAVRAS: " + _caso_em_palavras(sessao, playbook)
    if memoria:
        fixo += "\n\nO QUE A CORRETORA JÁ ENSINOU:\n" + "\n".join(memoria)
    conversa = list(conversa or [])
    fixo += ("\n\nA CONVERSA COM O SEGURADO (as últimas mensagens, a mais antiga primeiro):\n"
             + "\n".join(conversa) if conversa
             else "\n\nA CONVERSA COM O SEGURADO: (não disponível neste caso)")
    muda = f"{_MARCA_DO_VARIAVEL}{_gatilho_legivel(gatilho)}."
    antes = _telas_antes(sessao)
    if antes:
        muda += "\n\nANTES DISSO NA CONVERSA COM A SEGURADORA (as falas mais antigas):\n" + antes
    if mapa:
        muda += ("\n\nTELAS PARECIDAS QUE JÁ VIMOS NESTA SEGURADORA (o mapa da URA, recortado):\n"
                 + mapa)
    irmas = _rotas_irmas(playbook, sessao, tela)
    if irmas:
        muda += ("\n\nROTAS IRMÃS (passos conhecidos parecidos com esta tela, em outros corredores "
                 "desta seguradora ou deste serviço em outras):\n" + irmas)
    variavel = variavel.replace("\n\nSua resposta:", "\n\nSua resposta (o JSON):")
    msgs["user"] = estavel + fixo + muda + variavel
    return msgs


def mensagens_para_o_provedor(provedor: str, mensagens: list) -> list:
    """As mensagens do destravador no formato de QUEM VAI RESPONDER — hoje, como vieram, para TODO
    provedor: nenhum `cache_control` (F5a, pelo número; a F1c tinha posto três pontos na Anthropic).

    📊 Bancada real de 30/09 (`tests/corpus/bancada/RESULTADOS/destravador_*.json`, soma de
    `tokens.in / cache_read / cache_write` dos braços anthropic): o reserva decidindo, 44 chamadas —
    entrada 330.926, lido 79.985 (×0,10), gravado 200.621 (×1,25) → 309.095 tokens-equivalentes
    contra 330.926 sem cache (−6,6 %, na ordem MAIS favorável: casos do mesmo corredor em sequência);
    o mesmo como 2ª opinião, 3 chamadas: +12,4 %; o maior da Anthropic, 11: +7,5 %. O ponto ③ (parte estável do `user`,
    8–10 mil tokens) só é lido quando o MESMO acionamento chama de novo em 5 min; o ① sozinho
    (📊 2.271 caracteres ≈ 570 tokens) fica abaixo do mínimo cacheável. Em produção a Anthropic só
    responde como RESERVA do destravador (a 2ª opinião não é chamada enquanto o DEDUZIR está sem
    calibração) e há poucas travas por acionamento → o prêmio de 25 % na gravação não se paga.
    A ORDEM de `compor_mensagens` (o fixo primeiro) fica: é de graça e é o que o cache automático de
    prefixo da OpenAI usa. Para religar: medir de novo com tráfego real e pôr o ponto que se paga."""
    return list(mensagens)


def texto_da_mensagem(m: Any) -> str:
    """O TEXTO de uma mensagem, em string ou em blocos (para comparar o prompt de dois provedores)."""
    c = getattr(m, "content", m)
    if isinstance(c, list):
        return "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in c)
    return str(c or "")


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


def opcao_que_nao_vai_ao_segurado(rotulo: Any, *, com_custo: bool = False) -> bool:
    """A opção é NAVEGAÇÃO ou IRREVERSÍVEL — nunca é oferecida ao segurado, e a resposta dele que
    a escolher nunca volta à URA (X1). `com_custo=True` é a pergunta do CUSTO (D1: lá o segurado
    decide o custo, vendo o valor); fora dela, a opção que fala de dinheiro também sai."""
    from app.services import insurer_dispatch_service as IDS

    r = IDS._norm_text(str(rotulo or ""))
    if not r.strip() or IDS.navega_para_o_segurado(rotulo):
        return bool(r.strip())
    if (_RX_OPCAO_QUE_NAO_VAI_AO_SEGURADO.search(r) or _RX_OPCAO_NOVO_ATENDIMENTO.search(_n(r))
            or _RX_TROCA_TITULAR.search(_n(r))):
        return True
    return not com_custo and bool(IDS._RX_DINHEIRO_NA_TELA.search(r) or _RX_CUSTO_DA_TELA_EXTRA.search(r))


def opcoes_de_conteudo(tela: str, *, com_custo: bool = False) -> List[List[str]]:
    """As opções de CONTEÚDO da tela ([[tecla, rótulo], …]), sem navegação — o MESMO critério da
    pergunta do `sem_chute` (`sem_chute_ao_segurado`): numerada guarda o dígito da tela; lista de
    botões é renumerada 1..n (a volta casa pelo rótulo). "Nenhuma das anteriores" fica: é resposta.
    Conserto X1: nem o IRREVERSÍVEL (`opcao_que_nao_vai_ao_segurado`)."""
    from app.services import insurer_dispatch_service as IDS

    num = IDS.opcoes_numeradas(str(tela or ""))
    if num:
        return [[str(d), str(r)] for d, r in num
                if not opcao_que_nao_vai_ao_segurado(r, com_custo=com_custo)]
    conteudo = [str(r) for r in IDS._rotulos_da_tela(str(tela or ""))
                if not opcao_que_nao_vai_ao_segurado(r, com_custo=com_custo)]
    return [[str(i), r] for i, r in enumerate(conteudo, 1)]


def _tela_tem_opcoes(tela: str) -> bool:
    from app.services import insurer_dispatch_service as IDS

    return bool(IDS.opcoes_numeradas(str(tela or "")) or IDS._rotulos_da_tela(str(tela or "")))


# ── W2b — a PERGUNTA da tela, sem o menu ─────────────────────────────────────────────────────────
#: constante_justificada (o teto): 📊 01/10, `_pergunta_da_tela` sobre as 56 telas que chegam ao
#: PERGUNTAR no `casos_d.jsonl`: a mais longa tem 95 caracteres, nenhuma cortada; sobre as 1.555 telas
#: com pergunta do acervo `telas_reais/`: 7 cortadas (parágrafos de aviso, não perguntas). O corte é
#: por PALAVRA, com "…" — nunca no meio dela.
_TETO_DA_PERGUNTA = 160
#: Onde uma frase acaba: pontuação + espaço, ou um emoji ("Aguarde um momento 🙂 Por favor, …").
#: constante_justificada: o ":" acaba a frase porque é ele que separa o comando das opções quando o
#: menu chega numa linha só ("Escolha a opção que melhor te atende: Para você …" — o defeito W2b).
_RX_FIM_DE_FRASE = re.compile("(?<=[.!?:…])\\s+|\\s*[\U0001F300-\U0001FAFF☀-➿⬀-⯿️]+\\s*")
#: constante_justificada: o itálico do WhatsApp (`_…_`) é a NOTA ao lado ("_Lembrando que se você está em uma Rodovia…_",
#: "_Aguarde um instante…_"): vira frase própria e nunca é a pergunta. 📊 bradesco-007/008/009 do
#: `casos_d.jsonl`: sem isso, a nota era escolhida no lugar de "…via local ou rodovia?".
_RX_ITALICO = re.compile(r"(?:(?<=\s)|^)_|_(?=\s|$|[.!?:,;])")
#: constante_justificada: a marca de MENU dentro de um texto corrido: "Botão 1:", "1 - ", "*2* - " e a navegação com
#: maiúscula no meio da linha (" Voltar"). Case-sensitive de propósito: "digite *voltar*" é prosa.
_RX_MARCA_DE_MENU = re.compile(
    r"(?:^|\s)(?:Bot[ãa]o\s*\d{1,2}\s*:|\d{1,2}\s*[-–)]\s|(?:Voltar|Sair|Menu|Encerrar)(?=\s|$|[.!]))")
#: constante_justificada: duas frases coladas sem pontuação ("…preciso que informe Qual o horário…", "…WhatsApp Web”
#: Selecione abaixo…"): a pergunta começa na ÚLTIMA palavra de pergunta/comando com maiúscula.
#: Só estas palavras — maiúscula solta no meio da frase é nome próprio ("qual Seguradora").
_RX_INICIO_DE_PERGUNTA = re.compile(
    r"(?<=\S)\s+(?=(?:Qual|Quais|Quanto|Quantos|Quantas|Quando|Onde|Como|Informe|Digite|Selecione|"
    r"Escolha|Confirme|Me informe|Me diga|Por favor)\b)")
#: constante_justificada: a frase-COMANDO (além de `_MARCA_DE_PERGUNTA`, que já tem informe/digite/qual/envie/me diga):
#: os verbos de escolha que os menus medidos usam ("Escolha a opção…", "Selecione abaixo…",
#: "confirme o veículo…", "preciso que selecione…").
_RX_FRASE_COMANDO = re.compile(r"\b(?:escolha|selecione|seleciona|confirme|indique|responda)\b")
#: constante_justificada: NÃO é a pergunta — a navegação ("Se quiser mudar de opção, digite voltar",
#: "Clique no botão abaixo…"), a condição SEM "?" ("Se não houver, é só digitar não tem") e a frase
#: que é SÓ saudação ("Olá, tudo bem?"). 📊 yelum-065/azul-049 do `casos_d.jsonl` e os menus da tokio:
#: com elas, a pergunta copiada era a saudação, a condição ou o "clique". ⚠️ "Se for necessário,
#: posso te ligar…?" e "Oi, você ainda está comigo?" SÃO perguntas (porto/azul/tokio no acervo).
_RX_FRASE_QUE_NAO_E_PERGUNTA = re.compile(
    r"^(?:se|caso)\b[^?]*$|^(?:clique|clica|toque)\b|"
    r"^(?:ola|oi|bom dia|boa tarde|boa noite)\W*$|"
    r"^(?:(?:ola|oi|bom dia|boa tarde|boa noite)\b[^?]{0,40}?)?\btudo (?:bem|certo|bom)\W*$|"
    r"\b(?:digite|digita|digitar|envie|escreva|responda|clique)\b.{0,15}\b(?:voltar|sair|menu|encerrar|inicio)\b")


def _pergunta_da_tela(tela: str) -> str:
    """W2b — a PERGUNTA que a tela faz, SEM o menu: a frase com "?" (a última antes da 1ª opção,
    que não seja saudação nem nota), senão a frase-COMANDO antes da 1ª opção ("Escolha a opção que
    melhor te atende", "Selecione…", "Informe…", "Digite…"). Sem as opções, sem navegação, sem
    markdown, inteira (≤ `_TETO_DA_PERGUNTA`, cortada por palavra). As OPÇÕES vão SEPARADAS
    (`opcoes_de_conteudo` → o roteador as numera, uma por linha).

    🔴 As linhas de opção saem pelos PARSERS do produto (`opcoes_numeradas`, `_rotulos_da_tela` — o
    `parse_options` do Atlas), nunca por regex nova (§9.4). Na tela que chega numa linha só, o fim
    de frase (":" "?" "." emoji) e a marca de menu ("Botão 1:", "1 - ", " Voltar") fazem o corte.
    📊 O defeito: `"Escolha a opção que melhor te atende: Para você Seguros e serviços… Voltar
    Escolha a opção… Segur"` — o menu inteiro, cortado aos 200."""
    from app.services import insurer_dispatch_service as IDS

    texto = str(tela or "")
    rotulos = {IDS._norm_text(str(r)).strip(" .*:") for r in IDS._rotulos_da_tela(texto)}
    rotulos |= {IDS._norm_text(str(r)).strip(" .*:") for _d, r in IDS.opcoes_numeradas(texto)}
    rotulos.discard("")

    def marca(frase: str) -> bool:
        n = IDS._norm_text(frase)
        return bool(re.search(IDS._MARCA_DE_PERGUNTA, n) or _RX_FRASE_COMANDO.search(n))

    def linha_de_opcao(linha: str) -> bool:
        crua = linha.replace("*", "").strip()
        if re.match(r"^(?:Bot[ãa]o\s*\d{1,2}\s*:|\d{1,2}\s*[-–.)]\s)", crua):
            return True
        if "?" in crua or marca(crua):
            return False
        ln = IDS._norm_text(crua).strip(" .*:")
        return any(r and r in ln and len(ln) <= len(r) + 14 for r in rotulos)

    def e_menu(frase: str) -> bool:
        """Dois ou mais rótulos do menu que ocupam a maior parte da frase: é o menu corrido, não
        uma pergunta que os cita ("…numa via local ou rodovia?", "É reparo ou instalação?")."""
        if "?" in frase:
            return False
        n = IDS._norm_text(frase).strip(" .*:")
        achados = [r for r in rotulos if len(r) >= 3 and re.search(rf"(?<!\w){re.escape(r)}(?!\w)", n)]
        return len(achados) >= 2 and sum(map(len, achados)) * 2 >= len(n)

    # ① as frases ANTES da 1ª opção (o menu e o que vem depois dele — repetição, erro — ficam fora)
    frases: List[Tuple[str, bool]] = []          # (frase, é nota em itálico)
    acabou = False
    for linha in texto.replace("*", "").splitlines():
        if not linha.strip():
            continue
        if linha_de_opcao(linha):
            break
        trechos = _RX_ITALICO.split(linha)
        for i, trecho in enumerate(trechos):
            italico = i % 2 == 1 and i < len(trechos) - 1   # `_` sem par (um link) não é nota
            for pedaco in _RX_FIM_DE_FRASE.split(trecho):
                m = _RX_MARCA_DE_MENU.search(pedaco)
                if m:   # o menu começou no meio do texto corrido: fica só o que veio antes dele
                    pedaco, acabou = pedaco[:m.start()], True
                p = " ".join(pedaco.split()).strip(" _")
                if p and p not in [f for f, _i in frases]:
                    frases.append((p, italico))
                if acabou:
                    break
            if acabou:
                break
        if acabou:
            break
    # ② a frase que é a PERGUNTA — nunca saudação, condição, nota em itálico nem o menu corrido
    boas = [f for f, italico in frases
            if not italico and not e_menu(f)
            and not _RX_FRASE_QUE_NAO_E_PERGUNTA.search(IDS._norm_text(f).strip(" .:"))]
    perguntas = [f for f in boas if "?" in f]
    comandos = [f for f in boas if marca(f)]
    abre_lista = [f for f in boas if f.endswith(":")]   # "Os horários que eu tenho são:"
    if perguntas:
        q = perguntas[-1]
    elif comandos:
        # com o menu reconhecido pelo parser, as frases já pararam na 1ª opção: a última é a mais
        # perto dela. Sem ele (o menu corrido numa linha só), o comando que ABRE a tela vem antes.
        q = comandos[0] if not rotulos and "\n" not in texto.strip() else comandos[-1]
    elif abre_lista:
        q = abre_lista[-1]
    else:
        # sem pergunta nem comando: a última frase — salvo o menu corrido que o parser não leu
        # (o que sobrou ali é rótulo, não pergunta; melhor a frase do produto que um rótulo).
        corrido = not rotulos and (acabou or len(frases) > 1) and "\n" not in texto.strip()
        q = boas[-1] if boas and not corrido else ""
    q = _RX_INICIO_DE_PERGUNTA.split(q)[-1] if marca(q) else q
    q = q.rstrip(" :;,-–")
    if len(q) > _TETO_DA_PERGUNTA:
        q = q[:_TETO_DA_PERGUNTA].rsplit(" ", 1)[0].rstrip(" ,;:-–") + "…"
    return q


def _pergunta_ao_segurado(tela: str, opcoes: List[List[str]]) -> str:
    q = _pergunta_da_tela(tela)
    if not q:
        return ("A seguradora precisa de uma resposta sua para seguir — "
                + ("qual destas opções vale para você?" if opcoes else "pode me dizer o que ela pediu?"))
    if opcoes:
        return f"A seguradora está perguntando: “{q}” — qual destas opções vale para você?"
    return f"A seguradora está perguntando: “{q}” — pode me responder?"


# ── X1 · ajuste W (P-N1) — o texto do MODELO nunca vai ao segurado ──────────────────────────────
#: 🔴 Não há mais conferente do texto do modelo: a pergunta ao segurado é SEMPRE a composta pelo
#: código (`_pergunta_composta`). constante_justificada (por que tirar o conferente, e não apertá-lo):
#: 📊 laudo de confirmação da SPEC-123, P-N1 — o conferente (`conferir_texto_ao_segurado`) deixava
#: passar "Ele esta no local agora?" (3ª pessoa), "O veiculo do segurado esta na garagem?" e
#: "Clique em Continuar para seguir?" (navegação), e não sabia conferir se a pergunta era a da
#: tela. Cada aperto (2ª pessoa, verbos de navegação, relação com a tela) é mais uma régua que
#: erra em silêncio; a pergunta da TELA e a frase do produto para o slot já dizem o que a
#: seguradora quer saber. O que o modelo quis perguntar fica só no DIÁRIO ("o modelo propôs").


def _slots_do_passo(sessao: Dict[str, Any], tela: str,
                    playbook: Optional[Dict[str, Any]] = None) -> List[str]:
    """Os slots que o PASSO DO CORREDOR desta tela declara (`match_ura_step`: `requires` + os
    `{slot}` da resposta). É o único slot que pode responder uma OPÇÃO como "dado do caso" (X2)."""
    from app.services import corridor_playbooks as CP
    from app.services.insurer_dispatch_service import get_playbook

    pb = playbook if playbook is not None else (get_playbook(str(sessao.get("playbook_ref") or "")) or {})
    if not pb or not str(tela or "").strip():
        return []
    try:
        passo = CP.match_ura_step(pb, str(tela), str(sessao.get("subservice") or "")) or {}
    except Exception:  # noqa: BLE001 — sem passo, nenhum slot declarado (o caminho mais seguro)
        return []
    if passo.get("noop"):
        return []
    saida: List[str] = []
    for s in list(passo.get("requires") or []) + re.findall(r"\{(\w+)\}", str(passo.get("reply") or "")):
        if str(s) not in saida:
            saida.append(str(s))
    return saida


def _pergunta_composta(tela: str, conteudo: List[List[str]], sessao: Dict[str, Any]) -> str:
    """X1 · ajuste W — a pergunta ao segurado, SEMPRE COMPOSTA PELO CÓDIGO: a frase do produto para o
    slot do passo (`como_perguntar_ao_segurado`, 2ª pessoa) ou a pergunta da PRÓPRIA tela (+ as
    opções de conteúdo filtradas, que o roteador acrescenta). ⛔ O texto do modelo NÃO entra aqui —
    nem limpo (P-N1): ele vai só ao diário, como "o modelo propôs" (`_registrar`)."""
    from app.services import corridor_playbooks as CP

    q = _pergunta_da_tela(tela)
    molde = ""
    for s in _slots_do_passo(sessao, tela):
        try:
            molde = CP.como_perguntar_ao_segurado(s, str(sessao.get("playbook_ref") or "")) or ""
        except Exception:  # noqa: BLE001
            molde = ""
        if molde:
            break
    if molde and not conteudo:
        if not q:
            return f"Me diga {molde}, por favor."
        return f"Me diga {molde}, por favor. (a pergunta da seguradora: “{q}”)"
    return _pergunta_ao_segurado(tela, conteudo)


def _texto_sem_as_opcoes(tela: str) -> str:
    """A tela sem as LINHAS de opção — "Informações sobre pagamento" é uma opção do menu da Porto,
    não um custo que a tela anuncia."""
    from app.services import insurer_dispatch_service as IDS

    rotulos = {IDS._norm_text(str(r)).strip(" .*:") for r in IDS._rotulos_da_tela(str(tela or ""))}
    rotulos |= {IDS._norm_text(str(r)).strip(" .*:") for _d, r in IDS.opcoes_numeradas(str(tela or ""))}
    rotulos.discard("")
    fora = []
    for linha in str(tela or "").splitlines():
        ln = IDS._norm_text(linha).strip()
        if any(r and r in ln and len(ln) <= len(r) + 14 for r in rotulos):
            continue
        fora.append(linha)
    return "\n".join(fora)


def _tela_anuncia_custo(tela: str) -> bool:
    """A tela (sem as linhas de opção) fala de dinheiro — pelo regex do PRODUTO ou pelo vocabulário
    que passou (`_RX_CUSTO_DA_TELA_EXTRA`). Sem exigir marca de pergunta: 📊 red team C3–C5, o custo
    sem "?" e um "Continuar" que o aceita."""
    from app.services import insurer_dispatch_service as IDS

    t = IDS._norm_text(_texto_sem_as_opcoes(tela))
    return bool(IDS._RX_DINHEIRO_NA_TELA.search(t) or _RX_CUSTO_DA_TELA_EXTRA.search(t))


def _pergunta_do_custo(tela: str) -> str:
    """A pergunta ao segurado que MOSTRA o custo da tela — ele decide (D1)."""
    from app.services import insurer_dispatch_service as IDS

    linhas = [" ".join(l.replace("*", "").split()) for l in str(tela or "").splitlines()]
    dinheiro = [l for l in linhas if l and (IDS._RX_DINHEIRO_NA_TELA.search(IDS._norm_text(l))
                                             or _RX_CUSTO_DA_TELA_EXTRA.search(IDS._norm_text(l)))]
    trecho = " / ".join(dinheiro)[:300] or _pergunta_da_tela(tela)
    return (f"A seguradora informou algo que envolve custo ou pagamento e precisa da sua decisão: "
            f"“{trecho}”. Como você quer seguir?")


def _rotulo_escolhido(tela: str, valor: str) -> str:
    from app.services.acao_do_cerebro import rotulo_de

    return rotulo_de(tela, valor)[1]


#: constante_justificada: um slot MASCARADO (`{ENDERECO}`, `{CPF}` — o corpus da bancada e o rastro
#: higienizado). Normalizado, `{ENDERECO}` vira a palavra "endereco" — e qualquer rótulo com essa
#: palavra ("Digitar endereço") passaria por dado do caso. Máscara só casa com ela mesma, crua.
_RX_MASCARA = re.compile(r"^\{[A-Z_]+\}$")
#: constante_justificada: o menor pedaço que conta como o MESMO dado quando um contém o outro
#: (o segurado escreveu "Rua X 123", a tela pede "Rua X 123 fundos"). 6 caracteres E um dígito OU
#: duas palavras: 📊 os dados de verdade são todos maiores (placa 7, CEP 8, CPF 11, endereço com
#: número); as palavras soltas do caso que mais aparecem em rótulo ("casa", "centro", "carro",
#: "sim") são menores ou de uma palavra só — e por igualdade continuam valendo.
_MINIMO_DO_PEDACO = 6


def _pedaco_do_mesmo_dado(curto: str, longo: str) -> bool:
    """`curto` é uma sequência de PALAVRAS INTEIRAS de `longo`, e grande o bastante para ser dado."""
    if len(curto) < _MINIMO_DO_PEDACO or not (re.search(r"\d", curto) or " " in curto):
        return False
    return f" {curto} " in f" {longo} "


def _compacto(s: Any) -> str:
    """Normalizado e SEM espaço: "111.222.333-44" = "11122233344", "ABC-1D23" = "abc1d23"."""
    return re.sub(r"\s+", "", _n(s))


def _slots_do_tipo_da_tela(tela: str) -> List[str]:
    """Os slots do TIPO de dado que a tela pede, pela tabela do PRODUTO (`_PERGUNTAS_DE_DADO`)."""
    from app.services import insurer_dispatch_service as IDS

    nt = IDS._norm_text(str(tela or ""))
    saida: List[str] = []
    for _campo, rx, slots in IDS._PERGUNTAS_DE_DADO:
        if re.search(rx, nt, re.IGNORECASE):
            saida += [str(s) for s in slots if str(s) not in saida]
    return saida


def _e_dado_do_caso(valor: str, sessao: Dict[str, Any], tela: str = "") -> bool:
    """O valor É um dado do caso? Os slots (sem o que o SISTEMA preencheu — `slots_padrao`).

    F1c — 📊 antes casava por SUBSTRING ("Digitar endereço" passava por `{ENDERECO}`).
    🔴 CONSERTO X2 (juiz B2 · red team B1/B2) — 📊 "Sim" igual a QUALQUER slot sim/não
    (`pessoa_no_local`, `risco_confirmado_sem_fumaca`) respondia "Sim" sozinho a qualquer tela
    sim/não (60 de 74 telas reais com "Sim" e palavra sensível; `rt-scripts/pol_corpus.py`), e o
    pedaço de endereço passava. Agora:
      · rótulo de NAVEGAÇÃO da tela nunca é dado;
      · escolher uma OPÇÃO da tela só é dado quando o slot é o que o PASSO DO CORREDOR desta tela
        declara (`_slots_do_passo`) e o valor dele CASA a opção — senão é DEDUZIR;
      · texto livre: IGUAL (normalizado, sem espaço) a um slot INTEIRO do tipo que a tela pede
        (`_slots_do_tipo_da_tela` + o passo); tela sem tipo conhecido: igual a um slot, nunca um
        sim/não genérico (`_RX_SIM_NAO`); nunca "contido" (o pedaço saiu);
      · máscara (`{ENDERECO}`) só casa com ela mesma, crua."""
    v = _n(valor)
    if len(v) < 2 and not v.isdigit():
        return False
    tem_tela = bool(str(tela or "").strip())
    rot = _rotulo_escolhido(tela, valor) if tem_tela else ""
    from app.services.insurer_dispatch_service import rotulo_e_de_navegacao

    if rot and rotulo_e_de_navegacao(rot):
        return False
    padrao = set(sessao.get("slots_padrao") or ())
    slots = {str(k): x for k, x in (sessao.get("slots") or {}).items() if k not in padrao}
    do_passo = [s for s in (_slots_do_passo(sessao, tela) if tem_tela else []) if s not in padrao]
    if rot:
        # OPÇÃO da tela: só o slot do PASSO, e só se o valor dele casa a opção escolhida
        alvos = {_compacto(rot), _compacto(valor)}
        return any(_compacto(slots.get(s)) in alvos for s in do_passo
                   if isinstance(slots.get(s), (str, int)) and not isinstance(slots.get(s), bool)
                   and _compacto(slots.get(s)))
    if len(v) < 2:
        return False
    tipo = (_slots_do_tipo_da_tela(tela) if tem_tela else []) + do_passo
    if tipo:
        fontes = [(k, slots.get(k)) for k in tipo if k in slots]
    else:
        fontes = [(k, x) for k, x in slots.items() if not str(k).endswith("_opcao")]
        fontes += list((sessao.get("captured") or {}).items())
        if _RX_SIM_NAO.match(v):
            return False        # sim/não genérico só vale como o slot DECLARADO pela tela
    cv = _compacto(valor)
    for _k, x in fontes:
        if not isinstance(x, (str, int)) or isinstance(x, bool):
            continue
        cru = str(x).strip()
        if _RX_MASCARA.match(cru):
            if str(valor or "").strip() == cru:
                return True
            continue
        if cv and cv == _compacto(cru):
            return True
    return False


#: constante_justificada: a OPÇÃO que abre um SEGUNDO trabalho (normalizada, sem acento). 📊 As
#: redações reais (`tests/corpus/telas_reais`): "Abrir novo atendimento" / "Abrir um novo
#: atendimento" (allianz), "Não, abrir novo serviço" (allianz-auto), "Novo serviço" / "Novo
#: atendimento" (porto, azul, yelum), "Pedir outro serviço" (hdi). ⚠️ NÃO é o
#: `corridor_playbooks._RX_COMECA_TRABALHO_NOVO`: aquele responde "é navegação?" (errar para o
#: lado do "não" lá só custa a régua do DEDUZIR) e casa `abrir` sozinho e `outros serviços` —
#: 📊 F1c: a categoria "*3 -* Outros serviços" do 1º menu da Allianz (des-D-escolhe_servico-
#: allianz-025, nota 92 + 2ª opinião concordando) ia a uma PESSOA, e "Abrir a porta" (o serviço
#: de chaveiro da allianz-residencial) também iria. (constante_justificada: acima.)
_RX_OPCAO_NOVO_ATENDIMENTO = re.compile(
    r"\b(?:abrir|iniciar|pedir|solicitar|seguir para)\s+(?:um |uma |o |a )?(?:nov[oa]|outr[oa])\b|"
    r"\bnov[oa]s? (?:atendimento|servico|solicitacao|chamado|pedido|assistencia)|"
    r"\boutr[oa] (?:atendimento|servico|solicitacao|chamado|pedido|assistencia)\b")
#: constante_justificada: "outros serviços" (PLURAL) é CATEGORIA de serviço no 1º menu (allianz,
#: mapfre "2ª via de apólice e outros serviços") — e só abre trabalho novo quando a TELA mostra que
#: já há um: 📊 "Identifiquei que temos uma solicitação de serviço feita", "A solicitação de GUINCHO
#: está concluída", "Seu atendimento foi cancelado", "Posso te ajudar com algo mais?".
_RX_OPCAO_OUTROS_SERVICOS = re.compile(r"\boutr[oa]s (?:servicos|atendimentos|assistencias)\b")
_RX_TELA_COM_TRABALHO_EM_CURSO = re.compile(
    r"conclu[ií]d|solicitacao (?:de servico )?feita|identifiquei que|ja (?:possui|tem|existe)|"
    r"em andamento|algo mais|foi (?:cancelad|agendad|reagendad|registrad)|nao foi reagendad")
#: constante_justificada: a TELA que pergunta se abre OUTRO trabalho — o "Sim" executaria.
#: 📊 hdi-auto: "Gostaria de solicitar algum outro serviço? Botão 1: Sim".
_RX_TELA_PEDE_OUTRO = re.compile(
    r"(?:solicitar|pedir|abrir|iniciar)\s+(?:algum |um |uma )?(?:outr[oa]|nov[oa]) "
    r"(?:servico|atendimento|solicitacao|chamado|pedido|assistencia)")


def _abre_novo_atendimento(alvo: str, norm_tela: str, afirma: bool, tem_pergunta: bool,
                           sessao: Dict[str, Any]) -> bool:
    """A resposta abriria um SEGUNDO atendimento (o NUNCA `novo_atendimento`)?"""
    if _RX_OPCAO_NOVO_ATENDIMENTO.search(alvo):
        return True
    em_curso = bool(_RX_TELA_COM_TRABALHO_EM_CURSO.search(norm_tela)) or any(
        "protocol" in str(k).lower() for k in (sessao.get("captured") or {}))
    if _RX_OPCAO_OUTROS_SERVICOS.search(alvo) and em_curso:
        return True
    return bool(afirma and tem_pergunta and _RX_TELA_PEDE_OUTRO.search(norm_tela))


def _digitos_do_caso(sessao: Dict[str, Any]) -> str:
    vals = list((sessao.get("slots") or {}).values()) + list((sessao.get("captured") or {}).values())
    return " ".join(re.sub(r"\D", "", str(x)) for x in vals if x not in (None, ""))


def _tokens_de_digitos(valores: List[Any]) -> set:
    """Os NÚMEROS INTEIROS dos valores: cada sequência de dígitos (separadores `.-/ ` juntados) e o
    valor só-dígitos inteiro. 🔴 X2 (red team B2): "333" e "2233" estão DENTRO dos dígitos do CPF
    11122233344 — e passavam por número do caso. Número do caso é um número INTEIRO do caso."""
    saida: set = set()
    for x in valores:
        if x in (None, "") or isinstance(x, bool) or not isinstance(x, (str, int)):
            continue
        s = str(x)
        saida.update(re.findall(r"\d+", re.sub(r"(?<=\d)[.\-/ ](?=\d)", "", s)))
        saida.update(re.findall(r"\d+", s))
        so = re.sub(r"\D", "", s)
        if so:
            saida.add(so)
            if so.startswith("55") and len(so) >= 12:
                saida.add(so[2:])      # o telefone com e sem o 55 do país
    return saida


def _numero_inventado(valor: str, sessao: Dict[str, Any]) -> bool:
    """O valor traz um número (≥ 3 dígitos) que não é um número INTEIRO do caso?"""
    do_caso = _tokens_de_digitos(list((sessao.get("slots") or {}).values())
                                 + list((sessao.get("captured") or {}).values()))
    return any(r not in do_caso for r in re.findall(r"\d{3,}", re.sub(r"[.\-/ ]", "", str(valor or ""))))


def _caso_completo(sessao: Dict[str, Any], playbook: Dict[str, Any]) -> bool:
    """Todo slot que o corredor exige para este serviço está preenchido (pelo segurado, não pelo
    padrão do sistema)."""
    slots = sessao.get("slots") or {}
    padrao = set(sessao.get("slots_padrao") or ())
    pede = [str(x) for x in (playbook.get("required_slots") or [])]
    sub = ((playbook.get("subservices") or {}).get(str(sessao.get("subservice") or "")) or {})
    pede += [str(x) for x in (sub.get("required_slots") or [])]
    return bool(pede) and all(str(slots.get(x) or "").strip() and x not in padrao for x in pede)


def _nunca_da_tela(norm_tela: str, tem_pergunta: bool, sessao: Dict[str, Any],
                   playbook: Dict[str, Any], gatilho: str) -> str:
    """A TELA cuja resposta AFIRMATIVA é irreversível → a chave do NUNCA, ou "". Usada quando a
    resposta afirma (RESPONDER) e quando se pensa em perguntar ao segurado (a pergunta seria a
    mesma decisão, só que terceirizada a ele sem ver o todo) — X1/X2."""
    if _RX_TELA_ABRE_SINISTRO.search(norm_tela) or _RX_TELA_ABRE_SINISTRO_EXTRA.search(norm_tela):
        return "abrir_sinistro"
    if tem_pergunta and (_RX_CANCELA.search(norm_tela) or _RX_TELA_CANCELA_EXTRA.search(norm_tela)):
        return "cancelar_pedido"
    if tem_pergunta and (_RX_TELA_PEDE_OUTRO.search(norm_tela) or _RX_TELA_NOVO_EXTRA.search(norm_tela)):
        return "novo_atendimento"
    if tem_pergunta and _RX_TROCA_TITULAR.search(norm_tela):
        return "trocar_titular"
    if _RX_TELA_CONFIRMA_ABERTURA.search(norm_tela) and (
            not _caso_completo(sessao, playbook)
            or str(gatilho or "").startswith("conferencia_divergente")):
        return "confirmar_abertura"
    return ""


def _provedor_diferente(segunda: Optional[dict], provedor: str) -> bool:
    p2 = str((segunda or {}).get("provedor") or "").strip().lower()
    p1 = str(provedor or "").strip().lower()
    return bool(p1) and bool(p2) and p1 != p2


# ═════════════════════════════════════════════════════════════════════════════
# O NÚCLEO DA POLÍTICA — canal-agnóstico (SPEC-124 D1: "a MESMA política nos dois canais; proibido copiar")
# ═════════════════════════════════════════════════════════════════════════════
# O que é IGUAL no WhatsApp e no portal mora aqui, uma vez: as chaves do NUNCA ligadas, e a régua
# classe × nota × limiar × 2ª opinião de OUTRO provedor × DEDUZIR desligado. O que muda de canal —
# o que é "navegação", "dado do caso", "opção" e "a mesma resposta" — entra como FUNÇÃO do canal.
PASSO_AGE = "age"
PASSO_REBAIXAR = "rebaixar"
PASSO_PRECISA_SEGUNDA = "precisa_segunda"


@dataclass
class Veredito:
    """O que a régua decidiu: AGIR com a `classe`, REBAIXAR (pergunta/pessoa, `porque`) ou buscar a 2ª opinião."""
    passo: str
    classe: str
    porque: str = ""


def chaves_ligadas(nunca=None) -> tuple:
    """As chaves do NUNCA SOZINHO que valem nesta decisão (`nunca` = a MUTAÇÃO do G2, nos dois canais)."""
    return NUNCA_SOZINHO if nunca is None else tuple(nunca)


def regua_do_nucleo(proposta: Proposta, *, limiar: int, provedor: str = "",
                    segunda_opiniao: Optional[dict] = None, pedir_segunda: bool = False,
                    e_navegacao, e_dado_do_caso, tem_opcoes: bool, valor_nas_opcoes,
                    mesma_resposta) -> Veredito:
    """A régua de uma RESPOSTA proposta (D1–D3 do Founder). Pura; as funções do canal são PREGUIÇOSAS
    (chamadas só quando a régua chega nelas, na mesma ordem de sempre).

    CONDUZIR que não é navegação e RESPONDER COM DADO que não é dado do caso viram DEDUZIR. DEDUZIR:
    desligado sem calibração (`DEDUZIR_AUTONOMO_CALIBRADO`); senão o valor tem de ser uma opção (se há
    opções), nota ≥ limiar, e a 2ª opinião de OUTRO provedor escolhendo a MESMA resposta.
    `segunda_opiniao["concordou"]` é gravado no próprio dict (o diário o lê)."""
    classe = proposta.classe
    if classe == "conduzir" and not e_navegacao():
        classe = "deduzir"            # não é navegação: é escolha — a régua do DEDUZIR
    if classe == "responder_com_dado" and not e_dado_do_caso():
        classe = "deduzir"            # não é dado do caso: é dedução
    if classe != "deduzir":
        return Veredito(PASSO_AGE, classe)
    if not DEDUZIR_AUTONOMO_CALIBRADO:
        # G3 sem calibração (ver a constante): nenhum DEDUZIR age sozinho, e a 2ª opinião não é paga
        return Veredito(PASSO_REBAIXAR, classe, "deduzir_sem_calibracao")
    if tem_opcoes and not valor_nas_opcoes():
        return Veredito(PASSO_REBAIXAR, classe, "valor_fora_das_opcoes")
    lim = _limiar_efetivo(limiar)
    if proposta.nota is None or proposta.nota < lim:
        return Veredito(PASSO_REBAIXAR, classe, "nota_abaixo_do_limiar")
    if segunda_opiniao is None:
        if pedir_segunda:
            return Veredito(PASSO_PRECISA_SEGUNDA, classe, "precisa_segunda_opiniao")
        return Veredito(PASSO_REBAIXAR, classe, "sem_segunda_opiniao")
    if not _provedor_diferente(segunda_opiniao, provedor):
        return Veredito(PASSO_REBAIXAR, classe, "segunda_opiniao_do_mesmo_provedor")
    concordou = (str(segunda_opiniao.get("acao") or "") == "RESPONDER"
                 and mesma_resposta(str(segunda_opiniao.get("valor") or "")))
    segunda_opiniao["concordou"] = bool(concordou)
    if not concordou:
        return Veredito(PASSO_REBAIXAR, classe, "segunda_opiniao_discordou")
    return Veredito(PASSO_AGE, classe)


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
    from app.services import insurer_dispatch_service as IDS

    ligadas = chaves_ligadas(nunca)
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

    def perguntar_composta(porque: str) -> Destravamento:
        """🔴 X1 — a pergunta que o MODELO quis fazer (ou a que a régua do DEDUZIR rebaixou) sai
        COMPOSTA PELO CÓDIGO (`_pergunta_composta`; o texto do modelo nunca entra). E não sai quando a tela é irreversível (a
        resposta do segurado executaria o NUNCA) nem quando o irreversível era TUDO o que a tela
        oferecia (sobrou nenhuma opção para ele escolher) — aí é uma pessoa."""
        if not ida:
            return pessoa(porque or "ida_e_volta_proibida")
        chave = _nunca_da_tela(norm_tela, tem_pergunta, sessao, playbook, g)
        if chave and chave in ligadas:
            return pessoa(chave)
        if _tela_tem_opcoes(tela) and not conteudo:
            # só navegação e/ou o irreversível: não sobrou NADA que o segurado possa escolher
            return pessoa("nenhuma_opcao_para_o_segurado")
        return perguntar(_pergunta_composta(tela, conteudo, sessao), porque)

    def rebaixar(porque: str) -> Destravamento:
        """DEDUZIR que não passou: pergunta ao segurado se a tela pergunta algo; senão pessoa."""
        if ida and (len(conteudo) >= 2 or re.search(IDS._MARCA_DE_PERGUNTA, IDS._norm_text(tela))):
            return perguntar_composta(porque)
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
    rot_da_resposta = _rotulo_escolhido(tela, valor) if p.acao == "RESPONDER" else ""
    afirma_a_tela = p.acao == "RESPONDER" and bool(
        _RX_AFIRMATIVO.search(_n(valor)) or _RX_AFIRMATIVO.search(_n(rot_da_resposta)))
    custo = "aceite_de_custo" in ligadas and (bool(
        AC.proibicao(tela, valor if p.acao == "RESPONDER" else "", playbook=playbook, session=sessao,
                     proibicoes=("aceite_de_custo",)))
        # X2 — 📊 red team C1–C6: o custo com outras palavras, ou sem "?", aceito por uma OPÇÃO
        # ("Sim", "Continuar", "Prosseguir") ou por uma afirmação.
        or (p.acao == "RESPONDER" and bool(rot_da_resposta or afirma_a_tela)
            and _tela_anuncia_custo(tela)))
    if custo:
        conteudo = opcoes_de_conteudo(tela, com_custo=True)   # D1: aqui o segurado decide o custo

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
        rot = rot_da_resposta
        alvo = _n(rot or valor)
        afirma = afirma_a_tela
        da_tela = _nunca_da_tela(norm_tela, tem_pergunta, sessao, playbook, g) if afirma else ""
        if "abrir_sinistro" in ligadas and (_RX_SINISTRO.search(alvo) or da_tela == "abrir_sinistro"):
            return pessoa("abrir_sinistro")
        if "cancelar_pedido" in ligadas and (
                _RX_CANCELA.search(alvo) or _RX_TELA_CANCELA_EXTRA.search(alvo)
                or da_tela == "cancelar_pedido"):
            return pessoa("cancelar_pedido")
        if "novo_atendimento" in ligadas and (
                _abre_novo_atendimento(alvo, norm_tela, afirma, tem_pergunta, sessao)
                or da_tela == "novo_atendimento"):
            return pessoa("novo_atendimento")
        if "trocar_titular" in ligadas and (_RX_TROCA_TITULAR.search(alvo) or da_tela == "trocar_titular"):
            return pessoa("trocar_titular")
        if "confirmar_abertura" in ligadas and da_tela == "confirmar_abertura":
            return pessoa("confirmar_abertura")
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
            if _numero_inventado(valor, sessao):     # X2: número INTEIRO do caso, nunca "contido"
                return pessoa("inventar_dado")
            # a tela pede um DADO (placa, CPF, telefone, endereço… — a tabela do PRODUTO,
            # `_PERGUNTAS_DE_DADO`) e o valor não é opção da tela nem dado do caso
            if not rot and not _e_dado_do_caso(valor, sessao, tela) and any(
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

    # ⑤ PERGUNTAR — 🔴 X1: o texto do modelo NUNCA vai cru ao segurado. A pergunta é composta
    #    pelo código (a da tela / a frase do produto para o slot do passo + as opções de conteúdo
    #    filtradas). Ajuste W (P-N1): o texto do modelo NUNCA entra — vai só ao diário.
    if p.acao == "PERGUNTAR_AO_SEGURADO":
        return perguntar_composta("")

    # ⑥ RESPONDER, por classe — o NÚCLEO canal-agnóstico (`regua_do_nucleo`, SPEC-124 D1). O que é
    #    "navegação", "dado do caso", "opção da tela" e "a mesma resposta" é do CANAL (aqui, a URA).
    def _e_navegacao() -> bool:
        rot = _rotulo_escolhido(tela, valor)
        eco = IDS.classe_da_tela(playbook, str(tela), slots=sessao.get("slots")).get("chave") == "eco_de_dado"
        # X2 (red team B2): no ECO só CONFIRMAR o eco do caso conduz ("Sim"/"Confirmar", uma opção
        # da tela). Texto livre ("Rua Inventada, 2233") ou "Não" num eco é escolha — DEDUZIR.
        eco_confirmado = eco and bool(rot) and bool(_RX_AFIRMATIVO.search(_n(rot)))
        return bool((rot and IDS.rotulo_e_de_navegacao(rot)) or eco_confirmado)

    v = regua_do_nucleo(
        p, limiar=lim, provedor=provedor, segunda_opiniao=segunda_opiniao, pedir_segunda=pedir_segunda,
        e_navegacao=_e_navegacao, e_dado_do_caso=lambda: _e_dado_do_caso(valor, sessao, tela),
        tem_opcoes=bool(conteudo), valor_nas_opcoes=lambda: bool(_rotulo_escolhido(tela, valor)),
        mesma_resposta=lambda outro: AC._mesma_resposta(tela, valor, outro))
    base["classe"] = v.classe
    if v.passo == PASSO_PRECISA_SEGUNDA:
        return Destravamento(acao="PESSOA", valor=valor, proibicao="precisa_segunda_opiniao", **base)
    if v.passo == PASSO_REBAIXAR:
        return rebaixar(v.porque)

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
    return await _sem_o_relogio_de_producao(llm).ainvoke(
        mensagens_para_o_provedor(resolvido.provider, mensagens))


@dataclass
class ModeloInjetado:
    """Um modelo de FORA do catálogo para `destravar(llm=…, llm_segunda=…)` — a bancada.

    `llm` é qualquer coisa com `ainvoke(mensagens)` (o braço da bancada, um dublê); `provedor` e
    `modelo` dizem QUEM responde (a 2ª opinião tem de ser de outro provedor — D3). As mensagens
    chegam no formato do provedor (`mensagens_para_o_provedor`), como em produção.
    ⛔ Produção NUNCA injeta: o modelo vem do catálogo (`llm_papeis`), nunca de fora."""
    llm: Any
    provedor: str
    modelo: str = ""


async def _chamar_injetado(m: "ModeloInjetado", mensagens: list):
    """(resposta, provedor, modelo) do modelo injetado — as mensagens no formato dele."""
    prov = str(m.provedor or "").strip().lower()
    r = await asyncio.wait_for(m.llm.ainvoke(mensagens_para_o_provedor(prov, mensagens)),
                               timeout=TETO_DA_CHAMADA_S)
    return r, prov, str(m.modelo or "")


async def _segunda_injetada(m: Optional["ModeloInjetado"], mensagens: list,
                            provedor: str) -> Tuple[Optional[dict], float]:
    """A 2ª opinião injetada. Sem ela, ou do MESMO provedor de quem decidiu → nenhuma (D3).
    ⛔ Com `llm` injetado, a 2ª opinião NUNCA cai no catálogo: a bancada não chama produção."""
    from app.agents.utils import extract_text_from_content

    p2 = str((m.provedor if m else "") or "").strip().lower()
    if m is None or not p2 or p2 == str(provedor or "").strip().lower():
        return None, 0.0
    try:
        r, prov, modelo = await _chamar_injetado(m, mensagens)
    except Exception as e:  # noqa: BLE001 — como no catálogo: 2ª opinião que falha = sem 2ª opinião
        logger.warning("[DESTRAVADOR] 2ª opinião injetada falhou: %s", type(e).__name__)
        return None, 0.0
    pr = ler_destravamento(extract_text_from_content(getattr(r, "content", None)) or "")
    return ({"provedor": prov, "modelo": modelo, "classe": pr.classe,
             "acao": pr.acao if pr.formato_ok else "PESSOA", "valor": pr.valor, "nota": pr.nota,
             "formato_ok": pr.formato_ok, "concordou": False}, _custo(r, modelo))


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
                                                          service_type=SERVICE_TYPE,
                                                          preparar=mensagens_para_o_provedor),
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
                r = await asyncio.wait_for(
                    llm.ainvoke(mensagens_para_o_provedor(cand.provider, mensagens)),
                    timeout=TETO_DA_CHAMADA_S)
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


def tentativa_na_tela(sessao: Dict[str, Any], tela: str) -> str:
    """Qual DECISÃO sobre esta tela é esta, contada pelo que JÁ ACONTECEU na conversa (X5):
    `<vezes que a tela chegou>.<respostas do destravador depois da última vez que ela chegou>`.

    🔴 Juiz pendência 4 · red team P5: a chave era empresa+acionamento+tela, e a 2ª decisão na MESMA
    tela (a URA a repetiu; o Sentinela tentou de novo) devolvia a linha da 1ª — o diário perdia uma
    decisão (G5: uma linha por decisão). ⛔ A MESMA entrega repetida (a mesma mensagem processada de
    novo, sem nada novo na conversa) conta igual — e cai na MESMA linha, sem duplicar."""
    alvo = " ".join(_n(tela).split())
    chegou, depois = 0, 0
    for e in (sessao or {}).get("transcript") or []:
        if not isinstance(e, dict):
            continue
        texto = " ".join(_n(e.get("text")).split())
        if str(e.get("direction") or "") == "in" and texto and alvo and texto in alvo:
            chegou += 1
            depois = 0
        elif str(e.get("direction") or "") == "out" and str(e.get("via") or "") == "destravador":
            depois += 1
    return f"{chegou}.{depois}"


def chave_de_idempotencia(company_id: str, sessao: Dict[str, Any], tela: str) -> str:
    """empresa + acionamento + tela + TENTATIVA (`tentativa_na_tela`): a mesma entrega, UMA linha;
    a 2ª decisão na mesma tela, a sua própria linha (X5)."""
    run = str((sessao or {}).get("work_run_id") or (sessao or {}).get("case_id") or "")
    t = " ".join(_n(tela).split())
    return (f"destravador:{company_id}:{run}:{hashlib.sha256(t.encode()).hexdigest()[:24]}:"
            f"{tentativa_na_tela(sessao, tela)}")


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


#: O teto do `motivo` que o destravador manda ao diário (o diário mascara e corta em 400).
_TETO_MOTIVO_NO_DIARIO = 300


def motivo_no_diario(d: Destravamento) -> str:
    """O `motivo` da linha do diário: o do modelo + `[proibição]` + — ajuste W (P-N1) — a pergunta
    que o modelo PROPÔS ao segurado, que não foi ao segurado (a composta pelo código foi). É o único
    lugar onde o texto livre do modelo fica; o diário mascara os dados do caso (`_mascarar`)."""
    proposta = ""
    if d.acao_do_modelo == "PERGUNTAR_AO_SEGURADO" and str(d.valor_do_modelo or "").strip():
        proposta = f" [o modelo propôs: “{' '.join(str(d.valor_do_modelo).split())[:160]}”]"
    base = d.motivo + (f" [{d.proibicao}]" if d.proibicao else "")
    return base[:_TETO_MOTIVO_NO_DIARIO - len(proposta)] + proposta


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
            limiar=d.limiar, motivo=motivo_no_diario(d),
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
                    limiar: int = 70, llm: Optional[ModeloInjetado] = None,
                    llm_segunda: Optional[ModeloInjetado] = None) -> Destravamento:
    """UMA trava → UMA decisão. `gatilho` = o reason do motor (ponto B) ou "cerebro"/"sentinela"
    (ponto A). Monta o contexto COMPLETO, chama o modelo do papel `destravador`, aplica a POLÍTICA
    EM CÓDIGO, registra no diário e devolve a decisão. ⛔ Nunca envia nada. Nunca levanta.

    `llm` / `llm_segunda` (F1c): quem decide e a 2ª opinião INJETADOS (`ModeloInjetado`) — a
    bancada mede braços de fora do catálogo pelo MESMO fio. Com `llm` injetado, a 2ª opinião é só
    `llm_segunda` (None → sem 2ª opinião). Produção não passa nada: tudo pelo catálogo."""
    try:
        return await _destravar(company_id, sessao, tela, gatilho=gatilho, modo=modo, limiar=limiar,
                                llm=llm, llm_segunda=llm_segunda)
    except Exception as e:  # noqa: BLE001 — falha fechada
        logger.error("[DESTRAVADOR] falhou (%s) — pessoa", type(e).__name__)
        return Destravamento(classe="nunca_sozinho", acao="PESSOA", proibicao="falha_do_destravador",
                             limiar=_limiar_efetivo(limiar),
                             modo=modo if modo in ("on", "sombra") else "on", gatilho=str(gatilho or ""))


async def _destravar(company_id: str, sessao: dict, tela: str, *, gatilho: str, modo: str,
                     limiar: int, llm: Optional[ModeloInjetado] = None,
                     llm_segunda: Optional[ModeloInjetado] = None) -> Destravamento:
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
        if llm is not None:
            resposta, provedor, modelo = await _chamar_injetado(llm, conversa)
        else:
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
        if llm is not None:
            segunda, c2 = await _segunda_injetada(llm_segunda, conversa, provedor)
        else:
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


# ═════════════════════════════════════════════════════════════════════════════
# O PORTAL DE VIDROS — o MESMO núcleo, outro canal (SPEC-124 F1 · D1/D2/D5)
# ═════════════════════════════════════════════════════════════════════════════
#
# O fio: `portal_tool._aguardar` vê o job `needs_human` com `acao_esperada = responder:<slot>` e o modo
# `on` (`cerebro_modos`: seguradora pela chave do corredor, ramo `vidros`; a linha `todos` vale) →
# `destravar_parada_do_portal` → a CLASSE da parada pela TABELA (código) → o modelo do papel
# `destravador` (catálogo) só quando a tabela deixa o modelo propor → `decidir_parada_do_portal` (o
# NÚCLEO `regua_do_nucleo` + o NUNCA do portal) → diário (`origem='portal'`) → a tool continua o MESMO
# pedido (`montar_job_de_continuacao`, mecanismo da 001.10.1) ou segue o caminho de hoje (pergunta).
# ⛔ Este módulo continua sem enviar nada: quem enfileira a continuação é a tool, e o `confirm` dela é
# o gate de hoje (`portal_tool.envio_liberado`).
ORIGEM_DO_PORTAL = "portal"
RAMO_DO_PORTAL = "vidros"
ROTA_DO_PORTAL = "portal:vidros_lanternas"

#: A ação no diário quando o canal é o portal: a resposta foi ao PORTAL, não à URA (migration 20261001_04).
ACAO_NO_DIARIO_DO_PORTAL = {**ACAO_NO_DIARIO, "RESPONDER": "respondeu_portal"}

#: constante_justificada: quantas vezes o destravador pode continuar o MESMO pedido sozinho. 📊 O mapa
#: fechado das paradas (`vidros_estado.ETAPA_DA_PARADA`) tem 6 etapas que esperam `responder:*` (peça,
#: causa, lataria, cidade, questionário, reparo) — e com o DEDUZIR desligado só a UF age hoje. 3 cobre a
#: UF + duas perguntas do questionário quando a calibração religar, e corta o laço (o portal parando
#: sempre no mesmo ponto) antes de virar uma fila de jobs na seguradora. Passou do teto → caminho de hoje.
TETO_DE_DESTRAVAMENTOS_POR_PEDIDO = 3

#: 🔴 A CLASSE DE CADA PARADA do API-first — a tabela do laudo do BLOCO 0 da SPEC-124 (o código decide a
#: classe; o modelo só propõe o VALOR onde a tabela deixa). Parada fora daqui = técnica: não se destrava.
#: constante_justificada (cada linha):
#:   uf_desconhecida         o estado do serviço é DADO DO CASO (cadastro/cidade do serviço) e a lista
#:                           do portal é fechada (27 UFs): responder com o dado, se ele está na lista
#:   tipo_de_telefone_…      o tipo de contato é CONTRATO nosso (D-E00110-01): conduzir — mas a parada
#:                           espera `reler` (o vigia relê); o plugue `responder:*` não chega nela
#:   *_ambigua · motivo_ambiguo · questionario_incompleto   escolher numa lista = DEDUZIR (desligado
#:                           sem calibração → pergunta ao segurado; o questionário nunca "Não sabe")
#:   pecas_de_lataria_ausentes · cidade_sem_rede · decidir_vistoria   só o segurado sabe
#:   decidir_reparo          reparo × troca muda FRANQUIA/custo: NUNCA sozinho, pergunta (D2)
#:   pronto_para_agendar · horario_indisponivel   loja e horário: a escolha (e a loja paga) é dele (D2)
#:   coverage_absent · maybe_committed · pronto_para_* · prioridade_nao_medida   NUNCA → gate / pessoa
CLASSE_DA_PARADA_DO_PORTAL: Dict[str, str] = {
    "uf_desconhecida": "responder_com_dado",
    "tipo_de_telefone_desconhecido": "conduzir",
    "peca_ambigua": "deduzir",
    "motivo_ambiguo": "deduzir",
    "peca_de_lataria_ambigua": "deduzir",
    "cidade_ambigua": "deduzir",
    "questionario_incompleto": "deduzir",
    "pecas_de_lataria_ausentes": "perguntar_ao_segurado",
    "cidade_sem_rede": "perguntar_ao_segurado",
    "decidir_vistoria": "perguntar_ao_segurado",
    "decidir_reparo": "nunca_sozinho",
    "pronto_para_agendar": "nunca_sozinho",
    "horario_indisponivel": "nunca_sozinho",
    "coverage_absent": "nunca_sozinho",
    "maybe_committed": "nunca_sozinho",
    "pronto_para_abrir": "nunca_sozinho",
    "pronto_para_materializar": "nunca_sozinho",
    "pronto_para_vistoria": "nunca_sozinho",
    "prioridade_nao_medida": "nunca_sozinho",
}

#: O NUNCA de cada parada NUNCA: (a chave de `NUNCA_SOZINHO` — a MESMA lista do WhatsApp —, e o que se
#: faz: "pergunta" ao segurado, ou "pessoa"/gate). D2 do Founder: aceitar franquia/valor/custo, escolher
#: loja paga fora do caso, cancelar, inventar dado. Confirmar com o caso completo continua no gate de hoje.
NUNCA_DA_PARADA_DO_PORTAL: Dict[str, Tuple[str, str]] = {
    "decidir_reparo": ("aceite_de_custo", "pergunta"),
    "pronto_para_agendar": ("aceite_de_custo", "pergunta"),
    "horario_indisponivel": ("aceite_de_custo", "pergunta"),
    "coverage_absent": ("afirma_cobertura", "pessoa"),
    "maybe_committed": ("novo_atendimento", "pessoa"),
    "pronto_para_abrir": ("confirmacao_final", "pessoa"),
    "pronto_para_materializar": ("confirmacao_final", "pessoa"),
    "pronto_para_vistoria": ("confirmacao_final", "pessoa"),
    "prioridade_nao_medida": ("confirmacao_final", "pessoa"),
}

#: O que faltava, em palavras de gente (a frase do diário — D7: nada de nome de variável).
_O_QUE_FALTAVA_NO_PORTAL = {
    "uf_desconhecida": "o estado (UF) onde o serviço vai ser feito",
    "tipo_de_telefone_desconhecido": "o tipo do telefone de contato",
    "peca_ambigua": "escolher a peça certa na lista do portal",
    "motivo_ambiguo": "escolher a causa do dano na lista do portal",
    "peca_de_lataria_ambigua": "escolher a peça de lataria na lista do portal",
    "pecas_de_lataria_ausentes": "dizer quais peças de lataria foram atingidas",
    "cidade_ambigua": "escolher a cidade do serviço na lista do portal",
    "cidade_sem_rede": "outra cidade com loja para o serviço",
    "questionario_incompleto": "uma resposta do questionário da seguradora",
    "decidir_reparo": "a escolha entre reparar ou trocar a peça",
    "decidir_vistoria": "como o segurado prefere fazer a vistoria",
    "pronto_para_agendar": "a escolha da loja e do horário",
    "horario_indisponivel": "outro horário, porque o escolhido não está mais livre",
}

#: constante_justificada: o VALOR que aceita custo, no texto normalizado (`_n`: sem acento, sem "$"). D2:
#: "aceitar franquia/valor/custo" e "loja paga". O falso positivo custa uma pergunta ao segurado; o
#: negativo, um custo aceito por ele sem ele saber.
_RX_CUSTO_NO_PORTAL = re.compile(
    r"\bfranquia|\bvalor(?:es)?\b|\bcusto|\bpag(?:ar|o|a|amento|ando)\b|\bcobr|\bparticipac|\breais\b|"
    r"\bexcedente|\bdesconto|\bpreco|\bdeposit|\bpix\b|\br \d")
#: constante_justificada: o VALOR que cancela/desiste/encerra o pedido (D2 "cancelar") — o radical do
#: WhatsApp (`_RX_CANCELA`) + desistir/encerrar, no texto normalizado.
_RX_CANCELA_NO_PORTAL = re.compile(r"\bcancel|\bdesist|\bencerr")


def chave_da_seguradora_do_portal(params: Optional[dict]) -> str:
    """A seguradora do pedido como `cerebro_modos` a conhece: a chave do CORREDOR (`normalize_insurer_key`,
    a régua única do produto — 📊 "LIBERTY SEGUROS S/A" → `yelum`). Nunca constante de corretora."""
    nome = str((params or {}).get("insurer_name") or "").strip()
    if not nome:
        return ""
    try:
        from app.services.corridor_playbooks import normalize_insurer_key

        return normalize_insurer_key(nome) or ""
    except Exception:  # noqa: BLE001
        return ""


def _folhas(valor: Any) -> List[str]:
    if isinstance(valor, dict):
        return [x for v in valor.values() for x in _folhas(v)]
    if isinstance(valor, (list, tuple)):
        return [x for v in valor for x in _folhas(v)]
    if isinstance(valor, bool) or valor is None:
        return []
    return [str(valor)]


def valores_do_caso_no_portal(params: Optional[dict]) -> set:
    """Os VALORES do caso (normalizados) que podem responder o portal: o que a conversa e a apólice
    trouxeram. ⛔ Fora: as chaves internas (`_…`), o `contato` (é da CORRETORA) e o `confirm`."""
    fora = {"contato", "confirm", "solicitante"}
    return {_n(x) for k, v in (params or {}).items()
            if not str(k).startswith("_") and k not in fora for x in _folhas(v) if _n(x)}


def _opcao_igual(valor: Any, opcoes: List[str]) -> str:
    """A opção da lista do portal que É este valor (igualdade normalizada, nunca pedaço). "" se nenhuma."""
    alvo = _n(valor)
    if not alvo:
        return ""
    iguais = [o for o in opcoes if _n(o) == alvo]
    return iguais[0] if len(iguais) == 1 else ""


def parada_do_portal(evidence: Any) -> Dict[str, Any]:
    """A parada que o job do portal gravou (`evidence` = o `_augment_hitl_evidence` do worker):
    `{stage, operacao, slot, opcoes, pergunta, mensagem}`."""
    from app.agents.tools.portal_params import acao_esperada

    ev = evidence if isinstance(evidence, dict) else {}
    operacao, slot = acao_esperada(ev)
    af = ev.get("api_first") if isinstance(ev.get("api_first"), dict) else {}
    stage = str(ev.get("stage") or af.get("parou_em") or "").strip()
    cont = ev.get("continuacao") if isinstance(ev.get("continuacao"), dict) else {}
    opcoes = [" ".join(str(o).split()) for o in (ev.get("opcoes") or []) if str(o or "").strip()][:60]
    return {"stage": stage, "operacao": operacao, "slot": slot, "opcoes": opcoes,
            "pergunta": " ".join(str(ev.get("pergunta") or "").split())[:300],
            "mensagem": " ".join(str(ev.get("message") or cont.get("motivo") or "").split())[:300]}


def texto_da_parada(parada: Dict[str, Any]) -> str:
    """A "tela" do portal, para o diário e para o modelo: o que faltava, a pergunta e as opções."""
    falta = _O_QUE_FALTAVA_NO_PORTAL.get(parada.get("stage") or "", "um dado do pedido")
    linhas = [f"O portal de vidros parou o pedido: falta {falta}."]
    if parada.get("pergunta"):
        linhas.append(f"Pergunta do portal: {parada['pergunta']}")
    if parada.get("mensagem"):
        linhas.append(f"Motivo: {parada['mensagem']}")
    if parada.get("opcoes"):
        linhas.append("Opções da lista do portal:")
        linhas += [f"{i} - {o}" for i, o in enumerate(parada["opcoes"], 1)]
    return "\n".join(linhas)


def resposta_do_portal(stage: str, slot: str, valor: str, params: Optional[dict]) -> Dict[str, Any]:
    """`{slot: valor}` no CONTRATO da continuação (`portal_params.respostas_da_chamada`, o MESMO da
    001.10.1) — ou `{}` quando a resposta não tem formato para esta parada, ou é a MESMA com que o
    portal parou (reenviá-la produziria a mesma parada e um job a mais na seguradora)."""
    import copy

    from app.agents.tools.portal_params import respostas_da_chamada

    origem = params if isinstance(params, dict) else {}
    novo = copy.deepcopy({k: v for k, v in origem.items() if k != "_runtime"})
    valor = str(valor or "").strip()
    if not slot or not valor:
        return {}
    local = dict(novo.get("local") or {})
    cid = dict(local.get("cidade_servico") or {}) if isinstance(local.get("cidade_servico"), dict) else {}
    if slot == "cidade_servico":
        if stage == "uf_desconhecida":
            if not str(cid.get("cidade") or "").strip():
                return {}
            cid["uf"] = valor.upper()
        elif stage == "cidade_ambigua":
            cid["cidade"] = valor
        else:
            return {}
        local["cidade_servico"] = cid
        novo["local"] = local
    elif slot == "como":
        novo["dano"] = {**dict(novo.get("dano") or {}), "como": valor}
    elif slot == "peca" or slot.startswith("pergunta_"):
        novo["especificos"] = {**dict(novo.get("especificos") or {}), slot: valor}
    else:
        return {}      # lataria (lista), reparo (NUNCA): o destravador não responde
    return respostas_da_chamada(novo, origem, slot)


def decidir_parada_do_portal(proposta: Optional[Proposta], parada: Dict[str, Any], params: Optional[dict], *,
                             limiar: int = LIMIAR_MINIMO, modo: str = "on", provedor: str = "",
                             segunda_opiniao: Optional[dict] = None, pedir_segunda: bool = False,
                             nunca=None) -> Optional[Destravamento]:
    """A POLÍTICA no portal (D1/D2), em CÓDIGO e pura: a TABELA dá a classe; o NUNCA do portal; o NÚCLEO
    (`regua_do_nucleo`, o MESMO do WhatsApp) decide a resposta. `proposta=None` → só o código: devolve a
    decisão quando a tabela basta, ou `None` quando o modelo tem de propor o valor."""
    ligadas = chaves_ligadas(nunca)
    lim = _limiar_efetivo(limiar)
    stage = str(parada.get("stage") or "")
    opcoes = list(parada.get("opcoes") or [])
    classe_tab = CLASSE_DA_PARADA_DO_PORTAL.get(stage, "")
    pode_perguntar = parada.get("operacao") == "responder"
    base: Dict[str, Any] = dict(classe=classe_tab or "nunca_sozinho", nota=None, limiar=lim, motivo="",
                                modo=modo, provedor=provedor, segunda_opiniao=segunda_opiniao,
                                gatilho=f"portal:{stage}")
    if proposta is not None:
        base.update(nota=proposta.nota, motivo=proposta.motivo, formato_ok=proposta.formato_ok,
                    acao_do_modelo=proposta.acao if proposta.formato_ok else "",
                    valor_do_modelo=proposta.valor)

    def pessoa(porque: str, classe: Optional[str] = None) -> Destravamento:
        d = Destravamento(acao="PESSOA", proibicao=porque, **base)
        if classe:
            d.classe = classe
        return d

    def perguntar(porque: str, classe: Optional[str] = None) -> Destravamento:
        if not pode_perguntar:
            return pessoa(porque, classe)
        d = Destravamento(acao="PERGUNTAR_AO_SEGURADO", proibicao=porque,
                          valor=(parada.get("pergunta") or texto_da_parada(parada))[:400],
                          opcoes=[[str(i), o] for i, o in enumerate(opcoes, 1)], **base)
        if classe:
            d.classe = classe
        return d

    # ① A parada técnica não se destrava (o vigia relê; a equipe segue pelo número).
    if not classe_tab:
        return pessoa("parada_tecnica", "nunca_sozinho")
    # ② O NUNCA da TABELA — antes do modelo (nem se gasta).
    if classe_tab == "nunca_sozinho":
        chave, como = NUNCA_DA_PARADA_DO_PORTAL.get(stage, ("confirmacao_final", "pessoa"))
        if chave in ligadas:
            return perguntar(chave) if como == "pergunta" else pessoa(chave)
    # ③ Só o segurado sabe.
    if classe_tab == "perguntar_ao_segurado":
        return perguntar("so_o_segurado_sabe")
    # ④ DEDUZIR sem calibração: o NÚCLEO decide sem o modelo (a mesma régua; a 2ª opinião não é paga).
    if classe_tab == "deduzir" and not DEDUZIR_AUTONOMO_CALIBRADO:
        v = regua_do_nucleo(Proposta(classe="deduzir", acao="RESPONDER", nota=None), limiar=lim,
                            e_navegacao=lambda: False, e_dado_do_caso=lambda: False,
                            tem_opcoes=bool(opcoes), valor_nas_opcoes=lambda: False,
                            mesma_resposta=lambda _o: False)
        base["classe"] = v.classe
        return perguntar(v.porque)
    if proposta is None:
        return None
    # ⑤ A saída do modelo.
    p = proposta
    if not p.formato_ok:
        return pessoa(f"saida_invalida:{p.erro}", "nunca_sozinho")
    if p.acao == "PESSOA":
        return pessoa("o_modelo_chamou_uma_pessoa")
    if p.acao != "RESPONDER":
        # PERGUNTAR (ou um SILENCIO, que no portal não existe): o caminho de hoje — o agente pergunta.
        return perguntar("o_modelo_quis_perguntar" if p.acao == "PERGUNTAR_AO_SEGURADO"
                         else "silencio_no_portal", "perguntar_ao_segurado")
    valor = p.valor
    nv = _n(valor)
    opcao = _opcao_igual(valor, opcoes)
    # ⑥ O NUNCA do portal sobre o VALOR (D2) — a mesma lista de chaves do WhatsApp.
    if "aceite_de_custo" in ligadas and (_RX_CUSTO_NO_PORTAL.search(nv) or "r$" in str(valor).lower()):
        return perguntar("aceite_de_custo")
    if "cancelar_pedido" in ligadas and _RX_CANCELA_NO_PORTAL.search(nv):
        return pessoa("cancelar_pedido")
    if "abrir_sinistro" in ligadas and _RX_SINISTRO.search(nv):
        return pessoa("abrir_sinistro")
    if "afirma_cobertura" in ligadas and not opcao:
        from app.services import acao_do_cerebro as AC

        if AC._RX_AFIRMA_COBERTURA.search(valor or ""):
            return pessoa("afirma_cobertura")
    caso = valores_do_caso_no_portal(params)
    if "inventar_dado" in ligadas and _numero_inventado(
            valor, {"slots": {str(i): x for i, x in enumerate(_folhas(params or {}))}}):
        return pessoa("inventar_dado")
    # ⑦ O NÚCLEO. A classe é a da TABELA (o modelo não promove a parada); o código prova cada uma.
    classe = classe_tab if classe_tab in ("conduzir", "responder_com_dado", "deduzir") else p.classe
    v = regua_do_nucleo(
        Proposta(classe=classe, acao="RESPONDER", valor=valor, nota=p.nota, motivo=p.motivo),
        limiar=lim, provedor=provedor, segunda_opiniao=segunda_opiniao, pedir_segunda=pedir_segunda,
        e_navegacao=lambda: classe_tab == "conduzir" and bool(opcao),
        e_dado_do_caso=lambda: bool(opcao or not opcoes) and nv in caso,
        tem_opcoes=bool(opcoes), valor_nas_opcoes=lambda: bool(opcao),
        mesma_resposta=lambda outro: _n(outro) == nv or (bool(opcao) and _opcao_igual(outro, opcoes) == opcao))
    base["classe"] = v.classe
    if v.passo == PASSO_PRECISA_SEGUNDA:
        return Destravamento(acao="PESSOA", valor=valor, proibicao="precisa_segunda_opiniao", **base)
    if v.passo == PASSO_REBAIXAR:
        return perguntar(v.porque)
    final = opcao or valor
    if not resposta_do_portal(stage, str(parada.get("slot") or ""), final, params):
        return perguntar("resposta_sem_formato_ou_repetida")
    return Destravamento(acao="RESPONDER", valor=final, **base)


#: 🔴 A parte FIXA do prompt do portal: o cabeçalho do canal + as MESMAS regras de resposta do WhatsApp
#: (classes, nota, JSON) — fatiadas da instrução de lá, nunca reescritas.
_REGRAS_DA_RESPOSTA = INSTRUCAO_DO_DESTRAVADOR[
    INSTRUCAO_DO_DESTRAVADOR.index("CLASSES — escolha UMA:"):INSTRUCAO_DO_DESTRAVADOR.index("══════ O ROTEIRO")]
INSTRUCAO_DO_DESTRAVADOR_NO_PORTAL = (
    "══════ VOCÊ FOI CHAMADO PORQUE O PORTAL DE VIDROS PAROU O PEDIDO ══════\n"
    "OBJETIVO: continuar o MESMO pedido de vidros na seguradora sem chamar uma pessoa da corretora — com a "
    "resposta CERTA. O pedido JÁ EXISTE no portal; a sua resposta continua ele (nunca abre outro). Leia o "
    "caso, a conversa com o segurado e a parada, e decida como um atendente experiente decidiria.\n"
    "No portal, \"a tela\" é a parada: o que faltava e a lista FECHADA de opções do portal. Responder = "
    "escolher UMA opção da lista, escrita igual. Nunca aceite franquia, valor ou custo, nunca escolha loja "
    "paga, nunca cancele, nunca invente dado: isso é do segurado ou de uma pessoa.\n\n"
    + _REGRAS_DA_RESPOSTA)


def _caso_do_portal_em_palavras(params: Dict[str, Any]) -> str:
    """O que o caso diz, sem documento, placa, chassi, telefone ou e-mail (o modelo não precisa deles)."""
    dano = params.get("dano") if isinstance(params.get("dano"), dict) else {}
    local = params.get("local") if isinstance(params.get("local"), dict) else {}
    cid = local.get("cidade_servico") if isinstance(local.get("cidade_servico"), dict) else {}
    esp = params.get("especificos") if isinstance(params.get("especificos"), dict) else {}
    linhas = [f"- seguradora: {params.get('insurer_name') or 'não informada'}",
              f"- peça: {dano.get('peca') or 'não informada'}",
              f"- como ocorreu: {dano.get('como') or 'não informado'}",
              f"- onde ocorreu: {dano.get('onde') or 'não informado'}",
              f"- cidade do serviço: {cid.get('cidade') or '?'} / estado {cid.get('uf') or '?'}",
              f"- estado do cadastro do segurado: {local.get('estado') or '?'}"]
    if dano.get("descricao"):
        linhas.append(f"- relato: {' '.join(str(dano['descricao']).split())[:400]}")
    for k, v in list(esp.items())[:20]:
        if not str(k).startswith("_"):
            linhas.append(f"- {str(k).replace('_', ' ')}: {' '.join(str(v).split())[:120]}")
    return "\n".join(linhas)


def _historico_do_pedido(evidence: Dict[str, Any], params: Dict[str, Any]) -> str:
    est = evidence.get("vidros_estado") if isinstance(evidence.get("vidros_estado"), dict) else {}
    cont = evidence.get("continuacao") if isinstance(evidence.get("continuacao"), dict) else {}
    antes = params.get("_continuacao") if isinstance(params.get("_continuacao"), dict) else {}
    linhas = [f"- estado do pedido no portal: {est.get('estado') or 'desconhecido'}",
              f"- etapa onde parou: {cont.get('etapa') or '?'}"]
    if antes.get("respostas"):
        linhas.append("- respostas já levadas ao portal neste pedido: "
                      + ", ".join(str(k).replace("_", " ") for k in antes["respostas"]))
    return "\n".join(linhas)


def compor_mensagens_do_portal(parada: Dict[str, Any], params: Dict[str, Any], evidence: Dict[str, Any], *,
                               conversa: Optional[List[str]] = None,
                               memoria: Optional[List[str]] = None) -> Dict[str, str]:
    """O prompt do destravador no PORTAL. Puro. Fixo primeiro (o cache por prefixo), a parada por último."""
    user = "DADOS DO CASO:\n" + _caso_do_portal_em_palavras(params)
    if memoria:
        user += "\n\nO QUE A CORRETORA JÁ ENSINOU:\n" + "\n".join(memoria)
    user += ("\n\nA CONVERSA COM O SEGURADO (as últimas mensagens, a mais antiga primeiro):\n" + "\n".join(conversa)
             if conversa else "\n\nA CONVERSA COM O SEGURADO: (não disponível neste caso)")
    user += "\n\nO PEDIDO ATÉ AQUI:\n" + _historico_do_pedido(evidence, params)
    user += f"{_MARCA_DO_VARIAVEL}o portal parou e esta parada pode ser respondida por aqui.\n\n"
    user += texto_da_parada(parada) + "\n\nSua resposta (o JSON):"
    return {"system": INSTRUCAO_DO_DESTRAVADOR_NO_PORTAL, "user": user}


def _telefone_da_conversa(params: Dict[str, Any]) -> str:
    sessao = str(params.get("_conversation_id") or "")
    partes = sessao.split(":")
    return re.sub(r"\D", "", partes[1]) if len(partes) >= 2 and partes[0] == "whatsapp" else ""


def _frase_do_portal(seguradora: str, parada: Dict[str, Any], d: Destravamento) -> str:
    """A frase para GENTE (D7) do portal: "No portal da loja de vidros, faltava …"."""
    falta = _O_QUE_FALTAVA_NO_PORTAL.get(str(parada.get("stage") or ""), "um dado do pedido")
    try:
        from app.services.diario_de_decisoes import _POR_QUE, _nome_da_seguradora

        nome, por_classe = _nome_da_seguradora(seguradora), _POR_QUE
    except Exception:  # noqa: BLE001
        nome, por_classe = (seguradora or "a seguradora").capitalize(), {}
    if d.modo == "sombra":
        fez = "apenas observou, sem responder nada" + (
            f" (se estivesse ligado, teria respondido “{d.valor[:80]}”)" if d.acao == "RESPONDER" else "")
    else:
        fez = {"RESPONDER": f"respondeu ao portal “{d.valor[:80]}” e continuou o MESMO pedido",
               "PERGUNTAR_AO_SEGURADO": "deixou a pergunta para o segurado",
               "PESSOA": "deixou o caso para uma pessoa da corretora"}.get(d.acao, "decidiu")
    porque = PORQUE.get(d.proibicao) or por_classe.get(d.classe, "")
    porque = porque[len("porque "):] if porque.startswith("porque ") else porque
    extra = []
    if d.nota is not None:
        extra.append(f"certeza {d.nota}%")
    if d.segunda_opiniao and "concordou" in d.segunda_opiniao:
        extra.append("a segunda opinião concordou" if d.segunda_opiniao.get("concordou")
                     else "a segunda opinião discordou")
    frase = (f"No portal da loja de vidros ({nome}), faltava {falta}. O agente {fez}"
             + (f" porque {porque}" if porque else "") + (f" ({', '.join(extra)})." if extra else "."))
    return frase + (" (Em sombra: nada foi enviado.)" if d.modo == "sombra" else "")


def _sessao_para_mascarar(params: Dict[str, Any]) -> Dict[str, Any]:
    """Os campos de PESSOA do pedido, no formato que o mascarador do diário lê (`higienizar_para_o_rastro`)."""
    seg = params.get("segurado") if isinstance(params.get("segurado"), dict) else {}
    slots = {k: v for k, v in seg.items() if isinstance(v, (str, int)) and not isinstance(v, bool)}
    slots.update({"placa": params.get("placa") or "", "cpf_cnpj": params.get("cpf_cnpj") or ""})
    return {"slots": slots, "client_phone": _telefone_da_conversa(params)}


def chave_do_diario_do_portal(company_id: str, job_id: str, parada: Dict[str, Any]) -> str:
    """Empresa + o JOB que parou + a parada: a mesma parada relida, UMA linha; a próxima (outro job), outra."""
    return f"destravador:portal:{company_id}:{job_id}:{parada.get('stage') or ''}"[:200]


async def _registrar_do_portal(company_id: str, parada: Dict[str, Any], params: Dict[str, Any],
                               d: Destravamento, *, job_id: str, work_run_id: Optional[str]) -> Optional[str]:
    try:
        from app.services import diario_de_decisoes as DD
    except Exception as e:  # noqa: BLE001
        logger.warning("[DESTRAVADOR] diário indisponível (%s) — decisão sem linha", type(e).__name__)
        return None
    seguradora = chave_da_seguradora_do_portal(params)
    acao = "nao_agiu" if d.modo == "sombra" else ACAO_NO_DIARIO_DO_PORTAL.get(d.acao, "chamou_pessoa")
    d.explicacao = _frase_do_portal(seguradora, parada, d)
    run = str(work_run_id or params.get("_work_run_id") or "").strip()
    dano = params.get("dano") if isinstance(params.get("dano"), dict) else {}
    try:
        return await DD.registrar_decisao(
            company_id=str(company_id), origem=ORIGEM_DO_PORTAL,
            work_run_id=run if re.fullmatch(r"[0-9a-fA-F-]{36}", run) else None, conversation_id=None,
            seguradora=seguradora, ramo=RAMO_DO_PORTAL, rota=ROTA_DO_PORTAL,
            servico=str(dano.get("peca") or ""), tela=texto_da_parada(parada), classe=d.classe, acao=acao,
            valor=d.valor, nota=d.nota, limiar=d.limiar, motivo=motivo_no_diario(d),
            explicacao_para_gente=d.explicacao, modelo=d.modelo, segunda_opiniao=d.segunda_opiniao,
            modo=d.modo, gatilho=d.gatilho, chave_idempotencia=chave_do_diario_do_portal(company_id, job_id, parada),
            sessao=_sessao_para_mascarar(params))
    except Exception as e:  # noqa: BLE001
        logger.warning("[DESTRAVADOR] diário falhou (%s)", type(e).__name__)
        return None


async def destravar_parada_do_portal(company_id: str, evidence: Any, params: Any, *, modo: str,
                                     limiar: int = LIMIAR_MINIMO, job_id: str = "",
                                     work_run_id: Optional[str] = None,
                                     llm: Optional[ModeloInjetado] = None,
                                     llm_segunda: Optional[ModeloInjetado] = None) -> Optional[Destravamento]:
    """UMA parada do portal → UMA decisão (ou `None`: modo off, ou a parada não espera `responder:*`).

    `params` = os do JOB que parou (o que o portal usou). Monta o contexto (o caso, a conversa com o
    segurado, a parada, o histórico do pedido), chama o modelo do papel `destravador` SÓ quando a tabela
    deixa, aplica a política (`decidir_parada_do_portal` → `regua_do_nucleo`) e registra no diário.
    ⛔ Nunca envia nada. Nunca levanta: falha → PESSOA (o caminho de hoje)."""
    m = str(modo or "").strip().lower()
    if m not in ("on", "sombra"):
        return None
    try:
        return await _destravar_parada_do_portal(company_id, evidence, params, modo=m, limiar=limiar,
                                                 job_id=job_id, work_run_id=work_run_id, llm=llm,
                                                 llm_segunda=llm_segunda)
    except Exception as e:  # noqa: BLE001 — falha fechada
        logger.error("[DESTRAVADOR] portal falhou (%s) — caminho de hoje", type(e).__name__)
        return Destravamento(classe="nunca_sozinho", acao="PESSOA", proibicao="falha_do_destravador",
                             limiar=_limiar_efetivo(limiar), modo=m, gatilho="portal")


async def _destravar_parada_do_portal(company_id: str, evidence: Any, params: Any, *, modo: str, limiar: int,
                                      job_id: str, work_run_id: Optional[str],
                                      llm: Optional[ModeloInjetado],
                                      llm_segunda: Optional[ModeloInjetado]) -> Optional[Destravamento]:
    from langchain_core.messages import HumanMessage, SystemMessage

    from app.agents.utils import extract_text_from_content

    cid = str(company_id or "").strip()
    ev = evidence if isinstance(evidence, dict) else {}
    prm = dict(params) if isinstance(params, dict) else {}
    parada = parada_do_portal(ev)
    if parada["operacao"] != "responder" or not cid:
        return None
    lim = _limiar_efetivo(limiar)
    d = decidir_parada_do_portal(None, parada, prm, limiar=lim, modo=modo)
    if d is None:
        conversa_seg, memoria = await asyncio.gather(
            _com_teto(_conversa_do_segurado(cid, {"client_phone": _telefone_da_conversa(prm)}), []),
            _com_teto(_memoria_da_corretora(cid), []))
        msgs = compor_mensagens_do_portal(parada, prm, ev, conversa=conversa_seg, memoria=memoria)
        conversa = [SystemMessage(content=msgs["system"]), HumanMessage(content=msgs["user"])]
        try:
            if llm is not None:
                resposta, provedor, modelo = await _chamar_injetado(llm, conversa)
            else:
                resposta, provedor, modelo = await _chamar_quem_decide(conversa, cid, modo)
        except Exception as e:  # noqa: BLE001 — o modelo caiu: nada foi decidido
            logger.warning("[DESTRAVADOR] portal: modelo falhou (%s) — caminho de hoje", type(e).__name__)
            resposta, provedor, modelo = None, "", ""
        if resposta is None:
            d = Destravamento(classe="nunca_sozinho", acao="PESSOA", proibicao="modelo_falhou",
                              limiar=lim, modo=modo, gatilho=f"portal:{parada['stage']}")
        else:
            custo = _custo(resposta, modelo)
            proposta = ler_destravamento(extract_text_from_content(getattr(resposta, "content", None)) or "")
            d = decidir_parada_do_portal(proposta, parada, prm, limiar=lim, modo=modo, provedor=provedor,
                                         pedir_segunda=True)
            if d is not None and d.proibicao == "precisa_segunda_opiniao":
                if llm is not None:
                    segunda, c2 = await _segunda_injetada(llm_segunda, conversa, provedor)
                else:
                    segunda, c2 = await _segunda_opiniao(conversa, cid, modo, provedor,
                                                         texto_da_parada(parada))
                custo += c2
                d = decidir_parada_do_portal(proposta, parada, prm, limiar=lim, modo=modo, provedor=provedor,
                                             segunda_opiniao=segunda, pedir_segunda=False)
            d.modelo = modelo
            d.custo_usd = round(custo, 6)
            d.modelo_chamado = True
    d.diario_id = await _registrar_do_portal(cid, parada, prm, d, job_id=str(job_id or ""),
                                             work_run_id=work_run_id)
    return d
