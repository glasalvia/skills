---
name: "dev-orchestrator"
description: "Planifica, ejecuta y supervisa tareas de desarrollo delegando a subagentes con verificación empírica por card, testeo E2E y cleanup del panel."
---

# Skill: dev-orchestrator

## Propósito

Transformar una intención de desarrollo —expresada por el usuario en lenguaje natural— en un **plan de trabajo estructurado, ejecutable y verificable**, delegando cada tarea atómica a un subagente especializado bajo supervisión del agente principal.

No es un generador de código. Es un **sistema de ejecución de proyectos** con planificación colaborativa, ejecución supervisada, verificación empírica y cierre documentado. Aplica a cualquier proyecto dentro del workspace.

---

## Flujo de 5 Fases

```
FASE 1: PLANIFICACIÓN COLABORATIVA
  Usuario ↔ Main
  Output: PLAN.md con tareas secuenciales y dependencias

FASE 2: DESCOMPOSICIÓN EN WORKBOARD
  Main crea cards con dependencias (workboard_link)
  Output: Board con DAG de tareas

FASE 3: EJECUCIÓN SUPERVISADA
  Main → Subagentes
  Main verifica cada card completada antes de promover la siguiente
  Output: Cards en completed + verificación pasada

FASE 4: TESTEO Y CIERRE
  Todas las cards completadas → post-mortem + test end-to-end
  Limpia cron watchdog + workboard panel
  Output: Resumen + lecciones en tasks/lessons.md

FASE 5: MONITOREO CONTINUO (durante FASE 3)
  Cron watchdog 30min → detecta cards colgadas, bloqueos, notifica al main
```

---

## FASE 1 — Planificación Colaborativa

### Procedimiento

1. El usuario expresa una intención de desarrollo.
2. El agente principal investiga el estado actual del codebase:
   - Lee archivos relevantes (no el proyecto entero).
   - Consulta la DB si aplica.
   - Identifica dependencias entre componentes.
3. El main propone un `PLAN.md` con:
   - Título del proyecto.
   - Ecuación del problema (qué se resuelve, por qué).
   - Lista de tareas atómicas secuenciales con dependencias.
   - Cada tarea incluye: objetivo, archivos involucrados, complejidad estimada.
   - **Asignación de modelo a cada tarea** según la heurística de complejidad.
4. El usuario revisa, ajusta, **aprueba explícitamente**.
5. El main no avanza a FASE 2 sin aprobación.

### Estructura de PLAN.md

```markdown
# Plan: [Título]

## Ecuación
[Problema → Solución → Por qué]

## Tareas

| # | Tarea | Depende de | Complejidad | Modelo |
|---|-------|-----------|-------------|--------|
| 1 | ... | — | baja | qwen_mtp |
| 2 | ... | 1 | alta | deepseek |
| 3 | ... | 1,2 | media | qwen_mtp |

## Verificación final
[Comando o query que valida el proyecto completo]
```

---

## FASE 2 — Descomposición en Workboard

### Procedimiento

1. El main crea un board en workboard (o usa uno existente).
2. Por cada tarea del PLAN.md, crea una card con `workboard_create`.
3. Establece dependencias con `workboard_link` (parent → child).
4. Usa `workboard_promote` para habilitar las cards sin dependencias.

### Estructura obligatoria de cada card

```
Título: [Verbo] [Objeto] — una línea clara

Notas (formato fijo):
  Objetivo: [Qué se espera lograr, en una oración]
  Verificación: [Comando SQL, bash, o python que el main ejecuta para validar]
  Output esperado: [Archivo(s) que se crearán/modificarán]
  Complejidad: [baja|media|alta]
  Contexto estimado: [N líneas lectura] / [N líneas escritura]
  Modifica existentes: [sí|no]
  Modelo asignado: [qwen_mtp|deepseek|main]
```

### Atributos adicionales de card

| Atributo | Valor |
|---|---|
| `boardId` | Nombre del proyecto (ej: `game-compare`) |
| `priority` | `normal` por defecto, `high` para bloqueantes |
| `labels` | `dev-orchestrator`, `[fase]` |
| `skills` | Según la tarea (ej: `python-debugpy`, `gog-workspace`) |

---

## FASE 3 — Ejecución Supervisada

### ⚠️ RESTRICCIÓN CRÍTICA: Sin paralelismo con modelo local

Si el backend de inferencia es un modelo local (Ollama, llama.cpp, etc.), **no existe concurrencia real de inferencia**. Cada solicitud se serializa en el servidor de modelos. Lanzar múltiples subagentes simultáneos contra el mismo modelo local produce:

1. Contención de GPU/CPU — todos los subagentes compiten por el mismo recurso de cómputo.
2. Timeouts en cascada — cada subagente espera su turno de inferencia mientras su propio cronómetro de timeout corre.
3. Multiplicación de overhead de contexto — cada subagente carga contexto desde cero, desperdiciando tokens en establecer el mismo estado.

**Regla:** Con modelo local, todo es serial. Un subagente a la vez. Usar `sessions_yield` entre spawns, o ejecutar directamente en sesión principal si la tarea es trivial.

**Excepción:** Backends con concurrencia real (OpenRouter, OpenAI, Anthropic) sí soportan subagentes paralelos porque cada request va a un worker de inferencia independiente.

### Reglas de despacho

| Regla | Detalle |
|---|---|
| **DAG primero** | Una card solo se despacha cuando todas sus parents están `completed`. Usar `workboard_read` para verificar estado de dependencias. Si `workboard_claim` falla con `card dependencies are not done` 2 veces → no reintentar. Reportar al usuario. |
| **qwen_mtp preferente serial** | qwen3.6-35b-mtp es la **primera opción** para cualquier card de complejidad baja o media. Solo UNA card qwen_mtp a la vez — ejecución estrictamente serial. El main espera su completion antes de despachar otra qwen_mtp. |
| **qwen_mtp — cleanup OBLIGATORIO tras finalizar** | Cada subagente delegado a `ollama/qwen3.6-35b-mtp` DEBE ser eliminado al completar. Usar `sessions_spawn(cleanup="delete")` en cada spawn de qwen_mtp. Esto es innegociable: los subagentes qwen_mtp no deben persistir — son efímeros por diseño. No usar `cleanup="keep"` bajo ninguna circunstancia para qwen_mtp. |
| **deepseek bajo demanda** | deepseek-v4-pro se reserva para cards de complejidad **alta**, diseño/arquitectura, o refactors que requieren razonamiento profundo. Si qwen_mtp está disponible y la card es baja/media → qwen_mtp. Si qwen_mtp ya está ocupado y la card es baja/media → encolar hasta que qwen_mtp se libere. Solo usar deepseek para baja/media si qwen_mtp falla 2 veces. |
| **deepseek paralelo** | Hasta 3 cards deepseek simultáneas (solo alta complejidad). Si hay más de 3 pendientes, se encolan. |
| **Claim antes de spawn** | `workboard_claim` → `sessions_spawn(mode="run")`. Guardar claim token. |
| **Heartbeat** | Para tareas largas (>5 min), `workboard_heartbeat` cada 2-3 minutos. |

### Parámetros de sessions_spawn por modelo

| Modelo | `cleanup` | `model` | `runtime` |
|---|---|---|---|
| `ollama/qwen3.6-35b-mtp` | **`"delete"`** (OBLIGATORIO) | `ollama/qwen3.6-35b-mtp:latest` | `subagent` |
| `openrouter/deepseek/deepseek-v4-pro` | `"keep"` (por defecto) | `openrouter/deepseek/deepseek-v4-pro` | `subagent` |

### Verificación post-ejecución

1. El subagente completa → el main recibe el completion event.
2. El main ejecuta el comando del campo `Verificación` de la card.
3. Si pasa → `workboard_complete` con summary, proof, artifacts.
4. Si falla → `workboard_comment` documentando el error, reabrir la card. Si falla 2 veces la misma verificación → `workboard_block` con razón, notificar al usuario.
5. Tras completar una card, ejecutar `workboard_dispatch` para promover las cards que dependían de ella.

### Regla de 2 fallos (ANTI-LOOP)

Si un mismo tool call falla 2 veces con el mismo error → PARAR. No reintentar. Documentar en la card y notificar al usuario. Esto aplica a `workboard_claim`, `exec`, `sessions_spawn`, etc.

---

## FASE 4 — Testeo y Cierre

### 4.1 — Test End-to-End

Cuando TODAS las cards están en `completed`, el main ejecuta una **verificación end-to-end** del sistema completo — no solo las verificaciones individuales de cada card:

1. Levantar el sistema (servidor, frontend, lo que aplique).
2. Ejecutar el comando de verificación final del `PLAN.md`.
3. Probar los flujos principales: si es una API → curl a los endpoints clave con distintos filtros/parámetros. Si es un pipeline → ejecutar sobre lote pequeño. Si es frontend → verificar que carga sin errores JS.
4. Si todas las pruebas pasan → proceder a post-mortem.
5. Si alguna falla → crear card de corrección, volver a FASE 3 para esa card.

El test end-to-end es **obligatorio** — no se considera el proyecto completo sin él.

### 4.2 — Post-mortem

Al completar todas las cards y pasar el test end-to-end:

```markdown
# Post-mortem: [Proyecto] — [Fecha]

## Resultados
| # | Card | Estado | Intentos | Modelo |
|---|------|--------|----------|--------|
| 1 | ... | completed | 1 | qwen_mtp |

## Archivos modificados
- `path/to/file` — [qué cambió]

## Métricas finales
[Resultados concretos: matches, líneas, rendimiento]

## Lecciones
- [Qué falló, qué se aprendió]
```

Las lecciones se agregan a `tasks/lessons.md` en el proyecto.

### 4.3 — Limpieza del Panel de Trabajo (OBLIGATORIO)

El workboard **NUNCA debe quedar con cards acumuladas** tras finalizar un proyecto. La limpieza es parte innegociable del cierre:

1. **Eliminar el cron watchdog** con `cron(action="remove")`.
2. **Eliminar subagentes residuales** — verificar con `subagents(action="list")` que no queden sesiones qwen_mtp o deepseek vivas. Si las hay, eliminarlas.
3. **Archivar el board del proyecto** con `workboard_board_archive(id="<boardId>")`. Esto retira todas las cards del panel visual de una sola operación. No se requiere eliminación individual de cards — el board archivado deja de aparecer en el panel inmediatamente.
4. **Mover `PLAN.md`** a `tasks/archive/PLAN_[proyecto]_[fecha].md`.
5. **Liberar** cualquier card bloqueada restante con `workboard_release`.

### Principio de panel limpio

> El panel de trabajo es un espacio de **trabajo activo**, no un repositorio histórico. Al finalizar un proyecto, el panel debe quedar completamente vacío en todas sus columnas. Si el usuario ejecuta `workboard_list` tras el cierre y ve cards, la FASE 4 no se ha completado correctamente. Los boards archivados preservan el registro histórico sin contaminar el espacio de trabajo.

---

## FASE 5 — Monitoreo Continuo (Watchdog)

### Cron watchdog

Al iniciar FASE 3, el main crea un cron:

```
schedule: every 30 min
payload: systemEvent
text: "WATCHDOG: Revisar estado de cards del proyecto [nombre]. 
       Verificar cards running sin heartbeat >15 min, 
       cards blocked:user, y cards failed con reintentos agotados.
       Si hay anomalías, ejecutar workboard_dispatch y reportar."
sessionTarget: main
```

### Acciones del watchdog

| Condición | Acción |
|---|---|
| Card `running` sin heartbeat > 15 min | `workboard_reclaim`, notificar al usuario |
| Card `blocked` con razón `user` | Notificar al usuario con la pregunta concreta |
| Card `failed` | Notificar al usuario, no reintentar automáticamente |
| Todas las cards `completed` | Notificar, proceder a FASE 4 |

---

## Asignación de Modelos

| Modelo | Prioridad | Cuándo se usa | Paralelismo | Cleanup |
|---|---|---|---|---|
| `ollama/qwen3.6-35b-mtp` | **PRIMERO** | Cards de complejidad baja/media, tareas mecánicas, ejecución de comandos, verificaciones | Serial estricto — 1 a la vez | **DELETE obligatorio** |
| `openrouter/deepseek/deepseek-v4-pro` | **SEGUNDO** | Cards de complejidad alta, diseño/arquitectura, refactors complejos. Solo si qwen_mtp ya está ocupado y la card es urgente, o si la card es de alta complejidad. | Paralelo — hasta 3 simultáneos | Keep (por defecto) |
| `main` (sin subagente) | **TERCER** | Cards de verificación trivial (<30s), tasks de complejidad mínima que no justifican overhead de subagente | N/A | N/A |

### Heurística de complejidad

```
complejidad = (archivos_a_leer × 0.3) + (archivos_a_modificar × 0.5) + (lógica_nueva × 0.2)

baja:  < 5  → qwen_mtp (primera opción)
media: 5-8  → qwen_mtp (primera opción), deepseek solo si qwen falla 2 veces
alta:  > 8  → deepseek
```

### Regla de oro de asignación

> **qwen_mtp es la opción por defecto.** Solo se escala a deepseek cuando la complejidad lo exige o qwen_mtp ya está ocupado. Nunca se asignan dos tareas simultáneas a qwen_mtp. Si hay múltiples cards qwen_mtp pendientes, se procesan en serie — una tras otra. **Todo subagente qwen_mtp se elimina automáticamente al finalizar** (`cleanup="delete"`).

---

## Límites de Contexto por Card

| Complejidad | Máx. líneas lectura | Máx. líneas escritura |
|---|---|---|
| baja | 200 | 100 |
| media | 300 | 200 |
| alta | 500 | 300 |

Si una tarea excede estos límites, se descompone en subtareas durante FASE 1.

---

## Lo que NO hace

- No ejecuta código sin planificación previa aprobada.
- No modifica archivos existentes sin autorización explícita en la card (campo `Modifica existentes: sí`).
- No decide arquitectura unilateralmente — decisiones de diseño pasan por el usuario en FASE 1.
- No ejecuta cards en paralelo si el DAG no lo permite.
- **No lanza múltiples subagentes simultáneos contra un modelo local** (Ollama, llama.cpp). Con modelo local, todo es serial. Esta es la causa #1 de timeouts en cascada.
- No deja crons huérfanos — se eliminan en FASE 4.
- No reintenta una card más de 2 veces sin consultar al usuario.
- No ignora la regla de los 2 fallos de MEMORY.md.
- No asigna tareas a deepseek si qwen_mtp puede manejarlas.
- No cierra un proyecto sin ejecutar el test end-to-end de FASE 4.
- **No mantiene subagentes qwen_mtp vivos tras finalizar su tarea** — `cleanup="delete"` es innegociable para qwen_mtp.
- **No deja el panel de trabajo con cards acumuladas** tras el cierre — el board se archiva y el panel queda limpio.

---

## Ejemplo de Sesión

```
Usuario: "Quiero invertir el pipeline de game-compare para usar 
         el catálogo Xbox desde IGDB"

Main: Investiga codebase → Propone PLAN.md con 5 tareas:
  1. Crear igdb_fetch_xbox_catalog() en _api_helpers.py [baja, qwen_mtp]
  2. Crear xbox_steam_pipeline.py [alta, deepseek] → depende de 1
  3. Ejecutar pipeline sobre 100 juegos [media, qwen_mtp] → depende de 2
  4. Verificar métricas [baja, qwen_mtp] → depende de 3
  5. Actualizar README.md [baja, qwen_mtp] → depende de 4

Usuario: Aprueba.

Main: Crea 5 cards con dependencias → Crea cron watchdog → 
      Despacha card 1 con sessions_spawn(cleanup="delete", model="ollama/qwen3.6-35b-mtp") →
      qwen_mtp completa y su sesión se borra automáticamente →
      Verifica → Completa card 1 →
      Despacha card 2 con sessions_spawn(cleanup="keep", model="openrouter/deepseek/deepseek-v4-pro") →
      deepseek completa, sesión se conserva → Verifica → Completa card 2 →
      Despacha cards 3,4,5 con sessions_spawn(cleanup="delete", model="ollama/qwen3.6-35b-mtp") —
      cada una se elimina al terminar, serial estricto →
      FASE 4: Test end-to-end → Post-mortem → 
      Elimina cron → Archiva board con workboard_board_archive → Panel limpio →
      Archiva PLAN.md → Listo.
```

---

## Interacción con otros Skills

Si una card involucra dominios específicos, el main asigna el skill correspondiente en el campo `skills` de la card:

| Dominio | Skill |
|---|---|
| Python debugging | `python-debugpy` |
| Google Workspace | `gog-workspace` |
| Web scraping | `browser-automation` |
| Base de datos SQLite | (manejo directo, sin skill) |
| APIs REST | (manejo directo, sin skill) |

## Environment
- **cachy-gla:** Orquestación completa con subagentes. Modelos: deepseek-v4-flash (principal), qwen3.6-35b (fallback local).
- **Raspi:** No implementado (sin capacidad de subagentes ni modelos grandes).
- **Dependencias:** Node.js, OpenClaw SDK, acceso a sesiones de agente.
