# -*- coding: utf-8 -*-
"""SPEC-094.1 · B.5 — a prova de ponta a ponta, SEM REDE.

    ZIP da base publica
      -> `susep_ses_ingest.ingerir()`        agrega 1,8 milhao de linhas
      -> armazenamento (MinIO local ou FAKE) grava SO o agregado
      -> `susep_ses_provider.ler_agregado()` devolve o feixe de plataforma
      -> `registry.calcular("market.loss_ratio")`
      -> a celula da Porto: 05886 · grupo 05 · 202604-06 = 0,5712

🔴 **Ela NAO e um guarda da suite**, e nao roda no CI: depende de um ZIP de
571 MB que nao mora no repositorio. O que o guarda `test_a_fabrica_de_
relatorios.py` [3] prova com dado sintetico, esta prova mede sobre a base
REAL — e as duas fazem falta. A medida do BLOCO 0 e conferida A MAO aqui: o
trimestre e recalculado direto do CSV agregado, linha a linha, ANTES de o
registry ser chamado. Sem essa conta paralela, "o numero bateu" so diria que o
motor concorda consigo mesmo.

⛔ Nenhuma rede. O ZIP e um arquivo local; se ele nao existir, a prova para e
diz isso — nunca baixa nada.

    cd backend
    python scripts/prova_b5_ses_ponta_a_ponta.py <caminho-do-BaseCompleta.zip>
"""
import io, os, sys, time, json, socket, tracemalloc
from datetime import date

sys.path.insert(0, os.path.abspath("."))

#: O ZIP vem do argumento ou de `SES_ZIP`. ⚠️ Nunca de um caminho de maquina
#: escrito aqui dentro: a prova tem de rodar na maquina de quem a repete.
ZIP = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("SES_ZIP", ""))
if not ZIP or not os.path.exists(ZIP):
    print("⛔ Passe o caminho do BaseCompleta.zip (argumento ou SES_ZIP). "
          "Esta prova NAO baixa nada.")
    raise SystemExit(2)


class MinioFalso:
    """O armazenamento, em memoria. Mesma superficie que `MinioService` usa."""

    def __init__(self):
        self.objetos = {}

    def put_bytes(self, chave, corpo, tipo="application/octet-stream"):
        self.objetos[chave] = bytes(corpo)
        return chave

    def download_file(self, chave):
        if chave not in self.objetos:
            raise FileNotFoundError(chave)
        return io.BytesIO(self.objetos[chave])


def minio_local_responde():
    alvo = os.environ.get("MINIO_ENDPOINT", "")
    if not alvo:
        return False, "MINIO_ENDPOINT nao esta no ambiente"
    host, _, porta = alvo.replace("http://", "").replace("https://", "").partition(":")
    try:
        with socket.create_connection((host, int(porta or 9000)), timeout=2):
            return True, alvo
    except Exception as exc:  # noqa: BLE001
        return False, "%s: %s" % (type(exc).__name__, exc)


print("=" * 74)
print("  SPEC-094.1 · B.5 — a prova de ponta a ponta")
print("=" * 74)
vivo, motivo = minio_local_responde()
print("  armazenamento: %s (%s)" % ("MinIO local" if vivo else "MinIO FAKE (em memoria)", motivo))
print("  ZIP: %s (%.1f MB)" % (os.path.basename(ZIP), os.path.getsize(ZIP) / 1e6))

import types as _t
# a casca vazia de `app.services`: o `__init__` real arrasta fastembed, que
# nao esta neste ambiente e nada tem a ver com a prova.
_pkg = _t.ModuleType("app.services"); _pkg.__path__ = ["app/services"]
sys.modules["app.services"] = _pkg
import app.services.susep_ses_ingest as ING
from app.providers import susep_ses_provider as PROV
from app.comercial.metricas import registry as R
from app.providers.reference_analytics_provider import fatos_de_fixture

minio = MinioFalso()

# --- 1 · ingestao ---------------------------------------------------------
tracemalloc.start()
t0 = time.perf_counter()
manifesto = ING.ingerir(minio=minio, caminho_local=ZIP, anos=["2026"])
t_ingestao = time.perf_counter() - t0
_atual, pico = tracemalloc.get_traced_memory()
tracemalloc.stop()
print("\n[1] INGESTAO")
print("    linhas lidas .......... %s" % manifesto.get("linhas_lidas", "?"))
print("    celulas agregadas ..... %s" % manifesto.get("celulas"))
print("    competencia final ..... %s" % manifesto.get("competencia_final"))
print("    objetos gravados ...... %s" % [o["objeto"] for o in manifesto["objetos"]])
print("    📊 latencia ........... %.2f s" % t_ingestao)
print("    📊 pico de memoria .... %.1f MB (tracemalloc)" % (pico / 1e6))
print("    📊 bytes no objeto .... %d" % len(minio.objetos["susep/ses/2026.csv"]))

# --- 2 · leitura ----------------------------------------------------------
t0 = time.perf_counter()
feixe = PROV.ler_agregado(2026, minio,
                          competencia_final=manifesto.get("competencia_final", ""))
t_leitura = time.perf_counter() - t0
print("\n[2] LEITURA DO AGREGADO")
print("    celulas no feixe ...... %d" % len(feixe.facts))
print("    fonte ................. %s" % feixe.fonte)
print("    competencia final ..... %s" % feixe.competencia_final)
print("    coenti de 'Porto Seguro' -> %s" % feixe.coenti_de("porto_seguro"))
print("    coenti de 'sulamerica'   -> %s" % feixe.coenti_de("sulamerica"))
print("    📊 latencia ........... %.3f s" % t_leitura)

# --- 3 · a celula na mao, direto do CSV agregado --------------------------
import csv
premio = sinistro = 0.0
por_mes = {}
texto = minio.objetos["susep/ses/2026.csv"].decode("utf-8")
for linha in csv.DictReader(io.StringIO(texto), delimiter=";"):
    if (linha["coenti"] == "05886" and linha["coramo"][:2] == "05"
            and linha["damesano"] in ("202604", "202605", "202606")):
        p, s = float(linha["premio_ganho"]), float(linha["sinistro_ocorrido"])
        premio += p
        sinistro += s
        # 🔴 o mes soma TODAS as celulas do grupo 05 antes de dividir: dividir
        # celula a celula e depois somar as razoes daria outro numero.
        balde = por_mes.setdefault(linha["damesano"], [0.0, 0.0])
        balde[0] += p
        balde[1] += s
print("\n[3] A CELULA NA MAO (05886 · grupo 05 · 202604-06)")
for mes in sorted(por_mes):
    p, s = por_mes[mes]
    print("    %s ................ %.4f  (%.2f%%)" % (mes, s / p, 100.0 * s / p))
print("    trimestre ............. %.6f  (%.2f / %.2f)" % (sinistro / premio, sinistro, premio))

# --- 4 · o mesmo numero, saindo do REGISTRY -------------------------------
import dataclasses
fatos = fatos_de_fixture()
# 🔴 A carteira sintetica da prova vive NA JANELA de 2026-Q2. A fixture da 094 e
# de 2025, e `_montar_contexto` filtra por `valid_from`: com ela `ctx.apolices`
# sai VAZIA e o recorte por entidade nunca acontece — o numero ate bate, por a
# Porto ser a maior do ramo 05, e bateria pelo motivo errado.
# ⛔ Nenhum nome de pessoa, nenhum documento, nenhuma placa.
modelo = fatos.policies[0]
fatos.policies = [dataclasses.replace(
    modelo, policy_ref="prova-b5-porto", insurer="Porto Seguro",
    valid_from=date(2026, 4, 1), valid_to=date(2027, 3, 31))]
t0 = time.perf_counter()
r = R.calcular("market.loss_ratio", fatos, (date(2026, 4, 1), date(2026, 6, 30)),
               mercado=feixe)
t_metrica = time.perf_counter() - t0
linha = next((x for x in (r.breakdown or []) if x["rotulo"] == "05886·05"), None)
print("\n[4] O REGISTRY")
print("    market.loss_ratio ..... %s (unit=%s)" % (r.value, r.unit))
print("    cobertura ............. %s" % r.coverage)
print("    linhas no breakdown ... %d" % len(r.breakdown or []))
print("    05886·05 .............. %s" % (linha and linha["sinistralidade"]))
print("    📊 latencia da metrica  %.3f s" % t_metrica)
for w in (r.warnings or []):
    print("    ⚠️  %s" % w)

golden = 0.5712
medido = linha["sinistralidade"] if linha else None
print("\n" + "=" * 74)
if medido is not None and abs(round(medido, 4) - golden) < 1e-9:
    print("  ✅ GOLDEN DA PORTO: %.6f -> %.4f == %.4f" % (medido, round(medido, 4), golden))
else:
    print("  ⛔ GOLDEN NAO BATE: %r (esperado %.4f)" % (medido, golden))
print("=" * 74)
