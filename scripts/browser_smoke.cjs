/* End-to-end training-only smoke test. Never points at an existing case vault. */
const { chromium } = require('playwright');
const { spawn } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const assert = require('node:assert/strict');

async function main() {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'traceharbor-e2e-'));
  const output = process.env.TRACEHARBOR_SCREENSHOTS || temp;
  fs.mkdirSync(output, { recursive: true });
  const port = 18742;
  const root = path.resolve(__dirname, '..');
  const python = process.env.TRACEHARBOR_PYTHON || 'python3';
  const server = spawn(python, ['-m', 'traceharbor', '--data-dir', temp, 'serve', '--port', String(port)], { cwd: root });
  const session = await new Promise((resolve, reject) => {
    let stdout = '';
    const timer = setTimeout(() => reject(new Error('Server did not start within 20 seconds')), 20000);
    server.stdout.on('data', chunk => {
      stdout += chunk.toString();
      const match = stdout.match(/#token=([A-Za-z0-9_-]+)/);
      if (match) { clearTimeout(timer); resolve(match[1]); }
    });
    server.once('error', reject);
    server.once('exit', code => { clearTimeout(timer); reject(new Error(`Server exited (${code})`)); });
  });
  let browser;
  try {
    browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({ viewport: { width: 1440, height: 1100 }, acceptDownloads: true });
    const page = await context.newPage();
    const errors = [], outbound = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
    page.on('request', request => { if (!request.url().startsWith(`http://127.0.0.1:${port}`) && !request.url().startsWith('blob:')) outbound.push(request.url()); });
    await page.goto(`http://127.0.0.1:${port}/#token=${session}`);
    await page.getByRole('heading', { name: 'Workspace overview' }).waitFor();
    assert(!page.url().includes('token='), 'Session fragment must be cleared');
    await page.screenshot({ path: path.join(output, 'overview-empty.png'), fullPage: true });

    await page.getByRole('button', { name: 'Load a labelled training case' }).click();
    await page.getByRole('button', { name: 'Create training case', exact: true }).click();
    await page.getByRole('heading', { name: 'TRAINING · Documentation review', exact: true }).waitFor();
    await page.getByRole('button', { name: 'Audit', exact: true }).click();
    await page.getByRole('button', { name: 'Run integrity check' }).click();
    await page.getByText('No inconsistencies detected', { exact: true }).waitFor();

    await page.getByRole('button', { name: 'Add record', exact: true }).click();
    await page.getByRole('button', { name: 'Write an analyst finding' }).click();
    await page.getByLabel('Title', { exact: true }).fill('TRAINING · <script>alert(1)</script> is literal text');
    await page.getByLabel('Observation and reasoning').fill('Cross-site scripting test with training content only.');
    await page.getByRole('button', { name: 'Save record', exact: true }).click();
    await page.getByRole('button', { name: 'All', exact: true }).click();
    await page.getByRole('heading', { name: 'TRAINING · <script>alert(1)</script> is literal text' }).waitFor();

    await page.getByRole('button', { name: 'Evidence lab', exact: true }).click();
    await page.getByLabel('Choose evidence file').setInputFiles({ name: 'training-note.txt', mimeType: 'text/plain', buffer: Buffer.from('TraceHarbor training evidence.\n') });
    await page.getByLabel('Collection notes (optional)').fill('Synthetic browser-test file. Not real evidence.');
    await page.getByRole('button', { name: 'Run analysis', exact: true }).click();
    await page.getByRole('heading', { name: 'Analysis complete', exact: true }).waitFor();
    assert(await page.getByText('training-note.txt · 0.0 KiB').count() === 1);

    await page.getByRole('button', { name: 'Link inspector', exact: true }).click();
    await page.getByLabel('Public HTTP(S) URL').fill('https://example.org/page?training=1');
    await page.getByRole('button', { name: 'Inspect URL', exact: true }).click();
    await page.getByRole('heading', { name: 'URL structure', exact: true }).waitFor();
    await page.getByRole('button', { name: 'Public leads', exact: true }).click();
    await page.getByLabel('Public username', { exact: true }).fill('training_example');
    await page.getByRole('button', { name: 'Prepare public links' }).click();
    await page.getByRole('heading', { name: 'Candidate public URLs' }).waitFor();
    assert.equal(await page.locator('#lead-result .status-pill.unverified').count(), 3);

    await page.getByRole('button', { name: 'Case library', exact: false }).first().click();
    await page.getByRole('button', { name: 'Open case' }).click();
    await page.getByRole('button', { name: 'Files', exact: true }).click();
    await page.getByRole('heading', { name: 'training-note.txt', exact: true }).waitFor();
    await page.getByRole('button', { name: 'Export', exact: true }).click();
    const downloaded = page.waitForEvent('download');
    await page.getByRole('button', { name: 'Download report ZIP' }).click();
    const download = await downloaded;
    await download.saveAs(path.join(temp, 'browser-report.zip'));
    assert(fs.statSync(path.join(temp, 'browser-report.zip')).size > 1000);

    await page.getByRole('button', { name: 'Archive', exact: true }).click();
    await page.getByText('This case is archived.', { exact: false }).waitFor();
    await page.getByRole('button', { name: 'Reopen', exact: true }).click();
    await page.getByRole('button', { name: 'Archive', exact: true }).waitFor();
    await page.getByRole('button', { name: 'Overview', exact: true }).first().click();
    await page.getByRole('heading', { name: 'Workspace overview' }).waitFor();
    await page.screenshot({ path: path.join(output, 'workspace-desktop.png'), fullPage: true });
    const search = page.getByRole('textbox', { name: 'Search cases or records' });
    await search.fill('nothing-will-match-this');
    await page.getByRole('heading', { name: 'No matching cases' }).waitFor();
    await search.fill('');
    await page.reload();
    await page.getByRole('heading', { name: 'Workspace overview' }).waitFor();
    await page.getByRole('button', { name: 'TRAINING · Documentation review', exact: true }).waitFor();

    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({ path: path.join(output, 'workspace-mobile.png'), fullPage: true });
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'Mobile page overflows horizontally');
    await page.getByRole('button', { name: 'Toggle navigation' }).click();
    await page.getByRole('button', { name: 'Field guide', exact: true }).click();
    await page.getByRole('heading', { name: 'Good research leaves a trail.' }).waitFor();
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'Mobile guide overflows');
    assert.deepEqual(outbound, [], 'Analysis must not contact third-party servers');
    assert.deepEqual(errors, [], 'No browser errors or CSP violations');
    await page.getByRole('button', { name: 'Toggle navigation' }).click();
    await page.getByRole('button', { name: 'Lock workspace' }).click();
    await page.getByRole('heading', { name: 'Your evidence. Your workspace.' }).waitFor();
    console.log('PASS: training case, findings/XSS, evidence upload, audit verification, URL inspection, public leads, export, archive/reopen, search, persistence, mobile navigation and session lock.');
    console.log(`Screenshots: ${output}`);
  } finally {
    if (browser) await browser.close();
    server.kill('SIGTERM');
  }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
