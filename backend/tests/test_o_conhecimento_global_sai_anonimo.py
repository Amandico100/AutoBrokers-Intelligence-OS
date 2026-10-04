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


def run():
    print("== P-E0018-14 · o conhecimento global sai sempre anonimo ==\n")
    dist, store, _redis, _qdrant, _factory = O3._bootstrap()
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
    check("depois da releitura com banco mudo, a lista continua", depois == antes, depois)
    check("e o templatize de toda mensagem continua apagando a marca",
          "Vagalume" not in mascarado and "{CORRETORA}" in mascarado, mascarado)

    print(f"\n== Resumo: {PASS} passaram, {FAIL} falharam ==")
    if FAILURES:
        for n, d in FAILURES:
            print(f"  - {n}: {d}")
        sys.exit(1)


if __name__ == "__main__":
    run()
