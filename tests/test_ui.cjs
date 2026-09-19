const { readFileSync } = require('node:fs');
const { join } = require('node:path');
const vm = require('node:vm');
const test = require('node:test');
const assert = require('node:assert/strict');

const html = readFileSync(join(__dirname, '../intelligence-vs-cost.html'), 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
const metrics = [...html.matchAll(/name="metric" value="([^"]+)"/g)].map(m => m[1]);
const added = ['livebench_coding', 'livebench_agentic_coding'];
const metadata = {
  release: '2026_06_25', source_model: 'test-max',
  subtasks: { livebench_coding: { completed: 1, expected: 2 }, livebench_agentic_coding: { completed: 3, expected: 3 } },
};
const model = (name, cost, score, time) => ({
  name, creator: 'OpenAI', provider: 'OpenAI', slug: name,
  intelligence_index: 50, coding_index: 30, math_index: 40, terminalbench_v4_0: 20,
  livebench_coding: score, livebench_agentic_coding: score,
  livebench: score == null ? null : metadata,
  cost_per_task: cost, e2e_response_time_s: time,
  price_1m_input_tokens: 1, price_1m_output_tokens: 2, output_tokens_per_second: 10,
});
const models = [model('Zero', 1, 0, null), model('Best', 2, 90, 50),
  model('Dominated', 3, 50, 20), model('Missing', 4, null, 10)];

// Only the DOM methods used by this page; production functions and handlers run unchanged.
async function page(data = models, metric = added[0]) {
  function element() {
    const attributes = {}, events = {};
    return {
      innerHTML: '', textContent: '', hidden: false, style: {}, dataset: {}, events,
      clientWidth: 1000, clientHeight: 800, offsetHeight: 20, offsetWidth: 240,
      min: 0, max: 1000, step: 1, value: '',
      get options() {
        return [...this.innerHTML.matchAll(/<option value="([^"]+)"([^>]*)>/g)].map(m => ({
          value: m[1], selected: / selected/.test(m[2]),
        }));
      },
      get selectedOptions() { return this.options.filter(option => option.selected); },
      classList: { contains: () => false },
      addEventListener: (name, fn) => { events[name] = fn; },
      setAttribute: (name, value) => { attributes[name] = value; },
      getAttribute: name => attributes[name],
      getBoundingClientRect: () => ({ left: 0, top: 0, width: 1000, height: 800 }),
      querySelectorAll(selector) {
        if (selector !== 'circle[data-i]') return [];
        return [...this.innerHTML.matchAll(/data-i="(\d+)"/g)].map(m => {
          const circle = element(); circle.dataset.i = m[1]; return circle;
        });
      },
    };
  }
  const nodes = new Map();
  const node = id => { if (!nodes.has(id)) nodes.set(id, element()); return nodes.get(id); };
  const radios = metrics.map(value => Object.assign(element(), { value }));
  node('chart').parentElement = node('chart-card');
  node('table-view').hidden = true;
  const location = new URL(`https://example.test/intelligence-vs-cost.html?metric=${metric}`);
  const context = vm.createContext({
    URL, URLSearchParams, location, setTimeout, clearTimeout,
    history: { replaceState: (_, __, url) => { location.href = url.href; } },
    window: { addEventListener() {} },
    document: {
      getElementById: node, addEventListener() {},
      querySelectorAll: selector => selector === 'input[name="metric"]' ? radios : [],
      querySelector: selector => radios.find(r => selector.includes(`value="${r.value}"`)) || node(selector),
    },
    fetch: async () => ({ ok: true, json: async () => structuredClone(data) }),
  });
  vm.runInContext(script, context);
  await new Promise(setImmediate);
  assert.doesNotMatch(node('status').textContent, /Could not load/);
  const api = vm.runInContext('({state, render, paretoFront, showTooltip, livebenchScore})', context);
  const table = () => node('#data-table tbody').innerHTML;
  node('table-toggle').events.click({ currentTarget: node('table-toggle') });
  return { ...api, node, radios, table, location };
}

for (const metric of added) {
  test(`${metric}: URL, radio, table, Pareto, tooltip and provenance`, async () => {
    const p = await page(models, metric);
    assert.equal(p.state.metric, metric);
    assert.equal(p.radios.find(r => r.value === metric).checked, true);
    assert.match(p.node('chart').getAttribute('aria-label'), /LiveBench.*AA Intelligence Index/);
    assert.doesNotMatch(p.node('chart').innerHTML, /NaN|Infinity/);
    assert.match(p.node('chart').innerHTML, /Zero: LiveBench/);
    assert.doesNotMatch(p.table(), /<td>Missing<\/td>/);
    assert(p.table().indexOf('<td>Best</td>') < p.table().indexOf('<td>Dominated</td>'));
    assert.match(p.table(), /2026_06_25 · test-max · 1\/2 subtasks/);
    assert.equal(p.paretoFront(p.state.models.filter(m => m[metric] != null), metric).map(m => m.name).join(','), 'Zero,Best');
    p.showTooltip(p.state.models[0], p.node('chart'));
    assert.match(p.node('tooltip').innerHTML, /LiveBench Agentic Coding/);
    assert.match(p.node('tooltip').innerHTML, /3\/3 subtasks/);
    p.radios.find(r => r.value === 'coding_index').events.change();
    assert.equal(p.state.metric, 'coding_index');
    assert.equal(p.location.searchParams.get('metric'), 'coding_index');
    assert.match(p.table(), /<td>Missing<\/td>/);
    p.radios.find(r => r.value === metric).events.change();
    assert.equal(p.location.searchParams.get('metric'), metric);
  });

  test(`${metric}: model/provider selectors and response-time filter`, async () => {
    const p = await page(models, metric);
    assert.match(p.node('provider-select').innerHTML, /<option value="OpenAI"/);
    assert.match(p.node('model-select').innerHTML, /<option value="OpenAI::Best"/);
    p.node('e2e-number').value = '25';
    p.node('e2e-number').events.input();
    assert.doesNotMatch(p.table(), /<td>Best<\/td>/);
    assert.match(p.table(), /<td>Zero<\/td>/); // Unknown response time remains visible.
    p.state.selectedModels.delete('OpenAI::Zero');
    p.render();
    assert.doesNotMatch(p.table(), /<td>Zero<\/td>/);
    p.node('clear-models').events.click();
    assert.equal(p.table(), '');
    assert.doesNotMatch(p.node('chart').innerHTML, /NaN|Infinity/);
    models.forEach(m => p.state.selectedModels.add(`OpenAI::${m.name}`));
    p.render();
    assert.match(p.table(), /<td>Zero<\/td>/);
    assert.match(p.table(), /<td>Dominated<\/td>/);
  });

  test(`${metric}: older JSON and missing metadata remain usable`, async () => {
    const old = models.map(m => Object.fromEntries(Object.entries(m).filter(([k]) => !k.startsWith('livebench'))));
    const p = await page(old, metric);
    assert.equal(p.table(), '');
    assert.doesNotMatch(p.node('chart').innerHTML, /NaN|Infinity/);
    p.radios.find(r => r.value === 'terminalbench_v4_0').events.change();
    assert.match(p.table(), /<td>Best<\/td>/);
    assert.equal(p.livebenchScore({ [metric]: 0 }, metric), '0.0');
    assert.match(p.livebenchScore({ [metric]: 1, livebench: { ...metadata, source_model: '<script>' } }, metric), /&lt;script>/);
  });
}
