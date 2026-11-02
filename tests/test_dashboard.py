from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest
from drama_factory import api
from drama_factory.store import Store


def test_generate_button(tmp_path,monkeypatch):
    monkeypatch.setattr(api,'store',Store(tmp_path))
    with TestClient(api.app) as client:
        monkeypatch.setattr('httpx.request',lambda method,url,**kwargs: client.request(method,url.replace('http://127.0.0.1:8000',''),**{k:v for k,v in kwargs.items() if k!='timeout'}))
        app = AppTest.from_file('../app.py',default_timeout=60).run()
        assert not app.exception
        next(b for b in app.button if b.label=='Generate New Episode').click().run()
        assert not app.exception
        assert app.success
        assert client.get('/jobs').json()[0]['status']=='complete'
