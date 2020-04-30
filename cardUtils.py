import numpy

printSuit = ['S', 'C', 'H', 'D']
printValue = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']


def length(cards):
    return cards[0].size


def printCard(card):
    return f'{printValue[card[1]]}{printSuit[card[0]]}'


def printCards(cards):
    cards = numpy.array(cards).T
    return ', '.join([printCard(card) for card in cards])


def numberOfCards(state, category):
    return numpy.sum(state[category])

