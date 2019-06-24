#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Han Xiao <artex.xh@gmail.com> <https://hanxiao.github.io>
import os
import random
import sys
import time
import numpy as np
from .worker_skeleton import WKRWorkerSkeleton

class WKRPreprocessWorker(WKRWorkerSkeleton):
    def __init__(self, id, args, worker_address_list, sink_address, device_id):
        super().__init__(id, args, worker_address_list, sink_address, device_id, 
        args.pre_gpu_memory_fraction, 
        args.pre_model_name, 
        args.pre_batch_size, 
        args.pre_batch_group_timeout, 
        args.pre_tmp_folder, 
        name='PRE-WORKER', color='yellow')
    