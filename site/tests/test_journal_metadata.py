"""Independent metadata enrichment contracts; no real network or paid services."""
import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import journal_metadata as m

NOW = datetime(2026, 10, 26, 6, tzinfo=timezone.utc)
TITLE = 'Machine learning predicts alloy properties'
ABSTRACT = 'We use machine learning to predict mechanical properties of alloys and design materials with validated experimental performance. ' * 3
DOI = '10.1038/s41563-026-test'
REGISTRY = [{'id':'nature-materials','title':'Nature Materials','issns':['1476-4660'],'publisher':'Springer Nature'}]


def record(**kw):
    return {'title':TITLE,'doi':DOI,'url':'https://doi.org/'+DOI,'abstract':'','first_seen':NOW.isoformat(),
            'item_id':'original-id','journal_relevance':{'status':'pending'},**kw}


def state(rows=None):
    return {'version':1,'journals':{'nature-materials':{'records':rows or {DOI:record()}}}}


def cfg(**kw):
    return {'journals':REGISTRY,'metadata':{**m.DEFAULTS,**kw}}


def missing_crossref(doi,title,budget):
    budget.reserve()
    return None,None


def missing_openalex(candidates,budget):
    budget.reserve()
    return {}


def response(data=b'<html/>',kind='text/html',status=200,location=None):
    r=Mock(status_code=status,headers={'Content-Type':kind,**({'Location':location} if location else {})})
    r.__enter__=Mock(return_value=r);r.__exit__=Mock(return_value=False)
    r.iter_content.return_value=[data]
    return r


def session_for(responses):
    session=Mock();session.__enter__=Mock(return_value=session);session.__exit__=Mock(return_value=False)
    session.get.side_effect=responses
    return session


class JournalMetadataTests(unittest.TestCase):
    def test_crossref_enrichment_and_identity_unchanged(self):
        s=state();original=copy.deepcopy(s['journals']['nature-materials']['records'][DOI])
        def cr(doi,title,budget):budget.reserve();return ABSTRACT,None
        with patch.object(m,'_crossref',side_effect=cr),patch.object(m,'_openalex') as oa,patch.object(m,'_request') as pub:
            receipt=m.enrich_candidates(s,cfg(),NOW)
        row=s['journals']['nature-materials']['records'][DOI]
        self.assertEqual((receipt['attempted'],receipt['improved'],receipt['requests']),(1,1,1))
        self.assertEqual(row['abstract'],ABSTRACT.strip());self.assertEqual(row['metadata_provider'],'crossref')
        self.assertIsNone(row['metadata_next_attempt_at']);oa.assert_not_called();pub.assert_not_called()
        for k in ('item_id','first_seen','doi','url','journal_relevance'):self.assertEqual(row[k],original[k])

    def test_crossref_exact_doi_required(self):
        payload=json.dumps({'message':{'DOI':'10.1038/wrong','abstract':ABSTRACT}}).encode()
        with patch.object(m,'_request',return_value=(payload,'api')),self.assertRaises(m.MetadataUnavailable):m._crossref(DOI,TITLE,m.Budget({},20,NOW))

    def test_openalex_batch_uses_exact_dois_and_reconstructs(self):
        index={}
        for n,word in enumerate(ABSTRACT.split()):index.setdefault(word,[]).append(n)
        payload={'results':[{'doi':'https://doi.org/'+DOI,'abstract_inverted_index':index},
                            {'doi':'10.1038/unrequested','abstract_inverted_index':index}]}
        with patch.object(m,'_request',return_value=(json.dumps(payload).encode(),'api')) as request:
            result=m._openalex([{'doi':DOI,'row':record()}],m.Budget({},20,NOW))
        self.assertEqual(set(result),{DOI});self.assertEqual(result[DOI][0],ABSTRACT.strip())
        self.assertIn('https://doi.org/'+DOI,request.call_args.kwargs['params']['filter'])

    def test_openalex_single_batch_improves_multiple_candidates(self):
        rows={f'10.1038/test{i}':record(doi=f'10.1038/test{i}') for i in range(3)};s=state(rows)
        def oa(candidates,budget):budget.reserve();return {c['doi']:(ABSTRACT,None) for c in candidates}
        with patch.object(m,'_crossref',side_effect=missing_crossref),patch.object(m,'_openalex',side_effect=oa) as batch,patch.object(m,'_request') as pub:
            receipt=m.enrich_candidates(s,cfg(),NOW)
        self.assertEqual((receipt['improved'],receipt['requests']),(3,4));self.assertEqual(batch.call_count,1);pub.assert_not_called()

    def test_publisher_requires_exact_doi_and_abstract_not_title(self):
        good=f'<html><meta name="citation_doi" content="{DOI}"><meta property="og:description" content="{ABSTRACT}"></html>'.encode()
        self.assertEqual(m.publisher_abstract(good,DOI,TITLE),ABSTRACT.strip())
        for data in [good.replace(DOI.encode(),b'10.1038/wrong'),good.replace(b'citation_doi',b'unknown_doi'),
                     f'<meta name="citation_doi" content="{DOI}"><meta name="citation_abstract" content="{TITLE} Nature Materials 2026">'.encode()]:
            with self.subTest(data=data[:60]),self.assertRaises(m.MetadataUnavailable):m.publisher_abstract(data,DOI,TITLE)

    def test_conflicting_doi_rejected(self):
        data=f'<meta name="citation_doi" content="{DOI}"><meta name="dc.identifier.doi" content="10.1038/wrong"><meta name="citation_abstract" content="{ABSTRACT}">'.encode()
        with self.assertRaises(m.MetadataUnavailable):m.publisher_abstract(data,DOI,TITLE)

    def test_jsonld_and_open_nature_abstract(self):
        node={'@type':'ScholarlyArticle','identifier':{'@type':'PropertyValue','propertyID':'DOI','value':DOI},'abstract':ABSTRACT}
        data=('<script type="application/ld+json">'+json.dumps({'@graph':[node]})+'</script>').encode()
        self.assertEqual(m.publisher_abstract(data,DOI,TITLE),ABSTRACT.strip())
        data=f'<meta name="citation_doi" content="{DOI}"><section data-title="Abstract"><div class="c-article-section__content"><p>{ABSTRACT}</p></div></section><section><p>OTHER FULL BODY</p></section>'.encode()
        self.assertEqual(m.publisher_abstract(data,DOI,TITLE),ABSTRACT.strip())
        self.assertNotIn('OTHER FULL BODY',m.publisher_abstract(data,DOI,TITLE))

    def test_canonical_doi_identity_and_challenge_rejected(self):
        data=f'<link rel="canonical" href="https://doi.org/{DOI}"><meta name="citation_abstract" content="{ABSTRACT}">'.encode()
        self.assertEqual(m.publisher_abstract(data,DOI,TITLE),ABSTRACT.strip())
        for text in ['Just a moment, verify you are human. '*10,'Sign in to access this article. '*10,'Nature Materials is a multidisciplinary journal. '*10]:
            self.assertIsNone(m.abstract_text(text,TITLE))

    def test_abstract_cap_and_invalid_api_types(self):
        self.assertEqual(len(m.abstract_text('Material science data. '*600)),6000)
        for value in [None,{},[],23,ABSTRACT[:50]]:self.assertIsNone(m.abstract_text(value,TITLE))
        for index in [{'A':[0],'B':[0]},{'A':[-1]},{'A':[True]},{'A':[20001]},{'A':'not-list'}]:self.assertIsNone(m._inverted_abstract(index))

    def test_hard_twenty_request_cap_and_daily_persistence(self):
        rows={f'10.1038/test{i}':record(doi=f'10.1038/test{i}') for i in range(30)};s=state(rows)
        with patch.object(m,'_crossref',side_effect=missing_crossref),patch.object(m,'_openalex',side_effect=missing_openalex) as oa,patch.object(m,'_request') as pub:
            receipt=m.enrich_candidates(s,cfg(max_candidates=20),NOW)
            again=m.enrich_candidates(s,cfg(max_candidates=20),NOW)
        self.assertEqual(receipt['requests'],20);self.assertEqual(again['requests'],0)
        self.assertEqual(s['metadata_budget']['requests'],20);oa.assert_not_called();pub.assert_not_called()
        self.assertEqual(receipt['skip_reasons']['candidate_limit'],10)

    def test_redirect_consumes_budget_and_private_redirect_never_followed(self):
        budget=m.Budget({},20,NOW)
        session=session_for([response(status=302,location='https://www.nature.com/articles/test'),response(data=b'public')])
        with patch.object(m.requests,'Session',return_value=session):data,url=m._request('https://nature.com/articles/test',budget)
        self.assertEqual(budget.used,2);self.assertEqual(data,b'public');self.assertFalse(session.trust_env)
        session=session_for([response(status=302,location='https://127.0.0.1/private')]);budget=m.Budget({},20,NOW)
        with patch.object(m.requests,'Session',return_value=session),self.assertRaises(m.MetadataUnavailable):m._request('https://nature.com/articles/test',budget)
        self.assertEqual(session.get.call_count,1)

    def test_timeout_and_size_are_bounded_no_hidden_retry(self):
        session=session_for([response(data=b'x'*2_000_001)])
        with patch.object(m.requests,'Session',return_value=session),self.assertRaises(m.MetadataUnavailable):m._request('https://nature.com/articles/test',m.Budget({},20,NOW))
        self.assertEqual(session.get.call_count,1);self.assertEqual(session.get.call_args.kwargs['timeout'],(5,12))
        self.assertFalse(session.get.call_args.kwargs['allow_redirects'])

    def test_priority_and_no_low_signal_or_existing_abstract_calls(self):
        s=state({'weak':record(title='Atomistic mechanism discovery',doi='10.1038/weak'),
                 'strong':record(), 'unrelated':record(title='New methods for microscopy',doi='10.1038/unrelated'),
                 'existing':record(doi='10.1038/existing',abstract=ABSTRACT)})
        with patch.object(m,'_crossref',side_effect=missing_crossref) as cr:
            receipt=m.enrich_candidates(s,cfg(max_requests=1,max_candidates=1),NOW)
        self.assertEqual(cr.call_args.args[0],DOI);self.assertEqual(receipt['attempted'],1)
        self.assertEqual(receipt['skip_reasons']['has_abstract'],1)
        self.assertEqual(receipt['skip_reasons']['no_materials_ai_title_hint'],1)

    def test_failure_backoff_one_three_seven_days_and_no_raw_error(self):
        s=state()
        dates=[NOW,NOW+timedelta(days=1),NOW+timedelta(days=4)]
        for attempt,now in enumerate(dates,1):
            with patch.object(m,'_crossref',side_effect=missing_crossref),patch.object(m,'_openalex',side_effect=missing_openalex),patch.object(m,'_request',side_effect=m.MetadataUnavailable('PRIVATE_ERROR')):
                receipt=m.enrich_candidates(s,cfg(),now)
            row=s['journals']['nature-materials']['records'][DOI]
            self.assertEqual(row['metadata_attempts'],attempt)
            self.assertEqual(datetime.fromisoformat(row['metadata_next_attempt_at']),now+timedelta(days=(1,3,7)[attempt-1]))
            self.assertNotIn('PRIVATE_ERROR',json.dumps(s));self.assertEqual(receipt['failed'],1)
            with patch.object(m,'_crossref') as cr:m.enrich_candidates(s,cfg(),now+timedelta(hours=1));cr.assert_not_called()

    def test_disabled_or_zero_no_network(self):
        for settings in [cfg(enabled=False),cfg(max_requests=0),cfg(max_candidates=0)]:
            with self.subTest(settings=settings),patch.object(m,'_request') as request:
                receipt=m.enrich_candidates(state(),settings,NOW)
            self.assertEqual(receipt['requests'],0);request.assert_not_called()

    def test_settings_reject_unbounded_and_bad_ledger(self):
        for change in [{'max_requests':21},{'max_candidates':21},{'enabled':'yes'},{'max_requests':True},{'api_key':'secret'}]:
            with self.subTest(change=change),self.assertRaises(ValueError):m.enrich_candidates(state(),cfg(**change),NOW)
        for ledger in [{'date':'2027-01-01','requests':1},{'date':'2026-10-26','requests':-1}]:
            with self.subTest(ledger=ledger),self.assertRaises(ValueError):m.Budget({**state(),'metadata_budget':ledger},20,NOW)

    def test_corrupt_ledger_fail_closed_without_blocking_archive(self):
        invalid = [None, [], {}, 'not-a-mapping', {'date':'0000-bad','requests':0},
                   {'date':'2026-10-99','requests':0}, {'date':'20261026','requests':0},
                   {'date':'2026-10-27','requests':0}, {'date':None,'requests':0},
                   {'date':123,'requests':0}, {'date':'2026-10-26','requests':True},
                   {'date':'2026-10-26','requests':None}, {'date':'2026-10-26','requests':[]},
                   {'date':'2026-10-26','requests':-1}, {'date':'2026-10-26'},
                   {'requests':0}]
        for ledger in invalid:
            with self.subTest(ledger=ledger):
                s={**state(),'metadata_budget':copy.deepcopy(ledger)};original=copy.deepcopy(s)
                with patch.object(m,'_request') as request:
                    receipt=m.enrich_candidates(s,cfg(),NOW)
                self.assertEqual(receipt['status'],'budget_invalid')
                self.assertEqual(receipt['requests'],0);request.assert_not_called()
                self.assertEqual(s,original)
                with self.assertRaises(ValueError):m.Budget(s,20,NOW)

    def test_publisher_fallback_after_crossref_openalex(self):
        s=state();data=f'<meta name="citation_doi" content="{DOI}"><meta name="citation_abstract" content="{ABSTRACT}">'.encode()
        def fetch(url,budget,**kw):budget.reserve();return data,url
        with patch.object(m,'_crossref',side_effect=missing_crossref),patch.object(m,'_openalex',side_effect=missing_openalex),patch.object(m,'_request',side_effect=fetch) as request:
            receipt=m.enrich_candidates(s,cfg(),NOW)
        self.assertEqual(receipt['requests'],3);self.assertEqual(receipt['providers']['publisher'],1)
        self.assertEqual(request.call_args.args[0],'https://www.nature.com/articles/s41563-026-test')

    def test_private_urls_and_credentials_never_used(self):
        for url in ['http://www.nature.com/a','https://localhost/a','https://127.0.0.1/a','https://www.nature.com.evil/a','https://user:secret@www.nature.com/a','https://www.nature.com:444/a']:
            with self.subTest(url=url),self.assertRaises(m.MetadataUnavailable):m._safe_url(url)

if __name__=='__main__':unittest.main()
