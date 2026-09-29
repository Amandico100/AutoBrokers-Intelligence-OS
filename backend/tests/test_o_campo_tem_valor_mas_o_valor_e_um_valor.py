# -*- coding: utf-8 -*-
"""O campo tem valor — mas o valor É um valor?

SPEC-118, **o conserto único** de 26/09/2026. Um juiz e um red team, cegos um ao
outro, julgaram a SPEC e acharam quatro defeitos da MESMA família, num produto
que já tinha uma `GUARDA ANTI-INVENÇÃO` escrita depois de um incidente real:

```
o campo tem valor, então ninguém pergunta se o valor é um valor
```

## Os quatro, medidos ANTES do conserto (26/09/2026, motor real)

```
B1  par_de_coordenadas('nan','nan')   -> ('nan','nan')      state=ready_to_send
    par_de_coordenadas('nan','-48.5') -> ('nan','-48.5…')   meio par com NaN
    e o paramsJSON saía com "latitude":"nan" para a Porto
    CONTROLE: '0'/'0' -> None   ·   'inf'/'inf' -> None     (esses ERAM pegos)

C1  local_latitude=0 (o INTEIRO)      -> ok=True  params['latitude']="0"
    causa: `str(0 or "")` é `''` — o zero é falsy, a conferência nunca rodava

B2  pin {name:'Estacionamento', address:'Rod. SC-401, km 5'}
      -> local_cidade='Estacionamento'  e a Porto abria o chamado nessa "cidade"

B3  estado="ZZ" · cep="0" · numero="nao sei" · cidade="48.5477" · rua com
    quebra de linha  ->  TODOS com ok=True
    CONTROLE: rua=""  -> ok=False   (só a AUSÊNCIA era conferida)
```

## O que este arquivo afirma, e como

🔴 **Tudo chama o MOTOR** (CLAUDE.md §9.4): o pin passa pelo produtor REAL
(`whatsapp/evolution_inbound._texto_de_localizacao`), o texto pelo parser REAL
(`corridor_playbooks.parse_address_br`), os slots pela sessão REAL
(`insurer_dispatch_service.new_dispatch_session`) e a resposta pelo montador REAL
(`montar_resposta_de_flow`), com o mapa REAL da Porto. Nenhum helper daqui
reimplementa régua de produto.

🔴 **E cada afirmação tem a sua LINHA DE CONTROLE** (CLAUDE.md §9.2): o caso
honesto, ao lado do desonesto, no mesmo turno. Sem ela, um guarda que recusa
tudo passaria por guarda — e o primeiro valor legítimo recusado ensinaria a
desligá-lo.

⚠️ Nada de PII e nenhum nome de corretora (CLAUDE.md §13.3/§13.9): CPF de teste
canônico, placa em formato legal, telefone de padrão sequencial, endereços do
próprio acervo mascarado.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]

PORTO = "porto-auto-whatsapp@v1"
SUB = "guincho"
#: 📊 O formulário de endereço da Porto — captura de 21/09/2026 10:24.
FLOW_ENDERECO = "709854848132894"
#: 📊 A coordenada do pin, 6 casas (≈ 11 cm). Centro de Florianópolis.
PIN_LAT = "-27.588016"
PIN_LON = "-48.544253"


def _carregar(dotted: str, rel: str):
    """O arquivo REAL de produção, pelo caminho, sem subir `app.agents`."""
    if str(RAIZ) not in sys.path:
        sys.path.insert(0, str(RAIZ))
    spec = importlib.util.spec_from_file_location(dotted, RAIZ / rel)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[dotted] = modulo
    spec.loader.exec_module(modulo)
    return modulo


PB = _carregar("app.services.corridor_playbooks", "app/services/corridor_playbooks.py")
DS = _carregar("app.services.insurer_dispatch_service",
               "app/services/insurer_dispatch_service.py")
INB = _carregar("app.services.whatsapp.evolution_inbound",
                "app/services/whatsapp/evolution_inbound.py")
TOOL = _carregar("app.agents.tools.insurer_dispatch_tool",
                 "app/agents/tools/insurer_dispatch_tool.py")

#: Um caso de guincho com tudo verdadeiro e NADA de ninguém.
CASO = {
    "titular_cpf": "52998224725",
    "veiculo_placa": "ABC1D23",
    "local_atual": "R. Exemplo Um, 0, Centro, Florianopolis - SC, 88000-000",
    "local_destino": "Oficina Central, Rua B, 50, Sao Jose - SC",
    "problema_descricao": "o carro nao liga",
    "telefone_contato": "48991234567",
    "pessoa_no_local": "quem esta com o veiculo",
    "local_seguro": "sim",
    # SPEC-120 · D9 (CLAUDE.md §9.3): o portão da porto passou a cobrar o táxi
    #    depois do guincho — o "caso completo" ganhou a resposta do segurado.
    "taxi_apos_guincho": "não",
    "quando": "agora",
    "ponto_referencia": "em frente ao mercado",
    # 🔴 O PIN ENTRA NO CASO BASE, e isto não é detalhe de arranjo.
    #
    # 📊 Sem ele, `latitude`/`longitude` faltam e o montador devolve `ok=False`
    #    para TODO caso — inclusive os desonestos. Os guardas de B3 ficariam
    #    verdes **pelo motivo errado**, que é a classe de defeito que este
    #    arquivo inteiro existe para fechar (CLAUDE.md §9.3: um guarda que não
    #    tem como falhar não guarda nada; um que passa por OUTRA razão é pior,
    #    porque parece guardar).
    #    Com o pin no caso base, a única coisa que pode faltar é o campo em
    #    exame — e por isso cada asserção NOMEIA a chave que espera em `missing`.
    "local_latitude": PIN_LAT,
    "local_longitude": PIN_LON,
}


def _sessao(**extra):
    slots = dict(CASO)
    slots.update(extra)
    return DS.new_dispatch_session(case_id="conserto", company_id="conserto",
                                   playbook_ref=PORTO, subservice=SUB, slots=slots)


def _montar(slots):
    schema = PB.native_flow(PB.get_playbook(PORTO), FLOW_ENDERECO)
    assert schema is not None, "o mapa da Porto saiu do playbook"
    return PB.montar_resposta_de_flow(schema, slots, FLOW_ENDERECO)


def _fecha_com(lat, lon):
    """(estado da sessão, ok do montador, a latitude que iria à seguradora)."""
    s = _sessao(local_latitude=lat, local_longitude=lon)
    m = _montar(s["slots"])
    return s["state"], m["ok"], (m["params"] or {}).get("latitude")


# ===========================================================================
# B1 · `nan` NÃO É COORDENADA — E A FAMÍLIA INTEIRA, NÃO SÓ A PALAVRA
# ===========================================================================

@pytest.mark.parametrize("lat,lon", [
    ("nan", "nan"), ("NaN", "nan"), ("-nan", "nan"), ("NAN", "NAN"),
    ("nan", "-48.5"), ("-27.5", "nan"),          # o MEIO PAR também
    (float("nan"), float("nan")),                 # e o float, não só o texto
    (float("nan"), -48.544253),
])
def test_a_familia_do_nan_NAO_e_um_par_de_coordenadas(lat, lon):
    """🔴 Toda comparação com `nan` devolve `False` — inclusive `abs(nan) > 90`
    e `abs(nan) < 1e-6`, que eram as duas únicas conferências. O `nan`
    atravessava as duas **por definição do IEEE 754**, não por descuido.

    ⚠️ A lista cobre a FAMÍLIA (`nan`, `-nan`, `NaN`, `NAN`, meio par, float),
    porque o defeito não é a palavra: é a conferência ser uma COMPARAÇÃO.
    """
    assert PB.par_de_coordenadas(lat, lon) is None


def test_o_nan_NAO_fecha_o_formulario_da_porto():
    """E o fio inteiro: a sessão não nasce pronta e a resposta não sai."""
    estado, ok, latitude = _fecha_com("nan", "nan")
    assert estado != "ready_to_send", estado
    assert ok is False
    assert latitude is None


@pytest.mark.parametrize("lat,lon,porque", [
    ("0", "0", "o Golfo da Guine (o default do protobuf)"),
    (0, 0, "🔴 C1 — o zero INTEIRO, que `or \"\"` confundia com vazio"),
    (0.0, 0.0, "🔴 C1 — e o zero FLOAT"),
    ("inf", "inf", "o infinito"),
    ("91", "10", "fora da faixa do planeta"),
    ("-27.5", "", "meio par"),
])
def test_o_que_ja_era_recusado_CONTINUA_recusado(lat, lon, porque):
    """A linha de controle do conserto: nada foi afrouxado para o `nan` caber."""
    estado, ok, latitude = _fecha_com(lat, lon)
    assert (estado, ok, latitude) == ("preparing", False, None), porque


def test_CONTROLE_o_pin_HONESTO_continua_fechando_o_formulario():
    """🔴 Sem esta linha o arquivo não prova nada: um guarda que recusa TUDO
    recusaria também o acionamento que funciona, e o primeiro guincho perdido
    ensinaria a desligá-lo (CLAUDE.md §9.2)."""
    estado, ok, latitude = _fecha_com(PIN_LAT, PIN_LON)
    assert (estado, ok, latitude) == ("ready_to_send", True, PIN_LAT)


def test_CONTROLE_a_coordenada_numerica_HONESTA_tambem_fecha():
    """O conserto do zero numérico não pode recusar o número honesto."""
    estado, ok, latitude = _fecha_com(-27.588016, -48.544253)
    assert (estado, ok) == ("ready_to_send", True)
    assert latitude == PIN_LAT


# ===========================================================================
# B2 · O NOME DO LUGAR DO PIN NÃO É A CIDADE DO CHAMADO
# ===========================================================================

def _pin(name: str, address: str, lat=-27.588016, lon=-48.544253) -> str:
    """O texto que o PRODUTOR REAL escreve para um `locationMessage`."""
    texto = INB._texto_de_localizacao({"locationMessage": {   # noqa: SLF001
        "degreesLatitude": lat, "degreesLongitude": lon,
        "name": name, "address": address}})
    assert texto, "o produtor devolveu None para um pin com coordenada"
    return texto


@pytest.mark.parametrize("name,address", [
    ("Estacionamento", "Rod. SC-401, km 5"),          # 🔴 o caso mais comum
    ("Posto Shell", "Rod. BR-101, km 210"),
    ("Shopping Iguatemi", ""),                        # pin SÓ com nome
    ("Borracharia do Zé", "Servidao Sem Nome"),
])
def test_o_nome_do_lugar_do_pin_NUNCA_vira_cidade_nem_rua(name, address):
    """📊 O defeito medido: `{name:'Estacionamento', address:'Rod. SC-401, km 5'}`
    virava `local_cidade='Estacionamento'`, e a Porto abria o chamado na cidade
    de "Estacionamento" — sem travar, porque o portão não cobra um campo que
    está PREENCHIDO. CLAUDE.md §9.5.

    ⚠️ O nome continua NO TEXTO (quem lê a conversa precisa dele); o que ele
    deixa de ser é campo de endereço.
    """
    texto = _pin(name, address)
    assert name in texto, ("o nome do lugar sumiu do texto — ele é informação "
                           "boa para quem lê a conversa, e só não é endereço")
    fora = PB.parse_address_br(texto)
    assert fora.get("cidade") != name, fora
    assert fora.get("rua") != name, fora
    assert fora.get("bairro") != name, fora

    sessao = _sessao(local_atual=texto, local_latitude=None, local_longitude=None)
    assert sessao["slots"].get("local_cidade") != name, sessao["slots"]
    assert sessao["slots"].get("local_rua") != name, sessao["slots"]


def test_o_pin_de_RODOVIA_vai_a_uma_pessoa_em_vez_de_inventar_a_cidade():
    """🔴 O desfecho honesto: sem cidade, o portão COBRA a cidade. O caso pára
    e alguém pergunta — em vez de o guincho sair para "Estacionamento"."""
    texto = _pin("Estacionamento", "Rod. SC-401, km 5")
    sessao = _sessao(local_atual=texto)
    assert sessao["state"] != "ready_to_send"
    assert "local_cidade" in (sessao.get("missing_slots") or []), sessao.get("missing_slots")
    # e o agente pede em português, sem nome de campo cru
    pedido = " ".join(DS.como_pedir_ao_segurado(PORTO, sessao["missing_slots"]))
    assert "local_cidade" not in pedido, pedido


def test_CONTROLE_o_pin_com_ENDERECO_DE_VERDADE_continua_decomposto():
    """A linha de controle de B2: o pin cujo `address` tem logradouro, número,
    bairro, cidade e UF continua virando os cinco campos — inclusive quando o
    `name` vem junto. 📊 Este caso JÁ saía certo antes do conserto (o
    `_STREET_RE` achava a rua), e continua saindo."""
    texto = _pin("Posto Shell",
                 "R. Rafael Bandeira, 41 - Centro, Florianopolis - SC, 88015-530")
    fora = PB.parse_address_br(texto)
    assert fora.get("rua") == "R. Rafael Bandeira", fora
    assert fora.get("numero") == "41", fora
    assert fora.get("bairro") == "Centro", fora
    assert fora.get("cidade") == "Florianopolis", fora
    assert fora.get("uf") == "SC", fora
    assert fora.get("cep") == "88015-530", fora


def test_CONTROLE_a_coordenada_do_pin_continua_sendo_LIDA():
    """O conserto mexeu nas LINHAS do texto do pin. A coordenada é lida de uma
    delas — se a ordem quebrasse, o formulário deixaria de fechar em silêncio."""
    texto = _pin("Posto Shell",
                 "R. Rafael Bandeira, 41 - Centro, Florianopolis - SC, 88015-530")
    assert PB.coordenada_do_pin(texto) == (PIN_LAT, PIN_LON)
    # ⚠️ O par vem do TEXTO, não do caso base: as duas chaves são apagadas de
    #    propósito, senão esta asserção passaria sem o pin ter sido lido.
    sessao = _sessao(local_atual=texto, local_latitude=None, local_longitude=None)
    assert sessao["slots"].get("local_latitude") == PIN_LAT, sessao["slots"]


def test_o_contrato_entre_o_produtor_e_o_parser_NAO_pode_quebrar_calado():
    """🔴 O rótulo é escrito num arquivo e saltado noutro. 📊 Se os dois textos
    divergirem, o defeito de 26/09 volta **em silêncio** — então o guarda mede
    o par, não cada lado."""
    rotulo = INB._ROTULO_DO_NOME_DO_PIN                      # noqa: SLF001
    linha = "%s: Estacionamento" % rotulo
    assert PB._LINHA_DO_NOME_DO_PIN_RE.search(linha), (      # noqa: SLF001
        "o parser não salta a linha que o produtor escreve: %r" % linha)
    assert not PB._LINHA_DO_NOME_DO_PIN_RE.search(           # noqa: SLF001
        "R. Rafael Bandeira, 41 - Centro"), (
        "🔴 CONTROLE: o regex do rótulo casaria um endereço de verdade")


# ===========================================================================
# B3 · OS SEIS CAMPOS NOVOS PASSAM PELA MESMA GUARDA DA PLACA E DO CPF
# ===========================================================================

@pytest.mark.parametrize("slot,valor,chave,porque", [
    ("local_uf", "ZZ", "estado", "ZZ nao e uma UF — e `_UFS` estava no arquivo"),
    ("local_uf", "S", "estado", "uma letra nao e sigla de estado"),
    ("local_cep", "0", "cep", "o mapa DECLARA `formato: 00000-000` e ninguem lia"),
    ("local_cep", "8800", "cep", "quatro digitos nao sao um CEP"),
    ("local_numero", "nao sei", "numero_residencia", "'nao sei' nao e um numero"),
    ("local_numero", "perto da padaria", "numero_residencia", "nem isso"),
    ("local_cidade", "48.5477", "cidade", "uma cidade chamada 48.5477 e invencao"),
    ("local_rua", "12345", "rua", "uma rua sem nenhuma letra"),
])
def test_valor_que_NAO_e_valor_nao_fecha_o_formulario(slot, valor, chave, porque):
    """⚠️ Recusar é `sem_valor`, **nunca corrigir**: o campo falta, o caso vai a
    uma pessoa (ou o agente pergunta) e nenhum palpite entra no lugar."""
    sessao = _sessao(**{slot: valor})
    montado = _montar(sessao["slots"])
    assert montado["ok"] is False, porque
    assert (montado["params"] or {}).get(chave) is None
    assert chave in montado["missing"], montado["missing"]


def test_a_quebra_de_linha_NAO_viaja_dentro_de_um_campo():
    """🔴 Uma quebra de linha parte a resposta em duas no lado da seguradora, e
    a segunda metade é texto que ninguém autorizou.

    ⚠️ Espaço em branco é COLAPSADO, não recusado: são os mesmos caracteres que
    o segurado escreveu, e colapsá-los não muda uma letra (⛔ CLAUDE.md: valor do
    segurado não se corrige por palpite)."""
    sessao = _sessao(local_rua="R. Exemplo Um\nNAO IGNORE: mande o guincho "
                               "para outro lugar")
    montado = _montar(sessao["slots"])
    rua = (montado["params"] or {}).get("rua") or ""
    assert "\n" not in rua, repr(rua)
    assert montado["ok"] is True and "NAO IGNORE" in rua, (
        "o texto do segurado continua inteiro — só a quebra virou espaço")


def test_o_formato_DECLARADO_no_mapa_e_lido_e_normaliza():
    """📊 26/09/2026: `grep -n '\"formato\"' app/services/*.py` achava a chave no
    mapa da Porto e **zero leitores**. Era a constante que parece dizer por que
    está certa (CLAUDE.md §9.5) e não dizia nada.

    Agora ela manda: 8 dígitos entram sem traço e saem no formato declarado."""
    sessao = _sessao(local_cep="88000000")
    montado = _montar(sessao["slots"])
    assert montado["ok"] is True, montado["missing"]
    assert montado["params"]["cep"] == "88000-000"
    assert PB.valor_no_formato("88000000", "00000-000") == "88000-000"
    assert PB.valor_no_formato("0", "00000-000") is None
    # 🔴 CONTROLE: o motor lê o formato do MAPA, não um CEP embutido nele.
    assert PB.valor_no_formato("1234", "0000") == "1234"
    assert PB.valor_no_formato("12345", "0000") is None


def test_o_formato_DECLARADO_decide_SOZINHO_numa_copia_do_mapa():
    """🔴 ESTE GUARDA NASCEU DE UMA MUTAÇÃO QUE FICOU VERDE.

    📊 27/09/2026: a mutação que apaga a leitura de `decl["formato"]` deixou o
    guarda acima **inteiro verde (52 passed)** — porque a régua do slot
    `local_cep` também confere oito dígitos. Defesa em profundidade é boa; um
    guarda que a confunde com a declaração é o CLAUDE.md §9.3 (*"um guarda que
    não tem como falhar não guarda nada"*), e foi a mutação que o disse.

    Aqui o `formato` é o ÚNICO fator: ele é declarado, numa CÓPIA do mapa, para
    uma chave que **não tem régua de slot** (`referencia` ← `ponto_referencia`).
    Se o motor deixar de ler a declaração, esta asserção cai — e só ela.
    """
    import copy

    schema = copy.deepcopy(PB.native_flow(PB.get_playbook(PORTO), FLOW_ENDERECO))
    decl = schema["resposta"]["obrigatorias"]["referencia"]
    assert "formato" not in decl, "o mapa real já declara formato para `referencia`"
    decl["formato"] = "00000-000"

    # ⚠️ Texto que NÃO cabe no formato declarado: a chave falta, e o motivo é
    #    `formato_invalido` — não `sem_valor`, porque valor existe.
    sessao = _sessao()
    ruim = PB.montar_resposta_de_flow(schema, sessao["slots"], FLOW_ENDERECO)
    assert ruim["ok"] is False, (
        "o `formato` declarado no mapa NÃO foi lido: `referencia` = %r passou "
        "com oito dígitos exigidos" % ((ruim["params"] or {}).get("referencia"),))
    assert "referencia" in ruim["missing"], ruim["missing"]
    motivos = {d["campo"]: d["motivo"] for d in ruim["missing_detail"]}
    assert motivos.get("referencia") == "formato_invalido", motivos

    # 🔴 CONTROLE 1 — o MESMO valor no formato declarado passa, normalizado.
    bom = PB.montar_resposta_de_flow(
        schema, {**sessao["slots"], "ponto_referencia": "88000000"}, FLOW_ENDERECO)
    assert bom["ok"] is True, bom["missing"]
    assert bom["params"]["referencia"] == "88000-000", bom["params"]["referencia"]

    # 🔴 CONTROLE 2 — o mapa REAL (sem `formato` em `referencia`) continua
    #    aceitando o ponto de referência em português. Sem esta linha, o teste
    #    acima passaria num motor que recusasse texto livre sempre.
    real = _montar(sessao["slots"])
    assert real["ok"] is True, real["missing"]
    assert real["params"]["referencia"] == "em frente ao mercado"


@pytest.mark.parametrize("slot,valor", [
    ("local_uf", "sc"),                 # minúscula é a MESMA sigla
    ("local_cep", "88000-000"),
    ("local_numero", "0"),              # 📊 2 das 3 capturas da Porto têm "0"
    ("local_numero", "1235"),
    ("local_numero", "120A"),
    ("local_numero", "s/n"),
    ("local_cidade", "Florianopolis"),
    ("local_cidade", "São José dos Pinhais"),
    ("local_rua", "R. Exemplo Um"),
])
def test_CONTROLE_o_valor_HONESTO_continua_passando(slot, valor):
    """A metade que impede o guarda de virar carimbo: cada régua tem de deixar
    passar o valor legítimo — inclusive o `numero_residencia = "0"` que a
    própria Porto grava quando não há número."""
    sessao = _sessao(**{slot: valor})
    montado = _montar(sessao["slots"])
    assert montado["ok"] is True, (slot, valor, montado["missing"])


def test_CONTROLE_o_caso_inteiro_HONESTO_continua_saindo_com_as_dez_chaves():
    """📊 As 10 chaves presentes em 3 de 3 capturas de 21/09 e 14/09/2026."""
    sessao = _sessao()
    montado = _montar(sessao["slots"])
    assert montado["ok"] is True, montado["missing"]
    dez = {"rua", "numero_residencia", "bairro", "cidade", "estado", "cep",
           "referencia", "label_endereco_completo", "latitude", "longitude"}
    assert dez <= set(montado["params"]), dez - set(montado["params"])
    assert "ZZ" not in montado["params"]["label_endereco_completo"]


# ===========================================================================
# B3 · E A GUARDA ANTI-INVENÇÃO DA FERRAMENTA CONHECE OS SEIS
# ===========================================================================

@pytest.mark.parametrize("campo,valor", [
    ("local_uf", "ZZ"), ("local_cep", "0"), ("local_numero", "nao sei"),
    ("local_cidade", "48.5477"), ("local_rua", "1234"), ("local_bairro", "999"),
])
def test_a_guarda_anti_invencao_da_ferramenta_recusa_os_seis(campo, valor):
    """🔴 A guarda nasceu no incidente de 10/07/2026 (*"placa e telefone
    inventados foram parar na seguradora"*) e conferia TRÊS campos. A F3/F4
    acrescentou SEIS que vão à seguradora e nenhum entrou — no mesmo commit em
    que o comentário logo acima dela explica por que ela existe."""
    ferramenta = TOOL.InsurerDispatchTool(company_id="corretora-A")
    fora = ferramenta._run(                                   # noqa: SLF001
        insurer_key="porto", line_kind="auto", subservice=SUB,
        dados_confirmados=True,
        **{**{k: v for k, v in CASO.items() if k != "ponto_referencia"},
           campo: valor})
    assert fora.get("status") == "missing_data", fora
    assert fora.get("missing") == [campo], fora
    assert "NÃO envie isso à seguradora" in str(fora.get("content") or "")


def test_CONTROLE_a_ferramenta_aceita_os_seis_HONESTOS():
    """Sem esta, a de cima provaria só que a ferramenta sabe dizer não."""
    ferramenta = TOOL.InsurerDispatchTool(company_id="corretora-A")
    fora = ferramenta._run(                                   # noqa: SLF001
        insurer_key="porto", line_kind="auto", subservice=SUB,
        dados_confirmados=True,
        local_uf="SC", local_cep="88000-000", local_numero="0",
        local_cidade="Florianopolis", local_rua="R. Exemplo Um",
        local_bairro="Centro",
        **{k: v for k, v in CASO.items() if k != "ponto_referencia"})
    assert fora.get("status") != "missing_data", fora
