# Selección de modelo para subagentes — cheat-sheet (canónico en docs)

Regla completa: `docs/.claude/rules/model-selection-subagents.md`. Aquí sólo el
invariante operativo.

> **Reducida a cheat-sheet 2026-09-07.** Era una copia completa de 28 290 B que
> había divergido: **cero** menciones de `claude-fable-5-1` —no sabía que la
> versión existe— y **tres** pasajes con el encuadre en USD que
> `calibration-verified-numbers.md` prohíbe citar como costo. Una sesión con
> sólo este repo en alcance cargaba la guía equivocada. Misma clase que
> H-DOCS-97; el error de fondo, :ref:`h-docs-1137`.

## El costo lo domina lo que el agente RELEE

El **98.07 %** de lo que consume un subagente es caché leída. Acortar el prompt
o pedir menos salida no ahorra nada: los dos juntos son el **0.02 %**. Lo que
acota el gasto es el número de **turnos**, y eso lo fija un prompt con los
archivos nombrados y la condición de cierre escrita.

## El orden por turno, en tokens equivalentes — NO en USD

| `model:` | resuelve a | caché leída | por turno, contra opus | rango |
|---|---|---|---|---|
| `haiku` | `claude-haiku-4-5` | 0.1 | 0.20× — **no arranca** (piso 126 029 tokens) | 1 |
| `sonnet` | `claude-sonnet-5` | 0.2 | **0.40×** | 3 |
| `opus` | `claude-opus-5` | 0.5 | 1.00× | 4 |
| `fable` | `claude-fable-5-1` | **0.25** | **0.79×** | **5** |

**`fable` no es «el caro».** Por token de entrada y salida cuesta el doble que
opus; por token de **caché leída** cuesta la mitad — y ése es el token que
domina. Con mayor rango declarado (5 contra 4) y 13 capacidades contra 12,
**domina a opus en los dos ejes** para trabajo de subagente.

**Las dos versiones de fable NO son intercambiables:** `claude-fable-5` está en
`tier_10_50` (caché leída 1.0, o sea **2×** opus) y `claude-fable-5-1` en
`tier_10_50_cache_read_0_25`. El alias resuelve a la 5-1.

**Criterio:** análisis y redacción → `sonnet`. Razonamiento adversarial o
decisión con trade-offs finos → `fable`, con `opus` de respaldo si no está
disponible. Elegir opus «por ser el caro» es el encuadre en USD sobreviviendo.

## El alias no determina el modelo

Resuelve distinto según el proveedor: el mismo `sonnet` da `claude-sonnet-4-5`
(ventana 200 k) o `claude-sonnet-5` (1 M). Por eso el store guarda el
identificador que el **transcript** declara, no el alias del despacho.

`claude-mythos-5`, `claude-mythos-5-1` y `claude-opus-4-5` están en el catálogo
y **ningún alias los alcanza**: existen como eslabón de `fallback_3p`, no como
opción despachable.

## Lo que el modelo económico NO relaja

Todo subagente de análisis **persiste su documento** en la iniciativa antes de
devolver el resumen — el resumen no lo sustituye. Y si modifica código, quedan
**dos** commits: el del repo de código y el de docs citando `repo@hash`.

El identificador del modelo va **completo** en commits, comentarios y tablas de
telemetría; **prohibido sólo en el cuerpo y el título de un PR**.
