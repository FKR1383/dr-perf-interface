/* ELK owns placement and routing. Boundary ports let each parent lay out its
 * children vertically while the top-level workflow remains horizontal. */
(function(root,factory){
  if(typeof module==='object'&&module.exports)module.exports=factory(require('./vendor/elk.bundled'));
  else root.DrperfLayout=factory(root.ELK);
})(typeof globalThis!=='undefined'?globalThis:this,function(ELK){
  'use strict';
  const elk=new ELK();
  async function layout(roots,nodes,edges){
    const ids=new Map([...nodes.keys()].map((key,i)=>[key,'n'+i]));
    const reverse=new Map([...ids].map(([key,id])=>[id,key]));
    const parents=new Map(),graphs=new Map(),segments=new Map();
    const options={
      'elk.algorithm':'layered','elk.hierarchyHandling':'SEPARATE_CHILDREN',
      'elk.edgeRouting':'ORTHOGONAL',
      'elk.layered.considerModelOrder.strategy':'NODES_AND_EDGES',
      // forceNodeModelOrder can move FIXED_POS ports in ELK 0.12. The order
      // edges below preserve sibling order without breaking boundary routing.
      'elk.layered.cycleBreaking.strategy':'MODEL_ORDER',
      'elk.layered.nodePlacement.strategy':'SIMPLE',
      'elk.spacing.nodeNode':'40','elk.layered.spacing.nodeNodeBetweenLayers':'40',
      'elk.randomSeed':'1'
    };
    let nextOrder=0;
    function ordered(keys){
      return keys.slice(1).map((key,i)=>({id:'order'+nextOrder++,sources:[ids.get(keys[i])],targets:[ids.get(key)],
        layoutOptions:{'elk.layered.priority.direction':'1000'}}));
    }
    function node(key,parent=null){
      const n=nodes.get(key);parents.set(key,parent);
      const g={id:ids.get(key),width:n.width,height:n.header,
        layoutOptions:{...options,'elk.direction':'DOWN','elk.portConstraints':'FIXED_SIDE',
          'elk.padding':`[top=${n.header+20},left=20,bottom=20,right=20]`},
        ports:[],children:n.children.map(child=>node(child,key)),edges:ordered(n.children)};
      graphs.set(key,g);return g;
    }
    const root={id:'root',layoutOptions:{...options,'elk.direction':'RIGHT',
      'elk.layered.spacing.nodeNodeBetweenLayers':'60','elk.padding':'[top=24,left=24,bottom=24,right=24]'},
      children:roots.map(key=>node(key)),edges:ordered(roots)};
    graphs.set(null,root);
    function ancestors(key){const path=[key];while(key!==null){key=parents.get(key);path.push(key);}return path;}
    function port(key,i,side){
      const id=`p${i}${side}_${ids.get(key)}`;
      graphs.get(key).ports.push({id,width:0,height:0,layoutOptions:{'elk.port.side':side==='s'?'EAST':'WEST'}});
      return id;
    }
    edges.forEach((e,i)=>{
      const sourcePath=ancestors(e.source),targetPath=ancestors(e.target);
      const common=sourcePath.find(key=>targetPath.includes(key));
      const parts=[];
      function ascend(key,side){
        let endpoint=key===common?port(key,i,side):ids.get(key);
        const chain=[];
        while(key!==common&&parents.get(key)!==common){
          const parent=parents.get(key),boundary=port(parent,i,side);
          chain.push({parent,source:side==='s'?endpoint:boundary,target:side==='s'?boundary:endpoint});
          key=parent;endpoint=boundary;
        }
        return {endpoint,chain};
      }
      const s=ascend(e.source,'s'),t=ascend(e.target,'t');
      parts.push(...s.chain,{parent:common,source:s.endpoint,target:t.endpoint},...t.chain.reverse());
      parts.forEach((p,j)=>{
        const id=`e${i}_${j}`;segments.set(id,{edge:i,order:j});
        graphs.get(p.parent).edges.push({id,sources:[p.source],targets:[p.target]});
      });
    });
    async function arrange(key){
      const graph=graphs.get(key);
      if(!graph.children.length&&key!==null)return graph;
      const children=await Promise.all(graph.children.map(child=>arrange(reverse.get(child.id))));
      // Fix the ports computed inside each child before routing outside it.
      // Otherwise a second layout can move a boundary port and break its edge.
      const input={...graph,children:children.map(child=>({id:child.id,width:child.width,height:child.height,
        ports:child.ports,
        layoutOptions:{'elk.portConstraints':'FIXED_POS'}}))};
      const result=key===null?await elk.layout(input):(await elk.layout({id:'frame_'+graph.id,
        layoutOptions:{'elk.algorithm':'fixed','elk.hierarchyHandling':'SEPARATE_CHILDREN'},
        children:[input]})).children[0];
      const originals=new Map(children.map(child=>[child.id,child]));
      result.children=result.children.map(child=>({...originals.get(child.id),...child,
        children:originals.get(child.id).children,edges:originals.get(child.id).edges}));
      return result;
    }
    const result=await arrange(null);
    const boxes=new Map(),pieces=new Map(),routes=new Map();
    function collect(n,x=0,y=0){
      x+=n.x||0;y+=n.y||0;
      if(reverse.has(n.id))boxes.set(reverse.get(n.id),{x,y,width:n.width,height:n.height});
      for(const e of n.edges||[]){
        const segment=segments.get(e.id);if(!segment)continue;
        if(!e.sections?.length)throw new Error('ELK did not route region relationship '+segment.edge);
        if(!pieces.has(segment.edge))pieces.set(segment.edge,[]);
        pieces.get(segment.edge).push({order:segment.order,sections:e.sections.map(s=>[s.startPoint,...(s.bendPoints||[]),s.endPoint].map(p=>({x:p.x+x,y:p.y+y})))});
      }
      for(const child of n.children||[])collect(child,x,y);
    }
    collect(result);
    for(const [i,parts]of pieces){
      // Join boundary segments so a wait has one arrowhead at its real target.
      const path=[];
      for(const part of parts.sort((a,b)=>a.order-b.order))for(const section of part.sections){
        const previous=path[path.length-1],first=section[0];
        if(previous&&Math.abs(previous.x-first.x)<.01&&Math.abs(previous.y-first.y)<.01)path.push(...section.slice(1));
        else if(previous)throw new Error('Disconnected wait route '+i+': '+JSON.stringify([previous,first]));
        else path.push(...section);
      }
      routes.set(i,[path]);
    }
    return {width:result.width,height:result.height,boxes,routes};
  }
  return {layout};
});
