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
    "computação": "COMP",
    "ciência da computação": "COMP",
    "inteligência artificial": "COMP",
    "aprendizado de máquina": "COMP",
    "big data": "COMP",
    "blockchain": "COMP",
    "internet of things": "COMP",
    "iot": "COMP",
    "internet das coisas": "COMP",
    "computer networks": "COMP",
    "networking": "COMP",
    "natural language processing": "COMP",
    "nlp": "COMP",
    "quantum computing": "COMP",
    # Telecomunicações
    "telecommunications": "ENGI",
    "telecommunication": "ENGI",
    "telecomunicações": "ENGI",
    "telecomunicação": "ENGI",
    "telecom": "ENGI",
    "telecommunications engineering": "ENGI",
    "wireless communications": "ENGI",
    "wireless networks": "ENGI",
    "redes sem fio": "ENGI",
    "mobile networks": "ENGI",
    "5g": "ENGI",
    "6g": "ENGI",
    "signal processing": "ENGI",
    "processamento de sinais": "ENGI",
    "fiber optics": "ENGI",
    "fibra óptica": "ENGI",
    "satellite communications": "ENGI",
    "comunicações por satélite": "ENGI",
    # Engenharia
    "engineering": "ENGI",
    "mechanical engineering": "ENGI",
    "aerospace engineering": "ENGI",
    "electrical engineering": "ENGI",
    "civil engineering": "ENGI",
    "chemical engineering": "CENG",
    "engenharia": "ENGI",
    "engenharia mecânica": "ENGI",
    "engenharia elétrica": "ENGI",
    "engenharia civil": "ENGI",
    "engenharia eletrônica": "ENGI",
    "electronics": "ENGI",
    "eletrônica": "ENGI",
    "control systems": "ENGI",
    "automation": "ENGI",
    "automação": "ENGI",
    "biomedical engineering": "ENGI",
    "engenharia biomédica": "ENGI",
    "automotive engineering": "ENGI",
    "electric vehicles": "ENGI",
    "veículos elétricos": "ENGI",
    # Terra / ambiente
    "remote sensing": "EART",
    "atmospheric science": "EART",
    "earth science": "EART",
    "geology": "EART",
    "geography": "EART",
    "geografia": "EART",
    "oceanography": "EART",
    "oceanografia": "EART",
    "meteorology": "EART",
    "meteorologia": "EART",
    "environmental science": "ENVI",
    "environmental": "ENVI",
    "meio ambiente": "ENVI",
    "ciências ambientais": "ENVI",
    # Saúde / medicina
    "medicine": "MEDI",
    "medical": "MEDI",
    "clinical": "MEDI",
    "medicina": "MEDI",
    "health sciences": "HEAL",
    "healthcare": "HEAL",
    "health": "HEAL",
    "saúde": "HEAL",
    "public health": "HEAL",
    "saúde pública": "HEAL",
    "epidemiology": "MEDI",
    "epidemiologia": "MEDI",
    "surgery": "MEDI",
    "cirurgia": "MEDI",
    "cardiology": "MEDI",
    "cardiologia": "MEDI",
    "oncology": "MEDI",
    "oncologia": "MEDI",
    "nursing": "NURS",
    "enfermagem": "NURS",
    "dentistry": "DENT",
    "odontologia": "DENT",
    "pharmacology": "PHAR",
    "pharmaceutical": "PHAR",
    "farmacologia": "PHAR",
    "toxicology": "PHAR",
    "toxicologia": "PHAR",
    "veterinary": "VETE",
    "veterinária": "VETE",
    "neuroscience": "NEUR",
    "neurociência": "NEUR",
    "psychology": "PSYC",
    "psicologia": "PSYC",
    "immunology": "IMMU",
    "microbiology": "IMMU",
    "imunologia": "IMMU",
    "microbiologia": "IMMU",
    # Ciências biológicas
    "biochemistry": "BIOC",
    "genetics": "BIOC",
    "molecular biology": "BIOC",
    "genomics": "BIOC",
    "biotechnology": "BIOC",
    "biophysics": "BIOC",
    "bioquímica": "BIOC",
    "genética": "BIOC",
    "biologia molecular": "BIOC",
    "biotecnologia": "BIOC",
    "biology": "AGRI",
    "biological sciences": "AGRI",
    "agricultural": "AGRI",
    "agriculture": "AGRI",
    "biologia": "AGRI",
    "agricultura": "AGRI",
    "nutrition": "AGRI",
    "nutrição": "AGRI",
    "food science": "AGRI",
    "ciência de alimentos": "AGRI",
    # Ciências exatas
    "physics": "PHYS",
    "astronomy": "PHYS",
    "astrophysics": "PHYS",
    "quantum physics": "PHYS",
    "física": "PHYS",
    "astronomia": "PHYS",
    "astrofísica": "PHYS",
    "chemistry": "CHEM",
    "química": "CHEM",
    "materials science": "MATE",
    "nanotechnology": "MATE",
    "ciência dos materiais": "MATE",
    "nanotecnologia": "MATE",
    "mathematics": "MATH",
    "matemática": "MATH",
    "statistics": "MATH",
    "estatística": "MATH",
    "energy": "ENER",
    "energia": "ENER",
    "renewable energy": "ENER",
    "energia renovável": "ENER",
    "solar energy": "ENER",
    "energia solar": "ENER",
    "wind energy": "ENER",
    "energia eólica": "ENER",
    # Humanas / sociais / negócios
    "economics": "ECON",
    "finance": "ECON",
    "economia": "ECON",
    "finanças": "ECON",
    "business": "BUSI",
    "management": "BUSI",
    "accounting": "BUSI",
    "negócios": "BUSI",
    "administração": "BUSI",
    "contabilidade": "BUSI",
    "logistics": "BUSI",
    "logística": "BUSI",
    "marketing": "BUSI",
    "social sciences": "SOCI",
    "social science": "SOCI",
    "ciências sociais": "SOCI",
    "law": "SOCI",
    "direito": "SOCI",
    "education": "SOCI",
    "educação": "SOCI",
    "arts": "ARTS",
    "humanities": "ARTS",
    "artes": "ARTS",
    "humanidades": "ARTS",
    "linguistics": "ARTS",
    "linguística": "ARTS",
    "philosophy": "ARTS",
    "filosofia": "ARTS",
    "history": "ARTS",
    "história": "ARTS",
    "decision sciences": "DECI",
    "operations research": "DECI",
    "pesquisa operacional": "DECI",
    "multidisciplinary": "MULT",
    "multidisciplinar": "MULT",
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
