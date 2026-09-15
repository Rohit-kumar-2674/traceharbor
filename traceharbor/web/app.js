const $ = (selector, root = document) => root.querySelector(selector);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const paths = {
  grid:'M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z',
  folder:'M3 7V5a1 1 0 0 1 1-1h5l2 3h9a1 1 0 0 1 1 1v11a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V7z',
  scan:'M8 3H3v5 M16 3h5v5 M21 16v5h-5 M8 21H3v-5 M3 12h18',
  link:'M10 13a4 4 0 0 0 6 0l4-4a4 4 0 0 0-6-6l-2 2 M14 11a4 4 0 0 0-6 0l-4 4a4 4 0 0 0 6 6l2-2',
  search:'M21 21l-5-5 M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0',
  book:'M12 5v16 M12 5C9 2 5 2 2 4v15c4-2 7-1 10 2 3-3 6-4 10-2V4c-4-2-7-2-10 1',
  shield:'M12 2l8 4v7c0 4-8 9-8 9s-8-5-8-9V6z M8 12l3 3 5-6',
  arrow:'M5 12h14 M14 7l5 5-5 5',
  plus:'M12 5v14 M5 12h14',
  file:'M5 2h9l5 5v15H5z M14 2v6h5 M8 13h8 M8 17h6',
  hash:'M9 3L7 21 M17 3l-2 18 M3 9h18 M2 15h18',
  note:'M5 3h14v18H5z M8 7h8 M8 11h8 M8 15h5',
  clock:'M12 8v5l3 2 M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0',
  upload:'M12 16V3 M7 8l5-5 5 5 M3 15v6h18v-6',
  down:'M12 3v13 M7 11l5 5 5-5 M3 17v4h18v-4',
  lock:'M7 11V7a5 5 0 0 1 10 0v4 M4 11h16v11H4z M12 15v3',
  menu:'M3 6h18 M3 12h18 M3 18h18',
  compare:'M8 3v18 M16 3v18 M3 7h10 M11 17h10 M3 7l3-3 M3 7l3 3 M21 17l-3-3 M21 17l-3 3',
  check:'M5 12l4 4L20 5',
  archive:'M3 3h18v5H3z M5 8v13h14V8 M9 12h6'
};
const icon = name => `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="${paths[name] || paths.file}"/></svg>`;
const kindIcon = kind => ({file:'file',source:'link',finding:'note',event:'clock'}[kind] || 'file');
const date = value => new Date(value).toLocaleString([], {dateStyle:'medium',timeStyle:'short'});
const bytes = value => value >= 1048576 ? `${(value/1048576).toFixed(2)} MiB` : `${(value/1024).toFixed(1)} KiB`;
const button = (label, action, type='secondary', extra='') => `<button class="btn ${type}" data-action="${action}" ${extra}>${label}</button>`;
const badge = value => `<span class="status-pill ${esc(value)}">${esc(value)}</span>`;
const empty = (title, message, action='') => `<div class="empty"><div class="square-icon">${icon('folder')}</div><h3>${esc(title)}</h3><p>${esc(message)}</p>${action}</div>`;
const state = {route:'overview',cases:[],openTabs:[],activeCase:null,caseView:'all',query:'',filter:'active',status:null,lab:null,preview:null,verification:null};
const params = new URLSearchParams(location.hash.slice(1));
let token = params.get('token') || sessionStorage.getItem('traceharbor-session') || '';
if (params.has('token')) history.replaceState(null, '', location.pathname);
if (token) sessionStorage.setItem('traceharbor-session', token);

async function api(path, options={}) {
  const headers = {'Authorization':`Bearer ${token}`, ...(options.body ? {'Content-Type':'application/json'} : {})};
  const response = await fetch(`/api${path}`, {...options,headers:{...headers,...options.headers}});
  if (!response.ok) {
    let message = `Request failed (${response.status}).`;
    try { const data = await response.json(); message = typeof data.detail === 'string' ? data.detail : message; } catch {}
    if (response.status === 401) { token=''; sessionStorage.removeItem('traceharbor-session'); locked(); }
    throw new Error(message);
  }
  return options.raw ? response : response.json();
}
const post = (path, body) => api(path, {method:'POST',body:JSON.stringify(body)});
let toastTimer;
function toast(message) { $('#toast').textContent=message; $('#toast').classList.add('show'); clearTimeout(toastTimer); toastTimer=setTimeout(()=>$('#toast').classList.remove('show'),5000); }
async function refreshCases() { state.cases=(await api('/cases')).cases; }
function selectedCaseOptions(optional=true) { return `${optional?'<option value="">Analyse only · do not save</option>':''}${state.cases.filter(c=>c.status==='active').map(c=>`<option value="${c.id}" ${state.activeCase?.id===c.id?'selected':''}>${esc(c.title)}</option>`).join('')}`; }

function locked(message='') {
  $('#dialog').close();
  $('#app').innerHTML=`<main class="login"><div class="login-card"><img src="/mark.svg" alt="TraceHarbor"><div class="eyebrow">LOCAL INVESTIGATION WORKSPACE</div><h1>Your evidence.<br>Your workspace.</h1><p>Open the private session link printed by <code>traceharbor serve</code>, or paste its access key below.</p><form data-form="unlock" class="form-grid"><div class="field"><label for="session-key">Session key or private session link</label><input id="session-key" name="key" type="password" autocomplete="off" required placeholder="Paste from your terminal"></div><p class="error" id="unlock-error">${esc(message)}</p><button class="btn primary" type="submit">Unlock workspace ${icon('arrow')}</button></form><p class="tool-note">Local single-user access. Keep the key private; it changes when the server restarts.</p></div></main>`;
}

async function start() {
  if (!token) return locked();
  try { state.status=await api('/status'); await refreshCases(); shell(); }
  catch(error) { locked(error.message); }
}

function shell() {
  const nav=(route,label,name)=>`<button class="nav-item ${state.route===route?'active':''}" data-route="${route}">${icon(name)}${label}${route==='cases'?`<span class="count">${state.cases.length}</span>`:''}</button>`;
  $('#app').innerHTML=`<div class="shell"><aside class="sidebar" aria-label="Main navigation"><div class="brand"><img src="/mark.svg" alt=""><div><strong>TraceHarbor</strong><span>EVIDENCE BEFORE INFERENCE</span></div></div><div class="nav-group">WORKSPACE</div>${nav('overview','Overview','grid')}${nav('cases','Case library','folder')}<div class="nav-group">INVESTIGATION TOOLS</div>${nav('lab','Evidence lab','scan')}${nav('links','Link inspector','link')}${nav('leads','Public leads','search')}<div class="nav-group">RESOURCES</div>${nav('guide','Field guide','book')}<div class="sidebar-foot"><div class="session"><span class="dot"></span><div><strong>Local session</strong><small>Single-user workspace</small></div><button class="lock-button" data-action="lock" aria-label="Lock workspace">${icon('lock')}</button></div><p class="sidebar-note">Originals stay on this device.<br>No automatic external requests.</p></div></aside><div class="workspace"><header class="topbar"><button class="mobile-menu" data-action="menu" aria-label="Toggle navigation">${icon('menu')}</button><div class="breadcrumb">Workspace <b>/ <span id="crumb">Overview</span></b></div><div class="top-tools"><label class="search-box">${icon('search')}<input id="search" placeholder="Search cases or records…" aria-label="Search cases or records" value="${esc(state.query)}"></label><span class="top-badge"><span class="dot"></span>LOCAL-FIRST</span><span class="avatar" title="Local analyst label, not an authenticated identity">LA</span></div></header><div class="tabs" id="tabs" aria-label="Open workspaces"></div><main class="content" id="content"></main></div></div>`;
  renderTabs(); content();
}

function renderTabs() {
  $('#tabs').innerHTML=`<button class="tab ${state.route==='overview'?'selected':''}" data-route="overview">${icon('grid')}Overview</button>${state.openTabs.map(c=>`<div class="tab ${state.route==='case'&&state.activeCase?.id===c.id?'selected':''}"><button class="link-button" data-action="open-case" data-id="${c.id}">${icon('folder')}${esc(c.title.slice(0,27))}</button><button class="tab-close" data-action="close-tab" data-id="${c.id}" aria-label="Close ${esc(c.title)} tab">×</button></div>`).join('')}${!['overview','case','cases'].includes(state.route)?`<span class="tab selected">${icon('scan')}${esc({lab:'Evidence lab',links:'Link inspector',leads:'Public leads',guide:'Field guide'}[state.route])}</span>`:''}`;
}

function footer() { return `<footer class="footer-line"><span>TRACEHARBOR / RESEARCH WORKSPACE / v${esc(state.status.version)}</span><span>Private by default. Human judgment required.</span></footer>`; }
function content() {
  const routes={overview:overview,cases:caseLibrary,case:casePage,lab:labPage,links:linksPage,leads:leadsPage,guide:guidePage};
  $('#crumb').textContent={overview:'Overview',cases:'Case library',case:'Case workspace',lab:'Evidence lab',links:'Link inspector',leads:'Public leads',guide:'Field guide'}[state.route];
  $('#content').innerHTML=(routes[state.route] || overview)()+footer();
}

function pageHeading(eyebrow,title,description,actions='') { return `<div class="page-heading"><div><div class="eyebrow">${eyebrow}</div><h1>${title}</h1><p>${description}</p></div><div class="actions">${actions}</div></div>`; }
function filteredCases() { const q=state.query.toLowerCase(); return state.cases.filter(c=>`${c.title} ${c.purpose} ${c.analyst} ${c.id}`.toLowerCase().includes(q)); }
function caseRows(cases) { return cases.map(c=>`<div class="case-row"><div class="square-icon">${icon('folder')}</div><div><button class="case-title" data-action="open-case" data-id="${c.id}">${esc(c.title)}</button><div class="case-sub">${c.counts.file+c.counts.source} evidence records · ${esc(date(c.last_activity))}</div></div>${badge(c.status)}</div>`).join(''); }
function overview() {
  const totals=state.cases.reduce((a,c)=>{for(const k of Object.keys(a)) a[k]+=c.counts[k]; return a;},{file:0,source:0,finding:0,event:0});
  const stat=(label,value,sub,name)=>`<div class="stat"><div class="stat-top">${label}${icon(name)}</div><strong>${value.toString().padStart(2,'0')}</strong><small>${sub}</small></div>`;
  const tool=(route,name,title,desc)=>`<button class="tool-card" data-route="${route}"><div class="square-icon">${icon(name)}</div><div><h3>${title}</h3><p>${desc}</p></div>${icon('arrow')}</button>`;
  const cases=filteredCases().slice(0,5);
  return pageHeading('YOUR INVESTIGATION DESK','Workspace overview','A clear view of your cases, evidence and next steps.',button(icon('plus')+' New case','new-case','primary'))+
    `<section class="hero"><div><div class="eyebrow">COLLECT CAREFULLY. CONNECT RESPONSIBLY.</div><h1>Evidence, in context.</h1><p>A considered workspace for public-source research. Preserve the original, document the source, and keep your findings grounded.</p></div><div class="hero-art" aria-hidden="true"><div class="rings"><img src="/mark.svg" alt=""></div><span class="hero-coordinate mono">LOCAL / TRACEABLE / HUMAN-LED</span></div></section><section class="stats" aria-label="Workspace statistics">${stat('Active cases',state.cases.filter(c=>c.status==='active').length,'Ready for investigation','folder')}${stat('Preserved files',totals.file,'Hashed at collection','hash')}${stat('Source references',totals.source,'Manually recorded URLs','link')}${stat('Findings',totals.finding,'Analyst-written observations','note')}</section><div class="two-col"><section><div class="section-heading"><h2>Recent cases</h2><button class="link-button" data-route="cases">View case library ${icon('arrow')}</button></div><div class="panel">${cases.length?caseRows(cases):empty(state.query?'No matching cases':'Your first case starts here',state.query?'Try a different search.':'Give your research a purpose, then build an evidence trail.',button(icon('plus')+' Create a case','new-case','primary'))}</div><div class="mini-note">${icon('shield')}<p><strong>Keep evidence and inference separate.</strong><br>Matching usernames, editable metadata and OCR text are leads—not proof. Corroborate before drawing conclusions.</p></div></section><section><div class="section-heading"><h2>Tools at hand</h2><span class="inline-chip">OFFLINE ANALYSIS</span></div><div class="panel">${tool('lab','scan','Examine a file','Metadata, fingerprints and local OCR')}${tool('links','link','Inspect a source URL','Structure and privacy considerations')}${tool('leads','search','Explore public leads','Candidate URLs for manual review')}</div><button class="link-button" data-action="training">${icon('book')} Load a labelled training case ${icon('arrow')}</button></section></div>`;
}

function caseLibrary() {
  const cases=filteredCases().filter(c=>state.filter==='all'||c.status===state.filter);
  return pageHeading('ORGANISED RESEARCH','Case library','Keep each purpose, source and finding in its own context.',button(icon('plus')+' New case','new-case','primary'))+
    `<div class="toolbar"><div class="segmented">${['active','archived','all'].map(f=>`<button class="${state.filter===f?'active':''}" data-action="filter" data-value="${f}">${f[0].toUpperCase()+f.slice(1)}</button>`).join('')}</div><small>${cases.length} ${cases.length===1?'case':'cases'}</small></div>${cases.length?`<div class="case-grid">${cases.map(c=>`<article class="case-card"><div class="case-card-top"><div class="square-icon">${icon('folder')}</div>${badge(c.status)}</div><h3>${esc(c.title)}</h3><p>${esc(c.purpose.slice(0,200))}</p><div class="case-sub mono">${c.id.slice(0,8).toUpperCase()} · ${c.counts.file+c.counts.source} evidence · ${c.counts.finding} findings</div><div class="actions"><small>${esc(date(c.last_activity))}</small>${button('Open case '+icon('arrow'),'open-case','small',`data-id="${c.id}"`)}</div></article>`).join('')}</div>`:empty('No cases in this view','Create a case or change the status filter.',button('New case','new-case','primary'))}`;
}

function record(entry) {
  const a=entry.analysis;
  return `<article class="record" id="record-${entry.id}"><div class="record-head"><div class="square-icon">${icon(kindIcon(entry.kind))}</div><div class="record-main"><h3>${esc(entry.title)}</h3><small>${esc(entry.kind.toUpperCase())} · ${esc(date(entry.created_at))} · <span class="mono">${entry.id.slice(0,8)}</span></small></div>${badge(entry.assessment)}</div>${entry.event_at?`<p><strong>Reported event:</strong> ${esc(date(entry.event_at))} <small>(${esc(entry.event_at)})</small></p>`:''}${entry.body?`<p>${esc(entry.body)}</p>`:''}${entry.source_url?`<a class="source-link" href="${esc(entry.source_url)}" target="_blank" rel="noopener noreferrer">${esc(entry.source_url)} ↗</a>`:''}${entry.references?.length?`<div class="actions">${entry.references.map(ref=>`<button class="link-button" data-action="reference" data-id="${ref}">${icon('link')} Evidence ${ref.slice(0,8)}</button>`).join('')}</div>`:''}${a?`<div class="hash-line"><b>SHA-256 / ORIGINAL FILE</b><code>${esc(a.sha256)}</code></div><div class="actions"><span class="inline-chip">${bytes(a.size_bytes)}</span>${a.image?`<span class="inline-chip">${esc(a.image.format)} · ${a.image.width} × ${a.image.height}</span>`:''}${button('Copy hash','copy-hash','small',`data-hash="${esc(a.sha256)}"`)}${button(icon('down')+' Original','original','small',`data-id="${entry.id}"`)}</div><details><summary>Analysis, metadata &amp; OCR</summary><pre>${esc(JSON.stringify(a,null,2))}</pre></details>`:''}</article>`;
}

function casePage() {
  const c=state.activeCase;
  if(!c) return empty('Select a case','Open one from the case library.');
  const entries=c.entries.filter(e=>JSON.stringify(e).toLowerCase().includes(state.query.toLowerCase()));
  const map={files:'file',sources:'source',findings:'finding',timeline:'event'};
  const list=state.caseView==='all'?entries:entries.filter(e=>e.kind===map[state.caseView]);
  if(state.caseView==='timeline') list.sort((a,b)=>a.event_at.localeCompare(b.event_at));
  let body;
  if(state.caseView==='audit') body=`<div class="notice">This hash-linked log detects local inconsistencies when checked. It is not independently timestamped or protected from an administrator rewriting the entire database. Analyst labels do not authenticate a person.</div>${button(icon('shield')+' Run integrity check','verify','primary')}<div id="verify-result">${verificationHtml()}</div><div class="panel">${c.audit.map(a=>`<div class="audit-row"><span class="mono">${String(a.seq).padStart(2,'0')}</span><div><strong>${esc(a.action)}</strong><small> · ${esc(date(a.at))}</small><code>record ${esc(a.record_id)}<br>hash ${esc(a.hash)}<br>previous ${esc(a.previous)}</code></div></div>`).join('')}</div>`;
  else if(state.caseView==='compare') body=comparePage(c.entries.filter(e=>e.kind==='file'));
  else body=`<div class="panel ${state.caseView==='timeline'?'timeline':''}">${list.length?list.map(record).join(''):empty('Nothing recorded here yet','Add a file, a source reference, a finding or a timestamped event. Each addition is logged.')}</div>`;
  return pageHeading(`CASE / ${c.id.slice(0,8).toUpperCase()}`,esc(c.title),`${esc(c.analyst)} · Created ${esc(date(c.created_at))}`,button(icon('archive')+(c.status==='active'?' Archive':' Reopen'),'archive')+button(icon('down')+' Export','export','primary'))+
    `<div class="case-metadata"><p>${esc(c.purpose)}</p>${badge(c.status)} <span class="inline-chip">${c.entries.length} records</span> <span class="inline-chip">${c.audit.length} audit entries</span></div>${c.status==='archived'?'<div class="notice">This case is archived. Reopen it to add records. Existing evidence remains available.</div>':''}<div class="toolbar"><div class="segmented">${['all','files','sources','findings','timeline','audit','compare'].map(v=>`<button class="${state.caseView===v?'active':''}" data-action="case-view" data-value="${v}">${v[0].toUpperCase()+v.slice(1)}</button>`).join('')}</div>${c.status==='active'?`<div class="actions">${button(icon('plus')+' Add record','add-record','primary')}</div>`:''}</div>${body}`;
}

function verificationHtml() {
  const v=state.verification;
  return v?`<div class="verify-result ${v.valid?'':'failed'}"><strong>${v.valid?'No inconsistencies detected':'Integrity check failed'}</strong><br>${v.records} records · ${v.files} originals · ${v.audit_entries} audit entries<br><code>Head: ${esc(v.head_hash)}</code>${v.issues.map(i=>`<p>${esc(i)}</p>`).join('')}<small>${esc(v.limitation)}</small></div>`:'';
}

function comparePage(files) {
  if(files.length<2) return empty('Two file records are needed','Add two files to this case to compare original bytes and image dHash.');
  const options=files.map(e=>`<option value="${e.id}">${esc(e.title)} · ${e.id.slice(0,8)}</option>`).join('');
  return `<div class="panel"><div class="panel-head"><h2>Compare evidence files</h2>${icon('compare')}</div><div class="panel-body"><form data-form="compare" class="form-grid"><div class="form-grid two"><div class="field"><label for="left">First file</label><select name="left" id="left">${options}</select></div><div class="field"><label for="right">Second file</label><select name="right" id="right">${options}</select></div></div><p class="tool-note">An exact SHA-256 match means the recorded byte content matches. Image dHash is an appearance heuristic, never a facial or identity match.</p><p class="error"></p><button class="btn primary">Compare originals</button></form><div id="compare-result"></div></div></div>`;
}

function analysisHtml(a) {
  return `<div class="result-header"><div class="square-icon">${icon('check')}</div><div><h3>Analysis complete</h3><small class="file-label">${esc(a.filename)} · ${bytes(a.size_bytes)}</small></div></div>${state.preview&&a.image?`<img class="file-preview" src="${esc(state.preview)}" alt="Uploaded evidence preview">`:''}<div class="hash-line"><b>SHA-256</b><code>${esc(a.sha256)}</code></div><div class="actions">${button('Copy SHA-256','copy-hash','small',`data-hash="${a.sha256}"`)}</div>${a.image?`<dl class="kv"><dt>Image</dt><dd>${esc(a.image.format)} / ${a.image.width} × ${a.image.height} / ${esc(a.image.mode)}</dd><dt>dHash (64-bit)</dt><dd class="mono">${esc(a.image.dhash)}</dd><dt>Frames</dt><dd>${a.image.frames}</dd></dl><details><summary class="tool-note">EXIF metadata</summary><pre class="ocr-output">${esc(JSON.stringify(a.image.exif,null,2))}</pre></details>`:''}<h3>OCR transcription</h3><p class="tool-note">Status: ${esc(a.ocr.status)}. ${esc(a.ocr.notice || 'Local extraction when requested.')}</p>${a.ocr.text?`<pre class="ocr-output">${esc(a.ocr.text)}</pre>`:''}${a.warnings.map(w=>`<p class="tool-note">${esc(w)}</p>`).join('')}`;
}

function labPage() {
  return pageHeading('FILE ANALYSIS','Evidence lab','Examine a file locally. Preserve its original bytes when saving to a case.')+
    `<div class="two-col"><div><div class="panel"><div class="panel-head"><h2>Examine an original</h2><small>MAX 10 MiB</small></div><div class="panel-body"><form data-form="analyze" class="form-grid"><div class="upload-zone">${icon('upload')}<h3>A closer look starts here.</h3><p>Any file for hashes. Supported images for metadata and OCR.</p><input id="evidence-file" name="file" type="file" required aria-label="Choose evidence file"></div><div class="field"><label for="save-case">Save analysis and original in a case</label><select name="case_id" id="save-case">${selectedCaseOptions()}</select><small>Select “Analyse only” to avoid retaining the file or its results.</small></div><div class="field"><label for="file-source">Source URL (optional)</label><input id="file-source" name="source_url" type="url" maxlength="2048" placeholder="https://example.org/source"><small>Use only a public source. Review URLs for access tokens before saving.</small></div><div class="field"><label for="file-notes">Collection notes (optional)</label><textarea id="file-notes" name="body" maxlength="12000" placeholder="Where did the file come from? How was it obtained?"></textarea></div><label class="check"><input type="checkbox" name="ocr" ${state.status.capabilities.ocr?'':'disabled'}>Extract text with local Tesseract OCR ${state.status.capabilities.ocr?'':'(not installed)'}</label><p class="error"></p><button class="btn primary" type="submit">${icon('scan')} Run analysis</button></form></div></div><div class="mini-note">${icon('lock')}<p>No upload to a third-party service. OCR may contain errors. Originals and metadata are not encrypted at rest.</p></div></div><div class="panel"><div class="panel-head"><h2>Analysis output</h2><small>LOCAL PROCESSING</small></div><div class="panel-body" id="analysis-result">${state.lab?analysisHtml(state.lab):empty('Ready when you are','Select a file to inspect its byte fingerprints, available image metadata and OCR text.')}</div></div></div>`;
}

function linksPage() {
  return pageHeading('PUBLIC-SOURCE REVIEW','Link inspector','Inspect a URL’s structure without contacting its server.')+
    `<div class="panel"><div class="panel-body"><form class="form-grid" data-form="inspect"><div class="field"><label for="inspect-url">Public HTTP(S) URL</label><input id="inspect-url" type="url" name="url" placeholder="https://example.org/article" required maxlength="2048"></div><p class="error"></p><button class="btn primary">${icon('link')} Inspect URL</button></form></div></div><div id="url-result"></div><div class="mini-note">${icon('shield')}<p>This is a syntax and privacy check, not a reputation scan. The tool does not fetch the page, identify an owner, verify a claim or assess a person.</p></div>`;
}

function leadsPage() {
  return pageHeading('MANUAL PUBLIC-SOURCE RESEARCH','Public leads','Prepare a small set of public profile links for human review.')+
    `<div class="notice">A matching username does not establish identity or common ownership. These links are unverified candidates. No private accounts are accessed, and no existence checks run automatically.</div><div class="panel"><div class="panel-body"><form class="form-grid" data-form="leads"><div class="field"><label for="username">Public username</label><input id="username" name="username" placeholder="A username you are authorised to research" pattern="[A-Za-z0-9_-]{1,39}" maxlength="39" required><small>Up to 39 letters, digits, hyphens or underscores. No names, phone numbers or email searches.</small></div><p class="error"></p><button class="btn primary">${icon('search')} Prepare public links</button></form></div></div><div id="lead-result"></div>`;
}

function guidePage() {
  return pageHeading('A PRACTICAL FIELD GUIDE','Good research leaves a trail.','Make every observation understandable, reviewable and proportionate.')+
    `<article class="guide"><div class="notice"><strong>Research release, not operational certification.</strong> TraceHarbor is not independently validated for police evidence handling or court use. Do not use this release for live sensitive casework without security, privacy and forensic review.</div><div class="panel"><div class="panel-body"><h2>01 / Start with a defined purpose</h2><p>Create a case and record why you are collecting information. Stay within your authority. Minimise personal data, use training material first, and document who can access your device.</p><h2>02 / Preserve before interpreting</h2><p>Use Evidence lab to calculate original-byte hashes, inspect image metadata and optionally transcribe text. Saving to a case retains an unchanged copy. EXIF is editable; OCR is fallible; timestamps record local system time, not a trusted time source.</p><h2>03 / Separate observation from assessment</h2><p>Record public URLs as source references. Write findings in your own words and attach supporting evidence IDs. “Corroborated” is your assessment, not a TraceHarbor verdict. Record contradictory evidence too; username matches never prove identity.</p><h2>04 / Make events explicit</h2><p>Add timeline events with a reported event time and supporting references. Event times are distinct from when a record was saved. Enter them in your browser’s local timezone; the workspace stores UTC.</p><h2>05 / Verify and review before sharing</h2><p>Run the case integrity check. Export a portable ZIP with HTML, JSON and checksums; originals are optional. Exports include raw notes and metadata and are not automatically redacted. Review them for location data and other sensitive content.</p><h2>What local-first does—and does not—mean</h2><p>Analysis makes no external requests. Opening a public lead or source link contacts that website in your browser. Data is stored on disk without application-level encryption. Use full-disk encryption and secure backups; locking this browser is not an operating-system security boundary.</p><h2>Terminal workflow</h2><pre>python -m traceharbor doctor
python -m traceharbor analyze image.jpg --ocr
python -m traceharbor cases
python -m traceharbor verify CASE_ID
python -m traceharbor export CASE_ID --output report.zip</pre><h2>About this release</h2><p>FastAPI backend, SQLite records, optional Pillow and Tesseract, and a dependency-free browser interface. Maximum file size: 10 MiB; decoded images: 20 megapixels. Up to 500 cases and 500 records per case. No facial identification, surveillance, bypassing access controls or risk scores for people.</p></div></div><p class="tagline">Evidence before inference.</p></article>`;
}

function modal(title,body,form,submit='Save record') {
  const d=$('#dialog');
  d.innerHTML=`<form data-form="${form}"><header class="dialog-head"><h2>${title}</h2><button class="btn ghost small" type="button" data-action="close-modal" aria-label="Close dialog">×</button></header><div class="dialog-body"><div class="form-grid">${body}</div><p class="error"></p></div><footer class="dialog-foot"><button type="button" class="btn" data-action="close-modal">Cancel</button><button class="btn primary" type="submit">${submit}</button></footer></form>`;
  if(!d.open) d.showModal();
}
function newCaseModal() {
  modal('Open a new case',`<div class="field"><label for="case-title">Case title</label><input id="case-title" name="title" maxlength="120" required placeholder="A clear, descriptive research title"></div><div class="field"><label for="case-purpose">Purpose and scope</label><textarea id="case-purpose" name="purpose" maxlength="4000" required placeholder="What question are you investigating, and what is your authority or consent to collect this information?"></textarea></div><div class="field"><label for="analyst">Analyst label</label><input id="analyst" name="analyst" maxlength="120" value="Local analyst" required><small>A label for your records, not a verified identity.</small></div>`,'new-case','Create case');
}
function addRecordModal() {
  modal('Add to the evidence trail',`<button class="tool-card" type="button" data-action="add-file">${icon('file')} Analyse and preserve a file ${icon('arrow')}</button><button class="tool-card" type="button" data-action="entry-form" data-kind="source">${icon('link')} Record a public source ${icon('arrow')}</button><button class="tool-card" type="button" data-action="entry-form" data-kind="finding">${icon('note')} Write an analyst finding ${icon('arrow')}</button><button class="tool-card" type="button" data-action="entry-form" data-kind="event">${icon('clock')} Add a timeline event ${icon('arrow')}</button>`,'choose-record','Done');
}
function entryModal(kind) {
  const c=state.activeCase;
  modal({source:'Record a source reference',finding:'Write an analyst finding',event:'Add a timeline event'}[kind],`<input type="hidden" name="kind" value="${kind}"><div class="field"><label for="entry-title">Title</label><input id="entry-title" name="title" maxlength="200" required></div>${kind==='source'?`<div class="field"><label for="source-url">Public source URL</label><input id="source-url" name="source_url" type="url" maxlength="2048" required placeholder="https://"><small>A reference only; the page is not fetched or preserved. Save a lawful local copy separately if needed.</small></div>`:''}${kind==='event'?'<div class="field"><label for="event-at">Reported event time (your local timezone)</label><input name="event_at" id="event-at" type="datetime-local" required><small>Stored in UTC; not the collection timestamp.</small></div>':''}<div class="field"><label for="entry-body">${kind==='source'?'Source context and limitations':'Observation and reasoning'}</label><textarea id="entry-body" name="body" maxlength="12000" ${kind==='source'?'':'required'}></textarea></div>${kind!=='source'?`<div class="field"><label for="assessment">Analyst assessment</label><select name="assessment" id="assessment"><option value="unverified">Unverified</option><option value="corroborated">Corroborated — supporting reference required</option><option value="disputed">Disputed</option></select></div><div class="field"><label for="references">Supporting evidence references</label><select id="references" name="references" multiple>${c.entries.map(e=>`<option value="${e.id}">${esc(e.title)} · ${e.id.slice(0,8)}</option>`).join('')}</select><small>Choose relevant records. Existing records are immutable; add a new finding for corrections.</small></div>`:''}`,'entry');
}

async function openCase(id) {
  state.activeCase=await api(`/cases/${id}`); state.route='case'; state.query=''; state.verification=null;
  if(!state.openTabs.some(c=>c.id===id)) state.openTabs.push({id,title:state.activeCase.title});
  shell();
}
async function navigate(route) { state.route=route; state.query=''; shell(); }
async function download(path,name) {
  const response=await api(path,{raw:true}); const url=URL.createObjectURL(await response.blob());
  const a=document.createElement('a'); a.href=url; a.download=name; a.click(); setTimeout(()=>URL.revokeObjectURL(url),30000);
}
function filePayload(file) {
  if(file.size>10*1024*1024) throw new Error('Choose a file no larger than 10 MiB.');
  if(!file.size) throw new Error('Empty files are not supported.');
  return new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result.split(',')[1]);reader.onerror=()=>reject(new Error('Could not read the selected file.'));reader.readAsDataURL(file);});
}

document.addEventListener('input', event=>{
  if(event.target.id==='search'){state.query=event.target.value;if(['case','cases','overview'].includes(state.route)) content();}
});

document.addEventListener('click',async event=>{
  const route=event.target.closest('[data-route]');
  if(route) return navigate(route.dataset.route);
  const target=event.target.closest('[data-action]'); if(!target) return;
  const action=target.dataset.action;
  try {
    if(action==='menu') $('.sidebar').classList.toggle('open');
    else if(action==='lock'){token='';sessionStorage.removeItem('traceharbor-session');if(state.preview)URL.revokeObjectURL(state.preview);Object.assign(state,{lab:null,preview:null,cases:[],openTabs:[],activeCase:null,verification:null});locked();}
    else if(action==='new-case') newCaseModal();
    else if(action==='close-modal') $('#dialog').close();
    else if(action==='open-case') {state.caseView='all';await openCase(target.dataset.id);}
    else if(action==='close-tab'){state.openTabs=state.openTabs.filter(c=>c.id!==target.dataset.id);if(state.activeCase?.id===target.dataset.id)state.route='overview';shell();}
    else if(action==='filter'){state.filter=target.dataset.value;content();}
    else if(action==='case-view'){state.caseView=target.dataset.value;content();}
    else if(action==='add-record') addRecordModal();
    else if(action==='entry-form') entryModal(target.dataset.kind);
    else if(action==='add-file'){$('#dialog').close();navigate('lab');}
    else if(action==='copy-hash'){await navigator.clipboard.writeText(target.dataset.hash);toast('SHA-256 copied.');}
    else if(action==='reference'){state.caseView='all';state.query='';content();$(`#record-${target.dataset.id}`)?.scrollIntoView({behavior:'smooth',block:'center'});}
    else if(action==='verify'){target.disabled=true;state.verification=await api(`/cases/${state.activeCase.id}/verify`);$('#verify-result').innerHTML=verificationHtml();}
    else if(action==='archive'){const next=state.activeCase.status==='active'?'archived':'active';await api(`/cases/${state.activeCase.id}`,{method:'PATCH',body:JSON.stringify({status:next})});await refreshCases();await openCase(state.activeCase.id);toast(next==='active'?'Case reopened.':'Case archived. Evidence has been retained.');}
    else if(action==='export') modal('Review before exporting',`<div class="notice">Reports include case notes, URLs, OCR and raw metadata. They are not automatically redacted. Review for personal data before sharing.</div><p class="tool-note">The ZIP includes a printable HTML report, structured JSON, the audit trail and a checksum manifest. Export stops if integrity checks fail.</p><label class="check"><input name="originals" type="checkbox">Include original files (up to 100 MiB total)</label>`,'export','Download report ZIP');
    else if(action==='original') modal('Download preserved original',`<input type="hidden" name="entry_id" value="${target.dataset.id}"><div class="notice">This file may contain sensitive information or malicious content. It downloads as a .bin file. Use an isolated environment when examining untrusted files.</div>`,'original','Download original');
    else if(action==='training') modal('Create a training case',`<p class="tool-note">Creates a clearly labelled practice case using public Python and Pillow documentation links, an example finding, and a labelled training event. No real people or incident data are included.</p>`,'training','Create training case');
  } catch(error) {toast(error.message);} finally {target.disabled=false;}
});

document.addEventListener('submit', async event=>{
  const form=event.target; if(!form.dataset.form) return;event.preventDefault();
  const kind=form.dataset.form, fd=new FormData(form), values=Object.fromEntries(fd), submit=$('button[type=submit]',form)||$('button:not([type])',form), error=$('.error',form);
  if(error) error.textContent=''; if(submit)submit.disabled=true;
  try {
    if(kind==='unlock'){
      const input=values.key.trim();token=input.includes('#token=')?new URLSearchParams(input.split('#')[1]).get('token'):input;
      if(!token)throw new Error('Paste the session key from your terminal.');sessionStorage.setItem('traceharbor-session',token);await start();return;
    }
    if(kind==='new-case'){const c=await post('/cases',values);$('#dialog').close();await refreshCases();state.caseView='all';await openCase(c.id);toast('Case created. Start collecting evidence.');}
    else if(kind==='choose-record') $('#dialog').close();
    else if(kind==='entry'){
      values.references=fd.getAll('references');if(values.event_at)values.event_at=new Date(values.event_at).toISOString();
      await post(`/cases/${state.activeCase.id}/entries`,values);$('#dialog').close();await refreshCases();await openCase(state.activeCase.id);toast('Record added to the evidence trail.');
    }
    else if(kind==='analyze'){
      const file=fd.get('file'), data_base64=await filePayload(file);
      $('#analysis-result').innerHTML='<div class="loading">Analysing locally… OCR can take up to 20 seconds.</div>';
      const payload={filename:file.name,title:file.name,kind:'file',data_base64,ocr:fd.has('ocr'),source_url:values.source_url,body:values.body};
      const response=await post(values.case_id?`/cases/${values.case_id}/entries`:'/analyze',payload);state.lab=response.analysis||response;
      if(state.preview)URL.revokeObjectURL(state.preview);state.preview=state.lab.image?URL.createObjectURL(file):null;
      if($('#analysis-result'))$('#analysis-result').innerHTML=analysisHtml(state.lab);
      if(values.case_id){await refreshCases();toast('Original and analysis saved to the selected case.');}else toast('Analysis complete. File and results were not saved.');
    }
    else if(kind==='inspect'){
      const result=await post('/inspect-url',{url:values.url});
      $('#url-result').innerHTML=`<div class="panel"><div class="panel-head"><h2>URL structure</h2><span class="inline-chip">NOT FETCHED</span></div><div class="panel-body"><dl class="kv">${['scheme','hostname','port','path','query','fragment'].map(k=>`<dt>${esc(k)}</dt><dd class="mono">${esc(result[k]||'—')}</dd>`).join('')}</dl>${result.notices.map(n=>`<p class="tool-note">${esc(n)}</p>`).join('')}<a class="btn" href="${esc(result.url)}" target="_blank" rel="noopener noreferrer">Open source manually ↗</a></div></div>`;
    }
    else if(kind==='leads'){
      const result=await post('/public-leads',{username:values.username});
      $('#lead-result').innerHTML=`<div class="panel"><div class="panel-head"><h2>Candidate public URLs</h2><small>NOT CHECKED</small></div>${result.links.map(l=>`<div class="case-row"><div class="square-icon">${icon('link')}</div><div><a class="case-title" href="${esc(l.url)}" target="_blank" rel="noopener noreferrer">${esc(l.label)} ↗</a><div class="case-sub">${esc(l.url)}</div></div>${badge('unverified')}</div>`).join('')}</div>`;
    }
    else if(kind==='compare'){
      if(values.left===values.right)throw new Error('Select two different file records.');const result=await post('/compare',values);
      $('#compare-result').innerHTML=`<div class="verify-result"><strong>${result.exact_bytes_match?'Exact original-byte match':'Original bytes differ'}</strong><div class="compare-number">${result.dhash_distance===null?'—':result.dhash_distance}</div><span>dHash distance ${result.dhash_distance===null?'unavailable':'out of 64 bits'}</span><p>${esc(result.notice)}</p></div>`;
    }
    else if(kind==='export'){await download(`/cases/${state.activeCase.id}/export?originals=${fd.has('originals')}`,`traceharbor-${state.activeCase.id.slice(0,8)}.zip`);$('#dialog').close();toast('Report downloaded. Review sensitive data before sharing.');}
    else if(kind==='original'){await download(`/entries/${values.entry_id}/original`,`${values.entry_id}.bin`);$('#dialog').close();}
    else if(kind==='training'){
      const c=await post('/cases',{title:'TRAINING · Documentation review',purpose:'Labelled practice data only. Review how documentation describes hashes and image metadata; no real incident or person is being investigated.',analyst:'Training analyst'});
      const s=await post(`/cases/${c.id}/entries`,{kind:'source',title:'Python hashlib documentation',source_url:'https://docs.python.org/3/library/hashlib.html',body:'Training source reference. No page contents have been automatically fetched or preserved.'});
      await post(`/cases/${c.id}/entries`,{kind:'source',title:'Pillow image documentation',source_url:'https://pillow.readthedocs.io/en/stable/reference/Image.html',body:'Training reference for manual review of image handling.'});
      await post(`/cases/${c.id}/entries`,{kind:'finding',title:'TRAINING · Establish a comparison baseline',body:'Example analyst note: retain an independently verified hash before comparing a file later. This is a training exercise, not an incident finding.',references:[s.id],assessment:'unverified'});
      await post(`/cases/${c.id}/entries`,{kind:'event',title:'TRAINING · Practice session opened',body:'A practice timeline event recorded when this training case was created.',event_at:new Date().toISOString(),references:[s.id]});
      $('#dialog').close();await refreshCases();state.caseView='all';await openCase(c.id);toast('Labelled training case created.');
    }
  }catch(exc){if(error&&document.contains(error))error.textContent=exc.message;else toast(exc.message);if(kind==='analyze'&&$('#analysis-result'))$('#analysis-result').innerHTML=empty('Analysis was not completed',exc.message);}
  finally{if(submit)submit.disabled=false;}
});

start();
