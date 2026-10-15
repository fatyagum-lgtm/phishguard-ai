export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch('/api' + path, init);
  const data = await response.json();
  if (!response.ok)
    throw new Error(
      typeof data.detail === 'string' ? data.detail : 'Request failed. Check the local API.',
    );
  return data as T;
}
export function download(value: unknown, name: string) {
  const blob = new Blob([JSON.stringify(value, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export const pretty = (value: string) => value.replaceAll('_', ' ');
export const percent = (value: number | null | undefined) =>
  value == null ? '—' : `${(value * 100).toFixed(1)}%`;
