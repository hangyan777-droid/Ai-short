from pathlib import Path
import streamlit as st
from dotenv import load_dotenv
from drama_factory.core import CHARACTERS, Character, generate_mock, plan_episode

load_dotenv()
st.set_page_config(page_title='AI Short Drama Factory', page_icon='🎬')
st.title('🎬 AI Short Drama Factory')
st.caption('60-second school romance episodes · Mock mode · CAD $0 / $18 per episode')
st.info('Mock videos use colored scene cards, timed subtitle tracks and silent audio. Paid Runway generation is disabled.')
premise = st.text_area('Story premise', 'Two final-year students connect through a forgotten sketchbook.', max_chars=500)
profiles = []
with st.expander('Reusable character profiles', expanded=True):
    for index, character in enumerate(CHARACTERS):
        name = st.text_input(f'{character.role.title()} name', character.name, key=f'name_{index}')
        description = st.text_area(f'{character.role.title()} profile', character.description, key=f'profile_{index}')
        profiles.append(Character(name, character.role, description))
if st.button('Generate Episode', type='primary'):
    try:
        with st.spinner('Planning and assembling your mock episode...'):
            episode = plan_episode(premise, tuple(profiles))
            path = generate_mock(episode, Path(__file__).parent / 'outputs')
            st.session_state['episode'] = episode
            st.session_state['video'] = str(path)
        st.success('Episode complete. Actual cost: CAD $0.00')
    except (ValueError, RuntimeError, OSError) as error:
        st.error(str(error))
if 'video' in st.session_state:
    path = Path(st.session_state['video'])
    st.subheader(st.session_state['episode'].title)
    st.video(str(path))
    st.download_button('Download episode', path.read_bytes(), 'episode.mp4', 'video/mp4')
    st.download_button('Download storyboard and character profiles', (path.parent / 'storyboard.json').read_bytes(), 'storyboard.json', 'application/json')
    st.download_button('Download captions', (path.parent / 'captions.srt').read_bytes(), 'captions.srt')
    for scene in st.session_state['episode'].scenes:
        st.write(f'**{scene.title} · {scene.seconds}s** — {scene.action}')
