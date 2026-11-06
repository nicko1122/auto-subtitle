import io
import json
import shutil
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

from src.api import asset_packages
from src.core import luna_pipeline
from src.core.exporter import parse_srt_content


@pytest.mark.parametrize('invalid', [
    'not an srt',
    '1\n00:00:01,000 --> 00:00:02,000\nvalid\n\n2\nbad --> time\nlost',
    '1\n00:00:02,000 --> 00:00:01,000\nbackwards',
])
def test_invalid_subtitle_import_leaves_working_srt_and_script_unchanged(tmp_path, invalid):
    package = tmp_path / 'package'
    package.mkdir()
    (package / 'video.mp4').touch()
    subtitle = package / 'video.srt'
    subtitle.write_text('1\n00:00:01,000 --> 00:00:02,000\n原字幕\n')
    script = package / 'video.txt'
    script.write_text('原詞')
    before = {p.name: p.read_bytes() for p in package.iterdir()}
    with pytest.raises(ValueError):
        asset_packages.import_files(tmp_path, '', [('video.txt', io.BytesIO(b'new')), ('video.srt', io.BytesIO(invalid.encode()))], target=package)
    assert before == {p.name: p.read_bytes() for p in package.iterdir()}


def test_strict_subtitle_parser_preserves_empty_cues_and_vtt_metadata():
    track = parse_srt_content('WEBVTT\n\nNOTE metadata\nignore\n\nfirst\n00:01.000 --> 00:02.000\n\n00:03.000 --> 00:04.000\ntext\n', strict=True)
    assert [s.text for s in track.segments] == ['', 'text']
    assert parse_srt_content('', strict=True).segments == []


def test_keyword_matches_are_retained_and_reviewed(tmp_path, monkeypatch):
    text = '我想作曲給你聽'
    words = [{'word':c, 'start':i, 'end':i+1} for i,c in enumerate(text)]
    raw = {'raw_segments':[{'id':1,'start':0,'end':len(text),'text':text,'words':words}]}
    monkeypatch.setattr(luna_pipeline, 'transcribe_native_audio', lambda **kw: raw)
    pipeline = luna_pipeline.LunaPipeline('unused', text, output_dir=str(tmp_path), script_mode='reference', llm_audit=False)
    pipeline.reference_lines = [text]
    pipeline.audio_duration = len(text)
    pipeline.step_2_whisper_full_asr()
    assert pipeline.org_lines == [text]
    assert pipeline.manifest['suspected_hallucinations'][0]['action'] == 'retained_for_review'
    model = Mock()
    model.align.return_value.segments = []
    monkeypatch.setattr(luna_pipeline, 'load_native_whisper_model', lambda *args: model)
    monkeypatch.setattr(luna_pipeline, 'cut_audio_segment', lambda *args: False)
    pipeline.step_3_and_4_alignment_and_evidence()
    pipeline.step_7_display_rules_and_export(pipeline.step_5_and_6_luna_decision())
    assert pipeline.reviews[0]['status'] == 'needs_review'
    assert 'suspected_hallucination' in pipeline.reviews[0]['anomalies']
    assert json.loads((tmp_path/'validation.json').read_text())['asr_coverage_complete']


def test_editor_integrity():
    if not shutil.which('node'):
        pytest.skip('Node.js is required')
    subprocess.run(['node','tests/editor_integrity.cjs'], check=True, cwd=Path(__file__).resolve().parents[1])
