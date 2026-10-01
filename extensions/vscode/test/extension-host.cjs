'use strict';
const assert = require('node:assert/strict');
const path = require('node:path');
const vscode = require('vscode');

async function run() {
  const extension = vscode.extensions.getExtension('MJChku.drperf-explorer');
  assert.ok(extension, 'extension is installed in the development host');
  const api = await extension.activate();
  const root = vscode.workspace.workspaceFolders[0].uri.fsPath;
  await api.load(vscode.Uri.file(path.join(__dirname, '../demo/pipeline.drperf.json')));
  const model = api.getReport();
  assert.equal(model.regions.length, 7);
  const document = await vscode.workspace.openTextDocument(
    path.join(root, 'examples/explorer/pipeline.c')
  );
  let editor = await vscode.window.showTextDocument(document);
  const lenses = await vscode.commands.executeCommand(
    'vscode.executeCodeLensProvider',
    document.uri
  );
  assert.ok(lenses.length >= 7, `expected source-linked regions, got ${lenses.length}`);
  assert.ok(lenses.some((l) => l.command?.title.includes('64*items')));
  const enqueue = model.regions.find((r) => r.id === 'enqueue');
  const line = enqueue.sources[0].line - 1;
  editor.selection = new vscode.Selection(line, 0, line, 0);
  assert.equal(api.currentRegion(editor), 'enqueue');
  assert.ok((await api.getSourceStatus('enqueue')).every((source) => source.state === 'matches'));
  const hovers = await vscode.commands.executeCommand(
    'vscode.executeHoverProvider',
    document.uri,
    new vscode.Position(line, 8)
  );
  assert.ok(hovers.length);
  // A region selected from the tree must reveal its source even when another
  // document is active, and keep the performance panel alongside it.
  const unrelated = await vscode.workspace.openTextDocument({ content: 'other file' });
  await vscode.window.showTextDocument(unrelated);
  await vscode.commands.executeCommand('drperf.inspectRegion', 'enqueue');
  const revealed = vscode.window.visibleTextEditors.find(
    (candidate) => candidate.document.uri.toString() === document.uri.toString()
  );
  assert.ok(revealed, 'region click opens its source beside the explorer');
  assert.equal(revealed.selection.active.line, line);
  editor = revealed;
  assert.ok(vscode.window.tabGroups.all.some((group) =>
    group.viewColumn !== revealed.viewColumn && group.tabs.some(
      (tab) => tab.input instanceof vscode.TabInputWebview
    )
  ), 'source and explorer occupy different editor groups');
  const scenarioUri = vscode.Uri.file(path.join(root, 'scenario.json'));
  await vscode.workspace.fs.writeFile(
    scenarioUri,
    Buffer.from(
      JSON.stringify({
        schema: 'drperf.scenario.v1',
        modelId: model.id,
        scenario: {
          edits: [{ region: 'enqueue', state: 'items', op: 'scale', value: 2 }],
          relations: []
        }
      })
    )
  );
  await vscode.commands.executeCommand('drperf.openScenario', scenarioUri);
  for (let i = 0; i < 150 && !api.getAnalysisStatus(); ++i)
    await new Promise((resolve) => setTimeout(resolve, 100));
  const analysis = api.getAnalysisStatus();
  assert.ok(analysis, 'webview completes background analysis');
  assert.equal(analysis.error, undefined);
  assert.equal(analysis.backend, 'worker');
  assert.deepEqual(analysis.changedRegions, ['enqueue']);
  await editor.edit((edit) =>
    edit.insert(new vscode.Position(0, 0), '/* changed after measurement */\n')
  );
  const stale = await vscode.commands.executeCommand(
    'vscode.executeCodeLensProvider',
    document.uri
  );
  assert.ok(stale.some((l) => l.command?.title.includes('source changed')));
  assert.ok((await api.getSourceStatus('enqueue')).some((source) => source.state === 'changed'));
  await vscode.window.showTextDocument(document);
  await vscode.commands.executeCommand('undo');
  for (let i = 0; i < 30 && document.isDirty; ++i)
    await new Promise((resolve) => setTimeout(resolve, 50));
  assert.equal(document.isDirty, false);
  await vscode.commands.executeCommand('drperf.openJointDemo');
  for (let i = 0; i < 150 && !api.getAnalysisStatus()?.validationMeasuredId; ++i)
    await new Promise((resolve) => setTimeout(resolve, 100));
  const joint = api.getAnalysisStatus();
  assert.equal(
    joint?.validationStructureMatches,
    true,
    'bundled joint demo includes measured validation'
  );
  assert.equal(joint.error, undefined);
  assert.deepEqual([...joint.changedRegions].sort(), [
    'copy',
    'decode',
    'dequeue',
    'dispatch',
    'enqueue',
    'lookup'
  ]);
  const variants = structuredClone(model);
  variants.id = 'source-variant-test';
  variants.trace = { complete: false, events: [], recordCount: 0 };
  variants.regions.push({
    ...structuredClone(enqueue),
    id: 'enqueue@extra-pcv',
    name: 'enqueue [items, extra]',
    states: ['items', 'extra'],
    calls: 0,
    regimes: [],
    points: []
  });
  const variantsUri = vscode.Uri.file(path.join(root, 'variants.drperf.json'));
  await vscode.workspace.fs.writeFile(variantsUri, Buffer.from(JSON.stringify(variants)));
  await api.load(variantsUri);
  await vscode.commands.executeCommand('drperf.inspectRegion', 'enqueue@extra-pcv');
  editor.selection = new vscode.Selection(line, 0, line, 0);
  assert.equal(
    api.currentRegion(editor),
    'enqueue@extra-pcv',
    'cursor tracking preserves a selected source-overlapping PCV schema'
  );
  const invalidUri = vscode.Uri.file(path.join(root, 'invalid.drperf.json'));
  await vscode.workspace.fs.writeFile(
    invalidUri,
    Buffer.from(JSON.stringify({ schema: 'wrong', regions: 'not an array' }))
  );
  await vscode.window.showTextDocument(await vscode.workspace.openTextDocument(invalidUri));
  let diagnostics = [];
  for (let i = 0; i < 100; ++i) {
    diagnostics = vscode.languages.getDiagnostics(invalidUri);
    if (diagnostics.length) break;
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  console.log(
    'SCHEMA DIAGNOSTICS:',
    JSON.stringify(diagnostics.map((d) => ({ severity: d.severity, message: d.message })))
  );
  assert.ok(
    diagnostics.some((d) => /required|array|drperf.explorer.v1/.test(d.message)),
    'bundled JSON schema validates exported-report documents'
  );
  await vscode.commands.executeCommand('workbench.action.closeAllEditors');
  console.log(
    'EXTENSION HOST PASS: activation, report loading, source CodeLens, hover, cursor mapping, webview worker, saved-scenario import, stale-source detection, JSON schema diagnostics.'
  );
}
module.exports = { run };
