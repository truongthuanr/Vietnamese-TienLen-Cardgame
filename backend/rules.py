from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from schemas import Card, ComboType, LastPlay, Move, Suit

SUIT_ORDER: Dict[Suit, int] = {
    Suit.spades: 0,
    Suit.clubs: 1,
    Suit.diamonds: 2,
    Suit.hearts: 3,
}


@dataclass(frozen=True)
class Combo:
    type: ComboType
    rank: int
    length: int
    suit: Optional[Suit] = None


def evaluate_combo(cards: List[Card]) -> Combo:
    if not cards:
        raise ValueError("No cards provided")

    if len(cards) == 1:
        card = cards[0]
        return Combo(type=ComboType.single, rank=card.rank, length=1, suit=card.suit)

    counts = _rank_counts(cards)
    unique_ranks = sorted(counts.keys())

    if len(cards) == 2 and len(counts) == 1:
        return Combo(type=ComboType.pair, rank=unique_ranks[0], length=2)

    if len(cards) == 3 and len(counts) == 1:
        return Combo(type=ComboType.triple, rank=unique_ranks[0], length=3)

    if len(cards) == 4 and len(counts) == 1:
        return Combo(type=ComboType.four_kind, rank=unique_ranks[0], length=4)

    if _is_consecutive_pairs(cards, counts):
        high_rank = max(unique_ranks)
        return Combo(
            type=ComboType.consecutive_pairs,
            rank=high_rank,
            length=len(cards) // 2,
        )

    if _is_straight(unique_ranks, len(cards)):
        return Combo(type=ComboType.straight, rank=max(unique_ranks), length=len(cards))

    raise ValueError("Invalid combo")


def can_beat(candidate: Combo, last: Combo) -> bool:
    if candidate.type != last.type:
        return False

    if candidate.type in (ComboType.straight, ComboType.consecutive_pairs):
        if candidate.length != last.length:
            return False

    if candidate.rank != last.rank:
        return candidate.rank > last.rank

    if candidate.type == ComboType.single and candidate.suit and last.suit:
        return SUIT_ORDER[candidate.suit] > SUIT_ORDER[last.suit]

    return False


def validate_move(move: Move, last_play: Optional[LastPlay]) -> Optional[LastPlay]:
    if move.type == "pass":
        if last_play is None:
            raise ValueError("Cannot pass without a last play")
        return None

    if move.type != "play":
        raise ValueError("Invalid move type")

    if not move.cards:
        raise ValueError("Play requires cards")

    candidate = evaluate_combo(move.cards)
    if last_play is not None:
        last_combo = evaluate_combo(last_play.cards)
        if candidate.type != last_combo.type:
            if not _can_special_beat(candidate, last_combo):
                raise ValueError("Move does not beat last play")
        else:
            if not can_beat(candidate, last_combo) and not _can_special_upgrade(candidate, last_combo):
                raise ValueError("Move does not beat last play")

    return LastPlay(type=candidate.type, cards=move.cards, by_player_id=move.by_player_id)


def detect_win(remaining_cards: int) -> bool:
    return remaining_cards == 0


def _rank_counts(cards: List[Card]) -> Dict[int, int]:
    counts: Dict[int, int] = {}
    for card in cards:
        counts[card.rank] = counts.get(card.rank, 0) + 1
    return counts


def _is_straight(unique_ranks: List[int], total_cards: int) -> bool:
    if total_cards < 3 or len(unique_ranks) != total_cards:
        return False
    if 15 in unique_ranks:
        return False
    return all(b - a == 1 for a, b in zip(unique_ranks, unique_ranks[1:]))


def _is_consecutive_pairs(cards: List[Card], counts: Dict[int, int]) -> bool:
    if len(cards) < 6 or len(cards) % 2 != 0:
        return False
    if any(count != 2 for count in counts.values()):
        return False
    unique_ranks = sorted(counts.keys())
    if 15 in unique_ranks:
        return False
    return all(b - a == 1 for a, b in zip(unique_ranks, unique_ranks[1:]))


def _can_special_beat(candidate: Combo, last: Combo) -> bool:
    is_single_two = last.type == ComboType.single and last.rank == 15
    is_pair_two = last.type == ComboType.pair and last.rank == 15
    if candidate.type == ComboType.four_kind:
        return is_single_two or is_pair_two
    if candidate.type == ComboType.consecutive_pairs:
        if candidate.length >= 4:
            return is_single_two or is_pair_two
        if candidate.length == 3:
            return is_single_two
        if candidate.length == 4 and last.type == ComboType.four_kind:
            return True
    return False


def _can_special_upgrade(candidate: Combo, last: Combo) -> bool:
    if candidate.type == ComboType.consecutive_pairs and last.type == ComboType.consecutive_pairs:
        return candidate.length == 4 and last.length == 3 and candidate.rank > last.rank
    return False
