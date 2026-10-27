// Renders every page and modal for every role against a RUNNING server (http://localhost:8000). Usage: node tests/ui_smoke.js
const fs = require('fs'), vm = require('vm'), path = require('path');
const dir = path.join(__dirname, '..', 'frontend', 'js');
const script = ['core', 'pages', 'modals', 'main'].map(n => fs.readFileSync(path.join(dir, n + '.js'), 'utf8')).join('\n');
const els = {}; global.el = s => els[s] || (els[s] = { value: '', innerHTML: '', textContent: '', style: {}, files: [], classList: { contains: () => false }, dataset: {} });
global.document = { querySelector: global.el, addEventListener() {}, createElement: () => ({}), body: { appendChild() {} }, documentElement: { dataset: {} }, head: { appendChild() {} } };
const store = {}; global.localStorage = { getItem: k => store[k] ?? null, setItem: (k, v) => store[k] = v, clear: () => Object.keys(store).forEach(k => delete store[k]), removeItem: k => delete store[k] };
const _f = fetch; global.fetch = (u, o) => _f(u.startsWith('/') ? 'http://localhost:8000' + u : u, o); global.URL.createObjectURL = () => '';
const tests = `;(async()=>{const fails=[];const T=async(n,f)=>{try{await f()}catch(e){fails.push(n+': '+(e&&e.stack||e))}};
for(const [u,p] of [['official','official123'],['greenfield','greenfield123'],['lakeview','lakeview123'],['admin','admin123']]){
 el('#u').value=u;el('#pw').value=p;await login();await new Promise(r=>setTimeout(r,300));
 for(const pg of PG.filter(x=>!x[6]||isO())){await T(u+'/'+pg[0],async()=>{S.page=pg[0];await render();const h=el('#page').innerHTML;if(!h.includes('<h1>'+pg[3])||h.includes('undefined')||h.includes('NaN'))throw new Error('bad html '+h.slice(0,200))})}
 await T(u+' modals',async()=>{const fid=u=='lakeview'?3:1;await open_(fid);await addF();await renM(fid);await relM();instM()});
 console.log(u,'pages ok:',PG.filter(x=>!x[6]||isO()).length)}
console.log(fails.length?'FAILS:\\n'+fails.join('\\n'):'UI TEST PASSED');process.exit(0)})();`;
vm.runInThisContext(script + tests);
