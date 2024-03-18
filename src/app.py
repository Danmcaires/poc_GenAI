import datetime
import logging
import os
import sys
import uuid
from langchain.text_splitter import CharacterTextSplitter
from langchain.chains import ConversationalRetrievalChain
from langchain_community.vectorstores import Chroma
from langchain.schema.document import Document
from langchain.memory.buffer import ConversationBufferMemory
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from api_request import openstack_request
from openai import OpenAI
from constants import LOG


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
    memory, retriever = create_vectorstore(llm)
    # Create chat response generator
    generator = ConversationalRetrievalChain.from_llm(
                llm=llm,
                retriever=retriever,
                memory=memory)
    bot = openstack_request(OPENAI_API_KEY)

    # Give the LLM date time context
    query = f"From now on you will use {datetime.datetime.now()} as current datetime for any datetime related user query"
    generator.invoke(query)

    # Add session to sessions map
    sessions[session_id] = {"generator": generator, "llm": llm, "id": session_id, "bot": bot}
    LOG.info(f"New session with ID: {session_id} initiated. Model: {model}, Temperature: {temperature}")
    return sessions[session_id]


def create_logger():
    # Create logger
    LOG = logging.getLogger("chatbot")
    LOG.setLevel(logging.INFO)

    # Create a file handler and set its level to INFO
    file_handler = logging.FileHandler('chatbot.log')
    file_handler.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)

    # Add the file handler to the logger
    LOG.addHandler(file_handler)
    LOG.info("Chatbot logger initiated.")


def create_vectorstore(llm):
    # Create Chroma vector store
    data_start = "start vectorstore"
    docs = [Document(page_content=x) for x in data_start]
    vectorstore = Chroma.from_documents(documents=docs, embedding=OpenAIEmbeddings(openai_api_key = OPENAI_API_KEY))

    memory = ConversationBufferMemory(
    llm=llm, memory_key="chat_history", return_messages=True)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 1})

    return memory, retriever


def ask(query, session):
    query_completion = query + ". If the API response lacks the necessary information or if no context is provided, respond with 'I don't know'. Only provide commands if explicitly requested by the user. Ensure a comprehensive understanding of the given context before generating a response."
    LOG.info(f"User query: {query}")
    response = session['generator'].invoke(query_completion)

    client = OpenAI(api_key=OPENAI_API_KEY)
    prompt_status = client.chat.completions.create(model='gpt-3.5-turbo',
                                                   messages=[{"role": "system",
                                                              "content": "Your task is to understand the context of a text. Look for clues indicating whether the text provides information about a subject. If you come across phrases such as 'I'm sorry', 'no context', 'no information', or 'I don't know', it likely means there isn't enough information available. Similarly, if the text mentions not having access to the information, or if it offers directives without the user requesting them explicitly, the context is negative."},
                                                             {"role": "user",
                                                              "content": f"Based on the following text, check if the general context indicates that there is information about what is being asked or not. Make sure to answer only the words 'positive' if there is information, or 'negative' if there isn't. Don't answer nothing besides it.\nUser query {query}\nResponse: {response['answer']}"}])
    print(f'prompt status: {prompt_status.choices[0].message.content}', file=sys.stderr)
    if 'negative' in prompt_status.choices[0].message.content.lower():
        LOG.info("Negative response from LLM")
        feed_vectorstore(query, session)
        response = session['generator'].invoke(f"{query}. If the provided context indicates an error during the API response retrieval, relay this information in your response.")

    LOG.info(f"Chatbot response: {response['answer']}")
    return response['answer']


def feed_vectorstore(query, session):
    response = session["bot"].get_API_response(query)

    if response is None:
        raise Exception('API response is null')

    print(f'API response: {response}', file=sys.stderr)

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
    create_logger()
    try:
        global OPENAI_API_KEY
        OPENAI_API_KEY = os.environ['OPENAI_API_KEY']
        is_api_key_valid(OPENAI_API_KEY)
    except Exception:
        raise Exception("Error while trying to set OpenAI API Key variable")
    LOG.info("API key configured")
    return True


def is_api_key_valid(key):
    try:
        client = OpenAI(api_key=key)
        _ = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "This is a test."}],
            max_tokens=5
        )
    except Exception:
        raise Exception("The provided key is not valid.")
    return True
