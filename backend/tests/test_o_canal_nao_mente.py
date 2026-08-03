"""O canal diz o que é, ou admite que não sabe — mas não afirma o que não confirmou.

📊 Medido em 03/08/2026 no banco de produção (projeto `dcajcvlzcjbmyapmklil`):

    SELECT id, purpose, is_active, channel_status, last_seen_at,
           now() - last_seen_at AS idade
    FROM integrations ORDER BY last_seen_at DESC NULLS LAST;

    observer   6c9c55e2…  ativa  connected     29/07 18:49    4 dias 09h
    observer   04b5cdbc…  ativa  connected     29/07 18:48    4 dias 09h
    observer   3aa75902…  ativa  connecting    28/07 13:39    5 dias 14h
    attendance 04b5cdbc…  ativa  disconnected  22/07 20:44   11 dias 07h

Três canais ATIVOS afirmando um estado que ninguém confirmava há quatro ou cinco
dias. Um deles preso em "Conectando…" — que não é só desatualizado, é uma
promessa: sugere um progresso em curso que já não existia. **E nenhum vigia
desmentia.**

É a mesma família do `work_run` em `queued` sem lease, e a mesma família do
`master` × `master_admin`: um registro que sobreviveu ao fato que ele descrevia,
sem ninguém encarregado de contestá-lo.

A causa, que é mais simples do que o sintoma
--------------------------------------------
`last_seen_at` só era escrito quando chegava um `connection.update` do Evolution
(`webhook.py`, `observer_intake.py`) ou no pareamento. Evento de TRANSIÇÃO não
chega em canal parado — logo o silêncio era indistinguível da saúde, e a coluna
que deveria medir vida media apenas "a última vez que algo mudou".

Por isso o heartbeat **confirma antes de contestar**: pergunta ao provedor e,
quando a resposta vem, renova `last_seen_at`. Só depois disso "ninguém confirmou
este canal há 15 minutos" passa a ser evidência de alguma coisa.

O que este arquivo prova
------------------------
V1  o vocabulário único continua de pé (estado desconhecido não vira "connected")
V2  `last_seen_at` é lido em TODAS as formas que o PostgREST devolve
V3  obsolescência medida contra as linhas REAIS de produção
V4  a tabela-verdade da decisão, inclusive os dois casos em que o certo é calar
V5  a varredura sobre as 4 linhas ativas medidas — e o alarme que NÃO se repete
V6  a sonda que responde renova `last_seen_at` (a correção da causa-raiz)
V7  sonda que explode não derruba a varredura nem inventa queda
V8  o job entrou no APScheduler que já existia; nenhum motor novo nasceu
V9  o token do canal nunca chega ao log
V10 o interruptor de emergência existe e desliga de verdade
"""

from __future__ import annotations

import asyncio
import importlib.util
import io
import os
import re
import sys
import types
from datetime import datetime, timedelta, timezone

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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


def _carregar_channel_state():
    """Carrega o módulo por caminho — `app/core/__init__` puxa pydantic e o
    mundo inteiro, e este teste não precisa do mundo."""
    for nome in ("app", "app.services", "app.services.whatsapp"):
        modulo = sys.modules.setdefault(nome, types.ModuleType(nome))
        modulo.__path__ = []
    caminho = os.path.join(RAIZ, "backend", "app", "services", "whatsapp", "channel_state.py")
    spec = importlib.util.spec_from_file_location("app.services.whatsapp.channel_state", caminho)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules["app.services.whatsapp.channel_state"] = modulo
    spec.loader.exec_module(modulo)
    return modulo


CS = _carregar_channel_state()

# O relógio dos testes: 03/08/2026 04:00 UTC, alguns minutos depois da medição.
AGORA = datetime(2026, 8, 3, 4, 0, 0, tzinfo=timezone.utc)

# As linhas ATIVAS exatamente como o banco as devolveu em 03/08/2026.
# `token` é ilustrativo 💭 — o valor real é cifrado e nunca sai do cofre.
LINHAS_REAIS = [
    {"id": "35e45ffb", "company_id": "6c9c55e2", "provider": "evolution-go",
     "purpose": "observer", "is_active": True, "channel_status": "connected",
     "last_seen_at": "2026-07-29 18:49:02.368809+00", "token": "cifrado",
     "base_url": "https://exemplo.invalid"},
    {"id": "2130e95f", "company_id": "04b5cdbc", "provider": "evolution-go",
     "purpose": "observer", "is_active": True, "channel_status": "connected",
     "last_seen_at": "2026-07-29 18:48:55.365001+00", "token": "cifrado",
     "base_url": "https://exemplo.invalid"},
    {"id": "d0746839", "company_id": "3aa75902", "provider": "evolution-go",
     "purpose": "observer", "is_active": True, "channel_status": "connecting",
     "last_seen_at": "2026-07-28 13:39:24.464987+00", "token": "cifrado",
     "base_url": "https://exemplo.invalid"},
    {"id": "595f6cb0", "company_id": "04b5cdbc", "provider": "evolution-go",
     "purpose": "attendance", "is_active": True, "channel_status": "disconnected",
     "last_seen_at": "2026-07-22 20:44:46.692560+00", "token": "cifrado",
     "base_url": "https://exemplo.invalid"},
]


# ---------------------------------------------------------------------------
# Banco de mentira: o suficiente para a varredura rodar inteira, sem rede.
# ---------------------------------------------------------------------------
class _Consulta:
    def __init__(self, banco, linhas, campos=None):
        self._banco, self._linhas, self._campos = banco, linhas, campos

    def select(self, *_a, **_k):
        return self

    def update(self, campos):
        return _Consulta(self._banco, self._linhas, campos)

    def eq(self, coluna, valor):
        if self._campos is None:
            return _Consulta(self._banco, [l for l in self._linhas if l.get(coluna) == valor])
        self._banco.filtros.append((coluna, valor))
        return self

    def in_(self, coluna, valores):
        return _Consulta(self._banco, [l for l in self._linhas if l.get(coluna) in valores],
                         self._campos)

    def limit(self, *_a, **_k):
        return self

    def execute(self):
        if self._campos is not None:
            self._banco.escritas.append(dict(self._campos))
            return types.SimpleNamespace(data=[])
        return types.SimpleNamespace(data=[dict(l) for l in self._linhas])


class BancoFalso:
    def __init__(self, linhas):
        self.linhas = [dict(l) for l in linhas]
        self.escritas: list[dict] = []
        self.filtros: list[tuple] = []

    def table(self, _nome):
        return _Consulta(self, self.linhas)


def _varrer(linhas, resposta_da_sonda=None, explodir=False, agora=AGORA):
    """Roda a varredura completa com sonda e alarme injetados."""
    banco = BancoFalso(linhas)
    alarmes: list[dict] = []

    async def sonda(_linha):
        if explodir:
            raise RuntimeError("provedor fora do ar")
        return resposta_da_sonda

    async def alarme(linha, decisao, idade):
        alarmes.append({"id": linha["id"], "decisao": decisao, "idade": idade})

    resumo = asyncio.run(CS.verificar_canais(db=banco, sonda=sonda, alarme=alarme, agora=agora))
    return resumo, banco, alarmes


# ---------------------------------------------------------------------------


def teste_o_vocabulario_continua_honesto():
    print("\n[V1] Estado que não se conhece NÃO vira 'connected'")
    checar(CS.normalizar_estado("banana") == CS.DESCONHECIDO,
           "estado desconhecido continua 'unknown'")
    checar(CS.esta_conectado("unknown") is False,
           "'unknown' não passa por conectado",
           "tela que mostra Conectado sem confirmação faz o corretor achar "
           "que os segurados estão sendo atendidos")
    checar(CS.rotulo_humano("unknown") == "Estado desconhecido",
           "e a pessoa lê 'Estado desconhecido', não uma palavra de protocolo")
    checar(CS.CONECTANDO in CS.ESTADOS_QUE_AFIRMAM and CS.CONECTADO in CS.ESTADOS_QUE_AFIRMAM,
           "'connecting' entra na lista dos que AFIRMAM",
           "5 dias em 'Conectando…' é promessa de progresso que não existe")
    checar(CS.DESCONECTADO not in CS.ESTADOS_QUE_AFIRMAM,
           "quem já diz 'disconnected' não está mentindo — não se contesta")


def teste_o_instante_e_lido_em_qualquer_forma():
    print("\n[V2] `last_seen_at` é lido em todas as formas do PostgREST")
    esperado = datetime(2026, 7, 29, 18, 49, 2, 368809, tzinfo=timezone.utc)
    checar(CS.ler_instante("2026-07-29 18:49:02.368809+00") == esperado,
           "offset de DUAS casas ('+00') — a forma que o banco devolveu de verdade",
           "é aqui que `fromisoformat` cru falha e a idade viraria None")
    checar(CS.ler_instante("2026-07-29T18:49:02.368809+00:00") == esperado,
           "ISO completo com '+00:00'")
    checar(CS.ler_instante("2026-07-29T18:49:02.368809Z") == esperado, "sufixo 'Z'")
    checar(CS.ler_instante("2026-07-29 18:49:02.368809").tzinfo is timezone.utc,
           "sem fuso é assumido UTC (nunca ingênuo)",
           "datetime ingênuo subtraído de um com fuso levanta TypeError e "
           "derrubaria a varredura inteira")
    checar(CS.ler_instante("não é data") is None and CS.ler_instante(None) is None,
           "lixo e vazio devolvem None, não explodem")
    checar(CS.esta_obsoleto(None, AGORA) is True,
           "nunca confirmado conta como obsoleto",
           "None é o caso mais obsoleto que existe, não o mais fresco")


def teste_obsolescencia_contra_producao():
    print("\n[V3] A régua de 15 minutos aplicada às linhas reais")
    for linha in LINHAS_REAIS:
        idade = CS.idade_em_minutos(linha["last_seen_at"], AGORA)
        checar(CS.esta_obsoleto(linha["last_seen_at"], AGORA, 15),
               f"{linha['id']} ({linha['purpose']}) está obsoleta",
               f"{idade / 60:.0f}h sem confirmação")
    recente = (AGORA - timedelta(minutes=5)).isoformat()
    checar(not CS.esta_obsoleto(recente, AGORA, 15),
           "5 minutos NÃO é obsoleto",
           "um ciclo perdido é ruído; três seguidos é padrão")
    limiar = (AGORA - timedelta(minutes=14, seconds=59)).isoformat()
    checar(not CS.esta_obsoleto(limiar, AGORA, 15), "14min59s ainda é fresco")
    checar(CS.esta_obsoleto((AGORA - timedelta(minutes=15, seconds=1)).isoformat(), AGORA, 15),
           "15min01s já não é")


def teste_a_tabela_verdade_da_decisao():
    print("\n[V4] O núcleo puro decide — e às vezes o certo é não mexer")
    velho = "2026-07-29 18:49:02+00"
    novo = (AGORA - timedelta(minutes=2)).isoformat()

    d = CS.decidir_heartbeat(estado_atual="connected", last_seen_at=velho, agora=AGORA)
    checar(d["novo_estado"] == CS.DESCONHECIDO and d["alarmar"] is True,
           "afirmava 'connected', ninguém confirmou → 'unknown' + alarme", str(d))
    checar(d["tocar_last_seen"] is False,
           "e NÃO renova `last_seen_at`",
           "renovar sem confirmação seria forjar frescor — o defeito original "
           "vestido de correção")

    d = CS.decidir_heartbeat(estado_atual="connecting", last_seen_at=velho, agora=AGORA)
    checar(d["novo_estado"] == CS.DESCONHECIDO,
           "'connecting' de 5 dias também é contestado", str(d))

    d = CS.decidir_heartbeat(estado_atual="disconnected", last_seen_at=velho, agora=AGORA)
    checar(d["novo_estado"] is None and d["alarmar"] is False,
           "já honesto: não mexe e não alarma",
           "re-alarmar todo ciclo é como se ensina alguém a ignorar alarme")

    d = CS.decidir_heartbeat(estado_atual="connected", last_seen_at=novo, agora=AGORA)
    checar(d["novo_estado"] is None and d["motivo"] == "ainda_fresco",
           "fresco e sem sonda: silêncio",
           "sonda que falhou não é canal que caiu")

    d = CS.decidir_heartbeat(estado_atual="connected", last_seen_at=velho,
                             resposta_da_sonda="open", agora=AGORA)
    checar(d["novo_estado"] == CS.CONECTADO and d["tocar_last_seen"] is True
           and d["alarmar"] is False,
           "sonda confirmou: estado mantido e `last_seen_at` RENOVADO", str(d))

    d = CS.decidir_heartbeat(estado_atual="connected", last_seen_at=novo,
                             resposta_da_sonda="close", agora=AGORA)
    checar(d["novo_estado"] == CS.DESCONECTADO and d["alarmar"] is True,
           "sonda desmentiu: vira 'disconnected' (queda MEDIDA) + alarme", str(d))
    checar(CS.decidir_heartbeat(estado_atual="disconnected", last_seen_at=novo,
                                resposta_da_sonda="close", agora=AGORA)["alarmar"] is False,
           "confirmar queda de quem já estava caído não alarma de novo")

    checar(CS.estado_da_sonda({"data": {"LoggedIn": True}}) == CS.CONECTADO
           and CS.estado_da_sonda({"data": {"Connected": True}}) == CS.CONECTANDO
           and CS.estado_da_sonda({}) == CS.DESCONECTADO,
           "a resposta do Evolution GO é traduzida como em `_go_status_payload`",
           "LoggedIn = sessão de pé; Connected sozinho = só o websocket")


def teste_a_varredura_sobre_producao():
    print("\n[V5] A varredura desmente os três — uma vez, não a cada ciclo")
    resumo, banco, alarmes = _varrer(LINHAS_REAIS)

    checar(resumo["verificados"] == 4, "as 4 integrações ativas foram olhadas", str(resumo))
    checar(resumo["contestados"] == 3,
           "as 3 que AFIRMAVAM foram contestadas",
           "duas 'connected' de 4 dias e uma 'connecting' de 5")
    checar(resumo["inalterados"] == 1,
           "a que já dizia 'disconnected' ficou intacta",
           "canal honesto não é canal quebrado")
    # `all([])` é True: sem o len() na frente, uma varredura que não escreve
    # NADA passaria por estas duas linhas. Verde vazio é pior que vermelho.
    checar(len(banco.escritas) == 3
           and all(e["channel_status"] == CS.DESCONHECIDO for e in banco.escritas),
           "as 3 escritas gravam 'unknown', NUNCA 'disconnected'",
           "não medimos queda nenhuma — só perdemos o direito de dizer Conectado")
    checar(len(banco.escritas) == 3
           and all("last_seen_at" not in e for e in banco.escritas),
           "e nenhuma escrita forjou frescor")
    checar(("id", "35e45ffb") in banco.filtros and ("company_id", "6c9c55e2") in banco.filtros,
           "toda escrita filtra por id E por corretora",
           "o job varre a plataforma inteira; sem o filtro de tenant um erro "
           "de código atravessaria corretoras")
    checar(len(alarmes) == 3, f"3 alarmes na primeira passada (saíram {len(alarmes)})")

    # Segunda passada: o banco agora diz 'unknown' — não há mais mentira a desfazer.
    segundo_estado = [dict(l, channel_status=CS.DESCONHECIDO) if l["channel_status"] in
                      ("connected", "connecting") else l for l in LINHAS_REAIS]
    resumo2, banco2, alarmes2 = _varrer(segundo_estado)
    checar(resumo2["contestados"] == 0 and not alarmes2,
           "segunda varredura: zero escritas e zero alarmes",
           "um vigia que grita a cada 5 minutos vira ruído e é silenciado")


def teste_a_sonda_que_responde_renova_o_frescor():
    print("\n[V6] Confirmar é o que faz a coluna significar alguma coisa")
    resumo, banco, alarmes = _varrer(LINHAS_REAIS, resposta_da_sonda="open")
    checar(resumo["confirmados"] == 4 and resumo["contestados"] == 0,
           "provedor respondeu por todas: 4 confirmadas", str(resumo))
    checar(len(banco.escritas) == 4
           and all(e.get("last_seen_at") for e in banco.escritas),
           "as 4 renovam `last_seen_at`",
           "era exatamente isto que faltava: nada renovava a coluna, então "
           "silêncio e saúde eram indistinguíveis")
    checar(not alarmes, "e ninguém é acordado à toa")

    resumo, banco, alarmes = _varrer(LINHAS_REAIS, resposta_da_sonda="close")
    checar(len(banco.escritas) == 4
           and all(e["channel_status"] == CS.DESCONECTADO for e in banco.escritas),
           "provedor disse que caiu: aí sim 'disconnected'",
           "queda medida pode ser afirmada; queda suposta, não")
    checar(len(alarmes) == 3,
           "alarma pelas 3 que afirmavam estar bem, não pela que já admitia",
           f"saíram {len(alarmes)}")


def teste_a_sonda_que_explode_nao_derruba_nada():
    print("\n[V7] Provedor fora do ar não vira acusação nem exceção")
    resumo, banco, _ = _varrer(LINHAS_REAIS, explodir=True)
    checar(resumo["ok"] is True and resumo["erros"] == 4,
           "a varredura sobreviveu e contou os erros", str(resumo))
    checar(not banco.escritas,
           "e NÃO escreveu nada",
           "exceção na sonda não é veredito sobre o canal do corretor")


def teste_o_job_entrou_no_agendador_que_ja_existia():
    print("\n[V8] Nenhum motor paralelo (CLAUDE.md §5)")
    proc = _ler("backend", "app", "tasks", "buffer_processor.py")
    checar('id="channel_heartbeat_check"' in proc, "o job está registrado")
    checar("from app.services.whatsapp.channel_state import verificar_canais" in proc,
           "e aponta para o dono do estado do canal")
    checar("max_instances=1" in proc.split("channel_heartbeat_check")[0].rsplit("add_job", 1)[-1]
           or "max_instances=1," in proc,
           "com uma instância por vez")
    checar(proc.count("AsyncIOScheduler()") == 1,
           "continua havendo UM agendador no arquivo")

    fonte = _ler("backend", "app", "services", "whatsapp", "channel_state.py")
    for proibido in ("AsyncIOScheduler", "BackgroundScheduler", "add_job", "while True"):
        checar(proibido not in fonte,
               f"o heartbeat não traz '{proibido}' consigo",
               "quem agenda é o APScheduler que já existe")
    checar("PROVEDORES_SONDAVEIS" in fonte and "evolution-go" in fonte,
           "só sonda o provedor que sabemos perguntar",
           "marcar provedor que não sabemos sondar transformaria a nossa "
           "ignorância em acusação")


def teste_o_token_nunca_chega_ao_log():
    print("\n[V9] O segredo do canal não vaza pelo vigia")
    fonte = _ler("backend", "app", "services", "whatsapp", "channel_state.py")
    checar("decrypt_integration_secret" in fonte,
           "o token é lido pela porta do cofre, não do banco cru")
    checar(not re.search(r'f"[^"]*\{token', fonte) and not re.search(r"f'[^']*\{token", fonte),
           "o token nunca entra numa f-string")
    linhas_de_log = [l for l in fonte.split("\n") if "logger." in l]
    checar(all("token" not in l or "sem token" in l for l in linhas_de_log),
           "nenhuma chamada de log recebe o token",
           "CLAUDE.md §13.3: só presença/ausência, nunca o valor")
    checar('"apikey": token' in fonte,
           "e o token só é usado onde precisa ser: no cabeçalho da sonda")


def teste_o_interruptor_desliga_de_verdade():
    print("\n[V10] Existe botão de desligar, e ele funciona")
    anterior = os.environ.get("CHANNEL_HEARTBEAT_ENABLED")
    try:
        os.environ["CHANNEL_HEARTBEAT_ENABLED"] = "0"
        checar(CS.heartbeat_ligado() is False, "CHANNEL_HEARTBEAT_ENABLED=0 desliga")
        resumo, banco, _ = _varrer(LINHAS_REAIS)
        checar(resumo["verificados"] == 0 and not banco.escritas,
               "e desligado ele não lê nem escreve nada")
        os.environ["CHANNEL_HEARTBEAT_ENABLED"] = "1"
        checar(CS.heartbeat_ligado() is True, "e volta a ligar")
    finally:
        if anterior is None:
            os.environ.pop("CHANNEL_HEARTBEAT_ENABLED", None)
        else:
            os.environ["CHANNEL_HEARTBEAT_ENABLED"] = anterior

    anterior_limite = os.environ.get("CHANNEL_HEARTBEAT_STALE_MINUTES")
    try:
        os.environ["CHANNEL_HEARTBEAT_STALE_MINUTES"] = "45"
        checar(CS.limite_obsoleto_minutos() == 45, "o limite é ajustável por ambiente")
        os.environ["CHANNEL_HEARTBEAT_STALE_MINUTES"] = "isto-não-é-número"
        checar(CS.limite_obsoleto_minutos() == CS.LIMITE_OBSOLETO_MINUTOS,
               "variável mal escrita cai no padrão de 15, não derruba o job")
    finally:
        if anterior_limite is None:
            os.environ.pop("CHANNEL_HEARTBEAT_STALE_MINUTES", None)
        else:
            os.environ["CHANNEL_HEARTBEAT_STALE_MINUTES"] = anterior_limite


def main() -> int:
    print("=" * 68)
    print("O CANAL NAO MENTE — HEARTBEAT DO WHATSAPP (SPEC-063 BLOCO V)")
    print("=" * 68)
    for t in (teste_o_vocabulario_continua_honesto,
              teste_o_instante_e_lido_em_qualquer_forma,
              teste_obsolescencia_contra_producao,
              teste_a_tabela_verdade_da_decisao,
              teste_a_varredura_sobre_producao,
              teste_a_sonda_que_responde_renova_o_frescor,
              teste_a_sonda_que_explode_nao_derruba_nada,
              teste_o_job_entrou_no_agendador_que_ja_existia,
              teste_o_token_nunca_chega_ao_log,
              teste_o_interruptor_desliga_de_verdade):
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
    print("O CANAL CONFIRMA, CONTESTA OU ADMITE — MAS NAO AFIRMA SEM PROVA")
    return 0


if __name__ == "__main__":
    sys.exit(main())
