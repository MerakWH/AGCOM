async function radarChart() {
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

  var rC = document.getElementById("radarChart");
  document.getElementById("barChart2").style.display = "none";
  document.getElementById("barChart3").style.display = "none";
  document.getElementById("stackedBarChart").style.display = "none";
  document.getElementById("calendarChart").style.display = "none";
  document.getElementById("lineChart").style.display = "none";
  document.getElementById("lineChart2").style.display = "none";
  document.getElementById("radarChart2").style.display = "none";
  document.getElementById("radarChart3").style.display = "none";
  document.getElementById("barPieChart").style.display = "none";
  document.getElementById("tableDiv").style.display = "none";
  document.getElementById("loadingScreen").style.display = "none";
  rC.style.display = "block";
  if (radarChartInstance !== null) {
    radarChartInstance.dispose();
  }
  document.querySelector(".card-title").innerHTML =
    '<u>Confronto Politici</u><span>&nbsp&nbsp&nbsp/seleziona fino a 4 politici-partiti</span> <br><br>Tempo per argomento<br><br><span> Questo grafico visualizza la quantità totale di tempo che un esponente o gruppo politico dedica a diversi argomenti. <br>Ogni raggio del grafico rappresenta un argomento, per visualizzare nel dettaglio il tempo di trasmissione degli argomenti bisogna passare con il cursore sopra la "ragnatela" che descrive un esponente o gruppo politico. <br><br>Il grafico interattivo offre la possibilità di nascondere un intero set di dati cliccando sul nome corrispondente nella legenda.</span>';
  if (
    $("#select_pol").val()[0] == undefined ||
    $("#select_pol").val()[0] == ""
  ) {
    document.querySelector(".card-title").innerHTML =
      "<u>Confronto Politici</u><span>&nbsp&nbsp&nbsp/seleziona fino a 4 politici-partiti</span> <br><br> Tempo per argomento<br><br><span>É necessario selezionare almeno un politico/partito per utilizzare questo grafico. </span>";
    functionIsRunning = false;
    return 0;
  }
  radarChartInstance = echarts.init(rC);
  radarChartInstance.showLoading();
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
  var politicians = [];
  var values = [];
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
    var temp_values = [];
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
          temp_values.push(popped_topic);
          total_minutes += popped_topic.minutes;
        }
        if (lengthData < data.page_size){
          break;
        }
      }
    }
    values.push(temp_values);
    politicians.push(value);
  }
  if (total_minutes == 0) {
    document.querySelector(".card-title").innerHTML =
      "Charts <span>/Bar + Pie Chart</span> <br><br> NO DATA FOUND";
    radarChartInstance.hideLoading();
    functionIsRunning = false;
    return 0;
  }
  var minutes = [];
  var topics = [];
  values.forEach(function (value) {
    var temp = [];
    value.forEach(function (v) {
      temp.push(v["minutes"]);
    });
    minutes.push(temp);
  });
  max_min = [];
  values[0].forEach(function (t) {
    topics.push(t["topic"]);
    max_min.push(0);
  });
  values.forEach(function (data) {
    data.forEach(function (x, index) {
      if (max_min[index] < x["minutes"]) {
        max_min[index] = x["minutes"] + x["minutes"] / 5;
      } else {
      }
    });
  });
  var indicator = [];
  var data = [];
  topics.forEach(function (f, index) {
    indicator.push({ name: f, max: max_min[index] });
  });
  politicians.forEach(function (p, index) {
    data.push({ name: p, value: minutes[index] });
  });
  option = {
    legend: {
      top: 50,
      data: politicians,
      left: "left",
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
          '<b style="padding-right: 10px;">' + params.name + "</b></div>";
        indicator.forEach((vv, index) => {
          result += '<div style="display: flex; align-items: center;">';
          result += '<b style="padding-right: 10px;">' + vv.name + ":</b>";
          result += calcTime(params.value[index]);
          result += "</div>";
        });
        return result;
      },
    },
    radar: {
      indicator: indicator,
      center: ["50%", "55%"],
    },
    series: [
      {
        name: "Minutes politicians",
        type: "radar",
        data: data,
      },
    ],
  };
  radarChartInstance.setOption(option);
  radarChartInstance.hideLoading();
  functionIsRunning = false;
}
