// initializing politicians/political group list (select)
async function handleOptionChange(radio) {
  const select_pol =  $('#select_pol');
  select_pol.prop('disabled', true).select2({
    placeholder: 'Caricamento...'
  });
  $('#select_pol').empty();
  if (radio.value == "politician") {
    document.getElementById("select_affiliations").disabled = false;
    if (
      $("#select_affiliations").val()[0] != undefined &&
      $("#select_affiliations").val()[0] != ""
    ) {
      var selected_affiliation = "";
      selected_affiliation += `${encodeURIComponent($("#select_affiliations").val()[0])}`;
      var url = "/v1/politicians-affiliation/" + selected_affiliation;
      const data = await fetchData(url);
      data["politicians"].forEach((valore) => {
        const option = new Option(valore, valore, false, false);
        select_pol.append(option);
      });
    }else{
      var i = 1;
      while (true) {
        var url = "/v1/politicians" + `?page=${i}`;
        i++;
        const data = await fetchData(url);
        if (data.politicians.length === 0) break;
        data["politicians"].forEach((valore) => {
          const option = new Option(valore, valore, false, false);
          select_pol.append(option);
        });
      }
    }
  } else if (radio.value == "political_group") {
    document.getElementById("select_affiliations").disabled = true;
    $("#select_affiliations").empty();
    var i = 1;
    while (true) {
      var url = "/v1/political-groups" + `?page=${i}`;
      i++;
      const data = await fetchData(url);
      if (data["political groups"].length === 0) break;
      data["political groups"].forEach((valore) => {
        const option = new Option(valore, valore, false, false);
        select_pol.append(option);
      });
    }
  }
  select_pol.prop('disabled', false).select2({
    placeholder: 'Cerca politico/partito'
  });
}

let isUpdating = false;
let firtInitialization = [false, false];

//initialize selects (channels, programs, topics, affiliations)
async function fetchChannels() {
  if (isUpdating && firtInitialization[0]) return;
  firtInitialization[0] = true;
  isUpdating = true;
  const old_value = $("#select_channels").val()[0];
  var select_channels = $('#select_channels');
  select_channels.prop('disabled', true).select2({
    placeholder: 'Caricamento...'
  });
  $('#select_channels').empty();
  var i = 1;
  var selected_program = "";
  if (
    $("#select_programs").val()[0] != undefined &&
    $("#select_programs").val()[0] != ""
  ) {
    selected_program = `&program_=${encodeURIComponent($("#select_programs").val()[0])}`
    }
  while (true) {
    var url = "/v1/channels" + `?page=${i}` + selected_program;
    i++;
    const result = await fetchData(url);
    if (result.channels.length === 0) break;
    result.channels.forEach((valore) => {
      const option = new Option(valore, valore, false, false);
      select_channels.append(option);
    });
  }
  select_channels.prop('disabled', false).select2({
    placeholder: 'Cerca canale'
  });
  if (old_value != undefined){
    select_channels.onchange = null;
    select_channels.value = old_value;
    $('#select_channels').val(old_value).trigger('change');
    select_channels.onchange = function() {
        updateCharts(tab, still_running);
        fetchPrograms();
    };
  }
  isUpdating = false;
}

async function fetchPrograms() {
  if (isUpdating && firtInitialization[1]) return;
  firtInitialization[1] = true;
  isUpdating = true;
  const old_value = $("#select_programs").val()[0];
  var select_programs = $('#select_programs');
  select_programs.prop('disabled', true).select2({
    placeholder: 'Caricamento...'
  });
  $('#select_programs').empty();
  var i = 1;
  var selected_channel = "";
  if (
    $("#select_channels").val()[0] != undefined &&
    $("#select_channels").val()[0] != ""
  ) {
    selected_channel += `&channel_=${encodeURIComponent($("#select_channels").val()[0])}`;
  }
  while (true) {
    var url = "/v1/programs" + `?page=${i}` + selected_channel;
    i++;
    const result = await fetchData(url);
    if (result.programs.length === 0) break;
    result.programs.forEach((valore) => {
      const option = new Option(valore, valore, false, false);
      select_programs.append(option);
    });
  }
  select_programs.prop('disabled', false).select2({
    placeholder: 'Cerca programma'
  });
  if (old_value != undefined){
    select_programs.onchange = null;
    select_programs.value = old_value;
    $('#select_programs').val(old_value).trigger('change');
    select_programs.onchange = function() {
        updateCharts(tab, still_running);
        fetchChannels();
    };
  }
  isUpdating = false;
}

async function fetchTopics() {
  const select_topics = document.getElementById("select_topics");
  $('#select_topics').data('select2').$container.find('.select2-search__field').attr('placeholder', 'Caricamento...');
  select_topics.disabled = true;
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
  $('#select_topics').data('select2').$container.find('.select2-search__field').attr('placeholder', 'Cerca argomento');
  select_topics.disabled = false;
}

async function fetchAffiliations() {
  const old_value = $("#select_affiliations").val()[0];
  var select_affiliations = $('#select_affiliations');
  if ($("#select_pol").val().length > 1) {
    select_affiliations.prop('disabled', true);
    $("#select_affiliations").empty();
  } else if (!$("#political_group").is(":checked")) {
    select_affiliations.prop('disabled', true).select2({
      placeholder: 'Caricamento...'
    });
    $('#select_affiliations').empty();
    var i = 1;
    var selected_politician = "";
    if (
      $("#select_pol").val()[0] != undefined &&
      $("#select_pol").val()[0] != ""
    ) {
      selected_politician += `&politician_=${encodeURIComponent($("#select_pol").val()[0])}`;
    }
    while (true) {
      var url = "/v1/affiliations" + `?page=${i}` + selected_politician;
      i++;
      const result = await fetchData(url);
      if (result.affiliations.length === 0) break;
      result.affiliations.forEach((valore) => {
        const option = new Option(valore, valore, false, false);
        select_affiliations.append(option);
      });
    }
    select_affiliations.prop('disabled', false).select2({
      placeholder: 'Cerca partito'
    });
    if (old_value != undefined){
      select_affiliations.onchange = null;
      select_affiliations.value = old_value;
      $('#select_affiliations').val(old_value).trigger('change');
      select_affiliations.onchange = function() {
          updateCharts(tab, still_running);
          updatePoliticians();
      };
    }
  }
}

async function updatePoliticians() {
  const selectedOption = $('input[name="choose_pol"]:checked').val();
  var rad = {};
  rad["value"] = selectedOption;
  const old_value = $("#select_pol").val()[0];
  handleOptionChange(rad).then(() => {
    if (old_value != undefined){
      const select_pol = document.getElementById('select_pol');
      select_pol.onchange = null;
      select_pol.value = old_value;
      $('#select_pol').val(old_value).trigger('change');
      select_pol.onchange = function() {
          updateCharts(tab, still_running);
          fetchAffiliations();
      };
    }
  });
}