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
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

# --- Carregamento de Variáveis de Ambiente ---
load_dotenv()
SPOON_API_KEY = os.getenv("SPOON_API_KEY") 
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")

# --- Definição da Ferramenta ---
@tool
def buscador_de_receitas(ingredientes: str) -> str:
    """
    Busca receitas com base em uma lista de ingredientes EM INGLÊS.
    O input deve ser uma string com ingredientes específicos separados por vírgula (ex: 'ground beef,cheese').
    """
    api_url = "https://api.spoonacular.com/recipes/findByIngredients"
    params = {'ingredients': ingredientes, 'number': 5, 'ranking': 1, 'apiKey': SPOON_API_KEY}
    try:
        response = requests.get(api_url, params=params)
        response.raise_for_status()
        receitas = response.json()
        if not receitas:
            return f"Nenhuma receita encontrada com os ingredientes: {ingredientes}."
        
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

# --- Configuração do Agente ---

# -- Ferramentas --
tools = [buscador_de_receitas]
tool_node = ToolNode(tools)

# -- LLMs --
llm = ChatGroq(model="llama-3.3-70b-versatile", api_key=GROQ_API_KEY, temperature=0)
llm_with_tools = llm.bind_tools(tools)
llm_tradutor = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=GOOGLE_API_KEY, temperature=0)

# -- Prompts --
prompt_agente = ChatPromptTemplate.from_messages([
    ("system", 
    "Você é um assistente de culinária. Sua tarefa é usar a ferramenta 'buscador_de_receitas' com os ingredientes fornecidos."
    "Após receber o resultado da ferramenta, apresente a informação de forma clara em português."),
    MessagesPlaceholder(variable_name="messages"),
])
chain_agente = prompt_agente | llm_with_tools

# -- Estado do Grafo --
class State(dict):
    messages: Annotated[list, add_messages]

# -- Nós do Grafo --
def tradutor(state: State):
    """Nó que traduz e refina os ingredientes do usuário."""
    user_input = state['messages'][-1].content
    
    prompt_tradutor = ChatPromptTemplate.from_template(
        "Traduza a seguinte lista de ingredientes para o inglês, usando termos culinários específicos. "
        "Exemplos: 'carne de hambúrguer' -> 'ground beef'. 'peito de frango' -> 'chicken breast'."
        "Retorne APENAS a lista de ingredientes traduzida, separada por vírgulas. "
        "Lista: {ingredientes}"
    )
    chain_tradutora = prompt_tradutor | llm_tradutor
    ingredientes_traduzidos = chain_tradutora.invoke({"ingredientes": user_input}).content

    return {"messages": [HumanMessage(content=f"Ingredientes traduzidos para busca: {ingredientes_traduzidos}")]}

def chatbot(state: State):
    """Nó principal do agente que decide se usa uma ferramenta."""
    return {"messages": [chain_agente.invoke({"messages": state['messages']})]}

def roteador_de_ferramenta(state: State):
    """Roteador que direciona para a ferramenta ou finaliza."""
    last_message = state['messages'][-1]
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"
    else:
        return END

# 5. Montagem do Grafo
graph_builder = StateGraph(State)
graph_builder.add_node("tradutor", tradutor)
graph_builder.add_node("chatbot", chatbot)
graph_builder.add_node("tools", tool_node)

graph_builder.add_edge(START, "tradutor")
graph_builder.add_edge("tradutor", "chatbot")
graph_builder.add_conditional_edges("chatbot", roteador_de_ferramenta)
graph_builder.add_edge("tools", "chatbot")

# -- Compilação com Memória --
memory = InMemorySaver()
graph = graph_builder.compile(checkpointer=memory)

# --- Interface com Streamlit ---
st.set_page_config(page_title="🤖 Chef Agente", page_icon="🧑‍🍳")
st.title("🧑‍🍳 Chef Agente")
st.caption("Um Agente de IA especialista para encontrar suas receitas.")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    if isinstance(msg, HumanMessage):
        with st.chat_message("user"):
            st.markdown(msg.content)
    elif isinstance(msg, AIMessage) and msg.content:
        with st.chat_message("assistant"):
            st.markdown(msg.content)
    elif isinstance(msg, ToolMessage):
        with st.expander(f"⚙️ Ferramenta `{msg.name}` foi usada. Clique para ver os detalhes."):
            st.code(msg.content, language=None)

if prompt := st.chat_input("Ingredientes Disponíveis (Ex: Tomate, queijo e ovo): "):
    st.session_state.messages.append(HumanMessage(content=prompt))
    
    with st.spinner("O Chef está buscando algumas de suas receitas... 🍳"):
        thread_id = "conversa_principal"
        result = graph.invoke(
            {"messages": st.session_state.messages},
            config={"configurable": {"thread_id": thread_id}}
        )
        
        messages_para_exibir = []
        for msg in result['messages']:
            if isinstance(msg, HumanMessage) and msg.content.startswith("Ingredientes traduzidos para busca:"):
                continue
            messages_para_exibir.append(msg)
        
        st.session_state.messages = messages_para_exibir
        st.rerun()
