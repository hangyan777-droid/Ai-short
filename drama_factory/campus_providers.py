"""Documented HTTP adapters, with no automatic billable retries."""
import base64
from pathlib import Path
import time
import httpx
from PIL import Image
from .campus_state import sha
from .film import validate_clip

RUNWAY='https://api.dev.runwayml.com/v1'


def image_uri(path):
    path=Path(path)
    raw=path.read_bytes()
    if len(raw)>5_000_000:
        raise ValueError('Reference image exceeds 5 MB')
    with Image.open(path) as im:
        if im.format!='PNG' or im.size!=(720,1280):
            raise ValueError('Reference/keyframe must be a 720x1280 PNG')
        im.verify()
    return 'data:image/png;base64,'+base64.b64encode(raw).decode()


def download(url,target):
    if not url.startswith('https://'):
        raise ValueError('Expected HTTPS asset')
    with httpx.stream('GET',url,timeout=120,follow_redirects=False) as response:
        if not response.is_success:
            raise RuntimeError(f'Asset download HTTP {response.status_code}; resume the existing task, do not regenerate')
        size=0
        with target.open('wb') as file:
            for chunk in response.iter_bytes():
                size+=len(chunk)
                if size>250_000_000:
                    raise ValueError('Downloaded asset exceeds 250 MB')
                file.write(chunk)


def runway(state,rid,payload,kind,target,cost,key):
    row=state.begin(rid,payload,cost,target)
    target=Path(target)
    target.parent.mkdir(parents=True,exist_ok=True)
    if row['status']=='complete':
        if not target.exists() or sha(target)!=row['asset_sha']:
            raise ValueError(f'{rid}: completed asset changed or missing. Restore it; never regenerate automatically.')
        return
    if row['status']=='failed':
        raise ValueError(f'{rid}: failed task. Reservation held; paid retry needs a separate explicit approval and reconciliation.')
    with httpx.Client(headers={'Authorization':f'Bearer {key}','X-Runway-Version':'2024-11-06'},timeout=60) as client:
        if row['task_id'] is None:
            # begin() persists submitting before the POST. Only the fresh caller may POST.
            if row.get('_fresh') is not True:
                raise RuntimeError(f'{rid}: ambiguous submission. Find the task in provider history; no automatic resubmission.')
        task_id=row['task_id']
        if task_id is None:
            response=client.post(RUNWAY+('/text_to_image' if kind=='image' else '/image_to_video'),json=payload)
            if not response.is_success:
                raise RuntimeError(f'{rid}: submission HTTP {response.status_code}; reservation held until reconciled')
            task_id=response.json()['id']
            state.update(rid,status='polling',task_id=task_id)
        for attempt in range(120):
            response=client.get(RUNWAY+'/tasks/'+task_id)
            if response.status_code==429 or response.status_code>=500:
                time.sleep(min(10,2+attempt))
                continue
            if not response.is_success:
                raise RuntimeError(f'{rid}: polling HTTP {response.status_code}; resume existing task later')
            result=response.json()
            if result['status']=='SUCCEEDED':
                break
            if result['status'] in ('FAILED','CANCELED','CANCELLED'):
                state.update(rid,status='failed',error='Provider task failed; reservation held')
                raise RuntimeError(f'{rid}: provider task failed. No paid retry was submitted.')
            time.sleep(5)
        else:
            raise RuntimeError('Polling time limit; rerun the same approved command to resume')
    # No API authorization on the output download.
    temp=target.with_suffix('.partial'+target.suffix)
    download(result['output'][0],temp)
    if kind=='image':
        with Image.open(temp) as im:
            if im.size!=(720,1280):
                raise ValueError('Expected a 720x1280 image; check provider ratio before continuing')
            im.convert('RGB').save(temp,format='PNG')
    else:
        validate_clip(temp)
        import json,subprocess
        info=json.loads(subprocess.run(['ffprobe','-v','error','-show_streams','-of','json',str(temp)],check=True,capture_output=True,text=True).stdout)
        video=next(s for s in info['streams'] if s['codec_type']=='video')
        if video['width']<720 or video['height']<1280:
            raise ValueError('Provider returned below 720p portrait; do not upscale silently')
    temp.replace(target)
    state.update(rid,status='complete',asset_sha=sha(target))


def speech(state,rid,payload,target,cost,key):
    before=state.request(rid)
    row=state.begin(rid,payload,cost,target)
    target=Path(target)
    target.parent.mkdir(parents=True,exist_ok=True)
    if row['status']=='complete':
        if not target.is_file() or sha(target)!=row['asset_sha']:
            raise ValueError('Narration asset changed; restore it rather than resubmit')
        return
    if before:
        raise RuntimeError('Ambiguous TTS submission. Reconcile provider billing before authorizing a replacement.')
    with httpx.Client(timeout=120) as client:
        response=client.post('https://api.openai.com/v1/audio/speech',headers={'Authorization':f'Bearer {key}'},json=payload)
    if not response.is_success:
        raise RuntimeError(f'TTS HTTP {response.status_code}; reservation retained')
    temp=target.with_suffix('.partial.wav')
    temp.write_bytes(response.content)
    # Verify real audio, not a JSON error saved as a WAV.
    import subprocess
    subprocess.run(['ffprobe','-v','error','-select_streams','a:0','-show_entries','stream=codec_type',str(temp)],check=True,capture_output=True)
    temp.replace(target)
    state.update(rid,status='complete',asset_sha=sha(target))
