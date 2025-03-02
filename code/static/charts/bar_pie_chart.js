async function barPieChart() {
  function dataFormatter(obj, list, m_y, x_y) {
    var temp;
    for (var year = m_y; year <= x_y; year++) {
      var max = 0;
      var sum = 0;
      temp = obj[year];
      for (var i = 0, l = temp.length; i < l; i++) {
        max = Math.max(max, temp[i]);
        sum += temp[i];
        obj[year][i] = {
          name: list[i],
          value: temp[i],
        };
      }
      obj[year + "max"] = Math.floor(max / 100) * 100;
      obj[year + "sum"] = sum;
    }
    return obj;
  }
  var bpC = document.getElementById("barPieChart");
  bpC.style.display = "block";
  document.getElementById("barChart2").style.display = "none";
  document.getElementById("barChart3").style.display = "none";
  document.getElementById("stackedBarChart").style.display = "none";
  document.getElementById("calendarChart").style.display = "none";
  document.getElementById("lineChart").style.display = "none";
  document.getElementById("lineChart2").style.display = "none";
  document.getElementById("radarChart").style.display = "none";
  document.getElementById("radarChart2").style.display = "none";
  document.getElementById("radarChart3").style.display = "none";
  document.getElementById("tableDiv").style.display = "none";
  document.getElementById("loadingScreen").style.display = "none";
  if (barPieChartInstance !== null) {
    barPieChartInstance.dispose();
  }
  document.querySelector(".card-title").innerHTML =
    "<u>Analisi Canale</u><span>&nbsp&nbsp&nbsp/seleziona fino a 4 politici-partiti </span><br><br>Tempo di partecipazione nei programmi <br><br><span>Questo grafico rappresenta la durata degli interventi nei programmi di un canale televisivo riguardo un esponente o gruppo politico negli anni. <br>Le categorie corrispondono ai programmi televisivi all'interno di un canale, mentre i valori indicano il tempo totale degli interventi associati a ciascun programma. <br>Questo grafico consente di analizzare quanto tempo un programma ha dedicato a un politico o partito specifico in un anno, permettendo di confrontare le tendenze dei dati tra diversi anni. <br>Inoltre, viene visualizzato un piccolo grafico a torta che mostra la somma totale del tempo di intervento per ogni politico o partito nel canale durante l'anno selezionato. <br><br>Il grafico è interattivo, permette di nascondere le barre non d’interesse cliccandoci sopra, con la possibilità di ripristinarle tramite il tasto <u>back</u>. <br>È inoltre possibile nascondere uno dei set di dati cliccando sul nome corrispondente nella legenda. </span>";
  if (
    $("#select_pol").val()[0] == undefined ||
    $("#select_pol").val()[0] == "" ||
    $("#select_channels").val()[0] == undefined ||
    $("#select_channels").val()[0] == ""
  ) {
    document.querySelector(".card-title").innerHTML =
      "<u>Analisi Canale</u><span>&nbsp&nbsp&nbsp/seleziona fino a 4 politici-partiti </span><br><br>Tempo di partecipazione nei programmi <br><br><span>É necessario selezionare almeno un politico/partito e un canale per utilizzare questo grafico. </span>";
    return 0;
  }
  barPieChartInstance = echarts.init(bpC);
  barPieChartInstance.showLoading();
  const p = document.getElementById("politician");
  const pg = document.getElementById("political_group");
  if (p.checked == true) {
    var t = "/v1/minutes-channel-per-politician/";
  } else if (pg.checked == true) {
    var t = "/v1/minutes-channel-per-political-group/";
  } else {
    return 0;
  }
  const selectedValues = $("#select_pol").val();
  var min_year = start_date.value.split("-")[0];
  var max_year = end_date.value.split("-")[0];
  var politicians_list = {};
  var programs_list = [];
  var first_done = false;
  var data_timeline = [];
  var data_legend = [];
  var series = [];
  var options = [];
  var notZero = [];
  for (var x = min_year; x <= max_year; x++) {
    data_timeline.push("year " + x);
  }
  var url_c = "";
  var url_p = "";
  var url_t = "";
  var url_a = "";
  if (
    $("#select_channels").val()[0] != undefined &&
    $("#select_channels").val()[0] != ""
  ) {
    url_c += `${encodeURIComponent($("#select_channels").val()[0])}`;
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
  var total_minutes = 0;
  for (const value of selectedValues) {
    const url =
      t +
      url_c +
      "/" +
      value +
      "?start_date_=" +
      start_date.value.replace(/-/g, "%2F") +
      "&end_date_=" +
      end_date.value.replace(/-/g, "%2F") +
      "&kind_=" +
      cb +
      url_a +
      url_p +
      url_t;
    const data = await fetchData(url);
    total_minutes += data.total;
    if (p.checked == true) {
      data_legend.push(data["politician"]);
    } else if (pg.checked == true) {
      data_legend.push(data["political group"]);
    }
    var temp_list = {};
    data.programs.forEach((prgm, index) => {
      if (!first_done) {
        programs_list.push(prgm.program);
      }
      var check_zero = false;
      for (var yr in prgm.data) {
        if (temp_list[yr] === undefined) {
          temp_list[yr] = [];
        }
        temp_list[yr].push(prgm.data[yr]);
        if (prgm.data[yr] != 0) {
          check_zero = true;
        }
      }
      notZero[index] = check_zero;
    });
    politicians_list[value] = dataFormatter(
      temp_list,
      programs_list,
      min_year,
      max_year
    );
    first_done = true;
    series.push({ name: value, type: "bar" });
  }
  if (total_minutes == 0) {
    document.querySelector(".card-title").innerHTML =
      "Charts <span>/Bar + Pie Chart</span> <br><br> NO DATA FOUND";
    barPieChartInstance.hideLoading();
    return 0;
  }
  for (var pol in politicians_list) {
    for (var j = min_year; j <= max_year; j++) {
      for (var k = politicians_list[pol][j].length; k >= 0; k--) {
        if (!notZero[k]) {
          politicians_list[pol][j].splice(k, 1);
        }
      }
    }
  }
  for (var i = notZero.length; i >= 0; i--) {
    if (!notZero[i]) {
      programs_list.splice(i, 1);
    }
  }
  for (var x = min_year; x <= max_year; x++) {
    var data_ = [];
    var series_ = [];
    var arg = x + "sum";
    data_legend.forEach((p) => {
      data_.push({ name: p, value: politicians_list[p][arg] });
    });
    data_legend.forEach((p) => {
      series_.push({ data: politicians_list[p][x] });
    });
    series_.push({ data: data_ });
    var title = decodeURIComponent(url_c) + "   " + x;
    var f_title = { text: title };
    options.push({ title: f_title, series: series_ });
  }
  series.push({
    name: "%",
    type: "pie",
    center: ["80%", "20%"],
    radius: "15%",
    z: 100,
    tooltip: {
      formatter: function (params) {
        var result = "";
        result += '<div style="display: flex; align-items: center;">';
        result +=
          '<span style="display:inline-block;margin-right:5px;border-radius:50%;width:10px;height:10px;background-color:' +
          params.color +
          ';"></span>';
        result += '<b style="padding-right: 10px;">' + params.name + ":</b>";
        result += calcTime(params.value);
        result +=
          '<p style="padding-left: 10px;">(' + params.percent + "%)</b>";
        result += "</div>";
        return result;
      },
    },
  });
  option = {
    baseOption: {
      timeline: {
        axisType: "category",
        // realtime: false,
        // loop: false,
        autoPlay: true,
        // currentIndex: 2,
        playInterval: 2000,
        // controlStyle: {
        //     position: 'left'
        // },
        data: data_timeline,
        label: {
          formatter: function (s) {
            return new Date(s).getFullYear();
          },
        },
      },
      title: {
        left: "center",
        top: "top",
      },
      tooltip: {
        formatter: function (params) {
          var result = "";
          result += '<div style="display: flex; align-items: center;">';
          result +=
            '<b style="padding-right: 10px;">' + params[0].name + ":</b></div>";
          params.forEach((value) => {
            result +=
              '<div style="display: flex; align-items: center;"><span style="display:inline-block;margin-right:5px;border-radius:50%;width:10px;height:10px;background-color:' +
              value.color +
              ';"></span>';
            result +=
              '<b style="padding-right: 10px;">' + value.seriesName + ":</b>";
            result += calcTime(value.value);
            result += "</div>";
          });
          return result;
        },
      },
      legend: {
        top: 100,
        left: "right",
        data: data_legend,
      },
      calculable: true,
      grid: {
        top: 300,
        bottom: 100,
        tooltip: {
          trigger: "axis",
          axisPointer: {
            type: "shadow",
            label: {
              show: true,
              formatter: function (params) {
                return params.value.replace("\n", "");
              },
            },
          },
        },
      },
      xAxis: [
        {
          type: "category",
          axisLabel: { interval: 0 },
          data: programs_list,
          splitLine: { show: false },
          axisLabel: false,
        },
      ],
      yAxis: [
        {
          type: "value",
          name: "minutes",
        },
      ],
      series: series,
    },
    options: options,
  };
  barPieChartInstance.setOption(option);
  barPieChartInstance.hideLoading();

  var removedElements = [];
  var removedPrograms = [];
  var removedIndex = [];
  var counter = 0;
  barPieChartInstance.on("click", function (p) {
    if (programs_list.length > 1) {
      if (p.componentType == "series") {
        counter++;
        var c = 0;
        for (var pol in politicians_list) {
          for (var j = min_year; j <= max_year; j++) {
            var anno_string = j + "sum";
            var temp = politicians_list[pol][j].splice(p.dataIndex, 1);
            removedElements.push(temp);
            politicians_list[pol][anno_string] -= temp[0].value;
            options[j - min_year].series[data_legend.length].data[c].value -=
              temp[0].value;
          }
          c++;
        }
        removedPrograms.push(programs_list.splice(p.dataIndex, 1));
        removedIndex.push(p.dataIndex);
        option = {
          baseOption: {
            timeline: {
              axisType: "category",
              // realtime: false,
              // loop: false,
              autoPlay: false,
              // currentIndex: 2,
              playInterval: 2000,
              // controlStyle: {
              //     position: 'left'
              // },
              data: data_timeline,
              label: {
                formatter: function (s) {
                  return new Date(s).getFullYear();
                },
              },
            },
            title: {},
            tooltip: {},
            legend: {
              left: "right",
              data: data_legend,
            },
            calculable: true,
            grid: {
              top: 80,
              bottom: 100,
              tooltip: {
                trigger: "axis",
                axisPointer: {
                  type: "shadow",
                  label: {
                    show: true,
                    formatter: function (params) {
                      return params.value.replace("\n", "");
                    },
                  },
                },
              },
            },
            xAxis: [
              {
                type: "category",
                axisLabel: { interval: 0 },
                data: programs_list,
                splitLine: { show: false },
                axisLabel: false,
              },
            ],
            yAxis: [
              {
                type: "value",
                name: "minutes",
              },
            ],
            series: series,
            graphic: [
              {
                type: "text",
                left: 50,
                top: 20,
                style: {
                  text: "Back",
                  fontSize: 18,
                },
                onclick: function () {
                  if (counter > 0) {
                    var rp = removedPrograms.splice(
                      removedPrograms.length - 1,
                      1
                    );
                    var l = removedIndex.length - 1;
                    var lx = (max_year - min_year + 1) * data_legend.length;
                    var c = 0;
                    var ri = removedIndex.splice(removedIndex.length - 1, 1);
                    for (var pol in politicians_list) {
                      for (var j = min_year; j <= max_year; j++) {
                        var re = removedElements.splice(l * lx, 1);
                        politicians_list[pol][j].splice(ri[0][0], 0, re[0][0]);
                        options[j - min_year].series[data_legend.length].data[
                          c
                        ].value += re[0][0].value;
                      }
                      c++;
                    }
                    programs_list.splice(ri[0][0], 0, rp[0][0]);
                    barPieChartInstance.setOption(option);
                    counter--;
                  }
                },
              },
            ],
          },
          options: options,
        };
        barPieChartInstance.setOption(option);
      }
    }
  });
}
