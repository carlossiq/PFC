import { useEffect, useRef, useState } from 'react'

interface Offset {
  x: number
  y: number
}

interface ImageCropModalProps {
  file: File
  // Proporção final (ver REPORT_COVER_IMAGE_TARGET_SIZE em services/config.ts,
  // espelhando app/core/services/report_cover_image.py) - a moldura de edição
  // usa a MESMA proporção, só menor, pra o que o usuário vê já ser o corte real.
  targetWidth: number
  targetHeight: number
  onCancel: () => void
  onConfirm: (blob: Blob) => void
}

const FRAME_WIDTH = 240
const MAX_ZOOM = 3

// Editor de "avatar" (zoom + arraste dentro de uma moldura de proporção
// fixa) pra padronizar a imagem de capa do relatório - o usuário decide o
// enquadramento, não um corte automático no servidor (ver
// app/core/services/report_cover_image.py, que só reafirma esse tamanho
// como rede de segurança). O resultado confirmado já sai no tamanho exato
// (targetWidth x targetHeight), pronto pra upload.
export function ImageCropModal({ file, targetWidth, targetHeight, onCancel, onConfirm }: ImageCropModalProps) {
  const frameHeight = Math.round((FRAME_WIDTH * targetHeight) / targetWidth)
  const imgRef = useRef<HTMLImageElement>(null)
  const dragRef = useRef<{ startX: number; startY: number; startOffset: Offset } | null>(null)

  const [imageUrl, setImageUrl] = useState<string | null>(null)
  const [naturalSize, setNaturalSize] = useState<{ width: number; height: number } | null>(null)
  const [zoom, setZoom] = useState(1)
  const [offset, setOffset] = useState<Offset>({ x: 0, y: 0 })
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => {
    const url = URL.createObjectURL(file)
    setImageUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [file])

  function baseScaleFor(width: number, height: number): number {
    return Math.max(FRAME_WIDTH / width, frameHeight / height)
  }

  function clampOffset(value: Offset, dispWidth: number, dispHeight: number): Offset {
    const minX = Math.min(0, FRAME_WIDTH - dispWidth)
    const minY = Math.min(0, frameHeight - dispHeight)
    return {
      x: Math.min(0, Math.max(value.x, minX)),
      y: Math.min(0, Math.max(value.y, minY)),
    }
  }

  const baseScale = naturalSize ? baseScaleFor(naturalSize.width, naturalSize.height) : 1
  const effectiveScale = baseScale * zoom
  const displayWidth = naturalSize ? naturalSize.width * effectiveScale : 0
  const displayHeight = naturalSize ? naturalSize.height * effectiveScale : 0

  function handleImageLoad() {
    const img = imgRef.current
    if (!img) return
    const width = img.naturalWidth
    const height = img.naturalHeight
    setNaturalSize({ width, height })
    const scale = baseScaleFor(width, height)
    const dispWidth = width * scale
    const dispHeight = height * scale
    setZoom(1)
    setOffset({ x: (FRAME_WIDTH - dispWidth) / 2, y: (frameHeight - dispHeight) / 2 })
  }

  function handlePointerDown(e: React.PointerEvent<HTMLDivElement>) {
    e.currentTarget.setPointerCapture(e.pointerId)
    dragRef.current = { startX: e.clientX, startY: e.clientY, startOffset: offset }
  }

  function handlePointerMove(e: React.PointerEvent<HTMLDivElement>) {
    if (!dragRef.current) return
    const dx = e.clientX - dragRef.current.startX
    const dy = e.clientY - dragRef.current.startY
    setOffset(
      clampOffset(
        { x: dragRef.current.startOffset.x + dx, y: dragRef.current.startOffset.y + dy },
        displayWidth,
        displayHeight
      )
    )
  }

  function handlePointerUp(e: React.PointerEvent<HTMLDivElement>) {
    dragRef.current = null
    if (e.currentTarget.hasPointerCapture(e.pointerId)) {
      e.currentTarget.releasePointerCapture(e.pointerId)
    }
  }

  function applyZoom(nextZoom: number) {
    if (!naturalSize) return
    const clamped = Math.min(MAX_ZOOM, Math.max(1, nextZoom))
    const scale = baseScaleFor(naturalSize.width, naturalSize.height) * clamped
    const dispWidth = naturalSize.width * scale
    const dispHeight = naturalSize.height * scale
    setZoom(clamped)
    setOffset((prev) => clampOffset(prev, dispWidth, dispHeight))
  }

  function handleWheel(e: React.WheelEvent<HTMLDivElement>) {
    e.preventDefault()
    applyZoom(zoom - e.deltaY * 0.001)
  }

  function handleConfirm() {
    const img = imgRef.current
    if (!img || !naturalSize) return
    const canvas = document.createElement('canvas')
    canvas.width = targetWidth
    canvas.height = targetHeight
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    setIsSaving(true)
    const scaleFactor = targetWidth / FRAME_WIDTH
    ctx.drawImage(
      img,
      offset.x * scaleFactor,
      offset.y * scaleFactor,
      displayWidth * scaleFactor,
      displayHeight * scaleFactor
    )
    canvas.toBlob((blob) => {
      setIsSaving(false)
      if (blob) onConfirm(blob)
    }, 'image/png')
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-lg p-6 w-full max-w-sm">
        <h2 className="text-lg font-bold text-gray-900 mb-1">Ajustar imagem de capa</h2>
        <p className="text-sm text-gray-600 mb-4">
          Arraste a imagem para posicionar e use o zoom para ajustar ao quadro padrão do relatório.
        </p>

        <div
          className="relative mx-auto overflow-hidden rounded-md border border-gray-300 bg-gray-100 cursor-move select-none touch-none"
          style={{ width: FRAME_WIDTH, height: frameHeight }}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onWheel={handleWheel}
        >
          {imageUrl && (
            <img
              ref={imgRef}
              src={imageUrl}
              onLoad={handleImageLoad}
              draggable={false}
              alt="Prévia para recorte"
              className="absolute top-0 left-0 max-w-none pointer-events-none"
              style={
                displayWidth && displayHeight
                  ? {
                      width: displayWidth,
                      height: displayHeight,
                      transform: `translate(${offset.x}px, ${offset.y}px)`,
                    }
                  : undefined
              }
            />
          )}
        </div>

        <div className="flex items-center gap-3 mt-4">
          <span className="text-xs text-gray-500 shrink-0">Zoom</span>
          <input
            type="range"
            min={1}
            max={MAX_ZOOM}
            step={0.01}
            value={zoom}
            onChange={(e) => applyZoom(parseFloat(e.target.value))}
            disabled={!naturalSize}
            className="flex-1 accent-[#0f9448]"
          />
        </div>

        <div className="flex gap-3 justify-end mt-6">
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 text-gray-700 bg-gray-200 hover:bg-gray-300 rounded-lg transition-colors font-medium"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            disabled={!naturalSize || isSaving}
            className="px-4 py-2 text-white bg-[#0f9448] hover:bg-[#0d843f] rounded-lg transition-colors font-medium disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {isSaving ? 'Salvando...' : 'Usar esta imagem'}
          </button>
        </div>
      </div>
    </div>
  )
}
