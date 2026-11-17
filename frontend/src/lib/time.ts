// PM-INS-0020 (۶د) — server times are UTC; some older values were written without a zone marker («2026-11-17T05:38»),
// which a browser reads as LOCAL time and shows «۵:۳۸» to an owner in Dubai. Treat a zoneless value as UTC and show it
// in the viewer's own clock (Dubai for the owner).
export function serverDate(s?: string | null): Date | null {
  if (!s) return null;
  const hasZone = /(Z|[+-]\d\d:?\d\d)$/.test(s);
  const d = new Date(hasZone ? s : `${s}Z`);
  return isNaN(d.getTime()) ? null : d;
}

export function localTime(s?: string | null): string {
  const d = serverDate(s);
  return d ? d.toLocaleString('fa-IR') : '-';
}
