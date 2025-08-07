# Case-Distrito

## Desafio

Desenvolver um Agente de IA ReACT com uma TOOL, utilizando interface Streamlit e usando o Langsmith para observação.

## Como Funciona

Este projeto utiliza uma arquitetura de agente multi-passo com dois LLMs especialistas para garantir uma tradução confiavel e uma busca de receitas eficiente.

### A Ferramenta (Tool): buscador_de_receitas 🧑‍🍳

O núcleo da ação do agente. É uma função que se conecta à API do Spoonacular para buscar receitas, mas com uma regra importante: ela espera receber os ingredientes já em inglês e em termos culinários específicos.

### O Cérebro do Agente: Uma "Linha de Montagem" com LangGraph 🧠

O agente é construído como um grafo com múltiplos nós:

* Nó 1: O Tradutor (com Gemini-2.5-flash)

Quando o usuário envia uma mensagem em português (ex: "carne de hambúrguer"), o primeiro nó é ativado. Ele usa um LLM especialista em tradução e contexto, o Gemini 2.5 Flash, para converter o input para termos culinários precisos em inglês (ex: "ground beef").

* Nó 2: O Agente ReAct (com Llama-3.3-70b-versatile)

Com os ingredientes já traduzidos, o fluxo passa para o nó principal do agente. Usando o Llama-3.3-70b-versatile via Groq, ele analisa o texto em inglês e executa o ciclo ReAct: raciocina que precisa usar a ferramenta buscador_de_receitas e age, passando os ingredientes corretos para ela.

* Nó 3: A Ferramenta e a Resposta Final
 
O nó da ferramenta é executado, e o resultado da busca retorna ao agente. Ele então formula a resposta final de forma amigável para o usuário, em português.

### A Interface e a Observabilidade 🖥️

* Interface (Streamlit): A conversa acontece em uma interface web construída com Streamlit e implantada no Streamlit Community Cloud.

* Observabilidade (LangSmith): Cada passo da linha de montagem — a tradução com Gemini, a decisão do Llama3 e a execução da ferramenta — é rastreado no LangSmith, permitindo uma depuração completa do fluxo de pensamento do agente.

[Streamlit Link](https://case-distrito-6pvyqudt4vftoggg8puhxw.streamlit.app/)
