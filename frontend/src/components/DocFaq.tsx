import { useState } from 'react'
import { ChevronDown } from 'lucide-react'

interface FaqItem {
  id: string
  question: string
  answer: string
}

const faqItems: FaqItem[] = [
  {
    id: 'label-botao',
    question: "Por que às vezes o botão mostra \"Avançar\" ou \"Ver parâmetros\" em vez de \"Gerar\" ou \"Refinar parâmetros\"?",
    answer:
      'O app compara o que você preencheu agora com o que já foi gerado da última vez. Se nada relevante mudou, ele reaproveita o resultado anterior em vez de chamar a IA de novo — e o rótulo do botão muda para indicar que não vai gerar algo novo, só avançar.',
  },
  {
    id: 'cascata',
    question: 'Por que editar um campo em uma etapa anterior faz com que eu precise gerar tudo de novo nas etapas seguintes?',
    answer:
      'Cada etapa depende do que foi definido antes dela (tema, tema refinado, query escolhida). Ao mudar algo em uma etapa anterior, o conteúdo já gerado nas etapas seguintes deixa de corresponder à entrada atual, então ele é invalidado. É o mesmo mecanismo da pergunta acima, só que percebido "para a frente": a etapa seguinte detecta que a entrada mudou e oferece gerar de novo.',
  },
  {
    id: 'voltar',
    question: 'Se eu clicar em Voltar, eu perco o que já tinha gerado?',
    answer:
      'Não. O que foi gerado continua salvo enquanto a sessão estiver aberta. Voltar e Avançar restauram exatamente onde você estava, sem chamar a IA de novo — a menos que algo em uma etapa anterior tenha mudado nesse meio tempo (ver pergunta acima).',
  },
  {
    id: 'sessao-concluida',
    question: 'Quando uma sessão passa a contar como concluída?',
    answer:
      'Ao clicar em "Montar .tex" na Geração do Relatório. Até lá, "Salvar Progresso" grava o que você já preencheu e mantém a sessão pendente, para continuar depois pela tela de Busca. Depois de montar o .tex, a pesquisa (queries, termos, buscas) não pode mais ser editada, só o texto do relatório.',
  },
  {
    id: 'continuar-pesquisa',
    question: 'Continuar uma pesquisa salva reabre onde eu parei?',
    answer:
      'Sim. "Continuar pesquisa", na tela de Busca, reabre a sessão na etapa em que ela foi salva, com os documentos e termos restaurados do banco, sem consultar as APIs de novo. Sessões concluídas mostram "Ver Relatório", que abre direto o editor do documento.',
  },
  {
    id: 'sessao-bloqueada',
    question: 'Por que não consigo sair da tela de prospecção sem confirmar antes?',
    answer:
      'Enquanto uma sessão está em andamento, o menu lateral fica bloqueado e o navegador avisa antes de fechar a aba. É uma proteção pra evitar perder progresso não salvo por engano.',
  },
  {
    id: 'amostragem-sem-gerar',
    question: 'Por que a "Amostragem de Termos" não tem um botão para gerar outros termos?',
    answer:
      'Os termos são extraídos automaticamente do texto dos resultados, sem IA generativa: os mesmos documentos sempre produzem os mesmos termos. Por isso não existe "gerar outros", só a opção de marcar ou desmarcar quais termos entram na query final. Para obter termos diferentes, mude a query exploratória. Veja Extração de Termos.',
  },
  {
    id: 'keybert-modelo',
    question: 'Posso trocar o modelo do KeyBERT?',
    answer:
      'Sim, em Configurações › Geral › "Modelo do KeyBERT". As opções recomendadas são distiluse-base-multilingual-cased-v2 (padrão, multilíngue), all-mpnet-base-v2 (patentes e textos técnicos) e allenai/specter (artigos acadêmicos). A troca só vale depois de reiniciar o backend, e o mesmo modelo é usado no RAG do relatório.',
  },
  {
    id: 'usepackage',
    question: 'Por que meu \\usepackage faz a compilação do PDF falhar?',
    answer:
      'O compilador roda sem internet e só tem os pacotes instalados na imagem latex-compiler. Pacotes como multirow, siunitx, wrapfig ou makecell não estão disponíveis. A lista do que já está carregado e do que pode ser adicionado está em Relatório e LaTeX › Pacotes LaTeX.',
  },
  {
    id: 'citacoes',
    question: 'Por que o texto da IA não cita um documento que eu esperava?',
    answer:
      'O LLM só vê os trechos mais relevantes de cada seção, recuperados por RAG, e o sistema remove toda citação que não corresponda a um documento desse contexto. Um documento pouco relevante para a seção pode ficar de fora. É possível ajustar "Corte relativo do RAG" e "Top-K do RAG por seção" em Configurações › Geral e gerar a seção de novo, ou citar o documento manualmente no editor.',
  },
  {
    id: 'curva-s-confiavel',
    question: 'O que significa o aviso de ajuste pouco confiável na curva S?',
    answer:
      'O ajuste logístico não passou em algum critério de qualidade: R² abaixo de 0,90, saturação alta com menos de 5 anos de dados ou taxa de crescimento implausível. A curva continua sendo exibida, sem a parte projetada, e deve ser lida com cautela. Buscas com mais anos e mais documentos costumam resolver. Veja Pipeline de Prospecção › Curva S.',
  },
  {
    id: 'editar-tex',
    question: 'Minhas edições no .tex são perdidas se eu gerar algo de novo?',
    answer:
      'Só com "Remontar .tex", que refaz o documento do zero e pede confirmação antes. Compilar, revisar, inserir imagens ou baixar o .zip nunca descartam edições.',
  },
]

export function DocFaq() {
  const [openId, setOpenId] = useState<string | null>(faqItems[0].id)

  return (
    <div className="w-full">
      <h2 className="text-3xl font-bold mb-2 text-gray-900">FAQ</h2>
      <p className="text-base text-gray-600 mb-8">
        Respostas para dúvidas comuns sobre o comportamento do app. Para o passo a passo completo, veja o{' '}
        <span className="font-medium">Guia do Usuário</span>.
      </p>

      <div className="space-y-3">
        {faqItems.map((item) => {
          const isOpen = openId === item.id
          return (
            <div key={item.id} className="border border-gray-300 rounded-lg overflow-hidden bg-white">
              <button
                onClick={() => setOpenId(isOpen ? null : item.id)}
                className="w-full flex items-center justify-between gap-4 px-5 py-4 text-left hover:bg-gray-50 transition-colors"
              >
                <span className="text-lg font-medium text-gray-900">{item.question}</span>
                <ChevronDown
                  className={`w-5 h-5 flex-shrink-0 text-gray-500 transition-transform ${isOpen ? 'rotate-180' : ''}`}
                />
              </button>
              {isOpen && (
                <div className="px-5 pb-5 text-base text-gray-700 leading-relaxed">{item.answer}</div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
