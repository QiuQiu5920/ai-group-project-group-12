import pickle

import numpy as np
import torch
import torch.optim as optim

from total_util import dqn_step
from total_util import QNet_dqn
from total_util import Memory
from total_util import get_env_info
from total_util import check_path
from total_util import device, FLOAT, LONG
from total_util import ZFilter
from NTEnv import NTEnv


class DQN:
    def __init__(self,
                 env_id,
                 render=False,
                 num_process=1,
                 memory_size=1000000,
                 explore_size=10000,
                 step_per_iter=3000,
                 lr_q=1e-3,
                 gamma=0.99,
                 batch_size=128,
                 min_update_step=1000,
                 epsilon=0.90,
                 update_target_gap=50,
                 seed=1,
                 model_path=None
                 ):
        self.env_id = env_id
        self.render = render
        self.num_process = num_process
        self.memory = Memory(size=memory_size)
        self.explore_size = explore_size
        self.step_per_iter = step_per_iter
        self.lr_q = lr_q
        self.gamma = gamma
        self.batch_size = batch_size
        self.min_update_step = min_update_step
        self.update_target_gap = update_target_gap
        self.epsilon = epsilon
        self.seed = seed
        self.model_path = model_path

        self._init_model()

    def _init_model(self):
        """init model from parameters"""
        self.env, env_continuous, num_states, self.num_actions = get_env_info(
            self.env_id)
        assert not env_continuous, "DQN is only applicable to discontinuous environment !!!!"
        self.env = NTEnv()
        env_continuous = False
        obs = self.env.reset()
        num_states = obs.shape[0]
        self.num_actions = 2
        # seeding
        np.random.seed(self.seed)
        torch.manual_seed(self.seed)
        # self.env.seed(self.seed)

        # initialize networks
        self.value_net = QNet_dqn(num_states, self.num_actions).to(device)
        self.value_net_target = QNet_dqn(
            num_states, self.num_actions).to(device)

        self.running_state = ZFilter((num_states,), clip=5)

        # load model if necessary
        if self.model_path:
            print("Loading Saved Model {}_dqn.p".format(self.env_id))
            self.value_net, self.running_state = pickle.load(
                open('{}/{}_dqn.p'.format(self.model_path, self.env_id), "rb"))

        self.value_net_target.load_state_dict(self.value_net.state_dict())

        self.optimizer = optim.Adam(self.value_net.parameters(), lr=self.lr_q)

    def choose_action(self, state):
        state = FLOAT(state).unsqueeze(0).to(device)
        if np.random.uniform() <= self.epsilon:
            with torch.no_grad():
                action = self.value_net.get_action(state)
            action = action.cpu().numpy()[0]
        else:  # choose action greedy
            action = np.random.randint(0, self.num_actions)
        return action

    def eval(self, i_iter, render=False):
        """evaluate model"""
        state = self.env.reset()
        test_reward = 0
        while True:
            if render:
                self.env.render()
            # state = self.running_state(state)
            action = self.choose_action(state)
            state, reward, done, _ = self.env.step(action)

            test_reward += reward
            if done:
                break
        print(f"Iter: {i_iter}, test Reward: {test_reward}")
        self.env.close()

    def learn(self, writer, i_iter):
        """interact"""
        global_steps = (i_iter - 1) * self.step_per_iter
        log = dict()
        num_steps = 0
        num_episodes = 0
        total_reward = 0
        min_episode_reward = float('inf')
        max_episode_reward = float('-inf')

        while num_steps < self.step_per_iter:
            state = self.env.reset()
            # state = self.running_state(state)
            episode_reward = 0
            info = {}
            info['valued_cards'] = []
            info['card_pool'] = -1
            info['chip_pool'] = -1
            for t in range(10000):
                if self.render:
                    self.env.render()

                if global_steps < self.explore_size:  # explore
                    action = np.random.choice([0, 1])
                elif info['card_pool'] != -1:
                    if info['card_pool'] in info['valued_cards'] or \
                        info['card_pool'] <= info['chip_pool']:
                        action = 0
                        # action = self.choose_action(state)
                    else:
                        action = self.choose_action(state)
                else:  # choose according to target net
                    action = self.choose_action(state)

                next_state, reward, done, info = self.env.step(action)
                # next_state = self.running_state(next_state)
                mask = 0 if done else 1
                # ('state', 'action', 'reward', 'next_state', 'mask', 'log_prob')
                self.memory.push(state, action, reward, next_state, mask, None)

                episode_reward += reward
                global_steps += 1
                num_steps += 1

                if global_steps >= self.min_update_step:
                    batch = self.memory.sample(
                        self.batch_size)  # random sample batch
                    self.update(batch)

                if global_steps % self.update_target_gap == 0:
                    self.value_net_target.load_state_dict(
                        self.value_net.state_dict())

                if done or num_steps >= self.step_per_iter:
                    break

                state = next_state

            num_episodes += 1
            total_reward += episode_reward
            min_episode_reward = min(episode_reward, min_episode_reward)
            max_episode_reward = max(episode_reward, max_episode_reward)

        self.env.close()

        log['num_steps'] = num_steps
        log['num_episodes'] = num_episodes
        log['total_reward'] = total_reward
        log['avg_reward'] = total_reward / num_episodes
        log['max_episode_reward'] = max_episode_reward
        log['min_episode_reward'] = min_episode_reward

        print(f"Iter: {i_iter}, num steps: {log['num_steps']}, total reward: {log['total_reward']: .4f}, "
              f"min reward: {log['min_episode_reward']: .4f}, max reward: {log['max_episode_reward']: .4f}, "
              f"average reward: {log['avg_reward']: .4f}")

        # record reward information
        writer.add_scalar("total reward", log['total_reward'], i_iter)
        writer.add_scalar("average reward", log['avg_reward'], i_iter)
        writer.add_scalar("min reward", log['min_episode_reward'], i_iter)
        writer.add_scalar("max reward", log['max_episode_reward'], i_iter)
        writer.add_scalar("num steps", log['num_steps'], i_iter)

    def update(self, batch):
        batch_state = FLOAT(batch.state).to(device)
        batch_action = LONG(batch.action).to(device)
        batch_reward = FLOAT(batch.reward).to(device)
        batch_next_state = FLOAT(batch.next_state).to(device)
        batch_mask = FLOAT(batch.mask).to(device)

        alg_step_stats = dqn_step(self.value_net, self.optimizer, self.value_net_target, batch_state, batch_action,
                                  batch_reward, batch_next_state, batch_mask, self.gamma)

    def save(self, save_path):
        """save model"""
        check_path(save_path)
        pickle.dump((self.value_net, self.running_state),
                    open('{}/{}_dqn.p'.format(save_path, self.env_id), 'wb'))
