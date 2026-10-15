import { test, expect } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
const shots = path.resolve('../docs/screenshots');
test('actual API, URL/email flows, research, offline resources and responsive layout', async ({
  page,
  request,
}) => {
  fs.mkdirSync(shots, { recursive: true });
  const remote: string[] = [];
  const errors: string[] = [];
  page.on('request', (r) => {
    if (!r.url().startsWith('http://127.0.0.1:8000') && !r.url().startsWith('blob:'))
      remote.push(r.url());
  });
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto('/');
  await expect(page.getByText('Local model ready')).toBeVisible();
  const report = await (await request.get('/api/research/summary')).json();
  await expect(page.locator('.metric').first()).toContainText(
    report.dataset.sample_rows.toLocaleString(),
  );
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: path.join(shots, 'overview.png'), fullPage: true });
  await page.getByRole('button', { name: /URL analysis/ }).click();
  await page.getByRole('button', { name: 'Benign-looking', exact: true }).click();
  await page.getByRole('button', { name: /Analyze URL/ }).click();
  await expect(page.getByRole('heading', { name: 'review required', exact: true })).toBeVisible();
  const sample = await (
    await request.post('/api/analyze/url', {
      data: { url: 'https://example.org/articles/security-basics' },
    })
  ).json();
  await expect(page.locator('.score strong')).toHaveText(`${(sample.score * 100).toFixed(1)}%`);
  await expect(page.getByRole('heading', { name: 'Model explanation' })).toBeVisible();
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Export JSON ↓' }).click();
  expect((await download).suggestedFilename()).toBe('phishguard-url-report.json');
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: path.join(shots, 'url-analysis.png'), fullPage: true });
  await page.getByRole('button', { name: /Email investigation/ }).click();
  await page.getByRole('button', { name: 'Load synthetic message' }).click();
  await page.getByRole('button', { name: /Analyze email/ }).click();
  await expect(page.getByText('UNVERIFIED HEADER CLAIMS')).toBeVisible();
  await expect(page.getByText(/NOT independently verified/)).toBeVisible();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: path.join(shots, 'email-investigation.png'), fullPage: true });
  let dialog = false;
  page.on('dialog', async (d) => {
    dialog = true;
    await d.dismiss();
  });
  await page
    .getByLabel('Paste message text or raw email')
    .fill(
      'Subject: <img src=x onerror=alert(1)>\nContent-Type: text/html\n\n<script>alert(1)</script><p>Visible text</p>',
    );
  await page.getByRole('button', { name: /Analyze email/ }).click();
  await expect(page.getByText('<img src=x onerror=alert(1)>', { exact: true })).toBeVisible();
  expect(await page.locator('img').count()).toBe(0);
  expect(dialog).toBe(false);
  await page.locator('input[type=file]').setInputFiles({
    name: 'fixture.eml',
    mimeType: 'message/rfc822',
    buffer: Buffer.from('Subject: Uploaded fixture\n\nPlain text'),
  });
  await expect(page.getByText('Uploaded fixture', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: /Research laboratory/ }).click();
  await expect(page.getByRole('heading', { name: 'Model comparison' })).toBeVisible();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: path.join(shots, 'research.png'), fullPage: true });
  await page.getByLabel('Evaluation protocol').selectOption('random');
  await expect(page.getByText('8,000 test samples')).toBeVisible();
  await page.getByLabel('Evaluation protocol').selectOption('domain_disjoint');
  await page.getByLabel('Inspect model').selectOption('forest_no_https');
  await expect(page.getByText(/No perturbation study was run/)).toBeVisible();
  await page.getByRole('button', { name: /Model & dataset/ }).click();
  await expect(page.getByRole('heading', { name: 'Trust boundaries' })).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  for (const name of ['Overview', 'URL analysis', 'Research laboratory']) {
    await page
      .getByRole('button', { name: new RegExp(name) })
      .first()
      .click();
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
    ).toBe(true);
  }
  await page
    .getByRole('button', { name: /Overview/ })
    .first()
    .click();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: path.join(shots, 'mobile.png'), fullPage: true });
  expect(remote).toEqual([]);
  expect(errors).toEqual([]);
});
