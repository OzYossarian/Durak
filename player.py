import random
import time
from functools import partial
from itertools import combinations

from game import getCards


def allSublists(xs, maxSize=None):
    if maxSize is None:
        maxSize = len(xs)
    return [list(ys) for i in range(1, maxSize + 1) for ys in combinations(xs, i)]


class Player:
    def __init__(self, name, game):
        # Players should all believe that they are player 0, although they will have a 'true' name too.
        # The indices of the attacker and defender will then be relative to this player.
        self.name = name
        self.game = game

        self.openAttacks = 1
        self.closedAttacks = 2
        self.defences = 3
        self.trumps = 4
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

            if len(closedAttacks) + len(defences) == 0:
                # Can possibly bounce.
                attackValue = openAttacks[0][0]
                bounceCards = [(value, suit) for (value, suit) in cards if value == attackValue]
                bounces = allSublists(bounceCards)
                for bounce in bounces:
                    actions.append(partial(self.game.bounce, self.name, state, bounce))

            # Can always concede.
            # If there are more open attacks than we have cards, then only pick up as many as we have cards.
            surplusAttacks = len(openAttacks) - len(cards)
            if surplusAttacks > 0:
                for attacks in combinations(openAttacks, surplusAttacks):
                    actions.append(partial(self.game.concede, self.name, state, list(attacks)))
            else:
                actions.append(partial(self.game.concede, self.name, state, openAttacks))

            # Can possibly defend
            for attack in openAttacks:
                for card in cards:
                    if self.canDefend(attack, card, state):
                        actions.append(partial(self.game.defend, self.name, state, card, attack))

        elif self.isAttacker(state) and len(openAttacks) + len(closedAttacks) == 0:
            # Can attack with multiple cards of the same value
            for v in range(13):
                vCards = [(value, suit) for (value, suit) in cards if value == v]
                attacks = allSublists(vCards)
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
        return state[self.defender][0][0] == 0

    def isAttacker(self, state):
        return state[self.attacker][0][0] == 0

    def canDefend(self, attack, card, state):
        (attackValue, attackSuit) = attack
        (value, suit) = card
        if suit == attackSuit:
            return value > attackValue
        else:
            return suit == state[self.trumps][0][0]
