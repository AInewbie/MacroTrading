let token='';
export async function load(){const r=await fetch('/api/state',{cache:'no-store'});const data=await r.json();if(!r.ok)throw new Error(data.error||'Unable to load workspace');token=data.csrf_token;return data;}
export async function post(path,body={}){const r=await fetch('/api/'+path,{method:'POST',headers:{'Content-Type':'application/json','X-MacroTrading-Token':token},body:JSON.stringify(body)});const data=await r.json();if(!r.ok)throw new Error(data.error||`Request failed (${r.status})`);return data;}
