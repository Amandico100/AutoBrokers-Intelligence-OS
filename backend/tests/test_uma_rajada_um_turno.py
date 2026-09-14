# -*- coding: utf-8 -*-
r"""G1 · G2 · G4 · G5 — UMA RAJADA, UM TURNO.
SPEC-EXTRA-001.2 BLOCO AB (§5, §6.1, §6.3, §12).

🔴 **O defeito, medido.** `message_buffer_service.should_process` fechava a
rajada por OCIOSIDADE, com um PISO de 8 s que nenhuma configuração descia. A
pessoa mandava cinco mensagens em 40 s e recebia duas respostas — a primeira
sem ter lido a segunda metade. 📊 No acervo, **113 de 400** rajadas reais
viraram 2+ blocos de resposta; das 400, a janela por conteúdo une **189** em um
turno só (contra 127 com janela fixa de 8 s).

🔴 **E o elo que a proteção declarada não cobria.** `buffer_processor.py:47-51`
afirma que o `get_and_clear` atômico protege contra concorrência. Protege
contra DUAS TAREFAS NA MESMA CHAVE — não contra a **chave nova** que as
mensagens 3, 4 e 5 criam enquanto a resposta 1 é gerada, e que a varredura de
1 s transforma no segundo turno. É esse buraco que a TRAVA fecha.

```
 [G1a] A TRAVA        duas tarefas na MESMA conversa -> uma ganha; a outra
                      devolve False e ⛔ NÃO TOCA O BUFFER
 [G1b] O PARALELO     conversas diferentes -> chaves de turno diferentes
                      (LINHA DE CONTROLE: test_midia_e_concorrencia_do_webhook)
 [G1c] ESCOPO VAZIO   duas corretoras sem integração identificada -> NENHUMA
                      trava a outra (recusa fail-closed). 🔴 vermelho HOJE
 [G1d] @lid           o MESMO contato por `@lid` e por telefone -> UMA chave
 [G1e] A LIBERAÇÃO    `fechar_turno` usa o script LITERAL da doc do Redis
 [G2]  A JANELA       as 20 rajadas REAIS do corpus, pelo motor, com o relógio
                      dublado -> o número de turnos que a regra prevê
 [G4]  RE-PLANEJAR    a mensagem do meio da janela entra na MESMA resposta
 [G5]  A POSSE        quem perdeu o turno NÃO envia
```

⛔ SEGURANÇA: sem rede, sem banco, sem Redis de verdade. O corpus guarda só
traços; nenhum telefone deste arquivo existe.

Rodar (de dentro de `backend/`):
    PYTHONIOENCODING=utf-8 python tests/test_uma_rajada_um_turno.py
    ... --so G2   ·   ... --mutar   ·   ... --mutar M-AB1
"""
from __future__ import annotations

import asyncio
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # .../backend
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
os.environ["SEM_REDE"] = "1"

PASS = 0
FAIL = 0

#: ⛔ 100% SINTÉTICOS.
TEL_A = "5511900000001"
TEL_B = "5511900000002"
INTEG_A = "integ-corretora-A"
INTEG_B = "integ-corretora-B"

CORPUS = os.path.join(RAIZ, "tests", "corpus", "rajadas_reais.jsonl")

import app.services.message_buffer_service as M  # noqa: E402
from app.services.whatsapp.identidade_do_evento import telefone_do_evento  # noqa: E402


def _p(texto):
    try:
        print(texto)
    except UnicodeEncodeError:
        cod = getattr(sys.stdout, "encoding", None) or "ascii"
        print(str(texto).encode(cod, "replace").decode(cod, "replace"))


def check(nome, cond, detalhe=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        _p("  [ok] %s" % nome)
    else:
        FAIL += 1
        _p("  [FALHOU] %s" % nome + ("\n         %s" % str(detalhe)[:700] if detalhe else ""))
    return bool(cond)


# ===========================================================================
# O RELÓGIO DUBLADO — a rajada real acontece em 40 s; o teste, em milissegundos
# ===========================================================================
RELOGIO = [datetime(2026, 9, 14, 12, 0, 0)]


class _DataHoraDublada:
    @staticmethod
    def now():
        return RELOGIO[0]

    @staticmethod
    def fromisoformat(texto):
        return datetime.fromisoformat(texto)


def _ligar_o_relogio():
    M.datetime = _DataHoraDublada


def _andar(segundos: float):
    RELOGIO[0] = RELOGIO[0] + timedelta(seconds=segundos)


# ===========================================================================
# O REDIS DUBLÊ — `set(nx,ex)`, `get`, `delete`, `setex`, `eval`, `pipeline`.
# ⚠️ O TTL expira pelo RELÓGIO DUBLADO: é assim que G5 consegue ver um turno
#    que estourou sem esperar 90 segundos de verdade.
# ===========================================================================
class _Pipe:
    def __init__(self, redis):
        self.redis = redis
        self.acoes = []

    def get(self, k):
        self.acoes.append(("get", k))

    def delete(self, k):
        self.acoes.append(("delete", k))

    async def execute(self):
        saida = []
        for acao, k in self.acoes:
            saida.append(await getattr(self.redis, acao)(k))
        return saida


class _RedisDuble:
    def __init__(self):
        self.dados = {}       # chave -> (valor, expira_em|None)

    def _vivo(self, k):
        item = self.dados.get(k)
        if item is None:
            return None
        valor, expira = item
        if expira is not None and RELOGIO[0] >= expira:
            self.dados.pop(k, None)
            return None
        return valor

    async def get(self, k):
        return self._vivo(k)

    async def set(self, k, v, nx=False, ex=None):
        if nx and self._vivo(k) is not None:
            return None
        self.dados[k] = (v, RELOGIO[0] + timedelta(seconds=int(ex)) if ex else None)
        return True

    async def setex(self, k, ttl, v):
        self.dados[k] = (v, RELOGIO[0] + timedelta(seconds=int(ttl)))
        return True

    async def delete(self, k):
        return 1 if self.dados.pop(k, None) is not None else 0

    async def eval(self, script, numkeys, *args):
        chave = args[0]
        token = args[1]
        atual = self._vivo(chave)
        if script == M.LUA_LIBERA_SE_FOR_MEU:
            if atual == token:
                self.dados.pop(chave, None)
                return 1
            return 0
        if script == M.LUA_RENOVA_SE_FOR_MEU:
            if atual == token:
                valor, _ = self.dados[chave]
                self.dados[chave] = (
                    valor, RELOGIO[0] + timedelta(seconds=int(args[2])))
                return 1
            return 0
        # ⛔ Um script desconhecido NÃO pode "passar": seria um DEL cego
        # atravessando o dublê sem ninguém ver.
        raise AssertionError("script Lua desconhecido no dublê: %r" % script[:80])

    def pipeline(self):
        return _Pipe(self)


def servico_novo():
    _ligar_o_relogio()
    return M.MessageBufferService(_RedisDuble())


# ===========================================================================
# O SINTETIZADOR — traços do corpus de volta a um texto que os REPRODUZ
# ===========================================================================
#
# 🔴 O corpus guarda traços, nunca texto (§13) — e `should_process` precisa de
# uma mensagem. A saída é gerar um texto SINTÉTICO e **provar, pelo próprio
# motor, que ele tem os mesmos traços da mensagem real**. Se a síntese errar, o
# teste falha ali, antes de medir qualquer janela.
def texto_com_os_tracos(item: dict) -> str:
    if item["tipo"] != "text" and not item["n_chars"]:
        return ""
    if item["dado_curto"]:
        return "ok." if item["pont_final"] else "ok"
    if item["conectivo"]:
        return "eu preciso de"
    if item["pont_final"]:
        return "preciso de ajuda com o carro."
    return "preciso de ajuda com o carro hoje cedo"


def conferir_a_sintese(item: dict) -> bool:
    t = M.tracos_da_mensagem(texto_com_os_tracos(item), tipo=item["tipo"])
    return (t.dado_curto == item["dado_curto"]
            and t.termina_em_pontuacao_final == item["pont_final"]
            and t.termina_em_conectivo == item["conectivo"])


def carregar_corpus():
    with io.open(CORPUS, encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


# ===========================================================================
# G1a — DUAS TAREFAS NA MESMA CONVERSA
# ===========================================================================
def g1a():
    _p("\n[G1a] Duas tarefas na MESMA conversa: uma ganha, a outra não toca o buffer")

    async def cenario():
        s = servico_novo()
        await s.add_message(TEL_A, "bateu o carro", "pending", "pending", {},
                            {"_integration_id": INTEG_A}, escopo=INTEG_A)
        chave = s.chave(INTEG_A, TEL_A)

        primeiro = await s.abrir_turno(INTEG_A, TEL_A)
        segundo = await s.abrir_turno(INTEG_A, TEL_A)
        buffer_intacto = await s.redis.get(chave) is not None
        return primeiro, segundo, buffer_intacto, s, chave

    primeiro, segundo, intacto, s, chave = asyncio.run(cenario())
    check("a primeira tarefa ganha o turno (token)", bool(primeiro))
    check("a segunda devolve None", segundo is None,
          "com duas travas abertas, as duas rodadas respondem a mesma pessoa")
    check("e o BUFFER continua lá, intocado", intacto,
          "🔴 a ordem é a regra: se a trava viesse DEPOIS do get_and_clear, "
          "perder a trava custaria as cinco mensagens do segurado")

    async def liberar():
        fechou = await s.fechar_turno(INTEG_A, TEL_A, primeiro)
        de_novo = await s.abrir_turno(INTEG_A, TEL_A)
        return fechou, de_novo

    fechou, de_novo = asyncio.run(liberar())
    check("fechar_turno libera", fechou)
    check("e a conversa volta a aceitar turno", bool(de_novo))


# ===========================================================================
# G1b — CONVERSAS DIFERENTES NÃO SE TRAVAM
# ===========================================================================
def g1b():
    _p("\n[G1b] A trava é por CONVERSA, nunca por corretora")

    async def cenario():
        s = servico_novo()
        um = await s.abrir_turno(INTEG_A, TEL_A)
        outro = await s.abrir_turno(INTEG_A, TEL_B)
        mesma_pessoa_outra_corretora = await s.abrir_turno(INTEG_B, TEL_A)
        return um, outro, mesma_pessoa_outra_corretora

    um, outro, cruzado = asyncio.run(cenario())
    check("dois segurados da MESMA corretora rodam em paralelo",
          bool(um) and bool(outro),
          "⛔ trava por corretora é o defeito da EXTRA-001.8, não o conserto desta")
    check("o MESMO segurado em DUAS corretoras roda em paralelo", bool(cruzado),
          "a chave herda o escopo do buffer (SPEC-063 Bloco H)")
    check("a chave do turno carrega escopo E telefone",
          M.MessageBufferService.chave_do_turno(INTEG_A, TEL_A)
          != M.MessageBufferService.chave_do_turno(INTEG_A, TEL_B),
          "chave sem telefone = uma corretora inteira em fila indiana")


# ===========================================================================
# G1c — ESCOPO VAZIO: FAIL-CLOSED (🔴 vermelho ANTES do código)
# ===========================================================================
def g1c():
    _p("\n[G1c] Escopo vazio nas DUAS corretoras: nenhuma trava a outra")

    async def cenario():
        s = servico_novo()
        a = await s.abrir_turno("", TEL_A)
        b = await s.abrir_turno("", TEL_A)          # outra corretora, mesmo telefone
        rotulo = await s.abrir_turno("sem-integracao", TEL_A)
        sem_telefone = await s.abrir_turno(INTEG_A, "")
        return a, b, rotulo, sem_telefone

    a, b, rotulo, sem_tel = asyncio.run(cenario())
    check("escopo vazio RECUSA o turno (fail-closed)", a is None,
          "aceitar custaria a resposta da corretora ERRADA, e isso não volta atrás")
    check("e a segunda corretora também é recusada — nenhuma trava a outra",
          b is None,
          "🔴 é o estado de HOJE que este guarda mata: as duas caíam em "
          "`whatsapp_turno:sem-integracao:{telefone}`")
    check("o rótulo `sem-integracao` explícito também recusa", rotulo is None,
          "ele é FIXO: não isola nada")
    check("evento sem contraparte identificável recusa", sem_tel is None)


# ===========================================================================
# G1d — @lid E TELEFONE SÃO UMA CHAVE SÓ
# ===========================================================================
def g1d():
    _p("\n[G1d] O mesmo contato por @lid e por telefone gera UMA chave")

    por_lid = telefone_do_evento(
        {"remoteJid": "123456789012345@lid", "remoteJidAlt": TEL_A + "@s.whatsapp.net"})
    por_linha = telefone_do_evento({"remoteJid": TEL_A + "@s.whatsapp.net"})

    check("`telefone_do_evento` resolve o @lid para o telefone",
          por_lid == TEL_A, f"veio {por_lid!r}")
    check("e a linha direta dá o mesmo telefone", por_linha == TEL_A)
    check("logo, UMA chave de turno",
          M.MessageBufferService.chave_do_turno(INTEG_A, por_lid)
          == M.MessageBufferService.chave_do_turno(INTEG_A, por_linha),
          "duas chaves = dois turnos = duas respostas para a mesma pessoa")
    check("e UMA chave de buffer",
          M.MessageBufferService.chave(INTEG_A, por_lid)
          == M.MessageBufferService.chave(INTEG_A, por_linha))


# ===========================================================================
# G1e — A LIBERAÇÃO É O SCRIPT LITERAL DA DOC
# ===========================================================================
def g1e():
    _p("\n[G1e] `fechar_turno` usa o script literal da doc do Redis, e nunca DEL cego")

    literal = ('if redis.call("get",KEYS[1]) == ARGV[1] then '
               'return redis.call("del",KEYS[1]) else return 0 end')
    check("o script do código é IGUAL ao da documentação (§20 E01)",
          M.LUA_LIBERA_SE_FOR_MEU == literal,
          f"código: {M.LUA_LIBERA_SE_FOR_MEU!r}")

    fonte = io.open(os.path.join(RAIZ, "app", "services",
                                 "message_buffer_service.py"), encoding="utf-8").read()
    corpo = fonte[fonte.index("    async def fechar_turno"):]
    corpo = corpo[:corpo.index("\n    async def ")] if "\n    async def " in corpo else corpo
    check("e `fechar_turno` não chama `delete` direto",
          ".delete(" not in corpo,
          "um DEL cego apaga a trava de OUTRO turno — E01 é explícita")

    async def cenario():
        s = servico_novo()
        meu = await s.abrir_turno(INTEG_A, TEL_A)
        alheio = await s.fechar_turno(INTEG_A, TEL_A, "token-de-outra-rodada")
        ainda = await s.ainda_sou_o_dono(INTEG_A, TEL_A, meu)
        return alheio, ainda

    alheio, ainda = asyncio.run(cenario())
    check("token errado NÃO libera a trava", alheio is False)
    check("e o dono continua dono", ainda is True)


# ===========================================================================
# G2 — AS 20 RAJADAS REAIS, PELO MOTOR, COM O RELÓGIO DUBLADO
# ===========================================================================
async def _turnos_da_rajada(rajada, servico=None):
    """Roda a rajada pelo MOTOR: `add_message` + `should_process` reais, com a
    varredura de 1 s do `buffer_processor` reproduzida sobre o relógio dublado.
    """
    s = servico or servico_novo()
    chave = s.chave(INTEG_A, TEL_A)
    turnos = 0

    async def varrer(segundos: float):
        nonlocal turnos
        restante = float(segundos)
        while restante > 0:
            passo = min(1.0, restante)
            _andar(passo)
            restante -= passo
            if await s.should_process(chave):
                turnos += 1
                await s.get_and_clear_buffer(chave)

    for pos, item in enumerate(rajada["itens"]):
        if pos:
            await varrer(item["intervalo_ms"] / 1000.0)
        await s.add_message(
            TEL_A, texto_com_os_tracos(item), "pending", "pending", {},
            {"_integration_id": INTEG_A}, escopo=INTEG_A, tipo=item["tipo"])
    # depois da última mensagem, a varredura continua até a janela fechar
    await varrer(float(M.TETO_DA_RAJADA_SEGUNDOS) + 2.0)
    return turnos


def g2():
    _p("\n[G2] As 20 rajadas REAIS do corpus, pelo motor")
    corpus = carregar_corpus()
    check("o corpus tem pelo menos 20 rajadas reais", len(corpus) >= 20,
          f"tem {len(corpus)}")

    sinteses_ok = sum(1 for r in corpus for i in r["itens"] if conferir_a_sintese(i))
    total_itens = sum(len(r["itens"]) for r in corpus)
    check("cada texto sintético REPRODUZ os traços da mensagem real",
          sinteses_ok == total_itens,
          f"{sinteses_ok}/{total_itens} — se a síntese erra, a janela mede outra coisa")

    certas = erradas = 0
    detalhe = []
    for rajada in corpus:
        RELOGIO[0] = datetime(2026, 9, 14, 12, 0, 0)
        vistos = asyncio.run(_turnos_da_rajada(rajada))
        if vistos == rajada["turnos_esperados"]:
            certas += 1
        else:
            erradas += 1
            detalhe.append("%s: motor %d x esperado %d"
                           % (rajada["id"], vistos, rajada["turnos_esperados"]))
    check("o MOTOR devolve exatamente o número de turnos que a regra prevê",
          erradas == 0, "; ".join(detalhe[:6]))

    um_turno = [r for r in corpus if r["turnos_esperados"] == 1]
    unia_hoje = [r for r in um_turno if r["turnos_hoje"] >= 2]
    check("a maioria do corpus vira UM turno", len(um_turno) >= 15,
          f"{len(um_turno)} de {len(corpus)}")
    check("e a maior parte delas HOJE virava 2+ respostas — é o defeito que morre",
          len(unia_hoje) >= 10, f"{len(unia_hoje)}")

    # 🔴 LINHA DE CONTROLE: a mesma bateria com a janela FIXA de 8 s tem de dar
    # OUTRO número. Sem ela, um corpus fácil "passaria" por acaso.
    guardados = (M.JANELA_DADO_CURTO_SEGUNDOS, M.JANELA_FRASE_INACABADA_SEGUNDOS)
    try:
        M.JANELA_DADO_CURTO_SEGUNDOS = 8
        M.JANELA_FRASE_INACABADA_SEGUNDOS = 8
        fixa = 0
        for rajada in corpus:
            RELOGIO[0] = datetime(2026, 9, 14, 12, 0, 0)
            if asyncio.run(_turnos_da_rajada(rajada)) != rajada["turnos_esperados"]:
                fixa += 1
    finally:
        (M.JANELA_DADO_CURTO_SEGUNDOS,
         M.JANELA_FRASE_INACABADA_SEGUNDOS) = guardados
    check("CONTROLE: com janela FIXA de 8 s o mesmo motor erra %d rajadas" % fixa,
          fixa >= 3,
          "as duas medidas precisam CONSEGUIR ser diferentes (CLAUDE.md §9.2)")


# ===========================================================================
# G2b — O PISO DE 8 s MORREU
# ===========================================================================
def g2b():
    _p("\n[G2b] O piso de 8 s morreu, e o teto não sobe acima de 25 s")
    saida = subprocess.run(
        [sys.executable, "-c",
         "import io,os,sys;"
         "alvo='max(settings.BUFFER';"
         "achados=[];"
         "[achados.append(os.path.join(r,f)) for r,_,fs in os.walk('app') "
         "for f in fs if f.endswith('.py') and alvo in "
         "io.open(os.path.join(r,f),encoding='utf-8').read()];"
         "print('|'.join(achados))"],
        cwd=RAIZ, capture_output=True, text=True,
        encoding="utf-8", errors="replace")
    check("`grep max(settings.BUFFER` volta VAZIO",
          not (saida.stdout or "").strip(),
          f"sobreviventes: {saida.stdout!r} — sobrevivente = defeito")

    check("a janela do dado curto é 3 s", M.JANELA_DADO_CURTO_SEGUNDOS == 3)
    check("a da frase completa, 8 s", M.JANELA_FRASE_COMPLETA_SEGUNDOS == 8)
    check("a da frase inacabada, 18 s", M.JANELA_FRASE_INACABADA_SEGUNDOS == 18)
    check("o teto é 25 s — a constante da Meta (§20 E02)",
          M.TETO_DA_RAJADA_SEGUNDOS == 25)

    curto = M.janela_de_espera(M.tracos_da_mensagem("ABC1D23"))
    frase = M.janela_de_espera(M.tracos_da_mensagem("bati o carro na esquina."))
    meio = M.janela_de_espera(M.tracos_da_mensagem("eu estava indo para"))
    check("um dado curto fecha em 3 s", curto == 3, f"deu {curto}")
    check("uma frase completa, em 8 s", frase == 8, f"deu {frase}")
    check("uma frase inacabada, em 18 s", meio == 18, f"deu {meio}")
    check("e as três CONSEGUEM ser diferentes", len({curto, frase, meio}) == 3)


# ===========================================================================
# G4 — A MENSAGEM DO MEIO DA JANELA ENTRA NA MESMA RESPOSTA
# ===========================================================================
def g4():
    _p("\n[G4] A mensagem que chega no meio do turno entra na MESMA resposta")

    async def cenario():
        s = servico_novo()
        chave = s.chave(INTEG_A, TEL_A)
        await s.add_message(TEL_A, "bati o carro", "pending", "pending", {},
                            {"_integration_id": INTEG_A}, escopo=INTEG_A)
        await s.add_message(TEL_A, "na avenida", "pending", "pending", {},
                            {"_integration_id": INTEG_A}, escopo=INTEG_A)
        buffer = await s.get_and_clear_buffer(chave)
        combinado = s.get_combined_message(buffer)

        # ... e AGORA o segurado manda a terceira, com o turno já aberto.
        await s.add_message(TEL_A, "tem foto aqui", "pending", "pending", {},
                            {"_integration_id": INTEG_A}, escopo=INTEG_A)
        novos = await s.mesclar_o_que_chegou(chave)
        sobrou = await s.redis.get(chave)
        vazio = await s.mesclar_o_que_chegou(chave)
        return combinado, novos, sobrou, vazio

    combinado, novos, sobrou, vazio = asyncio.run(cenario())
    check("a rajada original vira UM texto", combinado.count("\n") == 1, repr(combinado))
    check("a mensagem do meio é devolvida pela re-leitura", len(novos) == 1,
          f"{novos!r} — devolver [] é a mensagem se PERDENDO")
    check("e ela não se perde: o texto dela está lá",
          M.texto_do_item(novos[0]) == "tem foto aqui")
    check("o buffer fica VAZIO depois da mescla (get+delete atômico)", sobrou is None)
    check("uma segunda re-leitura devolve [] — não há laço", vazio == [])
    check("o teto de re-planejamento existe e é finito",
          isinstance(M.REPLANEJAMENTOS_MAX, int) and 0 < M.REPLANEJAMENTOS_MAX <= 5,
          f"REPLANEJAMENTOS_MAX={M.REPLANEJAMENTOS_MAX}")


# ===========================================================================
# G5 — QUEM PERDEU A POSSE NÃO ENVIA
# ===========================================================================
def g5():
    _p("\n[G5] Quem perdeu a posse do turno NÃO envia")

    async def cenario():
        s = servico_novo()
        token = await s.abrir_turno(INTEG_A, TEL_A, ttl_s=90)
        dono_agora = await s.ainda_sou_o_dono(INTEG_A, TEL_A, token)
        _andar(91)                       # o turno estourou o TTL
        dono_depois = await s.ainda_sou_o_dono(INTEG_A, TEL_A, token)
        outro = await s.abrir_turno(INTEG_A, TEL_A)     # outra rodada assumiu
        dono_com_outro = await s.ainda_sou_o_dono(INTEG_A, TEL_A, token)
        impostor = await s.ainda_sou_o_dono(INTEG_A, TEL_A, "token-inventado")
        return dono_agora, dono_depois, outro, dono_com_outro, impostor

    agora, depois, outro, com_outro, impostor = asyncio.run(cenario())
    check("dentro do turno, sou o dono", agora is True)
    check("depois do TTL, NÃO sou mais", depois is False,
          "E01: 'don't assume that a lock is retained as long as the process "
          "that had acquired it is alive'")
    check("outra rodada consegue abrir o turno", bool(outro))
    check("e o token velho deixa de ser dono", com_outro is False,
          "enviar aqui seria a SEGUNDA resposta para a mesma pergunta")
    check("token inventado nunca é dono", impostor is False)

    # E o caminho REAL de envio pergunta isso ANTES de falar.
    fonte = io.open(os.path.join(RAIZ, "app", "api", "webhook.py"),
                    encoding="utf-8").read()
    pos_posse = fonte.find("ainda_sou_o_dono")
    pos_envio = fonte.find("whatsapp_service.send_message,\n            to_number=")
    if pos_envio < 0:
        pos_envio = fonte.find("to_number=payload.phone, text=ai_response")
    check("`ainda_sou_o_dono` está no caminho de envio do webhook", pos_posse > 0)
    check("e ele é perguntado ANTES do `send_message` da resposta",
          0 < pos_posse < pos_envio,
          f"posse em {pos_posse}, envio em {pos_envio}")
    trecho = fonte[pos_posse:pos_envio] if pos_posse > 0 else ""
    check("e quem perdeu a posse RETORNA sem enviar", "\n                return" in trecho,
          "⛔ nunca enviar 'por via das dúvidas'")


# ===========================================================================
# G5b — A TRAVA EXISTE MESMO NO SERVIÇO REAL
# ===========================================================================
def g5b():
    _p("\n[G5b] O serviço REAL tem a trava (o varredor tolera dublê, o produto não)")
    for nome in ("abrir_turno", "renovar_turno", "ainda_sou_o_dono",
                 "fechar_turno", "chave_do_turno", "mesclar_o_que_chegou"):
        check("MessageBufferService.%s existe" % nome,
              hasattr(M.MessageBufferService, nome),
              "o `getattr` do buffer_processor degrada em silêncio se sumir")

    proc = io.open(os.path.join(RAIZ, "app", "tasks", "buffer_processor.py"),
                   encoding="utf-8").read()
    pos_trava = proc.find("abrir_turno")
    pos_clear = proc.find("get_and_clear_buffer(chave)")
    check("no varredor, a trava vem ANTES do get_and_clear",
          0 < pos_trava < pos_clear,
          "🔴 invertido, perder a trava custa o BUFFER — as mensagens somem")
    check("e o turno é sempre fechado (`finally`)",
          "finally:" in proc and "fechar_turno" in proc)

    async def renova():
        s = servico_novo()
        token = await s.abrir_turno(INTEG_A, TEL_A, ttl_s=90)
        ok = await s.renovar_turno(INTEG_A, TEL_A, token, ttl_s=90)
        alheio = await s.renovar_turno(INTEG_A, TEL_A, "outro", ttl_s=90)
        no_teto = await s.renovar_turno(INTEG_A, TEL_A, token, ttl_s=90,
                                        renovacoes_feitas=M.TURNO_RENOVACOES_MAX)
        return ok, alheio, no_teto

    ok, alheio, no_teto = asyncio.run(renova())
    check("o dono renova", ok is True)
    check("quem não é dono NÃO renova", alheio is False)
    check("e a renovação tem TETO (E01)", no_teto is False,
          f"TURNO_RENOVACOES_MAX={M.TURNO_RENOVACOES_MAX}")


GATES = {"G1a": g1a, "G1b": g1b, "G1c": g1c, "G1d": g1d, "G1e": g1e,
         "G2": g2, "G2b": g2b, "G4": g4, "G5": g5, "G5b": g5b}


# ===========================================================================
# AS MUTACOES — por COPIA, em SUBPROCESSO. A arvore precisa estar parada.
# ===========================================================================
MBS = "app/services/message_buffer_service.py"

MUTACOES = [
    # (a) a trava que sempre deixa entrar = trava nenhuma
    ("M-AB1", MBS,
     "        token = uuid4().hex\n        chave = self.chave_do_turno(escopo, phone)",
     "        token = uuid4().hex\n        chave = self.chave_do_turno(escopo, phone)\n"
     "        return token  # MUTACAO",
     "G1a"),
    # (b) chave da trava SEM o telefone -> uma corretora inteira em fila indiana
    ("M-AB2", MBS,
     '        return f"{TURNO_PREFIXO}:{esc}:{phone}"',
     '        return f"{TURNO_PREFIXO}:{esc}"  # MUTACAO',
     "G1b"),
    # (c) 🔴 aceitar escopo vazio = o estado de HOJE, e duas corretoras colidem
    ("M-AB3", MBS,
     '        esc = str(escopo or "").strip()\n'
     '        return bool(esc) and esc != ESCOPO_SEM_INTEGRACAO',
     "        return True  # MUTACAO",
     "G1c"),
    # (d) DEL cego no lugar do script que compara o valor
    ("M-AB4", MBS,
     "            resultado = await self.redis.eval(\n"
     "                LUA_LIBERA_SE_FOR_MEU, 1, chave, token)",
     "            resultado = await self.redis.delete(chave)  # MUTACAO",
     "G1e"),
    # (e) janela FIXA de 8 s -> as rajadas do corpus fragmentam
    ("M-AB5", MBS,
     "    if t.dado_curto:\n        return JANELA_DADO_CURTO_SEGUNDOS",
     "    return 8  # MUTACAO\n    if t.dado_curto:\n        return JANELA_DADO_CURTO_SEGUNDOS",
     "G2"),
    # (f) a re-leitura devolve [] -> a mensagem do meio se perde
    ("M-AB6", MBS,
     "        bruto = resultados[0] if resultados else None",
     "        return []  # MUTACAO\n        bruto = resultados[0] if resultados else None",
     "G4"),
    # (g) `ainda_sou_o_dono` sempre True -> duas respostas
    ("M-AB7", MBS,
     "        if not token:\n            return False\n"
     "        chave = self.chave_do_turno(escopo, phone)\n        try:\n"
     "            atual = await self.redis.get(chave)",
     "        return True  # MUTACAO\n"
     "        if not token:\n            return False\n"
     "        chave = self.chave_do_turno(escopo, phone)\n        try:\n"
     "            atual = await self.redis.get(chave)",
     "G5"),
    # (h) desligar a resolução de @lid -> duas chaves para a mesma pessoa
    ("M-AB8", "app/services/whatsapp/identidade_do_evento.py",
     '    if remoto.endswith("@lid"):',
     '    if False and remoto.endswith("@lid"):  # MUTACAO',
     "G1d"),
    # (i) o teto do buffer volta a poder SUBIR acima de 25 s
    ("M-AB9", MBS,
     "TETO_DA_RAJADA_SEGUNDOS = 25",
     "TETO_DA_RAJADA_SEGUNDOS = 300  # MUTACAO",
     "G2b"),
]


def _rodar(gate):
    return subprocess.run(
        [sys.executable, os.path.abspath(__file__), "--so", gate],
        # 🔴 `text=True` sozinho decodifica com a codepage do Windows (cp1252) e
        # ESTOURA no primeiro emoji da saida: `r.stdout` volta VAZIO e uma
        # mutacao VERMELHA e contada como verde. Medido em 14/09/2026.
        cwd=RAIZ, capture_output=True, text=True, timeout=900,
        encoding="utf-8", errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"},
    )


def rodar_mutacoes(filtro=None):
    _p("\n[MUT] MUTACOES POR COPIA -- cada uma em SUBPROCESSO. A arvore precisa estar parada.")
    vermelhas = verdes = 0
    for mid, relativo, de, para, gate in MUTACOES:
        if filtro and mid != filtro:
            continue
        caminho = os.path.normpath(os.path.join(RAIZ, relativo))
        original = io.open(caminho, encoding="utf-8").read()
        if de not in original:
            _p("  [FALHOU] %s: a ancora nao existe em %s -- mutacao NAO aplicada "
               "NAO e mutacao passada" % (mid, relativo))
            verdes += 1
            continue
        base = _rodar(gate)
        backup = tempfile.NamedTemporaryFile(delete=False, suffix=".bak-ab-g1").name
        shutil.copyfile(caminho, backup)
        try:
            io.open(caminho, "w", encoding="utf-8", newline="\n").write(
                original.replace(de, para, 1))
            r = _rodar(gate)
            falhas = [l.strip() for l in (r.stdout or "").splitlines() if "[FALHOU]" in l]
            if base.returncode == 0 and r.returncode != 0 and falhas:
                vermelhas += 1
                _p("  [ok] %s deixa %s VERMELHO: %s" % (mid, gate, falhas[0][:180]))
            else:
                verdes += 1
                _p("  [FALHOU] %s NAO deixou %s vermelho (base rc=%s, mutado rc=%s)\n%s"
                   % (mid, gate, base.returncode, r.returncode, (r.stdout or r.stderr)[-900:]))
        finally:
            shutil.copyfile(backup, caminho)
            os.unlink(backup)
            assert io.open(caminho, encoding="utf-8").read() == original, \
                "restauracao falhou em " + relativo
    _p("\n  PLACAR DAS MUTACOES: %d vermelhas - %d verdes" % (vermelhas, verdes))
    return verdes == 0


def main():
    args = sys.argv[1:]
    if "--mutar" in args:
        i = args.index("--mutar")
        filtro = args[i + 1] if len(args) > i + 1 and args[i + 1].startswith("M-") else None
        return 0 if rodar_mutacoes(filtro) else 1

    so = args[args.index("--so") + 1] if "--so" in args else None
    if not so:
        _p("=" * 78)
        _p("  G1 G2 G4 G5 -- UMA RAJADA, UM TURNO  (SPEC-EXTRA-001.2 BLOCO AB)")
        _p("=" * 78)
    for gid, fn in GATES.items():
        if so and gid != so:
            continue
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            import traceback
            check("%s EXPLODIU (defeito do guarda ou do produto)" % gid, False,
                  "%s: %s\n%s" % (type(exc).__name__, exc, traceback.format_exc()[-900:]))
    if not so:
        _p("\n" + "=" * 78)
        _p("  %d assercoes verdes - %d vermelhas" % (PASS, FAIL))
        _p("=" * 78)
    return 1 if FAIL else 0


def test_uma_rajada_um_turno():
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
