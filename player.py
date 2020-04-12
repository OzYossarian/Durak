import random
import time


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
            if len(actions) == 0:
                # No actions available yet - wait for updates.
                state = self.game.getState(self.name)
            else:
                action = actions[-1]
                state = action(self.name, state)
                if state is None:
                    # Our action was accepted.
                    time.sleep(random.uniform(0, 1))
                    state = self.game.getState(self.name)

                # If state not None, our action was rejected, so pick again based on updated state.

    def hasCards(self, state):
        return sum([sum(suit) for suit in state[0]]) > 0

    def getPossibleActions(self, state):
        # Must only use the state to determine actions, nothing else.
        actions = []

        if (self.isDefending(state)):
            if sum(sum(suit) for suit in state[self.openAttack]) == 0:
                # Can't defend until we've been attacked.
                return []
            actions.append(self.game.concede)

        actions.append(self.game.decline)
        return actions

    def isDefending(self, state):
        return state[self.defender][0][0] == self.name


