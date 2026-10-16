# -*- coding: utf-8 -*-
"""O PERFIL DA RENOVAÇÃO — o que o pedido do Agger exige e a apólice não traz. SPEC-131-A F5.

> **O TESTE DO PRODUTO:** 📊 canário da F4 (13/10): todo AUTO real ficou `pendente(falta_dado)` com 16 campos faltando
> (CPF, nascimento, sexo, estado civil, CEP, FIPE, ano, combustível, condutor, tempo de habilitação). Sem o perfil,
> NADA é calculado — a madrugada inteira entrega só pendências.

    montar(company_id, item, apolice, ficha, fonte) -> (perfil, nao_conferidos)

`perfil` = {grupo: {campo: valor}} nos nomes do contrato DO RAMO (`pedido.catalogo_do_ramo`) — o que `pedido.de_apolice`
recebe. `nao_conferidos` = {"grupo.campo": "porquê"}: TODA suposição sai marcada, com o motivo escrito (CLAUDE.md §9.5);
a madrugada põe esses nomes em `assumidos` do pedido (o robô e a página sabem que não vieram da pessoa) e no evento.

A ORDEM de cada campo (o que vence):
    1. a InfoCap, MEDIDA (📊 12/10, 10 AUTO reais, só contagens — ver `fonte_infocap.documento_cru` e vizinhos):
         `/documento` codcli · sinistro  ·  `/cliente` cpf_cnpj · datanas · sexo · estado_civil · enderecos[].cep
         `/itens` (na data) placa · anofab · anomod · combustível · bonusclas · e, no RE, o endereço do risco
    2. a ficha da apólice (`pedido.de_apolice` já a usa: placa, chassi, ano modelo, a vigência, a seguradora)
    3. a REGRA declarada da renovação — cada uma abaixo, com o porquê ao lado da constante, e SEMPRE marcada
⛔ O que muda o preço e não tem fonte nem regra fica de FORA: o pedido sai `pendente(falta_dado)` com o NOME do campo.
⛔ Nada aqui é logado com valor; CPF/CNPJ só passa pelo validador (`documento_br.documento_valido`) e pelo HMAC da
   conferência de identidade — o pedido o cifra (`porta._cifrar`). ⛔ Nenhum nome de corretora (CLAUDE.md §13.9).
"""
from __future__ import annotations

import logging
import re
import unicodedata
from datetime import date, datetime
from types import SimpleNamespace
from typing import Any, Dict, List, Mapping, Optional, Tuple

logger = logging.getLogger(__name__)

Perfil = Dict[str, Dict[str, Any]]
NaoConferidos = Dict[str, str]


class PerfilMontado(dict):
    """O perfil ({grupo: {campo: valor}}) que `pedido.de_apolice` recebe como sempre, levando junto os
    `nao_conferidos` ({"grupo.campo": "porquê"}) para quem montou o pedido os declarar."""

    def __init__(self, perfil: Mapping[str, Mapping[str, Any]], nao_conferidos: Mapping[str, str]):
        super().__init__({g: dict(v) for g, v in perfil.items()})
        self.nao_conferidos: NaoConferidos = dict(nao_conferidos)


# ---------------------------------------------------------------------------------------------------------------------
# AS REGRAS DECLARADAS — cada constante diz por que está certa (CLAUDE.md §9.5)
# ---------------------------------------------------------------------------------------------------------------------
#: O CONDUTOR PRINCIPAL é o SEGURADO. 🔴 Por quê: 📊 a InfoCap não guarda condutor (0/10 em `/cliente`, `/documento`,
#: `/itens` e nas observações do item); o contrato do pedido já assume isso quando o condutor vem vazio
#: (`pedido._de_apolice_auto`: relação "próprio", `assumidos`) — o mesmo do canal (`conversa.montar_perfil`).
POR_QUE_CONDUTOR = "condutor principal = o segurado (a InfoCap não guarda condutor)"

#: O TEMPO DE HABILITAÇÃO = idade − 18, limitado a 10 anos.
#: 🔴 Por que 18: a CNH exige 18 anos (CTB art. 140, I) — o tempo NUNCA passa de idade − 18; a regra não inventa
#:    experiência que a pessoa não pode ter.
#: 🔴 Por que o teto 10: não declarar mais experiência do que precisa (o lado conservador) — 📊 o único valor que a tela
#:    do Agger gravou é 11 (25/25 corpos, `tests/fixtures/agger`), e a lista de opções não foi medida (P-129B-05): 10
#:    cabe em qualquer lista que vá até 11. 💭 acima de 10 anos a faixa de preço não muda nas seguradoras.
#: Menor de 26 anos: o tempo real pode ser MENOR que o máximo — o motivo diz isso ao corretor.
IDADE_DA_HABILITACAO = 18
TETO_DO_TEMPO_DE_HABILITACAO = 10
IDADE_EM_QUE_O_TEMPO_PODE_SER_MENOR = 26
POR_QUE_TEMPO = "tempo de habilitação = idade − 18, limitado a 10 anos (a InfoCap não guarda a 1ª habilitação)"
POR_QUE_TEMPO_JOVEM = POR_QUE_TEMPO + " — segurado com menos de 26 anos: o tempo real pode ser menor"

#: O ESTADO CIVIL: o RÓTULO da InfoCap → o código do Agger, só para os códigos OBSERVADOS no Agger.
#: 🔴 Por quê: 📊 1 · 2 · 4 são os ÚNICOS códigos em corpos do `calcularV2` (47 corpos, `tests/fixtures/agger`); 📊 a
#:    InfoCap usa os mesmos números para esses rótulos (12/10, 8/10 clientes: SOLTEIRO(A)=1 · CASADO(A)=2 ·
#:    DIVORCIADO(A)=4 em `cod_estado_civil`); e o formulário de vida do Agger lista Solteiro, Casado, Separado,
#:    Divorciado, Viúvo nessa ordem (`tests/fixtures/agger_formularios`, posições 1·2·4). Duas fontes independentes
#:    casam — mas o rótulo de cada código NUNCA foi lido no Agger (P-129B-05): todo estado civil sai NÃO CONFERIDO.
#: ⚠️ Pelo RÓTULO, nunca pelo `cod_estado_civil`: a tabela de códigos é do cadastro de CADA corretora na InfoCap.
ESTADO_CIVIL_NO_AGGER: Dict[str, int] = {"solteiro": 1, "casado": 2, "divorciado": 4}
POR_QUE_ESTADO_CIVIL = "estado civil do cadastro da InfoCap; o código do Agger não foi lido (P-129B-05)"
POR_QUE_ESTADO_CIVIL_PADRAO = ("estado civil ausente ou sem código observado no Agger — o padrão do produto "
                               "(o mais frequente nas gravações, o mesmo do canal)")

#: O SEXO vazio no cadastro → o primeiro nome pela tabela do IBGE (a MESMA régua do canal, D-133A1-02); ambíguo → fica
#: faltando. 📊 12/10: sexo vazio em 2/10 cadastros.
POR_QUE_SEXO_PELO_NOME = "sexo vazio no cadastro: deduzido do primeiro nome pela tabela do IBGE (a régua do canal)"

#: O PERNOITE é o endereço RESIDENCIAL do cadastro. 🔴 Por quê: 📊 a InfoCap não guarda o CEP de pernoite (0/10 no item);
#: o endereço do cadastro é residencial em 10/10 (`tipo` "R"); `pedido._de_apolice_auto` já o assume (`assumidos`).
POR_QUE_PERNOITE = "CEP de pernoite = o do endereço residencial do cadastro"

#: O SINISTRO da apólice anterior. 📊 `/documento.sinistro` "F" em 21/21 (as duas bases) = 0. "T" → 1: a quantidade
#: não é lida, e 1 é o MENOR número verdadeiro (nunca "sem sinistro" por omissão — o robô mandaria 0).
POR_QUE_SINISTRO = "a apólice anterior tem sinistro; a quantidade não é lida na InfoCap — 1 (o mínimo verdadeiro)"

#: O que a PLACA supre (D-133A-03 estendida à renovação — `pedido.CAMPOS_QUE_A_PLACA_SUPRE_NA_RENOVACAO`): a FIPE, o
#: ano e — F6, com os 7 códigos da tela medidos — o combustível que a InfoCap não traz (o robô o lê da FIPE do modelo).
POR_QUE_PELA_PLACA = "o Agger preenche pela placa (buscaPlaca); a InfoCap não traz o valor no formato do Agger"

#: O perfil que a porta deixa com o PADRÃO DA TELA na origem auxiliar (D-128-07, `pedido.CAMPOS_DE_PERFIL`).
POR_QUE_PADRAO_DA_TELA = "padrão da tela do Agger — a InfoCap não traz (D-128-07)"

#: A FIPE do item só vale com 7 dígitos (o formato que o Agger grava, 📊 "0013277"). 📊 9/10 itens a trazem com 5–6
#: dígitos — completar com zeros é escolher o carro por dedução: fica com a placa.
DIGITOS_DA_FIPE = 7

#: O COMBUSTÍVEL: o RÓTULO da InfoCap → o rótulo da lista da TELA do Agger, que `contrato.CODIGOS_MEDIDOS` traduz em
#: código (📊 F6 13/10: a lista do campo Combustível lida no bundle do app — GASOLINA 1 · ALCOOL 2 · DIESEL 3 ·
#: ELÉTRICO 5 · FLEX 6 · TETRAFUEL 10 · HÍBRIDO 11; controle: FLEX = 6 em 18/18 corpos gravados).
#: 📊 F5: 40 AUTO de uma janela de 10 dias — Flex 13 · vazio 8 · Gasolina 7 · None 4 · Diesel 3 · "Nao Informado" 2 ·
#: Eletrico 2 · Hibrido 1. 🔴 Por que cada linha está certa (CLAUDE.md §9.5):
COMBUSTIVEL_NO_AGGER: Dict[str, str] = {
    # o carro que aceita álcool E gasolina É o flex — a InfoCap escreve os dois combustíveis; a tela chama de FLEX
    "alcool/gasolina": "flex", "gasolina/alcool": "flex", "alcool gasolina": "flex", "bicombustivel": "flex",
    "flex": "flex",
    # o MESMO nome na InfoCap e na tela (sem acento): nenhuma interpretação
    "gasolina": "gasolina", "diesel": "diesel", "eletrico": "eletrico", "hibrido": "hibrido", "tetrafuel": "tetrafuel",
    # a tela chama de ALCOOL; "etanol" é o nome de bomba do MESMO combustível (álcool etílico hidratado)
    "alcool": "alcool", "etanol": "alcool",
}
#: ⛔ vazio · None · "Nao Informado" · qualquer rótulo fora da tabela → o perfil NÃO põe combustível: a PLACA supre
#: (o robô lê o combustível da FIPE do modelo, como a tela faz — `montador.js` `COMBUSTIVEL`); sem placa, fica faltando.
COMBUSTIVEL_FLEX = frozenset(k for k, v in COMBUSTIVEL_NO_AGGER.items() if v == "flex")   # compat. (F5)


def combustivel_no_agger(rotulo: Any) -> Optional[str]:
    """O rótulo da InfoCap → o rótulo da tela do Agger (`COMBUSTIVEL_NO_AGGER`), ou None (a placa supre)."""
    return COMBUSTIVEL_NO_AGGER.get(_sem_acento(rotulo)) if rotulo is not None else None

_PLACA = re.compile(r"[A-Z]{3}\d[A-Z0-9]\d{2}")


# ---------------------------------------------------------------------------------------------------------------------
def _sem_acento(texto: Any) -> str:
    t = unicodedata.normalize("NFKD", str(texto or ""))
    return re.sub(r"\s+", " ", "".join(c for c in t if not unicodedata.combining(c)).lower()).strip()


def _digitos(valor: Any) -> str:
    return re.sub(r"\D", "", str(valor or ""))


def _data(valor: Any) -> Optional[date]:
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = str(valor or "").strip()[:10]
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(texto, fmt).date()
        except ValueError:
            continue
    return None


def _idade(nasc: date, hoje: date) -> int:
    return hoje.year - nasc.year - ((hoje.month, hoje.day) < (nasc.month, nasc.day))


def _ano(valor: Any, hoje: date) -> Optional[int]:
    d = _digitos(valor)
    if len(d) != 4:
        return None
    ano = int(d)
    return ano if 1950 <= ano <= hoje.year + 1 else None


def _placa(valor: Any) -> Optional[str]:
    p = re.sub(r"[^A-Za-z0-9]", "", str(valor or "")).upper()
    return p if _PLACA.fullmatch(p) else None


def _sim(valor: Any) -> bool:
    return str(valor or "").strip().upper() in ("T", "S", "SIM", "TRUE", "1")


def data_dos_itens(inicio: Optional[date], fim: Optional[date], hoje: date) -> date:
    """A `data=` de `/itens`: HOJE presa na vigência (a regra de `infocap_connector._itens_reference_date`, D-130B-10):
    a renovação que ainda não começou → o início; a vencida → o fim."""
    ref = hoje
    if inicio is not None and ref < inicio:
        ref = inicio
    if fim is not None and ref > fim:
        ref = fim
    return ref


def _ramo(apolice: Any, item: Mapping[str, Any]) -> int:
    from app.services.multicalculo import pedido as P

    alvo = apolice if apolice is not None else SimpleNamespace(ramo=item.get("ramo_sigla"))
    return P._ramo_do_agger(alvo)


def _placa_da_apolice(apolice: Any, ficha: Any) -> Optional[str]:
    from app.services.multicalculo import pedido as P

    cad = P._valor_de(getattr(getattr(apolice, "item_de_risco", None), "placa", None)) if apolice is not None else None
    return _placa(cad) or _placa(P._objeto_do_risco(apolice, ficha).get("placa"))


def _o_cliente_e_o_da_apolice(cliente_doc: str, item: Mapping[str, Any]) -> bool:
    """O cadastro lido é o do segurado DESTA renovação? Pelo HMAC que a lista gravou (`renovacoes.documento_hmac`);
    sem ele, pelos 2 últimos dígitos do mascarado; sem os dois, não há como divergir."""
    esperado = item.get("documento_hmac")
    if esperado:
        try:
            from app.services.multicalculo.renovacao import hmac_do_documento

            return hmac_do_documento(cliente_doc) == esperado
        except Exception:  # noqa: BLE001 — sem a chave não se confere: o mascarado decide
            pass
    mascarado = _digitos(item.get("documento_mascarado"))
    return not mascarado or cliente_doc.endswith(mascarado)


def _cep_residencial(cliente: Mapping[str, Any]) -> Optional[str]:
    enderecos = [e for e in (cliente.get("enderecos") or []) if isinstance(e, Mapping)]
    ordem = sorted(enderecos, key=lambda e: (not _sim(e.get("padrao")), str(e.get("tipo") or "").upper() != "R"))
    for e in ordem:
        cep = _digitos(e.get("cep"))
        if len(cep) == 8 and cep != "00000000":
            return cep
    return None


def _item_do_veiculo(itens: List[Mapping[str, Any]], placa: Optional[str]) -> Optional[Mapping[str, Any]]:
    vivos = [i for i in itens if not _sim(i.get("cancelado"))]
    if placa:
        mesmos = [i for i in vivos if _placa(i.get("placa")) == placa]
        if len(mesmos) == 1:
            return mesmos[0]
    return vivos[0] if len(vivos) == 1 else None


# ---------------------------------------------------------------------------------------------------------------------
def montar(company_id: str, item: Mapping[str, Any], apolice: Any, ficha: Any, fonte: Any, *,
           config: Optional[Mapping[str, Any]] = None, hoje: Optional[date] = None) -> Tuple[Perfil, NaoConferidos]:
    """(perfil, nao_conferidos) de UM item da renovação. Síncrono (a fonte é urllib): a madrugada chama em thread.
    Levanta o que a fonte levantar (`FalhaDaInfocap`) — quem chama decide (a borda devolve None: o item fica com o que
    falta, nunca com dado inventado)."""
    from app.services.multicalculo import pedido as P
    from app.utils.documento_br import documento_valido

    hoje = hoje or date.today()
    ramo = _ramo(apolice, item)
    if ramo == P.RAMO_VIDA:
        return _montar_vida(item, apolice, fonte, hoje=hoje)
    catalogo = {g: set(P._nomes(c)) for g, c in P.catalogo_do_ramo(ramo).items()}
    auto = ramo == P.RAMO_AUTO
    perfil: Perfil = {}
    nao: NaoConferidos = {}

    def por(grupo: str, campo: str, valor: Any, porque: Optional[str] = None) -> None:
        if campo not in catalogo.get(grupo, ()) or valor is None or (isinstance(valor, str) and not valor.strip()):
            return
        perfil.setdefault(grupo, {})[campo] = valor
        if porque:
            nao[f"{grupo}.{campo}"] = porque

    codfil = item.get("codfil") or 1
    nosnum = item.get("nosnum")
    doc = fonte.documento_cru(codfil, nosnum) or {}

    # ── o SEGURADO: o cadastro do cliente da apólice (`/documento.codcli` → `/cliente`)
    cliente: Mapping[str, Any] = {}
    codcli = str(doc.get("codcli") or "").strip()
    if codcli:
        cliente = fonte.cliente_cru(doc.get("codfil") or codfil, codcli) or {}
    documento = _digitos(cliente.get("cpf_cnpj"))
    if cliente and documento and not _o_cliente_e_o_da_apolice(documento, item):
        logger.warning("[RENOV] o cadastro do cliente diverge do documento da renovação — não usado")
        nao["segurado.cpf_cnpj"] = "o cadastro do cliente na InfoCap não é o do segurado da apólice — não usado"
        cliente, documento = {}, ""
    pj = len(documento) == 14 or str(cliente.get("pessoa") or "").upper() == "J"
    if documento and documento_valido(documento):
        por("segurado", "cpf_cnpj", documento)
        por("segurado", "tipo_pessoa", "J" if pj else "F")
    elif documento:
        nao["segurado.cpf_cnpj"] = "o CPF/CNPJ do cadastro não fecha o dígito verificador — não usado"
    por("segurado", "nome", str(cliente.get("nome") or "").strip() or None)
    nasc = _data(cliente.get("datanas")) if not pj else None
    if nasc is not None and not (0 <= _idade(nasc, hoje) <= 110):
        nasc = None
    por("segurado", "nascimento", nasc.isoformat() if nasc else None)
    if not pj:
        sexo = str(cliente.get("sexo") or "").strip().upper()
        if sexo in ("M", "F"):
            por("segurado", "sexo", sexo)
        elif cliente.get("nome") and "sexo" in catalogo.get("segurado", ()):
            from app.services.canal.conversa import limiar_do_sexo_pelo_nome, sexo_pelo_nome

            por("segurado", "sexo", sexo_pelo_nome(cliente.get("nome"), min_pct=limiar_do_sexo_pelo_nome(config)),
                POR_QUE_SEXO_PELO_NOME)
        if cliente and "estado_civil" in catalogo.get("segurado", ()):
            from app.services.canal.conversa import ESTADO_CIVIL_PADRAO

            rotulo = re.sub(r"\(a\)|\(o\)", "", _sem_acento(cliente.get("estado_civil"))).strip()
            codigo = ESTADO_CIVIL_NO_AGGER.get(rotulo.split(" ")[0] if rotulo else "")
            if codigo is not None:
                por("segurado", "estado_civil", codigo, POR_QUE_ESTADO_CIVIL)
            elif auto:
                # o AUTO EXIGE o estado civil (o residencial não): sem rótulo com código, o padrão — marcado
                por("segurado", "estado_civil", ESTADO_CIVIL_PADRAO, POR_QUE_ESTADO_CIVIL_PADRAO)
    cep = _cep_residencial(cliente)
    por("segurado", "cep", cep)

    # ── o ITEM na data (o veículo / o endereço do risco)
    vig = getattr(apolice, "vigencia", None)
    inicio = getattr(vig, "inicio", None) or _data(doc.get("inivig"))
    fim = getattr(vig, "fim", None) or _data(doc.get("fimvig"))
    itens = list(fonte.itens_crus(codfil, nosnum, data_dos_itens(inicio, fim, hoje)) or [])
    placa_apolice = _placa_da_apolice(apolice, ficha) if auto else None
    alvo = _item_do_veiculo(itens, placa_apolice)

    if auto:
        # 🔴 conserto C2 (juiz B2): MOTO dentro da sigla AUTO → a marca no perfil; `pedido.de_apolice` a lê e levanta
        # `RamoIndisponivel(ramo_nao_cotado)` ANTES de qualquer pedido (a borda da madrugada engole exceção daqui e a
        # transformaria em `falta_dado`; a marca atravessa como dado). O item do veículo; sem ele, os itens vivos.
        vivos = [i for i in itens if not _sim(i.get("cancelado"))]
        candidatos = [alvo] if alvo is not None else vivos
        tipo = P.veiculo_nao_cotado(*(i.get(k) for i in candidatos for k in ("categoria", "veiculo")))
        if tipo is not None:
            perfil[P.MARCA_DO_VEICULO_NAO_COTADO] = {"tipo": tipo}
            return perfil, nao
        # o CONDUTOR (= o segurado; `de_apolice` copia os campos dele) e o tempo de habilitação pela idade
        if not pj and nasc is not None:
            idade = _idade(nasc, hoje)
            if idade >= IDADE_DA_HABILITACAO:
                tempo = min(idade - IDADE_DA_HABILITACAO, TETO_DO_TEMPO_DE_HABILITACAO)
                por("condutor", "tempo_habilitacao", tempo,
                    POR_QUE_TEMPO_JOVEM if idade < IDADE_EM_QUE_O_TEMPO_PODE_SER_MENOR else POR_QUE_TEMPO)
        if not pj and documento:
            for campo in ("cpf", "nome", "nascimento", "sexo", "estado_civil", "relacao_com_segurado"):
                nao[f"condutor.{campo}"] = POR_QUE_CONDUTOR
        if cep:
            nao["pernoite.cep_pernoite"] = POR_QUE_PERNOITE
        placa = placa_apolice
        if alvo is not None:
            if placa is None:
                placa = _placa(alvo.get("placa"))
                por("veiculo", "placa", placa)
            por("veiculo", "ano_fabricacao", _ano(alvo.get("anofab"), hoje))
            por("veiculo", "ano_modelo", _ano(alvo.get("anomod"), hoje))
            por("veiculo", "combustivel", combustivel_no_agger(alvo.get("combustivel")))
            fipe = _digitos(alvo.get("fipe"))
            if placa is None and len(fipe) == DIGITOS_DA_FIPE:
                por("veiculo", "fipe", fipe)
            bonus = _digitos(alvo.get("bonusclas"))
            if bonus and 0 <= int(bonus) <= 10:
                por("renovacao", "bonus_anterior", int(bonus))
        if placa is not None:
            for grupo_campo in P.CAMPOS_QUE_A_PLACA_SUPRE_NA_RENOVACAO:
                campo = grupo_campo[1]
                if campo not in perfil.get("veiculo", {}):
                    nao[f"veiculo.{campo}"] = POR_QUE_PELA_PLACA
        for grupo, campo in P.CAMPOS_DE_PERFIL:
            nao.setdefault(f"{grupo}.{campo}", POR_QUE_PADRAO_DA_TELA)
    elif alvo is not None:
        # RE: o endereço do RISCO é o do item (📊 8/9 itens de RE com CEP, logradouro, bairro, cidade e UF)
        cep_risco = _digitos(alvo.get("cep"))
        por("risco", "cep", cep_risco if len(cep_risco) == 8 else None)
        por("risco", "logradouro", str(alvo.get("endereco") or "").strip() or None)
        por("risco", "numero", str(alvo.get("numero") or "").strip() or None)
        por("risco", "complemento", str(alvo.get("complemento") or "").strip() or None)
        por("risco", "bairro", str(alvo.get("bairro") or "").strip() or None)
        por("risco", "cidade", str(alvo.get("cidade") or "").strip() or None)
        uf = str(alvo.get("estado") or "").strip().upper()
        por("risco", "uf", uf if re.fullmatch(r"[A-Z]{2}", uf) else None)

    # ── a RENOVAÇÃO: o sinistro da apólice anterior (`/documento.sinistro`)
    sinistro = str(doc.get("sinistro") or "").strip().upper()
    if sinistro == "F":
        por("renovacao", "sinistros_anterior", 0)
    elif sinistro in ("T", "S"):
        por("renovacao", "sinistros_anterior", 1, POR_QUE_SINISTRO)

    return {g: v for g, v in perfil.items() if v}, nao


# ---------------------------------------------------------------------------------------------------------------------
# SPEC-129-D — o perfil da VIDA INDIVIDUAL (ramo 91): SÓ o que a InfoCap TEM. ⛔ Nenhuma regra declarada aqui.
# ---------------------------------------------------------------------------------------------------------------------
#: 🔴 Por que a vida NÃO herda as regras do auto (CLAUDE.md §9.5 · D-129D-05):
#:   · o SEXO vazio não é deduzido do nome (a régua do canal serve ao auto): na vida o sexo muda a tábua de mortalidade —
#:     um palpite errado é declaração inexata (Código Civil, art. 766). Vazio → falta.
#:   · o ESTADO CIVIL sem rótulo do formulário de vida não vira padrão (o auto usa o "mais frequente"). → falta.
#:   · fumante, renda e esporte radical: 📊 BLOCO 0 M2, NENHUMA rota da InfoCap os tem (0/22 VIND) → nunca aparecem aqui;
#:     o pedido os aponta em `faltando()` e a madrugada pergunta ao comercial.
#:   · a PROFISSÃO: o texto do cadastro (`/cliente.profissao`, 📊 7/22) — o casamento com a BUSCA do Agger é do robô
#:     (V1, casamento inequívoco ou falta, D-129D-06); o código da InfoCap só acompanha (não é o código do Agger).
#: 📊 o nascimento está no cadastro em 15/22 e no item de vida (`/itens.datnas`) em 7/8 — o item só completa quando o CPF
#: do item É o do cadastro (o mesmo segurado).


def _montar_vida(item: Mapping[str, Any], apolice: Any, fonte: Any, *, hoje: date) -> Tuple[Perfil, NaoConferidos]:
    from app.services.multicalculo import pedido as P
    from app.utils.documento_br import cpf_valido

    seg: Dict[str, Any] = {}
    nao: NaoConferidos = {}
    codfil = item.get("codfil") or 1
    nosnum = item.get("nosnum")
    doc = fonte.documento_cru(codfil, nosnum) or {}
    cliente: Mapping[str, Any] = {}
    codcli = str(doc.get("codcli") or "").strip()
    if codcli:
        cliente = fonte.cliente_cru(doc.get("codfil") or codfil, codcli) or {}
    documento = _digitos(cliente.get("cpf_cnpj"))
    if cliente and documento and not _o_cliente_e_o_da_apolice(documento, item):
        logger.warning("[RENOV] o cadastro do cliente diverge do documento da renovação — não usado")
        nao["segurado.cpf"] = "o cadastro do cliente na InfoCap não é o do segurado da apólice — não usado"
        cliente, documento = {}, ""
    if documento and len(documento) == 11 and cpf_valido(documento):
        seg["cpf"] = documento
    elif documento:
        nao["segurado.cpf"] = "o documento do cadastro não é um CPF válido — vida individual é de uma pessoa"
    nome = str(cliente.get("nome") or "").strip()
    if nome:
        seg["nome"] = nome
    vig = getattr(apolice, "vigencia", None)
    inicio = getattr(vig, "inicio", None) or _data(doc.get("inivig"))
    fim = getattr(vig, "fim", None) or _data(doc.get("fimvig"))
    itens = list(fonte.itens_crus(codfil, nosnum, data_dos_itens(inicio, fim, hoje)) or [])
    do_segurado = [i for i in itens if not _sim(i.get("cancelado")) and documento
                   and _digitos(i.get("cpf")) == documento]
    nasc = _data(cliente.get("datanas")) or next((_data(i.get("datnas")) for i in do_segurado if _data(i.get("datnas"))),
                                                 None)
    if nasc is not None and 0 <= _idade(nasc, hoje) <= 110:
        seg["data_nascimento"] = nasc.isoformat()
    sexo = P._rotulo_da_vida(P.SEXO_DA_VIDA, str(cliente.get("sexo") or "").strip())
    if sexo in set(P.SEXO_DA_VIDA.values()):
        seg["sexo"] = sexo
    civil = P._rotulo_da_vida(P.ESTADO_CIVIL_DA_VIDA, str(cliente.get("estado_civil") or "").strip())
    if civil in set(P.ESTADO_CIVIL_DA_VIDA.values()):
        seg["estado_civil"] = civil
    cep = _cep_residencial(cliente)
    if cep:
        seg["cep"] = cep
    profissao = str(cliente.get("profissao") or "").strip()
    if profissao and not profissao.isdigit():
        seg["profissao_texto"] = profissao
    codigo = _digitos(cliente.get("cod_profissao")) or next(
        (_digitos(i.get("cod_profissao")) for i in do_segurado if _digitos(i.get("cod_profissao"))), "")
    if codigo:
        seg["profissao_codigo_infocap"] = codigo
    return ({"segurado": seg} if seg else {}), nao


def nomes_do_catalogo(ramo: int, nomes: Any) -> List[str]:
    """Os "grupo.campo" de `nomes` que existem no catálogo do ramo (o que pode virar `assumido` no pedido)."""
    from app.services.multicalculo import pedido as P

    catalogo = {g: set(P._nomes(c)) for g, c in P.catalogo_do_ramo(ramo).items()}
    saida = []
    for n in nomes or ():
        g, _, c = str(n).partition(".")
        if c in catalogo.get(g, ()):
            saida.append(f"{g}.{c}")
    return sorted(set(saida))
