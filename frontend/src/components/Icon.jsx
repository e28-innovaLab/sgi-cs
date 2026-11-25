
const ICONOS = {
    chevron_left: '‹',
    chevron_right: '›'
};

export default function Icon({ name, size = 20, style }) {
    return (
        <span
            className="icon"
            aria-hidden="true"
            style={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: size + 6,
                lineHeight: 1,
                ...style
            }}
        >
            {ICONOS[name] || name}
        </span>
    );
}
