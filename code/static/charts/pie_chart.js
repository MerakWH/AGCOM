async function pieChart() {
  if ($("#select_pol").val().length == 0) {
    return 0;
  }
  document.getElementById("barChart").style.display = "none";
  document.getElementById("barChart2").style.display = "none";
  document.getElementById("pieChart2").style.display = "none";
  document.getElementById("stackedBarChart").style.display = "none";
  document.getElementById("calendarChart").style.display = "none";
  document.getElementById("lineChart").style.display = "none";
  document.getElementById("lineChart2").style.display = "none";
  document.getElementById("radarChart").style.display = "none";
  document.getElementById("radarChart2").style.display = "none";
  document.getElementById("radarChart3").style.display = "none";
  document.getElementById("barPieChart").style.display = "none";
  document.getElementById("loadingScreen").style.display = "none";
  var pC = document.getElementById("pieChart");
  pC.style.display = "block";
  var pieChart = echarts.init(pC);
  pieChart.showLoading();
  const p = document.getElementById("politician");
  const pg = document.getElementById("political_group");
  if (p.checked == true) {
    var t = "/v1/politician-channels/";
  } else if (pg.checked == true) {
    var t = "/v1/political-group-channels/";
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
    var final = [];
    for (let i = 0; i < result["channels"].length; i++) {
      var j = {};
      j["name"] = result["channels"][i]["channel"];
      j["value"] = result["channels"][i]["interventions"];
      if (j["value"] != 0) {
        final.push(j);
      }
    }
    if (cb == "none") {
      final = [];
    }
    option = {
      title: {
        text: "Interventions in channel",
        subtext:
          "Here we can analyze the time a channel spends for a politician",
        left: "center",
      },
      tooltip: {
        trigger: "item",
      },
      legend: {
        orient: "vertical",
        left: "left",
      },
      series: [
        {
          type: "pie",
          radius: "50%",
          data: final,
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
    pieChart.setOption(option);
    pieChart.hideLoading();
  });
}
