# Base mínima (~357 MB, ver texlive/texlive:latest-minimal no Docker Hub) +
# só os pacotes que config/prompts/report_latex_template.py de fato usa
# (verificado por grep \usepackage no próprio template, não uma aposta de
# "scheme" pronto) - muito mais leve que texlive/texlive:latest (full,
# ~2,74 GB), que instala milhares de pacotes nunca referenciados por este
# relatório. `tlmgr install` roda uma vez, no build da imagem (precisa de
# internet aqui) - o container final, já com os pacotes instalados, não
# precisa de internet pra compilar depois na intranet restrita.
FROM texlive/texlive:latest-minimal

# "minimal" só traz os motores TeX/Metafont crus - nem o kernel do LaTeX
# (latex-bin, article.cls etc, ver collection-latex) vem instalado. Coleções
# em vez de pacotes avulsos: mais robusto que ir descobrindo dependência
# faltante uma a uma (collection-latex = kernel + classes base;
# collection-latexrecommended já cobre geometry/graphics/hyperref).
RUN tlmgr update --self && \
    tlmgr install \
        collection-latex \
        collection-latexrecommended \
        collection-fontsrecommended \
        babel-portuges \
        enumitem \
        latexmk && \
    tlmgr path add
# tlmgr path add: a imagem "latest-minimal" (diferente de "latest"/"full") não
# põe o bin dir do TeX Live (/usr/local/texlive/<ano>/bin/x86_64-linux) no
# PATH por padrão - sem isso "latexmk"/"pdflatex" não são achados em tempo de
# execução mesmo instalados. `tlmgr path add` cria os symlinks no lugar certo.

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

COPY app.py .

EXPOSE 8090

CMD ["python3", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8090"]
