# Durak

ToDo:

- Represent actions as matrices? So applying them just means adding them to our current state?

- Add a 'belief state' aspect into a player's state? Where they keep track of which cards an opponent has a
particular card? e.g. 1 if they definitely have it, 0 if they definitely don't, or -1 (or 1/2 or -infinity) if we
have no idea? Will involve changing the overwritable slot to an unbounded queue - every time an update takes place
a player will need to update their beliefs of other people's cards.

- Experiment with scoring functions. One idea: once out of cards, player's score is number of cards held by all other
players, with loser's score being negative the number of cards they had left. Another: score is 1 for anyone who
didn't lose, with -1 for the loser.

- Possible simplifications:
  - Strict turn-taking - no race to see whose action is accepted
  - One vs one (or one vs random)
