/**
 * PM-INS-0033 — «📥 انتقالِ ورود از کرومِ خودِ مالک». Builds the ONE-SITE bookmarklet the owner clicks in their own
 * Chrome while signed in to that site. It reads only what the site's own page can read (localStorage, IndexedDB —
 * Firebase keeps the user there — and non-HttpOnly cookies).
 *
 * PM-INS-0036 (round 2): the project's own CSP (`form-action 'self'`, `connect-src 'self'` — Detective-1 has both)
 * blocks a form POST or fetch from that page to our server; the owner got «Method Not Allowed» in the new tab. So the
 * bookmarklet now OPENS our receiver page (GET /api/inspector-agent/login/import — CSP does not restrict navigation)
 * and hands the dump over with postMessage, addressed to our origin only; the receiver POSTs it same-origin with the
 * single-use 15-minute ticket bound to that host (the server encrypts it at once). window.open is called FIRST, while
 * the click's user activation is still live. Nothing goes in a URL. Backend: backend/app/services/manual_login.py.
 */

export function buildImportBookmarklet(token: string, importUrl: string, host: string): string {
  const q = (s: string) => JSON.stringify(s);
  const code = `(()=>{const T=${q(token)},U=${q(importUrl)},H=${q(host)};`
    + `if(location.hostname!==H){alert('این بوک‌مارک فقط برای '+H+' است — اول همان سایت را (واردشده) باز کنید و در همان زبانه بزنید');return}`
    + `const O=new URL(U).origin,w=window.open(U,'_blank');`
    + `if(!w){alert('کروم پنجرهٔ تازه را مسدود کرد. در سمتِ راستِ نوارِ نشانی روی نشانِ «Pop-up blocked» بزنید، «Always allow» را انتخاب کنید و دوباره روی بوک‌مارک کلیک کنید.');return}`
    + `let D=null,R=false,S=false;const go=()=>{if(D&&R&&!S){S=true;w.postMessage({pmImport:'data',t:T,d:D},O)}};`
    + `addEventListener('message',e=>{if(e.source===w&&e.origin===O&&e.data&&e.data.pmImport==='ready'){R=true;go()}});`
    + `(async()=>{try{`
    + `const ls={};for(let i=0;i<localStorage.length;i++){const k=localStorage.key(i);ls[k]=localStorage.getItem(k)}`
    + `const idb=[];if(indexedDB.databases){for(const i of await indexedDB.databases()){if(!i.name)continue;`
    + `const db=await new Promise((r,j)=>{const o=indexedDB.open(i.name);o.onsuccess=()=>r(o.result);o.onerror=()=>j(o.error)});`
    + `const stores=[];for(const sn of Array.from(db.objectStoreNames)){const st=db.transaction(sn,'readonly').objectStore(sn);`
    + `const recs=await new Promise(r=>{const a=[];const c=st.openCursor();c.onsuccess=()=>{const cu=c.result;if(!cu||a.length>=5000)return r(a);`
    + `a.push(st.keyPath==null?{key:cu.key,value:cu.value}:{value:cu.value});cu.continue()};c.onerror=()=>r(a)});`
    + `stores.push({name:sn,keyPath:st.keyPath,autoIncrement:st.autoIncrement,indexes:Array.from(st.indexNames).map(n=>{const x=st.index(n);`
    + `return{name:n,keyPath:x.keyPath,multiEntry:x.multiEntry,unique:x.unique}}),records:recs})}`
    + `idb.push({name:i.name,version:db.version,stores});db.close()}}`
    + `D=JSON.stringify({origin:location.origin,href:location.href,title:document.title,cookie:document.cookie,localStorage:ls,indexedDB:idb});go()`
    + `}catch(e){alert('انتقال انجام نشد: '+e)}})()})()`;
  return 'javascript:' + encodeURIComponent(code);
}
