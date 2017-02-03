from collections import deque
import os

import numpy as np
from keras.models import Sequential
from keras.layers.core import Dense, Dropout, Activation, Flatten
from keras.layers import InputLayer
from keras.models import model_from_yaml
import keras.callbacks
import keras.backend.tensorflow_backend as KTF
import tensorflow as tf

f_log = './log'
f_model = './models'

model_filename = 'dqn_model.yaml'
weights_filename = 'dqn_model_weights.hdf5'


class DQNAgent:
    """
    Multi Layer Perceptron with Experience Replay
    """

    def __init__(self, enable_actions, environment_name):
        # parameters
        self.name = os.path.splitext(os.path.basename(__file__))[0]
        self.environment_name = environment_name
        self.enable_actions = enable_actions
        self.n_actions = len(self.enable_actions)
        self.minibatch_size = 32
        self.replay_memory_size = 1000
        self.learning_rate = 0.001
        self.discount_factor = 0.9
        self.exploration = 0.1
        self.model_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
        self.model_name = "{}.ckpt".format(self.environment_name)

        self.old_session = KTF.get_session()
        self.session = tf.Session('')
        KTF.set_session(self.session)

        # replay memory
        self.D = deque(maxlen=self.replay_memory_size)

        # variables
        self.current_loss = 0.0

    def init_model(self):

        self.model = Sequential()
        self.model.add(InputLayer(input_shape=(8, 8)))
        self.model.add(Flatten())
        self.model.add(Dense(64, activation='relu'))
        self.model.add(Dropout(0.2))
        self.model.add(Dense(self.n_actions))
        self.model.compile(loss='mean_squared_error',
                           optimizer="rmsprop",
                           metrics=['accuracy'])

    def Q_values(self, state):
        # Q(state, action) of all actions
        res = self.model.predict(np.array([state]))

        return res[0]

    def select_action(self, state, epsilon):
        if np.random.rand() <= epsilon:
            # random
            return np.random.choice(self.enable_actions)
        else:
            # max_action Q(state, action)
            return self.enable_actions[np.argmax(self.Q_values(state))]

    def store_experience(self, state, action, reward, state_1, terminal):
        self.D.append((state, action, reward, state_1, terminal))

    def experience_replay(self):
        state_minibatch = []
        y_minibatch = []

        # sample random minibatch
        minibatch_size = min(len(self.D), self.minibatch_size)
        minibatch_indexes = np.random.randint(0, len(self.D), minibatch_size)

        for j in minibatch_indexes:
            state_j, action_j, reward_j, state_j_1, terminal = self.D[j]
            action_j_index = self.enable_actions.index(action_j)

            y_j = self.Q_values(state_j)

            if terminal:
                y_j[action_j_index] = reward_j
            else:
                # reward_j + gamma * max_action' Q(state', action') alpha(learing rate) = 1
                y_j[action_j_index] = reward_j + self.discount_factor * np.max(self.Q_values(state_j_1))  # NOQA

            state_minibatch.append(state_j)
            y_minibatch.append(y_j)

        # training
        self.model.fit(np.array(state_minibatch), np.array(y_minibatch), verbose=0)

        # for log
        score = self.model.evaluate(np.array(state_minibatch), np.array(y_minibatch), verbose=0)
        self.current_loss = score[0]

    def load_model(self, model_path=None):

        yaml_string = open(os.path.join(f_model, model_filename)).read()
        self.model = model_from_yaml(yaml_string)
        self.model.load_weights(os.path.join(f_model, weights_filename))

        self.model.compile(loss='mean_squared_error',
                           optimizer="rmsprop",
                           metrics=['accuracy'])

    def save_model(self):
        yaml_string = self.model.to_yaml()
        open(os.path.join(f_model, 'dqn_model.yaml'), 'w').write(yaml_string)
        print('save weights')
        self.model.save_weights(os.path.join(f_model, 'dqn_model_weights.hdf5'))

    def end_session(self):
        KTF.set_session(self.old_session)