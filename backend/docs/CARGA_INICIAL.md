# Carga inicial de aulas y equipamiento

Se incorporó una carga de catálogos desde CSV y Excel XLSX, con validación previa,
errores por fila y confirmación explícita. La implementación está separada en
`reportes/importaciones/` y utiliza los modelos y serializers existentes de
`espacios`, sin modificarlos. Sus rutas se agregan en `reportes/urls.py`.

Este módulo no cambia reservas, participantes, stock de registros existentes,
permisos generales ni la configuración o código del frontend. Tampoco agrega
modelos o migraciones. Los archivos no se conservan después de la petición.

## Instalación

Desde `backend`:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-importacion.txt
```

Ese archivo incluye las dependencias base y agrega `openpyxl` y `defusedxml` para
Excel. `requirements.txt` no se modifica. CSV funciona con las dependencias base;
si falta el lector Excel, una carga XLSX devuelve 503 con la indicación de instalarlo.

Si el servidor Django ya estaba iniciado sin recarga automática, reiniciarlo para
que lea las rutas nuevas.

## Flujo de uso

1. Descargar la plantilla del catálogo que se va a cargar.
2. Completar los datos. Para equipamiento, las categorías y aulas referenciadas
   deben existir previamente.
3. Enviar el archivo sin `confirmar`, o con `confirmar=false`, para validar.
4. Corregir las filas señaladas hasta que el informe no tenga errores.
5. Enviar el archivo nuevamente con `confirmar=true` para crear las altas.

La confirmación vuelve a validar contra la base actual; una validación anterior
no reserva nombres ni garantiza que los catálogos no cambien entre peticiones.

## API

Todos los endpoints requieren `Authorization: Token <token>` y un administrador
activo o superusuario. Coordinación y Solicitante no pueden importar. Sin token
se responde 401; sin permiso, 403. Los permisos se declaran en las vistas del
módulo y no alteran la política global de Abel.

| Método y ruta | Uso |
| --- | --- |
| `GET /api/importaciones/aulas/` | Columnas admitidas y límites de aulas. |
| `POST /api/importaciones/aulas/` | Validar o confirmar carga de aulas. |
| `GET /api/importaciones/equipamientos/` | Columnas admitidas y límites de equipos. |
| `POST /api/importaciones/equipamientos/` | Validar o confirmar carga de equipos. |
| `GET /api/importaciones/plantillas/aulas/` | Descargar CSV con encabezados de aulas. |
| `GET /api/importaciones/plantillas/equipamientos/` | Descargar CSV con encabezados de equipos. |

POST utiliza `multipart/form-data` con `archivo` y `confirmar` opcional. No admite
otros campos. No hay PUT, PATCH ni DELETE.

Ejemplo con `curl.exe` en PowerShell; reemplazar el token y la ruta del archivo:

```powershell
$tokenImportacion = '<token>'
curl.exe -H "Authorization: Token $tokenImportacion" -F 'archivo=@aulas.csv' -F 'confirmar=false' 'http://127.0.0.1:8000/api/importaciones/aulas/'
curl.exe -H "Authorization: Token $tokenImportacion" -F 'archivo=@aulas.csv' -F 'confirmar=true' 'http://127.0.0.1:8000/api/importaciones/aulas/'
```

## Columnas

### Aulas

Obligatorias: `nombre`, `capacidad`.

Opcionales: `tipo`, `ubicacion`, `caracteristicas`, `estado`, `sillas`, `mesas`,
`color`. Un valor opcional vacío se omite; en una alta se aplican los valores
predeterminados del modelo.

```csv
nombre,capacidad,tipo,ubicacion,estado,sillas,mesas
Laboratorio inicial,20,LABORATORIO,Planta baja,DISPONIBLE,20,5
Aula inicial,30,AULA,Primer piso,DISPONIBLE,30,6
```

`tipo`: AULA, LABORATORIO, TALLER u OTRO. `estado`: DISPONIBLE, MANTENIMIENTO o
FUERA_SERVICIO. Capacidad mínima 1; sillas y mesas admiten 0.

### Equipamiento

Obligatorias: `nombre`, `categoria`, `cantidad`, `trasladable`.

Opcionales: `aula`, `estado`. `categoria` y `aula` son **nombres exactos** del
catálogo, no identificadores numéricos. No se crean categorías o aulas implícitamente.
La cantidad mínima es 1. Un equipo fijo necesita un aula existente.

```csv
nombre,categoria,cantidad,trasladable,aula,estado
Notebooks iniciales,Tecnología,10,true,,DISPONIBLE
Proyector inicial,Tecnología,1,false,Aula inicial,DISPONIBLE
```

Este ejemplo requiere que ya exista la categoría `Tecnología` y que se haya
cargado `Aula inicial`. Los booleanos admiten true/false, 1/0 y sí/no, sin
distinción entre mayúsculas y minúsculas.

Los encabezados se normalizan: `Categoría` se interpreta como `categoria`, por
ejemplo. Los valores de nombres conservan mayúsculas, acentos y signos; se quitan
solo espacios externos. Las relaciones y la identidad se comparan exactamente.

## Política de duplicados y atomicidad

La carga solo crea registros nuevos:

- Aula existente: se identifica por `nombre`.
- Equipo existente: se identifica por nombre, categoría, aula y condición trasladable.
- Si un registro existente coincide con los campos proporcionados, se omite y se
  informa su ID; repetir el mismo archivo no duplica ni suma cantidades.
- Si los campos proporcionados difieren, se marca error. No se cambia capacidad,
  estado ni stock. Para editar se utiliza la gestión normal del catálogo.
- Si la misma identidad aparece dos veces dentro del archivo, ambas filas se
  marcan como duplicadas. Si hay varias coincidencias en la base, se pide revisar
  el catálogo en vez de escoger una arbitrariamente.

Se valida el lote completo antes de crear. Una fila con errores impide todas las
altas del archivo. La confirmación se realiza dentro de una transacción; un fallo
de integridad durante el guardado revierte también las filas guardadas antes del
fallo. En PostgreSQL las cargas de este módulo se serializan con un bloqueo de
transacción propio; no se cambian las restricciones de los catálogos ni los otros
servicios que los escriben.

## Informes y respuestas

Respuesta de ejemplo al validar un archivo con una fila nueva:

```json
{
  "recurso": "aulas",
  "modo": "validacion",
  "resumen": {"filas": 1, "por_crear": 1, "omitidas": 0, "creadas": 0, "errores": 0},
  "filas": [{"fila": 2, "accion": "crear"}]
}
```

Cada fila tiene `accion` crear, omitir o error. `id` aparece para registros
omitidos y altas confirmadas. `errores` contiene mensajes por campo cuando
corresponde. `fila` señala la fila física del archivo, contando el encabezado.

`por_crear` es la cantidad de altas propuestas en el plan validado, no un saldo:
al confirmar correctamente puede coincidir con `creadas`. Si hay errores,
`creadas` siempre es cero y ninguna de las altas propuestas se guarda.

- 200: validación correcta o confirmación sin altas porque todo ya existía.
- 201: confirmación con registros creados.
- 400: archivo, parámetros o filas inválidas. Las filas inválidas incluyen el
  informe; los problemas generales del archivo se informan en `archivo`.
- 409: conflicto de integridad durante el guardado, con rollback completo;
  volver a validar el archivo.
- 503: dependencia de Excel no instalada.

## Formatos y límites

- CSV UTF-8, con o sin BOM, separado por coma o punto y coma. Se respetan comillas
  y saltos de línea dentro de una celda.
- XLSX de una sola hoja, sin fórmulas ni celdas con errores. Los datos deben
  quedar dentro de las primeras 1001 filas físicas: encabezado más 1000 filas.
- Máximo 2 MiB por archivo, 1000 filas con datos y 16 columnas. Filas vacías se omiten.
- Se rechazan encabezados vacíos, repetidos, desconocidos o requeridos faltantes,
  archivos dañados y filas con columnas desajustadas.
- Se acota además el contenido interno expandido del XLSX. No se extrae a disco.
- El formato antiguo `.xls` y los libros con macros `.xlsm` no están soportados.

## Consola y ejecución por scripts

Se puede usar la misma validación y transacción desde una terminal, sin frontend:

```powershell
# Solo validar, sin modificar datos:
.\.venv\Scripts\python.exe manage.py importar_catalogo aulas .\aulas.csv

# Confirmar las altas:
.\.venv\Scripts\python.exe manage.py importar_catalogo aulas .\aulas.csv --confirmar
.\.venv\Scripts\python.exe manage.py importar_catalogo equipamientos .\equipos.xlsx --confirmar
```

La salida es el mismo informe JSON. Si se encuentran errores, el comando termina
con un error y no deja altas parciales. Este comando usa las credenciales de base
del entorno de Django y debe ejecutarlo quien administre el backend. No instala
tareas programadas ni modifica procesos de reservas en segundo plano.

## Verificación

```powershell
.\.venv\Scripts\python.exe manage.py test reportes.importaciones reportes.test_importaciones_api --settings=config.test_settings
.\.venv\Scripts\python.exe manage.py test reportes.importaciones reportes.test_importaciones_api --noinput
```

Resultado: 44 pruebas de importación aprobadas con SQLite y PostgreSQL. Junto con
las 34 de consulta inteligente, se verificaron 78 pruebas de los módulos nuevos.
Se cubren permisos, plantillas, CSV/XLSX, formato y límites, validación sin
escrituras, duplicados, reimportación, referencias, rollback y comando de consola.
No es una declaración sobre los cambios que el resto del equipo desarrolla en
paralelo.

Para detalles del lector Excel se consultó la [documentación oficial de openpyxl](https://openpyxl.readthedocs.io/en/stable/api/openpyxl.reader.excel.html).
