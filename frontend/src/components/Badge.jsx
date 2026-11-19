// tono: ok | warn | err | info | neutro
export default function Badge({ tono = 'info', children }) {
  return <span className={'badge badge-' + tono}>{children}</span>;
}