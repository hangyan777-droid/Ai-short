from decimal import Decimal
import json
import subprocess
import pytest
from drama_factory.core import check_budget, generate_mock, plan_episode
from drama_factory.providers import RunwayProvider, authorize_episode


def test_story_and_profiles():
    episode = plan_episode('A rainy school afternoon')
    assert sum(s.seconds for s in episode.scenes) == 60
    assert len(episode.characters) == 2
    assert all('A rainy school afternoon' in s.action for s in episode.scenes)
    assert episode == plan_episode(episode.premise)

@pytest.mark.parametrize('value', ['18.01', '-1', 'NaN', 'Infinity'])
def test_budget_rejects_invalid_cost(value):
    with pytest.raises(ValueError):
        check_budget(Decimal(value))


def test_budget_boundary_and_cumulative():
    assert check_budget(Decimal('18')) == Decimal('18')
    with pytest.raises(ValueError):
        check_budget(Decimal('10'), Decimal('9'))


def test_paid_provider_disabled():
    with pytest.raises(NotImplementedError):
        RunwayProvider().generate(plan_episode('hello').scenes[0], (), None)


def test_preflight_budget():
    class ExpensiveProvider:
        def estimate_cad(self, scene):
            return Decimal('4')
    with pytest.raises(ValueError):
        authorize_episode(ExpensiveProvider(), plan_episode('hello').scenes)

@pytest.mark.parametrize('premise', ['', ' ' , 'x' * 501])
def test_invalid_premise(premise):
    with pytest.raises(ValueError):
        plan_episode(premise)


def test_real_ffmpeg_mock_workflow(tmp_path, monkeypatch):
    import socket
    def no_network(*args, **kwargs):
        raise AssertionError('Mock mode must not use the network')
    monkeypatch.setattr(socket, 'create_connection', no_network)
    path = generate_mock(plan_episode('A forgotten sketchbook'), tmp_path)
    probe = subprocess.run(['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(path)], check=True, capture_output=True, text=True)
    data = json.loads(probe.stdout)
    assert abs(float(data['format']['duration']) - 60) < .1
    assert {s['codec_type'] for s in data['streams']} == {'video', 'audio', 'subtitle'}
    video = next(s for s in data['streams'] if s['codec_type'] == 'video')
    assert (video['width'], video['height']) == (360, 640)
    subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-f', 'null', '-'], check=True)
    assert json.loads((path.parent / 'budget.json').read_text())['spent'] == '0.00'
    assert len(json.loads((path.parent / 'storyboard.json').read_text())['scenes']) == 6
