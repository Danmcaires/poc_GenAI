from langchain.chains import ConversationalRetrievalChain
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain.schema.document import Document
from langchain.memory.buffer import ConversationBufferMemory
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.text_splitter import CharacterTextSplitter
from api_request import k8s_request
from openai import OpenAI
import os

### To locally test the app ,uncomment this function and the last two lines of this file
# def main():
#     set_openai_key()
    #     initiate_generator()
#     query = input()
#     ask(query)


def initiate_generator():
    # Initiate LLM
    llm = ChatOpenAI(
        model_name="gpt-3.5-turbo",
        temperature=0,
        openai_api_key=OPENAI_API_KEY)
    # Create vectorstore
    memory, retriever = create_vectorstore(llm)
    # Create chat response generator
    global generator
    generator = ConversationalRetrievalChain.from_llm(
                llm=llm,
                retriever=retriever,
                memory=memory)


def create_vectorstore(llm):
    # Create Chroma vector store
    data_start = "start vectorstore"
    docs = [Document(page_content=x) for x in data_start]
    vectorstore = Chroma.from_documents(documents=docs, embedding=OpenAIEmbeddings(openai_api_key = OPENAI_API_KEY))

    memory = ConversationBufferMemory(
    llm=llm, memory_key="chat_history", return_messages=True)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 1})

    return memory, retriever


def ask(query):
    query += ". If an API response is provided as context and in the provided API response doesn't have this information or no context is provided, make sure that your response is 'I don't know'."
    response = generator.invoke(query)
    if "I'm sorry" in response['answer'] or "there is no information" in response['answer'] or response['answer'] == "I don't know":
        feed_vectorstore(query)
        response = generator.invoke(query)

    print(response['answer'])
    return response['answer']
    ## Uncommnet to test locally
    # query = input().lower()


def feed_vectorstore(query):
    llm = ChatOpenAI(openai_api_key=OPENAI_API_KEY)
    bot = k8s_request(query, OPENAI_API_KEY)
    response = k8s_request.get_API_response(bot)

    text_splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=0)
    all_splits = text_splitter.split_text(response)
    docs = [Document(page_content=x) for x in all_splits]
    vectorstore = Chroma.from_documents(documents=docs, embedding=OpenAIEmbeddings(openai_api_key = OPENAI_API_KEY))

    memory = ConversationBufferMemory(
    llm=llm, memory_key="chat_history", return_messages=True)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 1})

    global generator
    generator = ConversationalRetrievalChain.from_llm(
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


# if __name__ == "__main__":
#     main()