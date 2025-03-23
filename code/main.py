"""
This module provides a series of RESTful APIs to provide data
gathered from the agcomdata.parquet file.

Author: Merak Winston Hall
Date: 2024-07-13
"""

import psycopg2
from fastapi import FastAPI, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse
from datetime import datetime
import warnings
from datetime import datetime
import datetime as dt

warnings.filterwarnings('ignore')

DB_HOST = "dpg-cva6ogbtq21c73bs2j8g-a.frankfurt-postgres.render.com"
DB_PORT = "5432"
DB_NAME = "agcom_dati_monitoraggio"
DB_USER = "agcom_dati_monitoraggio_user"
DB_PASSWORD = "o6uuicatOkvkAKZc41deozEBd56g8nrm"
TABLE_NAME = "records"

def query_postgresql(query, params=None):
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        with conn.cursor() as cur:
            cur.execute(query, params)
            data = cur.fetchall()
        conn.close()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading from PostgreSQL: {e}")

# -------------------------------------------------------

def get_min_max_dates():
    query = f"""SELECT MIN(day), MAX(day) FROM {TABLE_NAME};"""
    result = query_postgresql(query)
    return result[0][0].strftime('%Y/%m/%d'), result[0][1].strftime('%Y/%m/%d')

start_date, end_date = get_min_max_dates()

kind = ["speech", "news", "both"]

politicians_list = [k[0] for k in query_postgresql(f"""SELECT DISTINCT fullname FROM {TABLE_NAME} WHERE name != 'Soggetto Collettivo';""")]
political_groups_list  = [k[0] for k in query_postgresql(f"""SELECT DISTINCT lastname FROM {TABLE_NAME} WHERE name = 'Soggetto Collettivo';""")]
channels = [k[0] for k in query_postgresql(f"""SELECT DISTINCT channel FROM {TABLE_NAME};""")]
programs = [k[0] for k in query_postgresql(f"""SELECT DISTINCT program FROM {TABLE_NAME};""")]
affiliations = [k[0] for k in query_postgresql(f"""SELECT DISTINCT affiliation FROM {TABLE_NAME};""")]
topics = [k[0] for k in query_postgresql(f"""SELECT DISTINCT topic FROM {TABLE_NAME};""")]

def validate_date(date_str):
    try:
        return datetime.strptime(date_str, '%Y/%m/%d')
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY/MM/DD") from exc

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
    version="0.0.1",
)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index():
    return FileResponse('templates/home.html')

@app.get("/index")
async def read_charts():
    """
    Serve the index.html file.
    """
    return FileResponse('templates/index.html')

@app.get("/faq")
async def read_faq():
    """
    Serve the pages-faq.html file.
    """
    return FileResponse('templates/pages-faq.html')

@app.get("/contact")
async def contact():
    """
    Serve the pages-contact.html file.
    """
    return FileResponse('templates/pages-contact.html')

# -------------------------------------------------------

@app.get("/v1/politicians")
async def get_politicians(
    start_date_: str = Query(default=start_date),
    end_date_: str = Query(default=end_date),
    kind_: str = Query(default="both", enum=kind),
    page: int = Query(default=1),
    page_size: int = Query(default=5000)
):
    """
    Return all politicians with pagination
    """
    if page < 1 or page_size < 1:
        raise HTTPException(status_code=400, detail="Page and page size must be positive integers.")
    

    kind_filter = "" if kind_ == "both" else f"AND kind = '{kind_}'"

    query = f"""
        SELECT DISTINCT fullname
        FROM {TABLE_NAME}
        WHERE name != 'Soggetto Collettivo' AND day BETWEEN %s AND %s {kind_filter}
        GROUP BY fullname
        ORDER BY fullname
    """

    politicians_ = query_postgresql(query, (start_date_, end_date_))
    politicians_ = [p[0] for p in politicians_]

    start = (page - 1) * page_size
    end = start + page_size

    return {
        "total": len(politicians_),
        "politicians": politicians_[start:end],
        "page_size": page_size
    }


@app.get("/v1/political-groups")
async def get_political_groups(
    start_date_: str = Query(default=start_date, description="Start date"),
    end_date_: str = Query(default=end_date, description="End date"),
    kind_: str = Query(default="both", description="Type of data", enum=kind),
    page: int = Query(default=1, description="Page number"),
    page_size: int = Query(default=5000, description="Page size")
):
    """
    Return all political groups with pagination
    """
    if page < 1 or page_size < 1:
        raise HTTPException(status_code=400, detail="Page and page size must be positive integers.")

    kind_filter = "" if kind_ == "both" else f"AND kind = '{kind_}'"

    query = f"""
        SELECT DISTINCT lastname
        FROM {TABLE_NAME}
        WHERE name = 'Soggetto Collettivo' AND day BETWEEN %s AND %s {kind_filter}
        GROUP BY lastname
        ORDER BY lastname
    """

    political_groups_ = query_postgresql(query, (start_date_, end_date_))
    political_groups_ = [pg[0] for pg in political_groups_]

    start = (page - 1) * page_size
    end = start + page_size

    return {
        "total": len(political_groups_),
        "political_groups": political_groups_[start:end],
        "page_size": page_size
    }


@app.get("/v1/channels")
async def get_channels(
    page: int = Query(default=1, description="Page number"),
    page_size: int = Query(default=5000, description="Page size"),
    program_: str = Query(default = "all", description="Program")
):
    """
    Return all channels
    """
    if page < 1 or page_size < 1:
        raise HTTPException(status_code=400, detail="Page and page size must be positive integers.")
    
    filter = ""

    if program_ != "all":
        if program_ not in programs:
            raise HTTPException(status_code=400, detail="Invalid program")
        filter = f"""WHERE program = '{program_}'"""
        
    query = f"""
        SELECT DISTINCT channel
        FROM {TABLE_NAME}
        {filter}
        GROUP BY channel
        ORDER BY channel
    """

    channels_ = query_postgresql(query)
    channels_ = [k[0] for k in channels_]

    start = (page - 1) * page_size
    end = start + page_size

    return { "channels": channels_[start:end], "page_size": page_size }


@app.get("/v1/programs")
async def get_programs(
    page: int = Query(default=1, description="Page number"),
    page_size: int = Query(default=5000, description="Page size"),
    channel_: str = Query(default = "all", description="Channel")
):
    """
    Return all programs
    """
    if page < 1 or page_size < 1:
        raise HTTPException(status_code=400, detail="Page and page size must be positive integers.")
    
    filter = ""

    if channel_ != "all":
        if channel_ not in channels:
            raise HTTPException(status_code=400, detail="Invalid channel")
        filter = f"""WHERE channel = '{channel_}'"""

    query = f"""
        SELECT DISTINCT program
        FROM {TABLE_NAME}
        {filter}
        GROUP BY program
        ORDER BY program
    """

    programs_ = query_postgresql(query)
    programs_ = [k[0] for k in programs_]

    start = (page - 1) * page_size
    end = start + page_size

    return { "programs": programs_[start:end], "page_size": page_size }


@app.get("/v1/affiliations")
async def get_affiliations(
    page: int = Query(default=1, description="Page number"),
    page_size: int = Query(default=5000, description="Page size"),
    politician_: str = Query(default = "all", description="Politician")
):
    """
    Return all affiliations
    """
    if page < 1 or page_size < 1:
        raise HTTPException(status_code=400, detail="Page and page size must be positive integers.")
    
    filter = ""

    if politician_ != "all":
        if politician_ not in politicians_list:
            raise HTTPException(status_code=400, detail="Invalid politician")
        filter = f"""WHERE fullname = '{politician_}'"""

    query = f"""
        SELECT DISTINCT affiliation
        FROM {TABLE_NAME}
        {filter}
        GROUP BY affiliation
        ORDER BY affiliation
    """

    affiliations_ = query_postgresql(query)
    affiliations_ = [k[0] for k in affiliations_]

    start = (page - 1) * page_size
    end = start + page_size

    return { "affiliations": affiliations_[start:end], "page_size": page_size }


@app.get("/v1/topics")
async def get_topics(
    page: int = Query(default=1, description="Page number"),
    page_size: int = Query(default=5000, description="Page size")
):
    """
    Return all topics
    """
    if page < 1 or page_size < 1:
        raise HTTPException(status_code=400, detail="Page and page size must be positive integers.")

    query = f"""
        SELECT DISTINCT topic
        FROM {TABLE_NAME}
        GROUP BY topic
        ORDER BY topic
    """

    topics_ = query_postgresql(query)
    topics_ = [k[0] for k in topics_]

    start = (page - 1) * page_size
    end = start + page_size

    return { "topics": topics_[start:end], "page_size": page_size }

# -------------------------------------------------------

@app.get("/v1/politician-topics/{name}")
async def get_politician_topics(
    name: str,
    start_date_: str = Query(default=start_date),
    end_date_: str = Query(default=end_date),
    kind_: str = Query(default="both", enum=kind),
    channel_: str = Query(default="all"),
    affiliation_: str = Query(default="all"),
    program_: str = Query(default="all"),
    topic_: str = Query(default="all"),
    page: int = Query(default=1),
    page_size: int = Query(default=100)
):
    """
    Return how much a politician talked about all the possible topics
    """
    if page < 1 or page_size < 1:
        raise HTTPException(status_code=400, detail="Page and page size must be positive integers.")
    if name not in politicians_list:
        raise HTTPException(status_code=400, detail="Invalid name")

    conditions = ["name != 'Soggetto Collettivo'", "fullname = %s"]
    params = [name]

    if channel_ != "all":
        if channel_ not in channels:
            raise HTTPException(status_code=400, detail="Invalid channel")
        conditions.append("channel = %s")
        params.append(channel_)
    if affiliation_ != "all":
        if affiliation_ not in affiliations:
            raise HTTPException(status_code=400, detail="Invalid affiliation")
        conditions.append("affiliation = %s")
        params.append(affiliation_)
    if program_ != "all":
        if program_ not in programs:
            raise HTTPException(status_code=400, detail="Invalid program")
        conditions.append("program = %s")
        params.append(program_)
    if topic_ != "all":
        if topic_ not in topics:
            raise HTTPException(status_code=400, detail="Invalid topic")
        conditions.append("topic = %s")
        params.append(topic_)
    if kind_ != "both":
        conditions.append("kind = %s")
        params.append(kind_)

    condition_str = " AND ".join(conditions)

    query = f"""
        SELECT topic, SUM(duration), COUNT(*)
        FROM {TABLE_NAME}
        WHERE {condition_str} AND day BETWEEN %s AND %s
        GROUP BY topic
        ORDER BY topic
    """
    params.extend([start_date_, end_date_])

    data = query_postgresql(query, params)
    explicit_data = []
    for d in data:
        temp_topic = d[0]
        temp_duration = d[1]
        temp_interventions = d[2]
        explicit_data.append({"topic": temp_topic, "minutes": temp_duration, "interventions": temp_interventions})

    paginated_data = explicit_data[(page - 1) * page_size: page * page_size]

    return {"politician": name, "topics": paginated_data, "page_size": page_size}


@app.get("/v1/political-group-topics/{name}")
async def get_political_group_topics(
    name: str,
    start_date_: str = Query(default=start_date),
    end_date_: str = Query(default=end_date),
    kind_: str = Query(default="both", enum=kind),
    channel_: str = Query(default="all"),
    program_: str = Query(default="all"),
    topic_: str = Query(default="all"),
    page: int = Query(default=1),
    page_size: int = Query(default=100)
):
    """
    Return how much a political group talked about all the possible topics 
    """
    if page < 1 or page_size < 1:
        raise HTTPException(status_code=400, detail="Page and page size must be positive integers.")
    if name not in political_groups_list:
        raise HTTPException(status_code=400, detail="Invalid name")

    conditions = ["name = 'Soggetto Collettivo'", "lastname = %s"]
    params = [name]

    if channel_ != "all":
        if channel_ not in channels:
            raise HTTPException(status_code=400, detail="Invalid channel")
        conditions.append("channel = %s")
        params.append(channel_)
    if program_ != "all":
        if program_ not in programs:
            raise HTTPException(status_code=400, detail="Invalid program")
        conditions.append("program = %s")
        params.append(program_)
    if topic_ != "all":
        if topic_ not in topics:
            raise HTTPException(status_code=400, detail="Invalid topic")
        conditions.append("topic = %s")
        params.append(topic_)
    if kind_ != "both":
        conditions.append("kind = %s")
        params.append(kind_)

    condition_str = " AND ".join(conditions)

    query = f"""
        SELECT topic, SUM(duration), COUNT(*)
        FROM {TABLE_NAME}
        WHERE {condition_str} AND day BETWEEN %s AND %s
        GROUP BY topic
        ORDER BY topic
    """
    params.extend([start_date_, end_date_])

    data = query_postgresql(query, params)
    explicit_data = []
    for d in data:
        temp_topic = d[0]
        temp_duration = d[1]
        temp_interventions = d[2]
        explicit_data.append({"topic": temp_topic, "minutes": temp_duration, "interventions": temp_interventions})

    paginated_data = explicit_data[(page - 1) * page_size: page * page_size]

    return {"political group": name, "topics": paginated_data, "page_size": page_size}

# -------------------------------------------------------

@app.get("/v1/politician-channels/{name}")
async def get_politician_channels(
    name: str,
    start_date_: str = Query(default=start_date, description="Start date"),
    end_date_: str = Query(default=end_date, description="End date"),
    kind_: str = Query(default="both", description="Type of data", enum=kind),
    channel_: str = Query(default="all", description="Channel"),
    affiliation_: str = Query(default="all", description="Affiliation"),
    program_: str = Query(default="all", description="Program"),
    topic_: str = Query(default="all", description="Topic"),
    page: int = Query(default=1, description="Page number"),
    page_size: int = Query(default=100, description="Page size")
):
    """
    Return how much a politician talked in a specific channel
    """
    if page < 1 or page_size < 1:
        raise HTTPException(status_code=400, detail="Page and page size must be positive integers.")
    if name not in politicians_list:
        raise HTTPException(status_code=400, detail="Invalid name")

    conditions = ["name != 'Soggetto Collettivo'", "fullname = %s"]
    params = [name]

    if channel_ != "all":
        if channel_ not in channels:
            raise HTTPException(status_code=400, detail="Invalid channel")
        conditions.append("channel = %s")
        params.append(channel_)
    if affiliation_ != "all":
        if affiliation_ not in affiliations:
            raise HTTPException(status_code=400, detail="Invalid affiliation")
        conditions.append("affiliation = %s")
        params.append(affiliation_)
    if program_ != "all":
        if program_ not in programs:
            raise HTTPException(status_code=400, detail="Invalid program")
        conditions.append("program = %s")
        params.append(program_)
    if topic_ != "all":
        if topic_ not in topics:
            raise HTTPException(status_code=400, detail="Invalid topic")
        conditions.append("topic = %s")
        params.append(topic_)
    if kind_ != "both":
        conditions.append("kind = %s")
        params.append(kind_)

    condition_str = " AND ".join(conditions)

    query = f"""
        SELECT channel, SUM(duration), COUNT(*)
        FROM {TABLE_NAME}
        WHERE {condition_str} AND day BETWEEN %s AND %s
        GROUP BY channel
        ORDER BY channel ASC
    """
    params.extend([start_date_, end_date_])

    data = query_postgresql(query, params)

    explicit_data = []
    for d in data:
        temp_channel = d[0]
        temp_duration = d[1]
        temp_interventions = d[2]
        explicit_data.append({"channel": temp_channel, "minutes": temp_duration, "interventions": temp_interventions})

    paginated_data = explicit_data[(page - 1) * page_size: page * page_size]

    return { "politician": name, "channels": paginated_data, "page_size": page_size }


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
    if page < 1 or page_size < 1:
        raise HTTPException(status_code=400, detail="Page and page size must be positive integers.")
    if name not in political_groups_list:
        raise HTTPException(status_code=400, detail="Invalid name")

    conditions = ["name = 'Soggetto Collettivo'", "lastname = %s"]
    params = [name]

    if channel_ != "all":
        if channel_ not in channels:
            raise HTTPException(status_code=400, detail="Invalid channel")
        conditions.append("channel = %s")
        params.append(channel_)
    if program_ != "all":
        if program_ not in programs:
            raise HTTPException(status_code=400, detail="Invalid program")
        conditions.append("program = %s")
        params.append(program_)
    if topic_ != "all":
        if topic_ not in topics:
            raise HTTPException(status_code=400, detail="Invalid topic")
        conditions.append("topic = %s")
        params.append(topic_)
    if kind_ != "both":
        conditions.append("kind = %s")
        params.append(kind_)

    condition_str = " AND ".join(conditions)

    query = f"""
        SELECT channel, SUM(duration), COUNT(*)
        FROM {TABLE_NAME}
        WHERE {condition_str} AND day BETWEEN %s AND %s
        GROUP BY channel
        ORDER BY channel ASC
    """
    params.extend([start_date_, end_date_])

    data = query_postgresql(query, params)

    explicit_data = []
    for d in data:
        temp_channel = d[0]
        temp_duration = d[1]
        temp_interventions = d[2]
        explicit_data.append({"channel": temp_channel, "minutes": temp_duration, "interventions": temp_interventions})

    paginated_data = explicit_data[(page - 1) * page_size: page * page_size]

    return { "political group": name, "channels": paginated_data, "page_size": page_size }

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

    query = f"""
        SELECT DISTINCT fullname
        FROM {TABLE_NAME}
        WHERE affiliation = %s AND fullname != affiliation
    """

    data = query_postgresql(query, [name])
    final_list = [item[0] for item in data]

    return {"affiliation": name, "politicians": final_list}


@app.get("/v1/affiliations-politician/{name}")
async def get_affiliations_politician(
    name: str,
):
    """
    Return how many affiliations a politician has participated in
    """
    if name not in politicians_list:
        raise HTTPException(status_code=400, detail="Invalid politician")

    query = f"""
        SELECT DISTINCT affiliation
        FROM {TABLE_NAME}
        WHERE fullname = %s
    """

    data = query_postgresql(query, [name])
    final_list = [item[0] for item in data]

    return {"politician": name, "affiliations": final_list}

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
    if name not in affiliations:
        raise HTTPException(status_code=400, detail="Invalid name")

    conditions = ["affiliation = %s"]
    params = [name]

    if channel_ != "all":
        if channel_ not in channels:
            raise HTTPException(status_code=400, detail="Invalid channel")
        conditions.append("channel = %s")
        params.append(channel_)
    if program_ != "all":
        if program_ not in programs:
            raise HTTPException(status_code=400, detail="Invalid program")
        conditions.append("program = %s")
        params.append(program_)
    if topic_ != "all":
        if topic_ not in topics:
            raise HTTPException(status_code=400, detail="Invalid topic")
        conditions.append("topic = %s")
        params.append(topic_)
    if kind_ != "both":
        conditions.append("kind = %s")
        params.append(kind_)

    condition_str = " AND ".join(conditions)

    query = f"""
        SELECT COUNT(*) AS interventions, SUM(duration) AS total_minutes
        FROM {TABLE_NAME}
        WHERE {condition_str} AND day BETWEEN %s AND %s
    """
    params.extend([start_date_, end_date_])

    data = query_postgresql(query, params)

    return { "political group": name, "interventions": data[0][0], "minutes": data[0][1] }

# -------------------------------------------------------

@app.get("/v1/dates")
async def get_dates():
    """
    Return the first and last date of the dataset
    """
    query = f"""
        SELECT MIN(day), MAX(day)
        FROM {TABLE_NAME}
    """

    data = query_postgresql(query)

    start_date_ = data[0][0].strftime('%Y-%m-%d')
    end_date_ = data[0][1].strftime('%Y-%m-%d')

    return {"first_date": start_date_, "end_date": end_date_}

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
    if name not in politicians_list:
        raise HTTPException(status_code=400, detail="Invalid name")

    conditions = ["name != 'Soggetto Collettivo'", "fullname = %s"]
    params = [name]

    if channel_ != "all":
        if channel_ not in channels:
            raise HTTPException(status_code=400, detail="Invalid channel")
        conditions.append("channel = %s")
        params.append(channel_)
    if affiliation_ != "all":
        if affiliation_ not in affiliations:
            raise HTTPException(status_code=400, detail="Invalid affiliation")
        conditions.append("affiliation = %s")
        params.append(affiliation_)
    if program_ != "all":
        if program_ not in programs:
            raise HTTPException(status_code=400, detail="Invalid program")
        conditions.append("program = %s")
        params.append(program_)
    if topic_ != "all":
        if topic_ not in topics:
            raise HTTPException(status_code=400, detail="Invalid topic")
        conditions.append("topic = %s")
        params.append(topic_)
    if kind_ != "both":
        conditions.append("kind = %s")
        params.append(kind_)

    condition_str = " AND ".join(conditions)

    query = f"""
        SELECT EXTRACT(YEAR FROM day) AS year, COUNT(*) AS interventions, SUM(duration) AS total_minutes
        FROM {TABLE_NAME}
        WHERE {condition_str} AND day BETWEEN %s AND %s
        GROUP BY year
        ORDER BY year
    """

    params.extend([start_date_, end_date_])

    data = query_postgresql(query, params)

    temp_years = [int(row[0]) for row in data]
    temp_interventions = [row[1] for row in data]
    temp_minutes = [row[2] for row in data]
    total_minutes = sum(temp_minutes)

    years = []
    interventions = []
    minutes = []

    first_year = int(start_date_.split('/')[0])
    last_year = int(end_date_.split('/')[0])

    while first_year != (last_year + 1):
        if first_year in temp_years:
            years.append(str(temp_years.pop(0)))
            interventions.append(temp_interventions.pop(0))
            minutes.append(temp_minutes.pop(0))
        else:
            years.append(str(first_year))
            interventions.append(0)
            minutes.append(0)
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
    if name not in political_groups_list:
        raise HTTPException(status_code=400, detail="Invalid name")

    conditions = ["name = 'Soggetto Collettivo'", "lastname = %s"]
    params = [name]

    if channel_ != "all":
        if channel_ not in channels:
            raise HTTPException(status_code=400, detail="Invalid channel")
        conditions.append("channel = %s")
        params.append(channel_)
    if program_ != "all":
        if program_ not in programs:
            raise HTTPException(status_code=400, detail="Invalid program")
        conditions.append("program = %s")
        params.append(program_)
    if topic_ != "all":
        if topic_ not in topics:
            raise HTTPException(status_code=400, detail="Invalid topic")
        conditions.append("topic = %s")
        params.append(topic_)
    if kind_ != "both":
        conditions.append("kind = %s")
        params.append(kind_)

    condition_str = " AND ".join(conditions)

    query = f"""
        SELECT EXTRACT(YEAR FROM day) AS year, COUNT(*) AS interventions, SUM(duration) AS total_minutes
        FROM {TABLE_NAME}
        WHERE {condition_str} AND day BETWEEN %s AND %s
        GROUP BY year
        ORDER BY year
    """

    params.extend([start_date_, end_date_])

    data = query_postgresql(query, params)

    temp_years = [int(row[0]) for row in data]
    temp_interventions = [row[1] for row in data]
    temp_minutes = [row[2] for row in data]
    total_minutes = sum(temp_minutes)

    years = []
    interventions = []
    minutes = []

    first_year = int(start_date_.split('/')[0])
    last_year = int(end_date_.split('/')[0])

    while first_year != (last_year + 1):
        if first_year in temp_years:
            years.append(str(temp_years.pop(0)))
            interventions.append(temp_interventions.pop(0))
            minutes.append(temp_minutes.pop(0))
        else:
            years.append(str(first_year))
            interventions.append(0)
            minutes.append(0)
        first_year += 1

    return { "political group": name, "years": years,
            "interventions": interventions, "minutes": minutes, "total": total_minutes }

# -------------------------------------------------------

@app.get("/v1/interventions-politician-per-day/{name}")
async def get_interventions_politician_per_day(
    name: str,
    year: str = Query(description="choose year"),
    kind_: str = Query(default = "both" , description="Type of data", enum = kind),
    channel_: str = Query(default = "all", description="Channel"),
    affiliation_: str = Query(default = "all", description="Affiliation"),
    program_: str = Query(default = "all", description="Program"),
    topic_: str = Query(default = "all", description="Topic"),
    page: int = Query(default=1, description="Page number"),
    page_size: int = Query(default=366, description="Page size")
):
    """
    Return how much a politician has intervened in tv per day for a specific year
    """
    if page < 1 or page_size < 1:
        raise HTTPException(status_code=400, detail="Page and page size must be positive integers.")
    if name not in politicians_list:
        raise HTTPException(status_code=400, detail="Invalid name")

    conditions = ["name != 'Soggetto Collettivo'", "fullname = %s"]
    params = [name]

    if channel_ != "all":
        if channel_ not in channels:
            raise HTTPException(status_code=400, detail="Invalid channel")
        conditions.append("channel = %s")
        params.append(channel_)
    if affiliation_ != "all":
        if affiliation_ not in affiliations:
            raise HTTPException(status_code=400, detail="Invalid affiliation")
        conditions.append("affiliation = %s")
        params.append(affiliation_)
    if program_ != "all":
        if program_ not in programs:
            raise HTTPException(status_code=400, detail="Invalid program")
        conditions.append("program = %s")
        params.append(program_)
    if topic_ != "all":
        if topic_ not in topics:
            raise HTTPException(status_code=400, detail="Invalid topic")
        conditions.append("topic = %s")
        params.append(topic_)
    if kind_ != "both":
        conditions.append("kind = %s")
        params.append(kind_)

    condition_str = " AND ".join(conditions)

    query = f"""
        SELECT day, COUNT(*) AS interventions, COALESCE(SUM(duration), 0) AS total_minutes
        FROM {TABLE_NAME}
        WHERE {condition_str} AND day BETWEEN %s AND %s
        GROUP BY day 
        ORDER BY day
    """
    start_date_ = str(year) + "/01/01"
    end_date_ = str(year) + "/12/31"

    params.extend([start_date_, end_date_])

    data = query_postgresql(query, params)

    begin_date = dt.date(int(start_date_.split('/')[0]),
                         int(start_date_.split('/')[1]),
                         int(start_date_.split('/')[2]))
    final_date = dt.date(int(end_date_.split('/')[0]),
                         int(end_date_.split('/')[1]),
                         int(end_date_.split('/')[2]))

    results = {}
    current_date = begin_date

    while current_date <= final_date:
        results[str(current_date)] = {"interventions": 0, "minutes": 0}
        current_date += dt.timedelta(days=1)

    for day, interventions, minutes in data:
        results[str(day)] = {"interventions": interventions, "minutes": minutes}

    paginated_list = list(results.items())[(page - 1) * page_size : page * page_size]

    return {"politician": name, "interventions": paginated_list, 
            "max_value": max(paginated_list, key=lambda x: x[1]["interventions"])[1]["interventions"]}


@app.get("/v1/interventions-political-group-per-day/{name}")
async def get_interventions_political_group_per_day(
    name: str,
    year: str = Query(description="choose year"),
    kind_: str = Query(default = "both" , description="Type of data", enum = kind),
    channel_: str = Query(default = "all", description="Channel"),
    program_: str = Query(default = "all", description="Program"),
    topic_: str = Query(default = "all", description="Topic"),
    page: int = Query(default=1, description="Page number"),
    page_size: int = Query(default=366, description="Page size")
):
    """
    Return how much a political group has intervened in tv per day for a specific year
    """
    if page < 1 or page_size < 1:
        raise HTTPException(status_code=400, detail="Page and page size must be positive integers.")
    if name not in political_groups_list:
        raise HTTPException(status_code=400, detail="Invalid name")

    conditions = ["name = 'Soggetto Collettivo'", "lastname = %s"]
    params = [name]

    if channel_ != "all":
        if channel_ not in channels:
            raise HTTPException(status_code=400, detail="Invalid channel")
        conditions.append("channel = %s")
        params.append(channel_)
    if program_ != "all":
        if program_ not in programs:
            raise HTTPException(status_code=400, detail="Invalid program")
        conditions.append("program = %s")
        params.append(program_)
    if topic_ != "all":
        if topic_ not in topics:
            raise HTTPException(status_code=400, detail="Invalid topic")
        conditions.append("topic = %s")
        params.append(topic_)
    if kind_ != "both":
        conditions.append("kind = %s")
        params.append(kind_)

    condition_str = " AND ".join(conditions)

    query = f"""
        SELECT day, COUNT(*) AS interventions, COALESCE(SUM(duration), 0) AS total_minutes
        FROM {TABLE_NAME}
        WHERE {condition_str} AND day BETWEEN %s AND %s
        GROUP BY day 
        ORDER BY day
    """
    start_date_ = str(year) + "/01/01"
    end_date_ = str(year) + "/12/31"

    params.extend([start_date_, end_date_])

    data = query_postgresql(query, params)

    begin_date = dt.date(int(start_date_.split('/')[0]),
                         int(start_date_.split('/')[1]),
                         int(start_date_.split('/')[2]))
    final_date = dt.date(int(end_date_.split('/')[0]),
                         int(end_date_.split('/')[1]),
                         int(end_date_.split('/')[2]))

    results = {}
    current_date = begin_date

    while current_date <= final_date:
        results[str(current_date)] = {"interventions": 0, "minutes": 0}
        current_date += dt.timedelta(days=1)

    for day, interventions, minutes in data:
        results[str(day)] = {"interventions": interventions, "minutes": minutes}

    paginated_list = list(results.items())[(page - 1) * page_size : page * page_size]

    return { "political group": name, "interventions": paginated_list,
             "max_value": max(paginated_list, key=lambda x: x[1]["interventions"])[1]["interventions"]}

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
    if name not in politicians_list:
        raise HTTPException(status_code=400, detail="Invalid name")

    conditions = ["name != 'Soggetto Collettivo'", "fullname = %s"]
    params = [name]

    if channel_ != "all":
        if channel_ not in channels:
            raise HTTPException(status_code=400, detail="Invalid channel")
        conditions.append("channel = %s")
        params.append(channel_)
    if affiliation_ != "all":
        if affiliation_ not in affiliations:
            raise HTTPException(status_code=400, detail="Invalid affiliation")
        conditions.append("affiliation = %s")
        params.append(affiliation_)
    if program_ != "all":
        if program_ not in programs:
            raise HTTPException(status_code=400, detail="Invalid program")
        conditions.append("program = %s")
        params.append(program_)
    if topic_ != "all":
        if topic_ not in topics:
            raise HTTPException(status_code=400, detail="Invalid topic")
        conditions.append("topic = %s")
        params.append(topic_)
    if kind_ != "both":
        conditions.append("kind = %s")
        params.append(kind_)

    condition_str = " AND ".join(conditions)

    query = f"""
        SELECT channel, program, COUNT(*) AS interventions, SUM(duration) AS total_minutes
        FROM {TABLE_NAME}
        WHERE {condition_str} AND day BETWEEN %s AND %s
        GROUP BY channel, program
        ORDER BY channel, total_minutes DESC;
    """
    params.extend([start_date_, end_date_])

    data = query_postgresql(query, params)

    final_channels = []
    while len(data) != 0:
        temp_programs = []
        temp_data = data.pop(0)
        temp_channel = temp_data[0]
        temp_programs.append({"program": temp_data[1], "interventions": temp_data[2], "minutes": temp_data[3]})

        
        while len(data) != 0 and data[0][0] == temp_channel:
            temp_data = data.pop(0)
            temp_programs.append({"program": temp_data[1], "interventions": temp_data[2], "minutes": temp_data[3]})
            
        final_channels.append({"channel": temp_channel, "programs": temp_programs})

    return { "politician": name, "channels": final_channels }


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
    if name not in political_groups_list:
        raise HTTPException(status_code=400, detail="Invalid name")

    conditions = ["name = 'Soggetto Collettivo'", "lastname = %s"]
    params = [name]

    if channel_ != "all":
        if channel_ not in channels:
            raise HTTPException(status_code=400, detail="Invalid channel")
        conditions.append("channel = %s")
        params.append(channel_)
    if program_ != "all":
        if program_ not in programs:
            raise HTTPException(status_code=400, detail="Invalid program")
        conditions.append("program = %s")
        params.append(program_)
    if topic_ != "all":
        if topic_ not in topics:
            raise HTTPException(status_code=400, detail="Invalid topic")
        conditions.append("topic = %s")
        params.append(topic_)
    if kind_ != "both":
        conditions.append("kind = %s")
        params.append(kind_)

    condition_str = " AND ".join(conditions)

    query = f"""
        SELECT channel, program, COUNT(*) AS interventions, SUM(duration) AS total_minutes
        FROM {TABLE_NAME}
        WHERE {condition_str} AND day BETWEEN %s AND %s
        GROUP BY channel, program
        ORDER BY channel, total_minutes DESC;
    """
    params.extend([start_date_, end_date_])

    data = query_postgresql(query, params)

    final_channels = []
    while len(data) != 0:
        temp_programs = []
        temp_data = data.pop(0)
        temp_channel = temp_data[0]
        temp_programs.append({"program": temp_data[1], "interventions": temp_data[2], "minutes": temp_data[3]})
        
        while len(data) != 0 and data[0][0] == temp_channel:
            temp_data = data.pop(0)
            temp_programs.append({"program": temp_data[1], "interventions": temp_data[2], "minutes": temp_data[3]})
            
        final_channels.append({"channel": temp_channel, "programs": temp_programs})

    return { "political group": name, "channels": final_channels }

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
    if name not in politicians_list:
        raise HTTPException(status_code=400, detail="Invalid name")
    if channel not in channels:
        raise HTTPException(status_code=400, detail="Invalid channel")

    conditions = ["name != 'Soggetto Collettivo'", "fullname = %s", "channel = %s"]
    params = [name, channel]

    if affiliation_ != "all":
        if affiliation_ not in affiliations:
            raise HTTPException(status_code=400, detail="Invalid affiliation")
        conditions.append("affiliation = %s")
        params.append(affiliation_)
    if program_ != "all":
        if program_ not in programs:
            raise HTTPException(status_code=400, detail="Invalid program")
        conditions.append("program = %s")
        params.append(program_)
    if topic_ != "all":
        if topic_ not in topics:
            raise HTTPException(status_code=400, detail="Invalid topic")
        conditions.append("topic = %s")
        params.append(topic_)
    if kind_ != "both":
        conditions.append("kind = %s")
        params.append(kind_)

    condition_str = " AND ".join(conditions)

    query = f"""
        SELECT program, topic, COUNT(*) AS interventions, SUM(duration) AS total_minutes
        FROM {TABLE_NAME}
        WHERE {condition_str} AND day BETWEEN %s AND %s
        GROUP BY program, topic
        ORDER BY program, total_minutes DESC;
    """
    params.extend([start_date_, end_date_])

    data = query_postgresql(query, params)

    final_programs = []
    while len(data) != 0:
        temp_topics = []
        temp_data = data.pop(0)
        temp_program = temp_data[0]
        temp_topics.append({"topic": temp_data[1], "interventions": temp_data[2], "minutes": temp_data[3]})

        while len(data) != 0 and data[0][0] == temp_program:
            temp_data = data.pop(0)
            temp_topics.append({"topic": temp_data[1], "interventions": temp_data[2], "minutes": temp_data[3]})

        final_programs.append({"program": temp_program, "topics": temp_topics})


    return { "politician": name, "channel": channel, "programs": final_programs }


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
    if name not in political_groups_list:
        raise HTTPException(status_code=400, detail="Invalid name")
    if channel not in channels:
        raise HTTPException(status_code=400, detail="Invalid channel")

    conditions = ["name = 'Soggetto Collettivo'", "lastname = %s", "channel = %s"]
    params = [name, channel]

    if program_ != "all":
        if program_ not in programs:
            raise HTTPException(status_code=400, detail="Invalid program")
        conditions.append("program = %s")
        params.append(program_)
    if topic_ != "all":
        if topic_ not in topics:
            raise HTTPException(status_code=400, detail="Invalid topic")
        conditions.append("topic = %s")
        params.append(topic_)
    if kind_ != "both":
        conditions.append("kind = %s")
        params.append(kind_)

    condition_str = " AND ".join(conditions)

    query = f"""
        SELECT program, topic, COUNT(*) AS interventions, SUM(duration) AS total_minutes
        FROM {TABLE_NAME}
        WHERE {condition_str} AND day BETWEEN %s AND %s
        GROUP BY program, topic
        ORDER BY program, total_minutes DESC;
    """
    params.extend([start_date_, end_date_])

    data = query_postgresql(query, params)

    final_programs = []
    while len(data) != 0:
        temp_topics = []
        temp_data = data.pop(0)
        temp_program = temp_data[0]
        temp_topics.append({"topic": temp_data[1], "interventions": temp_data[2], "minutes": temp_data[3]})

        while len(data) != 0 and data[0][0] == temp_program:
            temp_data = data.pop(0)
            temp_topics.append({"topic": temp_data[1], "interventions": temp_data[2], "minutes": temp_data[3]})

        final_programs.append({"program": temp_program, "topics": temp_topics})

    return { "political group": name, "channel": channel, "programs": final_programs }

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
    if name not in politicians_list:
        raise HTTPException(status_code=400, detail="Invalid name")
    if channel not in channels:
        raise HTTPException(status_code=400, detail="Invalid channel")
    
    query = f"""
        SELECT DISTINCT program
        FROM {TABLE_NAME}
        WHERE channel = '{channel}'
    """

    programs_in_channel = query_postgresql(query)

    conditions = ["name != 'Soggetto Collettivo'", "fullname = %s", "channel = %s"]
    params = [name, channel]

    if affiliation_ != "all":
        if affiliation_ not in affiliations:
            raise HTTPException(status_code=400, detail="Invalid affiliation")
        conditions.append("affiliation = %s")
        params.append(affiliation_)
    if program_ != "all":
        if program_ not in programs:
            raise HTTPException(status_code=400, detail="Invalid program")
        conditions.append("program = %s")
        params.append(program_)
    if topic_ != "all":
        if topic_ not in topics:
            raise HTTPException(status_code=400, detail="Invalid topic")
        conditions.append("topic = %s")
        params.append(topic_)
    if kind_ != "both":
        conditions.append("kind = %s")
        params.append(kind_)

    condition_str = " AND ".join(conditions)

    query = f"""
        SELECT program, day, SUM(duration) AS total_minutes
        FROM {TABLE_NAME}
        WHERE {condition_str} AND day BETWEEN %s AND %s
        GROUP BY program, day
        ORDER BY program, total_minutes DESC;
    """
    params.extend([start_date_, end_date_])

    data = query_postgresql(query, params)

    last_year = int(end_date_.split('/')[0])

    total = 0

    final_programs = []
    while len(data) != 0:
        first_year = int(start_date_.split('/')[0])
        years = {}
        while first_year != (last_year + 1):
            years[str(first_year)] = 0
            first_year += 1
        temp_data = data.pop(0)
        temp_program = temp_data[0]
        years[temp_data[1].strftime('%Y')] += temp_data[2]
        total += temp_data[2]

        while len(data) != 0 and data[0][0] == temp_program:
            temp_data = data.pop(0)
            years[temp_data[1].strftime('%Y')] += temp_data[2]
            total += temp_data[2]
        
        final_programs.append({"program": temp_program, "data": years})
    
    first_year = int(start_date_.split('/')[0])
    years = {}
    while first_year != (last_year + 1):
        years[str(first_year)] = 0
        first_year += 1

    for p in programs_in_channel:
        check = False
        for item in final_programs:
            if p[0] == item["program"]:
                check = True
                continue
        if not check:
            final_programs.append({"program": p[0], "data": years})

    sorted_programs = sorted(final_programs, key=lambda x: x["program"])

    return { "politician": name, "total": total, "programs": sorted_programs }


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
    if name not in political_groups_list:
        raise HTTPException(status_code=400, detail="Invalid name")
    if channel not in channels:
        raise HTTPException(status_code=400, detail="Invalid channel")
    
    query = f"""
        SELECT DISTINCT program
        FROM {TABLE_NAME}
        WHERE channel = '{channel}'
    """

    programs_in_channel = query_postgresql(query)

    conditions = ["name = 'Soggetto Collettivo'", "lastname = %s", "channel = %s"]
    params = [name, channel]

    if program_ != "all":
        if program_ not in programs:
            raise HTTPException(status_code=400, detail="Invalid program")
        conditions.append("program = %s")
        params.append(program_)
    if topic_ != "all":
        if topic_ not in topics:
            raise HTTPException(status_code=400, detail="Invalid topic")
        conditions.append("topic = %s")
        params.append(topic_)
    if kind_ != "both":
        conditions.append("kind = %s")
        params.append(kind_)

    condition_str = " AND ".join(conditions)

    query = f"""
        SELECT program, day, SUM(duration) AS total_minutes
        FROM {TABLE_NAME}
        WHERE {condition_str} AND day BETWEEN %s AND %s
        GROUP BY program, day
        ORDER BY program, total_minutes DESC;
    """
    params.extend([start_date_, end_date_])

    data = query_postgresql(query, params)

    last_year = int(end_date_.split('/')[0])

    total = 0

    final_programs = []
    while len(data) != 0:
        first_year = int(start_date_.split('/')[0])
        years = {}
        while first_year != (last_year + 1):
            years[str(first_year)] = 0
            first_year += 1
        temp_data = data.pop(0)
        temp_program = temp_data[0]
        years[temp_data[1].strftime('%Y')] += temp_data[2]
        total += temp_data[2]

        while len(data) != 0 and data[0][0] == temp_program:
            temp_data = data.pop(0)
            years[temp_data[1].strftime('%Y')] += temp_data[2]
            total += temp_data[2]
        
        final_programs.append({"program": temp_program, "data": years})
    
    first_year = int(start_date_.split('/')[0])
    years = {}
    while first_year != (last_year + 1):
        years[str(first_year)] = 0
        first_year += 1

    for p in programs_in_channel:
        check = False
        for item in final_programs:
            if p[0] == item["program"]:
                check = True
                continue
        if not check:
            final_programs.append({"program": p[0], "data": years})

    sorted_programs = sorted(final_programs, key=lambda x: x["program"])

    return { "political group": name, "total": total, "programs": sorted_programs }



@app.get("/v2/minutes-channel-per-politician/{channel}/{name}")
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
    if name not in politicians_list:
        raise HTTPException(status_code=400, detail="Invalid name")
    if channel not in channels:
        raise HTTPException(status_code=400, detail="Invalid channel")
    
    query = f"""
        SELECT DISTINCT program
        FROM {TABLE_NAME}
        WHERE channel = '{channel}'
        ORDER BY program
    """

    programs_in_channel = query_postgresql(query)

    conditions = ["name != 'Soggetto Collettivo'", "fullname = %s", "channel = %s"]
    params = [name, channel]

    if affiliation_ != "all":
        if affiliation_ not in affiliations:
            raise HTTPException(status_code=400, detail="Invalid affiliation")
        conditions.append("affiliation = %s")
        params.append(affiliation_)
    if program_ != "all":
        if program_ not in programs:
            raise HTTPException(status_code=400, detail="Invalid program")
        conditions.append("program = %s")
        params.append(program_)
    if topic_ != "all":
        if topic_ not in topics:
            raise HTTPException(status_code=400, detail="Invalid topic")
        conditions.append("topic = %s")
        params.append(topic_)
    if kind_ != "both":
        conditions.append("kind = %s")
        params.append(kind_)

    condition_str = " AND ".join(conditions)

    query = f"""
        SELECT program, EXTRACT(YEAR FROM day) AS year, SUM(duration) AS total_duration
        FROM {TABLE_NAME}
        WHERE {condition_str} AND day BETWEEN %s AND %s
        GROUP BY program, EXTRACT(YEAR FROM day)
        ORDER BY program, total_duration DESC
    """
    params.extend([start_date_, end_date_])

    data = query_postgresql(query, params)

    first_year = int(start_date_.split('/')[0])
    last_year = int(end_date_.split('/')[0])
    
    years = {}
    while first_year != (last_year + 1):
        years[str(first_year)] = 0
        first_year += 1

    final_programs = []
    for p in programs_in_channel:
        final_programs.append({"program": p[0], "data": years.copy()})


    total = 0

    while len(data) != 0:
        temp_data = data.pop(0)
        for item in final_programs:
            if item["program"] == temp_data[0]:
                item["data"][str(temp_data[1])] = temp_data[2]
                total += temp_data[2]
                break

    return { "politician": name, "total": total, "programs": final_programs }


@app.get("/v2/minutes-channel-per-political-group/{channel}/{name}")
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
    if name not in political_groups_list:
        raise HTTPException(status_code=400, detail="Invalid name")
    if channel not in channels:
        raise HTTPException(status_code=400, detail="Invalid channel")
    
    query = f"""
        SELECT DISTINCT program
        FROM {TABLE_NAME}
        WHERE channel = '{channel}'
        ORDER BY program
    """

    programs_in_channel = query_postgresql(query)

    conditions = ["name = 'Soggetto Collettivo'", "lastname = %s", "channel = %s"]
    params = [name, channel]

    if program_ != "all":
        if program_ not in programs:
            raise HTTPException(status_code=400, detail="Invalid program")
        conditions.append("program = %s")
        params.append(program_)
    if topic_ != "all":
        if topic_ not in topics:
            raise HTTPException(status_code=400, detail="Invalid topic")
        conditions.append("topic = %s")
        params.append(topic_)
    if kind_ != "both":
        conditions.append("kind = %s")
        params.append(kind_)

    condition_str = " AND ".join(conditions)

    query = f"""
        SELECT program, EXTRACT(YEAR FROM day) AS year, SUM(duration) AS total_duration
        FROM {TABLE_NAME}
        WHERE {condition_str} AND day BETWEEN %s AND %s
        GROUP BY program, EXTRACT(YEAR FROM day)
        ORDER BY program, total_duration DESC
    """
    params.extend([start_date_, end_date_])

    data = query_postgresql(query, params)

    first_year = int(start_date_.split('/')[0])
    last_year = int(end_date_.split('/')[0])
    
    years = {}
    while first_year != (last_year + 1):
        years[str(first_year)] = 0
        first_year += 1

    final_programs = []
    for p in programs_in_channel:
        final_programs.append({"program": p[0], "data": years.copy()})


    total = 0

    while len(data) != 0:
        temp_data = data.pop(0)
        for item in final_programs:
            if item["program"] == temp_data[0]:
                item["data"][str(temp_data[1])] = temp_data[2]
                total += temp_data[2]
                break

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
    page_size: int = Query(default=100, description="Page size"),
):
    """
    Return for a politician, all the channels he spoke to, in which programs, 
    what topic it was about, duration and date
    """
    if page < 1 or page_size < 1:
        raise HTTPException(status_code=400, detail="Page and page size must be positive integers.")
    if name not in politicians_list:
        raise HTTPException(status_code=400, detail="Invalid name")

    conditions = ["name != 'Soggetto Collettivo'", "fullname = %s"]
    params = [name]

    if channel_ != "all":
        if channel_ not in channels:
            raise HTTPException(status_code=400, detail="Invalid channel")
        conditions.append("channel = %s")
        params.append(channel_)
    if affiliation_ != "all":
        if affiliation_ not in affiliations:
            raise HTTPException(status_code=400, detail="Invalid affiliation")
        conditions.append("affiliation = %s")
        params.append(affiliation_)
    if program_ != "all":
        if program_ not in programs:
            raise HTTPException(status_code=400, detail="Invalid program")
        conditions.append("program = %s")
        params.append(program_)
    if topic_ != "all":
        if topic_ not in topics:
            raise HTTPException(status_code=400, detail="Invalid topic")
        conditions.append("topic = %s")
        params.append(topic_)
    if kind_ != "both":
        conditions.append("kind = %s")
        params.append(kind_)

    condition_str = " AND ".join(conditions)

    query = f"""
        SELECT channel, program, topic, SUM(duration)
        FROM {TABLE_NAME}
        WHERE {condition_str} AND day BETWEEN %s AND %s
        GROUP BY channel, program, topic
        ORDER BY channel, program, topic
    """
    params.extend([start_date_, end_date_])

    data = query_postgresql(query, params)

    final_channels = []
    channel_dict = {}

    for channel, program, topic, minutes in data:
        if channel not in channel_dict:
            channel_dict[channel] = []
        found = False
        for entry in channel_dict[channel]:
            if entry['program'] == program:
                entry['topics'].append({"topic": topic, "minutes": minutes})
                found = True
                break
        if not found:
            channel_dict[channel].append({
                "program": program,
                "topics": [{"topic": topic, "minutes": minutes}]
            })

    for channel, programs in channel_dict.items():
        final_channels.append({"channel": channel, "programs": programs})

    paginated_channels = final_channels[(page - 1) * page_size: page * page_size]

    return {
        "politician": name,
        "channels": paginated_channels,
        "page": page,
        "page_size": page_size,
        "total_pages": (len(final_channels) + page_size - 1) // page_size,
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
    if page < 1 or page_size < 1:
        raise HTTPException(status_code=400, detail="Page and page size must be positive integers.")
    if name not in political_groups_list:
        raise HTTPException(status_code=400, detail="Invalid name")

    conditions = ["name = 'Soggetto Collettivo'", "lastname = %s"]
    params = [name]

    if channel_ != "all":
        if channel_ not in channels:
            raise HTTPException(status_code=400, detail="Invalid channel")
        conditions.append("channel = %s")
        params.append(channel_)
    if program_ != "all":
        if program_ not in programs:
            raise HTTPException(status_code=400, detail="Invalid program")
        conditions.append("program = %s")
        params.append(program_)
    if topic_ != "all":
        if topic_ not in topics:
            raise HTTPException(status_code=400, detail="Invalid topic")
        conditions.append("topic = %s")
        params.append(topic_)
    if kind_ != "both":
        conditions.append("kind = %s")
        params.append(kind_)

    condition_str = " AND ".join(conditions)

    query = f"""
        SELECT channel, program, topic, SUM(duration)
        FROM {TABLE_NAME}
        WHERE {condition_str} AND day BETWEEN %s AND %s
        GROUP BY channel, program, topic
        ORDER BY channel, program, topic
    """
    params.extend([start_date_, end_date_])

    data = query_postgresql(query, params)

    final_channels = []
    channel_dict = {}

    for channel, program, topic, minutes in data:
        if channel not in channel_dict:
            channel_dict[channel] = []
        found = False
        for entry in channel_dict[channel]:
            if entry['program'] == program:
                entry['topics'].append({"topic": topic, "minutes": minutes})
                found = True
                break
        if not found:
            channel_dict[channel].append({
                "program": program,
                "topics": [{"topic": topic, "minutes": minutes}]
            })

    for channel, programs in channel_dict.items():
        final_channels.append({"channel": channel, "programs": programs})

    paginated_channels = final_channels[(page - 1) * page_size: page * page_size]

    return {
        "political_group": name,
        "channels": paginated_channels,
        "page": page,
        "page_size": page_size,
        "total_pages": (len(final_channels) + page_size - 1) // page_size,
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
    if channel not in channels:
        raise HTTPException(status_code=400, detail="Invalid channel")

    conditions = ["name != 'Soggetto Collettivo'", "channel = %s"]
    params = [channel]

    if name_ != "all":
        if name_ not in politicians_list:
            raise HTTPException(status_code=400, detail="Invalid name")
        conditions.append("fullname = %s")
        params.append(name_)
    if affiliation_ != "all":
        if affiliation_ not in affiliations:
            raise HTTPException(status_code=400, detail="Invalid affiliation")
        conditions.append("affiliation = %s")
        params.append(affiliation_)
    if program_ != "all":
        if program_ not in programs:
            raise HTTPException(status_code=400, detail="Invalid program")
        conditions.append("program = %s")
        params.append(program_)
    if topic_ != "all":
        if topic_ not in topics:
            raise HTTPException(status_code=400, detail="Invalid topic")
        conditions.append("topic = %s")
        params.append(topic_)
    if kind_ != "both":
        conditions.append("kind = %s")
        params.append(kind_)

    condition_str = " AND ".join(conditions)

    query = f"""
        SELECT fullname, SUM(duration)
        FROM {TABLE_NAME}
        WHERE {condition_str} AND day BETWEEN %s AND %s
        GROUP BY fullname
        ORDER BY SUM(duration) DESC
        LIMIT %s
    """
    params.extend([start_date_, end_date_, n_pol])

    result = query_postgresql(query, params)

    final_list = [{"name": name, "minutes": minutes} for name, minutes in result]

    return { "channel": channel, "pol": final_list }


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
    if channel not in channels:
        raise HTTPException(status_code=400, detail="Invalid channel")

    conditions = ["name = 'Soggetto Collettivo'", "channel = %s"]
    params = [channel]

    if name_ != "all":
        if name_ not in political_groups_list:
            raise HTTPException(status_code=400, detail="Invalid name")
        conditions.append("lastname = %s")
        params.append(name_)
    if program_ != "all":
        if program_ not in programs:
            raise HTTPException(status_code=400, detail="Invalid program")
        conditions.append("program = %s")
        params.append(program_)
    if topic_ != "all":
        if topic_ not in topics:
            raise HTTPException(status_code=400, detail="Invalid topic")
        conditions.append("topic = %s")
        params.append(topic_)
    if kind_ != "both":
        conditions.append("kind = %s")
        params.append(kind_)

    condition_str = " AND ".join(conditions)

    query = f"""
        SELECT fullname, SUM(duration)
        FROM {TABLE_NAME}
        WHERE {condition_str} AND day BETWEEN %s AND %s
        GROUP BY fullname
        ORDER BY SUM(duration) DESC
        LIMIT %s
    """
    params.extend([start_date_, end_date_, n_pol])

    result = query_postgresql(query, params)

    final_list = [{"name": name, "minutes": minutes} for name, minutes in result]

    return { "channel": channel, "pol": final_list }

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
    if program not in programs:
        raise HTTPException(status_code=400, detail="Invalid program")

    conditions = ["name != 'Soggetto Collettivo'", "program = %s"]
    params = [program]

    if name_ != "all":
        if name_ not in politicians_list:
            raise HTTPException(status_code=400, detail="Invalid name")
        conditions.append("fullname = %s")
        params.append(name_)
    if affiliation_ != "all":
        if affiliation_ not in affiliations:
            raise HTTPException(status_code=400, detail="Invalid affiliation")
        conditions.append("affiliation = %s")
        params.append(affiliation_)
    if channel_ != "all":
        if channel_ not in channels:
            raise HTTPException(status_code=400, detail="Invalid channel")
        conditions.append("program = %s")
        params.append(channel_)
    if topic_ != "all":
        if topic_ not in topics:
            raise HTTPException(status_code=400, detail="Invalid topic")
        conditions.append("topic = %s")
        params.append(topic_)
    if kind_ != "both":
        conditions.append("kind = %s")
        params.append(kind_)

    condition_str = " AND ".join(conditions)

    query = f"""
        SELECT fullname, SUM(duration)
        FROM {TABLE_NAME}
        WHERE {condition_str} AND day BETWEEN %s AND %s
        GROUP BY fullname
        ORDER BY SUM(duration) DESC
        LIMIT %s
    """
    params.extend([start_date_, end_date_, n_pol])

    result = query_postgresql(query, params)

    final_list = [{"name": name, "minutes": minutes} for name, minutes in result]

    return { "program": program, "pol": final_list }


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
    if program not in programs:
        raise HTTPException(status_code=400, detail="Invalid program")

    conditions = ["name = 'Soggetto Collettivo'", "program = %s"]
    params = [program]

    if name_ != "all":
        if name_ not in political_groups_list:
            raise HTTPException(status_code=400, detail="Invalid name")
        conditions.append("lastname = %s")
        params.append(name_)
    if channel_ != "all":
        if channel_ not in channels:
            raise HTTPException(status_code=400, detail="Invalid channel")
        conditions.append("program = %s")
        params.append(channel_)
    if topic_ != "all":
        if topic_ not in topics:
            raise HTTPException(status_code=400, detail="Invalid topic")
        conditions.append("topic = %s")
        params.append(topic_)
    if kind_ != "both":
        conditions.append("kind = %s")
        params.append(kind_)

    condition_str = " AND ".join(conditions)

    query = f"""
        SELECT fullname, SUM(duration)
        FROM {TABLE_NAME}
        WHERE {condition_str} AND day BETWEEN %s AND %s
        GROUP BY fullname
        ORDER BY SUM(duration) DESC
        LIMIT %s
    """
    params.extend([start_date_, end_date_, n_pol])

    result = query_postgresql(query, params)

    final_list = [{"name": name, "minutes": minutes} for name, minutes in result]

    return { "program": program, "pol": final_list }