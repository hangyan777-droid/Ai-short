"""Resumable local production. No network providers are invoked."""
import json
import uuid
from dataclasses import asdict
from .core import CHARACTERS, plan_episode, run


def create_job(store, premise, characters=None):
    episode = plan_episode(premise, characters or CHARACTERS)
    board = asdict(episode)
    for index, shot in enumerate(board['scenes']):
        shot.update(dialogue=shot['caption'], character_refs=[c.name for c in episode.characters], environment='School corridor and courtyard', camera_movement='Slow cinematic push-in', model='mock', consistency_review='Human review required', beat=['hook','connection','progression','twist','resolution','ending'][index])
    job = uuid.uuid4().hex
    with store.connection() as db:
        db.execute('INSERT INTO jobs VALUES(?,?,?,NULL)', (job, 'queued', json.dumps(board)))
        db.executemany('INSERT INTO shots(job,idx,status) VALUES(?,?,?)', [(job, i, 'pending') for i in range(6)])
    return job


def produce(store, job):
    # Atomic claim prevents double workers. A stale interrupted job is explicitly resumed.
    with store.connection() as db:
        claimed = db.execute("UPDATE jobs SET status='running',error=NULL WHERE id=? AND status IN ('queued','failed')", (job,)).rowcount
    if not claimed:
        return
    folder = store.root / job
    folder.mkdir(exist_ok=True)
    try:
        board = store.job(job)['storyboard']
        colors = ['27374d','526d82','66545e','354f52','7f5539','52796f']
        for index, scene in enumerate(board['scenes']):
            target = folder / f'shot_{index}.mp4'
            state = store.job(job)['shots'][index]
            if state['status'] == 'complete' and target.exists():
                continue
            store.reserve(job, f'mock-{index}', 0)
            temp = folder / f'shot_{index}.partial.mp4'
            run(['ffmpeg','-v','error','-y','-f','lavfi','-i',f'color=c=0x{colors[index]}:s=360x640:r=24:d=10','-c:v','libx264','-preset','ultrafast','-pix_fmt','yuv420p',str(temp)])
            temp.replace(target)
            with store.connection() as db:
                db.execute("UPDATE shots SET status='complete' WHERE job=? AND idx=?", (job,index))
                db.execute('UPDATE costs SET actual=0 WHERE job=? AND request_id=?', (job,f'mock-{index}'))
        captions = []
        for index, scene in enumerate(board['scenes']):
            def stamp(seconds):
                return f'00:{seconds//60:02d}:{seconds%60:02d},000'
            captions.append(f"{index+1}\n{stamp(index*10)} --> {stamp((index+1)*10)}\n{scene['caption']}\n")
        (folder / 'captions.srt').write_text('\n'.join(captions), encoding='utf-8')
        (folder / 'storyboard.json').write_text(json.dumps(board,ensure_ascii=False,indent=2),encoding='utf-8')
        (folder / 'clips.txt').write_text(''.join(f"file 'shot_{i}.mp4'\n" for i in range(6)))
        for aspect in ('portrait','landscape'):
            temp = folder / f'{aspect}.partial.mp4'
            cmd = ['ffmpeg','-v','error','-y','-f','concat','-safe','1','-i',str(folder/'clips.txt'),'-f','lavfi','-i','anullsrc=r=48000:cl=stereo','-i',str(folder/'captions.srt'),'-map','0:v','-map','1:a','-map','2:s']
            if aspect == 'landscape':
                cmd += ['-vf','scale=202:360,pad=640:360:(ow-iw)/2:(oh-ih)/2','-c:v','libx264','-preset','ultrafast']
            else:
                cmd += ['-c:v','copy']
            run(cmd + ['-c:a','aac','-c:s','mov_text','-t','60','-movflags','+faststart',str(temp)])
            temp.replace(folder / f'{aspect}.mp4')
        with store.connection() as db:
            db.execute("UPDATE jobs SET status='complete' WHERE id=?", (job,))
    except Exception as error:
        with store.connection() as db:
            db.execute("UPDATE jobs SET status='failed',error=? WHERE id=?", (str(error),job))
