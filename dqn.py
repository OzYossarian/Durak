import copy

import tensorflow as tf
from datetime import datetime

from tensorflow_core.python.training.checkpoint_management import CheckpointManager
from tf_agents.agents import DqnAgent
from tf_agents.drivers import dynamic_step_driver
from tf_agents.environments.wrappers import TimeLimit
from tf_agents.metrics import tf_metrics
from tf_agents.environments.tf_py_environment import TFPyEnvironment
from tf_agents.networks.q_network import QNetwork
from tf_agents.policies.policy_saver import PolicySaver
from tf_agents.replay_buffers.tf_uniform_replay_buffer import TFUniformReplayBuffer
from tf_agents.utils.common import element_wise_squared_loss, Checkpointer

tf.compat.v1.enable_v2_behavior()

# ToDo: hyperparameters!

num_iterations = 10

initial_collect_steps = 1000
collect_steps_per_iteration = 1
replay_buffer_max_length = 100000

batch_size = 64
learning_rate = 1e-3
log_interval = 10

num_eval_episodes = 1
eval_interval = 10

hidden_layers = 100
num_parallel_calls = 3
num_steps = 2
prefetch = 3

projectPath = '/Users/Teague/PycharmProjects/Durak'


def train(train_durak, eval_durak):
    train_env = TFPyEnvironment(TimeLimit(train_durak, duration=1000))
    eval_env = TFPyEnvironment(TimeLimit(eval_durak, duration=1000))

    train_agent = createAgent(train_durak, train_env)
    eval_agent = createAgent(eval_durak, eval_env)

    eval_checkpoint_save = tf.train.Checkpoint(policy=train_agent.policy)
    manager = CheckpointManager(eval_checkpoint_save, f'{projectPath}/Policies', max_to_keep=1)
    eval_checkpoint_load = tf.train.Checkpoint(policy=eval_agent.policy)
    checkpoints = [manager, eval_checkpoint_load]

    iterator, replay_observer = setupReplayBuffer(train_agent, train_env)

    trainAgent(train_agent, iterator, replay_observer, train_env, eval_env, checkpoints)


def trainAgent(agent, iterator, replay_observer, train_env, eval_env, checkpoints):
    driver, train_metrics = setupTraining(agent, replay_observer, train_env)
    episode_len = []
    final_time_step, policy_state = driver.run()

    for i in range(num_iterations):
        final_time_step, _ = driver.run(final_time_step, policy_state)

        experience, _ = next(iterator)
        train_loss = agent.train(experience=experience)
        step = agent.train_step_counter.numpy()

        if step % log_interval == 0:
            logProgress(episode_len, step, train_loss, train_metrics)

        if step % eval_interval == 0:
            evaluateProgress(step, eval_env, checkpoints)

    # ToDo: plot progress?
    saveAgent(agent)


# ToDo - there is almost certainly a better way to do this. Need to ensure that the evaluation policy
#  is using the action mask from the evaluation environment, not the training environment. Currently not
#  actually sure that this is restoring the policy from the trained agent at all. Might well just be
#  using the policy from the eval_agent (defined above). Investigate (somehow!).
def evaluateProgress(step, eval_env, checkpoints):
    path = checkpoints[0].save()
    checkpoints[1].restore(path)
    avg_return = compute_avg_return(eval_env, checkpoints[1].policy, num_eval_episodes)
    print(f'step = {step}: Average Return = {avg_return}')


def saveAgent(agent):
    checkpoint = tf.train.Checkpoint(agent=agent)
    now = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    checkpointPath = f'{projectPath}/Agents/{now}_'
    checkpoint.save(checkpointPath)
    print('Saved agent!')


def logProgress(episode_len, step, train_loss, train_metrics):
    print(f'step = {step}: loss = {train_loss.loss}')
    episode_len.append(train_metrics[3].result().numpy())
    print(f'Episodes: {train_metrics[0].result().numpy()}')
    print(f'Environment steps: {train_metrics[1].result().numpy()}')
    print(f'Average return: {train_metrics[2].result().numpy()}')
    print(f'Average episode length: {train_metrics[3].result().numpy()}')


def setupTraining(agent, replay_observer, train_env):
    train_metrics = [
        tf_metrics.NumberOfEpisodes(),
        tf_metrics.EnvironmentSteps(),
        tf_metrics.AverageReturnMetric(),
        tf_metrics.AverageEpisodeLengthMetric(),
    ]

    driver = dynamic_step_driver.DynamicStepDriver(
        train_env,
        agent.collect_policy,
        observers=replay_observer + train_metrics,
        num_steps=1)

    return driver, train_metrics


def setupReplayBuffer(agent, train_env):
    replay_buffer = TFUniformReplayBuffer(
        data_spec=agent.collect_data_spec,
        batch_size=train_env.batch_size,
        max_length=replay_buffer_max_length)

    replay_observer = [replay_buffer.add_batch]

    dataset = replay_buffer.as_dataset(
        num_parallel_calls=num_parallel_calls,
        sample_batch_size=batch_size,
        num_steps=num_steps).prefetch(prefetch)

    iterator = iter(dataset)
    return iterator, replay_observer


def createAgent(durak_env, tf_env):
    q_net = QNetwork(
        tf_env.observation_spec(),
        tf_env.action_spec(),
        fc_layer_params=(hidden_layers,))

    optimizer = tf.compat.v1.train.AdamOptimizer(learning_rate=learning_rate)
    train_step_counter = tf.Variable(0)

    agent = DqnAgent(
        tf_env.time_step_spec(),
        tf_env.action_spec(),
        q_network=q_net,
        optimizer=optimizer,
        observation_and_action_constraint_splitter=durak_env.observation_and_action_constraint_splitter,
        td_errors_loss_fn=element_wise_squared_loss,
        train_step_counter=train_step_counter)

    agent.initialize()
    return agent


def compute_avg_return(environment, policy, num_episodes=10):
    total_return = 0.0
    for _ in range(num_episodes):

        time_step = environment.reset()
        episode_return = 0.0

        while not time_step.is_last():
            action_step = policy.action(time_step)
            time_step = environment.step(action_step.action)
            episode_return += time_step.reward
        total_return += episode_return

    avg_return = total_return / num_episodes
    return avg_return.numpy()[0]


# ToDo: similar to a comment above - currently not actually sure that this is restoring the policy
#  from the trained agent at all. Might well just be using the policy from the agent created here.
def loadLatestAgent(durak_environment):
    tf_environment = TFPyEnvironment(TimeLimit(durak_environment, duration=1000))
    agent = createAgent(durak_environment, tf_environment)

    checkpoint = tf.train.Checkpoint(agent=agent)
    directory = f'{projectPath}/Agents'
    status = checkpoint.restore(tf.train.latest_checkpoint(directory))

    # ToDo: this raises a couple of warnings - check whether they're ignorable.
    # status.assert_consumed()

    return checkpoint


def samplePolicy(eval_durak, policy):
    environment = TFPyEnvironment(TimeLimit(eval_durak, duration=1000))
    compute_avg_return(environment, policy)
