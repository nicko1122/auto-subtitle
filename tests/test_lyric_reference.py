import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.core import luna_pipeline
from src.core.lyric_reference import build_lyric_occurrences


def segment(text, start=0):
    words = [{'word': char, 'start': start + index, 'end': start + index + 1} for index, char in enumerate(text)]
    return {'id': start, 'text': text, 'start': start, 'end': start + len(text), 'words': words}


def test_reference_reuses_chorus_and_partial_lines_in_audio_order():
    reference = ['別想！', '我要是變成你——那才叫真的完了！', '我要靈魂，不要高薪。']
    spoken = [segment('我要靈魂不要高興'), segment('別想別想別想別想', 20), segment('我要是變成你那才叫真的玩樂', 40), segment('那才叫真的玩樂', 60), segment('我要靈魂不要高興', 80)]
    occurrences = build_lyric_occurrences(reference, spoken)
    assert [item['text'] for item in occurrences] == [reference[2], *[reference[0]] * 4, reference[1], '那才叫真的完了！', reference[2]]
    assert [item['occurrence'] for item in occurrences if item['text'] == reference[0]] == [1, 2, 3, 4]
    assert occurrences[-1]['words'][0]['start'] == 80
    indices = [index for item in occurrences for index in range(item['word_start'], item['word_end'])]
    assert indices == list(range(sum(len(item['words']) for item in spoken)))


def test_reference_preserves_unmatched_speech_and_does_not_invent_repeats():
    spoken = [segment('快去找個工作'), segment('臨時改唱其他東西', 20), segment('生活才會更好', 40)]
    occurrences = build_lyric_occurrences(['生活才會更好', '快去找個工作', '從沒唱過這一句'], spoken)
    assert [item['text'] for item in occurrences] == ['快去找個工作', '臨時改唱其他東西', '生活才會更好']
    assert [item['source_line_id'] for item in occurrences] == [2, None, 1]
    assert build_lyric_occurrences(['別想'], []) == []


def test_segment_without_word_timestamps_is_retained_for_review():
    occurrences = build_lyric_occurrences(['別想'], [{'text': '別想別想', 'start': 10, 'end': 12, 'words': []}])
    assert len(occurrences) == 1
    assert occurrences[0]['text'] == '別想別想'
    assert occurrences[0]['source_line_id'] is None
    assert occurrences[0]['words'] == [{'word': '別想別想', 'start': 10, 'end': 12, 'segment_only': True}]


@pytest.mark.parametrize('mode', ['reference', 'transcript'])
def test_pipeline_expands_reference_before_alignment_and_reports_coverage(tmp_path, monkeypatch, mode):
    asr = {'raw_segments': [segment('別想', 1), segment('別想', 10), segment('另外一句', 20)]}
    monkeypatch.setattr(luna_pipeline, 'transcribe_native_audio', lambda **kwargs: asr)
    model = SimpleNamespace(cpu=Mock(), align=Mock(return_value=SimpleNamespace(segments=[])))
    monkeypatch.setattr(luna_pipeline, 'load_native_whisper_model', lambda *args: model)
    monkeypatch.setattr(luna_pipeline, 'cut_audio_segment', lambda *args: False)
    pipeline = luna_pipeline.LunaPipeline('unused', '別想', output_dir=str(tmp_path), script_mode=mode, llm_audit=False)
    pipeline.org_lines = ['別想']
    pipeline.reference_lines = ['別想']
    pipeline.audio_duration = 30
    pipeline.step_2_whisper_full_asr()
    pipeline.step_3_and_4_alignment_and_evidence()
    final = pipeline.step_7_display_rules_and_export(pipeline.step_5_and_6_luna_decision())
    expected = ['別想', '別想', '另外一句'] if mode == 'reference' else ['別想']
    assert model.align.call_args.args[1] == '\n'.join(expected)
    assert [item.text for item in final.segments] == expected
    report = json.loads((tmp_path / 'validation.json').read_text())
    assert report['validation_passed']
    if mode == 'reference':
        assert report['lyrics_text_100_percent_match'] is None
        assert report['reference_lines_count'] == 1
        assert report['matched_occurrences'] == 2
        assert report['asr_only_occurrences'] == 1
        assert report['asr_coverage_complete']
        assert pipeline.reviews[-1]['status'] == 'needs_review'
        assert 'asr_only_not_in_reference' in pipeline.reviews[-1]['anomalies']
        assert [(item.start, item.end) for item in final.segments] == [(1, 3.16), (10, 12.16), (20, 24.16)]
    else:
        assert report['lyrics_text_100_percent_match']


def test_empty_reference_asr_does_not_allocate_aligner_or_fabricate_cues(tmp_path, monkeypatch):
    monkeypatch.setattr(luna_pipeline, 'transcribe_native_audio', lambda **kwargs: {'raw_segments': []})
    loader = Mock(side_effect=AssertionError('No aligner needed for empty ASR'))
    monkeypatch.setattr(luna_pipeline, 'load_native_whisper_model', loader)
    pipeline = luna_pipeline.LunaPipeline('unused', '別想', output_dir=str(tmp_path), script_mode='reference')
    pipeline.reference_lines = ['別想']
    pipeline.audio_duration = 10
    pipeline.step_2_whisper_full_asr()
    assert pipeline.org_lines == []
    assert pipeline.step_3_and_4_alignment_and_evidence() == []
    assert pipeline.step_5_and_6_luna_decision() == []
    assert pipeline.step_7_display_rules_and_export([]).segments == []
    loader.assert_not_called()


def test_unknown_script_mode_fails_before_processing(tmp_path):
    with pytest.raises(ValueError, match='script_mode'):
        luna_pipeline.LunaPipeline('unused', '', output_dir=str(tmp_path), script_mode='other')


def test_unknown_provider_does_not_fall_through_to_cloud(tmp_path):
    with pytest.raises(ValueError, match='llm_provider'):
        luna_pipeline.LunaPipeline('unused', '原詞', output_dir=str(tmp_path), llm_provider='auto')
