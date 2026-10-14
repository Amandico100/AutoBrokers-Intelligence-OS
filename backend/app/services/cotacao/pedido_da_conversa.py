# -*- coding: utf-8 -*-
"""O PEDIDO a partir da CONVERSA do chat — SPEC-132-B (B1 · §2 o fio, §4 "A conversa").

    montar(dados, *, ficha=None, textos_crus=(), config=None) -> Montagem
        o que o corretor disse (os campos que o modelo leu da conversa) + a apólice anexada (a FICHA 130-B, quando há)
        → `pedido.de_ficha` (o MESMO miolo da renovação, sem o bloco dela) → `faltando()` com a placa suprindo
        FIPE/ano/combustível (`servico="cotacao"`, a MESMA regra do canal e da renovação).
    frase_do_que_falta(montagem) -> "Faltam: a data de nascimento do cliente e o CEP onde o carro dorme."
    resumo(montagem, onde, opcoes) -> o texto que o corretor confere ANTES de calcular (CPF mascarado)
    ficha_do_anexo(db, company_id, conversation_id, ...) -> a ficha estruturada do PDF anexado nesta conversa

🔴 As regras de validação são as do CANAL (`canal.conversa.validar_*`) — uma régua só para CPF, placa, CEP e data.
🔴 O CPF que o modelo devolve pode chegar MASCARADO (o guardrail do chat troca PII antes do modelo — Presidio,
   `guardrails.validate_input`). Quando o valor do modelo não fecha o dígito, a régua o procura no TEXTO CRU das
   últimas falas do corretor nesta conversa (`textos_crus`, lido do banco por quem chama) — e só aceita se houver UM.
⛔ Nada aqui é logado com valor. ⛔ O resumo nunca mostra o CPF inteiro (`renovacao.mascarar_documento`).
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

RAMO_AUTO, RAMO_RESIDENCIAL, RAMO_CONDOMINIO, RAMO_EMPRESARIAL = 31, 2, 16, 18

#: o que o corretor escreve → o ramo do Agger (os ramos que o motor calcula: `pedido.RAMOS_ACEITOS`)
RAMO_DO_TEXTO: Dict[str, int] = {
    "auto": RAMO_AUTO, "carro": RAMO_AUTO, "automovel": RAMO_AUTO, "veiculo": RAMO_AUTO, "31": RAMO_AUTO,
    "residencial": RAMO_RESIDENCIAL, "casa": RAMO_RESIDENCIAL, "apartamento": RAMO_RESIDENCIAL, "2": RAMO_RESIDENCIAL,
    "condominio": RAMO_CONDOMINIO, "16": RAMO_CONDOMINIO,
    "empresarial": RAMO_EMPRESARIAL, "empresa": RAMO_EMPRESARIAL, "comercio": RAMO_EMPRESARIAL, "18": RAMO_EMPRESARIAL,
}
#: o que NÃO sai por aqui, e a frase de gente (D-131-28: moto é SPEC própria; frota e RCF-V: `pedido.SIGLAS_AUTO_NAO_
#: COTADAS` — o pedido de AUTO do Agger é o de UM carro, com casco)
FRASE_FORA: Dict[str, str] = {
    "moto": "Moto eu ainda não coto por aqui — o cálculo que eu uso no Agger é o de carro. Cote a moto direto no Agger.",
    "frota": "Frota (vários veículos numa apólice só) eu ainda não coto por aqui — cote direto no Agger.",
    "rcfv": "Seguro só de responsabilidade civil (RCF-V) eu ainda não coto por aqui — cote direto no Agger.",
    "outro": "Por aqui eu coto carro, residencial, condomínio e empresarial. Esse ramo ainda não — cote direto no Agger.",
}
_FORA_DO_TEXTO = (("moto", re.compile(r"\b(moto|motos|motocicleta|motoneta|scooter|ciclomotor)\b")),
                  ("frota", re.compile(r"\bfrota\b")),
                  ("rcfv", re.compile(r"\b(rcf-?v|rcfv|so terceiros|so responsabilidade civil)\b")))

#: as opções de cada ramo quando a corretora não escolheu outras (`servicos.cotacao.opcoes`, a chave que a B2 põe no
#: Configurar): no carro as três da página de venda (Recomendada · Mais em conta · Mais completa, SPEC §4), no RE as
#: duas que os presets de RE têm (`presets.ORDEM_RE`)
OPCOES_DO_AUTO: Tuple[str, ...] = ("padrao", "economica", "completa_mais")
OPCOES_DO_RE: Tuple[str, ...] = ("padrao", "economica")
NOME_DA_OPCAO = {"padrao": "a completa (a base da Recomendada)", "economica": "a mais em conta",
                 "completa_mais": "a completa com mais coberturas", "minima": "a mínima"}

#: os rótulos de GENTE de cada campo que pode faltar ("grupo.campo" do contrato → a frase)
ROTULO: Dict[str, str] = {
    "segurado.cpf_cnpj": "o CPF do cliente (ou o CNPJ, se for empresa)",
    "segurado.nome": "o nome completo do cliente",
    "segurado.nascimento": "a data de nascimento do cliente",
    "segurado.sexo": "o sexo do cliente (a seguradora pede)",
    "segurado.estado_civil": "o estado civil do cliente",
    "segurado.cep": "o CEP do cliente (e o de onde o carro dorme, se for outro)",
    "veiculo.placa": "a placa do carro",
    "veiculo.fipe": "o código FIPE do carro",
    "veiculo.ano_fabricacao": "o ano de fabricação do carro",
    "veiculo.combustivel": "o combustível do carro",
    "pernoite.cep_pernoite": "o CEP onde o carro dorme",
    "condutor.cpf": "o CPF de quem mais dirige",
    "condutor.nome": "o nome de quem mais dirige",
    "condutor.nascimento": "a data de nascimento de quem mais dirige",
    "condutor.sexo": "o sexo de quem mais dirige",
    "condutor.estado_civil": "o estado civil de quem mais dirige",
    "condutor.tempo_habilitacao": "há quantos anos o principal condutor tem carteira de motorista",
    "risco.cep": "o CEP do imóvel",
    "risco.logradouro": "a rua do imóvel",
    "risco.bairro": "o bairro do imóvel",
    "risco.cidade": "a cidade do imóvel",
    "risco.uf": "o estado (UF) do imóvel",
    "risco.valor_basica": "o valor a segurar contra incêndio (a cobertura básica)",
    "risco.tipo_imovel": "o tipo do imóvel",
    "risco.construcao": "o tipo de construção",
    "risco.uso": "o uso do imóvel",
    "risco.objeto": "o que vai ser segurado (prédio, conteúdo ou os dois)",
    "risco.pavimento": "o pavimento do imóvel",
    "risco.localizacao": "onde fica o estabelecimento",
    "risco.atividade": "a atividade da empresa no local",
    "risco.estrutura": "a estrutura do condomínio",
    "risco.ano_fundacao": "o ano de fundação do condomínio",
    "comissao_desconto.comissao_percentual": "a comissão",
}
#: os três que a placa supre: sem a placa, pergunta-se A PLACA (uma pergunta, não três)
_DA_PLACA = ("veiculo.fipe", "veiculo.ano_fabricacao", "veiculo.combustivel")


def _sem_acento(texto: Any) -> str:
    from app.services.canal.conversa import _sem_acento as f

    return f(texto)


class ForaDoEscopo(ValueError):
    """O ramo/veículo não sai por aqui. `frase` é para o corretor."""

    def __init__(self, chave: str):
        self.chave = chave
        self.frase = FRASE_FORA.get(chave, FRASE_FORA["outro"])
        super().__init__(chave)


def ramo_do_texto(ramo: Any, *, descricao: Any = None) -> int:
    """"carro" → 31, "condomínio" → 16 … Moto, frota, RCF-V e o resto → `ForaDoEscopo` (com a frase)."""
    texto = _sem_acento(f"{ramo or ''} {descricao or ''}")
    for chave, padrao in _FORA_DO_TEXTO:
        if padrao.search(texto):
            raise ForaDoEscopo(chave)
    r = _sem_acento(ramo).strip()
    if not r:
        return RAMO_AUTO
    if r in RAMO_DO_TEXTO:
        return RAMO_DO_TEXTO[r]
    for palavra, valor in RAMO_DO_TEXTO.items():
        if not palavra.isdigit() and re.search(rf"\b{palavra}\b", r):
            return valor
    raise ForaDoEscopo("outro")


# =====================================================================================================================
# a régua (a do canal) e o texto cru
# =====================================================================================================================
def _validar(nome: str, valor: Any) -> Optional[Any]:
    from app.services.canal import conversa as C

    if valor is None or (isinstance(valor, str) and not valor.strip()):
        return None
    return {"cpf": C.validar_cpf, "placa": C.validar_placa, "cep": C.validar_cep, "data": C.validar_data,
            "sexo": C.validar_sexo, "nome": C.validar_nome}[nome](valor)


def validar_cnpj(texto: Any) -> Optional[str]:
    """14 dígitos com os dois dígitos verificadores (a regra da Receita)."""
    d = re.sub(r"\D", "", str(texto or ""))
    if len(d) != 14 or d == d[0] * 14:
        return None
    for n, pesos in ((12, (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)), (13, (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2))):
        soma = sum(int(d[i]) * pesos[i] for i in range(n))
        dv = 0 if soma % 11 < 2 else 11 - soma % 11
        if dv != int(d[n]):
            return None
    return d


def documento_valido(texto: Any) -> Optional[str]:
    return _validar("cpf", texto) or validar_cnpj(texto)


_CANDIDATOS = {
    "cpf": re.compile(r"(?<!\d)(\d{3}\.?\d{3}\.?\d{3}-?\d{2}|\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2})(?!\d)"),
    "placa": re.compile(r"\b([A-Za-z]{3}[\s-]?\d[A-Za-z0-9]\d{2})\b"),
    "cep": re.compile(r"(?<!\d)(\d{5}-?\d{3})(?!\d)"),
    "data": re.compile(r"\b(\d{1,2}[/.\-]\d{1,2}[/.\-]\d{4})\b"),
}


def unico_no_texto_cru(tipo: str, textos: Iterable[str], *, compativel_com: Any = None) -> Optional[str]:
    """O ÚNICO valor válido daquele tipo nas falas cruas do corretor (as mais recentes primeiro). Dois DIFERENTES →
    None (nunca escolhe: pergunta). ⛔ Nunca loga o que achou.

    `compativel_com` (só o CPF — conserto juiz B3): o valor MASCARADO que o modelo mandou para ESTE pedido
    (`***.***.***-25`, `<CPF>`). Só conta o achado que tem os MESMOS dígitos visíveis nas mesmas posições — o CPF de
    outro cliente da mesma conversa ("…-25" do João quando o da Maria é "…-31") nunca entra."""
    achados: List[str] = []
    for t in textos or ():
        for bruto in _CANDIDATOS[tipo].findall(str(t or "")):
            v = documento_valido(bruto) if tipo == "cpf" else _validar(tipo, bruto)
            if v and compativel_com is not None and not documento_compativel(v, compativel_com):
                continue
            if v and v not in achados:
                achados.append(v)
    return achados[0] if len(achados) == 1 else None


#: os caracteres com que uma máscara esconde um dígito (`***.***.***-25`, `xxx.xxx.xxx-25`, `•••`, `#`)
_CURINGA = set("*xX•#_?")


def documento_compativel(documento: str, mascarado: Any) -> bool:
    """O documento achado (só dígitos) CABE no valor mascarado que o modelo mandou? Cada dígito visível tem de estar
    na MESMA posição (contada do FIM — a máscara da renovação mostra os 2 últimos). Sem dígito visível (`<CPF>`), cabe
    (a conferência dos dígitos verificadores e o "único" fazem o resto). Mais dígitos visíveis que o documento → não."""
    texto = str(mascarado or "")
    sinais = [ch for ch in texto if ch.isdigit() or ch in _CURINGA]
    visiveis = [ch for ch in sinais if ch.isdigit()]
    if not visiveis:
        return True
    if len(sinais) > len(documento):
        return False
    for i, ch in enumerate(reversed(sinais)):
        if ch.isdigit() and documento[len(documento) - 1 - i] != ch:
            return False
    return True


def valor_em_reais(texto: Any) -> Optional[float]:
    """O dinheiro como o corretor (ou o modelo) escreve: "4.200" → 4200 · "4200.00" → 4200,00 · "3.500,50" → 3500,50 ·
    "3500.50" → 3500,50 · "R$ 4.200,00" → 4200,00 · 4200 → 4200. O separador que tem 1–2 dígitos depois é o decimal;
    com 3 dígitos depois (e nada além) é o de milhar. Ilegível, zero ou negativo → None (nunca um número inventado).
    🔴 Conserto RT B-1: o parser antigo apagava TODO ponto — "4200.00" virava 420.000."""
    if isinstance(texto, bool) or texto is None:
        return None
    if isinstance(texto, (int, float)):
        return round(float(texto), 2) if float(texto) > 0 else None
    limpo = re.sub(r"(?i)r\$|reais|\s", "", str(texto)).strip()
    if not limpo or not re.fullmatch(r"\d[\d.,]*", limpo):
        return None
    ultimo = max(limpo.rfind("."), limpo.rfind(","))
    if ultimo == -1:
        inteiro, decimal = limpo, ""
    else:
        depois = limpo[ultimo + 1:]
        if len(depois) in (1, 2):                      # o último separador é o decimal
            inteiro, decimal = limpo[:ultimo], depois
        elif len(depois) == 3:                         # milhar ("4.200", "1,234,567")
            inteiro, decimal = limpo, ""
        else:
            return None
    inteiro = re.sub(r"[.,]", "", inteiro)
    if not inteiro.isdigit():
        return None
    valor = float(f"{inteiro}.{decimal or '0'}")
    return round(valor, 2) if valor > 0 else None


# =====================================================================================================================
# a MONTAGEM
# =====================================================================================================================
@dataclass
class Montagem:
    ramo: int
    pedido: Any                                     # PedidoDeCalculo (ou None quando nem montou)
    faltam: List[str] = field(default_factory=list)          # "grupo.campo" (nomes, nunca valores)
    problemas: List[str] = field(default_factory=list)       # frases: "o CPF não confere (…)"
    inferidos: Dict[str, str] = field(default_factory=dict)  # "grupo.campo" → como foi deduzido (para o resumo)
    situacao: str = "novo_sem_apolice"
    apolice_atual: Optional[Dict[str, Any]] = None
    descricao: Optional[str] = None
    do_anexo: bool = False
    #: o que o corretor DISSE do seguro de hoje (seguradora, prêmio) — só para o resumo dele, nunca para a página
    seguro_declarado: Optional[Dict[str, Any]] = None

    @property
    def completa(self) -> bool:
        return self.pedido is not None and not self.faltam and not self.problemas


def _limpo(v: Any) -> Any:
    if isinstance(v, str):
        v = v.strip()
        return v or None
    return v


def _ano(v: Any) -> Optional[int]:
    try:
        n = int(str(v).strip()[:4]) if v is not None and str(v).strip() else None
    except ValueError:
        return None
    return n if n and 1950 <= n <= 2100 else None


def _inteiro(v: Any, *, minimo: int = 0, maximo: int = 80) -> Optional[int]:
    if isinstance(v, bool) or v is None:
        return None
    try:
        n = int(float(str(v).replace(",", ".").strip()))
    except ValueError:
        m = re.search(r"\d+", str(v))
        n = int(m.group(0)) if m else None
    return n if n is not None and minimo <= n <= maximo else None


def _sim_nao(v: Any) -> Optional[bool]:
    if isinstance(v, bool):
        return v
    if v is None:
        return None
    from app.services.canal.conversa import sim_nao

    return sim_nao(v)


def montar(dados: Mapping[str, Any], *, ficha: Any = None, textos_crus: Sequence[str] = (),
           config: Optional[Mapping[str, Any]] = None) -> Montagem:
    """Os campos que o modelo leu da conversa (`dados`, nomes desta ferramenta — ver `cotacao_tool._PrepararIn`) + a
    ficha do anexo → `Montagem`. Levanta `ForaDoEscopo` para moto/frota/RCF-V/ramo que o motor não calcula."""
    from app.services.canal.conversa import ESTADO_CIVIL_PADRAO, limiar_do_sexo_pelo_nome, sexo_pelo_nome
    from app.services.multicalculo.pedido import CampoDesconhecido, RamoIndisponivel, de_ficha

    d = {k: _limpo(v) for k, v in dict(dados or {}).items()}
    descricao = d.get("descricao_do_veiculo") or d.get("descricao")
    ramo = ramo_do_texto(d.get("ramo"), descricao=descricao)
    problemas: List[str] = []
    inferidos: Dict[str, str] = {}

    # -- o documento do cliente: o do modelo, ou o ÚNICO válido no texto cru (o modelo pode ter visto mascarado) ------
    doc = documento_valido(d.get("cpf_cnpj")) if d.get("cpf_cnpj") else None
    if not doc and d.get("cpf_cnpj"):
        # 🔴 conserto juiz B3: o texto cru só é lido quando o MODELO indicou um CPF (mascarado) PARA ESTE pedido — e o
        #    achado tem de casar com os dígitos visíveis dele. Sem CPF do modelo, o CPF de OUTRO cliente da conversa
        #    nunca completa o pedido: falta o CPF, e a ferramenta pergunta.
        doc = unico_no_texto_cru("cpf", textos_crus, compativel_com=d.get("cpf_cnpj"))
        if not doc and not re.search(r"[*<x•#]|mascar", str(d.get("cpf_cnpj")), re.I):
            problemas.append("o CPF/CNPJ que veio não confere (o dígito verificador não bate) — confira e me mande "
                             "de novo")
    seg: Dict[str, Any] = {}
    if doc:
        seg["cpf_cnpj"] = doc
        seg["tipo_pessoa"] = "J" if len(doc) == 14 else "F"
    nome = d.get("nome")
    if nome:
        nome_ok = _validar("nome", nome)
        if nome_ok:
            seg["nome"] = nome_ok
        else:
            problemas.append("o nome do cliente precisa vir completo (nome e sobrenome)")
    for campo, chave in (("email", "email"), ("telefone", "telefone")):
        if d.get(chave):
            seg[campo] = d[chave]

    if ramo == RAMO_AUTO:
        perfil = _perfil_auto(d, seg, textos_crus, problemas, inferidos, config=config,
                              estado_civil_padrao=ESTADO_CIVIL_PADRAO,
                              sexo_pelo_nome=sexo_pelo_nome, limiar=limiar_do_sexo_pelo_nome)
    else:
        perfil = _perfil_re(d, seg, ramo, textos_crus, problemas)

    if ficha is not None and ramo == RAMO_AUTO:
        from app.services.multicalculo.pedido import veiculo_nao_cotado

        tipo = veiculo_nao_cotado(descricao, ((ficha or {}).get("objeto_do_risco") or {}).get("descricao")
                                  if isinstance(ficha, Mapping) else None)
        if tipo == "moto":
            raise ForaDoEscopo("moto")
    try:
        pedido = de_ficha(ficha, perfil, ramo=ramo)
    except RamoIndisponivel as exc:
        raise ForaDoEscopo("moto" if "moto" in str(exc).lower() else "outro") from None
    except CampoDesconhecido as exc:
        # o NOME do campo pode ir ao log; o valor, nunca (a mensagem do contrato só tem o nome)
        logger.info("[COTACAO] campo fora do contrato: %s", str(exc)[:80])
        problemas.append("um dos dados do imóvel não é um campo que a seguradora pede ("
                         + str(exc).split(":")[-1].strip()[:40] + ")")
        return Montagem(ramo=ramo, pedido=None, problemas=problemas, inferidos=inferidos, descricao=descricao)

    faltam = pedido.faltando(origem="auxiliar", servico="cotacao")
    faltam += [c for c in pedido.sem_codigo() if c not in faltam]
    if ramo == RAMO_AUTO:
        # o que a placa supre fica DECLARADO ("o Agger preenche pela placa") — a MESMA chamada que a porta faz
        pedido = pedido.assumindo_pela_placa(servico="cotacao")
    for k in list(inferidos):
        if "." in k and pedido.valor(*k.split(".", 1)) is None:
            inferidos.pop(k)
    situacao, apolice_atual, declarado = seguro_atual(d, ficha)
    return Montagem(ramo=ramo, pedido=pedido, faltam=faltam, problemas=problemas, inferidos=inferidos,
                    situacao=situacao, apolice_atual=apolice_atual, descricao=descricao, do_anexo=ficha is not None,
                    seguro_declarado=declarado)


def premio_conferido_da_ficha(ficha: Any) -> Optional[float]:
    """O prêmio que a FICHA da 130-B CONFERIU: a leitura fechou (a soma das coberturas bate com o prêmio líquido
    impresso — `leitura.estado == "fechou"`), o documento é uma APÓLICE e o prêmio esperado é um número > 0. Qualquer
    outra coisa (não fechou, endosso, proposta, sem prêmio) → None. ⚠️ É o prêmio LÍQUIDO (sem IOF): a página diz isso."""
    if not isinstance(ficha, Mapping):
        return None
    leitura = ficha.get("leitura") if isinstance(ficha.get("leitura"), Mapping) else {}
    tipo = str(leitura.get("tipo_documento") or ficha.get("tipo_documento") or "")
    if str(leitura.get("estado") or "") != "fechou" or tipo != "apolice":
        return None
    return valor_em_reais(leitura.get("premio_esperado"))


def seguro_atual(d: Mapping[str, Any], ficha: Any) -> Tuple[str, Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """(situacao, apolice_atual, seguro_declarado) — conserto juiz B2 + RT B-1 (SPEC §4.4, D-132B-02, mutação 5).

    🔴 `novo_com_apolice` (e com ela a "economia" na página do CLIENTE) SÓ com a apólice ANEXADA nesta conversa, lida
       pela ficha da 130-B, com o prêmio CONFERIDO (`premio_conferido_da_ficha`). O prêmio é o da FICHA — nunca o que
       o modelo escreveu — e vai com `origem="documento"` e `base="liquido"`.
    ⛔ O que o corretor DIGITOU ("ele paga 4.200 hoje na Porto") vira `seguro_declarado`: aparece no RESUMO que ele
       confere ("o cliente disse que paga…") e nunca vai à página do cliente."""
    seguradora = str(d.get("seguradora_atual") or "").strip() or None
    premio_dito = valor_em_reais(d.get("premio_atual_anual"))
    declarado = None
    if seguradora or premio_dito:
        declarado = {k: v for k, v in (("seguradora", seguradora), ("premio_anual", premio_dito)) if v}
    premio_lido = premio_conferido_da_ficha(ficha)
    if ficha is not None and seguradora and premio_lido:
        return "novo_com_apolice", {"seguradora": seguradora, "premio_anual": premio_lido, "origem": "documento",
                                    "base": "liquido"}, declarado
    return "novo_sem_apolice", None, declarado


def _perfil_auto(d: Mapping[str, Any], seg: Dict[str, Any], textos_crus: Sequence[str], problemas: List[str],
                 inferidos: Dict[str, str], *, config: Any, estado_civil_padrao: int, sexo_pelo_nome: Any,
                 limiar: Any) -> Dict[str, Dict[str, Any]]:
    nasc = _validar("data", d.get("nascimento")) if d.get("nascimento") else None
    if d.get("nascimento") and not nasc:
        nasc = unico_no_texto_cru("data", textos_crus)
        if not nasc:
            problemas.append("a data de nascimento precisa vir como dia/mês/ano, de alguém entre 18 e 100 anos")
    if nasc:
        seg["nascimento"] = nasc
    sexo = _validar("sexo", d.get("sexo")) if d.get("sexo") else None
    if not sexo and seg.get("nome"):
        sexo = sexo_pelo_nome(seg["nome"], min_pct=limiar(config))
        if sexo:
            inferidos["segurado.sexo"] = "pelo nome — corrija se não for"
    if sexo:
        seg["sexo"] = sexo
    cep = _validar("cep", d.get("cep")) or (unico_no_texto_cru("cep", textos_crus) if d.get("cep") else None)
    if d.get("cep") and not cep:
        problemas.append("o CEP do cliente precisa ter 8 números")
    if cep:
        seg["cep"] = cep
    seg["estado_civil"] = estado_civil_padrao                # o canal faz igual (o rótulo de cada código não foi medido)
    inferidos["segurado.estado_civil"] = "não perguntado — vai o padrão do Agger"

    veic: Dict[str, Any] = {}
    placa = _validar("placa", d.get("placa")) if d.get("placa") else None
    if d.get("placa") and not placa:
        placa = unico_no_texto_cru("placa", textos_crus)
        if not placa:
            problemas.append("a placa precisa ter 7 caracteres, tipo ABC1D23 ou ABC1234")
    if placa:
        veic["placa"] = placa
    if d.get("fipe"):
        fipe = re.sub(r"\D", "", str(d["fipe"]))
        if len(fipe) == 7:
            veic["fipe"] = fipe
        else:
            problemas.append("o código FIPE tem 7 números (ex.: 001327-7) — se não souber, a placa basta")
    for campo in ("ano_fabricacao", "ano_modelo"):
        if _ano(d.get(campo)):
            veic[campo] = _ano(d.get(campo))
    if d.get("combustivel"):
        veic["combustivel"] = _sem_acento(d["combustivel"]).strip()
    for campo in ("zero_km",):
        if _sim_nao(d.get(campo)) is not None:
            veic[campo] = _sim_nao(d.get(campo))
    if d.get("chassi"):
        veic["chassi"] = d["chassi"]

    pern: Dict[str, Any] = {}
    cep_p = _validar("cep", d.get("cep_pernoite")) if d.get("cep_pernoite") else None
    if d.get("cep_pernoite") and not cep_p:
        problemas.append("o CEP onde o carro dorme precisa ter 8 números")
    if cep_p:
        pern["cep_pernoite"] = cep_p
    elif cep:
        inferidos["pernoite.cep_pernoite"] = "o mesmo CEP do cliente"

    cond: Dict[str, Any] = {}
    anos = _inteiro(d.get("anos_de_carteira"))
    if d.get("anos_de_carteira") is not None and anos is None:
        problemas.append("os anos de carteira precisam ser um número (ex.: 10)")
    if anos is not None:
        cond["tempo_habilitacao"] = anos
    jovem = _sim_nao(d.get("jovem_condutor"))
    if jovem is not None:
        cond["jovem_condutor"] = jovem
    cpf_c = documento_valido(d.get("condutor_cpf")) if d.get("condutor_cpf") else None
    if cpf_c and cpf_c != seg.get("cpf_cnpj"):
        cond.update({"cpf": cpf_c, "estado_civil": estado_civil_padrao})
        for de, para, regra in (("condutor_nome", "nome", "nome"), ("condutor_nascimento", "nascimento", "data"),
                                ("condutor_sexo", "sexo", "sexo")):
            v = _validar(regra, d.get(de)) if d.get(de) else None
            if v:
                cond[para] = v
        if "sexo" not in cond and cond.get("nome"):
            s = sexo_pelo_nome(cond["nome"], min_pct=limiar(config))
            if s:
                cond["sexo"] = s
                inferidos["condutor.sexo"] = "pelo nome — corrija se não for"
    else:
        inferidos["condutor"] = "o próprio cliente"
    return {"segurado": seg, "veiculo": veic, "pernoite": pern, "condutor": cond}


def _perfil_re(d: Mapping[str, Any], seg: Dict[str, Any], ramo: int, textos_crus: Sequence[str],
               problemas: List[str]) -> Dict[str, Dict[str, Any]]:
    """RE: o segurado (só os campos do catálogo DO RAMO) + o `risco` como o modelo o montou (nomes do contrato)."""
    from app.services.multicalculo.pedido import catalogo_do_ramo

    cat = catalogo_do_ramo(ramo)
    nomes_seg = {e[0] for e in cat.get("segurado", ())}
    if "nascimento" in nomes_seg and d.get("nascimento"):
        nasc = _validar("data", d.get("nascimento")) or unico_no_texto_cru("data", textos_crus)
        if nasc:
            seg["nascimento"] = nasc
        else:
            problemas.append("a data de nascimento precisa vir como dia/mês/ano")
    if "sexo" in nomes_seg and _validar("sexo", d.get("sexo")):
        seg["sexo"] = _validar("sexo", d.get("sexo"))
    seg = {k: v for k, v in seg.items() if k in nomes_seg}
    risco = {str(k): _limpo(v) for k, v in dict(d.get("risco") or {}).items() if _limpo(v) is not None}
    if risco.get("cep"):
        cep = _validar("cep", risco["cep"])
        if cep:
            risco["cep"] = cep
        else:
            problemas.append("o CEP do imóvel precisa ter 8 números")
            risco.pop("cep")
    return {"segurado": seg, "risco": risco}


# =====================================================================================================================
# as FRASES de gente
# =====================================================================================================================
def _rotulo(chave: str) -> str:
    if chave in ROTULO:
        return ROTULO[chave]
    campo = chave.split(":")[0].split(".")[-1].replace("_", " ")
    return f"o campo {campo}"


def _juntar(itens: Sequence[str]) -> str:
    itens = [i for i in itens if i]
    if len(itens) <= 1:
        return "".join(itens)
    return ", ".join(itens[:-1]) + " e " + itens[-1]


def rotulos_do_que_falta(faltam: Sequence[str], *, tem_placa: bool, condutor_e_o_cliente: bool = True) -> List[str]:
    """As frases do que falta, sem repetição; sem a placa, os três que ela supre viram UMA pergunta: a placa. Quando
    quem mais dirige é o próprio cliente, o `condutor.X` que falta junto com o `segurado.X` é a MESMA pergunta."""
    vistos: List[str] = []
    da_placa = [f for f in faltam if f in _DA_PLACA]
    pares = {"condutor.cpf": "segurado.cpf_cnpj", "condutor.nome": "segurado.nome",
             "condutor.nascimento": "segurado.nascimento", "condutor.sexo": "segurado.sexo",
             "condutor.estado_civil": "segurado.estado_civil"}
    for f in faltam:
        if condutor_e_o_cliente and f in pares and pares[f] in faltam:
            continue
        if f == "pernoite.cep_pernoite" and "segurado.cep" in faltam:
            continue                                      # o CEP de pernoite é o do cliente quando ele não diz outro
        if f in _DA_PLACA and not tem_placa:
            rot = "a placa do carro (com ela eu acho modelo, ano e combustível)"
        else:
            rot = _rotulo(f)
        if rot not in vistos:
            vistos.append(rot)
    if da_placa and tem_placa:
        logger.info("[COTACAO] a placa veio e ainda falta %s", ",".join(da_placa))
    return vistos


def frase_do_que_falta(m: Montagem) -> str:
    partes: List[str] = []
    if m.faltam:
        tem_placa = bool(m.pedido is not None and m.pedido.valor("veiculo", "placa"))
        partes.append("Faltam: " + _juntar(rotulos_do_que_falta(
            m.faltam, tem_placa=tem_placa, condutor_e_o_cliente="condutor" in m.inferidos)) + ".")
    if m.problemas:
        partes.append("E preciso conferir: " + _juntar(m.problemas) + ".")
    return " ".join(partes)


def opcoes_da_cotacao(config: Optional[Mapping[str, Any]], ramo: int) -> Tuple[str, ...]:
    """As opções que a corretora pediu (`servicos.cotacao.opcoes`) — só as que a porta aceita no ramo, na ordem do
    disparo — ou as do produto. Lista vazia/ilegível → as do produto (nunca um cálculo sem opção)."""
    from app.services.multicalculo.porta import OPCOES_POR_RAMO

    aceitas = OPCOES_POR_RAMO.get(int(ramo)) or OPCOES_DO_AUTO
    padrao = OPCOES_DO_AUTO if int(ramo) == RAMO_AUTO else OPCOES_DO_RE
    serv = (config or {}).get("servicos") if isinstance(config, Mapping) else None
    pedidas = ((serv or {}).get("cotacao") or {}).get("opcoes") if isinstance(serv, Mapping) else None
    if isinstance(pedidas, (list, tuple)):
        escolhidas = tuple(o for o in aceitas if o in set(map(str, pedidas)))
        if escolhidas:
            return escolhidas
    return tuple(o for o in aceitas if o in padrao)


def _data_br(iso: Any) -> str:
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", str(iso or ""))
    return f"{m.group(3)}/{m.group(2)}/{m.group(1)}" if m else str(iso or "")


def _cep_br(cep: Any) -> str:
    d = re.sub(r"\D", "", str(cep or ""))
    return f"{d[:5]}-{d[5:]}" if len(d) == 8 else str(cep or "")


def resumo(m: Montagem, *, onde: str, opcoes: Sequence[str]) -> str:
    """O que o corretor CONFERE antes de calcular. ⛔ O CPF sai mascarado (só os 2 últimos)."""
    from app.services.multicalculo.renovacao import mascarar_documento

    p = m.pedido
    v = p.valor
    linhas = ["Confira antes de eu calcular:"]
    doc = mascarar_documento(v("segurado", "cpf_cnpj")) or "(sem documento)"
    cliente = f"- Cliente: {v('segurado', 'nome') or '(sem nome)'} — {'CNPJ' if len(str(v('segurado', 'cpf_cnpj') or '')) == 14 else 'CPF'} {doc}"
    if v("segurado", "nascimento"):
        cliente += f", nascimento {_data_br(v('segurado', 'nascimento'))}"
    if v("segurado", "sexo"):
        cliente += ", sexo " + ("masculino" if v("segurado", "sexo") == "M" else "feminino")
        if "segurado.sexo" in m.inferidos:
            cliente += f" ({m.inferidos['segurado.sexo']})"
    linhas.append(cliente)
    if m.ramo == RAMO_AUTO:
        carro = f"- Carro: placa {v('veiculo', 'placa')}" if v("veiculo", "placa") else "- Carro: sem placa"
        if m.descricao:
            carro += f" ({m.descricao})"
        supridos = [c for c in _DA_PLACA if c in p.assumidos]
        if supridos:
            carro += " — modelo, ano e combustível o Agger lê pela placa"
        elif v("veiculo", "fipe"):
            carro += f", FIPE {v('veiculo', 'fipe')}, ano {v('veiculo', 'ano_fabricacao') or '?'}"
        linhas.append(carro)
        linhas.append(f"- CEP do cliente: {_cep_br(v('segurado', 'cep'))} · onde o carro dorme: "
                      f"{_cep_br(v('pernoite', 'cep_pernoite'))}"
                      + (" (o mesmo)" if "pernoite.cep_pernoite" in p.assumidos else ""))
        cond = "o próprio cliente" if "condutor.relacao_com_segurado" in p.assumidos or "condutor" in m.inferidos \
            else f"{v('condutor', 'nome') or 'outra pessoa'} (CPF {mascarar_documento(v('condutor', 'cpf'))})"
        anos = v("condutor", "tempo_habilitacao")
        linhas.append(f"- Quem mais dirige: {cond}" + (f", carteira há {anos} ano(s)" if anos is not None else ""))
        jovem = v("condutor", "jovem_condutor")
        uso = "uso, garagem e quilometragem: o padrão do Agger (não perguntei)"
        if jovem is not None:
            uso += " · alguém de 18 a 25 anos dirige: " + ("sim" if jovem else "não")
        linhas.append(f"- {uso[0].upper()}{uso[1:]}")
    else:
        r = p.campos.get("risco") or {}
        end = ", ".join(str(r[k]) for k in ("logradouro", "numero", "bairro", "cidade", "uf") if r.get(k))
        nome_ramo = {RAMO_RESIDENCIAL: "Residencial", RAMO_CONDOMINIO: "Condomínio",
                     RAMO_EMPRESARIAL: "Empresarial"}.get(m.ramo, "Imóvel")
        linhas.append(f"- {nome_ramo}: {end or 'endereço não informado'} — CEP {_cep_br(r.get('cep'))}")
        if r.get("valor_basica") is not None:
            from app.providers.policy_data_provider import reais

            linhas.append(f"- Cobertura básica (incêndio): {reais(r.get('valor_basica'))}")
    if m.do_anexo:
        linhas.append("- Da apólice anexada eu usei: " + (_juntar([x for x in (
            "a placa" if "veiculo.placa" in (p.campos.get("veiculo") or {}) else "",
            "o CEP" if "segurado.cep" in p.assumidos or "risco.cep" in p.assumidos else "") if x]) or "nada além do que você disse"))
    if m.apolice_atual:
        from app.providers.policy_data_provider import reais

        linhas.append(f"- Seguro atual (da apólice anexada): {m.apolice_atual.get('seguradora')}, prêmio líquido "
                      f"{reais(m.apolice_atual.get('premio_anual'))} por ano — a apresentação mostra ao cliente quanto "
                      "ele economiza")
    elif m.seguro_declarado:
        from app.providers.policy_data_provider import reais

        dito = m.seguro_declarado
        partes = [x for x in (dito.get("seguradora"),
                              f"{reais(dito['premio_anual'])} por ano" if dito.get("premio_anual") else None) if x]
        linhas.append("- O cliente disse que paga hoje: " + ", ".join(partes) + " (sem a apólice anexada isso não vai "
                      "para a apresentação do cliente — para mostrar a economia, anexe a apólice atual)")
    nomes = [NOME_DA_OPCAO.get(o, o) for o in opcoes]
    linhas.append(f"- Vou calcular {len(nomes)} versões: {_juntar(nomes)}"
                  + (" — na resposta mostro a Recomendada, a Mais em conta e a Mais completa." if m.ramo == RAMO_AUTO
                     else "."))
    linhas.append(f"- Onde: {onde}")
    if p.avisos:
        if "placa_diverge_do_documento" in p.avisos:
            linhas.append("- Atenção: a placa que você disse é diferente da que está na apólice — vale a que você disse.")
        if "documento_nao_e_a_apolice" in p.avisos:
            linhas.append("- Atenção: o arquivo anexado não parece ser a apólice (endosso, proposta ou documento do carro).")
    return "\n".join(linhas)


# =====================================================================================================================
# a FICHA do anexo desta conversa (a 132-A grava `messages.payload.attachments = [{nome, mime, bytes, path, bucket?}]`)
# =====================================================================================================================
BUCKET_PADRAO_DOS_DOCUMENTOS = "chat-docs"
_PDF = re.compile(r"\.pdf$", re.I)


def anexos_da_conversa(db: Any, company_id: str, conversation_id: str, *, limite: int = 20) -> List[Dict[str, Any]]:
    """Os anexos (PDF) das últimas falas do corretor NESTA conversa, o mais recente primeiro. 🔴 Só os do prefixo DESTA
    corretora (`<company_id>/…` — o mesmo que a rota de upload exige): um path de fora nunca é lido (CLAUDE.md §7).
    A conversa é conferida por quem chama (`conversations.company_id`)."""
    cli = getattr(db, "client", db)
    linhas = list(getattr(cli.table("messages").select("id, conversation_id, role, payload, created_at")
                          .eq("conversation_id", str(conversation_id)).eq("role", "user")
                          .order("created_at", desc=True).limit(limite).execute(), "data", None) or [])
    saida: List[Dict[str, Any]] = []
    for l in linhas:
        if str(l.get("conversation_id")) != str(conversation_id):
            continue
        for a in ((l.get("payload") or {}).get("attachments") or []) if isinstance(l.get("payload"), Mapping) else []:
            if not isinstance(a, Mapping):
                continue
            path = str(a.get("path") or "")
            nome = str(a.get("nome") or a.get("name") or "")
            mime = str(a.get("mime") or "")
            if not path.startswith(f"{company_id}/"):
                continue
            if "pdf" not in mime.lower() and not _PDF.search(nome or path):
                continue
            saida.append({"path": path, "nome": nome or path.rsplit("/", 1)[-1],
                          "bucket": str(a.get("bucket") or BUCKET_PADRAO_DOS_DOCUMENTOS)})
    return saida


def textos_crus_da_conversa(db: Any, conversation_id: str, *, limite: int = 12) -> List[str]:
    """As últimas falas do corretor nesta conversa, como ele as escreveu (o banco guarda o texto que ELE digitou).
    ⛔ Só para a régua de CPF/placa/CEP/data — nunca vai ao modelo nem ao log."""
    cli = getattr(db, "client", db)
    try:
        linhas = list(getattr(cli.table("messages").select("conversation_id, role, content, created_at")
                              .eq("conversation_id", str(conversation_id)).eq("role", "user")
                              .order("created_at", desc=True).limit(limite).execute(), "data", None) or [])
    except Exception as exc:  # noqa: BLE001 — sem o texto cru, vale o que o modelo mandou
        logger.warning("[COTACAO] falas cruas ilegíveis (%s)", type(exc).__name__)
        return []
    return [str(l.get("content") or "") for l in linhas if str(l.get("conversation_id")) == str(conversation_id)]


async def ficha_do_anexo(db: Any, company_id: str, conversation_id: str, *, nome: Optional[str] = None,
                         ler: Any = None, baixar: Any = None) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """(a ficha estruturada, aviso). Acha o PDF anexado nesta conversa (pelo nome, ou o mais recente), baixa os BYTES
    do Storage pelo service role (o prefixo da corretora conferido) e o lê com o leitor ÚNICO da 130-B
    (`policy_document_evidence_service.ler_anexo_de_seguro`, em memória — nada é gravado). `ler`/`baixar`: dublês."""
    import asyncio

    try:
        anexos = await asyncio.to_thread(anexos_da_conversa, db, company_id, conversation_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[COTACAO] anexos da conversa ilegíveis (%s)", type(exc).__name__)
        return None, "Não consegui achar o arquivo anexado nesta conversa."
    if nome:
        alvo = _sem_acento(nome).strip()
        anexos = [a for a in anexos if alvo and alvo in _sem_acento(a["nome"])] or anexos[:0]
    if not anexos:
        return None, "Não achei uma apólice em PDF anexada nesta conversa — anexe o PDF e me peça de novo."
    a = anexos[0]
    try:
        if baixar is None:
            cli = getattr(db, "client", db)
            dados = await asyncio.to_thread(lambda: cli.storage.from_(a["bucket"]).download(a["path"]))
        else:
            dados = await baixar(a["bucket"], a["path"])
    except Exception as exc:  # noqa: BLE001
        logger.warning("[COTACAO] o anexo não baixou (%s)", type(exc).__name__)
        return None, "Não consegui abrir o arquivo anexado — anexe de novo, por favor."
    if ler is None:
        from app.services.policy_document_evidence_service import ler_anexo_de_seguro as ler
    try:
        ficha = await ler(dados, a["nome"], company_id=company_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[COTACAO] a leitura do anexo falhou (%s)", type(exc).__name__)
        return None, "Não consegui ler a apólice anexada — me diga os dados do carro que eu sigo sem ela."
    if not isinstance(ficha, Mapping) or (ficha.get("leitura") or {}).get("estado") == "falhou" \
            and not any((ficha.get("objeto_do_risco") or {}).values()):
        return None, "Não consegui ler a apólice anexada — me diga os dados do carro que eu sigo sem ela."
    return dict(ficha), None
