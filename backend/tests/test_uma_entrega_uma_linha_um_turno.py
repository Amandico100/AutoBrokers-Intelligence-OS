# -*- coding: utf-8 -*-
r"""G9 — UMA ENTREGA = UMA LINHA = UM TURNO. SPEC-EXTRA-001.2 BLOCO E1.

🔴 **O que este guarda afirma, e sobre QUE motor.**

```
payload_do_pipeline        a forma da chave                          (webhook.py, PURA)
e_duplicata_do_banco       23505 é acerto, nao falha                 (webhook.py, PURA)
gravar_mensagem_do_pipeline  o UNICO escritor de `messages` do pipeline (webhook.py)
```

📊 O indice unico parcial `messages_espelho_sem_duplicata_uidx` existe desde
06/08/2026 sobre `(conversation_id, payload->>'wa_message_id')`
(`20260806_02_espelho_sem_duplicata.sql:41-43`) — e as linhas do pipeline
nasciam **sem `payload`**, logo fora do indice. O espelho ja gravava a chave e ja
tratava o 23505; o pipeline, nao.

```
 [GE1a] A MESMA ENTREGA 2x   1 linha em `messages`, e a 2a devolve "ja_estava"
 [GE1b] SEM ID               a linha entra assim mesmo, sem chave e sem erro
 [GE1c] O CONTROLE           erro que NAO e duplicata SOBE (o escritor nao engole)
 [GE1d] O TENANT             nenhum `wa_message_id` sob dois `company_id` com o
                             MESMO papel — e o PAR: papeis OPOSTOS sao legitimos
 [GE1e] QUEM E O ESCRITOR    os dois inserts do pipeline passam pelo escritor unico
```

🔴 **GE1d e a invariante que NAO se escreve.** 📊 Medido em 14/09/2026: **157**
`wa_message_id` repetidos, **0** na mesma conversa, **127** entre corretoras,
**0** com o mesmo papel. Os 127 sao as DUAS PONTAS da mesma conversa entre
linhas das proprias corretoras (Resulta <-> AutoFleet <-> Amandus): o WhatsApp da
um id GLOBAL, o espelho do remetente grava `assistant` e o do destinatario grava
`user`. ⛔ A invariante ingenua *"o mesmo id nunca sob dois company_id"* e
**falsa por construcao** — escreve-la seria fabricar um vazamento que nao existe.
O que este guarda afirma e o vazamento de verdade: **mesmo papel nas duas pontas**.

⛔ SEGURANCA: sem rede, sem banco, sem Redis. Telefones e ids 100% sinteticos.

Rodar (de dentro de `backend/`):
    PYTHONIOENCODING=utf-8 python tests/test_uma_entrega_uma_linha_um_turno.py
    ... --so GE1a   ·   ... --mutar   ·   ... --mutar M-E1a
"""
from __future__ import annotations

import ast
import asyncio
import io
import os
import shutil
import subprocess
import sys
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # .../backend
WEBHOOK = os.path.join(RAIZ, "app", "api", "webhook.py")
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
os.environ["SEM_REDE"] = "1"

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
        _p("  [FALHOU] %s" % nome + ("\n         %s" % str(detalhe)[:700] if detalhe else ""))
    return bool(cond)


# ===========================================================================
# O CARREGADOR — as funcoes REAIS do webhook.py, sem importar o modulo
#
# 📊 `import app.api.webhook` custa ~77 s (medido em 08/09/2026). Um teste que o
# importasse seria um teste que ninguem roda. A forma e a mesma de
# `test_midia_e_concorrencia_do_webhook.py:61-89`: os NOS REAIS da AST, byte a
# byte o que vai para producao. Editar `webhook.py` muda o que este teste executa.
# ===========================================================================
def carregar_do_fonte(caminho, nomes, extras=None):
    fonte = io.open(caminho, encoding="utf-8").read()
    arvore = ast.parse(fonte)
    escolhidos = []
    for no in arvore.body:
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)) and no.name in nomes:
            escolhidos.append(no)
    achados = {n.name for n in escolhidos}
    faltando = set(nomes) - achados
    check("todos os nomes pedidos existem em %s" % os.path.basename(caminho),
          not faltando, "sumiram: %s" % sorted(faltando))
    modulo = ast.Module(body=escolhidos, type_ignores=[])
    ns = {"__name__": "webhook_recortado", "asyncio": asyncio,
          "Optional": __import__("typing").Optional, "Any": __import__("typing").Any}
    ns.update(extras or {})
    exec(compile(ast.fix_missing_locations(modulo), caminho, "exec"), ns)  # noqa: S102
    return ns


ESPELHO_PY = os.path.join(RAIZ, "app", "services", "atlas", "espelho_chat.py")

MOTOR = carregar_do_fonte(
    WEBHOOK, ["payload_do_pipeline", "e_duplicata_do_banco",
              "gravar_mensagem_do_pipeline"])


# ===========================================================================
# O DUBLE DO BANCO — ele SIMULA o indice unico parcial, e nada mais
# ===========================================================================
class _ErroDoPostgrest(Exception):
    pass


class _Tabela:
    def __init__(self, banco, nome):
        self.banco = banco
        self.nome = nome
        self._linha = None
        self._filtros = {}
        self._contem = None
        self._lendo = False

    def insert(self, linha):
        self._linha = dict(linha)
        return self

    # --- leitura: o que a consulta de `wa_message_ids` precisa (J7) --------
    def select(self, *_a, **_k):
        self._lendo = True
        return self

    def eq(self, campo, valor):
        self._filtros[campo] = valor
        return self

    def contains(self, caminho, valores):
        self._contem = (caminho, list(valores or []))
        return self

    def limit(self, _n):
        return self

    def _ler(self):
        achadas = []
        for l in (self.banco.linhas.get(self.nome) or []):
            if any(l.get(k) != v for k, v in self._filtros.items()):
                continue
            if self._contem:
                caminho, valores = self._contem
                campo = str(caminho).split(">")[-1]
                lista = (l.get("payload") or {}).get(campo) or []
                if not all(v in lista for v in valores):
                    continue
            achadas.append(l)
        return _Resposta(achadas)

    def execute(self):
        if self._lendo and self._linha is None:
            return self._ler()
        linha = self._linha or {}
        if self.nome == "messages":
            chave = (linha.get("conversation_id"),
                     (linha.get("payload") or {}).get("wa_message_id"))
            # 🔴 O indice e PARCIAL: `WHERE payload->>'wa_message_id' IS NOT NULL`.
            #    Linha sem chave NAO colide com nada — e e por isso que a
            #    resposta da IA, hoje sem id, nao ganha dedupe (GE1b).
            if chave[1] is not None and chave in self.banco.chaves:
                raise _ErroDoPostgrest(
                    '{"code":"23505","message":"duplicate key value violates '
                    'unique constraint \\"messages_espelho_sem_duplicata_uidx\\""}')
            if chave[1] is not None:
                self.banco.chaves.add(chave)
        if self.banco.explodir:
            raise _ErroDoPostgrest(self.banco.explodir)
        self.banco.linhas.setdefault(self.nome, []).append(linha)
        return self


class _Resposta:
    def __init__(self, data):
        self.data = data


class BancoDuble:
    def __init__(self, explodir=None):
        self.linhas = {}
        self.chaves = set()
        self.explodir = explodir

    def table(self, nome):
        return _Tabela(self, nome)


ENTREGA = {"conversation_id": "conv-a", "role": "user", "content": "oi",
           "type": "text"}
ID_DA_META = "wamid.SINTETICO0001"


# ===========================================================================
# OS GATES
# ===========================================================================
def ge1a():
    _p("\n[GE1a] a MESMA entrega duas vezes -> UMA linha, e a 2a e 'ja_estava'")
    banco = BancoDuble()

    async def _rodar():
        a = await MOTOR["gravar_mensagem_do_pipeline"](
            banco, dados=dict(ENTREGA), wa_message_id=ID_DA_META, direcao="in")
        b = await MOTOR["gravar_mensagem_do_pipeline"](
            banco, dados=dict(ENTREGA), wa_message_id=ID_DA_META, direcao="in")
        return a, b

    a, b = asyncio.run(_rodar())
    linhas = banco.linhas.get("messages") or []
    check("a 1a gravou", a == "gravada", a)
    check("a 2a nao levantou e disse 'ja_estava'", b == "ja_estava", b)
    check("UMA linha em `messages`, nao duas", len(linhas) == 1, len(linhas))
    check("a linha carrega a chave, a origem e a direcao",
          (linhas[0].get("payload") or {}) == {
              "origem": "agente", "direcao": "in", "wa_message_id": ID_DA_META},
          linhas[0].get("payload"))

    # 🔴 O PAR: entrega DIFERENTE, na mesma conversa, continua entrando. Sem ele
    #    este gate ficaria verde com um escritor que nunca grava nada.
    banco2 = BancoDuble()

    async def _par():
        await MOTOR["gravar_mensagem_do_pipeline"](
            banco2, dados=dict(ENTREGA), wa_message_id=ID_DA_META, direcao="in")
        await MOTOR["gravar_mensagem_do_pipeline"](
            banco2, dados=dict(ENTREGA), wa_message_id="wamid.SINTETICO0002",
            direcao="in")

    asyncio.run(_par())
    check("PAR: dois ids DIFERENTES -> duas linhas",
          len(banco2.linhas.get("messages") or []) == 2,
          len(banco2.linhas.get("messages") or []))


def ge1b():
    _p("\n[GE1b] sem id do provider: a linha entra, SEM chave e SEM erro")
    banco = BancoDuble()

    async def _rodar():
        return await MOTOR["gravar_mensagem_do_pipeline"](
            banco, dados={"conversation_id": "conv-a", "role": "assistant",
                          "content": "ok"},
            wa_message_id=None, direcao="out")

    r = asyncio.run(_rodar())
    linhas = banco.linhas.get("messages") or []
    check("gravou", r == "gravada" and len(linhas) == 1, (r, len(linhas)))
    payload = (linhas[0].get("payload") or {}) if linhas else {}
    check("o payload tem origem e direcao",
          payload.get("origem") == "agente" and payload.get("direcao") == "out",
          payload)
    check("⛔ e NAO inventou `wa_message_id`", "wa_message_id" not in payload, payload)

    # 📊 O estado declarado de 14/09/2026: `whatsapp_service.send_message` devolve
    # `bool`, nao `SendResult`, e fatia em BALOES (N ids por envio). Enquanto o id
    # nao atravessar a fachada, a resposta da IA fica fora do indice — e a rede de
    # seguranca continua sendo `e_a_nossa_propria_voz` + `_eco_do_dashboard`.
    # ⛔ Este gate AFIRMA a limitacao em vez de escondê-la (P-E0012-02).
    banco2 = BancoDuble()

    async def _duas_sem_chave():
        await MOTOR["gravar_mensagem_do_pipeline"](
            banco2, dados={"conversation_id": "conv-a", "role": "assistant",
                           "content": "ok"}, wa_message_id=None, direcao="out")
        await MOTOR["gravar_mensagem_do_pipeline"](
            banco2, dados={"conversation_id": "conv-a", "role": "assistant",
                           "content": "ok"}, wa_message_id=None, direcao="out")

    asyncio.run(_duas_sem_chave())
    check("DECLARADO: sem chave nao ha dedupe — duas linhas entram",
          len(banco2.linhas.get("messages") or []) == 2,
          len(banco2.linhas.get("messages") or []))


def ge1c():
    _p("\n[GE1c] O CONTROLE — erro que NAO e duplicata SOBE")
    banco = BancoDuble(explodir='{"code":"08006","message":"connection failure"}')

    async def _rodar():
        return await MOTOR["gravar_mensagem_do_pipeline"](
            banco, dados=dict(ENTREGA), wa_message_id="wamid.SINTETICO0003",
            direcao="in")

    subiu = False
    try:
        asyncio.run(_rodar())
    except _ErroDoPostgrest:
        subiu = True
    check("banco fora do ar NAO e tratado como dedupe", subiu,
          "o escritor engoliu um erro que nao era 23505")
    check("`e_duplicata_do_banco` separa os dois casos",
          MOTOR["e_duplicata_do_banco"]('{"code":"23505"}')
          and MOTOR["e_duplicata_do_banco"]("duplicate key value")
          and not MOTOR["e_duplicata_do_banco"]('{"code":"08006"}'))


# ---------------------------------------------------------------------------
# GE1d — A INVARIANTE DE TENANT, sobre uma fixture de GRUPOS
# ---------------------------------------------------------------------------
#: ⛔ 100% SINTETICO. As empresas sao "A"/"B", nunca UUID de corretora; os ids
#: sao `wamid.SINTETICO*`. A FORMA e a do acervo medido em 14/09/2026.
GRUPOS = [
    # as duas pontas da mesma conversa entre linhas das proprias corretoras:
    # papeis OPOSTOS. 📊 127 grupos assim, e nenhum e vazamento.
    {"id": "wamid.SINTETICO1001", "pontas": [("A", "assistant"), ("B", "user")]},
    {"id": "wamid.SINTETICO1002", "pontas": [("A", "user"), ("B", "assistant")]},
    # a mensagem normal: uma ponta so.
    {"id": "wamid.SINTETICO1003", "pontas": [("A", "user")]},
]

#: 🔴 O grupo que NAO pode existir: o MESMO papel sob duas corretoras. Se ele
#: aparecer no acervo, a corretora B esta lendo a mensagem que o segurado
#: mandou para a A.
GRUPO_DE_VAZAMENTO = {"id": "wamid.SINTETICO9999",
                      "pontas": [("A", "user"), ("B", "user")]}


def violacoes_de_tenant(grupos):
    """Grupos em que o MESMO papel aparece sob dois `company_id`."""
    ruins = []
    for grupo in grupos:
        por_papel = {}
        for empresa, papel in grupo["pontas"]:
            por_papel.setdefault(papel, set()).add(empresa)
        if any(len(e) > 1 for e in por_papel.values()):
            ruins.append(grupo["id"])
    return ruins


def ge1d():
    _p("\n[GE1d] o tenant: nenhum `wa_message_id` sob dois company_id com o MESMO papel")
    check("o acervo sintetico (papeis OPOSTOS) esta limpo",
          violacoes_de_tenant(GRUPOS) == [], violacoes_de_tenant(GRUPOS))
    # 🔴 A MUTACAO DE DENTRO: um guarda que nao consegue ficar vermelho e
    #    carimbo. Com o grupo de papel IGUAL injetado, ele TEM de acusar.
    com_vazamento = GRUPOS + [GRUPO_DE_VAZAMENTO]
    check("CONTROLE: com um grupo de papel IGUAL injetado, ele ACUSA",
          violacoes_de_tenant(com_vazamento) == [GRUPO_DE_VAZAMENTO["id"]],
          violacoes_de_tenant(com_vazamento))
    # ⛔ E o PAR que impede a versao ingenua de voltar: dois company_id no mesmo
    #    id NAO sao, por si, violacao.
    dois_tenants = [g for g in GRUPOS if len(g["pontas"]) > 1]
    check("PAR: dois company_id no mesmo id, com papeis opostos, e LEGITIMO",
          len(dois_tenants) == 2 and violacoes_de_tenant(dois_tenants) == [],
          dois_tenants)


def ge1e():
    _p("\n[GE1e] quem e o ESCRITOR de `messages` no pipeline, hoje")
    fonte = io.open(WEBHOOK, encoding="utf-8").read()
    arvore = ast.parse(fonte)
    alvo = None
    for no in arvore.body:
        if isinstance(no, ast.AsyncFunctionDef) and no.name == "process_whatsapp_message_background":
            alvo = no
    check("`process_whatsapp_message_background` existe", alvo is not None)
    if alvo is None:
        return
    trecho = ast.dump(alvo)
    # 🔴 A pergunta do §0.3: "quem E o escritor HOJE". Um insert cru em
    #    `messages` dentro do pipeline e uma linha que nasce sem chave.
    inserts_crus = 0
    for no in ast.walk(alvo):
        if isinstance(no, ast.Call) and isinstance(no.func, ast.Attribute) \
                and no.func.attr == "insert":
            alvo_da_chamada = ast.dump(no.func.value)
            if "'messages'" in alvo_da_chamada or '"messages"' in alvo_da_chamada:
                inserts_crus += 1
    check("⛔ ZERO inserts crus em `messages` no pipeline", inserts_crus == 0,
          "%d insert(s) fora do escritor unico" % inserts_crus)
    check("os DOIS inserts passam por `gravar_mensagem_do_pipeline`",
          trecho.count("gravar_mensagem_do_pipeline") == 2,
          trecho.count("gravar_mensagem_do_pipeline"))


def ge1f():
    _p("\n[GE1f] Rajada de 3 -> UMA linha com os TRES ids; reentrega de qualquer um -> 0 linha nova (J7)")

    # \U0001F4CA O defeito medido em 14/09/2026: a linha COMBINADA do pipeline
    #    entrava no indice com o id da ULTIMA mensagem da rajada, e o espelho
    #    grava cada mensagem com o SEU id, na MESMA conversa. Quem chegasse
    #    depois levava 23505 — e se o perdedor fosse o pipeline, era o TEXTO
    #    COMBINADO que se perdia. Os N-1 ids ficavam fora do indice, entao a
    #    reentrega da Meta de qualquer um deles virava linha nova.
    ids = ["wamid.SINTETICO0001", "wamid.SINTETICO0002", "wamid.SINTETICO0003"]
    banco = BancoDuble()

    async def _rodar():
        primeiro = await MOTOR["gravar_mensagem_do_pipeline"](
            banco, dados=dict(ENTREGA, content="bateu o carro\nna avenida\ntem foto"),
            wa_message_id=ids[0], direcao="in", wa_message_ids=ids)
        # a Meta reentrega CADA uma das tres
        de_novo = [await MOTOR["gravar_mensagem_do_pipeline"](
            banco, dados=dict(ENTREGA, content="so a terceira"),
            wa_message_id=i, direcao="in", wa_message_ids=[i]) for i in ids]
        return primeiro, de_novo

    primeiro, de_novo = asyncio.run(_rodar())
    linhas = banco.linhas.get("messages") or []
    check("a rajada de 3 virou UMA linha", primeiro == "gravada" and len(linhas) == 1,
          "%s / %d linhas" % (primeiro, len(linhas)))
    payload = (linhas[0] or {}).get("payload") or {}
    check("\U0001F534 e a linha carrega os TRES ids", payload.get("wa_message_ids") == ids,
          payload)
    check("a chave do indice e o PRIMEIRO id, nao o ultimo",
          payload.get("wa_message_id") == ids[0], payload)
    check("a reentrega do PRIMEIRO id nao cria linha nova",
          de_novo[0] == "ja_estava", de_novo)
    check("e o texto combinado continua sendo o que esta no chat",
          len(banco.linhas.get("messages") or []) >= 1
          and "\n" in str(linhas[0].get("content")), linhas[0].get("content"))

    # \u26a0\ufe0f Os ids 2 e 3 NAO estao no indice unico (a chave e uma so por linha):
    #    quem os barra e a consulta do espelho por `payload->wa_message_ids`.
    #    Este guarda prova que a LISTA existe e os contem; o espelho a consulta.
    check("os ids 2 e 3 ficam registrados na LISTA, que e o que o espelho consulta",
          all(i in (payload.get("wa_message_ids") or []) for i in ids[1:]), payload)

    fonte = io.open(ESPELHO_PY, encoding="utf-8").read()
    check("\U0001F534 o espelho consulta `payload->wa_message_ids` antes de gravar",
          "payload->wa_message_ids" in fonte,
          "sem a consulta, a atendente le a rajada duas vezes: inteira e picada")
    pos_consulta = fonte.find("payload->wa_message_ids")
    pos_insert = fonte.find("_inserir_mensagem(cliente, conversa_id)")
    check("e a consulta vem ANTES do insert da mensagem",
          0 < pos_consulta < pos_insert, (pos_consulta, pos_insert))
    check('\u26a0\ufe0f e SO para inbound (a linha combinada so existe no que o segurado manda)',
          'if direcao == "in" and str(message_id or "").strip():' in fonte,
          "uma consulta por mensagem de SAIDA seria leitura paga por nada")


GATES = {"GE1a": ge1a, "GE1b": ge1b, "GE1c": ge1c, "GE1d": ge1d, "GE1e": ge1e,
         "GE1f": ge1f}


# ===========================================================================
# AS MUTACOES — por COPIA, em SUBPROCESSO. A arvore precisa estar parada.
# ===========================================================================
MUTACOES = [
    # (d) 🔴 J7 de volta: a linha combinada volta a guardar UM id so
    ("M-E1d", "app/api/webhook.py",
     '    if todos:\n'
     '        # \u26d4 TODOS os ids da rajada.',
     '    if False:\n'
     '        # \u26d4 TODOS os ids da rajada.',
     "GE1f"),
    # (e) 🔴 J7 de volta: o espelho deixa de consultar a lista de ids
    ("M-E1e", "app/services/atlas/espelho_chat.py",
     '        if direcao == "in" and str(message_id or "").strip():',
     "        if False:",
     "GE1f"),
    # (a) 🔴 A MUTACAO DO CARD: tirar o `wa_message_id` do insert do pipeline.
    #     E o estado de ANTES desta SPEC — a linha nasce fora do indice parcial.
    ("M-E1a", "app/api/webhook.py",
     "    saida = {\"origem\": \"agente\", \"direcao\": str(direcao or \"\")}\n"
     "    if chave:",
     "    saida = {\"origem\": \"agente\", \"direcao\": str(direcao or \"\")}\n"
     "    if False:",
     "GE1a"),
    # (b) o 23505 volta a ser tratado como falha -> o acerto do indice vira erro.
    ("M-E1b", "app/api/webhook.py",
     '    return "23505" in texto or "duplicate key" in texto.lower()',
     "    return False",
     "GE1a"),
    # (c) o escritor engole TUDO -> banco fora do ar passa por dedupe.
    ("M-E1c", "app/api/webhook.py",
     "        if e_duplicata_do_banco(erro):\n            return \"ja_estava\"\n        raise",
     "        return \"ja_estava\"",
     "GE1c"),
]


def _rodar(gate):
    return subprocess.run(
        [sys.executable, os.path.abspath(__file__), "--so", gate],
        # 🔴 `text=True` sozinho decodifica com a codepage do Windows (cp1252) e
        # ESTOURA no primeiro emoji da saida — `r.stdout` volta VAZIO, `falhas`
        # fica vazia, e a mutacao vermelha e contada como verde. Medido em
        # 14/09/2026: M-E3b (4 linhas [FALHOU]) reportada como "NAO deixou
        # vermelho". ⚠️ Um harness que nao le a saida nao mede mutacao nenhuma.
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
        backup = tempfile.NamedTemporaryFile(delete=False, suffix=".bak-e0012g9").name
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
        _p("  G9 -- UMA ENTREGA = UMA LINHA = UM TURNO  (SPEC-EXTRA-001.2 E1)")
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


def test_uma_entrega_uma_linha_um_turno():
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
