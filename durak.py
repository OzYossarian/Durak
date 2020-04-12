import threading

from game import Game
from player import Player


def main():
    numberOfPlayers = 4
    minCards = 6
    maxAttacks = 5
    game = Game(numberOfPlayers, minCards, maxAttacks)
    players = [Player(i, game) for i in range(numberOfPlayers)]

    threads = [threading.Thread(target=(lambda p: p.play()), args=(players[i],)) for i in range(numberOfPlayers)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()


main()
