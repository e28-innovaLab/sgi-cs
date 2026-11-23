export default function Icon({ name, size = 20, style }) {
  return <span className="icon" aria-hidden="true" style={{ fontSize: size, ...style }}>{name}</span>;
}