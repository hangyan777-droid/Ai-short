"""CAMPUS LOVE: preproduction, dry-run-first test shot, and approval-gated production."""
import argparse
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import json
import os
from pathlib import Path
import sys
from dotenv import load_dotenv
from .budget import quote_cad
from .campus_state import Production, sha
from .campus_providers import image_uri, runway, speech
from .film import ROOT, digest, save, lock

SOURCE=ROOT/'film/campus_love/episode_01.json'
PRICING=ROOT/'film/campus_love/pricing.example.json'
CHARACTERS=ROOT/'assets/characters'
MODELS={'gen4_turbo','kling3.0_standard'}


def load_story(root):
    path=Path(root)/'storyboard.json'
    data=json.loads((path if path.exists() else SOURCE).read_text(encoding='utf8'))
    if data['duration']!=60 or len(data['shots'])!=12:
        raise ValueError('Episode must contain twelve 5-second shots')
    for i,s in enumerate(data['shots'],1):
        if s['id']!=f'{i:02d}' or s['start']!=(i-1)*5 or s['seconds']!=5 or s['model'] not in MODELS:
            raise ValueError('Invalid timeline, shot id or unsupported model')
        if any(len(s[k].encode('utf-16-le'))//2>1000 for k in ('image_prompt','video_prompt')):
            raise ValueError('Runway prompts exceed 1000 UTF-16 units')
        if not 0<=s['audio']['start_offset']<5 or not 0<s['audio']['max_seconds']<=5-s['audio']['start_offset']:
            raise ValueError('Audio slot must fit the shot')
    return data


def price(path):
    data=json.loads(Path(path).read_text())
    quote_cad(1,data['usd_to_cad'],data['tax_margin'])
    for name in ('gen4_image_usd','gen4_turbo_usd_per_second','kling3.0_standard_usd_per_second','tts_usd_per_million_chars'):
        value=Decimal(data[name])
        if not value.is_finite() or value<=0:
            raise ValueError('Unit prices must be positive and finite')
    for name in ('retry_video_shots','retry_images'):
        if not isinstance(data[name],int) or not 0<=data[name]<=12:
            raise ValueError('Invalid retry allowance')
    quote_cad(data['retry_audio_usd'],data['usd_to_cad'],data['tax_margin'])
    return data


def cad(usd,p):
    return quote_cad(usd,p['usd_to_cad'],p['tax_margin'])


def estimate(story,p):
    image=cad(p['gen4_image_usd'],p)
    video=sum((cad(Decimal(p[s['model']+'_usd_per_second'])*5,p) for s in story['shots']),Decimal(0))
    # UTF-8 byte length is conservative for Japanese per-character TTS billing.
    audio=sum((cad(Decimal(len(s['audio']['text'].encode('utf8')))*Decimal(p['tts_usd_per_million_chars'])/1_000_000,p) for s in story['shots'] if s['audio']['text']),Decimal(0))
    base=18*image+video+audio
    retry=cad(Decimal(p['gen4_turbo_usd_per_second'])*5,p)*p['retry_video_shots']+image*p['retry_images']+cad(p['retry_audio_usd'],p)
    return dict(currency='CAD',rate=p['usd_to_cad'],tax_margin=p['tax_margin'],character_references_cad=str(6*image),keyframes_cad=str(12*image),video_cad=str(video),japanese_speech_cad=str(audio),single_5s_gen4_turbo_cad=str(cad(Decimal(p['gen4_turbo_usd_per_second'])*5,p)),base_cad=str(base),retry_allowance_cad=str(retry),conservative_cad=str(base+retry),limit_cad='18.00',within_cap=base+retry<=18,pricing_verified=verified(p),note='Illustrative until current model pricing/capabilities are verified. Retry allowance is not permission to submit retries. No funding minimums included.')


def verified(p):
    try:
        date=datetime.fromisoformat(p['verified_at']).replace(tzinfo=timezone.utc)
        age=datetime.now(timezone.utc)-date
        return p['capabilities_verified'] is True and timedelta(0)<=age<=timedelta(days=7) and bool(p['sources'])
    except (TypeError,ValueError,KeyError):
        return False


def bible_fingerprint(story):
    files={}
    for who in story['characters']:
        for view in ('front','side','full'):
            path=CHARACTERS/who/f'{view}.png'
            if not path.exists():
                raise ValueError(f'Missing Character Bible image: {path}')
            image_uri(path)
            files[f'{who}/{view}']=sha(path)
    return digest({'characters':story['characters'],'files':files})


def keyframe_fingerprint(root,story):
    return digest({'story':story,'characters':bible_fingerprint(story),'files':{s['id']:sha(root/'keyframes'/f"{s['id']}.png") for s in story['shots']}})


def test_fingerprint(root,story,shot):
    sid=f'{shot:02d}'
    return digest({'story':story,'characters':bible_fingerprint(story),'clip':sha(root/'clips'/f'{sid}.mp4'),'keyframe':sha(root/'keyframes'/f'{sid}.png')})


def write_documents(root,story,p):
    root.mkdir(parents=True,exist_ok=True)
    if not (root/'storyboard.json').exists():
        save(root/'storyboard.json',story)
    report=estimate(story,p)
    save(root/'budget_estimate.json',report)
    lines=[f"# CAMPUS LOVE — Episode 01: {story['title_zh']}",story['title_ja'],'60 seconds · 720×1280 · 12 shots · Japanese voice-over · simplified Chinese subtitles',story['style'],'## Continuity decision',story['continuity'],'## Permanent Character Bible']
    for who,c in story['characters'].items():
        lines.extend([f"### {c['name']} ({c['japanese_name']}), {c['age']}",c['personality'],c['appearance'],c['wardrobe'],c['voice']])
    lines+=['## Screenplay and shot prompts']
    for s in story['shots']:
        lines.extend([f"### Shot {s['id']} · {s['start']}–{s['start']+5}s · {s['title']}",f"Location: {s['location']} | Emotion: {s['emotion']} | Camera: {s['camera_movement']}",f"Japanese ({s['audio']['kind']}, {s['audio']['speaker']}): {s['audio']['text'] or '[ambience only]'}",f"Chinese subtitle: {s['subtitle_zh']}",f"Visual: {s['visual']}",f"Image prompt: {s['image_prompt']}",f"Motion prompt: {s['video_prompt']}",f"Post-production Japanese overlay: {s['overlay_ja'] or '[none]'}",s['review']])
    lines+=['## Budget',json.dumps(report,ensure_ascii=False,indent=2),'All real imagery, voice quality, timing and character consistency remain unverified until a real approved test. Never present a mock render as a film.']
    (root/'PRODUCTION.md').write_text('\n\n'.join(lines)+'\n',encoding='utf8')
    return report


def make_plan(action,root,story,p,state,shot=1):
    tasks=[]
    blockers=[]
    dependencies={}
    def block(message):
        if message not in blockers:
            blockers.append(message)
    if action in ('keyframes','test-shot','produce'):
        try:
            fingerprint=bible_fingerprint(story)
            dependencies['characters']=fingerprint
            if not state.approved('characters',fingerprint):
                block('Review all six reference images and run approve --asset characters')
        except (ValueError,OSError) as e:
            block(str(e))
    if action in ('test-shot','produce'):
        selected=[story['shots'][shot-1]] if action=='test-shot' else story['shots']
        for s in selected:
            path=root/'keyframes'/f"{s['id']}.png"
            if path.exists():
                dependencies[f"keyframe:{s['id']}"]=sha(path)
            else:
                block(f"Missing approved keyframe {s['id']}; run keyframes first")
        if action=='test-shot':
            try:
                frame=root/'keyframes'/f'{shot:02d}.png'
                image_uri(frame)
                fp=digest({'story':story,'characters':bible_fingerprint(story),'frame':sha(frame)})
                dependencies['test-keyframe']=fp
                if not state.approved(f'keyframe:{shot:02d}',fp):
                    block(f'Review the test keyframe and run approve --asset keyframe --shot {shot}')
            except (OSError,ValueError) as e:
                block(str(e))
        else:
            try:
                fp=keyframe_fingerprint(root,story)
                dependencies['keyframes']=fp
                if not state.approved('keyframes',fp):
                    block('Review all keyframes and run approve --asset keyframes')
            except (OSError,ValueError) as e:
                block(str(e))
        if action=='produce':
            try:
                fp=test_fingerprint(root,story,1)
                dependencies['test-shot']=fp
                if not state.approved('test-shot',fp):
                    block('Review the real 5-second test and run approve --asset test-shot')
                row=state.request('video:01')
                if not row or row['status']!='complete':
                    block('An actual completed API test shot is required')
            except (OSError,ValueError):
                block('A real test shot must be generated and approved before full production')
    if action=='characters':
        for who,c in story['characters'].items():
            for view in ('front','side','full'):
                description=f"{story['style']} {c['name']}, fictional Japanese student age {c['age']}. {c['appearance']} {c['wardrobe']}"
                instruction={'front':'Front-facing portrait, neutral background, natural expression.','side':'Side-angle portrait, exactly the same person as @identity.','full':'Full-body standing reference, exactly the same person as @identity, ordinary school attire.'}[view]
                tasks.append(dict(id=f'image:{who}:{view}',kind='image',target=str(CHARACTERS/who/f'{view}.png'),model='gen4_image',prompt=description+' '+instruction,refs=[] if view=='front' else [(str(CHARACTERS/who/'front.png'),'identity')],usd=p['gen4_image_usd']))
    elif action=='keyframes':
        for s in story['shots']:
            refs=[(str(CHARACTERS/w/'front.png'),w) for w in s['characters']]
            # Up to three documented reference images: two identities plus one full-body wardrobe.
            refs.append((str(CHARACTERS/s['characters'][0]/'full.png'),'uniform'))
            tasks.append(dict(id=f"keyframe:{s['id']}",kind='image',target=str(root/'keyframes'/f"{s['id']}.png"),model='gen4_image',prompt=s['image_prompt'],refs=refs,usd=p['gen4_image_usd']))
    elif action in ('test-shot','produce'):
        selected=[story['shots'][shot-1]] if action=='test-shot' else story['shots']
        for s in selected:
            tasks.append(dict(id=f"video:{s['id']}",kind='video',target=str(root/'clips'/f"{s['id']}.mp4"),model=s['model'],prompt=s['video_prompt'],frame=str(root/'keyframes'/f"{s['id']}.png"),usd=str(Decimal(p[s['model']+'_usd_per_second'])*5)))
        if action=='produce':
            for s in story['shots']:
                if s['audio']['text']:
                    tasks.append(dict(id=f"audio:{s['id']}",kind='audio',target=str(root/'audio'/f"{s['id']}.wav"),text=s['audio']['text'],voice=os.getenv('AOI_TTS_VOICE','nova') if s['audio']['speaker']=='aoi' else os.getenv('HARUTO_TTS_VOICE','alloy'),max_seconds=s['audio']['max_seconds'],usd=str(Decimal(len(s['audio']['text'].encode('utf8')))*Decimal(p['tts_usd_per_million_chars'])/1_000_000)))
    for task in tasks:
        if len(task.get('prompt','').encode('utf-16-le'))//2>1000:
            raise ValueError('Reference prompt exceeds documented limit')
        task['cad']=str(cad(task['usd'],p))
    costs=state.costs()
    scope={t['id'] for t in tasks}
    outside=sum((Decimal(r['actual'] if r['actual'] is not None else r['reserved'])/100 for k,r in costs.items() if k not in scope),Decimal(0))
    total=outside+sum((Decimal(costs[t['id']]['actual'] if costs[t['id']]['actual'] is not None else costs[t['id']]['reserved'])/100 if t['id'] in costs else Decimal(t['cad']) for t in tasks),Decimal(0))
    if total>18:
        block('Committed costs plus this scope exceed CAD $18')
    if not verified(p):
        block('Current pricing/capabilities are unverified. Use a verified pricing file dated within seven days.')
    # Character images are shared permanently; an existing file must never be silently overwritten.
    for task in tasks:
        if task['kind']=='image' and Path(task['target']).exists() and state.request(task['id']) is None:
            block('Existing image without provenance: import and record its cost explicitly; never overwrite permanent references')
    return dict(action=action,story_sha=digest(story),pricing=p,dependencies=dependencies,tasks=tasks,total_committed_cad=str(total),blockers=blockers,limit_cad='18.00')


def execute(plan,state):
    if Decimal(state.report()['committed_cad'])>18:
        raise ValueError('Existing committed costs exceed CAD $18; stop and reconcile')
    if plan['blockers']:
        raise ValueError('; '.join(plan['blockers']))
    if (state.root/'MOCK_ONLY').exists():
        raise ValueError('Mock output directory cannot be used for paid production')
    keys={'runway':os.getenv('RUNWAY_API_KEY'),'tts':os.getenv('OPENAI_API_KEY')}
    if not keys['runway'] or (any(t['kind']=='audio' for t in plan['tasks']) and not keys['tts']):
        raise ValueError('Missing credential: set RUNWAY_API_KEY and, for narration, OPENAI_API_KEY securely in .env')
    if os.getenv('TTS_PROVIDER','openai')!='openai' and any(t['kind']=='audio' for t in plan['tasks']):
        raise ValueError('Only the documented OpenAI TTS adapter is implemented; supply Japanese audio manually for other providers')
    ordered=sorted(plan['tasks'],key=lambda t: 0 if t['kind']=='audio' else 1)
    for task in ordered:
        if not verified(plan['pricing']):
            raise ValueError('Pricing verification expired; obtain a fresh quote before continuing')
        if task['kind']=='audio':
            payload=dict(model='tts-1',voice=task['voice'],input=task['text'],response_format='wav')
            if task['voice'] not in ('alloy','echo','fable','onyx','nova','shimmer'):
                raise ValueError('Unsupported tts-1 voice')
            speech(state,task['id'],payload,task['target'],task['cad'],keys['tts'])
            from .campus_edit import probe
            duration=float(probe(Path(task['target']))['format']['duration'])
            if duration>task['max_seconds']*1.25:
                raise ValueError('Narration exceeds its slot even at 1.25x speed; shorten it and approve any new request separately.')
        else:
            payload=dict(model=task['model'],promptText=task['prompt'],ratio='720:1280')
            if task['kind']=='image':
                if task['refs']:
                    payload['referenceImages']=[dict(uri=image_uri(path),tag=tag) for path,tag in task['refs']]
            else:
                payload.update(promptImage=image_uri(task['frame']),duration=5)
                if task['model']=='kling3.0_standard':
                    payload['audio']=False
            runway(state,task['id'],payload,task['kind'],task['target'],task['cad'],keys['runway'])
        save(state.root/'cost_report.json',state.report())


def approve_asset(args,root,story,state):
    if (root/'MOCK_ONLY').exists():
        raise ValueError('Mock footage cannot satisfy real production approval')
    if args.asset=='characters':
        fingerprint=bible_fingerprint(story)
        name='characters'
    elif args.asset=='keyframes':
        fingerprint=keyframe_fingerprint(root,story); name='keyframes'
    elif args.asset=='keyframe':
        image_uri(root/'keyframes'/f'{args.shot:02d}.png')
        fingerprint=digest({'story':story,'characters':bible_fingerprint(story),'frame':sha(root/'keyframes'/f'{args.shot:02d}.png')}); name=f'keyframe:{args.shot:02d}'
    else:
        row=state.request(f'video:{args.shot:02d}')
        if not row or row['status']!='complete' or sha(root/'clips'/f'{args.shot:02d}.mp4')!=row['asset_sha']:
            raise ValueError('Only a completed, unchanged real API clip may be approved')
        fingerprint=test_fingerprint(root,story,args.shot); name='test-shot'
    state.approve(name,fingerprint)
    print(f'Recorded human review approval: {name}. This is not permission for paid API calls.')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['preproduce','characters','keyframes','test-shot','produce','approve','render-test','edit','reconcile'])
    parser.add_argument('--episode',type=int,choices=[1],default=1)
    parser.add_argument('--shot',type=int,choices=range(1,13),default=1)
    parser.add_argument('--output',type=Path,default=ROOT/'outputs/episode_01')
    parser.add_argument('--pricing',type=Path,default=PRICING)
    parser.add_argument('--execute',action='store_true',help='Potentially paid; requires approval of exact quote hash')
    parser.add_argument('--approve-quote',default='')
    parser.add_argument('--asset',choices=['characters','keyframes','keyframe','test-shot'])
    parser.add_argument('--request-id')
    parser.add_argument('--actual-cad')
    parser.add_argument('--billing-source',default='')
    args=parser.parse_args(argv)
    load_dotenv(ROOT/'.env')
    root=args.output.resolve()
    root.mkdir(parents=True,exist_ok=True)
    with lock(root):
        state=Production(root)
        story=load_story(root)
        p=price(args.pricing)
        if args.action=='preproduce':
            report=write_documents(root,story,p)
            save(root/'cost_report.json',state.report())
            print(json.dumps(report,ensure_ascii=False,indent=2))
            print('Created:',root/'PRODUCTION.md')
        elif args.action=='approve':
            if not args.asset:
                raise ValueError('--asset is required')
            approve_asset(args,root,story,state)
        elif args.action=='reconcile':
            if not args.request_id or args.actual_cad is None:
                raise ValueError('--request-id, --actual-cad and --billing-source are required')
            state.reconcile(args.request_id,args.actual_cad,args.billing_source)
            save(root/'cost_report.json',state.report())
            print(json.dumps(state.report(),indent=2))
        elif args.action in ('render-test','edit'):
            from .campus_edit import render_test, assemble
            if args.action=='render-test':
                render_test(root,story,state)
            else:
                assemble(root,story,state,mock=False)
        else:
            plan=make_plan(args.action,root,story,p,state,args.shot)
            approval=digest(plan)
            (root/'quotes').mkdir(exist_ok=True)
            save(root/'quotes'/f'{approval}.json',plan)
            print(json.dumps(plan,ensure_ascii=False,indent=2))
            print('Approval hash:',approval)
            print('DRY RUN: no requests sent.' if not args.execute else 'Explicit paid execution requested.')
            if args.execute:
                if not args.approve_quote or args.approve_quote!=approval:
                    raise ValueError('Use --approve-quote with the exact reviewed dry-run hash. No paid requests sent.')
                try:
                    execute(plan,state)
                    if args.action=='produce':
                        from .campus_edit import assemble
                        assemble(root,story,state,mock=False)
                finally:
                    save(root/'cost_report.json',state.report())
            else:
                print('Resolve blockers, repeat dry run, obtain explicit approval, then use --execute --approve-quote HASH.')

if __name__=='__main__':
    main()
