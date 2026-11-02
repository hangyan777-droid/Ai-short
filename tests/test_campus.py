"""No external API calls. State, approvals and adapter contracts use local assets."""
from datetime import datetime, timezone
from decimal import Decimal
from io import BytesIO
import json
from pathlib import Path
from types import SimpleNamespace
import subprocess
import wave

import httpx
from PIL import Image
import pytest
from drama_factory import campus, campus_providers
from drama_factory.campus_state import Production, sha
from drama_factory.film import digest, save


@pytest.fixture
def setup(tmp_path,monkeypatch):
    root=tmp_path/'episode'; root.mkdir()
    monkeypatch.setattr(campus,'CHARACTERS',tmp_path/'characters')
    monkeypatch.setenv('RUNWAY_API_KEY','test-not-real')
    monkeypatch.setenv('OPENAI_API_KEY','test-not-real')
    monkeypatch.setenv('TTS_PROVIDER','openai')
    story=campus.load_story(root)
    p=campus.price(campus.PRICING)
    p.update(verified_at=datetime.now(timezone.utc).isoformat(),capabilities_verified=True)
    return root,story,p,Production(root)


def refs(story):
    for who in story['characters']:
        for view in ('front','side','full'):
            path=campus.CHARACTERS/who/f'{view}.png'
            path.parent.mkdir(parents=True,exist_ok=True)
            Image.new('RGB',(720,1280),'gray').save(path)


def test_preproduce_and_dryrun_never_use_network(setup,monkeypatch,capsys):
    root,story,p,state=setup
    def forbidden(*args,**kwargs): pytest.fail('Dry runs must never create a network client')
    monkeypatch.setattr(httpx,'Client',forbidden)
    campus.main(['preproduce','--episode','1','--output',str(root)])
    assert (root/'PRODUCTION.md').exists()
    assert json.loads((root/'budget_estimate.json').read_text())['pricing_verified'] is False
    campus.main(['test-shot','--episode','1','--shot','1','--output',str(root)])
    assert 'DRY RUN' in capsys.readouterr().out
    assert not state.costs()
    plan=campus.make_plan('test-shot',root,story,p,state)
    assert plan['blockers']


def test_manual_script_preserved(setup):
    root,story,p,state=setup
    save(root/'storyboard.json',story)
    story['shots'][0]['subtitle_zh']='手动修改的字幕'
    save(root/'storyboard.json',story)
    campus.write_documents(root,campus.load_story(root),p)
    assert '手动修改的字幕' in (root/'PRODUCTION.md').read_text()


def test_budget_estimate_and_overcap(setup):
    root,story,p,state=setup
    estimate=campus.estimate(story,p)
    assert estimate['base_cad']=='7.37'
    assert estimate['conservative_cad']=='8.49'
    assert estimate['single_5s_gen4_turbo_cad']=='0.41'
    p['gen4_image_usd']='100'
    plan=campus.make_plan('characters',root,story,p,state)
    assert any('exceed' in b for b in plan['blockers'])
    with pytest.raises(ValueError): campus.execute(plan,state)
    assert not state.costs()


def test_missing_and_stale_price_block_paid_calls(setup):
    root,story,p,state=setup
    p['verified_at']='2000-01-01'
    plan=campus.make_plan('characters',root,story,p,state)
    assert not campus.verified(p)
    with pytest.raises(ValueError,match='unverified'): campus.execute(plan,state)


def test_full_production_requires_real_test(setup):
    root,story,p,state=setup
    plan=campus.make_plan('produce',root,story,p,state)
    assert any('test shot' in b for b in plan['blockers'])
    with pytest.raises(ValueError): campus.execute(plan,state)
    assert not state.costs()


def test_character_file_change_invalidates_approval(setup):
    root,story,p,state=setup
    refs(story)
    fingerprint=campus.bible_fingerprint(story)
    state.approve('characters',fingerprint)
    assert not campus.make_plan('keyframes',root,story,p,state)['blockers']
    Image.new('RGB',(720,1280),'blue').save(campus.CHARACTERS/'haruto/front.png')
    assert not state.approved('characters',campus.bible_fingerprint(story))
    assert campus.make_plan('keyframes',root,story,p,state)['blockers']


def test_exact_quote_required_and_keys_not_sufficient(setup):
    root,story,p,state=setup
    price_file=root/'pricing.json'; save(price_file,p)
    with pytest.raises(ValueError,match='exact reviewed'):
        campus.main(['characters','--output',str(root),'--pricing',str(price_file),'--execute','--approve-quote','incorrect'])
    assert not state.costs()


def test_reconcile_releases_unused_reservation(setup):
    root,story,p,state=setup
    row=state.begin('example',{'payload':1},'10',root/'asset')
    assert row['_fresh']
    state.update('example',status='complete')
    state.reconcile('example','2.00','provider billing receipt, verified manually')
    assert state.report()['committed_cad']=='2.00'
    assert state.report()['actual_reported_cad']=='2.00'
    state.store.reserve('campus_episode_01','another','16.00')
    with pytest.raises(ValueError,match='exceeded'):
        state.store.reserve('campus_episode_01','too-much','.01')


def test_submitting_state_never_auto_retries(setup,monkeypatch):
    root,story,p,state=setup
    payload={'model':'gen4_image'}
    state.begin('ambiguous',payload,'.13',root/'test.png')
    class Client:
        def __init__(self,**kwargs): pass
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def post(self,*args,**kwargs): pytest.fail('Never retry ambiguous paid request')
    monkeypatch.setattr(httpx,'Client',Client)
    with pytest.raises(RuntimeError,match='ambiguous'):
        campus_providers.runway(state,'ambiguous',payload,'image',root/'test.png','.13','test-key')


@pytest.fixture(scope='module')
def source_clip(tmp_path_factory):
    path=tmp_path_factory.mktemp('source')/'clip.mp4'
    subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','color=c=gray:s=720x1280:r=24:d=5','-c:v','libx264','-threads','2','-preset','ultrafast','-pix_fmt','yuv420p',str(path)],check=True)
    return path


def test_adapter_stages_and_resume_without_double_spend(setup,monkeypatch,source_clip):
    root,story,p,state=setup
    submissions=[]
    task_kind={}
    audio=BytesIO()
    with wave.open(audio,'wb') as file:
        file.setparams((1,2,22050,0,'NONE','not compressed')); file.writeframes(b'\0\0'*22050)
    class Client:
        def __init__(self,**kwargs): pass
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def post(self,url,**kwargs):
            body=kwargs['json']; submissions.append((url,body))
            if url.endswith('/audio/speech'):
                return httpx.Response(200,content=audio.getvalue())
            task=f'task-{len(submissions)}'; task_kind[task]='image' if url.endswith('/text_to_image') else 'video'
            return httpx.Response(200,json={'id':task})
        def get(self,url):
            task=url.rsplit('/',1)[1]
            return httpx.Response(200,json={'status':'SUCCEEDED','output':[f'https://assets.test/{task}']})
    def download(url,target):
        kind=task_kind[url.rsplit('/',1)[1]]
        if kind=='image': Image.new('RGB',(720,1280),'gray').save(target,format='PNG')
        else: target.write_bytes(source_clip.read_bytes())
    monkeypatch.setattr(httpx,'Client',Client)
    monkeypatch.setattr(campus_providers,'download',download)
    campus.execute(campus.make_plan('characters',root,story,p,state),state)
    assert len(submissions)==6
    state.approve('characters',campus.bible_fingerprint(story))
    campus.execute(campus.make_plan('keyframes',root,story,p,state),state)
    assert len(submissions)==18
    for url,body in submissions[6:18]:
        assert len(body['referenceImages'])<=3
        assert body['ratio']=='720:1280'
    campus.approve_asset(SimpleNamespace(asset='keyframe',shot=1),root,story,state)
    plan=campus.make_plan('test-shot',root,story,p,state)
    assert not plan['blockers']
    campus.execute(plan,state)
    assert len(submissions)==19
    assert campus.make_plan('produce',root,story,p,state)['blockers']
    campus.approve_asset(SimpleNamespace(asset='keyframes',shot=1),root,story,state)
    campus.approve_asset(SimpleNamespace(asset='test-shot',shot=1),root,story,state)
    full=campus.make_plan('produce',root,story,p,state)
    assert not full['blockers']
    campus.execute(full,state)
    # Six references, twelve keyframes, twelve clips, eleven spoken lines.
    assert len(submissions)==41
    assert sum(url.endswith('/image_to_video') for url,_ in submissions)==12
    assert sum(url.endswith('/audio/speech') for url,_ in submissions)==11
    before=state.report()['committed_cad']
    campus.execute(campus.make_plan('produce',root,story,p,state),state)
    assert len(submissions)==41
    assert state.report()['committed_cad']==before=='7.37'
    assert state.report()['unreconciled_reserved_cad']=='7.37'
    assert state.report()['actual_reported_cad']=='0.00'  # No billing reported, reservations still held.
    image=submissions[0][1]
    assert 'referenceImages' not in image
    assert 'referenceImages' in submissions[1][1]


def test_kling_no_audio_parameter(setup):
    root,story,p,state=setup
    story['shots'][10]['model']='kling3.0_standard'
    plan=campus.make_plan('produce',root,story,p,state)
    task=next(t for t in plan['tasks'] if t['id']=='video:11')
    assert task['model']=='kling3.0_standard'
    assert Decimal(task['usd'])==Decimal('.5')


def test_mock_cannot_approve_real_test(setup):
    root,story,p,state=setup
    (root/'MOCK_ONLY').touch()
    with pytest.raises(ValueError,match='Mock footage'):
        campus.approve_asset(SimpleNamespace(asset='test-shot',shot=1),root,story,state)


def test_subtitles_and_mock_promotion_guard(setup):
    from drama_factory.campus_edit import subtitles, assemble
    root,story,p,state=setup
    subtitles(root,story,True)
    ass=(root/'subtitles.ass').read_text()
    assert '其实，我也一直喜欢你。' in ass
    assert '実は、私もずっと好きだった。' in ass
    assert 'Noto Sans CJK SC' in ass and 'Noto Sans CJK JP' in ass
    assert 'NO REAL VOICE' in ass
    assert len((root/'subtitles.zh.srt').read_text().split('-->'))==13
    (root/'MOCK_ONLY').touch()
    with pytest.raises(ValueError,match='separate'):
        assemble(root,story,state,mock=False)
