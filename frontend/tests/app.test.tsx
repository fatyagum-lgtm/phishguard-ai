import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, it, expect, afterEach } from 'vitest';
import App from '../src/App';
import { URLInvestigation, EmailInvestigation } from '../src/Investigations';
afterEach(() => vi.restoreAllMocks());
it('supports main navigation and honest unavailable states', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({ ok: false, json: async () => ({ detail: 'No model' }) }),
  );
  render(<App />);
  await screen.findByText('API unavailable — start the local backend');
  fireEvent.click(screen.getByRole('button', { name: /URL analysis/ }));
  expect(screen.getByLabelText('URL to investigate')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: /Email investigation/ }));
  expect(screen.getByLabelText('Paste message text or raw email')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: /Research laboratory/ }));
  expect(screen.getByText('No experiment artifact available')).toBeInTheDocument();
});
it('validates URL input before calling the backend', () => {
  const fetch = vi.fn();
  vi.stubGlobal('fetch', fetch);
  render(<URLInvestigation />);
  fireEvent.change(screen.getByLabelText('URL to investigate'), {
    target: { value: 'javascript:alert(1)' },
  });
  fireEvent.click(screen.getByRole('button', { name: /Analyze URL/ }));
  expect(screen.getByRole('alert')).toHaveTextContent('absolute HTTP(S)');
  expect(fetch).not.toHaveBeenCalled();
});
it('shows server errors without interpreting hostile strings as markup', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: false,
      json: async () => ({ detail: '<img src=x onerror=alert(1)>' }),
    }),
  );
  const { container } = render(<URLInvestigation />);
  fireEvent.change(screen.getByLabelText('URL to investigate'), {
    target: { value: 'https://example.org' },
  });
  fireEvent.click(screen.getByRole('button', { name: /Analyze URL/ }));
  await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('<img'));
  expect(container.querySelector('img')).toBeNull();
});
it('loads the actual synthetic email fixture into the form', () => {
  render(<EmailInvestigation />);
  fireEvent.click(screen.getByRole('button', { name: 'Load synthetic message' }));
  expect(
    (screen.getByLabelText('Paste message text or raw email') as HTMLTextAreaElement).value,
  ).toContain('Authentication-Results:');
});
