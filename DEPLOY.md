# 🚀 Guía de Despliegue a Google Cloud Run

## Prerrequisitos

1. **Cuenta de Google Cloud** con un proyecto creado
2. **Google Cloud SDK (gcloud CLI)** instalado
   - Descarga: https://cloud.google.com/sdk/docs/install
3. **Docker** instalado (opcional, Cloud Build lo hace por ti)

## 📋 Pasos para Desplegar

### 1. Instalar Google Cloud SDK

Si no lo tienes instalado:

**Windows:**
```powershell
# Descarga el instalador desde:
# https://cloud.google.com/sdk/docs/install#windows

# O usa Chocolatey:
choco install gcloudsdk
```

**Verificar instalación:**
```bash
gcloud --version
```

### 2. Autenticarse en Google Cloud

```bash
gcloud auth login
```

Esto abrirá tu navegador para autenticarte.

### 3. Crear o Seleccionar un Proyecto

**Crear nuevo proyecto:**
```bash
gcloud projects create tu-proyecto-id --name="PDF Reports DIGEI"
```

**O listar proyectos existentes:**
```bash
gcloud projects list
```

**Configurar el proyecto:**
```bash
gcloud config set project tu-proyecto-id
```

### 4. Habilitar APIs Necesarias

```bash
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
```

### 5. Desplegar el Servicio

**Opción A - Usando el script automático:**

1. Edita `deploy.sh` y cambia `PROJECT_ID` por tu ID de proyecto
2. Ejecuta:
```bash
chmod +x deploy.sh
./deploy.sh
```

**Opción B - Comandos manuales:**

```bash
# 1. Construir y subir la imagen
gcloud builds submit --tag gcr.io/tu-proyecto-id/pdf-reports

# 2. Desplegar a Cloud Run
gcloud run deploy pdf-reports \
  --image gcr.io/tu-proyecto-id/pdf-reports \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --port 8080 \
  --max-instances 10
```

### 6. Obtener la URL del Servicio

Después del despliegue, verás una URL como:
```
https://pdf-reports-xxxxxxxxx-uc.a.run.app
```

## 🔧 Actualizar el Frontend

Una vez desplegado, actualiza la URL en tu frontend Next.js:

**Archivo:** `components/download-report-button.tsx`

Cambia:
```typescript
const response = await fetch('http://127.0.0.1:8000/generar-pdf', {
```

Por:
```typescript
const response = await fetch('https://TU-URL-DE-CLOUD-RUN/generar-pdf', {
```

## 📊 Monitoreo y Logs

**Ver logs:**
```bash
gcloud run services logs read pdf-reports --region us-central1
```

**Ver métricas:**
```bash
gcloud run services describe pdf-reports --region us-central1
```

## 💰 Costos Estimados

Cloud Run cobra por:
- **Solicitudes:** $0.40 por millón de solicitudes
- **Tiempo de CPU:** $0.00002400 por vCPU-segundo
- **Memoria:** $0.00000250 por GiB-segundo

**Nivel gratuito mensual:**
- 2 millones de solicitudes
- 360,000 vCPU-segundos
- 180,000 GiB-segundos

Para un uso normal (100-500 reportes/mes), probablemente estarás dentro del nivel gratuito.

## 🔒 Seguridad (Opcional)

Si quieres que solo tu frontend pueda acceder:

```bash
# Desplegar sin acceso público
gcloud run deploy pdf-reports \
  --image gcr.io/tu-proyecto-id/pdf-reports \
  --no-allow-unauthenticated

# Crear una cuenta de servicio
gcloud iam service-accounts create pdf-invoker

# Dar permisos
gcloud run services add-iam-policy-binding pdf-reports \
  --member="serviceAccount:pdf-invoker@tu-proyecto-id.iam.gserviceaccount.com" \
  --role="roles/run.invoker"
```

## 🔄 Actualizar el Servicio

Para actualizar después de hacer cambios:

```bash
# Reconstruir y redesplegar
gcloud builds submit --tag gcr.io/tu-proyecto-id/pdf-reports
gcloud run deploy pdf-reports --image gcr.io/tu-proyecto-id/pdf-reports
```

## ❓ Troubleshooting

**Error: "Permission denied"**
- Verifica que las APIs estén habilitadas
- Asegúrate de tener permisos de Editor en el proyecto

**Error: "Build failed"**
- Revisa los logs: `gcloud builds list`
- Verifica que `requirements.txt` esté correcto

**Error: "Service timeout"**
- Aumenta el timeout: `--timeout 300`
- Aumenta la memoria: `--memory 1Gi`

## 📞 Soporte

Si tienes problemas, revisa:
- Documentación oficial: https://cloud.google.com/run/docs
- Logs del servicio: `gcloud run services logs read pdf-reports`
