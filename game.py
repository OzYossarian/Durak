import random
import numpy

import observables
from cardUtils import numberOfCards, printSuit, printCards, length, getCards, getTrumps
from masker import Masker
from player import Player


class Game():
    def __init__(self, numberOfPlayers, minCards, maxAttacks):
        self.numberOfPlayers = numberOfPlayers
        self.minCards = minCards
        self.maxAttacks = maxAttacks

        self.masker = Masker()
        self.players = [Player(i, self.masker, maxAttacks) for i in range(numberOfPlayers)]

        self.openAttacks = self._stateIndex(observables.openAttacks)
        self.closedAttacks = self._stateIndex(observables.closedAttacks)
        self.defences = self._stateIndex(observables.defences)
        self.trumps = self._stateIndex(observables.trumps)
        self.burned = self._stateIndex(observables.burned)
        self.attacker = self._stateIndex(observables.attacker)
        self.defender = self._stateIndex(observables.defender)
        self.pack = self._stateIndex(observables.pack)

        # Initialise these later
        self.state = None
        self.declinedToAttack = None
        self.playersNotOut = None
        self.activePlayer = None
        self.turns = None
        self.gameOver = None

    def step(self):
        observation = self.observation(self.activePlayer)
        action = self.players[self.activePlayer].act(observation)
        self.updateState(action)

    def updateState(self, actionIndex):
        actions = [self._attack, self._joinAttack, self._bounce, self._defend, self._concede, self._declineToAttack]
        action, data = self.masker.action(actionIndex)
        actions[action](data)
        self.gameOver = len(self.playersNotOut) == 1

    def play(self):
        while not self.gameOver:
            self.step()

    def initialiseState(self):
        self.declinedToAttack = 0
        self.playersNotOut = list(range(self.numberOfPlayers))
        self.turns = 0
        self.gameOver = False

        self.state = numpy.zeros((self.numberOfPlayers + 8, 4, 13), dtype=int)

        trumps = random.randrange(4)
        self.state[self.trumps][trumps] = 1
        self.state[self.pack] = 1

        attacker = random.randrange(self.numberOfPlayers)
        defender = (attacker + 1) % self.numberOfPlayers
        self._setAttacker(attacker)
        self._setDefender(defender)
        self.activePlayer = attacker

        self._pickUpCards(self._getDefender())

    def observation(self, player):
        # Attacker and defender should be relative to this player.
        attacker = self._getAttacker()
        defender = self._getDefender()
        relativeAttacker = (attacker - player) % self.numberOfPlayers
        relativeDefender = (defender - player) % self.numberOfPlayers

        bounceLimit = length(self._getCards(self._nextPlayer(player)))
        defenderCardsLength = length(self._getCards(self._getDefender()))

        extras = [attacker, defender, relativeAttacker, relativeDefender, bounceLimit, defenderCardsLength]
        extras = observables.encodeExtras(extras)

        basics = [player, self.openAttacks, self.closedAttacks, self.defences, self.trumps, self.burned]

        return numpy.concatenate((self.state[basics], extras), axis=0)

    def _pickUpCards(self, firstToPickUp):
        pack = numpy.array(self._getCards(self.pack))
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
                    self.state[self.pack][newCards] = 0
                    self.state[player][newCards] = 1
                player = self._previousPlayer(player)

        self._stateChanged()

    def _stateChanged(self):
        print(f'\nGame state:\n')
        print(self.state)
        print(f'\n\nTrumps are {printSuit[getTrumps(self.state, self.trumps)]}.')
        print(f'Players {", ".join([str(player) for player in self.playersNotOut])} are still in')
        print(f'Player {self.activePlayer} is active\n')

        self.declinedToAttack = 0

    def _attack(self, attackCards):
        print(f'Player {self.activePlayer} attacks with {printCards(attackCards)}...')

        # If attacking with multiple cards, check all the values are the same.
        assert numpy.unique(attackCards[1]).size == 1
        # Check player actually has these cards.
        assert numpy.all(self.state[self.activePlayer][attackCards] == 1)

        self.state[self.activePlayer][attackCards] = 0
        self.state[self.openAttacks][attackCards] = 1

        self._updateStateAfterAttack()

    def _joinAttack(self, attackCard):
        print(f'Player {self.activePlayer} joins attacks: attacks with {printCards(attackCard)}...')

        # Check a card of this value appears on the table already somewhere.
        openAttacks = self._getCards(self.openAttacks)
        closedAttacks = self._getCards(self.closedAttacks)
        defences = self._getCards(self.defences)

        assert any(numpy.any(cards[1] == attackCard[1]) for cards in [closedAttacks, defences])
        assert self.state[self.activePlayer][attackCard] == 1
        totalAttacks = length(openAttacks) + length(closedAttacks)
        assert totalAttacks < self.maxAttacks

        self.state[self.activePlayer][attackCard] = 0
        self.state[self.openAttacks][attackCard] = 1

        self._updateStateAfterAttack()

    def _bounce(self, bounceCards):
        print(f'Player {self.activePlayer} bounces with {printCards(bounceCards)}...')

        assert self.activePlayer == self._getDefender()
        # Check there are only open attacks
        assert numberOfCards(self.state, self.closedAttacks) + numberOfCards(self.state, self.defences) == 0
        # Check all open attacks have same value
        attackValues = numpy.unique(self._getCards(self.openAttacks)[1])
        assert attackValues.size == 1
        # Check these cards have that value too
        assert numpy.all(bounceCards[1] == attackValues[0])

        self.state[self.openAttacks][bounceCards] = 1
        self.state[self.activePlayer][bounceCards] = 0

        self._updateAttackerAndDefender(newAttacker=self.activePlayer)
        self._updateStateAfterAttack()

    def _updateStateAfterAttack(self):
        if numpy.sum(self.state[self.activePlayer]) == 0:
            print(f'Player {self.activePlayer} is out!')
            # Let the defender handle update of attacker/defender
            playerOut = self.activePlayer
            self.activePlayer = self._nextPlayer(playerOut)
            self.playersNotOut.remove(playerOut)
        else:
            self.activePlayer = self._nextPlayer(self.activePlayer)

        self._stateChanged()

    def _defend(self, cards):
        attack, defence = cards
        print(f'Player {self.activePlayer} defends {printCards(attack)} with {printCards(defence)}...')

        (attackSuit, attackingValue) = (attack[0][0], attack[1][0])
        (defenceSuit, defenceValue) = (defence[0][0], defence[1][0])

        assert self.state[self.openAttacks][attack] == 1
        assert self.state[self.activePlayer][defence] == 1
        assert (defenceValue > attackingValue and defenceSuit == attackSuit) \
               or self.state[self.trumps][defenceSuit][0] == 1 and defenceSuit != attackSuit

        self.state[self.openAttacks][attack] = 0
        self.state[self.closedAttacks][attack] = 1
        self.state[self.activePlayer][defence] = 0
        self.state[self.defences][defence] = 1

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

    def _concede(self, _):
        print(f'Player {self.activePlayer} concedes...')

        # Concede all the cards on the table
        for category in [self.openAttacks, self.closedAttacks, self.defences]:
            cards = self._getCards(category)
            self.state[category][cards] = 0
            self.state[self.activePlayer][cards] = 1

        newAttacker = self._nextPlayer(self.activePlayer)
        firstToPickUp = self._previousPlayer(self.activePlayer)

        self._updateAttackerAndDefender(newAttacker)
        self.turns += 1
        self.activePlayer = self._nextPlayer(self.activePlayer)
        self._pickUpCards(firstToPickUp)

    def _declineToAttack(self, _):
        print(f'Player {self.activePlayer} declines to attack...')
        self.declinedToAttack += 1

        everyoneDeclined = self.declinedToAttack == len(self.playersNotOut) - 1
        if length(self._getCards(self.openAttacks)) == 0 and everyoneDeclined:
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
            cards = self._getCards(category)
            self.state[category][cards] = 0
            self.state[self.burned][cards] = 1

        self._updateAttackerAndDefender(newAttacker)
        self.turns += 1
        self._pickUpCards(firstToPickUp)

    def _getCards(self, category):
        return getCards(self.state, category)

    def _stateIndex(self, observable):
        return self.numberOfPlayers - 1 + observable

    def _setAttacker(self, attacker):
        self.state[self.attacker] = numpy.full((4, 13), attacker, dtype=int)

    def _getAttacker(self):
        return self.state[self.attacker][0][0]

    def _setDefender(self, defender):
        self.state[self.defender] = numpy.full((4, 13), defender, dtype=int)

    def _getDefender(self):
        return self.state[self.defender][0][0]

    def _nextPlayer(self, player):
        return self.playersNotOut[(self.playersNotOut.index(player) + 1) % len(self.playersNotOut)]

    def _previousPlayer(self, player):
        return self.playersNotOut[(self.playersNotOut.index(player) - 1) % len(self.playersNotOut)]
