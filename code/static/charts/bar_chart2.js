async function barChart2() {
  controller.abort();
  while(functionIsRunning){
    await new Promise((resolve) => setTimeout(resolve, 50));
    if (!controller.signal.aborted){
      return;
    }
  }
  functionIsRunning = true;
  controller = new AbortController();
  var bC = document.getElementById("barChart2");
  bC.style.display = "block";
  document.getElementById("barChart3").style.display = "none";
  document.getElementById("stackedBarChart").style.display = "none";
  document.getElementById("calendarChart").style.display = "none";
  document.getElementById("lineChart").style.display = "none";
  document.getElementById("lineChart2").style.display = "none";
  document.getElementById("radarChart").style.display = "none";
  document.getElementById("radarChart2").style.display = "none";
  document.getElementById("radarChart3").style.display = "none";
  document.getElementById("barPieChart").style.display = "none";
  document.getElementById("tableDiv").style.display = "none";
  document.getElementById("loadingScreen").style.display = "none";
  if (barChart2Instance !== null) {
    barChart2Instance.dispose();
  }
  document.querySelector(".card-title").innerHTML =
    "Confronto Politici <span>/Grafico a Barre</span>";
  if (
    $("#select_pol").val()[0] == undefined ||
    $("#select_pol").val()[0] == ""
  ) {
    document.querySelector(".card-title").innerHTML =
      "Confronto Politici <span>/Grafico a Barre<br><br> You need to select at least a politician/political group to use this chart</span>";
    functionIsRunning = false;
    return 0;
  }
  barChart2Instance = echarts.init(bC);
  barChart2Instance.showLoading();
  const p = document.getElementById("politician");
  const pg = document.getElementById("political_group");
  if (p.checked == true) {
    var t = "/v1/politician-topics/";
  } else if (pg.checked == true) {
    var t = "/v1/political-group-topics/";
  } else {
    functionIsRunning = false;
    return 0;
  }
  var final_values = [];
  var politicians = [];
  var url_c = "";
  var url_p = "";
  var url_t = "";
  var url_a = "";
  if (
    $("#select_channels").val()[0] != undefined &&
    $("#select_channels").val()[0] != ""
  ) {
    url_c += `&channel_=${encodeURIComponent($("#select_channels").val()[0])}`;
  }
  if (
    $("#select_programs").val()[0] != undefined &&
    $("#select_programs").val()[0] != ""
  ) {
    url_p += `&program_=${encodeURIComponent($("#select_programs").val()[0])}`;
  }
  if (
    $("#select_topics").val()[0] != undefined &&
    $("#select_topics").val()[0] != ""
  ) {
    url_t += `&topic_=${encodeURIComponent($("#select_topics").val()[0])}`;
  }
  if (
    $("#select_affiliations").val()[0] != undefined &&
    $("#select_affiliations").val()[0] != ""
  ) {
    url_a += `&affiliation_=${encodeURIComponent(
      $("#select_affiliations").val()[0]
    )}`;
  }
  const selectedValues = $("#select_pol").val();
  var total_minutes = 0;
  for (const value of selectedValues) {
    var i = 1;
    var values = [];
    const baseUrl =
      t +
      value +
      "?start_date_=" +
      start_date.value.replace(/-/g, "%2F") +
      "&end_date_=" +
      end_date.value.replace(/-/g, "%2F") +
      "&kind_=" +
      cb +
      url_a +
      url_c +
      url_p +
      url_t;

    while (true) {
      if (controller.signal.aborted) {
        functionIsRunning = false;
        return;
      }
      var url = `${baseUrl}&page=${i}`;
      i++;
      const data = await fetchData(url);
      if (!data || data.topics.length == 0) {
        break;
      } else {
        const lengthData = data.topics.length;
        while (data.topics.length > 0) {
          let popped_topic = data.topics.shift();
          values.push(popped_topic);
          total_minutes += popped_topic.minutes;
        }
        if (lengthData < data.page_size){
          break;
        }
      }
    }
    politicians.push(value);
    final_values.push(values);
  }
  if (total_minutes == 0) {
    document.querySelector(".card-title").innerHTML =
      "Charts <span>/Bar + Pie Chart</span> <br><br> NO DATA FOUND";
    barChart2Instance.hideLoading();
    functionIsRunning = false;
    return 0;
  }
  var topics = [];
  final_values.forEach((v) => {
    var t = [];
    v.forEach((x) => {
      t.push(x["topic"]);
    });
    topics = t;
  });
  var series = [];
  final_values.forEach((v, index) => {
    var m = [];
    v.forEach((x) => {
      m.push(x["minutes"]);
    });
    series.push({ name: politicians[index], type: "bar", data: m });
  });
  var option = {
    title: {
      left: "center",
      top: "top",
      subtext:
        "check how much a politician/political group talked about a certain topic (in minutes), \n and compare up to 4 politician/political groups, \n click on a topic (bar) to hide it!",
    },
    tooltip: {
      trigger: "axis",
      axisPointer: {
        type: "shadow",
      },
      formatter: function (params) {
        var result = "";
        result += "<b>" + params[0].name + "</b>";
        params.forEach((item, index) => {
          result += '<div style="display: flex; align-items: center;">';
          result +=
            '<span style="display:inline-block;margin-right:5px;border-radius:50%;width:10px;height:10px;background-color:' +
            item.color +
            ';"></span>';
          result +=
            '<b style="padding-right: 10px;">' +
            params[index].seriesName +
            ":</b>";
          result += calcTime(params[index].data);
          result += "</div>";
        });
        return result;
      },
    },
    legend: {
      top: 90,
    },
    grid: {
      top: 150,
      left: "3%",
      right: "4%",
      bottom: "3%",
      containLabel: true,
    },
    yAxis: {
      type: "value",
      boundaryGap: [0, 0.01],
    },
    xAxis: {
      type: "category",
      data: topics,
      show: false,
    },
    series: series,
  };
  barChart2Instance.setOption(option);
  barChart2Instance.hideLoading();
  var removedElements = [];
  var removedTopics = [];
  var removedIndex = [];
  var counter = 0;

  barChart2Instance.on("click", function (p) {
    if (p.componentType == "series") {
      counter++;
      var t;
      var tempList = [];
      series.forEach((v) => {
        if (v["data"].indexOf(p.data) != -1) {
          t = v["data"].indexOf(p.data);
        }
      });
      series.forEach((v, index) => {
        tempList.push(v["data"][t]);
        v["data"].splice(t, 1);
        series[index] = v;
      });
      removedIndex.push(t);
      removedTopics.push(topics[t]);
      topics.splice(t, 1);
      removedElements.push(tempList);
      var option2 = {
        tooltip: {
          trigger: "axis",
          axisPointer: {
            type: "shadow",
          },
        },
        legend: {},
        grid: {
          top: 150,
          left: "3%",
          right: "4%",
          bottom: "3%",
          containLabel: true,
        },
        yAxis: {
          type: "value",
          boundaryGap: [0, 0.01],
        },
        xAxis: {
          type: "category",
          data: topics,
          show: false,
        },
        series: series,
        graphic: [
          {
            type: "text",
            left: 0,
            top: 80,
            style: {
              text: "Back",
              fontSize: 18,
            },
            onclick: function () {
              if (counter > 0) {
                var rt = removedTopics.splice(removedTopics.length - 1, 1);
                var re = removedElements.splice(removedElements.length - 1, 1);
                var ri = removedIndex.splice(removedIndex.length - 1, 1);
                topics.splice(ri[0], 0, rt[0]);
                series.forEach((ser, index) => {
                  ser["data"].splice(ri[0], 0, re[0][index]);
                });
                option.series = series;
                barChart2Instance.setOption(option);
                counter--;
              }
            },
          },
        ],
      };
      barChart2Instance.setOption(option2);
    }
  });
  functionIsRunning = false;
}
