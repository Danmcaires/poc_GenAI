import datetime
import json
import logging
import os
import sys
import uuid

import boto3
from langchain.chains import ConversationalRetrievalChain
from langchain.memory.buffer import ConversationBufferMemory
from langchain.schema.document import Document
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.embeddings.bedrock import BedrockEmbeddings
from langchain_community.llms import Bedrock
from langchain_community.vectorstores import Chroma

from api_request import k8s_request, wr_request
from constants import CLIENT_ERROR_MSG, LLAMA_PROMPT_END, LOG, MODEL


def initiate_sessions():
    global sessions
    sessions = {}
    global node_list
    node_list = create_instance_list()


def get_session(session_id):
    return sessions.get(session_id)


def new_session(model_id, temperature):
    client = boto3.client(service_name='bedrock-runtime')

    # Create vectorstore
    llm = Bedrock(client=client, model_id=model_id, model_kwargs={"temperature": 0})

    session_id = str(uuid.uuid4())
    memory, retriever = create_vectorstore(llm)
    # Create chat response generator
    generator = ConversationalRetrievalChain.from_llm(llm=llm, retriever=retriever, memory=memory)

    # Give the LLM date time context
    query = f"From now on you will use {datetime.datetime.now()} as current datetime for any datetime related user query"  # noqa: E501
    generator.invoke(query)

    # Create API connections
    k8s_bot = k8s_request(llm)
    wr_bot = wr_request(llm)

    # Add session to sessions map
    sessions[session_id] = {
        "generator": generator,
        "llm": llm,
        "id": session_id,
        "k8s_bot": k8s_bot,
        "wr_bot": wr_bot,
    }
    LOG.info(
        f"New session with ID: {session_id} initiated. Model: {model_id}, "
        f"Temperature: {temperature}"
    )
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
    vectorstore = Chroma.from_documents(documents=docs, embedding=BedrockEmbeddings())

    memory = ConversationBufferMemory(llm=llm, memory_key="chat_history", return_messages=True)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 1})

    return memory, retriever


def ask(query, session):
    query_completion = (
        query
        + ". If an API response is provided as context and in the provided API response doesn't have this information or no context is provided, make sure that your response is 'I don't know'. Unless the user explicitly ask for commands you will not provide any. Make sure to read the entire given context before giving your response."  # noqa: E501
    )
    LOG.info(f"User query: {query}")
    response = session['generator'].invoke(query_completion)
    chat_response = response['answer']

    print(f'######{chat_response}', file=sys.stderr)

    client = boto3.client(service_name='bedrock-runtime')
    prompt_status = f"<s>[INST] <<SYS>>Your task is to understand the context of a text. Look for clues indicating whether the text provides information about a subject. If you come across phrases such as 'I'm sorry', 'no context', 'no information', or 'I don't know', it likely means there isn't enough information available. Similarly, if the text mentions not having access to the information, or if it offers directives without the user requesting them explicitly, the context is negative. Based on the following text, check if the general context indicates that there is information about what is being asked or not. Make sure to answer only the words 'positive' if there is information, or 'negative' if there isn't. Don't elaborate in your answer simply say 'positive' or 'negative'.<</SYS>> </s> User query:{query}\nResponse: {response} [/INST]"  # noqa: E501

    body = json.dumps(
        {
            "prompt": prompt_status,
            "temperature": 0.1,
            "top_p": 0.9,
        }
    )

    modelId = MODEL
    accept = 'application/json'
    contentType = 'application/json'

    response = client.invoke_model(
        body=body, modelId=modelId, accept=accept, contentType=contentType
    )
    response_body = json.loads(response.get('body').read())
    sentiment_analisys = response_body['generation']
    print(f"sentiment: {sentiment_analisys}", file=sys.stderr)

    if 'negative' in sentiment_analisys.lower():
        LOG.info("Negative response from LLM")
        feed_vectorstore(query, session)
        response = session['generator'].invoke(query)
        chat_response = response['answer']

    LOG.info(f"Chatbot response: {chat_response}")
    return chat_response


def feed_vectorstore(query, session):
    response = api_response(query, session)

    if response is None:
        raise Exception('API response is null')

    print(f'API response: {response}', file=sys.stderr)

    text_splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=0)
    all_splits = text_splitter.split_text(response)
    docs = [Document(page_content=x) for x in all_splits]
    vectorstore = Chroma.from_documents(documents=docs, embedding=BedrockEmbeddings())

    llm = session['llm']

    memory = ConversationBufferMemory(llm=llm, memory_key="chat_history", return_messages=True)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 1})

    sessions[session['id']]['generator'] = ConversationalRetrievalChain.from_llm(
        llm=llm, retriever=retriever, memory=memory
    )


def is_api_key_valid():
    create_logger()
    try:
        client = boto3.client(service_name='bedrock')
        _ = client.list_foundation_models()
    except Exception:
        raise Exception("The provided key is not valid.")
    return True


def define_api_pool(query, session):
    # Use LLM to decide if Kubernetes or Wind River API pool should be used.
    system_prompt = f"You are an AI assistant connected to a Wind River system and based on the user query you will define which set of APIs is best to retrieve the necessary information to answer the question. Based on the following query you will choose between Wind River APIs and Kubernetes APIs. You will not provide that specific API, only inform if it is a Wind River or a Kubernetes API. Your answer should not contain the word API. {LLAMA_PROMPT_END}"  # noqa: E501,W605
    prompt = f"<s>[INST] <<SYS>>{system_prompt}<</SYS>> Example: 'List my active alarms. [\INST] Wind River' </s> [INST] User query:{query} [/INST]"  # noqa: E501,W605
    response = session["llm"].invoke(prompt).lower()

    print(f"###########{response}", file=sys.stderr)
    if "kubernetes" in response:
        return "Kubernetes"
    elif "wind river" in response:
        return "Wind River"
    else:
        return "Undefined"


def api_response(query, session):
    instance = define_system(query)
    print(f'Query being made to {instance["name"]}', file=sys.stderr)
    LOG.info(f'Query being made to {instance["name"]}')

    print('Defining API pool', file=sys.stderr)
    LOG.info('Defining API pool')
    pool = define_api_pool(query, session)
    print(f'LLM defined {pool} as the API subject', file=sys.stderr)
    LOG.info(f'LLM defined {pool} as the API subject')
    if pool == "Kubernetes":
        response = session["k8s_bot"].get_API_response(user_query=query, instance=instance)
    elif pool == "Wind River":
        response = session["wr_bot"].get_API_response(user_query=query, instance=instance)
    else:
        response = CLIENT_ERROR_MSG

    return response


def define_system(query):
    # Initiate Boto3
    client = boto3.client(service_name='bedrock-runtime')

    format_response = "name: <name>"

    # Create prompt
    prompt_status = f"<s>[INST] <<SYS>>You are a system that choses a node in a Distributed Cloud environment. Your job is to define which of the instances given in the context, the user is asking about. Make sure that only 1 is given in your response, the answer will never be more than 1 instance. Your answer will follow the format: {format_response}. Make sure this format is followed and nothing else is given in the your response.<</SYS>>List of available instances: {node_list}\nUser query: {query}\nYour answer will only have what the format dictates, don't add any other text. If the query did not informed any instance name, you will answer 'name: System Controller'. You will not choose a subcloud that isn't explicitly asked about.[/INST]"  # noqa: E501

    # Create request body
    body = json.dumps(
        {
            "prompt": prompt_status,
            "temperature": 0.1,
            "top_p": 0.9,
        }
    )

    modelId = MODEL
    accept = 'application/json'
    contentType = 'application/json'

    # Get completion
    response = client.invoke_model(
        body=body, modelId=modelId, accept=accept, contentType=contentType
    )

    response_body = json.loads(response.get('body').read())
    print(f'Completion: {response_body["generation"]}', file=sys.stderr)
    name = response_body['generation'].split(":")[1].strip().replace(".", "")

    print(f'Result after normalization: {name}', file=sys.stderr)
    node_dict = {}

    # Iterate over each key-value pair
    for node in node_list:
        if node['name'] == name:
            node_dict = node
    return node_dict


def create_instance_list():
    # Create list
    instance_list = []

    # Add the system controller as first item on the list
    controller = {
        "name": "System Controller",
        "URL": os.environ['OAM_IP'],
        "type": "central cloud",
        "token": os.environ['TOKEN'],
    }
    instance_list.append(controller)

    try:
        # Load subclouds information
        with open("src/subclouds.json", "r") as f:
            data = json.load(f)

        for item in data:
            new_subcloud = {
                "name": item["name"],
                "URL": item["URL"],
                "type": "subcloud",
                "token": item["k8s_token"],
            }

            instance_list.append(new_subcloud)
    except:
        LOG.warning("No subcloud information was added to the list of instances")

    return instance_list
