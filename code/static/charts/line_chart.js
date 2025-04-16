async function lineChart() {
  controller.abort();
  while(functionIsRunning){
    await new Promise((resolve) => setTimeout(resolve, 50));
    if (!controller.signal.aborted){
      return;
    }
  }
  functionIsRunning = true;
  controller = new AbortController();
  if(select_pol_length != 4){
    select_pol_length = 4;
    selectPolLength4();
  }
  
  var lC = document.getElementById("lineChart");
  lC.style.display = "block";
  document.getElementById("barChart2").style.display = "none";
  document.getElementById("barChart3").style.display = "none";
  document.getElementById("stackedBarChart").style.display = "none";
  document.getElementById("lineChart2").style.display = "none";
  document.getElementById("calendarChart").style.display = "none";
  document.getElementById("radarChart").style.display = "none";
  document.getElementById("radarChart2").style.display = "none";
  document.getElementById("radarChart3").style.display = "none";
  document.getElementById("barPieChart").style.display = "none";
  document.getElementById("tableDiv").style.display = "none";
  document.getElementById("loadingScreen").style.display = "none";
  if (lineChartInstance !== null) {
    lineChartInstance.dispose();
  }
  document.querySelector(".card-title").innerHTML =
    "<u>Confronto Politici</u><span>&nbsp&nbsp&nbsp/seleziona fino a 4 politici-partiti</span> <br><br>Interventi annui <br><br><span>Questo grafico rappresenta il numero degli interventi di un esponente o gruppo politico nel corso degli anni, permettendo di analizzare l'andamento della presenza televisiva di un soggetto, individuando eventuali picchi o cali di interesse. <br>Le categorie corrispondono agli anni, mentre i valori indicano il numero totale di interventi e notizie trasmesse durante ciascun anno. <br><br>La legenda in alto consente di nascondere o mostrare i vari insiemi di dati. </span>";
  if (
    $("#select_pol").val()[0] == undefined ||
    $("#select_pol").val()[0] == ""
  ) {
    document.querySelector(".card-title").innerHTML =
      "<u>Confronto Politici</u><span>&nbsp&nbsp&nbsp/seleziona fino a 4 politici-partiti</span> <br><br>Interventi annui <br><br><span>É necessario selezionare almeno un politico/partito per utilizzare questo grafico. </span>";
    functionIsRunning = false;
    return 0;
  }
  lineChartInstance = echarts.init(lC);
  lineChartInstance.showLoading();
  const p = document.getElementById("politician");
  const pg = document.getElementById("political_group");
  if (p.checked == true) {
    var t = "/v1/interventions-politician-per-year/";
  } else if (pg.checked == true) {
    var t = "/v1/interventions-political-group-per-year/";
  } else {
    functionIsRunning = false;
    return 0;
  }
  var series = [];
  var years;
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
    if (controller.signal.aborted) {
      functionIsRunning = false;
      return;
    }
    const url =
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
    const data = await fetchData(url);
    if (!data) {
      functionIsRunning = false;
      return;
    }
    total_minutes += data.total;
    years = data["years"];
    var interventions = data["interventions"];
    series.push(interventions);
    if (p.checked == true) {
      politicians.push(data["politician"]);
    } else if (pg.checked == true) {
      politicians.push(data["political group"]);
    }
  }
  if (total_minutes == 0) {
    document.querySelector(".card-title").innerHTML =
      "Charts <span>/Bar + Pie Chart</span> <br><br> NO DATA FOUND";
    lineChartInstance.hideLoading();
    functionIsRunning = false;
    return 0;
  }
  option = {
    xAxis: {
      type: "category",
      data: years,
    },
    yAxis: {
      type: "value",
    },
    grid: {
      top: 150,
    },
    legend: {
      top: 50,
      data: politicians,
      left: "right",
      orient: "vertical",
      formatter: function (name) {
        if (name.length > 35) {
          var index = 35;
          while (name.charAt(index) !== " " && index > 0) {
            index--;
          }
          if (index === 0) {
            index = 35;
          }
          return name.substr(0, index) + "\n" + name.substr(index);
        } else {
          return name;
        }
      },
    },
    tooltip: {
      trigger: "item",
      formatter: function (params) {
        console.log(params);
        var result = "";
        result += '<div style="display: flex; align-items: center;">';
        result +=
          '<span style="display:inline-block;margin-right:5px;border-radius:50%;width:10px;height:10px;background-color:' +
          params.color +
          ';"></span>';
        result +=
          '<b style="padding-right: 10px;">' +
          params.name +
          ":</b> " +
          params.value +
          " interventions</div>";
        return result;
      },
    },
    series: [
      {
        name: politicians[0],
        data: series[0],
        type: "line",
      },
      {
        name: politicians[1],
        data: series[1],
        type: "line",
      },
      {
        name: politicians[2],
        data: series[2],
        type: "line",
      },
      {
        name: politicians[3],
        data: series[3],
        type: "line",
      },
    ],
  };
  lineChartInstance.setOption(option);
  lineChartInstance.hideLoading();
  functionIsRunning = false;
}
