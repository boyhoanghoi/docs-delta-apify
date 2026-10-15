import asyncio
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch, AsyncMock
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from docsdelta.config import RunConfig, validate_snapshot
from docsdelta.extract import extract_document, chunk_markdown, digest
from docsdelta.pipeline import run_pipeline, compare_document, snapshot_entry
from docsdelta.transport import Page, FetchError, validate_url, public_ip, PublicResolver
from docsdelta.output import pages_csv

URL = "https://docs.python.org/3/test.html"
HTML = '<html><head><title>Guide</title></head><body><nav>old menu</nav><main><h1>Guide</h1><p>Install the package and configure your environment to process documents safely.</p><h2>Usage</h2><p>Call the public function with your project settings.</p><pre><code class="language-python">print("hello")\n</code></pre><ul><li>First item</li><li>Second item</li></ul><a href="next.html">Next</a></main><script>noise()</script></body></html>'


class FakeClient:
    mapping = {}
    requests = 0
    def __init__(self, config): self.requests = 0
    async def __aenter__(self): return self
    async def __aexit__(self, *args): pass
    async def fetch(self, url, **kwargs):
        self.requests += 1
        result = self.mapping.get(url, FetchError("http_error", "Missing fixture", 404))
        if isinstance(result, Exception): raise result
        return result


class ExtractionTests(unittest.TestCase):
    def test_clean_markdown_and_stable_hash(self):
        config = RunConfig()
        a = extract_document(HTML, URL, config)
        b = extract_document(HTML.replace('old menu','new menu').replace('noise()','other()'), URL, config)
        self.assertEqual(a['contentHash'], b['contentHash'])
        self.assertIn('# Guide', a['markdown']); self.assertIn('```python', a['markdown'])
        self.assertIn('- First item', a['markdown']); self.assertNotIn('old menu',a['markdown'])
        self.assertIn('[Next](https://docs.python.org/3/next.html)',a['markdown'])

    def test_malformed_links_do_not_destroy_content(self):
        html = HTML.replace('<head>','<head><link rel="canonical" href="http://[bad">').replace('href="next.html"','href="http://[bad"')
        row = extract_document(html, URL, RunConfig())
        self.assertIn('Next', row['markdown']); self.assertIsNone(row['canonicalUrl'])

    def test_redirect_relative_links_use_final_url(self):
        row = extract_document(HTML, URL, RunConfig(), base_url='https://docs.python.org/v2/intro/')
        self.assertIn('https://docs.python.org/v2/intro/next.html',row['markdown'])
        self.assertTrue(all(c['sourceUrl']==URL for c in row['chunks']))

    def test_chunks_bounded_and_stable(self):
        text = '# One\n\n' + ('long documentation paragraph ' * 60)
        chunks = chunk_markdown(text,URL,200)
        self.assertTrue(all(len(c['text'])<=200 for c in chunks)); self.assertGreater(len(chunks),2)
        self.assertEqual(chunks,chunk_markdown(text,URL,200)); self.assertEqual(len({c['id'] for c in chunks}),len(chunks))

    def test_diff_and_tombstones(self):
        a = extract_document(HTML,URL,RunConfig())
        b = extract_document(HTML.replace('Call the public function','Invoke the changed function'),URL,RunConfig())
        result = compare_document(b,snapshot_entry(a))
        self.assertEqual(result['status'],'UPDATED'); self.assertIn('-Call',result['diff'])
        self.assertTrue(result['removedChunkIds']); self.assertTrue(result['addedChunkIds'])
        self.assertEqual(compare_document(a,snapshot_entry(a))['status'],'UNCHANGED')

    def test_chunk_setting_changes_count_as_updates(self):
        html = HTML.replace('Call the public function', 'Long documentation content. '*30 + 'Call the public function')
        a = extract_document(html,URL,RunConfig(chunk_size=1800))
        b = extract_document(html,URL,RunConfig(chunk_size=200))
        self.assertEqual(a['contentHash'],b['contentHash']); self.assertEqual(compare_document(b,snapshot_entry(a))['status'],'UPDATED')

    def test_invalid_selector_and_snapshot_hash(self):
        with self.assertRaises(ValueError): RunConfig.from_dict({'contentCssSelector':'['})
        with self.assertRaises(ValueError): validate_snapshot({'version':1,'pages':{URL:{'markdown':'hello','contentHash':'fake','chunks':[]}}})
        with self.assertRaises(ValueError): validate_snapshot({'version':1,'pages':{},'oversized':'x'*(5*1024*1024)})

    def test_empty_missing_selector_and_limits(self):
        self.assertEqual(extract_document('<main>Enable JavaScript to continue loading this website.</main>',URL,RunConfig())['skipReason'],'insufficient_content')
        self.assertEqual(extract_document(HTML,URL,RunConfig(content_css_selector='.missing'))['skipReason'],'content_selector_not_found')
        self.assertEqual(extract_document('<main>'+'word '*1000+'</main>',URL,RunConfig(max_text_chars=1000))['skipReason'],'content_truncated')

    def test_csv_formula_safety(self):
        doc=extract_document(HTML,URL,RunConfig()); row={'url':URL,**doc,**compare_document(doc,None),'title':'=HYPERLINK("bad")'}
        self.assertIn("'=HYPERLINK",pages_csv([row]))

    def test_long_diff_lines_are_marked_and_keep_change_tail(self):
        old='A'*2500+' OLD'; new='A'*2500+' NEW'
        before={'markdown':old,'contentHash':digest(old),'chunks':chunk_markdown(old,URL)}
        after={'markdown':new,'contentHash':digest(new),'chunks':chunk_markdown(new,URL)}
        result=compare_document(after,before)
        self.assertTrue(result['diffTruncated']);self.assertIn('OLD',result['diff']);self.assertIn('NEW',result['diff'])


class PipelineTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self): FakeClient.mapping={URL:Page(URL,HTML,200,'text/html')}

    async def test_snapshot_roundtrip_and_new(self):
        report=await run_pipeline(RunConfig(urls=[URL]),client_factory=FakeClient)
        self.assertEqual(report['results'][0]['status'],'NEW'); self.assertEqual(validate_snapshot(report['snapshot']),report['snapshot'])

    async def test_unchanged_filter_never_calls_paid_save(self):
        baseline=(await run_pipeline(RunConfig(urls=[URL]),client_factory=FakeClient))['snapshot']
        calls=[]
        async def save(row): calls.append(row); return True
        report=await run_pipeline(RunConfig(urls=[URL],previous_snapshot=baseline,changed_only=True),save,client_factory=FakeClient)
        self.assertEqual(calls,[]);self.assertEqual(report['results'],[]);self.assertEqual(report['snapshot'],baseline)

    async def test_failed_truncated_and_out_of_scope_preserve_baseline(self):
        baseline=(await run_pipeline(RunConfig(urls=[URL]),client_factory=FakeClient))['snapshot']
        original=copy.deepcopy(baseline)
        for fixture in [FetchError('blocked','blocked',403),Page(URL,'<main>'+'huge '*1000+'</main>',200,'text/html')]:
            FakeClient.mapping[URL]=fixture
            report=await run_pipeline(RunConfig(urls=[URL],previous_snapshot=baseline,max_text_chars=1000),client_factory=FakeClient)
            self.assertEqual(report['results'],[]);self.assertEqual(report['snapshot'],original)
        self.assertEqual(baseline,original)
        self.assertTrue(report['summary']['cannotInferDeletions'])

    async def test_unsaved_result_does_not_advance_snapshot(self):
        async def refuse(row): return False
        result=await run_pipeline(RunConfig(urls=[URL]),refuse,client_factory=FakeClient)
        self.assertEqual(result['results'],[]);self.assertEqual(result['snapshot']['pages'],{})

    async def test_snapshot_capacity_stops_before_callback(self):
        calls=[]
        async def save(row):calls.append(row);return True
        with patch('docsdelta.pipeline.MAX_SNAPSHOT_BYTES',20):
            report=await run_pipeline(RunConfig(urls=[URL]),save,client_factory=FakeClient)
        self.assertEqual(calls,[]);self.assertEqual(report['snapshot']['pages'],{})
        self.assertEqual(report['diagnostics'][0]['status'],'snapshot_capacity')

    async def test_exact_utf8_snapshot_bound_roundtrip(self):
        url=URL+'?lang=việt'
        FakeClient.mapping[url]=Page(url,HTML.replace('Guide','Hướng dẫn'),200,'text/html')
        first=await run_pipeline(RunConfig(urls=[url]),client_factory=FakeClient)
        size=len(json.dumps(first['snapshot'],ensure_ascii=False).encode('utf-8'))
        with patch('docsdelta.pipeline.MAX_SNAPSHOT_BYTES',size):
            exact=await run_pipeline(RunConfig(urls=[url]),client_factory=FakeClient)
        self.assertEqual(len(exact['results']),1);self.assertEqual(validate_snapshot(exact['snapshot']),exact['snapshot'])
        with patch('docsdelta.pipeline.MAX_SNAPSHOT_BYTES',size-1):
            small=await run_pipeline(RunConfig(urls=[url]),client_factory=FakeClient)
        self.assertEqual(small['results'],[]);self.assertEqual(small['snapshot']['pages'],{})

    async def test_aggregate_content_limit_prevents_saving(self):
        calls=[]
        async def save(row):calls.append(row);return True
        with patch('docsdelta.pipeline.MAX_RUN_CHARS',10):
            report=await run_pipeline(RunConfig(urls=[URL]),save,client_factory=FakeClient)
        self.assertEqual(calls,[]);self.assertEqual(report['diagnostics'][0]['status'],'run_content_limit')

    async def test_bounded_same_site_sitemap(self):
        sitemap='https://docs.python.org/sitemap.xml'
        FakeClient.mapping[sitemap]=Page(sitemap,f'<urlset><url><loc>{URL}</loc></url><url><loc>https://other.com/docs</loc></url></urlset>',200,'application/xml')
        report=await run_pipeline(RunConfig(urls=[],sitemap_urls=[sitemap],max_pages=1),client_factory=FakeClient)
        self.assertEqual(len(report['results']),1);self.assertEqual(report['summary']['attemptedPages'],1)


class TransportTests(unittest.TestCase):
    def test_private_and_legacy_targets_rejected(self):
        for url in ['http://127.0.0.1','http://169.254.169.254/','http://[::1]/','file:///etc/passwd','https://user:pass@example.com/','http://127.1','https://example.com:8080/']:
            with self.subTest(url=url),self.assertRaises(FetchError):validate_url(url)
        for ip in ['127.0.0.1','10.0.0.1','169.254.169.254','::ffff:127.0.0.1','::1']:self.assertFalse(public_ip(ip))
        self.assertTrue(public_ip('8.8.8.8'))

    def test_fragment_removed(self):self.assertEqual(validate_url('https://docs.python.org/#heading'),'https://docs.python.org/')


class ResolverTests(unittest.IsolatedAsyncioTestCase):
    async def test_private_dns_answer_is_rejected_before_connection(self):
        resolver=PublicResolver()
        resolver._resolver.resolve=AsyncMock(return_value=[{'host':'127.0.0.1','port':443}])
        with self.assertRaises(OSError):await resolver.resolve('public-name.example',443)
        await resolver.close()


if __name__=='__main__':unittest.main()
