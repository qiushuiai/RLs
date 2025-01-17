#!/usr/bin/env python3
# encoding: utf-8

import numpy as np
import tensorflow as tf
import tensorflow_probability as tfp

from collections import namedtuple

from rls.utils.tf2_utils import (gaussian_clip_rsample,
                                 gaussian_likelihood_sum,
                                 gaussian_entropy)
from rls.algos.base.on_policy import On_Policy
from rls.utils.build_networks import ValueNetwork
from rls.utils.specs import OutputNetworkType

PG_Train_BatchExperiences = namedtuple('PG_Train_BatchExperiences', 'obs, action, discounted_reward')


class PG(On_Policy):
    def __init__(self,
                 envspec,

                 lr=5.0e-4,
                 epoch=5,
                 network_settings={
                     'actor_continuous': [32, 32],
                     'actor_discrete': [32, 32]
                 },
                 **kwargs):
        super().__init__(envspec=envspec, **kwargs)
        self.epoch = epoch
        if self.is_continuous:
            self.net = ValueNetwork(
                name='net',
                representation_net=self._representation_net,
                value_net_type=OutputNetworkType.ACTOR_MU_LOGSTD,
                value_net_kwargs=dict(output_shape=self.a_dim,
                                      network_settings=network_settings['actor_continuous'])
            )
        else:
            self.net = ValueNetwork(
                name='net',
                representation_net=self._representation_net,
                value_net_type=OutputNetworkType.ACTOR_DCT,
                value_net_kwargs=dict(output_shape=self.a_dim,
                                      network_settings=network_settings['actor_discrete'])
            )
        self.lr = self.init_lr(lr)
        self.optimizer = self.init_optimizer(self.lr)

        self.initialize_data_buffer(sample_data_type=PG_Train_BatchExperiences)

        self._worker_params_dict.update(self.net._policy_models)

        self._all_params_dict.update(self.net._all_models)
        self._all_params_dict.update(optimizer=self.optimizer)
        self._model_post_process()

    def choose_action(self, obs, evaluation=False):
        a, self.next_cell_state = self._get_action(obs, self.cell_state)
        a = a.numpy()
        return a

    @tf.function
    def _get_action(self, obs, cell_state):
        with tf.device(self.device):
            output, cell_state = self.net(obs, cell_state=cell_state)
            if self.is_continuous:
                mu, log_std = output
                sample_op, _ = gaussian_clip_rsample(mu, log_std)
            else:
                logits = output
                norm_dist = tfp.distributions.Categorical(logits=logits)
                sample_op = norm_dist.sample()
        return sample_op, cell_state

    def calculate_statistics(self):
        self.data.cal_dc_r(self.gamma, 0., normalize=True)

    def learn(self, **kwargs):
        self.train_step = kwargs.get('train_step')

        def _train(data, cell_state):
            for _ in range(self.epoch):
                loss, entropy = self.train(data, cell_state)
            summaries = dict([
                ['LOSS/loss', loss],
                ['Statistics/entropy', entropy]
            ])
            return summaries

        self._learn(function_dict={
            'calculate_statistics': self.calculate_statistics,
            'train_function': _train,
            'summary_dict': dict([['LEARNING_RATE/lr', self.lr(self.train_step)]])
        })

    @tf.function
    def train(self, BATCH, cell_state):
        with tf.device(self.device):
            with tf.GradientTape() as tape:
                output, cell_state = self.net(BATCH.obs, cell_state=cell_state)
                if self.is_continuous:
                    mu, log_std = output
                    log_act_prob = gaussian_likelihood_sum(BATCH.action, mu, log_std)
                    entropy = gaussian_entropy(log_std)
                else:
                    logits = output
                    logp_all = tf.nn.log_softmax(logits)
                    log_act_prob = tf.reduce_sum(tf.multiply(logp_all, BATCH.action), axis=1, keepdims=True)
                    entropy = -tf.reduce_mean(tf.reduce_sum(tf.exp(logp_all) * logp_all, axis=1, keepdims=True))
                loss = -tf.reduce_mean(log_act_prob * BATCH.discounted_reward)
            loss_grads = tape.gradient(loss, self.net.trainable_variables)
            self.optimizer.apply_gradients(
                zip(loss_grads, self.net.trainable_variables)
            )
            self.global_step.assign_add(1)
            return loss, entropy
