"""
Seed inicial das tabelas de configuração (db/config_models.py) a partir dos
valores hoje hardcoded em core/config.py - roda uma vez, só se a tabela
correspondente estiver vazia (idempotente: não sobrescreve edições feitas
pelo front em execuções seguintes).

Chamado por db/init_db.py depois do create_all.
"""

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.logging import get_logger
from db.config_models import (
    AppSetting,
    LLMCallSiteBinding,
    LLMProviderConfig,
    SearchApiSelection,
)

logger = get_logger(__name__)


@dataclass(frozen=True)
class _SettingSeed:
    key: str
    value_type: str
    category: str
    label: str
    description: str
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    step: Optional[float] = None
    is_secret: bool = False


# Espelha VARIAVEIS_DE_CONFIGURACAO.md (seções 3-8) - LLM (seção 1) e feature
# flags de API de busca (seção 9) NÃO entram aqui: viram
# LLMProviderConfig/LLMCallSiteBinding e SearchApiSelection, respectivamente.
#
# `description` explica o que o campo faz e as consequências de aumentar ou
# diminuir demais (o front acrescenta o "valor recomendado" sozinho, a
# partir de `default_value` - não precisa repetir o número aqui).
#
# search_year_from/search_year_to não têm min_value/max_value: não existe
# teto natural pro ANO INICIAL (pode ser qualquer ano passado), e o teto do
# ano atual pro ANO FINAL é validado à parte (não é um "range" pra slider -
# ver config_router.py::_validate_year), então os dois ficam como caixa de
# texto simples.
_SETTINGS_SEED: list[_SettingSeed] = [
    # --- external_api (secretas) ---
    _SettingSeed("lens_api_token", "str", "external_api", "Lens API Token", "Token da API Lens (patentes/artigos - lens_patent/lens_scholarly). Sem isso, nenhuma das duas fica disponível como opção de API de busca.", is_secret=True),
    _SettingSeed("ops_consumer_key", "str", "external_api", "OPS Consumer Key", "Consumer key OAuth2 da API OPS (European Patent Office). Sem isso (junto com o Consumer Secret), a OPS não fica disponível como API de patentes.", is_secret=True),
    _SettingSeed("ops_consumer_secret", "str", "external_api", "OPS Consumer Secret", "Consumer secret OAuth2 da API OPS - usado junto com a Consumer Key pra autenticar.", is_secret=True),
    _SettingSeed("scopus_api_key", "str", "external_api", "Scopus API Key", "API key da Scopus (Elsevier). Sem isso, a Scopus não fica disponível como API de artigos.", is_secret=True),
    # --- search ---
    _SettingSeed("search_year_from", "int", "search", "Ano inicial padrão", "Ano inicial da janela de busca (probe search e geração de query). Não existe um mínimo natural (pode cobrir décadas de histórico), mas quanto mais antigo, mais lenta e menos focada tende a ficar a busca inicial; um ano muito recente pode deixar de fora referências importantes mais antigas do tema."),
    _SettingSeed("search_year_to", "int", "search", "Ano final padrão", "Ano final da mesma janela - não pode ser maior que o ano atual (não existe patente/artigo publicado no futuro). Um valor muito no passado exclui publicações recentes do tema."),
    _SettingSeed("probe_top_k", "int", "search", "Top-K da probe", "Número de resultados pedidos na probe search, antes da amostragem pra extração de termos. Aumentar demais deixa a extração de termos mais lenta (o custo cresce mais rápido que o número de documentos) sem necessariamente melhorar a qualidade dos termos; diminuir demais reduz a diversidade da amostra, gerando termos menos representativos do tema.", 1, 100, 1),
    _SettingSeed("final_top_k", "int", "search", "Top-K da busca final", "Número de resultados usados na busca final pra montar os agregados (depositantes/instituições/CPC/área). Aumentar demais deixa a busca final mais lenta e pode esbarrar em limites de paginação das APIs; diminuir demais reduz a robustez estatística dos agregados exibidos.", 1, 500, 1),
    # --- relevance ---
    _SettingSeed("relevance_threshold", "float", "relevance", "Threshold de relevância", "Corte mínimo de relevância pra um resultado ser considerado válido na filtragem. Aumentar demais pode descartar resultados relevantes de verdade (falsos negativos); diminuir demais deixa passar resultados pouco relacionados ao tema (ruído).", 0.0, 1.0, 0.01),
    _SettingSeed("llm_max_query_complexity", "float", "relevance", "Complexidade máxima de query", "Teto de complexidade aceito numa query gerada por IA antes de forçar uma nova tentativa mais simples. Aumentar demais permite queries muito complexas, que as APIs de busca podem rejeitar ou demorar bem mais pra processar; diminuir demais força queries simples demais, perdendo precisão na busca.", 0.0, 1.0, 0.01),
    # --- term_extraction ---
    _SettingSeed("term_extraction_title_weight", "float", "term_extraction", "Peso do título", "Peso do título no BM25F (canal lexical de pontuação) - título costuma ser mais denso em termos-chave que o abstract. Aumentar muito faz os termos dependerem quase só do título, ignorando contexto do abstract; diminuir muito faz o título (geralmente mais informativo) pesar pouco no resultado.", 0.0, 10.0, 0.1),
    _SettingSeed("term_extraction_abstract_weight", "float", "term_extraction", "Peso do abstract", "Peso do abstract no BM25F. Aumentar muito faz o abstract dominar sobre o título; diminuir muito ignora o contexto que só aparece no corpo do abstract, não no título.", 0.0, 10.0, 0.1),
    _SettingSeed("term_extraction_score_threshold", "float", "term_extraction", "Threshold de score", "Corte mínimo de final_rrf_score (escala RRF, não 0-1) pra um termo ser retornado. Aumentar demais pode devolver poucos termos - ou nenhum, se o lote inteiro ficar abaixo do corte (por isso existe o piso de termos mínimos, ver abaixo); diminuir demais deixa passar termos genéricos e pouco relevantes.", 0.0, 0.1, 0.001),
    _SettingSeed("term_extraction_min_returned_terms", "int", "term_extraction", "Piso de termos devolvidos", "Quantidade mínima de termos sempre devolvida, mesmo abaixo do threshold de score. Aumentar demais garante volume mas pode forçar termos de baixa qualidade só pra completar a cota; diminuir demais (perto de 0) pode devolver poucos termos pro usuário selecionar quando o threshold for rígido pro lote.", 0, 60, 1),
    _SettingSeed("term_extraction_unigram_penalty", "float", "term_extraction", "Penalidade de unigrama", "Ajuste de ranking pra termos de 1 palavra (tendem a ser mais genéricos que frases). Mais negativo penaliza mais forte os unigramas, favorecendo termos compostos; perto de 0 ou positivo deixa unigramas competirem em pé de igualdade, podendo poluir a lista com palavras soltas genéricas.", -2.0, 2.0, 0.05),
    _SettingSeed("term_extraction_bigram_bonus", "float", "term_extraction", "Bônus de bigrama", "Ajuste de ranking pra termos de 2 palavras. Mais alto favorece bigramas sobre outros tamanhos; muito negativo os penaliza, favorecendo unigramas ou frases maiores.", -2.0, 2.0, 0.05),
    _SettingSeed("term_extraction_trigram_bonus", "float", "term_extraction", "Bônus de trigrama", "Ajuste de ranking pra termos de 3+ palavras (tendem a ser mais específicos e úteis pra busca). Aumentar demais pode priorizar frases longas e hiperespecíficas de um único documento; diminuir demais perde a vantagem de especificidade desses termos.", -2.0, 2.0, 0.05),
    _SettingSeed("term_extraction_bad_bigram_penalty", "float", "term_extraction", "Penalidade de bigrama ruim", "Penalidade extra quando um bigrama bate um padrão gramatical ruim (ex: advérbio+verbo, sinal de fragmento em vez de frase nominal). Mais negativo filtra mais agressivamente esses fragmentos; perto de 0 deixa esses fragmentos competirem normalmente, poluindo a lista.", -2.0, 0.0, 0.05),
    _SettingSeed("term_extraction_bad_trigram_penalty", "float", "term_extraction", "Penalidade de trigrama ruim", "Mesma penalidade extra por padrão gramatical ruim, pra trigramas. Mais negativo filtra mais agressivamente; perto de 0 deixa passar mais fragmentos não-nominais.", -2.0, 0.0, 0.05),
    _SettingSeed("term_extraction_bm25_k1", "float", "term_extraction", "BM25 k1", "Controla a saturação de frequência de termo no BM25F (o quanto repetir o termo continua aumentando o score). Aumentar demais faz termos muito repetidos dominarem desproporcionalmente o ranking; diminuir muito (perto de 0) faz o score saturar rápido demais, quase ignorando a frequência.", 0.0, 3.0, 0.05),
    _SettingSeed("term_extraction_bm25_b", "float", "term_extraction", "BM25 b", "Controla o quanto o BM25F normaliza pelo tamanho do documento. Aumentar demais (perto de 1) penaliza fortemente termos vindos de documentos longos; diminuir demais (perto de 0) ignora o tamanho do documento, favorecendo documentos longos.", 0.0, 1.0, 0.05),
    _SettingSeed("term_extraction_rrf_k", "int", "term_extraction", "RRF k", "Constante k do Reciprocal Rank Fusion, usada pra fundir os canais de score. Valores altos suavizam a fusão (menos peso pra posição exata no rank); valores baixos fazem os primeiros colocados de cada canal dominarem muito mais o resultado final.", 1, 200, 1),
    _SettingSeed("term_extraction_cvalue_min_frequency", "int", "term_extraction", "Frequência mínima (C-value)", "Frequência bruta mínima pra um candidato sobreviver ao filtro de C-value (redundância entre termos aninhados). Aumentar demais descarta termos raros mas potencialmente relevantes; diminuir demais (1) deixa até termos vistos uma única vez competirem, podendo incluir ruído.", 1, 10, 1),
    # --- fuzzy_matching ---
    _SettingSeed("depositant_fuzzy_match_threshold", "float", "fuzzy_matching", "Threshold de fuzzy match", "Score mínimo (RapidFuzz WRatio, 0-100) pra agrupar nomes parecidos de depositante/instituição como a mesma entidade. Aumentar demais deixa de agrupar variações reais de grafia (ex: 'Acme Corp' e 'Acme Corporation' ficam contados separado); diminuir demais funde entidades na verdade distintas (ex: 'Acme Inc' com 'Acme Solutions Inc').", 0.0, 100.0, 1.0),
    # --- statistical_inference ---
    _SettingSeed("statistical_inference_max_duration_seconds", "int", "statistical_inference", "Duração máxima (s)", "Teto de tempo pra pedir iterações extras de busca até a amostra saturar (Chao1). Aumentar demais deixa a inferência estatística demorar muito mais em temas com pouca saturação; diminuir demais pode interromper antes da amostra ficar estatisticamente confiável.", 1, 600, 1),
    _SettingSeed("statistical_inference_saturation_threshold", "float", "statistical_inference", "Threshold de saturação", "Cobertura estimada (Chao1) abaixo da qual a amostra é considerada insuficiente. Aumentar demais exige mais buscas pra considerar a amostra suficiente (mais tempo/custo); diminuir demais aceita amostras pouco representativas como se já fossem suficientes.", 0.0, 1.0, 0.01),
    _SettingSeed("statistical_inference_f1_ratio_threshold", "float", "statistical_inference", "Threshold de singletons", "Proporção de categorias vistas só 1x acima da qual a amostra é considerada insuficiente (sinal de cauda longa não capturada). Aumentar demais tolera amostras com muita cauda longa não capturada; diminuir demais exige quase nenhum singleton, difícil de atingir em temas de nicho.", 0.0, 1.0, 0.01),
    _SettingSeed("statistical_inference_f2_min", "int", "statistical_inference", "Mínimo de doubletons", "Número mínimo de categorias vistas exatamente 2x pra uma estimativa Chao1 ser considerada estável. Aumentar demais exige amostras muito maiores pra confiar na estimativa; diminuir demais (0) aceita estimativas instáveis, sensíveis a ruído.", 0, 50, 1),
    _SettingSeed("statistical_inference_bootstrap_resamples", "int", "statistical_inference", "Reamostragens (bootstrap)", "Número de reamostragens (bootstrap com reposição) usadas pra medir a estabilidade do ranking top-10. Aumentar demais deixa o cálculo mais lento sem ganho de precisão a partir de um certo ponto; diminuir demais deixa a métrica de estabilidade ruidosa e pouco confiável.", 100, 10000, 100),
    _SettingSeed("statistical_inference_max_titles_for_relevance", "int", "statistical_inference", "Máximo de títulos (relevância)", "Teto de títulos amostrados aleatoriamente pra calcular a relevância semântica média com o tema pesquisado. Aumentar demais deixa o cálculo mais lento (mais embeddings pra gerar); diminuir demais deixa a média pouco representativa (amostra pequena demais).", 1, 100, 1),
    # --- general ---
    _SettingSeed("test_mode", "bool", "general", "Modo de teste", "Força o uso do MockLLMService (respostas falsas, sem custo/rede) em todas as chamadas de IA - usado só pela suíte de testes automatizados. Ligado fora de testes, a aplicação para de chamar qualquer IA de verdade em qualquer call site."),
    _SettingSeed("llm_keybert_model", "str", "general", "Modelo do KeyBERT", "Modelo sentence-transformers usado pelo canal semântico do TermExtractor (KeyBERT) e pelo RAG do relatório. Carregado uma única vez no boot - trocar aqui só faz efeito depois de reiniciar o backend. Alternativas: 'all-mpnet-base-v2' (melhor pra patentes/textos técnicos), 'allenai/specter' (papers acadêmicos)."),
    _SettingSeed("ollama_request_timeout_seconds", "int", "general", "Timeout do Ollama (s)", "Tempo máximo de espera pelas chamadas a um servidor Ollama/compatível (local ou intranet) antes de desistir. Aumentar demais deixa o app esperar muito tempo se o servidor travar; diminuir demais pode cortar respostas de modelos legitimamente lentos (ex: modelos grandes na intranet) antes de terminarem.", 10, 1200, 10),
    _SettingSeed("rag_relative_min_relevance", "float", "general", "Corte relativo do RAG", "Fração do score do trecho mais relevante abaixo da qual um trecho recuperado pelo RAG é descartado antes de ir pro prompt do relatório. Aumentar demais (perto de 1) deixa só os pouquíssimos trechos mais próximos do tema, podendo faltar contexto; diminuir demais (perto de 0) deixa entrar documentos periféricos, e a IA passa a tratar assuntos laterais como centrais.", 0.0, 1.0, 0.05),
    _SettingSeed("languagetool_language", "str", "general", "Idioma da revisão de texto", "Código de idioma do LanguageTool usado no botão \"Revisão\" do editor do relatório (ortografia, acentuação e concordância). O padrão é pt-BR; trocar só faz sentido se o relatório for redigido em outra variante (ex.: pt-PT)."),
    _SettingSeed("rag_top_k_per_section", "int", "general", "Top-K do RAG por seção", "Quantos trechos o RAG (ChromaDB) recupera por seção do relatório antes de montar o prompt de geração de texto. Aumentar demais deixa o prompt maior e mais caro sem necessariamente melhorar o texto gerado; diminuir demais pode faltar contexto relevante pra IA escrever a seção.", 1, 20, 1),
]


def _current_value_as_str(key: str, value_type: str) -> str:
    raw = getattr(settings, key, None)
    if raw is None:
        return ""
    if value_type == "bool":
        return "true" if raw else "false"
    return str(raw)


async def seed_app_settings(session: AsyncSession) -> None:
    count = await session.scalar(select(func.count()).select_from(AppSetting))
    if count:
        return

    for seed in _SETTINGS_SEED:
        current_value = _current_value_as_str(seed.key, seed.value_type)
        session.add(
            AppSetting(
                key=seed.key,
                value=current_value,
                value_type=seed.value_type,
                category=seed.category,
                is_secret=seed.is_secret,
                min_value=seed.min_value,
                max_value=seed.max_value,
                step=seed.step,
                label=seed.label,
                description=seed.description,
                # Nunca guarda o valor original de uma secret como "recomendado" -
                # não existe uma "api_key recomendada", e exporia o segredo do
                # .env original no tooltip pra sempre (update_value nunca toca
                # nesta coluna).
                default_value=None if seed.is_secret else current_value,
            )
        )
    await session.commit()
    logger.info("app_settings_seeded", count=len(_SETTINGS_SEED))


async def seed_missing_app_settings(session: AsyncSession) -> None:
    """Configurações acrescentadas em _SETTINGS_SEED DEPOIS do seed inicial
    (ex.: rag_relative_min_relevance, languagetool_language) - seed_app_settings
    só roda com a tabela vazia, então sem isso elas nunca chegariam a um banco
    já existente. Idempotente: só insere chaves ausentes, nunca altera valor
    editado pelo usuário."""
    existing = set((await session.execute(select(AppSetting.key))).scalars())
    missing = [seed for seed in _SETTINGS_SEED if seed.key not in existing]
    for seed in missing:
        current_value = _current_value_as_str(seed.key, seed.value_type)
        session.add(
            AppSetting(
                key=seed.key,
                value=current_value,
                value_type=seed.value_type,
                category=seed.category,
                is_secret=seed.is_secret,
                min_value=seed.min_value,
                max_value=seed.max_value,
                step=seed.step,
                label=seed.label,
                description=seed.description,
                default_value=None if seed.is_secret else current_value,
            )
        )
    if missing:
        await session.commit()
        logger.info("app_settings_added", keys=[seed.key for seed in missing])


async def seed_search_api_selection(session: AsyncSession) -> None:
    count = await session.scalar(select(func.count()).select_from(SearchApiSelection))
    if count:
        return

    # Preserva o comportamento de hoje: se ambas as flags de uma família
    # vierem True no .env atual (caso real), OPS/Scopus vencem por padrão.
    patent_active = "ops" if getattr(settings, "ops_enabled", True) else "lens_patent"
    scholarly_active = "scopus" if getattr(settings, "scopus_enabled", True) else "lens_scholarly"

    session.add_all(
        [
            SearchApiSelection(family="patent", active_provider_code=patent_active),
            SearchApiSelection(family="scholarly", active_provider_code=scholarly_active),
        ]
    )
    await session.commit()
    logger.info("search_api_selection_seeded", patent=patent_active, scholarly=scholarly_active)


async def seed_llm_configs_and_bindings(session: AsyncSession) -> None:
    count = await session.scalar(select(func.count()).select_from(LLMProviderConfig))
    if count:
        return

    configs: dict[str, LLMProviderConfig] = {}

    if getattr(settings, "llm_anthropic_api_key", None):
        configs["anthropic"] = LLMProviderConfig(
            provider_code="anthropic",
            model=settings.llm_anthropic_model,
            api_key=settings.llm_anthropic_api_key,
            base_url="",
        )
    if getattr(settings, "llm_gemini_api_key", None):
        configs["gemini"] = LLMProviderConfig(
            provider_code="gemini",
            model=settings.llm_gemini_model,
            api_key=settings.llm_gemini_api_key,
            base_url="",
        )
    # Ollama sempre semeado - servidor local não exige api_key.
    configs["ollama"] = LLMProviderConfig(
        provider_code="ollama",
        model=getattr(settings, "ollama_model", "qwen2.5:3b-instruct"),
        api_key=getattr(settings, "ollama_api_key", None) or "",
        base_url=getattr(settings, "ollama_base_url", "http://localhost:11434"),
    )

    for row in configs.values():
        session.add(row)
    await session.commit()
    for row in configs.values():
        await session.refresh(row)

    query_provider = (getattr(settings, "llm_provider", "mock") or "mock").lower()
    query_config = configs.get(query_provider) or configs.get("ollama")

    if query_config is not None:
        for call_site in ("theme_candidates", "probe_query", "final_query"):
            session.add(LLMCallSiteBinding(call_site=call_site, config_id=query_config.id))

    session.add(LLMCallSiteBinding(call_site="report_writing", config_id=configs["ollama"].id))
    await session.commit()
    logger.info("llm_configs_and_bindings_seeded", providers=list(configs.keys()))


async def seed_missing_call_site_bindings(session: AsyncSession) -> None:
    """Pontos de uso de IA criados DEPOIS do seed inicial (ex.:
    report_review) ganham um binding apontando pro mesmo modelo da redação
    do relatório - seed_llm_configs_and_bindings só roda com o banco vazio.
    Idempotente: nunca altera um binding já existente."""
    from app.core.services.llm_config_resolver import CALL_SITES

    existing = {row.call_site: row.config_id for row in (await session.execute(select(LLMCallSiteBinding))).scalars()}
    fallback = existing.get("report_writing")
    if fallback is None:
        fallback = await session.scalar(select(LLMProviderConfig.id).order_by(LLMProviderConfig.id).limit(1))
    if fallback is None:
        return
    missing = [call_site for call_site in CALL_SITES if call_site not in existing]
    for call_site in missing:
        session.add(LLMCallSiteBinding(call_site=call_site, config_id=fallback))
    if missing:
        await session.commit()
        logger.info("llm_call_site_bindings_added", call_sites=missing, config_id=fallback)


async def seed_all_config(session: AsyncSession) -> None:
    await seed_app_settings(session)
    await seed_missing_app_settings(session)
    await seed_search_api_selection(session)
    await seed_llm_configs_and_bindings(session)
    await seed_missing_call_site_bindings(session)
