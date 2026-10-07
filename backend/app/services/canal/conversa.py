# -*- coding: utf-8 -*-
"""A CONVERSA do canal comparador — SPEC-133-A U4 (D-133A-01 · D-133A-05 · D-133A-08 · D-MC-59/70).

Uma conversa guiada por ESTADO: uma pergunta por vez, na ordem de `ROTEIRO`, texto curto e humano. Cada resposta passa
primeiro pela REGRA (placa antiga/Mercosul, CEP de 8 dígitos, CPF com dígito verificador, datas, sim/não, números com
régua). Só a resposta LIVRE que a regra não entende vai ao MODELO, pelo papel `canal_cotacao` do Model Router
(`llm_factory.invocar_com_reserva` — nenhum cliente de LLM novo), e o que o modelo devolve é RECONFERIDO pela mesma
regra. Modelo fora, lento ou inventando → a conversa pergunta de novo; nunca inventa. CPF, placa, CEP, nome e datas
NUNCA vão ao modelo (só regra).

    responder(db, company_id, telefone_e164, texto, midia, estado, *, config) → Resposta(baloes, estado, disparar)

O consentimento (D-133A-05, o texto da SPEC) vem ANTES de qualquer dado pessoal; "não" encerra com educação e o estado
fica só com o "não". Apólice/foto depois do "sim": guarda a REFERÊNCIA da mídia e segue (a leitura é da 130-B).
Fora do escopo (sinistro, falar com alguém, carro de aplicativo — sem código medido) → oferece passar à corretora.

⛔ D-MC-59: nunca força venda, nunca "o mais barato do mercado", nunca urgência. Nada aqui é logado com valor.
🔴 O que a pergunta NÃO pergunta, e por quê (P-129B-05 — os RÓTULOS de estado civil, uso e garagem do Agger não foram
medidos; perguntar e não conseguir usar a resposta seria enganar a pessoa):
    estado civil  → `ESTADO_CIVIL_PADRAO` (o código medido mais frequente), declarado em `assumidos`
    garagem       → fica o PADRÃO DA TELA (`agger_robo.PADROES_DO_QUESTIONARIO`), declarado em `assumidos`
    uso           → pergunta "aplicativo?" (D-MC-70); "não" → o padrão da tela (assumido); "sim" → passa à corretora
"""
from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import logging
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

logger = logging.getLogger(__name__)

PAPEL = "canal_cotacao"
SERVICE_TYPE = "canal_cotacao"
TETO_DO_MODELO_S = 8.0
MAX_TENTATIVAS = 3
VERSAO_DO_ESTADO = 1
NOME_PADRAO_DO_CANAL = "Quem Cobra Menos"   # só se a config não trouxer `canal.nome` (D-MC-55: é config, não constante)

#: 📊 `tests/fixtures/agger/*.json` (gravações R1/R2 + vivo_conta_a/b, 07/10): estadoCivil 2 em 32 de 47 corpos com
#: valor (1 em 3, 4 em 12). O RÓTULO de cada código não foi medido (P-129B-05) — por isso a conversa NÃO pergunta o
#: estado civil: usa o código mais frequente e o declara `assumido` (a página e o robô sabem que não veio da pessoa).
#: 🔴 Por que este número e não outro: é o único que as gravações mostram como o caso comum; trocar exige medir a lista.
ESTADO_CIVIL_PADRAO = 2


def _texto_do_consentimento(nome_do_canal: str) -> str:
    """D-133A-05 — a verdade do paralelo (o CPF vai a TODAS as corretoras aderidas, não só à vencedora)."""
    return (f"Antes de começar: o seu CPF e o seu carro vão às seguradoras pelas corretoras parceiras do "
            f"{nome_do_canal}, para cotar; ninguém é obrigado a fechar.")


#: a versão do texto que a pessoa aceitou (o repositório da F1 grava junto do "sim"/"não")
VERSAO_DO_CONSENTIMENTO = "133A-v1-" + hashlib.sha256(
    _texto_do_consentimento(NOME_PADRAO_DO_CANAL).encode("utf-8")).hexdigest()[:8]


@dataclass
class Resposta:
    baloes: List[str]
    estado: Dict[str, Any]
    disparar: Optional[Dict[str, Any]] = None   # o perfil completo (ver `montar_perfil`)


# =====================================================================================================================
# a REGRA
# =====================================================================================================================
def _sem_acento(texto: Any) -> str:
    t = unicodedata.normalize("NFKD", str(texto or ""))
    return re.sub(r"\s+", " ", "".join(c for c in t if not unicodedata.combining(c)).lower()).strip()


_SIM = re.compile(r"^(sim|s|ss|claro|pode|pode sim|ok|okay|beleza|blz|bora|vamos|aceito|concordo|quero|isso|"
                  r"com certeza|positivo|uhum|aham|👍|✅)[.! ]*$")
_NAO = re.compile(r"^(nao|n|nao quero|agora nao|prefiro nao|negativo|nem|nunca|nenhum|ninguem|👎)[.! ]*$")


def sim_nao(texto: Any) -> Optional[bool]:
    t = _sem_acento(texto)
    if _SIM.match(t):
        return True
    if _NAO.match(t) or t.startswith("nao,") or t.startswith("nao "):
        return False
    return None


def validar_placa(texto: Any) -> Optional[str]:
    """Antiga (AAA9999) e Mercosul (AAA9A99). Devolve sem separador, maiúscula."""
    p = re.sub(r"[^A-Za-z0-9]", "", str(texto or "")).upper()
    return p if re.fullmatch(r"[A-Z]{3}\d[A-Z0-9]\d{2}", p) else None


def validar_cep(texto: Any) -> Optional[str]:
    d = re.sub(r"\D", "", str(texto or ""))
    return d if len(d) == 8 and d != "00000000" else None


def validar_cpf(texto: Any) -> Optional[str]:
    d = re.sub(r"\D", "", str(texto or ""))
    if len(d) != 11 or d == d[0] * 11:
        return None
    for n in (9, 10):
        soma = sum(int(d[i]) * (n + 1 - i) for i in range(n))
        dv = (soma * 10) % 11 % 10
        if dv != int(d[n]):
            return None
    return d


def validar_data(texto: Any, *, hoje: Optional[date] = None) -> Optional[str]:
    """dd/mm/aaaa (ou com - .) → ISO, com idade de 18 a 100 anos."""
    m = re.search(r"\b(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})\b", str(texto or "")) or \
        re.fullmatch(r"\s*(\d{2})(\d{2})(\d{4})\s*", str(texto or ""))
    if not m:
        return None
    try:
        d = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        return None
    hoje = hoje or datetime.now(timezone.utc).date()
    idade = hoje.year - d.year - ((hoje.month, hoje.day) < (d.month, d.day))
    return d.isoformat() if 18 <= idade <= 100 else None


def validar_nome(texto: Any) -> Optional[str]:
    t = re.sub(r"\s+", " ", str(texto or "")).strip()
    partes = t.split(" ")
    if len(partes) < 2 or len(t) > 120 or not all(re.fullmatch(r"[A-Za-zÀ-ÿ'´`.\-]+", p) for p in partes):
        return None
    return t


def validar_sexo(texto: Any) -> Optional[str]:
    t = _sem_acento(texto)
    if re.fullmatch(r"(m|masc|masculino|homem|sou homem|ele)[.! ]*", t):
        return "M"
    if re.fullmatch(r"(f|fem|feminino|mulher|sou mulher|ela)[.! ]*", t):
        return "F"
    return None


def _numero(texto: Any) -> Optional[float]:
    """"3.500", "R$ 3.500,00", "800 km", "1,2 mil" → número (None se não houver UM número claro)."""
    t = _sem_acento(texto).replace("r$", " ")
    achados = re.findall(r"\d[\d.]*(?:,\d+)?", t)
    if len(achados) != 1:
        return None
    bruto = achados[0]
    if "," in bruto:
        bruto = bruto.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+", bruto):
        bruto = bruto.replace(".", "")
    try:
        v = float(bruto)
    except ValueError:
        return None
    if re.search(r"\bmil\b", t):
        v *= 1000
    return v


def validar_km(texto_ou_valor: Any) -> Optional[int]:
    v = texto_ou_valor if isinstance(texto_ou_valor, (int, float)) and not isinstance(texto_ou_valor, bool) \
        else _numero(texto_ou_valor)
    return int(round(v)) if v is not None and 0 <= v <= 20000 else None


def validar_anos_de_carteira(texto_ou_valor: Any) -> Optional[int]:
    v = texto_ou_valor if isinstance(texto_ou_valor, (int, float)) and not isinstance(texto_ou_valor, bool) \
        else _numero(texto_ou_valor)
    return int(v) if v is not None and float(v).is_integer() and 0 <= v <= 80 else None


_PULAR = re.compile(r"\b(pular|pula|pulo|nao sei|nao lembro|prefiro nao|nao tenho|sem seguro|nao tenho seguro|"
                    r"passo|proxima)\b")


def validar_premio(texto_ou_valor: Any) -> Tuple[bool, Optional[float]]:
    """(entendeu, valor anual). "pular" → (True, None). "200 por mês" → 2400."""
    if isinstance(texto_ou_valor, (int, float)) and not isinstance(texto_ou_valor, bool):
        v = float(texto_ou_valor)
        return (True, round(v, 2)) if 300 <= v <= 60000 else (False, None)
    t = _sem_acento(texto_ou_valor)
    if _PULAR.search(t) or t in ("-", "nada", "nenhum"):
        return True, None
    v = _numero(t)
    if v is None:
        return False, None
    if re.search(r"\b(mes|mensal|mensais|por mes|ao mes)\b", t):
        v *= 12
    return (True, round(v, 2)) if 300 <= v <= 60000 else (False, None)


_FORA_DO_ESCOPO = re.compile(r"\b(atendente|humano|pessoa de verdade|falar com (alguem|voces|a corretora|um corretor|"
                             r"uma pessoa)|sinistro|bati o carro|batida|guincho|reboque|segunda via|boleto|"
                             r"cancelar (o |meu )?seguro|seguro de vida|seguro residencial|plano de saude)\b")
_RECOMECAR = re.compile(r"\b(recomecar|comecar de novo|nova cotacao|cotar de novo|outra cotacao|reiniciar)\b")
_QUER_FECHAR = re.compile(r"\b(quero fechar|fechar|fecha|quero sim|vamos fechar|bora fechar|quero contratar|"
                          r"contratar|quero esse|quero essa|pode fechar)\b")


# =====================================================================================================================
# o ROTEIRO — uma pergunta por vez (SPEC §4; D-MC-70: "aplicativo?" é a 1ª do perfil)
# =====================================================================================================================
@dataclass(frozen=True)
class Passo:
    chave: str
    pergunta: str
    dica: str
    regra: Callable[[str], Any]
    tipo_do_modelo: Optional[str] = None    # None = só regra (dado pessoal nunca vai ao modelo)


ROTEIRO: Tuple[Passo, ...] = (
    Passo("placa", "Pra começar: qual a placa do carro?", "A placa tem 7 caracteres, tipo ABC1D23 ou ABC1234.",
          validar_placa),
    Passo("cep", "Qual o CEP de onde o carro dorme?", "O CEP tem 8 números, tipo 01001-000.", validar_cep),
    Passo("aplicativo", "Você usa o carro pra trabalhar com aplicativo (Uber, 99…)?", "Pode responder sim ou não.",
          sim_nao, "sim_nao"),
    Passo("km_mensal", "Mais ou menos quantos km você roda por mês?", "Um número aproximado já serve, tipo 800.",
          validar_km, "numero"),
    Passo("jovem", "Alguém de 18 a 25 anos dirige o carro?", "Pode responder sim ou não.", sim_nao, "sim_nao"),
    Passo("cpf", "Agora o CPF de quem mais dirige o carro.", "O CPF tem 11 números, tipo 123.456.789-09.",
          validar_cpf),
    Passo("nome", "E o nome completo dessa pessoa?", "Me manda nome e sobrenome.", validar_nome),
    Passo("nascimento", "Qual a data de nascimento? (ex.: 25/03/1985)", "Me manda no formato dia/mês/ano.",
          validar_data),
    Passo("sexo", "A seguradora pede: é homem ou mulher?", "Pode responder homem ou mulher.", validar_sexo, "sexo"),
    Passo("habilitacao", "Há quantos anos tem carteira de motorista?", "Só o número de anos, tipo 10.",
          validar_anos_de_carteira, "numero"),
    Passo("premio", "Última pergunta: quanto você paga hoje no seu seguro? (pode pular)",
          "Me diz o valor por ano (tipo 2.800) — ou escreva pular.", lambda t: validar_premio(t), "numero"),
)
_POR_CHAVE = {p.chave: p for p in ROTEIRO}
ETAPAS = tuple(p.chave for p in ROTEIRO)


# =====================================================================================================================
# o MODELO — só para entender resposta livre
# =====================================================================================================================
_INSTRUCAO = (
    "Você interpreta UMA resposta curta de uma pessoa no WhatsApp a UMA pergunta de um formulário de cotação de seguro "
    "de carro. Responda SÓ com JSON: {\"valor\": ..., \"fora_do_escopo\": true|false}. Tipos de valor: "
    "sim_nao → true, false ou null · numero → um número ou null · sexo → \"M\", \"F\" ou null · "
    "intencao → \"fechar\", \"nao\", \"duvida\" ou null. Nunca invente: se a resposta não disser, valor null. "
    "fora_do_escopo = true só quando a pessoa pede outra coisa (sinistro, falar com alguém, outro seguro).")


def _objeto_json(texto: str) -> Optional[dict]:
    m = re.search(r"\{.*\}", str(texto or ""), re.S)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
    except (ValueError, TypeError):
        return None
    return obj if isinstance(obj, dict) else None


async def _chamar_o_papel(mensagens: list, company_id: str) -> Any:
    from app.factories.llm_factory import invocar_com_reserva

    return await invocar_com_reserva(PAPEL, mensagens, company_id=company_id or None, service_type=SERVICE_TYPE)


async def entender(tipo: str, pergunta: str, texto: str, *, company_id: str, llm: Any = None) -> Optional[dict]:
    """{"valor", "fora_do_escopo"} ou None (modelo fora, lento, ou saída inválida). Nunca levanta."""
    mensagens = [{"role": "system", "content": _INSTRUCAO},
                 {"role": "user", "content": json.dumps({"tipo": tipo, "pergunta": pergunta,
                                                          "resposta": str(texto or "")[:300]}, ensure_ascii=False)}]
    try:
        chamada = llm.ainvoke(mensagens) if llm is not None else _chamar_o_papel(mensagens, company_id)
        resposta = await asyncio.wait_for(chamada, timeout=TETO_DO_MODELO_S)
        conteudo = getattr(resposta, "content", resposta)
        if isinstance(conteudo, list):
            conteudo = " ".join(str(p.get("text", "")) if isinstance(p, dict) else str(p) for p in conteudo)
        return _objeto_json(str(conteudo))
    except Exception as exc:  # noqa: BLE001 — no escuro, pergunta de novo
        logger.warning("[CANAL] o modelo não respondeu (%s) — pergunto de novo", type(exc).__name__)
        return None


# =====================================================================================================================
# o estado
# =====================================================================================================================
def _agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _nome_do_canal(config: Optional[Mapping[str, Any]]) -> str:
    canal = (config or {}).get("canal") if isinstance(config, Mapping) else None
    nome = str((canal or {}).get("nome") or "").strip() if isinstance(canal, Mapping) else ""
    return nome or NOME_PADRAO_DO_CANAL


def _novo_estado() -> Dict[str, Any]:
    return {"versao": VERSAO_DO_ESTADO, "etapa": "consentimento", "respostas": {}, "tentativas": {}}


def _primeiro_nome(nome: Any) -> Optional[str]:
    p = str(nome or "").strip().split(" ")[0]
    return p.capitalize() if p else None


def montar_perfil(respostas: Mapping[str, Any]) -> Dict[str, Any]:
    """As respostas → {pedido (grupos do contrato), assumidos, premio_atual_declarado, primeiro_nome}.

    O condutor principal (quem respondeu "CPF de quem mais dirige") é também o segurado: os campos do segurado que vêm
    dele, o CEP do segurado (= o de pernoite) e a relação "próprio" são `assumidos`. Garagem e uso ficam com o padrão
    da tela (assumidos). FIPE/ano/combustível: a placa supre (D-133A-03, `pedido.CAMPOS_QUE_A_PLACA_SUPRE`)."""
    r = respostas
    pessoa = {"nome": r["nome"], "nascimento": r["nascimento"], "sexo": r["sexo"],
              "estado_civil": ESTADO_CIVIL_PADRAO}
    pedido = {
        "segurado": {"tipo_pessoa": "F", "cpf_cnpj": r["cpf"], "cep": r["cep"], **pessoa},
        "veiculo": {"placa": r["placa"]},
        "pernoite": {"cep_pernoite": r["cep"]},
        "condutor": {"cpf": r["cpf"], "relacao_com_segurado": "proprio", "tempo_habilitacao": r["habilitacao"],
                     "jovem_condutor": bool(r["jovem"]), **pessoa},
        "questionario": {"km_mensal": r["km_mensal"]},
    }
    assumidos = sorted({"segurado.cpf_cnpj", "segurado.nome", "segurado.nascimento", "segurado.sexo",
                        "segurado.estado_civil", "condutor.estado_civil", "segurado.cep",
                        "condutor.relacao_com_segurado", "pernoite.garagem_residencia", "veiculo.uso"})
    return {"pedido": pedido, "assumidos": assumidos, "premio_atual_declarado": r.get("premio"),
            "primeiro_nome": _primeiro_nome(r["nome"])}


def _perfil_fecha(perfil: Mapping[str, Any]) -> List[str]:
    """O que o pedido do canal ainda recusaria (nomes de campo). Vazio = a porta aceita."""
    from app.services.multicalculo.pedido import PedidoDeCalculo

    p = PedidoDeCalculo.de_dict(perfil["pedido"], assumidos=perfil["assumidos"])
    return p.faltando(origem="canal") + p.sem_codigo() + p.perfil_faltando()


# =====================================================================================================================
# os efeitos (F1 · cotacao) — import tardio: a F1 escreve `repositorio`/`envio` em paralelo
# =====================================================================================================================
async def _registrar_consentimento(db: Any, company_id: str, telefone: str, aceito: bool) -> None:
    from app.services.canal import repositorio

    await asyncio.to_thread(repositorio.registrar_consentimento, db, company_id, telefone, aceito=aceito,
                            versao_do_texto=VERSAO_DO_CONSENTIMENTO)


# =====================================================================================================================
# responder
# =====================================================================================================================
async def responder(db: Any, company_id: str, telefone_e164: str, texto: str, midia: Optional[dict],
                    estado: dict, *, config: Any = None, llm: Any = None) -> Resposta:
    """Um turno. `estado` é o que `repositorio.carregar_estado` devolveu ({} na 1ª vez); a resposta traz o NOVO estado
    (quem chama salva) e, quando o perfil fecha, `disparar` (quem chama passa a `cotacao.disparar`)."""
    est = copy.deepcopy(estado or {})
    t = str(texto or "").strip()
    baixo = _sem_acento(t)
    nome_canal = _nome_do_canal(config)
    etapa = str(est.get("etapa") or "")

    if not etapa or etapa in ("recusou", "encerrado", "falhou", "sem_preco"):
        return _apresentacao(nome_canal)
    if etapa in ("passado", "resultado", "oferta_passagem", "oferta_ajuda") and _RECOMECAR.search(baixo):
        return _apresentacao(nome_canal)

    if etapa == "passado":
        quem = (est.get("resultado") or {}).get("anfitria_nome") or "a corretora"
        return Resposta([f"Já pedi para {quem} falar com você. Se quiser fazer uma nova cotação, é só escrever "
                         "*nova cotação*."], est)

    if etapa == "consentimento":
        return await _no_consentimento(db, company_id, telefone_e164, t, est, nome_canal, llm)

    if etapa == "calculando":
        if not est.get("run_id") and _passou(est.get("disparado_em"), SEM_DISPARO_APOS_S):
            # o perfil fechou mas a cotação NÃO começou (ex.: o limite do dia barrou o disparo na entrada): a pessoa
            # não fica presa em "calculando" e as respostas (CPF…) não ficam guardadas
            novo = {k: v for k, v in est.items() if k not in ("respostas", "tentativas")}
            novo["etapa"] = "falhou"
            return Resposta(["Não consegui começar a sua cotação desta vez. Se quiser tentar de novo mais tarde, é só "
                             "escrever *nova cotação*."], novo)
        return Resposta(["Ainda estou calculando nas seguradoras. Assim que ficar pronto, te mando aqui. 🙂"], est)

    if etapa in ("resultado", "oferta_passagem"):
        return await _depois_do_resultado(db, company_id, telefone_e164, t, est, llm)

    if etapa == "oferta_ajuda":
        resposta = sim_nao(t)
        if resposta is True:
            from app.services.canal import cotacao

            ok = await cotacao.pedir_ajuda_humana(db, company_id, telefone_e164, est,
                                                  motivo=str(est.get("motivo_ajuda") or "fora_do_escopo"))
            est["etapa"] = "encerrado"
            est.pop("respostas", None)
            if ok:
                return Resposta(["Pronto! Pedi para a equipe falar com você por aqui."], est)
            return Resposta(["Anotei o seu pedido. Ainda não consegui avisar a equipe automaticamente — assim que "
                             "alguém estiver disponível, responde você por aqui."], est)
        if resposta is False:
            volta = est.pop("voltar_para", None)
            if volta in ETAPAS:
                est["etapa"] = volta
                return Resposta(["Combinado! Seguimos então.", _POR_CHAVE[volta].pergunta], est)
            est["etapa"] = "encerrado"
            return Resposta(["Tudo bem! Se precisar, é só mandar um oi."], est)
        return Resposta(["Quer que eu passe para uma pessoa? Pode responder sim ou não."], est)

    if etapa in ETAPAS:
        return await _no_roteiro(db, company_id, telefone_e164, t, midia, est, llm)

    logger.warning("[CANAL] etapa desconhecida no estado (%s) — recomeço", etapa[:30])
    return _apresentacao(nome_canal)


def _apresentacao(nome_canal: str) -> Resposta:
    est = _novo_estado()
    return Resposta([f"Oi! Aqui é o {nome_canal}. Eu comparo o seguro do seu carro em várias seguradoras, de graça e "
                     "sem compromisso.",
                     _texto_do_consentimento(nome_canal) + "\n\nPosso seguir? (sim ou não)"], est)


async def _no_consentimento(db, company_id, telefone, t, est, nome_canal, llm) -> Resposta:
    resposta = sim_nao(t)
    if resposta is None and t:
        lido = await entender("sim_nao", "Posso seguir com a cotação?", t, company_id=company_id, llm=llm)
        v = (lido or {}).get("valor")
        resposta = v if isinstance(v, bool) else None
    if resposta is True:
        await _registrar_consentimento(db, company_id, telefone, True)
        est.update({"etapa": ETAPAS[0], "consentimento": "sim", "consentimento_em": _agora_iso(),
                    "respostas": {}, "tentativas": {}})
        return Resposta(["Combinado! São umas perguntas rápidas, uma de cada vez.", ROTEIRO[0].pergunta], est)
    if resposta is False:
        await _registrar_consentimento(db, company_id, telefone, False)
        # G4: o "não" encerra e NADA fica além dele
        novo = {"versao": VERSAO_DO_ESTADO, "etapa": "recusou", "consentimento": "nao",
                "consentimento_em": _agora_iso()}
        return Resposta(["Tudo bem! Não guardei nenhum dado seu. Se mudar de ideia, é só mandar um oi."], novo)
    # nada de dado pessoal antes do "sim": o que veio não é guardado
    return Resposta(["Pra eu começar, preciso do seu ok. " + _texto_do_consentimento(nome_canal)
                     + "\n\nPosso seguir? (sim ou não)"], est)


async def _no_roteiro(db, company_id, telefone, t, midia, est, llm) -> Resposta:
    etapa = est["etapa"]
    passo = _POR_CHAVE[etapa]
    baixo = _sem_acento(t)

    if _RECOMECAR.search(baixo):
        est.update({"etapa": ETAPAS[0], "respostas": {}, "tentativas": {}})
        return Resposta(["Vamos do começo então.", ROTEIRO[0].pergunta], est)

    if midia:
        ref = {"tipo": str(midia.get("tipo") or "midia")[:20], "ref": _referencia_da_midia(midia)}
        if ref["ref"]:
            est.setdefault("midias", []).append(ref)
        if not t:
            return Resposta(["Recebi, obrigado! Guardei aqui.", passo.pergunta], est)

    if _FORA_DO_ESCOPO.search(baixo):
        return _oferecer_ajuda(est, "fora_do_escopo", voltar_para=etapa)

    valor, entendeu = _pela_regra(passo, t)
    if not entendeu and passo.tipo_do_modelo and t:
        lido = await entender(passo.tipo_do_modelo, passo.pergunta, t, company_id=company_id, llm=llm)
        if lido and lido.get("fora_do_escopo") is True:
            return _oferecer_ajuda(est, "fora_do_escopo", voltar_para=etapa)
        if lido and lido.get("valor") is not None:
            valor, entendeu = _reconferir(passo, lido.get("valor"))

    if not entendeu:
        tent = dict(est.get("tentativas") or {})
        tent[etapa] = int(tent.get(etapa) or 0) + 1
        est["tentativas"] = tent
        if tent[etapa] >= MAX_TENTATIVAS:
            return _oferecer_ajuda(est, "nao_entendi", voltar_para=etapa)
        return Resposta([f"Desculpa, não entendi. {passo.dica}", passo.pergunta], est)

    if etapa == "aplicativo" and valor is True:
        # 📊 o código de "aplicativo" em `tpUso` não foi medido (P-129B-05): cotar como particular seria errado
        return _oferecer_ajuda(est, "aplicativo", voltar_para=None,
                               frase="Pra carro de aplicativo eu ainda não consigo cotar por aqui. Posso pedir para "
                                     "uma corretora parceira falar com você — quer?")

    est.setdefault("respostas", {})[etapa] = valor
    proxima = ETAPAS.index(etapa) + 1
    if proxima < len(ETAPAS):
        est["etapa"] = ETAPAS[proxima]
        return Resposta([ROTEIRO[proxima].pergunta], est)

    perfil = montar_perfil(est["respostas"])
    falta = _perfil_fecha(perfil)
    if falta:   # defeito de código, nunca da pessoa — passa a uma pessoa em vez de mandar um pedido que a porta recusa
        logger.error("[CANAL] o perfil da conversa não fecha o pedido: %s", ", ".join(falta))
        return _oferecer_ajuda(est, "perfil_incompleto", voltar_para=None)
    est["etapa"] = "calculando"
    est["primeiro_nome"] = perfil["primeiro_nome"]
    est["premio_atual_declarado"] = perfil["premio_atual_declarado"]
    est["disparado_em"] = _agora_iso()
    return Resposta(["Perfeito, obrigado! Já estou calculando nas seguradoras pelas corretoras parceiras. Leva uns "
                     "minutinhos — te mando o resultado aqui."], est, disparar=perfil)


#: o perfil fechou e nenhum run nasceu depois disto → a cotação não começou
SEM_DISPARO_APOS_S = 120


def _passou(iso: Any, segundos: float) -> bool:
    try:
        t = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return True
    t = t if t.tzinfo else t.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - t).total_seconds() > segundos


def _referencia_da_midia(midia: Mapping[str, Any]) -> str:
    """Só a REFERÊNCIA da mídia (id/caminho no storage), nunca o conteúdo nem uma URL com credencial."""
    for chave in ("ref", "storage_ref", "path", "media_id", "id", "message_id"):
        v = str(midia.get(chave) or "").strip()
        if v and not v.lower().startswith(("http://", "https://", "data:")):
            return v[:200]
    return ""


def _pela_regra(passo: Passo, t: str) -> Tuple[Any, bool]:
    if passo.chave == "premio":
        return _inverter(validar_premio(t))
    v = passo.regra(t)
    return v, v is not None


def _inverter(par: Tuple[bool, Any]) -> Tuple[Any, bool]:
    return par[1], par[0]


def _reconferir(passo: Passo, valor: Any) -> Tuple[Any, bool]:
    """O que o modelo devolveu passa pela MESMA régua (o modelo nunca vence a regra)."""
    if passo.tipo_do_modelo == "sim_nao":
        return (valor, True) if isinstance(valor, bool) else (None, False)
    if passo.tipo_do_modelo == "sexo":
        return (valor, True) if valor in ("M", "F") else (None, False)
    if passo.chave == "premio":
        return _inverter(validar_premio(valor))
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        return None, False
    v = passo.regra(valor)
    return v, v is not None


def _oferecer_ajuda(est: dict, motivo: str, *, voltar_para: Optional[str], frase: Optional[str] = None) -> Resposta:
    est["etapa"] = "oferta_ajuda"
    est["motivo_ajuda"] = motivo
    if voltar_para:
        est["voltar_para"] = voltar_para
    else:
        est.pop("voltar_para", None)
    texto = frase or ("Por aqui eu faço só a cotação do seguro do carro. Posso pedir para uma pessoa da corretora "
                      "parceira falar com você — quer?")
    return Resposta([texto], est)


async def _depois_do_resultado(db, company_id, telefone, t, est, llm) -> Resposta:
    from app.services.canal import cotacao

    # qualquer resposta da pessoa cancela os lembretes (G8): marca no estado E pede o cancelamento do run
    est["respondeu_em"] = _agora_iso()
    await asyncio.to_thread(cotacao.cancelar_lembretes, db, company_id, est)
    res = est.get("resultado") or {}
    quem = res.get("anfitria_nome") or "a corretora"
    baixo = _sem_acento(t)

    if _FORA_DO_ESCOPO.search(baixo) and not _QUER_FECHAR.search(baixo):
        est["etapa"] = "oferta_passagem"
        return Resposta([f"Isso a {quem} resolve melhor que eu. Quer que eu peça para alguém de lá falar com você?"],
                        est)

    intencao = None
    resp = sim_nao(t)
    if _QUER_FECHAR.search(baixo) or resp is True:
        intencao = "fechar"
    elif resp is False:
        intencao = "nao"
    elif t:
        lido = await entender("intencao", "Quer fechar esse preço?", t, company_id=company_id, llm=llm)
        v = (lido or {}).get("valor")
        intencao = v if v in ("fechar", "nao", "duvida") else None

    if intencao == "fechar":
        baloes = await cotacao.passar_para_corretora(db, company_id, telefone, est)
        est["etapa"] = "passado"
        return Resposta(baloes, est)
    if intencao == "nao":
        est["etapa"] = "encerrado"
        validade = res.get("validade_ate")
        fim = f" O link continua valendo até {validade}, se quiser rever." if validade else ""
        return Resposta([f"Tudo bem! Obrigado por cotar com a gente.{fim}"], est)
    est["etapa"] = "oferta_passagem"
    return Resposta([f"Sem problema! Se tiver alguma dúvida, a {quem} pode te ajudar. Quer que eu peça para alguém de "
                     "lá falar com você? (sim ou não)"], est)
