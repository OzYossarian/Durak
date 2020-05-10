import os

import tensorflow as tf
from datetime import datetime
from tf_agents.agents import DqnAgent
from tf_agents.drivers import dynamic_step_driver
from tf_agents.environments.wrappers import TimeLimit
from tf_agents.metrics import tf_metrics
from tf_agents.environments.tf_py_environment import TFPyEnvironment
from tf_agents.networks.q_network import QNetwork
from tf_agents.policies.policy_saver import PolicySaver
from tf_agents.replay_buffers.tf_uniform_replay_buffer import TFUniformReplayBuffer
from tf_agents.utils.common import element_wise_squared_loss

tf.compat.v1.enable_v2_behavior()

# ToDo: hyperparameters!

num_iterations = 1000

initial_collect_steps = 1000
collect_steps_per_iteration = 1
replay_buffer_max_length = 100000

batch_size = 64
learning_rate = 1e-3
log_interval = 100

num_eval_episodes = 1
eval_interval = 100

hidden_layers = 100
num_parallel_calls = 3
num_steps = 2
prefetch = 3

projectPath = '/Users/Teague/PycharmProjects/Durak'


def train(train_durak, eval_durak):
    train_env = TFPyEnvironment(TimeLimit(train_durak, duration=1000))
    eval_env = TFPyEnvironment(TimeLimit(eval_durak, duration=1000))

    agent = createAgent(train_durak, train_env)
    iterator, replay_observer = setupReplayBuffer(agent, train_env)

    trainAgent(agent, iterator, replay_observer, train_env)


def trainAgent(agent, iterator, replay_observer, train_env):
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

        # if step % eval_interval == 0:
        #     avg_return = compute_avg_return(eval_env, agent.policy, num_eval_episodes)
        #     print(f'step = {step}: Average Return = {avg_return}')

    # plt.plot(episode_len)
    # plt.show()

    saveAgent(agent)

    # checkpoint.restore(path).assert_consumed()


def saveAgent(agent):
    checkpoint = tf.train.Checkpoint(agent=agent)
    now = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    checkpointPath = f'{projectPath}/Checkpoints/{now}_Agent'
    checkpoint.save(checkpointPath)
    print('Saved agent!')

    PolicySaver(agent.policy).save(f'{projectPath}/Policies/{now}_Policy')
    print('Saved policy!')


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

def createAgent(train_durak, train_env):
    q_net = QNetwork(
        train_env.observation_spec(),
        train_env.action_spec(),
        fc_layer_params=(hidden_layers,))

    optimizer = tf.compat.v1.train.AdamOptimizer(learning_rate=learning_rate)
    train_step_counter = tf.Variable(0)

    agent = DqnAgent(
        train_env.time_step_spec(),
        train_env.action_spec(),
        q_network=q_net,
        optimizer=optimizer,
        observation_and_action_constraint_splitter=train_durak.observation_and_action_constraint_splitter,
        td_errors_loss_fn=element_wise_squared_loss,
        train_step_counter=train_step_counter)

    agent.initialize()
    return agent


# ToDo - currently this ignores action mask completely.
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


def loadLatestAgent(train_durak):
    train_env = TFPyEnvironment(TimeLimit(train_durak, duration=1000))
    agent = createAgent(train_durak, train_env)

    checkpoint = tf.train.Checkpoint(agent=agent)
    directory = f'{projectPath}/Checkpoints'
    status = checkpoint.restore(tf.train.latest_checkpoint(directory))
    status.assert_consumed()
    print('Loaded agent!')


def loadLatestPolicy():
    (root, directories, _) = next(os.walk(f'{projectPath}/Policies'))
    print(sorted(directories))
    latest = sorted(directories)[-1]
    policy = tf.saved_model.load(os.path.join(root, latest))
    return policy


def samplePolicy(eval_durak, policy):
    environment = TFPyEnvironment(TimeLimit(eval_durak, duration=1000))
    compute_avg_return(environment, policy)
