#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Han Xiao <artex.xh@gmail.com> <https://hanxiao.github.io>
import multiprocessing
import os
import random
import sys
import threading
import time
from collections import defaultdict
from datetime import datetime
from itertools import chain
from multiprocessing import Process
from multiprocessing.pool import Pool

import numpy as np
import zmq
import zmq.decorators as zmqd
from termcolor import colored
from zmq.utils import jsonapi

from .helper import *
from .protocol import *
from .http import BertHTTPProxy
from .zmq_decor import multi_socket

from .statistic import ServerStatistic

from waveglow_infer import mel_lib

class WKRPreSink(Process):
    def __init__(self, args, front_presink_addr, worker_address_list):
        super().__init__()
        self.exit_flag = multiprocessing.Event()
        self.front_sink_addr = front_presink_addr
        self.verbose = args.verbose
        self.is_ready = multiprocessing.Event()
        self.postworker_address_list = worker_address_list
        self.number_postworker_address = len(worker_address_list)

        self.transfer_protocol = args.protocol

        self.current_jobnum = 0
        self.maximum_jobnum = 0
        self.total_processed = 0
        
        
        self.logdir = args.log_dir
        self.logger = set_logger(colored('PRESINK', 'cyan'), logger_dir=self.logdir, verbose=args.verbose)

    def close(self):
        self.logger.info('shutting down...')
        self.is_ready.clear()
        self.exit_flag.set()
        self.terminate()
        self.join()
        self.logger.info('terminated!')

    def run(self):
        self._run()

    @zmqd.socket(zmq.PULL)
    @zmqd.socket(zmq.PAIR)
    @zmqd.socket(zmq.PAIR)
    @multi_socket(zmq.PUSH, num_socket='number_postworker_address')
    def _run(self, receiver, frontend, post_sink, *backend_postsocks):

        def push_new_job(client, req_id, msg, msg_info):
            _sock = rand_backend_socket

            logger.info('request job\tjob_id: {}@{}\ttotal_partial: {}'.format(client, req_id, 1))
            post_sink.send_multipart([client_addr, ServerCmd.new_job, jsonapi.dumps({'job_parts': '1', 'split_info': {}}), to_bytes(req_id)])

            send_to_next(self.transfer_protocol, client, req_id, msg, _sock)

        receiver_addr = auto_bind(receiver)
        pre_to_post_sink_addr = auto_bind(post_sink)

        frontend.connect(self.front_sink_addr)

        for sock, addr in zip(backend_postsocks, self.postworker_address_list):
            sock.bind(addr)

        poller = zmq.Poller()
        poller.register(frontend, zmq.POLLIN)
        poller.register(receiver, zmq.POLLIN)
        poller.register(post_sink, zmq.POLLIN)
        
        # send worker receiver address back to frontend
        frontend.send(receiver_addr.encode('ascii'))
        frontend.send(pre_to_post_sink_addr.encode('ascii'))

        # Windows does not support logger in MP environment, thus get a new logger
        # inside the process for better compability
        logger = set_logger(colored('PRESINK', 'cyan'), logger_dir=self.logdir, verbose=self.verbose)
        logger.info('ready')
        self.is_ready.set()

        rand_backend_socket = None
        while not self.exit_flag.is_set():
            try:
                socks = dict(poller.poll())
                if socks.get(receiver) == zmq.POLLIN:
                    client, req_id, msg, msg_info = recv_from_prev(self.transfer_protocol, receiver)

                    logger.info("collect {}#{}".format(client, req_id))
                    
                    # pick random socket
                    rand_backend_socket = random.choice([b for b in backend_postsocks if b != rand_backend_socket])

                    # delivery job
                    push_new_job(client, req_id, msg, msg_info)

                    self.current_jobnum -= 1
                    self.total_processed += 1
                    logger.info('pushed post worker\tjob id: %s \tleft: %d' % (job_info, self.current_jobnum))

                if socks.get(frontend) == zmq.POLLIN:
                    client_addr, msg_type, msg_info, req_id = frontend.recv_multipart()
                    if msg_type == ServerCmd.new_job:
                        job_info = client_addr + b'#' + req_id
                        # # register a new job
                        # pending_jobs[job_info].checksum = int(msg_info)
                        logger.info('job register\tjob id: %s' % job_info)
                        self.current_jobnum += 1
                        self.maximum_jobnum = self.current_jobnum if self.current_jobnum > self.maximum_jobnum else self.maximum_jobnum
                        
                    elif msg_type == ServerCmd.show_config:
                        time.sleep(0.1)  # dirty fix of slow-joiner: sleep so that client receiver can connect.
                        logger.info('send config\tclient %s' % client_addr)
                        prev_status = jsonapi.loads(msg_info)
                        status={
                            'statistic_presink': {
                                'total_job_in_queue': self.current_jobnum,
                                'maximum_job_in_queue': self.maximum_jobnum,
                                'total_processed_job': self.total_processed,
                                'util': self.current_jobnum/(self.maximum_jobnum) if self.maximum_jobnum > 0 else 0
                            }
                        }
                        post_sink.send_multipart([client_addr, msg_type, jsonapi.dumps({**prev_status, 
                                                                                        **status}), req_id])
            except Exception as e:
                import traceback
                tb=traceback.format_exc()
                logger.error('{}\n{}'.format(e, tb))