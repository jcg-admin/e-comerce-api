"""La suite del inventario de la referencia.

Defiende al AGREGADOR, no al extractor: ``declared_symbols``, ``signature_of``
y ``body_class`` ya tienen su suite en el run del censo de presencia
(``orm-symbol-presence-census-20260910T175850``), y este run los importa en vez
de reescribirlos. Lo que aqui se prueba es lo que este instrumento anade — la
unidad CRUDA con su clase duenia, el desglose por clase, y que una raiz ausente
emita cero en vez de fabricar.

Todos los sujetos son REALES del arbol de la referencia. Un sujeto fabricado
confirmaria el encuadre de quien escribio el instrumento.
"""
import importlib.util
import os
import pathlib
import sys

import pytest

RUN_DIR = pathlib.Path(__file__).resolve().parents[1]
REPO = RUN_DIR.parents[2]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


inventory_module = _load(
    '_inventory_reference_orm', RUN_DIR / 'inventory_reference_orm.py')
roots = _load('_inventory_roots', REPO / 'scripts/reference_roots.py')

ORM_19C = roots.TREE_ROOTS['odoo19c'] / 'odoo' / 'orm'


@pytest.fixture(scope='module')
def orm():
    if not ORM_19C.is_dir():
        pytest.skip(f'la raiz de la referencia no esta montada: {ORM_19C}')
    return inventory_module.inventory(ORM_19C)


def _file(report, name):
    for entry in report['files']:
        if entry['name'] == name:
            return entry
    raise AssertionError(f'{name} no esta en el inventario')


def test_raw_exceeds_unique_where_a_name_repeats_across_classes(orm):
    """La unidad es la OCURRENCIA, no el nombre.

    ``fields_relational.py`` declara ``setup_nonrelated`` en cuatro clases. Un
    agregador que deduplicara por nombre —el defecto que este eje corrige—
    reportaria una sola. Es el discriminador de la suite.
    """
    entry = _file(orm, 'fields_relational.py')
    assert entry['raw'] > entry['unique']
    duenios = [clase['name'] for clase in entry['classes']
               for metodo in clase['methods']
               if metodo['name'] == 'setup_nonrelated']
    assert len(duenios) == 4, duenios
    assert len(set(duenios)) == 4, 'las cuatro son clases distintas'


def test_a_class_carries_its_own_methods(orm):
    """El desglose es POR CLASE: ``BaseModel`` declara 194 metodos."""
    entry = _file(orm, 'models.py')
    base = [clase for clase in entry['classes'] if clase['name'] == 'BaseModel']
    assert len(base) == 1
    assert len(base[0]['methods']) == 194


def test_an_absent_root_yields_zero_and_does_not_fabricate():
    """``odoo/orm`` NO existe en 18c — su ORM vive plano en ``odoo/``.

    El agregador emite cero archivos y cero simbolos. Un cero fabricado seria
    indistinguible de «medi y no hay», que es el sub-patron D.
    """
    ausente = roots.TREE_ROOTS['odoo18c'] / 'odoo' / 'orm'
    assert not ausente.is_dir(), 'la premisa del caso cambio: 18c ya trae odoo/orm'
    report = inventory_module.inventory(ausente)
    assert report['files'] == []
    assert report['totals']['files'] == 0
    assert report['totals']['symbols'] == 0
    assert report['root_exists'] is False


def test_the_signature_travels_with_the_function(orm):
    """Cada funcion lleva su firma — es el tercer eje del encargo."""
    entry = _file(orm, 'utils.py')
    parse = [f for f in entry['functions'] if f['name'] == 'parse_field_expr']
    assert len(parse) == 1
    assert parse[0]['signature']['params'] == ['field_expr']


def test_totals_are_the_sum_of_the_files(orm):
    """El total no se recuenta por su cuenta: se compone de las filas."""
    total = orm['totals']
    assert total['files'] == len(orm['files'])
    assert total['classes'] == sum(len(e['classes']) for e in orm['files'])
    assert total['module_functions'] == sum(len(e['functions']) for e in orm['files'])
    assert total['methods'] == sum(
        len(c['methods']) for e in orm['files'] for c in e['classes'])
    assert total['symbols'] == (
        total['classes'] + total['module_functions'] + total['methods'])
