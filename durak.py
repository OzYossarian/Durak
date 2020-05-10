import dqn
from environment import DurakEnvironment

numberOfPlayers = 4
minCards = 6
maxAttacks = 5

# ToDo: pick a style - camelCase or the_other_case
def main():
    # train_durak = DurakEnvironment(numberOfPlayers, minCards, maxAttacks)
    eval_durak = DurakEnvironment(numberOfPlayers, minCards, maxAttacks)
    # train.train(train_durak, eval_durak)

    policy = dqn.loadLatestPolicy()
    dqn.samplePolicy(eval_durak, policy)

main()
