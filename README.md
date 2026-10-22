# sgi-cs
Sistema de gestión institucional inteligente para el centro de simulación.

Backend con Django, Django REST Framework y PostgreSQL.

El desarrollo del backend se organiza en cuatro etapas:

1. **Base del sistema:** proyecto, modelos, relaciones, migraciones, admin y primera consulta de disponibilidad. Es el trabajo inicial existente.
2. **Acceso y gestión por API:** autenticación, roles, usuarios, aulas, categorías, equipamiento y estados. Implementada en esta entrega.
3. **Operación de reservas:** actividades, responsables, participantes estimados, asignación de aulas y equipos, validaciones, confirmación/cancelación y agenda.
4. **Integración y gestión inteligente:** importación CSV/Excel, indicadores, alertas, contratos para BI/IA, pruebas integrales y preparación del despliegue.

La etapa 2 permite al frontend empezar a trabajar con usuarios y datos reales. La etapa 3 deberá validar las reservas en el servidor, dentro de transacciones; consultar disponibilidad no garantiza una asignación ante solicitudes simultáneas.

Consultá [la guía de la etapa 2](backend/docs/ETAPA_2.md) para ver el alcance, los permisos, el contrato de la API, ejemplos y los siguientes pasos.

## Puesta en marcha (PowerShell)

Requisitos: Python 3.13 y una base PostgreSQL local creada para el proyecto.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Editá `.env` con tus credenciales PostgreSQL y una clave propia. Podés generar la clave con:

```powershell
.\.venv\Scripts\python.exe -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Luego:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py runserver
```

`migrate` crea los roles `ADMIN` y `COORDINACION`; `createsuperuser` asigna `ADMIN` y solicita los datos personales. No se incluyen cuentas ni contraseñas predeterminadas.

API: `http://127.0.0.1:8000/api/`. Administración de Django: `http://127.0.0.1:8000/admin/`.

## Verificación

Desde `backend`, para ejecutar las pruebas sin un servidor PostgreSQL:

```powershell
.\.venv\Scripts\python.exe manage.py test --settings=config.test_settings
.\.venv\Scripts\python.exe manage.py check --settings=config.test_settings
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run --settings=config.test_settings
```

Las pruebas usan SQLite en memoria, una base independiente que se destruye al terminar. La configuración normal conserva PostgreSQL. Para probar también con PostgreSQL configurado, ejecutá `python manage.py test`; el usuario de base de datos debe poder crear la base de pruebas.
