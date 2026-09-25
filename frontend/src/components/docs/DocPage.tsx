import type { ReactNode } from 'react'
import type { DocBlock, DocPageData } from '../../constants/docs/types'

// Trechos entre `crases` viram <code> inline - o conteúdo em
// constants/docs/*.ts é texto simples, sem markdown.
function renderInline(text: string): ReactNode {
  const parts = text.split(/(`[^`]+`)/g)
  return parts.map((part, i) =>
    part.startsWith('`') && part.endsWith('`') && part.length > 1 ? (
      <code key={i} className="font-mono text-[0.9em] bg-gray-100 text-gray-800 px-1 py-0.5 rounded">
        {part.slice(1, -1)}
      </code>
    ) : (
      part
    )
  )
}

function Block({ block }: { block: DocBlock }) {
  switch (block.type) {
    case 'paragraph':
      return <p className="text-base text-gray-600 leading-relaxed">{renderInline(block.text)}</p>
    case 'note':
      return (
        <p className="text-base text-gray-700 bg-gray-100 border-l-2 border-gray-400 rounded-r-md px-3 py-2">
          {renderInline(block.text)}
        </p>
      )
    case 'warning':
      return (
        <p className="text-base text-amber-900 bg-amber-50 border-l-2 border-amber-500 rounded-r-md px-3 py-2">
          {renderInline(block.text)}
        </p>
      )
    case 'list': {
      const ListTag = block.ordered ? 'ol' : 'ul'
      return (
        <ListTag
          className={`${block.ordered ? 'list-decimal' : 'list-disc'} pl-6 space-y-1 text-base text-gray-600 leading-relaxed`}
        >
          {block.items.map((item, i) => (
            <li key={i}>{renderInline(item)}</li>
          ))}
        </ListTag>
      )
    }
    case 'code':
      return (
        <figure>
          {block.caption && <figcaption className="text-sm text-gray-500 mb-1">{block.caption}</figcaption>}
          <pre className="overflow-x-auto bg-[#17212b] text-gray-100 text-sm font-mono rounded-md px-4 py-3 leading-relaxed">
            <code>{block.code}</code>
          </pre>
        </figure>
      )
    case 'table':
      return (
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm border border-gray-300 bg-white">
            <thead className="bg-gray-100">
              <tr>
                {block.headers.map((h) => (
                  <th key={h} className="text-left font-semibold text-gray-800 px-3 py-2 border-b border-gray-300">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {block.rows.map((row, i) => (
                <tr key={i} className="border-b border-gray-200 last:border-b-0 align-top">
                  {row.map((cell, j) => (
                    <td key={j} className="px-3 py-2 text-gray-700">
                      {renderInline(cell)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )
  }
}

interface DocPageProps extends DocPageData {
  // Conteúdo extra logo abaixo da descrição (ex.: link pro Swagger em DocApi).
  children?: ReactNode
}

// Renderizador comum das páginas de Documentação e do About: seção ->
// subseções -> blocos (parágrafo, nota, aviso, lista, código, tabela).
// Um índice no topo leva direto a cada seção.
export function DocPage({ title, description, sections, children }: DocPageProps) {
  return (
    <div className="w-full max-w-5xl">
      <h2 className="text-3xl font-bold mb-2 text-gray-900">{title}</h2>
      <p className="text-base text-gray-600 mb-6">{renderInline(description)}</p>
      {children}

      {sections.length > 2 && (
        <nav className="mb-8 flex flex-wrap gap-2">
          {sections.map((section) => (
            <a
              key={section.id}
              href={`#doc-${section.id}`}
              className="text-sm px-3 py-1 rounded-full border border-gray-300 bg-white text-gray-700 hover:border-[#0f9448] hover:text-[#0f9448]"
            >
              {section.title}
            </a>
          ))}
        </nav>
      )}

      <div className="space-y-10">
        {sections.map((section) => (
          <section key={section.id} id={`doc-${section.id}`} className="scroll-mt-4">
            <h3 className="text-xl font-semibold text-gray-900 mb-4">{section.title}</h3>
            {section.intro && <p className="text-base text-gray-700 mb-3">{renderInline(section.intro)}</p>}

            <div className="ml-4 space-y-6">
              {section.subsections.map((sub) => (
                <div key={sub.title}>
                  <p className="text-lg font-medium text-gray-800 mb-2 flex items-center gap-2">
                    {sub.title}
                    {sub.inProgress && (
                      <span className="text-sm font-normal text-amber-700 bg-amber-100 px-2 py-0.5 rounded-full">
                        em construção
                      </span>
                    )}
                  </p>
                  <div className="space-y-3">
                    {sub.blocks.map((block, i) => (
                      <Block key={i} block={block} />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  )
}
