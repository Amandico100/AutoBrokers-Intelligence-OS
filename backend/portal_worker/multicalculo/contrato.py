# -*- coding: utf-8 -*-
"""Os tipos do cálculo multisseguradora — SPEC-128 U2 (D-MC-37).

🔴 O cálculo NÃO usa o nome em inglês no código (D-MC-37): é CÁLCULO, RODADA, OFERTA.

Todo tipo carrega `ramo`. 📊 31 = auto no Agger (`cotacao.ramo` do `calcularV2`
nas duas gravações de 18/09). A SPEC-129-C acrescenta Condomínio (16), Residencial (2)
e Empresarial (18): o CONTRATO F1↔F2 do pedido de RE está em `CAMPOS_DO_PEDIDO_RE` /
`problemas_do_pedido_re` / `PedidoDeCalculoRE` (abaixo).

O que este módulo NUNCA carrega numa `Oferta`: login, senha, loginWs, senhaWs,
URL ou caminho de PDF. As CHAVES são conferidas por `CHAVES_PROIBIDAS_NA_OFERTA`; URL e
chave de API DENTRO de texto (mensagem, alerta, rótulo) o leitor troca por
`<removido:url>`/`<redacted:...>` (`redaction.sem_url_nem_chave`, conserto B1). A comissão vem em campo separado, `comissao_percentual`,
marcado INTERNO — nunca vai para o cliente (o adaptador da 129-B corta).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Tuple

RAMO_AUTO = 31
# SPEC-129-C — os ramos de RE. 📊 `cotacao.ramo` das 9 gravações reais saneadas (tests/fixtures/agger_ramos/
# gravacao_{condominio,residencial,empresarial}_{1,2,3}.json, 11/10): 16 · 2 · 18; e a rota de cada formulário
# (formulario_*.json `ramo`/`rota`: /cotacao/condominio · /residencial · /empresarial).
RAMO_CONDOMINIO = 16
RAMO_RESIDENCIAL = 2
RAMO_EMPRESARIAL = 18
RAMOS_RE: Tuple[int, ...] = (RAMO_CONDOMINIO, RAMO_RESIDENCIAL, RAMO_EMPRESARIAL)
RAMOS: Tuple[int, ...] = (RAMO_AUTO,) + RAMOS_RE
NOME_DO_RAMO = {RAMO_AUTO: "auto", RAMO_CONDOMINIO: "condominio", RAMO_RESIDENCIAL: "residencial",
                RAMO_EMPRESARIAL: "empresarial"}

# --------------------------------------------------------------------------
# As famílias de resposta de uma seguradora (E10)
# --------------------------------------------------------------------------
OFERTA = "OFERTA"                # ao menos um item de `resultados[]` com prêmio > 0
CREDENCIAL = "CREDENCIAL"        # login/senha da corretora na seguradora
PERMISSAO = "PERMISSAO"          # o usuário existe mas não tem permissão
ACEITACAO = "ACEITACAO"          # a seguradora não aceita ESTE risco
COMERCIAL = "COMERCIAL"          # acordo comercial: a oferta não é dada ao parceiro
INSTABILIDADE = "INSTABILIDADE"  # a seguradora caiu; tentar de novo pode resolver
DADO = "DADO"                    # o PEDIDO precisa de correção: dado inválido, cobertura obrigatória que
                                 # faltou, ou "calcule como renovação" (📊 vivo 04/10 + gravacao_r2) — o
                                 # corretor/motor conserta e recalcula; não é recusa do risco
PENDENTE = "PENDENTE"            # ainda não respondeu nesta rodada
DESCONHECIDA = "DESCONHECIDA"    # respondeu, sem oferta, e nenhuma regra reconheceu
SEM_ATIVIDADE = "SEM_ATIVIDADE_COMPATIVEL"  # SPEC-129-C: saiu do empresarial sem atividade inequívoca (ver abaixo)

FAMILIAS: Tuple[str, ...] = (
    OFERTA, CREDENCIAL, PERMISSAO, ACEITACAO, COMERCIAL,
    INSTABILIDADE, DADO, PENDENTE, DESCONHECIDA, SEM_ATIVIDADE,
)

# --------------------------------------------------------------------------
# Ajuste — o que o corretor muda e o motor recalcula
# --------------------------------------------------------------------------
TIPOS_DE_AJUSTE: Tuple[str, ...] = (
    "comissao", "desconto", "assistencia", "carro_reserva", "vidros",
    "franquia", "percentual_fipe", "cobertura",
)
# SPEC-129-C: no RE só estes fazem sentido — carro reserva/franquia/FIPE são do automóvel e `vidros` no RE é um
# VALOR segurado (📊 `configuracoes.vidros` 20000 em gravacao_condominio_1), não o código do auto: muda-se por
# `cobertura` ({"vidros": valor}). `assistencia` no RE usa os códigos do RE (presets.ASSISTENCIA_RE).
TIPOS_DE_AJUSTE_RE: Tuple[str, ...] = ("comissao", "desconto", "assistencia", "cobertura")

# Chaves que uma Oferta NUNCA tem — o teste do contrato confere por máquina.
CHAVES_PROIBIDAS_NA_OFERTA: Tuple[str, ...] = (
    "login", "senha", "loginws", "senhaws", "pathpdf", "url", "pdf_url",
    "pdffilenameagger", "authorization", "token",
)


@dataclass(frozen=True)
class Ajuste:
    tipo: str
    valor: Any
    seguradora: Optional[int] = None  # None = vale para todas
    ramo: int = RAMO_AUTO

    def __post_init__(self) -> None:
        if self.tipo not in TIPOS_DE_AJUSTE:
            raise ValueError(f"tipo de ajuste desconhecido: {self.tipo!r}")
        if self.ramo in RAMOS_RE and self.tipo not in TIPOS_DE_AJUSTE_RE:
            raise ValueError(f"ajuste {self.tipo!r} não existe no ramo {self.ramo}")


# --------------------------------------------------------------------------
# O pedido — os campos do `calcularV2` agrupados
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Campo:
    """Um campo do formulário. `obrigatorio=None` = a SPEC-128 ainda não mediu
    (F3 preenche com a E3: só os VALORES de `obrigatorio` mudam)."""
    nome: str
    caminho: str            # caminho no corpo do `calcularV2`
    obrigatorio: Optional[bool] = None
    valor: Any = None


# grupo → ((nome, caminho no calcularV2, obrigatorio), ...)
# 📊 caminhos lidos do `calcularV2` das gravações R1/R2 de 18/09 (fixtures
# `gravacao_r1.json`/`gravacao_r2.json`, chave `pedido.corpo`).
# `obrigatorio` MEDIDO na SPEC-128 E3 (📊 04/10 18:59, conta_a: "Calcular" com o formulário vazio → a tela recusou
# 15 campos, `e3_validacao.json` no rascunho do gerente; o 16º, tempo de habilitação, a tela só exige DEPOIS, no
# fluxo do condutor — observado, não contado no formulário vazio) · False = a tela aceitou vazio · None = não medido.
# Os 16 obrigatórios não dizem tudo: o questionário (garagem, uso, km) vem com PADRÕES da tela e o cálculo sai com eles.
CAMPOS_DO_PEDIDO_AUTO: dict = {
    "segurado": (
        ("tipo_pessoa", "cotacao.segurado.tipoPessoa", None),
        ("cpf_cnpj", "cotacao.segurado.cpfCnpj", True),
        ("nome", "cotacao.segurado.nome", True),
        ("nascimento", "cotacao.segurado.dataNasc", True),
        ("sexo", "cotacao.segurado.sexo", True),
        ("estado_civil", "cotacao.segurado.estadoCivil", True),
        ("cep", "cotacao.segurado.cep", True),
        ("telefone", "cotacao.segurado.fone1", False),
        ("email", "cotacao.segurado.email", False),
        ("pcd", "cotacao.segurado.isPCD", None),
    ),
    "veiculo": (
        ("fipe", "cotacao.automoveis[].fipe", True),
        ("modelo", "cotacao.automoveis[].descricao", None),
        ("fabricante", "cotacao.automoveis[].fabricante", None),
        ("ano_fabricacao", "cotacao.automoveis[].anoFabricacao", True),
        ("ano_modelo", "cotacao.automoveis[].anoModelo", None),
        ("combustivel", "cotacao.automoveis[].combustivel", True),
        ("placa", "cotacao.automoveis[].placa", False),
        ("chassi", "cotacao.automoveis[].chassi", False),
        ("zero_km", "cotacao.automoveis[].zeroKm", None),
        ("blindado", "cotacao.automoveis[].blindado", None),
        ("kit_gas", "cotacao.automoveis[].kitGas", None),
        ("alienado", "cotacao.automoveis[].alienado", None),
        ("uso", "cotacao.automoveis[].tpUso", None),
        ("percentual_fipe", "cotacao.automoveis[].pctAjuste", None),
    ),
    "pernoite": (
        ("cep_pernoite", "cotacao.automoveis[].cepPernoite", True),
        ("garagem_residencia", "cotacao.automoveis[].garagemResidencia", None),
        ("garagem_trabalho", "cotacao.automoveis[].garagemTrabalho", None),
        ("garagem_estudo", "cotacao.automoveis[].garagemEstudo", None),
    ),
    "condutor": (
        ("relacao_com_segurado", "cotacao.automoveis[].condutores[].relacComSegurado", None),
        ("cpf", "cotacao.automoveis[].condutores[].cpfCnpj", True),
        ("nome", "cotacao.automoveis[].condutores[].nome", True),
        ("nascimento", "cotacao.automoveis[].condutores[].dataNasc", True),
        ("sexo", "cotacao.automoveis[].condutores[].sexo", True),
        ("estado_civil", "cotacao.automoveis[].condutores[].estadoCivil", True),
        ("tempo_habilitacao", "cotacao.automoveis[].condutores[].tempoHabilitacao", True),
        ("jovem_condutor", "cotacao.automoveis[].jovemCondutor", None),
    ),
    "renovacao": (
        ("renovacao", "cotacao.renovacao", None),
        ("bonus_anterior", "cotacao.bonusAnterior", None),
        ("sinistros_anterior", "cotacao.sinistrosAnterior", None),
        ("numero_apolice_anterior", "cotacao.numeroRenovacao", None),
        ("seguradora_anterior", "cotacao.seguradoraAnteriorId", None),
        ("fim_vigencia_anterior", "cotacao.vigFimAnterior", None),
        ("vigencia_inicio", "cotacao.vigenciaIni", None),
        ("vigencia_fim", "cotacao.vigenciaFim", None),
    ),
    "coberturas": (
        ("tipo_cobertura", "cotacao.calculos[].tipoCobertura", None),
        ("tipo_franquia", "cotacao.calculos[].tipoFranquia", None),
        ("danos_materiais", "cotacao.calculos[].isDanosMateriais", None),
        ("danos_corporais", "cotacao.calculos[].isDanosCorporais", None),
        ("danos_morais", "cotacao.calculos[].isDanosMorais", None),
        ("app_morte", "cotacao.calculos[].isAppMorte", None),
        ("assistencia", "cotacao.calculos[].assist24hs", None),
        ("carro_reserva", "cotacao.calculos[].carroReserva", None),
        ("vidros", "cotacao.calculos[].vidros", None),
        ("valor_de_novo", "cotacao.calculos[].valorDeNovo", None),
    ),
    # 📊 o `calcularV2` das gravações NÃO traz campo de pacote: `packageType`
    # só aparece na RESPOSTA. O caminho do pedido é medido na E20 (F3).
    "pacotes": (
        ("tipo_de_pacote", "a medir (E20)", None),
    ),
    "comissao_desconto": (
        ("comissao_percentual", "cotacao.calculos[].percComissao", None),
        ("desconto_percentual", "cotacao.calculos[].percDesconto", None),
    ),
}


# --------------------------------------------------------------------------
# Os CÓDIGOS dos campos de lista do Agger — SPEC-129-B F4 (a costura porta × robô)
# --------------------------------------------------------------------------
# O robô (`agger_robo.cotacao_do_pedido`) manda CÓDIGO nos campos de lista; texto sem código medido o robô recusa
# só no disparo, lá na frente. A PORTA traduz com ESTA tabela e recusa o resto como `PedidoIncompleto` (nunca um
# disparo recusado depois de o pedido entrar na fila). 🔴 Só entra aqui texto→código MEDIDO (CLAUDE.md §9.5):
#   📊 sexo "M"/"F" ............ 18/18 corpos do `calcularV2` das fixtures (gravacao_r1/r2, vivo_conta_a/b)
#   📊 combustível Flex = 6 .... 18/18 corpos (e `montador.js` COMBUSTIVEL); os outros 6, a lista da tela (F6, abaixo)
#   📊 relação "próprio" = 1 ... 17/18 condutores (o 18º, código 14, não tem rótulo medido)
# Estado civil (📊 códigos 1, 2 e 4 nas fixtures), uso, garagem, fabricante: o RÓTULO de cada código NÃO foi
# medido — só o código entra (P-129B-05: medir a lista de opções da tela e acrescentar aqui).
CODIGOS_MEDIDOS: dict = {
    ("segurado", "sexo"): {"m": "M", "masculino": "M", "f": "F", "feminino": "F"},
    ("condutor", "sexo"): {"m": "M", "masculino": "M", "f": "F", "feminino": "F"},
    ("segurado", "tipo_pessoa"): {"f": "F", "fisica": "F", "j": "J", "juridica": "J"},
    # 📊 SPEC-131-A F6 (13/10): a lista do campo Combustível da TELA do Agger, lida no bundle do app (o chunk do
    # formulário AUTO: `static combustivel=[{value,viewValue}]`, o mesmo `inArrayValidator` que exige o campo). O rótulo
    # é o `viewValue` da tela (sem acento, minúsculo); o código é o `value` que vai no `calcularV2`.
    # CONTROLE: FLEX = 6 é o código dos 18/18 corpos gravados — a lista lida e o que a tela manda são a mesma coisa.
    # Espelho em `montador.js` `COMBUSTIVEL` (o rótulo da FIPE → código): mudou aqui, muda lá (o teste do perfil confere).
    ("veiculo", "combustivel"): {"gasolina": 1, "alcool": 2, "diesel": 3, "eletrico": 5, "flex": 6, "tetrafuel": 10,
                                 "hibrido": 11},
    ("condutor", "relacao_com_segurado"): {"proprio": 1},
}
#: campos que o robô manda como NÚMERO inteiro (`agger_robo._int`): código de lista ou quantidade
CAMPOS_DE_CODIGO_INTEIRO: Tuple[Tuple[str, str], ...] = (
    ("segurado", "estado_civil"), ("condutor", "estado_civil"), ("condutor", "relacao_com_segurado"),
    ("condutor", "tempo_habilitacao"), ("veiculo", "fabricante"), ("veiculo", "ano_fabricacao"),
    ("veiculo", "ano_modelo"), ("veiculo", "combustivel"), ("veiculo", "uso"), ("veiculo", "percentual_fipe"),
    ("renovacao", "bonus_anterior"), ("renovacao", "sinistros_anterior"), ("questionario", "km_mensal"),
)
#: campos que o robô manda como TEXTO de dígitos (📊 `garagemResidencia: "2"` em 18/18 corpos)
CAMPOS_DE_CODIGO_TEXTO: Tuple[Tuple[str, str], ...] = (
    ("pernoite", "garagem_residencia"), ("pernoite", "garagem_trabalho"), ("pernoite", "garagem_estudo"),
)
#: campos sim/não (o robô faz `bool(valor)`: o texto "não" viraria VERDADEIRO — a porta converte ou recusa)
CAMPOS_SIM_NAO: Tuple[Tuple[str, str], ...] = (
    ("segurado", "pcd"), ("veiculo", "zero_km"), ("veiculo", "blindado"), ("veiculo", "kit_gas"),
    ("veiculo", "alienado"), ("condutor", "jovem_condutor"), ("renovacao", "renovacao"),
)

# A SEGURADORA ANTERIOR da renovação: o robô a acha em `calculo/seguradorasRenovacao` pelo NOME (o id é do Agger).
# A ficha da InfoCap dá o `coenti` (SUSEP, `susep_ses_provider.coenti_de`); esta tabela leva o coenti ao nome
# EXATO da lista do Agger. 📊 nomes: `gravacao_r1.json` `seguradoras_renovacao` (69 itens, 05/10); 📊 coenti:
# `mapa_de_seguradoras()` (15 chaves). Cada linha diz por que é a mesma empresa (§9.5).
# ⛔ Fora daqui (a porta recusa como `PedidoIncompleto`): SulAmérica (coenti UNKNOWN no mapa e DUAS entradas no
# Agger) · Unimed (`auto=false` no Agger).
SEGURADORA_ANTERIOR_NO_AGGER: dict = {
    "05177": "Allianz",                               # única Allianz da lista
    "05355": "Azul Companhia de Seguros Gerais",      # o MESMO nome da SUSEP (AZUL COMPANHIA DE SEGUROS GERAIS)
    "05312": "Bradesco Auto/RE Cia de Seg.",          # BRADESCO AUTO/RE COMPANHIA DE SEGUROS, abreviado
    "06572": "HDI",                                   # única HDI
    "06238": "Mapfre Vera Cruz Seguradora S/A",       # única Mapfre da lista
    "05886": "Porto Seguro Cia Seg. Gerais",          # PORTO SEGURO COMPANHIA DE SEGUROS GERAIS, abreviado
    "04952": "Suhai Seguradora",                      # única Suhai
    "06751": "Seguro Sura S.A.",                      # única Sura
    "06190": "Tokio Marine Seguradora S.A",           # TOKIO MARINE SEGURADORA S.A.
    "05185": "Yelum Seguradora",                      # YELUM SEGUROS S.A. (a ex-Liberty; única Yelum)
    "05495": "Zurich - Minas Brasil",                 # ZURICH MINAS BRASIL SEGUROS S.A.
    "06467": "Alfa Seguros e Previdência S.A.",       # única Alfa da lista
    "05720": "Sompo Seguros",                         # SOMPO SEGUROS S.A. (a outra, "Sompo Consumer", não)
}


@dataclass(frozen=True)
class PedidoDeCalculoAuto:
    ramo: int = RAMO_AUTO
    segurado: Tuple[Campo, ...] = ()
    veiculo: Tuple[Campo, ...] = ()
    pernoite: Tuple[Campo, ...] = ()
    condutor: Tuple[Campo, ...] = ()
    renovacao: Tuple[Campo, ...] = ()
    coberturas: Tuple[Campo, ...] = ()
    pacotes: Tuple[Campo, ...] = ()
    comissao_desconto: Tuple[Campo, ...] = ()
    seguradoras: Tuple[int, ...] = ()   # códigos das seguradoras pedidas


# ======================================================================================================================
# 🔴 O CONTRATO F1 ↔ F2 DA SPEC-129-C — o pedido de RE (Condomínio 16 · Residencial 2 · Empresarial 18)
# ======================================================================================================================
# O dict que o motor entrega ao robô (`agger_robo.disparar(sessao, pedido, coberturas)`) para RE:
#     {"ramo": 16|2|18,
#      "segurado":          {campo: valor},     # CAMPOS_DO_PEDIDO_RE[ramo]["segurado"]
#      "risco":             {campo: valor},     # o endereço do risco + o bem (+ "extras": {chave_de_cobertura: valor})
#      "renovacao":         {campo: valor},     # como o auto (sinistros_anterior vira TEXTO "0"/"1" no corpo)
#      "comissao_desconto": {"comissao_percentual": n, "desconto_percentual": n?},   # comissão OBRIGATÓRIA (D-129C-05)
#      "seguradoras": [códigos], "assumidos": [...], "coberturas": {}, "pacotes": {}}
# As COBERTURAS de cada opção NÃO moram no pedido: a porta as resolve com `presets.coberturas_re(ramo, opcao,
# valor_basica, extras)` e o robô as aplica em `cotacao.configuracoes` (nunca no item — 📊 0 chaves de cobertura nos
# itens das 9 gravações). `risco.valor_basica` é a Básica (incêndio) DO PEDIDO (D-129C-03: nenhum valor segurado fixo).
# Cada código abaixo vem SÓ das fixtures medidas (CLAUDE.md §9.5): `formulario_<ramo>.json` (as opções da tela, lidas
# rótulo a rótulo do JS do app em 11/10) e os corpos gravados `gravacao_<ramo>_{1,2}.json` (o TIPO de cada valor).
#
# Tipos (o que a porta entrega; `TIPO_DO_CAMPO_RE`): "texto" · "digitos" (só dígitos) · "data" (AAAA-MM-DD) ·
# "inteiro" · "codigo" (inteiro de uma lista medida) · "codigo_texto" (dígito como TEXTO — 📊 imovelPavimentacao "0")
# · "booleano" · "dinheiro" (número ≥ 0) · "lista_de_codigos" · "mapa_de_cobertura" ({chave: dinheiro}).
_ENDERECO_DO_RISCO = (
    # 📊 formulario_*.json: a seção "Endereço" vai para `configuracoes.imovel*` nos 3 ramos (obrigatórios: CEP, UF,
    # cidade, bairro, logradouro; número e complemento não)
    ("cep", "cotacao.configuracoes.imovelCep", True),
    ("logradouro", "cotacao.configuracoes.imovelLogradouro", True),
    ("numero", "cotacao.configuracoes.imovelNumero", False),
    ("complemento", "cotacao.configuracoes.imovelComplemento", False),
    ("bairro", "cotacao.configuracoes.imovelBairro", True),
    ("cidade", "cotacao.configuracoes.imovelCidade", True),
    ("uf", "cotacao.configuracoes.imovelUF", True),
    # a Básica (incêndio/raio/explosão): obrigatória nos 3 formulários; o VALOR vem do pedido (D-129C-03)
    ("valor_basica", "cotacao.configuracoes.isDanosIncendioRaioExplosao", True),
    # 📊 valorDeNovo Não 0 · Sim 1 (padrão da tela Sim; 1 nas 6 gravações recentes)
    ("valor_de_novo", "cotacao.configuracoes.valorDeNovo", False),
    ("extras", "cotacao.configuracoes.<chave de presets.CHAVES_DE_COBERTURA_RE[ramo]>", False),
)
_RENOVACAO_RE = (
    ("renovacao", "cotacao.renovacao", False),
    ("bonus_anterior", "cotacao.bonusAnterior", False),
    ("sinistros_anterior", "cotacao.sinistrosAnterior", False),     # 📊 TEXTO "0"/"1" no RE em 6/9 gravações (as 3 migradas: int 0)
    ("numero_apolice_anterior", "cotacao.numeroRenovacao", False),
    ("seguradora_anterior", "cotacao.seguradoraAnteriorId", False),
    ("fim_vigencia_anterior", "cotacao.vigFimAnterior", False),
    ("vigencia_inicio", "cotacao.vigenciaIni", False),
    ("vigencia_fim", "cotacao.vigenciaFim", False),
)
_COMISSAO_RE = (
    # 🔴 D-129C-05: a comissão vai EXPLÍCITA no item (`percComissao`). 📊 sem ela a tela usa percComissaoEmpres = 0 em
    # TODAS as 10 seguradoras da conta (formulario_empresarial.json `seguradoras.na_conta`) — mandar o padrão da conta
    # seria comissão ZERO. Por isso é obrigatória no RE (o robô recusa antes de qualquer rede).
    ("comissao_percentual", "cotacao.calculos[].percComissao", True),
    ("desconto_percentual", "cotacao.calculos[].percDesconto", False),
)
CAMPOS_DO_PEDIDO_RE: dict = {
    RAMO_CONDOMINIO: {
        "segurado": (
            # 📊 formulario_condominio: CNPJ e Razão Social obrigatórios; o app força tipoPessoa "J"
            # (valoresEstaticosDraftSegurado {tipoPessoa:"J"}; 📊 J em 15/15 negócios lidos, BLOCO0-GRAVACAO)
            ("cpf_cnpj", "cotacao.segurado.cpfCnpj", True),
            ("nome", "cotacao.segurado.nome", True),
            ("telefone", "cotacao.segurado.fone1", False),
            ("email", "cotacao.segurado.email", False),
        ),
        "risco": _ENDERECO_DO_RISCO + (
            ("tipo_imovel", "cotacao.configuracoes.imovelAtividade", True),          # Tipo de Condomínio (códigos)
            ("estrutura", "cotacao.configuracoes.estruturaCondominio", True),
            ("ano_fundacao", "cotacao.configuracoes.anoFundacao", True),             # 📊 TEXTO "2005"
            ("blocos", "cotacao.configuracoes.qtdBlocos", True),                     # 📊 TEXTO "4"
            ("pavimentos", "cotacao.configuracoes.pavimentos", True),                # 📊 TEXTO "5"
            ("elevadores", "cotacao.configuracoes.qtdElevadores", True),             # 📊 inteiro 0 (às vezes texto)
            ("area_construida", "cotacao.configuracoes.areaConstruida", False),
            ("funcionarios", "cotacao.configuracoes.qtdFuncionarios", False),
            ("protecoes", "cotacao.configuracoes.sisProtecaoIncendRoubo", False),    # 📊 [1] · [1,7] · [1,2,7]
            ("patrimonio_historico", "cotacao.configuracoes.imovelPatrimonioHistorico", False),
            ("area_comercial", "cotacao.configuracoes.condPossuiAreaComercial", False),
            ("desmoronamento_5_anos", "cotacao.configuracoes.desmoronamento", False),
        ),
        "renovacao": _RENOVACAO_RE,
        "comissao_desconto": _COMISSAO_RE,
    },
    RAMO_RESIDENCIAL: {
        "segurado": (
            ("cpf_cnpj", "cotacao.segurado.cpfCnpj", True),
            ("nome", "cotacao.segurado.nome", True),
            ("nascimento", "cotacao.segurado.dataNasc", True),     # 📊 formulario_residencial: obrigatório
            ("sexo", "cotacao.segurado.sexo", False),              # 📊 padrão do app "M" (informacoesDefault)
            ("estado_civil", "cotacao.segurado.estadoCivil", False),
            ("telefone", "cotacao.segurado.fone1", False),
            ("email", "cotacao.segurado.email", False),
        ),
        "risco": _ENDERECO_DO_RISCO + (
            ("tipo_imovel", "cotacao.configuracoes.imovelTipoResidencia", True),
            ("construcao", "cotacao.configuracoes.imovelConstrucao", True),
            ("uso", "cotacao.configuracoes.imovelUso", True),
            ("objeto", "cotacao.configuracoes.imovelObjetoSegurado", True),
            ("alarme", "cotacao.configuracoes.imovelPossuiAlarme", False),
            ("vigilancia_24h", "cotacao.configuracoes.imovelPossuiVigilancia24hs", False),
            ("grades", "cotacao.configuracoes.imovelPossuiGrades", False),
            ("cerca_eletrica", "cotacao.configuracoes.imovelPossuiCercaEletrica", False),
            ("alarme_monitorado", "cotacao.configuracoes.imovelPossuiAlarmeMonitorado", False),
            ("porteiro_eletronico", "cotacao.configuracoes.imovelPossuiPorteiroEletronico", False),
            ("cftv", "cotacao.configuracoes.imovelPossuiCircuitoFechado", False),
            ("patrimonio_historico", "cotacao.configuracoes.imovelPatrimonioHistorico", False),
            ("proprietario", "cotacao.configuracoes.seguradoProprietario", False),   # 📊 padrão da tela: marcado
            ("area_de_risco", "cotacao.configuracoes.areaRisco", False),
            ("zona_rural", "cotacao.configuracoes.zonaRural", False),
            ("atividade_no_local", "cotacao.configuracoes.imovelAtividadeProfissionalLocal", False),
        ),
        "renovacao": _RENOVACAO_RE,
        "comissao_desconto": _COMISSAO_RE,
    },
    RAMO_EMPRESARIAL: {
        "segurado": (
            ("cpf_cnpj", "cotacao.segurado.cpfCnpj", True),
            ("nome", "cotacao.segurado.nome", True),
            ("telefone", "cotacao.segurado.fone1", False),
            ("email", "cotacao.segurado.email", False),
        ),
        "risco": _ENDERECO_DO_RISCO + (
            # 🔴 a atividade é POR SEGURADORA (D-129C-04): o robô a procura em `getOptionsBySegFull` com este TEXTO e
            # põe o código de cada seguradora em `calculos[].valoresAjusteSeguradora` (📊 gravacao_empresarial_1/2)
            ("atividade", "cotacao.calculos[].valoresAjusteSeguradora.imovelAtividadeProfissionalLocal", True),
            # CNAE: SÓ ajuda a achar a classe da atividade (agger_robo.CNAE_DA_CLASSE). 📊 nenhum corpo RECENTE leva
            # `cnae` (gravacao_empresarial_1/2) e o formulário de hoje não tem o campo — não vai ao Agger.
            ("cnae", "(não vai ao corpo)", False),
            ("pavimento", "cotacao.configuracoes.imovelPavimentacao", True),
            ("localizacao", "cotacao.configuracoes.imovelLocalEstabelecimento", True),
            ("construcao", "cotacao.configuracoes.imovelConstrucao", True),
            ("ano_construcao", "cotacao.configuracoes.anoConstrucao", False),         # 📊 inteiro 2023
            ("objeto", "cotacao.configuracoes.imovelObjetoSegurado", True),
            ("alarme", "cotacao.configuracoes.imovelPossuiAlarme", False),
            ("alarme_monitorado", "cotacao.configuracoes.imovelPossuiAlarmeMonitorado", False),
            ("cftv", "cotacao.configuracoes.imovelPossuiCircuitoFechado", False),
            ("vigilancia_24h", "cotacao.configuracoes.imovelPossuiVigilancia24hs", False),
            ("grades_fechadura_tetra", "cotacao.configuracoes.imovelPossuiGradesEFechaduraTetra", False),
            ("sensor_infravermelho", "cotacao.configuracoes.imovelPossuiSensorInfravermelho", False),
            ("extintor", "cotacao.configuracoes.imovelPossuiExtintor", False),
            ("hidrante", "cotacao.configuracoes.imovelPossuiHidrante", False),
            ("sprinkler", "cotacao.configuracoes.imovelPossuiSprinkler", False),
            ("detector_fumaca", "cotacao.configuracoes.imovelPossuiDetectorFumaca", False),
            ("brigada_incendio", "cotacao.configuracoes.imovelPossuiBrigadaIncendio", False),
            ("deposito", "cotacao.configuracoes.imovelUtilizadoDeposito", False),
            ("divisa_terreno_baldio", "cotacao.configuracoes.imovelDivisaTerronoBaldio", False),
            ("patrimonio_historico", "cotacao.configuracoes.imovelPatrimonioHistorico", False),
            ("telha_metalica", "cotacao.configuracoes.imovelTelhaEstruturaMetalica", False),
            ("caixa_eletronico", "cotacao.configuracoes.imovelCaixaEletronico", False),
            ("isopainel", "cotacao.configuracoes.imovelPossuiIsopainel", False),
            ("em_obra", "cotacao.configuracoes.imovelConstrucaoReforma", False),
        ),
        "renovacao": _RENOVACAO_RE,
        "comissao_desconto": _COMISSAO_RE,
    },
}

#: (ramo, grupo, campo) → o nome do campo no corpo (a última parte do caminho). Só os que vão a `configuracoes`.
def chave_no_corpo(ramo: int, grupo: str, campo: str) -> Optional[str]:
    for nome, caminho, _obr in CAMPOS_DO_PEDIDO_RE[ramo][grupo]:
        if nome == campo:
            parte = caminho.rsplit(".", 1)[-1]
            # 🔴 costura 129-C: o "<" do caminho-modelo das extras ("…configuracoes.<chave de presets.CHAVES_…[ramo]>")
            # fica ANTES do último ponto — conferir só a `parte` devolvia "CHAVES_DE_COBERTURA_RE[ramo]>" como chave, e o
            # robô mandava o dict das extras inteiro sob ela em `configuracoes` (a F1 nunca mandou extras; a F2 sempre)
            return parte if caminho.startswith("cotacao.configuracoes.") and "<" not in caminho else None
    return None


# Os CÓDIGOS dos campos de lista do RE — texto (normalizado: minúscula, sem acento) → código. 🔴 SÓ os medidos:
# 📊 formulario_condominio/residencial/empresarial.json `campos[].opcoes` (rótulo a rótulo, JS do app de 11/10).
# ⚠️ NÃO são ordinais: construção Superior = 4 (e Sólida = 1); não "corrija" para a ordem da tela.
CODIGOS_MEDIDOS_RE: dict = {
    # condomínio · Tipo de Condomínio (imovelAtividade): Residencial 1 · Escritório 2 · Consultório 3 · Comercial 4 ·
    # Flat/Apart Hotel 5 · Shopping Center 6 · Misto 7  (📊 1 em 12/15 negócios lidos)
    (RAMO_CONDOMINIO, "tipo_imovel"): {"residencial": 1, "escritorio": 2, "consultorio": 3, "comercial": 4,
                                       "flat": 5, "flat/apart hotel": 5, "apart hotel": 5, "shopping": 6,
                                       "shopping center": 6, "misto": 7},
    (RAMO_CONDOMINIO, "estrutura"): {"vertical": 1, "horizontal": 2},
    # equipamentos → códigos de sisProtecaoIncendRoubo (📊 [1] 10 · [1,7] 4 · [1,2,7] 1 nos negócios lidos)
    (RAMO_CONDOMINIO, "protecoes"): {"extintores": 1, "hidrantes": 2, "sprinklers": 3, "alarme": 4,
                                     "cerca eletrica": 5, "porteiro eletronico": 6, "cftv": 7,
                                     "circuito fechado de cftv": 7, "detector de fumaca": 8,
                                     "brigada de incendio": 9, "catraca eletronica": 10},
    # residencial
    (RAMO_RESIDENCIAL, "tipo_imovel"): {"casa": 1, "casa em condominio": 2, "casa em condominio fechado": 2,
                                        "apartamento": 3},
    (RAMO_RESIDENCIAL, "construcao"): {"superior": 4, "solida": 1, "mista": 2, "inferior": 3},
    (RAMO_RESIDENCIAL, "uso"): {"habitual": 1, "veraneio": 2, "desocupado": 3},
    (RAMO_RESIDENCIAL, "objeto"): {"predio": 1, "conteudo": 2, "predio + conteudo": 3, "predio e conteudo": 3},
    # empresarial — pavimento e localização são TEXTO no corpo (📊 "0" nas 2 gravações recentes; Business/Data)
    (RAMO_EMPRESARIAL, "pavimento"): {"terreo": "0", "primeiro": "1", "primeiro andar": "1",
                                      "segundo em diante": "2", "segundo andar ou acima": "2"},
    (RAMO_EMPRESARIAL, "localizacao"): {"outros": "0", "aeroporto": "1", "ceasa": "2", "ceasa/mercado": "2",
                                        "mercado": "2", "condominio comercial": "3", "shopping": "4",
                                        "supermercado": "5"},
    (RAMO_EMPRESARIAL, "construcao"): {"superior": 4, "solida": 1, "mista": 2, "inferior": 3},
    (RAMO_EMPRESARIAL, "objeto"): {"predio": 1, "conteudo": 2, "predio + conteudo": 3, "predio e conteudo": 3},
}
#: os códigos válidos de cada campo de lista (o que a porta aceita já como código) — os mesmos valores acima
CODIGOS_VALIDOS_RE: dict = {k: frozenset(v.values()) for k, v in CODIGOS_MEDIDOS_RE.items()}
# 📊 qtdElevadores: as opções da tela são 0–4 (formulario_condominio); o corpo aceita mais (📊 "15" num negócio lido)
CODIGOS_VALIDOS_RE[(RAMO_CONDOMINIO, "elevadores")] = None   # inteiro ≥ 0, sem lista fechada

TIPO_DO_CAMPO_RE: dict = {
    ("segurado", "cpf_cnpj"): "digitos", ("segurado", "nome"): "texto", ("segurado", "nascimento"): "data",
    ("segurado", "sexo"): "texto", ("segurado", "estado_civil"): "inteiro", ("segurado", "telefone"): "digitos",
    ("segurado", "email"): "texto",
    ("risco", "cep"): "digitos", ("risco", "logradouro"): "texto", ("risco", "numero"): "texto",
    ("risco", "complemento"): "texto", ("risco", "bairro"): "texto", ("risco", "cidade"): "texto",
    ("risco", "uf"): "texto", ("risco", "valor_basica"): "dinheiro", ("risco", "valor_de_novo"): "booleano",
    ("risco", "extras"): "mapa_de_cobertura", ("risco", "tipo_imovel"): "codigo", ("risco", "estrutura"): "codigo",
    ("risco", "ano_fundacao"): "texto", ("risco", "blocos"): "texto", ("risco", "pavimentos"): "texto",
    ("risco", "elevadores"): "inteiro", ("risco", "area_construida"): "texto", ("risco", "funcionarios"): "texto",
    ("risco", "protecoes"): "lista_de_codigos", ("risco", "construcao"): "codigo", ("risco", "uso"): "codigo",
    ("risco", "objeto"): "codigo", ("risco", "atividade"): "texto", ("risco", "cnae"): "digitos",
    ("risco", "pavimento"): "codigo_texto", ("risco", "localizacao"): "codigo_texto",
    ("risco", "ano_construcao"): "inteiro",
    ("renovacao", "renovacao"): "booleano", ("renovacao", "bonus_anterior"): "inteiro",
    ("renovacao", "sinistros_anterior"): "inteiro", ("renovacao", "numero_apolice_anterior"): "texto",
    ("renovacao", "seguradora_anterior"): "texto", ("renovacao", "fim_vigencia_anterior"): "data",
    ("renovacao", "vigencia_inicio"): "data", ("renovacao", "vigencia_fim"): "data",
    ("comissao_desconto", "comissao_percentual"): "dinheiro", ("comissao_desconto", "desconto_percentual"): "dinheiro",
}


def tipo_do_campo_re(grupo: str, campo: str) -> str:
    """O tipo de um campo do pedido de RE; os sim/não do bem (imovelPossui*, perguntas) são 'booleano'."""
    return TIPO_DO_CAMPO_RE.get((grupo, campo), "booleano" if grupo == "risco" else "texto")


# As SEGURADORAS de cada ramo — o filtro GLOBAL do Agger (📊 `app/seguradoraStatus.<ramo>Status == 1`, lido do JS do
# app em 11/10: formulario_<ramo>.json `seguradoras.habilitadas_no_agger_global`) ∩ as ativas na conta, menos Azul (10)
# e Aliro (22) (regra do JS `getSeguradorasStatus`). Sem herdeiros (o GRUPO do auto não vale no RE: 📊 a Mitsui está
# na lista global do empresarial mas não tem config própria na conta). O robô passa ESTA lista ao montador.js.
SEGURADORAS_DO_RAMO: dict = {
    RAMO_CONDOMINIO: (1, 4, 5, 8, 11, 19, 32, 35),
    RAMO_RESIDENCIAL: (1, 3, 4, 5, 7, 8, 11, 12, 19, 24, 27, 31, 33, 43, 49),
    RAMO_EMPRESARIAL: (1, 3, 4, 5, 7, 8, 11, 12, 13, 19, 24, 32, 35, 43),
}
SEGURADORAS_FORA_DO_RE: Tuple[int, ...] = (10, 22)   # Azul · Aliro (getSeguradorasStatus)
# Os campos de `seguradorasRenovacao` que dizem se a seguradora anterior serve no ramo (📊 lista branca
# "seguradoras_renovacao" do leitor: auto · residencial · condominio · empresarial)
CAMPO_DO_RAMO_NA_RENOVACAO: dict = {RAMO_CONDOMINIO: "condominio", RAMO_RESIDENCIAL: "residencial",
                                    RAMO_EMPRESARIAL: "empresarial"}


def campos_do_pedido(ramo: int) -> dict:
    """O catálogo do pedido do ramo: {grupo: ((nome, caminho, obrigatório), ...)}."""
    if ramo == RAMO_AUTO:
        return CAMPOS_DO_PEDIDO_AUTO
    if ramo in CAMPOS_DO_PEDIDO_RE:
        return CAMPOS_DO_PEDIDO_RE[ramo]
    raise ValueError(f"ramo {ramo} não implementado (há: {', '.join(str(r) for r in RAMOS)})")


# 🔴 costura 129-C (decisão do contrato × a tela, nota 90 × 35): marcada a renovação, a TELA dos 3 ramos passa a exigir
# QUATRO campos — 📊 formulario_{condominio,residencial,empresarial}.json `campos[].libera_quando`: "renovacao = true
# (então obrigatórios: vigFimAnterior, seguradoraAnteriorId, sinistrosAnterior, bonusAnterior)". O robô preencheria
# bônus 0 / sinistros "0" / vigência anterior vazia por conta própria — declarar à seguradora "sem sinistro, bônus 0"
# sem saber é preço errado e calado (CLAUDE.md §9.5). Faltando qualquer um, o pedido volta como `PedidoIncompleto`.
# ⚠️ `sinistros_anterior = 0` e `bonus_anterior = 0` são RESPOSTAS (não vazios): `_vazio_re(0)` é falso.
# E `valor_de_novo` (obrigatório na tela de condomínio/residencial) fica OPCIONAL no pedido, nota 85 × 60: a tela abre
# com "Sim" já marcado (📊 `padrao_na_tela: "Sim"`) e o robô manda 1 quando o pedido cala (agger_robo
# `_MOLDE_CONFIGURACOES[*]["valorDeNovo"] = 1`) — o corpo nunca sai sem ele; exigir a pergunta só travaria o corretor.
CAMPOS_DA_RENOVACAO_NA_TELA: Tuple[str, ...] = ("fim_vigencia_anterior", "seguradora_anterior", "sinistros_anterior",
                                                 "bonus_anterior")


def _vazio_re(v: Any) -> bool:
    return v is None or (isinstance(v, str) and not v.strip()) or (isinstance(v, (list, dict)) and not v)


def problemas_do_pedido_re(pedido: Any) -> Tuple[str, ...]:
    """O que falta ou não tem código medido num pedido de RE (o dict do robô), como "grupo.campo" — NOMES, nunca
    valores. Vazio = o robô pode montar o corpo. A porta (F2) devolve isto como `PedidoIncompleto`."""
    if not isinstance(pedido, dict):
        return ("pedido",)
    ramo = pedido.get("ramo")
    if ramo not in CAMPOS_DO_PEDIDO_RE:
        return ("ramo",)
    saida = []
    for grupo, campos in CAMPOS_DO_PEDIDO_RE[ramo].items():
        dados = pedido.get(grupo) if isinstance(pedido.get(grupo), dict) else {}
        conhecidos = {n for n, _c, _o in campos}
        for k in dados:
            if k not in conhecidos:
                saida.append(f"{grupo}.{k}:desconhecido")
        for nome, _caminho, obrigatorio in campos:
            v = dados.get(nome)
            if _vazio_re(v):
                if obrigatorio:
                    saida.append(f"{grupo}.{nome}")
                continue
            validos = CODIGOS_VALIDOS_RE.get((ramo, nome)) if grupo == "risco" else None
            tipo = tipo_do_campo_re(grupo, nome)
            if tipo == "dinheiro" and (isinstance(v, bool) or not isinstance(v, (int, float)) or v < 0):
                saida.append(f"{grupo}.{nome}:valor")
            elif tipo == "booleano" and not isinstance(v, bool):
                saida.append(f"{grupo}.{nome}:sim_nao")
            elif tipo == "lista_de_codigos" and not (isinstance(v, list) and all(
                    isinstance(x, int) and not isinstance(x, bool) and (validos is None or x in validos) for x in v)):
                saida.append(f"{grupo}.{nome}:codigo")
            elif tipo in ("codigo", "codigo_texto") and validos is not None and v not in validos:
                saida.append(f"{grupo}.{nome}:codigo")
            elif tipo == "inteiro" and (isinstance(v, bool) or not isinstance(v, int)):
                if not (isinstance(v, str) and v.strip().isdigit()):
                    saida.append(f"{grupo}.{nome}:codigo")
            elif tipo == "mapa_de_cobertura" and not (isinstance(v, dict) and all(
                    isinstance(x, (int, float)) and not isinstance(x, bool) and x >= 0 for x in v.values())):
                saida.append(f"{grupo}.{nome}:valor")
    ren = pedido.get("renovacao") if isinstance(pedido.get("renovacao"), dict) else {}
    if ren.get("renovacao") is True:
        for nome in CAMPOS_DA_RENOVACAO_NA_TELA:
            if _vazio_re(ren.get(nome)):
                saida.append(f"renovacao.{nome}")
    return tuple(saida)


@dataclass(frozen=True)
class PedidoDeCalculoRE:
    """O pedido de RE validado contra o catálogo do ramo. `de_dict` levanta `ValueError` com os NOMES do que falta
    (nunca valores); `para_dict()` é o dict que o motor entrega ao robô."""
    ramo: int
    segurado: Any
    risco: Any
    renovacao: Any = None
    comissao_desconto: Any = None
    seguradoras: Tuple[int, ...] = ()

    def __repr__(self) -> str:   # ⛔ nunca os valores (CNPJ, nome, endereço)
        return f"PedidoDeCalculoRE(ramo={self.ramo}, risco={len(self.risco or {})} campos)"

    __str__ = __repr__

    @classmethod
    def de_dict(cls, dados: Any) -> "PedidoDeCalculoRE":
        problemas = problemas_do_pedido_re(dados)
        if problemas:
            raise ValueError("pedido de RE inválido: " + ", ".join(problemas))
        return cls(ramo=int(dados["ramo"]), segurado=dict(dados.get("segurado") or {}),
                   risco=dict(dados.get("risco") or {}), renovacao=dict(dados.get("renovacao") or {}),
                   comissao_desconto=dict(dados.get("comissao_desconto") or {}),
                   seguradoras=tuple(sorted({int(s) for s in dados.get("seguradoras") or ()})))

    def para_dict(self) -> dict:
        return {"ramo": self.ramo, "segurado": dict(self.segurado), "risco": dict(self.risco),
                "renovacao": dict(self.renovacao or {}), "comissao_desconto": dict(self.comissao_desconto or {}),
                "seguradoras": list(self.seguradoras), "assumidos": [], "coberturas": {}, "pacotes": {}}


# --------------------------------------------------------------------------
# O resultado
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Parcelamento:
    parcelas: Optional[int]
    tipo_pagamento: Optional[int]
    primeira_parcela: Optional[float]
    demais_parcelas: Optional[float]


@dataclass(frozen=True)
class Oferta:
    seguradora: str
    seguradora_codigo: Optional[int]
    pacote: str                         # `resultados[].identificacao`
    tipo_de_pacote: Optional[int]       # `resultados[].packageType`
    premio_total: float
    premio_mensal: Optional[float]
    franquia_valor: Optional[float]
    franquia_tipo: Optional[str]
    coberturas: Tuple[Tuple[str, Any], ...] = ()   # só a lista branca
    parcelamentos: Tuple[Parcelamento, ...] = ()
    tem_pdf: bool = False
    numero_calculo_presente: bool = False
    alertas: Tuple[str, ...] = ()
    # 🔴 INTERNO: nunca vai para o cliente. O adaptador da 129-B corta.
    comissao_percentual: Optional[float] = field(default=None, metadata={"interno": True})
    ramo: int = RAMO_AUTO


@dataclass(frozen=True)
class RespostaDaSeguradora:
    seguradora: str
    seguradora_codigo: Optional[int]
    familia: str
    ofertas: Tuple[Oferta, ...] = ()
    mensagens: Tuple[str, ...] = ()
    credenciais_validas: Optional[bool] = None
    tempo_resposta_ms: Optional[int] = None
    ramo: int = RAMO_AUTO


@dataclass(frozen=True)
class RodadaDoCalculo:
    t_s: Optional[float]
    respostas: Tuple[RespostaDaSeguradora, ...]
    fechado: bool
    ramo: int = RAMO_AUTO

    @property
    def ofertas(self) -> Tuple[Oferta, ...]:
        return tuple(o for r in self.respostas for o in r.ofertas)

    def por_familia(self) -> dict:
        saida: dict = {}
        for r in self.respostas:
            saida[r.familia] = saida.get(r.familia, 0) + 1
        return saida


# --------------------------------------------------------------------------
# Evento — a narração ao vivo (D-MC-50) só pode nascer daqui
# --------------------------------------------------------------------------
NOVA_OFERTA = "nova_oferta"
# a MESMA oferta (seguradora, pacote, tipo de pacote) voltou com outro prêmio: a narração
# TROCA o preço, não soma uma oferta. 📊 0 casos nas 5 fixtures (04/10) — o tipo existe para
# que o caso, quando vier, não vire uma segunda "nova_oferta" do mesmo pacote.
OFERTA_ATUALIZADA = "oferta_atualizada"
SEGURADORA_RECUSOU = "seguradora_recusou"
CONJUNTO_FECHADO = "conjunto_fechado"   # UMA vez por cálculo (leitor_agger.eventos_do_calculo)
# SPEC-129-C D-129C-04: no empresarial, a seguradora cuja atividade NÃO casou de forma inequívoca com a do pedido SAI do
# cálculo (nunca um código errado) e é narrada com este evento (família DADO: o corretor pode escolher o código à mão).
SEM_ATIVIDADE_COMPATIVEL = "sem_atividade_compativel"
# 🔴 Conserto 129-C (canário #3/#7 + juiz P1): a FAMÍLIA desse evento é o NOME do tipo, em maiúsculas — a mesma que a
# comparação (`app/services/multicalculo/comparacao.SEM_ATIVIDADE`) já mostra. Antes o motor gravava DADO e a comparação
# mostrava SEM_ATIVIDADE_COMPATIVEL: duas famílias para o mesmo fato.
assert SEM_ATIVIDADE == SEM_ATIVIDADE_COMPATIVEL.upper()
# O motivo gravado no evento (conserto 129-C canário #5): o texto da seguradora, saneado, até este tamanho.
MOTIVO_MAX = 300
MOTIVO_SEM_ATIVIDADE = "nenhuma atividade da lista desta seguradora casa sem dúvida com a do pedido"


@dataclass(frozen=True)
class Evento:
    tipo: str
    t_s: Optional[float]
    seguradora: Optional[str] = None
    seguradora_codigo: Optional[int] = None
    familia: Optional[str] = None
    oferta: Optional[Oferta] = None
    ramo: int = RAMO_AUTO
    # Conserto 129-C (canário #5): POR QUE a seguradora recusou — o texto dela (sem URL/chave; o motor ainda passa o
    # redator de PII). Fora da igualdade: o mesmo evento com outro texto é o MESMO evento (a chave não muda).
    motivo: Optional[str] = field(default=None, compare=False)
