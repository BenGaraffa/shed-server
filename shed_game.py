import random
from datetime import datetime
from enum import Enum
from pathlib import Path
import pickle

def get_card_rank(card: str):
    # Extracts the numerical rank from a card string
    return None if not card else int(card[1:]) 

class PlayerState:
    # Represents a player in the game
    def __init__(self, name: str):
        self.name = name
        self.cards_hand = []         # Cards currently in player's hand
        self.cards_face_up = []      # Player's face-up cards
        self.cards_face_down = []    # Player's face-down cards

    def is_winner(self):
        # Check if the player has won (no cards left)
        return not (self.cards_hand or self.cards_face_up or self.cards_face_down)
    
    def get_json(self):
        # Return json of the player's current state
        return {
            'name': self.name,
            'cards_hand': self.cards_hand.copy(),
            'cards_face_up': self.cards_face_up.copy(),
            'cards_face_down': self.cards_face_down.copy()
        }

    def __repr__(self):
        string = f"Name: {self.name}\n"
        string += f"Hand: {self.cards_hand}\n"
        string += f"Face Up: {self.cards_face_up}\n"
        return string + f"Face Down: {self.cards_face_down}\n"
        

class TableCards:
    # Represents the cards on the table
    def __init__(self):
        # Initialize a deck of cards, shuffle it, and prepare stacks
        self.deck = [f'{suit}{str(i).zfill(2)}' for i in range(2, 15) for suit in ['h', 'd', 'c', 's']]
        self.stack_discard = []  # Discarded cards stack
        self.stack_play = []     # Cards currently in play
    
    def deck_shuffle(self, seed = None):
        # Using datetime to generate a granular seed
        if not seed:
            seed = int(datetime.now().timestamp() * 1e6)
            
        random.Random(seed).shuffle(self.deck)
        return seed

    def get_json(self):
        # Return json of the table's current state
        return {
            'deck': self.deck.copy(),
            'stack_discard': self.stack_discard.copy(),
            'stack_play': self.stack_play.copy()
        }


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
        self.round_index = 0
        self.game_start_time = ''
        self.game_history = {'magic_cards': magic_cards}
        self.same_cards_count = 0
        self.last_cards = []
        self.is_game_over = False
        self.winning_order = []
    
    def store_game_state(self):
        self.game_history[self.game_start_time]['rounds'][self.round_index]['player_states'] = [player.get_json() for player in self.player_states]
        self.game_history[self.game_start_time]['rounds'][self.round_index]['table_cards'] = self.table_cards.get_json()
            
    def start_game(self):
        self.game_start_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
        seed = self.table_cards.deck_shuffle()
        self.game_history[self.game_start_time] = {'seed': seed, 'rounds': []}

        with open('seeds.txt', 'w') as file:
            file.write(str(seed))

        self.deal_cards()
        self.create_round()
        self.store_game_state()
        self.round_index += 1
        self.create_round()

    def create_round(self):
        self.game_history[self.game_start_time]['rounds'].append({player_index: [] for player_index in range(len(self.player_states))})

    def init_turn(self):
        # Choose the first player and set the start index
        if self.turn_index == self.start_index and self.round_index == 1:
            self.start_index = self.choose_first_player()
            self.turn_index = self.start_index
        self.check_round_start()

        if self.player_states[self.turn_index].is_winner():
            return [None]
        
        # send playable cards
        playable_cards = self.get_playable_cards(self.turn_index)
        if playable_cards:
            return playable_cards
        
        return ['#']
    
    def complete_turn(self, actions=[]):
        # Round start/store logic
        player_state = self.player_states[self.turn_index]
        # Parse actions
        for action in actions:
            match action:
                case None:
                    pass
                case '#':
                    # Pickup
                    player_state.cards_hand.extend(self.table_cards.stack_play)
                    self.table_cards.stack_play.clear()
                    self.append_player_actions(action)
                case _:
                    # Play card
                    result = self.play_card(action)
                    self.append_player_actions(action)
                    if  result == '*' and self.get_player_last_action() != '*':
                        self.append_player_actions('*')
                        
        if player_state.is_winner():
            self.check_game_over()
            
        if self.is_game_over:
            self.store_game_state()
            # print(f"Winning players: {self.winning_order}")
            return

        # Load next player's turns
        if actions[0] == None or self.get_player_last_action() != '*':
            self.next_turn()

    def get_player_index(self, player_name: str):
        player_names = [player.name for player in self.player_states]
        return player_names.index(player_name)

    def card_swap(self, player_name, cards=[]):
        player_state = self.player_states[self.get_player_index(player_name)]
        if not cards[0] in player_state.cards_hand:
            raise ValueError(f"{cards[0]} not in {player_name}'s hand")
        if not cards[1] in player_state.cards_face_up:
            raise ValueError(f"{cards[0]} not in {player_name}'s face up cards")

        hand_index = player_state.cards_hand.index(cards[0])
        face_up_index = player_state.cards_face_up.index(cards[1])
        player_state.cards_hand[hand_index] = cards[1]
        player_state.cards_face_up[face_up_index] = cards[0]

    def append_player_actions(self, action):
        self.game_history[self.game_start_time]['rounds'][self.round_index][self.turn_index].append(action)
    
    def get_player_last_action(self):
        player_history = self.game_history[self.game_start_time]['rounds'][self.round_index][self.turn_index]
        return None if not player_history else player_history[-1]

    def check_round_start(self):
        if self.turn_index == self.start_index:
            self.store_game_state()
            self.create_round()
            self.round_index += 1
            self.check_same_cards()

    def check_same_cards(self):
        if self.table_cards.deck:
            return
        current_cards = set(card for player_state in self.player_states for card in player_state.cards_hand)
        current_cards.update(set(self.table_cards.stack_play))

        if current_cards == self.last_cards:
            self.same_cards_count += 1
        else:
            self.last_cards = current_cards
            self.same_cards_count = 0
        
        if self.same_cards_count == 10:
            # print(f"Game over, due to repetition")
            self.is_game_over = True

    def check_game_over(self):
        for player_state in self.player_states:
            if player_state.is_winner() and player_state.name not in self.winning_order:
                self.winning_order.append(player_state.name)

        if len([None for player_state in self.player_states if not player_state.is_winner()]) <= 1:
            self.is_game_over = True

    def get_last_player_actions(self):
        round_ = self.game_history[self.game_start_time]['rounds'][self.round_index]
        index = len(self.player_states) - 1 if self.turn_index - 1 == -1 else self.turn_index - 1
            
        if not round_[index]:
            raise ValueError(f"{self.player_states[index].name} has no previous turn")
        return round_[self.turn_index] if self.get_player_last_action() == '*' else round_[index]
    
    def reset(self, new_players: dict = None):
        # Reset game-related variables
        self.table_cards = TableCards()  # Reset the table cards
        self.start_index = 0             # Reset the start index
        self.turn_index = 0              # Reset the turn index
        self.round_index = 0             # Reset the round index
        self.is_game_over = False        # Reset the game over state
        self.winning_order = []          # Reset the winning order

        # Rotate the player_states list to change the starting player
        if not new_players:
            self.player_states.insert(0, self.player_states.pop())
            return
        
        # Create a queue of new players
        new_player_queue = [PlayerState(name) for name in new_players if name not in {player.name for player in self.player_states}]

        # Replace players who have left with new players from the queue
        for i, player_state in enumerate(self.player_states):
            if player_state.name not in new_players:
                self.player_states[i] = new_player_queue.pop(0) if new_player_queue else None

        # Remove None values (if any players were not replaced)
        self.player_states = [player for player in self.player_states if player is not None]

        # Add any remaining new players to the end of the list
        self.player_states.extend(new_player_queue)

        self.player_states.insert(0, self.player_states.pop())

    def choose_first_player(self):
        lowest_cards = [self.get_lowest_card(player_state) for player_state in self.player_states]
        min_card = min(lowest_cards)
        return self.turn_index if min_card == 15 else lowest_cards.index(min_card)
    
    def get_lowest_card(self, player_state: PlayerState):
        return min([card_rank for card in player_state.cards_hand if (card_rank := get_card_rank(card)) not in self.magic_cards], default=15)

    def get_playable_cards(self, player_index: int):
        player_state = self.player_states[player_index]
        if player_state.cards_hand:
            return [card for card in player_state.cards_hand if self.can_play_card(card)]
        elif player_state.cards_face_up:
            return [card for card in player_state.cards_face_up if self.can_play_card(card)]
        elif player_state.cards_face_down:
            return [card for card in player_state.cards_face_down if self.can_play_card(card)]

    def can_play_card(self, card: str):
        card_rank = get_card_rank(card)

        effective_top_card = self.find_effective_top_card()
        effective_top_card_rank = get_card_rank(effective_top_card) if effective_top_card else None
        
        # Filter cards for lowest if on first round
        if self.round_index == 1 and self.start_index == self.turn_index:
            return card_rank == self.get_lowest_card(self.player_states[self.turn_index])

        # Allow card if nothing on deck
        if not effective_top_card_rank:
            return True

        # Magic card rules (if the played card is a magic card)
        if card_rank in self.magic_cards:
            if effective_top_card_rank not in self.magic_cards[card_rank].playable_on:
                return False

        # Check for LOWER_THAN magic ability on the effective top card
        elif effective_top_card_rank in self.magic_cards:
            top_magic_card = self.magic_cards[effective_top_card_rank]
            if top_magic_card.magic_ability == MagicAbilities.LOWER_THAN and card_rank > effective_top_card_rank:
                return False

        # Regular rule for non-magic cards or when there's no effective top card
        elif effective_top_card_rank and card_rank < effective_top_card_rank:
            return False

        return True

    def find_effective_top_card(self):
        # Find the first card that is not an Invisible magic card
        for card in reversed(self.table_cards.stack_play):
            card_rank = get_card_rank(card)
            if not (card_rank in self.magic_cards and self.magic_cards[card_rank].magic_ability == MagicAbilities.INVISIBLE):
                return card
        return None

    def play_card(self, card: str):
        # Handles the action of a player playing a card
        # Includes validation, playing the card, and checking for special conditions
        if not self.can_play_card(card):
            raise ValueError(f"Can't play '{card}' on '{self.find_effective_top_card()}'")
        
        player_state = self.player_states[self.turn_index]
        if card in player_state.cards_hand:
            player_state.cards_hand.remove(card)
            # Replace the played card from the player's hand with a new one from the deck
            if self.table_cards.deck:
                player_state.cards_hand.append(self.table_cards.deck.pop())
        elif card in player_state.cards_face_up:
            player_state.cards_face_up.remove(card)
        elif card in player_state.cards_face_down:
            player_state.cards_face_down.remove(card)
        else:
            raise ValueError(f"Player {self.turn_index} ({player_state.name}) doesn't have '{card}'")        

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

    def output_history(self):
        Path(".\game_history").mkdir(parents=True, exist_ok=True)
        output_filename = f".\game_history\game_{self.game_start_time}_{self.game_history[self.game_start_time]['seed']}_history_output.txt"
        with open(output_filename, "w+") as file:
            file.write(f"Seed: {self.game_history[self.game_start_time]['seed']}\n\n")
            for i, round_ in enumerate(self.game_history[self.game_start_time]['rounds']):
                file.write(f"Round {i}:\n{round_}\n\n")

        print(f"Game history written to {output_filename}")

# Magic card rules
magic_cards = {
    2: MagicCard(MagicAbilities.RESET, set(range(2, 15)), False),
    3: MagicCard(MagicAbilities.INVISIBLE, set(range(2, 15)), False),
    7: MagicCard(MagicAbilities.LOWER_THAN, set(range(2, 8)), False),
    10: MagicCard(MagicAbilities.BURN, set(range(2, 15)), True)
}

if __name__ == '__main__':
    players = {'Ben0': [], 'Ben1': [], 'Ben2': [], 'Ben3': []}
    game = GameState(players, magic_cards)
    game.start_game()

    game.card_swap(game.player_states[game.turn_index].name, [game.player_states[game.turn_index].cards_hand[0], game.player_states[game.turn_index].cards_face_up[0]])

    while not game.is_game_over:
        # play random  cards
        playable_cards = game.init_turn()
        game.complete_turn([playable_cards[0]])
    
    game.output_history()

    # game.reset()

    # game.start_game()

    # while not game.is_game_over:
    #     # play highest card available
    #     playable_cards = game.init_turn()
    #     if playable_cards == ['#']:
    #         game.complete_turn(['#'])
    #         continue
    #     playable_card_ranks = [get_card_rank(card) for card in playable_cards]
    #     highest_card =  playable_cards[playable_card_ranks.index(max(playable_card_ranks))]
    #     game.complete_turn([highest_card])

    # game.output_history()

    # game.reset()

    # game.start_game()

    # while not game.is_game_over:
    #     # play highest card available
    #     playable_cards = game.init_turn()
    #     if playable_cards == ['#']:
    #         game.complete_turn(['#'])
    #         continue
    #     playable_card_ranks = [get_card_rank(card) for card in playable_cards]
    #     lowest_card =  playable_cards[playable_card_ranks.index(min(playable_card_ranks))]
    #     game.complete_turn([lowest_card])

    # game.output_history()