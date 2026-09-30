'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),os=require('node:os'),path=require('node:path'),vm=require('node:vm');
const {createRequire}=require('node:module');
test('host uses snapshot, avoids graph selection echoes and follows only user cursor events',async()=>{
  const folder=fs.mkdtempSync(path.join(os.tmpdir(),'drperf-nav-'));
  const root=path.resolve(__dirname,'..');
  const model=JSON.parse(fs.readFileSync(path.join(root,'demo/pipeline.drperf.json'),'utf8'));
  const source=fs.readFileSync(path.join(root,'demo/pipeline.c'),'utf8');
  const snapshot=path.join(folder,'snapshot');
  for(const r of model.regions)for(const s of r.sources){
    const dest=path.join(snapshot,s.path);fs.mkdirSync(path.dirname(dest),{recursive:true});fs.writeFileSync(dest,source);
  }
  model.provenance.sourceRoot=snapshot;
  fs.writeFileSync(path.join(folder,'profile.json'),JSON.stringify(model));
  const noop=()=>({dispose(){}}),commands=new Map(),messages=[],shown=[],warnings=[];
  let receive,selection,layout={orientation:0,groups:[{size:.5},{size:.5}]};
  class Uri{
    constructor(p){this.fsPath=p;this.path=p;this.scheme='file';}
    toString(){return 'file://'+this.fsPath;}
    static file(p){return new Uri(p);}
    static joinPath(u,...parts){return new Uri(path.join(u.fsPath,...parts));}
  }
  class Range{constructor(line){this.start={line};this.end={line};}}
  const vscode={Uri,Range,EventEmitter:class{event=noop;fire(){};dispose(){}},
    ViewColumn:{One:1,Two:2,Beside:-2},TextEditorSelectionChangeKind:{Keyboard:1,Mouse:2,Command:3},
    commands:{registerCommand:(id,cb)=>(commands.set(id,cb),noop()),
      getCommands:async()=>['vscode.getEditorLayout','vscode.setEditorLayout'],
      executeCommand:async(id,value)=>{
        if(id==='vscode.getEditorLayout')return structuredClone(layout);
        if(id==='vscode.setEditorLayout')layout=structuredClone(value);
      }},
    languages:{registerCodeLensProvider:noop,registerHoverProvider:noop},
    RelativePattern:class{},
    workspace:{workspaceFolders:[{uri:Uri.file(folder)}],textDocuments:[],
      getWorkspaceFolder:()=>({uri:Uri.file(folder)}),getConfiguration:()=>({get:(key,def)=>def}),
      fs:{stat:async u=>fs.statSync(u.fsPath),readFile:async u=>fs.readFileSync(u.fsPath),writeFile:async(u,b)=>fs.writeFileSync(u.fsPath,b)},
      createFileSystemWatcher:()=>({dispose(){},onDidChange:noop,onDidCreate:noop}),
      onDidChangeTextDocument:noop,onDidChangeConfiguration:noop,
      openTextDocument:async u=>({uri:u,version:1,lineCount:source.split('\n').length,getText:()=>fs.readFileSync(u.fsPath,'utf8')})},
    window:{createOutputChannel:()=>({dispose(){},appendLine(){}}),registerTreeDataProvider:noop,
      onDidChangeTextEditorSelection:cb=>(selection=cb,noop()),
      createWebviewPanel:()=>({viewColumn:2,reveal(){},onDidDispose:noop,
        webview:{asWebviewUri:u=>u.toString(),postMessage:m=>messages.push(m),onDidReceiveMessage:cb=>(receive=cb,noop())}}),
      showSaveDialog:async()=>Uri.file(path.join(folder,'graph.html')),
      showTextDocument:async(doc,options)=>{
        shown.push(doc.uri.fsPath);
        selection({kind:3,textEditor:{document:doc,selection:{active:{line:options.selection.start.line}}}});
      },showWarningMessage:m=>warnings.push(m),showErrorMessage:m=>warnings.push(m),showInformationMessage:m=>warnings.push(m)}
  };
  const file=path.join(root,'extension.js'),required=createRequire(file),module={exports:{}};
  vm.runInNewContext(fs.readFileSync(file,'utf8'),{module,exports:module.exports,
    require:n=>n==='vscode'?vscode:required(n),Buffer,setTimeout,clearTimeout,structuredClone});
  const subscriptions=[];
  try{
    const api=module.exports.activate({subscriptions,extensionUri:Uri.file(root),workspaceState:{get(){},update(){}}});
    await api.load(Uri.file(path.join(folder,'profile.json')));
    assert.ok((await api.getSourceStatus('enqueue')).every(s=>s.state==='matches'));
    await commands.get('drperf.showExplorer')();
    await receive({type:'ready'});messages.length=0;
    await receive({type:'exportGraphHtml',modelId:'stale',view:{}});
    assert.equal(fs.existsSync(path.join(folder,'graph.html')),false);
    await receive({type:'exportGraphHtml',modelId:model.id,view:{mode:'top',selected:'enqueue'}});
    assert.match(fs.readFileSync(path.join(folder,'graph.html'),'utf8'),/DecompressionStream/);
    assert.match(warnings.pop(),/Graph saved/);
    fs.unlinkSync(path.join(folder,'graph.html'));
    const dialog=vscode.window.showSaveDialog;
    vscode.window.showSaveDialog=async()=>undefined;
    await receive({type:'exportGraphHtml',modelId:model.id});
    assert.equal(fs.existsSync(path.join(folder,'graph.html')),false);
    vscode.window.showSaveDialog=dialog;
    await receive({type:'select',region:'enqueue',openSource:false});
    assert.equal(shown.length,0);
    assert.equal(messages.filter(m=>m.type==='select').length,0);
    await receive({type:'source',region:'enqueue',index:0});
    assert.ok(shown[0].startsWith(snapshot+path.sep));assert.deepEqual(warnings,[]);
    assert.equal(messages.filter(m=>m.type==='select').length,0,'programmatic source opening does not feed back');
    const location=model.regions.find(r=>r.id==='copy').sources[0];
    const document=await vscode.workspace.openTextDocument(Uri.file(path.join(snapshot,location.path)));
    selection({kind:1,textEditor:{document,selection:{active:{line:location.line-1}}}});
    assert.equal(messages.filter(m=>m.type==='select').at(-1).region,'copy');
    await receive({type:'graphFullscreen',enabled:true});assert.equal(layout.groups[1].size,.98);
    await receive({type:'graphFullscreen',enabled:false});assert.equal(layout.groups[1].size,.5);
  }finally{
    // Mock panel intentionally has no asynchronous disposal behavior.
    fs.rmSync(folder,{recursive:true,force:true});
  }
});
