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
async function page(data = models, metric = added[0], query = `metric=${metric}`) {
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
      focus() {}, contains: () => true, querySelector: () => null,
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
  node('model-picker').hidden = true;
  const location = new URL(`https://example.test/intelligence-vs-cost.html?${query}`);
  const context = vm.createContext({
    URL, URLSearchParams, location, setTimeout, clearTimeout, CSS: { escape: s => s },
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

  test(`${metric}: grouped model picker and response-time filter`, async () => {
    const data = [...models, model('Best (high)', 2.5, 91, 40), { ...model('Gemini', 1.5, 60, 5), provider: 'Google' }];
    const p = await page(data, metric);
    const groups = () => p.node('model-groups').innerHTML;
    const label = () => p.node('model-picker-toggle').textContent;
    const toggle = (dataset, checked) => p.node('model-groups').events.change({ target: { dataset, checked } });
    const search = (value) => { p.node('model-search').value = value; p.node('model-search').events.input(); };

    // Every model starts selected; providers are grouped and sorted.
    assert.equal(label(), 'Models: 5 of 5 selected');
    assert(groups().indexOf('data-provider="Google"') < groups().indexOf('data-provider="OpenAI"'));
    assert.match(groups(), /data-key="OpenAI::Best"[^>]* checked/);
    assert.doesNotMatch(groups(), /Best \(high\)/); // Reasoning levels share one row.

    p.node('model-picker-toggle').events.click({ preventDefault() {}, stopPropagation() {} });
    assert.equal(p.node('model-picker').hidden, false);
    assert.equal(p.node('model-picker-toggle').getAttribute('aria-expanded'), 'true');

    // Provider checkboxes select and clear a whole group in one click.
    toggle({ provider: 'OpenAI' }, false);
    assert.equal([...p.state.selectedModels].some(key => key.startsWith('OpenAI::')), false);
    toggle({ provider: 'OpenAI' }, true);
    assert.equal([...p.state.selectedModels].filter(key => key.startsWith('OpenAI::')).length, 4);

    // One model row hides all its reasoning levels; the provider becomes mixed.
    toggle({ key: 'OpenAI::Best' }, false);
    assert.doesNotMatch(p.table(), /<td>Best/);
    assert.equal(label(), 'Models: 4 of 5 selected');
    assert.match(groups(), /data-provider="OpenAI"[^>]* data-mixed/);
    assert.match(groups(), />3\/4</);

    // A provider header toggles every model of that provider.
    toggle({ provider: 'OpenAI' }, true);
    assert.match(p.table(), /<td>Best \(high\)<\/td>/);
    toggle({ provider: 'OpenAI' }, false);
    assert.doesNotMatch(p.table(), /<td>(Zero|Best|Dominated)<\/td>/);
    assert.match(p.table(), /<td>Gemini<\/td>/);
    toggle({ provider: 'OpenAI' }, true);

    // Search matches model and provider names; bulk actions apply to matches only.
    search('zero');
    toggle({ key: 'OpenAI::Best' }, false);
    assert.match(groups(), /data-provider="OpenAI"[^>]* checked/); // Header follows the matching models.
    assert.match(groups(), />3\/4</);
    toggle({ key: 'OpenAI::Best' }, true);
    search('gem');
    assert.doesNotMatch(groups(), /data-provider="OpenAI"/);
    p.node('clear-models').events.click();
    assert.doesNotMatch(p.table(), /<td>Gemini<\/td>/);
    assert.match(p.table(), /<td>Zero<\/td>/);
    p.node('select-all-models').events.click();
    assert.match(p.table(), /<td>Gemini<\/td>/);
    search('openai');
    assert.match(groups(), /data-key="OpenAI::Zero"/);
    assert.doesNotMatch(groups(), /data-provider="Google"/);
    search('nothing-matches');
    assert.match(groups(), /No models match/);
    search('');

    p.node('e2e-number').value = '25';
    p.node('e2e-number').events.input();
    assert.doesNotMatch(p.table(), /<td>Best<\/td>/);
    assert.match(p.table(), /<td>Zero<\/td>/); // Unknown response time remains visible.
    p.state.selectedModels.delete('OpenAI::Zero');
    p.render();
    assert.doesNotMatch(p.table(), /<td>Zero<\/td>/);
    p.node('clear-models').events.click();
    assert.equal(p.table(), '');
    assert.equal(label(), 'Models: 0 of 5 selected');
    assert.doesNotMatch(p.node('chart').innerHTML, /NaN|Infinity/);
    p.node('select-all-models').events.click();
    assert.match(p.table(), /<td>Zero<\/td>/);
    assert.match(p.table(), /<td>Dominated<\/td>/);
    assert.equal(label(), 'Models: 5 of 5 selected');
  });

  test(`${metric}: compact model selection URL restores the selected set`, async () => {
    const data = [...models, { ...model('Gemini', 1.5, 60, 5), provider: 'Google' }];
    const p = await page(data, metric);
    p.node('model-picker-toggle').events.click({ preventDefault() {}, stopPropagation() {} });
    p.node('model-groups').events.change({ target: { dataset: { key: 'OpenAI::Best' }, checked: false } });
    const encoded = p.location.searchParams.get('models');
    assert(encoded);
    assert(encoded.length < [...p.state.selectedModels].join(',').length);

    const restored = await page(data, metric, p.location.search.slice(1));
    assert.deepEqual([...restored.state.selectedModels].sort(), [...p.state.selectedModels].sort());
    assert.doesNotMatch(restored.table(), /<td>Best<\/td>/);
    assert.match(restored.table(), /<td>Zero<\/td>/);

    restored.node('clear-models').events.click();
    assert.equal(restored.state.selectedModels.size, 0);
    assert.equal(restored.location.searchParams.get('models'), '00');
    restored.node('select-all-models').events.click();
    assert.equal(restored.location.searchParams.has('models'), false);
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
