import random


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
        attacker = random.randrange(numberOfPlayers)
        defender = (attacker + 1) % numberOfPlayers
        attacker = constantMatrix(attacker, 4, 13)
        defender = constantMatrix(defender, 4, 13)
        trumps = constantMatrix(random.randrange(4), 4, 13)

        pack, playerCards = self.dealCards(numberOfPlayers, minCards)
        burned = constantMatrix(0, 4, 13)
        openAttack = constantMatrix(0, 4, 13)
        closedAttack = constantMatrix(0, 4, 13)
        defence = constantMatrix(0, 4, 13)

        self.state = playerCards + [
            attacker,
            defender,
            openAttack,
            closedAttack,
            defence,
            trumps,
            burned,
            pack,
        ]

        self.attacker = numberOfPlayers + 0
        self.defender = numberOfPlayers + 1
        self.openAttack = numberOfPlayers + 2
        self.closedAttack = numberOfPlayers + 3
        self.defence = numberOfPlayers + 4
        self.trumps = numberOfPlayers + 5
        self.burned = numberOfPlayers + 6

    def dealCards(self, numberOfPlayers, minCards):
        pack = constantMatrix(1, 4, 13)
        playerCards = [[[0 for _ in range(13)] for _ in range(4)] for _ in range(numberOfPlayers)]
        cards = [(value, suit) for value in range(13) for suit in range(4)]
        random.shuffle(cards)

        for player in range(numberOfPlayers):
            for i in range(minCards):
                (value, suit) = cards[player * minCards + i]
                playerCards[player][suit][value] = 1
                pack[suit][value] = 0

        return pack, playerCards

    def playerState(self, player):
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


class Player:
    def __init__(self, name, game):
        self.name = name
        self.game = game

    def getState(self):
        return self.game.playerState(self.name)


game = Game(4, 6)
player = Player(0, game)
print(f'\nGame state:\n')
printState(game.state)
print(f'\nPlayer state:\n')
printState(player.getState())
