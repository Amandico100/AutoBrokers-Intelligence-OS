# -*- coding: utf-8 -*-
"""SPEC-123 F1a — 🔴 O TESTE DO FIO do destravador.

O FIO (o do produto, nada reimplementado; dublê SÓ na borda — o cliente do provedor, o banco,
o Redis e o diário, que é da F4 e ainda não costurou):

  tela REAL do acervo (`tests/corpus/telas_reais/yelum-residencial.jsonl`, mascarada)
  → `insurer_dispatch_service.handle_insurer_message` (o MOTOR real) → `needs_human`
    `tela_que_decide:escolhe_o_servico`  ← HOJE TRAVA AQUI (vai a uma pessoa)
  → `destravador.destravar(modo="on")`
      → `mensagens_do_destravador` (o prompt do PRODUTO `build_human_phase_messages` + o contexto)
      → `llm_factory.invocar_com_reserva("destravador")` REAL → `create_llm` REAL (resolvedor pelo
        snapshot, ledger, relógio) → o CLIENTE do provedor (DUBLÊ, openai)
      → `ler_destravamento` → `decidir_destravamento` (a POLÍTICA)
      → a 2ª opinião: `destravador_segunda` → `create_llm` REAL → o cliente (DUBLÊ, anthropic)
      → `guard_human_phase_reply` (o conferente do PRODUTO)
      → `diario_de_decisoes.registrar_decisao` (DUBLÊ da borda: a F4 costura depois)
  → a decisão: RESPONDER "Encanador" — sem pessoa.

Nasceu VERMELHO: antes da F1a, `app.services.destravador` não existia (ModuleNotFoundError).
⛔ Nada sai da máquina. Nenhuma mensagem é enviada: o destravador não tem como enviar.
"""
from __future__ import annotations

import asyncio
import json
import sys
import types
from typing import Any

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from tests.test_spec122_sombra_e_sem_chute import (  # noqa: F401 — `amb` e `_fio_fixo` são fixtures
    AC, CLIENTE, D, EMPRESA_A, EMPRESA_B, FIO, R, _fio_fixo, amb, sessao, tela_real,
)
from app.factories import llm_factory as _LF
from app.services import destravador as DT

#: O helper REAL de produção (o `amb` da SPEC-122 o troca por um espião; aqui ele volta).
_INVOCAR_REAL = _LF.invocar_com_reserva

REF_YELUM_RES = "yelum-residencial-whatsapp@v1"
#: 📊 A tela REAL (acervo mascarado) do menu de serviços da Yelum residencial. Com o serviço
#: não informado no caso, o motor a classifica `tela_que_decide:escolhe_o_servico` e chama uma
#: pessoa (sondagem de 30/09: `handle_insurer_message` → needs_human).
TELA_SERVICOS = tela_real("yelum-residencial", r"Qual o servi[çc]o que voc[êe] precisa\?")
RELATO = "está vazando água embaixo da pia da cozinha, o sifão soltou"


def js(**k) -> str:
    return json.dumps(k, ensure_ascii=False)


class _ModeloDoDestravador(BaseChatModel):
    """O CLIENTE do provedor, dublado. Responde por (papel, provedor) e diz QUEM respondeu
    (`response_metadata.model_provider`, como o langchain real)."""

    amb: Any = None
    resolvido: Any = None

    @property
    def _llm_type(self) -> str:
        return "duble-123"

    def _generate(self, messages, stop=None, run_manager=None, **kw):
        from app.core.callbacks.cost_callback import CostCallbackHandler
        from app.core.relogio_do_modelo import RelogioDoModeloCallback

        r = self.resolvido
        cbs = list(self.callbacks or [])
        custo = [c for c in cbs if isinstance(c, CostCallbackHandler)]
        self.amb.chamadas_ao_modelo.append({
            "papel": r.papel, "provedor": r.provider, "modelo": r.model,
            "company_id": custo[0].company_id if custo else None,
            "service_type": custo[0].service_type if custo else None,
            "relogio": any(isinstance(c, RelogioDoModeloCallback) for c in cbs),
            "system": messages[0].content, "user": messages[1].content})
        resp = self.amb.respostas
        saida = resp.get((r.papel, r.provider), resp.get(r.papel, ""))
        if isinstance(saida, BaseException):
            raise saida
        meta = dict(resp.get(("meta", r.papel, r.provider)) or
                    {"model_provider": r.provider, "model_name": r.model})
        return ChatResult(generations=[ChatGeneration(message=AIMessage(
            content=str(saida), response_metadata=meta,
            usage_metadata={"input_tokens": 1000, "output_tokens": 50, "total_tokens": 1050}))])


def diario_duble(monkeypatch):
    """A BORDA do banco do diário (a F4 é a dona de `diario_de_decisoes`; a costura é depois)."""
    mod = types.ModuleType("app.services.diario_de_decisoes")
    mod.linhas = []

    async def registrar_decisao(**kw):
        mod.linhas.append(kw)
        return f"diario-{len(mod.linhas)}"

    mod.registrar_decisao = registrar_decisao
    monkeypatch.setitem(sys.modules, "app.services.diario_de_decisoes", mod)
    import app.services as pacote

    monkeypatch.setattr(pacote, "diario_de_decisoes", mod, raising=False)
    return mod


@pytest.fixture
def dt(amb, monkeypatch):
    from app.factories import model_policy as MP

    monkeypatch.setattr(_LF, "invocar_com_reserva", _INVOCAR_REAL)

    def _construir(resolvido, api_key, *, max_tokens, temperature, callbacks):
        return _ModeloDoDestravador(amb=amb, resolvido=resolvido, callbacks=list(callbacks or []))

    monkeypatch.setattr(_LF.LLMFactory, "construir", staticmethod(_construir))
    MP.limpar_cache()
    amb.respostas = {}
    amb.diario = diario_duble(monkeypatch)
    yield amb
    MP.limpar_cache()


def sessao_travada(company=EMPRESA_A, run="run-123", slots=None, **extra):
    """A sessão como o MOTOR a deixa depois da tela real: `needs_human` + o motivo."""
    s = sessao(REF_YELUM_RES, "", company=company, run=run,
               slots=dict(slots if slots is not None else {"problema_descricao": RELATO}), **extra)
    s = D.handle_insurer_message(s, TELA_SERVICOS)
    return s


def destravar(company, s, tela, **k):
    k.setdefault("gatilho", s.get("reason") or "cerebro")
    k.setdefault("modo", "on")
    return asyncio.run(DT.destravar(company, s, tela, **k))


def test_O_FIO_a_tela_real_que_hoje_trava_vira_uma_decisao_certa_sem_pessoa(dt):
    """🔴 O TESTE DO FIO: motor real → trava → destravador → política → 2ª opinião → diário."""
    s = sessao_travada(conversa_segurado=[f"[segurado] {RELATO}"])
    # HOJE: o motor trava e chama uma pessoa (a premissa que o fio precisa, medida pelo motor)
    assert (s["state"], s["reason"]) == ("needs_human", "tela_que_decide:escolhe_o_servico"), (
        s.get("state"), s.get("reason"))
    dt.respostas = {
        ("destravador", "openai"): js(classe="deduzir", acao="RESPONDER", valor="Encanador", nota=88,
                                      motivo="vazamento no sifão da pia é serviço de encanador"),
        ("destravador_segunda", "anthropic"): js(classe="deduzir", acao="RESPONDER", valor="Encanador",
                                                 nota=91, motivo="vazamento = encanador"),
    }
    d = destravar(EMPRESA_A, s, TELA_SERVICOS)
    # a decisão: RESPONDER, sem pessoa
    assert (d.acao, d.valor, d.classe, d.proibicao) == ("RESPONDER", "Encanador", "deduzir", ""), d
    assert (d.nota, d.limiar, d.modo, d.provedor) == (88, 70, "on", "openai")
    assert d.segunda_opiniao["provedor"] == "anthropic" and d.segunda_opiniao["concordou"] is True
    # o custo estimado das DUAS chamadas (preço do catálogo × tokens da resposta; o ledger é a verdade)
    assert d.custo_usd > 0.002, d.custo_usd
    # as duas chamadas: pela fábrica do produto, papéis e ledger certos, a corretora certa
    ch = [(c["papel"], c["provedor"], c["service_type"], c["company_id"]) for c in dt.chamadas_ao_modelo]
    assert ch == [("destravador", "openai", "destravador", EMPRESA_A),
                  ("destravador_segunda", "anthropic", "destravador_segunda", EMPRESA_A)], ch
    # o prompt: o do PRODUTO + o contexto do destravador (a conversa com o segurado inclusive)
    p = dt.chamadas_ao_modelo[0]
    assert "EM NOME DA CORRETORA" in p["system"], "o prompt do produto não está lá"
    assert "O ROTEIRO AUTOMÁTICO TRAVOU" in p["system"] and '"nota"' in p["system"]
    assert RELATO in p["user"] and "A CONVERSA COM O SEGURADO" in p["user"]
    assert "Qual o serviço que você precisa?" in p["user"]
    # a 2ª opinião é INDEPENDENTE: a mesma tela e o mesmo contexto, sem a resposta da primeira
    seg = dt.chamadas_ao_modelo[1]
    assert DT.texto_da_mensagem(seg["user"]) == p["user"]
    assert DT.texto_da_mensagem(seg["system"]) == p["system"]
    # F1c — o CACHE DE PROMPT, pelo fio real (fábrica → cliente): a instrução FIXA é o começo do
    # prompt; a OpenAI recebe texto puro (ela recusa `cache_control`); a Anthropic recebe os três
    # pontos de cache — o fim da instrução fixa, o fim do system e o fim da parte estável do user.
    assert isinstance(p["system"], str) and p["system"].startswith(DT.INSTRUCAO_DO_DESTRAVADOR)
    assert isinstance(p["user"], str)
    efemero = {"type": "ephemeral"}
    assert [(b["text"] == DT.INSTRUCAO_DO_DESTRAVADOR, b.get("cache_control")) for b in seg["system"]] == [
        (True, efemero), (False, efemero)], seg["system"]
    [estavel, muda] = seg["user"]
    assert estavel.get("cache_control") == efemero and "cache_control" not in muda
    assert muda["text"].startswith(DT._MARCA_DO_VARIAVEL) and RELATO in estavel["text"]
    assert "Qual o serviço que você precisa?" in muda["text"], "a TELA é a parte que muda"
    # UMA linha no diário, legível por gente
    [linha] = dt.diario.linhas
    assert d.diario_id == "diario-1"
    assert (linha["company_id"], linha["origem"], linha["work_run_id"]) == (EMPRESA_A, "acionamento", "run-123")
    assert (linha["classe"], linha["acao"], linha["valor"], linha["nota"], linha["limiar"]) == (
        "deduzir", "respondeu_ura", "Encanador", 88, 70)
    assert (linha["modo"], linha["gatilho"], linha["seguradora"], linha["rota"]) == (
        "on", "tela_que_decide:escolhe_o_servico", "yelum", REF_YELUM_RES)
    assert linha["chave_idempotencia"].startswith(f"destravador:{EMPRESA_A}:run-123:")
    frase = linha["explicacao_para_gente"]
    assert "Yelum" in frase and "Encanador" in frase and "certeza 88%" in frase and "concordou" in frase
    assert "_" not in frase.replace("{NOME}", ""), f"jargão na frase para gente: {frase}"


def test_O_FIO_CONTROLE_a_segunda_opiniao_discordando_nao_age(dt):
    """A LINHA DE CONTROLE do fio: a MESMA tela, o MESMO primeiro modelo — a 2ª opinião escolhe
    outra opção e o destravador NÃO responde à URA (pergunta ao segurado: a Yelum espera)."""
    s = sessao_travada()
    dt.respostas = {
        ("destravador", "openai"): js(classe="deduzir", acao="RESPONDER", valor="Encanador", nota=88,
                                      motivo="vazamento"),
        ("destravador_segunda", "anthropic"): js(classe="deduzir", acao="RESPONDER",
                                                 valor="Desentupimento", nota=80, motivo="entupiu"),
    }
    d = destravar(EMPRESA_A, s, TELA_SERVICOS)
    assert d.acao == "PERGUNTAR_AO_SEGURADO" and d.proibicao == "segunda_opiniao_discordou", d
    assert d.segunda_opiniao["concordou"] is False
    assert "você" in d.valor and d.opcoes and all(len(o) == 2 for o in d.opcoes)
    assert not [o for o in d.opcoes if o[1].strip().lower() == "voltar"], "navegação oferecida ao segurado"
    [linha] = dt.diario.linhas
    assert linha["acao"] == "perguntou_segurado"


def test_O_FIO_duas_corretoras_a_decisao_vai_ao_diario_da_dona(dt):
    s = sessao_travada(company=EMPRESA_B, run="run-123-b")
    dt.respostas = {"destravador": js(classe="nunca_sozinho", acao="PESSOA", valor="", nota=40,
                                      motivo="não sei")}
    d = destravar(EMPRESA_B, s, TELA_SERVICOS)
    assert d.acao == "PESSOA"
    assert [l["company_id"] for l in dt.diario.linhas] == [EMPRESA_B]
    assert [c["company_id"] for c in dt.chamadas_ao_modelo] == [EMPRESA_B]


class _Injetado:
    """Um braço de FORA do catálogo (o que a bancada injeta): guarda o que recebeu."""

    def __init__(self, saida):
        self.saida, self.recebido = saida, []

    async def ainvoke(self, mensagens, **kw):
        self.recebido.append(mensagens)
        return AIMessage(content=self.saida)


def test_F1c_a_injecao_decide_pelo_mesmo_fio_sem_tocar_o_catalogo(dt):
    """F1c item 4: `destravar(llm=…, llm_segunda=…)` — a bancada injeta quem decide e a 2ª opinião
    em vez de trocar `_chamar_quem_decide`/`_segunda_opiniao` pelo nome. A política, o conferente e o
    diário são os mesmos; a fábrica de produção NÃO é chamada; cada braço recebe o SEU formato."""
    s = sessao_travada()
    um = _Injetado(js(classe="deduzir", acao="RESPONDER", valor="Encanador", nota=88, motivo="pia"))
    dois = _Injetado(js(classe="deduzir", acao="RESPONDER", valor="Encanador", nota=90, motivo="pia"))
    d = destravar(EMPRESA_A, s, TELA_SERVICOS,
                  llm=DT.ModeloInjetado(um, "openai", "modelo-a"),
                  llm_segunda=DT.ModeloInjetado(dois, "anthropic", "modelo-b"))
    assert (d.acao, d.valor, d.classe, d.provedor, d.modelo) == ("RESPONDER", "Encanador", "deduzir",
                                                                 "openai", "modelo-a"), d
    assert d.segunda_opiniao["provedor"] == "anthropic" and d.segunda_opiniao["concordou"] is True
    assert dt.chamadas_ao_modelo == [], "a injeção não pode cair no catálogo de produção"
    assert len(dt.diario.linhas) == 1
    [(s1, u1)] = um.recebido
    [(s2, u2)] = dois.recebido
    assert isinstance(s1.content, str) and isinstance(s2.content, list)        # openai × anthropic
    assert DT.texto_da_mensagem(s2) == s1.content and DT.texto_da_mensagem(u2) == u1.content


def test_F1c_injetado_sem_segunda_opiniao_nao_deduz_e_nao_chama_o_catalogo(dt):
    s = sessao_travada()
    um = _Injetado(js(classe="deduzir", acao="RESPONDER", valor="Encanador", nota=95, motivo="pia"))
    d = destravar(EMPRESA_A, s, TELA_SERVICOS, llm=DT.ModeloInjetado(um, "openai", "modelo-a"))
    assert d.acao != "RESPONDER" and d.proibicao == "sem_segunda_opiniao", d
    assert dt.chamadas_ao_modelo == []
    # e a 2ª opinião injetada do MESMO provedor também não vale (D3)
    dois = _Injetado(js(classe="deduzir", acao="RESPONDER", valor="Encanador", nota=95, motivo="pia"))
    d2 = destravar(EMPRESA_A, sessao_travada(run="run-123b"), TELA_SERVICOS,
                   llm=DT.ModeloInjetado(um, "openai"), llm_segunda=DT.ModeloInjetado(dois, "openai"))
    assert d2.acao != "RESPONDER" and dois.recebido == [], d2


def test_F1c_a_bancada_injeta_e_nao_troca_o_destravador_pelo_nome():
    import inspect

    from app.services.evals import bancada as B

    fonte = inspect.getsource(B.motor_destravador)
    assert "atributo_trocado(DT," not in fonte and "llm=llm" in fonte and "llm_segunda=llm_segunda" in fonte


def test_F1c_o_prefixo_do_prompt_e_o_mesmo_em_toda_chamada():
    """O cache de prompt casa por PREFIXO: duas corretoras, duas seguradoras, duas telas → o system
    começa pela MESMA instrução fixa, byte a byte. CONTROLE: o resto do system muda (a seguradora)."""
    from tests.test_spec123_destravador_politica import REF_HDI, TELA_PLACA

    a = DT.compor_mensagens(sessao_travada(), TELA_SERVICOS, gatilho="tela_que_decide:escolhe_o_servico")
    b = DT.compor_mensagens(sessao(REF_HDI, "guincho", company=EMPRESA_B), TELA_PLACA, gatilho="cerebro")
    fixo = DT.INSTRUCAO_DO_DESTRAVADOR
    assert a["system"].startswith(fixo) and b["system"].startswith(fixo)
    assert a["system"][len(fixo):] != b["system"][len(fixo):]
    for m in (a, b):    # a parte que muda a cada tela vem DEPOIS da parte estável do acionamento
        i = m["user"].find(DT._MARCA_DO_VARIAVEL)
        assert i > 0 and m["user"].find("Dados do caso") < i < m["user"].find("Tela da seguradora agora")
