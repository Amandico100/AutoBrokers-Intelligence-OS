"""Nenhuma conversa se perde ao virar mapa. SPEC-038.

O que aconteceu em 28/07/2026
------------------------------
A Resulta pareou o WhatsApp e o `HISTORY_SYNC` trouxe 7.445 eventos de seis
seguradoras em duas horas. Ao conferir os mapas tecidos:

    Allianz .... `meta.events` = 2000   no banco: 4.986
    Porto ...... `meta.events` = 1000   no banco: 1.009

Dois mil e mil. Redondos demais para serem coincidência: é o **limite padrão do
PostgREST**, que devolve no máximo 1.000 linhas por consulta e **não avisa**.

O tecelão pedia os eventos em lotes de 50 sessões e confiava no que voltava.
A Allianz tinha 81 sessões — dois lotes, dois mil eventos, **2.986 descartados
em silêncio**. O mapa foi construído sobre 40% do material.

Por que este é o pior tipo de defeito
-------------------------------------
O mapa não parecia quebrado. Parecia **pequeno**. E "pequeno" a gente atribui a
"a corretora usou pouco" — nunca a "o leitor cortou".

As mensagens nunca saíram do banco. Mas o que o agente vai seguir amanhã é o
MAPA, e o mapa estava pela metade.

A regra do Founder
------------------
> "NENHUMA MSG PODE SER PERDIDA OU APAGADA DO WHATSAPP DA RESULTA. TAMBÉM
>  PRECISAMOS GARANTIR QUE TODOS OS MAPAS SEJAM PREENCHIDOS, SEM ERRO."
"""

from __future__ import annotations

import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FALHAS: list[str] = []


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def _ler(*p: str) -> str:
    with open(os.path.join(RAIZ, *p), encoding="utf-8") as fh:
        return fh.read()


def _so_codigo(fonte: str) -> str:
    aspas3 = chr(34) * 3
    sem_doc = re.sub(aspas3 + r"(?:.|\n)*?" + aspas3, "", fonte)
    return "\n".join(l for l in sem_doc.split("\n")
                     if not l.lstrip().startswith("#"))


def teste_o_tecelao_pagina_ate_o_fim():
    print("\n[1] O tecelão lê TODAS as páginas, não as primeiras mil")
    fonte = _so_codigo(_ler("app", "services", "atlas", "weaver.py"))
    checar("_pagina_tudo" in fonte, "existe leitura paginada")
    checar(".range(" in fonte, "usa `range` para pedir a página seguinte")
    # Sem `order`, o Postgres não garante a mesma sequência entre páginas — a
    # paginação passa a pular e repetir linhas, que é pior que truncar.
    i = fonte.find("def _eventos")
    corpo = fonte[i: i + 700] if i != -1 else ""
    checar(".order(" in corpo,
           "a consulta paginada tem ordem fixa",
           "sem ordem, paginar pula e repete — pior que truncar")
    checar("if len(lote) < _PAGINA" in fonte,
           "para quando a fonte seca, não num número fixo")


def teste_a_sentinela_pagina_as_rotas():
    print("\n[2] A Sentinela enxerga TODAS as rotas")
    fonte = _so_codigo(_ler("app", "services", "atlas", "route_sentinel.py"))
    i = fonte.find("def _keys")
    corpo = fonte[i: i + 1200] if i != -1 else ""
    checar(".range(" in corpo,
           "a lista de rotas é paginada",
           "com 3 corretoras pareadas passa de 1.000 sessões, e as rotas "
           "cortadas nunca mais seriam retecidas")
    checar(".order(" in corpo, "com ordem fixa")


def teste_a_marca_dagua_e_a_ingestao():
    print("\n[3] Histórico antigo que ACABOU de chegar conta como novidade")
    fonte = _so_codigo(_ler("app", "services", "atlas", "route_sentinel.py"))
    i = fonte.find("def _session_watermarks")
    corpo = fonte[i: i + 900] if i != -1 else ""
    checar('row.get("created_at")' in corpo,
           "a marca d'água é a data de INGESTÃO")
    # A ordem importa: created_at PRIMEIRO, last_event_at só como reserva.
    pos_criado = corpo.find('row.get("created_at")')
    pos_evento = corpo.find('row.get("last_event_at")')
    checar(pos_criado != -1 and (pos_evento == -1 or pos_criado < pos_evento),
           "e a data da mensagem é só reserva",
           "pareamento traz PASSADO: detectar novidade pela data da mensagem "
           "falha justamente quando a novidade é passado")
    # E a consulta tem de trazer o campo, senão a regra acima lê None.
    checar("created_at" in _ler("app", "services", "atlas", "route_sentinel.py")
           .split("observed_sessions")[1][:400],
           "a consulta traz `created_at`")


def teste_uma_seguradora_ruim_nao_derruba_as_outras():
    print("\n[4] Uma seguradora com defeito não deixa as outras sem mapa")
    fonte = _so_codigo(_ler("app", "api", "admin_atlas.py"))
    i = fonte.find("keys = await asyncio.to_thread(_distinct)")
    corpo = fonte[i: i + 1600] if i != -1 else ""
    checar("try:" in corpo and "except Exception" in corpo,
           "cada seguradora é tecida por conta própria")
    checar('"falhas"' in corpo,
           "e a resposta DIZ qual falhou",
           "um 500 mudo fez o Founder ver 'Falha ao tecer' sem saber de quê")
    checar('"ok": not falhas' in corpo,
           "`ok` só é verdadeiro se TODAS teceram",
           "ok com buraco escondido é a resposta mais perigosa possível aqui")
    # A lista antiga era `[await weave_insurer(k, ramo) for k in keys]`.
    checar(re.search(r"\[\s*await weave_insurer\([^\]]*for k in keys\s*\]",
                     corpo) is None,
           "a lista sem tratamento de erro não voltou")


def teste_um_vocabulario_so_para_o_estado_do_canal():
    print("\n[5] Um vocabulário só para 'o WhatsApp está conectado?'")
    # Havia três: o pareamento escrevia "connecting"/"connected", o webhook
    # escrevia "open"/"close" (vocabulário do Evolution) e as telas liam
    # "connected". Com a Resulta conectada e funcionando, o Admin mostrava
    # `unknown`.
    fonte = _so_codigo(_ler("app", "services", "whatsapp", "channel_state.py"))
    checar("def normalizar_estado" in fonte, "existe um tradutor único")
    checar('"open": CONECTADO' in fonte, "e ele conhece o vocabulário do Evolution")
    checar("DESCONHECIDO" in fonte and "_TRADUCAO.get(chave, DESCONHECIDO)" in fonte,
           "estado que ele não conhece vira DESCONHECIDO",
           "inventar conexão não confirmada faz o corretor achar que os "
           "segurados estão sendo atendidos quando não estão")

    # E quem escreve tem de traduzir.
    for arq in (("app", "api", "webhook.py"),
                ("app", "services", "atlas", "observer_intake.py")):
        f = _so_codigo(_ler(*arq))
        if '"channel_status"' in f:
            checar("normalizar_estado" in f,
                   f"{arq[-1]} traduz antes de gravar")


def teste_nada_no_atlas_apaga_conversa():
    print("\n[6] O material do Atlas nunca é apagado")
    # `observed_events` e `observed_sessions` são a matéria-prima dos mapas.
    # Nada, em lugar nenhum, pode removê-los: um mapa se reteceria pior amanhã
    # do que hoje, e ninguém saberia por quê.
    alvos = [("app", "services", "atlas", n) for n in
             ("weaver.py", "route_sentinel.py", "observer_intake.py",
              "history_ingest.py", "attendance_capture.py", "templater.py")]
    alvos.append(("app", "api", "admin_atlas.py"))
    for partes in alvos:
        fonte = _so_codigo(_ler(*partes))
        perigos = re.findall(
            r'table\(\s*["\'](observed_events|observed_sessions)["\']\s*\)'
            r'[^\n]*\.delete', fonte)
        checar(not perigos, f"{partes[-1]} não apaga material do Atlas",
               str(perigos[:2]))


def teste_a_purga_do_espelho_e_governada():
    print("\n[7] A única remoção que existe é a retenção — e é governada")
    # `purge_expired_sync` APAGA `attendance_transcripts` e
    # `attendance_sessions`. É deliberado e é a política de privacidade da
    # SPEC-040: o transcript CRU (com CPF, telefone, conversa do segurado)
    # expira; o destilado — playbooks de conduta, sem PII — é permanente.
    #
    # Este caso não proíbe a purga. Ele cobra as três coisas que a tornam
    # aceitável, e que se caírem transformam política em perda de dado.
    fonte = _so_codigo(_ler("app", "services", "atlas", "attendance_capture.py"))
    i = fonte.find("def purge_expired_sync")
    corpo = fonte[i: i + 900] if i != -1 else ""
    checar(bool(corpo), "a purga existe e está isolada numa função")

    # 1. Só o Espelho. O material do Atlas nunca entra aqui.
    checar("TRANSCRIPTS_TABLE" in corpo and "SESSIONS_TABLE" in corpo,
           "só apaga as tabelas do Espelho de Atendimento")
    checar("observed_events" not in corpo and "observed_sessions" not in corpo,
           "e NUNCA o material do Atlas",
           "o mapa precisa poder ser retecido daqui a um ano")

    # 2. Por data de INGESTÃO, não da mensagem. Sem isso, o histórico de março
    #    que acabou de chegar seria apagado no dia seguinte ao pareamento.
    checar('.lt("created_at"' in corpo,
           "o corte é por data de INGESTÃO",
           "por data da mensagem, o histórico recém-importado sumiria no dia "
           "seguinte ao pareamento")
    checar("wa_timestamp" not in corpo,
           "não usa a data original da mensagem")

    # 3. Prazo configurável e com piso — nunca zero por acidente.
    fonte_ret = fonte[fonte.find("def retention_days"): fonte.find("def retention_days") + 300]
    checar("max(7," in fonte_ret,
           "o prazo tem piso de 7 dias",
           "uma variável mal digitada não pode virar purga imediata")


def teste_a_mesma_mensagem_tem_sempre_o_mesmo_id():
    print("\n[8] Reimportar o histórico não cria cópia")
    # Medido em 28/07/2026: a Allianz tinha 14.203 linhas para 5.330 mensagens
    # reais. Os três history_sync do dia (14:01, 15:02, 15:43) gravaram tudo de
    # novo. O `on_conflict="observer_number,message_id"` existe e estava certo;
    # o id é que mudava, porque terminava em `hash(texto)` — e `hash()` de
    # string em Python é aleatorizado A CADA PROCESSO.
    fonte = _so_codigo(_ler("app", "services", "atlas", "history_ingest.py"))
    checar("abs(hash(" not in fonte,
           "o id não depende mais do hash aleatório do processo",
           "com PYTHONHASHSEED variável, cada reimportação duplica tudo")
    checar("hashlib" in fonte, "usa hash determinístico")

    import hashlib as _h
    import importlib.util as _iu
    spec = _iu.spec_from_file_location(
        "_hi", os.path.join(RAIZ, "app", "services", "atlas", "history_ingest.py"))
    mod = _iu.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception:  # noqa: BLE001 — sem deps de runtime, basta a função
        mod = None

    if mod is not None and hasattr(mod, "_history_message_id"):
        f = mod._history_message_id
        a = f("5511", 1767117869, 0, False, "text", "Termo de Privacidade")
        b = f("5511", 1767117869, 0, False, "text", "Termo de Privacidade")
        checar(a == b, "a mesma mensagem gera o mesmo id")
        # O id antigo usava só os 60 primeiros caracteres. Duas mensagens
        # longas com o mesmo começo colidiam, e a segunda era descartada em
        # silêncio pelo `ignore_duplicates` — isso PERDIA mensagem.
        longa_a = "x" * 60 + " primeira"
        longa_b = "x" * 60 + " segunda"
        checar(f("5511", 100, 0, False, "text", longa_a)
               != f("5511", 100, 0, False, "text", longa_b),
               "duas mensagens longas de começo igual não colidem",
               "o id antigo truncava em 60 e a segunda sumia")
        checar(f("5511", 100, 0, False, "text", "Ok")
               != f("5511", 100, 0, True, "text", "Ok"),
               "o 'Ok' da seguradora não é o 'Ok' da corretora")


def teste_o_espelho_le_cada_mensagem_uma_vez():
    print("\n[9] O Espelho não paga duas vezes pela mesma conversa")
    # Medido em 28/07/2026: `attendance_transcripts` tinha 116.877 linhas para
    # 58.786 mensagens reais (1,99x, todas do history_sync — o `live` está em
    # 1,00x). Cada conversa chegava à LLM com toda mensagem escrita duas vezes:
    # média de 15,1 linhas para 7,4 mensagens.
    #
    # E o transcript é cortado em 7.000 caracteres: 56 sessões estouravam o
    # teto, e só 9 estourariam sem as cópias. As 47 do meio são as conversas
    # mais longas — as que mais tinham a ensinar — e perdiam o fim, que é onde
    # o atendimento se resolve.
    fonte = _so_codigo(_ler("app", "services", "attendance_distiller.py"))
    i = fonte.find("def _load_session_text_sync")
    trecho = fonte[i:i + 1400] if i >= 0 else ""
    checar(bool(trecho), "a leitura do transcript existe")
    checar("_sem_copias" in trecho,
           "o transcript enviado à LLM passa pelo mesmo filtro de cópias",
           "sem isso o custo dobra e as conversas longas perdem o fim")
    checar("attendance_transcripts" in trecho, "e continua lendo a tabela certa")

    # O filtro é UM só, compartilhado com o Tecelão. Duas implementações
    # divergiriam com o tempo e uma delas voltaria a contar copiado.
    checar("from app.services.atlas.weaver import _sem_copias" in trecho,
           "e é o MESMO filtro do Tecelão, não uma segunda cópia da regra")


def teste_a_falha_de_midia_diz_o_que_houve():
    print("\n[10] 'HTTPStatusError' não conserta nada")
    # 23 mídias marcadas `failed` no Espelho, todas com o mesmo texto. 401
    # (token), 404 (mídia expirada no WhatsApp) e 5xx (servidor fora) pedem
    # três consertos diferentes, e o registro não distinguia nenhum.
    fonte = _so_codigo(_ler("app", "services", "atlas", "observer_media.py"))
    checar("_motivo_da_falha" in fonte, "a falha é traduzida antes de gravar")
    checar("status_code" in fonte, "e o status HTTP entra no registro")
    # A janela é a FUNÇÃO, não um punhado de caracteres: `_download_media` vem
    # logo depois e lê o token por dever de ofício. Medir o vizinho errado dá
    # alarme falso hoje e silêncio no dia que importa.
    i = fonte.find("def _motivo_da_falha")
    resto = fonte[i:]
    # `async def` também encerra a função: procurar só por `def` faz a janela
    # engolir a próxima — foi o que aconteceu na primeira versão deste teste.
    prox = re.search(r"\n(?:async\s+)?def\s", resto[1:])
    corpo = resto[:prox.start() + 1] if prox else resto
    checar(".text" not in corpo and ".content" not in corpo,
           "sem o corpo da resposta, que pode trazer dado de cliente")
    checar("token" not in corpo.lower() and "apikey" not in corpo.lower(),
           "e sem nada que se pareça com credencial", corpo[-90:])


def main() -> int:
    print("=" * 70)
    print("NENHUMA CONVERSA SE PERDE AO VIRAR MAPA")
    print("=" * 70)
    for teste in (teste_o_tecelao_pagina_ate_o_fim,
                  teste_a_sentinela_pagina_as_rotas,
                  teste_a_marca_dagua_e_a_ingestao,
                  teste_uma_seguradora_ruim_nao_derruba_as_outras,
                  teste_um_vocabulario_so_para_o_estado_do_canal,
                  teste_nada_no_atlas_apaga_conversa,
                  teste_a_purga_do_espelho_e_governada,
                  teste_a_mesma_mensagem_tem_sempre_o_mesmo_id,
                  teste_o_espelho_le_cada_mensagem_uma_vez,
                  teste_a_falha_de_midia_diz_o_que_houve):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {teste.__name__} EXPLODIU: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 70)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("O MAPA É FEITO DE TUDO QUE FOI OBSERVADO, NÃO DAS PRIMEIRAS MIL LINHAS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
