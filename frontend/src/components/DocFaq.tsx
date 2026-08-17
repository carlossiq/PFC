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
    id: 'salvar-vs-finalizar',
    question: '"Salvar Progresso" e "Finalizar Sessão" fazem a mesma coisa?',
    answer:
      'Não. "Salvar Progresso" grava o que você já preencheu até agora e mantém a sessão como pendente, pra você continuar depois pela tela de Busca. "Finalizar Sessão" (disponível na etapa "Resultados Iniciais") marca a sessão como concluída. Hoje esse é o ponto em que a sessão passa a contar como finalizada no sistema, mesmo havendo mais etapas depois dele na barra de progresso.',
  },
  {
    id: 'continuar-pesquisa',
    question: 'Por que continuar uma pesquisa salva volta pro início em vez de exatamente onde eu parei?',
    answer:
      'Continuar uma sessão salva (pela tela de Busca) recarrega os dados que você já preencheu, mas hoje sempre reabre na primeira etapa. Além disso, os resultados de busca da Exploração Inicial não ficam salvos — pode ser necessário confirmar a query de novo para trazê-los de volta.',
  },
  {
    id: 'sessao-bloqueada',
    question: 'Por que não consigo sair da tela de prospecção sem confirmar antes?',
    answer:
      'Enquanto uma sessão está em andamento, o menu lateral fica bloqueado e o navegador avisa antes de fechar a aba. É uma proteção pra evitar perder progresso não salvo por engano.',
  },
  {
    id: 'relatorio',
    question: 'A etapa "Geração do Relatório" já gera um relatório?',
    answer: 'Ainda não — essa etapa está em construção. Por enquanto ela só mostra os botões de navegação.',
  },
  {
    id: 'amostragem-sem-gerar',
    question: 'Por que a "Amostragem de Termos" não tem um botão para gerar outros termos?',
    answer:
      'Os termos são extraídos automaticamente do texto dos resultados, sem IA generativa — por isso não existe um "gerar outros", só a opção de marcar/desmarcar quais termos entram na query final.',
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
