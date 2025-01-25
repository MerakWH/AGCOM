// initializing politicians/political group list (select)
async function handleOptionChange(radio) {
  const select_pol = document.getElementById("select_pol");
  while (select_pol.options.length > 0) {
    select_pol.remove(0);
  }
  const o = document.createElement("option");
  select_pol.appendChild(o);
  if (radio.value == "politician") {
    document.getElementById("select_affiliations").disabled = false;
    var i = 1;
    while (true) {
      var url = "/v1/politicians" + `?page=${i}`;
      i++;
      const data = await fetchData(url);
      if (data.politicians.length === 0) {
        break;
      }
      data["politicians"].forEach((valore) => {
        var option = document.createElement("option");
        option.value = valore;
        option.text = valore;
        select_pol.appendChild(option);
      });
    }
  } else if (radio.value == "political_group") {
    document.getElementById("select_affiliations").disabled = true;
    $("#select_affiliations").empty();
    var i = 1;
    while (true) {
      var url = "/v1/political-groups" + `?page=${i}`;
      i++;
      const data = await fetchData(url);
      if (data["political groups"].length === 0) {
        break;
      }
      data["political groups"].forEach((valore) => {
        var option = document.createElement("option");
        option.value = valore;
        option.text = valore;
        select_pol.appendChild(option);
      });
    }
  }
}

//initialize selects (channels, programs, topics, affiliations)
async function fetchChannels() {
  var select_channels = document.getElementById("select_channels");
  const o = document.createElement("option");
  select_channels.appendChild(o);
  var i = 1;
  while (true) {
    var url = "/v1/channels" + `?page=${i}`;
    i++;
    const result = await fetchData(url);
    if (result.channels.length == 0) {
      break;
    } else {
      result["channels"].forEach((valore) => {
        var option = document.createElement("option");
        option.value = valore;
        option.text = valore;
        select_channels.appendChild(option);
      });
    }
  }
}

async function fetchPrograms() {
  const select_programs = document.getElementById("select_programs");
  const o = document.createElement("option");
  select_programs.appendChild(o);
  while (select_programs.options.length > 0) {
    select_programs.remove(0);
  }
  var i = 1;
  var selected_channel = "";
  if (
    $("#select_channels").val()[0] != undefined &&
    $("#select_channels").val()[0] != ""
  ) {
    selected_channel += `&channel_=${$("#select_channels").val()[0]}`;
  }
  while (true) {
    var url = "/v1/programs" + `?page=${i}` + selected_channel;
    i++;
    const result = await fetchData(url);
    if (result.programs.length == 0) {
      break;
    } else {
      result["programs"].forEach((valore) => {
        var option = document.createElement("option");
        option.value = valore;
        option.text = valore;
        select_programs.appendChild(option);
      });
    }
  }
}
async function fetchTopics() {
  const select_topics = document.getElementById("select_topics");
  const o = document.createElement("option");
  select_topics.appendChild(o);
  var i = 1;
  while (true) {
    var url = "/v1/topics" + `?page=${i}`;
    i++;
    const result = await fetchData(url);
    if (result.topics.length == 0) {
      break;
    } else {
      result["topics"].forEach((valore) => {
        var option = document.createElement("option");
        option.value = valore;
        option.text = valore;
        select_topics.appendChild(option);
      });
    }
  }
}

async function fetchAffiliations() {
  const select_affiliations = document.getElementById("select_affiliations");
  const o = document.createElement("option");
  select_affiliations.appendChild(o);
  if ($("#select_pol").val().length > 1) {
    document.getElementById("select_affiliations").disabled = true;
    $("#select_affiliations").empty();
  } else if (!$("#political_group").is(":checked")) {
    document.getElementById("select_affiliations").disabled = false;
    while (select_affiliations.options.length > 0) {
      select_affiliations.remove(0);
    }
    var i = 1;
    var selected_politician = "";
    if (
      $("#select_pol").val()[0] != undefined &&
      $("#select_pol").val()[0] != ""
    ) {
      selected_politician += `&politician_=${$("#select_pol").val()[0]}`;
    }
    while (true) {
      var url = "/v1/affiliations" + `?page=${i}` + selected_politician;
      i++;
      const result = await fetchData(url);
      if (result.affiliations.length == 0) {
        break;
      } else {
        result["affiliations"].forEach((valore) => {
          var option = document.createElement("option");
          option.value = valore;
          option.text = valore;
          select_affiliations.appendChild(option);
        });
      }
    }
  }
}
