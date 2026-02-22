from datetime import datetime

import pytest

from backend.rules import can_beat, detect_win, evaluate_combo, validate_move
from backend.schemas import Card, ComboType, LastPlay, Move, Suit


def make_card(rank: int, suit: Suit) -> Card:
    return Card(rank=rank, suit=suit)


def test_evaluate_single():
    combo = evaluate_combo([make_card(3, Suit.spades)])
    assert combo.type == ComboType.single
    assert combo.rank == 3
    assert combo.suit == Suit.spades


def test_evaluate_pair():
    combo = evaluate_combo([make_card(7, Suit.spades), make_card(7, Suit.clubs)])
    assert combo.type == ComboType.pair
    assert combo.rank == 7


def test_evaluate_triple():
    combo = evaluate_combo(
        [
            make_card(9, Suit.spades),
            make_card(9, Suit.clubs),
            make_card(9, Suit.diamonds),
        ]
    )
    assert combo.type == ComboType.triple
    assert combo.rank == 9


def test_evaluate_four_kind():
    combo = evaluate_combo(
        [
            make_card(11, Suit.spades),
            make_card(11, Suit.clubs),
            make_card(11, Suit.diamonds),
            make_card(11, Suit.hearts),
        ]
    )
    assert combo.type == ComboType.four_kind
    assert combo.rank == 11


def test_evaluate_straight():
    combo = evaluate_combo(
        [
            make_card(3, Suit.spades),
            make_card(4, Suit.clubs),
            make_card(5, Suit.hearts),
            make_card(6, Suit.diamonds),
        ]
    )
    assert combo.type == ComboType.straight
    assert combo.rank == 6
    assert combo.length == 4


def test_evaluate_straight_rejects_two():
    with pytest.raises(ValueError):
        evaluate_combo(
            [
                make_card(12, Suit.spades),
                make_card(13, Suit.clubs),
                make_card(14, Suit.hearts),
                make_card(15, Suit.diamonds),
            ]
        )


def test_evaluate_consecutive_pairs():
    combo = evaluate_combo(
        [
            make_card(3, Suit.spades),
            make_card(3, Suit.clubs),
            make_card(4, Suit.diamonds),
            make_card(4, Suit.hearts),
            make_card(5, Suit.spades),
            make_card(5, Suit.clubs),
        ]
    )
    assert combo.type == ComboType.consecutive_pairs
    assert combo.rank == 5
    assert combo.length == 3


def test_evaluate_invalid_combo():
    with pytest.raises(ValueError):
        evaluate_combo([make_card(3, Suit.spades), make_card(4, Suit.clubs)])


def test_can_beat_same_type_rank():
    last = evaluate_combo([make_card(8, Suit.spades)])
    candidate = evaluate_combo([make_card(9, Suit.spades)])
    assert can_beat(candidate, last) is True


def test_can_beat_single_suit_tiebreak():
    last = evaluate_combo([make_card(8, Suit.clubs)])
    candidate = evaluate_combo([make_card(8, Suit.hearts)])
    assert can_beat(candidate, last) is True


def test_can_beat_straight_length_mismatch():
    last = evaluate_combo(
        [make_card(3, Suit.spades), make_card(4, Suit.clubs), make_card(5, Suit.hearts)]
    )
    candidate = evaluate_combo(
        [
            make_card(4, Suit.spades),
            make_card(5, Suit.clubs),
            make_card(6, Suit.hearts),
            make_card(7, Suit.diamonds),
        ]
    )
    assert can_beat(candidate, last) is False


def test_validate_move_pass_requires_last_play():
    move = Move(type="pass", cards=None, by_player_id=_uuid(), ts=datetime.utcnow())
    with pytest.raises(ValueError):
        validate_move(move, None)


def test_validate_move_play_beats_last():
    last_play = LastPlay(
        type=ComboType.single,
        cards=[make_card(7, Suit.spades)],
        by_player_id=_uuid(),
    )
    move = Move(
        type="play",
        cards=[make_card(9, Suit.clubs)],
        by_player_id=_uuid(),
        ts=datetime.utcnow(),
    )
    new_last = validate_move(move, last_play)
    assert new_last is not None
    assert new_last.type == ComboType.single


def test_validate_move_play_rejects_invalid():
    last_play = LastPlay(
        type=ComboType.pair,
        cards=[make_card(7, Suit.spades), make_card(7, Suit.clubs)],
        by_player_id=_uuid(),
    )
    move = Move(
        type="play",
        cards=[make_card(8, Suit.spades)],
        by_player_id=_uuid(),
        ts=datetime.utcnow(),
    )
    with pytest.raises(ValueError):
        validate_move(move, last_play)


def test_special_beat_four_kind_beats_single_two():
    last_play = LastPlay(
        type=ComboType.single,
        cards=[make_card(15, Suit.spades)],
        by_player_id=_uuid(),
    )
    move = Move(
        type="play",
        cards=[
            make_card(9, Suit.spades),
            make_card(9, Suit.clubs),
            make_card(9, Suit.diamonds),
            make_card(9, Suit.hearts),
        ],
        by_player_id=_uuid(),
        ts=datetime.utcnow(),
    )
    new_last = validate_move(move, last_play)
    assert new_last is not None
    assert new_last.type == ComboType.four_kind


def test_special_beat_four_kind_beats_pair_two():
    last_play = LastPlay(
        type=ComboType.pair,
        cards=[make_card(15, Suit.spades), make_card(15, Suit.hearts)],
        by_player_id=_uuid(),
    )
    move = Move(
        type="play",
        cards=[
            make_card(6, Suit.spades),
            make_card(6, Suit.clubs),
            make_card(6, Suit.diamonds),
            make_card(6, Suit.hearts),
        ],
        by_player_id=_uuid(),
        ts=datetime.utcnow(),
    )
    new_last = validate_move(move, last_play)
    assert new_last is not None
    assert new_last.type == ComboType.four_kind


def test_special_beat_three_consecutive_pairs_beats_single_two():
    last_play = LastPlay(
        type=ComboType.single,
        cards=[make_card(15, Suit.diamonds)],
        by_player_id=_uuid(),
    )
    move = Move(
        type="play",
        cards=[
            make_card(3, Suit.spades),
            make_card(3, Suit.clubs),
            make_card(4, Suit.diamonds),
            make_card(4, Suit.hearts),
            make_card(5, Suit.spades),
            make_card(5, Suit.clubs),
        ],
        by_player_id=_uuid(),
        ts=datetime.utcnow(),
    )
    new_last = validate_move(move, last_play)
    assert new_last is not None
    assert new_last.type == ComboType.consecutive_pairs


def test_special_beat_four_consecutive_pairs_beats_pair_two():
    last_play = LastPlay(
        type=ComboType.pair,
        cards=[make_card(15, Suit.spades), make_card(15, Suit.hearts)],
        by_player_id=_uuid(),
    )
    move = Move(
        type="play",
        cards=[
            make_card(3, Suit.spades),
            make_card(3, Suit.clubs),
            make_card(4, Suit.diamonds),
            make_card(4, Suit.hearts),
            make_card(5, Suit.spades),
            make_card(5, Suit.clubs),
            make_card(6, Suit.diamonds),
            make_card(6, Suit.hearts),
        ],
        by_player_id=_uuid(),
        ts=datetime.utcnow(),
    )
    new_last = validate_move(move, last_play)
    assert new_last is not None
    assert new_last.type == ComboType.consecutive_pairs


def test_special_beat_three_consecutive_pairs_rejects_pair_two():
    last_play = LastPlay(
        type=ComboType.pair,
        cards=[make_card(15, Suit.spades), make_card(15, Suit.hearts)],
        by_player_id=_uuid(),
    )
    move = Move(
        type="play",
        cards=[
            make_card(3, Suit.spades),
            make_card(3, Suit.clubs),
            make_card(4, Suit.diamonds),
            make_card(4, Suit.hearts),
            make_card(5, Suit.spades),
            make_card(5, Suit.clubs),
        ],
        by_player_id=_uuid(),
        ts=datetime.utcnow(),
    )
    with pytest.raises(ValueError):
        validate_move(move, last_play)


def test_detect_win():
    assert detect_win(0) is True
    assert detect_win(3) is False


def _uuid():
    from uuid import uuid4

    return uuid4()
