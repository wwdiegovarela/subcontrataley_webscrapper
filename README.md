# Subcontrataley webscraper

Scraper Selenium del portal [Subcontrataley](https://www5.subcontrataley.cl/login.php).

## Estructura

```
flows/                         # lógica de cada rama
*_cloudrun.py                  # entry points Cloud Run Job (igual que documentos-instalaciones)
cloudbuild.yaml                # 1 imagen → N jobs
deploy_jobs.sh                 # deploy manual de todos los jobs
run_flujo.py                   # CLI local por rama
```

## Setup

```bash
cd subcontrataley_webscrapper
pip install -r requirements.txt
cp env.example .env   # completar password (comillas si tiene #)
```

## Cloud Run Jobs

Misma forma que `cargas_documentos_instalaciones_webscrapper`:

- **1 imagen** `gcr.io/worldwide-470917/subcontrataley-webscrapper`
- **N jobs**, cada uno con `--command=python --args=*_cloudrun.py`
- Secrets (usuario/password/token) se configuran una vez en el Job; el update
  solo toca vars base (`--update-env-vars`) y no las pisa

| Job | Script |
|-----|--------|
| `subcontrataley-libro-asistencia` | `libro_asistencia_cloudrun.py` |
| `subcontrataley-ingreso-trabajadores` | `ingreso_trabajadores_cloudrun.py` |

### Opción 1: Cloud Build desde Git (recomendado)

Igual que `cargas_documentos_instalaciones_webscrapper`: push a `main` → build + update de jobs.

1. Repo GitHub (ej. `wwdiegovarela/subcontrataley_webscrapper`)
2. En [Cloud Build Triggers](https://console.cloud.google.com/cloud-build/triggers?project=worldwide-470917):
   - **CREATE TRIGGER**
   - **Nombre:** `deploy-subcontrataley-jobs`
   - **Event:** Push to a branch
   - **Branch:** `^main$`
   - **Configuration:** Cloud Build configuration file
   - **Location:** `cloudbuild.yaml`
3. Primera vez: configurar secrets en cada Job (ver abajo). Los siguientes deploys no los pisan.

```bash
cd subcontrataley_webscrapper
git push origin main
# o manual:
gcloud builds submit --config=cloudbuild.yaml .
```

### Opción 2: deploy_jobs.sh

```bash
cd subcontrataley_webscrapper
bash deploy_jobs.sh
```

### Secrets (una vez)

```bash
gcloud run jobs update subcontrataley-libro-asistencia --region=us-east1 \
  --update-env-vars="SUBCONTRATALEY_USERNAME=USER,SUBCONTRATALEY_PASSWORD=PASS"

gcloud run jobs update subcontrataley-ingreso-trabajadores --region=us-east1 \
  --update-env-vars="SUBCONTRATALEY_USERNAME=USER,SUBCONTRATALEY_PASSWORD=PASS,TOKEN_CR_CONTRATOS=TOKEN"
```

### Ejecutar

```bash
gcloud run jobs execute subcontrataley-libro-asistencia --region=us-east1
gcloud run jobs execute subcontrataley-ingreso-trabajadores --region=us-east1
```

### Local (simula contenedor)

```bash
HEADLESS=true python libro_asistencia_cloudrun.py
HEADLESS=true python ingreso_trabajadores_cloudrun.py
# o pipeline ingreso vía CLI:
python run_flujo.py ingreso_trabajadores_e2e
```

**Permisos SA** (`webscrapper@worldwide-470917.iam.gserviceaccount.com`):

- Libro asistencia: `storage.objectViewer` (o similar) en el bucket de documentos
- Ingreso: BigQuery Data Viewer / Job User en `worldwide-470917.cr_reportes`

**Ingreso — pipeline:** listado SCL → BQ/CR (asistencia + contratos + faena ≤1 mes) →
plantilla vacía fresca → rellenar → validar → carga masiva.

## Ramos CLI locales

| CLI | Descripción |
|-----|-------------|
| `liquidaciones` | Liquidaciones de Sueldo |
| `libro_asistencia` | Libro de Asistencia |
| `pagos_afp_afc` | Pagos AFP y AFC |
| `pagos_isapre_fonasa` | Pagos Isapre / FONASA |
| `listado_trabajadores` | Listado finiquitables |
| `ingreso_trabajadores` | Solo subir plantilla ya rellena |
| `ingreso_trabajadores_e2e` | Pipeline completo de ingreso |

```bash
python run_flujo.py --list
python run_flujo.py liquidaciones
```

## Convención de captura

```text
flujo: liquidaciones
xpath plantilla: /html/body/...
```
