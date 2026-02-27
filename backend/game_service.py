import json
import random
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from redis_store import ROOM_TTL_SECONDS, get_redis, room_hands_key, room_meta_key, room_state_key
from room_service import get_players, get_room, update_player
from rules import can_beat, evaluate_combo, validate_move
from schemas import Card, ComboType, GameState, GameStatus, LastPlay, Move, RoomStatus, Suit

CARDS_PER_PLAYER = 13


def _serialize_cards(cards: List[Card]) -> str:
    return json.dumps([card.model_dump(mode="json") for card in cards])


def _deserialize_cards(raw: str) -> List[Card]:
    return [Card.model_validate(item) for item in json.loads(raw)]


def _create_deck() -> List[Card]:
    cards: List[Card] = []
    for rank in range(3, 16):
        for suit in Suit:
            cards.append(Card(rank=rank, suit=suit))
    return cards


def _deal_hands(players: List[UUID], deck: List[Card]) -> Dict[UUID, List[Card]]:
    hands: Dict[UUID, List[Card]] = {player_id: [] for player_id in players}
    index = 0
    for card in deck:
        hands[players[index]].append(card)
        index = (index + 1) % len(players)
        if all(len(hand) >= CARDS_PER_PLAYER for hand in hands.values()):
            break
    return hands


def _find_start_player(hands: Dict[UUID, List[Card]]) -> UUID:
    for player_id, cards in hands.items():
        if any(card.rank == 3 and card.suit == Suit.spades for card in cards):
            return player_id
    return next(iter(hands))


def _next_player(players: List[UUID], current: UUID) -> UUID:
    idx = players.index(current)
    return players[(idx + 1) % len(players)]


async def start_game(code: str, max_games: Optional[int] = None) -> GameState:
    code = code.upper()
    room = await get_room(code)
    if room is None:
        raise ValueError("Room not found")
    players = await get_players(code)
    if len(players) < 2:
        raise ValueError("Not enough players to start")

    if max_games is not None and max_games >= 1:
        room.max_games = max_games
    room.status = RoomStatus.in_game

    players_order = [player.id for player in sorted(players, key=lambda p: p.seat)]
    deck = _create_deck()
    random.shuffle(deck)
    hands = _deal_hands(players_order, deck)
    current_turn = _find_start_player(hands)

    first_game = room.games_played == 0
    state = GameState(
        room_id=room.id,
        status=GameStatus.playing,
        deck=[],
        players_order=players_order,
        current_turn=current_turn,
        last_play=None,
        pass_count=0,
        winner_id=None,
        first_game=first_game,
        first_turn_required=first_game,
    )

    client = await get_redis()
    pipeline = client.pipeline()
    pipeline.set(room_state_key(code), json.dumps(state.model_dump(mode="json")))
    room.games_played += 1
    pipeline.set(
        room_meta_key(code),
        json.dumps(room.model_dump(mode="json", exclude={"players"})),
    )
    for player_id, cards in hands.items():
        pipeline.hset(room_hands_key(code), str(player_id), _serialize_cards(cards))
    pipeline.expire(room_state_key(code), ROOM_TTL_SECONDS)
    pipeline.expire(room_hands_key(code), ROOM_TTL_SECONDS)
    await pipeline.execute()

    for player in players:
        player.hand_count = len(hands[player.id])
        await update_player(code, player)

    return state


async def play_turn(code: str, player_id: UUID, cards_payload: List[dict]) -> GameState:
    code = code.upper()
    client = await get_redis()
    raw_state = await client.get(room_state_key(code))
    if raw_state is None:
        raise ValueError("Game not started")

    state = GameState.model_validate(json.loads(raw_state))
    if state.status != GameStatus.playing:
        raise ValueError("Game already finished")
    if state.current_turn != player_id:
        raise ValueError("Not your turn")

    raw_hand = await client.hget(room_hands_key(code), str(player_id))
    if raw_hand is None:
        raise ValueError("Player hand not found")
    hand_cards = _deserialize_cards(raw_hand)
    cards = [Card.model_validate(payload) for payload in cards_payload]

    if not _hand_contains(hand_cards, cards):
        raise ValueError("Cards not in hand")

    if state.first_turn_required:
        has_three_spades = any(card.rank == 3 and card.suit == Suit.spades for card in cards)
        if not has_three_spades:
            raise ValueError("First play must include 3 of spades")

    move = Move(type="play", cards=cards, by_player_id=player_id, ts=datetime.utcnow())
    last_play = validate_move(move, state.last_play)
    if state.last_play is not None:
        await _apply_chop_scoring(code, state.last_play, move)

    remaining_hand = _remove_cards(hand_cards, cards)
    await client.hset(room_hands_key(code), str(player_id), _serialize_cards(remaining_hand))

    state.last_play = last_play
    state.pass_count = 0
    if state.first_turn_required:
        state.first_turn_required = False
    if not remaining_hand:
        state.status = GameStatus.finished
        state.winner_id = player_id
    state.current_turn = _next_player(state.players_order, player_id)
    await client.set(room_state_key(code), json.dumps(state.model_dump(mode="json")), ex=ROOM_TTL_SECONDS)

    await _sync_hand_count(code, player_id, len(remaining_hand))
    if state.status == GameStatus.finished:
        await _apply_end_game_scoring(code)
    return state

# Get the player's current hand of cards
# This is used to display the player's hand in the UI and to validate their moves.
async def get_hand(code: str, player_id: UUID) -> List[Card]:
    code = code.upper()
    client = await get_redis()
    raw_hand = await client.hget(room_hands_key(code), str(player_id))
    if raw_hand is None:
        raise ValueError("Player hand not found")
    return _deserialize_cards(raw_hand)


async def maybe_start_next_game(code: str) -> Tuple[Optional[GameState], bool]:
    code = code.upper()
    room = await get_room(code)
    if room is None:
        return None, False
    client = await get_redis()
    raw_state = await client.get(room_state_key(code))
    if raw_state is None:
        return None, False
    state = GameState.model_validate(json.loads(raw_state))
    if state.status != GameStatus.finished:
        return None, False
    if room.games_played >= room.max_games:
        room.status = RoomStatus.waiting
        room.games_played = 0
        await _reset_ready_status(code)
        pipeline = client.pipeline()
        pipeline.delete(room_state_key(code))
        pipeline.delete(room_hands_key(code))
        pipeline.set(room_meta_key(code), json.dumps(room.model_dump(mode="json", exclude={"players"})))
        pipeline.expire(room_meta_key(code), ROOM_TTL_SECONDS)
        await pipeline.execute()
        return None, True
    next_state = await start_game(code)
    return next_state, False


async def pass_turn(code: str, player_id: UUID) -> GameState:
    code = code.upper()
    client = await get_redis()
    raw_state = await client.get(room_state_key(code))
    if raw_state is None:
        raise ValueError("Game not started")

    state = GameState.model_validate(json.loads(raw_state))
    if state.current_turn != player_id:
        raise ValueError("Not your turn")
    if state.last_play is None:
        raise ValueError("Cannot pass without a last play")

    state.pass_count += 1
    if state.pass_count >= len(state.players_order) - 1:
        state.pass_count = 0
        state.current_turn = state.last_play.by_player_id
        state.last_play = None
    else:
        state.current_turn = _next_player(state.players_order, player_id)

    await client.set(room_state_key(code), json.dumps(state.model_dump(mode="json")), ex=ROOM_TTL_SECONDS)
    return state


async def get_game_state(code: str) -> Optional[GameState]:
    code = code.upper()
    client = await get_redis()
    raw_state = await client.get(room_state_key(code))
    if raw_state is None:
        return None
    return GameState.model_validate(json.loads(raw_state))


def _hand_contains(hand: List[Card], desired: List[Card]) -> bool:
    hand_counts: Dict[tuple[int, str], int] = {}
    for card in hand:
        key = (card.rank, card.suit.value)
        hand_counts[key] = hand_counts.get(key, 0) + 1
    for card in desired:
        key = (card.rank, card.suit.value)
        if hand_counts.get(key, 0) == 0:
            return False
        hand_counts[key] -= 1
    return True


def _remove_cards(hand: List[Card], to_remove: List[Card]) -> List[Card]:
    remove_counts: Dict[tuple[int, str], int] = {}
    for card in to_remove:
        key = (card.rank, card.suit.value)
        remove_counts[key] = remove_counts.get(key, 0) + 1
    remaining: List[Card] = []
    for card in hand:
        key = (card.rank, card.suit.value)
        if remove_counts.get(key, 0) > 0:
            remove_counts[key] -= 1
        else:
            remaining.append(card)
    return remaining


async def _sync_hand_count(code: str, player_id: UUID, count: int) -> None:
    players = await get_players(code)
    for player in players:
        if player.id == player_id:
            player.hand_count = count
            await update_player(code, player)
            return


async def _apply_chop_scoring(code: str, last_play: LastPlay, move: Move) -> None:
    last_combo = evaluate_combo(last_play.cards)
    candidate = evaluate_combo(move.cards)
    delta = 0

    if last_combo.rank == 15 and last_combo.type in {ComboType.single, ComboType.pair}:
        if candidate.type in {ComboType.four_kind, ComboType.consecutive_pairs}:
            delta = sum(_two_penalty(card.suit) for card in last_play.cards)
    elif last_combo.type == ComboType.consecutive_pairs and last_combo.length == 3:
        if candidate.type == ComboType.consecutive_pairs and candidate.length == 4:
            delta = 2
    elif last_combo.type == ComboType.four_kind:
        if candidate.type == ComboType.consecutive_pairs and candidate.length == 4:
            delta = 2
    elif last_combo.type == ComboType.consecutive_pairs and last_combo.length == 4:
        if candidate.type == ComboType.consecutive_pairs and candidate.length == 4 and can_beat(candidate, last_combo):
            delta = 4

    if delta > 0:
        await _apply_score_delta(code, move.by_player_id, last_play.by_player_id, delta)


async def _apply_end_game_scoring(code: str) -> None:
    players = await get_players(code)
    if not players:
        return
    client = await get_redis()
    hands_raw = await client.hgetall(room_hands_key(code))
    hand_counts: Dict[UUID, int] = {}
    for player in players:
        raw_hand = hands_raw.get(str(player.id))
        hand_counts[player.id] = len(_deserialize_cards(raw_hand)) if raw_hand else 0
    seat_map = {player.id: player.seat for player in players}
    ordered = sorted(players, key=lambda p: (hand_counts.get(p.id, 0), seat_map.get(p.id, 0)))

    if len(players) == 2:
        score_table = [2, -2]
    elif len(players) == 3:
        score_table = [2, 1, -1]
    else:
        score_table = [2, 1, -1, -2]

    for index, player in enumerate(ordered[: len(score_table)]):
        player.score += score_table[index]
        await update_player(code, player)


async def _apply_score_delta(code: str, winner_id: UUID, loser_id: UUID, delta: int) -> None:
    players = await get_players(code)
    updated = False
    for player in players:
        if player.id == winner_id:
            player.score += delta
            await update_player(code, player)
            updated = True
        elif player.id == loser_id:
            player.score -= delta
            await update_player(code, player)
            updated = True
    if not updated:
        return


def _two_penalty(suit: Suit) -> int:
    if suit in {Suit.spades, Suit.clubs}:
        return 1
    return 2


async def _reset_ready_status(code: str) -> None:
    players = await get_players(code)
    for player in players:
        if player.is_ready:
            player.is_ready = False
            await update_player(code, player)
