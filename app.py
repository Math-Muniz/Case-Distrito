# --- Imports Básicos ---
import os
import requests
import json
from dotenv import load_dotenv
from typing import Annotated

# --- Import do Streamlit ---
import streamlit as st

# --- Imports do LangChain / LangGraph ---
from langchain.tools import tool
from langgraph.graph.message import add_messages
from langgraph.graph import START, END, StateGraph
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import ToolNode
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

# --- Carregamento de Variáveis de Ambiente ---
load_dotenv()
SPOON_API_KEY = os.getenv("SPOON_API_KEY") 
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")

# --- Definição da Ferramenta ---
@tool
def buscador_de_receitas(ingredientes: str) -> str:
    """
    Caso o input esteja em PT-BR, tranforme em EN-US (ex: 'tomatoes,cheese,eggs') para passar pela API.
    Busca receitas com base em uma lista de ingredientes disponíveis.
    Verificar os ingredientes disponíveis do input antes de passar pela API.
    O input deve ser uma string com os ingredientes separados por vírgula (ex: 'tomatoes,cheese,eggs').
    Retorna uma lista de receitas com os ingredientes que elas usam e os que faltam.
    Sempre responda no mesmo idioma do input.
    """
    api_url = "https://api.spoonacular.com/recipes/findByIngredients"
    params = {
        'ingredients': ingredientes,
        'number': 5,
        'ranking': 1,
        'apiKey': SPOON_API_KEY
    }
    try:
        response = requests.get(api_url, params=params)
        response.raise_for_status()
        receitas = response.json()
        if not receitas:
            return "Nenhuma receita encontrada com esses ingredientes."
        
        resultado_formatado = "Encontrei estas receitas para você:\n\n"
        for receita in receitas:
            resultado_formatado += f"--- Título: {receita['title']} ---\n"
            ingredientes_usados = ', '.join([ing['name'] for ing in receita['usedIngredients']])
            resultado_formatado += f"  - Ingredientes que você tem: {ingredientes_usados}\n"
            if receita['missedIngredientCount'] > 0:
                ingredientes_faltando = ', '.join([ing['name'] for ing in receita['missedIngredients']])
                resultado_formatado += f"  - Ingredientes que faltam: {ingredientes_faltando}\n"
            else:
                resultado_formatado += "  - Você tem todos os ingredientes!\n"
            resultado_formatado += "\n"
        return resultado_formatado
    except requests.exceptions.RequestException as e:
        return f"Erro ao conectar com a API: {e}"
    except Exception as e:
        return f"Ocorreu um erro: {e}"

# --- Configuração do Agente ---

# 1. Ferramentas
tools = [buscador_de_receitas]
tool_node = ToolNode(tools)

# 2. LLM 
llm = ChatGroq(model="llama-3.3-70b-versatile", api_key=GROQ_API_KEY, temperature=0)
llm_with_tools = llm.bind_tools(tools)

# 3. Prompt
prompt_template = ChatPromptTemplate.from_messages([
    (
        "system",
        "Você é um assistente de culinária. Seu trabalho é usar a ferramenta 'buscador_de_receitas' para encontrar pratos para o usuário. "
        "Após receber o resultado da ferramenta, sua única tarefa é apresentar essa informação de forma clara e amigável para o usuário. "
        "Quando for responder para o usuario sempre responda o nome da receita e os ingredientes no idioma do input."
        "Antes de dar a resposta final para o usuario confirme os ingredientes que eu disse que tinha e os que faltam para ver se está tudo correto"
        "Não chame a ferramenta novamente depois de já ter um resultado."
    ),
    MessagesPlaceholder(variable_name="messages"),
])

chain = prompt_template | llm_with_tools

# 4. Estado do Grafo
class State(dict):
    messages: Annotated[list, add_messages]

# 5. Nós do Grafo
def chatbot(state: State):
    return {"messages": [chain.invoke({"messages": state['messages']})]}

def router(state: State):
    last_message = state['messages'][-1]
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"
    else:
        return END

# 6. Montagem do Grafo
graph_builder = StateGraph(State)
graph_builder.add_node("chatbot", chatbot)
graph_builder.add_node("tools", tool_node)
graph_builder.add_edge(START, "chatbot")
graph_builder.add_conditional_edges("chatbot", router)
graph_builder.add_edge("tools", "chatbot")

# 7. Compilação com Memória
memory = InMemorySaver()
graph = graph_builder.compile(checkpointer=memory)

# --- Interface com Streamlit ---
st.set_page_config(page_title="🤖 Chef Agente", page_icon="🧑‍🍳")

st.title("🧑‍🍳 Chef Agente")
st.caption("Um Agente de IA que mostra o que está fazendo por baixo dos panos.")

# Inicializa o histórico de mensagens se ele não existir
if "messages" not in st.session_state:
    st.session_state.messages = []

# Exibição das Mensagens
for msg in st.session_state.messages:
    if isinstance(msg, HumanMessage):
        with st.chat_message("user"):
            st.markdown(msg.content)
    elif isinstance(msg, AIMessage) and msg.content:
        # Exibe a mensagem do assistente apenas se tiver conteúdo (a resposta final)
        with st.chat_message("assistant"):
            st.markdown(msg.content)
    elif isinstance(msg, ToolMessage):
        with st.expander(f"⚙️ Ferramenta `{msg.name}` foi usada. Clique para ver os detalhes."):
            st.code(msg.content, language=None)

# Campo de input para nova mensagem
if prompt := st.chat_input("Ingredientes Disponíveis (Ex: ovos, queijo e tomate): "):
    # Adiciona a mensagem do usuário ao estado e exibe na tela
    st.session_state.messages.append(HumanMessage(content=prompt))
    
    # Invoca o grafo com o histórico de mensagens
    with st.spinner("O Chef está pensando e usando suas ferramentas... 🍳"):
        thread_id = "conversa_principal"
        
        # O resultado do grafo contém TODAS as mensagens da execução, incluindo as da ferramenta
        result = graph.invoke(
            {"messages": st.session_state.messages},
            config={"configurable": {"thread_id": thread_id}}
        )
        
        # Substitui o histórico antigo pelo histórico completo e atualizado da execução
        st.session_state.messages = result['messages']
        
        # Força o Streamlit a rodar o script do início para redesenhar a tela com as novas mensagens
        st.rerun()