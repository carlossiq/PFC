import { useState, useEffect } from "react";
import { StepsBar } from "./Steps";
import { ConfiguracoesTab } from "./ConfiguracoesTab";
import { SearchPage } from "../pages/SearchPage";
import { StatisticsPage } from "../pages/StatisticsPage";
import { Step1 } from "./steps/Step1";
import { Step3 } from "./steps/Step3";
import { InitialResults } from "./steps/InitialResults";
import { TermSampling } from "./steps/TermSampling";
import { FinalExploration } from "./steps/FinalExploration";
import { FinalResults } from "./steps/FinalResults";
import { OutrosSteps } from "./steps/OutrosSteps";
import { SaveProgressButton } from "./SaveProgressButton";
import { useWorkflowStore } from "../stores/useWorkflowStore";
import { useProspectingStore } from "../stores/useProspectingStore";
import { useFormStore } from "../stores/useFormStore";
import { useHistoryStore } from "../stores/useHistoryStore";
import { useSidebarStore } from "../stores/useSidebarStore";
import { TABS } from "../constants/tabs";
import { STEPS } from "../constants/steps";
import { buildSaveSessionPayload, saveSession } from "../services/sessionInput";
import { resolveIntakePayload } from "../services/refineTopic";

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
    step2Candidates,
    step2GeneratedForInput,
    setShouldRegenerateStep2,
    resetStep2Iterations,
    incrementStep2Iterations,
    step3Queries,
    step3GeneratedForIntake,
    step3ArticleQueries,
    step3ArticleGeneratedForIntake,
    aiCallsInFlight,
    reset: formReset,
  } = useFormStore();
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
    // Editar o input original do Step1 reseta o contador de iterações do Step2
    // (refinamentos anteriores não valem mais pra um input diferente).
    resetStep2Iterations();
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
      // Apenas navega para o Step2 - nada é persistido no backend até a sessão
      // ser finalizada. Só força regeneração dos parâmetros (e conta como uma
      // iteração de refinamento por IA) se o input mudou desde a última
      // geração - senão reaproveita os candidatos já gerados sem chamar a IA
      // de novo.
      const inputChanged = JSON.stringify(input) !== step2GeneratedForInput;
      if (inputChanged) {
        incrementStep2Iterations();
        setShouldRegenerateStep2(true);
      }
      setStep(step, 0);
    }
  };

  const handleStartProspection = () => {
    if (handleValidateTopic()) {
      // "Gerar Query" pula o Step2 (sem refinamento por IA), indo direto pra
      // Exploração Inicial (mesmo destino que "Confirm" já usa) - nada é
      // persistido no backend até a sessão ser finalizada. O Step3 trata o
      // input cru da mesma forma que um tema refinado pela IA.
      historyPush({
        step,
        substep,
        selectedTheme: step2SelectedTheme,
      });
      // Limpa uma seleção do Step2 de uma visita anterior - sem isso,
      // resolveIntakePayload usaria o tema (possivelmente editado) de uma
      // visita anterior ao Step2 em vez do input cru que o usuário acabou de
      // preencher, contrariando a intenção de "Gerar Query" (pular a IA).
      setStep2SelectedTheme(null);
      setStep(STEPS.INITIAL_EXPLORATION, null);
    }
  };

  const handleCancel = () => {
    setTab(TABS.WELCOME);
    reset();
    formReset();
    historyReset();
    setTopicError(false);
    setHasAttempted(false);
  };

  // Avança step e salva o estado atual no histórico antes de sair.
  const handleNext = () => {
    historyPush({
      step,
      substep,
      selectedTheme: step2SelectedTheme,
    });
    nextStep();
  };

  // Salva o progresso atual (o que estiver preenchido até o momento) com
  // completed=false. Cria a sessão na primeira vez (POST), atualiza nas
  // seguintes (PUT), guardando o sessionId retornado no form store.
  const handleSaveProgress = async () => {
    const formState = useFormStore.getState()
    const payload = buildSaveSessionPayload(formState, false)
    const result = await saveSession(formState.sessionId, formState.sessionName, payload)
    useFormStore.getState().setSessionId(result.session_id, result.session_public_id)
    // Evita reenviar (e duplicar) as mesmas chamadas de IA num próximo save.
    useFormStore.getState().clearAiCallLog()
  }

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

  // "Refinar parâmetros" só navega (sem chamar IA de novo) quando já existem
  // candidatos gerados pro input atual - mesma assinatura comparada em
  // handleRefineParameters acima. `step2Candidates.length > 0` distingue de
  // uma sessão retomada que nunca passou pelo Step2 (só o tema cru do
  // usuário), onde a assinatura bate trivialmente mas não há parâmetros de
  // IA pra "ver".
  const step2AlreadyGenerated =
    step2Candidates.length > 0 && JSON.stringify(input) === step2GeneratedForInput;

  // "Gerar Query" pula o Step2 (zera step2SelectedTheme em
  // handleStartProspection), então a assinatura do intake que o Step3 vai
  // comparar é sempre a do input cru - ver resolveIntakePayload.
  const step3IntakeSignature = JSON.stringify(resolveIntakePayload(input, null));
  const step3AlreadyGenerated =
    !!step3Queries &&
    step3GeneratedForIntake === step3IntakeSignature &&
    !!step3ArticleQueries &&
    step3ArticleGeneratedForIntake === step3IntakeSignature;

  return (
    <main className="flex-1 p-2 transition-all duration-300">
      <div className="h-[calc(100vh-5rem)] bg-gray-200 rounded-tl-2xl overflow-hidden flex flex-col">
        {isStartProspection && <StepsBar />}

        <div className="relative flex-1 overflow-y-auto px-4 py-3">
          {isStartProspection && (
            <SaveProgressButton
              disabled={!input.theme.trim() || aiCallsInFlight > 0}
              onSave={handleSaveProgress}
            />
          )}
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
                refineAlreadyGenerated={step2AlreadyGenerated}
                queryAlreadyGenerated={step3AlreadyGenerated}
                onCancel={handleCancel}
                onBack={handlePrevStep}
                onNext={handleNext}
              />
              <Step3
                step={step}
                substep={substep}
                onBack={handlePrevStep}
                onNext={handleNext}
              />
              <InitialResults
                step={step}
                substep={substep}
                onBack={handlePrevStep}
                onNext={handleNext}
              />
              <TermSampling
                step={step}
                substep={substep}
                onBack={handlePrevStep}
                onNext={handleNext}
              />
              <FinalExploration
                step={step}
                substep={substep}
                onBack={handlePrevStep}
                onNext={handleNext}
              />
              <FinalResults
                step={step}
                substep={substep}
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
          ) : tab === TABS.SEARCH ? (
            <SearchPage />
          ) : tab === TABS.STATISTICS ? (
            <StatisticsPage />
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