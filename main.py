from langchain.chains import ConversationalRetrievalChain, LLMChain
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import AIMessage, HumanMessage
from langchain.schema.document import Document
from langchain.memory import ConversationSummaryMemory
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from api_request import k8s_request
import json

from openai import OpenAI

def main():

    OPENAI_API_KEY = get_openai_key()

    llm = ChatOpenAI(openai_api_key=OPENAI_API_KEY)

    # First chatbot question
    print("What would like to know?")
    query = input()
    bot = k8s_request(query, OPENAI_API_KEY)
    response = k8s_request.get_API_response(bot)
    with open ("response.txt", "w") as f:
        f.write(f"API response = {response}")
    #response = str(RESPONSE)
    loader = TextLoader("response.txt")
    documents = loader.load()
    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
    docs = text_splitter.split_documents(documents)

    # Create doc from response
    #doc = Document(page_content=documents, metadata={})

    # Create Chroma vector store
    #text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=0)
    #all_splits = text_splitter.split_documents(doc.page_content)
    vectorstore = Chroma.from_documents(documents=docs, embedding=OpenAIEmbeddings(openai_api_key = OPENAI_API_KEY))

    memory = ConversationSummaryMemory(
    llm=llm, memory_key="chat_history", return_messages=True)

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are chatbot that provides information about a StarlingX system. Your answer is a succint paragraph answering exactly what the user asked. Make sure to use the chat history to provide your answer, like a conversation. Make sure to answer in the user query language. If you don't know the answer type 'I don't know', don't try to come up with a answer that is possibly wrong."),
        ("user", "{input}")
    ])

    output_parser = StrOutputParser()
    question_generator_chain = LLMChain(llm=llm, prompt=prompt)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 1})

    # Answering first question
    generator = ConversationalRetrievalChain.from_llm(
                llm=llm,
                retriever=retriever,
                memory=memory)



    repeat = "yes"

    while repeat == "yes":
        #ask(query)
        response = generator.invoke(query)
        print(response['answer'])
        print("Do you have more questions?(yes/no)")
        repeat = input().lower()
        if repeat == "yes":
            print("What would like to know?")
            query = input()

    print("Thank you for using the StarlingX chatbot!")


# def ask(chain):
#     print("What would like to know?")
#     query = input()
#     print(chain.invoke(
#         {
#             "chat_history": [
#                 HumanMessage(content="Retrieve information about the pods in my system"),
#                 AIMessage(content= RESPONSE),
#             ],
#             "input": f"{query}"}))


def get_openai_key():
    print("Hello! This is the chatbot for your StarlingX cluster.")
    print("To procced, you need to provide an OpenAI API key:")
    valid_key = False

    while valid_key == False:
        api_key = input()
        #valid_key = is_api_key_valid(api_key)
        #if valid_key == False:
        #    print("The provided key is not valid."
        #          "Please provide a valid OpenAI API key:")
        valid_key = True

    return api_key


def is_api_key_valid(key):
    try:
        client = OpenAI(api_key=key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "This is a test."}],
            max_tokens=5
        )
    except:
        return False
    else:
        return True


if __name__ == "__main__":
    main()