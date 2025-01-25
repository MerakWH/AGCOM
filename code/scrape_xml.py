#!/usr/bin/env python
# coding: utf-8

# In[1]:


import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from io import StringIO
import os
import chardet 
from spellchecker import SpellChecker
from langdetect import detect
import string
import wikipediaapi
from fuzzywuzzy import process


# In[2]:


spell = SpellChecker(language='it')
special_words = {"TG5", "TG24","MAG","OMNIBUS","LA7","UOZZAP!",
                 "TAGADA'","DIMARTEDI'","MARTEDIPIU'","MEDIASET",
                 "TGCOM","TGCOM24","TG4",'CONTROCORRENTE',"DEEJAY",
                 "CROZZA","RAI","TG1","SETTEGIORNI","(L.I.S.)",
                 "150ESIMO","1/2H","#CARTABIANCA","NEWS24",
                 "PARLAMENTANDO","SABATO24","CONTROCORRENTE",
                 "(VN)","PRES.","CATTELAN","PIAZZAPULITA","SILVIO",
                 "SPAZIOLIBERO","TG3","DIGITANGO","BERLUSCONI","COSTANZO",
                 "SIENA","CROZZA","MARMOLADA","LA7",
                 "COVID-19", "OK", "CEO", "NASA", "Wi-Fi"}  


# In[3]:


# # Endpoint URL di Wikidata per le query SPARQL
# endpoint_url = "https://query.wikidata.org/sparql"

# # Query SPARQL per ottenere i nomi dei politici italiani
# query_politicians = """
# SELECT DISTINCT ?givenNameLabel ?familyNameLabel WHERE {
#   ?person wdt:P31 wd:Q5;           # Instance of human
#           wdt:P106 wd:Q82955;      # Occupation: politician
#           wdt:P27 wd:Q38;          # Country of citizenship: Italy
#           wdt:P735 ?givenName;     # Given name
#           wdt:P734 ?familyName.    # Family name
#   SERVICE wikibase:label {         # Get the labels
#     bd:serviceParam wikibase:language "it".
#     ?givenName rdfs:label ?givenNameLabel.
#     ?familyName rdfs:label ?familyNameLabel.
#   }
# }
# ORDER BY ?givenNameLabel ?familyNameLabel
# """
# query_movements = """
# SELECT ?politicalMovement ?politicalMovementLabel WHERE {
#   ?politicalMovement wdt:P31 wd:Q7278;  # Istanza di organizzazione politica
#                  wdt:P17 wd:Q38.        # Localizzata in Italia
#   SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],it". }
# }
# """
# def get_results(endpoint_url, query):
#     headers = {'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0'}
#     data = requests.get(endpoint_url, headers=headers, params={'query': query, 'format': 'json'}).json()
#     return data

# politicians_data = get_results(endpoint_url, query_politicians)
# politicians_movements_data = get_results(endpoint_url, query_movements)
# politicians = {}
# politicians_movements = {}
# politicians_names = [(result['givenNameLabel']['value']) for result in politicians_data['results']['bindings']]
# politicians_familynames = [(result['familyNameLabel']['value']) for result in politicians_data['results']['bindings']]
# politicians_names = list(set(politicians_names))
# politicians_familynames = list(set(politicians_familynames))


# In[4]:


def correct_accent(sentence):
    if sentence is not None:
        substituions = {
            "E'": "È",
            "e'": "è",
            "A'": "À",
            "a'": "à",
            "I'": "Ì",
            "i'": "ì",
            "O'": "Ò",
            "o'": "ò",
            "U'": "Ù",
            "u'": "ù"
        }
        
        for k, v in substituions.items():
            sentence = re.sub(re.escape(k), v, sentence)
        
    return sentence
    


# Function to check for unrecognized characters
def needs_spellcheck(s):
    need = False
    # Definition of the alphabet and accepted characters
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    numbers = "0123456789"
    punctuation_characters = ".,:;!?-'\"()[]{}\\"
    special_characters = "#&@"
    math_characters = "+-*/=%^"
    accents="àèìòùáéíóúäëïöü"
    # Create the pattern that includes all accepted characters
    accepted_characters = alphabet + numbers + punctuation_characters + special_characters + math_characters + accents+ " "
    # Create the regex pattern to find unaccepted characters
    pattern = f"[^{re.escape(accepted_characters)}]"
    if re.search(pattern, s) is not None:
        need = True
    return need



# In[5]:


def correct_politician_movement_name(name):
    if name is not None:
        best_match = process.extractOne(name,list(politicians_movements.values()))
        limit = 90  
        if best_match[1] >= limit:
            return best_match[0]
    return name


# In[6]:


def capitalize_title(text):
    if text is not None:
        conjunctions = {"e", "ma", "o", "né", "che", "se", "per", "con", "di", "a", "da", "in", "su", "tra", "fra"}
        words = text.split()    
        capitalized_words = [
            word.capitalize() if word.lower() not in conjunctions else word.lower()
            for word in words
        ]
        return ' '.join(capitalized_words)
    else:
        return text


# In[7]:


def download_file(url, outputfile,encoding=None):
    headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    response = requests.get(url,headers=headers)
    if encoding is not None:
            response.encoding = 'utf-8-sig'
    with open(outputfile, 'wb') as file:
        file.write(response.content)


# In[8]:


def detect_encoding(file_path): 
    with open(file_path, 'rb') as file: 
        detector = chardet.universaldetector.UniversalDetector() 
        for line in file: 
            detector.feed(line) 
            if detector.done: 
                break
        detector.close() 
    return detector.result['encoding'] 


# In[9]:


# URL of the page to scrape
rooturl = "https://www.agcom.it/"
url_desc = "taxonomy/term/277"
url = rooturl + url_desc
# Custom headers with a User-Agent
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}
# Send a GET request to the page
response = requests.get(url, headers=headers)
response.raise_for_status()  # Check that the request was successful
# Parse the page content
soup = BeautifulSoup(response.content, "html.parser")


# In[10]:


total_pages = 0
# Find the pagination element
pagination = soup.find('ul', class_='pagination pager__items js-pager__items')
# Extract the aria-label attribute
if pagination:
    aria_label = pagination.get('aria-label', '')
    # Extract the value after "of"
    if "of" in aria_label:
        total_pages = int(aria_label.split("of")[1].strip())


# In[11]:


hrefs = []
for pageindex in range(total_pages):
    pageurl = url + "?page=" + str(pageindex)
    response = requests.get(pageurl, headers=headers)
    response.raise_for_status()  # Check that the request was successful
    # Parse the page content
    soup = BeautifulSoup(response.content, "html.parser")
    read_more_links = soup.find_all('a', class_='read-more')
    # Extract the href attributes
    hrefs.extend([link.get('href') for link in read_more_links])


# In[12]:


dataxml = []
for href in hrefs:
    dataurl = rooturl + href.lstrip('/')
    response = requests.get(dataurl, headers=headers)
    response.raise_for_status()  # Check that the request was successful
    soup = BeautifulSoup(response.content, "html.parser")
    xml_links = soup.find_all('a', type='application/xml')
    dataxml.extend([link.get('href') for link in xml_links])


# In[13]:


xmlfile = dataxml[0]
dataurl = rooturl + xmlfile.lstrip('/')
filename = os.path.basename(dataurl)
download_file(dataurl,filename)
encoding = detect_encoding(filename).lower()
xml_content = ""
with open(filename, 'r', encoding=encoding) as file:
    xml_content = file.readlines()[1:]  
    xml_content = ''.join(xml_content)  
data_toclean = pd.read_xml(StringIO(xml_content), parser='lxml')
data_toclean = data_toclean.iloc[2:, :]
del data_toclean['TESTO']


# In[14]:


for xmlfile in dataxml[1:]:
    dataurl = rooturl + xmlfile.lstrip('/')
    filename = os.path.basename(dataurl)
    download_file(dataurl,filename)
    encoding = detect_encoding(filename).lower()
    xml_content = ""
    with open(filename, 'r', encoding=encoding) as file:
        xml_content = file.readlines()[1:]  # Legge tutte le righe eccetto la prima
        xml_content = ''.join(xml_content)  # Unisce le righe in una singola stringa
    
    df= pd.read_xml(StringIO(xml_content), parser='lxml')
    df = df.iloc[2:, :]
    if 'TESTO' in df.columns:
        del df['TESTO']
    data_toclean = pd.concat([data_toclean, df])


# In[15]:


fields = ['ARGOMENTO','PROGRAMMA','MICRO_CATEGORIA'] #,'COGNOME','NOME']


# In[16]:


def replace_question_marks(s):
    if s is not None:
        return re.sub(r'(?<! )\?(?! )', '-', s)

def correct_s(s):
    single = True
    if s is not None:
        if needs_spellcheck(s):
            words = s.split()
            for idx in range(len(words)):
                if needs_spellcheck(words[idx]):
                    if len(words[idx]) > 1:
                        cword = spell.correction(words[idx])
                        if cword is not None:
                            words[idx] = cword
                        else:
                            if words[idx][:-1].isdigit():
                                cword =  words[idx][:-1] + "°"
                                words[idx] = cword
                        single = False
            if single:
                s = spell.correction(s)
                sigle = False
            else:
                s = ' '.join(words)
        s = correct_accent(s)
        s = replace_question_marks(s)
    return s
        
def get_correctvalue(v,dictionary):
    print(dictionary[v])


# In[17]:


for field in fields:
    new_labels = {}
    labels = data_toclean[field].unique()
    for label in labels:
        new_labels[label] = correct_s(label)
    data_toclean[field] = data_toclean[field].map(new_labels).fillna(data_toclean[field])


# In[18]:


data = data_toclean.drop_duplicates().dropna()


# In[19]:


data.DURATA = data.DURATA.astype(int)


# In[20]:


def convertime(datestring):
    rdatestring = None
    if "." in datestring:
        rdatestring = pd.to_datetime(datestring,  format="%d.%m.%Y")
    elif "/" in datestring:
        rdatestring = pd.to_datetime(datestring,  format="%d/%m/%Y")
    return(rdatestring)


# In[21]:


data['DATA'] = data['DATA'].apply(lambda x: x.replace(" 00:00", ""))
data['DATA'] = data['DATA'].apply(lambda x: x.replace(":00", ""))
data['DATA'] = data.DATA.apply(convertime) # = pd.to_datetime(data["DATA"],  format="%d.%m.%Y")


# In[28]:


cols = {"CANALE":"channel",
        "PROGRAMMA":"program",
        "DATA":"day",
        "COGNOME":"lastname",
        "NOME":"name",
        "MICRO_CATEGORIA":"affiliation",
        "ARGOMENTO":"topic",
        "DURATA":"duration",
        "TIPO_TEMPO":"kind"}
data.rename(columns=cols,inplace=True)


# In[29]:


def correct_politician_name(name):
    politicians_names = ["Niccolò Maria","Nicolò","Niccolò","Giosuè",
                         "Totò","Desirè","Andrè","Cécile","Giovì",'Jose',"Alì Listi"]
    if name is not None:
        best_match = process.extractOne(name,politicians_names)
        limit = 90  
        if best_match[1] >= limit:
            return best_match[0]
    return name


# In[30]:


def correct_politician_lastname(name):
    politicians_names = ["Bonafè","Cassì","Schininà","Patanè",
                         "Santanchè","Mulé","Carrà","Aricò",
                         "Verzè",'Scutellà',"Cantù","Zappalà",
                         "Germanà",
                         "D'Alì" #ciro
                         ,"D'Alò" #antonio
                         ,"Miccichè","Lucà","Raschillà",
                         "Saccà","Urzì","Cirinnà","Falcomatà",
                         "Danzì","Bertolè","Porrà","Calabrò",
                         "Macrì","Salmè","Durì","Schilirò",
                         "Niceta Potì",'Scatà',"Alverà","Scarfò"
                         "D'Incà","Samonà","Dessì","Sperlì",
                         "Chiricò","Andò","Muscarà","Chissalè",
                         "Pettenà","Zuccalà","Carlà Campa","Currò","Calò",
                         "Daccò","Montà","Gioffrè","Granà","Ciagà",
                         "Mazzà","Alì","Palù","Carlà","Figà Talamanca",
                         "Mammì","Praticò",'Pellicanò',"Cannistrà",
                         "Verì","Orrù","Borrè",'Wagué',"Scottà","Virzì",
                         "Idà","Pavorè","Spanò",'Venè',"Cà",'Cuè',
                         "Crisà","Nicolò","Niccolò","Giuffrè",
                         "Benvegnù","Marcianò","Dehò","Scamardì",
                         "Schirò","Rösch","Calà Lesina","Gullà",
                         "Faccà","Marù","D'Angeli","D'Alberto",
                         "Ballarò","Chittò","Maffè","Serranò",
                         "Verità","Ingrillì","Giampà","Spirlì"

                         ]
    if name is not None:
        best_match = process.extractOne(name,politicians_names)
        limit = 80  
        if best_match[1] >= limit:
            return best_match[0]
    return name


# In[31]:


new_lastnames = {}
movementstofix = {}
movementstofix["Italia Viva - Italia C'�"] = "Italia Viva - Italia C'è"
movementstofix["L'Italia s'� desta"] = "L'Italia s'è desta"
movementstofix["Movimento Verde � Popolare"] = "Movimento Verde - Popolare"
movementstofix["Comitato io Dico S�"] = "Comitato io Dico Sì"
movementstofix["LAlternativa c�-Lista del Popolo per la Costituzione"] = "LAlternativa c'è-Lista del Popolo per la Costituzione"
movementstofix["Azione - +Europa � Radicali Italiani"] = "Azione - +Europa - Radicali Italiani"
movementstofix["Facciamo Eco � Federazione dei Verdi"] = "Facciamo Eco - Federazione dei Verdi"
movementstofix["Movimento Nazionale per la Sovranit�"] = "Movimento Nazionale per la Sovranità"
movementstofix["Pi� Europa-Centro Democratico"] = "Più Europa-Centro Democratico"
movementstofix["Democrazia � Libert� - La Margherita"] = "Democrazia - Libertà - La Margherita"
movementstofix["Chiamparino per il Piemonte del s�"] = "Chiamparino per il Piemonte del sì"
movementstofix["Pi� Europa"] = "Più Europa"
movementstofix["L'Italia � popolare"] = "L'Italia è popolare"
movementstofix["Ragione e Libert�"] = "Ragione e Libertà"
movementstofix["Il s� delle Libert�"] = "Il sì delle Libertà"
movementstofix["S� Toscana a Sinistra"] = "Sì Toscana a Sinistra"
movementstofix["Comitato Democratici per il S�"] = "Comitato Democratici per il Sì"
movementstofix["Centro Democratico � Italiani in Europa"] = "Centro Democratico - Italiani in Europa"
for name in data.lastname.unique():
    if needs_spellcheck(name):
        nm = correct_politician_lastname(name)
        if nm != name:
            new_lastnames[name] = nm
        else:
            new_lastnames[name] = movementstofix[name]        


# In[32]:


data["lastname"] = data["lastname"].map(new_lastnames).fillna(data["lastname"])


# In[35]:


data.loc[(data['name'] == 'Antonio') & (data['lastname'] == "D'Alì"), 'name'] = "D'Alò"


# In[ ]:


data.to_parquet(".." + os.sep + "docs"  + os.sep +  "data" + os.sep + "agcomdata.parquet")

