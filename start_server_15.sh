cd /data/worker_as_service_socket/; \
wkr-serving-start \
-protocol obj \
-model_dir=/data/worker_as_service \
-model_name=frozen_inference_graph.pb \
-port_in=8770 \
-port_out=8772 \
-num_worker 2 \
-batch_size 1 \
-device_map 1 \
-gpu_memory_fraction=0.25