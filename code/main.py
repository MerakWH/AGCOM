"""
This module provides a series of RESTful APIs to provide data
gathered from the agcomdata.parquet file.

Author: Merak Winston Hall
Date: 2024-07-13
"""

import os
import warnings
from datetime import datetime
import datetime as dt
from fastapi import FastAPI, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse
import boto3
import polars as pl
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
import io
warnings.filterwarnings('ignore')


# Configura le variabili d'ambiente per le credenziali AWS
AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
REGION_NAME = os.getenv('AWS_REGION', 'eu-north-1')
BUCKET_NAME = os.getenv('BUCKET_NAME', 'agcom-parquet')
S3_FILE_PATH = 'agcomdata.parquet'  # percorso del file in S3


def read_parquet_from_s3():
    try:
        # Crea client S3
        s3_client = boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY,
            region_name=REGION_NAME
        )

        # Scarica il file in memoria
        response = s3_client.get_object(Bucket=BUCKET_NAME, Key=S3_FILE_PATH)
        file_stream = io.BytesIO(response['Body'].read())

        # Legge come LazyFrame
        return pl.scan_parquet(file_stream)

    except (NoCredentialsError, PartialCredentialsError):
        raise HTTPException(status_code=403, detail="AWS credentials error")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading from S3: {e}")

# Caricamento Lazy dei dati
data = read_parquet_from_s3()

# Aggiunge la colonna fullname e modifica "kind"
data = data.with_columns([
    (pl.col("name") + " " + pl.col("lastname")).alias("fullname"),
    pl.col("kind").replace({"Parola": "speech", "Notizia": "news"}).alias("kind")
])

politicians = data.filter(pl.col("name") != "Soggetto collettivo")
politicians_list = politicians.select("fullname").unique().collect().to_series().to_list()

political_groups = data.filter(pl.col("name") == "Soggetto collettivo")
political_groups_list = political_groups.select('lastname').unique().collect().to_series().to_list()

start_date = data.select(pl.min("day")).collect().to_series()[0].strftime('%Y/%m/%d')
end_date = data.select(pl.max("day")).collect().to_series()[0].strftime('%Y/%m/%d')

kind = ["speech", "news", "both"]

channels = data.select("channel").unique().collect().to_series().to_list()
programs = data.select('program').unique().collect().to_series().to_list()
affiliations = data.select('affiliation').unique().collect().to_series().to_list()
topics = data.select('topic').unique().collect().to_series().to_list()

# -------------------------------------------------------

def validate_date(date_str):
    """
    Function to validate dates (from string to datetime)
    """
    try:
        return datetime.strptime(date_str, '%Y/%m/%d')
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY/MM/DD") from exc


def filter_data(data_, start_date_, end_date_, kind_):
    """
    Function to filter data by selected date interval and kind
    """
    start_date_ = validate_date(start_date_)
    end_date_ = validate_date(end_date_)

    if start_date_ > end_date_:
        raise HTTPException(status_code=400, detail="Start date must be before end date")

    filtered_data = data_.filter(pl.col("day") >= start_date_).filter(pl.col("day") <= end_date_)


    if kind_ != "both":
        filtered_data = filtered_data.filter(pl.col("kind") == kind_)

    return filtered_data

# -------------------------------------------------------

description = """
## AGCOM - elementary data of the italian television monitoring

This API provides the possibility to query the elementary televised monitoring data provided by [AGCOM](https://www.agcom.it/) - Italian authority for guarantees in communications - of political interventions (data as news or as word)

The data can be found in XML format at [https://www.agcom.it/dati-elementari-di-monitoraggio-televisivo](https://www.agcom.it/dati-elementari-di-monitoraggio-televisivo)

Period:<br/>
from **%s** to **%s**


The license under which the data is released by AGCOM is CC-BY-SA-NC

![](https://www.agcom.it/documents/10179/4502194/Logo+Creative+common/2e1fe5a2-4324-4965-b8af-76403bb42b15?t=1618583317352)

""" % (start_date, end_date)

app = FastAPI(
    title="AGCOM - dati elementari di monitoraggio televisivo",
    description=description,
    version="0.0.1",
    contact={
        "name": "Merak",
        "email": "merakwinston.hall@gmail.com",
    },
    license_info={
        "name": "data under cc-by-nc-sa",
        "url": "https://creativecommons.org/licenses/by-nc-sa/4.0/"
    },
)

app.mount("/static", StaticFiles(directory="code/static"), name="static")

@app.get("/")
async def read_index():
    """
    Serve the home.html file.
    """
    return FileResponse('code/templates/home.html')

@app.get("/index")
async def read_charts():
    """
    Serve the index.html file.
    """
    return FileResponse('code/templates/index.html')

@app.get("/faq")
async def read_faq():
    """
    Serve the pages-faq.html file.
    """
    return FileResponse('code/templates/pages-faq.html')

@app.get("/contact")
async def contact():
    """
    Serve the pages-contact.html file.
    """
    return FileResponse('code/templates/pages-contact.html')

# -------------------------------------------------------

@app.get("/v1/politicians")
async def get_politicians(
    start_date_: str = Query(default=start_date, description="Start date"),
    end_date_: str = Query(default=end_date, description="End date"),
    kind_: str = Query(default="both", description="Type of data", enum=kind),
    page: int = Query(default=1, description="Page number"),
    page_size: int = Query(default=15000, description="Page size")
):
    """
    Return all politicians with pagination
    """
    if page < 1 or page_size < 1:
        raise HTTPException(status_code=400, detail="Page and page size must be positive integers.")

    politicians_ = filter_data(politicians, start_date_, end_date_, kind_)
    politicians_ = politicians_.select('fullname').unique().collect().to_series().to_list()
    politicians_.sort()

    # Calcola gli offset per la paginazione
    start = (page - 1) * page_size
    end = start + page_size

    paginated_politicians = politicians_[start:end]

    return {
        "total": len(politicians_),
        "politicians": paginated_politicians
    }


@app.get("/v1/political-groups")
async def get_political_groups(
    start_date_: str = Query(default = start_date, description="Start date"),
    end_date_: str = Query(default = end_date, description="End date"),
    kind_: str = Query(default = "both" , description="Type of data", enum = kind),
    page: int = Query(default=1, description="Page number"),
    page_size: int = Query(default=15000, description="Page size")
):
    """
    Return all political groups
    """
    if page < 1 or page_size < 1:
        raise HTTPException(status_code=400, detail="Page and page size must be positive integers.")

    political_groups_ = filter_data(political_groups, start_date_, end_date_, kind_)
    political_groups_ = political_groups_.select('lastname').unique().collect().to_series().to_list()
    political_groups_.sort()

    # Calcola gli offset per la paginazione
    start = (page - 1) * page_size
    end = start + page_size

    paginated_political_groups = political_groups_[start:end]

    return {
        "total": len(political_groups_),
        "political groups": paginated_political_groups
    }


@app.get("/v1/channels")
async def get_channels(
    page: int = Query(default=1, description="Page number"),
    page_size: int = Query(default=15000, description="Page size"),
    program_: str = Query(default = "all", description="Program")
):
    """
    Return all channels
    """
    filtered_data = data

    if program_ != "all":
        if program_ not in programs:
            raise HTTPException(status_code=400, detail="Invalid program")
        filtered_data = filtered_data.filter(pl.col('program') == program_)

    channels_ = filtered_data.select('channel').unique().collect().to_series().to_list()
    channels_.sort()

    start = (page - 1) * page_size
    end = start + page_size

    paginated_channels = channels_[start:end]

    return { "channels": paginated_channels }


@app.get("/v1/programs")
async def get_programs(
    page: int = Query(default=1, description="Page number"),
    page_size: int = Query(default=15000, description="Page size"),
    channel_: str = Query(default = "all", description="Channel")
):
    """
    Return all programs
    """
    filtered_data = data

    if channel_ != "all":
        if channel_ not in channels:
            raise HTTPException(status_code=400, detail="Invalid channel")
        filtered_data = filtered_data.filter(pl.col('channel') == channel_)

    programs_ = filtered_data.select('program').unique().collect().to_series().to_list()
    programs_.sort()

    start = (page - 1) * page_size
    end = start + page_size

    paginated_programs = programs_[start:end]

    return { "programs": paginated_programs }


@app.get("/v1/affiliations")
async def get_affiliations(
    page: int = Query(default=1, description="Page number"),
    page_size: int = Query(default=15000, description="Page size"),
    politician_: str = Query(default = "all", description="Politician")
):
    """
    Return all affiliations
    """
    filtered_data = data

    if politician_ != "all":
        if politician_ not in politicians_list:
            raise HTTPException(status_code=400, detail="Invalid politician")
        filtered_data = filtered_data.filter(pl.col('fullname') == politician_)

    affiliations_ = filtered_data.select('affiliation').unique().collect().to_series().to_list()
    affiliations_.sort()

    start = (page - 1) * page_size
    end = start + page_size

    paginated_affiliations = affiliations_[start:end]

    return { "affiliations": paginated_affiliations }


@app.get("/v1/topics")
async def get_topics(
    page: int = Query(default=1, description="Page number"),
    page_size: int = Query(default=15000, description="Page size")
):
    """
    Return all topics
    """

    topics_ = data.select('topic').unique().collect().to_series().to_list()
    topics_.sort()

    start = (page - 1) * page_size
    end = start + page_size

    paginated_topics_ = topics_[start:end]

    return { "topics": paginated_topics_ }

# -------------------------------------------------------

@app.get("/v1/politician-topics/{name}")
async def get_politician_topics(
    name: str,
    start_date_: str = Query(default = start_date, description="Start date"),
    end_date_: str = Query(default = end_date, description="End date"),
    kind_: str = Query(default = "both" , description="Type of data", enum = kind),
    channel_: str = Query(default = "all", description="Channel"),
    affiliation_: str = Query(default = "all", description="Affiliation"),
    program_: str = Query(default = "all", description="Program"),
    topic_: str = Query(default = "all", description="Topic"),
    page: int = Query(default=1, description="Page number"),
    page_size: int = Query(default=100, description="Page size")
):
    """
    Return how much a politician talked about all the possible topics
    """
    filtered_data = politicians

    if name not in politicians_list:
        raise HTTPException(status_code=400, detail="Politician not found")
    filtered_data = filtered_data.filter(pl.col('fullname') == name)

    if channel_ != "all":
        if channel_ not in channels:
            raise HTTPException(status_code=400, detail="Invalid channel")
        filtered_data = filtered_data.filter(pl.col('channel') == channel_)

    if affiliation_ != "all":
        if affiliation_ not in affiliations:
            raise HTTPException(status_code=400, detail="Invalid affiliation")
        filtered_data = filtered_data.filter(pl.col('affiliation') == affiliation_)

    if program_ != "all":
        if program_ not in programs:
            raise HTTPException(status_code=400, detail="Invalid program")
        filtered_data = filtered_data.filter(pl.col('program') == program_)

    if topic_ != "all":
        if topic_ not in topics:
            raise HTTPException(status_code=400, detail="Invalid topic")
        filtered_data = filtered_data.filter(pl.col('topic') == topic_)

    politician_topics = filter_data(filtered_data, start_date_, end_date_, kind_)
    final_list = []
    start = (page - 1) * page_size
    end = start + page_size

    for t in topics:
        temp = politician_topics.filter(pl.col('topic') == t)
        total = temp.select('duration').sum().collect().to_series().to_list()
        interventions = temp.select(pl.len()).collect().item()
        final_list.append({"topic": t,
                           "minutes" : total[0],
                           "interventions" : interventions })

    paginated_list = final_list[start:end]

    return { "politician": name, "topics": paginated_list }


@app.get("/v1/political-group-topics/{name}")
async def get_political_group_topics(
    name: str,
    start_date_: str = Query(default = start_date, description="Start date"),
    end_date_: str = Query(default = end_date, description="End date"),
    kind_: str = Query(default = "both" , description="Type of data", enum = kind),
    channel_: str = Query(default = "all", description="Channel"),
    program_: str = Query(default = "all", description="Program"),
    topic_: str = Query(default = "all", description="Topic"),
    page: int = Query(default=1, description="Page number"),
    page_size: int = Query(default=100, description="Page size")
):
    """
    Return how much a political group talked about all the possible topics 
    """
    filtered_data = political_groups

    if name not in political_groups_list:
        raise HTTPException(status_code=400, detail="Political Group not found")
    filtered_data = filtered_data.filter(pl.col('lastname') == name)

    if channel_ != "all":
        if channel_ not in channels:
            raise HTTPException(status_code=400, detail="Invalid channel")
        filtered_data = filtered_data.filter(pl.col('channel') == channel_)

    if program_ != "all":
        if program_ not in programs:
            raise HTTPException(status_code=400, detail="Invalid program")
        filtered_data = filtered_data.filter(pl.col('program') == program_)

    if topic_ != "all":
        if topic_ not in topics:
            raise HTTPException(status_code=400, detail="Invalid topic")
        filtered_data = filtered_data.filter(pl.col('topic') == topic_)

    polgroup_topics = filter_data(filtered_data, start_date_, end_date_, kind_)
    final_list = []
    start = (page - 1) * page_size
    end = start + page_size

    for t in topics:
        temp = polgroup_topics.filter(pl.col('topic') == t)
        total = temp.select('duration').sum().collect().to_series().to_list()
        interventions = temp.select(pl.len()).collect().item()
        final_list.append({"topic": t,
                           "minutes" : total[0],
                           "interventions" : interventions })

    paginated_list = final_list[start:end]

    return { "political group": name, "topics": paginated_list }

# -------------------------------------------------------

@app.get("/v1/politician-channels/{name}")
async def get_politician_channels(
    name: str,
    start_date_: str = Query(default = start_date, description="Start date"),
    end_date_: str = Query(default = end_date, description="End date"),
    kind_: str = Query(default = "both" , description="Type of data", enum = kind),
    channel_: str = Query(default = "all", description="Channel"),
    affiliation_: str = Query(default = "all", description="Affiliation"),
    program_: str = Query(default = "all", description="Program"),
    topic_: str = Query(default = "all", description="Topic"),
    page: int = Query(default=1, description="Page number"),
    page_size: int = Query(default=100, description="Page size")
):
    """
    Return how much a politician talked in a specific channel
    """
    filtered_data = politicians

    if name not in politicians_list:
        raise HTTPException(status_code=400, detail="Politician not found")
    filtered_data = filtered_data.filter(pl.col('fullname') == name)

    if channel_ != "all":
        if channel_ not in channels:
            raise HTTPException(status_code=400, detail="Invalid channel")
        filtered_data = filtered_data.filter(pl.col('channel') == channel_)

    if affiliation_ != "all":
        if affiliation_ not in affiliations:
            raise HTTPException(status_code=400, detail="Invalid affiliation")
        filtered_data = filtered_data.filter(pl.col('affiliation') == affiliation_)

    if program_ != "all":
        if program_ not in programs:
            raise HTTPException(status_code=400, detail="Invalid program")
        filtered_data = filtered_data.filter(pl.col('program') == program_)

    if topic_ != "all":
        if topic_ not in topics:
            raise HTTPException(status_code=400, detail="Invalid topic")
        filtered_data = filtered_data.filter(pl.col('topic') == topic_)

    politician_channels = filter_data(filtered_data, start_date_, end_date_, kind_)
    channels_list = politician_channels.select('channel').unique().collect().to_series().to_list()
    channels_list.sort()
    final_list = []
    start = (page - 1) * page_size
    end = start + page_size

    for c in channels_list:
        temp = politician_channels.filter(pl.col('channel') == c)
        total = temp.select('duration').sum().collect().to_series().to_list()
        interventions = temp.select(pl.len()).collect().item()
        final_list.append({"channel": c,
                           "minutes" : total[0],
                           "interventions" : interventions })

    paginated_list = final_list[start:end]

    return { "politician": name, "channels": paginated_list }


@app.get("/v1/political-group-channels/{name}")
async def get_political_group_channels(
    name: str,
    start_date_: str = Query(default = start_date, description="Start date"),
    end_date_: str = Query(default = end_date, description="End date"),
    kind_: str = Query(default = "both" , description="Type of data", enum = kind),
    channel_: str = Query(default = "all", description="Channel"),
    program_: str = Query(default = "all", description="Program"),
    topic_: str = Query(default = "all", description="Topic"),
    page: int = Query(default=1, description="Page number"),
    page_size: int = Query(default=100, description="Page size")
):
    """
    Return how much a political group talked in a specific channel
    """
    filtered_data = political_groups

    if name not in political_groups_list:
        raise HTTPException(status_code=400, detail="Political Group not found")
    filtered_data = filtered_data.filter(pl.col('lastname') == name)

    if channel_ != "all":
        if channel_ not in channels:
            raise HTTPException(status_code=400, detail="Invalid channel")
        filtered_data = filtered_data.filter(pl.col('channel') == channel_)

    if program_ != "all":
        if program_ not in programs:
            raise HTTPException(status_code=400, detail="Invalid program")
        filtered_data = filtered_data.filter(pl.col('program') == program_)

    if topic_ != "all":
        if topic_ not in topics:
            raise HTTPException(status_code=400, detail="Invalid topic")
        filtered_data = filtered_data.filter(pl.col('topic') == topic_)

    polgroup_channels = filter_data(filtered_data, start_date_, end_date_, kind_)
    channels_list = polgroup_channels.select('channel').unique().collect().to_series().to_list()
    channels_list.sort()
    final_list = []
    start = (page - 1) * page_size
    end = start + page_size

    for c in channels_list:
        temp = polgroup_channels.filter(pl.col('channel') == c)
        total = temp.select('duration').sum().collect().to_series().to_list()
        interventions = temp.select(pl.len()).collect().item()
        final_list.append({"channel": c,
                           "minutes" : total[0],
                           "interventions" : interventions })

    paginated_list = final_list[start:end]

    return { "political group": name, "channels": paginated_list }

# -------------------------------------------------------

@app.get("/v1/politicians-affiliation/{name}")
async def get_politicians_affiliation(
    name: str,
):
    """
    Return how many politicians participate (have participated) in an affiliation
    """
    if name not in affiliations:
        raise HTTPException(status_code=400, detail="Invalid affiliation")
    politicians_affiliation = politicians.filter(pl.col('affiliation') == name)
    final_list = politicians_affiliation.select('fullname').unique().collect().to_series().to_list()

    return { "affiliation": name, "politicians": final_list }


@app.get("/v1/affiliations-politician/{name}")
async def get_affiliations_politician(
    name: str,
):
    """
    Return how many affiliations a politician have participated in
    """
    if name not in politicians_list:
        raise HTTPException(status_code=400, detail="Invalid politician")
    affiliations_politician = politicians.filter(pl.col('fullname') == name)
    final_list = affiliations_politician.select('affiliation').unique().collect().to_series().to_list()

    return { "politician": name, "affiliations": final_list}

# -------------------------------------------------------

@app.get("/v1/interventions-political-group/{name}")
async def get_interventions_political_group(
    name: str,
    start_date_: str = Query(default = start_date, description="Start date"),
    end_date_: str = Query(default = end_date, description="End date"),
    kind_: str = Query(default = "both" , description="Type of data", enum = kind),
    channel_: str = Query(default = "all", description="Channel"),
    program_: str = Query(default = "all", description="Program"),
    topic_: str = Query(default = "all", description="Topic")
):
    """
    Return how much a political group has intervened in tv 
    (counting also politicians single intervents)
    """
    filtered_data = data

    if name not in affiliations:
        raise HTTPException(status_code=400, detail="Political Group not found")
    filtered_data = filtered_data.filter(pl.col('affiliation') == name)

    if channel_ != "all":
        if channel_ not in channels:
            raise HTTPException(status_code=400, detail="Invalid channel")
        filtered_data = filtered_data.filter(pl.col('channel') == channel_)

    if program_ != "all":
        if program_ not in programs:
            raise HTTPException(status_code=400, detail="Invalid program")
        filtered_data = filtered_data.filter(pl.col('program') == program_)

    if topic_ != "all":
        if topic_ not in topics:
            raise HTTPException(status_code=400, detail="Invalid topic")
        filtered_data = filtered_data.filter(pl.col('topic') == topic_)

    interventions_polgroup = filter_data(filtered_data, start_date_, end_date_, kind_)
    interventions = interventions_polgroup.select(pl.len()).collect().item()
    minutes = interventions_polgroup.select('duration').sum().collect().to_series().to_list()

    return { "political group": name, "interventions": interventions, "minutes": minutes[0] }

# -------------------------------------------------------

@app.get("/v1/dates")
async def get_dates():
    """
    Return the first and last date of the dataset
    """
    start_date_ = data.select('day').min().collect().to_series()[0].strftime('%Y-%m-%d')
    end_date_ = data.select('day').max().collect().to_series()[0].strftime('%Y-%m-%d')

    return { "first_date": start_date_, "end_date": end_date_}

# -------------------------------------------------------

@app.get("/v1/interventions-politician-per-year/{name}")
async def get_interventions_politician_per_year(
    name: str,
    start_date_: str = Query(default = start_date, description="Start date"),
    end_date_: str = Query(default = end_date, description="End date"),
    kind_: str = Query(default = "both" , description="Type of data", enum = kind),
    channel_: str = Query(default = "all", description="Channel"),
    affiliation_: str = Query(default = "all", description="Affiliation"),
    program_: str = Query(default = "all", description="Program"),
    topic_: str = Query(default = "all", description="Topic")
):
    """
    Return how much a politician has intervened in tv per year
    """
    filtered_data = politicians

    if name not in politicians_list:
        raise HTTPException(status_code=400, detail="Politician not found")
    filtered_data = filtered_data.filter(pl.col('fullname') == name)

    if channel_ != "all":
        if channel_ not in channels:
            raise HTTPException(status_code=400, detail="Invalid channel")
        filtered_data = filtered_data.filter(pl.col('channel') == channel_)

    if affiliation_ != "all":
        if affiliation_ not in affiliations:
            raise HTTPException(status_code=400, detail="Invalid affiliation")
        filtered_data = filtered_data.filter(pl.col('affiliation') == affiliation_)

    if program_ != "all":
        if program_ not in programs:
            raise HTTPException(status_code=400, detail="Invalid program")
        filtered_data = filtered_data.filter(pl.col('program') == program_)

    if topic_ != "all":
        if topic_ not in topics:
            raise HTTPException(status_code=400, detail="Invalid topic")
        filtered_data = filtered_data.filter(pl.col('topic') == topic_)

    interventions_politician = filter_data(filtered_data, start_date_, end_date_, kind_)

    first_year = int(start_date_.split('/')[0])
    last_year = int(end_date_.split('/')[0])

    years = []
    interventions = []
    minutes = []
    total_minutes = 0

    while first_year != (last_year + 1):
        fy = datetime.strptime(str(first_year), '%Y')
        ly = datetime.strptime(str(first_year + 1), '%Y')
        a = interventions_politician.filter(pl.col('day') >= fy)
        a = a.filter(pl.col('day') <= ly)
        years.append(str(first_year))
        interventions.append(a.select(pl.len()).collect().item())
        minutes.append(a.select('duration').sum().collect().to_series().to_list()[0])
        total_minutes += a.select('duration').sum().collect().to_series().to_list()[0]
        first_year += 1

    return { "politician": name, "years": years,
            "interventions": interventions, "minutes": minutes, "total": total_minutes }


@app.get("/v1/interventions-political-group-per-year/{name}")
async def get_interventions_political_group_per_year(
    name: str,
    start_date_: str = Query(default = start_date, description="Start date"),
    end_date_: str = Query(default = end_date, description="End date"),
    kind_: str = Query(default = "both" , description="Type of data", enum = kind),
    channel_: str = Query(default = "all", description="Channel"),
    program_: str = Query(default = "all", description="Program"),
    topic_: str = Query(default = "all", description="Topic")
):
    """
    Return how much a political group has intervened in tv per year
    """
    filtered_data = political_groups

    if name not in political_groups_list:
        raise HTTPException(status_code=400, detail="Political Group not found")
    filtered_data = filtered_data.filter(pl.col('lastname') == name)

    if channel_ != "all":
        if channel_ not in channels:
            raise HTTPException(status_code=400, detail="Invalid channel")
        filtered_data = filtered_data.filter(pl.col('channel') == channel_)

    if program_ != "all":
        if program_ not in programs:
            raise HTTPException(status_code=400, detail="Invalid program")
        filtered_data = filtered_data.filter(pl.col('program') == program_)

    if topic_ != "all":
        if topic_ not in topics:
            raise HTTPException(status_code=400, detail="Invalid topic")
        filtered_data = filtered_data.filter(pl.col('topic') == topic_)

    interventions_polgroup = filter_data(filtered_data, start_date_, end_date_, kind_)

    first_year = int(start_date_.split('/')[0])
    last_year = int(end_date_.split('/')[0])

    years = []
    interventions = []
    minutes = []
    total_minutes = 0

    while first_year != (last_year + 1):
        fy = datetime.strptime(str(first_year), '%Y')
        ly = datetime.strptime(str(first_year + 1), '%Y')
        a = interventions_polgroup.filter(pl.col('day') >= fy)
        a = a.filter(pl.col('day') <= ly)
        years.append(first_year)
        interventions.append(a.select(pl.len()).collect().item())
        minutes.append(a.select('duration').sum().collect().to_series().to_list()[0])
        total_minutes += a.select('duration').sum().collect().to_series().to_list()[0]
        first_year += 1

    return { "political group": name, "years": years,
            "interventions": interventions, "minutes": minutes, "total": total_minutes }

# -------------------------------------------------------

@app.get("/v1/interventions-politician-per-day/{name}")
async def get_interventions_politician_per_day(
    name: str,
    start_date_: str = Query(default = start_date, description="Start date"),
    end_date_: str = Query(default = end_date, description="End date"),
    kind_: str = Query(default = "both" , description="Type of data", enum = kind),
    channel_: str = Query(default = "all", description="Channel"),
    affiliation_: str = Query(default = "all", description="Affiliation"),
    program_: str = Query(default = "all", description="Program"),
    topic_: str = Query(default = "all", description="Topic"),
    page: int = Query(default=1, description="Page number"),
    page_size: int = Query(default=1, description="Page size")
):
    """
    Return how much a politician has intervened in tv per day
    """
    filtered_data = politicians

    if name not in politicians_list:
        raise HTTPException(status_code=400, detail="Politician not found")
    filtered_data = filtered_data.filter(pl.col('fullname') == name)

    if channel_ != "all":
        if channel_ not in channels:
            raise HTTPException(status_code=400, detail="Invalid channel")
        filtered_data = filtered_data.filter(pl.col('channel') == channel_)

    if affiliation_ != "all":
        if affiliation_ not in affiliations:
            raise HTTPException(status_code=400, detail="Invalid affiliation")
        filtered_data = filtered_data.filter(pl.col('affiliation') == affiliation_)

    if program_ != "all":
        if program_ not in programs:
            raise HTTPException(status_code=400, detail="Invalid program")
        filtered_data = filtered_data.filter(pl.col('program') == program_)

    if topic_ != "all":
        if topic_ not in topics:
            raise HTTPException(status_code=400, detail="Invalid topic")
        filtered_data = filtered_data.filter(pl.col('topic') == topic_)

    interventions_politician = filter_data(filtered_data, start_date_, end_date_, kind_)

    batch_size = 5000
    calendar_list = []

    batch_index = 0
    batch = interventions_politician.slice(batch_index, batch_size).collect()

    while batch.height != 0:
        calendar_list.extend(batch.select("day").to_series().to_list())
        batch_index += batch_size
        batch = interventions_politician.slice(batch_index, batch_size).collect()

    return {}


@app.get("/v1/interventions-political-group-per-day/{name}")
async def get_interventions_political_group_per_day(
    name: str,
    start_date_: str = Query(default = start_date, description="Start date"),
    end_date_: str = Query(default = end_date, description="End date"),
    kind_: str = Query(default = "both" , description="Type of data", enum = kind),
    channel_: str = Query(default = "all", description="Channel"),
    program_: str = Query(default = "all", description="Program"),
    topic_: str = Query(default = "all", description="Topic"),
    page: int = Query(default=1, description="Page number"),
    page_size: int = Query(default=10, description="Page size")
):
    """
    Return how much a political group has intervened in tv per day
    """
    filtered_data = political_groups

    if name not in political_groups_list:
        raise HTTPException(status_code=400, detail="Political Group not found")
    filtered_data = filtered_data.filter(pl.col('lastname') == name)

    if channel_ != "all":
        if channel_ not in channels:
            raise HTTPException(status_code=400, detail="Invalid channel")
        filtered_data = filtered_data.filter(pl.col('channel') == channel_)

    if program_ != "all":
        if program_ not in programs:
            raise HTTPException(status_code=400, detail="Invalid program")
        filtered_data = filtered_data.filter(pl.col('program') == program_)

    if topic_ != "all":
        if topic_ not in topics:
            raise HTTPException(status_code=400, detail="Invalid topic")
        filtered_data = filtered_data.filter(pl.col('topic') == topic_)

    interventions_polgroup = filter_data(filtered_data, start_date_, end_date_, kind_)
    start = (page - 1) * page_size
    end = start + page_size

    begin_date = dt.date(int(start_date_.split('/')[0]),
                         int(start_date_.split('/')[1]),
                         int(start_date_.split('/')[2]))
    b = begin_date
    final_date = dt.date(int(end_date_.split('/')[0]),
                         int(end_date_.split('/')[1]),
                         int(end_date_.split('/')[2]))
    day = dt.timedelta(1)
    year = begin_date.year
    interventions = []
    i = []
    max_value = 0

    while begin_date != final_date:
        if begin_date.year != year:
            interventions.append(i)
            year = year + 1
            for j in i:
                if max_value < j[1]:
                    max_value = j[1]
            i = []
        else:
            d = datetime.strptime(str(begin_date), "%Y-%m-%d")
            temp = interventions_polgroup.filter(pl.col("day") == d)
            i.append([begin_date, temp.select(pl.len()).collect().item()])
            begin_date = begin_date + day
    interventions.append(i)

    paginated_list = interventions[start:end]

    return { "political group": name, "interventions": paginated_list, "max_value": max_value,
            "begin year": b.year, "final year": final_date.year}

# -------------------------------------------------------

@app.get("/v1/politician-channels-programs/{name}")
async def get_politician_channels_programs(
    name: str,
    start_date_: str = Query(default = start_date, description="Start date"),
    end_date_: str = Query(default = end_date, description="End date"),
    kind_: str = Query(default = "both" , description="Type of data", enum = kind),
    channel_: str = Query(default = "all", description="Channel"),
    affiliation_: str = Query(default = "all", description="Affiliation"),
    program_: str = Query(default = "all", description="Program"),
    topic_: str = Query(default = "all", description="Topic")
):
    """
    Return every channel a politician talked in, specifying for each 
    channel all the programs he participated in and for how long (minutes)
    """
    filtered_data = politicians

    if name not in politicians_list:
        raise HTTPException(status_code=400, detail="Politician not found")
    filtered_data = filtered_data.filter(pl.col('fullname') == name)

    if channel_ != "all":
        if channel_ not in channels:
            raise HTTPException(status_code=400, detail="Invalid channel")
        filtered_data = filtered_data.filter(pl.col('channel') == channel_)

    if affiliation_ != "all":
        if affiliation_ not in affiliations:
            raise HTTPException(status_code=400, detail="Invalid affiliation")
        filtered_data = filtered_data.filter(pl.col('affiliation') == affiliation_)

    if program_ != "all":
        if program_ not in programs:
            raise HTTPException(status_code=400, detail="Invalid program")
        filtered_data = filtered_data.filter(pl.col('program') == program_)

    if topic_ != "all":
        if topic_ not in topics:
            raise HTTPException(status_code=400, detail="Invalid topic")
        filtered_data = filtered_data.filter(pl.col('topic') == topic_)

    politician_channels = filter_data(filtered_data, start_date_, end_date_, kind_)
    channels_ = politician_channels.select('channel').unique().collect().to_series().to_list()
    final_list = []

    for c in channels_:
        single_channel = politician_channels.filter(pl.col('channel') == c)
        programs_channel = single_channel.select('program').unique().collect().to_series().to_list()
        temp = []
        for p in programs_channel:
            single_program = single_channel.filter(pl.col('program') == p)
            p1 = single_program.select('program').unique().collect().to_series().to_list()
            total = single_program.select('duration').sum().collect().to_series().to_list()
            temp.append({'program': p1[0], 'minutes': total[0]})
        final_list.append({'channel': single_channel.select('channel').unique().collect()
                            .to_series().to_list()[0], 'programs': temp})

    return { "politician": name, "channels": final_list }


@app.get("/v1/political-group-channels-programs/{name}")
async def get_political_group_channels_programs(
    name: str,
    start_date_: str = Query(default = start_date, description="Start date"),
    end_date_: str = Query(default = end_date, description="End date"),
    kind_: str = Query(default = "both" , description="Type of data", enum = kind),
    channel_: str = Query(default = "all", description="Channel"),
    program_: str = Query(default = "all", description="Program"),
    topic_: str = Query(default = "all", description="Topic")
):
    """
    Return every channel a political group talked in, specifying for each 
    channel all the programs he participated in and for how long (minutes)
    """

    filtered_data = political_groups

    if name not in political_groups_list:
        raise HTTPException(status_code=400, detail="Political Group not found")
    filtered_data = filtered_data.filter(pl.col('lastname') == name)

    if channel_ != "all":
        if channel_ not in channels:
            raise HTTPException(status_code=400, detail="Invalid channel")
        filtered_data = filtered_data.filter(pl.col('channel') == channel_)

    if program_ != "all":
        if program_ not in programs:
            raise HTTPException(status_code=400, detail="Invalid program")
        filtered_data = filtered_data.filter(pl.col('program') == program_)

    if topic_ != "all":
        if topic_ not in topics:
            raise HTTPException(status_code=400, detail="Invalid topic")
        filtered_data = filtered_data.filter(pl.col('topic') == topic_)

    polgroup_channels = filter_data(filtered_data, start_date_, end_date_, kind_)
    channels_ = polgroup_channels.select('channel').unique().collect().to_series().to_list()
    final_list = []

    for c in channels_:
        single_channel = polgroup_channels.filter(pl.col('channel') == c)
        programs_channel = single_channel.select('program').unique().collect().to_series().to_list()
        temp = []
        for p in programs_channel:
            single_program = single_channel.filter(pl.col('program') == p)
            p1 = single_program.select('program').unique().collect().to_series().to_list()
            total = single_program.select('duration').sum().collect().to_series().to_list()
            temp.append({'program': p1[0], 'minutes': total[0]})
        final_list.append({'channel': single_channel.select('channel').unique().collect()
                           .to_series().to_list()[0], 'programs': temp})

    return { "political group": name, "channels": final_list }

# -------------------------------------------------------

@app.get("/v1/channel-programs-politician/{name}/{channel}")
async def get_channel_programs_politician(
    name: str,
    channel: str,
    start_date_: str = Query(default = start_date, description="Start date"),
    end_date_: str = Query(default = end_date, description="End date"),
    kind_: str = Query(default = "both" , description="Type of data", enum = kind),
    affiliation_: str = Query(default = "all", description="Affiliation"),
    program_: str = Query(default = "all", description="Program"),
    topic_: str = Query(default = "all", description="Topic")
):
    """
    Return every program of a channel a politician talked in, 
    specifying for each program all the topics and for how long (minutes)
    """
    filtered_data = politicians

    if channel not in channels:
        raise HTTPException(status_code=400, detail="Channel not found")
    filtered_data = filtered_data.filter(pl.col('channel') == channel)

    if name not in politicians_list:
        raise HTTPException(status_code=400, detail="Politician not found")
    filtered_data = filtered_data.filter(pl.col('fullname') == name)

    if affiliation_ != "all":
        if affiliation_ not in affiliations:
            raise HTTPException(status_code=400, detail="Invalid affiliation")
        filtered_data = filtered_data.filter(pl.col('affiliation') == affiliation_)

    if program_ != "all":
        if program_ not in programs:
            raise HTTPException(status_code=400, detail="Invalid program")
        filtered_data = filtered_data.filter(pl.col('program') == program_)

    if topic_ != "all":
        if topic_ not in topics:
            raise HTTPException(status_code=400, detail="Invalid topic")
        filtered_data = filtered_data.filter(pl.col('topic') == topic_)

    politician_channels = filter_data(filtered_data, start_date_, end_date_, kind_)
    programs_ = politician_channels.select('program').unique().collect().to_series().to_list()
    final_list = []

    for p in programs_:
        single_program = politician_channels.filter(pl.col('program') == p)
        topics_programs = single_program.select('topic').unique().collect().to_series().to_list()
        temp = []
        for t in topics_programs:
            single_topic = single_program.filter(pl.col('topic') == t)
            t1 = single_topic.select('topic').unique().collect().to_series().to_list()
            total = single_topic.select('duration').sum().collect().to_series().to_list()
            temp.append({'topic': t1[0], 'minutes': total[0]})
        final_list.append({'program': single_program.select('program').unique().collect()
                           .to_series().to_list()[0], 'topics': temp})

    return { "politician": name, "channel": channel, "programs": final_list }


@app.get("/v1/channel-programs-political-group/{name}/{channel}")
async def get_channel_programs_political_group(
    name: str,
    channel: str,
    start_date_: str = Query(default = start_date, description="Start date"),
    end_date_: str = Query(default = end_date, description="End date"),
    kind_: str = Query(default = "both" , description="Type of data", enum = kind),
    program_: str = Query(default = "all", description="Program"),
    topic_: str = Query(default = "all", description="Topic")
):
    """
    Return every program of a channel a political group talked in, 
    specifying for each program all the topics and for how long (minutes)
    """

    filtered_data = political_groups

    if channel not in channels:
        raise HTTPException(status_code=400, detail="Channel not found")
    filtered_data = filtered_data.filter(pl.col('channel') == channel)

    if name not in political_groups_list:
        raise HTTPException(status_code=400, detail="Political Group not found")
    filtered_data = filtered_data.filter(pl.col('lastname') == name)

    if program_ != "all":
        if program_ not in programs:
            raise HTTPException(status_code=400, detail="Invalid program")
        filtered_data = filtered_data.filter(pl.col('program') == program_)

    if topic_ != "all":
        if topic_ not in topics:
            raise HTTPException(status_code=400, detail="Invalid topic")
        filtered_data = filtered_data.filter(pl.col('topic') == topic_)

    polgroup_channels = filter_data(filtered_data, start_date_, end_date_, kind_)
    programs_ = polgroup_channels.select('program').unique().collect().to_series().to_list()
    final_list = []

    for p in programs_:
        single_program = polgroup_channels.filter(pl.col('program') == p)
        topics_programs = single_program.select('topic').unique().collect().to_series().to_list()
        temp = []
        for t in topics_programs:
            single_topic = single_program.filter(pl.col('topic') == t)
            t1 = single_topic.select('topic').unique().collect().to_series().to_list()
            total = single_topic.select('duration').sum().collect().to_series().to_list()
            temp.append({'topic': t1[0], 'minutes': total[0]})
        final_list.append({'program': single_program.select('program').unique().collect()
                           .to_series().to_list()[0], 'topics': temp})

    return { "political group": name, "channel": channel, "programs": final_list }

# -------------------------------------------------------

@app.get("/v1/minutes-channel-per-politician/{channel}/{name}")
async def get_minutes_channel_per_politician(
    channel: str,
    name: str,
    start_date_: str = Query(default = start_date, description="Start date"),
    end_date_: str = Query(default = end_date, description="End date"),
    kind_: str = Query(default = "both" , description="Type of data", enum = kind),
    affiliation_: str = Query(default = "all", description="Affiliation"),
    program_: str = Query(default = "all", description="Program"),
    topic_: str = Query(default = "all", description="Topic")
):
    """
    Return all the programs in a channel, and how many minutes a politician has intervened
    """

    filtered_data = politicians

    if channel not in channels:
        raise HTTPException(status_code=400, detail="Channel not found")
    filtered_data = filtered_data.filter(pl.col('channel') == channel)

    if name not in politicians_list:
        raise HTTPException(status_code=400, detail="Politician not found")

    if affiliation_ != "all":
        if affiliation_ not in affiliations:
            raise HTTPException(status_code=400, detail="Invalid affiliation")
        filtered_data = filtered_data.filter(pl.col('affiliation') == affiliation_)

    if program_ != "all":
        if program_ not in programs:
            raise HTTPException(status_code=400, detail="Invalid program")
        filtered_data = filtered_data.filter(pl.col('program') == program_)

    if topic_ != "all":
        if topic_ not in topics:
            raise HTTPException(status_code=400, detail="Invalid topic")
        filtered_data = filtered_data.filter(pl.col('topic') == topic_)

    all_programs_channel = filter_data(filtered_data, start_date_, end_date_, kind_)
    programs_channel = all_programs_channel.select('program').unique().collect().to_series().to_list()
    programs_channel.sort()

    first_year = int(start_date_.split('/')[0])
    last_year = int(end_date_.split('/')[0])

    final_programs = []
    total = 0

    for prog in programs_channel:
        temp_prgrm = {}
        temp_prgrm["program"] = prog
        temp = all_programs_channel.filter(pl.col('program') == prog)
        temp = temp.filter(pl.col('fullname') == name)
        if topic_ != 'all':
            temp = temp.filter(pl.col('topic') == topic_)
        datas = {}
        m_y = first_year
        x_y = last_year
        while m_y != (x_y + 1):
            fy = datetime.strptime(str(m_y), '%Y')
            ly = datetime.strptime(str(m_y + 1), '%Y')
            a = temp.filter(pl.col('day') >= fy)
            a = a.filter(pl.col('day') <= ly)
            datas[m_y] = a.select('duration').sum().collect().to_series().to_list()[0]
            total += a.select('duration').sum().collect().to_series().to_list()[0]
            m_y += 1
        temp_prgrm["data"] = datas
        final_programs.append(temp_prgrm)

    return { "politician": name, "total": total, "programs": final_programs }


@app.get("/v1/minutes-channel-per-political-group/{channel}/{name}")
async def get_minutes_channel_per_political_group(
    channel: str,
    name: str,
    start_date_: str = Query(default = start_date, description="Start date"),
    end_date_: str = Query(default = end_date, description="End date"),
    kind_: str = Query(default = "both" , description="Type of data", enum = kind),
    program_: str = Query(default = "all", description="Program"),
    topic_: str = Query(default = "all", description="Topic")
):
    """
    Return all the programs in a channel, and how many minutes a political group has intervened
    """

    filtered_data = political_groups

    if channel not in channels:
        raise HTTPException(status_code=400, detail="Channel not found")
    filtered_data = filtered_data.filter(pl.col('channel') == channel)

    if name not in political_groups_list:
        raise HTTPException(status_code=400, detail="Political group not found")

    if program_ != "all":
        if program_ not in programs:
            raise HTTPException(status_code=400, detail="Invalid program")
        filtered_data = filtered_data.filter(pl.col('program') == program_)

    if topic_ != "all":
        if topic_ not in topics:
            raise HTTPException(status_code=400, detail="Invalid topic")
        filtered_data = filtered_data.filter(pl.col('topic') == topic_)

    all_programs_channel = filter_data(filtered_data, start_date_, end_date_, kind_)
    programs_channel = all_programs_channel.select('program').unique().collect().to_series().to_list()
    programs_channel.sort()

    first_year = int(start_date_.split('/')[0])
    last_year = int(end_date_.split('/')[0])

    final_programs = []
    total = 0

    for prog in programs_channel:
        temp_prgrm = {}
        temp_prgrm["program"] = prog
        temp = all_programs_channel.filter(pl.col('program') == prog)
        temp = temp.filter(pl.col('lastname') == name)
        if topic_ != 'all':
            temp = temp.filter(pl.col('topic') == topic_)
        datas = {}
        m_y = first_year
        x_y = last_year
        while m_y != (x_y + 1):
            fy = datetime.strptime(str(m_y), '%Y')
            ly = datetime.strptime(str(m_y + 1), '%Y')
            a = temp.filter(pl.col('day') >= fy)
            a = a.filter(pl.col('day') <= ly)
            datas[m_y] = a.select('duration').sum().collect().to_series().to_list()[0]
            total += a.select('duration').sum().collect().to_series().to_list()[0]
            m_y += 1
        temp_prgrm["data"] = datas
        final_programs.append(temp_prgrm)

    return { "political group": name, "total": total, "programs": final_programs }

# -------------------------------------------------------

@app.get("/v1/channels-programs-topics-politician/{name}")
async def get_channels_programs_topics_politician(
    name: str,
    start_date_: str = Query(default=start_date, description="Start date"),
    end_date_: str = Query(default=end_date, description="End date"),
    kind_: str = Query(default="both", description="Type of data", enum=kind),
    channel_: str = Query(default="all", description="Channel"),
    affiliation_: str = Query(default="all", description="Affiliation"),
    program_: str = Query(default="all", description="Program"),
    topic_: str = Query(default="all", description="Topic"),
    page: int = Query(default=1, description="Page number"),
    page_size: int = Query(default=10000, description="Page size"),
    program_page: int = Query(default=1, description="Program page number"),
    program_page_size: int = Query(default=10000, description="Program page size")
):
    """
    Return for a politician, all the channels he spoke to, in which programs, 
    what topic it was about, duration and date
    """

    if page < 1 or page_size < 1 or program_page < 1 or program_page_size < 1:
        raise HTTPException(status_code=400, detail="Page and page size must be positive integers.")

    filtered_data = data

    if name not in politicians_list:
        raise HTTPException(status_code=400, detail="Politician not found")
    filtered_data = filtered_data.filter(pl.col('fullname') == name)

    if program_ != "all":
        if program_ not in programs:
            raise HTTPException(status_code=400, detail="Invalid program")
        filtered_data = filtered_data.filter(pl.col('program') == program_)

    if channel_ != "all":
        if channel_ not in channels:
            raise HTTPException(status_code=400, detail="Invalid channel")
        filtered_data = filtered_data.filter(pl.col('channel') == channel_)

    if affiliation_ != "all":
        if affiliation_ not in affiliations:
            raise HTTPException(status_code=400, detail="Invalid affiliation")
        filtered_data = filtered_data.filter(pl.col('affiliation') == affiliation_)

    if topic_ != "all":
        if topic_ not in topics:
            raise HTTPException(status_code=400, detail="Invalid topic")
        filtered_data = filtered_data.filter(pl.col('topic') == topic_)

    all_channels = filter_data(filtered_data, start_date_, end_date_, kind_)
    channels_p = all_channels.select('channel').unique().collect().to_series().to_list()
    channels_p.sort()

    final_channels = []
    total_program_count = 0

    if len(channels_p) != 0:
        for channel in channels_p:
            single_channel = all_channels.filter(pl.col('channel') == channel)
            programs_in_channel = single_channel.select('program').unique().collect().to_series().to_list()
            programs_in_channel.sort()
            total_program_count += len(programs_in_channel)
            final_programs = []

            # Paginazione dei programmi
            start_program_index = (program_page - 1) * program_page_size
            end_program_index = start_program_index + program_page_size
            paginated_programs = programs_in_channel[start_program_index:end_program_index]

            for program in paginated_programs:
                single_program = single_channel.filter(pl.col('program') == program)
                topics_in_program = single_program.select('topic').unique().collect().to_series().to_list()
                topics_in_program.sort()
                final_topics = []
                for topic in topics_in_program:
                    single_topic = single_program.filter(pl.col('topic') == topic)
                    minutes = single_topic.select('duration').sum().collect().to_series().to_list()[0]
                    final_topics.append({"topic": topic, "minutes": minutes})
                final_programs.append({"program": program, "topics": final_topics})

            final_channels.append({"channel": channel, "programs": final_programs})

    # Paginazione dei canali
    start_index = (page - 1) * page_size
    end_index = start_index + page_size
    paginated_channels = final_channels[start_index:end_index]

    return {
        "politician": name,
        "channels": paginated_channels,
        "page": page,
        "page_size": page_size,
        "total_pages": (len(final_channels) + page_size - 1) // page_size,
        "program_page": program_page,
        "program_page_size": program_page_size,
        "total_program_pages": (total_program_count + program_page_size - 1) // program_page_size
    }


@app.get("/v1/channels-programs-topics-political-group/{name}")
async def get_channels_programs_topics_political_group(
    name: str,
    start_date_: str = Query(default=start_date, description="Start date"),
    end_date_: str = Query(default=end_date, description="End date"),
    kind_: str = Query(default="both", description="Type of data", enum=kind),
    channel_: str = Query(default="all", description="Channel"),
    program_: str = Query(default="all", description="Program"),
    topic_: str = Query(default="all", description="Topic"),
    page: int = Query(default=1, description="Page number"),
    page_size: int = Query(default=10000, description="Page size"),
    program_page: int = Query(default=1, description="Program page number"),
    program_page_size: int = Query(default=10000, description="Program page size")
):
    """
    Return for a political group, all the channels they spoke to, in which programs, 
    what topics were discussed, duration, and date.
    """

    if page < 1 or page_size < 1 or program_page < 1 or program_page_size < 1:
        raise HTTPException(status_code=400, detail="Page and page size must be positive integers.")

    filtered_data = data

    if name not in political_groups_list:
        raise HTTPException(status_code=400, detail="Political group not found")
    filtered_data = filtered_data.filter(pl.col('lastname') == name)

    if program_ != "all":
        if program_ not in programs:
            raise HTTPException(status_code=400, detail="Invalid program")
        filtered_data = filtered_data.filter(pl.col('program') == program_)

    if channel_ != "all":
        if channel_ not in channels:
            raise HTTPException(status_code=400, detail="Invalid channel")
        filtered_data = filtered_data.filter(pl.col('channel') == channel_)

    if topic_ != "all":
        if topic_ not in topics:
            raise HTTPException(status_code=400, detail="Invalid topic")
        filtered_data = filtered_data.filter(pl.col('topic') == topic_)

    all_channels = filter_data(filtered_data, start_date_, end_date_, kind_)
    channels_p = all_channels.select('channel').unique().collect().to_series().to_list()
    channels_p.sort()

    final_channels = []
    total_program_count = 0

    for channel in channels_p:
        single_channel = all_channels.filter(pl.col('channel') == channel)
        programs_in_channel = single_channel.select('program').unique().collect().to_series().to_list()
        programs_in_channel.sort()
        total_program_count += len(programs_in_channel)
        final_programs = []

        # Paginazione dei programmi
        start_program_index = (program_page - 1) * program_page_size
        end_program_index = start_program_index + program_page_size
        paginated_programs = programs_in_channel[start_program_index:end_program_index]

        for program in paginated_programs:
            single_program = single_channel.filter(pl.col('program') == program)
            topics_in_program = single_program.select('topic').unique().collect().to_series().to_list()
            topics_in_program.sort()
            final_topics = []
            for topic in topics_in_program:
                single_topic = single_program.filter(pl.col('topic') == topic)
                minutes = single_topic.select('duration').sum().collect().to_series().to_list()[0]
                final_topics.append({"topic": topic, "minutes": minutes})
            final_programs.append({"program": program, "topics": final_topics})

        final_channels.append({"channel": channel, "programs": final_programs})

    # Paginazione dei canali
    start_index = (page - 1) * page_size
    end_index = start_index + page_size
    paginated_channels = final_channels[start_index:end_index]

    return {
        "political_group": name,
        "channels": paginated_channels,
        "page": page,
        "page_size": page_size,
        "total_pages": (len(final_channels) + page_size - 1) // page_size,
        "program_page": program_page,
        "program_page_size": program_page_size,
        "total_program_pages": (total_program_count + program_page_size - 1) // program_page_size
    }


# -------------------------------------------------------

@app.get("/v1/channel-politicians/{channel}")
async def get_channel_politicians(
    channel: str,
    start_date_: str = Query(default = start_date, description="Start date"),
    end_date_: str = Query(default = end_date, description="End date"),
    kind_: str = Query(default = "both" , description="Type of data", enum = kind),
    name_: str = Query(default = "all", description="Politician"),
    affiliation_: str = Query(default = "all", description="Affiliation"),
    program_: str = Query(default = "all", description="Program"),
    topic_: str = Query(default = "all", description="Topic"),
    n_pol: int = Query(default = 10, description="number of politicians to analyze")
):
    """
    Return how much time a channel dedicated to politicians
    """
    filtered_data = politicians

    if channel not in channels:
        raise HTTPException(status_code=400, detail="Channel not found")
    filtered_data = filtered_data.filter(pl.col('channel') == channel)

    if name_ != "all":
        if name_ not in politicians_list:
            raise HTTPException(status_code=400, detail="Invalid politician")
        filtered_data = filtered_data.filter(pl.col('fullname') == name_)

    if affiliation_ != "all":
        if affiliation_ not in affiliations:
            raise HTTPException(status_code=400, detail="Invalid affiliation")
        filtered_data = filtered_data.filter(pl.col('affiliation') == affiliation_)

    if program_ != "all":
        if program_ not in programs:
            raise HTTPException(status_code=400, detail="Invalid program")
        filtered_data = filtered_data.filter(pl.col('program') == program_)

    if topic_ != "all":
        if topic_ not in topics:
            raise HTTPException(status_code=400, detail="Invalid topic")
        filtered_data = filtered_data.filter(pl.col('topic') == topic_)

    channel_politicians = filter_data(filtered_data, start_date_, end_date_, kind_)
    all_politicians = channel_politicians.select('fullname').unique().collect().to_series().to_list()
    final_list = []

    for p in all_politicians:
        temp = channel_politicians.filter(pl.col('fullname') == p)
        total = temp.select('duration').sum().collect().to_series().to_list()
        final_list.append({"name": p,
                           "minutes" : total[0]})

    sorted_list = sorted(final_list, key=lambda x: x['minutes'], reverse=True)

    return { "channel": channel, "pol": sorted_list[:n_pol] }


@app.get("/v1/channel-political-groups/{channel}")
async def get_channel_political_groups(
    channel: str,
    start_date_: str = Query(default = start_date, description="Start date"),
    end_date_: str = Query(default = end_date, description="End date"),
    kind_: str = Query(default = "both" , description="Type of data", enum = kind),
    name_: str = Query(default = "all", description="Political group"),
    program_: str = Query(default = "all", description="Program"),
    topic_: str = Query(default = "all", description="Topic"),
    n_pol: int = Query(default = 10, description="number of political groups to analyze")
):
    """
    Return how much time a channel dedicated to political groups
    """
    filtered_data = political_groups

    if channel not in channels:
        raise HTTPException(status_code=400, detail="Channel not found")
    filtered_data = filtered_data.filter(pl.col('channel') == channel)

    if name_ != "all":
        if name_ not in political_groups_list:
            raise HTTPException(status_code=400, detail="Invalid political group")
        filtered_data = filtered_data.filter(pl.col('lastname') == name_)

    if program_ != "all":
        if program_ not in programs:
            raise HTTPException(status_code=400, detail="Invalid program")
        filtered_data = filtered_data.filter(pl.col('program') == program_)

    if topic_ != "all":
        if topic_ not in topics:
            raise HTTPException(status_code=400, detail="Invalid topic")
        filtered_data = filtered_data.filter(pl.col('topic') == topic_)

    channel_polgroup = filter_data(filtered_data, start_date_, end_date_, kind_)
    all_polgroups = channel_polgroup.select('lastname').unique().collect().to_series().to_list()
    final_list = []

    for p in all_polgroups:
        temp = channel_polgroup.filter(pl.col('lastname') == p)
        total = temp.select('duration').sum().collect().to_series().to_list()
        final_list.append({"name": p,
                           "minutes" : total[0]})

    sorted_list = sorted(final_list, key=lambda x: x['minutes'], reverse=True)

    return { "channel": channel, "pol": sorted_list[:n_pol] }

# -------------------------------------------------------

@app.get("/v1/program-politicians/{program}")
async def get_program_politicians(
    program: str,
    start_date_: str = Query(default = start_date, description="Start date"),
    end_date_: str = Query(default = end_date, description="End date"),
    kind_: str = Query(default = "both" , description="Type of data", enum = kind),
    name_: str = Query(default = "all", description="Politician"),
    affiliation_: str = Query(default = "all", description="Affiliation"),
    channel_: str = Query(default = "all", description="Channel"),
    topic_: str = Query(default = "all", description="Topic"),
    n_pol: int = Query(default = 10, description="number of politicians to analyze")
):
    """
    Return how much time a program dedicated to politicians
    """
    filtered_data = politicians

    if program not in programs:
        raise HTTPException(status_code=400, detail="Program not found")
    filtered_data = filtered_data.filter(pl.col('program') == program)

    if name_ != "all":
        if name_ not in politicians_list:
            raise HTTPException(status_code=400, detail="Invalid politician")
        filtered_data = filtered_data.filter(pl.col('fullname') == name_)

    if affiliation_ != "all":
        if affiliation_ not in affiliations:
            raise HTTPException(status_code=400, detail="Invalid affiliation")
        filtered_data = filtered_data.filter(pl.col('affiliation') == affiliation_)

    if channel_ != "all":
        if channel_ not in channels:
            raise HTTPException(status_code=400, detail="Invalid channel")
        filtered_data = filtered_data.filter(pl.col('channel') == channel_)

    if topic_ != "all":
        if topic_ not in topics:
            raise HTTPException(status_code=400, detail="Invalid topic")
        filtered_data = filtered_data.filter(pl.col('topic') == topic_)

    program_politicians = filter_data(filtered_data, start_date_, end_date_, kind_)
    all_politicians = program_politicians.select('fullname').unique().collect().to_series().to_list()
    final_list = []

    for p in all_politicians:
        temp = program_politicians.filter(pl.col('fullname') == p)
        total = temp.select('duration').sum().collect().to_series().to_list()
        final_list.append({"name": p,
                           "minutes" : total[0]})

    sorted_list = sorted(final_list, key=lambda x: x['minutes'], reverse=True)

    return { "program": program, "pol": sorted_list[:n_pol] }


@app.get("/v1/program-political-groups/{program}")
async def get_program_political_groups(
    program: str,
    start_date_: str = Query(default = start_date, description="Start date"),
    end_date_: str = Query(default = end_date, description="End date"),
    kind_: str = Query(default = "both" , description="Type of data", enum = kind),
    name_: str = Query(default = "all", description="Political group"),
    channel_: str = Query(default = "all", description="Channel"),
    topic_: str = Query(default = "all", description="Topic"),
    n_pol: int = Query(default = 10, description="number of political groups to analyze")
):
    """
    Return how much time a program dedicated to political groups
    """
    filtered_data = political_groups

    if program not in programs:
        raise HTTPException(status_code=400, detail="Program not found")
    filtered_data = filtered_data.filter(pl.col('program') == program)

    if name_ != "all":
        if name_ not in political_groups_list:
            raise HTTPException(status_code=400, detail="Invalid political group")
        filtered_data = filtered_data.filter(pl.col('lastname') == name_)

    if channel_ != "all":
        if channel_ not in channels:
            raise HTTPException(status_code=400, detail="Invalid channel")
        filtered_data = filtered_data.filter(pl.col('channel') == channel_)

    if topic_ != "all":
        if topic_ not in topics:
            raise HTTPException(status_code=400, detail="Invalid topic")
        filtered_data = filtered_data.filter(pl.col('topic') == topic_)

    program_polgroup = filter_data(filtered_data, start_date_, end_date_, kind_)
    all_polgroups = program_polgroup.select('lastname').unique().collect().to_series().to_list()
    final_list = []

    for p in all_polgroups:
        temp = program_polgroup.filter(pl.col('lastname') == p)
        total = temp.select('duration').sum().collect().to_series().to_list()
        final_list.append({"name": p,
                           "minutes" : total[0]})

    sorted_list = sorted(final_list, key=lambda x: x['minutes'], reverse=True)

    return { "program": program, "pol": sorted_list[:n_pol] }
