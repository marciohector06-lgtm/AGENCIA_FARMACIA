// Comandos customizados do Cypress para este projeto ficam aqui.

const TOKEN_KEY = "farmacia_mas_token";

declare global {
  // eslint-disable-next-line @typescript-eslint/no-namespace -- augmentação de tipos do Cypress exige `namespace` (padrão oficial da lib)
  namespace Cypress {
    interface Chainable {
      /**
       * Visita uma rota já "logada", sem bater no backend: AppShell só
       * verifica se existe um token não-nulo no localStorage (a validação
       * real do JWT é 100% no backend), então um valor qualquer libera o
       * guard. Use quando a tela testada não depende de dados reais vindos
       * de um backend autenticado (ex.: só checar chrome/navegação, ou
       * telas com as próprias chamadas mockadas via cy.intercept).
       */
      visitAutenticado(path: string): Chainable<Cypress.AUTWindow>;
      /**
       * Loga de verdade contra o backend (`apiUrl` do cypress.config.ts) e
       * visita a rota já com um JWT válido no localStorage. Use quando a
       * tela faz chamadas reais (CRUD "backend real") que o backend só
       * aceita com um token que passa na validação de verdade.
       */
      visitAutenticadoReal(path: string): Chainable<Cypress.AUTWindow>;
    }
  }
}

Cypress.Commands.add("visitAutenticado", (path: string) => {
  return cy.visit(path, {
    onBeforeLoad(win) {
      win.localStorage.setItem(TOKEN_KEY, "fake-token-para-teste-e2e");
    },
  });
});

Cypress.Commands.add("visitAutenticadoReal", (path: string) => {
  const apiUrl = Cypress.env("apiUrl") || "http://127.0.0.1:8001/api/v1";
  return cy
    .request("POST", `${apiUrl}/auth/login`, {
      email: "operador@farmacia.local",
      senha: "CHANGE_ME_OPERADOR",
    })
    .then((res) => {
      return cy.visit(path, {
        onBeforeLoad(win) {
          win.localStorage.setItem(TOKEN_KEY, res.body.access_token);
        },
      });
    });
});

export {};
