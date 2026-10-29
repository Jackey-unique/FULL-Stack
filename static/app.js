"use strict";
const $ = id => document.getElementById(id);
let token = null, page = 1, pages = 1, selected = null;
function message(text) { $("message").textContent = text; $("message").hidden = !text; }
async function api(path, options = {}) {
  const headers = {...(token ? {Authorization: "Bearer " + token} : {}), ...(options.body ? {"Content-Type":"application/json"} : {})};
  const result = await fetch("/api/v1" + path, {...options, headers});
  const data = result.status === 204 ? null : await result.json();
  if (!result.ok) {
    if (result.status === 401 && token) { token=null; $("workspace").hidden=true; $("login-panel").hidden=false; $("logout").hidden=true; $("detail").close(); }
    throw new Error(data?.error?.message || "Request failed");
  }
  return data;
}
function filters() { const q = new URLSearchParams(); for (const [k,v] of new FormData($("filters"))) if(v) q.set(k,v); return q; }
function cell(text) { const td=document.createElement("td"); td.textContent=text; return td; }
async function load() {
  const query=filters();
  const overview=await api("/statistics/overview?"+query);
  const synthetic=overview.data.by_source.length===1 && overview.data.by_source[0]._id==="synthetic";
  $("data-notice").textContent=synthetic ? "SYNTHETIC DEMO — All samples and estimates are invented test fixtures. No real images or clinical predictions." : "LOCAL RESEARCH DATA — File presence is not image quality control. Precomputed results require documented provenance.";
  $("dmri-label").textContent=synthetic?"Synthetic fixture flag":"Primary file presence";
  $("fmri-label").textContent=synthetic?"Synthetic fixture flag":"Primary file presence";
  $("paired-label").textContent=synthetic?"Synthetic paired fixtures":"Both local image types";
  const stats=overview.data.modalities[0] || {};
  $("total").textContent=overview.data.total; $("dmri").textContent=stats.dmri || 0; $("fmri").textContent=stats.fmri || 0; $("paired").textContent=stats.both || 0;
  query.set("page",page); query.set("page_size",10);
  const list=await api("/samples?"+query); pages=list.pagination.pages;
  $("rows").replaceChildren();
  for(const item of list.data){
    const row=document.createElement("tr");
    row.append(cell(item.sample_code),cell(item.age_at_scan_weeks == null ? "Unknown" : item.age_at_scan_weeks.toFixed(2)+" wk"),cell([item.has_dmri?"dMRI":"",item.has_fmri?"fMRI":""].filter(Boolean).join(" + ") || "Metadata only"),cell(item.status),cell(item.source));
    const td=cell(""); const button=document.createElement("button");button.textContent="View →";button.onclick=()=>openDetail(item._id).catch(e=>message(e.message));td.append(button);row.append(td);$("rows").append(row);
  }
  if(!list.data.length){const row=document.createElement("tr"), td=cell("No visible samples match these filters.");td.colSpan=6;row.append(td);$("rows").append(row);}
  $("page-info").textContent=`${list.pagination.total} sessions · Page ${page} of ${Math.max(1,pages)}`;
  $("previous").disabled=page<=1;$("next").disabled=page>=pages;
}
function entry(container,title,text){const box=document.createElement("div");box.className="entry";const label=document.createElement("strong"),p=document.createElement("p");label.textContent=title;p.textContent=text;box.append(label,p);container.append(box);}
async function openDetail(id){
  selected=id;const item=(await api("/samples/"+id)).data;
  $("detail-title").textContent=item.sample_code;
  $("detail-summary").textContent=`${item.source} · ${item.visibility} · ${item.files.length} indexed files · ${item.notes.length} notes`;
  $("notes").replaceChildren();$("analyses").replaceChildren();
  for(const note of item.notes)entry($("notes"),note.category,note.text);
  if(!item.notes.length)entry($("notes"),"No notes","Add the first research observation below.");
  for(const analysis of item.analyses)entry($("analyses"),`${analysis.modality} · ${analysis.estimated_age_weeks} weeks`,`${analysis.method} (${analysis.model_version})\nDifference: ${analysis.age_difference_weeks ?? "unknown"} weeks\n${analysis.provenance}`);
  if(!item.analyses.length)entry($("analyses"),"No precomputed results","No developmental age has been inferred for this sample.");
  $("raw").textContent=JSON.stringify(item,null,2);
  if(!$("detail").open)$("detail").showModal();
}
$("login-form").onsubmit=async event=>{event.preventDefault();message("");try{const data=await api("/auth/login",{method:"POST",body:JSON.stringify({username:$("username").value,password:$("password").value})});token=data.access_token;$("password").value="";$("account").textContent=data.user.display_name+" · "+data.user.role;$("login-panel").hidden=true;$("workspace").hidden=false;$("logout").hidden=false;page=1;await load();}catch(e){message(e.message);}};
$("filters").onsubmit=event=>{event.preventDefault();page=1;message("");load().catch(e=>message(e.message));};
$("previous").onclick=()=>{page--;load().catch(e=>message(e.message));};
$("next").onclick=()=>{page++;load().catch(e=>message(e.message));};
$("logout").onclick=async()=>{try{await api("/auth/logout",{method:"POST"});}finally{token=null;$("workspace").hidden=true;$("login-panel").hidden=false;$("logout").hidden=true;}};
$("close-detail").onclick=()=>$("detail").close();
$("note-form").onsubmit=async event=>{event.preventDefault();try{await api(`/samples/${selected}/notes`,{method:"POST",body:JSON.stringify({text:$("note-text").value,category:"research"})});$("note-text").value="";await openDetail(selected);}catch(e){message(e.message);$("detail").close();}};
