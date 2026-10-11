# Laudo B0-b · SPEC-129-C · os três ramos na InfoCap

> ⚠️ ERRATA 11/10 (SPEC-131-0-A): a medição foi feita por uma conexão com o login da AutoFleet; a InfoCap da Resulta tem RE — ver programa-multicalculo/131-0/BLOCO0-INFOCAP-A-CONEXAO-TROCADA.md

Investigador B0-b (Opus 5.5), 11/10/2026. Só leitura: GET na InfoCap, `set transaction read only` no banco. **Nada foi gravado na
InfoCap nem no Supabase.** No repositório, nada foi alterado; os arquivos novos estão em `docs/intake/` (fora do git, pelo `.gitignore:113`).
Nenhum dado pessoal neste laudo: apólice = `sha256(nosnum)[:10]`, cliente = `sha256(codcli)[:10]`, PDF de conversa = `conv-<sha256[:12]>`.

O documento saneado para o repositório, com as tabelas 1, 3 e 4, está em `scratchpad/b0b-129c/RAMOS-NA-INFOCAP.md`.
Este laudo traz o método, as provas e os canários.

## 1. Como foi lido

- **Credencial:** `backend/.env` **não** tem `CORP_INFOCAP_RESULTA_*` (📊 17 chaves, nenhuma da InfoCap; o pacote presumia que
  tinha). Usei o mesmo caminho da 131-0: `tenant_connections ⨝ connector_templates(slug='infocap')`, `status='connected'`
  (📊 1 linha, na corretora de ensaio), decifrada com Fernet e o `ENCRYPTION_KEY`. Nenhum segredo foi impresso.
  📊 As 7 conexões InfoCap: 1 connected, 2 disconnected, 4 archived.
- **Cliente:** `scratchpad/b0b-129c/ic.py`, que só faz GET, com cache em disco (`raw/`, que contém PII e fica só no scratchpad), retry e
  tratamento de 404/400 "Nenhum..." como vazio.
- **Documentação:** a coleção Postman (`documenter.gw.postman.com/api/collections/33455116/2sAYkBrLmi`) tem 54 requisições.
  As duas que importam aqui, e que o código ainda não usa: **`/documento_anexos?codfil&nosnum`**, que devolve os anexos com `url` S3
  baixável sem cabeçalho, e **`/lista_ramos?telram=`**.
- **Mapa de ramos** (`/ramos`, 55 ramos): COND = **4**, RESI = **2**, EMPR = **3**, BRES = **45**. `/lista_ramos?telram=1`
  só lista ramos de auto. Os códigos do Agger (16/2/18) são outro mapa.

## 2. O achado: a InfoCap da Resulta é o sistema do AUTO

| medição 📊 (11/10/2026) | resultado |
|---|---|
| `/documentos_bi` 2015 a 2026, `tipo_doc=TODOS`, ano a ano | 32.901 documentos · COND 0 · RESI 12 · EMPR 3 · BRES 0 |
| `/renovacoes`, `fimvig` de 11/10/2026 a 31/12/2031, `cancelado=F` | 3.040 · AUTO 2.972 · RESI 5 · EMPR 2 · COND 0 |
| `/renovacoes` com `codram=4`, `cancelado=T`, 2025 a 2027 | 0 |
| `/documentos?texto=CONDOMINIO / EDIFICIO / RESIDENCIAL / ASSOCIACAO` | 0 / 0 / 0 / 0 |
| `/lista_clientes` (prefixo) `CONDOMINIO`, `EDIFICIO` · cadastro total (`/clientes`) | 0, 0 · 16.290 |
| `codfil` 2 a 5 | ignorado: tudo vem com `codfil=1` |
| `/login`: as 17 flags `p*` | todas `T` |
| 88 CPF/CNPJ válidos (dígito verificador conferido) nas conversas de "outros ramos" do intake → `/cliente_cpf` → `/cliente_ligacoes` | **79 são clientes** · 518 documentos ligados · AUTO 488, FROT 16, CTVE 10, MOBI 4 · **RESI, COND e EMPR: 0** |

FATO: o cliente patrimonial existe na InfoCap; a apólice patrimonial, não. INFERÊNCIA: a carteira patrimonial é controlada
fora (Agger, portais, planilha). Sobra uma ressalva: pode existir **outra base ou login InfoCap** só da carteira patrimonial, que
este acesso não alcança. Nada no intake menciona isso (📊 0 ocorrências de "infocap" ou "corp" nas conversas de outros ramos e
no arquivo de acessos dos portais). **Pergunta ao Founder: a Resulta lança condomínio, residencial e empresarial em algum sistema?**

A base mistura duas SUSEPs: das 14 apólices patrimoniais com PDF, 10 são da segunda corretora do grupo e 4 da Resulta.

## 3. O que foi baixado e onde está

`C:\Users\amand\Projetos\AUTOBROKERS RESULTA\AutoBrokers-FIX\docs\intake\MULTICALCULO AGGER\129C-RAMOS\`
- `residencial\`: 16 PDFs (13 da InfoCap: apólices e propostas de 11 apólices; 2 da Tokio vindos das conversas: uma proposta e uma cotação)
- `empresarial\`: 8 PDFs (Sura: 1 proposta; Yelum: 7 arquivos de **uma** apólice cadastrada 2 vezes). O boleto foi descartado.
- `condominio\`: 1 PDF (Tokio Condomínio, das conversas)
- `INDICE.json`: sem dado pessoal. Traz id, origem, ramo InfoCap × ramo real, produto, casa/apto, habitual/veraneio, seguradora,
  vigência, prêmio, arquivos e o bloco `canarios`.
- `_PRIVADO-chaves-infocap.json`: `nosnum`/`codfil`/`codcli` para reabrir cada apólice (`/documento`). Só local.

**Total: 15 documentos InfoCap** (é TUDO o que a base tem desses ramos, então o teto de 15 por ramo não foi atingido: RESI 12,
EMPR 3, COND 0) **mais 3 PDFs das conversas**. O Supabase Storage não foi usado: gravar seria escrita em produção, e o intake local
atende aos outros chats. 📊 Buckets existentes: avatars (público), portal-evidence, chat-media, voice-messages, chat-docs
(não existe bucket `documents`).

A API **entrega o PDF** (`/documento_anexos`, tipos A = apólice, I = proposta/inspeção, O = outro, P = proposta, B = boleto).
📊 Os dados estruturados vêm pela metade: `/itens` traz `garantias[]` (garantia, `impseg` = LMI, taxa, prêmio, franquia
"10.00%-350,00") em **4 de 15** documentos, conferidos contra o PDF em 2; nos outros 11, vem vazio. `/documento` não tem LMI.
**Fonte: o PDF; `garantias[]` é atalho quando foi lançado.**

## 4. Coberturas: resumo (as tabelas completas estão no RAMOS-NA-INFOCAP.md §3)

- **Residencial (n = 13):** a básica (incêndio) aparece em 13/13, mediana de R$ 100 mil (R$ 500 mil entre as avulsas). O pacote padrão
  das avulsas é incêndio, RC familiar, vendaval, danos elétricos, aluguel e assistência 24 h. O mais em conta: Porto com incêndio de
  R$ 100 mil, RC de R$ 10 mil e aluguel de R$ 8 mil, por R$ 247,88. Seis das 13 são HDI Duo, atrelado ao auto (pacote fixo 30/3/6/6, de R$ 166 a 198).
  Casa 10, apartamento 2; habitual 12, veraneio 1.
- **Condomínio (n = 1, Tokio):** incêndio de R$ 17,6 milhões; bens dos condôminos R$ 2 milhões; RC síndico e RC condomínio
  R$ 700 mil cada; aluguel dos condôminos R$ 250 mil; vendaval R$ 200 mil; RC garagem; ruptura de tubulações; danos elétricos;
  portões; roubo; vidros; assistência. Total de R$ 8.934. Vertical, residencial, sem elevador, valor de novo. **Não informa área nem unidades.**
- **Empresarial (n = 1, Sura, proposta):** imóvel desocupado (loja), valor em risco de R$ 911 mil; incêndio = valor em risco,
  vendaval R$ 50 mil, impacto R$ 30 mil, danos elétricos R$ 20 mil. Atípico: não serve como pacote padrão.

## 5. A regra dos +15 %

📊 2 pares de anos seguidos, os dois HDI Duo: incêndio de R$ 30 mil → R$ 30 mil (**0 %**) nos dois. **Não confirmado e não testável na
InfoCap**, porque as renovações montadas pelas comerciais não estão lá. A medição tem de ser feita no histórico do Agger
(LMI anterior × LMI cotado). Até lá, é **parâmetro declarado da corretora**, não constante de código.

## 6. Canários (um cálculo de conferência por ramo, pelo gerente)

| ramo | id | por quê | ressalva |
|---|---|---|---|
| Condomínio | **conv-9789d6e0ee0f** (`condominio/conv-9789d6e0ee0f_A.pdf`) | vigente de 22/01/2026 a 22/01/2027, Resulta, todas as coberturas com LMI e o tipo, a estrutura, os elevadores e a indenização | não está na InfoCap (veio da conversa); área e unidades não constam e precisam vir de outra fonte |
| Residencial | **cffc0a6ea2** (HDI Em Casa) | vigente de 26/01/2026 a 26/01/2027, avulso (não é Duo), casa habitual de alvenaria, incêndio de R$ 100 mil + RC + danos elétricos + vendaval + valor de novo, com apólice e proposta | é HDI, não Allianz. A alternativa é **1ee68aee40** (Porto, vigente até 27/05/2027, incêndio de R$ 500 mil). Nenhuma Allianz vigente na InfoCap |
| Empresarial | **63b746709f** (Sura) | o único empresarial verdadeiro, vigente de 10/02/2026 a 10/02/2027 | é PROPOSTA (o `pretot` na InfoCap é 0) e o imóvel está desocupado: risco atípico. Um caso melhor tem de vir do Agger ou da Resulta |

## 7. Riscos e recomendações ao gerente

1. **A premissa do Founder está refutada pela medição:** a InfoCap não é a fonte dos ramos patrimoniais. Registrar isso na SPEC e
   perguntar onde a Resulta guarda essas apólices. RECOMENDAÇÃO: usar o histórico do Agger (672/182/115) como fonte de coberturas e de renovação.
2. **O ramo da InfoCap pode estar errado** (2 "EMPR" que são residencial) e **duplicado** (1 apólice com 2 códigos de cliente).
   O motor deve ler o ramo do PDF ou da seguradora quando houver conflito.
3. **Duas SUSEPs numa conexão:** a apólice traz o corretor; a regra de dono e a carteira por corretora não podem presumir 1 conexão = 1 corretora.
4. **`/documento_anexos` é o caminho do PDF** e o código atual não o usa (`infocap_connector.py` procura `acompanhamento.emissao.url_apolice`).
5. `backend/.env` sem `CORP_INFOCAP_*`: o `FonteInfocap.para_empresa("resulta")` falha nesta máquina. A credencial vive em `tenant_connections`.
