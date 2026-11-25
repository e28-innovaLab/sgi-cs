# SIGES - Sistema de Gestión Institucional Inteligente

Este proyecto forma parte del trabajo colaborativo de InnovaLab, para el desarrollo del Sistema de Gestión Institucional Inteligente del Centro de Simulación.

Permite gestionar espacios, reservas, recursos y equipos del Centro de Simulación. Está compuesto por una aplicación web frontend y un backend que administra la lógica del sistema y el acceso a los datos.


## Estructura del repositorio

El repositorio se organiza en dos módulos principales:

```text
sgi-cs/
├── backend/
│   └── Código del servidor y API
├── frontend/
│   └── Código de la aplicación web
└── README.md
```


## Tecnologías utilizadas

### Frontend

- React
- JavaScript
- HTML
- CSS
- Vite

### Backend

- Python 3.13
- Django
- Django REST Framework
- PostgreSQL


## Funcionalidades

### Frontend

La aplicación web cuenta con las siguientes funcionalidades:

- Inicio de sesión.
- Panel principal de gestión.
- Visualización de espacios.
- Gestión de reservas.
- Gestión de recursos y equipos.
- Navegación entre módulos.

### Backend

El backend proporciona una API para gestionar la información y las operaciones del sistema.

Entre sus funcionalidades se encuentran:

- Autenticación y gestión de usuarios.
- Administración de roles y permisos.
- Gestión de aulas y espacios.
- Administración de categorías y equipamiento.
- Gestión de reservas y sus estados.
- Asociación de usuarios y participantes a las reservas.
- Validaciones de fechas, horarios y disponibilidad.
- Asignación de aulas y equipos.
- Gestión de asistencia de participantes.
- Automatización de estados de reservas según sus horarios.

Para conocer más detalles sobre la API, sus permisos y sus funcionalidades, consultá la documentación disponible en `backend/docs/`.

Los endpoints de indicadores, las reglas de alertas y la consolidación histórica
se describen en [Reportes y alertas](backend/docs/REPORTES_Y_ALERTAS.md).


## Instalación y ejecución

### Backend

Requisitos:

- Python 3.13.
- PostgreSQL instalado y funcionando.
- Una base de datos PostgreSQL creada para el proyecto.

Desde la raíz del repositorio, ejecutá en PowerShell:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Configurá el archivo `.env` con las credenciales de PostgreSQL y una clave secreta propia.

Podés generar una clave secreta ejecutando:

```powershell
.\.venv\Scripts\python.exe -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Luego ejecutá las migraciones y creá un superusuario:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py createsuperuser
```

Para iniciar el servidor de desarrollo:

```powershell
.\.venv\Scripts\python.exe manage.py runserver
```

El comando `migrate` crea los roles iniciales `ADMIN` y `COORDINACION`. El comando `createsuperuser` permite crear una cuenta administradora con el rol `ADMIN`.

No se incluyen cuentas ni contraseñas predeterminadas.

Direcciones disponibles:

- API: http://127.0.0.1:8000/api/
- Administración de Django: http://127.0.0.1:8000/admin/


### Frontend

Requisitos:

- Node.js.
- npm.

Desde la raíz del repositorio, ejecutá:

```bash
cd frontend
npm install
npm run dev
```

Vite iniciará el servidor de desarrollo y mostrará en la terminal la dirección local para acceder a la aplicación web.


## Verificación del backend

Para ejecutar las pruebas y verificaciones del backend, ingresá primero a la carpeta `backend`.

En PowerShell:

```powershell
.\.venv\Scripts\python.exe manage.py test --settings=config.test_settings
.\.venv\Scripts\python.exe manage.py check --settings=config.test_settings
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run --settings=config.test_settings
```

Las pruebas utilizan SQLite en memoria, una base de datos independiente que se destruye al finalizar. La configuración habitual del proyecto utiliza PostgreSQL.

Para ejecutar las pruebas utilizando PostgreSQL, podés ejecutar:

```powershell
python manage.py test
```

En ese caso, el usuario de base de datos debe tener permisos para crear la base de datos de pruebas.
