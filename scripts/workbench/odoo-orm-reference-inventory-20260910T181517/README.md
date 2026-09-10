# odoo-orm-reference-inventory

`TASK-API-0392` · `odoo-tools@abe4040ec1` · `api@cdb41aa6` · 2026-09-10T18:18:48

## El encargo

> «ya que tenemos el reporte, vamos a crear un analisis sobre lo que tiene
> ODOO_TOOLS en ORM, contando los archivos, las clases, funciones, firmas de
> funciones,»

## La premisa que se corrigio antes del primer comando

Este run **no extiende cobertura**. La lectura natural —«el censo midio lo
nuestro, ahora medimos lo suyo para ver que falta»— es falsa: el censo de
presencia (`TASK-API-0391`) ya alcanzo **los 22 archivos no-`__init__`** de
`odoo/orm`, porque cada uno tiene un archivo del mismo nombre en `src/orm`.
Los seis «sin contraparte» que aquel run reporto son archivos **nuestros**.

Lo que cambia son la **unidad** y el **desglose**, y decirlo importa porque si
no las dos cifras se leen como contradictorias:

| | censo de presencia | este inventario |
|---|---|---|
| unidad | nombre **unico** por archivo | **ocurrencia**, con su clase duenia |
| total | 792 simbolos de referencia | **954** crudos · **792** unicos |
| desglose | una fila por archivo | archivo → clases → metodos → firma |

Que el `792` coincida byte a byte es el **control cruzado**: las dos
poblaciones son la misma, y la diferencia de 162 es exactamente el homonimo
entre clases del mismo archivo.

## Las piezas

| archivo | que hace |
|---|---|
| `inventory_reference_orm.py` | el agregador: archivo → clases → metodos, con firma y conteo crudo contra unico |
| `probes/probe_orm_across_trees.py` | el eje de version: donde vive el ORM en los cuatro arboles |
| `tests/test_inventory_reference_orm.py` | 5 aserciones, sujetos reales, dos anulaciones |
| `outputs/inventory-odoo19c.json` | el inventario completo con cada firma |
| `outputs/orm-across-trees.json` | la salida de la sonda |

`declared_symbols`, `signature_of` y `body_class` se **importan** del run del
censo. No se reescriben: dos extractores del mismo juicio son dos fuentes de
verdad que nadie sincroniza.

## El eje de version — por que la poblacion es 19c y solo 19c

| alias | `odoo/` | `odoo/orm/` | `.py` | ORM plano |
|---|---|---|---|---|
| `odoo18c` | si | **NO** | 0 | `models.py`=7637 `fields.py`=5443 `api.py`=1581 |
| `odoo18e` | **NO** | NO | 0 | — |
| `odoo19c` | si | **si** | **23** | — |
| `odoo19e` | **NO** | NO | 0 | — |

`odoo/orm` como **paquete existe solo en 19**. No es que 18 no tenga ORM: lo
tiene **plano**, en tres archivos de `odoo/`. Y Enterprise no trae directorio
`odoo/` en ninguna de sus dos versiones — es un arbol de addons que se monta
sobre Community, asi que su cero es **ausencia de directorio**, no ausencia de
ORM.

Las dos formas **no se suman**: seria fusionar dos versiones del producto en
una poblacion, que es el defecto que `H-API-76` registro.

## Los resultados

```
archivos  lineas   clases  fn_modulo  metodos  crudo  unico
      23   20084       59         87      808    954    792
```

Firmas: **155** declaran algun parametro opcional · **19** llevan `*args` ·
**11** tienen kw-only · **13** llevan `**kwargs`. Cuerpos `stub`: **38**.
Clases sin metodos: **2**.

Las cinco clases mayores: `BaseModel` 194 (`models.py:334`), `Field` 72
(`fields.py:92`), `Environment` 49 (`environments.py:40`), `Registry` 43
(`registry.py:84`), `Domain` 31 (`domains.py:196`).

El archivo con mas homonimos entre clases es `fields_relational.py` — **86**
ocurrencias contra **50** nombres; le sigue `domains.py`, 142 contra 88. Ahi
vive la diferencia de unidad entera.

*Metrica:* ocurrencias declaradas por AST en `odoo/orm` de `odoo19c`
(`odoo-tools@abe4040ec1`) — clase, funcion de modulo, o metodo con su clase
duenia — con la firma completa de cada llamable.

*Ciega a:* los 4 simbolos declarados dentro de un `if`/`try` de modulo
(`decorators.py:18`, medidos, no estimados); las clases anidadas (0 hoy); los
cierres dentro de funciones; los metodos que `MetaModel` pueda ligar por
metaclase o `setattr`; y al hecho de que `types.py` y `__init__.py` den 0 —
declaran alias y re-exportan, no estan vacios. Tambien al mapeo archivo-a-
archivo entre el ORM plano de 18 y el paquete de 19, que no se afirma aqui.
