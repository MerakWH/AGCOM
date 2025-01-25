var pieChartInstance = null;

async function pieChart2() {
  if (pieChartInstance !== null) {
    pieChartInstance.dispose();
  }
  if ($("#select_pol").val().length == 0) {
    return 0;
  }
  document.getElementById("barChart").style.display = "none";
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
  var pC = document.getElementById("pieChart2");
  pC.style.display = "block";
  pieChartInstance = echarts.init(pC);
  pieChartInstance.showLoading();
  const p = document.getElementById("politician");
  const pg = document.getElementById("political_group");
  if (p.checked == true) {
    var t = "/v1/politician-channels/";
    var t2 = "/v1/channel-programs-politician/";
  } else if (pg.checked == true) {
    var t = "/v1/political-group-channels/";
    var t2 = "/v1/channel-programs-political-group/";
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
  const data = await fetchData(url);
  var final = [];
  for (let i = 0; i < data["channels"].length; i++) {
    var j = {};
    j["name"] = await data["channels"][i]["channel"];
    j["value"] = data["channels"][i]["minutes"];
    if (j["value"] != 0) {
      final.push(j);
    }
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
    if (fin.value <= (totalInterventions / 100) * 5) {
      altro.value += fin.value;
      altro_channels.push(fin.name);
    } else {
      new_final.push(fin);
    }
  });
  new_final.push(altro);
  new_final.sort((a, b) => b.value - a.value);
  option = {
    title: {
      text: "Interventions in channel",
      subtext: "Here we can analyze the time a channel spends for a politician",
      left: "center",
    },
    tooltip: {
      trigger: "item",
      formatter: function (params) {
        var result = "";
        result += "<b>" + params.name + "</b>";
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
    legend: {
      orient: "vertical",
      left: "left",
    },
    series: [
      {
        type: "pie",
        radius: "50%",
        data: new_final,
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
  pieChartInstance.setOption(option, true);
  pieChartInstance.hideLoading();
  var removedElements = [];

  pieChartInstance.on("legendselectchanged", async function (p) {
    if (p.selected[p.name] == false) {
      var ind;
      new_final.forEach((ch, index) => {
        if (ch.name == p.name) {
          ind = index;
        }
      });
      removedElements.push(JSON.parse(JSON.stringify(new_final[ind])));
      new_final[ind].value = 0;
    } else {
      var ind;
      removedElements.forEach((ch, index) => {
        if (ch.name == p.name) {
          ind = index;
        }
      });
      new_final.forEach((ch, index) => {
        if (ch.name == removedElements[ind].name) {
          ch.value = removedElements[ind].value;
        }
      });
      removedElements.splice(ind, 1);
    }
    totalInterventions = 0;
    for (let i = 0; i < final.length; i++) {
      totalInterventions += final[i].value;
    }
    if (p.selected["altro"] == true) {
      altro.value = 0;
      altro_channels = [];
      new_final = [];
      final.forEach((fin) => {
        if (fin.value <= (totalInterventions / 100) * 5 && fin.value != 0) {
          altro.value += fin.value;
          altro_channels.push(fin.name);
        } else {
          new_final.push(fin);
        }
      });
      if (altro.value != 0) {
        new_final.push(altro);
      }
    }
    new_final.sort((a, b) => b.value - a.value);
    option.series[0].data = new_final;
    pieChartInstance.setOption(option);
  });

  pieChartInstance.on("click", async function (p) {
    var check_selection = false;
    var sbC = document.getElementById("stackedBarChart");
    sbC.style.display = "block";
    if (p.data.name == "altro") {
      sbC.style.height = "4000px";
    }
    var stackedBarChart = echarts.init(sbC);
    stackedBarChart.showLoading();
    var data3 = { channel: "altro", programs: [] };
    var list_channels = [];
    if (p.data.name != "altro") {
      const url3 =
        t2 +
        encodeURIComponent($("#select_pol").val()[0]) +
        "/" +
        encodeURIComponent(p.data.name) +
        "?start_date_=" +
        start_date.value.replace(/-/g, "%2F") +
        "&end_date_=" +
        end_date.value.replace(/-/g, "%2F") +
        "&kind_=" +
        cb;
      data3 = await fetchData(url3);
    } else {
      for (const ch of altro_channels) {
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
        temp_data3.programs.forEach((pgrm) => {
          data3.programs.push(pgrm);
          list_channels.push(temp_data3.channel);
        });
      }
    }
    var y = [];
    data3.programs.forEach((r) => {
      y.push(r.program);
    });
    var series3 = [];
    var legenda = {};
    TOPICS.topics.forEach((t) => {
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
      for (item in stackedBarChart.getOption().legend[0].selected) {
        newSelected[item] = !check_selection;
      }
      check_selection = !check_selection;
      stackedBarChart.setOption({
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
          if (p.data.name == "altro") {
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
    stackedBarChart.setOption(option3);
    stackedBarChart.hideLoading();

    stackedBarChart.on("legendselectchanged", async function (p) {
      if (Object.values(p.selected).every((value) => value === true)) {
        check_selection = true;
        stackedBarChart.setOption({
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
        stackedBarChart.setOption({
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
  });
}
