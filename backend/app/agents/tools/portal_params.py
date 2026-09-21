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
    DO_SEGURADO,
    catalogo_de_familias,
    compor_descricao,
    mensagem_para_o_agente,
    o_que_falta,
    para_o_segurado,
    pergunta_do_campo,
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
                  "onde_realizar_o_servico",
                  # 🔴 SPEC-EXTRA-001.10 P0-5 — A CIDADE DO SERVIÇO TRAVA.
                  #
                  # 📊 `CodigoCidade` é chave obrigatória do PATCH nas 4
                  # capturas de 20/09/2026, e a cidade é perguntada em 8 de 8
                  # blocos do roteiro da atendente humana. Sem ela o robô entra
                  # no portal e para numa tela que ninguém consegue responder
                  # por ele — o CEP da apólice é o de CASA, e quem quebra o
                  # vidro viajando conserta onde está.
                  "cidade_para_o_servico",
                  # 🔴 N-2 (D-E00110-02) — só existe para para-brisa, e por
                  # isso não precisa de exceção aqui: a pergunta só nasce na
                  # família do para-brisa (`_ESPECIFICAS_POR_IDENTIDADE`), e o
                  # que não nasce não trava. 📊 Sem ela a journey para DEPOIS de
                  # o número do atendimento existir.
                  "aceita_reparo",
                  # 🔴 P1-5 — na lataria o `CodigoAtendimento` nasce logo após
                  # o PATCH, e é o PATCH que leva `ServicosMartelinhoLataria`.
                  # Perguntar a lista de peças depois é conversar sobre um
                  # pedido que já nasceu. Mesma regra: só a família lataria a faz.
                  "pecas_lataria")

# ⚠️ ESTA É A VERDADE ÚNICA, e a `description` da tool é GERADA dela.
#
# 📊 Até 20/09/2026 três lugares discordavam: o prompt mandava chamar com 3
# coisas (`prompts.py:136`), `TRANSPORTAVEIS` recusava por 6, e a `description`
# listava tudo à mão. O modelo lia o prompt — o mais errado dos três — e
# recebia de volta um pedido do que o prompt dissera que não precisava.
#
# Venceu a lista que é CÓDIGO EXECUTADO. O prompt aponta para a ferramenta, e a
# ferramenta se descreve a partir daqui. Só há uma forma de as três voltarem a
# divergir: alguém reescrever o texto à mão — e o guarda de FORMA reprova isso.


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


#: 🔴 O PONTO DE TROCA da tabela de apelidos — SPEC-EXTRA-001.10 P0-4.
#:
#: A fatia A desta SPEC escreve `portal_worker.journeys.vidros_api`, que resolve
#: a seguradora POR DADO (a partir do `GET /seguradoras/` ao vivo, 📊 38 itens) e
#: publica `apelidos_de_seguradora()` / `resolver_seguradora()`.
#:
#: ⚠️ **E as duas funções respondem perguntas DIFERENTES, medido em 20/09/2026**
#: com o arquivo já no disco:
#:
#:     apelidos_de_seguradora()[1]   ("PORTO SEGURO", "PORTO")        ← SLUG da API
#:     _INSURER_ALIASES              ("PORTO",        "Porto Seguro") ← NOME de tela
#:
#: Ligar uma na outra hoje faria `normalize_insurer("LIBERTY SEGUROS S/A")`
#: devolver `LIBERTY` em vez de `Yelum` — 📊 exatamente o que aconteceu quando o
#: import foi consumido de verdade, com `test_spec020_portal_action.py` vermelho
#: em cinco linhas. Por isso o interruptor existe e nasce DESLIGADO: a troca é
#: de uma linha, e é do gerente, depois que A fechar o contrato de
#: `resolver_seguradora` (que devolve `{"slug", "codigo", "nome_de_tela"}` — é
#: `nome_de_tela` o que esta função precisa, não o slug).
#:
#: 🔴 A LINHA A TROCAR: `_APELIDOS_VEM_DA_API = True`, e `_apelidos_do_portal`
#: passa a ler `nome_de_tela` de `resolver_seguradora`. Nada mais muda aqui.
_APELIDOS_VEM_DA_API = False


def _apelidos_do_portal() -> Tuple[Tuple[str, str], ...]:
    """Os apelidos em vigor. Hoje: a tabela local (ver `_APELIDOS_VEM_DA_API`).

    ⛔ Duas tabelas não podem CONVIVER (CLAUDE.md §5): esta função é a ÚNICA
    leitora de `_INSURER_ALIASES`, e a consolidação é ligar o interruptor —
    nunca escrever um terceiro mapa em algum outro arquivo.

    ⚠️ Import TARDIO e tolerante quando ligado: `portal_worker` viaja na imagem
    do smith-api (📊 `backend/Dockerfile:11 COPY . .`), mas um `ImportError` no
    topo tiraria a tool inteira do ar por causa de uma tabela de sinônimos.
    """
    if not _APELIDOS_VEM_DA_API:
        return _INSURER_ALIASES
    try:
        from portal_worker.journeys.vidros_api import apelidos_de_seguradora

        vivos = tuple((str(k).upper(), str(v)) for k, v in apelidos_de_seguradora())
        return vivos or _INSURER_ALIASES
    except Exception:  # noqa: BLE001
        return _INSURER_ALIASES


def normalize_insurer(name: Optional[str]) -> str:
    """Nome da seguradora como o PORTAL a conhece. Fonte: seguradora da InfoCap."""
    raw = str(name or "").strip()
    up = raw.upper()
    for frag, canon in _apelidos_do_portal():
        if frag in up:
            return canon
    return raw.title() if raw else ""


# ===========================================================================
# A CIDADE DO SERVIÇO — texto de gente virando {uf, cidade}
# ===========================================================================
# 📊 O segurado escreve "Joinville/SC", "Joinville - SC", "joinville sc" ou só
# "Joinville". Os quatro são a mesma cidade, e nenhum deles é um `CodigoCidade`:
# quem resolve o código é a journey, por `GET /ufs` → `GET /cidades?UF=`.
#
# ⚠️ Quando o texto não traz o estado, o padrão é o da APÓLICE — e isso fica
# DECLARADO em `local.cidade_servico_uf_de`, nunca silencioso. Um estado
# assumido em silêncio manda o pedido para a cidade homônima de outro estado, e
# "Campinas/SP" × "Campinas/RJ" não se desfaz depois de o pedido nascer.
_UFS = ("AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS",
        "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC",
        "SE", "SP", "TO")


def cidade_e_uf_do_servico(texto: Optional[str],
                           uf_da_apolice: Optional[str] = None) -> Tuple[str, str, str]:
    """(cidade, uf, de_onde_veio_a_uf). Tudo "" quando o texto não diz cidade.

    `de_onde_veio_a_uf` é "segurado" quando ele escreveu o estado e "apolice"
    quando caiu no padrão — a distinção existe para que a journey e o dossiê
    saibam o que foi ASSUMIDO.
    """
    bruto = _fold(texto)
    # Separadores que a gente usa na vida: "/", "-", vírgula e o próprio espaço.
    pedacos = [p.strip() for p in "".join(
        " " if c in "/,-–—|" else c for c in bruto).split() if p.strip()]
    if not pedacos:
        return "", "", ""

    uf = ""
    origem = ""
    if len(pedacos) > 1 and pedacos[-1].upper() in _UFS:
        uf, origem = pedacos[-1].upper(), "segurado"
        pedacos = pedacos[:-1]
    if not uf:
        padrao = _fold(uf_da_apolice).upper()
        if padrao in _UFS:
            uf, origem = padrao, "apolice"

    # "rio de janeiro" → "Rio de Janeiro", não "Rio De Janeiro": o autocomplete
    # do portal casa por texto, e a preposição maiúscula é ruído gratuito.
    palavras = [p.title() for p in pedacos]
    palavras = [palavras[0]] + [
        (p.lower() if p.lower() in _LIGACOES else p) for p in palavras[1:]]
    cidade = " ".join(palavras)
    if not cidade:
        return "", "", ""
    return cidade, uf, origem


def descricao_da_tool() -> str:
    """A `description` de `portal_action`, GERADA de `TRANSPORTAVEIS` + as famílias.

    🔴 P0-5, a reconciliação das três verdades. Enquanto este texto era escrito
    à mão, ele era a terceira opinião sobre o que o portal pede — e a que o
    modelo lia junto com o prompt. Agora ele é uma PROJEÇÃO da lista que
    realmente recusa o payload: acrescentar um campo a `TRANSPORTAVEIS` muda a
    descrição no mesmo commit, sem ninguém lembrar de nada.

    ⚠️ O que continua escrito à mão são as PROIBIÇÕES e o comportamento da
    ferramenta — eles não derivam de campo nenhum e não podem sumir numa
    geração automática.
    """
    trava = []
    for campo in TRANSPORTAVEIS:
        p = pergunta_do_campo(campo)
        if p is None or p.de_quem != DO_SEGURADO:
            continue
        trava.append(f"{campo} ({p.texto.split('?')[0].strip()[:90]}…)")
    familias = ", ".join(sorted(catalogo_de_familias()))
    return (
        "Abre o atendimento de VIDROS/farois/lanternas/retrovisores/para-choque/lataria "
        "no portal da seguradora. "
        "NAO decore a lista do que coletar: CHAME a ferramenta com o que voce ja tem e "
        "ela devolve, em portugues, EXATAMENTE a proxima pergunta que falta — uma por "
        "vez, para voce fazer ao segurado e chamar de novo. "
        "O que trava o pedido hoje, e que ela vai cobrar: "
        + "; ".join(trava) + ". "
        "Ha perguntas ESPECIFICAS por familia de peca (" + familias + "), e sao elas "
        "que decidem QUAL peca do catalogo da apolice sera pedida — a ferramenta diz "
        "quais quando souber a peca. Mande-as em `especificos`. "
        "A ferramenta busca SOZINHA os dados reais da apolice (placa, veiculo, endereco, "
        "seguradora) na InfoCap — NAO peca placa/CEP/endereco ao cliente e NUNCA os "
        "invente. Se houver mais de uma apolice AUTO ativa, ela devolve as opcoes para "
        "voce perguntar qual. Ela avisa o cliente que esta abrindo e volta com o "
        "resultado. NAO finaliza sozinha o pedido."
    )


def _lista_de_pecas(bruto) -> list:
    """As peças amassadas como LISTA, venha como vier.

    O modelo às vezes devolve `["porta", "paralama"]` e às vezes
    `"porta e paralama"` — as duas são a mesma resposta do segurado. Aceitar só
    uma forma faria metade das respostas sumirem no transporte, que é o defeito
    que `TRANSPORTAVEIS` existe para não repetir.
    """
    if isinstance(bruto, (list, tuple, set)):
        itens = [str(x).strip() for x in bruto]
    else:
        texto = str(bruto or "")
        for sep in (";", " e ", ","):
            texto = texto.replace(sep, ",")
        itens = [p.strip() for p in texto.split(",")]
    return [p for p in itens if p and p.lower() not in ("none", "null")]


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
        # P0-5 — aceita o campo tanto no topo quanto em `especificos` (que é o
        # transporte declarado em `como_devolver`). `especificos` vence, porque
        # é o caminho que a pergunta ensina ao agente.
        "cidade_para_o_servico": flat.get("cidade_para_o_servico"),
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

    # A cidade do serviço vem do que o segurado respondeu; o ESTADO cai para o
    # da apólice quando ele não o disse, e a queda fica declarada (P0-5).
    cidade_servico, cidade_servico_uf, cidade_servico_origem = cidade_e_uf_do_servico(
        ja_sei.get("cidade_para_o_servico"), cli.get("estado"))

    # N-3 — o contato que vai ao portal. Tudo vem do banco: o segurado da
    # InfoCap, a corretora do Perfil de Acionamento. ⛔ Nada de constante de
    # corretora aqui (CLAUDE.md §13.9): `sol` já é o perfil daquela `company_id`.
    tel_segurado = str(cli.get("telefone") or "").strip()
    contato = {
        # 📊 "6" = Corretor na tabela `RelacaoTitular` do POST /solicitantes.
        # O número é do portal, não nosso — por isso vai como string literal.
        "relacao": "6",
        "telefone": tel_segurado or sol["telefone"],
        "tipo_telefone": "segurado" if tel_segurado else "corretora",
        "email_segurado": str(cli.get("email") or "").strip(),
        "email_corretora": sol["email"],
        "nome_solicitante": sol["nome"],
        "documento_corretor": sol["cpf_cnpj"],
    }

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
            # P1-5 — a lista de peças amassadas do MESMO evento. Só a família
            # lataria a faz nascer, e por isso ela é `[]` em todo o resto: a
            # journey lê o tamanho, não a presença da chave.
            "pecas_lataria": _lista_de_pecas(ja_sei.get("pecas_lataria")),
        },
        # As respostas do passo 6 (80%), ja coletadas na conversa. A journey ja
        # le esta chave (`vidros_lanternas.abrir_atendimento`) e a entrega ao
        # cerebro adaptativo — era o unico pedaco do caminho que nascia vazio.
        "especificos": {k: v for k, v in especificos.items()
                        if (v if isinstance(v, (list, tuple)) else str(v or "").strip())},
        "local": {
            "estado": _fold(cli.get("estado")).upper(),
            "cidade": _fold(cli.get("cidade")).title(),
            "cep": str(cli.get("cep") or "").strip(),
            # 🔴 P0-5 — A CIDADE DO SERVIÇO, que NÃO é a cidade do cadastro.
            #
            # As duas convivem na mesma chave de propósito: `local.cidade` é
            # onde ele MORA (vai no cadastro e no cálculo de domicílio) e
            # `local.cidade_servico` é onde ele QUER o serviço (vira
            # `CodigoCidade` no PATCH). Guardá-las com o mesmo nome faria a
            # journey escolher uma por engano — e a escolha errada é um
            # vidraceiro em outra cidade.
            "cidade_servico": {"uf": cidade_servico_uf, "cidade": cidade_servico},
            "cidade_servico_uf_de": cidade_servico_origem,
        },
        # 🔴 N-3 (D-E00110-01) — QUEM A LOJA LIGA PARA ACHAR.
        #
        # 📊 Medido em 20/09/2026: 3 das 4 capturas gravaram o telefone com
        # `Tipo 21 = CELULAR CORRETOR`, e o portal respondeu
        # `PossuiTelefoneRecebeWhatsapp:false` — o segurado não recebe nada da
        # seguradora e a loja liga para a corretora, que então liga para ele.
        # `Tipo 20 = CELULAR SEGURADO` tem ZERO exercícios.
        #
        # O desenho: a RELAÇÃO declarada continua sendo a verdade (quem abre é
        # a corretora → "6" = Corretor; declarar "O Próprio" seria declaração
        # falsa), e o CONTATO passa a ser o do segurado, porque é ele que a
        # loja precisa achar para combinar o dia. O e-mail da corretora
        # continua indo junto — é assim que ela recebe a cópia.
        #
        # ⚠️ Sem telefone do segurado o contato CAI para o da corretora, com o
        # tipo dizendo a verdade. Um telefone vazio no portal é um pedido que
        # ninguém consegue agendar.
        "contato": contato,
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


# ===========================================================================
# O DESFECHO VIRA MENSAGEM — SPEC-EXTRA-001.10 N-1 / P1-1
# ===========================================================================
#
# 🔴 Quem decide o que acontece depois do pedido é o PORTAL, não nós. 📊 Medido
# em 20/09/2026 sobre 3 capturas: `GET /agendamentos/opcoes-disponiveis` devolve
# 20 chaves booleanas e o bundle as roteia — e duas apólices idênticas, na mesma
# seguradora e na mesma categoria, deram desfechos OPOSTOS (uma loja já
# atribuída × uma agenda com lojas). Não é atributo de peça, é decisão do portal.
#
# Este bloco só TRADUZ o que veio. Ele nunca escolhe loja, nunca promete dia e
# nunca inventa endereço: cada linha abaixo só aparece se o dado chegou.

#: 📊 Copy do HTML da tela final do portal (20/09/2026), reescrita em português
#: de gente. Vai em TODO desfecho, porque o golpe do "depósito da franquia"
#: chega justamente a quem acabou de abrir um atendimento de verdade.
AVISO_ANTIFRAUDE = (
    "Importante: a franquia, quando existe, é paga na hora do serviço, direto "
    "na loja. Ninguém vai te pedir depósito ou transferência antes — se pedirem, "
    "não pague nada e me chama aqui."
)


def _linhas_de_franquia(desfecho: dict) -> list:
    """Cada linha `{titulo, valor}` que o portal mandou, do jeito que ele mandou.

    ⚠️ "SEM FRANQUIA" é um VALOR válido, não ausência — 📊 a captura de
    20/09/2026 trouxe as três linhas juntas: *Valor para troca 630*, *Desconto
    para reparo 630* e *Valor para reparo SEM FRANQUIA*. Tratar texto como
    "vazio" apagaria justamente a linha que é boa notícia.
    """
    saida = []
    for item in (desfecho.get("franquias") or []):
        if not isinstance(item, dict):
            continue
        titulo = str(item.get("titulo") or "").strip()
        valor = item.get("valor")
        valor_txt = str(valor).strip() if valor is not None else ""
        if not (titulo and valor_txt):
            continue
        if valor_txt.replace(".", "").replace(",", "").isdigit():
            valor_txt = f"R$ {valor_txt}"
        saida.append(f"• {titulo}: {valor_txt}")
    return saida


def _bloco_da_loja(loja: dict) -> list:
    linhas = []
    nome = str(loja.get("nome") or "").strip()
    if nome:
        linhas.append(f"Loja: {nome}")
    endereco = str(loja.get("endereco") or "").strip()
    if endereco:
        linhas.append(f"Endereço: {endereco}")
    referencia = str(loja.get("referencia") or "").strip()
    if referencia:
        linhas.append(f"Ponto de referência: {referencia}")
    telefone = str(loja.get("telefone") or "").strip()
    if telefone:
        linhas.append(f"Telefone: {telefone}")
    return linhas


def mensagem_do_desfecho(desfecho: Optional[dict]) -> str:
    """O que o segurado lê quando o portal decidiu. "" = não há desfecho legível.

    🔴 NUNCA INVENTA LOJA. Toda loja citada sai de `desfecho["loja"]` ou de
    `desfecho["lojas"]`; sem elas, a mensagem diz o que sabe e para. Uma loja
    inventada manda uma pessoa dirigir até um endereço que não existe.
    """
    if not isinstance(desfecho, dict) or not desfecho:
        return ""

    tipo = str(desfecho.get("tipo") or "desconhecido").strip().lower()
    numero = str(desfecho.get("codigo_atendimento") or "").strip()

    partes = []
    if numero:
        partes.append(
            f"Seu atendimento foi aberto na seguradora ✅\n"
            f"Número do atendimento: {numero} — guarde esse número, é com ele que "
            f"você acompanha e cobra o serviço.")
    else:
        partes.append("Seu atendimento foi aberto na seguradora ✅")

    franquias = _linhas_de_franquia(desfecho)
    if franquias:
        partes.append("Sobre a franquia:\n" + "\n".join(franquias))

    if tipo == "loja_direta":
        bloco = _bloco_da_loja(desfecho.get("loja") or {})
        if bloco:
            partes.append(
                "A seguradora já escolheu a loja que vai fazer o serviço:\n"
                + "\n".join(bloco)
                + "\n\nÉ a loja que combina o dia com você. Se preferir adiantar, "
                  "pode ligar direto para ela e agendar.")
        else:
            partes.append(
                "A seguradora já encaminhou seu pedido para uma loja credenciada. "
                "Eles entram em contato com você para combinar o dia — assim que eu "
                "tiver os dados da loja, eu te passo aqui.")

    elif tipo == "agenda":
        lojas = [l for l in (desfecho.get("lojas") or []) if isinstance(l, dict)]
        if lojas:
            linhas = ["Você escolhe onde quer fazer o serviço. Estas são as lojas "
                      "credenciadas mais perto de você:"]
            for i, loja in enumerate(lojas, start=1):
                nome = str(loja.get("nome") or "").strip() or f"Loja {i}"
                endereco = str(loja.get("endereco") or "").strip()
                cidade = " ".join(x for x in (str(loja.get("cidade") or "").strip(),
                                              str(loja.get("uf") or "").strip()) if x)
                distancia = str(loja.get("distancia") or "").strip()
                tempo = str(loja.get("tempo") or "").strip()
                detalhe = ", ".join(x for x in (endereco, cidade) if x)
                perto = " · ".join(x for x in (distancia, tempo) if x)
                linha = f"{i}) {nome}"
                if detalhe:
                    linha += f" — {detalhe}"
                if perto:
                    linha += f" ({perto})"
                dias = [str(d).strip() for d in (loja.get("dias") or []) if str(d).strip()]
                if dias:
                    linha += f"\n   Dias com agenda: {', '.join(dias[:8])}"
                elif loja.get("tem_agenda") is False:
                    linha += "\n   (sem agenda aberta no momento)"
                linhas.append(linha)
            linhas.append(
                "Me diz o NÚMERO da loja que você prefere e o DIA que fica melhor. "
                "⚠️ Quem confirma o horário com a loja é a nossa equipe — eu anoto a "
                "sua escolha e passo para eles fecharem, e te aviso quando estiver "
                "confirmado. Não considere agendado até eu te confirmar.")
            partes.append("\n".join(linhas))
        else:
            partes.append(
                "A seguradora liberou o agendamento, mas não consegui ler a lista de "
                "lojas por aqui. Já passei para a nossa equipe buscar as opções e te "
                "retornar com elas.")

    elif tipo == "analista":
        # ⚠️ O texto do portal entra INTEIRO quando ele já diz o que precisa ser
        # dito, e só é substituído quando não diz. Repetir "está com o analista"
        # duas vezes na mesma mensagem soa a robô — e soar a robô é a única
        # coisa que o segurado nota antes do conteúdo.
        titulo = str(desfecho.get("titulo_portal") or "").strip()
        prazo = ("O retorno costuma sair até o próximo dia útil — assim que chegar, "
                 "eu te aviso aqui mesmo.")
        if "analista" in _fold(titulo).lower():
            partes.append(f"{titulo} {prazo}")
        else:
            partes.append("Seu pedido está com o analista da seguradora. " + prazo)

    elif tipo == "vistoria":
        partes.append(
            "A seguradora pediu uma vistoria antes de liberar o serviço. Essa parte "
            "quem conduz é a nossa equipe: já passei o seu caso para eles, com tudo o "
            "que você me contou, e eles te explicam o passo seguinte. Você não vai "
            "precisar repetir nada.")

    else:
        partes.append(
            "O pedido está aberto, mas a seguradora respondeu de um jeito que eu não "
            "consigo interpretar sozinho — e eu prefiro te dizer isso do que te dar "
            "uma informação errada. Já passei para a nossa equipe conferir direto com "
            "eles, e te aviso assim que tiver a resposta certa.")

    link = str(desfecho.get("link_area_segurado") or "").strip()
    if link:
        partes.append(f"Você também acompanha por aqui: {link}")

    partes.append(AVISO_ANTIFRAUDE)
    return "\n\n".join(p for p in partes if str(p).strip()).strip()


# ---------------------------------------------------------------------------
# AS PARADAS — desconhecido nunca vira silêncio
# ---------------------------------------------------------------------------
#
# Cada parada tem DUAS traduções: uma pergunta curta para o segurado (com as
# opções, quando o portal as deu) e um dossiê para quem vai resolver. A regra
# que nasceu aqui: **uma parada sem texto é uma parada que o segurado não vê**,
# e o que ele não vê ele cobra por outro canal.
_PARADAS = {
    "decidir_reparo": (
        "Boa notícia: a seguradora ofereceu REPARAR o seu vidro em vez de trocar. "
        "O reparo é sem custo de franquia, leva uns 30 minutos e mantém o vidro "
        "original do carro; se não ficar bom, você ainda pode pedir a troca depois. "
        "Você quer que eu aceite o reparo?",
        "O portal ofereceu o reparo (regras-reparo → ExibirDialogDeReparo=true) e a "
        "resposta do segurado não foi coletada antes. Nada foi materializado além do "
        "que já existia: responda `aceita_reparo` e o pedido continua do mesmo ponto.",
    ),
    "peca_ambigua": (
        "Só uma dúvida antes de eu seguir: qual peça exatamente foi danificada? "
        "Com o nome certinho eu peço a peça certa na seguradora.",
        "O texto da peça casou com mais de uma identidade no catálogo. O pedido não "
        "avança porque escolher errado abre o atendimento da peça errada, e o portal "
        "não deixa corrigir — seria preciso abrir outro.",
    ),
    "cidade_sem_rede": (
        "Consegui abrir o seu pedido, mas na cidade que você me passou a seguradora "
        "não tem loja credenciada. Tem alguma cidade vizinha onde você consiga levar "
        "o carro? Me diz qual que eu sigo daqui.",
        "`GET /clientes/cidades` não devolveu rede credenciada para a cidade "
        "informada. Peça outra cidade ao segurado — não escolha por ele.",
    ),
    "motivo_ambiguo": (
        "Me conta com um pouco mais de detalhe como o dano aconteceu? "
        "(foi uma pedra na estrada, alguém quebrou, você encontrou o carro assim...) "
        "É que a seguradora tem uma lista fechada de causas e eu quero marcar a certa.",
        "O relato não casou com confiança em nenhuma opção de `motivos-dano`. "
        "As opções reais do portal estão no dossiê abaixo — escolher por semelhança "
        "seria abrir o pedido com a causa errada.",
    ),
    "questionario_incompleto": (
        "Falta só uma coisa para eu concluir: a seguradora fez uma pergunta sobre o "
        "seu vidro que eu não sei responder por você. Já te mando qual é.",
        "O questionário do portal trouxe uma pergunta sem resposta coletada e sem "
        "saída de 'não sabe'. A pergunta literal e TODAS as opções estão no dossiê.",
    ),
    "tela_desconhecida": (
        "Comecei a abrir o seu pedido e a seguradora mostrou uma tela que eu ainda não "
        "conheço. Prefiro não arriscar e te dar informação errada: já passei para a "
        "nossa equipe concluir na mão, com tudo o que você me contou. Te aviso assim "
        "que estiver aberto. 🙏",
        "Tela/resposta fora do contrato conhecido. Vai para a fila de aprendizado "
        "(`tela_cega`, ramo vidros) e para um humano concluir. NÃO reexecute sem "
        "conferir se o atendimento já existe.",
    ),
}
_PARADAS["desconhecido"] = _PARADAS["tela_desconhecida"]


def texto_da_parada(stage: Optional[str]) -> Optional[Tuple[str, str]]:
    """(o que o segurado lê, o que a equipe lê). None = parada sem texto próprio."""
    chave = str(stage or "").strip().lower()
    return _PARADAS.get(chave)


# ===========================================================================
# P-PILOTO-08 — o que vai para a FILA DE APRENDIZADO, e como
# ===========================================================================
#
# 🔴 PURO, e é o que o torna provável offline: quem decide "isto é tela
# desconhecida" não toca em banco nem em rede. A gravação é do chamador
# (`portal_tool` dentro da janela de 150s · `vigia_do_portal` fora dela), e os
# dois usam ESTA função — duas definições de "desconhecido" fariam a fila
# receber do caminho A e não receber do caminho B, sem ninguém notar.

#: Os desfechos que a journey sabe traduzir. Qualquer outro é aprendizado.
_DESFECHOS_CONHECIDOS = ("loja_direta", "agenda", "analista", "vistoria")

#: Quanto do texto do portal entra na fila. A tela é para uma pessoa LER e
#: transformar em passo; 1200 caracteres já são mais do que ela consegue ler.
_TETO_DO_RESUMO = 1200


def slug_da_seguradora(params: Optional[dict]) -> str:
    """O `insurer_key` da fila de aprendizado, a partir do nome da seguradora.

    ⛔ Nunca uma constante de corretora nem uma lista fixa de seguradoras
    (CLAUDE.md §13.9): o nome vem do `params` daquele job, que veio da apólice
    daquela `company_id`. Nome vazio vira `desconhecida`, que é uma informação —
    a fila mostra que chegou tela de alguém que não soubemos nomear.
    """
    nome = _fold((params or {}).get("insurer_name")).strip().lower()
    slug = "_".join(p for p in "".join(
        c if c.isalnum() else " " for c in nome).split())
    return slug or "desconhecida"


def resumo_da_tela_desconhecida(evidence: Optional[dict]) -> Optional[dict]:
    """`{"onde", "texto"}` quando este job tem algo a ENSINAR. `None` quando não.

    Três entradas, e as três já existem no produto:

      `tela_desconhecida`  o caminho API disse, em contrato, que não entendeu
      `desfecho.tipo`      veio um tipo fora dos quatro que sabemos traduzir
      `debug_dom`/`final`  o caminho DOM parou sem desfecho conhecido

    ⛔ O texto tem de chegar aqui **já mascarado** pela origem (SPEC-087
    BLOCO C): escrever cru e mascarar depois é criar o vazamento e tapá-lo. Por
    isso esta função nunca inventa texto — ela só ESCOLHE qual dos resumos que a
    journey produziu vai para a fila, e corta no teto.
    """
    ev = evidence if isinstance(evidence, dict) else {}
    if not ev:
        return None

    marca = ev.get("tela_desconhecida")
    if isinstance(marca, dict):
        texto = str(marca.get("resumo_mascarado") or marca.get("resumo") or "").strip()
        onde = str(marca.get("onde") or "api").strip() or "api"
        if texto:
            return {"onde": onde, "texto": texto[:_TETO_DO_RESUMO]}

    desfecho = ev.get("desfecho") if isinstance(ev.get("desfecho"), dict) else None
    if desfecho is not None:
        tipo = str(desfecho.get("tipo") or "").strip().lower()
        if tipo in _DESFECHOS_CONHECIDOS:
            # 🔴 O PAR DE CONTROLE do guarda: desfecho conhecido NÃO ensina nada.
            # Sem esta saída, todo acionamento bem-sucedido entraria na fila e a
            # fila deixaria de ser fila de trabalho.
            return None
        titulo = str(desfecho.get("titulo_portal") or "").strip()
        roteador = desfecho.get("roteador")
        corpo = titulo or (f"roteador: {roteador}" if roteador else "")
        if corpo:
            return {"onde": f"desfecho_{tipo or 'sem_tipo'}",
                    "texto": corpo[:_TETO_DO_RESUMO]}

    # O caminho DOM: parou numa tela e guardou o que viu. Só vira aprendizado
    # quando NÃO há desfecho conhecido — senão a tela de sucesso entra na fila.
    for chave in ("debug_dom", "final"):
        bruto = ev.get(chave)
        texto = str(bruto if isinstance(bruto, str) else (bruto or {}).get("texto")
                    if isinstance(bruto, dict) else "").strip()
        if texto:
            return {"onde": chave, "texto": texto[:_TETO_DO_RESUMO]}
    return None


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

    # ----------------------------------------------------------------------
    # 🔴 SPEC-EXTRA-001.10 N-1 — O DESFECHO VEM ANTES DE TUDO.
    #
    # Quando a journey leu o roteador do portal, ela já sabe MAIS do que
    # qualquer heurística daqui: o número, a franquia linha a linha, a loja
    # atribuída ou as lojas com agenda. Deixar o desfecho para depois do
    # `switch` de status faria o caso mais completo ser respondido pela frase
    # mais genérica — e o segurado receberia "cheguei numa etapa que precisa de
    # revisão" sobre um pedido que o portal já concluiu.
    # ----------------------------------------------------------------------
    desfecho = ev.get("desfecho") if isinstance(ev.get("desfecho"), dict) else None
    if desfecho:
        corpo = mensagem_do_desfecho(desfecho)
        if corpo:
            numero = str(desfecho.get("codigo_atendimento") or "").strip()
            aviso = ("NAO peca para eu abrir de novo: o pedido ja existe e repetir "
                     "criaria um segundo atendimento na seguradora, que nao se desfaz.")
            if str(desfecho.get("tipo") or "").strip().lower() in ("desconhecido", "vistoria"):
                aviso += (" Este caso VAI para a equipe humana: mande o dossie e diga ao "
                          "segurado, com estas palavras, o que esta abaixo.")
            return (
                "O atendimento FOI ABERTO na seguradora"
                + (f" (numero {numero})." if numero else ".")
                + " ENTREGUE AO SEGURADO A MENSAGEM ABAIXO, com estas palavras — ela ja "
                  "esta em portugues de gente e tem tudo o que ele precisa. Numero, "
                  "valor, telefone e link se copiam EXATOS.\n\n"
                + corpo
                + "\n\n" + aviso
            )

    # A parada tem texto próprio? Então ele vence a frase genérica de
    # `needs_human` — que é verdadeira e inútil ("uma etapa que precisa de
    # revisão" não diz ao segurado o que fazer).
    parada = texto_da_parada(ev.get("stage"))
    if parada and status in ("needs_human", "failed"):
        para_ele, para_equipe = parada
        opcoes = [str(o)[:60] for o in (ev.get("opcoes") or [])][:12]
        extra = f"\nOpcoes que o portal ofereceu: {', '.join(opcoes)}" if opcoes else ""
        pergunta = str(ev.get("pergunta") or "").strip()
        if pergunta:
            extra += f"\nO portal perguntou, literalmente: \"{pergunta[:180]}\""
        return (
            "O pedido PAROU numa etapa que precisa de uma resposta. DIGA AO SEGURADO, "
            "com estas palavras:\n\n" + para_ele
            + "\n\n[para a equipe, nao mande ao segurado] " + para_equipe + extra
        )

    # ----------------------------------------------------------------------
    # SPEC-074 — o ESTADO DE NEGÓCIO vem antes do estado técnico.
    #
    # 🔴 O caminho API-first cria o pedido em DUAS fronteiras, e a segunda
    # produz o `CodigoAtendimento` — que é o número que a tela mostra e que o
    # extrator de texto grava em `evidence.protocolo`. Quando a journey roda
    # pela API, o número chega em `evidence.vidros_estado`, não pelo texto.
    #
    # Sem esta ponte, um job que criou o pedido pela API e falhou depois cairia
    # no ramo `failed` e diria "não consegui abrir" — exatamente o defeito que a
    # SPEC-074 P1 descreve, e o pior que se pode dizer a alguém cujo pedido
    # existe.
    #
    # A regra "o número vem primeiro" é preservada: este bloco só ACRESCENTA
    # uma segunda fonte para o mesmo número, nunca desloca a checagem original.
    # ----------------------------------------------------------------------
    est = ev.get("vidros_estado") if isinstance(ev.get("vidros_estado"), dict) else {}
    if not protocolo and est.get("tem_codigo_atendimento"):
        protocolo = str(est.get("codigo_atendimento") or "").strip()
    if not protocolo and est.get("existe_algo_na_seguradora"):
        # Existe pedido e não temos o número: dizer "não abriu" seria mentira, e
        # inventar um número seria pior. A frase fala a verdade incômoda.
        return ("O pedido FOI aberto no portal, mas não consegui ler o número do "
                "atendimento. NÃO reexecute — reabrir criaria um segundo pedido. "
                "Avise o segurado que a solicitação existe e que o número virá "
                "em seguida, e encaminhe para conferência humana.")

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
    """'aaa-0a91' e 'AAA0A91' sao o mesmo carro. So alfanumerico, maiusculo."""
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
