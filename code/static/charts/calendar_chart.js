async function calendarChart() {
  select_pol_length = 1;
  selectPolLength1();

  document.querySelector(".card-title").innerHTML =
    "Analisi Politico <span>/Grafico a Calendario -- Coming soon</span>";
  document.getElementById("barChart2").style.display = "none";
  document.getElementById("barChart3").style.display = "none";
  document.getElementById("stackedBarChart").style.display = "none";
  document.getElementById("lineChart").style.display = "none";
  document.getElementById("lineChart2").style.display = "none";
  document.getElementById("radarChart").style.display = "none";
  document.getElementById("radarChart2").style.display = "none";
  document.getElementById("radarChart3").style.display = "none";
  document.getElementById("barPieChart").style.display = "none";
  document.getElementById("tableDiv").style.display = "none";
  document.getElementById("loadingScreen").style.display = "none";
  return;

  var cC = document.getElementById("calendarChart");
  cC.style.display = "block";
  document.getElementById("barChart2").style.display = "none";
  document.getElementById("barChart3").style.display = "none";
  document.getElementById("stackedBarChart").style.display = "none";
  document.getElementById("lineChart").style.display = "none";
  document.getElementById("lineChart2").style.display = "none";
  document.getElementById("radarChart").style.display = "none";
  document.getElementById("radarChart2").style.display = "none";
  document.getElementById("radarChart3").style.display = "none";
  document.getElementById("barPieChart").style.display = "none";
  document.getElementById("tableDiv").style.display = "none";
  document.getElementById("loadingScreen").style.display = "none";
  if (calendarChartInstance !== null) {
    calendarChartInstance.dispose();
  }
  document.querySelector(".card-title").innerHTML =
    "Analisi Politico <span>/Grafico a Calendario</span>";
  if (
    $("#select_pol").val()[0] == undefined ||
    $("#select_pol").val()[0] == ""
  ) {
    document.querySelector(".card-title").innerHTML =
      "Analisi Politico <span>/Grafico a Calendario<br><br> You need to select at least a politician/political group to use this chart</span>";
    return 0;
  }
  calendarChartInstance = echarts.init(cC);
  calendarChartInstance.showLoading();
  const p = document.getElementById("politician");
  const pg = document.getElementById("political_group");
  if (p.checked == true) {
    var t = "/v1/interventions-politician-per-day/";
  } else if (pg.checked == true) {
    var t = "/v1/interventions-political-group-per-day/";
  } else {
    return 0;
  }
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
  const baseUrl =
    t +
    $("#select_pol").val()[0] +
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
  var i = 1;
  var data = {
    politician: $("#select_pol").val()[0],
    interventions: [],
    max_value: 0,
    "begin year": 0,
    "final year": 0,
  };
  var total_minutes = 0;
  while (true) {
    var url = `${baseUrl}&page=${i}`;
    i++;
    const i_data = await fetchData(url);
    if (i_data.interventions.length == 0) {
      break;
    } else {
      data.interventions.push(i_data["interventions"][0]);
      data.max_value = i_data.max_value;
      data["begin year"] = i_data["begin year"];
      data["final year"] = i_data["final year"];
      total_minutes += i_data["max_value"];
    }
  }
  if (total_minutes == 0) {
    document.querySelector(".card-title").innerHTML =
      "Charts <span>/Calendar Chart</span> <br><br> NO DATA FOUND";
    calendarChartInstance.hideLoading();
    return 0;
  }
  var interv = data["interventions"];
  var max_value = data["max_value"];
  var begin_year = data["begin year"];
  var final_year = data["final year"];
  var calendar = [];
  var series = [];
  interv.forEach(function (x, index) {
    x.forEach(function (y, index2) {
      interv[index][index2][0] = +echarts.time.parse(interv[index][index2][0]);
    });
  });
  for (var i = begin_year; i <= final_year; i++) {
    calendar.push({
      top: 150 + (i - begin_year) * 200,
      range: i.toString(),
      cellSize: ["auto", 20],
    });
  }
  for (var i = begin_year; i <= final_year; i++) {
    series.push({
      type: "heatmap",
      coordinateSystem: "calendar",
      calendarIndex: i - begin_year,
      data: interv[i - begin_year],
    });
  }
  option = {
    title: {
      subtext:
        "check a calendar with all interventions made in a day by a politician/political group",
      top: "top",
      left: "center",
    },
    tooltip: {
      position: "top",
      formatter: function (params) {
        const date = echarts.time.format(
          params.value[0],
          "{dd}-{MM}-{yyyy}",
          false
        );
        var result = "";
        result += '<div style="display: flex; align-items: center;">';
        result +=
          '<span style="display:inline-block;margin-right:5px;border-radius:50%;width:10px;height:10px;background-color:' +
          params.color +
          ';"></span>';
        result += `<b style="padding-right: 10px;">${date}: </b>${params.value[1]} interventions`;
        result += "</div>";
        return result;
      },
    },
    visualMap: {
      min: 0,
      max: max_value,
      calculable: true,
      orient: "horizontal",
      left: "center",
      top: 50,
    },
    calendar: calendar,
    series: series,
  };
  calendarChartInstance.setOption(option);
  calendarChartInstance.hideLoading();
}
