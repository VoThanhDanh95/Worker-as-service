import time
from wkr_serving.server import WKRServer, WKRHardWorker
from wkr_serving.server.helper import get_args_parser, import_tf

class Worker(WKRHardWorker):
    
    def get_env(self, device_id, tmp_dir):
        tf = import_tf(device_id=device_id)
        import numpy as np
        return [tf, np]
    
    def get_model(self, envs, model_dir, model_name, tmp_dir):
        tf, np = envs
        return np
    
    def predict(self, model, input):
        return input

if __name__ == "__main__":

    args = get_args_parser().parse_args([
        '-protocol', 'obj',
        '-model_dir', '/data1/ailabserver-models/face_service_models',
        '-model_name', 'mnet_double_10062019_tf19.pb',
        '-port_in', '8996',
        '-port_out', '8998',
        '-num_worker', '2',
        '-batch_size', '1',
        '-device_map', '-1',
        '-gpu_memory_fraction', '0.25'
    ])
    server = WKRServer(args, hardprocesser=Worker)

    # start server
    server.start()

    # join server
    server.join()
