import requests
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlsplit
import xml.etree.ElementTree as ET
import csv
from contextlib import closing
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
import psycopg2
from corrections import corrections_
import pandas as pd
import numpy as np


DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("Set the DATABASE_URL environment variable before starting AGCOM.")

# Intestazioni per simulare un browser
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
}

#FUNZIONE PER TROVARE TUTTI I LINK CHE CONTENGONO DATI DI MONITORAGGIO TELEVISIVO
def get_links():
    base_url = "https://www.agcom.it/dati-elementari-di-monitoraggio-televisivo?page="      # URL di partenza
    i=0
    list_url = []

    while True:
        url = base_url + str(i)     #URL di ogni pagina
        
        response = requests.get(url, headers=headers, timeout=60)       # Richiesta HTTP per ottenere il contenuto della pagina
        response.raise_for_status()     # Controlla se la richiesta ha avuto successo

        soup = BeautifulSoup(response.text, 'html.parser')      # Parsing del contenuto HTML

        all_links = soup.find_all('a', href=True)       # Trova tutti i link nella pagina

        filtered_links = [urljoin(url, link['href']) for link in all_links if "/node/" in link['href']]     # Filtro dei link che contengono 'node'

        if len(filtered_links) == 0:    # Se non trova più link esci
            break

        list_url.extend(filtered_links)     # aggiungi alla lista finale
        i=i+1   # prossima pagina
    if not list_url:
        raise RuntimeError("Nessuna pagina di monitoraggio trovata sul sito AGCOM.")
    return list(dict.fromkeys(list_url))


#FUNZIONE PER TROVARE IL LINK PER IL FILE XML PER OGNI PAGINA TROVATA
def find_xml_link(page_url):
    response = requests.get(page_url, headers=headers, timeout=60)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    for link in soup.find_all('a', href=True):
        if urlsplit(link['href']).path.lower().endswith(".xml"):
            return urljoin(page_url, link['href'])
    raise RuntimeError(f"Nessun allegato XML in {page_url}")


#FUNZIONE PER TRASFORMARE LE DATE (STRINGHE) IN DATETIME
def parse_date(date_str):
    formats = [
        "%d.%m.%Y %H:%M:%S", 
        "%d-%m-%Y %H:%M:%S", 
        "%d/%m/%Y %H:%M:%S", 
        "%d.%m.%Y %H:%M",
        "%d-%m-%Y %H:%M",
        "%d/%m/%Y %H:%M",
        "%d.%m.%Y",
        "%d-%m-%Y",
        "%d/%m/%Y"
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    if(date_str == ' D-NN- UN  00:00'):      #dato non valido trovato nell'XML
        return "non-valid data"
    raise ValueError(f"Formato data non riconosciuto: {date_str}")


#FUNZIONE PER TRASFORMARE UN XML IN CSV
def from_xml_to_csv(file_xml):
    tree = ET.parse(file_xml)
    root = tree.getroot()

    url_csv = file_xml.with_suffix(".csv")

    with open(url_csv, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['channel', 'program', 'day', 'lastname', 'name', 'affiliation', 'topic', 'duration', 'kind', 'fullname'])
        for idx, record in enumerate(root.findall('RECORD')):
            if idx == 0:  # Salta il primo RECORD che è quello che descrive lo schema
                continue
            if record == None:
                continue
            channel = record.find('CANALE').text
            program = record.find('PROGRAMMA').text
            lastname = record.find('COGNOME').text
            name = record.find('NOME').text
            affiliation = record.find('MICRO_CATEGORIA').text
            topic = record.find('ARGOMENTO').text
            duration = record.find('DURATA').text
            day = record.find('DATA').text
            kind = record.find('TIPO_TEMPO').text
            if (channel is None or program is None or lastname is None or 
                name is None or affiliation is None or topic is None or 
                duration is None or duration.isdigit() is False or day is None or kind is None):
                continue

            date_obj = parse_date(day)
            if(date_obj == 'non-valid data'):
                continue
            day = date_obj.strftime('%Y-%m-%d')

            if kind == 'Parola' or kind =='parola':
                kind = 'speech'
            elif kind == 'Notizia' or kind == 'notizia':
                kind = 'news'
            else:
                continue
            
            if name == 'Soggetto Collettivo' or name == 'Soggetto collettivo' or name == 'soggetto collettivo' or name == 'soggetto Collettivo':
                name = 'Soggetto Collettivo'
                fullname = lastname
            else:
                fullname = name + " " + lastname

            writer.writerow([channel, program, day, lastname, name, affiliation, topic, duration, kind, fullname])

    return url_csv


#METODO PER SCARICARE I FILE XML, CONVERTIRLI IN CSV, ED ELIMINARE GLI XML
def create_csv(link, directory):
    response = requests.get(link, headers=headers, timeout=60)
    response.raise_for_status()
    xml_path = directory / "source.xml"
    xml_path.write_bytes(response.content)
    return from_xml_to_csv(xml_path)


#METODO PER INSERIRE I DATI DEI FILE CSV NEL SERVER POSTGRESQL
def insert_data_postgresql(page_urls):
    with closing(psycopg2.connect(DATABASE_URL)) as conn, conn.cursor() as cursor, TemporaryDirectory() as directory:
        with conn:
            # Impedisce a due parser di importare gli stessi file contemporaneamente.
            cursor.execute("SELECT pg_advisory_lock(hashtext(%s))", ("agcom:data_parser",))
            cursor.execute("CREATE TABLE IF NOT EXISTS files_list (filename TEXT)")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS records (
                    channel TEXT,
                    program TEXT,
                    day DATE,
                    lastname TEXT,
                    name TEXT,
                    affiliation TEXT,
                    topic TEXT,
                    duration INTEGER,
                    kind TEXT,
                    fullname TEXT
                )
            """)
            cursor.execute("SELECT filename FROM files_list")
            loaded_urls = {row[0] for row in cursor.fetchall()}

        for page_url in page_urls:
            if page_url in loaded_urls:
                continue
            csv_file = create_csv(find_xml_link(page_url), Path(directory))
            df = pd.read_csv(csv_file)
            if df.empty:
                raise RuntimeError(f"Nessun record valido in {page_url}")
            df.replace(corrections_, regex=False, inplace=True)
            df.loc[(df['name'] == 'Antonio') & (df['lastname'] == "D'Al�"), 'lastname'] = "D'Alì"
            df.loc[(df['name'] == 'Ciro') & (df['lastname'] == "D'Al�"), 'lastname'] = "D'Alò"
            df['fullname'] = np.where(df['name'] == 'Soggetto Collettivo', 
                      df['lastname'], 
                      df['name'] + ' ' + df['lastname'])
            df.to_csv(csv_file, index=False, encoding="utf-8")

            with conn, csv_file.open(encoding="utf-8", newline="") as file:
                cursor.copy_expert("COPY records FROM STDIN WITH CSV HEADER", file)
                cursor.execute("INSERT INTO files_list (filename) VALUES (%s)", (page_url,))
            print(f"Importate {len(df)} righe da {page_url}", flush=True)

        cursor.execute("SELECT COUNT(*), MIN(day), MAX(day) FROM records")
        count, first_day, last_day = cursor.fetchone()
        if count == 0:
            raise RuntimeError("La tabella records è vuota dopo l'importazione.")
        print(f"Totale nel database: {count} righe dal {first_day} al {last_day}.")


if __name__ == "__main__":
    insert_data_postgresql(get_links())
