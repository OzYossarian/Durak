# Durak

ToDo:

- Add a 'belief state' aspect into a player's state? Where they keep track of which cards an opponent has a
particular card? e.g. 1 if they definitely have it, 0 if they definitely don't, or 1/2 if we
have no idea?

- Experiment with scoring functions. One idea: once out of cards, player's score is number of cards held by all other
players, with loser's score being negative the number of cards they had left. Another: score is 1 for anyone who
didn't lose, with -1 for the loser. The latter is more in keeping with Durak spirit - 'no winner, only a loser'.

- Could make splitter independent of durak environment by actually using the 'observation' to figure out the
action mask. Currently the would-be-defender stuff is the only bit that needs more than what's listed in the
observation to be determined. Possible solution; include in the observation a constant matrix noting how many
cards the would be defender has left. Then set this constant to 0 before passing the observation on to the
network.

- The change above would mean we could implement the evaluation part of the training loop without using
checkpoints, but am still not sure that the checkpoint.restore stuff is actually restoring a trained policy.
