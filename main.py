from fastapi import FastAPI, BackgroundTasks
import stanza
from pydantic import BaseModel
import gc

app = FastAPI()

class Sentence_payload(BaseModel):
    sentence: str
    language: str

def freeMemory(args):
    for arg in args:
        del arg
    del args
    gc.collect()

@app.get('/health')
async def health():
    return {'status': 'running'}

@app.post('/parse')
async def depParse(payload: Sentence_payload, background_tasks: BackgroundTasks):
    stanza.download(payload.language, 'models')
    parser = stanza.Pipeline(lang=payload.language, processors='tokenize, pos, lemma, depparse', dir='models')
    doc: stanza.Document = parser(payload.sentence)
    background_tasks.add_task(freeMemory, [doc, parser])
    return doc.to_dict()
