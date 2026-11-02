"""CLI for one film. Paid submission is explicit, quoted, resumable and never retried."""
import argparse
import base64
from contextlib import contextmanager
from decimal import Decimal
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import time
import wave

import httpx
from dotenv import load_dotenv
from PIL import Image
from .budget import quote_cad

ROOT = Path(__file__).resolve().parent.parent
PACK = ROOT / 'film' / 'episode.json'
API = 'https://api.dev.runwayml.com/v1'


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def save(path,value):
    temp=path.with_suffix('.tmp')
    temp.write_text(json.dumps(value,indent=2,ensure_ascii=False),encoding='utf8')
    temp.replace(path)


def pack():
    data=json.loads(PACK.read_text(encoding='utf8'))
    if len(data['shots'])!=12 or sum(s['seconds'] for s in data['shots'])!=60 or any(s['seconds']!=5 for s in data['shots']):
        raise ValueError('This workflow requires twelve five-second shots')
    return data


def frames(data):
    result={}
    for shot in data['shots']:
        path=PACK.parent / shot['keyframe']
        raw=path.read_bytes()
        if len(raw)>5_000_000 or raw[:8]!=b'\x89PNG\r\n\x1a\n' or struct.unpack('>II',raw[16:24])!=(720,1280):
            raise ValueError(f'{path} must be a PNG at 720x1280 below 5 MB')
        with Image.open(path) as image:
            image.verify()
        result[shot['id']]=hashlib.sha256(raw).hexdigest()
    return result


def make_quote(data, usd,rate,margin,prior,source):
    previous=Decimal(str(prior))
    if not previous.is_finite() or previous<0 or not source.strip():
        raise ValueError('Supply a valid prior cost and current pricing source')
    shot_cad=quote_cad(Decimal(str(usd))*5,rate,margin)
    if shot_cad<=0:
        raise ValueError('Paid quote must have a positive price')
    total=previous+12*shot_cad
    if total>18:
        raise ValueError(f'Quote CAD {total} exceeds CAD $18')
    return dict(script_sha=digest(data),frames=frames(data),usd_per_second=str(usd),rate=str(rate),margin=str(margin),prior_cad=str(previous),shot_cad=str(shot_cad),total_cad=str(total),price_source=source)


@contextmanager
def lock(folder):
    path=folder/'production.lock'
    try:
        fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    except FileExistsError:
        raise RuntimeError('Production locked. If a process crashed, confirm it stopped before removing production.lock.')
    os.close(fd)
    try:
        yield
    finally:
        path.unlink(missing_ok=True)


def command(args,cwd=None):
    result=subprocess.run(args,cwd=cwd,capture_output=True,text=True)
    if result.returncode:
        raise RuntimeError(result.stderr[-1500:])


def validate_clip(path):
    result=subprocess.run(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(path)],capture_output=True,text=True,check=True)
    data=json.loads(result.stdout)
    video=next(s for s in data['streams'] if s['codec_type']=='video')
    if float(data['format']['duration'])<4.9 or video['width']/video['height'] > 0.58 or video['width']/video['height'] < 0.54:
        raise ValueError(f'Invalid portrait shot: {path}')


def generate(data,folder,approval):
    quote=json.loads((folder/'quote.json').read_text())
    if approval!=digest(quote):
        raise ValueError('Exact quote approval hash required')
    fresh=make_quote(data,quote['usd_per_second'],quote['rate'],quote['margin'],quote['prior_cad'],quote['price_source'])
    if fresh!=quote:
        raise ValueError('Script, input images or quote changed. Requote and obtain fresh approval.')
    key=os.getenv('RUNWAY_API_KEY')
    if not key:
        raise ValueError('Set RUNWAY_API_KEY securely in .env before paid production')
    ledger_path=folder/'ledger.json'
    ledger=json.loads(ledger_path.read_text()) if ledger_path.exists() else {'quote_sha':approval,'shots':{}}
    if ledger['quote_sha']!=approval:
        raise ValueError('Existing production belongs to a different quote')
    with httpx.Client(headers={'Authorization':f'Bearer {key}','X-Runway-Version':'2024-11-06'},timeout=60) as client:
        for shot in data['shots']:
            sid=shot['id']
            target=folder/f'{sid}.mp4'
            state=ledger['shots'].get(sid)
            if state and state['status']=='complete':
                validate_clip(target)
                continue
            if state is None:
                reserved=Decimal(quote['prior_cad'])+sum(Decimal(v['reserved_cad']) for v in ledger['shots'].values())+Decimal(quote['shot_cad'])
                if reserved>18:
                    raise ValueError('Budget exhausted')
                state={'status':'submitting','reserved_cad':quote['shot_cad']}
                ledger['shots'][sid]=state
                save(ledger_path,ledger)  # Ambiguous network errors must never create a second paid task.
                raw=(PACK.parent/shot['keyframe']).read_bytes()
                response=client.post(API+'/image_to_video',json={'model':data['model'],'promptImage':'data:image/png;base64,'+base64.b64encode(raw).decode(),'promptText':shot['video_prompt'],'duration':5,'ratio':'720:1280'})
                if not response.is_success:
                    raise RuntimeError(f'Runway submission returned HTTP {response.status_code}. Reservation held; reconcile before retrying.')
                state.update(task_id=response.json()['id'],status='polling')
                save(ledger_path,ledger)
            if 'task_id' not in state:
                raise RuntimeError(f'Shot {sid}: ambiguous submission. Reconcile in Runway; automatic resubmission prohibited.')
            if state['status']=='failed':
                raise RuntimeError(f'Shot {sid} failed. Reservation held; no automatic paid retry.')
            for _ in range(120):
                response=client.get(API+'/tasks/'+state['task_id'])
                if not response.is_success:
                    raise RuntimeError(f'Polling HTTP {response.status_code}; resume later using saved task ID.')
                task=response.json()
                if task['status']=='SUCCEEDED':
                    break
                if task['status'] in ('FAILED','CANCELED','CANCELLED'):
                    state['status']='failed'
                    save(ledger_path,ledger)
                    raise RuntimeError(f'Shot {sid} failed; paid retries disabled.')
                time.sleep(5)
            else:
                raise RuntimeError('Polling time limit reached; resume later without new submission')
            url=task['output'][0]
            if not url.startswith('https://'):
                raise ValueError('Output must use HTTPS')
            # Fresh client: API Authorization is never sent to an asset host.
            temp=target.with_suffix('.partial.mp4')
            with httpx.stream('GET',url,timeout=120,follow_redirects=False) as download:
                download.raise_for_status()
                size=0
                with temp.open('wb') as file:
                    for chunk in download.iter_bytes():
                        size+=len(chunk)
                        if size>250_000_000:
                            raise ValueError('Asset too large')
                        file.write(chunk)
            validate_clip(temp)
            temp.replace(target)
            state['status']='complete'
            save(ledger_path,ledger)


def music(path):
    # Original four-chord arpeggio, synthesized locally; no licensed recording used.
    rate=22050
    chords=[(261.63,329.63,392),(220,261.63,329.63),(174.61,220,261.63),(196,246.94,293.66)]
    audio=bytearray()
    for i in range(rate*60):
        t=i/rate
        note=chords[int(t//4)%4][int(t*2)%3]
        phase=t%0.5
        env=math.exp(-5*phase)*min(1,phase*100)
        value=(math.sin(2*math.pi*note*phase)+.25*math.sin(4*math.pi*note*phase))*env
        fade=min(1,t/2,(60-t)/3)
        audio.extend(struct.pack('<h',int(3400*value*max(0,fade))))
    with wave.open(str(path),'wb') as file:
        file.setparams((1,2,rate,0,'NONE','not compressed'))
        file.writeframes(audio)


def assemble(data,folder,mock=False):
    for shot in data['shots']:
        validate_clip(folder/f"{shot['id']}.mp4")
    def stamp(s):
        return f'00:{s//60:02d}:{s%60:02d},000'
    lines=[]
    for i,shot in enumerate(data['shots'],1):
        prefix='[PIPELINE TEST] ' if mock else ''
        lines.append(f"{i}\n{stamp(shot['start'])} --> {stamp(shot['start']+5)}\n{prefix}{shot['subtitle']}\n")
    (folder/'captions.srt').write_text('\n'.join(lines),encoding='utf8')
    (folder/'clips.txt').write_text(''.join(f"file '{s['id']}.mp4'\n" for s in data['shots']))
    music(folder/'score.wav')
    name='PIPELINE_TEST.mp4' if mock else 'The_Seat_Beside_You.mp4'
    command(['ffmpeg','-v','error','-y','-f','concat','-safe','1','-i','clips.txt','-i','score.wav','-vf',"scale=720:1280,setsar=1,subtitles=captions.srt:force_style='Fontsize=18,Outline=1,MarginV=35'",'-map','0:v','-map','1:a','-r','24','-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-t','60','-movflags','+faststart',name],cwd=folder)
    print(folder/name)


def main():
    # Only the CAMPUS LOVE CLI is exposed. Legacy helpers remain for regression tests.
    import sys
    from .campus import main as campus_main
    try:
        return campus_main(sys.argv[1:])
    except (ValueError, OSError, RuntimeError) as error:
        print(f'Cannot continue: {error}', file=sys.stderr)
        raise SystemExit(2)
    except httpx.HTTPError:
        print('Network request failed. State and reservations are preserved. Reconcile before approving any paid retry.', file=sys.stderr)
        raise SystemExit(2)

if __name__=='__main__':
    main()
