# -*- coding: utf-8 -*-
r"""🔴 A LACUNA VIRA TAREFA — GATE D da SPEC-EXTRA-001.5.1 (D12, emenda E1).

📊 **O defeito, medido em 19/09/2026:** `select count(*) from capability_gaps`
→ **0**, e `rg -n "capability_gaps" backend/app` mostrava só a Auxiliary Factory
e dois leitores. O segurado perguntava, o agente respondia *"ainda não sei"* — e
o que ele não soube **morria no turno**. A próxima destilação escolhia
seguradora por palpite.

O QUE ESTE GUARDA MEDE
======================
```
[1] pergunta sem linha publicada, canal SEGURADO -> 1 linha  +  1 aviso
[2] a MESMA pergunta de novo -> a MESMA linha, frequency_count=2, ZERO aviso
[3] canal CORRETOR -> linha SIM, aviso NÃO (emenda E1)
[4] `fonte_indisponivel` -> NADA (é falha de infra, não falta de dado)
[5] varredor de PII sobre a descrição e sobre o aviso = ZERO
    CONTROLE: a mesma pergunta COM CPF fictício entra REDIGIDA
[6] erro do banco na lacuna NÃO altera a resposta ao cliente
[7] 🔴 AS TRÊS MUTAÇÕES: teto removido · aviso no corretor · pergunta crua
```

⛔ **NENHUMA mensagem sai, NENHUMA linha entra em produção.** A porta do grupo é
um DUBLÊ que só anota; a tabela é um duplo em memória que reproduz o `UNIQUE
(fingerprint)` real (`pg_indexes`, 19/09/2026) e o marcador de 24 h é um duplo
do `reivindicar_o_envio` do Redis.
"""
from __future__ import annotations

import asyncio
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend/
sys.path.insert(0, RAIZ)

from app.services import lacunas_de_conhecimento as L  # noqa: E402

OK = FAIL = 0


def checar(cond, rotulo, detalhe=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok    {rotulo}")
    else:
        FAIL += 1
        print(f"  FALHA \U0001F534 {rotulo}" + (f"\n        {detalhe}" if detalhe else ""))


def _fechar() -> int:
    print()
    print("=" * 74)
    print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
    print("=" * 74)
    return 1 if FAIL else 0


# ---------------------------------------------------------------------------
# O duplo da tabela — e ele reproduz o UNIQUE que existe de verdade
# ---------------------------------------------------------------------------
class _Resposta:
    def __init__(self, data):
        self.data = data


class _Consulta:
    def __init__(self, tabela, acao, carga=None):
        self.tabela, self.acao, self.carga = tabela, acao, carga
        self.filtros = {}

    def select(self, *_a, **_k):
        return self

    def eq(self, campo, valor):
        self.filtros[campo] = valor
        return self

    def limit(self, _n):
        return self

    def execute(self):
        return self.tabela._executar(self)


class _TabelaDeLacunas:
    """`capability_gaps` em memória. ⛔ Nenhuma escrita em produção."""

    def __init__(self, quebrar=False):
        self.linhas = []
        self.quebrar = quebrar
        self.escritas = 0

    def table(self, nome):
        assert nome == "capability_gaps", nome
        return self

    # a API do PostgREST que o serviço usa
    def select(self, *_a, **_k):
        return _Consulta(self, "select")

    def insert(self, carga):
        return _Consulta(self, "insert", carga)

    def update(self, carga):
        return _Consulta(self, "update", carga)

    def _executar(self, consulta):
        if self.quebrar:
            raise RuntimeError("banco fora do ar")
        if consulta.acao == "select":
            fp = consulta.filtros.get("fingerprint")
            return _Resposta([l for l in self.linhas if l["fingerprint"] == fp])
        if consulta.acao == "insert":
            self.escritas += 1
            nova = dict(consulta.carga)
            # 🔴 O UNIQUE REAL: `capability_gaps_fingerprint_uk (fingerprint)`,
            #    sem `company_id`. Um duplo que aceitasse duas linhas com o
            #    mesmo fingerprint deixaria passar o defeito que ele guarda.
            if any(l["fingerprint"] == nova["fingerprint"] for l in self.linhas):
                raise RuntimeError("duplicate key value violates "
                                   "capability_gaps_fingerprint_uk")
            nova.setdefault("frequency_count", 1)
            nova["id"] = "gap-%d" % (len(self.linhas) + 1)
            self.linhas.append(nova)
            return _Resposta([nova])
        if consulta.acao == "update":
            self.escritas += 1
            alvo = consulta.filtros.get("id")
            for l in self.linhas:
                if l["id"] == alvo:
                    l.update(consulta.carga)
                    return _Resposta([l])
            return _Resposta([])
        raise AssertionError(consulta.acao)


class _PortaDoGrupo:
    """O DUBLÊ da porta única da 001.3. ⛔ Nada sai."""

    def __init__(self):
        self.avisos = []

    async def __call__(self, _db, **kw):
        self.avisos.append(kw)
        return {"enviado": True, "calado": False, "motivo": "", "destino_ok": True}


class _Marcador:
    """O duplo do `reivindicar_o_envio` — o teto de 24 h, sem Redis.

    ⚠️ A semântica é a REAL: `True` = já avisaram, fique quieto.
    """

    def __init__(self, desligado=False):
        self.chaves = set()
        self.desligado = desligado

    async def __call__(self, company_id, conversation_id, tipo, segundos):
        if self.desligado:
            return False
        chave = (str(company_id), str(conversation_id), str(tipo))
        if chave in self.chaves:
            return True
        self.chaves.add(chave)
        return False


COBERTURA = {
    "estado": "nao_sabemos_ainda", "servico": "carro_reserva", "tipo": "assistencia",
    "insurer_key": "hdi", "ramo": "auto", "produto": "Auto Perfil",
    "plano": None, "motivo": "sem_linha_publicada", "origem": "nenhuma",
}
EMPRESA_A = "11111111-1111-1111-1111-111111111111"
EMPRESA_B = "22222222-2222-2222-2222-222222222222"
PERGUNTA = "tem carro reserva no meu plano?"
#: 💭 CPF FICTÍCIO — gerado para este teste, não pertence a ninguém.
CPF_FICTICIO = "529.982.247-25"

#: O varredor de PII: o que NUNCA pode estar gravado nem no aviso.
PII = re.compile(r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}|\(?\d{2}\)?\s?9?\d{4}-?\d{4}")


def _rodar(corotina):
    return asyncio.run(corotina)


#: ⚠️ Sentinela: `None` é um VALOR legítimo de `cobertura` (é o caso "a Skill
#: não reconheceu a pergunta"), então o padrão não pode ser `None`.
_PADRAO = object()


def _registrar(db, marcador, porta, *, canal, pergunta=PERGUNTA,
               company_id=EMPRESA_A, cobertura=_PADRAO):
    import app.services.o_grupo_so_o_que_importa as G

    antes = G.reivindicar_o_envio
    try:
        G.reivindicar_o_envio = marcador
        return _rodar(L.registrar_lacuna(
            db=db, company_id=company_id, canal=canal,
            cobertura=(COBERTURA if cobertura is _PADRAO else cobertura),
            pergunta=pergunta, enviar=porta))
    finally:
        G.reivindicar_o_envio = antes


# ---------------------------------------------------------------------------
print("\n[1] pergunta sem linha publicada, canal SEGURADO → 1 linha + 1 aviso")
db = _TabelaDeLacunas()
marcador, porta = _Marcador(), _PortaDoGrupo()
r1 = _registrar(db, marcador, porta, canal="segurado")
checar(r1.get("gravou") and r1.get("nova") and len(db.linhas) == 1,
       "🔴 gravou EXATAMENTE uma linha em `capability_gaps`", repr(r1))
linha = db.linhas[0] if db.linhas else {}
checar(linha.get("gap_type") == "missing_data"
       and linha.get("capability_key") == "insurance.cobertura_e_assistencia",
       "com `gap_type='missing_data'` e a capability de cobertura", repr(linha))
checar(linha.get("provider") == "hdi" and linha.get("company_id") == EMPRESA_A,
       "a seguradora vai em `provider` e a 1ª corretora em `company_id`",
       repr(linha))
checar(len(porta.avisos) == 1 and r1.get("avisou"),
       "🔴 e saiu EXATAMENTE um aviso pela porta do grupo", repr(r1))
checar(porta.avisos and porta.avisos[0].get("tipo") == "pedido_de_ajuda",
       "pelo tipo 🆘 `pedido_de_ajuda` — o modelo que já existia",
       repr(porta.avisos[0].get("tipo") if porta.avisos else None))
print("\n      📊 O AVISO, como sai:")
for l in str(porta.avisos[0].get("texto") if porta.avisos else "").splitlines():
    print("        " + l)

# ---------------------------------------------------------------------------
print("\n[2] a MESMA pergunta de novo → a MESMA linha, +1, e ZERO aviso novo")
r2 = _registrar(db, marcador, porta, canal="segurado")
checar(len(db.linhas) == 1 and db.linhas[0].get("frequency_count") == 2,
       "🔴 continua UMA linha, com `frequency_count=2`",
       repr([(l["fingerprint"][:8], l.get("frequency_count")) for l in db.linhas]))
checar(not r2.get("nova") and len(porta.avisos) == 1,
       "🔴 e NENHUM aviso novo — o teto de 24 h da emenda E1 segurou",
       repr(r2))
checar(r2.get("motivo") == "ja_avisei_esta_lacuna_hoje",
       "e ele diz POR QUE calou, em português", repr(r2.get("motivo")))

print("\n      🔴 CONTROLE do [2]: OUTRA lacuna, no MESMO dia, AVISA")
outra = dict(COBERTURA, servico="guincho")
r_outra = _registrar(db, marcador, porta, canal="segurado", cobertura=outra)
checar(len(db.linhas) == 2 and len(porta.avisos) == 2 and r_outra.get("avisou"),
       "🔴 CONTROLE: o teto é por LACUNA, não um silêncio geral de 24 h",
       f"linhas={len(db.linhas)} avisos={len(porta.avisos)}")

print("\n      🔴 CONTROLE do fingerprint: a MESMA falta em OUTRA corretora "
      "SOMA, não duplica")
r_b = _registrar(db, marcador, porta, canal="segurado", company_id=EMPRESA_B)
checar(len(db.linhas) == 2 and db.linhas[0].get("frequency_count") == 3,
       "🔴 a base de planos é GLOBAL: a mesma lacuna em duas corretoras é UMA "
       "tarefa com peso três",
       repr([(l.get("provider"), l.get("frequency_count")) for l in db.linhas]))
checar(db.linhas[0].get("company_id") == EMPRESA_A,
       "e `company_id` continua sendo a PRIMEIRA — procedência, não dono",
       repr(db.linhas[0].get("company_id")))
checar(r_b.get("avisou") and len(porta.avisos) == 3,
       "⚠️ mas a corretora B É avisada: o teto é por (lacuna, CORRETORA)",
       f"avisos={len(porta.avisos)}")

# ---------------------------------------------------------------------------
print("\n[3] canal CORRETOR → grava a linha, NÃO avisa o grupo")
db2 = _TabelaDeLacunas()
marcador2, porta2 = _Marcador(), _PortaDoGrupo()
r3 = _registrar(db2, marcador2, porta2, canal="corretor")
checar(r3.get("gravou") and len(db2.linhas) == 1,
       "a lacuna do chat do corretor É gravada (roadmap não tem canal)", repr(r3))
checar(not r3.get("avisou") and len(porta2.avisos) == 0,
       "🔴 e NENHUM aviso sai: quem precisa saber já está lendo a resposta",
       repr(porta2.avisos))
checar(r3.get("motivo") == "canal_do_corretor_nao_avisa",
       "e o motivo fica escrito", repr(r3.get("motivo")))

# ---------------------------------------------------------------------------
print("\n[4] `fonte_indisponivel` → NADA: falha de infra não é falta de dado")
db3 = _TabelaDeLacunas()
marcador3, porta3 = _Marcador(), _PortaDoGrupo()
r4 = _registrar(db3, marcador3, porta3, canal="segurado",
                cobertura=dict(COBERTURA, estado="fonte_indisponivel"))
checar(not r4.get("gravou") and len(db3.linhas) == 0 and len(porta3.avisos) == 0,
       "🔴 nem linha, nem aviso — registrá-la mandaria alguém curar uma "
       "condição geral que já está curada", repr(r4))
r4b = _registrar(db3, marcador3, porta3, canal="segurado",
                 cobertura=dict(COBERTURA, estado="coberto", origem="base"))
checar(not r4b.get("gravou") and len(db3.linhas) == 0,
       "e `coberto` tampouco vira lacuna — a base RESPONDEU", repr(r4b))
r4c = _registrar(db3, marcador3, porta3, canal="segurado", cobertura=None)
checar(not r4c.get("gravou"),
       "🔴 CONTROLE: sem veredito nenhum, nada acontece", repr(r4c))

# ---------------------------------------------------------------------------
print("\n[5] o varredor de PII — na descrição gravada E no texto do aviso")
db4 = _TabelaDeLacunas()
marcador4, porta4 = _Marcador(), _PortaDoGrupo()
pergunta_suja = ("meu CPF é %s e meu telefone (11) 98765-4321 — tem carro "
                 "reserva?" % CPF_FICTICIO)
r5 = _registrar(db4, marcador4, porta4, canal="segurado", pergunta=pergunta_suja)
gravado = db4.linhas[0].get("description_redacted") if db4.linhas else ""
aviso = porta4.avisos[0].get("texto") if porta4.avisos else ""
checar(not PII.search(str(gravado)),
       "🔴 `description_redacted` não carrega CPF nem telefone", repr(gravado))
checar(CPF_FICTICIO not in str(aviso)
       and CPF_FICTICIO.replace(".", "").replace("-", "") not in str(aviso)
       and "98765-4321" not in str(aviso),
       "🔴 e o TEXTO DO AVISO também não", str(aviso)[:400])
checar("carro reserva" in str(aviso).lower(),
       "🔴 CONTROLE: mas a pergunta CHEGA ao humano — redigir não é apagar",
       str(aviso)[:300])
checar(PII.search(pergunta_suja) is not None,
       "🔴 CONTROLE do varredor: ele ACHA o CPF na pergunta crua — ele consegue "
       "ficar vermelho", pergunta_suja)

# ---------------------------------------------------------------------------
print("\n[6] erro do banco na lacuna NÃO altera a resposta ao cliente")
db5 = _TabelaDeLacunas(quebrar=True)
marcador5, porta5 = _Marcador(), _PortaDoGrupo()
r6 = _registrar(db5, marcador5, porta5, canal="segurado")
checar(not r6.get("gravou") and str(r6.get("motivo", "")).startswith("erro_ao_gravar"),
       "🔴 o banco caiu, o serviço DEVOLVEU em vez de levantar", repr(r6))
checar(len(porta5.avisos) == 1,
       "⚠️ e o humano é avisado MESMO ASSIM — a lacuna existe ainda que a "
       "linha não tenha entrado", repr(len(porta5.avisos)))

# ---------------------------------------------------------------------------
print("\n[7] 🔴 AS TRÊS MUTAÇÕES — o guarda CONSEGUE ficar vermelho")
# (a) o teto de 24 h REMOVIDO
db6 = _TabelaDeLacunas()
sem_teto, porta6 = _Marcador(desligado=True), _PortaDoGrupo()
_registrar(db6, sem_teto, porta6, canal="segurado")
_registrar(db6, sem_teto, porta6, canal="segurado")
_registrar(db6, sem_teto, porta6, canal="segurado")
checar(len(porta6.avisos) == 3,
       "🔴 MUTAÇÃO (a) teto removido → 3 avisos para a MESMA lacuna "
       "(o guarda do [2] ficaria VERMELHO)", repr(len(porta6.avisos)))

# (b) o aviso saindo no canal do CORRETOR
_canal_original = L.registrar_lacuna
db7 = _TabelaDeLacunas()
marcador7, porta7 = _Marcador(), _PortaDoGrupo()


async def _sem_a_trava_de_canal(**kw):
    """A mutação: o canal deixa de decidir — todo mundo avisa."""
    return await _canal_original(**{**kw, "canal": "segurado"})


try:
    L.registrar_lacuna = _sem_a_trava_de_canal
    r_mut = _registrar(db7, marcador7, porta7, canal="corretor")
    checar(len(porta7.avisos) == 1,
           "🔴 MUTAÇÃO (b) aviso no canal do corretor → o grupo é interrompido "
           "(o guarda do [3] ficaria VERMELHO)", repr(r_mut))
finally:
    L.registrar_lacuna = _canal_original

# (c) a pergunta CRUA em `description_redacted`
_descricao_original = L.descricao_da_lacuna
db8 = _TabelaDeLacunas()
marcador8, porta8 = _Marcador(), _PortaDoGrupo()
try:
    L.descricao_da_lacuna = lambda _c: pergunta_suja
    _registrar(db8, marcador8, porta8, canal="segurado", pergunta=pergunta_suja)
    sujo = db8.linhas[0].get("description_redacted") if db8.linhas else ""
    checar(bool(PII.search(str(sujo))),
           "🔴 MUTAÇÃO (c) pergunta crua na descrição → o varredor a ENCONTRA "
           "(o guarda do [5] ficaria VERMELHO)", repr(sujo)[:200])
finally:
    L.descricao_da_lacuna = _descricao_original

print("\n      🔴 CONTROLE das mutações: restauradas as três, tudo volta ao certo")
db9 = _TabelaDeLacunas()
marcador9, porta9 = _Marcador(), _PortaDoGrupo()
_registrar(db9, marcador9, porta9, canal="segurado", pergunta=pergunta_suja)
_registrar(db9, marcador9, porta9, canal="segurado", pergunta=pergunta_suja)
_registrar(db9, marcador9, porta9, canal="corretor", pergunta=pergunta_suja)
checar(len(db9.linhas) == 1 and db9.linhas[0].get("frequency_count") == 3
       and len(porta9.avisos) == 1
       and not PII.search(str(db9.linhas[0].get("description_redacted"))),
       "🔴 CONTROLE: uma linha com peso 3, UM aviso, zero PII",
       repr([len(db9.linhas), db9.linhas[0].get("frequency_count"),
             len(porta9.avisos)]))

sys.exit(_fechar())
