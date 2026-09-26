# SPEC-117 · ANEXO — a bateria e a triagem NOMINAL, teste a teste

> 26/09/2026 · branch `spec/117-apolice-persistente` · o relatório é `SPEC-117-EXECUTION-REPORT.md` §8
> 📊 medido (data, fonte, comando) · 💭 ilustrativo, nunca citável como fato — CLAUDE.md §12.1

## A bateria, a triagem e o vermelho que a contagem escondia

📊 **A bateria inteira rodou UMA vez, depois do conserto único** (protocolo §5 ⑦ · §10):

```
cd backend && python -m pytest tests -q
→ 47 failed · 1566 passed · 1 skipped · 36 xfailed · 1 xpassed  em 3524.48 s (58 min 44 s)
```

📊 Linha de base (`docs/canon/reports/BATERIA-LINHA-DE-BASE.txt`, 24/09): **35** FAILED. Comparação **nominal, teste a
teste**, contra a base **e contra o commit base `79c9e80` num worktree separado** — não por contagem:

| grupo | n | o que é |
|---|---|---|
| **da base** | 33 | as 35 da base menos 2 que saíram da lista (ver abaixo — e **não** era ganho) |
| **pré-existentes fora da base** | 10 | `test_098_builder_a_unit` · `test_o_fio_do_modelo` · `spec116_f2_adaptadores` (2) · `spec116_f2_historico` (2) · `spec116_f3b_plataforma` (2) · `test_o_espelho_nao_le_o_proprio_eco` · `test_spec040_onda4_gate_council`. 📊 **Todas falham igual em `79c9e80`** — território do Model Router (SPEC-116) e encoding de terminal, zero contato com `policy_context`/`attendance_ficha` |
| **de ordem/ambiente** | 2 | `test_a_arvore_ficou_limpa_no_fim` e `…[test_o_corredor_da_porto_responde_a_ura_dela]` — 📊 **passam ISOLADAS** |
| **já consertada** | 1 | `test_o_protocolo_tem_policia` — faltava neste relatório a contagem da bateria e a nota. 📊 Agora: `1 passed` |
| 🔴 **DA SPEC-117** | 1 | `…[test_o_atendimento_tem_memoria]` — ver §8.1 |

### 🔴 §8.1 · As duas falhas que "sumiram" NÃO eram ganho — eram regressão escondida

**FATO.** Eu li a saída da bateria e, vendo dois testes da base desaparecerem da lista, registrei isso como ganho. **Era o
contrário**, e só a comparação nominal contra o commit base mostrou:

📊 `test_spec016_1_answer_quality`: base `EXIT=0 · 51/0` → HEAD `EXIT=1 · 50/3`.
📊 `test_spec016_policy_intelligence`: base `EXIT=0 · 92/0` → HEAD `EXIT=1 · 91/1`.

Os dois estão em `QUARENTENA` como `xfail(strict=True)` em `test_todos_os_guardas_script_rodam.py`. Com `strict`,
**script verde vira `FAILED` (xpass)** e **script vermelho vira `xfailed`, que não aparece na lista de falhas**. Eles
estavam na linha de base **porque passavam**; ao ficarem vermelhos, saíram da lista — e a bateria **pareceu melhorar
onde piorou**. 🔴 É o CLAUDE.md §9.3 ao contrário: a quarentena virou o lugar onde a regressão se esconde. Registrado
como pendência **P-S117-12**, com o tamanho medido: 📊 **32** entradas em quarentena são vermelhos reais invisíveis.

**A causa das 4 asserções vermelhas era um erro meu de conceito, no conserto do B5:**

```
"esta apólice É VIGENTE"     afirmação sobre COBERTURA  → exige fim de vigência CONHECIDO
"esta é a apólice DO CASO"   qual contrato se trata     → OUTRA pergunta, outra régua
```

O B5 apertou `vigente` — correto, para o agente nunca afirmar cobertura que não sabe — mas a mesma régua governava a
**seleção**. Resultado: quando o sistema de gestão **aponta** a apólice e não manda as datas (é o formato
`_sanitize_match`, P-S117-11), o produto voltava a **perder a apólice do caso** — o defeito que esta SPEC existe para
consertar, entrando por outra porta.

**O conserto** (`policy_context.py:399-458`, com a distinção escrita ao lado): `_selecionavel` = **não cancelada e não
expirada**; `_vigencia_afirmada` (nova) = `vigente is True`, e é ela que governa a escolha automática por *"única
vigente"* — 🔴 sem data o produto **não escolhe sozinho**, só aceita a que a fonte apontou. `apolices_vigentes` ficou
**intacta** (é sobre cobertura). `escolher_apolice` continua levantando em vencida e cancelada.

🔴 **E o conserto reabria um achado do red team — fechado no mesmo commit.** Com vigência desconhecida, o bloco do
prompt diria *"é ELA que vale"* calado sobre a vigência (era o R7). `attendance_ficha.py:772-782` passa a escrever
**"vigência não informada pelo sistema — não afirme que está vigente"**, com guarda novo e **linha de controle** (com o
fim presente, a frase **não** aparece).

📊 **Depois deste conserto** (`b5bebf5`):

```
test_o_atendimento_tem_memoria ....  EXIT=1 (34 ok + ModuleNotFoundError) → EXIT=0 · 39 asserções
test_spec016_1_answer_quality .....  EXIT=1 · 50/3 → EXIT=0 · 53/0
test_spec016_policy_intelligence ..  EXIT=1 · 91/1 → EXIT=0 · 92/0
gates da SPEC-117 .................  81 → 82 passed  (o guarda novo do R7)
bancada da SPEC-116 ...............  73 passed (intacto)
runner dos guardas-script .........  12 failed / 299 passed → 10 failed / 301 passed
```

📊 **As 2 mutações deste conserto, nos arquivos reais**, restauradas por cópia: `_selecionavel` voltando a
`vigente is True` → os dois guardas do SPEC-016 **VERMELHOS** (50/3 e 91/1) + 3 no pytest; `_selecionavel` aceitando
**vencida** → **4 VERMELHOS**, incluindo o de "vencida nunca" e o do B6.

### ⚠️ O limite honesto desta seção

🔴 **A recontagem completa da bateria NÃO foi refeita depois do commit `b5bebf5`.** A bateria inteira rodou uma vez,
antes dele (`47 failed / 1566 passed`), e o conserto posterior foi medido **nominalmente na área que ele toca**: os três
guardas-script alvo, os gates da SPEC, a bancada e o **runner completo dos guardas-script** (que melhorou de 12 para 10
falhas). 💭 Pela aritmética da triagem a bateria deveria cair para ~44 falhas, mas **isso é inferência, não medição** —
e não vai para o relatório como número medido. A próxima SPEC regrava a linha de base com a contagem dela.

📊 **O que a SPEC melhorou na suíte:** `test_infocap_policy_output_guard` saiu da lista por **conserto** (14/0, pela
fatia F2, commit `ead9b50`), e **4** entradas saíram da `QUARENTENA` com veredito escrito — 2 porque esta SPEC consertou
o defeito de produto, 1 porque consertou o guarda, 1 (comercial) porque `strict` obriga, com a ressalva escrita de que o
verde dela é parcial ("ponta a ponta PULADO").
