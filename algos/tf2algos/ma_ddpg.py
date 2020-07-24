import numpy as np
import tensorflow as tf
import rls
from algos.tf2algos.base.policy import Policy


class MADDPG(Policy):
    '''
    Multi-Agent Deep Deterministic Policy Gradient, https://arxiv.org/abs/1706.02275
    '''

    def __init__(self,
                 s_dim,
                 a_dim,
                 is_continuous,

                 ployak=0.995,
                 actor_lr=5.0e-4,
                 critic_lr=1.0e-3,
                 n=1,
                 i=0,
                 hidden_units={
                     'actor': [32, 32],
                     'q': [32, 32]
                 },
                 **kwargs):
        assert is_continuous, 'maddpg only support continuous action space'
        raise Exception('MA系列存在问题，还未修复')
        super().__init__(
            s_dim=s_dim,
            visual_sources=0,
            visual_resolution=0,
            a_dim=a_dim,
            is_continuous=is_continuous,
            **kwargs)
        self.n = n
        self.i = i
        self.ployak = ployak

        self.rnn_net = self._rnn_net(self.visual_net.hdim)

        # self.action_noise = rls.NormalActionNoise(mu=np.zeros(self.a_dim), sigma=1 * np.ones(self.a_dim))
        self.action_noise = rls.OrnsteinUhlenbeckActionNoise(mu=np.zeros(self.a_dim), sigma=0.2 * np.ones(self.a_dim))

        def _actor_net(): return rls.actor_dpg(self.s_dim, 0, self.a_dim, hidden_units['actor'])
        self.actor_net = _actor_net()
        self.actor_target_net = _actor_net()
        def _q_net(): return rls.critic_q_one((self.s_dim) * self.n, 0, (self.a_dim) * self.n, hidden_units['q'])
        self.q_net = _q_net()
        self.q_target_net = _q_net()
        self.update_target_net_weights(
            self.actor_target_net.weights + self.q_target_net.weights,
            self.actor_net.weights + self.q_net.weights
        )
        self.actor_lr, self.critic_lr = map(self.init_lr, [actor_lr, critic_lr])
        self.optimizer_actor, self.optimizer_critic = map(self.init_optimizer, [self.actor_lr, self.critic_lr])

        self.model_recorder(dict(
            actor=self.actor_net,
            q=self.q_net,
            optimizer_critic=self.optimizer_critic,
            optimizer_actor=self.optimizer_actor
        ))
        self.recorder.logger.info(self.action_noise)

    def show_logo(self):
        self.recorder.logger.info('''
　　ｘｘｘｘ　　　　ｘｘｘ　　　　　　　　　ｘｘ　　　　　　　　　ｘｘｘｘｘｘｘ　　　　　　　　ｘｘｘｘｘｘｘ　　　　　　　　ｘｘｘｘｘｘｘｘ　　　　　　　　ｘｘｘｘｘｘ　　　　　
　　　ｘｘｘ　　　　ｘｘ　　　　　　　　　ｘｘｘ　　　　　　　　　　　ｘ　　ｘｘｘ　　　　　　　　　ｘ　　ｘｘｘ　　　　　　　　　ｘｘ　　ｘｘ　　　　　　　ｘｘｘ　　ｘｘ　　　　　
　　　　ｘｘｘ　　ｘｘｘ　　　　　　　　　ｘｘｘ　　　　　　　　　　　ｘ　　　ｘｘ　　　　　　　　　ｘ　　　ｘｘ　　　　　　　　　ｘ　　　ｘｘｘ　　　　　　ｘｘ　　　　ｘ　　　　　
　　　　ｘｘｘ　　ｘｘｘ　　　　　　　　　ｘ　ｘｘ　　　　　　　　　　ｘ　　　ｘｘ　　　　　　　　　ｘ　　　ｘｘ　　　　　　　　　ｘ　　　ｘｘｘ　　　　　　ｘｘ　　　　　　　　　　
　　　　ｘｘｘｘ　ｘ　ｘ　　　　　　　　ｘｘ　ｘｘ　　　　　　　　　　ｘ　　　ｘｘｘ　　　　　　　　ｘ　　　ｘｘｘ　　　　　　　　ｘｘｘｘｘｘ　　　　　　　ｘ　　　ｘｘｘｘｘ　　　
　　　　ｘ　ｘｘｘｘ　ｘ　　　　　　　　ｘｘｘｘｘｘ　　　　　　　　　ｘ　　　ｘｘ　　　　　　　　　ｘ　　　ｘｘ　　　　　　　　　ｘ　　　　　　　　　　　　ｘｘ　　　ｘｘｘ　　　　
　　　　ｘ　ｘｘｘ　　ｘ　　　　　　　ｘｘ　　　ｘｘ　　　　　　　　　ｘ　　　ｘｘ　　　　　　　　　ｘ　　　ｘｘ　　　　　　　　　ｘ　　　　　　　　　　　　ｘｘ　　　　ｘ　　　　　
　　　　ｘ　　ｘｘ　　ｘ　　　　　　　ｘｘ　　　ｘｘ　　　　　　　　　ｘ　　ｘｘｘ　　　　　　　　　ｘ　　ｘｘｘ　　　　　　　　　ｘ　　　　　　　　　　　　ｘｘｘ　　ｘｘ　　　　　
　　ｘｘｘｘ　ｘｘｘｘｘｘ　　　　　ｘｘｘ　　ｘｘｘｘｘ　　　　　ｘｘｘｘｘｘｘ　　　　　　　　ｘｘｘｘｘｘｘ　　　　　　　　ｘｘｘｘｘ　　　　　　　　　　　ｘｘｘｘｘｘ　　　　　
　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　ｘｘ　　　
        ''')

    def choose_action(self, s, evaluation=False):
        return self._get_action(s, evaluation).numpy()

    def get_target_action(self, s):
        return self._get_target_action(s).numpy()

    @tf.function
    def _get_action(self, vector_input, evaluation):
        vector_input = self.cast(vector_input)
        with tf.device(self.device):
            mu = self.actor_net(vector_input)
            if evaluation == True:
                return mu
            else:
                return tf.clip_by_value(mu + self.action_noise(), -1, 1)

    @tf.function
    def _get_target_action(self, vector_input):
        vector_input = self.cast(vector_input)
        with tf.device(self.device):
            target_mu = self.actor_target_net(vector_input)
        return tf.clip_by_value(target_mu + self.action_noise(), -1, 1)

    def learn(self, episode, ap, al, ss, ss_, aa, aa_, s, r):
        ap, al, ss, ss_, aa, aa_, s, r = map(self.data_convert, (ap, al, ss, ss_, aa, aa_, s, r))
        summaries = self.train(ap, al, ss, ss_, aa, aa_, s, r)
        self.update_target_net_weights(
            self.actor_target_net.weights + self.q_target_net.weights,
            self.actor_net.weights + self.q_net.weights,
            self.ployak)
        summaries.update(dict([
            ['LEARNING_RATE/actor_lr', self.actor_lr(self.train_step)],
            ['LEARNING_RATE/critic_lr', self.critic_lr(self.train_step)]
        ]))
        self.write_training_summaries(self.global_step, summaries)

    @tf.function(experimental_relax_shapes=True)
    def train(self, q_actor_a_previous, q_actor_a_later, ss, ss_, aa, aa_, s, r):
        with tf.device(self.device):
            with tf.GradientTape() as tape:
                q = self.q_net(ss, aa)
                q_target = self.q_target_net(ss_, aa_)
                dc_r = tf.stop_gradient(r + self.gamma * q_target)
                td_error = q - dc_r
                q_loss = 0.5 * tf.reduce_mean(tf.square(td_error))
            q_grads = tape.gradient(q_loss, self.q_net.trainable_variables)
            self.optimizer_critic.apply_gradients(
                zip(q_grads, self.q_net.trainable_variables)
            )
            with tf.GradientTape() as tape:
                mu = self.actor_net(s)
                mumu = tf.concat((q_actor_a_previous, mu, q_actor_a_later), axis=-1)
                q_actor = self.q_net(ss, mumu)
                actor_loss = -tf.reduce_mean(q_actor)
            actor_grads = tape.gradient(actor_loss, self.actor_net.trainable_variables)
            self.optimizer_actor.apply_gradients(
                zip(actor_grads, self.actor_net.trainable_variables)
            )
            self.global_step.assign_add(1)
            return dict([
                ['LOSS/actor_loss', actor_loss],
                ['LOSS/critic_loss', q_loss]
            ])

    @tf.function(experimental_relax_shapes=True)
    def train_persistent(self, q_actor_a_previous, q_actor_a_later, ss, ss_, aa, aa_, s, r):
        with tf.device(self.device):
            with tf.GradientTape(persistent=True) as tape:
                q = self.q_net(ss, aa)
                q_target = self.q_target_net(ss_, aa_)
                dc_r = tf.stop_gradient(r + self.gamma * q_target)
                td_error = q - dc_r
                q_loss = 0.5 * tf.reduce_mean(tf.square(td_error))
                mu = self.actor_net(s)
                mumu = tf.concat((q_actor_a_previous, mu, q_actor_a_later), axis=-1)
                q_actor = self.q_net(ss, mumu)
                actor_loss = -tf.reduce_mean(q_actor)
            q_grads = tape.gradient(q_loss, self.q_net.trainable_variables)
            self.optimizer_critic.apply_gradients(
                zip(q_grads, self.q_net.trainable_variables)
            )
            actor_grads = tape.gradient(actor_loss, self.actor_net.trainable_variables)
            self.optimizer_actor.apply_gradients(
                zip(actor_grads, self.actor_net.trainable_variables)
            )
            self.global_step.assign_add(1)
            return dict([
                ['LOSS/actor_loss', actor_loss],
                ['LOSS/critic_loss', q_loss]
            ])