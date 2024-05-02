from prob_model import ProbabilisticModel

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

import unittest
class TestMethods(unittest.TestCase):
    
    def create_test_node(self):
        player_hand_str = ['h11', 'd03', 'c10']
        player_face_up_str = ['h05', 'd06', 'c07']
        opponent_face_up_str = ['h08', 'd09', 'c04']

        prob_model = ProbabilisticModel()
        prob_model.initialize_game(player_hand_str, player_face_up_str, opponent_face_up_str)
        prob_model.move_card('h11', 'player_hand', 'play_stack')
        prob_model.deal_unseen(1, 'player_hand')
        prob_model.update_probabilities()
        
        max_depth = 1
        return Node(prob_model, max_depth)
    
    def test_node(self):
        node = self.create_test_node()

        node.generate_playable_cards('opponent_hand')
        expected_playable_cards = ['h02', 'h03', 'h10', 'h12', 'h13', 'h14', 'd02', 'd10',
                                   'd11', 'd12', 'd13', 'd14', 'c02', 'c03', 'c11', 'c12',
                                   'c13', 'c14', 's02', 's03', 's10', 's11', 's12', 's13',
                                   's14']
        self.assertEqual(node.playable_cards, expected_playable_cards)

        node.simulate_moves()
        expected_child_nodes = []
        self.assertEqual(node.child_nodes, expected_child_nodes)

        best_moves = node.get_best_moves()
        expected_best_moves = []
        self.assertEqual(node.best_moves, expected_best_moves)
        
if __name__ == '__main__':
    unittest.main()