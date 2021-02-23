"use strict"
/* 
数据加载
*/

//读取文件列表
function read_file_list(){
    var client = new XMLHttpRequest()
    client.onreadystatechange = function () {
        if (this.readyState == 4 && this.status == 200 && this.response != null) {
            file_list = this.response
            fresh_selection()
        }
    }
    client.responseType = "json"
    client.open("GET", "data/list.json")
    client.setRequestHeader("Cache-Control","no-cache")
    client.send()
}
//更新选择列表
function fresh_selection() {
    //解释选项
    app_data.date_list = []
    for (var i in file_list[app_data.vup_id]) {
        var d = file_list[app_data.vup_id][i]["d"]
        var ds = d.substring(0, 4) + "-" + d.substring(4, 6) + "-" + d.substring(6, 8)
        app_data.date_list.push({str: ds, val: d})
        //切到最新一天
        app_data.date_n = app_data.date_list[0].val
    }
    //加载并绘图
    load_data()
}

//读取数据文件
function load_data() {
    //当前文件
    var current_file = app_data.vup_id.toString() + "-" + app_data.date_n + ".json"
    //加载文件并绘图
    var client = new XMLHttpRequest()
    client.onreadystatechange = function () {
        if (this.readyState == 4 && this.status == 200 && this.response != null) {
            all_data = this.response        
            //更新页面
            update_page()
            document.getElementById('loading_icon').hidden = true
        }
    }
    client.responseType = "json"
    client.open("GET", "data/" + current_file)
    client.setRequestHeader("Cache-Control","no-cache")
    client.send()
    document.getElementById('loading_icon').hidden = false
}





















//根据数据更新页面
/*
生成网页可用的数据集
1. 弹幕密度(5s)
2. 分段弹幕热词(10s)
3. sc列表
4. 热词
    1. 全体观众
    2. 单推人（带牌子）
    3. 舰长
5. 弹幕数
    1. 总体
    2. 单推人
    3. 舰长
6. 互动人数
    1. 总体
    2. 单推人
    3. 舰长
7. 发弹幕最多的前10人
*/
function update_page(){
    //转化sc列表
    sc_data = []
    for (var i in all_data["sc_list"]){
        var t = all_data["sc_list"][i]["t"]
        sc_data.push([t, 0])
    }
    //主要图像
    density = all_data["density"]
    keywords_density = all_data["keywords_density"]
    hot_words = all_data["hot_words"]
    peak_lines = []
    if (show_peak_lines)
        for (var i in all_data["peaks"])
            peak_lines.push({xAxis: all_data["peaks"][i]})
    //获取直播开始时间
    live_start_time = moment(all_data["density"][0][0])
    draw()
    //转化热词列表用于搜索
    var hot_words_search_text = []
    for (i in hot_words){
        hot_words_search_text.push({t: hot_words[i][0], l: hot_words[i][1]})
    }
    hot_words_search = new Fuse(hot_words_search_text, {keys:["l"], includeScore: true, threshold: 0.2})


    //总热词、弹幕数、弹幕数、互动观众
    app_data.all_hot_words = all_data["all_hot_words"]
    app_data.danmu_count = all_data["danmu_count"]
    app_data.interact_count = all_data["interact_count"]
    app_data.most_interact = all_data["most_interact"]
    //峰值列表
    var peaks = []
    for (var i in all_data["peaks"]){
        var t = all_data["peaks"][i]
        peak_lines.push({xAxis: t})
        var word_list = find_hot_words(t)
        peaks.push({time_raw: t, time: set_display_time(t), words: word_list.join(" ")})
    }
    app_data.peaks = peaks
    //sc列表
    var superchats = []
    for (var i in all_data["sc_list"]){
        var sc = all_data["sc_list"][i]
        superchats.push({
            time_raw: sc["t"], 
            time: set_display_time(sc["t"]), 
            name: sc["u"],
            price: sc["p"],
            content: sc["c"]
        })
    }
    app_data.superchat_list = superchats
    //更新直播开始时间
    document.getElementById("live_start_time_form").classList.remove('was-validated')
    document.getElementById("live_start_time").oninput = null
    document.getElementById("live_start_time").value = live_start_time.format("HH:mm:ss")
    document.getElementById("live_start_time").oninput = validate_time
    //录播跳转
    document.getElementById("jump_to_recording").href="https://space.bilibili.com/674622242/video?keyword="+encodeURIComponent(moment(app_data.date_n).format("YYYY年M月D日"))

}

//热词搜索
function search(){
    var query_text = app_data.search_query
    //搜索
    var result = hot_words_search.search(query_text)
    var search_results = []
    for (var i in result){
        var t = result[i]["item"]["t"]
        search_results.push({time_raw: t, time: set_display_time(t), words: result[i]["item"]["l"].join(" ")})
    }
    app_data.search_results = search_results
    //显示列表
    var container = document.getElementById('search_result_container')
    var bsCollapse = new bootstrap.Collapse(container,{toggle: false})
    bsCollapse.show()
}
//时间零点改变
function time_zero_change(){
    for (var i in app_data.search_results)
        app_data.search_results[i].time = set_display_time(app_data.search_results[i].time_raw)
    for (var i in app_data.peaks)
        app_data.peaks[i].time = set_display_time(app_data.peaks[i].time_raw)
    for (var i in app_data.superchat_list)
        app_data.superchat_list[i].time = set_display_time(app_data.superchat_list[i].time_raw)
    draw()
}








/* 
绘图相关函数
*/

//初始化图表
function draw_init() {
    var option = {
        title: {
            left: 'center',
            text: '弹幕热度与热词',
        },
        grid: {
            left: 30,
            right: "5%"
        },
        color: [
            "#D62D2D"
        ],
        tooltip: {
            trigger: "axis",
            formatter: function (p) { return set_tooltip(p, false) },
        },
        toolbox: {
            feature: {
                saveAsImage: {}
            }
        },
        xAxis: {
            type: 'value',
            min: "dataMin",
            max: "dataMax",
            boundaryGap: false,
            minInterval: 1000*20,
            splitLine:{
                show: false
            }
        },
        yAxis: [
            {
                type: 'value',
                boundaryGap: [0, '10%'],
                axisLine:{
                    show: true
                },
                axisTick:{
                    show: false
                }
            },
            {
                type: 'value',
                min: -1,
                max: 0.1,
                show: false
            },
        ],
        media: [
            {
                query: {
                    minWidth: 650,
                },
                option: {
                    dataZoom: [
                        {
                            type: 'inside',
                            moveOnMouseMove: false,
                            start: 0,
                            end: 100
                        },
                        {
                            type: 'slider',
                            brushSelect: false,
                            start: 0,
                            end: 100,
                            showDetail: false,
                            handleIcon: "none",
                        }
                    ],
                    tooltip: {
                        triggerOn: 'mousemove'
                    }
                }
            },
            {
                query: {
                    maxWidth: 650,
                },
                option: {
                    dataZoom: [
                        {
                            type: 'inside',
                            moveOnMouseMove: true,
                            start: 0,
                            end: 100
                        },
                        {
                            type: 'slider',
                            show: false
                        }
                    ],
                    xAxis: {
                        axisPointer: {
                            snap: true,
                            handle: {
                                show: true,
                                color: '#ffffff',
                                margin: 30
                            }
                        }
                    },
                    tooltip: {
                        triggerOn: 'click'
                    }
                }
            },
        ],
        series: [
            {
                name: '弹幕量',
                type: 'line',
                smooth: true,
                symbol: 'none',
                areaStyle: {},
                data: density,
                markLine:{
                    label:{
                        show: false
                    },
                    symbol: "none",
                    data: peak_lines
                }
            },
            {
                name: "superchat",
                type: "scatter",
                data: sc_data,
                yAxisIndex: 1,
                symbolSize: 15,
                tooltip: {
                    trigger: "item",
                    formatter: function(p){return set_tooltip_sc(p)},
                    confine: true,
                    extraCssText: 'max-width: 300px word-wrap:break-word white-space: normal'
                },
                itemStyle:{
                    color: function(p){return get_sc_color(p.value[0])},
                    opacity: 0.5
                }
            }
        ]
    }

    // 使用刚指定的配置项和数据显示图表。
    myChart.setOption(option)
}

//主要绘图
function draw() {
    var option = {xAxis:{axisLabel:{}}}
    //设置横轴
    if (app_data.use_live_time) {
        option.xAxis.axisLabel.formatter = function (value) {
            var t = moment.duration(moment(value).diff(live_start_time))
            return format_duration(t)
        }
    }
    else {
        option.xAxis.axisLabel.formatter = function (value) {
            return moment(value).format("HH:mm:ss")
        }
    }
    //设置颜色
    if (app_data.vup_id == '22384516') option.color=["#D62D2D"]
    else option.color=["#A888C5"]
    //设置数据
    if (app_data.show_keywords_density) 
        option.series = [{ data: keywords_density, markLine: { data: [] } }, { data: [] }]
    else
        option.series = [{ data: density, markLine: { data: [] } }, { data: [] }]
    //显示峰值及醒目留言
    if (show_peak_lines) option.series[0].markLine.data = peak_lines
    if (app_data.show_superchat) option.series[1].data = sc_data
    myChart.setOption(option)
}

















/* 
工具函数
*/
function format_duration(t){
    var m = Math.floor(t.asMinutes()).toString()
    var s = t.seconds().toString()
    if (m.length == 1) { m = "0" + m }
    if (s.length == 1) { s = "0" + s }
    return m + ":" + s
}
function set_display_time(t) {
    // 设置显示时间
    if (app_data.use_live_time) {
        var d = moment.duration(moment(t).diff(live_start_time))
        return format_duration(d)
    }
    else {
        return moment(t).format("HH:mm:ss")
    }
}
function find_hot_words(t){
    // 查找最邻近的热词
    var word_list = hot_words[hot_words.length - 1][1]
    var last_sub = Math.abs(hot_words[0][0] - t)
    for (var i = 1; i < hot_words.length; i++) {
        var sub = Math.abs(hot_words[i][0] - t)
        if (sub >= last_sub) {
            word_list = hot_words[i - 1][1]
            break
        }
        last_sub = sub
    }
    return word_list
}
function set_tooltip(p) {
    // 查找热词
    var t = p[0].value[0]
    var word_list = find_hot_words(t)
    var output = "<strong>时间: " + set_display_time(t) + "<br />弹幕热词: </strong><br />"
    return output + word_list.join("<br />")
}
function set_tooltip_sc(p) {
    //查找sc内容
    for (var i in all_data["sc_list"]){
        var t = all_data["sc_list"][i]["t"]
        if (p.value[0] == t){
            return "<strong>时间: "+set_display_time(p.value[0])+"<br />醒目留言: </strong><br />"+all_data["sc_list"][i]["u"]+": ￥"+all_data["sc_list"][i]["p"].toString()+"<br />"+all_data["sc_list"][i]["c"]
        }
    }
}
function get_sc_color(sc_time){
    //查找sc颜色
    var sc_c = null
    for (var i in all_data["sc_list"]){
        var t = all_data["sc_list"][i]["t"]
        if (sc_time == t){
            var price = all_data["sc_list"][i]["p"]
            for (var j in sc_colors[0]){
                if (sc_colors[0][j] > price){
                    sc_c = sc_colors[1][j]
                    break
                }
            }
        }
    }
    if (sc_c) return "rgb("+sc_c[0].toString()+", "+sc_c[1].toString()+", "+sc_c[2].toString()+")"
    else return "rgb(0,0,0)"
}

//验证更新时间
function validate_time() {
    var live_time_d = document.getElementById("live_start_time")
    live_time_d.setCustomValidity("")
    var live_time_s = live_time_d.value
    var live_time_l = live_time_s.split(/[:：]/)
    if (live_time_l.length != 3){
        live_time_d.setCustomValidity('Wrong format.')
        return
    }
    for (var i in live_time_l){
        if (/^\d{1,2}$/.test(live_time_l[i]) == false){
            live_time_d.setCustomValidity('Wrong format.')
            return
        }
    }
    live_time_l[0] = parseInt(live_time_l[0])
    live_time_l[1] = parseInt(live_time_l[1])
    live_time_l[2] = parseInt(live_time_l[2])
    if (live_time_l[0]<0 || live_time_l[0]>=24 || live_time_l[1]<0 || live_time_l[1]>=60 || live_time_l[2]<0 || live_time_l[2]>=60){
        live_time_d.setCustomValidity('Wrong format.')
        return
    }
    //更改开始时间 绘图
    live_start_time.hour(live_time_l[0])
    live_start_time.minute(live_time_l[1])
    live_start_time.second(live_time_l[2])
    if(app_data.use_live_time){
        draw()
        time_zero_change()
    }
}



var app_data = {
    date_list: [
        {str: '2021-01-30', val: 20210130}
    ],
    date_n: 20210130,
    vup_id: '22384516',
    all_hot_words: {
        all: ['???','???','???','???','???','???','???','???','???','???'],
        captain: ['???','???','???','???','???','???'],
        gachi: ['???','???','???','???','???','???']
    },
    danmu_count: {
        all: '???',
        captain: '???',
        gachi: '???'
    },
    interact_count: {
        all: '???',
        captain: '???',
        gachi: '???'
    },
    most_interact: [
        ['???', '???'],['???', '???'],['???', '???'],['???', '???'],['???', '???'],['???', '???'],['???', '???'],['???', '???'],['???', '???'],['???', '???']
    ],
    peaks: [
        {time_raw: 0, time: '00:00:00', words: 'loading...'}
    ],
    superchat_list: [
        {time_raw: 0, time: '00:00:00', name: 'Octave', price: 0, content: 'loading...'}
    ],
    search_results: [],
    search_query: '',
    use_live_time: false,
    show_superchat: false,
    show_keywords_density: false
}
var app = new Vue({
    el: '#app',
    data: app_data
})






//初始化变量
var all_data = {}
var density = []
var keywords_density = []
var hot_words = []
var hot_words_search = null
var sc_data = []
var peak_lines = []
var file_list = {}
var live_start_time = 0
var show_peak_lines = false
var sc_colors = [[50,100,500,1000,999999999],[[0,183,212],[0,190,165],[255,179,0],[244,91,0],[207,0,0]]]
var myChart = echarts.init(document.getElementById('main_chart'))
//注册事件
document.getElementById("vup_list").onchange = fresh_selection
document.getElementById("date_list").onchange = load_data
document.getElementById("use_live_time").onchange = time_zero_change
document.getElementById("show_superchat").onchange = draw
document.getElementById("show_keywords_density").onchange = draw
document.getElementById("search_button").onclick = search
document.getElementById("toggle_search_result").onclick = function() {
    var container = document.getElementById('search_result_container')
    var bsCollapse = new bootstrap.Collapse(container)
}
document.getElementById("live_start_time").onfocus = function(){
    document.getElementById("live_start_time_form").classList.add('was-validated')
}
document.getElementById('query_text').onkeyup = function(event){
    if ( event.key == "Enter" ){
        document.getElementById("search_button").focus()
        search()
    }
}
document.getElementById('peak_list_container').addEventListener('hidden.bs.collapse', function () {
    show_peak_lines = false
    draw()
})
document.getElementById('peak_list_container').addEventListener('shown.bs.collapse', function () {
    show_peak_lines = true
    draw()
})


//读文件列表
read_file_list()
//初始化图表
draw_init()
