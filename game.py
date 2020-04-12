import random
import threading

from communication import OverwritableSlot

printedSuits = ['S', 'C', 'H', 'D']
printedCards = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']

def constantMatrix(value, rows, columns):
    return [[value for _ in range(columns)] for _ in range(rows)]


def printState(state):
    result = [
        '\n'.join(' '.join(str(value) for value in suit) for suit in cards)
        for cards in state
    ]
    print('\n\n'.join(result) + '\n')


def toString(card):
    return f'{printedCards[card[0]]} {printedSuits[card[1]]}'


def getCards(state, category):
    return [
        (value, suit)
        for suit in range(4)
        for value in range(13)
        if state[category][suit][value] == 1
    ]


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

        self._initialiseState()

    def _initialiseState(self):
        self.state = [[] for _ in range(self.numberOfPlayers + 8)]

        for i in range(self.numberOfPlayers):
            self.state[i] = constantMatrix(0, 4, 13)

        attacker = random.randrange(self.numberOfPlayers)
        defender = (attacker + 1) % self.numberOfPlayers
        self.state[self.attacker] = constantMatrix(attacker, 4, 13)
        self.state[self.defender] = constantMatrix(defender, 4, 13)

        self.state[self.openAttack] = constantMatrix(0, 4, 13)
        self.state[self.closedAttack] = constantMatrix(0, 4, 13)
        self.state[self.defence] = constantMatrix(0, 4, 13)

        self.state[self.trumps] = constantMatrix(random.randrange(4), 4, 13)
        self.state[self.burned] = constantMatrix(0, 4, 13)
        self.state[self.pack] = constantMatrix(1, 4, 13)

        print(f'\nTrumps are {printedSuits[self.state[self.trumps][0][0]]}.\n')
        self._pickUpCards()


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
        # Previous methods must increment attacker/defender
        pack = getCards(self.state, self.pack)
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

    # Public methods: synchronisation needs to be considered!

    def getState(self, player):
        # No lock required: players should be able to call this anytime.
        # Will block until there is an update of the game state.
        return self.toPlayers[player].receive()

    def joinAttack(self, player, attackingCard, defendingCard):
        with self.lock:
            pass

    def attack(self, player, playerState, attackingCards):
        with self.lock:
            latestPlayerState = self._playerState(player)
            if playerState != latestPlayerState:
                # Player is acting on old information - reject this action.
                return

            print(f'Player {player} attacks with {", ".join([toString(card) for card in attackingCards])}...')
            # If attacking with multiple cards, check all the values are the same
            assert len(set(value for (value, suit) in attackingCards)) == 1
            assert all(self.state[player][suit][value] == 1 for (value, suit) in attackingCards)

            for (value, suit) in attackingCards:
                self.state[player][suit][value] = 0
                self.state[self.openAttack][suit][value] = 1

            self._updatePlayers()

    def bounce(self, player, playerState, bounceCard):
        with self.lock:
            latestPlayerState = self._playerState(player)
            if playerState != latestPlayerState:
                # Player is acting on old information - reject this action.
                return

    def defend(self, player, playerState, defendingCard, attackingCard):
        with self.lock:
            latestPlayerState = self._playerState(player)
            if playerState != latestPlayerState:
                # Player is acting on old information - reject this action.
                return

            print(f'Player {player} defends {toString(attackingCard)} with {toString(defendingCard)}...')
            (attackingCardValue, attackingCardSuit) = attackingCard
            (defendingCardValue, defendingCardSuit) = defendingCard

            # ToDo: shouldn't need these in future:
            assert self.state[self.openAttack][attackingCardSuit][attackingCardValue] == 1
            assert self.state[player][defendingCardSuit][defendingCardValue] == 1
            assert (defendingCardValue > attackingCardValue and defendingCardSuit == attackingCardSuit) or \
                defendingCardSuit == self.state[self.trumps][0][0]

            self.state[self.openAttack][attackingCardSuit][attackingCardValue] = 0
            self.state[self.closedAttack][attackingCardSuit][attackingCardValue] = 1
            self.state[player][defendingCardSuit][defendingCardValue] = 0
            self.state[self.defence][defendingCardSuit][defendingCardValue] = 1

            self.active[player] = False

            if sum(sum(suit) for suit in self.state[self.defence]) == 5:
                # Successful defence!
                for category in [self.closedAttack, self.defence]:
                    cards = getCards(self.state, category)
                    for (value, suit) in cards:
                        self.state[category][suit][value] = 0
                        self.state[self.burned][suit][value] = 1

                newAttacker = player
                newDefender = (player + 1) % self.numberOfPlayers
                self._updateAttackerAndDefender(newAttacker, newDefender)
                self._pickUpCards()
            else:
                self._updatePlayers()

    def concede(self, player, playerState):
        with self.lock:
            latestPlayerState = self._playerState(player)
            if playerState != latestPlayerState:
                # Player is acting on old information - reject this action.
                return

            print(f'Player {player} concedes...')
            for category in [self.openAttack, self.closedAttack, self.defence]:
                cards = getCards(self.state, category)
                for (value, suit) in cards:
                    self.state[category][suit][value] = 0
                    self.state[player][suit][value] = 1

            newAttacker = (player + 1) % self.numberOfPlayers
            newDefender = (newAttacker + 1) % self.numberOfPlayers
            self._updateAttackerAndDefender(newAttacker, newDefender)
            self._pickUpCards()

    def declineToAttack(self, player, playerState):
        with self.lock:
            latestPlayerState = self._playerState(player)
            if playerState != latestPlayerState:
                # Player is acting on old information - reject this action.
                return # latestPlayerState

            print(f'Player {player} declines to attack...')
            self.active[player] = False
            if not any(self.active):
                print(f'Everyone declines to attack...')
                # If this call has ended the round then we must have a successful defence.
                defender = self.state[self.defender][0][0]
                newAttacker = defender
                newDefender = (defender + 1) % self.numberOfPlayers
                self._updateAttackerAndDefender(newAttacker, newDefender)
                self._pickUpCards()

    def waitForUpdates(self, player, _):
        # No lock required: players should be able to call this anytime.
        print(f'Player {player} waits for updates...')
        return
