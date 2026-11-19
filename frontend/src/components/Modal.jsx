import { useEffect, useRef } from 'react';
import Icon from './Icon.jsx';
// Foco dentro del modal, Escape cierra, al cerrar el foco vuelve al botón que lo abrió.
export default function Modal({ titulo, subtitulo, onClose, children, pie, ancho = 640, alerta }) {
  const ref = useRef(), prev = useRef(document.activeElement);
  useEffect(() => {
    const el = ref.current; el?.querySelector('input,select,textarea,button')?.focus();
    const k = e => {
      if (e.key === 'Escape') onClose();
      if (e.key === 'Tab') { const f = [...el.querySelectorAll('button,input,select,textarea,a[href]')].filter(x => !x.disabled); if (!f.length) return; const a = f[0], z = f[f.length - 1]; if (e.shiftKey && document.activeElement === a) { e.preventDefault(); z.focus(); } else if (!e.shiftKey && document.activeElement === z) { e.preventDefault(); a.focus(); } }
    };
    document.addEventListener('keydown', k);
    const p = prev.current;
    return () => { document.removeEventListener('keydown', k); p?.focus?.(); };
  }, [onClose]);
  return (
    <div className="overlay">
      <div ref={ref} className="modal" role={alerta ? 'alertdialog' : 'dialog'} aria-modal="true" aria-labelledby="modal-tit" style={{ maxWidth: ancho }}>
        <div className="modal-head">
          <div><div id="modal-tit" className="modal-tit">{titulo}</div>{subtitulo && <div className="modal-sub">{subtitulo}</div>}</div>
          <button className="btn-icon" aria-label="Cerrar" onClick={onClose}><Icon name="close" /></button>
        </div>
        <div className="modal-body">{children}</div>
        {pie && <div className="modal-pie">{pie}</div>}
      </div>
    </div>
  );
}
