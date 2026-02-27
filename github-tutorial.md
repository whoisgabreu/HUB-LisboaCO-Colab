Tutorial: Trabalhando com Branch por Feature + Pull Request

Este guia explica:

Como criar uma branch por feature

Como abrir uma Pull Request (PR)

Como remover a branch após o merge

Fluxo recomendado para times que usam GitHub.

🚀 1️⃣ Atualize sua main antes de começar

Antes de criar qualquer feature, garanta que sua base está atualizada:

git checkout main
git pull origin main

Isso evita conflitos futuros.

🌿 2️⃣ Criando uma Branch por Feature

Cada nova funcionalidade deve ter sua própria branch.

Exemplo: vamos implementar um filtro por operação.

git checkout -b filtro-operacao

📌 Boas práticas para nome de branch:

feature/nome-da-feature

fix/nome-do-bug

chore/ajuste-interno

Exemplo mais profissional:

git checkout -b feature/filtro-operacao
💻 3️⃣ Desenvolvendo a Feature

Faça as alterações normalmente.

Depois:

git add .
git commit -m "feat: adiciona filtro por operação"

Se necessário, faça vários commits organizados.

☁️ 4️⃣ Enviando a Branch para o Repositório Remoto
git push origin feature/filtro-operacao

Agora sua branch está no GitHub.

🔎 5️⃣ Criando a Pull Request (PR)

Acesse o repositório no GitHub

Clique em Compare & pull request

Confirme:

Base: main

Compare: feature/filtro-operacao

Adicione título e descrição claros

Clique em Create pull request

Exemplo de título:

feat: adiciona filtro por operação na listagem
🔁 6️⃣ Atualizando a Branch Antes do Merge (Se necessário)

Se a main mudou enquanto você trabalhava:

git checkout main
git pull
git checkout feature/filtro-operacao
git merge main

Resolva possíveis conflitos e envie novamente:

git push
✅ 7️⃣ Fazendo o Merge

Após revisão e aprovação:

Escolha uma das opções:

Merge commit

Squash and merge (recomendado para histórico limpo)

Clique em Merge pull request.

🗑️ 8️⃣ Apagando a Branch da PR

Após o merge, o GitHub mostrará:

Delete branch

Clique para remover a branch remota.

🖥️ 9️⃣ Apagando a Branch Local

No seu computador:

git branch -d feature/filtro-operacao

Se precisar forçar:

git branch -D feature/filtro-operacao