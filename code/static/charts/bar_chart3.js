async function barChart3() {
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

  var bC = document.getElementById("barChart3");
  bC.style.display = "block";
  document.getElementById("barChart2").style.display = "none";
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
  if (barChart3Instance !== null) {
    barChart3Instance.dispose();
  }
  document.querySelector(".card-title").innerHTML =
    "<u>Analisi Politico</u> <br><br>Tempo di trasmissione per canale televisivo <br><br><span>Questo grafico mostra il tempo totale degli interventi di un esponente o gruppo politico sui diversi canali televisivi, consente quindi di analizzare quanto tempo un canale dedica a un determinato politico o partito. <br>Le categorie rappresentano i canali presenti nella banca dati, mentre i valori indicano i tempi totali di intervento su ciascun canale. <br><br>Cliccando su una delle barre rappresentanti i canali, si accede a un grafico a barre sovrapposte, che descrive il tempo di trasmissione deidcato all'esponente nei programmi del canale selezionato, mostrando anche gli argomenti trattati nell'intervento.</span>";
  if (
    $("#select_pol").val()[0] == undefined ||
    $("#select_pol").val()[0] == ""
  ) {
    document.querySelector(".card-title").innerHTML =
      "<u>Analisi Politico</u> <br><br>Tempo di trasmissione per canale televisivo <br><br><span>É necessario selezionare un politico/partito per utilizzare questo grafico. </span>";
    functionIsRunning = false;
    return 0;
  }
  barChart3Instance = echarts.init(bC);
  barChart3Instance.showLoading();
  const p = document.getElementById("politician");
  const pg = document.getElementById("political_group");
  if (p.checked == true) {
    var t = "/v1/politician-channels/";
    var t2 = "/v1/channel-programs-politician/";
  } else if (pg.checked == true) {
    var t = "/v1/political-group-channels/";
    var t2 = "/v1/channel-programs-political-group/";
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
  var data = {
    politician: $("#select_pol").val()[0],
    channels: [],
  };
  var i = 1;
  var total_minutes = 0;
  while (true) {
    if (controller.signal.aborted) {
      functionIsRunning = false;
      return;
    }
    var url = `${baseUrl}&page=${i}`;
    i++;
    const i_data = await fetchData(url);
    if (!i_data || i_data.channels.length == 0) {
      break;
    } else {
      const lengthData = i_data.channels.length;
      while (i_data.channels.length > 0) {
        let popped_channel = i_data.channels.shift();
        data.channels.push(popped_channel);
        total_minutes += popped_channel.minutes;
      }
      if (lengthData < i_data.page_size){
        break;
      }
    }
  }
  if (total_minutes == 0) {
    document.querySelector(".card-title").innerHTML =
      "Charts <span>/Bar Chart</span> <br><br> NO DATA FOUND";
    barChart3Instance.hideLoading();
    functionIsRunning = false;
    return 0;
  }
  var final = [];
  for (let i = 0; i < data["channels"].length; i++) {
    var j = {};
    j["name"] = await data["channels"][i]["channel"];
    j["value"] = data["channels"][i]["minutes"];
    if (j["value"] != 0) {
      final.push(j);
    } // && j.name != "Mediaset TgCom 24"
  }
  if (cb == "none") {
    final = [];
  }
  var totalInterventions = 0;
  for (let i = 0; i < final.length; i++) {
    totalInterventions += final[i].value;
  }
  var new_final = [];
  var altro_channels = [];
  var altro = { name: "altro", value: 0 };
  final.forEach((fin) => {
    if (fin.value <= (totalInterventions / 100) * 1) {
      altro.value += fin.value;
      altro_channels.push(fin.name);
    } else {
      new_final.push(fin);
    }
  });
  new_final.push(altro);
  new_final.sort((a, b) => b.value - a.value);
  new_final_channel = [];
  new_final_value = [];
  new_final.forEach((val) => {
    new_final_channel.push(val.name);
    new_final_value.push(val.value);
  });
  option = {
    xAxis: {
      type: "category",
      data: new_final_channel,
      axisLabel: false,
    },
    yAxis: {
      type: "value",
    },
    grid: {
      top: 100,
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
        result += '<b style="padding-right: 10px;">' + params.name + ":</b>";
        result += calcTime(params.value);
        result += "</div>";
        return result;
      },
    },
    series: [
      {
        type: "bar",
        data: new_final_value,
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
  barChart3Instance.setOption(option, true);
  barChart3Instance.hideLoading();

  barChart3Instance.on("click", async function (p) {
    controller.abort();
    while(functionIsRunning){
      await new Promise((resolve) => setTimeout(resolve, 50));
      if (!controller.signal.aborted){
        return;
      }
    }
    functionIsRunning = true;
    controller = new AbortController();
    var check_selection = false;
    var sbC = document.getElementById("stackedBarChart");
    sbC.style.display = "block";
    if (stackedBarChartInstance !== null) {
      stackedBarChartInstance.dispose();
    }
    stackedBarChartInstance = echarts.init(sbC);
    stackedBarChartInstance.showLoading();
    var data3 = { channel: "altro", programs: [] };
    var list_channels = [];
    if (controller.signal.aborted) {
      functionIsRunning = false;
      return;
    }
    if (p.name != "altro") {
      const url3 =
        t2 +
        encodeURIComponent($("#select_pol").val()[0]) +
        "/" +
        encodeURIComponent(p.name) +
        "?start_date_=" +
        start_date.value.replace(/-/g, "%2F") +
        "&end_date_=" +
        end_date.value.replace(/-/g, "%2F") +
        "&kind_=" +
        cb +
        url_a +
        url_p +
        url_t;
      data3 = await fetchData(url3);
    } else {
      for (const ch of altro_channels) {
        if (controller.signal.aborted) {
          functionIsRunning = false;
          return;
        }
        const url3 =
          t2 +
          encodeURIComponent($("#select_pol").val()[0]) +
          "/" +
          encodeURIComponent(ch) +
          "?start_date_=" +
          start_date.value.replace(/-/g, "%2F") +
          "&end_date_=" +
          end_date.value.replace(/-/g, "%2F") +
          "&kind_=" +
          cb;
        temp_data3 = await fetchData(url3);
        if (!temp_data3) {
          continue;
        }
        temp_data3.programs.forEach((pgrm) => {
          data3.programs.push(pgrm);
          list_channels.push(temp_data3.channel);
        });
      }
    }
    if (!data3) {
      functionIsRunning = false;
      return;
    }
    heightPixels = (50 + data3.programs.length*50).toString() + "px";
    document.getElementById("stackedBarChart").style.height = heightPixels;
    var y = [];
    data3.programs.forEach((r) => {
      y.push(r.program);
    });
    var series3 = [];
    var legenda = {};
    TOPICS.forEach((t) => {
      var programValue = [];
      data3.programs.forEach((r, index) => {
        var found = false;
        r.topics.forEach((rt) => {
          if (rt.topic == t) {
            programValue.push(rt.minutes);
            found = true;
          }
        });
        if (found == false) {
          programValue.push(0);
        }
      });
      if (programValue.some((element) => element !== 0)) {
        series3.push({
          name: t,
          type: "bar",
          stack: "total",
          emphasis: { focus: "series" },
          data: programValue,
        });
        legenda[t] = false;
      }
    });
    yShorted = [];
    y.forEach((ch, index) => {
      if (ch.length > 15) {
        yShorted.push(ch.substring(0, 15) + "...");
      } else {
        yShorted.push(ch);
      }
    });

    const s_d_all = function () {
      var newSelected = {};
      for (item in stackedBarChartInstance.getOption().legend[0].selected) {
        newSelected[item] = !check_selection;
      }
      check_selection = !check_selection;
      stackedBarChartInstance.setOption({
        legend: {
          selected: newSelected,
        },
        graphic: [
          {
            type: "text",
            left: 50,
            style: {
              text: check_selection ? "Deseleziona Tutto" : "Seleziona Tutto",
              fontSize: 18,
            },
            onclick: arguments.callee,
          },
        ],
      });
    };

    option3 = {
      title: {
        text: data3.channel,
        left: "center",
      },
      tooltip: {
        trigger: "axis",
        axisPointer: {
          type: "shadow",
        },
        formatter: function (params) {
          var result = "";
          if (p.name == "altro") {
            result +=
              "<b>" +
              list_channels[params[0].dataIndex] +
              "  -  " +
              y[params[0].dataIndex] +
              "</b>";
          } else {
            result += "<b>" + y[params[0].dataIndex] + "</b>";
          }
          params.forEach((item, index) => {
            if (params[index].data != 0) {
              result += '<div style="display: flex; align-items: center;">';
              result +=
                '<span style="display:inline-block;margin-right:5px;border-radius:50%;width:10px;height:10px;background-color:' +
                item.color +
                ';"></span>';
              result +=
                '<b style="padding-right: 10px;">' +
                params[index].seriesName +
                ": " +
                "</b>";
              result += calcTime(params[index].data);
              result += "</div>";
            }
          });
          return result;
        },
      },
      legend: {
        selected: legenda, /// remove if you want the bars to be shown
        type: "scroll",
        top: 30,
      },
      grid: {
        left: "3%",
        right: "4%",
        bottom: "3%",
        containLabel: true,
      },
      xAxis: {
        type: "value",
      },
      yAxis: {
        type: "category",
        data: yShorted,
      },
      series: series3,
      graphic: [
        {
          type: "text",
          left: 50,
          style: {
            text: "Seleziona tutto",
            fontSize: 18,
          },
          onclick: s_d_all,
        },
      ],
    };
    stackedBarChartInstance.setOption(option3);
    stackedBarChartInstance.hideLoading();

    stackedBarChartInstance.on("legendselectchanged", async function (p) {
      if (Object.values(p.selected).every((value) => value === true)) {
        check_selection = true;
        stackedBarChartInstance.setOption({
          graphic: [
            {
              type: "text",
              left: 50,
              style: {
                text: "Deseleziona tutto",
                fontSize: 18,
              },
              onclick: s_d_all,
            },
          ],
        });
      } else if (Object.values(p.selected).every((value) => value === false)) {
        check_selection = false;
        stackedBarChartInstance.setOption({
          graphic: [
            {
              type: "text",
              left: 50,
              style: {
                text: "Seleziona tutto",
                fontSize: 18,
              },
              onclick: s_d_all,
            },
          ],
        });
      }
    });
    functionIsRunning = false;
  });
  functionIsRunning = false;
}
