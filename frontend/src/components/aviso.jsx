import Icon from './Icon.jsx';
const IC = { error: 'error', warn: 'warning', info: 'info', ok: 'check_circle' };
export default function Aviso({ tono = 'info', titulo, children, accion }) {
  return (
    <div className={'aviso aviso-' + tono} role={tono === 'error' ? 'alert' : undefined}>
      <Icon name={IC[tono]} size={22} />
      <div className="aviso-body">{titulo && <strong>{titulo}</strong>}<div>{children}</div>{accion}</div>
    </div>
  );
}