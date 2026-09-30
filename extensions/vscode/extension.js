'use strict';
const vscode = require('vscode');
const path = require('node:path');
const crypto = require('node:crypto');
const { execFile } = require('node:child_process');
const Model = require('./media/model');
const Navigation = require('./navigation');
const { graphHtml } = require('./graph-export');

function activate(context) {
  let report = null,
    reportUri = null,
    panel = null,
    selected = null,
    demo = false,
    watcher = null,
    sourceTimer = null,
    loadSequence = 0,
    pendingScenario = null,
    webviewReady = false,
    analysisStatus = null;
  let sourceOpenSequence = 0, savedEditorLayout = null, layoutQueue = Promise.resolve();
  const sourceWarnings = new Set();
  const changed = new vscode.EventEmitter();
  const lensesChanged = new vscode.EventEmitter();
  const documentHashes = new WeakMap();
  const output = vscode.window.createOutputChannel('drperf');
  context.subscriptions.push(changed, lensesChanged, output, {
    dispose: () => {
      watcher?.dispose();
      clearTimeout(sourceTimer);
      panel?.dispose();
    }
  });
  const configuration = () => vscode.workspace.getConfiguration('drperf');
  const sourceRoot = () => {
    const configured = configuration().get('sourceRoot', '');
    const folder =
      (reportUri && vscode.workspace.getWorkspaceFolder(reportUri)) ||
      vscode.workspace.workspaceFolders?.[0];
    return Navigation.sourceRoot(configured, folder?.uri.fsPath,
      report?.provenance?.sourceRoot, (vscode.workspace.workspaceFolders || []).map(f=>f.uri.fsPath));
  };
  function sourceUri(location) {
    if (demo) return vscode.Uri.joinPath(context.extensionUri, 'demo', 'pipeline.c');
    const root = sourceRoot();
    if (!root || typeof location.path !== 'string' || path.isAbsolute(location.path)) return null;
    const candidate = path.resolve(root, location.path),
      relative = path.relative(root, candidate);
    if (relative === '..' || relative.startsWith('..' + path.sep) || path.isAbsolute(relative))
      return null;
    return vscode.Uri.file(candidate);
  }
  function locations(document) {
    if (!report || document.uri.scheme !== 'file') return [];
    const result = [];
    for (const region of report.regions)
      for (const location of region.sources) {
        if (sourceUri(location)?.toString() === document.uri.toString())
          result.push({ region, location });
      }
    return result;
  }
  function stale(document, location) {
    let cached = documentHashes.get(document);
    if (!cached || cached.version !== document.version) {
      cached = {
        version: document.version,
        hash: crypto.createHash('sha256').update(document.getText()).digest('hex')
      };
      documentHashes.set(document, cached);
    }
    return location.sha256 !== cached.hash;
  }
  async function getSourceStatus(regionId = selected) {
    const region = report?.regions.find((r) => r.id === regionId);
    if (!region) return [];
    const documents = new Map(
      vscode.workspace.textDocuments.map((document) => [document.uri.toString(), document])
    );
    const files = new Map();
    return Promise.all(
      region.sources.map(async (location) => {
        const uri = sourceUri(location);
        if (!uri) return { path: location.path, state: 'unavailable' };
        const document = documents.get(uri.toString());
        if (document)
          return { path: location.path, state: stale(document, location) ? 'changed' : 'matches' };
        try {
          if (!files.has(uri.toString()))
            files.set(
              uri.toString(),
              vscode.workspace.fs
                .readFile(uri)
                .then((bytes) => crypto.createHash('sha256').update(bytes).digest('hex'))
            );
          const hash = await files.get(uri.toString());
          return { path: location.path, state: hash === location.sha256 ? 'matches' : 'changed' };
        } catch {
          return { path: location.path, state: 'unavailable' };
        }
      })
    );
  }
  async function sendSourceStatus() {
    if (!panel || !report || !selected) return;
    const currentReport = report,
      currentRegionId = selected;
    const sources = await getSourceStatus(currentRegionId);
    if (report === currentReport && selected === currentRegionId)
      panel?.webview.postMessage({
        type: 'sourceStatus',
        modelId: report.id,
        region: currentRegionId,
        sources
      });
  }
  function scheduleSourceStatus() {
    clearTimeout(sourceTimer);
    sourceTimer = setTimeout(() => void sendSourceStatus(), 120);
  }
  function currentRegion(editor = vscode.window.activeTextEditor) {
    if (!editor) return null;
    const line = editor.selection.active.line + 1;
    const candidates = locations(editor.document).filter(
      ({ location }) => location.line <= line && line <= location.endLine
    );
    candidates.sort(
      (a, b) => a.location.endLine - a.location.line - (b.location.endLine - b.location.line)
    );
    // Runtime PCV-schema variants can share the same source annotation. Keep
    // the user's selected variant instead of switching back on cursor events.
    const first = candidates[0];
    if (
      first &&
      candidates.some(
        (candidate) =>
          candidate.region.id === selected &&
          candidate.location.line === first.location.line &&
          candidate.location.endLine === first.location.endLine
      )
    )
      return selected;
    return candidates[0]?.region.id || null;
  }
  function sendModel() {
    if (!panel || !webviewReady) return;
    panel?.webview.postMessage({
      type: 'model',
      model: report,
      selected,
      demo,
      sourceAvailable: !!sourceRoot() || demo,
      reportPath: reportUri?.fsPath || 'Bundled example'
    });
    if (pendingScenario) {
      if (pendingScenario.modelId === report.id)
        panel.webview.postMessage({
          type: 'scenario',
          scenario: pendingScenario.scenario,
          modelId: pendingScenario.modelId,
          measured: pendingScenario.measured,
          measuredName: pendingScenario.measuredName
        });
      else
        vscode.window.showWarningMessage(
          'The report changed before the saved scenario opened. Reopen the scenario with its original report.'
        );
      pendingScenario = null;
    }
    void sendSourceStatus();
  }
  function selectRegion(regionId, reveal = true, notify = true) {
    if (!report?.regions.some((r) => r.id === regionId)) return;
    selected = regionId;
    if (reveal) showExplorer();
    if (notify) panel?.webview.postMessage({ type: 'select', region: regionId });
    void sendSourceStatus();
  }
  async function openSource(regionId, index = 0, preserveFocus = false) {
    const sequence = ++sourceOpenSequence, currentReport = report;
    const region = report?.regions.find((r) => r.id === regionId);
    const location = region?.sources[index];
    const uri = location && sourceUri(location);
    if (!uri) {
      vscode.window.showInformationMessage(
        'No source location in this workspace. Set drperf.sourceRoot or export with --source-root.'
      );
      return;
    }
    try {
      const document = await vscode.workspace.openTextDocument(uri);
      if (sequence !== sourceOpenSequence || report !== currentReport) return;
      const line = Math.min(Math.max(0, location.line - 1), document.lineCount - 1);
      await vscode.window.showTextDocument(document, {
        viewColumn:
          panel?.viewColumn === vscode.ViewColumn.One
            ? vscode.ViewColumn.Two
            : vscode.ViewColumn.One,
        preserveFocus,
        preview: true,
        selection: new vscode.Range(line, 0, line, 0)
      });
      const warningKey = report.id+':'+uri.toString();
      if (stale(document, location) && !preserveFocus && !sourceWarnings.has(warningKey)) {
        sourceWarnings.add(warningKey);
        vscode.window.showWarningMessage(
          'Source has changed since this report was exported. Recorded formulas may be stale.'
        );
      }
    } catch (error) {
      vscode.window.showErrorMessage('Cannot open region source: ' + error.message);
    }
  }
  function graphFullscreen(enabled) {
    layoutQueue = layoutQueue.then(()=>applyGraphFullscreen(enabled));
    return layoutQueue;
  }
  async function applyGraphFullscreen(enabled) {
    try {
      const commands = await vscode.commands.getCommands(true);
      if (!commands.includes('vscode.getEditorLayout') || !commands.includes('vscode.setEditorLayout')) return;
      if (enabled && panel && !savedEditorLayout) {
        const layout = await vscode.commands.executeCommand('vscode.getEditorLayout');
        if (!layout?.groups) return;
        savedEditorLayout = layout;
        panel.reveal(panel.viewColumn, false);
        await vscode.commands.executeCommand('vscode.setEditorLayout',
          Navigation.expandedLayout(layout, panel.viewColumn));
      } else if (!enabled && savedEditorLayout) {
        const original = savedEditorLayout; savedEditorLayout = null;
        const current = await vscode.commands.executeCommand('vscode.getEditorLayout');
        // Do not undo editor groups the user added/removed while expanded.
        if (current?.groups && Navigation.leafCount(current) === Navigation.leafCount(original))
          await vscode.commands.executeCommand('vscode.setEditorLayout', original);
      }
    } catch (error) { output.appendLine('Graph layout: '+error.message); }
  }
  function showExplorer() {
    if (!report) {
      openReport();
      return;
    }
    if (panel) {
      panel.reveal(panel.viewColumn, true);
      return;
    }
    panel = vscode.window.createWebviewPanel(
      'drperf.explorer',
      'drperf · Region Explorer',
      vscode.ViewColumn.Beside,
      {
        enableScripts: true,
        retainContextWhenHidden: true,
        localResourceRoots: [vscode.Uri.joinPath(context.extensionUri, 'media')]
      }
    );
    webviewReady = false;
    const webview = panel.webview;
    const nonce = crypto.randomBytes(24).toString('base64');
    const media = (file) =>
      webview.asWebviewUri(vscode.Uri.joinPath(context.extensionUri, 'media', file));
    webview.html = `<!doctype html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
      <meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src ${webview.cspSource} data:; style-src ${webview.cspSource}; script-src 'nonce-${nonce}'; worker-src blob:; connect-src ${webview.cspSource};">
      <link rel="stylesheet" href="${media('explorer.css')}"><title>drperf Region Explorer</title></head>
      <body><div id="app" aria-live="polite"></div><script nonce="${nonce}" src="${media('expressions.js')}"></script><script nonce="${nonce}" src="${media('model.js')}"></script><script nonce="${nonce}" src="${media('analysis-client.js')}" data-expressions="${media('expressions.js')}" data-model="${media('model.js')}" data-worker="${media('analysis-worker.js')}"></script><script nonce="${nonce}" src="${media('execution-graph.js')}"></script><script nonce="${nonce}" src="${media('vendor/elk.bundled.js')}"></script><script nonce="${nonce}" src="${media('graph-layout.js')}"></script><script nonce="${nonce}" src="${media('explorer.js')}"></script></body></html>`;
    panel.onDidDispose(
      () => {
        void graphFullscreen(false);
        panel = null;
        webviewReady = false;
      },
      null,
      context.subscriptions
    );
    webview.onDidReceiveMessage(
      async (message) => {
        if (!message || typeof message.type !== 'string') return;
        if (message.type === 'ready') {
          webviewReady = true;
          sendModel();
        } else if (message.type === 'analysisFinished' && message.baseModelId === report?.id)
          analysisStatus = message;
        else if (message.type === 'configureSourceRoot')
          await vscode.commands.executeCommand(
            'workbench.action.openSettings',
            'drperf.sourceRoot'
          );
        else if (message.type === 'source' && typeof message.region === 'string')
          await openSource(message.region, Number.isInteger(message.index) ? message.index : 0);
        else if (message.type === 'exportGraphHtml' && report && message.modelId === report.id) {
          const snapshot = report;
          try {
            const uri = await vscode.window.showSaveDialog({
              defaultUri: reportUri && vscode.Uri.joinPath(reportUri, '..', path.basename(reportUri.path).replace(/\.json$/i, '') + '.graph.html'),
              filters: { 'Interactive graph': ['html'] }, saveLabel: 'Save graph HTML'
            });
            if (uri) {
              await vscode.workspace.fs.writeFile(uri, Buffer.from(graphHtml(snapshot, message.view || {})));
              vscode.window.showInformationMessage('Graph saved: ' + uri.fsPath + '. Open it in a browser.');
            }
          } catch (error) { vscode.window.showErrorMessage('Cannot export graph: ' + error.message); }
        }
        else if (message.type === 'graphFullscreen') await graphFullscreen(message.enabled === true);
        else if (message.type === 'select' && typeof message.region === 'string') {
          ++sourceOpenSequence;
          selectRegion(message.region, false, false);
          if (message.openSource !== false && report?.regions.find((r) => r.id === message.region)?.sources.length)
            await openSource(message.region, 0, true);
        } else if (message.type === 'reload') await reload();
        else if (message.type === 'loadValidationReport') {
          const uri = (
            await vscode.window.showOpenDialog({
              canSelectMany: false,
              openLabel: 'Compare against measured run',
              filters: { 'drperf report': ['drperf.json', 'json'] }
            })
          )?.[0];
          if (!uri) return;
          try {
            const measured = await readModel(uri);
            panel?.webview.postMessage({
              type: 'validationModel',
              model: measured,
              name: path.basename(uri.fsPath)
            });
          } catch (error) {
            vscode.window.showErrorMessage('Cannot load validation report: ' + error.message);
          }
        } else if (message.type === 'exportScenario' && message.scenario && report) {
          try {
            const result = Model.replay(report, message.scenario);
            const uri = await vscode.window.showSaveDialog({
              filters: { 'drperf scenario': ['json'] },
              saveLabel: 'Save scenario'
            });
            if (uri)
              await vscode.workspace.fs.writeFile(
                uri,
                Buffer.from(
                  JSON.stringify({ schema: 'drperf.scenario.v1', ...result }, null, 2) + '\n'
                )
              );
          } catch (error) {
            vscode.window.showErrorMessage(error.message);
          }
        }
      },
      null,
      context.subscriptions
    );
  }
  async function readModel(uri) {
    const info = await vscode.workspace.fs.stat(uri);
    if (info.size > 50 * 1024 * 1024)
      throw new Error('Report is larger than 50 MiB. Export fewer runs or lower --max-trace.');
    const bytes = await vscode.workspace.fs.readFile(uri);
    return Model.validate(JSON.parse(Buffer.from(bytes).toString('utf8')));
  }
  async function load(uri, isDemo = false) {
    const sequence = ++loadSequence;
    const parsed = await readModel(uri);
    if (sequence !== loadSequence) return;
    analysisStatus = null;
    ++sourceOpenSequence;
    sourceWarnings.clear();
    report = parsed;
    reportUri = uri;
    demo = isDemo;
    if (!report.regions.some((r) => r.id === selected)) selected = report.regions[0]?.id;
    context.workspaceState.update('drperf.lastReport', isDemo ? null : uri.toString());
    vscode.commands.executeCommand('setContext', 'drperf.reportLoaded', true);
    changed.fire();
    lensesChanged.fire();
    sendModel();
    watcher?.dispose();
    if (!isDemo) {
      watcher = vscode.workspace.createFileSystemWatcher(
        new vscode.RelativePattern(path.dirname(uri.fsPath), path.basename(uri.fsPath))
      );
      watcher.onDidChange(() => reload());
      watcher.onDidCreate(() => reload());
    }
  }
  async function reload() {
    if (!reportUri) return;
    try {
      await load(reportUri, demo);
    } catch (error) {
      vscode.window.showErrorMessage('Could not reload drperf report: ' + error.message);
    }
  }
  async function openReport(uri) {
    try {
      if (!(uri instanceof vscode.Uri)) {
        const chosen = await vscode.window.showOpenDialog({
          canSelectMany: false,
          filters: { 'drperf report': ['drperf.json', 'json'] }
        });
        uri = chosen?.[0];
      }
      if (!uri) return;
      await load(uri);
      showExplorer();
    } catch (error) {
      vscode.window.showErrorMessage('Cannot open drperf report: ' + error.message);
    }
  }
  async function openScenario(uri) {
    try {
      if (!report) {
        await openReport();
        if (!report) return;
      }
      if (!(uri instanceof vscode.Uri))
        uri = (
          await vscode.window.showOpenDialog({
            canSelectMany: false,
            openLabel: 'Open drperf scenario',
            filters: { 'drperf scenario': ['json'] }
          })
        )?.[0];
      if (!uri) return;
      if ((await vscode.workspace.fs.stat(uri)).size > 50 * 1024 * 1024)
        throw new Error('Scenario file is larger than 50 MiB.');
      const saved = JSON.parse(
        Buffer.from(await vscode.workspace.fs.readFile(uri)).toString('utf8')
      );
      const scenario = saved.scenario || saved;
      if (!Array.isArray(scenario.edits) || !Array.isArray(scenario.relations))
        throw new Error('Invalid saved scenario.');
      const expected =
        scenario.costBasis === 'recorded' &&
        report.measurement?.markerAdjustment !== 'none; marker API instructions retained'
          ? report.id + ':recorded'
          : report.id;
      if (saved.modelId && saved.modelId !== expected)
        throw new Error(
          'This scenario belongs to a different report. Open its original report first.'
        );
      pendingScenario = { scenario, modelId: report.id };
      analysisStatus = null;
      showExplorer();
      if (webviewReady) sendModel();
    } catch (error) {
      vscode.window.showErrorMessage('Cannot open scenario: ' + error.message);
    }
  }
  async function exportReport() {
    if (!vscode.workspace.isTrusted) {
      vscode.window.showWarningMessage(
        'Trust this workspace before running the drperf exporter. Existing reports can still be viewed.'
      );
      return;
    }
    const raw = (
      await vscode.window.showOpenDialog({
        canSelectFiles: false,
        canSelectFolders: true,
        canSelectMany: false,
        openLabel: 'Select raw drperf measurements'
      })
    )?.[0];
    if (!raw) return;
    const destination = await vscode.window.showSaveDialog({
      defaultUri: vscode.Uri.joinPath(raw, '..', 'regions.drperf.json'),
      filters: { 'drperf report': ['drperf.json'] }
    });
    if (!destination) return;
    const root =
      sourceRoot() ||
      vscode.workspace.getWorkspaceFolder(raw)?.uri.fsPath ||
      path.dirname(raw.fsPath);
    const script =
      configuration().get('exporterPath', '') || path.join(root, 'bin', 'drperf-export');
    const python = configuration().get('pythonPath', 'python3');
    await vscode.window.withProgress(
      {
        location: vscode.ProgressLocation.Notification,
        title: 'Exporting drperf region interfaces',
        cancellable: true
      },
      async (_, cancellation) => {
        try {
          await new Promise((resolve, reject) => {
            const child = execFile(
              python,
              [script, raw.fsPath, '--source-root', root, '-o', destination.fsPath],
              { cwd: root, maxBuffer: 8 * 1024 * 1024, timeout: 300000 },
              (error, stdout, stderr) => {
                output.append(stdout);
                output.append(stderr);
                if (error) reject(error);
                else resolve();
              }
            );
            const cancel = cancellation.onCancellationRequested(() => child.kill());
            child.once('exit', () => cancel.dispose());
          });
          await load(destination);
          showExplorer();
        } catch (error) {
          output.show();
          vscode.window.showErrorMessage('drperf export failed: ' + error.message);
        }
      }
    );
  }
  const provider = {
    onDidChangeTreeData: changed.event,
    getChildren(element) {
      if (!report || element?.leaf) return [];
      if (!element) return report.regions.map((region) => ({ region }));
      if (element.region)
        return element.region.states.map((state) => ({
          region: element.region,
          state,
          leaf: true
        }));
      return [];
    },
    getTreeItem(element) {
      const { region, state } = element;
      const item = new vscode.TreeItem(
        state || region.name,
        element.leaf || !region.states.length
          ? vscode.TreeItemCollapsibleState.None
          : vscode.TreeItemCollapsibleState.Collapsed
      );
      item.description = state ? 'PCV' : `${region.calls} calls`;
      item.tooltip =
        region.regimes.map((fit) => Model.formula(region, fit)).join('\n') ||
        'Insufficient varied states';
      item.command = {
        command: 'drperf.inspectRegion',
        title: 'Inspect performance interface',
        arguments: [region.id]
      };
      return item;
    }
  };
  context.subscriptions.push(vscode.window.registerTreeDataProvider('drperf.regions', provider));
  const selectors = ['python', 'c', 'cpp', 'rust'].map((language) => ({
    language,
    scheme: 'file'
  }));
  context.subscriptions.push(
    vscode.languages.registerCodeLensProvider(selectors, {
      onDidChangeCodeLenses: lensesChanged.event,
      provideCodeLenses(document) {
        if (!configuration().get('codeLens', true)) return [];
        return locations(document)
          .filter(({ location }) => location.line <= document.lineCount)
          .map(({ region, location }) => {
            const title = stale(document, location)
              ? 'drperf: source changed · inspect recorded interface'
              : `drperf: ${Model.formula(region)} · ${region.calls} calls`;
            return new vscode.CodeLens(
              new vscode.Range(location.line - 1, 0, location.line - 1, 0),
              { command: 'drperf.inspectRegion', title, arguments: [region.id] }
            );
          });
      }
    })
  );
  context.subscriptions.push(
    vscode.languages.registerHoverProvider(selectors, {
      provideHover(document, position) {
        const match = locations(document).find(
          ({ location }) => location.line === position.line + 1
        );
        if (!match) return;
        const markdown = new vscode.MarkdownString();
        markdown.appendText(match.region.name + ' — CPU instructions per call\n\n');
        match.region.regimes.forEach((fit) =>
          markdown.appendCodeblock(Model.formula(match.region, fit), 'text')
        );
        markdown.appendText(
          stale(document, match.location)
            ? 'Source changed since export.'
            : 'Recorded interface; valid only at observed states within checker tolerance.'
        );
        return new vscode.Hover(markdown);
      }
    })
  );
  context.subscriptions.push(
    vscode.window.onDidChangeTextEditorSelection((event) => {
      if (panel && configuration().get('followCursor', true) &&
          (event.kind === vscode.TextEditorSelectionChangeKind.Keyboard ||
           event.kind === vscode.TextEditorSelectionChangeKind.Mouse)) {
        const region = currentRegion(event.textEditor);
        if (region && region !== selected) selectRegion(region, false);
      }
    })
  );
  context.subscriptions.push(
    vscode.workspace.onDidChangeTextDocument((event) => {
      lensesChanged.fire();
      if (locations(event.document).length) scheduleSourceStatus();
    })
  );
  context.subscriptions.push(
    vscode.workspace.onDidChangeConfiguration(() => {
      lensesChanged.fire();
      scheduleSourceStatus();
    })
  );
  for (const [command, callback] of Object.entries({
    'drperf.openReport': openReport,
    'drperf.openScenario': openScenario,
    'drperf.showExplorer': showExplorer,
    'drperf.exportReport': exportReport,
    'drperf.refresh': reload,
    'drperf.openJointDemo': async () => {
      await load(vscode.Uri.joinPath(context.extensionUri, 'demo', 'refined.drperf.json'), true);
      const baseline = report;
      const saved = JSON.parse(
        Buffer.from(
          await vscode.workspace.fs.readFile(
            vscode.Uri.joinPath(context.extensionUri, 'demo', 'joint.scenario.json')
          )
        ).toString('utf8')
      );
      const measured = await readModel(
        vscode.Uri.joinPath(context.extensionUri, 'demo', 'joint-changed.drperf.json')
      );
      if (report !== baseline) return;
      if (saved.modelId !== baseline.id)
        throw new Error('Bundled scenario does not match its report.');
      pendingScenario = {
        scenario: saved.scenario,
        modelId: baseline.id,
        measured,
        measuredName: 'Measured joint producer/expansion change'
      };
      analysisStatus = null;
      showExplorer();
      sendModel();
    },
    'drperf.openRefinedDemo': async () => {
      await load(vscode.Uri.joinPath(context.extensionUri, 'demo', 'refined.drperf.json'), true);
      selected = 'lookup';
      showExplorer();
      sendModel();
    },
    'drperf.openDemo': async () => {
      await load(vscode.Uri.joinPath(context.extensionUri, 'demo', 'pipeline.drperf.json'), true);
      showExplorer();
    },
    'drperf.inspectRegion': async (region) => {
      if (!report) {
        await openReport();
        return;
      }
      const candidate = typeof region === 'string' ? region : currentRegion();
      if (candidate) {
        selectRegion(candidate);
        if (report.regions.find((r) => r.id === candidate)?.sources.length)
          await openSource(candidate, 0, true);
      } else showExplorer();
    }
  }))
    context.subscriptions.push(vscode.commands.registerCommand(command, callback));
  const saved = context.workspaceState.get('drperf.lastReport');
  if (saved)
    load(vscode.Uri.parse(saved)).catch((error) =>
      output.appendLine('Previous report unavailable: ' + error.message)
    );
  return {
    load,
    getReport: () => report,
    currentRegion,
    getSourceStatus,
    getAnalysisStatus: () => analysisStatus
  };
}

function deactivate() {}
module.exports = { activate, deactivate };
