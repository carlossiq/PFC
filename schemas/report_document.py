"""Schemas for the REPTEC/AGITEC LaTeX report document endpoints (POST
/report/{session_id}/sections/{section_key}/rag|generate, /sections/static,
/assemble, /compile-pdf) - separado de schemas/report.py (que cobre só os
PNGs gerados por ReportService)."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, model_validator


class SectionRagResponse(BaseModel):
    """Resultado de POST /report/{session_id}/sections/{section_key}/rag."""

    section_key: str
    rag_context: str
    status: str


class SectionGenerateResponse(BaseModel):
    """Resultado de POST /report/{session_id}/sections/{section_key}/generate."""

    section_key: str
    generated_text: str
    status: str


class SectionGenerateRequest(BaseModel):
    """Corpo (opcional) de POST /report/{session_id}/sections/{section_key}/generate -
    estatísticas agregadas que o FRONT já tem em memória (step4PatentResults/
    step4ArticleResults, ver useChartCreation.ts) pra alimentar os prompts de
    'informacoes_cientificas'/'informacoes_tecnologicas'/'tendencias_ciclo_vida'
    (ver report_prompts.py). Existem porque `_fetch_final_patents_and_articles`
    (dados vindos do banco) fica vazio na prática - os documentos da busca
    FINAL nunca são persistidos em patent/article, só os da probe (ver
    buildProbeQueryPayload no front) - sem isso essas 3 seções sempre geram
    texto genérico tipo "não há dados disponíveis", mesmo com resultados reais.
    Todos os campos são opcionais e só sobrescrevem o que `_build_report_data`
    calcularia (quase sempre 0/vazio hoje); omitir um campo preserva esse
    default."""

    article_count: Optional[int] = None
    top_journals: list[str] = Field(default_factory=list)
    top_fields: list[str] = Field(default_factory=list)
    patent_count: Optional[int] = None
    top_applicants: list[str] = Field(default_factory=list)
    top_cpc_codes: list[str] = Field(default_factory=list)
    s_curve_phase: Optional[str] = None
    growth_rate: Optional[str] = None
    peak_year: Optional[int] = None


class SignatureBlock(BaseModel):
    """Assinante no formato do REPTEC: "NOME – POSTO/GRAD." numa linha e a
    função na linha de baixo (ex.: "RICARDO W. A. GUIMARÃES – TC" /
    "Adj da Seção de Informações Tecnológicas")."""

    nome: str = ""
    posto: str = ""
    funcao: str = ""
    # Formato antigo (posto e função num campo só) - payloads já salvos em
    # SessionReport.assemble_payload continuam remontáveis: vira `posto`.
    posto_funcao: str = ""

    @model_validator(mode="after")
    def _legacy_posto_funcao(self) -> "SignatureBlock":
        if not self.posto.strip() and self.posto_funcao.strip():
            self.posto = self.posto_funcao
        return self


class SignaturesInput(BaseModel):
    """Cada papel (elaborado/revisado/aprovado) aceita 1+ assinantes - o
    front sempre manda pelo menos um item por papel (não deixa remover o
    último, ver ReportGeneration.tsx), mas o backend não depende disso: uma
    lista vazia aqui simplesmente não sobrescreve o default de
    DEFAULT_SIGNATURES (ver _merge_signatures)."""

    elaborado_por: list[SignatureBlock] = Field(default_factory=list)
    revisado_por: list[SignatureBlock] = Field(default_factory=list)
    aprovado_por: list[SignatureBlock] = Field(default_factory=list)


class StaticSectionsRequest(BaseModel):
    """Corpo de POST /report/{session_id}/sections/static - monta Capa,
    Sumário, Metodologia, Referências (administrativas), Referências
    Bibliográficas e Assinaturas localmente, sem LLM/RAG (ver
    config/prompts/report_static_sections.py)."""

    numero: str = Field(..., description="Número do REPTEC, ex.: '001'")
    ano: str = Field(..., description="Ano do REPTEC, ex.: '2026'")
    referencias_administrativas: list[str] = Field(
        default_factory=list,
        description="Ex.: 'DIEx Nº 115-A3/DCT de 6 de janeiro de 2023' - editado pelo usuário.",
    )
    referencias_bibliograficas_adicionais: list[str] = Field(default_factory=list)
    databases: list[str] = Field(
        default_factory=list,
        description="Bases ADICIONAIS às auto-detectadas pela fonte real da busca final da sessão "
        "(ver _detect_databases_used em report_document_router.py) - normalmente pode ficar vazio.",
    )
    assinaturas: Optional[SignaturesInput] = None
    period_start: Optional[int] = Field(
        default=None,
        description="Ano inicial efetivamente usado na busca (ver step4PatentQuery/ArticleQuery.year_range no "
        "front) - sobrescreve SessionInput.year_from (quase sempre null hoje, o ano é escolhido por query, "
        "não no Step1) quando informado.",
    )
    period_end: Optional[int] = None
    tema: str = Field(default="", description="Tema do relatório - entra na Finalidade (texto fixo).")
    destinatario: str = Field(
        default="",
        description='Para quem é o relatório, ex.: "Indústria de Material Bélico do Brasil (IMBEL)" - completa a '
        "frase fixa da Finalidade (ver report_static_sections.render_finalidade).",
    )
    objetivo: Optional[str] = Field(
        default=None,
        description="Objetivo escrito pelo usuário - quando vem preenchido substitui a seção de IA 'objetivo'.",
    )


class StaticSectionsResponse(BaseModel):
    metodologia: str
    referencias_administrativas: list[str]
    referencias_bibliograficas: list[str]
    databases_detected: list[str] = Field(
        default_factory=list,
        description="Bases de dados detectadas automaticamente a partir de SessionProbeQuery.fonte "
        "(mais as que vieram em StaticSectionsRequest.databases) - exibido como info read-only no front.",
    )


class QuadroBuscaInput(BaseModel):
    """Quadro de busca (query final + contagem) exibido na seção Resultados -
    o front já tem esses dados em memória (step4PatentQuery/step4ArticleQuery
    + step4*Results), por isso vem do corpo da requisição em vez de
    reconstruído no backend."""

    patente_query: Optional[str] = None
    patente_count: Optional[int] = None
    artigo_query: Optional[str] = None
    artigo_count: Optional[int] = None


class AssembleRequest(BaseModel):
    """Corpo de POST /report/{session_id}/assemble - dados da capa e
    assinaturas (referências administrativas e demais seções vêm do que já
    foi persistido pelas rotas de seção/estáticas)."""

    numero: str
    ano: str
    tema: str
    referencias_administrativas: list[str] = Field(default_factory=list)
    assinaturas: Optional[SignaturesInput] = None
    quadro_busca: Optional[QuadroBuscaInput] = None
    # Linha "Rio de Janeiro, 10 de agosto de 2023." antes das assinaturas -
    # a data é a da montagem (ver _local_data).
    local: str = "Rio de Janeiro"


class AssembleResponse(BaseModel):
    """Resultado de POST /report/{session_id}/assemble - só produz o .tex
    (nunca compila PDF, ver POST /compile-pdf)."""

    tex_object_key: str
    tex_content: str
    sections_missing: list[str] = []
    charts_missing: list[str] = []


class CompilePdfRequest(BaseModel):
    """Corpo (opcional) de POST /report/{session_id}/compile-pdf - quando
    `tex_content` vem preenchido (edição livre feita na tela do documento),
    sobrescreve o `.tex` persistido ANTES de compilar, já que o texto
    editado no front nunca é salvo automaticamente em nenhuma outra rota."""

    tex_content: Optional[str] = None


class CompilePdfResponse(BaseModel):
    """Resultado de POST /report/{session_id}/compile-pdf - rota separada,
    só chamada quando o usuário decidir compilar."""

    success: bool
    pdf_object_key: Optional[str] = None
    pdf_base64: Optional[str] = None
    log: Optional[str] = None


class ReportSectionStatus(BaseModel):
    """Status persistido de uma seção (ver SessionReportSection) - usado por
    GET /{session_id}/document pra reconstruir o checklist ao retomar."""

    section_key: str
    status: str
    generated_text: Optional[str] = None


class ReportDocumentResponse(BaseModel):
    """Resultado de GET /report/{session_id}/document - estado atual do
    relatório dessa sessão (se algum), usado tanto pra retomar o checklist
    quanto pra reabrir uma sessão já finalizada direto na tela de documento.
    `report_status`/`tex_content`/`pdf_available` vêm None/""/False quando a
    sessão ainda não tem nenhum SessionReport (nunca passou por /assemble)."""

    has_report: bool
    report_status: Optional[str] = None
    tex_object_key: Optional[str] = None
    tex_content: Optional[str] = None
    pdf_available: bool = False
    sections: list[ReportSectionStatus] = Field(default_factory=list)


class ReportChartItem(BaseModel):
    filename: str
    image_base64: str
    chart_type: str
    document_type: str
    caption: str
    # "generated" = gráfico criado pelo sistema (não pode ser excluído no
    # editor); "attachment" = imagem avulsa enviada pelo usuário.
    origin: str = "generated"


class ReportChartsResponse(BaseModel):
    charts: list[ReportChartItem] = Field(default_factory=list)


class ReportPdfResponse(BaseModel):
    pdf_base64: str


class ReviewRequest(BaseModel):
    """Corpo de POST /report/{session_id}/review - o .tex ATUAL do editor
    (pode ter edições ainda não compiladas)."""

    tex_content: str
    # Log da última compilação que falhou (o front já tem em mãos) - vira
    # "problemas de LaTeX" com a linha correspondente.
    compile_log: Optional[str] = None
    # Segunda opinião por IA (ponto de uso "report_review") - mais lenta,
    # só quando o usuário pede.
    include_ai: bool = False


class ReviewLatexIssue(BaseModel):
    line: int
    message: str
    severity: str
    offset: Optional[int] = None
    length: int = 0
    replacement: Optional[str] = None


class ReviewSuggestion(BaseModel):
    offset: int
    length: int
    original: str
    replacements: list[str]
    message: str
    category: str
    source: str
    rule_id: str = ""
    section: str = ""


class ReviewScopeItem(BaseModel):
    start: int
    end: int
    section: str
    reason: str


class ReviewResponse(BaseModel):
    latex_issues: list[ReviewLatexIssue] = Field(default_factory=list)
    suggestions: list[ReviewSuggestion] = Field(default_factory=list)
    scope: list[ReviewScopeItem] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
