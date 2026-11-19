// Datos de ejemplo. Reemplazar por llamadas a la API (ver src/api/README.md).
export const HOY = 2; // 0 = lunes … 4 = viernes
export const DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes'];
export const FERIADOS = [4]; // viernes
export const AREAS = ['FTS', 'Formación Profesional', 'Educación Superior', 'Escuelas técnicas', 'Externo'];

export const ESPACIOS = [
  { id: 'e1', nombre: 'SUM', tipo: 'Salón de usos múltiples', cap: 80, piso: 'PB', sims: [], estado: 'Disponible', car: ['Proyector', 'Sonido', 'Accesible'] },
  { id: 'e2', nombre: 'Lab. de Informática', tipo: 'Laboratorio', cap: 30, piso: '1', sims: [], estado: 'Disponible', car: ['30 PC', 'Proyector'] },
  { id: 'e3', nombre: 'Aula 1', tipo: 'Aula', cap: 25, piso: '1', sims: [], estado: 'Disponible', car: ['Pizarra', 'TV'] },
  { id: 'e4', nombre: 'Aula 2', tipo: 'Aula', cap: 25, piso: '1', sims: [], estado: 'Disponible', car: ['Pizarra'] },
  { id: 'e5', nombre: 'Aula de Robótica', tipo: 'Aula taller', cap: 25, piso: '2', sims: [], estado: 'Disponible', car: ['Mesas de trabajo'] },
  { id: 'e6', nombre: 'Sala de Simulación Clínica', tipo: 'Sala de simulación', cap: 12, piso: '2', sims: [{ n: 'Maniquí de RCP', c: 4, fijo: true }], estado: 'Disponible', car: ['Cámaras'] },
  { id: 'e7', nombre: 'Aula Maker', tipo: 'Aula taller', cap: 20, piso: '2', sims: [], estado: 'Mantenimiento', desde: '28/9', hasta: '5/10', motivo: 'Calibración de impresoras 3D', car: ['Impresoras 3D'] },
];

export const EQUIPOS = [
  { id: 'q1', n: 'Notebook', cat: 'Informática', cant: 24, fijo: false, critico: false, ubic: 'Depósito', estado: 'Disponible' },
  { id: 'q2', n: 'Proyector portátil', cat: 'Audiovisual', cant: 3, fijo: false, critico: false, ubic: 'Depósito', estado: 'Disponible' },
  { id: 'q3', n: 'Micrófono inalámbrico', cat: 'Audiovisual', cant: 4, fijo: false, critico: false, ubic: 'SUM', estado: 'Disponible' },
  { id: 'q4', n: 'Kit de robótica', cat: 'Robótica', cant: 12, fijo: true, critico: true, ubic: 'Aula de Robótica', estado: 'Disponible' },
  { id: 'q5', n: 'Maniquí de RCP', cat: 'Simulación', cant: 4, fijo: true, critico: true, ubic: 'Sala de Simulación Clínica', estado: 'Disponible' },
  { id: 'q6', n: 'Silla', cat: 'Mobiliario', cant: 60, fijo: false, critico: false, ubic: 'Depósito', estado: 'Disponible' },
  { id: 'q7', n: 'Impresora 3D', cat: 'Maker', cant: 4, fijo: true, critico: true, ubic: 'Aula Maker', estado: 'Mantenimiento' },
];

export const ACTIVIDADES = [
  { id: 'a1', titulo: 'Jornada de RCP', tipo: 'Práctica', sol: 'FTS', sp: 'e6', dia: 1, ini: 9, fin: 12, insc: 12, resp: 'Lic. Sergio Ibarra', codigo: '4821', personas: [], reg: false, cancelada: false },
  { id: 'a2', titulo: 'Charla de orientación', tipo: 'Charla', sol: 'Educación Superior', sp: 'e1', dia: 2, ini: 10, fin: 12, insc: 80, resp: 'Prof. Ana Ruiz', codigo: '', personas: [], reg: false, cancelada: false },
  { id: 'a4', titulo: 'Práctica de primeros auxilios', tipo: 'Práctica', sol: 'FTS', sp: 'e1', dia: 2, ini: 11, fin: 13, insc: 30, resp: 'Lic. Sergio Ibarra', codigo: '', personas: [], reg: false, cancelada: false },
  { id: 'a3', titulo: 'Taller de robótica', tipo: 'Taller', sol: 'Escuelas técnicas', sp: 'e5', dia: 3, ini: 14, fin: 17, insc: 20, resp: 'Ing. Pablo Díaz', codigo: '', personas: [], reg: false, cancelada: false },
];

export const PEDIDOS = [
  { id: 'p9', canal: 'Mail', sol: 'Formación Profesional', titulo: 'Capacitación en planillas de cálculo', tipo: 'Capacitación', dia: 3, ini: 14, fin: 17, cupo: 20, resp: 'Lic. Marta Gómez', req: [{ n: 'Notebook', cant: 20 }], estado: 'Por asignar' },
  { id: 'p3', canal: 'Formulario', sol: 'FTS', titulo: 'Práctica de RCP avanzada', tipo: 'Práctica', dia: 1, ini: 10, fin: 12, cupo: 10, resp: 'Lic. Sergio Ibarra', req: [{ n: 'Maniquí de RCP', cant: 4 }], estado: 'Por asignar' },
];

export const USUARIOS = [
  { id: 'u1', nombre: 'Laura Méndez', mail: 'lmendez@buenosaires.gob.ar', rol: 'Administrador', activo: true },
  { id: 'u2', nombre: 'Diego Paz', mail: 'dpaz@buenosaires.gob.ar', rol: 'Coordinación', activo: true },
];
