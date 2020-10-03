DEFAULT_ENV_PARAMS = {
    'SawyerPush-v0':{
        'n_cycles':10,
        'n_batches':5,
        'n_test_rollouts':50,
        'batch_size':64,
        'rollout_batch_size':1
    },
    # 'SawyerReachXYZEnv-v1':{
    #     'n_cycles':5,
    #     'n_batches':2,
    #     'n_test_rollouts':50,
    #     'batch_size':64
    # },
    'FetchReach-v1': {
        'n_cycles': 10,  
        'n_test_rollouts': 20,
        'n_batches': 2, 
        'batch_size': 64,
    },
    # 'FetchPush-v1': {
    #     'n_cycles': 10,  
    #     'n_test_rollouts': 20,
    #     'n_batches': 10, 
    #     'batch_size': 256,
    # },
}


DEFAULT_PARAMS = {  
    # env
    'max_u': 1.,  # max absolute value of actions on different coordinates
    # ddpg
    'layers': 3,  # number of layers in the critic/actor networks
    'hidden': 256,  # number of neurons in each hidden layers
    'Q_lr': 0.001,  # critic learning rate
    'pi_lr': 0.001,  # actor learning rate
    'polyak': 0.95,  # polyak averaging coefficient
    'action_l2': 1.0,  # quadratic penalty on actions (before rescaling by max_u)
    'clip_obs': 200.,
    'scope': 'ddpg',  # can be tweaked for testing
    'relative_goals': False,
    'clip_pos_returns': True,
    'clip_return': True,
    # buffer
    'buffer_size': int(1E6),  # for experience replay
    'sampler': 'random',

    # training
    'n_cycles': 50,  # per epoch
    'rollout_batch_size': 2,  # per mpi thread
    'n_batches': 40,  # training batches per cycle
    'batch_size': 1024,  #258 per mpi thread, measured in transitions and reduced to even multiple of chunk_length.
    'n_test_rollouts': 10,  # number of test rollouts per epoch, each consists of rollout_batch_size rollouts
    'test_with_polyak': False,  # run test episodes with the target network
    # playing 
    'play_episodes':1, # number of running test episodes
    # saving
    'policy_save_interval': 10,
    # exploration
    'random_eps': 0.3,  # percentage of time a random action is taken
    'noise_eps': 0.2,  # std of gaussian noise added to not-completely-random actions as a percentage of max_u
    # HER
    'replay_strategy': 'future',  # supported modes: future, none
    'replay_k': 4,  # number of additional goals used for replay, only used if off_policy_data=future
    # normalization
    'norm_eps': 1e-4,  # epsilon used for observation normalization
    'norm_clip': 5,  # normalized observations are cropped to this values

    # random init episode
    'random_init':100, # for dynamic n-step, this should be bigger

    # n step hindsight experience
    'n_step':3,
    'use_nstep':False,

    # lambda n-step
    'use_lambda_nstep':False,
    'lamb':0.7,

    # dynamic n-step
    'use_dynamic_nstep':True, # if true then use_n_step=False
    'alpha':0.5,
    'dynamic_batchsize':512,  # warm up the dynamic model
    'dynamic_init':500,

    # if do not use her
    'no_her':False    # no her, will be used for DDPG and n-step DDPG
}