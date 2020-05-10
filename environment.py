import numpy
import tensorflow as tf
import tf_agents.trajectories.time_step as time_step
from tf_agents.environments import py_environment
from tf_agents.specs import array_spec

import observables
from game import Game


class DurakEnvironment(py_environment.PyEnvironment):
    def __init__(self, numberOfPlayers, minCards, maxAttacks):
        super().__init__()

        self.game = Game(numberOfPlayers, minCards, maxAttacks)
        self.player = self.game.players[0]

        minObservation = numpy.zeros((8, 4, 13), dtype=int)
        maxObservation = numpy.ones((8, 4, 13), dtype=int)
        maxObservation[[6, 7]] = numpy.full((2, 4, 13), self.game.numberOfPlayers - 1, dtype=int)

        self._observation_spec = array_spec.BoundedArraySpec(
            shape=(8, 4, 13), dtype=int, minimum=minObservation, maximum=maxObservation, name='observation')

        self._action_spec = array_spec.BoundedArraySpec(
            shape=(), dtype=int, minimum=0, maximum=self.game.masker.totalActions - 1, name='action')

        # ToDo - hyperparameters
        self.transitionDiscount = 0.9
        self.episodeEnded = False

    def action_spec(self):
        return self._action_spec

    def observation_spec(self):
        return self._observation_spec

    def observation_and_action_constraint_splitter(self, observation):
        actionMask = self.player.getActionMask(observation.numpy()[0]) \
            if not self.game.gameOver \
            else self.game.masker.blankMask()
        maskShape = [1, self.game.masker.totalActions]
        actionMask = tf.reshape(tf.convert_to_tensor(actionMask), maskShape)

        playerObservation = observables.playerObservation(observation.numpy()[0])
        observationShape = [1, 8, 4, 13]
        playerObservation = tf.reshape(tf.convert_to_tensor(playerObservation), observationShape)

        return playerObservation, actionMask

    def _reset(self):
        self.game.initialiseState()
        self.episodeEnded = False

        # Fast forward to the agent's first turn
        while self.game.activePlayer != self.player.name:
            self.game.step()

        observation = self.game.observation(self.player.name)
        return time_step.restart(observation)

    def _step(self, action):
        if self.episodeEnded:
            return self.reset()

        self.game.updateState(action)

        while self.game.activePlayer != self.player.name and not self.game.gameOver:
            self.game.step()

        observation = self.game.observation(self.player.name)

        if self.game.gameOver:
            print('Game over: terminating...')
            self._episode_ended = True
            reward = self._calculateReward()
            # Don't bother calculating valid actions; say they're all invalid.
            return time_step.termination(observation, reward)
        else:
            return time_step.transition(observation, reward=0, discount=self.transitionDiscount)

    def _calculateReward(self):
        assert len(self.game.playersNotOut) == 1
        return -100 if self.game.playersNotOut[0] == self.player.name else 100
