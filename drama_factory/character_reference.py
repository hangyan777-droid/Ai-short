"""Character-only art direction and an offline review sheet. No network calls."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

LOOK = ('Photorealistic Japanese live-action coming-of-age film reference. Fictional person, '
        'not a celebrity likeness. Natural skin pores, soft window daylight, restrained warm color, '
        'quiet expression. No anime, idol styling, beauty filter, skin smoothing, logos or text. ')


def prompt(who, character, view):
    identity = {
        'haruto': ('Haruto Sato, a fictional 17-year-old Japanese schoolboy. Soft black layered hair '
                   'with a natural fringe, dark-brown eyes, natural youthful facial proportions, '
                   'slim build, gentle slightly shy expression. White short-sleeve school shirt, '
                   'navy straight-leg trousers, plain white sneakers; no accessories. '),
        'aoi': ('Aoi Nakamura, a fictional 17-year-old Japanese schoolgirl. Straight dark hair with '
                'soft bangs, dark-brown eyes, natural youthful facial proportions, no visible makeup, '
                'warm observant expression. White school blouse, loose ivory knit cardigan, navy '
                'knee-length pleated skirt, white socks, brown loafers. '),
    }[who]
    # Use one summer wardrobe per reference set; graduation variants are separate shot instructions.
    view_text = {
        'front': ('Front-facing head-and-shoulders portrait, eye-level 85mm-style lens, both ears '
                  'where visible, hair fully in frame, pale neutral background, relaxed closed mouth. '
                  'Recognizable natural face, simple framing, vertical 9:16.'),
        'side': ('Use @identity as the identity reference: the same face, hairline, age and outfit. '
                 'True left-side profile, head and shoulders, eye-level lens, nose and ear silhouette '
                 'clear, pale neutral background, relaxed closed mouth, vertical 9:16.'),
        'full': ('Use @identity as the identity reference: the same face, hair, age and outfit. '
                 'Head-to-toe front-facing standing reference, eye-level 50mm-style lens, ordinary '
                 'school posture, arms at sides with hands visible, both shoes fully in frame, '
                 'pale neutral background, vertical 9:16.'),
    }[view]
    if character['name'] not in ('Haruto Sato','Aoi Nakamura') or character['age'] != 17:
        raise ValueError('Character identity changed; revise the reference prompts before quoting')
    result=LOOK+identity+view_text
    if len(result.encode('utf-16-le'))//2>1000:
        raise ValueError('Reference prompt exceeds the documented API length limit')
    return result


def review_sheet(characters_root, destination):
    """Show only existing real reference files; never invent preview portraits."""
    characters_root=Path(characters_root)
    destination=Path(destination)
    sheet=Image.new('RGB',(720,1000),'#f1f0eb')
    draw=ImageDraw.Draw(sheet)
    try:
        font=ImageFont.load_default(size=22)
    except TypeError:
        font=ImageFont.load_default()
    for row,who in enumerate(('haruto','aoi')):
        for col,view in enumerate(('front','side','full')):
            source=characters_root/who/f'{view}.png'
            if not source.is_file():
                raise ValueError(f'Missing {source}; a review sheet needs all six generated images')
            with Image.open(source) as image:
                picture=image.convert('RGB')
                picture.thumbnail((220,430))
            x=col*240+(240-picture.width)//2
            y=row*500+45
            sheet.paste(picture,(x,y))
            draw.text((col*240+10,row*500+10),f'{who.title()} - {view}',fill='black',font=font)
    destination.parent.mkdir(parents=True,exist_ok=True)
    sheet.save(destination)
    return destination
