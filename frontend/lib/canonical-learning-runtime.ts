export interface QuizRuntimeRef {
  learningUnitId: string;
  resultStorageKey: string;
  learnHref: string;
  resultsHref: string;
  restartHref: string;
}

export interface ModuleTestRuntimeRef {
  sectionId: string;
  resultStorageKey: string;
  resultsHref: string;
  restartHref: string;
}

export function buildQuizRuntimeRef(learningUnitId: string): QuizRuntimeRef {
  return {
    learningUnitId,
    resultStorageKey: `quiz_result_${learningUnitId}`,
    learnHref: `/learn/${learningUnitId}`,
    resultsHref: `/quiz/${learningUnitId}/results`,
    restartHref: `/quiz/${learningUnitId}`,
  };
}

export function buildModuleTestRuntimeRef(sectionId: string): ModuleTestRuntimeRef {
  return {
    sectionId,
    resultStorageKey: `module_test_result_${sectionId}`,
    resultsHref: `/module-test/${sectionId}/results`,
    restartHref: `/module-test/${sectionId}`,
  };
}
