"use strict";

// Geometry-only navigation. No prescribed routes; every route is calculated from
// the current position, free-space boundaries, and physical scenery footprints.
class FreeNavigation {
  constructor() { this.obstacles = []; this.areas = []; this.clearance = .65; }
  addArea(x, z, radius, group = "hub") { this.areas.push({x,z,radius,group}); }
  addObstacle(x, z, width, depth) { this.obstacles.push({x,z,hw:width/2,hz:depth/2}); }
  clear(x, z, group = "hub") {
    const inside = group === "hub"
      ? x > -55 && x < 55 && z > -33 && z < 106
      : this.areas.some(a => a.group === group && Math.hypot(a.x-x,a.z-z) < a.radius);
    return inside && !this.obstacles.some(o => Math.abs(o.x-x) < o.hw+this.clearance && Math.abs(o.z-z) < o.hz+this.clearance);
  }
  line(a,b,group) {
    if(![a.x,a.z,b.x,b.z].every(Number.isFinite))return false;
    const n = Math.ceil(Math.hypot(b.x-a.x,b.z-a.z)/.3);
    for(let i=0;i<=n;i++) { const t=n?i/n:0; if(!this.clear(a.x+(b.x-a.x)*t,a.z+(b.z-a.z)*t,group)) return false; }
    return true;
  }
  nearest(point, group) {
    if(this.clear(point.x,point.z,group)) return {x:point.x,z:point.z};
    for(let radius=.5;radius<=18;radius+=.5) for(let i=0;i<32;i++) {
      const p={x:point.x+Math.cos(i*Math.PI/16)*radius,z:point.z+Math.sin(i*Math.PI/16)*radius};
      if(this.clear(p.x,p.z,group)) return p;
    }
    return null;
  }
  route(start, goal, group="hub") {
    const a=this.nearest(start,group), b=this.nearest(goal,group);
    if(!a||!b) return [];
    if(this.line(a,b,group)) return [a,b];
    // Keep the search grid anchored at the exact valid start, not a rounded
    // point that could be inside nearby scenery.
    const key=(x,z)=>`${x.toFixed(4)},${z.toFixed(4)}`, origin={...a};
    const open=[{...origin,g:0,f:Math.hypot(origin.x-b.x,origin.z-b.z)}], scores=new Map([[key(origin.x,origin.z),0]]), parents=new Map(), closed=new Set();
    let found=null;
    for(let budget=0;open.length&&budget<18000;budget++) {
      open.sort((p,q)=>q.f-p.f); const p=open.pop(), pk=key(p.x,p.z);
      if(closed.has(pk)) continue; closed.add(pk);
      if(Math.hypot(p.x-b.x,p.z-b.z)<1.6&&this.line(p,b,group)){found=p;break;}
      for(let dx=-1;dx<=1;dx++) for(let dz=-1;dz<=1;dz++) {
        if(!dx&&!dz)continue; const q={x:p.x+dx,z:p.z+dz}, qk=key(q.x,q.z);
        if(closed.has(qk)||!this.line(p,q,group))continue;
        const g=p.g+Math.hypot(dx,dz); if(g>=(scores.get(qk)??Infinity))continue;
        scores.set(qk,g);parents.set(qk,p);open.push({...q,g,f:g+Math.hypot(q.x-b.x,q.z-b.z)});
      }
    }
    if(!found)return [];
    const path=[b]; for(let p=found;p;p=parents.get(key(p.x,p.z))) path.push({x:p.x,z:p.z}); path.push(a);path.reverse();
    const smooth=[a]; let i=0;
    while(i<path.length-1){let j=path.length-1;while(j>i+1&&!this.line(path[i],path[j],group))j--;smooth.push(path[j]);i=j;}
    return smooth;
  }
}
if(typeof module!=="undefined")module.exports={FreeNavigation};
