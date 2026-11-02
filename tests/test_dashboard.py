from streamlit.testing.v1 import AppTest


def test_generate_button(tmp_path, monkeypatch):
    from drama_factory import core
    original = core.generate_mock
    monkeypatch.setattr(core, 'generate_mock', lambda episode, root: original(episode, tmp_path))
    app = AppTest.from_file('../app.py', default_timeout=60).run()
    assert not app.exception
    app.button[0].click().run()
    assert not app.exception
    assert 'Actual cost: CAD $0.00' in app.success[0].value
    assert len(list(tmp_path.glob('*/episode.mp4'))) == 1
