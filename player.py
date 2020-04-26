import random
import time
from itertools import combinations

import numpy

import observables
from game import getCards, length


def allSublists(xs, maxSize=None):
    if maxSize is None:
        maxSize = len(xs)
    return [numpy.array(ys) for i in range(1, maxSize + 1) for ys in combinations(xs, i)]


class Player:
    def __init__(self, name, maxAttacks):
        # Players should all believe that they are player 0, although they will have a 'true' name too.
        # The indices of the attacker and defender will then be relative to this player.
        self.name = name
        self.maxAttacks = maxAttacks

        # ToDo: player could hold and update beliefs about other players' cards?

    def act(self, observation):
        actions = self._getPossibleActions(observation)
        action = random.choice(actions)
        return action

    def _getPossibleActions(self, observation):
        # Must only use the state to determine actions, nothing else.
        openAttacks = getCards(observation, observables.openAttacks)
        closedAttacks = getCards(observation, observables.closedAttacks)
        defences = getCards(observation, observables.defences)
        cards = getCards(observation, observables.playerCards)

        if self._isDefender(observation):
            if length(openAttacks) == 0:
                # Can't defend until we've been attacked.
                return [self._createAction([])]
            actions = []
            if length(closedAttacks) + length(defences) == 0:
                actions.extend(self._bounceActions(cards, openAttacks))
            actions.extend(self._concedeActions(cards, openAttacks, closedAttacks, defences))
            actions.extend(self._defendActions(cards, openAttacks, observation))
            return actions

        elif self._isAttacker(observation) and length(openAttacks) + length(closedAttacks) == 0:
            return list(self._attackActions(cards))

        # Can only attack if defender has elected to defend and there are fewer than 'maxAttacks' attacks already.
        elif length(defences) > 0 and length(openAttacks) + length(closedAttacks) < self.maxAttacks:
            # Can always decline to attack.
            actions = [self._createAction([])]
            actions.extend(self._joinAttackActions(cards, closedAttacks, defences))
            return actions

        else:
            return [self._createAction([])]

    def _concedeActions(self, cards, openAttacks, closedAttacks, defences):
        # If there are more open attacks than we have cards, then only pick up as many as we have cards.
        actions = []
        pickUpClosedAttacks = [
            (observables.playerCards, closedAttacks, 1),
            (observables.closedAttacks, closedAttacks, -1)]
        pickUpDefences = [(observables.playerCards, defences, 1), (observables.defences, defences, -1)]

        surplusAttacks = length(openAttacks) - length(cards)
        if surplusAttacks > 0:
            for attacks in combinations(numpy.array(openAttacks).T, surplusAttacks):
                attacks = tuple(numpy.array(attacks).T)
                # Concede all the defences and closed attacks
                pickUpOpenAttacks = [(observables.playerCards, attacks, 1), (observables.openAttacks, attacks, -1)]
                action = self._createAction(pickUpClosedAttacks + pickUpOpenAttacks + pickUpDefences)
                actions.append(action)
        else:
            pickUpOpenAttacks = [(observables.playerCards, openAttacks, 1), (observables.openAttacks, openAttacks, -1)]
            action = self._createAction(pickUpClosedAttacks + pickUpOpenAttacks + pickUpDefences)
            actions.append(action)
        return actions

    def _joinAttackActions(self, cards, closedAttacks, defences):
        # Can only attack with cards whose values are already on the table.
        valuesAllowed = numpy.concatenate((closedAttacks[1], defences[1]), axis=None)
        indices = numpy.where(numpy.isin(cards[1], valuesAllowed))[0]
        for i in indices:
            card = (cards[0][i], cards[1][i])
            yield self._createAction([(observables.playerCards, card, -1), (observables.openAttacks, card, 1)])

    def _attackActions(self, cards):
        # Can attack with multiple cards of the same value
        for value in range(13):
            valueCards = numpy.array(cards).T[numpy.where(cards[1] == value)]
            attacks = allSublists(valueCards)
            for attack in attacks:
                yield self._createAction([
                    (observables.playerCards, tuple(attack.T), -1),
                    (observables.openAttacks, tuple(attack.T), 1)])

    def _defendActions(self, cards, openAttacks, observation):
        # ToDo: optimise all this switching between numpy arrays and tuples
        for attack in numpy.array(openAttacks).T:
            for card in numpy.array(cards).T:
                if self._canDefend(attack, card, observation):
                    addDefence = [
                        (observables.playerCards, tuple(card.T), -1),
                        (observables.defences, tuple(card.T), 1)]
                    closeAttack = [
                        (observables.openAttacks, tuple(attack.T), -1),
                        (observables.closedAttacks, tuple(attack.T), 1)]
                    yield self._createAction(addDefence + closeAttack)

    def _bounceActions(self, cards, openAttacks):
        attackValue = openAttacks[1][0]
        bounceCards = numpy.array(cards).T[numpy.where(cards[1] == attackValue)]
        bounces = allSublists(bounceCards)
        for bounce in bounces:
            yield self._createAction([
                (observables.playerCards, tuple(bounce.T), -1),
                (observables.openAttacks, tuple(bounce.T), 1)])

    def _createAction(self, changes):
        action = numpy.zeros((4, 4, 13), dtype=int)
        for category, cards, value in changes:
            action[category][cards] = numpy.full(length(cards), value, dtype=int)
        return action

    def _isDefender(self, observation):
        return observation[observables.defender][0][0] == 0

    def _isAttacker(self, observation):
        return observation[observables.attacker][0][0] == 0

    def _canDefend(self, attack, card, observation):
        (attackSuit, attackValue) = tuple(attack)
        (suit, value) = tuple(card)
        if suit == attackSuit:
            return value > attackValue
        else:
            return observation[observables.trumps][suit][0] == 1
