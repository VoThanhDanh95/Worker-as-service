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

class WKRSink(Process):
    def __init__(self, args, nav_to_sink_addr, worker_socket_addrs):
        super().__init__()
        self.port = args.port_out
        self.exit_flag = multiprocessing.Event()
        self.nav_to_sink_addr = nav_to_sink_addr
        self.verbose = args.verbose
        self.is_ready = multiprocessing.Event()
        self.worker_socket_addrs = worker_socket_addrs

        self.transfer_protocol = args.protocol

        self.current_jobnum = 0
        self.maximum_jobnum = 0
        self.total_processed = 0

        self.logdir = args.log_dir
        self.logger = set_logger(colored('SINK', 'green'), logger_dir=self.logdir, verbose=args.verbose)

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
    @zmqd.socket(zmq.PUB)
    def _run(self, receiver, frontend, sender):

        receiver_addr = auto_bind(receiver)
        frontend.connect(self.nav_to_sink_addr)
        sender.bind('tcp://*:%d' % self.port)

        poller = zmq.Poller()
        poller.register(frontend, zmq.POLLIN)
        poller.register(receiver, zmq.POLLIN)

        # send worker receiver address back to frontend
        frontend.send(receiver_addr.encode('ascii'))
        
        # Windows does not support logger in MP environment, thus get a new logger
        # inside the process for better compability
        logger = set_logger(colored('SINK', 'green'), logger_dir=self.logdir, verbose=self.verbose)
        logger_error = set_logger(colored('SINK-ERROR', 'red'), logger_dir=self.logdir, verbose=self.verbose, error_log=True)
        logger.info('ready')
        self.is_ready.set()

        sink_status = ServerStatistic()
        latency_status = defaultdict(lambda: {'start': -1, 'end': -1})

        def check_status(sink_status, latency_status):
            result = []
            removed_keys = []
            for k, status in latency_status.items():
                if status['start'] != -1 and status['end'] != -1:
                    latency = (status['end']-status['start'])*1000
                    result.append(latency)
                    removed_keys.append(k)
            for k in removed_keys:
                latency_status.pop(k)
            for res in result:
                sink_status.update_key('latency', res)
            # print('\n',dict(latency_status), '\n', result, '\n')

        while not self.exit_flag.is_set():
            try:
                socks = dict(poller.poll())

                if socks.get(receiver) == zmq.POLLIN:
                    client, req_id, msg, msg_info = recv_from_prev_raw(receiver)

                    if msg_info == ServerCmd.statistic:
                        # record statistic value
                        stat_info = jsonapi.loads(msg)
                        for k, v in stat_info.items():
                            sink_status.update_key(k, v)
                    else:
                        # main processing flow
                        if msg_info == ServerCmd.exception:
                            # exception
                            logger_error.error("exception processing {}#{}\n{}".format(client, req_id, msg))
                            sink_status.update([
                                to_bytes(client), 
                                ServerCmd.exception, 
                                to_bytes(req_id), 
                                b'1'
                            ])
                        else:
                            # embeding
                            logger.info("collected {}#{}".format(client, req_id))
                            sink_status.update([
                                to_bytes(client), 
                                b'<new_request>', 
                                to_bytes(req_id), 
                                b'1'
                            ])
                        send_to_next_raw(client, req_id, msg, msg_info, sender)

                        # update latency
                        job_id = to_str(client) + '#' + to_str(req_id)
                        latency_status[job_id]['end'] = time.time()
                        check_status(sink_status, latency_status)

                        self.current_jobnum -= 1
                        self.total_processed += 1
                        logger.info('send back\tjob id: {}#{} \tleft: {}'.format(client, req_id, self.current_jobnum))

                if socks.get(frontend) == zmq.POLLIN:
                    request = frontend.recv_multipart()
                    client_addr, msg_type, msg_info, req_id = request
                    if msg_type == ServerCmd.new_job:
                        job_id = to_str(client_addr) + '#' + to_str(req_id)
                        self.current_jobnum += 1
                        self.maximum_jobnum = self.current_jobnum if self.current_jobnum > self.maximum_jobnum else self.maximum_jobnum
                        job_info = jsonapi.loads(msg_info)

                        # update latency
                        latency_status[job_id]['start'] = job_info['time']
                        check_status(sink_status, latency_status)

                        logger.info('registed job\tjob id: {}\tleft: {}'.format(job_id, self.current_jobnum))

                    elif msg_type == ServerCmd.show_config:
                        time.sleep(0.1)  # dirty fix of slow-joiner: sleep so that client receiver can connect.
                        sink_status.update(request)
                        logger.info('send config\tclient %s' % client_addr)
                        prev_status = jsonapi.loads(msg_info)
                        
                        status={
                            'statistic_postsink': {**{
                                'total_job_in_queue': self.current_jobnum,
                                'maximum_job_in_queue': self.maximum_jobnum,
                                'total_processed_job': self.total_processed,
                                'util': self.current_jobnum/(self.maximum_jobnum) if self.maximum_jobnum > 0 else 0
                            }, **sink_status.value}
                        }
                        send_to_next('obj', client_addr, req_id, {**prev_status, **status}, sender)
                    elif msg_type == ServerCmd.exception:
                        # not yet registed to the server
                        send_to_next_raw(client_addr, req_id, msg_info, ServerCmd.exception, sender)
                        logger_error.error("exception received {}#{}\{}".format(client_addr, req_id, msg_info))

            except Exception as e:
                logger_error.error('{}'.format(e), exc_info=True)
