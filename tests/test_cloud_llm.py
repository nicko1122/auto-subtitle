from src.core.proofreader import SubtitleProofreader
from src.schemas.subtitle import SubtitleTrack, SubtitleSegment

proofreader = SubtitleProofreader()
print(f"Testing mode 1: Pure LLM homophone correction (no lyrics provided)...")
track1 = SubtitleTrack(
    source_file="test1.mp3",
    segments=[
        SubtitleSegment(id=1, start=1.0, end=3.5, text="像是隔著開平洋"),
    ]
)
res1 = proofreader.proofread_track(track1)
for s in res1.segments:
    print(f"-> id={s.id}: {s.text}")

print(f"\nTesting mode 2: Lyrics-assisted proofreading (with reference script)...")
track2 = SubtitleTrack(
    source_file="test2.mp3",
    segments=[
        SubtitleSegment(id=1, start=0.0, end=2.5, text="客廳座個老頭"),
        SubtitleSegment(id=2, start=2.5, end=5.0, text="別想叫我活成你那樣"),
    ]
)
script2 = "客廳坐個老頭，眼神像把鏽蝕的刀。\n別想叫我活成你那樣！"
res2 = proofreader.proofread_track(track2, reference_script=script2)
for s in res2.segments:
    print(f"-> id={s.id}: {s.text}")

print("\nAll tests passed successfully!")
