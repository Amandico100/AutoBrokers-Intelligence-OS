"""`--verificar-mutacoes` — a mutação é EXECUTADA, nunca lida. SPEC-083 §3.6.

A v1 da SPEC dava 3 pontos por um **comentário** dizendo que a mutação ficou
vermelha. **Comentário não fica vermelho.**

O ciclo, e cada passo existe por um risco concreto:

```
1. COPIA o arquivo para um temporário
   🔴 NUNCA `git checkout` — ele apaga trabalho não commitado. E
      `git diff --quiet` NÃO VÊ arquivo untracked, então nem prova a restauração.
      (as duas coisas estão registradas na memória do projeto)
2. aplica a substituição            — recria o furo
3. roda o teste                     — EXIGE a asserção nomeada em vermelho
4. restaura da cópia                — e confere por HASH que voltou idêntico
```

🔴 **Mutação declarada que não produz vermelho vale ZERO e vira linha no
relatório.** É a diferença entre um guarda e um enfeite.
"""

from __future__ import annotations

import hashlib
import importlib.util
import io
import os
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Dict, List, NamedTuple, Tuple

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Resultado(NamedTuple):
    arquivo: str
    rotulo: str
    aplicou: bool
    ficou_vermelha: bool
    restaurado_identico: bool
    detalhe: str

    @property
    def ok(self) -> bool:
        return self.aplicou and self.ficou_vermelha and self.restaurado_identico


def _hash(caminho: str) -> str:
    with open(caminho, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _carregar_mutacoes(teste: str) -> List[Tuple[str, str, str, str]]:
    """Lê o `MUTACOES` do arquivo de teste sem executar as asserções dele."""
    sp = importlib.util.spec_from_file_location("_mut_" + os.path.basename(teste), teste)
    mod = importlib.util.module_from_spec(sp)
    saida = io.StringIO()
    real = sys.stdout
    sys.stdout = saida
    try:
        sp.loader.exec_module(mod)
    except SystemExit:
        pass
    finally:
        sys.stdout = real
    return list(getattr(mod, "MUTACOES", []))


def _rodar(teste: str) -> str:
    r = subprocess.run([sys.executable, teste], cwd=RAIZ,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=300,
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    return (r.stdout or "") + (r.stderr or "")


def _assercao_vermelha(saida: str, rotulo: str) -> bool:
    """A asserção NOMEADA caiu?

    🔴 Não basta *"o teste ficou vermelho"* — qualquer erro de sintaxe faria isso.
    O que se exige é que **aquela** asserção caia, e é isso que liga a mutação ao
    guarda que ela testa.
    """
    alvo = rotulo.strip()
    for linha in saida.splitlines():
        l = linha.strip()
        if not (l.startswith("FALHA") or l.startswith("[FALHOU]") or l.startswith("FALHOU")):
            continue
        if alvo in l or alvo.lstrip("🔴 ").strip() in l:
            return True
    return False



# ═════════════════════════════════════════════════════════════════════════════
# 🔴 A TRAVA — MEDIR UMA ROTA **ESCREVE** NO ARQUIVO DO CORREDOR
# ═════════════════════════════════════════════════════════════════════════════
#
# `medir_rota.py` chama `verificar()` em TODA medição, e cada mutação grava em
# `app/services/corridor_playbooks.py` e restaura. Uma medição sozinha é segura:
# copia, muta, roda, devolve, confere o hash.
#
# 🔴 **Duas ao mesmo tempo não são.** Em 22/08/2026, quatro subagentes mediram
#    rotas em paralelo enquanto a sessão principal media outra. As restaurações
#    correram umas por cima das outras e o corredor ficou com a mutação do
#    FURO 1 aplicada:
#
#        - "anchor": r"(?:informe|confirme) o n[úu]mero da resid[êe]ncia"
#        + "anchor": r"informe o n[úu]mero da resid[êe]ncia"
#
#    ⚠️ E `confirme` é justamente a redação que a URA usa — a mutação existe
#    para provar isso. O produto ficou com a âncora MORTA, e a única razão de
#    ter sido pego foi um `git status` de rotina.
#
# 📊 E um dos subagentes viu o sintoma sem saber a causa: *"esta listagem
#    mostra 5 telas órfãs, mas a chamada anterior mostrou 3"*. Medição que
#    muda de resposta entre duas chamadas não é ruído: é a árvore se movendo
#    debaixo de quem mede.
#
# ⚠️ A trava é de ARQUIVO, e não de processo, de propósito: os concorrentes são
#    processos Python separados (subagente, sessão, script de CI), e um
#    `threading.Lock` não os enxergaria.
_TRAVA = os.path.join(RAIZ, ".baseline", ".mutacao.lock")
_ESPERA_MAX = 900.0        # 15 min: uma rodada completa das 6 mutações cabe
_TRAVA_VELHA = 1800.0      # 30 min sem tocar = o dono morreu, a trava é lixo


class MutadorOcupado(RuntimeError):
    """Outra medição está com o corredor mutado. Esperar é obrigatório."""


def _tomar_a_trava(espera: float = _ESPERA_MAX) -> int:
    os.makedirs(os.path.dirname(_TRAVA), exist_ok=True)
    inicio = time.monotonic()
    while True:
        try:
            fd = os.open(_TRAVA, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            return fd
        except FileExistsError:
            # ⚠️ Trava órfã: um processo morto no meio deixaria todo mundo
            #    esperando para sempre, e a cura seria pior — alguém apagaria
            #    a trava "para destravar" e o problema voltaria calado.
            try:
                idade = time.time() - os.path.getmtime(_TRAVA)
                if idade > _TRAVA_VELHA:
                    os.unlink(_TRAVA)
                    continue
            except FileNotFoundError:
                continue
            if time.monotonic() - inicio > espera:
                raise MutadorOcupado(
                    f"outra medicao esta mutando o corredor ha mais de "
                    f"{espera:.0f}s (trava: {_TRAVA}). 🔴 NAO apague a trava: "
                    f"o corredor pode estar mutado neste instante.")
            time.sleep(0.5)


def _soltar_a_trava(fd: int) -> None:
    try:
        os.close(fd)
    finally:
        try:
            os.unlink(_TRAVA)
        except FileNotFoundError:
            pass


def verificar(teste: str) -> List[Resultado]:
    """Aplica cada mutação, exige o vermelho nomeado, restaura e confere o hash."""
    caminho_teste = teste if os.path.isabs(teste) else os.path.join(RAIZ, teste)
    mutacoes = _carregar_mutacoes(caminho_teste)
    fora: List[Resultado] = []

    # 🔴 Ninguém muta o corredor em paralelo. Ver o cabeçalho da trava.
    # ⚠️ `_rodar_mutacoes`, e nao `_rodar`: ja existe um `_rodar(teste)`
    #    interno que executa o arquivo de teste. Colidir com ele fez a funcao
    #    nova chamar a si mesma com o argumento errado -- e as mutacoes nao
    #    rodaram. 🔴 A assercao do hash ficou VERDE por vacuidade: o corredor
    #    saiu identico porque ninguem o tocou. Quem denunciou foi o exit code.
    _fd = _tomar_a_trava()
    try:
        return _rodar_mutacoes(caminho_teste, mutacoes)
    finally:
        _soltar_a_trava(_fd)


def _rodar_mutacoes(caminho_teste: str, mutacoes) -> List[Resultado]:
    fora: List[Resultado] = []
    for arquivo, de, para, rotulo in mutacoes:
        alvo = os.path.join(RAIZ, arquivo)
        h_antes = _hash(alvo)

        with tempfile.TemporaryDirectory() as tmp:
            copia = os.path.join(tmp, os.path.basename(alvo))
            shutil.copy2(alvo, copia)          # 1 · a CÓPIA

            with open(alvo, encoding="utf-8") as fh:
                fonte = fh.read()
            if de not in fonte:
                fora.append(Resultado(arquivo, rotulo, False, False, True,
                                      f"o texto a mutar NAO EXISTE mais no arquivo: {de[:60]!r}"))
                continue
            mutado = fonte.replace(de, para, 1)

            try:
                with open(alvo, "w", encoding="utf-8") as fh:
                    fh.write(mutado)           # 2 · aplica
                saida = _rodar(caminho_teste)  # 3 · roda
                vermelha = _assercao_vermelha(saida, rotulo)
            finally:
                shutil.copy2(copia, alvo)      # 4 · RESTAURA da cópia

        h_depois = _hash(alvo)
        identico = h_antes == h_depois
        detalhe = "" if vermelha else "a assercao nomeada NAO caiu -- a mutacao e enfeite"
        if not identico:
            detalhe += "  🔴 O ARQUIVO NAO VOLTOU IDENTICO"
        fora.append(Resultado(arquivo, rotulo, True, vermelha, identico, detalhe))
    return fora


def imprimir(res: List[Resultado]) -> str:
    L = ["=== --verificar-mutacoes ==="]
    for r in res:
        marca = "[OK]  " if r.ok else "[FALHA]"
        L.append(f"  {marca} {r.rotulo[:72]}")
        L.append(f"          aplicou={r.aplicou}  ficou_vermelha={r.ficou_vermelha}  "
                 f"restaurado_identico={r.restaurado_identico}")
        if r.detalhe:
            L.append(f"          {r.detalhe}")
    bons = sum(1 for r in res if r.ok)
    L.append(f"  -> {bons} de {len(res)} mutacoes EXECUTADAS e vermelhas")
    return "\n".join(L)


if __name__ == "__main__":
    alvo = sys.argv[1] if len(sys.argv) > 1 else "tests/test_a_regua_nao_tem_furo.py"
    r = verificar(alvo)
    print(imprimir(r))
    raise SystemExit(0 if all(x.ok for x in r) else 1)
