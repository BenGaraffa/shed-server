from prob_model import ProbabilisticModel
from copy import deepcopy
import pickle

class Node:
    def __init__(self, prob_model, layer):
        self.prob_model = prob_model
        self.layer = layer
        self.playable_cards = []
        self.child_nodes = []
        self.best_moves = []
        self.playable_prob = None
        
    def generate_playable_cards(self, loc):
        top_card = self.prob_model.top_card
        self.playable_prob, self.playable_cards = self.prob_model.get_playable_probability(loc, top_card)
        print(self.playable_cards)
        
    def simulate_moves(self, from_loc):
        for card in self.playable_cards:
            child = Node(deepcopy(self.prob_model), 3)
            child.prob_model.move_card(card, from_loc, 'play_stack')
            child.prob_model.deal_unseen(1, from_loc)
            child.prob_model.update_probabilities()
            self.child_nodes.append(child)
            
    def __eq__(self, other):
        if not isinstance(other, Node):
            return NotImplemented
        
        return (
            self.prob_model == other.prob_model and
            self.layer == other.layer and
            self.playable_cards == other.playable_cards and
            self.child_nodes == other.child_nodes and
            self.best_moves == other.best_moves
        )


import unittest
class TestMethods(unittest.TestCase):
    
    def create_test_node(self):
        player_hand_str = ['h14', 'd03', 'c10']
        player_face_up_str = ['h05', 'd06', 'c07']
        opponent_face_up_str = ['h08', 'd09', 'c04']

        prob_model = ProbabilisticModel()
        prob_model.initialize_game(player_hand_str, player_face_up_str, opponent_face_up_str)
        prob_model.move_card('h14', 'player_hand', 'play_stack')
        prob_model.deal_unseen(1, 'player_hand')
        prob_model.update_probabilities()
        
        max_depth = 1
        
        return Node(prob_model, max_depth)
    
    def test_node(self):
        node = self.create_test_node()

        node.generate_playable_cards('opponent_hand')
        expected_playable_cards = ['h02', 'h03', 'h10', 'd02', 'd10','d14', 'c02', 
                                   'c03', 'c14', 's02', 's03', 's10', 's14']
        self.assertEqual(node.playable_cards, expected_playable_cards)

        node.simulate_moves('opponent_hand')
        expected_child_nodes = []
        with open('simulate_moves_expected_child_nodes.data', 'rb') as file:
            expected_child_nodes = pickle.load(file)
        self.assertEqual(node.child_nodes, expected_child_nodes)
        
        best_moves = node.get_best_moves()
        expected_best_moves = []
        self.assertEqual(node.best_moves, expected_best_moves)
        
if __name__ == '__main__':
    unittest.main()