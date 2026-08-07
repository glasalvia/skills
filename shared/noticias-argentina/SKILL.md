---
name: "noticias-argentina"
description: "Recolecta noticias mas relevantes de Argentina desde Infobae y La Politica Online via RSS, filtradas y puntuadas por relevancia"
---

# Skill: Noticias de Argentina

## Descripción
Recolecta las noticias más relevantes de Argentina desde múltiples fuentes RSS, filtrando por contenido argentino y puntuándolas según relevancia (política, economía, sociedad).

## Fuentes
- **Infobae:** `https://www.infobae.com/arc/outboundfeeds/rss/`
- **La Política Online (LPO):** `https://www.lapoliticaonline.com/files/rss/ultimasnoticias.xml`

## Script Principal
- **Path:** `~/scripts/rss_noticias.py`

## Uso

### Ejecutar bajo demanda
```bash
python3 ~/scripts/rss_noticias.py
```

### Crear cron para envío diario
```bash
# Ejemplo: todos los días a las 8:00 AM y 18:00 PM
cron add "noticias_arg_manana" \
  --schedule "0 8 * * *" \
  --tz "America/Buenos_Aires" \
  --isolated \
  --message "Ejecutá python3 /home/glasalvia/.openclaw/workspace/scripts/rss_noticias.py y presentame el resultado con este formato:
  Resumen diario de noticias, agrupado por categoria, con un breve comentario de tendencia sobre que temas dominan la agenda del dia."

cron add "noticias_arg_tarde" \
  --schedule "0 18 * * *" \
  --tz "America/Buenos_Aires" \
  --isolated \
  --message "Ejecutá python3 /home/glasalvia/.openclaw/workspace/scripts/rss_noticias.py y presentame las novedades de la tarde en relacion a lo que salio a la manana."
```

## Funcionamiento Interno

1. **Fetch RSS:** Descarga ambos feeds XML (Infobae + LPO) con timeout de 20s
2. **Filtrado Argentina:** Para Infobae, filtra noticias que mencionen keywords argentinas (provincias, políticos, economía local). LPO es 100% argentina.
3. **Scoring de relevancia:** Sistema de pesos por keywords:
   - **Prioridad alta (15-30 pts):** Milei, presidencial, dolar, inflacion, FMI, Congreso, elecciones, BCRA, reforma, candidato 2027
   - **Prioridad media (5-15 pts):** Mundial, seleccion argentina, clubes de futbol, protesta, inseguridad
   - **Prioridad baja (2-5 pts):** Espectaculos, farandula, tecnologia
   - **Penalizaciones:** Clickbait, noticias virales sin sustancia, contenido de otros paises de LATAM
   - **Bonus:** Fuente LPO (+15), descripción sustancial (+5)
4. **Deduplicación:** Evita titulos similares (mismos primeros 40 caracteres)
5. **Top 12:** Muestra las 12 más relevantes agrupadas por categoría

## Categorías detectadas
- POLITICA: Presidencia, Congreso, elecciones, partidos
- ECONOMIA: Dolar, inflacion, BCRA, FMI, impuestos
- SOCIEDAD: Protestas, inseguridad, justicia, clima
- MUNDIAL2026: Seleccion Argentina en el Mundial
- DEPORTES: Futbol local, otros deportes
- TECNOLOGIA: IA, startups, big tech
- ESPECTACULOS: Cine, TV, farandula

## Agregar nuevas fuentes
Editar el diccionario `FEEDS` en `rss_noticias.py`:
```python
FEEDS = {
    "Infobae": "https://www.infobae.com/arc/outboundfeeds/rss/",
    "La Politica Online": "https://www.lapoliticaonline.com/files/rss/ultimasnoticias.xml",
    # Agregar nuevas fuentes aqui
}
```

## Environment
- **cachy-gla:** RSS fetch directo, scoring por relevancia, generación de resumen vía Ollama/Qwen.
- **Raspi:** No implementado (sin Ollama/Qwen local para scoring).
- **Dependencias:** `python3-feedparser`, `requests`, `lxml`. Ollama endpoint: `http://localhost:11434`.
