# -*- coding: utf-8 -*-
"""O conhecimento global sai SEMPRE anônimo — P-E0018-14 · D-MC-39 (04/10/2026).

`conduct_playbooks` é GLOBAL (⛔ nunca `company_id` nela — D-MC-39) e nasce das
conversas de UMA corretora. O funil único de escrita é
`attendance_distiller._save_playbook_draft_sync`; o porteiro é
`curadoria_cartas.anonimizar_para_o_global`, que COMPÕE o `templatize` (com as
marcas de corretora lidas de `companies`) e a segunda rede de
`intelligence.redaction_service`.

O que se afirma é o comportamento do MOTOR (CLAUDE.md §9.4): o caminho REAL de
escrita, com dublê só na borda (banco e modelo), e os doubles são os MESMOS de
`test_spec040_onda3_distiller.py`. O nome de corretora é FICTÍCIO e vem do
dublê de `companies` (§13.9).

  [1] sujo, pelo FIO INTEIRO (modelo → distill_once → insert): nada vaza
  [2] sujo, direto no escritor: nada vaza, e o que foi trocado é contado
  [3] CONTROLE: playbook limpo, só sobre o serviço → gravado IGUAL
  [4] o que o mascarador NÃO pega (corretora com acento) → NÃO grava
  [5] sem a lista de corretoras (banco mudo) → NÃO grava (falha fechada)
  [6] o log da recusa não carrega o dado
  [7] o guarda CONSEGUE falhar: porteiro trocado por identidade → a sonda vê
      o vazamento (§9.3: prove que as duas coisas conseguem ser diferentes)
  [8] a releitura de 5 min com o banco mudo não esvazia a lista do mascarador
      de MENSAGEM — e o porteiro, nesse caso, fica SEM lista (nunca a velha)
  [9]-[16] o conserto único do 0.5, com o `INSURER_REGISTRY` REAL: Q2 (corretora
      por variante: domínio, handle, núcleo), Q4 (nome de ofício nunca é marca),
      Q3 (nome de pessoa em contexto), as formas que os dois motores deixavam
      passar, o conhecimento público intacto, a lista velha, o log por hash e o
      laço de custo (grupo recusado só volta com material novo)

Standalone, como os irmãos: `python tests/test_o_conhecimento_global_sai_anonimo.py`.
"""

import asyncio
import copy
import json
import logging
import os
import sys
from pathlib import Path

os.environ["DESTILADOR_TETO_POR_RODADA"] = "500"
sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_spec040_onda3_distiller as O3  # noqa: E402  — os MESMOS doubles

PASS = FAIL = 0
FAILURES = []


def check(name, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  [ok] {name}")
    else:
        FAIL += 1
        FAILURES.append((name, detail))
        print(f"  [X] {name}{': ' + str(detail) if detail else ''}")


# 💭 Tudo FICTÍCIO: corretora, pessoa, telefone, CPF, placa e e-mail.
CORRETORA = {"id": "c-ficticia", "company_name": "Vagalume Seguros",
             "legal_name": "Vagalume Corretora de Seguros Ltda"}
CORRETORA_2 = {"id": "c-ficticia-2", "company_name": "Pirilampo Corretora",
               "legal_name": "Pirilampo Assessoria em Seguros Ltda"}

PLAYBOOK_SUJO = {
    "objetivo": "acionar guincho sem friccao",
    "acolhimento": "Olá, meu nome é Joana Pereira e vou cuidar do seu caso.",
    "assinatura": "Joana Pereira - Vagalume Seguros",
    "ficha_coleta": [
        {"campo": "cpf", "como_pedir": "Confirme o CPF 123.456.789-09 do titular",
         "quando": "antes de acionar", "ja_temos_na_apolice": True},
        {"campo": "placa", "como_pedir": "A placa ABC1D23 é a do carro parado?",
         "quando": "antes de acionar", "ja_temos_na_apolice": True},
    ],
    "pre_checks": ["Pirilampo Corretora já confirma a cobertura antes"],
    "encerramento": "Qualquer coisa ligue (48) 99876-5432 ou escreva para "
                    "joana.pereira@vagalume.com.br",
    "frases_exemplo": ["Ja estou acionando, fica tranquilo!"],
}

#: o que NÃO pode chegar à tabela global, em minúsculas e sem acento
PROIBIDOS = ("vagalume", "pirilampo", "joana", "pereira", "123.456.789-09",
             "12345678909", "abc1d23", "99876", "5432", "@vagalume")


def _sem_acento_baixo(t):
    import unicodedata
    n = unicodedata.normalize("NFKD", t)
    return "".join(c for c in n if not unicodedata.combining(c)).lower()


def _vazou(linhas):
    """Os proibidos que aparecem em QUALQUER coluna das linhas gravadas."""
    alvo = _sem_acento_baixo(json.dumps(linhas, ensure_ascii=False))
    return [p for p in PROIBIDOS if p in alvo]


class _Captura(logging.Handler):
    def __init__(self):
        super().__init__()
        self.msgs = []

    def emit(self, record):
        self.msgs.append(record.getMessage())


def _novo_mundo(store, companies):
    """Banco limpo, cache das marcas vencida — cada caso lê `companies` de novo."""
    store.clear()
    if companies is not None:
        store["companies"] = [dict(c) for c in companies]
    sys.modules["app.services.atlas.templater"]._CACHE_MARCAS = None
    sys.modules["app.services.curadoria_cartas"]._marcas_lidas_em = None



# ══════════════════════════════════════════════════════════════════════════
# O CONSERTO ÚNICO DO 0.5 — os ataques do red team (Q2, Q3, Q4 e as
# pendências), todos pelo caminho REAL de escrita, com o `INSURER_REGISTRY`
# REAL carregado (📊 o red team mostrou que sem ele o teste não via Q2/Q4:
# a lista de seguradoras vinha vazia). Tudo FICTÍCIO (§13.9).
# ══════════════════════════════════════════════════════════════════════════
VAGALUME = CORRETORA
PB_CONTROLE = {
    "objetivo": "acionar guincho sem friccao",
    "encerramento": "em perda total o guincho leva ao patio da seguradora",
    "pre_checks": ["confirmar a cobertura de guincho e o km",
                   "Pode me mandar a foto da CNH de quem estava dirigindo? "
                   "Pode ser foto legível da frente e verso."],
}


def _carregar_registro_real():
    """O `INSURER_REGISTRY` de verdade, no lugar onde o porteiro o importa."""
    import importlib.util
    raiz = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "app.services.insurer_registry", raiz / "app/services/insurer_registry.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    sys.modules["app.services.insurer_registry"] = mod
    return mod


def _grava(dist, store, companies, content, ramo="auto", servico="guincho"):
    """(linha gravada ou None) — o mundo zerado e a lista relida a cada caso."""
    _novo_mundo(store, companies)
    dist._save_playbook_draft_sync(ramo, servico, copy.deepcopy(content), 13, "m")
    linhas = store.get("conduct_playbooks", [])
    return linhas[0] if linhas else None


def _nao_vazou(linha, proibido):
    return linha is None or _sem_acento_baixo(proibido) not in _sem_acento_baixo(
        json.dumps(linha, ensure_ascii=False))


def run_ataques(dist, store, cur, cap):
    registro = _carregar_registro_real()
    seg = cur._seguradoras()
    check("o registro REAL de seguradoras chegou ao porteiro (porto, azul, tokio)",
          {"porto", "azul", "tokio"} <= set(seg[1]) and len(registro.INSURER_REGISTRY) >= 10,
          sorted(seg[1])[:20])

    # [9] Q2 — corretora por variante: domínio, handle, nome que começa com
    # seguradora, parte distintiva.
    print("\n[9] Q2: a corretora por variante do nome -> nunca chega ao global")
    q2 = [
        ([VAGALUME], "site vagalumeseguros.com.br", "vagalumeseguros"),
        ([VAGALUME], "insta @vagalumeseguros", "vagalumeseguros"),
        ([VAGALUME], "www.VagalumeCorretora.com", "vagalumecorretora"),
        ([VAGALUME], "vagalume_seguros no insta", "vagalume_seguros"),
        ([VAGALUME], "o time #VagalumeSeguros confirma", "vagalume"),
        ([VAGALUME], "a Vaga-lume confirma", "vaga-lume"),
        ([VAGALUME, {"id": "c2", "company_name": "Porto Real Corretora",
                     "legal_name": "Porto Real Corretora de Seguros Ltda"}],
         "a Porto Real Corretora confirma o guincho", "porto real corretora"),
        ([VAGALUME, {"id": "c2", "company_name": "Azul Marinho Seguros",
                     "legal_name": "Azul Marinho Corretora Ltda"}],
         "a Azul Marinho confirma", "azul marinho"),
        ([VAGALUME, {"id": "c2", "company_name": "Céu Azul Corretora",
                     "legal_name": "Ceu Azul Corretora de Seguros Ltda"}],
         "a Céu Azul confirma", "ceu azul"),
        ([VAGALUME, {"id": "c2", "company_name": "Céu Azul Corretora",
                     "legal_name": "Ceu Azul Corretora de Seguros Ltda"}],
         "a CEU AZUL confirma", "ceu azul"),
        ([VAGALUME, {"id": "c2", "company_name": "JR Seguros",
                     "legal_name": "JR Corretora de Seguros Ltda"}],
         "acesse jrseguros.com.br", "jrseguros"),
    ]
    for companies, frase, proibido in q2:
        linha = _grava(dist, store, companies, {"objetivo": "acionar guincho",
                                                "encerramento": frase})
        check(f"Q2 {frase!r}", _nao_vazou(linha, proibido),
              linha and linha["content"].get("encerramento"))
    # a mesma corretora no ramo/serviço (chave do grupo)
    linha = _grava(dist, store, [VAGALUME], dict(O3.PLAYBOOK), servico="guincho vagalumeseguros")
    check("Q2 a forma compacta na CHAVE do grupo tambem barra", linha is None)

    # [10] Q4 — palavra genérica nunca vira marca: o MESMO playbook, com um
    # tenant de nome de ofício, grava IGUAL ao controle (byte a byte).
    print("\n[10] Q4: tenant com nome de oficio nao apaga nem corrompe o global")
    controle = _grava(dist, store, [VAGALUME], PB_CONTROLE)
    check("CONTROLE: so a Vagalume -> gravado igual", controle is not None
          and controle["content"] == PB_CONTROLE, controle and controle["content"])
    for nome, ramo, servico in [("Auto Center Corretora", "auto", "guincho"),
                                ("Vida Plena Corretora", "vida", "funeral"),
                                ("Total Corretora de Seguros", "auto", "guincho"),
                                ("Guincho Express Corretora", "auto", "guincho"),
                                ("Casa Forte Seguros", "residencial", "chaveiro")]:
        linha = _grava(dist, store, [VAGALUME, {"id": "c9", "company_name": nome,
                                                "legal_name": nome + " Ltda"}],
                       PB_CONTROLE, ramo=ramo, servico=servico)
        check(f"Q4 tenant {nome!r} -> {ramo}/{servico} gravado IGUAL",
              linha is not None and linha["content"] == PB_CONTROLE,
              linha and linha["content"])
    # e a frase INTEIRA continua sendo marca
    linha = _grava(dist, store, [VAGALUME, {"id": "c9", "company_name": "Total Corretora de Seguros",
                                            "legal_name": "Total Corretora de Seguros Ltda"}],
                   {"objetivo": "x", "e": "a Total Corretora de Seguros confirma"})
    check("Q4 mas a frase inteira 'Total Corretora de Seguros' nao chega",
          _nao_vazou(linha, "total corretora"), linha and linha["content"])

    # [11] Q3 — nome de pessoa em contexto.
    print("\n[11] Q3: nome de pessoa em contexto -> nao grava")
    q3 = [
        ("Oi, aqui é a Joana da Vagalume", "joana"),
        ("fale com a Maria da central", "maria"),
        ("pode falar com João que ele resolve", "joao"),
        ("confirme com a Fernanda antes", "fernanda"),
        ("a joana pereira confirma", "joana"),
        ("Att, Joana", "joana"),
        ("Atenciosamente, Bruno", "bruno"),
        ("O Carlos confirmou o horario", "carlos"),
        ("fale com o corretor Marcos Antonio", "marcos"),
        ("Peça para o João Silva enviar a foto.", "joao"),
        ("Assinado: Ricardo Gomes", "ricardo"),
        ("a Rosa do financeiro confirma", "rosa"),
        ("falar com socorro no financeiro", "socorro"),
    ]
    for frase, proibido in q3:
        linha = _grava(dist, store, [VAGALUME], {"objetivo": "acionar guincho",
                                                 "encerramento": frase})
        check(f"Q3 {frase!r}", _nao_vazou(linha, proibido),
              linha and linha["content"].get("encerramento"))
    for rot, conteudo, proibido in [
        ("nome em CHAVE de JSON", {"objetivo": "x", "responsaveis": {"Joana Pereira": "guincho"}}, "joana"),
        ("frase em CHAVE de JSON", {"objetivo": "x", "fale com a Maria": "guincho"}, "maria"),
    ]:
        linha = _grava(dist, store, [VAGALUME], conteudo)
        check(f"Q3 {rot}", _nao_vazou(linha, proibido), linha and linha["content"])
    for servico in ("guincho da Joana Pereira", "falar com João"):
        linha = _grava(dist, store, [VAGALUME], dict(O3.PLAYBOOK), servico=servico)
        check(f"Q3 nome no SERVICO {servico!r} -> nao grava", linha is None)

    # [12] as formas de identificador que os dois motores deixavam passar.
    print("\n[12] placa, telefone e CPF que passavam pelos dois motores")
    for frase, proibido in [
        ("placa abc-1234 parada", "abc-1234"),
        ("placa abc 1234 parada", "abc 1234"),
        ("placa abc 1d23 parada", "abc 1d23"),
        ("ligue 9 9876-5432", "9876-5432"),
        ("ligue 99876-5432", "99876-5432"),
        ("ramal direto 3222-1144", "3222-1144"),
        ("CPF 123/456/789-09", "123/456"),
    ]:
        linha = _grava(dist, store, [VAGALUME], {"objetivo": "x", "encerramento": frase})
        check(f"forma {frase!r}", _nao_vazou(linha, proibido),
              linha and linha["content"].get("encerramento"))

    # [13] conhecimento PÚBLICO e conteúdo legítimo: gravam, e INTACTOS.
    print("\n[13] conhecimento publico e conteudo legitimo gravam intactos")
    intactos = [
        "ligue 08007272766 para a assistencia",
        "ligue 0800 727 2766, nas capitais 4004-7676 ou 3003 9303",
        "Azul Seguros WhatsApp: (21) 3906-2985",
        "vigencia 2025-2026, renovacao em 30 dias",
        "acione a Porto Seguro pelo app; a Allianz exige foto do painel",
        "Tokio Marine abre sinistro online; a Yelum pede o laudo",
        "com ceu azul ou chuva o guincho vai",
        "o carro azul marinho esta no patio",
        "guincho no bairro Santa Maria, oficina em Sao Jose, voo para João Pessoa",
        "pedido de socorro na rodovia; a rosa dos ventos",
        "das 08:00 as 18:00; seg a sex 8h-18h",
        "Pode me mandar a foto da CNH de quem estava dirigindo? Pode ser foto legível da frente e verso.",
        "Sr(a). {NOME}, seu guincho foi acionado",
        "leve a um auto center credenciado da seguradora",
        "a corretora sempre confirma; a assessoria tecnica tambem",
        "Encaminhe para o Atendimento Humano se pedir Cancelamento",
        "o marcos do contrato sao a vistoria e a emissao",
        "conforme a norma da SUSEP",
    ]
    companies = [VAGALUME, CORRETORA_2,
                 {"id": "c3", "company_name": "Céu Azul Corretora",
                  "legal_name": "Ceu Azul Corretora de Seguros Ltda"},
                 {"id": "c4", "company_name": "Auto Center Corretora",
                  "legal_name": "Auto Center Corretora Ltda"}]
    for frase in intactos:
        conteudo = {"objetivo": "acionar guincho", "encerramento": frase}
        linha = _grava(dist, store, companies, conteudo)
        check(f"intacto {frase[:60]!r}", linha is not None and linha["content"] == conteudo,
              (linha and linha["content"].get("encerramento"))
              or cur.anonimizar_para_o_global(conteudo)[2])
    # 📊 04/10, nos 18 playbooks reais: a forma compacta SOLTA de uma corretora
    # casava dentro de palavra comum (a marca + "do"). Substring não é marca.
    previa = {"id": "c5", "company_name": "Prévia Corretora", "legal_name": "Previa Corretora Ltda"}
    conteudo = {"objetivo": "x", "e": "o resultado sai previamente.pdf, depois previamente"}
    linha = _grava(dist, store, [VAGALUME, previa], conteudo)
    check("marca que e PREFIXO de palavra comum nao barra a palavra (nem colada)",
          linha is not None and linha["content"] == conteudo,
          cur.anonimizar_para_o_global(conteudo)[2])
    linha = _grava(dist, store, [VAGALUME, previa], {"objetivo": "x", "e": "siga @previacorretora"})
    check("CONTROLE: o handle da mesma marca barra", linha is None)
    linha = _grava(dist, store, [VAGALUME], {"objetivo": "x",
                                             "e": "Central 24h: (48) 3222-1144"})
    check("telefone que NAO e de seguradora sai mascarado, sem parentese orfao",
          linha is not None and linha["content"]["e"] == "Central 24h: {TELEFONE}",
          linha and linha["content"])

    # [14] lista velha: banco mudo na releitura -> o porteiro NÃO grava.
    print("\n[14] banco mudo na releitura -> nao grava (nunca a lista velha)")
    _novo_mundo(store, [VAGALUME])
    cur.marcas_de_corretora_frescas()
    store["companies"].append({"id": "c7", "company_name": "Pirilampo Corretora",
                               "legal_name": "Pirilampo Ltda"})
    banco = sys.modules["app.core.database"]
    real_cli = banco.get_supabase_client

    class _CliMudo:
        def __init__(self):
            self.client = self
            self._r = real_cli().client

        def table(self, nome):
            if nome == "companies":
                raise ConnectionError("fora")
            return self._r.table(nome)

    banco.get_supabase_client = _CliMudo
    cur._marcas_lidas_em = None
    cap.msgs.clear()
    try:
        pid = dist._save_playbook_draft_sync("auto", "guincho",
                                             {"objetivo": "x", "e": "a Pirilampo confirma"}, 13, "m")
    finally:
        banco.get_supabase_client = real_cli
    check("corretora nova + releitura falhou -> nenhum insert", pid is None
          and not store.get("conduct_playbooks"), store.get("conduct_playbooks"))
    check("e o motivo e a lista indisponivel",
          any("lista_de_corretoras_indisponivel" in m for m in cap.msgs), cap.msgs[-1:])

    # [15] o log da recusa: o grupo IDENTIFICÁVEL (hash curto) e só o tipo.
    print("\n[15] o log da recusa diz o grupo por hash, sem o dado")
    cap.msgs.clear()
    _grava(dist, store, [VAGALUME], dict(O3.PLAYBOOK), servico="guincho da vagalume")
    gid = dist.id_do_grupo("auto", "guincho da vagalume")
    todos = " ".join(cap.msgs)
    check("o log traz o id do grupo (hash curto) e o tipo",
          gid in todos and "chave:corretora" in todos, cap.msgs)
    check("e nao traz o grupo em claro", "vagalume" not in todos.lower(), cap.msgs)

    # [16] o laço de custo: grupo recusado não volta à fila sem material novo.
    print("\n[16] grupo recusado so volta com material NOVO (marcador transitorio)")

    class _RedisSync:
        def __init__(self):
            self.kv = {}

        def set(self, k, v, ex=None):
            self.kv[k] = v

        def get(self, k):
            return self.kv.get(k)

        def delete(self, *ks):
            for k in ks:
                self.kv.pop(k, None)

        def scan_iter(self, match=None, count=None):
            prefixo = (match or "").rstrip("*")
            return [k for k in list(self.kv) if k.startswith(prefixo)]

    red = sys.modules["app.core.redis"]
    for com_redis in (True, False):
        rotulo = "Redis" if com_redis else "SEM Redis (memoria)"
        dist._RECUSAS_EM_MEMORIA.clear()
        fake = _RedisSync()
        if com_redis:
            red.get_redis_client = lambda: fake
        elif hasattr(red, "get_redis_client"):
            del red.get_redis_client
        _novo_mundo(store, [VAGALUME])
        O3._seed_sessions(store)
        for s in store["attendance_sessions"]:
            s["summary"] = {"distilled": {"ramo": "auto", "servico": "guincho",
                                          "at": s["started_at"]}}
        check(f"[{rotulo}] antes: o grupo esta na fila",
              ("auto", "guincho") in dist._grupos_sem_playbook_sync(5))
        sujo = {"objetivo": "x", "e": "a Vagalúme confirma"}
        dist._save_playbook_draft_sync("auto", "guincho", sujo, 13, "m")
        check(f"[{rotulo}] recusado: o grupo SAI da fila (nao chama o modelo de novo)",
              ("auto", "guincho") not in dist._grupos_sem_playbook_sync(5))
        if com_redis:
            check("[Redis] o marcador mora no Redis, com o material e sem o dado",
                  any(dist.id_do_grupo("auto", "guincho") in k for k in fake.kv)
                  and all("vagal" not in str(v).lower() for v in fake.kv.values()),
                  fake.kv)
        n = len(store["attendance_sessions"])
        for i in range(5):
            s = copy.deepcopy(store["attendance_sessions"][0])
            s["id"] = f"novo{i}"
            store["attendance_sessions"].append(s)
        check(f"[{rotulo}] com 5 conversas novas o grupo VOLTA",
              ("auto", "guincho") in dist._grupos_sem_playbook_sync(5),
              len(store["attendance_sessions"]) - n)
    dist._RECUSAS_EM_MEMORIA.clear()

    # [17] a cópia em MEMÓRIA do marcador vence no mesmo prazo do Redis (14 dias).
    # Sem isso, num processo longo sem Redis, o grupo recusado e sem conversa
    # nova ficava fora da fila para sempre (confirmação de 04/10). Relógio FALSO.
    print("\n[17] sem Redis: o marcador em memoria vence em 14 dias (relogio falso)")
    if hasattr(red, "get_redis_client"):
        del red.get_redis_client
    relogio_real = dist._relogio
    agora = [1_000_000.0]
    dist._relogio = lambda: agora[0]
    try:
        for passou, deve_voltar, rotulo in [
                (dist._RECUSA_TTL_S - 1, False, "CONTROLE: 14 dias menos 1 s -> continua fora"),
                (dist._RECUSA_TTL_S + 1, True, "14 dias e 1 s -> o grupo VOLTA sem material novo")]:
            dist._RECUSAS_EM_MEMORIA.clear()
            agora[0] = 1_000_000.0
            _novo_mundo(store, [VAGALUME])
            O3._seed_sessions(store)
            for s in store["attendance_sessions"]:
                s["summary"] = {"distilled": {"ramo": "auto", "servico": "guincho",
                                              "at": s["started_at"]}}
            dist._save_playbook_draft_sync("auto", "guincho",
                                           {"objetivo": "x", "e": "a Vagalúme confirma"}, 13, "m")
            fora = ("auto", "guincho") not in dist._grupos_sem_playbook_sync(5)
            agora[0] += passou
            volta = ("auto", "guincho") in dist._grupos_sem_playbook_sync(5)
            check(f"[17] {rotulo}", fora and volta == deve_voltar, (fora, volta))
    finally:
        dist._relogio = relogio_real
        dist._RECUSAS_EM_MEMORIA.clear()

    # [18] o NÚCLEO todo genérico de ≥ 2 palavras, escrito SEM o sufixo
    # (confirmação de 04/10): com maiúscula é a marca; colado é domínio/handle.
    print("\n[18] nucleo generico de 2+ palavras: com maiuscula ou colado -> nunca chega")
    for nome, frase, proibido in [
        ("Porto Real Corretora", "aqui é da Porto Real, posso ajudar", "porto real"),
        ("Porto Real Corretora", "site portoreal.com.br", "portoreal"),
        ("Porto Real Corretora", "siga @portorealseguros", "portoreal"),
        ("Auto Center Corretora", "a Auto Center confirma o guincho", "auto center"),
        ("Vida Plena Corretora", "equipe Vida Plena informa", "vida plena"),
        ("Alfa Real Seguros", "a Alfa Real confirma", "alfa real"),
        ("Auto Center Corretora", "a AUTO CENTER confirma", "auto center"),
    ]:
        linha = _grava(dist, store, [VAGALUME, {"id": "c9", "company_name": nome,
                                                "legal_name": nome + " Ltda"}],
                       {"objetivo": "acionar guincho", "encerramento": frase})
        check(f"[18] {nome!r}: {frase!r}", _nao_vazou(linha, proibido),
              linha and linha["content"].get("encerramento"))
    # CONTROLE: a mesma régua NÃO come a prosa do serviço em minúscula, nem o
    # nome de seguradora, com os mesmos tenants de nome de ofício.
    tenants = [VAGALUME] + [{"id": f"c{i}", "company_name": n, "legal_name": n + " Ltda"}
                            for i, n in enumerate(("Auto Center Corretora", "Vida Plena Corretora",
                                                   "Total Corretora de Seguros",
                                                   "Porto Real Corretora",
                                                   "Tokio Marine Corretora"), start=10)]
    for frase in ["em perda total o guincho leva ao patio da seguradora",
                  "leve a um auto center de serviços credenciado",
                  "o seguro de vida plena cobre o funeral",
                  "o porto real de embarque fica longe",
                  "a Tokio Marine abre sinistro online; site tokiomarine.com.br",
                  "acione a Porto Seguro pelo app"]:
        conteudo = {"objetivo": "acionar guincho", "encerramento": frase}
        linha = _grava(dist, store, tenants, conteudo)
        check(f"[18] CONTROLE intacto {frase[:50]!r}",
              linha is not None and linha["content"] == conteudo,
              (linha and linha["content"].get("encerramento"))
              or cur.anonimizar_para_o_global(conteudo)[2])
    # Q4 segue: UMA palavra genérica sozinha nunca é marca
    linha = _grava(dist, store, [VAGALUME, {"id": "c9", "company_name": "Total Corretora",
                                            "legal_name": "Total Corretora Ltda"}],
                   {"objetivo": "x", "e": "a Total cobre perda Total"})
    check("[18] Q4: 'Total' sozinha, mesmo com maiuscula, nao e marca",
          linha is not None and linha["content"]["e"] == "a Total cobre perda Total",
          linha and linha["content"])


def run():
    print("== P-E0018-14 · o conhecimento global sai sempre anonimo ==\n")
    dist, store, _redis, _qdrant, _factory = O3._bootstrap()
    _carregar_registro_real()       # como em produção: o porteiro sabe quem é seguradora
    cur = sys.modules["app.services.curadoria_cartas"]
    cap = _Captura()
    logging.getLogger("app.services.attendance_distiller").addHandler(cap)

    original_do_modelo = O3.PLAYBOOK

    # [1] O FIO INTEIRO: o modelo (dublê) devolve um playbook sujo, a rodada do
    # destilador sintetiza e grava pelo funil real.
    print("[1] o fio inteiro: modelo -> distill_once -> conduct_playbooks")
    _novo_mundo(store, [CORRETORA, CORRETORA_2])
    O3._seed_sessions(store)
    O3.PLAYBOOK = copy.deepcopy(PLAYBOOK_SUJO)
    try:
        asyncio.run(dist.distill_once(force=True))
    finally:
        O3.PLAYBOOK = original_do_modelo
    pbs = store.get("conduct_playbooks", [])
    check("o fio chegou ao escritor (o modelo foi chamado para o playbook)",
          any("treinador" in c["system"] for c in _factory.calls))
    check("nada do que identifica corretora/pessoa chegou a conduct_playbooks",
          not _vazou(pbs), _vazou(pbs))
    check("e o playbook FOI gravado, anonimizado (a limpeza bastou)",
          len(pbs) == 1 and "{CORRETORA}" in json.dumps(pbs[0]["content"])
          and "{CPF}" in json.dumps(pbs[0]["content"]),
          pbs[0]["content"] if pbs else "nenhum insert")

    # [2] direto no escritor — o mesmo funil que o lapidador usa.
    print("\n[2] direto no escritor (o funil do lapidador)")
    _novo_mundo(store, [CORRETORA, CORRETORA_2])
    pid = dist._save_playbook_draft_sync("auto", "guincho",
                                         copy.deepcopy(PLAYBOOK_SUJO), 13, "m")
    pbs = store.get("conduct_playbooks", [])
    check("gravou, e sem nenhum dos proibidos", pid and not _vazou(pbs), _vazou(pbs))
    anon = (pbs[0].get("source_stats") or {}).get("anonimizado") if pbs else {}
    check("a contagem do que foi trocado vai para source_stats (sem o trecho)",
          isinstance(anon, dict) and anon.get("{CPF}", 0) >= 1
          and anon.get("{CORRETORA}", 0) >= 1 and anon.get("{TELEFONE}", 0) >= 1,
          anon)
    check("as chaves do JSON sobrevivem (ficha_coleta continua lida pelos leitores)",
          pbs and isinstance(pbs[0]["content"].get("ficha_coleta"), list)
          and pbs[0]["content"]["ficha_coleta"][0]["campo"] == "cpf")

    # [3] CONTROLE: o porteiro não come conteúdo legítimo.
    print("\n[3] CONTROLE: playbook limpo, so sobre o servico")
    _novo_mundo(store, [CORRETORA, CORRETORA_2])
    limpo = copy.deepcopy(O3.PLAYBOOK)
    pid = dist._save_playbook_draft_sync("auto", "guincho", limpo, 13, "m")
    pbs = store.get("conduct_playbooks", [])
    check("gravado", bool(pid) and len(pbs) == 1)
    check("gravado IGUAL, byte a byte", pbs and pbs[0]["content"] == O3.PLAYBOOK,
          pbs[0]["content"] if pbs else None)
    check("e nada foi contado como mascarado",
          pbs and (pbs[0].get("source_stats") or {}).get("anonimizado") == {},
          (pbs[0].get("source_stats") or {}).get("anonimizado") if pbs else None)

    # [4] o que o mascarador não pega: a corretora com acento. A grafia exata é
    # trocada pelo `templatize`; a variante passa por ele — e o porteiro barra.
    print("\n[4] o que sobra depois da limpeza -> NAO grava")
    _novo_mundo(store, [CORRETORA, CORRETORA_2])
    cap.msgs.clear()
    com_acento = copy.deepcopy(O3.PLAYBOOK)
    com_acento["encerramento"] = "a Vagalúme sempre confirma o horario do guincho"
    pid = dist._save_playbook_draft_sync("auto", "guincho", com_acento, 13, "m")
    check("a variante passa pelo mascarador (a limpeza sozinha NAO bastaria)",
          "Vagalúme" in cur.veredito_de_pii(com_acento["encerramento"])[0])
    check("e o insert NAO acontece", pid is None
          and not store.get("conduct_playbooks"), store.get("conduct_playbooks"))
    check("o log diz o TIPO do que sobrou",
          any("corretora" in m and "NAO gravado" in m for m in cap.msgs), cap.msgs)

    # [5] banco mudo: sem a lista de corretoras não há como conferir.
    print("\n[5] sem a lista de corretoras -> NAO grava")
    _novo_mundo(store, None)
    pid = dist._save_playbook_draft_sync("auto", "guincho",
                                         copy.deepcopy(O3.PLAYBOOK), 13, "m")
    check("falha fechada: nenhum insert", pid is None
          and not store.get("conduct_playbooks"))
    check("e o motivo e dito",
          any("lista_de_corretoras_indisponivel" in m for m in cap.msgs), cap.msgs[-1:])

    # [6] a chave do grupo também é conferida, e o log a esconde.
    print("\n[6] a chave do grupo vaza -> NAO grava, e o log nao a repete")
    _novo_mundo(store, [CORRETORA, CORRETORA_2])
    cap.msgs.clear()
    pid = dist._save_playbook_draft_sync("auto", "guincho da vagalume",
                                         copy.deepcopy(O3.PLAYBOOK), 13, "m")
    check("nenhum insert", pid is None and not store.get("conduct_playbooks"))
    todos = " ".join(cap.msgs).lower()
    check("o log nao carrega nenhum dado (nem o grupo com a marca)",
          cap.msgs and "<grupo oculto>" in todos and not any(
              p in _sem_acento_baixo(todos) for p in PROIBIDOS), cap.msgs)

    # [7] A SONDA CONSEGUE FICAR VERMELHA: com o porteiro trocado por identidade,
    # o mesmo playbook sujo chega inteiro ao insert. Sem isto, [1]-[2] verdes
    # poderiam ser só uma sonda que não enxerga nada.
    print("\n[7] o guarda consegue falhar (porteiro trocado por identidade)")
    _novo_mundo(store, [CORRETORA, CORRETORA_2])
    real = cur.anonimizar_para_o_global
    cur.anonimizar_para_o_global = lambda c, **_k: (c, {}, [])
    try:
        dist._save_playbook_draft_sync("auto", "guincho",
                                       copy.deepcopy(PLAYBOOK_SUJO), 13, "m")
    finally:
        cur.anonimizar_para_o_global = real
    vazou = _vazou(store.get("conduct_playbooks", []))
    esperados = {"vagalume", "pirilampo", "joana", "pereira", "123.456.789-09",
                 "abc1d23", "99876", "@vagalume"}
    check("sem o porteiro, a sonda VE corretora, pessoa, CPF, placa, telefone e e-mail",
          esperados <= set(vazou), sorted(esperados - set(vazou)))

    # [8] a releitura forçada pelo porteiro, com o banco mudo, NÃO apaga a lista
    # que o mascarador de toda mensagem já tinha (efeito colateral do TTL curto).
    print("\n[8] banco mudo na releitura: o mascarador nao perde as marcas")
    _novo_mundo(store, [CORRETORA, CORRETORA_2])
    tpl = sys.modules["app.services.atlas.templater"]
    antes = cur.marcas_de_corretora_frescas()
    banco = sys.modules["app.core.database"]
    real_cli = banco.get_supabase_client

    def _mudo():
        raise ConnectionError("banco fora")

    banco.get_supabase_client = _mudo
    cur._marcas_lidas_em = None          # a cache do porteiro venceu
    try:
        depois = cur.marcas_de_corretora_frescas()
        mascarado = tpl.templatize("a Vagalume Seguros confirma o guincho")
    finally:
        banco.get_supabase_client = real_cli
    check("a lista lida antes tinha as marcas", "Vagalume" in antes, antes)
    # 🔴 O FATO MUDOU (§9.3, red team 04/10): o PORTEIRO não aceita mais a lista
    # velha — uma corretora criada depois da última leitura atravessaria. Para
    # ele, banco mudo na releitura = lista indisponível = não grava. A lição que
    # este caso guardava migra inteira para a linha de baixo: o mascarador de
    # MENSAGEM continua com a lista que tinha.
    check("depois da releitura com banco mudo, o PORTEIRO fica sem lista (nunca a velha)",
          depois == (), depois)
    check("e o templatize de toda mensagem continua apagando a marca",
          "Vagalume" not in mascarado and "{CORRETORA}" in mascarado, mascarado)

    run_ataques(dist, store, cur, cap)

    print(f"\n== Resumo: {PASS} passaram, {FAIL} falharam ==")
    if FAILURES:
        for n, d in FAILURES:
            print(f"  - {n}: {d}")
        sys.exit(1)


if __name__ == "__main__":
    run()
