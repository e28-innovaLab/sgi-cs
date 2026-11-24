// Barra de horarios libres y ocupados (8 a 20 h).
export default function BarraDia({ bloques, nuevo }) {
  const pos = h => ((h - 8) / 12) * 100 + '%', ancho = (a, b) => ((b - a) / 12) * 100 + '%';
  return (
    <div className="barra" aria-label="Disponibilidad del día">
      {bloques.map((b, i) => <span key={i} className="barra-ocupado" style={{ left: pos(b.ini), width: ancho(b.ini, b.fin) }} title={b.titulo} />)}
      {nuevo && <span className="barra-nuevo" style={{ left: pos(nuevo.ini), width: ancho(nuevo.ini, nuevo.fin) }} />}
      <span className="barra-eje"><span>8</span><span>14</span><span>20</span></span>
    </div>
  );
}
