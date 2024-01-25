import os
import uuid
from langchain.text_splitter import CharacterTextSplitter
from langchain.chains import ConversationalRetrievalChain
from langchain_community.vectorstores import Chroma
from langchain.schema.document import Document
from langchain.memory.buffer import ConversationBufferMemory
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from api_request import k8s_request, stx_request
from openai import OpenAI


def initiate_sessions():
    global sessions
    sessions = {}

def get_session(session_id): 
    return sessions.get(session_id)

def new_session(model, temperature):
    # Create vectorstore
    llm = ChatOpenAI(
        model_name=model,
        temperature=float(temperature),
        openai_api_key=OPENAI_API_KEY)
    session_id = str(uuid.uuid4())
    memory, retriever = create_vectorstore(llm, session_id)
    # Create chat response generator
    generator = ConversationalRetrievalChain.from_llm(
                llm=llm,
                retriever=retriever,
                memory=memory)
    # Add session to sessions map
    sessions[session_id] = {"generator": generator, "llm": llm, "id": session_id}
    return sessions[session_id]


def create_vectorstore(llm, session_id):
    # Create Chroma vector store
    data_start = "start vectorstore"
    docs = [Document(page_content=x) for x in data_start]
    vectorstore = Chroma.from_documents(documents=docs, embedding=OpenAIEmbeddings(openai_api_key = OPENAI_API_KEY))

    memory = ConversationBufferMemory(
    llm=llm, memory_key="chat_history", return_messages=True)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 1})

    return memory, retriever


def ask(query, session):
    query_completion = query + ". If an API response is provided as context and in the provided API response doesn't have this information or no context is provided, make sure that your response is 'I don't know'."
    response = session['generator'].invoke(query_completion)
    if "I'm sorry" in response['answer'] or "there is no information" in response['answer'] or "I don't know" in response['answer']:
        feed_vectorstore(query, session)
        response = session['generator'].invoke(query_completion)

    return response['answer']


def feed_vectorstore(query, session):
    response = api_response(query)

    text_splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=0)
    all_splits = text_splitter.split_text(response)
    docs = [Document(page_content=x) for x in all_splits]
    vectorstore = Chroma.from_documents(documents=docs, embedding=OpenAIEmbeddings(openai_api_key = OPENAI_API_KEY))

    llm = session['llm']

    memory = ConversationBufferMemory(
    llm=llm, memory_key="chat_history", return_messages=True)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 1})

    sessions[session['id']]['generator'] = ConversationalRetrievalChain.from_llm(
                llm=llm,
                retriever=retriever,
                memory=memory)


def set_openai_key():
    try:
        global OPENAI_API_KEY
        OPENAI_API_KEY = os.environ['OPENAI_API_KEY']
        is_api_key_valid(OPENAI_API_KEY)
    except:
        raise Exception("Error while trying to set OpenAI API Key variable")


def is_api_key_valid(key):
    try:
        client = OpenAI(api_key=key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "This is a test."}],
            max_tokens=5
        )
    except:
        raise Exception("The provided key is not valid.")
    else:
        return True


def define_api_pool(query):
    # Use LLM to decide if Kubernetes or StarlingX API pool should be used.
    client = OpenAI(api_key=OPENAI_API_KEY)

    prompt = f"Based on the following query you will choose between StarlingX APIs and Kubernetes APIs. You will not provide that specific API, only inform if it is a Starlingx or a Kubernetes API. Make sure that your response only contains the name StarlingX or the name Kubernetes and nothing else.\n\nUser query: {query}"

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": "You are an AI connected to a StarlingX system and based on the user query you will define which set of APIs is best to retrieve the necessary information to answer the question."}, {"role": "user", "content": prompt}]
    )

    print(f"###########{response.choices[0].message.content}")
    if response.choices[0].message.content.lower() == "kubernetes":
        return "Kubernetes"
    elif response.choices[0].message.content.lower() == "starlingx":
        return "StarlingX"
    else:
        raise ValueError('LLM could not define specific API pool.')


def api_response(query):
    pool = define_api_pool(query)
    if pool == "Kubernetes":
        bot = k8s_request(query, OPENAI_API_KEY)
        response = k8s_request.get_API_response(bot)
    elif pool == "StarlingX":
        bot = stx_request(query, OPENAI_API_KEY)
        response = stx_request.get_API_response(bot)
    else:
        raise ValueError('Error while trying to get API response.')

    return response
