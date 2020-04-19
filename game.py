import copy
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

def numberOfCards(state, category):
    return sum([sum(suit) for suit in state[category]])

class Game:
    def __init__(self, numberOfPlayers, minCards, maxAttacks):
        self.numberOfPlayers = numberOfPlayers
        self.minCards = minCards
        self.maxAttacks = maxAttacks

        self.lock = threading.Lock()
        self.toPlayers = [OverwritableSlot() for _ in range(numberOfPlayers)]

        self.trumps = self.numberOfPlayers + 0
        self.openAttacks = self.numberOfPlayers + 1
        self.closedAttacks = self.numberOfPlayers + 2
        self.defences = self.numberOfPlayers + 3
        self.burned = self.numberOfPlayers + 4
        self.pack = self.numberOfPlayers + 5

        self.attacker = None
        self.defender = None

        self.declinedToAttack = [False for _ in range(self.numberOfPlayers)]
        self.activePlayers = list(range(self.numberOfPlayers))

        self.turns = 0
        self._initialiseState()

    def _initialiseState(self):
        self.state = [[] for _ in range(self.numberOfPlayers + 6)]

        for i in range(self.numberOfPlayers):
            self.state[i] = constantMatrix(0, 4, 13)

        self.state[self.openAttacks] = constantMatrix(0, 4, 13)
        self.state[self.closedAttacks] = constantMatrix(0, 4, 13)
        self.state[self.defences] = constantMatrix(0, 4, 13)

        trumps = random.randrange(4)
        self.state[self.trumps] = [[1 if suit == trumps else 0 for _ in range(13)] for suit in range(4)]
        self.state[self.burned] = constantMatrix(0, 4, 13)
        self.state[self.pack] = constantMatrix(1, 4, 13)

        self.attacker = random.randrange(self.numberOfPlayers)
        self.defender = (self.attacker + 1) % self.numberOfPlayers

        print(f'\nTrumps are {printedSuits[trumps]}.')
        self._pickUpCards()

    def _updatePlayers(self):
        print(f'\nGame state:\n')
        printState(self.state)
        for player in self.activePlayers:
            self.declinedToAttack[player] = False
            self.toPlayers[player].send(copy.deepcopy(self._playerState(player)))

    def _playerState(self, player):
        # Attacker and defender should be relative to this player.
        attacker = (self.attacker - player) % self.numberOfPlayers
        defender = (self.defender - player) % self.numberOfPlayers
        attacker = constantMatrix(attacker, 4, 13)
        defender = constantMatrix(defender, 4, 13)

        components = [
            player,
            self.trumps,
            self.openAttacks,
            self.closedAttacks,
            self.defences,
            self.burned
        ]
        return [self.state[i] for i in components] + [attacker, defender]

    def _pickUpCards(self):
        # Previous methods must increment attacker/defender
        pack = getCards(self.state, self.pack)
        random.shuffle(pack)

        # Defender picks up first, then attacker, then others.
        player = self.defender
        for _ in range(len(self.activePlayers)):
            playerCards = numberOfCards(self.state, player)
            if playerCards < self.minCards:
                newCards = pack[:self.minCards - playerCards]
                pack = pack[self.minCards - playerCards:]
                for (value, suit) in newCards:
                    self.state[self.pack][suit][value] = 0
                    self.state[player][suit][value] = 1
            player = self._previousPlayer(player)

        if len(pack) == 0:
            self.inEndgame = True

        self._updatePlayers()

    def _updateAttackerAndDefender(self, newAttacker):
        newDefender = self._nextPlayer(newAttacker)
        self.attacker = newAttacker
        self.defender = newDefender

    def _successfulDefence(self):
        # Burn closed attacks and defences, but also burn any open attacks -
        # the defender might just have used their last cards.
        print(f'Successful defence by player {self.defender}!')
        for category in [self.openAttacks, self.closedAttacks, self.defences]:
            cards = getCards(self.state, category)
            for (value, suit) in cards:
                self.state[category][suit][value] = 0
                self.state[self.burned][suit][value] = 1

        self._updateAttackerAndDefender(self.defender)
        self.turns += 1
        self._pickUpCards()

    def _nextPlayer(self, player):
        return self.activePlayers[(self.activePlayers.index(player) + 1) % len(self.activePlayers)]

    def _previousPlayer(self, player):
        return self.activePlayers[(self.activePlayers.index(player) - 1) % len(self.activePlayers)]

    def _endGame(self):
        assert len(self.activePlayers) == 1
        loser = self.activePlayers[0]
        print(f'Player {loser} loses after {self.turns} turns!')
        # Give loser all the cards so they know they've lost.
        for category in [self.openAttacks, self.closedAttacks, self.defences]:
            cards = getCards(self.state, category)
            for (value, suit) in cards:
                self.state[category][suit][value] = 0
                self.state[loser][suit][value] = 1

    # Public methods: synchronisation needs to be considered!

    def getState(self, player):
        # No lock required: players should be able to call this anytime.
        # Will block until there is an update of the game state.
        return self.toPlayers[player].receive()

    def joinAttack(self, player, playerState, card):
        with self.lock:
            latestPlayerState = self._playerState(player)
            if playerState != latestPlayerState:
                print(f'Player {player} joining attack based on old information - reject this action.')
                return

            print(f'Player {player} joins attacks: attacks with {toString(card)}...')
            # Check a card of this value appears on the table already somewhere.
            attackCards = getCards(self.state, self.openAttacks) + getCards(self.state, self.closedAttacks)
            cardsOnTable = attackCards + getCards(self.state, self.defences)
            assert any(value == card[0] for (value, suit) in cardsOnTable)
            assert self.state[player][card[1]][card[0]] == 1
            assert len(attackCards) < self.maxAttacks

            self.state[player][card[1]][card[0]] = 0
            self.state[self.openAttacks][card[1]][card[0]] = 1

            self._updatePlayers()

    def attack(self, player, playerState, cards):
        with self.lock:
            latestPlayerState = self._playerState(player)
            if playerState != latestPlayerState:
                print(f'Player {player} attacking based on old information - reject this action.')
                return

            print(f'Player {player} attacks with {", ".join([toString(card) for card in cards])}...')
            # If attacking with multiple cards, check all the values are the same
            assert len(set(value for (value, suit) in cards)) == 1
            assert all(self.state[player][suit][value] == 1 for (value, suit) in cards)

            for (value, suit) in cards:
                self.state[player][suit][value] = 0
                self.state[self.openAttacks][suit][value] = 1

            self._updatePlayers()

    def bounce(self, player, playerState, cards):
        with self.lock:
            latestPlayerState = self._playerState(player)
            if playerState != latestPlayerState:
                print(f'Player {player} bouncing based on old information - reject this action.')
                return

            print(f'Player {player} bounces with {", ".join([toString(card) for card in cards])}...')
            # Check there are only open attacks
            # Check all open attacks have same value
            # Check these cards have that value too
            assert player == self.defender
            assert numberOfCards(self.state, self.closedAttacks) + numberOfCards(self.state, self.defences) == 0
            attackValues = set(value for (value, suit) in getCards(self.state, self.openAttacks))
            assert len(attackValues) == 1
            attackValue = attackValues.pop()
            assert all(card[0] == attackValue for card in cards)

            for (value, suit) in cards:
                self.state[self.openAttacks][suit][value] = 1
                self.state[player][suit][value] = 0

            self._updateAttackerAndDefender(player)
            self._updatePlayers()

    def defend(self, player, playerState, defendingCard, attackingCard):
        with self.lock:
            latestPlayerState = self._playerState(player)
            if playerState != latestPlayerState:
                print(f'Player {player} defending based on old information - reject this action.')
                return

            print(f'Player {player} defends {toString(attackingCard)} with {toString(defendingCard)}...')
            (attackingCardValue, attackingCardSuit) = attackingCard
            (defendingCardValue, defendingCardSuit) = defendingCard

            assert self.state[self.openAttacks][attackingCardSuit][attackingCardValue] == 1
            assert self.state[player][defendingCardSuit][defendingCardValue] == 1
            assert (defendingCardValue > attackingCardValue and defendingCardSuit == attackingCardSuit) or \
                   self.state[self.trumps][defendingCardSuit][0] == 1

            self.state[self.openAttacks][attackingCardSuit][attackingCardValue] = 0
            self.state[self.closedAttacks][attackingCardSuit][attackingCardValue] = 1
            self.state[player][defendingCardSuit][defendingCardValue] = 0
            self.state[self.defences][defendingCardSuit][defendingCardValue] = 1

            self.declinedToAttack[player] = False

            if numberOfCards(self.state, self.defences) == self.maxAttacks or numberOfCards(self.state, player) == 0:
                self._successfulDefence()
            else:
                self._updatePlayers()

    def concede(self, player, playerState, attacksToConcede):
        with self.lock:
            latestPlayerState = self._playerState(player)
            if playerState != latestPlayerState:
                print(f'Player {player} conceding based on old information - reject this action.')
                return

            print(f'Player {player} concedes...')
            for (value, suit) in attacksToConcede:
                numberOfOpenAttacks = numberOfCards(self.state, self.openAttacks)
                surplus = numberOfOpenAttacks - numberOfCards(self.state, player)
                assert surplus <= 0 and len(attacksToConcede) == numberOfOpenAttacks \
                       or 0 < surplus == len(attacksToConcede)
                assert self.state[self.openAttacks][suit][value] == 1

            # Concede all the defences and closed attacks
            for category in [self.closedAttacks, self.defences]:
                cards = getCards(self.state, category)
                for (value, suit) in cards:
                    self.state[category][suit][value] = 0
                    self.state[player][suit][value] = 1

            # Concede the selected open attacks cards
            for (value, suit) in attacksToConcede:
                self.state[self.openAttacks][suit][value] = 0
                self.state[player][suit][value] = 1

            # Burn any leftover open attacks
            for (value, suit) in getCards(self.state, self.openAttacks):
                self.state[self.openAttacks][suit][value] = 0
                self.state[self.burned][suit][value] = 1

            self._updateAttackerAndDefender(self._nextPlayer(player))
            self.turns += 1
            self._pickUpCards()

    def declineToAttack(self, player, playerState):
        with self.lock:
            latestPlayerState = self._playerState(player)
            if playerState != latestPlayerState:
                print(f'Player {player} declining based on old information - reject this action.')
                return

            print(f'Player {player} declines to attack...')
            self.declinedToAttack[player] = True

            decliners = [self.declinedToAttack[player] for player in self.activePlayers]
            everyoneDeclined = len([() for declined in decliners if declined]) == len(self.activePlayers) - 1
            if len(getCards(self.state, self.openAttacks)) == 0 and everyoneDeclined:
                print(f'Everyone declines to attack...')
                # If this call has ended the round then we must have a successful defence.
                self._successfulDefence()

    def waitForUpdates(self, player, _):
        with self.lock:
            print(f'Player {player} waits for updates...')

    def done(self, player, _):
        with self.lock:
            print(f'Player {player} is out!')
            if player == self.attacker:
                self._updateAttackerAndDefender(self._nextPlayer(player))
            self.activePlayers.remove(player)
            if len(self.activePlayers) == 1:
                self._endGame()
            self._updatePlayers()
