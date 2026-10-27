// Main: event handlers and app start
document.addEventListener('click',async ev=>{const t=ev.target.closest('[data-a],[data-d]');if(!t)return;if(t.dataset.d){ev.preventDefault();const[u,p]=t.dataset.d.split(':');$('#u').value=u;$('#pw').value=p;return}
const a=t.dataset.a,id=t.dataset.id,v=s=>$(s).value;if(a=='x'&&ev.target!=t&&t.classList.contains('m'))return;if(t.tagName=='A')ev.preventDefault();const modal=$('#mod').innerHTML!='';let re=0;
try{if(a=='pg'){S.page=t.dataset.k;S.q=S.st='';if(S.page!='fdr')S.inst=''}else if(a=='o')return open_(id);else if(a=='x'){$('#mod').innerHTML=''}else if(a=='rf'){}
else if(a=='fi'){S.inst=id;S.page='fdr'}else if(a=='ci'){S.inst=''}else if(a=='addf')return addF();else if(a=='addi')return instM();else if(a=='reln')return relM();else if(a=='rnm')return renM(id);
else if(a=='vb'){const r=await api(`/fdrs/${id}/verify`,{method:'POST'});toast('Bank verification result: '+r.bank_status.replace('_',' '));re=1}
else if(a=='ap'||a=='rj'){await api(`/fdrs/${id}/decide_release`,{body:{approve:a=='ap'}});toast(a=='ap'?'Release approved':'Release rejected');re=1}
else if(a=='rm'){if(!v('#rk'))return;await api(`/fdrs/${id}/remark`,{body:{text:v('#rk')}});toast('Remark added');re=1}
else if(a=='rq'){await api(`/fdrs/${id}/request_release`,{body:{reason:'Requested via portal'}});toast('Release request submitted');re=1}
else if(a=='ud'){const fi=$('#ud').files[0];if(!fi)return toast('Choose a file first',1);await up(id,fi);toast('Document attached');re=1}
else if(a=='theme'){setTheme(TH=='dark'?'light':'dark');return}
else if(a=='regshow'||a=='regback'){$('#sbox').style.display=a=='regshow'?'none':'';$('#rbox').style.display=a=='regshow'?'block':'none';return}
else if(a=='regsub'){const b={name:v('#gn'),email:v('#ge'),phone:v('#gp'),username:v('#gu'),password:v('#gw')},r=await fetch('/api/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)}),j=await r.json().catch(()=>({})),m=$('#rmsg');m.className=r.ok?'ok':'er';m.textContent=r.ok?'Registration submitted. You can sign in after AICTE approves it.':(j.error||'Registration failed');if(r.ok)['#gn','#ge','#gp','#gu','#gw'].forEach(x=>$(x).value='');return}
else if(a=='rga'||a=='rgr'){await api(`/registrations/${id}/decide`,{body:{approve:a=='rga'}});toast(a=='rga'?'Institution approved':'Registration rejected')}
else if(a=='edf')return editM(id);else if(a=='ei')return editInstM(id,t.dataset.e,t.dataset.p);
else if(a=='efs'){await api(`/fdrs/${id}`,{method:'PUT',body:{bank:v('#eb'),fdr_number:v('#en'),amount:v('#ea'),issue_date:v('#ei2'),maturity_date:v('#em')}});toast('Details updated; bank re-verification required');$('#mod').innerHTML=''}
else if(a=='eis'){await api(`/institutions/${id}`,{method:'PUT',body:{email:v('#ce'),phone:v('#cp')}});toast('Contact updated');$('#mod').innerHTML=''}
else if(a=='ys'){await api(`/institutions/${id}`,{method:'PUT',body:{email:v('#yE'),phone:v('#yP')}});toast('Contact saved')}
else if(a=='ns'){await api('/notify_settings',{body:{desk_email:v('#dE'),desk_phone:v('#dP'),regional_email:v('#rE'),regional_phone:v('#rP'),chairman_email:v('#cE'),chairman_phone:v('#cP')}});toast('Contacts saved')}
else if(a=='nt'){const r=await api('/notify_test',{body:{email:v('#tE'),phone:v('#tP')}});toast('Test result: '+r.results.map(x=>x.channel+' '+x.status+(x.detail?' ('+x.detail+')':'')).join(', '))}
else if(a=='scan'){const r=await api('/scan',{method:'POST'});toast(r.new_alerts+' new alerts generated')}
else if(a=='csv'){const r=await fetch(`/api/reports/${t.dataset.k}?fmt=csv`,{headers:{Authorization:'Bearer '+S.tok}}),u=URL.createObjectURL(await r.blob()),l=document.createElement('a');l.href=u;l.download=t.dataset.k+'_report.csv';l.click();return}
else if(a=='fsub'){const body={bank:v('#nb'),fdr_number:v('#nn'),amount:v('#na'),issue_date:v('#ni'),maturity_date:v('#nm')};if($('#nI'))body.institution_id=v('#nI');const r=await api('/fdrs',{body}),fi=$('#fl').files[0];if(fi)await up(r.id,fi);toast('FDR submitted');$('#mod').innerHTML='';S.page='fdr'}
else if(a=='rns'){await api(`/fdrs/${id}/renew`,{body:{bank:v('#rb'),fdr_number:v('#rn'),amount:v('#ra'),maturity_date:v('#rd')}});toast('Renewal submitted');$('#mod').innerHTML='';S.page='ren'}
else if(a=='rsub'){if(!v('#rf1'))return;await api(`/fdrs/${v('#rf1')}/request_release`,{body:{reason:v('#rr')}});toast('Release request submitted');$('#mod').innerHTML=''}
else if(a=='isub'){await api('/institutions',{body:{name:v('#in'),username:v('#iu'),password:v('#ip'),email:v('#ie'),phone:v('#iph')}});toast('Institution created');$('#mod').innerHTML=''}
if(re&&modal&&S.open)await open_(S.open);await render()}catch(e){if(e)console.error(e)}});
let qt;document.addEventListener('input',ev=>{const t=ev.target,tb=async()=>{const x=(await ftab()).split('|');$('#cnt').textContent=x[0];$('#tb').innerHTML=x.slice(1).join('|')};
if(t.id=='q'){S.q=t.value;clearTimeout(qt);qt=setTimeout(tb,250)}if(t.id=='off'){const o=+t.value;clearTimeout(qt);qt=setTimeout(async()=>{await api('/time',{body:{offset:o}});toast('Demo date moved +'+o+' days; reminders recalculated');render()},300)}});
document.addEventListener('change',async ev=>{const t=ev.target;if(t.id=='st'){S.st=t.value;const x=(await ftab()).split('|');$('#cnt').textContent=x[0];$('#tb').innerHTML=x.slice(1).join('|')}if(t.id=='vf'){S.vf=t.value;render()}
if(t.id=='fl'&&t.files[0])await ocrFill(t.files[0]);});
$('#go').onclick=login;$('#pw').onkeydown=$('#u').onkeydown=e=>{if(e.key=='Enter')login()};$('#lo').onclick=$('#lo2').onclick=out;setTheme(TH);if(S.tok&&S.user)start();
