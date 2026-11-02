import os
import httpx
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
API = os.getenv('CAMPUS_API_URL','http://127.0.0.1:8000').rstrip('/')
st.set_page_config(page_title='Campus Drama Factory',page_icon='🎬',layout='wide')
st.title('🎬 Campus Drama Factory')
st.caption('Innocent school romance · 60 seconds · CAD $18 maximum · Free mock mode')
st.info('Local test footage only. OpenAI, Runway and TTS calls are disabled. No credits are spent.')

def request(method,path,**kwargs):
    response = httpx.request(method,API+path,timeout=30,**kwargs)
    response.raise_for_status()
    return response

try:
    request('GET','/health')
    library, production = st.tabs(['Character Library','Episode Production'])
    with library:
        for profile in request('GET','/characters').json():
            with st.form(profile['id']):
                st.subheader(profile['role'].title())
                fields = {}
                for key in ('name','description','hairstyle','facial_features','clothing','voice','reference_image'):
                    fields[key] = st.text_input(key.replace('_',' ').title(),profile.get(key,''),key=profile['id']+key)
                st.caption('Reference image: local path or URL metadata only; mock mode does not fetch images.')
                if st.form_submit_button('Save Profile'):
                    request('POST','/characters',json={**fields,'role':profile['role']})
                    st.success('Saved to SQLite')
    with production:
        premise = st.text_area('Story premise','A forgotten sketchbook brings two students together.',max_chars=500)
        if st.button('Generate New Episode',type='primary'):
            result = request('POST','/jobs',json={'premise':premise}).json()
            st.session_state['selected_job'] = result['id']
            st.success('Production queued. Refresh progress to inspect it.')
        st.button('Refresh Progress')
        jobs = request('GET','/jobs').json()
        if jobs:
            ids = [j['id'] for j in jobs]
            selected = st.selectbox('Production jobs',ids,index=ids.index(st.session_state.get('selected_job')) if st.session_state.get('selected_job') in ids else 0)
            job = request('GET',f'/jobs/{selected}').json()
            st.write('Status:',job['status'])
            st.progress(sum(s['status']=='complete' for s in job['shots'])/6)
            st.subheader('Production Cost')
            st.json(job['cost'])
            if job['error']:
                st.error(job['error'])
            if job['status'] in ('failed','queued') and st.button('Resume Production'):
                request('POST',f'/jobs/{selected}/resume')
                st.rerun()
            with st.expander('Script and Storyboard Preview'):
                st.json(job['storyboard'])
            st.subheader('Per-Shot Review')
            for shot in job['shots']:
                i = shot['idx']
                with st.expander(f"Shot {i+1}: {shot['status']} · {shot['review']}"):
                    st.write(job['storyboard']['scenes'][i])
                    st.selectbox('Model',['mock'],key=f'{selected}-{i}-model')
                    st.caption('Paid model selection and automatic consistency detection are not enabled.')
                    if shot['status']=='complete':
                        st.video(request('GET',f'/jobs/{selected}/assets/shot_{i}.mp4').content)
                    review = st.selectbox('Visual consistency',['pending','approved','inconsistent'],index=['pending','approved','inconsistent'].index(shot['review']),key=f'{selected}-{i}-review')
                    if st.button('Save Review',key=f'{selected}-{i}-save'):
                        request('POST',f'/jobs/{selected}/shots/{i}/review',json={'review':review})
                        st.rerun()
            if job['status']=='complete':
                st.subheader('Export Final Video')
                for aspect in ('portrait','landscape'):
                    video = request('GET',f'/jobs/{selected}/assets/{aspect}.mp4').content
                    st.download_button(f'Download {aspect} MP4',video,f'{aspect}.mp4','video/mp4')
                st.video(request('GET',f'/jobs/{selected}/assets/portrait.mp4').content)
                for asset in ('captions.srt','storyboard.json'):
                    st.download_button(f'Download {asset}',request('GET',f'/jobs/{selected}/assets/{asset}').content,asset)
except (httpx.HTTPError,ValueError) as error:
    st.error(f'Backend unavailable or request rejected: {error}')
    st.code('python -m uvicorn drama_factory.api:app --host 127.0.0.1 --port 8000')
