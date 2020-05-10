import dqn
from environment import DurakEnvironment

numberOfPlayers = 4
minCards = 6
maxAttacks = 5

def main():
    train_durak = DurakEnvironment(numberOfPlayers, minCards, maxAttacks)
    eval_durak = DurakEnvironment(numberOfPlayers, minCards, maxAttacks)
    dqn.train(train_durak, eval_durak)

    # checkpoint = dqn.loadLatestAgent(eval_durak)
    # dqn.samplePolicy(eval_durak, checkpoint.agent.policy)

main()
