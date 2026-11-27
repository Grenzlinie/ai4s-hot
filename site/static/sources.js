'use strict';
(() => {
  const cards = [...document.querySelectorAll('.source-card')];
  const sections = [...document.querySelectorAll('[data-section]')];
  const query = document.getElementById('source-query');
  const count = document.getElementById('source-count');
  let group = 'all';
  function filter() {
    const text = query.value.trim().toLocaleLowerCase();
    for (const card of cards) card.hidden = (group !== 'all' && card.dataset.group !== group) || !card.dataset.search.toLocaleLowerCase().includes(text);
    for (const section of sections) section.hidden = ![...section.querySelectorAll('.source-card')].some(card => !card.hidden);
    const shown = cards.filter(card => !card.hidden).length;
    count.textContent = `${shown} / ${cards.length} 个官方入口`;
    document.getElementById('source-empty').hidden = shown !== 0;
    for (const button of document.querySelectorAll('[data-show]')) button.setAttribute('aria-pressed', String(button.dataset.show === group));
  }
  query.addEventListener('input', filter);
  for (const button of document.querySelectorAll('[data-show]')) button.addEventListener('click', () => { group = button.dataset.show; filter(); });
  filter();
  const note = document.getElementById('source-archive-note');
  fetch('./data/source-health.json', { cache: 'no-cache' }).then(response => {
    if (!response.ok) throw new Error('archive unavailable');
    return response.json();
  }).then(data => {
    const health = new Map((Array.isArray(data.sources) ? data.sources : []).map(source => [source.id, source]));
    const labels = {ok:'最近采集成功',partial:'最近采集部分完成',error:'最近采集未完成',unconfigured:'站内尚未配置'};
    for (const card of cards) {
      const source = health.get(card.dataset.sourceId), status = card.querySelector('.source-status');
      status.dataset.status = source?.status || 'unknown';
      status.textContent = source ? (labels[source.status] || '站内状态待确认') : '等待站内首次采集';
      if (source?.last_attempt && Number.isFinite(Date.parse(source.last_attempt))) status.title = '最近尝试：' + new Date(source.last_attempt).toLocaleString('zh-CN', {timeZone:'Asia/Shanghai'});
    }
    const generated = new Date(data.generated_at);
    note.textContent = Number.isFinite(generated.getTime()) ? `站内归档更新于 ${generated.toLocaleString('zh-CN', {timeZone:'Asia/Shanghai'})}（北京时间）。官网内容可能更新得更早。` : '官网提供完整更新；站内收录按采集规则筛选。';
  }).catch(() => {
    note.textContent = '暂时无法读取站内更新状态，仍可直接使用下方官网入口。';
    for (const status of document.querySelectorAll('.source-status')) status.textContent = '站内状态暂未读取';
  });
})();
