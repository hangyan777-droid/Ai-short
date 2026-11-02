from decimal import Decimal
import json
from pathlib import Path
import httpx
from PIL import Image
import pytest
from drama_factory import film

@pytest.fixture
def ready(tmp_path,monkeypatch):
    data=film.pack()
    plan=tmp_path/'film'
    (plan/'frames').mkdir(parents=True)
    for shot in data['shots']:
        Image.new('RGB',(720,1280),'gray').save(plan/shot['keyframe'])
    monkeypatch.setattr(film,'PACK',plan/'episode.json')
    out=tmp_path/'production'
    out.mkdir()
    return data,out


def test_story_structure():
    data=film.pack()
    assert sum(s['seconds'] for s in data['shots'])==60
    assert len({s['id'] for s in data['shots']})==12
    assert all(len(s['video_prompt'])<1000 for s in data['shots'])
    assert all('18-year-old' in c for c in data['characters'].values())


def test_quote_hash_and_limit(ready):
    data,out=ready
    quote=film.make_quote(data,'.05','1.40','.15','5','verified test price')
    # Round every request upward conservatively.
    assert Decimal(quote['total_cad'])==Decimal('9.92')
    first=film.digest(quote)
    Image.new('RGB',(720,1280),'blue').save(film.PACK.parent/'frames/01.png')
    changed=film.make_quote(data,'.05','1.40','.15','5','verified test price')
    assert first!=film.digest(changed)
    with pytest.raises(ValueError,match='exceeds'):
        film.make_quote(data,'1','1.4','.15','0','test')


def test_approval_and_missing_key(ready,monkeypatch):
    data,out=ready
    quote=film.make_quote(data,'.05','1.4','.15','0','test')
    film.save(out/'quote.json',quote)
    with pytest.raises(ValueError,match='approval'):
        film.generate(data,out,'wrong')
    monkeypatch.delenv('RUNWAY_API_KEY',raising=False)
    with pytest.raises(ValueError,match='RUNWAY_API_KEY'):
        film.generate(data,out,film.digest(quote))


def test_ambiguous_post_never_retried(ready,monkeypatch):
    data,out=ready
    quote=film.make_quote(data,'.05','1.4','.15','0','test')
    film.save(out/'quote.json',quote)
    monkeypatch.setenv('RUNWAY_API_KEY','test-not-real')
    calls=[]
    class Client:
        def __init__(self,**kwargs): pass
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def post(self,*args,**kwargs):
            calls.append(kwargs['json'])
            raise httpx.ReadTimeout('Unknown submission outcome')
    monkeypatch.setattr(film.httpx,'Client',Client)
    with pytest.raises(httpx.ReadTimeout):
        film.generate(data,out,film.digest(quote))
    with pytest.raises(RuntimeError,match='ambiguous'):
        film.generate(data,out,film.digest(quote))
    assert len(calls)==1
    assert calls[0]['model']=='gen4_turbo'
    assert calls[0]['ratio']=='720:1280'
    assert calls[0]['duration']==5
    assert json.loads((out/'ledger.json').read_text())['shots']['01']['reserved_cad']=='0.41'


def test_polling_resumes_existing_task(ready,monkeypatch):
    data,out=ready
    quote=film.make_quote(data,'.05','1.4','.15','0','test')
    film.save(out/'quote.json',quote)
    film.save(out/'ledger.json',{'quote_sha':film.digest(quote),'shots':{'01':{'reserved_cad':'0.41','status':'polling','task_id':'existing-task'}}})
    monkeypatch.setenv('RUNWAY_API_KEY','test-not-real')
    class Client:
        def __init__(self,**kwargs): pass
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def post(self,*args,**kwargs): pytest.fail('Must not resubmit paid shot')
        def get(self,url):
            assert url.endswith('/tasks/existing-task')
            return httpx.Response(503,request=httpx.Request('GET',url))
    monkeypatch.setattr(film.httpx,'Client',Client)
    with pytest.raises(RuntimeError,match='Polling HTTP 503'):
        film.generate(data,out,film.digest(quote))


def test_successful_generation_and_rerun_do_not_rebill(ready,monkeypatch):
    data,out=ready
    quote=film.make_quote(data,'.05','1.4','.15','5','test')
    film.save(out/'quote.json',quote)
    monkeypatch.setenv('RUNWAY_API_KEY','test-not-real')
    posts=[]
    class Client:
        def __init__(self,**kwargs): pass
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def post(self,url,**kwargs):
            posts.append(kwargs['json'])
            return httpx.Response(200,json={'id':f'task-{len(posts)}'})
        def get(self,url):
            return httpx.Response(200,json={'status':'SUCCEEDED','output':['https://assets.example/shot.mp4']})
    class Download:
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def raise_for_status(self): pass
        def iter_bytes(self): yield b'test-video'
    def stream(method,url,**kwargs):
        assert 'headers' not in kwargs  # No API bearer token on asset fetches.
        assert url.startswith('https://assets.example/')
        return Download()
    monkeypatch.setattr(film.httpx,'Client',Client)
    monkeypatch.setattr(film.httpx,'stream',stream)
    monkeypatch.setattr(film,'validate_clip',lambda path: None)
    film.generate(data,out,film.digest(quote))
    film.generate(data,out,film.digest(quote))
    assert len(posts)==12
    ledger=json.loads((out/'ledger.json').read_text())
    assert all(s['status']=='complete' for s in ledger['shots'].values())
    assert sum(Decimal(s['reserved_cad']) for s in ledger['shots'].values())==Decimal('4.92')
