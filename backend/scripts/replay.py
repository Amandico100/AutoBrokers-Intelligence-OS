"""O REPLAY — SPEC-083 §3.3, Bloco B. A única medida que reproduziu.

Cada tela do corpus roda pelo **MOTOR** (`match_ura_step`) e cai numa classe:

```
RESPONDIDA      casou um passo que devolve resposta          ✅
NOOP            casou um passo `noop`                        ✅
ORFA_INOCUA     não casou, e `_tela_pede_alguma_coisa` = False   ⚪ tolerável
ORFA_FUNCIONAL  não casou, e `_tela_pede_alguma_coisa` = True    🔴 é o defeito
HANDOFF         não casou, mas dispara `detect_handoff_trigger`  ⊘ fora do denominador
CAPTURADA       não casou, mas `extract_capture_anchors` a LÊ     ⊘ fora do denominador
FORMULÁRIO      casou `detect_native_flow` → RESPONDIDA se a resposta MONTA
                (`montar_resposta_de_flow.ok`), ORFA_FUNCIONAL se não. É
                consultado ANTES do passo, e essa é a única divergência
                declarada em relação à ordem do motor (C6).
```

🔴 **O eixo B vale 35 dos 100 pontos porque esta é a única medida que reproduziu.**
O juiz reconstruiu o replay da régua à mão e chegou às mesmas 20 respondidas da
auditoria. É o que separa a régua (20 respondidas) de `mapfre-auto` (0 de 29).

🔴 **E o discriminador é o do PRODUTO, nunca um novo.**
`_tela_pede_alguma_coisa(playbook, texto) -> bool` mora em
`insurer_dispatch_service.py:1974` e lê os `finalize_anchors` do próprio corredor.
*"Um segundo discriminador divergiria em silêncio"* (SPEC-083 §3.3).
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import regua_motor as M   # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(RAIZ, "tests", "corpus", "telas_reais")

RESPONDIDA = "RESPONDIDA"
NOOP = "NOOP"
ORFA_INOCUA = "ORFA_INOCUA"
ORFA_FUNCIONAL = "ORFA_FUNCIONAL"
HANDOFF = "HANDOFF"
CAPTURADA = "CAPTURADA"


class Tela(NamedTuple):
    session_id: str
    wa_timestamp: str
    texto: str
    classe: str
    passo: Optional[str]


class Replay(NamedTuple):
    rota: Any
    telas: List[Tela]
    amostra: str                 # 📊 "AMOSTRA: 5 de 137 sessoes"
    sessoes_no_corpus: int
    sessoes_no_acervo: Optional[int]

    @property
    def respondidas(self) -> int:
        return sum(1 for t in self.telas if t.classe == RESPONDIDA)

    @property
    def noops(self) -> int:
        return sum(1 for t in self.telas if t.classe == NOOP)

    @property
    def orfas_funcionais(self) -> List[Tela]:
        return [t for t in self.telas if t.classe == ORFA_FUNCIONAL]

    @property
    def capturadas(self) -> int:
        """Telas de DESFECHO — quem as lê é `extract_capture_anchors` (C9)."""
        return sum(1 for t in self.telas if t.classe == CAPTURADA)

    @property
    def handoffs(self) -> int:
        """Telas que o corredor manda para humano DE PROPÓSITO (C8)."""
        return sum(1 for t in self.telas if t.classe == HANDOFF)

    @property
    def orfas_inocuas(self) -> int:
        return sum(1 for t in self.telas if t.classe == ORFA_INOCUA)

    @property
    def formularios(self) -> int:
        """Telas de FORMULÁRIO NATIVO — a URA não aceita texto nelas (C6)."""
        return sum(1 for t in self.telas if str(t.passo or "").startswith("flow"))

    @property
    def pedem_algo(self) -> int:
        """Telas que PEDEM alguma coisa — o denominador do determinismo."""
        return self.respondidas + len(self.orfas_funcionais)

    @property
    def determinismo(self) -> Optional[float]:
        """`respondidas ÷ (telas que pedem algo)`. `None` quando não há denominador."""
        if not self.pedem_algo:
            return None
        return self.respondidas / self.pedem_algo


def carregar_corpus(seguradora: str, ramo: str) -> List[Dict[str, Any]]:
    caminho = os.path.join(CORPUS, f"{seguradora}-{ramo}.jsonl")
    if not os.path.exists(caminho):
        return []
    linhas = []
    with open(caminho, encoding="utf-8") as fh:
        for l in fh:
            if l.strip():
                linhas.append(json.loads(l))
    return linhas


def _slots_do_corredor(pb: Dict[str, Any], servico: str,
                       flow: Dict[str, Any]) -> Dict[str, Any]:
    """Os slots que ESTE corredor promete ter, no vocabulário do formulário.

    🔴 Nada aqui é inventado. Os NOMES saem de `required_slots` do subserviço e
    de `slots_com_padrao_do_motor` (o que `new_dispatch_session` injeta), e o
    VALOR é o id da primeira opção do próprio schema capturado. A pergunta que
    isto responde é a única que o corpus consegue responder offline: **o
    corredor chega a COLETAR o campo que o formulário exige?** Quem julga o
    resultado é `montar_resposta_de_flow`, e mais ninguém — a régua não sabe o
    que é responder um formulário, então pergunta a quem sabe.

    ⚠️ O valor é um id de opção VÁLIDO de propósito. Um sentinela (`"x"`)
    cairia em `valor_nao_reconhecido` em todo `RadioButtonsGroup` e faria TODA
    rota reprovar — o item mediria o sentinela, não o corredor.

    ⚠️ E campo condicional não é chutado: quando o campo do `visible_if` não
    está montado, `_flow_visivel` devolve INDETERMINADO = visível, e o
    dependente entra em `missing` junto. É o lado conservador, e é o do motor.
    """
    sub = (pb.get("subservices") or {}).get(M.canonical_subservice(servico)) or {}
    declarados = set(sub.get("required_slots") or [])
    try:
        declarados |= set(M.slots_com_padrao_do_motor(pb, sub) or [])
    except Exception:
        pass
    slots: Dict[str, Any] = {}
    for _tela, comp in M.flow_components(flow):
        nome = str(comp.get("slot") or "")
        if nome and nome in declarados:
            opcoes = comp.get("options") or []
            slots[nome] = str(opcoes[0].get("id")) if opcoes else "sim"
    return slots


def replay(rota, *, sessoes_no_acervo: Optional[int] = None) -> Replay:
    """Roda o corpus de `(seguradora, ramo)` pelo motor, filtrando por serviço."""
    pb = M.get_playbook(rota.ref)
    todas = carregar_corpus(rota.seguradora, rota.ramo)

    # 🔴 SO AS SESSOES QUE PASSARAM POR ESTA ROTA.
    #
    # A SPEC-084 §5.1① e literal: *"Ache as sessoes do corpus que passam por ESTA
    # ROTA"*. Sem o filtro, o replay roda o corpus inteiro de (seguradora, ramo)
    # contra uma rota so -- e as telas de OUTRO servico viram orfas funcionais
    # dela. 📊 Medido: 20 orfas para `maquina_de_lavar` onde a SPEC-083 §4.1
    # espera **1**, porque `allianz-residencial` tem SEIS servicos num corpus.
    #
    # 🔴 A SESSAO SEM SERVICO NAO E TRONCO -- e nao-classificada. E a diferenca
    #    custou a nota da rota de referencia.
    #
    # ⚠️ A primeira versao incluia `servico=None` em TODA rota, presumindo que
    #    fossem as telas de tronco (Termo, CPF, endereco) que valem para todas.
    #    📊 Medido em `allianz-residencial`, depois do teto por rota:
    #
    # ```
    #    maquina_de_lavar   4 sessoes / 102 telas   (as dela)
    #    None               5 sessoes /  61 telas   (a cascata NAO classificou)
    #    juntas           163 telas -> 26 ORFAS FUNCIONAIS -> NAO_RESPONDE
    # ```
    #
    #    A rota de referencia caiu de **64/96 para `NAO_RESPONDE`** por incluir
    #    sessoes de servico desconhecido. Nao-classificado nao e tronco: e uma
    #    sessao inteira de OUTRO servico que a cascata nao soube nomear.
    #
    # ⚠️ **E o tronco de verdade ainda esta por vir:** a SPEC-084 §3.3 manda
    #    classificar TELA a tela em tronco/galho/folha (`--exportar-arvore`).
    #    Quando a arvore existir, as telas de TRONCO das sessoes nao classificadas
    #    voltam para todas as rotas -- que e o que a §2.4 chama de *"as que pagam
    #    por todas"*. Ate la, o filtro e por sessao, e a medida e honesta.
    linhas = [l for l in todas if l.get("servico") == rota.servico]
    telas: List[Tela] = []
    for l in linhas:
        texto = l["text"]
        # ==================================================================
        # 🔴 C6 — A TELA QUE TRAVA O ACIONAMENTO ERA "ÓRFÃ INÓCUA"
        # ==================================================================
        #
        # Quarto ponto cego da mesma família (C8, C9, P-084-30) — e o único
        # que erra para o lado do PRÊMIO, não do castigo.
        #
        # 📊 Medido em 23/08/2026: este arquivo chamava `match_ura_step`,
        #    `detect_handoff_trigger` e `extract_capture_anchors`, e **nunca**
        #    `detect_native_flow`. `regua_motor` nem sequer a reexportava. As 5
        #    telas de formulário nativo do corpus — `hdi/auto/guincho` 3,
        #    `yelum/auto/guincho` 2 — caíam em `_tela_pede_alguma_coisa=False`,
        #    porque o texto que ABRE o flow não tem marca de pergunta: **a
        #    pergunta está DENTRO do formulário**. Saíam do denominador como
        #    ORFA_INOCUA, e o item *"zero órfãs funcionais"* dava 20/20 às duas
        #    rotas enquanto a tela que TRAVA o acionamento não contava.
        #
        # 📊 E o buraco é material, não formal. Com os slots que o corredor
        #    declara coletar, `montar_resposta_de_flow` devolve **ok=False**:
        #
        #      rb_EmGaragemOuEstacionamento  "O veículo está em uma garagem?"
        #      rb_NivelDaRua                 "Em relação ao nível da rua…"
        #      rb_InformacoesLocal           "Qual é a situação do local?"
        #
        #    Três perguntas que ninguém faz ao segurado. O corredor NÃO
        #    responde este formulário — e a régua chamava isso de inócuo.
        #
        # 🔴 Este furo não é o do C8 (a régua punindo o certo). É o inverso, e
        #    o mais perigoso: **a régua PREMIANDO o buraco.**
        #
        # ⚠️ A CLASSE É RESPONDIDA **OU** ORFA_FUNCIONAL, conforme o produto
        #    consiga montar a resposta — decidido por nota: (a) sempre
        #    RESPONDIDA quando monta 35 · (b) sempre ORFA_FUNCIONAL 55 · (c)
        #    classe nova 25 · (d) as duas conforme monte **92**.
        #    (b) nunca ficaria verde: no dia em que o corredor coletar os três
        #    slots, a rota seguiria com "defeitos" no relatório — e régua que
        #    não tem como ficar verde ensina a ignorar régua. (c) seria o furo
        #    com nome novo: HANDOFF e CAPTURADA saem do denominador porque o
        #    corredor NÃO deve responder aquelas telas; aqui ele **deve**.
        #
        # 🔴 E VEM ANTES DO PASSO — a única divergência declarada entre este
        #    replay e a ordem do motor. No motor,
        #    `_responder_formulario_nativo` é consultado DEPOIS do laço de
        #    passos. Um `ura_step` de TEXTO cuja âncora casasse a tela do
        #    formulário faria o motor responder texto e este replay marcar
        #    RESPONDIDA. **A URA não aceita texto nessa tela.** Três linhas de
        #    âncora comprariam os 20 pontos de volta e apagariam o defeito —
        #    que é o incentivo invertido do C8, um nível acima.
        #    📊 Custo medido da inversão: ZERO. Hoje nenhuma tela de flow casa
        #    passo nenhum, e as duas notas são as mesmas com ou sem ela. É
        #    guarda, não é queda.
        flow = M.detect_native_flow(pb, texto)
        passo = (None if flow is not None
                 else M.match_ura_step(pb, texto, subservice=rota.servico))
        if flow is not None:
            montado = M.montar_resposta_de_flow(
                flow, _slots_do_corredor(pb, rota.servico, flow))
            classe = RESPONDIDA if montado.get("ok") else ORFA_FUNCIONAL
            # ⚠️ O nome guarda os campos que faltam mesmo quando é órfã: é o
            #    que faz o executor seguinte ler *"faltam três perguntas ao
            #    segurado"* em vez de *"tem uma tela estranha aqui"*.
            nome = (f"flow:{montado.get('flow_id')}" if montado.get("ok")
                    else "flow_falta:" + ",".join(montado.get("missing") or []))
        elif passo is not None:
            classe = NOOP if passo.get("noop") else RESPONDIDA
            nome = passo.get("step")
        # ==================================================================
        # 🔴 C8 — HANDOFF É UM DESFECHO, E A RÉGUA O CONTAVA COMO BURACO
        # ==================================================================
        #
        # O réplay perguntava só `match_ura_step`. Uma tela que o corredor
        # manda para humano **de propósito** não casa passo nenhum — e caía em
        # `ORFA_FUNCIONAL`, que é *"o defeito"*.
        #
        # 📊 Medido em 22/08/2026: **28 telas em 6 rotas** já disparavam
        #    `detect_handoff_trigger` e eram contadas como falha.
        #
        # 🔴 O efeito é o mesmo perverso do P-084-30: **a régua punia o
        #    handoff correto.** Um executor que otimizasse por ela apagaria os
        #    gatilhos e ganharia ponto — e o corredor passaria a conduzir, em
        #    silêncio, fluxos que exigem uma pessoa (cancelar serviço, alterar
        #    agendamento, sinistro).
        #
        # ⚠️ A ORDEM É A DO MOTOR, e não é escolha de estilo: em
        #    `insurer_dispatch_service`, `detect_handoff_trigger` é consultado
        #    DEPOIS do laço de passos. Se um passo casa, o corredor responde e
        #    o gatilho nunca é lido. Inverter aqui mediria outro corredor.
        #
        # ⚠️ E `HANDOFF` **sai do denominador**, não entra no numerador. Parar
        #    não é responder deterministicamente; contá-lo como acerto inflaria
        #    o determinismo de quem só sabe desistir. O item mede *"das telas
        #    que este corredor TEM de responder, quantas ele responde"* — e uma
        #    tela que ele NÃO deve responder não é dessa população.
        elif M.detect_handoff_trigger(pb, texto):
            classe = HANDOFF
            nome = None
        # ==================================================================
        # 🔴 C9 — A TELA DO DESFECHO CONTAVA COMO BURACO
        # ==================================================================
        #
        # Terceiro ponto cego da mesma familia (C8, P-084-30). A tela de
        # RESUMO com o protocolo nao casa passo nenhum -- **e nao deve**: nao
        # ha o que responder. Quem a le e `extract_capture_anchors`, que tira
        # dela o protocolo e o agendamento que vao para o segurado.
        #
        # 📊 Medido em 22/08/2026 na rota de referencia: as duas telas
        #    contadas como orfa devolviam
        #       protocol=51014008
        #       schedule={'day': 'terca-feira, {data}',
        #                 'periodo': '13:00 as 18:00 (tarde)'}
        #    🔴 **A regua chamava de defeito exatamente a tela que prova que a
        #    rota chegou ao fim.**
        #
        # ⚠️ Vem DEPOIS do handoff, e a ordem importa: uma tela que dispara
        #    gatilho E tem captura e handoff -- o motor para nela, e o que a
        #    regua mede tem de ser o que o motor faz.
        #
        # ⚠️ E sai do denominador, como o HANDOFF: ler nao e responder.
        elif M.extract_capture_anchors(pb, texto):
            classe = CAPTURADA
            nome = None
        else:
            pede = M.tela_pede_alguma_coisa(pb, texto)
            classe = ORFA_FUNCIONAL if pede else ORFA_INOCUA
            nome = None
        telas.append(Tela(l["session_id"], l.get("wa_timestamp") or "",
                          texto, classe, nome))

    sessoes = len({l["session_id"] for l in linhas})
    # ⚠️ *"Todo ponto que depende do corpus carrega a amostra"* (§3.3). Sem isto,
    #    ruído de amostragem lê-se como defeito de rota.
    amostra = (f"AMOSTRA: {sessoes} de {sessoes_no_acervo} sessoes"
               if sessoes_no_acervo else f"AMOSTRA: {sessoes} sessoes")
    return Replay(rota, telas, amostra, sessoes, sessoes_no_acervo)


def imprimir_detalhado(r: Replay, limite: int = 12) -> str:
    L = [f"{r.rota}",
         f"  {r.amostra}",
         f"  telas no corpus ......... {len(r.telas)}",
         f"  RESPONDIDA .............. {r.respondidas}",
         f"  NOOP .................... {r.noops}",
         f"  ORFA_INOCUA ............. {r.orfas_inocuas}",
         f"  HANDOFF ................. {r.handoffs}   (fora do denominador)",
         f"  CAPTURADA ............... {r.capturadas}   (fora do denominador)",
         f"  ORFA_FUNCIONAL .......... {len(r.orfas_funcionais)}   <-- o defeito"]
    d = r.determinismo
    L.append(f"  determinismo ............ "
             + ("sem denominador (nenhuma tela pede algo)" if d is None
                else f"{100*d:.0f}%  ({r.respondidas} de {r.pedem_algo})"))
    if r.orfas_funcionais:
        L.append("\n  as orfas funcionais:")
        for t in r.orfas_funcionais[:limite]:
            L.append(f"    [{t.session_id}] {' '.join(t.texto.split())[:96]}")
        if len(r.orfas_funcionais) > limite:
            L.append(f"    ... e mais {len(r.orfas_funcionais)-limite}")
    return "\n".join(L)
