"""Lectura acotada de archivos de carga; no consulta ni modifica la base."""

import csv
from io import BytesIO, StringIO
from pathlib import Path
import re
import unicodedata
from zipfile import BadZipFile, ZipFile
from xml.etree import ElementTree

from .schemas import COLUMNAS


MAX_BYTES = 2 * 1024 * 1024
MAX_FILAS = 1000
MAX_COLUMNAS = 16
MAX_BYTES_EXPANDIDOS = 20 * 1024 * 1024
MAX_ENTRADAS_ZIP = 1000


class ArchivoInvalido(ValueError):
    """El archivo no puede interpretarse sin ambigüedad."""


class DependenciaExcelNoDisponible(ArchivoInvalido):
    """La instalación admite CSV pero todavía no incluye el lector Excel."""


def _vacio(valor):
    return valor is None or isinstance(valor, str) and not valor.strip()


def _normalizar_encabezado(valor):
    if not isinstance(valor, str) or not valor.strip():
        raise ArchivoInvalido('Todos los encabezados deben tener un nombre.')
    if len(valor) > 100:
        raise ArchivoInvalido('Los nombres de las columnas no pueden superar 100 caracteres.')
    texto = ''.join(c for c in unicodedata.normalize('NFKD', valor.strip().lower())
                    if not unicodedata.combining(c))
    return re.sub(r'\s+', '_', texto)


def _encabezados(valores, tipo):
    if not valores or len(valores) > MAX_COLUMNAS:
        raise ArchivoInvalido(f'El archivo debe tener entre 1 y {MAX_COLUMNAS} columnas.')
    nombres = [_normalizar_encabezado(valor) for valor in valores]
    if len(set(nombres)) != len(nombres):
        raise ArchivoInvalido('Hay encabezados repetidos.')
    esquema = COLUMNAS[tipo]
    faltantes = set(esquema['obligatorias']) - set(nombres)
    desconocidas = set(nombres) - set(esquema['obligatorias']) - set(esquema['opcionales'])
    if faltantes:
        raise ArchivoInvalido('Faltan columnas obligatorias: ' + ', '.join(sorted(faltantes)) + '.')
    if desconocidas:
        raise ArchivoInvalido('Columnas no admitidas: ' + ', '.join(sorted(desconocidas)) + '.')
    return nombres


def _agregar(resultado, numero, valores, encabezados, tipo):
    if all(_vacio(valor) for valor in valores):
        return
    if len(valores) != len(encabezados):
        raise ArchivoInvalido(f'La fila {numero} no tiene la misma cantidad de columnas que el encabezado.')
    if len(resultado) >= MAX_FILAS:
        raise ArchivoInvalido(f'El máximo es de {MAX_FILAS} filas de datos.')
    opcionales = set(COLUMNAS[tipo]['opcionales'])
    datos = {}
    for nombre, valor in zip(encabezados, valores):
        if isinstance(valor, str):
            valor = valor.strip()
        if nombre in opcionales and _vacio(valor):
            continue
        datos[nombre] = valor
    resultado.append({'fila': numero, 'datos': datos})


def _leer_csv(contenido, tipo):
    try:
        texto = contenido.decode('utf-8-sig')
    except UnicodeDecodeError as exc:
        raise ArchivoInvalido('Guardá el CSV en UTF-8, con o sin BOM.') from exc
    if '\x00' in texto:
        raise ArchivoInvalido('El CSV contiene caracteres nulos o una codificación no admitida.')
    try:
        muestra = texto[:8192]
        try:
            separador = csv.Sniffer().sniff(muestra, delimiters=',;').delimiter
        except csv.Error:
            # Permite informar columnas faltantes en vez de un error opaco del sniffer.
            separador = ';' if muestra.splitlines() and ';' in muestra.splitlines()[0] else ','
        lector = csv.reader(StringIO(texto, newline=''), delimiter=separador, strict=True)
        encabezados = _encabezados(next(lector, []), tipo)
        resultado = []
        while True:
            numero = lector.line_num + 1
            valores = next(lector, None)
            if valores is None:
                break
            _agregar(resultado, numero, valores, encabezados, tipo)
        return resultado
    except csv.Error as exc:
        raise ArchivoInvalido('El CSV está mal formado; revisá separadores, comillas y tamaño de sus celdas.') from exc


def _numero_columna(referencia):
    if len(referencia) > 16:
        raise ArchivoInvalido('El Excel contiene referencias de celdas fuera de rango.')
    match = re.fullmatch(r'([A-Za-z]+)[1-9][0-9]*', referencia)
    if not match:
        raise ArchivoInvalido('El Excel contiene referencias de celdas inválidas.')
    numero = 0
    for caracter in match.group(1).upper():
        numero = numero * 26 + ord(caracter) - ord('A') + 1
    return numero


def _validar_zip(contenido):
    try:
        with ZipFile(BytesIO(contenido)) as archivo:
            entradas = archivo.infolist()
            if len(entradas) > MAX_ENTRADAS_ZIP:
                raise ArchivoInvalido('El Excel contiene demasiadas partes internas.')
            if sum(e.file_size for e in entradas) > MAX_BYTES_EXPANDIDOS:
                raise ArchivoInvalido('El contenido expandido del Excel supera los 20 MiB.')
            if any(e.flag_bits & 1 for e in entradas):
                raise ArchivoInvalido('No se admiten archivos Excel cifrados.')
            for entrada in entradas:
                if not entrada.filename.lower().endswith(('.xml', '.rels')):
                    continue
                xml = archivo.read(entrada)
                inspeccion = xml.replace(b'\x00', b'').upper()
                if b'<!DOCTYPE' in inspeccion or b'<!ENTITY' in inspeccion:
                    raise ArchivoInvalido('El Excel contiene declaraciones XML no admitidas.')
                if re.fullmatch(r'xl/worksheets/[^/]+\.xml', entrada.filename):
                    _validar_filas_xml(xml)
    except ArchivoInvalido:
        raise
    except Exception as exc:
        raise ArchivoInvalido('El archivo no es un Excel XLSX válido o está dañado.') from exc


def _validar_filas_xml(xml):
    """Acota filas dispersas sin confiar en las dimensiones declaradas del libro."""
    try:
        contador = 0
        for _, elemento in ElementTree.iterparse(BytesIO(xml), events=['end']):
            etiqueta = elemento.tag.rsplit('}', 1)[-1]
            if etiqueta == 'c':
                if _numero_columna(elemento.attrib.get('r', '')) > MAX_COLUMNAS:
                    raise ArchivoInvalido(f'El Excel supera las {MAX_COLUMNAS} columnas admitidas.')
            elif etiqueta == 'row':
                contador += 1
                numero = int(elemento.attrib.get('r', contador))
                if not 1 <= numero <= MAX_FILAS + 1 or contador > MAX_FILAS + 1:
                    raise ArchivoInvalido(f'El Excel debe quedar dentro de las primeras {MAX_FILAS + 1} filas físicas.')
            elemento.clear()
    except (ElementTree.ParseError, TypeError, ValueError) as exc:
        if isinstance(exc, ArchivoInvalido):
            raise
        raise ArchivoInvalido('La hoja Excel contiene XML o posiciones de fila inválidas.') from exc


def _leer_xlsx(contenido, tipo):
    try:
        from openpyxl import load_workbook
    except ImportError as exc:
        raise DependenciaExcelNoDisponible('Instalá requirements-importacion.txt para habilitar archivos XLSX.') from exc
    _validar_zip(contenido)
    libro = None
    try:
        libro = load_workbook(BytesIO(contenido), read_only=True, data_only=False, keep_links=False)
        if len(libro.worksheets) != 1:
            raise ArchivoInvalido('El Excel debe contener una sola hoja.')
        hoja = libro.worksheets[0]
        hoja.reset_dimensions()
        filas = hoja.iter_rows(max_row=MAX_FILAS + 1, max_col=MAX_COLUMNAS + 1)
        resultado, encabezados = [], None
        for numero, celdas in enumerate(filas, start=1):
            for celda in celdas:
                if celda.data_type == 'f':
                    raise ArchivoInvalido(f'La fila {numero} contiene fórmulas; importá solo valores.')
                if celda.data_type == 'e':
                    raise ArchivoInvalido(f'La fila {numero} contiene errores de Excel.')
            valores = [celda.value for celda in celdas]
            while valores and valores[-1] is None:
                valores.pop()
            if encabezados is None:
                encabezados = _encabezados(valores, tipo)
            else:
                if len(valores) > len(encabezados):
                    raise ArchivoInvalido(f'La fila {numero} tiene datos fuera de las columnas del encabezado.')
                valores.extend([None] * (len(encabezados) - len(valores)))
                _agregar(resultado, numero, valores, encabezados, tipo)
        return resultado
    except ArchivoInvalido:
        raise
    except Exception as exc:
        raise ArchivoInvalido('El archivo no es un Excel XLSX válido o está dañado.') from exc
    finally:
        if libro is not None:
            libro.close()


def leer_archivo(archivo, tipo):
    if tipo not in COLUMNAS:
        raise ArchivoInvalido('Tipo de catálogo no admitido.')
    extension = Path(str(getattr(archivo, 'name', ''))).suffix.lower()
    if extension not in ('.csv', '.xlsx'):
        raise ArchivoInvalido('Solo se admiten archivos .csv y .xlsx; .xls no está soportado.')
    contenido = archivo.read(MAX_BYTES + 1)
    if not isinstance(contenido, bytes):
        raise ArchivoInvalido('El archivo debe enviarse en formato binario.')
    if not contenido:
        raise ArchivoInvalido('El archivo está vacío.')
    if len(contenido) > MAX_BYTES:
        raise ArchivoInvalido('El archivo supera el límite de 2 MiB.')
    resultado = _leer_csv(contenido, tipo) if extension == '.csv' else _leer_xlsx(contenido, tipo)
    if not resultado:
        raise ArchivoInvalido('El archivo no contiene filas de datos.')
    return resultado
