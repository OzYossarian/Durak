import random
import numpy
import observables
from cardUtils import length, getCards, allSublists, getTrumps


class Player:
    def __init__(self, name, masker, maxAttacks):
        # Players should all believe that they are player 0, although they will have a 'true' name too.
        # The indices of the attacker and defender will then be relative to this player.
        self.name = name
        self.masker = masker
        self.maxAttacks = maxAttacks

        # ToDo: player could hold and update beliefs about other players' cards?

    def act(self, observation):
        actionMask = self.getActionMask(observation)
        # Eventually the playerObservation will be input to some sort of policy method.
        playerObservation = observables.playerObservation(observation)
        action = random.choice(numpy.where(actionMask == 1)[0])
        return action

    def getActionMask(self, observation):
        openAttacks = getCards(observation, observables.openAttacks)
        closedAttacks = getCards(observation, observables.closedAttacks)
        defences = getCards(observation, observables.defences)
        cards = getCards(observation, observables.cards)
        defenderCardsLength = observables.getDefenderCardsLength(observation)

        if self.name == observables.getDefender(observation):
            # Can always concede
            actions = [self.masker.concedeIndex]
            if length(closedAttacks) + length(defences) == 0:
                actions.extend(self._bounceActions(cards, openAttacks, observables.getBounceLimit(observation)))
            actions.extend(self._defendActions(cards, openAttacks, getTrumps(observation, observables.trumps)))
            return self.masker.mask(actions)

        elif self.name == observables.getAttacker(observation) and length(openAttacks) + length(closedAttacks) == 0:
            return self.masker.mask(list(self._attackActions(cards, defenderCardsLength)))

        # Can only attack if there are fewer than 'maxAttacks' attacks already.
        elif length(openAttacks) + length(closedAttacks) < self.maxAttacks:
            assert length(defences) > 0
            assert defenderCardsLength > 0
            # Can always decline to attack.
            actions = [self.masker.declineToAttackIndex]
            actions.extend(self._joinAttackActions(cards, closedAttacks, defences))
            return self.masker.mask(actions)

        else:
            return self.masker.mask([self.masker.declineToAttackIndex])

    def _joinAttackActions(self, cards, closedAttacks, defences):
        # Can only attack with cards whose values are already on the table.
        valuesAllowed = numpy.concatenate((closedAttacks[1], defences[1]), axis=None)
        indices = numpy.where(numpy.isin(cards[1], valuesAllowed))[0]
        for i in indices:
            card = (cards[0][i], cards[1][i])
            yield self.masker.joinAttackIndex(card)

    def _attackActions(self, cards, defenderCardsLength):
        # Can attack with multiple cards of the same value.
        # Only allow as many attacks as the defender has cards left.
        for value in range(13):
            valueCards = numpy.array(cards).T[numpy.where(cards[1] == value)]
            attacks = allSublists(valueCards, maxSize=defenderCardsLength)
            for attack in attacks:
                yield self.masker.attackIndex(tuple(attack.T))

    def _defendActions(self, cards, openAttacks, trumps):
        # ToDo: optimise all this switching between numpy arrays and tuples?
        for attack in numpy.array(openAttacks).T:
            for card in numpy.array(cards).T:
                if self._canDefend(attack, card, trumps):
                    yield self.masker.defenceIndex(tuple(attack), tuple(card))

    def _bounceActions(self, cards, openAttacks, bounceLimit):
        attackValue = openAttacks[1][0]
        bounceCards = numpy.array(cards).T[numpy.where(cards[1] == attackValue)]
        # Don't allow a situation where the would-be defender has to defend more cards than they have left.
        maxSize = bounceLimit - length(openAttacks)
        if maxSize > 0:
            bounces = allSublists(bounceCards, maxSize)
            for bounce in bounces:
                yield self.masker.bounceIndex(tuple(bounce.T))

    def _canDefend(self, attack, card, trumps):
        (attackSuit, attackValue) = tuple(attack)
        (suit, value) = tuple(card)
        if suit == attackSuit:
            return value > attackValue
        else:
            return suit == trumps
