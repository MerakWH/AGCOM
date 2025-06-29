"""
This module provides a series of RESTful APIs to provide data
gathered from the AGCOM site.

Author: Merak Winston Hall
Date: 2024-07-13
"""

import asyncpg
import asyncio
import psycopg2
from typing import Annotated
from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse
from datetime import datetime
import warnings
from datetime import datetime
import datetime as dt
from contextlib import asynccontextmanager
warnings.filterwarnings('ignore')

DB_HOST = "dpg-d1gl8onfte5s738q1160-a.frankfurt-postgres.render.com"
DB_PORT = "5432"
DB_NAME = "agcom_dati_monitoraggio_mr2f"
DB_USER = "agcom_dati_monitoraggio_mr2f_user"
DB_PASSWORD = "6MMMPLGLTpESi1js8gyIzFf20hxrRpqW"
TABLE_NAME = "records"


db_pool = None
kind = ["speech", "news", "both"]

@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool, start_date, end_date, kind, politicians_list, political_groups_list, channels, programs, affiliations, topics

    db_pool = await asyncpg.create_pool(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        min_size=1,
        max_size=10,
    )

    static_data = await get_static_data()
    politicians_list = static_data["politicians"]
    political_groups_list = static_data["political_groups"]
    channels = static_data["channels"]
    programs = static_data["programs"]
    affiliations = static_data["affiliations"]
    topics = static_data["topics"]

    yield
    await db_pool.close()


async def query_postgresql(query: str, params: tuple = None):
    async with db_pool.acquire() as conn:
        records = await conn.fetch(query, *params) if params else await conn.fetch(query)
        return [dict(r) for r in records]
    
def query_postgresql_sync(query, params=None):
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

async def get_min_max_dates():
    query = f"""SELECT MIN(day) AS min, MAX(day) AS max FROM {TABLE_NAME};"""
    result = await query_postgresql(query)
    return result[0]['min'].strftime('%Y/%m/%d'), result[0]['max'].strftime('%Y/%m/%d')

def get_min_max_dates_sync():
    query = f"""SELECT MIN(day), MAX(day) FROM {TABLE_NAME};"""
    result = query_postgresql_sync(query)
    return result[0][0].strftime('%Y/%m/%d'), result[0][1].strftime('%Y/%m/%d')

start_date, end_date = get_min_max_dates_sync()

async def get_static_data():
    politicians_query = f"""
        SELECT DISTINCT fullname
        FROM {TABLE_NAME}
        WHERE name != 'Soggetto Collettivo';
    """
    political_groups_query = f"""
        SELECT DISTINCT lastname
        FROM {TABLE_NAME}
        WHERE name = 'Soggetto Collettivo';
    """
    queries = {
        "channels": f"SELECT DISTINCT channel FROM {TABLE_NAME};",
        "programs": f"SELECT DISTINCT program FROM {TABLE_NAME};",
        "affiliations": f"SELECT DISTINCT affiliation FROM {TABLE_NAME};",
        "topics": f"SELECT DISTINCT topic FROM {TABLE_NAME};"
    }

    politicians = [r['fullname'] for r in await query_postgresql(politicians_query)]
    political_groups = [r['lastname'] for r in await query_postgresql(political_groups_query)]

    channels = [r['channel'] for r in await query_postgresql(queries["channels"])]
    programs = [r['program'] for r in await query_postgresql(queries["programs"])]
    affiliations = [r['affiliation'] for r in await query_postgresql(queries["affiliations"])]
    topics = [r['topic'] for r in await query_postgresql(queries["topics"])]

    return {
        "politicians": politicians,
        "political_groups": political_groups,
        "channels": channels,
        "programs": programs,
        "affiliations": affiliations,
        "topics": topics
    }

def validate_date(date_str):
    try:
        return datetime.strptime(date_str, '%Y/%m/%d')
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY/MM/DD") from exc
    
def add_condition(index, field, value, allowed_list, conditions, params):
    if value != "all" and value != "both":
        if value not in allowed_list:
            raise HTTPException(status_code=400, detail=f"Invalid {field}")
        conditions.append(f"{field} = ${index}")
        params.append(value)
        index += 1
    return index

def add_topics(index, topics_list, conditions, params):
    temp_conditions = []
    for topic_ in topics_list:
        if topic_ not in topics:
                raise HTTPException(status_code=400, detail=f"Invalid topic")
        temp_conditions.append(f"${index}")
        params.append(topic_)
        index += 1
    if topics_list:
        query = "topic IN (" + ", ".join(temp_conditions) + ")"
        conditions.append(query)
    return index

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
    lifespan=lifespan
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

@app.head("/ping")
async def ping():
    return {}

@app.get("/v1/data-for-select")
async def get_data_for_select():
    """
    Return all data used to initialize selects in homepage
    """

    return {"start_date": start_date,
            "end_date": end_date,
            "politicians_list": politicians_list,
            "political_groups_list": political_groups_list,
            "channels": channels,
            "programs": programs,
            "affiliations": affiliations,
            "topics": topics }


@app.get("/v1/politicians")
async def get_politicians(
    request: Request,
    start_date_: str = Query(default=start_date),
    end_date_: str = Query(default=end_date),
    kind_: str = Query(default="both", enum=kind),
    page: int = Query(default=1),
    page_size: int = Query(default=5000)
):

    start_date_obj = datetime.strptime(start_date_, "%Y/%m/%d").date()
    end_date_obj = datetime.strptime(end_date_, "%Y/%m/%d").date()

    kind_filter = "" if kind_ == "both" else f"AND kind = '{kind_}'"

    query = f"""
        SELECT DISTINCT fullname
        FROM {TABLE_NAME}
        WHERE name != 'Soggetto Collettivo' AND day BETWEEN $1 AND $2 {kind_filter}
        GROUP BY fullname
        ORDER BY fullname
    """

    task = asyncio.create_task(query_postgresql(query, (start_date_obj, end_date_obj)))

    while not task.done():
        if await request.is_disconnected():
            task.cancel()
            raise HTTPException(status_code=499, detail="Client disconnected")
        await asyncio.sleep(0.2)

    try:
        rows = await task
    except asyncio.CancelledError:
        raise HTTPException(status_code=499, detail="Query cancelled by client")

    politicians_ = [row['fullname'] for row in rows]

    start = (page - 1) * page_size
    end = start + page_size

    return {
        "total": len(politicians_),
        "politicians": politicians_[start:end],
        "page_size": page_size
    }


@app.get("/v1/political-groups")
async def get_political_groups(
    request: Request,
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
    
    start_date_obj = datetime.strptime(start_date_, "%Y/%m/%d").date()
    end_date_obj = datetime.strptime(end_date_, "%Y/%m/%d").date()

    kind_filter = "" if kind_ == "both" else f"AND kind = '{kind_}'"

    query = f"""
        SELECT DISTINCT lastname
        FROM {TABLE_NAME}
        WHERE name = 'Soggetto Collettivo' AND day BETWEEN $1 AND $2 {kind_filter}
        GROUP BY lastname
        ORDER BY lastname
    """

    task = asyncio.create_task(query_postgresql(query, (start_date_obj, end_date_obj)))

    while not task.done():
        if await request.is_disconnected():
            task.cancel()
            raise HTTPException(status_code=499, detail="Client disconnected")
        await asyncio.sleep(0.2)

    try:
        rows = await task
    except asyncio.CancelledError:
        raise HTTPException(status_code=499, detail="Query cancelled by client")
    
    political_groups_ = [row['lastname'] for row in rows]

    start = (page - 1) * page_size
    end = start + page_size

    return {
        "total": len(political_groups_),
        "political_groups": political_groups_[start:end],
        "page_size": page_size
    }


@app.get("/v1/channels")
async def get_channels(
    request: Request,
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

    task = asyncio.create_task(query_postgresql(query))

    while not task.done():
        if await request.is_disconnected():
            task.cancel()
            raise HTTPException(status_code=499, detail="Client disconnected")
        await asyncio.sleep(0.2)

    try:
        rows = await task
    except asyncio.CancelledError:
        raise HTTPException(status_code=499, detail="Query cancelled by client")

    channels_ = [row['channel'] for row in rows]

    start = (page - 1) * page_size
    end = start + page_size

    return { "channels": channels_[start:end], "page_size": page_size }


@app.get("/v1/programs")
async def get_programs(
    request: Request,
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

    task = asyncio.create_task(query_postgresql(query))

    while not task.done():
        if await request.is_disconnected():
            task.cancel()
            raise HTTPException(status_code=499, detail="Client disconnected")
        await asyncio.sleep(0.2)

    try:
        rows = await task
    except asyncio.CancelledError:
        raise HTTPException(status_code=499, detail="Query cancelled by client")

    programs_ = [row['program'] for row in rows]

    start = (page - 1) * page_size
    end = start + page_size

    return { "programs": programs_[start:end], "page_size": page_size }


@app.get("/v1/affiliations")
async def get_affiliations(
    request: Request,
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

    task = asyncio.create_task(query_postgresql(query))

    while not task.done():
        if await request.is_disconnected():
            task.cancel()
            raise HTTPException(status_code=499, detail="Client disconnected")
        await asyncio.sleep(0.2)

    try:
        rows = await task
    except asyncio.CancelledError:
        raise HTTPException(status_code=499, detail="Query cancelled by client")
    
    affiliations_ = [row['affiliation'] for row in rows]

    start = (page - 1) * page_size
    end = start + page_size

    return { "affiliations": affiliations_[start:end], "page_size": page_size }


@app.get("/v1/topics")
async def get_topics(
    request: Request,
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

    task = asyncio.create_task(query_postgresql(query))

    while not task.done():
        if await request.is_disconnected():
            task.cancel()
            raise HTTPException(status_code=499, detail="Client disconnected")
        await asyncio.sleep(0.2)

    try:
        rows = await task
    except asyncio.CancelledError:
        raise HTTPException(status_code=499, detail="Query cancelled by client")
        
    topics_ = [row['topic'] for row in rows]

    start = (page - 1) * page_size
    end = start + page_size

    return { "topics": topics_[start:end], "page_size": page_size }

# -------------------------------------------------------

@app.get("/v1/politician-topics/{name}")
async def get_politician_topics(
    request: Request,
    name: str,
    start_date_: str = Query(default=start_date),
    end_date_: str = Query(default=end_date),
    kind_: str = Query(default="both", enum=kind),
    channel_: str = Query(default="all"),
    affiliation_: str = Query(default="all"),
    program_: str = Query(default="all"),
    topics_list: Annotated[list[str], Query()] = [],
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

    conditions = ["name != 'Soggetto Collettivo'", "fullname = $1"]
    params = [name]
    index = 2

    index = add_condition(index, "channel", channel_, channels, conditions, params)
    index = add_condition(index, "affiliation", affiliation_, affiliations, conditions, params)
    index = add_condition(index, "program", program_, programs, conditions, params)
    index = add_topics(index, topics_list, conditions, params)
    index = add_condition(index, "kind", kind_, kind, conditions, params )

    conditions.append(f"day BETWEEN ${index} AND ${index + 1}")
    start_date_obj = validate_date(start_date_)
    end_date_obj = validate_date(end_date_)
    params.extend([start_date_obj, end_date_obj])

    condition_str = " AND ".join(conditions)

    query = f"""
        SELECT topic, SUM(duration) as duration, COUNT(*) as interventions
        FROM {TABLE_NAME}
        WHERE {condition_str}
        GROUP BY topic
        ORDER BY topic
    """

    task = asyncio.create_task(query_postgresql(query, tuple(params)))

    while not task.done():
        if await request.is_disconnected():
            task.cancel()
            raise HTTPException(status_code=499, detail="Client disconnected")
        await asyncio.sleep(0.2)

    try:
        rows = await task
    except asyncio.CancelledError:
        raise HTTPException(status_code=499, detail="Query cancelled by client")

    explicit_data = []
    for row in rows:
        temp_topic = row['topic']
        temp_duration = row['duration']
        temp_interventions = row['interventions']
        explicit_data.append({"topic": temp_topic, "minutes": temp_duration, "interventions": temp_interventions})

    paginated_data = explicit_data[(page - 1) * page_size: page * page_size]

    return {"politician": name, "topics": paginated_data, "page_size": page_size}


@app.get("/v1/political-group-topics/{name}")
async def get_political_group_topics(
    request: Request,
    name: str,
    start_date_: str = Query(default=start_date),
    end_date_: str = Query(default=end_date),
    kind_: str = Query(default="both", enum=kind),
    channel_: str = Query(default="all"),
    program_: str = Query(default="all"),
    topics_list: Annotated[list[str], Query()] = [],
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

    conditions = ["name = 'Soggetto Collettivo'", "lastname =$1"]
    params = [name]
    index = 2

    index = add_condition(index, "channel", channel_, channels, conditions, params)
    index = add_condition(index, "program", program_, programs, conditions, params)
    index = add_topics(index, topics_list, conditions, params)
    index = add_condition(index, "kind", kind_, kind, conditions, params )

    conditions.append(f"day BETWEEN ${index} AND ${index + 1}")
    start_date_obj = validate_date(start_date_)
    end_date_obj = validate_date(end_date_)
    params.extend([start_date_obj, end_date_obj])

    condition_str = " AND ".join(conditions)

    query = f"""
        SELECT topic, SUM(duration) as duration, COUNT(*) as interventions
        FROM {TABLE_NAME}
        WHERE {condition_str}
        GROUP BY topic
        ORDER BY topic
    """

    task = asyncio.create_task(query_postgresql(query, tuple(params)))

    while not task.done():
        if await request.is_disconnected():
            task.cancel()
            raise HTTPException(status_code=499, detail="Client disconnected")
        await asyncio.sleep(0.2)

    try:
        rows = await task
    except asyncio.CancelledError:
        raise HTTPException(status_code=499, detail="Query cancelled by client")

    explicit_data = []
    for row in rows:
        temp_topic = row['topic']
        temp_duration = row['duration']
        temp_interventions = row['interventions']
        explicit_data.append({"topic": temp_topic, "minutes": temp_duration, "interventions": temp_interventions})

    paginated_data = explicit_data[(page - 1) * page_size: page * page_size]

    return {"political group": name, "topics": paginated_data, "page_size": page_size}

# -------------------------------------------------------

@app.get("/v1/politician-channels/{name}")
async def get_politician_channels(
    request: Request,
    name: str,
    start_date_: str = Query(default=start_date, description="Start date"),
    end_date_: str = Query(default=end_date, description="End date"),
    kind_: str = Query(default="both", description="Type of data", enum=kind),
    channel_: str = Query(default="all", description="Channel"),
    affiliation_: str = Query(default="all", description="Affiliation"),
    program_: str = Query(default="all", description="Program"),
    topics_list: Annotated[list[str], Query()] = [],
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

    conditions = ["name != 'Soggetto Collettivo'", "fullname = $1"]
    params = [name]
    index = 2

    index = add_condition(index, "channel", channel_, channels, conditions, params)
    index = add_condition(index, "affiliation", affiliation_, affiliations, conditions, params)
    index = add_condition(index, "program", program_, programs, conditions, params)
    index = add_topics(index, topics_list, conditions, params)
    index = add_condition(index, "kind", kind_, kind, conditions, params )

    conditions.append(f"day BETWEEN ${index} AND ${index + 1}")
    start_date_obj = validate_date(start_date_)
    end_date_obj = validate_date(end_date_)
    params.extend([start_date_obj, end_date_obj])

    condition_str = " AND ".join(conditions)

    query = f"""
        SELECT channel, SUM(duration) as duration, COUNT(*) as interventions
        FROM {TABLE_NAME}
        WHERE {condition_str}
        GROUP BY channel
        ORDER BY channel ASC
    """

    task = asyncio.create_task(query_postgresql(query, tuple(params)))

    while not task.done():
        if await request.is_disconnected():
            task.cancel()
            raise HTTPException(status_code=499, detail="Client disconnected")
        await asyncio.sleep(0.2)

    try:
        rows = await task
    except asyncio.CancelledError:
        raise HTTPException(status_code=499, detail="Query cancelled by client")

    explicit_data = []
    for row in rows:
        temp_channel = row['channel']
        temp_duration = row['duration']
        temp_interventions = row['interventions']
        explicit_data.append({"channel": temp_channel, "minutes": temp_duration, "interventions": temp_interventions})

    paginated_data = explicit_data[(page - 1) * page_size: page * page_size]

    return { "politician": name, "channels": paginated_data, "page_size": page_size }


@app.get("/v1/political-group-channels/{name}")
async def get_political_group_channels(
    request: Request,
    name: str,
    start_date_: str = Query(default = start_date, description="Start date"),
    end_date_: str = Query(default = end_date, description="End date"),
    kind_: str = Query(default = "both" , description="Type of data", enum = kind),
    channel_: str = Query(default = "all", description="Channel"),
    program_: str = Query(default = "all", description="Program"),
    topics_list: Annotated[list[str], Query()] = [],
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

    conditions = ["name = 'Soggetto Collettivo'", "lastname = $1"]
    params = [name]
    index = 2

    index = add_condition(index, "channel", channel_, channels, conditions, params)
    index = add_condition(index, "program", program_, programs, conditions, params)
    index = add_topics(index, topics_list, conditions, params)
    index = add_condition(index, "kind", kind_, kind, conditions, params )

    conditions.append(f"day BETWEEN ${index} AND ${index + 1}")
    start_date_obj = validate_date(start_date_)
    end_date_obj = validate_date(end_date_)
    params.extend([start_date_obj, end_date_obj])

    condition_str = " AND ".join(conditions)

    query = f"""
        SELECT channel, SUM(duration) as duration, COUNT(*) as interventions
        FROM {TABLE_NAME}
        WHERE {condition_str}
        GROUP BY channel
        ORDER BY channel ASC
    """

    task = asyncio.create_task(query_postgresql(query, tuple(params)))

    while not task.done():
        if await request.is_disconnected():
            task.cancel()
            raise HTTPException(status_code=499, detail="Client disconnected")
        await asyncio.sleep(0.2)

    try:
        rows = await task
    except asyncio.CancelledError:
        raise HTTPException(status_code=499, detail="Query cancelled by client")

    explicit_data = []
    for row in rows:
        temp_channel = row['channel']
        temp_duration = row['duration']
        temp_interventions = row['interventions']
        explicit_data.append({"channel": temp_channel, "minutes": temp_duration, "interventions": temp_interventions})

    paginated_data = explicit_data[(page - 1) * page_size: page * page_size]

    return { "political group": name, "channels": paginated_data, "page_size": page_size }

# -------------------------------------------------------

@app.get("/v1/politicians-affiliation/{name}")
async def get_politicians_affiliation(
    name: str,
    request: Request
):
    """
    Return how many politicians participate (have participated) in an affiliation
    """
    if name not in affiliations:
        raise HTTPException(status_code=400, detail="Invalid affiliation")

    query = f"""
        SELECT DISTINCT fullname
        FROM {TABLE_NAME}
        WHERE affiliation = $1 AND fullname != affiliation
    """
    task = asyncio.create_task(query_postgresql(query, tuple([name])))

    while not task.done():
        if await request.is_disconnected():
            task.cancel()
            raise HTTPException(status_code=499, detail="Client disconnected")
        await asyncio.sleep(0.2)

    try:
        rows = await task
    except asyncio.CancelledError:
        raise HTTPException(status_code=499, detail="Query cancelled by client")

    final_list = [row['fullname'] for row in rows]

    return {"affiliation": name, "politicians": final_list}


@app.get("/v1/affiliations-politician/{name}")
async def get_affiliations_politician(
    name: str,
    request: Request
):
    """
    Return how many affiliations a politician has participated in
    """
    if name not in politicians_list:
        raise HTTPException(status_code=400, detail="Invalid politician")

    query = f"""
        SELECT DISTINCT affiliation
        FROM {TABLE_NAME}
        WHERE fullname = $1
    """

    task = asyncio.create_task(query_postgresql(query, tuple([name])))

    while not task.done():
        if await request.is_disconnected():
            task.cancel()
            raise HTTPException(status_code=499, detail="Client disconnected")
        await asyncio.sleep(0.2)

    try:
        rows = await task
    except asyncio.CancelledError:
        raise HTTPException(status_code=499, detail="Query cancelled by client")

    final_list = [row['affiliation'] for row in rows]

    return {"politician": name, "affiliations": final_list}

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

    data = query_postgresql_sync(query)

    start_date_ = data[0][0].strftime('%Y-%m-%d')
    end_date_ = data[0][1].strftime('%Y-%m-%d')

    return {"first_date": start_date_, "end_date": end_date_}

# -------------------------------------------------------

@app.get("/v1/interventions-politician-per-year/{name}")
async def get_interventions_politician_per_year(
    request: Request,
    name: str,
    start_date_: str = Query(default = start_date, description="Start date"),
    end_date_: str = Query(default = end_date, description="End date"),
    kind_: str = Query(default = "both" , description="Type of data", enum = kind),
    channel_: str = Query(default = "all", description="Channel"),
    affiliation_: str = Query(default = "all", description="Affiliation"),
    program_: str = Query(default = "all", description="Program"),
    topics_list: Annotated[list[str], Query()] = [],
):
    """
    Return how much a politician has intervened in tv per year
    """
    if name not in politicians_list:
        raise HTTPException(status_code=400, detail="Invalid name")

    conditions = ["name != 'Soggetto Collettivo'", "fullname = $1"]
    params = [name]
    index = 2

    index = add_condition(index, "channel", channel_, channels, conditions, params)
    index = add_condition(index, "affiliation", affiliation_, affiliations, conditions, params)
    index = add_condition(index, "program", program_, programs, conditions, params)
    index = add_topics(index, topics_list, conditions, params)
    index = add_condition(index, "kind", kind_, kind, conditions, params )

    conditions.append(f"day BETWEEN ${index} AND ${index + 1}")
    start_date_obj = validate_date(start_date_)
    end_date_obj = validate_date(end_date_)
    params.extend([start_date_obj, end_date_obj])

    condition_str = " AND ".join(conditions)

    query = f"""
        SELECT EXTRACT(YEAR FROM day) AS year, COUNT(*) AS interventions, SUM(duration) AS duration
        FROM {TABLE_NAME}
        WHERE {condition_str}
        GROUP BY year
        ORDER BY year
    """

    task = asyncio.create_task(query_postgresql(query, tuple(params)))

    while not task.done():
        if await request.is_disconnected():
            task.cancel()
            raise HTTPException(status_code=499, detail="Client disconnected")
        await asyncio.sleep(0.2)

    try:
        rows = await task
    except asyncio.CancelledError:
        raise HTTPException(status_code=499, detail="Query cancelled by client")


    temp_years = [int(row['year']) for row in rows]
    temp_interventions = [row['interventions'] for row in rows]
    temp_minutes = [row['duration'] for row in rows]
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
    request: Request,
    name: str,
    start_date_: str = Query(default = start_date, description="Start date"),
    end_date_: str = Query(default = end_date, description="End date"),
    kind_: str = Query(default = "both" , description="Type of data", enum = kind),
    channel_: str = Query(default = "all", description="Channel"),
    program_: str = Query(default = "all", description="Program"),
    topics_list: Annotated[list[str], Query()] = [],
):
    """
    Return how much a political group has intervened in tv per year
    """
    if name not in political_groups_list:
        raise HTTPException(status_code=400, detail="Invalid name")

    conditions = ["name = 'Soggetto Collettivo'", "lastname = $1"]
    params = [name]
    index = 2

    index = add_condition(index, "channel", channel_, channels, conditions, params)
    index = add_condition(index, "program", program_, programs, conditions, params)
    index = add_topics(index, topics_list, conditions, params)
    index = add_condition(index, "kind", kind_, kind, conditions, params )

    conditions.append(f"day BETWEEN ${index} AND ${index + 1}")
    start_date_obj = validate_date(start_date_)
    end_date_obj = validate_date(end_date_)
    params.extend([start_date_obj, end_date_obj])

    condition_str = " AND ".join(conditions)

    query = f"""
        SELECT EXTRACT(YEAR FROM day) AS year, COUNT(*) AS interventions, SUM(duration) AS duration
        FROM {TABLE_NAME}
        WHERE {condition_str}
        GROUP BY year
        ORDER BY year
    """

    task = asyncio.create_task(query_postgresql(query, tuple(params)))

    while not task.done():
        if await request.is_disconnected():
            task.cancel()
            raise HTTPException(status_code=499, detail="Client disconnected")
        await asyncio.sleep(0.2)

    try:
        rows = await task
    except asyncio.CancelledError:
        raise HTTPException(status_code=499, detail="Query cancelled by client")


    temp_years = [int(row['year']) for row in rows]
    temp_interventions = [row['interventions'] for row in rows]
    temp_minutes = [row['duration'] for row in rows]
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
    request: Request,
    name: str,
    year: str = Query(description="choose year"),
    kind_: str = Query(default = "both" , description="Type of data", enum = kind),
    channel_: str = Query(default = "all", description="Channel"),
    affiliation_: str = Query(default = "all", description="Affiliation"),
    program_: str = Query(default = "all", description="Program"),
    topics_list: Annotated[list[str], Query()] = [],
    page: int = Query(default=1, description="Page number"),
    page_size: int = Query(default=367, description="Page size")
):
    """
    Return how much a politician has intervened in tv per day for a specific year
    """
    if page < 1 or page_size < 1:
        raise HTTPException(status_code=400, detail="Page and page size must be positive integers.")
    if name not in politicians_list:
        raise HTTPException(status_code=400, detail="Invalid name")

    conditions = ["name != 'Soggetto Collettivo'", "fullname = $1"]
    params = [name]
    index = 2

    index = add_condition(index, "channel", channel_, channels, conditions, params)
    index = add_condition(index, "affiliation", affiliation_, affiliations, conditions, params)
    index = add_condition(index, "program", program_, programs, conditions, params)
    index = add_topics(index, topics_list, conditions, params)
    index = add_condition(index, "kind", kind_, kind, conditions, params )

    start_date_ = str(year) + "/01/01"
    end_date_ = str(year) + "/12/31"
    conditions.append(f"day BETWEEN ${index} AND ${index + 1}")
    start_date_obj = validate_date(start_date_)
    end_date_obj = validate_date(end_date_)
    params.extend([start_date_obj, end_date_obj])

    condition_str = " AND ".join(conditions)

    query = f"""
        SELECT day, COUNT(*) AS interventions, COALESCE(SUM(duration), 0) AS duration
        FROM {TABLE_NAME}
        WHERE {condition_str}
        GROUP BY day 
        ORDER BY day
    """

    task = asyncio.create_task(query_postgresql(query, tuple(params)))

    while not task.done():
        if await request.is_disconnected():
            task.cancel()
            raise HTTPException(status_code=499, detail="Client disconnected")
        await asyncio.sleep(0.2)

    try:
        rows = await task
    except asyncio.CancelledError:
        raise HTTPException(status_code=499, detail="Query cancelled by client")


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

    for row in rows:
        results [str(row['day'])] = {"interventions": row["interventions"],
                "minutes": row["duration"]}

    paginated_list = list(results.items())[(page - 1) * page_size : page * page_size]

    max_value = 0
    if paginated_list:
        max_value = max(paginated_list, key=lambda x: x[1]["interventions"])[1]["interventions"]

    return {"politician": name, "interventions": paginated_list, 
            "max_value": max_value, "page_size": page_size}


@app.get("/v1/interventions-political-group-per-day/{name}")
async def get_interventions_political_group_per_day(
    request: Request,
    name: str,
    year: str = Query(description="choose year"),
    kind_: str = Query(default = "both" , description="Type of data", enum = kind),
    channel_: str = Query(default = "all", description="Channel"),
    program_: str = Query(default = "all", description="Program"),
    topics_list: Annotated[list[str], Query()] = [],
    page: int = Query(default=1, description="Page number"),
    page_size: int = Query(default=367, description="Page size")
):
    """
    Return how much a political group has intervened in tv per day for a specific year
    """
    if page < 1 or page_size < 1:
        raise HTTPException(status_code=400, detail="Page and page size must be positive integers.")
    if name not in political_groups_list:
        raise HTTPException(status_code=400, detail="Invalid name")

    conditions = ["name = 'Soggetto Collettivo'", "lastname = $1"]
    params = [name]
    index = 2

    index = add_condition(index, "channel", channel_, channels, conditions, params)
    index = add_condition(index, "program", program_, programs, conditions, params)
    index = add_topics(index, topics_list, conditions, params)
    index = add_condition(index, "kind", kind_, kind, conditions, params )

    start_date_ = str(year) + "/01/01"
    end_date_ = str(year) + "/12/31"
    conditions.append(f"day BETWEEN ${index} AND ${index + 1}")
    start_date_obj = validate_date(start_date_)
    end_date_obj = validate_date(end_date_)
    params.extend([start_date_obj, end_date_obj])

    condition_str = " AND ".join(conditions)

    query = f"""
        SELECT day, COUNT(*) AS interventions, COALESCE(SUM(duration), 0) AS duration
        FROM {TABLE_NAME}
        WHERE {condition_str}
        GROUP BY day 
        ORDER BY day
    """

    task = asyncio.create_task(query_postgresql(query, tuple(params)))

    while not task.done():
        if await request.is_disconnected():
            task.cancel()
            raise HTTPException(status_code=499, detail="Client disconnected")
        await asyncio.sleep(0.2)

    try:
        rows = await task
    except asyncio.CancelledError:
        raise HTTPException(status_code=499, detail="Query cancelled by client")


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

    for row in rows:
        results [str(row['day'])] = {"interventions": row["interventions"],
                "minutes": row["duration"]}

    paginated_list = list(results.items())[(page - 1) * page_size : page * page_size]

    max_value = 0
    if paginated_list:
        max_value = max(paginated_list, key=lambda x: x[1]["interventions"])[1]["interventions"]

    return { "political group": name, "interventions": paginated_list,
             "max_value": max_value, "page_size": page_size}

# -------------------------------------------------------

@app.get("/v1/politician-channels-programs/{name}")
async def get_politician_channels_programs(
    request: Request,
    name: str,
    start_date_: str = Query(default = start_date, description="Start date"),
    end_date_: str = Query(default = end_date, description="End date"),
    kind_: str = Query(default = "both" , description="Type of data", enum = kind),
    channel_: str = Query(default = "all", description="Channel"),
    affiliation_: str = Query(default = "all", description="Affiliation"),
    program_: str = Query(default = "all", description="Program"),
    topics_list: Annotated[list[str], Query()] = [],
):
    """
    Return every channel a politician talked in, specifying for each 
    channel all the programs he participated in and for how long (minutes)
    """
    if name not in politicians_list:
        raise HTTPException(status_code=400, detail="Invalid name")

    conditions = ["name != 'Soggetto Collettivo'", "fullname = $1"]
    params = [name]
    index = 2

    index = add_condition(index, "channel", channel_, channels, conditions, params)
    index = add_condition(index, "affiliation", affiliation_, affiliations, conditions, params)
    index = add_condition(index, "program", program_, programs, conditions, params)
    index = add_topics(index, topics_list, conditions, params)
    index = add_condition(index, "kind", kind_, kind, conditions, params )

    conditions.append(f"day BETWEEN ${index} AND ${index + 1}")
    start_date_obj = validate_date(start_date_)
    end_date_obj = validate_date(end_date_)
    params.extend([start_date_obj, end_date_obj])

    condition_str = " AND ".join(conditions)

    query = f"""
        SELECT channel, program, COUNT(*) AS interventions, SUM(duration) AS duration
        FROM {TABLE_NAME}
        WHERE {condition_str}
        GROUP BY channel, program
        ORDER BY channel, duration DESC;
    """

    task = asyncio.create_task(query_postgresql(query, tuple(params)))

    while not task.done():
        if await request.is_disconnected():
            task.cancel()
            raise HTTPException(status_code=499, detail="Client disconnected")
        await asyncio.sleep(0.2)

    try:
        rows = await task
    except asyncio.CancelledError:
        raise HTTPException(status_code=499, detail="Query cancelled by client")

    final_channels = []
    while len(rows) != 0:
        temp_programs = []
        temp_data = rows.pop(0)
        temp_channel = temp_data['channel']
        temp_programs.append({"program": temp_data['program'], "interventions": temp_data['interventions'], "minutes": temp_data['duration']})

        
        while len(rows) != 0 and rows[0]['channel'] == temp_channel:
            temp_data = rows.pop(0)
            temp_programs.append({"program": temp_data['program'], "interventions": temp_data['interventions'], "minutes": temp_data['duration']})
            
        final_channels.append({"channel": temp_channel, "programs": temp_programs})

    return { "politician": name, "channels": final_channels }


@app.get("/v1/political-group-channels-programs/{name}")
async def get_political_group_channels_programs(
    request: Request,
    name: str,
    start_date_: str = Query(default = start_date, description="Start date"),
    end_date_: str = Query(default = end_date, description="End date"),
    kind_: str = Query(default = "both" , description="Type of data", enum = kind),
    channel_: str = Query(default = "all", description="Channel"),
    program_: str = Query(default = "all", description="Program"),
    topics_list: Annotated[list[str], Query()] = [],
):
    """
    Return every channel a political group talked in, specifying for each 
    channel all the programs he participated in and for how long (minutes)
    """
    if name not in political_groups_list:
        raise HTTPException(status_code=400, detail="Invalid name")

    conditions = ["name = 'Soggetto Collettivo'", "lastname = $1"]
    params = [name]
    index = 2

    index = add_condition(index, "channel", channel_, channels, conditions, params)
    index = add_condition(index, "program", program_, programs, conditions, params)
    index = add_topics(index, topics_list, conditions, params)
    index = add_condition(index, "kind", kind_, kind, conditions, params )

    conditions.append(f"day BETWEEN ${index} AND ${index + 1}")
    start_date_obj = validate_date(start_date_)
    end_date_obj = validate_date(end_date_)
    params.extend([start_date_obj, end_date_obj])

    condition_str = " AND ".join(conditions)

    query = f"""
        SELECT channel, program, COUNT(*) AS interventions, SUM(duration) AS duration
        FROM {TABLE_NAME}
        WHERE {condition_str}
        GROUP BY channel, program
        ORDER BY channel, duration DESC;
    """

    task = asyncio.create_task(query_postgresql(query, tuple(params)))

    while not task.done():
        if await request.is_disconnected():
            task.cancel()
            raise HTTPException(status_code=499, detail="Client disconnected")
        await asyncio.sleep(0.2)

    try:
        rows = await task
    except asyncio.CancelledError:
        raise HTTPException(status_code=499, detail="Query cancelled by client")

    final_channels = []
    while len(rows) != 0:
        temp_programs = []
        temp_data = rows.pop(0)
        temp_channel = temp_data['channel']
        temp_programs.append({"program": temp_data['program'], "interventions": temp_data['interventions'], "minutes": temp_data['duration']})
        
        while len(rows) != 0 and rows[0]['channel'] == temp_channel:
            temp_data = rows.pop(0)
            temp_programs.append({"program": temp_data['program'], "interventions": temp_data['interventions'], "minutes": temp_data['duration']})
            
        final_channels.append({"channel": temp_channel, "programs": temp_programs})

    return { "political group": name, "channels": final_channels }

# -------------------------------------------------------

@app.get("/v1/channel-programs-politician/{name}/{channel}")
async def get_channel_programs_politician(
    request: Request,
    name: str,
    channel: str,
    start_date_: str = Query(default = start_date, description="Start date"),
    end_date_: str = Query(default = end_date, description="End date"),
    kind_: str = Query(default = "both" , description="Type of data", enum = kind),
    affiliation_: str = Query(default = "all", description="Affiliation"),
    program_: str = Query(default = "all", description="Program"),
    topics_list: Annotated[list[str], Query()] = [],
):
    """
    Return every program of a channel a politician talked in, 
    specifying for each program all the topics and for how long (minutes)
    """
    if name not in politicians_list:
        raise HTTPException(status_code=400, detail="Invalid name")
    if channel not in channels:
        raise HTTPException(status_code=400, detail="Invalid channel")

    conditions = ["name != 'Soggetto Collettivo'", "fullname = $1", "channel = $2"]
    params = [name, channel]
    index = 3

    index = add_condition(index, "affiliation", affiliation_, affiliations, conditions, params)
    index = add_condition(index, "program", program_, programs, conditions, params)
    index = add_topics(index, topics_list, conditions, params)
    index = add_condition(index, "kind", kind_, kind, conditions, params )

    conditions.append(f"day BETWEEN ${index} AND ${index + 1}")
    start_date_obj = validate_date(start_date_)
    end_date_obj = validate_date(end_date_)
    params.extend([start_date_obj, end_date_obj])

    condition_str = " AND ".join(conditions)

    query = f"""
        SELECT program, topic, COUNT(*) AS interventions, SUM(duration) AS duration
        FROM {TABLE_NAME}
        WHERE {condition_str}
        GROUP BY program, topic
        ORDER BY program, duration DESC;
    """

    task = asyncio.create_task(query_postgresql(query, tuple(params)))

    while not task.done():
        if await request.is_disconnected():
            task.cancel()
            raise HTTPException(status_code=499, detail="Client disconnected")
        await asyncio.sleep(0.2)

    try:
        rows = await task
    except asyncio.CancelledError:
        raise HTTPException(status_code=499, detail="Query cancelled by client")

    final_programs = []
    while len(rows) != 0:
        temp_topics = []
        temp_data = rows.pop(0)
        temp_program = temp_data['program']
        temp_topics.append({"topic": temp_data['topic'], "interventions": temp_data['interventions'], "minutes": temp_data['duration']})

        while len(rows) != 0 and rows[0]['program'] == temp_program:
            temp_data = rows.pop(0)
            temp_topics.append({"topic": temp_data['topic'], "interventions": temp_data['interventions'], "minutes": temp_data['duration']})

        final_programs.append({"program": temp_program, "topics": temp_topics})


    return { "politician": name, "channel": channel, "programs": final_programs }


@app.get("/v1/channel-programs-political-group/{name}/{channel}")
async def get_channel_programs_political_group(
    request: Request,
    name: str,
    channel: str,
    start_date_: str = Query(default = start_date, description="Start date"),
    end_date_: str = Query(default = end_date, description="End date"),
    kind_: str = Query(default = "both" , description="Type of data", enum = kind),
    program_: str = Query(default = "all", description="Program"),
    topics_list: Annotated[list[str], Query()] = [],
):
    """
    Return every program of a channel a political group talked in, 
    specifying for each program all the topics and for how long (minutes)
    """
    if name not in political_groups_list:
        raise HTTPException(status_code=400, detail="Invalid name")
    if channel not in channels:
        raise HTTPException(status_code=400, detail="Invalid channel")

    conditions = ["name = 'Soggetto Collettivo'", "lastname = $1", "channel = $2"]
    params = [name, channel]
    index = 3

    index = add_condition(index, "program", program_, programs, conditions, params)
    index = add_topics(index, topics_list, conditions, params)
    index = add_condition(index, "kind", kind_, kind, conditions, params )

    conditions.append(f"day BETWEEN ${index} AND ${index + 1}")
    start_date_obj = validate_date(start_date_)
    end_date_obj = validate_date(end_date_)
    params.extend([start_date_obj, end_date_obj])

    condition_str = " AND ".join(conditions)

    query = f"""
        SELECT program, topic, COUNT(*) AS interventions, SUM(duration) AS duration
        FROM {TABLE_NAME}
        WHERE {condition_str}
        GROUP BY program, topic
        ORDER BY program, duration DESC;
    """

    task = asyncio.create_task(query_postgresql(query, tuple(params)))

    while not task.done():
        if await request.is_disconnected():
            task.cancel()
            raise HTTPException(status_code=499, detail="Client disconnected")
        await asyncio.sleep(0.2)

    try:
        rows = await task
    except asyncio.CancelledError:
        raise HTTPException(status_code=499, detail="Query cancelled by client")


    final_programs = []
    while len(rows) != 0:
        temp_topics = []
        temp_data = rows.pop(0)
        temp_program = temp_data['program']
        temp_topics.append({"topic": temp_data['topic'], "interventions": temp_data['interventions'], "minutes": temp_data['duration']})

        while len(rows) != 0 and rows[0]['program'] == temp_program:
            temp_data = rows.pop(0)
            temp_topics.append({"topic": temp_data['topic'], "interventions": temp_data['interventions'], "minutes": temp_data['duration']})

        final_programs.append({"program": temp_program, "topics": temp_topics})

    return { "political group": name, "channel": channel, "programs": final_programs }

# -------------------------------------------------------

@app.get("/v1/minutes-channel-per-politician/{channel}/{name}")
async def get_minutes_channel_per_politician(
    request: Request,
    channel: str,
    name: str,
    start_date_: str = Query(default = start_date, description="Start date"),
    end_date_: str = Query(default = end_date, description="End date"),
    kind_: str = Query(default = "both" , description="Type of data", enum = kind),
    affiliation_: str = Query(default = "all", description="Affiliation"),
    program_: str = Query(default = "all", description="Program"),
    topics_list: Annotated[list[str], Query()] = [],
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

    task = asyncio.create_task(query_postgresql(query))

    while not task.done():
        if await request.is_disconnected():
            task.cancel()
            raise HTTPException(status_code=499, detail="Client disconnected")
        await asyncio.sleep(0.2)

    try:
        programs_in_channel = await task
    except asyncio.CancelledError:
        raise HTTPException(status_code=499, detail="Query cancelled by client")

    conditions = ["name != 'Soggetto Collettivo'", "fullname = $1", "channel = $2"]
    params = [name, channel]
    index = 3

    index = add_condition(index, "affiliation", affiliation_, affiliations, conditions, params)
    index = add_condition(index, "program", program_, programs, conditions, params)
    index = add_topics(index, topics_list, conditions, params)
    index = add_condition(index, "kind", kind_, kind, conditions, params )

    conditions.append(f"day BETWEEN ${index} AND ${index + 1}")
    start_date_obj = validate_date(start_date_)
    end_date_obj = validate_date(end_date_)
    params.extend([start_date_obj, end_date_obj])

    condition_str = " AND ".join(conditions)

    query = f"""
        SELECT program, day, SUM(duration) AS duration
        FROM {TABLE_NAME}
        WHERE {condition_str}
        GROUP BY program, day
        ORDER BY program, duration DESC;
    """

    task = asyncio.create_task(query_postgresql(query, tuple(params)))

    while not task.done():
        if await request.is_disconnected():
            task.cancel()
            raise HTTPException(status_code=499, detail="Client disconnected")
        await asyncio.sleep(0.2)

    try:
        rows = await task
    except asyncio.CancelledError:
        raise HTTPException(status_code=499, detail="Query cancelled by client")

    last_year = int(end_date_.split('/')[0])

    total = 0

    final_programs = []
    while len(rows) != 0:
        first_year = int(start_date_.split('/')[0])
        years = {}
        while first_year != (last_year + 1):
            years[str(first_year)] = 0
            first_year += 1
        temp_data = rows.pop(0)
        temp_program = temp_data['program']
        years[temp_data['day'].strftime('%Y')] += temp_data['duration']
        total += temp_data['duration']

        while len(rows) != 0 and rows[0]['program'] == temp_program:
            temp_data = rows.pop(0)
            years[temp_data['day'].strftime('%Y')] += temp_data['duration']
            total += temp_data['duration']
        
        final_programs.append({"program": temp_program, "data": years})
    
    first_year = int(start_date_.split('/')[0])
    years = {}
    while first_year != (last_year + 1):
        years[str(first_year)] = 0
        first_year += 1

    for p in programs_in_channel:
        check = False
        for item in final_programs:
            if p['program'] == item["program"]:
                check = True
                continue
        if not check:
            final_programs.append({"program": p['program'], "data": years})

    sorted_programs = sorted(final_programs, key=lambda x: x["program"])

    return { "politician": name, "total": total, "programs": sorted_programs }


@app.get("/v1/minutes-channel-per-political-group/{channel}/{name}")
async def get_minutes_channel_per_political_group(
    request: Request,
    channel: str,
    name: str,
    start_date_: str = Query(default = start_date, description="Start date"),
    end_date_: str = Query(default = end_date, description="End date"),
    kind_: str = Query(default = "both" , description="Type of data", enum = kind),
    program_: str = Query(default = "all", description="Program"),
    topics_list: Annotated[list[str], Query()] = [],
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

    task = asyncio.create_task(query_postgresql(query))

    while not task.done():
        if await request.is_disconnected():
            task.cancel()
            raise HTTPException(status_code=499, detail="Client disconnected")
        await asyncio.sleep(0.2)

    try:
        programs_in_channel = await task
    except asyncio.CancelledError:
        raise HTTPException(status_code=499, detail="Query cancelled by client")

    conditions = ["name = 'Soggetto Collettivo'", "lastname = $1", "channel = $2"]
    params = [name, channel]
    index = 3

    index = add_condition(index, "program", program_, programs, conditions, params)
    index = add_topics(index, topics_list, conditions, params)
    index = add_condition(index, "kind", kind_, kind, conditions, params )

    conditions.append(f"day BETWEEN ${index} AND ${index + 1}")
    start_date_obj = validate_date(start_date_)
    end_date_obj = validate_date(end_date_)
    params.extend([start_date_obj, end_date_obj])

    condition_str = " AND ".join(conditions)

    query = f"""
        SELECT program, day, SUM(duration) AS duration
        FROM {TABLE_NAME}
        WHERE {condition_str}
        GROUP BY program, day
        ORDER BY program, duration DESC;
    """

    task = asyncio.create_task(query_postgresql(query, tuple(params)))

    while not task.done():
        if await request.is_disconnected():
            task.cancel()
            raise HTTPException(status_code=499, detail="Client disconnected")
        await asyncio.sleep(0.2)

    try:
        rows = await task
    except asyncio.CancelledError:
        raise HTTPException(status_code=499, detail="Query cancelled by client")

    last_year = int(end_date_.split('/')[0])

    total = 0

    final_programs = []
    while len(rows) != 0:
        first_year = int(start_date_.split('/')[0])
        years = {}
        while first_year != (last_year + 1):
            years[str(first_year)] = 0
            first_year += 1
        temp_data = rows.pop(0)
        temp_program = temp_data['program']
        years[temp_data['day'].strftime('%Y')] += temp_data['duration']
        total += temp_data['duration']

        while len(rows) != 0 and rows[0]['program'] == temp_program:
            temp_data = rows.pop(0)
            years[temp_data['day'].strftime('%Y')] += temp_data['duration']
            total += temp_data['duration']
        
        final_programs.append({"program": temp_program, "data": years})
    
    first_year = int(start_date_.split('/')[0])
    years = {}
    while first_year != (last_year + 1):
        years[str(first_year)] = 0
        first_year += 1

    for p in programs_in_channel:
        check = False
        for item in final_programs:
            if p['program'] == item["program"]:
                check = True
                continue
        if not check:
            final_programs.append({"program": p['program'], "data": years})

    sorted_programs = sorted(final_programs, key=lambda x: x["program"])

    return { "political group": name, "total": total, "programs": sorted_programs }



@app.get("/v2/minutes-channel-per-politician/{channel}/{name}")
async def get_minutes_channel_per_politician(
    request: Request,
    channel: str,
    name: str,
    start_date_: str = Query(default = start_date, description="Start date"),
    end_date_: str = Query(default = end_date, description="End date"),
    kind_: str = Query(default = "both" , description="Type of data", enum = kind),
    affiliation_: str = Query(default = "all", description="Affiliation"),
    program_: str = Query(default = "all", description="Program"),
    topics_list: Annotated[list[str], Query()] = [],
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

    task = asyncio.create_task(query_postgresql(query))

    while not task.done():
        if await request.is_disconnected():
            task.cancel()
            raise HTTPException(status_code=499, detail="Client disconnected")
        await asyncio.sleep(0.2)

    try:
        programs_in_channel = await task
    except asyncio.CancelledError:
        raise HTTPException(status_code=499, detail="Query cancelled by client")

    conditions = ["name != 'Soggetto Collettivo'", "fullname = $1", "channel = $2"]
    params = [name, channel]
    index = 3

    index = add_condition(index, "affiliation", affiliation_, affiliations, conditions, params)
    index = add_condition(index, "program", program_, programs, conditions, params)
    index = add_topics(index, topics_list, conditions, params)
    index = add_condition(index, "kind", kind_, kind, conditions, params )

    conditions.append(f"day BETWEEN ${index} AND ${index + 1}")
    start_date_obj = validate_date(start_date_)
    end_date_obj = validate_date(end_date_)
    params.extend([start_date_obj, end_date_obj])

    condition_str = " AND ".join(conditions)

    query = f"""
        SELECT program, EXTRACT(YEAR FROM day) AS year, SUM(duration) AS duration
        FROM {TABLE_NAME}
        WHERE {condition_str}
        GROUP BY program, EXTRACT(YEAR FROM day)
        ORDER BY program, duration DESC
    """

    task = asyncio.create_task(query_postgresql(query, tuple(params)))

    while not task.done():
        if await request.is_disconnected():
            task.cancel()
            raise HTTPException(status_code=499, detail="Client disconnected")
        await asyncio.sleep(0.2)

    try:
        rows = await task
    except asyncio.CancelledError:
        raise HTTPException(status_code=499, detail="Query cancelled by client")

    first_year = int(start_date_.split('/')[0])
    last_year = int(end_date_.split('/')[0])
    
    years = {}
    while first_year != (last_year + 1):
        years[str(first_year)] = 0
        first_year += 1

    final_programs = []
    for p in programs_in_channel:
        final_programs.append({"program": p['program'], "data": years.copy()})

    total = 0

    while len(rows) != 0:
        temp_data = rows.pop(0)
        for item in final_programs:
            if item["program"] == temp_data['program']:
                item["data"][str(temp_data['year'])] = temp_data['duration']
                total += temp_data['duration']
                break

    return { "politician": name, "total": total, "programs": final_programs }


@app.get("/v2/minutes-channel-per-political-group/{channel}/{name}")
async def get_minutes_channel_per_political_group(
    request: Request,
    channel: str,
    name: str,
    start_date_: str = Query(default = start_date, description="Start date"),
    end_date_: str = Query(default = end_date, description="End date"),
    kind_: str = Query(default = "both" , description="Type of data", enum = kind),
    program_: str = Query(default = "all", description="Program"),
    topics_list: Annotated[list[str], Query()] = [],
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

    task = asyncio.create_task(query_postgresql(query))

    while not task.done():
        if await request.is_disconnected():
            task.cancel()
            raise HTTPException(status_code=499, detail="Client disconnected")
        await asyncio.sleep(0.2)

    try:
        programs_in_channel = await task
    except asyncio.CancelledError:
        raise HTTPException(status_code=499, detail="Query cancelled by client")

    conditions = ["name = 'Soggetto Collettivo'", "lastname = $1", "channel = $2"]
    params = [name, channel]
    index = 3

    index = add_condition(index, "program", program_, programs, conditions, params)
    index = add_topics(index, topics_list, conditions, params)
    index = add_condition(index, "kind", kind_, kind, conditions, params )

    conditions.append(f"day BETWEEN ${index} AND ${index + 1}")
    start_date_obj = validate_date(start_date_)
    end_date_obj = validate_date(end_date_)
    params.extend([start_date_obj, end_date_obj])

    condition_str = " AND ".join(conditions)

    query = f"""
        SELECT program, EXTRACT(YEAR FROM day) AS year, SUM(duration) AS duration
        FROM {TABLE_NAME}
        WHERE {condition_str}
        GROUP BY program, EXTRACT(YEAR FROM day)
        ORDER BY program, duration DESC
    """

    task = asyncio.create_task(query_postgresql(query, tuple(params)))

    while not task.done():
        if await request.is_disconnected():
            task.cancel()
            raise HTTPException(status_code=499, detail="Client disconnected")
        await asyncio.sleep(0.2)

    try:
        rows = await task
    except asyncio.CancelledError:
        raise HTTPException(status_code=499, detail="Query cancelled by client")

    first_year = int(start_date_.split('/')[0])
    last_year = int(end_date_.split('/')[0])
    
    years = {}
    while first_year != (last_year + 1):
        years[str(first_year)] = 0
        first_year += 1

    final_programs = []
    for p in programs_in_channel:
        final_programs.append({"program": p['program'], "data": years.copy()})

    total = 0

    while len(rows) != 0:
        temp_data = rows.pop(0)
        for item in final_programs:
            if item["program"] == temp_data['program']:
                item["data"][str(temp_data['year'])] = temp_data['duration']
                total += temp_data['duration']
                break

    return { "political group": name, "total": total, "programs": final_programs }

# -------------------------------------------------------

@app.get("/v1/channels-programs-topics-politician/{name}")
async def get_channels_programs_topics_politician(
    request: Request,
    name: str,
    start_date_: str = Query(default=start_date, description="Start date"),
    end_date_: str = Query(default=end_date, description="End date"),
    kind_: str = Query(default="both", description="Type of data", enum=kind),
    channel_: str = Query(default="all", description="Channel"),
    affiliation_: str = Query(default="all", description="Affiliation"),
    program_: str = Query(default = "all", description="Program"),
    topics_list: Annotated[list[str], Query()] = [],
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

    conditions = ["name != 'Soggetto Collettivo'", "fullname = $1"]
    params = [name]
    index = 2

    index = add_condition(index, "channel", channel_, channels, conditions, params)
    index = add_condition(index, "affiliation", affiliation_, affiliations, conditions, params)
    index = add_condition(index, "program", program_, programs, conditions, params)
    index = add_topics(index, topics_list, conditions, params)
    index = add_condition(index, "kind", kind_, kind, conditions, params )

    conditions.append(f"day BETWEEN ${index} AND ${index + 1}")
    start_date_obj = validate_date(start_date_)
    end_date_obj = validate_date(end_date_)
    params.extend([start_date_obj, end_date_obj])

    condition_str = " AND ".join(conditions)

    query = f"""
        SELECT channel, program, topic, SUM(duration) as duration
        FROM {TABLE_NAME}
        WHERE {condition_str}
        GROUP BY channel, program, topic
        ORDER BY channel, program, topic
    """

    task = asyncio.create_task(query_postgresql(query, tuple(params)))

    while not task.done():
        if await request.is_disconnected():
            task.cancel()
            raise HTTPException(status_code=499, detail="Client disconnected")
        await asyncio.sleep(0.2)

    try:
        rows = await task
    except asyncio.CancelledError:
        raise HTTPException(status_code=499, detail="Query cancelled by client")

    final_channels = []
    channel_dict = {}

    for row in rows:
        if row['channel'] not in channel_dict:
            channel_dict[row['channel']] = []
        found = False
        for entry in channel_dict[row['channel']]:
            if entry['program'] == row['program']:
                entry['topics'].append({"topic": row['topic'], "minutes": row['duration']})
                found = True
                break
        if not found:
            channel_dict[row['channel']].append({
                "program": row['program'],
                "topics": [{"topic": row['topic'], "minutes": row['duration']}]
            })

    for channel, program in channel_dict.items():
        final_channels.append({"channel": channel, "programs": program})

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
    request: Request,
    name: str,
    start_date_: str = Query(default=start_date, description="Start date"),
    end_date_: str = Query(default=end_date, description="End date"),
    kind_: str = Query(default="both", description="Type of data", enum=kind),
    channel_: str = Query(default="all", description="Channel"),
    program_: str = Query(default="all", description="Program"),
    topics_list: Annotated[list[str], Query()] = [],
    page: int = Query(default=1, description="Page number"),
    page_size: int = Query(default=10000, description="Page size"),
):
    """
    Return for a political group, all the channels they spoke to, in which programs, 
    what topics were discussed, duration, and date.
    """
    if page < 1 or page_size < 1:
        raise HTTPException(status_code=400, detail="Page and page size must be positive integers.")
    if name not in political_groups_list:
        raise HTTPException(status_code=400, detail="Invalid name")

    conditions = ["name = 'Soggetto Collettivo'", "lastname = $1"]
    params = [name]
    index = 2

    index = add_condition(index, "channel", channel_, channels, conditions, params)
    index = add_condition(index, "program", program_, programs, conditions, params)
    index = add_topics(index, topics_list, conditions, params)
    index = add_condition(index, "kind", kind_, kind, conditions, params )

    conditions.append(f"day BETWEEN ${index} AND ${index + 1}")
    start_date_obj = validate_date(start_date_)
    end_date_obj = validate_date(end_date_)
    params.extend([start_date_obj, end_date_obj])

    condition_str = " AND ".join(conditions)

    query = f"""
        SELECT channel, program, topic, SUM(duration) as duration
        FROM {TABLE_NAME}
        WHERE {condition_str}
        GROUP BY channel, program, topic
        ORDER BY channel, program, topic
    """

    task = asyncio.create_task(query_postgresql(query, tuple(params)))

    while not task.done():
        if await request.is_disconnected():
            task.cancel()
            raise HTTPException(status_code=499, detail="Client disconnected")
        await asyncio.sleep(0.2)

    try:
        rows = await task
    except asyncio.CancelledError:
        raise HTTPException(status_code=499, detail="Query cancelled by client")

    final_channels = []
    channel_dict = {}

    for row in rows:
        if row['channel'] not in channel_dict:
            channel_dict[row['channel']] = []
        found = False
        for entry in channel_dict[row['channel']]:
            if entry['program'] == row['program']:
                entry['topics'].append({"topic": row['topic'], "minutes": row['duration']})
                found = True
                break
        if not found:
            channel_dict[row['channel']].append({
                "program": row['program'],
                "topics": [{"topic": row['topic'], "minutes": row['duration']}]
            })

    for channel, program in channel_dict.items():
        final_channels.append({"channel": channel, "programs": program})

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
    request: Request,
    channel: str,
    start_date_: str = Query(default = start_date, description="Start date"),
    end_date_: str = Query(default = end_date, description="End date"),
    kind_: str = Query(default = "both" , description="Type of data", enum = kind),
    name_: str = Query(default = "all", description="Politician"),
    affiliation_: str = Query(default = "all", description="Affiliation"),
    program_: str = Query(default = "all", description="Program"),
    topics_list: Annotated[list[str], Query()] = [],
    n_pol: int = Query(default = 10, description="number of politicians to analyze")
):
    """
    Return how much time a channel dedicated to politicians
    """
    if channel not in channels:
        raise HTTPException(status_code=400, detail="Invalid channel")

    conditions = ["name != 'Soggetto Collettivo'", "channel = $1"]
    params = [channel, n_pol]
    index = 3

    index = add_condition(index, "fullname", name_, politicians_list, conditions, params)
    index = add_condition(index, "affiliation", affiliation_, affiliations, conditions, params)
    index = add_condition(index, "program", program_, programs, conditions, params)
    index = add_topics(index, topics_list, conditions, params)
    index = add_condition(index, "kind", kind_, kind, conditions, params )

    conditions.append(f"day BETWEEN ${index} AND ${index + 1}")
    start_date_obj = validate_date(start_date_)
    end_date_obj = validate_date(end_date_)
    params.extend([start_date_obj, end_date_obj])

    condition_str = " AND ".join(conditions)

    query = f"""
        SELECT fullname, SUM(duration) as duration
        FROM {TABLE_NAME}
        WHERE {condition_str}
        GROUP BY fullname
        ORDER BY duration DESC
        LIMIT $2
    """

    task = asyncio.create_task(query_postgresql(query, tuple(params)))

    while not task.done():
        if await request.is_disconnected():
            task.cancel()
            raise HTTPException(status_code=499, detail="Client disconnected")
        await asyncio.sleep(0.2)

    try:
        rows = await task
    except asyncio.CancelledError:
        raise HTTPException(status_code=499, detail="Query cancelled by client")

    final_list = []
    for row in rows:
        final_list.append({"name": row['fullname'], "minutes": row['duration']})

    return { "channel": channel, "pol": final_list }


@app.get("/v1/channel-political-groups/{channel}")
async def get_channel_political_groups(
    request: Request,
    channel: str,
    start_date_: str = Query(default = start_date, description="Start date"),
    end_date_: str = Query(default = end_date, description="End date"),
    kind_: str = Query(default = "both" , description="Type of data", enum = kind),
    name_: str = Query(default = "all", description="Political group"),
    program_: str = Query(default = "all", description="Program"),
    topics_list: Annotated[list[str], Query()] = [],
    n_pol: int = Query(default = 10, description="number of political groups to analyze")
):
    """
    Return how much time a channel dedicated to political groups
    """
    if channel not in channels:
        raise HTTPException(status_code=400, detail="Invalid channel")

    conditions = ["name = 'Soggetto Collettivo'", "channel = $1"]
    params = [channel, n_pol]
    index = 3

    index = add_condition(index, "fullname", name_, politicians_list, conditions, params)
    index = add_condition(index, "program", program_, programs, conditions, params)
    index = add_topics(index, topics_list, conditions, params)
    index = add_condition(index, "kind", kind_, kind, conditions, params )

    conditions.append(f"day BETWEEN ${index} AND ${index + 1}")
    start_date_obj = validate_date(start_date_)
    end_date_obj = validate_date(end_date_)
    params.extend([start_date_obj, end_date_obj])

    condition_str = " AND ".join(conditions)

    query = f"""
        SELECT fullname, SUM(duration) as duration
        FROM {TABLE_NAME}
        WHERE {condition_str}
        GROUP BY fullname
        ORDER BY duration DESC
        LIMIT $2
    """

    task = asyncio.create_task(query_postgresql(query, tuple(params)))

    while not task.done():
        if await request.is_disconnected():
            task.cancel()
            raise HTTPException(status_code=499, detail="Client disconnected")
        await asyncio.sleep(0.2)

    try:
        rows = await task
    except asyncio.CancelledError:
        raise HTTPException(status_code=499, detail="Query cancelled by client")

    final_list = []
    for row in rows:
        final_list.append({"name": row['fullname'], "minutes": row['duration']})

    return { "channel": channel, "pol": final_list }

# -------------------------------------------------------


@app.get("/v1/program-politicians/{program}")
async def get_program_politicians(
    request: Request,
    program: str,
    start_date_: str = Query(default = start_date, description="Start date"),
    end_date_: str = Query(default = end_date, description="End date"),
    kind_: str = Query(default = "both" , description="Type of data", enum = kind),
    name_: str = Query(default = "all", description="Politician"),
    affiliation_: str = Query(default = "all", description="Affiliation"),
    channel_: str = Query(default = "all", description="Channel"),
    topics_list: Annotated[list[str], Query()] = [],
    n_pol: int = Query(default = 10, description="number of politicians to analyze")
):
    """
    Return how much time a program dedicated to politicians
    """
    if program not in programs:
        raise HTTPException(status_code=400, detail="Invalid program")

    conditions = ["name != 'Soggetto Collettivo'", "program = $1"]
    params = [program, n_pol]
    index = 3

    index = add_condition(index, "fullname", name_, politicians_list, conditions, params)
    index = add_condition(index, "affiliation", affiliation_, affiliations, conditions, params)
    index = add_condition(index, "channel", channel_, channels, conditions, params)
    index = add_topics(index, topics_list, conditions, params)
    index = add_condition(index, "kind", kind_, kind, conditions, params )

    conditions.append(f"day BETWEEN ${index} AND ${index + 1}")
    start_date_obj = validate_date(start_date_)
    end_date_obj = validate_date(end_date_)
    params.extend([start_date_obj, end_date_obj])

    condition_str = " AND ".join(conditions)

    query = f"""
        SELECT fullname, SUM(duration) as duration
        FROM {TABLE_NAME}
        WHERE {condition_str}
        GROUP BY fullname
        ORDER BY duration DESC
        LIMIT $2
    """

    task = asyncio.create_task(query_postgresql(query, tuple(params)))

    while not task.done():
        if await request.is_disconnected():
            task.cancel()
            raise HTTPException(status_code=499, detail="Client disconnected")
        await asyncio.sleep(0.2)

    try:
        rows = await task
    except asyncio.CancelledError:
        raise HTTPException(status_code=499, detail="Query cancelled by client")

    final_list = []
    for row in rows:
        final_list.append({"name": row['fullname'], "minutes": row['duration']})

    return { "program": program, "pol": final_list }


@app.get("/v1/program-political-groups/{program}")
async def get_program_political_groups(
    request: Request,
    program: str,
    start_date_: str = Query(default = start_date, description="Start date"),
    end_date_: str = Query(default = end_date, description="End date"),
    kind_: str = Query(default = "both" , description="Type of data", enum = kind),
    name_: str = Query(default = "all", description="Political group"),
    channel_: str = Query(default = "all", description="Channel"),
    topics_list: Annotated[list[str], Query()] = [],
    n_pol: int = Query(default = 10, description="number of political groups to analyze")
):
    """
    Return how much time a program dedicated to political groups
    """
    if program not in programs:
        raise HTTPException(status_code=400, detail="Invalid program")

    conditions = ["name = 'Soggetto Collettivo'", "program = $1"]
    params = [program, n_pol]
    index = 3

    index = add_condition(index, "fullname", name_, politicians_list, conditions, params)
    index = add_condition(index, "channel", channel_, channels, conditions, params)
    index = add_topics(index, topics_list, conditions, params)
    index = add_condition(index, "kind", kind_, kind, conditions, params )

    conditions.append(f"day BETWEEN ${index} AND ${index + 1}")
    start_date_obj = validate_date(start_date_)
    end_date_obj = validate_date(end_date_)
    params.extend([start_date_obj, end_date_obj])

    condition_str = " AND ".join(conditions)

    query = f"""
        SELECT fullname, SUM(duration) as duration
        FROM {TABLE_NAME}
        WHERE {condition_str}
        GROUP BY fullname
        ORDER BY duration DESC
        LIMIT $2
    """
    task = asyncio.create_task(query_postgresql(query, tuple(params)))

    while not task.done():
        if await request.is_disconnected():
            task.cancel()
            raise HTTPException(status_code=499, detail="Client disconnected")
        await asyncio.sleep(0.2)

    try:
        rows = await task
    except asyncio.CancelledError:
        raise HTTPException(status_code=499, detail="Query cancelled by client")

    final_list = []
    for row in rows:
        final_list.append({"name": row['fullname'], "minutes": row['duration']})

    return { "program": program, "pol": final_list }

# -------------------------------------------------------

@app.get("/v1/politician-getall/{name}")
async def get_politician_getall(
    request: Request,
    name: str,
    date_: str = Query(default="all"),
    kind_: str = Query(default="both", enum=kind),
    channel_: str = Query(default="all"),
    affiliation_: str = Query(default="all"),
    program_: str = Query(default="all"),
    topics_list: Annotated[list[str], Query()] = [],
):
    """
    Return for a politician, all data from selected filters
    """
    if name not in politicians_list:
        raise HTTPException(status_code=400, detail="Invalid name")

    conditions = ["name != 'Soggetto Collettivo'", "fullname = $1"]
    params = [name]
    index = 2

    index = add_condition(index, "channel", channel_, channels, conditions, params)
    index = add_condition(index, "affiliation", affiliation_, affiliations, conditions, params)
    index = add_condition(index, "program", program_, programs, conditions, params)
    index = add_topics(index, topics_list, conditions, params)
    index = add_condition(index, "kind", kind_, kind, conditions, params )

    if date_ != "all":
        conditions.append(f"day = ${index}")
        params.append(validate_date(date_))
        index += 1

    condition_str = " AND ".join(conditions)

    query = f"""
        SELECT *
        FROM {TABLE_NAME}
        WHERE {condition_str}
    """

    task = asyncio.create_task(query_postgresql(query, tuple(params)))

    while not task.done():
        if await request.is_disconnected():
            task.cancel()
            raise HTTPException(status_code=499, detail="Client disconnected")
        await asyncio.sleep(0.2)

    try:
        rows = await task
    except asyncio.CancelledError:
        raise HTTPException(status_code=499, detail="Query cancelled by client")
    
    final_data = []
    for row in rows:
        final_data.append([
            row["channel"],
            row["program"],
            row["day"],
            row["lastname"],
            row["name"],
            row["affiliation"],
            row["topic"],
            row["duration"],
            row["kind"],
            row["fullname"],
            ])        

    return {"politician": name, "data": final_data}


@app.get("/v1/political-group-getall/{name}")
async def get_political_group_getall(
    request: Request,
    name: str,
    date_: str = Query(default="all"),
    kind_: str = Query(default="both", enum=kind),
    channel_: str = Query(default="all"),
    affiliation_: str = Query(default="all"),
    program_: str = Query(default="all"),
    topics_list: Annotated[list[str], Query()] = [],
):
    """
    Return for a political group, all data from selected filters
    """
    if name not in political_groups_list:
        raise HTTPException(status_code=400, detail="Invalid name")

    conditions = ["name = 'Soggetto Collettivo'", "lastname = $1"]
    params = [name]
    index = 2

    index = add_condition(index, "channel", channel_, channels, conditions, params)
    index = add_condition(index, "affiliation", affiliation_, affiliations, conditions, params)
    index = add_condition(index, "program", program_, programs, conditions, params)
    index = add_topics(index, topics_list, conditions, params)
    index = add_condition(index, "kind", kind_, kind, conditions, params )

    if date_ != "all":
        conditions.append(f"day = ${index}")
        params.append(validate_date(date_))
        index += 1

    condition_str = " AND ".join(conditions)

    query = f"""
        SELECT *
        FROM {TABLE_NAME}
        WHERE {condition_str}
    """

    task = asyncio.create_task(query_postgresql(query, tuple(params)))

    while not task.done():
        if await request.is_disconnected():
            task.cancel()
            raise HTTPException(status_code=499, detail="Client disconnected")
        await asyncio.sleep(0.2)

    try:
        rows = await task
    except asyncio.CancelledError:
        raise HTTPException(status_code=499, detail="Query cancelled by client")

    final_data = []
    for row in rows:
        final_data.append([
            row["channel"],
            row["program"],
            row["day"],
            row["lastname"],
            row["name"],
            row["affiliation"],
            row["topic"],
            row["duration"],
            row["kind"],
            row["fullname"],
            ])        

    return {"politician": name, "data": final_data}