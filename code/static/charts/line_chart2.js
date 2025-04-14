async function lineChart2() {
  select_pol_length = 4;
  controller.abort();
  while(functionIsRunning){
    await new Promise((resolve) => setTimeout(resolve, 50));
    if (!controller.signal.aborted){
      return;
    }
  }
  functionIsRunning = true;
  controller = new AbortController();
  selectPolLength4();

  var lC = document.getElementById("lineChart2");
  lC.style.display = "block";
  document.getElementById("barChart2").style.display = "none";
  document.getElementById("barChart3").style.display = "none";
  document.getElementById("stackedBarChart").style.display = "none";
  document.getElementById("calendarChart").style.display = "none";
  document.getElementById("lineChart").style.display = "none";
  document.getElementById("radarChart").style.display = "none";
  document.getElementById("radarChart2").style.display = "none";
  document.getElementById("radarChart3").style.display = "none";
  document.getElementById("barPieChart").style.display = "none";
  document.getElementById("tableDiv").style.display = "none";
  document.getElementById("loadingScreen").style.display = "none";
  if (lineChart2Instance !== null) {
    lineChart2Instance.dispose();
  }
  if (
    $("#select_pol").val()[0] == undefined ||
    $("#select_pol").val()[0] == ""
  ) {
    document.querySelector(".card-title").innerHTML =
      "<u>Confronto Politici</u><span>&nbsp&nbsp&nbsp/seleziona fino a 4 politici-partiti</span> <br><br>Interventi giornalieri <br><br><span>É necessario selezionare almeno un politico/partito per utilizzare questo grafico. </span>";
    functionIsRunning = false;
    return 0;
  }
  document.querySelector(".card-title").innerHTML =
    "<u>Confronto Politici</u><span>&nbsp&nbsp&nbsp/seleziona fino a 4 politici-partiti</span> <br><br>Interventi giornalieri <br><br><span>Questo grafico rappresenta il numero degli interventi di un esponente o gruppo politico in un determinato arco di tempo. <br>Le categorie corrispondono ai giorni all'interno dell'intervallo selezionato, mentre i valori indicano il numero totale di interventi e notizie trasmesse per ciascun giorno. <br>Il grafico consente di analizzare l'andamento della presenza televisiva di un politico o partito, individuando eventuali picchi o cali di interesse. <br><br>Una barra inferiore permette di ingrandire e visualizzare una frazione dell’intervallo di tempo totale, mentre la legenda in alto consente di nascondere o mostrare i vari insiemi di dati.</span>";

  lineChart2Instance = echarts.init(lC);
  lineChart2Instance.showLoading();
  const p = document.getElementById("politician");
  const pg = document.getElementById("political_group");
  if (p.checked == true) {
    var t = "/v1/interventions-politician-per-day/";
  } else if (pg.checked == true) {
    var t = "/v1/interventions-political-group-per-day/";
  } else {
    functionIsRunning = false;
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
  const selectedValues = $("#select_pol").val();
  var begin_year = parseInt(start_date.value.split("-")[0]);
  var final_year = parseInt(end_date.value.split("-")[0]);
  var series = [];
  var politicians = [];
  var total_minutes = 0;

  const finalUrl =
  "&kind_=" +
  cb +
  url_a +
  url_c +
  url_p +
  url_t;

  for (const value of selectedValues) {
    const beginUrl =
      t +
      value
    var values = [];
    var i = 0;

    while((begin_year + i) != final_year + 1){
      var j = 1;
      const baseUrl = 
      beginUrl +
      "?year=" +
      (begin_year + i) +
      finalUrl;
      while (true) {
        if (controller.signal.aborted) {
          functionIsRunning = false;
          return;
        }
        var url = `${baseUrl}&page=${j}`;
        const data = await fetchData(url);
        if (!data || data.interventions.length == 0) {
          break;
        }
        var temp = [];
        data.interventions.forEach((v) => {
          temp.push([v[0], v[1]["interventions"]]);
        });
        var temp = [];
        data.interventions.forEach((v) => {
          temp.push([v[0], v[1]["interventions"]]);
        });
        values.push(temp);
        total_minutes += data.max_value;
        if (data.interventions.length < data.page_size){
          break;
        }
        j++;
      }
      i++;
    }
    series.push(values);
    politicians.push(value);
  }
  if (total_minutes == 0) {
    document.querySelector(".card-title").innerHTML =
      "Charts <span>/Bar + Pie Chart</span> <br><br> NO DATA FOUND";
    lineChart2Instance.hideLoading();
    functionIsRunning = false;
    return 0;
  }
  series.forEach((pol, index) => {
    var f = [];
    pol.forEach((year) => {
      f = f.concat(year);
    });
    series[index] = f;
  });
  option = {
    xAxis: {
      type: "category",
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
          params.value[1] +
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
    dataZoom: [
      {
        id: "dataZoomX",
        type: "slider",
        xAxisIndex: [0],
        filterMode: "filter",
      },
    ],
  };
  lineChart2Instance.setOption(option);
  lineChart2Instance.hideLoading();
  functionIsRunning = false;
}
