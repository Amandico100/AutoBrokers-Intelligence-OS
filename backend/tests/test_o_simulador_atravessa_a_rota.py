# -*- coding: utf-8 -*-
"""BATERIA 2 — o simulador atravessa a rota, e responde as DUAS perguntas do §9.5.

> ## Casar a tela não é responder certo. E o guarda do simulador tem de ser capaz
> ## de ficar VERMELHO — senão ele é carimbo, não guarda.

O que este arquivo prova, e nada além:

```
[1] O SIMULADOR CHAMA O MOTOR, e não um regex próprio     CLAUDE.md §9.4
[2] A LINHA DE CONTROLE: um limpo mudo + três defeitos    CLAUDE.md §9.2
    plantados, cada um acusando SÓ a sua regra
[3] A MUTAÇÃO: cada controle fica VERMELHO quando o        CLAUDE.md §9.3 · G7
    defeito que ele guarda é reintroduzido
[4] A TABELA DE DECISÃO: achado grave nunca sai ATENDE     SPEC-119 §5 F4/F5
    SOZINHO, e a ordem §9.5 (errado antes de faltando)
[5] BATERIA 5 por rota: a tela da APÓLICE entra, a do
    PRÉDIO não — e é o que protege quatro rotas
```

🔴 **A SEÇÃO [1] É A MAIS IMPORTANTE, e a razão é medida.** 📊 O CLAUDE.md §9.4
registra um arquivo com **72 asserções verdes** convivendo com um agendamento que
nunca chegava ao cliente, porque tinha **zero** chamadas ao motor. Um simulador
que reimplementasse as três perguntas mediria a si mesmo. Então [1] lê o CÓDIGO
de `simular_corredor.py` por AST e cobra que as definições venham de
`conferir_respostas` e de `regua_motor` — não por leitura, por varredura.
"""
from __future__ import annotations

import ast
import os
import re
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))
sys.path.insert(0, str(RAIZ))

import conferir_respostas as CR   # noqa: E402
import regua_motor as M           # noqa: E402
import replay as RP               # noqa: E402
import simular_corredor as SC     # noqa: E402

SIMULADOR_PY = RAIZ / "scripts" / "simular_corredor.py"


# ═════════════════════════════════════════════════════════════════════════════
# [1] O SIMULADOR CHAMA O MOTOR — CLAUDE.md §9.4
# ═════════════════════════════════════════════════════════════════════════════

def _chamadas_do_arquivo(caminho: Path) -> set:
    """Todas as chamadas `X.y(...)` do arquivo, como `"X.y"` — por AST."""
    arvore = ast.parse(caminho.read_text(encoding="utf-8"))
    fora = set()
    for no in ast.walk(arvore):
        if not isinstance(no, ast.Call):
            continue
        f = no.func
        if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
            fora.add(f"{f.value.id}.{f.attr}")
        elif isinstance(f, ast.Attribute) and isinstance(f.value, ast.Attribute) \
                and isinstance(f.value.value, ast.Name):
            fora.add(f"{f.value.value.id}.{f.value.attr}.{f.attr}")
        elif isinstance(f, ast.Name):
            fora.add(f.id)
    return fora


def test_a_pergunta_a_e_do_replay_e_a_b_do_conferidor():
    """🔴 As duas perguntas vêm de quem já as define. Nada é reimplementado aqui."""
    chamadas = _chamadas_do_arquivo(SIMULADOR_PY)
    # (a) o passo casou a tela? — o replay do produto, e o motor por baixo dele
    assert "RP.replay" in chamadas, "a pergunta (a) tem de ser a do `replay.py`"
    assert "M.match_ura_step" in chamadas, \
        "a atribuição do achado à rota tem de rodar o MOTOR, não comparar nomes"
    # (b) a resposta está confirmada? — as três de `conferir_respostas`
    assert "CR.conferir" in chamadas, "a regra A/B/C sobre o corpus é do conferidor"
    assert "CR.origens_do_slot" in chamadas, "A (origem do slot) é do conferidor"
    assert "CR.decide_pelo_cliente" in chamadas, "B (decide pelo cliente) é do conferidor"
    assert "M.IDS.opcoes_numeradas" in chamadas, \
        "as opções da tela saem do parser do produto (CLAUDE.md §9.4)"


def test_o_simulador_nao_tem_regex_proprio_sobre_a_resposta_do_passo():
    """🔴 CONTROLE do [1]: os únicos padrões do arquivo são os de SITUAÇÃO.

    📊 O arquivo tem padrões — os de condomínio/empresarial/sinistro e o controle
    deles. O que ele NÃO pode ter é padrão que julgue a RESPOSTA de um passo
    (`reply`, `anchor`, `opcao`, `botao`): aquilo é o que `conferir_respostas`
    define, e uma segunda definição divergiria em silêncio.
    """
    fonte = SIMULADOR_PY.read_text(encoding="utf-8")
    # só as linhas de CÓDIGO (o comentário cita telas reais de propósito)
    codigo = [l for l in fonte.splitlines()
              if l.strip() and not l.lstrip().startswith("#")]
    suspeitas = [l for l in codigo
                 if re.search(r"re\.(search|match|fullmatch|compile)", l)
                 and re.search(r"reply|anchor|\\d|bot[aã]o|opcao", l, re.IGNORECASE)]
    assert not suspeitas, ("o simulador está julgando resposta com padrão próprio:\n"
                           + "\n".join(suspeitas))


# ═════════════════════════════════════════════════════════════════════════════
# [2] A LINHA DE CONTROLE — CLAUDE.md §9.2
# ═════════════════════════════════════════════════════════════════════════════

def test_a_linha_de_controle_fecha():
    """O limpo é MUDO e os três defeitos plantados são ACUSADOS, cada um na sua regra."""
    texto, falhas = SC.relatorio_de_controle()
    assert falhas == 0, texto


@pytest.mark.parametrize("nome_esperado", ["limpo", "A", "B", "C"])
def test_cada_controle_acusa_so_a_regra_dele(nome_esperado):
    """🔴 Um por um: sem isto, "0 falhas" poderia ser um conferidor mudo."""
    derivados = CR._slots_derivados()
    alvo = [c for c in SC.corredores_de_controle()
            if (c.esperada or "limpo") == nome_esperado]
    assert alvo, f"o controle {nome_esperado} desapareceu"
    c = alvo[0]
    assert c.tela, ("🔴 a tela REAL saiu do corpus — o controle ficaria verde por "
                    "não ter o que medir, que é o pior verde possível")
    regras = sorted(set(SC.regras_acusadas(c.pb, c.tela, derivados, c.servicos_da_tela)))
    assert regras == ([] if c.esperada is None else [c.esperada]), \
        f"{c.nome}: esperava {c.esperada}, saiu {regras}"


def test_a_tela_de_cada_controle_vem_do_acervo():
    """🔴 O texto da tela vem do acervo, nunca da imaginação (CLAUDE.md §9.4)."""
    corpus = {M._norm(l["text"]) for l in RP.carregar_corpus("allianz", "residencial")}
    for c in SC.corredores_de_controle():
        assert M._norm(c.tela) in corpus, \
            f"{c.nome}: a tela do controle não está em allianz-residencial.jsonl"


# ═════════════════════════════════════════════════════════════════════════════
# [3] AS MUTAÇÕES — G7: cada guarda fica VERMELHO com o defeito reintroduzido
# ═════════════════════════════════════════════════════════════════════════════
#
# 🔴 Aqui a mutação é do PLAYBOOK sintético, não do arquivo do produto: ela roda
#    em memória, não toca disco e não pode apagar edição de ninguém (P-118-14).

def test_mutacao_o_controle_limpo_fica_vermelho_com_cada_defeito():
    """O corredor LIMPO, mutado uma vez por regra, acusa aquela regra."""
    derivados = CR._slots_derivados()
    limpo = [c for c in SC.corredores_de_controle() if c.esperada is None][0]
    base = SC.regras_acusadas(limpo.pb, limpo.tela, derivados, limpo.servicos_da_tela)
    assert base == [], f"o CONTROLE já vem sujo: {base}"

    def _mutado(**troca):
        passo = {**limpo.pb["ura_steps"][0], **troca}
        return {**limpo.pb, "ura_steps": [passo]}

    # A · o slot deixa de ter origem
    pb_a = _mutado(reply="{slot_que_ninguem_preenche}")
    assert sorted(set(SC.regras_acusadas(pb_a, limpo.tela, derivados,
                                         limpo.servicos_da_tela))) == ["A"], \
        "a mutação A não ficou vermelha"

    # C · a mutação vai no sentido INVERSO, e é o único que prova a causa:
    #     tirar `only_subservices` do corredor da C tem de CALÁ-LA. Mutá-la no
    #     sentido direto (pôr `only_subservices` no corredor limpo) não funciona
    #     e não é defeito do guarda: a âncora do limpo é outra tela, e
    #     `match_ura_step` nem chega a casar. 📊 Foi assim que esta mutação ficou
    #     verde na primeira tentativa — detalhe de mutação, não de regra
    #     (CLAUDE.md §9.3, e é o que aconteceu duas vezes na SPEC-118).
    c = [x for x in SC.corredores_de_controle() if x.esperada == "C"][0]
    assert sorted(set(SC.regras_acusadas(c.pb, c.tela, derivados,
                                         c.servicos_da_tela))) == ["C"]
    sem_restricao = {**c.pb, "ura_steps": [{k: v for k, v in c.pb["ura_steps"][0].items()
                                            if k != "only_subservices"}]}
    assert SC.regras_acusadas(sem_restricao, c.tela, derivados, c.servicos_da_tela) == [], \
        "🔴 a C acusa mesmo SEM `only_subservices`: ela está medindo outra coisa"
    # e o outro lado da causa: com a restrição, mas SEM o corpus dizer de que
    # ofício é a tela, a C tem de ficar calada (é o corpus que sabe)
    assert SC.regras_acusadas(c.pb, c.tela, derivados, set()) == [], \
        "🔴 a C acusou sem evidência de corpus — ela virou palpite"


def test_mutacao_a_faixa_do_defeito_deixa_de_ser_atende_sozinho():
    """🔴 Achado GRAVE reintroduzido numa rota limpa → a rota sai de ATENDE SOZINHO."""
    rota = M.rota_de("allianz", "auto", "guincho")
    sim = SC.simular(rota)
    assert sim.faixa == SC.FAIXA_ATENDE, \
        f"a rota de referência mudou de faixa: {sim.faixa} — {sim.motivo}"

    plantado = CR.Achado(True, "B", "allianz", "auto", "um_passo_qualquer",
                         "a constante `2` escolhe entre 3 alternativas de conteúdo",
                         "tela de teste")
    faixa, causa, motivo = SC._faixa(rota, sim.replay, [plantado], sim.desfecho,
                                     sim.situacoes, M.get_playbook(rota.ref))
    assert faixa == SC.FAIXA_HANDOFF and causa == "defeito_de_resposta", \
        f"saiu {faixa}/{causa}"
    assert "um_passo_qualquer" in motivo, \
        "o motivo tem de NOMEAR o passo — o Founder lê o motivo, não a tabela"


def test_a_resposta_errada_vem_antes_da_resposta_que_falta():
    """🔴 A ordem do §9.5: um passo que responde errado é silencioso e chega ao
    cliente; um que trava é barulhento. Com os dois, o motivo é o do errado."""
    rota = M.rota_de("hdi", "auto", "guincho")
    sim = SC.simular(rota)
    assert sim.replay.orfas_funcionais, \
        "esta rota deixou de ter tela órfã — escolha outra para o teste da ORDEM"
    plantado = CR.Achado(True, "A", "hdi", "auto", "passo_calado",
                         "o slot `x` não tem origem", "tela de teste")
    faixa, causa, _ = SC._faixa(rota, sim.replay, [plantado], sim.desfecho,
                                sim.situacoes, M.get_playbook(rota.ref))
    assert (faixa, causa) == (SC.FAIXA_HANDOFF, "defeito_de_resposta"), \
        f"a órfã ganhou da resposta errada: {faixa}/{causa}"


# ═════════════════════════════════════════════════════════════════════════════
# [4] A TABELA DE DECISÃO — e o retrato medido de 27/09/2026
# ═════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def sims():
    return SC.simular_todas()


def test_as_setenta_e_tres_rotas_saem_com_faixa_e_causa(sims):
    assert len(sims) == len(M.rotas())
    for s in sims:
        assert s.faixa in (SC.FAIXA_ATENDE, SC.FAIXA_HANDOFF, SC.FAIXA_FALTA_CAPTURA)
        # 🔴 tudo que NÃO atende sozinho tem de dizer por quê, em português
        if s.faixa != SC.FAIXA_ATENDE:
            assert s.causa, f"{s.rota} sem causa"
            assert len(s.motivo) > 40, f"{s.rota}: motivo curto demais — {s.motivo!r}"
            assert "_" not in s.motivo.split("`")[0], \
                f"{s.rota}: nome de chave no meio da frase — {s.motivo!r}"


def test_rota_sem_uma_tela_no_corpus_e_falta_captura(sims):
    """🔴 CONTROLE da faixa ①, e ele é o gate G2 da SPEC-119 em forma de teste.

    📊 Medido em 27/09/2026 (`simular_corredor.py --todas`): `mapfre/auto/guincho`
    tem **ZERO** telas no corpus regerado pela F2 — `mapfre-auto.jsonl` traz 100
    linhas sem etiqueta e 14 de `carro_reserva`, e nenhuma de guincho. A rota
    continua SEM CORPUS, e é isso que este teste registra: não é que o robô falhe,
    é que não há conversa etiquetada para medir.
    """
    seca = [s for s in sims if not s.replay.telas]
    assert seca, "nenhuma rota sem corpus — o controle desta faixa ficou sem caso"
    for s in seca:
        assert (s.faixa, s.causa) == (SC.FAIXA_FALTA_CAPTURA, "sem_corpus"), \
            f"{s.rota} saiu {s.faixa}/{s.causa}"


def test_a_rota_que_encaminha_e_handoff_por_desenho_nao_por_defeito(sims):
    """A Tokio entrega LINK (SPEC-118) — e isso é o produto certo, não uma falha."""
    porta = [s for s in sims if s.causa == "por_desenho_link"]
    assert porta, "nenhuma rota `encaminha` — o controle desta faixa sumiu"
    for s in porta:
        assert s.faixa == SC.FAIXA_HANDOFF
        assert M.CP.subservice_outcome(M.get_playbook(s.rota.ref),
                                       s.rota.servico) == M.CP.OUTCOME_ENCAMINHA


def test_o_patamar_medido_em_27_09_nao_cai(sims):
    """📊 O RETRATO, medido em 27/09/2026 com `simular_corredor.py --todas`:

    ```
    ATENDE SOZINHO    25 de 73
    HANDOFF            2 de 73   (os dois por desenho: porto/vidros e tokio/guincho)
    FALTA CAPTURA     46 de 73   (31 sem corpus · 9 tela órfã · 6 sem desfecho)
    ```

    🔴 O gate da SPEC-119 é o PATAMAR, não o número (G4): o teste cobra **≥ 25**
    e exige que a rota de REFERÊNCIA do protocolo §7.1 — `allianz/auto/guincho` —
    esteja entre as que atendem. Um número exato viraria vermelho no dia em que a
    F5 acrescentar uma rota, e teste que fica vermelho por crescer ensina a
    ignorar teste.
    """
    atendem = {f"{s.rota.seguradora}/{s.rota.ramo}/{s.rota.servico}"
               for s in sims if s.faixa == SC.FAIXA_ATENDE}
    assert len(atendem) >= 25, f"o patamar caiu: {len(atendem)} — {sorted(atendem)}"
    assert "allianz/auto/guincho" in atendem, \
        "a rota de REFERÊNCIA do protocolo §7.1 saiu de ATENDE SOZINHO"


def test_atende_sozinho_exige_desfecho_e_zero_orfa_e_zero_grave(sims):
    """🔴 As três condições da SPEC-119 §5 F5③, conferidas uma a uma."""
    for s in sims:
        if s.faixa != SC.FAIXA_ATENDE:
            continue
        assert s.desfecho.chegou, f"{s.rota} atende sozinho sem nunca chegar ao fim"
        assert s.desfecho.sessoes, f"{s.rota} sem a conversa NOMEADA do desfecho"
        assert not s.replay.orfas_funcionais, f"{s.rota} atende com tela órfã"
        assert not s.graves, f"{s.rota} atende com achado grave: {s.graves}"
        assert not s.situacoes_furadas, f"{s.rota} atende com bateria 5 furada"


def test_nenhum_achado_do_conferidor_desaparece(sims):
    """🔴 SPEC-083 §7: *"truncar calado lê-se como 'cobrimos tudo'"*.

    Um achado que nenhuma rota reivindicou continua visível — e o total
    reivindicado + fora de rota tem de cobrir tudo o que o conferidor acusa.
    """
    derivados = CR._slots_derivados()
    do_conferidor = set()
    for seg, ramo in sorted({(s.rota.seguradora, s.rota.ramo) for s in sims}):
        for a in CR.conferir(seg, ramo, derivados):
            do_conferidor.add((a.regra, a.passo, a.porque))
    reivindicados = {(a.regra, a.passo, a.porque) for s in sims for a in s.achados}
    orfaos = {(a.regra, a.passo, a.porque) for a in SC.achados_fora_de_rota(sims)}
    assert do_conferidor == (reivindicados | orfaos), \
        f"achados perdidos: {sorted(do_conferidor - (reivindicados | orfaos))}"


# ═════════════════════════════════════════════════════════════════════════════
# [5] BATERIA 5 POR ROTA — a apólice entra, o prédio não
# ═════════════════════════════════════════════════════════════════════════════

def test_a_tela_da_apolice_entra_e_a_do_predio_nao():
    """🔴 A DISTINÇÃO QUE PROTEGE QUATRO ROTAS, e ela é medida.

    📊 As duas telas reais, `_norm`-adas, com o `session_id` ao lado:

    ```
    ① A APÓLICE   allianz-residencial c6b63f95
       "Qual seguro deseja utilizar? 1 - Residencial: … 2 - Condomínio: para
        áreas comuns e estrutura … 3 - Empresarial: …"          -> ENTRA
    ② O PRÉDIO    hdi-residencial 26c0546f · yelum-residencial af3b817e
       "Sua residência é uma casa individual ou está localizada em um
        condomínio? Botão 1: Casa Botão 2: Condomínio"           -> FICA FORA
    ```

    Um apartamento é "condomínio" na ② e **Residencial** na ①. Mandar a ② para uma
    pessoa tiraria `hdi/residencial/*` e `yelum/residencial/*` do ar para proteger
    um caso que não existe.
    """
    apolice = next((l for l in RP.carregar_corpus("allianz", "residencial")
                    if re.search(r"qual seguro deseja utilizar", M._norm(l["text"]))
                    and "condominio" in M._norm(l["text"])), None)
    assert apolice, "a tela da APÓLICE saiu do acervo"
    sit = SC.situacao_que_vai_para_gente(apolice["text"])
    assert sit and sit[0] == "apolice_de_condominio_ou_empresa", \
        f"a tela da apólice não é reconhecida: {sit}"

    predios = [l for base in ("hdi-residencial", "yelum-residencial")
               for l in RP.carregar_corpus(*base.split("-"))
               if re.search(r"casa (?:individual )?ou (?:est[áa]|fica)", M._norm(l["text"]))]
    assert predios, "a tela do PRÉDIO saiu do acervo — o controle perdeu o caso"
    for l in predios:
        assert SC.situacao_que_vai_para_gente(l["text"]) is None, (
            f"🔴 a pergunta de LOGÍSTICA entrou na bateria 5 (sessão "
            f"{l['session_id']}): isso tira quatro rotas do ar")


def test_o_menu_que_so_LISTA_sinistro_nao_entra():
    """🔴 CONTROLE do padrão de sinistro — e ele já custou caro no produto.

    📊 `corridor_playbooks.py` registra que o gatilho `sinistro` CRU derrubava
    *"mais da metade das sessões boas"*. O menu raiz da Porto LISTA "Sinistro de
    automóvel" como opção vizinha, e o passo `menu_como_ajudar` responde
    "Serviços para veículo" — que é o oposto de abrir sinistro pelo cliente.

    ⚠️ Este teste nasceu de um falso positivo REAL: a primeira versão do padrão
    tinha `sinistro de automovel` e marcou 4 rotas da Porto como furadas
    (sessões 67296ad9, d0d64bfc, a9560e3a, b1ff65f2).
    """
    menus = [l for l in RP.carregar_corpus("porto", "auto")
             if M._norm(l["text"]).startswith("como eu posso te ajudar")
             and "sinistro" in M._norm(l["text"])]
    assert menus, "o menu raiz da Porto saiu do acervo"
    for l in menus:
        assert SC.situacao_que_vai_para_gente(l["text"]) is None, (
            f"🔴 o menu que só LISTA sinistro entrou na bateria 5 (sessão "
            f"{l['session_id']}) — isso tira 4 rotas da Porto do ar")


def test_toda_situacao_da_bateria_5_vai_para_uma_pessoa(sims):
    """🔴 O pedido explícito do Founder, conferido rota a rota."""
    furadas = [(s.rota, x) for s in sims for x in s.situacoes if not x[3]]
    assert not furadas, "\n".join(
        f"{r} [{c}] sessão {ses}: {caminho}" for r, (c, ses, _t, _v, caminho) in furadas)


def test_o_guarda_da_bateria_5_roda_com_o_CASO_de_condominio():
    """🔴 SEM ISTO O GUARDA NÃO TEM COMO FICAR VERMELHO — CLAUDE.md §9.3.

    📊 Medido em 27/09/2026: com `slots={}`, a tela da apólice cai em
    `ramo_indeterminado` (tecla vazia → pessoa) **em qualquer versão do código**,
    inclusive na que respondia "2" sozinha. O guarda ficaria verde por motivo
    errado — foi assim que a SPEC-118 teve dois verdes falsos.

    A pergunta da bateria 5 só existe quando a apólice **é** de condomínio.
    """
    assert SC._SLOTS_DA_SITUACAO["apolice_de_condominio_ou_empresa"], \
        "os slots do caso de condomínio sumiram: o guarda virou carimbo"
    pb = M.get_playbook("allianz-residencial-whatsapp@v1")
    tela = next(l["text"] for l in RP.carregar_corpus("allianz", "residencial")
                if re.search(r"qual seguro deseja utilizar", M._norm(l["text"]))
                and "condominio" in M._norm(l["text"]))
    # com o caso de condomínio, o caminho tem de ser o NOVO, não o do slot vazio
    vai, caminho = SC.o_produto_manda_para_gente(
        pb, tela, "encanador",
        slots=SC._SLOTS_DA_SITUACAO["apolice_de_condominio_ou_empresa"])
    assert vai and "apolice_de_condominio_ou_empresa" in caminho, caminho
    # e o CONTROLE: com a apólice RESIDENCIAL o robô segue sozinho, como sempre
    vai_resid, caminho_resid = SC.o_produto_manda_para_gente(
        pb, tela, "encanador", slots={"qual_seguro_opcao": "Residencial"})
    assert not vai_resid, (
        "🔴 CONTROLE VERMELHO: a apólice RESIDENCIAL também está indo a uma "
        f"pessoa — a trava pegou largo demais. {caminho_resid}")


# ═════════════════════════════════════════════════════════════════════════════
# 🔴 §13.9 — o produto é de QUALQUER corretora
# ═════════════════════════════════════════════════════════════════════════════

def test_o_simulador_nao_tem_nome_de_corretora_nem_pii():
    """Nenhum nome de corretora, atendente, CPF, telefone ou placa no arquivo."""
    fonte = SIMULADOR_PY.read_text(encoding="utf-8")
    proibidos = ("resulta", "autofleet", "amandus", "regina", "saionara")
    achados = [p for p in proibidos if p in fonte.lower()]
    assert not achados, f"§13.9: nome de cliente/funcionário no código: {achados}"
    assert not re.search(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b", fonte), "CPF no código"
    assert not re.search(r"\b55\d{10,11}\b", fonte), "telefone no código"
