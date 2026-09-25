import { ExternalLink } from 'lucide-react'
import { apiPage } from '../../constants/docs/api'
import { API_BASE_URL } from '../../services/api'
import { DocPage } from './DocPage'

// Swagger do FastAPI fica na raiz do servidor (/docs), fora do prefixo
// /api/v1 das rotas - ver app/main.py (docs_url padrão).
const SWAGGER_URL = `${API_BASE_URL.replace(/\/api\/v\d+\/?$/, '')}/docs`

export function DocApi() {
  return (
    <DocPage {...apiPage}>
      <a
        href={SWAGGER_URL}
        target="_blank"
        rel="noreferrer"
        className="inline-flex items-center gap-2 mb-8 px-4 py-2 rounded-md bg-[#0f9448] hover:bg-[#0d843f] text-white text-sm font-semibold"
      >
        Abrir Swagger (schemas completos)
        <ExternalLink size={16} />
      </a>
    </DocPage>
  )
}
