import { useState, useEffect } from "react";
import { StepsBar } from "./Steps";
import { ConfiguracoesTab } from "./ConfiguracoesTab";
import { Step1 } from "./steps/Step1";
import { OutrosSteps } from "./steps/OutrosSteps";
import { useWorkflowStore } from "../stores/useWorkflowStore";
import { useProspectingStore } from "../stores/useProspectingStore";
import { useFormStore } from "../stores/useFormStore";
import { useHistoryStore } from "../stores/useHistoryStore";
import { useSidebarStore } from "../stores/useSidebarStore";
import { TABS } from "../constants/tabs";
import {
  mapInputToParamInitPayload,
  upsertParamInit,
  deleteParamInit,
  deleteParamInitViaBeacon,
} from "../services/paramInit";

const tabContents = {
  [TABS.WELCOME]: { title: "Welcome", label: "Welcome" },
  [TABS.START_PROSPECTION]: { title: "Start Prospection", label: "Start Prospection" },
  [TABS.SETTINGS]: { title: "Settings", label: "Settings" },
  [TABS.STATISTICS]: { title: "Statistics", label: "Statistics" },
  [TABS.SEARCH]: { title: "Search", label: "Search" },
  [TABS.ABOUT]: { title: "About", label: "About" },
  [TABS.DOCUMENTATION]: { title: "Documentation - Introduction", label: "Introduction" },
  [TABS.DOC_USER_GUIDE]: { title: "Documentation - User Guide", label: "User Guide" },
  [TABS.DOC_API]: { title: "Documentation - API Reference", label: "API Reference" },
  [TABS.DOC_FAQ]: { title: "Documentation - FAQ", label: "FAQ" },
  [TABS.HELP]: { title: "Help", label: "Help" },
  [TABS.USER]: { title: "Profile", label: "Profile" },
};

export function WorkflowPage() {
  const { tab, setTab } = useWorkflowStore();
  const { setLocked } = useSidebarStore();
  const { step, substep, nextStep, prevStep, reset, setStep } = useProspectingStore();
  const {
    input,
    setInput,
    step2SelectedTheme,
    setStep2SelectedTheme,
    setShouldRegenerateStep2,
    paramInitId,
    setParamInitId,
    reset: formReset,
  } = useFormStore();
  const { push: historyPush, pop: historyPop, reset: historyReset } = useHistoryStore();
  const [topicError, setTopicError] = useState(false);
  const [hasAttempted, setHasAttempted] = useState(false);
  const [isSavingParams, setIsSavingParams] = useState(false);

  useEffect(() => {
    if (tab === TABS.START_PROSPECTION) {
      setLocked(true);
    } else {
      setLocked(false);
    }
  }, [tab, setLocked]);

  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (tab === TABS.START_PROSPECTION) {
        e.preventDefault();
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [tab]);

  // pagehide só dispara quando a saída da página de fato acontece (diferente do
  // beforeunload, que dispara mesmo se o usuário cancelar o prompt de saída) -
  // por isso é aqui, e não no beforeunload, que descartamos a tupla PARAM_INIT.
  useEffect(() => {
    const handlePageHide = () => {
      if (tab === TABS.START_PROSPECTION && paramInitId) {
        deleteParamInitViaBeacon(paramInitId);
      }
    };

    window.addEventListener('pagehide', handlePageHide);
    return () => window.removeEventListener('pagehide', handlePageHide);
  }, [tab, paramInitId]);

  const handleFormChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setInput({ [name as keyof typeof input]: value });
    if (name === "theme" && value.trim()) {
      setTopicError(false);
    }
  };

  const handleValidateTopic = () => {
    setHasAttempted(true);
    if (!input.theme.trim()) {
      setTopicError(true);
      return false;
    }
    return true;
  };

  // Cria ou atualiza a tupla PARAM_INIT no backend com os dados atuais do formStore.
  // Retorna true se salvou com sucesso (e nesse caso já guardou o id retornado).
  const saveParamInit = async () => {
    setIsSavingParams(true);
    try {
      const payload = mapInputToParamInitPayload(input);
      const result = await upsertParamInit(paramInitId, payload);
      setParamInitId(result.id);
      return true;
    } catch (err) {
      console.error("Falha ao salvar parâmetros iniciais:", err);
      return false;
    } finally {
      setIsSavingParams(false);
    }
  };

  const handleRefineParameters = () => {
    if (handleValidateTopic()) {
      // Apenas navega para o Step2 - o PARAM_INIT só é persistido na confirmação (handleNext).
      // Força a regeneração dos parâmetros, já que o usuário pode ter mudado o input no Step1.
      setShouldRegenerateStep2(true);
      setStep(step, 0);
    }
  };

  const handleStartProspection = async () => {
    if (handleValidateTopic()) {
      // "Gerar Query" pula o Step2, então o save precisa acontecer aqui mesmo.
      const saved = await saveParamInit();
      if (saved) {
        nextStep();
      }
    }
  };

  const handleCancel = () => {
    if (paramInitId) {
      deleteParamInit(paramInitId).catch((err) =>
        console.error("Falha ao descartar parâmetros iniciais:", err)
      );
    }
    setTab(TABS.WELCOME);
    reset();
    formReset();
    historyReset();
    setTopicError(false);
    setHasAttempted(false);
  };

  // Avança step e salva o estado atual no histórico antes de sair.
  // Ao sair do Step2 (confirmar tema), persiste o PARAM_INIT antes de avançar.
  const handleNext = async () => {
    if (step === 0 && substep === 0) {
      const saved = await saveParamInit();
      if (!saved) return;
    }

    historyPush({
      step,
      substep,
      selectedTheme: step2SelectedTheme,
    });
    nextStep();
  };

  // Volta ao step anterior restaurando o estado salvo no histórico
  const handlePrevStep = () => {
    const snapshot = historyPop();
    if (snapshot) {
      setStep(snapshot.step, snapshot.substep);
      if (snapshot.selectedTheme) {
        setStep2SelectedTheme(snapshot.selectedTheme);
      }
    } else {
      prevStep();
    }
  };

  const currentTab = tabContents[tab as keyof typeof tabContents] || tabContents[TABS.SETTINGS];
  const isStartProspection = tab === TABS.START_PROSPECTION;

  return (
    <main className="flex-1 p-2 transition-all duration-300">
      <div className="h-[calc(100vh-5rem)] bg-gray-200 rounded-tl-2xl overflow-hidden flex flex-col">
        {isStartProspection && <StepsBar />}

        <div className="flex-1 overflow-y-auto px-4 py-3">
          {isStartProspection ? (
            <>
              <Step1
                step={step}
                substep={substep}
                formData={input}
                temaError={topicError}
                hasAttempted={hasAttempted}
                isSaving={isSavingParams}
                onFormChange={handleFormChange}
                onRefinirParametros={handleRefineParameters}
                onGerar={handleStartProspection}
                onCancel={handleCancel}
                onBack={handlePrevStep}
                onNext={handleNext}
              />
              <OutrosSteps
                step={step}
                substep={substep}
                onBack={handlePrevStep}
                onNext={handleNext}
              />
            </>
          ) : tab === TABS.SETTINGS ? (
            <ConfiguracoesTab />
          ) : (
            <>
              <h2 className="text-2xl font-bold mb-4">{currentTab.title}</h2>
              <p>Conteúdo de {currentTab.label}</p>
            </>
          )}
        </div>
      </div>
    </main>
  );
}