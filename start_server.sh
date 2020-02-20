cd /tmp; \
wkr-serving-start \
-protocol obj \
-model_dir=/data6/worker_as_service \
-model_name=frozen_inference_graph.pb \
-port_in=8070 \
-port_out=8072 \
-http_stat_dashboard=/home/zdeploy/AILab/duydv2/worker-as-service/plugin/dashboard \
-num_worker 2 \
-batch_size 1 \
-device_map 1 \
-gpu_memory_fraction=0.25