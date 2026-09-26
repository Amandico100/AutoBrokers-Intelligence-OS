# -*- coding: utf-8 -*-
"""SPEC-117 · F1 — os unitários do construtor ÚNICO do contexto da apólice.

🔴 **O `data` destes testes não é escrito à mão** (CLAUDE.md §9.4). Ele sai das
funções REAIS do conector — `infocap_connector._canonical_customer_identity` e
`_sanitize_policy` —, as duas que decidem o que cada papel vê. Se a máscara ou a
sanitização mudarem de forma amanhã, estes testes mudam com elas, e são eles que
dizem se a mudança apagou o contexto outra vez.

📊 **O defeito que o módulo conserta, medido em 26/09/2026 (HEAD `ca8ad24`):**

```
$ sed -n 423,425p backend/app/agents/nodes.py
    document = str(data.get("client_document") or "").strip()
    name = str(data.get("client_name") or "").strip()
    if not (document or name) or not policy_numbers:
        return None
```

No papel `attendance` o conector devolve `client_name_masked` /
`client_document_masked` — nunca os crus. A porta antiga devolvia `None`, e toda
regra pendurada no contexto (o ramo oficial que vence o palpite do modelo, a
apólice que chega ao portal e ao handoff) estava morta no WhatsApp.

⛔ Nenhum nome de corretora, de segurado ou de atendente real (CLAUDE.md §13.9).
Dois tenants sintéticos, um cliente sintético, um CPF sintético.
"""

import hashlib
import re
from datetime import date, timedelta

import pytest

from app.api.infocap_connector import (_canonical_customer_identity,
                                       _sanitize_policy)
from app.services import policy_context as PC

# --------------------------------------------------------------------------- #
# Os dois tenants e o cliente sintético
# --------------------------------------------------------------------------- #
#: 📊 UUIDs fixos: é isso que permite afirmar que a MESMA dupla `codfil:codigo`
#: gera pseudônimos DIFERENTES em corretoras diferentes (SPEC-117 G9).
TENANT_A = "11111111-1111-4111-8111-111111111111"
TENANT_B = "22222222-2222-4222-8222-222222222222"

#: ⚠️ Existem aqui para o guarda de PII poder PROCURÁ-LOS no que sai — nunca
#: para serem transportados.
DOC_SINTETICO = "39053344705"
DOC_FORMATADO = "390.533.447-05"
#: 🔴 As partes do nome não usam nenhuma palavra que apareça em nome de CAMPO do
#: contexto, e nenhuma delas é escrita só com os dígitos hexadecimais `a–f`: a
#: `chave` da apólice é hex, e uma parte como "De" ou "Cliente" daria falso
#: positivo na varredura. Aqui o achado só pode ser achado de verdade.
NOME_SINTETICO = "Zoraide Bentivoglio Marcuschi"
TELEFONE_SINTETICO = "11955550101"
EMAIL_SINTETICO = "zoraide.teste@exemplo.invalido"

_HOJE = date.today()


def _br(dias: int) -> str:
    return (_HOJE + timedelta(days=dias)).strftime("%d/%m/%Y")


#: 📊 Vigência calculada a partir de HOJE, não escrita à mão: `_active_expired`
#: compara com `datetime.now(timezone.utc)`, e data fixa transforma um guarda
#: verde de hoje num vermelho silencioso no ano que vem.
VIG_INICIO, VIG_FIM = _br(-60), _br(+300)
VENC_INICIO, VENC_FIM = _br(-800), _br(-400)


def _doc_infocap(
    *,
    numapo: str,
    nosnum: str,
    ramo: str = "AUTO",
    seguradora: str = "ALLIANZ",
    inivig: str = VIG_INICIO,
    fimvig: str = VIG_FIM,
    codigo: str = "7788",
    codfil: str = "4321",
    cancelado: bool = False,
    com_locator: bool = True,
) -> dict:
    """Um documento CRU da fonte, do jeito que a InfoCap entrega.

    `com_locator=False` reproduz 📊 o corpus da bancada, onde `policy_locator`
    vem `None` (a fonte não devolveu `nosnum`) — é o caso que exige a chave
    derivada do número humano.
    """
    doc = {
        "numapo": numapo,
        "codfil": codfil,
        "codigo": codigo,
        "seguradora_abrev": seguradora,
        "ramo_abrev": ramo,
        "inivig": inivig,
        "fimvig": fimvig,
        "cliente": NOME_SINTETICO,
        "cpf_cnpj": DOC_SINTETICO,
        "telefone": TELEFONE_SINTETICO,
        "email": EMAIL_SINTETICO,
        "itens": [{"descricao": "Colisao"}],
    }
    if com_locator:
        doc["nosnum"] = nosnum
    if cancelado:
        doc["cancelado"] = True
    return doc


def _auto_vigente(numapo: str = "A-0001") -> dict:
    return _doc_infocap(numapo=numapo, nosnum="900001")


def _resi_vigente(numapo: str = "R-0002", nosnum: str = "900002") -> dict:
    return _doc_infocap(numapo=numapo, nosnum=nosnum, ramo="RESI", seguradora="PORTO")


def _auto_vencida(numapo: str = "Z-9999") -> dict:
    """A vencida com o número MAIOR e a vigência MAIS RECENTE em aparência — é
    ela que uma regra distraída escolheria por ser "a última"."""
    return _doc_infocap(numapo=numapo, nosnum="900777",
                        inivig=VENC_INICIO, fimvig=VENC_FIM)


def _data_do_conector(*, unmasked: bool, docs=None, status: str = "found") -> dict:
    """O `data` que a ferramenta devolveria — montado pelas funções REAIS.

    🔴 Este é o ponto que separa este arquivo de um teste de fachada. O padrão é
    o mesmo de `test_o_atendimento_guarda_a_apolice.py` (F0), de propósito: as
    duas fatias têm de concordar sobre a forma da entrada.
    """
    brutos = docs if docs is not None else [_auto_vigente()]
    identidade = _canonical_customer_identity(brutos[0], brutos[0], unmasked=unmasked)
    apolices = [_sanitize_policy(d, unmasked) for d in brutos]
    return {
        "ok": True,
        "status": status,
        "source_ref": "infocap:documento",
        "result_count": len(apolices),
        "matched_by": "document",
        "identity_status": "identity_verified",
        **identidade,
        "selected": apolices[0] if len(apolices) == 1 else None,
        "matches": apolices,
    }


def _ctx(docs=None, *, company_id: str = TENANT_A, papel: str = "attendance",
         unmasked: bool = False, status: str = "found"):
    return PC.construir_policy_context(
        _data_do_conector(unmasked=unmasked, docs=docs, status=status),
        company_id=company_id,
        papel=papel,
    )


# --------------------------------------------------------------------------- #
# A VARREDURA de PII — recursiva, sobre VALORES e sobre NOMES DE CAMPO
# --------------------------------------------------------------------------- #
_RE_CPF = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")

#: 🔴 Comparação sem caixa: o que não pode aparecer de jeito nenhum.
_PROIBIDOS_SEM_CAIXA = (
    DOC_SINTETICO,
    DOC_FORMATADO,
    TELEFONE_SINTETICO,
    EMAIL_SINTETICO,
    "****05",              # o documento MASCARADO — a máscara fica no DTO, não aqui
    "C***",                # a forma do nome mascarado
) + tuple(p for p in NOME_SINTETICO.split() if len(p) >= 4)

#: ⚠️ Comparação COM caixa, e a razão é real: o `product` cru é `"AUTO"` e o
#: `ramo` canônico é `"auto"`. Sem a caixa, o campo LEGÍTIMO reprovaria o guarda
#: e o guarda seria desligado — que é como se perde um guarda de verdade.
_PROIBIDOS_COM_CAIXA = ("AUTO", "RESI", "infocap:4321:", "Colisao")

#: os nomes de campo que a lista branca da SPEC-117 §2 não admite em lugar
#: nenhum do contexto, em nenhuma profundidade.
_CAMPOS_PROIBIDOS = {
    "product", "policy_locator", "policy_locator_ref", "policy_ref",
    "client_name", "client_document", "client_name_masked",
    "client_document_masked", "client_phone", "client_email",
    "holder_name", "holder_name_masked", "masked_policy_number",
    "cpf_cnpj", "telefone", "email", "placa", "endereco", "titular",
}


def _varrer_pii(valor, caminho="contexto"):
    """Todos os achados de PII, recursivamente. Lista vazia = limpo."""
    achados = []
    if isinstance(valor, dict):
        for chave, sub in valor.items():
            nome = str(chave)
            if nome.lower() in _CAMPOS_PROIBIDOS:
                achados.append("%s.%s <- campo fora da lista branca" % (caminho, nome))
            achados.extend(_varrer_pii(sub, "%s.%s" % (caminho, nome)))
        return achados
    if isinstance(valor, (list, tuple)):
        for i, sub in enumerate(valor):
            achados.extend(_varrer_pii(sub, "%s[%d]" % (caminho, i)))
        return achados
    texto = "" if valor is None else str(valor)
    if not texto:
        return achados
    minusculo = texto.lower()
    for proibido in _PROIBIDOS_SEM_CAIXA:
        if proibido.lower() in minusculo:
            achados.append("%s = %r <- contém %r" % (caminho, texto, proibido))
    for proibido in _PROIBIDOS_COM_CAIXA:
        if proibido in texto:
            achados.append("%s = %r <- contém %r (cru)" % (caminho, texto, proibido))
    if _RE_CPF.search(texto):
        achados.append("%s = %r <- tem a forma de um CPF" % (caminho, texto))
    return achados


# --------------------------------------------------------------------------- #
# G1 — o contexto nasce nos DOIS papéis, e o ramo é o mesmo
# --------------------------------------------------------------------------- #
def test_g1_o_contexto_nasce_nos_dois_papeis_com_o_mesmo_ramo():
    """🔴 G1. O MESMO documento, os DOIS papéis: o contexto nasce nos dois e o
    `ramo` é igual. É a porta nova — "há apólice E há cliente identificado" —
    que faz o papel mascarado passar."""
    mascarado = _ctx(papel="attendance", unmasked=False)
    cru = _ctx(papel="core", unmasked=True)

    assert mascarado, "o papel do segurado tem de produzir contexto"
    assert cru, "o papel do core é o que já funcionava — se cair, o defeito é outro"

    assert mascarado["apolices"][0]["ramo"] == cru["apolices"][0]["ramo"] == "auto"
    assert mascarado["selected_policy_ramo"] == cru["selected_policy_ramo"] == "auto"
    assert mascarado["policy_numbers"] == cru["policy_numbers"] == ["A-0001"]

    # A exceção única da lista branca: identidade crua SÓ no core.
    assert "document" not in mascarado and "name" not in mascarado
    assert cru["document"] == DOC_SINTETICO and cru["name"] == NOME_SINTETICO


def test_g1_linha_de_controle_a_porta_antiga_fechava_no_papel_mascarado():
    """🔴 A LINHA DE CONTROLE (CLAUDE.md §9.2) — é ela que dá direito a dizer que
    o defeito era da PORTA, e não da consulta nem do papel.

    ⚠️ **Por que ela não afirma "a antiga devolve None" e pronto:** a F2 desta
    mesma SPEC vai fazer `nodes._safe_infocap_policy_context` DELEGAR a este
    módulo. Quando isso acontecer, a antiga deixa de devolver `None` — e um
    teste que exigisse `None` reprovaria o conserto que ele existe para provar.
    Então o guarda compara contra o **comportamento documentado** de 26/09/2026:
    se a porta antiga ainda é a de antes, ela fecha; se já delegou, ela tem de
    CONCORDAR com a nova. Nas duas situações, a afirmação que interessa é a
    mesma: **a função nova produz contexto onde a antiga não produzia.**
    """
    data = _data_do_conector(unmasked=False)
    nova = PC.construir_policy_context(data, company_id=TENANT_A, papel="attendance")
    assert nova, "a porta nova tem de abrir com identidade mascarada"

    from app.agents.nodes import _safe_infocap_policy_context

    antiga = _safe_infocap_policy_context(data)
    if antiga is None:
        # 📊 O estado medido em 26/09/2026 (nodes.py:423-425): a porta antiga
        # exige identidade CRUA e fecha no WhatsApp.
        assert not data.get("client_document") and not data.get("client_name")
        assert data.get("client_document_masked"), "o papel mascarado tem a versão mascarada"
    else:
        # A F2 já delegou. Então as duas têm de dizer a MESMA coisa.
        assert (antiga.get("policy_numbers") or []) == nova["policy_numbers"], (
            "a porta antiga passou a responder, mas discorda da nova: %r vs %r"
            % (antiga.get("policy_numbers"), nova["policy_numbers"]))


# --------------------------------------------------------------------------- #
# G2 — PII, a lista branca, e a MUTAÇÃO que prova que o guarda fica vermelho
# --------------------------------------------------------------------------- #
def test_g2_o_contexto_do_atendimento_nao_carrega_nenhum_dado_pessoal():
    """🔴 G2. Varredura RECURSIVA por conteúdo E por nome de campo."""
    contexto = _ctx(docs=[_auto_vigente(), _resi_vigente()], papel="attendance")
    assert contexto
    achados = _varrer_pii(contexto)
    assert achados == [], "PII no contexto do atendimento: %s" % achados


def test_g2_nem_o_papel_core_carrega_telefone_email_ou_locator():
    """⚠️ O core recebe `document` e `name` — e NADA além disso. Telefone,
    e-mail, locator cru e `product` cru não passam em nenhum papel."""
    contexto = _ctx(papel="core", unmasked=True)
    assert contexto
    # a exceção autorizada sai da varredura, o resto continua valendo
    sem_excecao = {k: v for k, v in contexto.items() if k not in ("document", "name")}
    achados = _varrer_pii(sem_excecao)
    assert achados == [], "PII no contexto do core, fora da exceção: %s" % achados


def test_g2_a_lista_branca_e_fechada_em_cima_e_por_apolice():
    """A lista branca da SPEC-117 §2 é FECHADA: campo novo no contexto reprova
    aqui antes de chegar ao modelo, à ficha durável e ao painel."""
    contexto = _ctx(docs=[_auto_vigente(), _resi_vigente()], papel="attendance")
    permitidos_no_topo = {
        "versao", "company_id", "cliente_ref", "apolices", "selecionada",
        "origem_por_campo", "evidencia",
        # derivadas, por compatibilidade (ver o docstring do módulo)
        "policy_numbers", "source", "selected_policy_number", "selected_policy_ramo",
    }
    assert set(contexto) <= permitidos_no_topo, set(contexto) - permitidos_no_topo

    por_apolice = {"chave", "numapo", "ramo", "seguradora", "vigencia_inicio",
                   "vigencia_fim", "vigente", "expirada", "cancelada"}
    for apolice in contexto["apolices"]:
        assert set(apolice) == por_apolice, set(apolice) ^ por_apolice


def test_g2_mutacao_o_guarda_de_pii_consegue_ficar_vermelho(monkeypatch):
    """🔴 CLAUDE.md §9.3 — um guarda que não consegue falhar não guarda nada.

    Três mutações, cada uma pegando o que as outras não pegam:
    **(A)** PII injetada FUNDO, dentro de `apolices[]`, por dentro do construtor;
    **(B)** PII no topo, num campo com nome inocente;
    **(C)** um campo da lista negra (`policy_locator_ref`) com valor aparentemente
    inofensivo — é o NOME do campo que reprova.
    """
    limpo = _ctx(papel="attendance")
    assert _varrer_pii(limpo) == [], "o controle tem de estar limpo"

    # (A) a mutação POR DENTRO do construtor, na função que decide a lista branca.
    original = PC._resumo_da_apolice

    def _vazando(apolice_sanitizada, chave):
        resumo = original(apolice_sanitizada, chave)
        resumo["titular"] = NOME_SINTETICO
        resumo["contato"] = TELEFONE_SINTETICO
        return resumo

    monkeypatch.setattr(PC, "_resumo_da_apolice", _vazando)
    vazado = _ctx(papel="attendance")
    achados = _varrer_pii(vazado)
    assert achados, "a varredura NÃO viu o nome do cliente dentro de apolices[] — carimbo, não guarda"
    assert any("titular" in a for a in achados), achados
    assert any(TELEFONE_SINTETICO in a for a in achados), achados
    monkeypatch.undo()

    # (B) PII no topo, com nome de campo que não está na lista negra.
    assert _varrer_pii({**limpo, "observacao": "segurado %s" % NOME_SINTETICO}), (
        "nome do cliente num campo de nome inocente passou pela varredura")

    # (C) o NOME do campo reprova, mesmo com valor curto.
    assert _varrer_pii({**limpo, "policy_locator_ref": "x"}), (
        "o campo policy_locator_ref passou pela varredura")


# --------------------------------------------------------------------------- #
# G5 — a seleção, e a regra que chega ao segurado
# --------------------------------------------------------------------------- #
def test_g5_auto_e_resi_vigentes_nao_escolhem_sozinhas_e_o_ramo_filtra():
    """Duas vigentes de ramos DIFERENTES: o construtor não escolhe. Quem escolhe
    pelo ramo é o PEDIDO — `apolices_vigentes(ctx, "resi")`."""
    contexto = _ctx(docs=[_auto_vigente(), _resi_vigente()])
    assert contexto["selecionada"] is None, contexto
    assert "selected_policy_number" not in contexto

    so_resi = PC.apolices_vigentes(contexto, "resi")
    assert [a["numapo"] for a in so_resi] == ["R-0002"], so_resi
    # o nome humano do ramo também serve — a régua é a mesma do projeto
    assert PC.apolices_vigentes(contexto, "residencial") == so_resi
    assert len(PC.apolices_vigentes(contexto)) == 2


def test_g5_duas_do_mesmo_ramo_vigentes_exigem_desambiguacao():
    contexto = _ctx(docs=[_resi_vigente("R-0002", "900002"),
                          _resi_vigente("R-0003", "900003")])
    assert contexto["selecionada"] is None
    assert len(PC.apolices_vigentes(contexto, "resi")) == 2
    assert PC.apolice_selecionada(contexto) is None


def test_g5_uma_vigente_sozinha_e_escolhida_sem_perguntar():
    contexto = _ctx(docs=[_auto_vigente()])
    assert contexto["selecionada"] == contexto["apolices"][0]["chave"]
    assert contexto["origem_por_campo"]["selecionada"] == "sistema_de_gestao"
    assert contexto["selected_policy_number"] == "A-0001"


def test_g5_a_vencida_com_numero_maior_nunca_e_a_escolhida():
    """🔴 O defeito que chegaria ao segurado: a vencida é a "mais recente" no
    texto e tem o número MAIOR. Ela nunca pode ser a apólice do caso."""
    contexto = _ctx(docs=[_auto_vigente("A-0001"), _auto_vencida("Z-9999")])
    escolhida = PC.apolice_selecionada(contexto)
    assert escolhida is not None
    assert escolhida["numapo"] == "A-0001", escolhida
    vencida = [a for a in contexto["apolices"] if a["numapo"] == "Z-9999"][0]
    assert vencida["expirada"] is True and vencida["vigente"] is False
    assert contexto["selecionada"] != vencida["chave"]


def test_g5_so_vencidas_nao_escolhe_nada_e_a_lista_continua_visivel():
    """Se todas venceram, `selecionada` é None e as apólices ficam listadas com
    `vigente=False` — quem responde decide o que dizer."""
    contexto = _ctx(docs=[_auto_vencida("Z-9999")])
    assert contexto, "a lista continua existindo: o corretor precisa vê-la"
    assert contexto["selecionada"] is None
    assert "selected_policy_number" not in contexto
    assert contexto["apolices"][0]["vigente"] is False
    assert PC.apolices_vigentes(contexto) == []


def test_g5_cancelada_nunca_e_escolhida_mesmo_sendo_a_unica():
    contexto = _ctx(docs=[_doc_infocap(numapo="C-0007", nosnum="900555",
                                       cancelado=True)])
    assert contexto["selecionada"] is None
    assert contexto["apolices"][0]["cancelada"] is True


def test_g5_escolher_apolice_vencida_levanta_erro_em_portugues():
    contexto = _ctx(docs=[_auto_vigente("A-0001"), _auto_vencida("Z-9999")])
    vencida = [a for a in contexto["apolices"] if a["numapo"] == "Z-9999"][0]
    with pytest.raises(ValueError) as erro:
        PC.escolher_apolice(contexto, vencida["chave"])
    assert "VENCIDA" in str(erro.value) and "Z-9999" in str(erro.value)


def test_g5_escolher_apolice_devolve_contexto_novo_sem_mutar_o_recebido():
    contexto = _ctx(docs=[_resi_vigente("R-0002", "900002"),
                          _resi_vigente("R-0003", "900003")])
    alvo = contexto["apolices"][1]
    novo = PC.escolher_apolice(contexto, alvo["chave"])

    assert novo is not contexto
    assert contexto["selecionada"] is None, "o contexto recebido foi MUTADO"
    assert novo["selecionada"] == alvo["chave"]
    assert novo["origem_por_campo"]["selecionada"] == "cliente"
    assert contexto["origem_por_campo"].get("selecionada") is None
    assert novo["selected_policy_number"] == alvo["numapo"]
    assert PC.apolice_selecionada(novo)["chave"] == alvo["chave"]


# --------------------------------------------------------------------------- #
# G9 — dois tenants
# --------------------------------------------------------------------------- #
def test_g9_o_mesmo_codfil_codigo_em_duas_corretoras_da_pseudonimos_diferentes():
    """🔴 G9. O `company_id` entra DENTRO do material do HMAC — é isso, e só
    isso, que isola o pseudônimo por corretora (decisão D3)."""
    data = _data_do_conector(unmasked=False)
    a = PC.construir_policy_context(data, company_id=TENANT_A, papel="attendance")
    b = PC.construir_policy_context(data, company_id=TENANT_B, papel="attendance")

    assert a["cliente_ref"] and b["cliente_ref"]
    assert a["cliente_ref"] != b["cliente_ref"], "o pseudônimo atravessou tenants"
    assert len(a["cliente_ref"]) == 24 and re.fullmatch(r"[0-9a-f]{24}", a["cliente_ref"])
    assert a["company_id"] == TENANT_A and b["company_id"] == TENANT_B
    assert PC.mesmo_cliente(a, b) is False


def test_g9_o_pseudonimo_nao_e_hash_nu_do_codigo():
    """⛔ ENISA R5: `sha256("7788")` cai por força bruta em segundos. O valor
    devolvido não pode ser nenhum hash sem chave do material."""
    contexto = _ctx()
    ref = contexto["cliente_ref"]
    for material in ("7788", "4321:7788", "%s:4321:7788" % TENANT_A):
        nu = hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]
        assert ref != nu, "o cliente_ref é hash SEM chave de %r" % material
    assert "7788" not in ref and TENANT_A not in ref


def test_g9_fundir_contextos_de_tenants_diferentes_nunca_mistura_apolices():
    a = _ctx(docs=[_auto_vigente("A-0001")], company_id=TENANT_A)
    b = _ctx(docs=[_resi_vigente("R-0002")], company_id=TENANT_B)

    fundido = PC.fundir(a, b)
    assert fundido["company_id"] == TENANT_B
    assert [x["numapo"] for x in fundido["apolices"]] == ["R-0002"]
    assert "A-0001" not in (fundido["policy_numbers"] or [])


def test_g9_cliente_ref_exige_tenant_e_alguma_identidade_da_fonte():
    assert PC.cliente_ref("", {"codigo": "7788", "codfil": "1"}) is None
    assert PC.cliente_ref(TENANT_A, {}) is None
    assert PC.cliente_ref(TENANT_A, None) is None
    assert PC.cliente_ref(TENANT_A, {"codigo": "7788"})
    # só `codfil` também identifica a filial do cadastro — é sinal, não ruído
    assert PC.cliente_ref(TENANT_A, {"codfil": "4321"})
    assert PC.cliente_ref(TENANT_A, {"codigo": "7788"}) != PC.cliente_ref(
        TENANT_A, {"codfil": "4321"})


# --------------------------------------------------------------------------- #
# A PORTA — o que fecha, e o que abre
# --------------------------------------------------------------------------- #
def test_a_porta_abre_so_com_client_ref_sem_nenhuma_identidade_textual():
    """A forma mais dura da porta nova: nem nome, nem CPF, nem mascarados — só o
    `codfil:codigo`. O contexto tem de nascer."""
    data = _data_do_conector(unmasked=False)
    for chave in ("client_name_masked", "client_document_masked"):
        data.pop(chave, None)
    contexto = PC.construir_policy_context(data, company_id=TENANT_A)
    assert contexto, "só o client_ref já identifica o cliente"
    assert contexto["cliente_ref"]


def test_a_porta_fecha_sem_apolice_e_sem_qualquer_identidade():
    sem_apolice = _data_do_conector(unmasked=False)
    sem_apolice["matches"] = []
    sem_apolice["selected"] = None
    assert PC.construir_policy_context(sem_apolice, company_id=TENANT_A) is None

    sem_identidade = _data_do_conector(unmasked=False)
    for chave in ("client_ref", "client_name_masked", "client_document_masked"):
        sem_identidade.pop(chave, None)
    assert PC.construir_policy_context(sem_identidade, company_id=TENANT_A) is None

    assert PC.construir_policy_context(_data_do_conector(unmasked=False), company_id="") is None
    assert PC.construir_policy_context(None, company_id=TENANT_A) is None


def test_a_porta_fecha_quando_o_numero_humano_nao_e_numero():
    """⛔ A régua do número é a ÚNICA do projeto (`numero_humano_valido`): `"0"`,
    `"00000"` e `"null"` não são número de apólice, e uma apólice sem número não
    entra no contexto."""
    for falso in ("0", "00000", "null", "-", ""):
        data = _data_do_conector(unmasked=False,
                                 docs=[_doc_infocap(numapo=falso, nosnum="900001")])
        assert PC.construir_policy_context(data, company_id=TENANT_A) is None, falso


# --------------------------------------------------------------------------- #
# fundir
# --------------------------------------------------------------------------- #
def test_fundir_novo_ausente_preserva_o_anterior_intacto():
    """🔴 SPEC-016.1 D6: cinco mensagens curtas não apagam a apólice do caso."""
    anterior = _ctx(docs=[_auto_vigente()])
    atual = anterior
    for curto in ("ok", "tá", "e agora?", "certo", "beleza"):
        atual = PC.fundir(atual, None)
        assert atual is anterior, "a mensagem %r apagou a apólice do caso" % curto
    assert PC.fundir(None, None) is None


def test_fundir_mesmo_cliente_sem_selecao_nova_preserva_a_selecionada():
    base = [_resi_vigente("R-0002", "900002"), _resi_vigente("R-0003", "900003")]
    anterior = PC.escolher_apolice(_ctx(docs=base), _ctx(docs=base)["apolices"][1]["chave"])
    novo = _ctx(docs=base)
    assert novo["selecionada"] is None, "controle: a consulta nova não escolheu nada"

    fundido = PC.fundir(anterior, novo)
    assert fundido["selecionada"] == anterior["selecionada"]
    assert fundido["origem_por_campo"]["selecionada"] == "cliente", (
        "quem escolheu foi o cliente; a fusão não pode reescrever a origem")
    assert fundido["selected_policy_number"] == anterior["selected_policy_number"]


def test_fundir_nao_preserva_selecionada_que_saiu_da_lista_ou_venceu():
    base = [_resi_vigente("R-0002", "900002"), _resi_vigente("R-0003", "900003")]
    anterior = PC.escolher_apolice(_ctx(docs=base), _ctx(docs=base)["apolices"][1]["chave"])

    # a apólice escolhida não está mais na lista nova
    novo = _ctx(docs=[_resi_vigente("R-0002", "900002")])
    fundido = PC.fundir(anterior, novo)
    assert fundido["selecionada"] == novo["selecionada"], fundido
    assert fundido["selecionada"] != anterior["selecionada"]


def test_fundir_cliente_diferente_substitui_o_contexto_inteiro():
    anterior = _ctx(docs=[_auto_vigente("A-0001")])
    outro = _ctx(docs=[_doc_infocap(numapo="B-0009", nosnum="900009", codigo="9999")])
    assert anterior["cliente_ref"] != outro["cliente_ref"], "controle: são clientes distintos"

    fundido = PC.fundir(anterior, outro)
    assert [a["numapo"] for a in fundido["apolices"]] == ["B-0009"]
    assert fundido["cliente_ref"] == outro["cliente_ref"]


def test_fundir_consulta_nova_com_selecao_vence():
    anterior = _ctx(docs=[_auto_vigente("A-0001")])
    novo = _ctx(docs=[_resi_vigente("R-0002")])
    assert novo["selecionada"], "controle: a consulta nova escolheu"
    assert PC.fundir(anterior, novo)["selected_policy_number"] == "R-0002"


def test_mesmo_cliente_e_sobre_identidade_opaca_nunca_sobre_nome_ou_cpf():
    a = _ctx(docs=[_auto_vigente()])
    b = _ctx(docs=[_resi_vigente()])
    assert PC.mesmo_cliente(a, b) is True, "mesmo codfil:codigo, mesmo tenant"
    assert PC.mesmo_cliente(a, None) is False
    assert PC.mesmo_cliente({"company_id": TENANT_A, "cliente_ref": None},
                            {"company_id": TENANT_A, "cliente_ref": None}) is False, (
        "sem pseudônimo não se herda apólice de ninguém")


# --------------------------------------------------------------------------- #
# chave_da_apolice
# --------------------------------------------------------------------------- #
def test_chave_da_apolice_e_estavel_com_locator_e_sem_locator():
    com = _sanitize_policy(_doc_infocap(numapo="A-0001", nosnum="900001"), False)
    sem = _sanitize_policy(
        _doc_infocap(numapo="S-0003", nosnum="ignorado", com_locator=False), False)
    assert sem["policy_locator"] is None, "controle: é o caso do corpus da bancada"

    assert PC.chave_da_apolice(com) == PC.chave_da_apolice(com)
    assert PC.chave_da_apolice(sem) == PC.chave_da_apolice(sem)
    assert PC.chave_da_apolice(com) != PC.chave_da_apolice(sem)
    assert re.fullmatch(r"[0-9a-f]{24}", PC.chave_da_apolice(com))
    assert PC.chave_da_apolice(sem).startswith("h:")
    assert len(PC.chave_da_apolice(sem)) == 24
    assert PC.chave_da_apolice({}) is None
    assert PC.chave_da_apolice(None) is None


def test_chave_da_apolice_nunca_expoe_nosnum_nem_codfil_em_claro():
    """⛔ A chave vai para a ficha durável e para o `selecionada`. Ela não pode
    ser o locator, nem conter as suas partes."""
    apolice = _sanitize_policy(_doc_infocap(numapo="A-0001", nosnum="900001"), False)
    chave = PC.chave_da_apolice(apolice)
    assert apolice["policy_locator_ref"] == "infocap:4321:900001", "controle"
    for parte in ("900001", "4321", "infocap", apolice["policy_locator_ref"]):
        assert parte not in chave, "%r apareceu na chave %r" % (parte, chave)


def test_a_chave_tecnica_nao_e_o_numero_humano():
    """🔴 `numapo` (o número que o segurado ouve) e a chave técnica são coisas
    DIFERENTES — e trocar uma pela outra reprova.

    📊 A prova de que a chave não é o número: duas apólices com o MESMO `numapo`
    e `nosnum` diferentes recebem chaves diferentes; e uma chave não contém o
    número humano em nenhuma formatação.
    """
    contexto = _ctx(docs=[_auto_vigente("A-0001"), _resi_vigente("R-0002")])
    for apolice in contexto["apolices"]:
        assert apolice["chave"] != apolice["numapo"]
        assert apolice["numapo"] not in apolice["chave"]
        assert "0001" not in apolice["chave"] or apolice["numapo"] != "A-0001"

    mesmo_numero = _ctx(docs=[_doc_infocap(numapo="A-0001", nosnum="900001"),
                              _doc_infocap(numapo="A-0001", nosnum="900002")])
    chaves = {a["chave"] for a in mesmo_numero["apolices"]}
    assert len(chaves) == 2, "o mesmo número humano em apólices distintas colidiu"

    # trocar a chave pelo número humano reprova, com mensagem de gente
    with pytest.raises(ValueError) as erro:
        PC.escolher_apolice(contexto, "A-0001")
    assert "nunca o numero humano" in str(erro.value)


# --------------------------------------------------------------------------- #
# O contrato do módulo
# --------------------------------------------------------------------------- #
def test_o_contexto_tem_versao_origem_e_evidencia():
    contexto = _ctx(docs=[_auto_vigente()])
    assert contexto["versao"] == PC.VERSAO == 1
    assert contexto["source"] == contexto["evidencia"]["fonte"] == "infocap_customer_catalog"
    assert contexto["evidencia"]["consultado_em"].endswith("+00:00"), contexto["evidencia"]
    for campo in ("numapo", "ramo", "seguradora", "vigencia"):
        assert contexto["origem_por_campo"][campo] == "sistema_de_gestao"


def test_o_modulo_e_puro_nao_importa_banco_rede_nem_async():
    """⛔ CLAUDE.md §5: o construtor é uma peça pura. Se um dia alguém puser um
    `await`, uma sessão de banco ou um cliente HTTP aqui, este guarda reprova."""
    import inspect

    fonte = inspect.getsource(PC)
    for proibido in ("async def", "await ", "httpx", "requests", "supabase",
                     "AsyncSession", "get_db", "aiohttp"):
        assert proibido not in fonte, "o módulo deixou de ser puro: %r" % proibido


def test_a_chave_do_hmac_nunca_aparece_no_contexto_nem_na_excecao(monkeypatch):
    """⛔ CLAUDE.md §13.3: segredo só por presença/ausência."""
    segredo = "chave-de-teste-nao-e-segredo-real-9f3a"
    monkeypatch.setenv("POLICY_CONTEXT_HMAC_KEY", segredo)
    contexto = _ctx(docs=[_auto_vigente()])
    import json as _json

    assert segredo not in _json.dumps(contexto, default=str)
    assert PC.chave_de_plataforma_presente() is True

    # a chave dedicada tem precedência sobre a de plataforma
    monkeypatch.setenv("ENCRYPTION_KEY", "outra-chave-de-teste")
    assert _ctx(docs=[_auto_vigente()])["cliente_ref"] == contexto["cliente_ref"]

    monkeypatch.delenv("POLICY_CONTEXT_HMAC_KEY")
    assert _ctx(docs=[_auto_vigente()])["cliente_ref"] != contexto["cliente_ref"], (
        "trocar a chave tinha de trocar o pseudônimo — senão ela não entra no HMAC")
