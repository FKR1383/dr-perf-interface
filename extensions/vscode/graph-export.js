'use strict';
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { gzipSync } = require('node:zlib');

// A portable snapshot: all assets and the complete report travel in one file.
// Report strings are compressed data, never interpolated as executable code.
function graphHtml(report, view = {}) {
  const nonce = crypto.randomBytes(24).toString('base64');
  const read = name => fs.readFileSync(path.join(__dirname, 'media', name), 'utf8');
  const script = (source, attrs = '') => `<script nonce="${nonce}" ${attrs}>${source.replace(/<\/script/gi, '<\\/script')}</script>`;
  const dataUrl = name => 'data:text/javascript;base64,' + Buffer.from(read(name)).toString('base64');
  const payload = gzipSync(JSON.stringify({ report, view })).toString('base64');
  return `<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'nonce-${nonce}'; style-src 'unsafe-inline'; worker-src blob:; connect-src data:; img-src data:;">
<title>drperf region graph</title><style>${read('explorer.css')}</style></head>
<body><template id="elk-license">ELK.js 0.12.0 — https://github.com/kieler/elkjs
${read('vendor/ELK-LICENSE.md').replaceAll('&','&amp;').replaceAll('<','&lt;')}</template><div id="app">Loading embedded profile…</div>
${script('window.DrperfStandalone = true;')}
${script(read('expressions.js'))}${script(read('model.js'))}
${script(read('analysis-client.js'), `data-expressions="${dataUrl('expressions.js')}" data-model="${dataUrl('model.js')}" data-worker="${dataUrl('analysis-worker.js')}"`)}
${script(read('execution-graph.js'))}${script(read('vendor/elk.bundled.js'))}${script(read('graph-layout.js'))}${script(read('explorer.js'))}
${script(`(async () => {
  try {
    const bytes = Uint8Array.from(atob('${payload}'), c => c.charCodeAt(0));
    const json = await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).text();
    const {report, view} = JSON.parse(json);
    window.DrperfStandalone = view;
    window.postMessage({type:'model', model:report, selected:view.selected}, '*');
  } catch (error) {
    document.getElementById('app').textContent = 'Cannot open graph: '+error.message;
  }
})();`)}
</body></html>`;
}
module.exports = { graphHtml };
