'use strict';
const http = require('node:http');
const fs = require('node:fs/promises');
const path = require('node:path');
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const base = path.resolve(__dirname, '..');
const output = path.resolve(__dirname, '../../../out/explorer-ui');
const model = JSON.parse(
  require('node:fs').readFileSync(path.join(base, 'demo/pipeline.drperf.json'), 'utf8')
);
const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'nonce-test'; worker-src blob:; connect-src 'self'; style-src 'self'; img-src 'self' data:"><link rel="stylesheet" href="/media/explorer.css"></head><body><div id="app"></div><script nonce="test" src="/media/expressions.js"></script><script nonce="test" src="/media/model.js"></script><script nonce="test" src="/media/analysis-client.js" data-expressions="/media/expressions.js" data-model="/media/model.js" data-worker="/media/analysis-worker.js"></script><script nonce="test" src="/media/execution-graph.js"></script><script nonce="test" src="/media/vendor/elk.bundled.js"></script><script nonce="test" src="/media/graph-layout.js"></script><script nonce="test" src="/media/explorer.js"></script></body></html>`;
(async () => {
  await fs.mkdir(output, { recursive: true });
  const server = http.createServer(async (req, res) => {
    if (req.url === '/') {
      res.writeHead(200, { 'Content-Type': 'text/html' });
      res.end(html);
      return;
    }
    if(req.url==='/actual-graph.json' && process.env.DRPERF_UI_GRAPH_PROFILE) {
      res.writeHead(200,{'Content-Type':'application/json'});
      res.end(await fs.readFile(process.env.DRPERF_UI_GRAPH_PROFILE));return;
    }
    const target = path.resolve(base, '.' + req.url);
    if (!target.startsWith(base + path.sep)) {
      res.writeHead(403);
      res.end();
      return;
    }
    try {
      const data = await fs.readFile(target);
      res.writeHead(200, {
        'Content-Type': target.endsWith('.js') ? 'text/javascript' : 'text/css'
      });
      res.end(data);
    } catch {
      res.writeHead(404);
      res.end();
    }
  });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  let browser;
  try {
    browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
    const page = await browser.newPage({
      viewport: { width: 1280, height: 900 },
      deviceScaleFactor: 1
    });
    async function assertGraphLayout() {
      const problems=await page.evaluate(()=>{
        const issues=[],svg=document.querySelector('.execution-svg');
        const content=[...document.querySelectorAll('.execution-node foreignObject')];
        for(const f of content){
          const child=f.firstElementChild;
          if(child.scrollHeight>Number(f.getAttribute('height'))+1)issues.push('clipped height: '+f.parentNode.dataset.region);
          if(child.scrollWidth>Number(f.getAttribute('width'))+1)issues.push('clipped width: '+f.parentNode.dataset.region);
        }
        const bounds=content.map(f=>f.getBBox());
        for(const edge of document.querySelectorAll('.execution-edge')) {
          const length=edge.getTotalLength();
          for(let i=0;i<=100;i++){
            const p=edge.getPointAtLength(length*i/100);
            if(bounds.some(b=>p.x>b.x+1&&p.x<b.x+b.width-1&&p.y>b.y+1&&p.y<b.y+b.height-1)){
              issues.push('arrow crosses text: '+edge.dataset.source+' -> '+edge.dataset.target);break;
            }
          }
        }
        if(svg&&Number(svg.getAttribute('width'))/svg.viewBox.baseVal.width<.0049)issues.push('invalid zoom');
        return issues;
      });
      assert.deepEqual(problems,[]);
    }
    async function graphAction(name) {
      await page.locator('.execution-more>summary').click();
      await page.getByRole('button',{name,exact:typeof name==='string'}).click();
    }
    const errors = [];
    page.on('pageerror', (error) => errors.push(error.message));
    await page.goto(`http://127.0.0.1:${server.address().port}`);
    await page.evaluate((m) => {
      window.hostMessages = [];
      window.addEventListener('drperfHostMessage', (e) => window.hostMessages.push(e.detail));
      window.postMessage({ type: 'model', model: m, selected: 'enqueue' }, '*');
    }, model);
    await page.getByRole('heading', { name: 'enqueue', exact: true }).waitFor();
    assert.match(await page.locator('.formula').first().textContent(), /64\*items/);
    await page.evaluate(
      (id) =>
        window.postMessage(
          {
            type: 'sourceStatus',
            modelId: id,
            region: 'enqueue',
            sources: [{ path: 'pipeline.c', state: 'changed' }]
          },
          '*'
        ),
      model.id
    );
    await page.getByText(/Source differs from the exported snapshot/).waitFor();
    await page.evaluate(
      (id) =>
        window.postMessage(
          {
            type: 'sourceStatus',
            modelId: id,
            region: 'enqueue',
            sources: [{ path: 'pipeline.c', state: 'matches' }]
          },
          '*'
        ),
      model.id
    );
    await page.getByText(/Source differs from the exported snapshot/).waitFor({ state: 'hidden' });
    await page.screenshot({ path: path.join(output, 'interface.png'), fullPage: true });
    await page.getByRole('button', { name: 'Relationships', exact: true }).click();
    assert.equal(await page.locator('.relationship').count(), model.relations.length);
    await page.getByLabel('Filter relationships').fill('enqueue');
    assert.ok((await page.locator('.relationship').count()) > 0);
    await page.getByLabel('Filter relationships').fill('');
    await page.screenshot({ path: path.join(output, 'relationships.png'), fullPage: true });
    await page.getByRole('button', { name: 'What-if', exact: true }).click();
    await page.locator('.scenario-table tbody tr').first().waitFor();
    assert.equal(await page.locator('.scenario-table tbody tr').count(), 1);
    assert.equal(await page.evaluate(() => window.DrperfAnalysis.backend), 'worker');
    await page.getByRole('button', { name: 'Use first observed equation for each target' }).click();
    await page.locator('.scenario-table tr[data-region="copy"]').waitFor();
    assert.ok((await page.locator('.scenario-table tbody tr').count()) >= 5);
    await page
      .getByRole('button', { name: 'Find distinguishing experiments', exact: true })
      .click();
    await page
      .locator(
        '.experiment-suggestion[data-experiment-region="decode"][data-experiment-op="scale"]'
      )
      .waitFor();
    assert.match(
      await page
        .locator(
          '.experiment-suggestion[data-experiment-region="decode"][data-experiment-op="scale"]'
        )
        .textContent(),
      /copy.bytes/
    );
    const copyEquation = await page.getByLabel('Relationship for copy.bytes').inputValue();
    await page.getByLabel('Relationship for copy.bytes').selectOption('');
    assert.equal(
      await page.locator('.experiment-suggestion').count(),
      0,
      'changed assumptions invalidate displayed experiment suggestions'
    );
    await page.getByLabel('Relationship for copy.bytes').selectOption(copyEquation);
    await page.locator('.scenario-table tr[data-region="copy"]').waitFor();
    const copy = page.locator('.scenario-table tr[data-region="copy"]');
    assert.ok((await copy.textContent()).includes('extrapolated'));
    await page.screenshot({ path: path.join(output, 'scenario.png'), fullPage: true });
    const changed = JSON.parse(
      await fs.readFile(path.join(base, 'demo/changed.drperf.json'), 'utf8')
    );
    await page.evaluate(
      (m) =>
        window.postMessage(
          { type: 'validationModel', model: m, name: 'Changed measured program' },
          '*'
        ),
      changed
    );
    await page.locator('tr[data-validation-region="lookup"]').waitFor();
    assert.match(
      await page.locator('tr[data-validation-region="lookup"]').textContent(),
      /22%/
    );
    await page.screenshot({ path: path.join(output, 'validation.png'), fullPage: true });
    await page.getByRole('button', { name: 'Compare runs', exact: true }).click();
    await page.locator('.comparison-table').waitFor();
    assert.match(
      await page.locator('tr[data-comparison-region="enqueue"]').textContent(),
      /paired/
    );
    assert.match(
      await page.locator('tr[data-comparison-region="copy"]').textContent(),
      /No paired states/
    );
    await page.screenshot({ path: path.join(output, 'comparison.png'), fullPage: true });
    await page.getByRole('button', { name: 'Relationships', exact: true }).click();
    await page.locator('.relationship-check-summary').waitFor();
    assert.equal(
      await page.locator('.relationship-check[data-relationship-status="fails"]').count(),
      0
    );
    await page.getByRole('button', { name: 'What-if', exact: true }).click();
    await page.getByRole('button', { name: 'Save scenario and per-region results' }).click();
    assert.ok(
      await page.evaluate(() =>
        window.hostMessages.some(
          (m) => m.type === 'exportScenario' && m.scenario.edits[0].value === 2
        )
      )
    );
    await page.getByRole('button', { name: '+ Add another PCV' }).click();
    await page.getByLabel('Region for intervention 2', { exact: true }).selectOption('decode');
    await page.getByLabel('Intervention value 2', { exact: true }).fill('1.5');
    assert.equal(await page.locator('.notice.error').count(), 0);
    await page.getByLabel('Compare alternative relationships', { exact: true }).check();
    await page.getByText('copy.bytes: disagreement at 24/24 calls').waitFor();
    await page.screenshot({ path: path.join(output, 'alternatives.png'), fullPage: true });
    await page.setViewportSize({ width: 520, height: 850 });
    await page.screenshot({ path: path.join(output, 'narrow.png'), fullPage: true });
    assert.ok(
      await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)
    );
    await page.setViewportSize({ width: 1280, height: 900 });
    // Proposals are independently checked, retain counterexamples, and require opt-in.
    await page.getByLabel('Proposed target region').selectOption('decode');
    await page.getByLabel('Proposed state expression').fill('3 * last("dequeue", "items")');
    await page.getByRole('button', { name: 'Check proposed relationship', exact: true }).click();
    await page.getByText('Failed at 24 of 24 recorded target calls.').waitFor();
    await page.getByLabel('Proposed state expression').fill('2 * last("dequeue", "items")');
    await page.getByRole('button', { name: 'Check proposed relationship', exact: true }).click();
    await page
      .getByRole('button', { name: 'Use checked proposal as an assumption', exact: true })
      .click();
    assert.match(
      await page.getByLabel('Relationship for decode.tokens').inputValue(),
      /^proposed:/
    );
    await page.getByRole('button', { name: 'Save scenario and per-region results' }).click();
    assert.ok(
      await page.evaluate(() =>
        window.hostMessages.some(
          (m) => m.type === 'exportScenario' && m.scenario.proposals?.length === 1
        )
      )
    );
    // The latest edit wins even when worker work is already queued.
    await page.evaluate(() => {
      const input = document.querySelector('[aria-label="Intervention value 1"]');
      for (const value of ['3', '4', '2']) {
        input.value = value;
        input.dispatchEvent(new Event('input', { bubbles: true }));
      }
    });
    await page.locator('#scenario-result .analysis-pending').waitFor({ state: 'hidden' });
    await page.getByRole('button', { name: 'Save scenario and per-region results' }).click();
    const savedScenario = await page.evaluate(
      () => window.hostMessages.filter((m) => m.type === 'exportScenario').at(-1).scenario
    );
    assert.equal(savedScenario.edits[0].value, 2);
    // A saved scenario is checked again, and importing it cannot overwrite a
    // subsequent edit made while that check is running.
    await page.evaluate(
      ({ id, scenario }) => {
        window.dispatchEvent(
          new MessageEvent('message', { data: { type: 'scenario', modelId: id, scenario } })
        );
        const input = document.querySelector('[aria-label="Intervention value 1"]');
        input.value = '3';
        input.dispatchEvent(new Event('input', { bubbles: true }));
      },
      { id: model.id, scenario: savedScenario }
    );
    await page.locator('#scenario-result .analysis-pending').waitFor({ state: 'hidden' });
    assert.equal(await page.getByLabel('Intervention value 1', { exact: true }).inputValue(), '3');
    await page.evaluate(
      ({ id, scenario }) => window.postMessage({ type: 'scenario', modelId: id, scenario }, '*'),
      { id: model.id, scenario: savedScenario }
    );
    await page.waitForFunction(
      () =>
        document.querySelector('[aria-label="Intervention value 1"]')?.value === '2' &&
        !document.querySelector('#scenario-result .analysis-pending')
    );
    assert.equal(
      await page.getByLabel('Intervention value 2', { exact: true }).inputValue(),
      '1.5'
    );
    assert.match(
      await page.getByLabel('Relationship for decode.tokens').inputValue(),
      /^proposed:/
    );
    const bad = structuredClone(model);
    bad.validity.errors = ['slot overflow'];
    await page.evaluate((m) => window.postMessage({ type: 'model', model: m }, '*'), bad);
    await page
      .getByText('Measurement errors: slot overflow. Scenario predictions are disabled.')
      .waitFor();
    assert.equal(await page.locator('.scenario-table').count(), 0);
    const hostile = structuredClone(model);
    hostile.regions[0].name = '<img src=x onerror="window.exploited=1">';
    await page.evaluate(
      (m) => window.postMessage({ type: 'model', model: m, selected: m.regions[0].id }, '*'),
      hostile
    );
    await page.getByRole('button', { name: 'Interface', exact: true }).click();
    assert.equal(await page.locator('img').count(), 0);
    assert.equal(await page.evaluate(() => window.exploited), undefined);
    const refined = JSON.parse(
      await fs.readFile(path.join(base, 'demo/refined.drperf.json'), 'utf8')
    );
    const joint = JSON.parse(
      await fs.readFile(path.join(base, 'demo/joint-changed.drperf.json'), 'utf8')
    );
    const jointScenario = JSON.parse(
      await fs.readFile(path.join(base, 'demo/joint.scenario.json'), 'utf8')
    );
    await page.evaluate(
      ({ model, measured, saved }) => {
        window.postMessage({ type: 'model', model }, '*');
        window.postMessage(
          {
            type: 'scenario',
            modelId: model.id,
            scenario: saved.scenario,
            measured,
            measuredName: 'Measured joint producer/expansion change'
          },
          '*'
        );
      },
      { model: refined, measured: joint, saved: jointScenario }
    );
    await page.locator('tr[data-validation-region="lookup"]').waitFor();
    assert.match(await page.locator('tr[data-validation-region="lookup"]').textContent(), /24\/24/);
    assert.match(
      await page.locator('tr[data-validation-region="dispatch"]').textContent(),
      /17\/24/
    );
    assert.equal(
      await page.getByLabel('Intervention value 2', { exact: true }).inputValue(),
      '1.5'
    );
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({ path: path.join(output, 'joint.png'), fullPage: false });
    // The parent percentage follows its displayed child terms. A resolved
    // child remains atomic even when its descendants have unexplained work.
    const composed = structuredClone(model);
    composed.id += ':child-share';
    composed.relations = [];
    const region = (id, cost, unexplained) => ({
      id, name: id, states: ['n'], calls: 1, sources: [], droppedCalls: 0,
      points: [{state: [1], observed: cost, recorded: cost, calls: 1}],
      regimes: [{coefficients: [0], constant: cost - unexplained,
        dependent: ['n'], range: [[1, 1]], unexplainedShare: unexplained / cost,
        points: [{state: [1], explained: cost - unexplained, unexplained, calls: 1}],
        blocks: {unexplained: unexplained ? 1 : 0},
        attribution: {coefficients: [[]], constant: [], unexplained: []}}]
    });
    composed.regions = [region('parent', 100, 0), region('child', 100, 0), region('grandchild', 200, 150)];
    const edge = (child, resolved) => ({child, form: resolved ? 'product' : 'unresolved',
      argumentStates: ['n'], arguments: null, sequenceArguments: null, indexVariable: 'j',
      multiplicity: resolved ? {coefficients: ['0'], constant: '1'} : null});
    composed.composition = {status: 'observed', regions: [
      {id: 'parent', states: ['n'], children: [edge('child', false)]},
      {id: 'child', states: ['n'], children: [edge('grandchild', true)]},
      {id: 'grandchild', states: ['n'], children: []}]};
    composed.trace = {complete: true, recordCount: 3, events: [
      {region: 'parent', values: {n: 1}, seq: 1, end: 6, group: '0:1', thread: '1'},
      {region: 'child', values: {n: 1}, seq: 2, end: 5, group: '0:1', thread: '1'},
      {region: 'grandchild', values: {n: 1}, seq: 3, end: 4, group: '0:1', thread: '1'}]};
    await page.getByRole('button', {name: 'Interface', exact: true}).click();
    await page.evaluate((m) => window.postMessage({type: 'model', model: m, selected: 'parent'}, '*'), composed);
    await page.getByRole('heading', {name: 'parent', exact: true}).waitFor();
    assert.equal(await page.locator('.interface-unexplained').textContent(), '75% unexplained (estimate)');
    assert.match(await page.locator('.formula').textContent(), /unexplained\(F\[child\]\)/);
    assert.equal(await page.getByText(/Tied PCVs:/).count(), 0);
    await page.getByRole('button', {name: 'F[child]', exact: true}).click();
    await page.getByRole('heading', {name: 'child', exact: true}).waitFor();
    assert.equal(await page.locator('.interface-unexplained').textContent(), '0% unexplained (estimate)');
    // Topology stays compact; the selected interface appears in the right pane.
    await page.evaluate((m)=>window.postMessage({type:'model',model:m,selected:'parent'},'*'),composed);
    await page.getByRole('button',{name:'Graph',exact:true}).click();
    await page.locator('.execution-graph[aria-busy="false"] .execution-svg').waitFor({timeout:60000});
    await page.getByText(/Waits not captured/).waitFor();
    await page.getByRole('button',{name:'Show details',exact:true}).click();
    assert.equal(await page.locator('.execution-node').count(),1);
    assert.match(await page.locator('.execution-inspector .formula').textContent(),/F\[child\]/);
    await page.locator('.execution-inspector .formula').getByRole('button',{name:'F[child]',exact:true}).click();
    await page.locator('.execution-graph[aria-busy="false"] .execution-svg').waitFor({timeout:60000});
    assert.equal(await page.locator('.execution-node').count(),2);
    assert.equal(await page.locator('.execution-edge.contains').count(),0);
    const waiting=structuredClone(composed);waiting.id+=':wait';
    waiting.waits={status:'observed',events:[{...waiting.trace.events[2],id:'published'}],
      operations:[{...waiting.trace.events[0],api:'sem_wait',id:'consumed',producers:['published']}]};
    await page.evaluate(m=>window.postMessage({type:'model',model:m,selected:'parent'},'*'),waiting);
    await page.locator('.execution-reveal-wait').waitFor();
    assert.equal(await page.locator('.execution-edge.wait').count(),0);
    assert.equal(await page.locator('.execution-node').count(),1);
    assert.match(await page.locator('.execution-inspector .execution-edge-row[data-kind="wait"]').textContent(),/parent.*grandchild/);
    await page.getByRole('button',{name:'Zoom in',exact:true}).click();
    await page.locator('.execution-graph[aria-busy="false"] .execution-svg').waitFor({timeout:60000});
    const zoomBefore=await page.locator('.execution-zoom').textContent();
    await page.locator('.execution-reveal-wait').click();
    await page.locator('.execution-graph[aria-busy="false"] .execution-svg').waitFor({timeout:60000});
    assert.equal(await page.locator('.execution-zoom').textContent(),zoomBefore);
    await assertGraphLayout();
    assert.equal(await page.locator('.execution-node').count(),3);
    await page.getByRole('button',{name:'Collapse child',exact:true}).click();
    await page.locator('.execution-graph[aria-busy="false"] .execution-svg').waitFor({timeout:60000});
    assert.equal(await page.locator('.execution-node').count(),2);
    assert.match(await page.locator('.execution-inspector .execution-edge-row[data-kind="wait"]').textContent(),/grandchild/);
    await page.getByRole('button',{name:'Full-screen graph',exact:true}).click();
    await page.locator('.execution-graph[aria-busy="false"] .execution-svg').waitFor({timeout:60000});
    const expanded=await page.locator('.execution-graph').boundingBox();
    assert.equal(Math.round(expanded.width),page.viewportSize().width);
    assert.equal(Math.round(expanded.height),page.viewportSize().height);
    await page.getByRole('button',{name:'Zoom in',exact:true}).click();
    await page.locator('.execution-graph[aria-busy="false"] .execution-svg').waitFor({timeout:60000});
    await page.evaluate(()=>{window.graphBeforeEcho=document.querySelector('.execution-svg');window.postMessage({type:'select',region:'parent'},'*');});
    await page.waitForTimeout(50);
    assert.equal(await page.evaluate(()=>window.graphBeforeEcho===document.querySelector('.execution-svg')),true);
    await page.keyboard.press('Escape');
    assert.equal(await page.locator('body.graph-fullscreen').count(),0);
    await page.getByRole('button',{name:'Interface',exact:true}).click();
    await page.locator('.interface-unexplained').waitFor();
    await page.getByRole('button',{name:'Graph',exact:true}).click();
    await page.locator('.execution-graph[aria-busy="false"] .execution-svg').waitFor({timeout:60000});
    const partial=structuredClone(waiting);partial.id+=':partial';partial.waits.status='partial';
    await page.evaluate(m=>window.postMessage({type:'model',model:m,selected:'parent'},'*'),partial);
    await page.getByText(/Wait capture is incomplete/).waitFor();
    assert.equal(await page.locator('.execution-edge.wait').count(),0);
    if(process.env.DRPERF_UI_GRAPH_PROFILE) {
      await page.evaluate(async()=>{const m=await (await fetch('/actual-graph.json')).json();window.postMessage({type:'model',model:m,selected:'admit.free_blocks'},'*');});
      await page.locator('.execution-scope').filter({hasText:'105 regions in this profile'}).waitFor({state:'attached'});
    await page.locator('.execution-graph[aria-busy="false"] .execution-svg').waitFor({timeout:60000});
      await page.getByRole('button',{name:'Hide details',exact:true}).click();
      const roomy=await page.locator('.execution-canvas').boundingBox();
      assert.ok(roomy.height>=page.viewportSize().height*.9,'webview graph uses 90% of screen');
      assert.ok(roomy.width>=page.viewportSize().width*.97,'region list hidden by default');
      await graphAction('Show region list');
      assert.equal(await page.locator('.region-sidebar').isVisible(),true);
      await graphAction('Hide region list');
      assert.equal(await page.locator('.region-sidebar').isVisible(),false);
      await page.getByRole('button',{name:'Show details',exact:true}).click();
      assert.equal(await page.locator('.execution-node').count(),11);
      assert.equal(await page.getByRole('button',{name:'Inspect',exact:true}).count(),0);
      await page.getByRole('button',{name:'Expand all',exact:true}).click();
    await page.locator('.execution-graph[aria-busy="false"] .execution-svg').waitFor({timeout:60000});
      assert.equal(await page.locator('.execution-node').count(),133);
      assert.equal(await page.locator('.execution-edge.wait').count(),1);
      assert.equal(await page.evaluate(()=>new Set([...document.querySelectorAll('.execution-node')].map(n=>n.dataset.region)).size),105);
      await assertGraphLayout();
      await graphAction('Collapse all');
    await page.locator('.execution-graph[aria-busy="false"] .execution-svg').waitFor({timeout:60000});
      await graphAction('All waits (1)');
    await page.locator('.execution-graph[aria-busy="false"] .execution-svg').waitFor({timeout:60000});
      assert.equal(await page.locator('.execution-edge.wait').count(),1);
      const blue=await page.locator('.execution-edge.wait').first().evaluate(e=>({color:getComputedStyle(e).stroke,dashes:getComputedStyle(e).strokeDasharray}));
      assert.equal(blue.dashes,'7px, 4px');assert.equal(blue.color,'rgb(119, 184, 255)');
      await page.getByRole('button',{name:'Select region worker.get_finished',exact:true}).click();
    await page.locator('.execution-graph[aria-busy="false"] .execution-svg').waitFor({timeout:60000});
      const parentFormula=await page.locator('.execution-inspector .formula').textContent();
      assert.match(parentFormula,/F\[worker.poll\]/);
      await page.getByRole('button',{name:'Full-screen graph',exact:true}).click();
    await page.locator('.execution-graph[aria-busy="false"] .execution-svg').waitFor({timeout:60000});
      await page.getByRole('button',{name:'Fit graph',exact:true}).click();
    await page.locator('.execution-graph[aria-busy="false"] .execution-svg').waitFor({timeout:60000});
      await page.screenshot({path:path.join(output,'ditto-all-waits-fullscreen.png'),fullPage:false});
      await page.getByRole('button',{name:'Expand worker.get_finished',exact:true}).click();
    await page.locator('.execution-graph[aria-busy="false"] .execution-svg').waitFor({timeout:60000});
      assert.equal(await page.getByRole('button',{name:'Expand worker.submit_store',exact:true}).count(),1);
      for(const region of ['worker.poll','rt.poll','rt.finish']) await page.getByRole('button',{name:'Expand '+region,exact:true}).click();
    await page.locator('.execution-graph[aria-busy="false"] .execution-svg').waitFor({timeout:60000});
      assert.equal(await page.locator('.execution-node[data-region="store.drain"]').count(),1);
      assert.equal(await page.locator('.execution-node[data-region="carrier.transfer"]').count(),0);
      const edge=page.locator('.execution-edge.wait[data-source="store.drain"][data-target="carrier.transfer"]');
      assert.equal(await edge.count(),1);
      // Both names stay visible when only one container has been expanded.
      assert.equal(await page.locator('.execution-edge-label,.execution-port-label').count(),0);
      await page.getByRole('button',{name:'Select region store.drain',exact:true}).click();
      await page.getByRole('button',{name:'Reveal wait: store.drain waits on carrier.transfer · 9 observations',exact:true}).click();
    await page.locator('.execution-graph[aria-busy="false"] .execution-svg').waitFor({timeout:60000});
      assert.ok(await page.locator('.execution-node[data-region="carrier.transfer"]').count()>0);
      await page.getByRole('button',{name:'Select region worker.get_finished',exact:true}).click();
      assert.equal(await page.locator('.execution-inspector .formula').textContent(),parentFormula);
      await page.getByRole('button',{name:'Fit graph',exact:true}).click();
    await page.locator('.execution-graph[aria-busy="false"] .execution-svg').waitFor({timeout:60000});
      await assertGraphLayout();
      await page.screenshot({path:path.join(output,'ditto-nested-waits.png'),fullPage:false});
      await page.keyboard.press('Escape');
      await page.getByRole('button',{name:'Select region store.drain',exact:true}).click();
    await page.locator('.execution-graph[aria-busy="false"] .execution-svg').waitFor({timeout:60000});
      assert.match(await page.locator('.execution-edge-row[data-kind="wait"][data-source="store.drain"]').textContent(),/9 observations.*1 per store.drain/);
      await graphAction('Full graph');
    await page.locator('.execution-graph[aria-busy="false"] .execution-svg').waitFor({timeout:60000});
      await graphAction('Collapse all');
    await page.locator('.execution-graph[aria-busy="false"] .execution-svg').waitFor({timeout:60000});
      await page.getByRole('button',{name:'Full-screen graph',exact:true}).click();
    await page.locator('.execution-graph[aria-busy="false"] .execution-svg').waitFor({timeout:60000});
      await page.getByRole('button',{name:'Fit graph',exact:true}).click();
    await page.locator('.execution-graph[aria-busy="false"] .execution-svg').waitFor({timeout:60000});
      await page.screenshot({path:path.join(output,'ditto-full-105-regions.png'),fullPage:false});
      await page.keyboard.press('Escape');
      console.log('Full Ditto: 105 regions in 133 nesting boxes, 1 cross-region wait edge; real expansion and no Inspect buttons passed.');
    }
    if(process.env.DRPERF_UI_EVENT_DIR) {
      for(const [name,ordered,violations] of [['correct-probe',10,0],['premature-probe',5,5]]) {
        const m=JSON.parse(await fs.readFile(path.join(process.env.DRPERF_UI_EVENT_DIR,name+'.drperf.json'),'utf8'));
        await page.evaluate(m=>window.postMessage({type:'model',model:m,selected:'candidates.get'},'*'),m);
        await page.locator('.execution-node[data-region="candidates.get"]').waitFor();
        await graphAction(/^All waits/);
    await page.locator('.execution-graph[aria-busy="false"] .execution-svg').waitFor({timeout:60000});
        assert.equal(await page.locator('.execution-edge.wait[data-event-status="ordered"]').count(),1);
        assert.equal(await page.locator('.execution-edge.wait.violation').count(),violations?1:0);
        assert.match(await page.locator('.execution-event-summary').textContent(),new RegExp(`${violations} violations`));
        const label=page.locator('.execution-reveal-wait[data-event-status="ordered"]');
        assert.equal(await label.count(),1);
        if(name==='correct-probe')assert.match(await page.locator('.execution-inspector .execution-edge-details').textContent(),/1 per candidates.get invocation/);
        if(violations) {
          const line=page.locator('.execution-edge.violation');
          assert.equal(await line.getAttribute('marker-end'),'url(#execution-arrow-violation)');
          assert.equal(await line.evaluate(n=>getComputedStyle(n).stroke),'rgb(240, 132, 132)');
        }
        await label.click();
    await page.locator('.execution-graph[aria-busy="false"] .execution-svg').waitFor({timeout:60000});
        assert.equal(await page.locator('.execution-node[data-region="candidates.build"]').count(),1);
        await page.getByRole('button',{name:'Full-screen graph',exact:true}).click();
    await page.locator('.execution-graph[aria-busy="false"] .execution-svg').waitFor({timeout:60000});
        await page.getByRole('button',{name:'Fit graph',exact:true}).click();
    await page.locator('.execution-graph[aria-busy="false"] .execution-svg').waitFor({timeout:60000});
        await assertGraphLayout();
        await page.screenshot({path:path.join(output,'ditto-events-'+name+'.png'),fullPage:false});
        await page.keyboard.press('Escape');
        await page.setViewportSize({width:640,height:900});
        await graphAction(/^All waits/);
    await page.locator('.execution-graph[aria-busy="false"] .execution-svg').waitFor({timeout:60000});
        await page.getByRole('button',{name:'Fit graph',exact:true}).click();
    await page.locator('.execution-graph[aria-busy="false"] .execution-svg').waitFor({timeout:60000});
        await assertGraphLayout();
        await page.screenshot({path:path.join(output,'ditto-events-narrow.png'),fullPage:false});
        await page.setViewportSize({width:1280,height:900});
      }
      console.log('Actual Ditto declared events: blue ordered edges, red violations, exact endpoints, fullscreen passed.');
    }
    await page.getByRole('button',{name:'Interface',exact:true}).click();
    const actualProfile = process.env.DRPERF_UI_PROFILE;
    if (actualProfile) {
      const actual = JSON.parse(await fs.readFile(actualProfile, 'utf8'));
      const Model = require('../media/model');
      Model.validate(actual);
      const info = Model.interfaceExplanation(actual, 'conn.ingest_meta');
      assert.ok(info.share > 0 && info.children.some((c) => c.child === 'worker.add_lease_ids'));
      await page.evaluate((m) => window.postMessage({type: 'model', model: m, selected: 'conn.ingest_meta'}, '*'), actual);
      await page.getByRole('heading', {name: 'conn.ingest_meta', exact: true}).waitFor();
      assert.equal(await page.locator('.interface-unexplained').textContent(), `${Math.round(info.share * 100)}% unexplained (estimate)`);
      assert.equal(await page.getByText(/Tied PCVs:/).count(), 0);
      console.log('Actual profile composed unexplained:', Math.round(info.share * 100) + '%');
    }
    assert.deepEqual(errors, []);
    console.log(
      'UI PASS: formulas, all relations, opt-in propagation, multiple PCVs, measured-run validation, checked proposals, narrow layout, invalid-data guard, safe rendering.'
    );
  } finally {
    await browser?.close();
    server.close();
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
