async function barChart() {
  if ($("#select_pol").val().length == 0) {
    return 0;
  }
  document.getElementById("barChart2").style.display = "none";
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
  var bC = document.getElementById("barChart");
  bC.style.display = "block";
  var barChart = echarts.init(bC);
  barChart.showLoading();
  const p = document.getElementById("politician");
  const pg = document.getElementById("political_group");
  if (p.checked == true) {
    var t = "/v1/politician-topics/";
  } else if (pg.checked == true) {
    var t = "/v1/political-group-topics/";
  } else {
    return 0;
  }
  const url =
    t +
    $("#select_pol").val()[0] +
    "?start_date_=" +
    start_date.value.replace(/-/g, "%2F") +
    "&end_date_=" +
    end_date.value.replace(/-/g, "%2F") +
    "&kind_=" +
    cb;
  fetchData(url).then((result) => {
    var topics = [];
    var minutes = [];
    var f = [];
    for (let i = 0; i < result["topics"].length; i++) {
      if (result["topics"][i]["interventions"] != 0) {
        var x = [
          result["topics"][i]["interventions"],
          result["topics"][i]["topic"],
        ];
        f.push(x);
      }
    }
    f.sort((a, b) => a[0] - b[0]);
    f.forEach((value) => {
      minutes.push(value[0]);
      topics.push(value[1]);
    });
    option = {
      title: {
        text: "Interventions in channel",
        subtext:
          "Here we can analyze what type of topic a politician talked about",
        left: "center",
      },
      yAxis: {
        type: "category",
        data: topics,
        axisLabel: false,
      },
      xAxis: {
        type: "value",
      },
      tooltip: {
        trigger: "item",
      },
      series: [
        {
          data: minutes,
          type: "bar",
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowOffsetX: 0,
              shadowColor: "rgba(0, 0, 0, 0.5)",
            },
          },
        },
      ],
    };
    barChart.setOption(option);
    barChart.hideLoading();
  });
}
