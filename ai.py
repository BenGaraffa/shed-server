import pickle

def extract_card_counts(player_state):
    """Extracts the number of cards in hand, face-up, and face-down."""
    return len(player_state['cards_hand']), len(player_state['cards_face_up']), len(player_state['cards_face_down'])

def extract_player_actions(round_data, player_index):
    """Extracts the count of specific actions ('*' for burn, '#' for pickup) taken by a player in a round."""
    player_actions = round_data.get(player_index, [])
    return player_actions.count('*'), player_actions.count('#')

def extract_sequential_actions(rounds, round_index, player_index, max_actions_length=5):
    """Extracts the actions of a player in the current and previous rounds, if available."""
    current_round_actions = rounds[round_index].get(player_index, [])
    previous_round_actions = rounds[round_index - 1].get(player_index, []) if round_index > 0 else []

    # Truncate or pad the lists to ensure a fixed length
    current_round_actions = current_round_actions[:max_actions_length] + ['None'] * (max_actions_length - len(current_round_actions))
    previous_round_actions = previous_round_actions[:max_actions_length] + ['None'] * (max_actions_length - len(previous_round_actions))

    return current_round_actions, previous_round_actions

def extract_round_specific_actions(round_data, player_index, max_actions_length=5):
    """Extracts the actions taken by a player in a specific round."""
    actions = round_data.get(player_index, [])
    # Ensure fixed length
    return actions[:max_actions_length] + ['None'] * (max_actions_length - len(actions))


def extract_actions_before_burn(round_data, player_index, num_players, start_index, max_actions_length=5):
    """
    Extracts the actions of a player before a burn action considering the start index of the round.
    """
    actions_before_burn = []
    
    # Determine the order of players based on the start_index
    player_order = [(i + start_index) % num_players for i in range(num_players)]

    # Find the position of the current player in the order
    current_player_pos = player_order.index(player_index)

    # Iterate through the actions in the order of play
    for pos in range(current_player_pos, current_player_pos - num_players, -1):
        actual_player_index = player_order[pos % num_players]
        player_actions = round_data.get(actual_player_index, [])
        
        for action in player_actions:
            if action == '*' or len(actions_before_burn) >= max_actions_length:
                # Either a burn is found or max length is reached
                return actions_before_burn + ['None'] * (max_actions_length - len(actions_before_burn))
            actions_before_burn.append(action)

    return actions_before_burn + ['None'] * (max_actions_length - len(actions_before_burn))


def extract_hand_size_change(player_state_before, player_state_after):
    """Calculates the change in the number of cards in hand between two rounds."""
    return len(player_state_before['cards_hand']) - len(player_state_after['cards_hand'])

def extract_actions_when_almost_winning(player_state, round_data, player_index, max_actions_length=5):
    """Extracts the actions of a player when they are close to winning."""
    actions = []
    if len(player_state['cards_hand']) <= 2:
        actions = round_data.get(player_index, [])
    # Ensure fixed length
    return actions[:max_actions_length] + ['None'] * (max_actions_length - len(actions))

def extract_plays_before_pickup(round_data, round_index, rounds, player_index, num_players, start_index):
    """
    Counts how many times a player plays before a player who has not run out of cards picks up.
    """
    plays_before_pickup = 0
    player_actions = round_data.get(player_index, [])

    # Determine the order of players based on the start_index
    player_order = [(i + start_index) % num_players for i in range(num_players)]

    # Find the position of the current player and the next player in the order
    current_player_pos = player_order.index(player_index)
    next_player_pos = (current_player_pos + 1) % num_players
    next_player_index = player_order[next_player_pos]

    next_player_round_data = rounds[round_index].get(next_player_index, [])
    next_player_state = rounds[round_index]['player_states'][next_player_index]

    if len(next_player_state['cards_hand']) + len(next_player_state['cards_face_up']) + len(next_player_state['cards_face_down']) > 0:
        # Check if the next player with cards picks up after the current player's actions
        for action in player_actions:
            if '#' in next_player_round_data:  # '#' represents a pickup
                if next_player_round_data.index('#') > player_actions.index(action):
                    plays_before_pickup += 1
                break

    return plays_before_pickup

def prepare_dataset(game_histories):
    features_labels = []

    for game in game_histories:
        start_index = game['start_index']
        winning_order = game['winning_order']
        rounds = game['game_history']['rounds']
        num_players = len(winning_order) + 1

        for round_index, round_info in enumerate(rounds):
            player_states = round_info['player_states']

            for player_index, player_state in enumerate(player_states):
                # Extract features using the functions
                card_counts = extract_card_counts(player_state)
                player_actions = extract_player_actions(round_info, player_index)
                sequential_actions = extract_sequential_actions(rounds, round_index, player_index)
                round_specific_actions = extract_round_specific_actions(round_info, player_index)
                actions_before_burn = extract_actions_before_burn(round_info, player_index, num_players, start_index)
                hand_size_change = extract_hand_size_change(round_info['player_states'][player_index - 1] if player_index > 0 else player_states[0], player_state)
                actions_almost_winning = extract_actions_when_almost_winning(player_state, round_info, player_index)
                plays_before_pickup = extract_plays_before_pickup(round_info, round_index, rounds, player_index, num_players, start_index)

                # Ensure all features are in tuple format
                sequential_actions_tuple = tuple(sequential_actions)
                round_specific_actions_tuple = tuple(round_specific_actions)
                actions_before_burn_tuple = tuple(actions_before_burn)
                actions_almost_winning_tuple = tuple(actions_almost_winning)

                # Combine features
                combined_features = (card_counts + player_actions + sequential_actions_tuple + round_specific_actions_tuple + actions_before_burn_tuple + (hand_size_change,) + actions_almost_winning_tuple + (plays_before_pickup,))

                # Label based on the player's final position
                position = winning_order.index(player_state['name']) + 1 if player_state['name'] in winning_order else len(player_states)

                # Combine features and label
                features_labels.append((combined_features, position))

    return features_labels

# Loading and preparing the dataset
def load_game_histories(filename):
    with open(filename, 'rb') as file:
        return pickle.load(file)

# Load the game histories
loaded_game_histories = load_game_histories('game_histories.pkl')

# Assuming 'loaded_game_histories' is your loaded data
features_labels = prepare_dataset(loaded_game_histories)

from sklearn.model_selection import train_test_split
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score

# Assuming 'features_labels' is your prepared dataset
features, labels = zip(*features_labels)


expected_length = 24  # Set this to the length you expect based on your feature extraction logic
for feature_vector in features:
    if len(feature_vector) != expected_length:
        print(f"Inconsistent feature vector length found: {len(feature_vector)}")

def flatten(features):
    if isinstance(features, (list, tuple)):
        return [item for sublist in features for item in flatten(sublist)]
    else:
        return [features]

# Flatten and ensure consistent length for each feature vector
features = [flatten(feature_vector) for feature_vector in features]

from sklearn.preprocessing import OneHotEncoder

# Assuming 'features' is a list of feature vectors, and some features are categorical (like card types)
encoder = OneHotEncoder()
X = encoder.fit_transform(features).toarray()

# Convert to numpy arrays for compatibility with scikit-learn
# X = np.array(features)
y = np.array(labels)

# Splitting the dataset into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Creating the RandomForestClassifier
model = RandomForestClassifier()

# Training the model
model.fit(X_train, y_train)

# Making predictions on the test set
y_pred = model.predict(X_test)

# Evaluating the model
print("Model Accuracy:", accuracy_score(y_test, y_pred))
print("\nClassification Report:\n", classification_report(y_test, y_pred))
