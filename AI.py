import torch
import torch.nn as nn
import torch.optim as optim
import random
from pathlib import Path
from datetime import datetime

def card_to_index(card: str):
    """Converts a card string to a unique index or a special value for no card."""
    if not card:
        return 60  # Special value indicating no card

    suit_order = {'h': 0, 'd': 1, 'c': 2, 's': 3}
    rank = int(card[1:]) - 2  # Subtract 2 since ranks start from 2
    suit = suit_order[card[0]]
    return rank + 13 * suit  # There are 13 ranks for each suit


def index_to_card(index: int):
    """Converts an index back to a card string or a marker for no card."""
    if index == 60:
        return ''  # Or any other suitable representation for no card

    suits = ['h', 'd', 'c', 's']
    rank = index % 13 + 2  # Add 2 since ranks start from 2
    suit = suits[index // 13]
    return f"{suit}{str(rank).zfill(2)}"


def get_binary_indicators(cards: list):
    """Creates a 52-binary indicator array for the given list of cards."""
    try:
        indicators = [0] * 52
        for card in cards:
            if card == '#' or card is None:
                continue
            index = card_to_index(card)
            indicators[index] = 1
        return indicators
    except Exception as e:
        print(f"Card value: {card}, Card index: {card_to_index(card)}", e)


def save_to_file(filename, data):
    Path(".\loss_history").mkdir(parents=True, exist_ok=True)
    with open(f".\loss_history\{filename}", 'a') as file:  # 'a' mode appends to the file
        file.write(data + "\n")


class DQN(nn.Module):
    def __init__(self, input_size, output_size):
        super(DQN, self).__init__()
        self.net = nn.Sequential(
            nn.Linear(input_size, 128),
            nn.ReLU(),
            nn.Linear(128, 256),
            nn.ReLU(),
            nn.Linear(256, output_size)
        )

    def forward(self, x):
        return self.net(x)


class AIAgent:
    def __init__(self, name):
        self.name = name
        # input_size = 168
        self.model = DQN(input_size=168, output_size=52)
        self.optimizer = optim.Adam(self.model.parameters(), lr=0.001)
        self.criterion = nn.MSELoss()
        self.history = []
        self.accurate_actions = 0
        self.total_actions = 0

        # If you have a GPU, move the model to GPU
        if torch.cuda.is_available():
            print('CUDA AVAILABLE')
            self.model.cuda()


    def decide_move(self, player_states, table_cards, playable_cards, same_cards_count):
        """
        Decide on the next move based on the current game state.
        
        :param game_state: The current state of the game
        :return: The chosen action (a card to play or a special action)
        """
        player_index = [player.name for player in player_states].index(self.name)

        player_state = player_states[player_index]
        # opponent_player_state = player_states[(player_index + 1) % len(player_states)]
        
        player_hand = get_binary_indicators(player_state.cards_hand) # 52 binary indicator
        # player_face_up = get_binary_indicators(player_state.cards_face_up) # 52 binary indicator
        # player_face_down = [1 if i < len(player_state.cards_face_down) else 0 for i in range(1, 4)] # 3 binary indicator
        # opponent_hand_count = len(opponent_player_state.cards_hand) # 1 integer
        # opponent_face_up = get_binary_indicators(opponent_player_state.cards_face_up) # 52 binary indicator
        # opponent_face_down = [1 if i < len(opponent_player_state.cards_face_down) else 0 for i in range(1, 4)] # 3 binary indicator
        # reversed_stack_play = list(reversed(table_cards.stack_play))
        # play_stack = [card_to_index(reversed_stack_play[i]) if i <= len(table_cards.stack_play) - 1 else 60 for i in range(3)] # 3 integers

        # 1 integer representing range of cards in deck (low, medium, high)
        # if len(table_cards.deck) < 20:
        #     deck_level = 0
        # elif 20 <= len(table_cards.deck) <= 40:
        #     deck_level = 1
        # else:
        #     deck_level = 2

        # normalise variables
        # opponent_hand_count = opponent_hand_count / 52
        # play_stack = [card / 60 for card in play_stack]
        # same_round_count = same_cards_count / 10

        # flatten
        # round_state = player_hand + play_stack + player_face_up + player_face_down + [opponent_hand_count] + opponent_face_up + opponent_face_down  + [deck_level] + [same_round_count]

        # simplified round_state
        top_card = (card_to_index(table_cards.stack_play[-1]) if len(table_cards.stack_play) > 0 else 60) / 60
        round_state = player_hand + [top_card] + ([0] * 115)

        state_tensor = torch.tensor([round_state], dtype=torch.float32)
        if torch.cuda.is_available():
            state_tensor = state_tensor.cuda()

        with torch.no_grad():
            predicted_action = self.model(state_tensor)

        # Select the card with the highest score
        highest_score_index = predicted_action.argmax(dim=1).item()
        predicted_card = index_to_card(highest_score_index)

        move_was_correct = predicted_card in playable_cards
        predicted_action = get_binary_indicators([predicted_card])
        self.learn_from_move(round_state, predicted_action, move_was_correct)
        
        # Check if the predicted card is in playable_cards
        if move_was_correct:
            chosen_card = [predicted_card]
            self.accurate_actions += 1
        else:
            # Fallback strategy if the predicted card is not playable
            chosen_card = [random.choice(playable_cards)]
            given_action = get_binary_indicators(chosen_card)
            self.learn_from_move(round_state, given_action, True)

        self.total_actions += 1

        # Randomly choose one of the playable cards as the action
        action = get_binary_indicators(chosen_card)
        
        self.history.append((round_state, action))
        return chosen_card
    
    def learn_from_move(self, last_state, last_action, move_was_correct):
        # Convert the last state and action to tensors
        state_tensor = torch.tensor(last_state, dtype=torch.float32)
        action_tensor = torch.tensor(last_action, dtype=torch.float32)

        if torch.cuda.is_available():
            state_tensor = state_tensor.cuda()
            action_tensor = action_tensor.cuda()

        # Forward pass to get predictions
        predictions = self.model(state_tensor)

        # Use a different reward based on whether the move was correct
        reward = 1.0 if move_was_correct else -1.0
        target = torch.full(predictions.shape, reward, dtype=torch.float32)

        # Calculate loss and perform backpropagation
        loss = self.criterion(predictions, target)
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

    
    def learn_from_game_end(self, final_reward):
        now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
        for state, action in self.history:
            # Convert to tensors
            state = torch.tensor(state, dtype=torch.float32)
            action = torch.tensor(action, dtype=torch.float32)

            # Forward pass to get predictions
            predictions = self.model(state)

            # The target in basic Q-learning is the reward of the action
            # Here, we use final_reward as the target since you're updating at the end of the game
            # Adjust this part if your learning strategy is different
            target = torch.full(predictions.shape, final_reward, dtype=torch.float32)

            # Calculate loss (assuming Binary Cross-Entropy)
            loss = self.criterion(predictions, target)

            # Backpropagation
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()

            # Logging
            # loss_info = f"Loss: {loss.item()}"
            # save_to_file(f"game_logs_{self.name}_{now}_{final_reward}.txt", loss_info)
        print(f"Accurate actions: {self.accurate_actions}/{self.total_actions}")
        self.accurate_actions = 0
        self.total_actions = 0
        self.history = []
