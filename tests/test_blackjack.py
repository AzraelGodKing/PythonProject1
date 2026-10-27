"""Blackjack rules. Shoes are stacked so the deal order is: player, dealer, player, dealer, then draws."""

import pytest

from arcade.core.cards import Card, Shoe, cards
from arcade.core.chips import Bank, InsufficientChips
from arcade.games.blackjack.logic import (
    Action,
    Blackjack,
    Hand,
    Outcome,
    Phase,
    RuleError,
    Rules,
    basic_strategy,
    hand_value,
    is_blackjack,
)


def table(codes: str, balance: int = 1000, **rules) -> Blackjack:
    return Blackjack(bank=Bank(balance), rules=Rules(**rules), shoe=Shoe.stacked(cards(codes)))


@pytest.mark.parametrize(
    ("codes", "total", "soft"),
    [
        ("AS KH", 21, True),
        ("AS AH", 12, True),
        ("AS AH 9C", 21, True),
        ("AS AH KC", 12, False),
        ("AS 6H", 17, True),
        ("AS 6H 10C", 17, False),
        ("KS QH 2C", 22, False),
        ("AS AH AC AD", 14, True),
        ("AS AH AC AD 7S 10H", 21, False),
        ("5S 6H", 11, False),
    ],
)
def test_hand_value(codes, total, soft):
    assert hand_value(cards(codes)) == (total, soft)


def test_is_blackjack_needs_two_cards():
    assert is_blackjack(cards("AS KH"))
    assert not is_blackjack(cards("7S 7H 7C"))


def test_plain_win_pays_even_money():
    game = table("10S 9H 10H 8D")  # player 20 vs dealer 17
    game.deal(100)
    assert game.phase is Phase.PLAYER
    game.stand()
    assert game.phase is Phase.DONE
    assert game.hands[0].outcome is Outcome.WIN
    assert game.bank.balance == 1100
    assert game.round_net == 100


def test_player_blackjack_pays_three_to_two_immediately():
    game = table("AS 9H KH 7D")
    game.deal(100)
    assert game.phase is Phase.DONE
    assert game.hands[0].outcome is Outcome.BLACKJACK
    assert game.bank.balance == 1150


def test_odd_bet_blackjack_rounds_down():
    game = table("AS 9H KH 7D")
    game.deal(25)
    assert game.hands[0].payout == 25 + 37


def test_dealer_peeks_with_ten_up():
    game = table("9S KH 9H AD")  # dealer K + A, player 18
    game.deal(100)
    assert game.phase is Phase.DONE
    assert game.hands[0].outcome is Outcome.LOSE
    assert game.bank.balance == 900


def test_both_blackjack_push():
    game = table("AS KH KS AD")
    game.deal(100)
    assert game.hands[0].outcome is Outcome.PUSH
    assert game.bank.balance == 1000


def test_insurance_offered_against_ace_and_pays_when_dealer_has_blackjack():
    game = table("10S AH 9H KD")
    game.deal(100)
    assert game.phase is Phase.INSURANCE
    assert game.available_actions() == set()
    with pytest.raises(RuleError):
        game.hit()
    game.insurance(True)
    assert game.phase is Phase.DONE
    assert game.hands[0].outcome is Outcome.LOSE
    # -100 main bet, -50 insurance, +150 insurance payout (2:1 plus stake)
    assert game.bank.balance == 1000
    assert game.round_net == 0


def test_insurance_lost_when_dealer_has_no_blackjack_and_play_continues():
    game = table("10S AH 9H 6D 5C 10C")  # player 19, dealer A6 hits to 12 then busts
    game.deal(100)
    game.insurance(True)
    assert game.phase is Phase.PLAYER
    game.stand()
    assert game.insurance_payout == 0
    assert game.hands[0].outcome is Outcome.WIN
    assert game.bank.balance == 1000 - 100 - 50 + 200


def test_declining_insurance_against_ace():
    game = table("10S AH 9H KD")
    game.deal(100)
    game.insurance(False)
    assert game.insurance_bet == 0
    assert game.bank.balance == 900


def test_insurance_needs_chips():
    game = table("10S AH 9H 6D", balance=100)
    game.deal(100)
    assert not game.can_insure()
    with pytest.raises(InsufficientChips):
        game.insurance(True)


def test_bust_loses_even_if_dealer_busts_and_dealer_skips_drawing():
    game = table("10S 6H 6H 10D KC 9S")
    game.deal(100)
    game.hit()  # 16 + K = 26
    assert game.phase is Phase.DONE
    assert game.hands[0].outcome is Outcome.BUST
    assert len(game.dealer) == 2  # all hands busted: dealer doesn't draw
    assert game.bank.balance == 900


def test_dealer_hits_soft_17_by_default_and_stands_when_configured():
    hits = table("10S AH 8H 6D 2C")
    hits.deal(100)
    hits.insurance(False)
    hits.stand()
    assert len(hits.dealer) == 3  # A6 + 2 = 19
    assert hits.hands[0].outcome is Outcome.LOSE

    stands = table("10S AH 8H 6D 2C", dealer_hits_soft_17=False)
    stands.deal(100)
    stands.insurance(False)
    stands.stand()
    assert len(stands.dealer) == 2
    assert stands.hands[0].outcome is Outcome.WIN


def test_hit_to_21_finishes_hand_automatically():
    game = table("5S 10H 6H 7D KC")
    game.deal(10)
    game.hit()
    assert game.hands[0].total == 21
    assert game.phase is Phase.DONE


def test_double_down_takes_one_card_and_doubles_bet():
    game = table("5S 10H 6H 7D 10C")  # player 11, dealer 17
    game.deal(100)
    assert Action.DOUBLE in game.available_actions()
    game.double()
    hand = game.hands[0]
    assert hand.doubled and hand.bet == 200 and len(hand.cards) == 3
    assert hand.outcome is Outcome.WIN
    assert game.bank.balance == 1200


def test_cannot_double_after_hitting_or_without_chips():
    game = table("2S 10H 3H 7D 2C 10C")
    game.deal(100)
    game.hit()
    assert Action.DOUBLE not in game.available_actions()
    with pytest.raises(RuleError):
        game.double()

    poor = table("5S 10H 6H 7D", balance=100)
    poor.deal(100)
    assert Action.DOUBLE not in poor.available_actions()


def test_split_creates_two_hands_with_their_own_bets():
    game = table("8S 10H 8H 7D 3C 2C 10S 10D")
    game.deal(50)
    assert Action.SPLIT in game.available_actions()
    game.split()
    assert len(game.hands) == 2
    assert [len(h.cards) for h in game.hands] == [2, 2]
    assert game.bank.balance == 900
    assert game.active == 0
    game.stand()  # 8+3 = 11
    assert game.active == 1
    game.stand()  # 8+2 = 10
    assert game.phase is Phase.DONE
    # dealer 17, both hands lose
    assert [h.outcome for h in game.hands] == [Outcome.LOSE, Outcome.LOSE]


def test_split_ten_values_and_twenty_one_after_split_is_not_blackjack():
    game = table("KS 9H QH 8D AC 7C")  # split K/Q; first gets A (21), second gets 7
    game.deal(100)
    game.split()
    first = game.hands[0]
    assert first.total == 21
    assert not first.natural
    assert game.active == 1  # 21 finished the first hand automatically
    game.stand()
    assert first.outcome is Outcome.WIN
    assert first.payout == 200  # even money, not 3:2


def test_split_aces_get_one_card_each_and_stand():
    game = table("AS 9H AH 8D KC 5C")
    game.deal(100)
    game.split()
    assert game.phase is Phase.DONE  # no decisions on split aces
    assert [h.total for h in game.hands] == [21, 16]
    assert [h.outcome for h in game.hands] == [Outcome.WIN, Outcome.LOSE]
    assert game.bank.balance == 1000


def test_resplit_aces_only_when_allowed():
    blocked = table("AS 9H AH 8D AC 5C")
    blocked.deal(100)
    blocked.split()
    assert blocked.phase is Phase.DONE

    allowed = table("AS 9H AH 8D AC 5C 9C 9D", resplit_aces=True)
    allowed.deal(100)
    allowed.split()
    assert allowed.phase is Phase.PLAYER
    assert allowed.available_actions() == {Action.STAND, Action.SPLIT}
    allowed.split()
    assert len(allowed.hands) == 3


def test_split_limit_and_double_after_split_rule():
    game = table("8S 10H 8H 7D 8C 8D 8C 2S 3S", max_hands=2, double_after_split=False)
    game.deal(10)
    game.split()
    assert Action.SPLIT not in game.available_actions()
    assert Action.DOUBLE not in game.available_actions()


def test_unequal_cards_cannot_split():
    game = table("8S 10H 9H 7D")
    game.deal(10)
    assert Action.SPLIT not in game.available_actions()
    with pytest.raises(RuleError):
        game.split()


def test_deal_validation():
    game = table("10S 9H 10H 8D", balance=100)
    with pytest.raises(RuleError):
        game.deal(1)
    with pytest.raises(InsufficientChips):
        game.deal(101)
    game.deal(10)
    with pytest.raises(RuleError):
        game.deal(10)
    with pytest.raises(RuleError):
        game.insurance(True)


def test_credit_allows_betting_into_debt():
    game = Blackjack(bank=Bank(10, credit=500), shoe=Shoe.stacked(cards("10S 9H 10H 8D")))
    game.deal(200)
    assert game.bank.balance == -190


def test_single_deck_never_shows_the_same_card_twice_on_the_table():
    game = Blackjack(bank=Bank(100_000), rules=Rules(decks=1))
    for _ in range(300):
        game.deal(5)
        if game.phase is Phase.INSURANCE:
            game.insurance(False)
        while game.phase is Phase.PLAYER:
            if game.current.total < 15:
                game.hit()
            else:
                game.stand()
        on_table = [c for h in game.hands for c in h.cards] + game.dealer
        assert len(on_table) == len(set(on_table))
        assert len(game.shoe) + len(game.shoe._discards) + len(on_table) == 52


def test_hole_card_hidden_until_round_ends():
    game = table("10S 9H 7H 8D")
    game.deal(10)
    assert not game.hole_revealed
    assert game.dealer_up == Card("9", "hearts")
    game.stand()
    assert game.hole_revealed


def strategy(codes: str, up: str, actions=None) -> Action:
    hand = Hand(cards(codes), 10)
    available = actions if actions is not None else {Action.HIT, Action.STAND, Action.DOUBLE, Action.SPLIT}
    return basic_strategy(hand, Card.parse(up), available)


@pytest.mark.parametrize(
    ("codes", "up", "expected"),
    [
        ("AS AH", "6D", Action.SPLIT),
        ("8S 8H", "10D", Action.SPLIT),
        ("10S 10H", "6D", Action.STAND),
        ("9S 9H", "7D", Action.STAND),
        ("5S 5H", "6D", Action.DOUBLE),
        ("AS 7H", "4D", Action.DOUBLE),
        ("AS 7H", "8D", Action.STAND),
        ("AS 7H", "9D", Action.HIT),
        ("AS 6H", "2D", Action.HIT),
        ("AS 8H", "6D", Action.DOUBLE),
        ("AS 9H", "6D", Action.STAND),
        ("10S 6H", "10D", Action.HIT),
        ("10S 6H", "5D", Action.STAND),
        ("10S 2H", "3D", Action.HIT),
        ("10S 2H", "4D", Action.STAND),
        ("6S 5H", "AD", Action.DOUBLE),
        ("6S 4H", "10D", Action.HIT),
        ("5S 4H", "3D", Action.DOUBLE),
        ("5S 3H", "6D", Action.HIT),
        ("10S 7H", "AD", Action.STAND),
    ],
)
def test_basic_strategy(codes, up, expected):
    assert strategy(codes, up) is expected


def test_basic_strategy_falls_back_when_double_unavailable():
    assert strategy("6S 5H", "6D", {Action.HIT, Action.STAND}) is Action.HIT
    assert strategy("AS 7H", "4D", {Action.HIT, Action.STAND}) is Action.STAND
