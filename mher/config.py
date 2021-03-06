import os

import gym
import numpy as np

from mher.algos import DDPG, SAC
from mher.algos.util import dims_to_shapes
from mher.buffers.replay_buffer import ReplayBuffer
from mher.common import logger
from mher.common.monitor import Monitor
from mher.default_cfg import DEFAULT_ENV_PARAMS, DEFAULT_PARAMS
from mher.envs.env_utils import (cached_make_env, get_rewardfun,
                                 simple_goal_subtract)
from mher.envs.wrappers.wrapper_utils import recurse_attribute
from mher.samplers import *
from mher.buffers import *


def log_params(params):
    for key in sorted(params.keys()):
        logger.info('{}: {}'.format(key, params[key]))


def process_params(env, tmp_env, rank, args, extra_args):
    params = DEFAULT_PARAMS
    env_name = env.spec.id
    params['env_name'] = env_name
    if env_name in DEFAULT_ENV_PARAMS:
        params.update(DEFAULT_ENV_PARAMS[env_name])  # merge env-specific parameters in config
    
    params['rollout_batch_size'] = env.num_envs
    params['random_init'] = args.random_init
    params['play_episodes'] = args.play_episodes
    params.update(extra_args)
    params = prepare_params(tmp_env, params)
    
    if rank == 0:
        log_params(params)
    return params

# get policy params
def prepare_params(tmp_env, params):
    # default max episode steps
    params['reward_fun'] = get_rewardfun(params, tmp_env)
    # algo params
    algo_params = dict()
    max_episode_steps = recurse_attribute(tmp_env, '_max_episode_steps')
    assert max_episode_steps is not None, 'Env object should have _max_episode_steps attribute!'
    params['T'] = max_episode_steps
    params['max_u'] = np.array(params['max_u']) if isinstance(params['max_u'], list) else params['max_u']
    params['gamma'] = 1. - 1. / params['T']
    for name in ['hidden', 'layers', 'polyak', 'Q_lr', 'pi_lr', 'norm_eps', 'norm_clip', 'max_u',
                 'action_l2', 'clip_obs', 'relative_goals', 'clip_pos_returns', 'clip_return']:
        algo_params[name] = params[name]
        # params['_' + name] = params[name]
        del params[name]
    algo_params['scope'] = params['algo']
    
    params['algo_params'] = algo_params
    return params

def configure_algorithm(dims, params, buffer):
    algo_params = params['algo_params']
    if 'nstep' in params['sampler']:
        vloss_type = 'tf_gamma'
    # elif 'nstep' in params['sampler'] and 'her' in params['sampler']:
    #     vloss_type = 'target'
    else:
        vloss_type = 'normal'
    if 'priority' in params['sampler']:
        priority = True
    else:
        priority = False
    algo_params.update({'input_dims': dims.copy(),  
                        'buffer':buffer,
                        'clip_pos_returns': algo_params['clip_pos_returns'], 
                        'clip_return': (1. / (1. - params['gamma'])) 
                                        if algo_params['clip_return'] else np.inf, 
                        'subtract_goals': simple_goal_subtract,
                        'gamma': params['gamma'],
                        'vloss_type': vloss_type,
                        'priority': priority
                        })
    if params['algo'] == 'sac':
        algo_params['sac_alpha'] = params['sac_alpha']
        policy = SAC(**algo_params)
    else:
        policy = DDPG(**algo_params) 
    return policy

def configure_dims(env, params):
    env.reset()
    obs, _, _, info = env.step(env.action_space.sample())
    dims = {
        'o': obs['observation'].shape[0],
        'u': env.action_space.shape[0],
        'g': obs['desired_goal'].shape[0]
    }
    for key, value in info.items():
        value = np.array(value)
        if value.ndim == 0:
            value = value.reshape(1)
        dims['info_{}'.format(key)] = value.shape[0]
    return dims

def configure_rollout(params):
    rollout_params = {
        'exploit': False,
        'use_target_net': False,
        'compute_Q': False,
    }
    eval_params = {
        'exploit': True,
        'use_target_net': params['test_with_polyak'],
        'compute_Q': True,
    }
    for name in ['T', 'rollout_batch_size', 'gamma', 'noise_eps', 'random_eps']:
        rollout_params[name] = params[name]
        eval_params[name] = params[name]
    return rollout_params, eval_params

def configure_buffer(dims, params, sampler):
    input_shapes = dims_to_shapes(dims)
    buffer_shapes = {key: (params['T'] if key != 'o' else params['T'] + 1, *input_shapes[key]) for key, val in input_shapes.items()}
    buffer_shapes['g'] = (buffer_shapes['g'][0], dims['g'])
    buffer_shapes['ag'] = (params['T'] + 1, dims['g'])
    buffer_size = (params['buffer_size'] // params['rollout_batch_size']) * params['rollout_batch_size'] # buffer_size % rollout_batch_size should be zero
    if 'priority' in params['sampler']:
        Buffer = PrioritizedReplayBuffer
    else:
        Buffer = ReplayBuffer
    return Buffer(buffer_shapes, buffer_size, params['T'], sampler)

def configure_sampler(dims, params):
    if params['sampler'] == 'random':
         sampler = RandomSampler(params['T'], params['reward_fun'], params['batch_size'])
    elif params['sampler'].startswith('her'): # valid: her_future, her_random, her_final, her_episode
        strategy = params['sampler'].replace('her_', '')
        sampler = HER_Sampler(params['T'], params['reward_fun'], params['batch_size'], 
                            params['relabel_p'], strategy)
    elif params['sampler'] == 'nstep':
        sampler = Nstep_Sampler(params['T'], params['reward_fun'], params['batch_size'], 
                                params['relabel_p'], params['nstep'], params['gamma'])
    elif params['sampler'].startswith('nstep_her'):
        strategy = params['sampler'].replace('nstep_her_', '')
        sampler = Nstep_HER_Sampler(params['T'], params['reward_fun'], params['batch_size'], 
                                    params['relabel_p'], params['nstep'], params['gamma'], strategy)
    elif params['sampler'] == 'priority':
        sampler = PrioritizedSampler(params['T'], params['reward_fun'], params['batch_size'],
                                params['buffer_size'], params['alpah'], params['beta'], params['eps'])
    elif params['sampler'].startswith('priority_her'):
        strategy = params['sampler'].replace('priority_her_', '')
        sampler = PrioritizedHERSampler(params['T'], params['reward_fun'], params['batch_size'],
                                params['buffer_size'], params['alpah'], params['beta'], params['eps'],
                                params['relabel_p'], strategy)
    else:
        raise NotImplementedError
    return sampler

def configure_epoch(num_epoch, params):
    if num_epoch:  # prefer to use num_poch
        n_epochs = num_epoch
    else:
        n_epochs = params['total_timesteps'] // params['n_cycles'] // params['T'] // params['rollout_batch_size']
    return n_epochs
