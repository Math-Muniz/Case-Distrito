# Case-Distrito

## Desafio

Desenvolver um Agente de IA ReACT com uma TOOL, utilizando interface Streamlit e usando o Langsmith para observação.

## Como Funciona
Este projeto é um agente de IA construído sobre três pilares principais: uma ferramenta para interagir com o mundo, o agente e uma interface web para conversar com o usuário.

* A Ferramenta(Tool): buscador_de_receitas 🧑‍🍳

O coração da funcionalidade do agente é uma ferramenta customizada que se conecta à API do Spoonacular. A função dela é:

Receber uma lista de ingredientes do usuário.

Chamar a API externa para encontrar receitas que usem esses ingredientes.

Formatar o resultado de forma clara, mostrando as receitas encontradas, os ingredientes que o usuário já tem e os que faltam.

* O Agente: LangGraph 🧠

Em vez de um fluxo linear, o agente usa LangGraph.

Raciocinar (Reasoning): Quando o usuário envia uma mensagem (ex: "tenho ovos e queijo"), o nó principal chatbot é ativado. Usando o modelo Llama3 via Groq, ele analisa a mensagem e o prompt do sistema. Ele percebe que, para cumprir a tarefa, precisa de informações externas e decide que a melhor ação é usar a ferramenta buscador_de_receitas.

Agir (Acting): A decisão é enviada a um roteador, que direciona o fluxo para o nó tools. Este nó executa a ferramenta, que chama a API do Spoonacular e obtém os dados das receitas.

Observar e Raciocinar de Novo: O resultado da ferramenta (a lista de receitas) é enviado de volta ao nó chatbot. O agente agora "observa" essa nova informação e, seguindo as instruções do prompt, sua nova tarefa se torna "apresentar este resultado de forma amigável ao usuário".

* A Interface: Streamlit 🖥️

A interface web foi construída com Streamlit e o Deploy foi feito no Streamlit Community.

* Observabilidade: LangSmith

Cada chamada ao LLM, cada decisão do roteador e cada execução da ferramenta são rastreadas e enviadas para o LangSmith. Isso permite depurar o fluxo de pensamento do agente, monitorar o uso das APIs e garantir que ele esteja se comportando como esperado.

[Streamlit Link](https://case-distrito-icmapevhxqg7eicdnvxppl.streamlit.app/)
