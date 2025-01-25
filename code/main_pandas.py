from fastapi import FastAPI, Query
from starlette.responses import FileResponse
import pandas as pd
import os
import warnings
from datetime import datetime
import calendar
warnings.filterwarnings('ignore')


data = pd.read_parquet(".." + os.sep + "docs"  + os.sep +  "data" + os.sep + "agcomdata.parquet")

data["fullname"] = data['name'] + " " + data['lastname']
data['day'] = pd.to_datetime(data['day'])

data['kind'] = data['kind'].replace({'Parola': 'speech', 'Notizia': 'news'})

start_date = data.day.min().strftime('%d/%m/%Y')
end_date = data.day.max().strftime('%d/%m/%Y')

kind = ["speech", "news", "both"]

politicians = data[data.name != "political movement"]
political_groups = data[data.name == "political movement"]

channels = data.channel.unique()
programs = data.program.unique()
affiliations = data.affiliation.unique()
topics = data.topic.unique()

# -------------------------------------------------------

def validate_date(date_str):
    """
    Function to validate dates (from string to datetime)
    """
    try:
        return datetime.strptime(date_str, '%d/%m/%Y')
    except ValueError as exc:
        raise ValueError("Incorrect date format, should be DD-MM-YYYY") from exc


def filter_data(data_, start_date_, end_date_, kind_):
    """
    Function to filter data by selected date interval and kind
    """
    start_date_ = validate_date(start_date_)
    end_date_ = validate_date(end_date_)

    filtered_data = data_[
        (data_.day >= start_date_) &
        (data_.day <= end_date_)]

    if kind_ != "both":
        filtered_data = filtered_data[filtered_data.kind == kind_]

    return filtered_data

# -------------------------------------------------------

app = FastAPI()

@app.get("/")
async def read_index():
    """
    Serve the index.html file.
    """
    return FileResponse('index.html')

# -------------------------------------------------------

@app.get("/v1/politicians")
async def get_politicians(
    start_date_: str = Query(default = start_date, description="Start date"),
    end_date_: str = Query(default = end_date, description="End date"),
    kind_: str = Query(default = "both" , description="Type of data", enum = kind)
):
    """
    Return all politicians
    """
    politicians_ = filter_data(politicians, start_date_, end_date_, kind_)
    politicians_ = politicians_.fullname.unique().tolist()

    return { "politicians": politicians_ }



@app.get("/v1/political_groups")
async def get_political_groups(
    start_date_: str = Query(default = start_date, description="Start date"),
    end_date_: str = Query(default = end_date, description="End date"),
    kind_: str = Query(default = "both" , description="Type of data", enum = kind)
):
    """
    Return all political groups
    """

    political_groups_ = filter_data(political_groups, start_date_, end_date_, kind_)
    political_groups_ = political_groups_.lastname.unique().tolist()

    return { "political_groups": political_groups_ }


@app.get("/v1/channels")
async def get_channels():
    """
    Return all channels
    """

    channels_ = data.channel.unique().tolist()

    return { "channels": channels_ }


@app.get("/v1/programs")
async def get_programs():
    """
    Return all programs
    """
    programs_ = data.program.unique().tolist()

    return { "programs": programs_ }


@app.get("/v1/affiliations")
async def get_affiliations():
    """
    Return all affiliations
    """

    affiliations_ = data.affiliation.unique().tolist()

    return { "affiliations": affiliations_ }


@app.get("/v1/topics")
async def get_topics():
    """
    Return all topics
    """

    topics_ = data.topic.unique().tolist()

    return { "topics": topics_ }

# -------------------------------------------------------

@app.get("/v1/politicianTopics/{name}")
async def get_politician_topics(
    name: str,
    start_date_: str = Query(default = start_date, description="Start date"),
    end_date_: str = Query(default = end_date, description="End date"),
    kind_: str = Query(default = "both" , description="Type of data", enum = kind)
):
    """
    Return how much a politician talked about all the possible topics
    """

    politician_topics = politicians[politicians['fullname'] == name]
    politician_topics = filter_data(politician_topics, start_date_, end_date_, kind_)
    final_list = []

    for t in topics:
        temp = politician_topics[politician_topics.topic == t]
        total = temp["duration"].sum()
        interventions = temp.shape[0]
        final_list.append({"topic": t,
                           "minutes" : int(total),
                           "interventions" : int(interventions) })

    return { "politician": name, "topics": final_list }


@app.get("/v1/polGroupTopics/{name}")
async def get_political_group_topics(
    name: str,
    start_date_: str = Query(default = start_date, description="Start date"),
    end_date_: str = Query(default = end_date, description="End date"),
    kind_: str = Query(default = "both" , description="Type of data", enum = kind)
):
    """
    Return how much a political group talked about all the possible topics 
    """
    polgroup_topics = political_groups[political_groups.lastname == name]
    polgroup_topics = filter_data(polgroup_topics, start_date_, end_date_, kind_)
    final_list = []

    for t in topics:
        temp = polgroup_topics[polgroup_topics.topic == t]
        total = temp["duration"].sum()
        interventions = temp.shape[0]
        final_list.append({"topic": t,
                           "minutes" : int(total),
                           "interventions" : int(interventions) })

    return { "political group": name, "topics": final_list }

# -------------------------------------------------------

@app.get("/v1/politicianChannels/{name}")
async def get_politician_channels(
    name: str,
    start_date_: str = Query(default = start_date, description="Start date"),
    end_date_: str = Query(default = end_date, description="End date"),
    kind_: str = Query(default = "both" , description="Type of data", enum = kind)
):
    """
    Return how much a politician talked in a specific channel
    """

    politician_channels = politicians[politicians['fullname'] == name]
    politician_channels = filter_data(politician_channels, start_date_, end_date_, kind_)
    final_list = []

    for c in channels:
        temp = politician_channels[politician_channels['channel'] == c]
        total = temp["duration"].sum()
        interventions = temp.shape[0]
        final_list.append({"channel": c,
                           "minutes" : int(total),
                           "interventions" : int(interventions)})

    return { "politician": name, "channels": final_list }


@app.get("/v1/polGroupChannels/{name}")
async def get_political_group_channels(
    name: str,
    start_date_: str = Query(default = start_date, description="Start date"),
    end_date_: str = Query(default = end_date, description="End date"),
    kind_: str = Query(default = "both" , description="Type of data", enum = kind)
):
    """
    Return how much a political group talked in a specific channel
    """
    polgroup_channels = political_groups[political_groups.lastname == name]
    polgroup_channels = filter_data(polgroup_channels, start_date_, end_date_, kind_)
    final_list = []

    for c in channels:
        temp = polgroup_channels[polgroup_channels.channel == c]
        total = temp["duration"].sum()
        interventions = temp.shape[0]
        final_list.append({"channel": c,
                           "minutes" : int(total),
                           "interventions" : int(interventions) })

    return { "political group": name, "channels": final_list }

# -------------------------------------------------------

@app.get("/v1/politiciansAffiliation/{name}")
async def get_politicians_affiliation(
    name: str,
    start_date_: str = Query(default = start_date, description="Start date"),
    end_date_: str = Query(default = end_date, description="End date"),
    kind_: str = Query(default = "both" , description="Type of data", enum = kind)
):
    """
    Return how many politicians participate (have participated) in an affiliation
    """

    politicians_affiliation = politicians[politicians.affiliation == name]
    politicians_affiliation = filter_data(politicians_affiliation, start_date_, end_date_, kind_)
    final_list = politicians_affiliation.fullname.unique().tolist()

    return { "affiliation": name, "politicians": final_list}


@app.get("/v1/affiliationsPolitician/{name}")
async def get_affiliations_politician(
    name: str,
    start_date_: str = Query(default = start_date, description="Start date"),
    end_date_: str = Query(default = end_date, description="End date"),
    kind_: str = Query(default = "both" , description="Type of data", enum = kind)
):
    """
    Return how many affiliations a politician have participated in
    """

    affiliations_politician = politicians[politicians.fullname == name]
    affiliations_politician = filter_data(affiliations_politician, start_date_, end_date_, kind_)
    final_list = affiliations_politician.affiliation.unique().tolist()

    return { "politician": name, "affiliations": final_list}

# -------------------------------------------------------

@app.get("/v1/interventionsPoliticalGroup/{name}")
async def get_interventions_political_group(
    name: str,
    start_date_: str = Query(default = start_date, description="Start date"),
    end_date_: str = Query(default = end_date, description="End date"),
    kind_: str = Query(default = "both" , description="Type of data", enum = kind)
):
    """
    Return how much a political group has intervened in tv 
    (counting also politicians single intervents)
    """

    interventions_polgroup = data[data.affiliation == name]
    interventions_polgroup = filter_data(interventions_polgroup, start_date_, end_date_, kind_)
    interventions = interventions_polgroup.shape[0]
    minutes = interventions_polgroup.duration.sum()


    return { "political group": name, "interventions": int(interventions), "minutes": int(minutes) }
