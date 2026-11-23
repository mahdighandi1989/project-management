/**
 * PM-INS-0033 — «📥 انتقالِ ورود از کرومِ خودِ مالک». Builds the ONE-SITE bookmarklet the owner clicks in their own
 * Chrome while signed in to that site. It reads only what the site's own page can read (localStorage, IndexedDB —
 * Firebase keeps the user there — and non-HttpOnly cookies) and form-POSTs it in a new tab, with a single-use
 * 15-minute ticket bound to that host, to /api/inspector-agent/login/import (the server encrypts it at once).
 * Nothing goes in a URL; nothing is shown on screen. Backend: backend/app/services/manual_login.py.
 */

export function buildImportBookmarklet(token: string, importUrl: string, host: string): string {
  const q = (s: string) => JSON.stringify(s);
  const code = `(async()=>{try{const T=${q(token)},U=${q(importUrl)},H=${q(host)};`
    + `if(location.hostname!==H){alert('این بوک‌مارک فقط برای '+H+' است — اول همان سایت را (واردشده) باز کنید');return}`
    + `const ls={};for(let i=0;i<localStorage.length;i++){const k=localStorage.key(i);ls[k]=localStorage.getItem(k)}`
    + `const idb=[];if(indexedDB.databases){for(const i of await indexedDB.databases()){if(!i.name)continue;`
    + `const db=await new Promise((r,j)=>{const o=indexedDB.open(i.name);o.onsuccess=()=>r(o.result);o.onerror=()=>j(o.error)});`
    + `const stores=[];for(const sn of Array.from(db.objectStoreNames)){const st=db.transaction(sn,'readonly').objectStore(sn);`
    + `const recs=await new Promise(r=>{const a=[];const c=st.openCursor();c.onsuccess=()=>{const cu=c.result;if(!cu||a.length>=5000)return r(a);`
    + `a.push(st.keyPath==null?{key:cu.key,value:cu.value}:{value:cu.value});cu.continue()};c.onerror=()=>r(a)});`
    + `stores.push({name:sn,keyPath:st.keyPath,autoIncrement:st.autoIncrement,indexes:Array.from(st.indexNames).map(n=>{const x=st.index(n);`
    + `return{name:n,keyPath:x.keyPath,multiEntry:x.multiEntry,unique:x.unique}}),records:recs})}`
    + `idb.push({name:i.name,version:db.version,stores});db.close()}}`
    + `const d=JSON.stringify({origin:location.origin,href:location.href,title:document.title,cookie:document.cookie,localStorage:ls,indexedDB:idb});`
    + `const f=document.createElement('form');f.method='POST';f.action=U;f.target='_blank';f.acceptCharset='utf-8';f.style.display='none';`
    + `for(const[n,v]of[['t',T],['d',d]]){const e=document.createElement('textarea');e.name=n;e.value=v;f.appendChild(e)}`
    + `document.body.appendChild(f);f.submit();f.remove()}catch(e){alert('انتقال انجام نشد: '+e)}})()`;
  return 'javascript:' + encodeURIComponent(code);
}
