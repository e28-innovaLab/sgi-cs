
import './calendario.css';
import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useStore } from '../store.jsx';
import { DIAS, FERIADOS, HOY } from '../data/mocks.js';
import { evaluar } from '../logic/disponibilidad.js';
import { rango, seSuperpone } from '../logic/formato.js';
import Badge from '../components/badge.jsx';
import Button from '../components/button.jsx';
import Aviso from '../components/aviso.jsx';
import Icon from '../components/Icon.jsx';

const TIPOS = ['Práctica', 'Charla', 'Taller', 'Capacitación'];
const HORAS = Array.from({ length: 12 }, (_, i) => 8 + i);

const hoyReal = new Date();

function sumarDias(fecha, cantidad) {
    const nueva = new Date(fecha);
    nueva.setDate(nueva.getDate() + cantidad);
    return nueva;
}

function claveFecha(fecha) {
    const y = fecha.getFullYear();
    const m = String(fecha.getMonth() + 1).padStart(2, '0');
    const d = String(fecha.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
}

function lunesDe(fecha) {
    const dia = (fecha.getDay() + 6) % 7;
    return sumarDias(fecha, -dia);
}

function fechaActividad(a) {
    if (a.fecha) {
        const partes = String(a.fecha).slice(0, 10).split('-');

        if (partes.length === 3) {
            return new Date(
                +partes[0],
                +partes[1] - 1,
                +partes[2]
            );
        }
    }

    return sumarDias(lunesDe(hoyReal), Number(a.dia));
}

function esMismoDia(a, b) {
    return claveFecha(a) === claveFecha(b);
}

function esDiaHabil(fecha) {
    return fecha.getDay() >= 1 && fecha.getDay() <= 5;
}

function nombreMes(fecha) {
    return new Intl.DateTimeFormat('es-AR', {
        month: 'long',
        year: 'numeric'
    }).format(fecha);
}

export default function Calendario() {
    const { state } = useStore();
    const nav = useNavigate();

    const [vista, setVista] = useState('mes');
    const [dia, setDia] = useState(HOY);

    const [fechaSeleccionada, setFechaSeleccionada] = useState(
        sumarDias(lunesDe(hoyReal), HOY)
    );

    const [mesActual, setMesActual] = useState(
        new Date(hoyReal.getFullYear(), hoyReal.getMonth(), 1)
    );

    const [f, setF] = useState({
        sp: '',
        tipo: '',
        estado: ''
    });

    const sp = id => state.espacios.find(s => s.id === id);

    const acts = useMemo(() => state.actividades.filter(a =>
        (!f.sp || a.sp === f.sp) &&
        (!f.tipo || a.tipo === f.tipo) &&
        (!f.estado || (
            f.estado === 'Cancelada'
                ? a.cancelada
                : !a.cancelada
        ))
    ), [state.actividades, f]);

    const enConflicto = a =>
        !a.cancelada &&
        state.actividades.some(b =>
            b.id !== a.id &&
            !b.cancelada &&
            b.sp === a.sp &&
            esMismoDia(fechaActividad(a), fechaActividad(b)) &&
            seSuperpone(a, b)
        );

    const pedidosConflicto = state.pedidos.filter(p =>
        p.estado === 'Por asignar' &&
        state.espacios.every(s =>
            evaluar(p, s, state).conflictos.length > 0
        )
    );

    const hayFiltros = f.sp || f.tipo || f.estado;

    const abrir = a =>
        nav('/actividad/' + a.id, {
            state: { from: '/calendario' }
        });

    const seleccionarFecha = fecha => {
        setFechaSeleccionada(fecha);
        setDia((fecha.getDay() + 6) % 7);
        setVista('dia');
    };

    const moverMes = cantidad => {
        setMesActual(actual =>
            new Date(
                actual.getFullYear(),
                actual.getMonth() + cantidad,
                1
            )
        );
    };

    const moverDia = cantidad => {
        const nueva = sumarDias(fechaSeleccionada, cantidad);

        if (!esDiaHabil(nueva)) return;

        setFechaSeleccionada(nueva);
        setDia((nueva.getDay() + 6) % 7);
    };

    const actividadesDelDia = fecha =>
        acts
            .filter(a => esMismoDia(fechaActividad(a), fecha))
            .sort((a, b) => a.ini - b.ini);

    const semanaActual = lunesDe(hoyReal);

    const esFeriado = fecha =>
        FERIADOS.includes(claveFecha(fecha));

    const Bloque = ({ a, compacto }) => (
        <button
            className={
                'bloque' +
                (a.cancelada ? ' cancelada' : '') +
                (enConflicto(a) ? ' conflicto' : '')
            }
            onClick={() => abrir(a)}
        >
            <strong>{rango(a.ini, a.fin)}</strong>
            <span>{a.titulo}</span>

            {!compacto && (
                <>
                    <span className="muted">
                        {sp(a.sp)?.nombre}
                    </span>

                    {a.req?.length > 0 && (
                        <span className="muted">
                            Equipamiento: {a.req.map(r =>
                                `${r.cant} ${r.n}`
                            ).join(', ')}
                        </span>
                    )}
                </>
            )}

            {enConflicto(a) ? (
                <Badge tono="err">Conflicto de horario</Badge>
            ) : (
                <Badge tono={a.cancelada ? 'neutro' : 'info'}>
                    {a.cancelada ? 'Cancelada' : 'Programada'}
                </Badge>
            )}
        </button>
    );

    // Construcción del almanaque mensual de lunes a viernes.
    const primerDia = new Date(
        mesActual.getFullYear(),
        mesActual.getMonth(),
        1
    );

    const ultimoDia = new Date(
        mesActual.getFullYear(),
        mesActual.getMonth() + 1,
        0
    );

    let primerHabil = new Date(primerDia);

    while (!esDiaHabil(primerHabil)) {
        primerHabil = sumarDias(primerHabil, 1);
    }

    const espaciosIniciales = (primerHabil.getDay() + 6) % 7;
    const celdasMes = [];

    for (let i = 0; i < espaciosIniciales; i++) {
        celdasMes.push(null);
    }

    for (
        let fecha = new Date(primerHabil);
        fecha <= ultimoDia;
        fecha = sumarDias(fecha, 1)
    ) {
        if (esDiaHabil(fecha)) {
            celdasMes.push(new Date(fecha));
        }
    }

    while (celdasMes.length % 5 !== 0) {
        celdasMes.push(null);
    }

    const actividadesFechaSeleccionada =
        actividadesDelDia(fechaSeleccionada);

    return (
        <div className="calendario-vista">

            {/* ENCABEZADO Y FILTROS */}
            <section
                className="filtros"
                aria-label="Vista y filtros del calendario"
            >
                <div className="segmentado" role="tablist" aria-label="Vista">
                    {[
                        ['dia', 'Día'],
                        ['semana', 'Semana'],
                        ['mes', 'Mes']
                    ].map(([k, l]) => (
                        <button
                            key={k}
                            role="tab"
                            aria-selected={vista === k}
                            className={vista === k ? 'on' : ''}
                            onClick={() => setVista(k)}
                        >
                            {l}
                        </button>
                    ))}
                </div>

                {vista === 'dia' && (
                    <div className="row">
                        <button
                            className="btn-icon"
                            aria-label="Día anterior"
                            disabled={dia === 0}
                            onClick={() => moverDia(-1)}
                        >
                            <Icon name="chevron_left" />
                        </button>

                        <strong>
                            {new Intl.DateTimeFormat('es-AR', {
                                weekday: 'long',
                                day: 'numeric',
                                month: 'long',
                                year: 'numeric'
                            }).format(fechaSeleccionada)}
                        </strong>

                        <button
                            className="btn-icon"
                            aria-label="Día siguiente"
                            disabled={dia === 4}
                            onClick={() => moverDia(1)}
                        >
                            <Icon name="chevron_right" />
                        </button>
                    </div>
                )}

                {vista === 'mes' && (
                    <div className="mes-navegacion">
                        <button
                            className="btn-icon"
                            aria-label="Mes anterior"
                            onClick={() => moverMes(-1)}
                        >
                            <Icon name="chevron_left" />
                        </button>

                        <strong className="mes-titulo">
                            {nombreMes(mesActual)}
                        </strong>

                        <button
                            className="btn-icon"
                            aria-label="Mes siguiente"
                            onClick={() => moverMes(1)}
                        >
                            <Icon name="chevron_right" />
                        </button>
                    </div>
                )}

                <select
                    aria-label="Espacio"
                    value={f.sp}
                    onChange={e => setF({ ...f, sp: e.target.value })}
                >
                    <option value="">Todos los espacios</option>
                    {state.espacios.map(s => (
                        <option key={s.id} value={s.id}>
                            {s.nombre}
                        </option>
                    ))}
                </select>

                <select
                    aria-label="Actividad"
                    value={f.tipo}
                    onChange={e => setF({ ...f, tipo: e.target.value })}
                >
                    <option value="">Todas las actividades</option>
                    {TIPOS.map(t => (
                        <option key={t}>{t}</option>
                    ))}
                </select>

                <select
                    aria-label="Estado"
                    value={f.estado}
                    onChange={e => setF({ ...f, estado: e.target.value })}
                >
                    <option value="">Todos los estados</option>
                    <option>Programada</option>
                    <option>Cancelada</option>
                </select>

                {hayFiltros && (
                    <Button
                        variant="texto"
                        onClick={() => setF({
                            sp: '',
                            tipo: '',
                            estado: ''
                        })}
                    >
                        Limpiar filtros
                    </Button>
                )}
            </section>

            {/* LEYENDA */}
            <div className="leyenda" aria-label="Leyenda">
                <Badge tono="info">Programada</Badge>
                <Badge tono="err">Conflicto de horario</Badge>
                <Badge tono="neutro">Cancelada</Badge>
                <span className="ley-feriado">
                    Feriado: sin reservas
                </span>
                <span className="ley-mant">
                    Espacio en mantenimiento
                </span>
            </div>

            {/* PEDIDOS SIN ESPACIO DISPONIBLE */}
            {pedidosConflicto.length > 0 && (
                <Aviso
                    tono="error"
                    titulo={
                        pedidosConflicto.length === 1
                            ? '1 pedido sin espacio disponible'
                            : pedidosConflicto.length + ' pedidos sin espacio disponible'
                    }
                    accion={
                        <Button
                            size="sm"
                            variant="secundario"
                            onClick={() =>
                                nav('/pedidos', {
                                    state: {
                                        sel: pedidosConflicto[0].id
                                    }
                                })
                            }
                        >
                            Resolver en Pedidos
                        </Button>
                    }
                >
                    {pedidosConflicto.map(p => p.titulo).join(' · ')}
                </Aviso>
            )}

            {/* VISTA SEMANAL */}
            {vista === 'semana' && (
                <section className="semana">
                    {DIAS.map((d, i) => {
                        const fechaDia = sumarDias(semanaActual, i);
                        const feriado = esFeriado(fechaDia);

                        const actividades = acts
                            .filter(a =>
                                a.fecha
                                    ? esMismoDia(fechaActividad(a), fechaDia)
                                    : Number(a.dia) === i
                            )
                            .sort((a, b) => a.ini - b.ini);

                        return (
                            <div
                                key={d}
                                className={
                                    'dia' +
                                    (feriado ? ' feriado' : '') +
                                    (esMismoDia(fechaDia, hoyReal) ? ' hoy' : '')
                                }
                            >
                                <button
                                    className="dia-tit"
                                    onClick={() => seleccionarFecha(fechaDia)}
                                >
                                    <span>
                                        {d} {fechaDia.getDate()}
                                    </span>

                                    {esMismoDia(fechaDia, hoyReal) && (
                                        <Badge tono="info">Hoy</Badge>
                                    )}

                                    {feriado && (
                                        <Badge tono="err">Feriado</Badge>
                                    )}
                                </button>

                                {feriado ? (
                                    <p className="muted">Sin reservas.</p>
                                ) : (
                                    actividades.map(a => (
                                        <Bloque key={a.id} a={a} />
                                    ))
                                )}
                            </div>
                        );
                    })}
                </section>
            )}

            {/* VISTA DIARIA */}
            {vista === 'dia' && (
                esFeriado(fechaSeleccionada) ? (
                    <Aviso
                        tono="error"
                        titulo="Este día es feriado"
                    >
                        No se reservan espacios ese día.
                    </Aviso>
                ) : (
                    <section
                        className="card dia-grilla"
                        style={{
                            gridTemplateColumns:
                                '64px repeat(' +
                                (f.sp ? 1 : state.espacios.length) +
                                ', minmax(140px,1fr))'
                        }}
                    >
                        <span />

                        {state.espacios
                            .filter(s => !f.sp || s.id === f.sp)
                            .map(s => (
                                <strong
                                    key={s.id}
                                    className={
                                        'dg-esp' +
                                        (s.estado === 'Mantenimiento' ? ' mant' : '')
                                    }
                                >
                                    {s.nombre}

                                    {s.estado === 'Mantenimiento' && (
                                        <Badge tono="warn">
                                            Mantenimiento
                                        </Badge>
                                    )}
                                </strong>
                            ))}

                        {HORAS.map(h => (
                            <div
                                key={h}
                                className="dg-fila"
                                style={{ display: 'contents' }}
                            >
                                <span className="dg-hora">{h}:00</span>

                                {state.espacios
                                    .filter(s => !f.sp || s.id === f.sp)
                                    .map(s => {
                                        const a = actividadesFechaSeleccionada.find(
                                            x => x.sp === s.id && x.ini === h
                                        );

                                        const ocupado = actividadesFechaSeleccionada.some(
                                            x => x.sp === s.id &&
                                                x.ini < h &&
                                                x.fin > h
                                        );

                                        return (
                                            <div
                                                key={s.id}
                                                className={
                                                    'dg-celda' +
                                                    (s.estado === 'Mantenimiento' ? ' mant' : '')
                                                }
                                            >
                                                {a && (
                                                    <Bloque a={a} compacto />
                                                )}

                                                {!a && ocupado && null}
                                            </div>
                                        );
                                    })}
                            </div>
                        ))}
                    </section>
                )
            )}

            {/* VISTA MENSUAL */}
            {vista === 'mes' && (
                <section className="mes">
                    {DIAS.map(d => (
                        <strong key={d} className="mes-cab">
                            {d}
                        </strong>
                    ))}

                    {celdasMes.map((fecha, i) => {
                        if (!fecha) {
                            return (
                                <div
                                    key={'vacio-' + i}
                                    className="mes-dia mes-vacio"
                                />
                            );
                        }

                        const delDia = actividadesDelDia(fecha);
                        const feriado = esFeriado(fecha);
                        const esHoy = esMismoDia(fecha, hoyReal);
                        const seleccionada = esMismoDia(
                            fecha,
                            fechaSeleccionada
                        );

                        return (
                            <button
                                key={claveFecha(fecha)}
                                className={
                                    'mes-dia' +
                                    (feriado ? ' feriado' : '') +
                                    (esHoy ? ' hoy' : '') +
                                    (seleccionada ? ' seleccionado' : '')
                                }
                                onClick={() => seleccionarFecha(fecha)}
                            >
                                <span className="mes-num">
                                    {fecha.getDate()}
                                </span>

                                {esHoy && (
                                    <Badge tono="info">Hoy</Badge>
                                )}

                                {feriado && (
                                    <Badge tono="err">Feriado</Badge>
                                )}

                                {delDia.slice(0, 3).map(a => (
                                    <span
                                        key={a.id}
                                        className={
                                            'mes-act' +
                                            (enConflicto(a) ? ' conflicto' : '') +
                                            (a.cancelada ? ' cancelada' : '')
                                        }
                                        onClick={e => {
                                            e.stopPropagation();
                                            abrir(a);
                                        }}
                                    >
                                        {a.ini}:00 {a.titulo}
                                    </span>
                                ))}

                                {delDia.length > 3 && (
                                    <span className="muted">
                                        +{delDia.length - 3} más
                                    </span>
                                )}
                            </button>
                        );
                    })}
                </section>
            )}

            {/* AVISO CUANDO NO HAY ACTIVIDADES */}
            {!acts.length && (
                <Aviso
                    tono="info"
                    titulo="No hay actividades para estos filtros"
                >
                    Probá con otro espacio, tipo o estado.
                </Aviso>
            )}
        </div>
    );
}
