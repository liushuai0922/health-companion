'use strict';
function guidanceNode(tag, className, content){
  const node=document.createElement(tag);
  if(className)node.className=className;
  if(content!==undefined)node.textContent=content;
  return node;
}
function guidanceSource(parent, url, label){
  if(typeof url!=='string'||!url.startsWith('https://'))return;
  const link=guidanceNode('a','',label);
  link.href=url;link.target='_blank';link.rel='noopener';
  parent.append(link);
}
function renderIntegratedGuidance(guide, conditions){
  const combined=guide.combined_guidance;
  const box=document.getElementById('combined-guidance');
  box.hidden=!conditions.length;
  box.replaceChildren();
  if(!box.hidden){
    box.append(guidanceNode('p','eyebrow','把多项健康目标放在一起'));
    box.append(guidanceNode('h2','','综合饮食建议'));
    box.append(guidanceNode('p','muted',combined.scope));
    box.append(guidanceNode('h3','combined-subtitle','一餐怎么搭配'));
    box.append(guidanceNode('p','combined-meal',combined.meal_approach));
    const groups=[['共同重点',combined.common_goals],['各疾病还需关注',combined.specific_goals],['需要个别确认',combined.review_goals]];
    for(const [title,goals] of groups){
      if(!goals.length)continue;
      box.append(guidanceNode('h3','combined-subtitle',title));
      const list=guidanceNode('div','combined-list');
      for(const goal of goals){
        const article=guidanceNode('article','combined-goal');
        article.append(guidanceNode('h3','',goal.title));
        article.append(guidanceNode('p','',goal.action));
        const source=guidanceNode('small','', '适用：'+goal.diseases.join('、')+'  ');
        for(const url of goal.source_urls)guidanceSource(source,url,'来源 ↗');
        article.append(source);list.append(article);
      }
      box.append(list);
    }
    if(combined.combination_notes.length){
      const notes=guidanceNode('div','combined-notes');
      notes.append(guidanceNode('h3','','一起考虑时'));
      for(const note of combined.combination_notes)notes.append(guidanceNode('p','',note));
      box.append(notes);
    }
  }
  const details=document.getElementById('disease-details');
  details.hidden=!guide.disease_guides.length;
  details.replaceChildren();
  if(details.hidden)return;
  const heading=guidanceNode('div','section-title');
  heading.append(guidanceNode('h2','','按疾病查看详细说明'));
  heading.append(guidanceNode('span','muted small','点击来源可核对原文'));
  details.append(heading);
  for(const disease of guide.disease_guides){
    const detail=guidanceNode('details','card disease-detail');
    detail.append(guidanceNode('summary','',disease.title+'　展开说明 ↓'));
    detail.append(guidanceNode('p','muted',disease.scope));
    const sections=guidanceNode('div','gout-sections');
    for(const section of disease.sections){
      const article=guidanceNode('article','');
      article.append(guidanceNode('h3','',section.title));
      article.append(guidanceNode('p','',section.text));
      article.append(guidanceNode('small','',section.examples));
      sections.append(article);
    }
    detail.append(sections);
    const sources=guidanceNode('p','source','依据：');
    guidanceSource(sources,disease.source_url,disease.source_title+' ↗');
    if(disease.extra_source_url)guidanceSource(sources,disease.extra_source_url,'官方问答 ↗');
    detail.append(sources);details.append(detail);
  }
}
