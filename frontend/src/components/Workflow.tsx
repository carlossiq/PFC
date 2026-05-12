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
  const { input, setInput, step2SelectedTheme, step2ThemeSet, setStep2SelectedTheme, setStep2ThemeSet } = useFormStore();
  const { push: historyPush, pop: historyPop, reset: historyReset } = useHistoryStore();
  const [topicError, setTopicError] = useState(false);
  const [hasAttempted, setHasAttempted] = useState(false);

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

  const handleRefineParameters = () => {
    if (handleValidateTopic()) {
      // Dados já estão no formStore, apenas avançar no workflow
      setStep(step, 0);
    }
  };

  const handleStartProspection = () => {
    if (handleValidateTopic()) {
      console.log("Iniciando prospecção com:", input);
      nextStep();
    }
  };

  const handleCancel = () => {
    setTab(TABS.WELCOME);
    reset();
    historyReset();
    setTopicError(false);
    setHasAttempted(false);
  };

  // Avança step e salva o estado atual no histórico antes de sair
  const handleNext = () => {
    historyPush({
      step,
      substep,
      selectedTheme: step2SelectedTheme,
      themeSet: step2ThemeSet,
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
      setStep2ThemeSet(snapshot.themeSet);
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