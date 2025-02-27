# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/080_models.HydraMultiRocketPlus.ipynb.

# %% auto 0
__all__ = ['HydraMultiRocket', 'HydraMultiRocketBackbonePlus', 'HydraMultiRocketPlus']

# %% ../../nbs/080_models.HydraMultiRocketPlus.ipynb 3
from collections import OrderedDict
from typing import Any

import numpy as np
import torch
import torch.nn as nn

from ..imports import default_device
from .HydraPlus import HydraBackbonePlus
from .layers import Flatten, rocket_nd_head
from .MultiRocketPlus import MultiRocketBackbonePlus

# %% ../../nbs/080_models.HydraMultiRocketPlus.ipynb 4
class HydraMultiRocketBackbonePlus(nn.Module):

    def __init__(self, c_in, c_out, seq_len, d=None, 
                 k = 8, g = 64, max_c_in = 8, clip=True,
                 num_features=50_000, max_dilations_per_kernel=32, kernel_size=9, max_num_channels=None, max_num_kernels=84,
                 use_bn=True, fc_dropout=0, custom_head=None, zero_init=True, use_diff=True, device=default_device()):

        super().__init__()

        self.hydra = HydraBackbonePlus(c_in, c_out, seq_len, k=k, g=g, max_c_in=max_c_in, clip=clip, device=device, zero_init=zero_init)
        self.multirocket = MultiRocketBackbonePlus(c_in, seq_len, num_features=num_features, max_dilations_per_kernel=max_dilations_per_kernel,
                                                   kernel_size=kernel_size, max_num_channels=max_num_channels, max_num_kernels=max_num_kernels, 
                                                   use_diff=use_diff)

        self.num_features = self.hydra.num_features + self.multirocket.num_features
        
    
    # transform in batches of *batch_size*
    def batch(self, X, split=None, batch_size=256):
        bs = X.shape[0]
        if bs <= batch_size:
            return self(X)
        elif split is None:
            Z = [self(X[i:i+batch_size]) for i in range(0, bs, batch_size)]
            return torch.cat(Z)
        else:
            batches = torch.as_tensor(split).split(batch_size)
            Z = [self(X[batch]) for batch in batches]
            return torch.cat(Z)
    
    
    def forward(self, x):
        x = torch.cat([self.hydra(x), self.multirocket(x)], -1)
        return x

# %% ../../nbs/080_models.HydraMultiRocketPlus.ipynb 5
class HydraMultiRocketPlus(nn.Sequential):

    def __init__(self, 
        c_in:int, # num of channels in input
        c_out:int, # num of channels in output
        seq_len:int, # sequence length
        d:tuple=None, # shape of the output (when ndim > 1)
        k:int=8, # number of kernels per group in HydraBackbone
        g:int=64, # number of groups in HydraBackbone
        max_c_in:int=8, # max number of channels per group in HydraBackbone
        clip:bool=True, # clip values >= 0 in HydraBackbone
        num_features:int=50_000, # number of MultiRocket features
        max_dilations_per_kernel:int=32, # max dilations per kernel in MultiRocket
        kernel_size:int=9, # kernel size in MultiRocket
        max_num_channels:int=None, # max number of channels in MultiRocket
        max_num_kernels:int=84, # max number of kernels in MultiRocket
        use_bn:bool=True, # use batch norm
        fc_dropout:float=0., # dropout probability
        custom_head:Any=None, # optional custom head as a torch.nn.Module or Callable
        zero_init:bool=True, # set head weights and biases to zero
        use_diff:bool=True, # use diff(X) as input
        device:str=default_device(), # device to use
        ):
        # Backbone
        backbone = HydraMultiRocketBackbonePlus(c_in, c_out, seq_len, k=k, g=g, max_c_in=max_c_in, clip=clip, device=device, zero_init=zero_init,
                                                num_features=num_features, max_dilations_per_kernel=max_dilations_per_kernel,
                                                kernel_size=kernel_size, max_num_channels=max_num_channels, max_num_kernels=max_num_kernels, use_diff=use_diff)
        
        num_features = backbone.num_features


        # Head
        self.head_nf = num_features
        if custom_head is not None: 
            if isinstance(custom_head, nn.Module): head = custom_head
            else: head = custom_head(self.head_nf, c_out, 1)
        elif d is not None:
            head = rocket_nd_head(num_features, c_out, seq_len=None, d=d, use_bn=use_bn, fc_dropout=fc_dropout, zero_init=zero_init)
        else:
            layers = [Flatten()]
            if use_bn:
                layers += [nn.BatchNorm1d(num_features)]
            if fc_dropout:
                layers += [nn.Dropout(fc_dropout)]
            linear = nn.Linear(num_features, c_out)
            if zero_init:
                nn.init.constant_(linear.weight.data, 0)
                nn.init.constant_(linear.bias.data, 0)
            layers += [linear]
            head = nn.Sequential(*layers)

        super().__init__(OrderedDict([('backbone', backbone), ('head', head)]))

HydraMultiRocket = HydraMultiRocketPlus
