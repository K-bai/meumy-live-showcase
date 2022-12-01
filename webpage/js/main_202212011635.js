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
        var dl = d.split("-")
        var ds = dl[0].substring(0, 4) + "-" + dl[0].substring(4, 6) + "-" + dl[0].substring(6, 8)
        if ( dl.length>1 ) ds = ds + "-" + dl[1]
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
1. 弹幕密度 包括总弹幕 打call 哈 草 问号(5s)
2. 分段弹幕热词(10s)
3. sc列表
4. 热词(数量最多)
    1. 全体观众
    2. 单推人（带牌子）
    3. 舰长
5. 推测可能的关键词(按直播的idf给出)
    1. 全体观众
6. 弹幕数
    1. 总体
    2. 单推人
    3. 舰长
7. 互动人数
    1. 总体
    2. 单推人
    3. 舰长
8. 发弹幕最多的前10人
9. 弹幕峰值时间
*/
function update_page(){
    //转化sc列表
    sc_data = []
    for (var i in all_data["sc_list"]){
        var t = all_data["sc_list"][i]["t"]
        sc_data.push([t, 0])
    }
    //主要图像
    density = data_transpose(all_data["density"]["x"], all_data["density"]["total"])
    keywords_density = data_transpose(all_data["density"]["x"], all_data["density"]["call"])
    haha_density = data_transpose(all_data["density"]["x"], all_data["density"]["haha"])
    fuck_density = data_transpose(all_data["density"]["x"], all_data["density"]["fuck"])
    problem_density = data_transpose(all_data["density"]["x"], all_data["density"]["problem"])
    hot_words = all_data["hot_words"]
    peak_lines = []
    if (show_peak_lines)
        for (var i in all_data["peaks"])
            peak_lines.push({xAxis: all_data["peaks"][i]})
    //获取直播开始时间
    live_start_time = moment(all_data["density"]["x"][0])
    draw()
    //转化热词列表用于搜索
    var hot_words_search_text = []
    for (i in hot_words){
        hot_words_search_text.push({t: hot_words[i][0], l: hot_words[i][1]})
    }
    hot_words_search = new Fuse(hot_words_search_text, {keys:["l"], includeScore: true, threshold: 0.2})


    //总热词、弹幕数、弹幕数、互动观众
    hot_words_switch()
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
    //录播跳转 在2022-01-08后呜米的录播跳转合集 在2022-02-24后咩栗的录播跳转合集
    let cur_date = app_data.date_n.split("-")[0]
    if (moment(cur_date).isAfter('2022-01-08') && app_data.vup_id === '22384516'){
        document.getElementById("jump_to_recording").href="https://space.bilibili.com/617459493/channel/seriesdetail?sid=379199&ctype=0"
    }
    else if (moment(cur_date).isAfter('2022-02-24') && app_data.vup_id === '8792912'){
        document.getElementById("jump_to_recording").href="https://space.bilibili.com/745493/channel/seriesdetail?sid=2060035"
    }
    else {
        document.getElementById("jump_to_recording").href="https://space.bilibili.com/674622242/video?keyword="+encodeURIComponent(moment(cur_date).format("YYYY年M月D日"))
    }
}

function data_transpose(x, y){
    //数据转置
    let rst = []
    for (let i in x)
        rst.push([x[i], y[i]])
    return rst
}

function search(){
    //热词搜索
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

function time_zero_change(){
    //时间零点改变
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

function get_sc_series(data){
    return {
        name: "superchat",
        type: "scatter",
        data: data,
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
        },
        markLine:{
            label:{
                show: false
            },
            symbol: "none",
            data: []
        }
    }
}

function get_default_series(data){
    return {
        name: '弹幕量',
        type: 'line',
        smooth: true,
        symbol: 'none',
        areaStyle: {},
        data: data
    }
}

function get_lined_series(data, description){
    return {
        name: description,
        type: 'line',
        smooth: true,
        symbol: 'none',
        data: data
    }
}

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
            "#C42E30"
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
                },
                min: 0,
                max: 120
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
        series: []
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
    if (app_data.vup_id == '22384516') option.color=["#C42E30"]
    else option.color=["#769CD2"]
    //设置数据
    option.series = [
        get_default_series([], '弹幕量'),
        get_default_series([], '打call'),
        get_lined_series([], '哈'),
        get_lined_series([], '草'),
        get_lined_series([], '?'),
        get_sc_series([])
    ]
    if (app_data.show_density=='all')
        option.series[0].data = density
    else if (app_data.show_density=='call')
        option.series[1].data = keywords_density
    else if (app_data.show_density=='haha')
        option.series[2].data = haha_density
    else if (app_data.show_density=='fuck')
        option.series[3].data = fuck_density
    else if (app_data.show_density=='problem')
        option.series[4].data = problem_density
    //显示峰值及醒目留言
    if (app_data.show_superchat) option.series[5].data = sc_data
    if (show_peak_lines) option.series[5].markLine.data = peak_lines
    console.log(option)
    myChart.setOption(option)
}

















/* 
工具函数
*/
function format_duration(t){
    var h = t.hours().toString()
    var m = t.minutes().toString()
    var s = t.seconds().toString()
    if (h.length == 1) { h = "0" + h }
    if (m.length == 1) { m = "0" + m }
    if (s.length == 1) { s = "0" + s }
    return h + ":" + m + ":" + s
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

function hot_words_switch(){
    //切换热词和关键词
    if (app_data.show_key_words){
        app_data.words_title = "弹幕关键词"
        app_data.all_hot_words = all_data["all_key_words"]
        app_data.all_hot_words.gachi = all_data["all_hot_words"]["gachi"]
        app_data.all_hot_words.captain = all_data["all_hot_words"]["captain"]
    }
    else{
        app_data.words_title = "观众最爱发的词"
        app_data.all_hot_words = all_data["all_hot_words"]
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
    show_key_words: false,
    show_density: 'all',
    words_title: "观众最爱发的词"
}
var app = new Vue({
    el: '#app',
    data: app_data
})






//初始化变量
var all_data = {}
var density = []
var keywords_density = []
var haha_density = []
var fuck_density = []
var problem_density = []
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
document.getElementById("show_key_words").onchange = hot_words_switch
document.getElementById("show_superchat").onchange = draw
document.getElementById("show_all_density").onchange = draw
document.getElementById("show_keywords_density").onchange = draw
document.getElementById("show_haha_density").onchange = draw
document.getElementById("show_fuck_density").onchange = draw
document.getElementById("show_problem_density").onchange = draw
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
