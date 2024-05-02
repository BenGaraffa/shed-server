from shed_game import can_play_card, magic_cards

def card_to_index(card: str):
    """Converts a card string to a unique index or a special value for no card."""
    if not card:
        return 60  # Special value indicating no card
    elif card == '#':
        return 52

    suit_order = {'h': 0, 'd': 1, 'c': 2, 's': 3}
    rank = int(card[1:]) - 2  # Subtract 2 since ranks start from 2
    suit = suit_order[card[0]]
    return rank + 13 * suit  # There are 13 ranks for each suit


def index_to_card(index: int):
    """Converts an index back to a card string or a marker for no card."""
    if index == 52:
        return '#'
    if index == 60:
        return ''  # Or any other suitable representation for no card

    suits = ['h', 'd', 'c', 's']
    rank = index % 13 + 2  # Add 2 since ranks start from 2
    suit = suits[index // 13]
    return f"{suit}{str(rank).zfill(2)}"


class ProbabilisticModel:
    def __init__(self):
        # Represents the probability of each card being in each location
        # Indexes 0-51 correspond to the 52 cards
        # 'player_hand', 'opponent_hand', 'deck', 'discarded', 'face_up' represent the locations
        self.card_probabilities = {
            'player_hand': [0.0] * 52,
            'opponent_hand': [0.0] * 52,
            'player_face_up': [0.0] * 52,
            'opponent_face_up': [0.0] * 52,
            'player_face_down': [0.0] * 52,
            'opponent_face_down': [0.0] * 52,
            'discarded': [0.0] * 52,
            'play_stack': [0.0] * 52,
            'deck': [1.0] * 52  # Initially, all cards are assumed to be in the deck
        }
        self.unseen_cards = [1.0] * 52
        self.deck_count = 52
        self.player_unseen_hand_count = 0
        self.opponent_unseen_hand_count = 0
        self.player_face_down_count = 0
        self.opponent_face_down_count = 0

        self.top_card = ''

    def move_card(self, card_str, from_loc, to_loc):
        card_index = card_to_index(card_str)

        if self.card_probabilities[from_loc][card_index] == 0.0:
            raise Exception(f"Card '{card_str}' not in '{from_loc}'")

        if self.unseen_cards[card_index] == 1.0:
            self.unseen_cards[card_index] = 0.0

            if from_loc == 'deck':
                self.deck_count -= 1
            elif from_loc == 'player_hand':
                self.player_unseen_hand_count -= 1
            elif from_loc == 'opponent_hand':
                self.opponent_unseen_hand_count -= 1
            elif from_loc == 'player_face_down':
                self.player_face_down_count -= 1
            elif from_loc == 'opponent_face_down':
                self.opponent_face_down_count -= 1

        if to_loc == 'play_stack': self.top_card = card_str

        for loc in self.card_probabilities:
            self.card_probabilities[loc][card_index] = 1.0 if loc == to_loc else 0.0

    def move_stack(self, from_loc, to_loc):
        for card_index, card_prob in self.card_probabilities[from_loc]:
            if card_prob == 1.0:
                self.move_card(index_to_card(card_index), from_loc, to_loc)
    
    def deal_unseen(self, no_cards, location):
        if location not in ['player_hand', 'opponent_hand', 'player_face_down', 'opponent_face_down']:
            raise Exception(f"Can't deal unseen cards to {location}")
        
        if self.deck_count - no_cards < 0:
            raise Exception(f"Can't deal {no_cards}, only {self.deck_count} left in the deck")
        
        self.deck_count -= no_cards
        if location == 'player_hand':
            self.player_unseen_hand_count += no_cards
        elif location == 'opponent_hand':
            self.opponent_unseen_hand_count += no_cards
        elif location == 'player_face_down':
            self.player_face_down_count += no_cards
        elif location == 'opponent_face_down':
            self.opponent_face_down_count += no_cards

    def get_playable_probability(self, loc, top_card):
        playable_card_probs = {}
        for card_index, card_prob in enumerate(self.card_probabilities[loc]):
            card_str = index_to_card(card_index)
            if card_prob != 0 and can_play_card(card_str, top_card, magic_cards):
                playable_card_probs[card_str] = card_prob

        # Calculate the probability of having at least one playable card
        if not playable_card_probs:
            return 0.0  # No playable cards
        else:
            # Calculate the probability of not having any playable cards
            prob_no_playable_cards = 1.0
            for _, prob in playable_card_probs.items():
                prob_no_playable_cards *= (1 - prob)
            
            # The probability of having at least one playable card is the complement of having none
            # If needed make it return probabilities too, for more specific searching
            return (1 - prob_no_playable_cards, playable_card_probs), list(playable_card_probs.keys())


    def update_probabilities(self):
        # Update probabilities based on game progress and visible actions
        # This function should be called after any action in the game
        total_unseen = sum(self.unseen_cards)
        if total_unseen > 0:
            # Update probabilities for unknown cards
            for i in range(52):
                # Check if the card's location is unknown (not confirmed to be in any specific location)
                if self.unseen_cards[i] == 1.0:
                    self.card_probabilities['deck'][i] = self.deck_count / total_unseen
                    self.card_probabilities['player_hand'][i] = self.player_unseen_hand_count / total_unseen
                    self.card_probabilities['opponent_hand'][i] = self.opponent_unseen_hand_count / total_unseen
                    self.card_probabilities['player_face_down'][i] = self.player_face_down_count / total_unseen
                    self.card_probabilities['opponent_face_down'][i] = self.opponent_face_down_count / total_unseen
    

    def aggregate_probabilities(self):
        """
        Aggregate the probabilities from all locations for each card into a single array.

        Returns:
        - list: A list of probabilities where each element represents the aggregated probability
                of the corresponding card being in any of the tracked locations.
        """
        total_probabilities = [0.0] * 52  # Initialize an array for the aggregated probabilities
        for i in range(52):  # Iterate over each card
            for location in self.card_probabilities:  # Sum the probabilities across all locations
                total_probabilities[i] += self.card_probabilities[location][i]
        return total_probabilities

    def initialize_game(self, player_hand, player_face_up, opponent_face_up):

        # Update probabilities based on the starting hands and face-up cards
        for card in player_hand:
            self.move_card(card, 'deck', 'player_hand')
        
        for card in player_face_up:
            self.move_card(card, 'deck', 'player_face_up')

        for card in opponent_face_up:
            self.move_card(card, 'deck', 'opponent_face_up')

        self.deal_unseen(3, 'opponent_hand')
        self.deal_unseen(3, 'player_face_down')
        self.deal_unseen(3, 'opponent_face_down')
        
        # Update probabilities for the remaining deck and opponent's hand
        self.update_probabilities()

    def get_card_probability(self, card_str, location):
        card_index = card_to_index(card_str)
        return self.card_probabilities[location][card_index]
    
    def __eq__(self, other):
        if not isinstance(other, ProbabilisticModel):
            # don't attempt to compare against unrelated types
            return NotImplemented

        return (
            self.card_probabilities == other.card_probabilities and
            self.unseen_cards == other.unseen_cards and
            self.deck_count == other.deck_count and
            self.player_unseen_hand_count == other.player_unseen_hand_count and
            self.opponent_unseen_hand_count == other.opponent_unseen_hand_count and
            self.player_face_down_count == other.player_face_down_count and
            self.opponent_face_down_count == other.opponent_face_down_count and
            self.top_card == other.top_card
        )

# Usage example:
player_hand_str = ['h06', 'd03', 'c10']
player_face_up_str = ['h05', 'd06', 'c07']
opponent_face_up_str = ['h08', 'd09', 'c04']

prob_model = ProbabilisticModel()
prob_model.initialize_game(player_hand_str, player_face_up_str, opponent_face_up_str)

# # Display the probabilities (for demonstration purposes)
# print("Probabilities after game setup:")
# for location in prob_model.card_probabilities:
#     print(f"{location}: {prob_model.card_probabilities[location]}")

# print("player_face_down sum:", round(sum(prob_model.card_probabilities['player_face_down'])))

# print("Unseen Cards:")
# print(prob_model.unseen_cards)

# print("Aggregated Probabilities:")
# print(prob_model.aggregate_probabilities())
# top_card_str = 'h14'  # Example top card
# broken...
# print(prob_model.get_playable_probability('opponent_hand', 'h11'))
# print(f"Probability that opponent can play on {top_card_str}: {prob_opponent_can_play:.2f}")

# for card in player_hand_str:
#     print(prob_model.get_playable_probability('opponent_hand', card))
# prob, playable_card_probs = prob_model.get_playable_probability('opponent_hand', 'h08')

# print(prob, len(playable_card_probs))

