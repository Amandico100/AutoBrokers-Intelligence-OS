"""O número da corretora não é nosso para queimar.

O defeito, medido em 02/08/2026
-------------------------------
📊 Busca por controle de vazão no repositório inteiro::

    rg "rate.?limit|throttle|governor|vazao" backend/app/ ....  0 resultados úteis
    único espaçamento existente ............................  _dormir(0.7)
                                                              entre balões da MESMA mensagem

📊 `billing_collection._send_test_messages`, antes deste bloco::

    for item in items[: cfg["max_boletos_por_execucao"]]:   # limite 50
        send_message(...)                                   # 1
        send_document(...)                                  # 2

    50 itens x 2 mensagens = 100 mensagens em rajada, sem uma pausa,
    saindo do WhatsApp DA CORRETORA.

Um número novo que dispara 100 mensagens seguidas é banido. Quem perde o canal
é a corretora — o número que os segurados dela têm salvo na agenda. O prejuízo
não cai na plataforma; cai em quem confiou nela.

📊 `delivery_executor._whatsapp` já dizia isso em voz alta desde a SPEC-064:
tentava `from app.services.whatsapp import outbound_governor` e, no `except`,
devolvia *"governador de envio ainda não existe — o briefing não sai por
WhatsApp até a SPEC-063 Bloco C"*. Uma guarda por IMPORT, não por flag: flag
alguém liga por engano.

O que este teste prova
----------------------
G1  o intervalo é sorteado entre 4 e 8 min e **nunca cai em minuto redondo**
G2  a janela é 08:00–20:00 no fuso da corretora, e **domingo é bloqueado**
G3  os tetos param: 12/hora, 20/dia em número novo, 200 em maduro
G4  "maduro" exige tempo **E** volume — cada um sozinho mente
G5  a parada de emergência é por corretora e **não derruba as vizinhas**
G6  **mensagem quente nunca é atrasada** — o segurado está esperando
G7  Redis mudo não vira permissão: mensagem fria falha FECHADA
G8  o governador estende a fila que já existia (CLAUDE.md §5)
G9  a rajada de 100 do `billing_collection` passou a perguntar antes
G10 `delivery_executor` foi destravado sem perder a guarda por import

As provas de G1–G7 são FUNCIONAIS: chamam a função de decisão com relógios e
contadores de mentira. Um teste que só procura string no arquivo prova que
alguém digitou a palavra, não que o sistema decide certo.
"""

from __future__ import annotations

import importlib.util
import io
import os
import sys
import types
from datetime import datetime, timedelta, timezone

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKEND = os.path.join(RAIZ, "backend")
FALHAS: list[str] = []


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def _ler(*p: str) -> str:
    with io.open(os.path.join(RAIZ, *p), encoding="utf-8") as fh:
        return fh.read()


def _sem_comentario(f: str) -> str:
    return "\n".join(l for l in f.split("\n") if not l.lstrip().startswith("#"))


# ---------------------------------------------------------------------------
# O módulo, carregado com o mundo de fora todo falso.
# ---------------------------------------------------------------------------

class _Resultado:
    def __init__(self, data=None, count=None):
        self.data = data or []
        self.count = count


class _Tabela:
    def __init__(self, banco, nome):
        self.banco, self.nome = banco, nome
        self._eq, self._gte, self._contar = [], [], False

    def select(self, *_a, **kw):
        self._contar = kw.get("count") == "exact"
        return self

    def insert(self, payload):
        self.banco.dados.setdefault(self.nome, []).append(dict(payload))
        return self

    def eq(self, col, val):
        self._eq.append((col, val))
        return self

    def gte(self, col, val):
        self._gte.append((col, val))
        return self

    def neq(self, *_a):
        return self

    def order(self, col, desc=False):
        self._ordem = (col, desc)
        return self

    def limit(self, *_a):
        return self

    def execute(self):
        if self.banco.explodir:
            raise RuntimeError("banco fora do ar")
        linhas = list(self.banco.dados.get(self.nome, []))
        for col, val in self._eq:
            linhas = [r for r in linhas if str(r.get(col)) == str(val)]
        for col, val in self._gte:
            linhas = [r for r in linhas if str(r.get(col) or "") >= str(val)]
        ordem = getattr(self, "_ordem", None)
        if ordem:
            linhas.sort(key=lambda r: str(r.get(ordem[0]) or ""), reverse=bool(ordem[1]))
        return _Resultado(linhas, count=len(linhas) if self._contar else None)


class _Banco:
    def __init__(self):
        self.dados: dict = {}
        self.explodir = False
        self.client = self

    def table(self, nome):
        return _Tabela(self, nome)


class _Redis:
    """Redis de mentira com `nx`, `ttl` e `delete` — o mínimo que o gate usa."""

    def __init__(self):
        self.kv: dict = {}
        self.expira: dict = {}
        self.listas: dict = {}
        self.mudo = False

    def _checar(self):
        if self.mudo:
            raise RuntimeError("redis fora do ar")

    async def get(self, k):
        self._checar()
        return self.kv.get(k)

    async def set(self, k, v, ex=None, nx=False):
        self._checar()
        if nx and k in self.kv:
            return None
        self.kv[k] = v
        if ex:
            self.expira[k] = int(ex)
        return True

    async def ttl(self, k):
        self._checar()
        return self.expira.get(k, -1)

    async def delete(self, k):
        self._checar()
        self.kv.pop(k, None)
        self.expira.pop(k, None)
        return 1

    async def rpush(self, k, v):
        self._checar()
        self.listas.setdefault(k, []).append(v)
        return len(self.listas[k])

    async def lpop(self, k):
        self._checar()
        lst = self.listas.get(k) or []
        return lst.pop(0) if lst else None

    async def llen(self, k):
        self._checar()
        return len(self.listas.get(k) or [])


def montar(agora=None):
    """Carrega `platform_outbound` com banco, Redis e RELÓGIO falsos.

    O relógio não é luxo. A primeira versão deste teste consultava
    `datetime.now` de verdade: passou às 14:00 e reprovou às 01:12 com sete
    erros — porque janela e domingo são decisões sobre HORAS. Um teste de
    horário que lê o relógio da máquina só é verde no turno certo, e um teste
    que só é verde no turno certo não prova nada às 3 da manhã, que é
    exatamente quando o defeito importa.
    """
    banco, redis = _Banco(), _Redis()
    for nome in ("app", "app.core", "app.services", "app.services.atlas"):
        m = sys.modules.setdefault(nome, types.ModuleType(nome))
        m.__path__ = []

    db = types.ModuleType("app.core.database")
    db.get_supabase_client = lambda: banco
    sys.modules["app.core.database"] = db

    red = types.ModuleType("app.core.redis")

    async def _cliente():
        if redis.mudo:
            raise RuntimeError("redis fora do ar")
        return redis

    red.get_async_redis_client = _cliente
    sys.modules["app.core.redis"] = red

    obs = types.ModuleType("app.services.atlas.observer_intake")
    obs._br_variants = lambda p: {"".join(c for c in str(p) if c.isdigit())}
    sys.modules["app.services.atlas.observer_intake"] = obs

    # 🔴 O AGENTE DE ATENDIMENTO LIGADO, porque este teste é sobre VAZÃO.
    #
    # SPEC-078 A.1: `send_to_client_guarded` passou a ler o interruptor
    # (`agents.is_active` do papel `attendance`) antes de qualquer outra coisa —
    # era a única porta automática, periódica e endereçada a segurado que não o
    # consultava. Sem este dublê, os 4 envios deste teste são recusados com
    # `agente_desligado` e o arquivo inteiro fica vermelho pelo motivo errado.
    #
    # CLAUDE.md §9.3: quando o fato muda, o teste muda com ele. Este continua
    # provando o que sempre provou — espaçamento, tetos, janela, fila. Quem
    # prova o guarda NOVO, com linha de controle, é
    # `test_spec078_bloco_a_seguranca.py`.
    cap = types.ModuleType("app.services.atlas.attendance_capture")

    async def _agente_ligado(_c):
        return True

    cap.attendance_agent_active = _agente_ligado
    sys.modules["app.services.atlas.attendance_capture"] = cap

    dr = types.ModuleType("app.services.dispatch_router")

    async def _sem_acionamento(_c):
        return []

    dr.list_active_dispatches = _sem_acionamento
    sys.modules["app.services.dispatch_router"] = dr

    act = types.ModuleType("app.services.activity_log")
    act.registrado = []

    async def _log(company_id, categoria, titulo, detalhe=""):
        act.registrado.append({"company_id": company_id, "titulo": titulo})

    act.log_activity = _log
    sys.modules["app.services.activity_log"] = act

    integ = types.ModuleType("app.services.integration_service")

    class _IS:
        def get_platform_whatsapp_integration(self, _c):
            return {"id": "canal-1"}

    integ.get_integration_service = lambda: _IS()
    sys.modules["app.services.integration_service"] = integ

    wa = types.ModuleType("app.services.whatsapp_service")
    wa.enviados = []

    class _WA:
        def send_message(self, numero, texto, _integ):
            wa.enviados.append({"para": numero, "texto": texto})
            return True

    wa.get_whatsapp_service = lambda: _WA()
    sys.modules["app.services.whatsapp_service"] = wa

    caminho = os.path.join(BACKEND, "app", "services", "platform_outbound.py")
    spec = importlib.util.spec_from_file_location("app.services.platform_outbound", caminho)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["app.services.platform_outbound"] = mod
    spec.loader.exec_module(mod)
    if agora is not None:
        mod._agora = lambda: agora
    return mod, banco, redis, wa, act


def rodar(coro):
    import asyncio

    return asyncio.run(coro)


# ---------------------------------------------------------------------------

# Uma terça-feira às 10:00 em São Paulo (13:00 UTC) — dentro da janela.
TERCA_10H = datetime(2026, 8, 4, 13, 0, tzinfo=timezone.utc)
# Domingo às 10:00 em São Paulo.
DOMINGO_10H = datetime(2026, 8, 2, 13, 0, tzinfo=timezone.utc)
# Terça às 21:00 em São Paulo (00:00 UTC de quarta) — fora da janela.
TERCA_21H = datetime(2026, 8, 5, 0, 0, tzinfo=timezone.utc)
# Terça às 07:30 em São Paulo — antes de abrir.
TERCA_0730 = datetime(2026, 8, 4, 10, 30, tzinfo=timezone.utc)


def teste_o_intervalo_nao_bate_no_minuto_cheio():
    print("\n[G1] O espaçamento é 4–8 min, e o segundo nunca é redondo")
    po, *_ = montar()

    amostras = [po.intervalo_entre_frias() for _ in range(4000)]
    checar(all(240 < s < 480 for s in amostras),
           "todo intervalo cai entre 4 e 8 minutos, exclusivo",
           f"min={min(amostras)} max={max(amostras)}")
    redondos = [s for s in amostras if s % 30 == 0]
    checar(not redondos,
           "nenhum intervalo cai em múltiplo de 30 segundos",
           f"{len(redondos)} redondos, ex.: {redondos[:5]} — "
           "mensagens a cada 5:00 cravados são assinatura de robô")
    checar(len(set(amostras)) > 150,
           "os valores são realmente variados",
           f"só {len(set(amostras))} valores distintos em 4000 sorteios")

    # E o ajuste não pode empurrar para fora do teto.
    checar(po.intervalo_entre_frias(sorteio=lambda a, b: 450) == 457,
           "um sorteio redondo é corrigido sem estourar o teto",
           f"450 -> {po.intervalo_entre_frias(sorteio=lambda a, b: 450)}")
    checar(po.intervalo_entre_frias(sorteio=lambda a, b: 9999) <= 479,
           "sorteio absurdo é grampeado no teto")


def teste_a_janela_fecha_de_noite_e_no_domingo():
    print("\n[G2] 08:00–20:00 no fuso da corretora, domingo bloqueado")
    po, *_ = montar()

    dentro = po.dentro_da_janela(TERCA_10H)
    checar(dentro.pode, "terça 10:00 está dentro", dentro.motivo)

    noite = po.dentro_da_janela(TERCA_21H)
    checar(not noite.pode and noite.esperar_s > 0,
           "terça 21:00 está fora, e diz em quanto tempo reabre",
           f"{noite.motivo} / esperar={noite.esperar_s}")

    cedo = po.dentro_da_janela(TERCA_0730)
    checar(not cedo.pode, "terça 07:30 ainda não abriu", cedo.motivo)
    checar(1500 < cedo.esperar_s < 1900,
           "às 07:30 faltam ~30 min para abrir",
           f"esperar={cedo.esperar_s}s")

    domingo = po.dentro_da_janela(DOMINGO_10H)
    checar(not domingo.pode and "domingo" in domingo.motivo.lower(),
           "domingo 10:00 é bloqueado mesmo em horário comercial",
           domingo.motivo)

    # E a reabertura pula o domingo inteiro, em vez de cair nele.
    abertura = po.proxima_abertura(datetime(2026, 8, 1, 23, 0, tzinfo=timezone.utc))
    local = abertura.astimezone(po.fuso_da_corretora())
    checar(local.weekday() != 6 and local.hour == 8,
           "sábado à noite reabre na SEGUNDA às 08:00, não no domingo",
           f"reabre em {local.isoformat()}")

    # A borda: 20:00 cravado já é fora.
    vinte = datetime(2026, 8, 4, 23, 0, tzinfo=timezone.utc)  # 20:00 em SP
    checar(not po.dentro_da_janela(vinte).pode,
           "20:00 cravado já está fora — o fim é exclusivo")
    oito = datetime(2026, 8, 4, 11, 0, tzinfo=timezone.utc)  # 08:00 em SP
    checar(po.dentro_da_janela(oito).pode,
           "08:00 cravado já está dentro — o início é inclusivo")


def teste_os_tetos_param_de_verdade():
    print("\n[G3] 12 por hora · 20 por dia (novo) · 200 (maduro)")
    po, *_ = montar()

    livre = po.avaliar_vazao(agora_utc=TERCA_10H, na_hora=0, no_dia=0, maturidade="novo")
    checar(livre.pode, "canal zerado, dentro da janela: passa", livre.motivo)

    hora = po.avaliar_vazao(agora_utc=TERCA_10H, na_hora=12, no_dia=0, maturidade="novo")
    checar(not hora.pode and "hora" in hora.motivo,
           "a 12ª mensagem da hora fecha o portão", hora.motivo)
    checar(3000 < hora.esperar_s <= 3600,
           "e a espera vai até a virada da hora (10:00 -> 11:00)",
           f"esperar={hora.esperar_s}s")

    onze = po.avaliar_vazao(agora_utc=TERCA_10H, na_hora=11, no_dia=0, maturidade="novo")
    checar(onze.pode, "com 11 na hora ainda cabe uma", onze.motivo)

    dia_novo = po.avaliar_vazao(agora_utc=TERCA_10H, na_hora=0, no_dia=20, maturidade="novo")
    checar(not dia_novo.pode and "20" in dia_novo.motivo,
           "número novo para no 20º do dia", dia_novo.motivo)

    dia_maduro = po.avaliar_vazao(agora_utc=TERCA_10H, na_hora=0, no_dia=20, maturidade="maduro")
    checar(dia_maduro.pode,
           "o mesmo 20º passa num número maduro",
           "o teto do dia depende da reputação do canal, não do calendário")

    trava_maduro = po.avaliar_vazao(agora_utc=TERCA_10H, na_hora=0, no_dia=200,
                                    maturidade="maduro")
    checar(not trava_maduro.pode and "200" in trava_maduro.motivo,
           "e o maduro também tem fim: 200", trava_maduro.motivo)

    checar(po.teto_do_dia("novo") == 20 and po.teto_do_dia("maduro") == 200,
           "os tetos são 20 e 200",
           f"{po.teto_do_dia('novo')} / {po.teto_do_dia('maduro')}")

    # 📊 Consequência aritmética que precisa ficar escrita: 12/h dentro de uma
    # janela de 12 h dá 144/dia. O teto de 200 do maduro é folga, nunca a
    # restrição ativa. Se um dia alguém subir 12/h, isto aqui muda junto.
    checar(po._TETO_HORA * (po._JANELA_FECHA_H - po._JANELA_ABRE_H) < po._TETO_DIA_MADURO,
           "o teto por hora é a restrição ativa, não o teto diário do maduro",
           f"{po._TETO_HORA}/h x {po._JANELA_FECHA_H - po._JANELA_ABRE_H}h = "
           f"{po._TETO_HORA * (po._JANELA_FECHA_H - po._JANELA_ABRE_H)} < {po._TETO_DIA_MADURO}")


def teste_maduro_exige_tempo_E_volume():
    print("\n[G4] 'Maduro' precisa das duas coisas")
    po, *_ = montar()

    checar(po.maturidade_do_canal(60, 500) == "maduro",
           "60 dias e 500 envios: maduro")
    checar(po.maturidade_do_canal(365, 3) == "novo",
           "um ano de idade e 3 envios: NOVO",
           "número velho e parado não tem reputação — só tem idade")
    checar(po.maturidade_do_canal(1, 5000) == "novo",
           "5000 envios em 1 dia: NOVO",
           "isso não é maturidade, é exatamente a rajada que estamos impedindo")
    checar(po.maturidade_do_canal(0, 0) == "novo",
           "canal sem histórico nenhum: novo")
    checar(po.maturidade_do_canal(29, 199) == "novo" and po.maturidade_do_canal(30, 200) == "maduro",
           "a fronteira é 30 dias E 200 envios, inclusiva")


def teste_a_parada_e_por_corretora():
    print("\n[G5] O freio de uma corretora não derruba as outras")
    po, banco, redis, wa, act = montar(TERCA_10H)

    checar(rodar(po.parar_envios("corretora-A", "número sob análise")) is True,
           "a parada é registrada")
    checar(rodar(po.envios_parados("corretora-A")) == "número sob análise",
           "e o motivo fica legível para quem for perguntar",
           "um freio sem motivo escrito é um freio que ninguém sabe soltar")
    checar(rodar(po.envios_parados("corretora-B")) is None,
           "a corretora vizinha continua liberada",
           "chave por company_id — parada global seria uma corretora derrubando a outra")

    parada = rodar(po.governar_envio("corretora-A"))
    checar(not parada.pode and parada.esperar_s == 0,
           "com o freio puxado o veredito é recusa, não adiamento",
           f"{parada!r}")
    checar("parad" in parada.motivo.lower(),
           "e o motivo diz que está parado", parada.motivo)

    vizinha = rodar(po.governar_envio("corretora-B"))
    checar(vizinha.pode, "a vizinha envia normalmente", vizinha.motivo)

    checar(any("PARADOS" in r["titulo"] for r in act.registrado),
           "a parada aparece em Atividades — o corretor vê que foi parado")

    # E a mensagem fria de A não é enfileirada: guardar tudo enquanto o freio
    # está puxado faz sair de uma vez quando ele soltar.
    wa.enviados.clear()
    res = rodar(po.send_to_client_guarded("corretora-A", "5547999112233", "oi", "billing"))
    checar(res.get("ok") is False and res.get("queued") is False,
           "envio frio de A é recusado, e NÃO vai para a fila",
           f"{res}")
    checar(not wa.enviados, "nada saiu pelo canal")

    checar(rodar(po.retomar_envios("corretora-A")) is True, "o freio solta")
    checar(rodar(po.envios_parados("corretora-A")) is None, "e some do Redis")


def teste_mensagem_quente_nunca_espera():
    print("\n[G6] Resposta a quem está esperando NÃO passa pelo governador")
    po, banco, redis, wa, act = montar(TERCA_10H)

    # Cenário desenhado para barrar tudo que é frio ao mesmo tempo:
    # domingo, de madrugada, com o freio puxado e o teto estourado.
    rodar(po.parar_envios("c1", "freio de teste"))

    frio = po.avaliar_vazao(agora_utc=DOMINGO_10H, temperatura=po.FRIA,
                            parado="freio de teste", na_hora=99, no_dia=99)
    checar(not frio.pode, "no pior cenário, a fria não sai", frio.motivo)

    quente = po.avaliar_vazao(agora_utc=DOMINGO_10H, temperatura=po.QUENTE,
                              parado="freio de teste", na_hora=99, no_dia=99,
                              gate_livre=False, redis_ok=False)
    checar(quente.pode,
           "no MESMO cenário, a quente passa",
           "domingo + freio + teto estourado + Redis mudo — e ainda assim sai, "
           "porque tem um segurado do outro lado esperando resposta")
    checar("esperando" in quente.motivo,
           "e o motivo diz de quem é a espera", quente.motivo)

    # Prova de ponta a ponta: sai pelo canal, agora, com o freio puxado.
    wa.enviados.clear()
    res = rodar(po.send_to_client_guarded("c1", "5547999112233",
                                          "Já verifiquei sua apólice, segue",
                                          "atendimento", temperatura=po.QUENTE))
    checar(res.get("ok") is True and res.get("queued") is False and len(wa.enviados) == 1,
           "a resposta quente saiu na hora, com o freio da corretora puxado",
           f"{res} / enviados={wa.enviados}")

    # E o padrão do parâmetro é o lado seguro.
    import inspect

    padrao = inspect.signature(po.send_to_client_guarded).parameters["temperatura"].default
    checar(padrao == po.FRIA,
           "quem esquecer de declarar a temperatura cai no caminho GOVERNADO",
           f"padrão={padrao!r} — padrão QUENTE deixaria qualquer chamador novo sem freio")


def teste_redis_mudo_nao_libera_mensagem_fria():
    print("\n[G7] Não saber não é permissão")
    po, banco, redis, wa, act = montar(TERCA_10H)

    redis.mudo = True
    v = rodar(po.governar_envio("c1"))
    checar(not v.pode, "sem Redis, a mensagem fria não sai", v.motivo)
    checar(v.esperar_s > 0, "mas é adiamento, não descarte", f"esperar={v.esperar_s}")
    checar("fria" in v.motivo.lower() or "redis" in v.motivo.lower(),
           "e o motivo nomeia a causa", v.motivo)

    quente = rodar(po.governar_envio("c1", temperatura=po.QUENTE))
    checar(quente.pode, "e a quente continua saindo com o Redis fora do ar",
           "o atendimento não pode parar porque o cache caiu")

    redis.mudo = False
    banco.explodir = True
    v2 = rodar(po.governar_envio("c1"))
    checar(not v2.pode,
           "sem conseguir ler quanto já saiu, a fria também não sai",
           "não saber se o teto estourou é o mesmo que não ter teto")
    banco.explodir = False


def teste_o_governador_de_ponta_a_ponta():
    print("\n[G8] O espaçamento segura a segunda mensagem, e a fila é a que já existia")
    po, banco, redis, wa, act = montar(TERCA_10H)
    wa.enviados.clear()

    fila = po._QUEUE_KEY.format(company_id="c9")

    primeira = rodar(po.send_to_client_guarded("c9", "5547999110001", "cobranca 1", "billing"))
    checar(primeira.get("ok") and not primeira.get("queued") and len(wa.enviados) == 1,
           "a primeira fria sai na hora — nada a espaçar ainda", f"{primeira}")
    checar(len(banco.dados.get("platform_sends", [])) == 1,
           "e fica registrada em platform_sends (a fonte durável dos tetos)")

    segunda = rodar(po.send_to_client_guarded("c9", "5547999110002", "cobranca 2", "billing"))
    checar(segunda.get("queued") is True and len(wa.enviados) == 1,
           "a segunda é ADIADA — o espaçamento está valendo", f"{segunda}")
    checar(240 < int(segunda.get("esperar_s") or 0) < 480,
           "e o adiamento é de 4 a 8 minutos", f"esperar_s={segunda.get('esperar_s')}")
    checar(len(redis.listas.get(fila) or []) == 1,
           "o adiado foi para a FILA QUE JÁ EXISTIA (_QUEUE_KEY), não para uma nova",
           "uma segunda fila de saída seria motor paralelo — CLAUDE.md §5")

    import json

    entrada = json.loads(redis.listas[fila][0])
    checar(entrada.get("adiamentos") == 1,
           "a entrada carrega o contador de adiamentos por vazão",
           f"{entrada}")
    checar("next_try" in entrada,
           "e o next_try que o drenador já sabia respeitar desde a SPEC-045")

    # O teto diário fecha o dia, mesmo com o gate livre e a hora vazia.
    #
    # Os 20 envios ficam ESPALHADOS pelo dia de propósito. Na primeira versão
    # deste teste eles estavam todos no mesmo instante, e o veredito que voltou
    # foi "teto de 12 por hora" — o teto da hora é conferido antes do teto do
    # dia, então 20 envios juntos nunca chegam a exercitar o limite diário.
    banco.dados["platform_sends"] = [
        {"company_id": "c9", "phone": "5547999110000", "kind": "billing",
         "sent_at": (TERCA_10H - timedelta(minutes=90 + i * 20)).isoformat()}
        for i in range(20)]
    redis.kv.pop(po._GATE_KEY.format(company_id="c9"), None)

    h = rodar(po.historico_de_envios("c9", TERCA_10H))
    checar(h["na_hora"] == 0 and h["no_dia"] == 20,
           "20 envios espalhados pelo dia: 0 na última hora, 20 no dia",
           f"{h}")

    estourado = rodar(po.governar_envio("c9", agora_utc=TERCA_10H))
    checar(not estourado.pode and "diário" in estourado.motivo,
           "com a hora vazia e 20 no dia, o número novo fecha assim mesmo",
           estourado.motivo)
    checar(estourado.esperar_s > 3600,
           "e a espera vai até a janela reabrir amanhã, não até a próxima hora",
           f"esperar={estourado.esperar_s}s")


def teste_a_rajada_da_cobranca_pergunta_antes():
    print("\n[G9] billing_collection não dispara mais 100 mensagens seguidas")
    fonte = _ler("backend", "app", "services", "billing_collection.py")
    codigo = _sem_comentario(fonte)

    checar("_esperar_o_governador" in codigo,
           "o laço de envio consulta o governador")
    checar("governar_envio" in codigo,
           "e a consulta é ao governador de verdade, não a um freio local")

    # A ordem importa: perguntar DEPOIS de enviar não impede rajada nenhuma.
    laco = fonte.index("for indice, item in enumerate(a_enviar):")
    pergunta = fonte.index("_esperar_o_governador", laco)
    envio = fonte.index("get_whatsapp_service().send_message", laco)
    checar(pergunta < envio,
           "a pergunta vem ANTES do envio",
           "perguntar depois de enviar seria contar o estrago, não evitá-lo")

    checar("break" in fonte[pergunta:envio],
           "quando o governador nega, a rotina PARA o laço",
           "continuar iterando ignorando o não seria pior que não perguntar")
    checar("record_platform_send" in codigo,
           "e todo envio é registrado — sem registro o teto diário nunca fecha")
    checar("await asyncio.sleep(" in codigo and "time.sleep(" not in codigo,
           "a espera é assíncrona",
           "time.sleep aqui congelaria o event loop de TODAS as corretoras (Bloco H)")

    # E o par texto+boleto continua junto: é uma aproximação, não duas.
    checar(codigo.index("_esperar_o_governador") < codigo.index("send_document"),
           "o boleto em PDF sai logo após o texto que o anuncia",
           "espaçar o anexo do texto deixaria o segurado esperando um arquivo "
           "que ele acabou de ler que viria 'abaixo'")

    # Prova funcional do orçamento: espera curta cabe, espera longa não.
    po, *_ = montar()
    curta = po.avaliar_vazao(agora_utc=TERCA_10H, gate_livre=False, faltam_no_gate_s=300)
    longa = po.dentro_da_janela(TERCA_21H)
    checar(0 < curta.esperar_s <= 3600,
           "espaçamento cabe no orçamento de 1h da rotina",
           f"esperar={curta.esperar_s}")
    checar(longa.esperar_s > 3600,
           "janela fechada NÃO cabe — a rotina para e relata em vez de dormir a noite",
           f"esperar={longa.esperar_s}")


def teste_o_briefing_foi_destravado_sem_perder_a_guarda():
    print("\n[G10] delivery_executor destravado, guarda por import intacta")
    caminho = os.path.join(BACKEND, "app", "services", "whatsapp", "outbound_governor.py")
    checar(os.path.exists(caminho),
           "o módulo existe no caminho que o executor procura",
           "app/services/whatsapp/outbound_governor.py — o nome estava escrito "
           "no `except` do executor desde a SPEC-064")

    fonte = _ler("backend", "app", "services", "intelligence", "delivery_executor.py")
    codigo = _sem_comentario(fonte)
    checar("from app.services.whatsapp import outbound_governor" in codigo,
           "o import continua sendo a guarda",
           "trocar por flag seria trocar 'não existe' por 'alguém pode ligar sem querer'")
    checar("ainda não existe" in fonte,
           "e o motivo escrito para o caso de o módulo sumir continua lá")
    checar("governar_envio_sync" in codigo,
           "o canal consulta o governador antes de enviar")
    checar("temperatura=outbound_governor.QUENTE" in codigo,
           "e não reserva slot duas vezes para a mesma aproximação",
           "o slot é reservado uma vez, no governar_envio_sync")

    # O motivo do canal SEMPRE contém a palavra 'governador' — é o que o teste
    # do Bloco E (test_briefing_sai_de_pending) verifica.
    inicio = fonte.index("def _whatsapp(")
    fim = fonte.index("def _esperar(", inicio)
    corpo = fonte[inicio:fim]
    motivos = corpo.count('ResultadoDeCanal(')
    com_governador = corpo.lower().count("governador")
    checar(motivos >= 4 and com_governador >= motivos,
           "todo caminho de saída do canal nomeia o governador",
           f"{motivos} resultados, {com_governador} menções")

    # O façade não pode ter lógica — se tiver, virou o segundo motor.
    fachada = _ler("backend", "app", "services", "whatsapp", "outbound_governor.py")
    checar("from app.services.platform_outbound import" in fachada,
           "o módulo reexporta de platform_outbound")
    corpo_util = [l for l in _sem_comentario(fachada).split("\n")
                  if l.strip() and not l.strip().startswith(('"', "'"))]
    checar(not any(l.startswith("def ") or l.startswith("class ") for l in corpo_util),
           "e não define função nem classe própria",
           "lógica aqui seria uma segunda fila de saída — CLAUDE.md §5")


def main() -> int:
    print("=" * 68)
    print("GOVERNADOR DE ENVIO — O NUMERO DA CORRETORA NAO E NOSSO PARA QUEIMAR")
    print("=" * 68)
    for t in (teste_o_intervalo_nao_bate_no_minuto_cheio,
              teste_a_janela_fecha_de_noite_e_no_domingo,
              teste_os_tetos_param_de_verdade,
              teste_maduro_exige_tempo_E_volume,
              teste_a_parada_e_por_corretora,
              teste_mensagem_quente_nunca_espera,
              teste_redis_mudo_nao_libera_mensagem_fria,
              teste_o_governador_de_ponta_a_ponta,
              teste_a_rajada_da_cobranca_pergunta_antes,
              teste_o_briefing_foi_destravado_sem_perder_a_guarda):
        try:
            t()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{t.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {t.__name__} EXPLODIU: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 68)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("A VAZAO E GOVERNADA, E QUEM ESTA ESPERANDO NAO ESPERA MAIS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
