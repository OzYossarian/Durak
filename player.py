import random
import numpy
from itertools import combinations
from cardUtils import length


def allSublists(xs, maxSize=None):
    if maxSize is None:
        maxSize = len(xs)
    return [numpy.array(ys) for i in range(1, maxSize + 1) for ys in combinations(xs, i)]


class Player:
    def __init__(self, name, game):
        # Players should all believe that they are player 0, although they will have a 'true' name too.
        # The indices of the attacker and defender will then be relative to this player.
        self.name = name
        self.game = game

        # ToDo: player could hold and update beliefs about other players' cards?

    def act(self, observation):
        actionMask = self.getActionMask()
        action = random.choice(numpy.where(actionMask == 1)[0])
        return action

    def getActionMask(self):
        openAttacks = self.game.getCards(self.game.openAttacks)
        closedAttacks = self.game.getCards(self.game.closedAttacks)
        defences = self.game.getCards(self.game.defences)
        cards = self.game.getCards(self.name)

        if self.name == self.game.getDefender():
            # Can always concede
            actions = [self.game.masker.concedeIndex]
            if length(closedAttacks) + length(defences) == 0:
                actions.extend(self._bounceActions(cards, openAttacks))
            actions.extend(self._defendActions(cards, openAttacks))
            return self.game.masker.mask(actions)

        elif self.name == self.game.getAttacker() and length(openAttacks) + length(closedAttacks) == 0:
            return self.game.masker.mask(list(self._attackActions(cards)))

        # Can only attack if there are fewer than 'maxAttacks' attacks already.
        elif length(openAttacks) + length(closedAttacks) < self.game.maxAttacks:
            assert length(defences) > 0
            assert length(self.game.getCards(self.game.getDefender())) > 0
            # Can always decline to attack.
            actions = [self.game.masker.declineToAttackIndex]
            actions.extend(self._joinAttackActions(cards, closedAttacks, defences))
            return self.game.masker.mask(actions)

        else:
            return self.game.masker.mask([self.game.masker.declineToAttackIndex])

    def _joinAttackActions(self, cards, closedAttacks, defences):
        # Can only attack with cards whose values are already on the table.
        valuesAllowed = numpy.concatenate((closedAttacks[1], defences[1]), axis=None)
        indices = numpy.where(numpy.isin(cards[1], valuesAllowed))[0]
        for i in indices:
            card = (cards[0][i], cards[1][i])
            yield self.game.masker.joinAttackIndex(card)

    def _attackActions(self, cards):
        # Can attack with multiple cards of the same value.
        # Only allow as many attacks as the defender has cards left.
        maxSize = length(self.game.getCards(self.game.getDefender()))
        for value in range(13):
            valueCards = numpy.array(cards).T[numpy.where(cards[1] == value)]
            attacks = allSublists(valueCards, maxSize)
            for attack in attacks:
                yield self.game.masker.attackIndex(tuple(attack.T))

    def _defendActions(self, cards, openAttacks):
        # ToDo: optimise all this switching between numpy arrays and tuples?
        for attack in numpy.array(openAttacks).T:
            for card in numpy.array(cards).T:
                if self._canDefend(attack, card):
                    yield self.game.masker.defenceIndex(tuple(attack), tuple(card))

    def _bounceActions(self, cards, openAttacks):
        attackValue = openAttacks[1][0]
        bounceCards = numpy.array(cards).T[numpy.where(cards[1] == attackValue)]
        # Don't allow a situation where the would-be defender has to defend more cards than they have left.
        wouldBeDefender = self.game.nextPlayer(self.name)
        maxSize = length(self.game.getCards(wouldBeDefender)) - length(openAttacks)
        if maxSize > 0:
            bounces = allSublists(bounceCards, maxSize)
            for bounce in bounces:
                yield self.game.masker.bounceIndex(tuple(bounce.T))

    def _canDefend(self, attack, card):
        (attackSuit, attackValue) = tuple(attack)
        (suit, value) = tuple(card)
        if suit == attackSuit:
            return value > attackValue
        else:
            return suit == self.game.getTrumps()
