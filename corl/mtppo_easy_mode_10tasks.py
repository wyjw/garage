# flake8: noqa
#!/usr/bin/env python3
"""
This is an example to train a multi env task with PPO algorithm.
"""

import gym
import tensorflow as tf
import numpy as np

from garage.envs import normalize
from garage.envs.env_spec import EnvSpec
from garage.experiment import LocalRunner, run_experiment
from garage.np.baselines import LinearFeatureBaseline
from garage.sampler.utils import mt_rollout
from garage.tf.algos import PPO
from garage.tf.baselines import GaussianMLPBaseline
from garage.tf.envs import TfEnv
from garage.tf.policies import GaussianMLPPolicy
from garage.tf.samplers import MultiEnvironmentVectorizedSampler2
from multiworld.envs.mujoco.sawyer_xyz.sawyer_reach_push_pick_place_6dof import SawyerReachPushPickPlace6DOFEnv


EXP_PREFIX = 'corl_easy_mtppo_ten_task'
def make_envs(env_names):
    return [TfEnv(normalize(gym.make(env_name))) for env_name in env_names]


def run_task(*_):
    with LocalRunner() as runner:

        # goal_low = np.array((-0.1, 0.8, 0.02))
        # goal_high = np.array((0.1, 0.9, 0.02))
        # goals = np.random.uniform(low=goal_low, high=goal_high, size=(4, len(goal_low))).tolist()
        # print('constructing envs')
        # envs = [
        #     TfEnv(SawyerReachPushPickPlace6DOFEnv(
        #         tasks=[{'goal': np.array(g),  'obj_init_pos': np.array([0, 0.6, 0.02]), 'obj_init_angle': 0.3, 'type':'push'}],
        #         random_init=False,
        #         if_render=False,))
        #     for g in goals
        # ]

        from corl.env_list import EASY_MODE_DICT, EASY_MODE_ARGS_KWARGS

        task_env_cls_dict = EASY_MODE_DICT
        task_args_kwargs = EASY_MODE_ARGS_KWARGS
        assert len(task_env_cls_dict.keys()) == len(task_args_kwargs.keys())
        for k in task_env_cls_dict.keys():
            assert k in task_args_kwargs

        task_envs = []
        task_names = []
        for task, env_cls in task_env_cls_dict.items():
            task_args = task_args_kwargs[task]['args']
            task_kwargs = task_args_kwargs[task]['kwargs']
            task_envs.append(TfEnv(env_cls(*task_args, **task_kwargs)))
            task_names.append(task)

        policy = GaussianMLPPolicy(
            env_spec=task_envs[0].spec,
            task_dim=len(task_envs),
            hidden_sizes=(200, 100),
            hidden_nonlinearity=tf.nn.tanh,
            output_nonlinearity=None,
            adaptive_std=True,
            init_std=2.,
        )

        # baseline = GaussianMLPBaseline(
        #     env_spec=task_envs[0].spec,
        #     task_dim=len(task_envs),
        #     regressor_args=dict(
        #         hidden_sizes=(200, 100),
        #         use_trust_region=True,
        #     ),
        # )

        baseline = LinearFeatureBaseline(env_spec=task_envs[0].spec)

        # NOTE: make sure when setting entropy_method to 'max', set
        # center_adv to False and turn off policy gradient. See
        # tf.algos.NPO for detailed documentation.
        algo = PPO(
            env_spec=task_envs[0].spec,
            task_dim=len(task_envs),
            policy=policy,
            baseline=baseline,
            max_path_length=150,
            discount=0.99,
            gae_lambda=1,
            lr_clip_range=0.1,
            optimizer_args=dict(
                batch_size=32,
                max_epochs=10,
            ),
            stop_entropy_gradient=False,
            entropy_method='regularized',
            policy_ent_coeff=2e-3,
            center_adv=True,
        )

        runner.setup(algo, task_envs, sampler_cls=MultiEnvironmentVectorizedSampler2)

        runner.train(n_epochs=int(1e7), batch_size=4096 * len(task_envs), plot=False)

run_experiment(run_task, exp_prefix=EXP_PREFIX, seed=1, n_parallel=1)
# with tf.Session() as sess:
#     mt_rollout('src/data/local/ppo-push-multi-task/ppo_push_multi_task_2019_06_26_17_56_37_0001', 199, animated=True)
