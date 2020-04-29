import os
import sys
import time
import requests

from wkr_serving.client import WKRWorker, WKRDecentralizeCentral
from wkr_serving.client import WKRClient

class AIModel(WKRWorker):

    # Create connection to service
    def get_model(self, ip, port, port_out):
        return WKRClient(ip=ip, port=port, port_out=port_out, ignore_all_checks=True)

    # Do the work loop, just 1 job at a time for efficiency
    def do_work(self, model, logger):
        try:
            # Step 1: get data, ex: from redis
            input = {'i': 1}
            # Step 2: model.encode
            result = model.encode(input)
            # Step 3: push result
            status = request.post(PUSH_API, json=result)

            if status.status_code == 200:
                logger.info('DONE job with input: {}'.format(input))
            else:
                raise Exception('Push result failed')
        except Exception as e:
            raise Exception("{}\nTHIS IS CUSTOM EXCEPTION for input: {}".format(e, input))

    # close model connection to service
    def off_model(self, model):
        model.close()

if __name__ == "__main__":
    from tts_serving.client.helper import get_args_parser
    SERVICE_PUSH_PORT = 8066
    SERVICE_PULL_PORT = 8068
    args = get_args_parser().parse_args(['-port', '21324',
                                        '-port_out', '21326',
                                        '-num_client', '24',
                                        '-remote_servers', '[["0.0.0.0", {}, {}]]'.format(SERVICE_PUSH_PORT, SERVICE_PULL_PORT),
                                        '-log_dir', '/data/log/tts_central_staging'])
    handler = WKRDecentralizeCentral(AIModel, args)
    handler.start()