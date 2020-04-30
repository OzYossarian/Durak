import numpy


class Masker:
    def __init__(self):
        self.totalActions = 195 + 52 + 182 + 2704 + 1 + 1
        self.attackStart = 0
        self.joinAttackStart = self.attackStart + 195
        self.bounceStart = self.joinAttackStart + 52
        self.defendStart = self.bounceStart + 182
        self.concedeIndex = self.defendStart + 2704
        self.declineToAttackIndex = self.concedeIndex + 1

        self.attackCode = 0
        self.joinAttackCode = 1
        self.bounceCode = 2
        self.defenceCode = 3
        self.concedeCode = 4
        self.declineToAttackCode = 5

        self.threeCombos = [
            (0,), (1,), (2,), (3,),
            (0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3),
            (0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3),
        ]
        self.fourCombos = self.threeCombos + [(0, 1, 2, 3)]

        self.defenceTable = numpy.arange(52 * 52).reshape((4, 13, 4, 13))
        self.joinAttackTable = numpy.arange(52).reshape(4, 13)

    def attackIndex(self, cards):
        values = set(cards[1])
        assert len(values) == 1
        value = values.pop()
        # Once assertion works, just do:
        # value = cards[1][0]
        return self.attackStart + (value * len(self.fourCombos)) + self.fourCombos.index(tuple(cards[0]))

    def joinAttackIndex(self, card):
        return self.joinAttackStart + self.joinAttackTable[card[0]][card[1]]

    def bounceIndex(self, cards):
        values = set(cards[1])
        assert len(values) == 1
        value = values.pop()
        # Once assertion works, just do:
        # value = cards[1][0]
        return self.bounceStart + (value * len(self.threeCombos)) + self.threeCombos.index(tuple(cards[0]))

    def defenceIndex(self, attack, defence):
        return self.defendStart + self.defenceTable[attack[0]][attack[1]][defence[0]][defence[1]]

    def mask(self, validActions):
        mask = numpy.zeros(self.totalActions, dtype=int)
        try:
            mask[validActions] = 1
        except:
            print(f'Valid actions: {validActions}')
            raise AssertionError
        return mask

    def action(self, actionIndex):
        if actionIndex < self.joinAttackStart:
            return self.attackAction(actionIndex)
        elif actionIndex < self.bounceStart:
            return self.joinAttackAction(actionIndex - self.joinAttackStart)
        elif actionIndex < self.defendStart:
            return self.bounceAction(actionIndex - self.bounceStart)
        elif actionIndex < self.concedeIndex:
            return self.defenceAction(actionIndex - self.defendStart)
        elif actionIndex == self.concedeIndex:
            return self.concedeCode, None
        elif actionIndex == self.declineToAttackIndex:
            return self.declineToAttackCode, None
        else:
            raise ValueError('Unrecognised action index')

    def attackAction(self, attackIndex):
        value = attackIndex / len(self.fourCombos)
        suits = self.fourCombos[attackIndex % len(self.fourCombos)]
        cards = (numpy.array(suits, dtype=int), numpy.array([value for _ in range(len(suits))], dtype=int))
        return self.attackCode, cards

    def joinAttackAction(self, joinAttackIndex):
        card = numpy.unravel_index([joinAttackIndex], (4, 13))
        return self.joinAttackCode, card

    def bounceAction(self, bounceIndex):
        value = bounceIndex / len(self.threeCombos)
        suits = self.threeCombos[bounceIndex % len(self.threeCombos)]
        cards = (numpy.array(suits, dtype=int), numpy.array([value for _ in range(len(suits))], dtype=int))
        return self.bounceCode, cards

    def defenceAction(self, defenceIndex):
        indices = numpy.unravel_index([defenceIndex], (4, 13, 4, 13))
        attack = indices[0:2]
        defence = indices[2:4]
        return self.defenceCode, (attack, defence)
