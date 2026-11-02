"""Deterministic story planning, budget enforcement, and local video production."""
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
import json
import shutil
import subprocess
import uuid

LIMIT = Decimal('18.00')

@dataclass(frozen=True)
class Character:
    name: str
    role: str
    description: str

CHARACTERS = (
    Character('Ethan', 'male lead', '18-year-old final-year student; dark wavy hair, navy cardigan, reserved and kind'),
    Character('Maya', 'female lead', '18-year-old final-year student; shoulder-length black hair, cream sweater, curious and confident'),
)

@dataclass(frozen=True)
class Scene:
    title: str
    action: str
    caption: str
    seconds: int = 10

@dataclass(frozen=True)
class Episode:
    title: str
    premise: str
    characters: tuple[Character, ...]
    scenes: tuple[Scene, ...]


def plan_episode(premise: str, characters=CHARACTERS) -> Episode:
    premise = premise.strip()
    if not premise or len(premise) > 500:
        raise ValueError('Enter a premise between 1 and 500 characters.')
    if len(characters) != 2 or any(not c.name.strip() or not c.description.strip() for c in characters):
        raise ValueError('Both character profiles need a name and description.')
    boy, girl = characters
    beats = [
        ('The encounter', f'{girl.name} drops a notebook in a sunlit school corridor. {boy.name} stops to help.', 'One ordinary afternoon...'),
        ('A small connection', f'{boy.name} notices a sketch of the school rooftop in the notebook.', 'You draw the places I go to think.'),
        ('The invitation', f'{girl.name} invites {boy.name} to meet after class by the library.', 'Meet me when the last bell rings.'),
        ('The misunderstanding', f'{girl.name} waits as rain starts; {boy.name} is delayed helping a classmate.', 'Maybe I imagined the connection.'),
        ('The choice', f'{boy.name} races down the corridor carrying an umbrella.', 'Some moments are worth running for.'),
        ('A new beginning', f'{boy.name} finds {girl.name}; they share the umbrella and walk home.', 'Tomorrow, same time?'),
    ]
    scenes = tuple(Scene(t, f'{a} Story context: {premise}. Cinematic warm light, gentle camera movement, consistent wardrobe.', c) for t, a, c in beats)
    return Episode('When the Last Bell Rings', premise, tuple(characters), scenes)


def check_budget(estimated_cad: Decimal, spent_cad: Decimal = Decimal('0')) -> Decimal:
    if not estimated_cad.is_finite() or not spent_cad.is_finite() or min(estimated_cad, spent_cad) < 0:
        raise ValueError('Costs must be finite and nonnegative.')
    total = estimated_cad + spent_cad
    if total > LIMIT:
        raise ValueError('Episode would exceed the CAD $18 budget limit.')
    return total


def run(command: list[str]) -> None:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f'FFmpeg failed: {result.stderr[-2000:]}')


def generate_mock(episode: Episode, output_root: Path) -> Path:
    check_budget(Decimal('0'))
    if sum(s.seconds for s in episode.scenes) != 60:
        raise ValueError('An episode must be exactly 60 seconds.')
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
        raise RuntimeError('Install FFmpeg and ffprobe before generating an episode.')
    folder = output_root / uuid.uuid4().hex
    folder.mkdir(parents=True)
    (folder / 'storyboard.json').write_text(json.dumps(asdict(episode), indent=2), encoding='utf-8')
    colors = ['0x27374d', '0x526d82', '0x66545e', '0x354f52', '0x7f5539', '0x52796f']
    subtitle_lines = []
    for i, scene in enumerate(episode.scenes):
        subtitle_lines.append(f'{i+1}\n00:00:{i*10:02d},000 --> 00:01:00,000\n{scene.title}: {scene.caption}\n' if i == 5 else f'{i+1}\n00:00:{i*10:02d},000 --> 00:00:{(i+1)*10:02d},000\n{scene.title}: {scene.caption}\n')
        # All filter values are internal constants; user text never enters a shell or filter.
        run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', f'color=c={colors[i]}:s=360x640:r=24:d={scene.seconds}', '-an', '-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p', str(folder / f'scene_{i}.mp4')])
    (folder / 'captions.srt').write_text('\n'.join(subtitle_lines), encoding='utf-8')
    (folder / 'clips.txt').write_text(''.join(f"file 'scene_{i}.mp4'\n" for i in range(6)), encoding='utf-8')
    target = folder / 'episode.mp4'
    run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '1', '-i', str(folder / 'clips.txt'), '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo', '-i', str(folder / 'captions.srt'), '-map', '0:v', '-map', '1:a', '-map', '2:s', '-c:v', 'copy', '-c:a', 'aac', '-c:s', 'mov_text', '-t', '60', '-movflags', '+faststart', str(target)])
    (folder / 'budget.json').write_text(json.dumps({'currency': 'CAD', 'limit': '18.00', 'spent': '0.00', 'mode': 'mock'}))
    return target
