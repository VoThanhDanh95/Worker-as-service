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

from .presink import WKRPreSink
from .postsink import WKRSink
from .preprocess_worker import WKRPreprocessWorker
from .hard_worker import WKRHardWorker
from .statistic import ServerStatistic

__all__ = ['__version__', 'WKRServer', 'WKRHardWorker', 'WKRPreprocessWorker']
__version__ = '1.0.0-a'

class WKRServer(threading.Thread):
    def __init__(self, args, preprocessor=WKRPreprocessWorker, hardprocesser=WKRHardWorker):
        super().__init__()
        
        self.preprocessor_skeleton = preprocessor
        if not issubclass(self.preprocessor_skeleton, WKRPreprocessWorker):
            raise AssertionError('preprocessor must inherit from class WKRPreprocessWorker')

        self.hardprocessor_skeleton = hardprocesser
        if not issubclass(self.hardprocessor_skeleton, WKRHardWorker):
            raise AssertionError('hardprocesser must inherit from class WKRHardWorker')

        self.model_dir = args.model_dir

        self.pre_num_worker = args.pre_num_worker
        self.pre_device_map = args.pre_device_map
        self.pre_gpu_memory_fraction = args.pre_gpu_memory_fraction
        self.pre_all_cpu = args.pre_cpu

        self.wkr_num_worker = args.wkr_num_worker
        self.wkr_device_map = args.wkr_device_map
        self.wkr_gpu_memory_fraction = args.wkr_gpu_memory_fraction
        self.wkr_all_cpu = args.wkr_cpu

        # tacotron settings
        self.num_concurrent_presocket = max(8, args.pre_num_worker * 2)
        self.pre_batch_size = args.pre_batch_size

        self.num_concurrent_postsocket = max(8, args.wkr_num_worker * 2)
        self.wkr_batch_size = args.wkr_batch_size

        self.total_concurrent_socket = self.num_concurrent_presocket+self.num_concurrent_postsocket

        self.port = args.port
        self.args = args
        self.transfer_protocol = args.protocol

        self.status_args = {k: v for k, v in sorted(vars(args).items())}
        self.status_static = {
            'python_version': sys.version,
            'server_version': __version__,
            'pyzmq_version': zmq.pyzmq_version(),
            'zmq_version': zmq.zmq_version(),
            'server_start_time': str(datetime.now()),
        }
        self.processes = []
        self.logdir = args.log_dir
        self.logger = set_logger(colored('NAVIGATOR', 'red'), logger_dir=self.logdir, verbose=args.verbose)
        self.logger.info('freeze, optimize and export graph, could take a while...')
        
        self.is_ready = threading.Event()

    def __enter__(self):
        self.start()
        self.is_ready.wait()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        self.logger.info('shutting down...')
        self._send_close_signal()
        self.is_ready.clear()
        self.join()

    @zmqd.context()
    @zmqd.socket(zmq.PUSH)
    def _send_close_signal(self, _, frontend):
        frontend.connect('tcp://localhost:%d' % self.port)
        frontend.send_multipart([b'', ServerCmd.terminate, b'', b''])

    @staticmethod
    def shutdown(args):
        with zmq.Context() as ctx:
            ctx.setsockopt(zmq.LINGER, args.timeout)
            with ctx.socket(zmq.PUSH) as frontend:
                try:
                    frontend.connect('tcp://%s:%d' % (args.ip, args.port))
                    frontend.send_multipart([b'', ServerCmd.terminate, b'', b''])
                    print('shutdown signal sent to %d' % args.port)
                except zmq.error.Again:
                    raise TimeoutError(
                        'no response from the server (with "timeout"=%d ms), please check the following:'
                        'is the server still online? is the network broken? are "port" correct? ' % args.timeout)

    def run(self):
        self._run()

    @zmqd.context()
    @zmqd.socket(zmq.PULL)
    @zmqd.socket(zmq.PAIR)
    @zmqd.socket(zmq.PAIR)
    @multi_socket(zmq.PUSH, num_socket='total_concurrent_socket')
    def _run(self, _, frontend, presink, sink, *backend_socks):

        backend_presocks = backend_socks[:self.num_concurrent_presocket]
        backend_postsocks = backend_socks[-self.num_concurrent_postsocket:]

        def push_new_job(client, req_id, msg):
            _sock = rand_backend_socket
            send_to_next(self.transfer_protocol, client, req_id, msg, _sock)
            # _sock.send_multipart([_job_id, _msg])

        # bind all sockets
        self.logger.info('bind all sockets')
        frontend.bind('tcp://*:%d' % self.port)
        addr_front2presink = auto_bind(presink)
        addr_front2postsink = auto_bind(sink)

        addr_backend_pre_list = [auto_bind(b) for b in backend_presocks]
        self.logger.info('open %d navigator-preprocess worker sockets' % len(addr_backend_pre_list))
        addr_backend_post_list = [auto_bind(b) for b in backend_postsocks]
        self.logger.info('open %d presink-main worker sockets' % len(addr_backend_post_list))

        # self, args, front_presink_addr, worker_address_list
        self.logger.info('start the pre-sink')
        proc_presink = WKRPreSink(self.args, addr_front2presink, addr_backend_post_list)
        self.processes.append(proc_presink)
        proc_presink.start()
        addr_presink = presink.recv().decode('ascii')
        addr_pre_post_sink = presink.recv().decode('ascii')

        # start the sink process
        self.logger.info('start the post-sink')
        proc_postsink = WKRSink(self.args, addr_front2postsink, addr_pre_post_sink, addr_backend_post_list)
        self.processes.append(proc_postsink)
        proc_postsink.start()
        addr_sink = sink.recv().decode('ascii')

        # start the pre-backend processes
        # TaceWorker: self, id, args, worker_address_list, sink_address, device_id
        self.logger.info('start pre-workers')
        device_map_preprocess = self._get_device_map(self.pre_num_worker, self.pre_device_map, self.pre_gpu_memory_fraction, run_all_cpu=self.pre_all_cpu)
        for idx, device_id in enumerate(device_map_preprocess):
            process = self.preprocessor_skeleton(idx, self.args, addr_backend_pre_list, addr_presink, device_id)
            self.processes.append(process)
            process.start()
            # process.is_ready.wait() # start model sequencely

        # start the post-backend processes
        # WaveWorker: self, id, args, worker_address_list, sink_address, device_id
        self.logger.info('start main-workers')
        device_map_main_worker = self._get_device_map(self.wkr_num_worker, self.wkr_device_map, self.wkr_gpu_memory_fraction, run_all_cpu=self.wkr_all_cpu)
        for idx, device_id in enumerate(device_map_main_worker):
            process = self.hardprocessor_skeleton(idx, self.args, addr_backend_post_list, addr_sink, device_id)
            self.processes.append(process)
            process.start()
            # process.is_ready.wait() # start model sequencely

        # start the http-service process
        if self.args.http_port:
            self.logger.info('start http proxy')
            proc_proxy = BertHTTPProxy(self.args)
            self.processes.append(proc_proxy)
            proc_proxy.start()

        rand_backend_socket = None
        server_status = ServerStatistic()

        for p in self.processes:
            p.is_ready.wait()

        self.is_ready.set()
        self.logger.info('all set, ready to serve request!')

        while True:
            try:
                request = frontend.recv_multipart()
                client, req_id, msg, msg_info = request
                # client, req_id, msg, msg_info = recv_from_prev(self.transfer_protocol, frontend)
                # request = [client, msg, req_id, msg_info]
            except (ValueError, AssertionError):
                self.logger.error('received a wrongly-formatted request (expected 4 frames, got %d)' % len(request))
                self.logger.error('\n'.join('field %d: %s' % (idx, k) for idx, k in enumerate(request)), exc_info=True)
            else:
                server_status.update(request)
                if msg == ServerCmd.terminate:
                    break
                elif msg == ServerCmd.show_config:
                    self.logger.info('new config request\treq id: %d\tclient: %s' % (int(req_id), client))
                    status_runtime = {'client': client.decode('ascii'),
                                      'num_process': len(self.processes),
                                      'navigator -> pre-worker': addr_backend_pre_list,
                                      'pre-worker -> pre-sink': addr_presink,
                                      'pre-sink -> post-worker': addr_backend_post_list,
                                      'post-worker -> sink': addr_sink,
                                      'navigator <-> pre-sink': addr_front2presink,
                                      'navigator <-> sink': addr_front2postsink,
                                      'pre-sink <-> sink': addr_pre_post_sink,
                                      'server_current_time': str(datetime.now()),
                                      'statistic': server_status.value,
                                      'preprocessor_device_map': device_map_preprocess,
                                      'preprocessor_batch_size': self.pre_batch_size,
                                      'main_device_map': device_map_main_worker,
                                      'main_batch_size': self.wkr_batch_size,
                                      'protocol': self.transfer_protocol,
                                      'num_concurrent_presocket': self.num_concurrent_presocket,
                                      'num_concurrent_postsocket': self.num_concurrent_postsocket,
                                      'total_concurrent_socket': self.total_concurrent_socket}
                    presink.send_multipart([client, msg, jsonapi.dumps({**status_runtime,
                                                                     **self.status_args,
                                                                     **self.status_static}), req_id])
                else:
                    self.logger.info('new encode request\treq id: %s\info: %s\tclient: %s' %
                                     (str(req_id), str(msg_info), client))

                    # regist job
                    presink.send_multipart([client, ServerCmd.new_job, msg_info, req_id])

                    # pick random socket
                    rand_backend_socket = random.choice([b for b in backend_presocks if b != rand_backend_socket])

                    info = jsonapi.loads(msg_info)
                    if self.transfer_protocol == 'obj':
                        msg = decode_object(msg, info)
                    else:
                        msg = decode_ndarray(msg, info)

                    # push job
                    push_new_job(client, req_id, msg)
                    # job_id = client + b'#' + req_id
                    # push_new_job(job_id, msg, msg_info)

        for p in self.processes:
            p.close()

        self.logger.info('terminated!')

    def _get_device_map(self, num_worker, device_map, per_process_gpu_fragment, run_all_cpu=False):
        self.logger.info('get devices map')
        run_on_gpu = False
        device_map = [-1] * num_worker
        if not run_all_cpu:
            try:
                import GPUtil
                num_all_gpu = len(GPUtil.getGPUs())
                avail_gpu = GPUtil.getAvailable(order='memory', limit=min(num_all_gpu, num_worker),
                                                maxMemory=0.9, maxLoad=0.9)
                num_avail_gpu = len(avail_gpu)
                if num_avail_gpu >= num_worker:
                    run_on_gpu = True
                elif 0 < num_avail_gpu < num_worker:
                    self.logger.warning('only %d out of %d GPU(s) is available/free, but "num_worker=%d"' %
                                        (num_avail_gpu, num_all_gpu, num_worker))
                    run_on_gpu = True
                else:
                    self.logger.warning('no GPU available, fall back to CPU')
                
                if run_on_gpu:
                    device_map = ((device_map or avail_gpu) * num_worker)[: num_worker]

            except FileNotFoundError:
                self.logger.warning('nvidia-smi is missing, often means no gpu on this machine. '
                                    'fall back to cpu!')
        
        self.logger.info('device map: \n\t\t%s' % '\n\t\t'.join(
            'worker %2d -> %s' % (w_id, ('gpu %2d' % g_id) if g_id >= 0 else 'cpu') for w_id, g_id in
            enumerate(device_map)))
        return device_map
