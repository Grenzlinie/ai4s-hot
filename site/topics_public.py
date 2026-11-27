"""Deterministic public broad categories; never scientific similarity evidence.

Keep supported fine labels unchanged. Public wording can justify a broad field;
otherwise a general category describes the archive record without guessing a
scientific specialty. This migration needs neither secrets nor a reference corpus.
"""
from topics_v1 import topic_ancestors
from topics_decision import content_facets

METHOD = 'public_coarse_v1'
ROOT = 'public:content'
GENERAL = 'public:area:general'


def complete_public_topics(payload):
    from landscape import AREAS, paper_area, recovery_area
    taxonomy = payload.setdefault('taxonomy', {})
    topics = taxonomy.setdefault('topics', [])
    categories = [(ROOT, '公开内容分类', None)]
    categories += [('public:area:' + key, label, ROOT) for key, label, _ in AREAS]
    categories += [(GENERAL, '综合研究', ROOT),
                   ('public:kind:model_release', '模型发布', ROOT),
                   ('public:kind:engineering_update', '工程与工具', ROOT),
                   ('public:kind:organization_policy', '机构动态', ROOT),
                   ('public:kind:general_update', '通用 AI 与应用动态', ROOT)]
    by_id = {t['id']: t for t in topics}
    for id_, name, parent in categories:
        row = {'id': id_, 'name': name, 'path': ('公开内容分类 / ' if parent else '') + name,
               'parent_id': parent, 'facet': ROOT, 'active': True}
        if id_ in by_id:
            by_id[id_].update(row)
            by_id[id_].pop('retired', None)
        else:
            topics.append(row); by_id[id_] = row
    migrated = 0
    for item in payload.get('items', []):
        # Collection synchronization may retire website-owned IDs temporarily.
        # Their coarse receipts are regenerated, never historical fine evidence.
        if 'topic_history' in item:
            item['topic_history'] = [l for l in item['topic_history']
                                     if not l.get('id', '').startswith('public:')]
        scope, kind, domains = content_facets(item)
        item.setdefault('topic_scope', scope)
        item.setdefault('content_kind', kind)
        item.setdefault('domain_facets', domains)
        labels = item.get('topic_labels') or []
        active = [l for l in labels if l.get('id') in by_id and by_id[l['id']].get('active', True)
                  and not by_id[l['id']].get('retired') and l.get('method') != METHOD]
        # V1 labels without receipts are still real existing classifications.
        legacy = [id_ for id_ in item.get('topic_leaf_ids', []) if id_ in by_id
                  and by_id[id_].get('active', True) and not by_id[id_].get('retired')
                  and not id_.startswith('public:')]
        if active or (payload.get('schema_version') == 1 and legacy):
            continue
        area = paper_area(item.get('title', ''), item.get('excerpt', ''))
        if area == 'other':
            area = recovery_area({k: item.get(k, '') for k in ('title', 'excerpt')}, {})
        if item.get('topic_scope') == 'unknown' and item.get('type') != 'paper' and area == 'other':
            category = 'public:kind:general_update'
            reason = '公开内容是 AI 产品、应用或行业进展，尚不足以推断具体科学研究领域；按通用 AI 与应用动态归类。'
        elif item.get('topic_scope') == 'non_research':
            category = 'public:kind:' + item['content_kind'].removeprefix('web:')
            if category not in by_id: category = 'public:kind:engineering_update'
            reason = '依据公开内容的类型归入此宽类；不据此推断科学研究主题。'
        else:
            category = GENERAL if area == 'other' else 'public:area:' + area
            reason = ('现有公开标题与摘要不足以确定具体研究领域，归入综合研究；未推断细分类。'
                      if area == 'other' else '公开标题或摘要出现此领域的明确术语，仅作领域宽分类；不推断具体体系或研究方法。')
        retired = [l for l in labels if l.get('id') in by_id and (not by_id[l['id']].get('active', True) or by_id[l['id']].get('retired'))]
        if retired:
            history = {l['id']: l for l in item.get('topic_history', [])}
            history.update({l['id']: l for l in retired})
            item['topic_history'] = [history[k] for k in sorted(history)]
        row = {'id': category, 'facet': ROOT, 'method': METHOD, 'score': None,
               'confidence': 'low', 'status': 'broad_only', 'public_reason': reason}
        item.update(topic_labels=[row], topic_leaf_ids=[category],
                    topic_ids=topic_ancestors([category], topics), topic_status='broad_only',
                    topic_method=METHOD)
        migrated += 1
    receipt = taxonomy.get('classification')
    if isinstance(receipt, dict):
        receipt['unclassified'] = sum(not p.get('topic_leaf_ids') for p in payload.get('items', []))
    return {'items': len(payload.get('items', [])), 'broad_categories': migrated,
            'unclassified': sum(not p.get('topic_leaf_ids') for p in payload.get('items', []))}
