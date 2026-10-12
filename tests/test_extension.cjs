const vm = require('node:vm');
const fs = require('node:fs');
const assert = require('node:assert/strict');
const calls = [];
const context = {
 console, URL, setTimeout, clearTimeout, setInterval: () => 1, clearInterval: () => {},
 WebSocket: class { constructor() {} },
 chrome: {
   tabs: {
     create: async opts => ({ id: 42, status: 'complete', url: opts.url }),
     get: async id => ({ id, status: 'complete', url: 'https://directory.example/submit' }),
     query: async () => { throw new Error('must not use active tab'); },
   },
   scripting: { executeScript: async opts => {
     calls.push(opts);
     if (opts.func.name === 'inspectPage') return [{ frameId: 0, result: {found:true, confirmed:true}}, {frameId:3, result:{found:true}}];
     return [{frameId:0,result:true}];
   }}
 }
};
vm.createContext(context);
vm.runInContext(fs.readFileSync('extension/background.js','utf8'),context);
(async () => {
 assert.equal((await context.handle({cmd:'click',selector:'button'})).status,'error');
 assert.equal((await context.handle({cmd:'navigate',url:'https://directory.example/submit'})).tab_id,42);
 assert.equal((await context.handle({cmd:'fill',selector:'input',value:'A'})).status,'ok');
 assert.equal((await context.handle({cmd:'click',selector:'button'})).status,'ok');
 const click = calls.find(c=>c.func.name==='clickElement');
 assert.equal(click.target.tabId,42);
 assert.deepEqual(Array.from(click.target.frameIds),[0]);
 assert.equal((await context.handle({cmd:'navigate',url:'file:///secret'})).status,'error');
 console.log('extension task-tab isolation, navigation and single-frame click: passed');
})().catch(e => { console.error(e); process.exitCode=1; });
