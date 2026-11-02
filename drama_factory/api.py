import json
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from .core import CHARACTERS, Character
from .store import Store
from .production import create_job, produce

load_dotenv()
store = Store(os.getenv('CAMPUS_DATA_DIR', 'data'))

@asynccontextmanager
async def lifespan(app):
    # Run one API worker per database. Recovery never submits paid requests.
    with store.connection() as db:
        db.execute("UPDATE jobs SET status='failed',error='Interrupted; resume to continue' WHERE status='running'")
        for c in CHARACTERS:
            profile = dict(name=c.name, role=c.role, hairstyle=c.description, facial_features='', clothing='', voice='Gentle youthful voice', reference_image='', description=c.description)
            db.execute('INSERT OR IGNORE INTO characters VALUES(?,?)', (c.role,json.dumps(profile)))
    yield

app = FastAPI(title='Campus Drama Factory', lifespan=lifespan)

class Profile(BaseModel):
    name: str = Field(min_length=1,max_length=100)
    role: str = Field(min_length=1,max_length=100)
    description: str = Field(min_length=1,max_length=2000)
    hairstyle: str = ''
    facial_features: str = ''
    clothing: str = ''
    voice: str = ''
    reference_image: str = ''

class EpisodeRequest(BaseModel):
    premise: str = Field(min_length=1,max_length=500)
    mode: Literal['mock'] = 'mock'

class Review(BaseModel):
    review: Literal['pending','approved','inconsistent']

@app.get('/health')
def health():
    return {'status':'ok','mode':'mock','paid_enabled':False}

@app.get('/characters')
def characters():
    with store.connection() as db:
        return [dict(id=r['id'], **json.loads(r['profile'])) for r in db.execute('SELECT * FROM characters ORDER BY id')]

@app.post('/characters')
def save_character(profile: Profile):
    with store.connection() as db:
        db.execute('INSERT INTO characters VALUES(?,?) ON CONFLICT(id) DO UPDATE SET profile=excluded.profile', (profile.role,json.dumps(profile.model_dump())))
    return {'id':profile.role}

@app.get('/jobs')
def jobs():
    with store.connection() as db:
        ids = [r[0] for r in db.execute('SELECT id FROM jobs ORDER BY rowid DESC LIMIT 50')]
    return [store.job(i) for i in ids]

@app.get('/jobs/{job}')
def get_job(job: str):
    try:
        return store.job(job)
    except KeyError:
        raise HTTPException(404,'Job not found')

@app.post('/jobs',status_code=202)
def new_job(request: EpisodeRequest, background: BackgroundTasks):
    profiles = {p['role']:p for p in characters()}
    selected = tuple(Character(profiles[c.role]['name'],c.role,profiles[c.role]['description']) for c in CHARACTERS)
    try:
        job = create_job(store,request.premise,selected)
    except ValueError as error:
        raise HTTPException(422,str(error))
    background.add_task(produce,store,job)
    return {'id':job}

@app.post('/jobs/{job}/resume',status_code=202)
def resume(job: str, background: BackgroundTasks):
    current = get_job(job)
    if current['status'] not in ('failed','queued'):
        raise HTTPException(409,'Only failed or queued jobs can resume')
    background.add_task(produce,store,job)
    return {'id':job}

@app.post('/jobs/{job}/shots/{index}/review')
def review(job: str,index: int, body: Review):
    get_job(job)
    with store.connection() as db:
        if not db.execute('UPDATE shots SET review=? WHERE job=? AND idx=?',(body.review,job,index)).rowcount:
            raise HTTPException(404,'Shot not found')
    return {'review':body.review}

@app.get('/jobs/{job}/assets/{asset}')
def asset(job: str,asset: str):
    get_job(job)
    allowed = ['portrait.mp4','landscape.mp4','storyboard.json','captions.srt'] + [f'shot_{i}.mp4' for i in range(6)]
    if asset not in allowed:
        raise HTTPException(404,'Unknown asset')
    path = store.root / job / asset
    if not path.is_file():
        raise HTTPException(404,'Asset not ready')
    return FileResponse(path,filename=asset)
