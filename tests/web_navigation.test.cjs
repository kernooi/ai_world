const test = require('node:test');
const assert = require('node:assert/strict');
const {FreeNavigation} = require('../src/autonomous_ai_world/web/navigation.js');

function validRoute(nav,start,end,group='hub') {
  const path=nav.route(start,end,group);
  assert.ok(path.length>=2,'A reachable destination must have a route');
  assert.deepEqual(path[0],start);
  assert.deepEqual(path.at(-1),end);
  for(let i=1;i<path.length;i++)assert.ok(nav.line(path[i-1],path[i],group),'Every segment must clear scenery');
  return path;
}
test('open floor has a direct route, independent of location graph',()=>{
  const nav=new FreeNavigation();assert.equal(validRoute(nav,{x:-17.2,z:6.3},{x:21.1,z:19.7}).length,2);
});
test('routes around a table without cutting diagonally through corners',()=>{
  const nav=new FreeNavigation();nav.addObstacle(0,0,8,12);
  assert.ok(validRoute(nav,{x:-12,z:0},{x:12,z:0}).length>2);
});
test('fractional starts next to a wall stay outside the wall',()=>{
  const nav=new FreeNavigation();nav.addObstacle(0,0,8,12);
  validRoute(nav,{x:-4.66,z:.12},{x:12,z:.37});
});
test('accessor-backed Babylon-style vectors are normalized into plain coordinates',()=>{
  const nav=new FreeNavigation();nav.addObstacle(0,0,12,12);
  class Vector {constructor(x,z){this._x=x;this._z=z;}get x(){return this._x;}get z(){return this._z;}}
  const path=nav.route(new Vector(-12,0),new Vector(12,0));
  assert.ok(path.length>2);assert.deepEqual(path[0],{x:-12,z:0});
  for(let i=1;i<path.length;i++)assert.ok(nav.line(path[i-1],path[i],'hub'));
});
test('solid barrier is unreachable, never a teleport route',()=>{
  const nav=new FreeNavigation();nav.addObstacle(0,30,120,2);
  assert.deepEqual(nav.route({x:0,z:0},{x:0,z:45}),[]);
});
test('pocket worlds navigate connected islands but cannot walk into another world',()=>{
  const nav=new FreeNavigation();nav.addArea(120,0,14,'a');nav.addArea(140,0,14,'a');nav.addArea(180,0,14,'b');
  validRoute(nav,{x:120,z:0},{x:140,z:0},'a');
  assert.equal(nav.clear(180,0,'a'),false);
  assert.deepEqual(nav.route({x:120,z:0},{x:180,z:0},'a'),[]);
});
test('occupied spawn positions resolve to clear floor; outside bounds rejected',()=>{
  const nav=new FreeNavigation();nav.addObstacle(0,0,4,4);
  const point=nav.nearest({x:0,z:0},'hub');assert.ok(nav.clear(point.x,point.z));
  assert.equal(nav.clear(56,0),false);assert.equal(nav.clear(0,-34),false);
});
