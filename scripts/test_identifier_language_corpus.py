#!/usr/bin/env python3
"""Contrato del CUARTO criterio: el corpus, que es abierto.

Los tres criterios anteriores son cerrados por construccion — siete sufijos,
una lista de particulas y una lista de palabras. Una lista solo atrapa lo que
alguien se acordo de enumerar, asi que la siguiente palabra se cuela: medido,
de seis identificadores espanoles escritos el 2026-09-07 el gate vio **cero**.

El caso que DISCRIMINA es el 2: esas seis palabras no estan en `SPANISH_WORDS`
ni tienen morfologia exclusiva. Un gate con solo los tres criterios cerrados
pasa el caso 1 y falla el 2.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
GATE = HERE / 'check_identifier_language.py'

#: Las seis que el gate aprobo teniendolas delante. Ninguna esta en la lista
#: cerrada — se comprueba en el caso 3, que es lo que hace honesto al caso 2.
SPANISH_MISSED = ['bien', 'mal', 'corre', 'falso', 'limpio', 'raiz']

#: Ingles de nuestro propio codigo. Su margen medido va de -6.9 a 1.6; los mas
#: altos son cognados exactos (`final`, `total`), la ceguera ya declarada.
ENGLISH_KEPT = ['root', 'run', 'clean', 'fake', 'passed', 'failed', 'marker',
                'banks', 'found', 'layer', 'check', 'gate', 'store', 'board']

passed = failed = 0


def check(label, got, want):
    global passed, failed
    if got == want:
        print(f'  OK   {label}'); passed += 1
    else:
        print(f'  FAIL {label}: {got!r} != {want!r}'); failed += 1


def run_on(source):
    """Corre el gate sobre un archivo con ese cuerpo. Devuelve (rc, salida)."""
    with tempfile.NamedTemporaryFile('w', suffix='.py', delete=False) as handle:
        handle.write(source); path = handle.name
    try:
        done = subprocess.run([sys.executable, str(GATE), path],
                              capture_output=True, text=True)
        return done.returncode, done.stdout + done.stderr
    finally:
        Path(path).unlink(missing_ok=True)


import check_identifier_language as gate  # noqa: E402

print('=== Caso 1: el corpus esta, o el gate no puede medir ===')
check('los dos lexicos cargan', gate.corpus_available(), True)

print('=== Caso 2 (EL QUE DISCRIMINA): atrapa espanol fuera de la lista ===')
vistas = [w for w in SPANISH_MISSED if gate.spanish_by_corpus(w)]
check('las seis se ven', sorted(vistas), sorted(SPANISH_MISSED))

print('=== Caso 3: y ninguna de las seis estaba en la lista cerrada ===')
check('la lista no las tenia',
      [w for w in SPANISH_MISSED if w in gate.SPANISH_WORDS], [])

print('=== Caso 4: no marca ingles de nuestro codigo ===')
falsos = [w for w in ENGLISH_KEPT if gate.spanish_by_corpus(w)]
check('cero falsos positivos', falsos, [])

print('=== Caso 5: el veredicto llega al gate entero ===')
rc, salida = run_on('def bien():\n    limpio = 1\n    return limpio\n')
check('rechaza el archivo', rc, 1)
check('nombra la palabra', 'bien' in salida, True)

print('=== Caso 6: un archivo en ingles pasa ===')
rc, _ = run_on('def passed():\n    clean = 1\n    return clean\n')
check('acepta el archivo', rc, 0)

print()
print(f'{passed} ok, {failed} fallos (alcance medido: {passed + failed} aserciones '
      f'sobre {GATE})')
raise SystemExit(1 if failed else 0)
