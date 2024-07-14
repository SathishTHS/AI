from django.shortcuts import render, redirect, HttpResponse
from django.http import JsonResponse
from django.contrib import messages
from django.urls import path

from langchain_community.document_loaders import PyPDFLoader
import chromadb
from chromadb.utils.embedding_functions import GoogleGenerativeAiEmbeddingFunction, OllamaEmbeddingFunction, SentenceTransformerEmbeddingFunction
import os, json, docx2txt

from .forms import FileForm
from .models import file_model, conversation_history
from . text_split import splitter
#from . gemini_api import genai

import google.generativeai as genai

from celery import shared_task
from django.core.files import File
from django.core.files.storage import FileSystemStorage

from dotenv import load_dotenv
load_dotenv()

# Create your views here.

#genai=genai()
splitter = splitter()

client = chromadb.Client()

# google_embedding_model_name = "models/text-embedding-004"
# google_embedding_model_name = "models/embedding-001"

sentence_embedding = SentenceTransformerEmbeddingFunction(model_name='all-mpnet-base-v2')
google_embedding = GoogleGenerativeAiEmbeddingFunction(api_key=os.environ['GEMINI_API_KEY'])
ollama_embedding = OllamaEmbeddingFunction(url="http://localhost:11434/api/embeddings", model_name="llama2")

collection = client.get_or_create_collection(name='fileEmbeddingCollections', embedding_function=sentence_embedding)

ids=[]
documents =[]

histories = []
chat_doc_dict ={}

genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
modelName = 'gemini-1.5-flash'
generation_config = genai.types.GenerationConfig(
    top_k=10,
    top_p=1.0,
    temperature=1.0,
    max_output_tokens=100,
    response_mime_type='text/plain',
)
model = genai.GenerativeModel(modelName, generation_config=generation_config)


def to_markdown(text):
    return text.replace('**','')

def home(request):
    # return HttpResponse('Welcome')
    files = FileForm()
    files_list = file_model.objects.all()

    if files_list:
        session = request.session

        global collection, ids, documents

        if request.method == 'POST':
            user_prompt = request.POST['question']

            if ids and documents:
                try:
                    n_results = 5
                    embedding_result = collection.query(query_texts=[user_prompt], n_results=n_results)

                    rel_text = embedding_result['documents'][0][0]
                    messages.success(request, 'Related Text %s' % rel_text)

                    if rel_text:
                        prompt = f"""Summarize the context: {rel_text},
                            based on the question: {user_prompt} in 2 to 3 lines. 
                            Answer the user's question only using the 
                            context information in a gentle manner"""

                        # retrieve or starting the conversation

                        '''chat_session = model.start_chat()
                        chat_session.'''
                        conversation = session.get('conversation', [])  

                        conversation.append({'role': 'user', 'parts': [prompt]})

                        #adding entire messages inside the generate content to get the multi turn conversation
                        model_response = model.generate_content(conversation).text
                        response = to_markdown(model_response)
                        conversation.append({'role': 'model', 'parts': [response]})

                        # Update session with conversation
                        session['conversation'] = conversation  
                        session.save()

                        if messages:
                            last_message = conversation[-1]  
                        else:
                            None
                        
                        chat_history = conversation_history.objects.create(question=user_prompt, response=response)
                        if chat_history not in histories:
                            histories.append(chat_history)

                        chat_doc_dict = {'questions': user_prompt, 'responses':model_response}
                        
                        #'conversations': conversation
                        context = {'chat_doc_dict':chat_doc_dict, 'last_message': last_message, 'forms': files, 'files_list': files_list}
                        return render(request, 'chat_ai.html', context)

                    '''context = {'forms':files, 'files_list':files_list}
                    return render(request, 'chat_ai.html', context)'''

                except Exception as e:
                    return HttpResponse(str(e))
            

            else:
                # retrieve or starting the conversation
                conversation = session.get('conversation', [])  
                conversation.append({'role': 'user', 'parts': [user_prompt]})

                #adding entire messages inside the generate content to get the multi turn conversation
                model_response = model.generate_content(conversation).text
                response = to_markdown(model_response)
                conversation.append({'role': 'model', 'parts': [response]})

                # Update session with conversation
                session['conversation'] = conversation  
                session.save()

                if messages:
                    last_message = conversation[-1]  
                else:
                    None

                chat_history = conversation_history.objects.create(question=user_prompt, response=response)
                if chat_history not in histories:
                    histories.append(chat_history)

                context = {'conversations': conversation, 'last_message': last_message, 'forms': files, 'files_list': files_list}
                return render(request, 'chat_ai.html', context)
        
        context = {'forms':files, 'files_list':files_list}
        return render(request, 'chat_ai.html', context)

    else:
        context = {'forms':files}
        return render(request, 'chat_ai.html', context)
    
    
def upload_file(request):
    if request.method=='POST':
        files = FileForm(request.POST, request.FILES)
        if files.is_valid():
            file = request.FILES.get('form_file')
            
            # to check the file already exist in models.py(sql db) or not
            file_exist = file_model.objects.filter(file_detail=file).exists()
            if file_exist:
                messages.error(request, 'The file %s is already exists...'% file)
            else:
                file_model.objects.create(file_detail=file)
                messages.success(request, 'File uploaded successfully')

            return redirect('ConAI:home')


def delete_file(request, id):
    file = file_model.objects.get(id=id)
    file.delete()

    os.remove(file.file_detail.path)
    messages.success(request, 'File deleted successfully')
    return redirect('ConAI:home')


def select_file(request, id):
   if request.method=='GET':
        try:
            uploaded_file = file_model.objects.get(id=id)
            # to get the file path using django-storages
            file_path = uploaded_file.file_detail.path

            global collection
            chunk_dict = {} 

            if file_path.endswith('.pdf'):
                pdf_file = PyPDFLoader(file_path)
                pages_in_pdf = pdf_file.load()
                
                for page in pages_in_pdf:
                    content_in_page = page.page_content
                    chunks = splitter.rec_text_splitter.split_text(content_in_page)
                    for chunk in chunks:
                        documents.append(chunk)

                        doc_size = len(documents)
                        for i in range(doc_size):
                            id = f'id{i+1}'
                            if id not in ids:
                                ids.append(id)
                            
                                chunk_dict[id]={'Text':chunk}

            elif file_path.endswith('.docx'):
                content_in_page = docx2txt.process(file_path)
                chunks = splitter.rec_text_splitter.split_text(content_in_page)
                for chunk in chunks:
                    documents.append(chunk)

                    doc_size = len(documents)
                    for i in range(doc_size):
                        id = f'id{i+1}'
                        if id not in ids:
                            ids.append(id)
                        
                            chunk_dict[id]={'Text':chunk}
        
            if chunk_dict:
                if ids and documents:
                    collection.upsert(ids=ids, documents=documents)

                text_chunks = []
                for chunk_id, content in chunk_dict.items():
                    text_chunks.append({'id': chunk_id, 'text': content['Text']})
                
                if text_chunks:
                    chunk_size = len(documents)
                    messages.success(request, 'File selected successfully, extracted %s chunks' % chunk_size)

                #context = {'text_chunks': text_chunks, 'ids': ids}
                #return render(request, 'chat_ai.html', context)
                return redirect('ConAI:home')   
            
        except Exception as e:
            return str(e)
    


def clear_session(request):
    global collection, ids, chat_doc_dict
    session = request.session
    session.clear()
    if ids:
        collection.delete(ids=ids)
    documents = []
    ids = []
    chat_doc_dict ={}
    messages.success(request, 'Session cleared')
    return redirect('ConAI:home')


def chat_hsitory(request):
    latest_questions = conversation_history.objects.order_by('-created_at')[:5]
    return render(request, 'chat_history.html', {"latest_questions":latest_questions})


def clear_chat_history(request):
    # need to use bracket for delete() all the history from db
    conversation_history.objects.all().delete()
    return redirect('ConAI:chat_hsitory')


'''def ai_converse(request):
    session = request.session
    if request.method=='POST':
        user_prompt = request.POST['question']

        messages = session.get('conversation', [])

        messages.append({'role': 'user', 'parts': [user_prompt]})
        model_response = model.generate_content(messages).text
        response = to_markdown(model_response)
        messages.append({'role': 'model', 'parts': [response]})
        
        session['conversation'] = messages
        session.save()

        conversations = messages

        #return render(request, 'chat_ai.html', {'conversations':messages})
        return redirect('ConAI:home')
'''