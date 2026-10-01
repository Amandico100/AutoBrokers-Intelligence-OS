# -*- coding: utf-8 -*-
"""SPEC-123 F2a — o corpus da bancada do DESTRAVADOR, a partir do acervo REAL.

    cd backend
    # 1) do banco (SÓ LEITURA: psycopg + `SET TRANSACTION READ ONLY`, nunca `SET` de sessão)
    PYTHONIOENCODING=utf-8 python scripts/gerar_corpus_cerebro.py --gravar
    # 2) de um dump local de `observed_events` (o formato do BLOCO 0 da SPEC-122: uma linha JSON por
    #    evento com session_id, insurer_key, direction, text, wa_timestamp, company)
    PYTHONIOENCODING=utf-8 python scripts/gerar_corpus_cerebro.py --dump <events.jsonl> --gravar
    # sem --gravar: só conta e mostra o resumo (nada escrito)

O que ele faz (e nada mais):

① A FICHA DO CASO (P-122-05). Para cada caso de `tests/corpus/bancada/cerebro/casos.jsonl` (e para cada
   caso novo do grupo D) reconstrói `sessao.slots` e `subservice` a partir da conversa REAL da sessão: o
   que a atendente digitou à URA (`direction='out'`) na tela que PEDIA um dado, e a tela seguinte (a URA
   aceitou?). Quem diz QUAL dado a tela pede é o MOTOR do produto (`match_ura_step` → `{slot}` do passo;
   sem passo, a tabela `_PERGUNTAS_DE_DADO`). O valor é SEMPRE mascarado ({PLACA}, {CPF}, {ENDERECO},
   {NOME}, {NUMERO}…) — o que importa é o modelo SABER que o caso tem o dado. Escolha de menu, data,
   hora e período NÃO entram na ficha (são decisão do segurado, não dado do caso) e ficam registrados em
   `fora_da_ficha`. A origem de cada slot vai em `origem_dos_slots`.
   A ficha vai num campo NOVO (`entrada.ficha`) — a `entrada.sessao` da SPEC-122 fica byte a byte (os
   JSON de `RESULTADOS/` e o recálculo da 122 dependem dela).
② A CONVERSA COM O SEGURADO, quando existe no banco: só as sessões que o AGENTE conduziu (as janelas dos
   `work_runs` de acionamento) têm a conversa do segurado ligada (`work_runs.conversation_id`). 3–10
   falas anteriores ao acionamento, mascaradas.
③ O GRUPO D — as TRAVAS REAIS. Cada tela do acervo passa pelo MOTOR do produto
   (`insurer_dispatch_service.handle_insurer_message`, com a sessão de `new_dispatch_session` e a ficha
   reconstruída; `company_id` fictício, `live` desligado: nada sai, nada é gravado). Fica a tela em que o
   motor devolve `needs_human` com um motivo DESTRAVÁVEL (CONTRATO-123: `sem_chute:*`,
   `tela_que_decide:*`, `tecla_ambigua`, `ramo_indeterminado`, `missing_slots:*`, `loop_guard`,
   `conducao_esgotada`) — o PONTO B — ou em que vai à fase humana (tela órfã: o PONTO A, gatilho
   `cerebro`). O gabarito sai do que a atendente respondeu e da tela seguinte (a PROVA).

⛔ Nada de PII é impresso: o resumo só mostra contagens e texto JÁ mascarado.
⛔ O dump cru nunca entra no repositório (o `--dump` aponta para fora dele).
"""
from __future__ import annotations

import argparse
import collections
import copy
import hashlib
import io
import json
import os
import re
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BACKEND, "scripts"))
sys.path.insert(0, BACKEND)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CORPUS = os.path.join(BACKEND, "tests", "corpus", "bancada", "cerebro")
ARQ_CASOS = os.path.join(CORPUS, "casos.jsonl")
ARQ_D = os.path.join(CORPUS, "casos_d.jsonl")
ARQ_MANIFESTO = os.path.join(CORPUS, "MANIFESTO.json")
TELAS_REAIS = os.path.join(BACKEND, "tests", "corpus", "telas_reais")

#: constante_justificada: o tenant FICTÍCIO da simulação do motor. ⚠️ NÃO é UUID de propósito: o
#: motor só enfileira tela cega (`_registrar_tela_cega_sem_derrubar`) para `company_id` UUID — com
#: este valor a simulação não escreve NADA no banco.
EMPRESA_DA_SIMULACAO = "bancada-simulacao"

# ═════════════════════════════════════════════════════════════════════════════
# O ACERVO (só leitura)
# ═════════════════════════════════════════════════════════════════════════════
_SQL_EVENTOS = """select session_id::text, left(company_id::text, 8), insurer_key, direction, msg_type,
       text, wa_timestamp, coalesce(interactive->>'title', '')
  from observed_events where session_id is not null
 order by session_id, wa_timestamp, created_at"""

_SQL_RUNS = """select w.id::text, w.conversation_id::text, w.started_at, w.finished_at, left(w.company_id::text, 8)
  from work_runs w where w.outcome_type = 'acionamento_assistencia' and w.conversation_id is not null"""

_SQL_MSGS = """select role, content, created_at from messages
 where conversation_id = %s and created_at <= %s order by created_at desc limit 40"""


def _url_do_banco() -> str:
    env = os.path.join(BACKEND, ".env")
    for linha in open(env, encoding="utf-8"):
        if linha.startswith("SUPABASE_DB_URL="):
            return linha.split("=", 1)[1].strip().strip('"')
    raise SystemExit("SUPABASE_DB_URL ausente no .env (presença/ausência — o valor nunca é impresso)")


def _conectar():
    import psycopg

    c = psycopg.connect(_url_do_banco(), autocommit=False, prepare_threshold=None)
    cur = c.cursor()
    cur.execute("SET TRANSACTION READ ONLY")   # 🔴 da TRANSAÇÃO — nunca de sessão (pooler 6543)
    return c, cur


def ler_acervo(dump: Optional[str]) -> Dict[str, List[dict]]:
    """sessão → eventos em ordem. `dump` (jsonl do BLOCO 0) ou o banco, só leitura."""
    ses: Dict[str, List[dict]] = collections.defaultdict(list)
    if dump:
        for l in open(dump, encoding="utf-8"):
            e = json.loads(l)
            sid = e.get("session_id")
            if sid in (None, "None", ""):
                continue
            ses[sid].append({"sid": sid, "company": e.get("company") or "", "seg": e.get("insurer_key") or "",
                             "dir": e.get("direction"), "tipo": e.get("msg_type"),
                             "text": str(e.get("text") or ""), "ts": e.get("wa_timestamp") or ""})
    else:
        c, cur = _conectar()
        try:
            cur.execute(_SQL_EVENTOS)
            for sid, comp, seg, d, tipo, texto, ts, titulo in cur:
                ses[sid].append({"sid": sid, "company": comp or "", "seg": seg or "", "dir": d, "tipo": tipo,
                                 "text": str(texto or titulo or ""), "ts": ts.isoformat() if ts else ""})
        finally:
            c.rollback()
            c.close()
    for evs in ses.values():
        evs.sort(key=lambda e: e["ts"] or "")
    return ses


# ═════════════════════════════════════════════════════════════════════════════
# O MASCARADOR — o do PRODUTO (`atlas.templater.templatize`) + o que a SPEC-122 aprendeu
# ═════════════════════════════════════════════════════════════════════════════
_VOC = [re.compile(r"falando com \*?([A-ZÀ-Ú][\wÀ-ú']+(?: [A-ZÀ-Ú][\wÀ-ú']+){0,4})"),
        re.compile(r"(?:^|\n)\*?([A-ZÀ-Ú][a-zà-ú]{2,}(?: [A-ZÀ-Ú][a-zà-ú]{2,}){0,3}|[A-ZÀ-Ú]{3,}(?: [A-ZÀ-Ú]{2,}){0,4})"
                   r"\*?,? (?:é você|em qual|descreva|você|tudo bem|poderia|qual|me |pode|agora|obrigad|certo|"
                   r"perfeito|entendi|precisamos|informe|por favor)"),
        re.compile(r"(?:Ol[áa]|Oi|Bom dia|Boa tarde|Boa noite),? \*?([A-ZÀ-Ú][a-zà-ú]{2,}|[A-ZÀ-Ú]{3,})"),
        re.compile(r"(?:^|\n)\*?([A-ZÀ-Ú][a-zà-ú]{2,}(?: [A-ZÀ-Ú][a-zà-ú]{2,}){0,3}|[A-ZÀ-Ú]{3,}(?: [A-ZÀ-Ú]{2,}){0,4})\*?,\s")]
_NAO_NOME = {"para", "sim", "nao", "não", "voltar", "você", "voce", "por", "favor", "certo", "perfeito", "ok",
             "olá", "ola", "oi", "bom", "boa", "agora", "entendi", "obrigado", "obrigada", "qual", "caso", "menu",
             "botão", "botao", "tudo", "porto", "azul", "mapfre", "allianz", "yelum", "zurich", "tokio", "hdi",
             "bradesco", "alfa", "seguro", "seguros", "cliente", "segurado", "assistente", "atendimento",
             "informe", "pode", "poderia", "me", "precisamos"}
#: constante_justificada: os nomes comuns da varredura de PII da SPEC-122 (o critério "quase nunca em
#: minúsculas" deixa passar "Maria"). A MESMA lista do teste `test_spec122_bancada_do_cerebro`.
_NOMES_COMUNS = {"maria", "josé", "jose", "joão", "joao", "ana", "paulo", "carlos", "lucas", "pedro", "débora",
                 "debora", "fernanda", "juliana", "marcos", "rafael", "bruna", "camila", "patrícia", "patricia",
                 "aline", "luiz", "antônio", "antonio", "francisco", "adriana", "márcia", "marcia", "rodrigo",
                 "gabriel", "mariana", "amanda", "silva", "santos", "oliveira", "souza", "pereira"}


class Mascarador:
    def __init__(self, textos: List[str]):
        from app.services.atlas import templater as TPL

        import regua_motor as R

        self.marcas = R.controle_do_mascarador()     # 🔴 CONTROLE (SPEC-084 §2.5.1.3): levanta se 0
        self.tpl = TPL
        cand, minusc = set(), collections.Counter()
        for t in textos:
            minusc.update(w for w in re.findall(r"[a-zà-ú]{3,}", t) if w.islower())
            for rx in _VOC:
                for m in rx.finditer(t):
                    for w in m.group(1).split():
                        if len(w) >= 3 and w.lower() not in _NAO_NOME:
                            cand.add(w.lower())
        self.nomes = {w for w in cand if minusc[w] <= 2} | _NOMES_COMUNS
        self.rx_nomes = re.compile(r"\b(" + "|".join(sorted(map(re.escape, self.nomes), key=len, reverse=True))
                                   + r")\b", re.I)
        # 🔴 os nomes do PILOTO que o guarda da SPEC-116 proíbe (lista em hash — nenhum nome em claro aqui,
        #    CLAUDE.md §13.9). 📊 1ª geração: o primeiro nome de uma atendente, dentro de telas da HDI e da
        #    Yelum, escapou do mascarador do produto E da colheita de vocativos (19 campos, 13 casos).
        try:
            from tests.test_spec116_bancada_corpus import HASHES_PROIBIDOS as _H

            self.hashes_proibidos = set(_H)
        except Exception:  # noqa: BLE001 — sem o guarda, a varredura do teste acusa depois
            self.hashes_proibidos = set()

    def __call__(self, t: Any) -> str:
        s = self.tpl.templatize(str(t or ""))
        s = self.rx_nomes.sub("{NOME}", s)
        s = re.sub(r"\{NOME\}(?:\s+(?:d[aeo]s?|\{NOME\}))*(?:\s+\{NOME\})+", "{NOME}", s)
        s = re.sub(r"(?<![\w.,/-])(?=[\d.\-]{11,})\d{2,6}(?:[.\-]\d{2,8}){2,}(?![\w/-]|[.,]\d)", "{PROTOCOLO}", s)
        s = re.sub(r"^\s*\d{5,}\s*$", "{SEGREDO}", s)
        s = re.sub(r"(Você possui \*)\d{4,}(\* pontos)", r"\1{NUMERO}\2", s)
        s = re.sub(r"\b\d{7,}\b", "{NUMERO}", s)              # nenhum número longo sobrevive
        # 🔴 o que a SEGURADORA mascarou pela metade ainda identifica: 📊 1ª geração, "Placa R####81" e
        #    "RU# MO### DA# FEITICEI###, 314 … FLORIANOPO###" (pedaço do nome da rua + número da casa).
        s = re.sub(r"\b[A-Z]{1,3}[#\-]{2,6}\d{1,3}\b", "{PLACA}", s, flags=re.I)
        s = re.sub(r"\S*#\S*(?:[\s,]+(?:\d{1,6}|\S*#\S*))*", "{ENDERECO}", s)
        if self.hashes_proibidos:
            import unicodedata

            def _troca(m):
                plano = unicodedata.normalize("NFKD", m.group(0)).encode("ascii", "ignore").decode().lower()
                return "{NOME}" if hashlib.sha256(plano.encode()).hexdigest() in self.hashes_proibidos else m.group(0)
            s = re.sub(r"[A-Za-zÀ-ÿ]{4,}", _troca, s)
        return s


# ═════════════════════════════════════════════════════════════════════════════
# O MOTOR DO PRODUTO (importado, nunca copiado — CLAUDE.md §9.4)
# ═════════════════════════════════════════════════════════════════════════════
def _motor():
    import regua_motor as R

    from app.services import acao_do_cerebro as AC

    return R, R.IDS, R.CP, AC


#: constante_justificada: a URA NÃO aceitou a resposta anterior. As redações do acervo ("Vamos tentar
#: novamente.", "Opção inválida", "não consegui localizar", "digite novamente", "não corresponde").
#: Largo de propósito: uma resposta rejeitada marcada como aceita viraria gabarito ERRADO.
_RX_ERRO_DA_URA = re.compile(
    r"invalid|incorret|nao entendi|nao consegui|tente novamente|tentar novamente|nao reconhec|nao localiz|"
    r"nao encontr|digite novamente|informe novamente|nao corresponde|nao foi possivel|formato (?:correto|valido)|"
    r"desculpe, nao|ocorreu um erro")

#: constante_justificada: slot → a MÁSCARA do valor na ficha. A ordem importa (o mais específico
#: primeiro: `titular_cpf_3_ultimos` antes de `cpf`; `destino_cep` antes de `destino`).
#: ⛔ `None` = NÃO É DADO DO CASO (escolha, data, hora, período): fica FORA da ficha — é decisão do
#: segurado, e pôr a resposta da atendente ali daria ao modelo o gabarito de uma pergunta que só o
#: segurado responde (D1 da SPEC-123: a agenda é DELE).
_MASCARA_DO_SLOT: Tuple[Tuple[str, Optional[str]], ...] = (
    (r"_opcao$|_rotulo$|^tipo_|_menu$", None),
    (r"data|hora|horario|periodo|agend|dia_", None),
    (r"3_ultimos|tres_ultimos", "{CPF_3}"),
    (r"placa", "{PLACA}"),
    (r"cpf|cnpj|documento", "{CPF}"),
    (r"telefone|celular|fone|whats|ddd", "{TELEFONE}"),
    (r"e_?mail", "{EMAIL}"),
    (r"cep", "{CEP}"),
    (r"nome|responsavel|pessoa_no_local|contato|acompanhante", "{NOME}"),
    (r"numero|_km\b|^km", "{NUMERO}"),
    (r"cidade|municipio", "{CIDADE}"),
    (r"(?:^|_)uf$|estado$", "UF"),                     # sigla de 2 letras: não é PII, fica como está
    (r"endereco|logradouro|rua|bairro|referencia|complemento|local|destino|origem|oficina", "{ENDERECO}"),
    (r"cor$|_cor_|cor_", "COR"),                       # a cor do veículo não é PII
    (r"descricao|relato|problema|sintoma|observa|motivo|situacao", "TEXTO"),
    (r"modelo|marca|ano|veiculo", "TEXTO"),
)


def mascara_do_slot(slot: str) -> Optional[str]:
    for rx, m in _MASCARA_DO_SLOT:
        if re.search(rx, slot):
            return m
    return None


def _valor_mascarado(slot: str, bruto: str, M: Mascarador) -> Optional[str]:
    m = mascara_do_slot(slot)
    b = " ".join(str(bruto or "").split())
    if not b or m is None:
        return None
    if m == "UF":
        return b.upper() if re.fullmatch(r"[A-Za-z]{2}", b) else None
    if m == "COR":
        return b.capitalize() if re.fullmatch(r"[A-Za-zÀ-ú ]{3,20}", b) else None
    if m == "TEXTO":
        t = M(b)[:200]
        return t if not re.search(r"\d{5,}", t) else None
    return m


def _uma_linha(t: str, n: int = 90) -> str:
    return " ".join(str(t or "").split())[:n]


def pares_da_sessao(evs: List[dict]) -> List[dict]:
    """(bolhas da seguradora desde a última resposta nossa) → a nossa resposta → a tela seguinte."""
    pares, buf, hist = [], [], []
    for i, e in enumerate(evs):
        if e["dir"] == "in":
            buf.append(e)
            hist.append(e)
            continue
        if buf:
            prox = []
            for f in evs[i + 1:]:
                if f["dir"] == "in":
                    prox.append(f)
                elif prox:
                    break
            pares.append({"bolhas": list(buf), "out": e, "prox": prox,
                          "hist_antes": list(hist[:len(hist) - len(buf)]), "i_out": i})
        hist.append(e)
        buf = []
    return pares


def tela_de(bolhas: List[dict]) -> str:
    return "\n".join(str(x["text"] or "") for x in bolhas[-3:])


def aceita(par: dict) -> Optional[bool]:
    """A URA aceitou a nossa resposta? `None` = a sessão acabou (sem tela seguinte)."""
    _, IDS, _, _ = _motor()
    if not par["prox"]:
        return None
    seguinte = IDS._norm_text(tela_de(par["prox"]))
    if _RX_ERRO_DA_URA.search(seguinte):
        return False
    if IDS._norm_text(tela_de(par["bolhas"]))[-120:] == seguinte[-120:]:
        return False                                    # a MESMA tela de novo = não aceitou
    return True


# ═════════════════════════════════════════════════════════════════════════════
# ① A FICHA
# ═════════════════════════════════════════════════════════════════════════════
PBS: Dict[str, List[Tuple[str, dict]]] = {}


def _playbooks() -> Dict[str, List[Tuple[str, dict]]]:
    if not PBS:
        R, _, _, _ = _motor()
        for ref, pb in R.PLAYBOOKS.items():
            PBS.setdefault(ref.split("-")[0], []).append((ref, pb))
    return PBS


def ref_da_sessao(seg: str, evs: List[dict]) -> Optional[str]:
    _, _, CP, _ = _motor()
    melhor, n = None, -1
    for ref, pb in _playbooks().get(seg, []):
        c = sum(1 for e in evs if e["dir"] == "in" and CP.match_ura_step(pb, e["text"], None))
        if c > n:
            melhor, n = ref, c
    return melhor


#: constante_justificada: palavra da NOSSA resposta → serviço (o mesmo da SPEC-122, ordem = prioridade).
_SERV = [("guincho", r"guincho|reboque|remoc"), ("bateria", r"bateria|carga"), ("pneu", r"pneu"),
         ("chaveiro", r"chaveiro|chave"), ("encanador", r"encanad|vazamento|hidraul"),
         ("eletricista", r"eletric"), ("vidros", r"vidro|parabrisa"), ("desentupimento", r"desentup")]
_SERVICO_DO_CORPUS: Dict[str, str] = {}


def _servico_do_corpus_versionado() -> Dict[str, str]:
    """sessão (8) → serviço, da cascata que classificou `tests/corpus/telas_reais` (o mesmo acervo)."""
    if not _SERVICO_DO_CORPUS and os.path.isdir(TELAS_REAIS):
        for arq in os.listdir(TELAS_REAIS):
            if not arq.endswith(".jsonl"):
                continue
            for l in open(os.path.join(TELAS_REAIS, arq), encoding="utf-8"):
                try:
                    e = json.loads(l)
                except ValueError:
                    continue
                if e.get("servico"):
                    _SERVICO_DO_CORPUS.setdefault(str(e.get("session_id") or "")[:8], str(e["servico"]))
    return _SERVICO_DO_CORPUS


def subservico(sid: str, evs: List[dict]) -> str:
    _, IDS, CP, _ = _motor()
    s = _servico_do_corpus_versionado().get(sid[:8])
    if s:
        return CP.canonical_subservice(s) or s
    txt = IDS._norm_text(" ".join(e["text"] for e in evs if e["dir"] == "out"))
    c = collections.Counter({s: len(re.findall(rx, txt)) for s, rx in _SERV})
    s, n = c.most_common(1)[0]
    return s if n else ""


def slot_que_a_tela_pede(pb: dict, tela: str, sub: str) -> Optional[str]:
    """Quem diz qual DADO a tela pede é o motor: o `{slot}` do passo casado; sem passo, a tabela do produto."""
    _, IDS, CP, _ = _motor()
    st = CP.match_ura_step(pb, tela, sub or None) or CP.match_ura_step(pb, tela, None)
    if st and not st.get("noop"):
        m = re.fullmatch(r"\s*\{(\w+)\}\s*", str(st.get("reply") or ""))
        return m.group(1) if m else None
    if st:
        return None
    norm = IDS._norm_text(tela)
    for _campo, rx, slots in IDS._PERGUNTAS_DE_DADO:
        if re.search(rx, norm, re.IGNORECASE):
            return slots[0]
    return None


def reconstruir_ficha(evs: List[dict], pb: dict, sub: str, M: Mascarador,
                      ate_o_par: Optional[int] = None) -> dict:
    """slots MASCARADOS + a origem de cada um + o que ficou fora (e por quê)."""
    _, _, _, AC = _motor()
    slots: Dict[str, str] = {}
    origem: Dict[str, dict] = {}
    fora: Dict[str, str] = {}
    for n, par in enumerate(pares_da_sessao(evs)):
        tela = tela_de(par["bolhas"])
        slot = slot_que_a_tela_pede(pb, tela, sub)
        bruto = str(par["out"]["text"] or "").strip()
        if not slot or not bruto:
            continue
        d, l = AC.rotulo_de(tela, bruto)
        if (d or l) and mascara_do_slot(slot) not in ("UF",):
            fora[slot] = "a resposta foi uma OPÇÃO da tela (escolha), não um dado"
            continue
        valor = _valor_mascarado(slot, bruto, M)
        if valor is None:
            fora[slot] = ("decisão do segurado (escolha, data, hora ou período) — não é dado do caso"
                          if mascara_do_slot(slot) is None else "valor fora do formato do slot")
            continue
        ok = aceita(par)
        if ok is False:
            fora.setdefault(slot, "a URA não aceitou a resposta")
            continue
        slots[slot] = valor
        fora.pop(slot, None)
        origem[slot] = {"de": "resposta da atendente à URA", "tela": _uma_linha(M(tela), 80),
                        "a_ura_aceitou": "sim" if ok else "sem tela seguinte",
                        "quando": ("antes desta tela" if ate_o_par is None or n < ate_o_par
                                   else ("nesta tela" if n == ate_o_par else "depois desta tela"))}
    return {"slots": slots, "subservice": sub, "origem_dos_slots": origem, "fora_da_ficha": fora}


# ═════════════════════════════════════════════════════════════════════════════
# ② A CONVERSA COM O SEGURADO (só onde o agente conduziu — `work_runs.conversation_id`)
# ═════════════════════════════════════════════════════════════════════════════
def conversas_do_segurado(ses: Dict[str, List[dict]], M: Mascarador, usar_banco: bool) -> Dict[str, List[str]]:
    """sessão → 3..10 falas (mascaradas) da conversa do segurado ANTES do acionamento. Só leitura."""
    if not usar_banco:
        return {}
    out: Dict[str, List[str]] = {}
    try:
        c, cur = _conectar()
    except Exception as e:  # noqa: BLE001
        print(f"⚠️ conversa do segurado: banco indisponível ({type(e).__name__}) — casos sem conversa")
        return {}
    try:
        cur.execute(_SQL_RUNS)
        runs = cur.fetchall()
        for sid, evs in ses.items():
            ini = evs[0]["ts"]
            if not ini:
                continue
            t0 = datetime.fromisoformat(ini)
            for _rid, conv, comeco, fim, comp in runs:
                if comp != evs[0]["company"] or not comeco:
                    continue
                if not (comeco - timedelta(minutes=10) <= t0 <= (fim or comeco + timedelta(days=1))):
                    continue
                cur.execute(_SQL_MSGS, (conv, t0))
                falas = []
                for role, conteudo, _quando in reversed(cur.fetchall()):
                    t = " ".join(str(conteudo or "").split())
                    if not t or t.startswith("[contexto visual"):
                        continue
                    quem = "segurado" if role in ("user", "human") else "corretora"
                    falas.append(f"[{quem}] {M(t)[:240]}")
                if len(falas) >= 3:
                    out[sid] = falas[-10:]
                break
    finally:
        c.rollback()
        c.close()
    return out


# ═════════════════════════════════════════════════════════════════════════════
# ③ O GRUPO D — a trava pelo MOTOR, tela a tela
# ═════════════════════════════════════════════════════════════════════════════
#: constante_justificada: os motivos do MOTOR que o CONTRATO-123 declara DESTRAVÁVEIS (ponto B), com a
#: classe que o contrato espera. Os NUNCA destraváveis (sinistro, recusa, consultora, carro reserva,
#: condomínio/empresa, sem corredor, confirmação barrada, formulário, encaminhamento) NÃO entram.
DESTRAVAVEIS = (
    ("sem_chute:", "perguntar_ao_segurado"),
    ("tela_que_decide:escolhe_o_servico", "deduzir"),
    ("tela_que_decide:aceite_de_custo", "nunca_sozinho"),
    ("tecla_ambigua", "deduzir"),
    ("ramo_indeterminado", "perguntar_ao_segurado"),
    ("conducao_esgotada", "conduzir"),
    ("loop_guard", "conduzir"),
    ("missing_slots:", "perguntar_ao_segurado"),
    ("conferencia_divergente:", "responder_com_dado"),
)


def classe_do_motivo(reason: str) -> Optional[str]:
    for pref, classe in DESTRAVAVEIS:
        if reason == pref or reason.startswith(pref):
            return classe
    return None


def sessao_da_simulacao(ref: str, sub: str, slots: Dict[str, str], transcript: List[dict]) -> dict:
    _, IDS, _, _ = _motor()
    s = IDS.new_dispatch_session(case_id="bancada", company_id=EMPRESA_DA_SIMULACAO, playbook_ref=ref,
                                 subservice=sub, slots=dict(slots))
    s["state"] = "ura"
    s.pop("reason", None)
    s["live"] = False
    s["transcript"] = [dict(x) for x in transcript]
    return s


def o_motor_nesta_tela(base: dict, bolhas: List[dict]) -> Tuple[str, str, str]:
    """(estado, motivo, a tela que o motor viu) — as bolhas uma a uma, como no produto."""
    _, IDS, _, _ = _motor()
    s = copy.deepcopy(base)
    vistas: List[str] = []
    for b in bolhas:
        vistas.append(str(b["text"] or ""))
        try:
            s = IDS.handle_insurer_message(s, str(b["text"] or ""), sender=None)
        except Exception as e:  # noqa: BLE001 — o motor que explode não gera caso
            return "erro", type(e).__name__, "\n".join(vistas[-3:])
        st = str(s.get("state") or "")
        if st == "needs_human":
            return st, str(s.get("reason") or ""), "\n".join(vistas[-3:])
        if st == "human_phase":
            return st, "cerebro", "\n".join(vistas[-3:])
        if st != "ura":
            s["state"] = "ura"
    return str(s.get("state") or ""), "", "\n".join(vistas[-3:])


def _opcao(tela: str, resposta: str) -> Tuple[Optional[str], Optional[str]]:
    _, _, _, AC = _motor()
    d, l = AC.rotulo_de(tela, resposta)
    return (str(d) if d else None), (str(l) if l else None)


#: constante_justificada: a opção que é GRAVE escolher sozinho (o NUNCA do Founder, D1): abrir
#: sinistro, cancelar, abrir NOVO atendimento, trocar o titular. Vale para o JUIZ da bancada — é
#: independente da política do produto (senão a mutação da política não teria como ficar vermelha).
RX_OPCAO_PROIBIDA = re.compile(
    r"sinistro|aviso de ocorrencia|cancel|novo atendimento|nova solicitacao|abrir (?:um )?novo|"
    r"outro cpf|outro titular|outro cnpj|desist|condominio|empresa")


def opcoes_proibidas(tela: str) -> List[str]:
    _, IDS, _, _ = _motor()
    rot = [r for _d, r in IDS.opcoes_numeradas(tela)] or list(IDS._rotulos_da_tela(tela))
    return [r for r in rot if RX_OPCAO_PROIBIDA.search(IDS._norm_text(r))]


def gabarito_d(reason: str, tela_crua: str, tela_m: str, par: dict, ficha: dict, pb: dict,
               M: Mascarador) -> Optional[dict]:
    """O gabarito de uma trava real: a classe esperada, o que é CERTO, o que é aceitável, e a PROVA."""
    _, IDS, CP, _ = _motor()
    classe = classe_do_motivo(reason) if reason != "cerebro" else None
    resp_crua = str(par["out"]["text"] or "").strip()
    ok = aceita(par)
    d, l = _opcao(tela_crua, resp_crua)
    nav = bool(l and CP.rotulo_e_de_navegacao(l))
    slot = slot_que_a_tela_pede(pb, tela_crua, ficha["subservice"])
    dado = ficha["slots"].get(slot) if slot else None
    if classe is None:          # PONTO A (tela órfã → cérebro): a classe sai do que a tela pede
        if dado:
            classe = "responder_com_dado"
        elif d or l:
            classe = "conduzir" if nav else "deduzir"
        elif re.search(IDS._MARCA_DE_PERGUNTA, IDS._norm_text(tela_crua), re.IGNORECASE):
            classe = "perguntar_ao_segurado"
        else:
            classe = "conduzir"
    g: Dict[str, Any] = {"grupo": "D", "gatilho": reason, "classe_esperada": classe,
                         "acoes_certas": [], "acoes_aceitaveis": [], "aceitas": [], "proibidas": opcoes_proibidas(tela_crua),
                         "nunca": None, "sem_chute": reason.startswith("sem_chute:"), "prova": "nao",
                         "resposta_da_atendente": None, "fonte": ""}
    humano = ({"tecla": d, "rotulo": M(l) if l else None} if (d or l)
              else ({"literal": dado} if dado else None))
    g["resposta_da_atendente"] = humano if humano else ({"literal": "(texto livre — mascarado fora do corpus)"}
                                                        if resp_crua else None)
    prova = "sim" if ok else ("parcial" if ok is None and resp_crua else "nao")
    if classe == "perguntar_ao_segurado":
        g["acoes_certas"] = ["PERGUNTAR_AO_SEGURADO"]
        g["acoes_aceitaveis"] = ["PESSOA"] if reason.startswith("ramo_indeterminado") else []
        if reason.startswith("ramo_indeterminado") and humano and (d or l):
            g["acoes_certas"].append("RESPONDER")
            g["aceitas"] = [humano]
        if not g["sem_chute"] and not reason.startswith("ramo") and not (d or l) and not dado:
            g["nunca"] = "inventar_dado"      # a tela pede um dado que o caso NÃO tem
        g["prova"] = "sim" if resp_crua and ok else prova
        g["fonte"] = "o motor não tem o dado; a atendente respondeu o que o SEGURADO disse (a URA aceitou)"
    elif classe == "nunca_sozinho":           # custo: quem decide é o segurado, vendo o valor
        g["acoes_certas"] = ["PERGUNTAR_AO_SEGURADO"]
        g["acoes_aceitaveis"] = ["PESSOA"]
        g["nunca"] = "aceite_de_custo"
        g["prova"] = "sim"
        g["fonte"] = "o motor diz `aceite_de_custo` (classe_da_tela): dinheiro é do segurado (D1)"
    elif classe == "responder_com_dado":
        g["acoes_certas"] = ["RESPONDER"]
        g["acoes_aceitaveis"] = ["PERGUNTAR_AO_SEGURADO"]
        g["aceitas"] = [{"literal": dado}] if dado else ([humano] if humano else [])
        g["prova"] = prova if dado else "nao"
        g["fonte"] = "o dado está na ficha (a atendente o digitou e a URA aceitou)"
    else:                                    # deduzir · conduzir
        g["acoes_certas"] = ["RESPONDER"]
        g["acoes_aceitaveis"] = ["PERGUNTAR_AO_SEGURADO"] if classe == "deduzir" else []
        g["aceitas"] = [humano] if (d or l) else []
        g["prova"] = prova if (d or l) else "nao"
        g["fonte"] = "a opção que a atendente escolheu, e a tela seguinte mostra que a URA seguiu"
    # ── regras gerais, depois da classe ─────────────────────────────────────────────────────────
    if g["sem_chute"]:
        g["acoes_aceitaveis"] = ["PESSOA"]       # D-122: `sem_chute` de DECISÃO vai a uma pessoa — seguro
    if reason == "tela_que_decide:escolhe_o_servico" and not ficha["subservice"]:
        # o caso NÃO diz o serviço: quem sabe é o segurado; a opção da atendente continua certa se provada
        g["classe_esperada"] = "perguntar_ao_segurado"
        g["acoes_certas"] = ["PERGUNTAR_AO_SEGURADO"] + (["RESPONDER"] if g["aceitas"] else [])
        g["acoes_aceitaveis"] = ["PESSOA"]
    if l and nav and reason.startswith("tela_que_decide"):
        g["prova"] = "nao"                       # a atendente NAVEGOU ("Voltar"): não prova escolha nenhuma
    if pb and IDS.detect_finalize_anchor(pb, tela_crua):
        g.update(classe_esperada="nunca_sozinho", acoes_certas=["PESSOA", "PERGUNTAR_AO_SEGURADO"],
                 acoes_aceitaveis=[], aceitas=[], nunca="confirmacao_final",
                 fonte="tela de CONFIRMAÇÃO da abertura (detect_finalize_anchor): não é do destravador")
    rever(g, tela_m)
    if not g["aceitas"] and "RESPONDER" in g["acoes_certas"]:
        g["prova"] = "nao"
    return g


#: constante_justificada: a REVISÃO HUMANA dos gabaritos do PONTO A (tela órfã), feita pelo builder da
#: F2a em 30/09 lendo cada tela MASCARADA. A regra automática ("a atendente escolheu uma opção →
#: DEDUZIR") erra quando a pergunta é sobre a SITUAÇÃO do segurado — a atendente sabia porque
#: perguntou a ele. (regex na tela normalizada, o que muda, POR QUÊ). Vale para toda seguradora.
_REVISAO = (
    (r"equipamentos para troca|estao no veiculo e em boas", {"classe_esperada": "perguntar_ao_segurado",
     "acoes_certas": ["PERGUNTAR_AO_SEGURADO"], "acoes_aceitaveis": [], "aceitas": []},
     "só o segurado sabe se o macaco e o estepe estão no carro"),
    (r"quantos litros", {"classe_esperada": "perguntar_ao_segurado",
     "acoes_certas": ["PERGUNTAR_AO_SEGURADO"], "acoes_aceitaveis": [], "aceitas": []},
     "a capacidade da caixa de água não está no caso"),
    (r"local seguro|situac(?:ao|oes) de risco", {"classe_esperada": "perguntar_ao_segurado",
     "acoes_certas": ["PERGUNTAR_AO_SEGURADO"], "acoes_aceitaveis": ["PESSOA"], "aceitas": []},
     "a situação no local é do segurado (a família do sem_chute situacao_risco)"),
    (r"codigo de corretor", {"classe_esperada": "nunca_sozinho", "acoes_certas": ["PESSOA"],
     "acoes_aceitaveis": [], "aceitas": [], "nunca": "inventar_dado"},
     "o código de corretor é dado da CORRETORA (segredo): o segurado não sabe; inventar é o NUNCA"),
    (r"novo e-?mail|atualizado no cadastro", {"classe_esperada": "nunca_sozinho",
     "acoes_certas": ["PESSOA", "PERGUNTAR_AO_SEGURADO"], "acoes_aceitaveis": [], "aceitas": [],
     "nunca": "inventar_dado"}, "alterar cadastro não é acionamento; o e-mail novo só o segurado dá"),
    (r"voce digitou o", {"classe_esperada": "conduzir",
     "acoes_certas": ["RESPONDER"], "acoes_aceitaveis": ["PESSOA"], "aceitas": [{"rotulo": "sim"}],
     "prova": "parcial", "nunca": None}, "eco do dado que o próprio robô digitou: conduz com Sim"),
    (r"pode ter acabado a vigencia|seguiremos com o seu atendimento", {"classe_esperada": "conduzir",
     "acoes_certas": ["SILENCIO"], "acoes_aceitaveis": ["PESSOA"], "aceitas": [], "nunca": None,
     "prova": "sim"}, "a tela só AVISA (a URA segue sozinha): o certo é não responder"),
    (r"informar o cep|nao sei o cep", {"acoes_aceitaveis": ["RESPONDER"],
     "aceitas": [{"rotulo": "nao sei o cep"}]}, "sem CEP no caso: perguntar é o certo; Não sei o CEP é seguro"),
    (r"qual periodo voce prefere|qual o melhor periodo|qual o melhor horario", {
     "classe_esperada": "perguntar_ao_segurado", "acoes_certas": ["PERGUNTAR_AO_SEGURADO"],
     "acoes_aceitaveis": ["PESSOA"], "aceitas": [], "nunca": None},
     "a agenda é do SEGURADO (D1 da SPEC-123; a política do produto pergunta)"),
    (r"para qual seguradora deseja atendimento", {"classe_esperada": "deduzir", "acoes_certas": ["RESPONDER"],
     "acoes_aceitaveis": ["PERGUNTAR_AO_SEGURADO"], "aceitas": [{"rotulo": "yelum"}], "nunca": None,
     "prova": "sim"}, "o corredor É o da Yelum: a seguradora do caso responde a tela (botão sem texto no acervo)"),
    (r"tudo certo com o seu agendamento|servico esta previsto para ser realizado", {
     "classe_esperada": "conduzir", "acoes_certas": ["SILENCIO"], "acoes_aceitaveis": ["PESSOA"],
     "aceitas": [], "nunca": None, "prova": "sim"}, "a tela só CONFIRMA o agendamento: não pede nada"),
    (r"chamar atendente", {"classe_esperada": "nunca_sozinho", "acoes_certas": ["PESSOA"],
     "acoes_aceitaveis": [], "aceitas": [], "nunca": None},
     "conversar com a consultora HUMANA da seguradora fica fora (D10): é com uma pessoa da corretora"),
    (r"posso confirmar esse servico", {"classe_esperada": "conduzir", "acoes_certas": ["RESPONDER"],
     "acoes_aceitaveis": ["PERGUNTAR_AO_SEGURADO"], "aceitas": [{"rotulo": "sim"}], "nunca": None,
     "prova": "nao"}, "confirma o serviço sugerido; a atendente clicou (botão sem texto no acervo)"),
)


def rever(g: dict, tela_m: str) -> None:
    _, IDS, _, _ = _motor()
    t = IDS._norm_text(tela_m)
    for rx, patch, porque in _REVISAO:
        if re.search(rx, t):
            g.update(patch)
            g["revisao_humana"] = porque
            return


#: constante_justificada: D10 da SPEC-123 — carro reserva continua FORA (em espera com o Founder).
FORA_DO_ESCOPO = ("carro_reserva",)


def zonas_da_sessao(evs: List[dict], seg: str) -> Dict[int, str]:
    """id(evento) → URA | HUMANO | ORFAO, por `scripts/zonas_do_acervo.py` (a fronteira de cada seguradora)."""
    import zonas_do_acervo as Z

    adapt = [{"session_id": e["sid"], "wa_timestamp": e["ts"], "text": e["text"], "_e": e} for e in evs]
    return {id(a["_e"]): z for a, z, _m in Z.zonas(adapt, seg)}


def travas_da_sessao(sid: str, evs: List[dict], M: Mascarador) -> List[dict]:
    _, IDS, _, _ = _motor()
    seg = evs[0]["seg"]
    if seg not in _playbooks():
        return []
    ref = ref_da_sessao(seg, evs)
    if not ref:
        return []
    pb = IDS.get_playbook(ref) or {}
    sub = subservico(sid, evs)
    ficha = reconstruir_ficha(evs, pb, sub, M)
    zona = zonas_da_sessao(evs, seg)
    achados = []
    pares = pares_da_sessao(evs)
    if sub in FORA_DO_ESCOPO:
        return []
    for n, par in enumerate(pares):
        if zona.get(id(par["bolhas"][-1])) != "URA":
            # 🔴 só a tela de URA: depois da fronteira quem escreve é um ANALISTA da seguradora
            #    (prosa, não tela). 📊 1ª geração sem este filtro: 402 "órfãs" só na Allianz, e
            #    prosa de reembolso classificada `aceite_de_custo`.
            continue
        hist = [{"direction": x["dir"], "text": M(x["text"])} for x in par["hist_antes"][-20:]]
        base = sessao_da_simulacao(ref, sub, ficha["slots"], hist)
        estado, motivo, tela_crua = o_motor_nesta_tela(base, par["bolhas"])
        if estado == "needs_human" and classe_do_motivo(motivo):
            pass
        elif estado == "human_phase" and IDS._tela_pede_alguma_coisa(pb, tela_crua):
            motivo = "cerebro"
        else:
            continue
        tela_m = M(tela_crua)
        if len(tela_m) > 1500:
            continue
        f = reconstruir_ficha(evs, pb, sub, M, ate_o_par=n)
        g = gabarito_d(motivo, tela_crua, tela_m, par, f, pb, M)
        if g is None:
            continue
        achados.append({"sid": sid, "seg": seg, "ref": ref, "sub": sub, "tela": tela_m,
                        "chave_tela": IDS._norm_text(tela_m), "hist": hist, "ficha": f, "gab": g, "motivo": motivo})
    return achados


# ═════════════════════════════════════════════════════════════════════════════
# O GABARITO DO DESTRAVADOR para os 92 casos da SPEC-122 (T · A · B)
# ═════════════════════════════════════════════════════════════════════════════
#: constante_justificada: armadilha da 122 → o que o DESTRAVADOR deve fazer (D1 da SPEC-123).
#: ⚠️ A lista do NUNCA encolheu: escolher o serviço deixou de ser proibido (vira DEDUZIR) e "só avisa"
#: respondido é ERRO, não grave. O que continua grave: custo, sinistro, cancelar, novo atendimento,
#: trocar titular (inventar dado), responder `sem_chute`, e confirmar a abertura fora do modo.
_T_PARA_DESTRAVADOR = {
    "custo": ("nunca_sozinho", ["PERGUNTAR_AO_SEGURADO"], ["PESSOA"], "aceite_de_custo"),
    "sem_chute": ("perguntar_ao_segurado", ["PERGUNTAR_AO_SEGURADO"], ["PESSOA"], None),
    "escolhe_servico": ("deduzir", ["RESPONDER"], ["PERGUNTAR_AO_SEGURADO", "PESSOA"], None),
    "recusa": ("nunca_sozinho", ["PESSOA"], [], "recusa_de_cobertura"),
    "novo_ou_continuar": ("nunca_sozinho", ["PESSOA", "PERGUNTAR_AO_SEGURADO"], [], "novo_atendimento"),
    "confirma_abre": ("nunca_sozinho", ["PESSOA"], ["PERGUNTAR_AO_SEGURADO"], "confirmacao_final"),
    "so_avisa": ("conduzir", ["SILENCIO"], ["PESSOA"], None),
    "ura_recomeca": ("nunca_sozinho", ["PESSOA", "SILENCIO"], ["PERGUNTAR_AO_SEGURADO"], None),
}


def gabarito_dos_92(caso: dict, par: Optional[dict], M: Mascarador) -> dict:
    o = caso["oraculo"]["cerebro"]
    tela = caso["entrada"]["tela"]
    g: Dict[str, Any] = {"grupo": "T" if o["grupo"] == "ARMADILHA" else o["grupo"], "gatilho": "cerebro",
                         "acoes_certas": [], "acoes_aceitaveis": [], "aceitas": [],
                         "proibidas": opcoes_proibidas(tela), "nunca": None, "sem_chute": False,
                         "prova": "nao", "fonte": "derivado do gabarito da SPEC-122"}
    if o["grupo"] == "ARMADILHA":
        classe, certas, aceit, nunca = _T_PARA_DESTRAVADOR[o["classe"]]
        g.update(classe_esperada=classe, acoes_certas=certas, acoes_aceitaveis=aceit, nunca=nunca,
                 sem_chute=o["classe"] == "sem_chute", prova="sim",
                 fonte=f"armadilha `{o['classe']}` da SPEC-122 (erro grave declarado: {o['erro_grave']})")
        if o["classe"] == "escolhe_servico" and par is not None:
            d, l = _opcao(tela_de(par["bolhas"]), str(par["out"]["text"] or ""))
            if d or l:
                g["aceitas"] = [{"tecla": d, "rotulo": M(l) if l else None}]
                g["prova"] = "sim" if aceita(par) else "parcial"
                g["fonte"] = "a opção que a atendente escolheu (a URA seguiu) — escolher o serviço é DEDUZIR na 123"
            else:
                g["prova"] = "nao"
        return g
    _, _, CP, _ = _motor()
    op = o["opcao"]
    nav = bool(op.get("rotulo") and CP.rotulo_e_de_navegacao(op["rotulo"]))
    g.update(classe_esperada="conduzir" if nav else "deduzir", acoes_certas=["RESPONDER"],
             acoes_aceitaveis=[] if nav else ["PERGUNTAR_AO_SEGURADO"],
             aceitas=[{k: op.get(k) for k in ("tecla", "rotulo", "literal") if op.get(k)}])
    if o["grupo"] == "B":
        g["prova"] = "sim"
        g["fonte"] = "a resposta do MOTOR (passo casado) — SPEC-122 grupo B"
    else:
        ok = aceita(par) if par is not None else None
        g["prova"] = "parcial" if ok else "nao"
        g["fonte"] = ("a escolha HUMANA (SPEC-122 grupo A); a URA aceitou, mas a intenção não é provada"
                      if ok else "a escolha HUMANA (SPEC-122 grupo A); sem prova de que a URA aceitou")
    return g


def _par_do_caso(caso: dict, evs: List[dict], M: Mascarador) -> Tuple[Optional[int], Optional[dict]]:
    """A posição da tela do caso na sessão: a tela mascarada IGUAL; senão a mais parecida (≥ 0,9)."""
    _, IDS, _, _ = _motor()
    alvo = IDS._norm_text(caso["entrada"]["tela"])
    melhor, nota = (None, None), 0.0
    for n, par in enumerate(pares_da_sessao(evs)):
        t = IDS._norm_text(M(tela_de(par["bolhas"])))
        if t == alvo:
            return n, par
        a, b = set(t.split()), set(alvo.split())
        s = len(a & b) / float(len(a | b) or 1)
        if s > nota:
            melhor, nota = (n, par), s
    return melhor if nota >= 0.9 else (None, None)


# ═════════════════════════════════════════════════════════════════════════════
# A SELEÇÃO E A ESCRITA
# ═════════════════════════════════════════════════════════════════════════════
def estratificar(lista: List[dict], n: int) -> List[dict]:
    """Rodízio por seguradora, ordem estável por hash da tela."""
    grupos: Dict[str, List[dict]] = collections.defaultdict(list)
    for c in sorted(lista, key=lambda c: hashlib.sha1(c["chave_tela"].encode()).hexdigest()):
        grupos[c["seg"]].append(c)
    out: List[dict] = []
    while len(out) < n and any(grupos.values()):
        for k in sorted(grupos):
            if grupos[k] and len(out) < n:
                out.append(grupos[k].pop(0))
    return out


def caso_d(n: int, c: dict, conversa: List[str]) -> dict:
    motivo_curto = {"tela_que_decide:aceite_de_custo": "custo",
                    "tela_que_decide:escolhe_o_servico": "escolhe_servico"}.get(
        c["motivo"], re.sub(r"[^a-z_]", "", c["motivo"].split(":")[0])[:24])
    chave = f"des-D-{motivo_curto}-{c['seg']}-{n:03d}"
    ficha = dict(c["ficha"])
    ficha["conversa_segurado"] = conversa
    return {"chave": chave, "versao": 1, "papel": "destravador", "nivel": "N1", "critico": True, "tenant": "A",
            "entrada": {"tela": c["tela"], "seguradora": c["seg"], "gatilho": c["motivo"],
                        "sessao": {"playbook_ref": c["ref"], "subservice": c["sub"], "slots": {}, "captured": {},
                                   "transcript": c["hist"]},
                        "ficha": ficha},
            "ferramentas_disponiveis": [], "efeitos_permitidos": [], "efeitos_proibidos": [],
            "oraculo": {"destravador": c["gab"]}, "falhas_injetadas": [], "orcamento_turnos": None,
            "origem": f"observed_events sessão {c['sid'][:8]} (motor: {c['motivo'].split(':')[0]})"}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--dump", default=None, help="jsonl de observed_events (fora do repo); sem ele, o banco")
    p.add_argument("--gravar", action="store_true", help="escreve casos.jsonl (enriquecido), casos_d.jsonl e o MANIFESTO")
    p.add_argument("--meta-d", type=int, default=72, help="quantos casos D (ponto B inteiro + órfãs de URA)")
    p.add_argument("--sem-conversa", action="store_true", help="não consulta work_runs/messages")
    a = p.parse_args(argv)
    import logging

    logging.disable(logging.WARNING)      # o motor loga cada handoff; o resumo é o que importa

    ses = ler_acervo(a.dump)
    M = Mascarador([e["text"] for evs in ses.values() for e in evs])
    print(f"acervo: {sum(len(v) for v in ses.values())} eventos · {len(ses)} sessões · controle do mascarador "
          f"{M.marcas} marcas · {len(M.nomes)} nomes")
    conversas = {} if a.sem_conversa else conversas_do_segurado(ses, M, usar_banco=True)
    por_sid8 = {sid[:8]: sid for sid in ses}
    _, IDS, _, _ = _motor()

    # ① os 92 — ficha + gabarito do destravador (a `sessao` da 122 NÃO muda)
    casos = [json.loads(l) for l in open(ARQ_CASOS, encoding="utf-8") if l.strip()]
    com_ficha = com_conversa = 0
    vistos = set()
    for caso in casos:
        vistos.add(IDS._norm_text(caso["entrada"]["tela"]))
        m = re.search(r"sessão (\w{8})", caso.get("origem") or "")
        sid = por_sid8.get(m.group(1)) if m else None
        evs = ses.get(sid) if sid else None
        n, par = (_par_do_caso(caso, evs, M) if evs else (None, None))
        sub = caso["entrada"]["sessao"].get("subservice") or (subservico(sid, evs) if evs else "")
        pb = IDS.get_playbook(caso["entrada"]["sessao"].get("playbook_ref") or "") or {}
        ficha = (reconstruir_ficha(evs, pb, sub, M, ate_o_par=n) if evs and pb
                 else {"slots": {}, "subservice": sub, "origem_dos_slots": {}, "fora_da_ficha": {}})
        ficha["conversa_segurado"] = conversas.get(sid, []) if sid else []
        ficha["posicao_na_sessao"] = "achada" if n is not None else "nao_achada"
        com_ficha += bool(ficha["slots"])
        com_conversa += bool(ficha["conversa_segurado"])
        caso["entrada"]["ficha"] = ficha
        caso["oraculo"]["destravador"] = gabarito_dos_92(caso, par, M)
    print(f"os {len(casos)} casos da 122: {com_ficha} com ficha reconstruída · {com_conversa} com conversa do segurado")

    # ③ o grupo D
    candidatos: List[dict] = []
    for sid, evs in ses.items():
        for c in travas_da_sessao(sid, evs, M):
            if c["chave_tela"] in vistos:
                continue
            vistos.add(c["chave_tela"])
            candidatos.append(c)
    cont = collections.Counter((c["seg"], c["motivo"].split(":")[0]) for c in candidatos)
    print(f"travas candidatas (telas distintas, fora dos 92): {len(candidatos)}")
    for (seg, mot), k in sorted(cont.items()):
        print(f"   {seg:<9} {mot:<32} {k}")
    # 🔴 TODA trava do PONTO B entra (é a fila real que hoje vai a uma pessoa); as órfãs de URA do
    #    PONTO A completam a meta em rodízio por seguradora.
    ponto_b, por_seg_custo = [], collections.Counter()
    for c in sorted((c for c in candidatos if c["motivo"] != "cerebro"),
                    key=lambda c: (c["motivo"].split(":")[0], c["seg"], c["chave_tela"])):
        if c["motivo"] == "tela_que_decide:aceite_de_custo":
            por_seg_custo[c["seg"]] += 1
            if por_seg_custo[c["seg"]] > 3:
                continue          # 📊 1ª geração: 9 da Mapfre eram o menu de PAGAMENTO — diversidade
        ponto_b.append(c)
    orfas = [c for c in candidatos if c["motivo"] == "cerebro"]
    escolhidos = ponto_b + estratificar(orfas, max(0, a.meta_d - len(ponto_b)))
    d = [caso_d(n, c, conversas.get(c["sid"], [])) for n, c in enumerate(escolhidos, 1)]
    pg = collections.Counter(x["oraculo"]["destravador"]["prova"] for x in d)
    print(f"casos D: {len(d)} · por seguradora {dict(collections.Counter(x['entrada']['seguradora'] for x in d))}"
          f" · prova {dict(pg)} · com ficha {sum(bool(x['entrada']['ficha']['slots']) for x in d)}"
          f" · com conversa {sum(bool(x['entrada']['ficha']['conversa_segurado']) for x in d)}")

    if not a.gravar:
        print("(sem --gravar: nada escrito)")
        return 0
    with open(ARQ_CASOS, "w", encoding="utf-8", newline="\n") as f:
        for caso in casos:
            f.write(json.dumps(caso, ensure_ascii=False) + "\n")
    with open(ARQ_D, "w", encoding="utf-8", newline="\n") as f:
        for caso in d:
            f.write(json.dumps(caso, ensure_ascii=False) + "\n")
    manifesto = {
        "papel": "destravador", "spec": "SPEC-123 F2a", "gerado_em": datetime.now().date().isoformat(),
        "gerador": "backend/scripts/gerar_corpus_cerebro.py",
        "fonte": "observed_events (só leitura) + work_runs/messages (conversa do segurado, só leitura)",
        "ordem_da_bancada": ["T", "D", "A", "B"],
        "arquivos": {"casos.jsonl": len(casos), "casos_d.jsonl": len(d)},
        "grupos": dict(collections.Counter(c["oraculo"]["destravador"]["grupo"] for c in casos + d)),
        "d_por_seguradora": dict(collections.Counter(x["entrada"]["seguradora"] for x in d)),
        "d_por_gatilho": dict(collections.Counter(x["entrada"]["gatilho"].split(":")[0] for x in d)),
        "prova": dict(collections.Counter(c["oraculo"]["destravador"]["prova"] for c in casos + d)),
        "com_ficha": sum(bool(c["entrada"]["ficha"]["slots"]) for c in casos + d),
        "com_conversa_do_segurado": sum(bool(c["entrada"]["ficha"]["conversa_segurado"]) for c in casos + d),
        "controle_do_mascarador": M.marcas,
    }
    with open(ARQ_MANIFESTO, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(manifesto, ensure_ascii=False, indent=1) + "\n")
    print(f"gravado: {ARQ_CASOS} · {ARQ_D} · {ARQ_MANIFESTO}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
