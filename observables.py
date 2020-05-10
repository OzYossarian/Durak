import numpy

cards = 0
openAttacks = 1
closedAttacks = 2
defences = 3
trumps = 4
burned = 5
attacker = 6
defender = 7
pack = 8

extras = 6
absoluteAttacker = 0
absoluteDefender = 1
relativeAttacker = 2
relativeDefender = 3
bounceLimit = 4
defenderCardsLength = 5


def getAttacker(observation):
    return observation[extras][suit(absoluteAttacker)][value(absoluteAttacker)]


def getDefender(observation):
    return observation[extras][suit(absoluteDefender)][value(absoluteDefender)]


def getRelativeAttacker(observation):
    return observation[extras][suit(absoluteAttacker)][value(absoluteAttacker)]


def getRelativeDefender(observation):
    return observation[extras][suit(absoluteDefender)][value(absoluteDefender)]


def getBounceLimit(observation):
    return observation[extras][suit(bounceLimit)][value(bounceLimit)]


def getDefenderCardsLength(observation):
    return observation[extras][suit(defenderCardsLength)][value(defenderCardsLength)]


def encodeExtras(data):
    # Ultimately the splitter will encode attacker and defender as constant matrices. For now, we can
    # treat the last part of the observation as a space to include data that we need in order to calculate
    # the action mask, but which won't be passed to the network.
    encoded = numpy.zeros(2 * 4 * 13, dtype=int)
    for i in range(len(data)):
        encoded[i] = data[i]
    encoded = encoded.reshape((2, 4, 13))
    return encoded


def playerObservation(observation):
    attackerMatrix = numpy.full((4, 13), getRelativeAttacker(observation), dtype=int)
    defenderMatrix = numpy.full((4, 13), getRelativeDefender(observation), dtype=int)
    observation[attacker] = attackerMatrix
    observation[defender] = defenderMatrix
    return observation


def suit(index):
    return index // 13


def value(index):
    return index % 13
