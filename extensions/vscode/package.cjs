/* Preserve monorepo-relative README links in a portable VSIX. */
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const elkRoot = path.dirname(require.resolve('elkjs/package.json'));
fs.mkdirSync(path.join(__dirname, 'media/vendor'), {recursive:true});
fs.copyFileSync(path.join(elkRoot, 'lib/elk.bundled.js'), path.join(__dirname, 'media/vendor/elk.bundled.js'));
fs.copyFileSync(path.join(elkRoot, 'LICENSE.md'), path.join(__dirname, 'media/vendor/ELK-LICENSE.md'));
const { execFileSync, spawnSync } = require('node:child_process');
const commit = execFileSync('git', ['rev-parse', 'HEAD'], {
  cwd: __dirname,
  encoding: 'utf8'
}).trim();
const repository = 'MJChku/dr-perf-interface';
const result = spawnSync(
  process.execPath,
  [
    require.resolve('@vscode/vsce/vsce'),
    'package',
    '--skip-license',
    '--baseContentUrl',
    `https://github.com/${repository}/blob/${commit}/extensions/vscode`,
    '--baseImagesUrl',
    `https://raw.githubusercontent.com/${repository}/${commit}/extensions/vscode`,
    ...process.argv.slice(2)
  ],
  { cwd: __dirname, stdio: 'inherit' }
);
if (result.error) throw result.error;
process.exitCode = result.status ?? 1;
