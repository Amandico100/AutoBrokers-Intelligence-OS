# -*- coding: utf-8 -*-
"""CONSERTO B da SPEC-119 — o que chega ao SEGURADO e à SEGURADORA.

> ## Casar a tela não é responder certo. E cada defeito aqui ficava VERDE.

Seis defeitos, todos medidos em 28/09/2026, todos com a tela REAL do acervo ao
lado. Cada um tem a sua MUTAÇÃO: o guarda tem de ficar VERMELHO quando o defeito
é reintroduzido, senão ele é carimbo (CLAUDE.md §9.3).

```
[1] A SEGUNDA TELA DE TRÊS OPÇÕES   `menu_solicitar_para` respondia "1" onde a
    opção 2 é CONDOMÍNIO — e a justificativa ao lado descrevia OUTRA tela
[3] "ABRIR UM NOVO ATENDIMENTO"     era classificado como NAVEGAÇÃO, e a rede de
    segurança (`NAO_SEI`) era DESLIGADA POR INSTRUÇÃO ali
[4] O VOCABULÁRIO DA NAVEGAÇÃO      aceitava `condominio`/`empresarial`/
    `residencial` sem nenhum guarda reclamar (103 asserções verdes)
[5] O RAMO NOVO DO SENTINELA        entregava dossiê e avisava o segurado, e não
    ANUNCIAVA no feed quando as duas coisas falhavam
[6] A TRAVA DO CONDOMÍNIO           era casamento EXATO: "Seguro Condomínio" e
    "Empresarial / PME" seguiam sozinhos
[7] O FISCAL E O EXTRATOR           8 de 10 rascunhos defeituosos passavam, e o
    extrator FABRICAVA um deles (`str(content)` de um dict)
```

🔴 **As linhas de CONTROLE são o que dá direito à conclusão** (CLAUDE.md §9.2):
a apólice RESIDENCIAL continua seguindo sozinha, a tela do PRÉDIO ("casa
individual ou condomínio?") continua fora da trava, e `Continuar`/`Voltar`
continuam navegando.
"""
from __future__ import annotations

import ast
import asyncio
import json
import os
import re
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
os.environ.setdefault("INSURER_DISPATCH_LIVE", "false")

from app.providers import policy_data_provider as PDP  # noqa: E402
from app.services import corridor_playbooks as CP   # noqa: E402
from app.services import insurer_dispatch_service as D  # noqa: E402

CORPUS = RAIZ / "tests" / "corpus" / "telas_reais"
REF_RESID = "allianz-residencial-whatsapp@v1"


def _carregar_pelo_caminho(nome: str, relativo: str):
    """O MÓDULO, carregado pelo ARQUIVO — o mesmo código, nunca uma cópia.

    ⚠️ `from app.agents import utils` executa `app/agents/__init__.py`, que
    importa o grafo inteiro e o cliente do Supabase. 📊 Rodando junto com
    `test_o_simulador_atravessa_a_rota.py` isso dá `ImportError: cannot import
    name 'get_supabase_client'`, porque `scripts/regua_motor.py` instala módulos
    ESPELHO para `app`, `app.services` e `app.core` em `sys.modules`. Carregar
    pelo caminho mede o mesmo arquivo sem acordar o grafo.
    """
    import importlib.util as iu
    spec = iu.spec_from_file_location(nome, RAIZ / relativo)
    modulo = iu.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


AGU = _carregar_pelo_caminho("_agentes_utils_119", "app/agents/utils.py")


def telas(nome: str):
    caminho = CORPUS / f"{nome}.jsonl"
    if not caminho.exists():
        return []
    with open(caminho, encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


def uma_tela(nome: str, padrao: str, extra: str = ""):
    """A primeira tela REAL do acervo que casa o padrão, com o `session_id`."""
    for l in telas(nome):
        n = CP._norm(l["text"])
        if re.search(padrao, n, re.IGNORECASE | re.DOTALL) and (
                not extra or re.search(extra, n, re.IGNORECASE | re.DOTALL)):
            return l
    return None


# ═════════════════════════════════════════════════════════════════════════════
# [1] A SEGUNDA TELA DE TRÊS OPÇÕES — `menu_solicitar_para`
# ═════════════════════════════════════════════════════════════════════════════
#
# 📊 A tela real, `allianz-residencial.jsonl`, sessão `2540f42f`:
#
#     "Você gostaria de solicitar serviços de assistência para:
#      *1 -* Residência  *2 -* Condomínio  *3 -* Empresa"
#
# 🔴 O passo respondia a constante `1`, e NÃO TINHA GUARDA NENHUM:
#    `grep -rln menu_solicitar_para backend/tests/` não achava um arquivo.

TELA_SOLICITAR_PARA = uma_tela("allianz-residencial",
                               r"solicitar servi[çc]os de assist[êe]ncia para",
                               r"condominio")


def test_o_acervo_tem_a_segunda_tela_de_tres_opcoes():
    """📊 CONTROLE ZERO: sem a tela real, tudo abaixo mediria imaginação."""
    assert TELA_SOLICITAR_PARA, (
        "a tela `solicitar serviços de assistência para` com Condomínio saiu do "
        "acervo — este arquivo inteiro ficaria verde por não ter o que medir")
    opcoes = dict(D.opcoes_numeradas(TELA_SOLICITAR_PARA["text"]))
    assert len(opcoes) == 3, f"a tela deixou de ter 3 opções: {opcoes}"
    assert CP._norm(opcoes["2"]).startswith("condominio"), (
        f"🔴 a opção 2 desta tela deixou de ser Condomínio: {opcoes} — a premissa "
        f"do conserto mudou")


def _passo_de(tela: str, servico: str = "encanador"):
    return CP.match_ura_step(CP.get_playbook(REF_RESID), tela, subservice=servico)


@pytest.mark.parametrize("rotulo,tecla,destino", [
    ("Residencial", "1", "ura"),      # 🔴 CONTROLE: o residencial segue sozinho
    ("Condomínio", "2", "humano"),
    ("Empresarial", "3", "humano"),
])
def test_a_tecla_desta_tela_vem_do_caso_e_o_condominio_para(rotulo, tecla, destino):
    """🔴 O defeito, e o controle dele, na mesma tabela.

    Com `reply: "1"` fixo, `resolver_tecla` devolvia **None** (ela só olha
    `{algo_opcao}`), a trava `_apolice_de_areas_comuns` nunca rodava, e todo
    chamado de ÁREAS COMUNS de condomínio abria na apólice da UNIDADE.
    """
    passo = _passo_de(TELA_SOLICITAR_PARA["text"])
    assert passo and passo.get("step") == "menu_solicitar_para", passo
    sessao = {"slots": {"qual_seguro_opcao": rotulo}, "origem_das_teclas": {}}
    t = D.resolver_tecla(CP.get_playbook(REF_RESID), passo, sessao,
                         TELA_SOLICITAR_PARA["text"])
    assert t is not None, (
        "🔴 `resolver_tecla` voltou a devolver None nesta tela — a constante "
        "voltou, e com ela a trava do condomínio deixa de alcançar o passo")
    assert (t["valor"], t["destino"]) == (tecla, destino), t
    if destino == "humano":
        assert t["reason"] == "apolice_de_condominio_ou_empresa", t


def test_mutacao_a_constante_de_volta_deixa_a_trava_sem_alcance():
    """🔴 O guarda fica VERMELHO com o defeito reintroduzido (G7).

    ⚠️ A mutação é do PASSO em memória, não do arquivo: ela não toca disco e não
    pode apagar edição de ninguém (P-118-14).
    """
    passo = dict(_passo_de(TELA_SOLICITAR_PARA["text"]))
    mutado = {**passo, "reply": "1"}
    mutado.pop("requires", None)
    sessao = {"slots": {"qual_seguro_opcao": "Condomínio"}, "origem_das_teclas": {}}
    assert D.resolver_tecla(CP.get_playbook(REF_RESID), mutado, sessao,
                            TELA_SOLICITAR_PARA["text"]) is None, (
        "🔴 a mutação não ficou vermelha: `resolver_tecla` devolveu algo para uma "
        "constante, então este guarda não estava provando o que diz provar")


def test_a_justificativa_desta_tela_nao_pode_descrever_outra():
    """🔴 O corolário do §9.5, no lugar exato onde ele estava quebrado.

    A justificativa antiga dizia *"1-Residência 2-Veículo"* — uma tela de DUAS
    opções — enquanto o acervo mostra três e a 2 é Condomínio.
    """
    passo = _passo_de(TELA_SOLICITAR_PARA["text"])
    just = str(passo.get("constante_justificada") or "")
    assert "veiculo" not in CP._norm(just), (
        f"🔴 a justificativa voltou a descrever a tela de DUAS opções: {just!r}")


# ═════════════════════════════════════════════════════════════════════════════
# [3] A TELA QUE PERGUNTA "ABRIR UM NOVO ATENDIMENTO?" NÃO É NAVEGAÇÃO
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("frase,veta", [
    ("abrir atendimento", True),
    ("abrir novo atendimento", True),        # 🔴 a redação REAL
    ("abrir um novo atendimento", True),     # 🔴 a redação REAL
    ("abrir um novo chamado", True),
    ("reagendado", True),
    ("reagendar", True),
    ("agendado", True),
    # 🔴 CONTROLE: `encerrar`, `desistir`, `voltar` e `sair` são RÓTULOS de
    #    navegação, e o veto tem de continuar fora deles — `mapfre-auto
    #    b979f244` só PODE ser conduzida porque `encerrar` não veta.
    ("encerrar", False),
    ("desistir", False),
    ("voltar", False),
    ("sair", False),
])
def test_o_veto_alcanca_a_redacao_real_de_abrir(frase, veta):
    assert bool(D._RX_ABRE_AGENDA_CANCELA.search(frase)) is veta, frase


TELA_NOVO_ATENDIMENTO = uma_tela("yelum-auto",
                                 r"abrir um novo atendimento ou continuar")


def test_a_tela_do_novo_atendimento_decide_e_nao_conduz():
    """🔴 Duas respostas, dois desfechos: continuar o acionamento em curso, ou
    abrir um SEGUNDO e perder o protocolo do primeiro.

    ⚠️ E o preço é maior do que parece: quando a classe é `conduz/navegacao`, o
    prompt do modelo recebe *"⛔ NÃO responda NAO_SEI aqui"* — a rede de
    segurança é desligada POR INSTRUÇÃO exatamente nesta tela.
    """
    assert TELA_NOVO_ATENDIMENTO, "a tela do novo atendimento saiu do acervo"
    classe = D.classe_da_tela(None, TELA_NOVO_ATENDIMENTO["text"], slots={})
    assert classe["classe"] != CP.CLASSE_CONDUZ, (
        f"🔴 a tela que pergunta se abre um NOVO atendimento voltou a ser "
        f"conduzida (sessão {TELA_NOVO_ATENDIMENTO['session_id']}): {classe}")
    assert classe["chave"] != "navegacao", classe


def test_a_tela_de_outro_servico_da_tokio_tambem_decide():
    """⚠️ A mesma falha, na tokio: a opção 1 é *Outro serviço*."""
    tela = uma_tela("tokio-auto", r"posso te ajudar em algo mais")
    if not tela:
        pytest.skip("a tela `posso te ajudar em algo mais` saiu do acervo da tokio")
    classe = D.classe_da_tela(None, tela["text"], slots={})
    assert classe["chave"] != "navegacao", (
        f"🔴 *Outro serviço* voltou a ser navegação (sessão "
        f"{tela['session_id']}): {classe}")


# ═════════════════════════════════════════════════════════════════════════════
# [4] O VOCABULÁRIO DA NAVEGAÇÃO TEM GUARDA — e ele cobre as palavras que doem
# ═════════════════════════════════════════════════════════════════════════════

def test_o_vocabulario_de_hoje_passa_pelo_proprio_guarda():
    """📊 CONTROLE: o guarda não pode reprovar a lista que existe."""
    recusadas = [(e, CP.entrada_pode_ser_navegacao(e))
                 for e in CP._VOCABULARIO_DE_NAVEGACAO
                 if CP.entrada_pode_ser_navegacao(e)]
    assert not recusadas, f"o guarda reprova a lista de hoje: {recusadas}"


@pytest.mark.parametrize("palavra", [
    # ① rótulo de RAMO — a mutação M-RT1c do red team, que dava 103 verdes
    "condominio", "empresarial", "residencial", "casa", "apartamento",
    # ② rótulo que COMEÇA TRABALHO NOVO — as quatro que saíram da lista
    "novo atendimento", "abrir novo atendimento", "outro servico",
    "outros servicos", "abrir chamado",
])
def test_mutacao_palavra_de_conteudo_nao_entra_no_vocabulario(palavra):
    """🔴 O guarda que faltava. Sem ele, a mutação M-RT1c ficava VERDE."""
    motivo = CP.entrada_pode_ser_navegacao(palavra)
    assert motivo, (
        f"🔴 {palavra!r} entraria no vocabulário da navegação sem ninguém "
        f"reclamar — é a mutação M-RT1c do red team, 103 asserções verdes")


@pytest.mark.parametrize("palavra", [
    "continuar", "voltar", "voltar ao menu", "sair", "encerrar atendimento",
    "menu principal", "mais opcoes", "nenhuma das anteriores",
])
def test_controle_a_navegacao_de_verdade_continua_entrando(palavra):
    """🔴 CONTROLE: um guarda que recusasse tudo não guardaria nada."""
    assert CP.entrada_pode_ser_navegacao(palavra) is None, \
        CP.entrada_pode_ser_navegacao(palavra)


def test_a_tela_dos_tres_ramos_nunca_e_navegacao():
    """🔴 O efeito da M-RT1c no PRODUTO, e não só na lista."""
    tela = ("Para continuar, escolha: *1 -* Residencial *2 -* Condominio "
            "*3 -* Empresarial")
    classe = D.classe_da_tela(None, tela, slots={})
    assert classe["chave"] != "navegacao", (
        f"🔴 a tela que escolhe o RAMO virou navegação: {classe}")


# ═════════════════════════════════════════════════════════════════════════════
# [5] O RAMO NOVO DO SENTINELA ANUNCIA NO FEED DA CORRETORA
# ═════════════════════════════════════════════════════════════════════════════
#
# 🔴 O ramo de ESGOTAMENTO tem os TRÊS desfechos desde 18/08/2026, inclusive o
#    pior: *"🔴 Acionamento travou, a equipe NÃO foi avisada e o segurado TAMBÉM
#    NÃO … Ligue para ele."*. O ramo novo (`tela_que_decide`) entrega o mesmo
#    dossiê e faz o mesmo aviso, e escrevia só um `logger.warning`.

VIGIA_PY = RAIZ / "app" / "tasks" / "dispatch_watchdog.py"


def _funcao(nome: str):
    arvore = ast.parse(VIGIA_PY.read_text(encoding="utf-8"))
    for no in ast.walk(arvore):
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)) and no.name == nome:
            return no
    return None


def test_os_dois_ramos_de_handoff_chamam_o_MESMO_anunciador():
    """🔴 Um só escritor (CLAUDE.md §5) — lido por AST, não por leitura.

    ⚠️ E os dois ramos moram na MESMA função (`_tentar_recuperar`), então a
    varredura conta as CHAMADAS: precisa haver duas.
    """
    fonte = VIGIA_PY.read_text(encoding="utf-8")
    arvore = ast.parse(fonte)
    chamadas = [n for n in ast.walk(arvore)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                and n.func.id == "_anunciar_o_handoff_no_feed"]
    assert len(chamadas) >= 2, (
        f"🔴 só {len(chamadas)} ramo(s) do Sentinela anuncia(m) no feed — o ramo "
        f"que não anuncia deixa o PIOR desfecho silencioso para a corretora")
    assert _funcao("_anunciar_o_handoff_no_feed"), \
        "o anunciador do feed sumiu do Vigia"


def test_o_anunciador_tem_os_TRES_desfechos_e_o_pior_manda_ligar():
    """🔴 Três desfechos, três frases DIFERENTES — feed que mente encerra a
    investigação antes ainda de a flag mentir."""
    ditas = []

    async def _log(company_id, canal, titulo, corpo):
        ditas.append((titulo, corpo))

    import app.services.activity_log as AL
    original = AL.log_activity
    AL.log_activity = _log
    try:
        from app.tasks.dispatch_watchdog import _anunciar_o_handoff_no_feed as anunciar
        for dossie, avisado in ((True, False), (False, True), (False, False)):
            asyncio.get_event_loop_policy().new_event_loop().run_until_complete(
                anunciar("co-1", dossie, avisado, "Travou", "Travou"))
    finally:
        AL.log_activity = original

    assert len(ditas) == 3, ditas
    assert len({t for t, _ in ditas}) == 3, f"duas frases iguais: {ditas}"
    pior = ditas[-1]
    assert "TAMBÉM NÃO" in pior[0], pior
    assert "Ligue para ele" in pior[1], (
        "🔴 o pior desfecho parou de mandar a corretora LIGAR para o segurado")


# ═════════════════════════════════════════════════════════════════════════════
# [6] A TRAVA DO CONDOMÍNIO CASA POR CONTENÇÃO — com o controle multi-ramo
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("rotulo,familia", [
    ("Seguro Condomínio", "cond"),
    ("Condomínio (áreas comuns)", "cond"),
    ("Empresarial / PME", "empr"),
    ("Condomínio", "cond"),
    ("Residencial", "resi"),
    ("Residência", "resi"),
    # 🔴 AS DUAS LINHAS DE CONTROLE, e elas valem tanto quanto as de cima:
    #    um rótulo que nomeia 2+ famílias NÃO decide ramo nenhum.
    ("Residência, Condomínio ou Empresa", None),
    ("Sua residência é uma casa individual ou está localizada em um condomínio?",
     None),
])
def test_o_ramo_dentro_do_rotulo(rotulo, familia):
    assert PDP.familia_de_ramo_do_rotulo(rotulo) == familia, \
        PDP.familia_de_ramo_do_rotulo(rotulo)


def test_a_contencao_e_por_palavra_inteira():
    """⛔ 📊 SPEC-094.1: `SURA` casa dentro de `ASSURANCE`, e casamento parcial
    produz catálogo errado. O guarda que fecha essa porta."""
    for falso in ("Assurance", "Residencialidade", "Empresarialmente"):
        assert PDP.familia_de_ramo_do_rotulo(falso) is None, falso


def test_controle_a_tela_do_predio_continua_fora_da_trava():
    """🔴 Um apartamento é *condomínio* na pergunta do PRÉDIO e **Residencial**
    na pergunta da APÓLICE. Mandar a primeira para uma pessoa tiraria
    `hdi/residencial/*` e `yelum/residencial/*` do ar."""
    achou = False
    for base in ("hdi-residencial", "yelum-residencial"):
        tela = uma_tela(base, r"casa (?:individual )?ou (?:est[áa]|fica)")
        if not tela:
            continue
        achou = True
        assert PDP.familia_de_ramo_do_rotulo(" ".join(tela["text"].split())) is None, (
            f"🔴 a pergunta de LOGÍSTICA virou decisão de ramo (sessão "
            f"{tela['session_id']})")
    assert achou, "a tela do PRÉDIO saiu do acervo — o controle perdeu o caso"


# ═════════════════════════════════════════════════════════════════════════════
# [7] O EXTRATOR NÃO SERIALIZA OBJETO, E O FISCAL RECUSA O QUE NÃO É FRASE
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("conteudo,esperado", [
    ([{"text": "1"}], "1"),                              # bloco sem `type`
    ([{"type": "output_text", "text": "1"}], "1"),       # Responses API da OpenAI
    ({"type": "text", "text": "1"}, "1"),                # 🔴 um DICT, não lista
    ([{"type": "text", "text": "ok"}], "ok"),
    ("ok", "ok"),
    (None, ""),
    ([{"type": "text"}], ""),                            # `text` sem a chave
    ([{"type": "tool_use", "name": "x"}], ""),
    ([{"type": "reasoning", "text": "penso"},
      {"type": "text", "text": "ok"}], "ok"),            # 🔴 raciocínio fica FORA
])
def test_o_extrator_devolve_texto_ou_nada(conteudo, esperado):
    assert AGU.extract_text_from_content(conteudo) == esperado


def test_mutacao_o_extrator_nunca_serializa_objeto_para_a_URA():
    """🔴 O `return str(content)` era o defeito: o `repr` de um dict é CURTO, e
    o fiscal aprovava um `"{'type': 'text', 'text': '1'}"` rumo à seguradora.

    Falha FECHADA (string vazia, que o fiscal recusa) vence falha ABERTA
    (`repr`, que ele aceita).
    """
    class Exotico:
        def __repr__(self):
            return "<objeto que NAO e resposta>"

    saida = AGU.extract_text_from_content(Exotico())
    assert saida == "", f"🔴 o extrator voltou a serializar objeto: {saida!r}"
    assert "return str(content)" not in (RAIZ / "app" / "agents" / "utils.py"
                                         ).read_text(encoding="utf-8"), \
        "🔴 o `str(content)` voltou ao extrator"


def _fiscal(rascunho: str):
    return D.guard_human_phase_reply(
        rascunho,
        {"slots": {}, "captured": {}, "playbook_ref": REF_RESID},
        insurer_message="Digite o CPF do titular")


@pytest.mark.parametrize("rascunho", [
    "[{'type': 'text', 'text': '1'}]",     # repr de lista de blocos
    "{'type': 'text', 'text': '1'}",       # repr de dict — o que o extrator fazia
    '{"type":"tool_use","name":"x"}',      # JSON de tool_use
    "```\n1\n```",                         # markdown com cerca
    "[]",
])
def test_o_fiscal_recusa_o_que_nao_e_frase(rascunho):
    v = _fiscal(rascunho)
    assert not v["ok"] and v["reason"] == "nao_e_frase", v


@pytest.mark.parametrize("rascunho", ["1", "Sim", "Sim, pode seguir", "Agora"])
def test_controle_o_fiscal_continua_aprovando_resposta_de_verdade(rascunho):
    """🔴 CONTROLE: um fiscal que recusasse tudo tiraria o produto do ar."""
    assert _fiscal(rascunho)["ok"], _fiscal(rascunho)


# ═════════════════════════════════════════════════════════════════════════════
# 🔴 §13.9 — o produto é de QUALQUER corretora
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("relativo", [
    "app/agents/utils.py",
    "app/providers/policy_data_provider.py",
    "app/tasks/dispatch_watchdog.py",
])
def test_o_que_este_conserto_tocou_nao_tem_nome_de_corretora_nem_pii(relativo):
    """🔴 §13.9: o produto é de QUALQUER corretora.

    ⚠️ A varredura é sobre os ARQUIVOS CONSERTADOS, nunca sobre este teste: um
    arquivo que se mede a si mesmo fica vermelho pela própria lista de palavras
    proibidas — e guarda que falha por se ler ensina a ignorar guarda.
    ⛔ `corridor_playbooks.py` e `insurer_dispatch_service.py` ficam de fora
    porque já têm guarda próprio e citam telas reais com marcações do acervo.
    """
    fonte = (RAIZ / relativo).read_text(encoding="utf-8").lower()
    proibidos = ("resulta ", "autofleet", "amandus", "saionara")
    assert not [p for p in proibidos if p in fonte], relativo
    assert not re.search(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b", fonte), f"CPF em {relativo}"
    assert not re.search(r"\b55\d{10,11}\b", fonte), f"telefone em {relativo}"
