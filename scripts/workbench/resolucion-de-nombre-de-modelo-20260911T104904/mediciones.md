# Resolución de `_name` → modelo en una relación — mediciones

Todas de esta sesión, contra Django 6.0.5 instalado y `odoo19c`.

## M1 — el puerto NO introdujo ningún renombre
Los nombres de clase de `test_orm` de la referencia son `TestOrmCategory`,
`TestOrmDiscussion`, … verbatim (155 clases, 146 con `_name`).

## M2 — destinos relacionales en `test_orm.py` de la referencia
143 totales · 116 del mismo addon · 26 `res.*` · 1 `ir.*`.

## M3 — la referencia declara `_name` en los modelos que nuestro árbol no
`ResUsers._name = 'res.users'`, `ResPartner._name = 'res.partner'`;
los nuestros no lo declaran.

## M4 — la semilla: `fields.Many2one` devuelve un `ForeignKey` PELADO
```
tipo devuelto       : (ForeignKey, ForeignObject, RelatedField, FieldCacheMixin)
subclase de proyecto: False
contribute_to_class : django.db.models.fields.related  (no nuestro)
```
No hay `contribute_to_class` propio que interceptar: el único punto que
controlamos hoy es la función `fields.Many2one`, el mismo asiento donde vive
`_apply_ondelete`.

## M5 — dónde revienta un nombre de DOS puntos, y cuándo
`__init__` lo acepta sin tocarlo (`remote_field.model == 'test_orm.multi.line'`).
Revienta **al crear la clase**, por la vía perezosa de Django:

```
base.py:213  __new__
base.py:393  add_to_class
related.py:923 contribute_to_class
related.py:396 contribute_to_class
related.py:86  lazy_related_operation
utils.py:15/22 make_model_tuple  -> ValueError: Invalid model reference
```

`make_model_tuple` hace `app_label, model_name = model.split(".")`: un nombre
de dos puntos no cabe en su espacio de claves. **30 nombres distintos** de los
destinos de `test_orm.py` tienen dos puntos o más.

## M6 — referencias hacia ADELANTE en el mismo archivo
De los 116 destinos del mismo addon: **41 hacia adelante**, 72 hacia atrás,
3 fuera del archivo. Una sustitución en el momento de construir NO puede
resolver esas 41: la clase todavía no existe.

## M7 — el nombre de clase NO es función del `_name`
Medido sobre las **1103** clases con `_name` de `odoo19c/addons`:
**936 coinciden** con el CamelCase de su `_name` y **167 NO** (15 %).
Ejemplos: `l10n_id_efaktur_coretax.document` → `EfakturDocument`;
`l10n_latam.identification.type` → `L10n_LatamIdentificationType`;
`sale.edi.xml.ubl_bis3` → `SaleEdiXmlUbl_Bis3`.

Consecuencia: derivar el nombre de clase del `_name` con una transformación
sería una **invención**, falsa en el 15 % de los casos. La fuente nunca lo
deriva — resuelve por registro (`env[name]`).

## M8 — el espacio de claves de Django
`Apps.register_model` indexa por `model._meta.model_name` = `cls.__name__.lower()`,
bajo `all_models[app_label]`. Nuestro `base` da
`['baseenableprofilingwizard', 'checkoutattempt', …]` — nombres de clase, no
`_name`. Nuestro registro por `_name` ya existe y es `orm.registry.MODELS_BY_NAME`,
poblado por la señal `class_prepared` (`registry.py:387`).

## M9 — la relación muerta EN SILENCIO (2026-09-11T10:54:53)
Un nombre de **un solo punto** que no corresponde a ningún modelo registrado
NO levanta excepción. La clase se crea, `remote_field.model` se queda como
`str`, y `deconstruct()` emite la cadena en minúsculas:

```
clase creada sin excepcion : ProbeOneDot
remote_field.model         : 'base.companysettingXYZ'
tipo                       : str
-> operacion pendiente sobre una clave que NUNCA se registra: relacion muerta EN SILENCIO

resuelta  remote_field.model: <class 'addons.base.models.company_setting.CompanySetting'>
resuelta  deconstruct to=   : base.companysetting
NO resuelta deconstruct to= : base.companysettingxyz
```

Consecuencia para el control del resolutor (sub-patrón D de
`metrica-decide-la-conclusion.md`): un test que afirme *«no levanta
excepción»* pasaría con la relación muerta. **El control tiene que afirmar
`field.remote_field.model is <la clase>` después de `apps.populate()`**, no
la ausencia de error.

## M10 — el resolutor de Django, las dos líneas que un callback diferido reproduce
`django/db/models/fields/related.py:392-394`:

```python
def resolve_related_class(model, related, field):
    field.remote_field.model = related
    field.do_related_class(related, model)
```

y su registro en `:396-397` con `lazy_related_operation(...)`. El
`split(".")` sobre `remote_field.model` aparece además en `related.py:740` y
`:1816` — o sea que el **string con punto** es vocabulario vivo de Django en
más de un sitio, no sólo en `make_model_tuple`.

## M11 — el discriminador de vocabulario, medido
Sobre los `_name` de `odoo19c`:

```
_name medidos                      : 1472
con MAYUSCULA tras el primer punto : 0
```

Django nombra `app_label.ModelName` — segundo segmento **capitalizado**. La
fuente nombra `modulo.modelo` — segundo segmento **siempre en minúscula**, y
admite ≥2 puntos (`l10n_ar.afip.responsibility.type`). Por tanto
*«segundo segmento en minúscula, o ≥2 puntos»* separa los dos vocabularios
**sin registro**, que es exactamente lo que hace falta para una **referencia
adelantada**: ahí ni `'base.ResPartner'` ni `'test_orm.discussion'` están en
ningún registro todavía.

*Métrica:* la caja de la primera letra del segmento posterior al primer punto.
*Ciega a:* un `_name` de la fuente cuyo segundo segmento empezara con
mayúscula — 0 medidos hoy; si apareciera, el discriminador lo mandaría al
vocabulario de Django.

## M12 — dónde falla hoy un nombre de dos puntos
La traza de `test_orm.discussion.tag` (dos puntos) sube por el camino **de
Django**, no por el nuestro: `base.py:213 __new__` → `base.py:393
add_to_class` → `related.py:923` → `related.py:396 contribute_to_class` →
`related.py:86 lazy_related_operation` → `utils.py:15/22 make_model_tuple`.

Es decir: el fallo ocurre **al crear la clase**, no al construir el campo.
`Many2one.__init__` acepta la cadena intacta. Un resolutor que quiera ver
el nombre antes que `make_model_tuple` tiene que interponerse en
`contribute_to_class`, que es un método de instancia del campo.

## M13 — las tres relaciones NO están al mismo nivel
```
fields.Many2one  -> django.db.models.fields.related.ForeignKey       (desnudo)
fields.One2many  -> orm.fields_relational.One2many                   (clase propia)
fields.Many2many -> django.db.models.fields.related.ManyToManyField  (desnudo)
```

`One2many` ya es clase del proyecto; las otras dos son la clase de Django sin
envolver. Por eso el diferimiento **no puede vivir en la factoría de
`Many2one`**: al siguiente modelo con un `Many2many` hacia otro addon el
porte se vuelve a parar. El hogar tiene que cubrir las tres.

---

## M14 — la relación muerta NO es silenciosa en la creación de la base (2026-09-11T11:05:05)

M9 midió que declarar `Many2one('base.companysettingXYZ')` **no levanta
excepción** al construir la clase. Eso sigue siendo cierto y es sólo la mitad:
al crear la base de pruebas, la misma relación **aborta**.

Comando y salida (cola del traceback):

```
$ uv run pytest tests/unit/scripts/test_check_fk_naming.py -q --reuse-db \
      -k test_the_real_declaration_is_measured_as_faithful
django_db_setup -> setup_databases -> create_test_db -> migrate.handle
  -> sync_apps(connection, executor.loader.unmigrated_apps)
  -> editor.create_model -> table_sql -> column_sql
  -> related.py:1225 db_parameters -> :1115 target_field
  -> :804 foreign_related_fields -> :791 related_fields
  -> :1142/:771 resolve_related_fields
ValueError: Related model 'test_orm.category' cannot be resolved
```

**Dos hechos que esto fija, y ninguno estaba medido:**

1. **`src/addons/test_orm` YA está en `INSTALLED_APPS`.** No se declaró a
   mano: `base.py:115 LOCAL_APPS = _local_apps()` lo **deriva** del grafo de
   addons (`:83` — `('core',) + tuple(f'addons.{node.name}' for node in graph)`),
   así que basta el `__manifest__.py` para que entre. Contesta la incógnita de
   si el addon carga: carga, y sin tocar settings.
2. **Sus 153 modelos obtienen tabla por `sync_apps`**, la rama de
   *unmigrated apps* de `migrate`. Es ahí donde la FK se resuelve, y ahí donde
   el nombre punteado de la referencia no tiene destinatario en el espacio de
   claves de Django (M12).

**Consecuencia de orden, no de diseño:** el resolutor diferido deja de ser el
paso siguiente y pasa a ser el **bloqueo**. Con el addon en el árbol, la
creación de la base falla, y con ella **todo test que pida la fixture `db`** —
no sólo los del addon. Medido: los tests preexistentes de
`test_check_fk_naming.py` erroran igual que los nuevos.

*Métrica:* el traceback de `django_db_setup` en un `pytest` con `--reuse-db`
sobre la base QA caliente.
*Ciega a:* el caso en que el addon **no** esté en el árbol — ahí `sync_apps` no
ve sus 153 modelos y la relación muerta no existe; es exactamente la maniobra
de aislamiento que los controles del gate ADR-029 usaron para correr.

> **Corregida la ceguera declarada (2026-09-11T11:13:36).** Decía que el resultado podía dar
> «verde en una máquina y rojo en otra según el estado de su base». Es
> **empíricamente falso**: la corrida que produjo este traceback fue **con
> `--reuse-db` sobre la base QA ya caliente**, y falló igual. La causa es que
> `migrate` corre `sync_apps` sobre las apps sin migraciones en **cada**
> invocación y crea toda tabla ausente de `introspection.table_names()` — la
> base caliente no lo salta. El rojo es determinista en cualquier máquina con
> el addon presente.
>
> Una ceguera mal declarada es peor que ninguna: da por acotado un riesgo que
> no existe y deja sin nombrar el que sí (la ausencia del addon). Es el defecto
> que `metrica-decide-la-conclusion.md` existe para atrapar, cometido en la
> línea que lo declara.
