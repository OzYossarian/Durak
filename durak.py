import threading

from game import Game
from player import Player
from synchronisation import AndBarrier


def main():
    numberOfPlayers = 4
    minCards = 6
    maxAttacks = 5
    game = Game(numberOfPlayers, minCards, maxAttacks)

    game.play()


main()
