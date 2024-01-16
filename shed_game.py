import random
from datetime import datetime
from enum import Enum


def get_card_rank(card: str):
    # Extracts the numerical rank from a card string
    return int(card[1:])


class PlayerState:
    # Represents a player in the game
    def __init__(self, name: str):
        self.name = name
        self.cards_hand = []         # Cards currently in player's hand
        self.cards_face_up = []      # Player's face-up cards
        self.cards_face_down = []    # Player's face-down cards

    def is_winner(self):
        # Check if the player has won (no cards left
        return not (self.cards_hand or self.cards_face_up or self.cards_face_down)
    
    def __repr__(self):
        string = f"Name: {self.name}\n"
        string += f"Hand: {self.cards_hand}\n"
        string += f"Face Down: {self.cards_face_up}\n"
        return string + f"Face Up: {self.cards_face_down}\n"
        

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
        self.magic_cards = magic_cards
        self.player_states = [PlayerState(player_name) for player_name in players.keys()]
        self.table_cards = TableCards()
        self.start_index = 0
        self.turn_index = 0
        self.is_game_over = False
        self.game_history = {'magic_cards': magic_cards}
    
    def store_game_state(self):
        self.game_history[self.game_start_time].append({0: [], 1: [], 'player_states': {}, 'table_cards': {}})
        # for player in player_states:
            
    def start_game(self):
        if self.is_game_over == True: 
            self.reset()
        self.deal_cards()
        self.start_index = self.choose_first_player()
        self.turn_index = self.start_index
        self.round_index = 0
        self.game_start_time = datetime.now().strftime("%Y-%m-%d | %H:%M:%S")
        self.game_history[self.game_start_time] = [self.create_round()]

    def create_round(self):
        round_ = {player_index: [] for player_index in range(len(self.player_states))}
        round_['player_states'] = self.player_states # Change to json objectable format later
        round_['table_cards'] = self.table_cards
        return round_

    def init_turn(self):
        # send playable cards
        playable_cards = self.get_playable_cards(self.turn_index)
        if playable_cards:
            return playable_cards
        
        self.complete_turn(['#'])
        return []
    
    # result = init_turn()
    # if not result:
    #     send message to player
    #     return

    def extend_player_actions(self, action):
        self.game_history[self.game_start_time][self.round_index][self.turn_index].extend(action)
    
    def get_last_player_action(self):
        return self.game_history[self.game_start_time][self.round_index][self.turn_index][-1]
            
    def complete_turn(self, actions=[]):
        player_state = self.player_states[self.turn_index]
        # Parse actions
        for action in actions:
            match action:
                case '#':
                    # Pickup
                    player_state.cards_hand.extend(self.table_cards.stack_play)
                    self.table_cards.stack_play.clear()
                    self.extend_player_actions(action)
                case _:
                    # Play card
                    result = self.play_card(action)
                    self.extend_player_actions(action)
                    if  result == '*' and self.get_last_player_action() != '*':
                        self.extend_player_actions('*')

        # What happened...
        player_state.name
        # send actions???

        # Load next player's turn
    
        self.next_turn()

        # Turn histoy append
    
    def reset(self, new_players: dict):
        # Rotate the player_states list to change the starting player
        self.player_states.insert(0, self.player_states.pop())

        # Create sets of old and new player names
        old_player_names = set(player_state.name for player_state in self.player_states)
        new_player_names = set(new_players.keys())

        # Only proceed if there are changes in the player list
        if old_player_names != new_player_names:
            # List of new player names
            new_player_list = list(new_players.keys())

            # Replace players who have left with new players, or mark them for removal
            new_player_index = 0
            for i in range(len(self.player_states)):
                if self.player_states[i].name not in new_players:
                    if new_player_index < len(new_player_list):
                        # Replace with a new player
                        self.player_states[i] = PlayerState(new_player_list[new_player_index])
                        new_player_index += 1
                    else:
                        # Mark for removal
                        self.player_states[i] = None

            # Remove None values
            self.player_states = [player for player in self.player_states if player is not None]

            # Add remaining new players to the end of the list
            if new_player_index < len(new_player_list):
                remaining_new_players = new_player_list[new_player_index:]
                self.player_states.extend(PlayerState(name) for name in remaining_new_players)

        # Reset game-related variables
        self.table_cards = TableCards()  # Reset the table cards
        self.is_game_over = False        # Reset game over flag
        self.turn_index = 0              # Reset the turn index

    def choose_first_player(self):
        lowest_cards = [self.get_lowest_card(player_state) for player_state in self.player_states]
        return lowest_cards.index(min(lowest_cards))
    
    def get_lowest_card(self, player_state: PlayerState):
        return min([card_rank for card in player_state.cards_hand if (card_rank := get_card_rank(card)) not in self.magic_cards.keys()])

    def get_playable_cards(self, player_index: int):
        player_state = self.player_states[player_index]
        if player_state.cards_hand:
            return [card for card in player_state.cards_hand if self.can_play_card(card)]
        elif player_state.cards_face_up:
            return [card for card in player_state.cards_face_up if self.can_play_card(card)]
        elif player_state.cards_face_down:
            return [card for card in player_state.cards_face_down if self.can_play_card(card)]

    def can_play_card(self, card: str):
        # Determines if a card can be played based on its rank and game rules
        card_rank = get_card_rank(card)
        if self.round_index == 0 and self.start_index == self.turn_index:
            return card_rank == self.get_lowest_card(self.player_states[self.turn_index])

        top_card_rank = get_card_rank(self.table_cards.top_card())

        if not top_card_rank:
            return True
        
        # Various rules for playing cards, including magic card effects
        if card_rank in self.magic_cards:
            if top_card_rank in self.magic_cards[card_rank].playable_on:
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

    def play_card(self, card: str):
        # Handles the action of a player playing a card
        # Includes validation, playing the card, and checking for special conditions
        if not self.can_play_card(card):
            raise ValueError(f"Can't play '{card}' on '{self.table_cards.top_card()}'")
        
        player_state = self.player_states[self.turn_index]
        if card in player_state.cards_hand:
            player_state.cards_hand.remove(card)
        elif card in player_state.cards_face_up:
            player_state.cards_face_up.remove(card)
        elif card in player_state.cards_face_down:
            player_state.cards_face_down.remove(card)
        else:
            raise ValueError(f"Can't play '{card}' as '{player_state}'")        

        self.table_cards.stack_play.append(card)

        card_rank = get_card_rank(card)
        if card_rank in self.magic_cards and self.magic_cards[card_rank].is_effect_now:
            if self.magic_cards[card_rank].magic_ability == MagicAbilities.BURN:
                return self.burn_play_stack()
                
        if self.check_last_four():
            return self.burn_play_stack()
        
        return ''

    def check_last_four(self):
        # Check if the last four cards on the play stack are of the same rank
        if len(self.table_cards.stack_play) < 4:
            return False
        return len({get_card_rank(card) for card in self.table_cards.stack_play[-4:]}) == 1
    
    def burn_play_stack(self):
        # Move all cards from the play stack to the discard stack
        self.table_cards.stack_discard.extend(self.table_cards.stack_play)
        self.table_cards.stack_play.clear()
        return '*'
    
    def replace_card(self, card: str, player_index: int):
        # Replace a played card from the player's hand with a new one from the deck
        if self.table_cards.deck:
            self.player_states[player_index].cards_hand.append(self.table_cards.deck.pop())
        
    def next_turn(self):
        # Move to the next player's turn
        self.turn_index = (self.turn_index + 1) % len(self.player_states)

    def deal_cards(self):
        # Deal initial cards to all players
        for player_state in self.player_states:
            for _ in range(3):
                player_state.cards_hand.append(self.table_cards.deck.pop())
                player_state.cards_face_up.append(self.table_cards.deck.pop())
                player_state.cards_face_down.append(self.table_cards.deck.pop())


# Magic card rules
magic_cards = {
    2: MagicCard(MagicAbilities.RESET, set(range(2, 15)), False),
    3: MagicCard(MagicAbilities.INVISIBLE, set(range(2, 15)), False),
    7: MagicCard(MagicAbilities.LOWER_THAN, set(range(2, 8)), False),
    10: MagicCard(MagicAbilities.BURN, set(range(2, 15)), True)
}


if __name__ == '__main__':
    game = GameState({'Ben1': [], 'Ben2': []}, magic_cards)
    game.start_game()
    for i, player_state in enumerate(game.player_states):
        print(i, player_state)
    print(game.turn_index)

    print(actions := game.init_turn())
    game.complete_turn([actions[0]])
    print(game.table_cards.deck)
    print(game.table_cards.stack_play)
    print(game.table_cards.stack_discard)