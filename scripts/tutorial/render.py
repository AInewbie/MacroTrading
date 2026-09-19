"""Add readable instructional captions without changing the recorded dashboard."""
from pathlib import Path
import json, subprocess

out=Path('tutorial-output')
timeline=json.loads((out/'timeline.json').read_text())
def ass_time(s):
    h=int(s//3600);m=int(s%3600//60);seconds=s%60
    return f'{h}:{m:02}:{seconds:05.2f}'
def srt_time(s):
    ms=round(s*1000);return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'
def clean(s):return s.replace('\\','/').replace('{','(').replace('}',')').replace('\n',' ')
ass='''[Script Info]
ScriptType: v4.00+
PlayResX: 1600
PlayResY: 900
WrapStyle: 0
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,DejaVu Sans,25,&H00FFFFFF,&H00FFFFFF,&H001B2D40,&H001B2D40,0,0,0,0,100,100,0,0,1,0,0,2,60,60,14,1
Style: Chapter,DejaVu Sans,14,&H00C4D176,&H00C4D176,&H001B2D40,&H001B2D40,-1,0,0,0,100,100,0,0,1,0,0,7,30,30,809,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
srt=[];chapters=[];last=None
for n,row in enumerate(timeline['scenes'],1):
    start,end=ass_time(row['start']),ass_time(row['end'])
    ass+=f'Dialogue: 0,{start},{end},Chapter,,0,0,0,,{clean(row["chapter"])}\n'
    ass+=f'Dialogue: 1,{start},{end},Caption,,0,0,0,,{clean(row["text"])}\n'
    srt.append(f'{n}\n{srt_time(row["start"])} --> {srt_time(row["end"])}\n{row["text"]}\n')
    if row['chapter']!=last:chapters.append(f'{int(row["start"]//60):02}:{int(row["start"]%60):02} {row["chapter"]}');last=row['chapter']
(out/'captions.ass').write_text(ass)
(out/'MacroTrading-Dashboard-Tutorial.srt').write_text('\n'.join(srt))
(out/'chapters.txt').write_text('MacroTrading v0.5 — captioned screen recording\nSynthetic demonstration data; no live trades or paid AI calls.\n\n'+'\n'.join(chapters)+'\n')
filters=['pad=iw:900:0:0:color=0x102840']
for b in timeline['highlights']:
    x=max(0,int(b['x'])-3);y=max(0,int(b['y'])-3);w=min(1600-x,int(b['width'])+6);h=min(800-y,int(b['height'])+6)
    if w>0 and h>0:filters.append(f"drawbox=x={x}:y={y}:w={w}:h={h}:color=0x26b6a5@0.9:t=3:enable='between(t,{b['start']:.3f},{b['end']:.3f})'")
filters.append('ass=tutorial-output/captions.ass')
subprocess.run(['ffmpeg','-y','-loglevel','warning','-i',str(out/'raw.mp4'),'-vf',','.join(filters),'-c:v','libx264','-preset','medium','-crf','22','-pix_fmt','yuv420p','-movflags','+faststart','-an',str(out/'MacroTrading-Dashboard-Tutorial.mp4')],check=True)
subprocess.run(['ffmpeg','-y','-loglevel','warning','-ss','12','-i',str(out/'MacroTrading-Dashboard-Tutorial.mp4'),'-frames:v','1',str(out/'poster.jpg')],check=True)
probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(out/'MacroTrading-Dashboard-Tutorial.mp4')]))
assert probe['streams'][0]['width']==1600 and probe['streams'][0]['height']==900
assert float(probe['format']['duration'])>150
print('MP4 verified:',probe['format']['duration'],'seconds;',probe['format']['size'],'bytes')
