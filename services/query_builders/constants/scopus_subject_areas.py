"""
Scopus SUBJAREA field: códigos ASJC (All Science Journal Classification).

Diferente de outros campos simples da Scopus (AUTH, AFFIL, KEY...), SUBJAREA
não aceita texto livre entre aspas - só aceita um dos 27 códigos de 4 letras
abaixo, sem aspas (ex: SUBJAREA(COMP), nunca SUBJAREA("Computer Science")).
Testado direto contra a API: com aspas e nome livre, 0 resultados sempre,
mesmo em queries amplas; com o código correto, resultados normais.

A LLM que gera o `field_of_study` não conhece essa lista (ver
config/prompts/general_system_prompt.txt, que pede algo como "Computer
Vision" ou "Remote Sensing" - texto livre e granular, não um dos 27
códigos), então o texto que ela gera precisa ser mapeado pro código mais
próximo antes de virar SUBJAREA(...).
"""

from typing import Optional

# As 27 áreas maiores da classificação ASJC da Elsevier (código -> nome
# oficial). Referência: https://service.elsevier.com/app/answers/detail/a_id/15181
ASJC_SUBJECT_AREAS: dict[str, str] = {
    "AGRI": "Agricultural and Biological Sciences",
    "ARTS": "Arts and Humanities",
    "BIOC": "Biochemistry, Genetics and Molecular Biology",
    "BUSI": "Business, Management and Accounting",
    "CENG": "Chemical Engineering",
    "CHEM": "Chemistry",
    "COMP": "Computer Science",
    "DECI": "Decision Sciences",
    "DENT": "Dentistry",
    "EART": "Earth and Planetary Sciences",
    "ECON": "Economics, Econometrics and Finance",
    "ENER": "Energy",
    "ENGI": "Engineering",
    "ENVI": "Environmental Science",
    "HEAL": "Health Professions",
    "IMMU": "Immunology and Microbiology",
    "MATE": "Materials Science",
    "MATH": "Mathematics",
    "MEDI": "Medicine",
    "MULT": "Multidisciplinary",
    "NEUR": "Neuroscience",
    "NURS": "Nursing",
    "PHAR": "Pharmacology, Toxicology and Pharmaceutics",
    "PHYS": "Physics and Astronomy",
    "PSYC": "Psychology",
    "SOCI": "Social Sciences",
    "VETE": "Veterinary",
}

# Termos/subáreas comuns que a LLM tende a gerar (ver exemplos no prompt e em
# temas reais já testados: "Artificial Intelligence", "Medical Informatics",
# "Robotics", "Remote Sensing", "Atmospheric Science"...), mapeados pro
# código ASJC mais próximo. Chaves em minúsculo; o lookup normaliza o input.
_KEYWORD_TO_CODE: dict[str, str] = {
    # Computação
    "computer science": "COMP",
    "computer vision": "COMP",
    "artificial intelligence": "COMP",
    "machine learning": "COMP",
    "deep learning": "COMP",
    "data science": "COMP",
    "software engineering": "COMP",
    "information technology": "COMP",
    "informatics": "COMP",
    "medical informatics": "COMP",
    "robotics": "COMP",
    "cybersecurity": "COMP",
    # Engenharia
    "engineering": "ENGI",
    "mechanical engineering": "ENGI",
    "aerospace engineering": "ENGI",
    "electrical engineering": "ENGI",
    "civil engineering": "ENGI",
    "chemical engineering": "CENG",
    # Terra / ambiente
    "remote sensing": "EART",
    "atmospheric science": "EART",
    "earth science": "EART",
    "geology": "EART",
    "environmental science": "ENVI",
    "environmental": "ENVI",
    # Saúde / medicina
    "medicine": "MEDI",
    "medical": "MEDI",
    "clinical": "MEDI",
    "health sciences": "HEAL",
    "healthcare": "HEAL",
    "health": "HEAL",
    "nursing": "NURS",
    "dentistry": "DENT",
    "pharmacology": "PHAR",
    "pharmaceutical": "PHAR",
    "veterinary": "VETE",
    "neuroscience": "NEUR",
    "psychology": "PSYC",
    "immunology": "IMMU",
    "microbiology": "IMMU",
    # Ciências biológicas
    "biochemistry": "BIOC",
    "genetics": "BIOC",
    "molecular biology": "BIOC",
    "biology": "AGRI",
    "biological sciences": "AGRI",
    "agricultural": "AGRI",
    "agriculture": "AGRI",
    # Ciências exatas
    "physics": "PHYS",
    "astronomy": "PHYS",
    "chemistry": "CHEM",
    "materials science": "MATE",
    "mathematics": "MATH",
    "energy": "ENER",
    # Humanas / sociais / negócios
    "economics": "ECON",
    "finance": "ECON",
    "business": "BUSI",
    "management": "BUSI",
    "accounting": "BUSI",
    "social sciences": "SOCI",
    "social science": "SOCI",
    "arts": "ARTS",
    "humanities": "ARTS",
    "decision sciences": "DECI",
    "multidisciplinary": "MULT",
}


def resolve_asjc_code(free_text: str) -> Optional[str]:
    """
    Mapeia um texto livre de área de estudo (gerado pela LLM) pro código
    ASJC mais próximo. Retorna None se não achar nenhuma correspondência
    razoável - nesse caso o chamador deve descartar o valor em vez de gerar
    uma cláusula SUBJAREA que nunca vai casar com nada.
    """
    normalized = free_text.strip().lower()
    if not normalized:
        return None

    # Já é um código válido (a LLM raramente faz isso, mas não custa aceitar).
    if free_text.strip().upper() in ASJC_SUBJECT_AREAS:
        return free_text.strip().upper()

    if normalized in _KEYWORD_TO_CODE:
        return _KEYWORD_TO_CODE[normalized]

    # Substring nos dois sentidos (ex: "medical informatics" contém
    # "informatics"; "AI" descrito como "applied artificial intelligence"
    # contém "artificial intelligence") - aliases mais longos primeiro pra
    # não deixar um match curto e genérico vencer um mais específico.
    for alias in sorted(_KEYWORD_TO_CODE, key=len, reverse=True):
        if alias in normalized or normalized in alias:
            return _KEYWORD_TO_CODE[alias]

    return None
