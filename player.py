import random
import time

from game import getCards


class Player:
    def __init__(self, name, game):
        self.name = name
        self.game = game

        self.attacker = 1
        self.defender = 2
        self.openAttack = 3
        self.closedAttack = 4
        self.defence = 5
        self.trumps = 6
        self.burned = 7

    def play(self):
        state = self.game.getState(self.name)
        while self.hasCards(state):
            actions = self.getPossibleActions(state)
            action = actions[-1]
            action()
            # time.sleep(random.uniform(0, 1))
            state = self.game.getState(self.name)

    def hasCards(self, state):
        return sum([sum(suit) for suit in state[0]]) > 0

    def getPossibleActions(self, state):
        # Must only use the state to determine actions, nothing else.
        actions = [lambda: self.game.waitForUpdates(self.name, state)]

        if (self.isDefending(state)):
            openAttacks = getCards(state, self.openAttack)
            # Can't defend until we've been attacked.
            if len(openAttacks) > 0:
                actions.append(lambda: self.game.concede(self.name, state))
                cards = getCards(state, 0)
                for attack in openAttacks:
                    for card in cards:
                        if self.canDefend(attack, card, state):
                            actions.append(lambda: self.game.defend(self.name, state, card, attack))
        else:
            actions.append(lambda: self.game.declineToAttack(self.name, state))

        return actions

    def isDefending(self, state):
        return state[self.defender][0][0] == self.name

    def canDefend(self, attack, card, state):
        (attackValue, attackSuit) = attack
        (value, suit) = card
        result = value > attackValue and suit == attackSuit

        trumps = state[self.trumps][0][0]
        if attackSuit != trumps:
            result = result or suit == trumps

        return result


