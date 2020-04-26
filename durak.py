import threading

from game import Game
from player import Player
from synchronisation import AndBarrier


def main():
    numberOfPlayers = 4
    minCards = 6
    maxAttacks = 5
    players = [Player(i, maxAttacks) for i in range(numberOfPlayers)]
    game = Game(players, minCards, maxAttacks)

    game.play()


main()
