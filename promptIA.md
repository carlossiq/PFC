Técnicas anti-alucinação:

persona pattern; chain of thoughts; few shot learning

Técnicas para construir queries de prospecção

Reuni as práticas mais consolidadas em busca de patentes e em bibliometria, e depois apliquei ao que vi nas suas queries.

1. Combine palavras-chave com classificação (CPC/IPC)

Patentes usam linguagem jurídica e técnica variada, então a busca só por palavra-chave acha algumas patentes, mas não todas. As classes CPC agrupam patentes parecidas mesmo quando descrevem a invenção com termos diferentes, o que ajuda a revisar tudo o que é relevante e reduz o ruído. O EPO alerta que buscas só por palavra-chave podem perder documentos importantes, principalmente de escritórios asiáticos, cujos depósitos nem sempre estão mapeados na CPC. Por isso a recomendação é usar os dois caminhos e juntá-los com OR/AND. 
Northeastern University
CAS

Um método prático: mapear o problema para seções CPC amplas, escolher subclasses específicas para precisão e só então acrescentar palavras-chave com operadores booleanos. Também dá para descobrir os códigos CPC relevantes olhando patentes já encontradas e usá-los numa segunda busca. 
SciSpace
Converting Quarterly

2. Trate a busca como iterativa (o que o seu probe já tenta fazer)

O processo é iterativo: faz-se uma revisão rápida dos resultados, refina-se a string e incorporam-se novas palavras-chave e códigos de classificação que apareceram na análise. Isso valida a lógica do seu probe search. O ganho vem de alimentar a reescrita com termos e CPCs vindos de documentos realmente relevantes, não só com termos frequentes. 
Lexology

3. Comece por uma "semente" e valide

Na bibliometria, a abordagem padrão é partir de um termo central como busca-semente, listar candidatos de alta frequência, confirmar o significado deles, testá-los por co-ocorrência e checagem manual para equilibrar recall e precisão, e depois combinar com filtro por categoria temática. Existe também um método sistemático para tecnologias emergentes que busca buscas replicáveis, com recall alto e precisão satisfatória. 
Springer
Springer

4. Meça precisão e recall, mesmo que por amostragem

Um estudo comparou estratégias de recuperação validando manualmente amostras aleatórias de 522 artigos e calculando precisão e um "pseudo-recall". A estratégia baseada em palavras-chave teve o melhor desempenho, e as baseadas em citação ficaram bem abaixo. Para você, isso significa: separe 30 a 50 resultados, marque relevante ou não, e use a taxa como métrica para comparar versões da query. Sem isso não dá para saber se uma mudança melhorou. 
arxiv

5. Escolha o campo conscientemente

Restringir a busca a título, resumo e palavras-chave do autor aumenta a precisão, mas pode reduzir o recall. Outra revisão observa que limitar a "Título" e "Resumo", ou só a "Título", gera um conjunto mais focado tematicamente. A escolha depende do objetivo: para curva S e contagem, precisão pesa mais. 
PubMed Central
PubMed Central

6. Cubra sinônimos, siglas e variantes, e cuide da sintaxe da base

Comece pelos termos centrais, incluindo sinônimos, abreviações e grafias alternativas. Use booleanos, curingas e truncamento, e respeite a sintaxe própria de cada base, além de filtros de período, tipo de documento e categoria. Proximidade também ajuda: ela encontra documentos em que duas palavras aparecem a poucas palavras de distância, sem serem adjacentes. 
ScienceDirect
PatentPC

7. Use LLM para expandir, com ancoragem

A literatura aponta que métodos com aprendizado de máquina e LLMs podem ajudar com sinonímia e polissemia, mas trazem novas fontes de viés. Há trabalhos que geram queries a partir de frases-chave extraídas com apoio de conhecimento do IPC, selecionando as k melhores para montar a query de recuperação. É o mesmo princípio do seu pipeline, com o CPC como âncora. 
PubMed Central
arxiv

Aplicação às suas queries de TETRA

Estes pontos são leitura minha das queries que você colou, não vêm dessas fontes:

Query de artigos sem âncora: o ABS(...) junta com OR termos genéricos como "radio communication", "tactical communication", "defense applications" e "military operations". Qualquer artigo sobre rádio ou operações militares entra, mesmo sem falar de TETRA. Isso explica os 650 resultados pouco úteis. O tema deve ser obrigatório: (TETRA ou "terrestrial trunked radio") AND (contexto).
Desvio de escopo: o tema é Terrestrial Trunked Radio, mas a query foi ampliada para "militar/defesa". Isso muda o objeto da prospecção.
Ambiguidade de "TETRA": a sigla pega peixe (tetra), Tetra Pak, Tetra Tech e similares. Prefira o nome completo, ou exija TETRA junto de contexto (radio, trunked, PMR, ETSI, TETRAPOL, TEDS).
Precedência booleana: na query de patentes, OR e AND misturados no mesmo nível dependem da precedência da base. Parentetize cada bloco explicitamente.
Janelas de tempo diferentes: patentes de 2010 a 2026 e artigos de 2000 a 2026 dificultam comparar as curvas S.
Sem classificação: a query de patentes não usa CPC. Para TETRA, verifique códigos de radiocomunicação móvel (região H04W e H04B; confirme os códigos exatos no Espacenet antes de usar).
Fluxo sugerido para o pipeline
Bloco A (tema, obrigatório): nome completo + sigla + variantes (trunked radio, TETRA, TETRA Release 2, TEDS).
Bloco B (contexto, opcional): só para refinar, nunca para ampliar sozinho.
Bloco C (CPC): extraídos dos documentos relevantes do probe, com OR em relação ao bloco A, não AND, para não perder patentes mal classificadas.
Probe: 50 a 100 documentos, com termos por document frequency e CPCs mais frequentes.
Reescrita pela IA: entrega o tema original, 10 a 15 termos limpos e os top CPCs. Pede a query no formato de cada base, com a sintaxe correta (Espacenet e Scopus são diferentes).
Validação: amostra de 30 a 50 resultados, precisão medida. Guarde a versão da query e a métrica.
Ajuste: se a precisão for baixa, estreite o campo (título e resumo) e adicione NOT para ruídos conhecidos. Se o recall for baixo, acrescente sinônimos e CPCs.