# PORTAL HDI DIGITAL — o mapa do território

**Endereço** `https://www.hdi.com.br/hdidigital/` · **Portal key** `hdi_corretor`
**Última medição** 12/08/2026 · **Cobrança** ✅ funciona

> **O método está na [SPEC-033](../specs/SPEC-033-portal-api-automation-playbook.md)
> e na [SPEC-070](../specs/SPEC-070-cobranca-multi-seguradora.md).** Este
> documento é só o que se sabe DESTE portal. Leia as duas antes.

---

# 1. A PORTA

## 1.1 O login tem duas camadas

📊 A tela tem **10 inputs**, e os dois que a pessoa enxerga **não têm `id` nem
`name`**:

```
j_username     text      0 x 0    ← o campo REAL (j_security_check clássico)
j_password     password  0 x 0    ← o campo REAL
cod_produtor   text      0 x 0    ← oculto
(sem id/name)  text    295 x 40   ← o que o corretor vê e digita
(sem id/name)  password 295 x 40  ← idem
m_flg_intranet · m_multiEmpresa · t_prd · c_pc · m_cpf_prdtor   hidden
```

**Casar por `id` ou `name` não acha o campo visível.** Preenchemos **as duas
camadas**: a visível porque é o caminho que a página espera, a oculta porque é
o que o servidor lê.

## 1.2 A tela monta por JS — esperar tempo fixo não serve

📊 Com `wait 2s` fixo o robô concluía *"campos de login não encontrados"* — um
falso negativo que parecia bloqueio de portal. Espera-se o **campo de senha
visível existir** (`width > 40`), não o relógio.

## 1.3 Sem CAPTCHA — a única menção é CSS morto

📊 O único `captcha` no HTML é `.g-recaptcha { display: none; }`. Widget
desligado. **Login é senha pura.**

## 1.4 🔴 Akamai Bot Manager — a trava mais séria

Cookies `_abck`, `bm_sz`, `bm_sv`, `ak_bmsc`. Recusa com `Access Denied` +
`errors.edgesuite.net`.

📊 Medido um fator por vez, com CONTROLE repetido no início e no fim:

```
headless clássico ...........  BLOQUEADO
+ args anti-automação .......  BLOQUEADO
+ script de stealth .........  BLOQUEADO
+ args E stealth ............  BLOQUEADO
navegador COM janela ........  PASSOU
--headless=new ..............  PASSOU     ← e roda sem tela
```

**Cinco variações, o mesmo bloqueio → nenhuma delas era a causa.** O fator é o
*modo* headless: o clássico é um binário separado, com impressão digital
própria. Ver `portal_worker.worker._launch_kwargs()`.

**E ele também reage à FREQUÊNCIA.** 📊 Depois de ~15 acessos em 30 minutos, o
modo que passava começou a receber `Access Denied` — e continuou bloqueado 12
minutos depois. Bloqueio por IP, temporário, disparado por volume.

### O segundo fator: o User-Agent

✅ **RESOLVIDO em 12/08/2026.** O `--headless=new` conserta a impressão digital
em **JavaScript**, mas **não** tira `HeadlessChrome` do **cabeçalho**. São dois
fatores independentes, e o Akamai barra pelo primeiro que encontrar.

📊 Medido do MESMO IP, variando só o User-Agent, com controle nas duas pontas:

```
UA limpo   (Chrome/…)           PASSOU
UA padrão  (HeadlessChrome/…)   BLOQUEADO
UA limpo   (Chrome/…)           PASSOU
```

> **A lição que quase custou uma assinatura de proxy:** o diagnóstico anterior
> comparou o navegador com "um cliente HTTP simples" (`page.request`) e concluiu
> que o fator era o IP. **O teste estava furado** — `page.request` herda o
> User-Agent do contexto, então os dois mandaram o mesmo cabeçalho e o teste não
> isolou o que dizia isolar. Um teste que não consegue separar o que promete
> separar produz uma conclusão confiante e errada.

**A correção:** o contexto do worker define `user_agent`, derivado do próprio
binário (troca só `HeadlessChrome` por `Chrome`, mantendo versão e plataforma).
Ver `portal_worker.worker.user_agent_sem_headless`.

📊 **Resultado no servidor, pela fila real:** `done`, 1 boleto de 27.037 bytes
no bucket, **saída de rede direta — sem proxy nenhum.** O IP de datacenter
(Hostinger, AS47583) **não** era um fator para a HDI.

## 1.5 A sessão dura 30 minutos

📊 `serverTime=1786386642398` → `sessionExpiry=1786388442397` = **1.800.000 ms**.

**Consequência de arquitetura:** com espaçamento de 4–8 min entre envios, uma
rodada de 20 inadimplentes levaria ~2 h — a sessão morre no minuto 30. É por
isso que **colher e entregar são fases separadas** (SPEC-070 §5).

---

# 2. A TOPOLOGIA

Dois mundos no mesmo domínio:

```
/digital2/...            shell MODERNO. JSON. Angular/jQuery.
                         Sessão viaja em ?chaveUsuario=...&tokenSec=...

/web/hdidigital/*.htm    app LEGADO de 2008 (Progress WebSpeed).
                         HTML iso-8859-1. Estado em <input hidden>.
```

## 2.1 A ponte entre eles

```
POST /digital2/legado/dsp_parcelas_busca_2008/1/9?chaveUsuario=&tokenSec=
   → devolve um <form id="formCarregarLegado"> que se auto-submete
   → e é ele que carrega a IDENTIDADE da sessão
```

**Campos que vêm na ponte** (todos necessários adiante):

```
m_cod_corretor .... 500027665      código do corretor na HDI
m_cod_sucursal .... 008            filial
l_s / n_s ......... 008 / FLORIANOPOLIS
c_pc .............. X605000297115_4620    ← MUDA A CADA SESSÃO
c_pc_orig ......... idem
c_pc_grupo ........ idem
m_cpf_prdtor ...... CPF do corretor (é o login)
m_nome_user_web ... idem
tokenSec .......... token de sessão
m_cod_opcao_menu_2008 = 9   ← 9 é o menu Parcela
t_prd / t_prd_orig = C      ← C de Corretor
```

> ⚠️ **`c_pc` não é fixo.** 📊 O mesmo corretor apareceu com
> `K659709550002_4420`, `G667095500029_4420`, `A...`, `X605000297115_4620` em
> sessões diferentes. **Colher do HTML, nunca fixar.**

## 2.2 Encoding

`text/html;charset=iso-8859-1`, e mistura acento cru com entidade
(`D&eacute;bito`). Sem `html.unescape`, `debito` não casa e a parcela em débito
passa por boleto.

---

# 3. AS ARMADILHAS

## 3.1 🔴 A busca é ASSÍNCRONA — a que mais custou

📊 O **primeiro POST nunca devolve a tabela.** Devolve:

```html
<p class="txt" title="Req:1331319740-Processando:1331272048">
   Por favor aguarde. Estamos processando a requisição...</p>
<script>tempo = setTimeout("document.f_requisicao.submit();",5000);</script>
```

...e um `<form name="f_requisicao">` que se **reenvia sozinho em 5 s**. É o
reenvio que traz as parcelas.

```
1º POST   m_num_requisicao=1331319740   m_num_requisicao2=0   m_total=0
2º POST   m_num_requisicao=0            m_num_requisicao2=1331319740   m_total=2
                                        ↑ os dois TROCAM DE LUGAR
```

> **Por que é a pior:** HTTP 200, ~4 KB de corpo, tudo com cara de sucesso. O
> parser lia zero linhas e ia terminar `done` dizendo **"nenhum inadimplente"**.
> Falhava afirmando o contrário do que estava acontecendo.

## 3.2 🔴 `s_tipo=1` é "A vencer", não "Atrasadas"

📊 O `<select>` real:

```html
<option value="0">Todas</option>
<option value="1" selected>A vencer</option>   ← o padrão da TELA
<option value="2">Quitadas</option>
<option value="3">Atrasadas</option>           ← o que a cobrança quer
<option value="4">Canceladas</option>
```

Adivinhar custou cinco rodadas contra o portal. O `<select>` responde em três
segundos.

## 3.3 🔴 O boleto não é um `<a href>`

A célula `Gerar` é um `<td>` com:

```html
onclick="alerta_conjugado('');window.open('dsp_boleto.htm?p=<hash-grande>',
         'boleto','toolbar=no,...')"
```

Procurar `href` não acha nada, **mesmo com a tabela lida corretamente**.

## 3.4 🟠 Uma `<table>` POR DOCUMENTO, e HTML malformado

Não é uma tabela com N linhas: são N tabelas de uma linha, e a primeira **não
fecha o `<tbody>`**. Parser que exige HTML bem formado quebra.

## 3.5 🟠 Crédito também não gera boleto

📊 A coluna `Forma de Pagamento` traz `Boleto` · `Débito` · `Crédito`. Nos dois
últimos, a coluna `Gerar` diz *"Parcela diferente de Boleto Bancário."*

**A marca certa é a frase, não a forma de pagamento** — casar por "débito"
deixa o Crédito passar como se tivesse boleto.

---

# 4. AS TRAVAS

## 4.1 🚫 Botões que ESCREVEM no contrato — o robô nunca toca

Ficam na **mesma linha** do boleto, e todos por `onclick`:

| Botão | Função JS | O que faz |
|---|---|---|
| Reprogramação de Parcela | `reprogParcela(...)` | muda vencimento |
| Termo de Adimplência | `termoAdimplencia(...)` | emite documento |
| Antecipação de Parcelas | `checkAntecipa(...)` | antecipa cobrança |
| **Alterações Financeiras** | `checkAlterar(...)` | **troca forma de pagamento** |

📊 O `checkAlterar` abre `prompt()` com opções e submete para
`dsp_troca_dc_x_boleto.htm`, `dsp_troca_dados_credito.htm`,
`dsp_troca_dados_debito.htm`. **É por aqui que se converteria débito em boleto —
e é exatamente por isso que é proibido ao robô.**

Em `hdi_corretor.ACOES_PROIBIDAS`, com teste que consegue falhar.

## 4.2 Janela máxima de 30 dias

📊 Da validação do próprio botão Buscar:

```js
if (dat_final - dat_inicial > 2583600000) alert("Período não pode ser superior a 30 dias...")
// 2.583.600.000 ms = 29,9 dias
```

Outros limites vistos no mesmo JS: 60 dias em `checkParcelaAlter`; 15 dias
quando `tarefaweb` (Excel) está marcado com `s_tipo` 1 ou 3; 1 ano para
geração de arquivo.

**Varredura em blocos de 30 dias, sem buraco entre eles.**

## 4.3 Outras validações da tela

```
nome ....... mínimo 10 caracteres
placa ...... mínimo 6
chassi ..... mínimo 10
CPF ........ 11 dígitos exatos    CNPJ ... 14
data ....... DD/MM/AAAA
```

---

# 5. OS SERVIÇOS

## 5.1 COBRANÇA ✅ funciona

**A cadeia, quatro passos:**

```
1  POST /digital2/legado/dsp_parcelas_busca_2008/1/9?chaveUsuario=&tokenSec=
      → <form> com a identidade da sessão

2  POST /web/hdidigital/dsp_parcelas_busca_2008.htm    (com esses campos)
      → a tela de busca

3  POST /web/hdidigital/dsp_parcelas_view_2008.htm
      + data_ini · data_fim · s_tipo=3
      → "aguarde" → REENVIAR f_requisicao → A TABELA

4  onclick da célula Gerar → dsp_boleto.htm?p=<hash>
      → boletoPDF.jsp?<todos os dados>  → O PDF
```

**Campos da tabela de resultado:**

```
Documento/Parcela .... 01.008.119.003755.000000 - 02 de 06
Vencto. .............. 09/08/26
Limite sem Vistoria .. 04/09/26
Nome cliente ......... CONDOMINIO HORIZON RESIDENCIAL
Valor (R$) ........... 1.006,02
Posição .............. Parcela a Vencer | Parcela em Atraso   ← o marcador
Data de Pagamento .... (vazio se não pago)
Data Prev. Receb. .... 
Forma de Pagamento ... Boleto | Débito | Crédito
Gerar ................ "2ª via" (onclick) | "Parcela diferente de Boleto Bancário."
```

**O `<tr id>` codifica a apólice inteira:**
`tr_01008005A065191000000004` = `01`·`008`·`005`·`A`·`065191`·`000000`·`04`
= empresa · sucursal · carteira · tipo · nº documento · endosso · parcela

**A URL do boleto traz o boleto inteiro montado** (`boletoPDF.jsp?...`): banco,
carteira, nosso número, agência, conta, cedente, convênio, cliente, CPF/CNPJ,
endereço, CEP, valor, vencimento, mensagens de instrução.

**O que fazer com débito/crédito em atraso:** não há boleto. Vira **tarefa para
a atendente** e o robô **não fala com o segurado** (decisão do Founder,
12/08/2026).

**Código:** `backend/portal_worker/journeys/hdi_corretor.py`
**Fixture:** `backend/tests/fixtures/hdi_parcelas.py` (estrutura real, dados trocados)

## 5.2 RENOVAÇÃO 📋 conhecimento anotado, sem código

**Menu Renovação** — 📊 visto no portal, submenus:

```
Renovações
Renovações HDI Seguros do Brasil (antiga Sompo Consumer)
Renovação Patrimonial
Renovação Ativa
Relatório Renovações
```

**Pistas já colhidas:**
- `renovacaoAutomaticaController_03072026.js` e `renegociacaoFrotaController_*.js`
  carregam na home — a renovação tem controlador próprio no shell novo
- `apoliceAnteriorController_*.js` sugere consulta à apólice anterior
- Em Adm → Relatórios existe **Renovações** e **Status dos seus Negócios**
- 💭 **Hipótese a testar:** a renovação deve seguir o mesmo desenho
  `dsp_<algo>_2008.htm` do legado, com a mesma ponte e provavelmente a mesma
  busca assíncrona. Confirmar com uma captura de Response.

**O que já está pronto e serve:** login (§1), ponte (§2.1), leitura de tabela
legada, o modo do navegador (§1.4), e a lista de botões proibidos (§4.1).

## 5.3 COTAÇÃO 📋 conhecimento anotado, sem código

**Menu do topo:** `Cotação · Vida · +Negócios · Proposta · Vistoria`

📊 Controladores vistos carregando na home (indicam o que existe do lado novo):

```
cotacaoController · calcularController · resumoCotacaoController
resumoCotacaoHomeController · crivoController · subscricaoController
agravoDescontoController · garantiaController · coberturaController
veiculoController · produtoController · itemController
bureauReceitaFederalController · avaliacaoRiscoController
padraoCalculoController · melhorDataPagamentoController
formaPagamentoController · parametrosFrota · frotaImportacaoArquivoController
xlsx.full.min.js  ← importação de frota por Excel
```

> ⚠️ **Cotação é TRANSACIONAL.** SPEC-033 §7: capturar o fluxo inteiro, e
> **parar antes de emitir**. Emissão é dinheiro do cliente.

## 5.4 OUTROS SERVIÇOS

**Adm → Relatórios:** Comissões · Acompanhamento · Notas Fiscais Pendentes ·
**Cartas Enviadas** · Apólice em PDF · Extrato Pró-Labore · Status dos Negócios

**Adm → Cliente:** Cadastro · **Buscar Clientes** · **Meus Clientes**

> 💭 **Duas pistas guardadas:**
> `Cartas Enviadas` pode ser onde a HDI arquiva a carta de inadimplência (o
> equivalente à Ficha de Gestão da Allianz).
> `Buscar Clientes` / `Meus Clientes` pode ter telefone — mas a regra do produto
> é que o telefone vem do sistema de gestão da corretora, não do portal.

**Menu do topo, completo:** Home · Cotação · Vida · +Negócios · Proposta ·
Vistoria · Apólice · Rastreador · **Parcela** · Renovação · Sinistro · Ajuda · Adm

**Cabeçalho:** Assistência · Chat On-Line · Manuais · Busca de Clientes · Pesquisa HDI

---

# 6. DADOS DA TELA que a cobrança NÃO usa

Anotados de propósito — é o que faz a renovação custar menos depois.

```
Limite sem Vistoria .............. data
Data Prev. Receb. ................ data
Cobertura Proporcional até ....... data (por documento)
Tentativas de débito ............. nº · última · próxima  (linhas em débito)
Total Pago no período ............ soma
Total em Aberto no período ....... soma
Legenda (★ por linha) ............ atraso acima do limite · faturamento mensal ·
                                   pagamento diferente de boleto · parcela
                                   anterior pendente
mostra_proposta(empresa, sucursal, carteira, tipo, docum, endosso, item,
                t_corretor, cod_corretor, tokenSec)  ← abre a proposta
"Agendar geração de arquivo Excel. Intervalo: 15 minuto(s)"  ← exportação
g_bol(...)  ← gerador de boleto alternativo, por parâmetros soltos
```

---

# 7. HISTÓRICO

| Data | O que aconteceu |
|---|---|
| 10/08/2026 | Primeiras capturas. Filtro `api` no F12 não achou nada — **a HDI não usa essa palavra em endereço nenhum**. O filtro certo é `dsp_` |
| 10/08 | Akamai bloqueia headless clássico. Medido, resolvido com `--headless=new` |
| 10/08 | ~15 visitas em 30 min → bloqueio por IP, ~horas |
| 12/08 | Response completo capturado. **Os 4 defeitos caíram de uma vez** |
| 12/08 | ✅ 1 boleto real de 27.037 bytes baixado, validado como `%PDF` |
| 12/08 | Pelo worker no servidor: `Access Denied`. Diagnóstico apontou o IP — **e estava errado**, por culpa do próprio teste (§1.4) |
| 12/08 | ✅ **HDI FECHADA.** UA limpo → `done` pelo worker de produção, boleto no bucket, **sem proxy**. Allianz na mesma rodada: 4 de 4 (linha de controle) |

---

*Autoridade: SPEC-033 (método) · SPEC-070 (processo) · SPEC-023A (runbook Allianz, o molde).*
