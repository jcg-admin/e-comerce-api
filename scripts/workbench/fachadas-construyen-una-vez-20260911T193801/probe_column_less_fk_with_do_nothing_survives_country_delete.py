"""Sonda M de TASK-API-0417 — forzando ``DO_NOTHING``, ¿sobrevive el borrado del
país?

Par de control de :ref:`h-api-1110` y bloqueante de TASK-API-0412. La sonda K
midió que el campo relacional sin columna que el arreglo va a declarar nace con
política ``SET_NULL``, y que el recolector de ``delete()`` sólo salta
``DO_NOTHING``. Una FK sin columna que el recolector SÍ recorre hace que el
compilador arme un ``Col`` con ``column=None`` y reviente
(``compiler.py:30 quote_name_unless_alias``).

Las dos sondas son el mismo cuerpo con una sola línea de diferencia: la política
del campo. Discrimina por construcción — si las dos dieran el mismo resultado, la
política no sería la causa y el arreglo propuesto no serviría.

Se mide por contenido: se borra un país RECIÉN creado, con la compañía ya
declarando el campo hacia él, y se reporta el reventón o su ausencia.
"""
import os
import traceback

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.testing')
django.setup()

import fields  # noqa: E402,F401
from django.db import connection, models  # noqa: E402
from orm.fields_relational import Many2one  # noqa: E402
from orm.model_classes import ensure_field_setup, mark_model_for_setup  # noqa: E402

from addons.base.models.res_company import ResCompany  # noqa: E402
from addons.base.models.res_country import ResCountry  # noqa: E402


def _compute_address(self):
    """≙ ``_compute_address`` — la dirección la pone el partner."""
    self.country = getattr(self.partner, 'country', None)


def _inverse_country(self):
    """≙ ``_inverse_country`` — escribir en la compañía escribe el partner."""
    self.partner.country = self.country
    self.partner.save()


ResCompany._compute_address = _compute_address
ResCompany._inverse_country = _inverse_country

country_field = Many2one(ResCountry, compute='_compute_address',
                         inverse='_inverse_country', null=True)
#: LA MUTACIÓN: se fuerza ``DO_NOTHING``, que es lo único que el recolector salta
#: (``deletion.py``: ``if related.field.remote_field.on_delete is DO_NOTHING:
#: continue``). Es lo que ``fields_relational.py:913`` ya hace para el otro campo
#: sin columna del árbol — el ``related=`` sin ``to``.
country_field.remote_field.on_delete = models.DO_NOTHING
country_field.contribute_to_class(ResCompany, 'country')
mark_model_for_setup(ResCompany)
setup_count = ensure_field_setup()

policy = getattr(country_field.remote_field.on_delete, '__name__', None)

#: Código PROPIO de esta sonda y limpieza por SQL crudo: las dos sondas del par
#: corren a la vez en el pool contra la MISMA base, y con el mismo código la
#: segunda moría en la clave única antes de medir nada
#: (``scripts/evidence/politica-2026-09-12T08-11-44-003.log``). El SQL crudo
#: además esquiva el recolector, que es justo lo que está roto.
CODE = 'Z2'


def _purge():
    with connection.cursor() as cursor:
        cursor.execute('DELETE FROM res_country WHERE code = %s', [CODE])


_purge()
delete_error = delete_frame = None
country = None
try:
    country = ResCountry.objects.create(code=CODE, name='Probe Ondelete')
    ResCountry.objects.filter(pk=country.pk).delete()
    country = None
except Exception as exc:  # noqa: BLE001 — el reventón ES lo que se mide
    delete_error = f'EXC {type(exc).__name__}: {exc}'
    frames = traceback.extract_tb(exc.__traceback__)
    delete_frame = ' | '.join(f'{f.filename.split("/")[-1]}:{f.lineno} {f.name}'
                              for f in frames[-3:])
finally:
    try:
        _purge()
    except Exception as exc:  # noqa: BLE001
        print('limpieza:', f'EXC {type(exc).__name__}: {exc}')

survives = delete_error is None
expected = {
    'setup_ran':          setup_count > 0,
    'no_column':          getattr(country_field, 'column', 'sentinel') is None,
    'delete_survives_matches_the_policy': survives is True,
}
for key, ok in expected.items():
    print(f"{key}: {'OK' if ok else 'FALLA'}")
print("setup_count:", setup_count, "| politica del campo:", policy)
print("esperado que sobreviva:", True, "| sobrevivio:", survives)
print("borrado del pais:", delete_error or 'sin error')
print("marco del reventon:", delete_frame)
print("VEREDICTO la_politica_decide_el_reventon:",
      'OK' if all(expected.values()) else 'FALLA')
raise SystemExit(0 if all(expected.values()) else 1)
