import numpy as np
import scipy.ndimage as ndimage
import tensorflow as tf
import blosc
import random
#from prototype11.atari_environment_wrapper import atari_environment
from custom_environments.cart import Cart
from custom_environments.cartpole import CartPole
from custom_environments.pygames import ple_wrapper
import gym
#from matplotlib import pyplot as plt
#import pylab
import uuid

def process_frame2(frame):
    s = np.dot(frame, np.array([.299, .587, .114])).astype(np.uint8)
    s = ndimage.zoom(s, (0.4, 0.525))
    #s.resize((84, 84, 1))
    return s

class Memory:
    def __init__(self, size):
       self.max_size = size
       self.mem = []

    def add(self, element):
        self.mem.append(element)

        if len(self.mem) > self.max_size:
            self.mem.pop(0)

    def sample(self, size):
        size = min(size, len(self.mem))
        return random.sample(self.mem, size)

class Memory_with_compression:
    def __init__(self, size, shape=[84, 84, 4]):
       self.shape = [1] + shape
       self.max_size = size
       self.mem = []

    def add(self, element):
        ele = []
        ele.append(blosc.compress(np.reshape(element[0], np.prod(np.array(self.shape))).tobytes(), typesize=1)) #Current state
        ele.append(element[1]) #Action
        ele.append(element[2]) #Reward
        ele.append(blosc.compress(np.reshape(element[3], np.prod(np.array(self.shape))).tobytes(), typesize=1)) #Next state
        ele.append(element[4]) #Done
        self.mem.append(ele)

        if len(self.mem) > self.max_size:
            self.mem.pop(0)

    def sample(self, size):
        size = min(size, len(self.mem))
        elements = random.sample(self.mem, size)

        elements_decompressed = []
        for i in range(size):
            element_decompressed = []
            element_decompressed.append(np.reshape(np.fromstring(blosc.decompress(elements[i][0]), dtype=np.uint8), tuple(self.shape)))
            element_decompressed.append(elements[i][1])
            element_decompressed.append(elements[i][2])
            element_decompressed.append(np.reshape(np.fromstring(blosc.decompress(elements[i][3]), dtype=np.uint8), tuple(self.shape)))
            element_decompressed.append(elements[i][4])
            elements_decompressed.append(element_decompressed)
        return elements_decompressed

    def __del__(self):
        del self.mem

class Memory_with_compression2:
    def __init__(self, size, shape=[84, 84, 4]):
       self.shape = [1] + shape
       self.max_size = size
       self.mem = []

    def add(self, element):
        ele = []
        ele.append(blosc.compress(np.reshape(element[0], np.prod(np.array(self.shape))).tobytes(), typesize=1)) #States
        ele.append(element[1]) #Action
        ele.append(element[2]) #Reward
        ele.append(element[3]) #Done
        self.mem.append(ele)

        if len(self.mem) > self.max_size:
            self.mem.pop(0)

    def sample(self, size):
        size = min(size, len(self.mem))
        elements = random.sample(self.mem, size)

        elements_decompressed = []
        for i in range(size):
            element_decompressed = []
            element_decompressed.append(np.reshape(np.fromstring(blosc.decompress(elements[i][0]), dtype=np.uint8), tuple(self.shape)))
            element_decompressed.append(elements[i][1])
            element_decompressed.append(elements[i][2])
            element_decompressed.append(elements[i][3])
            elements_decompressed.append(element_decompressed)
        return elements_decompressed

    def __del__(self):
        del self.mem

def update_target_graph(from_scope, to_scope):
    from_vars = tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES, from_scope)
    to_vars = tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES, to_scope)

    op_holder = []
    for from_var, to_var in zip(from_vars, to_vars):
        op_holder.append(to_var.assign(from_var))
    return op_holder

def update_target_graph_vars(from_vars, to_vars):
    op_holder = []
    for from_var, to_var in zip(from_vars, to_vars):
        op_holder.append(to_var.assign(from_var))
    return op_holder

#A soft version of update target graph
def update_target_graph2(from_scope, to_scope, tau=.001):
    from_vars = tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES, from_scope)
    to_vars = tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES, to_scope)

    op_holder = []
    for from_var, to_var in zip(from_vars, to_vars):
        op_holder.append(to_var.assign(tf.multiply(from_var, tau) + tf.multiply(to_var, 1. - tau)))
    return op_holder

def update_target_graph3(from_vars, to_vars, tau=.001):
    op_holder = []
    for from_var, to_var in zip(from_vars, to_vars):
        op_holder.append(to_var.assign(tf.multiply(from_var, tau) + tf.multiply(to_var, 1. - tau)))
    return op_holder

def split(array, w, s):
    assert len(array.shape) == 4
    channels = array.shape[-1]
    sliced = []
    rbegin = 0; cbegin = 0;
    while rbegin + w <= array.shape[1]:
        cbegin = 0
        while cbegin + w <= array.shape[2]:
            sliced.append(array[:, rbegin:rbegin+w, cbegin:cbegin+w, :])
            cbegin += s
        rbegin += s

    sliced = np.concatenate(sliced, axis=0)
    sliced = np.reshape(sliced, (-1, w * w * channels))
    sliced = sliced.astype(np.float64) / 255.
    return sliced

def unison_shuffled_copies(a, b):
    assert len(a) == len(b)
    p = np.random.permutation(len(a))
    return a[p], b[p]

def shuffle(a):
    p = np.random.permutation(len(a))
    return a[p]

class env_interface:
    def __init__(self, interface, rom=None, pixel_feature=None, padding=False, render=True):
        assert interface in ['gym', 'gym!atari', 'ale', 'custom_cart', 'custom_cartpole', 'ple']
        if interface in ['gym', 'ale']:
            assert rom is not None
        self.interface = interface
        self.rom = rom

        if interface in ['custom_cart', 'custom_cartpole']:
            assert pixel_feature in [True, False]
            self.pixel_feature = pixel_feature
            self.padding = padding
            self.render = render

        if self.interface == 'gym':
            self.env = gym.make(self.rom)
            self.action_size = self.env.action_space.n
            self.obs_space_shape = (210, 160, 3)
        if self.interface == 'gym!atari':
            self.env = gym.make(self.rom)
            self.action_size = self.env.action_space.n
            self.obs_space_shape = self.env.observation_space.shape
        elif self.interface == 'ale':
            self.env = atari_environment(self.rom, display_screen=False)
            self.action_size = self.env.num_actions
            self.obs_space_shape = (210, 160, 3)
        elif self.interface == 'custom_cart':
            self.env = Cart(pixelFeature=self.pixel_feature, render=self.render)
            if self.env.pixelFeature:
                self.obs_space_shape = self.env.screenSize
            elif self.env.pixelFeature == False and self.padding == True:
                self.obs_space_shape = (2, 2)
            else:
                self.obs_space_shape = (2,)
            self.action_size = self.env.numActions
        elif self.interface == 'custom_cartpole':
            self.env = CartPole(pixelFeature=self.pixel_feature, render=self.render)
            if self.env.pixelFeature:
                self.obs_space_shape = self.env.screenSize
            elif self.env.pixelFeature == False and self.padding == True:
                self.obs_space_shape = (2, 2)
            else:
                self.obs_space_shape = (4,)
            self.action_size = self.env.numActions
        elif self.interface == 'ple':
            self.env = ple_wrapper(rom)
            self.obs_space_shape = tuple(self.env.screen_dims)
            self.action_size = self.env.action_size

    def reset(self):
        if self.interface == 'gym':
            frame = process_frame2(self.env.reset())
            return frame
        elif self.interface == 'gym!atari':
            frame = self.env.reset()
            return frame
        elif self.interface == 'ale':
            frame = self.env.reset()
            return frame
        elif self.interface == 'custom_cart':
            self.env = Cart(pixelFeature=self.pixel_feature, render=self.render)
            frame = self.env.getCurrentState()
            return self.pad(frame)
        elif self.interface == 'custom_cartpole':
            self.env = CartPole(pixelFeature=self.pixel_feature, render=self.render)
            frame = self.env.getCurrentState()
            return self.pad(frame)
        elif self.interface == 'ple':
            return self.env.reset()

    def step(self, action):
        if self.interface == 'gym':
            frame, reward, done, info = self.env.step(action)
            frame = process_frame2(frame)
            return frame, reward, done, info 
        if self.interface == 'gym!atari':
            frame, reward, done, info = self.env.step(action)
            return frame, reward, done, info
        elif self.interface == 'ale':
            frame, reward, done = self.env.step(action)
            return frame, float(reward), done, None
        elif self.interface == 'custom_cart':
            frame, reward, done = self.env.act(action - 1)
            return self.pad(frame) , reward, done, None
        elif self.interface == 'custom_cartpole':
            frame, reward, done = self.env.act(action - 1)
            return self.pad(frame) , reward, done, None
        elif self.interface == 'ple':
            frame, reward, done = self.env.step(action)
            return frame, reward, done, None
    
    def pad(self, frame):
        if self.padding == False:
            return frame
        assert self.pixel_feature == False
        if self.interface == 'custom_cart':
            ret = np.concatenate([frame[..., np.newaxis], np.zeros((2, 1))], axis=-1)
            return ret
        elif self.interface == 'custom_cartpole':
            return frame.reshape((2, 2,))

    def __del__(self):
        if self.interface == 'gym':
            self.env.close()

def parse_states(states, mode):
    assert mode in ['gbm', 'cc', 'gae']

    if mode == 'gbm':
        assert states.shape[-1] == 2
        return states[:, :, :, 0][..., np.newaxis], states[:, :, :, 1][..., np.newaxis]
    elif mode == 'cc' or mode == 'gae':
        assert len(states.shape) == 4
        return states, states

def parse_split_shuffle_states(states, mode, w, s):
    assert mode in ['gbm', 'cc', 'gae']

    if mode == 'gbm':
        x = states[:, :, :, 0][..., np.newaxis]
        y = states[:, :, :, 1][..., np.newaxis]
        x = split(x, w, s)
        y = split(y, w, s)
        x, y = unison_shuffled_copies(x, y)
        return x, y
    elif mode == 'cc' or mode == 'gae':
        x = split(states, w, s)
        x = shuffle(x)
        return x, x

# Taken from https://github.com/openai/baselines/blob/master/baselines/ddpg/noise.py, which is
# based on http://math.stackexchange.com/questions/1287634/implementing-ornstein-uhlenbeck-in-matlab
class OrnsteinUhlenbeckActionNoise:
    def __init__(self, mu, sigma=0.3, theta=.15, dt=1e-2, x0=None):
        self.theta = theta
        self.mu = mu
        self.sigma = sigma
        self.dt = dt
        self.x0 = x0
        self.reset()

    def __call__(self):
        x = self.x_prev + self.theta * (self.mu - self.x_prev) * self.dt + \
                self.sigma * np.sqrt(self.dt) * np.random.normal(size=self.mu.shape)
        self.x_prev = x
        return x

    def reset(self):
        self.x_prev = self.x0 if self.x0 is not None else np.zeros_like(self.mu)

    def __repr__(self):
        return 'OrnsteinUhlenbeckActionNoise(mu={}, sigma={})'.format(self.mu, self.sigma)

def log(x):
    return tf.log(tf.maximum(x, 1e-6))

def lrelu(x, alpha=.2):
  return tf.nn.relu(x) - alpha * tf.nn.relu(-x)

def sample_z(batch_size, latent_size):
    #return np.random.uniform(-1., 1., [batch_size, latent_size])
    return np.random.normal(0., 1., [batch_size, latent_size])

def dispims(M, height, width, border=0, bordercolor=0.0, **kwargs):
    """ Display the columns of matrix M in a montage. """
    numimages = M.shape[1]
    n0 = np.int(np.ceil(np.sqrt(numimages)))
    n1 = np.int(np.ceil(np.sqrt(numimages)))
    im = bordercolor*\
         np.ones(((height+border)*n1+border,(width+border)*n0+border),dtype='<f8')
    for i in range(n0):
        for j in range(n1):
            if i*n1+j < M.shape[1]:
                im[j*(height+border)+border:(j+1)*(height+border)+border,\
                   i*(width+border)+border:(i+1)*(width+border)+border] = \
                np.vstack((\
                  np.hstack((np.reshape(M[:,i*n1+j],(width,height)).T,\
                         bordercolor*np.ones((height,border),dtype=float))),\
                  bordercolor*np.ones((border,width+border),dtype=float)\
                  ))
    pylab.imshow(im.T,cmap=pylab.cm.gray,interpolation='nearest', **kwargs)
    pylab.show()

def get_random_string():
    return str(uuid.uuid4().get_hex().upper()[0:6])

def str2list(string):
    l = string.split(',')
    assert len(l) == 4

    import ast
    l[0] = ast.literal_eval(l[0])
    for i in range(1, len(l)):
        l[i] = int(l[i])

    return l
