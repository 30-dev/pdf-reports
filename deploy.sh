#!/bin/bash

# Configuración
PROJECT_ID="tu-proyecto-id"  # Cambia esto por tu ID de proyecto de Google Cloud
SERVICE_NAME="pdf-reports"
REGION="us-central1"  # Puedes cambiar la región si lo deseas

echo "🚀 Desplegando servicio de PDF a Google Cloud Run..."

# 1. Configurar el proyecto
gcloud config set project $PROJECT_ID

# 2. Habilitar APIs necesarias
echo "📦 Habilitando APIs necesarias..."
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com

# 3. Construir y subir la imagen a Container Registry
echo "🔨 Construyendo imagen Docker..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME

# 4. Desplegar a Cloud Run
echo "☁️ Desplegando a Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --port 8080 \
  --max-instances 10

echo "✅ ¡Despliegue completado!"
echo "🌐 Tu servicio estará disponible en la URL que aparece arriba"
