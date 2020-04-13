import random
import time
from functools import partial
from itertools import combinations

from game import getCards


def allSublists(xs, maxSize):
    return [list(ys) for i in range(1, maxSize + 1) for ys in combinations(xs, i)]


class Player:
    def __init__(self, name, game):
        self.name = name
        self.game = game

        self.attacker = 1
        self.defender = 2
        self.openAttacks = 3
        self.closedAttacks = 4
        self.defences = 5
        self.trumps = 6
        self.burned = 7

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
        return sum([sum(suit) for suit in state[0]]) > 0

    def hasLost(self, state):
        return sum([sum(suit) for suit in state[0]]) + sum([sum(suit) for suit in state[self.burned]]) == 52


    def getPossibleActions(self, state):
        # Must only use the state to determine actions, nothing else.
        actions = []
        openAttacks = getCards(state, self.openAttacks)
        closedAttacks = getCards(state, self.closedAttacks)
        defences = getCards(state, self.defences)
        cards = getCards(state, 0)

        if self.isDefender(state):
            # Can't defend until we've been attacked.
            if len(openAttacks) == 0:
                return [partial(self.game.waitForUpdates, self.name, state)]

            # Must either defend or concede
            # If there are more open attacks than we have cards, then only pick up as many as we have cards
            surplusAttacks = len(openAttacks) - len(cards)
            if surplusAttacks > 0:
                for attacks in combinations(openAttacks, surplusAttacks):
                    actions.append(partial(self.game.concede, self.name, state, list(attacks)))
            else:
                actions.append(partial(self.game.concede, self.name, state, openAttacks))
            for attack in openAttacks:
                for card in cards:
                    if self.canDefend(attack, card, state):
                        actions.append(partial(self.game.defend, self.name, state, card, attack))

        elif self.isAttacker(state) and len(openAttacks) + len(closedAttacks) == 0:
            # Can attack with multiple cards of the same value
            for v in range(13):
                vCards = [(value, suit) for (value, suit) in cards if value == v]
                attacks = allSublists(vCards, len(vCards))
                [actions.append(partial(self.game.attack, self.name, state, attack)) for attack in attacks]

        # Can only attack if defender has elected to defend and there are fewer than five attacks already.
        elif len(defences) > 0 and len(openAttacks) + len(closedAttacks) < 5:
            # Can only attack with cards whose values are already on the table.
            actions.append(partial(self.game.declineToAttack, self.name, state))
            for card in cards:
                if any(value == card[0] for (value, _) in openAttacks + closedAttacks + defences):
                    actions.append(partial(self.game.joinAttack, self.name, state, card))

        else:
            # Have to wait for updates.
            actions.append(partial(self.game.waitForUpdates, self.name, state))

        return actions

    def isDefender(self, state):
        return state[self.defender][0][0] == self.name

    def isAttacker(self, state):
        return state[self.attacker][0][0] == self.name

    def canDefend(self, attack, card, state):
        (attackValue, attackSuit) = attack
        (value, suit) = card
        if suit == attackSuit:
            return value > attackValue
        else:
            return suit == state[self.trumps][0][0]
