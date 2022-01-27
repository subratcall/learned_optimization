# coding=utf-8
# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tasks based on simple convolutional nets."""
# pylint: disable=invalid-name

from typing import Any, Optional, Sequence, Callable

import gin
import haiku as hk
import jax
import jax.numpy as jnp
from learned_optimization.tasks import base
from learned_optimization.tasks.datasets import image

Params = Any
ModelState = Any
PRNGKey = jnp.ndarray


def _cross_entropy_pool_loss(
    hidden_units: Sequence[int],
    activation_fn: Callable[[jnp.ndarray], jnp.ndarray],
    initializers: Optional[hk.initializers.Initializer] = None,
    pool: str = "avg",
    num_classes: int = 10):
  """Haiku function for a conv net with pooling and cross entropy loss."""
  if not initializers:
    initializers = {}

  def _fn(batch):
    net = batch["image"]
    strides = [2] + [1] * (len(hidden_units) - 1)
    for hs, ks, stride in zip(hidden_units, [3] * len(hidden_units), strides):
      net = hk.Conv2D(hs, ks, stride=stride)(net)
      net = activation_fn(net)

    if pool == "avg":
      net = jnp.mean(net, [1, 2])
    elif pool == "max":
      net = jnp.max(net, [1, 2])
    else:
      raise ValueError("pool type not supported")

    logits = hk.Linear(num_classes)(net)

    labels = jax.nn.one_hot(batch["label"], num_classes)
    loss_vec = base.softmax_cross_entropy(labels=labels, logits=logits)
    return jnp.mean(loss_vec)

  return _fn


class _ConvTask(base.Task):
  """Helper class to construct tasks with different configs."""

  def __init__(self, base_model_fn, datasets):
    super().__init__()
    self._mod = hk.transform(base_model_fn)
    self.datasets = datasets

  def init(self, key) -> Params:
    return self._mod.init(key, next(self.datasets.train))

  def loss(self, params, key, data):
    return self._mod.apply(params, key, data)

  def normalizer(self, loss):
    return jnp.clip(loss, 0,
                    1.5 * jnp.log(self.datasets.extra_info["num_classes"]))


@gin.configurable
def Conv_Cifar10_16_32x64x64():
  """A 3 hidden layer convnet designed for 16x16 cifar10."""
  base_model_fn = _cross_entropy_pool_loss([32, 64, 64],
                                           jax.nn.relu,
                                           num_classes=10)
  datasets = image.cifar10_datasets(batch_size=128, image_size=(16, 16))
  return _ConvTask(base_model_fn, datasets)


@gin.configurable
def Conv_Cifar10_32x64x64():
  """A 3 hidden layer convnet designed for 32x32 cifar10."""
  base_model_fn = _cross_entropy_pool_loss([32, 64, 64],
                                           jax.nn.relu,
                                           num_classes=10)
  datasets = image.cifar10_datasets(batch_size=128)
  return _ConvTask(base_model_fn, datasets)
