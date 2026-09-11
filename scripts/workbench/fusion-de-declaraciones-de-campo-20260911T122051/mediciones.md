# Fusión de declaraciones de campo — el mecanismo `_base_fields__` de la fuente

<!-- ultima medicion anadida: 2026-09-11T12:45:33 -->

> Última medición registrada: 2026-09-11T12:39:07.

Banco abierto 2026-09-11T12:21:43. Pregunta: qué hace la referencia cuando **dos clases de
definición del mismo modelo declaran el mismo campo**, y qué hace nuestro árbol
ante la misma forma.

El disparador es una declaración REAL del addon que se está portando (#332):

```python
# odoo19c: odoo/addons/test_orm/models/test_orm.py:28 — TestOrmCategory
display_name = fields.Char(
    inverse='_inverse_display_name',
    recursive=True,
)
```

Ni `compute=` ni `store=`. El `compute` sale de `BaseModel.display_name`
(`odoo19c: odoo/orm/models.py:473`), y llega por la fusión.

## M1 — el universo de los dos parámetros, por AST

El grep por línea **no sirve** y por eso se descarta: las dos declaraciones de
`display_name` que llevan `inverse=` lo llevan en la SEGUNDA línea de la
llamada. Medir el significante (la línea de la declaración) y concluir sobre el
significado (la llamada) es el sub-patrón A.

| Instrumento | `inverse=` | `recursive=` |
|---|---|---|
| `grep -n` por línea | 94 | 21 |
| recorrido AST de `ast.Call` | **273** | **42** |

El grep subcuenta **2.9×** y **2.0×**. Reparto por tipo de campo: `inverse`
sale en 18 tipos (Char 68 · Many2one 50 · Boolean 35 · Float 24 · Selection 20 ·
Many2many 15 · One2many 14 · Monetary 12 · …), `recursive` en 9 (Many2one 13 ·
Char 12 · Boolean 4 · Float 4 · …).

**Ninguno de los dos es una necesidad acotada**: son infraestructura del
vocabulario de campo, no un caso del addon que se porta.

Comando: `census_inverse_recursive.py`.

### M1-bis — `display_name` redeclarado como campo

**10** declaraciones en Python (el grep inicial dio 31 porque contaba archivos
`.js` de mock: `hr/static/tests/…`, `web/static/tests/…`,
`spreadsheet/static/tests/…`). De las 10, **4** llevan `inverse=` o
`recursive=`:

| Archivo | Clase | Parámetros declarados |
|---|---|---|
| `addons/project/models/project_task.py:315` | `ProjectTask` | `help`, **`inverse`** |
| `odoo/addons/test_orm/models/test_orm.py:28` | `TestOrmCategory` | **`inverse`**, **`recursive`** |
| `odoo/addons/test_orm/models/test_orm.py:758` | `TestOrmRecursive` | **`recursive`**, `store` |
| `odoo/addons/test_orm/models/test_orm.py:797` | `TestOrmRecursiveTree` | **`recursive`**, `store` |

Las otras 6 declaran `compute` · `help` · `compute_sudo` · `string` ·
`store` ×2.

## M2 — el enrutador nuestro, medido en proceso

```
fields.Char()                                -> CharField    inverse=None recursive=False
fields.Char(store=False)                     -> NonStored    inverse=None recursive=False
fields.Char(inverse='_x')                    -> CharField    inverse=None recursive=False
fields.Char(recursive=True)                  -> CharField    inverse=None recursive=False
fields.Char(inverse='_x', recursive=True)    -> CharField    inverse=None recursive=False
fields.Char(compute='_c')                    -> NonStored    inverse=None recursive=False
fields.Char(recursive=True, store=True)      -> CharField    inverse=None recursive=False
fields.Char(related='a.b')                   -> NonStored    inverse=None recursive=False
```

**`inverse=` solo NO enruta a `NonStored`. Y eso es FIEL**, no un defecto —
medido en la fuente, no supuesto. El bloque `attrs` de
`odoo19c: odoo/orm/fields.py:443-459` sólo escribe `store` bajo
`if attrs.get('compute')` y `if attrs.get('related')`. `inverse` aparece
**una sola vez** en ese bloque, y no para decidir columna sino `readonly`:

```python
attrs['readonly'] = attrs.get('readonly', not attrs.get('inverse'))   # :451
```

Nuestro puerto ya lleva esa línea (`src/orm/fields_nonstored.py:370`).

Comando: `probe_router.py`.

## M3 — dónde se pierde el valor, exactamente

```
apply_source_defaults SI los devuelve:
  store=False, inverse='_x'     attrs.inverse='_x'  store=False
  store=False, recursive=True   attrs.recursive=True store=False
  compute='_c', inverse='_x'    attrs.inverse='_x'  store=False
  related='a.b', inverse='_x'   attrs.inverse='_x'  store=False

pero el CAMPO construido:
  Char(store=False, inverse='_x')    -> NonStored  inverse=None   <-- PERDIDO
  Char(store=False, recursive=True)  -> NonStored  recursive=False <-- PERDIDO
  Char(compute='_c', inverse='_x')   -> NonStored  inverse='_x'   <-- llega
  Char(related='a.b', inverse='_x')  -> NonStored  inverse='_x'   <-- llega

vars(NonStored(inverse='_x', recursive=True)) =
  ['compute','default','help_text','name','related','search','verbose_name']
```

Dos puntos de pérdida, y el vocabulario **ya estaba portado**:

1. `_declared_source_vocabulary` **sí** extrae los dos
   (`fields_nonstored.py:342-343`) y `apply_source_defaults` **sí** los
   devuelve en `attrs` (`:378-380`).
2. La **salida temprana** de `annotate_related` —
   `if not related and not attrs.get('compute'): return field` — los tira
   cuando la declaración es `store=False` a secas.
3. `NonStored.__init__` los traga en `**_ignored`: no quedan en
   `__dict__` por ninguna vía que no sea el `setattr` de
   `annotate_related`.

Comando: `probe_drop_point.py`.

## M4 — el defecto GRANDE: nuestro árbol crea una columna que la fuente no crea

Forma exacta de `TestOrmCategory`: base abstracta con
`Char(compute=…, store=False)`, subclase que redeclara con
`Char(inverse=…, recursive=True)`.

```
el atributo de clase de la subclase : FieldDescriptor
  compute  = <AUSENTE>
  inverse  = <AUSENTE>
  recursive= <AUSENTE>

lo que el registro por MRO devuelve:
  tipo     = NonStored
  compute  = _compute_label
  inverse  = None

¿la subclase creo COLUMNA para label? True
base declara NonStored? True
```

El nombre queda **partido en dos objetos**: una **columna real** en
`_meta.get_fields()` que la fuente nunca crea, y la entrada `NonStored` de
la base que el registro por MRO sigue devolviendo — con el `compute` de la
base y **sin** el `inverse` de la redeclaración.

**Y el gate se queda verde.** `scripts/check_display_name.py::not_a_field`
exige que `display_name` sea `NonStored` en **alguna** clase del MRO; la
base lo es, así que pasa con la columna espuria delante. Sub-patrón D: el verde
no distingue «el puerto es correcto» de «el instrumento mira el tipo, no el
objeto que gana».

Comando: `probe_merge_today.py`.

## M5 — cómo fusiona la fuente, verbatim

`odoo19c: odoo/orm/fields.py:414-432` (`_get_attrs`):

```python
attrs = {}
modules = []
for field in self._args__.get('_base_fields__', ()):
    if not isinstance(self, type(field)):
        # 'self' overrides 'field' and their types are not compatible;
        # so we ignore all the parameters collected so far
        attrs.clear()
        modules.clear()
        continue
    attrs.update(field._args__)
    if field._module:
        modules.append(field._module)
attrs.update(self._args__)
```

Acumular los `_args__` de cada declaración en orden de override, con un
**reinicio por incompatibilidad de tipo**, y superponer al final los propios.

El sitio donde se arma, `odoo19c: odoo/orm/model_classes.py:409-415`:

```python
if len(fields_) == 1 and fields_[0]._direct and fields_[0].model_name == model_cls._name:
    model_cls._fields__[name] = fields_[0]
else:
    Field = type(fields_[-1])
    add_field(model_cls, name, Field(_base_fields__=tuple(fields_)))
```

Una **instancia nueva**, del tipo de la **última** declaración, construida con
toda la cadena. Y el contrato del atributo, `:266`:

```python
_base_fields__: tuple[Self, ...] = ()  # the fields defining self, in override order
```

## La divergencia, en una línea

| | fuente | nuestro árbol hoy |
|---|---|---|
| redeclaración | acumula `_args__` de la cadena y superpone los propios | **último gana**: `non_stored_fields` hace `found[name] = held` recorriendo `reversed(__mro__)` |
| objeto resultante | UNA instancia del tipo de la última | **DOS**: columna de Django en la subclase + `NonStored` de la base en el registro |
| sitio | ensamblado de la clase de registro | no existe — Django arma una clase por modelo desde el MRO |

*Métrica:* el tipo y los atributos del objeto que queda en `vars(cls)`, el que
devuelve `non_stored_fields`, y la presencia del nombre en
`_meta.get_fields()`, sobre modelos desechables construidos bajo
`django.setup()` completo.
*Ciega a:* el reinicio por incompatibilidad de tipo de `:419-423` —no se ha
ejercitado una redeclaración que cambie el tipo de campo—; y a los consumidores
de `recursive` (`fields.py:3508-3511`, `:4157`, `models.py:3361`), que
existen y no se han medido con un campo que lo declare de verdad.

---

## M6 — ¿cuántas redeclaraciones vivas hay en el árbol? (corregida)

`probe_tree_redeclarations.py` sobre `apps.get_models()` bajo `django.setup()`:

```
modelos medidos: 399
stored sobre NonStored (el defecto de M4): 1
    test_orm.TestOrmCategory display_name DisplayNameMixin
NonStored sobre stored: 0
por nombre: {'display_name': 1}
```

**El guion tenía un defecto de precedencia y se corrigió antes de citarlo.**
`stored_in_bases` llevaba `meta is None or getattr(meta,'abstract',False) is
False and base is cls`; `base is cls` es **inalcanzable** en un recorrido sobre
`__mro__[1:]`, así que por precedencia la condición se reducía a `meta is
None`. Corregido a lo que de verdad mide, la cifra **no cambia**: 399 y 1. Se
registra porque un instrumento cuya condición no dice lo que hace no sirve como
evidencia aunque acierte.

Cruzado con las migraciones: `grep -rn "display_name" src/**/migrations/` da
**0**, y `test_orm` no tiene directorio `migrations/`. El defecto **no está
codificado en ninguna parte**: es infraestructura prospectiva más un caso vivo
del addon en vuelo.

*Métrica:* nombres declarados como campo con columna en `cls` que una base del
MRO declara como `NonStored`, y el recíproco, sobre los 399 modelos
registrados.
*Ciega a:* NonStored-sobre-NonStored y stored-sobre-stored (herencia abstracta
de Django, último gana), que no se midieron; y a un descriptor colgado con
`setattr` pelado después del arranque.

## M7 — qué diccionario guarda hoy `_args__`, en las dos ramas

`probe_args_is_post_translation.py`:

```
Char(inverse='_x', recursive=True)  [rama con columna]
    tipo      : CharField
    _args__   : {}
    .inverse  : None
    .recursive: False
    .store    : True

Char('Label', store=False, inverse='_x')  [rama sin columna]
    tipo      : NonStored
    _args__   : None (atributo presente, sin valor)
    .inverse  : None
    .recursive: False
    .store    : False

NonStored(default=None, search='_s')  [declaracion directa]
    tipo      : NonStored
    _args__   : None (atributo presente, sin valor)
```

El docstring de `_field_get_attrs` dice *"Recibe lo declarado en `_args__`"*.
**Hoy es falso en las dos ramas**, y el flujo leído lo explica sin conjetura:

1. `Char()` traduce `required`→`blank`, `help`→`help_text`, `size`→`max_length`;
2. `apply_source_defaults` llama a `_declared_source_vocabulary`, que **saca de
   `kwargs`** `compute`, `inverse`, `recursive`, `precompute`, `compute_sudo`,
   `related_sudo`, `readonly`, `store` (y `copy` condicional);
3. `models.CharField(*args, **kwargs)` — el envoltorio anota `_args__` de lo que
   **queda**, que ya no tiene el vocabulario de la fuente;
4. `annotate_related` **sale temprano** con `not related and not
   attrs.get('compute')`, así que `inverse` y `recursive` no se anotan tampoco.

El `_args__ = None` de `NonStored` no es una ausencia: es el default de clase
que instala el segundo bucle de `_FIELD_CLASS_ATTRIBUTES` (`fields.py:1969`)
sobre esa clase. `NonStored.__init__` nunca lo asigna.

*Métrica:* las claves de `_args__` y los tres atributos del vocabulario de la
fuente sobre un campo construido por la fachada, en sus tres formas.
*Ciega a:* un campo construido sin pasar por la fachada, y a las otras ocho
fachadas (se midió `Char`).

## M8a — el ORDEN de la fuente: fusión ANTES, bloques DESPUÉS

`odoo19c: odoo/orm/fields.py:414-465`, verbatim:

```python
def _get_attrs(self, model_class, name):
    attrs = {}
    for field in self._args__.get('_base_fields__', ()):   # :419
        if not isinstance(self, type(field)):
            attrs.clear(); modules.clear(); continue        # :423
        attrs.update(field._args__)                         # :426
    attrs.update(self._args__)                              # :429
    ...
    if attrs.get('compute'):    ...                          # :443
    if attrs.get('related'):    ...                          # :452
    if attrs.get('precompute'): ...                          # :459
```

**La fusión ocurre en `:419-429` y los bloques `attrs` en `:443-465`.** Nuestro
árbol invierte el orden: los tres bloques corren en la **fachada**
(`apply_source_defaults`), antes de que ninguna fusión sea posible, porque la
fachada sólo ve la declaración de UNA clase.

Consecuencia medible: una subclase que declare `compute=` sobre una base que
declaró `store=True` se resuelve aquí con el diccionario de la subclase sola;
allá, con el acumulado.

*Métrica:* el orden de las sentencias en el cuerpo de `_get_attrs` de la
referencia.
*Ciega a:* si algún consumidor de la referencia depende de ese orden — se leyó
el cuerpo, no se ejercitó.

## M8b — de dónde sale el `_args__` de `NonStored`

`src/orm/fields.py:1948` instala `_FIELD_CLASS_ATTRIBUTES` sobre
`models.Field`; **`:1969` repite el bucle sobre `NonStored`**, con `store` como
única excepción. `_args__: None` es una de sus 66 entradas (`:1901`). Por eso el
atributo existe con valor `None` en un objeto que nunca lo asigna.

## M9 — la fusión NO está muerta: corre y se le da el diccionario equivocado

`probe_merge_is_reached.py` espía `models.Field._get_attrs` durante un cuerpo de
clase:

```
llamadas a _get_attrs durante el cuerpo de clase: 2
  campo 'label'
    _args__ de entrada : {'max_length': 8}
    attrs de salida    : {'max_length': 8, 'model_name': '', 'name': 'label',
                          '_module': None, '_modules': ()}
  campo 'id'
    _args__ de entrada : {'verbose_name': 'ID', 'primary_key': True, ...}

estado final del campo construido:
    .inverse       : None
    .recursive     : False
    .string        : None
    ._extra_keys__ : ()
```

Declarar `_get_attrs` "código muerto" habría sido concluir sobre el significado
leyendo el significante. **Se ejecuta en cada campo de cada clase**; la cadena
`contribute_to_class` → `_setup_attrs__` → `_get_attrs` → `__dict__.update` ya
está cableada entera. Lo que falta no es la costura: es que `_args__` lleve el
vocabulario de la fuente y que **alguien pase `_base_fields__`** —
`grep -rn "_base_fields__=" src/` da **0**.

El campo declarado con `'Label'` sale con `.string = None`: la fuente lo fuerza
en `:317` (`kwargs['string'] = string`) y aquí el posicional va a
`verbose_name` de Django sin que nadie lo espeje.

*Métrica:* número de invocaciones de `_get_attrs`, su `_args__` de entrada y su
`attrs` de salida, durante la ejecución del cuerpo de una clase de modelo.
*Ciega a:* lo que ocurre en `add_to_class` de una extensión `_inherit`, que no
se ejerció aquí.

## M10a — cuántas declaraciones de `NonStored` esquivan la fachada, y qué declara la fuente para ellas

Comando y salida:

```
$ grep -rn "= NonStored(" src/ --include=*.py
src/orm/fields_misc.py:54:              field = NonStored(*args, **kwargs)
src/orm/fields_numeric.py:73:           field = NonStored(*args, **kwargs)
src/orm/fields_textual.py:233:          campo = NonStored(*args, **kwargs)
src/orm/fields_company_dependent.py:482:  field = NonStored(*args, related=related, **kwargs)
src/orm/models.py:2942:                 display_name = NonStored(default=..., search=...)
src/addons/base/models/res_groups.py:177: full_name = NonStored(default=..., search=...)
```

**Seis, y la partición importa: cuatro de las seis son la rama de construcción
DE LA PROPIA FACHADA** —el `else` que elige `NonStored` cuando `store` sale
falso—, no declaraciones de modelo. Las declaraciones **facade-less reales son
DOS**, y la fuente declara las dos **con la fachada**:

| nuestro | fuente | cómo la declara la fuente |
|---|---|---|
| `src/orm/models.py:2942` `display_name` | `odoo19c: odoo/orm/models.py:473` | `display_name = Char(string='Display Name', compute=..., search=...)` |
| `src/addons/base/models/res_groups.py:177` `full_name` | `odoo19c: odoo/addons/base/models/res_groups.py:30` | `full_name = fields.Char(compute='_compute_full_name', string='Group Name', search='_search_full_name')` |

*Métrica:* ocurrencias del literal `= NonStored(` bajo `src/`, cruzadas con la
declaración verbatim de la fuente para cada nombre de campo.
*Ciega a:* una construcción de `NonStored` que no use ese literal —una llamada
indirecta, un `getattr`— y a las declaraciones de `addons/` fuera de `src/`.

**Consecuencia para la premisa que estaba en juego:** la condicional del
encargo —«si `DisplayNameMixin` es la única declaración directa»— es **falsa**:
son dos. La regla inventada «sin fachada ⇒ compatible con cualquiera» se retira
igual, pero el arreglo toca dos sitios, no uno.

## M10b — el control positivo REAL del mecanismo de fusión, en el repo

La fuente redeclara `display_name` en `test_orm` **sin `compute` y sin
`store`** — los hereda por `_base_fields__` de `BaseModel.display_name`:

```
odoo19c: odoo/addons/test_orm/models/test_orm.py:28-31
    display_name = fields.Char(
        inverse='_inverse_display_name',
        recursive=True,
    )
```

Nuestro puerto es **byte a byte igual** (`src/addons/test_orm/models/test_orm.py:36-39`).

Lo que la fuente compone para ese campo, siguiendo `_get_attrs` (`:414-465`):

| paso | resultado |
|---|---|
| `_args__` de la subclase | `{'inverse': ..., 'recursive': True}` |
| merge con `_base_fields__` (`:426`) | `+ {'string': 'Display Name', 'compute': '_compute_display_name', 'search': '_search_display_name'}` |
| bloque `compute` (`:443-451`) | ve el `compute` heredado → deriva el campo **sin columna** |

Lo que nuestro árbol compone, medido en M9: `.store: True`, `.inverse: None`,
`.recursive: False`, `.string: None`. Es decir **un `CharField` con columna**,
y los dos parámetros declarados caen en el `**_ignored` de `NonStored.__init__`
sin aplicarse.

**El defecto no es que `attrs` salga mal: es que el OBJETO ya está elegido.** La
fachada decide `CharField` contra `NonStored` en el sitio de declaración, viendo
sólo `{inverse, recursive}`; ninguna fusión posterior puede des-construir un
`CharField` en un `NonStored`. Por eso el arreglo **no** puede ser recomputar
`attrs` dentro de `_get_attrs`: tiene que **reconstruir el campo** desde el
diccionario fusionado, por la misma fachada que lo construyó.

*Métrica:* la declaración verbatim de los dos árboles, más el estado del campo
construido que M9 midió en proceso.
*Ciega a:* si algún otro de los 399 modelos hereda un `compute` por una vía que
`__mro__` no recorra (una inyección posterior, un `contribute_to_class` de
tercero). Medido sobre `__mro__[1:]`, que es la vía que Django usa.

---

## M10c — un `NonStored` heredado NO llega por `_meta`: llega por `__mro__`

Es la trampa 3, y decide **dónde** puede vivir la costura. Sonda en proceso
bajo `django.setup()` completo: un mixin abstracto que declara
`fields.Char(store=False, …)` y una subclase concreta que lo hereda.

```
display_name en _meta: False
en vars(subclase): False
tipo por atributo:    NonStored
mro:                  ['InheritsTheMixinProbe', 'DisplayNameMixinProbe', 'Model', 'AltersData', 'object']
llega por mro:        True
```

La causa está en Django: la copia desde un padre abstracto recorre
`_meta.local_fields`, que sólo contiene **campos de Django**. Un `NonStored` no
es `models.Field`, así que no está en `local_fields` y no se copia — sobrevive
únicamente como atributo de clase en el `__mro__`.

Consecuencias para la costura, las dos:

1. **La declaración base se busca en `cls.__mro__[1:]` leyendo `vars(base)`**,
   nunca en `_meta`. Un recorrido por `_meta` vería cero y publicaría «no hay
   nada que fusionar» — el sub-patrón D con el instrumento equivocado.
2. **La subclase no tiene el nombre en `vars()`**, así que instalar el campo
   reconstruido con `setattr(cls, name, fresh)` no pisa nada: lo declara donde
   antes sólo había herencia.

*Métrica:* `_meta.get_fields()`, `vars()` por clase del `__mro__` y el tipo del
atributo resuelto, sobre un par mixin-abstracto/concreta construido en proceso.
*Ciega a:* el caso en que la base declare un campo **con columna** (un
`CharField` de verdad) — ése sí lo copia `local_fields` y toma otro camino, que
es el «stored-over-stored» que Django ya resuelve por último-gana y que queda
como sucesor sin portar a ciegas.
