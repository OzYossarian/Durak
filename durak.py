import dqn
from environment import DurakEnvironment
from game import Game

numberOfPlayers = 4
minCards = 6
maxAttacks = 5

def playWithoutAgent():
    game = Game(4, 6, 5)
    game.initialiseState()
    game.play()

def train():
    train_durak = DurakEnvironment(numberOfPlayers, minCards, maxAttacks)
    eval_durak = DurakEnvironment(numberOfPlayers, minCards, maxAttacks)
    dqn.train(train_durak, eval_durak)

    # checkpoint = dqn.loadLatestAgent(eval_durak)
    # dqn.samplePolicy(eval_durak, checkpoint.agent.policy)

playWithoutAgent()
# train()
