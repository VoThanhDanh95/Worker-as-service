import time
from wkr_serving.server import WKRServer, WKRHardWorker
from wkr_serving.server.helper import get_args_parser, import_tf

class Worker(WKRHardWorker):
    
    def get_env(self, device_id, tmp_dir):
        tf = import_tf(device_id=device_id)
        import numpy as np

        info_logger = self.new_logger()
        error_logger = self.new_logger(error_logger=True)

        return [tf, np, info_logger, error_logger]
    
    def get_model(self, envs, model_dir, model_name, tmp_dir):
        tf, np, info_logger, error_logger = envs

        info_logger.info("Begin load model")
        try:
            # load model
            pass
        except Exception as e:
            error_logger.error("Load model error")

        return model, info_logger, error_logger
    
    def predict(self, model, input):
        model, info_logger, error_logger = model
        
        info_logger.info("Processing input: {}".format(input))

        start_process = time.time()
        # preprocess
        done_preprocess = time.time()
        # predict
        done_predict = time.time()

        info_logger.info("DONE input: {}".format(input))

        # log statistic number
        self.record_statistic({
            'preprocess': (done_preprocess-start_process)*1000/len(input),
            'predict': (done_predict-done_preprocess)*1000/len(input),
            'batchsize': len(input)
        })

        return result

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
