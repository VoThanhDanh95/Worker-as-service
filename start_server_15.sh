# # max len 80
# cd /data/tts_as_service_sockets/; \
# wkr-serving-start \
# -port_in=8066 \
# -port_out=8068 \
# -http_port=9006 \
# -http_stat_dashboard=/zserver/AI-projects/AILab/synthersize-as-service/plugin/dashboard \
# -model_dir=/data/ailabserver-models/viettts_singlevoice \
# -tacotron_model_name=TrangTay-BN-04-18-2019-tf18.pb \
# -tacotron_config_name=tacotron_modelsb/small.tacotron.upper.json.trangtay.v70 \
# -waveglow_model_name=waveglow_local_1010000.pth \
# -waveglow_config_name=waveglow.config.json \
# -tac_num_worker=3  \
# -tac_batch_size=16 \
# -target_max_seq_len=150 \
# -tac_device_map 1 7 0 \
# -tac_batch_group_timeout=20 \
# -tac_gpu_memory_fraction=0.25 \
# -wav_num_worker=8 \
# -wav_device_map 1 7 1 7 0 7 0 1 \
# -mel_lens 200 250 250 300 300 300 150 350 \
# -wav_batch_size=1 \
# -wav_gpu_memory_fraction=0.25 \
# -log_dir /data/log/tts_service_baomoi

# max len 120
cd /data/tts_as_service_sockets/; \
wkr-serving-start \
-port_in=8066 \
-port_out=8068 \
-http_port=9006 \
-http_stat_dashboard=/zserver/AI-projects/AILab/synthersize-as-service/plugin/dashboard \
-model_dir=/data/ailabserver-models/viettts_singlevoice \
-tacotron_model_name=TrangTay-BN-04-18-2019-tf18.pb \
-tacotron_config_name=tacotron_modelsb/small.tacotron.upper.json.trangtay.v70 \
-waveglow_model_name=waveglow_local_1010000.pth \
-waveglow_config_name=waveglow.config.json \
-tac_num_worker 3 \
-tac_batch_size 8 \
-tac_batch_size_cpu 4 \
-target_max_seq_len 120 \
-target_min_seq_len 80 \
-tac_device_map 1 7 0 \
-tac_batch_group_timeout=20 \
-tac_gpu_memory_fraction=0.25 \
-wav_num_worker=8 \
-wav_device_map 0 0 1 1 7 7 1 7 \
-mel_lens 250 400 300 350 350 250 400 400 \
-wav_batch_size=1 \
-wav_gpu_memory_fraction=0.25 \
-log_dir /data/log/tts_service_baomoi