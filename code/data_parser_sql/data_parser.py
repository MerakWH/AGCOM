import requests
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import xml.etree.ElementTree as ET
import csv
from datetime import datetime
import psycopg2


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
        
        response = requests.get(url, headers=headers)       # Richiesta HTTP per ottenere il contenuto della pagina
        response.raise_for_status()     # Controlla se la richiesta ha avuto successo

        soup = BeautifulSoup(response.text, 'html.parser')      # Parsing del contenuto HTML

        all_links = soup.find_all('a', href=True)       # Trova tutti i link nella pagina

        filtered_links = [urljoin(url, link['href']) for link in all_links if "/node/" in link['href']]     # Filtro dei link che contengono 'node'

        if len(filtered_links) == 0:    # Se non trova più link esci
            break

        filtered_links = list(set(filtered_links))  # rimuove valori uguali
        list_url.extend(filtered_links)     # aggiungi alla lista finale
        i=i+1   # prossima pagina
    return list_url


#FUNZIONE PER TROVARE IL LINK PER IL FILE XML PER OGNI PAGINA TROVATA
def find_xml_link(page_url):
    try:
        page_response = requests.get(page_url, headers=headers)
        page_response.raise_for_status()
        page_soup = BeautifulSoup(page_response.text, 'html.parser')
        xml_link = page_soup.find_all('a', href=True)
        filtered_links = [urljoin(page_url, link['href']) for link in xml_link if "/sites/default/files/" in link['href']]
        return filtered_links[0]
    except Exception as e:
        print(f"Errore nel trovare XML in {page_url}: {e}")
    return None


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

    url_csv = file_xml[:-3] + 'csv'
    csv_filenames.append(url_csv)

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

    print("Conversione completata!")


#METODO PER SCARICARE I FILE XML, CONVERTIRLI IN CSV, ED ELIMINARE GLI XML
def create_csv(link):
    directory_name = os.path.dirname(os.path.realpath(__file__))

    # Ottieni il nome del file dall'URL
    nome_file = os.path.basename(link)
    percorso_file = os.path.join(directory_name, nome_file)

    # Scarica il file
    response = requests.get(link, headers=headers)
    if response.status_code == 200:
        with open(percorso_file, 'wb') as f:
            f.write(response.content)
        print(f"File {nome_file} scaricato.")
            
        from_xml_to_csv(nome_file)
    
        # Elimina il file subito dopo
        os.remove(percorso_file)
        print(f"File {nome_file} eliminato.")
    else:
        print(f"Errore nel download di {nome_file}: {response.status_code}")


#METODO PER RIMUOVERE I FILE CSV
def remove_csv(file):
    if file.endswith(".csv") and os.path.isfile(file):
        try:
            os.remove(file)
            print(f"File rimosso: {file}")
        except Exception as e:
            print(f"Errore nella rimozione di {file}: {e}")
    else:
        print(f"File non trovato o non valido: {file}")


#METODO PER INSERIRE I DATI DEI FILE CSV NEL SERVER POSTGRESQL
def insert_data_postgresql(csv_file_list):
    db_config = {
        'dbname': 'agcom_dati_monitoraggio',
        'user': 'agcom_dati_monitoraggio_user',
        'password': 'o6uuicatOkvkAKZc41deozEBd56g8nrm',
        'host': 'dpg-cva6ogbtq21c73bs2j8g-a.frankfurt-postgres.render.com',  
        'port': '5432'
    }
    try:
        # Connessione al database PostgreSQL
        conn = psycopg2.connect(
            dbname=db_config['dbname'],
            user=db_config['user'],
            password=db_config['password'],
            host=db_config['host'],
            port=db_config['port']
        )
        cursor = conn.cursor()
        print('connessione avvenuta!')

        for csv_file in csv_file_list:
        # Apertura del file CSV e inserimento dati
            with open(csv_file, 'r') as file:

                # Costruzione della query SQL
                cursor.copy_expert(f"COPY records FROM STDIN WITH CSV HEADER DELIMITER ','", file)
                conn.commit()
            remove_csv(csv_file)

        print("Dati inseriti con successo.")

    except Exception as e:
        print(f"Errore durante l'inserimento dei dati: {e}")

    finally:
        cursor.close()
        conn.close()



csv_filenames = []

link_list = get_links()
for link in link_list:
    xml_link = find_xml_link(link)
    create_csv(xml_link)

insert_data_postgresql(csv_filenames)