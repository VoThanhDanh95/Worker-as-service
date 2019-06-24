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
    def __init__(self, args, front_sink_addr, pre_to_post_sink_addr, post_worker_socket_addrs):
        super().__init__()
        self.port = args.port_out
        self.exit_flag = multiprocessing.Event()
        self.front_sink_addr = front_sink_addr
        self.pre_to_post_sink_addr = pre_to_post_sink_addr
        self.verbose = args.verbose
        self.is_ready = multiprocessing.Event()
        self.post_worker_socket_addrs = post_worker_socket_addrs

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
    @zmqd.socket(zmq.PAIR)
    @zmqd.socket(zmq.PUB)
    def _run(self, receiver, frontend, pre_sink, sender):

        receiver_addr = auto_bind(receiver)
        frontend.connect(self.front_sink_addr)
        pre_sink.connect(self.pre_to_post_sink_addr)
        sender.bind('tcp://*:%d' % self.port)

        pending_jobs = defaultdict(lambda: SinkJob(protocol=self.transfer_protocol))  # type: Dict[str, SinkJob]

        poller = zmq.Poller()
        poller.register(frontend, zmq.POLLIN)
        poller.register(receiver, zmq.POLLIN)
        poller.register(pre_sink, zmq.POLLIN)

        # send worker receiver address back to frontend
        frontend.send(receiver_addr.encode('ascii'))
        
        # Windows does not support logger in MP environment, thus get a new logger
        # inside the process for better compability
        logger = set_logger(colored('SINK', 'green'), logger_dir=self.logdir, verbose=self.verbose)
        logger.info('ready')
        self.is_ready.set()

        sink_status = ServerStatistic()

        def check_finished_job(client_addr, req_id):
            client_addr, req_id = to_str(client_addr), to_str(req_id)
            finished = [(k, v) for k, v in pending_jobs.items() if v.is_done]
            for job_id, tmp in finished:
                x, x_info = tmp.result
                send_to_next(self.transfer_protocol, client_addr, req_id, x, sender)

                # update status
                sink_status.update([client_addr, b'<new_request>', req_id, b'1'])
                # release the job
                tmp.clear()
                pending_jobs.pop(job_id)
                self.current_jobnum -= 1
                self.total_processed += 1
                logger.info('send back\tjob id: %s \tleft: %d' % (job_id, self.current_jobnum))

        while not self.exit_flag.is_set():
            try:
                socks = dict(poller.poll())

                if socks.get(receiver) == zmq.POLLIN:
                    client, req_id, msg, msg_info = recv_from_prev(self.transfer_protocol, receiver)

                    logger.info("collect {}#{}".format(client, req_id))
                    
                    job_id = to_bytes("{}#{}".format(client, req_id))

                    # adding wave
                    pending_jobs[job_id].add_wave(msg, 0)

                    # check and send back finished jobs
                    check_finished_job(to_bytes(client), to_bytes(req_id))

                if socks.get(frontend) == zmq.POLLIN:
                    # client_addr, msg_type, msg_info, req_id = frontend.recv_multipart()
                    # if msg_type == ServerCmd.new_job:
                    #     job_info = client_addr + b'#' + req_id
                    #     # # register a new job
                    #     # pending_jobs[job_info].checksum = int(msg_info)
                    #     logger.info('job register\tsize: %d\tjob id: %s' % (int(msg_info), job_info))
                    #     self.current_jobnum += 1
                    #     self.maximum_jobnum = self.current_jobnum if self.current_jobnum > self.maximum_jobnum else self.maximum_jobnum

                    # elif msg_type == ServerCmd.show_config:
                    #     time.sleep(0.1)  # dirty fix of slow-joiner: sleep so that client receiver can connect.
                    #     logger.info('send config\tclient %s' % client_addr)
                    #     sender.send_multipart([client_addr, msg_info, req_id])
                    pass

                if socks.get(pre_sink) == zmq.POLLIN:
                    client_addr, msg_type, msg_info, req_id = pre_sink.recv_multipart()
                    if msg_type == ServerCmd.new_job:
                        job_id = client_addr + b'#' + req_id
                        number_part = 1
                        split_info = {}
                        pending_jobs[job_id].set_checksum(number_part)
                        pending_jobs[job_id].set_concatenate_info(split_info)
                        pending_jobs[job_id].check_fill()
                        
                        self.current_jobnum += 1
                        self.maximum_jobnum = self.current_jobnum if self.current_jobnum > self.maximum_jobnum else self.maximum_jobnum
                        logger.info('registed job\tnumber_part: {}\tjob id: {}'.format(number_part, job_id))
                        
                        check_finished_job(client_addr, req_id)

                    elif msg_type == ServerCmd.show_config:
                        time.sleep(0.1)  # dirty fix of slow-joiner: sleep so that client receiver can connect.
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
                                                                        
            except Exception as e:
                import traceback
                traceback.print_exc()
                tb=traceback.format_exc()
                logger.error('{}\n{}'.format(e, tb))

class SinkJob:
    def __init__(self, protocol='json'):
        self._pending_waves = []
        self.checksum = 0
        self.final_ndarray = None
        self.concatenate_info = None
        self.protocol = protocol

    def clear(self):
        self._pending_waves.clear()
        del self.final_ndarray

    def set_checksum(self, checksum):
        self.checksum = int(checksum)

    def set_concatenate_info(self, concatenate_info):
        self.concatenate_info = concatenate_info

    def fill_data(self):
        if self.is_have_all_part:
            sorted_waves = sorted(self._pending_waves, key=lambda tup: tup[0])
            sorted_waves = [a[1] for a in sorted_waves]
            
            if self.protocol == 'json':
                self.final_ndarray = sorted_waves
            else:
                self.final_ndarray = sorted_waves[0]

    def add_wave(self, data, partial_id):
        try:
            self._pending_waves.append((partial_id, data))
            self.fill_data()
        except Exception as e:
            import traceback
            tb=traceback.format_exc()
            logger = set_logger(colored('SinkJob', 'green'), True)
            logger.info('Error {}:\t{}'.format(e, tb))

    def check_fill(self):
        self.fill_data()

    @property
    def registed(self):
        return self.checksum > 0

    @property
    def progress(self):
        if self.registed:
            return len(self._pending_waves)/self.checksum
        else:
            return 0

    @property
    def is_have_all_part(self):
        return self.concatenate_info is not None and self.registed and len(self._pending_waves) == self.checksum

    @property
    def is_done(self):
        return self.is_have_all_part and self.final_ndarray is not None

    @property
    def result(self):
        if self.protocol == 'obj':
            x = self.final_ndarray
            x_info = {}
        else:
            x = self.final_ndarray
            x = x if len(x.shape) == 2 else x[np.newaxis, :]
            x_info = {'dtype': str(x.dtype),
                    'shape': x.shape}
        return x, x_info

    @property
    def description(self):
        return '_pending_waves: {}\tchecksum: {}\tfinal_ndarray: {}\tconcatenate_info: {}'.format(self._pending_waves, self.checksum, self.final_ndarray, self.concatenate_info)