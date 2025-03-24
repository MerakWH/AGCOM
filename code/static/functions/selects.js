async function handleOptionChange(radio) {                      // initializing politicians/political group list when radio is clicked
  const select_pol =  $('#select_pol');
  const select_affiliations = $("#select_affiliations");
  select_pol.prop('disabled', true).select2({                   //empty the select and block it while loading
    placeholder: 'Caricamento...'
  });
  $('#select_pol').empty();

  if (radio.value == "politician") {                            //if politician was selected
    if (                                                        //if an affiliation is selected
      select_affiliations.val()[0] != undefined &&
      select_affiliations.val()[0] != ""
    ) {                                                         //serach only the politicians that participated in that affiliation
      var affiliation_url = `${encodeURIComponent(select_affiliations.val()[0])}`;
      var url = "/v1/politicians-affiliation/" + affiliation_url;
      const data = await fetchData(url);
      data["politicians"].forEach((valore) => {
        const option = new Option(valore, valore, false, false);
        select_pol.append(option);
      });
    }else{                                                      //if no affiliation is selected, search every politician
      var url = "/v1/data-for-select";
      const data = await fetchData(url);
      data["politicians_list"].forEach((valore) => {
        const option = new Option(valore, valore, false, false);
        select_pol.append(option);
      });
      fetchAffiliations();
    }

  } else if (radio.value == "political_group") {                //else if political group was selected
    select_affiliations.prop('disabled', true).select2({        //disable affiliation select
      placeholder: '-'
    });
    select_affiliations.empty();

    var url = "/v1/data-for-select";
    const data = await fetchData(url);
    data["political_groups_list"].forEach((valore) => {
      const option = new Option(valore, valore, false, false);
      select_pol.append(option);
    });
  }

  select_pol.prop('disabled', false).select2({                  //re-enable select politician/political group
    placeholder: 'Cerca politico/partito',
    maximumSelectionLength: select_pol_length
  });
}


async function fetchChannels() {
  const select_channels = $('#select_channels');
  const old_value = select_channels.val()[0];                   //remember eventual channel that was selected
  select_channels.prop('disabled', true).select2({              //empty the select and block it while loading
    placeholder: 'Caricamento...'
  });
  select_channels.empty();

  var selected_program = "";                                    //if a program is selected, use it for filtering channels in the url
  if (
    $("#select_programs").val()[0] != undefined &&
    $("#select_programs").val()[0] != ""
  ) {
    selected_program = `&program_=${encodeURIComponent($("#select_programs").val()[0])}`
    var i = 1;
    while (true) {                                                //retrieve channels
      var url = "/v1/channels" + `?page=${i}` + selected_program;
      const data = await fetchData(url);
      data["channels"].forEach((valore) => {
        const option = new Option(valore, valore, false, false);
        select_channels.append(option);
      });
      if (data["channels"].length < data["page_size"]) break;
      i++;
    }
  } else {
    var url = "/v1/data-for-select";
    const data = await fetchData(url);
    data["channels"].forEach((valore) => {
      const option = new Option(valore, valore, false, false);
      select_channels.append(option);
    });
  }

  select_channels.prop('disabled', false).select2({             //re-enable select channels
    placeholder: 'Cerca canale',
    maximumSelectionLength: 1
  });

  if (old_value != undefined){                                  //if there was a channel selected
    select_channels.val(old_value).trigger('change');           //re-save it in the select
  }
}


async function fetchPrograms() {
  const select_programs = $('#select_programs');
  const old_value = select_programs.val()[0];                   //remember eventual program that was selected
  select_programs.prop('disabled', true).select2({              //empty the select and block it while loading
    placeholder: 'Caricamento...'
  });
  select_programs.empty();

  var selected_channel = "";                                    //if a channel is selected, use it for filtering programs in the url
  if (
    $("#select_channels").val()[0] != undefined &&
    $("#select_channels").val()[0] != ""
  ) {
    selected_channel += `&channel_=${encodeURIComponent($("#select_channels").val()[0])}`;

    var i = 1;
    while (true) {                                                //retrieve programs
      var url = "/v1/programs" + `?page=${i}` + selected_channel;
      const data = await fetchData(url);
      data["programs"].forEach((valore) => {
        const option = new Option(valore, valore, false, false);
        select_programs.append(option);
      });
      if (data["programs"].length < data["page_size"]) break;
      i++;
    }
  } else {
    var url = "/v1/data-for-select";
    const data = await fetchData(url);
    data["programs"].forEach((valore) => {
      const option = new Option(valore, valore, false, false);
      select_programs.append(option);
    });
  }

  select_programs.prop('disabled', false).select2({             //re-enable select programs
    placeholder: 'Cerca programma',
    maximumSelectionLength: 1
  });

  if (old_value != undefined){                                  //if there was a program selected
    select_programs.val(old_value).trigger('change');           //re-save it in the select
  }
}


async function fetchTopics() {
  const select_topics = $('#select_topics');
  select_topics.prop('disabled', true).select2({                //empty the select and block it while loading
    placeholder: 'Caricamento...'
  });
  select_topics.empty();

  var i = 1;
  while (true) {                                                //retrieve data
    var url = "/v1/topics" + `?page=${i}`;
    const data = await fetchData(url);
    data["topics"].forEach((valore) => {                        //insert data in select
      const option = new Option(valore, valore, false, false);
      select_topics.append(option);
    });
    if (data["topics"].length < data["page_size"]) break;
    i++;
  }

  select_topics.prop('disabled', false).select2({               //re-enable select programs
    placeholder: 'Cerca argomento',
    maximumSelectionLength: 1
  });
}


async function fetchAffiliations() {
  const select_affiliations = $('#select_affiliations');
  const old_value = select_affiliations.val()[0];               //remember eventual affiliation that was selected

  if ($("#select_pol").val().length > 1) {                      //if more politicians are selected, emtpy and disable affiliations selection
    select_affiliations.prop('disabled', true).select2({
      placeholder: '-'
    });
    select_affiliations.empty();
  
  } else if ($("#politician").is(":checked")) {                 //if radio politician is selected
    select_affiliations.prop('disabled', true).select2({        //empty the select and block it while loading
      placeholder: 'Caricamento...'
    });
    select_affiliations.empty();

    var selected_politician = "";                               //if a politician is selected, use it for filtering affiliations in the url
    if (
      $("#select_pol").val()[0] != undefined &&
      $("#select_pol").val()[0] != ""
    ) {
      selected_politician += `&politician_=${encodeURIComponent($("#select_pol").val()[0])}`;

      var i = 1;
      while (true) {                                              //retrieve affiliations
        var url = "/v1/affiliations" + `?page=${i}` + selected_politician;
        const data = await fetchData(url);
        if (data === null) {
          select_affiliations.prop('disabled', false).select2({
            placeholder: 'Cerca partito'
          });
          select_affiliations.empty();
          return;
        }
        data["affiliations"].forEach((valore) => {
          const option = new Option(valore, valore, false, false);
          select_affiliations.append(option);
        });
        if (data["affiliations"].length < data["page_size"]) break;
        i++;
      }
    } else {
      var url = "/v1/data-for-select";
      const data = await fetchData(url);
      if (data === null) {
        select_affiliations.prop('disabled', false).select2({
          placeholder: 'Cerca partito'
        });
        select_affiliations.empty();
        return;
      }
      data["affiliations"].forEach((valore) => {
        const option = new Option(valore, valore, false, false);
        select_affiliations.append(option);
      });
    }

    select_affiliations.prop('disabled', false).select2({       //re-enable select affiliations
      placeholder: 'Cerca partito',
      maximumSelectionLength: 1
    });

    if (old_value != undefined){                                //if there was an affiliation selected
      select_affiliations.val(old_value).trigger('change');     //re-save it in the select
    }
  }
}


async function updatePoliticians() {
  const select_pol = $("#select_pol");
  const selectedOption = $('input[name="choose_pol"]:checked').val();
  var rad = {};
  rad["value"] = selectedOption;                                //need a rad variable just to pass it into the handleOptionChange() function
  const old_value = select_pol.val()[0];
  handleOptionChange(rad).then(() => {                          //call handleOptionChange() function to update politicians
    if (old_value != undefined){                                //if there was an politician selected
      select_pol.val(old_value).trigger('change');              //re-save it in the select
    }
  });
}


async function initializeSelects(){                             //initialize selects
  const data = await fetchData('/v1/data-for-select');

  const select_channels = $('#select_channels');
  const select_programs = $('#select_programs');
  const select_topics = $('#select_topics');

  select_channels.prop('disabled', true).select2({
    placeholder: 'Caricamento...'
  });
  select_programs.prop('disabled', true).select2({
    placeholder: 'Caricamento...'
  });
  select_topics.prop('disabled', true).select2({
    placeholder: 'Caricamento...'
  });

  data["channels"].forEach((valore) => {                        //initialize channels select
    const option = new Option(valore, valore, false, false);
    select_channels.append(option);
  });
  select_channels.prop('disabled', false).select2({
    placeholder: 'Cerca canale',
    maximumSelectionLength: 1
  });

  data["programs"].forEach((valore) => {                        //initialize programs select
    const option = new Option(valore, valore, false, false);
    select_programs.append(option);
  });
  select_programs.prop('disabled', false).select2({
    placeholder: 'Cerca programma',
    maximumSelectionLength: 1
  });

  data["topics"].forEach((valore) => {                        //initialize topics select
    const option = new Option(valore, valore, false, false);
    select_topics.append(option);
  });
  select_topics.prop('disabled', false).select2({
    placeholder: 'Cerca argomento',
    maximumSelectionLength: 1
  });

  //initialize dates
  const start_date = document.getElementById("start_date");
  const end_date = document.getElementById("end_date");

  start_date.value = data["start_date"].replace(/\//g, "-");
  start_date.min = data["start_date"].replace(/\//g, "-");
  start_date.max = data["end_date"].replace(/\//g, "-");
  end_date.value = data["end_date"].replace(/\//g, "-");
  end_date.min = data["start_date"].replace(/\//g, "-");
  end_date.max = data["end_date"].replace(/\//g, "-");

  TOPICS.push(...data["topics"]);
}