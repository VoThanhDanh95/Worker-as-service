Vue.use(VueCharts);

var refreshTime = 10;

function logic_device(logic, total_device) {
    if (logic == 0) return 'CPU';
    if (logic>0) {
        if (logic == total_device) return 'GPU'
    }
    return 'CPU & GPU'
}

function getSum(total, num) {
    return total + num;
}

const vm = new Vue({
    el: '#mrc-ui',
    data: {
        serverUrl: '/',
        apiRoute: '/status/server',
        results: [],
        top_deck: [],
        second_deck: [],
        tacotron_deck: [],
        tacotron_deck_second: [],
        waveglow_deck: [],
        waveglow_deck_second: [],
        waveglow_decks_queues: [],
        waveglow_decks_queues_stat: [],
        hist_num_request: {
            'last': -1,
            'value': [],
            'label': []
        },
        hist_num_response: {
            'last': -1,
            'value': [],
            'label': []
        },
        hist_num_client: {
            'last': -1,
            'value': [],
            'label': []
        },
        hist_tacotron_util: {
            'last': -1,
            'value': [],
            'label': []
        },
        hist_waveglow_util: {
            'last': -1,
            'value': [],
            'label': []
        },
        max_num_points: 360
    },
    mounted: function () {
        this.$nextTick(function () {
            this.refreshDatabase();
        })
    },
    computed: {
        runningTime: function () {
            return moment(this.results.server_start_time).fromNow()
        }
    },
    methods: {
        histTacoValues: function (long) {
            return this.hist_tacotron_util.value.slice(-(long ? this.max_num_points : 60))
        },
        histTacoLabels: function (long) {
            return this.hist_tacotron_util.label.slice(-(long ? this.max_num_points : 60))
        },

        histWaveValues: function (long) {
            return this.hist_waveglow_util.value.slice(-(long ? this.max_num_points : 60))
        },
        histWaveLabels: function (long) {
            return this.hist_waveglow_util.label.slice(-(long ? this.max_num_points : 60))
        },

        histReqLabels: function (long) {
            var req = this.hist_num_request.label.slice(-(long ? this.max_num_points : 60))
            var c = req.map(function(e, i) {
                return i;
            });
            return req
        },
        histReqValues: function (long) {
            return this.hist_num_request.value.slice(-(long ? this.max_num_points : 60))
        },

        histResLabels: function (long) {
            var res = this.hist_num_response.label.slice(-(long ? this.max_num_points : 60))
            var c = res.map(function(e, i) {
                return i;
            });
            return res
        },
        histResValues: function (long) {
            return this.hist_num_response.value.slice(-(long ? this.max_num_points : 60))
        },

        histReqResLabels: function (long) {
            return this.hist_num_response.label.slice(-(long ? this.max_num_points : 60))
        },
        histReqResValues: function (long) {
            var req = this.hist_num_request.value.slice(-(long ? this.max_num_points : 60));
            var res = this.hist_num_response.value.slice(-(long ? this.max_num_points : 60));
            var req_dataset= {
                                fill: false,
                                borderColor: "#e83e8c",
                                data: req,
                            }
            var res_dataset= {
                                fill: false,
                                borderColor: "#fd7e14",
                                data: res,
                            }
            ress = [req_dataset, res_dataset]
            console.log(ress)
            return ress
        },

        histClientLabels: function (long) {
            return this.hist_num_client.label.slice(-(long ? this.max_num_points : 60))
        },
        histClientValues: function (long) {
            return this.hist_num_client.value.slice(-(long ? this.max_num_points : 60))
        },

        refreshDatabase: function () {
            $.ajax({
                url: this.apiRoute,
                dataType: 'text',
                cache: false,
                beforeSend: function () {
                    // console.log("Loading");
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    console.log(jqXHR);
                    console.log(textStatus);
                    console.log(errorThrown);
                },
                success: function (data) {
                    vm.results = JSON.parse(data);
                    // console.log(data)

                    vm.first_deck = [];
                    vm.second_deck = [];
                    vm.tacotron_deck = [];
                    vm.tacotron_deck_second = [];
                    vm.waveglow_deck = [];
                    vm.waveglow_deck_second = [];
                    vm.waveglow_decks_queues = [];
                    vm.waveglow_decks_queues_stat = [];

                    vm.addNewTimeData(vm.hist_num_request, vm.results.statistic.num_data_request-1, true, refreshTime);
                    vm.addNewTimeData(vm.hist_num_client, vm.results.statistic.num_total_client, false);
                    vm.addNewTimeData(vm.hist_num_response, vm.results.statistic_postsink.num_data_request, true, refreshTime);

                    vm.addNewTimeData(vm.hist_tacotron_util, vm.results.statistic_presink.util, false);
                    vm.addNewTimeData(vm.hist_waveglow_util, vm.results.statistic_postsink.util, false);

                    // add to top deck, high priority
                    
                    vm.addToDeck('Last Rq/S', parseInt(vm.hist_num_request['value'].slice(-1)[0]*1000)/1000, vm.first_deck, false);
                    
                    vm.addToDeck('Last Rp/S', parseInt(vm.hist_num_response['value'].slice(-1)[0]*1000)/1000, vm.first_deck, false);
                    vm.addToDeck('Serving', vm.results.statistic.num_data_request-vm.results.statistic_postsink.num_data_request-1, vm.first_deck);
                    
                    // other dynamic stat to the second deck
                    vm.addToDeck('Request', vm.results.statistic.num_data_request-1, vm.second_deck);
                    vm.addToDeck('Response', vm.results.statistic_postsink.num_data_request, vm.second_deck);
                    vm.addToDeck('Sys call.', vm.results.statistic.num_sys_request, vm.second_deck);
                    // vm.addToDeck('Avg Rq/S', parseInt(vm.results.statistic.avg_request_per_second*1000)/1000, vm.second_deck);
                    // vm.addToDeck('Avg Rp/S', parseInt(vm.results.statistic_postsink.avg_request_per_second*1000)/1000, vm.second_deck);

                    // mostly constant stat to the third deck
                    vm.addToDeck('Server version', vm.results.server_version, vm.second_deck);
                    vm.addToDeck('Uptime', vm.runningTime, vm.second_deck);

                    // tacotron info
                    var taco_total_device = vm.results.tacotron_device_map.length
                    vm.addToDeck('Workers', taco_total_device, vm.tacotron_deck_second);
                    vm.addToDeck('Batch size', vm.results.tacotron_batch_size, vm.tacotron_deck_second);
                    var logic_taco_device = vm.results.tacotron_device_map.map(x => x>=0?1:0).reduce(getSum);
                    // vm.addToDeck('Running on', logic_device(logic_taco_device, taco_total_device) + ' [' + vm.results.tacotron_device_map + ']', vm.tacotron_deck_second);
                    vm.addToDeck('Running on', '[' + vm.results.tacotron_device_map + ']', vm.tacotron_deck_second);

                    vm.addToDeck('Util', parseInt(vm.results.statistic_presink.util*100) + '%', vm.tacotron_deck);
                    vm.addToDeck('Job left', vm.results.statistic_presink.total_job_in_queue, vm.tacotron_deck);
                    
                    // waveglow info
                    var wave_total_device = vm.results.waveglow_device_map.length
                    vm.addToDeck('Workers', wave_total_device, vm.waveglow_deck_second);
                    vm.addToDeck('Batch size', vm.results.waveglow_batch_size, vm.waveglow_deck_second);
                    var logic_wave_device = vm.results.waveglow_device_map.map(x => x>=0?1:0).reduce(getSum);
                    // vm.addToDeck('Running on', logic_device(logic_wave_device, wave_total_device) + '[' + vm.results.waveglow_device_map + ']', vm.waveglow_deck_second);
                    vm.addToDeck('Running on', '[' + vm.results.waveglow_device_map + ']', vm.waveglow_deck_second);

                    vm.results.allocated_mel_lens.forEach(mel_len => {
                        var index = ''+vm.results.allocated_mel_lens.indexOf(mel_len);
                        var util = 0;
                        var total_serve = 0;
                        var stat = vm.results.statistic_postsink
                        if (index in stat.total_socket_job_in_queue) {
                            util = parseInt(stat.total_socket_job_in_queue[index]*100/stat.maximum_socket_job_in_queue[index])
                            total_serve = parseInt(stat.total_socket_proccessed_job[index])
                        }
                        vm.addToDeck('' + mel_len, ''+util+'%', vm.waveglow_decks_queues);
                        vm.addToDeck('' + mel_len, ''+total_serve, vm.waveglow_decks_queues_stat);
                    });

                    vm.addToDeck('Util', parseInt(vm.results.statistic_postsink.util*100) + '%', vm.waveglow_deck);
                    vm.addToDeck('Job left', vm.results.statistic_postsink.total_job_in_queue, vm.waveglow_deck);
                },
                complete: function () {
                    // console.log('Finished all tasks');
                }
            });
        },
        addToDeck: function (text, value, deck, round) {
            round = typeof round !== 'undefined' ? round : true;
            round = (!isNaN(parseFloat(value)) && isFinite(value)) ? round : false;
            deck.push({'text': text, 'value': round ? Math.round(value) : value})
        },
        addNewTimeData: function (ds, new_val, delta, scale) {
            scale = typeof scale !== 'undefined' ? scale : 1;

            if (ds.last >= 0)
                ds.value.push((new_val - (delta ? ds.last : 0))/scale);
            else
                ds.value.push(0);
            ds.last = new_val;
            ds.label.push(moment().format('h:mm:ss'));
            if (ds.label.length > vm.max_num_points) {
                ds.label = ds.label.slice(-vm.max_num_points);
                ds.value = ds.value.slice(-vm.max_num_points)
            }
        }
    }
});


setInterval(function () {
    vm.refreshDatabase();
    // console.log('update database!')
}, refreshTime * 1000);
