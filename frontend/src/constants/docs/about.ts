import type { DocPageData } from './types'

// Créditos e contexto acadêmico espelham a folha de rosto/ficha catalográfica
// do PFC (PFC/main.tex) - manter em sincronia se aquele texto mudar.
export const aboutPage: DocPageData = {
  title: 'Sobre o AGIA',
  description:
    'Sistema de apoio à prospecção tecnológica baseado em Inteligência Artificial, desenvolvido como Projeto de Final de Curso de Engenharia de Computação do Instituto Militar de Engenharia (IME), em parceria com a AGITEC.',
  sections: [
    {
      id: 'proposito',
      title: 'Propósito',
      subsections: [
        {
          title: 'O problema',
          blocks: [
            {
              type: 'paragraph',
              text: 'Um levantamento de prospecção tecnológica feito à mão passa por várias etapas: definir termos de busca, consultar bases com sintaxes diferentes, triar centenas ou milhares de resultados, identificar instituições e depositantes relevantes, analisar tendências ao longo do tempo e consolidar tudo em um documento que apoie a tomada de decisão. Cada etapa consome horas ou dias de profissionais qualificados, e a qualidade final depende muito da experiência de quem faz a busca.',
            },
          ],
        },
        {
          title: 'O objetivo',
          blocks: [
            {
              type: 'paragraph',
              text: 'Automatizar esse processo por meio da consulta integrada a bases de artigos científicos e patentes, da análise dos resultados recuperados e da geração automática de um relatório técnico consolidado no padrão REPTEC da AGITEC. Em cada ponto de decisão, o usuário revisa, ajusta ou rejeita o que a IA propõe antes de seguir.',
            },
            {
              type: 'list',
              items: [
                'Refino do tema e geração de queries com modelos de linguagem (LLMs) configuráveis por ponto de uso: Claude (Anthropic), Gemini (Google) ou modelos locais via Ollama.',
                'Busca automatizada em patentes (EPO Open Patent Services) e artigos (Scopus, com resumos enriquecidos via OpenAlex).',
                'Extração local de termos-chave (NLP), sem IA generativa, para ampliar a cobertura da busca final.',
                'Inferência estatística da amostra, rankings (top depositantes, instituições, CPC, áreas) e curva S de maturidade tecnológica.',
                'Relatório REPTEC editável em LaTeX, redigido com apoio de RAG sobre os documentos recuperados, com revisão linguística e compilação para PDF.',
              ],
            },
          ],
        },
      ],
    },
    {
      id: 'autoria',
      title: 'Autoria',
      subsections: [
        {
          title: 'Projeto de Final de Curso — IME, 2026',
          blocks: [
            {
              type: 'paragraph',
              text: 'Utilização de Inteligência Artificial para Análise e Prospecção Tecnológica através da Consulta a Artigos e Patentes. Curso de Graduação em Engenharia de Computação do Instituto Militar de Engenharia, Rio de Janeiro.',
            },
            {
              type: 'table',
              headers: ['Papel', 'Nome'],
              rows: [
                ['Autores', 'João Pedro Bandeira Belchior; Carlos Alexandre Siqueira de Almeida'],
                ['Orientadora', 'Maria Cláudia Reis Cavalcanti, D.Sc.'],
                ['Coorientador externo', 'Cel QEM José Adalberto França Junior — AGITEC'],
                ['Coorientadora externa', 'Maj Giselle de Farias Rosa — AGITEC'],
              ],
            },
          ],
        },
      ],
    },
    {
      id: 'tecnologia',
      title: 'Tecnologia',
      subsections: [
        {
          title: 'Stack',
          blocks: [
            {
              type: 'table',
              headers: ['Camada', 'Tecnologias'],
              rows: [
                ['Frontend', 'React + TypeScript (Vite), Zustand, Tailwind CSS'],
                ['Backend', 'Python, FastAPI assíncrono em arquitetura hexagonal (ports & adapters), SQLAlchemy 2.0'],
                ['Dados', 'PostgreSQL (sessões, queries, documentos), MinIO (gráficos, .tex, PDF, anexos), ChromaDB (vetores do RAG)'],
                ['IA generativa', 'Anthropic, Gemini ou servidor compatível com OpenAI (Ollama local ou LLM da intranet)'],
                ['NLP local', 'spaCy/PatternRank, BM25F, KeyBERT (sentence-transformers), RRF, C-value'],
                ['Relatório', 'Template LaTeX REPTEC, TeX Live (container latex-compiler), LanguageTool'],
              ],
            },
          ],
        },
        {
          title: 'Fontes de dados',
          blocks: [
            {
              type: 'list',
              items: [
                'Patentes: Open Patent Services (OPS) do Escritório Europeu de Patentes (EPO/Espacenet).',
                'Artigos científicos: Scopus (Elsevier), com resumos complementados pelo OpenAlex.',
                'As APIs ativas de cada família (patentes/artigos) são escolhidas em Configurações › Busca.',
              ],
            },
          ],
        },
        {
          title: 'Metodologia de referência',
          blocks: [
            {
              type: 'paragraph',
              text: 'A estrutura do relatório segue um REPTEC real da AGITEC. As figuras fixas da Metodologia (seções 5.1 a 5.3) seguem os trabalhos de Madeo e de Kucharavy sobre prospecção e ciclo de vida de tecnologias.',
            },
          ],
        },
      ],
    },
  ],
}
