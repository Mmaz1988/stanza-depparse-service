from fastapi import FastAPI, BackgroundTasks
import stanza
from pydantic import BaseModel
import gc

app = FastAPI()

class Sentence_payload(BaseModel):
    sentence: str

# init
stanza.download('en', 'models')

def freeMemory(args):
    print('Freeing up Memory')
    for arg in args:
        del arg
    del args
    gc.collect()

@app.get('/health')
async def health():
    return {'status': 'running'}

@app.post('/parse')
async def depParse(payload: Sentence_payload, background_tasks: BackgroundTasks):
    parser = stanza.Pipeline(lang='en', processors='tokenize, pos, lemma, depparse', dir='models')
    doc: stanza.Document = parser(payload.sentence)
    background_tasks.add_task(freeMemory, [doc, parser])
    return doc.to_dict()
