# Kit demo: the knuckle script rebuilt from layers (about 70 lines instead of 430). Every time comes from at("word").
from kit import *

def build():
    return [
        Scene(0, bg=YEL, trans="auto", layers=[
            Narrator(y=1335, s=1.6, pose=dict(hl=(-150, -318), hr=(150, -318)), smile=0.7),
            Headline("THAT CRACK ISN'T", 0.0, y=175, size=92), Headline("YOUR BONES", at("bones"), y=300, size=126, fill=RED),
            Starburst("CRACK!", at("crack"), 820, 760, 190, hold=0.55), Burst(at("crack"), 540, 800, sfx="crack"),
            Prop(bone_prop, at("bones"), 850, 560, 0.95, 24), Mark("cross", at("bones", off=0.1), 850, 560, sfx=None)]),
        Scene(at("pull"), bg="#CDB4DB", trans="auto", layers=[
            Narrator(y=1290, s=1.5, pose="wide"),
            Tag("KNUCKLE JOINT", at("knuckle"), y=320, size=72, fill=WHITE), Tag("TINY GAP", at("tiny"), y=420, size=58, fill=YEL, T1=at("fluid")),
            Tag("JOINT FLUID", at("fluid"), y=520, size=58, fill="#7CC6FF"),
            Starburst("POP!", at("pop"), 740, 700, 175, hold=0.9), Burst(at("pop"), 540, 800)]),
        Scene(at("it took"), bg="#B8F2C9", trans="auto", layers=[
            Narrator(y=1290, s=1.5, pose="point"), BigNumber(2015, at("2015"), fmt="{}", size=190, dur=0.6),
            Tag("MRI", at("mri"), x=835, y=420, size=78, fill=YEL, rot=8)]),
        Scene(at("so does"), bg="#FF8FA3", trans="auto", layers=[
            Narrator(y=1320, s=1.6, pose="worry", brow=-0.5, sweat=0.8, smile=-0.3), QMarks(at("does")),
            Headline("ARTHRITIS?", at("arthritis"), y=265, size=150, fill=RED, rot=-3), Burst(at("arthritis"), 540, 265)]),
        Scene(at("one doctor"), bg="#BDE0FE", trans="auto", layers=[
            Narrator(y=1320, s=1.55, outfit="doc", walk=(-150, 540, at("one doctor"), at("one doctor", off=0.95)), smile=0.8),
            Tag("DR. DONALD UNGER", at("tested"), y=330, size=66, fill=WHITE, rot=-3)]),
        Scene(at("his right"), bg="#FFD166", trans="auto", layers=[
            Narrator(y=1290, s=1.5, pose="cheer"), BigNumber(60, at("60"), fmt="{}+ YEARS", size=130, T1=at("twice")),
            Tag("LEFT", at("left"), x=290, y=1010, size=62, fill=YEL, rot=-3), Tag("RIGHT", at("right"), x=790, y=1010, size=62, fill=WHITE, rot=3),
            Stamp("CONTROL", at("control"), 790, 470, color=RED, w=470, h=150, size=100, rot=-12)]),
        Scene(at("neither"), bg="#B8F2C9", trans="auto", layers=[
            Narrator(y=1320, s=1.4, pose="hands_up", smile=0.9),
            Mark("check", at("neither", off=0.5), 290, 380), Mark("check", at("hand", 2, off=0.0), 790, 380),
            Headline("NO ARTHRITIS", at("arthritis", 1), y=190, size=112),
            Prop(trophy_prop, at("nobel"), 540, 900, 1.3, 0, enter="rise", sfx="bell_win"), Headline("IG NOBEL", at("nobel"), y=330, size=150, fill=YEL),
            Burst(at("nobel"), 540, 760, colors=(YEL, PINK, BLUE, GREEN, WHITE))]),
        Scene(at("a later"), bg="#CDB4DB", trans="auto", layers=[
            Headline("A LATER STUDY", at("a later"), y=250, size=100, T1=at("215")),
            BigNumber(215, at("215"), fmt="{} PEOPLE", y=250, size=118, dur=0.5),
            Crowd(at("215"), n=215, cols=18, spx=54, spy=80, x0=81, y0=372, dur=0.9, s=0.8, dim_at=at("no link")),
            Stamp("NO LINK", at("no link"), 540, 830, color=GREEN, fill=WHITE, w=700, h=230, size=168)]),
        Scene(at("so no"), bg=YEL, trans="auto", layers=[
            Narrator(x=330, y=1290, s=1.45, pose="hands_up", sweat=0.6, brow=-0.5),
            Narrator(x=770, y=1290, s=1.45, outfit="mom", flip=-1, pose=dict(hl=(30, -300), hr=(-30, -300)), talk=False, fists=False, brow=0.8, smile=-0.2),
            Headline("SORRY, MOM", at("sorry"), y=250, size=130, fill=RED, rot=2), Burst(at("sorry"), 540, 250)]),
    ]
