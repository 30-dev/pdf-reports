# Guía para IA: MVP de Captura de Datos con Next.js y Supabase

## 1. Resumen del Proyecto y Objetivo del MVP

**Objetivo Principal:** Crear una aplicación web para administrar y responder cuestionarios de autodiagnóstico. Los datos recolectados se almacenarán en Supabase y serán la fuente para generar los reportes finales.

**Tecnologías del MVP:**
- **Frontend:** Next.js (con TypeScript y Tailwind CSS).
- **Backend & Base de Datos:** Supabase.

**Meta del MVP:** Construir un sistema funcional que permita a los usuarios responder a un cuestionario definido y que sus respuestas se guarden en la base de datos. El cuestionario se basará en la estructura de dimensiones y subdimensiones del proyecto.

---

## 2. Modelo de Datos en Supabase

El primer paso es definir la estructura en Supabase para almacenar las preguntas y las respuestas. Este esquema es fundamental.

**Tablas Sugeridas:**

1.  **`organizaciones`** (o `usuarios`)
    - Almacena la información de la entidad que responde el cuestionario.
    - **Columnas:** `id` (uuid), `created_at` (timestamp), `nombre_organizacion` (text).

2.  **`cuestionarios`**
    - Define los diferentes cuestionarios disponibles.
    - **Columnas:** `id` (serial), `nombre` (text, ej: "Autodiagnóstico Igualdad de Género 2025"), `descripcion` (text).

3.  **`preguntas`**
    - Contiene cada una de las preguntas o ítems a evaluar, organizados por dimensión.
    - **Columnas:** `id` (serial), `cuestionario_id` (fk a `cuestionarios`), `dimension` (text, ej: "Dimensión 1: ..."), `texto_pregunta` (text, ej: "1.1 Subdimensión..."), `tipo_respuesta` (text, ej: "si_no_na").

4.  **`respuestas`**
    - Almacena la respuesta de una organización a una pregunta específica.
    - **Columnas:** `id` (serial), `organizacion_id` (fk a `organizaciones`), `pregunta_id` (fk a `preguntas`), `valor_respuesta` (text, ej: "Sí", "No", "No Aplica").

**Acción Inicial:**
- Crear estas tablas en el editor SQL de Supabase.
- Poblar la tabla `preguntas` con los datos inferidos de `tabla_subdimensiones.json`.

---

## 3. Plan de Desarrollo del MVP (Fases)

### **Fase 1: Configuración y Creación del Formulario**

**Objetivo:** Montar el proyecto Next.js y crear un formulario dinámico que cargue las preguntas desde Supabase.

**Pasos:**

1.  **Inicializar Proyecto Next.js y Supabase:**
    - `npx create-next-app@latest reporte-web-app --typescript --tailwind --eslint`
    - `npm install @supabase/supabase-js`
    - Configurar el cliente de Supabase en la aplicación.

2.  **Poblar la tabla `preguntas`:**
    - Crea un script de `seed` o inserta manualmente las preguntas desde `data/tabla_subdimensiones.json` en tu tabla `preguntas` de Supabase.

3.  **Crear la Página del Cuestionario (`app/cuestionario/[id]/page.tsx`):**
    - Esta página será un Server Component (`async function`).
    - Hará `fetch` de todas las preguntas de un cuestionario específico desde la tabla `preguntas` en Supabase.
    - Agrupará las preguntas por `dimension` para poder renderizarlas en secciones.

4.  **Crear Componentes del Formulario:**
    - **`SeccionDimension.tsx`:** Un componente que recibe un título de dimensión y una lista de preguntas, y las renderiza.
    - **`PreguntaInput.tsx`:** Un componente que renderiza una sola pregunta con sus opciones de respuesta (ej: radio buttons para "Sí", "No", "No Aplica").
    - El formulario principal debe ser un Componente de Cliente (`'use client'`) para manejar el estado de las respuestas.

### **Fase 2: Envío y Almacenamiento de Respuestas**

**Objetivo:** Capturar las respuestas del usuario en el formulario y guardarlas en la base de datos de Supabase.

**Pasos:**

1.  **Manejo del Estado del Formulario:**
    - En el componente principal del formulario (`'use client'`), usa un estado de React (`useState`) para almacenar las respuestas del usuario a medida que las selecciona. El estado podría ser un objeto donde la clave es el `pregunta_id` y el valor es la `valor_respuesta`.

2.  **Crear un Route Handler (API) para el Envío:**
    - Crea un archivo en `app/api/submit-answers/route.ts`.
    - Este endpoint recibirá los datos del formulario (ID de la organización y el objeto de respuestas).
    - Será responsable de iterar sobre las respuestas y hacer un `insert` múltiple en la tabla `respuestas` de Supabase.
    - Implementa validación y manejo de errores.

3.  **Función de Envío en el Cliente:**
    - En el componente del formulario, al hacer clic en "Enviar", se llamará a una función que:
        - Reúne los datos del estado.
        - Hace una petición `POST` al endpoint `/api/submit-answers` con los datos.
        - Muestra una notificación de éxito o error al usuario.

---

## 4. Próximos Pasos (Post-MVP)

- **Autenticación:** Requerir que los usuarios inicien sesión (con Supabase Auth) para poder responder y ver sus cuestionarios.
- **Dashboard de Usuario:** Crear una página donde un usuario pueda ver los cuestionarios que ha completado.
- **Roles y Permisos:** Definir diferentes roles si es necesario (ej: administrador, usuario).
- **Conexión con el Generador de Reportes:** Una vez que los datos están en Supabase, el microservicio de Python (o una nueva función serverless) puede leer desde esta base de datos para generar el PDF, cerrando el ciclo del proceso.