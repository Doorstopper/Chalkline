"""Explicit integration check; outputs stay in a separate test-results directory."""
import argparse
import json
from pathlib import Path
import subprocess
import time

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage
from chalkline.domain.project import new_project, save_project
from chalkline.infrastructure.exporter import Exporter, ExportCancelled
from chalkline.infrastructure.media import probe, process_options
from chalkline.rendering.annotations import overlay_image, ensure_fonts
from chalkline.rendering.text_layout import place_notes, measure_text
from chalkline.domain.markup import make_shape, point
from chalkline.domain.timing_edits import drag_timing

parser=argparse.ArgumentParser()
parser.add_argument('--root',type=Path,required=True)
parser.add_argument('--source',type=Path,required=True)
parser.add_argument('--markup',action='store_true',help='Include all seven native drawing tools in the 4K proof')
parser.add_argument('--timing-drag',action='store_true',help='Export a moved freeze and shortened slow section')
args=parser.parse_args()
app=QApplication([])
ensure_fonts()
result_root=args.root/'test-results'/time.strftime('%Y%m%d-%H%M%S')
result_root.mkdir(parents=True)
exporter=Exporter(args.root, progress=lambda p,m: print(f'{p:.0%} {m}',flush=True) if p>=.95 else None)
source=probe(args.source,exporter.ffprobe)
mark={'id':'native-proof','t':3,'pre':1,'post':2,'label':'Native 4K proof',
      'caption':'Native 4K • freeze + half speed',
      'shapes':[{'tool':'arrow','a':{'x':.2,'y':.3},'b':{'x':.5,'y':.5},'t':3,'linger':0,'color':'space'}],
      'freezes':[{'at':3,'hold':1}], 'slow':[{'from':3,'to':4,'rate':.5}]}
settings={'hold':1,'autoFreeze':True,'burnAll':False}
# Exercise preset re-placement through the actual 4K encoded overlay path.
note={'tool':'text','_notes':True,'text':'Keep space','fs':19,'a':{'x':.04,'y':.06},
      't':3,'linger':0,'color':'space'}
place_notes(note,2,0,3840,2160)
note['fs']=48
place_notes(note,2,0,3840,2160)
assert measure_text(note,3840).lines==['Keep space']
mark['shapes'].append(note)
if args.markup:
    for tool,a,b,color in [
        ('line',point(.1,.18),point(.35,.18),'path'),
        ('circle',point(.55,.3),point(.68,.5),'ours'),
        ('pen',point(.1,.62),point(.4,.72),'theirs'),
        ('zone',point(.55,.62),point(.7,.78),'space'),
        ('ground',point(.85,.65),point(.89,.65),'ball'),
    ]:
        mark['shapes'].append(make_shape(tool,a,b,3,color,points=[a,point(.2,.55),point(.3,.75),b]))
    settings['lineWt']=1.5
expected_duration=5
if args.timing_drag:
    mark=drag_timing(mark,'freezes',0,'at',3.5,0,float(source.duration))
    mark=drag_timing(mark,'slow',0,'to',3.4,0,float(source.duration))
    # 3 source seconds + .4 extra slow seconds + two independent 1-second holds.
    expected_duration=5.4
destination=result_root/'native-proof-4K.mp4'
exporter.export(args.source,mark,0,settings,destination)
info=probe(destination,exporter.ffprobe)
assert (info.width,info.height)==(3840,2160)
assert info.fps==source.fps
assert abs(info.duration-expected_duration)<.25,(info.duration,expected_duration)
assert info.audio
# Decode ALL output frames: container metadata alone cannot prove a usable export.
subprocess.run([exporter.ffmpeg,'-v','error','-i',str(destination),'-f','null','-'],check=True,**process_options())
for name,video,at in [('source',args.source,3),('freeze',destination,1.5),('motion',destination,3.5)]:
    path=result_root/f'{name}.png'
    subprocess.run([exporter.ffmpeg,'-v','error','-y','-ss',str(at),'-i',str(video),'-frames:v','1',str(path)],check=True,**process_options())
    image=QImage(str(path))
    assert not image.isNull()
    sample=image.scaled(96,54)
    brightness=sum(sample.pixelColor(x,y).lightness() for x in range(96) for y in range(54))/(96*54)
    assert brightness>5,(name,brightness)
overlay_image(3840,2160,mark,3,settings,True).save(str(result_root/'overlay.png'))
# Verify a no-audio source receives a consistent silent audio stream.
silent=result_root/'silent-source.mp4'
subprocess.run([exporter.ffmpeg,'-v','error','-y','-f','lavfi','-i','testsrc2=size=320x180:rate=30000/1001',
                '-t','1','-c:v','libx264','-pix_fmt','yuv420p',str(silent)],check=True,**process_options())
silent_export=result_root/'silent-export.mp4'
exporter.export(silent,{'t':.3,'pre':.3,'post':.3,'shapes':[]},0,{},silent_export,require_4k=False)
assert probe(silent_export,exporter.ffprobe).audio
assert str(probe(silent_export,exporter.ffprobe).fps)=='30000/1001'
# Reject unsupported annotations, overwrite, lower-resolution "4K", and cancellation.
for candidate,src,target in [({**mark,'shapes':[{'tool':'wedge'}]},args.source,result_root/'unsupported.mp4'),
                            (mark,args.source,destination),(mark,silent,result_root/'upscaled.mp4')]:
    try:
        exporter.export(src,candidate,0,settings,target)
        raise AssertionError('Expected export rejection')
    except (ValueError,FileExistsError):
        pass
exporter.stop()
try:
    exporter.export(args.source,mark,0,settings,result_root/'cancelled.mp4')
    raise AssertionError('Expected cancellation')
except ExportCancelled:
    pass
project=new_project()
project['media']={'path':str(args.source)}
project['session']['marks']=[mark]
project['session']['lineWt']=settings.get('lineWt',1)
project['settings']=settings
save_project(project,result_root/'Native proof.chalkline')
summary={'source':str(args.source),'export':str(destination),'width':info.width,'height':info.height,
         'fps':str(info.fps),'duration':info.duration,'decode':'all frames passed','blackFrames':'sampled source/freeze/motion passed',
         'silentSource':'passed','fractionalFps':'passed','guardrails':'passed'}
summary['notesPlacement']='resized top-right note remains one line at 3840x2160'
(result_root/'verification.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps(summary,indent=2),flush=True)
