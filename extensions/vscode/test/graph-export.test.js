'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const {gunzipSync}=require('node:zlib');
const {graphHtml}=require('../graph-export');
test('HTML embeds report and view as compressed data, never executable markup',()=>{
  const report={id:'</script><script>EVIL()</script>',regions:[]};
  const view={selected:'</script><img src=x onerror=EVIL()>',mode:'top',expanded:['child']};
  const html=graphHtml(report,view);
  assert.equal(html.includes('EVIL()'),false);
  const payload=html.match(/atob\('([A-Za-z0-9+/=]+)'\)/)[1];
  assert.deepEqual(JSON.parse(gunzipSync(Buffer.from(payload,'base64'))),{report,view});
  assert.match(html,/connect-src data:/);
});
