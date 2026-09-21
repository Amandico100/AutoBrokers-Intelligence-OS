# -*- coding: utf-8 -*-
r"""A COSTURA — o disjuntor do provedor pergunta ANTES de consumir o buffer.
SPEC-EXTRA-001.8, FATIA 4 · §7.4 ("breaker aberto não vira silêncio") + §8.

🔴 **O defeito que só aparece na COSTURA.** As duas peças estavam certas
sozinhas e erradas juntas:

```
app/core/relogio_do_modelo.py   abre um breaker por PROVEDOR quando ele cai
app/tasks/buffer_processor.py   consome o buffer (`get_and_clear` APAGA a
                                rajada do Redis) e chama o atendimento
```

Sem a costura, o breaker aberto vira SILÊNCIO: o varredor apaga as cinco
mensagens do segurado do Redis, a chamada ao modelo falha na hora, e ninguém
responde — nem hoje, nem quando o provedor voltar. 🔴 A SPEC §7.4 é explícita:
*"Um breaker que faz o agente calar sem avisar é pior que timeout."*

O QUE ESTE ARQUIVO ATRAVESSA — a saída REAL de uma fatia como entrada da outra,
com o MOTOR dos DOIS lados e dublê só na borda:

```
registrar_falha (REAL, relogio_do_modelo)  ->  breaker ABERTO no Redis dublê
   ->  provedores_barrados (REAL)  ->  processar_buffers_prontos (REAL)
   ->  adiar/renovar_vida (REAL, message_buffer_service)
   ->  [DUBLÊ: aqui estariam o modelo e o WhatsApp]
```

⛔ SEGURANÇA: zero rede, zero banco, zero Redis de verdade, zero LLM, zero
envio. Escopos e telefones sintéticos, herdados do guarda vizinho; nenhum nome
de corretora entra como constante (CLAUDE.md §13.9).

Rodar (de dentro de `backend/`):
    PYTHONIOENCODING=utf-8 python tests/test_a_costura_do_isolamento.py
    ... --so 3     ·     ... --mutar     ·     ... --mutar M-C-1
    python -m pytest tests/test_a_costura_do_isolamento.py -q -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import io
import os
import shutil
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)                       # .../backend
for caminho in (RAIZ, AQUI):
    if caminho not in sys.path:
        sys.path.insert(0, caminho)
os.environ["SEM_REDE"] = "1"

BUFFER_PY = os.path.join(RAIZ, "app", "tasks", "buffer_processor.py")
ESTE = os.path.abspath(__file__)

# ⚠️ O guarda vizinho é REAPROVEITADO de propósito: o Redis dublê que honra TTL,
# o relógio controlável e o recorte por AST do varredor já existem e já são a
# LINHA DE BASE desta SPEC. Reescrevê-los aqui seria um segundo motor de teste,
# que é como dois guardas passam a discordar sobre o mesmo fato.
import test_uma_corretora_nao_trava_a_outra as V  # noqa: E402

PASS = 0
FAIL = 0


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
        _p("  [FALHOU] %s" % nome + ("\n         %s" % str(detalhe)[:900] if detalhe else ""))
    return bool(cond)


# ===========================================================================
# O DUBLÊ — o do vizinho, mais os três comandos que o BREAKER usa
# ===========================================================================
class Duble(V._RedisDuble):
    """`exists`, `incr` e `delete(*chaves)` — o que `relogio_do_modelo` chama.

    ⚠️ Um dublê que aceitasse qualquer chamada esconderia justamente o comando
    que faltasse. Estes três são os que o breaker usa, e nada mais.
    """

    async def exists(self, chave):
        return 1 if self._vivo(chave) is not None else 0

    async def incr(self, chave):
        atual = self._vivo(chave)
        novo = int(atual or 0) + 1
        vence = self.dados.get(chave, (None, None))[1] if atual is not None else None
        self.dados[chave] = (str(novo), vence)
        return novo

    async def delete(self, *chaves):
        return sum(1 for k in chaves if self.dados.pop(k, None) is not None)


class RedisQueLevanta:
    """O Redis CAÍDO — todo comando levanta. Não é um Redis vazio."""

    def __getattr__(self, _nome):
        async def _erro(*a, **k):
            raise ConnectionError("redis fora")
        return _erro


#: Provedores sintéticos, dos que `relogio_do_modelo.PROVEDORES` conhece.
#: ⚠️ Corretora A e corretora B usam provedores DIFERENTES — é o desenho inteiro
#: desta prova: o provedor de uma cair não pode calar a outra.
PROVEDOR_A = "anthropic"
PROVEDOR_B = "openai"


def _servico(duble):
    V.M.datetime = V._DataHoraDublada
    return V.M.MessageBufferService(duble)


def _relogio_do_modelo(duble):
    """Faz `relogio_do_modelo` falar com ESTE dublê (ou com um Redis caído)."""
    import app.core.redis as R

    async def _cliente():
        return duble
    R.get_async_redis_client = _cliente
    import app.core.relogio_do_modelo as RM
    RM._MEMORIA.clear()
    return RM


def _carregar():
    """O varredor REAL, recortado do fonte — com as peças NOVAS da costura."""
    nomes = list(V.NOMES_DO_VARREDOR) + [
        "provedores_barrados", "_provedor_da_chave",
        "_PROVEDOR_POR_ESCOPO", "_PROVEDOR_CACHE_PADRAO_S",
        # A segunda pergunta da varredura (conserto unico, 21/09/2026).
        "provedores_em_meio_aberto",
    ]
    return V.carregar_varredor(nomes)


def _resolvedor(mapa):
    """escopo -> provedor. É o ponto injetável: no produto quem resolve é
    `provedor_do_escopo` (integração -> agente de atendimento -> provedor)."""
    async def resolver(escopo):
        return mapa.get(escopo)
    return resolver


class Borda:
    """A BORDA: onde estariam o modelo e o WhatsApp. Só anota quem chegou."""

    def __init__(self):
        self.atendidas = []

    def __call__(self, payload_dict=None, **extras):
        self.atendidas.append(str((payload_dict or {}).get("_integration_id") or ""))

        async def _nada():
            return True
        return _nada()


async def _varrer(bp, servico, duble, processar, *, barrados, provedor_de,
                  meio_abertos=None, timeout_s=0):
    _cursor, chaves = await duble.scan(0, match="whatsapp_buffer:*")
    return await bp["processar_buffers_prontos"](
        chaves, servico, processar, barrados=barrados, provedor_de=provedor_de,
        meio_abertos=meio_abertos, timeout_s=timeout_s)


async def _abrir_o_disjuntor(RM, provedor):
    """Abre o breaker chamando a função REAL, com erro transitório de verdade."""
    for _ in range(RM.BREAKER_FALHAS):
        await RM.registrar_falha(provedor, asyncio.TimeoutError("o provedor sumiu"))
    return await RM.estado_do_breaker(provedor)


def _preparar():
    """Um cenário limpo: dublê, serviço real, varredor real, duas corretoras."""
    V.RELOGIO[0] = V.datetime(2026, 9, 21, 9, 0, 0)
    duble = Duble()
    RM = _relogio_do_modelo(duble)
    servico = _servico(duble)
    bp = _carregar()
    V._zerar_admissao(bp)
    return duble, RM, servico, bp


# ===========================================================================
# 1 + 2. O DISJUNTOR ABERTO RETÉM — E SÓ A CORRETORA DELE
# ===========================================================================
def caso_1_e_2():
    _p("\n=== 1+2. disjuntor aberto retem a conversa DELE, e so a dele ===")

    async def corpo():
        duble, RM, servico, bp = _preparar()
        await V._semear(servico, V.ESCOPO_A, 3, inicio=0)
        await V._semear(servico, V.ESCOPO_B, 3, inicio=50)
        V._andar(30)          # a rajada fecha (debounce) sem o TTL vencer

        estado = await _abrir_o_disjuntor(RM, PROVEDOR_A)
        check("o disjuntor do provedor da corretora A esta ABERTO (funcao REAL)",
              estado.get("estado") == "aberto", estado)
        check("CONTROLE: o disjuntor do provedor da corretora B esta FECHADO",
              (await RM.estado_do_breaker(PROVEDOR_B)).get("estado") == "fechado")

        borda = Borda()
        resumo = await _varrer(
            bp, servico, duble, borda,
            barrados=bp["provedores_barrados"],
            provedor_de=_resolvedor({V.ESCOPO_A: PROVEDOR_A,
                                     V.ESCOPO_B: PROVEDOR_B}))

        check("as 3 conversas da corretora A foram ADIADAS por 'breaker'",
              resumo["adiadas"]["breaker"] == 3, resumo)
        check("🔴 a borda NUNCA foi chamada para a corretora A "
              "(nada chegou ao segurado)",
              V.ESCOPO_A not in borda.atendidas, borda.atendidas)
        vivas = [k for k in (await duble.scan(0, match="whatsapp_buffer:*"))[1]
                 if V.M.escopo_da_chave(k) == V.ESCOPO_A]
        check("🔴 os 3 buffers da corretora A CONTINUAM no Redis", len(vivas) == 3,
              vivas)
        ttls = [await duble.ttl(k) for k in vivas]
        check("e com a vida RENOVADA (TTL de volta aos %ds)"
              % V.M.settings.BUFFER_TTL_SECONDS,
              all(t == V.M.settings.BUFFER_TTL_SECONDS for t in ttls), ttls)

        # 🔴 2. O TÍTULO DA SPEC, na MESMA varredura.
        check("🔴 a corretora B foi ATENDIDA na MESMA varredura (3 conversas)",
              borda.atendidas.count(V.ESCOPO_B) == 3, borda.atendidas)
        check("a conta fecha: entrada = processadas + adiadas",
              resumo["prontas"] == resumo["processadas"] + sum(resumo["adiadas"].values()),
              resumo)
        check("e ninguem expirou", resumo["expiradas"] == 0, resumo)

        # 5. O QUE A CENTRAL LE.
        contador = duble.hashes.get(V.M.MessageBufferService.chave_dos_contadores(V.ESCOPO_A), {})
        check("os contadores da corretora A dizem ultimo_motivo='breaker'",
              contador.get("ultimo_motivo") == "breaker", contador)
        check("e contam 3 conversas em espera", contador.get("em_espera") == "3",
              contador)

        # LINHA DE CONTROLE: o MESMO cenario com o disjuntor FECHADO.
        await RM.registrar_sucesso(PROVEDOR_A)
        borda2 = Borda()
        resumo2 = await _varrer(
            bp, servico, duble, borda2,
            barrados=bp["provedores_barrados"],
            provedor_de=_resolvedor({V.ESCOPO_A: PROVEDOR_A,
                                     V.ESCOPO_B: PROVEDOR_B}))
        check("CONTROLE: disjuntor fechado -> a corretora A e atendida",
              borda2.atendidas.count(V.ESCOPO_A) == 3, borda2.atendidas)
        check("CONTROLE: e ninguem mais e adiado por 'breaker'",
              resumo2["adiadas"]["breaker"] == 0, resumo2)

    asyncio.run(corpo())


# ===========================================================================
# 3. A MENSAGEM NÃO SE PERDE — ela espera o provedor voltar
# ===========================================================================
def caso_3():
    _p("\n=== 3. depois de T o disjuntor vai a meio-aberto e a conversa RETIDA "
       "e atendida ===")

    async def corpo():
        duble, RM, servico, bp = _preparar()
        await V._semear(servico, V.ESCOPO_A, 2, inicio=0)
        V._andar(30)
        await _abrir_o_disjuntor(RM, PROVEDOR_A)

        resolver = _resolvedor({V.ESCOPO_A: PROVEDOR_A})
        entrada = 2
        atendidas = 0
        adiadas = 0
        expiradas = 0
        voltas = 0
        # O produto varre a cada 1 s; aqui cada volta avança 30 s do relógio —
        # é o mesmo que 30 varreduras, com a mesma consequência para o TTL.
        while voltas < 8:
            voltas += 1
            borda = Borda()
            resumo = await _varrer(bp, servico, duble, borda,
                                   barrados=bp["provedores_barrados"],
                                   provedor_de=resolver)
            atendidas += resumo["processadas"]
            adiadas += resumo["adiadas"]["breaker"]
            expiradas += resumo["expiradas"]
            if resumo["processadas"]:
                break
            V._andar(30)

        estado = await RM.estado_do_breaker(PROVEDOR_A)
        check("o disjuntor chegou a meio-aberto sozinho, pelo relogio",
              estado.get("estado") == "meio_aberto", estado)
        check("🔴 a conversa RETIDA foi atendida quando o provedor voltou",
              atendidas == entrada, "atendidas=%d em %d voltas" % (atendidas, voltas))
        check("ela esperou de verdade (foi adiada antes de ser atendida)",
              adiadas >= 2, adiadas)
        check("🔴 ZERO expiradas do comeco ao fim — nenhuma mensagem se perdeu",
              expiradas == 0, expiradas)

    asyncio.run(corpo())


# ===========================================================================
# 4. REDIS FORA — ninguém é adiado por "breaker"
# ===========================================================================
def caso_4():
    _p("\n=== 4. Redis fora -> ninguem e retido (na duvida, ATENDE) ===")

    async def corpo():
        duble, RM, servico, bp = _preparar()
        await V._semear(servico, V.ESCOPO_A, 2, inicio=0)
        await V._semear(servico, V.ESCOPO_B, 2, inicio=50)
        V._andar(30)
        await _abrir_o_disjuntor(RM, PROVEDOR_A)

        # 🔴 Agora o Redis CAI para o relógio do modelo — o breaker fica cego.
        _relogio_do_modelo(RedisQueLevanta())
        barrados = await bp["provedores_barrados"]()
        check("sem Redis o disjuntor nao barra ninguem", barrados == set(), barrados)

        borda = Borda()
        resumo = await _varrer(
            bp, servico, duble, borda,
            barrados=bp["provedores_barrados"],
            provedor_de=_resolvedor({V.ESCOPO_A: PROVEDOR_A,
                                     V.ESCOPO_B: PROVEDOR_B}))
        check("🔴 ninguem foi adiado por 'breaker'",
              resumo["adiadas"]["breaker"] == 0, resumo)
        check("as duas corretoras foram atendidas (4 conversas)",
              resumo["processadas"] == 4, resumo)

        # 🔴 E a dúvida de DENTRO: `estado_do_breaker` levantando. O relógio do
        # modelo já é fail-open por conta própria (ele devolve "fechado"), então
        # sem este dublê a nossa própria rede de segurança nunca seria exercida
        # — e um guarda que não tem como ficar vermelho não guarda nada
        # (CLAUDE.md §9.3).
        import app.core.relogio_do_modelo as RM2
        original = RM2.estado_do_breaker

        async def estado_que_explode(_provedor):
            raise RuntimeError("breaker indisponivel")

        RM2.estado_do_breaker = estado_que_explode
        try:
            check("🔴 breaker que EXPLODE tambem nao barra ninguem",
                  (await bp["provedores_barrados"]()) == set())
        finally:
            RM2.estado_do_breaker = original

        # E a segunda dúvida: a própria consulta explodindo.
        async def explode():
            raise RuntimeError("consulta ao breaker falhou")

        await V._semear(servico, V.ESCOPO_A, 1, inicio=90)
        V._andar(30)
        borda2 = Borda()
        resumo2 = await _varrer(bp, servico, duble, borda2, barrados=explode,
                                provedor_de=_resolvedor({V.ESCOPO_A: PROVEDOR_A}))
        check("consulta ao disjuntor explodindo tambem NAO retem ninguem",
              resumo2["adiadas"]["breaker"] == 0 and resumo2["processadas"] == 1,
              resumo2)

        # E a terceira: o resolvedor de provedor falhando.
        async def resolver_quebrado(_escopo):
            raise RuntimeError("nao consegui falar com o banco")

        _relogio_do_modelo(duble)
        await V._semear(servico, V.ESCOPO_A, 1, inicio=95)
        V._andar(30)
        borda3 = Borda()
        resumo3 = await _varrer(bp, servico, duble, borda3,
                                barrados=bp["provedores_barrados"],
                                provedor_de=resolver_quebrado)
        check("resolvedor de provedor quebrado -> ATENDE (nunca retem as cegas)",
              resumo3["adiadas"]["breaker"] == 0 and resumo3["processadas"] == 1,
              resumo3)

    asyncio.run(corpo())


# ===========================================================================
# 5. O RESOLVEDOR NÃO VAI AO BANCO POR CHAVE POR VARREDURA
# ===========================================================================
def caso_5():
    _p("\n=== 5. o provedor e resolvido UMA vez por corretora, nao por chave ===")

    async def corpo():
        duble, RM, servico, bp = _preparar()
        await V._semear(servico, V.ESCOPO_A, 20, inicio=0)
        V._andar(30)
        await _abrir_o_disjuntor(RM, PROVEDOR_A)

        idas = []

        async def resolver(escopo):
            idas.append(escopo)
            return PROVEDOR_A

        borda = Borda()
        resumo = await _varrer(bp, servico, duble, borda,
                               barrados=bp["provedores_barrados"],
                               provedor_de=resolver)
        check("as 20 conversas foram retidas", resumo["adiadas"]["breaker"] == 20,
              resumo)
        check("🔴 mas o provedor foi resolvido UMA vez (cache de escopo)",
              len(idas) == 1, idas)

        # Segunda varredura, dentro da janela do cache: nenhuma ida nova.
        await _varrer(bp, servico, duble, Borda(),
                      barrados=bp["provedores_barrados"], provedor_de=resolver)
        check("e a varredura seguinte nao voltou ao banco", len(idas) == 1, idas)

        # E sem disjuntor aberto, o resolvedor nem e chamado: custo ZERO no dia
        # normal, que e o desenho da opcao (ii).
        await RM.registrar_sucesso(PROVEDOR_A)
        bp["_PROVEDOR_POR_ESCOPO"].clear()
        await _varrer(bp, servico, duble, Borda(),
                      barrados=bp["provedores_barrados"], provedor_de=resolver)
        check("CONTROLE: disjuntor fechado -> ZERO resolucao de provedor",
              len(idas) == 1, idas)

    asyncio.run(corpo())


async def _envelhecer_tudo(duble, servico):
    """Renova o TTL de TODAS as chaves de buffer sem mexer no relogio global.

    ⚠️ O produto faz isso sozinho (`adiar` -> `renovar_vida` a cada varredura);
    aqui ele serve para o cenario poder ANDAR os 120 s que o disjuntor precisa
    para ir a meio-aberto sem que o TTL de 60 s do buffer coma a rajada antes.
    """
    _c, chaves = await duble.scan(0, match="whatsapp_buffer:*")
    for chave in list(chaves):
        await V._envelhecer(servico, chave, ocioso_s=30, idade_s=30)


async def _ate_o_meio_aberto(duble, servico, RM, provedor):
    """Anda o relogio ate o disjuntor ir sozinho a MEIO-ABERTO, sem perder buffer."""
    for _ in range(10):
        estado = await RM.estado_do_breaker(provedor)
        if estado.get("estado") == "meio_aberto":
            return estado
        # ⚠️ RENOVAR ANTES DE ANDAR: o TTL do buffer é de 60 s e o relógio anda
        # 40 s por volta. Renovar depois seria renovar o que já morreu.
        await _envelhecer_tudo(duble, servico)
        V._andar(40)
    return await RM.estado_do_breaker(provedor)


# ===========================================================================
# 6. A INEQUAÇÃO — o teto do TURNO é maior que o pior caso de UMA chamada
# ===========================================================================
#
# 🔴 O DEFEITO, medido em 21/09/2026 (`juiz/medir.py` M4):
#
#     LLM_TIMEOUT_SEGUNDOS 90 s x (LLM_MAX_RETRIES 2 + 1) = 270 s por chamada
#     WHATSAPP_TURNO_TIMEOUT_S ....................... =  180 s
#     270 > 180  ->  o teto do turno corta ANTES de o modelo desistir
#
# E cortar antes não é "cortar mais cedo": o corte é `CancelledError`, que NÃO é
# `Exception` — nenhum `except` do webhook rodava, a rajada já tinha saído do
# Redis, e o segurado ficava em SILÊNCIO definitivo.
#
# ⛔ OS NÚMEROS SÃO LIDOS DOS DOIS MÓDULOS, NUNCA REESCRITOS AQUI. Reescrever o
# 90 e o 300 neste arquivo é como a inequação passaria a valer sobre outra
# coisa no dia em que um dos dois mudasse (CLAUDE.md §5, §9.4).
def caso_6():
    _p("\n=== 6. o teto do TURNO > pior caso de UMA chamada (a inequacao) ===")
    bp = _carregar()
    import app.core.relogio_do_modelo as RM

    teto_do_turno = float(bp["_env_int"]("WHATSAPP_TURNO_TIMEOUT_S",
                                         bp["_TURNO_TIMEOUT_PADRAO_S"]))
    pior_caso = float(RM.TIMEOUT_S) * (int(RM.MAX_RETRIES) + 1)
    _p("      📊 LLM_TIMEOUT_SEGUNDOS=%s x (LLM_MAX_RETRIES=%s + 1) = %.0f s"
       % (RM.TIMEOUT_S, RM.MAX_RETRIES, pior_caso))
    _p("      📊 WHATSAPP_TURNO_TIMEOUT_S = %.0f s" % teto_do_turno)

    check("🔴 o teto do TURNO (%.0f s) e MAIOR que o pior caso de UMA chamada "
          "(%.0f s)" % (teto_do_turno, pior_caso),
          pior_caso < teto_do_turno,
          "com o teto menor, `wait_for` corta com CancelledError antes de o SDK "
          "desistir: nenhum `except Exception` roda, a rajada ja saiu do Redis "
          "e o segurado nao ouve nem a resposta nem a desculpa honesta")
    check("e os dois numeros foram LIDOS dos modulos, nao escritos aqui",
          bp["_TURNO_TIMEOUT_PADRAO_S"] == teto_do_turno
          and isinstance(RM.TIMEOUT_S, float),
          "teto=%s TIMEOUT_S=%s" % (bp["_TURNO_TIMEOUT_PADRAO_S"], RM.TIMEOUT_S))

    # 🔴 LINHA DE CONTROLE: a inequacao CONSEGUE ser falsa. Sem ela, um guarda
    # que sempre compara dois numeros quaisquer nao guarda nada (§9.3).
    check("CONTROLE: com o teto de 180 s (o valor de antes) a MESMA conta falha",
          not (pior_caso < 180.0),
          "se 180 tambem passasse, a comparacao nao estaria medindo nada")


# ===========================================================================
# 7. O PROVEDOR PENDURADO ABRE O DISJUNTOR — e as proximas ficam RETIDAS
# ===========================================================================
def caso_7():
    _p("\n=== 7. N turnos cortados pelo teto -> o disjuntor ABRE -> as "
       "proximas conversas ficam GUARDADAS ===")

    async def corpo():
        duble, RM, servico, bp = _preparar()
        resolver = _resolvedor({V.ESCOPO_A: PROVEDOR_A})
        n = RM.BREAKER_FALHAS

        async def pendura(payload_dict=None, **kw):
            """O provedor PENDURADO: a chamada nunca volta."""
            await asyncio.sleep(3600)

        estado_inicial = await RM.estado_do_breaker(PROVEDOR_A)
        check("o disjuntor comeca FECHADO", estado_inicial.get("estado") == "fechado",
              estado_inicial)

        cortados = 0
        for volta in range(n):
            (chave,) = await V._semear(servico, V.ESCOPO_A, 1, inicio=200 + volta)
            # ⚠️ O carimbo envelhece, o RELOGIO NAO anda: a janela do breaker
            # e de 60 s (`LLM_BREAKER_JANELA_SEGUNDOS`), e andar 30 s por volta
            # zeraria o contador de falhas no meio da medicao — o guarda ficaria
            # verde por engano, medindo outra coisa.
            await V._envelhecer(servico, chave, ocioso_s=30, idade_s=30)
            r = await _varrer(bp, servico, duble, pendura,
                              barrados=bp["provedores_barrados"],
                              provedor_de=resolver, timeout_s=0.05)
            cortados += r["timeouts"]

        estado = await RM.estado_do_breaker(PROVEDOR_A)
        check("os %d turnos foram cortados pelo teto" % n, cortados == n,
              "cortados=%d" % cortados)
        check("🔴 e o disjuntor do provedor ABRIU — o teto de turno conta como "
              "falha DELE", estado.get("estado") == "aberto", estado)

        # E agora a conversa SEGUINTE fica retida, com o buffer intacto.
        (chave_seguinte,) = await V._semear(servico, V.ESCOPO_A, 1, inicio=300)
        await V._envelhecer(servico, chave_seguinte, ocioso_s=30, idade_s=30)
        borda = Borda()
        r = await _varrer(bp, servico, duble, borda,
                          barrados=bp["provedores_barrados"],
                          provedor_de=resolver, timeout_s=0.05)
        vivas = [k for k in (await duble.scan(0, match="whatsapp_buffer:*"))[1]
                 if V.M.escopo_da_chave(k) == V.ESCOPO_A]
        check("🔴 a conversa seguinte foi ADIADA por 'breaker', nao consumida",
              r["adiadas"]["breaker"] == 1 and r["processadas"] == 0, r)
        check("🔴 e o buffer dela CONTINUA no Redis (a rajada nao se perdeu)",
              len(vivas) >= 1, vivas)
        check("ninguem expirou em nenhuma das voltas", r["expiradas"] == 0, r)

        # 🔴 LINHA DE CONTROLE: sem os cortes, o disjuntor nao abre sozinho.
        duble2, RM2, servico2, bp2 = _preparar()
        (chave_c,) = await V._semear(servico2, V.ESCOPO_A, 1, inicio=400)
        await V._envelhecer(servico2, chave_c, ocioso_s=30, idade_s=30)
        borda2 = Borda()
        r2 = await _varrer(bp2, servico2, duble2, borda2,
                           barrados=bp2["provedores_barrados"],
                           provedor_de=_resolvedor({V.ESCOPO_A: PROVEDOR_A}),
                           timeout_s=5)
        check("CONTROLE: sem turno cortado o disjuntor fica FECHADO e a "
              "conversa e ATENDIDA",
              (await RM2.estado_do_breaker(PROVEDOR_A)).get("estado") == "fechado"
              and r2["processadas"] == 1, r2)

    asyncio.run(corpo())


# ===========================================================================
# 8. MEIO-ABERTO: PASSA **UMA**, E SÓ UMA (§7.4)
# ===========================================================================
def caso_8():
    _p("\n=== 8. meio-aberto -> UMA sonda passa, as outras ficam guardadas ===")

    async def corpo():
        duble, RM, servico, bp = _preparar()
        resolver = _resolvedor({V.ESCOPO_A: PROVEDOR_A})
        await V._semear(servico, V.ESCOPO_A, 8, inicio=0)
        V._andar(30)
        await _abrir_o_disjuntor(RM, PROVEDOR_A)
        # O relogio anda ate o `aberto` vencer: o breaker vai sozinho a
        # meio-aberto, que e o instante que o §7.4 descreve.
        estado = await _ate_o_meio_aberto(duble, servico, RM, PROVEDOR_A)
        check("o disjuntor esta em MEIO-ABERTO", estado.get("estado") == "meio_aberto",
              estado)

        borda = Borda()
        r1 = await _varrer(bp, servico, duble, borda,
                           barrados=bp["provedores_barrados"],
                           provedor_de=resolver,
                           meio_abertos=bp["provedores_em_meio_aberto"])
        check("🔴 EXATAMENTE UMA conversa passou (a sonda)",
              r1["processadas"] == 1, r1)
        check("🔴 e as outras 7 ficaram GUARDADAS por 'breaker' — nao consumidas",
              r1["adiadas"]["breaker"] == 7, r1)
        check("nenhuma expirou", r1["expiradas"] == 0, r1)
        vivas = [k for k in (await duble.scan(0, match="whatsapp_buffer:*"))[1]
                 if V.M.escopo_da_chave(k) == V.ESCOPO_A]
        check("os 7 buffers continuam no Redis", len(vivas) == 7, len(vivas))

        # A SONDA DEU CERTO -> o provedor volta -> as 7 passam na volta seguinte.
        await RM.registrar_sucesso(PROVEDOR_A)
        borda2 = Borda()
        r2 = await _varrer(bp, servico, duble, borda2,
                           barrados=bp["provedores_barrados"],
                           provedor_de=resolver,
                           meio_abertos=bp["provedores_em_meio_aberto"])
        check("🔴 sonda com sucesso -> o disjuntor fecha e as 7 sao atendidas",
              r2["processadas"] == 7, r2)
        check("e ninguem sumiu do comeco ao fim",
              r1["expiradas"] == 0 and r2["expiradas"] == 0,
              "%s / %s" % (r1["expiradas"], r2["expiradas"]))

        # A SONDA FALHOU -> o breaker REABRE -> ninguem se perde.
        duble3, RM3, servico3, bp3 = _preparar()
        resolver3 = _resolvedor({V.ESCOPO_A: PROVEDOR_A})
        await V._semear(servico3, V.ESCOPO_A, 4, inicio=500)
        V._andar(30)
        await _abrir_o_disjuntor(RM3, PROVEDOR_A)
        await _ate_o_meio_aberto(duble3, servico3, RM3, PROVEDOR_A)

        async def explode(payload_dict=None, **kw):
            raise asyncio.TimeoutError("o provedor continua fora")

        r3 = await _varrer(bp3, servico3, duble3, explode,
                           barrados=bp3["provedores_barrados"],
                           provedor_de=resolver3,
                           meio_abertos=bp3["provedores_em_meio_aberto"])
        await RM3.registrar_falha(PROVEDOR_A, asyncio.TimeoutError("sonda falhou"))
        check("a sonda que FALHA reabre o disjuntor",
              (await RM3.estado_do_breaker(PROVEDOR_A)).get("estado") == "aberto")
        check("🔴 e ninguem sumiu (`expiradas == 0`)", r3["expiradas"] == 0, r3)

        # 🔴 LINHA DE CONTROLE: sem a pergunta do meio-aberto, o MESMO cenario
        # solta TODAS de uma vez. E o que o produto fazia ate 21/09/2026.
        duble4, RM4, servico4, bp4 = _preparar()
        await V._semear(servico4, V.ESCOPO_A, 8, inicio=600)
        V._andar(30)
        await _abrir_o_disjuntor(RM4, PROVEDOR_A)
        await _ate_o_meio_aberto(duble4, servico4, RM4, PROVEDOR_A)
        r4 = await _varrer(bp4, servico4, duble4, Borda(),
                           barrados=bp4["provedores_barrados"],
                           provedor_de=_resolvedor({V.ESCOPO_A: PROVEDOR_A}),
                           meio_abertos=None)
        check("CONTROLE: sem a pergunta do meio-aberto, as 8 passam de uma vez",
              r4["processadas"] == 8,
              "deu %s — se este numero nao fosse 8, o merito do caso acima "
              "iria para o lugar errado (CLAUDE.md §9.2)" % r4["processadas"])

    asyncio.run(corpo())


# ===========================================================================
# INFRAESTRUTURA — mutações
# ===========================================================================
CASOS = {"1": caso_1_e_2, "3": caso_3, "4": caso_4, "5": caso_5,
         "6": caso_6, "7": caso_7, "8": caso_8}

# ⚠️ ÂNCORA ATUALIZADA em 21/09/2026 (conserto único): os quatro pontos de
# adiamento passaram a chamar `_guardar`, que adia E anota o DONO da espera na
# mesma linha. A mutação continua sendo a MESMA ideia — perguntar ao disjuntor
# DEPOIS do `get_and_clear` —, só que sobre o texto de hoje.
_BLOCO = """            if com_cota and provedores_fora and provedor_de is not None:
                provedor = await _provedor_da_chave(provedor_de, escopo)
                if provedor and provedor in provedores_fora:
                    # ⚠️ Sem PII: nem chave, nem telefone, nem corretora.
                    logger.info("[ISOLAMENTO] conversa guardada: disjuntor "
                                "aberto no provedor %s", provedor)
                    return await _guardar(chave, escopo, "breaker")
"""

_DEPOIS_DO_CONSUMO = """                        combined_msg = buffer_service.get_combined_message(buffer)
                        if com_cota and provedores_fora and provedor_de is not None:
                            provedor = await _provedor_da_chave(provedor_de, escopo)
                            if provedor and provedor in provedores_fora:
                                return await _guardar(chave, escopo, "breaker")
"""

#: (descrição, [(arquivo, velho, novo)], casos que TÊM de ficar vermelhos)
MUTACOES = {
    "M-C-1": ("consultar o disjuntor DEPOIS do get_and_clear",
              [(BUFFER_PY, _BLOCO, ""),
               (BUFFER_PY,
                "                        combined_msg = buffer_service.get_combined_message(buffer)\n",
                _DEPOIS_DO_CONSUMO)],
              ["1"]),
    "M-C-2": ("fail-closed na duvida (breaker indisponivel barra o provedor)",
              [(BUFFER_PY,
                """        except Exception as erro:  # noqa: BLE001
            # ⛔ FAIL-OPEN: breaker indisponível nunca retém ninguém.
            logger.debug("[ISOLAMENTO] breaker indisponivel (%s)",
                         type(erro).__name__)
            continue""",
                """        except Exception as erro:  # noqa: BLE001
            barrados.add(provedor)
            continue""")],
              ["4"]),
    "M-C-3": ("disjuntor por PROCESSO inteiro, e nao por provedor",
              [(BUFFER_PY,
                "                if provedor and provedor in provedores_fora:",
                "                if provedores_fora:")],
              ["1"]),
    "M-C-4": ("o cache de provedor deixa de existir (uma ida por chave)",
              [(BUFFER_PY,
                "    if guardado is not None and guardado[1] > agora:",
                "    if False:")],
              ["5"]),
    # === AS TRÊS DO CONSERTO ÚNICO (21/09/2026) ===========================
    "M-C-5": ("o teto do turno volta a 180 s (menor que 90 x 3 = 270)",
              [(BUFFER_PY,
                "_TURNO_TIMEOUT_PADRAO_S = 300",
                "_TURNO_TIMEOUT_PADRAO_S = 180  # MUTACAO")],
              ["6"]),
    "M-C-6": ("a sonda do meio-aberto deixa de ser gastada (passam todas)",
              [(BUFFER_PY,
                "                    if not await _sonda_do_meio_aberto(provedor):",
                "                    if False:  # MUTACAO")],
              ["8"]),
    "M-C-7": ("o teto de turno deixa de contar falha do provedor pendurado",
              [(BUFFER_PY,
                """                                await _contar_timeout_no_breaker(
                                    provedor_de, escopo, teto_turno)""",
                "                                pass  # MUTACAO")],
              ["7"]),
}


def _mutar(nome):
    descricao, trocas, casos = MUTACOES[nome]
    backups = []
    try:
        for arquivo, velho, novo in trocas:
            fonte = io.open(arquivo, encoding="utf-8").read()
            if velho not in fonte:
                _p("[%s] ALVO NAO ENCONTRADO — a mutacao precisa ser atualizada:\n%s"
                   % (nome, velho[:120]))
                return 1
            backup = arquivo + ".backup_mutacao_costura"
            if arquivo not in [b[0] for b in backups]:
                shutil.copyfile(arquivo, backup)
                backups.append((arquivo, backup))
            io.open(arquivo, "w", encoding="utf-8").write(
                fonte.replace(velho, novo, 1))
        ruim = 0
        for caso in casos:
            proc = subprocess.run([sys.executable, ESTE, "--so", caso], cwd=RAIZ,
                                  capture_output=True, text=True, encoding="utf-8",
                                  errors="replace", timeout=900)
            vermelho = proc.returncode != 0
            _p("[%s] %s -> caso %s: %s" % (
                nome, descricao, caso,
                "VERMELHO ✅" if vermelho else "VERDE ❌ (o guarda e carimbo)"))
            if not vermelho:
                ruim = 1
                _p((proc.stdout or "")[-1200:])
        return ruim
    finally:
        for arquivo, backup in backups:
            shutil.copyfile(backup, arquivo)     # 🔴 restaura por CÓPIA
            os.remove(backup)


def principal(argv):
    global FAIL
    if "--mutar" in argv:
        pos = argv.index("--mutar")
        nomes = [argv[pos + 1]] if len(argv) > pos + 1 and not argv[pos + 1].startswith("--") \
            else sorted(MUTACOES)
        return 1 if sum(_mutar(n) for n in nomes) else 0

    escolhidos = [argv[argv.index("--so") + 1]] if "--so" in argv else list(CASOS)
    for nome in escolhidos:
        try:
            CASOS[nome]()
        except Exception as exc:  # noqa: BLE001
            import traceback
            check("o caso %s EXPLODIU" % nome, False,
                  "%s: %s\n%s" % (type(exc).__name__, exc,
                                  traceback.format_exc()[-1200:]))
    _p("\n%s\nRESUMO: %d ok, %d falhas\n%s" % ("=" * 60, PASS, FAIL, "=" * 60))
    return 1 if FAIL else 0


def test_a_costura_do_isolamento():
    """Ponte para o pytest — o mesmo caminho do script."""
    assert principal([]) == 0, "%d assercoes falharam" % FAIL


if __name__ == "__main__":
    sys.exit(principal(sys.argv[1:]))
