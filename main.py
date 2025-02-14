from fastapi import FastAPI
import stanza, datetime
import json
from pydantic import BaseModel
from fastapi_restful.tasks import repeat_every
from stanza.utils.conll import CoNLL
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()

# Origins for CORS handling
origins = ['*']

# add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# While stanza detects if a language is already downloaded and does notdownload it again if not necessary, the detection does take a significant amount of time.
# To save this time a Set of already downloaded languages that only persists at runtime is used to quickly check whether a language is already downloaded.
# This set does NOT represent all languages downloaded since it is initalized empty at start, but will be filled everytime a model is used once.
# This method may not be as failsafe, but in most cases way faster.
loadedLanguages = set()

# Store loaded parsers together with the last time theyhave been used to enable unloading of parsers that have not been used for a while.
loadedParsers = dict()

# the time in seconds how long a parser should be stored after it has been used last.
parser_load_time = 3600

class Sentence_payload(BaseModel):
    sentence: str
    language: str

@app.get('/health')
async def health():
    return {'status': 'running'}

@app.post('/parse')
async def depParse(payload: Sentence_payload):
    # if payload.language not in loadedLanguages:
    #     stanza.download(payload.language, 'models')
    #     loadedLanguages.add(payload.language)
    if payload.language not in loadedParsers.keys():
        parser = stanza.Pipeline(lang=payload.language, processors='tokenize, mwt, pos, lemma, depparse', dir='models')
        loadedParsers[payload.language] = [parser, datetime.datetime.now()]
    else:
        parser = loadedParsers[payload.language][0]
        loadedParsers[payload.language][1] = datetime.datetime.now()
    doc: stanza.Document = parser(payload.sentence)

    #create a json object that represents the dependency parse as a graph
    # a graph is a list of graph elements, where each element is a dict
    stgraph = []
    for sentence in doc.sentences:
        words = []
        root_element = {}
        root_element['id'] = "0"
        root_element['node_type'] = "input"
        stgraph.append({"data" : root_element})
        for word in sentence.words:
            graph_element = {}
            graph_element['id'] = str(word.id)
            graph_element['node_type'] = "input"
            avps = {}
            avps['text'] = word.text
            avps['lemma'] = word.lemma
            avps['upos'] = word.upos
            # if features are not null
            if word.feats != None:
                features = word.feats.split('|')
                for feature in features:
                    if feature != '_':
                        key, value = feature.split('=')
                        avps[key] = value

            graph_element['avp'] = avps
            stgraph.append({"data" : graph_element})

        for dependency in sentence.dependencies:
            graph_element = {}
            graph_element['id'] = "rid" + str(dependency[0].id) + "+" + str(dependency[2].id)
            graph_element['edge_type'] = "edge"
            graph_element['source'] = str(dependency[0].id)
            graph_element['target'] = str(dependency[2].id)
            graph_element['label'] = dependency[1]
            stgraph.append({"data" : graph_element})


    graph_elements = {"graphElements" : stgraph}


    stanzaAnnotation = {"graph" : graph_elements, "conllu" : "{:C}".format(doc)}

    print("{:C}".format(doc))
    print(json.dumps(stgraph))

    # return doc.to_dict()
    return json.dumps(stanzaAnnotation)

# scheduled task that unloads non recently used parsers
@app.on_event('startup')
@repeat_every(seconds=60)
async def unloadParser():
    current_time = datetime.datetime.now()
    for key in loadedParsers.keys():
        last_loaded = loadedParsers[key][1]
        delta: datetime.timedelta = current_time - last_loaded
        if delta.seconds > parser_load_time:
            loadedParsers.pop(key)