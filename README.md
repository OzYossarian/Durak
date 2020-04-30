# Durak

ToDo:

- Represent actions as matrices? So applying them just means adding them to our current state?
NOPE! Need a more efficient representation, because tf-agent works by indexing all possible actions.
Note there are six action types - attack, join attack, bounce, defend, concede, and decline to attack.

1. 'attack' - we can perform an initial attack with at most four cards. Let nCk denote 'n choose k'.
There are 13C1 * 4C1 one-card attacks. There are 13C1 * 4C2 2-card attacks, since any 2-card attack must consist of
choosing two cards of the same suit. Similarly there are 13C1 * 4C3 3-card attacks and 13C1 * 4C4 4-card attacks.
In all, there are (13 * 4) + (13 * 6) + (13 * 4) + (13 * 1) = 52 + 78 + 52 + 13 = 195 initial attack actions.

2. 'join attack' - all we can do here is attack with one card. So there are 52 actions.

3. 'bounce' - we can bounce with up to three cards, all of which must be the same suit. So there are 13C1 * 4C1
1-card bounces, 13C1 * 4C2 2-card bounces and 13C1 * 4C3 3-card attacks. So in total, 52 + 78 + 52 = 182 bounces.

4. 'defence' - a defence always consists of two cards; the one we're playing and the open attack that we're closing.
For ease of encoding we just say there are 52 * 52 = 2704 defences, but a few hundred or so are never valid.

5. 'concede' - can now change rules back to O.G. rules! We can prevent the attacker from attacking with more cards
than the defender has, so there will no longer be a situation where the defender chooses which cards to pick up.
So there's just one action.

6. 'decline to attack' - again, no choice involved, just one action.

- Add a 'belief state' aspect into a player's state? Where they keep track of which cards an opponent has a
particular card? e.g. 1 if they definitely have it, 0 if they definitely don't, or 1/2 if we
have no idea?

- Experiment with scoring functions. One idea: once out of cards, player's score is number of cards held by all other
players, with loser's score being negative the number of cards they had left. Another: score is 1 for anyone who
didn't lose, with -1 for the loser. The latter is more in keeping with Durak spirit - 'no winner, only a loser'.

- Possible simplifications:

Scribblings:

- How to handle situation where agent tries to perform action but action is rejected? Is it enough to just return
a reward of 0 (as usual)? Or do we need to say "the action was rejected, don't learn anything from this" somehow?
