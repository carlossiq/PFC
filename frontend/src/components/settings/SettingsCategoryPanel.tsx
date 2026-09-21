import { useEffect, useState } from 'react'
import { RangeSliderInput } from '../RangeSliderInput'
import { Toggle } from '../Toggle'
import { InfoTooltip } from '../InfoTooltip'
import { ConfirmButton } from '../ConfirmButton'
import { listSettings, updateSetting } from '../../services/config'
import type { AppSetting } from '../../services/config'

// search_year_from/search_year_to não têm range (ver db/config_seed.py) -
// não existe teto natural pro ano inicial, e o teto do ano atual pro ano
// final é validado aqui e no backend (config_router.py::_validate_year),
// não é um "range" pra desenhar slider.
const YEAR_KEYS_MAX_CURRENT_YEAR = new Set(['search_year_from', 'search_year_to'])

interface TextSettingFieldProps {
  setting: AppSetting
  saving: boolean
  onCommit: (value: string) => void
}

// Campo de texto com botão de confirmação lateral (em vez de salvar no
// blur) - o botão fica invisível até o valor digitado diferir do salvo,
// depois de clicar ele soma de volta (ConfirmButton.tsx).
function TextSettingField({ setting, saving, onCommit }: TextSettingFieldProps) {
  const [draft, setDraft] = useState(setting.value)

  useEffect(() => {
    setDraft(setting.value)
  }, [setting.value])

  const isYearField = YEAR_KEYS_MAX_CURRENT_YEAR.has(setting.key)
  const dirty = draft !== setting.value

  function handleConfirm() {
    let next = draft
    if (isYearField) {
      const currentYear = new Date().getFullYear()
      const parsed = parseInt(draft, 10)
      if (Number.isFinite(parsed) && parsed > currentYear) {
        next = String(currentYear)
        setDraft(next)
      }
    }
    onCommit(next)
  }

  return (
    <div className="flex items-center gap-2">
      <input
        type={setting.is_secret ? 'password' : 'text'}
        value={draft}
        placeholder={setting.is_secret ? '(vazio)' : undefined}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && dirty) handleConfirm()
        }}
        className="flex-1 text-sm border border-gray-300 rounded-md px-2 py-1.5 text-gray-900"
      />
      <ConfirmButton visible={dirty} disabled={saving} onConfirm={handleConfirm} />
    </div>
  )
}

interface SettingsCategoryPanelProps {
  categories: string[]
}

// Painel genérico pra um conjunto de categorias de app_settings - decide o
// controle certo por value_type: bool -> Toggle, numérico com min/max ->
// RangeSliderInput, string (ou ano, sem range) -> TextSettingField. Cada
// box tem um ícone de interrogação com o que aquele campo faz.
export function SettingsCategoryPanel({ categories }: SettingsCategoryPanelProps) {
  const [settings, setSettings] = useState<AppSetting[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [savingKey, setSavingKey] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    listSettings()
      .then((all) => {
        if (!cancelled) setSettings(all.filter((s) => categories.includes(s.category)))
      })
      .catch(() => {
        if (!cancelled) setError('Não foi possível carregar as configurações.')
      })
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [categories.join(',')])

  async function commit(key: string, value: string) {
    setSavingKey(key)
    setError(null)
    try {
      const updated = await updateSetting(key, value)
      setSettings((prev) => (prev ? prev.map((s) => (s.key === key ? updated : s)) : prev))
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      setError(typeof detail === 'string' ? detail : `Não foi possível salvar "${key}".`)
    } finally {
      setSavingKey(null)
    }
  }

  if (error) return <p className="text-sm text-red-600">{error}</p>
  if (!settings) return <p className="text-sm text-gray-500">Carregando...</p>
  if (settings.length === 0) return <p className="text-sm text-gray-500">Nenhuma configuração nessa categoria.</p>

  return (
    <div className="space-y-5">
      {settings.map((setting) => (
        <div key={setting.key} className="rounded-lg border border-gray-200 bg-white p-4">
          {setting.value_type === 'bool' ? (
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <p className="text-sm font-medium text-gray-800">{setting.label ?? setting.key}</p>
                {setting.description && (
                  <InfoTooltip description={setting.description} defaultValue={setting.default_value} />
                )}
              </div>
              <Toggle
                enabled={setting.value.toLowerCase() === 'true'}
                onChange={(enabled) => commit(setting.key, enabled ? 'true' : 'false')}
              />
            </div>
          ) : setting.min_value !== null && setting.max_value !== null ? (
            <RangeSliderInput
              label={setting.label ?? setting.key}
              value={parseFloat(setting.value) || 0}
              min={setting.min_value}
              max={setting.max_value}
              step={setting.step ?? 1}
              disabled={savingKey === setting.key}
              onCommit={(value) => commit(setting.key, String(value))}
              infoIcon={
                setting.description && (
                  <InfoTooltip description={setting.description} defaultValue={setting.default_value} />
                )
              }
            />
          ) : (
            <div className="flex flex-col gap-1">
              <div className="flex items-center gap-1.5">
                <label className="text-sm font-medium text-gray-800">{setting.label ?? setting.key}</label>
                {setting.description && (
                  <InfoTooltip description={setting.description} defaultValue={setting.default_value} />
                )}
              </div>
              <TextSettingField
                setting={setting}
                saving={savingKey === setting.key}
                onCommit={(value) => commit(setting.key, value)}
              />
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
