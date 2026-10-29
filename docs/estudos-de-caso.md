# Estudos de caso — bugs reais do MotoClub Brasil

Bugs encontrados em produção no [motoclub.run](https://motoclub.run), uma plataforma que eu idealizei, construí e testo sozinho.
O ponto em comum: **nenhum deles gerava erro nem log.** A tela parecia certa, o servidor respondia 200,
e o usuário simplesmente não conseguia fazer o que queria.

Todos os casos abaixo já estão corrigidos. Falhas de segurança estão descritas no nível do conceito,
sem detalhe que sirva de receita.

---

## 1. O site inteiro parecia funcionar, mas nenhum botão respondia

**Sintoma.** Relatos intermitentes de "botão não clica" e "fica em CARREGANDO". A página estava visualmente perfeita.
Por várias sessões o problema foi atribuído à ferramenta de preview, porque não reproduzia de forma óbvia.

**Investigação.** Duas hipóteses testadas e **falsificadas** em produção (cache e revalidação, com `Cache-Control`
conferido a cada tentativa). A causa real apareceu quebrando algo de propósito: removendo os arquivos de loading da
rota, o build passou a apontar o mecanismo.

**Causa raiz.** Cada `loading.tsx` do Next.js cria um limite de Suspense implícito. Nessa versão, a troca de
streaming nunca completava: o HTML ficava preso num `<div hidden>` estático e **nenhum evento do React estava
ligado** a nada. Aparência 100% correta, interatividade zero.

**Correção.** Remoção dos 22 `loading.tsx` e Suspense explícito onde ele era de fato necessário. Isso ainda revelou
um erro real que o Suspense implícito escondia.

**O que ficou.** A suíte reprova qualquer página com erro de JavaScript, mesmo que a tela "pareça" certa.

---

## 2. O link no WhatsApp às vezes vinha com imagem grande, às vezes sem

**Sintoma.** Ao compartilhar um evento, o card do WhatsApp ora saía grande, ora pequeno, ora sem imagem.
Duas correções anteriores atacaram o sintoma e o problema voltou.

**Investigação.** Medi em vez de teorizar: baixei a `og:image` de um evento que falhava e comparei com as meta tags.
A imagem real era **1279x1600 (vertical), com perfil ICC**; as meta tags declaravam **1200x630**.

**Causa raiz.** O recorte 1200x630 era gerado por canvas **no navegador** de quem cadastrava o evento. Quando essa etapa
falhava (calada), a página apontava para a foto original — e o crawler do WhatsApp descarta em silêncio a imagem
que não bate com o declarado.

**Correção.** A imagem passou a ser normalizada no servidor: 1200x630 exatos, JPEG **baseline**, sem ICC nem EXIF,
cabeçalho JFIF e `Content-Length`. Verificado byte a byte em produção.

**O que ficou.** [`tests/test_share_preview.py`](../tests/test_share_preview.py) abre a página como o crawler do
WhatsApp e inspeciona os marcadores do JPEG ([`support/jpeg.py`](../support/jpeg.py)): progressive, ICC,
tamanho real contra o declarado e tipo servido contra o declarado.

---

## 3. Qualquer usuário conseguia se promover a administrador

**Sintoma.** Nenhum. Foi achado de forma proativa, ao revisar como um novo admin seria cadastrado.

**Causa raiz.** Duas falhas que só são graves juntas:
1. a regra de segurança do banco que deixa o usuário editar o próprio perfil validava **qual linha** ele editava,
   mas não **quais valores** ele gravava — incluindo o campo de administrador;
2. várias rotas do servidor confiavam nesse campo da tabela, e não na permissão assinada dentro do token de login.

**Correção.** Defesa em profundidade: um gatilho no banco que impede o usuário comum de alterar esse campo, e todas as
rotas administrativas passaram a checar só a permissão do token, que o cliente não consegue alterar.
Testado com conta descartável, antes e depois.

**Lição.** Duas fontes de verdade para a mesma permissão sempre acabam divergindo. Quando a fonte errada é editável
pelo usuário, a divergência deixa de ser bug de tela e vira escalação de privilégio.

---

## 4. A regra de segurança que só existia em produção

**Sintoma.** Numa varredura com 10 contas de teste, um diretor de sede conseguia cadastrar membro na sede de outro.

**Investigação.** As migrations do repositório estavam corretas. Consultando as políticas **reais** do banco de
produção (`pg_policies`), apareceu uma política que **nunca tinha sido versionada**, aplicada direto no banco em
algum momento, que liberava a inserção para qualquer usuário logado.

**Por que demorou a aparecer.** Os testes anteriores sempre usavam contas que tinham motivo legítimo de passar
(presidente, diretor da própria sede). Ninguém tinha testado com um **estranho sem vínculo nenhum**.

**Lição.** O repositório não é a fonte de verdade do que está em produção. E todo teste de permissão precisa do
caso negativo: a pessoa que **não** deveria conseguir.

---

## 5. "Esqueci minha senha" nunca tinha funcionado

**Sintoma.** Achado testando outra funcionalidade: o link de recuperação de senha, recém-gerado, sempre caía em
"Link inválido ou expirado". Quem não usava login do Google e esquecia a senha ficava fora da conta para sempre.

**Causa raiz.** A biblioteca de autenticação usada no navegador não processava sozinha o token que vem no `#hash` do
link de recuperação. Nenhum evento disparava, nenhuma sessão era criada, nenhum erro aparecia.

**Correção.** Leitura explícita do hash e criação da sessão. Validado com link real em produção.

---

## 6. "Senha incorreta" com a senha certa, só no celular

**Sintoma.** Um usuário recebeu uma senha temporária e jurava digitar certo. Testada direto na API, a senha funcionava.

**Causa raiz.** Os campos de e-mail e senha não desligavam a capitalização automática do teclado. No Android, a
primeira letra da senha virava maiúscula — e o usuário nunca vê, porque o campo é mascarado.

**Correção.** `autoCapitalize="none"`, `autoCorrect="off"` e `autoComplete` corretos em todos os campos de
credencial, mais normalização do e-mail antes do login.

**Lição.** "Senha errada" relatada por usuário não é evidência de senha errada. É por isso que a suíte roda
**no tamanho de um celular** por padrão.

---

## Técnica que atravessa vários casos: testar com sessão real, nunca com a chave de serviço

Em várias telas, o usuário clicava em salvar, via "SALVO!", e nada era gravado. O banco devolvia sucesso com
**0 linhas alteradas**, que é o comportamento normal quando a regra de segurança bloqueia uma atualização.

Testar com a chave de serviço do banco nunca acharia isso, porque ela ignora as regras de segurança. Os testes de
permissão do projeto (no repositório privado) criam contas descartáveis e abrem uma **sessão real** para cada uma,
sem senha, exatamente como o navegador do usuário faria. Cada teste cobre quem deve conseguir **e** quem não deve,
e apaga tudo no fim.

---

## Achados desta suíte (28/10/2026)

Na primeira execução contra produção, a suíte encontrou 4 problemas que ninguém tinha relatado. Ficam marcados como
`xfail` com motivo: o CI continua verde, o problema fica documentado, e quando for corrigido o teste avisa para
tirar a marca.

| # | Achado | Teste |
|---|---|---|
| A1 | Página de clube não declara `og:image`: o link vai pro WhatsApp sem imagem, mesmo quando o clube tem brasão | `test_share_preview.py` |
| A2 | Evento sem foto: as meta tags declaram `image/jpeg`, o servidor entrega PNG | `test_share_preview.py` |
| A3 | Oficinas e postos de uma importação regional caíram todos na mesma coordenada (centro da cidade): 7 e 9 pinos empilhados | `test_map_api.py` |
| A4 | A home disparava erro de hidratação do React (#418) em toda visita — **corrigido no mesmo dia** | `test_public_pages.py` |

**Como o A4 foi fechado.** Ele estava marcado como `xfail(strict=True)`. Horas depois, uma mudança de cache publicada
na home eliminou o erro, e na execução seguinte o teste saiu como **XPASS e reprovou** — exatamente para avisar que
o problema tinha sumido e a marca precisava sair. Sem isso, um `xfail` esquecido esconderia uma regressão futura.
