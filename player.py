import random
import time
from functools import partial
from itertools import combinations

import numpy

from game import getCards, numberOfCards, length


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

        # ToDo: player should hold and update beliefs about other players' cards.
        self.cards = 0
        self.trumps = 1
        self.openAttacks = 2
        self.closedAttacks = 3
        self.defences = 4
        self.burned = 5

        self.attacker = 6
        self.defender = 7

    def play(self):
        state = self.game.getState(self.name)
        while self.hasCards(state) and not self.hasLost(state):
            actions = self.getPossibleActions(state)
            action = random.choice(actions)
            action()
            # time.sleep(random.uniform(0, 2))
            state = self.game.getState(self.name)
        if not self.hasLost(state):
            self.game.done(self.name, None)

    def hasCards(self, state):
        return numberOfCards(state, self.cards) > 0

    def hasLost(self, state):
        return numberOfCards(state, self.cards) + numberOfCards(state, self.burned) == 52

    def getPossibleActions(self, state):
        # Must only use the state to determine actions, nothing else.
        actions = []
        openAttacks = getCards(state, self.openAttacks)
        closedAttacks = getCards(state, self.closedAttacks)
        defences = getCards(state, self.defences)
        cards = getCards(state, self.cards)

        if self.isDefender(state):
            # Can't defend until we've been attacked.
            if length(openAttacks) == 0:
                return [partial(self.game.waitForUpdates, self.name, state)]

            if length(closedAttacks) + length(defences) == 0:
                # Can possibly bounce.
                attackValue = openAttacks[1][0]
                bounceCards = numpy.array(cards).T[numpy.where(cards[1] == attackValue)]
                bounces = allSublists(bounceCards)
                for bounce in bounces:
                    actions.append(partial(self.game.bounce, self.name, state, tuple(bounce.T)))

            # Can always concede.
            # If there are more open attacks than we have cards, then only pick up as many as we have cards.
            surplusAttacks = length(openAttacks) - length(cards)
            if surplusAttacks > 0:
                for attacks in combinations(numpy.array(openAttacks).T, surplusAttacks):
                    actions.append(partial(self.game.concede, self.name, state, tuple(numpy.array(attacks).T)))
            else:
                actions.append(partial(self.game.concede, self.name, state, openAttacks))

            # Can possibly defend
            # ToDo: optimise all this switching between numpy arrays and tuples
            for attack in numpy.array(openAttacks).T:
                for card in numpy.array(cards).T:
                    if self.canDefend(attack, card, state):
                        actions.append(partial(self.game.defend, self.name, state, tuple(card.T), tuple(attack.T)))

        elif self.isAttacker(state) and length(openAttacks) + length(closedAttacks) == 0:
            # Can attack with multiple cards of the same value
            for value in range(13):
                valueCards = numpy.array(cards).T[numpy.where(cards[1] == value)]
                attacks = allSublists(valueCards)
                for attack in attacks:
                    actions.append(partial(self.game.attack, self.name, state, tuple(attack.T)))

        # Can only attack if defender has elected to defend and there are fewer than 'maxAttacks' attacks already.
        elif length(defences) > 0 and length(openAttacks) + length(closedAttacks) < self.game.maxAttacks:
            # Can always decline to attack
            actions.append(partial(self.game.declineToAttack, self.name, state))
            # Can only attack with cards whose values are already on the table.
            valuesAllowed = numpy.concatenate((closedAttacks[1], defences[1]), axis=None)
            indices = numpy.where(numpy.isin(cards[1], valuesAllowed))[0]
            for i in indices:
                card = (cards[0][i], cards[1][i])
                actions.append(partial(self.game.joinAttack, self.name, state, card))

        else:
            # Have to wait for updates.
            actions.append(partial(self.game.waitForUpdates, self.name, state))

        return actions

    def isDefender(self, state):
        return state[self.defender][0][0] == 0

    def isAttacker(self, state):
        return state[self.attacker][0][0] == 0

    def canDefend(self, attack, card, state):
        (attackSuit, attackValue) = tuple(attack)
        (suit, value) = tuple(card)
        if suit == attackSuit:
            return value > attackValue
        else:
            return state[self.trumps][suit][0] == 1
