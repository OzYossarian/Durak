from itertools import combinations

import numpy

printSuit = ['S', 'C', 'H', 'D']
printValue = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']


def length(cards):
    return cards[0].size


def allSublists(xs, maxSize=None):
    if maxSize is None:
        maxSize = len(xs)
    return [numpy.array(ys) for i in range(1, maxSize + 1) for ys in combinations(xs, i)]


def printCard(card):
    return f'{printValue[card[1]]}{printSuit[card[0]]}'


def printCards(cards):
    cards = numpy.array(cards).T
    return ', '.join([printCard(card) for card in cards])


def numberOfCards(cards, category):
    return numpy.sum(cards[category])


def getCards(cards, category):
    return numpy.where(cards[category] == 1)


def getTrumps(cards, trumps):
    return numpy.where(cards[trumps] == 1)[0][0]

