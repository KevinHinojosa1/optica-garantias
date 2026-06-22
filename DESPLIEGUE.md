# Desplegar Óptica Los Andes (gratis)

## ¿Por qué no Netlify?

Esta aplicación es **FastAPI + Python + base de datos + archivos** (Excel, imágenes, PDF).  
**Netlify** solo sirve sitios estáticos y funciones serverless breves; **no puede ejecutar** este backend completo.

**Alternativa gratuita recomendada: [Render.com](https://render.com)** (plan Free).

---

## Opción A — Render (recomendada, gratis)

### 1. Subir el proyecto a GitHub

```bash
cd /ruta/a/mi-nuevo-proyecto
git init
git add .
git commit -m "Sistema Óptica Los Andes"
# Crear repo en github.com y luego:
git remote add origin https://github.com/TU_USUARIO/optica-garantias.git
git branch -M main
git push -u origin main
```

### 2. Crear cuenta en Render

1. Entra a [render.com](https://render.com) e inicia sesión con GitHub.
2. **New** → **Blueprint**.
3. Conecta el repositorio y Render detectará `render.yaml`.
4. En variables de entorno, configura:
   - `ANTHROPIC_API_KEY` — tu clave de Claude (para análisis de imágenes).
   - Opcional: `DATABASE_URL` si usas PostgreSQL (ver Opción B).

### 3. Desplegar

Render construye el `Dockerfile` y publica una URL como:

`https://optica-garantias.onrender.com`

La primera carga puede tardar ~1 minuto (el plan gratis “duerme” tras inactividad).

### 4. Probar

- `https://TU-URL.onrender.com/health` → debe responder `{"status":"ok"}`
- `https://TU-URL.onrender.com/importar` → pantalla principal

---

## Opción B — Base de datos persistente (recomendado en producción)

En el plan **gratis de Render**, los archivos SQLite **pueden perderse** al reiniciar el servicio.

Para datos que no se borren, usa **PostgreSQL gratis** en [Neon](https://neon.tech):

1. Crea un proyecto en Neon.
2. Copia la URL de conexión (formato `postgresql://...`).
3. En Render, variable de entorno:

```
DATABASE_URL=postgresql+psycopg://usuario:password@host/neondb?sslmode=require
```

(Reemplaza `postgresql://` por `postgresql+psycopg://` al pegar en Render.)

---

## Variables de entorno en producción

| Variable | Obligatoria | Descripción |
|----------|-------------|-------------|
| `ANTHROPIC_API_KEY` | Sí (para IA) | Análisis de garantías |
| `DATABASE_URL` | No | SQLite por defecto; Neon/Postgres para persistencia |
| `DEBUG` | No | `false` en producción |
| `DEFAULT_ASESOR` | No | Nombre por defecto en reportes |

---

## Otras plataformas gratuitas (similares a Render)

| Plataforma | Notas |
|------------|--------|
| [Fly.io](https://fly.io) | Free tier, permite volumen persistente |
| [Railway](https://railway.app) | Créditos mensuales limitados |
| [PythonAnywhere](https://www.pythonanywhere.com) | Free tier muy limitado |

---

## Desarrollo local (referencia)

```bash
./run.sh
# o
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```