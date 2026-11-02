from decimal import Decimal
import json
import subprocess
import pytest
from fastapi.testclient import TestClient
from drama_factory import api
from drama_factory.store import Store
from drama_factory.production import create_job, produce
from drama_factory.budget import quote_cad


def test_quotes():
    assert quote_cad('1','1.4','.15') == Decimal('1.61')
    assert quote_cad('.001') == Decimal('.01')
    for bad in ('NaN','-1','Infinity'):
        with pytest.raises(ValueError):
            quote_cad(bad)


def test_persistent_budget(tmp_path):
    store = Store(tmp_path)
    job = create_job(store,'A shy first crush')
    store.reserve(job,'first','10')
    Store(tmp_path).reserve(job,'first','10')
    with pytest.raises(ValueError):
        store.reserve(job,'retry','8.01')
    store.reserve(job,'second','8')
    assert store.job(job)['cost']['reserved_cad']==18


def test_api_and_resume(tmp_path,monkeypatch):
    store = Store(tmp_path)
    monkeypatch.setattr(api,'store',store)
    with TestClient(api.app) as client:
        profile = client.get('/characters').json()[0]
        profile['name']='Alex'
        assert client.post('/characters',json=profile).status_code==200
        assert client.post('/jobs',json={'premise':'hello','mode':'paid'}).status_code==422
        response = client.post('/jobs',json={'premise':'A graduation misunderstanding'})
        assert response.status_code==202
        job = response.json()['id']
        assert client.get(f'/jobs/{job}').json()['status']=='complete'
        shot = tmp_path / job / 'shot_0.mp4'
        stamp = shot.stat().st_mtime_ns
        with store.connection() as db:
            db.execute("UPDATE jobs SET status='failed' WHERE id=?",(job,))
        assert client.post(f'/jobs/{job}/resume').status_code==202
        assert shot.stat().st_mtime_ns==stamp
        assert client.get(f'/jobs/{job}').json()['cost']['actual_cad']==0
        assert client.post(f'/jobs/{job}/shots/0/review',json={'review':'inconsistent'}).status_code==200
        assert client.get(f'/jobs/{job}/assets/nope').status_code==404
        for aspect,size in [('portrait',(360,640)),('landscape',(640,360))]:
            path=tmp_path/job/f'{aspect}.mp4'
            result=subprocess.run(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(path)],capture_output=True,text=True,check=True)
            probe=json.loads(result.stdout)
            video=next(s for s in probe['streams'] if s['codec_type']=='video')
            assert (video['width'],video['height'])==size
            assert abs(float(probe['format']['duration'])-60)<.1
            assert client.get(f'/jobs/{job}/assets/{aspect}.mp4').status_code==200
