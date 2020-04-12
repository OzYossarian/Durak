import random
import threading
import time

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

    def _pickUpCards(self):
        print("Picking up cards...")
        # Previous methods must increment attacker/defender
        pack = [
            (value, suit)
            for suit in range(4)
            for value in range(13)
            if self.state[self.pack][suit][value] == 1
        ]
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

    def getState(self, player):
        return self.toPlayers[player].receive()

    # ToDo: when players call an action below, perhaps have them send what they believe to be the state too?
    # If the state is stale, reject their action, so that they aren't acting on ou-of-date knowledge?

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

    def concede(self, player):
        # Terminal action - ends the turn, new cards need to be dealt
        with self.lock:
            pass

    def decline(self, player):
        with self.lock:
            self.active[player] = False
            if not any(self.active):
                # If this call has ended the round then we must have a successful defence.
                defender = self.state[self.defender][0][0]
                newAttacker = defender
                newDefender = (defender + 1) % self.numberOfPlayers
                self.state[self.attacker] = constantMatrix(newAttacker, 4, 13)
                self.state[self.defender] = constantMatrix(newDefender, 4, 13)
                self._pickUpCards()


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
            time.sleep(random.uniform(0, 1))
            state = self.game.getState(self.name)

    def hasCards(self, state):
        return sum([sum(suit) for suit in state[0]]) > 0

    def getPossibleActions(self, state):
        # For now, don't make any actual moves.
        # Must only use the state to determine actions, nothing else.
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
