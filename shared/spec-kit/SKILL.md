---
name: "spec-kit"
description: "Spec-Driven Development (SDD) — flujo completo: Constitution → Specify → Plan → Tasks → Implement → Converge. Sin dependencia externa, todo sobre herramientas nativas de OpenClaw."
---

# Skill: spec-kit

## Propósito

Implementar el flujo **Spec-Driven Development (SDD)** definido por el proyecto [github/spec-kit](https://github.com/github/spec-kit) como un skill nativo de OpenClaw. Cada fase del flujo produce un artefacto de especificación que guía la fase siguiente, y el ciclo `Implement → Converge` se repite hasta que la implementación converge contra la especificación.

No requiere instalar `specify-cli`, ni Python, ni ningún binario externo. Todo se ejecuta con las herramientas nativas del agente: `read`, `write`, `edit`, `exec`, `apply_patch`.

---

## Docente de Activación

Este skill se activa CUANDO el usuario solicita:

- "Quiero construir [X] siguiendo SDD / Spec-Driven Development / spec-kit"
- "Usá el flujo de especificaciones de GitHub"
- "Hacé un specify/plan/tasks para [X]"
- Cualquier mención a `spec-kit`, `sdd`, `especificación ejecutable`
- El agente detecta que el proyecto no tiene especificación previa y la complejidad supera ~3 tareas

**Modo de invocación:** El usuario activa con `/speckit-<fase> <descripción>` en lenguaje natural. El agente infiere la fase faltante y la ejecuta.

---

## Arquitectura del Flujo

```
FASE 0: CONSTITUTION  →  governance.md
FASE 1: SPECIFY       →  specs/specification.md
FASE 2: PLAN          →  specs/plan.md
FASE 3: TASKS         →  specs/tasks.md
FASE 4: IMPLEMENT     →  código fuente
FASE 5: CONVERGE      →  diff contra spec
        ↓
  ←─── IMPLEMENT + CONVERGE ───→
  (repetir hasta CONVERGED)
```

### Ubicación de artefactos

Todos los artefactos se escriben en `specs/` dentro del workspace del proyecto:

| Artefacto | Ruta | Formato |
|---|---|---|
| Constitution | `specs/governance.md` | Markdown con principios y guidelines |
| Specification | `specs/specification.md` | Markdown con user stories, requisitos, criterios |
| Plan | `specs/plan.md` | Markdown con arquitectura, stack, milestones |
| Tasks | `specs/tasks.md` | Markdown con tareas atómicas, dependencias, asignaciones |
| Convergence | `specs/converge.md` | Check list de verificación contra spec (autogenerado) |

---

## FASE 0 — Constitution

### Propósito

Establecer los **principios rectores** del proyecto. Se ejecuta una sola vez por proyecto. Define las reglas de calidad, testing, rendimiento y experiencia de usuario que gobernarán todas las fases siguientes.

### Procedimiento

1. Preguntar al usuario por el dominio del proyecto (o inferirlo del contexto).
2. Generar `specs/governance.md` usando la plantilla embebida.
3. Leer el archivo generado, confirmar con el usuario.
4. Ajustar si el usuario lo solicita.

### Template: governance.md

```markdown
# Governance: [Nombre del Proyecto]

## Principios Rectores
<!-- Cada principio debe ser una regla binaria, verificable. -->

- **[Principio 1]**: [Regla concreta]
- **[Principio 2]**: [Regla concreta]
- **[Principio 3]**: [Regla concreta]

## Quality Gates
<!-- Prerrequisitos para considerar el proyecto completado. -->

- [ ] **Quality Gate 1**: [Condición medible]
- [ ] **Quality Gate 2**: [Condición medible]
- [ ] **Quality Gate 3**: [Condición medible]

## Constraints
<!-- Limitaciones técnicas o de dominio. -->

- [Constraint 1]
- [Constraint 2]

## Glossary
<!-- Términos específicos del dominio. -->

- **Término**: Definición
```

---

## FASE 1 — Specify

### Propósito

Definir **qué** construir, no **cómo**. El usuario describe en lenguaje natural lo que quiere. El agente estructura esa descripción en user stories, requisitos funcionales, no funcionales y criterios de aceptación.

### Procedimiento

1. Preguntar al usuario o inferir del contexto actual:
   - ¿Qué problema resuelve? (ecuación)
   - ¿Quiénes son los usuarios?
   - ¿Cuál es el resultado esperado?
   - Criterios de éxito medibles
2. Generar `specs/specification.md` usando la plantilla.
3. Leer el archivo generado al usuario (en modo resumen).
4. Si hay ambigüedades → preguntar y refinar.
5. No avanzar a FASE 2 sin confirmación explícita del usuario.

### Template: specification.md

```markdown
# Specification: [Nombre del Proyecto]

## Problem Statement
<!-- Qué problema resuelve, por qué existe. -->

## Stakeholders & Users
- **Primary**: [Usuario principal]
- **Secondary**: [Otros afectados]

## User Stories
<!-- Cada story sigue: "Como [rol], quiero [acción] para [beneficio]" -->

1. **Story 1**: [Texto]
   - Acceptance Criteria:
     - [ ] Criterio 1
     - [ ] Criterio 2
   - Priority: [Must-have / Should-have / Nice-to-have]

2. **Story 2**: [Texto]
   - Acceptance Criteria:
     - [ ] Criterio 1
   - Priority: [Must-have / Should-have / Nice-to-have]

## Non-Functional Requirements
<!-- Rendimiento, seguridad, escalabilidad, etc. -->

- **NFR 1**: [Descripción]
- **NFR 2**: [Descripción]

## Out of Scope
<!-- Lo que explícitamente NO se construye. -->

## Success Metrics
<!-- Métricas medibles que determinan si el proyecto es exitoso. -->
```

---

## FASE 2 — Plan

### Propósito

Definir **cómo** construir lo especificado. Stack tecnológico, arquitectura, componentes, dependencias entre ellos, milestones.

### Procedimiento

1. Leer `specs/specification.md` para entender el alcance.
2. Investigar el codebase actual (si existe) con `read`, `find`, `tree` o `grep`.
3. Generar `specs/plan.md` usando la plantilla.
4. Confirmar con el usuario. El usuario debe aprobar el plan antes de continuar.

### Template: plan.md

```markdown
# Plan: [Nombre del Proyecto]

## Tech Stack
<!-- Lenguajes, frameworks, librerías, bases de datos. -->
- **Language**: 
- **Framework**: 
- **Database**: 
- **Infrastructure**: 
- **Key Libraries**: 

## Architecture Overview
<!-- Breve descripción de la arquitectura, diagrama conceptual. -->

## Components
<!-- Descomposición arquitectónica. -->

### Component 1: [Nombre]
- **Purpose**: 
- **Interface**: 
- **Dependencies**: 
- **Files to create/modify**: 

### Component 2: [Nombre]
- **Purpose**: 
- **Interface**: 
- **Dependencies**: 
- **Files to create/modify**: 

## Milestones
<!-- Hitos con fecha estimada o dependencia secuencial. -->

- **M1**: [Descripción] — depende de: —
- **M2**: [Descripción] — depende de: M1
- **M3**: [Descripción] — depende de: M1, M2

## Data Flow
<!-- Cómo circulan los datos entre componentes, diagrama de flujo. -->
```

---

## FASE 3 — Tasks

### Propósito

Descomponer el plan en **tareas atómicas**, secuenciales y asignables. Cada tarea tiene un objetivo claro, archivos afectados, complejidad estimada y método de verificación.

### Procedimiento

1. Leer `specs/specification.md` y `specs/plan.md`.
2. Descomponer cada componente del plan en tareas atómicas:
   - Cada tarea debe poder verificarse con un comando `exec` (bash, test, curl)
   - Ninguna tarea debe exceder ~300 líneas de código o 5 archivos — si excede, subdividir
3. Generar `specs/tasks.md` usando la plantilla.
4. El orden de ejecución se deriva de las dependencias (DAG implícito).
5. Confirmar con el usuario antes de ejecutar.

### Template: tasks.md

```markdown
# Tasks: [Nombre del Proyecto]

## Task List

| # | Task | Depends On | Complexity | Files | Verification |
|---|------|-----------|------------|-------|------------|
| 1 | [Título] | — | baja | `file1.py` | `pytest test_file1.py -x` |
| 2 | [Título] | 1 | media | `file2.py`, `file1.py` | `python -c "..."` |
| 3 | [Título] | 1,2 | alta | `file3.py`, `utils.py` | `curl -XGET ...` |

### Task Detail: #1 — [Título]

- **Goal**: [Qué se debe lograr]
- **Files affected**: `path/to/file`
- **Approach**: [Instrucciones precisas de implementación]
- **Expected output**: [Qué archivos se crean/modifican, qué comando validará]
- **Complexity**: baja / media / alta
- **Model recommendation**: main / qwen_mtp / deepseek

### Task Detail: #2 — [Título]
...
```

---

## FASE 4 — Implement

### Propósito

Ejecutar las tareas en orden de dependencia, una por una, verificando cada una antes de pasar a la siguiente.

### Procedimiento

1. Leer `specs/tasks.md`.
2. Por cada tarea, en orden de dependencia (topológico):
   a. Leer los archivos involucrados para entender el estado actual.
   b. Ejecutar la implementación:
      - Si la tarea es **simple** (baja complejidad, <50 líneas): implementar directamente con `edit`/`write`.
      - Si la tarea es **compleja** (media/alta): delegar a subagente con `sessions_spawn(mode="run", model="<modelo>", cleanup="delete")` y pasar las instrucciones exactas.
   c. **Verificar** con el comando indicado en la tarea.
   d. Si la verificación falla:
      - Corregir (máximo 2 intentos).
      - Si falla 2 veces → marcar tarea como bloqueada, notificar al usuario.
   e. Si pasa → registrar el resultado y avanzar a la siguiente.
3. NO ejecutar tareas que dependen de una tarea fallida o bloqueada.
4. Al completar todas las tareas → pasar a FASE 5 (Converge).

### Consideraciones de Ejecución

- **Serial**: Las tareas se ejecutan en orden estrictamente secuencial (por dependencias del DAG).
- **Sin paralelismo**: No hay concurrencia a menos que el usuario lo solicite explícitamente.
- **Estado**: Cada tarea completada se registra como `[x]` en el `tasks.md` — usar `edit` para marcar.
- **Proof**: Al completar una tarea, adjuntar evidencia de que la verificación pasó (output del comando).

---

## FASE 5 — Converge

### Propósito

Comparar la implementación final contra la especificación y el plan, identificando discrepancias. Si las hay, generar nuevas tareas para cerrar la brecha.

### Procedimiento

1. Leer `specs/specification.md`, `specs/plan.md` y los archivos de implementación.
2. Generar `specs/converge.md` con una checklist de verificación:
   - Cada user story de la especificación → ¿está implementada?
   - Cada non-functional requirement → ¿se cumple?
   - Cada componente del plan → ¿existe y funciona?
   - ¿Los quality gates de la constitution están satisfechos?
3. Ejecutar la verificación empírica:
   - Comandos de test (`pytest`, `npm test`, etc.)
   - CURL a endpoints si aplica
   - Ejecución del pipeline si aplica
4. Si **todo pasa** → marcar como **CONVERGED**. Proyecto completo.
5. Si **hay discrepancias**:
   a. Agregar nuevas tareas correctivas en `specs/tasks.md`.
   b. Volver a FASE 4 para esas tareas.
   c. Repetir FASE 5.
6. El ciclo FASE 4 → FASE 5 se repite hasta que `converge.md` reporte **CONVERGED**.

### Template: converge.md

```markdown
# Convergence Report: [Proyecto]

## Spec Compliance

| Story ID | Story | Status | Evidence |
|----------|-------|--------|----------|
| S1 | [Story] | ✅ / ❌ / ⏳ | [comando / archivo] |
| S2 | [Story] | ✅ / ❌ / ⏳ | [comando / archivo] |

## Plan Compliance

| Component | Status | Evidence |
|-----------|--------|----------|
| C1 | ✅ / ❌ / ⏳ | [comando / archivo] |

## Quality Gates

| Gate | Result | Evidence |
|------|--------|----------|
| QG1 | ✅ / ❌ | [comando / archivo] |

## Conclusion

**STATUS: [CONVERGED / REMAINING WORK]**
<!-- Si REMAINING WORK, listar las nuevas tareas generadas. -->
```

---

## Extensiones Opt-In

### Bug-Fix Extension

Cuando el usuario reporta un bug (`/speckit-bug <descripción>`):

1. **Assess**: 
   - Reproducir el bug con un comando o leer el error.
   - Identificar causa raíz (grep, logs, stacktrace).
   - Registrar hallazgo en el task/ticket.
2. **Fix**: 
   - Aplicar corrección con `edit`.
   - Verificar que el bug no se reproduce más.
   - Verificar que no se introdujeron regresiones.
3. **Test**: 
   - Ejecutar test suite del componente afectado.
   - Confirmar que el fix resuelve el síntoma original.

### Assess Extension

Cuando el usuario quiere evaluar una idea antes de comprometerse (`/speckit-assess <idea>`):

1. **Intake**: Documentar la idea cruda (qué, para quién, por qué).
2. **Research**: Buscar evidencia a favor y en contra:
   - Web search (`web_search`, `tavily_search`).
   - Análisis de factibilidad técnica.
3. **Define**: Problema, objetivos, métricas de éxito.
4. **Shape**: Posibles soluciones con trade-offs.
5. **Decide**: **Go** / **Needs Clarification** / **Kill**.

---

## Flujo Completo de Referencia

```
Usuario: "Quiero construir un comparador de juegos Steam vs Xbox"

→ FASE 0: El agente crea specs/governance.md con principios del proyecto
→ FASE 1: El agente genera specs/specification.md (qué construir)
→ FASE 2: El agente genera specs/plan.md (cómo construir)
→ FASE 3: El agente descompone en specs/tasks.md (tareas atómicas)
→ FASE 4: El agente implementa tarea #1, verifica, [x], tarea #2...
→ FASE 5: El agente compara implementación contra spec

Si hay discrepancias:
→ FASE 4: Arreglar tareas faltantes
→ FASE 5: Re-verificar → CONVERGED → Proyecto completo

Bug: "El login explota cuando el token expira"
→ Bug Assess: reproducir → identificar causa
→ Bug Fix: corregir → verificar
→ Bug Test: test suite → confirmar

Assess: "¿Deberíamos migrar a PostgreSQL?"
→ Intake → Research → Define → Shape → Decide (Go / Kill)
```

## Lo que NO hace

- No ejecuta implementación sin especificación y plan aprobados (FASE 1 y 2).
- No avanza sin confirmación explícita del usuario en transiciones críticas (FASE 1→2, FASE 2→3).
- No implementa tareas fuera del orden de dependencias del DAG.
- No converge sin verificación empírica (comandos reales, no inspección visual).
- No reintenta una tarea más de 2 veces sin consultar al usuario.