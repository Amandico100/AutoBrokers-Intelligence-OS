# BLOCO 0 da SPEC-131-0 — a InfoCap da Resulta TEM condomínio, residencial e empresarial: a conexão estava com o login da AutoFleet

> 11/10/2026 · gerente da SPEC-131-0 (Opus 5.5) · só leitura na InfoCap (GET + POST /login) · nenhum nome, CPF ou telefone neste arquivo.
> Corrige a D-129C-02 e o BLOCO0-INFOCAP / RAMOS-NA-INFOCAP da 129-C. Pergunta do Founder (11/10): *"as apólices estão dentro do
> CORP e por algum motivo não estão aparecendo — tire a limpo"*.

## 1. A causa, em uma linha

📊 A única conexão InfoCap `connected` do produto — `5039f90d…`, nome **"InfoCap RESULTA"**, na corretora de ensaio Amandus, criada em
21/09/2026 — guarda o login **`autofleet@api.com.br`**. Tudo o que foi medido "na InfoCap da Resulta" por essa conexão desde 21/09 era a
carteira da **AutoFleet**.

```
comando: decifrar tenant_connections.encrypted_secret_ref pelo serviço do produto (get_encryption_service().decrypt), imprimir só o login
604ec9f1 (Amandus)  "InfoCap"               archived 04/09 (motivo "founder_decision_keep_resulta_only") -> login resulta@api.com.br
dfbfdea5 (Resulta)  "InfoCap · Resulta…"     archived 18/08                                              -> login de pessoa (não é o da API)
5039f90d (Amandus)  "InfoCap RESULTA"        CONNECTED desde 21/09                                       -> login autofleet@api.com.br   ⟵ a troca
```

## 2. A prova: dois bancos, dois logins

📊 `POST /login` com os dois logins (11/10): os dois entram, `codfil=1`, mesmas 17 permissões (`p9…p602 = T`), usuários distintos
(código 75 "API RESULTA" e 73 "API CORP"). São **dois bancos diferentes** da CorpAPI:

| `/documentos_bi` · `data=INIVIG` · `tipo_doc=A` | Resulta (`resulta@`) | AutoFleet (`autofleet@`) |
|---|---|---|
| 2024 | 📊 3.996 — AUTO 2.365 · **RESI 458 · COND 203 · EMPR 194** · … | 📊 2.877 — AUTO 2.823 · FROT 29 · RESI 2 |
| 2025 | 📊 1.680 — **RESI 400 · COND 248** · GOC 230 · **EMPR 190** · AUTO 97 · … | 📊 3.117 — AUTO 2.902 · CTVE 75 · PQRE 74 · RESI 5 |
| 2026 | 📊 1.173 — **RESI 255 · COND 227 · EMPR 148** · GOC 112 · … (AUTO fora do top 14) | 📊 2.727 — AUTO 2.432 · PQRE 219 · RESI 4 · EMPR 2 |

Bate com o que o Founder disse: a Resulta separou o auto para a AutoFleet (2024 → 2025 o AUTO da Resulta cai de 2.365 para 97) e
ficou com os outros ramos; a AutoFleet é auto e frota.

📊 O cliente-teste do Founder (CPF terminado em -36) existe nos DOIS bancos com o **mesmo código de cliente (3477)** — sinal de que o
banco da AutoFleet nasceu como cópia do da Resulta (a mesma apólice auto HDI de 2024, nosnum 91175, aparece nos dois):
- **Resulta:** 10+ apólices **RESI Allianz** (a vigente: 31/08/2026–31/08/2027), vida Zurich, consórcios Porto, um RD E.
- **AutoFleet:** auto Liberty/Yelum (04/05/2026–04/05/2027), celular Sura, auto Porto e HDI antigos.

**Por isso "o chat acha as apólices do Rafael":** pela conexão trocada, o chat da Amandus lê o banco da AutoFleet e acha o AUTO e o
celular — não o residencial. Comando: `GET /cliente_cpf?cpf_cnpj=…&codfil=1` → `GET /cliente_ligacoes?codigo=3477`, nos dois logins.

## 3. As renovações dos próximos 30 dias (11/10 → 10/11/2026), com o login certo

`GET /renovacoes?dt_ini=11/10/2026&dt_fim=10/11/2026&qtd_pag=5000&pag=1&ordem=nosnum&orientacao=asc&texto=&cancelado=F&resgates=F`

| | Resulta | AutoFleet |
|---|---|---|
| apólices | 📊 **99** — RESI 34 · EMPR 20 · COND 14 · VIND 6 · CAPI 5 · VIAG 4 · RCPR 3 · VGRP 3 · GOC 3 · NAUT 2 · … | 📊 **217** — AUTO 210 · MOBI 5 · FROT 1 · RESI 1 |

(As "228 renovações, 221 AUTO" da proposta da 131-0, medidas em 10/10 "na Resulta", são a AutoFleet: mesma ordem de grandeza.)

## 4. A regra do dono — agora provada em DOIS tenants reais

`GET /prod_docs?codfil=<codfil>&nosnum=<nosnum>` (avulso), uma chamada por apólice, em série; papel lido do sufixo do nome em
`GET /produtores?texto=&codage=1` (sem `codage` a rota dá 500).

| | Resulta (99) | AutoFleet (217) |
|---|---|---|
| apólices com **exatamente 1** produtor `indireto = "F"` | 📊 **99 / 99** | 📊 **217 / 217** |
| papel (sufixo do nome) desse produtor | 📊 FECHADOR 92 · EXECUTIVO 1 · sem rótulo 6 | 📊 FECHADOR 213 · sem rótulo 4 |
| a posição (`ordem`) dele | 📊 1: 37 · 2: 19 · 3: 23 · 4: 15 · 5: 3 · 6: 2 | 📊 1: 24 · 2: 95 · 3: 45 · 4: 51 · 5–6: 2 |
| o `ordem 1` é o dono? | 📊 **37 / 99** | 📊 **24 / 217** |
| o `produtor` de `/renovacoes` é o dono? | 📊 **38 / 99** | 📊 **25 / 217** |
| donos distintos no mês | 📊 9 (maiores: 40 · 33 · 11) | 📊 9 (maiores: 83 · 29 · 28) |
| códigos de produtor | 📊 119 (INDICADOR 18 · FECHADOR 15 · EXECUTIVO 2 · CORRETORA 3 · sem rótulo 81) | 📊 105 (17 · 14 · 2 · 3 · 69) |

Campos do `/prod_docs` avulso (📊 os dois bancos): `codpro`, `nome_produtor`, `ordem`, `indireto`, `codage`, `nome_agente`, `per_r`,
`val_r`, `perpart`, `taxa_repasse`, `forma_repasse_*`, `base_*`. 🔴 O código do produtor aqui é **`codpro`** (no `prod_docs` embutido em
`/renovacoes` é `cod_pro`).

**Conclusão (FATO):** D-131-0-03 vale nas duas corretoras: o dono da renovação na InfoCap é o produtor com `indireto = "F"` no
`/prod_docs` avulso. O código de hoje (`fonte_infocap.py`, `ordem == 1`) erra o dono em 62 de 99 (Resulta) e 193 de 217 (AutoFleet).

## 5. O que muda no programa

| antes | agora |
|---|---|
| D-129C-02: "a fonte de RE é o histórico do Agger, a InfoCap da Resulta não tem RE" | **revista** (D-131-0-26): a InfoCap da Resulta é a fonte de QUEM renova e QUANDO (99 no mês); o Agger continua a fonte das coberturas montadas pelas comerciais (laudo de campos em §6) |
| P-129C pendência "onde a Resulta lança RE?" | **FECHADA**: na InfoCap, no banco da Resulta |
| a conexão "InfoCap RESULTA" da Amandus | o nome mente — ela é a AutoFleet (D-131-0-27) |

## 6. Os três laudos (investigadores Opus 5.5, 11/10, só leitura)

**6.1 As apólices em PDF do intake × o CORP** (laudo fora do git: carrega números reais de apólice). 📊 As **25** apólices reais estão no
CORP, cada uma no banco da corretora impressa no PDF (**16 Resulta · 9 AutoFleet · 0 nas duas**), mesmo número e mesma vigência em 24/25.
As 15 de condomínio, residencial e empresarial: **todas no banco da Resulta**. Seguradoras por ramo na Resulta (📊 `/documentos_bi` 2026):
Condomínio 227 (Allianz 161 · Tokio 42 · HDI 10) · Residencial 255 (Allianz 178 · Yelum/LIBE 23 · HDI 19 · Tokio 14) · Empresarial 148
(Allianz 44 · Tokio 33 · Porto 29 · Chubb 12). Para a renovação de RE: `/itens` traz endereço do risco, atividade e coberturas com
importância segurada e franquia (📊 30 vigentes por ramo: coberturas COND 28 · RESI 29 · EMPR 22), mas a lista é INCOMPLETA (📊 condomínio
Allianz: 14 coberturas somam R$ 9.656,91 de R$ 12.050,14 do PDF) → a fonte completa é o PDF que o próprio CORP guarda.
Armadilhas da API: a busca por número só acha apólice VIGENTE; o número não tem formato fixo (casar por dígitos sobre a lista do cliente);
CPF com dois cadastros dá 500; `/itens` exige a data de início.

**6.2 A CorpAPI rota a rota** → [`LAUDO-CORPAPI-ROTA-A-ROTA.md`](LAUDO-CORPAPI-ROTA-A-ROTA.md). Os 4 links do Founder: `/renovacoes`,
**`/documento_anexos` (o PDF da apólice, link temporário de ~1 h — 📊 77 de 99 renovações com o arquivo da apólice; RESI/EMPR/COND
completos)**, `/documento`, `/producao`. `/renovacoes` aceita só `dt_ini, dt_fim, qtd_pag, pag, ordem, orientacao, texto, cancelado,
resgates, codcli, codram, codcia` (parâmetro desconhecido = 500) — **nenhum filtro por produtor**: o dono é calculado do nosso lado. O
produtor `indireto="F"` tem `perpart = 100` nas 99. Rota fora da coleção: `GET /usuario?codigo=N` (usuário ↔ produtor), 📊 vazia na prática
(1 de 39). "403" do gateway = rota inexistente, não permissão. Vazio às vezes é 200 com `message`.
🔴 Fora do escopo: `cpf_cnpj=00000000000` devolve um cliente REAL (P-1310-CPF-ZERO).

**6.3 Os prints do dashboard** → [`LAUDO-PRINTS-DO-CORP.md`](LAUDO-PRINTS-DO-CORP.md). Prints de 30/06–01/07/2025: CORP clássico (Resulta)
e CorpNow (AutoFleet). Nada escondido por permissão: as janelas padrão da TELA escondem (sinistros 180 dias, "documentos antigos",
"apenas vigentes"). O papel do produtor está no NOME, um cadastro por papel. 🔴 O `nosnum` se repete entre os dois bancos → nenhuma chave
pode ser só `codfil:nosnum` (auditoria da chave da apólice no relatório da 131-0-A).

**6.4 Precisa de HAR/F12 do Founder?** Para a parte A, **não** (nota 25 para o CORP clássico, que é tela transmitida; 72 "útil" para o
CorpNow). A API já entrega dono, renovações, itens e o PDF. Vira NECESSÁRIO (90) só se uma SPEC precisar de endossos/sinistros/"Acompanhamento"
pela tela — aí a sequência de cliques está no laudo dos prints §7.
