"""Local 60-second edit with Japanese voice slots and simplified Chinese subtitles."""
import json
import math
from pathlib import Path
import random
import shlex
import struct
import subprocess
import wave
from .film import music, save
from .campus_state import sha


def run(root,args):
    with (root/'rendering.log').open('a',encoding='utf8') as log:
        log.write('\n'+shlex.join(args)+'\n'); log.flush()
        result=subprocess.run(args,cwd=root,stdout=log,stderr=log)
    if result.returncode:
        raise RuntimeError(f'FFmpeg failed. See {root / "rendering.log"}')


def probe(path):
    result=subprocess.run(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(path)],check=True,capture_output=True,text=True)
    return json.loads(result.stdout)


def ass_stamp(sec):
    return f'{sec//3600}:{sec//60%60:02d}:{sec%60:02d}.00'


def escape(text):
    return text.replace('\\','＼').replace('{','（').replace('}','）').replace('\n','\\N')


def subtitles(root,story,mock):
    header='''[Script Info]
ScriptType: v4.00+
PlayResX: 720
PlayResY: 1280
WrapStyle: 0
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Chinese,Noto Sans CJK SC,38,&H00FFFFFF,&H00FFFFFF,&H00202020,&H80000000,0,0,0,0,100,100,0,0,1,2,1,2,40,40,110,1
Style: Japanese,Noto Sans CJK JP,30,&H00FFFFFF,&H00FFFFFF,&H00202020,&H80000000,0,0,0,0,100,100,0,0,1,2,1,8,40,40,150,1
Style: Title,Noto Sans CJK SC,34,&H00FFFFFF,&H00FFFFFF,&H00202020,&H80000000,0,0,0,0,100,100,0,0,1,2,1,8,40,40,60,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    lines=[header]
    srt=[]
    def stamp(s): return f'00:{s//60:02d}:{s%60:02d},000'
    for i,s in enumerate(story['shots'],1):
        start,end=s['start'],s['start']+5
        lines.append(f"Dialogue: 0,{ass_stamp(start)},{ass_stamp(end)},Chinese,,0,0,0,,{escape(s['subtitle_zh'])}\n")
        if s['overlay_ja']:
            lines.append(f"Dialogue: 0,{ass_stamp(start)},{ass_stamp(end-1 if i==12 else end)},Japanese,,0,0,0,,{escape(s['overlay_ja'])}\n")
        srt.append(f"{i}\n{stamp(start)} --> {stamp(end)}\n{s['subtitle_zh']}\n")
    lines.append(f"Dialogue: 0,0:00:00.00,0:00:03.00,Title,,0,0,0,,{escape(story['title_zh'])}\n")
    if mock:
        lines.append('Dialogue: 1,0:00:00.00,0:01:00.00,Japanese,,0,0,30,,PIPELINE TEST — NOT AI FOOTAGE / NO REAL VOICE\n')
    (root/'subtitles.ass').write_text(''.join(lines),encoding='utf8')
    (root/'subtitles.zh.srt').write_text('\n'.join(srt),encoding='utf8')


def local_audio(root,story):
    folder=root/'audio'; folder.mkdir(exist_ok=True)
    if not (folder/'original_score.wav').exists():
        music(folder/'original_score.wav')
    rate=22050
    rng=random.Random(1)
    output=bytearray()
    for i in range(rate*60):
        t=i/rate
        kind=story['shots'][min(11,int(t//5))]['ambience']
        if kind=='rain':
            value=rng.uniform(-1,1)*.13
        elif kind=='footsteps':
            phase=t%.6
            value=math.sin(2*math.pi*100*phase)*math.exp(-45*phase)*.2
        elif kind=='classroom_cicadas':
            value=math.sin(2*math.pi*3700*t)*(.5+.5*math.sin(2*math.pi*7*t))*.025
        else:
            value=rng.uniform(-1,1)*.008
        output.extend(struct.pack('<h',int(value*32767)))
    with wave.open(str(folder/'ambience.wav'),'wb') as file:
        file.setparams((1,2,rate,0,'NONE','not compressed')); file.writeframes(output)


def assemble(root,story,state,mock=False):
    root=Path(root).resolve()
    if bool((root/'MOCK_ONLY').exists())!=mock:
        raise ValueError('Mock and real rendering must use separate directories')
    if not mock:
        from .campus import bible_fingerprint,keyframe_fingerprint,test_fingerprint
        if not state.approved('characters',bible_fingerprint(story)) or not state.approved('keyframes',keyframe_fingerprint(root,story)):
            raise ValueError('Character Bible and keyframes need current human approval')
        if not state.approved('test-shot',test_fingerprint(root,story,1)):
            raise ValueError('The first real test shot must be approved')
        for s in story['shots']:
            for rid,target in [(f"video:{s['id']}",root/'clips'/f"{s['id']}.mp4")]+([(f"audio:{s['id']}",root/'audio'/f"{s['id']}.wav")] if s['audio']['text'] else []):
                row=state.request(rid)
                if not row or row['status']!='complete' or not target.is_file() or sha(target)!=row['asset_sha']:
                    raise ValueError(f'{rid}: only unchanged real provider assets can enter final output')
    normalized=root/'normalized'; normalized.mkdir(exist_ok=True)
    for s in story['shots']:
        sid=s['id']; source=root/'clips'/f'{sid}.mp4'
        info=probe(source)
        video=next(v for v in info['streams'] if v['codec_type']=='video')
        if float(info['format']['duration'])<4.99 or (not mock and (video['width']<720 or video['height']<1280)):
            raise ValueError('Shot must be at least five seconds and 720p portrait; no automatic upscaling')
        run(root,['ffmpeg','-v','error','-y','-i',str(source),'-vf','scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,setsar=1,fps=24','-an','-t','5','-c:v','libx264','-threads','2','-preset','ultrafast','-pix_fmt','yuv420p',str(normalized/f'{sid}.mp4')])
        voice=root/'audio'/f'{sid}.wav'
        dest=normalized/f'{sid}.wav'
        if s['audio']['text']:
            audio=probe(voice)
            if not any(v['codec_type']=='audio' for v in audio['streams']):
                raise ValueError('TTS file has no audio')
            duration=float(audio['format']['duration'])
            factor=max(1,duration/s['audio']['max_seconds'])
            if factor>1.25:
                raise ValueError(f'Shot {sid} Japanese narration too long. Shorten script or provide a reviewed shorter recording; do not automatically pay for another TTS request.')
            chain=f"atempo={factor},adelay={int(s['audio']['start_offset']*1000)},apad,atrim=duration=5,aresample=48000"
            run(root,['ffmpeg','-v','error','-y','-i',str(voice),'-af',chain,'-ac','1',str(dest)])
        else:
            run(root,['ffmpeg','-v','error','-y','-f','lavfi','-i','anullsrc=r=48000:cl=mono','-t','5',str(dest)])
    (normalized/'video.txt').write_text(''.join(f"file '{s['id']}.mp4'\n" for s in story['shots']))
    (normalized/'voice.txt').write_text(''.join(f"file '{s['id']}.wav'\n" for s in story['shots']))
    run(root,['ffmpeg','-v','error','-y','-f','concat','-safe','1','-i',str(normalized/'voice.txt'),'-c:a','pcm_s16le',str(root/'audio/narration_timeline.wav')])
    local_audio(root,story)
    subtitles(root,story,mock)
    name='pipeline_test_9x16.mp4' if mock else 'final_9x16.mp4'
    temp=root/('pipeline_test_9x16.partial.mp4' if mock else 'final_9x16.partial.mp4')
    run(root,['ffmpeg','-v','error','-y','-f','concat','-safe','1','-i',str(normalized/'video.txt'),'-i',str(root/'audio/narration_timeline.wav'),'-i',str(root/'audio/original_score.wav'),'-i',str(root/'audio/ambience.wav'),'-filter_complex',"[0:v]ass=subtitles.ass,fade=t=out:st=59:d=1[v];[1:a]volume=1[voice];[2:a]volume=0.22[music];[3:a]volume=0.3[amb];[voice][music][amb]amix=inputs=3:normalize=0,alimiter=limit=0.95:latency=1,afade=t=out:st=58:d=2[a]",'-map','[v]','-map','[a]','-t','60','-c:v','libx264','-threads','2','-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-ar','48000','-movflags','+faststart',str(temp)])
    info=probe(temp)
    video=next(s for s in info['streams'] if s['codec_type']=='video')
    if (video['width'],video['height'])!=(720,1280) or abs(float(info['format']['duration'])-60)>.04:
        raise ValueError('Final output does not meet duration/resolution requirements')
    run(root,['ffmpeg','-v','error','-i',str(temp),'-f','null','-'])
    temp.replace(root/name)
    save(root/'cost_report.json',state.report())
    save(root/'render_manifest.json',dict(mode='mock' if mock else 'real',output=name,duration=info['format']['duration'],resolution=[720,1280],sha256=sha(root/name),review='Real film still requires human visual/audio/Chinese subtitle review; no perfect consistency claim.'))
    print('Rendered:',root/name)


def render_test(root,story,state):
    if state.costs() or any((root/'clips').glob('*.mp4')) and not (root/'MOCK_ONLY').exists():
        raise ValueError('Use a separate empty output directory for pipeline testing; never overwrite real assets')
    (root/'MOCK_ONLY').touch()
    save(root/'storyboard.json',story)
    (root/'clips').mkdir(exist_ok=True); (root/'audio').mkdir(exist_ok=True)
    for i,s in enumerate(story['shots']):
        path=root/'clips'/f"{s['id']}.mp4"
        run(root,['ffmpeg','-v','error','-y','-f','lavfi','-i',f'color=c=0x{["9caa9b","c3b8a3","697c87"][i%3]}:s=720x1280:r=24:d=5','-c:v','libx264','-threads','2','-preset','ultrafast','-pix_fmt','yuv420p',str(path)])
        if s['audio']['text']:
            # Timing-only tone; explicitly not Japanese narration.
            run(root,['ffmpeg','-v','error','-y','-f','lavfi','-i','sine=frequency=440:duration=1','-af','volume=0.1',str(root/'audio'/f"{s['id']}.wav")])
    assemble(root,story,state,mock=True)
