"""SPEC-020 P3 + SPEC-025 — logica PURA da tool portal_action (sem langchain, testavel).

SPEC-025: os FATOS (placa, veiculo, chassi, endereco, seguradora) vem da InfoCap
(server-side, endpoint /itens + /cliente_cpf) — o LLM NUNCA fornece nem inventa
placa/local. O LLM so decide o que e julgamento: qual apolice (se varias), o dano
(peca/como/onde/descricao) e a data. normalize_insurer traduz o nome legado da
InfoCap para a marca que o portal usa (Liberty -> Yelum).

BLOCO 7.5 — A CONFERENCIA ACONTECE ANTES DE O PORTAL ABRIR.
📊 39 acionamentos, 33 paradas em `needs_human`, zero protocolos: o sistema abria
o portal e SO ENTAO descobria o que nao sabia. Agora `build_portal_params` so
devolve params quando nada do que o portal vai perguntar esta em aberto — e
quando falta, devolve a PERGUNTA pronta, em portugues de gente, para o agente
fazer ao segurado. O catalogo do que o portal pergunta mora num lugar so:
`app/services/perguntas_do_portal_de_vidros.py`.
"""
from __future__ import annotations

import unicodedata
from typing import Optional, Tuple

from app.services.perguntas_do_portal_de_vidros import (
    compor_descricao,
    mensagem_para_o_agente,
    o_que_falta,
    para_o_segurado,
)

# O QUE O AGENTE CONSEGUE DEVOLVER HOJE — e por que isso limita o que trava.
#
# Bloquear numa pergunta cuja resposta nao tem como chegar de volta cria o laco
# infinito que este repo ja pagou uma vez: o agente pergunta, o segurado
# responde, o schema da tool descarta a resposta, e a MESMA pergunta volta para
# sempre (era o defeito do `subservico_invalido` em `insurer_dispatch_tool`,
# provado em `test_o_acionamento_nao_pede_o_impossivel.py`).
#
# Estes cinco sao os campos de `PortalActionInput` que carregam resposta de
# pergunta. As especificas do 80% (pelicula, lado, trincado) NAO estao aqui
# porque a tool ainda nao tem campo para elas: elas continuam sendo COLETADAS
# (entram na mensagem que o agente le) e o transporte daqui para baixo ja existe
# — `params['especificos']` e lido por `vidros_lanternas.abrir_atendimento` e
# entregue ao cerebro adaptativo. Falta so um campo `especificos` na tool.
TRANSPORTAVEIS = ("cpf_cnpj", "data_dano", "peca", "como_ocorreu", "onde_ocorreu",
                  # SPEC-065 — a preferência de ONDE consertar entra aqui, e a
                  # razão é que uma parada no passo 7 é TERMINAL.
                  #
                  # 📊 O `Nº do atendimento` nasce no passo 7, ANTES da escolha
                  # da loja. Parar ali não é "tentar de novo depois": o pedido já
                  # existe na seguradora, e reexecutar cria um SEGUNDO.
                  #
                  # Sem esta linha, a preferência era coletada mas não cobrada:
                  # se ela fosse a ÚNICA coisa faltando, o agente nunca era
                  # avisado, o portal abria, e o fluxo morria na última tela —
                  # no lugar mais caro possível.
                  #
                  # E é a pergunta mais fácil de todas: "o técnico vai até você,
                  # ou você prefere levar numa oficina?" — qualquer pessoa
                  # responde sem consultar nada.
                  "onde_realizar_o_servico")


def _fold(s: Optional[str]) -> str:
    """ASCII-fold para o que sera DIGITADO no portal (cidade/endereco): o teste
    validado digitou 'Florianopolis' sem acento — formato comprovado no autocomplete."""
    return unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().strip()

# Sinonimos seguradora: nome/abreviacao da InfoCap -> marca no portal de vidros.
# Chave = fragmento (upper) testado por 'in'; ordem importa (mais especifico 1o).
_INSURER_ALIASES = (
    ("YELUM", "Yelum"),
    ("LIBERTY", "Yelum"),   # Liberty auto = Yelum (rebrand)
    ("LIBE", "Yelum"),
    ("TOKIO", "Tokio Marine"),
    ("PORTO", "Porto Seguro"),
    ("AZUL", "Azul"),
    ("ITAU", "Itau"),
    ("ITAÚ", "Itau"),
    ("MITSUI", "Mitsui"),
    ("MSIG", "Mitsui"),
    ("HDI", "HDI"),
    ("ALLIANZ", "Allianz"),
    ("BRADESCO", "Bradesco"),
    ("MAPFRE", "Mapfre"),
    ("SUHAI", "Suhai"),
    ("ZURICH", "Zurich"),
    ("SOMPO", "Sompo"),
)


def normalize_insurer(name: Optional[str]) -> str:
    """Nome da seguradora como o PORTAL a conhece. Fonte: seguradora da InfoCap."""
    raw = str(name or "").strip()
    up = raw.upper()
    for frag, canon in _INSURER_ALIASES:
        if frag in up:
            return canon
    return raw.title() if raw else ""


def build_portal_params(flat: dict, profile: dict, infocap: dict,
                        *, enviar_de_verdade: bool = False) -> Tuple[Optional[dict], Optional[str]]:
    """(params, erro). flat = decisoes do LLM (cpf, data, dano, placa_informada
    fallback). profile = perfil de acionamento da corretora. infocap = retorno REAL
    do vehicle lookup (policy/vehicle/client). erro != None quando falta fato.

    P-90 — `enviar_de_verdade` e o que vira `params['confirm']`, e ele NASCE
    False. Aqui morava um `"confirm": False` CRAVADO: nenhum caminho do
    repositorio conseguia liga-lo, entao o acionamento percorria o formulario
    inteiro e parava no 80% para sempre. 📊 9 dos 39 jobs chegaram exatamente
    ali ("cheguei na confirmacao (80%) — aprove para enviar") e a aprovacao nao
    existia em lugar nenhum.

    Continua nascendo False de proposito: quem decide e o CHAMADOR, que sabe se
    o agente de atendimento da corretora esta ligado (`portal_tool._arun`).
    Um default True aqui faria com que qualquer chamada nova — um teste, uma
    rotina, um caminho que ainda nao existe — abrisse pedido de verdade na
    seguradora por esquecimento. Esquecer tem de custar um pedido a menos,
    nunca um pedido a mais.

    A ordem e deliberada: primeiro os fatos que NAO dependem do segurado (perfil
    da corretora, seguradora, placa) — recusar por eles e barato e nao gasta a
    paciencia de ninguem. So depois a FICHA DO ACIONAMENTO, que precisa da
    InfoCap ja lida (o veiculo e o CEP saem de la) para saber o que NAO perguntar."""
    flat = flat or {}
    profile = profile or {}
    sol = {
        "relacao": "Corretor",
        "nome": str(profile.get("nome") or "").strip(),
        "email": str(profile.get("email") or "").strip(),
        "telefone": str(profile.get("telefone") or "").strip(),
        "cpf_cnpj": str(profile.get("cpf_cnpj") or "").strip(),
    }
    if not (sol["nome"] and sol["email"]):
        return None, ("A corretora ainda nao configurou o Perfil de Acionamento (nome + e-mail). "
                      "Configure em Personalizacao -> Corretora antes de acionar portais.")

    infocap = infocap or {}
    pol = infocap.get("policy") or {}
    veh = infocap.get("vehicle") or {}
    cli = infocap.get("client") or {}

    insurer = normalize_insurer(pol.get("seguradora") or pol.get("seguradora_abrev"))
    if not insurer:
        return None, "A InfoCap nao retornou a seguradora da apolice AUTO. Verifique a apolice."

    # Placa: SEMPRE da InfoCap. Fallback unico: o cliente informou (placa_informada)
    # porque a InfoCap nao tem — nunca a LLM por conta propria.
    placa = str(veh.get("placa") or "").strip().upper() or str(flat.get("placa_informada") or "").strip().upper()
    if not placa:
        return None, ("A apolice na InfoCap nao trouxe a PLACA do veiculo. Pergunte a placa ao segurado "
                      "e chame de novo com placa_informada.")

    # -------------------------------------------------------------------
    # BLOCO 7.5 — A FICHA DO ACIONAMENTO, conferida ANTES de abrir o portal.
    #
    # `ja_sei` junta as duas fontes: o que o segurado respondeu (via LLM) e o
    # que a InfoCap trouxe (veiculo e cep). E a segunda fonte que faz o produto
    # NAO perguntar a versao do carro nem o CEP a quem acabou de ter o vidro
    # quebrado — eles ja estao na apolice (mapa §8.3).
    # -------------------------------------------------------------------
    bruto = flat.get("especificos")
    especificos = {str(k): v for k, v in bruto.items()} if isinstance(bruto, dict) else {}
    ja_sei = {
        "cpf_cnpj": flat.get("cpf_cnpj"),
        "data_dano": flat.get("data_dano"),
        "peca": flat.get("peca"),
        "como_ocorreu": flat.get("como_ocorreu"),
        "onde_ocorreu": flat.get("onde_ocorreu"),
        "descricao": flat.get("descricao"),
        "veiculo": veh.get("veiculo"),
        "cep": cli.get("cep"),
        **especificos,
    }
    peca_dita = str(flat.get("peca") or "").strip()
    faltam = o_que_falta(peca_dita, ja_sei)
    # So trava no que o agente CONSEGUE responder de volta (ver TRANSPORTAVEIS).
    # O resto vai junto na mensagem, para ele coletar na mesma conversa.
    if [p for p in para_o_segurado(faltam) if p.campo in TRANSPORTAVEIS]:
        return None, mensagem_para_o_agente(faltam, peca_dita)

    endereco_txt = _fold(", ".join(p for p in (
        " ".join(x for x in (cli.get("logradouro"), cli.get("numero")) if x),
        cli.get("bairro"), f"{cli.get('cidade') or ''} {cli.get('estado') or ''}".strip(),
    ) if p))
    chassi = str(veh.get("chassi") or "").strip()

    params = {
        "insurer_name": insurer,
        "cpf_cnpj": str(flat.get("cpf_cnpj") or "").strip(),
        "placa": placa,
        "data_dano": str(flat.get("data_dano") or "").strip(),
        "solicitante": sol,
        "segurado": {
            "nome": str(cli.get("nome") or "").strip(),
            "apolice": str(pol.get("numapo") or "").strip(),
            "chassi": chassi,
            "ultimos_6_chassi": chassi[-6:] if chassi else "",
            "veiculo": str(veh.get("veiculo") or "").strip(),
            "cep": str(cli.get("cep") or "").strip(),
            "endereco": endereco_txt,
            "telefone": str(cli.get("telefone") or "").strip(),
            "email": str(cli.get("email") or "").strip(),
        },
        "dano": {
            "peca": str(flat.get("peca") or "").strip(),
            "como": str(flat.get("como_ocorreu") or "").strip(),
            "onde": str(flat.get("onde_ocorreu") or "").strip(),
            # 📊 O portal exige minimo de 30 caracteres aqui. Nao se pede ao
            # segurado que "escreva mais": o texto e COMPOSTO do que ele ja
            # disse (peca + relato + data + local). Relato dele com 30+ vai
            # inteiro, com as palavras dele.
            "descricao": compor_descricao(ja_sei),
        },
        # As respostas do passo 6 (80%), ja coletadas na conversa. A journey ja
        # le esta chave (`vidros_lanternas.abrir_atendimento`) e a entrega ao
        # cerebro adaptativo — era o unico pedaco do caminho que nascia vazio.
        "especificos": {k: v for k, v in especificos.items() if str(v or "").strip()},
        "local": {
            "estado": _fold(cli.get("estado")).upper(),
            "cidade": _fold(cli.get("cidade")).title(),
            "cep": str(cli.get("cep") or "").strip(),
        },
        # P-90 — O QUE DECIDE SE O PEDIDO NASCE DE VERDADE.
        #
        # `confirm=False` faz `run_adaptive` parar em `is_confirm_screen` (o 80%)
        # e devolver `needs_human`; `confirm=True` deixa o fluxo seguir ate o
        # passo 7, onde o Nº do atendimento aparece
        # (docs/canon/O-PORTAL-DE-VIDROS-TELA-POR-TELA.md §7).
        #
        # O valor vem de fora, do agente ligado — nao de uma constante. Era a
        # constante que fazia 39 acionamentos morrerem a 20% do fim.
        "confirm": bool(enviar_de_verdade),
    }
    return params, None


def format_result(job: dict) -> str:
    """Traduz o job terminado para uma frase natural para o agente.

    🔴 O NUMERO VEM PRIMEIRO, EM QUALQUER STATUS.

    📊 O `Nº do atendimento` nasce no passo 7, no topo da tela, ANTES da escolha
    da loja (mapa §7). Logo o pedido pode EXISTIR na seguradora num job que
    terminou `needs_human` (travou depois) ou ate `failed` (o navegador caiu
    depois). Nesses casos o segurado tem um atendimento aberto — e a unica coisa
    que o torna rastreavel e este numero chegar ate ele.

    Por isso a checagem do protocolo vem ANTES do `switch` de status: amarrar o
    numero ao status `done` faria o caso mais perigoso (pedido aberto + fluxo
    quebrado) ser justamente o unico que nao o diria.

    E a frase avisa para NAO reexecutar: repetir o fluxo cria um SEGUNDO
    atendimento, e isso nao se desfaz (mapa §9.5).
    """
    status = str((job or {}).get("status") or "")
    ev = (job or {}).get("evidence") or {}
    protocolo = str(ev.get("protocolo") or "").strip()
    if protocolo:
        passo7 = ev.get("passo7") if isinstance(ev.get("passo7"), dict) else {}
        recomendacao = str(passo7.get("recomendacao") or "").strip()
        if not recomendacao:
            recomendacao = ("Confirme com o segurado onde o servico sera feito (tecnico a domicilio "
                            "ou uma das lojas) — essa escolha e dele, e ela ainda esta em aberto.")
        # 🔴 OS OUTROS DOIS DADOS DA MESMA TELA — SPEC-071 BLOCO 6, 15/08/2026.
        #
        # 📊 A tela traz TRES coisas e so o protocolo chegava ao segurado:
        # a FRANQUIA (quanto ele paga) e o LINK DA VISTORIA (por onde ele manda
        # as fotos) ficavam no portal, obrigando a atendente a abri-lo.
        #
        # ⚠️ Cada um so aparece se foi LIDO. Frase sobre franquia sem franquia
        # lida seria o agente inventando valor — e valor inventado numa conversa
        # de seguro e o segurado descobrindo na hora de pagar.
        franquia = str(ev.get("franquia") or "").strip()
        link = str(ev.get("link_vistoria") or "").strip()
        extras = ""
        if franquia:
            extras += (f" A FRANQUIA e R$ {franquia} — diga o valor ao segurado ANTES "
                       "de ele escolher onde fazer o servico, porque e ele quem paga.")
        if link:
            extras += (f" As fotos do veiculo vao por este link: {link} — mande-o ao "
                       "segurado exatamente como esta, sem encurtar nem reescrever.")
        return (
            f"O atendimento FOI ABERTO na seguradora. Numero do atendimento: {protocolo}. "
            f"DIGA ESSE NUMERO AO SEGURADO — e com ele que ele acompanha e cobra o servico."
            f"{extras} "
            f"{recomendacao} "
            "NAO peca para eu abrir de novo: o pedido ja existe e repetir criaria um segundo "
            "atendimento na seguradora, que nao se desfaz."
        ).strip()
    if status == "done":
        return f"Acionamento concluido no portal. {ev.get('message') or 'protocolo gerado'}".strip()
    if status == "needs_human":
        stage = str(((job or {}).get("evidence") or {}).get("stage_80") or "")
        captured = (ev.get("message") or "").lower()
        if stage or "80%" in captured or "confirmacao" in captured:
            return ("Abri o pedido no portal com os dados da apolice e cheguei ate a etapa final de "
                    "confirmacao da peca — falta so a aprovacao final para enviar. Diga isso ao cliente "
                    "com clareza (pedido aberto, em confirmacao final).")
        opts = ev.get("opcoes")
        base = ev.get("message") or "o portal parou numa etapa que preciso confirmar"
        if opts:
            return f"No portal, preciso decidir '{ev.get('campo')}' entre: {', '.join(opts[:12])}. ({base})"
        return f"Cheguei ate uma etapa que precisa de revisao no portal ({base})."
    if status == "failed":
        return f"Nao consegui concluir no portal: {job.get('error') or ev.get('message') or 'erro'}."
    return "Enfileirei o acionamento; o worker de portais ainda nao processou (o acesso a portais esta desligado?)."


# ===========================================================================
# SPEC-065 bloco 7.2 — o portal nunca abre duas vezes o mesmo pedido.
#
# 📊 O `Nº do atendimento` nasce no passo 7, no TOPO da tela, antes da escolha
# da loja (docs/canon/O-PORTAL-DE-VIDROS-TELA-POR-TELA.md §7). O pedido ja
# existe na seguradora antes de o fluxo terminar — reexecutar nao corrige, cria
# um SEGUNDO atendimento.
#
# 📊 E ja aconteceu, em escala: 39 jobs `abrir_atendimento` para 5 pedidos
# distintos (Supabase dcajcvlzcjbmyapmklil, 04/08/2026). Um unico pedido tem 30
# jobs. Nao machucou ninguem so porque o gate do worker esta desligado.
#
# A chave identifica o PEDIDO, nao o job: corretora + placa + peca + data do
# dano. Logica pura aqui para poder ser testada sem banco, sem langchain e sem
# LLM — o guarda que so existe dentro do `_arun` e um guarda que ninguem
# consegue provar.
# ===========================================================================

_CHAVE_VERSAO = "v1"

# "vidro DA porta" e "vidro DE porta" sao a mesma peca. Estas palavras so ligam
# as outras; se ficarem na chave, viram dois pedidos que sao um.
_LIGACOES = frozenset({
    "de", "da", "do", "das", "dos", "e", "a", "o", "as", "os",
    "no", "na", "nos", "nas", "em", "um", "uma", "ao", "aos", "com",
})

_PECA_MAX = 80  # limita a entrada do indice; o LLM as vezes escreve uma frase


def normalizar_peca(texto: Optional[str]) -> str:
    """A peca como IDENTIDADE, nao como texto.

    Tira acento, caixa e pontuacao; joga fora as palavras de ligacao; ordena o
    que sobra. 'Vidro da Porta', 'vidro de porta' e 'porta - vidro' viram a
    mesma coisa.

    O que NAO e jogado fora, de proposito: os qualificadores. 'dianteira',
    'traseira', 'esquerdo', 'direito' e 'motorista' continuam na chave, porque
    o portal exige um pedido por item e por lado (§3 do mapa) — dois vidros
    quebrados sao dois atendimentos, e uma chave que os fundisse deixaria um
    lado quebrado sem ninguem saber.

    Ordenar e seguro aqui e nao noutro lugar: para dois pedidos DIFERENTES
    colidirem depois da ordenacao, eles teriam de ser anagramas de token — e
    peca diferente sempre troca uma palavra (dianteira/traseira), nunca so a
    ordem delas.
    """
    bruto = _fold(texto).lower()
    palavras = sorted(
        p for p in ("".join(c if c.isalnum() else " " for c in bruto)).split()
        if p and p not in _LIGACOES
    )
    return " ".join(palavras)[:_PECA_MAX]


def normalizar_placa(texto: Optional[str]) -> str:
    """'qjq-0a91' e 'QJQ0A91' sao o mesmo carro. So alfanumerico, maiusculo."""
    return "".join(c for c in _fold(texto).upper() if c.isalnum())


def normalizar_data(texto: Optional[str]) -> str:
    """'5/7/2026', '05-07-2026' e '05/07/2026' sao o mesmo dia.

    Nao vira digito puro: '5/7/2026' -> '572026' e '05/07/2026' -> '05072026'
    dariam chaves diferentes para a mesma data. Zero-padding resolve; formato
    que nao seja de tres partes cai no digito puro, que ao menos e estavel.
    """
    partes = [p for p in ("".join(c if c.isdigit() else " " for c in str(texto or ""))).split() if p]
    if len(partes) == 3:
        d, m, a = partes
        if len(a) == 2:
            a = "20" + a
        return f"{d.zfill(2)}{m.zfill(2)}{a.zfill(4)}"
    return "".join(partes)


def chave_de_idempotencia(params: Optional[dict], company_id: Optional[str] = None) -> str:
    """A impressao digital do PEDIDO. String vazia = sem chave (nao bloqueia nada).

    `company_id` vem separado porque `build_portal_params` nao o coloca em
    `params` — e mexer nela nao e desta tarefa. Aceita tambem `params['company_id']`
    para quem ja o tiver embutido.

    O que entra: corretora, placa, peca normalizada, data do dano.
    O que NAO entra, e por que:

      · a descricao livre — o segurado reconta a mesma historia com outras
        palavras ("quebraram o vidro" / "encontrei o carro arrombado") e isso
        criaria pedidos "diferentes" que sao o mesmo. Justamente o erro que
        custa caro: um segundo atendimento na seguradora nao se desfaz.
      · o `como_ocorreu` e o `onde_ocorreu` — mesma razao, sao julgamento do
        LLM sobre o mesmo fato.
      · a seguradora — ela e DERIVADA da apolice, que e derivada da placa. Se o
        `normalize_insurer` mudar de opiniao entre duas chamadas (Liberty ->
        Yelum), a chave mudaria sozinha e o guarda sumiria em silencio.
      · o CPF — tambem derivado: e o titular da apolice daquela placa.

    Retorna "" quando falta corretora, placa ou data — sem esses tres nao ha
    pedido para identificar, e uma chave meia-boca fundiria pedidos de carros
    diferentes. Na pratica e inalcancavel: `build_portal_params` ja recusa sem
    placa e sem data, e a tool sempre tem company_id. Fail-open de proposito:
    o guarda nunca pode ser o motivo de um atendimento nao acontecer.
    """
    params = params or {}
    empresa = str(company_id or params.get("company_id") or "").strip()
    placa = normalizar_placa(params.get("placa"))
    data = normalizar_data(params.get("data_dano"))
    if not (empresa and placa and data):
        return ""
    peca = normalizar_peca((params.get("dano") or {}).get("peca"))

    # 🔴 O LADO ENTRA NA CHAVE — SPEC-074, fechando a P-79.
    #
    # 📊 O portal diz, em texto na tela: *"se o item possuir lateralidade será
    # necessário abrir uma nova solicitação para o outro lado"*. Dois vidros
    # quebrados são DOIS pedidos legítimos.
    #
    # Sem o lado aqui, o segundo era barrado como repetição — e o segurado só
    # descobria quando o vidraceiro trocasse um vidro e fosse embora. A frase de
    # "já existe" ensinava a saída (*descreva a peça com o lado*), mas depender
    # de o modelo escrever a frase certa é exatamente o que esta SPEC desfaz.
    #
    # Só entra quando o lado NÃO está na peça: `normalizar_peca` já preserva
    # qualificadores (`esquerdo`, `motorista`, `dianteira`), então repetir aqui
    # criaria duas chaves para o mesmo pedido descrito de dois jeitos.
    lado = ""
    especificos = params.get("especificos")
    if isinstance(especificos, dict):
        bruto = str(especificos.get("lado_motorista_ou_carona") or "").strip()
        if bruto:
            marca = "motorista" if "motorista" in _fold(bruto) else (
                "carona" if "carona" in _fold(bruto) else _fold(bruto)[:16])
            if marca and marca not in peca:
                lado = marca

    # A versão sobe para `v2` porque a chave mudou de significado para peças com
    # lateralidade. As chaves `v1` históricas deixam de casar — e isso é o
    # desfecho desejado: 📊 são 34 jobs de julho, nenhum concluído, e um deles
    # bloquear um pedido legítimo de hoje é o defeito, não a proteção.
    return f"v2:{empresa}:{placa}:{data}:{peca}" + (f":{lado}" if lado else "")


def frase_de_pedido_ja_existente(job: Optional[dict]) -> str:
    """O que o agente diz quando o pedido JA existe — sem mentir.

    Nao inventa protocolo nem status: para um job que TERMINOU, o fato vem de
    `format_result` sobre o job real. Para um job ainda em curso o fato e
    omitido de proposito — `format_result` diria "Enfileirei o acionamento", e
    nesta chamada nada foi enfileirado; a frase mentiria sobre quem fez o que.

    O que esta funcao acrescenta e a explicacao de por que NAO abrimos outro, e
    a saida legitima para o caso em que o segurado realmente tem um segundo
    pedido (outra peca, outro lado).
    """
    job = job or {}
    status = str(job.get("status") or "")
    outro_pedido = (
        "Se o segurado quebrou OUTRA peca ou o OUTRO lado, isso e um pedido "
        "separado (o portal so aceita um item por atendimento): descreva a peca "
        "com o lado — ex.: 'vidro da porta traseira esquerda' — e chame de novo."
    )
    if status in ("done", "needs_human"):
        return (
            "Ja existe um atendimento aberto para este mesmo veiculo, peca e data do dano. "
            "NAO abri outro: o numero do atendimento nasce antes do fim do fluxo no portal, "
            "entao repetir criaria um SEGUNDO atendimento na seguradora, e isso nao se desfaz. "
            f"{format_result(job)} Repasse esse resultado ao segurado. {outro_pedido}"
        )
    return (
        "Ja existe um acionamento EM ANDAMENTO para este mesmo veiculo, peca e data do dano — "
        "nao abri outro. Diga ao segurado que o pedido dele ja esta em curso e que voce avisa "
        f"assim que houver resposta. {outro_pedido}"
    )
