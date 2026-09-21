import { useEffect, useRef, useState } from 'react'
import { InfoTooltip } from '../InfoTooltip'
import { ImageCropModal } from './ImageCropModal'
import {
  deleteReportCoverImage,
  getReportCoverImage,
  uploadReportCoverImage,
  REPORT_COVER_IMAGE_TARGET_SIZE,
  type ReportCoverImage,
} from '../../services/config'

const DESCRIPTION =
  'Símbolo/logo exibido na capa de todo relatório gerado (ver POST /report/{id}/assemble). ' +
  'Ao enviar uma imagem, você mesmo escolhe o enquadramento (zoom + posição) dentro de um ' +
  'quadro de proporção fixa, pra ficar padronizado em todo relatório. Atualizar aqui não ' +
  'altera PDFs já compilados, mas toda recompilação (botão "Compilar" na tela do relatório) ' +
  'passa a usar a imagem mais recente.'

const [TARGET_WIDTH, TARGET_HEIGHT] = REPORT_COVER_IMAGE_TARGET_SIZE

// Painel de "Geral" pra enviar/trocar/remover a imagem de capa do
// relatório - única imagem GLOBAL (não por sessão), persistida no MinIO
// (ver app/core/services/report_cover_image.py). Segue o mesmo padrão de
// "salva automaticamente" das outras configurações: selecionar um arquivo
// já dispara o upload, sem botão de confirmar separado.
export function ReportCoverImagePanel() {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [cover, setCover] = useState<ReportCoverImage | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [pendingFile, setPendingFile] = useState<File | null>(null)

  useEffect(() => {
    let cancelled = false
    getReportCoverImage()
      .then((result) => {
        if (!cancelled) setCover(result)
      })
      .catch(() => {
        if (!cancelled) setError('Não foi possível carregar a imagem de capa atual.')
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  function handleFileSelected(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    setError(null)
    setPendingFile(file)
  }

  async function handleCropConfirmed(blob: Blob) {
    setPendingFile(null)
    setIsSaving(true)
    setError(null)
    try {
      setCover(await uploadReportCoverImage(blob))
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'Não foi possível enviar a imagem.')
    } finally {
      setIsSaving(false)
    }
  }

  async function handleRemove() {
    setIsSaving(true)
    setError(null)
    try {
      await deleteReportCoverImage()
      setCover({ hasImage: false, imageBase64: null })
    } catch {
      setError('Não foi possível remover a imagem.')
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <div className="flex items-center gap-1.5 mb-3">
        <p className="text-sm font-medium text-gray-800">Imagem de capa do relatório</p>
        <InfoTooltip description={DESCRIPTION} />
      </div>

      {error && <p className="text-xs text-red-600 mb-3">{error}</p>}

      <div className="flex items-center gap-4">
        <div
          className="shrink-0 rounded-md border border-gray-200 bg-gray-50 flex items-center justify-center overflow-hidden"
          style={{ width: 100, height: 141 }}
        >
          {isLoading ? (
            <span className="text-[10px] text-gray-400">Carregando...</span>
          ) : cover?.hasImage && cover.imageBase64 ? (
            <img
              src={`data:image/png;base64,${cover.imageBase64}`}
              alt="Imagem de capa atual"
              className="w-full h-full object-cover"
            />
          ) : (
            <span className="text-[10px] text-gray-400 text-center px-2">Nenhuma imagem configurada</span>
          )}
        </div>

        <div className="flex flex-col gap-2">
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleFileSelected}
            className="hidden"
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={isSaving}
            className="text-sm font-semibold text-[#0f9448] hover:text-[#0d843f] disabled:opacity-60 disabled:cursor-not-allowed text-left"
          >
            {isSaving ? 'Enviando...' : cover?.hasImage ? 'Trocar imagem' : 'Enviar imagem'}
          </button>
          {cover?.hasImage && (
            <button
              type="button"
              onClick={handleRemove}
              disabled={isSaving}
              className="flex items-center gap-1.5 text-sm text-gray-400 hover:text-red-600 disabled:opacity-60 disabled:cursor-not-allowed text-left"
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
              Remover imagem
            </button>
          )}
        </div>
      </div>

      {pendingFile && (
        <ImageCropModal
          file={pendingFile}
          targetWidth={TARGET_WIDTH}
          targetHeight={TARGET_HEIGHT}
          onCancel={() => setPendingFile(null)}
          onConfirm={handleCropConfirmed}
        />
      )}
    </div>
  )
}
