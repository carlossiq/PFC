Feature nova: persistência de rascunho "PARAM_INIT"
Step1/Step2 do wizard agora salvam o formulário em progresso no backend, permitindo limpar o rascunho se o usuário cancelar ou fechar a aba.

schemas/param_init.py (novo) — validação do payload (tema obrigatório, resto opcional).
db/param_init_models.py (novo) — model SQLAlchemy da tabela param_init.
api/routes/param_init.py (novo) — POST/PUT/DELETE /param-init + POST /discard (alias para sendBeacon, que não manda DELETE).
app/main.py — router registrado.
db/init_db.py — cria as tabelas do param_init num bloco próprio.
frontend/src/services/ (novo) — client axios + funções upsertParamInit/deleteParamInit/deleteParamInitViaBeacon.
useFormStore.ts — novo campo paramInitId.
Workflow.tsx — salva ao sair do Step1, deleta ao cancelar, usa pagehide+beacon ao fechar a aba.
Fix de bug real (achado durante o setup de ambiente)
db/models.py — removido o índice idx_patent_applicants_year, que tentava criar um índice btree sobre uma coluna JSON (Postgres não permite — quebrava a inicialização do banco em qualquer instância nova). Confirmei que essa coluna nunca é filtrada em query nenhuma, então a remoção é segura.
Ambiente/infra
.gitignore — adicionado __pycache__/ e *.pyc (não estava ignorado antes).
UI — pedidos desta sessão
Step1.tsx — dica abaixo do campo Keywords: "Separe as keywords por vírgulas".
Step2.tsx — keywords agora aparecem em lista numerada (tanto em "Initial Parameters" quanto em "Generated Parameters"), em vez de uma linha separada por vírgula.
Não relacionado à feature (routine)
frontend/package-lock.json — só bump de dependências transitivas do Babel via npm install.
Ainda não rastreado, decisão pendente
ambinte.md — suas notas pessoais de setup (nome com typo, conteúdo específico desta máquina). Combinamos deixar de fora do commit, a menos que você queira reescrever como doc limpo.
Tudo já validado: build do frontend passa sem erros, backend sobe e roda ponta a ponta (testei criar/deletar um param_init via API).