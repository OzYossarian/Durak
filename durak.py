import random
import threading

from communication import OverwritableSlot


def constantMatrix(value, rows, columns):
    return [[value for _ in range(columns)] for _ in range(rows)]


def printState(state):
    result = [
        '\n'.join([' '.join([str(value) for value in suit]) for suit in cards])
        for cards in state
    ]
    print('\n\n'.join(result))


class Game:
    def __init__(self, numberOfPlayers, minCards):
        self.numberOfPlayers = numberOfPlayers
        self.minCards = minCards

        self.lock = threading.Lock()
        self.toPlayers = [OverwritableSlot() for _ in range(numberOfPlayers)]

        self.attacker = numberOfPlayers + 0
        self.defender = numberOfPlayers + 1
        self.openAttack = numberOfPlayers + 2
        self.closedAttack = numberOfPlayers + 3
        self.defence = numberOfPlayers + 4
        self.trumps = numberOfPlayers + 5
        self.burned = numberOfPlayers + 6

        self.state = None
        self.updateState(self.__initialiseState__())

    def __initialiseState__(self):
        attacker = random.randrange(self.numberOfPlayers)
        defender = (attacker + 1) % self.numberOfPlayers
        attacker = constantMatrix(attacker, 4, 13)
        defender = constantMatrix(defender, 4, 13)

        burned = constantMatrix(0, 4, 13)
        openAttack = constantMatrix(0, 4, 13)
        closedAttack = constantMatrix(0, 4, 13)
        defence = constantMatrix(0, 4, 13)
        trumps = constantMatrix(random.randrange(4), 4, 13)

        pack, playerCards = self.__dealCards__()

        return playerCards + [
            attacker,
            defender,
            openAttack,
            closedAttack,
            defence,
            trumps,
            burned,
            pack,
        ]

    def __dealCards__(self):
        pack = constantMatrix(1, 4, 13)
        playerCards = [[[0 for _ in range(13)] for _ in range(4)] for _ in range(self.numberOfPlayers)]
        cards = [(value, suit) for value in range(13) for suit in range(4)]
        random.shuffle(cards)

        for player in range(self.numberOfPlayers):
            for i in range(self.minCards):
                (value, suit) = cards[player * self.minCards + i]
                playerCards[player][suit][value] = 1
                pack[suit][value] = 0

        return pack, playerCards

    def updateState(self, newState):
        self.state = newState
        for i in range(self.numberOfPlayers):
            self.toPlayers[i].send(self.__playerState__(i))

    def getState(self, player):
        return self.toPlayers[player].receive()

    def __playerState__(self, player):
        components = [
            player,
            self.attacker,
            self.defender,
            self.openAttack,
            self.closedAttack,
            self.defence,
            self.trumps,
            self.burned
        ]
        return [self.state[i] for i in components]

    def joinAttack(self, player, attackingCard, defendingCard):
        with self.lock:
            pass

    def attack(self, player, attackingCards):
        with self.lock:
            pass

    def defend(self, player, defendingCard, attackingCard):
        with self.lock:
            pass

    def concede(self, player):
        with self.lock:
            pass

    def decline(self, player):
        with self.lock:
            pass




class Player:
    def __init__(self, name, game):
        self.name = name
        self.game = game

        self.attacker = 1
        self.defender = 2
        self.openAttack = 3
        self.closedAttack = 4
        self.defence = 5
        self.trumps = 6
        self.burned = 7

    def play(self):
        state = self.game.getState(self.name)
        while self.hasCards(state):
            action = random.choice(self.getPossibleActions(state))
            action()
            state = self.game.getState(self.name)

    def hasCards(self, state):
        return sum([sum(suit) for suit in state[0]]) > 0

    def getPossibleActions(self, state):
        # For now, don't make any actual moves.
        print(f'Player {self.name} declines...')
        return [lambda: self.game.decline(self.name)]


def main():
    numberOfPlayers = 4
    minCards = 6
    game = Game(numberOfPlayers, minCards)
    players = [Player(i, game) for i in range(numberOfPlayers)]

    threads = [threading.Thread(target=(lambda p: p.play()), args=(players[i],)) for i in range(numberOfPlayers)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

main()
