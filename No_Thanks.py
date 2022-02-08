import random

# 1. Deck
# ----------------------------------------------------------------------------

class Deck(object):
    """
    Deck consists of list of numbers (cards). Is initialised with standard list
    of cards in No Thanks!. Decks can be shuffled, drawn from and number of 
    cards counted.
    """
    
    def __init__(self):
        self.deck = []
        
    def build(self):
        cards_all = range(3,36)
        deck = random.sample(cards_all, 24)
        
        for card in deck:
            self.deck.append(card)
        
        print("The deck has been shuffled.")
            
    def draw(self):
        return self.deck.pop()

    def check_end(self):
        if self.deck == []:
            return True
        
# 2. Player
# ----------------------------------------------------------------------------
        
class Player(object):
    """
    Player consists of a list of cards and number of chips in posession.
    Players can take or pass cards and/or chips. Total points to player at any
    time can be calculated.
    """
    
    def __init__(self, name):
        self.name = name
        self.card_hand = list()
        self.chip_hand = 11
        
    def draw_card(self, deck, player):
        global card_pool
        
        card_pool = deck.draw()
        print(f'{self.name} draws the number ' + str(card_pool) + ".")
        
        player.rand_play(player, deck)
    
    def take_card(self, player, deck):
        global card_pool
        global chip_pool
        
        self.card_hand.append(card_pool)
        self.chip_hand += chip_pool
        chip_pool = 0
        
        print(f'{self.name} takes the ' + str(card_pool) + " and " + str(chip_pool) + " chips.")
        
        if deck.check_end() != True:
            player.draw_card(deck, player)
        
    def pass_card(self):
        global card_pool
        global chip_pool
        
        self.chip_hand -= 1
        chip_pool += 1
        
        print(f'{self.name} passes the ' + str(card_pool) + " and loses a chip.")
        
    def rand_play(self, player, deck):
        """
        Action is randomly determined. Note that players must take a card if
        they are out of chips.
        """
        global chip_pool
        decision = random.randint(0,1)
        
        if self.chip_hand == 0:
            decision == 0
        
        if decision == 0:
            player.take_card(player, deck)
            
        if decision == 1:
            player.pass_card()
            
    def point_tally(self):
        self.card_hand.sort()
        self.card_hand.reverse()
        
        for i in self.card_hand:
            if i-1 in self.card_hand:
                self.card_hand.remove(i)
        
        card_points = sum(self.card_hand)
        chip_points = self.chip_hand
        return card_points - chip_points
    
# 3. Game
# ----------------------------------------------------------------------------

def Run_Game(player_1, player_2, player_3):
    """
    A game reflects an iteration of turns, until the deck emtpies and total
    points are tallied. Winner is then determined. Initialised with three
    players.
    """

    Player_1 = Player(player_1)
    Player_2 = Player(player_2)
    Player_3 = Player(player_3)

    deck = Deck()
    deck.build()
    turn_no = 1
    global card_pool
    global chip_pool 
    """
    Global used as card_pool and chip_pool need to be updated each turn so
    cannot be reset between function calls.
    """
    card_pool = 0
    chip_pool = 0
    
    Player_1.draw_card(deck, Player_1)
    
    while deck.check_end() != True:
        turn_no += 1
        
        if turn_no % 3 == 1:
            Player_1.rand_play(Player_1, deck)
            
        if turn_no % 3 == 2:
            Player_2.rand_play(Player_2, deck)
            
        if turn_no % 3 == 0:
            Player_3.rand_play(Player_3, deck)
            
    else:
        P1_total = Player_1.point_tally()
        P2_total = Player_2.point_tally()
        P3_total = Player_3.point_tally()
        
        print(f'{Player_1.name} has a final score of ' + str(P1_total))
        print(f'{Player_2.name} has a final score of ' + str(P2_total))
        print(f'{Player_3.name} has a final score of ' + str(P3_total))
        
        if min(P1_total, P2_total, P3_total) == P1_total:
            print(f'{Player_1.name} has won!!!')
            
        elif min(P1_total, P2_total, P3_total) == P2_total:
             print(f'{Player_2.name} has won!!!')
         
        elif min(P1_total, P2_total, P3_total) == P3_total:
             print(f'{Player_3.name} has won!!!')
            
Run_Game('Alice', 'Bob', 'Claire')  