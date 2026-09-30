const { createServer } = require('node:http');
const { test } = require('node:test');
const { join } = require('node:path');

let firefox;
try { ({ firefox } = require('playwright')); } catch {}

test('Firefox model picker, provider bulk toggle and URL restore', { skip: !firefox }, async () => {
  const { readFileSync } = require('node:fs');
  const root = join(__dirname, '..');
  const server = createServer((req, res) => {
    const file = join(root, new URL(req.url, 'http://localhost').pathname.slice(1));
    if (!file.startsWith(root)) { res.writeHead(403).end(); return; }
    try {
      res.setHeader('Content-Type', file.endsWith('.json') ? 'application/json' : 'text/html');
      res.end(readFileSync(file));
    } catch { res.writeHead(404).end(); }
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  let browser;
  try {
    browser = await firefox.launch({ headless: true, executablePath: process.env.FIREFOX_BIN });
    const page = await browser.newPage();
    await page.route('**/models.json', route => route.fulfill({ json: [
      { name: 'Alpha', creator: 'OpenAI', provider: 'OpenAI', slug: 'alpha', cost_per_task: 1, intelligence_index: 50, e2e_response_time_s: 10 },
      { name: 'Beta', creator: 'OpenAI', provider: 'OpenAI', slug: 'beta', cost_per_task: 2, intelligence_index: 40, e2e_response_time_s: 20 },
      { name: 'Gamma', creator: 'Google', provider: 'Google', slug: 'gamma', cost_per_task: 3, intelligence_index: 30, e2e_response_time_s: 30 },
    ] }));
    await page.goto(`http://127.0.0.1:${server.address().port}/intelligence-vs-cost.html`);
    await page.waitForFunction(() => document.querySelector('#model-picker-toggle')?.textContent.includes('3 of 3 selected'));
    await page.getByRole('button', { name: /^Models/ }).click();
    await page.locator('#model-picker').waitFor({ state: 'visible' });

    await page.locator('input[data-provider="OpenAI"]').click();
    await page.waitForFunction(() => document.querySelector('#model-picker-toggle')?.textContent.includes('1 of 3 selected'));
    const selectionUrl = new URL(page.url());
    if (!selectionUrl.searchParams.has('models')) throw new Error('provider selection was not written to the URL');
    await page.reload();
    await page.waitForFunction(() => document.querySelector('#model-picker-toggle')?.textContent.includes('1 of 3 selected'));

    await page.getByRole('button', { name: /^Models/ }).click();
    await page.locator('input[data-provider="OpenAI"]').click();
    await page.waitForFunction(() => document.querySelector('#model-picker-toggle')?.textContent.includes('3 of 3 selected'));
    if (!(await page.locator('input[data-key="OpenAI::Alpha"]').isVisible())) {
      await page.locator('details[data-group="OpenAI"] > summary').click();
    }
    await page.locator('input[data-key="OpenAI::Alpha"]').click();
    await page.waitForFunction(() => document.querySelector('#model-picker-toggle')?.textContent.includes('2 of 3 selected'));
    const partialUrl = page.url();
    await page.reload();
    await page.waitForFunction(() => document.querySelector('#model-picker-toggle')?.textContent.includes('2 of 3 selected'));
    if (!new URL(partialUrl).searchParams.has('models')) throw new Error('partial selection was not serialized');
  } finally {
    await browser?.close();
    server.close();
  }
});
