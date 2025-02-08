import os
import openai
import joblib
from dotenv import load_dotenv
from django.shortcuts import render, redirect
from django.conf import settings
from django.http import HttpResponse
from django.http import JsonResponse
from django.contrib.auth import authenticate, login
from .models import PredictionHistory
from .models import pessoa
from django.contrib import messages
import requests
load_dotenv()  # take environment variables from .env.

# Configurar a API key da OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/v1/chat/completions")

def index(request):
    if request.method == 'POST':
        usuario = request.POST.get('username')
        senha = request.POST.get('password')

        # Primeiro, tenta autenticar com o sistema padrão do Django
        user = authenticate(username=usuario, password=senha)
        if user is not None:
            login(request, user)
            request.session['username'] = usuario
            request.session['password'] = senha
            request.session['usernamefull'] = user.get_full_name()
            return redirect('sentiment_gpt')  # Usuário Django sempre vai para sentiment

        # Se falhar, tenta autenticar no modelo `pessoa`
        try:
            usuario_pessoa = pessoa.objects.get(usuario=usuario, senha=senha)
            if usuario_pessoa.ativo:  # Verifica se o usuário está ativo
                request.session['username'] = usuario_pessoa.usuario
                request.session['usernamefull'] = usuario_pessoa.nome
                
                # **Lógica de Redirecionamento Baseada nas Permissões**
                if usuario_pessoa.permissao_sentiment_gpt:
                    return redirect('sentiment_gpt')  # GPT
                elif usuario_pessoa.permissao_sentiment_deepseek:
                    return redirect('sentiment_deepseek')  # DeepSeek
                elif usuario_pessoa.permissao_sentiment_ml:
                    return redirect('sentiment_ml')  # Machine Learning
                else:
                    messages.error(request, "Você não tem permissão para acessar o sistema.")
                    return redirect('index')

            else:
                messages.error(request, "Usuário inativo. Contate o administrador.")

        except pessoa.DoesNotExist:
            messages.error(request, "Usuário ou senha incorretos.")

    return render(request, 'sentiment/login.html')

    
    
def classify_sentiment_gpt(content, model="gpt-4o-mini"):
    """
    Usa o modelo OpenAI Chat para classificar o sentimento de um texto.
    Retorna apenas 'pos' ou 'neg'.
    """
    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Classify the sentiment of the following text as 'pos' for positive or 'neg' for negative."
                        f" Respond with only 'pos' or 'neg' and no additional text.\n\n"
                        f"Text: \"{content}\""
                    ),
                }
            ],
        )
        result = response["choices"][0]["message"]["content"].strip().lower()
        return result if result in ["pos", "neg"] else "invalid"
    except Exception as e:
        print(f"Error processing text: {content}\n{e}")
        return None
    
def classify_sentiment_deepseek(content, model="deepseek-chat"):
    """
    Usa a API da DeepSeek para classificar o sentimento de um texto.
    Retorna apenas 'pos' ou 'neg'.
    """
    try:
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Classify the sentiment of the following text as 'pos' for positive or 'neg' for negative."
                        " Respond with only 'pos' or 'neg' and no additional text.\n\n"
                        f"Text: \"{content}\""
                    ),
                }
            ],
            "temperature": 0.2,
            "max_tokens": 10
        }
        
        response = requests.post(DEEPSEEK_API_URL, json=payload, headers=headers)
        response_data = response.json()

        if "choices" in response_data:
            result = response_data["choices"][0]["message"]["content"].strip().lower()
            return result if result in ["pos", "neg"] else "invalid"
        
        print(f"DeepSeek API Error: {response_data}")
        return None

    except Exception as e:
        print(f"Error processing text: {content}\n{e}")
        return None
        
def cadastro(request):
    if request.method == 'POST':
        # Captura os dados do formulário
        nome = request.POST.get('nome')
        usuario = request.POST.get('usuario')
        senha = request.POST.get('senha')
        email = request.POST.get('email')
        celular = request.POST.get('celular')
        funcao = request.POST.get('funcao')
        nascimento = request.POST.get('nascimento')
        
        # Verifica se o e-mail já existe no banco de dados
        if pessoa.objects.filter(email=email).exists():
            messages.error(request, "E-mail já cadastrado. Utilize outro e-mail.")
            return redirect('cadastro')  # Redireciona para a página de cadastro
        
        # Cria um novo registro no modelo 'pessoa'
        nova_pessoa = pessoa(
            nome=nome,
            usuario=usuario,
            senha=senha,
            email=email,
            celular=celular,
            funcao=funcao,
            nascimento=nascimento,
        )
        nova_pessoa.save()
        
        # Adiciona uma mensagem de sucesso
        messages.success(request, f'Usuário {nome} cadastrado com sucesso!')
        
        # Redireciona para uma página de sucesso (pode ser alterado)
        return redirect('index')  # Substitua 'index' pelo nome correto da sua URL de destino

    # Renderiza o formulário de cadastro
    return render(request, 'sentiment/cadastro.html')
def sentiment_deepseek(request):
    usuario = request.session.get('username', None)

    if not usuario:
        messages.error(request, "Você precisa estar logado para acessar esta página.")
        return redirect('index')

    try:
        usuario_pessoa = pessoa.objects.get(usuario=usuario)
        if not usuario_pessoa.permissao_sentiment_deepseek:  # ✅ USANDO O CAMPO CORRETO
            messages.error(request, "Você não tem permissão para acessar esta página.")
            return redirect('index')
    except pessoa.DoesNotExist:
        messages.error(request, "Usuário não encontrado.")
        return redirect('index')

    return render(request, 'sentiment/sentiment_deepseek.html')

def sentiment_gpt(request):
    usuario = request.session.get('username', None)

    if not usuario:
        messages.error(request, "Você precisa estar logado para acessar esta página.")
        return redirect('index')

    try:
        usuario_pessoa = pessoa.objects.get(usuario=usuario)
        if not usuario_pessoa.permissao_sentiment_gpt:  # ✅ USANDO O CAMPO CORRETO
            messages.error(request, "Você não tem permissão para acessar esta página.")
            return redirect('index')
    except pessoa.DoesNotExist:
        messages.error(request, "Usuário não encontrado.")
        return redirect('index')

    return render(request, 'sentiment/sentiment_gpt.html')

def sentiment_ml(request):
    usuario = request.session.get('username', None)

    if not usuario:
        messages.error(request, "Você precisa estar logado para acessar esta página.")
        return redirect('index')

    try:
        usuario_pessoa = pessoa.objects.get(usuario=usuario)
        if not usuario_pessoa.permissao_sentiment_ml:  # ✅ USANDO O CAMPO CORRETO
            messages.error(request, "Você não tem permissão para acessar esta página.")
            return redirect('index')
    except pessoa.DoesNotExist:
        messages.error(request, "Usuário não encontrado.")
        return redirect('index')

    return render(request, 'sentiment/sentiment_ml.html')


def sobre(request):
    return render(request, 'sentiment/sobre.html')

def classify_sentiment_gpt_view(request):
    """
    Chama o modelo GPT para classificar sentimento via API.
    """
    if request.method == 'POST':
        text = request.POST.get('text', '')

        # Corrigindo chamada da função correta
        sentiment = classify_sentiment_gpt(text)  # Correto: Chamando a função de processamento

        if sentiment is None:
            return JsonResponse({'error': 'Erro ao processar sentimento com GPT'}, status=500)

        sentiment = "NEGATIVO" if sentiment == "neg" else "POSITIVO" if sentiment == "pos" else "INVÁLIDO"

        # Verifica usuário autenticado
        usuario_pessoa = None
        if 'username' in request.session and not request.user.is_authenticated:
            try:
                usuario_pessoa = pessoa.objects.get(usuario=request.session['username'])
            except pessoa.DoesNotExist:
                usuario_pessoa = None

        # Salva no histórico
        PredictionHistory.objects.create(
            text=text, 
            sentiment=sentiment, 
            source='sentiment-gpt', 
            user=request.user if request.user.is_authenticated else None, 
            usuario_pessoa=usuario_pessoa
        )

        return JsonResponse({'text': text, 'sentiment': sentiment})
    
    return JsonResponse({'error': 'Invalid request method'}, status=400)

def classify_sentiment_deepseek_view(request):
    """
    Chama o modelo DeepSeek para classificar sentimento via API.
    """
    if request.method == 'POST':
        text = request.POST.get('text', '')

        sentiment = classify_sentiment_deepseek(text)
        if sentiment is None:
            return JsonResponse({'error': 'Erro ao processar sentimento com DeepSeek'}, status=500)

        sentiment = "NEGATIVO" if sentiment == "neg" else "POSITIVO" if sentiment == "pos" else "INVÁLIDO"

        # Verifica usuário autenticado
        usuario_pessoa = None
        if 'username' in request.session and not request.user.is_authenticated:
            try:
                usuario_pessoa = pessoa.objects.get(usuario=request.session['username'])
            except pessoa.DoesNotExist:
                usuario_pessoa = None

        # Salva no histórico
        PredictionHistory.objects.create(
            text=text, 
            sentiment=sentiment, 
            source='sentiment-deepseek', 
            user=request.user if request.user.is_authenticated else None, 
            usuario_pessoa=usuario_pessoa
        )

        return JsonResponse({'text': text, 'sentiment': sentiment})
    
    return JsonResponse({'error': 'Invalid request method'}, status=400)

### Modelos de classificação por ML
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODEL_DIR = os.path.join(PROJECT_DIR, 'machine_learning', 'models')

# Caminhos absolutos para os modelos
CLASSIFIER_PATH = os.path.join(MODEL_DIR, 'sentiment_classifier_model.pkl')
VECTORIZER_PATH = os.path.join(MODEL_DIR, 'tfidf_vectorizer.pkl')
LABEL_ENCODER_PATH = os.path.join(MODEL_DIR, 'label_encoder.pkl')

classifier = joblib.load(CLASSIFIER_PATH)
vectorizer = joblib.load(VECTORIZER_PATH)
label_encoder = joblib.load(LABEL_ENCODER_PATH)

def sentiment_ml(request):
    usuario = request.session.get('username', None)

    if not usuario:
        messages.error(request, "Você precisa estar logado para acessar esta página.")
        return redirect('index')

    try:
        usuario_pessoa = pessoa.objects.get(usuario=usuario)
        if not usuario_pessoa.permissao_sentiment_ml:
            messages.error(request, "Você não tem permissão para acessar esta página.")
            return redirect('index')
    except pessoa.DoesNotExist:
        messages.error(request, "Usuário não encontrado.")
        return redirect('index')

    return render(request, 'sentiment/sentiment_ml.html')


def predict_sentiment(request):
    # Captura o texto enviado via GET
    new_text = request.GET.get('text', '')
    if not new_text:
        return JsonResponse({'error': 'Texto não fornecido'}, status=400)

    try:
        # Converte o texto para o formato necessário pelo vetor TF-IDF
        new_text_tfidf = vectorizer.transform([new_text])
        # Realiza a previsão com o modelo
        predicted_label_encoded = classifier.predict(new_text_tfidf)
        # Tenta converter a previsão de volta para o rótulo original
        try:
            predicted_label = label_encoder.inverse_transform(predicted_label_encoded)
        except ValueError as e:
            return JsonResponse({'error': f'Rótulo desconhecido detectado: {str(e)}'}, status=400)

        # Determina o usuário autenticado (User ou pessoa)
        usuario_pessoa = None
        if 'username' in request.session and not request.user.is_authenticated:
            try:
                usuario_pessoa = pessoa.objects.get(usuario=request.session['username'])
            except pessoa.DoesNotExist:
                usuario_pessoa = None

        # Criação do registro no histórico de previsões
        PredictionHistory.objects.create(
            text=new_text,
            sentiment=predicted_label[0],
            source='sentiment_ml',
            user=request.user if request.user.is_authenticated else None,
            usuario_pessoa=usuario_pessoa  # Associa usuário da tabela pessoa, se existir
        )

        # Retorna o resultado como JSON
        return JsonResponse({
            'texto': new_text,
            'sentimento_previsto': predicted_label[0]
        })
    except Exception as e:
        return JsonResponse({'error': f'Erro ao processar o texto: {str(e)}'}, status=500)


def history(request):
    predictions = PredictionHistory.objects.all().order_by('-created_at')  # Recupera o histórico
    return render(request, 'sentiment/historico.html', {'predictions': predictions})