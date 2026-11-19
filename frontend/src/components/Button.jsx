import Icon from './Icon.jsx';

// variant: primario | secundario | neutro | acento | destructivo | texto
export default function Button({ variant = 'primario', size, icon, children, ...rest }) {
  return (
    <button className={'btn btn-' + variant + (size ? ' btn-' + size : '')} {...rest}>
      {icon && <Icon name={icon} size={19} />}{children}
    </button>
  );
}