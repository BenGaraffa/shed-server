import random
from enum import Enum


def get_card_rank(card: str):
    # Extracts the numerical rank from a card string
    return int(card[1:])


class Player:
    # Represents a player in the game
    def __init__(self, name: str, websocket):
        self.name = name
        self.cards_hand = []         # Cards currently in player's hand
        self.cards_face_up = []      # Player's face-up cards
        self.cards_face_down = []    # Player's face-down cards

    def is_winner(self):
        # Check if the player has won (no cards left)
        return not (self.cards_hand or self.cards_face_up or self.cards_face_down)


class TableCards:
    # Represents the cards on the table
    def __init__(self):
        # Initialize a deck of cards, shuffle it, and prepare stacks
        self.deck = [f'{suit}{str(i).zfill(2)}' for i in range(2, 15) for suit in ['h', 'd', 'c', 's']]
        random.shuffle(self.deck)
        self.stack_discard = []  # Discarded cards stack
        self.stack_play = []     # Cards currently in play

    def top_card(self):
        # Return the top card of the play stack
        return self.stack_play[-1] if self.stack_play else None
    
    def second_card(self):
        # Return the second card from the top of the play stack
        return self.stack_play[-2] if len(self.stack_play) > 1 else None


class MagicAbilities(Enum):
    # Enumeration for different magic abilities of cards
    BURN = 1
    RESET = 2
    LOWER_THAN = 3
    INVISIBLE = 4


class MagicCard:
    # Represents a card with a magic ability
    def __init__(self, magic_ability: MagicAbilities, playable_on: set, is_effect_now: bool):
        self.magic_ability = magic_ability  # The magic ability of the card
        self.playable_on = playable_on      # Set of ranks on which the card can be played
        self.is_effect_now = is_effect_now  # If the effect of the card is immediate


class GameState:
    def __init__(self, players: dict, magic_cards: dict):
        self.players = {name: Player(name, None) for name in players}
        self.magic_cards = magic_cards
        self.table_cards = TableCards()
        self.turn_index = 0

    def can_play_card(self, card_rank: int):
        # Determines if a card can be played based on its rank and game rules
        top_card_rank = get_card_rank(self.table_cards.top_card())
        
        # Various rules for playing cards, including magic card effects
        if card_rank in self.magic_cards:
            if top_card_rank not in self.magic_cards[card_rank].playable_on:
                return False
        elif top_card_rank in self.magic_cards:
            top_magic_card = self.magic_cards[top_card_rank]
            if top_magic_card.magic_ability == MagicAbilities.LOWER_THAN and card_rank > top_card_rank:
                return False
            elif top_magic_card.magic_ability == MagicAbilities.INVISIBLE:
                second_card_rank = get_card_rank(self.table_cards.second_card())
                if second_card_rank is not None and card_rank < second_card_rank:
                    return False
        elif card_rank < top_card_rank:
            return False
        return True

    def play_card(self, card: str, player_name: str):
        # Handles the action of a player playing a card
        # Includes validation, playing the card, and checking for special conditions
        card_rank = get_card_rank(card)
        if not self.can_play_card(card_rank):
            raise ValueError(f"Can't play '{card}' on '{self.table_cards.top_card()}'")
        
        self.table_cards.stack_play.append(card)
        self.replace_card(card, player_name)

        if card_rank in self.magic_cards and self.magic_cards[card_rank].is_effect_now:
            if self.magic_cards[card_rank].magic_ability == MagicAbilities.BURN:
                self.burn_play_stack()
                return
            
        if self.check_last_four():
            self.burn_play_stack()
            return
        
        self.next_turn()

    def check_last_four(self):
        # Check if the last four cards on the play stack are of the same rank
        if len(self.table_cards.stack_play) < 4:
            return False
        return len({get_card_rank(card) for card in self.table_cards.stack_play[-4:]}) == 1
    
    def burn_play_stack(self):
        # Move all cards from the play stack to the discard stack
        self.table_cards.stack_discard.extend(self.table_cards.stack_play)
        self.table_cards.stack_play.clear()
    
    def replace_card(self, card: str, player_name: str):
        # Replace a played card from the player's hand with a new one from the deck
        player = self.players[player_name]
        player.cards_hand.remove(card)
        if self.table_cards.deck:
            player.cards_hand.append(self.table_cards.deck.pop())
        
    def next_turn(self):
        # Move to the next player's turn
        self.turn_index = (self.turn_index + 1) % len(self.players)

    def deal_cards(self):
        # Deal initial cards to all players
        for player in self.players.values():
            for _ in range(3):
                player.cards_hand.append(self.table_cards.deck.pop())
                player.cards_face_up.append(self.table_cards.deck.pop())
                player.cards_face_down.append(self.table_cards.deck.pop())


# Magic card rules
magic_cards = {
    2: MagicCard(MagicAbilities.RESET, set(range(2, 15)), False),
    3: MagicCard(MagicAbilities.INVISIBLE, set(range(2, 15)), False),
    7: MagicCard(MagicAbilities.LOWER_THAN, set(range(2, 8)), False),
    10: MagicCard(MagicAbilities.BURN, set(range(2, 15)), True)
}
