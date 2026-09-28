'use strict';
const $ = id => document.getElementById(id);
const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const e = escapeHtml;
const mealNames = {breakfast:'早餐',lunch:'午餐',dinner:'晚餐',snack:'加餐与饮品'};
const state = {patientId:null, profile:null, diseases:{}, foods:[], referenceDrugs:[], referenceFoods:{}, referenceGuidelines:[], featuredTopics:[], literacy:null, references:null, diary:null, guide:null, dirty:false, loadToken:0, journalLoaded:false, journalActivities:[], journalRecords:[], caseStudy:null};
const localDate = () => new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
const splitList = value => [...new Set(value.split(/[,，、\n]/).map(s=>s.trim()).filter(Boolean))];
function notify(message, isError=false){$('message').textContent=message;$('message').hidden=!message;if(isError)$('message').scrollIntoView({behavior:'smooth',block:'center'});}
async function api(path, options={}){
  const response=await fetch(path,{...options,headers:{'Content-Type':'application/json',...options.headers}});
  const data=await response.json();
  if(!response.ok){let text=data.detail;if(Array.isArray(text))text=text.map(x=>x.msg).join('；');const error=new Error(typeof text==='string'?text:'请求失败，请稍后再试');error.status=response.status;throw error;}
  return data;
}
function formToProfile(){
  const preferences=splitList($('preferences').value);if($('weight-goal').checked)preferences.push('体重管理');
  const medications=[...document.querySelectorAll('.medication-row')].map(row=>{
    const value=key=>row.querySelector(`[data-med="${key}"]`).value.trim();
    const drugName=value('drug_name');
    return {id:row.dataset.medId?Number(row.dataset.medId):null,drug_name:drugName,generic_name:value('generic_name')||drugName,dose:Number(value('dose')),unit:value('unit'),route:value('route'),frequency:'daily',administration_time:splitList(value('times')),meal_relation:value('meal_relation'),start_date:value('start_date'),end_date:value('end_date')||null,indication:value('indication'),active:true};
  });
  const savedUric=(state.profile?.conditions||[]).map(c=>typeof c==='string'?c:c.status==='active'?c.disease_code:null).filter(c=>['gout','hyperuricemia'].includes(c));
  return {patient:{name:$('name').value.trim(),age:Number($('age').value),sex:$('sex').value,height_cm:Number($('height').value),weight_kg:Number($('weight').value),allergies:splitList($('allergies').value),dietary_preferences:[...new Set(preferences)]},conditions:[...document.querySelectorAll('[name="disease"]:checked')].map(x=>x.value).concat(savedUric),medications};
}
function updateSummary(){
  const h=Number($('height').value),w=Number($('weight').value);$('bmi-value').textContent=h>0&&w>0?(w/(h/100)**2).toFixed(1):'—';
  const codes=[...document.querySelectorAll('[name="disease"]:checked')].map(x=>x.value);
  $('profile-tags').innerHTML=codes.map(c=>`<span>${e(state.diseases[c]?.name||c)}</span>`).join('');
  $('profile-summary').textContent=codes.length?'饮食指南将结合这些记录，合并共同的饮食重点。':'没有选择疾病也可以记录饮食。';
}
function fillProfile(profile){
  const p=profile.patient;$('name').value=p.name;$('age').value=p.age;$('sex').value=p.sex||'unspecified';$('height').value=p.height_cm;$('weight').value=p.weight_kg;
  $('allergies').value=(p.allergies||[]).join('、');$('preferences').value=(p.dietary_preferences||[]).filter(x=>x!=='体重管理').join('、');$('weight-goal').checked=(p.dietary_preferences||[]).includes('体重管理');
  const codes=profile.conditions.map(c=>typeof c==='string'?c:c.status==='active'?c.disease_code:null);
  document.querySelectorAll('[name="disease"]').forEach(input=>input.checked=codes.includes(input.value));
  $('medication-list').replaceChildren();profile.medications.forEach(addMedication);updateMedicationEmpty();updateSummary();
}
function loadDemo(showMessage=true){
  state.patientId=null;state.profile=null;state.guide=null;state.diary=null;state.dirty=false;state.loadToken++;state.journalLoaded=false;
  localStorage.removeItem('health-companion-profile-v2');
  fillProfile({patient:{name:'林先生（演示）',age:42,sex:'male',height_cm:172,weight_kg:82,allergies:[],dietary_preferences:['清淡','体重管理']},conditions:['hyperlipidemia','fatty_liver'],medications:[]});
  $('step-nutrition').disabled=true;$('demo-note').hidden=false;showView('profile');
  if(showMessage)notify('已载入虚拟示例。你可以修改资料，再生成饮食指南；原有记录不会被删除。');
}
function selectOptions(options, selected){return Object.entries(options).map(([value,label])=>`<option value="${e(value)}" ${value===selected?'selected':''}>${e(label)}</option>`).join('');}
function addMedication(m={}){
  const row=document.createElement('div');row.className='medication-row';if(m.id)row.dataset.medId=m.id;
  row.innerHTML=`<div class="row-heading"><b class="small">用药记录</b><button type="button" class="remove remove-medication">移除此记录 ×</button></div><div class="fields">
  <label>药品名称<input data-med="drug_name" required maxlength="100" placeholder="按药盒或处方填写" value="${e(m.drug_name)}"></label>
  <label>通用名（选填）<input data-med="generic_name" maxlength="100" placeholder="例如：阿托伐他汀" value="${e(m.generic_name)}"></label>
  <label>每次剂量<input data-med="dose" type="number" step="any" min="0.000001" required placeholder="按处方填写" value="${e(m.dose)}"></label>
  <label>剂量单位<input data-med="unit" required maxlength="30" placeholder="例如：mg、片" value="${e(m.unit)}"></label>
  <label>每天服药时间<input data-med="times" required placeholder="08:00，20:00" value="${e((m.administration_time||[]).join('，'))}"></label>
  <label>与进餐关系<select data-med="meal_relation">${selectOptions({anytime:'无特殊记录',before_meal:'饭前',with_meal:'随餐',after_meal:'饭后',fasting:'空腹'},m.meal_relation||'anytime')}</select></label>
  <label>实际开始日期<input data-med="start_date" type="date" required value="${e(m.start_date)}"></label>
  <label>结束日期（选填）<input data-med="end_date" type="date" value="${e(m.end_date)}"></label>
  <label>用药途径<select data-med="route">${selectOptions({oral:'口服',injection:'注射',topical:'外用',inhalation:'吸入',other:'其他'},m.route||'oral')}</select></label>
  <label>用途备注（选填）<input data-med="indication" maxlength="500" value="${e(m.indication)}"></label></div>
  <p class="hint" style="margin:14px 0 0">这里只维护记录，不改变处方。移除已保存药物后，该记录会标为停用。</p>`;
  $('medication-list').append(row);row.querySelector('.remove-medication').addEventListener('click',()=>{row.remove();updateMedicationEmpty();});updateMedicationEmpty();
}
function updateMedicationEmpty(){$('no-medications').hidden=$('medication-list').children.length>0;}
function renderDrugResults(){
  const term=$('drug-search').value.trim().toLocaleLowerCase();
  const matches=state.referenceDrugs.filter(r=>!term||[r.name_zh,r.name_en,r.key,...r.aliases].some(x=>x.toLocaleLowerCase().includes(term))).slice(0,8);
  $('drug-results').innerHTML=matches.map(r=>`<div class="reference-row"><div><b>${e(r.name_zh)}</b><span>${e(r.name_en)} · ${e(r.group)}</span></div><div><button type="button" class="text-button" data-reference-drug="${e(r.key)}">填入名称</button>${r.dailymed_label_url?`<a href="${e(r.dailymed_label_url)}" target="_blank" rel="noopener" title="${e(r.dailymed_label_title)}">说明书 ↗</a>`:''}</div></div>`).join('')||'<p class="hint">当前本地索引没有匹配项。仍可按实际药盒手动填写；未收录不代表没有这个药。</p>';
}
function renderReferenceSources(){
  if(!state.references)return;
  $('reference-source-list').innerHTML=state.references.sources.map(s=>`<div><strong>${e(s.records)}</strong><span>${e(s.name_zh||s.name)}</span><small>${e(s.name)} · ${e(s.purpose)} · ${s.last_synced?'已同步':'待同步'}</small><a href="${e(s.url)}" target="_blank" rel="noopener">来源 ↗</a></div>`).join('');
}
function renderQueryDrugs(){
  const term=$('query-drug-search').value.trim().toLocaleLowerCase();
  const rows=state.referenceDrugs.filter(r=>!term||[r.name_zh,r.name_en,r.key,...r.aliases].some(x=>x.toLocaleLowerCase().includes(term))).slice(0,12);
  $('query-drug-results').innerHTML=rows.length?rows.map(r=>`<div class="reference-row"><div><b>${e(r.name_zh)}</b><span>${e(r.name_en)} · ${e(r.group)}</span></div><a href="${e(r.dailymed_label_url||r.rxnorm_url)}" target="_blank" rel="noopener">核对原始资料 ↗</a></div>`).join(''):'<p class="hint">本地常见药目录没有匹配项；未收录不代表不存在。</p>';
}
function renderQueryFoods(){
  const term=$('query-food-search').value.trim().toLocaleLowerCase();
  const rows=Object.values(state.referenceFoods).filter(r=>!term||[r.name_zh||'',r.description_en,r.key].some(x=>x.toLocaleLowerCase().includes(term))).slice(0,12);
  $('query-food-results').innerHTML=rows.length?rows.map(r=>`<div class="reference-row"><div><b>${e(r.name_zh||'暂无中文类别名')}</b><span>${e(r.description_en)} · ${e(r.data_type)}</span></div><a href="${e(r.source_url)}" target="_blank" rel="noopener">核对原始资料 ↗</a></div>`).join(''):'<p class="hint">精选食品样本没有匹配项；可在下方食品成分库继续查询。</p>';
}
function renderQueryGuidelines(){
  const term=$('query-guideline-search').value.trim().toLocaleLowerCase();
  const rows=state.referenceGuidelines.filter(g=>!term||[g.title,g.publisher,g.key].some(x=>x.toLocaleLowerCase().includes(term))).slice(0,30);
  $('query-guideline-results').innerHTML=rows.length?rows.map(g=>`<div class="reference-row"><div><b>${e(g.title)}</b><span>${e(g.publisher)} · ${e(g.year)}</span></div><a href="${e(g.source_url)}" target="_blank" rel="noopener">查看原文 ↗</a></div>`).join(''):'<p class="hint">没有匹配的官方指南。</p>';
}
$('query-drug-search').addEventListener('input',renderQueryDrugs);
$('query-food-search').addEventListener('input',renderQueryFoods);
$('query-guideline-search').addEventListener('input',renderQueryGuidelines);
function renderLiteracy(conditions, patient){
  const box=$('literacy-cards');
  if(!state.literacy){box.innerHTML='<p class="hint">科普资料暂不可用。</p>';return;}
  const codes=new Set(conditions.map(c=>c.disease_code));
  const matches=state.literacy.topics.filter(t=>t.always||t.conditions.some(code=>codes.has(code))||(t.older_adult&&patient.age>=65));
  box.innerHTML=matches.map(t=>{
    let value='检查结果未录入';
    if(t.key==='bmi'){
      const bmi=patient.bmi;
      let category='仅作身高体重参考';
      if(patient.age>=18&&patient.age<65)category=bmi<18.5?'低于一般成人参考范围':bmi<24?'在一般成人参考范围内':bmi<28?'落在一般成人超重范围':'落在一般成人肥胖筛查范围';
      value=`已计算 BMI ${e(bmi.toFixed(1))} · ${category}`;
    }
    return `<article class="literacy-item"><div class="literacy-head"><h3>${e(t.title)}</h3><span>${e(value)}</span></div><p>${e(t.meaning)}</p><p class="literacy-action"><b>看什么：</b>${e(t.look_for)}</p><a href="${e(t.source_url)}" target="_blank" rel="noopener">${e(t.source_title)} ↗</a></article>`;
  }).join('');
}
function renderGuidelines(conditions, age){
  const codes=new Set(conditions.map(c=>c.disease_code));
  if(age>=65)codes.add('older_adult');
  if(state.guide?.patient?.bmi>=28)codes.add('obesity');
  const matches=state.referenceGuidelines.filter(g=>g.condition_codes.some(code=>codes.has(code)));
  $('guideline-results').innerHTML=matches.length?matches.map(g=>`<div class="reference-row"><div><b>${e(g.title)}</b><span>${e(g.publisher)} · ${e(g.year)}</span></div><a href="${e(g.source_url)}" target="_blank" rel="noopener">查看原文 ↗</a></div>`).join(''):'<p class="hint">当前资料库暂无与你已记录疾病直接对应的指南索引。</p>';
}
async function searchPurines(){
  const q=$('purine-search').value.trim();
  if(!q){$('purine-results').innerHTML='<p class="hint">输入中文或英文食物名开始查询。</p>';return;}
  const result=await api(`/reference/purines?q=${encodeURIComponent(q)}&limit=12`);
  $('purine-results').innerHTML=result.items.length?result.items.map(r=>`<div class="reference-row"><div><b>${e(r.food_name_zh||'暂无中文类别名')}</b><span>${e(r.food_name_en)} · ${e(r.total_purines_mg)} ${e(r.unit)} · ${e(r.country||'产地未列出')} · 样本数 ${e(r.sample_n||'未列出')}</span></div><a href="${e(r.source_url)}" target="_blank" rel="noopener">数据来源 ↗</a></div>`).join(''):'<p class="hint">当前资料库没有匹配条目；可试英文名称。</p>';
}
let purineTimer;
$('purine-search').addEventListener('input',()=>{clearTimeout(purineTimer);purineTimer=setTimeout(()=>searchPurines().catch(error=>notify(error.message,true)),250);});
function renderFeaturedTopics(conditions, age){
  const codes=new Set(conditions.map(c=>c.disease_code));
  if(age>=65)codes.add('older_adult');
  if(state.guide?.patient?.bmi>=28)codes.add('obesity');
  const matches=state.featuredTopics.filter(t=>t.condition_codes.some(code=>codes.has(code)));
  $('featured-topic-results').innerHTML=matches.length?matches.map(t=>`<div class="reference-row"><div><b>${e(t.title_zh||t.title_en)}</b><span>${e(t.title_en)} · MedlinePlus 英文资料</span></div><a href="${e(t.source_url)}" target="_blank" rel="noopener">查看原文 ↗</a></div>`).join(''):'<p class="hint">当前没有直接匹配的主题；可在下方搜索。</p>';
}
async function searchComposition(){
  const q=$('composition-search').value.trim();
  if(!q){$('composition-results').innerHTML='<p class="hint">输入中文或英文食物名开始查询。</p>';return;}
  const result=await api(`/reference/composition?q=${encodeURIComponent(q)}&limit=12`);
  const number=(v,unit)=>v===null?'未列':`${Number(v).toFixed(1)} ${unit}`;
  $('composition-results').innerHTML=result.items.length?result.items.map(r=>{const n=r.nutrients_per_100g;return `<div class="reference-row"><div><b>${e(r.name_zh||'暂无中文类别名')}</b><span>${e(r.description_en)} · ${e(r.data_type==='foundation_food'?'基础食品库':'历史食品库')} · 每100克：能量 ${e(number(n.energy_kcal,'kcal'))}，蛋白质 ${e(number(n.protein_g,'g'))}，钠 ${e(number(n.sodium_mg,'mg'))}</span></div><a href="${e(r.source_url)}" target="_blank" rel="noopener">全部数据 ↗</a></div>`;}).join(''):'<p class="hint">本地目录没有匹配项；可试英文名称。</p>';
}
async function searchHealthTopics(){
  const q=$('topic-search').value.trim();
  if(!q){$('topic-results').innerHTML='';return;}
  const result=await api(`/reference/health-topics?q=${encodeURIComponent(q)}&limit=12`);
  $('topic-results').innerHTML=result.items.length?result.items.map(t=>`<div class="reference-row"><div><b>${e(t.title_zh||t.title_en)}</b><span>${e(t.title_en)} · MedlinePlus 英文资料</span></div><a href="${e(t.source_url)}" target="_blank" rel="noopener">查看原文 ↗</a></div>`).join(''):'<p class="hint">没有找到匹配的主题；大部分条目仅支持英文搜索。</p>';
}
let compositionTimer,topicTimer;
$('composition-search').addEventListener('input',()=>{clearTimeout(compositionTimer);compositionTimer=setTimeout(()=>searchComposition().catch(error=>notify(error.message,true)),250);});
$('topic-search').addEventListener('input',()=>{clearTimeout(topicTimer);topicTimer=setTimeout(()=>searchHealthTopics().catch(error=>notify(error.message,true)),250);});
function showView(view){
  if(view==='nutrition'&&!state.patientId)return;
  notify('');
  $('profile-view').hidden=view!=='profile';$('nutrition-view').hidden=view!=='nutrition';
  $('step-profile').classList.toggle('active',view==='profile');$('step-nutrition').classList.toggle('active',view==='nutrition');
  $('step-profile').setAttribute('aria-current',view==='profile'?'step':'false');$('step-nutrition').setAttribute('aria-current',view==='nutrition'?'step':'false');
  if(location.hash!==`#${view}`)history.replaceState(null,'',`#${view}`);
  window.scrollTo({top:0,behavior:'smooth'});
}
function showTab(tab){
  for(const key of ['guide','diary','journal','query']){$(`${key}-panel`).hidden=key!==tab;$(`tab-${key}`).classList.toggle('active',key===tab);$(`tab-${key}`).setAttribute('aria-selected',String(key===tab));}
}
const constraintLabels={saturated_fat:['减少饱和脂肪','↘'],fiber:['增加膳食纤维','↗'],added_sugar:['减少添加糖','−'],alcohol:['留意饮酒','○'],sodium:['减少盐摄入','−'],refined_carbohydrate:['调整主食选择','↔'],high_purine_food:['留意高嘌呤食物','○'],hydration:['确认饮水安排','◇']};
function renderSafety(alerts){return alerts.map(a=>`<div class="safety-note ${e(a.severity)}"><b>${e(a.category==='medication_meal_timing'?'用药与进餐提示':'需要核对的提醒')}</b><p>${e(a.explanation)} ${e(a.action)}</p><small>${e(a.exposure_note)} · 规则 ${e(a.rule_id)}</small></div>`).join('');}
function exerciseCard(activity, recommended=false, showMet=true){
  const source=activity.compendium_code?(showMet?`活动编码 ${e(activity.compendium_code)} · 19—59 岁成人参考 ${e(activity.met)} MET`:`活动编码 ${e(activity.compendium_code)} · 当前年龄不显示成人 MET 参考值`):'来源为一般活动建议；未给该动作指定 MET';
  const stage=activity.tags.includes('advanced')?'<b class="exercise-stage advanced">进阶项目</b>':activity.tags.includes('moderate')?'<b class="exercise-stage">中等强度示例</b>':recommended?'<b>起步推荐</b>':'';
  return `<article class="exercise-card"><div class="exercise-card-top"><span>${e(activity.category)}</span>${stage}</div><h4>${e(activity.name)}</h4><p><strong>从这里开始：</strong>${e(activity.start)}</p><p>${e(activity.how)}</p><p class="exercise-adjust">${e(activity.adjust)}</p><small>${source}${activity.met_note?` · ${e(activity.met_note)}`:''} · <a href="${e(activity.source_url)}" target="_blank" rel="noopener">查看来源 ↗</a></small></article>`;
}
function renderDiaryExerciseOptions(){
  const activities=state.guide?.exercise?.activities||[];
  const groups=[['适合从少量开始',a=>a.tags.includes('starter')],['建立基础后再尝试',a=>a.tags.includes('moderate')],['进阶距离或较高强度',a=>a.tags.includes('advanced')]];
  $('diet-exercise').innerHTML='<option value="">没有记录运动</option>'+groups.map(([label,match])=>`<optgroup label="${e(label)}">${activities.filter(match).map(a=>`<option value="${e(a.id)}">${e(a.name)}</option>`).join('')}</optgroup>`).join('');
}
function renderDietExerciseNote(){
  const id=$('diet-exercise').value,activity=state.guide?.exercise?.activities.find(a=>a.id===id);
  $('diet-exercise-note').textContent=activity?(activity.tags.includes('advanced')?'进阶项目：':activity.tags.includes('moderate')?'建立慢走基础后再尝试：':'起步项目：')+activity.adjust:'可选择慢走、广播体操、快走或进阶 5 公里项目；请填实际完成时长。';
}
function renderExercise(){
  const plan=state.guide?.exercise;if(!plan)return;
  $('exercise-scope').textContent=plan.available?`${plan.scope} ${plan.intensity_note}`:plan.reason;
  if(!plan.available){$('exercise-recommended').replaceChildren();$('exercise-week').replaceChildren();$('exercise-notes').replaceChildren();$('exercise-results').replaceChildren();$('exercise-search').disabled=true;return;}
  $('exercise-search').disabled=false;
  const byId=Object.fromEntries(plan.activities.map(item=>[item.id,item]));
  const showMet=state.guide.patient.age>=19&&state.guide.patient.age<=59;
  $('exercise-recommended').innerHTML=`<div class="exercise-grid">${plan.recommended.map(id=>exerciseCard(byId[id],true,showMet)).join('')}</div>`;
  $('exercise-week').innerHTML=plan.week.map(day=>`<div class="exercise-day"><b>${e(day.day)}</b><span>${day.items.length?day.items.map(item=>e(item.name)).join(' · '):'休息或自由轻活动'}</span></div>`).join('');
  $('exercise-notes').innerHTML=plan.notes.map(note=>`<div class="exercise-note"><b>${e(note.title)}</b><p>${e(note.text)} <a href="${e(note.source_url)}" target="_blank" rel="noopener">依据 ↗</a></p></div>`).join('');
  const term=$('exercise-search').value.trim().toLocaleLowerCase();
  const matches=plan.activities.filter(item=>!term||[item.name,item.category,item.how,...item.tags].some(value=>value.toLocaleLowerCase().includes(term)));
  $('exercise-results').innerHTML=matches.map(item=>exerciseCard(item,plan.recommended.includes(item.id),showMet)).join('')||'<p class="hint">没有匹配的活动；可尝试搜索“步行”“坐姿”或“拉伸”。</p>';
}
$('exercise-search').addEventListener('input',renderExercise);
async function loadGuide(){
  state.guide=await api(`/patients/${state.patientId}/diet-guide`);const g=state.guide,p=g.patient;
  const conditions=g.conditions.filter(c=>c.status==='active');
  $('nutrition-profile-summary').textContent=`${p.name} · ${p.age} 岁 · ${p.height_cm} cm / ${p.weight_kg} kg · BMI ${p.bmi.toFixed(1)}`;
  $('guide-tags').innerHTML=conditions.map(c=>`<span>${e(c.disease_name)}</span>`).join('');
  $('guide-description').textContent=conditions.length?'把多个健康目标放在一起，先关注共同的饮食重点。':'先从规律记录和多样的食物选择开始。';
  $('guide-cards').innerHTML=g.nutrition.constraints.map(c=>{
    const [title,icon]=constraintLabels[c.constraint]||[c.constraint,'◇'];
    const sources=[...new Set(c.provenance.map(p=>p.evidence_source))].filter(u=>u.startsWith('https://'));
    return `<article class="guide-card"><div class="guide-card-top"><span class="guide-icon">${e(icon)}</span><h3>${e(title)}</h3></div><p>${e(c.explanation)}</p><div class="source"><span>依据：${c.sources.map(s=>e(state.diseases[s]?.name||s)).join('、')}</span>${sources.map((u,i)=>`<a href="${e(u)}" target="_blank" rel="noopener">参考来源${sources.length>1?i+1:''} ↗</a>`).join('')}</div></article>`;
  }).join('')||'<div class="card empty-guide"><h3>暂没有疾病相关的饮食约束</h3><p class="muted">可以先记录一天的饮食，查看食物类别的演示评分。没有命中约束不代表已经完成营养评估。</p></div>';
  renderIntegratedGuidance(g, conditions);renderLiteracy(conditions,p);renderExercise();renderDiaryExerciseOptions();
  $('weight-note').textContent=g.weight_note;$('guide-bmi').textContent=p.bmi.toFixed(1);
  let safety=renderSafety(g.safety.alerts);
  if(g.safety.coverage.unknown_drugs.length)safety+=`<div class="safety-note">当前规则未覆盖这些药物：${e(g.safety.coverage.unknown_drugs.join('、'))}。请向医生或药师核对，不能据此判断没有风险。</div>`;
  if(p.allergies.length)safety+=`<div class="safety-note">已记录食物过敏：${e(p.allergies.join('、'))}。当前指南不提供食谱或无过敏保证，请核对具体食材。</div>`;
  if(p.age<18)safety+='<div class="safety-note">当前演示饮食方向主要面向成年人；未成年人的饮食请由专业人员结合生长情况确认，不提供总评分。</div>';
  $('guide-safety').innerHTML=safety;
  renderReferenceSources();renderGuidelines(conditions,p.age);renderFeaturedTopics(conditions,p.age);
}
function emptyDiary(day){return {day,day_complete:false,activity_level:'inactive',exercise_activity_id:null,exercise_minutes:0,meals:Object.keys(mealNames).map(name=>({name,status:'unreported',items:[],notes:''}))};}
function foodOptions(selected){return '<option value="">选择食物</option>'+state.foods.map(f=>`<option value="${f.id}" ${f.id===selected?'selected':''}>${e(f.name)}</option>`).join('');}
const reviewTagNotes={
  sugary_drink:'含糖饮品或甜食：留意这一餐的甜饮料、甜点',
  rich_food:'油炸或高脂食物：可考虑更清淡的做法',
  alcohol:'酒精饮品：请结合已记录的疾病核对饮酒安排',
  high_sodium:'高盐食物：留意加工或腌制食品的钠'
};
function foodReview(food){return food?Object.keys(reviewTagNotes).filter(tag=>(food.tags?.[tag]||0)>0).map(tag=>reviewTagNotes[tag]):[];}
function renderReviewSummary(){
  const flagged=state.diary.meals.flatMap(meal=>meal.items.map((item,index)=>({meal,index,food:state.foods.find(f=>f.id===item.food_id)})).filter(x=>foodReview(x.food).length));
  const box=$('food-review-summary');box.hidden=!flagged.length;
  if(!flagged.length){box.replaceChildren();return;}
  box.innerHTML=`<strong>已圈出 ${flagged.length} 处值得留意的食物</strong><p>点名称可定位到对应记录。圈选依据演示食物分类；未圈出不代表整天饮食已评估完毕。</p><div class="review-jump-list">${flagged.map(x=>`<button type="button" data-review-meal="${e(x.meal.name)}" data-review-index="${x.index}">${e(mealNames[x.meal.name])} · ${e(x.food.name)}</button>`).join('')}</div>`;
}
$('food-review-summary').addEventListener('click',event=>{
  const button=event.target.closest('[data-review-meal]');if(!button)return;
  const row=[...document.querySelectorAll('#meals .food-row')].find(el=>el.closest('[data-meal]')?.dataset.meal===button.dataset.reviewMeal&&el.dataset.index===button.dataset.reviewIndex);
  row?.scrollIntoView({behavior:'smooth',block:'center'});row?.querySelector('select[data-action="food"]')?.focus({preventScroll:true});
});
function renderMeals(){
  $('meals').innerHTML=state.diary.meals.map((meal,index)=>`<section class="card meal-card" data-meal="${meal.name}"><div class="meal-header"><h2><span class="meal-index">0${index+1}</span>${mealNames[meal.name]}</h2><select data-action="status" aria-label="${mealNames[meal.name]}记录状态">${selectOptions({unreported:'尚未记录',recorded:'已记录',skipped:meal.name==='snack'?'没有加餐':'这餐没吃'},meal.status)}</select></div>
  ${meal.items.map((item,i)=>{const food=state.foods.find(f=>f.id===item.food_id),reference=state.referenceFoods[item.food_id],reasons=foodReview(food);return `<div class="food-row ${reasons.length?'needs-review':''}" data-index="${i}"><div><span class="food-select-wrap"><select data-action="food" required aria-label="${mealNames[meal.name]}食物 ${i+1}">${foodOptions(item.food_id)}</select></span><span class="portion">${e(food?.portion||'从列表选择，或用“其他食物”记下名称。')}${reference?` · <a href="${e(reference.source_url)}" target="_blank" rel="noopener" title="${e(reference.description_en)}；仅作食品参考，不等于这餐的营养成分">USDA 参考 ↗</a>`:''}</span>${reasons.length?`<p class="food-review-note"><b>圈出原因：</b>${reasons.map(reason=>e(reason)).join("；")}</p>`:""}</div><label class="food-quantity-label"><input data-action="servings" aria-label="${mealNames[meal.name]}份数 ${i+1}" type="number" min="0.1" max="20" step="0.1" required value="${e(item.servings)}">份</label><button type="button" class="remove" data-action="remove" aria-label="删除${mealNames[meal.name]}食物 ${i+1}">×</button>${item.food_id==='other'?`<input class="food-description" data-action="description" required maxlength="200" placeholder="食物名称、做法和份量；暂不参与评分" value="${e(item.description)}">`:''}</div>`;}).join('')}
  <div class="meal-actions"><button type="button" class="text-button" data-action="add">＋ 添加食物</button><span class="small muted">份量按实际记录</span></div><textarea data-action="notes" aria-label="${mealNames[meal.name]}备注" maxlength="500" rows="1" placeholder="备注（不计分）；吃过的食物请逐项添加">${e(meal.notes)}</textarea></section>`).join('');
  $('day-complete').checked=state.diary.day_complete;
  $('activity-level').value=state.diary.activity_level||'inactive';
  $('diet-exercise').value=state.diary.exercise_activity_id||'';
  $('diet-exercise-minutes').value=state.diary.exercise_minutes||0;
  renderDietExerciseNote();
  renderReviewSummary();
}
function invalidateScore(){state.dirty=true;renderScore(null);$('diary-status').textContent='记录有更改，尚未保存。完整录入后，点击“保存饮食并评分”。';}
function exampleDiary(improved){
  const item=(food_id,servings=1)=>({food_id,servings,description:''});
  const dishes=improved?[[item('oats',1.5),item('egg'),item('milk'),item('whole_wheat')],[item('brown_rice',1.5),item('fish',1.5),item('vegetables',1.5),item('nuts')],[item('white_rice',1.5),item('tofu',2),item('vegetables',2)],[item('apple'),item('nuts'),item('water')]]:[[item('whole_wheat'),item('milk'),item('cake')],[item('white_rice'),item('fried_chicken'),item('vegetables')],[item('white_rice'),item('fatty_meat'),item('vegetables',0.5),item('beer')],[item('sweet_drink')]];
  state.diary={day:$('diary-date').value,day_complete:false,activity_level:$('activity-level').value,exercise_activity_id:$('diet-exercise').value||null,exercise_minutes:Number($('diet-exercise-minutes').value)||0,meals:Object.keys(mealNames).map((name,i)=>({name,status:'recorded',items:dishes[i],notes:'虚拟示例，仅用于体验'}))};
  renderMeals();invalidateScore();$('diary-status').textContent=`已载入${improved?'调整后':'待改善'}的虚拟饮食示例，尚未保存。请确认整天记录后再评分。`;
}
function renderNutrition(estimate){
  if(!estimate)return '';
  const t=estimate.totals, c=estimate.covered;
  const stat=(key,unit)=>`${e(t[key])}${unit}${c[key]?'':'（部分食品缺值）'}`;
  const comparisons=estimate.comparisons.map(x=>`<div class="nutrition-comparison"><span>${e(x.label)}：${e(x.actual)} ${e(x.unit)}<br><small>一般参考约 ${e(x.reference)} ${e(x.unit)}</small></span><b>${e(x.status)}</b></div>`).join('');
  const items=estimate.items.map(x=>`<li>${e(mealNames[x.meal])} · ${e(x.name)} ${e(x.servings)} 份，约 ${e(x.grams)} g：${e(x.energy_kcal)} kcal${x.source_url?` <a href="${e(x.source_url)}" target="_blank" rel="noopener">数据 ↗</a>`:''}<br><small>${e(x.assumption)}</small></li>`).join('');
  return `<section class="nutrition-estimate"><h3>已记录食物的营养粗估</h3><strong class="nutrition-energy">约 ${stat('energy_kcal',' kcal')}</strong><p>蛋白质 ${stat('protein_g',' g')} · 脂肪 ${stat('fat_g',' g')} · 碳水 ${stat('carbohydrate_g',' g')}</p><p>膳食纤维 ${stat('fiber_g',' g')} · 食物本身钠 ${stat('sodium_mg',' mg')}</p>${estimate.recorded_exercise?`<p><b>当天运动：</b>${e(estimate.recorded_exercise.name)} ${e(estimate.recorded_exercise.minutes)} 分钟</p>`:''}${comparisons||'<p class="nutrition-pending">当前只显示已记食物小计；记录完整且食品可估算后，才比较摄入多或少。</p>'}${estimate.notes.map(note=>`<p class="nutrition-note">${e(note)}</p>`).join('')}<details><summary>逐项估算与计算依据</summary><ul>${items}</ul><p>成人静息能量按 Mifflin–St Jeor 公式估算，维持需求再乘所选整体活动水平的演示系数（1.2、1.3、1.375、1.55 或 1.725；本次 ${e(estimate.activity_factor??'未选')}）。单次运动不再额外加算或扣除。偏少/偏多仅按维持需求 ±20% 的演示区间标注。蛋白质一般成人参考 0.8 g/kg，纤维参考 14 g/1000 kcal。不能由一天记录判定营养缺乏。</p><p><a href="${e(estimate.sources.food)}" target="_blank" rel="noopener">USDA FoodData Central ↗</a> · <a href="${e(estimate.sources.resting_energy)}" target="_blank" rel="noopener">静息能量公式 ↗</a> · <a href="${e(estimate.sources.protein)}" target="_blank" rel="noopener">营养参考值 ↗</a> · <a href="${e(estimate.sources.fiber)}" target="_blank" rel="noopener">膳食纤维参考 ↗</a></p></details></section>`;
}
function renderScore(result){
  $('score-value').textContent=result?.score??'—';$('score-label').textContent=result?.label||'先记录，再看变化。';
  $('score-description').textContent=result?result.limitations:'这不是临床量表。保存后可查看单独的热量与营养粗估。';
  if(!result){$('score-detail').replaceChildren();return;}
  let html=result.blockers.map(text=>`<p class="blocker">${e(text)}</p>`).join('');
  html+=renderNutrition(result.nutrition_estimate);
  if(result.score!==null){
    html+=result.dimensions.map(d=>`<div class="dimension"><div class="dimension-top"><span>${e(d.label)}</span><b>${d.earned} / ${d.weight}</b></div><div class="dimension-track"><i style="width:${d.completion}%"></i></div>${d.weighted_for.length?`<small>结合${d.weighted_for.map(c=>e(state.diseases[c]?.name||c)).join('、')}提高演示权重</small>`:''}</div>`).join('');
    html+=`<div class="suggestions"><b>下一餐，可以试试</b>${result.suggestions.length?result.suggestions.map(s=>`<p>· ${e(s)}</p>`).join(''):'<p>保留这些选择，并继续留意实际份量与饮食多样性。高分不代表营养已足量。</p>'}</div>`;
  }
  html+=result.allergy_notes.map(s=>`<p class="blocker">${e(s)}</p>`).join('');
  html+=renderSafety(result.safety?.alerts||[]);
  html+=`<details><summary>这个分数如何计算？</summary><p>${e(result.method)}</p><p>${e(result.total_formula)}。本次权重总和 ${result.total_weight}。</p>${result.dimensions.map(d=>`<p><b>${e(d.label)}</b>：${e(d.formula)}；本次分类份数 ${d.amount}。<a href="${e(d.evidence_source)}" target="_blank" rel="noopener">饮食方向来源 ↗</a></p>`).join('')}<p>这里的份数是演示分类计数，不是营养素含量。来源支持饮食方向，不验证此评分公式。</p><p>规则版本 ${e(result.rule_version)}；评分使用保存当时的健康资料。修改资料后，请重新保存当天饮食以重新评分。</p></details>`;
  $('score-detail').innerHTML=html;
}
async function loadDiary(day){
  const token=++state.loadToken;state.diary=emptyDiary(day);state.dirty=false;renderMeals();renderScore(null);$('diary-status').textContent='正在读取当天记录…';
  $('save-diary').disabled=true;
  try{const saved=await api(`/patients/${state.patientId}/diet-days/${day}`);if(token!==state.loadToken)return;state.diary=saved.diary;renderMeals();renderScore(saved.result);$('diary-status').textContent='已载入本地保存的记录。评分基于上次保存时的健康资料，可修改并重新评分。';}
  catch(error){if(token!==state.loadToken)return;if(error.status===404){$('diary-status').textContent='这一天还没有记录。逐项添加食物，或先体验一份虚拟示例。';}else notify(error.message,true);}
  finally{if(token===state.loadToken)$('save-diary').disabled=false;}
  if(token===state.loadToken)await loadHistory();
}
async function loadHistory(){
  const history=await api(`/patients/${state.patientId}/diet-days`);
  $('diary-history').innerHTML=history.length?'<span>最近记录：</span>'+history.map(item=>`<button type="button" class="text-button" data-day="${item.day}">${item.day} · ${item.score===null?'待补充':item.score+' 分'}</button>`).join(''):'';
}
function clearJournal(){
  for(const id of ['breakfast','lunch','dinner','snacks','notes'])$(`journal-${id}`).value='';
  $('journal-activity').value='';$('journal-minutes').value='0';$('journal-weight').value='';$('journal-status').textContent='这一天还没有综合日志。';
}
function fillJournal(entry){
  for(const id of ['breakfast','lunch','dinner','snacks','notes'])$(`journal-${id}`).value=entry[id]||'';
  $('journal-activity').value=entry.activity_id||'';$('journal-minutes').value=entry.activity_minutes??0;$('journal-weight').value=entry.weight_kg??'';
  $('journal-status').textContent='已载入本机保存的日志。';
}
async function loadJournalDay(day){
  try{const saved=await api(`/patients/${state.patientId}/journal-days/${day}`);if($('journal-date').value===day)fillJournal(saved.entry);}
  catch(error){if(error.status===404)clearJournal();else notify(error.message,true);}
}
function renderJournalList(){
  $('journal-list').innerHTML=state.journalRecords.length?state.journalRecords.map(row=>{
    const item=row.entry,brief=[item.breakfast,item.lunch,item.dinner].filter(Boolean).join(' · ');
    const activity=state.journalActivities.find(a=>a.id===item.activity_id);
    return `<button type="button" data-journal-day="${e(row.day)}"><b>${e(row.day)}</b><span>${e(brief||'未写三餐')}</span><small>${activity?`${e(activity.name)} ${e(item.activity_minutes)} 分钟`:'无运动记录'}${row.diet_score===null?'':` · 饮食演示分 ${e(row.diet_score)}`}</small></button>`;
  }).join(''):'<p class="hint">还没有逐日日志。填写左侧表单，从今天开始记录。</p>';
}
async function loadJournal(){
  if(!state.patientId)return;
  if(!state.journalLoaded){const catalog=await api('/catalog/exercises');state.journalActivities=catalog.activities;$('journal-activity').innerHTML='<option value="">今天未记录运动</option>'+catalog.activities.map(a=>`<option value="${e(a.id)}">${e(a.name)}</option>`).join('');state.journalLoaded=true;$('journal-date').value=localDate();$('journal-date').max=localDate();}
  state.journalRecords=await api(`/patients/${state.patientId}/journal-days?limit=180`);renderJournalList();await loadJournalDay($('journal-date').value);
}
function setJournalMode(mode){
  $('journal-personal').hidden=mode!=='personal';$('journal-case').hidden=mode!=='case';
  $('journal-personal-tab').className=`button ${mode==='personal'?'primary':'secondary'}`;
  $('journal-case-tab').className=`button ${mode==='case'?'primary':'secondary'}`;
}
function sparkline(values,min,max,label,color){
  const points=values.map((v,i)=>`${Math.round(i*640/(values.length-1))},${Math.round(96-(v-min)/(max-min)*82)}`).join(' ');
  return `<div class="case-plot"><b>${e(label)}</b><svg viewBox="0 0 640 110" role="img" aria-label="${e(label)}从案例第一天到最后一天的趋势" preserveAspectRatio="none"><line x1="0" y1="98" x2="640" y2="98" stroke="#dfe8dc"/><polyline points="${points}" fill="none" stroke="${color}" stroke-width="3" vector-effect="non-scaling-stroke"/></svg><span>1 月 → 6 月</span></div>`;
}
function renderCaseDay(index){
  const data=state.caseStudy,record=data.records[index];if(!record)return;
  $('case-day-range').value=index;$('case-day-label').textContent=`第 ${record.day_number} 天 · ${record.day}`;$('case-month').value=String(record.phase);
  $('case-day-detail').innerHTML=`<div><p class="eyebrow">${e(record.day)} · 第 ${e(record.day_number)} 天</p><h3>这一天的记录</h3><p>饮食习惯演示分 <strong>${e(record.diet_score)}</strong> · 食物热量粗估 <strong>约 ${e(record.energy_kcal)} kcal</strong></p><p>体重记录 <strong>${e(record.weight_kg)} kg</strong></p><p>运动：${record.activity_minutes?`${e(record.activity_name)} ${e(record.activity_minutes)} 分钟`:'休息日，没有记录运动'}</p><small>${e(record.note)}</small></div><div><p><b>早餐</b> ${e(record.breakfast)}</p><p><b>午餐</b> ${e(record.lunch)}</p><p><b>晚餐</b> ${e(record.dinner)}</p><p><b>加餐与饮品</b> ${e(record.snacks)}</p></div>`;
  document.querySelectorAll('[data-case-month]').forEach(button=>button.classList.toggle('active',Number(button.dataset.caseMonth)===record.phase));
}
async function loadCase(){
  if(!state.caseStudy)state.caseStudy=await api('/demo/half-year-case');
  const data=state.caseStudy,first=data.records[0],last=data.records.at(-1);
  $('case-notice').textContent=data.notice;
  const startWeek=data.records.slice(0,7).reduce((sum,r)=>sum+r.activity_minutes,0),endWeek=data.records.slice(-7).reduce((sum,r)=>sum+r.activity_minutes,0);
  $('case-metrics').innerHTML=`<div><strong>${e(data.days)}</strong><span>天逐日记录</span></div><div><strong>${e(first.weight_kg)} → ${e(last.weight_kg)}</strong><span>kg · 虚构体重记录</span></div><div><strong>${e(startWeek)} → ${e(endWeek)}</strong><span>分钟 · 首周与末周活动</span></div><div><strong>${e(first.diet_score)} → ${e(last.diet_score)}</strong><span>饮食习惯演示分</span></div>`;
  $('case-chart').innerHTML=sparkline(data.records.map(r=>r.weight_kg),75,83,'体重记录（kg）','#3d7f61')+sparkline(data.records.map(r=>r.diet_score),0,100,'饮食习惯演示分','#c28655');
  $('case-phases').innerHTML=data.phases.map((phase,i)=>`<button type="button" data-case-month="${i+1}"><b>${e(phase.month)} · ${e(phase.title)}</b><span>${e(phase.detail)}</span></button>`).join('');
  $('case-month').innerHTML=data.phases.map((phase,i)=>`<option value="${i+1}">${e(phase.month)} · ${e(phase.title)}</option>`).join('');
  $('case-day-range').max=data.records.length-1;renderCaseDay(0);
}
async function openNutrition(){await loadGuide();$('step-nutrition').disabled=false;showView('nutrition');showTab('guide');const day=$('diary-date').value||localDate();$('diary-date').value=day;await loadDiary(day);}
$('profile-form').addEventListener('submit',async event=>{
  event.preventDefault();$('save-profile').disabled=true;$('save-profile').textContent='正在保存并生成…';notify('');
  try{const payload=formToProfile();const profile=await api(state.patientId?`/patients/${state.patientId}/intake`:'/intake',{method:state.patientId?'PUT':'POST',body:JSON.stringify(payload)});state.patientId=profile.patient.id;state.profile=profile;localStorage.setItem('health-companion-profile-v2',state.patientId);fillProfile(profile);await openNutrition();}
  catch(error){notify(error.message,true);}finally{$('save-profile').disabled=false;$('save-profile').textContent='生成我的饮食指南 →';}
});
$('profile-form').addEventListener('input',updateSummary);
$('load-demo').addEventListener('click',()=>loadDemo());$('add-medication').addEventListener('click',()=>addMedication());
$('drug-search').addEventListener('input',renderDrugResults);
$('drug-results').addEventListener('click',event=>{const button=event.target.closest('[data-reference-drug]');if(!button)return;const drug=state.referenceDrugs.find(r=>r.key===button.dataset.referenceDrug);if(!drug)return;addMedication({drug_name:drug.name_zh,generic_name:drug.key});$('medication-list').lastElementChild.querySelector('[data-med="dose"]').focus();notify('已填入药名。请按实际处方补全剂量和时间；这不是用药推荐。');});
$('step-profile').addEventListener('click',()=>showView('profile'));$('edit-profile').addEventListener('click',()=>{showView('profile');notify('修改后请点击“生成我的饮食指南”保存。');});
$('step-nutrition').addEventListener('click',()=>showView('nutrition'));
$('tab-guide').addEventListener('click',()=>showTab('guide'));$('tab-diary').addEventListener('click',()=>showTab('diary'));$('go-diary').addEventListener('click',()=>{showTab('diary');$('diary-panel').scrollIntoView({behavior:'smooth',block:'start'});});
$('tab-journal').addEventListener('click',()=>{showTab('journal');setJournalMode('personal');loadJournal().catch(error=>notify(error.message,true));});
$('tab-query').addEventListener('click',()=>showTab('query'));
$('journal-personal-tab').addEventListener('click',()=>{setJournalMode('personal');loadJournal().catch(error=>notify(error.message,true));});
$('journal-case-tab').addEventListener('click',()=>{setJournalMode('case');loadCase().catch(error=>notify(error.message,true));});
$('journal-date').addEventListener('change',()=>{if($('journal-date').value)loadJournalDay($('journal-date').value).catch(error=>notify(error.message,true));});
$('journal-list').addEventListener('click',event=>{const button=event.target.closest('[data-journal-day]');if(!button)return;$('journal-date').value=button.dataset.journalDay;loadJournalDay(button.dataset.journalDay).catch(error=>notify(error.message,true));$('journal-form').scrollIntoView({behavior:'smooth',block:'start'});});
$('journal-form').addEventListener('submit',async event=>{
  event.preventDefault();if(!state.patientId)return;
  const day=$('journal-date').value;
  const entry={day,breakfast:$('journal-breakfast').value.trim(),lunch:$('journal-lunch').value.trim(),dinner:$('journal-dinner').value.trim(),snacks:$('journal-snacks').value.trim(),activity_id:$('journal-activity').value||null,activity_minutes:Number($('journal-minutes').value),weight_kg:$('journal-weight').value?Number($('journal-weight').value):null,notes:$('journal-notes').value.trim()};
  try{await api(`/patients/${state.patientId}/journal-days/${day}`,{method:'PUT',body:JSON.stringify(entry)});$('journal-status').textContent='已保存到本机。';state.journalRecords=await api(`/patients/${state.patientId}/journal-days?limit=180`);renderJournalList();}
  catch(error){notify(error.message,true);}
});
$('case-day-range').addEventListener('input',()=>{if(state.caseStudy)renderCaseDay(Number($('case-day-range').value));});
$('case-month').addEventListener('change',()=>{if(!state.caseStudy)return;const index=state.caseStudy.records.findIndex(r=>r.phase===Number($('case-month').value));if(index>=0)renderCaseDay(index);});
$('case-phases').addEventListener('click',event=>{const button=event.target.closest('[data-case-month]');if(!button||!state.caseStudy)return;const index=state.caseStudy.records.findIndex(r=>r.phase===Number(button.dataset.caseMonth));if(index>=0)renderCaseDay(index);});
$('example-poor').addEventListener('click',()=>exampleDiary(false));$('example-good').addEventListener('click',()=>exampleDiary(true));
$('meals').addEventListener('click',event=>{
  const button=event.target.closest('button[data-action]');if(!button)return;const section=button.closest('[data-meal]');const meal=state.diary.meals.find(m=>m.name===section.dataset.meal);
  if(button.dataset.action==='add'){meal.status='recorded';meal.items.push({food_id:'',servings:1,description:''});}
  if(button.dataset.action==='remove'){meal.items.splice(Number(button.closest('[data-index]').dataset.index),1);if(!meal.items.length)meal.status='unreported';}
  renderMeals();invalidateScore();
});
$('meals').addEventListener('change',event=>{
  const el=event.target,action=el.dataset.action;if(!action)return;const meal=state.diary.meals.find(m=>m.name===el.closest('[data-meal]').dataset.meal);
  if(action==='status'){
    if(el.value!=='recorded'&&meal.items.length&&!confirm('变更为未吃或未记录会清空这一餐尚未保存的食物，继续吗？')){el.value=meal.status;return;}
    meal.status=el.value;if(meal.status!=='recorded')meal.items=[];else if(!meal.items.length)meal.items.push({food_id:'',servings:1,description:''});renderMeals();
  }else if(action==='notes')meal.notes=el.value;
  else{const item=meal.items[Number(el.closest('[data-index]').dataset.index)];if(action==='food'){item.food_id=el.value;item.description='';renderMeals();}else if(action==='servings')item.servings=Number(el.value);else if(action==='description')item.description=el.value;}
  invalidateScore();
});
$('day-complete').addEventListener('change',()=>{state.diary.day_complete=$('day-complete').checked;invalidateScore();});
$('activity-level').addEventListener('change',()=>{state.diary.activity_level=$('activity-level').value;invalidateScore();});
$('diet-exercise').addEventListener('change',()=>{state.diary.exercise_activity_id=$('diet-exercise').value||null;if(!state.diary.exercise_activity_id){state.diary.exercise_minutes=0;$('diet-exercise-minutes').value='0';}renderDietExerciseNote();invalidateScore();});
$('diet-exercise-minutes').addEventListener('change',()=>{state.diary.exercise_minutes=Number($('diet-exercise-minutes').value);invalidateScore();});
$('diary-form').addEventListener('submit',async event=>{
  event.preventDefault();if(!state.patientId)return;$('save-diary').disabled=true;$('save-diary').textContent='正在保存与计算…';notify('');
  try{state.diary.day=$('diary-date').value;state.diary.day_complete=$('day-complete').checked;state.diary.activity_level=$('activity-level').value;state.diary.exercise_activity_id=$('diet-exercise').value||null;state.diary.exercise_minutes=Number($('diet-exercise-minutes').value);const saved=await api(`/patients/${state.patientId}/diet-days/${state.diary.day}`,{method:'PUT',body:JSON.stringify(state.diary)});state.diary=saved.diary;state.dirty=false;renderScore(saved.result);$('diary-status').textContent='已保存到本地。'+(saved.result.score===null?'记录尚不满足总评分条件，请查看右侧营养小计与说明。':'演示分与营养粗估已更新。');await loadHistory();if(innerWidth<700)$('score-card').scrollIntoView({behavior:'smooth',block:'start'});}
  catch(error){notify(error.message,true);}finally{$('save-diary').disabled=false;$('save-diary').textContent='保存饮食并估算 →';}
});
$('diary-date').addEventListener('change',()=>{
  const selected=$('diary-date').value;if(!selected)return;
  if(state.dirty&&!confirm('当前修改还未保存，确定切换日期吗？')){$('diary-date').value=state.diary.day;return;}
  loadDiary(selected).catch(error=>notify(error.message,true));
});
$('diary-history').addEventListener('click',event=>{const button=event.target.closest('[data-day]');if(button){if(state.dirty&&!confirm('当前修改还未保存，确定载入这一天吗？'))return;$('diary-date').value=button.dataset.day;loadDiary(button.dataset.day).catch(error=>notify(error.message,true));}});
window.addEventListener('hashchange',()=>showView(location.hash==='#nutrition'?'nutrition':'profile'));
async function init(){
  try{
    const [diseases,foods]=await Promise.all([api('/catalog/diseases'),api('/catalog/diet-foods')]);state.diseases=diseases;state.foods=foods.foods;
    const refs=await Promise.allSettled([api('/reference/sources'),api('/reference/drugs?limit=50'),api('/reference/foods?limit=50'),api('/reference/guidelines?limit=100'),api('/catalog/health-literacy'),api('/reference/health-topics?featured=true&limit=50')]);
    if(refs[0].status==='fulfilled')state.references=refs[0].value;
    if(refs[1].status==='fulfilled')state.referenceDrugs=refs[1].value.items;
    if(refs[2].status==='fulfilled')state.referenceFoods=Object.fromEntries(refs[2].value.items.map(r=>[r.key,r]));
    if(refs[3].status==='fulfilled')state.referenceGuidelines=refs[3].value.items;
    if(refs[4].status==='fulfilled')state.literacy=refs[4].value;
    if(refs[5].status==='fulfilled')state.featuredTopics=refs[5].value.items;
    renderDrugResults();renderReferenceSources();renderQueryDrugs();renderQueryFoods();renderQueryGuidelines();
    $('disease-options').innerHTML=Object.entries(diseases).filter(([code])=>!['hyperuricemia','gout'].includes(code)).map(([code,d])=>`<label class="disease-option"><input type="checkbox" name="disease" value="${e(code)}">${e(d.name)}</label>`).join('');
    $('diary-date').value=localDate();$('diary-date').max=localDate();
    const savedId=Number(localStorage.getItem('health-companion-profile-v2'));
    if(savedId>0){try{const profile=await api(`/patients/${savedId}/intake`);state.patientId=savedId;state.profile=profile;fillProfile(profile);$('demo-note').hidden=true;await loadGuide();$('step-nutrition').disabled=false;await loadDiary(localDate());showView(location.hash==='#nutrition'?'nutrition':'profile');}catch(error){if(error.status===404)loadDemo(false);else throw error;}}
    else loadDemo(false);
    $('save-profile').disabled=false;
  }catch(error){notify('连接失败：'+error.message+'。请确认本地服务已启动，然后刷新页面。',true);}
}
init();
