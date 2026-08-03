"""A plataforma não mistura corretoras, não trava, e não nasce aberta.

Quatro defeitos medidos em 02/08/2026, todos no caminho mais quente do produto.

H.1 · O buffer não tinha tenant na chave
----------------------------------------
    key = f"whatsapp_buffer:{phone}"          # só o telefone

O mesmo segurado pode falar com DUAS corretoras — ele tem auto numa e
residencial na outra, e isso é comum. Dentro da janela de 8 a 25 segundos, as
duas conversas caíam na MESMA chave: as mensagens eram concatenadas e
``data["payload"] = payload`` sobrescrevia o payload. O conjunto todo era
processado sob a integração da ÚLTIMA mensagem.

**A corretora B recebia a pergunta feita à corretora A, e respondia com o
agente dela.**

H.2 · O webhook legado nascia aberto
------------------------------------
``WHATSAPP_WEBHOOK_AUTH_MODE`` tinha padrão ``disabled``, e o EasyPanel **não
define esta variável**. A rota `/api/v1/webhook/z-api` resolvia o TENANT pelo
``connectedPhone`` do CORPO da requisição — que a corretora publica no site.

📊 `ZAPI_INSTANCE_ID`, `ZAPI_TOKEN` e `ZAPI_CLIENT_TOKEN` estão VAZIOS em
produção e o provider é `evolution-go`: a rota não recebe tráfego legítimo.
Fechá-la remove o buraco sem custo.

H.3 · `time.sleep` no caminho async
-----------------------------------
Quatro balões = 2,1 s com o event loop congelado. Nesse tempo o processo não
atende mais ninguém — nem outra corretora.

H.4 · O "número do observador" nunca foi um número
--------------------------------------------------
`_digits(identifier)` sobre `ab-obs-04b5cdbc04-1` produzia ``045041``, e sem
dígito nenhum caía no literal ``"attendance-channel"`` — 📊 que já apareceu numa
sessão real. A busca da sessão e o índice de dedupe usam
``(observer_number, message_id)`` **sem company_id**: duas corretoras no mesmo
valor teriam as conversas FUNDIDAS.
"""

from __future__ import annotations

import io
import os
import sys

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


def _sem_comentario(f: str) -> str:
    return "\n".join(l for l in f.split("\n") if not l.lstrip().startswith("#"))


def teste_o_buffer_isola_corretoras():
    print("\n[H1] O buffer tem TENANT na chave")
    fonte = _ler("backend", "app", "services", "message_buffer_service.py")
    codigo = _sem_comentario(fonte)

    checar('f"whatsapp_buffer:{phone}"' not in codigo,
           "a chave de só-telefone não existe mais",
           "era o que fundia conversas de corretoras diferentes")
    checar('f"whatsapp_buffer:{esc}:{phone}"' in codigo,
           "a chave carrega escopo + telefone")
    checar("_integration_id" in codigo and "connectedPhone" in codigo,
           "o escopo cai do id da integração para o número conectado",
           "o mais específico primeiro; nenhum dos dois é o telefone do cliente")

    # Prova funcional: dois escopos, duas chaves.
    ini = fonte.index("    def chave(")
    fim = fonte.index("    async def add_message", ini)
    ns: dict = {}
    exec(compile("class B:\n    @staticmethod\n" + fonte[ini:fim], "<chave>", "exec"), ns)  # noqa: S102
    chave = ns["B"].chave
    a, b = chave("integ-A", "5511999"), chave("integ-B", "5511999")
    checar(a != b, "mesmo telefone em corretoras diferentes gera chaves DIFERENTES",
           f"{a} vs {b}")
    checar(chave("", "5511999") == chave(None, "5511999"),
           "escopo ausente é determinístico (não gera chave nova a cada chamada)")


def teste_o_varredor_nao_remonta_chave():
    print("\n[H2] O varredor passa a chave inteira, não o telefone")
    proc = _sem_comentario(_ler("backend", "app", "tasks", "buffer_processor.py"))
    checar("buffer_service.should_process(chave)" in proc,
           "should_process recebe a chave completa")
    checar("buffer_service.get_and_clear_buffer(chave)" in proc,
           "get_and_clear_buffer também")
    checar('phone = key.split(":")[-1]' not in proc,
           "o parsing frágil da chave sumiu",
           "era ele que prendia o buffer ao formato de uma parte só")


def teste_o_webhook_legado_nasce_fechado():
    print("\n[H3] A porta legada nasce FECHADA")
    cfg = _ler("backend", "app", "core", "config.py")
    checar('WHATSAPP_WEBHOOK_AUTH_MODE: str = "shared_secret"' in cfg,
           "o padrão é shared_secret",
           "era 'disabled', e o EasyPanel não define a variável — "
           "produção rodava com a porta aberta")
    checar('WHATSAPP_WEBHOOK_AUTH_MODE: str = "disabled"' not in cfg,
           "o padrão aberto não voltou")


def teste_nao_ha_sleep_bloqueante():
    print("\n[H4] Cadência humana não congela o processo")
    ws = _sem_comentario(_ler("backend", "app", "services", "whatsapp_service.py"))
    checar("time.sleep(0.7)" not in ws and "time.sleep(1.2)" not in ws,
           "os sleeps diretos saíram do caminho de envio")
    checar("_dormir(" in ws, "existe uma espera que sabe onde está")


def teste_o_observador_tem_identidade_por_corretora():
    print("\n[H5] O identificador do canal não colide entre corretoras")
    cap = _ler("backend", "app", "services", "atlas", "attendance_capture.py")
    codigo = _sem_comentario(cap)
    checar('_digits(channel_number) or "attendance-channel"' not in codigo,
           "o literal constante 'attendance-channel' não é mais o fallback",
           "📊 ele JÁ apareceu numa sessão de produção — duas corretoras nele "
           "teriam as conversas fundidas")
    checar('f"{str(company_id or \'sem-empresa\')[:8]}:"' in codigo,
           "o identificador começa pela corretora",
           "garante unicidade sem depender da forma do identifier")


def teste_as_variaveis_de_envio_estao_documentadas():
    print("\n[H6] Toda chave que decide envio real está no .env.example")
    env = _ler("backend", ".env.example")
    for v in ("WHATSAPP_WEBHOOK_AUTH_MODE", "WHATSAPP_WEBHOOK_SECRET",
              "INSURER_DISPATCH_LIVE", "DISPATCH_FINALIZE_MODE",
              "DISPATCH_FINALIZE_LIVE_PLAYBOOKS", "CARTOGRAPHER_MODE",
              "ATTENDANT_INBOUND_ALLOWLIST", "CONTEXT_ASSEMBLY_MODE",
              "DESTILADOR_TETO_POR_RODADA", "CHAT_HISTORY_WINDOW"):
        checar(f"\n{v}=" in env, f"{v} documentada")

    # E o padrão escrito no exemplo tem de ser o SEGURO.
    checar("\nINSURER_DISPATCH_LIVE=false" in env,
           "o exemplo traz o portão de envio FECHADO",
           "exemplo com padrão perigoso é armadilha para quem clonar")
    checar("\nDISPATCH_FINALIZE_MODE=test" in env,
           "e o freio de finalização acionado")
    checar("\nCARTOGRAPHER_MODE=0" in env,
           "e o Cartógrafo, que envia WhatsApp real a seguradoras, desligado")


def main() -> int:
    print("=" * 68)
    print("HIGIENE DE PLATAFORMA — NAO MISTURA, NAO TRAVA, NAO NASCE ABERTA")
    print("=" * 68)
    for t in (teste_o_buffer_isola_corretoras,
              teste_o_varredor_nao_remonta_chave,
              teste_o_webhook_legado_nasce_fechado,
              teste_nao_ha_sleep_bloqueante,
              teste_o_observador_tem_identidade_por_corretora,
              teste_as_variaveis_de_envio_estao_documentadas):
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
    print("A PLATAFORMA ISOLA, RESPIRA E NASCE FECHADA")
    return 0


if __name__ == "__main__":
    sys.exit(main())
