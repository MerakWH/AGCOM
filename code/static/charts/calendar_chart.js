async function calendarChart() {
  controller.abort();
  while(functionIsRunning){
    await new Promise((resolve) => setTimeout(resolve, 50));
    if (!controller.signal.aborted){
      return;
    }
  }
  functionIsRunning = true;
  controller = new AbortController();
  if(select_pol_length != 1){
    select_pol_length = 1;
    selectPolLength1();
  }

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
  if (
    $("#select_pol").val()[0] == undefined ||
    $("#select_pol").val()[0] == ""
  ) {
    document.querySelector(".card-title").innerHTML =
    "<u>Analisi Politico</u> <br><br>Interventi giornalieri <br><br><span>É necessario selezionare un politico/partito per utilizzare questo grafico. </span>";
    functionIsRunning = false;
    return 0;
  }
  document.querySelector(".card-title").innerHTML =
    "<u>Analisi Politico</u> <br><br>Interventi giornalieri <br><br><span>Questo grafico mostra un calendario in cui ogni giorno è rappresentato dal numero di interventi televisivi effettuati da un esponente o gruppo politico. <br>Il grafico consente di identificare pattern e relazioni nei dati, confrontando i periodi in cui un politico o partito ha effettuato più o meno interventi o notizie. <br><br>Una barra di filtro situata in cima al grafico permette di visualizzare solo i giorni con un numero specifico di interventi. <br>Cliccando su uno dei giorni nel calendario, appare una tabella che mostra gli interventi svolti più nello specifico.</span>"
  calendarChartInstance = echarts.init(cC);
  calendarChartInstance.showLoading();
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
  var topic_index = 0;
  while ($("#select_topics").val()[topic_index] != undefined){
    if (
      $("#select_topics").val()[topic_index] != undefined &&
      $("#select_topics").val()[topic_index] != ""
    ) {
      url_t += `&topics_list=${encodeURIComponent($("#select_topics").val()[topic_index])}`;
    }
    topic_index++;
  }
  if (
    $("#select_affiliations").val()[0] != undefined &&
    $("#select_affiliations").val()[0] != ""
  ) {
    url_a += `&affiliation_=${encodeURIComponent(
      $("#select_affiliations").val()[0]
    )}`;
  }

  var begin_year = parseInt(start_date.value.split("-")[0]);
  var final_year = parseInt(end_date.value.split("-")[0]);
  var i_data = {
    politician: $("#select_pol").val()[0],
    interventions: [],
    max_value: 0,
  };
  var total_minutes = 0;
  var i = 0;
  
  const finalUrl =
    "&kind_=" +
    cb +
    url_a +
    url_c +
    url_p +
    url_t;

  while((begin_year + i) != final_year + 1){
    var j = 1;
    const baseUrl = 
    t +
    $("#select_pol").val()[0] +
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
      i_data.interventions.push(temp);
      i_data.max_value = data.max_value > i_data.max_value ? data.max_value : i_data.max_value;
      total_minutes += data.max_value;

      if (data.interventions.length < data.page_size){
        break;
      }
      j++;
    }
    i++;
  }
  heightPixels = (200 + i*200).toString() + "px";
  document.getElementById("calendarChart").style.height = heightPixels;
  if (total_minutes == 0) {
    document.querySelector(".card-title").innerHTML =
      "Charts <span>/Calendar Chart</span> <br><br> NO DATA FOUND";
    calendarChartInstance.hideLoading();
    functionIsRunning = false;
    return 0;
  }
  var interv = i_data["interventions"];
  var max_value = i_data["max_value"];
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

  calendarChartInstance.on("click", async function (variable) {
    if(variable.data[1] == 0){
      document.getElementById("tableDiv").style.display = "none";
      return;
    }
    controller.abort();
    while(functionIsRunning){
      await new Promise((resolve) => setTimeout(resolve, 50));
      if (!controller.signal.aborted){
        return;
      }
    }
    functionIsRunning = true;
    controller = new AbortController();

    const timestamp = variable.data[0];
    const date = new Date(timestamp);

    // Estrai anno, mese (aggiungi 1 perché parte da 0), e giorno
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0'); // aggiunge lo 0 davanti se serve
    const day = String(date.getDate()).padStart(2, '0');

    const formattedDate = `${year}/${month}/${day}`;

    document.getElementById("tableDiv").style.display = "none";
    document.getElementById("loadingScreen").style.display = "block";

    if (tab != undefined) {
      tab.clear();
    }

    var url = ""

    if (p.checked == true) {
      url = "/v1/politician-getall/";
    } else if (pg.checked == true) {
      url = "/v1/political-group-getall/";
    } else {
      document.getElementById("loadingScreen").style.display = "none"; // Nascondi la schermata di caricamento
      functionIsRunning = false;
      return 0;
    }

    url += $("#select_pol").val()[0] +
      "?date_=" +
      formattedDate +
      url_a +
      url_c +
      url_p +
      url_t +
      "&kind_=" +
      cb;

    fetchData(url).then(data => {
      if(data != null){
        data.data.forEach((r) => {
          var newRow = [
            r[0],
            r[1],
            r[6],
            r[7],
            r[2],
            r[8]
          ];
          tab.row.add(newRow).draw(false);
          document.getElementById("loadingScreen").style.display = "none";
          document.getElementById("tableDiv").style.display = "block";
        });
      }
    });
    functionIsRunning = false;
  });
  functionIsRunning = false;
}