import copy
import random
import threading

import numpy

from synchronisation import OverwritableSlot

printSuit = ['S', 'C', 'H', 'D']
printValue = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']


def length(cards):
    return cards[0].size


def constantMatrix(value, rows, columns):
    return numpy.full((rows, columns), value, dtype=int)


def printState(state):
    print(state)
    print()


def printCard(card):
    return f'{printValue[card[1]]}{printSuit[card[0]]}'


def printCards(cards):
    cards = numpy.array(cards).T
    return ', '.join([printCard(card) for card in cards])


def getCards(state, category):
    return numpy.where(state[category] == 1)


def numberOfCards(state, category):
    return numpy.sum(state[category])


class Game:
    def __init__(self, numberOfPlayers, minCards, maxAttacks):
        self.numberOfPlayers = numberOfPlayers
        self.minCards = minCards
        self.maxAttacks = maxAttacks

        self.trumps = self.numberOfPlayers + 0
        self.openAttacks = self.numberOfPlayers + 1
        self.closedAttacks = self.numberOfPlayers + 2
        self.defences = self.numberOfPlayers + 3
        self.burned = self.numberOfPlayers + 4
        self.pack = self.numberOfPlayers + 5

        self.numberOfGlobalComponents = 6
        self.numberOfActionComponents = 4

        self.attacker = None
        self.defender = None

        self.declinedToAttack = [False for _ in range(self.numberOfPlayers)]
        self.playersNotOut = list(range(self.numberOfPlayers))
        self.activePlayer = 0
        self.gameOver = False

        self.turns = 0
        self._initialiseState()

    def _initialiseState(self):
        self.state = numpy.zeros((self.numberOfPlayers + self.numberOfGlobalComponents, 4, 13), dtype=int)

        trumps = random.randrange(4)
        self.state[self.trumps][trumps] = numpy.ones(13, dtype=int)
        self.state[self.pack] = numpy.ones((4, 13), dtype=int)

        self.attacker = random.randrange(self.numberOfPlayers)
        self.defender = (self.attacker + 1) % self.numberOfPlayers

        print(f'\nTrumps are {printSuit[trumps]}.')
        self._pickUpCards()

    def _stateChanged(self):
        print(f'\nGame state:\n')
        attacker = numpy.full((4, 13), self.attacker, dtype=int)
        defender = numpy.full((4, 13), self.defender, dtype=int)
        printState(numpy.append(self.state, [attacker, defender], axis=0))

        for player in self.playersNotOut:
            self.declinedToAttack[player] = False

    def _playerState(self, player):
        # Attacker and defender should be relative to this player.
        attacker = (self.attacker - player) % self.numberOfPlayers
        defender = (self.defender - player) % self.numberOfPlayers
        attacker = numpy.full((4, 13), attacker, dtype=int)
        defender = numpy.full((4, 13), defender, dtype=int)

        observable = [player, self.trumps, self.openAttacks, self.closedAttacks, self.defences, self.burned]
        return numpy.append(self.state[observable], [attacker, defender], axis=0)

    def _pickUpCards(self):
        # Previous methods must increment attacker/defender
        pack = numpy.array(getCards(self.state, self.pack))
        if pack.shape[1] > 0:
            numpy.random.shuffle(numpy.transpose(pack))

            # Defender picks up first, then attacker, then others.
            player = self.defender
            for _ in range(len(self.playersNotOut)):
                playerCards = numberOfCards(self.state, player)
                if playerCards < self.minCards:
                    shortage = self.minCards - playerCards
                    newCards = tuple(pack[:, :shortage])
                    pack = pack[:, shortage:]
                    self.state[self.pack][newCards] = numpy.zeros(length(newCards), dtype=int)
                    self.state[player][newCards] = numpy.ones(length(newCards), dtype=int)
                player = self._previousPlayer(player)

        self._stateChanged()

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
            self.state[category][cards] = numpy.zeros(length(cards), dtype=int)
            self.state[self.burned][cards] = numpy.ones(length(cards), dtype=int)

        self._updateAttackerAndDefender(self.defender)
        self.turns += 1
        self._pickUpCards()

    def _nextPlayer(self, player):
        return self.playersNotOut[(self.playersNotOut.index(player) + 1) % len(self.playersNotOut)]

    def _previousPlayer(self, player):
        return self.playersNotOut[(self.playersNotOut.index(player) - 1) % len(self.playersNotOut)]

    def _endGame(self):
        assert len(self.playersNotOut) == 1
        self.gameOver = True
        loser = self.playersNotOut[0]
        print(f'Player {loser} loses after {self.turns} turns!')

        # Give loser all the cards so they know they've lost.
        for category in [self.openAttacks, self.closedAttacks, self.defences]:
            cards = getCards(self.state, category)
            self.state[category][cards] = numpy.zeros(length(cards), dtype=int)
            self.state[loser][cards] = numpy.ones(length(cards), dtype=int)

    # Public methods: synchronisation needs to be considered!

    def getState(self, player):
        return copy.deepcopy(self._playerState(player))

    def joinAttack(self, player, card):
        print(f'Player {player} joins attacks: attacks with {printCard(card)}...')
        assert player == self.activePlayer

        # Check a card of this value appears on the table already somewhere.
        openAttacks = getCards(self.state, self.openAttacks)
        closedAttacks = getCards(self.state, self.closedAttacks)
        defences = getCards(self.state, self.defences)

        assert any(numpy.any(cards[1] == card[1]) for cards in [closedAttacks, defences])
        assert self.state[player][card] == 1
        totalAttacks = length(openAttacks) + length(closedAttacks)
        assert totalAttacks < self.maxAttacks

        self.state[player][card] = 0
        self.state[self.openAttacks][card] = 1

        self.activePlayer = self._nextPlayer(self.activePlayer)
        self._stateChanged()

    def attack(self, player, cards):
        print(f'Player {player} attacks with {printCards(cards)}...')
        assert player == self.activePlayer

        # If attacking with multiple cards, check all the values are the same
        assert numpy.unique(cards[1]).size == 1
        assert numpy.all(self.state[player][cards] == 1)

        self.state[player][cards] = numpy.zeros(length(cards), dtype=int)
        self.state[self.openAttacks][cards] = numpy.ones(length(cards), dtype=int)

        self.activePlayer = self._nextPlayer(self.activePlayer)
        self._stateChanged()

    def bounce(self, player, cards):
        print(f'Player {player} bounces with {printCards(cards)}...')
        assert player == self.activePlayer

        # Check there are only open attacks
        # Check all open attacks have same value
        # Check these cards have that value too
        assert player == self.defender
        assert numberOfCards(self.state, self.closedAttacks) + numberOfCards(self.state, self.defences) == 0
        attackValues = numpy.unique(getCards(self.state, self.openAttacks)[1])
        assert attackValues.size == 1
        assert numpy.all(cards[1] == attackValues[0])

        self.state[self.openAttacks][cards] = numpy.ones(length(cards), dtype=int)
        self.state[player][cards] = numpy.zeros(length(cards), dtype=int)

        self.activePlayer = self._nextPlayer(self.activePlayer)
        self._updateAttackerAndDefender(player)
        self._stateChanged()

    def defend(self, player, defendingCard, attackingCard):
        print(f'Player {player} defends {printCard(attackingCard)} with {printCard(defendingCard)}...')
        assert player == self.activePlayer

        (attackingCardSuit, attackingCardValue) = attackingCard
        (defendingCardSuit, defendingCardValue) = defendingCard

        assert self.state[self.openAttacks][attackingCard] == 1
        assert self.state[player][defendingCard] == 1
        assert (defendingCardValue > attackingCardValue and defendingCardSuit == attackingCardSuit) \
            or self.state[self.trumps][defendingCardSuit][0] == 1 and defendingCardSuit != attackingCardSuit

        self.state[self.openAttacks][attackingCard] = 0
        self.state[self.closedAttacks][attackingCard] = 1
        self.state[player][defendingCard] = 0
        self.state[self.defences][defendingCard] = 1

        self.activePlayer = self._nextPlayer(self.activePlayer)
        if numberOfCards(self.state, self.defences) == self.maxAttacks or numberOfCards(self.state, player) == 0:
            self._successfulDefence()
        else:
            self._stateChanged()

    def concede(self, player, attacksToConcede):
        print(f'Player {player} concedes...')
        assert player == self.activePlayer

        numberOfOpenAttacks = numberOfCards(self.state, self.openAttacks)
        surplus = numberOfOpenAttacks - numberOfCards(self.state, player)
        assert surplus <= 0 and length(attacksToConcede) == numberOfOpenAttacks \
            or 0 < surplus == length(attacksToConcede)
        assert numpy.all(self.state[self.openAttacks][attacksToConcede] == 1)

        # Concede all the defences and closed attacks
        for category in [self.closedAttacks, self.defences]:
            cards = getCards(self.state, category)
            self.state[category][cards] = numpy.zeros(length(cards), dtype=int)
            self.state[player][cards] = numpy.ones(length(cards), dtype=int)

        # Concede the selected open attacks cards
        self.state[self.openAttacks][attacksToConcede] = numpy.zeros(length(attacksToConcede), dtype=int)
        self.state[player][attacksToConcede] = numpy.ones(length(attacksToConcede), dtype=int)

        # Burn any leftover open attacks
        leftovers = getCards(self.state, self.openAttacks)
        self.state[self.openAttacks][leftovers] = numpy.zeros(length(leftovers), dtype=int)
        self.state[self.burned][leftovers] = numpy.ones(length(leftovers), dtype=int)

        self.activePlayer = self._nextPlayer(self.activePlayer)
        self._updateAttackerAndDefender(self._nextPlayer(player))
        self.turns += 1
        self._pickUpCards()

    def declineToAttack(self, player):
        print(f'Player {player} declines to attack...')
        assert player == self.activePlayer
        self.activePlayer = self._nextPlayer(self.activePlayer)

        self.declinedToAttack[player] = True

        decliners = [self.declinedToAttack[player] for player in self.playersNotOut]
        everyoneDeclined = len([() for declined in decliners if declined]) == len(self.playersNotOut) - 1
        if length(getCards(self.state, self.openAttacks)) == 0 and everyoneDeclined:
            print(f'Everyone declines to attack...')
            # If this call has ended the round then we must have a successful defence.
            self._successfulDefence()


    def waitForUpdates(self, player):
        print(f'Player {player} waits for updates...')
        assert player == self.activePlayer
        self.activePlayer = self._nextPlayer(self.activePlayer)

    def done(self, player):
        print(f'Player {player} is out!')
        assert player == self.activePlayer
        self.activePlayer = self._nextPlayer(self.activePlayer)

        if player == self.attacker:
            self._updateAttackerAndDefender(self._nextPlayer(player))
        elif player == self.defender:
            self.defender = self._nextPlayer(player)
        self.playersNotOut.remove(player)
        if len(self.playersNotOut) == 1:
            self._endGame()

        self._stateChanged()
