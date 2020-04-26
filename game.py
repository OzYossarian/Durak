import copy
import random
import observables
import numpy

printSuit = ['S', 'C', 'H', 'D']
printValue = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']


def length(cards):
    return cards[0].size


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
    def __init__(self, players, minCards, maxAttacks):
        self.players = players
        self.numberOfPlayers = len(players)
        self.minCards = minCards
        self.maxAttacks = maxAttacks

        self.openAttacks = self._stateIndex(observables.openAttacks)
        self.closedAttacks = self._stateIndex(observables.closedAttacks)
        self.defences = self._stateIndex(observables.defences)
        self.trumps = self._stateIndex(observables.trumps)
        self.attacker = self._stateIndex(observables.attacker)
        self.defender = self._stateIndex(observables.defender)
        self.burned = self._stateIndex(observables.burned)
        self.pack = self._stateIndex(observables.pack)

        self.declinedToAttack = 0
        self.playersNotOut = list(range(self.numberOfPlayers))
        self.activePlayer = None

        self.turns = 0
        self._initialiseState()

    def play(self):
        gameOver = False
        while not gameOver:
            action = self.players[self.activePlayer].act(self._observation(self.activePlayer))
            self._updateState(action)
            gameOver = len(self.playersNotOut) == 1

    def _initialiseState(self):
        self.state = numpy.zeros((self.numberOfPlayers + 8, 4, 13), dtype=int)

        trumps = random.randrange(4)
        self.state[self.trumps][trumps] = numpy.ones(13, dtype=int)
        self.state[self.pack] = numpy.ones((4, 13), dtype=int)

        attacker = random.randrange(self.numberOfPlayers)
        defender = (attacker + 1) % self.numberOfPlayers
        self._setAttacker(attacker)
        self._setDefender(defender)
        self.activePlayer = attacker

        self._pickUpCards(self._getDefender())

    def _pickUpCards(self, firstToPickUp):
        pack = numpy.array(getCards(self.state, self.pack))
        if pack.shape[1] > 0:
            numpy.random.shuffle(numpy.transpose(pack))

            # Defender picks up first, then attacker, then others.
            player = firstToPickUp
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

    def _stateChanged(self):
        print(f'\nGame state:\n')
        printState(self.state)
        print(f'\nTrumps are {printSuit[self.state[self.trumps][0][0]]}.')
        print(f'Players {", ".join([str(player) for player in self.playersNotOut])} are still in')
        print(f'Player {self.activePlayer} is active')
        print()

        self.declinedToAttack = 0

    def _observation(self, player):
        # Attacker and defender should be relative to this player.
        attacker = (self._getAttacker() - player) % self.numberOfPlayers
        defender = (self._getDefender() - player) % self.numberOfPlayers
        attacker = numpy.full((4, 13), attacker, dtype=int)
        defender = numpy.full((4, 13), defender, dtype=int)

        # Order here must match that in observables.py.
        actionObservation = self.state[[player, self.openAttacks, self.closedAttacks, self.defences]]
        remainingObservation = self.state[[self.trumps, self.burned]]
        return numpy.concatenate((actionObservation, [attacker, defender], remainingObservation), axis=0)

    def _updateState(self, action):
        # ToDo: Once all this works, train on a more efficient version with assertions removed.
        assert numpy.sum(action) == 0
        affectedState = self.state[self._actionComponents(self.activePlayer)]
        assert numpy.all(affectedState[numpy.where(action == 1)] == 0)
        assert numpy.all(affectedState[numpy.where(action == -1)] == 1)

        if numpy.sum(action[observables.openAttacks]) > 0:
            attacks = numberOfCards(self.state, self.openAttacks) + numberOfCards(self.state, self.closedAttacks)
            if self.activePlayer == self._getDefender():
                self._bounce(action)
            elif self.activePlayer == self._getAttacker() and attacks == 0:
                self._attack(action)
            else:
                self._joinAttack(action)

        elif numpy.sum(action[observables.defences]) > 0:
            self._defend(action)

        elif numpy.sum(action[observables.playerCards]) > 0:
            self._concede(action)

        else:
            self._declineToAttack(action)

    def _joinAttack(self, action):
        attackCards = numpy.where(action[observables.openAttacks] == 1)
        assert length(attackCards) == 1
        attackCard = (attackCards[0][0], attackCards[1][0])
        print(f'Player {self.activePlayer} joins attacks: attacks with {printCards(attackCards)}...')

        # Check a card of this value appears on the table already somewhere.
        openAttacks = getCards(self.state, self.openAttacks)
        closedAttacks = getCards(self.state, self.closedAttacks)
        defences = getCards(self.state, self.defences)

        assert any(numpy.any(cards[1] == attackCard[1]) for cards in [closedAttacks, defences])
        assert self.state[self.activePlayer][attackCard] == 1
        totalAttacks = length(openAttacks) + length(closedAttacks)
        assert totalAttacks < self.maxAttacks

        self._updateStateAfterAttack(action)

    def _attack(self, action):
        attackCards = numpy.where(action[observables.openAttacks] == 1)
        print(f'Player {self.activePlayer} attacks with {printCards(attackCards)}...')

        # If attacking with multiple cards, check all the values are the same.
        assert numpy.unique(attackCards[1]).size == 1
        # Check player actually has these cards.
        assert numpy.all(self.state[self.activePlayer][attackCards] == 1)

        self._updateStateAfterAttack(action)

    def _bounce(self, action):
        bounceCards = numpy.where(action[observables.openAttacks] == 1)
        print(f'Player {self.activePlayer} bounces with {printCards(bounceCards)}...')

        assert self.activePlayer == self._getDefender()
        # Check there are only open attacks
        assert numberOfCards(self.state, self.closedAttacks) + numberOfCards(self.state, self.defences) == 0
        # Check all open attacks have same value
        attackValues = numpy.unique(getCards(self.state, self.openAttacks)[1])
        assert attackValues.size == 1
        # Check these cards have that value too
        assert numpy.all(bounceCards[1] == attackValues[0])

        self._updateAttackerAndDefender(newAttacker=self.activePlayer)
        self._updateStateAfterAttack(action)

    def _updateStateAfterAttack(self, action):
        self._applyAction(action)

        if numpy.sum(self.state[self.activePlayer]) == 0:
            print(f'Player {self.activePlayer} is out!')
            # Let the defender handle update of attacker/defender
            playerOut = self.activePlayer
            self.activePlayer = self._nextPlayer(playerOut)
            self.playersNotOut.remove(playerOut)
        else:
            self.activePlayer = self._nextPlayer(self.activePlayer)

        self._stateChanged()

    def _defend(self, action):
        attackingCards = numpy.where(action[observables.openAttacks] == -1)
        defendingCards = numpy.where(action[observables.defences] == 1)
        print(f'Player {self.activePlayer} defends {printCards(attackingCards)} with {printCards(defendingCards)}...')

        assert length(attackingCards) == 1
        assert length(defendingCards) == 1

        (attackingCardSuit, attackingCardValue) = (attackingCards[0][0], attackingCards[1][0])
        (defendingCardSuit, defendingCardValue) = (defendingCards[0][0], defendingCards[1][0])

        assert self.state[self.openAttacks][attackingCardSuit][attackingCardValue] == 1
        assert self.state[self.activePlayer][defendingCardSuit][defendingCardValue] == 1
        assert (defendingCardValue > attackingCardValue and defendingCardSuit == attackingCardSuit) \
               or self.state[self.trumps][defendingCardSuit][0] == 1 and defendingCardSuit != attackingCardSuit

        self._applyAction(action)

        if numberOfCards(self.state, self.activePlayer) == 0:
            print(f'Player {self.activePlayer} is out!')
            playerOut = self.activePlayer
            self.activePlayer = self._nextPlayer(playerOut)
            firstToPickUp = self._previousPlayer(playerOut)
            self.playersNotOut.remove(playerOut)
            self._successfulDefence(self.activePlayer, firstToPickUp)

        elif numberOfCards(self.state, self.defences) == self.maxAttacks:
            # Active player stays the same - defender becomes attacker
            self._successfulDefence(newAttacker=self.activePlayer, firstToPickUp=self.activePlayer)

        else:
            self.activePlayer = self._nextPlayer(self.activePlayer)
            self._stateChanged()

    def _concede(self, action):
        print(f'Player {self.activePlayer} concedes...')
        attacksToConcede = numpy.where(action[observables.openAttacks] == -1)

        numberOfOpenAttacks = numberOfCards(self.state, self.openAttacks)
        surplus = numberOfOpenAttacks - numberOfCards(self.state, self.activePlayer)
        assert surplus <= 0 and length(attacksToConcede) == numberOfOpenAttacks \
            or 0 < surplus == length(attacksToConcede)
        assert numpy.all(self.state[self.openAttacks][attacksToConcede] == 1)

        self._applyAction(action)

        # Burn any leftover open attacks
        leftovers = getCards(self.state, self.openAttacks)
        self.state[self.openAttacks][leftovers] = numpy.zeros(length(leftovers), dtype=int)
        self.state[self.burned][leftovers] = numpy.ones(length(leftovers), dtype=int)

        newAttacker = self._nextPlayer(self.activePlayer)
        firstToPickUp = self._previousPlayer(self.activePlayer)

        self._updateAttackerAndDefender(newAttacker)
        self.turns += 1
        self.activePlayer = self._nextPlayer(self.activePlayer)
        self._pickUpCards(firstToPickUp)

    def _declineToAttack(self, action):
        print(f'Player {self.activePlayer} declines to attack...')
        assert numpy.all(action == 0)
        self.declinedToAttack += 1

        everyoneDeclined = self.declinedToAttack == len(self.playersNotOut) - 1
        if length(getCards(self.state, self.openAttacks)) == 0 and everyoneDeclined:
            print(f'Everyone declines to attack...')
            defender = self._getDefender()
            assert self.activePlayer == self._previousPlayer(defender)
            # If this call has ended the round then we must have a successful defence.
            self._successfulDefence(newAttacker=defender, firstToPickUp=defender)

        self.activePlayer = self._nextPlayer(self.activePlayer)

    def _updateAttackerAndDefender(self, newAttacker):
        newDefender = self._nextPlayer(newAttacker)
        self._setAttacker(newAttacker)
        self._setDefender(newDefender)

    def _successfulDefence(self, newAttacker, firstToPickUp):
        # Burn closed attacks and defences, but also burn any open attacks -
        # the defender might just have used their last cards.
        print(f'Successful defence by player {self._getDefender()}!')
        for category in [self.openAttacks, self.closedAttacks, self.defences]:
            cards = getCards(self.state, category)
            self.state[category][cards] = numpy.zeros(length(cards), dtype=int)
            self.state[self.burned][cards] = numpy.ones(length(cards), dtype=int)

        self._updateAttackerAndDefender(newAttacker)
        self.turns += 1
        self._pickUpCards(firstToPickUp)

    def _stateIndex(self, observable):
        return self.numberOfPlayers - 1 + observable

    def _getAttacker(self):
        return self.state[self.attacker][0][0]

    def _setAttacker(self, attacker):
        self.state[self.attacker] = numpy.full((4,13), attacker, dtype=int)

    def _getDefender(self):
        return self.state[self.defender][0][0]

    def _setDefender(self, defender):
        self.state[self.defender] = numpy.full((4, 13), defender, dtype=int)

    def _nextPlayer(self, player):
        return self.playersNotOut[(self.playersNotOut.index(player) + 1) % len(self.playersNotOut)]

    def _previousPlayer(self, player):
        return self.playersNotOut[(self.playersNotOut.index(player) - 1) % len(self.playersNotOut)]

    def _actionComponents(self, player):
        return [player, self.openAttacks, self.closedAttacks, self.defences]

    def _applyAction(self, action):
        affectedState = self.state[self._actionComponents(self.activePlayer)]
        self.state[self._actionComponents(self.activePlayer)] = numpy.add(affectedState, action)
