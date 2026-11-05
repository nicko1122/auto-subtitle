import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.core import luna_pipeline


def test_mapping_uses_whole_word_window_and_contextual_pinyin():
    word = {'word': '银航', 'start': 2, 'end': 4, 'probability': .9}
    mapped = luna_pipeline.map_lyrics_to_asr_words(['銀行'], [{'words': [word]}])[0]
    assert mapped['matched_characters'] == 2
    assert mapped['original_characters'] == 2
    assert mapped['words'] == [word]
    partial = luna_pipeline.map_lyrics_to_asr_words(['鐘'], [{'words': [{'word': '時鐘', 'start': 2, 'end': 4}]}])[0]
    assert partial['words'][0]['start'] == 2
    assert partial['words'][0]['end'] == 4


def test_mapping_keeps_repeated_lyrics_in_distinct_positions():
    words = [{'word': '没有感觉', 'start': 1, 'end': 5}, {'word': '沒有感覺', 'start': 100, 'end': 104}]
    mapped = luna_pipeline.map_lyrics_to_asr_words(['沒有感覺', '沒有感覺'], [{'words': words}])
    assert [item['words'] for item in mapped] == [[words[0]], [words[1]]]
    assert [item['matched_characters'] for item in mapped] == [4, 4]


@pytest.mark.parametrize('lines,segments', [(['甲'], [{'words': [{'word': '乙', 'start': 0, 'end': 1}]}]), (['甲'], []), (['hello'], [{'words': [{'word': 'world', 'start': 0, 'end': 1}]}])])
def test_mapping_reports_missing_matches_without_inventing_times(lines, segments):
    result = luna_pipeline.map_lyrics_to_asr_words(lines, segments)[0]
    assert result['words'] == []
    assert result['matched_characters'] == 0


@pytest.mark.parametrize('has_words', [True, False])
def test_luna_uses_word_mapping_instead_of_whole_asr_segments(tmp_path, monkeypatch, has_words):
    model = SimpleNamespace(cpu=Mock(), align=Mock(return_value=SimpleNamespace(segments=[SimpleNamespace(start=5, end=6, text='甲', words=[]), SimpleNamespace(start=15, end=16, text='乙', words=[])])))
    monkeypatch.setattr(luna_pipeline, 'load_native_whisper_model', lambda *args: model)
    monkeypatch.setattr(luna_pipeline, 'cut_audio_segment', lambda *args: False)
    reasoner = Mock()
    reasoner.decide.return_value = '{"decisions":[]}'
    monkeypatch.setattr(luna_pipeline, 'LocalQwenReasoner', lambda *args: reasoner)
    pipeline = luna_pipeline.LunaPipeline('unused', '甲\n乙', output_dir=str(tmp_path))
    pipeline.org_lines = ['甲', '乙']
    pipeline.audio_duration = 30
    words = [{'word': '甲', 'start': 0, 'end': 2}, {'word': '乙', 'start': 20, 'end': 22}]
    pipeline.asr_clean_segments = [{'start': 0, 'end': 30, 'text': '甲乙', 'words': words if has_words else []}]
    evidence = pipeline.step_3_and_4_alignment_and_evidence()
    final = pipeline.step_5_and_6_luna_decision()
    assert [(cue.start, cue.end) for cue in final] == ([(0, 2), (20, 22)] if has_words else [(5, 6), (15, 16)])
    assert {cue['default_candidate_id'] for cue in evidence} == ({'cand_asr'} if has_words else {'cand_stable_ts'})
    assert all(row['status'] == 'needs_review' for row in pipeline.reviews)
    if not has_words:
        assert all('asr_mapping_missing' in cue['anomalies'] for cue in evidence)
        assert all('cand_asr' not in cue['candidates'] for cue in evidence)
    model.cpu.assert_called_once()


def cue(line_id, start, end, review=False):
    return {'line_id': line_id, 'org_line': '歌詞', 'default_candidate_id': 'cand_asr', 'candidates': {'cand_asr': {'start': start, 'end': end}, 'cand_stable_ts': {'start': start + .2, 'end': end + .2}}, 'anomalies': ['test'] if review else [], 'needs_review': review}


def test_mapping_overlap_caps_previous_end_without_delaying_next_onset(tmp_path):
    pipeline = luna_pipeline.LunaPipeline('unused', '', output_dir=str(tmp_path))
    pipeline.audio_duration = 4
    pipeline.cue_evidence = [cue(1, 0, 2), cue(2, 1.5, 3)]
    final = pipeline.step_5_and_6_luna_decision()
    assert [(item.start, item.end) for item in final] == [(0, 1.5), (1.5, 3)]


@pytest.mark.parametrize('reply', ['valid', 'unexpected_id', 'invalid_candidate', 'fractional_id', 'boolean_id'])
def test_luna_batches_word_evidence_and_keeps_invalid_decisions_for_review(tmp_path, monkeypatch, reply):
    requests = []
    def decide(system, user):
        payload = json.loads(user)
        requests.append(payload)
        assert len(payload) <= 4
        if reply == 'unexpected_id':
            decisions = [{'line_id': 99, 'action': 'keep'}]
        elif reply in ('fractional_id', 'boolean_id'):
            decisions = [{'line_id': 1.5 if reply == 'fractional_id' else True, 'action': 'keep'}]
        elif reply == 'invalid_candidate':
            decisions = [{'line_id': item['line_id'], 'action': 'choose_candidate', 'start_candidate_id': 'not_provided', 'end_candidate_id': 'cand_asr'} for item in payload]
        else:
            decisions = [{'line_id': item['line_id'], 'action': 'keep'} for item in payload]
        return json.dumps({'decisions': decisions})
    reasoner = Mock(decide=Mock(side_effect=decide))
    monkeypatch.setattr(luna_pipeline, 'LocalQwenReasoner', lambda *args: reasoner)
    pipeline = luna_pipeline.LunaPipeline('unused', '', output_dir=str(tmp_path))
    pipeline.audio_duration = 20
    pipeline.cue_evidence = [cue(i, i * 2, i * 2 + 1, True) for i in range(1, 10)]
    final = pipeline.step_5_and_6_luna_decision()
    assert len(requests) == 3
    assert [item.start for item in final] == [i * 2 for i in range(1, 10)]
    batches = json.loads((tmp_path / 'decision_batches.json').read_text())['batches']
    assert all(bool(item['missing_ids']) == (reply != 'valid') for item in batches)
    reasoner.close.assert_called_once()
