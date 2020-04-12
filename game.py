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
    print('\n\n'.join(result) + '\n')


class Game:
    def __init__(self, numberOfPlayers, minCards):
        self.numberOfPlayers = numberOfPlayers
        self.minCards = minCards

        self.lock = threading.Lock()
        self.toPlayers = [OverwritableSlot() for _ in range(numberOfPlayers)]

        self.attacker = self.numberOfPlayers + 0
        self.defender = self.numberOfPlayers + 1
        self.openAttack = self.numberOfPlayers + 2
        self.closedAttack = self.numberOfPlayers + 3
        self.defence = self.numberOfPlayers + 4
        self.trumps = self.numberOfPlayers + 5
        self.burned = self.numberOfPlayers + 6
        self.pack = self.numberOfPlayers + 7

        self.active = [False for _ in range(self.numberOfPlayers)]
        self.inEndgame = False

        self.state = self._initialiseState()
        self._updatePlayers()

    def _initialiseState(self):
        attacker = random.randrange(self.numberOfPlayers)
        defender = (attacker + 1) % self.numberOfPlayers
        attacker = constantMatrix(attacker, 4, 13)
        defender = constantMatrix(defender, 4, 13)

        burned = constantMatrix(0, 4, 13)
        openAttack = constantMatrix(0, 4, 13)
        closedAttack = constantMatrix(0, 4, 13)
        defence = constantMatrix(0, 4, 13)
        trumps = constantMatrix(random.randrange(4), 4, 13)

        pack, playerCards = self._dealCards()

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

    def _dealCards(self):
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

    def _updatePlayers(self):
        print(f'\nGame state:\n')
        printState(self.state)
        for i in range(self.numberOfPlayers):
            self.active[i] = True
            self.toPlayers[i].send(self._playerState(i))

    def _playerState(self, player):
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

    def _getCards(self, category):
        return [
            (value, suit)
            for suit in range(4)
            for value in range(13)
            if self.state[category][suit][value] == 1
        ]

    def _pickUpCards(self):
        print('Picking up cards...\n')
        # Previous methods must increment attacker/defender
        pack = self._getCards(self.pack)
        random.shuffle(pack)

        # Defender picks up first, then attacker, then others.
        defender = self.state[self.defender][0][0]
        for i in range(self.numberOfPlayers):
            player = (defender - i) % self.numberOfPlayers
            playerCards = sum([sum(suit) for suit in self.state[player]])
            if playerCards < self.minCards:
                newCards = pack[:self.minCards - playerCards]
                pack = pack[self.minCards - playerCards:]
                for (value, suit) in newCards:
                    self.state[self.pack][suit][value] = 0
                    self.state[player][suit][value] = 1

        if len(pack) == 0:
            self.inEndgame = True

        self._updatePlayers()

    def _updateAttackerAndDefender(self, attacker, defender):
        self.state[self.attacker] = constantMatrix(attacker, 4, 13)
        self.state[self.defender] = constantMatrix(defender, 4, 13)

    def getState(self, player):
        return self.toPlayers[player].receive()

    def joinAttack(self, player, attackingCard, defendingCard):
        with self.lock:
            pass

    def attack(self, player, attackingCards):
        with self.lock:
            pass

    def defend(self, player, defendingCard, attackingCard):
        # If successful, this ends the turn, new cards need to be dealt
        with self.lock:
            pass

    def concede(self, player, playerState):
        with self.lock:
            if playerState != self._playerState(player):
                # Player is acting on old information - reject this action.
                return

            print(f'Player {player} concedes...')
            for category in [self.openAttack, self.closedAttack, self.defence]:
                cards = self._getCards(category)
                for (value, suit) in cards:
                    self.state[category][suit][value] = 0
                    self.state[player][suit][value] = 1

            newAttacker = (player + 1) % self.numberOfPlayers
            newDefender = (newAttacker + 1) % self.numberOfPlayers
            self._updateAttackerAndDefender(newAttacker, newDefender)
            self._pickUpCards()

    def decline(self, player, playerState):
        with self.lock:
            if playerState != self._playerState(player):
                # Player is acting on old information - reject this action.
                return

            print(f'Player {player} declines...')
            self.active[player] = False
            if not any(self.active):
                # If this call has ended the round then we must have a successful defence.
                defender = self.state[self.defender][0][0]
                newAttacker = defender
                newDefender = (defender + 1) % self.numberOfPlayers
                self._updateAttackerAndDefender(newAttacker, newDefender)
                self._pickUpCards()