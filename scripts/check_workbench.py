#!/usr/bin/env python3
"""Gate del banco de trabajo — un trabajo declara donde aterriza lo que produce.

Verifica que cada directorio de ``scripts/workbench/`` lleve su
``manifest.json`` con las cinco claves que ``manifest_schema.json`` declara
obligatorias: ``question``, ``instrument``, ``metric``, ``blind_to`` y
``destination``.

Por que ESAS cinco
==================

No son ceremonia. Cada una cierra un defecto que este proyecto ya midio:

- ``question`` — un trabajo sin pregunta produce una salida que nadie sabe
  leer. Es la mitad que ``auto-audit-before-writing.md`` llama premisa.
- ``instrument`` — sin el, la cifra no se puede re-derivar y la unica forma
  de corregirla es reescribirla a mano.
- ``metric`` y ``blind_to`` — son ``metrica-decide-la-conclusion.md`` hecho
  campo obligatorio. Una cifra correcta sobre lo que no se pregunta engana
  igual que una equivocada, y el sub-patron C reincidio tres veces en la
  iniciativa de porte.
- ``destination`` — se declara ANTES de que exista lo que produce. Un trabajo
  sin destino declarado aterriza donde caiga, y ahi no lo encuentra nadie.

Nace SIN baseline
=================

Directiva del ejecutor 2026-08-30: *«ya no queremos deuda congelada»*. Un
baseline suprime hallazgos reales para que el gate no bloquee, y es la forma
de deuda que menos se ve porque el gate publica verde con ella dentro. Este
gate no lo tiene y no lo va a tener: el directorio nace vacio, asi que no hay
deuda heredada que congelar. Ver la tarea #219.

*Metrica:* presencia y forma de las cinco claves obligatorias en el
``manifest.json`` de cada subdirectorio de ``scripts/workbench/``.
*Ciega a:* si lo declarado es CIERTO — un ``metric`` que describa otra cosa
pasa igual que uno exacto. Eso lo mide quien revisa, no un gate de forma.

Uso::

    python3 scripts/check_workbench.py            # reporte
    python3 scripts/check_workbench.py --strict   # exit 1 si hay incumplidores
"""
import argparse
import json
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent

#: Los archivos del propio banco, que no son piezas de trabajo.
BENCH_FILES = {'README.md', 'manifest_schema.json'}


def thyrox_root():
    """Donde vive el proveedor — variable declarada, luego clon hermano.

    Mismo mecanismo que ``check_identifier_language.py`` ya usa en este
    directorio; no se inventa otro. Si ``THYROX_ROOT`` SE DECLARA es la UNICA
    fuente: una declarada-e-inexistente que cayera por detras al hermano
    volveria decorativa la variable.
    """
    declared = os.environ.get('THYROX_ROOT')
    if declared:
        root = pathlib.Path(declared)
        return root if (root / 'src' / 'workbench' / 'paths.py').is_file() else None
    sibling = REPO.parent / 'thyrox'
    return sibling if (sibling / 'src' / 'workbench' / 'paths.py').is_file() else None


def bench_root():
    """El hogar del banco, DECLARADO por el consumidor — no derivado.

    Hasta la tarea #247 esta raiz se componia con
    ``pathlib.Path(__file__).resolve().parent.parent / 'scripts' / 'workbench'``
    y se LIGABA en la firma de ``work_dirs``, asi que ni reasignando el modulo
    se movia. Consecuencia medida: con la raiz movida el gate publicaba
    ``0 incumplidor(es) (alcance medido: 0 pieza(s))`` y **exit 0** — el
    denominador salvaba al lector humano, el codigo de salida no discriminaba
    «no hay defectos» de «no medi nada».

    Hoy la resuelve ``thyrox: src/workbench/paths.py::workbench_dir``, que
    consulta en este orden: ``THYROX_WORKBENCH_API`` (la familia por clon) ->
    ``THYROX_WORKBENCH_DIR`` (la global) -> el default de la cadena declarada.
    En ESTE arbol la primera esta declarada en el ``.env`` de la raiz y apunta
    a ``scripts/workbench``, que es donde el banco vive de verdad — y por eso
    no se llama ``eventos``: la palabra ya nombra otras dos cosas aqui.

    ``HERE`` se pasa como punto de partida, no como aritmetica de ruta: lo que
    identifica es EL CLON al que este archivo pertenece, ascendiendo hasta
    reconocerlo por su prefijo. Eso sobrevive a que el archivo baje de nivel;
    componer el hogar de un dato sumando ``..`` no.

    Sin thyrox alcanzable NO se emite veredicto: rehusa con exit 2.
    """
    root = thyrox_root()
    if root is None:
        print('ERROR — no se encontro thyrox/src/workbench/paths.py. Declara '
              'THYROX_ROOT o clona thyrox como hermano. No se emite conteo: '
              'un 0 aqui seria un verde falso.', file=sys.stderr)
        raise SystemExit(2)
    sys.path.insert(0, str(root / 'src'))
    from workbench.paths import workbench_dir  # noqa: E402
    return workbench_dir(HERE)


def schema_of(root):
    """El esquema vive EN el banco, asi que se deriva de su raiz."""
    return root / 'manifest_schema.json'


def required_keys(schema_path=None):
    """Las obligatorias salen del esquema, no de una copia en este archivo.

    Duplicar la lista aqui crearia la segunda fuente de verdad que
    ``calibration-verified-numbers.md`` prohibe: el esquema y el gate
    divergirian y los dos seguirian dando un numero.
    """
    if schema_path is None:
        schema_path = schema_of(bench_root())
    if not schema_path.is_file():
        # Rehusa con codigo propio en vez de medir con una lista inventada:
        # un 0 sin esquema no distingue "todo cumple" de "no pude medir".
        print(f'ERROR — falta el esquema en {schema_path}. No se emite conteo: '
              'un 0 aqui seria un verde falso.', file=sys.stderr)
        raise SystemExit(2)
    return list(json.loads(schema_path.read_text())['required'])


def work_dirs(root=None):
    """Los subdirectorios que son piezas de trabajo."""
    if root is None:
        root = bench_root()
    if not root.is_dir():
        return []
    return sorted(d for d in root.iterdir()
                  if d.is_dir() and d.name not in BENCH_FILES
                  and not d.name.startswith(('.', '__')))


def offences_of(directory, keys):
    """Que le falta a esta pieza de trabajo. Lista vacia = cumple."""
    manifest = directory / 'manifest.json'
    if not manifest.is_file():
        return ['no declara manifest.json']
    try:
        declared = json.loads(manifest.read_text())
    except json.JSONDecodeError as error:
        return [f'manifest.json no es JSON valido: {error}']
    if not isinstance(declared, dict):
        return ['manifest.json no declara un objeto']

    found = []
    for key in keys:
        if key not in declared:
            found.append(f'falta la clave obligatoria {key!r}')
        elif not declared[key]:
            # Una clave presente y vacia es peor que ausente: parece
            # declarada. Es la misma forma que el verde que no discrimina.
            found.append(f'la clave {key!r} esta vacia')
    return found


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--strict', action='store_true',
                        help='exit 1 si hay piezas de trabajo incumplidoras')
    args = parser.parse_args(argv)

    root = bench_root()
    # Un banco presente y VACIO es un cero legitimo: un clon recien hecho no
    # tiene piezas todavia. Un banco que NO EXISTE es otra cosa — nadie midio
    # nada. Colapsarlos es el sub-patron D de
    # `metrica-decide-la-conclusion.md`, y era lo que este gate hacia: con la
    # raiz movida publicaba `0 incumplidor(es)` y salia 0.
    if not root.is_dir():
        print(f'ERROR — el banco declarado no existe: {root}. Declara '
              'THYROX_WORKBENCH_API (o THYROX_WORKBENCH_DIR) con el hogar '
              'real. No se emite conteo: un 0 aqui no distinguiria «ninguna '
              'pieza incumple» de «no medi nada».', file=sys.stderr)
        raise SystemExit(2)

    keys = required_keys(schema_of(root))
    directories = work_dirs(root)
    offenders = {d: found for d in directories
                 if (found := offences_of(d, keys))}

    for directory, found in offenders.items():
        print(f'  {directory.relative_to(REPO)}')
        for one in found:
            print(f'      {one}')

    print(f'check_workbench: {len(offenders)} incumplidor(es) '
          f'(alcance medido: {len(directories)} pieza(s) de trabajo; '
          f'{len(keys)} clave(s) obligatoria(s) leidas del esquema; '
          'sin baseline por directiva del ejecutor 2026-08-30)')
    if offenders and args.strict:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
