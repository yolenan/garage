"""A regression test for automatic benchmarking garage-TensorFlow-HER."""
import tensorflow as tf

from garage import wrap_experiment
from garage.envs import GymEnv, normalize
from garage.experiment import deterministic
from garage.np.exploration_policies import AddOrnsteinUhlenbeckNoise
from garage.replay_buffer import HERReplayBuffer
from garage.tf.algos import DDPG
from garage.tf.policies import ContinuousMLPPolicy
from garage.tf.q_functions import ContinuousMLPQFunction
from garage.trainer import TFTrainer

hyper_parameters = {
    'policy_lr': 1e-3,
    'qf_lr': 1e-3,
    'policy_hidden_sizes': [256, 256, 256],
    'qf_hidden_sizes': [256, 256, 256],
    'n_epochs': 50,
    'steps_per_epoch': 20,
    'n_exploration_steps': 100,
    'n_train_steps': 40,
    'discount': 0.9,
    'tau': 0.05,
    'replay_buffer_size': int(1e6),
    'sigma': 0.2,
}


@wrap_experiment
def her_garage_tf(ctxt, env_id, seed):
    """Create garage TensorFlow HER model and training.

    Args:
        ctxt (ExperimentContext): The experiment configuration used by
            :class:`~Trainer` to create the :class:`~Snapshotter`.
        env_id (str): Environment id of the task.
        seed (int): Random positive integer for the trial.

    """
    deterministic.set_seed(seed)

    with TFTrainer(ctxt) as trainer:
        env = normalize(GymEnv(env_id))

        policy = ContinuousMLPPolicy(
            env_spec=env.spec,
            hidden_sizes=hyper_parameters['policy_hidden_sizes'],
            hidden_nonlinearity=tf.nn.relu,
            output_nonlinearity=tf.nn.tanh,
        )

        exploration_policy = AddOrnsteinUhlenbeckNoise(
            env_spec=env.spec, policy=policy, sigma=hyper_parameters['sigma'])

        qf = ContinuousMLPQFunction(
            env_spec=env.spec,
            hidden_sizes=hyper_parameters['qf_hidden_sizes'],
            hidden_nonlinearity=tf.nn.relu,
        )

        replay_buffer = HERReplayBuffer(
            env_spec=env.spec,
            capacity_in_transitions=hyper_parameters['replay_buffer_size'],
            replay_k=4,
            reward_fn=env.compute_reward,
        )

        algo = DDPG(
            env_spec=env.spec,
            policy=policy,
            qf=qf,
            replay_buffer=replay_buffer,
            steps_per_epoch=hyper_parameters['steps_per_epoch'],
            policy_lr=hyper_parameters['policy_lr'],
            qf_lr=hyper_parameters['qf_lr'],
            target_update_tau=hyper_parameters['tau'],
            n_train_steps=hyper_parameters['n_train_steps'],
            discount=hyper_parameters['discount'],
            exploration_policy=exploration_policy,
            policy_optimizer=tf.compat.v1.train.AdamOptimizer,
            qf_optimizer=tf.compat.v1.train.AdamOptimizer,
            buffer_batch_size=256,
        )

        trainer.setup(algo, env)
        trainer.train(n_epochs=hyper_parameters['n_epochs'],
                      batch_size=hyper_parameters['n_exploration_steps'])
