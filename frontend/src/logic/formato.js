export const rango = (ini, fin) => `${ini}:00 a ${fin}:00 hs`;
export const seSuperpone = (a, b) => a.ini < b.fin && b.ini < a.fin;
