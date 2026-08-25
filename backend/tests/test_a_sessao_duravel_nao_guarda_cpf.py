# -*- coding: utf-8 -*-
"""O retrato durável do acionamento não guarda CPF — SPEC-085, FASE 1.

🔴 ESTE ARQUIVO FOI ESCRITO **ANTES** DO CONSERTO, E MOSTRADO VERMELHO.
É o que a §F1.4 manda, e a razão é a de sempre: um guarda que nasce verde não
provou nada — pode estar medindo outra coisa.

## O defeito, medido

📊 24/08/2026, `work_steps.output_summary` das 12 linhas dos quatro acionamentos
duráveis. As chaves de `slots`, lidas do banco:

    titular_cpf · telefone_contato · endereco_numero · ponto_referencia ·
    aparelho_marca · aparelho_modelo · problema_descricao · e os `*_opcao`

E no nível de cima, `client_phone` e `insurer_phone`. **Nada disso é mascarado.**
📊 O único filtro no caminho é `snapshot_duravel`
(`insurer_dispatch_service.py:191-210`), e o que ele filtra é **nome de
credencial** — a docstring dele diz, literal: *"Nada com cara de CREDENCIAL
atravessa"*. `_CHAVES_PROIBIDAS` não tem um único termo de PII.

⚠️ **E o `#####` que aparece no `transcript` NÃO é nosso** — é a máscara **da
seguradora** (`corridor_playbooks._CARACTERE_DE_MASCARA`). Confundir os dois foi
o que fez a v1 da SPEC escrever *"a máscara existe e não foi chamada"*.

## 🔴 A ARMADILHA, e ela é metade deste arquivo

`work_steps.output_summary` **é o payload de restauração da sessão**:

    snapshot_duravel → output_summary → _ultimo_retrato → sessao_restaurada
    → _gravar_no_redis → session["slots"] → render_reply → **A URA**

**Mascarar ali faz um acionamento restaurado responder `...1234` à seguradora.**
Por isso a máscara mora num GÊMEO — `work_steps.output_redacted`, criado na
FASE 0 — e nunca no lugar do payload.

🔴 **O CONTROLE deste arquivo é exatamente isso**, e sem ele o guarda (a)
passaria mascarando o payload inteiro e quebrando a restauração em silêncio:

    (a) o retrato PARA HUMANO não contém CPF nem telefone
    (b) 🔴 a sessão RESTAURADA responde à URA com o CPF REAL

Se (b) ficar verde por acidente — porque ninguém restaura nada — ele não guarda
nada. Por isso ele **percorre a restauração de verdade**.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent

# Valores FABRICADOS. Nenhum dado de segurado real entra num teste.
CPF_FALSO = "529.982.247-25"          # válido em dígito verificador, de ninguém
TELEFONE_FALSO = "5547988000001"
NOME_FALSO = "Fulano de Tal Sobrinho"


def _carregar(nome_do_modulo: str, caminho_relativo: str):
    """Carrega um módulo de `app/` sem passar por `app.services.__init__`.

    ⚠️ Aquele `__init__` importa `fastembed`, e 📊 o `gate.yml` **não roda
    `pip install`** — guarda que precise de dependência não roda em CI, e guarda
    que não roda não guarda. 🔴 E desfaz o que injetou: outros arquivos pytest
    da mesma sessão importam o `app` de verdade.
    """
    anteriores = {n: sys.modules.get(n) for n in ("app", "app.services")}
    injetados = [n for n in ("app", "app.services") if n not in sys.modules]
    try:
        for n in injetados:
            m = types.ModuleType(n)
            m.__path__ = [str(RAIZ / Path(*n.split(".")))]
            sys.modules[n] = m
        spec = importlib.util.spec_from_file_location(
            f"_spec085_{nome_do_modulo}", str(RAIZ / caminho_relativo))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        for n in injetados:
            if anteriores.get(n) is None:
                sys.modules.pop(n, None)
            else:
                sys.modules[n] = anteriores[n]


PII = _carregar("pii_da_sessao", "app/services/pii_da_sessao.py")
MOTOR = _carregar("motor", "app/services/insurer_dispatch_service.py")


def _sessao_com_pii() -> dict:
    """Uma sessão do corredor que deu certo — allianz-residencial, máquina de
    lavar — com os campos que 📊 o banco realmente guarda."""
    return {
        "case_id": "caso-de-teste",
        "state": "needs_human",
        "reason": "missing_slots:titular_cpf",
        "playbook_ref": "allianz-residencial-whatsapp@v1",
        "subservice": "maquina_de_lavar",
        "client_phone": TELEFONE_FALSO,
        "insurer_phone": "551140901444",
        "slots": {
            "titular_cpf": CPF_FALSO,
            "telefone_contato": TELEFONE_FALSO,
            "titular_nome": NOME_FALSO,
            "endereco_numero": "1234",
            "ponto_referencia": "em frente ao mercado, casa amarela",
            "problema_descricao": "a máquina de lavar não centrifuga",
            "eletrodomestico_opcao": "3",
            "periodo_agendamento_opcao": "1",
        },
        "transcript": [{"direction": "out", "text": "oi"}],
    }


# ---------------------------------------------------------------------------
# (a) O RETRATO PARA HUMANO NÃO LEVA PII
# ---------------------------------------------------------------------------

def test_o_retrato_para_humano_nao_leva_cpf():
    retrato = PII.retrato_para_humano(_sessao_com_pii())
    bruto = json.dumps(retrato, ensure_ascii=False)
    assert CPF_FALSO not in bruto, "o CPF atravessou inteiro"
    assert "52998224725" not in bruto, "o CPF atravessou sem pontuação"


def test_o_retrato_para_humano_nao_leva_telefone():
    retrato = PII.retrato_para_humano(_sessao_com_pii())
    bruto = json.dumps(retrato, ensure_ascii=False)
    assert TELEFONE_FALSO not in bruto, "o telefone do cliente atravessou"


def test_o_retrato_para_humano_nao_leva_nome_nem_endereco():
    """Nome e ponto de referência identificam tanto quanto um documento —
    `CLAUDE.md` §7: nenhum segredo em log, blueprint, artifact ou RAG."""
    retrato = PII.retrato_para_humano(_sessao_com_pii())
    bruto = json.dumps(retrato, ensure_ascii=False)
    assert NOME_FALSO not in bruto, "o nome do titular atravessou"
    assert "em frente ao mercado" not in bruto, "o ponto de referência atravessou"


def test_o_retrato_continua_servindo_para_TRIAR():
    """🔴 Mascarar tudo é fácil e inútil. Quem tria um travamento precisa saber
    QUAL corredor, QUAL serviço e POR QUE parou — nada disso é PII."""
    retrato = PII.retrato_para_humano(_sessao_com_pii())
    bruto = json.dumps(retrato, ensure_ascii=False)
    assert "allianz-residencial-whatsapp@v1" in bruto, "sumiu o corredor"
    assert "maquina_de_lavar" in bruto, "sumiu o subserviço"
    assert "missing_slots:titular_cpf" in bruto, "sumiu o motivo COMPLETO"


def test_a_escolha_de_menu_NAO_e_mascarada():
    """CONTROLE. `eletrodomestico_opcao = "3"` é a tecla que o corredor apertou,
    não um dado de pessoa. Mascarar isso apaga a única pista de POR ONDE ele
    andou — e um retrato que esconde o caminho não serve para triar nada."""
    retrato = PII.retrato_para_humano(_sessao_com_pii())
    slots = retrato.get("slots") or {}
    assert slots.get("eletrodomestico_opcao") == "3"
    assert slots.get("periodo_agendamento_opcao") == "1"


def test_CONTROLE_o_mascarador_consegue_deixar_passar():
    """🔴 §9.3: prove que ele CONSEGUE ser diferente. Um mascarador que apagasse
    o dicionário inteiro passaria em todos os testes de (a) acima."""
    limpa = {"case_id": "x", "state": "ura", "playbook_ref": "p@v1",
             "slots": {"eletrodomestico_opcao": "3"}}
    retrato = PII.retrato_para_humano(limpa)
    assert retrato.get("slots", {}).get("eletrodomestico_opcao") == "3", (
        "o mascarador apagou um campo que não é PII — ele não distingue")


def test_o_formato_nao_colide_com_a_mascara_DA_SEGURADORA():
    """🔴 §F1.1(b). `corridor_playbooks._CARACTERE_DE_MASCARA = "#*?•●"` é como o
    corredor reconhece a máscara **da seguradora**. Se a nossa usar os mesmos
    caracteres, o corredor passa a poder ler o próprio mascaramento como
    resposta da URA.

    ⚠️ Hoje isso é estruturalmente impossível — o retrato mascarado mora em
    `output_redacted` e a restauração lê `output_summary`. **Este teste é a
    segunda linha de defesa**, e ela custa nada."""
    proibidos = set("#*?•●")
    bruto = json.dumps(PII.retrato_para_humano(_sessao_com_pii()), ensure_ascii=False)
    usados = proibidos & set(bruto)
    assert not usados, (
        f"a máscara da sessão usa {sorted(usados)}, que é alfabeto da máscara "
        "DA SEGURADORA — colidir quebra `bate_com_mascara`")


# ---------------------------------------------------------------------------
# (b) 🔴 O CONTROLE QUE A v1 DA SPEC NÃO TINHA
# ---------------------------------------------------------------------------

def test_CONTROLE_a_sessao_restaurada_responde_com_o_CPF_REAL():
    """🔴 O payload de restauração NÃO pode ser mascarado.

    `snapshot_duravel` produz o que vai para `output_summary`, e é dele que a
    sessão volta. Se a máscara entrar aí, um acionamento restaurado responde
    `...1234` à seguradora — e o segurado fica sem chamado por causa de um
    conserto de privacidade.
    """
    original = _sessao_com_pii()
    payload = MOTOR.snapshot_duravel(original)
    voltou = MOTOR.sessao_restaurada(payload, motivo="teste")
    assert voltou["slots"]["titular_cpf"] == CPF_FALSO, (
        "a sessão restaurada perdeu o CPF real — a restauração foi mascarada, "
        "e o corredor vai responder a máscara para a URA")
    assert voltou["client_phone"] == TELEFONE_FALSO


def test_CONTROLE_os_dois_retratos_sao_DIFERENTES():
    """Se o mascarado e o payload forem iguais, um dos dois está errado — e o
    teste acima estaria passando por não haver o que mascarar."""
    sessao = _sessao_com_pii()
    payload = json.dumps(MOTOR.snapshot_duravel(sessao), ensure_ascii=False, default=str)
    humano = json.dumps(PII.retrato_para_humano(sessao), ensure_ascii=False, default=str)
    assert payload != humano, (
        "o retrato para humano é idêntico ao payload de restauração — ou nada "
        "foi mascarado, ou a restauração foi")


def test_o_checkpoint_grava_o_gemeo():
    """O escritor tem de usar o gêmeo. Estático, porque `registrar_checkpoint`
    só existe dentro de um `await` e de um cliente Supabase."""
    fonte = (RAIZ / "app" / "services" / "dispatch_router.py").read_text(encoding="utf-8")
    corpo = fonte.split("async def registrar_checkpoint", 1)[-1].split("\nasync def ", 1)[0]
    assert "output_redacted" in corpo, (
        "`registrar_checkpoint` não grava `output_redacted` — a coluna da "
        "FASE 0 continua vazia e o dossiê continua sem versão legível")
    assert "output_summary" in corpo, (
        "`registrar_checkpoint` deixou de gravar `output_summary` — é o payload "
        "de restauração, e sem ele o acionamento não volta")


def test_missing_slots_sobrevive_INTEIRO_ao_retrato():
    """🔴 Defeito meu, pego OLHANDO a saída — nenhum teste acima o via.

    O ramo que trata estrutura rodava antes da classificação, e engolia
    `missing_slots` (uma LISTA declarada segura) num `{LIST:1}`.

    📊 `missing_slots` é a informação mais útil que existe para triar: diz
    QUAIS slots faltaram. São nomes de campo, nunca valores. Sem ela, o retrato
    diz "parou por falta de dado" e não diz de qual — que é como não dizer nada.
    """
    sessao = _sessao_com_pii()
    sessao["missing_slots"] = ["titular_cpf", "periodo_agendamento_opcao"]
    retrato = PII.retrato_para_humano(sessao)
    assert retrato["missing_slots"] == ["titular_cpf", "periodo_agendamento_opcao"], (
        f"missing_slots foi engolido: {retrato.get('missing_slots')!r}")


def test_CONTROLE_estrutura_NAO_declarada_continua_colapsando():
    """E o controle do conserto: abrir a porta para as chaves seguras não pode
    abrir para todas. Uma estrutura que ninguém declarou continua virando só o
    formato — descer nela às cegas é como PII volta a passar."""
    sessao = _sessao_com_pii()
    sessao["dossie_bruto"] = [{"nome": NOME_FALSO, "cpf": CPF_FALSO}]
    retrato = PII.retrato_para_humano(sessao)
    assert retrato["dossie_bruto"] == "{LIST:1}", (
        f"estrutura não declarada atravessou: {retrato.get('dossie_bruto')!r}")
    assert NOME_FALSO not in json.dumps(retrato, ensure_ascii=False)


def test_o_case_id_NAO_carrega_o_telefone_do_cliente():
    """🔴 VAZAMENTO REAL, pego pela conferência no banco depois do backfill.

    📊 Medido em 24/08/2026, sobre as 12 etapas duráveis, sem trazer um único
    valor para a tela:

        case_id CONTÉM o telefone do cliente ....... 12 de 12
        comprimento do case_id ..................... 15, sempre

    O `case_id` deste produto é montado **a partir do telefone do segurado**.
    Ele tinha cara de identificador técnico e estava na lista de chaves seguras
    — é o `CLAUDE.md` §12.1 na forma mais cara: *"se o nome de um campo mente
    sobre o que ele guarda, conserte o campo"*.

    ⚠️ Um `assert` sobre a lista de chaves não pegaria isto. **Só a conferência
    do DADO pegou.**
    """
    sessao = _sessao_com_pii()
    sessao["case_id"] = f"wa:{TELEFONE_FALSO}"          # a forma real, fabricada
    bruto = json.dumps(PII.retrato_para_humano(sessao), ensure_ascii=False)
    assert TELEFONE_FALSO not in bruto, (
        "o telefone atravessou DENTRO do case_id — identificador que carrega "
        "PII não é identificador seguro")


def test_o_case_id_mascarado_ainda_da_um_FIO_para_puxar():
    """CONTROLE do conserto: mascarar não pode virar apagar. Quem tria precisa
    correlacionar — e a cauda dá o mesmo nível do telefone mascarado."""
    sessao = _sessao_com_pii()
    sessao["case_id"] = f"wa:{TELEFONE_FALSO}"
    retrato = PII.retrato_para_humano(sessao)
    assert retrato["case_id"].endswith(TELEFONE_FALSO[-4:]), (
        f"o case_id virou inútil para correlacionar: {retrato['case_id']!r}")
    # e o work_run_id, que é uuid de banco de verdade, continua inteiro
    sessao["work_run_id"] = "e5279497-a642-4703-a85f-d92a381e45ac"
    assert PII.retrato_para_humano(sessao)["work_run_id"] == \
        "e5279497-a642-4703-a85f-d92a381e45ac"


def test_CONTROLE_por_a_chave_na_lista_segura_NAO_resgata_o_case_id():
    """🔴 A ordem em `_classificar` é o conserto. Se alguém, daqui a seis meses,
    acrescentar `case_id` a `_CHAVES_SEGURAS` para 'facilitar a triagem', o
    vazamento volta em silêncio. O teste do identificador roda ANTES."""
    assert "case_id" not in PII._CHAVES_SEGURAS, (
        "case_id voltou para a lista segura — ele carrega telefone dentro")
    assert PII._classificar("case_id") == "documento"
