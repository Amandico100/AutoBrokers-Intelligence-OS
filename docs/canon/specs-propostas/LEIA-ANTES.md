# ⚠️ Propostas — não são canon

Estes documentos foram escritos por outro modelo e **não estão validados**.
`docs/canon/specs/` significa *aprovada*; esta pasta significa *candidata*.

**Revisado em 25/08/2026** por três lentes independentes (nenhuma sabia da
outra), contra o código e o banco.

---

## 🔴 A colisão de número — conserte antes de executar qualquer uma

**O número 086 já está ocupado**, e há teste vivo defendendo isso:

```
docs/canon/specs/SPEC-085-…md:390-392
  "não existe arquivo SPEC-086* em docs/canon/specs/. O conserto vive no
   CÓDIGO … Não procure a SPEC-086 — leia o código."

backend/tests/test_o_humano_e_chamado_de_verdade.py:228
  assert "human_handoff" in corpo, "o import da SPEC-086 sumiu"
```

📊 Também em `dispatch_router.py:1439` e `handoff_watchdog.py:241`.

> **"SPEC-086" hoje quer dizer o conserto do handoff humano.** A proposta toma
> o mesmo número para *continuidade de atendimento* — `GLOSSARIO.md` e
> `CLAUDE.md` §2.3: **um termo, uma definição.**

💭 **Sugestão:** as propostas passam a **094+**, e o piloto fica com a
**SPEC-093**, já escrita em `docs/canon/specs/`.

---

## As notas, e o que fazer com cada uma

| proposta | nota | o que fazer |
|---|:---:|---|
| **086** continuidade / posse | **62** · **68** | ⏸️ **depois do piloto.** Arquitetura de posse boa; **nada nela destrava o piloto** |
| **087** route self-healing | **62** | ⏸️ 🔴 **não bloqueia.** 📊 `playbook_overlays` = 0 linhas, namespace do escritor ≠ do leitor |
| **088** central de agentes | — | não toca atendimento |
| **090** fábrica de inteligência | — | melhora, não bloqueia |
| **091** protocol factory | — | não toca atendimento |

### 🔴 O que as três lentes acharam em comum

```
zero marcas 📊/💭 em 2.707 linhas da 086      CLAUDE.md §12.1
work_effects declarada "autoridade"          📊 0 linhas, 0 chamadores, sem DDL no repo
"assumir atendimento" (owner_user_id)        📊 0 de 2.738 — nunca rodou
o robô teve 4 conversas de WhatsApp          📊 21.901 de 23.028 msgs são espelho HUMANO
Blocos F e G exigem Work Run                 📊 conversa de WhatsApp não cria um
```

⚠️ **Nenhuma delas é ruim.** Elas descrevem um sistema mais maduro do que o
medido — e o piloto é o que vai produzir o dado que falta para calibrá-las.

---

## O que o piloto precisa está na `SPEC-093`

`docs/canon/specs/SPEC-093-o-piloto-o-atendimento-real-com-duas-pessoas-olhando.md`

```
E  🧑 a decisão do finalize        registro, não código
A  o papel `attendant`             só o botão, não a configuração
B  a allowlist                     ⚠️ e o alerta do Sentinela, que depende dela
C  🔴 o travamento vira evidência   e o clique da Regina deixa de virar "o robô"
D  a saudação do religamento       corte de 24h, pelo caminho que já tem limitador
F  a prova
```
