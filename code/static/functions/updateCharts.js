//update charts
async function updateCharts(tab, still_running) {
  if (document.getElementById("barChart2").style.display == "block") {
    barChart2();
  } else if (document.getElementById("barChart3").style.display == "block") {
    barChart3();
  } else if (
    document.getElementById("calendarChart").style.display == "block"
  ) {
    calendarChart();
  } else if (document.getElementById("lineChart").style.display == "block") {
    lineChart();
  } else if (document.getElementById("lineChart2").style.display == "block") {
    lineChart2();
  } else if (document.getElementById("radarChart").style.display == "block") {
    radarChart();
  } else if (document.getElementById("radarChart2").style.display == "block") {
    radarChart2();
  } else if (document.getElementById("radarChart3").style.display == "block") {
    radarChart3();
  } else if (document.getElementById("barPieChart").style.display == "block") {
    barPieChart();
  } else if (
    document.getElementById("tableDiv").style.display == "block" ||
    document.getElementById("loadingScreen").style.display == "block"
  ) {
    table(tab, still_running);
  }
}

async function selectPolLength1() {
  $("#select_pol").select2({
    maximumSelectionLength: 1,
    placeholder: "Cerca politico/partito",
    language: {
      noResults: function () {
        return "Seleziona un opzione tra partiti e politici";
      },
    },
  });
  if ($("#select_pol").val().length > 1) {
    temp = $("#select_pol").val()[0];
    $("#select_pol").val([temp]).trigger("change");
  }
}

async function selectPolLength4() {
  $("#select_pol").select2({
    maximumSelectionLength: 4,
    placeholder: "Cerca politico/partito",
    language: {
      noResults: function () {
        return "Seleziona un opzione tra partiti e politici";
      },
    },
  });
  if ($("#select_pol").val().length > 4) {
    temp = [
      $("#select_pol").val()[0],
      $("#select_pol").val()[1],
      $("#select_pol").val()[2],
      $("#select_pol").val()[3],
    ];
    $("#select_pol").val(temp).trigger("change");
  }
}

async function selectPolLength10() {
  $("#select_pol").select2({
    maximumSelectionLength: 10,
    placeholder: "Cerca politico/partito",
    language: {
      noResults: function () {
        return "Seleziona un opzione tra partiti e politici";
      },
    },
  });
}
