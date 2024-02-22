import datetime
import json
import logging
import os
import sys
import uuid
from langchain.text_splitter import CharacterTextSplitter
from langchain.chains import ConversationalRetrievalChain
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.schema.document import Document
from langchain.memory.buffer import ConversationBufferMemory
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from api_request import k8s_request, wr_request
from openai import OpenAI
from constants import CLIENT_ERROR_MSG, LOG


def initiate_sessions():
    global sessions
    sessions = {}
    global node_list
    node_list = create_instance_list()


def delete_old_sessions():
    sessions_del = []
    for session, value in sessions.items():
        time_difference = datetime.datetime.now() - value['timestamp']
        if time_difference.total_seconds() > 60 * 60:
            sessions_del.append(session)

    for session in sessions_del:
        LOG.info(f"Deleting old session: {session}")
        del sessions[session]


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

    # Give the LLM date time context
    query = f"From now on you will use {datetime.datetime.now()} as current datetime for any datetime related user query"
    generator.invoke(query)

    # Add session to sessions map
    sessions[session_id] = {"generator": generator, "llm": llm, "id": session_id, "timestamp": datetime.datetime.now()}
    LOG.info(f"New session with ID: {session_id} initiated. Model: {model}, Temperature: {temperature}")

    # Delete old sessions
    delete_old_sessions()

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
    query_completion = query + ". If an API response is provided as context and in the provided API response doesn't have this information or no context is provided, make sure that your response is 'I don't know'. Unless the user explicitly ask for commands you will not provide any. Make sure to read the entire given context before giving your response."
    LOG.info(f"User query: {query}")
    response = session['generator'].invoke(query_completion)

    print(f'######{response}', file=sys.stderr)
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
        response = session['generator'].invoke(query)

    # if "I'm sorry" in response['answer'] or "there is no information" in response['answer'] or "I don't know" in response['answer']:
    #     feed_vectorstore(query, session)
    #     response = session['generator'].invoke(query_completion)
    LOG.info(f"Chatbot response: {response['answer']}")
    return response['answer']


def feed_vectorstore(query, session):
    response = api_response(query, session)

    if response is None:
        raise Exception('API response is null')

    print(f'API response: {response}', file=sys.stderr)

    # regex = r"(?=.*\binternal\b)(?=.*\bserver\b)(?=.*\berror\b).+"
    # if re.search(regex, response.lower()):
    #     response = CLIENT_ERROR_MSG

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


def define_api_pool(query, session):
    # Use LLM to decide if Kubernetes or Wind River API pool should be used.
    complete_query = f"Based on the following query you will choose between Wind River APIs and Kubernetes APIs. You will not provide that specific API, only inform if it is a Wind River or a Kubernetes API. Make sure that your response only contains the name Wind River or the name Kubernetes and nothing else.\n\nUser query: {query}"

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an AI connected to a Wind River system and based on the user query you will define which set of APIs is best to retrieve the necessary information to answer the question."),
        ("user", "{input}")
    ])

    output_parser = StrOutputParser()
    chain = prompt | session["llm"] | output_parser
    response = chain.invoke({"input": complete_query})

    print(f"###########{response}")
    if response.lower() == "kubernetes":
        return "Kubernetes"
    elif response.lower() == "wind river":
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
        bot = k8s_request(query, OPENAI_API_KEY, instance)
        response = k8s_request.get_API_response(bot)
    elif pool == "Wind River":
        bot = wr_request(query, OPENAI_API_KEY, instance)
        response = wr_request.get_API_response(bot)
    else:
        response = CLIENT_ERROR_MSG

    return response


def define_system(query):
    # Initiate OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)

    # Expected llm response format
    format_response = "name: <name>"

    # Create prompt
    system_prompt = f"You are a system that choses a node in a Distributed Cloud environment. Your job is to define which of the instances given in the context, the user is asking about."
    user_prompt = f"Make sure that only 1 is given in your response, the answer will never be more than 1 instance. If the user did not specified which instance he wants the information, you will provide the information of the instance that contains central cloud as type.\nYour answer will follow the format: {format_response}. Make sure this format is followed and nothing else is given in the your response."


    #Get completion
    completion = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            temperature=0.5,
            messages=[{"role": "system", "content": system_prompt},
                      {"role": "user", "content": f"List of available instances: {node_list}\nUser query: {query}\n\n{user_prompt}"}]
        )

    print(f'Completion: {completion.choices[0].message.content}', file=sys.stderr)
    name = completion.choices[0].message.content.split(":")[1].strip().replace(".", "")
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
    controller = {"name":"System Controller",
                  "URL":os.environ['OAM_IP'],
                  "type":"central cloud",
                  "token":os.environ['TOKEN']}
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
            "token": item["k8s_token"]
            }

            instance_list.append(new_subcloud)
    except:
        LOG.warning("No subcloud information was added to the list of instances")

    return instance_list
