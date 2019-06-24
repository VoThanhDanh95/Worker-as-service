cd /tmp; \
wkr-serving-start \
-protocol obj \
-model_dir=/data6/worker_as_service \
-pre_model_name=none \
-wkr_model_name=frozen_inference_graph.pb \
-port_in=8070 \
-port_out=8072 \
-http_stat_dashboard=/home/zdeploy/AILab/duydv2/worker-as-service/plugin/dashboard \
-pre_num_worker=1 \
-pre_batch_size=1 \
-pre_device_map -1 \
-wkr_num_worker 1 \
-wkr_batch_size 1 \
-wkr_device_map 1 \
-wkr_gpu_memory_fraction=0.25 \
# -log_dir /data6/worker_as_service/logs
# -http_port=12010 \