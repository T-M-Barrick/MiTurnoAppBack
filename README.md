# Backend – MiTurno  
API REST para la gestión de turnos

Este repositorio contiene el backend del proyecto **MiTurno**, desarrollado con **FastAPI (Python)** y diseñado para brindar los servicios que consumen las interfaces del frontend del proyecto.

---

## Tecnologías

- Python  
- FastAPI  
- Uvicorn (servidor ASGI)  
- Base de datos relacional (configurable)  
- Autenticación JWT  

---

## Estructura del proyecto

```text
MiTurno/
├── core/
│   └── ... (configuración y lógica central)
├── routers/
│   └── ... (endpoints agrupados por módulo)
├── main.py
├── requirements.txt
├── Dockerfile
├── seed.py
└── .gitignore
```
---

## Requisitos
- Python 3.8+
- Dependencias del proyecto (definidas en requirements.txt)
- Base de datos configurada (MySQL, PostgreSQL u otra compatible)

---

## Instalación
1. Clonar el repositorio:

```bash 
git clone https://github.com/T-M-Barrick/MiTurno.git
cd MiTurno
```


2. Crear y activar un entorno virtual:

```bash
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows
```

3. Instalar dependencias:
```bash
pip install -r requirements.txt
```

4. Configurar variables de entorno (si aplica):

- SECRET_KEY para JWT
- Parámetros de conexión de la base de datos

---

## Ejecutar la API

```bash
Con Uvicorn
uvicorn main:app --reload
```
La API quedará disponible en: http://localhost:8000

---

## Endpoints principales
### Autenticación
- POST /auth/signup – Registrar nuevo usuario
- POST /auth/login – Iniciar sesión y obtener token JWT

### Usuarios
- GET /users/me – Obtener perfil del usuario autenticado
- PATCH /users/me – Editar perfil
- DELETE /users/me – Eliminar cuenta

### Turnos
- POST /turnos – Crear un turno

- GET /turnos – Listar turnos

- PATCH /turnos/{id} – Actualizar estado/turno

- DELETE /turnos/{id} – Eliminar turno

### Empresas y servicios
- GET /empresas – Listar empresas

- POST /empresas – Crear empresa (según rol)

- PATCH /empresas/{id} – Editar empresa

- GET /servicios – Listar servicios

- POST /servicios – Crear servicio

- PATCH /servicios/{id} – Editar servicio

---

## Seguridad
La API utiliza JSON Web Tokens (JWT) para la autenticación y autorización de los usuarios.
El token se envía en la cabecera Authorization: Bearer <token>.

---

## Migraciones y base de datos
- seed.py contiene datos de prueba o inicialización
- La configuración de la base de datos está en módulos dentro de core/

---

## Pruebas
- Se puede probar la API usando herramientas como:

- Postman
- Insomnia
- Swagger UI (FastAPI incluye documentación automática en /docs)
- Redoc (en /redoc)

---

## Deployment
Este backend se puede desplegar usando:

- Servidores compatibles ASGI
- Contenedores Docker (el proyecto incluye Dockerfile)
- Plataformas como Render, Railway o Heroku

--- 

## Metodología de trabajo

Se utilizó una metodología ágil basada en SCRUM, con apoyo de tableros tipo Kanban en Trello para la organización y seguimiento de tareas.

---

## Requisitos del sistema

- Navegador web moderno
- Conexión a Internet
- Compatible con PC y dispositivos móviles
- No requiere hardware especializado

---

## Futuras mejoras

- Integración de pagos en línea

- Notificaciones automáticas de turnos

- Aplicación móvil

- Reportes y estadísticas para empresas

---

## Contexto académico

Proyecto desarrollado en el marco de la materia Práctica Profesional Supervisada, integrando conocimientos técnicos y metodológicos adquiridos durante la carrera.

## Autores

Proyecto desarrollado por el equipo de MiTurno. <br>

Estudiantes:<br>

Lucas Conte (Diseño)

Fiamma Micheloni (Diseño)

Eduardo Morales (Backend)

Agustina Del Castillo (Frontend)

Priscila Ohannecian (Frontend)

Tomás Rossi (Backend)


## Licencia

*Proyecto académico – uso educativo.*
