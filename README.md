# MiTurno

Backend de una plataforma SaaS de gestión de turnos y reservas ("MiTurno"). Construido con FastAPI y PostgreSQL, soporta múltiples empresas con sus propias sucursales, servicios, profesionales y clientes.

---

## Características principales

- **Multi-tenant**: cada empresa gestiona sus propias sucursales de forma independiente
- **Sistema de turnos**: reserva, confirmación, cancelación y archivo de turnos
- **Servicios versionados**: cada servicio mantiene historial de precios y duraciones con franjas de vigencia
- **Disponibilidad semanal**: configuración de horarios por sucursal y profesional
- **Roles y permisos**: `PROPIETARIO`, `GERENTE_EMPRESA`, `GERENTE_SUCURSAL`, `EMPLEADO`
- **Registro de clientes por sucursal**: búsqueda por trigrama con soporte de tildes
- **Bloqueo de clientes**: cada sucursal puede bloquear clientes para impedir reservas
- **Favoritos**: los usuarios pueden guardar sucursales como favoritas
- **Reserva pública**: cada sucursal puede habilitar o deshabilitar la reserva pública
- **Notificaciones**: recordatorios de turnos por email (Brevo/Sendinblue)
- **Imágenes**: subida y gestión de logos via Cloudinary
- **Geocodificación**: resolución de direcciones y coordenadas (Nominatim)
- **Tareas programadas**: recordatorios de turnos, archivo automático de turnos (180 días), limpieza de notificaciones, expiración de tokens
- **Reset de contraseña**: por email (Brevo) y por código OTP vía móvil

---

## Requisitos previos

- Python 3.11+
- PostgreSQL 14+ con las siguientes extensiones habilitadas:

```sql
CREATE EXTENSION IF NOT EXISTS unaccent;   -- búsqueda sin tildes
CREATE EXTENSION IF NOT EXISTS pg_trgm;    -- búsqueda por similitud de texto
CREATE EXTENSION IF NOT EXISTS btree_gist; -- constraints de exclusión en disponibilidad y servicios
```

---

## Instalación

```bash
# 1. Clonar el repositorio
git clone <url-del-repo>
cd MiTurnoApp

# 2. Crear y activar entorno virtual
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con los valores correspondientes
```

---

## Variables de entorno

Crear un archivo `.env` en la raíz con las siguientes variables:

```env
# Servidor
PORT=8000
FRONTEND_URL=https://tu-frontend.com

# Base de datos
DB_URL=postgresql+psycopg2://usuario:password@localhost:5432/miturno

# JWT / Autenticación
SECRET_KEY=tu_clave_secreta
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
VERIFY_EMAIL_TOKEN_EXPIRE_HOURS=24
COOKIE_NAME=access_token
COOKIE_DOMAIN=tu-dominio.com
COOKIE_SECURE=true
COOKIE_SAMESITE=lax

# Rutas del front para emails
FRONT_VERIFICACTION_EMAIL_PATH=/verificar-email
FRONT_INVITE_EMAIL_PATH=/aceptar-invitacion
FRONT_RESET_EMAIL_PATH=/restablecer-password

# Email de envío
EMAIL=noreply@tu-dominio.com

# Gmail (alternativa a Brevo para algunos envíos)
GMAIL=tu-cuenta@gmail.com
GMAIL_PASSWORD=tu-password
GMAIL_APP_PASSWORD=tu-app-password

# Brevo / Sendinblue
SERVER_API_KEY_BREVO=tu_api_key
TEMPLATE_ID_VERIFICATION_EMAIL_USUARIO=0
TEMPLATE_ID_VERIFICATION_EMAIL_EMPRESA=0
TEMPLATE_ID_INVITE_EMAIL=0
TEMPLATE_ID_RESET_EMAIL=0
TEMPLATE_ID_TURNO_CANCELADO_EMAIL_CLIENTE=0
TEMPLATE_ID_TURNO_CANCELADO_EMAIL_EMPRESA=0

# Cloudinary
CLOUDINARY_CLOUD_NAME=tu_cloud_name
CLOUDINARY_API_KEY=tu_api_key
CLOUDINARY_API_SECRET=tu_api_secret
```

---

## Correr la aplicación en desarrollo (sin Docker)

```bash
# Iniciar el servidor de desarrollo
python main.py
# API disponible en http://localhost:8000
# Documentación Swagger en http://localhost:8000/docs
```

---

## Correr la aplicación en desarrollo (con Docker)

```bash
# Construir la imagen
docker build -t miturnoapp .

# Correr el contenedor
docker run -p 8000:8000 --env-file .env miturnoapp
```

---

## Arquitectura

### Flujo de un request

```
HTTP Request
    │
    ▼
Router (validación Pydantic + inyección de dependencias)
    │
    ├── Depends(get_current_user) → JWT desde cookie HTTP-only
    │
    ▼
CRUD (queries a DB + lógica de negocio)
    │
    ├── DomainError → register_exception_handlers → respuesta de error HTTP
    │
    ▼
Mapper (SQLAlchemy model → schema de respuesta)
    │
    ▼
Response Schema (Pydantic)
```

### Descripción de capas

| Capa | Responsabilidad |
|------|----------------|
| `routers/` | Endpoints FastAPI, validación de entrada, inyección de dependencias |
| `crud/` | Queries a la base de datos y validaciones de negocio; lanza `DomainError` ante fallos |
| `schemas/` | Modelos Pydantic para request y response |
| `mappers/` | Transforman instancias SQLAlchemy en schemas de respuesta |
| `core/models.py` | Todos los modelos ORM en un solo archivo |
| `core/config.py` | Carga de variables de entorno y configuración de Cloudinary |
| `core/autenticacion.py` | Lógica de autenticación JWT y extracción del usuario actual |
| `core/security.py` | Hash de contraseñas y generación de tokens |
| `core/exceptions.py` | Jerarquía de excepciones de dominio |
| `core/errores.py` | Definiciones de errores de negocio |
| `core/mensajes.py` | Envío de emails (Brevo y Gmail) |
| `core/constantes.py` | Constantes de la aplicación (tipos de notificación, URLs, etc.) |
| `core/timezone.py` | Manejo de zonas horarias |
| `core/auxiliares.py` | Funciones auxiliares compartidas |
| `core/database.py` | Configuración de la conexión a la base de datos |
| `core/logger.py` | Configuración del logger |
| `services/` | Tareas en background: envío de emails y SMS |
| `services/scheduler.py` | Jobs periódicos con APScheduler |
| `handlers/` | Registro de manejadores de excepciones HTTP |

---

## Modelo de datos

```
Usuario ──────────────────────────────────────────────────────────┐
    │                                                              │
    └──owns──→ Empresa ──has──→ Sucursal                          │
                   │                │                              │
          Miembro_Empresa    Miembro_Sucursal ◄────────────────────┘
          (roles:            (roles:
           PROPIETARIO,       GERENTE_SUCURSAL,
           GERENTE_EMPRESA)   EMPLEADO)

                                   Sucursal
                                       │
              ┌────────────────────────┼──────────────────────────┐
              │                        │                           │
        ServicioBase            Cliente_Sucursal                  Turno
        │          │                   │                           │
    Servicio   ExcepcionFecha   BloqueoSucursal           Notificacion
    (versión   (bloqueo de                            Estado_Turno x2
    con        fechas)                            (usuario / sucursal)
    vigencia)
        │
    Disponibilidad
    (horarios por día)

Usuario ──→ Favorito ──→ Sucursal
```

**Notas sobre el modelo:**
- `ServicioBase` agrupa versiones de un mismo servicio; `Servicio` almacena precio y duración con franjas de vigencia (`vigente_desde` / `vigente_hasta`), sin superposiciones garantizadas por `ExcludeConstraint`
- `Turno` guarda un estado independiente para el lado del usuario y para el lado de la sucursal
- `Cliente_Sucursal` es el registro de clientes propio de cada sucursal, separado del `Usuario` del sistema; tiene campo `busqueda_texto` para búsqueda por trigrama
- `ExcepcionFechaServicio` define rangos de fechas bloqueadas para un servicio (sin superposición garantizada por `ExcludeConstraint`)
- `BloqueoSucursal` permite a cada sucursal bloquear clientes individualmente
- `Sucursal` tiene un campo `busqueda_texto` generado automáticamente (via eventos SQLAlchemy) para búsqueda por trigrama
- `Blacklist` almacena los `jti` de tokens revocados al hacer logout
- `OTPCode` almacena códigos de un solo uso para reset de contraseña por móvil

---

## Autenticación

- Los tokens JWT se almacenan en cookies HTTP-only
- Cada token tiene un `jti` (JWT ID) único que permite revocación precisa
- Al hacer logout el `jti` se agrega a la tabla `token_blacklist`
- Los emails se normalizan antes de almacenarse para manejar aliases de Gmail, Outlook, Yahoo y otros proveedores

---

## Stack tecnológico

| Tecnología | Versión | Uso |
|-----------|---------|-----|
| FastAPI | 0.116.1 | Framework web |
| Uvicorn | 0.35.0 | Servidor ASGI |
| SQLAlchemy | 2.0.43 | ORM |
| PostgreSQL | 14+ | Base de datos |
| psycopg2-binary | 2.9.11 | Driver PostgreSQL síncrono |
| asyncpg | 0.31.0 | Driver PostgreSQL asíncrono |
| Pydantic | 2.11.7 | Validación de datos |
| python-jose | 3.5.0 | JWT |
| passlib + bcrypt | 1.7.4 / 4.0.1 | Hash de contraseñas |
| APScheduler | 3.11.0 | Tareas programadas |
| Cloudinary | 1.44.1 | Almacenamiento de imágenes |
| Brevo (sib-api-v3-sdk) | 7.6.0 | Envío de emails |
| Pillow | 12.0.0 | Procesamiento de imágenes |
| Requests | 2.32.5 | HTTP client (geocodificación) |
| python-dotenv | 1.1.1 | Carga de variables de entorno |
| python-multipart | 0.0.22 | Subida de archivos (logos) |
