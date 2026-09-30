'use strict';
const fs = require('node:fs');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const assert = require('node:assert/strict');
const {chromium} = require('playwright');
const {graphHtml} = require('../graph-export');
(async () => {
  const source = process.env.DRPERF_UI_GRAPH_PROFILE || path.join(__dirname, '../demo/pipeline.drperf.json');
  const report = JSON.parse(fs.readFileSync(source, 'utf8'));
  const file = path.resolve(__dirname, '../../../out/explorer-ui/ditto-full.graph.html');
  fs.mkdirSync(path.dirname(file), {recursive:true});
  fs.writeFileSync(file, graphHtml(report, {mode:'top'}));
  const browser = await chromium.launch({headless:true});
  try {
    const page = await browser.newPage({viewport:{width:1600,height:1000}});
    async function graphAction(name) {
      await page.locator('.execution-more>summary').click();
      await page.getByRole('button',{name,exact:typeof name==='string'}).click();
    }
    const errors=[], network=[];
    page.on('pageerror', e=>errors.push(e.message));
    await page.route(/^https?:/, route=>{network.push(route.request().url());return route.abort();});
    await page.goto(pathToFileURL(file).href);
    await page.locator('.execution-graph[aria-busy="false"] .execution-svg').waitFor({timeout:60000});
    assert.match(await page.locator('.execution-scope').textContent(),new RegExp(report.regions.length+' regions'));
    assert.equal(await page.getByRole('button',{name:'Export graph as HTML',exact:true}).count(),0);
    const viewport=page.viewportSize();
    const initialCanvas=await page.locator('.execution-canvas').boundingBox();
    const initialGraph=await page.locator('.execution-svg').boundingBox();
    assert.ok(initialCanvas.height>=viewport.height*.9,'graph occupies at least 90% of screen height by default');
    assert.ok(initialCanvas.width>=viewport.width*.97,'graph uses the available width');
    assert.ok(initialGraph.x>=initialCanvas.x&&initialGraph.y>=initialCanvas.y&&
      initialGraph.x+initialGraph.width<=initialCanvas.x+initialCanvas.width+1&&
      initialGraph.y+initialGraph.height<=initialCanvas.y+initialCanvas.height+1,'initial graph fits inside the visible canvas');
    assert.equal(await page.locator('.execution-inspector').isVisible(),false);
    await page.locator('.execution-more>summary').click();
    assert.equal((await page.locator('.execution-canvas').boundingBox()).height,initialCanvas.height,'menu overlays instead of shrinking graph');
    await page.keyboard.press('Escape');
    assert.equal(await page.locator('.execution-more').getAttribute('open'),null);
    await page.getByRole('button',{name:'Show details',exact:true}).click();
    assert.equal(await page.locator('.execution-inspector').isVisible(),true);
    assert.ok((await page.locator('.execution-canvas').boundingBox()).height<initialCanvas.height-100);
    await page.getByRole('button',{name:'Hide details',exact:true}).click();
    assert.equal((await page.locator('.execution-canvas').boundingBox()).height,initialCanvas.height);
    await page.screenshot({path:path.join(path.dirname(file),'ditto-graph-default.png')});
    await page.getByRole('button',{name:'Show details',exact:true}).click();
    if(report.regions.length===105) {
      await page.evaluate(()=>{
        const original=window.DrperfLayout.layout;
        window.DrperfLayout.layout=(...args)=>new Promise(resolve=>setTimeout(resolve,120)).then(()=>original(...args));
      });
      async function horizontalToggle(before,after,keyboard=false,uncached=false){
        const toggle=page.getByRole('button',{name:before,exact:true});
        await toggle.scrollIntoViewIfNeeded();
        const b=await toggle.boundingBox();
        const beforeScroll=await page.locator('.execution-canvas').evaluate(e=>({x:e.scrollLeft,y:e.scrollTop}));
        await page.evaluate(()=>window.graphBeforeExpand=document.querySelector('.execution-svg'));
        if(keyboard){await toggle.focus();await page.keyboard.press('Enter');}
        else await page.mouse.click(b.x+b.width/2,b.y+b.height/2);
        if(uncached) {
          assert.equal(await page.evaluate(()=>document.querySelector('.execution-svg')===window.graphBeforeExpand),true,'keep previous graph during ELK layout');
          assert.equal(await page.locator('.execution-graph').getAttribute('aria-busy'),'true');
        }
        await page.locator('.execution-graph[aria-busy="false"] .execution-svg').waitFor({timeout:60000});
        const next=page.getByRole('button',{name:after,exact:true});
const afterScroll=await page.locator('.execution-canvas').evaluate(e=>({x:e.scrollLeft,y:e.scrollTop,maxX:e.scrollWidth-e.clientWidth,maxY:e.scrollHeight-e.clientHeight}));
        assert.ok(Math.abs(afterScroll.x-Math.min(beforeScroll.x,afterScroll.maxX))<=2,'expansion does not pan the whole graph horizontally');
        assert.ok(Math.abs(afterScroll.y-Math.min(beforeScroll.y,afterScroll.maxY))<=2,'expansion does not pan the whole graph vertically');
        if(keyboard)assert.equal(await next.evaluate(e=>e===document.activeElement),true,'restore keyboard focus');
      }
      await horizontalToggle('Expand worker.get_finished','Collapse worker.get_finished',false,true);
      await horizontalToggle('Expand worker.poll','Collapse worker.poll',true,true);
      await horizontalToggle('Collapse worker.poll','Expand worker.poll',true);
      await horizontalToggle('Collapse worker.get_finished','Expand worker.get_finished');
      await page.getByRole('button',{name:'Fit graph',exact:true}).click();
      await horizontalToggle('Expand sched.build_meta','Collapse sched.build_meta',false,true);
      await horizontalToggle('Collapse sched.build_meta','Expand sched.build_meta');
      await graphAction('100%');
    }
    await page.getByRole('button',{name:'Expand all',exact:true}).click();
    await page.locator('.execution-graph[aria-busy="false"] .execution-svg').waitFor({timeout:60000});
    assert.equal(await page.evaluate(()=>new Set([...document.querySelectorAll('.execution-node')].map(n=>n.dataset.region)).size),report.regions.length);
    assert.equal(await page.locator('.execution-edge.wait').evaluateAll(es=>es.filter(e=>e.dataset.source===e.dataset.target).length),0);
    // Real pointer clicks on box padding select the cell, not just its name.
    const leaf=page.locator('.execution-node').filter({hasNot:page.locator('.execution-toggle')}).last();
    const key=await leaf.getAttribute('data-path'),id=await leaf.getAttribute('data-region');
    const beforeFill=await leaf.locator(':scope > rect').evaluate(e=>getComputedStyle(e).fill);
    const leafBox=await leaf.locator(':scope > rect').boundingBox();
    // Offsets are screen pixels; preserve a padding hit when Fit scales SVG.
    await leaf.locator(':scope > rect').click({position:{x:leafBox.width*.03,y:leafBox.height*.3}});
    assert.equal(await page.locator('.execution-node.highlighted').getAttribute('data-path'),key);
    assert.equal(await page.locator('.execution-node.selected').count(),1);
    assert.equal(await page.locator('.execution-inspector h1').textContent(),id);
    assert.notEqual(await page.locator('.execution-node.selected>rect').evaluate(e=>getComputedStyle(e).fill),beforeFill);
    const parent=page.locator('.execution-node').filter({has:page.locator('.execution-toggle')}).first();
    if(await parent.count()) {
      const parentId=await parent.getAttribute('data-region');
      const parentRect=parent.locator(':scope > rect');
      const parentBox=await parentRect.boundingBox();
      const scale=parentBox.width/Number(await parentRect.getAttribute('width'));
      await parentRect.click({position:{x:8*scale,y:12*scale}});
      assert.equal(await page.locator('.execution-inspector h1').textContent(),parentId);
      const toggle=page.locator('.execution-node.selected .execution-toggle');
      await toggle.click();
      await page.locator('.execution-graph[aria-busy="false"] .execution-svg').waitFor({timeout:60000});
      assert.equal(await page.locator('.execution-inspector h1').textContent(),parentId,'toggle does not select a different cell');
      await page.getByRole('button',{name:'Expand all',exact:true}).click();
      await page.locator('.execution-graph[aria-busy="false"] .execution-svg').waitFor({timeout:60000});
    }
    if(report.regions.length===105) {
      assert.equal(await page.locator('.execution-node').count(),133);
      assert.equal(await page.locator('.execution-edge.wait').count(),1);
      assert.equal(await page.locator('.execution-edge-label,.execution-port-label').count(),0,'arrows have no duplicate labels');
      assert.equal(await page.locator('.execution-node .formula,.execution-node .execution-formula').count(),0);
      await page.getByRole('button',{name:'Select region store.drain',exact:true}).click();
    await page.locator('.execution-graph[aria-busy="false"] .execution-svg').waitFor({timeout:60000});
      assert.equal(await page.locator('.execution-node').count(),133,'selection preserves expansion');
      assert.equal(await page.locator('.execution-inspector h1').textContent(),'store.drain');
      assert.ok(await page.locator('.execution-inspector .formula').count()>0);
      const left=await page.locator('.execution-canvas').boundingBox(),right=await page.locator('.execution-inspector').boundingBox();
      assert.ok(left.y+left.height<=right.y,'details are below the graph');
      await page.locator('.execution-canvas').evaluate(e=>e.scrollTop=500);
      const scroll=await page.locator('.execution-canvas').evaluate(e=>e.scrollTop);
      await page.evaluate(()=>[...document.querySelectorAll('.execution-region-name')].find(e=>e.textContent==='load.plan').click());
      assert.equal(await page.locator('.execution-canvas').evaluate(e=>e.scrollTop),scroll,'selection preserves graph scroll');
      assert.equal(await page.locator('.execution-inspector h1').textContent(),'load.plan');
      await graphAction('Collapse all');
    await page.locator('.execution-graph[aria-busy="false"] .execution-svg').waitFor({timeout:60000});
      await page.getByRole('button',{name:'Select region worker.get_finished',exact:true}).click();
      await page.getByRole('button',{name:'Reveal wait: store.drain waits on carrier.transfer · 9 observations',exact:true}).click();
    await page.locator('.execution-graph[aria-busy="false"] .execution-svg').waitFor({timeout:60000});
      assert.ok(await page.locator('.execution-node[data-region="carrier.transfer"]').count()>0);
      assert.ok(await page.locator('.execution-node[data-region="store.drain"]').count()>0);
    }
    await page.getByRole('button',{name:'Zoom in',exact:true}).click();
    await page.locator('.execution-graph[aria-busy="false"] .execution-svg').waitFor({timeout:60000});
    assert.notEqual(await page.locator('.execution-zoom').textContent(),'100%');
    await page.keyboard.press('Escape');
    assert.ok(await page.locator('body').evaluate(e=>e.classList.contains('graph-fullscreen')));
    await graphAction('Collapse all');
    await page.locator('.execution-graph[aria-busy="false"] .execution-svg').waitFor({timeout:60000});
    const positions=await page.locator('.execution-node>rect').evaluateAll(es=>es.map(e=>({x:e.getAttribute('x'),y:e.getAttribute('y')})));
    assert.ok(positions.every((p,i)=>i===0||Number(p.x)>Number(positions[i-1].x)),'regions stay in left-to-right order');
    await page.getByRole('button',{name:'Fit graph',exact:true}).click();
    await page.screenshot({path:path.join(path.dirname(file),'ditto-split-view.png')});
    await graphAction('Show sequence');
    await page.locator('.execution-graph[aria-busy="false"] .execution-svg').waitFor({timeout:60000});
    assert.ok(await page.locator('.execution-edge.sequence').count()>0);
    await graphAction('Hide sequence');
    await page.locator('.execution-graph[aria-busy="false"] .execution-svg').waitFor({timeout:60000});
    assert.equal(await page.locator('.execution-edge.sequence').count(),0);
    await page.setViewportSize({width:420,height:780});
    await page.reload();
    await page.locator('.execution-graph[aria-busy="false"] .execution-svg').waitFor({timeout:60000});
    const narrowCanvas=await page.locator('.execution-canvas').boundingBox();
    const narrowGraph=await page.locator('.execution-svg').boundingBox();
    assert.ok(narrowCanvas.height>=780*.9,'narrow graph also occupies 90% of the screen');
    assert.ok(narrowGraph.x>=narrowCanvas.x&&narrowGraph.x+narrowGraph.width<=narrowCanvas.x+narrowCanvas.width+1,'narrow initial fit');
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,'no page overflow');
    await page.locator('.execution-more>summary').click();
    const popup=await page.locator('.execution-menu').boundingBox();
    assert.ok(popup.x>=0&&popup.x+popup.width<=420,'tools remain within narrow screen');
    await page.keyboard.press('Escape');
    assert.deepEqual(errors,[]);assert.deepEqual(network,[]);
    console.log(`Offline graph passed: ${report.regions.length} regions, ${fs.statSync(file).size} bytes; ${file}`);
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
